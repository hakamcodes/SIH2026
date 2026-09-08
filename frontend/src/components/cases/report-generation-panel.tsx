"use client";

import { useState } from "react";
import { Download, FileOutput } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorNotice } from "@/components/common/error-state";
import { HashChip } from "@/components/common/hash-chip";
import { useInspector } from "@/components/shell/inspector-provider";
import { generateReport, reportDownloadPath } from "@/lib/api";
import { describeUnknownError } from "@/lib/errors";
import type { ReportGenerateResponse } from "@/lib/types";

import { CertificateCard } from "./certificate-card";

/**
 * Idempotent-per-case on the backend (backend/lmd/api/reports.py): each
 * generation overwrites the stored PDF and mints a fresh certificate with a
 * new timestamp and hash, so "Generate" is safe to press again but is
 * explicitly NOT a no-op -- the resulting document_sha256 changes each time.
 */
export function ReportGenerationPanel({ caseId }: { caseId: string }) {
  const { inspector } = useInspector();
  const [result, setResult] = useState<ReportGenerateResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    if (!inspector) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await generateReport(caseId, inspector.inspectorId);
      setResult(response);
    } catch (err) {
      setError(describeUnknownError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        size="sm"
        onClick={handleGenerate}
        disabled={!inspector || submitting}
        className="w-full gap-1.5"
      >
        <FileOutput className="size-3.5" aria-hidden="true" />
        {submitting ? "Generating…" : result ? "Regenerate report" : "Generate report"}
      </Button>
      {!inspector && (
        <p className="text-2xs text-fg-subtle">Sign in with an inspector identity to generate a report.</p>
      )}
      {error && <ErrorNotice>{error}</ErrorNotice>}

      {result && (
        <>
          <HashChip hash={result.document_sha256} label="document sha256" />
          <CertificateCard certificate={result.certificate} />
          <Button asChild variant="outline" size="sm" className="gap-1.5">
            <a href={reportDownloadPath(caseId)} download={`${caseId}.pdf`}>
              <Download className="size-3.5" aria-hidden="true" />
              Download PDF
            </a>
          </Button>
        </>
      )}
    </div>
  );
}
