import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { apiRequest } from '../../lib/api'
import type { Task } from '../../types/api'
import { TaskProgressEditor } from './TaskProgressEditor'

vi.mock('../../lib/api', () => ({ apiRequest: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('updates manual progress with the version and shows success', async () => {
  const task = { id: 4, progress: 0, updated_at: '2026-11-17T00:00:00Z' } as Task
  const saved = { ...task, progress: 70, updated_at: '2026-11-17T01:00:00Z' }
  vi.mocked(apiRequest).mockResolvedValueOnce(saved)
  const onSaved = vi.fn()
  render(<TaskProgressEditor task={task} onSaved={onSaved} />)
  fireEvent.change(screen.getByLabelText('Tiến độ thủ công (%)'), { target: { value: '70' } })
  fireEvent.click(screen.getByRole('button', { name: 'Cập nhật tiến độ' }))
  await waitFor(() => expect(apiRequest).toHaveBeenCalledWith('/api/v1/tasks/4/progress/', {
    method: 'PATCH', body: JSON.stringify({ progress: 70, expected_updated_at: task.updated_at }),
  }))
  expect(onSaved).toHaveBeenCalledWith(saved)
  expect(screen.getByRole('status')).toHaveTextContent('Đã cập nhật tiến độ.')
})
