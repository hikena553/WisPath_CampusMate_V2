/**
 * 全局未读提示（导航红点数据源）
 *
 * 汇总「单聊 + 群聊 + 站内通知」三路未读，供消息中心页内计数使用；
 * 「消息」导航红点只取单聊 + 群聊（见 msgTotal），通知在消息中心「通知」页内单独展示。
 *
 * 更新策略（双通道，保证「有新消息一定有提示」）：
 * 1) WebSocket 实时事件（new_message / new_group_message / 通知写入后）立即刷新，
 *    并把聊天事件通过 onChatEvent 广播给消息页 —— 聊天正文因此可以增量追加，不用再轮询；
 * 2) 5 秒轮询 + 标签页重新可见时刷新，兜底 WS 断开或代理不支持的情况。
 *
 * 连接管理：断线指数退避重连（3 秒起、30 秒封顶）+ 25 秒心跳，
 * 避免弱网 / 系统休眠后连接被回收就永久判死（旧实现的 onclose 只把 ws 置空，不会重连）。
 *
 * 模块级单例：布局常驻，多端（教师/学生）共用同一份计数，避免重复请求。
 */
import { ref, computed } from 'vue'
import { getUnreadSummary, clearAllUnread } from '@/api/messages'
import { markAllNotificationsRead } from '@/api/notification'
import { getToken } from '@/utils/token'

/** 聊天事件负载（服务端见 app/api/messages.py 的 send_message、app/api/groups.py 的 send_group_message） */
export interface ChatPushEvent {
  type: 'new_message' | 'new_group_message'
  id?: number
  sender_id?: number
  sender_name?: string
  content?: string
  created_at?: string
  group_id?: number
}
export type ChatEventHandler = (event: ChatPushEvent) => void

const chat = ref(0)
const group = ref(0)
const notification = ref(0)
/** 紧急未读通知数：存在时导航徽标切为强提醒（danger） */
const urgentUnread = ref(0)
const total = ref(0)
/** 论坛互动未读（评论/点赞/收藏/新粉丝）：归交流社区页的互动消息入口，不计入消息红点 */
const forum = ref(0)
/** 消息红点口径：单聊 + 群聊；站内通知只在消息中心「通知」页内单独计数，
 *  避免没有聊天消息时，仅因存在未读通知就让「消息」导航常亮红点 */
const msgTotal = computed(() => chat.value + group.value)

// 在线状态：user_id → 是否在线。由「列表接口初值 + WebSocket presence 事件」共同维护，
// 供消息页单聊绿点与群聊在线人数实时刷新。
const onlineMap = ref<Map<number, boolean>>(new Map())
// 在线状态变更计数：页面可 watch 它来重拉群列表（群在线人数需服务端聚合）
const presenceTick = ref(0)
// WebSocket 当前是否在线：消息页据此决定轮询节奏（在线 30 秒兜底，断线 6 秒补齐）
const wsConnected = ref(false)

// 聊天事件订阅者：消息页订阅后，收到推送直接增量追加到气泡列表
const chatHandlers = new Set<ChatEventHandler>()

/** 订阅聊天推送；返回取消订阅函数（页面 onBeforeUnmount 里调用） */
export function onChatEvent(handler: ChatEventHandler) {
  chatHandlers.add(handler)
  return () => { chatHandlers.delete(handler) }
}

function emitChatEvent(event: ChatPushEvent) {
  for (const handler of [...chatHandlers]) {
    try { handler(event) } catch { /* 单个订阅异常不影响未读刷新 */ }
  }
}

let timer: ReturnType<typeof setInterval> | null = null
let ws: WebSocket | null = null
let started = false
/** 重连定时器与退避间隔（毫秒） */
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectDelay = 3000
/** 心跳：服务端循环 receive_text()，25 秒一条防止中间设备按空闲断开 */
let heartbeatTimer: ReturnType<typeof setInterval> | null = null

async function refresh() {
  try {
    const s = await getUnreadSummary()
    chat.value = s.chat || 0
    group.value = s.group || 0
    notification.value = s.notification || 0
    urgentUnread.value = s.urgent_unread || 0
    total.value = s.total || 0
    forum.value = (s as any).forum || 0
  } catch {
    /* 静默失败：保留上一次计数，避免网络抖动导致红点闪没 */
  }
}

function cleanupSocket() {
  wsConnected.value = false
  if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null }
  ws = null
}

/** 断线后指数退避重连：3s → 6s → 12s → 24s → 30s 封顶 */
function scheduleReconnect() {
  if (!started || reconnectTimer) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    connectWs()
  }, reconnectDelay)
  reconnectDelay = Math.min(reconnectDelay * 2, 30000)
}

function connectWs() {
  if (ws) return
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  try {
    const token = getToken()
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    // 刷新后内存 token 为空时省略参数，由 httpOnly Cookie 兜底认证
    const tokenParam = token ? '?token=' + encodeURIComponent(token) : ''
    const socket = new WebSocket(proto + '//' + location.host + '/api/messages/ws' + tokenParam)
    ws = socket
    socket.onopen = () => {
      if (ws !== socket) return
      wsConnected.value = true
      reconnectDelay = 3000
      if (heartbeatTimer) clearInterval(heartbeatTimer)
      heartbeatTimer = setInterval(() => {
        try { socket.send('ping') } catch { /* 断线由 onclose 兜底 */ }
      }, 25000)
    }
    socket.onmessage = (e) => {
      let data: { type?: string; user_id?: number; online?: boolean; [key: string]: unknown } | null = null
      try { data = JSON.parse(e.data) } catch { /* 非法负载忽略，仍刷新未读 */ }
      // 在线状态变更：只更新在线映射，不牵动未读计数
      if (data?.type === 'presence' && typeof data.user_id === 'number') {
        applyPresence(data.user_id, !!data.online)
        return
      }
      // 聊天事件先广播给页面（同步追加，体感是「收到就上屏」），再刷新未读计数
      if (data && (data.type === 'new_message' || data.type === 'new_group_message')) {
        emitChatEvent(data as unknown as ChatPushEvent)
      }
      void refresh()
    }
    socket.onclose = (event) => {
      if (ws !== socket) return
      cleanupSocket()
      // 4001 = 服务端判定 token 无效：继续重连只会一直撞墙，交给 5s 轮询与重新登录兜底
      if (event.code === 4001) return
      scheduleReconnect()
    }
    socket.onerror = () => { /* 浏览器随后会触发 onclose，这里不重复处理 */ }
  } catch {
    cleanupSocket()
    scheduleReconnect()
  }
}

/** 应用一次在线状态变更（WebSocket 推送） */
function applyPresence(userId: number, online: boolean) {
  const next = new Map(onlineMap.value)
  next.set(userId, online)
  onlineMap.value = next
  presenceTick.value++
}

/** 用列表接口返回的在线初值回填在线映射（覆盖同一批用户的旧值） */
function syncPresence(entries: Array<{ user_id: number; online: boolean }>) {
  if (!entries.length) return
  const next = new Map(onlineMap.value)
  for (const e of entries) next.set(e.user_id, !!e.online)
  onlineMap.value = next
}

/** 指定用户当前是否在线 */
function isOnline(userId: number) {
  return onlineMap.value.get(userId) === true
}

function onVisibilityChange() {
  if (document.visibilityState !== 'visible') return
  void refresh()
  // 从后台回来立即补连一次：休眠期间连接可能已被系统回收
  if (!ws) {
    reconnectDelay = 3000
    connectWs()
  }
}

/** 布局挂载时调用（幂等，重复调用无副作用） */
function start() {
  if (started) return
  started = true
  void refresh()
  timer = setInterval(() => { void refresh() }, 5000)
  connectWs()
  document.addEventListener('visibilitychange', onVisibilityChange)
}

/** 布局卸载时调用 */
function stop() {
  started = false
  if (timer) { clearInterval(timer); timer = null }
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  document.removeEventListener('visibilitychange', onVisibilityChange)
  const socket = ws
  cleanupSocket()
  try { socket?.close() } catch { /* 忽略关闭异常 */ }
}

/**
 * 清除未读提示：单聊 + 群聊 + 站内通知一并清掉，红点即时归零。
 * 即使接口失败也先本地清零，避免用户点了没反应。
 */
async function clearAll() {
  try {
    await Promise.all([clearAllUnread(), markAllNotificationsRead()])
  } finally {
    chat.value = 0
    group.value = 0
    notification.value = 0
    urgentUnread.value = 0
    total.value = 0
    forum.value = 0
  }
}

export function useUnreadSummary() {
  return {
    chat, group, notification, urgentUnread, total, forum, msgTotal,
    refresh, start, stop, clearAll,
    onlineMap, presenceTick, isOnline, syncPresence,
    wsConnected, onChatEvent,
  }
}
