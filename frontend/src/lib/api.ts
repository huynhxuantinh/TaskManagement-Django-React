import type { ApiEnvelope } from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export function apiAssetUrl(path: string) {
  if (!path || /^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

let accessToken: string | null = null
let refreshPromise: Promise<string> | null = null
let authExpiredHandler: (() => void) | null = null

export class ApiError extends Error {
  status: number
  errors: Record<string, string[] | string>

  constructor(
    message: string,
    status: number,
    errors: Record<string, string[] | string> = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
  }
}

export function setAccessToken(token: string) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

export function clearAccessToken() {
  accessToken = null
}

export function setAuthExpiredHandler(handler: (() => void) | null) {
  authExpiredHandler = handler
}

function getCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`
  return document.cookie
    .split(';')
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix))
    ?.slice(prefix.length)
}

async function parseEnvelope<T>(response: Response): Promise<ApiEnvelope<T>> {
  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | null
  if (!response.ok || !payload?.success) {
    throw new ApiError(
      payload?.message || `Yêu cầu thất bại (${response.status}).`,
      response.status,
      payload?.errors,
    )
  }
  return payload
}

export async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const headers = new Headers({ 'Content-Type': 'application/json' })
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) headers.set('X-CSRFToken', decodeURIComponent(csrfToken))
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh/`, {
      method: 'POST',
      credentials: 'include',
      headers,
    })
    const envelope = await parseEnvelope<{ access: string }>(response)
    setAccessToken(envelope.data.access)
    return envelope.data.access
  })()

  try {
    return await refreshPromise
  } catch (error) {
    clearAccessToken()
    authExpiredHandler?.()
    throw error
  } finally {
    refreshPromise = null
  }
}

interface ApiRequestOptions extends RequestInit {
  authRetry?: boolean
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { authRetry = true, ...requestOptions } = options
  const headers = new Headers(requestOptions.headers)
  const bodyIsFormData = requestOptions.body instanceof FormData
  if (requestOptions.body && !bodyIsFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const method = (requestOptions.method ?? 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) headers.set('X-CSRFToken', decodeURIComponent(csrfToken))
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    credentials: 'include',
    headers,
  })

  if (
    response.status === 401 &&
    authRetry &&
    !path.startsWith('/api/v1/auth/login') &&
    !path.startsWith('/api/v1/auth/register')
  ) {
    await refreshAccessToken()
    return apiRequest<T>(path, { ...requestOptions, authRetry: false })
  }
  if (response.status === 204) return undefined as T
  const envelope = await parseEnvelope<T>(response)
  return envelope.data
}

