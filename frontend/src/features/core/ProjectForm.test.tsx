import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { apiRequest } from '../../lib/api'
import type { User } from '../../types/api'
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

describe('ProjectForm', () => {
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
})
