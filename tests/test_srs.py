from datetime import date, timedelta

from brained.models import ReviewState
from brained.srs import AGAIN, EASY, GOOD, HARD, schedule

D = date(2026, 1, 1)


def test_good_progression():
    s = schedule(ReviewState(), GOOD, D)
    assert s.interval == 1 and s.due == D + timedelta(days=1)
    s = schedule(s, GOOD, s.due)
    assert s.interval == 6
    s = schedule(s, GOOD, s.due)
    assert s.interval == 15  # 6 * 2.5
    assert len(s.history) == 3


def test_again_resets():
    s = schedule(schedule(schedule(ReviewState(), GOOD, D), GOOD, D), AGAIN, D)
    assert s.reps == 0 and s.interval == 1 and s.lapses == 1
    assert s.ease < 2.5


def test_easy_grows_faster_than_hard():
    base = schedule(schedule(ReviewState(), GOOD, D), GOOD, D)
    assert schedule(base, EASY, D).interval > schedule(base, HARD, D).interval


def test_ease_floor():
    s = ReviewState()
    for _ in range(20):
        s = schedule(s, AGAIN, D)
    assert s.ease >= 1.3
