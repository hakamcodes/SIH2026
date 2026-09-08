import { Ruler } from "lucide-react";

import { DataRow } from "@/components/common/panel";
import { formatValue } from "@/lib/format";
import { CONFIDENCE_VOCAB, confidenceBand } from "@/lib/vocab";
import type { OcrBox } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Shows the evidence behind one OCR box: the raw text, extraction
 * confidence, and font metrics -- including height_mm, which per invariant 9
 * must render as an explicit "no calibration reference" statement rather
 * than a blank whenever it is null.
 */
export function BoxDetailPanel({ box }: { box: OcrBox | null }) {
  if (!box) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-fg-subtle">
        <Ruler className="size-3.5 shrink-0" aria-hidden="true" />
        Hover or select a box on the image to inspect its OCR evidence.
      </p>
    );
  }

  const band = confidenceBand(box.confidence);
  const vocab = CONFIDENCE_VOCAB[band];

  return (
    <div
      className={cn(
        "animate-in fade-in rounded-sm border-l-[3px] bg-surface-subtle/60 py-1 pl-3 duration-150",
      )}
      style={{ borderLeftColor: vocab.stroke }}
    >
      <p className="label-caps mb-0.5">Selected OCR box</p>
      <dl>
        <DataRow label="Recognized text" value={box.text || "—"} mono />
        <DataRow
          label="Confidence"
          value={
            <span className={vocab.text}>
              {(box.confidence * 100).toFixed(0)}% ({vocab.label})
            </span>
          }
          mono
        />
        <DataRow label="Per-box enhancement" value={box.enhanced ? "Applied" : "Raw"} />
        <DataRow
          label="Ink height"
          value={
            box.font_metrics.height_mm !== null
              ? `${box.font_metrics.height_mm.toFixed(2)} mm`
              : "Not measurable"
          }
          mono
        />
      </dl>
      {!box.font_metrics.measurable && (
        <p className="mt-1.5 mb-1 rounded-sm border border-dashed border-border bg-surface p-2 text-2xs text-fg-muted">
          {box.font_metrics.reason === "no_calibration_reference_in_frame"
            ? "No calibration reference (ID-1 card) was in frame, so absolute millimetre measurement is unavailable. Relative height ratios remain valid; this figure does not."
            : formatValue(box.font_metrics.reason)}
        </p>
      )}
    </div>
  );
}
