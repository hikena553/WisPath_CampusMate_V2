/**
 * 教师端实时数据通道（SSE 客户端）
 *
 * 定位：这是「工作台 / 学生数据变更」的主通道，取代原先每 30 秒一次的全量轮询。
 *
 * 为什么是 SSE 而不是 WebSocket：
 * - 这里只需服务端 → 客户端的单向「某业务域变了」通知，不需要双向通信；
 * - SSE 基于普通 HTTP，天然穿透代理、浏览器原生 EventSource 自带重连、服务端实现简单；
 * - WebSocket 留给聊天这类需要双向、高频、低延迟交互的场景，按需单独建连，两者不混用。
 *
 * 更新策略（三层，保证「有变化一定显示、没变化不打扰」）：
 * 1) SSE 实时事件（主）：服务端写操作后立即推 {domains:[...]}，前端按域重拉；
 * 2) 本地事件总线：把 SSE 事件灌进 dataSync，页面复用既有的 onDataChange 订阅，
 *    同一批域在微任务里合并，一次操作只触发一次刷新，不会闪烁；
 * 3) 兜底校验轮询（从）：仅在 SSE 未连上、或标签页从后台恢复时触发一次全量校验，
 *    间隔远大于原 30 秒（默认 3 分钟），且连上后自动失效，避免「静默丢推送」。
 *
 * 移动端适配：
 * - 页面隐藏时主动断开 SSE（省电、避免后台被系统掐断后反复重连）；
 * - 回到前台立即重连并做一次校验拉取，避免休眠期间错过的事件；
 * - 重连采用指数退避，弱网下不会疯狂重试。
 */

import { onDataChange, emitDataChange, type DataDomain } from './dataSync'
import { getToken } from './token'

/** SSE 端点：走同源 /api，由 Vite 代理或 Nginx 转发到后端 */
const STREAM_PATH = '/api/realtime/stream'

/** 兜底校验间隔：SSE 在线时完全不轮询，仅在离线时按此间隔补齐 */
const FALLBACK_INTERVAL_MS = 180_000

/** 重连退避：3s 起，60s 封顶（弱网 / 服务重启期间不再疯狂重试） */
const RECONNECT_MIN_MS = 3_000
const RECONNECT_MAX_MS = 60_000

/** 连接状态：供页面显示「实时/降级」并决定是否启用兜底轮询 */
export type RealtimeStatus = 'idle' | 'connecting' | 'open' | 'closed'

type StatusListener = (status: RealtimeStatus) => void

let source: EventSource | null = null
let status: RealtimeStatus = 'idle'
let started = false
let reconnectDelay = RECONNECT_MIN_MS
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let fallbackTimer: ReturnType<typeof setInterval> | null = null

const statusListeners = new Set<StatusListener>()

function setStatus(next: RealtimeStatus) {
  if (status === next) return
  status = next
  for (const fn of Array.from(statusListeners)) {
    try { fn(next) } catch { /* 单个订阅者异常不影响连接 */ }
  }
}

/** 订阅连接状态变化；返回取消订阅函数 */
export function onRealtimeStatus(fn: StatusListener): () => void {
  statusListeners.add(fn)
  fn(status)
  return () => { statusListeners.delete(fn) }
}

/** 当前是否已建立实时通道 */
export function isRealtimeOpen(): boolean {
  return status === 'open'
}

function buildUrl(): string {
  // EventSource 无法自定义请求头，token 只能走查询参数；
  // 刷新后内存 token 为空时省略，由 httpOnly Cookie 兜底认证。
  const token = getToken()
  return token ? `${STREAM_PATH}?token=${encodeURIComponent(token)}` : STREAM_PATH
}

function clearReconnect() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
}

/** 断线指数退避重连 */
function scheduleReconnect() {
  if (!started || reconnectTimer) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connect()
  }, reconnectDelay)
  reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS)
}

function connect() {
  if (!started) return
  // 后台标签页不建连：移动端会挂起后台页面，连接只会变成僵尸
  if (typeof document !== 'undefined' && document.hidden) {
    setStatus('closed')
    return
  }
  if (source) return

  setStatus('connecting')
  let es: EventSource
  try {
    es = new EventSource(buildUrl())
  } catch {
    setStatus('closed')
    scheduleReconnect()
    return
  }
  source = es

  es.addEventListener('ready', () => {
    if (source !== es) return
    reconnectDelay = RECONNECT_MIN_MS
    setStatus('open')
    // 连上即做一次校验：断线期间可能漏过事件，这里补齐最终一致性
    emitDataChange('all', false)
    stopFallbackPolling()
  })

  es.addEventListener('change', (ev: MessageEvent) => {
    if (source !== es) return
    let domains: string[] | null = null
    try {
      const data = JSON.parse(ev.data) as { domains?: unknown }
      if (Array.isArray(data?.domains)) domains = data.domains as string[]
    } catch {
      // 负载异常：退化为全量校验，宁可多拉一次也不能漏
      emitDataChange('all', false)
      return
    }
    if (!domains || !domains.length) return
    // broadcast=false：服务端事件本身已同时推给该用户的所有标签页，再广播会来回弹跳
    emitDataChange(domains as DataDomain[], false)
  })

  es.onerror = () => {
    if (source !== es) return
    try { es.close() } catch { /* ignore */ }
    source = null
    setStatus('closed')
    // 清理 EventSource 内部状态后自行重连（浏览器原生重连不带退避，弱网下会打爆服务）
    startFallbackPolling()
    scheduleReconnect()
  }
}

function disconnect() {
  clearReconnect()
  const es = source
  source = null
  setStatus('closed')
  if (es) {
    try { es.close() } catch { /* ignore */ }
  }
}

/** 兜底校验轮询：仅在实时通道不可用时工作 */
function startFallbackPolling() {
  if (fallbackTimer) return
  fallbackTimer = setInterval(() => {
    if (isRealtimeOpen()) return
    if (typeof document !== 'undefined' && document.hidden) return
    emitDataChange('all', false)
  }, FALLBACK_INTERVAL_MS)
}

function stopFallbackPolling() {
  if (fallbackTimer) { clearInterval(fallbackTimer); fallbackTimer = null }
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    // 回到前台：立即补连并把断线期间可能的变更补拉一次
    reconnectDelay = RECONNECT_MIN_MS
    clearReconnect()
    connect()
    emitDataChange('all', false)
  } else {
    // 切到后台：断开连接，省电并避免僵尸连接；本地其他标签页仍可正常接收
    disconnect()
  }
}

/**
 * 启动实时通道（布局挂载时调用，幂等）。
 * 同一页面只建立一条 EventSource，多组件共享。
 */
export function startRealtime(): void {
  if (started) return
  started = true
  document.addEventListener('visibilitychange', onVisibilityChange)
  connect()
  // 初始阶段若连不上，兜底轮询先顶上，保证首屏数据不会一直停在缓存
  startFallbackPolling()
}

/** 停止实时通道（布局卸载 / 登出时调用） */
export function stopRealtime(): void {
  started = false
  document.removeEventListener('visibilitychange', onVisibilityChange)
  stopFallbackPolling()
  disconnect()
  setStatus('idle')
}

/**
 * 低频页面按需拉取：订阅指定业务域，返回取消订阅函数。
 * 这是页面接实时更新的推荐入口 —— 不需要自己管连接和轮询节奏。
 */
export function onRealtimeData(domains: DataDomain[] | 'all', fn: () => void): () => void {
  return onDataChange(domains, () => { fn() })
}
