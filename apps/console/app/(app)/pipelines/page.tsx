import {
  Workflow,
  Activity,
  Gauge,
  Radio,
  Layers,
  Timer,
  Image as ImageIcon,
  Database,
  Waves,
} from "lucide-react";
import { Badge, Card, PageHeader, Panel, SectionHeader, Stat } from "@/components/ui/primitives";
import { AreaChart } from "@/components/ui/charts";
import { getOverview, getPipelines, getDomainPacks, fmtNum } from "@/lib/data";
import type { Modality } from "@/lib/types";
import { PipelineRow } from "@/components/pipelines/pipeline-row";
import { MODALITY_META, freshnessSlo } from "@/components/pipelines/pipeline-utils";

/** Icon per modality for the multi-modal coverage strip. */
const MODALITY_ICON: Partial<Record<Modality, typeof Database>> = {
  imagery: ImageIcon,
  sensor_stream: Radio,
  structured: Database,
  time_series: Activity,
  geospatial: Layers,
  event_stream: Waves,
  text: Layers,
};

export default async function PipelinesPage() {
  const [pipelines, packs, overview] = await Promise.all([
    getPipelines(),
    getDomainPacks(),
    getOverview(),
  ]);

  // ---- Summary aggregates -------------------------------------------------
  const totalThroughput = pipelines.reduce((s, p) => s + p.recordsPerMin, 0);
  const streaming = pipelines.filter((p) => p.schedule === "streaming");
  const batch = pipelines.filter((p) => p.schedule !== "streaming");
  const withinSlo = pipelines.filter((p) => freshnessSlo(p.schedule, p.freshnessSec).withinSlo);
  const sloPct = pipelines.length ? Math.round((withinSlo.length / pipelines.length) * 100) : 100;
  const attention = pipelines.filter((p) => p.status === "degraded" || p.status === "failed");

  // Distinct modalities currently flowing through ingestion.
  const activeModalities = Array.from(new Set(pipelines.map((p) => p.modality)));

  // ---- Group by domain ----------------------------------------------------
  const domainName = (id: string) =>
    packs.find((p) => p.id === id)?.name.split(" · ")[0] ?? id;
  const byDomain = pipelines.reduce<Record<string, typeof pipelines>>((acc, p) => {
    (acc[p.domain] ??= []).push(p);
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Operate · Ingestion"
        title="Multi-modal ingestion, always in motion"
        description="Imagery tiles, real-time sensor meshes and nightly structured batches all flow through one orchestration plane — the same core engine, no per-modality forks. Throughput and freshness SLOs are watched continuously."
        actions={<Badge tone="auralis" dot>live</Badge>}
      />

      {/* Summary header */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat
              label="Total throughput"
              value={fmtNum(totalThroughput)}
              unit="rec / min"
              delta={{ value: "+8.2% / wk", positive: true }}
            />
            <Gauge size={18} className="text-auralis/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            {fmtNum(overview.rowsIndexed)} rows indexed lifetime
          </div>
        </Card>

        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="Freshness SLO"
              value={`${sloPct}%`}
              unit={`${withinSlo.length}/${pipelines.length}`}
              tone={sloPct >= 90 ? "verdant" : "solar"}
              hint="feeds within target"
            />
            <Timer size={18} className="text-verdant/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            Streaming ≤ 30s · batch ≤ 4h windows
          </div>
        </Card>

        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="Active pipelines"
              value={`${pipelines.length}`}
              unit={`${streaming.length} stream · ${batch.length} batch`}
              tone="pulse"
            />
            <Workflow size={18} className="text-pulse/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            Across {Object.keys(byDomain).length} domains, one orchestrator
          </div>
        </Card>

        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="Needs attention"
              value={`${attention.length}`}
              tone={attention.length === 0 ? "verdant" : "solar"}
              hint={attention.length === 0 ? "all nominal" : attention.map((p) => p.status).join(" · ")}
            />
            <Activity size={18} className={attention.length === 0 ? "text-verdant/70" : "text-solar/70"} />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            {attention.length === 0
              ? "Every feed healthy or streaming"
              : `${attention.map((p) => p.name).join(", ")}`}
          </div>
        </Card>
      </div>

      {/* Multi-modal coverage + aggregate throughput */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Aggregate ingest throughput"
            subtitle="Records per minute summed across every modality and domain — the same pipeline plane handles all of it."
            icon={<Activity size={16} />}
            action={<Badge tone="auralis" dot>live</Badge>}
          />
          <div className="mt-5">
            <AreaChart
              data={overview.ingestSeries}
              color="auralis"
              height={170}
              labels={["", "Mar", "", "Apr", "", "May", "", "Jun", "", "", "", "now"]}
            />
          </div>
        </Card>

        <Card>
          <SectionHeader
            title="Modalities in flight"
            subtitle="One engine, many shapes of data."
            icon={<Layers size={16} />}
          />
          <div className="mt-4 space-y-2.5">
            {activeModalities.map((m) => {
              const meta = MODALITY_META[m];
              const Icon = MODALITY_ICON[m] ?? Database;
              const feeds = pipelines.filter((p) => p.modality === m);
              const rpm = feeds.reduce((s, p) => s + p.recordsPerMin, 0);
              return (
                <div
                  key={m}
                  className="flex items-center justify-between rounded-md border border-hairline bg-veil-2/40 px-3 py-2.5"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon size={15} className="text-auralis/80" />
                    <span className="text-[12.5px] text-lumen">{meta.label}</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <span className="text-[11px] tabular-nums text-faint">{fmtNum(rpm)}/m</span>
                    <Badge tone={meta.tone}>{feeds.length}</Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Per-domain pipeline groups */}
      <div className="space-y-6">
        {Object.entries(byDomain).map(([domain, feeds]) => {
          const domThroughput = feeds.reduce((s, p) => s + p.recordsPerMin, 0);
          const domSlo = feeds.every((p) => freshnessSlo(p.schedule, p.freshnessSec).withinSlo);
          return (
            <div key={domain}>
              <SectionHeader
                title={domainName(domain)}
                subtitle={`${feeds.length} pipeline${feeds.length > 1 ? "s" : ""} · ${fmtNum(domThroughput)} rec/min`}
                icon={<Database size={16} />}
                action={
                  <Badge tone={domSlo ? "verdant" : "solar"} dot>
                    {domSlo ? "SLOs met" : "SLO risk"}
                  </Badge>
                }
              />
              {/* Column header for the rows below */}
              <div className="mt-4 hidden grid-cols-12 gap-3 px-3.5 text-[10.5px] uppercase tracking-wider text-faint lg:grid">
                <span className="col-span-4">Pipeline · modality</span>
                <span className="col-span-3">Throughput</span>
                <span className="col-span-2">Records / min</span>
                <span className="col-span-2">Freshness</span>
                <span className="col-span-1 text-right">Status</span>
              </div>
              <div className="mt-2 space-y-2">
                {feeds.map((p) => (
                  <PipelineRow key={p.id} p={p} />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Invariant footnote */}
      <Panel className="flex items-center gap-3 p-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
          <Workflow size={16} />
        </span>
        <p className="text-[12.5px] leading-relaxed text-muted">
          <span className="text-lumen">One orchestration plane, every modality.</span> Connectors are
          declared in domain-pack manifests; the engine resolves them from the registry. Adding a new
          source — a satellite feed, an IoT mesh, a nightly bureau drop — never changes the core.
        </p>
      </Panel>
    </div>
  );
}
