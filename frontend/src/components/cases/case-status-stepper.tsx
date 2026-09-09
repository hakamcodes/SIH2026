"use client";

import { useState } from "react";
import { Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CaseStatusBadge } from "@/components/common/status-badge";
import { useInspector } from "@/components/shell/inspector-provider";
import { updateCase } from "@/lib/api";
import { describeUnknownError } from "@/lib/errors";
import { CASE_STATUS_VOCAB } from "@/lib/vocab";
import { REASON_TO_BELIEVE_GATED_STATUSES } from "@/lib/types";
import type { CaseStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

import { ReasonToBelieveDialog } from "./reason-to-believe-dialog";

/**
 * The primary path a case takes. REJECTED_FALSE_POSITIVE is a branch off
 * UNDER_REVIEW rather than a step on this line -- it is offered as a
 * separate action, not a rung on the ladder, so the stepper does not imply
 * a case must pass through it to reach CLOSED.
 */
const PRIMARY_PATH: CaseStatus[] = [
  "QUEUED",
  "UNDER_REVIEW",
  "CONFIRMED_VIOLATION",
  "ESCALATED",
  "CLOSED",
];

interface CaseStatusStepperProps {
  status: CaseStatus;
  caseId: string;
  onChanged: () => void;
}

export function CaseStatusStepper({ status, caseId, onChanged }: CaseStatusStepperProps) {
  const { inspector } = useInspector();
  const [pending, setPending] = useState<CaseStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gateTarget, setGateTarget] = useState<CaseStatus | null>(null);

  const currentIndex = PRIMARY_PATH.indexOf(status);

  async function advance(target: CaseStatus) {
    if (!inspector) {
      setError("Sign in with an inspector identity first.");
      return;
    }
    if (REASON_TO_BELIEVE_GATED_STATUSES.includes(target)) {
      setGateTarget(target);
      return;
    }
    setPending(target);
    setError(null);
    try {
      await updateCase(caseId, { status: target }, inspector.inspectorId);
      onChanged();
    } catch (err) {
      setError(describeUnknownError(err));
    } finally {
      setPending(null);
    }
  }

  return (
    <div>
      <ol className="flex flex-wrap items-center gap-0">
        {PRIMARY_PATH.map((step, index) => {
          const entry = CASE_STATUS_VOCAB[step];
          const Icon = entry.icon;
          const done = index < currentIndex;
          const active = index === currentIndex;
          const reachable = index === currentIndex + 1;
          const isLast = index === PRIMARY_PATH.length - 1;

          return (
            <li key={step} className="flex items-center">
              <button
                type="button"
                disabled={!reachable || pending !== null}
                onClick={() => advance(step)}
                title={reachable ? `Advance to ${entry.label}` : entry.label}
                className={cn(
                  "flex items-center gap-1.5 rounded-sm border px-2 py-1.5 text-xs font-medium transition-colors duration-[var(--dur-fast)]",
                  active &&
                    "animate-pulse border-transparent bg-gradient-primary text-primary-foreground shadow-md",
                  done && "border-[var(--verdict-compliant-border)] bg-[var(--verdict-compliant-bg)] text-[var(--verdict-compliant-fg)]",
                  !active && !done && "border-dashed border-border text-fg-subtle",
                  reachable && !active && "border-border bg-surface text-foreground hover:border-border-strong hover:shadow-sm",
                  reachable && "cursor-pointer",
                  !reachable && "cursor-default",
                )}
              >
                {pending === step ? (
                  <Loader2 className="size-3.5 shrink-0 animate-spin" aria-hidden="true" />
                ) : done ? (
                  <Check className="size-3.5 shrink-0" aria-hidden="true" />
                ) : (
                  <Icon className="size-3.5 shrink-0" aria-hidden="true" />
                )}
                {entry.label}
              </button>
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={cn("mx-1 h-0.5 w-4 rounded-full transition-colors duration-[var(--dur)]", done ? "bg-gradient-primary" : "bg-border")}
                />
              )}
            </li>
          );
        })}
      </ol>

      {status === "UNDER_REVIEW" && (
        <div className="mt-2">
          <Button
            variant="outline"
            size="sm"
            disabled={pending !== null}
            onClick={() => advance("REJECTED_FALSE_POSITIVE")}
          >
            Reject — false positive
          </Button>
        </div>
      )}

      {status === "REJECTED_FALSE_POSITIVE" && (
        <p className="mt-2 text-xs text-fg-muted">
          <CaseStatusBadge status={status} size="sm" /> is a terminal branch off Under review, not
          part of the confirmed-violation path.
        </p>
      )}

      {error && <p className="mt-2 text-xs text-[var(--verdict-non-compliant-fg)]">{error}</p>}

      {gateTarget && (
        <ReasonToBelieveDialog
          caseId={caseId}
          targetStatus={gateTarget}
          onClose={() => setGateTarget(null)}
          onSuccess={() => {
            setGateTarget(null);
            onChanged();
          }}
        />
      )}
    </div>
  );
}
