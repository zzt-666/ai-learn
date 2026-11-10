import pytest
from pydantic import ValidationError

from app.models.quiz import Question, QuestionType, QuizGenerateRequest, QuizPayload


def test_single_question_ok():
    q = Question(
        id="q1",
        type=QuestionType.single,
        stem="场所是？",
        options=["线粒体", "叶绿体", "液泡", "核糖体"],
        answer_indexes=[1],
        explanation="材料写了叶绿体。",
    )
    assert q.type == QuestionType.single


def test_multiple_needs_at_least_two_answers():
    with pytest.raises(ValidationError):
        Question(
            id="q2",
            type=QuestionType.multiple,
            stem="原料？（多选）",
            options=["二氧化碳", "水", "氧气", "葡萄糖"],
            answer_indexes=[0],
            explanation="至少两个答案。",
        )


def test_boolean_must_be_correct_wrong():
    with pytest.raises(ValidationError):
        Question(
            id="q3",
            type=QuestionType.boolean,
            stem="判断题",
            options=["对", "错"],
            answer_indexes=[0],
            explanation="固定选项。",
        )

    q = Question(
        id="q3",
        type=QuestionType.boolean,
        stem="判断题",
        options=["正确", "错误"],
        answer_indexes=[0],
        explanation="固定选项。",
    )
    assert q.options == ["正确", "错误"]


def test_answer_index_out_of_range():
    with pytest.raises(ValidationError):
        Question(
            id="q1",
            type=QuestionType.single,
            stem="题",
            options=["A", "B", "C"],
            answer_indexes=[3],
            explanation="越界。",
        )


def test_quiz_generate_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        QuizGenerateRequest(source_text="   ")


def test_quiz_generate_request_allows_short_text():
    req = QuizGenerateRequest(source_text="光合作用", question_count=6)
    assert req.source_text == "光合作用"
    assert req.question_count == 6


def test_quiz_payload_question_count():
    payload = QuizPayload(
        topic_name="光合作用要点闯关",
        questions=[
            Question(
                id="q1",
                type=QuestionType.single,
                stem="场所？",
                options=["线粒体", "叶绿体", "液泡"],
                answer_indexes=[1],
                explanation="叶绿体。",
            ),
            Question(
                id="q2",
                type=QuestionType.boolean,
                stem="夜晚完全停止代谢。",
                options=["正确", "错误"],
                answer_indexes=[1],
                explanation="仍有呼吸。",
            ),
        ],
    )
    assert len(payload.questions) == 2
