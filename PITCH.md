# Dhairya (धैर्य): a turn-taking layer on Gnani Prisma v3.0 that waits for the value, not the silence

**One-page pitch · Great Indian AI Internship Challenge** · [Live demo](https://shreytiwari09.github.io/Dhairya/) · [Code](https://github.com/shreytiwari09/Dhairya) · [PDF version](docs/Dhairya-one-page-pitch.pdf)

> Voice agents end a caller's turn after a fixed silence, so they cut in while a caller reads out a mobile number, OTP, amount or date. Dhairya decides from **how much of the value has arrived**. On 152 unseen Hindi–English calls it **interrupted 0%**, got **99%** of values right and answered in **0.42 s**; the fixed timer that also never interrupted waited 1.73 s.

| 152 held-out calls | Interrupted the caller | Value right | Typical wait |
|---|---|---|---|
| Fixed timer 500 ms (run live on Prisma) | 62% | 36% | 0.75 s |
| Fixed timer 1500 ms (shortest that never interrupts) | 0% | 99% | 1.73 s |
| Smart Turn v3.2 (open model) † | 58% | 41% | 0.53 s |
| **Dhairya** | **0%** | **99%** | **0.42 s** |

† Not a fair test: every synthetic phrase ends with sentence-final intonation, which is what Smart Turn listens for. On 8 kHz phone-line audio (G.711), Dhairya: 0% interrupted, 98% right.

## 1. A real problem

Callers read numbers in pieces: five digits, a breath, five more. A timer short enough to feel fast cuts them off and saves half a number. One long enough not to makes every reply slow. This hits the calls that matter most: payments, KYC, OTPs, callbacks, where one wrong digit costs something.

## 2. Effective use of Gnani models

- **Prisma v3.0 realtime** at a 200 ms silence window, `verbatim` format: each spoken group arrives as text about 0.4 s after the pause.
- A Hindi–English number parser counts the digits per expected value (mobile, OTP, amount, date). Incomplete: wait. Complete: answer.
- **Prisma REST** re-reads the whole turn as a second pass. If it disagrees with the stream, the agent asks the caller to confirm.
- **Timbre v2.5** speaks the agent and the test callers.

## 3. Technical robustness

- 200 synthetic calls; 152 recorded *after* the policy was frozen. Timer baselines run live, not simulated. 95% intervals reported.
- Phone-line test: 8 kHz, G.711 mu-law, through Prisma at 8 kHz.
- Typed errors, retries, resumable runs. Fallbacks: a policy error falls back to a 1 s timer; a failed second pass asks the caller to confirm.
- 153 offline tests. Public live demo with rate limits.

## 4. What is new, and what I found

- The turn ends on **content**, not time. Extra digits are caught and read back; a hold cap nudges a stalled caller.
- Found by testing Prisma: the realtime stream takes one language; `x-partials` (undocumented) enables partial results; three digits said together return as one number word ("आठ सौ पिचानवे").
- Timbre v3.0 voices read digit words with long gaps, so v2.5 voices were used.

## Try it

The [demo](https://shreytiwari09.github.io/Dhairya/) lets you speak a number in your own voice. It replays your call through six fixed timers, so you see which would have cut you off. It also plays recorded calls and lets you set your own pause.

## Limits, stated plainly

Callers are synthetic, and Timbre generates what Prisma hears, so the test is partly circular. Only Hindi–English is measured. Open-ended amounts still fall back on a short timer. The agent is told which kind of value to expect. No real phone numbers or recordings are used.
