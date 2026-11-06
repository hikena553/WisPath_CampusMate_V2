/**
 * 教师端数据变更广播
 *
 * 背景：教师端页面大多依赖 30 秒轮询或「重新挂载」才会重新取数，
 * 智能体（桌宠对话）在后台通过工具调用新增任务 / 学生后，页面要等下一轮
 * 轮询才更新，看起来就是「操作了但页面没同步」。
 *
 * 这里做一个极轻量的进程内事件总线：
 * - 页面按业务域订阅，数据变动时立即静默刷新；
 * - 通过 BroadcastChannel 同步到同源的其他标签页（如管理端新增学生后，
 *   教师端已打开的标签页也能立即刷新）；
 * - 同一轮事件在微任务里合并，避免一次操作触发多次重复请求。
 */

export type DataDomain =
  | 'teacher-tasks'
  | 'teacher-students'
  | 'teacher-dashboard'
  | 'teacher-care'
  | 'teacher-approval'

export const ALL_DOMAINS: DataDomain[] = [
  'teacher-tasks',
  'teacher-students',
  'teacher-dashboard',
  'teacher-care',
  'teacher-approval',
]

type Listener = (domains: ReadonlySet<DataDomain>) => void

interface Subscription {
  domains: ReadonlySet<DataDomain> | null // null = 订阅全部
  fn: Listener
}

const subscriptions = new Set<Subscription>()
let pendingDomains = new Set<DataDomain>()
let flushScheduled = false

/** 同源多标签页同步通道（部分浏览器/隐私模式下不可用，失败即降级为仅当前页） */
let channel: BroadcastChannel | null = null
let channelTried = false

function ensureChannel(): BroadcastChannel | null {
  if (channelTried) return channel
  channelTried = true
  try {
    if (typeof BroadcastChannel === 'undefined') return null
    channel = new BroadcastChannel('campus-data-sync')
    channel.onmessage = (ev: MessageEvent) => {
      const domains = ev?.data?.domains
      if (Array.isArray(domains) && domains.length) {
        // 跨标签页来的事件只在本页分发，不再二次广播，避免来回弹跳
        dispatch(domains as DataDomain[])
      }
    }
  } catch {
    channel = null
  }
  return channel
}

function dispatch(domains: DataDomain[]) {
  for (const d of domains) pendingDomains.add(d)
  if (flushScheduled) return
  flushScheduled = true
  // 微任务合并：一次操作里连续 emit 只刷一次
  Promise.resolve().then(() => {
    flushScheduled = false
    const batch = pendingDomains
    pendingDomains = new Set()
    if (!batch.size) return
    for (const sub of Array.from(subscriptions)) {
      if (!sub.domains || Array.from(batch).some((d) => sub.domains!.has(d))) {
        try {
          sub.fn(batch)
        } catch {
          /* 单个订阅者异常不影响其他页面刷新 */
        }
      }
    }
  })
}

/**
 * 订阅数据变更。
 * @param domains 关心的业务域，'all' 表示全部
 * @param fn 变更回调（同一微任务批次的域会合并后回调一次）
 * @returns 取消订阅函数，组件卸载时务必调用
 */
export function onDataChange(domains: DataDomain[] | 'all', fn: Listener): () => void {
  const sub: Subscription = {
    domains: domains === 'all' ? null : new Set(domains),
    fn,
  }
  subscriptions.add(sub)
  return () => {
    subscriptions.delete(sub)
  }
}

/**
 * 广播数据变更。
 * @param domains 发生变动的业务域，'all' 表示全部
 * @param broadcast 是否同步到其他标签页（默认 true）
 */
export function emitDataChange(domains: DataDomain[] | 'all', broadcast = true): void {
  const list = domains === 'all' ? ALL_DOMAINS.slice() : domains.slice()
  if (!list.length) return
  dispatch(list)
  if (broadcast) {
    try {
      ensureChannel()?.postMessage({ domains: list })
    } catch {
      /* ignore */
    }
  }
}

/** 智能体一轮回复结束：工具调用可能改动了任务 / 学生 / 关怀等数据，统一通知刷新 */
export function emitAgentDataChange(): void {
  emitDataChange(['teacher-tasks', 'teacher-students', 'teacher-dashboard', 'teacher-care'])
}
