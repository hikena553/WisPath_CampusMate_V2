<template>
  <div class="chat-shell-layout">
    <div v-if="!isMobile" class="sidebar-container" :class="{ collapsed }">
      <Sidebar :role="role" @select="onSelect" @new="onNew" />
    </div>
    <!-- 移动端：侧边栏遮罩 + 滑入 -->
    <template v-if="isMobile">
      <div v-if="mobileSidebarVisible" class="mobile-sidebar-mask" @click="mobileSidebarVisible = false"></div>
      <div class="mobile-sidebar-drawer" :class="{ open: mobileSidebarVisible }">
        <Sidebar :role="role" @select="onSelect" @new="onNew" />
      </div>
    </template>
    <div class="chat-panel-wrap">
      <Transition name="chat-fade" mode="out-in">
        <ChatPanel
          :key="chatKey"
          :role="role"
          :conversation-id="store.activeId"
          :fetching="fetching"
          :show-menu-button="isMobile"
          @toggle-sidebar="mobileSidebarVisible = !mobileSidebarVisible"
        />
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Sidebar from './Sidebar.vue'
import ChatPanel from './ChatPanel.vue'
import { useConversationStore, type Conversation } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useResponsive } from '@/composables/useResponsive'

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher' }>(), { role: 'student' })
const store = props.role === 'teacher' ? useTeacherConversationStore() : useConversationStore()
const agentStore = props.role === 'teacher' ? useTeacherAgentStore() : useAgentStore()
const { isMobile } = useResponsive()
const collapsed = computed(() => store.sidebarCollapsed)
const chatKey = ref(0)
let selecting = false
const fetching = ref(false)
const mobileSidebarVisible = ref(false)

async function onSelect(conv: Conversation) {
  selecting = true
  fetching.value = true
  store.setActive(conv.id)
  await store.fetchMessages(conv.id)
  const msgs = store.messages.map(m => ({
    id: m.id.toString(),
    role: m.role as 'user' | 'assistant',
    content: m.content,
    timestamp: m.timestamp,
  }))
  agentStore.replaceMessages(msgs)
  fetching.value = false
  chatKey.value++
  selecting = false
  if (isMobile.value) {
    mobileSidebarVisible.value = false
  }
}

function onNew() {
  store.setActive(null)
  agentStore.clearMessages()
  chatKey.value++
  if (isMobile.value) {
    mobileSidebarVisible.value = false
  }
}

watch(() => store.activeId, () => {
  if (!selecting) chatKey.value++
})

onMounted(() => {
  store.setActive(null)
  agentStore.clearMessages()
  store.fetchList()
})
</script>

<style scoped>
.chat-shell-layout {
  display: flex; height: 100%;
  background: var(--bg-primary); border-radius: 12px;
  overflow: hidden; box-shadow: var(--shadow-lg);
}

.sidebar-container {
  width: 260px;
  flex-shrink: 0;
}
.sidebar-container.collapsed {
  width: 48px;
}

/* 移动端侧边栏遮罩 */
.mobile-sidebar-mask {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0, 0, 0, 0.35);
  animation: fadeIn 0.15s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* 移动端侧边栏抽屉 */
.mobile-sidebar-drawer {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 280px; z-index: 1001;
  transform: translateX(-100%);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 2px 0 16px rgba(0, 0, 0, 0.1);
}
.mobile-sidebar-drawer.open {
  transform: translateX(0);
}

.chat-panel-wrap {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; background: var(--bg-secondary);
  overflow: hidden;
}

/* 聊天过渡动画 */
.chat-fade-enter-active {
  transition: opacity .15s ease;
}
.chat-fade-leave-active {
  transition: opacity .1s ease;
}
.chat-fade-enter-from {
  opacity: 0;
}
.chat-fade-leave-to {
  opacity: 0;
}
</style>
