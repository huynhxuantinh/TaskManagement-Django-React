import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProjectDetailPage } from './ProjectDetailPage'

const mocks = vi.hoisted(() => ({ retry: vi.fn(), owners: { data: null as unknown, loading: true, error: '' } }))
const project = { id: 1, name: 'Project', description: '', start_date: null, end_date: null, creator: { id: 1, full_name: 'Admin', email: 'admin@example.com' }, progress: 0, updated_at: '2026-01-01T00:00:00Z' }
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 1, role: 'ADMIN' } }) }))
vi.mock('../components/ui/ToastContext', () => ({ useToast: () => vi.fn() }))
vi.mock('../hooks/useApiResource', () => ({ useApiResource: (path: string) => ({ data: path === '/api/v1/projects/1/' ? project : null, loading: false, error: '', setData: vi.fn(), reload: vi.fn() }) }))
vi.mock('../hooks/useAllPages', () => ({ useAllPages: (path: string) => path?.includes('/users/') ? { ...mocks.owners, reload: mocks.retry } : { data: { results: [], count: 0 }, loading: false, error: '', reload: vi.fn() } }))
vi.mock('../features/core/MembersPanel', () => ({ MembersPanel: () => null }))
vi.mock('../features/core/ProjectDashboard', () => ({ ProjectDashboard: () => null }))

afterEach(() => { cleanup(); mocks.owners.loading = true; mocks.owners.error = ''; mocks.owners.data = null; vi.clearAllMocks() })

it('reports owner loading failures in the edit form and retries', () => {
  const page = () => <MemoryRouter initialEntries={['/projects/1']}><Routes><Route path="/projects/:projectId" element={<ProjectDetailPage />} /></Routes></MemoryRouter>
  const { rerender } = render(page())
  fireEvent.click(screen.getByRole('button', { name: /sửa dự án/i }))
  expect(screen.getByRole('status')).toHaveTextContent('Đang tải danh sách chủ dự án')
  mocks.owners.loading = false
  mocks.owners.error = 'Lỗi kết nối'
  rerender(page())
  expect(screen.getByRole('alert')).toHaveTextContent('Lỗi kết nối')
  fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }))
  expect(mocks.retry).toHaveBeenCalledOnce()
})
