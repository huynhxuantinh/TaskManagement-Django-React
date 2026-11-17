import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import type { Project } from '../../types/api'
import { DashboardProjectProgress } from './DashboardProjectProgress'

const project = {
  id: 9,
  name: 'Nâng cấp hệ thống',
  description: '',
  start_date: '2026-10-01',
  end_date: '2026-12-31',
  creator: { id: 2, full_name: 'PM', email: 'pm@example.com', role: 'MANAGER' },
  member_count: 4,
  progress: 65,
  missing_estimate_count: 1,
  unfinished_task_count: 1,
  created_at: '2026-10-01T00:00:00Z',
} as Project

describe('DashboardProjectProgress', () => {
  afterEach(cleanup)
  it('shows progress for each visible project', () => {
    render(
      <MemoryRouter>
        <DashboardProjectProgress projects={[project]} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Nâng cấp hệ thống')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Tiến độ Nâng cấp hệ thống' })).toHaveAttribute('aria-valuenow', '65')
    expect(screen.getByText(/1 công việc tính tiến độ thiếu giờ ước lượng/)).toHaveTextContent('trọng số trung bình')
    expect(screen.getByText(/1 công việc tính tiến độ thiếu giờ ước lượng/)).toHaveTextContent('trọng số bằng nhau')
  })

  it('shows zero without suggesting estimates were substituted', () => {
    render(<MemoryRouter><DashboardProjectProgress projects={[{ ...project, missing_estimate_count: 0 }]} /></MemoryRouter>)
    expect(screen.getByText('0 công việc tính tiến độ thiếu giờ ước lượng.')).toBeInTheDocument()
    expect(screen.queryByText(/trọng số trung bình/)).not.toBeInTheDocument()
  })

  it('explains when 100 percent still has unfinished tasks', () => {
    render(<MemoryRouter><DashboardProjectProgress projects={[{ ...project, progress: 100 }]} /></MemoryRouter>)
    expect(screen.getByText(/Còn 1 công việc chưa hoàn thành/)).toHaveTextContent('làm tròn')
  })
})
