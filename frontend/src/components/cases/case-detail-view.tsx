"use client";

import { useState } from "react";
import { FileStack, RotateCw, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingPanel } from "@/components/common/loading-state";
import {
  CaseStatusBadge,
  EvidenceTypeBadge,
} from "@/components/common/status-badge";
import { DataRow, Panel, PanelBody, PanelHeader } from "@/components/common/panel";
import { HashChip } from "@/components/common/hash-chip";
import { useAsync } from "@/hooks/use-async";
import { fetchCase } from "@/lib/api";
import { formatTimestamp, formatValue } from "@/lib/format";
import { isApiError } from "@/lib/errors";
import { REASON_TO_BELIEVE_BASIS } from "@/lib/disclaimers";

import { AuditTimeline } from "./audit-timeline";
import { CaseStatusStepper } from "./case-status-stepper";
import { EvidenceUpload } from "./evidence-upload";
import { ReportGenerationPanel } from "./report-generation-panel";

export function CaseDetailView({ caseId }: { caseId: string }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, error, loading, refetch } = useAsync(
    (signal) => fetchCase(caseId, signal),
    [caseId, refreshKey],
  );

  function handleChanged() {
    setRefreshKey((k) => k + 1);
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Panel className="xl:col-span-2">
          <LoadingPanel />
        </Panel>
        <Panel>
          <LoadingPanel />
        </Panel>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load this case"
        detail={error.message}
        code={isApiError(error) && error.kind === "not_found" ? `case_id: ${caseId}` : undefined}
        action={
          <Button size="sm" variant="outline" onClick={refetch} className="gap-1.5">
            <RotateCw className="size-3.5" aria-hidden="true" />
            Retry
          </Button>
        }
      />
    );
  }

  if (!data) return null;

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <Panel className="xl:col-span-2">
        <PanelHeader
          title="Status"
          description="Advancing to Confirmed violation, Escalated, or Closed requires a recorded reason-to-believe note."
        />
        <PanelBody>
          <div className="mb-4">
            <CaseStatusStepper status={data.status} caseId={caseId} onChanged={handleChanged} />
          </div>
          <dl>
            <DataRow label="Status" value={<CaseStatusBadge status={data.status} />} />
            <DataRow label="Scan ID" value={data.scan_id} mono />
            <DataRow label="Assigned inspector" value={formatValue(data.assigned_inspector_id)} />
            <DataRow label="Created" value={formatTimestamp(data.created_at)} mono />
            <DataRow label="Verified" value={formatTimestamp(data.verified_at)} mono />
            <DataRow label="Closed" value={formatTimestamp(data.closed_at)} mono />
          </dl>
          {data.reason_to_believe_note ? (
            <div className="mt-3 rounded-md border border-border bg-surface-subtle p-3">
              <p className="label-caps mb-1">Reason to believe</p>
              <p className="text-sm">{data.reason_to_believe_note}</p>
              <p className="mt-1.5 text-2xs text-fg-subtle">{REASON_TO_BELIEVE_BASIS}</p>
            </div>
          ) : (
            <div className="mt-3 flex items-start gap-2 rounded-md border border-dashed border-border p-3">
              <ShieldCheck className="mt-0.5 size-3.5 shrink-0 text-fg-subtle" aria-hidden="true" />
              <p className="text-xs text-fg-muted">
                No reason-to-believe note recorded. Required before this case
                can move to Confirmed violation, Escalated, or Closed
                ({REASON_TO_BELIEVE_BASIS}).
              </p>
            </div>
          )}
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader title="Evidence" description="SHA-256 chain, per file." />
        <PanelBody className="p-0">
          {data.evidence.length === 0 ? (
            <EmptyState
              icon={FileStack}
              title="No evidence attached"
              description="Attached photos and certificates will appear here."
              className="py-8"
            />
          ) : (
            <ul>
              {data.evidence.map((item) => (
                <li
                  key={item.evidence_id}
                  className="flex flex-col gap-1.5 border-b border-border p-3 last:border-b-0"
                >
                  <div className="flex items-center justify-between gap-2">
                    <EvidenceTypeBadge evidenceType={item.evidence_type} size="sm" />
                    <span className="text-2xs text-fg-subtle">
                      {formatTimestamp(item.capture_timestamp)}
                    </span>
                  </div>
                  <HashChip hash={item.sha256_hash} label="sha256" />
                  <p className="text-2xs text-fg-subtle">Captured by {item.captured_by}</p>
                </li>
              ))}
            </ul>
          )}
          <div className="border-t border-border p-3">
            <EvidenceUpload caseId={caseId} onUploaded={handleChanged} />
          </div>
        </PanelBody>
      </Panel>

      <Panel className="xl:col-span-2">
        <PanelHeader
          title="Audit log"
          description="Hash-chained record of every case-affecting action."
        />
        <PanelBody className="p-0">
          <AuditTimeline caseId={caseId} refreshKey={refreshKey} />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          title="Violation report"
          description="Section 63 BSA 2023 certificate, generated per case."
        />
        <PanelBody>
          <ReportGenerationPanel caseId={caseId} />
        </PanelBody>
      </Panel>
    </div>
  );
}
