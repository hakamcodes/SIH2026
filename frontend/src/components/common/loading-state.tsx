import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** Generic row-skeleton loader. `aria-busy` on the wrapper, not a spinner --
 *  a stable skeleton avoids the flicker a spinner produces on a fast load. */
export function LoadingRows({
  rows = 4,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div aria-busy="true" aria-live="polite" className={cn("flex flex-col gap-2", className)}>
      <span className="sr-only">Loading…</span>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  );
}

export function LoadingPanel({ className }: { className?: string }) {
  return (
    <div aria-busy="true" aria-live="polite" className={cn("flex flex-col gap-3 p-4", className)}>
      <span className="sr-only">Loading…</span>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}
