/**
 * Stateless signed session — an HMAC-SHA256 cookie, verifiable in both the Edge
 * middleware and Node route handlers via Web Crypto (no Node-only APIs).
 *
 * Cookie value = base64url(JSON claims) + "." + base64url(HMAC(payload, secret)).
 * This mirrors the control-plane's token scheme so the same identity model is
 * used by the UI and the API.
 */

export const SESSION_COOKIE = "aegoria_session";
const SECRET = process.env.AEGORIA_SESSION_SECRET ?? "aegoria-dev-secret-change-me";
const TTL_SECONDS = 8 * 60 * 60; // 8 hours

export interface SessionUser {
  subject: string;
  displayName: string;
  roles: string[];
  jurisdiction: string;
  isSuperAdmin: boolean;
}

export interface SessionClaims extends SessionUser {
  iat: number;
  exp: number;
}

const enc = new TextEncoder();
const dec = new TextDecoder();

function b64urlFromBytes(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function bytesFromB64url(str: string): Uint8Array {
  const norm = str.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(norm + "=".repeat((4 - (norm.length % 4)) % 4));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
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
  return b64urlFromBytes(new Uint8Array(sig));
}

/** Create a signed cookie value for a user. */
export async function signSession(user: SessionUser): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const claims: SessionClaims = { ...user, iat: now, exp: now + TTL_SECONDS };
  const payload = b64urlFromBytes(enc.encode(JSON.stringify(claims)));
  const sig = await hmac(payload);
  return `${payload}.${sig}`;
}

/** Verify a cookie value; returns claims or null (bad signature / expired). */
export async function verifySession(token: string | undefined | null): Promise<SessionClaims | null> {
  if (!token) return null;
  const dot = token.indexOf(".");
  if (dot < 0) return null;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const expected = await hmac(payload);
  if (sig !== expected) return null;
  try {
    const claims = JSON.parse(dec.decode(bytesFromB64url(payload))) as SessionClaims;
    if (!claims.exp || claims.exp < Math.floor(Date.now() / 1000)) return null;
    return claims;
  } catch {
    return null;
  }
}

export const SESSION_MAX_AGE = TTL_SECONDS;
