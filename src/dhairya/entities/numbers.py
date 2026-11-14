"""Turn spoken numbers into digits or values.

Two readings, because callers say numbers two ways:
- digit_string: identifiers read digit by digit or in pairs (mobile, OTP, PIN).
- amount: quantities built with sau, hazaar, lakh, crore.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhairya.entities import lexicon_hi_en as lex
from dhairya.entities.normalize import lex_key, tokens


@dataclass(frozen=True)
class Tok:
    text: str
    kind: str  # num | digits | mult | fracval | fracadd | rep | currency | other
    value: float = 0.0
    english: bool = False
    ambiguous: bool = False

    @property
    def numberish(self) -> bool:
        return self.kind in ("num", "digits", "mult", "fracval", "fracadd", "rep")


def classify(token: str) -> Tok:
    key = lex_key(token)
    ambiguous = key in lex.AMBIGUOUS
    if key.isascii() and key.isdigit():
        return Tok(key, "digits", float(int(key)))
    if key in lex.HINDI_NUMBERS:
        return Tok(key, "num", lex.HINDI_NUMBERS[key], ambiguous=ambiguous)
    if key in lex.ENGLISH_NUMBERS:
        return Tok(key, "num", lex.ENGLISH_NUMBERS[key], english=True, ambiguous=ambiguous)
    if key in lex.MULTIPLIERS:
        return Tok(key, "mult", lex.MULTIPLIERS[key])
    if key in lex.FRACTION_VALUES:
        return Tok(key, "fracval", lex.FRACTION_VALUES[key])
    if key in lex.FRACTION_ADDS:
        return Tok(key, "fracadd", lex.FRACTION_ADDS[key])
    if key in lex.REPEATS:
        return Tok(key, "rep", lex.REPEATS[key])
    if key in lex.CURRENCY:
        return Tok(key, "currency")
    return Tok(key, "other")


def number_tokens(text: str) -> list[Tok]:
    """Classify tokens, demoting ambiguous words that stand apart from any number.

    "de do" and "ek minute" contain number words that are not numbers. A run of
    number words counts only if it holds at least one unambiguous member, or is
    three or more long.
    """
    toks = [classify(t) for t in tokens(text)]
    out = list(toks)
    i = 0
    while i < len(toks):
        if not toks[i].numberish:
            i += 1
            continue
        j = i
        while j < len(toks) and toks[j].numberish:
            j += 1
        run = toks[i:j]
        if all(t.ambiguous for t in run) and len(run) < 3:
            for k in range(i, j):
                out[k] = Tok(toks[k].text, "other")
        i = j
    return out


def _is_english_tens(tok: Tok) -> bool:
    return tok.kind == "num" and tok.english and tok.value >= 20 and tok.value % 10 == 0


def _is_english_unit(tok: Tok) -> bool:
    return tok.kind == "num" and tok.english and 1 <= tok.value <= 9


def digit_string(text: str) -> str:
    """Digits of an identifier, in order.

    A word from 10 to 99 gives two digits ("ninyanve" -> "99"), which is how
    numbers are read in pairs. "double seven" -> "77". Multiplier words are
    ignored: identifiers are not quantities.
    """
    toks = number_tokens(text)
    out: list[str] = []
    i = 0
    while i < len(toks):
        tok = toks[i]
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if tok.kind == "digits":
            out.append(tok.text)
        elif tok.kind == "rep" and nxt is not None and _single_digit(nxt) is not None:
            out.append(_single_digit(nxt) * int(tok.value))
            i += 1
        elif tok.kind == "num" and 1 <= tok.value <= 9 and nxt is not None and _is_hundred(nxt):
            # "आठ सौ पिचानवे": three digits read together, which Prisma writes as 895.
            rest, used = _two_digit_after(toks, i + 2)
            out.append(f"{int(tok.value)}{rest:02d}")
            i += 1 + used
        elif tok.kind == "num":
            if _is_english_tens(tok) and nxt is not None and _is_english_unit(nxt):
                out.append(str(int(tok.value + nxt.value)))
                i += 1
            else:
                out.append(str(int(tok.value)))
        i += 1
    return "".join(out)


def _is_hundred(tok: Tok) -> bool:
    return tok.kind == "mult" and tok.value == 100


def _two_digit_after(toks: list[Tok], at: int) -> tuple[int, int]:
    """The 0-99 part that follows "X hundred", and how many tokens it used."""
    if at >= len(toks) or toks[at].kind != "num":
        return 0, 0
    tok = toks[at]
    nxt = toks[at + 1] if at + 1 < len(toks) else None
    if _is_english_tens(tok) and nxt is not None and _is_english_unit(nxt):
        return int(tok.value + nxt.value), 2
    return int(tok.value), 1


def _single_digit(tok: Tok) -> str | None:
    if tok.kind == "num" and 0 <= tok.value <= 9:
        return str(int(tok.value))
    if tok.kind == "digits" and len(tok.text) == 1:
        return tok.text
    return None


@dataclass(frozen=True)
class Amount:
    value: int | None  # None when the text holds no number
    unit_after: bool  # a currency word follows the last number word
    dangling: bool  # ends on a word that needs a number after it ("sadhe", "aur")
    used_multiplier: bool
    ends_on_multiplier: bool = False  # "nau hazaar": hundreds or tens often follow


_CONNECTORS = frozenset({"aur", "and", "और"})


def amount(text: str) -> Amount:
    """Read a quantity: "teen hazaar paanch sau" -> 3500, "dhai lakh" -> 250000."""
    toks = number_tokens(text)
    total = 0.0
    current: float | None = None
    pending_add: float | None = None
    prev: Tok | None = None
    seen = used_mult = bare_sequence = False
    last_number_at = last_currency_at = -1

    for i, tok in enumerate(toks):
        if tok.kind in ("num", "digits"):
            seen = True
            last_number_at = i
            if pending_add is not None:
                current = tok.value + pending_add
                pending_add = None
            elif current is not None and prev is not None and _is_english_tens(prev):
                current = current + tok.value if _is_english_unit(tok) else tok.value
            elif current is not None:
                bare_sequence = True  # two numbers with no multiplier between them
                current = tok.value
            else:
                current = tok.value
        elif tok.kind == "fracval":
            seen = True
            last_number_at = i
            current = tok.value
        elif tok.kind == "fracadd":
            seen = True
            last_number_at = i
            pending_add = tok.value
        elif tok.kind == "mult":
            seen = used_mult = True
            last_number_at = i
            if current is not None:
                count = current
            elif pending_add is not None:
                count = 1 + pending_add  # "sava lakh" = 1.25 lakh
            else:
                count = 1.0
            total += count * tok.value
            current = pending_add = None
        elif tok.kind == "currency":
            last_currency_at = i
        if tok.numberish:
            prev = tok
        elif tok.kind != "currency":
            prev = None

    if not seen:
        return Amount(None, False, False, False)
    if bare_sequence and not used_mult:
        digits = digit_string(text)  # amount read digit by digit: "teen paanch shunya shunya"
        value = int(digits) if digits else None
    else:
        value = int(round(total + (current or 0.0)))
    dangling = pending_add is not None or (bool(toks) and toks[-1].text in _CONNECTORS)
    ends_on_mult = last_number_at >= 0 and toks[last_number_at].kind == "mult"
    return Amount(value, last_currency_at > last_number_at, dangling, used_mult, ends_on_mult)
