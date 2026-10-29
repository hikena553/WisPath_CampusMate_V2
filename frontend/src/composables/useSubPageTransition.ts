/**
 * 覆盖式子页的状态机：visible / open() / close() / after-leave 收尾
 *
 * 解决的是「从右滑入的子页」那一套固定套路 —— 父页 v-if 挂载 = 打开、
 * 用户点返回 = 先播 0.3s 退场动画、播完才通知父页卸载。这三步每次手写一遍很容易漏掉
 * 最后一步（父页立刻卸载 → 退场动画被掐断，观感是「啪」一下消失）。
 *
 * 与 SubPageShell 的分工：
 * - SubPageShell 负责渲染与动画（Teleport / Transition / 骨架 / Esc / 滚动锁）；
 * - 本 composable 只管状态：什么时候算打开、什么时候算关完。
 *
 * 典型用法（父页 v-if 控制挂载，挂载即打开）：
 *   const { visible, close, handleAfterLeave } = useSubPageTransition({
 *     onAfterLeave: () => emit('closed'),   // 父页收到后才卸载本组件
 *   })
 *   <SubPageShell v-model="visible" @after-leave="handleAfterLeave"> … </SubPageShell>
 *
 * 需要自己接管打开时机（例如带参数的 open(url)）时传 autoOpen: false，
 * 在自己的 open 里调用 open()。
 */
import { onMounted, ref } from 'vue'

export interface UseSubPageTransitionOptions {
  /** 挂载即打开（默认 true）。父页用 v-if 控制挂载时保持默认即可 */
  autoOpen?: boolean
  /** 开始关闭（退场动画起播的那一刻）触发，一般用来同步父页的「正在关闭」标记 */
  onClose?: () => void
  /** 退场动画播完、子树即将被移除时触发；父页应在这里才把子页从 DOM 上摘掉 */
  onAfterLeave?: () => void
}

export function useSubPageTransition(options: UseSubPageTransitionOptions = {}) {
  const { autoOpen = true, onClose, onAfterLeave } = options

  const visible = ref(false)
  /** 退场动画是否正在播（子页可据此禁用内部交互，避免关到一半又被点开） */
  const closing = ref(false)

  function open() {
    closing.value = false
    visible.value = true
  }

  /** 幂等：重复调用（连点返回 / Esc 与返回按钮同时触发）不会重复 emit */
  function close() {
    if (!visible.value || closing.value) return
    closing.value = true
    visible.value = false
    onClose?.()
  }

  /** 绑到 <SubPageShell @after-leave>：交给 SubPageShell 在元素移除前调用 */
  function handleAfterLeave() {
    closing.value = false
    onAfterLeave?.()
  }

  onMounted(() => {
    if (autoOpen) open()
  })

  return { visible, closing, open, close, handleAfterLeave }
}
