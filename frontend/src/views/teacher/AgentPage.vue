<template>
  <div class="agent-page">
    <ChatShell role="teacher" />
  </div>
</template>

<script setup lang="ts">
import ChatShell from '@/components/agent/ChatShell.vue'
</script>

<style scoped>
.agent-page { 
  height: 100%; 
  display: flex; 
  flex-direction: column; 
  overflow: hidden;
}
</style>
