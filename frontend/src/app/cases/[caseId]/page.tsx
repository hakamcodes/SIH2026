import { CaseDetailView } from "@/components/cases/case-detail-view";
import { PageHeader } from "@/components/shell/page-header";

export default async function CaseReviewPage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;

  return (
    <div>
      <PageHeader
        title="Case review"
        breadcrumbs={[{ label: "Cases", href: "/cases" }, { label: "Review" }]}
        description="Review, evidence, and the reason-to-believe gate."
        actions={
          <span className="rounded-sm border border-border bg-surface-subtle px-1.5 py-0.5 font-mono text-2xs text-fg-muted">
            {caseId}
          </span>
        }
      />
      <CaseDetailView caseId={caseId} />
    </div>
  );
}
