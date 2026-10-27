import { useState, type FormEvent } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { Modal } from '../components/ui/Modal'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { useAllPages } from '../hooks/useAllPages'
import { apiRequest } from '../lib/api'
import { updateUser } from '../lib/users'
import type { RoleCode, User } from '../types/api'

const selectClass = 'min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]'

export function AdminPage() {
  const { user: currentUser } = useAuth()
  const notify = useToast()
  const [query, setQuery] = useState('')
  const [creating, setCreating] = useState(false)
  const [fullName, setFullName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<RoleCode>('EMPLOYEE')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [createError, setCreateError] = useState('')
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState<User | undefined>()
  const [editFullName, setEditFullName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editError, setEditError] = useState('')
  const [deactivating, setDeactivating] = useState<User | undefined>()
  const [replacementId, setReplacementId] = useState('')
  const { data, setData, loading, error, reload } = useAllPages<User>(
    `/api/v1/users/?page_size=100&search=${encodeURIComponent(query)}`,
  )

  function closeCreate() {
    setCreating(false)
    setCreateError('')
  }

  function openEdit(user: User) {
    setEditing(user)
    setEditFullName(user.full_name)
    setEditEmail(user.email)
    setEditError('')
  }

  function closeEdit() {
    setEditing(undefined)
    setEditError('')
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault()
    if (!editing) return
    setSaving(true)
    setEditError('')
    try {
      const updated = await updateUser(editing.id, {
        full_name: editFullName.trim(),
        email: editEmail.trim(),
      })
      setData((current) => current ? {
        ...current,
        results: current.results.map((item) => item.id === updated.id ? updated : item),
      } : current)
      closeEdit()
      notify('Đã cập nhật tài khoản.')
    } catch (caught) {
      setEditError((caught as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function createAccount(event: FormEvent) {
    event.preventDefault()
    if (password !== confirmPassword) {
      setCreateError('Mật khẩu xác nhận không khớp.')
      return
    }
    setSaving(true)
    setCreateError('')
    try {
      await apiRequest<User>('/api/v1/users/', {
        method: 'POST',
        body: JSON.stringify({
          full_name: fullName.trim(),
          username: username.trim(),
          email: email.trim(),
          role,
          password,
        }),
      })
      setFullName('')
      setUsername('')
      setEmail('')
      setRole('EMPLOYEE')
      setPassword('')
      setConfirmPassword('')
      closeCreate()
      reload()
      notify('Đã tạo tài khoản nội bộ.')
    } catch (caught) {
      setCreateError((caught as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function changeRole(user: User, nextRole: RoleCode) {
    try {
      const updated = await apiRequest<User>(`/api/v1/users/${user.id}/role/`, {
        method: 'PATCH',
        body: JSON.stringify({ role: nextRole }),
      })
      setData((current) => current ? {
        ...current,
        results: current.results.map((item) => item.id === updated.id ? updated : item),
      } : current)
      notify('Đã cập nhật vai trò.')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  async function toggleActive(user: User) {
    if (user.is_active) {
      setDeactivating(user)
      setReplacementId('')
      return
    }
    try {
      const updated = await apiRequest<User>(`/api/v1/users/${user.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: true }),
      })
      setData((current) => current ? {
        ...current,
        results: current.results.map((item) => item.id === updated.id ? updated : item),
      } : current)
      notify('Đã kích hoạt tài khoản.')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  async function deactivate() {
    if (!deactivating) return
    try {
      const body: Record<string, string | boolean> = { is_active: false }
      if (replacementId) body.reassign_to_id = replacementId
      const updated = await apiRequest<User>(`/api/v1/users/${deactivating.id}/`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      })
      setData((current) => current ? {
        ...current,
        results: current.results.map((item) => item.id === updated.id ? updated : item),
      } : current)
      setDeactivating(undefined)
      notify('Đã vô hiệu hóa tài khoản và chuyển giao công việc.')
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="section-kicker">Kiểm soát truy cập / {data?.count ?? 0}</p>
          <h2 className="mt-1 text-3xl font-black tracking-tight">Quản trị người dùng</h2>
          <p className="mt-2 text-sm text-slate-600">Tạo tài khoản nội bộ, điều chỉnh vai trò và trạng thái truy cập.</p>
        </div>
        <Button onClick={() => setCreating(true)}>+ Tạo tài khoản</Button>
      </header>

      <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-4">
        <Field label="Tìm người dùng" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tên hoặc email…" />
      </div>
      {error && <StatePanel eyebrow="Quản trị" title="Không tải được người dùng" description={error} />}
      {loading && <div className="h-64 animate-pulse rounded-2xl bg-white" />}
      <section className="grid gap-3">
        {data?.results.map((user) => {
          const isSelf = user.id === currentUser?.id
          return (
            <article key={user.id} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 md:grid-cols-[1fr_auto_auto] md:items-center">
              <div>
                <strong className="block">{user.full_name}{isSelf ? ' (Bạn)' : ''}</strong>
                <span className="text-sm text-slate-500">{user.username ? `@${user.username} · ` : ''}{user.email}</span>
              </div>
              <select aria-label={`Vai trò ${user.full_name}`} value={user.role} disabled={isSelf} onChange={(event) => void changeRole(user, event.target.value as RoleCode)} className={`${selectClass} disabled:opacity-60`}>
                <option value="ADMIN">Quản trị viên</option>
                <option value="MANAGER">Quản lý</option>
                <option value="EMPLOYEE">Nhân viên</option>
              </select>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" aria-label={`Sửa tài khoản ${user.full_name}`} onClick={() => openEdit(user)}>Sửa</Button>
                <Button variant={user.is_active ? 'ghost' : 'secondary'} disabled={isSelf} className={user.is_active ? '!text-red-700' : ''} onClick={() => void toggleActive(user)}>{user.is_active ? 'Vô hiệu hóa' : 'Kích hoạt'}</Button>
              </div>
            </article>
          )
        })}
      </section>

      <Modal open={Boolean(editing)} title="Sửa tài khoản" onClose={closeEdit}>
        <form className="space-y-4" onSubmit={saveEdit}>
          <Field label="Họ và tên" value={editFullName} onChange={(event) => setEditFullName(event.target.value)} required maxLength={100} autoFocus />
          <Field label="Email" type="email" value={editEmail} onChange={(event) => setEditEmail(event.target.value)} required maxLength={100} />
          <p className="text-xs text-slate-500">Tên đăng nhập không thể thay đổi.</p>
          {editError && <p role="alert" className="text-sm font-semibold text-red-700">{editError}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={closeEdit}>Hủy</Button>
            <Button type="submit" disabled={saving || !editFullName.trim() || !editEmail.trim()}>{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={creating} title="Tạo tài khoản nội bộ" onClose={closeCreate}>
        <form className="space-y-4" onSubmit={createAccount}>
          <Field label="Họ và tên" value={fullName} onChange={(event) => setFullName(event.target.value)} required maxLength={100} autoFocus />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tên đăng nhập" value={username} onChange={(event) => setUsername(event.target.value)} required maxLength={50} autoComplete="off" />
            <Field label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={100} autoComplete="off" />
          </div>
          <label className="block">
            <span className="mb-2 block text-sm font-bold text-slate-800">Vai trò</span>
            <select className={selectClass} value={role} onChange={(event) => setRole(event.target.value as RoleCode)}>
              <option value="EMPLOYEE">Nhân viên</option>
              <option value="MANAGER">Quản lý</option>
              <option value="ADMIN">Quản trị viên</option>
            </select>
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Mật khẩu ban đầu" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} autoComplete="new-password" />
            <Field label="Xác nhận mật khẩu" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required minLength={8} autoComplete="new-password" />
          </div>
          <p className="text-xs text-slate-500">Tối thiểu 8 ký tự và không dùng mật khẩu quá phổ biến.</p>
          {createError && <p role="alert" className="text-sm font-semibold text-red-700">{createError}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={closeCreate}>Hủy</Button>
            <Button type="submit" disabled={saving || !fullName.trim() || !username.trim() || !email.trim() || !password || !confirmPassword}>{saving ? 'Đang tạo…' : 'Tạo tài khoản'}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={Boolean(deactivating)} title="Chuyển giao công việc" onClose={() => setDeactivating(undefined)}>
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Nếu tài khoản còn công việc đang mở, phải chuyển cho một thành viên phù hợp của tất cả dự án liên quan.</p>
          <label className="block text-sm font-bold">Người nhận
            <select className={`${selectClass} mt-2`} value={replacementId} onChange={(event) => setReplacementId(event.target.value)}>
              <option value="">Không chuyển (chỉ khi không còn task mở)</option>
              {data?.results.filter((item) => item.is_active && item.id !== deactivating?.id).map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.email}</option>)}
            </select>
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeactivating(undefined)}>Hủy</Button>
            <Button onClick={() => void deactivate()}>Xác nhận vô hiệu hóa</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
