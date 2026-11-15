# The problem Dhairya solves, and how

A one-document account of the problem, the evidence that it is real, how Gnani's stack handles it today, what was built, and what was measured. Every quote has a link. Every number is from [results/RESULTS.md](../results/RESULTS.md).

## 1. The problem in one paragraph

A voice agent has to decide when the caller has finished speaking. Most decide by silence: if the caller is quiet for a fixed time, the agent answers. People pause while reading out a mobile number, an OTP, an amount or a date. They read in groups: five digits, a breath, five more. A short timer takes the breath for the end, so the agent cuts in and saves half a number. A long timer avoids that and makes every other reply slow. Every fixed timer trades one harm for the other.

**Why it matters.** The values that are read out in pieces are the ones where a wrong digit costs something: a callback number, a one-time code, a payment amount, a date. Gnani's own banking write-up says speech-recognition errors "cluster on the vocabulary that matters most: amounts, dates, product identifiers, and consent confirmations."

## 2. What shows the problem was already bugging people

| Evidence | What it says | Source |
|---|---|---|
| Gnani's latency write-up | "Fixed silence timers are the wrong tool." It calls knowing when the caller has finished "the stage that most often ruins an otherwise fast system." | [What causes latency in voice AI](https://www.gnani.ai/resources/blogs/what-causes-latency-in-voice-ai-how-to-overcome-it) |
| Gnani's Prisma realtime docs | Silence timers and a manual `commit` frame are the controls. `x-min-silence-ms` is "the single biggest lever on end-of-utterance latency." The docs describe no setting that judges whether a spoken value is complete. | [Prisma realtime docs](https://docs.gnani.ai/api/STT/stt-websocket.md) |
| Gnani's banking write-up | Errors cluster on amounts, dates, identifiers and confirmations, the same values people dictate in pieces. | [Speech recognition for BFSI in India](https://www.gnani.ai/resources/blogs/blog-speech-recognition-bfsi-india-banking-compliance) |
| Telnyx | Ships a dedicated setting (`on_number_seconds`) for transcripts that end in a number, so callers can "finish reading out long numbers like account IDs or phone numbers." | [Telnyx interruption settings](https://developers.telnyx.com/docs/inference/ai-assistants/interruption-settings.md) |
| Vapi support forum | A user reports an agent interrupting a customer who is giving details. | [Vapi support thread](https://support.vapi.ai/t/27122035/issue-with-ai-agent-interrupting-customers-while-providing-c) |
| Smart Turn (the leading open turn-detection model) | Supports Hindi, but lists telephone-number and card-number entry as future work. | [Smart Turn on GitHub](https://github.com/pipecat-ai/smart-turn) |

## 3. How Gnani approaches it today

- Gnani's posts treat end-of-turn as a stage to get right, recommend content-aware ("semantic") end-pointing over fixed timers, and publish a way to measure latency: from the caller's last syllable to the agent's first audible syllable, at the 95th percentile, against a target under 800 ms.
- Prisma's realtime stream gives the developer the building blocks: a configurable server silence window (`x-min-silence-ms`), `speech_start` and finished `transcript` events, and a manual `commit` frame. Deciding when a value is *complete* is left to the application.

## 4. What was built

Dhairya (धैर्य, "patience") is a turn-taking layer on Prisma v3.0 realtime. It decides from what has been said, not from how long it has been quiet.

1. **Prisma v3.0 realtime** streams the caller's audio at a 200 ms silence window in `verbatim` format. Each spoken group arrives as text about 0.4 s after the pause.
2. A **Hindi–English number parser** (Devanagari and Latin, digit by digit or in pairs, "double" and "triple", lakh and crore) counts what has arrived for the kind of value expected: mobile number, OTP, amount or date.
3. **Policy:** incomplete means keep waiting; complete means answer now. Open amounts get a short grace. A hold cap nudges a stalled caller. Extra digits are caught and read back.
4. **Prisma REST** re-reads the whole turn as a second pass. If it disagrees with the stream, the agent asks the caller to confirm.
5. **Timbre v2.5** reads the value back.

The policies are pure functions of events and time, so the same code runs live and over saved traces. Everything is reproducible from the repository.

## 5. What was measured

200 synthetic Hindi–English calls (mobile numbers, OTPs, amounts, dates) with pauses of known length, played through Prisma. The policy was frozen on 48 of them; the other **152 had never been heard**. Fixed timers were run live, with Prisma's own silence window set to each timer's value.

| Policy | Interrupted the caller | Value right | Typical wait (P50) |
|---|---|---|---|
| Fixed timer 300 ms | 75% | 25% | 0.49 s |
| Fixed timer 500 ms | 62% | 36% | 0.75 s |
| Fixed timer 700 ms | 49% | 50% | 0.90 s |
| Fixed timer 1000 ms | 24% | 70% | 1.19 s |
| Fixed timer 1500 ms | 0% | 99% | 1.73 s |
| Fixed timer 2000 ms | 0% | 99% | 2.22 s |
| **Dhairya** | **0%** | **99%** | **0.42 s** |

- Dhairya's 0% interruption has a 95% interval of 0 to 2% over 152 calls.
- On 8 kHz phone-line audio (G.711) it still interrupted 0% and got 98% right, at a 0.36 s median wait.
- Reading: the slowest timers match Dhairya's accuracy but make the caller wait four to five times longer.

## 6. What was found about Prisma on the way

- The realtime stream takes exactly one language: `hi-IN,en-IN` is rejected (close code 1008), while `hi-IN` still hears English digits.
- An undocumented header, `x-partials: true`, switches on partial results.
- Three digits said together can come back as one number word ("eight nine five" as "आठ सौ पिचानवे"). The parser now reads it back as three digits.
- Timbre v3.0 voices read digit words with long gaps, which fragments recognition, so the test callers use v2.5 voices.
- Very short segments lose accuracy, so shortening the window further does not help.

## 7. What this does not claim

- It does not claim to have invented semantic turn detection. LiveKit, Pipecat's Smart Turn, AssemblyAI, Deepgram and Telnyx all have forms of it. The claim is narrow: number dictation in Hindi–English is a case that general turn detectors and Gnani's public API leave open, and nobody had published a measurement of it on Gnani's stack.
- The test callers are synthetic, and Timbre generates what Prisma hears, so the test is partly circular. Only Hindi–English is measured. Open-ended amounts still fall back on a short timer. The agent is told which kind of value to expect.
- Whether Gnani has an internal solution is unknown. "Nobody has built this" means nobody visibly has.

## 8. Where to look

- Live demo (speak a number in your own voice): https://dhairya-live.onrender.com
- Replay demo: https://shreytiwari09.github.io/Dhairya/
- Code and results: [README](../README.md), [results/RESULTS.md](../results/RESULTS.md), [API probe](../results/PROBE.md)
- One-page pitch: [PITCH.md](../PITCH.md)
