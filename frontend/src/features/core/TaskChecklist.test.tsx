import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  it('locks all checklist mutations while a slow update is pending', async () => {
    let resolveUpdate!: (value: unknown) => void
    vi.mocked(apiRequest).mockReturnValueOnce(new Promise((resolve) => { resolveUpdate = resolve }))
    render(<ToastContext.Provider value={vi.fn()}><TaskChecklist task={task} onChanged={vi.fn()} /></ToastContext.Provider>)
    fireEvent.change(screen.getByLabelText('Mục mới'), { target: { value: 'Mục mới' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Hoàn thành Mục B' }))
    expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục A' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Di chuyển Mục A xuống' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Sửa Mục A' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Đang lưu…' })).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Hoàn thành Mục A' }))
    expect(apiRequest).toHaveBeenCalledTimes(1)
    await act(async () => resolveUpdate({ ...task.checklist![1], is_completed: true }))
    await waitFor(() => expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục B' })).toBeEnabled())
    expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục B' })).toBeChecked()
  })

  it('restores ordering and unlocks controls after a failed slow reorder', async () => {
    let rejectUpdate!: (reason: Error) => void
    vi.mocked(apiRequest).mockReturnValueOnce(new Promise((_resolve, reject) => { rejectUpdate = reject }))
    const notify = vi.fn()
    render(<ToastContext.Provider value={notify}><TaskChecklist task={task} onChanged={vi.fn()} /></ToastContext.Provider>)
    fireEvent.click(screen.getByRole('button', { name: 'Di chuyển Mục A xuống' }))
    expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục A' })).toBeDisabled()
    await act(async () => rejectUpdate(new Error('Mạng lỗi')))
    await waitFor(() => expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục A' })).toBeEnabled())
    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual([expect.stringContaining('Mục A'), expect.stringContaining('Mục B')])
    expect(notify).toHaveBeenCalledWith('Mạng lỗi', 'error')
  })
  it('labels effective progress as task progress rather than checklist progress', () => {
    render(<ToastContext.Provider value={vi.fn()}><TaskChecklist task={{ ...task, has_subtasks: true, effective_progress: 80 }} onChanged={vi.fn()} /></ToastContext.Provider>)
    expect(screen.getByText('1/2 mục hoàn thành')).toBeInTheDocument()
    expect(screen.getByText(/Tiến độ công việc/)).toHaveTextContent('Tiến độ công việc 80%')
  })
  it('sửa nội dung và giữ trạng thái hoàn thành của mục', async () => {
    const onChanged = vi.fn()
    vi.mocked(apiRequest).mockResolvedValueOnce({ ...task.checklist![0], title: 'Mục đã sửa' })
    render(<ToastContext.Provider value={vi.fn()}><TaskChecklist task={task} onChanged={onChanged} /></ToastContext.Provider>)
    fireEvent.click(screen.getByRole('button', { name: 'Sửa Mục A' }))
    fireEvent.change(screen.getByLabelText('Nội dung mục checklist'), { target: { value: ' Mục đã sửa ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('/api/v1/tasks/7/checklist/1/', { method: 'PATCH', body: JSON.stringify({ title: 'Mục đã sửa' }) }))
    expect(screen.getByRole('checkbox', { name: 'Hoàn thành Mục đã sửa' })).toBeChecked()
    expect(onChanged).toHaveBeenCalledOnce()
  })

  it('cho phép hủy sửa và không cho sửa checklist chỉ đọc', () => {
    const { rerender } = render(<ToastContext.Provider value={vi.fn()}><TaskChecklist task={task} onChanged={vi.fn()} /></ToastContext.Provider>)
    fireEvent.click(screen.getByRole('button', { name: 'Sửa Mục A' }))
    fireEvent.change(screen.getByLabelText('Nội dung mục checklist'), { target: { value: 'Sai' } })
    fireEvent.click(screen.getByRole('button', { name: 'Hủy' }))
    expect(screen.getByText('Mục A')).toBeInTheDocument()
    expect(apiRequest).not.toHaveBeenCalled()
    rerender(<ToastContext.Provider value={vi.fn()}><TaskChecklist task={{ ...task, can_edit_checklist: false }} onChanged={vi.fn()} /></ToastContext.Provider>)
    expect(screen.queryByRole('button', { name: 'Sửa Mục A' })).not.toBeInTheDocument()
  })

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
