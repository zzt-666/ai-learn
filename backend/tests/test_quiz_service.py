from unittest.mock import MagicMock, patch

import pytest

from app.models.quiz import Question, QuestionType, QuizPayload
from app.services.quiz_service import generate_quiz


def _valid_payload(n: int = 6) -> QuizPayload:
    questions = []
    for i in range(n):
        if i % 3 == 2:
            questions.append(
                Question(
                    id=f"q{i+1}",
                    type=QuestionType.boolean,
                    stem=f"判断 {i+1}",
                    options=["正确", "错误"],
                    answer_indexes=[0],
                    explanation="讲解",
                )
            )
        elif i % 3 == 1:
            questions.append(
                Question(
                    id=f"q{i+1}",
                    type=QuestionType.multiple,
                    stem=f"多选 {i+1}（多选）",
                    options=["A", "B", "C", "D"],
                    answer_indexes=[0, 2],
                    explanation="讲解",
                )
            )
        else:
            questions.append(
                Question(
                    id=f"q{i+1}",
                    type=QuestionType.single,
                    stem=f"单选 {i+1}",
                    options=["A", "B", "C", "D"],
                    answer_indexes=[1],
                    explanation="讲解",
                )
            )
    return QuizPayload(topic_name="自动主题", questions=questions)


def test_generate_quiz_retries_then_succeeds():
    bad = QuizPayload(
        topic_name="坏",
        questions=[
            Question(
                id="q1",
                type=QuestionType.single,
                stem="只有单选",
                options=["A", "B", "C"],
                answer_indexes=[0],
                explanation="缺判断",
            )
        ]
        * 6,
    )
    # force duplicate ids / wrong mix by constructing manually invalid mix:
    # all single — validation should fail first call
    all_single = QuizPayload(
        topic_name="坏",
        questions=[
            Question(
                id=f"q{i}",
                type=QuestionType.single,
                stem=f"题{i}",
                options=["A", "B", "C"],
                answer_indexes=[0],
                explanation="x",
            )
            for i in range(6)
        ],
    )
    good = _valid_payload(6)
    chain = MagicMock()
    chain.invoke.side_effect = [all_single, good]

    with patch("app.services.quiz_service._build_quiz_chain", return_value=chain):
        result = generate_quiz("材料文本", None, 6)

    assert result.topic_name == "自动主题"
    assert len(result.questions) == 6
    assert chain.invoke.call_count == 2


def test_generate_quiz_keeps_user_topic_name():
    good = _valid_payload(6)
    chain = MagicMock()
    chain.invoke.return_value = good

    with patch("app.services.quiz_service._build_quiz_chain", return_value=chain):
        result = generate_quiz("材料", "我的主题", 6)

    assert result.topic_name == "我的主题"


def test_generate_quiz_fails_after_retry():
    all_single = QuizPayload(
        topic_name="坏",
        questions=[
            Question(
                id=f"q{i}",
                type=QuestionType.single,
                stem=f"题{i}",
                options=["A", "B", "C"],
                answer_indexes=[0],
                explanation="x",
            )
            for i in range(6)
        ],
    )
    chain = MagicMock()
    chain.invoke.return_value = all_single

    with patch("app.services.quiz_service._build_quiz_chain", return_value=chain):
        with pytest.raises(RuntimeError, match="出题失败"):
            generate_quiz("材料", None, 6)
