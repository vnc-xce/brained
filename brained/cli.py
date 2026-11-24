"""Interface en ligne de commande. Ne contient pas de logique métier."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from brained import planner, srs
from brained.models import Card, ReviewState
from brained.storage import Store

DAY_LABELS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def _store(args) -> Store:
    root = args.data or os.environ.get("BRAINED_DATA") or "data"
    return Store(Path(root).expanduser())


def _today(args) -> date:
    return date.fromisoformat(args.date) if args.date else date.today()


def _read_multiline(prompt: str) -> str:
    print(f"{prompt} (termine par une ligne vide) :")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


# --- Commandes ----------------------------------------------------------------

def cmd_add(args) -> int:
    store = _store(args)
    subject = args.subject or input("Matière : ").strip()
    title = args.title or input("Titre : ").strip()
    if args.question is not None:
        question, answer = args.question, args.answer or ""
    else:
        question = _read_multiline("Question (ou texte de synthèse)")
        answer = _read_multiline("Réponse (vide pour une fiche de synthèse)")
    card = Card(
        id=store.new_card_id(title),
        subject=subject.lower(),
        title=title,
        question=question,
        answer=answer,
        tags=[t.strip() for t in (args.tags or "").split(",") if t.strip()],
        created=_today(args),
    )
    path = store.save_card(card)
    print(f"Fiche créée : {path}")
    return 0


def cmd_list(args) -> int:
    store = _store(args)
    reviews = store.load_reviews()
    cards = store.load_cards()
    if args.subject:
        cards = [c for c in cards if c.subject == args.subject]
    if not cards:
        print("Aucune fiche.")
        return 0
    for card in cards:
        state = reviews.get(card.id)
        due = state.due.isoformat() if state and state.due else "nouvelle"
        print(f"[{card.subject}] {card.title}  ({card.id}, prochaine révision : {due})")
    return 0


def _show_card(card: Card, index: int, total: int) -> None:
    print("\n" + "─" * 50)
    print(f"{index}/{total}  [{card.subject}]  {card.title}")
    print("─" * 50)
    print(card.question)


def cmd_review(args) -> int:
    store = _store(args)
    today = _today(args)
    _, settings = store.load_plan()
    reviews = store.load_reviews()
    cards = planner.due_cards(store.load_cards(), reviews, today, settings, args.subject)
    if args.limit:
        cards = cards[: args.limit]
    if not cards:
        print("Rien à réviser aujourd'hui. 🎉")
        return 0

    print(f"{len(cards)} fiche(s) à réviser. Entrée pour voir la réponse, q pour quitter.")
    done = Counter()
    for i, card in enumerate(cards, 1):
        _show_card(card, i, len(cards))
        try:
            if card.is_qa:
                if input("\n[Entrée = réponse] ").strip().lower() == "q":
                    break
                print("\n" + card.answer)
            prompt = "\nNote : 1 raté · 2 difficile · 3 ok · 4 facile · q quitter > "
            while True:
                choice = input(prompt).strip().lower()
                if choice == "q" or choice in {"1", "2", "3", "4"}:
                    break
        except EOFError:
            break
        if choice == "q":
            break
        grade = int(choice) - 1
        state = reviews.get(card.id, ReviewState())
        reviews[card.id] = srs.schedule(state, grade, today)
        store.save_reviews(reviews)  # sauvegarde à chaque fiche
        done[grade] += 1
        print(f"→ prochaine révision dans {reviews[card.id].interval} jour(s)")

    total = sum(done.values())
    if total:
        summary = ", ".join(f"{done[g]} {srs.GRADE_LABELS[g]}" for g in sorted(done))
        print(f"\nSéance terminée : {total} fiche(s) révisée(s) ({summary}).")
    return 0


def cmd_today(args) -> int:
    store = _store(args)
    today = _today(args)
    goals, settings = store.load_plan()
    plan = planner.plan_day(goals, store.load_cards(), store.load_reviews(), today, settings)
    print(f"{DAY_LABELS[today.weekday()]} {today.isoformat()}")
    if not plan:
        print("Rien de prévu aujourd'hui. Ajoute des objectifs dans plan.json.")
        return 0
    total = 0
    for s in plan:
        if s.postponed:
            continue
        total += s.minutes
        print(f"  • {s.subject:<15} {s.minutes:>3} min   ({s.reason})")
    postponed = [s for s in plan if s.postponed]
    print(f"Total : {total} min sur {settings.budget_for(today)} min de budget.")
    if postponed:
        print("Reporté faute de temps : " + ", ".join(s.subject for s in postponed))
    return 0


def cmd_week(args) -> int:
    store = _store(args)
    goals, _ = store.load_plan()
    for d, todays in planner.week_schedule(goals, _today(args)):
        items = ", ".join(f"{g.subject} {g.minutes} min" for g in todays) or "repos"
        print(f"{DAY_LABELS[d.weekday()]:<9} {d.isoformat()}  {items}")
    return 0


def cmd_stats(args) -> int:
    store = _store(args)
    today = _today(args)
    _, settings = store.load_plan()
    cards = store.load_cards()
    reviews = store.load_reviews()
    due = Counter(c.subject for c in planner.due_cards(cards, reviews, today, settings))
    total = Counter(c.subject for c in cards)
    if not cards:
        print("Aucune fiche.")
        return 0
    print(f"{'Matière':<15} {'Fiches':>6} {'À revoir':>9}")
    for subject in sorted(total):
        print(f"{subject:<15} {total[subject]:>6} {due.get(subject, 0):>9}")
    return 0


def cmd_init(args) -> int:
    store = _store(args)
    store.cards_dir.mkdir(parents=True, exist_ok=True)
    if not store.plan_path.exists():
        store.plan_path.write_text(
            '{\n  "settings": {"daily_budget_minutes": 90, "new_cards_per_day": 10},\n'
            '  "subjects": {}\n}\n',
            encoding="utf-8",
        )
    print(f"Dossier de données prêt : {store.root}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="brained", description="Ton cerveau externe.")
    p.add_argument("--data", help="dossier des données (défaut : ./data ou $BRAINED_DATA)")
    p.add_argument("--date", help=argparse.SUPPRESS)  # pour tester : simule un autre jour
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="crée le dossier de données").set_defaults(func=cmd_init)

    a = sub.add_parser("add", help="ajoute une fiche")
    a.add_argument("-s", "--subject")
    a.add_argument("-t", "--title")
    a.add_argument("-q", "--question")
    a.add_argument("-a", "--answer")
    a.add_argument("--tags", help="séparés par des virgules")
    a.set_defaults(func=cmd_add)

    r = sub.add_parser("review", help="révise les fiches du jour")
    r.add_argument("-s", "--subject")
    r.add_argument("-n", "--limit", type=int)
    r.set_defaults(func=cmd_review)

    l = sub.add_parser("list", help="liste les fiches")
    l.add_argument("-s", "--subject")
    l.set_defaults(func=cmd_list)

    sub.add_parser("today", help="plan du jour").set_defaults(func=cmd_today)
    sub.add_parser("week", help="planning de la semaine").set_defaults(func=cmd_week)
    sub.add_parser("stats", help="fiches par matière").set_defaults(func=cmd_stats)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())
