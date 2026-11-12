"""EXP / 积分 / 等级纯函数（与需求 §5.5 锁定公式一致）。"""

from __future__ import annotations


EXP_PER_LEVEL = 300


def calc_session_rewards(*, correct_count: int, total_count: int) -> tuple[int, int]:
    """返回 (exp_gained, points_gained)。"""
    accuracy = (correct_count / total_count) if total_count > 0 else 0.0
    exp_gained = 40 + correct_count * 10
    points_gained = round(accuracy * 40)
    return exp_gained, points_gained


def calc_level(exp: int) -> int:
    return exp // EXP_PER_LEVEL + 1


def calc_level_progress(exp: int) -> tuple[float, int]:
    """返回 (level_progress 0~1, exp_to_next_level)。"""
    within = exp % EXP_PER_LEVEL
    progress = within / EXP_PER_LEVEL
    to_next = EXP_PER_LEVEL - within
    return progress, to_next
