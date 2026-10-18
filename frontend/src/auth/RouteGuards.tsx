import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { LoadingScreen } from '../components/ui/LoadingScreen'
import { StatePanel } from '../components/ui/StatePanel'
import type { RoleCode } from '../types/api'
import { useAuth } from './AuthContext'

export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <LoadingScreen label="Đang khôi phục phiên làm việc" />
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { status } = useAuth()
  if (status === 'loading') return <LoadingScreen label="Đang kiểm tra phiên làm việc" />
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />
  return <Outlet />
}

export function RoleRoute({ allowedRoles }: { allowedRoles: RoleCode[] }) {
  const { user } = useAuth()
  if (!user || !allowedRoles.includes(user.role)) {
    return (
      <main className="grid min-h-[70vh] place-items-center p-6">
        <StatePanel
          eyebrow="403 / Restricted"
          title="Bạn không có quyền truy cập"
          description="Khu vực này được giới hạn theo vai trò tài khoản."
        />
      </main>
    )
  }
  return <Outlet />
}

