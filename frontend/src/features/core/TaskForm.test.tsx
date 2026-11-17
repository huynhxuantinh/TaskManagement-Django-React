import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Project, Task } from '../../types/api'
import { TaskForm } from './TaskForm'

const mocks = vi.hoisted(() => ({ apiRequest: vi.fn(), members: { data: { results: [] as Array<{ id: number; user: { id: number; full_name: string; is_active: boolean } }> }, loading: false, error: '', reload: vi.fn() }, tasks: { data: { results: [] as Array<{ id: number; title: string; parent_id: number | null; status: { code: string } }> }, loading: false, error: '', reload: vi.fn() } }))
vi.mock('../../lib/api', () => ({ apiRequest: mocks.apiRequest }))
vi.mock('../../hooks/useAllPages', () => ({ useAllPages: (path: string) => path.includes('/members/') ? mocks.members : mocks.tasks }))

const project = { id: 1, name: 'Project' } as Project
const task = {
  id: 2, title: 'Old task', description: '', project, assignee: { id: 3, full_name: 'Former member' },
  status: { code: 'COMPLETED' }, priority: 2, parent_id: null, checklist_total: 0,
  has_subtasks: false, progress: 100, deadline: null, start_date: null, estimated_hours: null,
  updated_at: '2026-11-16T00:00:00Z',
} as unknown as Task

describe('TaskForm assignee', () => {
  afterEach(() => { cleanup(); mocks.members.data.results = []; mocks.tasks.data.results = []; mocks.members.loading = false; mocks.members.error = ''; mocks.tasks.loading = false; mocks.tasks.error = ''; vi.clearAllMocks() })

  it('limits the description and shows its length', () => {
    render(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    const description = screen.getByLabelText('Mô tả')
    expect(description).toHaveAttribute('maxLength', '500')
    fireEvent.change(description, { target: { value: 'Nội dung' } })
    expect(description).toHaveAccessibleDescription('8/500 ký tự')
  })

  it('accepts and sends estimates with two decimal places', async () => {
    mocks.apiRequest.mockResolvedValue(task)
    render(<TaskForm task={{ ...task, estimated_hours: '0.01' }} projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    const hours = screen.getByLabelText('Giờ ước lượng') as HTMLInputElement
    expect(hours).toHaveAttribute('min', '0.01')
    expect(hours).toHaveAttribute('step', '0.01')
    expect(hours.checkValidity()).toBe(true)
    fireEvent.change(hours, { target: { value: '0.12' } })
    expect(hours.checkValidity()).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalled())
    expect(JSON.parse(mocks.apiRequest.mock.calls[0][1].body)).toMatchObject({ estimated_hours: '0.12' })
  })

  it('explains that 100% does not automatically complete the task', () => {
    render(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByText(/đạt 100% không tự chuyển sang hoàn thành/i)).toBeInTheDocument()
  })

  it('explains how choosing a parent changes its progress calculation', () => {
    mocks.tasks.data.results = [{ id: 10, title: 'Công việc cha', parent_id: null, status: { code: 'TODO' } }]
    render(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Công việc cha'), { target: { value: '10' } })
    expect(screen.getByRole('note')).toHaveTextContent('tiến độ của công việc cha được tính từ các công việc con')
  })

  it('disables inactive members as assignees', () => {
    mocks.members.data.results = [
      { id: 1, user: { id: 4, full_name: 'Đang làm', is_active: true } },
      { id: 2, user: { id: 5, full_name: 'Đã nghỉ', is_active: false } },
    ]
    render(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByRole('option', { name: 'Đang làm' })).toBeEnabled()
    expect(screen.getByRole('option', { name: 'Đã nghỉ (đã vô hiệu hóa)' })).toBeDisabled()
  })

  it('blocks submission and provides separate retry controls for failed lists', () => {
    mocks.members.loading = true
    mocks.tasks.error = 'Lỗi công việc'
    const { rerender } = render(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByText('Đang tải danh sách thành viên…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tạo công việc' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại công việc' }))
    expect(mocks.tasks.reload).toHaveBeenCalledOnce()
    mocks.members.loading = false
    mocks.members.error = 'Lỗi thành viên'
    mocks.tasks.error = ''
    rerender(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại thành viên' }))
    expect(mocks.members.reload).toHaveBeenCalledOnce()
    expect(screen.getByRole('button', { name: 'Tạo công việc' })).toBeDisabled()
    mocks.members.error = ''
    rerender(<TaskForm projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Tạo công việc' })).toBeEnabled()
  })

  it('requires and sends a reason when creating an on-hold task', async () => {
    mocks.apiRequest.mockResolvedValue(task)
    render(<TaskForm projects={[project]} statuses={[{ code: 'TODO', name: 'Chưa thực hiện' }, { code: 'ON_HOLD', name: 'Tạm dừng' }]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Tên công việc'), { target: { value: 'Task mới' } })
    fireEvent.change(screen.getByLabelText('Trạng thái'), { target: { value: 'ON_HOLD' } })
    const note = screen.getByLabelText('Lý do tạm dừng')
    expect(note).toBeRequired()
    fireEvent.change(note, { target: { value: 'Chờ duyệt' } })
    fireEvent.click(screen.getByRole('button', { name: 'Tạo công việc' }))
    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalled())
    expect(JSON.parse(mocks.apiRequest.mock.calls[0][1].body)).toMatchObject({ status: 'ON_HOLD', note: 'Chờ duyệt' })
  })

  it.each([false, true])('sends assignee only when changed: %s', async (changed) => {
    mocks.apiRequest.mockResolvedValue(task)
    render(<TaskForm task={task} projects={[project]} statuses={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByLabelText('Người thực hiện')).toHaveValue('3')
    fireEvent.change(screen.getByLabelText('Tên công việc'), { target: { value: 'Updated task' } })
    if (changed) fireEvent.change(screen.getByLabelText('Người thực hiện'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))
    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalled())
    const body = JSON.parse(mocks.apiRequest.mock.calls[0][1].body)
    expect(body.expected_updated_at).toBe(task.updated_at)
    expect(body).not.toHaveProperty('description')
    expect(body).not.toHaveProperty('deadline')
    if (changed) expect(body.assignee_id).toBeNull()
    else expect(body).not.toHaveProperty('assignee_id')
  })
})
