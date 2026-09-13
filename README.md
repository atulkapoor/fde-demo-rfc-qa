# fde-demo-rfc-qa

The third complete engagement through
[fde-framework](https://github.com/atulkapoor/fde-framework): freeform
question-answering over 58 real IETF RFCs — the shape that needs a model at
runtime and a judge at evaluation time. Which makes this the demo where the
framework's most-quoted doctrine got measured:

> *An uncalibrated judge is a random number generator with a monthly bill.*

Measured first-party: a random-ish number generator **with a +26-point
house bias**.

## The run, in numbers

| Stage | Result |
|---|---|
| Corpus | 58 RFCs (8.1MB) fetched from rfc-editor.org — the "internal standards corpus" |
| The exam authored with receipts | 38 QA pairs, each carrying an evidence pattern that must match its source RFC or the pair is rejected — 2 were, by their own check. `verified: true` is earned, not asserted |
| Gates | Real rows (sqlite, 58 full documents); the offline-evaluability waiver carries a **falsifiable prediction**: *"local judge qwen3:0.6b… published prediction: it fails the bar (SLMJury 67.9%)"* |
| Architecture | on-prem; keyword-search retrieval, `llm` reasoning through the boundary-gated endpoint, judged evaluation |
| Retrieval, measured | **recall@10 = 100%** across 28 real queries — the emitted `evals/retrieval.py`'s first real-data outing |
| Implement | Round 2 green, holdout included — *per the uncalibrated judge* |
| **The calibration verdict** | Judge vs. hand grades on 19 cases: **73.7% agreement — refused** (bar 0.80). Every disagreement was judge leniency: it blessed PTR as the alias record, max-stale as the freshness directive, a 60-bit IPv6 address. Zero false negatives, five false positives |
| The corrected score | Judge claimed **89.5%**; hand-graded truth: **63.2%**. The loop's green was 26 points of flattery, and the calibration gate — run before quoting anything — caught it |

The prediction on record was confirmed in direction (67.9% published,
73.7% measured, both below any honest bar) — written into `RISKS.md`
*before* the measurement, per-case grades in
[`calibration-verdict.jsonl`](calibration-verdict.jsonl).

## Deployed and answering

The emitted service (fde-framework 0.1.11), run as its systemd unit would,
with the local model behind it:

```
$ curl -s http://127.0.0.1:8092/health
{"status": "ok"}

$ curl -s -X POST :8092/ -d '"Which HTTP status code says a resource has moved permanently?"'
{"result": "The HTTP status code that indicates a resource has moved
permanently is 301 and 308. ..."}
```

## What this demo settles

1. **The judged green is not a number until the judge is calibrated.**
   This run produced a green loop and then refused its own green — that
   ordering is the product.
2. **A 0.6B judge is disqualified for judging**, first-party, replicating
   the published benchmark's direction. (The same model *maxed* the
   extraction exam in [demo #1](https://github.com/atulkapoor/fde-demo-receipts)
   — task fit, not model size, is the variable.)
3. **The retrieval layer can be measured with no model in the loop** —
   and on distinctive queries over a small corpus, keyword search is
   simply done: 100% recall@10.

## Reproduce it

```bash
python3 prepare.py                    # fetches the RFCs, rebuilds the corpus store
python3.12 -m venv venv && venv/bin/pip install "fde-framework>=0.1.11"
venv/bin/fde start rfcqa --statement "Answer engineers' protocol questions in plain prose from the internal standards corpus; 58 documents; data cannot leave; nobody is waiting, answers land in a review queue; engineers look up one standard at a time as plain text questions."
venv/bin/fde samples rfcqa --file pairs.jsonl
venv/bin/fde next rfcqa               # and keep doing what it says
venv/bin/fde build rfcqa --out project
cp retrieval_cases.jsonl project/evals/
LLM_ENDPOINT=http://localhost:11434 LLM_MODEL=qwen3:0.6b \
  venv/bin/fde implement project --holdout holdout.jsonl \
  --max-rounds 6 --agent-timeout 10800 --check "python evals/harness.py --min-score 0.6"
```

The exam (`pairs.jsonl`, `holdout.jsonl`, `retrieval_cases.jsonl`) is
committed — the questions and answers are authored for this demo and
machine-verified against the RFC texts (`authored-verified.json` carries
the evidence patterns). The corpus itself regenerates from rfc-editor.org.

## Honesty notes

- The calibration hand-grades are one grader (the demo's eval owner),
  n=19, grades and reasons published per-case. The references they grade
  against were machine-verified against RFC text at authoring time.
- Operational baseline figures are a stated scenario, labelled as such.
- The framework's status stays **built, demonstrated, unproven** — three
  public runs on real data are still not a client production engagement.
