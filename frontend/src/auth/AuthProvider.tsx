import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import {
  apiRequest,
  clearAccessToken,
  refreshAccessToken,
  setAccessToken,
  setAuthExpiredHandler,
} from '../lib/api'
import type { User } from '../types/api'
import {
  AuthContext,
  type AuthStatus,
  type LoginInput,
  type RegisterInput,
} from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  const expireSession = useCallback(() => {
    clearAccessToken()
    setUser(null)
    setStatus('anonymous')
  }, [])

  useEffect(() => {
    setAuthExpiredHandler(expireSession)
    let active = true
    const restore = async () => {
      try {
        await refreshAccessToken()
        const restoredUser = await apiRequest<User>('/api/v1/auth/me/', {
          authRetry: false,
        })
        if (active) {
          setUser(restoredUser)
          setStatus('authenticated')
        }
      } catch {
        if (active) expireSession()
      }
    }
    void restore()
    return () => {
      active = false
      setAuthExpiredHandler(null)
    }
  }, [expireSession])

  const login = useCallback(async (input: LoginInput) => {
    const data = await apiRequest<{ access: string; user: User }>(
      '/api/v1/auth/login/',
      { method: 'POST', body: JSON.stringify(input), authRetry: false },
    )
    setAccessToken(data.access)
    setUser(data.user)
    setStatus('authenticated')
  }, [])

  const register = useCallback(
    async (input: RegisterInput) => {
      await apiRequest<User>('/api/v1/auth/register/', {
        method: 'POST',
        body: JSON.stringify(input),
        authRetry: false,
      })
      await login({ email: input.email, password: input.password })
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await apiRequest<null>('/api/v1/auth/logout/', {
        method: 'POST',
        authRetry: false,
      })
    } finally {
      expireSession()
    }
  }, [expireSession])

  const updateProfile = useCallback(
    async (input: { full_name: string }) => {
      if (!user) return
      const updated = await apiRequest<User>(`/api/v1/users/${user.id}/`, {
        method: 'PATCH',
        body: JSON.stringify(input),
      })
      setUser(updated)
    },
    [user],
  )

  const value = useMemo(
    () => ({ user, status, login, register, logout, updateProfile }),
    [user, status, login, register, logout, updateProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

