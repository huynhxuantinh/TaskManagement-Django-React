import type { Task, TaskStatus } from '../../types/api'

export function TaskStatusSelect({
  task,
  statuses,
  canChange,
  allowedStatusCodes,
  onChange,
}: {
  task: Task
  statuses: TaskStatus[]
  canChange: boolean
  allowedStatusCodes: string[]
  onChange: (status: string) => void
}) {
  if (!canChange || allowedStatusCodes.length === 0) {
    return <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{task.status.name}</span>
  }
  return (
    <select
      aria-label={`Trạng thái ${task.title}`}
      value={task.status.code}
      onChange={(event) => onChange(event.target.value)}
      className="min-h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]"
    >
      <option value={task.status.code}>{task.status.name}</option>
      {statuses.filter((status) => allowedStatusCodes.includes(status.code)).map((status) => <option key={status.code} value={status.code}>{status.name}</option>)}
    </select>
  )
}
