"""Seeded generator of synthetic caller scripts.

Every value is made up. The truth of each script is computed from the numbers
it was built from, never by parsing its own text, so the benchmark does not
grade the parser against itself.

    uv run python -m dhairya.bench.scripts --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from dhairya.config import settings
from dhairya.entities.lexicon_hi_en import _HINDI_0_99

HINDI = {value: words[1].split()[0] for value, words in _HINDI_0_99.items()}
ENGLISH_DIGITS = "zero one two three four five six seven eight nine".split()
MONTHS = "जनवरी फरवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर".split()
# v2.5 voices read a group of digits fluently (README: What we learned about the API).
VOICES = ["Nalini", "Bhavna", "Deepak", "Omkar"]
PAUSES_S = [0.4, 0.6, 0.8, 1.0, 1.3]
MOBILE_GROUPINGS = [(5, 5), (3, 3, 4), (4, 3, 3), (2, 2, 2, 2, 2), (10,)]


@dataclass(frozen=True)
class Script:
    id: str
    category: str  # mobile | otp | amount | date
    slot: str  # mobile | otp4 | otp6 | amount | date
    groups: list[str]  # what the caller says, one entry per breath group
    pauses_s: list[float]  # silence between groups; one shorter than groups
    truth: str
    voice: str
    variant: str  # how it was built, for breakdowns


def _digits_hi(digits: str, doubles: bool) -> str:
    out, i = [], 0
    while i < len(digits):
        if doubles and i + 1 < len(digits) and digits[i] == digits[i + 1]:
            out.append(f"डबल {HINDI[int(digits[i])]}")
            i += 2
        else:
            out.append(HINDI[int(digits[i])])
            i += 1
    return " ".join(out)


def _digits_en(digits: str) -> str:
    return " ".join(ENGLISH_DIGITS[int(d)] for d in digits)


def _split(digits: str, sizes: tuple[int, ...]) -> list[str]:
    out, at = [], 0
    for size in sizes:
        out.append(digits[at : at + size])
        at += size
    return out


def _pauses(rng: random.Random, groups: int) -> list[float]:
    return [rng.choice(PAUSES_S) for _ in range(groups - 1)]


def _mobile(rng: random.Random, i: int) -> Script:
    number = rng.choice("6789") + "".join(rng.choice("0123456789") for _ in range(9))
    sizes = MOBILE_GROUPINGS[i % len(MOBILE_GROUPINGS)]
    style = ["hindi", "hindi", "hindi_double", "english"][i % 4]
    parts = _split(number, sizes)
    if style == "english":
        groups = [_digits_en(p) for p in parts]
    else:
        groups = [_digits_hi(p, doubles=style == "hindi_double") for p in parts]
    if i % 3 == 0:
        groups[0] = "मेरा मोबाइल नंबर है " + groups[0]
    variant = f"{'-'.join(map(str, sizes))} {style}"
    return Script(f"mobile-{i:03d}", "mobile", "mobile", groups, _pauses(rng, len(groups)),
                  number, rng.choice(VOICES), variant)  # fmt: skip


def _otp(rng: random.Random, i: int) -> Script:
    length = 6 if i % 2 == 0 else 4
    code = "".join(rng.choice("0123456789") for _ in range(length))
    sizes = [(3, 3), (2, 2), (6,), (4,), (2, 2, 2), (2, 2)][i % 6]
    if sum(sizes) != length:
        sizes = (3, 3) if length == 6 else (2, 2)
    groups = [_digits_hi(p, doubles=False) for p in _split(code, sizes)]
    if i % 4 == 0:
        groups[0] = "ओटीपी है " + groups[0]
    return Script(f"otp-{i:03d}", "otp", f"otp{length}", groups, _pauses(rng, len(groups)),
                  code, rng.choice(VOICES), "-".join(map(str, sizes)))  # fmt: skip


_SPECIAL_AMOUNTS = [
    ("ढाई हज़ार", 2500),
    ("डेढ़ लाख", 150000),
    ("साढ़े तीन हज़ार", 3500),
    ("पंद्रह सौ", 1500),
    ("सवा लाख", 125000),
    ("डेढ़ सौ", 150),
]


def _amount(rng: random.Random, i: int) -> Script:
    unit = i % 5 != 0  # four in five end with "रुपये"
    kind = i % 4
    if kind == 0:
        text, value = _SPECIAL_AMOUNTS[(i // 4) % len(_SPECIAL_AMOUNTS)]
        groups, variant = [text], "special"
    elif kind == 3:
        lakh, thousand = rng.randint(1, 9), rng.choice([10, 20, 25, 50])
        groups = [f"{HINDI[lakh]} लाख", f"{HINDI[thousand]} हज़ार"]
        value, variant = lakh * 100000 + thousand * 1000, "lakh+hazaar"
    else:
        thousand, hundred = (
            rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 20, 25]),
            rng.randint(1, 9),
        )
        groups = [f"{HINDI[thousand]} हज़ार", f"{HINDI[hundred]} सौ"]
        value, variant = thousand * 1000 + hundred * 100, "hazaar+sau"
    if unit:
        groups[-1] += " रुपये"
    variant += " with unit" if unit else " no unit"
    return Script(f"amount-{i:03d}", "amount", "amount", groups, _pauses(rng, len(groups)),
                  str(value), rng.choice(VOICES), variant)  # fmt: skip


def _date(rng: random.Random, i: int) -> Script:
    day, month = rng.randint(1, 28), rng.randint(1, 12)
    if i % 4 == 0:
        groups, variant = [f"{HINDI[day]} {MONTHS[month - 1]}"], "one group"
    elif i % 4 == 1:
        groups, variant = [f"{HINDI[day]} तारीख", MONTHS[month - 1]], "day tareekh | month"
    else:
        groups, variant = [HINDI[day], MONTHS[month - 1]], "day | month"
    return Script(f"date-{i:03d}", "date", "date", groups, _pauses(rng, len(groups)),
                  f"{day:02d}-{month:02d}", rng.choice(VOICES), variant)  # fmt: skip


COUNTS = {"mobile": 80, "otp": 40, "amount": 48, "date": 32}
_MAKERS = {"mobile": _mobile, "otp": _otp, "amount": _amount, "date": _date}


def generate(seed: int) -> list[Script]:
    rng = random.Random(seed)
    return [_MAKERS[cat](rng, i) for cat, count in COUNTS.items() for i in range(count)]


def load(path: Path) -> list[Script]:
    return [Script(**item) for item in json.loads(path.read_text())]


def scripts_path() -> Path:
    return settings().data_dir / "scripts" / "scripts.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    scripts = generate(args.seed)
    path = scripts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(s) for s in scripts], ensure_ascii=False, indent=1))
    print(f"{len(scripts)} scripts written to {path}")


if __name__ == "__main__":
    main()
