# rfcqa: decision brief

Written by `fde report` on 2026-10-12 from the record at `engagements/rfcqa`. Every figure below is read off that record; nothing here is estimated. Where a section quotes a command, it is what the command prints today, and running it again is the way to check.

## The problem as stated

The first statement, as the client put it.

> Answer engineers' protocol questions in plain prose from the internal standards corpus; 58 documents; data cannot leave; nobody is waiting, answers land in a review queue; engineers look up one standard at a time as plain text questions.

## Where the engagement stands

The stage is computed from the evidence on the record, not declared.

```text
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
       NO an adoption figure measured in the field: none: fde outcome <eng> --metric adoption=<value>
  -- retrospective
       NO a retrospective captured as a case: none: fde retro

to reach pilot: the out-of-sample rows hold -- 30.0% on 10 cases
```

## What the record knows, and who said it

Every fact carries its source. A fact learned from a person or inferred is asserted, not established; the gates below say which ones still need establishing.

```text
known (17)
  functional scope:
    input_format = text   [Atul Kapoor, admin]
    output_shape = freeform   [system]
    query_pattern = lookup   [system]
    recall_span = within_turn   [Atul Kapoor, admin]
  non-functional scope:
    access_model = single_operator   [Atul Kapoor, admin]
    availability_target = business_hours   [Atul Kapoor, admin]
    human_waiting = no   [system]
  data scope:
    arrival_rate = 30   [Atul Kapoor, admin]
    corpus_churn = static   [Atul Kapoor, admin]
    corpus_size = 58   [system]
    data_residency = cannot_leave   [system]
  environment:
    accelerator = none   [Atul Kapoor, admin]
    environment_lifetime = permanent   [Atul Kapoor, admin]
    existing_iac_tool = none   [Atul Kapoor, admin]
    hosting = on-prem   [Atul Kapoor, admin]
  operations:
    operates_after_handover = app_team   [Atul Kapoor, admin]
  commercial:
    licence_posture = internal_only   [Atul Kapoor, admin]
  still open -- data scope: labelled_count, sensitivity_present · environment: container_competence, existing_cluster, provisioning_api · functional scope: external_systems · non-functional scope: cheap_path_coverage, confidence_calibrated, interpretability_required, latency_budget_ms

68% of what gets decided is settled

waived (2)
  offline_evaluability: local judge qwen3:0.6b on Ollama; calibration against the eval owner's hand grades runs BEFORE any judged number is quoted -- published prediction: it fails the bar (SLMJury 67.9%)
  outcome_contract: no client owns an outcome: a public demonstration on IETF RFCs; the baseline's business metric is stated, and nobody has set a target
```

## The number this system exists to move

No outcome contract is on the record; it is the eighth gate.

`fde outcome-contract` records the owner, the metric, its value today, the target, the method and the window -- or a waiver saying why not yet.

## The design, with its reasons

What `fde architect` decides from the facts above, with the approach each component takes and why; what could not be decided is listed under the risks. A build writes this same page as ARCHITECTURE.md.

Topology: **on-prem**  
Fingerprint: `844710d44a78626f`

### Scope

**Functional scope**
- `input_format` = text
- `output_shape` = freeform
- `query_pattern` = lookup
- `recall_span` = within_turn

**Non-functional scope**
- `access_model` = single_operator
- `availability_target` = business_hours
- `human_waiting` = no

**Data scope**
- `arrival_rate` = 30
- `corpus_churn` = static
- `corpus_size` = 58
- `data_residency` = cannot_leave

**Environment**
- `accelerator` = none
- `environment_lifetime` = permanent
- `existing_iac_tool` = none
- `hosting` = on-prem

**Operations**
- `operates_after_handover` = app_team

**Commercial**
- `licence_posture` = internal_only

### Decisions

| Component | Approach | Implemented with | Why |
|---|---|---|---|
| deployment | systemd-unit (advisory: decided and emitted, not a payload step) | plain-python | Service unit: always |
| evaluation | judged (advisory: decided and emitted, not a payload step) | plain-python | Judged: output_shape == freeform |
| governance | boundary-and-audit (advisory: decided and emitted, not a payload step) | plain-python | Boundary and audit: data_residency == cannot_leave |
| observability | structured-logs (advisory: decided and emitted, not a payload step) | plain-python | Structured logs: always |
| perception | text-extraction | plain-python | Text extraction: input_format == text |
| provisioning | manual-runbook (advisory: decided and emitted, not a payload step) | plain-python | Written steps: always |
| reasoning | llm | plain-python | Prompted model: output_shape == freeform |
| representation | segmentation | plain-python | Segmentation: output_shape == freeform |
| retrieval | keyword-search | plain-python | Keyword search: query_pattern == lookup |
| serving | self-hosted (advisory: decided and emitted, not a payload step) | plain-python | Self-hosted: data_residency == cannot_leave; hosting == on-prem |

### Sizing the index

The lexical index costs between five and twenty-five megabytes of memory per megabyte of corpus text depending on vocabulary size (measured at both ends on the emitted realization; size from the top). The unit's `MemoryMax` and the env file's `CORPUS_MAX_MB` are one decision: at the shipped defaults (2G, 80 MB of text) the service refuses a larger corpus at boot with one line rather than dying to the OOM killer before its socket opens. This profile states `corpus_size = 58` documents; at a few kilobytes each that is near the ceiling -- size it, or move the postings to disk (SQLite FTS5, standard library) which is a realization swap, not a redesign.

### Tools and libraries

| Component | Chosen | Licence | Alternatives in this topology |
|---|---|---|---|
| deployment | plain-python | PSF | -- |
| evaluation | plain-python | PSF | local-judge |
| governance | plain-python | PSF | -- |
| observability | plain-python | PSF | -- |
| perception | plain-python | PSF | -- |
| provisioning | plain-python | PSF | -- |
| reasoning | plain-python | PSF | -- |
| representation | plain-python | PSF | -- |
| retrieval | plain-python | PSF | -- |
| serving | plain-python | PSF | ollama, vllm |

Adopting an alternative the client already operates: `fde reuse <engagement> <stack>` and rebuild -- the architecture does not change, only the emitted code does.


### Rejected alternatives

What this design is not, and why. Usually the more useful half.

**deployment**
- `compose` -- nothing here matches container_competence == true -- unanswered: container_competence (an answer could admit it)
- `kubernetes-manifests` -- nothing here matches existing_cluster == true or external_systems > 2 -- unanswered: existing_cluster, external_systems (an answer could admit it)

**evaluation**
- `field-match` -- ruled out by output_shape == freeform
- `labelled-metrics` -- ruled out by output_shape == freeform

**governance**
- `audit-only` -- ruled out by data_residency == cannot_leave
- `role-scoped-authority` -- ruled out by access_model == single_operator

**observability**
- `traced` -- structured-logs is simpler and applies here

**perception**
- `ocr-pipeline` -- ruled out by input_format == text
- `passthrough` -- nothing here matches input_format == structured_data
- `speech-transcription` -- ruled out by input_format == text
- `video-ingestion` -- ruled out by input_format == text
- `windowed-ingestion` -- nothing here matches input_format == streams

**provisioning**
- `ansible-playbook` -- nothing here matches existing_iac_tool == ansible or provisioning_api == false -- unanswered: provisioning_api (an answer could admit it)
- `gitops` -- nothing here matches existing_cluster == true -- unanswered: existing_cluster (an answer could admit it)
- `terraform-module` -- nothing here matches provisioning_api == true or environment_lifetime == ephemeral -- unanswered: provisioning_api (an answer could admit it)

**reasoning**
- `cascade` -- nothing here matches confidence_calibrated == true and cheap_path_coverage < 0.95 -- unanswered: cheap_path_coverage, confidence_calibrated (an answer could admit it)
- `classical-ml` -- ruled out by output_shape == freeform
- `finetune` -- nothing here matches output_shape == freeform and labelled_count >= 1000 -- unanswered: labelled_count (an answer could admit it)
- `labelled-decision` -- nothing here matches output_shape == decision and input_format == text
- `optimisation-reasoning` -- ruled out by output_shape == freeform

**representation**
- `assisted-deterministic` -- nothing here matches output_shape == structured and cheap_path_coverage < 0.95 and interpretability_required == true or output_shape == decision and cheap_path_coverage < 0.95 -- unanswered: cheap_path_coverage, interpretability_required (an answer could admit it)
- `cascade` -- nothing here matches confidence_calibrated == true and cheap_path_coverage < 0.95 -- unanswered: cheap_path_coverage, confidence_calibrated (an answer could admit it)
- `classical-ml` -- ruled out by output_shape == freeform
- `deterministic` -- ruled out by output_shape == freeform
- `finetune` -- nothing here matches output_shape == freeform and labelled_count >= 1000 -- unanswered: labelled_count (an answer could admit it)
- `llm-extraction` -- nothing here matches output_shape == structured

**retrieval**
- `cascade` -- nothing here matches confidence_calibrated == true and cheap_path_coverage < 0.95 -- unanswered: cheap_path_coverage, confidence_calibrated (an answer could admit it)
- `graph-expanded-retrieval` -- ruled out by query_pattern == lookup
- `graph-retrieval` -- ruled out by query_pattern == lookup
- `hybrid-search` -- ruled out by corpus_size < 10000
- `reranked-retrieval` -- nothing here matches query_pattern == lookup and corpus_size > 200000 and human_waiting == "no"
- `vector-search` -- keyword-search is simpler and applies here

**serving**
- `managed-api` -- ruled out by data_residency == cannot_leave
- `serverless-gpu` -- ruled out by data_residency == cannot_leave

### Licences

Everything this design pulls in, so it can be checked before a legal team checks it.

- `plain-python`: PSF

## What the design rests on, and what was accepted

Waived gates, overridden recommendations, assumptions nobody has answered, and the facts the governance follows from. A build writes this same page as RISKS.md.

### Decided, emitted, not on the payload path

These components were decided and their modules are emitted, but the request path does not run them: the edge's structured log is the observability that runs, the ledger is the audit that runs, the unit is the deployment. Each module says so in its first lines. Wire one in, or leave it as the reference it is -- but do not read its presence as running code.

- `deployment`
- `evaluation`
- `governance`
- `observability`
- `provisioning`
- `serving`

### Facts this design stands on

The governance, the boundary and the topology follow from these values. A value learned from a person or inferred is asserted, not established -- confirm it with the client before the decision that rests on it stands.

- `data_residency = cannot_leave` -- artifact
- `hosting = on-prem` -- interview -- asserted, not established: confirm before the decisions resting on it stand

### Unanswered assumptions

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

### Gates waived

Each was blocking at build time. Somebody decided to proceed anyway, and this is who said what.

- **offline_evaluability** (2026-09-13) -- local judge qwen3:0.6b on Ollama; calibration against the eval owner's hand grades runs BEFORE any judged number is quoted -- published prediction: it fails the bar (SLMJury 67.9%)
  - covered: Freeform output needs a judge, and nothing may leave here.
- **outcome_contract** (2026-09-20) -- no client owns an outcome: a public demonstration on IETF RFCs; the baseline's business metric is stated, and nobody has set a target
  - covered: Nobody has agreed which number this system exists to move: no outcome contract was recorded.

## Decision debt

Everything the engagement rests on that nobody has settled, each with an owner and an age.

```text
rfcqa: decision debt as of 2026-10-12

  open (10)
    waiver         offline_evaluability: local judge qwen3:0.6b on Ollama; calibration against the eval owner's hand grades runs BEFORE any judged number is quoted -- published prediction: it fails the bar (SLMJury 67.9%)
                   owner: eval_owner  29 day(s)
                   next: meet the gate, or restate the waiver if it still holds
    waiver         outcome_contract: no client owns an outcome: a public demonstration on IETF RFCs; the baseline's business metric is stated, and nobody has set a target
                   owner: the author  22 day(s)
                   next: meet the gate, or restate the waiver if it still holds
    stated         accelerator = none: said by Atul Kapoor (admin), measurable but not measured
                   owner: admin
                   next: measure it: fde scan, or a document the client owns
    stated         existing_iac_tool = none: said by Atul Kapoor (admin), measurable but not measured
                   owner: admin
                   next: measure it: fde scan, or a document the client owns
    unsigned       data_access (2026-09-13)
                   owner: unsigned  29 day(s)
                   next: re-record with --by, or leave it and know it
    unsigned       security_review (2026-09-13)
                   owner: unsigned  29 day(s)
                   next: re-record with --by, or leave it and know it
    unsigned       waiver offline_evaluability (2026-09-13)
                   owner: unsigned  29 day(s)
                   next: re-record with --by, or leave it and know it
    unheard        sponsor has never been asked
                   owner: sponsor
                   next: fde ask <eng> --role sponsor
    unheard        user has never been asked
                   owner: user
                   next: fde ask <eng> --role user
    unheard        skeptic has never been asked
                   owner: skeptic
                   next: fde ask <eng> --role skeptic

10 item(s): 0 blocking the build, 0 blocking production, 0 older than 30 days, 3 unsigned
```

## What would stop this

The conditions on record under which the honest answer is to stop, judged against what has been measured so far.

```text
no stop conditions on record: fde stop-when <eng> --when "answered_accuracy < 0.88"
```

## The next decision

The single best next action judged from everything above, and what turns on it.

```text
next: fde scan engagements/rfcqa
  this build calls a model and LLM_ENDPOINT is not set -- scan names the runtime, the model sized to this hardware, and the export line
```
