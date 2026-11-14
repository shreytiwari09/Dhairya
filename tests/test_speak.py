import pytest

from dhairya.entities.numbers import amount, digit_string
from dhairya.entities.slots import DateSlot
from dhairya.entities.speak import spoken_digits, spoken_number, spoken_value


@pytest.mark.parametrize("digits", ["9876543210", "0042", "700126"])
def test_spoken_digits_read_back_by_the_parser(digits):
    assert digit_string(spoken_digits(digits)) == digits


@pytest.mark.parametrize("n", [0, 7, 99, 100, 150, 3500, 9700, 120000, 625000, 20000000, 12345678])
def test_spoken_number_reads_back_by_the_parser(n):
    assert amount(spoken_number(n)).value == n


def test_spoken_value_by_slot():
    assert spoken_value("amount", "3500").endswith("रुपये")
    assert DateSlot().evaluate(spoken_value("date", "23-06")).value == "23-06"
    assert digit_string(spoken_value("otp6", "335108")) == "335108"
    assert spoken_value("date", "kal") == "kal"
