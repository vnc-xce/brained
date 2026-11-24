"""Stockage sur disque, en formats portables.

Organisation du dossier de données :

    data/
      cards/<matiere>/<id>.md   une fiche = un fichier Markdown avec en-tête
      reviews.json              état de révision de chaque fiche
      plan.json                 objectifs par matière et réglages

Le reste du code ne passe que par la classe `Store` : une future app mobile ou
une API pourra la remplacer (base SQLite, synchro cloud...) sans toucher à la logique.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict
from datetime import date
from pathlib import Path

from brained.models import Card, Goal, ReviewState, Settings

DAY_NAMES = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]

_QA_RE = re.compile(
    r"^##\s*Question\s*\n(?P<q>.*?)^##\s*R[ée]ponse\s*\n(?P<a>.*)\Z",
    re.S | re.M | re.I,
)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "fiche"


# --- Markdown -----------------------------------------------------------------

def parse_card(text: str, fallback_id: str, fallback_subject: str) -> Card:
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("\n---", 1)
        if len(parts) == 2:
            for line in parts[0].splitlines()[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = parts[1].lstrip("-").lstrip("\n")

    match = _QA_RE.search(body.strip() + "\n")
    if match:
        question, answer = match["q"].strip(), match["a"].strip()
    else:
        question, answer = body.strip(), ""

    tags = [t.strip() for t in meta.get("tags", "").strip("[]").split(",") if t.strip()]
    created = date.fromisoformat(meta["created"]) if meta.get("created") else None
    return Card(
        id=meta.get("id", fallback_id),
        subject=meta.get("subject", fallback_subject),
        title=meta.get("title", fallback_id),
        question=question,
        answer=answer,
        tags=tags,
        created=created,
    )


def render_card(card: Card) -> str:
    lines = [
        "---",
        f"id: {card.id}",
        f"subject: {card.subject}",
        f"title: {card.title}",
    ]
    if card.tags:
        lines.append(f"tags: [{', '.join(card.tags)}]")
    if card.created:
        lines.append(f"created: {card.created.isoformat()}")
    lines.append("---")
    lines.append("")
    if card.is_qa:
        lines += ["## Question", card.question.strip(), "", "## Réponse", card.answer.strip()]
    else:
        lines.append(card.question.strip())
    return "\n".join(lines) + "\n"


# --- JSON helpers -------------------------------------------------------------

def _state_to_json(state: ReviewState) -> dict:
    data = asdict(state)
    for key in ("due", "last_review"):
        data[key] = data[key].isoformat() if data[key] else None
    return data


def _state_from_json(data: dict) -> ReviewState:
    data = dict(data)
    for key in ("due", "last_review"):
        data[key] = date.fromisoformat(data[key]) if data.get(key) else None
    return ReviewState(**data)


def _parse_days(days: list) -> list[int]:
    result = []
    for d in days:
        if isinstance(d, int):
            result.append(d)
        elif str(d).lower()[:3] in DAY_NAMES:
            result.append(DAY_NAMES.index(str(d).lower()[:3]))
        elif str(d).lower() in ("tous", "all", "*"):
            return list(range(7))
    return sorted(set(result))


# --- Store --------------------------------------------------------------------

class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.cards_dir = self.root / "cards"
        self.reviews_path = self.root / "reviews.json"
        self.plan_path = self.root / "plan.json"

    # Fiches
    def load_cards(self) -> list[Card]:
        cards = []
        for path in sorted(self.cards_dir.glob("**/*.md")):
            subject = path.parent.name if path.parent != self.cards_dir else "general"
            cards.append(parse_card(path.read_text(encoding="utf-8"), path.stem, subject))
        return cards

    def save_card(self, card: Card) -> Path:
        path = self.cards_dir / slugify(card.subject) / f"{card.id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_card(card), encoding="utf-8")
        return path

    def new_card_id(self, title: str) -> str:
        existing = {c.id for c in self.load_cards()}
        base = slugify(title)[:50]
        candidate, n = base, 2
        while candidate in existing:
            candidate, n = f"{base}-{n}", n + 1
        return candidate

    # Révisions
    def load_reviews(self) -> dict[str, ReviewState]:
        if not self.reviews_path.exists():
            return {}
        raw = json.loads(self.reviews_path.read_text(encoding="utf-8"))
        return {cid: _state_from_json(s) for cid, s in raw.get("cards", {}).items()}

    def save_reviews(self, reviews: dict[str, ReviewState]) -> None:
        payload = {
            "version": 1,
            "cards": {cid: _state_to_json(s) for cid, s in sorted(reviews.items())},
        }
        self.reviews_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.reviews_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.reviews_path)

    # Plan
    def load_plan(self) -> tuple[list[Goal], Settings]:
        if not self.plan_path.exists():
            return [], Settings()
        raw = json.loads(self.plan_path.read_text(encoding="utf-8"))
        settings = Settings(**raw.get("settings", {}))
        goals = [
            Goal(
                subject=name,
                minutes=int(g.get("minutes", 30)),
                days=_parse_days(g.get("days", ["tous"])),
                priority=int(g.get("priority", 2)),
            )
            for name, g in raw.get("subjects", {}).items()
        ]
        return goals, settings
