// deps are supplied by the caller, like useEffect itself, so the linter can't verify them here.
/* oxlint-disable react-hooks/exhaustive-deps */
import { useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'loading'; data?: undefined; error?: undefined }
  | { status: 'success'; data: T; error?: undefined }
  | { status: 'error'; data?: undefined; error: string }

/** Runs `load` whenever `deps` change, cancelling the previous request so stale responses never win. */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    setState({ status: 'loading' })
    load(controller.signal)
      .then((data) => setState({ status: 'success', data }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setState({ status: 'error', error: err instanceof Error ? err.message : 'Something went wrong' })
      })
    return () => controller.abort()
  }, deps)

  return state
}
