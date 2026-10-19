import type { Project, Task, User } from '../../types/api'

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
