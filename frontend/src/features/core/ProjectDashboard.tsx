import { Link } from 'react-router-dom'

import { Button } from '../../components/ui/Button'
import { StatePanel } from '../../components/ui/StatePanel'
import type { ProjectReport, Task } from '../../types/api'
import { ReportProgress } from '../support/ReportProgress'

interface ProjectDashboardProps {
  projectId: number
  report: ProjectReport | null
  tasks: Task[]
  taskCount: number
  showAllTasks: boolean
  canCreateTask?: boolean
  onCreateTask?: () => void
  loading: boolean
  reportError: string
  tasksError: string
}

const statusStyles: Record<string, string> = {
  TODO: 'bg-slate-100 text-slate-700',
  IN_PROGRESS: 'bg-sky-50 text-sky-700',
  COMPLETED: 'bg-emerald-50 text-emerald-700',
  ON_HOLD: 'bg-amber-50 text-amber-700',
}

const priorityLabels: Record<number, string> = {
  1: 'Thấp',
  2: 'Trung bình',
  3: 'Cao',
}

function formatDate(value: string | null) {
  if (!value) return 'Chưa đặt hạn'
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

export function ProjectDashboard({
  projectId,
  report,
  tasks,
  taskCount,
  showAllTasks,
  canCreateTask = false,
  onCreateTask,
  loading,
  reportError,
  tasksError,
}: ProjectDashboardProps) {
  if (loading) {
    return <div aria-label="Đang tải tổng quan dự án" className="h-80 animate-pulse rounded-3xl bg-white" />
  }

  const distribution = new Map(report?.task_distribution.map((item) => [item.code, item.count]) ?? [])
  const remaining = Math.max((report?.total_tasks ?? 0) - (report?.completed_tasks ?? 0), 0)
  const metrics = [
    { label: 'Tổng công việc', value: report?.total_tasks ?? 0, note: 'Trong toàn dự án' },
    { label: 'Đã hoàn thành', value: report?.completed_tasks ?? 0, note: `${report?.progress ?? 0}% tiến độ` },
    { label: 'Đang thực hiện', value: distribution.get('IN_PROGRESS') ?? 0, note: 'Đang được xử lý' },
    { label: 'Còn lại', value: remaining, note: 'Chưa hoàn thành' },
  ]

  return (
    <section className="space-y-5" aria-labelledby="project-overview-title">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="section-kicker">Theo dõi thực thi</p>
          <h2 id="project-overview-title" className="section-title">Tổng quan dự án</h2>
        </div>
        <Link to={`/tasks?project=${projectId}`} className="text-sm font-extrabold text-slate-700 hover:text-slate-950 hover:underline">
          Xem trang công việc →
        </Link>
      </div>

      {reportError && <StatePanel eyebrow="Tiến độ dự án" title="Không tải được số liệu" description={reportError} />}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article key={metric.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[var(--shadow)]">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{metric.label}</p>
            <strong className="mt-3 block font-mono text-3xl font-black text-slate-950">{metric.value}</strong>
            <span className="mt-1 block text-xs text-slate-500">{metric.note}</span>
          </article>
        ))}
      </div>

      {report && (
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="dashboard-hero rounded-3xl p-6 text-white">
            <p className="font-mono text-xs font-black uppercase tracking-[0.18em] text-[var(--accent)]">Tiến độ tổng thể</p>
            <div className="mt-6"><ReportProgress value={report.progress} label="Tiến độ dự án" /></div>
            <p className="mt-5 text-sm leading-6 text-slate-300">
              Đã hoàn thành {report.completed_tasks} trên tổng số {report.total_tasks} công việc.
            </p>
            {report.missing_estimate_count > 0 && (
              <p className="mt-3 rounded-xl bg-amber-300/15 px-3 py-2 text-sm font-semibold text-amber-100">
                {report.missing_estimate_count} công việc chưa có giờ ước lượng; hệ thống đang dùng trọng số trung bình.
              </p>
            )}
          </article>
          <article className="rounded-3xl border border-slate-200 bg-white p-6">
            <p className="section-kicker">Phân bổ công việc</p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {report.task_distribution.map((item) => (
                <div key={item.code} className="rounded-xl bg-slate-50 p-3">
                  <span className="block text-xs text-slate-500">{item.name}</span>
                  <strong className="mt-1 block font-mono text-xl">{item.count}</strong>
                </div>
              ))}
            </div>
          </article>
        </div>
      )}

      <article className="rounded-3xl border border-slate-200 bg-white p-5 md:p-6">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="section-kicker">Danh sách thực hiện / {taskCount}</p>
            <h3 className="section-title">{showAllTasks ? 'Công việc của dự án' : 'Công việc của bạn'}</h3>
          </div>
          <div className="flex items-center gap-3">
            {!showAllTasks && <span className="text-xs text-slate-500">Chỉ hiển thị công việc được giao cho bạn</span>}
            {canCreateTask && <Button onClick={onCreateTask}>+ Giao công việc</Button>}
          </div>
        </div>

        {tasksError && <div className="mt-5"><StatePanel eyebrow="Công việc" title="Không tải được danh sách" description={tasksError} /></div>}
        {!tasksError && tasks.length === 0 && (
          <p className="mt-5 rounded-xl bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">Chưa có công việc nào trong phạm vi của bạn.</p>
        )}
        <div className="mt-5 grid gap-3">
          {tasks.slice(0, 6).map((task) => (
            <div key={task.id} className={`grid gap-3 rounded-xl border p-4 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-center ${task.is_overdue ? 'border-red-200 bg-red-50/40' : 'border-slate-200'}`}>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <strong className="truncate text-sm text-slate-950">{task.title}</strong>
                  {task.is_overdue && <span className="rounded-full bg-red-100 px-2 py-1 text-[10px] font-black uppercase text-red-700">Quá hạn</span>}
                </div>
                <p className="mt-1 text-xs text-slate-500">{task.assignee?.full_name ?? 'Chưa phân công'} · Ưu tiên {priorityLabels[task.priority]}</p>
                <div className="mt-2 flex items-center gap-2"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${task.effective_progress}%` }} /></div><span className="font-mono text-[11px] font-bold text-slate-500">{task.effective_progress}%</span></div>
              </div>
              <span className={`w-fit rounded-full px-2.5 py-1 text-[10px] font-black uppercase ${statusStyles[task.status.code] ?? 'bg-slate-100 text-slate-700'}`}>
                {task.status.name}
              </span>
              <span className="text-xs font-semibold text-slate-500">Hạn {formatDate(task.deadline)}</span>
            </div>
          ))}
        </div>
        {tasks.length > 6 && <p className="mt-4 text-center text-xs text-slate-500">Còn {tasks.length - 6} công việc khác trong trang Công việc.</p>}
      </article>
    </section>
  )
}
