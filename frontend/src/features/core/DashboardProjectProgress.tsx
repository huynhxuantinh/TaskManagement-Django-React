import { Link } from 'react-router-dom'

import type { Project } from '../../types/api'

export function DashboardProjectProgress({ projects }: { projects: Project[] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="section-kicker">Theo dự án</p>
          <h3 className="section-title">Tiến độ từng dự án</h3>
        </div>
        <Link to="/projects" className="text-sm font-bold text-slate-600 hover:text-slate-950">Xem tất cả →</Link>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {projects.slice(0, 6).map((project) => (
          <Link key={project.id} to={`/projects/${project.id}`} className="rounded-xl border border-slate-200 p-4 transition hover:border-slate-400">
            <div className="flex items-center justify-between gap-3">
              <strong className="truncate text-sm">{project.name}</strong>
              <span className="font-mono text-sm font-black">{project.progress}%</span>
            </div>
            <div role="progressbar" aria-label={`Tiến độ ${project.name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={project.progress} className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${project.progress}%` }} />
            </div>
          </Link>
        ))}
        {projects.length === 0 && <p className="text-sm text-slate-500">Chưa có dự án trong phạm vi của bạn.</p>}
      </div>
    </section>
  )
}
