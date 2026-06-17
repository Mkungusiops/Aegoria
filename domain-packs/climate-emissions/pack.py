"""Optional Python hooks for the climate-emissions domain-pack.

The pack is **manifest-first**: ``manifest.yaml`` is the contract and a fully
declarative deployment needs nothing here. This module ships a few *generic*,
dependency-light hooks that bind to the same ``DomainPack`` protocol the core
expects (see ``aegoria_core.contracts.domain_pack.DomainPack``):

  * ``connectors()`` — id -> callable producing PyArrow tables from file sources
    (Parquet / CSV / GeoJSON), one per connector declared in the manifest.
  * ``models()``     — id -> loaded model object. Here a small, pure-NumPy
    robust-z-score anomaly detector and a seasonal-naive forecaster, mirroring
    the ``ModelSpec`` references in the manifest.

Nothing here is climate-specific in its mechanics: the connectors are format
readers and the models are statistical primitives parameterized entirely by the
manifest's ``params``. The market meaning lives in the manifest, not the code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import numpy as np

try:  # PyArrow is provided by the engine's `lite` extra.
    import pyarrow as pa
    import pyarrow.csv as pa_csv
    import pyarrow.parquet as pq
except ModuleNotFoundError:  # pragma: no cover - defensive; manifest still loads.
    pa = None  # type: ignore

from aegoria_core.contracts.domain_pack import DomainPackManifest
from aegoria_core.registry import domain_pack

PACK_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = PACK_DIR / "manifest.yaml"


# --------------------------------------------------------------------------- #
# Connectors — generic file readers returning PyArrow tables.
# --------------------------------------------------------------------------- #
def _read_parquet(uri: str, **_: Any) -> "pa.Table":
    return pq.read_table(uri)


def _read_csv(uri: str, **options: Any) -> "pa.Table":
    read_opts = pa_csv.ReadOptions(use_threads=True)
    delimiter = options.get("delimiter", ",")
    parse_opts = pa_csv.ParseOptions(delimiter=delimiter)
    return pa_csv.read_csv(uri, read_options=read_opts, parse_options=parse_opts)


def _read_geojson(uri: str, *, geometry_field: str = "geom", **_: Any) -> "pa.Table":
    """Flatten a GeoJSON FeatureCollection into columnar form.

    Geometry is carried as a WKT-ish string in ``geometry_field`` (consistent
    with the manifest's geometry columns); all feature ``properties`` become
    top-level columns. Kept deliberately minimal — no GIS dependency required.
    """
    doc = json.loads(Path(uri).read_text())
    features = doc.get("features", []) if isinstance(doc, dict) else []
    rows: list[dict[str, Any]] = []
    for feat in features:
        props = dict(feat.get("properties", {}) or {})
        geom = feat.get("geometry")
        props[geometry_field] = json.dumps(geom) if geom is not None else None
        rows.append(props)
    return pa.Table.from_pylist(rows)


_FORMAT_READERS: dict[str, Callable[..., "pa.Table"]] = {
    "parquet": _read_parquet,
    "csv": _read_csv,
    "geojson": _read_geojson,
}


def _make_connector(fmt: str, options: dict[str, Any]) -> Callable[[str], "pa.Table"]:
    reader = _FORMAT_READERS[fmt]

    def _connector(source_uri: str, **overrides: Any) -> "pa.Table":
        merged = {**options, **overrides}
        return reader(source_uri, **merged)

    return _connector


# --------------------------------------------------------------------------- #
# Models — pure-NumPy statistical primitives, parameterized by the manifest.
# --------------------------------------------------------------------------- #
class RobustZScoreAnomalyDetector:
    """Median/MAD robust z-score outlier flagger.

    Generic over any numeric column; optionally grouped (e.g. per facility). A
    point is anomalous when its modified z-score exceeds ``threshold``. Robust to
    the very spikes it is meant to detect (unlike mean/std z-scores).
    """

    def __init__(self, *, field: str, threshold: float = 3.5, group_by: Optional[str] = None) -> None:
        self.field = field
        self.threshold = float(threshold)
        self.group_by = group_by

    @staticmethod
    def _modified_z(values: np.ndarray) -> np.ndarray:
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        if mad == 0:
            # Fall back to std-based scaling when the MAD collapses.
            std = values.std()
            if std == 0:
                return np.zeros_like(values, dtype=float)
            return (values - values.mean()) / std
        return 0.6745 * (values - median) / mad

    def score(self, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return one record per input row with its score and anomaly flag."""
        rows = list(rows)
        if not rows:
            return []
        values = np.asarray([float(r[self.field]) for r in rows], dtype=float)
        scores = np.zeros(len(values), dtype=float)
        if self.group_by is not None:
            groups: dict[Any, list[int]] = {}
            for i, r in enumerate(rows):
                groups.setdefault(r.get(self.group_by), []).append(i)
            for idx in groups.values():
                scores[idx] = self._modified_z(values[idx])
        else:
            scores = self._modified_z(values)
        out: list[dict[str, Any]] = []
        for r, z in zip(rows, scores):
            out.append({**r, "anomaly_score": float(z), "is_anomaly": bool(abs(z) > self.threshold)})
        return out


class SeasonalNaiveForecaster:
    """Seasonal-naive forecaster: future = last observed value (per group).

    A deliberately simple, dependency-free baseline that the platform's generic
    ML service can call uniformly. ``horizon`` future steps are emitted per group.
    """

    def __init__(self, *, field: str, horizon: int = 7, group_by: Optional[str] = None) -> None:
        self.field = field
        self.horizon = int(horizon)
        self.group_by = group_by

    def forecast(self, rows: Iterable[dict[str, Any]]) -> dict[Any, list[float]]:
        rows = list(rows)
        last: dict[Any, float] = {}
        for r in rows:
            key = r.get(self.group_by) if self.group_by is not None else "__all__"
            last[key] = float(r[self.field])
        return {key: [val] * self.horizon for key, val in last.items()}


def _build_model(task: str, params: dict[str, Any]) -> Any:
    if task == "anomaly":
        return RobustZScoreAnomalyDetector(
            field=params.get("field", "value"),
            threshold=float(params.get("threshold", 3.5)),
            group_by=params.get("group_by"),
        )
    if task == "forecast":
        return SeasonalNaiveForecaster(
            field=params.get("field", "value"),
            horizon=int(params.get("horizon", 7)),
            group_by=params.get("group_by"),
        )
    raise ValueError(f"unsupported model task {task!r}")


# --------------------------------------------------------------------------- #
# DomainPack implementation — manifest + optional hooks.
# --------------------------------------------------------------------------- #
class ClimateEmissionsPack:
    """Runtime view of the climate-emissions pack (satisfies ``DomainPack``)."""

    def __init__(self, manifest: Optional[DomainPackManifest] = None) -> None:
        self._manifest = manifest or DomainPackManifest.from_yaml(MANIFEST_PATH)

    @property
    def manifest(self) -> DomainPackManifest:
        return self._manifest

    def connectors(self) -> dict[str, Callable[[str], Any]]:
        """id -> callable(source_uri) -> pa.Table, one per manifest connector."""
        out: dict[str, Callable[[str], Any]] = {}
        for spec in self._manifest.connectors:
            if spec.format not in _FORMAT_READERS:
                continue
            out[spec.id] = _make_connector(spec.format, spec.options)
        return out

    def models(self) -> dict[str, Any]:
        """id -> loaded model object, one per manifest ModelSpec."""
        return {m.id: _build_model(m.task, m.params) for m in self._manifest.models}

    def custom_quality(self) -> dict[str, Any]:
        """No bespoke quality checks — the manifest's declarative rules suffice."""
        return {}


@domain_pack("climate-emissions")
def make_pack(**_: Any) -> ClimateEmissionsPack:
    """Factory the registry calls to construct the pack (self-registers on import)."""
    return ClimateEmissionsPack()
