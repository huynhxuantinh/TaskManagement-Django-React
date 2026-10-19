export type RoleCode = 'ADMIN' | 'MANAGER' | 'EMPLOYEE'

export interface User {
  id: number
  full_name: string
  email: string
  role: RoleCode
  avatar_url: string
  is_active: boolean
  created_at: string
  permissions: string[]
}

export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data: T
  errors?: Record<string, string[] | string>
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Project {
  id: number
  name: string
  description: string
  start_date: string
  end_date: string
  creator: User
  member_count: number
  progress: number
  created_at: string
}

export interface ProjectMember {
  id: number
  user: User
  joined_at: string
}

export interface TaskStatus {
  code: string
  name: string
}

export interface Task {
  id: number
  title: string
  description: string
  project: { id: number; name: string }
  assignee: User | null
  status: TaskStatus
  priority: number
  deadline: string | null
  is_overdue: boolean
  created_at: string
}

export interface DashboardSummary {
  project_count: number
  task_count: number
  completed_task_count: number
  overdue_task_count: number
  team_count: number
  task_distribution: Array<{ code: string; name: string; count: number }>
  recent_tasks: Array<{
    id: number
    title: string
    priority: number
    deadline: string | null
    status: { code: string; name: string }
    project: { id: number; name: string }
  }>
}

