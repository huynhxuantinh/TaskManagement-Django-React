import { useCallback, useEffect, useRef, useState } from 'react'

import { apiRequest } from '../lib/api'
import type { Paginated } from '../types/api'

function apiPath(value: string) {
  if (!/^https?:\/\//i.test(value)) return value
  const url = new URL(value)
  return `${url.pathname}${url.search}`
}

export function useAllPages<T>(path: string | null) {
  const [data, setData] = useState<Paginated<T> | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const loadedPath = useRef<string | null>(null)
  const reload = useCallback(() => setVersion((value) => value + 1), [])

  useEffect(() => {
    if (!path) { loadedPath.current = null; return }
    const controller = new AbortController()
    async function load() {
      const isNewPath = loadedPath.current !== path
      if (isNewPath) setData(null)
      setLoading(isNewPath)
      setError('')
      try {
        const results: T[] = []
        const visited = new Set<string>()
        let next: string | null = path
        let count = 0
        while (next && !visited.has(next)) {
          visited.add(next)
          const page: Paginated<T> = await apiRequest<Paginated<T>>(apiPath(next), {
            signal: controller.signal,
          })
          count = page.count
          results.push(...page.results)
          next = page.next
        }
        if (!controller.signal.aborted) {
          loadedPath.current = path
          setData({ count, next: null, previous: null, results })
        }
      } catch (caught) {
        if ((caught as Error).name !== 'AbortError') setError((caught as Error).message)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [path, version])

  return {
    data: path ? data : null,
    setData,
    loading: path ? loading : false,
    error: path ? error : '',
    reload,
  }
}
