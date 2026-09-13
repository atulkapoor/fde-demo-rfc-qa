#!/usr/bin/env python3
"""Measure the retrieval layer alone. Exits non-zero on an empty case set,
an erroring retriever, or recall below the threshold -- so CI can gate on it.

The embedding and index choices set a ceiling on everything downstream: no
reranking, prompting or model upgrade recovers a document that was never
retrieved. End-to-end scores blur that ceiling into "quality"; this number is
the ceiling by itself. When a failing case's answer is missing from the
evidence, this -- not the prompt -- is the layer to fix (ops/diagnosis.md
walks the order).

Cases live in retrieval_cases.jsonl beside this file, one JSON object per
line:

    {"id": "case-1", "query": "...", "relevant": ["doc-7", "doc-12"]}

`relevant` lists the document ids a correct top-K must surface; recall@K is
the share of them that did. Seed cases from the engagement's own golden
queries -- the ones the eval owner would grade -- never from a benchmark.
"""

import argparse
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HERE = Path(__file__).parent
KS = (10, 50)


def load_cases():
    path = HERE / "retrieval_cases.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def resolve_retriever():
    """The deployed retriever, whatever shape its realization took.

    A module-level *instance* wins over everything: deployments wire state
    (an index, a connection) into an instance once, and constructing a fresh
    one here would measure an empty retriever and blame the index. Then a
    module-level run(query, top_k=...), then a class constructed once as the
    last resort. Wiring problems surface as the retriever's own refusal,
    which is the correct failure: an eval that silently skipped an unwired
    store would grade a system that cannot retrieve as though it could.
    """
    from app.components import retrieval as mod

    for name in sorted(vars(mod)):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if isinstance(obj, (type, types.ModuleType, types.FunctionType)):
            continue
        if callable(getattr(obj, "retrieve", None)):
            return lambda query, k, _r=obj: _r.retrieve(query, k)
        if callable(getattr(obj, "run", None)):
            return lambda query, k, _r=obj: _r.run(query, top_k=k)
    run = getattr(mod, "run", None)
    if callable(run) and not isinstance(run, type):
        return lambda query, k: run(query, top_k=k)
    for name in sorted(dir(mod)):
        obj = getattr(mod, name)
        if isinstance(obj, type):
            if callable(getattr(obj, "retrieve", None)):
                instance = obj()
                return lambda query, k, _r=instance: _r.retrieve(query, k)
            if callable(getattr(obj, "run", None)):
                instance = obj()
                return lambda query, k, _r=instance: _r.run(query, top_k=k)
    raise SystemExit(
        "no retriever found in app/components/retrieval.py -- expected a "
        "wired module-level instance, a run(query, top_k=...) function, or "
        "a class with retrieve() or run()"
    )


def surfaced_ids(result):
    """Ids from a ranked result list, or None when the shape is not one.

    None is an error, not a zero: a retriever returning a dict, or a list
    with no id-bearing entries, is mis-wired -- scoring it 0 would dilute
    the mean and keep CI green over a measurement that never happened.
    """
    if not isinstance(result, list):
        return None
    ids = [str(r.get("id")) for r in result if isinstance(r, dict) and "id" in r]
    if result and not ids:
        return None
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-recall", type=float, default=0.0,
                        help="fail below this mean recall@%d" % KS[0])
    args = parser.parse_args()

    cases = load_cases()
    if not cases:
        print("retrieval_cases.jsonl is empty -- nothing was measured, so "
              "nothing passed. Seed it with golden queries and the document "
              "ids a correct top-K must surface.", file=sys.stderr)
        return 1

    retrieve = resolve_retriever()
    errors = 0
    recalls = {k: [] for k in KS}
    misses = []
    for case in cases:
        raw = case.get("relevant")
        if not isinstance(raw, list) or not raw:
            errors += 1
            misses.append({"id": case.get("id"),
                           "note": "relevant must be a non-empty list of ids"})
            continue
        # Deduplicated: a repeated id is one document, and counting it twice
        # inflates recall for the cases that need scrutiny most.
        relevant = sorted({str(r) for r in raw})
        try:
            got = surfaced_ids(retrieve(case["query"], max(KS)))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            misses.append({"id": case.get("id"), "note": f"retriever errored: {exc}"})
            continue
        if got is None:
            errors += 1
            misses.append({"id": case.get("id"),
                           "note": "retriever returned no id-bearing result list"})
            continue
        for k in KS:
            top = set(got[:k])
            recalls[k].append(sum(1 for r in relevant if r in top) / len(relevant))
        absent = [r for r in relevant if r not in set(got[: max(KS)])]
        if absent:
            misses.append({"id": case.get("id"), "missing": absent})

    for k in KS:
        scored = recalls[k]
        mean = sum(scored) / len(scored) if scored else 0.0
        print(f"  recall@{k:<3} {len(scored):>4} cases  {mean:.1%}")
    for miss in misses[:10]:
        print(f"    {miss}", file=sys.stderr)

    if errors:
        print(f"{errors} case(s) errored -- the retriever is not wired end "
              f"to end yet", file=sys.stderr)
        return 1
    gate = recalls[KS[0]]
    mean = sum(gate) / len(gate) if gate else 0.0
    if mean <= 0:
        print("nothing relevant surfaced for any case. Look at the retrieval "
              "layer -- the index, the query handling, and the embedding "
              "model where one exists -- before anything downstream.",
              file=sys.stderr)
        return 1
    if mean < args.min_recall:
        print(f"recall@{KS[0]} below {args.min_recall:.1%} -- fix retrieval "
              f"before touching prompts or models: nothing downstream "
              f"recovers a document that never surfaced", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
