"""Make a clean recording sound like it came over a telephone line.

The caller's audio is resampled to 8 kHz and passed through G.711 mu-law, the
codec most Indian telephony still uses. ffmpeg does the work through pipes.
"""

from __future__ import annotations

import subprocess

import numpy as np

PHONE_RATE = 8000


class ChannelError(RuntimeError):
    pass


def _ffmpeg(args: list[str], data: bytes) -> bytes:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
            input=data,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ChannelError(
            "ffmpeg is not installed; it is needed for the phone-line condition"
        ) from exc
    if proc.returncode != 0:
        raise ChannelError(f"ffmpeg failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def to_phone_line(samples: np.ndarray, rate: int) -> tuple[np.ndarray, int]:
    """Resample to 8 kHz and round-trip through mu-law. Returns int16 samples at 8 kHz."""
    pcm = samples.astype("<i2").tobytes()
    encoded = _ffmpeg(
        ["-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0",
         "-ar", str(PHONE_RATE), "-c:a", "pcm_mulaw", "-f", "mulaw", "pipe:1"],
        pcm,
    )  # fmt: skip
    decoded = _ffmpeg(
        ["-f", "mulaw", "-ar", str(PHONE_RATE), "-ac", "1", "-i", "pipe:0",
         "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"],
        encoded,
    )  # fmt: skip
    return np.frombuffer(decoded, dtype="<i2").astype(np.int16), PHONE_RATE
