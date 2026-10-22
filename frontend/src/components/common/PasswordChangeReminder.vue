<template>
  <transition name="pwd-banner">
    <div
      v-if="visible"
      class="pwd-banner"
      @mouseenter="pauseAutoDismiss"
      @mouseleave="resumeAutoDismiss"
      @touchstart="pauseAutoDismiss"
    >
      <span class="pwd-banner-text">你仍在使用初始密码</span>
      <button type="button" class="pwd-banner-action" @click="openDialog">去修改</button>
      <button type="button" class="pwd-banner-close" aria-label="关闭提醒" @click="dismiss">
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      </button>
    </div>
  </transition>

  <ChangePasswordDialog v-model="showDialog" />
</template>

<script setup lang="ts">
/**
 * 初始密码提醒（非阻断）
 *
 * 顶部细条：单行文案 + 行内「去修改」+ 关闭，安静地挂在页面上方。
 * 无人操作时 12 秒自动收起，并在本次会话内不再出现（sessionStorage），
 * 避免每次路由切换都弹；手动关闭则按用户长期记住（localStorage）。
 * 改密成功后密码标记翻转，提醒自动消失。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ChangePasswordDialog from './ChangePasswordDialog.vue'

const route = useRoute()
const auth = useAuthStore()

/** 无人操作自动收起的时间 */
const AUTO_DISMISS_MS = 12_000

const showDialog = ref(false)
/** 计数触发本地存储标记重算（storage 不是响应式的） */
const dismissedTick = ref(0)
const autoDismissedTick = ref(0)

const dismissKey = computed(() => (auth.user?.id ? `pwd_reminder_dismissed:${auth.user.id}` : ''))
const autoDismissKey = computed(() => (auth.user?.id ? `pwd_reminder_auto_hidden:${auth.user.id}` : ''))

const dismissed = computed(() => {
  void dismissedTick.value
  return !!dismissKey.value && localStorage.getItem(dismissKey.value) === '1'
})

const autoHidden = computed(() => {
  void autoDismissedTick.value
  return !!autoDismissKey.value && sessionStorage.getItem(autoDismissKey.value) === '1'
})

const visible = computed(() => {
  const path = route.path
  return (
    auth.user?.password_changed === false &&
    !dismissed.value &&
    !autoHidden.value &&
    !path.startsWith('/login') &&
    !path.startsWith('/change-password')
  )
})

let autoTimer: number | undefined

function stopAutoDismiss() {
  if (autoTimer) {
    window.clearTimeout(autoTimer)
    autoTimer = undefined
  }
}

function startAutoDismiss() {
  stopAutoDismiss()
  autoTimer = window.setTimeout(() => {
    if (autoDismissKey.value) sessionStorage.setItem(autoDismissKey.value, '1')
    autoDismissedTick.value += 1
  }, AUTO_DISMISS_MS)
}

function pauseAutoDismiss() {
  stopAutoDismiss()
}

function resumeAutoDismiss() {
  if (visible.value && !showDialog.value) startAutoDismiss()
}

/** 长期关闭：本设备不再提醒 */
function dismiss() {
  if (dismissKey.value) localStorage.setItem(dismissKey.value, '1')
  dismissedTick.value += 1
  stopAutoDismiss()
}

/** 点击「去修改」后不再重复打扰，改密弹窗接管后续流程 */
function openDialog() {
  showDialog.value = true
  if (autoDismissKey.value) sessionStorage.setItem(autoDismissKey.value, '1')
  autoDismissedTick.value += 1
  stopAutoDismiss()
}

watch(visible, (value) => {
  if (value) startAutoDismiss()
  else stopAutoDismiss()
})

onMounted(() => {
  if (visible.value) startAutoDismiss()
})

onBeforeUnmount(stopAutoDismiss)
</script>

<style scoped>
/* 普通提示条：白底浅边、圆角悬浮在顶部居中，样式接近系统/开源项目的轻提示 */
.pwd-banner {
  position: fixed;
  top: calc(env(safe-area-inset-top) + 12px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1900;
  display: flex;
  align-items: center;
  gap: 10px;
  width: max-content;
  max-width: calc(100vw - 32px);
  height: 44px;
  padding: 0 8px 0 14px;
  box-sizing: border-box;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 12px;
  background: #ffffff;
  color: #111111;
  box-shadow: 0 6px 20px rgba(17, 17, 17, 0.08), 0 1px 3px rgba(17, 17, 17, 0.04);
}

.pwd-banner-text {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 1.4;
  letter-spacing: 0.2px;
  color: #3d3d43;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 普通文字链接式的操作，不抢视觉 */
.pwd-banner-action {
  flex-shrink: 0;
  height: 28px;
  padding: 0 6px;
  border: none;
  background: transparent;
  color: #111111;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 1px solid rgba(17, 17, 17, 0.5);
  border-radius: 0;
  transition: opacity 0.18s ease;
}

.pwd-banner-action:hover {
  opacity: 0.6;
}

.pwd-banner-close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #9a9aa0;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease;
}

.pwd-banner-close:hover {
  color: #111111;
  background: rgba(17, 17, 17, 0.05);
}

/* 桌面端：让出顶栏高度。transform 用于水平居中，动画需在此一并声明 */
@media (min-width: 769px) {
  .pwd-banner {
    top: calc(52px + 12px);
    min-width: 300px;
  }
}

.pwd-banner-enter-active,
.pwd-banner-leave-active {
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.22s ease;
}

.pwd-banner-enter-from,
.pwd-banner-leave-to {
  transform: translateX(-50%) translateY(-10px);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .pwd-banner-enter-active,
  .pwd-banner-leave-active {
    transition: opacity 0.2s ease;
  }
  .pwd-banner-enter-from,
  .pwd-banner-leave-to {
    transform: translateX(-50%);
  }
}
</style>
