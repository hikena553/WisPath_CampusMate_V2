<template>
  <div class="butler-chat">
    <!-- 工具条：最新资讯 / 总结对话（钉钉式吸顶操作条） -->
    <div class="butler-toolbar">
      <span class="butler-toolbar-status">
        <span class="butler-dot" :class="{ busy: loading }" />
        {{ statusText }}
      </span>
      <div class="butler-toolbar-actions">
        <button type="button" class="butler-chip" :disabled="loading" @click="pushBriefing(true)">
          <DtIcon name="news" :size="15" /> 最新资讯
        </button>
        <button type="button" class="butler-chip" :disabled="loading || !canSummarize" @click="summarizeConversation">
          <DtIcon name="summarize" :size="15" /> 总结对话
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="listRef" class="butler-list">
      <div v-for="m in messages" :key="m.id" class="butler-row" :class="m.role === 'user' ? 'is-mine' : 'is-theirs'">
        <div v-if="m.role === 'assistant'" class="butler-avatar">
          <img v-if="siteMascot" :src="siteMascot" alt="小绵管家" />
          <DtIcon v-else name="robot" :size="22" />
        </div>
        <div class="butler-col">
          <div v-if="m.kind === 'briefing'" class="butler-bubble is-push">
            <div class="butler-push-head">
              <span class="butler-push-tag">小绵管家 · 自动推送</span>
              <span class="butler-push-time">{{ m.time }}</span>
            </div>
            <p class="butler-push-digest">{{ m.content }}</p>
            <div v-if="m.items && m.items.length" class="butler-news">
              <a
                v-for="it in m.items"
                :key="it.id"
                class="butler-news-item"
                :href="it.link || undefined"
                :target="it.link ? '_blank' : undefined"
                rel="noopener noreferrer"
              >
                <span class="butler-news-title">{{ it.title }}</span>
                <span class="butler-news-meta">
                  <span class="dt-tag">{{ it.source_label }}</span>
                  <span v-if="it.summary" class="butler-news-summary">{{ truncate(it.summary, 56) }}</span>
                  <span v-if="it.published_at" class="butler-news-time">{{ formatShort(it.published_at) }}</span>
                </span>
              </a>
            </div>
          </div>
          <div v-else class="butler-bubble" :class="m.role === 'user' ? 'is-mine' : 'is-theirs'">
            {{ m.content }}
          </div>
          <div v-if="m.role === 'assistant'" class="butler-time">{{ m.time }}</div>
        </div>
        <div v-if="m.role === 'user'" class="butler-avatar is-mine">
          <img v-if="userAvatar" :src="userAvatar" alt="我" />
          <span v-else>{{ userInitial }}</span>
        </div>
      </div>

      <div v-if="loading" class="butler-row is-theirs">
        <div class="butler-avatar">
          <img v-if="siteMascot" :src="siteMascot" alt="小绵管家" />
          <DtIcon v-else name="robot" :size="22" />
        </div>
        <div class="butler-bubble is-theirs butler-typing"><i /><i /><i /></div>
      </div>
    </div>

    <!-- 输入栏 -->
    <div class="butler-input">
      <div class="butler-input-box">
        <textarea
          ref="inputRef"
          v-model="draft"
          class="butler-textarea"
          rows="1"
          placeholder="想了解什么，直接问小绵…"
          @input="autoResize"
          @keydown.enter.exact.prevent="send"
        />
        <button type="button" class="butler-send" :class="{ active: draft.trim() && !loading }"
          :disabled="!draft.trim() || loading" @click="send" aria-label="发送">
          <DtIcon name="send" :size="19" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 小绵管家会话（DingTalk Style）
 *
 * 教师端消息页与学生端消息中心共用的通用能力：
 * - 自动推送最新资讯（/api/butler/briefing，落地为一条「自动推送」消息）
 * - 总结对话内容（/api/butler/summarize）
 * - 与管家自由对话（/api/butler/chat）
 * 视觉沿用钉钉设计令牌（--dt-*）与钉钉风格图标（DtIcon）。
 */
import { computed, nextTick, onMounted, ref } from 'vue'
import DtIcon from '@/components/common/DtIcon.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useAuthStore } from '@/stores/auth'
import {
  getButlerBriefing, butlerChat, butlerSummarize,
  type ButlerFeedItem, type ButlerChatMessage,
} from '@/api/butler'

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher' }>(), { role: 'student' })

const { siteMascot, agentName } = useSiteConfig()
const auth = useAuthStore()

interface LocalMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  kind?: 'text' | 'briefing'
  items?: ButlerFeedItem[]
}

const messages = ref<LocalMessage[]>([])
const draft = ref('')
const loading = ref(false)
const listRef = ref<HTMLElement>()
const inputRef = ref<HTMLTextAreaElement>()
let seq = 0

const userAvatar = computed(() => auth.user?.avatar || '')
const userInitial = computed(() => (auth.userName || '我').slice(0, 1))

const statusText = computed(() => (loading.value ? '小绵正在思考…' : '在线 · 资讯随时推送'))
const canSummarize = computed(() => messages.value.some((m) => m.role === 'user'))

function nowLabel() {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function push(role: 'user' | 'assistant', content: string, extra: Partial<LocalMessage> = {}) {
  messages.value.push({ id: ++seq, role, content, time: nowLabel(), ...extra })
  void scrollToBottom()
}

function truncate(text: string, max: number) {
  const t = (text || '').replace(/\s+/g, ' ').trim()
  return t.length > max ? `${t.slice(0, max)}…` : t
}

function formatShort(iso: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()}`
}

async function scrollToBottom() {
  await nextTick()
  const el = listRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 96)}px`
}

/** 拉取并推送「最新资讯简报」 */
async function pushBriefing(manual = false) {
  if (loading.value) return
  loading.value = true
  try {
    const data = await getButlerBriefing(5)
    push('assistant', data.digest, { kind: 'briefing', items: data.items })
  } catch {
    if (manual) push('assistant', '资讯暂时拉取失败，稍后再试一次吧。')
  } finally {
    loading.value = false
  }
}

/** 总结当前对话内容 */
async function summarizeConversation() {
  if (loading.value) return
  const payload: ButlerChatMessage[] = messages.value
    .filter((m) => m.role === 'user' || (m.role === 'assistant' && m.kind !== 'briefing'))
    .map((m) => ({ role: m.role, content: m.content }))
  if (!payload.some((m) => m.role === 'user')) return
  loading.value = true
  try {
    const res = await butlerSummarize(payload)
    push('assistant', res.reply)
  } catch {
    push('assistant', '这次总结没成功，稍后再试一次吧。')
  } finally {
    loading.value = false
  }
}

/** 发送消息并与管家对话 */
async function send() {
  const text = draft.value.trim()
  if (!text || loading.value) return
  push('user', text)
  draft.value = ''
  await nextTick()
  autoResize()

  const history: ButlerChatMessage[] = messages.value
    .slice(0, -1)
    .filter((m) => m.role === 'user' || (m.role === 'assistant' && m.kind !== 'briefing'))
    .slice(-12)
    .map((m) => ({ role: m.role, content: m.content }))

  loading.value = true
  try {
    const res = await butlerChat(text, history)
    push('assistant', res.reply)
  } catch {
    push('assistant', '我暂时没连上，稍后再问我一次吧。')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const who = props.role === 'teacher' ? '老师' : '同学'
  push(
    'assistant',
    `你好，我是${agentName.value || '小绵'}管家。\n我会自动为你推送校园与行业的最新资讯，也可以帮你总结聊天要点。\n${who}，今天想看点什么呢？`,
  )
  void pushBriefing()
})
</script>

<style scoped>
.butler-chat {
  flex: 1 1 auto;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--dt-bg);
}

/* 工具条 */
.butler-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: 42px;
  padding: 0 14px;
  background: var(--dt-surface);
  border-bottom: 1px solid var(--dt-divider);
  flex-shrink: 0;
}
.butler-toolbar-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--dt-text-tertiary);
}
.butler-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--dt-success); }
.butler-dot.busy { background: var(--dt-warning); animation: butler-pulse 1s infinite; }
@keyframes butler-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.butler-toolbar-actions { display: inline-flex; align-items: center; gap: 8px; }
.butler-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: var(--dt-radius-sm);
  background: var(--dt-primary-soft);
  color: var(--dt-primary-strong);
  font-size: 12.5px;
  cursor: pointer;
  transition: background 0.16s var(--dt-ease);
}
.butler-chip:hover:not(:disabled) { background: #d9ebff; }
.butler-chip:disabled { opacity: 0.45; cursor: not-allowed; }

/* 消息列表：唯一的滚动容器，撑满剩余高度 */
.butler-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: 16px 14px 8px;
}
.butler-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 16px; }
.butler-row.is-mine { flex-direction: row-reverse; }
.butler-avatar {
  width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--dt-primary-soft); color: var(--dt-primary-strong);
  overflow: hidden;
}
.butler-avatar img { width: 100%; height: 100%; object-fit: cover; }
.butler-avatar.is-mine { background: var(--dt-surface-sunken); color: var(--dt-text-secondary); font-size: 14px; font-weight: 600; }
.butler-col { display: flex; flex-direction: column; max-width: min(78%, 460px); }
.butler-row.is-mine .butler-col { align-items: flex-end; }
.butler-time { font-size: 11px; color: var(--dt-text-quiet); margin-top: 4px; padding: 0 4px; }

.butler-bubble { padding: 10px 14px; border-radius: var(--dt-radius-bubble); font-size: 15px; line-height: 1.55; word-break: break-word; white-space: pre-wrap; }
.butler-bubble.is-mine { background: var(--dt-primary); color: #fff; border-bottom-right-radius: var(--dt-radius-xs); }
.butler-bubble.is-theirs { background: var(--dt-surface); color: var(--dt-text); border-bottom-left-radius: var(--dt-radius-xs); box-shadow: var(--dt-shadow-1); }

/* 自动推送（资讯简报）气泡 */
.butler-bubble.is-push { width: 100%; background: var(--dt-surface); border: 1px solid var(--dt-divider); border-radius: var(--dt-radius); border-bottom-left-radius: var(--dt-radius-xs); box-shadow: var(--dt-shadow-1); padding: 12px 14px; }
.butler-push-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.butler-push-tag { font-size: 11.5px; font-weight: 600; color: var(--dt-primary-strong); background: var(--dt-primary-soft); padding: 2px 8px; border-radius: var(--dt-radius-xs); }
.butler-push-time { font-size: 11px; color: var(--dt-text-quiet); }
.butler-push-digest { margin: 0; font-size: 14.5px; line-height: 1.6; color: var(--dt-text); white-space: pre-wrap; }
.butler-news { margin-top: 10px; border-top: 1px solid var(--dt-divider); }
.butler-news-item { display: flex; flex-direction: column; gap: 4px; padding: 10px 2px; border-bottom: 1px solid var(--dt-divider); text-decoration: none; }
.butler-news-item:last-child { border-bottom: none; }
.butler-news-item:active { background: var(--dt-hover); }
.butler-news-title { font-size: 14px; font-weight: 500; color: var(--dt-text); line-height: 1.45; }
.butler-news-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.butler-news-summary { flex: 1; min-width: 0; font-size: 12.5px; color: var(--dt-text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.butler-news-time { font-size: 11px; color: var(--dt-text-quiet); flex-shrink: 0; }

/* 输入中 */
.butler-typing { display: inline-flex; align-items: center; gap: 4px; min-height: 20px; }
.butler-typing i { width: 6px; height: 6px; border-radius: 50%; background: var(--dt-text-quiet); animation: butler-typing 1.2s infinite; }
.butler-typing i:nth-child(2) { animation-delay: 0.15s; }
.butler-typing i:nth-child(3) { animation-delay: 0.3s; }
@keyframes butler-typing { 0%, 60%, 100% { transform: translateY(0); opacity: 0.5; } 30% { transform: translateY(-3px); opacity: 1; } }

/* 输入栏 */
.butler-input { flex-shrink: 0; padding: 8px 14px; background: var(--dt-surface); border-top: 1px solid var(--dt-divider); }
.butler-input-box { display: flex; align-items: flex-end; gap: 8px; background: var(--dt-bg); border-radius: 22px; padding: 6px 6px 6px 14px; }
.butler-textarea {
  flex: 1; border: none; background: transparent; outline: none; resize: none;
  font-family: inherit; font-size: 15px; line-height: 1.5; color: var(--dt-text);
  padding: 6px 0; min-height: 22px; max-height: 96px; overflow-y: auto;
}
.butler-textarea::placeholder { color: var(--dt-text-quiet); }
.butler-textarea::-webkit-scrollbar { width: 0; }
.butler-send {
  width: 34px; height: 34px; border-radius: 50%; border: none; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--dt-surface-sunken); color: var(--dt-text-tertiary);
  cursor: not-allowed; transition: background 0.18s var(--dt-ease), color 0.18s var(--dt-ease);
}
.butler-send.active { background: var(--dt-primary); color: #fff; cursor: pointer; }
.butler-send.active:active { background: var(--dt-primary-press); }

@media (min-width: 768px) {
  .butler-list { padding: 20px 24px 10px; }
  .butler-input { padding: 10px 24px; }
}
</style>