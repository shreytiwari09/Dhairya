"""Prisma speech-to-text over REST (30 s per call). Responses are cached on disk."""

from __future__ import annotations

import json
from typing import Any

import httpx
import numpy as np

from dhairya.config import Settings
from dhairya.gnani.audio import pcm_to_wav
from dhairya.gnani.cache import cached_bytes, request_key
from dhairya.gnani.errors import error_for, with_retry

STT_PATH = "/stt/v3"


def transcribe(
    cfg: Settings,
    samples: np.ndarray,
    rate: int,
    *,
    language_code: str = "hi-IN,en-IN",
    fmt: str = "transcribe",
    hints: dict[str, str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Return the parsed JSON response. The text is under the "transcript" key."""
    wav = pcm_to_wav(samples, rate)
    fields = {
        "model": model or cfg.stt_model,
        "language_code": language_code,
        "format": fmt,
        **(hints or {}),
    }

    def call() -> bytes:
        def once() -> bytes:
            resp = httpx.post(
                cfg.base_url + STT_PATH,
                headers={"X-API-Key-ID": cfg.api_key},
                data=fields,
                files={"audio_file": ("audio.wav", wav, "audio/wav")},
                timeout=60.0,
            )
            if resp.status_code != 200:
                raise error_for(resp.status_code, resp.text)
            return resp.content

        return with_retry(once)

    data = cached_bytes(cfg.cache_dir, "stt_rest", request_key(fields, wav), call)
    return json.loads(data)
