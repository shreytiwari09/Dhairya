"""Record the agent's spoken lines for the demo page with Timbre.

The page plays these when an agent answers: the fixed-timer agent's early
"thank you" and Dhairya's read-back of each exported call's value. Spends a
few Timbre credits once; responses are cached.

    uv run python -m dhairya.demo.voices
"""

from __future__ import annotations

import json

from dhairya.config import ROOT, settings
from dhairya.entities.speak import spoken_value
from dhairya.gnani.audio import pcm_to_wav, trim_silence
from dhairya.gnani.tts import synthesize

AGENT_VOICE = "Omkar"  # a male v2.5 voice, distinct from the female test callers
TTS_MODEL = "timbre-v2.5"
RATE = 16000
CUT_IN = "जी, धन्यवाद! नोट कर लिया है।"
NUDGE = "जी, आगे बोलिए।"


def main() -> None:
    cfg = settings()
    demo = ROOT / "demo"
    out = demo / "audio" / "agent"
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads((demo / "data.json").read_text())

    lines = {"cutin": CUT_IN, "nudge": NUDGE}
    for call in data["calls"]:
        lines[f"readback-{call['id']}"] = f"{spoken_value(call['slot'], call['truth'])}। सही है?"

    durations = {}
    for name, text in lines.items():
        samples, rate = synthesize(cfg, text, AGENT_VOICE, sample_rate=RATE, model=TTS_MODEL)
        samples = trim_silence(samples, rate)
        (out / f"{name}.wav").write_bytes(pcm_to_wav(samples, rate))
        durations[name] = {"text": text, "duration_s": round(len(samples) / rate, 3)}

    (out / "lines.json").write_text(json.dumps(durations, ensure_ascii=False, indent=1))
    print(f"{len(lines)} agent lines written to {out}")


if __name__ == "__main__":
    main()
