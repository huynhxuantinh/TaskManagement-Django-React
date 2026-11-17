import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { ToastContext } from '../../components/ui/ToastContext'
import { apiRequest } from '../../lib/api'
import type { Task } from '../../types/api'
import { TaskDetails } from './TaskDetails'

vi.mock('../../lib/api', () => ({ apiRequest: vi.fn() }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('keeps an unfinished checklist draft when an item is checked and details reload', async () => {
  const item = { id: 4, title: 'Việc A', is_completed: false, position: 0, created_at: '' }
  const task = { id: 7, title: 'Task', description: '', start_date: null, deadline: null, effective_estimated_hours: null, parent: null, checklist: [item], checklist_done: 0, checklist_total: 1, effective_progress: 0, can_edit_checklist: true } as unknown as Task
  const checked = { ...item, is_completed: true }
  vi.mocked(apiRequest)
    .mockResolvedValueOnce(task)
    .mockResolvedValueOnce(checked)
    .mockResolvedValueOnce({ ...task, checklist: [checked], checklist_done: 1, effective_progress: 100 })
  render(<ToastContext.Provider value={vi.fn()}><TaskDetails taskId={7} onChanged={vi.fn()} /></ToastContext.Provider>)
  const input = await screen.findByLabelText('Mục mới')
  fireEvent.change(input, { target: { value: 'Mục đang nhập' } })
  fireEvent.click(screen.getByRole('checkbox', { name: 'Hoàn thành Việc A' }))
  await waitFor(() => expect(screen.getByText('1/1 mục hoàn thành')).toBeInTheDocument())
  expect(screen.getByLabelText('Mục mới')).toHaveValue('Mục đang nhập')
})
