"use client";

import { RotateCw, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/common/error-state";
import { LoadingRows } from "@/components/common/loading-state";
import { Panel, PanelBody, PanelHeader } from "@/components/common/panel";
import { PageHeader } from "@/components/shell/page-header";
import { useAsync } from "@/hooks/use-async";
import { fetchLimitations } from "@/lib/api";
import { NOT_CLAIMS, WHAT_THIS_SYSTEM_IS } from "@/lib/disclaimers";

/**
 * The eight fixed-scope items below are transcribed verbatim from
 * LEGAL_DISCLAIMERS.md and don't depend on a live fetch. The list underneath
 * comes from GET /api/v1/limitations, built server-side from the sentinel
 * files in packages/rules/ (backend/lmd/limitations.py) rather than a
 * hand-maintained duplicate -- it shrinks automatically if a sentinel is
 * ever resolved with real gazette data, with no frontend change required.
 */
export default function LimitationsPage() {
  const { data, error, loading, refetch } = useAsync((signal) => fetchLimitations(signal), []);

  return (
    <div>
      <PageHeader
        eyebrow="Transparency"
        title="Known limitations"
        description={WHAT_THIS_SYSTEM_IS}
      />

      <Panel className="mb-4">
        <PanelHeader
          title="What this system is not"
          description="Stated plainly rather than left for a judge to discover."
        />
        <PanelBody className="p-0">
          <ul>
            {NOT_CLAIMS.map((item) => (
              <li
                key={item.title}
                className="flex items-start gap-3 border-b border-border px-4 py-3 last:border-b-0"
              >
                <TriangleAlert
                  className="mt-0.5 size-4 shrink-0 text-[var(--sev-major)]"
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  <p className="mt-0.5 text-sm text-fg-muted">{item.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          title="Known data gaps"
          description="Built from the sentinel files in packages/rules/ via GET /api/v1/limitations — not a hand-maintained list."
        />
        <PanelBody className="p-0">
          {loading && <LoadingRows rows={4} className="p-4" />}
          {error && (
            <ErrorState
              title="Could not load limitations"
              detail={error.message}
              action={
                <Button size="sm" variant="outline" onClick={refetch} className="gap-1.5">
                  <RotateCw className="size-3.5" aria-hidden="true" />
                  Retry
                </Button>
              }
              className="m-4"
            />
          )}
          {data && (
            <ul>
              {data.limitations.map((item, index) => (
                <li
                  key={`${item.area}-${index}`}
                  className="flex items-start gap-3 border-b border-border px-4 py-3 last:border-b-0"
                >
                  <TriangleAlert
                    className="mt-0.5 size-4 shrink-0 text-fg-subtle"
                    aria-hidden="true"
                  />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="label-caps">{item.area}</p>
                      <span className="rounded-sm border border-border px-1 py-0.5 font-mono text-2xs text-fg-subtle">
                        {item.status}
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm text-fg-muted">{item.detail}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </PanelBody>
      </Panel>
    </div>
  );
}
