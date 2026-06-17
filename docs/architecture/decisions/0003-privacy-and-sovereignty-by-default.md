# 0003 — Privacy & sovereignty are defaults, not add-ons

- **Status:** Accepted
- **Date:** 2026-06-17
- **Deciders:** Platform architecture, governance
- **Related:** [Reference · Access Control & RBAC](../../reference/access-control-rbac.md), [Governance · Data Commons](../../governance/data-commons.md)

## Context

Aegoria carries sensitive data of every kind (PII, PHI, financial) across jurisdictions with
divergent law (GDPR, HIPAA, CCPA, emerging AI regulation). A platform where privacy is an
opt-in feature inevitably leaks: someone forgets to enable it. The resolution of the
surveillance-vs-privacy tension must be **structural** — safe by default, with the burden of
proof on *relaxing* protection, not on adding it.

## Decision

Privacy and data residency are **on by default** and enforced in the engine's governance
layer ([`services/governance.py`](../../../engine/aegoria_core/services/governance.py)), not
left to callers:

- **PII/PHI auto-classification** on ingest raises field sensitivity automatically.
- **Residency / sovereignty**: data bound to a jurisdiction may not be processed elsewhere.
- **Default-on obligations** for non-owners on sensitive data: masking, aggregate-only, and
  **differential privacy** (calibrated noise with an ε/δ budget).
- **Raw row-level PII retrieval is denied** for non-owners; use aggregates or de-identified queries.
- **Federated learning** lets models train where data lives — raw data never crosses a boundary.
- Misconfiguration **fails safe**: the default is *more* private, not less.

Defaults are expressed in [`config.py`](../../../engine/aegoria_core/config.py)
(`PrivacyDefaults`, all enabled) and can only be *relaxed* by explicit configuration.

## Consequences

**Positive**
- Regulatory posture holds across markets without per-domain privacy code.
- A forgotten setting protects more, not less — the dangerous direction is the hard one.
- Sovereignty is enforceable: residency denials happen before compute placement.

**Negative / costs we accept**
- Some convenience is traded away: raw PR pulls require explicit, audited elevation
  (e.g. the [super-admin](../../reference/access-control-rbac.md) break-glass role).
- Differential privacy adds noise to aggregates — correct, but it must be communicated to users.

**Neutral**
- The privacy mechanisms (DP, masking, federation) live behind swappable services and can be
  upgraded (e.g. to OpenDP) without changing the engine.

## Alternatives considered

- **Privacy as an opt-in feature/library** — the default-insecure failure mode; rejected.
- **Perimeter-only controls (network/role gates)** — necessary but insufficient; they don't
  protect a row once a query runs. We enforce at the data layer too.
