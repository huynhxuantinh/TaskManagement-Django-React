import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Paginated, Project, Task, User } from '../types/api'
import { TasksPage } from './TasksPage'

const mocks = vi.hoisted(() => ({
  apiRequest: vi.fn(),
  reload: vi.fn(),
  setData: vi.fn(),
  notify: vi.fn(),
}))

const employee = {
  id: 3,
  full_name: 'Employee',
  email: 'employee@example.com',
  role: 'EMPLOYEE',
  avatar_url: '',
  is_active: true,
  created_at: '',
  permissions: ['EMPLOYEE'],
} satisfies User

const project = {
  id: 1,
  name: 'Project',
  description: '',
  start_date: '',
  end_date: '',
  creator: {
    id: 2,
    full_name: 'Manager',
    email: 'manager@example.com',
    role: 'MANAGER',
    avatar_url: '',
    is_active: true,
    created_at: '',
    permissions: ['MANAGER'],
  },
  member_count: 2,
  progress: 50,
  missing_estimate_count: 0,
  created_at: '',
} satisfies Project

function task(id: number, parentId: number | null): Task {
  return {
    id,
    title: parentId ? 'Child' : 'Parent',
    description: '',
    project: { id: project.id, name: project.name },
    assignee: employee,
    status: { code: 'IN_PROGRESS', name: 'In progress' },
    priority: 2,
    parent_id: parentId,
    parent: parentId ? { id: parentId, title: 'Parent' } : null,
    has_subtasks: parentId === null,
    start_date: null,
    estimated_hours: null,
    progress: 50,
    effective_progress: 50,
    effective_estimated_hours: null,
    checklist_total: 0,
    checklist_done: 0,
    deadline: null,
    is_overdue: false,
    created_at: '',
    updated_at: '',
    completed_at: null,
    allowed_transitions: [{ code: 'COMPLETED', note_required: false }],
    can_edit_checklist: true,
  }
}

const parent = task(1, null)
const child = task(2, 1)

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: employee }) }))
vi.mock('../components/ui/ToastContext', () => ({ useToast: () => mocks.notify }))
vi.mock('../hooks/useAllPages', () => ({
  useAllPages: () => ({
    data: { count: 2, next: null, previous: null, results: [parent, child] } satisfies Paginated<Task>,
    setData: mocks.setData,
    loading: false,
    error: '',
    reload: mocks.reload,
  }),
}))
vi.mock('../hooks/useApiResource', () => ({
  useApiResource: (path: string) => {
    if (path.includes('/projects/')) {
      return { data: { count: 1, next: null, previous: null, results: [project] } }
    }
    if (path.includes('task-statuses')) {
      return { data: [{ code: 'IN_PROGRESS', name: 'In progress' }, { code: 'COMPLETED', name: 'Completed' }] }
    }
    return { data: [employee] }
  },
}))
vi.mock('../lib/api', () => ({
  apiRequest: mocks.apiRequest,
  apiDownload: vi.fn(),
}))
vi.mock('../features/core/TaskStatusSelect', () => ({
  TaskStatusSelect: ({ task: row, onChange }: { task: Task; onChange: (transition: Task['allowed_transitions'][number]) => void }) => (
    <button onClick={() => onChange(row.allowed_transitions[0])}>change-{row.id}</button>
  ),
}))
vi.mock('../features/core/TaskForm', () => ({ TaskForm: () => null }))
vi.mock('../features/core/TaskDetails', () => ({ TaskDetails: () => null }))
vi.mock('../features/core/TaskHistory', () => ({ TaskHistory: () => null }))

describe('TasksPage status synchronization', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.apiRequest.mockResolvedValue({
      ...child,
      status: { code: 'COMPLETED', name: 'Completed' },
      effective_progress: 100,
    })
  })

  it('reloads the list after a child status changes', async () => {
    render(<MemoryRouter><TasksPage /></MemoryRouter>)

    fireEvent.click(screen.getByRole('button', { name: 'change-2' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cập nhật' }))

    await waitFor(() => expect(mocks.reload).toHaveBeenCalledTimes(1))
  })
})
