# Access Control & RBAC

How Aegoria decides who may do what. Access control is **layered RBAC + ABAC**, enforced in
the engine's swappable [`GovernanceService`](../../engine/aegoria_core/services/governance.py)
— never in the UI. The UI and the control-plane API both resolve a credential into the same
`Principal`, which governance authorizes against.

- **RBAC** — roles on the principal × policy role-lists × built-in role rules.
- **ABAC** — attribute/`condition` expressions layered on top (jurisdiction, purpose, owner…).
- **Super-admin** — an apex break-glass role that bypasses all of the above.

## Concepts

| Concept | Where | Notes |
|---------|-------|-------|
| `Principal` | [`contracts/models.py`](../../engine/aegoria_core/contracts/models.py) | `subject`, `roles[]`, `attributes{}` (ABAC), `jurisdiction`, `clearance`. |
| `IdentityAdapter` | [`contracts/adapters.py`](../../engine/aegoria_core/contracts/adapters.py) | Pluggable IdP. `static` dev tokens today; OIDC/OAuth2 in production — same contract. |
| `AccessRequest` / `AccessDecision` | `contracts/models.py` | A request `(principal, dataset, action, purpose)` → `allow` + `reason` + `obligations[]`. |
| `Obligation` | `contracts/models.py` | A condition enforced on grant: `mask`, `aggregate_only`, `differential_privacy`, `residency`, `watermark`. |
| `AccessPolicySpec` | [`contracts/domain_pack.py`](../../engine/aegoria_core/contracts/domain_pack.py) | Declarative ABAC/RBAC a domain-pack ships: `effect`, `roles`, `actions`, `datasets` (glob), `condition`, `obligations`. |

## The authorization pipeline

`governance.authorize(request, meta)` runs an ordered pipeline and returns an `AccessDecision`:

```
0. Super-admin / break-glass   roles ∩ {superadmin, root}  → ALLOW, no obligations
1. Residency / sovereignty     jurisdiction residency required & principal elsewhere → DENY
2. Domain-pack policies (ABAC) match datasets×actions×roles, evaluate `condition`; allow/deny + obligations
3. Default RBAC                writes/admin require owner/admin/writer; raw row-level PII read → DENY
4. PII export                  non-owner export of PII → DENY (privacy default)
5. Privacy obligations         non-owner on sensitive data → mask + differential_privacy (+ aggregate_only)
```

Enforcement happens at **two points**: `authorize()` gates the request, then the
[`ComputeScheduler`](../../engine/aegoria_core/services/scheduler.py) enforces obligations on
the *result* — applying masking, differential-privacy noise, and denying raw-PII projections —
**before any row is materialized**.

### ABAC conditions

A policy's `condition` is a small CEL-like expression evaluated by a **safe AST evaluator**
(no `eval`) over `principal`, `resource`, and `compute` namespaces. Examples from the
reference packs:

```yaml
condition: principal.jurisdiction != "EU"          # deny processing outside the EU
condition: principal.subject != resource.owner     # mask unless you own the data
condition: principal.attributes.purpose == "underwriting"
```

A policy applies only when its condition is true; an unparseable condition fails safe (the
policy does not grant).

## Roles & the super-admin

Roles live on the `Principal` and are matched against policy `roles` by set intersection
(`_has_role`). Built-in role semantics:

| Role(s) | Effect |
|---------|--------|
| `superadmin`, `root` | **Apex / break-glass.** Unrestricted access, *no obligations* — bypasses residency, masking, DP, and every policy. Use sparingly; every access is still auditable. |
| `admin`, `owner` | Owner-equivalent: bypasses masking/DP for owned/sensitive data, but still subject to residency. |
| `writer` | May perform write/admin actions. |
| `analyst`, `steward`, `public`, … | Ordinary roles; governed by policies + privacy defaults. |

`is_owner = principal.subject == meta.owner or has_role({admin, owner})`.

## Authentication (UI + API)

Authentication is the seam in front of authorization; both surfaces share one identity model.

- **Console** ([`apps/console`](../../apps/console)) — a `/login` screen issues a signed,
  HTTP-only **session cookie** (HMAC-SHA256). [Middleware](../../apps/console/middleware.ts)
  gates every route; the cookie's claims become the principal shown in the UI.
- **Control-plane API** ([`control-plane`](../../control-plane)) — `POST /auth/login` returns a
  signed **bearer token** with the same claim shape; `POST /query` honors
  `Authorization: Bearer <token>`, so the caller's roles/jurisdiction drive RBAC/ABAC. A
  super-admin token bypasses governance; an analyst token remains constrained.

### Default accounts (demo)

Overridable via `AEGORIA_*_PASSWORD`. In production, replace the static store with an OIDC/OAuth2 IdP.

| Username | Role | Behaviour |
|----------|------|-----------|
| `admin` | Super Admin | Unrestricted (break-glass) |
| `steward` | Steward / Admin | Platform governance |
| `analyst` | Analyst · EU | Residency-bound; masking + differential privacy enforced |
| `viewer` | Viewer | Public, read-only |

## Worked examples

```text
analyst (EU)  · aggregate on consumer-credit   → ALLOW, obligations: residency + mask + differential_privacy(ε=1.0)
analyst (US)  · same query                     → DENY  (residency: data bound to EU)
analyst       · SELECT applicant_name, email…  → DENY  (raw PII projection not permitted)
superadmin    · SELECT applicant_name, email…  → ALLOW (break-glass; returns raw rows)
```

→ Related: [ADR 0003 — Privacy & sovereignty by default](../architecture/decisions/0003-privacy-and-sovereignty-by-default.md) · [Governance · Security](../governance/security.md) · [Adapter & Service Interfaces](./adapter-interfaces.md)
