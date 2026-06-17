"""Data assessment / profiling — *what is wrong with this data, and how to fix it*.

Profiles every column (types, completeness, distinctness, formatting, outliers),
detects PII by **reusing the engine's governance trust-fabric** (so the same
classifier that guards queries also guards onboarding), scores quality, and emits
a recommended :class:`CleaningPlan`. Pure and dependency-light: it reads an
already-capped Arrow table into Python lists and reasons over them.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import numpy as np
import pyarrow as pa

from ..contracts.models import (
    DatasetMetadata,
    DatasetRef,
    FieldSchema,
    FieldType,
    Modality,
    Sensitivity,
    TableSchema,
)
from .cleanser import _row_key, derive_plan
from .models import AssessmentReport, ColumnProfile

# Sentinels that mean "missing" but are stored as text.
_NULL_SENTINELS = {"", "na", "n/a", "null", "none", "nan", "-", "--", "?", "."}

_INT_RE = re.compile(r"^[-+]?\d+$")
_FLOAT_RE = re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$")
_BOOL_VALUES = {"true", "false", "t", "f", "yes", "no", "y", "n", "0", "1"}
_UNIT_RE = re.compile(r"^\s*[-+]?\d+(?:\.\d+)?\s*([A-Za-z%][A-Za-z%/]*)\s*$")

# Always-on PII heuristics so detection NEVER fails open (governance, when present,
# augments these). Mirrors the engine's governance classifier vocabulary.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)")
_NATIONAL_ID_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_NAME_HINTS = ("name", "first_name", "last_name", "full_name", "surname", "given_name")
_PII_NAME_HINTS = ("email", "phone", "ssn", "national_id", "passport", "address", "dob", "birth")
_PHI_NAME_HINTS = ("diagnosis", "icd", "mrn", "patient", "medical", "health", "treatment")
_SENS_ORDER = {"public": 0, "internal": 1, "confidential": 2, "financial": 3, "pii": 4, "phi": 5,
               "restricted": 6}


def assess(
    table: pa.Table,
    *,
    dataset: str,
    source: str,
    connector: str,
    governance: Any = None,
    row_estimate: int = 0,
    truncated: bool = False,
    sample_for_pii: int = 200,
) -> AssessmentReport:
    """Profile ``table`` and return a full assessment with a recommended plan."""
    n = table.num_rows
    columns: list[ColumnProfile] = []

    # Materialize each column once, keyed by POSITION (tolerates duplicate names).
    raw: dict[int, list[Any]] = {i: table.column(i).to_pylist() for i in range(table.num_columns)}

    pii_map = _classify_pii(table, governance, raw, sample_for_pii)

    for i, name in enumerate(table.column_names):
        prof = _profile_column(name, table.column(i), raw[i])
        sens, is_pii = pii_map.get(name, (prof.sensitivity, prof.pii))
        prof.sensitivity = sens
        prof.pii = is_pii
        if is_pii:
            # Never serialize raw PII sample values into the assessment report
            # (it is returned over HTTP and written to disk). Keep only aggregates.
            prof.top_values = []
            prof.near_duplicate_categories = []
            prof.numeric_min = prof.numeric_max = prof.numeric_mean = None
            if "contains PII — mask before sharing/AI ingestion" not in prof.issues:
                prof.issues.append("contains PII — mask before sharing/AI ingestion")
        columns.append(prof)

    dup_rows = _duplicate_rows(raw, n)

    completeness = (
        float(np.mean([1.0 - c.null_fraction for c in columns])) if columns else 1.0
    )
    col_scores = [c.quality_score for c in columns] or [1.0]
    dup_fraction = dup_rows / n if n else 0.0
    overall = float(np.mean(col_scores)) * (1.0 - 0.5 * dup_fraction)

    pii_columns = [c.name for c in columns if c.pii]
    issues_summary = _summarize_issues(columns, dup_rows)

    report = AssessmentReport(
        source=source,
        connector=connector,
        dataset=dataset,
        row_estimate=row_estimate or n,
        sampled_rows=n,
        truncated=truncated,
        column_count=len(columns),
        duplicate_rows=dup_rows,
        completeness=round(completeness, 4),
        overall_quality_score=round(max(0.0, min(1.0, overall)), 4),
        modality=_guess_modality(columns).value,
        pii_columns=pii_columns,
        has_pii=bool(pii_columns),
        columns=columns,
        issues_summary=issues_summary,
    )
    report.recommended_plan = derive_plan(report)
    return report


# --------------------------------------------------------------------------- #
# Per-column profiling
# --------------------------------------------------------------------------- #
def _profile_column(name: str, col: pa.ChunkedArray, values: list[Any]) -> ColumnProfile:
    n = len(values)
    is_string_arrow = pa.types.is_string(col.type) or pa.types.is_large_string(col.type)

    null_count = 0
    blank_count = 0
    whitespace_count = 0
    lengths: list[int] = []
    non_null_strs: list[str] = []        # post-strip, non-sentinel string values
    distinct: set[str] = set()

    for v in values:
        if v is None:
            null_count += 1
            continue
        s = v if isinstance(v, str) else str(v)
        stripped = s.strip()
        if isinstance(v, str):
            if s != stripped:
                whitespace_count += 1
            lengths.append(len(s))
        if stripped.lower() in _NULL_SENTINELS:
            blank_count += 1
            continue
        non_null_strs.append(stripped)
        distinct.add(stripped)

    effective_nulls = null_count + blank_count
    real_count = n - effective_nulls

    inferred, coercible = _infer_type(col, non_null_strs)
    numeric_min = numeric_max = numeric_mean = None
    outlier_count = 0
    if inferred in (FieldType.INT, FieldType.FLOAT, FieldType.DOUBLE):
        nums = _as_floats(col, non_null_strs)
        if nums:
            arr = np.array(nums, dtype="float64")
            numeric_min, numeric_max = float(arr.min()), float(arr.max())
            numeric_mean = float(arr.mean())
            outlier_count = _iqr_outliers(arr)

    distinct_count = len(distinct)
    distinct_fraction = distinct_count / real_count if real_count else 0.0
    # Categorical = a manageable set of distinct values: a small absolute count
    # (so tiny tables still qualify) or a low distinct fraction on larger ones.
    categorical = real_count > 0 and distinct_count <= max(50, int(0.5 * real_count))
    near_dupes, mixed_case = _near_duplicate_categories(non_null_strs) if categorical else ([], False)
    embedded_unit = _embedded_unit(non_null_strs)
    top_values = _top_values(non_null_strs) if categorical else []

    prof = ColumnProfile(
        name=name,
        arrow_type=str(col.type),
        inferred_type=inferred.value,
        count=n,
        null_count=null_count,
        blank_count=blank_count,
        distinct_count=distinct_count,
        null_fraction=round(effective_nulls / n, 4) if n else 0.0,
        distinct_fraction=round(distinct_fraction, 4),
        whitespace_count=whitespace_count,
        min_length=min(lengths) if lengths else None,
        max_length=max(lengths) if lengths else None,
        numeric_min=numeric_min,
        numeric_max=numeric_max,
        numeric_mean=round(numeric_mean, 4) if numeric_mean is not None else None,
        outlier_count=outlier_count,
        coercible_fraction=round(coercible, 4),
        mixed_case=mixed_case,
        near_duplicate_categories=near_dupes,
        embedded_unit=embedded_unit,
        top_values=top_values,
    )
    _annotate(prof, is_string_arrow)
    return prof


def _annotate(p: ColumnProfile, is_string_arrow: bool) -> None:
    """Attach issues, recommended steps and a 0..1 quality score to a column."""
    issues: list[str] = []
    steps: list[str] = []

    if p.null_fraction > 0:
        issues.append(f"{p.null_fraction:.0%} missing/blank")
        if p.blank_count:
            steps.append("empty_to_null")
    if p.whitespace_count:
        issues.append(f"{p.whitespace_count} values with stray whitespace")
        steps.append("trim")
    if p.mixed_case or p.near_duplicate_categories:
        issues.append("inconsistent category spellings/casing")
        steps.append("standardize_case")
        if p.near_duplicate_categories:
            steps.append("normalize_category")
    # A text column that is really numeric/temporal.
    if is_string_arrow and p.inferred_type in ("int", "float", "double", "date", "timestamp"):
        if p.coercible_fraction >= 0.9:
            issues.append(f"stored as text but is {p.inferred_type}")
            steps.append("coerce_type")
    if p.embedded_unit:
        issues.append(f"value+unit packed together (unit '{p.embedded_unit}')")
        steps.append("split_unit")
    if p.outlier_count:
        issues.append(f"{p.outlier_count} statistical outliers (IQR)")
    if p.distinct_count == 0:
        issues.append("entirely empty")
        steps.append("drop_empty_columns")

    completeness = 1.0 - p.null_fraction
    validity = p.coercible_fraction if p.inferred_type != "string" else 1.0
    consistency = 1.0
    if p.count:
        consistency -= p.whitespace_count / p.count
    if p.mixed_case or p.near_duplicate_categories:
        consistency -= 0.2
    consistency = max(0.0, consistency)
    score = (completeness + validity + consistency) / 3.0

    p.issues = issues
    # Preserve order, drop duplicates.
    p.recommended_steps = list(dict.fromkeys(steps))
    p.quality_score = round(max(0.0, min(1.0, score)), 4)


# --------------------------------------------------------------------------- #
# Type inference
# --------------------------------------------------------------------------- #
def _infer_type(col: pa.ChunkedArray, non_null_strs: list[str]) -> tuple[FieldType, float]:
    # Native (non-string) Arrow types are trusted as-is.
    if pa.types.is_integer(col.type):
        return FieldType.INT, 1.0
    if pa.types.is_floating(col.type):
        return FieldType.DOUBLE, 1.0
    if pa.types.is_boolean(col.type):
        return FieldType.BOOL, 1.0
    if pa.types.is_date(col.type):
        return FieldType.DATE, 1.0
    if pa.types.is_timestamp(col.type):
        return FieldType.TIMESTAMP, 1.0
    if not non_null_strs:
        return FieldType.STRING, 1.0

    total = len(non_null_strs)
    n_int = n_float = n_date = n_ts = n_bool = 0
    for s in non_null_strs:
        if _INT_RE.match(s):
            n_int += 1
        if _FLOAT_RE.match(s):
            n_float += 1
        if _DATE_RE.match(s):
            n_date += 1
        if _TIMESTAMP_RE.match(s):
            n_ts += 1
        if s.lower() in _BOOL_VALUES:
            n_bool += 1

    # Most specific wins when ~all values fit; require a high threshold.
    thresh = 0.9
    if n_ts / total >= thresh:
        return FieldType.TIMESTAMP, n_ts / total
    if n_date / total >= thresh:
        return FieldType.DATE, n_date / total
    if n_int / total >= thresh:
        return FieldType.INT, n_int / total
    if n_float / total >= thresh:
        return FieldType.DOUBLE, n_float / total
    # Only call a column boolean when it's low-cardinality booleans, not "0"/"1" ids.
    if n_bool / total >= thresh and len({s.lower() for s in non_null_strs}) <= 3:
        return FieldType.BOOL, n_bool / total
    return FieldType.STRING, 1.0


def _as_floats(col: pa.ChunkedArray, non_null_strs: list[str]) -> list[float]:
    if pa.types.is_integer(col.type) or pa.types.is_floating(col.type):
        return [float(v) for v in col.to_pylist() if v is not None]
    out: list[float] = []
    for s in non_null_strs:
        try:
            out.append(float(s))
        except ValueError:
            continue
    return out


def _iqr_outliers(arr: "np.ndarray") -> int:
    if arr.size < 4:
        return 0
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(np.count_nonzero((arr < lo) | (arr > hi)))


# --------------------------------------------------------------------------- #
# Categorical / unit heuristics
# --------------------------------------------------------------------------- #
def _near_duplicate_categories(values: list[str]) -> tuple[list[list[str]], bool]:
    """Group surface forms that collapse under trim+casefold; flag mixed casing."""
    groups: dict[str, set[str]] = {}
    for v in values:
        groups.setdefault(v.strip().casefold(), set()).add(v)
    near: list[list[str]] = []
    mixed_case = False
    for forms in groups.values():
        if len(forms) > 1:
            near.append(sorted(forms))
            if len({f.casefold() for f in forms}) == 1:
                mixed_case = True
    return near[:10], mixed_case


def _embedded_unit(values: list[str]) -> Optional[str]:
    if not values:
        return None
    units: dict[str, int] = {}
    matched = 0
    for v in values:
        m = _UNIT_RE.match(v)
        if m:
            matched += 1
            units[m.group(1)] = units.get(m.group(1), 0) + 1
    if matched / len(values) >= 0.6 and units:
        return max(units, key=lambda u: units[u])
    return None


def _top_values(values: list[str], k: int = 5) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:k]
    return [{"value": v, "count": c} for v, c in top]


# --------------------------------------------------------------------------- #
# Dataset-level helpers
# --------------------------------------------------------------------------- #
def _duplicate_rows(raw: dict[str, list[Any]], n: int) -> int:
    if not raw or n == 0:
        return 0
    names = list(raw)
    seen: set[tuple] = set()
    dups = 0
    for i in range(n):
        key = tuple(_row_key(raw[c][i]) for c in names)
        if key in seen:
            dups += 1
        else:
            seen.add(key)
    return dups


def _guess_modality(columns: list[ColumnProfile]) -> Modality:
    names = {c.name.lower() for c in columns}
    if {"latitude", "longitude"} <= names or "geometry" in names or "geom" in names:
        return Modality.GEOSPATIAL
    if any(c.inferred_type in ("date", "timestamp") for c in columns):
        return Modality.TIME_SERIES
    return Modality.STRUCTURED


def _summarize_issues(columns: list[ColumnProfile], dup_rows: int) -> list[str]:
    out: list[str] = []
    if dup_rows:
        out.append(f"{dup_rows} duplicate rows")
    miss = [c.name for c in columns if c.null_fraction > 0]
    if miss:
        out.append(f"{len(miss)} columns with missing values: {', '.join(miss[:6])}"
                   + ("…" if len(miss) > 6 else ""))
    mistyped = [c.name for c in columns if "coerce_type" in c.recommended_steps]
    if mistyped:
        out.append(f"{len(mistyped)} text columns are really numeric/temporal: "
                   + ", ".join(mistyped[:6]) + ("…" if len(mistyped) > 6 else ""))
    pii = [c.name for c in columns if c.pii]
    if pii:
        out.append(f"PII detected in: {', '.join(pii)}")
    return out


# --------------------------------------------------------------------------- #
# PII classification via the engine's governance trust-fabric
# --------------------------------------------------------------------------- #
def _classify_pii(
    table: pa.Table, governance: Any, raw: dict[int, list[Any]], sample_for_pii: int
) -> dict[str, tuple[str, bool]]:
    """Return ``{column: (sensitivity, pii)}``, failing CLOSED.

    An always-on local heuristic guarantees obvious PII is caught even when the
    governance service is unavailable or raises; governance, when present, only
    *strengthens* the result. Detection therefore never silently fails open.
    """
    result: dict[str, tuple[str, bool]] = {}
    for i, name in enumerate(table.column_names):
        sample = [(v if isinstance(v, str) else str(v)) for v in raw[i][:sample_for_pii] if v is not None]
        result[name] = _heuristic_pii(name, sample)

    for gname, (gsens, gpii) in _governance_pii(table, governance, raw, sample_for_pii).items():
        csens, cpii = result.get(gname, ("internal", False))
        result[gname] = (_max_sensitivity_str(csens, gsens), cpii or gpii)
    return result


def _heuristic_pii(name: str, sample: list[str]) -> tuple[str, bool]:
    lname = name.lower()
    if any(h in lname for h in _PHI_NAME_HINTS):
        return ("phi", True)
    if any(h in lname for h in _PII_NAME_HINTS) or any(h in lname for h in _NAME_HINTS):
        return ("pii", True)
    hits = checked = 0
    for s in sample:
        checked += 1
        if checked > 200:
            break
        if _EMAIL_RE.search(s) or _NATIONAL_ID_RE.search(s) or _PHONE_RE.search(s):
            hits += 1
    if checked and hits / checked >= 0.3:
        return ("pii", True)
    return ("internal", False)


def _max_sensitivity_str(a: str, b: str) -> str:
    return a if _SENS_ORDER.get(a, 1) >= _SENS_ORDER.get(b, 1) else b


def _governance_pii(
    table: pa.Table, governance: Any, raw: dict[int, list[Any]], sample_for_pii: int
) -> dict[str, tuple[str, bool]]:
    """Augment with the engine's governance classifier (the same one the query path uses)."""
    if governance is None or not hasattr(governance, "classify"):
        return {}
    fields: list[FieldSchema] = []
    for i, name in enumerate(table.column_names):
        inferred, _ = _infer_type(table.column(i), [
            (v if isinstance(v, str) else str(v)).strip()
            for v in raw[i][:sample_for_pii]
            if v is not None and (v if isinstance(v, str) else str(v)).strip().lower() not in _NULL_SENTINELS
        ])
        fields.append(FieldSchema(name=name, type=inferred))
    meta = DatasetMetadata(
        ref=DatasetRef(domain="prepared", name="onboarding"),
        schema=TableSchema(name="onboarding", fields=fields),
    )
    try:
        classified = governance.classify(meta, sample=table.slice(0, min(sample_for_pii, table.num_rows)))
    except Exception:  # pragma: no cover - never block assessment on classification
        return {}
    out: dict[str, tuple[str, bool]] = {}
    for f in classified.schema_.fields:
        sens = f.sensitivity.value if isinstance(f.sensitivity, Sensitivity) else str(f.sensitivity)
        out[f.name] = (sens, bool(f.pii))
    return out
