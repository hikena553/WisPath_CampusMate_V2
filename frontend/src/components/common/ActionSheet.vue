<script setup lang="ts">
import { watch, onUnmounted } from 'vue'
import { Close } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'

/**
 * ActionSheet —— 移动端底部半屏动作面板（微信 / iOS ActionSheet 范式）。
 *
 * 设计原则（v6.1 弹窗减负）：
 * - 移动端（<768px）：内容少 / 交互轻的场景不再开全屏子页、也不再弹居中对话框，
 *   统一用「半屏底部面板」承接：圆角上滑 + 把手 + 遮罩，点遮罩或把手即关。
 * - 桌面端（>=768px）：透传渲染为 el-dialog（$attrs 转发），样式沿用
 *   dialog-minimal.css「方案A · 极简卡片」。
 *
 * 用法与 el-dialog 一致：v-model / title / width + #footer 插槽。
 * 典型场景：单字段编辑、1~3 字段小表单、选项选择、轻量详情、删除确认。
 */
defineOptions({ name: 'ActionSheet', inheritAttrs: false })

const props = defineProps<{
  /** 显隐（v-model） */
  modelValue: boolean
  /** 标题（可省略，省略后仅显示把手） */
  title?: string
  /** 桌面端弹窗宽度（移动端半屏，不生效） */
  width?: string
  /** 隐藏头部（纯内容面板，如选项列表自带头部时） */
  hideHeader?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const { isMobile } = useResponsive()

function close() {
  emit('update:modelValue', false)
}

// 打开时锁住底层页面滚动，关闭时恢复
watch(() => props.modelValue, (v) => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = v && isMobile.value ? 'hidden' : ''
  }
}, { immediate: true })

onUnmounted(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})
</script>

<template>
  <!-- 移动端：半屏底部动作面板 -->
  <Teleport to="body">
    <Transition name="as-mask">
      <div v-if="isMobile && modelValue" class="as-mask" @click.self="close">
        <div class="as-sheet" role="dialog" :aria-label="title">
          <button type="button" class="as-grabber" aria-label="收起" @click="close" />
          <header v-if="!hideHeader && title" class="as-head">
            <div class="as-title">{{ title }}</div>
            <button type="button" class="as-close" aria-label="关闭" @click="close">
              <el-icon :size="16"><Close /></el-icon>
            </button>
          </header>
          <div class="as-body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="as-foot">
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
    :width="width || '480px'"
    @update:model-value="close"
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </el-dialog>
</template>

<style scoped>
/* ===== 遮罩 ===== */
.as-mask {
  position: fixed;
  inset: 0;
  z-index: 2700;
  display: flex;
  justify-content: center;
  background: rgba(17, 20, 26, 0.5);
}
.as-mask-enter-active { transition: opacity 0.25s ease; }
.as-mask-leave-active { transition: opacity 0.2s ease; }
.as-mask-enter-from,
.as-mask-leave-to { opacity: 0; }

/* ===== 面板：底部上滑，最大 78vh 可滚 ===== */
.as-sheet {
  align-self: flex-end;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 480px;
  max-height: 78vh;
  background: #fff;
  border-radius: 16px 16px 0 0;
  overflow: hidden;
  padding-bottom: env(safe-area-inset-bottom);
  animation: as-up 0.28s cubic-bezier(0.32, 0.72, 0.32, 1);
}
.as-mask-leave-active .as-sheet { animation: as-down 0.2s ease forwards; }
@keyframes as-up { from { transform: translateY(100%); } to { transform: translateY(0); } }
@keyframes as-down { from { transform: translateY(0); } to { transform: translateY(100%); } }

/* ===== 把手：点按即收起 ===== */
.as-grabber {
  flex-shrink: 0;
  width: 36px;
  height: 4px;
  margin: 8px auto 2px;
  padding: 0;
  border: 0;
  border-radius: 2px;
  background: #dfe2e8;
  cursor: pointer;
}

/* ===== 头部 ===== */
.as-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 16px 0;
}
.as-title {
  font-size: 15px;
  font-weight: 600;
  color: #1c1e21;
  letter-spacing: 0.2px;
}
.as-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-right: -6px;
  border: 0;
  border-radius: 50%;
  background: #f1f2f6;
  color: #6b7078;
  cursor: pointer;
}
.as-close:active { background: #e5e7ee; }

/* ===== 内容区 ===== */
.as-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding: 12px 16px 16px;
}

/* ===== 底部操作条 ===== */
.as-foot {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 16px 12px;
  border-top: 1px solid #eef0f4;
  background: #fff;
}
.as-foot > :deep(.el-button) { border-radius: 10px; }
</style>
