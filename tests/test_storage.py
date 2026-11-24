from datetime import date

from brained.models import Card, ReviewState
from brained.storage import Store, parse_card, render_card


def test_card_roundtrip(tmp_path):
    store = Store(tmp_path)
    card = Card("c1", "japonais", "Test", "Q ?", "R.", ["a", "b"], date(2026, 1, 1))
    store.save_card(card)
    assert store.load_cards() == [card]


def test_synthesis_card():
    card = parse_card("---\nid: x\nsubject: s\ntitle: T\n---\n\nTexte libre.\n", "f", "g")
    assert not card.is_qa and card.question == "Texte libre."
    assert "## Question" not in render_card(card)


def test_card_without_frontmatter():
    card = parse_card("## Question\nQ\n\n## Réponse\nR\n", "mon-id", "maths")
    assert (card.id, card.subject, card.question, card.answer) == ("mon-id", "maths", "Q", "R")


def test_reviews_roundtrip(tmp_path):
    store = Store(tmp_path)
    reviews = {"c1": ReviewState(due=date(2026, 1, 2), last_review=date(2026, 1, 1), interval=1)}
    store.save_reviews(reviews)
    assert store.load_reviews() == reviews


def test_new_card_id_unique(tmp_path):
    store = Store(tmp_path)
    store.save_card(Card(store.new_card_id("Hiragana あ"), "jp", "Hiragana あ", "q"))
    assert store.new_card_id("Hiragana あ") == "hiragana-2"
