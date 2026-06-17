import {
  Boxes,
  FileCode2,
  Layers,
  Plug,
  ShieldCheck,
  Sparkles,
  Store,
  Zap,
  ArrowRight,
} from "lucide-react";
import { Badge, Button, Card, PageHeader, Panel, SectionHeader, Stat } from "@/components/ui/primitives";
import { getDomainPacks } from "@/lib/data";
import { PackCard } from "@/components/packs/pack-card";

/** The declarative manifest sections — what a market author writes, never the core. */
const MANIFEST_SECTIONS = [
  { key: "datasets", label: "datasets:", icon: Layers, note: "schemas · modalities · jurisdictions" },
  { key: "ontology", label: "ontology:", icon: Boxes, note: "semantic terms & relations" },
  { key: "connectors", label: "connectors:", icon: Plug, note: "sources resolved from registry" },
  { key: "policies", label: "access_policies:", icon: ShieldCheck, note: "obligations · DP · residency" },
];

export default async function PacksPage() {
  const packs = await getDomainPacks();
  const installed = packs.filter((p) => p.status === "active");
  const marketplace = packs.filter((p) => p.status !== "active");

  const totalDatasets = packs.reduce((s, p) => s + p.datasets, 0);
  const totalPolicies = packs.reduce((s, p) => s + p.policies, 0);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operate · Domain Marketplace"
        title="Onboard an entire market — declaratively"
        description="Every domain on Aegoria is a self-contained pack: datasets, ontology, connectors, models and access policies expressed as a manifest. The engine resolves them from a registry. No market is special-cased."
        actions={
          <>
            <Button variant="default" disabled>
              <FileCode2 size={15} /> Author a pack
            </Button>
            <Button variant="primary" disabled>
              <Store size={15} /> Browse marketplace
            </Button>
          </>
        }
      />

      {/* HERO — the core-never-changes pitch */}
      <Card glow className="relative overflow-hidden animate-fade-up">
        <div className="pointer-events-none absolute inset-0 bg-veil-glow opacity-70" />
        <div className="relative grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div>
            <Badge tone="auralis" dot>
              the one invariant
            </Badge>
            <h2 className="mt-3 font-display text-[24px] font-semibold leading-tight tracking-tight text-lumen text-balance">
              Onboard a domain in <span className="text-auralis">&lt; 1 day</span> — without touching
              the core engine.
            </h2>
            <p className="mt-2.5 max-w-xl text-[13px] leading-relaxed text-muted">
              Climate emissions and consumer credit run on the identical lakehouse, privacy fabric and
              carbon-aware scheduler. A new market is a manifest, not a migration. Infra swaps via
              adapters; markets arrive via packs; the engine never forks.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button variant="primary" disabled>
                <Zap size={15} /> Install a pack
              </Button>
              <span className="inline-flex items-center gap-1.5 text-[12px] text-faint">
                <Sparkles size={13} className="text-auralis" /> Manifest → live · no core change
              </span>
            </div>

            {/* Pipeline of guarantees */}
            <div className="mt-6 flex items-center gap-2 text-[11.5px] text-muted">
              <span className="rounded-md border border-hairline bg-veil-2 px-2 py-1">Write manifest</span>
              <ArrowRight size={13} className="text-faint" />
              <span className="rounded-md border border-hairline bg-veil-2 px-2 py-1">Register pack</span>
              <ArrowRight size={13} className="text-faint" />
              <span className="rounded-md border border-auralis/40 bg-auralis/10 px-2 py-1 text-auralis">
                Engine resolves & serves
              </span>
            </div>
          </div>

          {/* Manifest preview */}
          <div className="rounded-lg border border-hairline bg-veil/60 p-4">
            <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-wider text-faint">
              <FileCode2 size={13} /> domain-pack.yaml
            </div>
            <div className="space-y-2">
              {MANIFEST_SECTIONS.map((s) => (
                <div key={s.key} className="flex items-center justify-between rounded-md bg-veil-2/50 px-3 py-2">
                  <div className="flex items-center gap-2.5">
                    <s.icon size={14} className="text-auralis/80" />
                    <span className="font-mono text-[12px] text-lumen">{s.label}</span>
                  </div>
                  <span className="text-[11px] text-faint">{s.note}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between rounded-md border border-auralis/30 bg-auralis/5 px-3 py-2">
              <span className="font-mono text-[12px] text-auralis">core_compat: &quot;&gt;=0.1.0,&lt;1.0.0&quot;</span>
              <Badge tone="verdant">verified</Badge>
            </div>
          </div>
        </div>
      </Card>

      {/* Marketplace stat strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="animate-fade-up">
          <Stat label="Packs available" value={`${packs.length}`} unit={`${installed.length} installed`} />
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <Stat label="Datasets onboarded" value={`${totalDatasets}`} tone="pulse" hint="declared, not coded" />
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <Stat label="Policies enforced" value={`${totalPolicies}`} tone="verdant" hint="DP · residency · masking" />
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <Stat label="Core changes" value="0" tone="auralis" hint="across every onboarding" />
        </Card>
      </div>

      {/* Installed */}
      <div>
        <SectionHeader
          title="Installed domains"
          subtitle="Live packs serving production traffic on the shared engine."
          icon={<Boxes size={16} />}
          action={<Badge tone="verdant" dot>{installed.length} active</Badge>}
        />
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          {installed.map((p) => (
            <PackCard key={p.id} pack={p} />
          ))}
        </div>
      </div>

      {/* Marketplace */}
      <div>
        <SectionHeader
          title="Marketplace"
          subtitle="Ready-to-install packs from partner consortia. Inspect the manifest, then onboard in a day."
          icon={<Store size={16} />}
          action={<Badge tone="neutral">{marketplace.length} available</Badge>}
        />
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
          {marketplace.map((p) => (
            <PackCard key={p.id} pack={p} />
          ))}
        </div>
      </div>

      {/* Invariant footnote */}
      <Panel className="flex items-center gap-3 p-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
          <ShieldCheck size={16} />
        </span>
        <p className="text-[12.5px] leading-relaxed text-muted">
          <span className="text-lumen">The core engine is immutable by design.</span> Storage,
          catalog, compute and identity are swapped through adapter protocols; domains are described in
          declarative packs and resolved from the registry at bootstrap. That is why a finance pack and
          a climate pack coexist with zero bespoke engine code.
        </p>
      </Panel>
    </div>
  );
}
