# Aegoria Documentation

> One planet. Every domain. Data you can trust.

This is the home of Aegoria's documentation. It is organized into sections by
**purpose** so each audience can find what it needs quickly. Every document is
versioned with the code and cross-links to the source of truth in the repo.

```
docs/
├── product/        — what & why: overview, roadmap, KPIs
├── architecture/   — how it works: architecture, tech stack, decisions (ADRs)
├── reference/      — precise specs: domain-pack format, adapter/service interfaces, access control
├── governance/     — data-commons model, security & compliance
└── brand/          — identity, the signature colour "Auralis", logo, voice
```

## Sections

| Section | Contents | Index |
|---------|----------|-------|
| **Product** | The problem, the constraints, the plan, and how success is measured. | [product/](./product/) |
| **Architecture** | The shape of the system, justified technology choices, and the decisions of record. | [architecture/](./architecture/) |
| **Reference** | Authoritative specifications: domain-pack manifests, adapter/service protocols, access control. | [reference/](./reference/) |
| **Governance** | Participatory data-commons model, sovereignty, and security & compliance. | [governance/](./governance/) |
| **Brand** | Name, tagline, palette, logo, typography, and voice. | [brand/](./brand/) |

## Start here, by role

- **New to Aegoria?** → [Product · Overview](./product/overview.md)
- **Engineer / architect?** → [Architecture · Overview](./architecture/overview.md) → [Decisions (ADRs)](./architecture/decisions/)
- **Onboarding a new market (domain-pack)?** → [Reference · Domain-Pack Specification](./reference/domain-pack-spec.md)
- **Adding a cloud / format / broker / IdP?** → [Reference · Adapter & Service Interfaces](./reference/adapter-interfaces.md)
- **Integrating auth or reasoning about access?** → [Reference · Access Control & RBAC](./reference/access-control-rbac.md)
- **Evaluating technology / lock-in risk?** → [Architecture · Tech Stack](./architecture/tech-stack.md)
- **Planning or tracking delivery?** → [Product · Roadmap](./product/roadmap.md) · [Product · KPIs](./product/kpis.md)
- **A contributing community / data steward?** → [Governance · Data Commons](./governance/data-commons.md)
- **Building UI / decks / branded surfaces?** → [Brand · Guidelines](./brand/guidelines.md)

## Conventions

- **Source of truth is the code.** Docs link to real files (e.g. the frozen
  [contracts](../engine/aegoria_core/contracts/)); when code and docs disagree, the
  code wins and the doc is a bug.
- **Decisions are recorded as ADRs.** Significant, hard-to-reverse choices live in
  [architecture/decisions/](./architecture/decisions/) using a lightweight ADR format.
- **Shared vocabulary lives in the [Glossary](./GLOSSARY.md).** Define a term once,
  reference it everywhere.
- **File naming:** lowercase-kebab-case, descriptive (no ordinal prefixes). ADRs are
  zero-padded and numbered (`NNNN-title.md`).
- **Voice:** precise, declarative, vendor-neutral. See the
  [Brand Guidelines](./brand/guidelines.md) for tone.

## Related top-level material

- Project [README](../README.md) — quickstart, Docker, repository layout.
- [Glossary](./GLOSSARY.md) — canonical terms used across all docs.
- Runnable proof: [`examples/e2e_demo.py`](../examples/e2e_demo.py).
