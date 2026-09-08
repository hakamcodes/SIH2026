import { VERDICT_VOCAB } from "@/lib/vocab";
import type { Verdict } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The scan review page's single most important fact -- overall_verdict --
 * was previously a small badge tucked into a panel header. Promoted to a
 * full-width band so it reads at a glance, the way a lab report leads with
 * PASS/FAIL rather than burying it in a table.
 */
export function VerdictBanner({ verdict }: { verdict: Verdict }) {
  const entry = VERDICT_VOCAB[verdict];
  const Icon = entry.icon;

  return (
    <div
      className={cn(
        "shadow-panel mb-4 flex items-center gap-3 rounded-md border px-4 py-3 sm:px-5 sm:py-3.5",
        entry.className,
      )}
    >
      <Icon className="size-6 shrink-0 sm:size-7" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-lg font-semibold tracking-tight sm:text-xl">{entry.label}</p>
        {entry.hint && <p className="text-xs opacity-90 sm:text-sm">{entry.hint}</p>}
      </div>
    </div>
  );
}
