# Where the failure lives

An unclear definition can look like a model error. Missing evidence can look like weak reasoning. A tool timeout can look like a capability limit. The expensive habit is re-prompting or switching models before finding which layer actually failed -- so this walks the layers in order, cheapest to check first, the model last.

## 1. Definitions

**Check** — take the failing case to whoever owns evaluation and ask what the right output is. If two people who should know disagree, stop here: no layer below this one can settle a question the client has not.

**If it is this** — the fix is a decision, recorded in the golden cases, not a change to any code. Disagreement here is a discovery finding, and surfacing it is this system working.

## 2. Evidence

**Check** — for the failing case, look at what retrieval returned before the model ever saw it. If the right answer is not in the evidence, this is recall, not reasoning.

**If it is this** — the fix lives in retrieval: the corpus, the index or the query. A better prompt cannot cite what never arrived.

**Measure** — `python evals/retrieval.py` scores this layer alone, no model in the loop: recall against the cases in `evals/retrieval_cases.jsonl`. The suspicion becomes a number before anything downstream gets blamed.

## 3. The model -- only now

**Check** — the evaluation's error breakdown, with everything above ruled out. One field dominating usually means a mapping to fix; failures spread across fields mean a capability limit.

**If it is this** — change the prompt before changing the model, one change at a time, re-running the evaluation after each. An improvement nobody measured is a mood.
