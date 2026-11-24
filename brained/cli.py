"""Command-line interface. Contains no business logic."""

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

DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _store(args) -> Store:
    root = args.data or os.environ.get("BRAINED_DATA") or "data"
    return Store(Path(root).expanduser())


def _today(args) -> date:
    return date.fromisoformat(args.date) if args.date else date.today()


def _read_multiline(prompt: str) -> str:
    print(f"{prompt} (end with an empty line):")
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


# --- Commands -----------------------------------------------------------------

def cmd_add(args) -> int:
    store = _store(args)
    subject = args.subject or input("Subject: ").strip()
    title = args.title or input("Title: ").strip()
    if args.question is not None:
        question, answer = args.question, args.answer or ""
    else:
        question = _read_multiline("Question (or summary text)")
        answer = _read_multiline("Answer (leave empty for a summary card)")
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
    print(f"Card created: {path}")
    return 0


def cmd_list(args) -> int:
    store = _store(args)
    reviews = store.load_reviews()
    cards = store.load_cards()
    if args.subject:
        cards = [c for c in cards if c.subject == args.subject]
    if not cards:
        print("No cards.")
        return 0
    for card in cards:
        state = reviews.get(card.id)
        due = state.due.isoformat() if state and state.due else "new"
        print(f"[{card.subject}] {card.title}  ({card.id}, next review: {due})")
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
        print("Nothing to review today. 🎉")
        return 0

    print(f"{len(cards)} card(s) to review. Press Enter to show the answer, q to quit.")
    done = Counter()
    for i, card in enumerate(cards, 1):
        _show_card(card, i, len(cards))
        try:
            if card.is_qa:
                if input("\n[Enter = answer] ").strip().lower() == "q":
                    break
                print("\n" + card.answer)
            prompt = "\nGrade: 1 again · 2 hard · 3 good · 4 easy · q quit > "
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
        store.save_reviews(reviews)  # save after every card
        done[grade] += 1
        print(f"→ next review in {reviews[card.id].interval} day(s)")

    total = sum(done.values())
    if total:
        summary = ", ".join(f"{done[g]} {srs.GRADE_LABELS[g]}" for g in sorted(done))
        print(f"\nSession done: {total} card(s) reviewed ({summary}).")
    return 0


def cmd_today(args) -> int:
    store = _store(args)
    today = _today(args)
    goals, settings = store.load_plan()
    plan = planner.plan_day(goals, store.load_cards(), store.load_reviews(), today, settings)
    print(f"{DAY_LABELS[today.weekday()]} {today.isoformat()}")
    if not plan:
        print("Nothing planned today. Add goals in plan.json.")
        return 0
    total = 0
    for s in plan:
        if s.postponed:
            continue
        total += s.minutes
        print(f"  • {s.subject:<15} {s.minutes:>3} min   ({s.reason})")
    postponed = [s for s in plan if s.postponed]
    print(f"Total: {total} min out of a {settings.budget_for(today)} min budget.")
    if postponed:
        print("Postponed (not enough time): " + ", ".join(s.subject for s in postponed))
    return 0


def cmd_week(args) -> int:
    store = _store(args)
    goals, _ = store.load_plan()
    for d, todays in planner.week_schedule(goals, _today(args)):
        items = ", ".join(f"{g.subject} {g.minutes} min" for g in todays) or "rest"
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
        print("No cards.")
        return 0
    print(f"{'Subject':<15} {'Cards':>6} {'Due':>6}")
    for subject in sorted(total):
        print(f"{subject:<15} {total[subject]:>6} {due.get(subject, 0):>6}")
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
    print(f"Data folder ready: {store.root}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="brained", description="Your external brain.")
    p.add_argument("--data", help="data folder (default: ./data or $BRAINED_DATA)")
    p.add_argument("--date", help=argparse.SUPPRESS)  # for testing: pretend it's another day
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the data folder").set_defaults(func=cmd_init)

    a = sub.add_parser("add", help="add a card")
    a.add_argument("-s", "--subject")
    a.add_argument("-t", "--title")
    a.add_argument("-q", "--question")
    a.add_argument("-a", "--answer")
    a.add_argument("--tags", help="comma-separated")
    a.set_defaults(func=cmd_add)

    r = sub.add_parser("review", help="review today's cards")
    r.add_argument("-s", "--subject")
    r.add_argument("-n", "--limit", type=int)
    r.set_defaults(func=cmd_review)

    l = sub.add_parser("list", help="list cards")
    l.add_argument("-s", "--subject")
    l.set_defaults(func=cmd_list)

    sub.add_parser("today", help="today's plan").set_defaults(func=cmd_today)
    sub.add_parser("week", help="schedule for the week").set_defaults(func=cmd_week)
    sub.add_parser("stats", help="cards per subject").set_defaults(func=cmd_stats)
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
