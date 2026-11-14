"""Play each rendered call through Prisma's realtime stream once and save the events.

This is the only benchmark step that calls Prisma live. Every policy is later
replayed over these traces offline. Finished calls are never recorded again.

    uv run python -m dhairya.bench.record --per-category 12
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dhairya.bench.channel import to_phone_line
from dhairya.bench.render import audio_dir, select
from dhairya.bench.scripts import load, scripts_path
from dhairya.config import Settings, settings
from dhairya.gnani.audio import wav_to_pcm
from dhairya.gnani.errors import GnaniAuthError, GnaniCreditError
from dhairya.gnani.stream import run_stream

WINDOW_MS = 200  # best setting found by the probe
FORMAT = "verbatim"
CONDITIONS = ("clean", "phone8k")


def trace_dir(cfg: Settings, window_ms: int = WINDOW_MS, condition: str = "clean") -> Path:
    """Main traces use the short window. Other windows are live checks of the fixed timers.

    The phone condition keeps every window, 200 included, in its own sub-folder.
    """
    if condition == "phone8k":
        return cfg.data_dir / "traces_phone8k" / str(window_ms)
    if window_ms == WINDOW_MS:
        return cfg.data_dir / "traces"
    return cfg.data_dir / "traces_live" / str(window_ms)


async def record_one(
    cfg: Settings,
    script_id: str,
    gate: asyncio.Semaphore,
    window_ms: int = WINDOW_MS,
    condition: str = "clean",
) -> str:
    out = trace_dir(cfg, window_ms, condition) / f"{script_id}.json"
    if out.exists() and "error" not in json.loads(out.read_text()):
        return "cached"
    meta = json.loads((audio_dir(cfg) / f"{script_id}.json").read_text())
    if "dropped" in meta:
        return "dropped"
    samples, rate = wav_to_pcm((audio_dir(cfg) / f"{script_id}.wav").read_bytes())
    if condition == "phone8k":
        samples, rate = await asyncio.to_thread(to_phone_line, samples, rate)
    async with gate:
        try:
            events = await run_stream(
                cfg, samples, rate, fmt=FORMAT, min_silence_ms=window_ms,
                tail_silence_s=window_ms / 1000 + 1.0, drain_s=1.0,
            )  # fmt: skip
        except (GnaniAuthError, GnaniCreditError):
            raise
        except Exception as exc:  # kept in the trace file and counted in the report
            out.write_text(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
            return "failed"
    trace = meta | {
        "window_ms": window_ms,
        "format": FORMAT,
        "condition": condition,
        "rate": rate,
        "events": [
            {"t": round(e.t, 3), "kind": e.kind, "text": e.text, "raw": e.raw} for e in events
        ],
    }
    out.write_text(json.dumps(trace, ensure_ascii=False, indent=1))
    return "recorded"


async def record_all(
    cfg: Settings,
    ids: list[str],
    concurrency: int,
    window_ms: int = WINDOW_MS,
    condition: str = "clean",
) -> dict[str, int]:
    gate = asyncio.Semaphore(concurrency)
    counts: dict[str, int] = {}
    done = 0

    async def one(script_id: str) -> None:
        nonlocal done
        status = await record_one(cfg, script_id, gate, window_ms, condition)
        counts[status] = counts.get(status, 0) + 1
        done += 1
        if done % 10 == 0:
            print(f"{done} of {len(ids)} done", flush=True)

    await asyncio.gather(*(one(i) for i in ids))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-category", type=int, default=None)
    parser.add_argument(
        "--concurrency", type=int, default=2, help="the probe showed two streams work"
    )
    parser.add_argument(
        "--window", type=int, default=WINDOW_MS,
        help="server silence window in ms; other than 200 records a live fixed-timer check",
    )  # fmt: skip
    parser.add_argument(
        "--condition", choices=CONDITIONS, default="clean",
        help="phone8k plays the calls as an 8 kHz G.711 mu-law telephone line would deliver them",
    )  # fmt: skip
    args = parser.parse_args()
    cfg = settings()
    trace_dir(cfg, args.window, args.condition).mkdir(parents=True, exist_ok=True)
    ids = [s.id for s in select(load(scripts_path()), args.per_category)]
    ids = [i for i in ids if (audio_dir(cfg) / f"{i}.json").exists()]
    try:
        counts = asyncio.run(record_all(cfg, ids, args.concurrency, args.window, args.condition))
    except (GnaniAuthError, GnaniCreditError) as exc:
        print(f"Stopped: {exc}")
        raise SystemExit(1) from exc
    print(counts)


if __name__ == "__main__":
    main()
