---
name: Dhairya
description: A deck of flat, saturated cards that opens onto a phone call you take on the page. Black, lilac, paper and umber chapters; green means the line is open, red means the caller was cut off.
colors:
  black: "#000000"
  black-2: "#141414"
  black-ink: "#f6f6f6"
  black-ink-2: "#b8b8b8"
  black-rule: "#333333"
  lilac-hi: "#ffcdff"
  lilac-top: "#ffe4ff"
  lilac-mid: "#f8cdfb"
  lilac-ground: "#f6c9f9"
  lilac-ground-2: "#ecb8f5"
  lilac-deep: "#ecb9ff"
  lilac-bar: "#f3c2fb"
  lilac-ink: "#221826"
  lilac-ink-2: "#5e4766"
  lilac-rule: "#cf9ad9"
  paper: "#fafaf8"
  paper-2: "#eeeeea"
  paper-ink: "#18181b"
  paper-ink-2: "#52525b"
  paper-rule: "#d4d4d0"
  umber: "#2f2315"
  umber-top: "#43341f"
  umber-deep: "#241a0e"
  umber-2: "#3b2c19"
  umber-ink: "#f7f0e3"
  umber-ink-2: "#d2c4a8"
  umber-rule: "#5f5138"
  open: "#0f7a43"
  open-ink: "#0c6b3a"
  open-wash: "#d5e8db"
  open-hi: "#74dca0"
  cut: "#d4321f"
  cut-ink: "#b52715"
  cut-wash: "#f4d9d2"
  cut-hi: "#ff9c8c"
  card-saffron: "#f2bd18"
  card-chocolate: "#6b4a26"
  card-orchid: "#d6b4f4"
  card-plum: "#5d3a66"
  card-cobalt: "#2468e8"
  card-cream: "#f4f1ea"
  card-vermilion: "#d93a22"
  card-teal: "#17917f"
  card-parchment: "#f4ead4"
  card-ink: "#17110c"
  card-gold: "#c9a24a"
  plate-paper: "#f6efdc"
  plate-ink: "#3b2a14"
typography:
  display:
    fontFamily: "Gilda Display, Georgia, Times New Roman, serif"
    fontSize: "clamp(2.5rem, 7vw, 7rem)"
    fontWeight: 400
    lineHeight: 0.96
    letterSpacing: "-0.01em"
  landing-display:
    fontFamily: "Gilda Display, Georgia, Times New Roman, serif"
    fontSize: "clamp(2.4rem, 6.1vw, 7.4rem)"
    fontWeight: 400
    lineHeight: 0.96
    letterSpacing: "-0.01em"
  big-figure:
    fontFamily: "Gilda Display, Georgia, Times New Roman, serif"
    fontSize: "clamp(3rem, 8vw, 8rem)"
    fontWeight: 400
    lineHeight: 0.9
  wordmark:
    fontFamily: "Rozha One, Gilda Display, serif"
    fontSize: "1.28rem"
    fontWeight: 400
    lineHeight: 1
  wordmark-hindi:
    fontFamily: "Rozha One, Anek Devanagari, Switzer, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1
  heading:
    fontFamily: "Switzer, Anek Devanagari, system-ui, sans-serif"
    fontSize: "clamp(1.4rem, 1.1rem + 1.3vw, 2.2rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.015em"
  lede:
    fontFamily: "Switzer, Anek Devanagari, system-ui, sans-serif"
    fontSize: "clamp(1.08rem, 1rem + 0.5vw, 1.42rem)"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "Switzer, Anek Devanagari, system-ui, sans-serif"
    fontSize: "clamp(1rem, 0.96rem + 0.22vw, 1.125rem)"
    fontWeight: 400
    lineHeight: 1.5
  digit:
    fontFamily: "Switzer, Anek Devanagari, system-ui, sans-serif"
    fontSize: "clamp(1.8rem, 0.8rem + 3.6vw, 4rem)"
    fontWeight: 640
    lineHeight: 1
  label:
    fontFamily: "Switzer, Anek Devanagari, system-ui, sans-serif"
    fontSize: "clamp(0.78rem, 0.72rem + 0.25vw, 0.92rem)"
    fontWeight: 600
    lineHeight: 1.2
rounded:
  card: "6.4% / 4.6%"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  pill: "99px"
  round: "50%"
spacing:
  gutter: "clamp(18px, 4.2vw, 64px)"
  measure: "62ch"
  page-max: "1280px"
  page-narrow: "1000px"
components:
  cta:
    backgroundColor: "{colors.lilac-hi}"
    textColor: "{colors.black}"
    rounded: "{rounded.pill}"
    padding: "0.38rem 1.4rem 0.38rem 0.38rem"
  cta-hover:
    backgroundColor: "#ffffff"
  answer-button:
    backgroundColor: "{colors.open}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0.45rem 1.4rem 0.45rem 0.45rem"
  answer-button-again:
    backgroundColor: "#0b0b0b"
    textColor: "#ffffff"
  hold-button:
    backgroundColor: "#0b0b0b"
    textColor: "#f5f5f3"
    rounded: "{rounded.round}"
    width: "clamp(180px, 22vw, 240px)"
  tally-row-open:
    backgroundColor: "{colors.open-wash}"
    textColor: "#131714"
    rounded: "{rounded.xl}"
    padding: "0.85rem 1rem"
  tally-row-cut:
    backgroundColor: "{colors.cut-wash}"
    textColor: "#131714"
    rounded: "{rounded.xl}"
    padding: "0.85rem 1rem"
  agent-row:
    backgroundColor: "{colors.paper-2}"
    textColor: "{colors.paper-ink-2}"
    rounded: "{rounded.lg}"
    padding: "0.7rem 0.9rem"
  top-bar-solid-black:
    backgroundColor: "{colors.black}"
    textColor: "{colors.black-ink}"
    padding: "0.95rem {spacing.gutter}"
  top-bar-solid-lilac:
    backgroundColor: "{colors.lilac-bar}"
    textColor: "{colors.paper-ink}"
  top-bar-solid-paper:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.paper-ink}"
  top-bar-solid-umber:
    backgroundColor: "{colors.umber}"
    textColor: "{colors.umber-ink}"
  plate:
    backgroundColor: "{colors.plate-paper}"
    textColor: "{colors.plate-ink}"
    rounded: "{rounded.sm}"
    padding: "0.5em 0.7em 0.42em"
  end-mark:
    backgroundColor: "{colors.lilac-ground}"
    textColor: "{colors.lilac-ink}"
    rounded: "24%"
    size: "clamp(120px, 12vw, 170px)"
---

# Design System: Dhairya

## 1. Overview

**Creative north star: "The Deck and the Line"**

The page is a deck of flat, saturated playing cards that opens onto a phone call. Chapters change ground like a hand being dealt: black, lilac, paper, umber, black. Cards are the only illustrated objects; they sit in a fanned hand on the landing, and in three "portal" scenes one card grows until it fills the screen and becomes the next chapter. Inside the paper chapter, a plain call interface (digit slots, a waveform line, an answer button) uses only two signal colours: green for an open line, red for a caller who was cut off.

The technique (black / lilac-gradient / paper / brown chapters, saturated flat cards, serif display over a grotesque body, pinned portal scenes, Lenis smooth scroll) was copied from grail-app.com at the builder's request. The card artwork, the logo, the words and the Hindi type are Dhairya's own. Grail's PP Pangaia font and artwork are not used.

**Key characteristics:**
- Four chapter grounds, each re-theming every component through CSS variables on `[data-ground]`.
- Flat SVG card art, drawn once as `<symbol>`s in `index.html` and reused by the hand, the loader and the portals.
- Serif display in capitals (Gilda Display); Switzer for everything read; Rozha One only for the wordmark.
- Green and red mean only "line open" and "caller cut off". They never decorate.
- Motion is cinematic by default and entirely optional: reduced motion or `?still` skips `scroll.js`.

## 2. Colors

Four chapter grounds. Each defines `--bg`, `--ground`, `--ground-2`, `--ink`, `--ink-2`, `--rule`; components read only those variables.

### Chapter grounds

| Ground | Used for | Background | ground / ground-2 | ink / ink-2 | rule |
|---|---|---|---|---|---|
| **Black** | landing, problem (`#problem`), details, ending | `#000` | `#000` / `#141414` | `#f6f6f6` / `#b8b8b8` | `#333` |
| **Lilac** | why (`#why`) | `radial-gradient(130% 95% at 50% 0%, #ffe4ff 0%, #f8cdfb 42%, #ecb9ff 100%)` | `#f6c9f9` / `#ecb8f5` | `#221826` / `#5e4766` | `#cf9ad9` |
| **Paper** | the call (`#call`) | `#fafaf8` | `#fafaf8` / `#eeeeea` | `#18181b` / `#52525b` | `#d4d4d0` |
| **Umber** | numbers (`#results`), how it decides (`#how`) | `linear-gradient(180deg, #43341f 0%, #241a0e 100%)` | `#2f2315` / `#3b2c19` | `#f7f0e3` / `#d2c4a8` | `#5f5138` |

Black and umber set focus rings to Lilac Pink `#ffcdff`; lilac and paper use Answer Green `#0f7a43`. Selection is `#ffcdff` on `#000`. `html` and `body` stay `#000` so overscroll never flashes light.

### Accents

- **Lilac Pink** `#ffcdff`: the accent on black and umber: CTA fill, "Built on" line, footer name, focus ring, loader card outline. This is the sanctioned exception: lilac text on black is the chosen palette, taken in technique from grail-app.com at the builder's request.
- **Lilac Ground** `#f6c9f9` and **Lilac Deep** `#ecb9ff`: the lilac chapter, the loader ground, the portal background that leads into a lilac or paper chapter, the ending logo tile, the favicon tile.
- `#837052` (taupe) was named as part of the umber family but appears nowhere in `index.html`, `styles.css` or `scroll.js`, so it is not a token.
- **Umber Deep** `#241a0e`: the bottom of the umber gradient, the portal ground leading into umber, and the `--night` fill of chart points.

### Signal colours (call, chart, tables)

- **Answer Green** `#0f7a43`, ink `#0c6b3a`, wash `#d5e8db`, on-dark `#74dca0`: line open, Dhairya waited, complete digit.
- **Hang-up Red** `#d4321f`, ink `#b52715`, wash `#f4d9d2`, on-dark `#ff9c8c`: caller cut off, a timer's cut-in, a lost digit.
- On umber and black the `-hi` variants carry meaning (`.r`, `.g`, chart points); on paper the `-ink` variants do.

### Card art colours (defined once in `index.html`)

| Symbol | Card | Colours |
|---|---|---|
| `art-check` | saffron | `#f2bd18` field, `#6b4a26` chocolate frame |
| `art-dots` | orchid | `#d6b4f4` field, `#5d3a66` plum dots |
| `art-waves` | cobalt | `#2468e8` field, `#f4f1ea` cream waves |
| `art-diamond` | vermilion | `#d93a22` field, `#f2bd18` diamonds |
| `art-stripes` | teal | `#17917f` field, `#f4ead4` parchment stripes at 45 degrees |
| `art-gold` | night | `#17110c` field, `#c9a24a` gold line work |
| `art-ten` | parchment | `#f4ead4` field, `#6b4a26` dots (five filled, five outlined) |

Every card has the same chassis: an inset frame at 9 px, quarter-circle corner pieces in the second colour, 250 x 350 viewBox. The portal **plate** (label across the card) is `#f6efdc` with `#3b2a14` 3 px border and text.

### Named rules

**The Chapter Variable Rule.** A component never hard-codes a chapter colour; it reads `--ink`, `--ink-2`, `--rule`, `--ground`, `--ground-2`. Changing `data-ground` re-themes it.

**The Signal Rule.** Green and red appear only where the call succeeded or failed. No decorative green, no red accents, no gradients on them.

**The Card Colour Rule.** Saturated colour lives on the cards. Chapter grounds stay in the black / lilac / paper / umber families.

## 3. Typography

- **Gilda Display** (headings, big figures; self-hosted, SIL OFL, `fonts/GildaDisplay-latin.woff2`): weight 400 only, uppercase for `.display`, line-height 0.96, tracking -0.01em. Fallback Georgia.
- **Switzer** (body and all interface text; loaded from Fontshare's own stylesheet as its licence asks, weights 300 to 700): 400 body, 560 to 700 labels and names. Tabular lining numerals are on for the whole body.
- **Rozha One** (the Dhairya wordmark in Latin and in Devanagari; self-hosted, SIL OFL, `RozhaOne-latin.woff2` and `RozhaOne-devanagari.woff2`): used only for the wordmark: top bar, loader top card and counter, ending ghost wordmark, footer name. It is never used for headings or body.
- **Anek Devanagari** (all Hindi text, `[lang="hi"]`; self-hosted, OFL, variable weight and width): the face for any Devanagari. Switzer's fallback chain includes it so mixed lines render.

Digits in the call use Switzer at 640 weight. Labels use `font-stretch` 86% to 92% to narrow them; this is a Switzer variable-width axis feature and degrades harmlessly.

### Named rules

**The One Display Face Rule.** Gilda Display for headings and the three big result figures; nothing else is a display face. Rozha One is a logotype, not a second heading face.

**The Hindi Is Its Own Face Rule.** Devanagari is always set in Anek Devanagari (or Rozha One in the wordmark), never left to a system fallback.

## 4. Layout

- Content sits in `.inner`, max 1280 px (`.narrow` 1000 px), side padding `--gutter` (`clamp(18px, 4.2vw, 64px)`). Reading text is capped at 54 to 62 characters.
- Chapters have top padding `clamp(6rem, 14vh, 9rem)` and bottom `clamp(4rem, 10vh, 7rem)`. The landing, problem, why and ending fill at least `100svh`; the call, numbers, how and details scroll freely.
- Breakpoints: 900 px (tablet: three-column rows become one, two-column flow) and 700 px (phone: slot width computed from the viewport so ten digits always fit, navigation drops to two links, footer stacks).
- Page rhythm is borders, not boxes: `1px solid var(--rule)` top rules above columns, fold rows, table rows.
- The page snaps to whole pages (see Motion); long chapters are left alone.

## 5. Elevation & Depth

Neutral elevation only. Shadows are black at low alpha; there are no coloured glows and no hard offset shadows.

- **Card in the hand:** `0 20px 50px rgb(0 0 0 / 0.5), 0 4px 12px rgb(0 0 0 / 0.35)` (`--shadow-card`).
- **Portal card:** `0 30px 80px rgb(0 0 0 / 0.45), 0 6px 16px rgb(0 0 0 / 0.3)`.
- **Loader card:** `0 5px 12px rgb(0 0 0 / 0.16)`; the top card adds `0 18px 40px rgb(0 0 0 / 0.35)`.
- **Plate on a card:** `0 10px 24px rgb(0 0 0 / 0.4)`.
- Surfaces are otherwise flat. Depth between chapters comes from ground colour and the portal transition, not shadow.

## 6. Shapes

- **Cards:** `border-radius: 6.4% / 4.6%` at a 5:7 ratio, always.
- **Pills:** `99px` for CTA, answer button, pause tags, decision markers, filter chips.
- **Discs:** `50%` for the hold button, play and call discs, fold toggle.
- **Surfaces:** 12 px tally rows, 10 px agent rows, 8 px buttons in pickers, 6 px plate and skip link, 4 px code and focus ring. Ending logo tile: `24%`.

## 7. Components

### Logo
A waveform with a held dot: six rounded vertical bars (three before, three after) around a centred circle, the held dot, which is the pause that Dhairya waits through. Defined once as `<symbol id="logo-mark" viewBox="0 0 64 64" fill="currentColor">`, so it takes the colour of its container. Used in: the top bar (1.9 rem) beside the wordmark; the loader's top card (46% width, `#ffcdff` on `#0a0a0a`); the ending logo tile (`#221826` on `#f6c9f9`); the footer name (1.7 rem, `#ffcdff`); and the favicon (on a `#f6c9f9` rounded tile).

Wordmark: "Dhairya" in Rozha One 1.28 rem beside "धैर्य" in Rozha One / Anek Devanagari 1.05 rem at 85% opacity.

### Top bar
Fixed, three columns (brand, tagline, navigation); transparent over the landing and **solid after scrolling past 80 px**, with the ground of the chapter beneath it (black `#000`, lilac `#f3c2fb`, paper `#fafaf8`, umber `#2f2315`) so it never prints over body text. Ink is light on black and umber, dark on lilac and paper; `data-on` is set by chapter triggers and by portal progress (the switch happens at 70% of a portal). It **hides on scroll down** (after 240 px, `yPercent -110`, 0.4 s `power2.out`) and returns on any upward scroll or keyboard focus. The tagline hides at 900 px; two nav links hide at 700 px.

### Hand of cards
Seven cards (check, dots, waves, diamond, stripes, gold, ten) fanned along the bottom of the landing: x at 8% to 92%, rotation -17 to +17 degrees, lifted by a centre-weighted offset, centre card on top. Each card bobs 7 px on its own 4.4 to 6.2 s loop and lifts 18 px on hover. On a fine pointer the hand shifts against the cursor; on scroll it drifts down slower than the page. Entry: cards rise from 460 px, staggered 0.08 s.

### Pinned portal scenes
Three scenes (lilac to paper, paper to umber, umber to umber) each pin for 115% of a viewport. A card (waves, diamond, check) arrives tilted and small, settles, then grows by `max(width, height)` ratio times 1.08 until it covers the screen, with a plate label (Try it yourself, The numbers, How it decides) that is removed once outgrown. At full cover the destination ground fades in as a clean cut and the next chapter is already beneath the portal (`margin-top: -100svh`), so no blank page appears. The next heading's letters then roll in.

### Call player (chapter 03)
A stage on paper: caller label and rule, ten digit slots (underlined, a gap slot at the number's split; filled slots underline in ink, green when Dhairya is the agent, a red slashed slot for a lost digit), a waveform line of bars with a moving playhead, dashed pause tags, and decision markers (red `cut`, green `open`) in pills. Captions show what the caller said (spoken words turn from `#646b63` to ink) and what the agent says. Controls: a green pill **answer button** with a white disc and phone icon (inverts to black "again"), a status line, and a tally of rows washed green or red.

### Hold-to-pause demo
A large black disc (180 to 240 px) with a progress ring (track in `--rule`, fill in green, 4 px, round caps) and a running time. The visitor holds it to pause mid-number; beside it a list of agents (fixed timers and Dhairya) turns red when cut in and green when done. Dhairya's row has a 2 px green inset outline. On tablet and phone the layout stacks and the disc centres.

### Results chart
An SVG plot on umber: cut-in rate against wait. Timers are dashed `#ff9c8c` curves with hollow points, Smart Turn a hollow neutral point, Dhairya a solid `#74dca0` point with a halo and a larger label. Axis and text use `--ink-2`; grid uses `--rule`. Above it three big figures in Gilda Display (3 to 8 rem) with small Switzer units; below it a figures table where Dhairya's row is highlighted `#12351f` with `#8ef0b4` text.

### Ending footer
Black, one full viewport: a "Get in touch" line, the logo tile, a closing line, a ghost wordmark (Rozha One, `#7a7a7a`, one line, with धैर्य) over a `#5c5c5c` rule, then a three-column footer (links, wordmark in lilac pink, links) that stacks centred at 700 px. The footer link to the repository appears when `data-repo` is set on `<body>`.

### Loader
A lilac ground with a deck of fourteen cards in the centre and a Rozha One percentage counter beneath. The cards rise in, stagger 0.05 s, with deterministic rotations; the top card is a black card with a lilac-pink border, the logo and the wordmark. The counter eases to 90% in 1.5 s and waits for fonts and data (`dhairya:ready`, or a 6 s limit), then runs to 100%. The deck then **spirals away** (each card flung along a rotating angle at 1.4 x scale, 1.05 s `power2.in`, reversed stagger), the lilac ground lifts up, and the landing intro starts underneath. Page content is `inert` until the loader leaves; a 12 s safety net removes it regardless.

### Fold rows and pickers (details)
Details use `<details>` rows with a plus-in-circle that rotates 45 degrees when open. Picker and filter buttons are 1.5 px outlined, 8 px radius, min height 42 px; a pressed filter inverts to ink on ground.

## 8. Motion

- **Smooth scroll:** Lenis, `lerp: 0.1`, wheel multiplier 1, driven from the GSAP ticker and synced to ScrollTrigger (`lagSmoothing(0)`). In-page links scroll over 1.5 s with an ease-out quartic.
- **Easing:** `--ease: cubic-bezier(0.22, 1, 0.36, 1)` for hover and state transitions (CTA lift, card lift, fold toggle, hold press); GSAP `expo.out` for reveals, `power2` / `power3` / `power4` for movement.
- **Reveals:** headings split into letters, each rising from 118% in a masked word, 1.1 s `expo.out`, 0.014 s stagger, once. Headings just after a portal wait until the portal leaves.
- **Snap to whole pages:** 170 ms after scrolling stops inside a short stretch (landing, problem, why, ending, each portal at start, 27% and end), the page glides 0.85 s to the nearest resting point in the direction of travel. Arriving just inside a long chapter, it goes to the chapter's start. Long chapters scroll freely.
- **Reduced motion and `?still`:** `scroll.js` returns before registering GSAP or Lenis; the loader is removed, headings stay visible, portals are plain bands, scrolling is native. CSS also removes card bobbing and collapses transition durations to 0.01 ms.
- Animate transform and opacity; never layout properties.

## 9. Do's and Don'ts

**Do**
- Re-theme by changing `data-ground`; read `--ink`, `--rule`, `--ground`.
- Use green and red only for open and cut.
- Reuse card art by `<use href="#art-...">`; add a new card as a new `<symbol>` with the same chassis.
- Set Hindi in Anek Devanagari and the wordmark in Rozha One.
- Keep shadows black and low-alpha.
- Keep every motion effect skippable with `?still` and reduced motion.

**Don't**
- Don't use Grail's PP Pangaia file or Grail's artwork; the technique is borrowed, the assets are not.
- Don't add coloured glows or hard offset shadows.
- Don't use Rozha One or Gilda Display for body text, or add a third display face.
- Don't put lilac text on paper or lilac grounds; lilac-pink text is for black and umber only.
- Don't add small-caps labels above headings (eyebrows or kickers) to new surfaces.
- Don't type result figures by hand; the page reads `data.json`.
