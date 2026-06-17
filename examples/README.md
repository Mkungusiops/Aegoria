# Aegoria examples

End-to-end proof that **one domain-neutral core engine** serves two completely
unrelated markets — `climate-emissions` (open environmental geodata) and
`consumer-credit` (sensitive, EU-resident PII) — purely by loading their
declarative domain-packs. No core code changes between markets.

## `e2e_demo.py`

A narrated, top-to-bottom run against a throwaway temp warehouse. It uses the
engine's **public API only** (`AegoriaEngine.bootstrap / .ingest / .query /
.catalog / .health` plus the resolved services), and prints numbered sections:

1. **Bootstrap** — discover providers from the registry, wire services, load
   both domain-packs from their manifests.
2. **Ingest** — capture multi-modal sample data for both markets into the
   Iceberg lakehouse, with a cryptographic provenance signature attached at the
   moment of capture.
3. **Climate query** — a governed open-data aggregate, placed by the
   carbon-aware scheduler on the **greenest** available region, with carbon
   grams accounted.
4. **Consumer-credit query** —
   - **(4a)** a governed aggregate **under differential privacy**: epsilon is
     spent and recorded against the privacy budget, and PII columns are masked;
   - **(4b)** a raw row-level PII `SELECT` is **DENIED** by governance.
5. **Provenance** — show a dataset's lineage edges and verify a C2PA-style
   content signature (including that tampering is rejected).
6. **KPI summary** — rows, quality, carbon/query and latency per dataset.

### Run it

```bash
/Users/jeff/Code/Aegoria/engine/.venv/bin/python \
    /Users/jeff/Code/Aegoria/examples/e2e_demo.py
```

The demo regenerates each pack's deterministic sample data on first run (via the
packs' own `sample_data/gen_sample.py`) and prints the path to the temp
warehouse it used. Nothing is written outside that temp directory and the packs'
`sample_data/` folders.

## Tests

The same flows are asserted under pytest:

```bash
/Users/jeff/Code/Aegoria/engine/.venv/bin/pytest /Users/jeff/Code/Aegoria/engine/tests -q
```

- `test_e2e.py` — both domains ingest > 0 rows, provenance attached, climate
  query is carbon-aware, consumer-credit aggregate runs under DP with epsilon
  spent + PII masked, raw PII select denied, lineage edges exist, signature
  verifies.
- `test_domain_neutrality.py` — **the key test**: a single, branchless helper
  serves both markets, and loading either pack performs zero edits to core
  (provider topology and core source are byte-stable across both markets).
- `test_contracts.py` — every default service satisfies its `SERVICE_PROTOCOLS`
  protocol and every configured adapter resolves and satisfies its adapter
  protocol after bootstrap.

## Note for integrators (consumer-credit governance)

The consumer-credit pack ships a `deny_processing_outside_eu` policy intended to
deny **only** when `principal.jurisdiction != "EU"`. The reference
`DefaultGovernance` (`engine/aegoria_core/services/governance.py`,
`_evaluate_policies`, ~lines 240–260) does **not** yet evaluate the
`AccessPolicySpec.condition` expression, so this policy currently denies *every*
consumer-credit access regardless of jurisdiction.

The demo and tests embrace this as the correct privacy-first DENY posture for
section 4b, and exercise the genuine engine DP + masking machinery
(`scheduler.execute` enforcing the manifest's `differential_privacy` + `mask`
obligations) for the ALLOW path in 4a — no example-local privacy logic is added.
Once `condition` evaluation lands in governance, the 4a path can be driven
straight through `engine.query()` with an EU analyst principal.
