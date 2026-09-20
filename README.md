# fde-demo-rfc-qa

> **The deliverable is in this repo**: [`project/`](project/) — the emitted, implemented, deployable output (pipeline service, deploy assets, runbooks, evals, ARCHITECTURE.md, RISKS.md). Start at [`project/README.md`](project/README.md).

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

The service entrypoint (built on 0.1.10 hours before 0.1.11 released;
the 0.1.11 entrypoint backported rather than rebuilding over the measured
run), run as its systemd unit would,
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

## Rebuilt on the 0.1.27 emitter (2026-09-20)

The framework has changed shape since this demo ran on 0.1.11 -- an HTTP
edge, a boundary, a ledger, a scorecard -- so the same recorded engagement
was built again as [`project-0.1.27/`](project-0.1.27/) and scored with
`fde scorecard project-0.1.27 --holdout ...` through a local Ollama: the
author `qwen3:0.6b`, the judge `dolphin-mistral`, a different model so the
author does not grade itself. No agent has touched this build; it is what
the framework emits from the recorded facts and the 28 authored pairs.

**16 of 23 measured properties hold**, and the seven that do not are the
honest state of a judged freeform exam this small:

| Row | Measured |
|---|---|
| Golden, 12 cases | 58.3% |
| Holdout, 10 cases never shipped | 30.0%; the card's sample floor is 30, so the row does not hold on size alone |
| Judge calibration | none on record: the hand-graded set has 19 cases and the protocol's floor is 20, so every judged number above is marked not quotable |
| Generalisation gap | 28 points |
| Beats the baseline error rate | no: the stated baseline records 4% first-pass error, a 96% bar, on a 30% holdout |
| Adversarial probes | 5 of 11, three failures attributed to misread bases, none followed |
| Edge, valid request, the answer says why | hold: the edge refuses forged identities and results, answers a real question from the corpus, and cites what it stood on |

The reading: a 28-pair exam over 58 RFCs with a 0.6-billion-parameter
author and an uncalibrated judge cannot support a claim, and the card
says so on four rows rather than averaging them away. What this rebuild
adds over the 0.1.11 run is the machinery around the number: the exam
record with every digest, the boot refusals, the request contract, and a
card that refuses to count a 19-case calibration or a 10-case holdout as
proof. The retrieval layer's own measurement (100% recall@10 on the
authored queries) is unchanged; `retrieval_cases.jsonl` ships in the
build's evals.

## Where it stands (fde 0.1.28)

`fde stage` computes the engagement's stage off the record -- never declared --
and appended the first transition to
[`engagements/rfcqa/lifecycle.jsonl`](engagements/rfcqa/lifecycle.jsonl):

```
rfcqa: prototype

  ok discovery
       ok a problem statement: Answer engineers' protocol questions in plain prose from the internal standards ...
  ok validation
       ok the gates pass or are waived on the record: all pass
       ok the exam is seeded from the client's pairs: 28 pairs
       ok a holdout the delivery never ships: 10 cases
       ok data access attested: sqlite standards.db returned 58 real documents (8.1MB, full text)
  ok prototype
       ok a build with its exam record: project-0.1.27
  -- pilot
       ok a scorecard on record: scorecard.json
       NO the out-of-sample rows hold: 30.0% on 10 cases
       ok the edge answers a valid request: 200 "The maximum length of a single DNS label is 63 octets, as s
  -- production
       NO a deployment on record: none: fde deployed <eng> --note
       ok no open incident: none open
  -- adoption
       NO an adoption figure measured in the field: none: fde outcome <eng> --metric adoption=<share>
  -- retrospective
       NO a retrospective captured as a case: none: fde retro

to reach pilot: the out-of-sample rows hold -- 30.0% on 10 cases

recorded: start -> prototype (lifecycle.jsonl)
```

The record stops at prototype because the scorecard's out-of-sample row does not hold: 30.0% on 10 holdout cases, judged by a local model the calibration gate refused (19 graded pairs against a floor of 20). The stage is computed off that row, so an uncalibrated judge keeps the engagement out of pilot rather than letting a judged number carry it there.

On 0.1.31 the eighth gate, the outcome contract (who owns the number the
system exists to move, its value today, its target, how it is measured, by
when), is waived on this record with the reason where a reader will find
it: no client owns an outcome in a public demonstration, and nobody has set
a target. `fde debt engagements/rfcqa` ([`debt.txt`](debt.txt)) lists what
the engagement rests on that nobody has settled: 10 items: two environment facts said and never measured, three roles never heard, two standing waivers (the judge's calibration and the outcome contract), and three entries with nobody's name on them. None blocks the
build or production; the waivers age from today.

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
- The committed `app/llm.py` sends no max-token cap — the receipts demo's
  sibling caps at 256 after measuring the cost of an uncapped local model.
  Left as measured here; the framework's emitted default gains the cap.
- The framework's status stays **built, demonstrated, unproven** — three
  public runs on real data are still not a client production engagement.
