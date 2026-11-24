"""Plan du jour : quelles matières travailler, et combien de temps.

V1 à base de règles. Un futur agent IA pourra remplacer `plan_day` en gardant
la même entrée (objectifs, fiches dues) et la même sortie (liste de `Session`).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from datetime import date

from brained.models import Card, Goal, ReviewState, Settings


@dataclass
class Session:
    subject: str
    minutes: int
    due_cards: int
    reason: str
    postponed: bool = False


def due_cards(
    cards: list[Card],
    reviews: dict[str, ReviewState],
    today: date,
    settings: Settings,
    subject: str | None = None,
) -> list[Card]:
    """Fiches à réviser aujourd'hui : d'abord les révisions en retard, puis les nouvelles (limitées)."""
    old, new = [], []
    for card in cards:
        if subject and card.subject != subject:
            continue
        state = reviews.get(card.id)
        if state is None or state.due is None:
            new.append(card)
        elif state.due <= today:
            old.append((state.due, card))
    old.sort(key=lambda x: x[0])
    return [c for _, c in old] + new[: settings.new_cards_per_day]


def plan_day(
    goals: list[Goal],
    cards: list[Card],
    reviews: dict[str, ReviewState],
    today: date,
    settings: Settings,
) -> list[Session]:
    due_by_subject = Counter(c.subject for c in due_cards(cards, reviews, today, settings))
    goals_by_subject = {g.subject: g for g in goals}
    weekday = today.weekday()

    candidates: list[tuple[int, Session]] = []
    for goal in goals:
        if weekday in goal.days:
            n = due_by_subject.get(goal.subject, 0)
            reason = "prévu aujourd'hui"
            if n:
                reason += f", {n} fiche(s) à revoir"
            candidates.append((goal.priority, Session(goal.subject, goal.minutes, n, reason)))

    for subject, n in due_by_subject.items():
        goal = goals_by_subject.get(subject)
        if goal and weekday in goal.days:
            continue
        minutes = max(5, math.ceil(n * settings.review_minutes_per_card))
        priority = goal.priority if goal else 3
        candidates.append(
            (priority, Session(subject, minutes, n, f"{n} fiche(s) à revoir, révision courte"))
        )

    candidates.sort(key=lambda x: (x[0], -x[1].due_cards, x[1].subject))

    plan, used, budget = [], 0, settings.budget_for(today)
    for _, session in candidates:
        if used + session.minutes <= budget:
            used += session.minutes
        else:
            session.postponed = True
        plan.append(session)
    return plan


def week_schedule(goals: list[Goal], start: date) -> list[tuple[date, list[Goal]]]:
    from datetime import timedelta

    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        todays = sorted((g for g in goals if d.weekday() in g.days), key=lambda g: g.priority)
        days.append((d, todays))
    return days
