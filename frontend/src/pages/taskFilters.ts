export interface TaskListFilters {
  search: string
  project: string
  assignee: string
  status: string
  priority: string
  deadlineFrom: string
  deadlineTo: string
  deadlinePreset: string
  ordering: string
}

export function buildTaskListParams(filters: TaskListFilters) {
  const params = new URLSearchParams({ page_size: '100' })
  if (filters.search) params.set('search', filters.search)
  if (filters.project) params.set('project', filters.project)
  if (filters.assignee) params.set('assignee', filters.assignee)
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.deadlineFrom) params.set('deadline_from', filters.deadlineFrom)
  if (filters.deadlineTo) params.set('deadline_to', filters.deadlineTo)
  if (filters.deadlinePreset) params.set(filters.deadlinePreset, 'true')
  if (filters.ordering) params.set('ordering', filters.ordering)
  return params
}
