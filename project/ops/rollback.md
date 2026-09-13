# Rolling back

Substrate: **systemd-unit**

```bash
sudo systemctl stop app
sudo ln -sfn /opt/app-previous /opt/app
sudo systemctl start app
systemctl status app --no-pager
```

## What this does not undo

Reverting a deployment restores the code. It does not reverse anything the running system already did. Everything below is irreversible by nature, and treating a rollback as though it covers them is how one incident becomes two.

- Nothing in this system takes irreversible actions.

Before rolling back, establish what the system did while the bad version was live. That question is easier to answer now than in an hour, and the audit trail is where the answer is.

## Data

A schema change applied forward is not undone by deploying the previous code. If this release migrated anything, the rollback is a migration of its own and needs writing before the release rather than during the incident.
