import { useState, type DragEvent, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { useToast } from '../../components/ui/ToastContext'
import { apiRequest } from '../../lib/api'
import type { Task, TaskChecklistItem } from '../../types/api'

export function TaskChecklist({ task, onChanged }: { task: Task; onChanged: () => void }) {
  const notify = useToast()
  const [items, setItems] = useState(task.checklist ?? [])
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [draggedId, setDraggedId] = useState<number | null>(null)
  const canEdit = task.status.code !== 'COMPLETED' && task.allowed_transitions.length > 0

  async function addItem(event: FormEvent) {
    event.preventDefault()
    const value = title.trim()
    if (!value) return
    setSaving(true)
    try {
      const item = await apiRequest<TaskChecklistItem>(`/api/v1/tasks/${task.id}/checklist/`, {
        method: 'POST',
        body: JSON.stringify({ title: value }),
      })
      setItems((current) => [...current, item])
      setTitle('')
      onChanged()
    } catch (caught) {
      notify((caught as Error).message, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function toggle(item: TaskChecklistItem) {
    try {
      const saved = await apiRequest<TaskChecklistItem>(
        `/api/v1/tasks/${task.id}/checklist/${item.id}/`,
        { method: 'PATCH', body: JSON.stringify({ is_completed: !item.is_completed }) },
      )
      setItems((current) => current.map((row) => row.id === saved.id ? saved : row))
      onChanged()
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  async function remove(item: TaskChecklistItem) {
    if (!window.confirm(`Xóa mục “${item.title}”?`)) return
    try {
      await apiRequest<void>(`/api/v1/tasks/${task.id}/checklist/${item.id}/`, {
        method: 'DELETE',
      })
      setItems((current) => current.filter((row) => row.id !== item.id))
      onChanged()
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  async function dropOn(targetId: number, event: DragEvent<HTMLLIElement>) {
    event.preventDefault()
    if (draggedId === null || draggedId === targetId) return
    const reordered = [...items]
    const from = reordered.findIndex((item) => item.id === draggedId)
    const to = reordered.findIndex((item) => item.id === targetId)
    if (from < 0 || to < 0) return
    const [moved] = reordered.splice(from, 1)
    reordered.splice(to, 0, moved)
    setItems(reordered)
    setDraggedId(null)
    try {
      const saved = await apiRequest<TaskChecklistItem[]>(
        `/api/v1/tasks/${task.id}/checklist/order/`,
        { method: 'PUT', body: JSON.stringify({ item_ids: reordered.map((item) => item.id) }) },
      )
      setItems(saved)
      onChanged()
    } catch (caught) {
      setItems(task.checklist ?? [])
      notify((caught as Error).message, 'error')
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="section-kicker">Checklist</p>
          <h3 className="text-lg font-extrabold">{task.checklist_done}/{task.checklist_total} mục hoàn thành</h3>
        </div>
        <span className="font-mono text-sm font-black text-slate-600">{task.effective_progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${task.effective_progress}%` }} />
      </div>
      {items.length === 0 && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Chưa có mục checklist.</p>}
      <ol className="space-y-2">
        {items.map((item) => (
          <li
            key={item.id}
            draggable={canEdit}
            onDragStart={() => setDraggedId(item.id)}
            onDragOver={(event) => canEdit && event.preventDefault()}
            onDrop={(event) => void dropOn(item.id, event)}
            className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3"
          >
            <span aria-hidden="true" className={`select-none text-slate-400 ${canEdit ? 'cursor-grab' : ''}`}>⋮⋮</span>
            <input aria-label={`Hoàn thành ${item.title}`} type="checkbox" checked={item.is_completed} disabled={!canEdit} onChange={() => void toggle(item)} className="size-4 accent-slate-900" />
            <span className={`min-w-0 flex-1 text-sm ${item.is_completed ? 'text-slate-400 line-through' : 'text-slate-800'}`}>{item.title}</span>
            {canEdit && <Button variant="ghost" className="!text-red-700" onClick={() => void remove(item)}>Xóa</Button>}
          </li>
        ))}
      </ol>
      {canEdit ? (
        <form onSubmit={addItem} className="flex items-end gap-2">
          <Field label="Mục mới" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={300} className="min-w-0" />
          <Button type="submit" disabled={saving || !title.trim() || items.length >= 100}>{saving ? 'Đang thêm…' : 'Thêm'}</Button>
        </form>
      ) : (
        <p className="text-xs text-slate-500">Checklist chỉ đọc do trạng thái hoặc quyền hiện tại.</p>
      )}
    </section>
  )
}
