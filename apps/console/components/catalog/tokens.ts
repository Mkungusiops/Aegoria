import type { Tone } from "@/components/ui/primitives";
import type { Modality, Sensitivity } from "@/lib/types";

/**
 * Shared presentation tokens for catalog surfaces. Mapping the engine's
 * sensitivity / modality vocabulary to design-system tones in one place keeps
 * the catalog browser, dataset detail and schema table visually consistent.
 */

export const SENSITIVITY_TONE: Record<Sensitivity, Tone> = {
  public: "verdant",
  internal: "ion",
  confidential: "solar",
  pii: "crimson",
  phi: "crimson",
  financial: "pulse",
  restricted: "crimson",
};

export const SENSITIVITY_LABEL: Record<Sensitivity, string> = {
  public: "Public",
  internal: "Internal",
  confidential: "Confidential",
  pii: "PII",
  phi: "PHI",
  financial: "Financial",
  restricted: "Restricted",
};

export const MODALITY_LABEL: Record<Modality, string> = {
  structured: "Structured",
  time_series: "Time series",
  geospatial: "Geospatial",
  imagery: "Imagery",
  sensor_stream: "Sensor stream",
  event_stream: "Event stream",
  text: "Text",
};

export const MODALITY_TONE: Record<Modality, Tone> = {
  structured: "auralis",
  time_series: "ion",
  geospatial: "verdant",
  imagery: "pulse",
  sensor_stream: "solar",
  event_stream: "solar",
  text: "ion",
};

export const DOMAIN_TONE: Record<string, Tone> = {
  "climate-emissions": "verdant",
  "consumer-credit": "auralis",
  "public-health": "ion",
  "freight-logistics": "solar",
};

export function domainTone(domain: string): Tone {
  return DOMAIN_TONE[domain] ?? "neutral";
}

/** Quality score (0..1) -> tone for badges / bars. */
export function qualityTone(score: number): Tone {
  if (score >= 0.95) return "verdant";
  if (score >= 0.85) return "auralis";
  if (score >= 0.7) return "solar";
  return "crimson";
}

/** Hex value for a tone — used for inline SVG/dot styling where classes can't reach. */
export const TONE_HEX: Record<Tone, string> = {
  auralis: "#16E0C4",
  pulse: "#7B61FF",
  verdant: "#57E08A",
  ion: "#3FA9FF",
  solar: "#FFB454",
  crimson: "#FF5C72",
  neutral: "#5C6B8A",
};

/**
 * Static text-colour classes keyed by tone. Declaring the full class strings
 * (never interpolated) keeps Tailwind's JIT scanner able to find them.
 */
export const TONE_TEXT: Record<Tone, string> = {
  auralis: "text-auralis",
  pulse: "text-pulse",
  verdant: "text-verdant",
  ion: "text-ion",
  solar: "text-solar",
  crimson: "text-crimson",
  neutral: "text-muted",
};
