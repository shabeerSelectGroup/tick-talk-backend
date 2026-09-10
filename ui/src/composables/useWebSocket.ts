import { onUnmounted, ref, shallowRef } from 'vue'
import type { WsEnvelope, WsEventType } from '@/types/ws'

function resolveWsBase(): string {
  const env = import.meta.env.VITE_WS_BASE_URL
  if (env) return env.replace(/\/$/, '')
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/api/v1/ws`
  }
  return 'ws://localhost:8000/api/v1/ws'
}

export type WsMessageHandler = (message: WsEnvelope) => void

export interface UseWebSocketOptions {
  /** Extra channels to subscribe after connect */
  channels?: () => string[]
  /** Reconnect with exponential backoff (default true) */
  autoReconnect?: boolean
  maxReconnectAttempts?: number
  onMessage?: WsMessageHandler
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useWebSocket(
  primaryChannel: () => string,
  options: UseWebSocketOptions = {}
) {
  const {
    channels = () => [],
    autoReconnect = true,
    maxReconnectAttempts = 12,
    onMessage,
    onConnect,
    onDisconnect,
  } = options

  const connected = ref(false)
  const reconnecting = ref(false)
  const lastMessage = shallowRef<WsEnvelope | null>(null)
  const handlers = new Map<string, Set<WsMessageHandler>>()

  let ws: WebSocket | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempt = 0
  let intentionalClose = false

  function on(eventType: WsEventType | string, handler: WsMessageHandler) {
    if (!handlers.has(eventType)) {
      handlers.set(eventType, new Set())
    }
    handlers.get(eventType)!.add(handler)
    return () => handlers.get(eventType)?.delete(handler)
  }

  function dispatch(msg: WsEnvelope) {
    lastMessage.value = msg
    onMessage?.(msg)
    handlers.get(msg.type)?.forEach((h) => h(msg))
    handlers.get('*')?.forEach((h) => h(msg))
  }

  function send(data: object) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }

  function subscribe(extra: string[]) {
    if (extra.length) send({ type: 'subscribe', channels: extra })
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      send({ type: 'ping', timestamp: Date.now() })
    }, 25000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    if (!autoReconnect || intentionalClose || reconnectAttempt >= maxReconnectAttempts) {
      reconnecting.value = false
      return
    }
    reconnecting.value = true
    const delay = Math.min(1000 * 2 ** reconnectAttempt, 30000)
    reconnectAttempt += 1
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  function connect() {
    const ch = primaryChannel()
    if (!ch) return

    intentionalClose = false
    if (ws) {
      ws.close()
      ws = null
    }

    const url = `${resolveWsBase()}?channel=${encodeURIComponent(ch)}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      reconnecting.value = false
      reconnectAttempt = 0
      subscribe(channels())
      startHeartbeat()
      onConnect?.()
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WsEnvelope
        if (msg.type === 'ping') {
          send({ type: 'pong', timestamp: Date.now() })
          return
        }
        if (msg.type === 'pong') return
        dispatch(msg)
      } catch {
        /* ignore malformed */
      }
    }

    ws.onclose = () => {
      connected.value = false
      stopHeartbeat()
      onDisconnect?.()
      if (!intentionalClose) scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    intentionalClose = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopHeartbeat()
    ws?.close()
    ws = null
    connected.value = false
    reconnecting.value = false
  }

  onUnmounted(disconnect)

  return {
    connected,
    reconnecting,
    lastMessage,
    connect,
    disconnect,
    send,
    on,
  }
}
