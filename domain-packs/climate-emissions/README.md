# Climate & Emissions — Aegoria Domain-Pack

A **manifest-first** reference domain-pack for Aegoria. It onboards a complete
greenhouse-gas / air-quality market *declaratively* — schemas, ontology,
semantic mappings, quality rules, ingestion connectors, ML model references and
default access policy all live in [`manifest.yaml`](./manifest.yaml). The core
engine loads this pack; the core engine never changes.

This is one of two deliberately **unrelated** reference packs shipped to prove
Aegoria is market-agnostic. It exercises four modalities end-to-end:
`time_series`, `geospatial`, `imagery` and `sensor_stream`.

## Datasets

| Dataset | Modality | Key fields | Sample |
| --- | --- | --- | --- |
| `facility_emissions` | `time_series` | `facility_id`, `geom` (POINT), `co2e_tonnes`, `observed_at`, `operator` | `sample_data/facility_emissions.parquet` |
| `sentinel_plumes` | `imagery` / `geospatial` | `tile_id`, `geom` (POLYGON), `ch4_ppb`, `captured_at` | `sample_data/sentinel_plumes.parquet` |
| `ground_sensors` | `sensor_stream` | `sensor_id`, `pm25`, `co2_ppm`, `ts` | `sample_data/ground_sensors.csv` |

Geometries are carried as WKT strings in EPSG:4326. All datasets are licensed
**CC-BY-4.0**; `sentinel_plumes` is scoped to the **EU** jurisdiction, the others
to **GLOBAL**.

## Ontology & semantics

Five terms — `Facility`, `Emission`, `CO2e`, `Region`, `Sensor` — are aligned to
external standards (SOSA/SSN, QUDT, schema.org, W3C WGS84) via `same_as` URIs.
`semantic_mappings` link every dataset field to a term, so raw columns gain
meaning and become interoperable across packs.

## Quality rules

Declarative rules per dataset cover:

- `not_null` on identity and timestamp fields,
- `range` ensuring `co2e_tonnes >= 0`, `ch4_ppb >= 0`, `pm25 >= 0` and a
  plausible CO2 ppm band,
- `freshness` bounds appropriate to each cadence (30 d / 14 d / 1 h).

## Connectors

File connectors for `parquet`, `csv` and `geojson` targeting each dataset; the
`ground_sensors` CSV connector carries a `*/5 * * * *` schedule hint for
streaming-style polling.

## Models

Three per-domain `ModelSpec` references the generic ML service can load:

- `emission_spike_anomaly` — robust z-score on `co2e_tonnes`, grouped by facility,
- `methane_plume_anomaly` — robust z-score on `ch4_ppb`,
- `emission_forecast` — seasonal-naive forecast of `co2e_tonnes`.

## Access policy

`open_read_watermarked` grants open public read/query/aggregate access to all
pack datasets with a **watermark** obligation for attribution. A companion
policy denies anonymous bulk export (aggregate access only).

## Optional Python hooks

[`pack.py`](./pack.py) is **optional**. A fully declarative deployment needs only
the manifest. The hooks provide generic, dependency-light implementations bound
to the `DomainPack` protocol:

- `connectors()` — PyArrow readers for Parquet / CSV / GeoJSON,
- `models()` — pure-NumPy robust-z-score anomaly detector and seasonal-naive
  forecaster, parameterized entirely by the manifest.

The pack self-registers via `@domain_pack("climate-emissions")` on import.

## Sample data

[`sample_data/gen_sample.py`](./sample_data/gen_sample.py) generates small,
**deterministic** synthetic samples (fixed NumPy seed) for each dataset, with a
few injected emission/plume spikes for the anomaly demos.

```bash
/Users/jeff/Code/Aegoria/engine/.venv/bin/python \
    domain-packs/climate-emissions/sample_data/gen_sample.py
```

Approximate sizes: `facility_emissions` ~2,880 rows, `sentinel_plumes` ~2,400
rows, `ground_sensors` ~2,880 rows.

## Verify

```bash
# Manifest validates against the contract
/Users/jeff/Code/Aegoria/engine/.venv/bin/python -c \
  "from aegoria_core.contracts.domain_pack import DomainPackManifest as M; \
   m=M.from_yaml('domain-packs/climate-emissions/manifest.yaml'); \
   print('pack', m.id, 'datasets', [d.name for d in m.datasets])"

# Regenerate sample data
/Users/jeff/Code/Aegoria/engine/.venv/bin/python \
  domain-packs/climate-emissions/sample_data/gen_sample.py
```
