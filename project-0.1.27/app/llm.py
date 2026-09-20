"""The one place this project talks to a language model.

Configuration is environment, not code:

- LLM_ENDPOINT   an OpenAI-compatible server on this machine or network
                 (vLLM, Ollama) -- the first-class path, because it works
                 inside a boundary.
- LLM_MODEL      model name for that endpoint (or the hosted default).
- ANTHROPIC_API_KEY  the hosted path -- refused outright when this build
                 carries a boundary, because a brief that may not leave
                 does not get to leave via the judge.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


class ModelUnconfigured(RuntimeError):
    """No model is reachable; nothing here guesses instead."""


def _boundary_present() -> bool:
    try:
        import app.boundary  # noqa: F401
    except ImportError:
        return False
    except RuntimeError:
        return True  # the boundary exists, and refused this environment
    return True


def complete_raw(prompt: str, timeout: float | None = None, *,
                 model: str, endpoint: str | None = None,
                 stop: list[str] | None = None) -> str:
    """One completion against /v1/completions, the prompt sent as the bytes
    the caller built. An adapter is trained on raw text by train/lora.py;
    served through the chat endpoint it would be wrapped in the base
    model's chat template -- tokens the recipe never produced.

    `stop` is sent to the server AND applied here: a base model that has
    not learned to stop continues with the next "Question:" it imagines,
    and a server that ignores the field would hand that back as the
    answer."""
    if timeout is None:
        timeout = float(os.environ.get("LLM_TIMEOUT", "120"))
    endpoint = endpoint or os.environ.get("LLM_ENDPOINT")
    if not endpoint:
        raise ModelUnconfigured(
            "an adapter is served by an OpenAI-compatible endpoint; set LLM_ENDPOINT")
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "temperature": 0,
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "512")),
        **({"stop": list(stop)} if stop else {}),
    }).encode()
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LLM_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["LLM_API_KEY"]
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/completions", data=body, headers=headers,
    )
    last_error = None
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                reply = json.load(response)
            try:
                text = reply["choices"][0]["text"]
                for marker in stop or ():
                    text = text.split(marker, 1)[0]
                return text
            except (KeyError, IndexError, TypeError) as exc:
                raise ModelUnconfigured(
                    f"the model endpoint answered without a completion: "
                    f"{str(reply)[:120]}") from exc
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            last_error = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        if attempt == 1:
            time.sleep(0.5)
    raise last_error


def complete(prompt: str, timeout: float | None = None, *,
             endpoint: str | None = None, model: str | None = None,
             max_tokens: int | None = None) -> str:
    if timeout is None:
        timeout = float(os.environ.get("LLM_TIMEOUT", "120"))
    endpoint = endpoint or os.environ.get("LLM_ENDPOINT")
    if endpoint:
        body = json.dumps({
            "model": model or os.environ.get("LLM_MODEL", "default"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            # A local model with no cap holds the request for as long as
            # it feels like reasoning; a person is sometimes waiting.
            "max_tokens": max_tokens or int(os.environ.get("LLM_MAX_TOKENS", "512")),
        }).encode()
        headers = {"Content-Type": "application/json"}
        if os.environ.get("LLM_API_KEY"):
            # A local server behind an auth proxy (vLLM --api-key) still
            # lives inside the boundary; the key rides in the header.
            headers["Authorization"] = "Bearer " + os.environ["LLM_API_KEY"]
        request = urllib.request.Request(
            endpoint.rstrip("/") + "/v1/chat/completions", data=body, headers=headers,
        )
        # One bounded retry on a TRANSPORT failure or a 5xx: a blip is not
        # a model failure, and a person may be waiting on the difference.
        # A 4xx is deterministic and is never retried -- doubling load on a
        # server that already said no is how a brownout becomes an outage.
        last_error = None
        for attempt in (1, 2):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    reply = json.load(response)
                try:
                    return reply["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise ModelUnconfigured(
                        f"the model endpoint answered without a completion: "
                        f"{str(reply)[:120]}") from exc
            except urllib.error.HTTPError as exc:
                if exc.code < 500:
                    raise
                last_error = exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
            if attempt == 1:
                time.sleep(0.5)
        raise last_error

    if os.environ.get("ANTHROPIC_API_KEY"):
        if _boundary_present():
            raise ModelUnconfigured(
                "this build carries a data boundary, so the hosted model is "
                "refused -- point LLM_ENDPOINT at a model inside it"
            )
        try:
            import anthropic
        except ImportError as exc:
            raise ModelUnconfigured(
                "the hosted path needs the anthropic package -- "
                "`pip install anthropic` -- or set LLM_ENDPOINT to a local "
                "OpenAI-compatible server instead"
            ) from exc

        response = anthropic.Anthropic().messages.create(
            model=os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    raise ModelUnconfigured(
        "no model is configured -- set LLM_ENDPOINT to an OpenAI-compatible "
        "local server (vLLM or Ollama), or ANTHROPIC_API_KEY where the "
        "boundary allows it"
    )
