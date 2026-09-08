import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

export interface Breadcrumb {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  /** Small uppercase label above the title, naming the section (e.g. "Scan
   *  review", "Ruleset"). Purely a hierarchy device -- falls back to nothing
   *  rather than repeating the title. */
  eyebrow?: string;
  /** One sentence stating what this page is for. Not marketing copy. */
  description?: string;
  breadcrumbs?: Breadcrumb[];
  /** Right-aligned primary actions. */
  actions?: React.ReactNode;
  /** Status badge or similar, sits inline after the title. */
  meta?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  eyebrow,
  description,
  breadcrumbs,
  actions,
  meta,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "mb-6 animate-in fade-in slide-in-from-bottom-1 border-b border-border pb-5 duration-300",
        className,
      )}
    >
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1 text-xs text-fg-subtle">
            {breadcrumbs.map((crumb, index) => (
              <li key={`${crumb.label}-${index}`} className="flex items-center gap-1">
                {index > 0 && (
                  <ChevronRight className="size-3 shrink-0" aria-hidden="true" />
                )}
                {crumb.href ? (
                  <Link
                    href={crumb.href}
                    className="hover:text-foreground hover:underline hover:underline-offset-2"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-fg-muted">{crumb.label}</span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          {eyebrow && <p className="label-caps mb-1 text-link">{eyebrow}</p>}
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight text-balance">{title}</h1>
            {meta}
          </div>
          {description && (
            <p className="mt-1.5 max-w-3xl text-sm text-fg-muted text-pretty">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}
