import { useState } from 'react'

import { Button } from '../components/ui/Button'
import { StatePanel } from '../components/ui/StatePanel'
import { useToast } from '../components/ui/ToastContext'
import { NotificationCard } from '../features/support/NotificationCard'
import { useApiResource } from '../hooks/useApiResource'
import { apiRequest } from '../lib/api'
import type { Notification, Paginated } from '../types/api'

export function NotificationsPage() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const path = `/api/v1/notifications/?page_size=100${filter === 'unread' ? '&is_read=false' : ''}`
  const { data, setData, loading, error, reload } = useApiResource<Paginated<Notification>>(path)
  const notify = useToast()

  async function markRead(notification: Notification) {
    try {
      const updated = await apiRequest<Notification>(`/api/v1/notifications/${notification.id}/read/`, { method: 'PATCH' })
      setData((current) => current ? {
        ...current,
        count: filter === 'unread' ? Math.max(0, current.count - 1) : current.count,
        results: filter === 'unread' ? current.results.filter((item) => item.id !== updated.id) : current.results.map((item) => item.id === updated.id ? updated : item),
      } : current)
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  async function markAllRead() {
    try {
      const result = await apiRequest<{ updated_count: number }>('/api/v1/notifications/read-all/', { method: 'POST' })
      reload()
      notify(`Đã đánh dấu ${result.updated_count} thông báo là đã đọc.`)
    } catch (caught) {
      notify((caught as Error).message, 'error')
    }
  }

  const unreadCount = data?.results.filter((item) => !item.is_read).length ?? 0
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"><div><p className="section-kicker">Hộp thư / {data?.count ?? 0}</p><h2 className="mt-1 text-3xl font-black tracking-tight">Trung tâm thông báo</h2><p className="mt-2 text-sm text-slate-600">Thông tin giao việc, thay đổi tiến độ và hạn chót của riêng bạn.</p></div><Button variant="secondary" disabled={unreadCount === 0} onClick={() => void markAllRead()}>Đọc tất cả</Button></header>
      <div className="flex gap-2" role="group" aria-label="Lọc thông báo"><Button variant={filter === 'all' ? 'primary' : 'secondary'} onClick={() => setFilter('all')}>Tất cả</Button><Button variant={filter === 'unread' ? 'primary' : 'secondary'} onClick={() => setFilter('unread')}>Chưa đọc</Button></div>
      {error && <StatePanel eyebrow="Lỗi đồng bộ" title="Không tải được thông báo" description={error} />}
      {loading && <div className="grid gap-3 md:grid-cols-2">{[1, 2, 3, 4].map((item) => <div key={item} className="h-44 animate-pulse rounded-2xl bg-white" />)}</div>}
      {!loading && data?.results.length === 0 && <StatePanel eyebrow="Hộp thư trống" title={filter === 'unread' ? 'Không còn thông báo chưa đọc' : 'Chưa có thông báo'} description="Thông báo mới sẽ xuất hiện khi dự án hoặc công việc thay đổi." />}
      <section className="grid gap-3 md:grid-cols-2" aria-label="Danh sách thông báo">{data?.results.map((item) => <NotificationCard key={item.id} notification={item} onRead={(value) => void markRead(value)} />)}</section>
    </div>
  )
}
