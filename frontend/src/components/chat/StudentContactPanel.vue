<template>
  <div class="contact-panel">
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
    <div v-else-if="!tutor" class="no-tutor">暂无辅导员信息</div>
    <template v-else>
      <div style="height: 8px;"></div>
      <div class="tutor-info">
        <el-avatar :size="48">{{ tutor.name[0] }}</el-avatar>
        <div>
          <strong>{{ tutor.name }}</strong>
          <small>辅导员</small>
        </div>
      </div>
      <div class="msg-list" ref="msgListRef">
        <template v-for="item in messageTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
          <div v-if="item.type === 'date'" class="date-separator">
            <span>{{ item.label }}</span>
          </div>
          <div v-else
            :class="['msg-bubble', item.msg.sender_id === userId ? 'mine' : 'theirs']">
            <div class="bubble-text">{{ item.msg.content }}</div>
            <div class="bubble-time">{{ formatTime(item.msg.created_at) }}</div>
          </div>
        </template>
      </div>
      <div class="input-bar">
        <div class="input-container">
          <div class="input-field-wrap">
            <textarea
              ref="textareaRef"
              v-model="newMsg"
              placeholder="输入消息..."
              class="chat-textarea"
              rows="1"
              @input="autoResize"
              @keydown.enter.prevent="sendMsg"
            ></textarea>
          </div>
          <div class="input-actions">
            <button
              type="button"
              :class="['action-icon-btn', { active: speech.isListening.value || recorder.isRecording.value }]"
              @click="toggleMic"
            >
              <el-icon :size="18"><Microphone /></el-icon>
            </button>
            <button
              type="button"
              class="send-btn"
              :disabled="!newMsg.trim()"
              @click="sendMsg"
            >
              <el-icon :size="18"><Top /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getConversations, getMessages, sendMessage, markRead } from '@/api/messages'
import { ElMessage } from 'element-plus'
import { Top, Microphone } from '@element-plus/icons-vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useMediaRecorder } from '@/composables/useMediaRecorder'

const emit = defineEmits<{ read: [] }>()
const auth = useAuthStore()
const userId = auth.user?.id ?? 0
const tutor = ref<{ id: number; name: string; avatar?: string } | null>(null)
const messages = ref<any[]>([])
const newMsg = ref('')
const msgListRef = ref<HTMLDivElement>()
const textareaRef = ref<HTMLTextAreaElement>()
const speech = useSpeechRecognition()
const recorder = useMediaRecorder()
const loading = ref(true)

function toggleMic() {
  if (!speech.isSupported.value && recorder.isSupported.value) {
    if (recorder.isRecording.value) {
      recorder.stop()
    } else {
      recorder.start()
    }
    return
  }
  if (speech.isListening.value) {
    speech.stop()
    if (speech.transcript.value) {
      newMsg.value += speech.transcript.value
    }
  } else {
    speech.start()
  }
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

const messageTimeline = computed(() => {
  const items: Array<{ type: 'date'; date: string; label: string } | { type: 'msg'; msg: any }> = []
  let lastDate = ''
  for (const m of messages.value) {
    const d = getDateStr(m.created_at)
    if (d !== lastDate) {
      items.push({ type: 'date', date: d, label: getDateLabel(m.created_at) })
      lastDate = d
    }
    items.push({ type: 'msg', msg: m })
  }
  return items
})

function parseDate(t: string) {
  let dateStr = t
  if (!dateStr.endsWith('Z') && !dateStr.includes('+') && dateStr.includes('T')) {
    dateStr += 'Z'
  } else if (!dateStr.endsWith('Z') && !dateStr.includes('+', 10)) {
    dateStr += 'Z'
  }
  return new Date(dateStr)
}

function getDateStr(t: string) {
  const d = parseDate(t)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

function getDateLabel(t: string) {
  const date = parseDate(t)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.floor((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

async function loadTutor() {
  if (auth.user?.tutor_id) {
    try {
      const convs: any[] = await getConversations()
      const t = convs.find((c: any) => c.user_id === auth.user!.tutor_id)
      if (t) {
        tutor.value = { id: t.user_id, name: t.user_name, avatar: t.user_avatar || undefined }
      } else {
        tutor.value = { id: auth.user!.tutor_id, name: '辅导员' }
      }
    } catch {
      tutor.value = { id: auth.user!.tutor_id!, name: '辅导员' }
    }
  }
}

async function loadMessages() {
  if (!tutor.value) return
  try {
    messages.value = await getMessages(tutor.value.id)
    await markRead(tutor.value.id)
    emit('read')
    nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' }))
  } catch {}
}

async function sendMsg() {
  if (!newMsg.value.trim() || !tutor.value) return
  try {
    await sendMessage(tutor.value.id, newMsg.value.trim())
    messages.value.push({
      id: Date.now(), sender_id: userId, receiver_id: tutor.value.id,
      content: newMsg.value.trim(), read: true, created_at: new Date().toISOString()
    })
    newMsg.value = ''
    nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' }))
  } catch { ElMessage.error('发送失败') }
}

function formatTime(t: string) {
  if (!t) return ''
  try {
    const date = parseDate(t)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return timeStr
  } catch { return t }
}

onMounted(async () => {
  await loadTutor()
  loading.value = false
  if (tutor.value) loadMessages()
})
</script>

<style scoped>
.contact-panel { display: flex; flex-direction: column; height: 100%; }
.tutor-info { display: flex; align-items: center; gap: 10px; padding: 4px 12px 6px; border-bottom: 1px solid #f0f0f0; }
.tutor-info div { display: flex; flex-direction: column; }
.tutor-info small { color: #999; font-size: 12px; }
.msg-list { flex: 1; overflow-y: auto; padding: 12px 16px; }

/* 日期分隔符 */
.date-separator { text-align: center; margin: 12px 0; }
.date-separator span {
  display: inline-block; padding: 3px 12px; border-radius: 10px;
  font-size: 11px; color: #999; background: rgba(0,0,0,.04);
}

/* 聊天气泡 */
.msg-bubble { margin-bottom: 10px; max-width: 80%; width: fit-content; }
.msg-bubble.mine { margin-left: auto; }
.msg-bubble.theirs { margin-right: auto; }
.bubble-text { padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.5; word-break: break-word; }
.mine .bubble-text { background: #409eff; color: #fff; border-bottom-right-radius: 3px; }
.theirs .bubble-text { background: #f0f4f9; color: #333; border-bottom-left-radius: 3px; }
.bubble-time {
  font-size: 10px; color: #aaa; margin-top: 3px; padding: 0 4px;
  display: flex; align-items: center; gap: 4px;
}
.mine .bubble-time { justify-content: flex-end; }

/* 输入栏 */
.input-bar {
  flex-shrink: 0;
  padding: 12px 16px 16px;
  background: #fff;
}
.input-container {
  background: #fff;
  border-radius: 24px;
  padding: 12px 12px 10px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 12px rgba(0,0,0,.04);
  transition: border-color .2s, box-shadow .2s;
}
.input-container:focus-within {
  border-color: #409eff;
  box-shadow: 0 2px 16px rgba(64,158,255,.12);
}

/* 文本输入框 */
.input-field-wrap { flex: 1; min-width: 0; }
.chat-textarea {
  width: 100%; border: none; background: transparent; outline: none;
  font-size: 15px; font-family: inherit; color: #1f2937; resize: none;
  line-height: 1.5; padding: 4px 6px; min-height: 24px; max-height: 120px;
  overflow-y: auto;
}
.chat-textarea::placeholder { color: #9ca3af; }
.chat-textarea::-webkit-scrollbar { width: 4px; }
.chat-textarea::-webkit-scrollbar-track { background: transparent; }
.chat-textarea::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
.chat-textarea::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

/* 底部操作按钮行 */
.input-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  margin-top: 4px;
  padding: 0 2px;
}

/* 图标按钮（麦克风等） */
.action-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all .15s;
  padding: 0;
}
.action-icon-btn:hover:not(:disabled) {
  background: #f3f4f6;
  color: #374151;
}
.action-icon-btn.active {
  background: rgba(64,158,255,.1);
  color: #409eff;
}

/* 发送按钮 */
.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: #409eff;
  color: #fff;
  cursor: pointer;
  transition: background .15s, transform .1s;
  padding: 0;
  flex-shrink: 0;
  margin-left: auto;
}
.send-btn:hover:not(:disabled) {
  background: #337ecc;
}
.send-btn:active:not(:disabled) {
  transform: scale(.94);
}
.send-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #9ca3af;
  font-size: 14px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.no-tutor { padding: 40px; text-align: center; color: #999; }
</style>
