"""Rebuffer the browser's audio chunks into the exact frames Prisma's stream wants."""

from __future__ import annotations

import numpy as np

from dhairya.config import STREAM_FRAME_BYTES


class FrameBuffer:
    """PCM16 little-endian bytes in any chunk size in; 1,024-byte (512-sample) frames out."""

    def __init__(self, frame_bytes: int = STREAM_FRAME_BYTES) -> None:
        self._size = frame_bytes
        self._rest = b""

    def push(self, data: bytes) -> list[np.ndarray]:
        self._rest += data
        frames = []
        while len(self._rest) >= self._size:
            frames.append(np.frombuffer(self._rest[: self._size], dtype="<i2").copy())
            self._rest = self._rest[self._size :]
        return frames
