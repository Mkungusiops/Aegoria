"use client";

import * as React from "react";
import { Link2, Network, Sparkles, Unlink } from "lucide-react";
import type { GraphEntity, GraphRelation } from "@/lib/types";
import { Badge, Panel, type Tone } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import {
  GRAPH_COLORS,
  domainMeta,
  entityRadius,
  isCrossDomain,
  relationLabel,
} from "./theme";

interface Props {
  entities: GraphEntity[];
  relations: GraphRelation[];
}

// Abstract drawing space; rendered into a responsive viewBox.
const W = 760;
const H = 520;
const PAD = 64;

const project = (v: number, span: number) => PAD + v * (span - PAD * 2);

export function GraphExplorer({ entities, relations }: Props) {
  const byId = React.useMemo(() => new Map(entities.map((e) => [e.id, e])), [entities]);

  const positions = React.useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    for (const e of entities) map.set(e.id, { x: project(e.x, W), y: project(e.y, H) });
    return map;
  }, [entities]);

  const degree = React.useMemo(() => {
    const d = new Map<string, number>();
    for (const e of entities) d.set(e.id, 0);
    for (const r of relations) {
      d.set(r.from, (d.get(r.from) ?? 0) + 1);
      d.set(r.to, (d.get(r.to) ?? 0) + 1);
    }
    return d;
  }, [entities, relations]);

  const crossLinks = React.useMemo(
    () => relations.filter((r) => isCrossDomain(r, byId)),
    [relations, byId],
  );

  const [active, setActive] = React.useState<string | null>(null);

  const neighborIds = React.useMemo(() => {
    const s = new Set<string>();
    if (!active) return s;
    for (const r of relations) {
      if (r.from === active) s.add(r.to);
      if (r.to === active) s.add(r.from);
    }
    return s;
  }, [active, relations]);

  const activeEntity = active ? byId.get(active) ?? null : null;
  const activeRelations = active
    ? relations.filter((r) => r.from === active || r.to === active)
    : [];

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      {/* ------------------------------------------------------- Graph canvas */}
      <div className="surface relative overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
          <div className="flex items-center gap-2 text-[12.5px] text-muted">
            <Network size={14} className="text-auralis" />
            <span className="text-lumen">Resolved entity graph</span>
            <span className="text-faint">· {entities.length} entities · {relations.length} relations</span>
          </div>
          <Badge tone="pulse" dot>
            {crossLinks.length} cross-domain link{crossLinks.length === 1 ? "" : "s"}
          </Badge>
        </div>

        <div className="grid-bg">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            width="100%"
            className="block"
            style={{ maxHeight: 560 }}
            role="img"
            aria-label="Cross-domain knowledge graph"
            onClick={() => setActive(null)}
          >
            <defs>
              <filter id="kg-glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3.4" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <linearGradient id="kg-bridge" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor={GRAPH_COLORS.verdant} />
                <stop offset="1" stopColor={GRAPH_COLORS.auralis} />
              </linearGradient>
            </defs>

            {/* Relations */}
            <g>
              {relations.map((r) => {
                const a = positions.get(r.from);
                const b = positions.get(r.to);
                if (!a || !b) return null;
                const cross = isCrossDomain(r, byId);
                const touched = active != null && (r.from === active || r.to === active);
                const dim = active != null && !touched;
                const mx = (a.x + b.x) / 2;
                const my = (a.y + b.y) / 2;
                const label = relationLabel(r.type);
                return (
                  <g
                    key={`${r.from}-${r.to}-${r.type}`}
                    className="transition-opacity duration-200"
                    opacity={dim ? 0.12 : 1}
                  >
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke={cross ? "url(#kg-bridge)" : "#2A3552"}
                      strokeWidth={cross ? 2.4 : 1.4}
                      strokeOpacity={cross ? 0.95 : touched ? 0.8 : 0.5}
                      strokeDasharray={cross ? "1 0" : touched ? "1 0" : "4 4"}
                    />
                    {(cross || touched) && (
                      <g transform={`translate(${mx}, ${my})`}>
                        <rect
                          x={-(label.length * 3.1 + 8)}
                          y={-9}
                          width={label.length * 6.2 + 16}
                          height={18}
                          rx={9}
                          fill="#0B0F1A"
                          stroke={cross ? GRAPH_COLORS.auralis : "#2A3552"}
                          strokeOpacity={cross ? 0.7 : 0.5}
                        />
                        <text
                          x={0}
                          y={3.5}
                          textAnchor="middle"
                          fontSize={9.5}
                          fontFamily="var(--font-mono)"
                          fill={cross ? GRAPH_COLORS.auralis : "#93A1C0"}
                        >
                          {label}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}
            </g>

            {/* Entities */}
            <g>
              {entities.map((e) => {
                const p = positions.get(e.id)!;
                const dm = domainMeta(e.domain);
                const color = GRAPH_COLORS[dm.color];
                const deg = degree.get(e.id) ?? 0;
                const r = entityRadius(e, deg);
                const isActive = active === e.id;
                const isNeighbor = neighborIds.has(e.id);
                const dim = active != null && !isActive && !isNeighbor;
                // Entities that anchor a cross-domain bridge get a halo.
                const bridges = crossLinks.some((c) => c.from === e.id || c.to === e.id);
                return (
                  <g
                    key={e.id}
                    transform={`translate(${p.x}, ${p.y})`}
                    className="cursor-pointer transition-opacity duration-200"
                    opacity={dim ? 0.3 : 1}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      setActive(isActive ? null : e.id);
                    }}
                  >
                    {bridges && (
                      <circle r={r + 7} fill="none" stroke={color} strokeOpacity={0.35} strokeWidth={1} strokeDasharray="3 3" />
                    )}
                    <circle
                      r={r}
                      fill="#0B0F1A"
                      stroke={color}
                      strokeWidth={isActive ? 2.6 : 1.6}
                      filter={isActive || bridges ? "url(#kg-glow)" : undefined}
                    />
                    <circle r={r} fill={color} fillOpacity={isActive ? 0.22 : 0.12} />
                    <text
                      y={r + 14}
                      textAnchor="middle"
                      fontSize={11}
                      fontFamily="var(--font-sans)"
                      fontWeight={600}
                      fill="#EAF1FF"
                    >
                      {e.label}
                    </text>
                    <text
                      y={r + 26}
                      textAnchor="middle"
                      fontSize={9}
                      fontFamily="var(--font-mono)"
                      fill="#5C6B8A"
                    >
                      {e.type}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-hairline px-4 py-3 text-[11.5px]">
          {Array.from(new Set(entities.map((e) => e.domain))).map((d) => {
            const m = domainMeta(d);
            return (
              <span key={d} className="inline-flex items-center gap-1.5 text-muted">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: GRAPH_COLORS[m.color] }} />
                {m.label}
              </span>
            );
          })}
          <span className="inline-flex items-center gap-1.5 text-muted">
            <span className="h-0.5 w-5 rounded-full" style={{ background: "linear-gradient(90deg,#57E08A,#16E0C4)" }} />
            cross-domain resolution
          </span>
          <span className="ml-auto text-faint">Click an entity to focus its neighbourhood</span>
        </div>
      </div>

      {/* ------------------------------------------------------ Detail panel */}
      <GraphPanel
        entity={activeEntity}
        relations={activeRelations}
        byId={byId}
        crossCount={crossLinks.length}
        onPick={(id) => setActive(id)}
      />
    </div>
  );
}

/* ------------------------------------------------------------------- Panel */
function GraphPanel({
  entity,
  relations,
  byId,
  crossCount,
  onPick,
}: {
  entity: GraphEntity | null;
  relations: GraphRelation[];
  byId: Map<string, GraphEntity>;
  crossCount: number;
  onPick: (id: string) => void;
}) {
  if (!entity) {
    return (
      <Panel className="flex flex-col gap-4 p-5">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
            <Sparkles size={16} />
          </span>
          <h3 className="font-display text-[15px] font-semibold tracking-tight text-lumen">Entity resolution</h3>
        </div>
        <p className="text-[12.5px] leading-relaxed text-muted">
          The knowledge graph fuses entities that domains describe in isolation. A
          steel plant in the <span className="text-verdant">climate</span> pack and a
          lender in the <span className="text-auralis">credit</span> pack are resolved
          to the same real-world corporate group — without either pack knowing about
          the other.
        </p>
        <div className="rounded-md border border-hairline bg-veil-1/60 p-3.5">
          <div className="flex items-center gap-2 text-[12px] text-lumen">
            <Link2 size={14} className="text-pulse" />
            {crossCount} cross-domain resolution{crossCount === 1 ? "" : "s"}
          </div>
          <p className="mt-1.5 text-[11.5px] leading-relaxed text-faint">
            Each link breaks a data silo while honouring per-domain access policy —
            relationships are visible, underlying PII is not.
          </p>
        </div>
        <p className="text-[11.5px] text-faint">Select an entity in the graph to inspect its resolved relationships.</p>
      </Panel>
    );
  }

  const dm = domainMeta(entity.domain);
  const tone: Tone = dm.color === "muted" ? "neutral" : dm.color;

  return (
    <Panel className="flex flex-col p-0">
      <div className="border-b border-hairline p-4">
        <div className="flex items-center justify-between">
          <Badge tone="neutral">{entity.type}</Badge>
          <Badge tone={tone} dot>
            {dm.label}
          </Badge>
        </div>
        <h3 className="mt-3 font-display text-[18px] font-semibold tracking-tight text-lumen">{entity.label}</h3>
        <p className="mt-0.5 break-all font-mono text-[10.5px] text-faint">{entity.id}</p>
      </div>

      <div className="p-4">
        <div className="mb-2.5 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-faint">
          <Network size={13} className="text-auralis" /> Resolved relations
          <span className="text-faint/70">· {relations.length}</span>
        </div>
        {relations.length === 0 ? (
          <p className="text-[11.5px] text-faint">No relations recorded.</p>
        ) : (
          <ul className="space-y-1.5">
            {relations.map((r) => {
              const otherId = r.from === entity.id ? r.to : r.from;
              const other = byId.get(otherId);
              if (!other) return null;
              const cross = isCrossDomain(r, byId);
              const odm = domainMeta(other.domain);
              const outgoing = r.from === entity.id;
              return (
                <li key={`${r.from}-${r.to}-${r.type}`}>
                  <button
                    onClick={() => onPick(otherId)}
                    className={cn(
                      "group flex w-full flex-col gap-1 rounded-md border bg-veil-1/60 px-2.5 py-2 text-left transition-colors hover:bg-veil-2",
                      cross ? "border-auralis/40" : "border-hairline hover:border-auralis/40",
                    )}
                  >
                    <div className="flex items-center gap-1.5 font-mono text-[10px] text-faint">
                      {cross && <Link2 size={11} className="text-auralis" />}
                      <span className={cn(cross && "text-auralis")}>{outgoing ? "" : "← "}{relationLabel(r.type)}{outgoing ? " →" : ""}</span>
                      {cross && <span className="ml-auto rounded-full border border-auralis/30 bg-auralis/10 px-1.5 text-[8.5px] text-auralis">cross-domain</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: GRAPH_COLORS[odm.color] }} />
                      <span className="min-w-0 flex-1 truncate text-[12.5px] text-lumen">{other.label}</span>
                      <span className="shrink-0 font-mono text-[9.5px] text-faint">{other.type}</span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="mt-auto border-t border-hairline p-4">
        {relations.some((r) => isCrossDomain(r, byId)) ? (
          <p className="flex items-start gap-2 text-[11.5px] leading-relaxed text-muted">
            <Link2 size={14} className="mt-0.5 shrink-0 text-auralis" />
            This entity sits on a cross-domain bridge — its identity is resolved across
            otherwise-siloed market packs.
          </p>
        ) : (
          <p className="flex items-start gap-2 text-[11.5px] leading-relaxed text-faint">
            <Unlink size={14} className="mt-0.5 shrink-0" />
            All relations stay within {dm.label}. Cross-domain links surface only when
            resolution confidence clears the threshold.
          </p>
        )}
      </div>
    </Panel>
  );
}
