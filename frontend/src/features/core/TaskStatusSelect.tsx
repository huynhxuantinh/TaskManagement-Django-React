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
  if (task.allowed_transitions.length === 0) {
    const reason = 'Không thể đổi trạng thái: bạn không có quyền hoặc không có bước chuyển hợp lệ.'
    return <span title={reason} aria-label={`${task.status.name}. ${reason}`} className="cursor-help rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{task.status.name}</span>
  }
  return (
    <select
      aria-label={`Trạng thái ${task.title}`}
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
  )
}
