# Results

200 synthetic calls through Prisma v3.0 realtime (`format: verbatim`, `hi-IN`).

- **Fixed timers** are live runs: each call was played with Prisma's own silence window (`x-min-silence-ms`) set to the timer value, and the first finished segment is the end of the turn. All six settings were recorded live.
- **Dhairya** runs over one recording per call made at its own setting, a 200 ms window. Its decisions are computed from those recorded events.

- **Cut in early:** the policy ended the turn before the caller's last sample.
- **Value correct:** the value held when the policy decided equals the script's value.
- **Wait:** time from the caller's last sample to the decision, for turns not cut in.
- **Nudges:** the policy gave up waiting and would prompt the caller.

## Held-out calls

The policy and parser were frozen before these calls were recorded. This is the result to quote.

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 152 | 75% | 68-81% | 25% | 19-32% | 0.49 | 0.57 | 0 |
| Fixed timer 500 ms | 152 | 62% | 55-70% | 36% | 29-44% | 0.75 | 1.04 | 0 |
| Fixed timer 700 ms | 152 | 49% | 42-57% | 50% | 42-58% | 0.90 | 1.27 | 0 |
| Fixed timer 1000 ms | 152 | 24% | 18-32% | 70% | 63-77% | 1.19 | 1.78 | 0 |
| Fixed timer 1500 ms | 152 | 0% | 0-2% | 99% | 95-100% | 1.73 | 1.99 | 0 |
| Fixed timer 2000 ms | 152 | 0% | 0-2% | 99% | 95-100% | 2.22 | 2.64 | 0 |
| Smart Turn v3.2 | 152 | 58% | 50-65% | 41% | 33-49% | 0.53 | 3.27 | 0 |
| **Dhairya** | 152 | 0% | 0-2% | 99% | 96-100% | 0.42 | 1.45 | 1 |

### Held-out: amount

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 36 | 75% | 59-86% | 25% | 14-41% | 0.47 | 0.48 | 0 |
| Fixed timer 500 ms | 36 | 53% | 37-68% | 47% | 32-63% | 0.72 | 0.91 | 0 |
| Fixed timer 700 ms | 36 | 36% | 22-52% | 64% | 48-78% | 0.86 | 0.95 | 0 |
| Fixed timer 1000 ms | 36 | 17% | 8-32% | 83% | 68-92% | 1.16 | 1.84 | 0 |
| Fixed timer 1500 ms | 36 | 0% | 0-10% | 100% | 90-100% | 1.71 | 1.87 | 0 |
| Fixed timer 2000 ms | 36 | 0% | 0-10% | 100% | 90-100% | 2.21 | 3.98 | 0 |
| Smart Turn v3.2 | 36 | 56% | 40-70% | 42% | 27-58% | 0.49 | 3.22 | 0 |
| **Dhairya** | 36 | 0% | 0-10% | 100% | 90-100% | 0.44 | 1.78 | 0 |

### Held-out: date

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 20 | 75% | 53-89% | 25% | 11-47% | 0.44 | 0.46 | 0 |
| Fixed timer 500 ms | 20 | 55% | 34-74% | 35% | 18-57% | 0.81 | 1.01 | 0 |
| Fixed timer 700 ms | 20 | 40% | 22-61% | 55% | 34-74% | 0.86 | 1.19 | 0 |
| Fixed timer 1000 ms | 20 | 15% | 5-36% | 85% | 64-95% | 1.16 | 1.18 | 0 |
| Fixed timer 1500 ms | 20 | 0% | 0-16% | 95% | 76-99% | 1.71 | 2.13 | 0 |
| Fixed timer 2000 ms | 20 | 0% | 0-16% | 95% | 76-99% | 2.18 | 2.21 | 0 |
| Smart Turn v3.2 | 20 | 40% | 22-61% | 55% | 34-74% | 0.70 | 3.25 | 0 |
| **Dhairya** | 20 | 0% | 0-16% | 95% | 76-99% | 0.40 | 0.95 | 1 |

### Held-out: mobile

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 68 | 79% | 68-87% | 21% | 13-32% | 0.52 | 0.61 | 0 |
| Fixed timer 500 ms | 68 | 75% | 64-84% | 25% | 16-36% | 0.79 | 1.14 | 0 |
| Fixed timer 700 ms | 68 | 65% | 53-75% | 35% | 25-47% | 0.94 | 1.30 | 0 |
| Fixed timer 1000 ms | 68 | 31% | 21-43% | 59% | 47-70% | 1.26 | 2.68 | 0 |
| Fixed timer 1500 ms | 68 | 0% | 0-5% | 99% | 92-100% | 1.76 | 1.86 | 0 |
| Fixed timer 2000 ms | 68 | 0% | 0-5% | 99% | 92-100% | 2.24 | 2.31 | 0 |
| Smart Turn v3.2 | 68 | 72% | 60-81% | 28% | 19-40% | 0.48 | 3.33 | 0 |
| **Dhairya** | 68 | 0% | 0-5% | 100% | 95-100% | 0.39 | 0.68 | 0 |

### Held-out: otp

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 28 | 64% | 46-79% | 36% | 21-54% | 0.49 | 0.53 | 0 |
| Fixed timer 500 ms | 28 | 50% | 33-67% | 50% | 33-67% | 0.73 | 0.77 | 0 |
| Fixed timer 700 ms | 28 | 36% | 21-54% | 64% | 46-79% | 0.90 | 1.27 | 0 |
| Fixed timer 1000 ms | 28 | 25% | 13-43% | 71% | 53-85% | 1.18 | 1.59 | 0 |
| Fixed timer 1500 ms | 28 | 0% | 0-12% | 100% | 88-100% | 1.72 | 1.89 | 0 |
| Fixed timer 2000 ms | 28 | 0% | 0-12% | 100% | 88-100% | 2.20 | 2.31 | 0 |
| Smart Turn v3.2 | 28 | 39% | 24-58% | 61% | 42-76% | 1.26 | 3.28 | 0 |
| **Dhairya** | 28 | 0% | 0-12% | 100% | 88-100% | 0.45 | 0.98 | 0 |

## Phone line: 8 kHz G.711 mu-law

The same calls were resampled to 8 kHz, passed through G.711 mu-law and streamed with `x-sample-rate: 8000`; the fixed timers are live runs at their own window, Dhairya runs over the 200 ms recording.

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 500 ms | 152 | 64% | 56-71% | 35% | 28-43% | 0.72 | 1.19 | 0 |
| Fixed timer 1500 ms | 152 | 0% | 0-2% | 97% | 93-99% | 1.73 | 1.99 | 0 |
| **Dhairya** | 152 | 0% | 0-2% | 98% | 94-99% | 0.36 | 1.58 | 2 |

Of 200 calls, 200 were recorded in this condition at 200 ms and 0 failed.

## Development calls

The first 12 scripts of each category. The amount logic and one misheard-word rule were changed after seeing these, so these numbers flatter the policy.

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 48 | 75% | 61-85% | 25% | 15-39% | 0.47 | 0.52 | 0 |
| Fixed timer 500 ms | 48 | 54% | 40-67% | 46% | 33-60% | 0.73 | 0.98 | 0 |
| Fixed timer 700 ms | 48 | 44% | 31-58% | 56% | 42-69% | 0.89 | 1.22 | 0 |
| Fixed timer 1000 ms | 48 | 21% | 12-34% | 75% | 61-85% | 1.17 | 2.09 | 0 |
| Fixed timer 1500 ms | 48 | 0% | 0-7% | 100% | 93-100% | 1.72 | 1.77 | 0 |
| Fixed timer 2000 ms | 48 | 0% | 0-7% | 100% | 93-100% | 2.20 | 2.27 | 0 |
| Smart Turn v3.2 | 48 | 67% | 53-78% | 33% | 22-47% | 1.80 | 3.32 | 0 |
| **Dhairya** | 48 | 0% | 0-7% | 100% | 93-100% | 0.38 | 1.29 | 0 |

### Development: amount

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 12 | 75% | 47-91% | 25% | 9-53% | 0.47 | 0.51 | 0 |
| Fixed timer 500 ms | 12 | 50% | 25-75% | 50% | 25-75% | 0.73 | 0.76 | 0 |
| Fixed timer 700 ms | 12 | 42% | 19-68% | 58% | 32-81% | 0.87 | 0.90 | 0 |
| Fixed timer 1000 ms | 12 | 17% | 5-45% | 83% | 55-95% | 1.16 | 1.18 | 0 |
| Fixed timer 1500 ms | 12 | 0% | 0-24% | 100% | 76-100% | 1.73 | 1.88 | 0 |
| Fixed timer 2000 ms | 12 | 0% | 0-24% | 100% | 76-100% | 2.24 | 2.28 | 0 |
| Smart Turn v3.2 | 12 | 75% | 47-91% | 25% | 9-53% | 0.38 | 2.94 | 0 |
| **Dhairya** | 12 | 0% | 0-24% | 100% | 76-100% | 0.40 | 1.68 | 0 |

### Development: date

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 12 | 75% | 47-91% | 25% | 9-53% | 0.45 | 0.48 | 0 |
| Fixed timer 500 ms | 12 | 42% | 19-68% | 58% | 32-81% | 0.73 | 0.75 | 0 |
| Fixed timer 700 ms | 12 | 33% | 14-61% | 67% | 39-86% | 0.86 | 0.88 | 0 |
| Fixed timer 1000 ms | 12 | 0% | 0-24% | 100% | 76-100% | 1.15 | 1.18 | 0 |
| Fixed timer 1500 ms | 12 | 0% | 0-24% | 100% | 76-100% | 1.69 | 1.73 | 0 |
| Fixed timer 2000 ms | 12 | 0% | 0-24% | 100% | 76-100% | 2.17 | 2.22 | 0 |
| Smart Turn v3.2 | 12 | 67% | 39-86% | 33% | 14-61% | 1.81 | 3.23 | 0 |
| **Dhairya** | 12 | 0% | 0-24% | 100% | 76-100% | 0.37 | 0.56 | 0 |

### Development: mobile

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 12 | 83% | 55-95% | 17% | 5-45% | 0.52 | 0.53 | 0 |
| Fixed timer 500 ms | 12 | 67% | 39-86% | 33% | 14-61% | 0.77 | 1.29 | 0 |
| Fixed timer 700 ms | 12 | 67% | 39-86% | 33% | 14-61% | 1.10 | 1.36 | 0 |
| Fixed timer 1000 ms | 12 | 42% | 19-68% | 42% | 19-68% | 1.22 | 1.24 | 0 |
| Fixed timer 1500 ms | 12 | 0% | 0-24% | 100% | 76-100% | 1.74 | 1.77 | 0 |
| Fixed timer 2000 ms | 12 | 0% | 0-24% | 100% | 76-100% | 2.24 | 2.27 | 0 |
| Smart Turn v3.2 | 12 | 75% | 47-91% | 25% | 9-53% | 3.28 | 3.43 | 0 |
| **Dhairya** | 12 | 0% | 0-24% | 100% | 76-100% | 0.37 | 0.55 | 0 |

### Development: otp

| Policy | Calls | Cut in early | 95% interval | Value correct | 95% interval | Wait P50 (s) | Wait P95 (s) | Nudges |
|---|---|---|---|---|---|---|---|---|
| Fixed timer 300 ms | 12 | 67% | 39-86% | 33% | 14-61% | 0.47 | 0.52 | 0 |
| Fixed timer 500 ms | 12 | 58% | 32-81% | 42% | 19-68% | 0.73 | 0.94 | 0 |
| Fixed timer 700 ms | 12 | 33% | 14-61% | 67% | 39-86% | 0.93 | 1.04 | 0 |
| Fixed timer 1000 ms | 12 | 25% | 9-53% | 75% | 47-91% | 1.58 | 2.42 | 0 |
| Fixed timer 1500 ms | 12 | 0% | 0-24% | 100% | 76-100% | 1.71 | 1.75 | 0 |
| Fixed timer 2000 ms | 12 | 0% | 0-24% | 100% | 76-100% | 2.18 | 2.22 | 0 |
| Smart Turn v3.2 | 12 | 50% | 25-75% | 50% | 25-75% | 1.80 | 3.20 | 0 |
| **Dhairya** | 12 | 0% | 0-24% | 100% | 76-100% | 0.37 | 0.53 | 0 |

## Does replaying a timer match running it live?

Each timer can also be replayed from the 200 ms recording: wait the rest of the timer after a segment's text arrives, and cancel if speech resumes. The table compares that replay with the live runs used above. The replay is harsher on a timer when a pause is exactly as long as the timer.

| Timer ms | Calls | Cut in early: live | replayed | Value correct: live | replayed | Wait P50 (s): live | replayed |
|---|---|---|---|---|---|---|---|
| 300 | 200 | 75% | 73% | 25% | 27% | 0.48 | 0.56 |
| 500 | 200 | 60% | 61% | 38% | 39% | 0.74 | 0.74 |
| 700 | 200 | 48% | 48% | 52% | 52% | 0.90 | 0.92 |
| 1000 | 200 | 24% | 33% | 72% | 66% | 1.18 | 1.22 |
| 1500 | 200 | 0% | 2% | 99% | 97% | 1.73 | 1.71 |
| 2000 | 200 | 0% | 0% | 99% | 100% | 2.22 | 2.21 |

## Reference: whole-call REST transcription

Transcribing each complete call through REST in Transcribe mode and reading it with the same parser gives the right value in 196 of 200 calls (98%). This is the ceiling for any policy that waits for the whole turn; misses here are speech-synthesis, transcription or parser errors, not timing.

## Dhairya's misses

| Call | Said | Truth | Heard value | Outcome |
|---|---|---|---|---|
| date-013 | अट्ठाईस तारीख / मैं। | 28-05 | 28 | nudge |

## Test set

- Calls recorded: 200. Scripts dropped because the voice paused inside a group: 0.
- Caller voices: Bhavna, Deepak, Nalini, Omkar (`timbre-v2.5`). Pauses between groups: 0.4, 0.6, 0.8, 1.0, 1.3 s, drawn at random per script.
- Scripts come from a seeded generator (`data/scripts/scripts.json`). All values are made up.

## Limits

- Callers are synthetic. Each breath group is synthesised separately and joined with silence, so pause lengths are exact but intonation is not natural.
- Timbre generates the speech that Prisma transcribes.
- Dhairya's row is computed from recorded events, not from a live conversation. The live agent exercises the same code in real time.
- Dhairya is told which kind of value to expect, as an agent that asked the question would know.
- Intervals are Wilson 95% intervals on each row; no paired test between policies yet.
