# Architecture

How Aegoria is built — its shape, the technology it stands on, and the decisions of
record that got it there.

| Document | Purpose |
|----------|---------|
| [Overview](./overview.md) | High-level architecture: data plane, trust fabric, plugin host, deployment topologies, and the governed query flow. |
| [Tech Stack](./tech-stack.md) | Every open-standard technology choice, its alternative, and the adapter that keeps it swappable (no lock-in). |
| [Decisions (ADRs)](./decisions/) | Architecture Decision Records — the significant, hard-to-reverse choices, with context and consequences. |

## The load-bearing idea

The core engine **never changes** when a market or a backend is added. Infrastructure
is swapped behind [adapter protocols](../reference/adapter-interfaces.md); markets onboard
as declarative [domain-packs](../reference/domain-pack-spec.md). The mechanics — a registry
of providers resolved against stable protocols — are detailed in the
[Overview](./overview.md) and ratified in
[ADR&nbsp;0001](./decisions/0001-core-engine-never-changes.md).

→ Back to [Documentation home](../README.md) · Related: [Reference](../reference/) · [Product · Roadmap](../product/roadmap.md)
