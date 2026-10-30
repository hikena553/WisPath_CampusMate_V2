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

const props = defineProps<{
  /** 显隐（v-model） */
  modelValue: boolean
  /** 标题：移动端子页栏 / 桌面端弹窗标题 */
  title?: string
  /** 桌面端弹窗宽度（移动端全屏，不生效） */
  width?: string
  /** 桌面端弹窗距顶距离 */
  top?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'opened'): void
}>()

const { isMobile } = useResponsive()

function close() {
  emit('update:modelValue', false)
}

// 移动端：子页出现后补发一次 opened（桌面端由 el-dialog 原生触发，经 $attrs 透传）
watch(() => props.modelValue, (v) => {
  if (v && isMobile.value) {
    nextTick(() => emit('opened'))
  }
  // 全屏子页打开时锁住底层页面滚动，关闭时恢复
  if (typeof document !== 'undefined') {
    document.body.style.overflow = v && isMobile.value ? 'hidden' : ''
  }
}, { immediate: true })

onUnmounted(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})
</script>

<template>
  <!-- 移动端：全屏子页承接（无遮罩弹窗） -->
  <Teleport to="body">
    <Transition name="rp-sheet">
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
          </div>
          <div v-if="$slots.footer" class="rp-foot">
            <slot name="footer" />
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
    @update:model-value="close"
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
  z-index: 2500;
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
  width: 30px;
  height: 30px;
  margin-left: -4px;
  border: 0;
  border-radius: 8px;
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
  padding: 16px 16px 24px;
}

/* ===== 底部操作条：吸底 + 安全区 ===== */
.rp-foot {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid #eef0f4;
}
.rp-foot > :deep(.el-button) { border-radius: 10px; }

/* ===== 过渡：整页自底部推入（原生 App 子页手感） ===== */
.rp-sheet-enter-active { transition: transform 0.3s cubic-bezier(0.32, 0.72, 0.32, 1); }
.rp-sheet-leave-active { transition: transform 0.24s cubic-bezier(0.4, 0, 1, 1); }
.rp-sheet-enter-from,
.rp-sheet-leave-to { transform: translateY(100%); }
</style>
