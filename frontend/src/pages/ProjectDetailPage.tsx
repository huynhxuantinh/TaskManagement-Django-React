import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { MembersPanel } from '../features/core/MembersPanel'
import { ProjectDashboard } from '../features/core/ProjectDashboard'
import { ProjectActions } from '../features/core/ProjectActions'
import { ProjectForm } from '../features/core/ProjectForm'
import { TaskForm } from '../features/core/TaskForm'
import { canManageProject } from '../features/core/permissions'
import { Modal } from '../components/ui/Modal'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { useAllPages } from '../hooks/useAllPages'
import { useApiResource } from '../hooks/useApiResource'
import { apiRequest } from '../lib/api'
import type { Project, ProjectReport, Task, TaskStatus, User } from '../types/api'

export function ProjectDetailPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const notify = useToast()
  const [editing, setEditing] = useState(false)
  const [creatingTask, setCreatingTask] = useState(false)
  const { data: project, setData: setProject, loading, error, reload: reloadProject } = useApiResource<Project>(projectId ? `/api/v1/projects/${projectId}/` : null)
  const { data: report, loading: reportLoading, error: reportError, reload: reloadReport } = useApiResource<ProjectReport>(projectId ? `/api/v1/reports/projects/${projectId}/` : null)
  const { data: tasks, loading: tasksLoading, error: tasksError, reload: reloadTasks } = useAllPages<Task>(projectId ? `/api/v1/tasks/?project=${projectId}&page_size=100&ordering=deadline` : null)
  const { data: statuses } = useApiResource<TaskStatus[]>('/api/v1/metadata/task-statuses/')
  const { data: managers } = useAllPages<User>(
    user?.role === 'ADMIN'
      ? '/api/v1/users/?role=MANAGER&is_active=true&page_size=100'
      : null,
  )

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
      <ProjectDashboard
        projectId={project.id}
        report={report}
        tasks={tasks?.results ?? []}
        taskCount={tasks?.count ?? 0}
        showAllTasks={user.role !== 'EMPLOYEE'}
        canCreateTask={canManageProject(user, project)}
        onCreateTask={() => setCreatingTask(true)}
        loading={reportLoading || tasksLoading}
        reportError={reportError}
        tasksError={tasksError}
      />
      <MembersPanel project={project} user={user} />
      <Modal open={creatingTask} title="Giao công việc mới" onClose={() => setCreatingTask(false)}>
        <TaskForm
          projects={[project]}
          statuses={statuses ?? []}
          onCancel={() => setCreatingTask(false)}
          onSaved={() => {
            setCreatingTask(false)
            reloadProject()
            reloadReport()
            reloadTasks()
            notify('Đã tạo công việc.')
          }}
        />
      </Modal>
      <Modal open={editing} title="Cập nhật dự án" onClose={() => setEditing(false)}>
        <ProjectForm project={project} ownerOptions={managers?.results ?? []} onCancel={() => setEditing(false)} onSaved={(saved) => { setProject(saved); setEditing(false); notify('Đã cập nhật dự án.') }} />
      </Modal>
    </div>
  )
}
