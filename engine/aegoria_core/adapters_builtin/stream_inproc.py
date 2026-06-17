"""``inproc`` stream adapter — an in-process pub/sub broker for the lite engine.

Topics are simple in-memory FIFO queues with per-(topic, group) read cursors, so
streaming ingest works end-to-end on a laptop without Kafka. The same
:class:`~aegoria_core.contracts.adapters.StreamAdapter` contract is implemented
by the Kafka/Pulsar adapters in scale-out; the engine never knows which broker
it is talking to.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable, Iterator, Optional

import structlog

from ..config import AegoriaConfig
from ..registry import adapter

log = structlog.get_logger("aegoria.adapter.stream.inproc")


class InProcStream:
    """Thread-safe, process-local topic queues with consumer-group cursors."""

    name = "inproc"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # topic -> list[(key, value, headers)]
        self._log: dict[str, list[tuple[Optional[str], bytes, dict[str, str]]]] = defaultdict(list)
        # (topic, group) -> next offset to read
        self._cursors: dict[tuple[str, str], int] = defaultdict(int)

    # -- StreamAdapter -------------------------------------------------- #
    def produce(
        self,
        topic: str,
        key: Optional[str],
        value: bytes,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        with self._lock:
            self._log[topic].append((key, value, dict(headers or {})))
        log.debug("produce", topic=topic, bytes=len(value))

    def consume(
        self,
        topic: str,
        group: str,
        on_message: Callable[[bytes, dict[str, str]], None],
    ) -> None:
        """Drain all currently-available records, advancing the group cursor."""
        for value, headers in self.poll(topic, group, max_records=10**9):
            on_message(value, headers)

    def poll(
        self,
        topic: str,
        group: str,
        max_records: int = 100,
    ) -> Iterator[tuple[bytes, dict[str, str]]]:
        with self._lock:
            offset = self._cursors[(topic, group)]
            records = self._log.get(topic, [])
            end = min(len(records), offset + max_records)
            batch = records[offset:end]
            self._cursors[(topic, group)] = end
        for _key, value, headers in batch:
            yield value, headers

    def topics(self) -> list[str]:
        with self._lock:
            return sorted(self._log)


# A single broker instance is shared across all factory calls within a process
# so producers and consumers wired through different ctx lookups see the same log.
_BROKER = InProcStream()


@adapter("stream", "inproc")
def make_inproc_stream(*, config: AegoriaConfig, ctx: Any = None, **options: Any) -> InProcStream:
    """Factory the engine invokes to build the in-process stream adapter."""
    return _BROKER
