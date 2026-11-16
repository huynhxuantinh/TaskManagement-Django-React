export function formatDate(value: string | null | undefined): string {
  if (!value) return 'Chưa có ngày'
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? 'Ngày không hợp lệ' : new Intl.DateTimeFormat('vi-VN').format(date)
}
