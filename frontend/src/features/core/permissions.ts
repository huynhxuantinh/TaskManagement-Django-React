import type { Project, User } from '../../types/api'

export function canCreateProjects(user: User) {
  return user.role === 'ADMIN' || user.role === 'MANAGER'
}

export function canManageProject(user: User, project: Project) {
  return user.role === 'ADMIN' || (user.role === 'MANAGER' && project.creator.id === user.id)
}
