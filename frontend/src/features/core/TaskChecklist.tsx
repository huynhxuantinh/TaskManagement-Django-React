import { useRef, useState, type DragEvent, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { useToast } from '../../components/ui/ToastContext'
import { apiRequest } from '../../lib/api'
import type { Task, TaskChecklistItem } from '../../types/api'

export function TaskChecklist({ task, onChanged, draft, onDraftChange }: { task: Task; onChanged: () => void; draft?: string; onDraftChange?: (value: string) => void }) {
  const notify = useToast()
  const [items, setItems] = useState(task.checklist ?? [])
  const [localTitle, setLocalTitle] = useState('')
  const title = draft ?? localTitle
  const setTitle = onDraftChange ?? setLocalTitle
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const [draggedId, setDraggedId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const canEdit = task.can_edit_checklist

  function beginSave() {
    if (!canEdit || savingRef.current) return false
    savingRef.current = true
    setSaving(true)
    return true
  }

  function endSave() {
    savingRef.current = false
    setSaving(false)
  }

  async function addItem(event: FormEvent) {
    event.preventDefault()
    const value = title.trim()
    if (!value || !beginSave()) return
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
      endSave()
    }
  }

  async function toggle(item: TaskChecklistItem) {
    if (!beginSave()) return
    try {
      const saved = await apiRequest<TaskChecklistItem>(
        `/api/v1/tasks/${task.id}/checklist/${item.id}/`,
        { method: 'PATCH', body: JSON.stringify({ is_completed: !item.is_completed }) },
      )
      setItems((current) => current.map((row) => row.id === saved.id ? saved : row))
      onChanged()
    } catch (caught) {
      notify((caught as Error).message, 'error')
    } finally {
      endSave()
    }
  }

  async function saveTitle(item: TaskChecklistItem) {
    const value = editTitle.trim()
    if (!value || savingRef.current) return
    if (value === item.title) { setEditingId(null); return }
    if (!beginSave()) return
    try {
      const saved = await apiRequest<TaskChecklistItem>(`/api/v1/tasks/${task.id}/checklist/${item.id}/`, {
        method: 'PATCH', body: JSON.stringify({ title: value }),
      })
      setItems((current) => current.map((row) => row.id === saved.id ? saved : row))
      setEditingId(null)
      setEditTitle('')
      onChanged()
    } catch (caught) {
      notify((caught as Error).message, 'error')
    } finally {
      endSave()
    }
  }

  async function remove(item: TaskChecklistItem) {
    if (savingRef.current) return
    if (!window.confirm(`Xóa mục “${item.title}”?`)) return
    if (!beginSave()) return
    try {
      await apiRequest<void>(`/api/v1/tasks/${task.id}/checklist/${item.id}/`, {
        method: 'DELETE',
      })
      setItems((current) => current.filter((row) => row.id !== item.id))
      onChanged()
    } catch (caught) {
      notify((caught as Error).message, 'error')
    } finally {
      endSave()
    }
  }

  async function saveOrder(reordered: TaskChecklistItem[], previous: TaskChecklistItem[]) {
    if (!beginSave()) return
    setItems(reordered)
    try {
      const saved = await apiRequest<TaskChecklistItem[]>(
        `/api/v1/tasks/${task.id}/checklist/order/`,
        { method: 'PUT', body: JSON.stringify({ item_ids: reordered.map((item) => item.id) }) },
      )
      setItems(saved)
      onChanged()
    } catch (caught) {
      setItems(previous)
      notify((caught as Error).message, 'error')
    } finally {
      endSave()
    }
  }

  async function move(itemId: number, offset: -1 | 1) {
    const from = items.findIndex((item) => item.id === itemId)
    const to = from + offset
    if (from < 0 || to < 0 || to >= items.length) return
    const reordered = [...items]
    const [moved] = reordered.splice(from, 1)
    reordered.splice(to, 0, moved)
    await saveOrder(reordered, items)
  }

  async function dropOn(targetId: number, event: DragEvent<HTMLLIElement>) {
    event.preventDefault()
    if (savingRef.current || draggedId === null || draggedId === targetId) return
    const from = items.findIndex((item) => item.id === draggedId)
    const to = items.findIndex((item) => item.id === targetId)
    if (from < 0 || to < 0) return
    const reordered = [...items]
    const [moved] = reordered.splice(from, 1)
    reordered.splice(to, 0, moved)
    setDraggedId(null)
    await saveOrder(reordered, items)
  }

  return (
    <section className="space-y-3" aria-busy={saving}>
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="section-kicker">Checklist</p>
          <h3 className="text-lg font-extrabold">{task.checklist_done}/{task.checklist_total} mục hoàn thành</h3>
        </div>
        <span className="text-right text-xs font-semibold text-slate-600">Tiến độ công việc <strong className="font-mono text-sm font-black">{task.effective_progress}%</strong></span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${task.effective_progress}%` }} />
      </div>
      {items.length === 0 && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Chưa có mục checklist.</p>}
      <ol className="space-y-2">
        {items.map((item, index) => (
          <li
            key={item.id}
            draggable={canEdit && !saving && editingId === null}
            onDragStart={() => setDraggedId(item.id)}
            onDragOver={(event) => canEdit && event.preventDefault()}
            onDrop={(event) => void dropOn(item.id, event)}
            className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3"
          >
            <span aria-hidden="true" className={`select-none text-slate-400 ${canEdit ? 'cursor-grab' : ''}`}>⋮⋮</span>
            <input aria-label={`Hoàn thành ${item.title}`} type="checkbox" checked={item.is_completed} disabled={!canEdit || saving || editingId !== null} onChange={() => void toggle(item)} className="size-4 accent-slate-900" />
            {editingId === item.id ? <input aria-label="Nội dung mục checklist" value={editTitle} onChange={(event) => setEditTitle(event.target.value)} maxLength={300} autoFocus className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2 py-2 text-sm" /> : <span className={`min-w-0 flex-1 text-sm ${item.is_completed ? 'text-slate-400 line-through' : 'text-slate-800'}`}>{item.title}</span>}
            {canEdit && editingId === item.id && <div className="flex items-center gap-1"><Button type="button" variant="secondary" disabled={saving} onClick={() => { setEditingId(null); setEditTitle('') }}>Hủy</Button><Button type="button" disabled={saving || !editTitle.trim()} onClick={() => void saveTitle(item)}>{saving ? 'Đang lưu…' : 'Lưu'}</Button></div>}
            {canEdit && editingId === null && <div className="flex items-center gap-1">
              <Button type="button" variant="ghost" className="!min-h-9 !px-2" disabled={saving} aria-label={`Sửa ${item.title}`} onClick={() => { setEditingId(item.id); setEditTitle(item.title) }}>Sửa</Button>
              <Button type="button" variant="ghost" className="!min-h-9 !px-2" disabled={saving || index === 0} aria-label={`Di chuyển ${item.title} lên`} onClick={() => void move(item.id, -1)}>↑</Button>
              <Button type="button" variant="ghost" className="!min-h-9 !px-2" disabled={saving || index === items.length - 1} aria-label={`Di chuyển ${item.title} xuống`} onClick={() => void move(item.id, 1)}>↓</Button>
              <Button type="button" variant="ghost" disabled={saving} className="!text-red-700" onClick={() => void remove(item)}>Xóa</Button>
            </div>}
          </li>
        ))}
      </ol>
      {canEdit ? (
        <form onSubmit={addItem} className="flex items-end gap-2">
          <Field label="Mục mới" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={300} className="min-w-0" />
          <Button type="submit" disabled={saving || !title.trim() || items.length >= 100}>{saving ? 'Đang lưu…' : 'Thêm'}</Button>
        </form>
      ) : (
        <p className="text-xs text-slate-500">Checklist chỉ đọc do trạng thái hoặc quyền hiện tại.</p>
      )}
    </section>
  )
}
