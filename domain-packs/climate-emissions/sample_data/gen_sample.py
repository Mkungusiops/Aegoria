#!/usr/bin/env python
"""Generate small, deterministic synthetic sample data for the climate-emissions pack.

Each of the three pack datasets gets a sample file shaped exactly like its
declared schema in ``manifest.yaml``:

  * facility_emissions -> Parquet (time_series)
  * sentinel_plumes    -> Parquet (imagery / geospatial)
  * ground_sensors     -> CSV     (sensor_stream)

The data is purely synthetic and reproducible: a single fixed NumPy seed drives
every value, so re-running this script byte-stably regenerates the same samples.
The generators deliberately inject a few emission/plume spikes so the pack's
anomaly model references have something to detect in demos.

Run with the engine venv::

    /Users/jeff/Code/Aegoria/engine/.venv/bin/python \
        /Users/jeff/Code/Aegoria/domain-packs/climate-emissions/sample_data/gen_sample.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq

SEED = 20260617
OUT_DIR = Path(__file__).resolve().parent

# Deterministic reference epoch so timestamps are stable across runs.
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)

N_FACILITIES = 24
N_FACILITY_DAYS = 120          # ~24 * 120 = 2,880 emission rows
N_TILES = 40
N_TILE_CAPTURES = 60           # 40 * 60 = 2,400 plume rows
N_SENSORS = 30
N_SENSOR_STEPS = 96            # 30 * 96 = 2,880 sensor rows (every 15 min over a day)


def _wkt_point(lon: float, lat: float) -> str:
    return f"POINT ({lon:.6f} {lat:.6f})"


def _wkt_box(lon: float, lat: float, size: float = 0.1) -> str:
    """Axis-aligned square polygon footprint around (lon, lat)."""
    x0, y0, x1, y1 = lon, lat, lon + size, lat + size
    ring = f"{x0:.6f} {y0:.6f}, {x1:.6f} {y0:.6f}, {x1:.6f} {y1:.6f}, {x0:.6f} {y1:.6f}, {x0:.6f} {y0:.6f}"
    return f"POLYGON (({ring}))"


def gen_facility_emissions(rng: np.random.Generator) -> pa.Table:
    """Per-facility CO2e daily time series with a handful of injected spikes."""
    facility_ids: list[str] = []
    geoms: list[str] = []
    co2e: list[float] = []
    observed_at: list[datetime] = []
    operators: list[str] = []

    operator_pool = [f"operator-{chr(ord('A') + i)}" for i in range(6)]

    for f in range(N_FACILITIES):
        fid = f"FAC-{f:04d}"
        lon = float(rng.uniform(-120.0, 30.0))
        lat = float(rng.uniform(-40.0, 60.0))
        geom = _wkt_point(lon, lat)
        operator = operator_pool[f % len(operator_pool)]
        baseline = float(rng.uniform(50.0, 900.0))
        # A weekly seasonal component plus noise.
        for d in range(N_FACILITY_DAYS):
            ts = EPOCH + timedelta(days=d)
            seasonal = 1.0 + 0.15 * np.sin(2.0 * np.pi * (d % 7) / 7.0)
            value = baseline * seasonal + float(rng.normal(0.0, baseline * 0.05))
            # Inject occasional positive spikes (anomalies).
            if rng.random() < 0.01:
                value *= float(rng.uniform(2.5, 4.0))
            facility_ids.append(fid)
            geoms.append(geom)
            co2e.append(round(max(0.0, value), 3))
            observed_at.append(ts)
            operators.append(operator)

    return pa.table(
        {
            "facility_id": pa.array(facility_ids, pa.string()),
            "geom": pa.array(geoms, pa.string()),
            "co2e_tonnes": pa.array(co2e, pa.float64()),
            "observed_at": pa.array(observed_at, pa.timestamp("us", tz="UTC")),
            "operator": pa.array(operators, pa.string()),
        }
    )


def gen_sentinel_plumes(rng: np.random.Generator) -> pa.Table:
    """Satellite CH4 plume detections per imagery tile, with footprint polygons."""
    tile_ids: list[str] = []
    geoms: list[str] = []
    ch4: list[float] = []
    captured_at: list[datetime] = []

    for t in range(N_TILES):
        tid = f"S5P-{t:05d}"
        lon = float(rng.uniform(-120.0, 30.0))
        lat = float(rng.uniform(-40.0, 60.0))
        geom = _wkt_box(lon, lat, size=0.1)
        baseline = float(rng.uniform(1800.0, 1950.0))  # ~global CH4 background in ppb
        for c in range(N_TILE_CAPTURES):
            ts = EPOCH + timedelta(hours=12 * c)
            enhancement = float(rng.normal(0.0, 15.0))
            value = baseline + enhancement
            if rng.random() < 0.02:  # a plume event
                value += float(rng.uniform(200.0, 800.0))
            tile_ids.append(tid)
            geoms.append(geom)
            ch4.append(round(max(0.0, value), 3))
            captured_at.append(ts)

    return pa.table(
        {
            "tile_id": pa.array(tile_ids, pa.string()),
            "geom": pa.array(geoms, pa.string()),
            "ch4_ppb": pa.array(ch4, pa.float64()),
            "captured_at": pa.array(captured_at, pa.timestamp("us", tz="UTC")),
        }
    )


def gen_ground_sensors(rng: np.random.Generator) -> pa.Table:
    """High-frequency PM2.5 / CO2 ground sensor readings (15-minute cadence)."""
    sensor_ids: list[str] = []
    pm25: list[float] = []
    co2_ppm: list[float] = []
    ts_list: list[datetime] = []

    for s in range(N_SENSORS):
        sid = f"SEN-{s:04d}"
        pm_base = float(rng.uniform(5.0, 35.0))
        co2_base = float(rng.uniform(400.0, 700.0))
        for step in range(N_SENSOR_STEPS):
            ts = EPOCH + timedelta(minutes=15 * step)
            # Diurnal cycle for CO2 + PM, peaking around commute hours.
            hour = (ts.hour + ts.minute / 60.0)
            diurnal = 1.0 + 0.3 * np.sin(2.0 * np.pi * (hour - 8.0) / 24.0)
            pm = pm_base * diurnal + float(rng.normal(0.0, 2.0))
            co2 = co2_base * diurnal + float(rng.normal(0.0, 20.0))
            sensor_ids.append(sid)
            pm25.append(round(max(0.0, pm), 3))
            co2_ppm.append(round(max(0.0, co2), 3))
            ts_list.append(ts)

    return pa.table(
        {
            "sensor_id": pa.array(sensor_ids, pa.string()),
            "pm25": pa.array(pm25, pa.float64()),
            "co2_ppm": pa.array(co2_ppm, pa.float64()),
            "ts": pa.array(ts_list, pa.timestamp("us", tz="UTC")),
        }
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    # Order matters for determinism: each generator draws from the same stream.
    fe = gen_facility_emissions(rng)
    sp = gen_sentinel_plumes(rng)
    gs = gen_ground_sensors(rng)

    fe_path = OUT_DIR / "facility_emissions.parquet"
    sp_path = OUT_DIR / "sentinel_plumes.parquet"
    gs_path = OUT_DIR / "ground_sensors.csv"

    pq.write_table(fe, fe_path, compression="snappy")
    pq.write_table(sp, sp_path, compression="snappy")
    pa_csv.write_csv(gs, gs_path)

    print(f"wrote {fe_path.name}: {fe.num_rows} rows")
    print(f"wrote {sp_path.name}: {sp.num_rows} rows")
    print(f"wrote {gs_path.name}: {gs.num_rows} rows")


if __name__ == "__main__":
    main()
