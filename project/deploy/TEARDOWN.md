# Taking it away

## The application

The substrate has no concept of un-doing, so these are manual and written out rather than left implied.

```bash
sudo systemctl disable --now app
sudo rm /etc/systemd/system/app.service
sudo systemctl daemon-reload
sudo rm -rf /opt/app /var/lib/app
sudo userdel app
```

## The environment

This provisioner has no destroy. Whatever it configured -- users, packages, mounts -- is removed by hand, or by re-running the provisioning against a clean target.

Then confirm nothing was left behind: data directories, secrets in a vault, DNS entries, and anything created by hand during the engagement.
