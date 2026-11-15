from app.services.question_split import (
    ExtractedQuestion,
    looks_like_image_question,
    split_questions_rule,
    split_questions_with_llm_fallback,
    suggest_mode_from_text,
)

BANK_MD = """
1. TCP 属于哪一层？
A. 应用层
B. 传输层
C. 网络层
D. 链路层
答案：B
解析：TCP 在传输层。

2. 下列哪些是传输层协议？
A. TCP
B. UDP
C. IP
D. HTTP
答案：AB
解析：TCP 与 UDP。

3. 路由器工作在网络层。
答案：对
解析：网络层设备。

4. 见图 3-1，阴影部分表示什么？
A. 时延
B. 带宽
答案：A
"""


def test_suggest_mode_prefers_drill_for_bank_like_text():
    mode, conf = suggest_mode_from_text(BANK_MD)
    assert mode == "drill"
    assert conf >= 0.5


def test_suggest_mode_prefers_master_for_notes():
    mode, _ = suggest_mode_from_text("本章介绍计算机网络的基本概念与发展历史。")
    assert mode == "master"


def test_rule_split_extracts_single_multi_judge_and_filters_image():
    result = split_questions_rule(BANK_MD)
    assert len(result.questions) >= 3
    types = {q.qtype for q in result.questions}
    assert "single" in types
    assert "multi" in types or "judge" in types
    assert all(not looks_like_image_question(q.stem) for q in result.questions)
    assert all("图" not in q.stem for q in result.questions)


TEXTBOOK_MD = """
2-1 下列选项中，不属于物理层接口规范定义范畴的是（ ）。
A. 引脚功能
B. 接口形状
C. 信号电平
D. 传输媒体
【答案】D
【解析】
传输媒体不属于接口四特性。

2-2 双绞线绞合的目的是（ ）。
A. 减少干扰
B. 提高传输速度
C. 增大传输距离
D. 增大抗拉强度
【答案】A
"""


def test_textbook_chapter_number_and_bracket_answer():
    mode, _ = suggest_mode_from_text(TEXTBOOK_MD)
    assert mode == "drill"
    result = split_questions_rule(TEXTBOOK_MD)
    assert len(result.questions) >= 2
    assert result.questions[0].answer_indices == [3]
    assert "物理层" in result.questions[0].stem


def test_llm_fallback_used_when_rules_empty():
    def fake_llm(_text: str):
        return [
            ExtractedQuestion(
                qtype="single",
                stem="备用题？",
                options=["A", "B"],
                answer_indices=[0],
                confidence=0.7,
            )
        ]

    result = split_questions_with_llm_fallback("没有题号的散文。", llm_splitter=fake_llm)
    assert len(result.questions) == 1
    assert result.questions[0].stem == "备用题？"
