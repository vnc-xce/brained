"""Révision espacée : variante simple de SM-2 (celle d'Anki, en plus court).

Notes : 0 = raté, 1 = difficile, 2 = ok, 3 = facile.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

from brained.models import ReviewState

AGAIN, HARD, GOOD, EASY = 0, 1, 2, 3
GRADE_LABELS = {AGAIN: "raté", HARD: "difficile", GOOD: "ok", EASY: "facile"}

MIN_EASE = 1.3


def schedule(state: ReviewState, grade: int, today: date) -> ReviewState:
    """Renvoie le nouvel état après une révision notée `grade` le jour `today`."""
    if grade not in GRADE_LABELS:
        raise ValueError(f"note invalide : {grade}")

    ease = state.ease
    reps = state.reps
    lapses = state.lapses

    if grade == AGAIN:
        reps = 0
        lapses += 1
        interval = 1
        ease = max(MIN_EASE, ease - 0.2)
    else:
        if reps == 0:
            interval = {HARD: 1, GOOD: 1, EASY: 4}[grade]
        elif reps == 1:
            interval = {HARD: 3, GOOD: 6, EASY: 8}[grade]
        else:
            factor = {HARD: 1.2, GOOD: ease, EASY: ease * 1.3}[grade]
            interval = max(state.interval + 1, round(state.interval * factor))
        ease = max(MIN_EASE, ease + {HARD: -0.15, GOOD: 0.0, EASY: 0.15}[grade])
        reps += 1

    history = state.history + [{"date": today.isoformat(), "grade": grade}]
    return replace(
        state,
        ease=round(ease, 3),
        interval=interval,
        reps=reps,
        lapses=lapses,
        due=today + timedelta(days=interval),
        last_review=today,
        history=history,
    )
