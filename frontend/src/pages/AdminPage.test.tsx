import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthContext, type AuthContextValue } from '../auth/AuthContext'
import { ToastContext } from '../components/ui/ToastContext'
import { ApiError } from '../lib/api'
import type { Paginated, User } from '../types/api'
import { AdminPage } from './AdminPage'

const mocks = vi.hoisted(() => ({
  updateUser: vi.fn(),
  setData: vi.fn(),
  reload: vi.fn(),
  apiRequest: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => ({ ...await importOriginal<typeof import('../lib/api')>(), apiRequest: mocks.apiRequest }))

vi.mock('../hooks/useAllPages', () => ({
  useAllPages: () => ({
    data: {
      count: 2,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          username: 'admin',
          full_name: 'Admin',
          email: 'admin@example.com',
          role: 'ADMIN',
          avatar_url: '',
          is_active: true,
          created_at: '',
          permissions: ['ADMIN'],
        },
        {
          id: 2,
          username: 'employee',
          full_name: 'Employee One',
          email: 'employee@example.com',
          role: 'EMPLOYEE',
          avatar_url: '',
          is_active: true,
          created_at: '',
          permissions: ['EMPLOYEE'],
        },
        {
          id: 3, username: 'manager', full_name: 'Manager', email: 'manager@example.com',
          role: 'MANAGER', avatar_url: '', is_active: true, created_at: '', permissions: ['MANAGER'],
        },
      ],
    } satisfies Paginated<User>,
    setData: mocks.setData,
    loading: false,
    error: '',
    reload: mocks.reload,
  }),
}))

vi.mock('../lib/users', () => ({
  updateUser: mocks.updateUser,
}))

const auth: AuthContextValue = {
  user: {
    id: 1,
    username: 'admin',
    full_name: 'Admin',
    email: 'admin@example.com',
    role: 'ADMIN',
    avatar_url: '',
    is_active: true,
    created_at: '',
    permissions: ['ADMIN'],
  },
  status: 'authenticated',
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  updateProfile: vi.fn(),
  uploadAvatar: vi.fn(),
  changePassword: vi.fn(),
}

describe('AdminPage', () => {
  afterEach(cleanup)
  it('shows server validation errors alongside the corresponding fields', async () => {
    mocks.apiRequest.mockRejectedValueOnce(new ApiError('Dữ liệu không hợp lệ.', 400, {
      username: ['Tên đăng nhập đã tồn tại.'], email: ['Email đã tồn tại.'], password: ['Mật khẩu quá yếu.'],
    }))
    render(<AuthContext.Provider value={auth}><ToastContext.Provider value={vi.fn()}><AdminPage /></ToastContext.Provider></AuthContext.Provider>)
    fireEvent.click(screen.getByRole('button', { name: '+ Tạo tài khoản' }))
    fireEvent.change(screen.getByLabelText('Họ và tên'), { target: { value: 'Example' } })
    fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'example' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'example@example.com' } })
    fireEvent.change(screen.getByLabelText('Mật khẩu ban đầu'), { target: { value: 'Password123!' } })
    fireEvent.change(screen.getByLabelText('Xác nhận mật khẩu'), { target: { value: 'Password123!' } })
    const usernameInput = screen.getByLabelText('Tên đăng nhập')
    const emailInput = screen.getByLabelText('Email')
    const passwordInput = screen.getByLabelText('Mật khẩu ban đầu')
    fireEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }))
    await waitFor(() => expect(usernameInput).toHaveAccessibleDescription('Tên đăng nhập đã tồn tại.'))
    expect(emailInput).toHaveAccessibleDescription('Email đã tồn tại.')
    expect(passwordInput).toHaveAccessibleDescription('Mật khẩu quá yếu.')
  })
  it('clears account details and password when creation is cancelled', () => {
    render(<AuthContext.Provider value={auth}><ToastContext.Provider value={vi.fn()}><AdminPage /></ToastContext.Provider></AuthContext.Provider>)
    fireEvent.click(screen.getByRole('button', { name: '+ Tạo tài khoản' }))
    fireEvent.change(screen.getByLabelText('Họ và tên'), { target: { value: 'Example' } })
    fireEvent.change(screen.getByLabelText('Tên đăng nhập'), { target: { value: 'example' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'example@example.com' } })
    fireEvent.change(screen.getByLabelText('Vai trò'), { target: { value: 'ADMIN' } })
    fireEvent.change(screen.getByLabelText('Mật khẩu ban đầu'), { target: { value: 'Password123!' } })
    fireEvent.change(screen.getByLabelText('Xác nhận mật khẩu'), { target: { value: 'Password123!' } })
    fireEvent.click(screen.getByRole('button', { name: 'Hủy' }))
    fireEvent.click(screen.getByRole('button', { name: '+ Tạo tài khoản' }))
    for (const label of ['Họ và tên', 'Tên đăng nhập', 'Email', 'Mật khẩu ban đầu', 'Xác nhận mật khẩu']) {
      expect(screen.getByLabelText(label)).toHaveValue('')
    }
    expect(screen.getByLabelText('Vai trò')).toHaveValue('EMPLOYEE')
  })
  it('transfers projects when demoting a manager and filters recipients', async () => {
    mocks.apiRequest.mockResolvedValue({ ...auth.user, id: 3, role: 'EMPLOYEE' })
    render(<AuthContext.Provider value={auth}><ToastContext.Provider value={vi.fn()}><AdminPage /></ToastContext.Provider></AuthContext.Provider>)

    fireEvent.change(screen.getByLabelText('Vai trò Manager'), { target: { value: 'EMPLOYEE' } })
    const recipient = screen.getByLabelText('Người tiếp quản')
    expect(recipient).not.toHaveTextContent('Employee One')
    fireEvent.change(recipient, { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Xác nhận hạ quyền' }))
    await waitFor(() => expect(mocks.apiRequest).toHaveBeenCalledWith('/api/v1/users/3/role/', {
      method: 'PATCH', body: JSON.stringify({ role: 'EMPLOYEE', reassign_to_id: '1' }),
    }))
  })

  it('only offers managers and admins when deactivating a manager', () => {
    render(<AuthContext.Provider value={auth}><ToastContext.Provider value={vi.fn()}><AdminPage /></ToastContext.Provider></AuthContext.Provider>)
    fireEvent.click(screen.getAllByRole('button', { name: 'Vô hiệu hóa' })[1])
    expect(screen.getByLabelText('Người nhận')).not.toHaveTextContent('Employee One')
    expect(screen.getByLabelText('Người nhận')).toHaveTextContent('Admin')
  })

  it('lets an admin edit another account name and email', async () => {
    mocks.updateUser.mockResolvedValue({
      ...auth.user,
      id: 2,
      username: 'employee',
      full_name: 'Employee Updated',
      email: 'updated@example.com',
      role: 'EMPLOYEE',
    })

    render(
      <AuthContext.Provider value={auth}>
        <ToastContext.Provider value={vi.fn()}>
          <AdminPage />
        </ToastContext.Provider>
      </AuthContext.Provider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Sửa tài khoản Employee One' }))
    fireEvent.change(screen.getByLabelText('Họ và tên'), {
      target: { value: 'Employee Updated' },
    })
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'updated@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Lưu thay đổi' }))

    await waitFor(() => {
      expect(mocks.updateUser).toHaveBeenCalledWith(2, {
        full_name: 'Employee Updated',
        email: 'updated@example.com',
      })
    })
  })
})
