"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, RotateCw, ScanLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CounterTile } from "@/components/dashboard/counter-tile";
import { ErrorState } from "@/components/common/error-state";
import { LoadingPanel } from "@/components/common/loading-state";
import { Panel, PanelBody, PanelHeader } from "@/components/common/panel";
import { PageHeader } from "@/components/shell/page-header";
import { useAsync } from "@/hooks/use-async";
import { fetchMetrics } from "@/lib/api";
import { CASE_STATUS_VOCAB, VERDICT_VOCAB } from "@/lib/vocab";
import { cn } from "@/lib/utils";
import type { CaseStatus, Verdict } from "@/lib/types";
import { VERDICTS, CASE_STATUSES } from "@/lib/types";

/**
 * Dashboard: verdict counters, case funnel, top failed rules,
 * top missing declarations, compliance by category, and recent scans.
 * Deliberately the only dashboard in this build (CLAUDE.md section 1).
 */
export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(() => new Date());

  const { data, error, loading } = useAsync(
    (signal) => fetchMetrics(signal),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [refreshKey],
  );

  function doRefresh() {
    setRefreshKey((k) => k + 1);
    setLastRefreshed(new Date());
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="Total scans, verdict distribution, case funnel, and inspection analytics."
        actions={
          <div className="flex items-center gap-2">
            <span className="hidden text-xs text-fg-subtle sm:block">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={doRefresh}
              disabled={loading}
              className="gap-1.5"
            >
              <RotateCw className={cn("size-3.5", loading && "animate-spin")} aria-hidden="true" />
              Refresh
            </Button>
          </div>
        }
      />

      {error && (
        <ErrorState
          title="Could not load metrics"
          detail={error.message}
          action={
            <Button size="sm" variant="outline" onClick={doRefresh} className="gap-1.5">
              <RotateCw className="size-3.5" aria-hidden="true" />
              Retry
            </Button>
          }
        />
      )}

      {/* Scan verdicts */}
      <section>
        <p className="label-caps mb-2">Scans</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <CounterTile
            label="Total scans"
            value={loading ? null : (data?.total_scans ?? 0)}
            icon={ScanLine}
            style={{ "--stagger": 0 } as React.CSSProperties}
          />
          {VERDICTS.map((verdict: Verdict, index) => (
            <CounterTile
              key={verdict}
              label={VERDICT_VOCAB[verdict].label}
              value={loading ? null : (data?.scans_by_verdict[verdict] ?? 0)}
              icon={VERDICT_VOCAB[verdict].icon}
              accentClassName={VERDICT_VOCAB[verdict].className.split(" ")[0]}
              style={{ "--stagger": index + 1 } as React.CSSProperties}
            />
          ))}
        </div>
      </section>

      {/* Case funnel */}
      <section>
        <p className="label-caps mb-2">Cases by status</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {CASE_STATUSES.map((status: CaseStatus, index) => (
            <CounterTile
              key={status}
              label={CASE_STATUS_VOCAB[status].label}
              value={loading ? null : (data?.cases_by_status[status] ?? 0)}
              icon={CASE_STATUS_VOCAB[status].icon}
              accentClassName={CASE_STATUS_VOCAB[status].className.split(" ")[0]}
              style={{ "--stagger": index + 1 } as React.CSSProperties}
            />
          ))}
        </div>
      </section>

      {/* Analytics grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Top failed rules */}
        <Panel>
          <PanelHeader
            title="Most frequently failed rules"
            description="Rules with the highest FAIL count across all scans."
          />
          <PanelBody className="p-0">
            {loading ? (
              <LoadingPanel />
            ) : !data?.top_failed_rules?.length ? (
              <p className="px-4 py-6 text-sm text-fg-muted text-center">No failed rules recorded yet.</p>
            ) : (
              <ol className="divide-y divide-border">
                {data.top_failed_rules.map((item, i) => (
                  <li key={item.rule_id} className="flex items-center gap-3 px-4 py-2.5">
                    <span className="w-5 shrink-0 text-xs text-fg-subtle font-mono">{i + 1}</span>
                    <AlertTriangle className="size-3.5 shrink-0 text-red-600" aria-hidden="true" />
                    <span className="flex-1 font-mono text-xs truncate">{item.rule_id}</span>
                    <span className="shrink-0 text-xs font-semibold tabular-nums text-red-600">
                      {item.fail_count}×
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </PanelBody>
        </Panel>

        {/* Top missing declarations */}
        <Panel>
          <PanelHeader
            title="Most common missing declarations"
            description="Fields most often absent from the extracted label data."
          />
          <PanelBody className="p-0">
            {loading ? (
              <LoadingPanel />
            ) : !data?.top_missing_fields?.length ? (
              <p className="px-4 py-6 text-sm text-fg-muted text-center">No missing fields recorded yet.</p>
            ) : (
              <ol className="divide-y divide-border">
                {data.top_missing_fields.map((item, i) => (
                  <li key={item.field} className="flex items-center gap-3 px-4 py-2.5">
                    <span className="w-5 shrink-0 text-xs text-fg-subtle font-mono">{i + 1}</span>
                    <span className="flex-1 text-xs truncate">{item.field.replaceAll("_", " ")}</span>
                    <span className="shrink-0 text-xs font-semibold tabular-nums text-amber-600">
                      {item.missing_count} scans
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </PanelBody>
        </Panel>

        {/* Compliance by category — with proportion bars */}
        <Panel>
          <PanelHeader
            title="Compliance by category"
            description="Verdict breakdown per commodity category."
          />
          <PanelBody className="p-0">
            {loading ? (
              <LoadingPanel />
            ) : !data?.compliance_by_category || Object.keys(data.compliance_by_category).length === 0 ? (
              <p className="px-4 py-6 text-sm text-fg-muted text-center">No category data yet.</p>
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-2 text-left text-fg-muted font-medium">Category</th>
                    <th className="px-4 py-2 text-right text-green-700 font-medium w-12">Pass</th>
                    <th className="px-4 py-2 text-right text-red-600 font-medium w-12">Fail</th>
                    <th className="px-4 py-2 text-right text-amber-600 font-medium w-16">Review</th>
                    <th className="px-4 py-2 w-24 text-fg-muted font-medium">Split</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {Object.entries(data.compliance_by_category).map(([cat, verdicts]) => {
                    const pass = verdicts.COMPLIANT ?? 0;
                    const fail = verdicts.NON_COMPLIANT ?? 0;
                    const review = verdicts.NEEDS_REVIEW ?? 0;
                    const total = pass + fail + review;
                    return (
                      <tr key={cat}>
                        <td className="px-4 py-2 capitalize">{cat.replaceAll("_", " ")}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-green-700">{pass}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-red-600">{fail}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-amber-600">{review}</td>
                        <td className="px-4 py-2">
                          {total > 0 ? (
                            <div
                              className="flex h-2 w-full overflow-hidden rounded-full bg-border"
                              title={`Pass ${pass}, Fail ${fail}, Review ${review}`}
                              aria-label={`Pass ${pass}, Fail ${fail}, Review ${review}`}
                            >
                              {pass > 0 && (
                                <span
                                  className="h-full bg-green-500"
                                  style={{ width: `${(pass / total) * 100}%` }}
                                />
                              )}
                              {fail > 0 && (
                                <span
                                  className="h-full bg-red-500"
                                  style={{ width: `${(fail / total) * 100}%` }}
                                />
                              )}
                              {review > 0 && (
                                <span
                                  className="h-full bg-amber-400"
                                  style={{ width: `${(review / total) * 100}%` }}
                                />
                              )}
                            </div>
                          ) : (
                            <span className="text-fg-subtle">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              </div>
            )}
          </PanelBody>
        </Panel>

        {/* Recent scans */}
        <Panel>
          <PanelHeader
            title="Recent inspections"
            description="Last 10 scans, newest first."
          />
          <PanelBody className="p-0">
            {loading ? (
              <LoadingPanel />
            ) : !data?.recent_scans?.length ? (
              <p className="px-4 py-6 text-sm text-fg-muted text-center">No scans yet.</p>
            ) : (
              <ol className="divide-y divide-border">
                {data.recent_scans.map((scan) => {
                  const verdict = scan.overall_verdict as Verdict | null;
                  return (
                    <li key={scan.scan_id ?? scan.created_at} className="flex items-center gap-3 px-4 py-2.5">
                      {verdict === "COMPLIANT" && <CheckCircle2 className="size-3.5 shrink-0 text-green-700" aria-hidden="true" />}
                      {verdict === "NON_COMPLIANT" && <AlertTriangle className="size-3.5 shrink-0 text-red-600" aria-hidden="true" />}
                      {(verdict === "NEEDS_REVIEW" || !verdict) && <Clock className="size-3.5 shrink-0 text-amber-600" aria-hidden="true" />}
                      <span className="flex-1 font-mono text-2xs truncate text-fg-muted">
                        {scan.scan_id ?? "—"}
                      </span>
                      <span className="shrink-0 text-xs text-fg-muted">{scan.scan_date ?? "—"}</span>
                      {verdict && (
                        <span className={cn(
                          "shrink-0 rounded-sm px-1 py-0.5 text-2xs font-medium",
                          verdict === "COMPLIANT" && "bg-green-50 text-green-700",
                          verdict === "NON_COMPLIANT" && "bg-red-50 text-red-600",
                          verdict === "NEEDS_REVIEW" && "bg-amber-50 text-amber-600",
                        )}>
                          {verdict === "COMPLIANT" ? "PASS" : verdict === "NON_COMPLIANT" ? "FAIL" : "REVIEW"}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </PanelBody>
        </Panel>

      </div>
    </div>
  );
}
