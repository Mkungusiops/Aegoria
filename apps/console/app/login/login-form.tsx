"use client";

import * as React from "react";
import { LogIn, ShieldCheck, Loader2, KeyRound } from "lucide-react";
import { cn } from "@/lib/cn";
import { LogoMark } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";

interface DemoAccount {
  username: string;
  password: string;
  label: string;
  role: string;
  tone: "auralis" | "pulse" | "verdant" | "neutral";
  super?: boolean;
}

// The provided sign-in credentials (defaults; override via AEGORIA_*_PASSWORD).
const DEMO: DemoAccount[] = [
  { username: "admin", password: "Aegoria-Superadmin-2026!", label: "Root Administrator", role: "Super Admin", tone: "auralis", super: true },
  { username: "steward", password: "steward", label: "Platform Steward", role: "Steward", tone: "pulse" },
  { username: "analyst", password: "analyst", label: "Credit Risk Analyst", role: "Analyst · EU", tone: "verdant" },
  { username: "viewer", password: "viewer", label: "Read-only Viewer", role: "Viewer", tone: "neutral" },
];

const TONES: Record<string, string> = {
  auralis: "border-auralis/30 bg-auralis/10 text-auralis",
  pulse: "border-pulse/30 bg-pulse/10 text-[#b3a4ff]",
  verdant: "border-verdant/30 bg-verdant/10 text-verdant",
  neutral: "border-hairline bg-veil-2 text-muted",
};

export function LoginForm({ from }: { from: string }) {
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || "Sign-in failed");
        setLoading(false);
        return;
      }
      // Full navigation so the new session cookie is applied by middleware.
      window.location.assign(from || "/");
    } catch {
      setError("Network error — is the console reachable?");
      setLoading(false);
    }
  }

  function fill(acc: DemoAccount) {
    setUsername(acc.username);
    setPassword(acc.password);
    setError("");
  }

  return (
    <div className="relative grid min-h-screen lg:grid-cols-2">
      <div className="absolute right-5 top-5 z-10">
        <ThemeToggle />
      </div>

      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-hairline bg-veil-1 p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0 grid-bg opacity-60" />
        <div
          className="pointer-events-none absolute -left-24 top-1/3 h-96 w-96 rounded-full opacity-30 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(22,224,196,0.5), transparent 60%)" }}
        />
        <div className="relative flex items-center gap-3">
          <LogoMark size={40} animate />
          <span className="font-display text-[22px] font-semibold tracking-[0.14em] text-lumen">AEGORIA</span>
        </div>
        <div className="relative max-w-md">
          <h1 className="font-display text-[34px] font-semibold leading-tight tracking-tight text-lumen text-balance">
            One planet. Every domain. <span className="text-auralis-gradient">Data you can trust.</span>
          </h1>
          <p className="mt-4 text-[14px] leading-relaxed text-muted">
            The planet-scale, market-agnostic lakehouse. Sign in to govern data across every
            sector — with privacy, provenance and carbon-aware compute by default.
          </p>
          <div className="mt-7 flex flex-wrap gap-2">
            {["Schema-on-read lakehouse", "ABAC / RBAC", "Differential privacy", "Carbon-aware", "C2PA provenance"].map((t) => (
              <span key={t} className="rounded-full border border-hairline bg-veil-2/60 px-3 py-1 text-[11.5px] text-muted">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="relative text-[11.5px] text-faint">Open-source core · privacy &amp; sovereignty by default</div>
      </div>

      {/* Sign-in panel */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <LogoMark size={34} />
            <span className="font-display text-[18px] font-semibold tracking-[0.14em] text-lumen">AEGORIA</span>
          </div>

          <h2 className="font-display text-[22px] font-semibold tracking-tight text-lumen">Sign in</h2>
          <p className="mt-1 text-[13px] text-muted">Authenticate to enter the control surface.</p>

          <form onSubmit={submit} className="mt-6 space-y-3.5">
            <label className="block">
              <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-wider text-faint">Username</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                className="h-11 w-full rounded-md border border-hairline bg-veil-1 px-3.5 text-[14px] text-lumen placeholder:text-faint focus:border-auralis/50 focus:outline-none focus:ring-2 focus:ring-auralis/20"
                placeholder="admin"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-wider text-faint">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="h-11 w-full rounded-md border border-hairline bg-veil-1 px-3.5 text-[14px] text-lumen placeholder:text-faint focus:border-auralis/50 focus:outline-none focus:ring-2 focus:ring-auralis/20"
                placeholder="••••••••••"
              />
            </label>

            {error && (
              <div className="rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12.5px] text-crimson">{error}</div>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-auralis text-[14px] font-semibold text-ink transition-all hover:brightness-110 disabled:opacity-50"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-7">
            <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-wider text-faint">
              <KeyRound size={12} /> Demo credentials — click to fill
            </div>
            <div className="grid gap-2">
              {DEMO.map((acc) => (
                <button
                  key={acc.username}
                  onClick={() => fill(acc)}
                  type="button"
                  className="group flex items-center justify-between rounded-md border border-hairline bg-veil-1/60 px-3 py-2 text-left transition-colors hover:border-auralis/30 hover:bg-veil-2"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 text-[12.5px] font-medium text-lumen">
                      {acc.super && <ShieldCheck size={12} className="text-auralis" />}
                      {acc.label}
                    </div>
                    <div className="mt-0.5 font-mono text-[11px] text-faint">
                      {acc.username} · {acc.password}
                    </div>
                  </div>
                  <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[10.5px] font-medium", TONES[acc.tone])}>
                    {acc.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
