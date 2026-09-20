#!/usr/bin/env python3
"""Calibrate the judge against a human before any judged number is quoted.

A judged evaluation's score is only as honest as the judge, and a local
judge at small-model scale can flatter a system by twenty points and more
(measured first-party). So the protocol is:

1. Run the pipeline over at least MIN_CASES golden inputs and keep what it
   answered.
2. A human -- the evaluation owner, not the builder -- grades each candidate
   against its reference as correct / partial / incorrect.
3. Record the grades as JSON lines in evals/judge-calibration.jsonl:

   {"id": "g-7", "output": <reference>, "candidate": <what the system said>,
    "human": "correct"}

4. Run this script. It asks the judge to grade the same candidates and
   reports agreement. Below the bar, the judge is REFUSED: the harness
   marks every judged run red until this passes, because a score from a
   judge that disagrees with the human a quarter of the time is not a
   measurement.

An uncalibrated judge is a random number generator with a monthly bill.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    # This script sends the client's references and the system's answers
    # to a judge; the boundary decides where that judge may be.
    import app.boundary  # noqa: E402, F401
except ImportError:
    pass  # no boundary in this build
except RuntimeError as refusal:
    print(f"refused by the boundary: {refusal}", file=sys.stderr)
    raise SystemExit(78) from None

from evals.harness import VERDICTS, judge_score  # noqa: E402

HERE = Path(__file__).parent
GRADES = HERE / "judge-calibration.jsonl"
RESULT = HERE / "judge-calibration.json"
BAR = 0.8
# Fewer cases cannot tell a judge from a coin with any confidence.
MIN_CASES = 20


def main():
    if not GRADES.exists():
        print(f"no hand grades at {GRADES.name}; see the protocol at the top "
              f"of this file", file=sys.stderr)
        return 1
    rows = [json.loads(line) for line in GRADES.read_text().splitlines()
            if line.strip()]
    bad = [r for r in rows if r.get("human") not in VERDICTS]
    if bad:
        print(f"{len(bad)} row(s) carry a grade outside "
              f"{sorted(VERDICTS)}", file=sys.stderr)
        return 1
    if len(rows) < MIN_CASES:
        print(f"{len(rows)} graded cases; {MIN_CASES} is the floor", file=sys.stderr)
        return 1

    cases, lenient, harsh = [], 0, 0
    for row in rows:
        human = VERDICTS[row["human"]]
        judge = judge_score(row.get("candidate"), row.get("output"))
        lenient += judge > human
        harsh += judge < human
        cases.append({"id": row.get("id"), "human": row["human"],
                      "judge": judge, "agree": judge == human})
    agreement = sum(c["agree"] for c in cases) / len(cases)
    passed = agreement >= BAR
    RESULT.write_text(json.dumps({
        "n": len(cases), "agreement": agreement, "bar": BAR, "passed": passed,
        "lenient": lenient, "harsh": harsh, "cases": cases,
    }, indent=2) + "\n")
    print(f"judge agreement with the human grader: {agreement:.1%} on "
          f"{len(cases)} cases -- {'passed' if passed else 'REFUSED'} "
          f"(bar {BAR:.0%})")
    print(f"  disagreements: {lenient} where the judge was more lenient than "
          f"the human, {harsh} where it was harsher")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
