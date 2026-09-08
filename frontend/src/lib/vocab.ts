/**
 * The single place where a backend enum value becomes a label, an icon and a
 * colour. 21 enum values across 4 vocabularies; if any component hardcodes a
 * colour for a status instead of reading it from here, the vocabularies drift.
 *
 * Every entry carries an icon as well as a colour, so meaning survives
 * greyscale printing and colour-vision deficiency (status is never
 * colour-only).
 */
import {
  AlertTriangle,
  Ban,
  CalendarClock,
  CheckCircle2,
  CircleDashed,
  CircleSlash,
  Clock,
  FileSearch,
  FileText,
  Gavel,
  HelpCircle,
  Layers,
  Ruler,
  Scale,
  ShieldAlert,
  Sigma,
  Split,
  Stamp,
  ThumbsDown,
  XOctagon,
  type LucideIcon,
} from "lucide-react";

import type {
  CaseStatus,
  EvidenceType,
  RuleCategory,
  RuleStatus,
  Severity,
  Verdict,
} from "./types";

export interface VocabEntry {
  label: string;
  icon: LucideIcon;
  /** Tailwind classes built from the semantic tokens in globals.css. */
  className: string;
  /** Short explanation surfaced in tooltips -- these are legally meaningful
   *  distinctions, not decoration. */
  hint?: string;
}

// -- VERDICT --------------------------------------------------------------
export const VERDICT_VOCAB: Record<Verdict, VocabEntry> = {
  COMPLIANT: {
    label: "Compliant",
    icon: CheckCircle2,
    className:
      "text-[var(--verdict-compliant-fg)] bg-[var(--verdict-compliant-bg)] border-[var(--verdict-compliant-border)]",
    hint: "No blocking rule failed and no field was too uncertain to judge.",
  },
  NON_COMPLIANT: {
    label: "Non-compliant",
    icon: XOctagon,
    className:
      "text-[var(--verdict-non-compliant-fg)] bg-[var(--verdict-non-compliant-bg)] border-[var(--verdict-non-compliant-border)]",
    hint: "At least one blocking rule failed. Outranks Needs review in aggregation.",
  },
  NEEDS_REVIEW: {
    label: "Needs review",
    icon: AlertTriangle,
    className:
      "text-[var(--verdict-needs-review-fg)] bg-[var(--verdict-needs-review-bg)] border-[var(--verdict-needs-review-border)]",
    hint: "A first-class outcome, not a soft pass: something could not be read with enough confidence to decide.",
  },
};

// -- RULE STATUS ----------------------------------------------------------
export const RULE_STATUS_VOCAB: Record<RuleStatus, VocabEntry> = {
  PASS: {
    label: "Pass",
    icon: CheckCircle2,
    className:
      "text-[var(--verdict-compliant-fg)] bg-[var(--verdict-compliant-bg)] border-[var(--verdict-compliant-border)]",
  },
  FAIL: {
    label: "Fail",
    icon: XOctagon,
    className:
      "text-[var(--verdict-non-compliant-fg)] bg-[var(--verdict-non-compliant-bg)] border-[var(--verdict-non-compliant-border)]",
  },
  REVIEW: {
    label: "Review",
    icon: AlertTriangle,
    className:
      "text-[var(--verdict-needs-review-fg)] bg-[var(--verdict-needs-review-bg)] border-[var(--verdict-needs-review-border)]",
    hint: "Evaluated, but a field's confidence fell below this rule's threshold.",
  },
  NOT_APPLICABLE: {
    label: "Not applicable",
    icon: CircleSlash,
    className:
      "text-[var(--status-na-fg)] bg-[var(--status-na-bg)] border-[var(--status-na-border)]",
    hint: "This rule's applicable_when condition did not match this commodity.",
  },
  NOT_IN_FORCE: {
    label: "Not in force",
    icon: CalendarClock,
    className:
      "text-[var(--status-not-in-force-fg)] bg-[var(--status-not-in-force-bg)] border-[var(--status-not-in-force-border)]",
    hint: "The rule did not exist in law on the scan date. Point-in-time evaluation, driven by effective_from / effective_to.",
  },
  NOT_EVALUABLE: {
    label: "Not evaluable",
    icon: HelpCircle,
    className:
      "text-[var(--status-not-evaluable-fg)] bg-[var(--status-not-evaluable-bg)] border-[var(--status-not-evaluable-border)] border-dashed",
    hint: "A required legal threshold is not sourced in this build. The system refuses to invent one.",
  },
};

// -- SEVERITY -------------------------------------------------------------
export const SEVERITY_VOCAB: Record<Severity, VocabEntry> = {
  BLOCKER: {
    label: "Blocker",
    icon: ShieldAlert,
    className: "text-[var(--sev-blocker)]",
    hint: "A failure here can produce a Non-compliant verdict.",
  },
  MAJOR: {
    label: "Major",
    icon: AlertTriangle,
    className: "text-[var(--sev-major)]",
  },
  MINOR: {
    label: "Minor",
    icon: CircleDashed,
    className: "text-[var(--sev-minor)]",
  },
  DIAGNOSTIC: {
    label: "Diagnostic",
    icon: FileSearch,
    className: "text-[var(--sev-diagnostic)]",
    hint: "Advisory only. Structurally incapable of producing a Non-compliant verdict.",
  },
};

/** Left border rule width/colour per severity, applied to rule rows. */
export const SEVERITY_BORDER: Record<Severity, string> = {
  BLOCKER: "border-l-2 border-l-[var(--sev-blocker)]",
  MAJOR: "border-l-2 border-l-[var(--sev-major)]",
  MINOR: "border-l-2 border-l-[var(--sev-minor)]",
  DIAGNOSTIC: "border-l-2 border-l-[var(--sev-diagnostic)] border-dashed",
};

// -- RULE CATEGORY --------------------------------------------------------
export const CATEGORY_VOCAB: Record<RuleCategory, VocabEntry> = {
  COMPLETENESS: {
    label: "Completeness",
    icon: Layers,
    className: "text-fg-muted",
    hint: "Is the mandatory declaration present at all? Bypasses the confidence gate.",
  },
  FORMAT: { label: "Format", icon: Stamp, className: "text-fg-muted" },
  MATH: { label: "Math", icon: Sigma, className: "text-fg-muted" },
  CONFLICT: { label: "Conflict", icon: Split, className: "text-fg-muted" },
  TEMPORAL: { label: "Temporal", icon: Clock, className: "text-fg-muted" },
  UNCERTAINTY: {
    label: "Uncertainty",
    icon: HelpCircle,
    className: "text-fg-muted",
  },
};

// -- CASE STATUS ----------------------------------------------------------
export const CASE_STATUS_VOCAB: Record<CaseStatus, VocabEntry> = {
  QUEUED: {
    label: "Queued",
    icon: Clock,
    className:
      "text-[var(--status-na-fg)] bg-[var(--status-na-bg)] border-[var(--status-na-border)]",
  },
  UNDER_REVIEW: {
    label: "Under review",
    icon: FileSearch,
    className:
      "text-[var(--verdict-needs-review-fg)] bg-[var(--verdict-needs-review-bg)] border-[var(--verdict-needs-review-border)]",
  },
  CONFIRMED_VIOLATION: {
    label: "Confirmed violation",
    icon: Gavel,
    className:
      "text-[var(--verdict-non-compliant-fg)] bg-[var(--verdict-non-compliant-bg)] border-[var(--verdict-non-compliant-border)]",
    hint: "Requires a recorded reason-to-believe note (Section 15(4)).",
  },
  REJECTED_FALSE_POSITIVE: {
    label: "Rejected — false positive",
    icon: ThumbsDown,
    className:
      "text-[var(--verdict-compliant-fg)] bg-[var(--verdict-compliant-bg)] border-[var(--verdict-compliant-border)]",
  },
  ESCALATED: {
    label: "Escalated",
    icon: Ban,
    className:
      "text-[var(--status-not-in-force-fg)] bg-[var(--status-not-in-force-bg)] border-[var(--status-not-in-force-border)]",
    hint: "Requires a recorded reason-to-believe note (Section 15(4)).",
  },
  CLOSED: {
    label: "Closed",
    icon: CheckCircle2,
    className:
      "text-[var(--status-na-fg)] bg-[var(--status-na-bg)] border-[var(--status-na-border)]",
    hint: "Requires a recorded reason-to-believe note (Section 15(4)).",
  },
};

// -- EVIDENCE TYPE --------------------------------------------------------
export const EVIDENCE_TYPE_VOCAB: Record<EvidenceType, VocabEntry> = {
  PACKAGE_PHOTO: {
    label: "Package photo",
    icon: FileText,
    className: "text-fg-muted",
  },
  CALIBRATION_FRAME: {
    label: "Calibration frame",
    icon: Ruler,
    className: "text-fg-muted",
    hint: "An ID-1 card in frame is what makes absolute millimetre measurement possible.",
  },
  ANNOTATED_OVERLAY: {
    label: "Annotated overlay",
    icon: Scale,
    className: "text-fg-muted",
  },
};

// -- CONFIDENCE -----------------------------------------------------------
/** Thresholds mirror backend/lmd/cv/overlay.py exactly. Changing them here
 *  without changing them there would make the UI disagree with the rendered
 *  evidence PNG. */
export const CONFIDENCE_HIGH = 0.9;
export const CONFIDENCE_MED = 0.7;

export type ConfidenceBand = "high" | "medium" | "low";

export function confidenceBand(confidence: number): ConfidenceBand {
  if (confidence >= CONFIDENCE_HIGH) return "high";
  if (confidence >= CONFIDENCE_MED) return "medium";
  return "low";
}

export const CONFIDENCE_VOCAB: Record<
  ConfidenceBand,
  { label: string; text: string; bg: string; stroke: string }
> = {
  high: {
    label: "High",
    text: "text-[var(--conf-high)]",
    bg: "bg-[var(--verdict-compliant-bg)]",
    stroke: "var(--conf-high)",
  },
  medium: {
    label: "Medium",
    text: "text-[var(--conf-med)]",
    bg: "bg-[var(--verdict-needs-review-bg)]",
    stroke: "var(--conf-med)",
  },
  low: {
    label: "Low",
    text: "text-[var(--conf-low)]",
    bg: "bg-[var(--verdict-non-compliant-bg)]",
    stroke: "var(--conf-low)",
  },
};
