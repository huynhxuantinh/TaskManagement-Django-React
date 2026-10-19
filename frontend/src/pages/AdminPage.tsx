import { useState } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { useApiResource } from '../hooks/useApiResource'
import { apiRequest } from '../lib/api'
import type { Paginated, RoleCode, User } from '../types/api'

export function AdminPage() {
  const { user: currentUser } = useAuth()
  const [query, setQuery] = useState('')
  const { data, setData, loading, error } = useApiResource<Paginated<User>>(`/api/v1/users/?page_size=100&search=${encodeURIComponent(query)}`)
  const notify = useToast()

  async function changeRole(user: User, role: RoleCode) {
    try {
      const updated = await apiRequest<User>(`/api/v1/users/${user.id}/role/`, { method: 'PATCH', body: JSON.stringify({ role }) })
      setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current)
      notify('Đã cập nhật vai trò.')
    } catch (caught) { notify((caught as Error).message, 'error') }
  }

  async function toggleActive(user: User) {
    try {
      const updated = await apiRequest<User>(`/api/v1/users/${user.id}/`, { method: 'PATCH', body: JSON.stringify({ is_active: !user.is_active }) })
      setData((current) => current ? { ...current, results: current.results.map((item) => item.id === updated.id ? updated : item) } : current)
      notify(updated.is_active ? 'Đã kích hoạt tài khoản.' : 'Đã vô hiệu hóa tài khoản.')
    } catch (caught) { notify((caught as Error).message, 'error') }
  }

  return (
    <div className="space-y-6"><header><p className="section-kicker">Access control / {data?.count ?? 0}</p><h2 className="mt-1 text-3xl font-black tracking-tight">Quản trị người dùng</h2><p className="mt-2 text-sm text-slate-600">Điều chỉnh vai trò và trạng thái tài khoản.</p></header><div className="max-w-md rounded-2xl border border-slate-200 bg-white p-4"><Field label="Tìm người dùng" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tên hoặc email…" /></div>{error && <StatePanel eyebrow="Admin" title="Không tải được người dùng" description={error} />}{loading && <div className="h-64 animate-pulse rounded-2xl bg-white" />}<section className="grid gap-3">{data?.results.map((user) => { const isSelf = user.id === currentUser?.id; return <article key={user.id} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 md:grid-cols-[1fr_auto_auto] md:items-center"><div><strong className="block">{user.full_name}{isSelf ? ' (Bạn)' : ''}</strong><span className="text-sm text-slate-500">{user.email}</span></div><select aria-label={`Vai trò ${user.full_name}`} value={user.role} disabled={isSelf} onChange={(event) => void changeRole(user, event.target.value as RoleCode)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold disabled:opacity-60"><option value="ADMIN">ADMIN</option><option value="MANAGER">MANAGER</option><option value="EMPLOYEE">EMPLOYEE</option></select><Button variant={user.is_active ? 'ghost' : 'secondary'} disabled={isSelf} className={user.is_active ? '!text-red-700' : ''} onClick={() => void toggleActive(user)}>{user.is_active ? 'Vô hiệu hóa' : 'Kích hoạt'}</Button></article> })}</section></div>
  )
}
