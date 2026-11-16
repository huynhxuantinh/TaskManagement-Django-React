import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import type { Project, User } from '../../types/api'
import { MembersPanel } from './MembersPanel'

vi.mock('../../hooks/useAllPages', () => ({ useAllPages: () => ({ data: { count: 2, results: [
  { id: 1, user: { id: 1, full_name: 'Active User', email: 'a@example.com', role: 'EMPLOYEE', is_active: true } },
  { id: 2, user: { id: 2, full_name: 'Inactive User', email: 'b@example.com', role: 'EMPLOYEE', is_active: false } },
] }, loading: false, error: '', reload: vi.fn() }) }))
vi.mock('../../components/ui/ToastContext', () => ({ useToast: () => vi.fn() }))

it('shows whether project members are active', () => {
  const project = { id: 1, creator: { id: 3 }, member_count: 2 } as Project
  const user = { id: 3, role: 'MANAGER' } as User
  render(<MembersPanel project={project} user={user} />)
  expect(screen.getByText('Đang hoạt động')).toBeInTheDocument()
  expect(screen.getByText('Đã vô hiệu hóa')).toBeInTheDocument()
})
