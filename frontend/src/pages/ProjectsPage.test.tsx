import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ProjectsPage } from './ProjectsPage'

const mocks = vi.hoisted(() => ({ paths: [] as string[], owners: { data: null as unknown, loading: true, error: '', reload: vi.fn() } }))
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { role: 'ADMIN' } }) }))
vi.mock('../hooks/useAllPages', () => ({
  useAllPages: (path: string) => (mocks.paths.push(path), path.includes('/users/') ? mocks.owners : {
    data: { count: 0, results: [] }, loading: false, error: '', reload: vi.fn(),
  }),
}))

afterEach(() => { cleanup(); mocks.paths.length = 0; mocks.owners.data = null; mocks.owners.loading = true; mocks.owners.error = ''; vi.clearAllMocks() })

it('sends selected sort field and direction to the project API', () => {
  render(<MemoryRouter><ProjectsPage /></MemoryRouter>)
  fireEvent.change(screen.getByLabelText('Sắp xếp theo'), { target: { value: 'name' } })
  fireEvent.change(screen.getByLabelText('Thứ tự'), { target: { value: 'asc' } })
  expect(mocks.paths.some((path) => path.includes('ordering=name'))).toBe(true)
  fireEvent.change(screen.getByLabelText('Thứ tự'), { target: { value: 'desc' } })
  expect(mocks.paths.some((path) => path.includes('ordering=-name'))).toBe(true)
})

it('blocks project creation while owners load or fail and allows retry', () => {
  const { rerender } = render(<MemoryRouter><ProjectsPage /></MemoryRouter>)
  expect(screen.getByRole('button', { name: '+ Tạo dự án' })).toBeDisabled()
  expect(screen.getByRole('status')).toHaveTextContent('Đang tải')
  mocks.owners.loading = false
  mocks.owners.error = 'Lỗi kết nối'
  rerender(<MemoryRouter><ProjectsPage /></MemoryRouter>)
  expect(screen.getByRole('button', { name: '+ Tạo dự án' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }))
  expect(mocks.owners.reload).toHaveBeenCalled()
  mocks.owners.error = ''
  mocks.owners.data = { results: [{ id: 1, full_name: 'Admin', email: 'admin@example.com', role: 'ADMIN', is_active: true }] }
  rerender(<MemoryRouter><ProjectsPage /></MemoryRouter>)
  fireEvent.click(screen.getByRole('button', { name: '+ Tạo dự án' }))
  expect(screen.getByLabelText('Chủ dự án')).toHaveValue('')
  expect(screen.getByLabelText('Chủ dự án')).toHaveTextContent('Tôi – Quản trị viên (mặc định)')
})
