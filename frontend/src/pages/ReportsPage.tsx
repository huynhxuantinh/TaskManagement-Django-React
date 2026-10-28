import { useState, type FormEvent } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { ReportProgress } from '../features/support/ReportProgress'
import { useAllPages } from '../hooks/useAllPages'
import { useApiResource } from '../hooks/useApiResource'
import { apiRequest } from '../lib/api'
import type { Contributor, Project, ProjectMember, ProjectReport, ReportMessage, WorkloadRow } from '../types/api'

function ReportsMessages({ projects }: { projects: Project[] }) {
  const { user } = useAuth()
  const notify = useToast()
  const { data, setData, loading, error, reload } = useAllPages<ReportMessage>('/api/v1/reports/messages/?page_size=100')
  const [projectId, setProjectId] = useState(String(projects[0]?.id ?? ''))
  const [receiverId, setReceiverId] = useState('')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [sending, setSending] = useState(false)
  const { data: members } = useAllPages<ProjectMember>(projectId ? `/api/v1/projects/${projectId}/members/?page_size=100` : null)

  async function send(event: FormEvent) {
    event.preventDefault()
    setSending(true)
    try {
      await apiRequest<ReportMessage>('/api/v1/reports/messages/', { method: 'POST', body: JSON.stringify({ project_id: Number(projectId), receiver_id: Number(receiverId), title, content }) })
      setTitle(''); setContent(''); setReceiverId(''); reload(); notify('Đã gửi báo cáo.')
    } catch (caught) { notify((caught as Error).message, 'error') } finally { setSending(false) }
  }

  async function markRead(message: ReportMessage) {
    try {
      const updated = await apiRequest<ReportMessage>(`/api/v1/reports/messages/${message.id}/read/`, { method: 'PATCH' })
      setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current)
    } catch (caught) { notify((caught as Error).message, 'error') }
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
      <form onSubmit={send} className="rounded-2xl border border-slate-200 bg-white p-5"><p className="section-kicker">Ghi chú dự án</p><h3 className="section-title">Gửi báo cáo</h3><div className="mt-5 space-y-4"><label className="block"><span className="mb-2 block text-sm font-bold">Dự án</span><select value={projectId} onChange={(event) => { setProjectId(event.target.value); setReceiverId('') }} required className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4">{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label><label className="block"><span className="mb-2 block text-sm font-bold">Người nhận</span><select value={receiverId} onChange={(event) => setReceiverId(event.target.value)} required className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4"><option value="">Chọn thành viên</option>{members?.results.filter((member) => member.user.id !== user?.id).map((member) => <option key={member.id} value={member.user.id}>{member.user.full_name}</option>)}</select></label><Field label="Tiêu đề" value={title} onChange={(event) => setTitle(event.target.value)} required /><label className="block"><span className="mb-2 block text-sm font-bold">Nội dung</span><textarea value={content} onChange={(event) => setContent(event.target.value)} required rows={5} className="w-full rounded-xl border border-slate-300 px-4 py-3" /></label><Button disabled={sending || !receiverId}>{sending ? 'Đang gửi…' : 'Gửi báo cáo'}</Button></div></form>
      <div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="section-kicker">Luồng trao đổi / {data?.count ?? 0}</p><h3 className="section-title">Trao đổi báo cáo</h3>{error && <div className="mt-4"><StatePanel eyebrow="Lỗi" title="Không tải được báo cáo" description={error} /></div>}{loading && <div className="mt-5 h-40 animate-pulse rounded-xl bg-slate-100" />}<div className="mt-5 max-h-[36rem] space-y-3 overflow-y-auto">{data?.results.map((message) => { const incoming = message.receiver.id === user?.id; return <article key={message.id} className={`rounded-xl border p-4 ${incoming && !message.is_read ? 'border-lime-300 bg-[var(--accent-soft)]/30' : 'border-slate-200'}`}><div className="flex items-start justify-between gap-3"><div><strong className="text-sm">{message.title}</strong><p className="mt-1 text-xs text-slate-500">{message.project.name} · {incoming ? `Từ ${message.sender.full_name}` : `Đến ${message.receiver.full_name}`}</p></div>{incoming && !message.is_read && <Button variant="ghost" className="!min-h-8 !px-2" onClick={() => void markRead(message)}>Đã đọc</Button>}</div><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{message.content}</p></article> })}{!loading && data?.results.length === 0 && <p className="py-10 text-center text-sm text-slate-500">Chưa có trao đổi báo cáo.</p>}</div></div>
    </section>
  )
}

export function ReportsPage() {
  const { user } = useAuth()
  const { data: projectsData, loading, error } = useAllPages<Project>('/api/v1/projects/?page_size=100&ordering=name')
  const [selectedId, setSelectedId] = useState('')
  const effectiveId = selectedId || String(projectsData?.results[0]?.id ?? '')
  const { data: report } = useApiResource<ProjectReport>(effectiveId ? `/api/v1/reports/projects/${effectiveId}/` : null)
  const { data: contributors } = useApiResource<Contributor[]>(effectiveId ? `/api/v1/reports/projects/${effectiveId}/top-contributors/` : null)
  const canViewWorkload = user?.role === 'ADMIN' || user?.role === 'MANAGER'
  const { data: workload } = useApiResource<WorkloadRow[]>(canViewWorkload ? '/api/v1/reports/workload/' : null)

  if (error) return <StatePanel eyebrow="Báo cáo" title="Không tải được dự án" description={error} />
  if (loading) return <div className="h-80 animate-pulse rounded-3xl bg-white" />
  if (!projectsData?.results.length) return <StatePanel eyebrow="Báo cáo" title="Chưa có dữ liệu báo cáo" description="Bạn cần thuộc ít nhất một dự án." />

  return (
    <div className="space-y-6"><header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="section-kicker">Phân tích vận hành</p><h2 className="mt-1 text-3xl font-black tracking-tight">Báo cáo vận hành</h2><p className="mt-2 text-sm text-slate-600">Tiến độ, phân bổ công việc và trao đổi theo đúng phạm vi truy cập.</p></div><label><span className="mb-2 block text-sm font-bold">Dự án</span><select value={effectiveId} onChange={(event) => setSelectedId(event.target.value)} className="min-h-12 rounded-xl border border-slate-300 bg-white px-4">{projectsData.results.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label></header>
      {report && <section className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]"><article className="dashboard-hero rounded-3xl p-7 text-white"><p className="font-mono text-xs font-black uppercase tracking-[0.18em] text-[var(--accent)]">{report.project_name}</p><div className="mt-8"><ReportProgress value={report.progress} label="Tiến độ tổng" /></div><div className="mt-8 grid grid-cols-2 gap-3"><div className="rounded-xl bg-white/10 p-4"><span className="text-xs text-slate-300">Tổng công việc</span><strong className="mt-2 block font-mono text-3xl">{report.total_tasks}</strong></div><div className="rounded-xl bg-white/10 p-4"><span className="text-xs text-slate-300">Đã hoàn thành</span><strong className="mt-2 block font-mono text-3xl">{report.completed_tasks}</strong></div></div></article><article className="rounded-3xl border border-slate-200 bg-white p-6"><p className="section-kicker">Phân bổ</p><h3 className="section-title">Theo trạng thái</h3><div className="mt-5 space-y-3">{report.task_distribution.map((item) => <div key={item.code} className="flex items-center justify-between border-b border-slate-100 py-2 text-sm"><span>{item.name}</span><strong className="font-mono">{item.count}</strong></div>)}</div></article></section>}
      <section className="grid gap-5 lg:grid-cols-2"><article className="rounded-2xl border border-slate-200 bg-white p-5"><p className="section-kicker">Thành viên đóng góp</p><h3 className="section-title">Đóng góp nổi bật</h3><div className="mt-5 space-y-3">{contributors?.map((row, index) => <div key={row.user.id} className="flex items-center gap-3 rounded-xl bg-slate-50 p-3"><span className="grid size-9 place-items-center rounded-full bg-slate-950 font-mono text-xs font-black text-white">{index + 1}</span><div className="min-w-0 flex-1"><strong className="block truncate text-sm">{row.user.full_name}</strong><span className="text-xs text-slate-500">{row.completed_tasks}/{row.total_tasks} hoàn thành</span></div></div>)}</div></article>{canViewWorkload && <article className="rounded-2xl border border-slate-200 bg-white p-5"><p className="section-kicker">Năng lực xử lý</p><h3 className="section-title">Khối lượng đội ngũ</h3><div className="mt-5 space-y-3">{workload?.map((row) => <div key={row.user.id} className="flex items-center justify-between rounded-xl border border-slate-100 p-3"><div><strong className="block text-sm">{row.user.full_name}</strong><span className="text-xs text-slate-500">{row.active_tasks} đang làm / {row.total_tasks} tổng</span></div><span className={`rounded-full px-2 py-1 text-[10px] font-black uppercase ${row.is_available ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{row.is_available ? 'Sẵn sàng' : 'Đang bận'}</span></div>)}</div></article>}</section>
      <ReportsMessages projects={projectsData.results} />
    </div>
  )
}
