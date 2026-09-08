"use client";

import { useState } from "react";
import { ClipboardList, Download, ImageOff, ListChecks, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingPanel } from "@/components/common/loading-state";
import { Panel, PanelBody, PanelHeader } from "@/components/common/panel";
import { useAsync } from "@/hooks/use-async";
import { fetchScan } from "@/lib/api";
import { isApiError } from "@/lib/errors";
import { CONFIDENCE_VOCAB, confidenceBand } from "@/lib/vocab";

import { AnnotatedCanvas } from "./annotated-canvas";
import { BoxDetailPanel } from "./box-detail-panel";
import { DisagreementBanner } from "./disagreement-banner";
import { ExtractedFieldsPanel } from "./extracted-fields-panel";
import { ScanRuleResultsTable } from "./scan-rule-results-table";
import { VerdictBanner } from "./verdict-banner";

/**
 * Renders the real GET /api/v1/scans/{id} response: the interactive
 * AnnotatedCanvas (raw image + hoverable/focusable OCR boxes, colour-coded by
 * confidence, never implying a box caused a rule outcome), the extracted
 * fields with per-field confidence, the pipeline A/B disagreement state, and
 * every applicable rule with its legal basis.
 */
export function ScanDetailView({ scanId }: { scanId: string }) {
  const { data, error, loading, refetch } = useAsync(
    (signal) => fetchScan(scanId, signal),
    [scanId],
  );
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [pinnedIndex, setPinnedIndex] = useState<number | null>(null);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Panel className="xl:col-span-3">
          <LoadingPanel />
        </Panel>
        <Panel className="xl:col-span-2">
          <LoadingPanel />
        </Panel>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Could not load this scan"
        detail={error.message}
        code={isApiError(error) && error.kind === "not_found" ? `scan_id: ${scanId}` : undefined}
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

  const highConfidence = data.ocr_boxes.filter((b) => confidenceBand(b.confidence) === "high").length;
  const medConfidence = data.ocr_boxes.filter((b) => confidenceBand(b.confidence) === "medium").length;
  const lowConfidence = data.ocr_boxes.filter((b) => confidenceBand(b.confidence) === "low").length;
  const activeIndex = pinnedIndex ?? hoverIndex;
  const activeBox = activeIndex !== null ? (data.ocr_boxes[activeIndex] ?? null) : null;

  return (
    <div>
      <VerdictBanner verdict={data.overall_verdict} />
      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-5">
      <Panel className="xl:col-span-3">
        <PanelHeader
          title="Annotated image"
          description="Hover or click a box for its OCR evidence. Colour reflects extraction confidence only, never rule outcome."
        />
        <PanelBody className="p-0">
          {data.ocr_boxes.length === 0 ? (
            <EmptyState
              icon={ImageOff}
              title="No text detected"
              description="Pipeline A returned zero OCR boxes for this image."
              className="aspect-4/3"
            />
          ) : (
            <>
              <AnnotatedCanvas
                scanId={scanId}
                boxes={data.ocr_boxes}
                hoverIndex={hoverIndex}
                onHover={setHoverIndex}
                pinnedIndex={pinnedIndex}
                onPin={setPinnedIndex}
              />
              <div className="border-t border-border p-3">
                <BoxDetailPanel box={activeBox} />
              </div>
              <div className="flex flex-wrap items-center gap-3 border-t border-border px-4 py-2.5 text-xs text-fg-muted">
                <span className={CONFIDENCE_VOCAB.high.text}>{highConfidence} high</span>
                <span className={CONFIDENCE_VOCAB.medium.text}>{medConfidence} medium</span>
                <span className={CONFIDENCE_VOCAB.low.text}>{lowConfidence} low</span>
                <span className="text-fg-subtle">{data.ocr_boxes.length} boxes detected</span>
                <a
                  href={`/api/lmd/scans/${scanId}/overlay`}
                  download
                  className="ml-auto inline-flex items-center gap-1 text-link hover:underline"
                >
                  <Download className="size-3" aria-hidden="true" />
                  Download annotated overlay
                </a>
              </div>
            </>
          )}
        </PanelBody>
      </Panel>

      <Panel className="xl:sticky xl:top-[calc(var(--topbar-h)+1rem)] xl:col-span-2 xl:self-start">
        <PanelHeader
          title="Extracted fields"
          description="Net quantity, MRP, dates, manufacturer, consumer care."
        />
        <PanelBody>
          {data.extraction_envelope ? (
            <>
              <ExtractedFieldsPanel envelope={data.extraction_envelope} />
              <div className="mt-3">
                <DisagreementBanner
                  ocrPipeline={data.extraction_envelope.ocr_pipeline}
                  llmPipeline={data.extraction_envelope.llm_pipeline}
                />
              </div>
            </>
          ) : (
            <EmptyState icon={ClipboardList} title="No extraction recorded" />
          )}
        </PanelBody>
      </Panel>

      <Panel className="xl:col-span-5">
        <PanelHeader
          title="Rule results"
          description="Every applicable rule, grouped by category, with legal basis and citation status."
        />
        <PanelBody className="p-0">
          {data.rule_results.length === 0 ? (
            <EmptyState icon={ListChecks} title="No rule results recorded" />
          ) : (
            <ScanRuleResultsTable results={data.rule_results} />
          )}
        </PanelBody>
      </Panel>
      </div>
    </div>
  );
}
