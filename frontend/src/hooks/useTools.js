import { useState, useEffect, useCallback } from 'react'

export function useFetch(fetchFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const run = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchFn()
      .then(res => { if (!cancelled) setData(res) })
      .catch(err => { if (!cancelled) setError(err.message || 'Something went wrong') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, deps)

  useEffect(() => {
    const cancel = run()
    return cancel
  }, [run])

  return { data, loading, error, retry: run }
}