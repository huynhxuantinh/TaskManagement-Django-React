import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { AuthContext, type AuthContextValue } from '../auth/AuthContext'
import { ToastContext } from '../components/ui/ToastContext'
import type { Paginated, User } from '../types/api'
import { AdminPage } from './AdminPage'

const mocks = vi.hoisted(() => ({
  updateUser: vi.fn(),
  setData: vi.fn(),
  reload: vi.fn(),
}))

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
