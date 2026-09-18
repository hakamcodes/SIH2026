"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale } from "lucide-react";

import { NAV_GROUP_LABELS, NAV_ITEMS, isNavItemActive, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

/**
 * Desktop: left sidebar rail (hidden below lg breakpoint).
 * Mobile: bottom tab bar (fixed, shown below lg breakpoint only).
 * Both use the same NavItem data; the layout differs.
 */
function NavLink({ item, active, compact }: { item: NavItem; active: boolean; compact?: boolean }) {
  const Icon = item.icon;
  if (compact) {
    // Mobile bottom tab bar: icon + short label, no active bar
    return (
      <Link
        href={item.href}
        aria-current={active ? "page" : undefined}
        title={item.description}
        className={cn(
          "flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium transition-colors duration-[var(--dur-fast)]",
          active
            ? "text-primary"
            : "text-fg-muted hover:text-foreground",
        )}
      >
        <span className="relative flex items-center justify-center">
          <Icon
            className={cn("size-5 shrink-0 transition-transform duration-[var(--dur)]", active ? "text-primary scale-110" : "text-fg-muted")}
            aria-hidden="true"
          />
          {/* Active indicator dot under icon */}
          {active && (
            <span
              aria-hidden="true"
              className="absolute -bottom-1 left-1/2 size-1 -translate-x-1/2 rounded-full bg-primary"
            />
          )}
        </span>
        <span className="mt-1 truncate max-w-[56px] text-center leading-tight">{item.label}</span>
      </Link>
    );
  }

  // Desktop sidebar link
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
          "absolute inset-y-1.5 left-0 w-[3px] rounded-r-full bg-accent-cta transition-transform duration-[var(--dur)]",
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
        className="flex h-[var(--topbar-h)] items-center gap-2 border-b border-sidebar-border px-3 transition-opacity duration-[var(--dur)] hover:opacity-80"
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

/** Mobile bottom tab bar — shown on small screens, hidden on lg+.
 *  Frosted glass effect with safe-area-inset-bottom support. */
export function BottomTabBar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main navigation"
      className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-border bg-surface/90 backdrop-blur-md lg:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      data-no-print
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.href}
          item={item}
          active={isNavItemActive(pathname, item.href)}
          compact
        />
      ))}
    </nav>
  );
}
