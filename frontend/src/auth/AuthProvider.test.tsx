import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from './AuthProvider'
import { ProtectedRoute, RoleRoute } from './RouteGuards'

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderRoutes(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<h1>Đăng nhập</h1>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<h1>Tổng quan</h1>} />
            <Route element={<RoleRoute allowedRoles={['ADMIN']} />}>
              <Route path="/admin" element={<h1>Quản trị</h1>} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('auth session and route guards', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('redirects to login when refresh session is unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(response({ success: false, message: 'unauthorized' }, 401)),
    )

    renderRoutes('/dashboard')

    expect(await screen.findByRole('heading', { name: 'Đăng nhập' })).toBeInTheDocument()
  })

  it('restores the user and blocks a role-restricted route', async () => {
    const employee = {
      id: 3,
      full_name: 'Employee One',
      email: 'employee1@task.com',
      role: 'EMPLOYEE',
      avatar_url: '',
      is_active: true,
      created_at: '2026-10-19T00:00:00Z',
      permissions: ['EMPLOYEE'],
    }
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          response({ success: true, message: 'ok', data: { access: 'fresh' } }),
        )
        .mockResolvedValueOnce(
          response({ success: true, message: 'ok', data: employee }),
        ),
    )

    renderRoutes('/admin')

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Quản trị' })).not.toBeInTheDocument()
    })
    expect(await screen.findByText(/không có quyền truy cập/i)).toBeInTheDocument()
  })
})

