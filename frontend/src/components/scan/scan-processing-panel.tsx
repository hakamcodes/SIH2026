import { CheckCircle2, Cpu, Loader2, ScanLine, UploadCloud } from "lucide-react";

import { cn } from "@/lib/utils";

export type ScanProcessingPhase = "uploading" | "processing" | "finalizing";

const SERVER_STAGE_CAPTIONS = [
  "Running RapidOCR text extraction…",
  "Structuring extracted fields (net quantity, MRP, dates, manufacturer)…",
  "Cross-checking numeric fields against the vision model, where configured…",
  "Evaluating the loaded ruleset against extracted fields…",
] as const;

interface StepDef {
  key: string;
  label: string;
  icon: typeof UploadCloud;
}

const STEPS: StepDef[] = [
  { key: "uploading", label: "Uploading image", icon: UploadCloud },
  { key: "processing", label: "Server-side processing", icon: Cpu },
  { key: "finalizing", label: "Finalizing result", icon: ScanLine },
];

function stepState(step: string, phase: ScanProcessingPhase): "done" | "active" | "pending" {
  const order = ["uploading", "processing", "finalizing"];
  const stepIndex = order.indexOf(step);
  const phaseIndex = order.indexOf(phase);
  if (stepIndex < phaseIndex) return "done";
  if (stepIndex === phaseIndex) return "active";
  return "pending";
}

/**
 * A single POST /api/v1/scans call runs pipeline A, optionally pipeline B,
 * and the rule engine server-side in one request -- there is no streaming
 * endpoint, so the individual stages inside "server-side processing" cannot
 * be observed from the browser. Rather than invent a fake percentage for
 * that phase, this shows a real upload percentage (measured via
 * XMLHttpRequest.upload.onprogress), then an honestly-indeterminate step
 * with an elapsed timer and rotating captions describing the pipeline's
 * known stages -- captions describe what the pipeline generally does, not a
 * confirmed live position in it.
 */
export function ScanProcessingPanel({
  phase,
  uploadPercent,
  elapsedSeconds,
  captionIndex,
}: {
  phase: ScanProcessingPhase;
  uploadPercent: number;
  elapsedSeconds: number;
  captionIndex: number;
}) {
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const elapsedLabel = `${minutes}:${String(seconds).padStart(2, "0")}`;

  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-in fade-in flex flex-col gap-5 rounded-md border border-border bg-surface-subtle/40 p-5 sm:p-6 duration-300"
    >
      <ol className="flex flex-col gap-0">
        {STEPS.map((step, index) => {
          const state = stepState(step.key, phase);
          const Icon = step.icon;
          const isLast = index === STEPS.length - 1;
          return (
            <li key={step.key} className="relative flex gap-3 pb-6 last:pb-0">
              {/* Vertical connector line */}
              {!isLast && (
                <span
                  aria-hidden="true"
                  className="absolute top-7 left-[13px] h-[calc(100%-1.75rem)] w-px bg-border"
                >
                  <span
                    className={cn(
                      "animate-draw-line block h-full w-full bg-gradient-primary",
                      state !== "done" && "hidden",
                    )}
                  />
                </span>
              )}

              {/* Step indicator */}
              <span
                className={cn(
                  "relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full border transition-colors duration-[var(--dur)]",
                  state === "done" &&
                    "border-[var(--verdict-compliant-border)] bg-[var(--verdict-compliant-bg)] text-[var(--verdict-compliant-fg)]",
                  state === "active" &&
                    "border-primary bg-surface text-primary shadow-[0_0_0_4px_color-mix(in_oklab,var(--primary)_12%,transparent)]",
                  state === "pending" && "border-border bg-surface text-fg-subtle",
                )}
                aria-hidden="true"
              >
                {/* Pulse ring on active step */}
                {state === "active" && (
                  <span
                    aria-hidden="true"
                    className="animate-pulse-ring absolute inset-0 rounded-full border border-primary"
                  />
                )}
                {state === "done" ? (
                  <CheckCircle2 className="size-4" />
                ) : state === "active" ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Icon className="size-3.5" />
                )}
              </span>

              <div className="min-w-0 flex-1 pt-0.5">
                <p
                  className={cn(
                    "text-sm",
                    state === "pending" ? "text-fg-subtle" : "font-medium text-foreground",
                  )}
                >
                  {step.label}
                </p>

                {step.key === "uploading" && state === "active" && (
                  <div className="mt-2 max-w-xs">
                    <div className="relative h-1.5 overflow-hidden rounded-full bg-border">
                      <div
                        className="shimmer relative h-full overflow-hidden rounded-full bg-gradient-primary transition-[width] duration-150"
                        style={{ width: `${uploadPercent}%` }}
                      />
                    </div>
                    <p className="mt-1 font-mono text-2xs text-fg-subtle">{uploadPercent}%</p>
                  </div>
                )}

                {step.key === "processing" && state === "active" && (
                  <div className="mt-1.5 flex flex-col gap-1.5">
                    <div className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-border">
                      <div className="h-full w-1/3 rounded-full bg-gradient-primary animate-indeterminate" />
                    </div>
                    <p className="text-xs text-fg-muted" aria-live="off">
                      {SERVER_STAGE_CAPTIONS[captionIndex % SERVER_STAGE_CAPTIONS.length]}
                    </p>
                    <p className="font-mono text-2xs text-fg-subtle">
                      Elapsed{" "}
                      <span className="tabular-nums">{elapsedLabel}</span>
                      {" "}— exact stage isn&apos;t reported by the backend; this can take up
                      to a minute on the first scan while the OCR model loads.
                    </p>
                  </div>
                )}

                {step.key === "finalizing" && state === "active" && (
                  <p className="mt-1 text-xs text-fg-muted">Preparing the scan review page…</p>
                )}

                {step.key === "uploading" && state === "done" && (
                  <p className="mt-0.5 text-xs text-[var(--verdict-compliant-fg)]">Complete</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
