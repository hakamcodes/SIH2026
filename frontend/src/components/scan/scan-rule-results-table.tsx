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
  let rowIndex = 0;

  return (
    <div className="overflow-x-auto">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead className="w-[10%] min-w-24">Rule</TableHead>
            <TableHead className="w-[13%] min-w-28">Status</TableHead>
            <TableHead className="w-[11%] min-w-24">Severity</TableHead>
            <TableHead className="w-[38%]">Message</TableHead>
            <TableHead className="w-[28%]">Legal basis</TableHead>
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
                {rows.map((row) => {
                  const stagger = rowIndex++;
                  return (
                  <TableRow
                    key={row.rule_id}
                    style={{ "--stagger": stagger } as React.CSSProperties}
                    className={cn(
                      "stagger-item align-top transition-[color,background-color,border-color,box-shadow,transform] duration-[var(--dur-fast)] hover:-translate-y-px hover:shadow-sm",
                      row.severity === "BLOCKER" && "border-l-2 border-l-[var(--sev-blocker)] bg-[var(--verdict-non-compliant-bg)]/30",
                      row.severity === "MAJOR" && "border-l-2 border-l-[var(--sev-major)] bg-[var(--verdict-needs-review-bg)]/30",
                    )}
                  >
                    <TableCell className="whitespace-normal break-words font-mono text-xs">
                      {row.rule_id}
                    </TableCell>
                    <TableCell className="whitespace-normal break-words">
                      <RuleStatusBadge status={row.status} size="sm" />
                    </TableCell>
                    <TableCell className="whitespace-normal break-words">
                      <SeverityLabel severity={row.severity} />
                    </TableCell>
                    <TableCell className="whitespace-normal break-words text-sm">
                      {row.message}
                    </TableCell>
                    <TableCell className="whitespace-normal break-words text-xs text-fg-muted">
                      {row.legal_basis}
                      {!row.citation_verified && (
                        <span className="ml-1.5 inline-block rounded-sm border border-border px-1 py-0.5 text-2xs">
                          illustrative
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                  );
                })}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
