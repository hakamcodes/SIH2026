"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ScanLine } from "lucide-react";

import { BottomTabBar, NavRail } from "./nav-rail";
import { TopBar } from "./top-bar";

/**
 * The identity page owns the full viewport (no rail, no top bar) because there
 * is nothing to navigate to before an inspector identity is set.
 */
function isBareRoute(pathname: string) {
  return pathname === "/";
}

/** Mobile FAB — fixed "New Scan" button for quick access while in the field.
 *  Hidden on the /scan route (already there) and on desktop (NavRail handles it). */
function MobileFAB({ pathname }: { pathname: string }) {
  if (pathname === "/scan" || pathname.startsWith("/scan/")) return null;
  return (
    <Link
      href="/scan"
      aria-label="New scan"
      className="fixed bottom-[4.5rem] right-4 z-40 flex items-center gap-2 rounded-full bg-gradient-primary px-4 py-3 text-sm font-semibold text-white shadow-lg transition-[box-shadow,transform] duration-[var(--dur)] hover:-translate-y-px hover:shadow-xl active:scale-95 lg:hidden"
      data-no-print
    >
      <ScanLine className="size-4 shrink-0" aria-hidden="true" />
      Scan
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (isBareRoute(pathname)) {
    return (
      <div className="flex min-h-dvh flex-col">
        <div className="flex flex-1 flex-col">{children}</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <div className="flex flex-1 overflow-hidden">
        <NavRail className="hidden lg:flex" />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="min-w-0 flex-1 overflow-y-auto pb-20 lg:pb-0" data-no-print="">
            <div
              key={pathname}
              className="animate-page-enter mx-auto max-w-[var(--content-max)] px-4 py-6 sm:px-6"
            >
              {children}
            </div>
          </main>
        </div>
      </div>
      {/* Mobile bottom tab bar — hidden on lg+ (NavRail takes over) */}
      <BottomTabBar />
      <MobileFAB pathname={pathname} />
    </div>
  );
}
