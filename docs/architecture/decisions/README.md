# Architecture Decision Records (ADRs)

An **ADR** captures a single significant, hard-to-reverse architectural decision: the
context that forced it, the decision itself, and the consequences we accept. ADRs are
immutable once accepted — we don't edit history, we supersede it with a new ADR.

## Why

The most important decisions in Aegoria are *constraints* (e.g. "the core engine never
changes"). Recording them — with their alternatives and trade-offs — keeps the system
honest as it grows and onboards contributors without re-litigating settled questions.

## Format & lifecycle

Each ADR uses the [template](./adr-template.md):

- **Status** — `Proposed` → `Accepted` → (`Superseded by NNNN` | `Deprecated`)
- **Context** — the forces and constraints in play
- **Decision** — what we will do (active voice)
- **Consequences** — positive, negative, and neutral results we accept
- **Alternatives considered** — and why they were not chosen

Files are numbered and immutable: `NNNN-short-title.md`. To change a decision, add a new
ADR that supersedes the old one (and update the old one's status line only).

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](./0001-core-engine-never-changes.md) | The core engine never changes | Accepted |
| [0002](./0002-iceberg-lakehouse-and-open-formats.md) | Iceberg lakehouse over open formats | Accepted |
| [0003](./0003-privacy-and-sovereignty-by-default.md) | Privacy & sovereignty are defaults, not add-ons | Accepted |
| [0004](./0004-provider-agnostic-adapters-and-plugins.md) | Provider-agnostic adapters + declarative plugins | Accepted |

→ Back to [Architecture](../README.md) · [Documentation home](../../README.md)
