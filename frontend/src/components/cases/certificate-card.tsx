import { Stamp } from "lucide-react";

import { DataRow } from "@/components/common/panel";
import { HashChip } from "@/components/common/hash-chip";
import { formatTimestamp } from "@/lib/format";
import type { Bsa63Certificate } from "@/lib/types";

/**
 * Section 63, Bharatiya Sakshya Adhiniyam 2023 certificate fields. Renders
 * the certificate's own `disclaimer` string verbatim rather than a
 * paraphrase -- the certifiable/court-admissible distinction (CLAUDE.md
 * section 4.2) must come from the record itself, not from UI copy that could
 * drift out of sync with it.
 */
export function CertificateCard({ certificate }: { certificate: Bsa63Certificate }) {
  return (
    <div className="rounded-md border border-border bg-surface-subtle p-3">
      <div className="mb-2 flex items-center gap-1.5">
        <Stamp className="size-3.5 text-fg-subtle" aria-hidden="true" />
        <p className="label-caps">Section 63 BSA 2023 certificate</p>
      </div>
      <dl>
        <DataRow label="Certificate ID" value={certificate.certificate_id} mono />
        <DataRow label="Device" value={certificate.device_identification} />
        <DataRow label="Process" value={certificate.production_process_description} />
        <DataRow label="Certifying officer" value={certificate.certifying_officer} />
        <DataRow label="Generated" value={formatTimestamp(certificate.generated_at)} mono />
      </dl>
      <div className="mt-2 flex flex-col gap-1.5">
        <HashChip hash={certificate.record_sha256} label="record sha256" />
        <HashChip hash={certificate.hmac_signature} label="hmac" />
      </div>
      <p className="mt-2 text-2xs text-fg-subtle">{certificate.disclaimer}</p>
    </div>
  );
}
