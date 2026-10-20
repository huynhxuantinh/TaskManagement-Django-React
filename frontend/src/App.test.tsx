import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import App from './App'
import { AuthProvider } from './auth/AuthProvider'
import { ToastProvider } from './components/ui/Toast'

describe('App', () => {
  it('renders the login screen when there is no session', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ success: false, message: 'unauthorized' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    render(
      <MemoryRouter initialEntries={['/login']}>
        <ToastProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: /chào mừng trở lại/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Tên đăng nhập hoặc email')).toBeInTheDocument()
    expect(screen.queryByText('Tài khoản demo')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Đăng ký' })).not.toBeInTheDocument()
  })
})
