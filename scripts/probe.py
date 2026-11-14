"""Phase 0 probe: does Prisma's realtime stream support the Dhairya design?

Spends a small number of credits. Writes results/PROBE.md and
results/probe_raw.json. Finished stream runs are saved and never repeated, so
the script can be re-run after a failure.

    uv run python scripts/probe.py                 # everything
    uv run python scripts/probe.py --stage rest    # one stage: rest|survey|repeat|commit|concurrency
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from dhairya.config import Settings, settings
from dhairya.entities.numbers import digit_string
from dhairya.gnani.audio import silence, trim_silence
from dhairya.gnani.errors import GnaniAuthError, GnaniCreditError
from dhairya.gnani.stream import run_stream
from dhairya.gnani.stt_rest import transcribe
from dhairya.gnani.tts import synthesize

RATE = 16000
# Timbre v3.0 voices read Devanagari digit words with 0.3-0.5 s gaps between words,
# which no caller does. This v2.5 voice reads a group fluently.
VOICE = "Nalini"
TTS_MODEL = "timbre-v2.5"
FINAL_KINDS = ("transcript", "final_transcript")
DIGIT_WORDS = ["शून्य", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ"]
FORMATS = ["verbatim", "codemix", "transcribe"]
WINDOWS_MS = [200, 300, 500]
PAUSES_S = [0.6, 0.8, 1.0]
STAGES = ["rest", "survey", "repeat", "relisten", "partials", "commit", "concurrency"]


def synthetic_numbers(count: int) -> list[str]:
    """Seeded, made-up 10-digit numbers. Not real phone numbers."""
    rng = random.Random(7)
    numbers = ["9876543210"]
    while len(numbers) < count:
        numbers.append(
            str(rng.choice("6789")) + "".join(rng.choice("0123456789") for _ in range(9))
        )
    return numbers


def spoken(digits: str) -> str:
    return " ".join(DIGIT_WORDS[int(d)] for d in digits)


def build_call(cfg: Settings, number: str, pause_s: float) -> tuple[np.ndarray, float, float]:
    """Two spoken groups of five digits with an exact pause between them.

    Returns (audio, time the pause starts, time speech ends).
    """
    first, _ = synthesize(cfg, spoken(number[:5]), VOICE, sample_rate=RATE, model=TTS_MODEL)
    second, _ = synthesize(cfg, spoken(number[5:]), VOICE, sample_rate=RATE, model=TTS_MODEL)
    first, second = trim_silence(first, RATE), trim_silence(second, RATE)
    lead = silence(0.3, RATE)
    audio = np.concatenate([lead, first, silence(pause_s, RATE), second])
    pause_start = (len(lead) + len(first)) / RATE
    return audio, pause_start, len(audio) / RATE


class Raw:
    """Results on disk, keyed by run name, so finished runs are not repeated."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}

    def has(self, key: str) -> bool:
        return key in self.data and "error" not in self.data[key]

    def put(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1))


def stream_once(
    cfg: Settings,
    raw: Raw,
    key: str,
    number: str,
    pause_s: float,
    window_ms: int,
    fmt: str,
    commit_after_pause_s: float | None = None,
) -> dict[str, Any]:
    if raw.has(key):
        return raw.data[key]
    audio, pause_start, speech_end = build_call(cfg, number, pause_s)
    commit_at = [pause_start + commit_after_pause_s] if commit_after_pause_s is not None else []
    try:
        events = asyncio.run(
            run_stream(cfg, audio, RATE, fmt=fmt, min_silence_ms=window_ms, commit_at=commit_at)
        )
    except (GnaniAuthError, GnaniCreditError):
        raise
    except Exception as exc:  # recorded, not hidden: the report lists failed runs
        result = {"error": f"{type(exc).__name__}: {exc}"}
        raw.put(key, result)
        return result
    segments = [(round(e.t, 3), e.text) for e in events if e.kind in FINAL_KINDS]
    heard = digit_string(" ".join(text for _, text in segments))
    after_pause = [t for t, _ in segments if t > pause_start]
    result = {
        "number": number,
        "pause_s": pause_s,
        "window_ms": window_ms,
        "format": fmt,
        "pause_start": round(pause_start, 3),
        "speech_end": round(speech_end, 3),
        "segments": segments,
        "heard_digits": heard,
        "correct": heard == number,
        # How soon after the caller paused did the first group's text reach us?
        "text_after_pause_s": round(after_pause[0] - pause_start, 3) if after_pause else None,
        "errors": [e.raw for e in events if e.kind == "error"],
        "events": [{**asdict(e), "t": round(e.t, 3)} for e in events],
    }
    raw.put(key, result)
    return result


def stage_rest(cfg: Settings, raw: Raw) -> None:
    audio, _, _ = build_call(cfg, "9876543210", 0.8)
    for fmt in FORMATS:
        key = f"rest/{fmt}"
        if raw.has(key):
            continue
        try:
            resp = transcribe(cfg, audio, RATE, fmt=fmt)
            text = str(resp.get("transcript", ""))
            raw.put(
                key,
                {
                    "transcript": text,
                    "heard_digits": digit_string(text),
                    "correct": digit_string(text) == "9876543210",
                    "response": resp,
                },
            )
        except (GnaniAuthError, GnaniCreditError):
            raise
        except Exception as exc:
            raw.put(key, {"error": f"{type(exc).__name__}: {exc}"})


def stage_survey(cfg: Settings, raw: Raw) -> None:
    for window in WINDOWS_MS:
        for fmt in FORMATS:
            stream_once(cfg, raw, f"survey/{window}/{fmt}", "9876543210", 0.8, window, fmt)


def best_setting(raw: Raw) -> tuple[int, str]:
    """Correct runs first, then the fastest text arrival. Falls back to 300 ms verbatim."""
    runs = [v for k, v in raw.data.items() if k.startswith("survey/") and "error" not in v]
    good = [r for r in runs if r["correct"] and r["text_after_pause_s"] is not None]
    if not good:
        return 300, "verbatim"
    top = min(good, key=lambda r: r["text_after_pause_s"])
    return top["window_ms"], top["format"]


def stage_repeat(cfg: Settings, raw: Raw, count: int) -> None:
    window, fmt = best_setting(raw)
    for i, number in enumerate(synthetic_numbers(count)):
        pause = PAUSES_S[i % len(PAUSES_S)]
        stream_once(cfg, raw, f"repeat/{window}/{fmt}/{i}", number, pause, window, fmt)


def stage_commit(cfg: Settings, raw: Raw) -> None:
    # Server window at its maximum, so any text arriving sooner is due to the commit frame.
    stream_once(
        cfg, raw, "commit/2000", "9876543210", 1.0, 2000, "verbatim", commit_after_pause_s=0.25
    )


def stage_concurrency(cfg: Settings, raw: Raw) -> None:
    if raw.has("concurrency"):
        return
    audio, _, _ = build_call(cfg, "9876543210", 0.6)

    async def both() -> list[Any]:
        runs = [run_stream(cfg, audio, RATE, min_silence_ms=300) for _ in range(2)]
        return await asyncio.gather(*runs, return_exceptions=True)

    outcomes = asyncio.run(both())
    raw.put(
        "concurrency",
        {
            "streams": [
                f"failed: {type(o).__name__}: {o}"
                if isinstance(o, Exception)
                else f"ok, {sum(1 for e in o if e.kind == 'transcript')} transcripts, "
                f"{sum(1 for e in o if e.kind == 'error')} error events"
                for o in outcomes
            ],
            "both_ok": all(
                not isinstance(o, Exception) and not any(e.kind == "error" for e in o)
                for o in outcomes
            ),
        },
    )


def stage_relisten(cfg: Settings, raw: Raw, count: int) -> None:
    """At the pause, send the audio so far to REST. Is the first group right, and how fast?"""
    for i, number in enumerate(synthetic_numbers(count)):
        key = f"relisten/{i}"
        if raw.has(key):
            continue
        audio, pause_start, _ = build_call(cfg, number, 0.8)
        so_far = audio[: int((pause_start + 0.3) * RATE)]
        try:
            started = time.monotonic()
            resp = transcribe(cfg, so_far, RATE, language_code="hi-IN", fmt="transcribe")
            took = time.monotonic() - started
            text = str(resp.get("transcript", ""))
            raw.put(
                key,
                {
                    "number": number,
                    "transcript": text,
                    "heard_digits": digit_string(text),
                    "correct": digit_string(text) == number[:5],
                    "round_trip_s": round(took, 3),
                    "server_s": resp.get("end_to_end_latency"),
                },
            )
        except (GnaniAuthError, GnaniCreditError):
            raise
        except Exception as exc:
            raw.put(key, {"error": f"{type(exc).__name__}: {exc}"})


def stage_partials(cfg: Settings, raw: Raw, count: int) -> None:
    """Long silence window with the undocumented partial results switched on."""
    for i, number in enumerate(synthetic_numbers(count)):
        key = f"partials/{i}"
        if raw.has(key):
            continue
        audio, pause_start, speech_end = build_call(cfg, number, 0.8)
        try:
            events = asyncio.run(
                run_stream(cfg, audio, RATE, min_silence_ms=1500, partials=True, tail_silence_s=3.0)
            )
        except (GnaniAuthError, GnaniCreditError):
            raise
        except Exception as exc:
            raw.put(key, {"error": f"{type(exc).__name__}: {exc}"})
            continue
        partials = [(round(e.t, 3), e.text) for e in events if e.kind == "partial_transcript"]
        finals = [(round(e.t, 3), e.text) for e in events if e.kind in FINAL_KINDS]
        first_half = next((t for t, text in partials if digit_string(text) == number[:5]), None)
        full = next((t for t, text in partials if digit_string(text) == number), None)
        final_digits = digit_string(" ".join(text for _, text in finals))
        raw.put(
            key,
            {
                "number": number,
                "pause_start": round(pause_start, 3),
                "speech_end": round(speech_end, 3),
                "partials": partials,
                "finals": finals,
                "first_group_after_pause_s": round(first_half - pause_start, 3)
                if first_half
                else None,
                "full_number_after_speech_end_s": round(full - speech_end, 3) if full else None,
                "final_after_speech_end_s": round(finals[-1][0] - speech_end, 3)
                if finals
                else None,
                "final_correct": final_digits == number,
                "ever_wrong_partial": any(
                    not number.startswith(digit_string(text))
                    for _, text in partials
                    if digit_string(text)
                ),
            },
        )


def verdict(ok: bool | None) -> str:
    return "not run" if ok is None else ("PASS" if ok else "FAIL")


def write_report(cfg: Settings, raw: Raw) -> str:
    d = raw.data
    rest = {k.split("/")[1]: v for k, v in d.items() if k.startswith("rest/")}
    survey = [v | {"key": k} for k, v in d.items() if k.startswith("survey/")]
    repeat = [v | {"key": k} for k, v in d.items() if k.startswith("repeat/")]
    commit = d.get("commit/2000")
    conc = d.get("concurrency")

    ok_survey = [r for r in survey if "error" not in r]
    ok_repeat = [r for r in repeat if "error" not in r]
    correct = sum(1 for r in ok_repeat if r["correct"])
    arrivals = [r["text_after_pause_s"] for r in ok_repeat if r["text_after_pause_s"] is not None]

    gate1 = (
        (bool(rest) and all("error" not in v for v in rest.values()) and bool(ok_survey))
        if rest or survey
        else None
    )
    gate2 = (correct >= 0.8 * len(repeat)) if repeat else None
    gate3 = (statistics.median(arrivals) <= 0.6) if arrivals else (False if repeat else None)
    gate4 = None
    if commit is not None:
        t = commit.get("text_after_pause_s")
        gate4 = "error" not in commit and t is not None and t < 1.5
    gate5 = conc["both_ok"] if conc else None

    lines = [
        "# Probe results",
        "",
        f"Model `{cfg.stt_model}` for speech-to-text, `{TTS_MODEL}` voice `{VOICE}` for the caller. "
        "Audio is two spoken groups of five digits with a pause of known length between them, 16 kHz.",
        "",
        "## Gates",
        "",
        "| Gate | Question | Result |",
        "|---|---|---|",
        f"| 1 | Key works for REST STT, realtime STT and TTS | {verdict(gate1)} |",
        f"| 2 | Streamed digits correct in at least 8 of 10 calls | {verdict(gate2)}"
        + (f" ({correct} of {len(repeat)})" if repeat else "")
        + " |",
        f"| 3 | First group's text arrives within 0.6 s of the pause starting (median) | {verdict(gate3)}"
        + (f" (median {statistics.median(arrivals):.2f} s)" if arrivals else "")
        + " |",
        f"| 4 | `commit` frame closes the utterance early | {verdict(gate4)} |",
        f"| 5 | Two streams can be open at once | {verdict(gate5)} |",
        "",
        "Gates 1 to 3 decide whether the design stands. Gates 4 and 5 only choose between options.",
        "",
        "## REST transcription of the whole call",
        "",
        "| Format | Transcript | Digits heard | Correct |",
        "|---|---|---|---|",
    ]
    for fmt, v in rest.items():
        if "error" in v:
            lines.append(f"| {fmt} | error: {v['error']} | | |")
        else:
            lines.append(
                f"| {fmt} | {v['transcript']} | {v['heard_digits']} | {'yes' if v['correct'] else 'no'} |"
            )

    lines += [
        "",
        "## Realtime survey: one call, 0.8 s pause, every window and format",
        "",
        "| Window ms | Format | Segments | Digits heard | Correct | Text after pause (s) |",
        "|---|---|---|---|---|---|",
    ]
    for r in survey:
        if "error" in r:
            lines.append(f"| {r['key']} | error: {r['error']} | | | | |")
            continue
        segs = " / ".join(text for _, text in r["segments"]) or "(none)"
        lines.append(
            f"| {r['window_ms']} | {r['format']} | {segs} | {r['heard_digits']} | "
            f"{'yes' if r['correct'] else 'no'} | {r['text_after_pause_s']} |"
        )

    if repeat:
        first = ok_repeat[0] if ok_repeat else None
        setting = f"{first['window_ms']} ms, {first['format']}" if first else "n/a"
        lines += [
            "",
            f"## Realtime repeat: {len(repeat)} different numbers at the best setting ({setting})",
            "",
            "| Number | Pause s | Segments | Digits heard | Correct | Text after pause (s) |",
            "|---|---|---|---|---|---|",
        ]
        for r in repeat:
            if "error" in r:
                lines.append(f"| {r['key']} | error: {r['error']} | | | | |")
                continue
            segs = " / ".join(text for _, text in r["segments"]) or "(none)"
            lines.append(
                f"| {r['number']} | {r['pause_s']} | {segs} | {r['heard_digits']} | "
                f"{'yes' if r['correct'] else 'no'} | {r['text_after_pause_s']} |"
            )

    if commit is not None:
        lines += ["", "## Commit frame", ""]
        if "error" in commit:
            lines.append(f"Run failed: {commit['error']}")
        else:
            lines.append(
                f"Server window 2000 ms, commit sent 0.25 s into a 1.0 s pause. "
                f"First text arrived {commit['text_after_pause_s']} s after the pause began. "
                f"Segments: {' / '.join(text for _, text in commit['segments']) or '(none)'}."
            )
    if conc:
        lines += ["", "## Two streams at once", ""] + [
            f"- Stream {i + 1}: {s}" for i, s in enumerate(conc["streams"])
        ]

    relisten = [v for k, v in d.items() if k.startswith("relisten/") and "error" not in v]
    if relisten:
        trips = [r["round_trip_s"] for r in relisten]
        lines += [
            "",
            "## Re-listen: REST transcription of the audio so far, sent at the pause",
            "",
            f"- First group correct: {sum(1 for r in relisten if r['correct'])} of {len(relisten)}",
            f"- Round trip: median {statistics.median(trips):.2f} s, slowest {max(trips):.2f} s",
            "",
            "| Number | Transcript | Digits heard | Correct | Round trip s |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['number']} | {r['transcript']} | {r['heard_digits']} | {'yes' if r['correct'] else 'no'} | {r['round_trip_s']} |"
            for r in relisten
        ]
    parts = [v for k, v in d.items() if k.startswith("partials/") and "error" not in v]
    if parts:
        lines += [
            "",
            "## Partial results (undocumented `x-partials` header), 1500 ms window",
            "",
            "The docs say the stream sends finished segments only. With the header `x-partials: true` it also "
            "sends `partial_transcript` events with running text.",
            "",
            "| Number | First group shown after pause began (s) | Full number shown after speech ended (s) | "
            "Final after speech ended (s) | Final correct | Any wrong partial |",
            "|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['number']} | {r['first_group_after_pause_s']} | {r['full_number_after_speech_end_s']} | "
            f"{r['final_after_speech_end_s']} | {'yes' if r['final_correct'] else 'no'} | "
            f"{'yes' if r['ever_wrong_partial'] else 'no'} |"
            for r in parts
        ]

    n_stream = len(survey) + len(repeat) + (1 if commit else 0) + (2 if conc else 0)
    lines += [
        "",
        "## Calls made",
        "",
        f"- REST transcriptions: {len(rest) + len(relisten)}",
        f"- Realtime sessions: {n_stream + len(parts)}",
        "- Speech syntheses: see `data/cache/tts/` (one file per distinct clip)",
        "",
        "Credit cost is not returned by the API. Compare the dashboard balance before and after this run.",
        "",
        "Raw events for every run are in `results/probe_raw.json`.",
    ]
    report = "\n".join(lines) + "\n"
    (cfg.results_dir / "PROBE.md").write_text(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--stage", choices=["all", *STAGES], default="all")
    parser.add_argument("--numbers", type=int, default=10, help="calls in the repeat stage")
    args = parser.parse_args()

    cfg = settings()
    if not cfg.api_key:
        print(
            "GNANI_API_KEY is empty. Add your key to the .env file in the project folder, then run again."
        )
        return 2
    cfg.results_dir.mkdir(parents=True, exist_ok=True)
    raw = Raw(cfg.results_dir / "probe_raw.json")
    stages = STAGES if args.stage == "all" else [args.stage]
    try:
        for stage in stages:
            print(f"stage: {stage}", flush=True)
            if stage == "rest":
                stage_rest(cfg, raw)
            elif stage == "survey":
                stage_survey(cfg, raw)
            elif stage == "repeat":
                stage_repeat(cfg, raw, args.numbers)
            elif stage == "relisten":
                stage_relisten(cfg, raw, args.numbers)
            elif stage == "partials":
                stage_partials(cfg, raw, min(args.numbers, 5))
            elif stage == "commit":
                stage_commit(cfg, raw)
            elif stage == "concurrency":
                stage_concurrency(cfg, raw)
    except (GnaniAuthError, GnaniCreditError) as exc:
        print(f"Stopped: {exc}")
        print(write_report(cfg, raw))
        return 1
    print(write_report(cfg, raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
