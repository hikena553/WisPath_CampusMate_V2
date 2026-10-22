import { computed, ref } from 'vue'

import { markBadgesSeen, syncBadges, type BadgeItem } from '@/api/badge'

/**
 * 勋章奖励动画队列（全局单例）。
 *
 * 后端 ``/badges/sync`` 是幂等的结算接口：它既返回本次新解锁的勋章，也带回历史上
 * 「还没播放过动画」的勋章，因此在布局挂载时调用一次即可补播离线期间获得的勋章。
 * 队列播完后再调 ``/badges/seen`` 清空待播，避免下次重复播。
 */
const queue = ref<BadgeItem[]>([])
const syncing = ref(false)
let inflight: Promise<void> | null = null

export const currentAward = computed<BadgeItem | null>(() => queue.value[0] ?? null)
export const awardRemaining = computed(() => Math.max(queue.value.length - 1, 0))

/**
 * 结算勋章并把新获得的推入播放队列。
 * 并发调用（布局层定时结算 + 个人中心挂载结算）复用同一个在途请求，
 * 保证 await 之后拿到的都是「已经结算完」的状态。
 */
export function syncBadgeAwards(): Promise<void> {
  if (inflight) return inflight
  syncing.value = true
  inflight = (async () => {
    try {
      const res = await syncBadges()
      const items = res?.new || []
      if (items.length) queue.value.push(...items)
    } catch {
      /* 结算失败不打扰用户，下次进入再补 */
    } finally {
      syncing.value = false
      inflight = null
    }
  })()
  return inflight
}

/** 动画播放完毕 / 用户跳过：出队；队列清空后回写已读 */
export async function consumeAward() {
  queue.value.shift()
  if (queue.value.length) return
  try {
    await markBadgesSeen()
  } catch {
    /* 标记失败无关紧要，最多下次再补播一次 */
  }
}

/** 跳过全部：清空队列并标记已读 */
export async function skipAllAwards() {
  queue.value = []
  try {
    await markBadgesSeen()
  } catch {
    /* ignore */
  }
}

export function useBadgeAward() {
  return { queue, currentAward, awardRemaining, syncing, sync: syncBadgeAwards, consume: consumeAward, skipAll: skipAllAwards }
}