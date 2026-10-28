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
} as Project

describe('ProjectForm', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

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
          name: project.name,
          description: project.description,
          start_date: project.start_date,
          end_date: project.end_date,
          creator_id: nextManager.id,
        }),
      },
    ))
  })
})
