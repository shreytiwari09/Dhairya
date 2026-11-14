"""Turn scripts into caller audio with pauses of exact, known length.

Each breath group is spoken by Timbre on its own, trimmed, and joined with
silence, so the true end of speech and every pause are known to the sample.
A whole-call REST transcription is stored as a reference; it is not used to
filter scripts, because that would bias the set toward what the parser reads.

    uv run python -m dhairya.bench.render --per-category 12
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np

from dhairya.bench.scripts import Script, load, scripts_path
from dhairya.config import Settings, settings
from dhairya.gnani.audio import pcm_to_wav, silence, trim_silence
from dhairya.gnani.errors import GnaniAuthError, GnaniCreditError, GnaniError
from dhairya.gnani.stt_rest import transcribe
from dhairya.gnani.tts import synthesize

log = logging.getLogger(__name__)
RATE = 16000
LEAD_S = 0.3
TTS_MODEL = "timbre-v2.5"
# A gap this long inside one group means the voice read it word by word, as the
# v3.0 voices do, which no caller does. Shorter unplanned pauses (after "mera
# number hai", say) are kept: they are natural, and they make the set harder.
MAX_INTERNAL_GAP_S = 0.45
# The first calls of each category were used to tune the policy (the pilot of
# 12 Nov). They are reported separately from the rest, which the policy never saw.
DEV_PER_CATEGORY = 12


def longest_internal_gap(samples: np.ndarray, rate: int, threshold: int = 300) -> float:
    loud = np.abs(samples.astype(np.int32)) > threshold
    active = np.convolve(loud, np.ones(rate // 50), "same") > 0
    edges = np.flatnonzero(np.diff(active.astype(np.int8)))
    quiet_runs = [b - a for a, b in zip(edges[:-1], edges[1:], strict=False) if not active[a + 1]]
    return max(quiet_runs, default=0) / rate


def select(scripts: list[Script], per_category: int | None) -> list[Script]:
    if per_category is None:
        return scripts
    seen: dict[str, int] = {}
    out = []
    for script in scripts:
        seen[script.category] = seen.get(script.category, 0) + 1
        if seen[script.category] <= per_category:
            out.append(script)
    return out


def audio_dir(cfg: Settings) -> Path:
    return cfg.data_dir / "audio"


def render_one(cfg: Settings, script: Script) -> dict:
    """Write <id>.wav and <id>.json. Returns the metadata (with "dropped" if unusable)."""
    meta_path = audio_dir(cfg) / f"{script.id}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    meta: dict = {"script": asdict(script), "rate": RATE}
    pieces = [silence(LEAD_S, RATE)]
    bounds: list[tuple[float, float]] = []
    at = LEAD_S
    worst_gap = 0.0
    for i, group in enumerate(script.groups):
        clip, _ = synthesize(cfg, group, script.voice, sample_rate=RATE, model=TTS_MODEL)
        clip = trim_silence(clip, RATE)
        worst_gap = max(worst_gap, longest_internal_gap(clip, RATE))
        bounds.append((round(at, 4), round(at + len(clip) / RATE, 4)))
        pieces.append(clip)
        at += len(clip) / RATE
        if i < len(script.pauses_s):
            pieces.append(silence(script.pauses_s[i], RATE))
            at += script.pauses_s[i]
    audio = np.concatenate(pieces)
    meta |= {
        "group_bounds": bounds,
        "speech_end": bounds[-1][1],
        "longest_internal_gap_s": round(worst_gap, 3),
    }
    if worst_gap > MAX_INTERNAL_GAP_S:
        meta["dropped"] = f"voice paused {worst_gap:.2f} s inside a group"
    else:
        try:
            resp = transcribe(cfg, audio, RATE, language_code="hi-IN", fmt="transcribe")
            meta["rest_whole_call"] = str(resp.get("transcript", ""))
        except (GnaniAuthError, GnaniCreditError):
            raise
        except GnaniError as exc:
            meta["rest_whole_call_error"] = str(exc)
        (audio_dir(cfg) / f"{script.id}.wav").write_bytes(pcm_to_wav(audio, RATE))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-category", type=int, default=None)
    args = parser.parse_args()
    cfg = settings()
    audio_dir(cfg).mkdir(parents=True, exist_ok=True)
    chosen = select(load(scripts_path()), args.per_category)
    dropped = failed = 0
    for n, script in enumerate(chosen, 1):
        try:
            meta = render_one(cfg, script)
        except (GnaniAuthError, GnaniCreditError) as exc:
            print(f"Stopped: {exc}")
            raise SystemExit(1) from exc
        except GnaniError as exc:
            failed += 1
            print(f"{script.id}: speech synthesis failed: {exc}")
            continue
        dropped += "dropped" in meta
        if n % 10 == 0:
            print(f"rendered {n} of {len(chosen)}", flush=True)
    usable = len(chosen) - dropped - failed
    print(f"{len(chosen)} scripts: {usable} usable, {dropped} dropped, {failed} failed")


if __name__ == "__main__":
    main()
