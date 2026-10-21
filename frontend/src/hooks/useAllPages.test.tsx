import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { apiRequest } from '../lib/api'
import { useAllPages } from './useAllPages'

vi.mock('../lib/api', () => ({ apiRequest: vi.fn() }))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

it('loads every page and normalizes absolute next links', async () => {
  vi.mocked(apiRequest)
    .mockResolvedValueOnce({
      count: 3,
      next: 'http://localhost:8010/api/v1/tasks/?page=2&page_size=2',
      previous: null,
      results: [1, 2],
    })
    .mockResolvedValueOnce({
      count: 3,
      next: null,
      previous: 'http://localhost:8010/api/v1/tasks/?page_size=2',
      results: [3],
    })

  const { result } = renderHook(() => useAllPages<number>('/api/v1/tasks/?page_size=2'))

  await waitFor(() => expect(result.current.loading).toBe(false))
  expect(result.current.data?.results).toEqual([1, 2, 3])
  expect(apiRequest).toHaveBeenNthCalledWith(
    2,
    '/api/v1/tasks/?page=2&page_size=2',
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  )
})
