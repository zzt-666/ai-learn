from app.models.quiz import QuestionType, QuizPayload


def validate_quiz_mix(payload: QuizPayload, expected_count: int) -> None:
    questions = payload.questions
    if len(questions) != expected_count:
        raise ValueError(f"题量必须为 {expected_count}，实际为 {len(questions)}")

    types = {q.type for q in questions}
    if QuestionType.single not in types:
        raise ValueError("题目中至少需要包含单选")
    if QuestionType.boolean not in types:
        raise ValueError("题目中至少需要包含判断")

    if not payload.topic_name.strip():
        raise ValueError("主题名不能为空")

    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("题目 id 不能重复")
