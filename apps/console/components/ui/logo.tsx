import { cn } from "@/lib/cn";

/**
 * The Aegoria mark: an aperture of three converging arcs around a luminous core —
 * many domains resolving into one trusted lens. Animated optionally.
 */
export function LogoMark({ size = 32, className, animate = false }: { size?: number; className?: string; animate?: boolean }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Aegoria"
      className={cn(className)}
    >
      <defs>
        <linearGradient id="ag-auralis" x1="14" y1="20" x2="82" y2="78" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#16E0C4" />
          <stop offset="0.55" stopColor="#21D6C9" />
          <stop offset="1" stopColor="#7B61FF" />
        </linearGradient>
        <radialGradient id="ag-core" cx="0.5" cy="0.45" r="0.6">
          <stop offset="0" stopColor="#EAFFFB" />
          <stop offset="0.4" stopColor="#16E0C4" />
          <stop offset="1" stopColor="#0BA98F" />
        </radialGradient>
      </defs>
      <circle cx="48" cy="48" r="40" stroke="#16E0C4" strokeOpacity="0.14" strokeWidth="1.5" />
      <g stroke="url(#ag-auralis)" strokeWidth="7" strokeLinecap="round" fill="none" className={animate ? "origin-center animate-[spin_18s_linear_infinite]" : ""}>
        <path d="M 22.02 33 A 30 30 0 0 1 78 48" transform="rotate(0 48 48)" />
        <path d="M 22.02 33 A 30 30 0 0 1 78 48" transform="rotate(120 48 48)" />
        <path d="M 22.02 33 A 30 30 0 0 1 78 48" transform="rotate(240 48 48)" />
      </g>
      <g fill="#16E0C4">
        <circle cx="78" cy="48" r="3.4" transform="rotate(0 48 48)" />
        <circle cx="78" cy="48" r="3.4" transform="rotate(120 48 48)" />
        <circle cx="78" cy="48" r="3.4" transform="rotate(240 48 48)" />
      </g>
      <circle cx="48" cy="48" r="12" fill="#16E0C4" fillOpacity="0.10" />
      <circle cx="48" cy="48" r="7.5" fill="url(#ag-core)" />
    </svg>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <LogoMark size={28} />
      <span className="font-display text-[19px] font-semibold tracking-[0.14em] text-lumen">AEGORIA</span>
    </div>
  );
}
