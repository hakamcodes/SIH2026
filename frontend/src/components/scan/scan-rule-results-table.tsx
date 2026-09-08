import { Fragment } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RuleStatusBadge, SeverityLabel } from "@/components/common/status-badge";
import type { RuleResultRow } from "@/lib/types";
import { CATEGORY_VOCAB } from "@/lib/vocab";
import type { RuleCategory } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Grouped by category (COMPLETENESS, FORMAT, MATH, CONFLICT, TEMPORAL,
 *  UNCERTAINTY) rather than a flat list of up to 29 rows -- matches how the
 *  ruleset itself is organized in packages/rules/lmd_rules.v1.json. */
export function ScanRuleResultsTable({ results }: { results: RuleResultRow[] }) {
  const byCategory = new Map<string, RuleResultRow[]>();
  for (const result of results) {
    const bucket = byCategory.get(result.category) ?? [];
    bucket.push(result);
    byCategory.set(result.category, bucket);
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-28">Rule</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="w-24">Severity</TableHead>
            <TableHead>Message</TableHead>
            <TableHead className="min-w-56">Legal basis</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[...byCategory.entries()].map(([category, rows]) => {
            const vocab = CATEGORY_VOCAB[category as RuleCategory];
            return (
              <Fragment key={category}>
                <TableRow className="bg-surface-subtle hover:bg-surface-subtle">
                  <TableCell colSpan={5} className="py-1.5">
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-fg-muted">
                      {vocab && <vocab.icon className="size-3.5 shrink-0" aria-hidden="true" />}
                      {vocab?.label ?? category}
                    </span>
                  </TableCell>
                </TableRow>
                {rows.map((row) => (
                  <TableRow
                    key={row.rule_id}
                    className={cn(
                      row.severity === "BLOCKER" && "border-l-2 border-l-[var(--sev-blocker)]",
                      row.severity === "MAJOR" && "border-l-2 border-l-[var(--sev-major)]",
                    )}
                  >
                    <TableCell className="font-mono text-xs">{row.rule_id}</TableCell>
                    <TableCell>
                      <RuleStatusBadge status={row.status} size="sm" />
                    </TableCell>
                    <TableCell>
                      <SeverityLabel severity={row.severity} />
                    </TableCell>
                    <TableCell className="max-w-md text-sm">{row.message}</TableCell>
                    <TableCell className="text-xs text-fg-muted">
                      {row.legal_basis}
                      {!row.citation_verified && (
                        <span className="ml-1.5 rounded-sm border border-border px-1 py-0.5 text-2xs">
                          illustrative
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
