<template>
  <div class="chat-modern">
    <!-- 移动端顶栏 -->
    <div v-if="showMenuButton" class="mobile-header">
      <el-button text circle class="menu-toggle" @click="emit('toggleSidebar')">
        <div class="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </el-button>
      <div class="mobile-header-title">{{ currentTitle }}</div>
      <el-button text circle class="menu-toggle" :disabled="loading" @click="handlePhoneCall">
        <el-icon :size="20"><Phone /></el-icon>
      </el-button>
    </div>
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

          </div>
      </div>

      <!-- Messages -->
      <template v-for="(msg, _i) in store.messages" :key="msg.id">
        <div :class="['msg-row', msg.role]">
          <div class="msg-bubble-col">
            <div :class="['bubble', msg.role]">
              <!-- Render images inline -->
              <div v-if="isImageMessage(msg)" class="bubble-image">
                <img :src="extractImageUrl(msg)" @click="previewImage = extractImageUrl(msg)" />
              </div>
              <div v-if="msg.content || msg.thinking || msg.role === 'user'" class="msg-text">
                <DeepThinking v-if="msg.role === 'assistant' && msg.thinking" :thinking="msg.thinking" :is-thinking="thinkingState === 'thinking' && msg.id === store.messages[store.messages.length - 1]?.id" />
                <div class="msg-text-body" v-html="renderMessageContent(msg)"></div>
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

    <!-- Voice Call Overlay -->
    <VoiceCallOverlay
      :visible="showVoiceCall"
      :conversation-id="voiceConvId"
      @close="handleVoiceClose"
    />

    <!-- 推荐对话 -->
    <div v-if="store.messages.length === 0" class="recommend-bar">
      <div class="recommend-title">为你推荐</div>
      <div class="recommend-list">
        <button
          v-for="item in recommendItems"
          :key="item"
          class="recommend-item"
          @click="input = item; send()"
        >
          <el-icon><Promotion /></el-icon>
          <span>{{ item }}</span>
        </button>
      </div>
    </div>

    <!-- Input Bar -->
    <div class="input-bar">
      <div class="input-container">
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
          <div class="char-counter" :class="{ warn: charRatio > 0.9, over: isOverLimit }">
            {{ inputCharCount.toLocaleString() }} / {{ MAX_INPUT_CHARS.toLocaleString() }}
          </div>
        </div>

        <!-- Bottom Actions -->
        <div class="input-actions">
          <!-- Upload buttons -->
          <el-dropdown trigger="click" @command="handleUploadCommand" :disabled="loading">
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

          <!-- Phone (桌面端显示，移动端隐藏) -->
          <el-tooltip content="语音通话" placement="top" :disabled="isMobile">
            <button
              v-if="!isMobile"
              type="button"
              class="action-icon-btn"
              :disabled="loading"
              @click="handlePhoneCall"
            >
              <el-icon :size="18"><Phone /></el-icon>
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

          <!-- Deep Think Toggle -->
          <el-tooltip content="深度思考" placement="top">
            <button
              type="button"
              :class="['action-icon-btn', { active: deepThinkEnabled }]"
              :disabled="loading"
              @click="deepThinkEnabled = !deepThinkEnabled"
            >
              <el-icon :size="18"><MagicStick /></el-icon>
            </button>
          </el-tooltip>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useConversationStore } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { sendChatMessage, fetchRecommendations } from '@/api/agent'
import { getToken } from '@/utils/token'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import type { ChatMessage, Suggestion } from '@/types'
import {
  Promotion, Paperclip, Picture, Document, Microphone, Phone, CopyDocument, EditPen, Menu, MagicStick, ArrowDown, Close, Delete,
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import MianCharacter from './MianCharacter.vue'
import DeepThinking from './DeepThinking.vue'
import VoiceCallOverlay from './VoiceCallOverlay.vue'

const { isMobile } = useResponsive()

const charState = ref<'idle' | 'thinking' | 'speaking'>('idle')
const charBubble = ref('')
const deepThinkEnabled = ref(false)
const thinkingState = ref<'idle' | 'thinking' | 'done'>('idle')
const MAX_INPUT_CHARS = 8000

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher'; conversationId?: number | null; fetching?: boolean; showMenuButton?: boolean }>(), { role: 'student', fetching: false, showMenuButton: false })
const emit = defineEmits<{ toggleSidebar: []; phoneCall: [] }>()
const showVoiceCall = ref(false)
const voiceConvId = ref<number | null>(null)

async function handlePhoneCall() {
  let cid = props.conversationId
  if (!cid) {
    const conv = await convStore.createConversation('normal')
    cid = conv?.id ?? null
  }
  voiceConvId.value = cid
  showVoiceCall.value = true
}

async function handleVoiceClose() {
  showVoiceCall.value = false
  const cid = voiceConvId.value
  voiceConvId.value = null
  if (!cid) return
  // 等待后端落库后，拉取最新消息并同步到智能体对话
  await new Promise(r => setTimeout(r, 400))
  await convStore.fetchMessages(cid)
  store.replaceMessages(
    convStore.messages.map(m => ({
      id: m.id.toString(),
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
    })),
  )
  convStore.setActive(cid)
  convStore.fetchList()
}

const store = props.role === 'teacher' ? useTeacherAgentStore() : useAgentStore()
const convStore = props.role === 'teacher' ? useTeacherConversationStore() : useConversationStore()
const router = useRouter()
const input = ref('')

// 当前对话标题
const currentTitle = computed(() => {
  if (!convStore.activeId) return '新对话'
  const conv = convStore.list.find(c => c.id === convStore.activeId)
  return conv?.title || '新对话'
})
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
  // 先设置为 auto 让浏览器重新计算 scrollHeight
  el.style.height = 'auto'
  // 然后设置为实际高度（最小16px，最大160px）
  el.style.height = Math.max(16, Math.min(el.scrollHeight, 160)) + 'px'
}

watch(input, () => {
  nextTick(autoResize)
})

watch(() => recorder.transcript.value, (val) => {
  if (val) {
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

const inputCharCount = computed(() => input.value.length)
const isOverLimit = computed(() => inputCharCount.value > MAX_INPUT_CHARS)
const charRatio = computed(() => Math.min(inputCharCount.value / MAX_INPUT_CHARS, 1))

// 模块级缓存，跨挂载保持
const _recommendCache: string[] = []

const recommendItems = ref<string[]>(
  _recommendCache.length ? [..._recommendCache] : [
    '帮我查一下下周的课程安排',
    '我想看看这学期的成绩单',
    '最近有什么校园活动通知',
    '帮我记录一下获奖信息',
  ]
)

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
    if (previewImage.value.startsWith('blob:')) {
      URL.revokeObjectURL(previewImage.value)
    }
    previewImage.value = URL.createObjectURL(file)
  } else {
    const url = URL.createObjectURL(file)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
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

// 轻量渲染：保留加粗，删除 markdown 标记符号（#、*、`、~ 及行首列表标记）
function renderMessageContent(msg: ChatMessage): string {
  let html = msg.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 加粗：**text**
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  // 删除行首标题标记（#）
  html = html.replace(/^\s*#{1,6}\s+/gm, '')

  // 删除行首列表标记（-、*）
  html = html.replace(/^\s*[-*]\s+/gm, '')

  // 删除其余 markdown 符号（#、*、反引号、波浪线）
  html = html.replace(/[#*`~]/g, '')

  // 换行
  html = html.replace(/\n/g, '<br>')

  return html
}

function formatTime(ts: string): string {
  if (!ts) return ''
  // 后端存储 UTC 时间，需要正确解析
  let d: Date
  if (ts.endsWith('Z') || ts.includes('+00:00')) {
    d = new Date(ts)
  } else {
    // 如果没有时区信息，假设是 UTC
    d = new Date(ts + 'Z')
  }
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' })
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
  closePreview()
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
  let deepThinkingActive = deepThinkEnabled.value
  thinkingState.value = 'idle'

  try {
    await sendChatMessage(
      text,
      history,
      (chunk) => {
        // 深度思考完毕，开始接收回复内容
        if (deepThinkingActive) {
          deepThinkingActive = false
          thinkingState.value = 'done'
        }
        // 开始接收正文时才关闭 loading
        if (loading.value) {
          loading.value = false
        }
        const last = store.messages[store.messages.length - 1]
        if (last) {
          store.updateMessage(last.id, { content: last.content + chunk })
        }
        if (charState.value !== 'speaking') {
          charState.value = 'speaking'
          charBubble.value = ''
        }
        scrollToBottom()
      },
      (full: string) => {
        loading.value = false
        charState.value = 'idle'
        charBubble.value = ''
        lastAssistantContent = full
        setTimeout(() => { charBubble.value = '有什么可以帮你的？' }, 500)
      },
      (suggestions) => {
        const last = store.messages[store.messages.length - 1]
        if (last) {
          store.updateMessage(last.id, { suggestions })
        }
      },
      (reasoning) => {
        // 进入思考状态
        if (thinkingState.value === 'idle') {
          thinkingState.value = 'thinking'
        }
        // 思考开始时关闭 loading 状态
        if (loading.value) {
          loading.value = false
        }
        const last = store.messages[store.messages.length - 1]
        if (last) {
          store.updateMessage(last.id, { thinking: (last.thinking || '') + reasoning })
        }
        scrollToBottom()
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
  // 动态获取推荐（有缓存则静默刷新）
  fetchRecommendations().then(items => {
    if (items.length > 0) {
      recommendItems.value = items
      _recommendCache.length = 0
      _recommendCache.push(...items)
    }
  })
})

onUnmounted(() => {
  closePreview()
})
</script>

<style scoped>
.chat-modern { 
  position: relative;
  display: flex; 
  flex-direction: column; 
  height: 100vh; 
  background: linear-gradient(180deg, #f0f8ff 0%, #fafcff 40%, #fff 100%); 
  overflow: hidden;
}

/* ── Messages Area ── */
.messages { flex: 1; overflow: hidden; padding: 0; }
.messages.scrolling { overflow-y: auto; padding: 12px 0; scroll-behavior: auto; }
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
  padding: 30px 24px; 
  max-width: 600px; 
  margin: -80px auto 0;
}

.ai-character { 
  position: relative; 
  margin: 0 auto 0px; 
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
.welcome-greeting h1 { font-size: 24px; color: #1a1a1a; margin-bottom: 4px; margin-top: 0; }
.welcome-greeting p { color: #888; font-size: 13px; line-height: 1.6; margin-bottom: 20px; }

/* 推荐对话 */
.recommend-bar {
  flex-shrink: 0;
  padding: 0 16px 8px;
  margin-top: -112px;
  background: #fff;
  position: relative;
  z-index: 10;
}
.recommend-title {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
  padding-left: 14px;
  max-width: 820px;
  margin-left: auto;
  margin-right: auto;
}
.recommend-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  max-width: 820px;
  margin: 0 auto;
  padding-left: 14px;
}
.recommend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #555;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.recommend-item:hover {
  border-color: #c0c4cc;
  background: #f9fafb;
  color: #333;
}
.recommend-item .el-icon {
  font-size: 14px;
  color: #409eff;
}

/* ── Message Bubbles ── */
.msg-row { 
  display: flex; gap: 8px; padding: 0 20px; margin-bottom: 10px; margin-top: 0; 
  max-width: 760px; margin-left: 140px; margin-right: auto; width: 100%; box-sizing: border-box;
}
.msg-row:first-child { margin-top: 10px; }
.msg-row.user { flex-direction: row-reverse; margin-left: auto; margin-right: 140px; }

.msg-avatar-col { flex-shrink: 0; }
.msg-avatar-col { flex-shrink: 0; margin-right: 8px; }
.msg-avatar-col :deep(.mc-name) { display: none; }

.msg-bubble-col { max-width: 85%; min-width: 0; }
.msg-row.assistant .msg-bubble-col { width: 85%; }
.msg-row.user .msg-bubble-col { display: flex; flex-direction: column; align-items: flex-end; }

.bubble {
  padding: 10px 14px; border-radius: 16px; line-height: 1.45;
  font-size: 14px; word-break: break-word;
}
.bubble.assistant {
  background: #f0f4f9; color: #1a1a1a; border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
  width: 100%;
}
.bubble.user {
  background: linear-gradient(135deg, #409eff, #337ecc); color: #fff;
  border-bottom-right-radius: 4px; box-shadow: 0 2px 8px rgba(64,158,255,.2);
}
.bubble-image { margin-bottom: 8px; }
.bubble-image img { max-width: 240px; border-radius: 10px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.1); }
.msg-text :deep(.msg-link) { color: #409eff; text-decoration: underline; }
.bubble.user .msg-text :deep(a) { color: #fff; text-decoration: underline; }

/* ── Markdown Styles ── */
.msg-text-body { line-height: 1.5; overflow-wrap: break-word; word-break: break-word; }
.msg-text-body > *:first-child { margin-top: 0; }
.msg-text-body > *:last-child { margin-bottom: 0; }
.msg-text :deep(.msg-code-block) {
  background: #f6f8fa;
  border-radius: 6px;
  padding: 10px;
  margin: 4px 0;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}
.msg-text :deep(.msg-code-block code) {
  background: transparent;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}
.msg-text :deep(.msg-inline-code) {
  background: rgba(175, 184, 193, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: monospace;
}
.msg-text :deep(.msg-h2) {
  font-size: 1.2em;
  font-weight: 600;
  margin: 8px 0 4px 0;
  padding-bottom: 3px;
  border-bottom: 1px solid #eee;
}
.msg-text :deep(.msg-h3) {
  font-size: 1.05em;
  font-weight: 600;
  margin: 6px 0 3px 0;
}
.msg-text :deep(.msg-h4) {
  font-size: 1em;
  font-weight: 600;
  margin: 4px 0 2px 0;
}
.msg-text :deep(.msg-quote) {
  border-left: 3px solid #ddd;
  padding-left: 10px;
  margin: 4px 0;
  color: #666;
  font-style: italic;
}
.msg-text :deep(.msg-ul),
.msg-text :deep(.msg-ol) {
  padding-left: 1.4em;
  margin: 4px 0;
}
.msg-text :deep(.msg-li),
.msg-text :deep(.msg-ol-li) {
  margin: 2px 0;
  list-style-position: inside;
}
.msg-text :deep(.msg-li) { list-style-type: disc; }
.msg-text :deep(.msg-ol-li) { list-style-type: decimal; }
.msg-text :deep(.msg-table) {
  border-collapse: collapse;
  margin: 4px 0;
  width: 100%;
  font-size: 13px;
  table-layout: fixed;
}
.msg-text :deep(.msg-th),
.msg-text :deep(.msg-td) {
  border: 1px solid #ddd;
  padding: 8px 12px;
  text-align: left;
}
.msg-text :deep(.msg-th) {
  background: #f6f8fa;
  font-weight: 600;
}
.msg-text :deep(.msg-tr:nth-child(even)) {
  background: #f9f9f9;
}
.bubble.user .msg-text :deep(.msg-code-block) {
  background: rgba(255, 255, 255, 0.2);
}
.bubble.user .msg-text :deep(.msg-inline-code) {
  background: rgba(255, 255, 255, 0.2);
}

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
  padding: 8px 16px;
  background: #fff;
}
.input-container {
  max-width: 820px;
  margin: 0 auto;
  background: #fff;
  border-radius: 24px;
  padding: 6px 14px 6px;
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
  margin-bottom: 4px;
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
  line-height: 1.5; padding: 6px 6px 0px; min-height: 16px; max-height: 160px;
  overflow-y: auto;
  transition: height 0.3s ease;
}
.chat-textarea::placeholder { color: #9ca3af; }
.chat-textarea::-webkit-scrollbar { width: 0; }
.chat-textarea::-webkit-scrollbar-track { background: transparent; }
.chat-textarea::-webkit-scrollbar-thumb { background: transparent; }
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
  margin-top: 2px;
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
.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  flex-shrink: 0;
}
.mobile-header-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  text-align: center;
  flex: 1;
}
.mobile-header-placeholder {
  width: 36px;
  flex-shrink: 0;
}
.menu-toggle { width: 36px; height: 36px; color: #555; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.menu-toggle:hover { color: #409eff; background: rgba(64,158,255,.08); }

.hamburger-icon {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 18px;
  height: 14px;
  gap: 3px;
}

.hamburger-icon span {
  display: block;
  width: 100%;
  height: 2px;
  background-color: currentColor;
  border-radius: 1px;
}

/* ── Mobile Responsive ── */
@media (max-width: 767px) {
  .chat-modern { border-radius: 0; }
  .welcome { padding-top: 0; }
  .welcome-content { padding: 20px 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: calc(100vh - 140px); }
  .ai-character { transform: scale(1.15); margin-bottom: 16px; }
  .welcome-greeting h1 { font-size: 22px; margin-bottom: 6px; }
  .welcome-greeting p { font-size: 13px; margin-bottom: 20px; }
  .msg-row { padding: 0 12px; margin-bottom: 8px; margin-left: 0; margin-right: 0; }
  .msg-row.user { flex-direction: row-reverse; margin-left: 0; margin-right: 0; }
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
