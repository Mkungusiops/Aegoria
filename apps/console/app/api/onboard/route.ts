import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/session";
import { CONTROL_PLANE_URL, mintControlPlaneToken } from "@/lib/control-plane";
import { canOnboard } from "@/lib/onboard";

export const runtime = "nodejs";

/**
 * Onboarding bridge. Authenticates the console session, enforces the privileged
 * role gate, mints a control-plane bearer for the user, and forwards either:
 *  - a raw file upload (octet-stream body + query params) -> /onboard/upload, or
 *  - a server source (JSON {source,...})                  -> /clean.
 */
export async function POST(req: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const claims = await verifySession(token);
  if (!claims) {
    return NextResponse.json({ detail: "authentication required" }, { status: 401 });
  }
  if (!canOnboard(claims.roles)) {
    return NextResponse.json(
      { detail: "onboarding requires a steward/admin/superadmin role" },
      { status: 403 },
    );
  }

  const bearer = await mintControlPlaneToken({
    subject: claims.subject,
    displayName: claims.displayName,
    roles: claims.roles,
    jurisdiction: claims.jurisdiction,
    isSuperAdmin: claims.isSuperAdmin,
  });

  const ct = req.headers.get("content-type") || "";
  try {
    let cpRes: Response;
    if (ct.includes("application/json")) {
      const body = await req.json();
      cpRes = await fetch(`${CONTROL_PLANE_URL}/clean`, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${bearer}` },
        body: JSON.stringify({
          source: body.source,
          dataset: body.dataset ?? null,
          connector: body.connector ?? null,
          land: body.land ?? true,
          ai: body.ai ?? true,
        }),
      });
    } else {
      // Upload: bytes are the body; filename/dataset/land/ai ride the query string.
      const qs = new URL(req.url).searchParams.toString();
      const bytes = await req.arrayBuffer();
      cpRes = await fetch(`${CONTROL_PLANE_URL}/onboard/upload?${qs}`, {
        method: "POST",
        headers: { "content-type": "application/octet-stream", authorization: `Bearer ${bearer}` },
        body: bytes,
      });
    }
    const text = await cpRes.text();
    return new NextResponse(text, {
      status: cpRes.status,
      headers: { "content-type": "application/json" },
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ detail: `control-plane unreachable: ${msg}` }, { status: 502 });
  }
}
