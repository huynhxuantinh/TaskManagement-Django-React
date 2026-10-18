import { useState, type FormEvent } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { useToast } from '../components/ui/ToastContext'
import { ApiError } from '../lib/api'

export function ProfilePage() {
  const { user, updateProfile } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const notify = useToast()
  if (!user) return null

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await updateProfile({ full_name: fullName.trim() })
      notify('Đã cập nhật hồ sơ.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Không thể cập nhật hồ sơ.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <section className="rounded-3xl bg-[var(--ink)] p-7 text-white">
        <div className="grid size-20 place-items-center rounded-2xl bg-[var(--accent)] text-2xl font-black text-slate-950">
          {user.full_name
            .split(' ')
            .slice(-2)
            .map((part) => part[0])
            .join('')
            .toUpperCase()}
        </div>
        <h2 className="mt-6 text-2xl font-black">{user.full_name}</h2>
        <p className="mt-1 text-slate-400">{user.email}</p>
        <div className="mt-8 border-t border-white/10 pt-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-400">
            Vai trò hiện tại
          </p>
          <strong className="mt-2 block text-[var(--accent)]">{user.role}</strong>
        </div>
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-7">
        <p className="section-kicker">Personal settings</p>
        <h2 className="section-title">Thông tin cá nhân</h2>
        <form className="mt-7 space-y-5" onSubmit={submit}>
          <Field
            label="Họ và tên"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
          />
          <Field label="Email" value={user.email} disabled hint="Email chưa thể tự thay đổi." />
          {error && <p role="alert" className="text-sm font-semibold text-red-700">{error}</p>}
          <Button disabled={saving || !fullName.trim()}>
            {saving ? 'Đang lưu…' : 'Lưu thay đổi'}
          </Button>
        </form>
      </section>
    </div>
  )
}

