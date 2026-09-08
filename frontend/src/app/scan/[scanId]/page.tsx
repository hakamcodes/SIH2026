import { PageHeader } from "@/components/shell/page-header";
import { ScanDetailView } from "@/components/scan/scan-detail-view";

export default async function ScanReviewPage({
  params,
}: {
  params: Promise<{ scanId: string }>;
}) {
  const { scanId } = await params;

  return (
    <div>
      <PageHeader
        title="Scan review"
        breadcrumbs={[{ label: "New scan", href: "/scan" }, { label: "Review" }]}
        description="Extraction, confidence and per-rule reasoning for one scan."
        meta={
          <span className="rounded-sm border border-border bg-surface-subtle px-1.5 py-0.5 font-mono text-2xs text-fg-muted">
            {scanId}
          </span>
        }
      />
      <ScanDetailView scanId={scanId} />
    </div>
  );
}
