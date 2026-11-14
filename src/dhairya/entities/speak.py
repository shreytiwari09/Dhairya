"""Turn a captured value back into words for the agent to read aloud.

Timbre reads numbers best when they are written as words, so digits are never
sent to it as numerals.
"""

from __future__ import annotations

from dhairya.entities.lexicon_hi_en import _HINDI_0_99

HINDI = {value: words[1].split()[0] for value, words in _HINDI_0_99.items()}
MONTHS = "जनवरी फरवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर".split()
_UNITS = ((10_000_000, "करोड़"), (100_000, "लाख"), (1_000, "हज़ार"), (100, "सौ"))


def spoken_digits(digits: str) -> str:
    return " ".join(HINDI[int(d)] for d in digits)


def spoken_number(n: int) -> str:
    parts = []
    for size, word in _UNITS:
        count, n = divmod(n, size)
        if count:
            parts.append(f"{spoken_number(count)} {word}")
    if n or not parts:
        parts.append(HINDI[n])
    return " ".join(parts)


def spoken_value(slot_name: str, value: str) -> str:
    """Words for a slot's canonical value: digits, an amount, or DD-MM[-YYYY]."""
    if slot_name == "amount":
        return f"{spoken_number(int(value))} रुपये"
    if slot_name == "date":
        parts = value.split("-")
        if len(parts) < 2 or not parts[0].isdigit():
            return value  # a relative day such as "kal" is already a word
        return f"{HINDI[int(parts[0])]} {MONTHS[int(parts[1]) - 1]}"
    return spoken_digits(value)
