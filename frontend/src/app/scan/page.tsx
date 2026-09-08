import { PageHeader } from "@/components/shell/page-header";
import { ScanUploadForm } from "@/components/scan/scan-upload-form";
import { Panel, PanelBody, PanelHeader } from "@/components/common/panel";

export default function NewScanPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Scan"
        title="New scan"
        description="Capture or upload one package photo. It runs through pipeline A (RapidOCR) and, if configured, pipeline B (vision model) before the rule engine evaluates it."
      />
      <Panel>
        <PanelHeader
          title="Package image"
          description="One image per scan — this build evaluates a single inspector-captured photograph, never a batch or a marketplace listing."
        />
        <PanelBody>
          <ScanUploadForm />
        </PanelBody>
      </Panel>
    </div>
  );
}
