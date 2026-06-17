"""``local-fs`` storage adapter — the laptop warehouse backend.

Implements :class:`~aegoria_core.contracts.adapters.StorageAdapter` over the
local filesystem rooted at ``config.warehouse_uri``. A bucket-style key maps to a
path under that root; ``presign`` returns a ``file://`` URL since there is no
remote signing authority offline. Swapping in S3/GCS/ABFS is a different adapter
registered under the same capability — the engine code never changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import structlog

from ..config import AegoriaConfig
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.storage.local-fs")


def _root(config: AegoriaConfig) -> Path:
    """Resolve the warehouse root, tolerating ``file://`` prefixes."""
    uri = config.warehouse_uri
    if uri.startswith("file://"):
        uri = uri[len("file://"):]
    return Path(uri).expanduser().resolve()


class LocalFsStorage:
    """File-backed object store. Keys are POSIX-style relative paths."""

    name = "local-fs"

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    # -- key <-> path helpers ------------------------------------------- #
    def _path(self, key: str) -> Path:
        rel = key.lstrip("/")
        target = (self._root / rel).resolve()
        # Prevent path traversal outside the warehouse root.
        if self._root not in target.parents and target != self._root:
            raise ValueError(f"key {key!r} escapes warehouse root")
        return target

    # -- StorageAdapter ------------------------------------------------- #
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        log.debug("put", key=key, bytes=len(data), content_type=content_type)
        return self.uri(key)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_dir():
            for child in sorted(path.rglob("*"), reverse=True):
                child.unlink() if child.is_file() else child.rmdir()
            path.rmdir()
        elif path.exists():
            path.unlink()

    def list(self, prefix: str) -> Iterable[str]:
        base = self._path(prefix)
        if base.is_file():
            yield prefix
            return
        if not base.exists():
            return
        for p in sorted(base.rglob("*")):
            if p.is_file():
                yield str(p.relative_to(self._root))

    def uri(self, key: str) -> str:
        return self._path(key).as_uri()

    def presign(self, key: str, expires_s: int = 3600) -> str:
        # No signing authority offline; the file:// URI is the durable handle.
        return self.uri(key)


@adapter("storage", "local-fs")
def make_local_fs_storage(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> LocalFsStorage:
    """Factory the engine invokes to build the local-fs storage adapter."""
    return LocalFsStorage(_root(config))
