import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiRequest } from '../../lib/api'
import type { Project, User } from '../../types/api'
import { ProjectForm } from './ProjectForm'

vi.mock('../../lib/api', () => ({ apiRequest: vi.fn() }))

const manager = {
  id: 3,
  full_name: 'Nguyễn Quản lý',
  email: 'manager@example.com',
  role: 'MANAGER',
  avatar_url: '',
  is_active: true,
  created_at: '',
  permissions: ['MANAGER'],
} as User

const nextManager = {
  ...manager,
  id: 4,
  full_name: 'Quản lý mới',
  email: 'next-manager@example.com',
} as User

const project = {
  id: 10,
  name: 'Dự án hiện tại',
  description: '',
  start_date: '2026-11-01',
  end_date: '2026-12-01',
  creator: manager,
  member_count: 2,
  progress: 0,
  missing_estimate_count: 0,
  created_at: '',
  updated_at: '2026-11-01T00:00:00Z',
} as Project

describe('ProjectForm', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('shows the project description limit and current length', () => {
    render(<ProjectForm onSaved={vi.fn()} onCancel={vi.fn()} />)
    const description = screen.getByLabelText('Mô tả')
    expect(description).toHaveAttribute('maxLength', '500')
    fireEvent.change(description, { target: { value: 'Mô tả' } })
    expect(description).toHaveAccessibleDescription('5/500 ký tự')
  })

  it('keeps the explicit current-user default when owner options arrive late', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ id: 1 })
    const { rerender } = render(<ProjectForm ownerOptions={[]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    rerender(<ProjectForm ownerOptions={[manager]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByLabelText('Chủ dự án')).toHaveValue('')
    expect(screen.getByLabelText('Chủ dự án')).toHaveTextContent('Tôi – Quản trị viên (mặc định)')
    fireEvent.change(screen.getByLabelText('Tên dự án'), { target: { value: 'Dự án mới' } })
    fireEvent.change(screen.getByLabelText('Ngày bắt đầu'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Ngày kết thúc'), { target: { value: '2026-12-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Tạo dự án' }))
    await waitFor(() => expect(apiRequest).toHaveBeenCalled())
    const [, options] = vi.mocked(apiRequest).mock.calls[0]
    expect(JSON.parse(options!.body as string)).not.toHaveProperty('creator_id')
  })

  it('rejects an owner removed from the options before submission', async () => {
    const { rerender } = render(<ProjectForm ownerOptions={[manager]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Tên dự án'), { target: { value: 'Dự án mới' } })
    fireEvent.change(screen.getByLabelText('Ngày bắt đầu'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Ngày kết thúc'), { target: { value: '2026-12-01' } })
    fireEvent.change(screen.getByLabelText('Chủ dự án'), { target: { value: '3' } })
    rerender(<ProjectForm ownerOptions={[nextManager]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Tạo dự án' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Vui lòng chọn chủ dự án hợp lệ')
    expect(apiRequest).not.toHaveBeenCalled()
  })

  it('shows the current owner even if absent from the options', () => {
    const admin = { ...manager, id: 1, full_name: 'Admin', role: 'ADMIN' } as User
    render(<ProjectForm project={{ ...project, creator: admin }} ownerOptions={[manager]} onSaved={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByLabelText('Chủ dự án')).toHaveValue('1')
    expect(screen.getByLabelText('Chủ dự án')).toHaveTextContent('Admin')
  })

  it('lets an admin assign a manager as project owner', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ id: 1 })
    render(<ProjectForm ownerOptions={[manager]} onSaved={vi.fn()} onCancel={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('Tên dự án'), { target: { value: 'Dự án mới' } })
    fireEvent.change(screen.getByLabelText('Ngày bắt đầu'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Ngày kết thúc'), { target: { value: '2026-12-01' } })
    fireEvent.change(screen.getByLabelText('Chủ dự án'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Tạo dự án' }))

    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('/api/v1/projects/', {
      method: 'POST',
      body: JSON.stringify({
        name: 'Dự án mới',
        description: '',
        start_date: '2026-11-01',
        end_date: '2026-12-01',
        creator_id: 3,
      }),
    }))
  })

  it('lets an admin change the owner of an existing project', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ ...project, creator: nextManager })
    render(
      <ProjectForm
        project={project}
        ownerOptions={[manager, nextManager]}
        onSaved={vi.fn()}
        onCancel={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByLabelText('Chủ dự án'), {
      target: { value: String(nextManager.id) },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))

    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(
      `/api/v1/projects/${project.id}/`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          expected_updated_at: project.updated_at,
          creator_id: nextManager.id,
        }),
      },
    ))
  })
})
