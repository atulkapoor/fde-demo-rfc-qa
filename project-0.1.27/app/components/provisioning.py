# Advisory: decided and recorded at build time -- not a
# step the payload passes through; the pipeline does not
# chain this module.
"""provisioning: manual-runbook, via plain-python.

Written steps: always

The artefacts are written into deploy/ at build time. What this records is
whether the chosen tool can take the deployment away again -- because that
capability is the difference between the options and it should be visible from
the code rather than inferred from the directory listing.
"""

from __future__ import annotations

from typing import Any


class Provisioning:
    """Guard, as manual-runbook."""

    interface = "Guard"
    approach = "manual-runbook"
    stack = "plain-python"

    # Only one of these knows what it created. Where it is False, TEARDOWN.md
    # carries the manual steps rather than pretending the question does not
    # arise.
    provides_teardown = "manual-runbook" == "terraform-module"

    def run(self, payload: Any) -> Any:
        return payload
