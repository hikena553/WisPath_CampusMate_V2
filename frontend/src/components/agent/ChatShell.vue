<template>
  <div class="chat-shell-layout">
    <div v-if="!isMobile" class="sidebar-container" :class="{ collapsed }">
      <Sidebar :role="role" @select="onSelect" @new="onNew" />
    </div>
    <!-- 移动端：侧边栏遮罩 + 滑入 -->
    <template v-if="isMobile">
      <div v-if="mobileSidebarVisible" class="mobile-sidebar-mask" @click="mobileSidebarVisible = false"></div>
      <div class="mobile-sidebar-drawer" :class="{ open: mobileSidebarVisible }">
        <Sidebar :role="role" @select="onSelect" @new="onNew" @close="mobileSidebarVisible = false" />
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
          @conversation-removed="onConversationRemoved"
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

/** 当前对话被删除/归档（移动端操作面板触发）：切到下一个对话，没有则回到新对话 */
function onConversationRemoved() {
  const next = store.list[0]
  if (next) onSelect(next)
  else onNew()
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

/* 移动端侧边栏遮罩
   z-index 需高于 MobileTabBar(1000)：否则遮罩不会压暗底部导航，
   底部 tab 会以"亮着且可点"的状态浮在抽屉之上，看起来像层级穿帮 */
.mobile-sidebar-mask {
  position: fixed; inset: 0; z-index: 1400;
  background: rgba(15, 23, 42, 0.42);
  -webkit-backdrop-filter: blur(3px);
  backdrop-filter: blur(3px);
  animation: fadeIn 0.18s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* 移动端侧边栏抽屉：占满大部分屏宽，给会话标题/阶段胶囊留出空间 */
.mobile-sidebar-drawer {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 86vw; max-width: 340px; z-index: 1401;
  transform: translateX(-100%);
  transition: transform 0.24s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 2px 0 24px rgba(15, 23, 42, 0.18);
  border-radius: 0 16px 16px 0;
  overflow: hidden;
}
.mobile-sidebar-drawer.open {
  transform: translateX(0);
}

.chat-panel-wrap {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; background: var(--bg-secondary);
  overflow: hidden;
}

/* 禁用聊天过渡动画 */
.chat-fade-enter-active,
.chat-fade-leave-active {
  transition: none !important;
}
.chat-fade-enter-from,
.chat-fade-leave-to {
  opacity: 1;
}
</style>
