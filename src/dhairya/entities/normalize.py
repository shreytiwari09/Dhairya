"""Indic-aware text clean-up.

Whisper's default normaliser replaces every Unicode mark with a space, which
shreds Devanagari words (matras are marks). This keeps them.
"""

from __future__ import annotations

import re
import unicodedata

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_COMMA_IN_NUMBER = re.compile(r"(?<=\d),(?=\d)")
_ORDINAL_SUFFIX = re.compile(r"(\d+)(st|nd|rd|th)\b")
_NUKTA = "़"
_CHANDRABINDU, _ANUSVARA = "ँ", "ं"
_ZERO_WIDTH = ("‌", "‍")


def normalize_text(text: str) -> str:
    """NFC, lower-case, ASCII digits, punctuation to spaces. Keeps '/' for dates."""
    text = unicodedata.normalize("NFC", text).lower().translate(_DEVANAGARI_DIGITS)
    text = _COMMA_IN_NUMBER.sub("", text)
    text = _ORDINAL_SUFFIX.sub(r"\1", text)
    text = text.replace("₹", " ₹ ")
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        keep = cat[0] in "LMN" or ch in "/₹" or ch in _ZERO_WIDTH
        out.append(ch if keep else " ")
    return " ".join("".join(out).split())


def lex_key(token: str) -> str:
    """Fold spelling variants that do not change the word.

    Drops the nukta (ड़ vs ड), maps chandrabindu to anusvara (पाँच vs पांच) and
    removes zero-width joiners. Used for both lexicon entries and input tokens.
    """
    token = unicodedata.normalize("NFD", token)
    token = token.replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA)
    for zw in _ZERO_WIDTH:
        token = token.replace(zw, "")
    return unicodedata.normalize("NFC", token)


def tokens(text: str) -> list[str]:
    return normalize_text(text).split()
