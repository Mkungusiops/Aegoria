"use client";

import * as React from "react";
import {
  BadgeCheck,
  Fingerprint,
  GitBranch,
  Hash,
  ShieldAlert,
  ShieldCheck,
  Clock,
  ArrowRight,
  ArrowDownRight,
  ArrowUpRight,
} from "lucide-react";
import type { LineageEdge, LineageNode } from "@/lib/types";
import { Badge, Panel, type Tone } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { layoutLineage, type PlacedNode } from "./layout";
import { KIND_META, NODE_COLORS, domainMeta, opMeta, provenanceFor } from "./theme";

interface Props {
  nodes: LineageNode[];
  edges: LineageEdge[];
}

const NODE_W = 152;
const NODE_H = 50;

/** Smooth left-to-right cubic between two node ports. */
function edgePath(x1: number, y1: number, x2: number, y2: number) {
  const dx = Math.max(40, (x2 - x1) * 0.5);
  return `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
}

export function LineageExplorer({ nodes, edges }: Props) {
  const layout = React.useMemo(() => layoutLineage(nodes, edges), [nodes, edges]);
  const [selected, setSelected] = React.useState<string | null>(
    () => nodes.find((n) => n.kind === "product")?.id ?? nodes[0]?.id ?? null,
  );
  const [hovered, setHovered] = React.useState<string | null>(null);

  const nodeById = React.useMemo(
    () => new Map(layout.nodes.map((n) => [n.id, n])),
    [layout.nodes],
  );

  // Connectivity sets for the active node (selected, falling back to hovered).
  const active = hovered ?? selected;
  const { upstream, downstream, activeEdges } = React.useMemo(() => {
    const up = new Set<string>();
    const down = new Set<string>();
    const eset = new Set<string>();
    if (active) {
      for (const e of layout.edges) {
        if (e.to === active) {
          up.add(e.from);
          eset.add(`${e.from}->${e.to}`);
        }
        if (e.from === active) {
          down.add(e.to);
          eset.add(`${e.from}->${e.to}`);
        }
      }
    }
    return { upstream: up, downstream: down, activeEdges: eset };
  }, [active, layout.edges]);

  const selectedNode = selected ? nodeById.get(selected) ?? null : null;

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      {/* ----------------------------------------------------------- DAG canvas */}
      <div className="surface relative overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
          <div className="flex items-center gap-2 text-[12.5px] text-muted">
            <GitBranch size={14} className="text-auralis" />
            <span className="text-lumen">Provenance DAG</span>
            <span className="text-faint">· {layout.nodes.length} artifacts · {layout.edges.length} transforms</span>
          </div>
          <KindLegend />
        </div>

        <div className="grid-bg overflow-x-auto">
          <svg
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            width="100%"
            className="block min-w-[720px]"
            style={{ height: Math.max(layout.height, 360) }}
            role="img"
            aria-label="Data lineage directed acyclic graph"
          >
            <defs>
              {Object.entries(NODE_COLORS).map(([k, v]) => (
                <marker
                  key={k}
                  id={`arrow-${k}`}
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M0,0 L10,5 L0,10 z" fill={v} />
                </marker>
              ))}
            </defs>

            {/* Edges */}
            <g>
              {layout.edges.map((e) => {
                const x1 = e.fromNode.x + NODE_W / 2;
                const y1 = e.fromNode.y;
                const x2 = e.toNode.x - NODE_W / 2;
                const y2 = e.toNode.y;
                const op = opMeta(e.operation);
                const isActive = activeEdges.has(`${e.from}->${e.to}`);
                const dim = active && !isActive;
                const mx = (x1 + x2) / 2;
                const my = (y1 + y2) / 2;
                return (
                  <g key={`${e.from}->${e.to}`} className="transition-opacity duration-200" opacity={dim ? 0.16 : 1}>
                    <path
                      d={edgePath(x1, y1, x2, y2)}
                      fill="none"
                      stroke={NODE_COLORS[op.color]}
                      strokeWidth={isActive ? 2.4 : 1.5}
                      strokeOpacity={isActive ? 0.95 : 0.45}
                      markerEnd={`url(#arrow-${op.color})`}
                    />
                    <g transform={`translate(${mx}, ${my})`}>
                      <rect
                        x={-(e.operation.length * 3.6 + 8)}
                        y={-9}
                        width={e.operation.length * 7.2 + 16}
                        height={18}
                        rx={9}
                        fill="#0B0F1A"
                        stroke={NODE_COLORS[op.color]}
                        strokeOpacity={isActive ? 0.6 : 0.3}
                      />
                      <text
                        x={0}
                        y={3.5}
                        textAnchor="middle"
                        fontSize={10}
                        fontFamily="var(--font-mono)"
                        fill={NODE_COLORS[op.color]}
                        opacity={isActive ? 1 : 0.7}
                      >
                        {e.operation}
                      </text>
                    </g>
                  </g>
                );
              })}
            </g>

            {/* Nodes */}
            <g>
              {layout.nodes.map((n) => (
                <NodeCard
                  key={n.id}
                  node={n}
                  selected={n.id === selected}
                  related={active != null && (n.id === active || upstream.has(n.id) || downstream.has(n.id))}
                  dim={active != null && n.id !== active && !upstream.has(n.id) && !downstream.has(n.id)}
                  onSelect={() => setSelected(n.id)}
                  onHover={(h) => setHovered(h ? n.id : null)}
                />
              ))}
            </g>
          </svg>
        </div>

        {/* Domain ribbon — proves two independent lineages share one engine. */}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-hairline px-4 py-3 text-[11.5px]">
          <span className="text-faint">Domains in view</span>
          {Array.from(new Set(layout.nodes.map((n) => n.domain))).map((d) => {
            const m = domainMeta(d);
            return (
              <span key={d} className="inline-flex items-center gap-1.5 text-muted">
                <span className="h-2 w-2 rounded-full" style={{ background: NODE_COLORS[m.color] }} />
                {m.label}
              </span>
            );
          })}
          <span className="ml-auto text-faint">Select a node to inspect its signed provenance →</span>
        </div>
      </div>

      {/* --------------------------------------------------------- Detail panel */}
      <ProvenancePanel
        node={selectedNode}
        upstream={[...upstream].map((id) => nodeById.get(id)!).filter(Boolean)}
        downstream={[...downstream].map((id) => nodeById.get(id)!).filter(Boolean)}
        edges={layout.edges}
        onPick={setSelected}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ NodeCard */
function NodeCard({
  node,
  selected,
  related,
  dim,
  onSelect,
  onHover,
}: {
  node: PlacedNode;
  selected: boolean;
  related: boolean;
  dim: boolean;
  onSelect: () => void;
  onHover: (h: boolean) => void;
}) {
  const meta = KIND_META[node.kind];
  const dm = domainMeta(node.domain);
  const color = NODE_COLORS[meta.color];
  const domainColor = NODE_COLORS[dm.color];
  const prov = provenanceFor(node.id);

  return (
    <g
      transform={`translate(${node.x - NODE_W / 2}, ${node.y - NODE_H / 2})`}
      className="cursor-pointer transition-opacity duration-200"
      opacity={dim ? 0.28 : 1}
      onClick={onSelect}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
    >
      {selected && (
        <rect x={-4} y={-4} width={NODE_W + 8} height={NODE_H + 8} rx={12} fill="none" stroke={color} strokeWidth={1.5} strokeOpacity={0.55} />
      )}
      <rect
        width={NODE_W}
        height={NODE_H}
        rx={10}
        fill="#0B0F1A"
        stroke={selected || related ? color : "#1E2740"}
        strokeWidth={selected ? 1.8 : 1.2}
      />
      {/* domain accent stripe */}
      <rect width={4} height={NODE_H} rx={2} fill={domainColor} />
      {/* kind glyph chip */}
      <circle cx={22} cy={NODE_H / 2} r={11} fill={color} fillOpacity={0.14} stroke={color} strokeOpacity={0.5} strokeWidth={1} />
      <text x={22} y={NODE_H / 2 + 4} textAnchor="middle" fontSize={11} fill={color}>
        {meta.glyph}
      </text>
      <text x={40} y={21} fontSize={11.5} fontFamily="var(--font-sans)" fontWeight={600} fill="#EAF1FF">
        {node.label.length > 15 ? `${node.label.slice(0, 14)}…` : node.label}
      </text>
      <text x={40} y={36} fontSize={9.5} fontFamily="var(--font-mono)" fill="#5C6B8A">
        {meta.label.toLowerCase()}
      </text>
      {/* signed badge */}
      <g transform={`translate(${NODE_W - 16}, 13)`}>
        <circle r={6} fill={prov.signed ? "#57E08A" : "#5C6B8A"} fillOpacity={0.18} />
        <text textAnchor="middle" y={3} fontSize={8} fill={prov.signed ? "#57E08A" : "#5C6B8A"}>
          {prov.signed ? "✓" : "·"}
        </text>
      </g>
    </g>
  );
}

/* ----------------------------------------------------------------- Legend */
function KindLegend() {
  return (
    <div className="hidden flex-wrap items-center gap-3 sm:flex">
      {(Object.keys(KIND_META) as (keyof typeof KIND_META)[]).map((k) => (
        <span key={k} className="inline-flex items-center gap-1.5 text-[10.5px] text-faint">
          <span className="h-2 w-2 rounded-full" style={{ background: NODE_COLORS[KIND_META[k].color] }} />
          {KIND_META[k].label}
        </span>
      ))}
    </div>
  );
}

/* -------------------------------------------------------- Provenance panel */
function ProvenancePanel({
  node,
  upstream,
  downstream,
  edges,
  onPick,
}: {
  node: PlacedNode | null;
  upstream: PlacedNode[];
  downstream: PlacedNode[];
  edges: { from: string; to: string; operation: string }[];
  onPick: (id: string) => void;
}) {
  if (!node) {
    return (
      <Panel className="grid place-items-center p-8 text-center text-[12.5px] text-faint">
        Select a node to inspect provenance.
      </Panel>
    );
  }
  const meta = KIND_META[node.kind];
  const dm = domainMeta(node.domain);
  const domainTone: Tone = dm.color === "muted" ? "neutral" : dm.color;
  const prov = provenanceFor(node.id);

  const opTo = (id: string) => edges.find((e) => e.from === node.id && e.to === id)?.operation;
  const opFrom = (id: string) => edges.find((e) => e.from === id && e.to === node.id)?.operation;

  return (
    <Panel className="flex flex-col p-0">
      <div className="border-b border-hairline p-4">
        <div className="flex items-center justify-between">
          <Badge tone={meta.tone}>{meta.label}</Badge>
          <Badge tone={domainTone} dot>
            {dm.label}
          </Badge>
        </div>
        <h3 className="mt-3 font-display text-[17px] font-semibold tracking-tight text-lumen">{node.label}</h3>
        <p className="mt-0.5 break-all font-mono text-[10.5px] text-faint">{node.id}</p>
      </div>

      {/* Provenance / C2PA block */}
      <div className="space-y-3 border-b border-hairline p-4">
        <div className="flex items-center gap-2">
          {prov.signed ? (
            <Badge tone="verdant"><BadgeCheck size={12} /> C2PA signed</Badge>
          ) : (
            <Badge tone="solar"><ShieldAlert size={12} /> Unsigned</Badge>
          )}
          <span className="text-[11px] text-faint">content provenance manifest</span>
        </div>

        <ProvRow icon={<Fingerprint size={13} />} label="Signer" value={prov.signer} />
        <ProvRow icon={<ShieldCheck size={13} />} label="Algorithm" value={prov.algorithm} />
        <ProvRow icon={<Hash size={13} />} label="Checksum" value={prov.checksum} mono />
        <ProvRow icon={<Clock size={13} />} label="Captured" value={fmtTime(prov.capturedAt)} mono />
        <ProvRow icon={<GitBranch size={13} />} label="Manifest" value={prov.manifest} mono break />
      </div>

      {/* Upstream / downstream */}
      <div className="grid grid-cols-1 gap-0 divide-y divide-hairline">
        <RelationGroup
          title="Upstream"
          empty="Origin artifact — no inputs."
          icon={<ArrowUpRight size={13} className="text-ion" />}
          rows={upstream.map((u) => ({ node: u, op: opFrom(u.id) }))}
          onPick={onPick}
        />
        <RelationGroup
          title="Downstream"
          empty="Terminal artifact — nothing derived yet."
          icon={<ArrowDownRight size={13} className="text-verdant" />}
          rows={downstream.map((d) => ({ node: d, op: opTo(d.id) }))}
          onPick={onPick}
        />
      </div>
    </Panel>
  );
}

function ProvRow({
  icon,
  label,
  value,
  mono,
  break: brk,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  mono?: boolean;
  break?: boolean;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 text-faint">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[10.5px] uppercase tracking-wider text-faint">{label}</div>
        <div className={cn("text-[12px] text-lumen", mono && "font-mono text-[11px]", brk && "break-all")}>{value}</div>
      </div>
    </div>
  );
}

function RelationGroup({
  title,
  icon,
  empty,
  rows,
  onPick,
}: {
  title: string;
  icon: React.ReactNode;
  empty: string;
  rows: { node: PlacedNode; op?: string }[];
  onPick: (id: string) => void;
}) {
  return (
    <div className="p-4">
      <div className="mb-2.5 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-faint">
        {icon} {title}
        <span className="text-faint/70">· {rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-[11.5px] text-faint">{empty}</p>
      ) : (
        <ul className="space-y-1.5">
          {rows.map(({ node, op }) => {
            const meta = KIND_META[node.kind];
            return (
              <li key={node.id}>
                <button
                  onClick={() => onPick(node.id)}
                  className="group flex w-full items-center gap-2 rounded-md border border-hairline bg-veil-1/60 px-2.5 py-1.5 text-left transition-colors hover:border-auralis/40 hover:bg-veil-2"
                >
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: NODE_COLORS[meta.color] }} />
                  <span className="min-w-0 flex-1 truncate text-[12px] text-lumen">{node.label}</span>
                  {op && (
                    <span className="shrink-0 font-mono text-[10px] text-faint group-hover:text-muted">{op}</span>
                  )}
                  <ArrowRight size={12} className="shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-auralis" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function fmtTime(iso: string) {
  if (!iso || iso === "—") return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").replace(/:\d\d\.\d+Z$/, "Z");
}
