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

