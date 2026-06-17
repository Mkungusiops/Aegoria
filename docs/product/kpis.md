# Aegoria — Key Performance Indicators

Aegoria commits to a small set of **concrete, continuously-measured KPIs**. Each is a direct
measurement of one of the five problems from *Overview* (fragmentation, quality &
misinformation, surveillance vs. privacy, energy/carbon, inequitable access). Each is also a
**card on the console** (`apps/console/app/page.tsx`, fixtures in
`apps/console/lib/data.ts`), so the platform's own dashboard *is* the scorecard.

For every KPI below: **Definition → Target → How it's measured → Console card** (the
`Kpi.id` / `Kpi.label` it maps to).

> Convention: targets are the platform's *steady-state* commitments. Phase-by-phase ramp is
> in *Roadmap*. Values shown in the console are illustrative fixtures until live
> telemetry is wired; the *definitions and targets* are the contract.

---

## 1. Lineage coverage

- **Attacks:** fragmentation/silos, misinformation.
- **Definition:** the fraction of datasets whose **complete upstream lineage** is recorded —
  every transform and source traceable via `LineageEdge` back to a provenance-signed origin.
- **Target:** **≥ 95%** of datasets with full upstream lineage.
- **How measured:** `datasets_with_full_lineage / total_datasets`, computed from the catalog's
  lineage graph at ingest/transform time. A dataset counts only if every parent edge resolves
  to a known source or another covered dataset.
- **Console card:** `lineage` — "Lineage coverage", target `≥ 95%`, tone *auralis*.

## 2. Data quality

- **Attacks:** quality & misinformation.
- **Definition:** the average pass rate of declared `QualityRule`s (not_null, unique, range,
  regex, enum, freshness) across all datasets, weighted toward `error`-severity rules.
- **Target:** **≥ 0.90** average passing quality rules.
- **How measured:** for each dataset, `passing_rules / total_rules` from the latest
  `QualityReport`; averaged across datasets. `error` failures are gating; `warn` failures are
  reported but non-gating. Run at ingest and on schedule.
- **Console card:** `quality` — "Data quality", target `≥ 0.90`, tone *verdant*.

## 3. Query latency at scale

- **Attacks:** inequitable access (usable performance for everyone), platform viability.
- **Definition:** the **p95 wall-clock latency** of governed queries — measured *after*
  authorization, carbon-aware placement, execution, and obligation enforcement — at
  TB-scale data.
- **Target:** **p95 ≤ 2 s @ TB-scale**, across all compute engines.
- **How measured:** `QueryStats`/`QueryResult` timing per run, aggregated to the 95th
  percentile over a rolling window, bucketed by data scale. Reported per engine and overall.
- **Console card:** `latency` — "Query latency p95", target `≤ 2s @ TB-scale`, tone *ion*.

## 4. Privacy guarantee — (ε,δ)-differential privacy

- **Attacks:** surveillance vs. privacy.
- **Definition:** the **quantified** privacy guarantee applied to aggregate answers over
  sensitive data: an (ε, δ)-differential-privacy bound, with **per-principal budget
  accounting**. This is not a yes/no flag — it is a number with a proof behind it.
- **Target:** **ε ≤ 1.0, δ = 1e-6 by default on PII** (the config defaults in
  `PrivacyDefaults`). Aggregates over sensitive data are answered under DP **100%** of the
  time; no aggregate exceeds its principal's remaining budget.
- **How measured:** the privacy engine applies a DP mechanism (e.g. Laplace) per the
  `differential_privacy` obligation and debits the principal's `PrivacyBudget` (ε spent /
  ε allotted). Compliance = (DP-covered aggregates / total sensitive aggregates) and
  (budget never exceeded). Console rows show ε spent per query.
- **Console card:** `privacy` — "Privacy guarantee", value `ε ≤ 1.0`, target `(ε,δ)-DP
  default`, hint `δ = 1e-6 on PII`, tone *pulse*. Reinforced by the per-query `ε` badge on the
  governed-query table.

## 5. Carbon per query

- **Attacks:** energy/carbon.
- **Definition:** the estimated **gCO₂ emitted per governed query**, and the **reduction vs.
  naive placement** achieved by the carbon-aware scheduler choosing the greenest *capable*
  region.
- **Target:** carbon-per-query trending down; **↓ ≥ 60% vs. naive placement**.
- **How measured:** `energy_kWh × region_gCO2_per_kWh` from the live `CarbonReading` for the
  chosen region, attributed per query (`QueryRun.carbonG`). Savings =
  `1 − (actual_carbon / naive_same_query_carbon)`. Greenest region is surfaced live.
- **Console card:** `carbon` — "Carbon / query", target `↓ 60% vs naive`, tone *verdant*.
  Also the hero "Carbon / query" stat and the carbon-aware-compute gauge.

## 6. New-domain onboarding time

- **Attacks:** fragmentation/silos (this is the headline proof of market-agnosticism).
- **Definition:** elapsed time from **starting a `DomainPackManifest`** to that market being
  **live** (datasets registered, quality + lineage running, governed queries answerable) —
  **with no change to the core engine**.
- **Target:** **≤ 5 days**, manifest → live, no core change.
- **How measured:** timestamp from first manifest commit to first successful governed query
  on the pack's datasets, with a CI assertion that `engine.py`, `registry.py`, `config.py`,
  and the contracts have **zero diffs** for the onboarding. (The two reference packs are the
  calibration baseline.)
- **Console card:** `onboard` — "New-domain onboarding", target `≤ 5 days`, hint `manifest →
  live, no core change`, tone *auralis*.

## 7. Orgs / sectors empowered (previously-excluded participants)

- **Attacks:** inequitable access.
- **Definition:** two related counts:
  - **Orgs empowered** — organisations onboarded onto the platform, with an explicit tally of
    those **previously data-poor / excluded** (no prior access to this class of
    infrastructure).
  - **Sectors live** — distinct unrelated markets running on the *same* core (the breadth
    proof; market-agnostic).
- **Target:** both **trending up**; sectors **≥ 3** (two reference packs + ≥ 1
  community-contributed), with previously-excluded orgs explicitly counted.
- **How measured:** registry of onboarded orgs (with a `previously_excluded` flag set at
  intake) and a distinct count of loaded domain-pack sectors. Reported with the
  data-commons governance records (*Data Commons*).
- **Console cards:** `orgs` — "Orgs empowered", hint `12 previously data-poor`, tone *solar*;
  and `sectors` — "Sectors live", target `market-agnostic`, tone *pulse*. Also the hero "Orgs
  empowered" stat.

---

## KPI → console card map

| KPI | `Kpi.id` | Console label | Target | Tone |
|-----|----------|---------------|--------|------|
| Lineage coverage | `lineage` | Lineage coverage | ≥ 95% | auralis |
| Data quality | `quality` | Data quality | ≥ 0.90 | verdant |
| Query latency p95 | `latency` | Query latency p95 | ≤ 2s @ TB-scale | ion |
| Privacy guarantee | `privacy` | Privacy guarantee | (ε,δ)-DP default (ε ≤ 1.0, δ = 1e-6) | pulse |
| Carbon per query | `carbon` | Carbon / query | ↓ 60% vs naive | verdant |
| New-domain onboarding | `onboard` | New-domain onboarding | ≤ 5 days | auralis |
| Orgs empowered | `orgs` | Orgs empowered | ↑ excluded sectors | solar |
| Sectors live | `sectors` | Sectors live | market-agnostic | pulse |

## Measurement principles

- **Continuous, not milestone-only.** KPIs are computed in CI and surfaced on the console at
  all times; a regression is a release blocker.
- **Two-market validity.** A KPI is only credible if it holds across the two unrelated
  reference packs. A metric that needs per-domain special-casing is not a platform KPI.
- **Fail-safe on privacy.** The privacy KPI is the one KPI that may never be traded off:
  under uncertainty, the platform applies *more* protection (smaller ε / denied query), not
  less, even at the cost of latency or coverage.
