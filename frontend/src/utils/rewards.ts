/** 与 backend `app.services.rewards` 一致：答对 +20 EXP/+5 积分；答错 +5 EXP。 */

export const EXP_PER_CORRECT = 20
export const EXP_PER_WRONG = 5
export const POINTS_PER_CORRECT = 5

export function calcSessionRewards(
  correctCount: number,
  totalCount: number,
): { expGained: number; pointsGained: number } {
  const total = Math.max(0, totalCount)
  const correct = Math.max(0, Math.min(correctCount, total))
  const wrong = Math.max(0, total - correct)
  return {
    expGained: correct * EXP_PER_CORRECT + wrong * EXP_PER_WRONG,
    pointsGained: correct * POINTS_PER_CORRECT,
  }
}
