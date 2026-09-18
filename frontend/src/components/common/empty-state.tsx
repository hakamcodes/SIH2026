import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Adapted from 21st.dev `@cnippet-dev/cnippet-empty` (composable Empty /
 * EmptyHeader / EmptyMedia / EmptyTitle / EmptyDescription / EmptyContent,
 * dependency-free).
 *
 * Adapted: collapsed the six exported slots into one props-driven component
 * because this product needs exactly one empty-state layout, not a
 * composition kit. Removed the `icon` variant's two decorative rotated
 * "stacked card" pseudo-elements and its shadow, which are the fake-depth
 * treatment this design direction rules out. Kept its structure (icon,
 * title, description, action), its restraint (no illustration), and its
 * text-balance/max-width choices.
 *
 * Polished: icon container now uses a layered halo + gradient-primary
 * accent to match the hero icon treatment, while keeping the same palette.
 */
interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "animate-in fade-in zoom-in-95 flex min-w-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-14 text-center duration-300",
        className,
      )}
    >
      {/* Layered halo + icon container */}
      <div className="relative flex items-center justify-center">
        {/* Outer halo ring */}
        <span
          aria-hidden="true"
          className="absolute size-16 rounded-full border border-border bg-surface-subtle opacity-60"
        />
        {/* Inner gradient icon container */}
        <span className="relative flex size-11 items-center justify-center rounded-full border border-border bg-gradient-to-br from-surface to-surface-subtle shadow-sm">
          <Icon className="size-4.5 text-fg-subtle" aria-hidden="true" />
        </span>
      </div>

      <div className="flex max-w-sm flex-col items-center">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && (
          <p className="mt-1 text-pretty text-sm text-fg-muted">{description}</p>
        )}
      </div>
      {action && <div className="flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}
