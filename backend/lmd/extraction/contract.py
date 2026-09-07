"""The canonical extraction shape. Per CLAUDE.md section 6: the nested
rules-JSON shape is canonical because the 29 rule conditions already
reference net_quantity.value, mrp.value, commodity.is_exempt, etc. Every
other field-name set in the research is a one-way input adapter into this.

All fields are Optional -- a field that a CV/OCR pipeline could not extract
is represented by its absence (or None), never invented. The rule engine's
DslContext treats "key absent" and "value is None" identically (both fail
`exists()`), so either is a safe way for a producer to represent "not found."
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Commodity(_Base):
    category: str | None = None
    subtype: str | None = None
    is_imported: bool | None = None
    is_exempt: bool | None = None


class NetQuantity(_Base):
    value: float | None = None
    unit: str | None = None


class Mrp(_Base):
    value: float | None = None
    currency_marker: str | None = None
    raw_text: str | None = None
    computed_value: float | None = None


class OriginalMrp(_Base):
    value: float | None = None
    is_visible: bool | None = None


class Sticker(_Base):
    mrp_value: float | None = None
    reason: str | None = None


class ManufacturerInfo(_Base):
    name: str | None = None
    address: str | None = None


class ConsumerCare(_Base):
    phone: str | None = None
    email: str | None = None


class Dimensions(_Base):
    length: float | None = None
    width: float | None = None


class PanelQuantity(_Base):
    net_quantity: NetQuantity | None = None


class PipelineReading(_Base):
    numeric_val: float | None = None
    text_val: str | None = None


class ListingData(_Base):
    net_quantity: str | None = None
    country_of_origin: str | None = None
    manufacturer_name: str | None = None
    price: float | None = None


class PackageOcrData(_Base):
    net_quantity: str | None = None
    country_of_origin: str | None = None
    manufacturer_name: str | None = None


class ExtractionEnvelope(_Base):
    schema_version: Literal["1.0"] = "1.0"

    scan_source: str | None = None
    scan_date: str | None = None

    commodity: Commodity | None = None
    net_quantity: NetQuantity | None = None
    mrp: Mrp | None = None
    mrp_candidates: list[float] | None = None
    sticker_detected: bool | None = None
    original_mrp: OriginalMrp | None = None
    sticker: Sticker | None = None
    usp_declared: float | None = None
    mfg_date: str | None = None
    best_before_date: str | None = None
    use_by_date: str | None = None
    expiry_date: str | None = None
    manufacturer_or_packer_or_importer: ManufacturerInfo | None = None
    common_or_generic_name: str | None = None
    brand_name: str | None = None
    consumer_care: ConsumerCare | None = None
    country_of_origin: str | None = None
    dimensions: Dimensions | None = None
    mfg_or_pack_or_import_month_year: str | None = None

    field_confidences: dict[str, float] | None = None

    panel_a: PanelQuantity | None = None
    panel_b: PanelQuantity | None = None

    ocr_pipeline: PipelineReading | None = None
    llm_pipeline: PipelineReading | None = None

    listing_data: ListingData | None = None
    package_ocr_data: PackageOcrData | None = None


def flatten(product: ExtractionEnvelope) -> list[dict[str, Any]]:
    """Derive the OCR-document's flat fields[] shape from the canonical envelope.

    Per CLAUDE.md section 6: "The OCR document's flat fields[] array is kept
    but derived... never author it by hand." Each leaf becomes one entry with
    its dotted path and value; a leaf that is None (not extracted) is omitted
    entirely, since a flat fields[] list is meant to enumerate what WAS found.
    """
    entries: list[dict[str, Any]] = []

    def _walk(value: Any, prefix: str) -> None:
        if isinstance(value, BaseModel):
            _walk(value.model_dump(exclude={"schema_version"} if prefix == "" else set()), prefix)
            return
        if isinstance(value, dict):
            for key, sub_value in value.items():
                if key == "schema_version":
                    continue
                path = f"{prefix}.{key}" if prefix else key
                _walk(sub_value, path)
            return
        if value is None:
            return
        entries.append({"field_name": prefix, "value": value})

    _walk(product, "")
    return entries
