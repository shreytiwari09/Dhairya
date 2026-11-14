# SPEC — Dhairya

Technical specification. Read [PRD.md](PRD.md) for what and why, and [hackathon.md](hackathon.md) section 13 for the API reference.

Nothing here has been run. Every Gnani parameter comes from the docs and must be confirmed by the probe (Phase 0) before code depends on it.

---

## 1. Tech stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.11, managed with `uv` | Already installed; audio, WebSocket and statistics libraries are all here |
| Realtime STT client | `websockets`, raw connection | Gnani's Python SDK "does not currently expose VAD tuning", and the silence settings are the point of the project |
| REST calls | `httpx` | Timeouts and retries under our control |
| Audio | `numpy`, `soundfile`, system `ffmpeg` | Splicing with exact silences; 8 kHz mu-law conversion |
| Local pause detection | Silero VAD as an ONNX file, run with `onnxruntime` | No PyTorch install; same pairing Smart Turn uses |
| Baseline turn model | Smart Turn v3.2 (8 MB ONNX, CPU) | Leading open model, supports Hindi, BSD-2-Clause |
| Statistics | `numpy` only | Wilson intervals and paired bootstrap are a few lines each |
| Demo server | FastAPI + `uvicorn`, serving JSON and a WebSocket of run events | The interface is a separate layer on top |
| Demo interface | Decided when the builder supplies the UI skill | The interface must be excellent; the skill sets the front-end approach |
| Tests | `pytest` | Standard |
| Lint and format | `ruff` | One tool |

### Choices I am pushing back on

- **Interface last, and separate.** The builder wants a great interface, and it will be designed with a UI skill supplied later. The back end therefore exposes everything the screen needs as plain data (section 5.7), so the interface can be built in whatever the skill calls for without touching the core. A framework is used only if the skill needs one. No interface work starts before the benchmark produces real numbers.
- **No LLM in the core.** The research report proposed Gemini to judge whether a sentence is complete. That adds 300 to 800 ms and a second key to a decision that must be fast. Smart Turn does the same job locally in tens of milliseconds. Gemini is an optional comparison in Phase 2.
- **No hosted live backend.** A public server would expose the API key or burn the 5,000 credits, and free hosts sleep. Ship a replay demo that plays recorded runs with no key, plus a live mode that runs locally.
- **No Evon.** It is not on the API and needs H100-class hardware.
- **No Gnani Python SDK.** It hides the silence settings on the stream. Use raw WebSocket and HTTP calls everywhere so every parameter is visible.

## 2. Data sources and APIs

All data is synthetic. Mobile numbers are generated with a seed and must not be checked against, or copied from, any real number.

### Gnani (base `https://api.vachana.ai`, header `X-API-Key-ID`)

| Use | Endpoint | Settings |
|---|---|---|
| Live transcription | `wss://api.vachana.ai/stt/v3/stream` | Headers: `x-api-key-id`, `model: prisma-v3.0`, `language_code: hi-IN` (the stream rejects a list), `format: verbatim`, `x-sample-rate: 16000` or `8000`, `x-min-silence-ms`, `keyterms`, `topic`, `previous_text` |
| Second pass | `POST /stt/v3` (multipart) | `audio_file`, `model=prisma-v3.0`, `language_code`, `format=transcribe`; 30 s limit per call |
| Caller voices and read-back | `POST /api/v1/tts/inference` (JSON) | `text`, `voice`, `model`, `language`, `speed` 0.85–1.15, `audio_config` |

Realtime stream rules from the docs:

- Audio is raw PCM, signed 16-bit little-endian, mono, in frames of exactly 1,024 bytes (32 ms at 16 kHz, 64 ms at 8 kHz), sent at real-time pace. Bursting "degrades VAD accuracy".
- Silence settings are fixed for the life of the connection: `x-min-silence-ms` (default 500, range 100–2000), `x-vad-threshold` (0.7), `x-min-speech-ms` (100, or 200 at 8 kHz), `x-min-segment-ms` (120), `x-max-speech-s`.
- Server events: `connected`, `speech_start`, `processing`, `transcript` (`text`, `segment_id`, `segment_index`, `audio_duration_ms`, `latency`, `utterance_id`, `is_final` always true), `error`, `settings_updated`.
- Client JSON frames: `{"type":"commit"}` closes the open utterance at once; `update_settings` changes language, format and hints from the next segment.
- No interim results, word timestamps or confidence. Sessions end at 15 minutes.
- Unknown: credit cost, rate limits, whether two streams may be open together. One documented 429 says "Only 1 active request is allowed at a time".

### Outside models (must be disclosed in the submission)

| Model | Use | Runs |
|---|---|---|
| Smart Turn v3.2 | Baseline, and completeness judge for non-number speech | Locally, ONNX. Input 16 kHz mono, up to 8 s, padded at the start. Follow `inference.py` in `pipecat-ai/smart-turn`. |
| Silero VAD | Finds pauses locally | Locally, ONNX |
| Gemini (optional, Phase 2) | Text completeness comparison | API; model name from `GEMINI_MODEL`, confirm the current fast model at build time |

## 3. Folder structure

```
Gnani.ai_hackathon_project/
├── README.md  LICENSE  docs/ (PRD.md, SPEC.md, DESIGN.md)
├── hackathon.md  research.md  reports/  research_notes/
├── pyproject.toml  .env.example  .gitignore  README.md
├── src/dhairya/
│   ├── config.py              # env vars, constants, paths
│   ├── gnani/
│   │   ├── stream.py          # raw WebSocket client for Prisma realtime
│   │   ├── stt_rest.py        # POST /stt/v3
│   │   ├── tts.py             # Timbre inference
│   │   ├── cache.py           # disk cache keyed by request hash
│   │   └── errors.py          # typed errors, retry policy
│   ├── entities/
│   │   ├── normalize.py       # NFC, Indic-aware text clean-up
│   │   ├── lexicon_hi_en.py   # number words, both scripts, variants
│   │   ├── numbers.py         # words/digits -> canonical digits or value
│   │   └── slots.py           # MobileSlot, OtpSlot, AmountSlot, DateSlot
│   ├── turn/
│   │   ├── types.py           # Trace, StreamEvent, Decision, TurnPolicy
│   │   ├── fixed_timer.py     # baseline
│   │   ├── smart_turn.py      # baseline
│   │   ├── entity_aware.py    # ours
│   │   └── hybrid.py          # ours + Smart Turn for non-number speech
│   ├── agent/session.py       # live loop: stream -> policy -> second pass -> read-back
│   ├── bench/
│   │   ├── scripts.py         # seeded script generator
│   │   ├── render.py          # Timbre clips, splice with known silences
│   │   ├── channel.py         # 8 kHz mu-law, noise
│   │   ├── record.py          # play audio through the stream, save traces
│   │   ├── replay.py          # run every policy over saved traces
│   │   ├── metrics.py         # cut-in, delay, accuracy, intervals
│   │   └── report.py          # results/RESULTS.md and charts
│   └── demo/
│       ├── server.py          # FastAPI: replay and live modes
│       └── static/index.html
├── scripts/probe.py           # Phase 0 go/no-go
├── tests/                     # unit tests, no network
├── data/
│   ├── scripts/               # generated scripts (committed)
│   ├── audio/                 # rendered clips (committed if small)
│   ├── traces/                # recorded stream events (committed)
│   ├── human/                 # self-recorded synthetic clips
│   └── cache/                 # raw API responses (git-ignored)
└── results/                   # RESULTS.md, CSVs, charts (committed)
```

## 4. Screens

### Demo screen

```
+----------------------------------------------------------------------------+
| DHAIRYA   the voice agent that lets you finish your number                 |
| Prisma v3.0 realtime  |  Timbre v3.0  |  [ Replay v ]  [ > Play call 017 ]  |
+----------------------------------------------------------------------------+
| Caller audio   ▁▃▆▇▆▃▁▁▁▁▁▁▁▃▆▇▆▅▃▁      pause 900 ms                       |
|                "nau ath saat chhe paanch"   |   "chaar teen do ek shunya"  |
+--------------------------------------+-------------------------------------+
| FIXED TIMER 500 ms                   | DHAIRYA                             |
|                                      |                                     |
| heard:  98765                        | heard:  98765  (5 of 10, waiting)   |
| x  CUT IN at 0.50 s into the pause   | heard:  98765 43210  (10 of 10)     |
|                                      | ok  turn closed 0.31 s after speech |
| saved:  98765        WRONG           | saved:  98765 43210     CORRECT     |
| agent: "Dhanyavaad, number mil gaya" | agent: "9876543210, sahi hai?"      |
+--------------------------------------+-------------------------------------+
| Whole test set (N = ...)   cut-in rate   delay P50 / P95   numbers correct |
|  Fixed 500 ms                   ..%          ... / ... ms        ..%       |
|  Fixed 1500 ms                  ..%          ... / ... ms        ..%       |
|  Smart Turn v3.2                ..%          ... / ... ms        ..%       |
|  Dhairya                     ..%          ... / ... ms        ..%       |
+----------------------------------------------------------------------------+
```

### Results screen (same page, below)

```
+----------------------------------------------------------------------------+
| Cut-in rate vs delay                                                       |
|  cut-in %                                                                  |
|   40 | o 300                                                               |
|   30 |    o 500                                                            |
|   20 |        o 700                                                        |
|   10 |              o 1000        * Smart Turn                             |
|    0 | # Dhairya                       o 1500        o 2000             |
|      +---------------------------------------------------------- delay ms  |
| By category:  Mobile | OTP/PIN | Amount | Date | Plain sentence            |
| By condition: 16 kHz clean | 8 kHz phone | Human clips                     |
| Ten worst failures: [play] script, heard, expected, policy                 |
+----------------------------------------------------------------------------+
```

## 5. Components

### 5.1 Core types (`turn/types.py`)

```python
@dataclass(frozen=True)
class StreamEvent:
    t: float  # seconds on the client monotonic clock, from audio start
    kind: str  # speech_start | processing | transcript | error
    text: str = ""
    segment_index: int = -1
    latency_ms: float = 0.0


@dataclass(frozen=True)
class Trace:
    utterance_id: str
    events: list[StreamEvent]
    audio_path: str
    truth: GroundTruth  # canonical value, category, true end time, pause list


class Decision(Enum):
    WAIT = 1
    END_TURN = 2
    NUDGE = 3  # hold cap reached: prompt the caller


class TurnPolicy(Protocol):
    name: str

    def reset(self, expected: SlotSpec | None) -> None: ...
    def on_event(self, ev: StreamEvent) -> Decision: ...
    def on_tick(self, t: float) -> Decision: ...  # called every 20 ms
```

Policies are pure: no network and no clock of their own. The same policy code runs live and over saved traces.

### 5.2 Entity engine (`entities/`)

- `normalize.py`: Unicode NFC, strip punctuation, lower-case Latin, keep Devanagari marks. Do not use Whisper's normaliser; it breaks Devanagari words.
- `numbers.py`: turns a token stream into digits or a value. Must handle:
  - Hindi 0–99 (all irregular), in Devanagari and common Latin spellings ("chhe"/"che"/"chha", "saat"/"sat");
  - English number words and ASCII and Devanagari digits;
  - "double seven", "triple nine";
  - digits read in pairs: in a mobile number or OTP, a word from 10 to 99 contributes two digits ("ninyanve" gives 9 9);
  - multipliers sau, hazaar, lakh, crore; "dedh", "dhai", "sadhe", "sava", "paune".
- `slots.py`: each slot takes text so far and returns `COMPLETE`, `INCOMPLETE` or `OPEN`.

| Slot | Complete when | Notes |
|---|---|---|
| Mobile | 10 digits, first digit 6–9 | Count-based, strong |
| OTP / PIN | Expected length reached (4 or 6) | Count-based, strong |
| Amount | A unit word follows, or lower-order parts are present | "teen hazaar" alone is `OPEN`: valid but may continue |
| Date | Day and month both present | Day alone is `INCOMPLETE`; year is optional |

### 5.3 Our policy (`turn/entity_aware.py`)

1. The agent knows what it asked for, so it passes the expected slot.
2. On each `transcript` event, append the text and ask the slot for its state.
3. `COMPLETE` → `END_TURN` immediately.
4. `INCOMPLETE` → `WAIT`. If nothing new arrives within `HOLD_CAP_S` (4.0), return `NUDGE`.
5. `OPEN` → `WAIT` for `GRACE_MS` (600), then `END_TURN`.
6. No slot expected, or the text contains no number → defer to the fallback (fixed timer in `entity_aware`, Smart Turn in `hybrid`).

The stream runs with a short server window (`x-min-silence-ms` about 200–300, set by the probe). The alternative, a long server window with the client sending `commit` at each local pause, is tested in the probe; use whichever gives cleaner digits.

### 5.4 Baselines

- `fixed_timer.py`: ends the turn when silence after a segment reaches T. T in 300, 500, 700, 1000, 1500, 2000 ms.
- `smart_turn.py`: at every local pause of 200 ms or more, run Smart Turn on the turn audio so far; end the turn if it says complete.

Fixed timers are replayed from traces recorded with a short window, because true pause lengths are known. Confirm the replay against live runs at 500 and 1000 ms on a subset, and report the agreement.

### 5.5 Live agent (`agent/session.py`)

Ask for a value → stream audio → policy decides → on `END_TURN`, send the whole turn's audio to `POST /stt/v3` with `format=transcribe` → compare with the streamed value → Timbre reads back the value, or asks again if the two disagree.

Hints sent to Prisma: `previous_text` is the agent's question, `topic` names the task, `keyterms` holds number words that the probe shows are misheard.

### 5.6 Benchmark

**Scripts.** Seeded generator. Categories: mobile, OTP/PIN, amount, date, plain complete sentence, plain incomplete sentence. Grouping patterns for mobile numbers: 5-5, 3-3-4, 2-2-2-2-2, with and without "double". Start with about 200 Hinglish utterances; the probe's credit reading sets the final size.

**Audio, two builds.**

| Build | How | Strength | Weakness |
|---|---|---|---|
| Spliced | Each group rendered by Timbre separately, joined with silences of exact length | True end time and pause lengths known to the sample | Each group ends with sentence-final intonation, which is unnatural and unfair to audio-based models |
| Tagged | Whole line rendered once using Timbre v3.0 pause tags and `speed` | Natural intonation | Pause positions must be measured from the audio |

Report both. Pause lengths are swept from 300 to 1500 ms, not assumed. Several Timbre voices.

**Pre-flight.** Every rendered clip is transcribed once through REST and checked against its script. Clips Timbre misspoke are dropped and listed.

**Conditions.** 16 kHz clean (P0); 8 kHz G.711 mu-law (P1); added noise (P2); 30–50 clips of the builder reading the same synthetic scripts (P1).

**Metrics.**

- Premature cut-in rate: the turn ended before the true end of speech.
- Delay: true end of speech to `END_TURN`, P50 and P95, client clock. Only for turns not cut in.
- Entity accuracy: exact match of the canonical value, by category.
- Nudge rate.
- Proportions with Wilson 95% intervals. Method differences with a paired bootstrap over utterances, blocked by voice.

**Output.** `results/RESULTS.md` with model versions, seeds, sample sizes, credits spent, the ten worst failures with audio paths, and a limits section.

### 5.7 Demo data contract (`demo/server.py`)

The interface reads only these, so it can be redesigned freely.

| Route | Returns |
|---|---|
| `GET /api/calls` | List of recorded calls: id, category, script text, language, condition |
| `GET /api/calls/{id}` | Audio URL, waveform peaks, true pauses, and for each policy the timeline of events (heard text, slot progress, decision, time) and the saved value |
| `GET /api/results` | The benchmark table and chart points, by policy, category and condition |
| `WS /api/live` | Live mode only: the same timeline events as they happen |

## 6. Design system

**Placeholder.** The builder will supply a UI skill, and the interface must be excellent. When the skill arrives, it replaces the tokens below; load it before writing any interface code.

These requirements stay whatever the design:

- The side-by-side call is the first thing on screen and is understood in 20 seconds.
- Readable in a phone-sized video: captured values large, timings visible.
- Words accompany every colour ("WRONG", "CORRECT").
- Every number on screen comes from the benchmark files, never typed in by hand.
- Works at phone width.

Starting tokens, to be replaced:

| Token | Value | Use |
|---|---|---|
| Background | `#0F1216` | Page |
| Panel | `#181D24` | Lanes, table |
| Text | `#E8ECF1` | Body |
| Muted | `#8B95A5` | Labels |
| Wrong | `#FF5A5F` | Cut-in, wrong value |
| Right | `#2ECC71` | Correct value |
| Accent | `#4DA3FF` | Our lane heading, buttons |

- Type: system UI font for text; `ui-monospace` for digits and timings. Captured values at 28 px or larger.

## 7. Environment variables

| Name | Required | Default | Purpose |
|---|---|---|---|
| `GNANI_API_KEY` | Yes for live runs | none | Sent as `X-API-Key-ID` |
| `GNANI_BASE_URL` | No | `https://api.vachana.ai` | |
| `GNANI_STT_MODEL` | No | `prisma-v3.0` | |
| `GNANI_TTS_MODEL` | No | `timbre-v3.0` | A voice works only with its own model |
| `DHAIRYA_MIN_SILENCE_MS` | No | `200` (set by probe) | Server window for our policy |
| `DHAIRYA_HOLD_CAP_S` | No | `4.0` | Longest wait before a nudge |
| `DHAIRYA_GRACE_MS` | No | `600` | Wait after an open-ended amount or date |
| `DHAIRYA_DATA_DIR` | No | `./data` | |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | No | none | Phase 2 comparison only |

`.env` is git-ignored. `.env.example` lists names with empty values.

## 8. Deployment

1. Public GitHub repository with the code, scripts, traces and results.
2. Replay demo published as a static page (GitHub Pages) from recorded runs. No key, no server.
3. Live mode runs locally with the builder's key and is what the video records.
4. Video of 60 seconds or less. Post on LinkedIn (and X). Submit the Microsoft Form.

## 9. Phases

Each phase ends in a state that could be submitted.

### P0 — proves the idea (must pass before anything else)

| Step | Output | Gate |
|---|---|---|
| 0.1 Project skeleton, `git init`, `.env`, `ruff`, `pytest` | The commands in the README work | |
| 0.2 `scripts/probe.py` | `results/PROBE.md` | See gates below |
| 0.3 Entity engine with unit tests | `tests/test_numbers.py`, `tests/test_slots.py` pass | |
| 0.4 Stream client, cache, recorder | Traces on disk | |
| 0.5 Scripts and spliced audio, Hinglish | About 200 utterances | |
| 0.6 Fixed-timer baselines and our policy over traces | `results/RESULTS.md` v1 | |

**Probe gates.** Stop and report to the user if any of 1–3 fails.

1. Key works for REST STT, realtime STT and TTS. Credits per call are read from the dashboard and written down.
2. A 10-digit number spoken with 600–1000 ms pauses, streamed at 200, 300 and 500 ms windows in `verbatim`, `codemix` and `transcribe`, yields the right digits in at least 8 of 10 tries for some setting.
3. Text for a segment arrives within about 600 ms of the pause starting.
4. `commit` closes an utterance as documented (decides 5.3's alternative).
5. Whether two streams can be open at once (decides whether live mode runs lanes together or one after the other).

### P1 — needed for a strong submission

Smart Turn baseline and hybrid policy · live agent with second pass and read-back · demo data routes (5.7) · the demo interface, designed with the UI skill, in replay mode · tagged audio build · 8 kHz phone condition · human clips · live confirmation of timer replay.

### P2 — strengthens it

Tamil–English and Bengali–English lexicons and test sets · noise condition · Gemini text-completeness comparison · report of Timbre misreadings found by pre-flight · caller self-corrections ("nahin, nau nahin, aath").

### P3 — only if time remains

AMR-NB condition (needs an ffmpeg build with libopencore-amr) · live microphone mode in the browser · open-ended entity detection with no expected slot.

## 10. Constraints and known limitations

- **Finished segments only.** The layer sees text only after a pause. It cannot react mid-word.
- **Expected slot.** The strong results apply when the agent knows what it asked for.
- **Amounts and dates are partly guesswork.** A grace period is a timer with better aim.
- **Synthetic callers.** Pause lengths and prosody are constructed. Human clips are few and from one speaker.
- **Circular test.** Timbre generates what Prisma hears.
- **Timer baselines are replayed**, with a live check on a subset.
- **Realtime pace.** A minute of test audio takes a minute to record, and possibly one stream at a time.
- **G.729 is not tested.** Stock ffmpeg cannot encode it.
- **Not a claim about Gnani's internal systems**, which are not public.
