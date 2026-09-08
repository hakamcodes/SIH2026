"use client";

import { RotateCw, ScanLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CounterTile } from "@/components/dashboard/counter-tile";
import { ErrorState } from "@/components/common/error-state";
import { PageHeader } from "@/components/shell/page-header";
import { useAsync } from "@/hooks/use-async";
import { fetchMetrics } from "@/lib/api";
import { CASE_STATUS_VOCAB, VERDICT_VOCAB } from "@/lib/vocab";
import type { CaseStatus, Verdict } from "@/lib/types";
import { VERDICTS, CASE_STATUSES } from "@/lib/types";

/**
 * The single counters page (CLAUDE.md section 1: "a single counters page is
 * the only dashboard" — no state/district/platform breakdown). GET
 * /api/v1/metrics returns two GROUP BY results that are sparse by
 * construction (a verdict or status with zero rows is simply absent from
 * the map), so every verdict and every case status is zero-filled here
 * before rendering -- a genuine zero and "not loaded yet" must never look
 * identical (CounterTile renders null as "—", a fetched 0 as "0").
 */
export default function DashboardPage() {
  const { data, error, loading, refetch } = useAsync((signal) => fetchMetrics(signal), []);

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="Total scans, verdict distribution, and case funnel. Deliberately the only dashboard in this build."
      />

      {error && (
        <ErrorState
          title="Could not load metrics"
          detail={error.message}
          action={
            <Button size="sm" variant="outline" onClick={refetch} className="gap-1.5">
              <RotateCw className="size-3.5" aria-hidden="true" />
              Retry
            </Button>
          }
          className="mb-6"
        />
      )}

      <div className="mb-6">
        <p className="label-caps mb-2">Scans</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <CounterTile
            label="Total scans"
            value={loading ? null : (data?.total_scans ?? 0)}
            icon={ScanLine}
          />
          {VERDICTS.map((verdict: Verdict) => (
            <CounterTile
              key={verdict}
              label={VERDICT_VOCAB[verdict].label}
              value={loading ? null : (data?.scans_by_verdict[verdict] ?? 0)}
              icon={VERDICT_VOCAB[verdict].icon}
              accentClassName={VERDICT_VOCAB[verdict].className.split(" ")[0]}
            />
          ))}
        </div>
      </div>

      <div>
        <p className="label-caps mb-2">Cases by status</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {CASE_STATUSES.map((status: CaseStatus) => (
            <CounterTile
              key={status}
              label={CASE_STATUS_VOCAB[status].label}
              value={loading ? null : (data?.cases_by_status[status] ?? 0)}
              icon={CASE_STATUS_VOCAB[status].icon}
              accentClassName={CASE_STATUS_VOCAB[status].className.split(" ")[0]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
