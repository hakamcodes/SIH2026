"""Prime backend/lmd/cv/pipeline_b.py's on-disk vision cache for demo images.

Pipeline B (Claude Vision) caches every response under
data/cache/vision/<sha256-of-image-bytes>.json, keyed purely by image
content (see pipeline_b.py:extract_with_vision). This script is a thin
driver over that existing function -- it adds no new caching logic -- so
that:

  1. The demo does not depend on ANTHROPIC_API_KEY being valid/unexpired
     at judge time.
  2. Repeat demo runs cost zero Anthropic API calls.
  3. The demo works fully offline once the cache files are committed.

IMPORTANT: the cache key is the sha256 of the *uploaded* bytes. The
frontend's client-side resize (frontend/src/lib/image-utils.ts) leaves an
already-JPEG image at or under 1280px on its longest side completely
unchanged, so to guarantee a cache hit at demo time:

  - Prime the exact file you intend to upload during the demo.
  - If that file is not already a JPEG at or under 1280px, resize it
    yourself first (e.g. with the same tool/settings the browser would use)
    so the bytes you prime here match the bytes that will actually be sent.

Usage (from repo root, with the backend venv active and ANTHROPIC_API_KEY set):

    python scripts/prime_vision_cache.py path/to/image1.jpg path/to/image2.jpg

With no arguments, primes every .jpg/.jpeg/.png under research/mainResearch/.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_SRC = _REPO_ROOT / "backend"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

_DEFAULT_DIR = _REPO_ROOT / "research" / "mainResearch"
_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def _default_images() -> list[Path]:
    if not _DEFAULT_DIR.is_dir():
        return []
    return sorted(p for p in _DEFAULT_DIR.iterdir() if p.suffix.lower() in _EXTENSIONS)


def main(argv: list[str]) -> int:
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Set it before priming the cache.", file=sys.stderr)
        return 1

    from lmd.cv.pipeline_b import _cache_path, extract_with_vision
    from lmd.evidence.hashing import sha256_bytes

    paths = [Path(p) for p in argv] if argv else _default_images()
    if not paths:
        print(f"No images given and none found under {_DEFAULT_DIR}", file=sys.stderr)
        return 1

    for path in paths:
        if not path.is_file():
            print(f"SKIP  {path} (not found)")
            continue
        image_bytes = path.read_bytes()
        sha = sha256_bytes(image_bytes)
        cache_file = _cache_path(sha)
        was_cached = cache_file.is_file()
        media_type = _MEDIA_TYPES.get(path.suffix.lower(), "image/jpeg")

        fields = extract_with_vision(image_bytes, media_type=media_type)

        status = "HIT (already cached)" if was_cached else "PRIMED (live API call)"
        print(f"{status:<24} {path}  sha256={sha}  -> {cache_file}")
        print(f"  fields read: {sorted(fields.keys()) or '(none)'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
