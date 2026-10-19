import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { ApiError } from '../lib/api'

export function LoginPage() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await login({ email: identifier, password })
      const from = (location.state as { from?: string } | null)?.from
      navigate(from || '/dashboard', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Không thể kết nối máy chủ.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Không gian bảo mật</p>
      <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950">Chào mừng trở lại</h2>
      <p className="mt-3 leading-7 text-slate-600">Đăng nhập để tiếp tục theo dõi dự án và công việc của bạn.</p>
      <form className="mt-8 space-y-5" onSubmit={submit}>
        <Field label="Tên đăng nhập hoặc email" autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="Nhập tên đăng nhập" required />
        <Field label="Mật khẩu" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" required />
        {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
        <Button className="w-full" disabled={submitting}>{submitting ? 'Đang xác thực…' : 'Đăng nhập'}</Button>
      </form>
      <p className="mt-7 text-center text-sm text-slate-600">Chưa có tài khoản? <Link to="/register" className="font-bold text-slate-950 underline decoration-[var(--accent)] decoration-2 underline-offset-4">Đăng ký</Link></p>
    </div>
  )
}

