import Link from "next/link";
import {
  ArrowUpRight,
  Boxes,
  Database,
  Leaf,
  Plus,
  ShieldCheck,
  TerminalSquare,
  Sparkles,
  Globe2,
} from "lucide-react";
import { Badge, Button, Card, Divider, PageHeader, Panel, ProgressBar, SectionHeader, Stat } from "@/components/ui/primitives";
import { AreaChart, BarSeries, RadialGauge, Sparkline } from "@/components/ui/charts";
import { getCarbon, getDomainPacks, getKpis, getOverview, getQueryRuns, fmtNum } from "@/lib/data";

export default async function CommandCenter() {
  const [o, kpis, packs, carbon, queries] = await Promise.all([
    getOverview(),
    getKpis(),
    getDomainPacks(),
    getCarbon(),
    getQueryRuns(),
  ]);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Command Center"
        title="Planetary data, under one trusted lens"
        description="Aegoria runs an identical core engine across every market. Climate emissions and consumer credit live side by side — same lakehouse, same privacy fabric, same carbon-aware compute — proving the platform is genuinely domain-neutral."
        actions={
          <>
            <Link href="/packs">
              <Button variant="default">
                <Plus size={15} /> Onboard domain
              </Button>
            </Link>
            <Link href="/query">
              <Button variant="primary">
                <TerminalSquare size={15} /> Query Studio
              </Button>
            </Link>
          </>
        }
      />

      {/* Hero metric row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Rows indexed" value={fmtNum(o.rowsIndexed)} delta={{ value: "+8.2% / wk", positive: true }} />
            <Database size={18} className="text-auralis/70" />
          </div>
          <Sparkline data={o.ingestSeries} color="auralis" className="mt-3 w-full" width={240} height={40} />
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Datasets · domains" value={`${o.datasets}`} unit={`/ ${o.domains} domains`} hint="market-agnostic" />
            <Boxes size={18} className="text-pulse/70" />
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {packs.slice(0, 4).map((p) => (
              <Badge key={p.id} tone={p.color}>
                {p.id.split("-")[0]}
              </Badge>
            ))}
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Orgs empowered" value={`${o.orgsOnboarded}`} delta={{ value: "12 previously data-poor", positive: true }} tone="solar" />
            <Globe2 size={18} className="text-solar/70" />
          </div>
          <div className="mt-4 text-[12px] text-muted">
            Across <span className="text-lumen">{o.sectorsOnboarded} sectors</span> and 3 continents, including offline-first edge nodes.
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat label="Carbon / query" value={`${o.carbonPerQuery}`} unit="gCO₂" delta={{ value: `−${Math.round(o.carbonSaved * 100)}% vs naive`, positive: true }} tone="verdant" />
            <Leaf size={18} className="text-verdant/70" />
          </div>
          <Sparkline data={o.carbonSeries} color="verdant" className="mt-3 w-full" width={240} height={40} />
        </Card>
      </div>

      {/* Throughput + carbon focus */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Ingest throughput"
            subtitle="Multi-modal records per minute across all domains — structured, imagery, geospatial and streaming."
            icon={<Database size={16} />}
            action={<Badge tone="auralis" dot>live</Badge>}
          />
          <div className="mt-5">
            <AreaChart
              data={o.ingestSeries}
              color="auralis"
              height={180}
              labels={["", "Mar", "", "Apr", "", "May", "", "Jun", "", "", "", "now"]}
            />
          </div>
        </Card>

        <Card>
          <SectionHeader title="Carbon-aware compute" subtitle="Greenest capable region wins." icon={<Leaf size={16} />} />
          <div className="mt-4 flex items-center justify-around">
            <RadialGauge value={o.carbonSaved * 100} color="verdant" label={`${Math.round(o.carbonSaved * 100)}%`} sublabel="saved" />
            <div className="space-y-3">
              {carbon.slice(0, 4).map((c) => (
                <div key={c.region} className="flex items-center gap-2.5">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: c.gco2PerKwh < 60 ? "#57E08A" : c.gco2PerKwh < 300 ? "#FFB454" : "#FF5C72" }}
                  />
                  <span className="w-16 text-[12px] text-lumen">{c.region}</span>
                  <span className="text-[11.5px] tabular-nums text-faint">{c.gco2PerKwh} g</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* KPI strip */}
      <div>
        <SectionHeader
          title="Platform KPIs"
          subtitle="Every success metric the platform commits to — measured continuously."
          icon={<Sparkles size={16} />}
          action={
            <Link href="/governance" className="text-[12px] text-auralis hover:underline">
              View charter <ArrowUpRight size={12} className="inline" />
            </Link>
          }
        />
        <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
          {kpis.map((k) => (
            <Panel key={k.id} className="p-4">
              <div className="flex items-baseline justify-between">
                <span className="text-[11.5px] uppercase tracking-wider text-faint">{k.label}</span>
              </div>
              <div className="mt-1.5 font-display text-[22px] font-semibold tabular-nums text-lumen">{k.value}</div>
              <ProgressBar value={k.progress} tone={k.tone} className="mt-2.5" />
              <div className="mt-2 flex items-center justify-between text-[10.5px] text-faint">
                <span>{k.hint}</span>
                <span className="text-muted">{k.target}</span>
              </div>
            </Panel>
          ))}
        </div>
      </div>

      {/* Governed queries + domain breadth */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Recent governed queries"
            subtitle="Every query is authorized, placed for low carbon, and privacy-enforced before results return."
            icon={<ShieldCheck size={16} />}
          />
          <div className="mt-4 overflow-hidden rounded-md border border-hairline">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="border-b border-hairline bg-veil-2/60 text-left text-[11px] uppercase tracking-wider text-faint">
                  <th className="px-3 py-2 font-medium">Query</th>
                  <th className="px-3 py-2 font-medium">Principal</th>
                  <th className="px-3 py-2 font-medium">Engine · region</th>
                  <th className="px-3 py-2 text-right font-medium">Carbon</th>
                  <th className="px-3 py-2 text-right font-medium">Privacy</th>
                  <th className="px-3 py-2 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {queries.map((q) => (
                  <tr key={q.id} className="border-b border-hairline/60 last:border-0 hover:bg-veil-2/40">
                    <td className="max-w-[220px] truncate px-3 py-2.5 font-mono text-[11.5px] text-muted">{q.sql}</td>
                    <td className="px-3 py-2.5 text-lumen">{q.principal}</td>
                    <td className="px-3 py-2.5 text-muted">{q.engine === "—" ? "—" : `${q.engine} · ${q.region}`}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-verdant">{q.carbonG ? `${q.carbonG}g` : "—"}</td>
                    <td className="px-3 py-2.5 text-right">
                      {q.dpApplied ? <Badge tone="pulse">ε {q.epsilonSpent}</Badge> : <span className="text-faint">—</span>}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <Badge tone={q.status === "ok" ? "verdant" : q.status === "denied" ? "crimson" : "ion"}>{q.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <SectionHeader title="Domains live" subtitle="Onboarded declaratively — core untouched." icon={<Boxes size={16} />} />
          <div className="mt-4 space-y-3">
            {packs.map((p) => (
              <Link key={p.id} href="/packs" className="block">
                <div className="group rounded-md border border-hairline bg-veil-2/40 p-3 transition-colors hover:border-auralis/30">
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-medium text-lumen">{p.name.split(" · ")[0]}</span>
                    <Badge tone={p.status === "active" ? p.color : "neutral"}>{p.status}</Badge>
                  </div>
                  <div className="mt-1 truncate text-[11.5px] text-faint">{p.name.split(" · ")[1]}</div>
                  <div className="mt-2 flex gap-3 text-[11px] text-muted">
                    <span>{p.datasets} datasets</span>
                    <span>{p.qualityRules} rules</span>
                    <span>{p.models} models</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
          <Divider className="my-4" />
          <Link href="/packs">
            <Button variant="default" className="w-full justify-center">
              Explore the domain marketplace
            </Button>
          </Link>
        </Card>
      </div>
    </div>
  );
}
