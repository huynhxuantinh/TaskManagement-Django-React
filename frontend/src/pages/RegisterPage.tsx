import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { ApiError } from '../lib/api'

export function RegisterPage() {
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await register(form)
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Không thể tạo tài khoản.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Thành viên mới</p>
      <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950">Tạo tài khoản</h2>
      <p className="mt-3 leading-7 text-slate-600">Tài khoản mới có vai trò Nhân viên; Quản trị viên có thể điều chỉnh sau.</p>
      <form className="mt-8 space-y-5" onSubmit={submit}>
        <Field label="Họ và tên" autoComplete="name" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} required />
        <Field label="Email" type="email" autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
        <Field label="Mật khẩu" type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} hint="Tối thiểu 8 ký tự, tránh mật khẩu phổ biến." required />
        {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
        <Button className="w-full" disabled={submitting}>{submitting ? 'Đang tạo…' : 'Tạo tài khoản'}</Button>
      </form>
      <p className="mt-7 text-center text-sm text-slate-600">Đã có tài khoản? <Link to="/login" className="font-bold text-slate-950 underline decoration-[var(--accent)] decoration-2 underline-offset-4">Đăng nhập</Link></p>
    </div>
  )
}

