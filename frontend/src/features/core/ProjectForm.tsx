import { useState, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { apiRequest } from '../../lib/api'
import type { Project } from '../../types/api'

export function ProjectForm({ project, onSaved, onCancel }: { project?: Project; onSaved: (project: Project) => void; onCancel: () => void }) {
  const [name, setName] = useState(project?.name ?? '')
  const [description, setDescription] = useState(project?.description ?? '')
  const [startDate, setStartDate] = useState(project?.start_date ?? '')
  const [endDate, setEndDate] = useState(project?.end_date ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const saved = await apiRequest<Project>(project ? `/api/v1/projects/${project.id}/` : '/api/v1/projects/', {
        method: project ? 'PATCH' : 'POST',
        body: JSON.stringify({ name, description, start_date: startDate, end_date: endDate }),
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
        <span className="mb-2 block text-sm font-bold text-slate-800">Mô tả</span>
        <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]" />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Ngày bắt đầu" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} required />
        <Field label="Ngày kết thúc" type="date" value={endDate} min={startDate} onChange={(event) => setEndDate(event.target.value)} required />
      </div>
      {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>Hủy</Button>
        <Button type="submit" disabled={saving}>{saving ? 'Đang lưu…' : project ? 'Lưu thay đổi' : 'Tạo dự án'}</Button>
      </div>
    </form>
  )
}
