import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { apiRequest } from '../lib/api'
import { useAllPages } from './useAllPages'
import { useApiResource } from './useApiResource'

vi.mock('../lib/api', () => ({ apiRequest: vi.fn() }))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

it.each(['all', 'single'])('keeps data on reload and clears it when the path changes: %s', async (kind) => {
  const first = kind === 'all' ? { count: 1, next: null, previous: null, results: [1] } : [1]
  vi.mocked(apiRequest).mockResolvedValueOnce(first).mockImplementation(() => new Promise(() => {}))
  const { result, rerender } = renderHook(
    ({ path }) => kind === 'all' ? useAllPages<number>(path) : useApiResource<number[]>(path),
    { initialProps: { path: '/first' } },
  )
  await waitFor(() => expect(result.current.data).toEqual(first))
  act(() => result.current.reload())
  expect(result.current.data).toEqual(first)
  expect(result.current.loading).toBe(false)
  rerender({ path: '/second' })
  await waitFor(() => expect(result.current.data).toBeNull())
  expect(result.current.loading).toBe(true)
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
