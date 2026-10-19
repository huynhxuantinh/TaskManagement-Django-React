import { useMemo, useState, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { useApiResource } from '../../hooks/useApiResource'
import { apiRequest } from '../../lib/api'
import type { Paginated, Project, ProjectMember, Task, TaskStatus } from '../../types/api'

const selectClass = 'min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]'

export function TaskForm({ task, projects, statuses, onSaved, onCancel }: { task?: Task; projects: Project[]; statuses: TaskStatus[]; onSaved: (task: Task) => void; onCancel: () => void }) {
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [projectId, setProjectId] = useState(String(task?.project.id ?? projects[0]?.id ?? ''))
  const [assigneeId, setAssigneeId] = useState(String(task?.assignee?.id ?? ''))
  const [status, setStatus] = useState(task?.status.code ?? statuses[0]?.code ?? 'TODO')
  const [priority, setPriority] = useState(String(task?.priority ?? 2))
  const [deadline, setDeadline] = useState(task?.deadline ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const membersPath = projectId ? `/api/v1/projects/${projectId}/members/?page_size=100` : null
  const { data: members } = useApiResource<Paginated<ProjectMember>>(membersPath)
  const selectedProject = useMemo(() => projects.find((project) => String(project.id) === projectId), [projectId, projects])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!projectId) return
    setSaving(true)
    setError('')
    const common = { title, description, assignee_id: assigneeId ? Number(assigneeId) : null, priority: Number(priority), deadline: deadline || null }
    try {
      const saved = await apiRequest<Task>(task ? `/api/v1/tasks/${task.id}/` : '/api/v1/tasks/', {
        method: task ? 'PATCH' : 'POST',
        body: JSON.stringify(task ? common : { ...common, project_id: Number(projectId), status }),
      })
      onSaved(saved)
    } catch (caught) {
      setError((caught as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Tên công việc" value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={200} autoFocus />
      <label className="block"><span className="mb-2 block text-sm font-bold text-slate-800">Mô tả</span><textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} className={`${selectClass} py-3`} /></label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label><span className="mb-2 block text-sm font-bold text-slate-800">Dự án</span><select className={selectClass} value={projectId} disabled={Boolean(task)} onChange={(event) => { setProjectId(event.target.value); setAssigneeId('') }} required>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
        <label><span className="mb-2 block text-sm font-bold text-slate-800">Người thực hiện</span><select className={selectClass} value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}><option value="">Chưa phân công</option>{members?.results.map((member) => <option key={member.id} value={member.user.id}>{member.user.full_name}</option>)}</select></label>
        {!task && <label><span className="mb-2 block text-sm font-bold text-slate-800">Trạng thái</span><select className={selectClass} value={status} onChange={(event) => setStatus(event.target.value)}>{statuses.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>}
        <label><span className="mb-2 block text-sm font-bold text-slate-800">Ưu tiên</span><select className={selectClass} value={priority} onChange={(event) => setPriority(event.target.value)}><option value="1">Thấp</option><option value="2">Trung bình</option><option value="3">Cao</option></select></label>
        <Field label="Hạn hoàn thành" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} />
      </div>
      {!selectedProject && <p className="text-sm text-amber-700">Bạn chưa có dự án nào có thể giao việc.</p>}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onCancel}>Hủy</Button><Button type="submit" disabled={saving || !selectedProject}>{saving ? 'Đang lưu…' : task ? 'Lưu thay đổi' : 'Tạo công việc'}</Button></div>
    </form>
  )
}
