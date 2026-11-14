"""Run Smart Turn v3.2 on every pause of every recorded call. Local, no Gnani calls.

At each finished segment the model is given the call audio up to that pause,
which is what a live agent would have. Probabilities are saved per call in
data/smart_turn/, in the order of the call's segment events.

    uv run python -m dhairya.bench.smart_turn_scores
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import numpy as np

from dhairya.bench.record import trace_dir
from dhairya.bench.render import audio_dir
from dhairya.config import ROOT, Settings, settings
from dhairya.gnani.audio import wav_to_pcm
from dhairya.turn.types import FINAL_KINDS

MODEL_URL = "https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/main/smart-turn-v3.2-cpu.onnx"
MODEL_PATH = ROOT / "models" / "smart-turn-v3.2-cpu.onnx"
# A segment's text reaches the client about this long after the audio the server
# closed the segment on (measured by the probe). Smart Turn gets audio up to that point.
STREAM_OVERHEAD_S = 0.19
WINDOW_S = 8  # the model looks at the last 8 seconds


def scores_dir(cfg: Settings) -> Path:
    return cfg.data_dir / "smart_turn"


def _model():
    import onnxruntime as ort
    from transformers import WhisperFeatureExtractor

    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", MODEL_URL, follow_redirects=True, timeout=120.0) as resp:
            resp.raise_for_status()
            MODEL_PATH.write_bytes(resp.read())
    options = ort.SessionOptions()
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(MODEL_PATH), sess_options=options), WhisperFeatureExtractor(
        chunk_length=WINDOW_S
    )


def probability(session, extractor, samples: np.ndarray, rate: int) -> float:
    """Probability that the speaker is finished. Follows inference.py in pipecat-ai/smart-turn."""
    audio = samples.astype(np.float32) / 32768.0
    limit = WINDOW_S * rate
    if len(audio) > limit:
        audio = audio[-limit:]
    else:
        audio = np.concatenate([np.zeros(limit - len(audio), dtype=np.float32), audio])
    inputs = extractor(
        audio, sampling_rate=rate, return_tensors="np", padding="max_length",
        max_length=limit, truncation=True, do_normalize=True,
    )  # fmt: skip
    features = inputs.input_features.astype(np.float32)
    return float(session.run(None, {"input_features": features})[0].reshape(-1)[0])


def main() -> None:
    cfg = settings()
    scores_dir(cfg).mkdir(parents=True, exist_ok=True)
    session, extractor = _model()
    timings: list[float] = []
    done = 0
    for path in sorted(trace_dir(cfg).glob("*.json")):
        out = scores_dir(cfg) / path.name
        trace = json.loads(path.read_text())
        if "error" in trace or out.exists():
            continue
        samples, rate = wav_to_pcm((audio_dir(cfg) / f"{path.stem}.wav").read_bytes())
        probabilities = []
        for event in trace["events"]:
            if event["kind"] not in FINAL_KINDS:
                continue
            heard_until = max(0.5, event["t"] - STREAM_OVERHEAD_S)
            started = time.perf_counter()
            probabilities.append(
                round(probability(session, extractor, samples[: int(heard_until * rate)], rate), 4)
            )
            timings.append(time.perf_counter() - started)
        out.write_text(json.dumps(probabilities))
        done += 1
    if timings:
        median_ms = 1000 * sorted(timings)[len(timings) // 2]
        print(f"{done} calls scored; median inference {median_ms:.0f} ms")
    else:
        print("nothing new to score")


if __name__ == "__main__":
    main()
