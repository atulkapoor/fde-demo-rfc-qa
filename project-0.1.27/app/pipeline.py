"""The order things run in.

Ordered by phase -- what reads text before what chunks it, what
indexes before what queries, nothing outward before reasoning has
decided -- so when an answer is wrong there is somewhere to look.
Approval gates and critics run first on the request path: they pass
everything that is not an action, and refuse an action before anything
costs money. Removing one is a visible diff, not an oversight.

Only payload-transforming components are chained here. Deployment,
provisioning, evaluation, serving and their kin are decided and
emitted, but a service unit is not a step a payload passes through.

Every step reads and writes one envelope (app/shapes.py). run()
normalises the caller's raw input into it and returns the OUTPUT --
what output() picks from the finished envelope -- so the evaluation
harness and the HTTP edge hand over, and get back, the same things.
"""

import json
import os
import sys
from pathlib import Path

from app import boundary  # noqa: F401 -- placement checked at import
from app.components import (
    perception,
    reasoning,
    representation,
    retrieval,
)
from app.contract import RefusedInput
from app.shapes import envelope

# Runs once per corpus, not once per request: read, chunk, index.
INGEST_STEPS = [
    ('perception', perception.Perception()),
    ('representation', representation.Representation()),
]

# One retriever, wired once: the ingest path fills it and the
# query path reads it. evals/retrieval.py measures this instance,
# never a fresh empty one.
RETRIEVER = retrieval.Retrieval()

# The request path.
STEPS = [
    ('retrieval', RETRIEVER),
    ('reasoning', reasoning.Reasoning()),
]


def _run_steps(steps, payload: dict) -> dict:
    for name, step in steps:
        try:
            payload = step.run(payload)
        except RefusedInput:
            raise
        except Exception:
            sys.stderr.write(json.dumps({"failed_step": name,
                                         "request_id": payload.get("request_id")})
                             + "\n")
            sys.stderr.flush()
            raise
    return payload


def ingest(documents: list[dict]) -> int:
    """Read, chunk and index a batch of documents into the wired retriever.
    Returns how many units the index now holds for them."""
    index = getattr(RETRIEVER, "index", None)
    if index is None:
        raise NotImplementedError(
            "this retriever is fed by its own ingest job; see its module docstring")
    payload = _run_steps(INGEST_STEPS, {"documents": documents})
    units = payload.get("chunks") or payload.get("records") or []
    # A chunk remembers its document: recall is graded per document, and a
    # hit on any chunk of it counts.
    index([{"id": u["id"], "text": u["text"], "source": u.get("source", u["id"])}
           for u in units])
    return len(units)


# What the last load_corpus() read, and what it could not.
LOADED: dict = {"documents": 0, "skipped": [], "refused": None}


def load_corpus(directory: str | None = None) -> int:
    """Ingest every document under CORPUS_DIR (or the given directory):
    .txt/.md files as one document each, .json as a list of {id, text},
    .jsonl as one {id, text} per line. Returns the document count; zero
    means the service has nothing to answer from, and /ready says so."""
    root = directory or os.environ.get("CORPUS_DIR")
    LOADED.update({"documents": 0, "skipped": [], "refused": None})
    if not root or not Path(root).is_dir():
        return 0
    documents = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix in (".txt", ".md"):
                documents.append({"id": str(path.relative_to(root)),
                                  "text": path.read_text(encoding="utf-8")})
            elif suffix == ".json":
                documents.extend(json.loads(path.read_text(encoding="utf-8")))
            elif suffix == ".jsonl":
                # Line by line: one torn record must not take the other
                # hundred thousand with it. Bad lines are counted, kept out.
                bad = 0
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        documents.append(json.loads(line))
                    except ValueError:
                        bad += 1
                if bad:
                    LOADED["skipped"].append({"file": str(path.relative_to(root)),
                                              "reason": f"{bad} malformed line(s) skipped"})
            else:
                # Not silently: a corpus that read a quarter of its files
                # answers confidently from a quarter of the truth.
                LOADED["skipped"].append({"file": str(path.relative_to(root)),
                                          "reason": f"unsupported type {suffix or '(none)'}"})
        except (OSError, ValueError) as exc:
            # One unreadable file must not crash-loop the service; it is
            # named in the boot log and counted in /ready.
            LOADED["skipped"].append({"file": str(path.relative_to(root)),
                                      "reason": f"{type(exc).__name__}: {str(exc)[:120]}"})
    # The lexical index costs between five and twenty-five megabytes of
    # memory per megabyte of corpus text, by vocabulary (measured both
    # ends). A corpus over the sized ceiling is refused with a line, not
    # killed by the cgroup before the socket opens. Raise CORPUS_MAX_MB
    # together with MemoryMax in the unit.
    ceiling = float(os.environ.get("CORPUS_MAX_MB", "80"))
    size_mb = sum(len(d.get("text", "")) for d in documents if isinstance(d, dict)) / 1e6
    if size_mb > ceiling:
        LOADED["refused"] = (f"corpus is {size_mb:.0f} MB of text; CORPUS_MAX_MB is "
                             f"{ceiling:.0f} (up to {ceiling * 25:.0f} MB of memory)")
        return 0
    ingested = 0
    for document in documents:
        try:
            ingest([document])
            ingested += 1
        except Exception as exc:  # noqa: BLE001 -- named, counted, not fatal
            # A record that is not even an object has no id to name.
            label = (document.get("id") if isinstance(document, dict)
                     else f"record {type(document).__name__}")
            LOADED["skipped"].append({"file": str(label),
                                      "reason": f"{type(exc).__name__}: {str(exc)[:120]}"})
    LOADED["documents"] = ingested
    return ingested


def output(payload: dict) -> object:
    """What a caller gets back: the answer, the decision, the mapped
    record, the plan -- whichever this system produces -- never the
    whole envelope with the principal and the raw input inside it.
    The evaluation harness compares THIS against each case's output.
    """
    for key in ("answer", "decision", "plan", "integration"):
        if key in payload:
            return payload[key]
    records = payload.get("records")
    if isinstance(records, list) and records and "mapped" in records[0]:
        if len(records) == 1:
            return records[0]["mapped"]
        return [r["mapped"] for r in records]
    if "retrieved" in payload:
        return payload["retrieved"]
    return {k: v for k, v in payload.items()
            if k not in ("request_id", "principal", "input")}


def run_envelope(raw: object, *, request_id: str | None = None,
                 principal: dict | None = None) -> dict:
    """The whole envelope after every step -- for tests and diagnosis."""
    payload = envelope(raw)
    payload["request_id"] = request_id or "local"
    payload["principal"] = principal or {"subject": "anonymous", "scopes": []}
    return _run_steps(STEPS, payload)


def run(raw: object, *, request_id: str | None = None,
        principal: dict | None = None) -> object:
    """One request through the payload path, answered.

    Exceptions propagate unchanged -- the edge maps their types to
    status codes -- but a failing step's name and the request id
    reach the journal first, so no traceback is anonymous. A refusal
    is an answer, not a failure, and passes through untouched.
    """
    return output(run_envelope(raw, request_id=request_id, principal=principal))


if __name__ == "__main__":
    from app.service import main

    raise SystemExit(main())
