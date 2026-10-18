import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  apiRequest,
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from './api'

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api client', () => {
  afterEach(() => {
    clearAccessToken()
    vi.unstubAllGlobals()
  })

  it('keeps access token in memory and sends credentials', async () => {
    setAccessToken('access-one')
    const fetchMock = vi.fn().mockResolvedValue(
      response({ success: true, message: 'ok', data: { id: 1 } }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest<{ id: number }>('/api/v1/auth/me/')).resolves.toEqual({
      id: 1,
    })
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/me/'),
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({ Authorization: 'Bearer access-one' }),
      }),
    )
  })

  it('refreshes once after 401 then retries the original request', async () => {
    document.cookie = 'csrftoken=csrf-value'
    setAccessToken('expired')
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ success: false, message: 'expired' }, 401))
      .mockResolvedValueOnce(
        response({ success: true, message: 'refreshed', data: { access: 'fresh' } }),
      )
      .mockResolvedValueOnce(
        response({ success: true, message: 'ok', data: { count: 3 } }),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest<{ count: number }>('/api/v1/projects/')).resolves.toEqual({
      count: 3,
    })
    expect(getAccessToken()).toBe('fresh')
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1][1]).toEqual(
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({ 'X-CSRFToken': 'csrf-value' }),
      }),
    )
  })
})

