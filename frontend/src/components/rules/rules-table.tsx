"use client";

import { useMemo } from "react";
import { BookText, RotateCw } from "lucide-react";

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
import { SeverityLabel } from "@/components/common/status-badge";
import { useAsync } from "@/hooks/use-async";
import { fetchRules } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { RuleCategory, Severity } from "@/lib/types";
import { CATEGORY_VOCAB } from "@/lib/vocab";
import { cn } from "@/lib/utils";

interface RulesTableProps {
  categoryFilter: RuleCategory | null;
  severityFilter: Severity | null;
  /** Bumped by RulesetReloadButton after a successful POST /rules/reload so
   *  this table refetches and shows the post-reload rule_count/rows. */
  refreshKey?: number;
}

export function RulesTable({ categoryFilter, severityFilter, refreshKey = 0 }: RulesTableProps) {
  const { data, error, loading, refetch } = useAsync(
    (signal) => fetchRules(signal),
    [refreshKey],
  );

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.rules.filter((rule) => {
      if (categoryFilter && rule.category !== categoryFilter) return false;
      if (severityFilter && rule.severity !== severityFilter) return false;
      return true;
    });
  }, [data, categoryFilter, severityFilter]);

  if (loading) {
    return <LoadingRows rows={6} className="p-4" />;
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load the ruleset"
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

  if (!data || data.rules.length === 0) {
    return (
      <EmptyState
        icon={BookText}
        title="No rules loaded"
        description="GET /api/v1/rules returned an empty ruleset."
      />
    );
  }

  if (filtered.length === 0) {
    return (
      <EmptyState
        icon={BookText}
        title="No rules match these filters"
        description={`${data.rule_count} rules are loaded in total. Clear a filter to see them.`}
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-28">Rule</TableHead>
            <TableHead className="w-32">Category</TableHead>
            <TableHead>Description</TableHead>
            <TableHead className="w-28">Severity</TableHead>
            <TableHead className="w-28">In force from</TableHead>
            <TableHead className="min-w-64">Legal basis</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((rule) => {
            const category = CATEGORY_VOCAB[rule.category as RuleCategory];
            return (
              <TableRow key={rule.rule_id}>
                <TableCell className="font-mono text-xs">{rule.rule_id}</TableCell>
                <TableCell>
                  {category ? (
                    <span className="inline-flex items-center gap-1.5 text-xs text-fg-muted">
                      <category.icon className="size-3.5 shrink-0" aria-hidden="true" />
                      {category.label}
                    </span>
                  ) : (
                    rule.category
                  )}
                </TableCell>
                <TableCell className="max-w-md text-sm">{rule.description}</TableCell>
                <TableCell>
                  <SeverityLabel severity={rule.severity} />
                </TableCell>
                <TableCell className="font-mono text-xs text-fg-muted">
                  {formatDate(rule.effective_from)}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-xs",
                    rule.citation_verified ? "text-fg-muted" : "text-fg-subtle italic",
                  )}
                  title={rule.citation_verified ? undefined : "Illustrative — not yet verified against a primary source"}
                >
                  {rule.legal_basis}
                  {!rule.citation_verified && (
                    <span className="ml-1.5 rounded-sm border border-border px-1 py-0.5 text-2xs">
                      illustrative
                    </span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
