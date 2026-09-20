# Deployment

Topology: **on-prem**  
Substrate: **systemd-unit**  
Provisioning: **manual-runbook**

Neither of these is a default. The substrate is a ladder and this is the rung the profile earned; the provisioner follows what the team already operates, whether there is an API to call, and whether this environment has to be destroyed cleanly.

The reasoning for each is in `ARCHITECTURE.md`, alongside what was rejected and why.

## Install

Every step below exists because the unit file demands its result --
the user, the interpreter path, the writable state dir, the env
file. Run as root on the target host, from this project's root:

```bash
useradd --system --shell /usr/sbin/nologin --home /opt/app app   # the unit's User=
REL=/opt/app/releases/$(date +%Y%m%d%H%M%S)   # releases side by side
mkdir -p "$REL"
# Stage the package, not the working tree: no tests, no CI, no .env.
rsync -a --exclude .git --exclude .venv --exclude tests --exclude .github \
      --exclude '.*' app evals pyproject.toml "$REL/"
# The documents to answer from (a build with a retrieval layer): the
# unit's StateDirectory owns /var/lib/app; corpus/ lives under it.
mkdir -p /var/lib/app/corpus && rsync -a corpus/ /var/lib/app/corpus/
chown -R app /var/lib/app
python3 -m venv "$REL/.venv"                  # ExecStart's interpreter
"$REL/.venv/bin/pip" install "$REL"
ln -sfn "$REL" /opt/app/current               # the unit runs `current`
install -D -m 640 -o root -g app deploy/env.example /etc/app/env   # then EDIT it
install -m 644 deploy/systemd/app.service /etc/systemd/system/app.service
systemctl daemon-reload && systemctl enable --now app
```

Before `enable --now`, edit `/etc/app/env`: set AUTH_TOKEN (the
service refuses every outward call without it), point the model
endpoint at a host inside the network, and never set
ANTHROPIC_API_KEY on a build whose data may not leave -- the boundary
refuses to import with it set. The service binds loopback; exposing
it means an authenticating, rate-limiting proxy in front, not BIND.

Then prove it:

```bash
curl -s localhost:8080/health   # liveness: the process answers
curl -s localhost:8080/ready    # readiness: dependencies answer
journalctl -u app -n 20 --no-pager
```
