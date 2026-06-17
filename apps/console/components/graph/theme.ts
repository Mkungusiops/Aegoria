/**
 * Visual vocabulary + light enrichment for the knowledge-graph view.
 *
 * The engine's KnowledgeGraphService emits typed Entity/Relation records (here
 * mapped to GraphEntity/GraphRelation with normalized 0..1 coordinates from a
 * force layout run offline). The console only paints — it never invents topology.
 */

import type { GraphEntity, GraphRelation } from "@/lib/types";

export const GRAPH_COLORS = {
  auralis: "#16E0C4",
  pulse: "#7B61FF",
  verdant: "#57E08A",
  ion: "#3FA9FF",
  solar: "#FFB454",
  crimson: "#FF5C72",
  muted: "#93A1C0",
} as const;

export type GraphColor = keyof typeof GRAPH_COLORS;

export const DOMAIN_META: Record<string, { label: string; color: GraphColor }> = {
  "climate-emissions": { label: "Climate · Emissions", color: "verdant" },
  "consumer-credit": { label: "Finance · Credit", color: "auralis" },
  shared: { label: "Shared registry", color: "pulse" },
};

export function domainMeta(domain: string) {
  return DOMAIN_META[domain] ?? { label: domain, color: "muted" as GraphColor };
}

/** Relations that bridge two different domains — the silo-breaking links. */
export const CROSS_DOMAIN_RELATIONS = new Set(["same_corporate_group"]);

/** Per-entity-type radius weight so hubs (regions, institutions) read bigger. */
const TYPE_WEIGHT: Record<string, number> = {
  Jurisdiction: 1.5,
  Region: 1.3,
  Institution: 1.25,
  Operator: 1.15,
  Facility: 1.0,
  Borrower: 0.9,
};

export function entityRadius(entity: GraphEntity, degree: number): number {
  const base = 13;
  const w = TYPE_WEIGHT[entity.type] ?? 1;
  return base * w + Math.min(degree, 4) * 2.2;
}

export function isCrossDomain(
  relation: GraphRelation,
  byId: Map<string, GraphEntity>,
): boolean {
  if (CROSS_DOMAIN_RELATIONS.has(relation.type)) return true;
  const a = byId.get(relation.from);
  const b = byId.get(relation.to);
  if (!a || !b) return false;
  if (a.domain === "shared" || b.domain === "shared") return false;
  return a.domain !== b.domain;
}

/** Pretty relation labels for link captions. */
export function relationLabel(type: string): string {
  return type.replace(/_/g, " ");
}
