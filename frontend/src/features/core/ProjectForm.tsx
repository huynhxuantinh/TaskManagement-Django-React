import { useState, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { apiRequest } from '../../lib/api'
import type { Project, User } from '../../types/api'

export function ProjectForm({ project, ownerOptions = [], onSaved, onCancel }: { project?: Project; ownerOptions?: User[]; onSaved: (project: Project) => void; onCancel: () => void }) {
  const [name, setName] = useState(project?.name ?? '')
  const [description, setDescription] = useState(project?.description ?? '')
  const [startDate, setStartDate] = useState(project?.start_date ?? '')
  const [endDate, setEndDate] = useState(project?.end_date ?? '')
  const [ownerId, setOwnerId] = useState(String(project?.creator.id ?? ''))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (ownerId && ownerId !== String(project?.creator.id ?? '') && !ownerOptions.some((owner) => String(owner.id) === ownerId && owner.is_active && ['ADMIN', 'MANAGER'].includes(owner.role))) {
      setError('Vui lòng chọn chủ dự án hợp lệ đang hoạt động.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const payload: Record<string, unknown> = project ? { expected_updated_at: project.updated_at } : { name, description, start_date: startDate, end_date: endDate }
      if (project) {
        if (name !== project.name) payload.name = name
        if (description !== project.description) payload.description = description
        if (startDate !== (project.start_date ?? '')) payload.start_date = startDate || null
        if (endDate !== (project.end_date ?? '')) payload.end_date = endDate || null
      }
      if (ownerId && ownerOptions.length > 0 && (!project || Number(ownerId) !== project.creator.id)) {
        payload.creator_id = Number(ownerId)
      }
      const saved = await apiRequest<Project>(project ? `/api/v1/projects/${project.id}/` : '/api/v1/projects/', {
        method: project ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
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
      <Field label="Tên dự án" value={name} onChange={(event) => setName(event.target.value)} required maxLength={200} autoFocus />
      <label className="block">
        <span id="project-description-label" className="mb-2 block text-sm font-bold text-slate-800">Mô tả</span>
        <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} maxLength={500} aria-labelledby="project-description-label" aria-describedby="project-description-limit" className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]" />
        <span id="project-description-limit" className="mt-1 block text-xs text-slate-500">{description.length}/500 ký tự</span>
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Ngày bắt đầu" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} required />
        <Field label="Ngày kết thúc" type="date" value={endDate} min={startDate} onChange={(event) => setEndDate(event.target.value)} required />
      </div>
      {ownerOptions.length > 0 && (
        <label className="block">
          <span className="mb-2 block text-sm font-bold text-slate-800">Chủ dự án</span>
          <select className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm" value={ownerId} onChange={(event) => setOwnerId(event.target.value)} required={Boolean(project)}>
            {!project && <option value="">Tôi – Quản trị viên (mặc định)</option>}
            {project && !ownerOptions.some((owner) => owner.id === project.creator.id) && <option value={project.creator.id}>{project.creator.full_name} · {project.creator.email} (chủ hiện tại)</option>}
            {ownerOptions.map((owner) => <option key={owner.id} value={owner.id}>{owner.full_name} · {owner.email}</option>)}
          </select>
        </label>
      )}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Hủy</Button>
        <Button type="submit" disabled={saving}>{saving ? 'Đang lưu…' : project ? 'Lưu thay đổi' : 'Tạo dự án'}</Button>
      </div>
    </form>
  )
}
