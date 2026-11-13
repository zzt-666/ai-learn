from app.services.prompts import (
    QUIZ_HUMAN,
    QUIZ_HUMAN_GROUNDED,
    QUIZ_SYSTEM,
    QUIZ_SYSTEM_GROUNDED,
    REPORT_SYSTEM,
    RESEARCH_SYSTEM,
)


def test_quiz_prompt_allows_model_knowledge():
    assert "训练知识" in QUIZ_SYSTEM or "已有知识" in QUIZ_SYSTEM
    assert "不要引入材料未出现的关键事实或外部百科" not in QUIZ_SYSTEM
    assert "你的唯一依据是用户提供的学习材料" not in QUIZ_SYSTEM
    assert "禁止弱智题" in QUIZ_SYSTEM
    assert "无论用户输入长短" in QUIZ_HUMAN


def test_grounded_quiz_prompt_prioritizes_research():
    assert "联网" in QUIZ_SYSTEM_GROUNDED or "参考内容" in QUIZ_SYSTEM_GROUNDED
    assert "以参考内容为准" in QUIZ_SYSTEM_GROUNDED
    assert "禁止弱智题" in QUIZ_SYSTEM_GROUNDED
    assert "{research_context}" in QUIZ_HUMAN_GROUNDED
    assert "优先依据参考内容" in QUIZ_HUMAN_GROUNDED


def test_research_prompt_guides_tool_choice():
    assert "tavily_search" in RESEARCH_SYSTEM
    assert "tavily_search_china" in RESEARCH_SYSTEM
    assert "tavily_extract" in RESEARCH_SYSTEM
    assert "不要出题" in RESEARCH_SYSTEM


def test_report_prompt_not_locked_to_material_only():
    assert "不编造材料没有的知识" not in REPORT_SYSTEM
    assert "主题" in REPORT_SYSTEM
