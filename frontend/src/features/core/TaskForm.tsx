import { useMemo, useState, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { useAllPages } from '../../hooks/useAllPages'
import { apiRequest } from '../../lib/api'
import type { Project, ProjectMember, Task, TaskStatus } from '../../types/api'

const selectClass = 'min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]'

export function TaskForm({ task, projects, statuses, onSaved, onCancel }: { task?: Task; projects: Project[]; statuses: TaskStatus[]; onSaved: (task: Task) => void; onCancel: () => void }) {
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [projectId, setProjectId] = useState(String(task?.project.id ?? projects[0]?.id ?? ''))
  const [assigneeId, setAssigneeId] = useState(String(task?.assignee?.id ?? ''))
  const [status, setStatus] = useState(task?.status.code ?? statuses[0]?.code ?? 'TODO')
  const [statusNote, setStatusNote] = useState('')
  const [priority, setPriority] = useState(String(task?.priority ?? 2))
  const [parentId, setParentId] = useState(String(task?.parent_id ?? ''))
  const [startDate, setStartDate] = useState(task?.start_date ?? '')
  const [estimatedHours, setEstimatedHours] = useState(task?.estimated_hours ?? '')
  const [progress, setProgress] = useState(String(task?.progress ?? 0))
  const [deadline, setDeadline] = useState(task?.deadline ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const membersPath = projectId ? `/api/v1/projects/${projectId}/members/?page_size=100` : null
  const { data: members, loading: membersLoading, error: membersError, reload: reloadMembers } = useAllPages<ProjectMember>(membersPath)
  const tasksPath = projectId ? `/api/v1/tasks/?project=${projectId}&page_size=100` : null
  const { data: projectTasks, loading: tasksLoading, error: tasksError, reload: reloadTasks } = useAllPages<Task>(tasksPath)
  const selectedProject = useMemo(() => projects.find((project) => String(project.id) === projectId), [projectId, projects])
  const parentOptions = useMemo(
    () => projectTasks?.results.filter((item) => (
      item.parent_id === null
      && item.id !== task?.id
      && (item.status.code !== 'COMPLETED' || item.id === task?.parent_id)
    )) ?? [],
    [projectTasks, task?.id, task?.parent_id],
  )
  const progressIsAutomatic = Boolean(task && (task.checklist_total > 0 || task.has_subtasks))
  const listsReady = Boolean(members && projectTasks && !membersLoading && !tasksLoading && !membersError && !tasksError)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!projectId || !listsReady) return
    if (!task && status === 'ON_HOLD' && !statusNote.trim()) {
      setError('Vui lòng nhập lý do tạm dừng.')
      return
    }
    setSaving(true)
    setError('')
    const common: Record<string, unknown> = task ? { expected_updated_at: task.updated_at } : {
      title, description, priority: Number(priority), start_date: startDate || null,
      estimated_hours: estimatedHours || null, deadline: deadline || null,
    }
    if (task) {
      if (title !== task.title) common.title = title
      if (description !== task.description) common.description = description
      if (Number(priority) !== task.priority) common.priority = Number(priority)
      if (startDate !== (task.start_date ?? '')) common.start_date = startDate || null
      if (estimatedHours !== (task.estimated_hours ?? '')) common.estimated_hours = estimatedHours || null
      if (deadline !== (task.deadline ?? '')) common.deadline = deadline || null
    }
    if (!task || assigneeId !== String(task.assignee?.id ?? '')) {
      common.assignee_id = assigneeId ? Number(assigneeId) : null
    }
    if (!progressIsAutomatic && (!task || Number(progress) !== task.progress)) common.progress = Number(progress)
    if (!task && status === 'ON_HOLD') common.note = statusNote.trim()
    if (!task || parentId !== String(task.parent_id ?? '')) {
      common.parent = parentId ? Number(parentId) : null
    }
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
      <label className="block"><span id="task-description-label" className="mb-2 block text-sm font-bold text-slate-800">Mô tả</span><textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} maxLength={500} aria-labelledby="task-description-label" aria-describedby="task-description-limit" className={`${selectClass} py-3`} /><span id="task-description-limit" className="mt-1 block text-xs text-slate-500">{description.length}/500 ký tự</span></label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label><span className="mb-2 block text-sm font-bold text-slate-800">Dự án</span><select className={selectClass} value={projectId} disabled={Boolean(task)} onChange={(event) => { setProjectId(event.target.value); setAssigneeId(''); setParentId('') }} required>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
        <label><span className="mb-2 block text-sm font-bold text-slate-800">Người thực hiện</span><select className={selectClass} value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}><option value="">Chưa phân công</option>{task?.assignee && !members?.results.some((member) => member.user.id === task.assignee?.id) && <option value={task.assignee.id} disabled>{task.assignee.full_name} (không còn trong danh sách)</option>}{members?.results.map((member) => <option key={member.id} value={member.user.id} disabled={!member.user.is_active}>{member.user.full_name}{member.user.is_active ? '' : ' (đã vô hiệu hóa)'}</option>)}</select></label>
        {!task && <label><span className="mb-2 block text-sm font-bold text-slate-800">Trạng thái</span><select className={selectClass} value={status} onChange={(event) => setStatus(event.target.value)}>{statuses.map((item) => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label>}
        <label><span className="mb-2 block text-sm font-bold text-slate-800">Ưu tiên</span><select className={selectClass} value={priority} onChange={(event) => setPriority(event.target.value)}><option value="1">Thấp</option><option value="2">Trung bình</option><option value="3">Cao</option></select></label>
        {!task?.has_subtasks && <label><span className="mb-2 block text-sm font-bold text-slate-800">Công việc cha</span><select className={selectClass} value={parentId} onChange={(event) => setParentId(event.target.value)}><option value="">Không có</option>{parentOptions.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}
        <Field label="Ngày bắt đầu" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        <Field label="Hạn hoàn thành" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} />
        <Field label="Giờ ước lượng" type="number" min="0.01" step="0.01" value={estimatedHours} onChange={(event) => setEstimatedHours(event.target.value)} placeholder="Ví dụ: 8" />
        <Field label="Tiến độ (%)" type="number" min="0" max="100" value={progress} disabled={progressIsAutomatic} onChange={(event) => setProgress(event.target.value)} />
      </div>
      {parentId && <p role="note" className="text-sm text-amber-700">Khi có công việc con, tiến độ của công việc cha được tính từ các công việc con thay vì checklist hoặc tiến độ nhập tay của cha. Số hiển thị có thể thay đổi.</p>}
      {membersLoading && <p role="status" className="text-sm text-slate-600">Đang tải danh sách thành viên…</p>}
      {membersError && <div role="alert" className="flex items-center gap-2 text-sm text-red-700"><span>Không tải được thành viên: {membersError}</span><Button type="button" variant="secondary" onClick={reloadMembers}>Thử lại thành viên</Button></div>}
      {tasksLoading && <p role="status" className="text-sm text-slate-600">Đang tải danh sách công việc cha…</p>}
      {tasksError && <div role="alert" className="flex items-center gap-2 text-sm text-red-700"><span>Không tải được công việc cha: {tasksError}</span><Button type="button" variant="secondary" onClick={reloadTasks}>Thử lại công việc</Button></div>}
      {!task && status === 'ON_HOLD' && <Field label="Lý do tạm dừng" value={statusNote} onChange={(event) => setStatusNote(event.target.value)} required maxLength={500} />}
      {progressIsAutomatic && <p className="text-xs font-semibold text-sky-700">Tiến độ đang được tính tự động từ checklist hoặc công việc con.</p>}
      <p className="text-xs text-slate-600">Tiến độ và trạng thái độc lập: đạt 100% không tự chuyển sang hoàn thành. Hãy cập nhật trạng thái khi công việc thực sự hoàn tất.</p>
      {!selectedProject && <p className="text-sm text-amber-700">Bạn chưa có dự án nào có thể giao việc.</p>}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onCancel}>Hủy</Button><Button type="submit" disabled={saving || !selectedProject || !listsReady}>{saving ? 'Đang lưu…' : task ? 'Lưu thay đổi' : 'Tạo công việc'}</Button></div>
    </form>
  )
}
