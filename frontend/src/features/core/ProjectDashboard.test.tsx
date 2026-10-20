import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import type { ProjectReport, Task } from '../../types/api'
import { ProjectDashboard } from './ProjectDashboard'

const report: ProjectReport = {
  project_id: 4,
  project_name: 'Tự động hóa kiểm thử',
  total_tasks: 6,
  completed_tasks: 2,
  progress: 33,
  task_distribution: [
    { code: 'COMPLETED', name: 'Đã hoàn thành', count: 2 },
    { code: 'IN_PROGRESS', name: 'Đang thực hiện', count: 1 },
    { code: 'TODO', name: 'Chưa thực hiện', count: 3 },
  ],
}

const task: Task = {
  id: 1,
  title: 'Viết kiểm thử giao diện',
  description: '',
  project: { id: 4, name: report.project_name },
  assignee: null,
  status: { code: 'TODO', name: 'Chưa thực hiện' },
  priority: 2,
  deadline: '2026-11-15',
  is_overdue: false,
  created_at: '2026-10-19T00:00:00Z',
  updated_at: '2026-10-19T00:00:00Z',
  completed_at: null,
  allowed_transitions: [],
}

afterEach(cleanup)

describe('ProjectDashboard', () => {
  it('hiển thị số liệu tổng quan và công việc dự án', () => {
    render(
      <MemoryRouter>
        <ProjectDashboard projectId={4} report={report} tasks={[task]} taskCount={1} showAllTasks loading={false} reportError="" tasksError="" />
      </MemoryRouter>,
    )

    expect(screen.getByText('Tổng quan dự án')).toBeInTheDocument()
    expect(screen.getByText('33% tiến độ')).toBeInTheDocument()
    expect(screen.getByText('Viết kiểm thử giao diện')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /xem trang công việc/i })).toHaveAttribute('href', '/tasks?project=4')
  })

  it('ghi rõ phạm vi công việc của nhân viên', () => {
    render(
      <MemoryRouter>
        <ProjectDashboard projectId={4} report={report} tasks={[]} taskCount={0} showAllTasks={false} loading={false} reportError="" tasksError="" />
      </MemoryRouter>,
    )

    expect(screen.getByText('Công việc của bạn')).toBeInTheDocument()
    expect(screen.getByText('Chỉ hiển thị công việc được giao cho bạn')).toBeInTheDocument()
    expect(screen.getByText('Chưa có công việc nào trong phạm vi của bạn.')).toBeInTheDocument()
  })
})
