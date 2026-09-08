import { AlertOctagon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * `role="alert"` so a failure is announced, not only shown in red -- the
 * backend has four different error envelope shapes and every one of them
 * eventually lands here.
 */
interface ErrorStateProps {
  title: string;
  detail?: string;
  /** Rendered monospaced under the detail: the rule ID, status code, or the
   *  `legal_basis` string the API returned. Never invent one. */
  code?: string;
  action?: React.ReactNode;
  className?: string;
}

export function ErrorState({
  title,
  detail,
  code,
  action,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-md border border-[var(--verdict-non-compliant-border)] bg-[var(--verdict-non-compliant-bg)] p-4",
        className,
      )}
    >
      <div className="flex items-start gap-2.5">
        <AlertOctagon
          className="mt-0.5 size-4 shrink-0 text-[var(--verdict-non-compliant-fg)]"
          aria-hidden="true"
        />
        <div className="min-w-0">
          <p className="text-sm font-medium text-[var(--verdict-non-compliant-fg)]">
            {title}
          </p>
          {detail && <p className="mt-1 text-sm text-foreground">{detail}</p>}
          {code && (
            <p className="mt-1.5 font-mono text-xs text-fg-muted break-all">{code}</p>
          )}
        </div>
      </div>
      {action && <div className="flex gap-2 pl-6.5">{action}</div>}
    </div>
  );
}

/** Inline variant for a field-level or panel-level failure. */
export function ErrorNotice({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      role="alert"
      className={cn(
        "flex items-start gap-1.5 text-xs text-[var(--verdict-non-compliant-fg)]",
        className,
      )}
    >
      <AlertOctagon className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}
