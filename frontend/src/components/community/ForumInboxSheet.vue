<template>
  <Teleport to="body">
    <!-- ① 遮罩：只干两件事 —— 桌面端点空白关闭、把背景压暗。
         刻意不参与滑动，只给一个 0.2s 淡入淡出：遮罩是整屏的，
         跟着面板一起 translateX 的话会变成一块黑幕横扫过屏幕。 -->
    <Transition name="fis-mask">
      <div v-if="modelValue" class="fis-mask" @click="close" />
    </Transition>

    <!-- ② 面板：进出场直接复用全局 .subpage（styles/subpage-transition.css，全站唯一实现），
         与资讯详情 / 搜索子页同一套 keyframes、同一时长（0.3s，:duration 给 320 兜底移除）。
         为什么这里不用 <SubPageShell>：外壳的 .subpage-root 骨架是「fixed inset:0 全屏 + 白底」，
         只适合整屏子页；本面板桌面端是右侧 420px 抽屉，被塞进全屏骨架后遮罩会一起卷进滑动元素。
         面板自己贴右边缘、宽度恰好是屏宽（移动端）/ 420px（桌面），
         于是 keyframes 的 translateX(100%) 在两种版式下都正好把它推出屏幕右侧，
         一套动画两个断点都对得上，也就不必为两套版式各写一份模板。 -->
    <Transition name="subpage" :duration="320" @after-leave="onAfterLeave">
      <section
        v-if="modelValue"
        class="fis-panel"
        role="dialog"
        aria-modal="true"
        aria-label="互动消息"
      >
        <!-- 页头按参考设计的结构排：左返回 / 中标题 / 右侧两个动作图标。
             参考图中间是「好友 | 消息」两个页签，那是聊天 App 的分区；
             本面板只有互动消息一类，所以居中标题原位保留，不硬造一个空页签。 -->
        <header class="fis-head">
          <button type="button" class="fis-icon-btn" :aria-label="isMobile ? '返回' : '关闭'" @click="close">
            <DtIcon :name="isMobile ? 'back' : 'close'" :size="20" />
          </button>
          <h2 class="fis-title">互动消息</h2>
          <div class="fis-actions">
            <button type="button" class="fis-icon-btn" aria-label="搜索" @click="inboxRef?.openSearch()">
              <DtIcon name="search" :size="19" />
            </button>
            <button
              v-if="unreadTotal > 0"
              type="button"
              class="fis-icon-btn"
              aria-label="全部标为已读"
              @click="inboxRef?.readAll()"
            >
              <DtIcon name="check" :size="20" />
            </button>
          </div>
        </header>
        <div class="fis-body">
          <ForumInbox ref="inboxRef" @open-profile="onOpenProfile" @unread-change="onUnreadChange" />
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 互动消息面板（论坛侧）
 *
 * 论坛的赞 / 收藏 / 评论 / 新粉丝只在这里出现，消息页只管群聊、私聊、通知——
 * 两套消息用两套表、两个入口，互不混排。
 * 入口是交流社区页右上角的信封图标（校园资讯页头那枚信封也指向这里）。
 *
 * 版式：移动端整屏覆盖（与消息页聊天子页同一套观感），桌面端右侧 420px 抽屉。
 * 进场 / 退场沿用全站覆盖式子页的那套滑入动画（styles/subpage-transition.css），
 * 面板贴右边缘，所以「从右侧滑入、原路滑出」在两个断点下都成立。
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import DtIcon from '@/components/common/DtIcon.vue'
import ForumInbox from '@/components/messages/ForumInbox.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { lockBodyScroll } from '@/utils/bodyScrollLock'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'unread-change', total: number): void
}>()

const { isMobile } = useResponsive()
const { refresh: refreshUnread } = useUnreadSummary()
const inboxRef = ref<InstanceType<typeof ForumInbox> | null>(null)
/** 未读总数：页头「全部标为已读」按钮的出现条件（0 时不占位） */
const unreadTotal = ref(0)

function close() {
  emit('update:modelValue', false)
  // 关掉面板时顺手刷新全局未读，入口红点与已读状态保持一致
  void refreshUnread()
}

function onOpenProfile(userId: number) {
  close()
  openUserHomepage(userId)
}

/** 面板内「全部已读 / 单条已读」后立刻同步入口徽标，不必等 5s 轮询 */
function onUnreadChange(total: number) {
  unreadTotal.value = total
  emit('unread-change', total)
  void refreshUnread()
}

/* ==================== 滚动锁 ====================
   面板自己内部滚动，背后页面不该跟着动。用引用计数版（utils/bodyScrollLock）：
   信封面板可能与资讯详情 / 搜索子页叠在一起，各层各持一把锁，互不拆台。
   退场动画播完才解锁，否则滑出的 0.3s 里背景就能被拖动。 */
let releaseScrollLock: (() => void) | null = null

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return // 关闭方向等 after-leave
    await nextTick()
    if (!releaseScrollLock) releaseScrollLock = lockBodyScroll()
  },
  { immediate: true },
)

function onAfterLeave() {
  releaseScrollLock?.()
  releaseScrollLock = null
}

/* ==================== Esc ====================
   与返回箭头同语义：面板里有分类/搜索子页时先退子页（ForumInbox.handleEsc
   返回 true 表示已消费），子页退完再关面板。 */
function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape' || !props.modelValue) return
  if (inboxRef.value?.handleEsc()) return
  close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  releaseScrollLock?.()
  releaseScrollLock = null
})

defineExpose({ reload: () => inboxRef.value?.reload() })
</script>

<style scoped>
/* ================= 遮罩 =================
   桌面端压暗背景 + 点空白关闭；移动端整屏面板会盖住它，所以透明（见文末媒体查询）——
   滑动过程中露出来的必须是下层页面，而不是一层浅灰。 */
.fis-mask {
  position: fixed;
  inset: 0;
  /* 盖过底部悬浮胶囊（1000），低于 Element 弹层（2000+） */
  z-index: 1500;
  background: rgba(0, 0, 0, .28);
}
.fis-mask-enter-active,
.fis-mask-leave-active { transition: opacity .2s ease; }
.fis-mask-enter-from,
.fis-mask-leave-to { opacity: 0; }

/* ================= 面板 =================
   贴右边缘固定：移动端 width:100%，桌面端 420px。
   宽度就是「被推出屏幕」所需的位移，所以全局 .subpage 的 translateX(100%)
   在两种版式下都恰好滑到屏幕外，不需要再写一份移动端专用 keyframes。 */
.fis-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 1501;
  display: flex;
  flex-direction: column;
  width: 420px;
  max-width: 100%;
  background: var(--dt-surface, #fff);
  box-shadow: -8px 0 32px rgba(0, 0, 0, .12);
  -webkit-tap-highlight-color: transparent;
}
/* 页头：左返回 / 中标题 / 右动作。标题绝对居中——两侧按钮数量不等时
   （未读为 0 时右侧只剩搜索），flex 居中会把标题推歪。 */
.fis-head {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 8px 0 10px;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.fis-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--dt-text, #171a1d);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.fis-icon-btn:hover { background: var(--dt-hover, rgba(0, 0, 0, .04)); }
.fis-title {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--dt-text, #171a1d);
  pointer-events: none;
}
.fis-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
}
.fis-body {
  flex: 1;
  min-height: 0;
  display: flex;
  padding-top: 10px;
}

@media (max-width: 767px) {
  .fis-mask { background: transparent; }
  .fis-panel {
    width: 100%;
    box-shadow: none;
  }
  .fis-head { height: 50px; }
}
</style>
