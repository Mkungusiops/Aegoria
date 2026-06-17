# Consumer Credit — Aegoria domain-pack

A privacy-first reference domain for **retail lending**: who applies for credit,
how they are adjudicated, and how funded accounts behave over time. It is the
second Aegoria reference pack and is deliberately unlike the climate pack — it is
structured + PII + financial, governed by EU data-protection law. The *only*
thing the two packs share is the manifest format. The Aegoria core never changes
to accommodate either of them.

> **All bundled data is synthetic.** Names are `Test User <n>`, national ids are
> `SYN-…`, emails use the reserved `example.test` domain. Nothing here is real
> personal data.

## What's in the box

| File | Purpose |
| --- | --- |
| `manifest.yaml` | The entire declarative pack: schemas, ontology, quality, connectors, models, **and policy**. |
| `sample_data/gen_sample.py` | Deterministic synthetic-data generator (fixed NumPy seed) → CSV + Parquet. |
| `pack.py` | Optional NumPy-only hooks behind the two model references (fair risk score, delinquency forecast). |

### Datasets

* **`loan_applications`** (structured) — one row per application:
  `application_id`, `applicant_name` *(PII)*, `national_id` *(PII)*,
  `email` *(PII)*, `income` *(financial)*, `amount` *(financial)*,
  `decision` *(confidential)*.
* **`repayment_history`** (time series) — monthly servicing snapshots:
  `account_id`, `month`, `balance` *(financial)*, `days_past_due`
  *(confidential)*. Pseudonymous: keyed by account, not by person.

Both datasets declare `jurisdiction: EU`, `regulations: [GDPR, ECOA]`, and
`residency_required: true`.

## Privacy & sovereignty are *manifest data*, not code

The headline claim of Aegoria is that a market onboards declaratively. This pack
proves it for the hardest case — regulated, personal financial data — without a
single line of engine change. Every protection below lives in `manifest.yaml`
and is enforced by the core's governance service through its standard
obligations (`mask`, `differential_privacy`, `aggregate_only`, `residency`):

1. **Data residency / sovereignty (`deny_processing_outside_eu`).**
   A `deny` rule on `datasets: ["*"]` with `condition:
   principal.jurisdiction != "EU"` and a `residency` obligation. Because policy
   evaluates *deny-overrides*, no later `allow` can move EU-resident credit data
   out of the EU. Cross-border processing is structurally impossible.

2. **Mask PII unless you own the record (`mask_pii_unless_owner`).**
   The default for everyone — underwriters, support, analysts, auditors — is a
   `mask` obligation over `applicant_name`, `national_id`, `email`. Raw
   identifiers are revealed only when `principal.subject == resource.owner`
   (the data subject themselves). PII is masked *by default*, not by exception.

3. **Differential privacy on every aggregate (`dp_on_aggregates`).**
   Aggregate/query access carries a `differential_privacy` obligation with
   `epsilon: 1.0`, `delta: 1e-6`, Laplace mechanism. The core's privacy-budget
   accounting (`PrivacyBudget`) tracks spend per principal; the pack simply
   declares the budget.

4. **Analysts are aggregate-only (`analysts_aggregate_only`).**
   A `deny` on `read`/`sample`/`export` for the `analyst` role, paired with an
   `aggregate_only` obligation (`min_group_size: 25`). Analysts can learn
   population-level facts, never individual ones.

5. **Lawful-purpose row access (`underwriter_row_access`).**
   Underwriters may read row-level applications, but only when
   `principal.attributes.purpose == "underwriting"` — and still subject to the
   residency and mask rules above.

The default privacy posture is also restated in `metadata`
(`privacy_posture: privacy-first-by-default`, default `epsilon`/`delta`,
`sovereignty.cross_border_transfers: prohibited`) so the catalog can surface it.

### Fairness

The `fair_risk_scorer` model declares `protected_attributes:
[applicant_name, national_id, email]` and a `demographic_parity` target with a
`0.05` tolerance. `pack.py` enforces this in code too: the scorer accepts only
the safe financial features and raises if any protected attribute is passed in.

## Ontology & interoperability

Five local terms — `cc:Borrower`, `cc:Application`, `cc:Income`, `cc:Account`,
`cc:Delinquency` — are each `same_as` an external **FIBO** (Financial Industry
Business Ontology) URI, with `schema.org/Person` as an extra alias for the
borrower. `semantic_mappings` bind raw columns to those terms, so a credit
`Borrower` is interoperable with any other FIBO-aware system without the core
knowing what a borrower is.

## Generating the sample data

```bash
/Users/jeff/Code/Aegoria/engine/.venv/bin/python \
  /Users/jeff/Code/Aegoria/domain-packs/consumer-credit/sample_data/gen_sample.py
```

This writes `loan_applications.{csv,parquet}` and
`repayment_history.{csv,parquet}` into `sample_data/`. Output is reproducible
(fixed seed `20260617`): ~4,000 applications and twelve monthly snapshots for
each funded account.

## Validating the manifest

```bash
/Users/jeff/Code/Aegoria/engine/.venv/bin/python -c \
"from aegoria_core.contracts.domain_pack import DomainPackManifest as M; \
m=M.from_yaml('domain-packs/consumer-credit/manifest.yaml'); \
print(m.id, [f.name for d in m.datasets for f in d.schema_.fields if f.pii])"
```
