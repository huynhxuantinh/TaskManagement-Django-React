import { StatePanel } from '../../components/ui/StatePanel'
import { useApiResource } from '../../hooks/useApiResource'
import type { Task } from '../../types/api'
import { TaskChecklist } from './TaskChecklist'

function formatDate(value: string | null) {
  if (!value) return 'Chưa đặt'
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

export function TaskDetails({ taskId, onChanged }: { taskId: number; onChanged: () => void }) {
  const { data: task, loading, error, reload } = useApiResource<Task>(`/api/v1/tasks/${taskId}/`)

  if (loading) return <div className="h-72 animate-pulse rounded-2xl bg-slate-100" />
  if (error || !task) return <StatePanel eyebrow="Công việc" title="Không tải được chi tiết" description={error} />

  function refresh() {
    reload()
    onChanged()
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm leading-6 text-slate-600">{task.description || 'Chưa có mô tả.'}</p>
        <dl className="mt-4 grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2">
          <div><dt className="text-xs font-bold uppercase text-slate-500">Ngày bắt đầu</dt><dd className="mt-1 text-sm font-semibold">{formatDate(task.start_date)}</dd></div>
          <div><dt className="text-xs font-bold uppercase text-slate-500">Hạn hoàn thành</dt><dd className="mt-1 text-sm font-semibold">{formatDate(task.deadline)}</dd></div>
          <div><dt className="text-xs font-bold uppercase text-slate-500">Giờ ước lượng</dt><dd className="mt-1 text-sm font-semibold">{task.effective_estimated_hours ? `${task.effective_estimated_hours} giờ` : 'Chưa ước lượng'}</dd></div>
          <div><dt className="text-xs font-bold uppercase text-slate-500">Quan hệ</dt><dd className="mt-1 text-sm font-semibold">{task.parent_id ? `Công việc con của #${task.parent_id}` : 'Công việc gốc'}</dd></div>
        </dl>
      </div>
      <TaskChecklist
        key={task.checklist?.map((item) => `${item.id}:${item.is_completed}:${item.position}`).join('|')}
        task={task}
        onChanged={refresh}
      />
    </div>
  )
}
