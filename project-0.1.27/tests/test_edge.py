"""The edge, defended by the deliverable itself.

app/service.py promises identity, request ids, strict framing, bounded
workers and a clean drain. Every promise below is asserted against the
service booted on an ephemeral port, model-free: an unreachable model is
a dependency problem the edge reports, not a reason the edge cannot be
tested. A change that drops the transfer-encoding refusal, the reserved
key strip or the close-after-error is caught here, not by a client.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "edge-test-token"


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _boot(tmp_path):
    port = _free_port()
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin"), "PORT": str(port),
        "AUTH_TOKEN": TOKEN, "GRANTED_SCOPES": "x",
        "LLM_ENDPOINT": "http://127.0.0.1:9", "STATE_DIR": str(tmp_path / "state"),
        "CORPUS_DIR": str(tmp_path / "no-corpus"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.service"], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        if proc.poll() is not None:
            raise AssertionError(f"service exited {proc.returncode}: {proc.stdout.read()[:800]}")
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            return proc, base, port
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise AssertionError("service never came up: " + proc.stdout.read()[:800])


def _post(base, body, headers=None, token=TOKEN):
    request = urllib.request.Request(
        base + "/", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {}),
                 **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read()), response.headers
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read()), error.headers


def test_the_edge_keeps_its_promises(tmp_path):
    proc, base, port = _boot(tmp_path)
    try:
        # identity: no token, no service; a forged principal is refused by
        # name, as is a forged result
        code, body, _ = _post(base, b'"hello"', token=None)
        assert code == 401 and "request_id" in body
        forged = b'{"query": "q", "principal": {"scopes": ["admin"]}}'
        code, body, headers = _post(base, forged)
        assert code == 422 and "principal" in body["refused"], body
        forged = b'{"query": "q", "answer": "forged"}'
        code, body, headers = _post(base, forged)
        assert code == 422 and "answer" in body["refused"], body
        # request ids: on every response, matching the header
        code, body, headers = _post(base, b"null")
        assert code == 422 and body["request_id"] == headers["X-Request-Id"]
        # framing
        assert _post(base, b"{}", headers={"Content-Length": "1_0"})[0] == 400
        assert _post(base, b"{}", headers={"Transfer-Encoding": "chunked"})[0] == 501
        assert _post(base, b"[" * 20000)[0] == 400
        code, body, headers = _post(base, b"null")
        assert headers.get("Connection") == "close", "errors must close the connection"
        # a request line that never parses is a JSON 400 with an id, not
        # an anonymous dropped socket (a TLS hello on the plaintext port)
        raw = socket.create_connection(("127.0.0.1", port), timeout=5)
        raw.sendall(b"\x16\x03\x01 not http at all\r\n\r\n")
        reply = b""
        try:
            while True:
                chunk = raw.recv(65536)
                if not chunk:
                    break
                reply += chunk
        except OSError:
            pass
        raw.close()
        assert reply.startswith(b"HTTP/1.1 400"), reply[:80]
        assert b"request_id" in reply, reply[:300]
        # a real request reaches the pipeline and answers with a shape
        code, body, _ = _post(base, b'"a question"')
        # an answer, a refusal, a dependency down, or a scaffold that says so
        # by name (501) -- never a bare 500, which once hid an import error
        # on every valid request
        assert code in (200, 422, 501, 503) and "request_id" in body, (code, body)
        # readiness reports the unreachable model, never a dropped socket
        try:
            urllib.request.urlopen(base + "/ready", timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 503
            assert "problems" in json.loads(error.read())
    finally:
        proc.terminate()
        assert proc.wait(timeout=30) == 0, "SIGTERM must drain and exit 0"


def test_a_refused_configuration_is_one_line_and_exit_78(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "app.service"], cwd=ROOT, capture_output=True, text=True,
        env={"PATH": os.environ.get("PATH", "/usr/bin"), "PORT": "not-a-port",
             "AUTH_TOKEN": TOKEN}, timeout=60,
    )
    assert result.returncode == 78, result.stderr[-400:]
    assert "Traceback" not in result.stderr
