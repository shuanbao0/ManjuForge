"""OpenAI GPT Image (gpt-image-{1,1.5,2}) client.

Used when the project's T2I/I2I instance has ``vendor_id == "openai"`` and
the active model id starts with ``gpt-image-``. Uses the official Images
and Image Edits endpoints — Edits accepts an image array for multi-
reference I2I.

API surface:
    POST {base}/images/generations           # T2I
    POST {base}/images/edits                 # I2I (multipart form)
    Authorization: Bearer <OPENAI_API_KEY>

The response carries either ``url`` or ``b64_json`` per image.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import time
from typing import List, Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://api.openai.com/v1"


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("OPENAI_API_KEY")
        if v:
            return v
    return get_cred("OPENAI_API_KEY")


def _resolve_model() -> str:
    from .instance import InstanceType, required_model_name
    return required_model_name(InstanceType.T2I)


def _size_for_openai(size: str) -> str:
    """Map our ``WxH`` (with ``*``) to the closest size GPT Image supports."""
    if not size or "*" not in size:
        return "1024x1024"
    try:
        w, h = (int(x) for x in size.split("*"))
    except ValueError:
        return "1024x1024"
    candidates = ["1024x1024", "1024x1536", "1536x1024", "auto"]
    target = w / h
    return min(candidates[:3], key=lambda c: abs(_aspect(c) - target))


def _aspect(s: str) -> float:
    a, b = s.split("x")
    return int(a) / int(b)


def generate_openai_image(
    prompt: str,
    output_path: str,
    *,
    size: str = "1024*1024",
    n: int = 1,
    negative_prompt: Optional[str] = None,
    ref_image_paths: Optional[List[str]] = None,
) -> Tuple[List[str], float]:
    """Run T2I (no refs) or I2I (with refs) on GPT Image.

    For I2I we use the ``/images/edits`` endpoint and forward up to 16
    references as multipart ``image[]`` fields. Negative prompt is folded
    into the text since the API has no dedicated field.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("GPT Image requires OPENAI_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()

    if negative_prompt:
        prompt = f"{prompt}\n\nAvoid: {negative_prompt}"

    saved: List[str] = []
    base_dir = os.path.dirname(output_path)
    base_name, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        ext = ".png"
    os.makedirs(base_dir, exist_ok=True)

    started = time.time()
    if ref_image_paths:
        local_refs = [p for p in ref_image_paths if p and os.path.exists(p)][:16]
        if local_refs:
            saved = _i2i_edit(
                base=base, api_key=api_key, model=model, prompt=prompt,
                size=_size_for_openai(size), n=n, ref_paths=local_refs,
                output_path=output_path, base_dir=base_dir, base_name=base_name, ext=ext,
            )
        else:
            logger.warning("GPT Image: no usable local reference; falling back to T2I")

    if not saved:
        saved = _t2i(
            base=base, api_key=api_key, model=model, prompt=prompt,
            size=_size_for_openai(size), n=n,
            output_path=output_path, base_dir=base_dir, base_name=base_name, ext=ext,
        )

    elapsed = time.time() - started
    logger.info("GPT Image saved %d files in %.2fs", len(saved), elapsed)
    return saved, elapsed


def _t2i(*, base, api_key, model, prompt, size, n, output_path, base_dir, base_name, ext) -> List[str]:
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": max(1, min(10, n)),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(f"{base}/images/generations", json=payload, headers=headers, timeout=300)
    return _consume_images(response, output_path, base_dir, base_name, ext, n)


def _i2i_edit(*, base, api_key, model, prompt, size, n, ref_paths, output_path, base_dir, base_name, ext) -> List[str]:
    files: List[tuple] = []
    file_handles = []
    try:
        for path in ref_paths:
            mime, _ = mimetypes.guess_type(path)
            mime = mime or "image/png"
            fh = open(path, "rb")
            file_handles.append(fh)
            files.append(("image[]", (os.path.basename(path), fh, mime)))

        data = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": str(max(1, min(10, n))),
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.post(
            f"{base}/images/edits",
            data=data, files=files, headers=headers, timeout=300,
        )
    finally:
        for fh in file_handles:
            try:
                fh.close()
            except Exception:  # pragma: no cover
                pass

    return _consume_images(response, output_path, base_dir, base_name, ext, n)


def _consume_images(response, output_path: str, base_dir: str, base_name: str, ext: str, n: int) -> List[str]:
    if response.status_code != 200:
        try:
            err = response.json()
        except Exception:
            err = {"detail": response.text}
        raise RuntimeError(f"GPT Image error: {err}")
    body = response.json()
    data = body.get("data", []) or []
    if not data:
        raise RuntimeError(f"GPT Image returned no images: {body}")

    saved: List[str] = []
    for i, item in enumerate(data):
        target = output_path if i == 0 and n == 1 else os.path.join(base_dir, f"{base_name}_{i}{ext}")
        if item.get("url"):
            r = requests.get(item["url"], timeout=120)
            r.raise_for_status()
            with open(target, "wb") as f:
                f.write(r.content)
        elif item.get("b64_json"):
            with open(target, "wb") as f:
                f.write(base64.b64decode(item["b64_json"]))
        else:
            continue
        saved.append(target)
    return saved


__all__ = ["generate_openai_image"]
