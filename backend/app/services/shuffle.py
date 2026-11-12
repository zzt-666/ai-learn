from __future__ import annotations

import random
from copy import deepcopy
from typing import TypeVar

T = TypeVar("T")


def shuffle_questions(questions: list[T], *, rng: random.Random | None = None) -> list[T]:
    """打乱题目顺序；不修改原列表元素内部（选项保持原样）。"""
    items = deepcopy(questions)
    (rng or random.Random()).shuffle(items)
    return items
