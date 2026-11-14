"""Write results/RESULTS.md from the saved traces.

uv run python -m dhairya.bench.report
"""

from __future__ import annotations

import json
from collections import defaultdict

from dhairya.bench.metrics import CallScore, Summary, summarise
from dhairya.bench.record import FORMAT, WINDOW_MS, trace_dir
from dhairya.bench.render import DEV_PER_CATEGORY, TTS_MODEL, audio_dir, select
from dhairya.bench.replay import (
    SLOTS,
    TIMERS_MS,
    load_traces,
    score_all,
    score_live_timer,
    score_phone,
    score_replayed,
    write_csv,
)
from dhairya.bench.scripts import load, scripts_path
from dhairya.config import Settings, settings

LABELS = {"dhairya": "**Dhairya**", "smart_turn": "Smart Turn v3.2"}


def _label(policy: str) -> str:
    if policy in LABELS:
        return LABELS[policy]
    return f"Fixed timer {policy.removeprefix('fixed_').removesuffix('ms')} ms"


def _pct(k: int, n: int) -> str:
    return f"{100 * k / n:.0f}%" if n else "-"


def _ci(interval: tuple[float, float]) -> str:
    return f"{100 * interval[0]:.0f}-{100 * interval[1]:.0f}%"


def _s(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "-"


def _table(summaries: list[Summary]) -> list[str]:
    lines = [
        "| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | "
        "Wait P50 (s) | Wait P95 (s) | Nudges |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {_label(s.policy)} | {s.n} | {_pct(s.cut_ins, s.n)} | {_ci(s.cut_in_ci)} | "
            f"{_pct(s.correct, s.n)} | {_ci(s.correct_ci)} | {_s(s.delay_p50)} | {_s(s.delay_p95)} | "
            f"{s.nudges} |"
        )
    return lines


def _by_policy(scores: list[CallScore]) -> list[Summary]:
    grouped: dict[str, list[CallScore]] = defaultdict(list)
    for score in scores:
        grouped[score.policy].append(score)
    return [summarise(policy, group) for policy, group in grouped.items()]


def _rest_reference(traces: list[dict]) -> tuple[int, int]:
    """Whole-call REST transcription read by the same parser: what a perfect wait could get."""
    right = total = 0
    for trace in traces:
        if "rest_whole_call" not in trace:
            continue
        script = trace["script"]
        total += 1
        right += SLOTS[script["slot"]].evaluate(trace["rest_whole_call"]).value == script["truth"]
    return right, total


def _phone_section(cfg: Settings, dev_ids: set[str]) -> list[str]:
    """Held-out calls replayed as a telephone line would deliver them. Empty if not recorded."""
    phone = score_phone(cfg)
    if not phone:
        return []
    held_out = [s for s in phone if s.script_id not in dev_ids]
    if not held_out:
        return []
    ids = [s.id for s in load(scripts_path())]
    recorded = len(load_traces(cfg, WINDOW_MS, "phone8k"))
    failed = sum(
        1
        for i in ids
        for path in [trace_dir(cfg, WINDOW_MS, "phone8k") / f"{i}.json"]
        if path.exists() and "error" in json.loads(path.read_text())
    )
    return [
        "",
        "## Phone line: 8 kHz G.711 mu-law",
        "",
        "The same calls were resampled to 8 kHz, passed through G.711 mu-law and streamed with "
        "`x-sample-rate: 8000`; the fixed timers are live runs at their own window, Dhairya runs "
        "over the 200 ms recording.",
        "",
        *_table(_by_policy(held_out)),
        "",
        f"Of {len(ids)} calls, {recorded} were recorded in this condition at 200 ms and "
        f"{failed} failed.",
    ]


def build(cfg: Settings) -> str:
    traces = load_traces(cfg)
    scores, live = score_all(cfg)
    replayed_all = score_replayed(cfg)
    write_csv(scores, cfg.results_dir / "scores.csv")
    metas = [json.loads(p.read_text()) for p in sorted(audio_dir(cfg).glob("*.json"))]
    dropped = [m for m in metas if "dropped" in m]
    categories = sorted({s.category for s in scores})
    voices = sorted({t["script"]["voice"] for t in traces})
    pauses = sorted({p for t in traces for p in t["script"]["pauses_s"]})
    rest_right, rest_total = _rest_reference(traces)

    lines = [
        "# Results",
        "",
        f"{len(traces)} synthetic calls through Prisma v3.0 realtime (`format: {FORMAT}`, `hi-IN`).",
        "",
        "- **Fixed timers** are live runs: each call was played with Prisma's own silence window "
        "(`x-min-silence-ms`) set to the timer value, and the first finished segment is the end "
        "of the turn. "
        + (
            "Settings not yet recorded live are replayed instead: "
            + ", ".join(f"{ms} ms" for ms in TIMERS_MS if ms not in live)
            + "."
            if set(TIMERS_MS) - live
            else "All six settings were recorded live."
        ),
        f"- **Dhairya** runs over one recording per call made at its own setting, a {WINDOW_MS} ms "
        "window. Its decisions are computed from those recorded events.",
        "",
        "- **Cut in early:** the policy ended the turn before the caller's last sample.",
        "- **Value correct:** the value held when the policy decided equals the script's value.",
        "- **Wait:** time from the caller's last sample to the decision, for turns not cut in.",
        "- **Nudges:** the policy gave up waiting and would prompt the caller.",
        "",
    ]
    dev_ids = {s.id for s in select(load(scripts_path()), DEV_PER_CATEGORY)}
    held_out = [s for s in scores if s.script_id not in dev_ids]
    dev = [s for s in scores if s.script_id in dev_ids]
    if held_out:
        lines += [
            "## Held-out calls",
            "",
            "The policy and parser were frozen before these calls were recorded. This is the result to quote.",
            "",
            *_table(_by_policy(held_out)),
        ]
        for category in categories:
            subset = [s for s in held_out if s.category == category]
            if subset:
                lines += ["", f"### Held-out: {category}", "", *_table(_by_policy(subset))]
    lines += _phone_section(cfg, dev_ids)
    lines += [
        "",
        "## Development calls",
        "",
        f"The first {DEV_PER_CATEGORY} scripts of each category. The amount logic and one "
        "misheard-word rule were changed after seeing these, so these numbers flatter the policy.",
        "",
        *_table(_by_policy(dev)),
    ]
    for category in categories:
        subset = [s for s in dev if s.category == category]
        if subset:
            lines += ["", f"### Development: {category}", "", *_table(_by_policy(subset))]

    agreement = []
    for window in sorted(live):
        own = score_live_timer(cfg, window)
        ids = {x.script_id for x in own}
        again = [x for x in replayed_all if x.policy == f"fixed_{window}ms" and x.script_id in ids]
        a, b = summarise("live", own), summarise("replayed", again)
        agreement.append(
            f"| {window} | {a.n} | {_pct(a.cut_ins, a.n)} | {_pct(b.cut_ins, b.n)} | "
            f"{_pct(a.correct, a.n)} | {_pct(b.correct, b.n)} | {_s(a.delay_p50)} | {_s(b.delay_p50)} |"
        )
    if agreement:
        lines += [
            "",
            "## Does replaying a timer match running it live?",
            "",
            "Each timer can also be replayed from the 200 ms recording: wait the rest of the timer "
            "after a segment's text arrives, and cancel if speech resumes. The table compares that "
            "replay with the live runs used above. The replay is harsher on a timer when a pause "
            "is exactly as long as the timer.",
            "",
            "| Timer ms | Calls | Cut in early: live | replayed | Value correct: live | replayed | "
            "Wait P50 (s): live | replayed |",
            "|---|---|---|---|---|---|---|---|",
            *agreement,
        ]

    lines += [
        "",
        "## Reference: whole-call REST transcription",
        "",
        f"Transcribing each complete call through REST in Transcribe mode and reading it with the "
        f"same parser gives the right value in {rest_right} of {rest_total} calls "
        f"({_pct(rest_right, rest_total)}). This is the ceiling for any policy that waits for the "
        "whole turn; misses here are speech-synthesis, transcription or parser errors, not timing.",
        "",
        "## Dhairya's misses",
        "",
        "| Call | Said | Truth | Heard value | Outcome |",
        "|---|---|---|---|---|",
    ]
    by_id = {t["script"]["id"]: t for t in traces}
    for s in scores:
        if s.policy == "dhairya" and (not s.correct or s.cut_in or s.decision != "end_turn"):
            script = by_id[s.script_id]["script"]
            said = " / ".join(
                e["text"] for e in by_id[s.script_id]["events"] if e["kind"] == "transcript"
            )
            outcome = "cut in" if s.cut_in else s.decision
            lines.append(
                f"| {s.script_id} | {said} | {script['truth']} | {s.heard_value} | {outcome} |"
            )

    lines += [
        "",
        "## Test set",
        "",
        f"- Calls recorded: {len(traces)}. Scripts dropped because the voice paused inside a "
        f"group: {len(dropped)}.",
        f"- Caller voices: {', '.join(voices)} (`{TTS_MODEL}`). Pauses between groups: "
        f"{', '.join(str(p) for p in pauses)} s, drawn at random per script.",
        "- Scripts come from a seeded generator (`data/scripts/scripts.json`). All values are made up.",
        "",
        "## Limits",
        "",
        "- Callers are synthetic. Each breath group is synthesised separately and joined with "
        "silence, so pause lengths are exact but intonation is not natural.",
        "- Timbre generates the speech that Prisma transcribes.",
        "- Dhairya's row is computed from recorded events, not from a live conversation. The live "
        "agent exercises the same code in real time.",
        "- Dhairya is told which kind of value to expect, as an agent that asked the question "
        "would know.",
        "- Intervals are Wilson 95% intervals on each row; no paired test between policies yet.",
    ]
    report = "\n".join(lines) + "\n"
    (cfg.results_dir / "RESULTS.md").write_text(report)
    return report


def main() -> None:
    print(build(settings()))


if __name__ == "__main__":
    main()
