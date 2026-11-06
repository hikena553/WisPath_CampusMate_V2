<template>
  <router-view />
  <!-- 初始密码提醒（非阻断）：未改密用户在任何页面右下角看到提示，可一键改密 -->
  <PasswordChangeReminder />
</template>

<script setup lang="ts">
import { watchEffect } from 'vue'
import PasswordChangeReminder from '@/components/common/PasswordChangeReminder.vue'
import { useVisualViewport } from '@/composables/useVisualViewport'

/* 键盘可见区：写进 CSS 变量，供登录 / 注册 / 找回密码等整屏页在移动端缩到键盘上方。
   这些页面是 fixed 整屏层，键盘弹出时 WebView 只缩 visualViewport，页面本身不会变矮，
   不处理的话表单底部和提交按钮会被键盘盖住。
   值要按 --app-zoom（#app 的移动端整体缩放比）折算，否则整屏层会大出 6%。 */
const { offsetTop, height, keyboardOpen } = useVisualViewport()

watchEffect(() => {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  if (!keyboardOpen.value || height.value <= 0) {
    root.style.removeProperty('--auth-vh')
    root.style.removeProperty('--auth-vtop')
    return
  }
  const raw = parseFloat(getComputedStyle(root).getPropertyValue('--app-zoom'))
  const zoom = Number.isFinite(raw) && raw > 0 ? raw : 1
  root.style.setProperty('--auth-vh', height.value / zoom + 'px')
  root.style.setProperty('--auth-vtop', offsetTop.value / zoom + 'px')
})
</script>
