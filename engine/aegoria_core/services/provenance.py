"""``default`` provenance service — C2PA-style signing + verification + chains.

Thin orchestration over the :class:`ProvenanceSigner` adapter and the catalog:

* :meth:`sign_asset` computes a checksum and a content signature, returning an
  enriched :class:`ProvenanceRecord`.
* :meth:`verify_asset` reports ``{valid, signer, checksum_match}``.
* :meth:`attach` appends a record to a dataset's provenance chain in the catalog.
* :meth:`chain` returns the ordered provenance chain for a dataset.
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any

import structlog

from ..contracts.models import DatasetRef, ProvenanceRecord
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.provenance")


class DefaultProvenance:
    """Content signing + verification on top of the provenance signer adapter."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx
        self._lock = threading.RLock()
        # In-process overlay for records attached outside the catalog metadata.
        self._chains: dict[str, list[ProvenanceRecord]] = {}

    @property
    def _signer(self) -> Any:
        return self._ctx.adapter("provenance")

    # -- ProvenanceService ---------------------------------------------- #
    def attach(self, ref: DatasetRef, record: ProvenanceRecord) -> None:
        with self._lock:
            self._chains.setdefault(ref.id, []).append(record)
        # Mirror into the catalog metadata if the dataset is registered.
        catalog = self._ctx.service("catalog")
        meta = catalog.get(ref)
        if meta is not None:
            meta.provenance = [*meta.provenance, record]
            catalog.register(meta)
        log.debug("attach", ref=ref.id, method=record.method)

    def sign_asset(self, payload: bytes, record: ProvenanceRecord) -> ProvenanceRecord:
        enriched = record.model_copy(deep=True)
        enriched.checksum_sha256 = hashlib.sha256(payload).hexdigest()
        enriched.content_signature = self._signer.sign(payload, enriched)
        enriched.signature_alg = getattr(self._signer, "alg", self._signer.name)
        log.debug("sign_asset", source=record.source_uri, alg=enriched.signature_alg)
        return enriched

    def verify_asset(self, payload: bytes, record: ProvenanceRecord) -> dict[str, Any]:
        checksum = hashlib.sha256(payload).hexdigest()
        checksum_match = record.checksum_sha256 is None or record.checksum_sha256 == checksum
        valid = False
        if record.content_signature:
            valid = self._signer.verify(payload, record.content_signature, record)
        return {
            "valid": bool(valid and checksum_match),
            "signer": self._signer.name,
            "checksum_match": checksum_match,
            "signature_present": bool(record.content_signature),
        }

    def chain(self, ref: DatasetRef) -> list[ProvenanceRecord]:
        catalog = self._ctx.service("catalog")
        meta = catalog.get(ref)
        records: list[ProvenanceRecord] = list(meta.provenance) if meta else []
        with self._lock:
            for rec in self._chains.get(ref.id, []):
                if rec not in records:
                    records.append(rec)
        records.sort(key=lambda r: r.captured_at)
        return records


@service("provenance", "default")
def make_default_provenance(*, ctx: EngineContext) -> DefaultProvenance:
    """Factory the engine invokes to build the default provenance service."""
    return DefaultProvenance(ctx)
