from app.services.prompts import QUIZ_HUMAN, QUIZ_SYSTEM, REPORT_SYSTEM


def test_quiz_prompt_allows_model_knowledge():
    assert "训练知识" in QUIZ_SYSTEM or "已有知识" in QUIZ_SYSTEM
    assert "不要引入材料未出现的关键事实或外部百科" not in QUIZ_SYSTEM
    assert "你的唯一依据是用户提供的学习材料" not in QUIZ_SYSTEM
    assert "禁止弱智题" in QUIZ_SYSTEM
    assert "无论用户输入长短" in QUIZ_HUMAN


def test_report_prompt_not_locked_to_material_only():
    assert "不编造材料没有的知识" not in REPORT_SYSTEM
    assert "主题" in REPORT_SYSTEM
