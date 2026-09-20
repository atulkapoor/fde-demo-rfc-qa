# Advisory: decided and recorded at build time -- not a
# step the payload passes through; the pipeline does not
# chain this module.
"""deployment: systemd-unit, via plain-python.

Service unit: always

The artefacts for this rung are written into deploy/ at build time. This module
records which rung was chosen and what would earn the next one, so the decision
is visible in the running system rather than only in a document nobody opens.
"""

from __future__ import annotations

from typing import Any


class Deployment:
    """Guard, as systemd-unit."""

    interface = "Guard"
    approach = "systemd-unit"
    stack = "plain-python"

    def rung(self) -> dict[str, Any]:
        """Where on the ladder this sits, and what moves it."""
        return {
            "approach": self.approach,
            "graduate_when": {
                "systemd-unit": "more than one long-lived process, or a dependency "
                                "that conflicts with the host",
                "compose": "multi-node scheduling, or zero-downtime rolling deploys",
                "kubernetes-manifests": "multi-tenant isolation, or an HA control plane "
                                        "somebody has asked for by name",
            }.get(self.approach, "nothing further"),
        }

    def run(self, payload: Any) -> Any:
        return payload
