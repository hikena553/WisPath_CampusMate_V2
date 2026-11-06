<template>
  <transition name="pwd-banner">
    <div
      v-if="visible"
      class="pwd-banner"
      role="status"
      @mouseenter="pauseAutoDismiss"
      @mouseleave="resumeAutoDismiss"
      @touchstart="pauseAutoDismiss"
    >
      <span class="pwd-banner-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <rect x="5" y="11" width="14" height="9" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
        </svg>
      </span>
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
/*
  视觉与登录成功提示（全局 ElMessage.success）保持一致：
  白底卡片 + 12px 圆角 + 1px 细边 + 轻投影，左侧状态图标、中间单行文案、右侧关闭。
  不再做成整条通栏，而是像提示条一样悬浮在顶部居中。
  z-index 高于页签栏（1000），低于 Element 弹层（2000+），改密弹窗打开时不会串层。
*/
.pwd-banner {
  position: fixed;
  top: calc(env(safe-area-inset-top, 0px) + 12px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1900;
  display: flex;
  align-items: center;
  gap: 8px;
  width: max-content;
  max-width: calc(100vw - 32px);
  padding: 11px 10px 11px 14px;
  box-sizing: border-box;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 12px;
  background: var(--bg-card);
  color: #111111;
  box-shadow: 0 10px 28px rgba(17, 17, 17, 0.08), 0 2px 6px rgba(17, 17, 17, 0.04);
}

/* 深色主题对齐全局提示条，避免白底卡片在暗色页面上突兀 */
:global(html.dark) .pwd-banner {
  border-color: rgba(255, 255, 255, 0.1);
  color: #e8e8ea;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45);
}

.pwd-banner-icon {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  color: inherit;
}

.pwd-banner-text {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 13.5px;
  line-height: 1.45;
  color: inherit;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 提示条内的行内操作：文字链接式，不抢视觉 */
.pwd-banner-action {
  flex: 0 0 auto;
  height: 24px;
  padding: 0 2px;
  border: none;
  background: transparent;
  color: inherit;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-decoration-color: color-mix(in srgb, currentColor 45%, transparent);
  text-underline-offset: 3px;
  transition: opacity 0.18s ease;
}

.pwd-banner-action:hover {
  opacity: 0.6;
}

.pwd-banner-close {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  opacity: 0.55;
  cursor: pointer;
  transition: opacity 0.18s ease, background 0.18s ease;
}

.pwd-banner-close:hover {
  opacity: 1;
  background: color-mix(in srgb, currentColor 8%, transparent);
}

/* 桌面端让出顶栏高度 */
@media (min-width: 769px) {
  .pwd-banner {
    top: calc(clamp(46px, 11.8vw, 52px) + 12px);
  }
}

/* 窄屏只是收紧留白，形态仍是悬浮卡片 */
@media (max-width: 768px) {
  .pwd-banner {
    gap: 6px;
    max-width: calc(100vw - 24px);
    padding: 10px 8px 10px 12px;
  }
  .pwd-banner-text {
    font-size: 12.5px;
  }
  .pwd-banner-action {
    font-size: 12px;
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
