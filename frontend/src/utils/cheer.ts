/** 按正确率挑选通关鼓励词（前端本地，不额外调模型） */
export function pickCheerTitle(accuracy: number): string {
  const pct = accuracy <= 1 ? accuracy * 100 : accuracy
  if (pct >= 95) return '绝了！这局封神'
  if (pct >= 80) return '通关！这局够味'
  if (pct >= 60) return '稳住！越闯越顺'
  if (pct >= 40) return '先过关，下次更猛'
  return '跌倒也算进步，再来一局'
}
