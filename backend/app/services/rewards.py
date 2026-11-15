"""EXP / 积分 / 等级纯函数。

通关结算与局内反馈一致：答对 +20 EXP / +5 积分；答错 +5 EXP（参与奖）、积分不加。
"""

from __future__ import annotations

EXP_PER_LEVEL = 300
EXP_PER_CORRECT = 20
EXP_PER_WRONG = 5
POINTS_PER_CORRECT = 5


def calc_session_rewards(*, correct_count: int, total_count: int) -> tuple[int, int]:
    """返回 (exp_gained, points_gained)。"""
    total = max(0, int(total_count))
    correct = max(0, min(int(correct_count), total))
    wrong = max(0, total - correct)
    exp_gained = correct * EXP_PER_CORRECT + wrong * EXP_PER_WRONG
    points_gained = correct * POINTS_PER_CORRECT
    return exp_gained, points_gained


def calc_level(exp: int) -> int:
    return exp // EXP_PER_LEVEL + 1


def calc_level_progress(exp: int) -> tuple[float, int]:
    """返回 (level_progress 0~1, exp_to_next_level)。"""
    within = exp % EXP_PER_LEVEL
    progress = within / EXP_PER_LEVEL
    to_next = EXP_PER_LEVEL - within
    return progress, to_next
