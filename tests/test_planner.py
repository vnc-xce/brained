from datetime import date

from brained.models import Card, Goal, ReviewState, Settings
from brained.planner import due_cards, plan_day

SATURDAY = date(2026, 11, 28)


def _cards():
    return [Card("j1", "japanese", "j1", "q"), Card("e1", "spanish", "e1", "q")]


def test_due_cards_new_and_late():
    reviews = {"j1": ReviewState(due=date(2026, 11, 20)), "e1": ReviewState(due=date(2026, 12, 30))}
    assert [c.id for c in due_cards(_cards(), reviews, SATURDAY, Settings())] == ["j1"]


def test_plan_includes_scheduled_and_late_subjects():
    goals = [Goal("pottery", 120, [5], 1), Goal("japanese", 30, list(range(7)), 1),
             Goal("spanish", 30, [0, 2], 2)]
    plan = plan_day(goals, _cards(), {}, SATURDAY, Settings(daily_budget_minutes=200))
    subjects = {s.subject: s for s in plan}
    assert subjects["pottery"].minutes == 120
    assert subjects["japanese"].due_cards == 1
    assert "short session" in subjects["spanish"].reason  # not scheduled on Saturday, but a card is due
    assert not any(s.postponed for s in plan)


def test_budget_postpones_low_priority():
    goals = [Goal("pottery", 120, [5], 1), Goal("japanese", 30, [5], 3)]
    plan = plan_day(goals, [], {}, SATURDAY, Settings(daily_budget_minutes=130))
    assert [s.subject for s in plan if s.postponed] == ["japanese"]


def test_budget_by_day():
    goals = [Goal("pottery", 120, [5], 1)]
    plan = plan_day(goals, [], {}, SATURDAY, Settings(daily_budget_minutes=60, budget_by_day={"sat": 180}))
    assert not plan[0].postponed
