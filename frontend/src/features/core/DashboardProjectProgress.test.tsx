import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

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
  created_at: '2026-10-01T00:00:00Z',
} as Project

describe('DashboardProjectProgress', () => {
  it('shows progress for each visible project', () => {
    render(
      <MemoryRouter>
        <DashboardProjectProgress projects={[project]} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Nâng cấp hệ thống')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Tiến độ Nâng cấp hệ thống' })).toHaveAttribute('aria-valuenow', '65')
  })
})
