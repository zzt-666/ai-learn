import pytest

from app.services.grading import is_correct, summarize_answers


def test_single_exact_match():
    assert is_correct([1], [1]) is True
    assert is_correct([1], [0]) is False


def test_multiple_set_equality_order_independent():
    assert is_correct([0, 2], [2, 0]) is True
    assert is_correct([0, 2], [0]) is False
    assert is_correct([0, 2], [0, 1, 2]) is False


def test_deduplicates_selected_indexes():
    assert is_correct([0, 0, 2], [0, 2]) is True


def test_summarize_answers():
    items = [
        {"is_correct": True},
        {"is_correct": True},
        {"is_correct": False},
    ]
    summary = summarize_answers(items)
    assert summary["correct_count"] == 2
    assert summary["wrong_count"] == 1
    assert summary["accuracy"] == pytest.approx(2 / 3)
