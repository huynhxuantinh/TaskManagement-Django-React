import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { Button } from '../components/ui/Button'
import { apiAssetUrl } from '../lib/api'
import type { RoleCode } from '../types/api'

const navigation: Array<{
  to: string
  label: string
  icon: Parameters<typeof Icon>[0]['name']
  roles?: RoleCode[]
}> = [
  { to: '/dashboard', label: 'Tổng quan', icon: 'grid' },
  { to: '/projects', label: 'Dự án', icon: 'folder' },
  { to: '/tasks', label: 'Công việc', icon: 'check' },
  { to: '/team', label: 'Đội ngũ', icon: 'users' },
  { to: '/reports', label: 'Báo cáo', icon: 'chart' },
  { to: '/notifications', label: 'Thông báo', icon: 'bell' },
]

const pageTitles: Record<string, string> = {
  '/dashboard': 'Tổng quan vận hành',
  '/projects': 'Không gian dự án',
  '/tasks': 'Luồng công việc',
  '/team': 'Đội ngũ',
  '/reports': 'Báo cáo',
  '/notifications': 'Thông báo',
  '/profile': 'Hồ sơ cá nhân',
  '/admin': 'Quản trị hệ thống',
}

function initials(name: string) {
  return name
    .split(' ')
    .slice(-2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function Sidebar({ close }: { close?: () => void }) {
  const { user, logout } = useAuth()
  if (!user) return null
  return (
    <aside className="flex h-full flex-col bg-[var(--ink)] text-white">
      <div className="border-b border-white/10 px-6 py-6">
        <NavLink to="/dashboard" onClick={close} className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-[var(--accent)] font-mono text-sm font-black text-[var(--ink)]">TM</span>
          <span>
            <strong className="block text-[15px] tracking-tight">Task Management</strong>
            <small className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-400">Internal OS</small>
          </span>
        </NavLink>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-5" aria-label="Điều hướng chính">
        {navigation
          .filter((item) => !item.roles || item.roles.includes(user.role))
          .map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={close}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${isActive ? 'bg-white text-slate-950' : 'text-slate-300 hover:bg-white/8 hover:text-white'}`
              }
            >
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
        {user.role === 'ADMIN' && (
          <NavLink
            to="/admin"
            onClick={close}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${isActive ? 'bg-white text-slate-950' : 'text-slate-300 hover:bg-white/8 hover:text-white'}`
            }
          >
            <Icon name="user" /> Quản trị
          </NavLink>
        )}
      </nav>
      <div className="border-t border-white/10 p-3">
        <NavLink to="/profile" onClick={close} className="flex items-center gap-3 rounded-xl p-3 hover:bg-white/8">
          {user.avatar_url ? (
            <img src={apiAssetUrl(user.avatar_url)} alt="" className="size-10 rounded-full object-cover" />
          ) : (
            <span className="grid size-10 place-items-center rounded-full bg-[var(--accent)] text-xs font-black text-slate-950">{initials(user.full_name)}</span>
          )}
          <span className="min-w-0 flex-1">
            <strong className="block truncate text-sm">{user.full_name}</strong>
            <small className="block truncate text-xs text-slate-400">{user.role}</small>
          </span>
        </NavLink>
        <Button variant="ghost" className="mt-1 w-full !justify-start !text-slate-300 hover:!bg-white/8 hover:!text-white" onClick={() => void logout()}>
          <Icon name="logout" /> Đăng xuất
        </Button>
      </div>
    </aside>
  )
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const { user } = useAuth()
  return (
    <div className="min-h-screen bg-[var(--canvas)]">
      <div className="fixed inset-y-0 left-0 hidden w-64 lg:block"><Sidebar /></div>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-slate-950/50" aria-label="Đóng menu" onClick={() => setMobileOpen(false)} />
          <div className="relative h-full w-72"><Sidebar close={() => setMobileOpen(false)} /></div>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-18 items-center gap-4 border-b border-slate-200/80 bg-[var(--canvas)]/90 px-4 backdrop-blur md:px-8">
          <button className="grid size-10 place-items-center rounded-xl border border-slate-300 bg-white lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Mở menu">
            <Icon name="menu" />
          </button>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">Workspace / {user?.role}</p>
            <h1 className="truncate text-lg font-extrabold tracking-tight text-slate-950">{location.pathname.startsWith('/projects/') ? 'Chi tiết dự án' : pageTitles[location.pathname] ?? 'Task Management'}</h1>
          </div>
          <NavLink to="/notifications" className="relative grid size-10 place-items-center rounded-xl border border-slate-300 bg-white text-slate-700 hover:border-slate-500" aria-label="Thông báo">
            <Icon name="bell" />
            <span className="absolute right-2 top-2 size-2 rounded-full bg-[var(--accent)] ring-2 ring-white" />
          </NavLink>
        </header>
        <main className="px-4 py-6 md:px-8 md:py-8"><Outlet /></main>
      </div>
    </div>
  )
}

