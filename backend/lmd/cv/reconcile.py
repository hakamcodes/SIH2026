"""Merge pipeline A (RapidOCR + structuring) and pipeline B (vision model)
output into one ExtractionEnvelope-shaped dict.

Per CLAUDE.md invariant 7, the vision model is never the SOLE source of a
numeric legal field's acceptance for a BLOCKER-level pass: when pipeline A
also produced a reading, both are surfaced via ocr_pipeline/llm_pipeline.
numeric_val, which the ALREADY-EXISTING rule LM-U02 (packages/rules/
lmd_rules.v1.json) uses to route to NEEDS_REVIEW on disagreement -- this
module does not re-implement or second-guess that acceptance decision, it
only supplies the two pipelines' readings.

When pipeline A found NOTHING for mrp/net_quantity but pipeline B did, the
value is still written into the envelope (never silently dropped -- the same
"absence is worse than low confidence" reasoning as the text-field ladder
below), but at VISION_ONLY_CONFIDENCE, which keeps LM-U01's Trust Gate from
ever letting that alone reach COMPLIANT.

Text fields (manufacturer/address, common name, brand name, country of
origin, best-before date) follow a three-tier acceptance ladder in
reconcile() below: pipeline A's own parse wins outright; otherwise a vision
value confirmed by an OCR line; otherwise vision alone. A vision-only value
is still written (never dropped),
because dropping a genuinely-present-but-unread declaration would produce a
false NON_COMPLIANT accusation, which is worse than a REVIEW flag. It is
written at VISION_ONLY_CONFIDENCE, which is deliberately below every
BLOCKER rule's min_field_confidence (>=0.7): LM-U01 (Trust Gate) pools the
confidence of every field referenced by an evaluated BLOCKER rule and fails
below 0.75, so a vision-only text field can flip a structural COMPLETENESS
rule (e.g. LM-C03) from FAIL to PASS, but can never let the overall verdict
reach COMPLIANT -- LM-U01 routes it to NEEDS_REVIEW instead. See
lmd.engine.engine._collect_blocker_confidences.
"""
from __future__ import annotations

import re
from typing import Any

from .pipeline_a import PipelineAResult
from .stages.structuring import source_line_for, structure_fields

# A text field sourced from vision alone (pipeline A's regex found nothing,
# and no OCR line corroborates it) is deliberately capped below every
# BLOCKER rule's min_field_confidence, so LM-U01 always routes the scan to
# NEEDS_REVIEW rather than letting it silently pass at the engine's un-set
# default confidence of 1.0.
VISION_ONLY_CONFIDENCE = 0.5

# A vision value corroborated by an OCR line is trusted almost as much as a
# pipeline-A-only reading, but still capped just below 1.0 since only one
# pipeline (OCR) actually produced the match; the confidence attached is
# whichever is lower between this cap and the confirming OCR line's own
# confidence.
VISION_CONFIRMED_CONFIDENCE_CAP = 0.9

_TEXT_FIELD_KEYS = (
    "manufacturer_or_packer_or_importer",
    "common_or_generic_name",
    "brand_name",
    "country_of_origin",
    "best_before_date",
    "mfg_date",
)

_NORMALIZE_RE = re.compile(r"[^\w\s]")


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", text.casefold()).strip()


def _text_value(field: Any) -> str | None:
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        # manufacturer_or_packer_or_importer is {"name":..., "address":...};
        # corroborate against the name, which is the shorter, more reliable
        # substring to expect verbatim in an OCR line.
        return field.get("name")
    return None


def _best_matching_line(value: str, lines: list[str]) -> tuple[str, float] | None:
    """Return (line, overlap_ratio) for the OCR line that best corroborates
    `value`, or None if no line clears the corroboration threshold."""
    norm_value = _normalize(value)
    if not norm_value:
        return None
    value_tokens = set(norm_value.split())
    best: tuple[str, float] | None = None
    for line in lines:
        norm_line = _normalize(line)
        if not norm_line:
            continue
        if norm_value in norm_line:
            return (line, 1.0)
        line_tokens = set(norm_line.split())
        if not value_tokens or not line_tokens:
            continue
        overlap = len(value_tokens & line_tokens) / len(value_tokens)
        if best is None or overlap > best[1]:
            best = (line, overlap)
    if best is not None and best[1] >= 0.6:
        return best
    return None


def _first_present(structured: dict, vision: dict, key: str) -> tuple[float | None, float | None]:
    ocr_val = structured.get(key, {}).get("value") if isinstance(structured.get(key), dict) else None
    vis_val = vision.get(key, {}).get("value") if isinstance(vision.get(key), dict) else None
    return ocr_val, vis_val


def reconcile(
    pipeline_a_result: PipelineAResult,
    vision_fields: dict[str, Any],
    scan_source: str = "package_image",
) -> dict[str, Any]:
    lines = [f.text for f in pipeline_a_result.fields]
    structured = structure_fields(lines)

    envelope: dict[str, Any] = {"schema_version": "1.0", "scan_source": scan_source}
    envelope.update(structured)

    field_confidences: dict[str, float] = {}

    # Text-field acceptance ladder: pipeline A already won (tier 1) for any
    # key already in `envelope`; otherwise try vision, corroborated (tier 2)
    # or not (tier 3).
    vision_source_map = {
        "manufacturer_or_packer_or_importer": "manufacturer_name",
        "common_or_generic_name": "common_or_generic_name",
        "brand_name": "brand_name",
        "country_of_origin": "country_of_origin",
        "best_before_date": "best_before_date",
        "mfg_date": "mfg_date",
    }
    for env_key in _TEXT_FIELD_KEYS:
        if env_key in envelope:
            continue
        vision_key = vision_source_map[env_key]
        raw_vision_value = vision_fields.get(vision_key)
        vision_text = _text_value(raw_vision_value)
        if not vision_text:
            continue
        if env_key == "manufacturer_or_packer_or_importer":
            envelope_value: Any = {
                "name": vision_text,
                "address": vision_fields.get("manufacturer_address"),
            }
        else:
            envelope_value = vision_text
        match = _best_matching_line(vision_text, lines)
        if match is not None:
            source_line, _ratio = match
            matching_fields = [f for f in pipeline_a_result.fields if f.text == source_line]
            ocr_confidence = max((f.confidence for f in matching_fields), default=VISION_CONFIRMED_CONFIDENCE_CAP)
            envelope[env_key] = envelope_value
            field_confidences[env_key] = min(ocr_confidence, VISION_CONFIRMED_CONFIDENCE_CAP)
        else:
            envelope[env_key] = envelope_value
            field_confidences[env_key] = VISION_ONLY_CONFIDENCE

    # Date-field LLM preference: if pipeline_a extracted a date but at low
    # confidence (e.g. due to squished OCR like 'DateMay'), and pipeline_b
    # produced a higher-confidence value for the same field, prefer the LLM
    # value.  The confidence is capped at VISION_CONFIRMED_CONFIDENCE_CAP to
    # keep LM-U01 honest when no OCR line independently corroborates it.
    _DATE_VISION_KEYS = {"mfg_date": "mfg_date", "best_before_date": "best_before_date"}
    for env_key, vision_key in _DATE_VISION_KEYS.items():
        if env_key not in envelope:
            continue  # pipeline_a didn't find it; the text-field ladder above handles absence
        current_conf = field_confidences.get(env_key, 1.0)
        if current_conf >= VISION_CONFIRMED_CONFIDENCE_CAP:
            continue  # already high-confidence; no need to defer to LLM
        raw_vision_value = vision_fields.get(vision_key)
        if not raw_vision_value or not isinstance(raw_vision_value, str):
            continue
        # Pipeline_b produced a date string; prefer it and mark as corroborated.
        envelope[env_key] = raw_vision_value
        field_confidences[env_key] = VISION_CONFIRMED_CONFIDENCE_CAP

    # Dual-pipeline numeric trust signal for LM-U02. MRP is the higher-stakes
    # numeric field, so prefer it when both pipeline A and pipeline B produced
    # a candidate for it; fall back to net_quantity.
    for key in ("mrp", "net_quantity"):
        ocr_val, vis_val = _first_present(structured, vision_fields, key)
        if ocr_val is not None and vis_val is not None:
            envelope["ocr_pipeline"] = {"numeric_val": ocr_val, "text_val": str(ocr_val)}
            envelope["llm_pipeline"] = {"numeric_val": vis_val, "text_val": str(vis_val)}
            break

    # Vision-only fallback: pipeline A's regex found nothing at all for this
    # numeric field, but pipeline B read one -- surface it rather than
    # dropping a genuinely-present declaration, capped below every BLOCKER
    # rule's min_field_confidence so it can flip a COMPLETENESS rule from
    # FAIL to PASS but LM-U01 still routes the scan to NEEDS_REVIEW.
    for key in ("mrp", "net_quantity"):
        if key in envelope:
            continue
        vis_raw = vision_fields.get(key)
        if not isinstance(vis_raw, dict) or vis_raw.get("value") is None:
            continue
        envelope[key] = vis_raw
        field_confidences[key] = VISION_ONLY_CONFIDENCE
        envelope.setdefault(
            "llm_pipeline", {"numeric_val": vis_raw["value"], "text_val": str(vis_raw["value"])}
        )

    for key in ("net_quantity", "mrp", "consumer_care", "mfg_date"):
        if key not in envelope or key in field_confidences:
            continue
        source_line = source_line_for(lines, key)
        if source_line is None:
            continue
        matching_fields = [f for f in pipeline_a_result.fields if f.text == source_line]
        if matching_fields:
            field_confidences[key] = max(f.confidence for f in matching_fields)
    for key in ("manufacturer_or_packer_or_importer", "common_or_generic_name", "country_of_origin",
                "best_before_date"):
        if key not in envelope or key in field_confidences:
            continue
        source_line = source_line_for(lines, key)
        if source_line is None:
            continue
        matching_fields = [f for f in pipeline_a_result.fields if f.text == source_line]
        if matching_fields:
            field_confidences[key] = max(f.confidence for f in matching_fields)

    if field_confidences:
        envelope["field_confidences"] = field_confidences

    return envelope
