import {
  BookText,
  FolderOpen,
  Gauge,
  ScanLine,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Grouping keeps the operational path (capture -> review) visually separate
   *  from the reference material (ruleset, limitations). */
  group: "work" | "reference";
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/scan",
    label: "New scan",
    icon: ScanLine,
    group: "work",
    description: "Capture or upload a package image",
  },
  {
    href: "/cases",
    label: "Cases",
    icon: FolderOpen,
    group: "work",
    description: "Inspector review queue",
  },
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: Gauge,
    group: "work",
    description: "Scan and case counters",
  },
  {
    href: "/rules",
    label: "Ruleset",
    icon: BookText,
    group: "reference",
    description: "The 29 rules as data",
  },
  {
    href: "/limitations",
    label: "Limitations",
    icon: TriangleAlert,
    group: "reference",
    description: "Known gaps, stated explicitly",
  },
];

export const NAV_GROUP_LABELS: Record<NavItem["group"], string> = {
  work: "Inspection",
  reference: "Reference",
};

/** Longest-prefix match so /scan/<id> keeps "New scan" active. */
export function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
