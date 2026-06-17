import {
  LayoutDashboard,
  Database,
  GitBranch,
  ShieldCheck,
  Leaf,
  Boxes,
  Share2,
  Workflow,
  TerminalSquare,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  group: "Observe" | "Trust" | "Operate" | "Govern";
  badge?: string;
}

export const NAV: NavItem[] = [
  { href: "/", label: "Command Center", icon: LayoutDashboard, group: "Observe" },
  { href: "/catalog", label: "Data Catalog", icon: Database, group: "Observe" },
  { href: "/lineage", label: "Lineage & Provenance", icon: GitBranch, group: "Observe" },
  { href: "/graph", label: "Knowledge Graph", icon: Share2, group: "Observe" },
  { href: "/trust", label: "Trust & Privacy", icon: ShieldCheck, group: "Trust" },
  { href: "/carbon", label: "Carbon & Compute", icon: Leaf, group: "Trust" },
  { href: "/pipelines", label: "Pipelines", icon: Workflow, group: "Operate" },
  { href: "/query", label: "Query Studio", icon: TerminalSquare, group: "Operate" },
  { href: "/packs", label: "Domain Packs", icon: Boxes, group: "Operate" },
  { href: "/governance", label: "Data Commons", icon: Users, group: "Govern" },
];

export const NAV_GROUPS = ["Observe", "Trust", "Operate", "Govern"] as const;
