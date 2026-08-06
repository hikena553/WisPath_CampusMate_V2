<template>
  <div class="agent-page">
    <ChatPanel />
  </div>
</template>

<script setup lang="ts">
import ChatPanel from '@/components/agent/ChatPanel.vue'
</script>

<style scoped>
.agent-page {
  height: 100%;
  overflow: hidden;
}
</style>
