<template>
  <div class="chat-modern">
    <!-- 移动端菜单按钮 -->
    <el-button v-if="showMenuButton" text circle class="menu-toggle" @click="emit('toggleSidebar')">
      <el-icon :size="20"><Operation /></el-icon>
    </el-button>
    <!-- Pending Files Preview (top-right) -->
    <div v-if="pendingFiles.length > 0" class="pending-files-corner">
      <el-tooltip content="清空全部" placement="bottom">
        <button type="button" class="clear-all-btn" @click="pendingFiles = []">
          <el-icon :size="14"><Delete /></el-icon> 清空文件
        </button>
      </el-tooltip>
      <template v-if="pendingFiles.length <= 3">
        <el-tag
          v-for="(file, idx) in pendingFiles"
          :key="idx"
          closable
          :type="getFileTypeTag(file.name)"
          size="small"
          class="file-tag-clickable"
          @close="removePendingFile(idx)"
          @click="previewPendingFile(file)"
        >
          <el-icon style="margin-right:4px;vertical-align:-2px"><Document /></el-icon>
          {{ file.name }}
        </el-tag>
      </template>
      <template v-else>
        <el-tag
          v-for="(file, idx) in pendingFiles.slice(0, 3)"
          :key="idx"
          closable
          :type="getFileTypeTag(file.name)"
          size="small"
          class="file-tag-clickable"
          @close="removePendingFile(idx)"
          @click="previewPendingFile(file)"
        >
          <el-icon style="margin-right:4px;vertical-align:-2px"><Document /></el-icon>
          {{ file.name }}
        </el-tag>
        <el-dropdown trigger="click" @command="handleOverflowCommand" popper-class="file-overflow-dropdown">
          <el-tag type="info" size="small" class="overflow-tag" effect="plain">
            +{{ pendingFiles.length - 3 }} 个文件
            <el-icon style="margin-left:2px;vertical-align:-2px"><ArrowDown /></el-icon>
          </el-tag>
          <template #dropdown>
            <el-dropdown-menu class="file-dropdown-menu">
              <el-dropdown-item
                v-for="(file, idx) in pendingFiles.slice(3)"
                :key="idx + 3"
                :command="idx + 3"
                class="file-dropdown-item"
              >
                <el-tag
                  :type="getFileTypeTag(file.name)"
                  size="small"
                  class="dropdown-file-tag"
                  @click.stop="previewPendingFile(file)"
                >
                  <el-icon style="margin-right:4px;vertical-align:-2px"><Document /></el-icon>
                  {{ file.name }}
                </el-tag>
                <el-icon
                  class="dropdown-remove"
                  @click.stop="removePendingFile(idx + 3)"
                ><Close /></el-icon>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </div>

    <div class="messages" ref="msgRef" :class="{ scrolling: store.messages.length > 0 }">

      <!-- Welcome Screen -->
      <div v-if="store.messages.length === 0" class="welcome">
        <div class="welcome-glow"></div>
        <div class="welcome-content">
          <div class="ai-character">
            <MianCharacter :state="charState" :bubble="charBubble" />
          </div>
          <div class="welcome-greeting">
            <h1>你好，我是<span class="gradient-text">绵小城</span></h1>
            <p>你的校园智能管家，所有事情直接跟我聊，一站式办结</p>
          </div>

          <!-- Quick Action Cards -->
          <div class="quick-grid">
            <div class="quick-card" v-for="a in actions" :key="a.label" @click="quickSend(a.example)">
              <div class="qc-icon" :style="{ background: a.color + '12', color: a.color }">{{ a.icon }}</div>
              <div class="qc-body">
                <strong>{{ a.label }}</strong>
                <small>{{ a.desc }}</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages -->
      <template v-for="(msg, _i) in store.messages" :key="msg.id">
        <div :class="['msg-row', msg.role]">
          <div v-if="msg.role === 'assistant'" class="msg-avatar-col">
            <MianCharacter state="idle" mini />
          </div>
          <div class="msg-bubble-col">
            <div :class="['bubble', msg.role]">
              <!-- Render images inline -->
              <div v-if="isImageMessage(msg)" class="bubble-image">
                <img :src="extractImageUrl(msg)" @click="previewImage = extractImageUrl(msg)" />
              </div>
              <div v-if="msg.content || msg.role === 'user'" class="msg-text">
                <DeepThinking v-if="msg.role === 'assistant' && msg.thinking" :thinking="msg.thinking" />
                <span v-html="renderMarkdown(msg.content)"></span>
              </div>
              <div v-else class="thinking-bubble">
                <span class="typing-dot" v-for="d in 3" :key="d" :style="{ animationDelay: (d * 0.15) + 's' }"></span>
              </div>
              <div v-if="msg.suggestions?.length" class="suggestions">
                <el-tag
                  v-for="s in msg.suggestions"
                  :key="s.text"
                  class="suggestion-tag"
                  effect="plain"
                  @click="handleSuggestion(s)"
                >{{ s.text }}</el-tag>
              </div>
            </div>
            <div class="msg-footer">
              <div class="msg-time">{{ formatTime(msg.timestamp) }}</div>
              <div class="msg-actions">
                <el-tooltip content="复制" placement="top">
                  <el-button text class="action-btn" @click="copyMessage(msg.content)">
                    <el-icon :size="14"><CopyDocument /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="msg.role === 'user'" content="编辑并回退" placement="top">
                  <el-button text class="action-btn" @click="editAndRevert(msg.content, _i)">
                    <el-icon :size="14"><EditPen /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </template>


    </div>

    <!-- Image Preview Overlay -->
    <Teleport to="body">
      <Transition name="preview-fade">
        <div v-if="previewImage" class="image-overlay" @click="closePreview">
          <Transition name="preview-scale" appear>
            <img :src="previewImage" class="preview-img" />
          </Transition>
          <button class="preview-close-btn" @click.stop="closePreview">
            <el-icon :size="20"><Close /></el-icon>
          </button>
        </div>
      </Transition>
    </Teleport>

    <!-- Input Bar -->
    <div class="input-bar">
      <div class="input-container">
        <!-- Feature Toggles -->
        <div class="feature-toggles">
          <button
            type="button"
            :class="['toggle-btn', { active: deepThinkEnabled }]"
            :disabled="loading"
            @click="deepThinkEnabled = !deepThinkEnabled"
          >
            <el-icon class="toggle-icon"><MagicStick /></el-icon>
            深度思考
          </button>
        </div>

        <!-- Text Input -->
        <div class="input-field-wrap">
          <textarea
            ref="textareaRef"
            v-model="input"
            :disabled="loading"
            placeholder="给绵小城发消息..."
            class="chat-textarea"
            rows="1"
            @input="autoResize"
            @keydown.enter.prevent="send"
          ></textarea>
          <div v-if="inputCharCount > 0" class="char-counter" :class="{ warn: charRatio > 0.9, over: isOverLimit }">
            {{ inputCharCount.toLocaleString() }} / {{ MAX_INPUT_CHARS.toLocaleString() }}
          </div>
        </div>

        <!-- Bottom Actions -->
        <div class="input-actions">
          <!-- Upload buttons -->
          <el-dropdown v-if="isMobile" trigger="click" @command="handleUploadCommand" :disabled="loading">
            <button type="button" class="action-icon-btn" :disabled="loading">
              <el-icon :size="18"><Paperclip /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="file">
                  <el-icon style="margin-right:4px"><Document /></el-icon>文件
                </el-dropdown-item>
                <el-dropdown-item command="image">
                  <el-icon style="margin-right:4px"><Picture /></el-icon>图片
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <template v-else>
            <el-tooltip content="上传文件" placement="top">
              <button type="button" class="action-icon-btn" :disabled="loading" @click="triggerUpload">
                <el-icon><Paperclip /></el-icon>
              </button>
            </el-tooltip>
            <el-tooltip content="上传图片" placement="top">
              <button type="button" class="action-icon-btn" :disabled="loading" @click="triggerImageUpload">
                <el-icon><Picture /></el-icon>
              </button>
            </el-tooltip>
          </template>
          <input ref="fileInputRef" type="file" multiple accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.zip,.rar" style="display:none" @change="onFileSelected" />
          <input ref="imageInputRef" type="file" multiple accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.svg" style="display:none" @change="onImageSelected" />

          <!-- Microphone -->
          <el-tooltip :content="micTooltip" placement="top">
            <button
              type="button"
              :class="['action-icon-btn', { active: speech.isListening.value || recorder.isRecording.value }]"
              :disabled="loading || (!speech.isSupported.value && !recorder.isSupported.value)"
              @click="toggleMic"
            >
              <el-icon :size="18"><Microphone /></el-icon>
            </button>
          </el-tooltip>

          <!-- Send Button -->
          <button
            type="button"
            :class="['send-btn', { loading }]"
            :disabled="loading"
            @click="send"
          >
            <el-icon v-if="!loading" :size="18"><Promotion /></el-icon>
            <span v-else class="send-spinner"></span>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUpdated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useConversationStore } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { sendChatMessage } from '@/api/agent'
import { getToken } from '@/utils/token'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import type { ChatMessage, Suggestion } from '@/types'
import {
  Promotion, Paperclip, Picture, Document, Microphone, CopyDocument, EditPen, Operation, MagicStick, ArrowDown, Close, Delete,
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import MianCharacter from './MianCharacter.vue'
import DeepThinking from './DeepThinking.vue'

const { isMobile } = useResponsive()

const charState = ref<'idle' | 'thinking' | 'speaking'>('idle')
const charBubble = ref('')
const deepThinkEnabled = ref(false)
const MAX_INPUT_CHARS = 8000

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher'; conversationId?: number | null; fetching?: boolean; showMenuButton?: boolean }>(), { role: 'student', fetching: false, showMenuButton: false })
const emit = defineEmits<{ toggleSidebar: [] }>()
const store = props.role === 'teacher' ? useTeacherAgentStore() : useAgentStore()
const convStore = props.role === 'teacher' ? useTeacherConversationStore() : useConversationStore()
const router = useRouter()
const input = ref('')
const msgRef = ref<HTMLElement>()
const textareaRef = ref<HTMLTextAreaElement>()
const loading = ref(false)
const previewImage = ref('')
const speech = useSpeechRecognition()
const recorder = useMediaRecorder()
const editingOriginal = ref<string | null>(null)

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

watch(input, () => {
  nextTick(autoResize)
})

watch(() => recorder.error.value, (val) => {
  if (val && val !== '转写失败' && val !== '网络错误' && val !== '无法访问麦克风' && val !== '录音失败') {
    input.value += val
  }
})

const micTooltip = computed(() => {
  if (!speech.isSupported.value && recorder.isSupported.value) {
    if (recorder.transcribing.value) return '转写中...'
    if (recorder.isRecording.value) return '录音中...'
    return '录音输入'
  }
  if (!speech.isSupported.value) return '当前浏览器不支持语音输入'
  if (speech.isListening.value) return '正在聆听...'
  return '语音输入'
})

const studentActions = [
  { icon: '📅', label: '请假申请', desc: '比赛、病假、事假直接说', color: '#409eff', example: '下周二参加ACM区域赛需要请假三天，从5月26号到5月28号' },
  { icon: '📝', label: '记录成长', desc: '获奖/比赛自动写入档案', color: '#67c23a', example: '我获得了挑战杯省赛二等奖，主办方是教育厅，级别是省级' },
  { icon: '📚', label: '查课表', desc: '看看今天上什么课', color: '#e6a23c', example: '查一下这周一的课表' },
  { icon: '📊', label: '查成绩', desc: '查看各科成绩和GPA', color: '#f56c6c', example: '帮我查一下这个学期的成绩和绩点' },
  { icon: '📢', label: '官网通知', desc: '教务处最新公告', color: '#b37feb', example: '查一下教务处发布了哪些最新通知' },
  { icon: '🏫', label: '校园知识', desc: '办事流程、规章制度', color: '#909399', example: '怎么申请在校证明？需要准备哪些材料？' },
]

const teacherActions = [
  { icon: '📋', label: '请假审批', desc: '查看待批请假申请', color: '#409eff', example: '查看当前待审批的请假' },
  { icon: '⚠️', label: '预警管理', desc: '查看学生心理预警', color: '#f56c6c', example: '查看当前预警列表' },
  { icon: '👥', label: '学生档案', desc: '查看名下学生成长', color: '#67c23a', example: '查看所有学生档案' },
  { icon: '🆘', label: '危机干预', desc: '记录干预措施', color: '#e6a23c', example: '记录危机干预' },
  { icon: '📢', label: '官网通知', desc: '教务处最新公告', color: '#b37feb', example: '查一下教务处发布了哪些最新通知' },
  { icon: '🏫', label: '校园知识', desc: '办事流程、规章制度', color: '#909399', example: '奖助学金的申请流程是什么？' },
]

const actions = computed(() => props.role === 'teacher' ? teacherActions : studentActions)

const inputCharCount = computed(() => input.value.length)
const isOverLimit = computed(() => inputCharCount.value > MAX_INPUT_CHARS)
const charRatio = computed(() => Math.min(inputCharCount.value / MAX_INPUT_CHARS, 1))

const fileInputRef = ref<HTMLInputElement>()
const imageInputRef = ref<HTMLInputElement>()
const pendingFiles = ref<File[]>([])
const pendingImagePreview = ref('')
let uploadedFileUrl = ''

function getFileTypeTag(name: string) {
  const n = name.toLowerCase()
  if (n.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg)$/)) return 'success'
  return 'warning'
}

function isDuplicate(file: File): boolean {
  return pendingFiles.value.some(f => f.name === file.name && f.size === file.size)
}

function triggerUpload() { fileInputRef.value?.click() }
function triggerImageUpload() { imageInputRef.value?.click() }
function handleUploadCommand(cmd: string) {
  if (cmd === 'file') triggerUpload()
  else if (cmd === 'image') triggerImageUpload()
}

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
      input.value += speech.transcript.value
    }
  } else {
    speech.start()
  }
}

async function onFileSelected(e: Event) {
  const t = e.target as HTMLInputElement
  if (!t.files?.length) return
  for (const file of Array.from(t.files)) {
    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning(`"${file.name}" 超过 10MB，已跳过`)
      continue
    }
    if (isDuplicate(file)) {
      ElMessage.warning(`"${file.name}" 已存在，已跳过`)
      continue
    }
    pendingFiles.value.push(file)
  }
  t.value = ''
}

async function onImageSelected(e: Event) {
  const t = e.target as HTMLInputElement
  if (!t.files?.length) return
  for (const file of Array.from(t.files)) {
    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning(`"${file.name}" 超过 10MB，已跳过`)
      continue
    }
    if (isDuplicate(file)) {
      ElMessage.warning(`"${file.name}" 已存在，已跳过`)
      continue
    }
    pendingFiles.value.push(file)
  }
  t.value = ''
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1)
}

function handleOverflowCommand(command: number) {
  removePendingFile(command)
}

function previewPendingFile(file: File) {
  if (file.type.startsWith('image/')) {
    previewImage.value = URL.createObjectURL(file)
  } else {
    const url = URL.createObjectURL(file)
    window.open(url, '_blank')
  }
}

function closePreview() {
  if (previewImage.value.startsWith('blob:')) {
    URL.revokeObjectURL(previewImage.value)
  }
  previewImage.value = ''
}

function isImageMessage(msg: ChatMessage): boolean {
  return /\.(jpg|jpeg|png|gif|bmp)/i.test(msg.content) && !msg.content.includes('\n')
}

function extractImageUrl(msg: ChatMessage): string {
  const m = msg.content.match(/https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|bmp)/i)
  return m ? m[0] : ''
}

function renderMarkdown(text: string): string {
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" class="msg-link">$1</a>')
    .replace(/\n/g, '<br>')
  return html
}

function formatTime(ts: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function send() {
  if ((!input.value.trim() && pendingFiles.value.length === 0) || loading.value) return
  if (input.value.length > MAX_INPUT_CHARS) {
    ElMessage.warning(`输入内容超出限制，最多可输入 ${MAX_INPUT_CHARS} 个字符`)
    return
  }
  loading.value = true

  // 获取或创建会话
  let cid = props.conversationId
  let skipConv = false
  if (!cid) {
    const analysisKeywords = ['分析', '评估', '评价', '解读', '学情']
    const isAnalysis = analysisKeywords.some(kw => input.value.includes(kw))
    if (isAnalysis) {
      skipConv = true
    } else {
      const conv = await convStore.createConversation('normal')
      if (conv) {
        convStore.setActive(conv.id)
        cid = conv.id
      } else { loading.value = false; return }
    }
  }

  const uploadedUrls: string[] = []
  if (pendingFiles.value.length > 0) {
    for (const file of pendingFiles.value) {
      const formData = new FormData()
      formData.append('file', file)
      const token = getToken()
      try {
        const resp = await fetch('/api/upload', {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        })
        if (resp.ok) {
          const data = await resp.json()
          uploadedUrls.push(data.url)
        }
      } catch { /* silent */ }
    }
    uploadedFileUrl = uploadedUrls[0] || ''
  }

  const fileNames = pendingFiles.value.map(f => f.name).join(', ')
  const text = input.value || (uploadedFileUrl ? '请帮我识别这个证明材料并记录到成长档案' : '')
  const userContent = pendingFiles.value.length > 0
    ? `[上传文件: ${fileNames}]\n${input.value || '请帮我识别并记录'}`
    : input.value

  const userMsg: ChatMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: userContent,
    timestamp: new Date().toISOString(),
  }
  store.addMessage(userMsg)
  input.value = ''
  editingOriginal.value = null
  pendingFiles.value = []
  pendingImagePreview.value = ''
  charState.value = 'thinking'
  charBubble.value = '让我想想...'

  const assistantId = (Date.now() + 1).toString()
  const assistantMsg: ChatMessage = {
    id: assistantId,
    role: 'assistant',
    content: '',
    timestamp: new Date().toISOString(),
  }
  store.addMessage(assistantMsg)

  const history = store.messages.slice(0, -1).map(m => ({ role: m.role, content: m.content }))

  let lastAssistantContent = ''

  try {
    await sendChatMessage(
      text,
      history,
      (chunk) => {
        const last = store.messages[store.messages.length - 1]
        if (last) {
          if (deepThinkEnabled.value) {
            last.content += chunk
            const thinkMatch = last.content.match(/##思考过程\s*([\s\S]*?)##回答/)
            const answerMatch = last.content.match(/##回答\s*([\s\S]*)/)
            if (thinkMatch) last.thinking = thinkMatch[1].trim()
            if (answerMatch) last.content = answerMatch[1].trim()
          } else {
            last.content += chunk
          }
        }
        if (charState.value !== 'speaking') {
          charState.value = 'speaking'
          charBubble.value = ''
        }
      },
      (full: string) => {
        loading.value = false
        charState.value = 'idle'
        charBubble.value = ''
        if (deepThinkEnabled.value) {
          const last = store.messages[store.messages.length - 1]
          if (last) {
            const thinkMatch = full.match(/##思考过程\s*([\s\S]*?)##回答/)
            const answerMatch = full.match(/##回答\s*([\s\S]*)/)
            if (thinkMatch) last.thinking = thinkMatch[1].trim()
            if (answerMatch) last.content = answerMatch[1].trim()
          }
        }
        lastAssistantContent = full
        setTimeout(() => { charBubble.value = '有什么可以帮你的？' }, 500)
      },
      (suggestions) => {
        const last = store.messages[store.messages.length - 1]
        if (last) last.suggestions = suggestions
      },
      uploadedFileUrl || undefined,
      cid || undefined,
      deepThinkEnabled.value,
      skipConv,
    )

    if (lastAssistantContent && cid) {
      try {
        await fetch(`/api/agent/conversations/${cid}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
          body: JSON.stringify({ role: 'assistant', content: lastAssistantContent, user_message: text }),
        })
      } catch { /* silent */ }
    }
  } catch {
    const placeholder = store.messages.find(m => m.id === assistantId)
    if (placeholder) {
      placeholder.content = '抱歉，连接失败，请稍后再试。'
    } else {
      store.addMessage({
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: '抱歉，连接失败，请稍后再试。',
        timestamp: new Date().toISOString(),
      })
    }
    loading.value = false
  }
  uploadedFileUrl = ''
}

function quickSend(text: string) {
  input.value = text
  send()
}

function handleSuggestion(s: Suggestion) {
  if (s.link) router.push(s.link)
}

async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function editAndRevert(content: string, index: number) {
  // 删除该消息之后的所有消息
  store.messages.splice(index)
  // 将消息内容放入输入框
  input.value = content
  editingOriginal.value = content
  // 聚焦到输入框
  nextTick(() => {
    const textarea = document.querySelector('.chat-textarea') as HTMLTextAreaElement
    if (textarea) {
      textarea.focus()
      // 将光标移到末尾
      textarea.setSelectionRange(content.length, content.length)
    }
  })
}

function scrollToBottom() {
  nextTick(() => {
    if (msgRef.value) {
      msgRef.value.scrollTop = msgRef.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, () => {
  scrollToBottom()
})

onMounted(() => {
  scrollToBottom()
})

onUpdated(() => {
  scrollToBottom()
})
</script>

<style scoped>
.chat-modern { 
  position: relative;
  display: flex; 
  flex-direction: column; 
  height: 100vh; 
  background: #fff; 
  overflow: hidden;
}

/* ── Messages Area ── */
.messages { flex: 1; overflow: hidden; padding: 0; }
.messages.scrolling { overflow-y: auto; padding: 12px 0; scroll-behavior: smooth; }
.messages.scrolling::-webkit-scrollbar { width: 4px; }
.messages.scrolling::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.messages.scrolling::-webkit-scrollbar-thumb:hover { background: #b0b5bd; }

/* ── Pending Files Corner ── */
.pending-files-corner {
  position: absolute;
  top: 8px;
  right: 16px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  padding: 12px 16px;
}
.overflow-tag {
  cursor: pointer;
  border-style: dashed;
  color: #909399;
  transition: all .2s;
}
.overflow-tag:hover {
  color: #409eff;
  border-color: #409eff;
}
.file-tag-clickable {
  cursor: pointer;
  transition: all .15s;
}
.file-tag-clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
}
.clear-all-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #909399;
  cursor: pointer;
  transition: all .15s;
  flex-shrink: 0;
  font-size: 12px;
  gap: 4px;
}
.clear-all-btn:hover {
  color: #f56c6c;
  border-color: #f56c6c;
  background: #fef0f0;
}
.dropdown-file-tag {
  cursor: pointer;
  font-size: 12px;
  pointer-events: auto;
  width: fit-content;
}
.dropdown-file-tag :deep(.el-tag__content) {
  display: flex;
  align-items: center;
}
.file-dropdown-item {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  padding: 6px 8px !important;
  gap: 8px !important;
}
.file-dropdown-menu {
  min-width: 280px;
}
.dropdown-remove {
  margin-left: auto;
  color: #999;
  cursor: pointer;
  flex-shrink: 0;
  padding: 2px;
  border-radius: 4px;
}
.dropdown-remove:hover {
  color: #f56c6c;
  background: #fef0f0;
}

/* ── Welcome Screen ── */
.welcome {
  position: relative; min-height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(180deg, #f0f8ff 0%, #fafcff 40%, #fff 100%);
  overflow: hidden;
}
.welcome-glow {
  position: absolute; top: -120px; left: 50%; transform: translateX(-50%);
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(64,158,255,.12) 0%, transparent 70%);
  pointer-events: none;
}
.welcome-content { 
  position: relative; 
  z-index: 1; 
  text-align: center; 
  padding: 40px 24px; 
  max-width: 640px; 
  margin: 0 auto;
}

.ai-character { 
  position: relative; 
  margin: 0 auto 10px; 
  display: flex; 
  align-items: center; 
  justify-content: center;
}
.ai-ring {
  position: absolute; width: 88px; height: 88px; border-radius: 50%;
  background: conic-gradient(from 0deg, #409eff, #67c23a, #e6a23c, #f56c6c, #409eff);
  animation: spin 4s linear infinite; padding: 3px;
  -webkit-mask: radial-gradient(circle at 50% 50%, transparent 38px, #000 38px);
  mask: radial-gradient(circle at 50% 50%, transparent 38px, #000 38px);
}
@keyframes spin { to { transform: rotate(360deg); } }
.ai-avatar {
  width: 72px; height: 72px; border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #67c23a);
  display: flex; align-items: center; justify-content: center;
  font-size: 32px; font-weight: 700; color: #fff;
  box-shadow: 0 4px 20px rgba(64,158,255,0.3);
}

.gradient-text {
  background: linear-gradient(135deg, #409eff, #67c23a);
  background-clip: text; -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.welcome-greeting h1 { font-size: 28px; color: #1a1a1a; margin-bottom: 8px; }
.welcome-greeting p { color: #888; font-size: 14px; line-height: 1.6; margin-bottom: 28px; }

/* 快捷卡片 */
.quick-grid { 
  display: grid; 
  grid-template-columns: repeat(3, 1fr); 
  gap: 10px; 
  margin-bottom: 24px;
}
.quick-card {
  background: #fff; border-radius: 14px; padding: 14px; cursor: pointer;
  border: 1px solid #f0f0f0; transition: border-color 0.2s, box-shadow 0.2s; 
  text-align: left;
  display: flex; gap: 10px; align-items: flex-start;
}
.quick-card:hover { 
  border-color: #409eff; 
  box-shadow: 0 4px 16px rgba(64,158,255,.12); 
}
.qc-icon { 
  width: 36px; height: 36px; border-radius: 10px; 
  display: flex; align-items: center; justify-content: center; 
  font-size: 18px; flex-shrink: 0;
}
.qc-body { min-width: 0; }
.qc-body strong { font-size: 13px; color: #333; display: block; }
.qc-body small { font-size: 11px; color: #999; display: block; margin-top: 2px; }

/* ── Message Bubbles ── */
.msg-row { 
  display: flex; gap: 8px; padding: 0 20px; margin-bottom: 10px; margin-top: 0; 
  max-width: 760px; margin-left: auto; margin-right: auto; width: 100%; box-sizing: border-box;
}
.msg-row:first-child { margin-top: 10px; }
.msg-row.user { flex-direction: row-reverse; }

.msg-avatar-col { flex-shrink: 0; }
.msg-avatar-col { flex-shrink: 0; margin-right: 8px; }
.msg-avatar-col :deep(.mc-name) { display: none; }

.msg-bubble-col { max-width: 85%; min-width: 0; }
.msg-row.user .msg-bubble-col { display: flex; flex-direction: column; align-items: flex-end; }

.bubble { 
  padding: 10px 14px; border-radius: 16px; line-height: 1.45; 
  font-size: 14px; word-break: break-word;
}
.bubble.assistant {
  background: #f0f4f9; color: #1a1a1a; border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.bubble.user {
  background: linear-gradient(135deg, #409eff, #337ecc); color: #fff;
  border-bottom-right-radius: 4px; box-shadow: 0 2px 8px rgba(64,158,255,.2);
}
.bubble-image { margin-bottom: 8px; }
.bubble-image img { max-width: 240px; border-radius: 10px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.msg-text :deep(.msg-link) { color: #409eff; text-decoration: underline; }
.bubble.user .msg-text :deep(a) { color: #fff; text-decoration: underline; }

.msg-time { font-size: 11px; color: #bbb; margin-top: 4px; padding-left: 4px; }
.msg-row.user .msg-time { padding-right: 4px; }

.msg-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
.msg-row.user .msg-footer { flex-direction: row-reverse; }
.msg-actions { display: flex; gap: 2px; opacity: 0; transition: opacity .2s; }
.msg-row:hover .msg-actions { opacity: 1; }
.action-btn { width: 24px; height: 24px; padding: 0; color: #bbb; border-radius: 4px; }
.action-btn:hover { color: #409eff; background: rgba(64,158,255,.08); }

/* 输入动画 */
.thinking-bubble {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 16px; border-radius: 16px 16px 16px 4px;
  background: #f0f2f5; box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.typing-dot { 
  width: 6px; height: 6px; border-radius: 50%; background: #c0c4cc; 
  animation: typingPulse 1.2s ease-in-out infinite; 
}
.typing-dot:nth-child(2) { animation-delay: 0.15s; }
.typing-dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes typingPulse { 
  0%, 100% { opacity: .3; transform: scale(.8); } 
  50% { opacity: 1; transform: scale(1.2); } 
}

/* 建议标签 */
.suggestions { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.suggestion-tag { 
  cursor: pointer; border-radius: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.suggestion-tag:hover {
  box-shadow: 0 2px 8px rgba(64,158,255,0.2);
}

/* ── Image Preview ── */
.image-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,.85); display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.preview-close-btn {
  position: absolute; top: 20px; right: 20px;
  width: 40px; height: 40px; border-radius: 50%;
  border: none; background: rgba(255,255,255,.9); color: #333;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background .2s, transform .15s; z-index: 1;
  box-shadow: 0 2px 12px rgba(0,0,0,.3);
}
.preview-close-btn:hover { background: #fff; transform: scale(1.1); }
.preview-close-btn:active { transform: scale(.95); }
.preview-img {
  max-width: 90vw; max-height: 90vh; border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0,0,0,.5);
  object-fit: contain;
}

/* 遮罩层过渡动画 */
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity .25s ease;
}
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

/* 图片缩放过渡动画 */
.preview-scale-enter-active {
  transition: transform .3s cubic-bezier(.4, 0, .2, 1), opacity .3s ease;
}
.preview-scale-leave-active {
  transition: transform .2s cubic-bezier(.4, 0, .2, 1), opacity .2s ease;
}
.preview-scale-enter-from {
  transform: scale(.85);
  opacity: 0;
}
.preview-scale-leave-to {
  transform: scale(.85);
  opacity: 0;
}

/* ── Input Bar ── */
.input-bar {
  flex-shrink: 0;
  padding: 12px 16px 12px;
  background: #fff;
}
.input-container {
  max-width: 768px;
  margin: 0 auto;
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

/* 功能开关（输入框上方） */
.feature-toggles {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  padding: 0 4px;
}
.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #6b7280;
  font-size: 13px;
  cursor: pointer;
  transition: all .2s;
  line-height: 1;
}
.toggle-btn:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}
.toggle-btn.active {
  border-color: #409eff;
  background: rgba(64,158,255,.06);
  color: #409eff;
}
.toggle-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}
.toggle-icon {
  font-size: 14px;
  line-height: 1;
}

/* 文本输入框 */
.input-field-wrap { flex: 1; min-width: 0; }
.chat-textarea {
  width: 100%; border: none; background: transparent; outline: none;
  font-size: 15px; font-family: inherit; color: #1f2937; resize: none;
  line-height: 1.5; padding: 4px 6px; min-height: 24px; max-height: 160px;
  overflow-y: auto;
}
.chat-textarea::placeholder { color: #9ca3af; }
.chat-textarea::-webkit-scrollbar { width: 4px; }
.chat-textarea::-webkit-scrollbar-track { background: transparent; }
.chat-textarea::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
.chat-textarea::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
.char-counter {
  text-align: right;
  font-size: 11px;
  color: #9ca3af;
  padding: 0 6px 2px;
  user-select: none;
}
.char-counter.warn { color: #f59e0b; }
.char-counter.over { color: #ef4444; }

/* 底部操作按钮行 */
.input-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  margin-top: 4px;
  padding: 0 2px;
}

/* 图标按钮（附件、麦克风等） */
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
.action-icon-btn:disabled {
  opacity: .4;
  cursor: not-allowed;
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
.send-btn.loading {
  background: #93c5fd;
}
.send-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}

/* ── Mobile Menu Button ── */
.menu-toggle { width: 36px; height: 36px; color: #555; margin: 4px 8px; flex-shrink: 0; }
.menu-toggle:hover { color: #409eff; background: rgba(64,158,255,.08); }

/* ── Mobile Responsive ── */
@media (max-width: 767px) {
  .chat-modern { border-radius: 0; }
  .welcome { padding-top: 0; }
  .welcome-content { padding: 20px 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: calc(100vh - 140px); }
  .ai-character { transform: scale(1.15); margin-bottom: 16px; }
  .welcome-greeting h1 { font-size: 22px; margin-bottom: 6px; }
  .welcome-greeting p { font-size: 13px; margin-bottom: 20px; }
  .quick-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; width: 100%; }
  .quick-card { padding: 12px; }
  .msg-row { padding: 0 12px; margin-bottom: 8px; }
  .bubble { padding: 8px 12px; font-size: 13px; }
  .input-bar { padding: 8px 10px; }
  .input-container { border-radius: 20px; padding: 10px; }
  .feature-toggles { margin-bottom: 6px; }
  .toggle-btn { padding: 4px 10px; font-size: 12px; }
  .chat-textarea { font-size: 14px; }
  .action-icon-btn { width: 28px; height: 28px; }
  .send-btn { width: 30px; height: 30px; }
  .msg-actions { opacity: 1; }
}
</style>
