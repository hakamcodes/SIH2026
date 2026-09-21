"""Compress-then-base64 helpers for storing images as Firestore document
fields instead of files on disk.

Firestore caps a single document at 1 MiB, and a scan document already
carries the extraction envelope, OCR boxes and rule results alongside the
image data, so there is no fixed "budget" per image -- _MAX_STORED_BYTES is
a conservative ceiling per image field, not a guarantee against ever hitting
the document cap on a scan with unusually large extraction data. Base64
itself adds ~33% size on top of whatever this returns.
"""
from __future__ import annotations

import base64
import io

from PIL import Image

_MAX_STORED_BYTES = 600_000
_MAX_DIMENSION_PX = 1600
_MIN_DIMENSION_PX = 400
_MIN_JPEG_QUALITY = 30


def compress_for_storage(
    image_bytes: bytes,
    image_format: str | None = None,
    max_bytes: int = _MAX_STORED_BYTES,
    max_dimension_px: int = _MAX_DIMENSION_PX,
    palette: bool = False,
) -> bytes:
    """Return image_bytes unchanged if already under max_bytes, otherwise
    downscale (and, for JPEG, step down quality) until it fits.
    image_format is "JPEG" or "PNG"; if omitted, it is read off the image
    itself (Pillow detects this on open) -- used for evidence uploads whose
    format isn't already known by the caller the way scan.py's is. Returns
    the original bytes unchanged if they can't be decoded as an image at
    all, rather than corrupting an evidence file the system can't compress.

    max_bytes/max_dimension_px are overridable because different callers have
    different budgets sharing the same 1 MiB Firestore field ceiling: a scan
    document has two image fields (original + overlay) alongside its rule
    results, but a report PDF embeds both of those images *inside a single
    pdf_base64 field*, so it needs a much tighter per-image budget to leave
    room for two images plus the rest of the document in one field.

    palette=True converts a PNG to an adaptive 64-color palette before the
    shrink loop -- opt-in because it loses color fidelity, appropriate for a
    boxes-and-text overlay but not for evidence/report images."""
    if len(image_bytes) <= max_bytes:
        return image_bytes

    try:
        opened = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return image_bytes

    with opened as im:
        fmt = (image_format or im.format or "JPEG").upper()
        if fmt == "JPEG":
            im = im.convert("RGB")

        width, height = im.size
        scale = min(1.0, max_dimension_px / max(width, height))
        if scale < 1.0:
            width, height = max(1, int(width * scale)), max(1, int(height * scale))
            im = im.resize((width, height), Image.LANCZOS)

        if fmt != "JPEG":
            # PNG has no quality knob, so an overlay with lots of drawn boxes
            # (which compresses far worse than a photo) needs the resize
            # itself to iterate: keep shrinking until it fits or we hit the
            # minimum dimension, rather than a single resize pass that can
            # still land well over the ceiling (measured: 1.6MB at the
            # original resize target on a dense overlay).
            if palette:
                # Boxes-and-text overlays have very few distinct colors, so
                # an adaptive 64-color palette shrinks the PNG far more than
                # resizing alone -- opt-in only, so evidence/report callers
                # that need full color fidelity are unaffected.
                current = im.convert("P", palette=Image.ADAPTIVE, colors=64)
            else:
                current = im
            data = image_bytes
            for _ in range(8):
                buf = io.BytesIO()
                current.save(buf, format=fmt, optimize=True)
                data = buf.getvalue()
                if len(data) <= max_bytes or max(current.size) <= _MIN_DIMENSION_PX:
                    break
                new_size = (max(_MIN_DIMENSION_PX, int(current.size[0] * 0.75)), max(_MIN_DIMENSION_PX, int(current.size[1] * 0.75)))
                current = current.resize(new_size, Image.LANCZOS)
            return data

        quality = 85
        data = image_bytes
        while True:
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes or quality <= _MIN_JPEG_QUALITY:
                return data
            quality -= 10


def encode_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")


def decode_base64(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))
