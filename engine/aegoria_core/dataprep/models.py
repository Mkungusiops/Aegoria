"""Result models for the data-onboarding pipeline (assess → clean → AI-ready).

These are additive Pydantic view-models — they are serialized straight to JSON for
the CLI, the control-plane and any downstream application. They are intentionally
separate from the frozen ``contracts.models`` core vocabulary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #
class ColumnProfile(BaseModel):
    name: str
    arrow_type: str
    inferred_type: str               # string|int|float|double|bool|date|timestamp
    count: int = 0
    null_count: int = 0
    blank_count: int = 0             # empty / whitespace-only / sentinel ("NA","-",...)
    distinct_count: int = 0
    null_fraction: float = 0.0
    distinct_fraction: float = 0.0
    whitespace_count: int = 0        # values with leading/trailing whitespace
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    numeric_min: Optional[float] = None
    numeric_max: Optional[float] = None
    numeric_mean: Optional[float] = None
    outlier_count: int = 0           # IQR-based, numeric columns
    coercible_fraction: float = 1.0  # share of non-null values parseable as inferred_type
    mixed_case: bool = False
    near_duplicate_categories: list[list[str]] = Field(default_factory=list)
    embedded_unit: Optional[str] = None   # e.g. values like "90 KG" -> unit "KG"
    top_values: list[dict[str, Any]] = Field(default_factory=list)
    sensitivity: str = "internal"
    pii: bool = False
    issues: list[str] = Field(default_factory=list)
    recommended_steps: list[str] = Field(default_factory=list)
    quality_score: float = 1.0


class AssessmentReport(BaseModel):
    source: str
    connector: str
    dataset: str
    row_estimate: int = 0
    sampled_rows: int = 0
    truncated: bool = False
    column_count: int = 0
    duplicate_rows: int = 0
    completeness: float = 1.0
    overall_quality_score: float = 1.0
    modality: str = "structured"
    pii_columns: list[str] = Field(default_factory=list)
    has_pii: bool = False
    columns: list[ColumnProfile] = Field(default_factory=list)
    issues_summary: list[str] = Field(default_factory=list)
    recommended_plan: "CleaningPlan" = Field(default=None)  # type: ignore[assignment]
    assessed_at: datetime = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
class CleaningStep(BaseModel):
    """One declarative cleaning operation. A plan is an ordered list of these."""

    op: str           # trim|collapse_ws|empty_to_null|standardize_case|normalize_category|
                      # split_unit|coerce_type|dedupe_rows|drop_empty_columns|impute|
                      # clip_outliers|flag_outliers
    columns: list[str] = Field(default_factory=list)  # empty -> all applicable columns
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class CleaningPlan(BaseModel):
    steps: list[CleaningStep] = Field(default_factory=list)


class StepResult(BaseModel):
    op: str
    columns: list[str] = Field(default_factory=list)
    cells_changed: int = 0
    rows_removed: int = 0
    columns_added: list[str] = Field(default_factory=list)
    columns_removed: list[str] = Field(default_factory=list)
    notes: str = ""


class CleanResult(BaseModel):
    dataset: str
    input_rows: int = 0
    output_rows: int = 0
    input_quality_score: float = 0.0
    output_quality_score: float = 0.0
    steps_applied: list[StepResult] = Field(default_factory=list)
    final_schema: list[dict[str, str]] = Field(default_factory=list)  # [{name,type}]
    cleaned_at: datetime = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------- #
# AI-ready export
# --------------------------------------------------------------------------- #
class AiChunk(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AiBundle(BaseModel):
    dataset: str
    format: str = "jsonl-documents"   # one JSON doc per line, RAG/embedding-ready
    chunk_count: int = 0
    rows_serialized: int = 0
    masked_fields: list[str] = Field(default_factory=list)
    jsonl_path: Optional[str] = None
    card_path: Optional[str] = None
    manifest_path: Optional[str] = None
    signature: Optional[str] = None
    signature_alg: Optional[str] = None
    sample: list[AiChunk] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Full onboarding result
# --------------------------------------------------------------------------- #
class OnboardResult(BaseModel):
    source: str
    connector: str
    dataset: str
    assessment: AssessmentReport
    cleaning: CleanResult
    outputs: dict[str, Any] = Field(default_factory=dict)
    landed_dataset: Optional[str] = None      # catalog ref id if landed in the lakehouse
    ai_bundle: Optional[AiBundle] = None
    finished_at: datetime = Field(default_factory=_utcnow)


AssessmentReport.model_rebuild()
