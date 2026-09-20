"""The HTTP edge. Stdlib only; runs as `python -m app.service`.

What the edge owns, and nothing else does:

- **identity**: a bearer token (AUTH_TOKEN) or nothing. The principal the
  pipeline sees -- subject and scopes -- is set HERE from configuration,
  never read from the body; a client cannot grant itself a scope.
- **a request id** on every log line and every response, refusals
  included, so an incident is correlated by id rather than by timestamp.
- **framing**: strict Content-Length, no transfer-encoding, a bounded
  body, bounded workers. A slow or hostile socket costs one worker and
  one deadline, never the service.
- **status codes**: refusal 422, dependency failure 503, anything else
  500 carrying the exception's NAME and the request id -- never its text,
  which on a build with a data boundary can carry the data.
- **boot**: configuration parsed once and refused if wrong (exit 78,
  EX_CONFIG); the corpus loaded; dependencies probed for /ready.
- **shutdown**: SIGTERM stops accepting, in-flight requests finish, exit 0.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app.contract import RefusedInput

try:
    # The boundary asserts at import. A violation is a configuration
    # refusal like any other: one line and exit 78, never a traceback the
    # unit restarts five times.
    from app import pipeline
except RuntimeError as boundary_refusal:
    print(json.dumps({"level": "fatal", "boot_problem": str(boundary_refusal)[:300]}),
          file=sys.stderr, flush=True)
    raise SystemExit(78) from None

NEEDS_MODEL = True
NEEDS_ADAPTER = False
HAS_RETRIEVAL = True
HAS_BOUNDARY = True
HAS_CONTROLS = False

try:
    from app.llm import ModelUnconfigured
except ImportError:  # no model seam in this build
    class ModelUnconfigured(RuntimeError):
        pass

try:
    from app.controls import CriticRejected, NeedsApproval
except ImportError:  # nothing mutative in this build
    class NeedsApproval(RuntimeError):
        pass

    class CriticRejected(RuntimeError):
        pass

try:
    from app.ledger import LEDGER
except ImportError:  # nothing outward in this build
    LEDGER = None

# Dependency failures, by type -- not by name. HTTPError is a URLError;
# the model server answering 503 is a retry-later, not a server bug.
TRANSIENT = (urllib.error.URLError, TimeoutError, ConnectionError, ModelUnconfigured)

CONTENT_LENGTH = re.compile(r"^[0-9]{1,12}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
READY_TTL_SECONDS = 5.0
# ready_at starts at -inf so the FIRST poll always probes: seeded at 0.0,
# a poll inside the first seconds of machine uptime answered green with
# no model and no corpus.
STATE: dict = {"corpus_documents": 0, "ready_at": float("-inf"), "ready_problems": [],
               "degraded": []}
_READY_LOCK = threading.Lock()


_LOG_LOCK = threading.Lock()


def _log(**fields) -> None:
    # One write, under a lock: two unlocked writes per line (print, then
    # its newline) interleaved 41% of lines into non-JSON under eight
    # workers, and a log shipper drops what it cannot parse. Flushed, so
    # journalctl at 3am shows what happened and SIGTERM loses nothing.
    line = json.dumps(fields, default=str) + "\n"
    with _LOG_LOCK:
        sys.stderr.write(line)
        sys.stderr.flush()


# --- configuration, parsed once ------------------------------------------


def _int_env(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    if not raw.isdigit() or not low <= int(raw) <= high:
        _log(level="fatal", config=name, value=raw,
             wanted=f"an integer in [{low}, {high}]")
        raise SystemExit(78)
    return int(raw)


def load_config() -> dict:
    """Every variable the edge reads, validated before a socket opens. A
    typo in /etc/app/env is one clear line and exit 78 -- not a restart
    loop with a traceback in it."""
    token = os.environ.get("AUTH_TOKEN", "").strip()
    scopes = [s for s in os.environ.get("GRANTED_SCOPES", "").split(",") if s.strip()]
    subject = os.environ.get("SERVICE_SUBJECT", "").strip()
    if token and not subject:
        subject = "token:" + hashlib.sha256(token.encode()).hexdigest()[:8]
    bind = os.environ.get("BIND", "127.0.0.1").strip()
    try:
        socket.getaddrinfo(bind, None)
    except OSError:
        _log(level="fatal", config="BIND", value=bind, wanted="a resolvable address")
        raise SystemExit(78) from None
    return {
        "port": _int_env("PORT", 8080, 1, 65535),
        "bind": bind,
        "max_body": _int_env("MAX_BODY_BYTES", 1024 * 1024, 1, 1024 * 1024 * 1024),
        "workers": _int_env("WORKERS", 8, 1, 1024),
        "token": token,
        "principal": {"subject": subject or "anonymous",
                      "scopes": [s.strip() for s in scopes] if token else []},
        "log_detail": os.environ.get("LOG_DETAIL", "") == "1",
        "trusted_proxy": os.environ.get("TRUSTED_PROXY", "") == "1",
    }


# --- readiness --------------------------------------------------------------


def _model_problems() -> list[str]:
    endpoint = os.environ.get("LLM_ENDPOINT", "").strip()
    if not endpoint:
        if os.environ.get("ANTHROPIC_API_KEY") and not HAS_BOUNDARY:
            return []
        return ["no model: set LLM_ENDPOINT (see deploy/env.example)"
                + ("; the hosted path is refused behind a boundary" if HAS_BOUNDARY else "")]
    parts = urlparse(endpoint)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return [f"LLM_ENDPOINT must be an http(s) URL, not {endpoint!r}"]
    try:
        with urllib.request.urlopen(endpoint.rstrip("/") + "/v1/models", timeout=3) as r:
            served = json.load(r)
        # A gateway answering a list or a string is a finding, never a
        # dropped connection: every parse failure lands here.
        ids = {m.get("id") for m in served.get("data", []) if isinstance(m, dict)}
    except Exception as exc:  # noqa: BLE001 -- any failure is one finding
        return [f"model endpoint unreachable or malformed: {type(exc).__name__}"]
    wanted = os.environ.get("LLM_MODEL", "").strip()
    if wanted and ids and wanted not in ids:
        return [f"LLM_MODEL {wanted!r} is not served by the endpoint"]
    adapter = os.environ.get("FINETUNED_MODEL", "").strip()
    if adapter and ids and adapter not in ids:
        # /ready was green while the first request failed: the adapter
        # is a served model like any other, listed or not.
        return [f"FINETUNED_MODEL {adapter!r} is not served by the endpoint "
                f"(vLLM --lora-modules names it)"]
    return []


def preflight(config: dict) -> tuple[list[str], list[str]]:
    """(permanent, transient). Permanent problems are configuration and
    refuse the boot; transient ones are dependencies and make /ready 503."""
    permanent, transient = [], []
    if NEEDS_ADAPTER and not os.environ.get("FINETUNED_MODEL", "").strip():
        # A bogus adapter name refused the boot; an absent one once booted
        # green and answered 503 to every request.
        permanent.append("FINETUNED_MODEL unset: this build answers through a fine-tuned "
                         "adapter and has none to answer with (see train/README.md)")
    if HAS_CONTROLS and not config["token"]:
        permanent.append("AUTH_TOKEN unset: outward calls need an authenticated "
                         "principal, so every tool call would be refused")
    if LEDGER is not None and getattr(LEDGER, "problem", None):
        permanent.append(LEDGER.problem)
    loaded = getattr(pipeline, "LOADED", {})
    skipped = loaded.get("skipped") or []
    # Skipped files DEGRADE readiness, they do not deny it: a stray
    # .DS_Store must not take a healthy service out of rotation. Past
    # half the corpus unreadable, it is not the corpus that was sized.
    STATE["degraded"] = skipped[:50]
    total = loaded.get("documents", 0) + len(skipped)
    if total and len(skipped) * 2 > total:
        transient.append(f"corpus: {len(skipped)} of {total} files unreadable")
    if NEEDS_MODEL:
        for problem in _model_problems():
            (transient if "unreachable" in problem else permanent).append(problem)
    if HAS_RETRIEVAL and STATE["corpus_documents"] == 0:
        transient.append("corpus empty: set CORPUS_DIR to the documents to answer from")
    return permanent, transient


def ready_problems(config: dict) -> list[str]:
    """Cached briefly: /ready is polled, and every poll must not become
    an outbound request to the model server."""
    with _READY_LOCK:
        fresh = time.monotonic() - STATE["ready_at"] <= READY_TTL_SECONDS
        if fresh:
            return list(STATE["ready_problems"])
        STATE["ready_at"] = time.monotonic()  # one prober at a time refreshes
    # The outbound probe runs outside the lock: a readiness check must
    # never block behind another readiness check.
    permanent, transient = preflight(config)
    with _READY_LOCK:
        STATE["ready_problems"] = permanent + transient
        return list(STATE["ready_problems"])


# --- the handler --------------------------------------------------------------


def build_handler(config: dict):
    slots = threading.BoundedSemaphore(config["workers"])
    token = config["token"].encode()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "app"
        sys_version = ""
        # A slow or malicious socket costs one thread and one deadline; an
        # idle keep-alive is dropped after this many seconds of silence,
        # which is also how long a drain waits for it.
        timeout = 10
        request_id = "-"

        # -- plumbing -------------------------------------------------------

        def _send(self, code: int, body: dict) -> None:
            data = json.dumps({**body, "request_id": self.request_id},
                              default=str).encode()
            # A request line that never parsed leaves the stdlib believing
            # this is HTTP/0.9, which writes no status line and no headers
            # -- a bare JSON body on the wire. Answer as HTTP/1.1 and close.
            if getattr(self, "request_version", "HTTP/0.9") == "HTTP/0.9":
                self.request_version = "HTTP/1.1"
                self.close_connection = True
            # Any error answered before the body was consumed leaves that
            # body on the socket, where keep-alive would parse it as the
            # next request line. Errors close the connection, always.
            if code >= 400 or STATE.get("draining"):
                self.close_connection = True
            try:
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Request-Id", self.request_id)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                if self.close_connection:
                    self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                _log(level="info", request_id=self.request_id, event="client went away")

        def send_error(self, code, message=None, explain=None):
            # Unsupported methods and framing faults answer in the same
            # JSON the contract promises, never the stdlib's HTML page --
            # and with a request id, which the stdlib path never assigned.
            if self.request_id == "-":
                self._begin()
            self._send(code, {"error": message or "request rejected"})

        def log_message(self, fmt, *args):
            _log(level="access", request_id=self.request_id, client=self._client(),
                 line=fmt % args)

        def _authorised(self) -> bool:
            if not token:
                return True
            header = self.headers.get("Authorization", "")
            given = header[7:].encode() if header.startswith("Bearer ") else b""
            return hmac.compare_digest(given, token)

        def _loopback(self) -> bool:
            return self.client_address[0] in ("127.0.0.1", "::1")

        def _begin(self) -> None:
            # A request line that never parsed has no headers yet -- and it
            # still gets an id and a JSON 400, never a dropped socket.
            headers = getattr(self, "headers", None)
            given = headers.get("X-Request-Id", "") if headers is not None else ""
            self.request_id = given if REQUEST_ID.match(given) else str(uuid.uuid4())[:8]

        def _client(self) -> str:
            # Behind the prescribed proxy every peer is loopback; the
            # forwarded address is trusted only when told to be.
            peer = self.client_address[0]
            headers = getattr(self, "headers", None)
            forwarded = headers.get("X-Forwarded-For", "") if headers is not None else ""
            if config["trusted_proxy"] and forwarded:
                return forwarded.split(",")[0].strip()[:64]
            return peer

        # -- routes -----------------------------------------------------------

        def do_HEAD(self):
            self._begin()
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "POST / with a JSON payload"})

        def do_GET(self):
            self._begin()
            if self.path == "/health":
                # Liveness only: the process is up.
                self._send(200, {"status": "ok"})
            elif self.path == "/ready":
                # Readiness: dependencies answer. A deploy gates on this,
                # so misconfiguration surfaces here, not on the first user.
                # Loopback may ask unauthenticated (the unit's own probe);
                # anyone else needs the token, or /ready is an amplifier.
                if not self._loopback() and not self._authorised():
                    self._send(401, {"error": "bearer token required"})
                    return
                try:
                    problems = ready_problems(config)
                except Exception as exc:  # noqa: BLE001 -- readiness never drops a socket
                    problems = [f"readiness probe failed: {type(exc).__name__}"]
                if problems:
                    self._send(503, {"ready": False, "problems": problems})
                else:
                    # File names are internal; the unauthenticated loopback
                    # probe gets the count, a bearer gets the list.
                    degraded = (STATE["degraded"] if self._authorised() and token
                                else len(STATE["degraded"]))
                    self._send(200, {"ready": True,
                                     "corpus_documents": STATE["corpus_documents"],
                                     "degraded": degraded})
            else:
                self._send(404, {"error": "POST / with a JSON payload"})

        def do_POST(self):
            self._begin()
            if not self._authorised():
                self._send(401, {"error": "bearer token required"})
                return
            if self.path != "/":
                self._send(404, {"error": "POST / with a JSON payload"})
                return
            if self.headers.get("Transfer-Encoding"):
                self._send(501, {"error": "transfer-encoding is not accepted; "
                                          "send Content-Length"})
                return
            lengths = self.headers.get_all("Content-Length") or []
            if len(lengths) != 1:
                self._send(411 if not lengths else 400,
                           {"error": "exactly one Content-Length required"})
                return
            if not CONTENT_LENGTH.match(lengths[0].strip()):
                self._send(400, {"error": "Content-Length is not a decimal integer"})
                return
            length = int(lengths[0])
            if length > config["max_body"]:
                self._send(413, {"error": f"body over {config['max_body']} bytes"})
                return
            # The body is read BEFORE a worker slot is taken: a slow
            # sender costs its own socket deadline, never a slot that a
            # fast caller needed. Eight trickling sockets once made every
            # real request a 503.
            try:
                payload = json.loads(self.rfile.read(length) or b"null")
            except Exception:  # noqa: BLE001 -- RecursionError is not a ValueError
                self._send(400, {"error": "body is not JSON"})
                return
            if not slots.acquire(blocking=False):
                self._send(503, {"error": "saturated; retry shortly"})
                return
            try:
                self._handle(payload)
            finally:
                slots.release()

        def _handle(self, payload) -> None:
            started = time.monotonic()
            try:
                env = pipeline.run_envelope(payload, request_id=self.request_id,
                                            principal=config["principal"])
            except RefusedInput as refusal:
                self._send(422, {"refused": str(refusal)})
                return
            except PermissionError as exc:  # ScopeDenied: the principal lacks it
                self._send(403, {"error": type(exc).__name__})
                return
            except (NeedsApproval, CriticRejected) as exc:  # a control said no
                self._send(409, {"error": type(exc).__name__})
                return
            except LookupError as exc:  # UnregisteredTool: no such tool
                self._send(400, {"error": type(exc).__name__})
                return
            except NotImplementedError as exc:  # a scaffold, by name
                _log(level="error", request_id=self.request_id, client=self._client(),
                     error="NotImplementedError", detail=str(exc)[:200])
                # The name of the state, with the request id; the scaffold's
                # own words go to the journal, never to a caller.
                self._send(501, {"error": "not implemented"})
                return
            except Exception as exc:  # noqa: BLE001 -- mapped, logged, never dropped
                fields = dict(level="error", request_id=self.request_id,
                              client=self._client(), error=type(exc).__name__,
                              ms=int((time.monotonic() - started) * 1000))
                if config["log_detail"]:
                    fields["detail"] = str(exc)[:300]
                _log(**fields)
                self._send(503 if isinstance(exc, TRANSIENT) else 500,
                           {"error": type(exc).__name__})
                return
            response = {"result": pipeline.output(env)}
            # An answer names what it stood on; a run says why it stopped.
            if env.get("retrieved"):
                response["sources"] = [
                    {k: item.get(k) for k in ("id", "source", "rank") if k in item}
                    for item in env["retrieved"]
                ]
            for key in ("stopped_because", "steps", "cost", "retrieval_note",
                        "cited", "evidence_dropped", "decided_by", "baseline",
                        "abstained", "margin", "top", "why"):
                if key in env:
                    response[key] = env[key]
            # The journal says what was decided and how sure: an incident
            # is reconstructed from here, not from a response nobody kept.
            _log(level="info", request_id=self.request_id, event="answered",
                 ms=int((time.monotonic() - started) * 1000),
                 client=self._client(), stopped_because=env.get("stopped_because"),
                 retrieval_note=env.get("retrieval_note"),
                 steps=env.get("steps"), cost=env.get("cost"),
                 decision=env.get("decision"), decided_by=env.get("decided_by"),
                 margin=env.get("margin"), why=env.get("why"))
            self._send(200, response)

    return Handler


class Server(ThreadingHTTPServer):
    # Workers are joined on close, so a drain finishes what it started.
    daemon_threads = False
    block_on_close = True

    def handle_error(self, request, client_address):
        # One structured line, never a traceback: a flood of dropped
        # connections must not push the audit lines out of the journal.
        exc = sys.exc_info()[1]
        _log(level="warning", event="connection error",
             error=type(exc).__name__ if exc else "unknown")


def main() -> int:
    config = load_config()
    if HAS_RETRIEVAL:
        try:
            STATE["corpus_documents"] = pipeline.load_corpus()
        except MemoryError:
            _log(level="fatal", boot_problem="the corpus does not fit in memory; "
                 "raise MemoryMax from the measured sizing in ARCHITECTURE.md "
                 "or lower CORPUS_MAX_MB")
            return 78
        except Exception as exc:  # noqa: BLE001 -- a refusal, never a restart loop
            _log(level="fatal", boot_problem=f"corpus load failed: {type(exc).__name__}: "
                                             f"{str(exc)[:200]}")
            return 78
        loaded = getattr(pipeline, "LOADED", {})
        if loaded.get("refused"):
            _log(level="fatal", boot_problem=loaded["refused"])
            return 78
        for skipped in loaded.get("skipped", []):
            _log(level="warning", event="corpus file skipped", **skipped)
        _log(level="info", event="corpus loaded", documents=STATE["corpus_documents"],
             skipped=len(loaded.get("skipped", [])))
    permanent, transient = preflight(config)
    for problem in permanent:
        _log(level="fatal", boot_problem=problem)
    if permanent:
        return 78
    for problem in transient:
        _log(level="warning", boot_problem=problem)

    try:
        server = Server((config["bind"], config["port"]), build_handler(config))
    except OSError as exc:
        _log(level="fatal", boot_problem=f"cannot bind {config['bind']}:{config['port']}: "
                                         f"{type(exc).__name__}")
        return 78

    def _drain(signum, frame):
        # Stop accepting from another thread (shutdown() blocks until
        # serve_forever returns), then close joins the in-flight workers.
        # Idle keep-alives get Connection: close on their next response and
        # time out within Handler.timeout otherwise.
        STATE["draining"] = True
        _log(level="info", event="sigterm: draining")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _drain)
    _log(level="info", event=f"serving on {config['bind']}:{config['port']}",
         ready_endpoint="/ready", needs_model=NEEDS_MODEL,
         authenticated=bool(config["token"]), workers=config["workers"])
    try:
        server.serve_forever()
    finally:
        server.server_close()
        _log(level="info", event="drained; exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
