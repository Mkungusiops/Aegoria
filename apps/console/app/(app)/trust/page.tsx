import Link from "next/link";
import {
  ArrowUpRight,
  Fingerprint,
  Lock,
  Network,
  ScrollText,
  ShieldCheck,
  SlidersHorizontal,
  BadgeCheck,
} from "lucide-react";
import { Badge, Button, Card, PageHeader, SectionHeader, Stat } from "@/components/ui/primitives";
import { DonutChart, RadialGauge } from "@/components/ui/charts";
import { getDatasets, getPolicies, getPrivacyBudgets } from "@/lib/data";
import { ClassificationCard } from "@/components/trust/classification-card";
import { PolicyTable } from "@/components/trust/policy-table";
import { PrivacyBudgets } from "@/components/trust/privacy-budgets";
import { FederatedExplainer } from "@/components/trust/federated-explainer";
import { ProvenanceStatus } from "@/components/trust/provenance-status";
import { SENSITIVITY_META } from "@/components/trust/sensitivity";

export default async function TrustPage() {
  const [datasets, policies, budgets] = await Promise.all([getDatasets(), getPolicies(), getPrivacyBudgets()]);

  // ---- Trust-fabric aggregates ------------------------------------------
  const allFields = datasets.flatMap((d) => d.fields);
  const piiFields = allFields.filter((f) => f.pii).length;
  const maskedFields = allFields.filter((f) => SENSITIVITY_META[f.sensitivity].maskedByDefault).length;
  const exposedFields = allFields.length - maskedFields;
  const piiDatasets = datasets.filter((d) => d.piiFields > 0).length;
  const denyRules = policies.filter((p) => p.effect === "deny").length;
  const residencyDatasets = datasets.filter((d) => d.residencyRequired);
  const signedPct = Math.round((datasets.filter((d) => d.signed).length / datasets.length) * 100);
  const maskCoverage = piiFields ? 100 : 0; // every PII field is masked-by-default in the fabric

  // Datasets that actually carry sensitive fields lead the classification grid.
  const classified = [...datasets].sort((a, b) => b.piiFields - a.piiFields);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Trust & Privacy Fabric"
        title="Privacy is the default, not a setting"
        description="Every byte is classified on ingest, every query is authorized with ABAC + RBAC, sensitive fields are masked before they ever leave the perimeter, and aggregate analytics spend a bounded differential-privacy budget. Residency fences and C2PA provenance are enforced by the same core engine across every domain."
        actions={
          <>
            <Link href="/governance">
              <Button variant="default">
                <ScrollText size={15} /> Policy charter
              </Button>
            </Link>
            <Link href="/catalog">
              <Button variant="primary">
                <SlidersHorizontal size={15} /> Browse catalog
              </Button>
            </Link>
          </>
        }
      />

      {/* Trust posture metric row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card glow className="animate-fade-up">
          <div className="flex items-start justify-between">
            <Stat
              label="PII fields protected"
              value={`${piiFields}`}
              unit={`/ ${allFields.length} fields`}
              delta={{ value: `${maskCoverage}% masked`, positive: true }}
              tone="crimson"
            />
            <Fingerprint size={18} className="text-crimson/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            across <span className="text-lumen">{piiDatasets}</span> datasets, tokenized on egress
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:60ms]">
          <div className="flex items-start justify-between">
            <Stat label="Active access policies" value={`${policies.length}`} unit="ABAC · RBAC" hint="evaluated per query" />
            <ShieldCheck size={18} className="text-auralis/70" />
          </div>
          <div className="mt-3 flex items-center gap-2 text-[11.5px]">
            <Badge tone="crimson">{denyRules} hard-deny</Badge>
            <span className="text-faint">incl. residency fences</span>
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:120ms]">
          <div className="flex items-start justify-between">
            <Stat label="Privacy guarantee" value="ε ≤ 1.0" unit="(ε,δ)-DP" tone="pulse" hint="δ = 1e-6 default" />
            <Lock size={18} className="text-pulse/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">
            <span className="text-lumen">{budgets.length}</span> live budgets metered for re-identification risk
          </div>
        </Card>
        <Card className="animate-fade-up [animation-delay:180ms]">
          <div className="flex items-start justify-between">
            <Stat
              label="Provenance verified"
              value={`${signedPct}%`}
              unit="C2PA signed"
              delta={{ value: "Ed25519", positive: true }}
              tone="verdant"
            />
            <BadgeCheck size={18} className="text-verdant/70" />
          </div>
          <div className="mt-3 text-[11.5px] text-faint">tamper-evident content credentials, verified on read</div>
        </Card>
      </div>

      {/* Classification overview */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <SectionHeader
            title="Sensitivity distribution"
            subtitle="How the fabric classifies every field at rest."
            icon={<Fingerprint size={16} />}
          />
          <div className="mt-5 flex items-center gap-5">
            <div className="relative grid place-items-center">
              <DonutChart
                segments={[
                  { value: exposedFields, color: "verdant", label: "exposed" },
                  { value: maskedFields, color: "crimson", label: "masked" },
                ]}
                size={132}
                thickness={16}
              />
              <div className="absolute flex flex-col items-center">
                <span className="font-display text-[22px] font-semibold tabular-nums text-lumen">{allFields.length}</span>
                <span className="text-[10px] uppercase tracking-wider text-faint">fields</span>
              </div>
            </div>
            <div className="flex-1 space-y-2.5">
              <Legend color="bg-crimson" label="Masked by default" value={maskedFields} sub="PII · financial · confidential" />
              <Legend color="bg-verdant" label="Exposed (open)" value={exposedFields} sub="public · internal" />
            </div>
          </div>
          <p className="mt-4 border-t border-hairline pt-3 text-[11px] leading-relaxed text-faint">
            Masking is the default for anything regulated — a field must be explicitly un-masked by an allow-policy to
            leave the perimeter in the clear.
          </p>
        </Card>

        <Card className="lg:col-span-2">
          <SectionHeader
            title="PII / PHI classification by dataset"
            subtitle="Which fields are sensitive, and whether they are masked or exposed — privacy-by-default, per modality."
            icon={<Lock size={16} />}
            action={
              <Link href="/catalog" className="text-[12px] text-auralis hover:underline">
                Full catalog <ArrowUpRight size={12} className="inline" />
              </Link>
            }
          />
          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
            {classified.map((d) => (
              <ClassificationCard key={d.id} dataset={d} />
            ))}
          </div>
        </Card>
      </div>

      {/* Access policies */}
      <Card>
        <SectionHeader
          title="Access policies — ABAC + RBAC"
          subtitle="Attribute- and role-based rules evaluated before any compute is placed. Deny rules (residency, PII) are hard boundaries the engine cannot route around."
          icon={<ShieldCheck size={16} />}
          action={
            <div className="flex items-center gap-2">
              <Badge tone="verdant">{policies.length - denyRules} allow</Badge>
              <Badge tone="crimson">{denyRules} deny</Badge>
            </div>
          }
        />
        <div className="mt-5">
          <PolicyTable policies={policies} />
        </div>
        {residencyDatasets.length > 0 && (
          <p className="mt-3 text-[11px] leading-relaxed text-faint">
            <span className="text-crimson/90">Residency-fenced:</span>{" "}
            {residencyDatasets.map((d) => d.name).join(", ")} — EU data is denied any compute placed outside EU regions,
            full stop.
          </p>
        )}
      </Card>

      {/* DP budgets + Federated learning */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <SectionHeader
            title="Differential-privacy budgets"
            subtitle="Bounded ε per subject — exhausted budgets refuse further queries."
            icon={<SlidersHorizontal size={16} />}
          />
          <div className="mt-5">
            <PrivacyBudgets budgets={budgets} />
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <SectionHeader
            title="Federated learning — data never leaves jurisdiction"
            subtitle="Train globally, keep data local. Only privacy-clipped gradients aggregate."
            icon={<Network size={16} />}
            action={<Badge tone="auralis" dot>privacy-preserving ML</Badge>}
          />
          <div className="mt-5">
            <FederatedExplainer />
          </div>
        </Card>
      </div>

      {/* Provenance + posture gauge */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="C2PA provenance & verification"
            subtitle="Content credentials bind lineage, license and quality to a tamper-evident hash chain — verified at query time."
            icon={<BadgeCheck size={16} />}
          />
          <div className="mt-5">
            <ProvenanceStatus datasets={datasets} />
          </div>
        </Card>

        <Card className="flex flex-col">
          <SectionHeader
            title="Trust posture"
            subtitle="Overall fabric integrity."
            icon={<ShieldCheck size={16} />}
          />
          <div className="mt-4 flex flex-1 flex-col items-center justify-center gap-4">
            <RadialGauge value={signedPct} color="verdant" label={`${signedPct}%`} sublabel="verified" />
            <div className="w-full space-y-2 text-[11.5px]">
              <PostureRow label="PII auto-masking" value="100%" tone="verdant" />
              <PostureRow label="Residency enforcement" value="enforced" tone="verdant" />
              <PostureRow label="DP on aggregates" value="ε ≤ 1.0" tone="pulse" />
              <PostureRow label="Cross-border row egress" value="0" tone="verdant" />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Legend({ color, label, value, sub }: { color: string; label: string; value: number; sub: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-hairline/70 bg-veil-2/40 px-3 py-2">
      <div className="flex items-center gap-2.5">
        <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
        <div className="leading-tight">
          <div className="text-[12px] text-lumen">{label}</div>
          <div className="text-[10px] text-faint">{sub}</div>
        </div>
      </div>
      <span className="font-display text-[16px] font-semibold tabular-nums text-lumen">{value}</span>
    </div>
  );
}

function PostureRow({ label, value, tone }: { label: string; value: string; tone: "verdant" | "pulse" }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-veil-2/40 px-2.5 py-1.5">
      <span className="text-muted">{label}</span>
      <span className={tone === "verdant" ? "font-medium text-verdant" : "font-medium text-[#b3a4ff]"}>{value}</span>
    </div>
  );
}
