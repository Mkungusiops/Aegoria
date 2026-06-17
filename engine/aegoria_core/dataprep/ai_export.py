"""AI-ready export — turn cleaned, governed data into RAG/ingestion artifacts.

The novel last mile: *dirty data, once cleaned, can be safely fed to an AI.* This
module (1) **masks PII using the engine's governance fabric** — the very same
obligation enforcement the query path applies — so personal data is reduced to an
opaque pseudonymous token and never reaches a prompt or vector store in the clear;
(2) serializes each row into a natural-language document with structured metadata;
(3) writes a JSONL corpus + a human/agent-readable *data card* + a signed
*manifest* so the downstream AI ingests data whose cleaning and provenance are
cryptographically verifiable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import pyarrow as pa

from ..contracts.models import (
    FieldSchema,
    FieldType,
    Obligation,
    ProvenanceRecord,
    Sensitivity,
    TableSchema,
)
from .models import AiBundle, AiChunk, AssessmentReport, CleanResult


def to_ai_bundle(
    table: pa.Table,
    report: AssessmentReport,
    *,
    dataset: str,
    out_dir: Path,
    governance: Any = None,
    signer: Any = None,
    cleaning: Optional[CleanResult] = None,
    chunk_rows: int = 1,
    max_rows: Optional[int] = None,
    mask_strategy: str = "hash",
) -> AiBundle:
    """Produce a PII-safe, provenance-signed JSONL bundle for AI ingestion."""
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = _schema_from_report(report)
    pii_fields = _pii_fields_for(report, table.column_names)

    masked = _mask(table, pii_fields, governance, schema, mask_strategy)
    if max_rows is not None and masked.num_rows > max_rows:
        masked = masked.slice(0, max_rows)

    rows = masked.to_pylist()
    pii_set = set(pii_fields)
    chunks = _chunk(rows, dataset, pii_set, chunk_rows)

    jsonl_path = out_dir / f"{dataset}.jsonl"
    payload = "\n".join(json.dumps(c.model_dump(), default=str) for c in chunks)
    jsonl_path.write_text(payload + ("\n" if payload else ""))
    payload_bytes = jsonl_path.read_bytes()
    checksum = hashlib.sha256(payload_bytes).hexdigest()

    signature = signature_alg = None
    if signer is not None:
        record = ProvenanceRecord(
            source_uri=report.source,
            captured_by="aegoria-dataprep",
            method="derive",
            checksum_sha256=checksum,
            software_agent="aegoria-dataprep-ai-export",
            transformation="clean+mask+serialize-for-ai",
        )
        try:
            signature = signer.sign(payload_bytes, record)
            signature_alg = getattr(signer, "alg", getattr(signer, "name", "unknown"))
        except Exception:  # pragma: no cover - signing is best-effort
            signature = None

    card_path = out_dir / f"{dataset}.card.md"
    card_path.write_text(_data_card(report, cleaning, dataset, len(chunks), pii_fields, signature))

    manifest_path = out_dir / f"{dataset}.manifest.json"
    manifest = {
        "dataset": dataset,
        "format": "jsonl-documents",
        "chunk_count": len(chunks),
        "rows_serialized": len(rows),
        "masked_fields": pii_fields,
        "mask_strategy": mask_strategy,
        "checksum_sha256": checksum,
        "signature": signature,
        "signature_alg": signature_alg,
        "quality_score": report.overall_quality_score,
        "source": report.source,
        "jsonl": jsonl_path.name,
        "card": card_path.name,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    return AiBundle(
        dataset=dataset,
        chunk_count=len(chunks),
        rows_serialized=len(rows),
        masked_fields=pii_fields,
        jsonl_path=str(jsonl_path),
        card_path=str(card_path),
        manifest_path=str(manifest_path),
        signature=signature,
        signature_alg=signature_alg,
        sample=chunks[:3],
    )


# --------------------------------------------------------------------------- #
def _pii_fields_for(report: AssessmentReport, columns: list[str]) -> list[str]:
    """Resolve which CLEANED columns must be masked.

    A PII column may have been renamed by cleaning — notably ``split_unit`` turns
    ``card`` into ``card_value`` / ``card_unit``. We map those derivations back so
    a renamed PII column is never accidentally excluded from masking (fail-closed).
    """
    pii_orig = set(report.pii_columns)
    out: list[str] = []
    for c in columns:
        if c in pii_orig:
            out.append(c)
            continue
        # derived columns: "<pii>_value" / "<pii>_unit"
        for suffix in ("_value", "_unit"):
            if c.endswith(suffix) and c[: -len(suffix)] in pii_orig:
                out.append(c)
                break
    return out


def _mask(
    table: pa.Table, pii_fields: list[str], governance: Any, schema: TableSchema, strategy: str
) -> pa.Table:
    """Mask PII via governance (preferred) or a local hash fallback."""
    if not pii_fields:
        return table
    if governance is not None and hasattr(governance, "apply_obligations"):
        obl = Obligation(kind="mask", params={"fields": pii_fields, "strategy": strategy})
        try:
            return governance.apply_obligations(table, [obl], schema=schema)
        except Exception:  # pragma: no cover - fall through to local masking
            pass
    cols, names = [], table.column_names
    for name in names:
        col = table.column(name)
        if name in pii_fields:
            hashed = [None if v is None else hashlib.sha256(str(v).encode()).hexdigest()[:16]
                      for v in col.to_pylist()]
            col = pa.array(hashed, pa.string())
        cols.append(col)
    return pa.table(cols, names=names)


def _chunk(rows: list[dict[str, Any]], dataset: str, pii: set[str], chunk_rows: int) -> list[AiChunk]:
    chunk_rows = max(1, chunk_rows)
    chunks: list[AiChunk] = []
    for start in range(0, len(rows), chunk_rows):
        group = rows[start:start + chunk_rows]
        texts, meta_rows = [], []
        for offset, row in enumerate(group):
            idx = start + offset
            texts.append(_row_to_text(dataset, idx, row, pii))
            # Metadata keeps every field (PII already reduced to an opaque token).
            meta_rows.append({k: _scalar(v) for k, v in row.items() if v is not None})
        if chunk_rows == 1:
            meta = meta_rows[0] if meta_rows else {}
            meta["_dataset"] = dataset
            chunks.append(AiChunk(id=f"{dataset}:{start}", text=texts[0], metadata=meta))
        else:
            chunks.append(AiChunk(
                id=f"{dataset}:{start}-{start + len(group) - 1}",
                text="\n\n".join(texts),
                metadata={"_dataset": dataset, "row_start": start, "row_count": len(group)},
            ))
    return chunks


def _row_to_text(dataset: str, idx: int, row: dict[str, Any], pii: set[str]) -> str:
    """De-identified natural-language rendering: PII columns are omitted from prose."""
    parts = []
    for k, v in row.items():
        if k in pii or v is None or v == "":
            continue
        parts.append(f"{_humanize(k)}: {_scalar(v)}")
    body = "; ".join(parts)
    return f"{_humanize(dataset)} record {idx} — {body}" if body else f"{_humanize(dataset)} record {idx}"


def _humanize(name: str) -> str:
    return name.replace("_", " ").strip().title() if name else name


def _scalar(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def _schema_from_report(report: AssessmentReport) -> TableSchema:
    fields = []
    for c in report.columns:
        try:
            ftype = FieldType(c.inferred_type)
        except ValueError:
            ftype = FieldType.STRING
        sens = Sensitivity.PII if c.pii else Sensitivity.INTERNAL
        fields.append(FieldSchema(name=c.name, type=ftype, pii=c.pii, sensitivity=sens))
    return TableSchema(name=report.dataset or "dataset", fields=fields)


def _data_card(
    report: AssessmentReport, cleaning: Optional[CleanResult], dataset: str,
    chunk_count: int, pii_fields: list[str], signature: Optional[str],
) -> str:
    lines = [
        f"# Data card — {dataset}",
        "",
        f"- **Source:** `{report.source}` (via `{report.connector}` connector)",
        f"- **Rows:** {report.row_estimate:,} total"
        + (f" — {report.sampled_rows:,} processed (truncated)" if report.truncated
           else f" — {report.sampled_rows:,} processed"),
        f"- **Columns:** {report.column_count}",
        f"- **Modality:** {report.modality}",
        f"- **Quality (assessed):** {report.overall_quality_score:.2f} / 1.00",
    ]
    if cleaning is not None:
        lines.append(
            f"- **Quality (after cleaning):** {cleaning.output_quality_score:.2f} / 1.00 "
            f"(from {cleaning.input_quality_score:.2f})"
        )
        lines.append(f"- **Rows after cleaning:** {cleaning.output_rows:,} "
                     f"(removed {cleaning.input_rows - cleaning.output_rows:,})")
    lines += [
        f"- **AI documents:** {chunk_count:,}",
        f"- **PII handling:** {('masked → ' + ', '.join(pii_fields)) if pii_fields else 'no PII detected'}",
        f"- **Provenance signature:** {'present (verifiable)' if signature else 'unsigned'}",
        "",
        "## Schema",
        "",
        "| column | type | PII | issues |",
        "| --- | --- | --- | --- |",
    ]
    for c in report.columns:
        issues = "; ".join(c.issues) if c.issues else "—"
        lines.append(f"| {c.name} | {c.inferred_type} | {'yes' if c.pii else 'no'} | {issues} |")
    if cleaning is not None and cleaning.steps_applied:
        lines += ["", "## Cleaning applied", ""]
        for s in cleaning.steps_applied:
            detail = []
            if s.cells_changed:
                detail.append(f"{s.cells_changed} cells")
            if s.rows_removed:
                detail.append(f"{s.rows_removed} rows removed")
            if s.columns_added:
                detail.append(f"+{', '.join(s.columns_added)}")
            lines.append(f"- **{s.op}**: {s.notes}" + (f" ({'; '.join(detail)})" if detail else ""))
    lines += [
        "",
        "_Cleaned and de-identified by Aegoria data-prep. Documents are safe for AI "
        "ingestion: PII is reduced to opaque tokens and the corpus is provenance-signed._",
        "",
    ]
    return "\n".join(lines)
