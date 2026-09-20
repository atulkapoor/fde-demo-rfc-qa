"""One envelope, every step.

Every step reads the keys it needs from this dict, writes the keys it
produces, and returns the SAME envelope (`{**payload, ...}`) -- never a
fresh one. A step that needs a key the envelope lacks refuses with
RefusedInput at its own door, instead of a KeyError three steps later.

Two keys are reserved for the edge (app/service.py) and never taken
from a caller: `request_id`, which every log line and response carries,
and `principal`, the authenticated identity and scopes every outward
call is authorised against. Anything a client sends under those names
is refused by name, the same as a forged result.

Keys, by who writes them:

    edge            request_id, principal {subject, scopes}, input
    caller          documents [{id, text}], pages, query, goal, items,
                    capacity, tool, arguments, session, subject
    perception      records [{id, text, losses, usable}], clean_share
    representation  chunks [{id, source, start, end, text}]  (segmentation)
                    records [{id, mapped, unmapped, rejected}], mapped_share
    memory          memory [...]
    retrieval       retrieved [{id, text, rank}]
    planning        plan {...}
    reasoning       answer | decision, stopped_because, steps, cost, trace
    integration     integration {result, duplicate, key}
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from app.contract import RefusedInput

RESERVED = ("request_id", "principal")
# Control characters and zero-width marks carry no content and smuggle a
# lot: a NUL, a zero-width joiner inside an identifier, a BOM. Scrubbed
# from every string a caller sends, before any step reads it.
INVISIBLE = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b-\u200f\u2060\ufeff]"
)


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return INVISIBLE.sub("", value)
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    return value

# What a caller may send TO THIS BUILD -- generated from the components on
# its request path, so a key nothing here reads is refused by name rather
# than silently ignored (a caller once sent `documents` to a build that
# ingests at boot and got a confident answer from another corpus). A key
# a step WRITES (answer, decision, known, retrieved, ...) arriving from a
# caller is a forged result, not an input, and is refused the same way.
# Extend this tuple when the implementation grows a real input.
CALLER_KEYS = (
    'query',
    'goal',
    'k',
)
MAX_QUESTION_CHARS = 4000
# The same ceiling on every entry shape: a bare string, `text`, and each
# `documents[].text`. Capping one path once let a 900 KB narrative in by
# another.
MAX_TEXT_CHARS = MAX_QUESTION_CHARS * 8
MAX_K = 100


class Step(Protocol):
    def run(self, payload: dict[str, Any]) -> dict[str, Any]: ...


def envelope(raw: Any) -> dict[str, Any]:
    """The caller's input, normalised into the envelope.

    A string is a question, a goal and a one-document corpus at once;
    an object is taken as it is, minus the reserved keys. Anything else
    is refused: the pipeline never guesses what None was meant to be.
    """
    raw = _clean(raw)
    if isinstance(raw, dict):
        forged = sorted(k for k in raw if k in RESERVED)
        if forged:
            raise RefusedInput(
                f"{forged} are set by the edge, never by a caller"
            )
        body = dict(raw)
        unknown = sorted(k for k in body if k not in CALLER_KEYS)
        if unknown:
            raise RefusedInput(
                f"unknown keys {unknown}; the request contract is CALLER_KEYS "
                f"in app/shapes.py"
            )
        # Well-known keys carry well-known shapes, whatever this build reads:
        # a caller sending documents as a string is malformed everywhere.
        for key in ("documents", "pages", "items", "rows", "events"):
            if key in body and not isinstance(body[key], list):
                raise RefusedInput(f"{key!r} must be a list")
        for key in ("query", "goal", "text", "session", "subject", "tool"):
            if key in body and not isinstance(body[key], str):
                raise RefusedInput(f"{key!r} must be a string")
        for key in ("query", "goal"):
            if key in body and len(body[key]) > MAX_QUESTION_CHARS:
                raise RefusedInput(f"{key!r} is over {MAX_QUESTION_CHARS} characters")
        if "text" in body and len(body["text"]) > MAX_TEXT_CHARS:
            raise RefusedInput(f"'text' is over {MAX_TEXT_CHARS} characters")
        for position, document in enumerate(body.get("documents") or []):
            content = document.get("text") if isinstance(document, dict) else None
            if isinstance(content, str) and len(content) > MAX_TEXT_CHARS:
                raise RefusedInput(
                    f"documents[{position}].text is over {MAX_TEXT_CHARS} characters"
                )
        if "k" in body and (not isinstance(body["k"], int) or isinstance(body["k"], bool)
                            or not 1 <= body["k"] <= MAX_K):
            raise RefusedInput(f"'k' must be an integer in [1, {MAX_K}]")
        if "arguments" in body and not isinstance(body["arguments"], dict):
            raise RefusedInput("'arguments' must be an object")
        env: dict[str, Any] = {"input": raw, **body}
        # A goal is a question to a system that answers from evidence.
        if "goal" in body and "query" not in body:
            env["query"] = body["goal"]
        text = body.get("text")
        if isinstance(text, str) and "documents" not in body:
            env["documents"] = [{"id": str(body.get("id", "input")), "text": text}]
        if isinstance(text, str) and "query" not in body:
            env["query"] = text
        return env
    if isinstance(raw, str):
        if not raw.strip():
            raise RefusedInput("empty input")
        if len(raw) > MAX_TEXT_CHARS:
            raise RefusedInput(f"input is over {MAX_TEXT_CHARS} characters")
        return {
            "input": raw, "text": raw, "query": raw, "goal": raw,
            "documents": [{"id": "input", "text": raw}],
        }
    raise RefusedInput(
        f"input must be a JSON object or a string, not {type(raw).__name__}"
    )


def require(payload: dict[str, Any], key: str, kind: type | tuple[type, ...],
            *, non_empty: bool = False) -> Any:
    """The key a step needs, or a refusal that names it."""
    if key not in payload:
        raise RefusedInput(f"missing {key!r}")
    value = payload[key]
    if not isinstance(value, kind):
        wanted = getattr(kind, "__name__", str(kind))
        raise RefusedInput(f"{key!r} must be {wanted}, not {type(value).__name__}")
    if non_empty and not value:
        raise RefusedInput(f"{key!r} is empty")
    return value


def documents_of(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Documents as [{id, text}], refusing anything that is not."""
    documents = require(payload, "documents", list, non_empty=True)
    out = []
    for position, document in enumerate(documents):
        if not isinstance(document, dict) or not isinstance(document.get("text"), str):
            raise RefusedInput(f"documents[{position}] needs a string 'text'")
        out.append({**document, "id": str(document.get("id", position))})
    return out
