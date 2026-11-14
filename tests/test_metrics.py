from dhairya.bench.metrics import CallScore, percentile, summarise, wilson


def test_wilson_matches_hand_worked_values():
    low, high = wilson(8, 10)
    assert abs(low - 0.4902) < 0.001 and abs(high - 0.9433) < 0.001
    low, high = wilson(0, 10)
    assert low == 0.0 and abs(high - 0.2775) < 0.001
    assert wilson(0, 0) == (0.0, 0.0)


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5
    assert percentile([0.4], 95) == 0.4
    assert abs(percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95) - 4.8) < 1e-9
    assert percentile([], 50) is None


def _score(cut_in=False, delay=0.4, correct=True, decision="end_turn"):
    return CallScore("x", "mobile", "v", "Nalini", "p", decision, cut_in, delay, correct, "1")


def test_summarise_counts_and_ignores_missing_delays():
    scores = [
        _score(),
        _score(delay=0.6),
        _score(cut_in=True, delay=None, correct=False),
        _score(decision="nudge", delay=None, correct=False),
    ]
    s = summarise("p", scores)
    assert (s.n, s.cut_ins, s.correct, s.nudges) == (4, 1, 2, 1)
    assert s.delay_p50 == 0.5
