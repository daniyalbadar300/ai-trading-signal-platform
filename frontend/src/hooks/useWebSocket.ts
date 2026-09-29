import { useEffect, useRef, useState } from 'react'
import type { Signal, WsMessage } from '../types'

interface WsState {
  latest: Record<string, Signal>
  snapshotLoaded: boolean
  connected: boolean
  receivedCount: number
}

/**
 * Subscribes to /ws/signals. On (re)connect the server sends a snapshot of
 * recent signals, then one message per live generated signal. Exponential
 * backoff reconnect so transient backend restarts don't kill the UI.
 */
export function useWebSocket(): WsState {
  const [state, setState] = useState<WsState>({
    latest: {},
    snapshotLoaded: false,
    connected: false,
    receivedCount: 0,
  })
  const socketRef = useRef<WebSocket | null>(null)
  const attemptRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closedRef = useRef(false)

  useEffect(() => {
    closedRef.current = false

    const connect = () => {
      if (closedRef.current) return
      // VITE_API_BASE set → derive the WS host from it (https→wss).
      // Otherwise same-origin (vite proxy / nginx / ingress handle the upgrade).
      const apiBase = import.meta.env.VITE_API_BASE
      const proto = apiBase ? apiBase.replace(/^http/, 'ws').replace(/\/$/, '')
                           : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`
      const ws = new WebSocket(`${proto}/ws/signals`)
      socketRef.current = ws

      ws.onopen = () => {
        attemptRef.current = 0
        setState((s) => ({ ...s, connected: true }))
      }

      ws.onmessage = (event) => {
        const msg: WsMessage = JSON.parse(event.data)
        setState((s) => {
          if (msg.type === 'snapshot') {
            const latest = { ...s.latest }
            for (const sig of msg.signals) latest[sig.symbol] = sig
            return { ...s, latest, snapshotLoaded: true }
          }
          return {
            ...s,
            latest: { ...s.latest, [msg.symbol]: msg },
            receivedCount: s.receivedCount + 1,
          }
        })
      }

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }))
        // Ignore close events from stale sockets (StrictMode double-mount,
        // or a socket replaced by a newer connect attempt).
        if (closedRef.current || socketRef.current !== ws) return
        const delay = Math.min(15000, 1000 * 2 ** attemptRef.current)
        attemptRef.current += 1
        timerRef.current = setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      closedRef.current = true
      if (timerRef.current) clearTimeout(timerRef.current)
      socketRef.current?.close()
    }
  }, [])

  return state
}
