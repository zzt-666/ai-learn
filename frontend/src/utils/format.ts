export function formatFinishedAt(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  if (sameDay) return `今天 ${hm}`

  const yest = new Date(now)
  yest.setDate(now.getDate() - 1)
  const isYest =
    d.getFullYear() === yest.getFullYear() &&
    d.getMonth() === yest.getMonth() &&
    d.getDate() === yest.getDate()
  if (isYest) return `昨天 ${hm}`

  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${hm}`
}

export function accuracyPercent(accuracy: number): number {
  return Math.round(accuracy * 100)
}
