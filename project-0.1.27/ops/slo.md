# Service objectives

Two buckets, because reporting one is half a story. A technical number nobody outside the team cares about, and a business number nobody inside it can move directly -- and a system healthy on the first while the second does not move is a system nobody will renew.

## Technical

- **Latency** — p95 under <not stated>ms at expected peak. Measured at the edge, not inside a component, because that is where somebody experiences it.
- **Availability** — business hours: planned windows outside them are free.
- **Evaluation score** — the golden layer at or above the threshold CI gates on. A drop here is a regression whether or not anything is down.
- **Adversarial score** — tracked separately and never averaged in. Scoring well on golden and badly on adversarial means nobody has attacked it yet.

## Business

- **The thing that should move** — stated by whoever asked for this, in their words, before it was built. If nobody can say what should change, that is the finding.

## Baseline

**Captured.** The numbers to beat, by their recorded definitions:

- **volume** — 1100 questions/month (protocol questions in the review queue (demo scenario, labelled simulated in the demo README)) — **stated, not measured**
- **cycle_time_per_unit_seconds** — 840 s (question to accepted answer, searching standards by hand (scenario)) — **stated, not measured**
- **labour_hours_per_week** — 12 h/week (senior engineers answering standards questions (scenario)) — **stated, not measured**
- **rework_rate** — 0.1 ratio (answers corrected after a spec was misread (scenario)) — **stated, not measured**
- **exception_rate** — 0.18 ratio (questions escalated to the standards owner (scenario)) — **stated, not measured**
- **error_rate** — 0.04 ratio (answers contradicting the spec text (scenario)) — **stated, not measured**
- **business_metric** — 9 hours (mean time to an accepted answer (scenario)) — **stated, not measured**

7 of these figures are stated rather than measured. The acceptance protocol's bar is the measured error rate; capture it by the same definition before quoting a delta.
- sampled: n=38, demo engagement on public RFCs; operational figures a stated scenario, answer ground truth machine-verified against the spec text

Re-measure by identical definitions in 60 days. A comparison that quietly changes a definition is a comparison with its thumb on the scale.
