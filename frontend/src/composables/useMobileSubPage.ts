import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch, type Ref } from 'vue'

/**
 * 页内「二级页面」的全局登记表。
 *
 * 底部悬浮导航（MobileTabBar）只属于**一级页面**（即底部页签自身对应的页面）。
 * 一旦页面内下钻到子页（学生详情 / 个人中心设置 / 聊天详情 / 今日任务等），
 * 返回链路应当由子页自己的返回按钮承担，全局页签此时既无意义、又会压住子页内容，
 * 所以布局层据此在移动端隐藏整条导航（连同底部让位）。
 *
 * 用计数而不是布尔值：子页可以层层叠加（如消息列表 → 聊天 → 群设置），
 * 任意一层关闭只能撤销自己那一层，最后一层退出时才恢复导航。
 */
const openLayers = ref(0)

export const hasOpenSubPage = computed(() => openLayers.value > 0)

/**
 * 把一个页内二级页面的显隐状态登记到全局表。
 * 传 computed 即可，页面无需关心布局层如何消费。
 */
export function useMobileSubPage(open: Ref<boolean>) {
  let counted = false

  function sync(value: boolean) {
    if (value === counted) return
    counted = value
    openLayers.value = Math.max(0, openLayers.value + (value ? 1 : -1))
  }

  watch(open, sync, { immediate: true })
  onBeforeUnmount(() => sync(false))
  // keep-alive 页面（教师端首页/学生档案）被切走时不再占用登记位，
  // 重新激活后再按当前状态补回，避免缓存页面把导航一直藏着
  onDeactivated(() => sync(false))
  onActivated(() => sync(open.value))
}

/**
 * 「下层让位」的全局登记表 —— 与上面那张表是两件事，别合并：
 * - openLayers 决定导航**要不要在**（隐藏 = 不渲染）；
 * - pushed 决定导航**要不要跟着内容一起走**。
 *
 * 页面自己把主内容推开 -30%（.subpage-underlay）时，底部胶囊属于布局层、
 * 不在页面里，如果不管它，就会「内容左移、胶囊钉在原地」—— 一层被拆成两半，
 * 观感很怪。所以页面在推开内容的同时在这里登记，布局层据此把胶囊一起推。
 *
 * 用计数而不是布尔值：同一个页面可能同时开多层子页（聊天 + 发起群聊），
 * 任意一层关闭只撤销自己那一次。
 */
const pushedLayers = ref(0)

export const isSubpagePushed = computed(() => pushedLayers.value > 0)

/** 页面推开内容时调用；传的 computed 与页面给 .subpage-underlay 用的是同一个。 */
export function useSubpagePush(active: Ref<boolean>) {
  let counted = false

  function sync(value: boolean) {
    if (value === counted) return
    counted = value
    pushedLayers.value = Math.max(0, pushedLayers.value + (value ? 1 : -1))
  }

  watch(active, sync, { immediate: true })
  onBeforeUnmount(() => sync(false))
  onDeactivated(() => sync(false))
  onActivated(() => sync(active.value))
}
