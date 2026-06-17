"""``default`` knowledge-graph service — in-memory entity/relation store + resolution.

Holds entities and relations in memory, loads per-domain ontology terms and
field->term mappings, and performs lightweight cross-domain entity resolution by
matching aliases/labels to a canonical entity. ``neighbors`` walks the relation
graph to a bounded depth; ``query`` supports a tiny ``type:Foo`` / ``prop=val``
pattern for the console. A scale-out graph DB (Neptune, JanusGraph) implements
the same contract.
"""

from __future__ import annotations

import threading
from typing import Any

import structlog

from ..contracts.domain_pack import OntologyTerm, SemanticMapping
from ..contracts.models import Entity, Relation
from ..engine import EngineContext
from ..registry import service

log = structlog.get_logger("aegoria.service.knowledge_graph")


def _norm(text: str) -> str:
    return text.strip().lower()


class DefaultKnowledgeGraph:
    """Process-local semantic graph with cross-domain entity resolution."""

    def __init__(self, ctx: EngineContext) -> None:
        self._ctx = ctx
        self._lock = threading.RLock()
        self._entities: dict[str, Entity] = {}
        self._relations: list[Relation] = []
        # domain -> {term_id: OntologyTerm}
        self._ontology: dict[str, dict[str, OntologyTerm]] = {}
        # domain -> [SemanticMapping]
        self._mappings: dict[str, list[SemanticMapping]] = {}
        # normalized alias/label -> canonical entity id
        self._alias_index: dict[str, str] = {}

    # -- ontology loading (called by engine.load_domain_pack) ----------- #
    def load_ontology(
        self,
        domain: str,
        terms: list[OntologyTerm],
        mappings: list[SemanticMapping] | None = None,
    ) -> None:
        with self._lock:
            self._ontology[domain] = {t.id: t for t in terms}
            self._mappings[domain] = list(mappings or [])
        log.debug("load_ontology", domain=domain, terms=len(terms))

    # -- KnowledgeGraphService ------------------------------------------ #
    def upsert_entity(self, entity: Entity) -> str:
        with self._lock:
            self._entities[entity.id] = entity
            for token in [entity.id, *entity.aliases, *([entity.properties.get("label")] if entity.properties.get("label") else [])]:
                self._alias_index.setdefault(_norm(str(token)), entity.id)
        return entity.id

    def upsert_relation(self, relation: Relation) -> None:
        with self._lock:
            self._relations.append(relation)

    def resolve(self, entity: Entity) -> Entity:
        """Return the canonical entity matched by id/alias/label across domains."""
        with self._lock:
            candidates = [entity.id, *entity.aliases]
            label = entity.properties.get("label")
            if label:
                candidates.append(str(label))
            for token in candidates:
                canonical_id = self._alias_index.get(_norm(str(token)))
                if canonical_id and canonical_id in self._entities:
                    return self._entities[canonical_id]
        # No match: this entity becomes its own canonical record.
        self.upsert_entity(entity)
        return entity

    def neighbors(self, entity_id: str, depth: int = 1) -> tuple[list[Entity], list[Relation]]:
        with self._lock:
            visited: set[str] = {entity_id}
            edges: list[Relation] = []
            frontier = {entity_id}
            for _ in range(max(0, depth)):
                next_frontier: set[str] = set()
                for rel in self._relations:
                    if rel.src in frontier or rel.dst in frontier:
                        edges.append(rel)
                        for node in (rel.src, rel.dst):
                            if node not in visited:
                                visited.add(node)
                                next_frontier.add(node)
                if not next_frontier:
                    break
                frontier = next_frontier
            visited.discard(entity_id)
            entities = [self._entities[i] for i in visited if i in self._entities]
            # de-duplicate edges preserving order
            seen: set[tuple[str, str, str]] = set()
            uniq_edges = []
            for e in edges:
                key = (e.src, e.dst, e.type)
                if key not in seen:
                    seen.add(key)
                    uniq_edges.append(e)
            return entities, uniq_edges

    def query(self, pattern: str) -> list[dict[str, Any]]:
        """Match entities by ``type:Foo`` and/or ``prop=value`` clauses."""
        clauses = [c.strip() for c in pattern.split() if c.strip()]
        type_filter: str | None = None
        prop_filters: dict[str, str] = {}
        for clause in clauses:
            if clause.startswith("type:"):
                type_filter = clause[len("type:"):]
            elif "=" in clause:
                k, _, v = clause.partition("=")
                prop_filters[k.strip()] = v.strip()
        out: list[dict[str, Any]] = []
        with self._lock:
            for ent in self._entities.values():
                if type_filter and ent.type != type_filter:
                    continue
                if any(str(ent.properties.get(k)) != v for k, v in prop_filters.items()):
                    continue
                out.append(ent.model_dump())
        return out


@service("knowledge_graph", "default")
def make_default_knowledge_graph(*, ctx: EngineContext) -> DefaultKnowledgeGraph:
    """Factory the engine invokes to build the default knowledge-graph service."""
    return DefaultKnowledgeGraph(ctx)
