import { useCallback, useEffect, useState } from 'react'

import { apiRequest } from '../lib/api'

export function useApiResource<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(Boolean(path))
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const reload = useCallback(() => setVersion((value) => value + 1), [])

  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError('')
      try {
        setData(await apiRequest<T>(path as string, { signal: controller.signal }))
      } catch (caught) {
        if ((caught as Error).name !== 'AbortError') setError((caught as Error).message)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [path, version])

  return { data, setData, loading, error, reload }
}
