export function isCorrect(
  answerIndexes: number[],
  selectedIndexes: number[],
): boolean {
  const a = [...new Set(answerIndexes)].sort((x, y) => x - y)
  const b = [...new Set(selectedIndexes)].sort((x, y) => x - y)
  return a.length === b.length && a.every((v, i) => v === b[i])
}

export function summarize(answers: { is_correct: boolean }[]) {
  const correct_count = answers.filter((a) => a.is_correct).length
  const wrong_count = answers.length - correct_count
  const accuracy = answers.length ? correct_count / answers.length : 0
  return { correct_count, wrong_count, accuracy }
}
