"""One-way adapter: research/NotebookLM/product-classification-decision-logic.md's
`image_analysis_parameters` shape -> the canonical nested extraction shape.

Per CLAUDE.md section 6, this exists only so the original research artifact
stays loadable in tests -- it is never the shape the rule engine or the
extraction contract are authored against.

This adapter is intentionally lossy in one direction: the legacy shape
records several fields as boolean *presence* flags rather than actual
values (`special_declarations.best_before_present`, `mrp_price.format_compliant`,
`special_declarations.dimensions_declared`, `manufacturer_info_present`). A
boolean cannot be turned into the real declared text/date/dimensions without
inventing data, so those flags are dropped rather than faked -- per CLAUDE.md
invariant #10 (never fabricate a value). Only fields carrying an actual
extracted value are mapped.
"""
from __future__ import annotations

from typing import Any


def from_legacy(legacy: dict[str, Any]) -> dict[str, Any]:
    params = legacy.get("image_analysis_parameters", {})
    out: dict[str, Any] = {}

    commodity: dict[str, Any] = {}
    if "product_category" in params:
        commodity["category"] = params["product_category"]
    if "commodity_subtype" in params:
        commodity["subtype"] = params["commodity_subtype"]
    if "is_imported" in params:
        commodity["is_imported"] = params["is_imported"]
    exemption_flags = params.get("exemption_flags")
    if isinstance(exemption_flags, dict) and exemption_flags:
        commodity["is_exempt"] = any(exemption_flags.values())
    if commodity:
        out["commodity"] = commodity

    net_quantity_src = params.get("net_quantity", {})
    net_quantity: dict[str, Any] = {}
    if "declared_value" in net_quantity_src:
        net_quantity["value"] = net_quantity_src["declared_value"]
    if "declared_unit" in net_quantity_src:
        net_quantity["unit"] = net_quantity_src["declared_unit"]
    if net_quantity:
        out["net_quantity"] = net_quantity

    mrp_src = params.get("mrp_price", {})
    mrp: dict[str, Any] = {}
    if "value" in mrp_src:
        mrp["value"] = mrp_src["value"]
    if "currency" in mrp_src:
        mrp["currency_marker"] = mrp_src["currency"]
    if mrp:
        out["mrp"] = mrp

    packing_date = params.get("packing_date", {})
    if packing_date.get("month") and packing_date.get("year"):
        # Month/year precision only -- no day was ever extracted, so this
        # cannot become a full mfg_date without inventing a day-of-month.
        out["mfg_or_pack_or_import_month_year"] = f"{packing_date['year']:04d}-{packing_date['month']:02d}"

    special = params.get("special_declarations", {})
    if special.get("country_of_origin"):
        out["country_of_origin"] = special["country_of_origin"]

    return out
