import { useEffect, useState } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { StatePanel } from '../components/ui/StatePanel'
import { apiRequest } from '../lib/api'
import { roleLabel } from '../lib/labels'
import type { DashboardSummary } from '../types/api'

const statusTone: Record<string, string> = {
  TODO: 'bg-slate-100 text-slate-700',
  IN_PROGRESS: 'bg-blue-50 text-blue-700',
  COMPLETED: 'bg-emerald-50 text-emerald-700',
  ON_HOLD: 'bg-amber-50 text-amber-700',
}

export function DashboardPage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    apiRequest<DashboardSummary>('/api/v1/dashboard/summary/', {
      signal: controller.signal,
    })
      .then(setSummary)
      .catch((caught: Error) => {
        if (caught.name !== 'AbortError') setError(caught.message)
      })
    return () => controller.abort()
  }, [])

  if (error) {
    return (
      <StatePanel
        eyebrow="Lỗi đồng bộ"
        title="Không tải được tổng quan"
        description={error}
      />
    )
  }

  const metrics = [
    { label: 'Dự án trong phạm vi', value: summary?.project_count, icon: 'folder' as const },
    { label: 'Tổng công việc', value: summary?.task_count, icon: 'check' as const },
    { label: 'Đã hoàn thành', value: summary?.completed_task_count, icon: 'grid' as const },
    { label: 'Đang quá hạn', value: summary?.overdue_task_count, icon: 'chart' as const },
  ]

  return (
    <div className="space-y-7">
      <section className="dashboard-hero overflow-hidden rounded-3xl bg-[var(--ink)] p-7 text-white md:p-10">
        <div className="relative z-10 max-w-2xl">
          <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-[var(--accent)]">
            Không gian trực tiếp / {user ? roleLabel(user.role) : ''}
          </p>
          <h2 className="mt-4 text-3xl font-black tracking-[-0.035em] md:text-4xl">
            Chào {user?.full_name.split(' ').at(-1)}, hôm nay mình đẩy dự án tiến thêm một nhịp.
          </h2>
          <p className="mt-4 max-w-xl leading-7 text-slate-300">
            Số liệu bên dưới chỉ phản ánh đúng phạm vi công việc mà tài khoản của bạn được phép truy cập.
          </p>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Chỉ số tổng quan">
        {metrics.map((metric, index) => (
          <article
            key={metric.label}
            className="metric-card"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <div className="flex items-start justify-between">
              <p className="text-sm font-semibold text-slate-500">{metric.label}</p>
              <span className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-700">
                <Icon name={metric.icon} className="size-4" />
              </span>
            </div>
            <strong className="mt-7 block font-mono text-3xl font-black text-slate-950">
              {summary ? metric.value : '—'}
            </strong>
          </article>
        ))}
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="section-kicker">Hoạt động gần đây</p>
              <h3 className="section-title">Công việc gần đây</h3>
            </div>
            <span className="font-mono text-xs text-slate-500">TOP 05</span>
          </div>
          <div className="mt-5 divide-y divide-slate-100">
            {!summary && <div className="h-44 animate-pulse rounded-xl bg-slate-100" />}
            {summary?.recent_tasks.length === 0 && (
              <p className="py-12 text-center text-sm text-slate-500">
                Chưa có công việc trong phạm vi của bạn.
              </p>
            )}
            {summary?.recent_tasks.map((task) => (
              <div key={task.id} className="flex items-center gap-4 py-4">
                <span
                  className={`size-2.5 rounded-full ${
                    task.priority === 3
                      ? 'bg-red-500'
                      : task.priority === 2
                        ? 'bg-amber-400'
                        : 'bg-slate-300'
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <strong className="block truncate text-sm text-slate-900">{task.title}</strong>
                  <span className="text-xs text-slate-500">{task.project.name}</span>
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-[10px] font-black ${
                    statusTone[task.status.code] ?? 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {task.status.name}
                </span>
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
          <p className="section-kicker">Phân bổ</p>
          <h3 className="section-title">Trạng thái công việc</h3>
          <div className="mt-6 space-y-5">
            {summary?.task_distribution.map((item) => {
              const percent = summary.task_count
                ? Math.round((item.count / summary.task_count) * 100)
                : 0
              return (
                <div key={item.code}>
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="font-semibold text-slate-700">{item.name}</span>
                    <span className="font-mono text-slate-500">{item.count} / {percent}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-[var(--accent)]"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </div>
              )
            })}
            {!summary && <div className="h-40 animate-pulse rounded-xl bg-slate-100" />}
          </div>
        </section>
      </div>
    </div>
  )
}

