"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Menu, Scale, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { NAV_GROUP_LABELS, NAV_ITEMS, isNavItemActive } from "@/lib/nav";
import { cn } from "@/lib/utils";

import { useInspector } from "./inspector-provider";

const RULESET_VERSION = process.env.NEXT_PUBLIC_LMD_RULESET_VERSION ?? "v1";

function MobileNav() {
  const pathname = usePathname();
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-11 lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="size-4" aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[17rem] p-0">
        <SheetTitle className="flex h-[var(--topbar-h)] items-center gap-2 border-b border-border px-4 text-sm font-semibold">
          <Scale className="size-4" aria-hidden="true" />
          Legal Metrology
        </SheetTitle>
        <nav aria-label="Main" className="flex flex-col gap-5 py-4">
          {(["work", "reference"] as const).map((group) => (
            <div key={group}>
              <p className="label-caps px-4 pb-1.5">{NAV_GROUP_LABELS[group]}</p>
              {NAV_ITEMS.filter((item) => item.group === group).map((item) => {
                const Icon = item.icon;
                const active = isNavItemActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex min-h-11 items-center gap-2.5 border-l-2 px-4 text-sm transition-colors duration-[var(--dur-fast)]",
                      active
                        ? "border-l-primary bg-surface-subtle font-medium text-foreground"
                        : "border-l-transparent text-fg-muted hover:bg-surface-subtle hover:text-foreground",
                    )}
                  >
                    <Icon className="size-4 shrink-0" aria-hidden="true" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  );
}

export function TopBar() {
  const { inspector, signOut } = useInspector();

  return (
    <header className="shadow-sm relative z-10 flex h-[var(--topbar-h)] shrink-0 items-center gap-2 border-b border-border bg-surface/80 px-2 backdrop-blur-md sm:px-4">
      <MobileNav />

      <Link
        href="/"
        className="flex items-center gap-2 text-sm font-semibold text-primary lg:hidden"
      >
        <Scale className="size-4" aria-hidden="true" />
        Legal Metrology
      </Link>

      <div className="ml-auto flex items-center gap-3">
        <div className="hidden items-baseline gap-1.5 sm:flex">
          <span className="label-caps">Ruleset</span>
          <span className="font-mono text-xs text-fg-muted">{RULESET_VERSION}</span>
        </div>

        {inspector ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-2 font-normal"
              >
                <UserRound className="size-3.5" aria-hidden="true" />
                <span className="max-w-[10rem] truncate">{inspector.name}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuLabel className="font-normal">
                <p className="text-sm font-medium">{inspector.name}</p>
                <p className="text-xs text-fg-muted">{inspector.designation}</p>
                <p className="mt-1 font-mono text-2xs text-fg-subtle">
                  X-Inspector-Id: {inspector.inspectorId}
                </p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={signOut}>
                <LogOut className="size-3.5" aria-hidden="true" />
                Change identity
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button asChild variant="outline" size="sm" className="h-8">
            <Link href="/">Set identity</Link>
          </Button>
        )}
      </div>
    </header>
  );
}
