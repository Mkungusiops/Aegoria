/**
 * Server-side bridge to the control-plane API.
 *
 * The console session and the control-plane token share the same HMAC-SHA256
 * scheme and `AEGORIA_SESSION_SECRET`, so we can mint a *control-plane* bearer
 * for the already-authenticated console user (correct `sub`, roles, clearance)
 * and call privileged endpoints on their behalf. This module is server-only.
 */
import "server-only";

import type { SessionUser } from "@/lib/auth/session";

const SECRET = process.env.AEGORIA_SESSION_SECRET ?? "aegoria-dev-secret-change-me";
const TOKEN_TTL_S = 60 * 10; // short-lived; minted per request

// Inside docker the console reaches the API by service name; override for local dev.
export const CONTROL_PLANE_URL =
  process.env.AEGORIA_API_URL || process.env.CONTROL_PLANE_URL || "http://api:8000";

const enc = new TextEncoder();

function b64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function hmac(payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  return b64url(new Uint8Array(sig));
}

/** Mint a control-plane bearer token (claim shape the control-plane expects). */
export async function mintControlPlaneToken(user: SessionUser): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const claims = {
    sub: user.subject,
    name: user.displayName,
    roles: user.roles,
    jurisdiction: user.jurisdiction,
    clearance: user.isSuperAdmin ? "restricted" : "confidential",
    attributes: { org: "aegoria", purpose: "onboarding" },
    iat: now,
    exp: now + TOKEN_TTL_S,
  };
  const payload = b64url(enc.encode(JSON.stringify(claims)));
  const sig = await hmac(payload);
  return `${payload}.${sig}`;
}
