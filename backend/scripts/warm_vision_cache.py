"""One-shot: populate data/cache/vision/<sha256>.json for the demo images so
the offline demo (CLAUDE.md section 10) works without ANTHROPIC_API_KEY at
demo time. Run once, with ANTHROPIC_API_KEY set, then commit the JSON files.

    python scripts/warm_vision_cache.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from lmd import config  # noqa: E402 -- loads .env before pipeline_b reads ANTHROPIC_API_KEY
from lmd.cv.pipeline_b import extract_with_vision  # noqa: E402
from lmd.evidence.hashing import sha256_bytes  # noqa: E402

_ = config  # loaded for its .env side effect

_IMAGES = [
    "01_curved_pouch_dense_text.jpg",
    "02_flat_box_clean.jpg",
    "04_rotated_blurry_dotmatrix.jpg",
    "06_curved_jar.jpg",
]


def main() -> None:
    images_dir = _REPO_ROOT / "research" / "mainResearch"
    for name in _IMAGES:
        image_path = images_dir / name
        if not image_path.is_file():
            print(f"SKIP  {name} (not found)")
            continue
        image_bytes = image_path.read_bytes()
        image_sha256 = sha256_bytes(image_bytes)
        fields = extract_with_vision(image_bytes, use_cache=True)
        print(f"{name}: sha256={image_sha256[:16]}... fields={sorted(fields.keys())}")


if __name__ == "__main__":
    main()
