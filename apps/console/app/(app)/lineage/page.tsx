import { BadgeCheck, GitBranch, Layers, ShieldCheck, Workflow } from "lucide-react";
import { Card, PageHeader, Panel, SectionHeader, Stat } from "@/components/ui/primitives";
import { getLineage } from "@/lib/data";
import { LineageExplorer } from "@/components/lineage/lineage-explorer";
import { NODE_COLORS, domainMeta, provenanceFor } from "@/components/lineage/theme";

export const metadata = {
  title: "Lineage & Provenance — Aegoria",
};

export default async function LineagePage() {
  const { nodes, edges } = await getLineage();

  const domains = Array.from(new Set(nodes.map((n) => n.domain)));
  const signed = nodes.filter((n) => provenanceFor(n.id).signed).length;
  const coverage = nodes.length ? Math.round((signed / nodes.length) * 100) : 0;
  const transforms = Array.from(new Set(edges.map((e) => e.operation)));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Observe · Lineage & Provenance"
        title="Every byte, traced from source to product"
        description="A single directed acyclic graph captures how raw signals become governed data products — across unrelated markets. Climate emissions and consumer credit flow through the same engine, each artifact carrying a C2PA-signed provenance manifest the moment it lands."
      />

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Lineage coverage" value="100%" hint="artifacts with full upstream" />
            <GitBranch size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Signed artifacts" value={`${signed}/${nodes.length}`} unit={`${coverage}%`} tone="verdant" hint="C2PA manifests" />
            <BadgeCheck size={18} className="text-verdant/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Transform types" value={`${transforms.length}`} tone="pulse" hint={transforms.join(" · ")} />
            <Workflow size={18} className="text-pulse/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat label="Independent lineages" value={`${domains.length}`} tone="solar" hint="one engine, many markets" />
            <Layers size={18} className="text-solar/70" />
          </div>
        </Card>
      </div>

      {/* The DAG explorer */}
      <div className="animate-fade-up [animation-delay:240ms]">
        <SectionHeader
          title="Interactive provenance graph"
          subtitle="Hover to trace a path; click a node to inspect its signature, checksum and neighbours. Two market lineages render side by side from pure topology — no bespoke layout per domain."
          icon={<GitBranch size={16} />}
        />
        <div className="mt-5">
          <LineageExplorer nodes={nodes} edges={edges} />
        </div>
      </div>

      {/* Per-domain pipelines + trust note */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Pipelines by domain"
            subtitle="Each domain-pack declares its own source → product chain. The core engine resolves and records lineage identically for all of them."
            icon={<Layers size={16} />}
          />
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {domains.map((d) => {
              const dm = domainMeta(d);
              const dn = nodes.filter((n) => n.domain === d);
              const de = edges.filter(
                (e) => dn.some((n) => n.id === e.from) || dn.some((n) => n.id === e.to),
              );
              const source = dn.find((n) => n.kind === "source" || n.kind === "stream");
              const product = dn.find((n) => n.kind === "product");
              return (
                <Panel key={d} className="p-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: NODE_COLORS[dm.color] }} />
                    <span className="text-[13px] font-medium text-lumen">{dm.label}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-1.5 font-mono text-[10.5px] text-muted">
                    <span className="rounded border border-hairline bg-veil-1/60 px-1.5 py-0.5">{source?.label ?? "source"}</span>
                    <span className="text-faint">→ … →</span>
                    <span className="rounded border border-hairline bg-veil-1/60 px-1.5 py-0.5 text-lumen">{product?.label ?? "product"}</span>
                  </div>
                  <div className="mt-3 flex gap-4 text-[11px] text-faint">
                    <span><span className="text-lumen">{dn.length}</span> artifacts</span>
                    <span><span className="text-lumen">{de.length}</span> transforms</span>
                  </div>
                </Panel>
              );
            })}
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="Why provenance matters"
            subtitle="Trust is a platform primitive."
            icon={<ShieldCheck size={16} />}
          />
          <ul className="mt-4 space-y-3 text-[12.5px] leading-relaxed text-muted">
            <li className="flex gap-2.5">
              <BadgeCheck size={15} className="mt-0.5 shrink-0 text-verdant" />
              <span>Every artifact is sealed with an <span className="text-lumen">Ed25519 / C2PA</span> manifest at ingest — tamper-evident from source to product.</span>
            </li>
            <li className="flex gap-2.5">
              <GitBranch size={15} className="mt-0.5 shrink-0 text-auralis" />
              <span>Lineage is captured by the engine, not authored by hand, so it stays complete as new domain-packs onboard.</span>
            </li>
            <li className="flex gap-2.5">
              <ShieldCheck size={15} className="mt-0.5 shrink-0 text-ion" />
              <span>Auditors can replay any product back to its raw inputs and verify each checksum independently.</span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
