import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Poll an async loader on an interval; returns data, error and a manual
 * refresh. `deps` re-triggers an immediate refresh when they change
 * (e.g. the selected symbol).
 */
export function usePolling<T>(
  loader: () => Promise<T>,
  intervalMs = 10000,
  deps: readonly unknown[] = [],
) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  const refresh = useCallback(async () => {
    try {
      const result = await loaderRef.current()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  useEffect(() => {
    void refresh()
    if (intervalMs <= 0) return
    const id = setInterval(() => void refresh(), intervalMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, intervalMs, ...deps])

  return { data, error, refresh }
}
