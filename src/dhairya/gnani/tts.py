"""Timbre text-to-speech over REST. Responses are cached on disk."""

from __future__ import annotations

import httpx
import numpy as np

from dhairya.config import Settings
from dhairya.gnani.audio import wav_to_pcm
from dhairya.gnani.cache import cached_bytes, request_key
from dhairya.gnani.errors import error_for, with_retry

TTS_PATH = "/api/v1/tts/inference"


def synthesize(
    cfg: Settings,
    text: str,
    voice: str,
    *,
    language: str = "hi-IN",
    speed: float = 1.0,
    sample_rate: int = 16000,
    model: str | None = None,
) -> tuple[np.ndarray, int]:
    """Return (int16 mono samples, sample rate) for the spoken text."""
    body = {
        "text": text,
        "voice": voice,
        "model": model or cfg.tts_model,
        "language": language,
        "speed": speed,
        "audio_config": {
            "sample_rate": sample_rate,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    def call() -> bytes:
        def once() -> bytes:
            resp = httpx.post(
                cfg.base_url + TTS_PATH,
                headers={"X-API-Key-ID": cfg.api_key},
                json=body,
                timeout=60.0,
            )
            if resp.status_code != 200:
                raise error_for(resp.status_code, resp.text)
            return resp.content

        return with_retry(once)

    data = cached_bytes(cfg.cache_dir, "tts", request_key(body), call)
    return wav_to_pcm(data)
