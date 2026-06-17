"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

const COLORS: Record<string, string> = {
  auralis: "#16E0C4",
  pulse: "#7B61FF",
  verdant: "#57E08A",
  ion: "#3FA9FF",
  solar: "#FFB454",
  crimson: "#FF5C72",
};

function buildPath(values: number[], w: number, h: number, pad = 2) {
  if (values.length === 0) return { line: "", area: "" };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = (w - pad * 2) / (values.length - 1 || 1);
  const pts = values.map((v, i) => {
    const x = pad + i * step;
    const y = pad + (h - pad * 2) * (1 - (v - min) / range);
    return [x, y] as const;
  });
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ");
  const area = `${line} L${pts[pts.length - 1][0].toFixed(2)},${h} L${pts[0][0].toFixed(2)},${h} Z`;
  return { line, area };
}

/* -------------------------------------------------------------- Sparkline */
export function Sparkline({
  data,
  color = "auralis",
  width = 120,
  height = 36,
  className,
}: {
  data: number[];
  color?: keyof typeof COLORS;
  width?: number;
  height?: number;
  className?: string;
}) {
  const id = React.useId();
  const { line, area } = buildPath(data, width, height, 2);
  const c = COLORS[color];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className={cn("overflow-visible", className)} preserveAspectRatio="none">
      <defs>
        <linearGradient id={`sl-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={c} stopOpacity="0.35" />
          <stop offset="1" stopColor={c} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#sl-${id})`} />
      <path d={line} fill="none" stroke={c} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* -------------------------------------------------------------- AreaChart */
export function AreaChart({
  data,
  color = "auralis",
  height = 160,
  labels,
  className,
}: {
  data: number[];
  color?: keyof typeof COLORS;
  height?: number;
  labels?: string[];
  className?: string;
}) {
  const id = React.useId();
  const W = 600;
  const { line, area } = buildPath(data, W, height, 6);
  const c = COLORS[color];
  return (
    <div className={cn("w-full", className)}>
      <svg viewBox={`0 0 ${W} ${height}`} width="100%" height={height} preserveAspectRatio="none">
        <defs>
          <linearGradient id={`ac-${id}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={c} stopOpacity="0.30" />
            <stop offset="1" stopColor={c} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((g) => (
          <line key={g} x1="0" x2={W} y1={height * g} y2={height * g} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
        ))}
        <path d={area} fill={`url(#ac-${id})`} />
        <path d={line} fill="none" stroke={c} strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {labels && (
        <div className="mt-2 flex justify-between text-[10.5px] text-faint">
          {labels.map((l, i) => (
            <span key={i}>{l}</span>
          ))}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------- BarSeries */
export function BarSeries({
  data,
  color = "auralis",
  height = 140,
  className,
}: {
  data: { label: string; value: number; color?: keyof typeof COLORS }[];
  color?: keyof typeof COLORS;
  height?: number;
  className?: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-end gap-2" style={{ height }}>
        {data.map((d, i) => (
          <div key={i} className="group flex flex-1 flex-col items-center justify-end gap-2">
            <div
              className="w-full rounded-t-sm transition-all duration-500 group-hover:brightness-125"
              style={{
                height: `${(d.value / max) * 100}%`,
                background: `linear-gradient(to top, ${COLORS[d.color ?? color]}22, ${COLORS[d.color ?? color]})`,
              }}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        {data.map((d, i) => (
          <span key={i} className="flex-1 truncate text-center text-[10px] text-faint">
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- RadialGauge */
export function RadialGauge({
  value,
  max = 100,
  size = 132,
  color = "auralis",
  label,
  sublabel,
}: {
  value: number;
  max?: number;
  size?: number;
  color?: keyof typeof COLORS;
  label?: string;
  sublabel?: string;
}) {
  const id = React.useId();
  const stroke = 10;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(1, Math.max(0, value / max));
  const c = COLORS[color];
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={`rg-${id}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={c} />
            <stop offset="1" stopColor="#7B61FF" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1A2236" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`url(#rg-${id})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - pct)}
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-[24px] font-semibold tabular-nums text-lumen">{label ?? Math.round(pct * 100)}</span>
        {sublabel && <span className="text-[10.5px] uppercase tracking-wider text-faint">{sublabel}</span>}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- DonutChart */
export function DonutChart({
  segments,
  size = 132,
  thickness = 16,
}: {
  segments: { value: number; color: keyof typeof COLORS; label: string }[];
  size?: number;
  thickness?: number;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = (size - thickness) / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1A2236" strokeWidth={thickness} />
      {segments.map((s, i) => {
        const len = (s.value / total) * circ;
        const el = (
          <circle
            key={i}
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={COLORS[s.color]}
            strokeWidth={thickness}
            strokeDasharray={`${len} ${circ - len}`}
            strokeDashoffset={-offset}
            className="transition-all duration-700"
          />
        );
        offset += len;
        return el;
      })}
    </svg>
  );
}
