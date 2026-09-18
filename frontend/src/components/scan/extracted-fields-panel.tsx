import { DataRow } from "@/components/common/panel";
import { formatQuantity, formatRupees, formatValue } from "@/lib/format";
import type { ExtractionEnvelope } from "@/lib/types";
import { CONFIDENCE_VOCAB, confidenceBand } from "@/lib/vocab";
import { cn } from "@/lib/utils";

/** field_confidences is keyed by TOP-LEVEL field name only (engine.py does
 *  `path.split(".")[0]`), so "net_quantity" covers both value and unit. */
function ConfidenceRing({
  field,
  confidences,
}: {
  field: string;
  confidences: Record<string, number> | null | undefined;
}) {
  const value = confidences?.[field];
  if (value === undefined) return null;

  const band = confidenceBand(value);
  const vocab = CONFIDENCE_VOCAB[band];
  const pct = Math.round(value * 100);

  // SVG circular arc parameters
  const r = 9; // radius
  const cx = 12;
  const cy = 12;
  const circumference = 2 * Math.PI * r;
  const dashOffset = circumference * (1 - value);

  return (
    <span
      className="ml-1.5 inline-flex items-center gap-1 align-middle"
      title={`Confidence: ${pct}%`}
    >
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        aria-hidden="true"
        className="shrink-0"
      >
        {/* Background track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth="2.5"
        />
        {/* Filled arc */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={vocab.stroke}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform="rotate(-90 12 12)"
        />

      </svg>
      <span className={cn("font-mono text-2xs tabular-nums", vocab.text)}>{pct}%</span>
    </span>
  );
}

export function ExtractedFieldsPanel({ envelope }: { envelope: ExtractionEnvelope }) {
  const confidences = envelope.field_confidences;
  const commodity = envelope.commodity;

  return (
    <dl>
      <DataRow
        label="Net quantity"
        value={
          <>
            {formatQuantity(envelope.net_quantity?.value, envelope.net_quantity?.unit)}
            <ConfidenceRing field="net_quantity" confidences={confidences} />
          </>
        }
        mono
      />
      <DataRow
        label="MRP"
        value={
          <>
            {formatRupees(envelope.mrp?.value)}
            <ConfidenceRing field="mrp" confidences={confidences} />
          </>
        }
        mono
      />
      <DataRow label="Common / generic name" value={formatValue(envelope.common_or_generic_name)} />
      <DataRow label="Brand" value={formatValue(envelope.brand_name)} />
      <DataRow
        label="Manufacturer"
        value={formatValue(envelope.manufacturer_or_packer_or_importer?.name)}
      />
      <DataRow
        label="Address"
        value={formatValue(envelope.manufacturer_or_packer_or_importer?.address)}
      />
      <DataRow label="Country of origin" value={formatValue(envelope.country_of_origin)} />
      <DataRow label="Mfg / pack date" value={formatValue(envelope.mfg_date)} mono />
      <DataRow label="Best before" value={formatValue(envelope.best_before_date)} mono />
      <DataRow label="Consumer care phone" value={formatValue(envelope.consumer_care?.phone)} mono />
      <DataRow label="Consumer care email" value={formatValue(envelope.consumer_care?.email)} mono />
      <DataRow label="Commodity category" value={formatValue(commodity?.category)} />
      <DataRow label="Imported" value={formatValue(commodity?.is_imported)} />
      <DataRow label="Exempt" value={formatValue(commodity?.is_exempt)} />
    </dl>
  );
}
