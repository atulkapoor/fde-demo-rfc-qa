"""Where each step is allowed to run.

Checked at import, not reviewed in a document. Data that may not leave
cannot leave by construction, and an embedding is not an exception --
it is recoverable to its source, so it inherits the same placement.
"""

import ipaddress
import os
from urllib.parse import urlparse

PLACEMENT = {
    'boundary-split': 'in_boundary',
    'deployment': 'in_boundary',
    'evaluation': 'in_boundary',
    'governance': 'in_boundary',
    'observability': 'in_boundary',
    'perception': 'in_boundary',
    'provisioning': 'in_boundary',
    'reasoning': 'in_boundary',
    'representation': 'in_boundary',
    'retrieval': 'in_boundary',
    'serving': 'in_boundary',
}

SENSITIVE = {
    'perception',
    'representation',
    'retrieval',
    'serving',
}


# The hosts an outward call may reach. Loopback and private ranges
# by default; anything else must be named in BOUNDARY_ALLOWED_HOSTS.
# A placement table cannot stop a typo in LLM_ENDPOINT -- this can.
EGRESS_VARS = ('LLM_ENDPOINT', 'JUDGE_ENDPOINT', 'SUPERMEMORY_ENDPOINT')


def _inside(host: str) -> bool:
    # A name is inside only when it is named: suffix trust
    # (.internal, .local) let exfil.example.com.local through.
    named = os.environ.get('BOUNDARY_ALLOWED_HOSTS', '').split(',')
    allowed = {h.strip() for h in named
               if h.strip()}
    if host in allowed:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host == 'localhost'
    # Not link-local: 169.254.169.254 is the cloud metadata service,
    # and Python counts that range as private.
    return address.is_loopback or (address.is_private and not address.is_link_local)


def check() -> None:
    """Fail loudly if anything sensitive has been moved outside -- in the
    placement table, or in the one place data actually leaves: a URL."""
    outside = [s for s in SENSITIVE if PLACEMENT.get(s) != 'in_boundary']
    if outside:
        raise RuntimeError(
            f'{outside} handle data that may not leave, but are placed outside'
        )
    if os.environ.get('ANTHROPIC_API_KEY'):
        raise RuntimeError(
            'ANTHROPIC_API_KEY is set on a build whose data may not leave')
    for name in EGRESS_VARS:
        value = os.environ.get(name, '').strip()
        if not value:
            continue
        parts = urlparse(value)
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            raise RuntimeError(f'{name} must be an http(s) URL inside the boundary')
        if not _inside(parts.hostname):
            raise RuntimeError(
                f'{name} points at {parts.hostname!r}, outside the boundary; '
                f'name it in BOUNDARY_ALLOWED_HOSTS if that is deliberate'
            )


check()
