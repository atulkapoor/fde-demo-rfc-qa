# Implementation log

## Round 1

- check: red
- changed: app/components/perception.py, app/components/reasoning.py, app/components/representation.py, app/components/retrieval.py, app/pipeline.py

```
metrics: judged comparison against the reference (calibration protocol in evals/acceptance.md)
  golden         19 cases  0.0%
               by source: {'system': 19}
  edge_case       0 cases  --
  adversarial     2 cases  0.0%
               by source: {'system': 2}
19 golden case(s) errored -- the pipeline is not yet implemented end to end
```

## Round 2

- check: green

```
metrics: judged comparison against the reference (calibration protocol in evals/acceptance.md)
  golden         19 cases  89.5%
               by source: {'prediction': 2}
  edge_case       0 cases  --
  adversarial     2 cases  100.0%
holdout: green (cases the implementer never saw)
```

**Stopped by**: harness green.
