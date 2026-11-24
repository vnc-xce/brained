"""Modèles de données, indépendants du stockage et de l'interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Card:
    """Une fiche de révision.

    `question` et `answer` sont remplis pour une fiche question/réponse.
    Pour une fiche de synthèse, `answer` est vide et `question` contient tout le texte.
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
    """État de révision espacée d'une fiche (algorithme SM-2)."""

    ease: float = 2.5
    interval: int = 0  # en jours
    reps: int = 0  # répétitions réussies d'affilée
    due: date | None = None  # None = nouvelle fiche, jamais révisée
    last_review: date | None = None
    lapses: int = 0
    history: list[dict] = field(default_factory=list)

    def is_due(self, today: date) -> bool:
        return self.due is None or self.due <= today


@dataclass
class Goal:
    """Objectif d'apprentissage pour une matière."""

    subject: str
    minutes: int  # durée d'une séance
    days: list[int]  # jours de la semaine (0 = lundi ... 6 = dimanche)
    priority: int = 2  # 1 = haute, 3 = basse


@dataclass
class Settings:
    daily_budget_minutes: int = 90
    new_cards_per_day: int = 10
    review_minutes_per_card: float = 1.0
    # budget différent selon le jour, ex : {"sam": 240}
    budget_by_day: dict[str, int] = field(default_factory=dict)

    def budget_for(self, day: date) -> int:
        key = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"][day.weekday()]
        return int(self.budget_by_day.get(key, self.daily_budget_minutes))
