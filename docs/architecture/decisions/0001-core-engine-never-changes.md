# 0001 — The core engine never changes

- **Status:** Accepted
- **Date:** 2026-06-17
- **Deciders:** Platform architecture
- **Related:** [0004 — Provider-agnostic adapters + declarative plugins](./0004-provider-agnostic-adapters-and-plugins.md), [Architecture · Overview](../overview.md)

## Context

Aegoria must serve *interchangeable* markets — finance, health, climate, logistics, and
markets not yet imagined — and *interchangeable* infrastructure — a laptop today, a
multi-cloud + edge mesh tomorrow. The classic failure mode is a platform that special-cases
each new domain or backend in its core, until the core is an unmaintainable tangle and
"adding a market" means a risky core release.

The non-negotiable requirement: **adding a domain or a backend must require zero edits to
engine code.**

## Decision

The engine ([`engine/aegoria_core/engine.py`](../../../engine/aegoria_core/engine.py)) binds
**only** to stable protocols ([`contracts/`](../../../engine/aegoria_core/contracts/)) and
resolves concrete providers from a [`Registry`](../../../engine/aegoria_core/registry.py) by
*capability + name*. It imports **no** concrete adapter, service, or domain-pack. Providers
self-register via decorators and are discovered through Python entry points
(`aegoria.providers`). Markets onboard as declarative domain-packs loaded at runtime.

We treat `engine.py`, `registry.py`, `config.py`, and `contracts/` as the **frozen core**.
Changing them is a core-version event; adding a market or backend is not.

## Consequences

**Positive**
- New markets/backends ship as plugins; the core is small, auditable, and stable.
- The invariant is *mechanically testable* — [`test_domain_neutrality.py`](../../../engine/tests/test_domain_neutrality.py)
  drives two unrelated markets through one branchless path and asserts the core source is byte-stable.
- Clear ownership boundary between platform team (core) and domain/infra teams (plugins).

**Negative / costs we accept**
- Indirection: everything flows through the registry and protocols, which is more abstract
  than direct calls.
- Protocols must be designed carefully up front; widening them is a core-version event.

**Neutral**
- Default services + adapters ship *with* the engine but register like any other provider —
  they are swappable, not privileged.

## Alternatives considered

- **Domain logic in the core with feature flags** — collapses under N markets; violates the
  requirement directly.
- **Inheritance / a base "DomainEngine" subclassed per market** — couples markets to a class
  hierarchy and to each other; no clean infra-swap story.
