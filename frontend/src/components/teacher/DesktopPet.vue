<template>
  <!-- 桌宠：教师端桌面端常驻入口，一键唤起与智能体对话，无需跳转智能体页面。
       挂载在 TeacherLayout 的布局层（.app-shell 内），因此：
       1) 与 HomePage 的 .home-dashboard 是兄弟关系，不会被其「全局禁动效」规则冻住；
       2) 路由切换时不会被重挂载，拖拽位置与展开态得以保留。 -->
  <div
    class="desk-pet"
    :style="{ left: pos.x + 'px', top: pos.y + 'px' }"
    :class="{ expanded, dragging }"
  >
    <Transition name="pet-fade">
      <div v-if="expanded" class="desk-pet-panel" :style="panelStyle">
        <PetChatPanel @close="collapse" />
      </div>
    </Transition>

    <button
      type="button"
      class="desk-pet-handle"
      :aria-label="`${agentName}，点击与我对话`"
      @pointerdown="onPointerDown"
      @keydown.enter.prevent="toggle"
      @keydown.space.prevent="toggle"
    >
      <MianCharacter state="idle" mini />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MianCharacter from '@/components/agent/MianCharacter.vue'
import PetChatPanel from '@/components/teacher/PetChatPanel.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

const { agentName } = useSiteConfig()

const POS_KEY = 'teacher_pet_pos'
const OPEN_KEY = 'teacher_pet_open'

/** 侧边栏宽度（TeacherLayout.vue 中 .sidebar 为 216px）：桌宠不能压到侧边栏上 */
const SIDEBAR_W = 216
const PET_SIZE = 56
const PANEL_W = 360
const PANEL_H = 520
const EDGE = 10

const expanded = ref(false)
const dragging = ref(false)
const pos = ref({ x: 0, y: 0 })

let dragOrigin = { x: 0, y: 0, left: 0, top: 0 }
let moved = false

/** 可用范围钳制：避开左侧 216px 侧边栏与底部安全区，防止桌宠跑到屏幕外 */
function clamp(x: number, y: number) {
  const maxLeft = Math.max(SIDEBAR_W + EDGE, window.innerWidth - PET_SIZE - EDGE)
  const maxTop = Math.max(EDGE, window.innerHeight - PET_SIZE - EDGE)
  return {
    x: Math.min(Math.max(x, SIDEBAR_W + EDGE), maxLeft),
    y: Math.min(Math.max(y, EDGE), maxTop),
  }
}

/**
 * 面板贴靠策略：默认浮在吉祥物上方、右对齐。
 * 视口空间不足时自动翻转（上方不够 → 改到下方；右侧不够 → 改到左侧），避免面板被裁切。
 */
const panelStyle = computed(() => {
  const roomAbove = pos.value.y >= PANEL_H + 64
  const roomRight = pos.value.x + PANEL_W <= window.innerWidth - EDGE
  return {
    top: roomAbove ? 'auto' : '64px',
    bottom: roomAbove ? '64px' : 'auto',
    right: roomRight ? '0' : 'auto',
    left: roomRight ? 'auto' : '0',
  }
})

function restore() {
  try {
    const raw = localStorage.getItem(POS_KEY)
    if (raw) {
      const saved = JSON.parse(raw) as { x: number; y: number }
      pos.value = clamp(saved.x, saved.y)
      return
    }
  } catch { /* 配置损坏时退回默认位置 */ }
  pos.value = clamp(window.innerWidth - PET_SIZE - 24, window.innerHeight - PET_SIZE - 24)
}

function toggle() {
  expanded.value ? collapse() : expand()
}

function expand() {
  expanded.value = true
  localStorage.setItem(OPEN_KEY, '1')
}

function collapse() {
  expanded.value = false
  localStorage.setItem(OPEN_KEY, '0')
}

function onPointerDown(e: PointerEvent) {
  // 只响应主键，避免右键菜单误拖
  if (e.button !== 0) return
  dragging.value = false
  moved = false
  dragOrigin = { x: e.clientX, y: e.clientY, left: pos.value.x, top: pos.value.y }
  const target = e.currentTarget as HTMLElement
  target.setPointerCapture(e.pointerId)
  target.addEventListener('pointermove', onPointerMove)
  target.addEventListener('pointerup', onPointerUp)
  target.addEventListener('pointercancel', onPointerUp)
}

function onPointerMove(e: PointerEvent) {
  const dx = e.clientX - dragOrigin.x
  const dy = e.clientY - dragOrigin.y
  // 4px 位移阈值：区分「点击=展开」与「拖拽=移动位置」
  if (!moved && Math.abs(dx) + Math.abs(dy) < 4) return
  moved = true
  dragging.value = true
  pos.value = clamp(dragOrigin.left + dx, dragOrigin.top + dy)
}

function onPointerUp(e: PointerEvent) {
  const target = e.currentTarget as HTMLElement
  target.removeEventListener('pointermove', onPointerMove)
  target.removeEventListener('pointerup', onPointerUp)
  target.removeEventListener('pointercancel', onPointerUp)
  dragging.value = false
  if (moved) {
    localStorage.setItem(POS_KEY, JSON.stringify(pos.value))
  } else {
    toggle()
  }
}

function onResize() {
  pos.value = clamp(pos.value.x, pos.value.y)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && expanded.value) collapse()
}

onMounted(() => {
  restore()
  expanded.value = localStorage.getItem(OPEN_KEY) === '1'
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKeydown)
})

// 展开态下窗口尺寸变化时同步校验面板翻转
watch(expanded, () => pos.value = clamp(pos.value.x, pos.value.y))
</script>

<style scoped>
.desk-pet {
  position: fixed;
  z-index: 950;
  transition: none;
}
.desk-pet.expanded { z-index: 951; }

.desk-pet-handle {
  position: relative;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.18), 0 1px 3px rgba(15, 23, 42, 0.1);
  cursor: grab;
  padding: 0;
  touch-action: none;
  user-select: none;
}
.desk-pet.dragging .desk-pet-handle { cursor: grabbing; }
.desk-pet-handle:hover { box-shadow: 0 8px 24px rgba(15, 23, 42, 0.22), 0 1px 3px rgba(15, 23, 42, 0.12); }
.desk-pet-handle:focus-visible { outline: 2px solid var(--tui-brand); outline-offset: 2px; }

.desk-pet-panel {
  position: absolute;
}

.pet-fade-enter-active, .pet-fade-leave-active { transition: opacity 0.18s var(--tui-ease), transform 0.18s var(--tui-ease); }
.pet-fade-enter-from, .pet-fade-leave-to { opacity: 0; transform: translateY(8px) scale(0.96); }

/* 尊重系统「减少动态效果」偏好 */
@media (prefers-reduced-motion: reduce) {
  .desk-pet-handle, .desk-pet-handle:hover { box-shadow: 0 6px 20px rgba(15, 23, 42, 0.18); }
  .pet-fade-enter-active, .pet-fade-leave-active { transition: none; }
}
</style>
