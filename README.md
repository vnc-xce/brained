# brained

An external brain for learning: flashcards, spaced repetition and a daily plan.
V1 = command-line proof of concept, no dependencies (Python 3.10+).

## Getting started

```bash
cd brained
python3 -m brained today      # what should I study today?
python3 -m brained review     # review today's cards
```

To get the `brained` command everywhere:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
brained today
```

Data is read from `./data` (or `--data <folder>`, or the `BRAINED_DATA` environment variable).

## Commands

| Command | What it does |
|---|---|
| `brained today` | today's plan: subjects, time, cards to review |
| `brained week` | schedule for the next 7 days |
| `brained review [-s subject] [-n 10]` | review session (grades: 1 again, 2 hard, 3 good, 4 easy) |
| `brained add -s japanese -t "Title" -q "Question" -a "Answer"` | new card (without options: interactive mode) |
| `brained list [-s subject]` | list cards and their next review date |
| `brained stats` | number of cards and cards due per subject |

## Data

```
data/
  cards/<subject>/<id>.md   one card = one Markdown file
  reviews.json              review state of each card (created on first review)
  plan.json                 goals per subject and time budget
```

A question/answer card:

```markdown
---
id: particle-wa
subject: japanese
title: The particle は
tags: [grammar]
---

## Question
What is the particle は used for?

## Answer
It marks the topic of the sentence.
```

Without `## Question` / `## Answer` sections, it is a summary card: the whole text is
shown and you grade whether you remembered it. You can write cards by hand in your
editor (or Obsidian); they are re-read on every command.

`plan.json`: for each subject, the length of a session, the days (`mon`…`sun` or `all`)
and a priority (1 high to 3 low). `budget_by_day` gives you more time on weekends.
A subject that is not scheduled on a given day but has overdue cards gets a short session.

## Architecture

```
brained/
  models.py    Card, ReviewState, Goal, Settings  (plain data)
  storage.py   Markdown + JSON read/write          (the only module that touches disk)
  srs.py       spaced repetition algorithm (simplified SM-2)
  planner.py   due cards + daily plan (rules)
  cli.py       command-line interface (no business logic)
```

Designed so the next steps don't require a rewrite:
- **Mobile app**: cards are Markdown + JSON files, easy to sync or to expose through
  a small API that reuses `storage` and `srs`.
- **Planning agent (AI)**: replace or extend `planner.plan_day`, which keeps the same
  input (goals, due cards) and the same output (a list of sessions).
- **Reminders**: a scheduled job (cron, notification) that calls `plan_day` every morning.

## Tests

```bash
pip install pytest && python3 -m pytest
```
