/**
 * Console user store (server-only). Mirrors the control-plane's accounts so the
 * UI and API share one identity model. Passwords are read from env with demo
 * defaults; in production this is replaced by an OIDC/OAuth2 sign-in.
 *
 * Roles map onto the engine's RBAC: `superadmin` is the apex break-glass role;
 * `analyst` is EU-resident and subject to residency + differential privacy.
 */

import type { SessionUser } from "./session";

interface UserRecord extends SessionUser {
  password: string;
}

function pw(envKey: string, fallback: string): string {
  return process.env[envKey] ?? fallback;
}

const USERS: Record<string, UserRecord> = {
  admin: {
    subject: "admin",
    displayName: "Root Administrator",
    roles: ["superadmin", "admin", "owner", "steward"],
    jurisdiction: "GLOBAL",
    isSuperAdmin: true,
    password: pw("AEGORIA_ADMIN_PASSWORD", "Aegoria-Superadmin-2026!"),
  },
  steward: {
    subject: "steward",
    displayName: "Platform Steward",
    roles: ["steward", "admin"],
    jurisdiction: "GLOBAL",
    isSuperAdmin: false,
    password: pw("AEGORIA_STEWARD_PASSWORD", "steward"),
  },
  analyst: {
    subject: "analyst",
    displayName: "Credit Risk Analyst",
    roles: ["analyst"],
    jurisdiction: "EU",
    isSuperAdmin: false,
    password: pw("AEGORIA_ANALYST_PASSWORD", "analyst"),
  },
  viewer: {
    subject: "viewer",
    displayName: "Read-only Viewer",
    roles: ["public"],
    jurisdiction: "GLOBAL",
    isSuperAdmin: false,
    password: pw("AEGORIA_VIEWER_PASSWORD", "viewer"),
  },
};

function timingSafeEqual(a: string, b: string): boolean {
  // Constant-time-ish comparison to avoid leaking password length/prefix.
  const max = Math.max(a.length, b.length);
  let diff = a.length ^ b.length;
  for (let i = 0; i < max; i++) diff |= a.charCodeAt(i % a.length || 0) ^ b.charCodeAt(i % b.length || 0);
  return diff === 0;
}

/** Validate credentials; returns the sanitized session user or null. */
export function authenticate(username: string, password: string): SessionUser | null {
  const rec = USERS[username?.trim()];
  if (!rec) {
    timingSafeEqual(password ?? "", "decoy-value-to-equalize-timing");
    return null;
  }
  if (!timingSafeEqual(password ?? "", rec.password)) return null;
  const { password: _pw, ...user } = rec;
  void _pw;
  return user;
}

/** Public, password-free directory used to render demo sign-in hints. */
export const DEMO_ACCOUNTS = Object.values(USERS).map((u) => ({
  subject: u.subject,
  displayName: u.displayName,
  roles: u.roles,
  jurisdiction: u.jurisdiction,
  isSuperAdmin: u.isSuperAdmin,
}));
