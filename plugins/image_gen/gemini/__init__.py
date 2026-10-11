"""Google Gemini image generation backend.

Uses the Gemini 2.5 Flash Image model via the Google AI Studio API.
Returns inline base64 PNG saved under ``$HERMES_HOME/cache/images/``.

Aspect ratio is passed as a natural-language instruction appended to the
prompt — the Gemini generateContent API has no dedicated size/ratio param.

Selection precedence (first hit wins):
1. ``GEMINI_IMAGE_MODEL`` env var
2. ``image_gen.gemini.model`` in ``config.yaml``
3. ``image_gen.model`` in ``config.yaml`` (when it's one of our IDs)
4. :data:`DEFAULT_MODEL` — ``gemini-2.5-flash-image``
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_b64_image,
    success_response,
)

logger = logging.getLogger(__name__)

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-flash-image": {
        "display": "Gemini 2.5 Flash Image",
        "speed": "~10s",
        "strengths": "Fast, multimodal, Google AI Studio free tier",
    },
}

DEFAULT_MODEL = "gemini-2.5-flash-image"

_ASPECT_HINTS = {
    "landscape": "wide landscape orientation (16:9)",
    "portrait": "tall portrait orientation (9:16)",
    "square": "square aspect ratio (1:1)",
}


def _resolve_model() -> str:
    env = os.environ.get("GEMINI_IMAGE_MODEL")
    if env and env in _MODELS:
        return env
    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else {}
        gemini_cfg = section.get("gemini") if isinstance(section, dict) else {}
        if isinstance(gemini_cfg, dict):
            m = gemini_cfg.get("model")
            if isinstance(m, str) and m in _MODELS:
                return m
        top = section.get("model") if isinstance(section, dict) else None
        if isinstance(top, str) and top in _MODELS:
            return top
    except Exception as exc:
        logger.debug("Could not read image_gen config: %s", exc)
    return DEFAULT_MODEL


def _api_key() -> Optional[str]:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


class GeminiImageGenProvider(ImageGenProvider):
    """Gemini ``generateContent`` image backend."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini"

    def is_available(self) -> bool:
        return bool(_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": mid,
                "display": meta["display"],
                "speed": meta["speed"],
                "strengths": meta["strengths"],
                "price": "free tier via Google AI Studio",
            }
            for mid, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Google Gemini",
            "badge": "free",
            "tag": "gemini-2.5-flash-image via Google AI Studio",
            "env_vars": [
                {
                    "key": "GOOGLE_API_KEY",
                    "prompt": "Google AI Studio API key",
                    "url": "https://aistudio.google.com/app/apikey",
                },
            ],
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)

        if not prompt:
            return error_response(
                error="Prompt is required and must be a non-empty string",
                error_type="invalid_argument",
                provider="gemini",
                aspect_ratio=aspect,
            )

        key = _api_key()
        if not key:
            return error_response(
                error=(
                    "GOOGLE_API_KEY not set. Add it to your .env file. "
                    "Get a free key at https://aistudio.google.com/app/apikey"
                ),
                error_type="auth_required",
                provider="gemini",
                aspect_ratio=aspect,
            )

        model_id = _resolve_model()
        hint = _ASPECT_HINTS.get(aspect, "")
        full_prompt = f"{prompt}, {hint}" if hint else prompt

        payload = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}], "role": "user"}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }).encode()

        url = f"{API_BASE}/{model_id}:generateContent?key={key}"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                response = json.loads(r.read())
        except Exception as exc:
            return error_response(
                error=f"Gemini API request failed: {exc}",
                error_type="api_error",
                provider="gemini",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        if "error" in response:
            return error_response(
                error=f"Gemini API error: {response['error'].get('message', response['error'])}",
                error_type="api_error",
                provider="gemini",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        parts = (
            response.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )

        b64_data = None
        mime_type = "image/png"
        for part in parts:
            inline = part.get("inlineData")
            if inline:
                b64_data = inline.get("data")
                mime_type = inline.get("mimeType", "image/png")
                break

        if not b64_data:
            return error_response(
                error="Gemini returned no image data in response",
                error_type="empty_response",
                provider="gemini",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        ext = mime_type.split("/")[-1].replace("jpeg", "jpg")
        try:
            saved_path = save_b64_image(b64_data, prefix="gemini", extension=ext)
        except Exception as exc:
            return error_response(
                error=f"Could not save image to cache: {exc}",
                error_type="io_error",
                provider="gemini",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        return success_response(
            image=str(saved_path),
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="gemini",
        )


def register(ctx) -> None:
    ctx.register_image_gen_provider(GeminiImageGenProvider())
