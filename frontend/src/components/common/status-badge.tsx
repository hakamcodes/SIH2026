"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { VocabEntry } from "@/lib/vocab";
import {
  CASE_STATUS_VOCAB,
  EVIDENCE_TYPE_VOCAB,
  RULE_STATUS_VOCAB,
  SEVERITY_VOCAB,
  VERDICT_VOCAB,
} from "@/lib/vocab";
import type {
  CaseStatus,
  EvidenceType,
  RuleStatus,
  Severity,
  Verdict,
} from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * The only badge primitive in the product. Every status-shaped value renders
 * through here so 21 enum values across 5 vocabularies stay visually
 * consistent, and so no component invents its own colour for a status.
 *
 * Always renders icon + text label: status is never conveyed by colour alone.
 */
interface StatusBadgeProps {
  entry: VocabEntry;
  size?: "sm" | "md";
  /** Hide the text label. Only for genuinely space-constrained cells; the
   *  label still reaches assistive tech via aria-label. */
  iconOnly?: boolean;
  className?: string;
}

export function StatusBadge({
  entry,
  size = "md",
  iconOnly = false,
  className,
}: StatusBadgeProps) {
  const Icon = entry.icon;

  const badge = (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-sm border font-medium whitespace-nowrap",
        size === "sm" ? "px-1.5 py-0.5 text-2xs" : "px-2 py-0.5 text-xs",
        entry.className,
        className,
      )}
      aria-label={iconOnly ? entry.label : undefined}
    >
      <Icon
        className={size === "sm" ? "size-3 shrink-0" : "size-3.5 shrink-0"}
        aria-hidden="true"
      />
      {!iconOnly && <span>{entry.label}</span>}
    </span>
  );

  if (!entry.hint) return badge;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{badge}</TooltipTrigger>
      <TooltipContent className="max-w-xs">{entry.hint}</TooltipContent>
    </Tooltip>
  );
}

// -- Thin wrappers, one per vocabulary ------------------------------------

export function VerdictBadge({
  verdict,
  ...rest
}: { verdict: Verdict } & Omit<StatusBadgeProps, "entry">) {
  return <StatusBadge entry={VERDICT_VOCAB[verdict]} {...rest} />;
}

export function RuleStatusBadge({
  status,
  ...rest
}: { status: RuleStatus } & Omit<StatusBadgeProps, "entry">) {
  return <StatusBadge entry={RULE_STATUS_VOCAB[status]} {...rest} />;
}

export function CaseStatusBadge({
  status,
  ...rest
}: { status: CaseStatus } & Omit<StatusBadgeProps, "entry">) {
  return <StatusBadge entry={CASE_STATUS_VOCAB[status]} {...rest} />;
}

export function EvidenceTypeBadge({
  evidenceType,
  ...rest
}: { evidenceType: EvidenceType } & Omit<StatusBadgeProps, "entry">) {
  return <StatusBadge entry={EVIDENCE_TYPE_VOCAB[evidenceType]} {...rest} />;
}

/** Severity reads as a plain labelled marker, not a filled pill: the filled
 *  treatment is reserved for outcomes, and a severity is not an outcome. */
export function SeverityLabel({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  const entry = SEVERITY_VOCAB[severity];
  const Icon = entry.icon;

  const content = (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-medium whitespace-nowrap",
        entry.className,
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden="true" />
      {entry.label}
    </span>
  );

  if (!entry.hint) return content;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{content}</TooltipTrigger>
      <TooltipContent className="max-w-xs">{entry.hint}</TooltipContent>
    </Tooltip>
  );
}
