import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { Modal } from '../components/ui/Modal'
import { StatePanel } from '../components/ui/StatePanel'
import { useAllPages } from '../hooks/useAllPages'
import type { Project, User } from '../types/api'
import { ProjectForm } from '../features/core/ProjectForm'
import { canCreateProjects } from '../features/core/permissions'
import { formatDate } from '../lib/date'

export function ProjectsPage() {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDirection, setSortDirection] = useState('desc')
  const [creating, setCreating] = useState(false)
  const ordering = `${sortDirection === 'desc' ? '-' : ''}${sortField}`
  const path = `/api/v1/projects/?page_size=100&search=${encodeURIComponent(search)}&ordering=${ordering}`
  const { data, loading, error, reload } = useAllPages<Project>(path)
  const { data: managers, loading: ownersLoading, error: ownersError, reload: reloadOwners } = useAllPages<User>(user?.role === 'ADMIN' ? '/api/v1/users/?is_active=true&page_size=100' : null)
  const ownersReady = user?.role !== 'ADMIN' || Boolean(managers && !ownersLoading && !ownersError)

  function submitSearch(event: FormEvent) {
    event.preventDefault()
    setSearch(query.trim())
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div><p className="section-kicker">Danh mục dự án / {data?.count ?? 0}</p><h2 className="mt-1 text-3xl font-black tracking-tight text-slate-950">Dự án trong phạm vi</h2><p className="mt-2 text-sm text-slate-600">Theo dõi tiến độ, mốc thời gian và đội phụ trách.</p></div>
        {user && canCreateProjects(user) && <Button disabled={!ownersReady} onClick={() => setCreating(true)}>+ Tạo dự án</Button>}
      </header>

      {user?.role === 'ADMIN' && ownersLoading && <p role="status" className="text-sm text-slate-600">Đang tải danh sách chủ dự án…</p>}
      {user?.role === 'ADMIN' && ownersError && <div role="alert" className="flex items-center gap-3 text-sm text-red-700"><span>Không tải được danh sách chủ dự án: {ownersError}</span><Button variant="secondary" onClick={reloadOwners}>Thử lại</Button></div>}

      <form onSubmit={submitSearch} className="flex flex-wrap gap-3 rounded-2xl border border-slate-200 bg-white p-3">
        <Field aria-label="Tìm dự án" label="Tìm dự án" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tên hoặc mô tả…" className="md:w-96" />
        <Button type="submit" variant="secondary" className="self-end">Tìm</Button>
        <label className="block text-sm font-bold"><span className="mb-2 block">Sắp xếp theo</span><select className="min-h-12 rounded-xl border border-slate-300 bg-white px-4" value={sortField} onChange={(event) => setSortField(event.target.value)}><option value="name">Tên dự án</option><option value="start_date">Ngày bắt đầu</option><option value="end_date">Ngày kết thúc</option><option value="created_at">Ngày tạo</option></select></label>
        <label className="block text-sm font-bold"><span className="mb-2 block">Thứ tự</span><select className="min-h-12 rounded-xl border border-slate-300 bg-white px-4" value={sortDirection} onChange={(event) => setSortDirection(event.target.value)}><option value="asc">Tăng dần</option><option value="desc">Giảm dần</option></select></label>
      </form>

      {error && <StatePanel eyebrow="Lỗi đồng bộ" title="Không tải được dự án" description={error} />}
      {loading && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-60 animate-pulse rounded-2xl bg-white" />)}</div>}
      {!loading && data?.results.length === 0 && <StatePanel eyebrow="Danh mục dự án" title="Chưa có dự án phù hợp" description="Thử từ khóa khác hoặc tạo dự án mới nếu bạn có quyền." />}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Danh sách dự án">
        {data?.results.map((project) => (
          <Link key={project.id} to={`/projects/${project.id}`} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-[var(--shadow)] transition hover:-translate-y-1 hover:border-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]">
            <div className="flex items-start justify-between gap-4"><div><span className="font-mono text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">PRJ-{String(project.id).padStart(3, '0')}</span><h3 className="mt-2 text-xl font-extrabold tracking-tight group-hover:underline">{project.name}</h3></div><span className="rounded-full bg-[var(--accent-soft)] px-2.5 py-1 font-mono text-xs font-black">{project.progress}%</span></div>
            <p className="mt-3 line-clamp-2 min-h-10 text-sm leading-5 text-slate-600">{project.description || 'Chưa có mô tả dự án.'}</p>
            <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${project.progress}%` }} /></div>
            <p className="mt-2 text-xs text-slate-600">Còn {project.unfinished_task_count} công việc chưa hoàn thành.</p>
            <div className="mt-4 flex items-end justify-between gap-3 text-xs text-slate-500"><span>{formatDate(project.start_date)} → {formatDate(project.end_date)}</span><strong className="text-slate-700">{project.member_count} thành viên</strong></div>
          </Link>
        ))}
      </section>

      <Modal open={creating} title="Tạo dự án mới" onClose={() => setCreating(false)}>
        {ownersReady ? <ProjectForm ownerOptions={managers?.results.filter((item) => item.is_active && item.role !== 'EMPLOYEE') ?? []} onCancel={() => setCreating(false)} onSaved={() => { setCreating(false); reload() }} /> : <p role="status">Vui lòng tải lại danh sách chủ dự án trước khi tạo.</p>}
      </Modal>
    </div>
  )
}
