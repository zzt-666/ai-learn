import pytest

from app.models.quiz import Question, QuestionType, QuizPayload
from app.services.quiz_validate import validate_quiz_mix


def _q(qid: str, qtype: QuestionType, answers: list[int], options: list[str] | None = None) -> Question:
    if options is None:
        if qtype == QuestionType.boolean:
            options = ["正确", "错误"]
        else:
            options = ["A", "B", "C", "D"]
    return Question(
        id=qid,
        type=qtype,
        stem=f"题干 {qid}",
        options=options,
        answer_indexes=answers,
        explanation="讲解",
    )


def test_validate_mix_ok_for_six():
    payload = QuizPayload(
        topic_name="测试主题",
        questions=[
            _q("q1", QuestionType.single, [0]),
            _q("q2", QuestionType.single, [1]),
            _q("q3", QuestionType.single, [2]),
            _q("q4", QuestionType.multiple, [0, 2]),
            _q("q5", QuestionType.multiple, [1, 3]),
            _q("q6", QuestionType.boolean, [0]),
        ],
    )
    validate_quiz_mix(payload, expected_count=6)


def test_validate_mix_rejects_wrong_count():
    payload = QuizPayload(
        topic_name="测试主题",
        questions=[_q("q1", QuestionType.single, [0])],
    )
    with pytest.raises(ValueError, match="题量"):
        validate_quiz_mix(payload, expected_count=6)


def test_validate_mix_requires_single_and_boolean_when_small():
    payload = QuizPayload(
        topic_name="测试主题",
        questions=[
            _q("q1", QuestionType.single, [0]),
            _q("q2", QuestionType.single, [1]),
            _q("q3", QuestionType.multiple, [0, 1]),
        ],
    )
    with pytest.raises(ValueError, match="判断"):
        validate_quiz_mix(payload, expected_count=3)
