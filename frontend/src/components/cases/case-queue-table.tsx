"use client";

import Link from "next/link";
import { FolderOpen, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingRows } from "@/components/common/loading-state";
import { CaseStatusBadge, VerdictBadge } from "@/components/common/status-badge";
import { useAsync } from "@/hooks/use-async";
import { fetchCases } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";

const QUEUE_COLUMNS = [
  "Case",
  "Status",
  "Scan verdict",
  "Inspector",
  "Opened",
] as const;

export function CaseQueueTable() {
  const { data, error, loading, refetch } = useAsync(
    (signal) => fetchCases({ limit: 100 }, signal),
    [],
  );

  if (loading) {
    return <LoadingRows rows={5} className="p-4" />;
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load the case queue"
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

  if (!data || data.cases.length === 0) {
    return (
      <EmptyState
        icon={FolderOpen}
        title="No cases yet"
        description="Cases are opened from a completed scan. Run a scan, then open a case to review it under the reason-to-believe workflow."
        action={
          <Button asChild size="sm">
            <Link href="/scan">New scan</Link>
          </Button>
        }
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {QUEUE_COLUMNS.map((col) => (
            <TableHead key={col}>{col}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.cases.map((row, index) => (
          <TableRow
            key={row.case_id}
            style={{ "--stagger": index } as React.CSSProperties}
            className="stagger-item cursor-pointer border-l-2 border-l-transparent transition-[background-color,border-color,box-shadow] duration-[var(--dur-fast)] hover:border-l-primary hover:bg-surface-subtle hover:shadow-sm"
            tabIndex={0}
          >
            <TableCell className="p-0">
              <Link
                href={`/cases/${row.case_id}`}
                className="block px-3 py-1.5 font-mono text-xs text-foreground focus-visible:outline-none"
              >
                {row.case_id}
              </Link>
            </TableCell>
            <TableCell>
              <CaseStatusBadge status={row.status} />
            </TableCell>
            <TableCell>
              <VerdictBadge verdict={row.scan_overall_verdict} size="sm" />
            </TableCell>
            <TableCell className="text-sm text-fg-muted">
              {row.assigned_inspector_id ?? "—"}
            </TableCell>
            <TableCell className="font-mono text-xs text-fg-muted">
              {formatTimestamp(row.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
