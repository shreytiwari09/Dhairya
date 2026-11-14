import shutil

import numpy as np
import pytest

from dhairya.bench.channel import to_phone_line

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _sine(rate: int, seconds: float = 1.0, hz: float = 440.0) -> np.ndarray:
    t = np.arange(int(rate * seconds)) / rate
    return (0.5 * 32767 * np.sin(2 * np.pi * hz * t)).astype(np.int16)


def test_phone_line_is_8khz_and_keeps_the_signal():
    out, rate = to_phone_line(_sine(16000), 16000)
    assert rate == 8000
    assert out.dtype == np.int16
    assert abs(len(out) - 8000) <= 160
    reference = _sine(8000)
    n = min(len(out), len(reference))
    corr = np.corrcoef(out[:n].astype(float), reference[:n].astype(float))[0, 1]
    assert corr > 0.9


def test_phone_line_handles_silence():
    out, rate = to_phone_line(np.zeros(1600, dtype=np.int16), 16000)
    assert rate == 8000 and len(out) > 0
