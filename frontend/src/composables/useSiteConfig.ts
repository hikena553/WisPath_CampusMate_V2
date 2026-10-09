/**
 * 站点配置（品牌）组合式：统一管理「管理端系统设置」中下发的展示类配置，
 * 让登录页、管理端、教师端、学生端读取同一份数据，解决「只在管理端生效」的问题。
 *
 * - 数据源：`GET /api/settings/public`（免登录白名单接口，不含任何敏感配置）
 * - 同步策略：应用启动加载一次 + 定时轮询 + 窗口重新可见时刷新，
 *   管理端保存设置后调用 `refreshSiteConfig()`，其他已打开的端口最迟一个周期内同步。
 * - 兜底策略：任何键未配置时回退内置默认值，保证各端口观感一致、不出现空白。
 */
import { computed, ref } from 'vue'
import { getPublicSettings, type PublicSettingKey } from '@/api/setting'

/** 品牌默认值：管理员未配置时的内置资源 */
export const DEFAULT_SITE_NAME = '绵小城'
export const DEFAULT_SITE_LOGO = '/images/校徽_圆形.png'
export const DEFAULT_SITE_MASCOT = '/images/mascot.png'

/** 跨端口同步轮询间隔（毫秒）：跨设备 / 跨浏览器场景下的兜底同步周期 */
const SYNC_INTERVAL_MS = 10_000

/** 同浏览器多标签即时同步通道：管理端保存后，教师端 / 学生端标签页立即刷新 */
const SYNC_CHANNEL = 'site-config-sync'

type SiteConfig = Record<PublicSettingKey, string>

const EMPTY: SiteConfig = {
  site_name: '',
  site_logo: '',
  site_mascot: '',
  site_announcement: '',
  agent_name: '',
}

const config = ref<SiteConfig>({ ...EMPTY })
const loaded = ref(false)

let inflight: Promise<void> | null = null
let syncStarted = false
let channel: BroadcastChannel | null = null

/** 同步 favicon：站点 Logo 变化时浏览器标签页图标一并更新 */
function applyFavicon() {
  const href = config.value.site_logo || DEFAULT_SITE_LOGO
  let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  if (link.getAttribute('href') !== href) link.setAttribute('href', href)
}

async function fetchSiteConfig(): Promise<void> {
  try {
    const data = await getPublicSettings()
    config.value = { ...EMPTY, ...data }
    loaded.value = true
    applyFavicon()
  } catch {
    // 网络异常 / 免登接口不可用时静默回退默认品牌，不打断页面渲染
  }
}

/** 加载站点配置（并发去重）；force=false 且已加载过则直接返回 */
export function loadSiteConfig(force = false): Promise<void> {
  if (!force && loaded.value) return Promise.resolve()
  if (inflight) return inflight
  inflight = fetchSiteConfig().finally(() => {
    inflight = null
  })
  return inflight
}

/** 通知同一浏览器的其他标签页刷新（跨标签即时同步） */
function broadcastRefresh() {
  try {
    channel?.postMessage({ type: 'refresh' })
  } catch {
    // 通道不可用时退化为轮询同步，不影响功能
  }
}

/**
 * 强制刷新站点配置：管理端保存设置、各端口进入时调用。
 * 默认同时广播给同浏览器其他标签页，实现"管理端一改，教师/学生端立刻跟着变"。
 */
export function refreshSiteConfig(options: { broadcast?: boolean } = {}): Promise<void> {
  if (options.broadcast !== false) broadcastRefresh()
  return loadSiteConfig(true)
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') void loadSiteConfig(true)
}

function onWindowFocus() {
  void loadSiteConfig(true)
}

function onChannelMessage(ev: MessageEvent) {
  if ((ev.data as { type?: string } | null)?.type === 'refresh') {
    // 接收端只刷新、不再广播，避免标签页之间来回触发
    void loadSiteConfig(true)
  }
}

/**
 * 启动跨端口同步（应用启动时调用一次）：
 * 首次加载 + 10 秒轮询兜底 + 标签页可见 / 窗口聚焦时刷新 + 同浏览器广播即时同步，
 * 因此教师端、学生端无论是否已经打开，都会在设置变更后同步到最新值。
 */
export function startSiteConfigSync(): void {
  void loadSiteConfig()
  if (syncStarted) return
  syncStarted = true
  setInterval(() => {
    void loadSiteConfig(true)
  }, SYNC_INTERVAL_MS)
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('focus', onWindowFocus)
  if (typeof BroadcastChannel !== 'undefined') {
    channel = new BroadcastChannel(SYNC_CHANNEL)
    channel.onmessage = onChannelMessage
  }
}

export function useSiteConfig() {
  return {
    /** 站点名称：导航栏品牌名 / 登录页标题 / 关于页 */
    siteName: computed(() => config.value.site_name || DEFAULT_SITE_NAME),
    /** 站点 Logo：顶栏校徽 / 关于页 / 分享页 / favicon */
    siteLogo: computed(() => config.value.site_logo || DEFAULT_SITE_LOGO),
    /** 吉祥物形象：登录页 / AI 角色 / 空态装饰 */
    siteMascot: computed(() => config.value.site_mascot || DEFAULT_SITE_MASCOT),
    /** 系统公告（未配置时为空串） */
    siteAnnouncement: computed(() => (config.value.site_announcement || '').trim()),
    /** AI 助手自我称谓 */
    agentName: computed(() => (config.value.agent_name || '').trim() || DEFAULT_SITE_NAME),
    loadSiteConfig,
    refreshSiteConfig,
  }
}