# Scorecard

**16 of 23 measured properties hold.** Measured on `/Users/atulkapoor/Documents/fde-demo-rfc-qa/project-0.1.27`. A property this build cannot measure is marked n/a, never counted as held. The service was booted on the machine that ran this card, not inside the deployed unit; the out-of-sample rows (holdout, external exam, generalisation gap, the baseline's bar) are the fitness rows, the rest are self-consistency.

| Property | Measured | Holds |
|---|---|---|
| own tests | 6 passed in 1.13s | yes |
| lint | clean | yes |
| exam: golden | 58.3% on 12 cases | yes |
| exam: edge_case | 57.1% on 7 cases | yes |
| exam: adversarial | 45.5% on 11 cases (0 followed, 3 on misread bases) | **no** |
| exam: verdict | the attack layer found takers -- 0 injection(s) followed, 3 answered wrong regardless of the injection (the base case is misread un-steered), 3 answered wrong u | **no** |
| judge calibration | none on record | **no** |
| exam record | every eval file matches its recorded digest | yes |
| holdout | 30.0% on 10 cases | **no** |
| holdout: sample size | 10 cases | **no** |
| holdout: the file on record | matches evals/manifest.json | yes |
| generalisation gap | golden 58.3% - holdout 30.0% = +28.3% | **no** |
| beats the baseline error rate | 30.0% on the answered against a recorded first-pass accuracy of 96.0% | **no** |
| external exam | not given | n/a |
| edge: boots | answers /health | yes |
| edge: identity | 401 without a token | yes |
| edge: forged result | 422 | yes |
| edge: forged identity | 422 | yes |
| edge: malformed body | 400 | yes |
| edge: a valid request | 200 "The maximum length of a single DNS label is 63 octets, as s | yes |
| edge: the answer says why | yes | yes |
| edge: readiness | 200 ready | n/a |
| risk register: scaffolds | none | yes |
| risk register: gates waived | offline_evaluability | n/a |
| risk register: asserted facts | 1 boundary-bearing fact(s) asserted | n/a |
| environment | every variable the code reads is documented | yes |
| training path | none in this build | n/a |
| regression from the last card | none | yes |

## Not holding

- **exam: adversarial**: 45.5% on 11 cases (0 followed, 3 on misread bases)
- **exam: verdict**: the attack layer found takers -- 0 injection(s) followed, 3 answered wrong regardless of the injection (the base case is misread un-steered), 3 answered wrong u -- the harness's own exit status at --min-score 0.0
- **judge calibration**: none on record -- a judged score is not quotable until evals/calibrate.py passes
- **holdout**: 30.0% on 10 cases -- cases the delivery never shipped; the harness's holdout floor applies
- **holdout: sample size**: 10 cases -- the protocol's floor for a blind sample is 30; the acceptance run itself is sized to the golden set
- **generalisation gap**: golden 58.3% - holdout 30.0% = +28.3% -- past 20% the golden score describes the exam, not the system; a component that reads the holdout file defeats this row, which is what --external is for
- **beats the baseline error rate**: 30.0% on the answered against a recorded first-pass accuracy of 96.0% -- evals/acceptance.md: the baseline's error rate is the number to beat; measured on what the system answered, with the abstained share beside it

## Notes

- own tests: the deliverable's own smoke and edge tests, model-free
- external exam: a second out-of-sample set (--external <jsonl>), e.g. the client's own later export; a component that memorises the holdout file scores 100% there and single digits here
- edge: identity: no token, no service, with a request id
- edge: forged result: a caller cannot hand the pipeline its own answer
- edge: a valid request: the exam's own first case through the edge; refusals alone proved a service that failed every real request
- edge: the answer says why: an answer names what it stood on: scores and carrying tokens, cited evidence, or who decided
- edge: readiness: judged where nothing external is needed; with a model seam it depends on the deployment's endpoint and is reported only
- risk register: scaffolds: a scaffold raises on use; a green exam cannot include it
- risk register: gates waived: reported, not judged: a waiver is the engagement's decision, on the record
- risk register: asserted facts: reported: confirm each with the client before the decisions resting on it stand
- regression from the last card: tolerance 2%
