import { Button } from '../../components/ui/Button'
import { notificationTypeLabels } from '../../lib/labels'
import type { Notification } from '../../types/api'

export function NotificationCard({ notification, onRead }: { notification: Notification; onRead: (notification: Notification) => void }) {
  return (
    <article className={`relative rounded-2xl border p-5 transition ${notification.is_read ? 'border-slate-200 bg-white' : 'border-lime-300 bg-[var(--accent-soft)]/35'}`}>
      {!notification.is_read && <span className="absolute right-4 top-4 size-2.5 rounded-full bg-lime-500" aria-label="Chưa đọc" />}
      <div className="flex flex-wrap items-center gap-2 pr-5"><span className="rounded-full bg-slate-950 px-2.5 py-1 font-mono text-[10px] font-black uppercase tracking-wider text-white">{notificationTypeLabels[notification.type] ?? notification.type}</span>{notification.is_priority && <span className="rounded-full bg-red-50 px-2.5 py-1 text-[10px] font-black uppercase text-red-700">Ưu tiên</span>}</div>
      <p className="mt-4 leading-6 text-slate-800">{notification.message}</p>
      <div className="mt-4 flex items-center justify-between gap-3"><time className="text-xs text-slate-500">{new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(notification.created_at))}</time>{!notification.is_read && <Button variant="ghost" className="!min-h-9 !px-2" onClick={() => onRead(notification)}>Đánh dấu đã đọc</Button>}</div>
    </article>
  )
}
