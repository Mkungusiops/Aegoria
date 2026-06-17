"""``default`` ML service — generic AI/ML with per-domain model specs.

Models are SUPPLIED PER-DOMAIN (registered from a pack's ``ModelSpec`` list); the
service itself stays domain-neutral. With no model it falls back to identity /
heuristic behaviour so flows work end-to-end on a laptop:

* :meth:`predict` echoes input (identity) unless a domain model is registered.
* :meth:`detect_anomalies` flags numeric outliers via z-score / IQR using numpy.
* :meth:`verify_content` combines a checksum check, the provenance signer's
  verification, and a simple plausibility heuristic into a verdict — the
  misinformation / content-authenticity seam.
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import structlog

from ..contracts.models import DatasetRef, ProvenanceRecord
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.ml")


class DefaultML:
    """Pluggable ML service; per-domain models, generic fallbacks."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx
        self._lock = threading.RLock()
        # domain -> model_id -> spec
        self._models: dict[str, dict[str, dict[str, Any]]] = {}

    # -- MLService ------------------------------------------------------ #
    def register_model(self, domain: str, model_id: str, spec: dict[str, Any]) -> None:
        with self._lock:
            self._models.setdefault(domain, {})[model_id] = dict(spec)
        log.debug("register_model", domain=domain, model_id=model_id, task=spec.get("task"))

    def _spec(self, domain: str, model_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._models.get(domain, {}).get(model_id)

    def predict(self, domain: str, model_id: str, data: pa.Table) -> pa.Table:
        spec = self._spec(domain, model_id)
        if spec is None:
            # No registered model: identity passthrough so pipelines still run.
            return data
        task = spec.get("task", "predict")
        if task in ("classify", "predict", "forecast"):
            # Heuristic baseline: mean of the first numeric column as a prediction.
            numeric = [n for n in data.column_names if pa.types.is_floating(data.column(n).type) or pa.types.is_integer(data.column(n).type)]
            if numeric:
                col = data.column(numeric[0])
                mean = pc.mean(col).as_py() or 0.0
                preds = pa.array([mean] * data.num_rows, type=pa.float64())
            else:
                preds = pa.array([None] * data.num_rows, type=pa.float64())
            return data.append_column(f"{model_id}_prediction", preds)
        return data

    def detect_anomalies(self, domain: str, ref: DatasetRef, data: pa.Table) -> pa.Table:
        """Flag rows whose numeric values are outliers by z-score (>3) or IQR."""
        n = data.num_rows
        flags = np.zeros(n, dtype=bool)
        scores = np.zeros(n, dtype="float64")
        for name in data.column_names:
            col = data.column(name)
            if not (pa.types.is_floating(col.type) or pa.types.is_integer(col.type)):
                continue
            arr = np.array([v if v is not None else np.nan for v in col.to_pylist()], dtype="float64")
            if np.all(np.isnan(arr)):
                continue
            std = np.nanstd(arr)
            mean = np.nanmean(arr)
            if std > 0:
                z = np.abs((arr - mean) / std)
                z = np.nan_to_num(z, nan=0.0)
                flags |= z > 3.0
                scores = np.maximum(scores, z)
            # IQR fallback for skewed columns.
            q1, q3 = np.nanpercentile(arr, [25, 75])
            iqr = q3 - q1
            if iqr > 0:
                lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                iqr_flag = (arr < lo) | (arr > hi)
                flags |= np.nan_to_num(iqr_flag, nan=False).astype(bool)
        out = data.append_column("is_anomaly", pa.array(flags.tolist(), type=pa.bool_()))
        out = out.append_column("anomaly_score", pa.array(scores.tolist(), type=pa.float64()))
        log.debug("detect_anomalies", ref=ref.id, anomalies=int(flags.sum()))
        return out

    def verify_content(self, domain: str, payload: bytes, claims: dict[str, Any]) -> dict[str, Any]:
        """Provenance + plausibility verification -> {verdict, confidence, evidence}."""
        evidence: dict[str, Any] = {}
        confidence = 0.5

        # 1. Checksum claim.
        claimed_checksum = claims.get("checksum_sha256")
        actual_checksum = hashlib.sha256(payload).hexdigest()
        checksum_match = claimed_checksum is None or claimed_checksum == actual_checksum
        evidence["checksum_match"] = checksum_match
        evidence["checksum_sha256"] = actual_checksum

        # 2. Cryptographic signature via the provenance signer adapter.
        signature = claims.get("content_signature")
        signature_valid = None
        if signature:
            signer = self._ctx.adapter("provenance")
            record = ProvenanceRecord(
                source_uri=str(claims.get("source_uri", "")),
                captured_by=str(claims.get("captured_by", "unknown")),
                method=str(claims.get("method", "ingest")),
                checksum_sha256=claimed_checksum or actual_checksum,
                software_agent=str(claims.get("software_agent", "aegoria-core")),
                software_version=str(claims.get("software_version", "0.1.0")),
            )
            signature_valid = signer.verify(payload, signature, record)
            evidence["signature_valid"] = signature_valid

        # 3. Model-based plausibility (registered per-domain verify model, else neutral).
        spec = self._spec(domain, str(claims.get("model_id", "")))
        plausible = True
        if spec and spec.get("task") == "verify_content":
            min_len = int(spec.get("params", {}).get("min_payload_bytes", 0))
            plausible = len(payload) >= min_len
            evidence["plausibility_model"] = spec.get("id")
        evidence["plausible"] = plausible

        # Combine into a verdict.
        if not checksum_match or signature_valid is False:
            verdict, confidence = "tampered", 0.95
        elif signature_valid is True and plausible:
            verdict, confidence = "authentic", 0.9
        elif plausible:
            verdict, confidence = "unverified", 0.6
        else:
            verdict, confidence = "suspect", 0.7

        log.debug("verify_content", domain=domain, verdict=verdict)
        return {"verdict": verdict, "confidence": confidence, "evidence": evidence}


@service("ml", "default")
def make_default_ml(*, ctx: EngineContext) -> DefaultML:
    """Factory the engine invokes to build the default ML service."""
    return DefaultML(ctx)
