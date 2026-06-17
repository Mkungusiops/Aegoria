# Aegoria — Governance & the Data Commons

Aegoria is not just software; it is a **data commons** — shared infrastructure whose value
comes from the communities and organisations that contribute to it. The technology enforces
trust (*Tech Stack*); this document defines the **participatory governance** that
decides *how the commons is run* and *who it serves*.

The governance model exists to honour two constraints from *Overview* that code alone
cannot guarantee: **data sovereignty by default**, and **empowering previously-excluded
orgs/sectors**. It is operationalised in the console's governance surface
(`apps/console/app/governance/`) and the `CommonsProposal` lifecycle
(`apps/console/lib/types.ts`).

---

## 1. Principles

1. **Contribution earns voice.** Those who contribute data, infrastructure, code, or
   stewardship effort get a proportional stake and a vote. The commons is governed by its
   participants, not by a single vendor.
2. **Sovereignty is inviolable.** A contributor never loses control of *their* data by
   joining. Residency, purpose limitation, and revocation are rights, not features.
3. **Transparency by default.** Cost, energy/carbon, access decisions, and governance
   outcomes are visible to participants. Power that cannot be seen cannot be checked.
4. **Open commitments.** Licensing and provenance are explicit, machine-readable, and
   binding — declared in every domain-pack and enforced by the engine.
5. **Equity is a goal, not a side effect.** Governance actively lowers barriers for
   data-poor and excluded participants (see *KPIs*, "Orgs empowered").

---

## 2. Stake and vote — how contributors get a say

A participant's **stake** is earned, not bought. It is a transparent, auditable function of
contribution, capped so no single party can dominate:

| Contribution | What it earns |
|--------------|---------------|
| **Data** contributed to the commons (under an open/declared license) | Stake proportional to *governed usefulness* (quality, lineage coverage, reuse), not raw volume |
| **Infrastructure** run for the mesh (storage, compute, edge/offline nodes) | Stake proportional to capacity served and, for compute, **carbon efficiency** |
| **Stewardship** (curation, quality rules, ontology alignment, pack maintenance) | Stake for sustained, verifiable maintenance |
| **Code** to the OSS core, adapters, or reference packs | Stake for merged, maintained contributions |

Rules that keep stake legitimate:

- **One-org-one-voice flooring.** Every verified participant org — including the smallest,
  newest, data-poor entrant — holds a guaranteed minimum vote, so the commons cannot become
  pay-to-win. This is the mechanism behind the "previously-excluded orgs empowered" KPI.
- **Stake caps.** No single participant may exceed a fixed share of total voting power,
  regardless of contribution size.
- **Quorum + supermajority** thresholds scale with the impact of a proposal (see §3).
- **Conflict recusal.** A participant materially affected by a proposal declares it; their
  vote is weighted/recused per the proposal's rules.

## 3. Proposal lifecycle

All material changes to the commons — onboarding a sector, changing default policy, adjusting
privacy budgets, altering carbon targets, licensing decisions — move through one lifecycle.
It maps directly to the console `CommonsProposal` states (`open → passed | rejected`):

1. **Draft.** Any participant drafts a proposal: title, summary, rationale, affected
   datasets/policies, and the concrete change (often a diff to a domain-pack policy or a
   platform default, never to the locked core).
2. **Review (open).** The proposal opens for discussion and impact assessment. Transparency
   dashboards (§5) show who/what it affects. `CommonsProposal.status = "open"`, with
   `forPct`, `participants`, and `closesIn` tracked live.
3. **Vote.** Stake-weighted vote with one-org-one-voice flooring. Thresholds by impact:
   - *Operational* (e.g. a new connector schedule): simple majority, standard quorum.
   - *Policy/privacy/sovereignty* (e.g. lowering a default ε, changing residency): **higher
     quorum + supermajority**, because they touch participants' rights.
4. **Enact or reject.** A passing proposal becomes a **declarative change** — a domain-pack
   policy update, a config default, a licensing record — applied through the normal swap
   mechanisms. The core engine is never edited (the invariant holds even in governance).
   `status = "passed"` or `"rejected"`, recorded immutably with provenance.
5. **Review & sunset.** Impactful changes carry a scheduled review; reversals follow the same
   lifecycle.

> Privacy and sovereignty are **floor rights, not vote items below the floor.** A proposal may
> make the commons *more* private/sovereign by majority, but *weakening* a participant's
> sovereignty over their own data cannot be imposed on them by vote — it requires that
> participant's explicit consent.

## 4. Data sovereignty

Sovereignty is enforced technically *and* protected procedurally.

- **Residency is enforced by the engine.** Data tagged with a jurisdiction
  (`Jurisdiction.residency_required`) cannot be processed outside its allowed regions — e.g.
  consumer-credit's `deny_processing_outside_eu` policy denies non-EU processing outright,
  deny-overrides everything.
- **Purpose limitation.** Access requires a declared, lawful purpose (e.g. underwriter row
  access only for `purpose == "underwriting"`). Purpose is checked at authorization.
- **Right to revoke / withdraw.** A contributor may withdraw their data or tighten its policy
  through the proposal lifecycle without needing anyone else's permission; downstream
  artifacts are flagged via lineage and provenance.
- **No silent re-purposing.** Any change to how a contributor's data may be used is a
  proposal that the contributor sees and (for their own data) controls.
- **Federation preserves sovereignty.** In cross-org work (Phase 3, *Roadmap*), only
  governed, DP-protected aggregates cross boundaries; raw rows stay in their residency zone,
  and federated learning trains *to* the data rather than moving it.

## 5. Transparency — cost & energy dashboards

Participants can see what the commons costs and emits, and how decisions are made. These are
console surfaces, not reports filed once a year:

- **Carbon dashboard** (`apps/console/app/carbon/`): per-region carbon intensity, greenest
  capable region, carbon-per-query, and savings vs. naive placement — the energy KPI made
  visible.
- **Governance surface** (`apps/console/app/governance/`): the platform charter, live
  proposals, vote progress, and the access-policy catalog.
- **Governed-query log** (console home): every query with principal, region, carbon, and
  privacy (ε spent) — so access is auditable.
- **Cost attribution.** Storage/compute cost attributed to contributors and consumers, so the
  commons' economics are legible and fairly shared.
- **Lineage & quality** (`apps/console/app/lineage/`, catalog): anyone can trace where a
  result came from and how trustworthy its inputs are.

## 6. Licensing & provenance commitments

These commitments are **declared as data in every domain-pack** and enforced by the engine,
so they are not promises — they are policy.

- **Explicit license on everything.** Each dataset and pack carries an SPDX `License` with
  redistribution and commercial-use terms (e.g. climate-emissions under **CC-BY-4.0** with an
  attribution watermark obligation; consumer-credit reference material under **Apache-2.0**
  with synthetic-only data). No dataset enters the commons without a declared license.
- **Attribution enforced as an obligation.** Where a license requires attribution, the engine
  attaches it (e.g. the `watermark` obligation on climate outputs) — attribution travels with
  the artifact.
- **Provenance signed at capture.** Every artifact is provenance-signed (Ed25519 today,
  C2PA-targeted) so its chain of custody is independently verifiable — directly countering
  misinformation and tampering.
- **Open-by-preference, sovereign-by-right.** The commons prefers open licenses to maximise
  reuse, while always honouring a contributor's lawful need to restrict (residency, PII,
  confidentiality). The two coexist because both are *declared* and *enforced* per dataset.

---

## 7. How governance stays inside the invariant

Governance changes the commons by changing **declarative artifacts** — pack policies, config
defaults, licensing/provenance records — applied through the same registry/config swap
mechanisms used for every other change. The core engine
(`engine/aegoria_core/engine.py`), the registry, the config schema, and the contracts are
**not** in scope for any proposal. The commons can re-govern itself completely without ever
forking the engine that makes it trustworthy. That is the invariant, applied to people.
