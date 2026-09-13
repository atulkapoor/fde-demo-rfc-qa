# Runbook

What you will see, what it means, and what to do. Failures here are grouped the way the evaluation harness classifies them, so a classified failure leads somewhere instead of sitting in a report.

## When the answers are wrong and nothing is obviously broken

Look at **perception** first. Quality flows one direction through this system, and that component caps everything after it -- no amount of work further along recovers what it lost.

Components in this system: `deployment`, `evaluation`, `governance`, `observability`, `perception`, `provisioning`, `reasoning`, `representation`, `retrieval`, `serving`.

When nothing on this page fits, `diagnosis.md` beside it walks the layers of this system in the order they are cheap to check -- definitions first, the model last.

## By failure source

### data

**You see** — Fields are missing or empty for a whole class of records, and the same records look wrong in the source too.

**Do** — The source was wrong before this system saw it. Check the feed, not the pipeline -- fixing this downstream means inventing values, which is worse than reporting the gap.

### input

**You see** — Answers are wrong in a way that correlates with a document layout or a file type, and the extracted text looks mangled.

**Do** — Parsing lost it. Look at what perception reported it could not keep -- the clean share and the flattened tables. Nothing downstream recovers information that was never read.

### prediction

**You see** — The value is present, plausible and wrong. Structure is fine; content is not.

**Do** — The rule or model produced it. Check the error breakdown by field: a single field dominating means a mapping to fix, spread failures mean a capability limit.

### output

**You see** — Right values in the wrong shape -- a number as a string, a date in the wrong format, a field in the wrong place.

**Do** — The contract is being violated at the edge. Validate against the contract before returning rather than after somebody complains.

### system

**You see** — Timeouts, restarts, memory exhaustion. Failures cluster in time rather than by input.

**Do** — Infrastructure, not logic. Check resource limits, concurrency settings and whether a dependency is degraded. Re-running the same input will usually succeed, which is how you tell.

### integration

**You see** — Each component behaves correctly in isolation and the whole produces nonsense.

**Do** — The seam between two parts. Check the contract at the boundary -- shapes that almost match are the usual cause, and both sides look right when read alone.

## If data may have left the boundary

**You see** — a component that handles regulated data appearing outside `in_boundary`, or an outward call from one.

**Do** — stop the deployment before investigating. `app/boundary.py` checks at import, so a running system with this problem was started with the check removed. Establish what left and over what period before restarting anything; that question gets harder every hour.
