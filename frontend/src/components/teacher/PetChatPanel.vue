<template>
  <section class="pet-panel" @keydown.esc="emit('close')">
    <header class="pet-head">
      <img :src="siteMascot" class="pet-head-logo" alt="" />
      <div class="pet-head-text">
        <strong>{{ agentName }}</strong>
        <span>直接说需求，我来办</span>
      </div>
      <button type="button" class="pet-head-btn" aria-label="收起" @click="emit('close')">
        <el-icon :size="14"><Minus /></el-icon>
      </button>
    </header>

    <!-- 会话切换：与智能体页共用同一组会话，切换后两边同步 -->
    <div class="pet-conv">
      <el-select
        :model-value="convStore.activeId ?? undefined"
        size="small"
        placeholder="新对话"
        class="pet-conv-select"
        @change="onSelect"
      >
        <el-option
          v-for="c in convStore.list"
          :key="c.id"
          :label="c.title || '新对话'"
          :value="c.id"
        />
      </el-select>
      <button type="button" class="pet-conv-new" @click="onNew">新对话</button>
    </div>

    <!-- 快捷指令：一键把常见诉求发给智能体，由智能体调用工具执行 -->
    <div class="pet-chips">
      <button
        v-for="q in quickAsks"
        :key="q"
        type="button"
        class="pet-chip"
        :disabled="fetching"
        @click="ask(q)"
      >
        {{ q }}
      </button>
    </div>

    <div class="pet-body">
      <ChatPanel
        ref="chatRef"
        :key="chatKey"
        role="teacher"
        :conversation-id="convStore.activeId"
        :fetching="fetching"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Minus } from '@element-plus/icons-vue'
import ChatPanel from '@/components/agent/ChatPanel.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useTeacherConversationStore, type Conversation } from '@/stores/teacherConversation'
import { useTeacherAgentStore } from '@/stores/teacherAgent'

const emit = defineEmits<{ close: [] }>()

const { siteMascot, agentName } = useSiteConfig()
const convStore = useTeacherConversationStore()
const agentStore = useTeacherAgentStore()

const chatRef = ref<InstanceType<typeof ChatPanel> | null>(null)
const chatKey = ref(0)
const fetching = ref(false)

/** 快捷指令：都是「让智能体去办事」的口语化表达，与移动端首页常用功能一一对应 */
const quickAsks = [
  '今天有哪些待审批',
  '帮我看下高危预警',
  '写一条班级公告',
]

/**
 * 切换会话：与 AgentPage 的 ChatShell 保持同一套动作
 * （setActive → fetchMessages → 替换消息 → chatKey++ 触发面板重挂载）。
 */
async function onSelect(id: number) {
  const conv = convStore.list.find((c: Conversation) => c.id === id)
  if (!conv || conv.id === convStore.activeId) return
  fetching.value = true
  convStore.setActive(conv.id)
  await convStore.fetchMessages(conv.id)
  agentStore.replaceMessages(
    convStore.messages.map((m) => ({
      id: m.id.toString(),
      role: m.role as 'user' | 'assistant',
      content: m.content,
      timestamp: m.timestamp,
    })),
  )
  fetching.value = false
  chatKey.value++
}

function onNew() {
  convStore.setActive(null)
  agentStore.clearMessages()
  chatKey.value++
}

async function ask(text: string) {
  await chatRef.value?.sendText(text)
}

/**
 * 仅拉取会话列表（供面板顶部的会话下拉使用）。
 * 刻意不在此处 setActive(null) / clearMessages()：桌宠挂在布局层，
 * 若在挂载时重置共享 store，会误清智能体页正在进行的会话。
 */
onMounted(() => {
  convStore.fetchList()
})
</script>

<style scoped>
/* 桌宠对话面板：360×520 的紧凑小窗，复用 ChatPanel 全能力（含工具调用） */
.pet-panel {
  display: flex;
  flex-direction: column;
  width: 360px;
  height: 520px;
  background: #fff;
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-3);
  overflow: hidden;
}

.pet-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--tui-hairline);
  flex-shrink: 0;
}
.pet-head-logo { width: 26px; height: 26px; object-fit: contain; flex-shrink: 0; }
.pet-head-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.pet-head-text strong { font-size: 13px; color: var(--tui-text); }
.pet-head-text span { font-size: 11px; color: var(--tui-text-quiet); }
.pet-head-btn {
  width: 24px; height: 24px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--tui-border-strong); border-radius: 50%;
  background: #fff; color: var(--tui-text-tertiary); cursor: pointer;
}
.pet-head-btn:hover { background: var(--tui-surface-muted); }

.pet-conv {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  flex-shrink: 0;
}
.pet-conv-select { flex: 1; min-width: 0; }
.pet-conv-new {
  flex-shrink: 0;
  height: 24px; padding: 0 8px;
  border: 1px solid var(--tui-border-strong); border-radius: 999px;
  background: #fff; color: var(--tui-text-secondary);
  font-family: inherit; font-size: 11.5px; cursor: pointer;
}
.pet-conv-new:hover { background: var(--tui-surface-muted); }

.pet-chips {
  display: flex; align-items: center; gap: 6px;
  padding: 0 10px 8px;
  overflow-x: auto;
  scrollbar-width: none;
  flex-shrink: 0;
}
.pet-chips::-webkit-scrollbar { display: none; }
.pet-chip {
  flex: 0 0 auto;
  height: 24px; padding: 0 9px;
  border: 1px solid var(--tui-border-strong); border-radius: 999px;
  background: var(--tui-surface-muted); color: var(--tui-text-secondary);
  font-family: inherit; font-size: 11.5px; white-space: nowrap; cursor: pointer;
}
.pet-chip:hover:not(:disabled) { background: var(--tui-brand-soft); color: var(--tui-brand-strong); border-color: var(--tui-brand-soft); }
.pet-chip:disabled { opacity: 0.5; cursor: not-allowed; }

.pet-body { flex: 1; min-height: 0; overflow: hidden; }

/* ChatPanel 原本为整页设计（height:100vh），塞进 360×520 小窗需收敛尺寸；
   所有覆盖都限定在 .pet-body 内，不影响智能体页面里的原样渲染。 */
.pet-body :deep(.chat-modern) { height: 100%; }
.pet-body :deep(.welcome-content) { padding: 18px 14px; }
.pet-body :deep(.ai-character .mc-img) { width: 92px; height: 92px; }
.pet-body :deep(.welcome-greeting h1) { font-size: 16px; }
.pet-body :deep(.welcome-greeting p) { font-size: 12px; margin-bottom: 14px; }
.pet-body :deep(.input-bar) { padding: 8px 10px; }
.pet-body :deep(.messages.scrolling) { padding: 8px 0; }
</style>
