import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import type { Task } from '../../types/api'
import { TaskHistory } from './TaskHistory'

vi.mock('../../hooks/useAllPages', () => ({ useAllPages: () => ({
  loading: false, error: '', data: { results: [{
    id: 1, action: 'STATUS_CHANGED', actor: { full_name: 'Nhân viên' }, created_at: '2026-11-17T00:00:00Z',
    changes: { status: { old: 'TODO', new: 'COMPLETED' }, priority: { old: 1, new: 3 }, checklist_incomplete_confirmed: { old: null, new: true }, checklist_unfinished_count: { old: null, new: 3 } },
  }, {
    id: 2, action: 'CHECKLIST_REORDERED', actor: null, created_at: '2026-11-17T00:00:00Z',
    changes: { order: { old: [5, 6], new: [6, 5] }, order_titles: { '5': 'Phân tích', '6': 'Kiểm thử' } },
  }, {
    id: 3, action: 'CHECKLIST_REORDERED', actor: null, created_at: '2026-11-17T00:00:00Z',
    changes: { order: { old: [9], new: [9] } },
  }] },
}) }))

it('shows checklist confirmation and incomplete count in task history', () => {
  render(<TaskHistory task={{ id: 1 } as Task} />)
  expect(screen.getByText('Đã xác nhận hoàn thành khi checklist chưa xong:')).toBeInTheDocument()
  expect(screen.getByText('Số mục checklist chưa hoàn thành:')).toBeInTheDocument()
  expect(screen.getByText('3')).toBeInTheDocument()
  expect(screen.getByText('Chưa thực hiện')).toBeInTheDocument()
  expect(screen.getByText('Đã hoàn thành')).toBeInTheDocument()
  expect(screen.getByText('Thấp')).toBeInTheDocument()
  expect(screen.getByText('Cao')).toBeInTheDocument()
  expect(screen.getByText('Phân tích → Kiểm thử')).toBeInTheDocument()
  expect(screen.getByText('Kiểm thử → Phân tích')).toBeInTheDocument()
  expect(screen.getAllByText('Mục #9 (không lưu tên)')).toHaveLength(2)
})
