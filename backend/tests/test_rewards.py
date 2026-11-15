from app.services.rewards import calc_level, calc_level_progress, calc_session_rewards


def test_session_rewards_per_question():
    # 6 题对 4：EXP = 4*20 + 2*5 = 90；积分 = 4*5 = 20
    exp_gained, points_gained = calc_session_rewards(correct_count=4, total_count=6)
    assert exp_gained == 90
    assert points_gained == 20


def test_session_rewards_all_correct():
    exp_gained, points_gained = calc_session_rewards(correct_count=5, total_count=5)
    assert exp_gained == 100
    assert points_gained == 25


def test_session_rewards_all_wrong():
    exp_gained, points_gained = calc_session_rewards(correct_count=0, total_count=3)
    assert exp_gained == 15
    assert points_gained == 0


def test_session_rewards_zero_total():
    exp_gained, points_gained = calc_session_rewards(correct_count=0, total_count=0)
    assert exp_gained == 0
    assert points_gained == 0


def test_level_from_exp():
    assert calc_level(0) == 1
    assert calc_level(299) == 1
    assert calc_level(300) == 2
    assert calc_level(1280) == 5


def test_level_progress():
    progress, to_next = calc_level_progress(1280)
    assert progress == 1280 % 300 / 300
    assert to_next == 300 - (1280 % 300)
