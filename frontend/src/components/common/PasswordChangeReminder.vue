<template>
  <transition name="pwd-reminder">
    <div v-if="visible" class="pwd-reminder">
      <span class="pwd-reminder-icon">
        <el-icon :size="15"><InfoFilled /></el-icon>
      </span>
      <span class="pwd-reminder-text">你的账号仍在使用初始密码，建议尽快修改</span>
      <el-button size="small" class="pwd-reminder-action" @click="showDialog = true">
        立即修改
      </el-button>
      <el-button link size="small" class="pwd-reminder-later" @click="dismiss">暂不提醒</el-button>
    </div>
  </transition>

  <ChangePasswordDialog v-model="showDialog" />
</template>

<script setup lang="ts">
/**
 * 初始密码提醒（非阻断）
 *
 * 后端不再拦截未改密用户（原 EnforcePasswordChangeMiddleware 已移除），
 * 这里只做一次轻量提示：悬浮卡片 + 一键打开改密弹窗。
 * 「暂不提醒」按用户持久化，避免每次刷新都打扰；改密成功后密码标记翻转，提醒自动消失。
 * 视觉沿用项目主题变量（theme.css）：卡片底色/边框/阴影/文字色均随浅色与深色主题切换。
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { InfoFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import ChangePasswordDialog from './ChangePasswordDialog.vue'

const route = useRoute()
const auth = useAuthStore()

const showDialog = ref(false)
/** 计数触发 dismissed 重算（localStorage 不是响应式的） */
const dismissedTick = ref(0)

const dismissKey = computed(() => (auth.user?.id ? `pwd_reminder_dismissed:${auth.user.id}` : ''))

const dismissed = computed(() => {
  void dismissedTick.value
  return !!dismissKey.value && localStorage.getItem(dismissKey.value) === '1'
})

const visible = computed(() => {
  const path = route.path
  return (
    auth.user?.password_changed === false &&
    !dismissed.value &&
    !path.startsWith('/login') &&
    !path.startsWith('/change-password')
  )
})

function dismiss() {
  if (dismissKey.value) localStorage.setItem(dismissKey.value, '1')
  dismissedTick.value += 1
}
</script>

<style scoped>
.pwd-reminder {
  position: fixed;
  left: 50%;
  bottom: 76px; /* 高于移动端底部导航（56px + 安全区） */
  transform: translateX(-50%);
  z-index: 1500;
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: calc(100vw - 32px);
  padding: 10px 12px 10px 14px;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  /* 主题阴影 + 一点与顶栏同源的蓝色浮起，避免白底卡片贴在白页面上看不清 */
  box-shadow: var(--shadow-xl), 0 2px 12px rgba(29, 78, 216, 0.08);
  backdrop-filter: blur(10px);
}

/* 图标底座：沿用主题里的警示色，浅色/深色下都不刺眼 */
.pwd-reminder-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  color: var(--accent-orange);
  background: rgba(230, 162, 60, 0.12);
}

.pwd-reminder-text {
  font-size: 13px;
  line-height: 1.4;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 主操作：站内统一的主色渐变按钮（同 TeacherLayout / ChatPanel）
   选择器带上父级类名，确保压过 Element Plus 的 .el-button--small 尺寸规则 */
.pwd-reminder .pwd-reminder-action {
  flex-shrink: 0;
  height: 30px;
  padding: 0 14px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #fff;
  background: linear-gradient(135deg, #409eff, #337ecc);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.28);
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: transparent;
  --el-button-hover-border-color: transparent;
  --el-button-active-bg-color: transparent;
  --el-button-hover-text-color: #fff;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.pwd-reminder .pwd-reminder-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.35);
}

.pwd-reminder .pwd-reminder-later {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.pwd-reminder .pwd-reminder-later:hover {
  color: var(--accent-blue);
}

@media (min-width: 769px) {
  .pwd-reminder {
    bottom: 28px;
  }
}

.pwd-reminder-enter-active,
.pwd-reminder-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.pwd-reminder-enter-from,
.pwd-reminder-leave-to {
  opacity: 0;
  transform: translate(-50%, 8px);
}
</style>