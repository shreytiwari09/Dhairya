# PRD — Dhairya

**One line:** a turn-taking layer for Gnani's Prisma realtime speech-to-text that stops a voice agent cutting off a caller who is still reading out a number, with a benchmark that proves it against fixed silence timers.

**Name:** "Dhairya" (धैर्य), Sanskrit and Hindi for patience. Tagline: "the voice agent that lets you finish your number".

**Challenge:** Gnani AI Great Indian AI Internship Challenge. Deadline 15 Nov 2026, 6:00 PM IST. Rules are in [hackathon.md](hackathon.md).

---

## 1. Problem

A voice agent has to decide when the caller has finished speaking. Most agents decide by silence: if the caller is quiet for a fixed time, the agent answers.

People pause while reading out a mobile number, an OTP, an amount or a date. They read digits in groups ("nau ath saat chhe paanch … chaar teen do ek shunya"). A short timer treats the pause as the end, so the agent interrupts and saves half a number. A long timer avoids that, and makes every other reply slow.

### Is this a real problem? Checked on 12 Nov 2026

| Evidence | Source |
|---|---|
| Gnani says "Fixed silence timers are the wrong tool" and that this stage "most often ruins an otherwise fast system". | [Gnani latency post](https://www.gnani.ai/resources/blogs/what-causes-latency-in-voice-ai-how-to-overcome-it) |
| Gnani's realtime API offers only silence and speech timers plus a manual `commit` frame. The docs describe no content-based turn detection. They call `x-min-silence-ms` "the single biggest lever on end-of-utterance latency". | [Prisma realtime docs](https://docs.gnani.ai/api/STT/stt-websocket.md) |
| Telnyx ships a dedicated setting, `on_number_seconds`, for transcripts that end in a number, so callers can "finish reading out long numbers like account IDs or phone numbers". | [Telnyx docs](https://developers.telnyx.com/docs/inference/ai-assistants/interruption-settings.md) |
| Vapi users report agents interrupting customers who are giving details. | [Vapi support forum](https://support.vapi.ai/t/27122035/issue-with-ai-agent-interrupting-customers-while-providing-c) |
| Smart Turn, the leading open turn-detection model, supports Hindi but lists telephone-number, card-number and address entry as future work. It does not mention code-mixed speech. | [Smart Turn repository](https://github.com/pipecat-ai/smart-turn) |
| Among challenge entries on GitHub, none is a stand-alone turn detector or turn-detection benchmark. The nearest are a 250 ms silence rule inside one agent and a barge-in handler (the caller interrupting the agent, which is the opposite direction). | GitHub repository search, 12 Nov 2026 |

**Verdict: the problem is real.** The claim has to be stated narrowly.

### What we can and cannot claim

- **Cannot claim:** "we invented semantic turn detection". LiveKit, Pipecat (Smart Turn), AssemblyAI, Deepgram and Telnyx all have it, and Gnani has a Pipecat plugin, so a developer could already attach Smart Turn to Prisma.
- **Can claim:** number dictation in Hinglish is the case that general turn detectors and Gnani's public API both leave open, and nobody has published a measurement of it on Gnani's stack. We build the layer and publish the measurement, with Smart Turn as a baseline.
- **Unknown:** whether Gnani has an internal solution. Three of the GitHub searches failed on network errors, LinkedIn and X were not searchable, and private repositories are invisible. "Nobody has built this" means nobody visibly has.

## 2. Who it is for

1. **Engineers building voice agents on Prisma** (Gnani's customers and Gnani's own team). They get a drop-in policy and numbers showing what each silence setting costs.
2. **Callers.** They finish their number without being interrupted, and get a fast reply when they are done.
3. **Judges.** They see Prisma's realtime controls used in depth, measured, on a problem Gnani has written about.

## 3. Goals

1. Hold the turn open while a dictated mobile number, OTP/PIN, amount or date is incomplete, and close it quickly once it is complete.
2. Measure three things on one fixed set of synthetic calls, for our layer and for every baseline:
   - premature cut-in rate;
   - delay from the caller's last syllable to the end-of-turn decision, at P50 and P95;
   - entity capture accuracy, by category.
3. Show the difference in a demo anyone understands in 20 seconds: the same call sent to two agents side by side.
4. Publish everything needed to reproduce the numbers: scripts, seeds, cached audio, raw traces, model versions.
5. Ship a demo interface that looks and feels excellent. The Gnani team gives UI little weight in judging, but the builder has made it a requirement, and it drives how well the public post does. It is designed with the UI skill the builder will supply, and it never comes before a working, measured core.

### Non-goals

- A general assistant, a full call-centre agent, or any consumer app.
- Barge-in handling (the caller interrupting the agent).
- A new speech model. No training.
- Real customer data of any kind.

## 4. What it does

| # | Capability | Detail |
|---|---|---|
| 1 | Listens on Prisma's realtime stream | Raw WebSocket, short silence window, so each spoken group arrives as text quickly |
| 2 | Tracks the entity being dictated | Understands Hindi and English number words, Latin and Devanagari script, digits, "double/triple", lakh/crore, and forms such as "dedh sau" and "dhai hazaar" |
| 3 | Decides wait or answer | Fixed-length entities (mobile, OTP, PIN) by count; amounts and dates by grammar plus a short grace period; other speech by an audio turn model |
| 4 | Never waits forever | After a capped hold it prompts the caller ("ji, aage boliye") |
| 5 | Double-checks the value | Re-transcribes the whole turn through the REST API in Transcribe mode and compares |
| 6 | Reads the value back | Timbre speaks the captured value for confirmation |
| 7 | Benchmarks itself | Synthetic callers with pauses of known length; baselines are fixed timers from 300 to 2000 ms and Smart Turn |

## 5. Languages

| Stage | Languages |
|---|---|
| First | Hinglish (Hindi–English, both scripts) |
| Then | Tamil–English and Bengali–English |

The second stage needs a new number-word list and a new test set per language. Results for languages the builder does not speak are labelled "not checked by a native speaker" unless someone checks a sample.

## 6. Success criteria

| Criterion | Target |
|---|---|
| Works end to end with a real Gnani key | Required |
| Cut-in rate on fixed-length entities | At most half the rate of a fixed timer that has the same median delay |
| Median delay on complete turns | No worse than a 700 ms fixed timer |
| Entity capture accuracy | Higher than every fixed-timer setting at 1000 ms or below |
| Reproducible | A stranger can re-run the scoring from cached traces without an API key |

These are targets, not results. The numbers are published as measured, including if a baseline wins. If the first probe shows the approach cannot work on Prisma's stream, the build stops and switches to the fallback in section 9.

## 7. Demo

One call, two agents on screen.

- **Left, fixed 500 ms timer:** the caller pauses after five digits, the agent interrupts and saves "98765".
- **Right, Dhairya:** the agent waits, the caller finishes, the agent saves "98765 43210" and reads it back.
- **Bottom:** the benchmark table for the whole test set.

The video is 60 seconds or less, uses synthetic data only, and shows the real system with nothing staged.

## 8. Awards it can qualify for

One entry can win at most one award.

| Award | Fit |
|---|---|
| Mixed Vibes (code-mixed voice) | Strong: Hinglish, then Tamil–English and Bengali–English |
| Solo Ninja | Yes, solo build |
| Noise Canceller (noisy phone audio) | Partial: 8 kHz phone audio is a test condition, noise is a later phase |
| Demo Day Drop (60-second demo) | Yes, if the video is 60 seconds or less |
| Small Town, Big Build | Likely: the builder's college is BML Munjal University, Kapriwas, Rewari district, Haryana. State the location exactly as it is; whether it counts as Tier 2 or 3 is Gnani's decision |

## 9. Risks

| Risk | Effect | Response |
|---|---|---|
| Prisma's stream returns finished segments only | Short windows may split or garble digits | Probe first; REST second pass; choose the output format by measurement |
| Credit cost and rate limits are unpublished | Benchmark may be smaller than planned | Probe reads cost off the dashboard; every response cached; one live request at a time |
| Smart Turn alone may already do well | Our added value shrinks | Report it honestly; the hybrid of Smart Turn plus entity tracking then becomes the contribution |
| Amounts are ambiguous ("teen hazaar" may be complete) | Content alone cannot decide | Grace period after open-ended amounts; reported as a separate category |
| Synthetic pauses are not real caller pauses | Results may flatter the method | Sweep pause lengths; add 30 to 50 clips of the builder reading synthetic scripts; state the limit |
| Timbre and Prisma are tested against each other | Circular | Human clips; state the limit |
| Someone publishes the same idea before the deadline | Looks derivative | Search again on submission morning |

**Fallback if the probe fails:** a phone-codec mismatch test that separates voice, line and listener as the cause of each failure (rank 2 in the research report).

## 10. Submission requirements

From [hackathon.md](hackathon.md):

- Uses at least one Gnani model (this uses Prisma v3.0 and Timbre).
- Outside models are disclosed: Smart Turn, and Gemini if it is used.
- Synthetic data only: no real phone numbers, Aadhaar, PAN, account numbers or recorded calls. Test mobile numbers are generated, not real.
- Public post on LinkedIn or X with `#GnaniAI` and `#GreatIndianAIInternshipChallenge`, Gnani AI tagged, before the form is submitted.
- Microsoft Form submitted before 6:00 PM IST on 15 Nov 2026.

## 11. Open questions for the builder

1. How many credits does one call cost? The API key exists; the probe answers this.
2. Is a Gemini key available? It is needed only for an optional phase.
3. Which UI skill will be used? The builder will supply it before the interface is built.
