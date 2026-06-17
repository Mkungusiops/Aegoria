import Link from "next/link";
import { Activity, Cpu, Gauge, Leaf, MapPin, TerminalSquare, Wind, Zap } from "lucide-react";
import { Badge, Button, Card, PageHeader, Panel, SectionHeader, Stat } from "@/components/ui/primitives";
import { AreaChart, BarSeries, RadialGauge } from "@/components/ui/charts";
import { getCarbon, getOverview, fmtNum } from "@/lib/data";
import { RegionTable } from "@/components/carbon/region-table";
import { PlacementExplainer } from "@/components/carbon/placement-explainer";
import { SavingsCompare } from "@/components/carbon/savings-compare";
import { intensityTone } from "@/components/carbon/intensity";

export default async function CarbonPage() {
  const [carbon, o] = await Promise.all([getCarbon(), getOverview()]);

  const sorted = [...carbon].sort((a, b) => a.gco2PerKwh - b.gco2PerKwh);
  const greenest = sorted[0];
  const local = carbon.find((c) => c.region === "local") ?? sorted[sorted.length - 1];

  // Carbon-aware vs naive baseline. The platform's headline carbon/query is the
  // aware figure; the naive figure derives from the same compute placed on the
  // caller's (dirtier) local grid — scaled by the relative grid intensity.
  const awareG = o.carbonPerQuery;
  const naiveG = +(awareG * (local.gco2PerKwh / greenest.gco2PerKwh)).toFixed(2);
  const savedPct = Math.round(o.carbonSaved * 100);

  // Daily energy + cost dashboard, derived consistently from the live figures.
  const queriesToday = o.queriesToday;
  const kwhPerQuery = 0.0009; // ~0.9 Wh / query at TB-scale
  const energyKwh = queriesToday * kwhPerQuery;
  const dailyCarbonKg = (queriesToday * awareG) / 1000;
  const naiveCarbonKg = (queriesToday * naiveG) / 1000;
  const energyCostUsd = energyKwh * 0.14; // blended $/kWh

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Carbon & Compute"
        title="Every query routed to the greenest grid"
        description="Compute is a climate decision. Aegoria's carbon-aware scheduler measures live grid intensity per region and relocates eligible work to the cleanest residency-compliant location — cutting emissions without touching the core engine. Sustainability is the optimization; compliance is the constraint."
        actions={
          <>
            <Link href="/pipelines">
              <Button variant="default">
                <Activity size={15} /> Pipelines
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

      {/* Metric row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat
              label="Carbon / query"
              value={`${awareG}`}
              unit="gCO₂"
              delta={{ value: `−${savedPct}% vs naive`, positive: true }}
              tone="verdant"
            />
            <Leaf size={18} className="text-verdant/70" />
          </div>
          <AreaChart data={o.carbonSeries} color="verdant" height={40} className="mt-3" />
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Greenest region" value={greenest.region} hint="scheduler pick" tone="verdant" />
            <MapPin size={18} className="text-verdant/70" />
          </div>
          <div className="mt-3 flex items-center gap-2 text-[11.5px]">
            <Badge tone="verdant">{greenest.gco2PerKwh} gCO₂/kWh</Badge>
            <span className="text-faint">{Math.round(greenest.renewableFraction * 100)}% renewable</span>
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Energy today" value={energyKwh.toFixed(1)} unit="kWh" hint={`${fmtNum(queriesToday)} queries`} tone="ion" />
            <Zap size={18} className="text-ion/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            ≈ <span className="text-lumen">${energyCostUsd.toFixed(2)}</span> blended grid cost
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat label="Carbon avoided" value={`${(naiveCarbonKg - dailyCarbonKg).toFixed(1)}`} unit="kg/day" tone="verdant" delta={{ value: "vs same-region", positive: true }} />
            <Wind size={18} className="text-verdant/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            <span className="text-lumen">{dailyCarbonKg.toFixed(1)}kg</span> emitted vs {naiveCarbonKg.toFixed(1)}kg naive
          </div>
        </Card>
      </div>

      {/* Regions + savings gauge */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Regional grid carbon intensity"
            subtitle="Live gCO₂/kWh per region, greenest-first. The scheduler always prefers the lowest-carbon eligible region."
            icon={<Leaf size={16} />}
            action={<Badge tone="verdant" dot>live grid feed</Badge>}
          />
          <div className="mt-5">
            <RegionTable regions={carbon} />
          </div>
        </Card>

        <Card className="flex flex-col">
          <SectionHeader title="Carbon-aware advantage" subtitle="Emissions cut vs naive placement." icon={<Gauge size={16} />} />
          <div className="mt-4 flex flex-1 flex-col items-center justify-center gap-5">
            <RadialGauge value={savedPct} color="verdant" label={`${savedPct}%`} sublabel="saved" />
            <div className="w-full space-y-2.5">
              <div className="flex items-center justify-between rounded-md bg-veil-2/40 px-3 py-2 text-[11.5px]">
                <span className="text-muted">Aware placement</span>
                <span className="font-medium tabular-nums text-verdant">{awareG} gCO₂</span>
              </div>
              <div className="flex items-center justify-between rounded-md bg-veil-2/40 px-3 py-2 text-[11.5px]">
                <span className="text-muted">Naive (local) baseline</span>
                <span className="font-medium tabular-nums text-crimson">{naiveG} gCO₂</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Placement walkthrough */}
      <Card>
        <SectionHeader
          title="How a query is placed"
          subtitle="The carbon-aware scheduler filters on residency first, then ranks survivors by live grid intensity — identical logic for every domain."
          icon={<Cpu size={16} />}
        />
        <div className="mt-5">
          <PlacementExplainer regions={carbon} />
        </div>
      </Card>

      {/* Trend + savings + energy */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Carbon per query — trend"
            subtitle="Grams of CO₂ per governed query over the trailing quarter, as carbon-aware placement matured."
            icon={<Activity size={16} />}
            action={
              <Badge tone="verdant">
                {o.carbonSeries[0]}g → {o.carbonSeries[o.carbonSeries.length - 1]}g
              </Badge>
            }
          />
          <div className="mt-5">
            <AreaChart
              data={o.carbonSeries}
              color="verdant"
              height={180}
              labels={["", "Mar", "", "Apr", "", "May", "", "Jun", "", "", "", "now"]}
            />
          </div>
        </Card>

        <Card>
          <SectionHeader title="Carbon vs naive baseline" subtitle="Same work, two schedulers." icon={<Leaf size={16} />} />
          <div className="mt-5">
            <SavingsCompare awareG={awareG} naiveG={naiveG} />
          </div>
        </Card>
      </div>

      {/* Energy + cost dashboard */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Renewable mix by region"
            subtitle="Share of clean generation behind each compute region — higher is greener."
            icon={<Wind size={16} />}
          />
          <div className="mt-6">
            <BarSeries
              data={sorted.map((r) => ({
                label: r.region,
                value: Math.round(r.renewableFraction * 100),
                color: intensityTone(r.gco2PerKwh),
              }))}
              height={150}
            />
          </div>
          <p className="mt-2 text-[11px] text-faint">Renewable fraction (%) per region — the scheduler biases work toward the leftmost bars.</p>
        </Card>

        <Card>
          <SectionHeader title="Energy & cost" subtitle="Today, across all engines." icon={<Zap size={16} />} />
          <div className="mt-5 space-y-3">
            <EnergyRow label="Compute energy" value={`${energyKwh.toFixed(1)} kWh`} sub={`${fmtNum(queriesToday)} queries · ~0.9 Wh ea`} tone="ion" />
            <EnergyRow label="Grid cost" value={`$${energyCostUsd.toFixed(2)}`} sub="blended $0.14 / kWh" tone="solar" />
            <EnergyRow label="Emissions (aware)" value={`${dailyCarbonKg.toFixed(1)} kg`} sub={`${awareG} gCO₂ / query`} tone="verdant" />
            <EnergyRow label="Emissions avoided" value={`${(naiveCarbonKg - dailyCarbonKg).toFixed(1)} kg`} sub={`vs ${naiveCarbonKg.toFixed(1)} kg naive`} tone="verdant" />
          </div>
          <Panel className="mt-4 p-3 text-[10.5px] leading-relaxed text-muted">
            Costs and emissions are reported on the same placement decision — choosing the greenest grid usually also
            lands on cheaper, renewables-backed capacity.
          </Panel>
        </Card>
      </div>
    </div>
  );
}

function EnergyRow({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "ion" | "solar" | "verdant";
}) {
  const color = { ion: "text-ion", solar: "text-solar", verdant: "text-verdant" }[tone];
  return (
    <div className="flex items-center justify-between rounded-md border border-hairline bg-veil-2/40 px-3 py-2.5">
      <div className="leading-tight">
        <div className="text-[12px] text-lumen">{label}</div>
        <div className="text-[10px] text-faint">{sub}</div>
      </div>
      <span className={`font-display text-[16px] font-semibold tabular-nums ${color}`}>{value}</span>
    </div>
  );
}
