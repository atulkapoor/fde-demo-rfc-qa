# Runbook

What you will see, what it means, and what to do. Failures here are grouped the way the evaluation harness classifies them, so a classified failure leads somewhere instead of sitting in a report.

## First five minutes

Commands before theory -- establish what is actually happening:

```bash
systemctl status app                    # running? since when? restarting?
journalctl -u app -n 100 --no-pager     # one JSON line per request
curl -s localhost:8080/health           # liveness: the process answers
curl -s localhost:8080/ready            # readiness: dependencies answer;
                                        # a 503 body names what is missing
```

Every log line and every response -- answers, refusals, errors -- carry the same `request_id` (also the `X-Request-Id` header, which a caller may set), so a user's failing request finds its log line by id, not by timestamp guessing. A restart loop in `systemctl status` with nothing in the journal means the process dies before logging -- run the ExecStart command by hand as the `app` user and read stderr directly.

## The ledger (builds that act on the world)

`$STATE_DIR/audit.jsonl` is append-only, fsync'd, and grows without bound -- rotate it under a retention the client signs off (it is the record of every outward call). `$STATE_DIR/idempotency.jsonl` is NEVER rotated: a key rotated away is an action that can happen twice. It is compacted instead -- `python -m app.ledger compact --keep-days 90` drops completed keys older than the client's retry horizon and keeps every unresolved one. A key that was reserved and never completed is a call that started and did not finish; every retry of that exact action is refused (`KeyUnresolved`) until a person establishes what happened and records it:

```bash
python -m app.ledger show <key>
python -m app.ledger resolve <key> '{"outcome": "sent once, confirmed in the CRM"}' --by <your name>
```

## The corpus (builds with a retrieval layer)

Ingested once at boot from `CORPUS_DIR`; files it could not read are named in the boot log and counted in `/ready`. A corpus update is a restart (`systemctl restart app` drains in-flight requests first).

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
