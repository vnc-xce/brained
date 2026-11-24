# brained

Un cerveau externe pour apprendre : fiches de révision, révision espacée et plan du jour.
V1 = proof of concept en ligne de commande, sans dépendance (Python 3.10+).

## Démarrer

```bash
cd brained
python3 -m brained today      # que faire aujourd'hui ?
python3 -m brained review     # réviser les fiches du jour
```

Pour avoir la commande `brained` partout :

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
brained today
```

Les données sont lues dans `./data` (ou `--data <dossier>`, ou la variable `BRAINED_DATA`).

## Commandes

| Commande | Rôle |
|---|---|
| `brained today` | plan du jour : matières, durée, fiches à revoir |
| `brained week` | planning des 7 prochains jours |
| `brained review [-s matière] [-n 10]` | séance de révision (notes 1 raté, 2 difficile, 3 ok, 4 facile) |
| `brained add -s japonais -t "Titre" -q "Question" -a "Réponse"` | nouvelle fiche (sans options : mode interactif) |
| `brained list [-s matière]` | liste des fiches et prochaine révision |
| `brained stats` | nombre de fiches et fiches à revoir par matière |

## Les données

```
data/
  cards/<matière>/<id>.md   une fiche = un fichier Markdown
  reviews.json              état de révision de chaque fiche (créé à la 1re révision)
  plan.json                 objectifs par matière et budget de temps
```

Une fiche question/réponse :

```markdown
---
id: particule-wa
subject: japonais
title: La particule は
tags: [grammaire]
---

## Question
À quoi sert la particule は ?

## Réponse
Elle marque le thème de la phrase.
```

Sans sections `## Question` / `## Réponse`, c'est une fiche de synthèse : tout le texte
s'affiche et tu notes si tu t'en souvenais. Tu peux écrire les fiches à la main dans
ton éditeur (ou Obsidian), elles sont relues à chaque commande.

`plan.json` : pour chaque matière, la durée d'une séance, les jours (`lun`…`dim` ou `tous`)
et une priorité (1 haute à 3 basse). `budget_by_day` permet d'avoir plus de temps le week-end.
Une matière qui n'est pas prévue ce jour-là mais a des fiches en retard reçoit une révision courte.

## Architecture

```
brained/
  models.py    Card, ReviewState, Goal, Settings  (données pures)
  storage.py   lecture/écriture Markdown + JSON   (seul module qui touche au disque)
  srs.py       algorithme de révision espacée (SM-2 simplifié)
  planner.py   fiches dues + plan du jour (règles)
  cli.py       interface en ligne de commande (aucune logique métier)
```

Prévu pour la suite sans tout réécrire :
- **App mobile** : les fiches sont des fichiers Markdown + JSON, faciles à synchroniser
  ou à exposer via une petite API qui réutilise `storage` et `srs`.
- **Agent planificateur (IA)** : remplacer ou enrichir `planner.plan_day`, qui garde la même
  entrée (objectifs, fiches dues) et la même sortie (liste de séances).
- **Rappels** : une tâche planifiée (cron, notification) qui appelle `plan_day` chaque matin.

## Tests

```bash
pip install pytest && python3 -m pytest
```
