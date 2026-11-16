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
  const [baseline, setBaseline] = useState(project)
  const [conflict, setConflict] = useState(false)
  const [notice, setNotice] = useState('')

  async function reloadLatest() {
    if (!baseline) return
    setSaving(true)
    try {
      const latest = await apiRequest<Project>(`/api/v1/projects/${baseline.id}/`)
      if (name === baseline.name) setName(latest.name)
      if (description === baseline.description) setDescription(latest.description)
      if (startDate === (baseline.start_date ?? '')) setStartDate(latest.start_date ?? '')
      if (endDate === (baseline.end_date ?? '')) setEndDate(latest.end_date ?? '')
      if (ownerId === String(baseline.creator.id)) setOwnerId(String(latest.creator.id))
      setBaseline(latest)
      setConflict(false)
      setError('')
      setNotice('Đã tải dữ liệu mới và giữ các trường bạn đã sửa. Hãy kiểm tra lại trước khi lưu; nội dung bạn sửa có thể ghi đè thay đổi cùng trường của người khác.')
    } catch (caught) {
      setError((caught as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (conflict) return
    if (ownerId && ownerId !== String(baseline?.creator.id ?? '') && !ownerOptions.some((owner) => String(owner.id) === ownerId && owner.is_active && ['ADMIN', 'MANAGER'].includes(owner.role))) {
      setError('Vui lòng chọn chủ dự án hợp lệ đang hoạt động.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const payload: Record<string, unknown> = baseline ? { expected_updated_at: baseline.updated_at } : { name, description, start_date: startDate || null, end_date: endDate || null }
      if (baseline) {
        if (name !== baseline.name) payload.name = name
        if (description !== baseline.description) payload.description = description
        if (startDate !== (baseline.start_date ?? '')) payload.start_date = startDate || null
        if (endDate !== (baseline.end_date ?? '')) payload.end_date = endDate || null
      }
      if (ownerId && ownerOptions.length > 0 && (!baseline || Number(ownerId) !== baseline.creator.id)) {
        payload.creator_id = Number(ownerId)
      }
      const saved = await apiRequest<Project>(project ? `/api/v1/projects/${project.id}/` : '/api/v1/projects/', {
        method: project ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      })
      onSaved(saved)
    } catch (caught) {
      if (caught && typeof caught === 'object' && 'status' in caught && caught.status === 409) setConflict(true)
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
        <Field label="Ngày bắt đầu" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        <Field label="Ngày kết thúc" type="date" value={endDate} min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} />
      </div>
      {ownerOptions.length > 0 && (
        <label className="block">
          <span className="mb-2 block text-sm font-bold text-slate-800">Chủ dự án</span>
          <select className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm" value={ownerId} onChange={(event) => setOwnerId(event.target.value)} required={Boolean(project)}>
            {!project && <option value="">Tôi – Quản trị viên (mặc định)</option>}
            {baseline && !ownerOptions.some((owner) => owner.id === baseline.creator.id) && <option value={baseline.creator.id}>{baseline.creator.full_name} · {baseline.creator.email} (chủ hiện tại)</option>}
            {ownerOptions.map((owner) => <option key={owner.id} value={owner.id}>{owner.full_name} · {owner.email}</option>)}
          </select>
        </label>
      )}
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      {conflict && <Button type="button" variant="secondary" disabled={saving} onClick={() => void reloadLatest()}>Tải dữ liệu mới</Button>}
      {notice && <p role="status" className="text-sm text-amber-700">{notice}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Hủy</Button>
        <Button type="submit" disabled={saving || conflict}>{saving ? 'Đang lưu…' : project ? 'Lưu thay đổi' : 'Tạo dự án'}</Button>
      </div>
    </form>
  )
}
