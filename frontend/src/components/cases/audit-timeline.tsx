"use client";

import { History, RotateCw, ShieldCheck, ShieldX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingRows } from "@/components/common/loading-state";
import { useAsync } from "@/hooks/use-async";
import { fetchCaseAudit } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Reads GET /api/v1/cases/{case_id}/audit (backend/lmd/api/cases.py), an
 * additive read-only endpoint over the existing hash-chained audit_log
 * table (backend/lmd/store/audit.py) -- no write path or schema changed.
 * `chain_verified` is recomputed server-side from the stored prev_hash /
 * entry_hash pairs on every request, not cached, so it reflects the
 * database's actual current state.
 */
export function AuditTimeline({ caseId, refreshKey }: { caseId: string; refreshKey: number }) {
  const { data, error, loading, refetch } = useAsync(
    (signal) => fetchCaseAudit(caseId, signal),
    [caseId, refreshKey],
  );

  if (loading) return <LoadingRows rows={3} className="p-4" />;

  if (error) {
    return (
      <ErrorState
        title="Could not load the audit log"
        detail={error.message}
        action={
          <Button size="sm" variant="outline" onClick={refetch} className="gap-1.5">
            <RotateCw className="size-3.5" aria-hidden="true" />
            Retry
          </Button>
        }
        className="m-4"
      />
    );
  }

  if (!data || data.entries.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No audit entries yet"
        description="Case-affecting actions (creation, status changes) are appended here as a hash chain."
        className="py-8"
      />
    );
  }

  return (
    <div className="p-3">
      <div
        className={cn(
          "mb-3 flex items-center gap-1.5 rounded-sm border px-2 py-1.5 text-xs font-medium",
          data.chain_verified
            ? "border-[var(--verdict-compliant-border)] bg-[var(--verdict-compliant-bg)] text-[var(--verdict-compliant-fg)]"
            : "border-[var(--verdict-non-compliant-border)] bg-[var(--verdict-non-compliant-bg)] text-[var(--verdict-non-compliant-fg)]",
        )}
      >
        {data.chain_verified ? (
          <ShieldCheck className="size-3.5 shrink-0" aria-hidden="true" />
        ) : (
          <ShieldX className="size-3.5 shrink-0" aria-hidden="true" />
        )}
        {data.chain_verified ? "Hash chain verified" : "Hash chain broken"}
      </div>

      <ol className="flex flex-col gap-0">
        {data.entries.map((entry, index) => (
          <li
            key={entry.log_id}
            style={{ "--stagger": index } as React.CSSProperties}
            className="stagger-item relative flex gap-3 pb-4 last:pb-0"
          >
            {index !== data.entries.length - 1 && (
              <span
                aria-hidden="true"
                className="absolute top-4 left-[5px] h-[calc(100%-1rem)] w-px bg-border"
              >
                <span className="animate-draw-line block h-full w-full bg-primary" />
              </span>
            )}
            <span
              aria-hidden="true"
              className="z-10 mt-1 size-2.5 shrink-0 rounded-full border-2 border-primary bg-surface"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm text-foreground">{entry.action}</p>
              <p className="mt-0.5 font-mono text-2xs text-fg-subtle">
                {entry.actor_id} · {formatTimestamp(entry.timestamp)}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
