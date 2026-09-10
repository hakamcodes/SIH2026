"use client";

import { usePathname } from "next/navigation";

import { NavRail } from "./nav-rail";
import { TopBar } from "./top-bar";

/**
 * The identity page owns the full viewport (no rail, no top bar) because there
 * is nothing to navigate to before an inspector identity is set.
 */
function isBareRoute(pathname: string) {
  return pathname === "/";
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
          <main className="min-w-0 flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[var(--content-max)] px-4 py-6 sm:px-6">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
