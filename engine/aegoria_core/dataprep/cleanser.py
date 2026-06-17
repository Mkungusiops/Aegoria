"""Cleansing — turn an assessment into a plan, then execute it on the data.

:func:`derive_plan` reads an :class:`AssessmentReport` and proposes an ordered,
*conservative* :class:`CleaningPlan` (it never fabricates values — imputation and
outlier-clipping are opt-in, not default). :func:`apply_plan` executes a plan over
an Arrow table and returns the cleaned table plus a per-step audit
(:class:`CleanResult`). Plans are plain data, so a caller can inspect, edit, store
or replay them.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Optional

import numpy as np
import pyarrow as pa

from .models import (
    AssessmentReport,
    CleaningPlan,
    CleaningStep,
    CleanResult,
    StepResult,
)

_NULL_SENTINELS = {"", "na", "n/a", "null", "none", "nan", "-", "--", "?", "."}
# Distinct, un-collidable sentinel for a NULL cell in a row-identity key so a true
# null is never conflated with the string "" (or any other value's str()).
_NULL_KEY = ("\x00aegoria-null\x00",)
_TRUE = {"true", "t", "yes", "y", "1"}
_FALSE = {"false", "f", "no", "n", "0"}
_UNIT_RE = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)\s*([A-Za-z%][A-Za-z%/]*)\s*$")
_WS_RE = re.compile(r"\s+")


def _row_key(value: Any) -> Any:
    """Row-identity key element that keeps NULL distinct from "" and avoids
    cross-type ``str()`` collisions (e.g. int 1 vs str "1")."""
    if value is None:
        return _NULL_KEY
    return (type(value).__name__, value)


# --------------------------------------------------------------------------- #
# Plan derivation
# --------------------------------------------------------------------------- #
def derive_plan(report: AssessmentReport) -> CleaningPlan:
    """Build a conservative, ordered cleaning plan from a profile."""
    cols = report.columns
    steps: list[CleaningStep] = []

    def pick(step: str) -> list[str]:
        return [c.name for c in cols if step in c.recommended_steps]

    trim_cols = pick("trim")
    if trim_cols:
        steps.append(CleaningStep(op="trim", columns=trim_cols,
                                  reason="remove leading/trailing whitespace"))

    blank_cols = pick("empty_to_null")
    if blank_cols:
        steps.append(CleaningStep(op="empty_to_null", columns=blank_cols,
                                  reason="normalize empty/sentinel values to null"))

    case_cols = pick("standardize_case")
    if case_cols:
        steps.append(CleaningStep(op="standardize_case", columns=case_cols,
                                  params={"case": "lower"},
                                  reason="unify inconsistent casing"))

    norm_cols = pick("normalize_category")
    if norm_cols:
        steps.append(CleaningStep(op="normalize_category", columns=norm_cols,
                                  reason="collapse near-duplicate category spellings"))

    unit_cols = [c.name for c in cols if c.embedded_unit and "split_unit" in c.recommended_steps]
    if unit_cols:
        steps.append(CleaningStep(op="split_unit", columns=unit_cols,
                                  reason="separate packed value and unit"))

    coerce_types = {c.name: c.inferred_type for c in cols if "coerce_type" in c.recommended_steps}
    if coerce_types:
        steps.append(CleaningStep(op="coerce_type", columns=list(coerce_types),
                                  params={"types": coerce_types},
                                  reason="cast text columns to their real type"))

    if report.duplicate_rows > 0:
        steps.append(CleaningStep(op="dedupe_rows",
                                  reason=f"drop {report.duplicate_rows} duplicate rows"))

    empty_cols = pick("drop_empty_columns")
    if empty_cols:
        steps.append(CleaningStep(op="drop_empty_columns", columns=empty_cols,
                                  reason="remove entirely-empty columns"))

    return CleaningPlan(steps=steps)


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #
def _arrow_logical(t: pa.DataType) -> str:
    if pa.types.is_integer(t):
        return "int"
    if pa.types.is_floating(t):
        return "double"
    if pa.types.is_boolean(t):
        return "bool"
    if pa.types.is_date(t):
        return "date"
    if pa.types.is_timestamp(t):
        return "timestamp"
    return "string"


class _Work:
    """Mutable column-store the cleaning ops transform in place."""

    def __init__(self, table: pa.Table) -> None:
        self.order: list[str] = list(table.column_names)
        self.data: dict[str, list[Any]] = {n: table.column(n).to_pylist() for n in self.order}
        self.ctype: dict[str, str] = {n: _arrow_logical(table.column(n).type) for n in self.order}
        self.n: int = table.num_rows

    def applicable(self, requested: list[str], *, string_only: bool = True) -> list[str]:
        cols = requested or list(self.order)
        out = [c for c in cols if c in self.order]
        if string_only:
            out = [c for c in out if self.ctype[c] == "string"]
        return out


def apply_plan(
    table: pa.Table, plan: CleaningPlan, *, dataset: str = "dataset",
    input_quality_score: float = 0.0,
) -> tuple[pa.Table, CleanResult]:
    """Execute ``plan`` against ``table``; return (cleaned_table, audit)."""
    w = _Work(table)
    results: list[StepResult] = []
    for step in plan.steps:
        handler = _HANDLERS.get(step.op)
        if handler is None:
            results.append(StepResult(op=step.op, notes="unknown op; skipped"))
            continue
        results.append(handler(w, step))

    cleaned = _build_table(w)
    result = CleanResult(
        dataset=dataset,
        input_rows=table.num_rows,
        # Authoritative row count from _Work — a zero-column result (all columns
        # dropped) still reports its true row count, which cleaned.num_rows loses.
        output_rows=w.n,
        input_quality_score=round(input_quality_score, 4),
        output_quality_score=_score(w),
        steps_applied=results,
        final_schema=[{"name": f.name, "type": str(f.type)} for f in cleaned.schema],
    )
    return cleaned, result


def _build_table(w: _Work) -> pa.Table:
    cols = []
    for name in w.order:
        cols.append(_build_array(w.data[name], w.ctype[name]))
    return pa.table(cols, names=list(w.order)) if w.order else pa.table({})


def _build_array(vals: list[Any], t: str) -> pa.Array:
    if t == "int":
        return pa.array([None if v is None else int(v) for v in vals], pa.int64())
    if t in ("float", "double"):
        return pa.array([None if v is None else float(v) for v in vals], pa.float64())
    if t == "bool":
        return pa.array([None if v is None else bool(v) for v in vals], pa.bool_())
    if t == "date":
        return pa.array(vals, pa.date32())
    if t == "timestamp":
        # All values are normalized to UTC instants in _coerce_value, so the
        # column is an unambiguous tz-aware UTC timestamp.
        return pa.array(vals, pa.timestamp("us", tz="UTC"))
    return pa.array([None if v is None else (v if isinstance(v, str) else str(v)) for v in vals], pa.string())


# -- individual ops --------------------------------------------------------- #
def _op_trim(w: _Work, step: CleaningStep) -> StepResult:
    changed = 0
    cols = w.applicable(step.columns)
    for c in cols:
        col = w.data[c]
        for i, v in enumerate(col):
            if isinstance(v, str) and v != v.strip():
                col[i] = v.strip()
                changed += 1
    return StepResult(op="trim", columns=cols, cells_changed=changed, notes=step.reason)


def _op_collapse_ws(w: _Work, step: CleaningStep) -> StepResult:
    changed = 0
    cols = w.applicable(step.columns)
    for c in cols:
        col = w.data[c]
        for i, v in enumerate(col):
            if isinstance(v, str):
                nv = _WS_RE.sub(" ", v).strip()
                if nv != v:
                    col[i] = nv
                    changed += 1
    return StepResult(op="collapse_ws", columns=cols, cells_changed=changed, notes=step.reason)


def _op_empty_to_null(w: _Work, step: CleaningStep) -> StepResult:
    changed = 0
    cols = w.applicable(step.columns)
    for c in cols:
        col = w.data[c]
        for i, v in enumerate(col):
            if isinstance(v, str) and v.strip().lower() in _NULL_SENTINELS:
                col[i] = None
                changed += 1
    return StepResult(op="empty_to_null", columns=cols, cells_changed=changed, notes=step.reason)


def _op_standardize_case(w: _Work, step: CleaningStep) -> StepResult:
    mode = step.params.get("case", "lower")
    fn = {"lower": str.lower, "upper": str.upper, "title": str.title}.get(mode, str.lower)
    changed = 0
    cols = w.applicable(step.columns)
    for c in cols:
        col = w.data[c]
        for i, v in enumerate(col):
            if isinstance(v, str):
                nv = fn(v)
                if nv != v:
                    col[i] = nv
                    changed += 1
    return StepResult(op="standardize_case", columns=cols, cells_changed=changed,
                      notes=f"{step.reason} ({mode})")


def _op_normalize_category(w: _Work, step: CleaningStep) -> StepResult:
    changed = 0
    cols = w.applicable(step.columns)
    for c in cols:
        col = w.data[c]
        # Canonical surface form = most frequent value within each trim+casefold group.
        groups: dict[str, dict[str, int]] = {}
        for v in col:
            if isinstance(v, str):
                key = v.strip().casefold()
                groups.setdefault(key, {})
                groups[key][v.strip()] = groups[key].get(v.strip(), 0) + 1
        canon = {k: max(forms, key=lambda f: forms[f]) for k, forms in groups.items()}
        for i, v in enumerate(col):
            if isinstance(v, str):
                nv = canon.get(v.strip().casefold(), v)
                if nv != v:
                    col[i] = nv
                    changed += 1
    return StepResult(op="normalize_category", columns=cols, cells_changed=changed, notes=step.reason)


def _op_split_unit(w: _Work, step: CleaningStep) -> StepResult:
    cols = w.applicable(step.columns)
    added: list[str] = []
    removed: list[str] = []
    changed = 0
    for c in cols:
        col = w.data[c]
        values: list[Optional[float]] = []
        units: list[Optional[str]] = []
        for v in col:
            m = _UNIT_RE.match(v) if isinstance(v, str) else None
            if m:
                values.append(float(m.group(1)))
                units.append(m.group(2))
                changed += 1
            else:
                values.append(None)
                units.append(None)
        vcol, ucol = f"{c}_value", f"{c}_unit"
        idx = w.order.index(c)
        w.order[idx:idx + 1] = [vcol, ucol]
        del w.data[c], w.ctype[c]
        w.data[vcol], w.ctype[vcol] = values, "double"
        w.data[ucol], w.ctype[ucol] = units, "string"
        added.extend([vcol, ucol])
        removed.append(c)
    return StepResult(op="split_unit", columns=cols, cells_changed=changed,
                      columns_added=added, columns_removed=removed, notes=step.reason)


def _op_coerce_type(w: _Work, step: CleaningStep) -> StepResult:
    types: dict[str, str] = step.params.get("types") or {c: "string" for c in step.columns}
    failed = 0
    changed = 0
    cols = []
    for name, target in types.items():
        if name not in w.order or w.ctype[name] != "string":
            continue
        cols.append(name)
        col = w.data[name]
        for i, v in enumerate(col):
            if v is None:
                continue
            parsed, ok = _coerce_value(str(v).strip(), target)
            col[i] = parsed
            changed += 1  # every non-null cell is rewritten string -> typed value
            if not ok:
                failed += 1
        w.ctype[name] = target
    return StepResult(op="coerce_type", columns=cols, cells_changed=changed,
                      notes=f"{step.reason}; {failed} unparseable -> null")


def _op_dedupe_rows(w: _Work, step: CleaningStep) -> StepResult:
    if w.n == 0:
        return StepResult(op="dedupe_rows", notes="empty")
    keep: list[int] = []
    seen: set[tuple] = set()
    for i in range(w.n):
        key = tuple(_row_key(w.data[c][i]) for c in w.order)
        if key not in seen:
            seen.add(key)
            keep.append(i)
    removed = w.n - len(keep)
    if removed:
        for c in w.order:
            w.data[c] = [w.data[c][i] for i in keep]
        w.n = len(keep)
    return StepResult(op="dedupe_rows", rows_removed=removed, notes=step.reason)


def _op_drop_empty_columns(w: _Work, step: CleaningStep) -> StepResult:
    requested = step.columns or list(w.order)
    removed: list[str] = []
    for c in list(requested):
        if c in w.order and all(v is None for v in w.data[c]):
            w.order.remove(c)
            del w.data[c], w.ctype[c]
            removed.append(c)
    return StepResult(op="drop_empty_columns", columns_removed=removed, notes=step.reason)


def _op_impute(w: _Work, step: CleaningStep) -> StepResult:
    strategy = step.params.get("strategy", "mean")
    const = step.params.get("value")
    cols = w.applicable(step.columns, string_only=False)
    changed = 0
    for c in cols:
        col = w.data[c]
        fill = _impute_value(col, w.ctype[c], strategy, const)
        if fill is None:
            continue
        for i, v in enumerate(col):
            if v is None:
                col[i] = fill
                changed += 1
    return StepResult(op="impute", columns=cols, cells_changed=changed,
                      notes=f"{step.reason or 'fill nulls'} ({strategy})")


def _op_clip_outliers(w: _Work, step: CleaningStep) -> StepResult:
    cols = [c for c in (step.columns or list(w.order))
            if c in w.order and w.ctype[c] in ("int", "double", "float")]
    changed = 0
    for c in cols:
        nums = [float(v) for v in w.data[c] if v is not None]
        if len(nums) < 4:
            continue
        arr = np.array(nums)
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        col = w.data[c]
        for i, v in enumerate(col):
            if v is None:
                continue
            fv = float(v)
            if fv < lo:
                col[i] = lo if w.ctype[c] != "int" else int(round(lo))
                changed += 1
            elif fv > hi:
                col[i] = hi if w.ctype[c] != "int" else int(round(hi))
                changed += 1
    return StepResult(op="clip_outliers", columns=cols, cells_changed=changed, notes=step.reason)


def _op_flag_outliers(w: _Work, step: CleaningStep) -> StepResult:
    cols = [c for c in (step.columns or list(w.order))
            if c in w.order and w.ctype[c] in ("int", "double", "float")]
    added: list[str] = []
    for c in cols:
        nums = [float(v) for v in w.data[c] if v is not None]
        flags = [False] * w.n
        if len(nums) >= 4:
            arr = np.array(nums)
            q1, q3 = np.percentile(arr, [25, 75])
            iqr = q3 - q1
            if iqr > 0:
                lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                for i, v in enumerate(w.data[c]):
                    flags[i] = v is not None and (float(v) < lo or float(v) > hi)
        fcol = f"{c}__outlier"
        idx = w.order.index(c)
        w.order.insert(idx + 1, fcol)
        w.data[fcol], w.ctype[fcol] = flags, "bool"
        added.append(fcol)
    return StepResult(op="flag_outliers", columns=cols, columns_added=added, notes=step.reason)


_HANDLERS = {
    "trim": _op_trim,
    "collapse_ws": _op_collapse_ws,
    "empty_to_null": _op_empty_to_null,
    "standardize_case": _op_standardize_case,
    "normalize_category": _op_normalize_category,
    "split_unit": _op_split_unit,
    "coerce_type": _op_coerce_type,
    "dedupe_rows": _op_dedupe_rows,
    "drop_empty_columns": _op_drop_empty_columns,
    "impute": _op_impute,
    "clip_outliers": _op_clip_outliers,
    "flag_outliers": _op_flag_outliers,
}


# -- value-level helpers ---------------------------------------------------- #
def _coerce_value(s: str, target: str) -> tuple[Any, bool]:
    try:
        if target == "int":
            return int(s), True
        if target in ("float", "double"):
            return float(s), True
        if target == "bool":
            low = s.lower()
            if low in _TRUE:
                return True, True
            if low in _FALSE:
                return False, True
            return None, False
        if target == "date":
            return date.fromisoformat(s), True
        if target == "timestamp":
            # Normalize every value to a UTC instant: naive strings are assumed UTC,
            # offset-bearing strings are converted — so the column is homogeneous.
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            return dt, True
    except (ValueError, TypeError):
        return None, False
    return s, True


def _impute_value(col: list[Any], ctype: str, strategy: str, const: Any) -> Any:
    if strategy == "constant":
        if ctype in ("int", "double", "float", "bool", "date", "timestamp"):
            # Don't poison a typed column with a value it can't hold (would crash
            # the final Arrow build); skip the fill if the constant doesn't fit.
            parsed, ok = _coerce_value(str(const), ctype)
            return parsed if ok else None
        return const
    present = [v for v in col if v is not None]
    if not present:
        return None
    if strategy == "mode":
        counts: dict[Any, int] = {}
        for v in present:
            counts[v] = counts.get(v, 0) + 1
        return max(counts, key=lambda k: counts[k])
    if ctype in ("int", "double", "float"):
        nums = np.array([float(v) for v in present])
        val = float(np.median(nums)) if strategy == "median" else float(nums.mean())
        return int(round(val)) if ctype == "int" else val
    return None


def _score(w: _Work) -> float:
    """A comparable post-clean quality score: completeness × consistency proxy."""
    if w.n == 0:
        return 1.0
    if not w.order:
        return 0.0  # every column was dropped (all empty) -> no usable data
    scores = []
    for c in w.order:
        nulls = sum(1 for v in w.data[c] if v is None)
        completeness = 1.0 - nulls / w.n
        # After cleaning, typed/trimmed columns are treated as valid+consistent.
        scores.append((completeness + 1.0 + 1.0) / 3.0)
    return round(float(np.mean(scores)), 4)
