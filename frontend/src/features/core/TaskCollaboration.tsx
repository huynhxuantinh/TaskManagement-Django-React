import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '../../components/ui/Button'
import { apiDownload, apiRequest } from '../../lib/api'

type Person = { full_name: string } | null
type Comment = { id: number; body: string; author: Person; created_at: string }
type Attachment = { id: number; original_name: string; size: number; uploader: Person }

export function TaskCollaboration({ taskId }: { taskId: number }) {
  const [comments, setComments] = useState<Comment[]>([])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [body, setBody] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const base = `/api/v1/tasks/${taskId}`

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [nextComments, nextAttachments] = await Promise.all([
          apiRequest<Comment[]>(`${base}/comments/`, { signal: controller.signal }), apiRequest<Attachment[]>(`${base}/attachments/`, { signal: controller.signal }),
        ])
        if (!controller.signal.aborted) { setComments(nextComments); setAttachments(nextAttachments); setLoaded(true) }
      } catch (caught) { if (!controller.signal.aborted) setError((caught as Error).message) }
      finally { if (!controller.signal.aborted) setLoading(false) }
    }
    void load()
    return () => controller.abort()
  }, [base, version])

  async function submitComment(event: FormEvent) {
    event.preventDefault()
    if (!body.trim()) return
    setBusy(true); setError('')
    try {
      const comment = await apiRequest<Comment>(`${base}/comments/`, { method: 'POST', body: JSON.stringify({ body: body.trim() }) })
      setComments((current) => [...current, comment]); setBody('')
    } catch (caught) { setError((caught as Error).message) }
    finally { setBusy(false) }
  }

  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    if (file.size > 10 * 1024 * 1024) { setError('Tệp đính kèm tối đa 10 MB.'); return }
    setBusy(true); setError('')
    const form = new FormData(); form.append('file', file)
    try {
      const attachment = await apiRequest<Attachment>(`${base}/attachments/`, { method: 'POST', body: form })
      setAttachments((current) => [...current, attachment]); setFile(null); setFileInputKey((value) => value + 1)
    } catch (caught) { setError((caught as Error).message) }
    finally { setBusy(false) }
  }

  async function download(item: Attachment) {
    setBusy(true); setError('')
    try {
      const blob = await apiDownload(`${base}/attachments/${item.id}/download/`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a'); link.href = url; link.download = item.original_name; link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (caught) { setError((caught as Error).message) }
    finally { setBusy(false) }
  }

  return <section aria-label="Bình luận và tệp đính kèm" className="space-y-4 rounded-xl border border-slate-200 p-4">
    {error && <p role="alert" className="text-sm text-red-700">{error} <Button type="button" variant="secondary" onClick={() => setVersion((value) => value + 1)}>Thử lại</Button></p>}
    {loading ? <p role="status">Đang tải…</p> : loaded && <>
      <h3 className="font-bold">Bình luận</h3>
      {comments.length === 0 ? <p className="text-sm text-slate-500">Chưa có bình luận.</p> : <ul className="space-y-2">{comments.map((item) => <li key={item.id} className="rounded-lg bg-slate-50 p-3 text-sm"><strong>{item.author?.full_name ?? 'Tài khoản đã xóa'}</strong><p className="whitespace-pre-wrap break-words">{item.body}</p></li>)}</ul>}
      <form onSubmit={submitComment} className="space-y-2"><label className="block text-sm font-semibold" htmlFor={`comment-${taskId}`}>Bình luận mới</label><textarea id={`comment-${taskId}`} value={body} onChange={(event) => setBody(event.target.value)} maxLength={5000} required className="w-full rounded-lg border border-slate-300 p-2" /><Button disabled={busy || !body.trim()} type="submit">Gửi bình luận</Button></form>
      <h3 className="font-bold">Tệp đính kèm</h3>
      {attachments.length === 0 ? <p className="text-sm text-slate-500">Chưa có tệp đính kèm.</p> : <ul className="space-y-2">{attachments.map((item) => <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 text-sm"><span className="break-all">{item.original_name} ({Math.ceil(item.size / 1024)} KB)</span><Button type="button" variant="secondary" disabled={busy} onClick={() => void download(item)}>Tải xuống</Button></li>)}</ul>}
      <form onSubmit={upload} className="space-y-2"><label htmlFor={`attachment-${taskId}`} className="block text-sm font-semibold">Chọn tệp (tối đa 10 MB)</label><input key={fileInputKey} id={`attachment-${taskId}`} type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="block w-full text-sm" /><Button type="submit" disabled={busy || !file}>Tải tệp lên</Button></form>
    </>}
  </section>
}
