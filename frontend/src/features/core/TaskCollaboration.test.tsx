import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { apiRequest } from '../../lib/api'
import { TaskCollaboration } from './TaskCollaboration'

vi.mock('../../lib/api', () => ({ apiRequest: vi.fn(), apiDownload: vi.fn() }))
afterEach(() => { cleanup(); vi.resetAllMocks() })

it('loads comments and files, then submits a comment and an attachment', async () => {
  vi.mocked(apiRequest).mockImplementation(async (path, options) => {
    if (options?.method === 'POST' && path.endsWith('/comments/')) return { id: 1, body: 'Đã kiểm tra', author: { full_name: 'An' } }
    if (options?.method === 'POST' && path.endsWith('/attachments/')) return { id: 2, original_name: 'report.txt', size: 3 }
    return []
  })
  render(<TaskCollaboration taskId={7} />)
  fireEvent.change(await screen.findByLabelText('Bình luận mới'), { target: { value: 'Đã kiểm tra' } })
  fireEvent.click(screen.getByRole('button', { name: 'Gửi bình luận' }))
  expect(await screen.findByText('Đã kiểm tra')).toBeInTheDocument()
  const file = new File(['abc'], 'report.txt', { type: 'text/plain' })
  fireEvent.change(screen.getByLabelText('Chọn tệp (tối đa 10 MB)'), { target: { files: [file] } })
  fireEvent.click(screen.getByRole('button', { name: 'Tải tệp lên' }))
  expect(await screen.findByText(/report.txt/)).toBeInTheDocument()
  await waitFor(() => expect(vi.mocked(apiRequest).mock.calls.some(([path, options]) => path.endsWith('/attachments/') && options?.body instanceof FormData)).toBe(true))
})

it('shows a load error instead of claiming there are no comments or files', async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('Mất kết nối'))
  render(<TaskCollaboration taskId={7} />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Mất kết nối')
  expect(screen.queryByText('Chưa có bình luận.')).not.toBeInTheDocument()
  expect(screen.queryByText('Chưa có tệp đính kèm.')).not.toBeInTheDocument()
})
