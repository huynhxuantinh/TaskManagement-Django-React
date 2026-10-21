import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ToastContext } from '../../components/ui/ToastContext'
import { apiRequest } from '../../lib/api'
import type { Task } from '../../types/api'
import { TaskChecklist } from './TaskChecklist'

vi.mock('../../lib/api', () => ({ apiRequest: vi.fn() }))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

const task: Task = {
  id: 7,
  title: 'Kiểm thử',
  description: '',
  project: { id: 1, name: 'Dự án' },
  assignee: null,
  status: { code: 'IN_PROGRESS', name: 'Đang thực hiện' },
  priority: 2,
  parent_id: null,
  parent: null,
  has_subtasks: false,
  start_date: null,
  estimated_hours: '4.00',
  effective_estimated_hours: '4.00',
  progress: 0,
  effective_progress: 50,
  checklist_total: 2,
  checklist_done: 1,
  checklist: [
    { id: 1, title: 'Mục A', is_completed: true, position: 0, created_at: '' },
    { id: 2, title: 'Mục B', is_completed: false, position: 1, created_at: '' },
  ],
  deadline: null,
  is_overdue: false,
  created_at: '',
  updated_at: '',
  completed_at: null,
  allowed_transitions: [{ code: 'COMPLETED', note_required: false }],
  can_edit_checklist: true,
}

describe('TaskChecklist', () => {
  it('gửi đúng thứ tự mới khi kéo thả', async () => {
    vi.mocked(apiRequest).mockResolvedValueOnce([
      { ...task.checklist![1], position: 0 },
      { ...task.checklist![0], position: 1 },
    ])
    render(
      <ToastContext.Provider value={vi.fn()}>
        <TaskChecklist task={task} onChanged={vi.fn()} />
      </ToastContext.Provider>,
    )

    const first = screen.getByText('Mục A').closest('li')!
    const second = screen.getByText('Mục B').closest('li')!
    fireEvent.dragStart(first)
    fireEvent.dragOver(second)
    fireEvent.drop(second)

    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(
      '/api/v1/tasks/7/checklist/order/',
      { method: 'PUT', body: JSON.stringify({ item_ids: [2, 1] }) },
    ))
  })

  it('sắp xếp được bằng nút lên xuống', async () => {
    vi.mocked(apiRequest).mockResolvedValueOnce([
      { ...task.checklist![1], position: 0 },
      { ...task.checklist![0], position: 1 },
    ])
    render(
      <ToastContext.Provider value={vi.fn()}>
        <TaskChecklist task={{ ...task, allowed_transitions: [] }} onChanged={vi.fn()} />
      </ToastContext.Provider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Di chuyển Mục A xuống' }))

    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(
      '/api/v1/tasks/7/checklist/order/',
      { method: 'PUT', body: JSON.stringify({ item_ids: [2, 1] }) },
    ))
    expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục A' })).toBeEnabled()
  })

  it('chỉ cho đọc checklist khi công việc đã hoàn thành', () => {
    render(
      <ToastContext.Provider value={vi.fn()}>
        <TaskChecklist task={{ ...task, status: { code: 'COMPLETED', name: 'Đã hoàn thành' }, can_edit_checklist: false }} onChanged={vi.fn()} />
      </ToastContext.Provider>,
    )

    expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục A' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Thêm' })).not.toBeInTheDocument()
  })
})
