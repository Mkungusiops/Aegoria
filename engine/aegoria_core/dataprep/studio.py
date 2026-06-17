"""``DataPrepStudio`` — the data-onboarding orchestrator (connect → assess → clean → output).

A façade over the engine's services and the ``source`` connectors that takes an
*external, messy* database/file and produces three outputs:

1. **Internal / another-app** — cleaned data as portable Parquet **and** CSV, plus
   (best-effort) a governed Iceberg table registered in the FAIR catalog so the
   cleaned dataset is queryable through the platform like any other.
2. **Machine report** — the full assessment + cleaning audit as JSON.
3. **AI-ready** — a PII-masked, provenance-signed JSONL corpus + data card for RAG.

It is registered under the ``dataprep`` adapter capability so it is discoverable
via ``aegoria doctor`` and swappable — and it requires **zero** changes to the
frozen engine: it is resolved from the registry and built from an
:class:`EngineContext`, exactly like every first-party service.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pyarrow as pa
import structlog

from ..contracts.models import (
    DatasetMetadata,
    DatasetRef,
    FieldSchema,
    FieldType,
    LineageEdge,
    Modality,
    ProvenanceRecord,
    TableSchema,
)
from ..engine import EngineContext
from ..registry import adapter
from ..sources.base import SourceDataset, detect_connector
from .ai_export import to_ai_bundle
from .cleanser import apply_plan
from .models import AssessmentReport, CleaningPlan, CleanResult, OnboardResult
from .profiler import assess as _assess

log = structlog.get_logger("aegoria.dataprep.studio")

_ARROW_TO_FIELD = {
    "string": FieldType.STRING,
    "int": FieldType.LONG,
    "double": FieldType.DOUBLE,
    "float": FieldType.DOUBLE,
    "bool": FieldType.BOOL,
    "date": FieldType.DATE,
    "timestamp": FieldType.TIMESTAMP,
}


def _safe_name(name: str) -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch in "_-") else "_" for ch in (name or "dataset"))
    return cleaned.strip("_") or "dataset"


class DataPrepStudio:
    """Connect to any source, assess it, clean it, and emit cleaned + AI-ready outputs."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx

    # -- engine collaborators (resolved lazily; degrade gracefully) ------ #
    def _governance(self) -> Any:
        try:
            return self._ctx.service("governance")
        except Exception:  # pragma: no cover
            return None

    def _signer(self) -> Any:
        try:
            return self._ctx.adapter("provenance")
        except Exception:  # pragma: no cover
            return None

    def _connector(self, name: str) -> Any:
        return self._ctx.registry.adapter("source", name, config=self._ctx.config, ctx=self._ctx)

    def exports_dir(self) -> Path:
        uri = self._ctx.config.warehouse_uri
        if uri.startswith("file://"):
            uri = uri[len("file://"):]
        return Path(uri).expanduser().parent / "exports"

    # -- pipeline stages ------------------------------------------------- #
    def connect(
        self,
        uri: str,
        *,
        connector: Optional[str] = None,
        table: Optional[str] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[pa.Table, SourceDataset]:
        name = detect_connector(uri, connector)
        conn = self._connector(name)
        return conn.read(uri, table=table, query=query, limit=limit, options=options)

    def list_tables(self, uri: str, *, connector: Optional[str] = None) -> list[str]:
        return self._connector(detect_connector(uri, connector)).list_tables(uri)

    def assess(
        self,
        uri: str,
        *,
        connector: Optional[str] = None,
        table: Optional[str] = None,
        query: Optional[str] = None,
        limit: Optional[int] = 50_000,
        dataset: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> AssessmentReport:
        arrow, descriptor = self.connect(
            uri, connector=connector, table=table, query=query, limit=limit, options=options
        )
        return self._assess_table(arrow, descriptor, dataset)

    def _assess_table(
        self, arrow: pa.Table, descriptor: SourceDataset, dataset: Optional[str]
    ) -> AssessmentReport:
        name = _safe_name(dataset or descriptor.table)
        return _assess(
            arrow,
            dataset=name,
            source=descriptor.uri,
            connector=descriptor.connector,
            governance=self._governance(),
            row_estimate=descriptor.row_estimate,
            truncated=descriptor.truncated,
        )

    def clean(
        self,
        uri: str,
        *,
        plan: Optional[CleaningPlan] = None,
        connector: Optional[str] = None,
        table: Optional[str] = None,
        query: Optional[str] = None,
        limit: Optional[int] = 200_000,
        dataset: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[pa.Table, CleanResult, AssessmentReport]:
        arrow, descriptor = self.connect(
            uri, connector=connector, table=table, query=query, limit=limit, options=options
        )
        report = self._assess_table(arrow, descriptor, dataset)
        chosen = plan or report.recommended_plan
        cleaned, result = apply_plan(
            arrow, chosen, dataset=report.dataset, input_quality_score=report.overall_quality_score
        )
        return cleaned, result, report

    # -- full onboarding ------------------------------------------------- #
    def onboard(
        self,
        uri: str,
        *,
        connector: Optional[str] = None,
        table: Optional[str] = None,
        query: Optional[str] = None,
        dataset: Optional[str] = None,
        limit: Optional[int] = 200_000,
        out_dir: Optional[str | Path] = None,
        domain: str = "prepared",
        principal: str = "dataprep",
        land: bool = True,
        ai: bool = True,
        plan: Optional[CleaningPlan] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> OnboardResult:
        """Run the whole pipeline and write every output. Returns a full receipt."""
        arrow, descriptor = self.connect(
            uri, connector=connector, table=table, query=query, limit=limit, options=options
        )
        report = self._assess_table(arrow, descriptor, dataset)
        name = report.dataset
        chosen = plan or report.recommended_plan
        cleaned, clean_result = apply_plan(
            arrow, chosen, dataset=name, input_quality_score=report.overall_quality_score
        )

        out = Path(out_dir) if out_dir else (self.exports_dir() / name)
        out.mkdir(parents=True, exist_ok=True)
        outputs = self._write_cleaned(cleaned, out, name, report, clean_result)

        landed = None
        if land:
            try:
                landed = self._land(cleaned, report, descriptor, domain, name, principal,
                                    quality_score=clean_result.output_quality_score)
                outputs["lakehouse_dataset"] = landed
            except Exception as exc:  # best-effort: never fail onboarding on landing
                outputs["lakehouse_error"] = str(exc)
                log.warning("land_failed", dataset=name, error=str(exc))

        bundle = None
        if ai:
            bundle = to_ai_bundle(
                cleaned, report, dataset=name, out_dir=out,
                governance=self._governance(), signer=self._signer(), cleaning=clean_result,
            )
            outputs["ai_jsonl"] = bundle.jsonl_path
            outputs["ai_card"] = bundle.card_path
            outputs["ai_manifest"] = bundle.manifest_path

        return OnboardResult(
            source=descriptor.uri,
            connector=descriptor.connector,
            dataset=name,
            assessment=report,
            cleaning=clean_result,
            outputs=outputs,
            landed_dataset=landed,
            ai_bundle=bundle,
        )

    # -- output writers -------------------------------------------------- #
    def _write_cleaned(
        self, cleaned: pa.Table, out: Path, name: str,
        report: AssessmentReport, clean_result: CleanResult,
    ) -> dict[str, Any]:
        import pyarrow.csv as pacsv
        import pyarrow.parquet as pq

        parquet_path = out / f"{name}.cleaned.parquet"
        csv_path = out / f"{name}.cleaned.csv"
        report_path = out / f"{name}.report.json"
        pq.write_table(cleaned, parquet_path)
        pacsv.write_csv(cleaned, csv_path)
        report_path.write_text(json.dumps(
            {"assessment": report.model_dump(), "cleaning": clean_result.model_dump()},
            indent=2, default=str,
        ))
        return {
            "parquet": str(parquet_path),
            "csv": str(csv_path),
            "report": str(report_path),
        }

    def _land(
        self, cleaned: pa.Table, report: AssessmentReport, descriptor: SourceDataset,
        domain: str, name: str, principal: str, *, quality_score: float = 0.0,
    ) -> str:
        """Register the cleaned table as a governed Iceberg dataset in the catalog."""
        ref = DatasetRef(domain=domain, name=name, version="1.0.0")
        schema = self._table_schema(cleaned, report, name)
        meta = DatasetMetadata(
            ref=ref,
            title=name.replace("_", " ").title(),
            description=f"Cleaned via Aegoria data-prep from {descriptor.uri}",
            schema=schema,
            modality=Modality(report.modality),
            owner=principal,
            tags=["prepared", "cleaned"],
        )
        lakehouse = self._ctx.service("lakehouse")
        catalog = self._ctx.service("catalog")
        catalog_adapter = self._ctx.adapter("catalog")
        if not catalog_adapter.table_exists(ref):
            meta.location_uri = lakehouse.create_table(meta.model_copy(deep=True))
        else:
            meta.location_uri = lakehouse.table_location(ref)
        lakehouse.write(ref, cleaned, mode="overwrite")

        gov = self._governance()
        if gov is not None:
            meta = gov.classify(meta, sample=cleaned.slice(0, min(200, cleaned.num_rows)))
        meta.provenance = [*meta.provenance, ProvenanceRecord(
            source_uri=descriptor.uri, captured_by=principal, method="derive",
            transformation="dataprep-clean", software_agent="aegoria-dataprep",
        )]
        meta.row_count = lakehouse.scan(ref).num_rows
        meta.quality_score = quality_score or report.overall_quality_score
        catalog.register(meta)
        catalog.record_lineage(LineageEdge(
            src=DatasetRef(domain=domain, name=f"source:{descriptor.connector}", version="ext"),
            dst=ref, operation="transform",
        ))
        log.info("landed", ref=ref.id, rows=meta.row_count)
        return ref.id

    @staticmethod
    def _table_schema(cleaned: pa.Table, report: AssessmentReport, name: str) -> TableSchema:
        from .cleanser import _arrow_logical

        pii = set(report.pii_columns)
        fields: list[FieldSchema] = []
        for f in cleaned.schema:
            logical = _arrow_logical(f.type)
            fields.append(FieldSchema(
                name=f.name,
                type=_ARROW_TO_FIELD.get(logical, FieldType.STRING),
                pii=f.name in pii,
            ))
        return TableSchema(name=name, fields=fields, modality=Modality(report.modality))


@adapter("dataprep", "studio")
def make_dataprep_studio(*, ctx: EngineContext, config: Any = None, **options: Any) -> DataPrepStudio:
    """Factory the registry invokes to build the data-prep studio."""
    return DataPrepStudio(ctx)
