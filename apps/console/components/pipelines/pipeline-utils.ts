import type { Modality } from "@/lib/types";
import type { Tone } from "@/components/ui/primitives";

/** Maps a pipeline status to a Badge tone and human label. */
export const STATUS_META: Record<
  "healthy" | "running" | "degraded" | "failed",
  { tone: Tone; label: string }
> = {
  healthy: { tone: "verdant", label: "healthy" },
  running: { tone: "auralis", label: "streaming" },
  degraded: { tone: "solar", label: "degraded" },
  failed: { tone: "crimson", label: "failed" },
};

/** Per-modality presentation: short label + accent colour used across the page. */
export const MODALITY_META: Record<Modality, { label: string; tone: Tone }> = {
  structured: { label: "Structured", tone: "auralis" },
  time_series: { label: "Time-series", tone: "pulse" },
  geospatial: { label: "Geospatial", tone: "verdant" },
  imagery: { label: "Imagery", tone: "ion" },
  sensor_stream: { label: "Sensor stream", tone: "verdant" },
  event_stream: { label: "Event stream", tone: "solar" },
  text: { label: "Text", tone: "pulse" },
};

/** Static text-colour utility classes per tone (Tailwind-safe, no interpolation). */
export const TONE_TEXT: Record<Tone, string> = {
  auralis: "text-auralis",
  pulse: "text-pulse",
  verdant: "text-verdant",
  ion: "text-ion",
  solar: "text-solar",
  crimson: "text-crimson",
  neutral: "text-muted",
};

/** Renders a freshness window (seconds since last record) as a compact string. */
export function fmtFreshness(sec: number): string {
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  if (sec < 86400) return `${(sec / 3600).toFixed(1)}h`;
  return `${(sec / 86400).toFixed(1)}d`;
}

/**
 * Freshness SLO check. Streaming feeds expect sub-minute lag; batch feeds are
 * judged against a generous window. Returns whether the feed is within SLO and
 * the target it is measured against.
 */
export function freshnessSlo(
  schedule: string,
  freshnessSec: number,
): { withinSlo: boolean; targetSec: number; targetLabel: string } {
  const streaming = schedule === "streaming";
  const targetSec = streaming ? 30 : 4 * 3600;
  return {
    withinSlo: freshnessSec <= targetSec,
    targetSec,
    targetLabel: streaming ? "30s" : "4h",
  };
}

/** Turns a cron expression into a friendly cadence description. */
export function fmtSchedule(schedule: string): string {
  if (schedule === "streaming") return "Continuous stream";
  const map: Record<string, string> = {
    "*/15 * * * *": "Every 15 minutes",
    "0 2 * * *": "Daily · 02:00",
    "0 4 * * *": "Daily · 04:00",
    "0 * * * *": "Hourly",
    "0 0 * * *": "Daily · midnight",
  };
  return map[schedule] ?? `cron · ${schedule}`;
}

/** Relative "x ago" from an ISO timestamp, anchored to now. */
export function fmtAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - then);
  const sec = Math.round(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.round(hr / 24)}d ago`;
}
