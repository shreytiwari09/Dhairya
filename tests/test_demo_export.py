import numpy as np

from dhairya.demo.export import build_lane, pick, policy_label, waveform_peaks
from dhairya.entities.slots import MobileSlot
from dhairya.turn.fixed_timer import FixedTimerPolicy

TRACE = {
    "script": {"id": "mobile-000", "truth": "9876543210"},
    "speech_end": 4.5,
    "events": [
        {"t": 0.45, "kind": "speech_start"},
        {"t": 2.40, "kind": "transcript", "text": "नौ आठ सात छह पाँच।"},
        {"t": 2.95, "kind": "speech_start"},
        {"t": 4.90, "kind": "transcript", "text": "चार तीन दो एक शून्य।"},
    ],
}


def test_peaks_have_requested_length_and_peak_at_one():
    samples = np.zeros(2400, dtype=np.int16)
    samples[1000] = -8000
    samples[2000] = 4000
    peaks = waveform_peaks(samples, 240)
    assert len(peaks) == 240
    assert max(peaks) == 1.0
    assert peaks[100] == 1.0
    assert peaks[200] == 0.5
    assert peaks[0] == 0.0


def test_peaks_of_silence_are_zero():
    assert waveform_peaks(np.zeros(1000, dtype=np.int16), 240) == [0.0] * 240


def test_short_timer_lane_is_a_cut_in_with_one_step():
    lane = build_lane(FixedTimerPolicy(500), "Fixed timer 500 ms", TRACE, MobileSlot())
    assert lane["decision"] == "end_turn"
    assert lane["decision_t"] == 2.7
    assert lane["cut_in"] is True
    assert lane["correct"] is False
    assert lane["value"] == "98765"
    assert lane["delay_s"] is None
    (step,) = lane["steps"]
    assert step["heard"] == step["text"]
    assert step["progress"] == "5 of 10 digits"
    assert step["state"] == "incomplete"


def test_long_timer_lane_waits_for_both_segments():
    lane = build_lane(FixedTimerPolicy(1500, window_ms=200), "x", TRACE, MobileSlot())
    assert lane["cut_in"] is False
    assert lane["correct"] is True
    assert lane["value"] == "9876543210"
    assert len(lane["steps"]) == 2
    assert lane["steps"][1]["state"] == "complete"
    assert lane["delay_s"] == round(lane["decision_t"] - 4.5, 3)


def test_pick_prefers_two_groups_then_shortest():
    calls = [
        {"id": "a", "category": "mobile", "groups": [1, 2, 3], "duration_s": 3.0},
        {"id": "b", "category": "mobile", "groups": [1, 2], "duration_s": 9.0},
        {"id": "c", "category": "mobile", "groups": [1, 2], "duration_s": 6.0},
        {"id": "d", "category": "otp", "groups": [1, 2], "duration_s": 5.0},
    ]
    assert [c["id"] for c in pick(calls, per_category=2)] == ["c", "b", "d"]


def test_labels():
    assert policy_label("fixed_1500ms") == "Fixed timer 1500 ms"
    assert policy_label("smart_turn") == "Smart Turn v3.2"
    assert policy_label("dhairya") == "Dhairya"
