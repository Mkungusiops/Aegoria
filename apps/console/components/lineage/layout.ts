/**
 * Deterministic layered DAG layout for the lineage graph.
 *
 * The engine never ships pixel coordinates — it emits a typed {nodes, edges}
 * provenance graph. The console derives a clean left-to-right layered ("Sugiyama"
 * style) layout from topology alone, so any domain-pack's lineage renders without
 * bespoke positioning. Layers come from the longest-path depth of each node;
 * within a layer nodes are ordered to keep their two domains visually separated.
 */

import type { LineageEdge, LineageNode } from "@/lib/types";

export interface PlacedNode extends LineageNode {
  layer: number;
  row: number;
  x: number;
  y: number;
}

export interface PlacedEdge extends LineageEdge {
  fromNode: PlacedNode;
  toNode: PlacedNode;
}

export interface LineageLayout {
  nodes: PlacedNode[];
  edges: PlacedEdge[];
  width: number;
  height: number;
  layers: number;
}

export interface LayoutOptions {
  /** Horizontal gap between layer centers. */
  colGap?: number;
  /** Vertical gap between rows. */
  rowGap?: number;
  /** Inner padding around the drawing. */
  pad?: number;
}

/** Longest-path layering: a node sits one layer right of its deepest parent. */
function computeLayers(nodes: LineageNode[], edges: LineageEdge[]): Map<string, number> {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const incoming = new Map<string, string[]>();
  const outgoing = new Map<string, string[]>();
  for (const n of nodes) {
    incoming.set(n.id, []);
    outgoing.set(n.id, []);
  }
  for (const e of edges) {
    if (!byId.has(e.from) || !byId.has(e.to)) continue;
    outgoing.get(e.from)!.push(e.to);
    incoming.get(e.to)!.push(e.from);
  }

  const layer = new Map<string, number>();
  const visiting = new Set<string>();

  const depth = (id: string): number => {
    const cached = layer.get(id);
    if (cached !== undefined) return cached;
    if (visiting.has(id)) return 0; // defensive: ignore cycles in a DAG view
    visiting.add(id);
    const parents = incoming.get(id) ?? [];
    const d = parents.length === 0 ? 0 : Math.max(...parents.map((p) => depth(p) + 1));
    visiting.delete(id);
    layer.set(id, d);
    return d;
  };

  for (const n of nodes) depth(n.id);
  return layer;
}

const KIND_ORDER: Record<LineageNode["kind"], number> = {
  source: 0,
  stream: 1,
  dataset: 2,
  model: 3,
  product: 4,
};

/**
 * Produce a fully-placed layout. Coordinates live in an abstract SVG space; the
 * caller renders into a responsive viewBox so the whole graph always fits.
 */
export function layoutLineage(
  nodes: LineageNode[],
  edges: LineageEdge[],
  opts: LayoutOptions = {},
): LineageLayout {
  const colGap = opts.colGap ?? 210;
  const rowGap = opts.rowGap ?? 84;
  const pad = opts.pad ?? 48;

  const layer = computeLayers(nodes, edges);
  const maxLayer = Math.max(0, ...nodes.map((n) => layer.get(n.id) ?? 0));

  // Group nodes per layer; order by domain then by kind for clean reading.
  const perLayer: LineageNode[][] = Array.from({ length: maxLayer + 1 }, () => []);
  for (const n of nodes) perLayer[layer.get(n.id) ?? 0].push(n);

  const domains = Array.from(new Set(nodes.map((n) => n.domain))).sort();
  const domainRank = new Map(domains.map((d, i) => [d, i] as const));
  for (const col of perLayer) {
    col.sort((a, b) => {
      const da = domainRank.get(a.domain) ?? 0;
      const db = domainRank.get(b.domain) ?? 0;
      if (da !== db) return da - db;
      if (KIND_ORDER[a.kind] !== KIND_ORDER[b.kind]) return KIND_ORDER[a.kind] - KIND_ORDER[b.kind];
      return a.label.localeCompare(b.label);
    });
  }

  const maxRows = Math.max(1, ...perLayer.map((c) => c.length));
  const contentHeight = (maxRows - 1) * rowGap;

  const placed = new Map<string, PlacedNode>();
  perLayer.forEach((col, l) => {
    // Vertically center each column's nodes within the tallest column.
    const colHeight = (col.length - 1) * rowGap;
    const offset = (contentHeight - colHeight) / 2;
    col.forEach((n, r) => {
      placed.set(n.id, {
        ...n,
        layer: l,
        row: r,
        x: pad + l * colGap,
        y: pad + offset + r * rowGap,
      });
    });
  });

  const placedEdges: PlacedEdge[] = [];
  for (const e of edges) {
    const fromNode = placed.get(e.from);
    const toNode = placed.get(e.to);
    if (!fromNode || !toNode) continue;
    placedEdges.push({ ...e, fromNode, toNode });
  }

  return {
    nodes: [...placed.values()],
    edges: placedEdges,
    width: pad * 2 + maxLayer * colGap,
    height: pad * 2 + contentHeight,
    layers: maxLayer + 1,
  };
}
