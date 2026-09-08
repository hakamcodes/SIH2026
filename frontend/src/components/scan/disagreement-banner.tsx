import { Split } from "lucide-react";

import type { PipelineReading } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Reads ocr_pipeline / llm_pipeline (cv/reconcile.py:158-163): both keys are
 * present only when pipeline A (RapidOCR) and pipeline B (vision model) each
 * produced a numeric candidate for the same field (MRP preferred, net
 * quantity as fallback -- reconcile.py does not record which one it was).
 * Per invariant 7 the vision model is never the sole source of a numeric
 * legal field, so disagreement here is exactly what routes LM-U02 to
 * NEEDS_REVIEW; this banner surfaces that live rather than leaving it
 * implicit in a rule row.
 */
export function DisagreementBanner({
  ocrPipeline,
  llmPipeline,
}: {
  ocrPipeline: PipelineReading | null | undefined;
  llmPipeline: PipelineReading | null | undefined;
}) {
  if (!ocrPipeline || !llmPipeline) {
    return (
      <p className="flex items-start gap-1.5 rounded-sm border border-dashed border-border bg-surface-subtle p-2.5 text-xs text-fg-muted">
        <Split className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        Pipeline B (vision model) produced no comparable numeric reading for
        this scan — no cross-check was possible, and no numeric field&apos;s
        acceptance depended on one.
      </p>
    );
  }

  const agree = ocrPipeline.numeric_val === llmPipeline.numeric_val;

  return (
    <p
      className={cn(
        "flex items-start gap-1.5 rounded-sm border p-2.5 text-xs",
        agree
          ? "border-[var(--verdict-compliant-border)] bg-[var(--verdict-compliant-bg)] text-[var(--verdict-compliant-fg)]"
          : "border-[var(--verdict-needs-review-border)] bg-[var(--verdict-needs-review-bg)] text-[var(--verdict-needs-review-fg)]",
      )}
    >
      <Split className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
      <span>
        Pipeline A (OCR) read <span className="font-mono">{ocrPipeline.text_val}</span>; pipeline
        B (vision) read <span className="font-mono">{llmPipeline.text_val}</span> for the same
        numeric field.{" "}
        {agree
          ? "Both pipelines agree."
          : "Disagreement routes this field's rule to Needs review — a confidently wrong digit is worse than a flagged one."}
      </span>
    </p>
  );
}
