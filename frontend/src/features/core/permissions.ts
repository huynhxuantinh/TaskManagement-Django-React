import type { Project, Task, User } from '../../types/api'

const nextStatuses: Record<string, string[]> = {
  TODO: ['IN_PROGRESS'],
  IN_PROGRESS: ['ON_HOLD', 'COMPLETED'],
  ON_HOLD: ['IN_PROGRESS'],
  COMPLETED: ['IN_PROGRESS'],
}

export function canCreateProjects(user: User) {
  return user.role === 'ADMIN' || user.role === 'MANAGER'
}

export function canManageProject(user: User, project: Project) {
  return user.role === 'ADMIN' || (user.role === 'MANAGER' && project.creator.id === user.id)
}

export function canChangeTaskStatus(user: User, task: Task, project?: Project) {
  return (
    user.role === 'ADMIN' ||
    task.assignee?.id === user.id ||
    (user.role === 'MANAGER' && project?.creator.id === user.id)
  )
}

export function allowedTaskStatusCodes(user: User, task: Task) {
  if (task.status.code === 'COMPLETED' && user.role !== 'ADMIN' && user.role !== 'MANAGER') return []
  return nextStatuses[task.status.code] ?? []
}
