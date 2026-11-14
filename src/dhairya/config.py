"""Settings and constants. The only module that reads the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Prisma realtime wants frames of exactly 1,024 bytes (512 samples of 16-bit mono PCM).
# Source: docs.gnani.ai/api/STT/stt-websocket.md
STREAM_FRAME_BYTES = 1024
STREAM_FRAME_SAMPLES = STREAM_FRAME_BYTES // 2

# Retry policy for 429 and 5xx. 429 carries no Retry-After header (Gnani error docs).
RETRY_TRIES = 4
RETRY_FIRST_DELAY_S = 1.0


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    stt_model: str
    tts_model: str
    data_dir: Path
    results_dir: Path

    @property
    def ws_base(self) -> str:
        return self.base_url.replace("https://", "wss://").replace("http://", "ws://")

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


def settings() -> Settings:
    return Settings(
        api_key=os.environ.get("GNANI_API_KEY", "").strip(),
        base_url=os.environ.get("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/"),
        stt_model=os.environ.get("GNANI_STT_MODEL", "prisma-v3.0"),
        tts_model=os.environ.get("GNANI_TTS_MODEL", "timbre-v3.0"),
        data_dir=Path(os.environ.get("DHAIRYA_DATA_DIR", str(ROOT / "data"))),
        results_dir=ROOT / "results",
    )
