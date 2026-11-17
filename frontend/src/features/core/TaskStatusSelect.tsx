import { useId } from 'react'
import type { Task, TaskStatus, TaskTransition } from '../../types/api'

export function TaskStatusSelect({
  task,
  statuses,
  onChange,
}: {
  task: Task
  statuses: TaskStatus[]
  onChange: (transition: TaskTransition) => void
}) {
  const reasonId = useId()
  const reasons = task.status_restrictions?.map((item) => item.reason) ?? []
  if (task.allowed_transitions.length === 0) {
    const reason = reasons.join(' ') || 'Không có bước chuyển trạng thái khả dụng.'
    return <div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{task.status.name}</span><p className="mt-2 max-w-64 text-xs text-slate-600">{reason}</p></div>
  }
  return (
    <div>
    <select
      aria-label={`Trạng thái ${task.title}`}
      aria-describedby={reasons.length ? reasonId : undefined}
      value={task.status.code}
      onChange={(event) => {
        const transition = task.allowed_transitions.find((item) => item.code === event.target.value)
        if (transition) onChange(transition)
      }}
      className="min-h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]"
    >
      <option value={task.status.code}>{task.status.name}</option>
      {statuses.filter((status) => task.allowed_transitions.some((item) => item.code === status.code)).map((status) => <option key={status.code} value={status.code}>{status.name}</option>)}
    </select>
    {reasons.length > 0 && <p id={reasonId} className="mt-1 max-w-64 text-xs text-slate-600">{reasons.join(' ')}</p>}
    </div>
  )
}
