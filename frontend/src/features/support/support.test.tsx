import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { NotificationCard } from './NotificationCard'
import { PreferenceToggle } from './PreferenceToggle'
import { ReportProgress } from './ReportProgress'
import type { Notification, NotificationPreference } from '../../types/api'

const notification: Notification = {
  id: 1,
  message: 'Bạn vừa được giao một công việc mới.',
  type: 'TASK_ASSIGNED',
  is_priority: true,
  is_read: false,
  created_at: '2026-10-19T09:00:00Z',
}

afterEach(cleanup)

describe('support workflows', () => {
  it('cho phép đánh dấu thông báo chưa đọc', () => {
    const onRead = vi.fn()
    render(<NotificationCard notification={notification} onRead={onRead} />)
    fireEvent.click(screen.getByRole('button', { name: /đánh dấu đã đọc/i }))
    expect(onRead).toHaveBeenCalledWith(notification)
  })

  it('không hiện thao tác đọc lại trên thông báo đã đọc', () => {
    render(<NotificationCard notification={{ ...notification, is_read: true }} onRead={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /đánh dấu đã đọc/i })).not.toBeInTheDocument()
  })

  it('toggle tùy chọn thông báo trả trạng thái mới', () => {
    const preference: NotificationPreference = { type: 'DEADLINE_APPROACHING', is_priority: false }
    const onChange = vi.fn()
    render(<PreferenceToggle preference={preference} onChange={onChange} />)
    fireEvent.click(screen.getByRole('switch'))
    expect(onChange).toHaveBeenCalledWith({ ...preference, is_priority: true })
  })

  it('giới hạn thanh tiến độ trong khoảng hợp lệ', () => {
    render(<ReportProgress value={140} label="Tiến độ dự án" />)
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100')
  })

  it('giới hạn tiến độ âm về 0', () => {
    render(<ReportProgress value={-5} label="Tiến độ âm" />)
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
  })

  it('hiển thị loại thông báo lạ và không gắn ưu tiên', () => {
    render(<NotificationCard notification={{ ...notification, type: 'CUSTOM', is_priority: false, is_read: true }} onRead={vi.fn()} />)
    expect(screen.getByText('CUSTOM')).toBeInTheDocument()
    expect(screen.queryByText('Ưu tiên')).not.toBeInTheDocument()
  })

  it('hỗ trợ loại preference mới và tắt trạng thái đang bật', () => {
    const onChange = vi.fn()
    render(<PreferenceToggle preference={{ type: 'CUSTOM', is_priority: true }} onChange={onChange} />)
    fireEvent.click(screen.getByRole('switch', { name: 'CUSTOM' }))
    expect(onChange).toHaveBeenCalledWith({ type: 'CUSTOM', is_priority: false })
  })
})
