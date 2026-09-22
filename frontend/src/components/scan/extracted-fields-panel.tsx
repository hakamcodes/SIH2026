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

const PANEL_BADGE_LABEL: Record<string, string> = {
  front: "Front",
  back: "Back",
  side: "Side",
  other: "Other",
};

/** Small tag naming which uploaded panel (front/back/side/other) won the
 *  merge for this field, on a multi-panel scan -- makes the field-level
 *  merge in backend/lmd/api/scan_multi.py's _merge_envelopes visible rather
 *  than implicit. Renders nothing on a single-image scan. */
function PanelSourceBadge({
  field,
  panelSources,
}: {
  field: string;
  panelSources: Record<string, string> | null | undefined;
}) {
  const panel = panelSources?.[field];
  if (!panel) return null;
  return (
    <span
      className="ml-1.5 inline-flex items-center rounded-sm border border-border bg-surface-subtle px-1 py-0.5 align-middle font-mono text-2xs text-fg-muted"
      title={`Value taken from the ${panel} panel`}
    >
      {PANEL_BADGE_LABEL[panel] ?? panel}
    </span>
  );
}

export function ExtractedFieldsPanel({
  envelope,
  panelSources,
}: {
  envelope: ExtractionEnvelope;
  panelSources?: Record<string, string>;
}) {
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
            <PanelSourceBadge field="net_quantity" panelSources={panelSources} />
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
            <PanelSourceBadge field="mrp" panelSources={panelSources} />
          </>
        }
        mono
      />
      <DataRow
        label="Common / generic name"
        value={<>{formatValue(envelope.common_or_generic_name)}<PanelSourceBadge field="common_or_generic_name" panelSources={panelSources} /></>}
      />
      <DataRow
        label="Brand"
        value={<>{formatValue(envelope.brand_name)}<PanelSourceBadge field="brand_name" panelSources={panelSources} /></>}
      />
      <DataRow
        label="Manufacturer"
        value={
          <>
            {formatValue(envelope.manufacturer_or_packer_or_importer?.name)}
            <PanelSourceBadge field="manufacturer_or_packer_or_importer" panelSources={panelSources} />
          </>
        }
      />
      <DataRow
        label="Address"
        value={formatValue(envelope.manufacturer_or_packer_or_importer?.address)}
      />
      <DataRow
        label="Country of origin"
        value={<>{formatValue(envelope.country_of_origin)}<PanelSourceBadge field="country_of_origin" panelSources={panelSources} /></>}
      />
      <DataRow
        label="Mfg / pack date"
        value={<>{formatValue(envelope.mfg_date)}<PanelSourceBadge field="mfg_date" panelSources={panelSources} /></>}
        mono
      />
      <DataRow
        label="Best before"
        value={<>{formatValue(envelope.best_before_date)}<PanelSourceBadge field="best_before_date" panelSources={panelSources} /></>}
        mono
      />
      <DataRow
        label="Consumer care phone"
        value={<>{formatValue(envelope.consumer_care?.phone)}<PanelSourceBadge field="consumer_care" panelSources={panelSources} /></>}
        mono
      />
      <DataRow label="Consumer care email" value={formatValue(envelope.consumer_care?.email)} mono />
      <DataRow label="Commodity category" value={formatValue(commodity?.category)} />
      <DataRow label="Imported" value={formatValue(commodity?.is_imported)} />
      <DataRow label="Exempt" value={formatValue(commodity?.is_exempt)} />
    </dl>
  );
}
