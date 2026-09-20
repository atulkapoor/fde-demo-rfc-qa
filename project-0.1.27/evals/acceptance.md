# Acceptance

Offline evaluation says the system matches its examples. This protocol says whether the people who live with the output accept it. Run it before production traffic, with the client in the room.

## Protocol

1. **Who judges**: the named evaluation owner (the client_readiness gate holds their name) -- the client_readiness gate is part of the engagement record that produced this project, not of this project -- plus at least one person who does the work today. Not the builder.
2. **Sample**: fresh items from live data -- never the golden set (the system has seen those 12 in CI). Size to match the golden set or 30, whichever is larger.
3. **Blind pass**: the judges label the sample before seeing the system's output; disagreement between judges is recorded, not resolved by the loudest voice.
4. **Compare**: system output against the blind labels, scored by the same metrics the harness runs -- for a decision task that is per-class precision and recall against the majority rate, never accuracy alone. Two judges who disagree on a case have found a specification question; it is recorded, and it blocks sign-off until the client answers it. The baseline's error rate is the number to beat -- beating zero was never the bar.
5. **Sign-off**: recorded with names and the score. A meeting that went well is not a sign-off.

## Exam record

Split seed 0, holdout share 0.3; `evals/manifest.json` carries the same record for tools.

- `golden.jsonl`: 12 cases, sha256 `902e9f59bf6901cd`
- `edge_case.jsonl`: 7 cases, sha256 `cd0e40f1e8cf1c35`
- `adversarial.jsonl`: 11 cases, sha256 `92fe83a07ddd954a`
- holdout: 10 cases, sha256 `7351789448b2f95e` -- kept with the engagement, never shipped; fde implement --holdout must be given the file with this digest

## Refusals worth respecting

If nobody can be found to judge, that is the client_readiness gate failing late -- stop and escalate rather than accepting on their behalf.

## Case schema

Every eval file (`golden.jsonl`, `edge_case.jsonl`, `adversarial.jsonl`, and any holdout) is JSON lines, one case per line:

```json
{"id": "g-1", "input": <what the pipeline receives>, "output": <the reference answer>}
{"id": "adv-1", "input": <a forbidden probe>, "expect_refusal": true}
```

`input` is handed to `app.pipeline.run` unchanged. A case with `expect_refusal` is correct only when the pipeline raises `RefusedInput`; a confident output is the failure the probe exists to catch. For structured outputs a case is correct only when every field matches; the harness names the fields that missed. (`expect` is accepted as a legacy alias of `output`.)

## Judge calibration

This evaluation is judged by a model. No judged number is quoted before the judge agrees with a human grader on at least 20 hand-graded cases at the bar `evals/calibrate.py` sets -- the harness prints every judged run as UNCALIBRATED until that has passed, and red once it has failed.
