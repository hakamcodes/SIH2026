"""Pipeline B: semantic cross-check via a vision-capable Claude model.

Per CLAUDE.md invariant 7, the vision model is NEVER the sole source of a
numeric legal field ("a confidently wrong digit is worse than 'could not
read'") -- it exists only to agree or disagree with pipeline A (RapidOCR).
See lmd.cv.reconcile for the acceptance rule.

Responses are cached under data/cache/vision/<sha256-of-image-bytes>.json,
keyed purely by image content, so a demo can run fully offline once the
cache is populated (CLAUDE.md: "is what makes an offline demo possible").
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from lmd.evidence.hashing import sha256_bytes

DEFAULT_MODEL = os.environ.get("LMD_VISION_MODEL") or "claude-haiku-4-5-20251001"

_CACHE_DIR = Path(__file__).resolve().parents[4] / "data" / "cache" / "vision"

# Bump this whenever _PROMPT or _ALLOWED_KEYS changes -- a cached response
# written under an older prompt cannot be trusted to carry the newer keys,
# and silently returning it would look like a confirmed cache hit while
# actually serving a narrower field set.
_PROMPT_VERSION = 2

_PROMPT = """You are assisting a Legal Metrology compliance scan. Look at this \
package photograph and extract ONLY what is clearly visible. Respond with a \
single JSON object with this exact shape (omit any key you cannot read \
confidently -- never guess a value):
{
  "net_quantity": {"value": <number>, "unit": "<g|kg|ml|l|mm|cm|m>"},
  "mrp": {"value": <number>},
  "country_of_origin": "<string>",
  "manufacturer_name": "<string>",
  "manufacturer_address": "<string>",
  "common_or_generic_name": "<string>",
  "brand_name": "<string>",
  "mfg_date": "<YYYY-MM-DD>",
  "best_before_date": "<YYYY-MM-DD>"
}
Respond with the JSON object only, no other text."""

_ALLOWED_KEYS = {
    "net_quantity",
    "mrp",
    "country_of_origin",
    "manufacturer_name",
    "manufacturer_address",
    "common_or_generic_name",
    "brand_name",
    "mfg_date",
    "best_before_date",
}
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class VisionClient(Protocol):
    def create_message(self, model: str, image_b64: str, media_type: str, prompt: str) -> str: ...


class AnthropicVisionClient:
    """Thin wrapper so pipeline_b.extract_with_vision can be unit-tested with
    a fake client and never needs network access in the test suite."""

    def __init__(self) -> None:
        import anthropic  # local import: importing this module must not require the SDK/key

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to .env or the environment before "
                "calling pipeline B (see CLAUDE.md / .env.example)."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def create_message(self, model: str, image_b64: str, media_type: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return "".join(block.text for block in response.content if block.type == "text")


@lru_cache(maxsize=1)
def _get_default_client() -> AnthropicVisionClient:
    # A fresh anthropic.Anthropic() opens its own httpx connection pool --
    # on a multi-panel scan that ran one per panel, which added up on the
    # 512MB Render free tier. Cache the process-global default; a caller
    # supplying its own `client=` (tests) is unaffected.
    return AnthropicVisionClient()


def _cache_path(image_sha256: str) -> Path:
    return _CACHE_DIR / f"{image_sha256}.json"


def _parse_response_text(text: str) -> dict[str, Any]:
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {k: v for k, v in parsed.items() if k in _ALLOWED_KEYS}


def extract_with_vision(
    image_bytes: bytes,
    media_type: str = "image/jpeg",
    model: str | None = None,
    client: VisionClient | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Return a best-effort subset of ExtractionEnvelope fields read by the
    vision model. An empty dict means "nothing read confidently," never a
    fabricated guess. Results are cached by image content hash.
    """
    image_sha256 = sha256_bytes(image_bytes)
    cache_file = _cache_path(image_sha256)

    if use_cache and cache_file.is_file():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached.get("prompt_version") == _PROMPT_VERSION:
            return cached["fields"]
        # Stale schema -- fall through and re-query rather than silently
        # returning a response captured under an older, narrower prompt.

    model = model or DEFAULT_MODEL
    if client is None:
        client = _get_default_client()

    import base64

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    raw_text = client.create_message(model=model, image_b64=image_b64, media_type=media_type, prompt=_PROMPT)
    image_b64 = None
    fields = _parse_response_text(raw_text)

    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {"model": model, "prompt_version": _PROMPT_VERSION, "fields": fields},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return fields
