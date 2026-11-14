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


@dataclass(frozen=True)
class LiveSettings:
    """The public live demo: who may use it and how much. Defaults are generous enough for a
    panel of judges to try several turns each, and capped so credits cannot run away."""

    enabled: bool
    max_concurrent: int  # simultaneous callers (Prisma allows more than one stream)
    per_ip_hour: int
    per_ip_day: int
    daily_total: int  # all visitors together, rolling 24 h
    allowed_origins: tuple[str, ...]
    keepalive_url: str  # the server's own public address, pinged so a free host never idles
    keepalive_s: int


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def live_settings() -> LiveSettings:
    origins = os.environ.get(
        "LIVE_ALLOWED_ORIGINS",
        "https://shreytiwari09.github.io,http://localhost:8765,http://127.0.0.1:8765",
    )
    return LiveSettings(
        enabled=os.environ.get("LIVE_ENABLED", "true").strip().lower() not in ("0", "false", "no"),
        max_concurrent=_int("LIVE_MAX_CONCURRENT", 3),
        per_ip_hour=_int("LIVE_PER_IP_HOUR", 15),
        per_ip_day=_int("LIVE_PER_IP_DAY", 40),
        daily_total=_int("LIVE_DAILY_TOTAL", 400),
        allowed_origins=tuple(o.strip().rstrip("/") for o in origins.split(",") if o.strip()),
        # Render sets RENDER_EXTERNAL_URL itself; KEEPALIVE_URL overrides it for other hosts.
        keepalive_url=(
            os.environ.get("KEEPALIVE_URL") or os.environ.get("RENDER_EXTERNAL_URL") or ""
        ).rstrip("/"),
        keepalive_s=_int("KEEPALIVE_SECONDS", 480),  # Render idles a free service after 15 minutes
    )


def settings() -> Settings:
    return Settings(
        api_key=os.environ.get("GNANI_API_KEY", "").strip(),
        base_url=os.environ.get("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/"),
        stt_model=os.environ.get("GNANI_STT_MODEL", "prisma-v3.0"),
        tts_model=os.environ.get("GNANI_TTS_MODEL", "timbre-v3.0"),
        data_dir=Path(os.environ.get("DHAIRYA_DATA_DIR", str(ROOT / "data"))),
        results_dir=ROOT / "results",
    )
