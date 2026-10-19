import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProjectActions } from './ProjectActions'
import { TaskStatusSelect } from './TaskStatusSelect'
import { canChangeTaskStatus, canCreateProjects, canManageProject } from './permissions'
import type { Project, Task, TaskStatus, User } from '../../types/api'

const user = (role: User['role'], id = 1): User => ({
  id,
  full_name: 'Test User',
  email: 'test@example.com',
  role,
  avatar_url: '',
  is_active: true,
  created_at: '',
  permissions: [],
})

const project: Project = {
  id: 9,
  name: 'Nền tảng nội bộ',
  description: '',
  start_date: '2026-10-01',
  end_date: '2026-11-01',
  creator: user('MANAGER', 2),
  member_count: 3,
  progress: 40,
  created_at: '',
}

const statuses: TaskStatus[] = [
  { code: 'TODO', name: 'Cần làm' },
  { code: 'COMPLETED', name: 'Hoàn thành' },
]

const task: Task = {
  id: 7,
  title: 'Tích hợp API',
  description: '',
  project: { id: project.id, name: project.name },
  assignee: user('EMPLOYEE', 3),
  status: statuses[0],
  priority: 2,
  deadline: null,
  is_overdue: false,
  created_at: '',
}

afterEach(cleanup)

describe('core workflow permissions', () => {
  it('chỉ Admin và Manager được tạo dự án', () => {
    expect(canCreateProjects(user('ADMIN'))).toBe(true)
    expect(canCreateProjects(user('MANAGER'))).toBe(true)
    expect(canCreateProjects(user('EMPLOYEE'))).toBe(false)
  })

  it('Manager chỉ quản lý dự án mình tạo', () => {
    expect(canManageProject(user('ADMIN'), project)).toBe(true)
    expect(canManageProject(user('MANAGER', 2), project)).toBe(true)
    expect(canManageProject(user('MANAGER', 4), project)).toBe(false)
  })

  it('ẩn hành động sửa và xóa với thành viên thường', () => {
    render(<ProjectActions user={user('EMPLOYEE', 3)} project={project} onEdit={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /sửa dự án/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /xóa dự án/i })).not.toBeInTheDocument()
  })

  it('cho người được phân công cập nhật trạng thái task', () => {
    const onChange = vi.fn()
    render(<TaskStatusSelect task={task} statuses={statuses} canChange onChange={onChange} />)
    fireEvent.change(screen.getByLabelText(/trạng thái tích hợp api/i), {
      target: { value: 'COMPLETED' },
    })
    expect(onChange).toHaveBeenCalledWith('COMPLETED')
  })

  it('xác định đầy đủ quyền cập nhật trạng thái task', () => {
    expect(canChangeTaskStatus(user('ADMIN'), task, project)).toBe(true)
    expect(canChangeTaskStatus(user('EMPLOYEE', 3), task, project)).toBe(true)
    expect(canChangeTaskStatus(user('MANAGER', 2), { ...task, assignee: null }, project)).toBe(true)
    expect(canChangeTaskStatus(user('MANAGER', 8), { ...task, assignee: null }, project)).toBe(false)
    expect(canChangeTaskStatus(user('EMPLOYEE', 8), { ...task, assignee: null })).toBe(false)
    expect(canManageProject(user('EMPLOYEE', 2), project)).toBe(false)
  })

  it('hiện trạng thái dạng nhãn khi không có quyền thay đổi', () => {
    render(<TaskStatusSelect task={task} statuses={statuses} canChange={false} onChange={vi.fn()} />)
    expect(screen.getByText('Cần làm')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })
})
