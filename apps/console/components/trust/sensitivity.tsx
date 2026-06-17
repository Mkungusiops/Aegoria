import type { Sensitivity } from "@/lib/types";
import type { Tone } from "@/components/ui/primitives";

/**
 * Shared sensitivity vocabulary for the Trust fabric. Maps the engine's
 * `Sensitivity` enum onto a console tone + whether the platform masks the
 * field by default. Privacy-by-default means: anything that is not `public`
 * or `internal` is masked unless an explicit allow-policy un-masks it.
 */
export const SENSITIVITY_META: Record<
  Sensitivity,
  { label: string; tone: Tone; maskedByDefault: boolean; regulated: boolean }
> = {
  public: { label: "Public", tone: "verdant", maskedByDefault: false, regulated: false },
  internal: { label: "Internal", tone: "ion", maskedByDefault: false, regulated: false },
  confidential: { label: "Confidential", tone: "solar", maskedByDefault: true, regulated: false },
  financial: { label: "Financial", tone: "solar", maskedByDefault: true, regulated: true },
  restricted: { label: "Restricted", tone: "crimson", maskedByDefault: true, regulated: true },
  pii: { label: "PII", tone: "crimson", maskedByDefault: true, regulated: true },
  phi: { label: "PHI", tone: "pulse", maskedByDefault: true, regulated: true },
};

export const isSensitive = (s: Sensitivity) => SENSITIVITY_META[s].maskedByDefault;
