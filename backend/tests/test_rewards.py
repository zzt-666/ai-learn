from app.services.rewards import calc_level, calc_level_progress, calc_session_rewards


def test_session_rewards_formula():
    # 6 题对 4：EXP = 40 + 4*10 = 80；积分 = round(4/6 * 40) = 27
    exp_gained, points_gained = calc_session_rewards(correct_count=4, total_count=6)
    assert exp_gained == 80
    assert points_gained == 27


def test_session_rewards_all_correct():
    exp_gained, points_gained = calc_session_rewards(correct_count=5, total_count=5)
    assert exp_gained == 90
    assert points_gained == 40


def test_session_rewards_zero_total():
    exp_gained, points_gained = calc_session_rewards(correct_count=0, total_count=0)
    assert exp_gained == 40
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
