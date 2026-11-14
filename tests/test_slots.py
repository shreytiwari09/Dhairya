import pytest

from dhairya.entities.slots import AmountSlot, DateSlot, MobileSlot, OtpSlot, SlotState

INCOMPLETE, OPEN, COMPLETE = SlotState.INCOMPLETE, SlotState.OPEN, SlotState.COMPLETE


@pytest.mark.parametrize(
    ("text", "state", "value"),
    [
        ("", INCOMPLETE, None),
        ("mera number hai", INCOMPLETE, None),
        ("nau aath saat chhe paanch", INCOMPLETE, "98765"),
        ("nau aath saat chhe paanch chaar teen do ek shunya", COMPLETE, "9876543210"),
        ("नौ आठ सात छह पांच चार तीन दो एक शून्य", COMPLETE, "9876543210"),
        ("98765 43210", COMPLETE, "9876543210"),
        ("shunya nau aath saat chhe paanch chaar teen do ek", INCOMPLETE, "0987654321"),
        ("shunya nau aath saat chhe paanch chaar teen do ek shunya", COMPLETE, "9876543210"),
        ("nau ek nau aath saat chhe paanch chaar teen do", OPEN, "9198765432"),  # +91 or not?
        ("nau ek nau aath saat chhe paanch chaar teen do ek shunya", COMPLETE, "9876543210"),
    ],
)
def test_mobile_slot(text, state, value):
    result = MobileSlot().evaluate(text)
    assert (result.state, result.value) == (state, value)


def test_mobile_slot_segments_arriving_one_by_one():
    slot = MobileSlot()
    heard = ""
    states = []
    for segment in ["mera number hai nau aath", "saat chhe paanch", "chaar teen", "do ek shunya"]:
        heard = f"{heard} {segment}".strip()
        states.append(slot.evaluate(heard).state)
    assert states == [INCOMPLETE, INCOMPLETE, INCOMPLETE, COMPLETE]


def test_mobile_validity():
    assert MobileSlot.is_valid("9876543210")
    assert not MobileSlot.is_valid("1234567890")


@pytest.mark.parametrize(
    ("text", "length", "state", "value"),
    [
        ("chaar do", 4, INCOMPLETE, "42"),
        ("chaar do saat nau", 4, COMPLETE, "4279"),
        ("double chaar saat nau", 4, COMPLETE, "4479"),
        ("otp hai teen teen", 6, INCOMPLETE, "33"),
        ("3 3 5 1 0 8", 6, COMPLETE, "335108"),
    ],
)
def test_otp_slot(text, length, state, value):
    result = OtpSlot(length=length).evaluate(text)
    assert (result.state, result.value) == (state, value)


@pytest.mark.parametrize(
    ("text", "state", "value"),
    [
        ("haan dena hai", INCOMPLETE, None),
        ("teen hazaar", OPEN, "3000"),  # valid, but "paanch sau" may follow
        ("नौ हज़ार।", OPEN, "9000"),
        ("teen hazaar paanch sau", OPEN, "3500"),
        ("teen hazaar paanch sau rupaye", COMPLETE, "3500"),
        ("sadhe", INCOMPLETE, "0"),
        ("teen hazaar aur", INCOMPLETE, "3000"),
        ("₹3,500", OPEN, "3500"),
    ],
)
def test_amount_slot(text, state, value):
    result = AmountSlot().evaluate(text)
    assert (result.state, result.value) == (state, value)


@pytest.mark.parametrize(
    ("text", "state", "value"),
    [
        ("", INCOMPLETE, None),
        ("teis", INCOMPLETE, "23"),
        ("june", INCOMPLETE, None),
        ("teis june", COMPLETE, "23-06"),
        ("तेईस जून", COMPLETE, "23-06"),
        ("june teis", COMPLETE, "23-06"),
        ("23 june 2026", COMPLETE, "23-06-2026"),
        ("23/06", COMPLETE, "23-06"),
        ("twenty third june", COMPLETE, "23-06"),
        ("do june", COMPLETE, "02-06"),
        ("bata do teis june", COMPLETE, "23-06"),  # "do" is "give"; nearest to month wins
        ("pehli march", COMPLETE, "01-03"),
        ("kal", COMPLETE, "kal"),
        ("paanch tareekh", INCOMPLETE, "05"),
        ("साथ। सितम्बर", COMPLETE, "07-09"),  # Prisma heard "सात" as "साथ"
    ],
)
def test_date_slot(text, state, value):
    result = DateSlot().evaluate(text)
    assert (result.state, result.value) == (state, value)


def test_amount_slot_flags_forms_that_usually_continue():
    assert AmountSlot().evaluate("नौ हज़ार").likely_more
    assert AmountSlot().evaluate("चार लाख").likely_more
    assert not AmountSlot().evaluate("नौ हज़ार सात सौ पचास").likely_more
    assert not AmountSlot().evaluate("नौ हज़ार रुपये").likely_more  # complete, not open


def test_mobile_slot_extra_digits_are_counted_and_not_used():
    result = MobileSlot().evaluate("98765 43210 12")
    assert (result.state, result.value, result.extra) == (COMPLETE, "9876543210", 2)


def test_mobile_slot_exactly_ten_digits_has_no_extra():
    assert MobileSlot().evaluate("98765 43210").extra == 0


def test_mobile_slot_91_prefix_is_not_extra():
    result = MobileSlot().evaluate("91 98765 43210")
    assert (result.state, result.value, result.extra) == (COMPLETE, "9876543210", 0)


def test_otp_slot_extra_digits():
    result = OtpSlot(length=4).evaluate("1 2 3 4 5 6")
    assert (result.state, result.value, result.extra) == (COMPLETE, "1234", 2)
    assert OtpSlot(length=4).evaluate("1 2 3 4").extra == 0
