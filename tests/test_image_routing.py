"""Routing tests for ``WanxImageModel.generate``.

Locks in which API family each DashScope model name dispatches to. Without
these tests the silent ``ImageSynthesis.call`` fallback (which only serves
deprecated models) used to swallow every newer model name and fail at
runtime with vague ``"url error"`` messages — see the qwen-image-2.0-pro
regression that motivated this routing.
"""
import base64

import pytest
import requests

from src.models.image import WanxImageModel


PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4//8/AwAI/AL+"
    "X2VINQAAAABJRU5ErkJggg=="
)


class _SyncMultimodalResponse:
    """Mimics the synchronous ``/multimodal-generation/generation`` reply."""

    status_code = 200
    text = (
        '{"output":{"choices":[{"message":{"content":[{"image":'
        '"https://example.com/sync.png"}]}}]}}'
    )

    def json(self):
        return {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": [{"image": "https://example.com/sync.png"}]
                        }
                    }
                ]
            }
        }


class _AsyncCreateResponse:
    status_code = 200
    text = '{"output":{"task_id":"task-x","task_status":"PENDING"}}'

    def json(self):
        return {"output": {"task_id": "task-x", "task_status": "PENDING"}}


class _AsyncPollResponse:
    status_code = 200

    def json(self):
        return {
            "output": {
                "task_status": "SUCCEEDED",
                "choices": [
                    {
                        "message": {
                            "content": [{"image": "https://example.com/async.png"}]
                        }
                    }
                ],
            }
        }


@pytest.mark.parametrize(
    "model,expected_family",
    [
        # multimodal_sync (HTTP /multimodal-generation/generation)
        ("wan2.6-t2i", "multimodal_sync"),
        ("qwen-image", "multimodal_sync"),
        ("qwen-image-plus", "multimodal_sync"),
        ("qwen-image-edit", "multimodal_sync"),
        ("qwen-image-2.0", "multimodal_sync"),
        ("qwen-image-2.0-pro", "multimodal_sync"),
        # image_gen_async (HTTP /image-generation/generation w/ polling)
        ("wan2.6-image", "image_gen_async"),
        ("wan2.5-t2i-preview", "image_gen_async"),
        ("wan2.5-i2i-preview", "image_gen_async"),
        # legacy_sdk (deprecated ImageSynthesis.call path)
        ("wanx-v1", "legacy_sdk"),
        ("flux-schnell", "legacy_sdk"),  # may move once we add a flux-on-DS adapter
        ("", "legacy_sdk"),
    ],
)
def test_classify_dashscope_family(model, expected_family):
    assert WanxImageModel._classify_dashscope_family(model) == expected_family


@pytest.mark.parametrize(
    "model",
    ["qwen-image", "qwen-image-plus", "qwen-image-2.0", "qwen-image-2.0-pro"],
)
def test_qwen_image_t2i_routes_to_multimodal_sync(monkeypatch, tmp_path, model):
    """qwen-image* T2I → /multimodal-generation/generation, sync response."""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _SyncMultimodalResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", lambda *a, **k: _AsyncPollResponse())
    monkeypatch.setattr(
        "src.models.image.get_provider_base_url", lambda _: "https://dashscope.test"
    )
    # Stub _download_image so the test stays offline.
    monkeypatch.setattr(WanxImageModel, "_download_image", lambda self, url, path: None)

    out = tmp_path / "out.png"
    img = WanxImageModel({})
    img.generate(prompt="hello", output_path=str(out), model_name=model)

    assert captured["url"].endswith("/multimodal-generation/generation")
    assert captured["payload"]["model"] == model
    # T2I has only the text content entry, no image entries.
    content = captured["payload"]["input"]["messages"][0]["content"]
    assert content == [{"text": "hello"}]


def test_qwen_image_edit_carries_reference_image(monkeypatch, tmp_path):
    """qwen-image-edit (I2I) → multimodal sync but with image content first."""
    ref = tmp_path / "ref.png"
    ref.write_bytes(base64.b64decode(PNG_1X1_BASE64))

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        return _SyncMultimodalResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(
        "src.models.image.get_provider_base_url", lambda _: "https://dashscope.test"
    )
    monkeypatch.setattr(WanxImageModel, "_download_image", lambda self, url, path: None)

    img = WanxImageModel({})
    img.generate(
        prompt="edit",
        output_path=str(tmp_path / "out.png"),
        ref_image_path=str(ref),
        model_name="qwen-image-edit",
    )

    assert captured["payload"]["model"] == "qwen-image-edit"
    content = captured["payload"]["input"]["messages"][0]["content"]
    image_entries = [c for c in content if "image" in c]
    text_entries = [c for c in content if "text" in c]
    assert len(image_entries) == 1
    assert text_entries[0]["text"] == "edit"


@pytest.mark.parametrize(
    "model",
    ["wan2.5-t2i-preview", "wan2.5-i2i-preview"],
)
def test_wan25_routes_to_image_generation_async(monkeypatch, tmp_path, model):
    """wan2.5-* → /image-generation/generation w/ task polling."""
    ref = tmp_path / "ref.png"
    ref.write_bytes(base64.b64decode(PNG_1X1_BASE64))

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _AsyncCreateResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", lambda *a, **k: _AsyncPollResponse())
    monkeypatch.setattr(
        "src.models.image.get_provider_base_url", lambda _: "https://dashscope.test"
    )
    monkeypatch.setattr(WanxImageModel, "_download_image", lambda self, url, path: None)
    monkeypatch.setattr("time.sleep", lambda _: None)

    img = WanxImageModel({})
    if model == "wan2.5-i2i-preview":
        img.generate(
            prompt="x",
            output_path=str(tmp_path / "out.png"),
            ref_image_path=str(ref),
            model_name=model,
        )
    else:
        img.generate(prompt="x", output_path=str(tmp_path / "out.png"), model_name=model)

    assert captured["url"].endswith("/image-generation/generation")
    assert captured["payload"]["model"] == model


def test_base_url_from_instance_applied_to_dashscope_sdk(monkeypatch, tmp_path):
    """instance.base_url should set ``dashscope.base_http_api_url`` so the
    Settings page's Base URL field is no longer a silent no-op."""
    import dashscope

    class FakeInstance:
        base_url = "https://my-proxy.example.com"

    monkeypatch.setattr("src.runtime.current_instance", lambda: FakeInstance())
    monkeypatch.setattr(
        "src.models.image.get_provider_base_url", lambda _: "https://dashscope.test"
    )
    # Stub the actual HTTP call so we don't need to mock the response body.
    monkeypatch.setattr(requests, "post", lambda *a, **k: _SyncMultimodalResponse())
    monkeypatch.setattr(WanxImageModel, "_download_image", lambda self, url, path: None)

    img = WanxImageModel({})
    img.generate(prompt="x", output_path=str(tmp_path / "out.png"), model_name="wan2.6-t2i")

    # The /api/v1 suffix is auto-appended.
    assert dashscope.base_http_api_url == "https://my-proxy.example.com/api/v1"


def test_base_url_with_api_v1_suffix_is_not_double_appended(monkeypatch, tmp_path):
    import dashscope

    class FakeInstance:
        base_url = "https://my-proxy.example.com/api/v1"

    monkeypatch.setattr("src.runtime.current_instance", lambda: FakeInstance())
    monkeypatch.setattr(
        "src.models.image.get_provider_base_url", lambda _: "https://dashscope.test"
    )
    monkeypatch.setattr(requests, "post", lambda *a, **k: _SyncMultimodalResponse())
    monkeypatch.setattr(WanxImageModel, "_download_image", lambda self, url, path: None)

    img = WanxImageModel({})
    img.generate(prompt="x", output_path=str(tmp_path / "out.png"), model_name="wan2.6-t2i")

    assert dashscope.base_http_api_url == "https://my-proxy.example.com/api/v1"
