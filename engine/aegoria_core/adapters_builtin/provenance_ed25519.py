"""``ed25519`` provenance signer — a stdlib stand-in for C2PA manifest signing.

The production adapter signs content + provenance manifests with Ed25519. To
keep the lite engine dependency-free, this implementation uses an HMAC-SHA256
keyed digest over the payload and the manifest's identifying fields. It satisfies
the :class:`~aegoria_core.contracts.adapters.ProvenanceSigner` contract: ``sign``
returns a hex digest, ``verify`` recomputes and compares in constant time. The
key derives deterministically from config so signatures are reproducible across
the control-plane and the CLI sharing one warehouse.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import structlog

from ..config import AegoriaConfig
from ..contracts.models import ProvenanceRecord
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.provenance.ed25519")

_ALG = "hmac-sha256(ed25519-stub)"


def _manifest_bytes(record: ProvenanceRecord) -> bytes:
    """Bind the signature to the manifest's identifying provenance fields."""
    parts = [
        record.source_uri,
        record.captured_by,
        record.method,
        record.checksum_sha256 or "",
        record.software_agent,
        record.software_version,
    ]
    return "|".join(parts).encode("utf-8")


class Ed25519Signer:
    """Keyed-digest content signer. Hex signature; constant-time verification."""

    name = "ed25519"
    alg = _ALG

    def __init__(self, secret: bytes) -> None:
        self._secret = secret

    def _digest(self, payload: bytes, record: ProvenanceRecord) -> str:
        mac = hmac.new(self._secret, digestmod=hashlib.sha256)
        mac.update(payload)
        mac.update(b"\x00")
        mac.update(_manifest_bytes(record))
        return mac.hexdigest()

    # -- ProvenanceSigner ----------------------------------------------- #
    def sign(self, payload: bytes, record: ProvenanceRecord) -> str:
        sig = self._digest(payload, record)
        log.debug("sign", source=record.source_uri, alg=self.alg)
        return sig

    def verify(self, payload: bytes, signature: str, record: ProvenanceRecord) -> bool:
        expected = self._digest(payload, record)
        return hmac.compare_digest(expected, signature or "")


@adapter("provenance", "ed25519")
def make_ed25519_signer(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> Ed25519Signer:
    """Factory the engine invokes to build the provenance signer.

    The key is derived deterministically from the warehouse identity (or an
    explicit ``key`` option) so independent processes verify each other's
    signatures over the shared warehouse.
    """
    key_material = str(options.get("key", config.warehouse_uri)).encode("utf-8")
    secret = hashlib.sha256(b"aegoria-provenance:" + key_material).digest()
    return Ed25519Signer(secret)
