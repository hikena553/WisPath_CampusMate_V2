/**
 * 全局未读提示（导航红点数据源）
 *
 * 汇总「单聊 + 群聊 + 站内通知」三路未读，供各端布局常驻使用。
 * 取值口径与消息中心一致：免打扰的群不计入。
 *
 * 更新策略（双通道，保证「有新消息一定有提示」）：
 * 1) WebSocket 实时事件（new_message / new_group_message / 通知写入后）立即刷新；
 * 2) 5 秒轮询 + 标签页重新可见时刷新，兜底 WS 断开或代理不支持的情况。
 *
 * 模块级单例：布局常驻，多端（教师/学生）共用同一份计数，避免重复请求。
 */
import { ref } from 'vue'
import { getUnreadSummary, clearAllUnread } from '@/api/messages'
import { markAllNotificationsRead } from '@/api/notification'
import { getToken } from '@/utils/token'

const chat = ref(0)
const group = ref(0)
const notification = ref(0)
const total = ref(0)

let timer: ReturnType<typeof setInterval> | null = null
let ws: WebSocket | null = null
let started = false

async function refresh() {
  try {
    const s = await getUnreadSummary()
    chat.value = s.chat || 0
    group.value = s.group || 0
    notification.value = s.notification || 0
    total.value = s.total || 0
  } catch {
    /* 静默失败：保留上一次计数，避免网络抖动导致红点闪没 */
  }
}

function connectWs() {
  if (ws) return
  try {
    const token = getToken()
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    // 刷新后内存 token 为空时省略参数，由 httpOnly Cookie 兜底认证
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
    ws = new WebSocket(`${proto}//${location.host}/api/messages/ws${tokenParam}`)
    ws.onmessage = () => { void refresh() }
    ws.onclose = () => { ws = null }
    ws.onerror = () => { ws = null }
  } catch {
    ws = null
  }
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') void refresh()
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
  document.removeEventListener('visibilitychange', onVisibilityChange)
  try { ws?.close() } catch { /* 忽略关闭异常 */ }
  ws = null
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
    total.value = 0
  }
}

export function useUnreadSummary() {
  return { chat, group, notification, total, refresh, start, stop, clearAll }
}