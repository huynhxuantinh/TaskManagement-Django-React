import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Project, Task } from '../../types/api'
import { TaskForm } from './TaskForm'

const mocks = vi.hoisted(() => ({ apiRequest: vi.fn() }))
vi.mock('../../lib/api', () => ({ apiRequest: mocks.apiRequest }))
vi.mock('../../hooks/useAllPages', () => ({ useAllPages: () => ({ data: { results: [] } }) }))

const project = { id: 1, name: 'Project' } as Project
const task = {
  id: 2, title: 'Old task', description: '', project, assignee: { id: 3, full_name: 'Former member' },
  status: { code: 'COMPLETED' }, priority: 2, parent_id: null, checklist_total: 0,
  has_subtasks: false, progress: 100, deadline: null, start_date: null, estimated_hours: null,
} as unknown as Task

describe('TaskForm assignee', () => {
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it.each([false, true])('sends assignee only when changed: %s', async (changed) => {
    mocks.apiRequest.mockResolvedValue(task)
    render(<TaskForm task={task} projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByLabelText('Người thực hiện')).toHaveValue('3')
    fireEvent.change(screen.getByLabelText('Tên công việc'), { target: { value: 'Updated task' } })
    if (changed) fireEvent.change(screen.getByLabelText('Người thực hiện'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalled())
    const body = JSON.parse(mocks.apiRequest.mock.calls[0][1].body)
    if (changed) expect(body.assignee_id).toBeNull()
    else expect(body).not.toHaveProperty('assignee_id')
  })
})
