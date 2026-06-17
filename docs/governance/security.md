# Security & Compliance

Aegoria's security posture is **structural**: protection is the default and enforced at the
data layer, so a forgotten setting fails *safe*. This document summarizes the controls,
the regulatory mapping, and how to report a vulnerability.

## Principles

1. **Privacy & sovereignty by default** — see [ADR 0003](../architecture/decisions/0003-privacy-and-sovereignty-by-default.md). Misconfiguration yields *more* protection, not less.
2. **Least privilege** — access is denied unless a role/policy grants it; raw PII is never returned to non-owners. See [Access Control & RBAC](../reference/access-control-rbac.md).
3. **Defense in depth** — perimeter auth (login/middleware/bearer tokens) *and* data-layer enforcement (governance + scheduler obligations).
4. **Provenance & integrity** — every dataset carries machine-readable provenance and a C2PA-style content signature attached at capture; tampering is detectable.
5. **Open & auditable** — open-source core; every access decision is explainable and logged.

## Controls

| Control | Mechanism | Where |
|---------|-----------|-------|
| Authentication | Signed session cookie (console) / HMAC bearer token (API); OIDC/OAuth2 in production | [`apps/console/lib/auth`](../../apps/console/lib/auth), [`control-plane`](../../control-plane) |
| Authorization (RBAC/ABAC) | Role + attribute policy pipeline | [`services/governance.py`](../../engine/aegoria_core/services/governance.py) |
| PII/PHI classification | Auto-detection on ingest; raises field sensitivity | `services/governance.py` |
| Data residency / sovereignty | Jurisdiction-bound data may not be processed elsewhere | `services/governance.py` |
| Differential privacy | Calibrated noise on aggregates with an (ε, δ) budget | `services/governance.py`, `services/scheduler.py` |
| Masking / aggregate-only | Obligations enforced on query results pre-materialization | `services/scheduler.py` |
| Federated learning | Models train where data lives; raw data never crosses a boundary | `services/governance.py` |
| Content provenance | sha256 checksum + C2PA-style signature; tamper detection | [`provenance_ed25519.py`](../../engine/aegoria_core/adapters_builtin/provenance_ed25519.py) |
| Secrets | `AEGORIA_SESSION_SECRET`, `AEGORIA_*_PASSWORD` via environment; never in code | deploy config |

## Regulatory mapping

| Regulation | How Aegoria supports it |
|------------|-------------------------|
| **GDPR** (EU) | Data residency enforcement, PII minimization (masking/DP), purpose-bound ABAC, provenance/lineage for accountability, right-to-erasure via dataset lifecycle. |
| **HIPAA** (US health) | PHI classification, de-identification (masking + DP), least-privilege access, audit trail. |
| **CCPA/CPRA** (California) | Data inventory via the FAIR catalog, purpose limitation, access controls. |
| **Emerging AI regulation** | Model provenance, dataset lineage, content signing (C2PA), and a misinformation/provenance verification service. |

Residency and regulations are declared per dataset/jurisdiction in domain-pack manifests and
the engine [config](../../engine/aegoria_core/config.py), so the same controls hold across markets.

## Hardening checklist (production)

- [ ] Replace the static user store with an OIDC/OAuth2 `IdentityAdapter`.
- [ ] Set strong `AEGORIA_SESSION_SECRET` and rotate; set per-account passwords.
- [ ] Serve over TLS and enable `secure` cookies (the demo runs http on localhost).
- [ ] Restrict CORS on the control-plane to known origins.
- [ ] Scope the super-admin role to break-glass use; alert on its use.
- [ ] Enable audit log shipping for all `AccessDecision`s.

## Reporting a vulnerability

Please report security issues privately to the maintainers (see the project README) rather
than opening a public issue. Provide reproduction steps and impact; we aim to acknowledge
within a few business days.

→ Related: [Access Control & RBAC](../reference/access-control-rbac.md) · [ADR 0003](../architecture/decisions/0003-privacy-and-sovereignty-by-default.md) · [Data Commons](./data-commons.md)
