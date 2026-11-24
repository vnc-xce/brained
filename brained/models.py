"""Data models, independent of storage and interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class Card:
    """A flashcard.

    `question` and `answer` are both set for a question/answer card.
    For a summary card, `answer` is empty and `question` holds the whole text.
    """

    id: str
    subject: str
    title: str
    question: str
    answer: str = ""
    tags: list[str] = field(default_factory=list)
    created: date | None = None

    @property
    def is_qa(self) -> bool:
        return bool(self.answer.strip())


@dataclass
class ReviewState:
    """Spaced repetition state of a card (SM-2 algorithm)."""

    ease: float = 2.5
    interval: int = 0  # in days
    reps: int = 0  # consecutive successful reviews
    due: date | None = None  # None = new card, never reviewed
    last_review: date | None = None
    lapses: int = 0
    history: list[dict] = field(default_factory=list)

    def is_due(self, today: date) -> bool:
        return self.due is None or self.due <= today


@dataclass
class Goal:
    """Learning goal for a subject."""

    subject: str
    minutes: int  # length of one session
    days: list[int]  # weekdays (0 = Monday ... 6 = Sunday)
    priority: int = 2  # 1 = high, 3 = low


@dataclass
class Settings:
    daily_budget_minutes: int = 90
    new_cards_per_day: int = 10
    review_minutes_per_card: float = 1.0
    # per-day budget override, e.g. {"sat": 240}
    budget_by_day: dict[str, int] = field(default_factory=dict)

    def budget_for(self, day: date) -> int:
        key = DAY_NAMES[day.weekday()]
        return int(self.budget_by_day.get(key, self.daily_budget_minutes))
