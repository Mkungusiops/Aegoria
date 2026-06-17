import { cookies } from "next/headers";
import { Lock } from "lucide-react";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";
import { canOnboard, ONBOARD_ROLES } from "@/lib/onboard";
import { Card, PageHeader } from "@/components/ui/primitives";
import { OnboardStudio } from "@/components/onboard/onboard-studio";

export default async function OnboardPage() {
  const claims = await verifySession((await cookies()).get(SESSION_COOKIE)?.value);
  const allowed = canOnboard(claims?.roles);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Operate"
        title="Onboard data"
        description="Bring your own database or files into the platform. Aegoria assesses quality and PII, cleans the data, and ships it three ways — cleaned exports for internal use, a governed dataset in the catalog, and a PII-masked corpus ready for AI ingestion."
      />
      {allowed ? (
        <OnboardStudio />
      ) : (
        <Card className="flex items-start gap-4">
          <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-md border border-hairline bg-veil-2 text-solar">
            <Lock size={18} />
          </span>
          <div>
            <h2 className="font-display text-[15px] font-semibold text-lumen">Restricted to data stewards</h2>
            <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-muted">
              Onboarding reads source data, lands governed datasets and produces PII-bearing artifacts, so it is limited to
              privileged roles ({ONBOARD_ROLES.join(", ")}). Your account does not currently hold one of these roles — ask
              a platform administrator for access.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
