import { VERDICT_VOCAB } from "@/lib/vocab";
import type { Verdict } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Verdict-specific solid gradient + glow, layered on top of the restrained
 *  -fg/-bg/-border trio in VERDICT_VOCAB (which stays the source of truth for
 *  every other rendering of a verdict -- table cells, filter chips, etc). This
 *  bold treatment is reserved for the one full-width banner per scan page. */
const VERDICT_BANNER_STYLE: Record<Verdict, string> = {
  COMPLIANT:
    "glow-compliant bg-[linear-gradient(135deg,var(--verdict-compliant-solid)_0%,var(--verdict-compliant-solid-2)_100%)] text-white border-transparent",
  NON_COMPLIANT:
    "glow-non-compliant bg-[linear-gradient(135deg,var(--verdict-non-compliant-solid)_0%,var(--verdict-non-compliant-solid-2)_100%)] text-white border-transparent",
  NEEDS_REVIEW:
    "glow-needs-review bg-[linear-gradient(135deg,var(--verdict-needs-review-solid)_0%,var(--verdict-needs-review-solid-2)_100%)] text-white border-transparent",
};

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
        "animate-scale-in mb-4 flex items-center gap-4 rounded-lg border px-5 py-4 sm:px-6 sm:py-5",
        VERDICT_BANNER_STYLE[verdict],
      )}
    >
      {/* Icon with pulse ring */}
      <span className="animate-hero-icon relative flex size-11 shrink-0 items-center justify-center rounded-full bg-white/20 sm:size-12">
        {/* Pulse ring — subtle, only plays once then loops slowly */}
        <span
          aria-hidden="true"
          className="animate-pulse-ring absolute inset-0 rounded-full border-2 border-white/40"
        />
        <Icon className="size-6 shrink-0 sm:size-7" aria-hidden="true" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="text-xl font-bold tracking-tight sm:text-2xl">{entry.label}</p>
        {entry.hint && <p className="mt-0.5 text-xs opacity-90 sm:text-sm">{entry.hint}</p>}
      </div>

      {/* Verdict shortcode — large, right-aligned, for quick scan at a distance */}
      <span className="hidden shrink-0 font-mono text-3xl font-black tracking-widest opacity-20 sm:block" aria-hidden="true">
        {verdict === "COMPLIANT" ? "PASS" : verdict === "NON_COMPLIANT" ? "FAIL" : "RVEW"}
      </span>
    </div>
  );
}
