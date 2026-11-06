<script setup lang="ts">
import { watch, nextTick, onUnmounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'

/**
 * ResponsivePopup —— 弹窗 / 全屏子页二合一容器（移动端优先）。
 *
 * 设计原则（v6 弹窗重设计）：
 * - 移动端（<768px）：不渲染遮罩弹窗，而是渲染全屏「子页」——
 *   48px 吸顶返回栏（与学业中心子页头 tui-appbar 同规格）+ 可滚动内容区 +
 *   可选底部操作条（#footer 插槽）。符合移动端「少弹窗、整页承接」的交互范式。
 * - 桌面端（>=768px）：透传渲染为 el-dialog，配合全局「方案A · 极简卡片」
 *   弹窗样式（styles/dialog-minimal.css）。
 *
 * 用法与 el-dialog 一致：v-model / title / width / top / #footer，
 * 其余属性与事件（如 :close-on-click-modal、@opened）经 $attrs 透传到桌面端
 * el-dialog；移动端在子页出现后同样会触发一次 opened，保证裁剪器等
 * 依赖 opened 的初始化逻辑两端可用。
 */
defineOptions({ name: 'ResponsivePopup', inheritAttrs: false })

const props = withDefaults(defineProps<{
  /** 显隐（v-model） */
  modelValue: boolean
  /** 标题：移动端子页栏 / 桌面端弹窗标题 */
  title?: string
  /** 桌面端弹窗宽度（移动端全屏，不生效） */
  width?: string
  /** 桌面端弹窗距顶距离 */
  top?: string
  /**
   * 移动端的进场方式，两选一：
   * - 'sheet'（默认）：整页自**底部**推入（0.3s 阻尼曲线）。适合「办一件事就关」的
   *   表单弹层（教师端关怀记录、巡视登记、发起任务等存量 20+ 个弹窗都是这个性质）。
   * - 'subpage'：走全站统一的整屏子页动画（styles/animations.css 的 .subpage ——
   *   从右滑入，配合打开方页面挂 .subpage-underlay 做「下层退 30%」的让位）。
   *   适合「进一层去挑东西」的页面，如发起群聊的选人页：它和消息搜索、添加朋友
   *   是同一层级的子页，从底部弹上来会显得比同层页面「矮一辈」。
   */
  transition?: 'sheet' | 'subpage'
}>(), {
  transition: 'sheet',
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'opened'): void
}>()

const { isMobile } = useResponsive()

function close() {
  emit('update:modelValue', false)
}

/**
 * 承接 el-dialog 的 update:modelValue。
 * el-dialog 在打开/关闭时都会派发该事件，旧实现直接绑 close 会无条件回传 false，
 * 语义上等同于「弹窗一被打开就被自己关掉」。这里只在真正的关闭动作（v===false）时回传。
 */
function onDialogVisibleChange(v: boolean) {
  if (v === false) emit('update:modelValue', false)
}

/**
 * 移动端全屏子页的滚动锁（引用计数）。
 *
 * 旧实现每个实例各自写 `document.body.style.overflow = ''`，弹窗叠加时
 * （例如公告子页里再起一个确认层）先关掉的那个会把锁清空，底层页面跟着滚起来。
 * 这里改成模块级计数：只有最后一个打开者关闭时才真正恢复滚动。
 */
let scrollLockCount = 0
let savedOverflow = ''

function lockScroll() {
  if (typeof document === 'undefined') return
  if (scrollLockCount === 0) {
    savedOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  scrollLockCount++
}

function unlockScroll() {
  if (typeof document === 'undefined') return
  if (scrollLockCount === 0) return
  scrollLockCount--
  if (scrollLockCount === 0) document.body.style.overflow = savedOverflow
}

// 本实例当前是否持有锁，避免重复加锁/重复解锁
let holdingLock = false

function syncScrollLock(shouldLock: boolean) {
  if (shouldLock === holdingLock) return
  holdingLock = shouldLock
  shouldLock ? lockScroll() : unlockScroll()
}

// 移动端：子页出现后补发一次 opened（桌面端由 el-dialog 原生触发，经 $attrs 透传）
// 同时跟踪 isMobile：打开状态下视口切到桌面会改走 el-dialog，此时必须释放滚动锁
watch([() => props.modelValue, isMobile], ([v, mobile], [, prevMobile]) => {
  if (v && mobile && !prevMobile) {
    nextTick(() => emit('opened'))
  }
  // 只有「移动端且打开」才需要锁；切换视口到桌面时也要释放
  syncScrollLock(!!v && mobile)
}, { immediate: true })

onUnmounted(() => {
  // 组件销毁时若仍持锁，必须归还，否则 body 会永久无法滚动
  syncScrollLock(false)
})
</script>

<template>
  <!-- 移动端：全屏子页承接（无遮罩弹窗）。
       transition='subpage' 时复用全站 .subpage 类（0.3s、从右滑入、进出同向），
       与消息搜索 / 添加朋友 / 办事子页同一套；默认 'sheet' 仍是底部推入。 -->
  <Teleport to="body">
    <Transition
      :name="transition === 'subpage' ? 'subpage' : 'rp-sheet'"
      :duration="transition === 'subpage' ? 320 : undefined"
    >
      <div v-if="isMobile && modelValue" class="rp-wrap" role="dialog" :aria-label="title">
        <div class="rp-sheet">
          <header class="rp-appbar">
            <button type="button" class="rp-back" aria-label="返回" @click="close">
              <el-icon :size="20"><ArrowLeft /></el-icon>
            </button>
            <div class="rp-title">
              <span class="rp-title-txt">{{ title }}</span>
            </div>
            <div v-if="$slots.right" class="rp-actions">
              <slot name="right" />
            </div>
          </header>
          <div class="rp-body">
            <slot />
            <!-- 操作按钮跟在表单内容末尾（页面结束的下面），不再悬浮吸底 -->
            <div v-if="$slots.footer" class="rp-foot">
              <slot name="footer" />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 桌面端：极简卡片弹窗（样式见 styles/dialog-minimal.css） -->
  <el-dialog
    v-if="!isMobile"
    v-bind="$attrs"
    :model-value="modelValue"
    :title="title"
    :width="width || '560px'"
    :top="top || '8vh'"
    @update:model-value="onDialogVisibleChange"
    @opened="$emit('opened')"
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </el-dialog>
</template>

<style scoped>
/* ===== 外层：全屏承载（桌面窄窗口下限宽 480px 居中，真机全宽） ===== */
.rp-wrap {
  position: fixed;
  inset: 0;
  z-index: 2700;
  display: flex;
  justify-content: center;
  background: #fff;
}
.rp-sheet {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 480px;
  height: 100%;
  background: #fff;
  overflow: hidden;
}

/* ===== 子页头：与 tui-appbar 同规格（48px 白底 + 发丝线） ===== */
.rp-appbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 48px;
  min-height: 48px;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid #e9ebee;
}
.rp-back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-left: 0;
  flex-shrink: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #1f2430;
  cursor: pointer;
}
.rp-back:active { background: rgba(20, 23, 26, 0.06); }
.rp-title {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
  color: #1f2430;
}
.rp-title-txt {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rp-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== 内容区 ===== */
.rp-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding: 16px 16px calc(24px + env(safe-area-inset-bottom));
}

/* ===== 操作区：随内容滚到页面末尾，与表单保持同一节奏 ===== */
.rp-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
  padding-top: 14px;
  padding-bottom: calc(4px + env(safe-area-inset-bottom));
  background: transparent;
  border-top: 1px solid #eef0f4;
}
/* 两个操作按钮一行铺满：取消 / 确定各占一半 */
.rp-foot > :deep(.el-button) {
  flex: 1 1 0;
  width: 100%;
  margin-left: 0;
  border-radius: 10px;
}

/* ===== 过渡：复用全站唯一实现 .subpage（styles/animations.css，右侧滑入/滑出） =====
   不再使用自底部推入的抽屉动画，保证与学生端多级页面切换手感完全一致。 */
</style>

<!-- 非 scoped：下拉浮层被 teleport 到 body，scoped 样式无法命中。
     移动端全屏子页层级为 2700，而 el-popper 默认约 2000，会把选项盖在子页下面。 -->
<style>
@media (max-width: 767px) {
  .el-select__popper,
  .el-dropdown__popper,
  .el-picker__popper {
    z-index: 3000 !important;
  }
}
</style>
