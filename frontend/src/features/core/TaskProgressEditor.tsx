import { useState, type FormEvent } from 'react'
import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { apiRequest } from '../../lib/api'
import type { Task } from '../../types/api'

export function TaskProgressEditor({ task, onSaved }: { task: Task; onSaved: (task: Task) => void }) {
  const [progress, setProgress] = useState(String(task.progress))
  const [version, setVersion] = useState(task.updated_at)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    const value = Number(progress)
    if (!progress.trim() || !Number.isInteger(value) || value < 0 || value > 100) {
      setError('Tiến độ phải là số nguyên từ 0 đến 100.')
      return
    }
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const updated = await apiRequest<Task>(`/api/v1/tasks/${task.id}/progress/`, {
        method: 'PATCH', body: JSON.stringify({ progress: value, expected_updated_at: version }),
      })
      setVersion(updated.updated_at)
      setProgress(String(updated.progress))
      setMessage('Đã cập nhật tiến độ.')
      onSaved(updated)
    } catch (caught) {
      setError((caught as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return <form onSubmit={submit} className="space-y-3 rounded-xl border border-slate-200 p-4">
    <Field label="Tiến độ thủ công (%)" type="number" min="0" max="100" step="1" value={progress} onChange={(event) => setProgress(event.target.value)} required />
    <p className="text-xs text-slate-500">Tiến độ 100% không tự chuyển trạng thái sang hoàn thành.</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {message && <p role="status" className="text-sm text-emerald-700">{message}</p>}
    <Button type="submit" disabled={saving}>{saving ? 'Đang lưu…' : 'Cập nhật tiến độ'}</Button>
  </form>
}
