"""Number, multiplier, month and currency words for Hindi and English.

Hindi 0-99 are all irregular, so each has its own entry, in Devanagari and in
the common Latin spellings. Latin spellings vary a lot; add variants here when
a transcript shows a new one.
"""

from __future__ import annotations

from dhairya.entities.normalize import lex_key

# value: (Latin spellings, Devanagari spellings), space-separated
_HINDI_0_99: dict[int, tuple[str, str]] = {
    0: ("shunya sifar", "शून्य सिफर"),
    1: ("ek", "एक"),
    2: ("do", "दो"),
    3: ("teen tin", "तीन"),
    4: ("chaar char", "चार"),
    5: ("paanch panch", "पांच पाच"),
    6: ("chhe che chhah chah chheh chhay", "छह छः छ: छे छै छ"),
    7: ("saat sat", "सात साथ"),  # "साथ" (with) is a common mishearing of "सात"
    8: ("aath ath aat", "आठ"),
    9: ("nau nao", "नौ"),
    10: ("das dus", "दस"),
    11: ("gyarah gyaarah gyara", "ग्यारह"),
    12: ("barah baarah bara", "बारह"),
    13: ("terah tera", "तेरह"),
    14: ("chaudah chauda", "चौदह"),
    15: ("pandrah pandra pandhrah", "पंद्रह पन्द्रह"),
    16: ("solah sola", "सोलह"),
    17: ("satrah satra", "सत्रह"),
    18: ("atharah athaarah athara", "अठारह"),
    19: ("unnis unnees", "उन्नीस"),
    20: ("bees bis", "बीस"),
    21: ("ikkis ikkees", "इक्कीस"),
    22: ("bais baees baais", "बाईस बाइस"),
    23: ("teis teees teyis", "तेईस तेइस"),
    24: ("chaubis chaubees", "चौबीस"),
    25: ("pachchis pachis pachees pacchis", "पच्चीस"),
    26: ("chhabbis chabbis", "छब्बीस"),
    27: ("sattais sattaees", "सत्ताईस सत्ताइस"),
    28: ("atthais athais atthaees", "अट्ठाईस अट्ठाइस अठ्ठाईस"),
    29: ("untis untees", "उनतीस"),
    30: ("tees tis", "तीस"),
    31: ("ikattis iktis ikatees", "इकतीस इकत्तीस"),
    32: ("battis battees", "बत्तीस"),
    33: ("taintis tentis taintees", "तैंतीस"),
    34: ("chauntis chautis", "चौंतीस"),
    35: ("paintis paintees pentis", "पैंतीस"),
    36: ("chhattis chattis", "छत्तीस"),
    37: ("saintis saintees sentis", "सैंतीस"),
    38: ("adtis artis adatis adtees", "अड़तीस"),
    39: ("untalis untaalis", "उनतालीस"),
    40: ("chalis chaalis chalees", "चालीस"),
    41: ("iktalis ikatalis", "इकतालीस"),
    42: ("bayalis byalis", "बयालीस"),
    43: ("taintalis tentalis", "तैंतालीस"),
    44: ("chauvalis chawalis chavalis", "चौवालीस चवालीस"),
    45: ("paintalis pentalis", "पैंतालीस"),
    46: ("chhiyalis chiyalis", "छियालीस"),
    47: ("saintalis sentalis", "सैंतालीस"),
    48: ("adtalis artalis", "अड़तालीस"),
    49: ("unchas unanchas", "उनचास"),
    50: ("pachas pachaas", "पचास"),
    51: ("ikyavan ikyawan", "इक्यावन"),
    52: ("bavan bawan baavan", "बावन"),
    53: ("tirpan tirepan", "तिरपन"),
    54: ("chauvan chauwan chawwan", "चौवन"),
    55: ("pachpan", "पचपन"),
    56: ("chhappan chappan", "छप्पन"),
    57: ("sattavan sattawan", "सत्तावन"),
    58: ("atthavan atthawan athawan", "अट्ठावन अठ्ठावन"),
    59: ("unsath unsaath", "उनसठ"),
    60: ("saath sath", "साठ"),
    61: ("iksath", "इकसठ"),
    62: ("basath", "बासठ"),
    63: ("tirsath", "तिरसठ"),
    64: ("chaunsath chausath", "चौंसठ चौसठ"),
    65: ("painsath pensath", "पैंसठ"),
    66: ("chhiyasath chiyasath", "छियासठ"),
    67: ("sadsath sarsath", "सड़सठ"),
    68: ("adsath arsath", "अड़सठ"),
    69: ("unhattar", "उनहत्तर"),
    70: ("sattar", "सत्तर"),
    71: ("ikhattar", "इकहत्तर"),
    72: ("bahattar", "बहत्तर"),
    73: ("tihattar", "तिहत्तर"),
    74: ("chauhattar", "चौहत्तर"),
    75: ("pachhattar pachattar", "पचहत्तर"),
    76: ("chhihattar chihattar", "छिहत्तर"),
    77: ("sathattar satahattar", "सतहत्तर"),
    78: ("athhattar athattar", "अठहत्तर"),
    79: ("unasi unyasi", "उनासी उन्यासी"),
    80: ("assi", "अस्सी"),
    81: ("ikyasi", "इक्यासी"),
    82: ("bayasi", "बयासी"),
    83: ("tirasi", "तिरासी"),
    84: ("chaurasi", "चौरासी"),
    85: ("pachasi", "पचासी"),
    86: ("chhiyasi chiyasi", "छियासी"),
    87: ("sattasi", "सत्तासी"),
    88: ("atthasi athasi", "अट्ठासी अठ्ठासी"),
    89: ("navasi nawasi", "नवासी"),
    90: ("nabbe nabbay navve", "नब्बे"),
    91: ("ikyanve ikyanave", "इक्यानवे इक्यानबे"),
    92: ("banve banave", "बानवे बानबे"),
    93: ("tiranve tiranave", "तिरानवे तिरानबे"),
    94: ("chauranve chauranave", "चौरानवे चौरानबे"),
    95: ("panchanve pachanve panchanave", "पंचानवे पचानवे पिचानवे पिच्चानवे पंचानबे पचानबे पिचानबे"),
    96: ("chhiyanve chiyanve chhiyanave", "छियानवे छियानबे"),
    97: ("sattanve sattanave", "सत्तानवे सत्तानबे"),
    98: ("atthanve athanve atthanave", "अट्ठानवे अठ्ठानवे अट्ठानबे"),
    99: ("ninyanve ninyanave ninanve", "निन्यानवे निन्यानबे"),
}

# English words, plus the Devanagari spellings a transcript may use for them.
_ENGLISH: dict[int, str] = {
    0: "zero oh ज़ीरो जीरो",
    1: "one वन",
    2: "two टू",
    3: "three थ्री",
    4: "four फोर",
    5: "five फाइव",
    6: "six सिक्स",
    7: "seven सेवन",
    8: "eight एट",
    9: "nine नाइन",
    10: "ten टेन",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    30: "thirty",
    40: "forty fourty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}

_MULTIPLIERS: dict[int, str] = {
    100: "sau hundred सौ हंड्रेड",
    1_000: "hazaar hazar hajar hajaar thousand हज़ार थाउजेंड",
    100_000: "lakh laakh lac lakhs लाख",
    10_000_000: "crore karod karor crores करोड़",
}

# Words that set a fractional count ("dedh sau" = 150, "dhai hazaar" = 2,500).
_FRACTION_VALUES: dict[float, str] = {1.5: "dedh डेढ़", 2.5: "dhai adhai ढाई अढ़ाई"}
# Words that adjust the next number ("sadhe teen" = 3.5, "paune do" = 1.75).
_FRACTION_ADDS: dict[float, str] = {
    0.5: "sadhe saadhe साढ़े",
    0.25: "sava sawa सवा",
    -0.25: "paune पौने",
}

_REPEATS: dict[int, str] = {2: "double डबल", 3: "triple ट्रिपल"}

_CURRENCY = "rupaye rupay rupaiye rupiya rupya rupee rupees rs ₹ रुपये रुपए रुपया रुपय रुपयों"

_MONTHS: dict[int, str] = {
    1: "january jan janvari जनवरी",
    2: "february feb farvari फरवरी",
    3: "march मार्च",
    4: "april aprail अप्रैल",
    5: "may mai मई",
    6: "june joon जून",
    7: "july julai जुलाई",
    8: "august aug agast अगस्त",
    9: "september sept sitambar सितंबर सितम्बर",
    10: "october oct aktubar अक्टूबर अक्तूबर",
    11: "november nov navambar नवंबर नवम्बर",
    12: "december dec disambar दिसंबर दिसम्बर",
}

_ORDINALS: dict[int, str] = {
    1: "first pehli pahli pehla pahla पहली पहला",
    2: "second doosri dusri दूसरी",
    3: "third teesri tisri तीसरी",
    4: "fourth chauthi चौथी",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
    20: "twentieth",
    30: "thirtieth",
}

# Day words that make a date complete on their own.
_RELATIVE_DAYS = "aaj kal parso parson today tomorrow आज कल परसों"

# Words that are also common non-number words ("de do", "ek minute", "mere saath",
# "tera number"). They count as numbers only next to another number word.
_AMBIGUOUS = "ek do one saath sath oh tera bara sola chauda tin sat एक दो साथ"


def _index(table: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for value, entry in table.items():
        words = " ".join(entry) if isinstance(entry, tuple) else entry
        for word in words.split():
            out[lex_key(word)] = value
    return out


HINDI_NUMBERS: dict[str, float] = _index(_HINDI_0_99)
ENGLISH_NUMBERS: dict[str, float] = _index(_ENGLISH)
MULTIPLIERS: dict[str, float] = _index(_MULTIPLIERS)
FRACTION_VALUES: dict[str, float] = _index(_FRACTION_VALUES)
FRACTION_ADDS: dict[str, float] = _index(_FRACTION_ADDS)
REPEATS: dict[str, float] = _index(_REPEATS)
MONTHS: dict[str, float] = _index(_MONTHS)
ORDINALS: dict[str, float] = _index(_ORDINALS)
CURRENCY: frozenset[str] = frozenset(lex_key(w) for w in _CURRENCY.split())
RELATIVE_DAYS: frozenset[str] = frozenset(lex_key(w) for w in _RELATIVE_DAYS.split())
AMBIGUOUS: frozenset[str] = frozenset(lex_key(w) for w in _AMBIGUOUS.split())
