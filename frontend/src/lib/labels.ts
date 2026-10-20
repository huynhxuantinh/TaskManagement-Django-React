import type { RoleCode } from '../types/api'

export const roleLabels: Record<RoleCode, string> = {
  ADMIN: 'Quản trị viên',
  MANAGER: 'Quản lý',
  EMPLOYEE: 'Nhân viên',
}

export const notificationTypeLabels: Record<string, string> = {
  GENERAL: 'Hệ thống',
  TASK_ASSIGNED: 'Giao việc',
  STATUS_CHANGED: 'Thay đổi tiến độ',
  PROJECT_ADDED: 'Thêm vào dự án',
  DEADLINE_APPROACHING: 'Sắp đến hạn',
  DEADLINE_OVERDUE: 'Đã quá hạn',
}

export const notificationPreferenceLabels: Record<string, string> = {
  GENERAL: 'Thông báo hệ thống',
  TASK_ASSIGNED: 'Khi được giao việc',
  STATUS_CHANGED: 'Khi trạng thái thay đổi',
  PROJECT_ADDED: 'Khi được thêm vào dự án',
  DEADLINE_APPROACHING: 'Khi sắp đến hạn',
  DEADLINE_OVERDUE: 'Khi đã quá hạn',
}

export function roleLabel(role: RoleCode) {
  return roleLabels[role] ?? role
}
