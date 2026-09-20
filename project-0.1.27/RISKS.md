# Risks accepted

## Decided, emitted, not on the payload path

These components were decided and their modules are emitted, but the request path does not run them: the edge's structured log is the observability that runs, the ledger is the audit that runs, the unit is the deployment. Each module says so in its first lines. Wire one in, or leave it as the reference it is -- but do not read its presence as running code.

- `deployment`
- `evaluation`
- `governance`
- `observability`
- `provisioning`
- `serving`

## Facts this design stands on

The governance, the boundary and the topology follow from these values. A value learned from a person or inferred is asserted, not established -- confirm it with the client before the decision that rests on it stands.

- `data_residency = cannot_leave` -- artifact
- `hosting = on-prem` -- interview -- asserted, not established: confirm before the decisions resting on it stand

## Unanswered assumptions

Decisions were made without these facts. Each is a risk until somebody answers it (`fde ask`, or the interview), and the answer may change a decision.

- cheap_path_coverage: not stated, so nothing was decided on it
- confidence_calibrated: not stated, so nothing was decided on it
- container_competence: not stated, so nothing was decided on it
- existing_cluster: not stated, so nothing was decided on it
- external_systems: not stated, so nothing was decided on it
- interpretability_required: not stated, so nothing was decided on it
- labelled_count: not stated, so nothing was decided on it
- latency_budget_ms: not stated, so nothing was decided on it
- provisioning_api: not stated, so nothing was decided on it
- sensitivity_present: not stated, so nothing was decided on it

## Gates waived

Each was blocking at build time. Somebody decided to proceed anyway, and this is who said what.

- **offline_evaluability** (2026-09-13) -- local judge qwen3:0.6b on Ollama; calibration against the eval owner's hand grades runs BEFORE any judged number is quoted -- published prediction: it fails the bar (SLMJury 67.9%)
  - covered: Freeform output needs a judge, and nothing may leave here.

