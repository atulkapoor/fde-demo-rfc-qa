# Provisioning runbook

Chosen because nothing here can be provisioned through an API --
somebody files a ticket, somebody racks a machine -- so the honest
artefact is the list of steps a person follows, written down once
instead of re-derived per environment.

Fill in each step as it is learned. A runbook nobody updates is a
runbook that lies. What is already known is filled in.

## Request

1. One Linux host inside the network the data may not leave (the unit
   pins egress to loopback and private ranges); python3 >= 3.10, systemd,
   rsync. 2 GB of memory for the service at the shipped ceilings; see
   ARCHITECTURE.md for the sizing arithmetic when the corpus is larger.
2. A service account `app` (nologin) and the paths the unit names:
   /opt/app/releases, /var/lib/app (StateDirectory creates it), /etc/app/env.
3. Reachability to the model endpoint named in /etc/app/env, and nothing
   else outward. _Who approves the host and the firewall rule: fill in._

## Verify

1. `systemctl status app` running; `curl -s localhost:8080/ready` answers
   200 -- a 503 names what is missing; `journalctl -u app -n 20` shows
   one JSON line per request.
2. `python -m pytest -q tests/` green in the release directory.

## Hand back

1. `deploy/TEARDOWN.md`, in order. The ledger under /var/lib/app is the
   record of every outward call: it is handed to the client, not deleted.
