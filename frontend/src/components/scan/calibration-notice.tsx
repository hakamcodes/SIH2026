import { Ruler } from "lucide-react";

import type { Calibration } from "@/lib/types";

/**
 * Per invariant 9: never guess a physical scale. Without an ID-1 calibration
 * card in frame, calibration is null and this states that plainly rather
 * than letting absolute-millimetre claims go unrendered and unexplained.
 */
export function CalibrationNotice({ calibration }: { calibration: Calibration | null | undefined }) {
  if (calibration) {
    return (
      <p className="flex items-center gap-1.5 text-2xs text-fg-subtle">
        <Ruler className="size-3 shrink-0" aria-hidden="true" />
        Calibration card detected — {calibration.px_per_mm.toFixed(2)} px/mm. Absolute millimetre
        measurements on this scan are demonstrable.
      </p>
    );
  }

  return (
    <p className="flex items-center gap-1.5 text-2xs text-fg-subtle">
      <Ruler className="size-3 shrink-0" aria-hidden="true" />
      No ID-1 calibration card detected in frame — absolute millimetre measurement is unavailable
      for this scan. Relative height ratios remain valid.
    </p>
  );
}
