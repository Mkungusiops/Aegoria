import {
  Users,
  Vote,
  Scale,
  Coins,
  ShieldCheck,
  Leaf,
  GitBranch,
  Gavel,
  HeartHandshake,
  ArrowUpRight,
} from "lucide-react";
import Link from "next/link";
import { Badge, Card, PageHeader, Panel, ProgressBar, SectionHeader, Stat } from "@/components/ui/primitives";
import { getProposals, getKpis } from "@/lib/data";
import { ProposalCard } from "@/components/governance/proposal-card";

/** KPI ids surfaced on the transparency strip, with an icon + destination. */
const TRANSPARENCY = [
  { id: "privacy", icon: ShieldCheck, href: "/trust" },
  { id: "carbon", icon: Leaf, href: "/carbon" },
  { id: "lineage", icon: GitBranch, href: "/lineage" },
] as const;

export default async function GovernancePage() {
  const [proposals, kpis] = await Promise.all([getProposals(), getKpis()]);

  const open = proposals.filter((p) => p.status === "open");
  const passed = proposals.filter((p) => p.status === "passed");
  const rejected = proposals.filter((p) => p.status === "rejected");
  const decided = proposals.filter((p) => p.status !== "open");
  const totalVoters = proposals.reduce((s, p) => s + p.participants, 0);

  const kpiById = (id: string) => kpis.find((k) => k.id === id);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Govern · Data Commons"
        title="The communities who contribute, decide"
        description="Aegoria is governed as a commons. Contributing organisations hold stake and vote on the policies that shape access, privacy and openness. Decisions are transparent, on the record, and bound to the platform's published guarantees."
        actions={<Badge tone="auralis" dot>{open.length} open votes</Badge>}
      />

      {/* Summary row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat label="Open proposals" value={`${open.length}`} hint="awaiting your stake" />
            <Vote size={18} className="text-auralis/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Passed" value={`${passed.length}`} tone="verdant" hint="enacted on platform" />
            <Gavel size={18} className="text-verdant/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Participants" value={`${totalVoters}`} tone="pulse" hint="cumulative votes cast" />
            <Users size={18} className="text-pulse/70" />
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat label="Rejected" value={`${rejected.length}`} tone="solar" hint="returned for revision" />
            <Scale size={18} className="text-solar/70" />
          </div>
        </Card>
      </div>

      {/* Open proposals + stake/voting explainer */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <SectionHeader
            title="Open for vote"
            subtitle="Live proposals. Stake is weighted by verified contribution — data-rich and data-poor members both have a seat."
            icon={<Vote size={16} />}
          />
          <div className="space-y-4">
            {open.map((p) => (
              <ProposalCard key={p.id} p={p} />
            ))}
            {open.length === 0 && (
              <Panel className="p-5 text-[12.5px] text-muted">No open proposals right now.</Panel>
            )}
          </div>
        </div>

        {/* How governance works */}
        <Card className="lg:self-start">
          <SectionHeader
            title="How the commons decides"
            subtitle="Stake-weighted, transparent, bound to guarantees."
            icon={<HeartHandshake size={16} />}
          />
          <ol className="mt-4 space-y-4">
            {[
              {
                icon: Coins,
                title: "Earn stake by contributing",
                body: "Datasets, quality rules and compute earn governance weight — a community's voice grows with what it shares.",
              },
              {
                icon: Vote,
                title: "Propose & vote openly",
                body: "Any member can table a proposal. Votes are public; a simple 60% majority of cast stake carries it.",
              },
              {
                icon: Gavel,
                title: "Decisions bind the platform",
                body: "A passed proposal updates policy packs — privacy floors, openness, signing — enforced by the engine.",
              },
            ].map((s) => (
              <li key={s.title} className="flex gap-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
                  <s.icon size={15} />
                </span>
                <div>
                  <div className="text-[12.5px] font-medium text-lumen">{s.title}</div>
                  <p className="mt-0.5 text-[11.5px] leading-relaxed text-muted">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-5 rounded-md border border-auralis/30 bg-auralis/5 p-3 text-[11.5px] leading-relaxed text-muted">
            <span className="text-auralis">Equity by design.</span> Previously data-poor members
            receive a participation floor so onboarding a market never means surrendering a voice.
          </div>
        </Card>
      </div>

      {/* Decided proposals */}
      {decided.length > 0 && (
        <div>
          <SectionHeader
            title="Recent decisions"
            subtitle="The public record of what the commons has enacted."
            icon={<Gavel size={16} />}
          />
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            {decided.map((p) => (
              <ProposalCard key={p.id} p={p} />
            ))}
          </div>
        </div>
      )}

      {/* Transparency strip — bound to published guarantees */}
      <div>
        <SectionHeader
          title="Bound to our guarantees"
          subtitle="Governance is accountable to the platform's published commitments — visible to every member, always."
          icon={<ShieldCheck size={16} />}
          action={
            <Link href="/" className="text-[12px] text-auralis hover:underline">
              Full KPI charter <ArrowUpRight size={12} className="inline" />
            </Link>
          }
        />
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          {TRANSPARENCY.map(({ id, icon: Icon, href }) => {
            const k = kpiById(id);
            if (!k) return null;
            return (
              <Link key={id} href={href} className="block">
                <Panel className="group p-4 transition-colors hover:border-auralis/30">
                  <div className="flex items-start justify-between">
                    <span className="text-[11.5px] uppercase tracking-wider text-faint">{k.label}</span>
                    <Icon size={16} className="text-auralis/70" />
                  </div>
                  <div className="mt-1.5 font-display text-[22px] font-semibold tabular-nums text-lumen">
                    {k.value}
                  </div>
                  <ProgressBar value={k.progress} tone={k.tone} className="mt-2.5" />
                  <div className="mt-2 flex items-center justify-between text-[10.5px] text-faint">
                    <span>{k.hint}</span>
                    <span className="text-muted">{k.target}</span>
                  </div>
                </Panel>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
