from dhairya.entities.slots import AmountSlot, MobileSlot
from dhairya.turn.entity_aware import EntityAwarePolicy
from dhairya.turn.fixed_timer import FixedTimerPolicy
from dhairya.turn.replay import replay
from dhairya.turn.smart_turn import SmartTurnPolicy
from dhairya.turn.types import Decision, StreamEvent

# A call shaped like the probe's: five digits, a 0.8 s pause, five digits.
# Speech 0.3-2.0 s and 2.8-4.5 s. Text arrives about 0.4 s after each pause starts.
SPEECH_END = 4.5
CALL = [
    StreamEvent(0.45, "speech_start"),
    StreamEvent(2.40, "transcript", "नौ आठ सात छह पाँच।"),
    StreamEvent(2.95, "speech_start"),
    StreamEvent(4.90, "transcript", "चार तीन दो एक शून्य।"),
]


def run(policy, events=CALL, slot=None, horizon=12.0):
    return replay(policy, events, slot if slot is not None else MobileSlot(), horizon)


def test_short_timer_cuts_in_during_the_pause():
    out = run(FixedTimerPolicy(500))
    assert out.decision is Decision.END_TURN
    assert out.t < SPEECH_END  # cut in
    assert MobileSlot().evaluate(out.heard).value == "98765"


def test_timer_equal_to_window_fires_on_the_first_segment():
    out = run(FixedTimerPolicy(200))
    assert (out.decision, out.t) == (Decision.END_TURN, 2.40)


def test_long_timer_waits_but_answers_late():
    out = run(FixedTimerPolicy(1500))
    assert out.decision is Decision.END_TURN
    assert out.t > SPEECH_END
    assert abs(out.t - (4.90 + 1.3)) < 0.03  # 1500 ms of silence, 200 already passed
    assert MobileSlot().evaluate(out.heard).value == "9876543210"


def test_speech_resuming_cancels_a_pending_timer():
    out = run(FixedTimerPolicy(700))  # would fire at 2.90; speech resumes at 2.95
    assert out.t < SPEECH_END
    out = run(FixedTimerPolicy(800))  # would fire at 3.00; cancelled at 2.95
    assert out.t > SPEECH_END


def test_dhairya_waits_through_the_pause_and_answers_at_once():
    out = run(EntityAwarePolicy())
    assert out.decision is Decision.END_TURN
    assert out.t == 4.90  # the moment the tenth digit's text arrives
    assert MobileSlot().evaluate(out.heard).value == "9876543210"


def test_dhairya_nudges_when_the_caller_stops_midway():
    out = run(EntityAwarePolicy(hold_cap_s=4.0), events=CALL[:2])
    assert out.decision is Decision.NUDGE
    assert abs(out.t - 6.40) < 0.03


def test_dhairya_gives_an_open_amount_a_grace_period():
    events = [StreamEvent(0.4, "speech_start"), StreamEvent(1.5, "transcript", "teen hazaar")]
    out = run(EntityAwarePolicy(long_grace_ms=1500), events=events, slot=AmountSlot())
    assert out.decision is Decision.END_TURN
    assert abs(out.t - 2.8) < 0.03  # ends on "hazaar": long grace of 1500 ms, 200 already passed


def test_dhairya_gives_a_finished_looking_amount_the_short_grace():
    events = [
        StreamEvent(0.4, "speech_start"),
        StreamEvent(1.5, "transcript", "teen hazaar pachaas"),
    ]
    out = run(EntityAwarePolicy(grace_ms=600), events=events, slot=AmountSlot())
    assert abs(out.t - 1.9) < 0.03  # 600 ms grace, 200 already passed


def test_dhairya_grace_is_cancelled_when_the_amount_continues():
    events = [
        StreamEvent(0.4, "speech_start"),
        StreamEvent(1.5, "transcript", "teen hazaar"),
        StreamEvent(1.8, "speech_start"),
        StreamEvent(3.0, "transcript", "paanch sau rupaye"),
    ]
    out = run(EntityAwarePolicy(grace_ms=600), events=events, slot=AmountSlot())
    assert (out.decision, out.t) == (Decision.END_TURN, 3.0)
    assert AmountSlot().evaluate(out.heard).value == "3500"


def test_dhairya_without_a_slot_falls_back_to_a_timer():
    policy = EntityAwarePolicy(fallback_ms=700)
    out = replay(policy, CALL, None, 12.0)
    assert out.t < SPEECH_END  # behaves like the 700 ms timer


def _with_probabilities(first, second):
    return [
        CALL[0],
        StreamEvent(2.40, "transcript", CALL[1].text, {"smart_turn_p": first}),
        CALL[2],
        StreamEvent(4.90, "transcript", CALL[3].text, {"smart_turn_p": second}),
    ]


def test_smart_turn_ends_when_the_model_says_finished():
    out = run(SmartTurnPolicy(), events=_with_probabilities(0.9, 0.9))
    assert (out.decision, out.t) == (Decision.END_TURN, 2.40)  # cut in at the pause


def test_smart_turn_waits_when_the_model_says_unfinished():
    out = run(SmartTurnPolicy(), events=_with_probabilities(0.1, 0.9))
    assert (out.decision, out.t) == (Decision.END_TURN, 4.90)


def test_smart_turn_falls_back_to_three_seconds_of_silence():
    out = run(SmartTurnPolicy(fallback_s=3.0), events=_with_probabilities(0.1, 0.1))
    assert out.decision is Decision.END_TURN
    assert abs(out.t - (4.90 + 2.8)) < 0.03
