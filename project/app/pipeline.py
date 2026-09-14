"""The order things run in.

Ordered by what caps what: a step whose quality bounds another comes
first, so when an answer is wrong there is somewhere to look.
Approval gates and critics are steps like any other -- removing one
is a visible diff, not an oversight.

Only payload-transforming components are chained here. Deployment,
provisioning, evaluation and their kin are decided and emitted, but a
service unit is not a step a payload passes through.

The evaluation harness calls run() with each golden case's raw input.
Adapting that input to the first step's payload shape is yours: do it
at the top of run(), where the seam is visible.
"""

from functools import lru_cache
from pathlib import Path

from app import boundary  # noqa: F401 -- placement checked at import
from app.components import perception
from app.components import reasoning
from app.components import representation
from app.components import retrieval
from app.components import serving
from app.contract import RefusedInput

CORPUS = Path(__file__).resolve().parent.parent / "data" / "corpus"

STEPS = [
    ('perception', perception.Perception()),
    ('serving', serving.Serving()),
    ('representation', representation.Representation()),
    # The deployed index, the same instance evals/retrieval.py measures.
    ('retrieval', retrieval.INDEX),
    ('reasoning', reasoning.Reasoning()),
]


@lru_cache(maxsize=1)
def corpus():
    """The shipped standards, read once: the corpus is static
    (corpus_churn == static), so re-reading it per question buys nothing."""
    return tuple(
        {"id": path.stem, "text": path.read_text(encoding="utf-8", errors="replace")}
        for path in sorted(CORPUS.glob("*.txt"))
    )


def chunks():
    """The corpus as the retrieval step receives it: the steps before it, run
    over the corpus alone."""
    payload = {"documents": list(corpus())}
    for name, step in STEPS:
        if name == 'retrieval':
            return payload["chunks"]
        payload = step.run(payload)
    raise RuntimeError("no retrieval step in STEPS")


def run(payload):
    # The operator, like the harness, hands over a question as bare text. It is
    # asked of the shipped corpus, which rides along with it into perception.
    if not isinstance(payload, str):
        raise RefusedInput(f"a question arrives as text, not {type(payload).__name__}")
    payload = {"query": payload, "documents": list(corpus())}
    for name, step in STEPS:
        payload = step.run(payload)
    return payload["answer"]


# Backported from fde-framework 0.1.11: the deployment runs
# `python -m app.pipeline`, and a module that defines functions and
# exits is a service that dies silently. This is the service.
if __name__ == "__main__":
    # Post-measurement ops hardening, updated to the 0.1.13 emission
    # (threaded server, read deadlines, body cap, catch-all 500s,
    # loopback bind by default) -- after the measured runs, labelled.
    import json as _json
    import os as _os
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from app.contract import RefusedInput

    MAX_BODY = int(_os.environ.get("MAX_BODY_BYTES", str(10 * 1024 * 1024)))

    class _Handler(BaseHTTPRequestHandler):
        # A slow or malicious socket must cost one thread and one
        # deadline, never the service.
        timeout = 30
        def _send(self, code, body):
            data = _json.dumps(body, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "POST / with a JSON payload"})

        def do_POST(self):
            if self.path != "/":
                self._send(404, {"error": "POST / with a JSON payload"})
                return
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._send(411, {"error": "Content-Length required"})
                return
            try:
                length = int(raw_length)
            except ValueError:
                self._send(400, {"error": "Content-Length is not a number"})
                return
            if length < 0 or length > MAX_BODY:
                self._send(413, {"error": "body too large"})
                return
            try:
                payload = _json.loads(self.rfile.read(length) or b"null")
            except ValueError:
                self._send(400, {"error": "body is not JSON"})
                return
            try:
                self._send(200, {"result": run(payload)})
            except RefusedInput as refusal:
                self._send(422, {"refused": str(refusal)})
            except Exception as exc:  # noqa: BLE001
                # A dropped connection tells the caller nothing; a
                # 500 with the exception NAME (never a traceback)
                # is a diagnosable failure.
                self._send(500, {"error": type(exc).__name__,
                                 "detail": str(exc)[:200]})

        def log_message(self, fmt, *args):
            print(fmt % args)

    port = int(_os.environ.get("PORT", "8080"))
    # Loopback by default: exposing the port is a deployment
    # decision made in the unit file (Environment=BIND=...),
    # never a default the code took alone.
    bind = _os.environ.get("BIND", "127.0.0.1")
    print(f"serving on {bind}:{port} -- /health, POST /")
    ThreadingHTTPServer((bind, port), _Handler).serve_forever()
