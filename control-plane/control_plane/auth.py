"""Authentication + the platform user store for the control-plane.

This is the API-side complement to the engine's RBAC: it turns a username +
password into a signed, stateless bearer token whose claims (subject, roles,
jurisdiction, ABAC attributes) become an :class:`aegoria_core.Principal` that the
``GovernanceService`` authorizes against. The token is an HMAC-SHA256-signed
``base64url(payload).base64url(sig)`` — no server-side session store.

The default users below ship a **super-admin** (apex role ``superadmin`` →
unrestricted, break-glass access) plus role-scoped demo accounts so RBAC is
observable end to end. Passwords are overridable via environment variables; in
production this whole module is replaced by an OIDC/OAuth2 adapter behind the
same Principal contract.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Optional

from aegoria_core.contracts.models import Principal, Sensitivity

# --------------------------------------------------------------------------- #
# User store (env-overridable). Never expose password fields over the API.
# --------------------------------------------------------------------------- #
def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


USERS: dict[str, dict[str, Any]] = {
    "admin": {
        "password": _env("AEGORIA_ADMIN_PASSWORD", "Aegoria-Superadmin-2026!"),
        "display_name": "Root Administrator",
        "roles": ["superadmin", "admin", "owner", "steward"],
        "jurisdiction": "GLOBAL",
        "clearance": Sensitivity.RESTRICTED.value,
        "attributes": {"purpose": "administration", "org": "aegoria"},
    },
    "steward": {
        "password": _env("AEGORIA_STEWARD_PASSWORD", "steward"),
        "display_name": "Platform Steward",
        "roles": ["steward", "admin"],
        "jurisdiction": "GLOBAL",
        "clearance": Sensitivity.CONFIDENTIAL.value,
        "attributes": {"purpose": "governance", "org": "aegoria"},
    },
    "analyst": {
        "password": _env("AEGORIA_ANALYST_PASSWORD", "analyst"),
        "display_name": "Credit Risk Analyst",
        "roles": ["analyst"],
        "jurisdiction": "EU",
        "clearance": Sensitivity.CONFIDENTIAL.value,
        "attributes": {"purpose": "underwriting", "region": "EU", "org": "riskco"},
    },
    "viewer": {
        "password": _env("AEGORIA_VIEWER_PASSWORD", "viewer"),
        "display_name": "Read-only Viewer",
        "roles": ["public"],
        "jurisdiction": "GLOBAL",
        "clearance": Sensitivity.PUBLIC.value,
        "attributes": {"purpose": "browsing"},
    },
}

_SECRET = _env("AEGORIA_SESSION_SECRET", "aegoria-dev-secret-change-me").encode()
_TOKEN_TTL_S = int(_env("AEGORIA_TOKEN_TTL_S", "28800"))  # 8 hours


# --------------------------------------------------------------------------- #
# Token signing / verification (stateless, HMAC-SHA256)
# --------------------------------------------------------------------------- #
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def issue_token(username: str, *, now: Optional[float] = None) -> str:
    user = USERS[username]
    now = now if now is not None else time.time()
    claims = {
        "sub": username,
        "name": user["display_name"],
        "roles": user["roles"],
        "jurisdiction": user["jurisdiction"],
        "clearance": user["clearance"],
        "attributes": user["attributes"],
        "iat": int(now),
        "exp": int(now) + _TOKEN_TTL_S,
    }
    payload = _b64(json.dumps(claims, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_token(token: str, *, now: Optional[float] = None) -> Optional[dict[str, Any]]:
    try:
        payload, sig = token.split(".", 1)
        expected = _b64(hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        claims = json.loads(_b64d(payload))
    except Exception:
        return None
    now = now if now is not None else time.time()
    if int(claims.get("exp", 0)) < now:
        return None
    return claims


def authenticate(username: str, password: str) -> Optional[dict[str, Any]]:
    """Constant-time password check. Returns the (sanitized) user or None."""
    user = USERS.get(username)
    if user is None:
        # Still do a comparison to reduce username-enumeration timing signal.
        hmac.compare_digest(password, "x")
        return None
    if not hmac.compare_digest(password, str(user["password"])):
        return None
    return public_user(username)


def public_user(username: str) -> dict[str, Any]:
    user = USERS[username]
    return {
        "subject": username,
        "displayName": user["display_name"],
        "roles": list(user["roles"]),
        "jurisdiction": user["jurisdiction"],
        "isSuperAdmin": bool({"superadmin", "root"} & set(user["roles"])),
    }


def principal_from_claims(claims: dict[str, Any]) -> Principal:
    try:
        clearance = Sensitivity(claims.get("clearance", Sensitivity.INTERNAL.value))
    except ValueError:
        clearance = Sensitivity.INTERNAL
    return Principal(
        subject=claims.get("sub", "anonymous"),
        display_name=claims.get("name", claims.get("sub", "anonymous")),
        roles=list(claims.get("roles", ["public"])),
        attributes=dict(claims.get("attributes", {})),
        jurisdiction=claims.get("jurisdiction", "GLOBAL"),
        clearance=clearance,
    )


def principal_from_bearer(authorization: Optional[str]) -> Optional[Principal]:
    """Parse an ``Authorization: Bearer <token>`` header into a Principal."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    claims = verify_token(token.strip())
    return principal_from_claims(claims) if claims else None
