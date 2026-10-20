import { useMemo, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { Modal } from '../components/ui/Modal'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { TaskForm } from '../features/core/TaskForm'
import { TaskHistory } from '../features/core/TaskHistory'
import { TaskStatusSelect } from '../features/core/TaskStatusSelect'
import { allowedTaskStatusCodes, canChangeTaskStatus, canCreateProjects, canManageProject } from '../features/core/permissions'
import { useApiResource } from '../hooks/useApiResource'
import { apiDownload, apiRequest } from '../lib/api'
import type { Paginated, Project, Task, TaskStatus } from '../types/api'

const selectClass = 'min-h-12 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]'
const priorities: Record<number, string> = { 1: 'Thấp', 2: 'Trung bình', 3: 'Cao' }

export function TasksPage() {
  const [searchParams] = useSearchParams()
  const { user } = useAuth()
  const notify = useToast()
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [projectFilter, setProjectFilter] = useState(searchParams.get('project') ?? '')
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [deadlineFrom, setDeadlineFrom] = useState('')
  const [deadlineTo, setDeadlineTo] = useState('')
  const [deadlinePreset, setDeadlinePreset] = useState('')
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Task | undefined>()
  const [historyTask, setHistoryTask] = useState<Task | undefined>()
  const [statusChange, setStatusChange] = useState<{ task: Task; status: string } | undefined>()
  const [statusNote, setStatusNote] = useState('')
  const params = new URLSearchParams({ page_size: '100' })
  if (search) params.set('search', search)
  if (projectFilter) params.set('project', projectFilter)
  if (statusFilter) params.set('status', statusFilter)
  if (priorityFilter) params.set('priority', priorityFilter)
  if (deadlineFrom) params.set('deadline_from', deadlineFrom)
  if (deadlineTo) params.set('deadline_to', deadlineTo)
  if (deadlinePreset) params.set(deadlinePreset, 'true')
  const { data, setData, loading, error, reload } = useApiResource<Paginated<Task>>(`/api/v1/tasks/?${params}`)
  const { data: projectsData } = useApiResource<Paginated<Project>>('/api/v1/projects/?page_size=100')
  const { data: statuses } = useApiResource<TaskStatus[]>('/api/v1/metadata/task-statuses/')
  const projectById = useMemo(() => new Map(projectsData?.results.map((project) => [project.id, project]) ?? []), [projectsData])
  const manageableProjects = useMemo(() => {
    if (!user) return []
    return projectsData?.results.filter((project) => canManageProject(user, project)) ?? []
  }, [projectsData, user])

  function submitSearch(event: FormEvent) {
    event.preventDefault()
    setSearch(query.trim())
  }

  async function changeStatus(task: Task, status: string, note: string) {
    try {
      const saved = await apiRequest<Task>(`/api/v1/tasks/${task.id}/status/`, { method: 'PATCH', body: JSON.stringify({ status, note }) })
      setData((current) => current ? { ...current, results: current.results.map((item) => item.id === saved.id ? saved : item) } : current)
      notify('Đã cập nhật trạng thái.')
      return true
    } catch (caught) {
      notify((caught as Error).message, 'error')
      return false
    }
  }

  async function submitStatusChange(event: FormEvent) {
    event.preventDefault()
    if (!statusChange || !statusNote.trim()) return
    if (await changeStatus(statusChange.task, statusChange.status, statusNote.trim())) {
      setStatusChange(undefined)
      setStatusNote('')
    }
  }

  async function remove(task: Task) {
    if (!window.confirm(`Xóa công việc “${task.title}”?`)) return
    try {
      await apiRequest<void>(`/api/v1/tasks/${task.id}/`, { method: 'DELETE' })
      reload()
      notify('Đã xóa công việc.')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  async function exportCsv() {
    try {
      const exportParams = new URLSearchParams(params)
      exportParams.delete('page_size')
      const blob = await apiDownload(`/api/v1/tasks/export/?${exportParams}`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'cong-viec.csv'
      link.click()
      URL.revokeObjectURL(url)
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="section-kicker">Danh sách thực hiện / {data?.count ?? 0}</p><h2 className="mt-1 text-3xl font-black tracking-tight">Luồng công việc</h2><p className="mt-2 text-sm text-slate-600">Lọc nhanh, giao việc và cập nhật tiến độ ngay tại một nơi.</p></div><div className="flex gap-2"><Button variant="secondary" onClick={() => void exportCsv()}>Xuất CSV</Button>{user && canCreateProjects(user) && <Button disabled={manageableProjects.length === 0} onClick={() => setCreating(true)}>+ Giao công việc</Button>}</div></header>

      <section className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 md:grid-cols-[minmax(14rem,1fr)_auto_auto_auto] md:items-end">
        <form onSubmit={submitSearch} className="flex gap-2"><Field label="Tìm công việc" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tên hoặc mô tả…" /><Button type="submit" variant="secondary" className="self-end">Tìm</Button></form>
        <label><span className="mb-2 block text-sm font-bold">Dự án</span><select className={selectClass} value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}><option value="">Tất cả</option>{projectsData?.results.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
        <label><span className="mb-2 block text-sm font-bold">Trạng thái</span><select className={selectClass} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">Tất cả</option>{statuses?.map((status) => <option key={status.code} value={status.code}>{status.name}</option>)}</select></label>
        <label><span className="mb-2 block text-sm font-bold">Ưu tiên</span><select className={selectClass} value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}><option value="">Tất cả</option><option value="1">Thấp</option><option value="2">Trung bình</option><option value="3">Cao</option></select></label>
      </section>
      <section className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 md:grid-cols-3">
        <label><span className="mb-2 block text-sm font-bold">Hạn từ ngày</span><input type="date" className={selectClass} value={deadlineFrom} onChange={(event) => setDeadlineFrom(event.target.value)} /></label>
        <label><span className="mb-2 block text-sm font-bold">Đến ngày</span><input type="date" className={selectClass} value={deadlineTo} onChange={(event) => setDeadlineTo(event.target.value)} /></label>
        <label><span className="mb-2 block text-sm font-bold">Mức độ hạn</span><select className={selectClass} value={deadlinePreset} onChange={(event) => setDeadlinePreset(event.target.value)}><option value="">Tất cả</option><option value="overdue">Quá hạn</option><option value="due_soon">Sắp hạn (3 ngày)</option></select></label>
      </section>

      {error && <StatePanel eyebrow="Lỗi đồng bộ" title="Không tải được công việc" description={error} />}
      {loading && <div className="h-72 animate-pulse rounded-2xl bg-white" />}
      {!loading && data?.results.length === 0 && <StatePanel eyebrow="Danh sách công việc" title="Không có công việc phù hợp" description="Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm." />}
      <section className="grid gap-3" aria-label="Danh sách công việc">
        {data?.results.map((task) => {
          const project = projectById.get(task.project.id)
          const manageable = Boolean(user && project && canManageProject(user, project))
          const allowedStatuses = user ? allowedTaskStatusCodes(user, task) : []
          return (
            <article key={task.id} className={`grid gap-4 rounded-2xl border bg-white p-5 shadow-[var(--shadow)] md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-center ${task.is_overdue ? 'border-red-300' : 'border-slate-200'}`}>
              <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><span className={`size-2.5 rounded-full ${task.priority === 3 ? 'bg-red-500' : task.priority === 2 ? 'bg-amber-400' : 'bg-slate-300'}`} /><h3 className="truncate font-extrabold text-slate-950">{task.title}</h3>{task.is_overdue && <span className="rounded-full bg-red-50 px-2 py-1 text-[10px] font-black uppercase text-red-700">Quá hạn</span>}</div><p className="mt-2 line-clamp-1 text-sm text-slate-500">{task.project.name} · {task.assignee?.full_name ?? 'Chưa phân công'} · {priorities[task.priority]}</p></div>
              {user && <TaskStatusSelect task={task} statuses={statuses ?? [task.status]} canChange={canChangeTaskStatus(user, task, project)} allowedStatusCodes={allowedStatuses} onChange={(status) => { setStatusChange({ task, status }); setStatusNote('') }} />}
              <div className="flex justify-end gap-1"><Button variant="ghost" onClick={() => setHistoryTask(task)}>Lịch sử</Button>{manageable && <><Button variant="ghost" onClick={() => setEditing(task)}>Sửa</Button><Button variant="ghost" className="!text-red-700" onClick={() => void remove(task)}>Xóa</Button></>}</div>
            </article>
          )
        })}
      </section>

      <Modal open={creating} title="Giao công việc mới" onClose={() => setCreating(false)}><TaskForm projects={manageableProjects} statuses={statuses ?? []} onCancel={() => setCreating(false)} onSaved={() => { setCreating(false); reload(); notify('Đã tạo công việc.') }} /></Modal>
      <Modal open={Boolean(editing)} title="Cập nhật công việc" onClose={() => setEditing(undefined)}>{editing && <TaskForm task={editing} projects={projectsData?.results ?? []} statuses={statuses ?? []} onCancel={() => setEditing(undefined)} onSaved={() => { setEditing(undefined); reload(); notify('Đã cập nhật công việc.') }} />}</Modal>
      <Modal open={Boolean(historyTask)} title={`Lịch sử · ${historyTask?.title ?? ''}`} onClose={() => setHistoryTask(undefined)}>{historyTask && <TaskHistory task={historyTask} />}</Modal>
      <Modal open={Boolean(statusChange)} title="Ghi chú thay đổi trạng thái" onClose={() => { setStatusChange(undefined); setStatusNote('') }}>
        <form className="space-y-4" onSubmit={submitStatusChange}>
          <p className="text-sm text-slate-600">Ghi chú này được lưu vào lịch sử công việc.</p>
          <label className="block text-sm font-bold">Ghi chú<textarea required maxLength={500} value={statusNote} onChange={(event) => setStatusNote(event.target.value)} className="mt-2 min-h-28 w-full rounded-xl border border-slate-300 p-3 font-normal outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]" placeholder="Nêu lý do hoặc kết quả cập nhật..." /></label>
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => { setStatusChange(undefined); setStatusNote('') }}>Hủy</Button><Button type="submit" disabled={!statusNote.trim()}>Cập nhật</Button></div>
        </form>
      </Modal>
    </div>
  )
}
