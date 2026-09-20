# Architecture

Topology: **on-prem**  
Fingerprint: `844710d44a78626f`

## Scope

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

## Decisions

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

## Sizing the index

The lexical index costs between five and twenty-five megabytes of memory per megabyte of corpus text depending on vocabulary size (measured at both ends on the emitted realization; size from the top). The unit's `MemoryMax` and the env file's `CORPUS_MAX_MB` are one decision: at the shipped defaults (2G, 80 MB of text) the service refuses a larger corpus at boot with one line rather than dying to the OOM killer before its socket opens. This profile states `corpus_size = 58` documents; at a few kilobytes each that is near the ceiling -- size it, or move the postings to disk (SQLite FTS5, standard library) which is a realization swap, not a redesign.

## Tools and libraries

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


## Rejected alternatives

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

## Assumptions

Nobody answered these, so nothing was decided on them. Each is a question worth asking before this is built.

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

## Licences

Everything this design pulls in, so it can be checked before a legal team checks it.

- `plain-python`: PSF
