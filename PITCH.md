# Dhairya (धैर्य): the voice agent that lets you finish your number

**One-page pitch · Great Indian AI Internship Challenge** · [Live demo](https://shreytiwari09.github.io/Dhairya/) · [Code](https://github.com/shreytiwari09/Dhairya)

## The problem

A voice agent has to decide when the caller has finished. Most use a fixed silence timer. People read out a mobile number, an OTP, an amount or a date in pieces: five digits, a breath, five more. A short timer cuts in on the breath and the agent saves half a number. A long timer stops the interruptions but slows every other reply.

## The solution

Dhairya is a turn-taking layer on **Gnani Prisma v3.0** realtime speech-to-text. It decides from *what has been said*, not from *how long it has been quiet*. A parser counts the digits that have arrived, in Hindi or English. Five of ten digits: keep the line open. The tenth: answer at once. A second pass over the whole turn through Prisma's REST endpoint checks the value, and **Gnani Timbre v2.5** reads it back to the caller.

## The evidence

200 synthetic Hindi–English calls with pauses of known length, played through Prisma. The policy was frozen on 48; the other **152 had never been heard**. Fixed timers were run live at their own silence setting.

| Policy | Interrupted the caller | Value right | Typical wait |
|---|---|---|---|
| Fixed timer 500 ms | 62% | 36% | 0.75 s |
| Fixed timer 1500 ms (shortest that never interrupts) | 0% | 99% | 1.73 s |
| **Dhairya** | **0%** | **99%** | **0.42 s** |

On 8 kHz phone-line audio (G.711) Dhairya still interrupted 0% and got 98% right. Full tables and misses: [results/RESULTS.md](results/RESULTS.md).

## Try it

The demo page lets you speak a number in your own voice and replays your call through six fixed timers, so you see which would have cut you off. It also plays recorded calls and lets you set your own pause.

## Limits

The callers are synthetic, and Timbre generates what Prisma hears, so the test is partly circular. Open-ended amounts still fall back on a short timer. Only Hindi–English is measured. The open Smart Turn baseline is not compared fairly, because every synthetic phrase ends with sentence-final intonation.

Solo build. All data is synthetic: no real phone numbers or call recordings.
