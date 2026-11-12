from app.models.quiz import Question, QuestionType
from app.services.shuffle import shuffle_questions
import random


def test_shuffle_keeps_options_and_answers():
    questions = [
        Question(
            id="q1",
            type=QuestionType.single,
            stem="A",
            options=["1", "2", "3"],
            answer_indexes=[1],
            explanation="e1",
        ),
        Question(
            id="q2",
            type=QuestionType.boolean,
            stem="B",
            options=["正确", "错误"],
            answer_indexes=[0],
            explanation="e2",
        ),
        Question(
            id="q3",
            type=QuestionType.multiple,
            stem="C",
            options=["x", "y", "z"],
            answer_indexes=[0, 2],
            explanation="e3",
        ),
    ]
    rng = random.Random(42)
    shuffled = shuffle_questions(questions, rng=rng)
    assert {q.id for q in shuffled} == {"q1", "q2", "q3"}
    by_id = {q.id: q for q in shuffled}
    assert by_id["q1"].options == ["1", "2", "3"]
    assert by_id["q1"].answer_indexes == [1]
    assert by_id["q3"].options == ["x", "y", "z"]
    assert by_id["q3"].answer_indexes == [0, 2]
    # 原列表未原地修改
    assert [q.id for q in questions] == ["q1", "q2", "q3"]
