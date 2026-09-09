"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale } from "lucide-react";

import { NAV_GROUP_LABELS, NAV_ITEMS, isNavItemActive, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

/**
 * Hand-written rather than adapted from a catalogue sidebar: every sidebar in
 * the 21st.dev results shipped a team switcher, collapsible multi-tier groups
 * and entrance animation this product has no use for. Five destinations need
 * five links.
 */
function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      title={item.description}
      className={cn(
        "group relative flex min-h-11 items-center gap-2.5 px-3.5 py-2 text-sm transition-colors duration-[var(--dur-fast)]",
        active
          ? "bg-sidebar-accent font-semibold text-sidebar-accent-foreground"
          : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
      )}
    >
      <span
        className={cn(
          "absolute inset-y-1.5 left-0 w-[3px] bg-accent-cta transition-transform duration-[var(--dur)]",
          active ? "scale-y-100" : "scale-y-0",
        )}
        aria-hidden="true"
      />
      <Icon
        className={cn(
          "size-4 shrink-0 transition-transform duration-[var(--dur-fast)]",
          active
            ? "text-sidebar-accent-foreground"
            : "text-sidebar-foreground/50 group-hover:text-sidebar-accent-foreground",
        )}
        aria-hidden="true"
      />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function NavRail({ className }: { className?: string }) {
  const pathname = usePathname();
  const groups = ["work", "reference"] as const;

  return (
    <nav
      aria-label="Main"
      className={cn(
        "bg-gradient-sidebar flex h-full w-[var(--rail-w)] shrink-0 flex-col border-r border-sidebar-border text-sidebar-foreground",
        className,
      )}
    >
      <Link
        href="/"
        className="flex h-[var(--topbar-h)] items-center gap-2 border-b border-sidebar-border px-3"
      >
        <Scale className="size-4 shrink-0 text-sidebar-primary" aria-hidden="true" />
        <span className="truncate text-sm font-semibold tracking-tight text-sidebar-foreground">
          Legal Metrology
        </span>
      </Link>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto py-4">
        {groups.map((group) => (
          <div key={group}>
            <p className="label-caps px-3 pb-1.5 text-sidebar-foreground/45">
              {NAV_GROUP_LABELS[group]}
            </p>
            <div className="flex flex-col">
              {NAV_ITEMS.filter((item) => item.group === group).map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  active={isNavItemActive(pathname, item.href)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-sidebar-border px-3 py-3">
        <p className="label-caps text-sidebar-foreground/45">Problem statement</p>
        <p className="mt-0.5 font-mono text-xs text-sidebar-foreground/70">SIH PS 26034</p>
      </div>
    </nav>
  );
}
