import { useState, type FormEvent } from 'react'

import { Button } from '../../components/ui/Button'
import { Field } from '../../components/ui/Field'
import { StatePanel } from '../../components/ui/StatePanel'
import { useToast } from '../../components/ui/ToastContext'
import { useApiResource } from '../../hooks/useApiResource'
import { apiRequest } from '../../lib/api'
import type { Paginated, Project, ProjectMember, User } from '../../types/api'
import { canManageProject } from './permissions'

function initials(name: string) {
  return name.split(' ').slice(-2).map((part) => part[0]).join('').toUpperCase()
}

export function MembersPanel({ project, user }: { project: Project; user: User }) {
  const path = `/api/v1/projects/${project.id}/members/?page_size=100`
  const { data, loading, error, reload } = useApiResource<Paginated<ProjectMember>>(path)
  const [email, setEmail] = useState('')
  const [saving, setSaving] = useState(false)
  const notify = useToast()
  const manageable = canManageProject(user, project)

  async function addMember(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      await apiRequest<ProjectMember>(`/api/v1/projects/${project.id}/members/`, {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setEmail('')
      reload()
      notify('Đã thêm thành viên vào dự án.')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function removeMember(member: ProjectMember) {
    if (!window.confirm(`Xóa ${member.user.full_name} khỏi dự án?`)) return
    try {
      await apiRequest<void>(`/api/v1/projects/${project.id}/members/${member.user.id}/`, { method: 'DELETE' })
      reload()
      notify('Đã xóa thành viên khỏi dự án.')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="section-kicker">Project access</p><h2 className="section-title">Thành viên ({data?.count ?? project.member_count})</h2></div>
        {manageable && (
          <form onSubmit={addMember} className="flex w-full gap-2 sm:w-auto">
            <Field label="Thêm bằng email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="user@task.com" required className="sm:w-64" />
            <Button type="submit" disabled={saving} className="self-end">Thêm</Button>
          </form>
        )}
      </div>
      {error && <div className="mt-5"><StatePanel eyebrow="Lỗi" title="Không tải được thành viên" description={error} /></div>}
      {loading && <div className="mt-5 h-24 animate-pulse rounded-xl bg-slate-100" />}
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {data?.results.map((member) => (
          <article key={member.id} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--accent-soft)] text-xs font-black">{initials(member.user.full_name)}</span>
            <div className="min-w-0 flex-1"><strong className="block truncate text-sm">{member.user.full_name}</strong><span className="block truncate text-xs text-slate-500">{member.user.email} · {member.user.role}</span></div>
            {manageable && member.user.id !== project.creator.id && <Button variant="ghost" className="!min-h-9 !px-2 !text-red-700" onClick={() => void removeMember(member)} aria-label={`Xóa ${member.user.full_name}`}>×</Button>}
          </article>
        ))}
      </div>
    </section>
  )
}
