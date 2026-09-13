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
import urllib.request


class ModelUnconfigured(RuntimeError):
    """No model is reachable; nothing here guesses instead."""


def _boundary_present() -> bool:
    try:
        import app.boundary  # noqa: F401
    except ImportError:
        return False
    return True


def complete(prompt: str, timeout: float = 120.0) -> str:
    endpoint = os.environ.get("LLM_ENDPOINT")
    if endpoint:
        body = json.dumps({
            "model": os.environ.get("LLM_MODEL", "default"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }).encode()
        request = urllib.request.Request(
            endpoint.rstrip("/") + "/v1/chat/completions",
            data=body, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)["choices"][0]["message"]["content"]

    if os.environ.get("ANTHROPIC_API_KEY"):
        if _boundary_present():
            raise ModelUnconfigured(
                "this build carries a data boundary, so the hosted model is "
                "refused -- point LLM_ENDPOINT at a model inside it"
            )
        import anthropic

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
