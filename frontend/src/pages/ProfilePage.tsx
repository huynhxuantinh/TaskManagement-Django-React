import { useState, type ChangeEvent, type FormEvent } from 'react'

import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { useToast } from '../components/ui/ToastContext'
import { PreferenceToggle } from '../features/support/PreferenceToggle'
import { useApiResource } from '../hooks/useApiResource'
import { apiAssetUrl, apiRequest, ApiError } from '../lib/api'
import { roleLabel } from '../lib/labels'
import type { NotificationPreference } from '../types/api'

function initials(name: string) {
  return name.split(' ').slice(-2).map((part) => part[0]).join('').toUpperCase()
}

export function ProfilePage() {
  const { user, updateProfile, uploadAvatar, changePassword } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [profileError, setProfileError] = useState('')
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const notify = useToast()
  const preferencesPath = user ? `/api/v1/users/${user.id}/preferences/` : null
  const { data: preferences, setData: setPreferences, loading: preferencesLoading } = useApiResource<NotificationPreference[]>(preferencesPath)
  if (!user) return null

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setSaving(true); setProfileError('')
    try { await updateProfile({ full_name: fullName.trim() }); notify('Đã cập nhật hồ sơ.') }
    catch (caught) { setProfileError(caught instanceof ApiError ? caught.message : 'Không thể cập nhật hồ sơ.') }
    finally { setSaving(false) }
  }

  async function selectAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    try { await uploadAvatar(file); notify('Đã cập nhật ảnh đại diện.') }
    catch (caught) { notify((caught as Error).message, 'error') }
    finally { setUploading(false); event.target.value = '' }
  }

  async function savePreferences() {
    if (!preferences) return
    try {
      const updated = await apiRequest<NotificationPreference[]>(preferencesPath!, { method: 'PUT', body: JSON.stringify(preferences) })
      setPreferences(updated); notify('Đã lưu tùy chọn thông báo.')
    } catch (caught) { notify((caught as Error).message, 'error') }
  }

  async function submitPassword(event: FormEvent) {
    event.preventDefault(); setPasswordError('')
    if (newPassword !== confirmPassword) { setPasswordError('Mật khẩu xác nhận chưa khớp.'); return }
    try { await changePassword({ current_password: currentPassword, new_password: newPassword }); notify('Đã đổi mật khẩu. Vui lòng đăng nhập lại.') }
    catch (caught) { setPasswordError((caught as Error).message) }
  }

  return (
    <div className="grid max-w-6xl gap-6 xl:grid-cols-[0.7fr_1.3fr]">
      <section className="h-fit rounded-3xl bg-[var(--ink)] p-7 text-white xl:sticky xl:top-26">
        {user.avatar_url ? <img src={apiAssetUrl(user.avatar_url)} alt={`Ảnh đại diện ${user.full_name}`} className="size-24 rounded-2xl object-cover ring-4 ring-white/10" /> : <div className="grid size-24 place-items-center rounded-2xl bg-[var(--accent)] text-2xl font-black text-slate-950">{initials(user.full_name)}</div>}
        <h2 className="mt-6 text-2xl font-black">{user.full_name}</h2><p className="mt-1 text-slate-400">{user.email}</p>
        <label className="mt-5 inline-flex min-h-11 cursor-pointer items-center rounded-xl border border-white/20 px-4 text-sm font-bold hover:bg-white/10"><input type="file" accept="image/png,image/jpeg,image/gif,image/webp" className="sr-only" onChange={(event) => void selectAvatar(event)} />{uploading ? 'Đang tải ảnh…' : 'Đổi ảnh đại diện'}</label>
        <p className="mt-2 text-xs text-slate-500">PNG, JPEG, GIF hoặc WebP · tối đa 2 MB</p>
        <div className="mt-8 border-t border-white/10 pt-5"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-400">Vai trò hiện tại</p><strong className="mt-2 block text-[var(--accent)]">{roleLabel(user.role)}</strong></div>
      </section>
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-7"><p className="section-kicker">Thiết lập cá nhân</p><h2 className="section-title">Thông tin cá nhân</h2><form className="mt-7 space-y-5" onSubmit={saveProfile}><Field label="Họ và tên" value={fullName} onChange={(event) => setFullName(event.target.value)} required /><Field label="Email" value={user.email} disabled hint="Email chỉ quản trị viên mới có thể thay đổi." />{profileError && <p role="alert" className="text-sm font-semibold text-red-700">{profileError}</p>}<Button disabled={saving || !fullName.trim()}>{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</Button></form></section>
        <section className="rounded-3xl border border-slate-200 bg-white p-7"><p className="section-kicker">Mức ưu tiên thông báo</p><h2 className="section-title">Tùy chọn thông báo</h2>{preferencesLoading ? <div className="mt-5 h-36 animate-pulse rounded-xl bg-slate-100" /> : <div className="mt-4">{preferences?.map((preference) => <PreferenceToggle key={preference.type} preference={preference} onChange={(updated) => setPreferences((current) => current?.map((item) => item.type === updated.type ? updated : item) ?? null)} />)}<Button variant="secondary" className="mt-4" onClick={() => void savePreferences()}>Lưu tùy chọn</Button></div>}</section>
        <section className="rounded-3xl border border-slate-200 bg-white p-7"><p className="section-kicker">Bảo mật</p><h2 className="section-title">Đổi mật khẩu</h2><p className="mt-2 text-sm text-slate-500">Sau khi đổi, tất cả phiên sẽ bị thu hồi và bạn cần đăng nhập lại.</p><form className="mt-6 space-y-4" onSubmit={submitPassword}><Field label="Mật khẩu hiện tại" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /><Field label="Mật khẩu mới" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} /><Field label="Xác nhận mật khẩu mới" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />{passwordError && <p role="alert" className="text-sm font-semibold text-red-700">{passwordError}</p>}<Button disabled={!currentPassword || !newPassword || !confirmPassword}>Đổi mật khẩu</Button></form></section>
      </div>
    </div>
  )
}
