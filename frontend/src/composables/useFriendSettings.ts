import { computed, ref } from 'vue'

import {
  getFriendSetting,
  getFriendSettings,
  updateFriendSetting,
  type FriendSetting,
  type FriendSettingPatch,
  type FriendSettingState,
} from '@/api/social'

/**
 * 好友设置的全局单例缓存。
 *
 * 一份数据三处用：个人主页「设置」页回填开关、主页封面挂「特别关心 / 亲密关系」标、
 * 消息列表给特别关心的人挂「特别」标。各自拉一次接口的话，在主页改完开关回到消息页
 * 标记还是旧的 —— 所以统一走这里：改完就写回缓存，所有读方立刻跟上。
 */
const map = ref<Record<number, FriendSetting>>({})
const loaded = ref(false)
/** 同一次会话里反复进主页不必重复拉全量；改完设置会自己写回缓存 */
let loadingPromise: Promise<void> | null = null

export function emptyFriendSetting(peerId: number): FriendSetting {
  return {
    peer_id: peerId,
    remark: '',
    care: false,
    mute: false,
    blocked: false,
    hide_peer_posts: false,
    hide_my_posts: false,
    intimacy: '',
  }
}

/** 拉全量（消息列表的「特别关心」标靠它）；同一时刻只发一次请求 */
export async function loadFriendSettings(force = false): Promise<void> {
  if (loaded.value && !force) return
  if (loadingPromise) return loadingPromise
  loadingPromise = (async () => {
    try {
      const list = await getFriendSettings()
      const next: Record<number, FriendSetting> = {}
      for (const item of list) next[item.peer_id] = item
      map.value = next
      loaded.value = true
    } catch {
      // 拉不到就按「什么都没设」渲染：设置页的开关是多步操作，不该因为一次
      // 后台请求失败把整页拦成错误态
    } finally {
      loadingPromise = null
    }
  })()
  return loadingPromise
}

/** 取某人的设置（缓存没有时给全默认，同时后台补一次全量） */
export function friendSettingOf(peerId: number): FriendSetting {
  return map.value[peerId] || emptyFriendSetting(peerId)
}

/** 主页专用：拿我 / 对方两份，顺带把「我这份」写进缓存 */
export async function fetchFriendSettingState(peerId: number): Promise<FriendSettingState> {
  const state = await getFriendSetting(peerId)
  map.value = { ...map.value, [peerId]: state.mine }
  return state
}

/** 局部保存：成功后写回缓存，返回最新的两份（服务端是唯一事实源） */
export async function saveFriendSetting(
  peerId: number,
  patch: FriendSettingPatch,
): Promise<FriendSettingState> {
  const state = await updateFriendSetting(peerId, patch)
  map.value = { ...map.value, [peerId]: state.mine }
  return state
}

/** 本地写回（用于删除好友等只改本地视图的场景，不触发请求） */
export function cacheFriendSetting(setting: FriendSetting) {
  map.value = { ...map.value, [setting.peer_id]: setting }
}

const careIds = computed(() => {
  const set = new Set<number>()
  for (const item of Object.values(map.value)) if (item.care) set.add(item.peer_id)
  return set
})

/** 亲密关系标识 → 展示文案 / 图标（后端只存 code，文案归前端） */
export const INTIMACY_OPTIONS: { code: string; label: string; icon: string; color: string }[] = [
  { code: 'bestie', label: '闺蜜', icon: '👭', color: '#f472b6' },
  { code: 'buddy', label: '基友', icon: '🤝', color: '#38bdf8' },
  { code: 'partner', label: '搭子', icon: '🍜', color: '#fbbf24' },
  { code: 'deskmate', label: '同桌', icon: '📚', color: '#a78bfa' },
]

export function intimacyMeta(code: string) {
  return INTIMACY_OPTIONS.find((o) => o.code === code) || null
}

export function useFriendSettings() {
  return {
    settingsMap: map,
    careIds,
    isCared: (id?: number | null) => !!id && careIds.value.has(id),
    loadFriendSettings,
    friendSettingOf,
  }
}
