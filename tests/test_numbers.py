import pytest

from dhairya.entities import lexicon_hi_en as lex
from dhairya.entities.normalize import lex_key, normalize_text
from dhairya.entities.numbers import amount, digit_string


def test_lexicon_covers_hindi_0_to_99_in_both_scripts():
    values = set(lex.HINDI_NUMBERS.values())
    assert values == set(range(100))
    devanagari = {v for k, v in lex.HINDI_NUMBERS.items() if not k.isascii()}
    latin = {v for k, v in lex.HINDI_NUMBERS.items() if k.isascii()}
    assert devanagari == set(range(100))
    assert latin == set(range(100))


def test_no_spelling_maps_to_two_values():
    # _index would silently keep the last one; check the source table has no clash.
    seen: dict[str, int] = {}
    for value, (latin, deva) in lex._HINDI_0_99.items():
        for word in (latin + " " + deva).split():
            key = lex_key(word)
            assert seen.setdefault(key, value) == value, f"{word} is both {seen[key]} and {value}"


def test_normalize_keeps_devanagari_marks_and_folds_digits():
    assert normalize_text("नौ, आठ! सात।") == "नौ आठ सात"
    assert normalize_text("९८७६५ ४३२१०") == "98765 43210"
    assert normalize_text("₹3,500") == "₹ 3500"
    assert normalize_text("23rd June") == "23 june"


def test_lex_key_folds_nukta_and_chandrabindu():
    assert lex_key("पाँच") == lex_key("पांच")
    assert lex_key("हज़ार") == lex_key("हजार")
    assert lex_key("अड़तीस") == lex_key("अडतीस")


@pytest.mark.parametrize(
    ("text", "digits"),
    [
        ("nau aath saat chhe paanch chaar teen do ek shunya", "9876543210"),
        ("नौ आठ सात छह पांच चार तीन दो एक शून्य", "9876543210"),
        ("नौ आठ सात छः पाँच", "98765"),
        ("nine eight seven six five four three two one zero", "9876543210"),
        ("98765 43210", "9876543210"),
        ("९८७६५ ४३२१०", "9876543210"),
        ("ninyanve aath saat", "9987"),  # pair reading: 99 then 8 then 7
        ("अट्ठानवे छिहत्तर चौवन बत्तीस दस", "9876543210"),  # read in pairs
        ("ninety eight seventy six fifty four thirty two ten", "9876543210"),
        ("double nau aath triple saat", "998777"),
        ("डबल नाइन एट सेवन", "9987"),
        ("nau 8 saat six", "9876"),  # mixed
        ("oh nine eight", "098"),
        ("bees paanch", "205"),  # Hindi has one word for 25, so this is 20 then 5
        ("twenty five", "25"),
        # Three digits read together come back from Prisma as one number: 8-9-5 as "895".
        ("आठ सौ पिचानवे", "895"),
        ("पाँच सौ इक्यानवे", "591"),
        ("नौ सौ", "900"),
        ("आठ सौ पाँच", "805"),
        ("eight hundred ninety five", "895"),
        ("नाइन एट। थ्री एट। फ़ोर वन। आठ सौ पिचानवे। पाँच सौ इक्यानवे।", "983841895591"),
    ],
)
def test_digit_string(text, digits):
    assert digit_string(text) == digits


@pytest.mark.parametrize(
    ("text", "digits"),
    [
        ("mera number hai nau aath saat", "987"),
        ("number likh lo", ""),
        ("bata do", ""),  # "do" here is "give", not 2
        ("ek minute", ""),
        ("mere saath aao", ""),
        ("मेरे साथ आओ", ""),  # "साथ" alone is "with", not 7
        ("नौ साथ आठ", "978"),  # next to numbers it is a misheard "सात"
        ("tera number kya hai", ""),
        ("ek do teen", "123"),  # three in a row is a number even if each is ambiguous
        ("nau do ek", "921"),
        ("haan to nau aath do", "982"),
    ],
)
def test_digit_string_ignores_non_number_uses(text, digits):
    assert digit_string(text) == digits


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("teen hazaar paanch sau", 3500),
        ("तीन हज़ार पांच सौ", 3500),
        ("teen hazaar paanch sau pachaas", 3550),
        ("dedh sau", 150),
        ("dhai hazaar", 2500),
        ("sadhe teen hazaar", 3500),
        ("sava lakh", 125000),
        ("paune do lakh", 175000),
        ("ek lakh bees hazaar", 120000),
        ("pandrah sau", 1500),
        ("do crore", 20000000),
        ("sau", 100),
        ("three thousand five hundred", 3500),
        ("twenty five thousand", 25000),
        ("three hundred and fifty", 350),
        ("3500", 3500),
        ("₹3,500", 3500),
        ("3 hazaar 500", 3500),
        ("teen paanch shunya shunya", 3500),  # read digit by digit
        ("pachchis", 25),
    ],
)
def test_amount_value(text, value):
    assert amount(text).value == value


def test_amount_flags():
    assert amount("kitna dena hai").value is None
    assert amount("teen hazaar rupaye").unit_after
    assert not amount("teen hazaar").unit_after
    assert not amount("rupaye teen hazaar").unit_after
    assert amount("sadhe").dangling
    assert amount("teen hazaar aur").dangling
    assert not amount("teen hazaar paanch sau").dangling
