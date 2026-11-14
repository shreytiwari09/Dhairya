"""Small PCM helpers. Audio in this project is mono int16 numpy arrays."""

from __future__ import annotations

import io
import struct
import wave

import numpy as np


def wav_to_pcm(data: bytes) -> tuple[np.ndarray, int]:
    """Read a WAV into (int16 mono samples, sample rate).

    Parses the RIFF chunks by hand because Timbre has been reported to send
    placeholder sizes (0xFFFFFFFF) in the header, which the wave module rejects.
    """
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a WAV file")
    pos, rate, channels, width, pcm = 12, 0, 1, 2, b""
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        body = pos + 8
        if chunk_id == b"fmt ":
            _fmt, channels, rate, _br, _ba, bits = struct.unpack("<HHIIHH", data[body : body + 16])
            width = bits // 8
        elif chunk_id == b"data":
            end = len(data) if size == 0xFFFFFFFF or body + size > len(data) else body + size
            pcm = data[body:end]
            break
        if size == 0xFFFFFFFF:
            break
        pos = body + size + (size & 1)
    if not rate or not pcm:
        raise ValueError("WAV has no fmt or data chunk")
    if width != 2:
        raise ValueError(f"expected 16-bit audio, got {width * 8}-bit")
    samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2")
    if channels > 1:
        samples = samples.reshape(-1, channels)[:, 0]
    return samples.astype(np.int16), rate


def pcm_to_wav(samples: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.astype("<i2").tobytes())
    return buf.getvalue()


def silence(seconds: float, rate: int) -> np.ndarray:
    return np.zeros(int(round(seconds * rate)), dtype=np.int16)


def trim_silence(samples: np.ndarray, rate: int, threshold: int = 300) -> np.ndarray:
    """Cut leading and trailing near-silence so spliced pauses have exact lengths.

    Keeps 10 ms of margin on each side to avoid clipping soft consonants.
    """
    loud = np.flatnonzero(np.abs(samples.astype(np.int32)) > threshold)
    if loud.size == 0:
        return samples
    margin = rate // 100
    return samples[max(0, loud[0] - margin) : min(len(samples), loud[-1] + margin)]
