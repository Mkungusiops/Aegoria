# Aegoria SDK — onboard a brand-new market in under a day

`aegoria-sdk` is the authoring toolchain for **domain-packs**: the declarative
plugins through which a new market joins the Aegoria lakehouse. The promise of
Aegoria is that **the core engine never changes** when you add a market — you ship
a pack (mostly YAML), the engine loads it, done. This SDK is how you write, check
and test that pack with confidence.

A domain-pack is *data*. The SDK never imports a concrete storage/compute/catalog
backend; it speaks only the frozen `aegoria_core` contracts, exactly like the
engine does. So a pack you validate here is a pack the engine can load anywhere.

---

## Install

The SDK depends on `aegoria-core`. In the engine virtualenv:

```bash
# from repo root, with the engine venv active
pip install -e ./sdk          # installs the `aegoria-pack` command
```

The quality-test harness reads sample data through `pyarrow`, which ships with the
engine's `lite` extra (already installed in the dev venv). If you install the SDK
standalone for pack CI, add the `testkit` extra: `pip install "aegoria-sdk[testkit]"`.

Verify the command is on your path:

```bash
aegoria-pack --version
```

---

## The 5-step onboarding

### 1. Scaffold a pack (1 minute)

```bash
aegoria-pack new climate-emissions \
  --name "Climate Emissions" \
  --maintainer "you@market.org"
```

This creates an **already-valid, already-tested** skeleton:

```
climate-emissions/
  manifest.yaml                          # the declarative onboarding document
  sample_data/climate-emissions-records.csv
  README.md                              # pack-local quickstart
```

Add `--hooks` to also emit `pack.py` with registration + optional code-hook stubs
(only needed when a connector/model requires real Python — most packs stay pure
YAML). Pick a `--modality` other than `structured` (e.g. `time_series`,
`geospatial`, `imagery`) for the seed dataset if that fits your market.

### 2. Model your market in `manifest.yaml` (most of the day)

The manifest is the whole onboarding. You edit declarations, not code:

- **`datasets`** — each with a `schema` (fields, types, `sensitivity`, `pii`,
  `primary_key`, `partition_by`), a `license`, a `jurisdiction`, `quality_rules`,
  and a `sample_data` path. The schema is domain-*neutral*; meaning is attached
  separately (next bullet), which is what lets the core treat every market alike.
- **`ontology`** — the concepts your market reasons about (`OntologyTerm`), each
  optionally `same_as` an external standard (FIBO, QUDT, schema.org) for
  interoperability.
- **`semantic_mappings`** — bind a dataset field to an ontology term. This is how
  raw columns gain meaning and join across domains.
- **`connectors`** — declare the ingestion sources the pack knows how to read
  (`format`, `options`, `target_dataset`).
- **`models`** — references to per-domain ML models (anomaly/forecast/verify).
- **`access_policies`** — default ABAC/RBAC policy with obligations
  (masking, differential privacy, residency). Sovereignty + privacy as defaults.

Mark sensitive fields explicitly:

```yaml
fields:
  - name: facility_owner
    type: string
    sensitivity: pii
    pii: true        # so the platform applies masking / DP obligations
```

### 3. Validate continuously (instant feedback)

```bash
aegoria-pack validate climate-emissions     # hard structural checks
aegoria-pack lint climate-emissions         # + best-practice advisories
aegoria-pack info climate-emissions         # human summary of the pack
```

`validate` runs the invariants the engine assumes at load time and exits non-zero
on any error:

- dataset names unique; field names unique within a dataset;
- ids unique across ontology / connectors / models / policies;
- every `semantic_mapping` resolves to a real dataset + field (+ ontology term);
- every `connector.target_dataset` and `model.target_dataset` exists;
- every quality rule's `field` exists in its dataset schema;
- `primary_key` / `partition_by` reference real fields;
- `core_compat` is a parseable version specifier.

`lint` adds non-blocking advisories — missing descriptions, datasets without
quality gates, PII not flagged, unmapped fields, policies that match no dataset.
Add `--strict` to fail on warnings too, and `--json` for machine output.

### 4. Test sample data against your quality gates (CI)

The same checks run programmatically, so a pack repo can gate merges without
standing up any infrastructure:

```python
# tests/test_pack.py  (in your pack repo)
from aegoria_sdk import run_pack_quality_gates

def test_quality_gates_pass():
    result = run_pack_quality_gates("climate-emissions", require_sample=True)
    assert result.passed, result.render()
```

The harness reads each dataset's `sample_data` into Arrow and evaluates every
declared `QualityRule` (`not_null`, `unique`, `range`, `regex`, `enum`,
`freshness`, `referential`). `custom` kinds are deferred to your pack's own code
hook. This is the recommended CI gate because it runs anywhere the SDK installs.

For an end-to-end check against real infra (when your deployment's adapters are
installed), the harness can build a throwaway, isolated engine that loads *only*
your pack:

```python
from aegoria_sdk import PackTestHarness

engine = PackTestHarness.from_path("climate-emissions").bootstrap_engine()
if engine is not None:                 # None when providers aren't wired yet
    meta = engine.ingest(domain="climate-emissions", connector="...",
                         source_uri="...", dataset="climate-emissions-records")
```

`bootstrap_engine` redirects the warehouse + catalog under a temp dir, so tests
never touch a developer's real lakehouse, and returns `None` (rather than failing)
when the concrete providers aren't available — your structural gates still run.

### 5. Ship it

Drop the pack directory into a path the engine's `AegoriaConfig.domain_pack_paths`
scans (default `./domain-packs`), or — for a pack with code hooks — publish it as a
package advertising an `aegoria.providers` entry point. The engine discovers and
loads it on `AegoriaEngine.bootstrap()`. **No core-engine change required.**

---

## CLI reference

| Command | Purpose |
| --- | --- |
| `aegoria-pack new <id>` | Scaffold a new, already-valid pack skeleton. |
| `aegoria-pack validate <path>` | Hard structural checks. Exit 1 on errors. |
| `aegoria-pack lint <path>` | Validate + best-practice advisories. |
| `aegoria-pack info <path>` | Human summary of what a pack declares. |

`<path>` may be a pack directory or a `manifest.yaml` file. `validate`/`lint`
accept `--strict` (warnings fail) and every command accepts `--json`.

## Python API

```python
from aegoria_sdk import (
    scaffold_pack,        # generate a pack skeleton
    validate_manifest,    # structural checks on a loaded DomainPackManifest
    validate_path,        # load + validate (or lint) a manifest file
    lint_manifest,        # validate + advisories
    PackTestHarness,      # spin a context to test one pack
    run_pack_quality_gates,
)
```

`validate_*` return a `ValidationReport` whose `.ok` is `True` when there are no
blocking errors and whose `.render()` produces a CI-friendly log. The harness
returns a `HarnessResult` with `.passed`, `.score`, and `.render()`.

---

## Why this keeps the core invariant intact

Everything market-specific is in the manifest; everything infra-specific is in
adapters. The SDK only reads and writes manifests and evaluates declared rules
against the core's own data vocabulary. Adding a market is authoring data and
running these checks — never editing `engine.py`, `registry.py`, the contracts, or
any adapter. That is the mechanical guarantee behind "the core engine never
changes."
