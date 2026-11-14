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
      setData(null)
      setLoading(true)
      setError('')
      try {
        const result = await apiRequest<T>(path as string, { signal: controller.signal })
        if (!controller.signal.aborted) setData(result)
      } catch (caught) {
        if ((caught as Error).name !== 'AbortError') setError((caught as Error).message)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [path, version])

  return { data: path ? data : null, setData, loading: path ? loading : false, error: path ? error : '', reload }
}
