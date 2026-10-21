import { useApiResource } from '../../hooks/useApiResource'
import type { Paginated, Task, TaskAuditLog } from '../../types/api'

const actionLabels: Record<TaskAuditLog['action'], string> = {
  CREATED: 'Tạo công việc',
  UPDATED: 'Cập nhật công việc',
  STATUS_CHANGED: 'Đổi trạng thái',
  DELETED: 'Xóa công việc',
}

const fieldLabels: Record<string, string> = {
  start_date: 'Ngày bắt đầu',
  estimated_hours: 'Giờ ước lượng',
  progress: 'Tiến độ',
  parent: 'Công việc cha',
  title: 'Tiêu đề',
  description: 'Mô tả',
  assignee: 'Người nhận',
  priority: 'Ưu tiên',
  deadline: 'Hạn chót',
  status: 'Trạng thái',
  note: 'Ghi chú',
  is_deleted: 'Đã xóa',
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'Chưa có'
  if (typeof value === 'object' && 'full_name' in value) {
    return String((value as { full_name: unknown }).full_name)
  }
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  return String(value)
}

export function TaskHistory({ task }: { task: Task }) {
  const { data, loading, error } = useApiResource<Paginated<TaskAuditLog>>(
    `/api/v1/tasks/${task.id}/history/?page_size=100`,
  )

  if (loading) return <div className="h-32 animate-pulse rounded-xl bg-slate-100" />
  if (error) return <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>
  if (!data?.results.length) return <p className="text-sm text-slate-500">Chưa có thay đổi được ghi nhận.</p>

  return (
    <ol className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
      {data.results.map((log) => (
        <li key={log.id} className="rounded-xl border border-slate-200 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong className="text-sm text-slate-950">{actionLabels[log.action]}</strong>
            <time className="text-xs text-slate-500">{new Date(log.created_at).toLocaleString('vi-VN')}</time>
          </div>
          <p className="mt-1 text-xs text-slate-500">Thực hiện bởi {log.actor?.full_name ?? 'Tài khoản đã xóa'}</p>
          <div className="mt-3 space-y-1 text-sm">
            {Object.entries(log.changes).map(([field, change]) => (
              <p key={field}>
                <span className="font-semibold">{fieldLabels[field] ?? field}:</span>{' '}
                <span className="text-slate-500">{displayValue(change.old)}</span>
                {' → '}
                <span>{displayValue(change.new)}</span>
              </p>
            ))}
          </div>
        </li>
      ))}
    </ol>
  )
}
