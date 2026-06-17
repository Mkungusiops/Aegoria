/**
 * Onboarding access policy — shared by the nav (to show/hide the menu item), the
 * page (server-side gate) and the API bridge (enforced gate). Mirrors the
 * control-plane's `_ONBOARDING_ROLES`: onboarding is a privileged write/ingest
 * action reserved for data stewards and admins.
 */
export const ONBOARD_ROLES = ["superadmin", "root", "admin", "owner", "steward"];

export function canOnboard(roles: string[] | undefined | null): boolean {
  if (!roles) return false;
  return roles.some((r) => ONBOARD_ROLES.includes(r));
}
