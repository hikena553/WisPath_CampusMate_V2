<template>
  <router-view />
  <!-- 初始密码提醒（非阻断）：未改密用户在任何页面右下角看到提示，可一键改密 -->
  <PasswordChangeReminder />
</template>

<script setup lang="ts">
import PasswordChangeReminder from '@/components/common/PasswordChangeReminder.vue'
</script>