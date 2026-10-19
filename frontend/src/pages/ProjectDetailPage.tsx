import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { MembersPanel } from '../features/core/MembersPanel'
import { ProjectActions } from '../features/core/ProjectActions'
import { ProjectForm } from '../features/core/ProjectForm'
import { Modal } from '../components/ui/Modal'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { useApiResource } from '../hooks/useApiResource'
import { apiRequest } from '../lib/api'
import type { Project } from '../types/api'

export function ProjectDetailPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const notify = useToast()
  const [editing, setEditing] = useState(false)
  const { data: project, setData: setProject, loading, error } = useApiResource<Project>(projectId ? `/api/v1/projects/${projectId}/` : null)

  async function remove() {
    if (!project || !window.confirm(`Xóa dự án “${project.name}”?`)) return
    try {
      await apiRequest<void>(`/api/v1/projects/${project.id}/`, { method: 'DELETE' })
      notify('Đã xóa dự án.')
      navigate('/projects')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  if (loading) return <div className="h-80 animate-pulse rounded-3xl bg-white" />
  if (error || !project || !user) return <StatePanel eyebrow="Dự án" title="Không mở được dự án" description={error || 'Dự án không tồn tại trong phạm vi của bạn.'} />

  return (
    <div className="space-y-6">
      <Link to="/projects" className="text-sm font-bold text-slate-600 hover:text-slate-950">← Danh sách dự án</Link>
      <section className="dashboard-hero overflow-hidden rounded-3xl p-7 text-white md:p-9">
        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl"><p className="font-mono text-xs font-black uppercase tracking-[0.18em] text-[var(--accent)]">PRJ-{String(project.id).padStart(3, '0')} · {project.progress}% hoàn thành</p><h2 className="mt-3 text-3xl font-black tracking-tight">{project.name}</h2><p className="mt-3 leading-7 text-slate-300">{project.description || 'Chưa có mô tả dự án.'}</p><p className="mt-5 text-sm text-slate-400">{project.start_date} → {project.end_date} · Chủ dự án: {project.creator.full_name}</p></div>
          <ProjectActions user={user} project={project} onEdit={() => setEditing(true)} onDelete={() => void remove()} />
        </div>
      </section>
      <MembersPanel project={project} user={user} />
      <Modal open={editing} title="Cập nhật dự án" onClose={() => setEditing(false)}>
        <ProjectForm project={project} onCancel={() => setEditing(false)} onSaved={(saved) => { setProject(saved); setEditing(false); notify('Đã cập nhật dự án.') }} />
      </Modal>
    </div>
  )
}
