"""``static`` identity adapter — token-as-claims auth for local development.

A bearer token is the literal string ``"<subject>:<role1,role2,...>"`` (the role
suffix is optional). Attributes for a subject come from an in-memory map seeded
via ``config`` options. In production this is replaced by an OIDC/OAuth2 adapter
under the same :class:`~aegoria_core.contracts.adapters.IdentityAdapter`
contract — the governance layer consumes a ``Principal`` either way.
"""

from __future__ import annotations

from typing import Any

import structlog

from ..config import AegoriaConfig
from ..contracts.models import Principal, Sensitivity
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.identity.static")


class StaticIdentity:
    """Resolves dev tokens into principals and looks up ABAC attributes."""

    name = "static"

    def __init__(self, attributes: dict[str, dict[str, Any]] | None = None) -> None:
        # subject -> ABAC attribute map (jurisdiction, clearance, owner_of, ...)
        self._attributes: dict[str, dict[str, Any]] = attributes or {}

    # -- IdentityAdapter ------------------------------------------------ #
    def authenticate(self, token: str) -> Principal:
        if not token:
            raise ValueError("empty identity token")
        subject, _, role_blob = token.partition(":")
        subject = subject.strip()
        if not subject:
            raise ValueError(f"malformed identity token {token!r}")
        roles = [r.strip() for r in role_blob.split(",") if r.strip()] or ["public"]
        attrs = dict(self._attributes.get(subject, {}))
        jurisdiction = str(attrs.get("jurisdiction", "GLOBAL"))
        clearance_raw = attrs.get("clearance", Sensitivity.INTERNAL.value)
        try:
            clearance = Sensitivity(clearance_raw)
        except ValueError:
            clearance = Sensitivity.INTERNAL
        return Principal(
            subject=subject,
            display_name=str(attrs.get("display_name", subject)),
            roles=roles,
            attributes=attrs,
            jurisdiction=jurisdiction,
            clearance=clearance,
        )

    def resolve_attributes(self, subject: str) -> dict[str, Any]:
        return dict(self._attributes.get(subject, {}))


@adapter("identity", "static")
def make_static_identity(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> StaticIdentity:
    """Factory the engine invokes to build the static identity adapter.

    ``options`` may carry ``attributes`` mapping subjects to ABAC attribute dicts.
    """
    return StaticIdentity(attributes=options.get("attributes"))
