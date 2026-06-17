import * as React from "react";
import { cn } from "@/lib/cn";

/* ---------------------------------------------------------------- Surfaces */
export function Card({
  className,
  glow = false,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  return (
    <div
      className={cn(
        "surface relative overflow-hidden p-5 transition-shadow duration-300",
        glow && "shadow-glow",
        className,
      )}
      {...props}
    />
  );
}

export function Panel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("surface-2 shadow-panel-sm", className)} {...props} />;
}

/* ------------------------------------------------------------ Section head */
export function SectionHeader({
  title,
  subtitle,
  icon,
  action,
  className,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div className="flex items-start gap-3">
        {icon && (
          <span className="mt-0.5 grid h-9 w-9 place-items-center rounded-md border border-hairline bg-veil-2 text-auralis">
            {icon}
          </span>
        )}
        <div>
          <h2 className="font-display text-[15px] font-semibold tracking-tight text-lumen">{title}</h2>
          {subtitle && <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

/* -------------------------------------------------------------------- Badge */
const toneMap = {
  auralis: "border-auralis/30 bg-auralis/10 text-auralis",
  pulse: "border-pulse/30 bg-pulse/10 text-[#b3a4ff]",
  verdant: "border-verdant/30 bg-verdant/10 text-verdant",
  ion: "border-ion/30 bg-ion/10 text-ion",
  solar: "border-solar/30 bg-solar/10 text-solar",
  crimson: "border-crimson/30 bg-crimson/10 text-crimson",
  neutral: "border-hairline bg-veil-2 text-muted",
} as const;
export type Tone = keyof typeof toneMap;

export function Badge({
  tone = "neutral",
  className,
  dot = false,
  children,
}: {
  tone?: Tone;
  className?: string;
  dot?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
        toneMap[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ Button */
export function Button({
  variant = "default",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "ghost" }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-[13px] font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-auralis/40 disabled:opacity-50";
  const variants = {
    default: "border border-hairline bg-veil-2 text-lumen hover:border-auralis/40 hover:bg-veil-3",
    primary: "bg-auralis text-ink font-semibold hover:brightness-110 shadow-[0_8px_24px_-10px_rgba(22,224,196,0.7)]",
    ghost: "text-muted hover:bg-veil-2 hover:text-lumen",
  };
  return <button className={cn(base, variants[variant], className)} {...props} />;
}

/* -------------------------------------------------------------------- Stat */
export function Stat({
  label,
  value,
  unit,
  delta,
  tone = "auralis",
  hint,
  className,
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  delta?: { value: string; positive?: boolean };
  tone?: Tone;
  hint?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-[11.5px] font-medium uppercase tracking-wider text-faint">{label}</span>
      <div className="flex items-baseline gap-1.5">
        <span className="font-display text-[26px] font-semibold leading-none tracking-tight text-lumen tabular-nums">
          {value}
        </span>
        {unit && <span className="text-[12px] text-muted">{unit}</span>}
      </div>
      <div className="flex items-center gap-2">
        {delta && (
          <span
            className={cn(
              "text-[11.5px] font-medium tabular-nums",
              delta.positive === false ? "text-crimson" : "text-verdant",
            )}
          >
            {delta.value}
          </span>
        )}
        {hint && <span className="text-[11.5px] text-faint">{hint}</span>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- ProgressBar */
export function ProgressBar({
  value,
  tone = "auralis",
  className,
}: {
  value: number; // 0..100
  tone?: Tone;
  className?: string;
}) {
  const fill = {
    auralis: "bg-auralis",
    pulse: "bg-pulse",
    verdant: "bg-verdant",
    ion: "bg-ion",
    solar: "bg-solar",
    crimson: "bg-crimson",
    neutral: "bg-muted",
  }[tone];
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-veil-3", className)}>
      <div className={cn("h-full rounded-full transition-all duration-700", fill)} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

/* ----------------------------------------------------------------- KeyValue */
export function KeyValue({ items, className }: { items: { k: string; v: React.ReactNode }[]; className?: string }) {
  return (
    <dl className={cn("grid grid-cols-2 gap-x-6 gap-y-3", className)}>
      {items.map((it) => (
        <div key={it.k} className="flex flex-col gap-0.5">
          <dt className="text-[11px] uppercase tracking-wider text-faint">{it.k}</dt>
          <dd className="text-[13px] text-lumen">{it.v}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ------------------------------------------------------------------ Divider */
export function Divider({ className }: { className?: string }) {
  return <div className={cn("hairline-x h-px w-full", className)} />;
}

/* ----------------------------------------------------------------- PageHead */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-hairline pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="animate-fade-up">
        {eyebrow && <div className="mb-1.5 text-[11.5px] font-medium uppercase tracking-[0.18em] text-auralis">{eyebrow}</div>}
        <h1 className="font-display text-[28px] font-semibold leading-tight tracking-tight text-lumen text-balance">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-[13.5px] leading-relaxed text-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
