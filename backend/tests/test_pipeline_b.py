"""Pipeline B: caching and response parsing, using a fake VisionClient so the
suite never needs network access or ANTHROPIC_API_KEY.
"""
import json

from lmd.cv import pipeline_b


class _FakeClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = 0

    def create_message(self, model, image_b64, media_type, prompt):
        self.calls += 1
        return self.response_text


def test_extract_with_vision_parses_json_response(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_b, "_CACHE_DIR", tmp_path)
    client = _FakeClient('{"net_quantity": {"value": 200, "unit": "g"}, "mrp": {"value": 150}}')
    fields = pipeline_b.extract_with_vision(b"fake-image-bytes", client=client, use_cache=False)
    assert fields["net_quantity"]["value"] == 200
    assert fields["mrp"]["value"] == 150


def test_extract_with_vision_ignores_unknown_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_b, "_CACHE_DIR", tmp_path)
    client = _FakeClient('{"net_quantity": {"value": 1}, "fabricated_field": "should be dropped"}')
    fields = pipeline_b.extract_with_vision(b"img", client=client, use_cache=False)
    assert "fabricated_field" not in fields


def test_extract_with_vision_returns_empty_on_unparseable_response(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_b, "_CACHE_DIR", tmp_path)
    client = _FakeClient("I could not read this label clearly.")
    fields = pipeline_b.extract_with_vision(b"img", client=client, use_cache=False)
    assert fields == {}


def test_extract_with_vision_caches_by_image_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_b, "_CACHE_DIR", tmp_path)
    client = _FakeClient('{"mrp": {"value": 99}}')
    fields1 = pipeline_b.extract_with_vision(b"same-image", client=client, use_cache=True)
    fields2 = pipeline_b.extract_with_vision(b"same-image", client=client, use_cache=True)
    assert fields1 == fields2 == {"mrp": {"value": 99}}
    assert client.calls == 1  # second call served from cache, no client invocation

    cached_files = list(tmp_path.glob("*.json"))
    assert len(cached_files) == 1
    assert json.loads(cached_files[0].read_text(encoding="utf-8"))["fields"]["mrp"]["value"] == 99
