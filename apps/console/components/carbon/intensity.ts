import type { Tone } from "@/components/ui/primitives";

/**
 * Shared carbon-intensity scale used across the Carbon & Compute page. Maps a
 * grid carbon intensity (gCO₂/kWh) onto a tone + hex so the greenest region is
 * always read as verdant and the dirtiest as crimson, consistently everywhere.
 */
export const HEX: Record<Tone, string> = {
  auralis: "#16E0C4",
  pulse: "#7B61FF",
  verdant: "#57E08A",
  ion: "#3FA9FF",
  solar: "#FFB454",
  crimson: "#FF5C72",
  neutral: "#6B7894",
};

export function intensityTone(gco2: number): Tone {
  if (gco2 < 60) return "verdant";
  if (gco2 < 200) return "ion";
  if (gco2 < 400) return "solar";
  return "crimson";
}

export function intensityLabel(gco2: number): string {
  if (gco2 < 60) return "very low";
  if (gco2 < 200) return "low";
  if (gco2 < 400) return "moderate";
  return "high";
}
