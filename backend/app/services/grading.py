def is_correct(answer_indexes: list[int], selected_indexes: list[int]) -> bool:
    a = sorted(set(answer_indexes))
    b = sorted(set(selected_indexes))
    return a == b


def summarize_answers(items: list[dict]) -> dict[str, float | int]:
    correct_count = sum(1 for item in items if item.get("is_correct"))
    wrong_count = len(items) - correct_count
    total = len(items)
    accuracy = (correct_count / total) if total else 0.0
    return {
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "accuracy": accuracy,
    }
