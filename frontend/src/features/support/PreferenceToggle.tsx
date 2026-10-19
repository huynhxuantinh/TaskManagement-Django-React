import type { NotificationPreference } from '../../types/api'

const labels: Record<string, string> = {
  GENERAL: 'Thông báo hệ thống',
  TASK_ASSIGNED: 'Khi được giao việc',
  STATUS_CHANGED: 'Khi trạng thái thay đổi',
  PROJECT_ADDED: 'Khi được thêm vào dự án',
  DEADLINE_APPROACHING: 'Khi deadline đến gần',
}

export function PreferenceToggle({ preference, onChange }: { preference: NotificationPreference; onChange: (value: NotificationPreference) => void }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-4 last:border-0">
      <div><strong className="block text-sm text-slate-900">{labels[preference.type] ?? preference.type}</strong><span className="text-xs text-slate-500">Đánh dấu nhóm này là ưu tiên.</span></div>
      <button type="button" role="switch" aria-checked={preference.is_priority} aria-label={labels[preference.type] ?? preference.type} onClick={() => onChange({ ...preference, is_priority: !preference.is_priority })} className={`relative h-7 w-12 rounded-full transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${preference.is_priority ? 'bg-slate-950' : 'bg-slate-300'}`}><span className={`absolute top-1 size-5 rounded-full bg-white shadow transition ${preference.is_priority ? 'left-6' : 'left-1'}`} /></button>
    </div>
  )
}
