# 0004 — Provider-agnostic adapters + declarative plugins

- **Status:** Accepted
- **Date:** 2026-06-17
- **Deciders:** Platform architecture
- **Related:** [0001 — The core engine never changes](./0001-core-engine-never-changes.md), [Reference · Adapter & Service Interfaces](../../reference/adapter-interfaces.md), [Reference · Domain-Pack Specification](../../reference/domain-pack-spec.md)

## Context

[ADR 0001](./0001-core-engine-never-changes.md) requires that new clouds, formats, brokers,
identity providers, and entire industries be added without editing engine code. That needs a
concrete extension mechanism with two distinct seams: one for **infrastructure** and one for
**domain knowledge**.

## Decision

Two extension mechanisms, both resolved by the registry:

1. **Adapters** — provider-agnostic *infrastructure* behind protocols
   (`StorageAdapter`, `CatalogAdapter`, `ComputeAdapter`, `StreamAdapter`, `IdentityAdapter`,
   `ProvenanceSigner`, `CarbonSource`) and *capability* services (`LakehouseService`,
   `GovernanceService`, `ComputeScheduler`, …). A backend is added by shipping an adapter that
   satisfies the protocol and registering it under a name the
   [config](../../../engine/aegoria_core/config.py) selects.

2. **Domain-packs** — *domain knowledge* as portable, versioned, **declarative** plugins
   ([manifest spec](../../reference/domain-pack-spec.md)): schemas, ontology, quality rules,
   ML-model references, and access policy as data — not code. The engine loads them at runtime.

Both register through the same [`Registry`](../../../engine/aegoria_core/registry.py) and are
discovered via `aegoria.providers` entry points. Default implementations ship with the engine
but are registered like any third-party provider.

## Consequences

**Positive**
- The two axes of change (infra, domain) are cleanly separated and independently versioned.
- A new market is usually **zero code** — a YAML manifest plus sample data.
- A new cloud/format is a self-contained adapter package; the registry validates it against
  its protocol at wiring time.

**Negative / costs we accept**
- Protocol surface must be stable and well-documented; a missing method is found late (at runtime).
- Pure-declarative packs cover most needs; the rare custom connector/model still ships code,
  but only behind the same adapter contracts.

**Neutral**
- Capability *services* (lakehouse, governance, scheduler) are also swappable — they're
  domain-neutral core code, but not privileged over alternative implementations.

## Alternatives considered

- **A single "plugin" abstraction for both infra and domain** — conflates two very different
  change axes and muddies the contracts.
- **Code-only domain extensions** — far higher onboarding cost; defeats the "onboard a market
  in under a day, declaratively" goal.
