"""Central source of truth for known gaps and roadmap-only capabilities.

Reads the sentinel files that already exist in packages/rules/ rather than
hardcoding a parallel list, so a limitation disappears from this surface
only when its underlying sentinel is actually resolved with real gazette
data (CLAUDE.md invariant 10: never fabricate a legal citation or
threshold; section 4.2: "state this plainly rather than letting a judge
discover it"). Consumed by lmd.api.limitations (the API surface) and
lmd.evidence.report_pdf (the printed report).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RULES_DIR = _REPO_ROOT / "packages" / "rules"

# Fixed by physics or by deliberate scope decision, not by a missing data
# file -- CLAUDE.md section 11's "what we must not say" list, restated as
# what the product says about itself.
_FIXED_SCOPE_LIMITATIONS = [
    "Actual net weight/volume cannot be verified from a photograph -- the system checks declaration "
    "consistency only, never a physical weighment or First Schedule maximum-permissible-error check.",
    "No geometric/cylindrical dewarp -- curved surfaces (jars, bottles, pouches) are read as-is; "
    "measured recovery on the curved-jar test image is effectively zero.",
    "Dot-matrix batch/expiry stamps are not reliably read by classical OCR; measured recovery on the "
    "dot-matrix test image is effectively zero.",
    "eMaap registration lookup and cross-state repeat-offender tracking are proposed architecture only "
    "-- eMaap has no public API and enforcement is a State subject. Not live.",
    "No web crawler / marketplace scraping, no automated notice dispatch, no multi-state case "
    "federation -- explicitly out of scope for this prototype (roadmap slide only).",
    "Font-size compliance under Rule 7 is never asserted from an arbitrary photograph with no "
    "calibration reference in frame; absolute millimetre measurement requires a detected ID-1 card.",
    "Hindi/Devanagari OCR accuracy is not claimed against a real photograph -- only a synthetic "
    "render has been tested to date.",
    "A generated PDF report is certifiable (BSA 2023 Section 63 certificate attached) but not "
    "automatically court-admissible.",
]

_RESERVED_UNWRITTEN_RULE_IDS = ["LM-C10", "LM-F08", "LM-F09"]


def _load_json(filename: str) -> dict[str, Any]:
    path = _RULES_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_known_limitations() -> dict[str, Any]:
    """Build the limitations surface entirely from sentinel files already
    committed in packages/rules/ -- adding real gazette data there removes
    the corresponding limitation here with no code change."""
    second_schedule = _load_json("second_schedule_sizes.json")
    font_tables = _load_json("rule7_font_tables.json")
    citations = _load_json("citations.json")

    limitations: list[dict[str, str]] = []

    if second_schedule.get("_status") == "PARTIAL_SOURCE":
        encoded = sorted(second_schedule.get("sizes_g", {}).keys())
        limitations.append(
            {
                "area": "second_schedule_sizes",
                "status": second_schedule["_status"],
                "detail": (
                    f"Only {', '.join(encoded)} standard-size list(s) are gazette-sourced and enforced "
                    "(LM-M04a/LM-M04b). Other Second Schedule categories (bread, milk powder, soaps, "
                    "detergent, paints, cement, rice, edible oil, bottled water) are not encoded pending "
                    "the actual gazetted text; a paraphrased secondary source is not sufficient to "
                    "encode a BLOCKER-severity size boundary."
                ),
            }
        )

    if font_tables.get("status") == "UNVERIFIED_SOURCE":
        limitations.append(
            {
                "area": "rule7_font_tables",
                "status": font_tables["status"],
                "detail": (
                    "Rule 7 Tables I/II minimum character-height thresholds (mm by pack size) are not "
                    "sourced anywhere in this build. Any rule needing them returns NOT_EVALUABLE."
                ),
            }
        )

    limitations.append(
        {
            "area": "reserved_rule_ids",
            "status": "UNWRITTEN",
            "detail": (
                f"{', '.join(_RESERVED_UNWRITTEN_RULE_IDS)} are reserved (Rule 6(5) multi-pack, "
                "Rule 6(7) GM-food declaration, cosmetic green/brown dot) but not authored -- no "
                "concrete DSL condition spec exists yet without inventing legal logic."
            ),
        }
    )

    do_not_cite = citations.get("do_not_cite", [])
    if do_not_cite:
        limitations.append(
            {
                "area": "citations_blocklist",
                "status": "EXCLUDED",
                "detail": (
                    "The following citations were identified as simulated/fabricated during research "
                    "red-teaming and are never surfaced by this system: "
                    + "; ".join(c["citation"] for c in do_not_cite)
                ),
            }
        )

    for detail in _FIXED_SCOPE_LIMITATIONS:
        limitations.append({"area": "scope", "status": "BY_DESIGN", "detail": detail})

    return {"limitations": limitations}
