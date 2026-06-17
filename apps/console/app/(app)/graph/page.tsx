import { Boxes, Link2, Network, ScanSearch, ShieldCheck } from "lucide-react";
import { Card, PageHeader, Panel, SectionHeader, Stat } from "@/components/ui/primitives";
import { getGraph } from "@/lib/data";
import { GraphExplorer } from "@/components/graph/graph-explorer";
import { GRAPH_COLORS, domainMeta, isCrossDomain } from "@/components/graph/theme";

export const metadata = {
  title: "Knowledge Graph — Aegoria",
};

export default async function GraphPage() {
  const { entities, relations } = await getGraph();

  const byId = new Map(entities.map((e) => [e.id, e]));
  const domains = Array.from(new Set(entities.map((e) => e.domain)));
  const types = Array.from(new Set(entities.map((e) => e.type)));
  const crossLinks = relations.filter((r) => isCrossDomain(r, byId));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Observe · Knowledge Graph"
        title="One identity layer, every sector"
        description="Domains describe the world in isolation — a facility here, a borrower there. Aegoria's entity-resolution layer fuses them into a single graph, breaking data silos while each market keeps its own governance. The result: a steel operator and a lender resolve to the same corporate group, across packs that never reference one another."
      />

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Entities resolved" value={`${entities.length}`} hint={`${types.length} types`} />
            <Network size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Relations" value={`${relations.length}`} tone="ion" hint="typed, directed edges" />
            <Link2 size={18} className="text-ion/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Cross-domain links" value={`${crossLinks.length}`} tone="pulse" hint="silos broken" />
            <ScanSearch size={18} className="text-pulse/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat label="Sectors joined" value={`${domains.filter((d) => d !== "shared").length}`} tone="verdant" hint="climate · finance" />
            <Boxes size={18} className="text-verdant/70" />
          </div>
        </Card>
      </div>

      {/* The graph */}
      <div className="animate-fade-up [animation-delay:240ms]">
        <SectionHeader
          title="Cross-domain entity resolution"
          subtitle="A force-directed graph of resolved entities. Gradient edges are cross-domain bridges — the links that connect markets the platform treats as fully independent."
          icon={<Network size={16} />}
        />
        <div className="mt-5">
          <GraphExplorer entities={entities} relations={relations} />
        </div>
      </div>

      {/* Explainers */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="How resolution breaks silos"
            subtitle="Entities arrive from independent domain-packs; the engine reconciles them into one identity layer without merging the underlying sensitive records."
            icon={<ScanSearch size={16} />}
          />
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <ResolutionStep
              n="01"
              title="Ingest in isolation"
              body="Each market pack lands its own entities — facilities, operators, institutions, borrowers — under its own schema and policy."
            />
            <ResolutionStep
              n="02"
              title="Resolve identities"
              body="The KnowledgeGraphService matches entities on shared signals and emits typed relations like operated_by and same_corporate_group."
            />
            <ResolutionStep
              n="03"
              title="Bridge, don't merge"
              body="Cross-domain links surface relationships for analysis while PII stays governed per-domain — relationships visible, raw data not."
            />
          </div>

          {crossLinks.length > 0 && (
            <div className="mt-5 rounded-md border border-auralis/30 bg-auralis/5 p-4">
              <div className="flex items-center gap-2 text-[12.5px] font-medium text-lumen">
                <Link2 size={15} className="text-auralis" /> Cross-domain bridges in this graph
              </div>
              <ul className="mt-3 space-y-2">
                {crossLinks.map((r) => {
                  const a = byId.get(r.from);
                  const b = byId.get(r.to);
                  if (!a || !b) return null;
                  return (
                    <li
                      key={`${r.from}-${r.to}-${r.type}`}
                      className="flex flex-wrap items-center gap-2 text-[12px]"
                    >
                      <span className="inline-flex items-center gap-1.5 text-lumen">
                        <span className="h-2 w-2 rounded-full" style={{ background: GRAPH_COLORS[domainMeta(a.domain).color] }} />
                        {a.label}
                      </span>
                      <span className="font-mono text-[10.5px] text-auralis">— {r.type.replace(/_/g, " ")} →</span>
                      <span className="inline-flex items-center gap-1.5 text-lumen">
                        <span className="h-2 w-2 rounded-full" style={{ background: GRAPH_COLORS[domainMeta(b.domain).color] }} />
                        {b.label}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </Card>

        <Card>
          <SectionHeader title="Entity inventory" subtitle="By domain and type." icon={<Boxes size={16} />} />
          <div className="mt-4 space-y-4">
            {domains.map((d) => {
              const dm = domainMeta(d);
              const items = entities.filter((e) => e.domain === d);
              return (
                <Panel key={d} className="p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-2 text-[12.5px] font-medium text-lumen">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: GRAPH_COLORS[dm.color] }} />
                      {dm.label}
                    </span>
                    <span className="text-[11px] text-faint">{items.length}</span>
                  </div>
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {items.map((e) => (
                      <span
                        key={e.id}
                        className="rounded-full border border-hairline bg-veil-1/60 px-2 py-0.5 text-[10.5px] text-muted"
                        title={`${e.label} · ${e.type}`}
                      >
                        {e.label}
                      </span>
                    ))}
                  </div>
                </Panel>
              );
            })}
          </div>
          <div className="mt-4 flex items-start gap-2 rounded-md border border-hairline bg-veil-1/60 p-3 text-[11.5px] leading-relaxed text-muted">
            <ShieldCheck size={14} className="mt-0.5 shrink-0 text-verdant" />
            Resolution runs under the same governance fabric — joins are policy-checked,
            so analysts see the graph without ever touching protected attributes.
          </div>
        </Card>
      </div>
    </div>
  );
}

function ResolutionStep({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <Panel className="p-4">
      <div className="font-display text-[13px] font-semibold text-auralis">{n}</div>
      <div className="mt-1.5 text-[13px] font-medium text-lumen">{title}</div>
      <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">{body}</p>
    </Panel>
  );
}
