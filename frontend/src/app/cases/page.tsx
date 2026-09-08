import Link from "next/link";

import { Button } from "@/components/ui/button";
import { CaseQueueTable } from "@/components/cases/case-queue-table";
import { Panel } from "@/components/common/panel";
import { PageHeader } from "@/components/shell/page-header";

export default function CasesPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Case management"
        title="Cases"
        description="Cases opened from a scan, moving through inspector review under the reason-to-believe gate."
        actions={
          <Button asChild size="sm">
            <Link href="/scan">Open a case from a scan</Link>
          </Button>
        }
      />
      <Panel>
        <CaseQueueTable />
      </Panel>
    </div>
  );
}
