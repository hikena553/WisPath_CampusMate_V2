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
        popper-class="pet-select-dropdown"
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
  /* 面板自身的字号基准：小窗外是浏览器默认 16px，
     Element Plus 的选择器等组件会继承它，在 11~13px 的小窗里显得明显偏大 */
  font-size: 12.5px;
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
  /* 标题栏即悬浮窗拖拽手柄（指针事件由 DesktopPet 处理）：
     给出「可拖动」的鼠标形态，并屏蔽触摸滚动，保证触屏上也能拖动面板 */
  cursor: move;
  touch-action: none;
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
/* 选择器内部再显式收一次：占位文案与展开箭头都要跟小窗同级（12.5px / 12px） */
.pet-conv :deep(.el-select__wrapper) { min-height: 24px; font-size: 12.5px; padding: 0 8px; }
.pet-conv :deep(.el-select__caret) { font-size: 12px; }
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

/* ── 小窗适配 ──────────────────────────────────────────────
   ChatPanel 是按整页设计的：消息行左右各留 140px、正文 14~15px、图标按钮 32~34px、
   欢迎语整体上移 -80px。直接塞进 360×520 的桌宠面板会横向溢出（气泡被裁）、
   欢迎语顶部被裁掉。这里把整页尺度统一收敛到小窗尺度。
   覆盖全部限定在 .pet-body 内，不影响智能体页面里的原样渲染。 */
.pet-body :deep(.chat-modern) { height: 100%; }

/* 欢迎语：去掉整页的负外边距与超大吉祥物，避免小窗里被顶部裁掉 */
.pet-body :deep(.welcome-content) { padding: 8px 12px; margin: 0 auto; max-width: none; }
.pet-body :deep(.welcome-glow) { width: 260px; height: 260px; }
.pet-body :deep(.ai-character .mc-scene) { width: 92px; height: 96px; }
.pet-body :deep(.ai-character .mc-glow) { width: 76px; height: 76px; }
.pet-body :deep(.ai-character .mc-img) { width: 76px; height: 76px; }
.pet-body :deep(.welcome-greeting h1) { font-size: 14px; }
.pet-body :deep(.welcome-greeting p) { font-size: 11px; margin-bottom: 6px; }

/* 消息区：整页的 140px 左右缩进 + 760px 限宽会把气泡挤出 360px 可视区 */
.pet-body :deep(.msg-row),
.pet-body :deep(.msg-row.user) {
  max-width: none;
  margin-left: 0;
  margin-right: 0;
  padding: 0 10px;
  gap: 6px;
}
.pet-body :deep(.msg-bubble-col) { max-width: 92%; }
.pet-body :deep(.msg-row.assistant .msg-bubble-col) { width: 92%; }
.pet-body :deep(.bubble) { font-size: 13px; padding: 8px 11px; border-radius: 14px; }
.pet-body :deep(.bubble-image img) { max-width: 100%; }
.pet-body :deep(.thinking-bubble) { padding: 8px 12px; }
.pet-body :deep(.msg-code-block) { font-size: 12px; padding: 8px; }
.pet-body :deep(.msg-table) { font-size: 12px; }
.pet-body :deep(.msg-th),
.pet-body :deep(.msg-td) { padding: 4px 6px; }
.pet-body :deep(.messages.scrolling) { padding: 8px 0; }

/* 为你推荐 / 回到最新：贴着小窗宽度排布。
   整页里推荐区是绝对定位（贴在输入栏正上方），在 300px 高的消息区里会悬空压住欢迎语；
   小窗里改为正常占位（消息区下方、输入栏上方），互不遮挡。 */
.pet-body :deep(.recommend-bar) { position: static; flex-shrink: 0; padding: 0 10px 6px; }
.pet-body :deep(.recommend-title) { font-size: 11px; padding-left: 4px; margin-bottom: 3px; max-width: none; }
.pet-body :deep(.recommend-list) { max-width: none; padding-left: 4px; gap: 3px; }
.pet-body :deep(.recommend-item) { font-size: 11.5px; padding: 3px 9px; }
.pet-body :deep(.scroll-bottom-btn) { height: 26px; padding: 0 10px; font-size: 11px; }

/* 输入栏：正文、图标与按钮统一收小，保证一行放得下全部操作 */
.pet-body :deep(.input-bar) { padding: 6px 8px; }
.pet-body :deep(.input-container) { max-width: none; border-radius: 16px; padding: 4px 10px; }
.pet-body :deep(.chat-textarea) { font-size: 13px; max-height: 96px; padding: 5px 4px 0; }
.pet-body :deep(.char-counter) { font-size: 10px; }
.pet-body :deep(.input-actions) { gap: 4px; }
.pet-body :deep(.toggle-btn) { padding: 4px 8px; font-size: 11px; gap: 4px; }
.pet-body :deep(.toggle-icon),
.pet-body :deep(.deep-think-icon),
.pet-body :deep(.essence-icon) { width: 12px; height: 12px; }
.pet-body :deep(.action-icon-btn) { width: 26px; height: 26px; }
/* el-icon 的 size 是内联 font-size，需 !important 才能随小窗收小 */
.pet-body :deep(.action-icon-btn .el-icon),
.pet-body :deep(.send-btn .el-icon) { font-size: 15px !important; }
.pet-body :deep(.send-btn) { width: 28px; height: 28px; }

/* 待发送文件预览：小窗里右上方不再占据半屏 */
.pet-body :deep(.pending-files-corner) { top: 2px; right: 2px; padding: 6px; gap: 4px; }
</style>

<!-- 会话下拉弹层：teleport 到 body，上面的作用域样式够不到，
     这里只靠 popper-class 限定在桌宠面板的这一个选择器上。
     Element Plus 默认 14px 字号 / 34px 行高，在 360px 宽的小窗里偏大。 -->
<style>
.pet-select-dropdown .el-select-dropdown__item { height: 28px; line-height: 28px; font-size: 12.5px; padding: 0 12px; }
.pet-select-dropdown .el-select-dropdown__empty { padding: 8px 0; font-size: 12px; }
</style>
