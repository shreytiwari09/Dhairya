"""Slots: given everything heard so far, is the value finished?

Each slot is a pure function of the accumulated text, so text that arrives
split across stream segments needs no special handling: join and re-evaluate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from dhairya.entities import lexicon_hi_en as lex
from dhairya.entities.normalize import normalize_text, tokens
from dhairya.entities.numbers import Tok, amount, classify, digit_string


class SlotState(Enum):
    INCOMPLETE = "incomplete"  # more must follow: keep waiting
    OPEN = "open"  # valid as it stands but may continue: wait a short grace period
    COMPLETE = "complete"  # finished: answer now


@dataclass(frozen=True)
class SlotResult:
    state: SlotState
    value: str | None
    progress: str  # human-readable, for the demo timeline
    likely_more: bool = False  # OPEN only: the form heard so far usually continues
    extra: int = 0  # digits heard beyond the ones used (mobile, OTP); the caller said too many


class Slot(Protocol):
    name: str

    def evaluate(self, text: str) -> SlotResult: ...


@dataclass(frozen=True)
class MobileSlot:
    """Indian mobile number: 10 digits, first digit 6-9."""

    name: str = "mobile"

    def evaluate(self, text: str) -> SlotResult:
        digits = digit_string(text)
        if len(digits) >= 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) >= 11 and digits.startswith("0"):
            digits = digits[1:]
        progress = f"{min(len(digits), 10)} of 10 digits"
        extra = max(0, len(digits) - 10)
        if len(digits) < 10:
            return SlotResult(SlotState.INCOMPLETE, digits or None, progress)
        if len(digits) == 10 and digits.startswith("0"):
            return SlotResult(SlotState.INCOMPLETE, digits, progress)  # leading 0 is a prefix
        if len(digits) in (10, 11) and digits.startswith("91"):
            # Could be a full number starting 91, or a +91 prefix with more to come.
            return SlotResult(SlotState.OPEN, digits[:10], progress, extra=extra)
        return SlotResult(SlotState.COMPLETE, digits[:10], progress, extra=extra)

    @staticmethod
    def is_valid(value: str) -> bool:
        return len(value) == 10 and value[0] in "6789"


@dataclass(frozen=True)
class OtpSlot:
    """Fixed-length code: OTP (usually 4 or 6) or PIN."""

    length: int = 6
    name: str = "otp"

    def evaluate(self, text: str) -> SlotResult:
        digits = digit_string(text)
        progress = f"{min(len(digits), self.length)} of {self.length} digits"
        if len(digits) < self.length:
            return SlotResult(SlotState.INCOMPLETE, digits or None, progress)
        extra = len(digits) - self.length
        return SlotResult(SlotState.COMPLETE, digits[: self.length], progress, extra=extra)


@dataclass(frozen=True)
class AmountSlot:
    """Rupee amount. Content alone cannot always tell if it is finished:
    "teen hazaar" is a valid amount and also the start of "teen hazaar paanch sau".
    """

    name: str = "amount"

    def evaluate(self, text: str) -> SlotResult:
        parsed = amount(text)
        if parsed.value is None:
            return SlotResult(SlotState.INCOMPLETE, None, "no amount yet")
        value = str(parsed.value)
        if parsed.dangling:
            return SlotResult(SlotState.INCOMPLETE, value, f"{value}, expecting more")
        if parsed.unit_after:
            return SlotResult(SlotState.COMPLETE, value, f"{value} rupees")
        return SlotResult(
            SlotState.OPEN, value, f"{value}, may continue", parsed.ends_on_multiplier
        )


_NUMERIC_DATE = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?\b")


@dataclass(frozen=True)
class DateSlot:
    """Day and month, with an optional year. Value is DD-MM or DD-MM-YYYY."""

    name: str = "date"

    def evaluate(self, text: str) -> SlotResult:
        norm = normalize_text(text)
        match = _NUMERIC_DATE.search(norm)
        if match and 1 <= int(match[1]) <= 31 and 1 <= int(match[2]) <= 12:
            value = f"{int(match[1]):02d}-{int(match[2]):02d}"
            if match[3]:
                value += f"-{match[3]}"
            return SlotResult(SlotState.COMPLETE, value, value)

        # No demotion of ambiguous words here: in "do june", "do" is the day.
        toks = [classify(t) for t in tokens(text)]
        for tok in toks:
            if tok.text in lex.RELATIVE_DAYS:
                return SlotResult(SlotState.COMPLETE, tok.text, tok.text)

        month_at = next((i for i, t in enumerate(toks) if t.text in lex.MONTHS), None)
        month = int(lex.MONTHS[toks[month_at].text]) if month_at is not None else None
        day = self._day(toks, month_at)
        year = next(
            (t.text for t in toks if t.kind == "digits" and len(t.text) == 4 and t.text[0] in "12"),
            None,
        )
        if day is not None and month is not None:
            value = f"{day:02d}-{month:02d}" + (f"-{year}" if year else "")
            return SlotResult(SlotState.COMPLETE, value, value)
        if day is not None:
            return SlotResult(SlotState.INCOMPLETE, f"{day:02d}", f"day {day}, no month yet")
        if month is not None:
            return SlotResult(SlotState.INCOMPLETE, None, "month only, no day yet")
        return SlotResult(SlotState.INCOMPLETE, None, "no date yet")

    @staticmethod
    def _day(toks: list[Tok], month_at: int | None) -> int | None:
        """Day of month: "teis", "23", "twenty third", "pehli".

        With a month present, the candidate nearest the month wins, so stray
        number words elsewhere ("bata do, teis june") do not become the day.
        With no month yet, the most recent candidate wins.
        """
        candidates: list[tuple[int, int]] = []  # (token index, day)
        i = 0
        while i < len(toks):
            tok = toks[i]
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if tok.text in lex.ORDINALS:
                candidates.append((i, int(lex.ORDINALS[tok.text])))
            elif tok.kind in ("num", "digits") and 1 <= tok.value <= 31:
                value = int(tok.value)
                if tok.english and value in (20, 30) and nxt is not None:
                    if nxt.text in lex.ORDINALS and lex.ORDINALS[nxt.text] <= 9:
                        value += int(lex.ORDINALS[nxt.text])
                        i += 1
                    elif nxt.kind == "num" and nxt.english and 1 <= nxt.value <= 9:
                        value += int(nxt.value)
                        i += 1
                if value <= 31:
                    candidates.append((i, value))
            i += 1
        if not candidates:
            return None
        if month_at is None:
            return candidates[-1][1]
        return min(candidates, key=lambda c: abs(c[0] - month_at))[1]
