<template>
  <div class="chat-modern" ref="rootRef">
    <!-- 移动端顶栏 -->
    <div v-if="showMenuButton" class="mobile-header">
      <el-button text circle class="menu-toggle" @click="emit('toggleSidebar')">
        <div class="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </el-button>
      <div
        class="mobile-header-title"
        :class="{ 'is-actionable': !!currentConv }"
        @click="openConvActions"
      >
        <span class="title-text">{{ currentTitle }}</span>
        <el-icon v-if="currentConv" class="title-caret" :size="12"><ArrowDown /></el-icon>
      </div>
      <el-button text circle class="menu-toggle" :disabled="loading" @click="handlePhoneCall">
        <el-icon :size="20"><Phone /></el-icon>
      </el-button>
      <!-- 无进行中的对话时不渲染，避免出现按了没反应的禁用按钮 -->
      <el-button v-if="currentConv" text circle class="menu-toggle" aria-label="对话操作" @click="openConvActions">
        <el-icon :size="20"><MoreFilled /></el-icon>
      </el-button>
    </div>

    <!-- 移动端会话操作面板：与侧边栏列表共用同一个豆包式底部动作表 -->
    <ConversationActionsSheet
      v-model:visible="showConvActions"
      :conv="currentConv"
      @command="onSheetCommand"
      @stage="sheetSetStage"
    />
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

    <!-- 推荐对话（固定在输入栏上方；一旦被输入框碰到就整条动画退场） -->
    <Transition name="recommend-out">
      <div
        v-if="store.messages.length === 0 && !recommendHidden && recommendItems.length > 0"
        class="recommend-bar"
      >
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
    </Transition>

    <!-- Input Bar -->
    <div class="input-bar">
      <div class="input-container" ref="inputContainerRef">
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
          <!-- Deep Think Toggle（胶囊按钮，位于上传按钮左侧） -->
          <el-tooltip content="深度思考" placement="top" :disabled="isMobile">
            <button
              type="button"
              :class="['toggle-btn', { active: deepThinkEnabled }]"
              :disabled="loading"
              @click="deepThinkEnabled = !deepThinkEnabled"
            >
              <svg class="deep-think-icon toggle-icon" viewBox="0 0 16 16" aria-hidden="true">
                <g
                  transform="matrix(0.9907486438751221,0,0,0.9907486438751221,0.07401084899902344,0.07401084899902344)"
                >
                  <path
                    fill="currentColor"
                    d=" M8,6.769999980926514 C8.678836822509766,6.769999980926514 9.229999542236328,7.321163177490234 9.229999542236328,8 C9.229999542236328,8.678836822509766 8.678836822509766,9.229999542236328 8,9.229999542236328 C7.321163177490234,9.229999542236328 6.769999980926514,8.678836822509766 6.769999980926514,8 C6.769999980926514,7.321163177490234 7.321163177490234,6.769999980926514 8,6.769999980926514z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    fill-opacity="0"
                    stroke="currentColor"
                    stroke-opacity="1"
                    stroke-width="1.4"
                    d=" M10.506570816040039,10.506570816040039 C7.301570892333984,13.711570739746094 3.5820748805999756,15.186075210571289 2.197999954223633,13.802000045776367 C0.81392502784729,12.417924880981445 2.289379835128784,8.698396682739258 5.494379997253418,5.493396282196045 C8.699379920959473,2.2883963584899902 12.417924880981445,0.81392502784729 13.802000045776367,2.197999954223633 C15.186075210571289,3.5820748805999756 13.711570739746094,7.301570892333984 10.506570816040039,10.506570816040039z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    fill-opacity="0"
                    stroke="currentColor"
                    stroke-opacity="1"
                    stroke-width="1.4"
                    d=" M10.730999946594238,5.269000053405762 C13.935999870300293,8.473999977111816 15.3100004196167,12.293999671936035 13.802000045776367,13.802000045776367 C12.293999671936035,15.3100004196167 8.475000381469727,13.935999870300293 5.269999980926514,10.730999946594238 C2.065000057220459,7.526000022888184 0.6899999976158142,3.7060000896453857 2.197999954223633,2.197999954223633 C3.7060000896453857,0.6899999976158142 7.526000022888184,2.063999891281128 10.730999946594238,5.269000053405762z"
                  />
                </g>
              </svg>
              <span>深度思考</span>
            </button>
          </el-tooltip>

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
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useConversationStore, type Conversation } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { sendChatMessage, fetchRecommendations } from '@/api/agent'
import { getToken } from '@/utils/token'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import type { ChatMessage, Suggestion } from '@/types'
import {
  Promotion, Paperclip, Picture, Document, Microphone, Phone, CopyDocument, EditPen, ArrowDown, Close, Delete,
  MoreFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import MianCharacter from './MianCharacter.vue'
import DeepThinking from './DeepThinking.vue'
import VoiceCallOverlay from './VoiceCallOverlay.vue'
import ConversationActionsSheet from './ConversationActionsSheet.vue'

const { isMobile } = useResponsive()

const charState = ref<'idle' | 'thinking' | 'speaking'>('idle')
const charBubble = ref('')
const deepThinkEnabled = ref(false)
const thinkingState = ref<'idle' | 'thinking' | 'done'>('idle')
const MAX_INPUT_CHARS = 8000

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher'; conversationId?: number | null; fetching?: boolean; showMenuButton?: boolean }>(), { role: 'student', fetching: false, showMenuButton: false })
const emit = defineEmits<{ toggleSidebar: []; phoneCall: []; 'conversation-removed': [] }>()
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

/** 当前对话对象与可选阶段：供移动端操作面板使用 */
const activeConvSnapshot = ref<Conversation | null>(null)
// 搜索/归档视图下，当前对话可能不在已加载列表里；缓存一份快照，保证操作面板仍可用
watch(
  () => convStore.list.find(c => c.id === convStore.activeId) || null,
  (found) => { if (found) activeConvSnapshot.value = { ...found } },
  { immediate: true },
)
const currentConv = computed(() => {
  if (!convStore.activeId) return null
  const live = convStore.list.find(c => c.id === convStore.activeId)
  if (live) return live
  return activeConvSnapshot.value?.id === convStore.activeId ? activeConvSnapshot.value : null
})
const showConvActions = ref(false)

function openConvActions() {
  if (!currentConv.value) return
  showConvActions.value = true
}

function convErrorText(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}

/** 移动端底部面板的动作分发（面板本身只管展示，动作仍由这里处理） */
function onSheetCommand(cmd: string) {
  switch (cmd) {
    case 'rename': return sheetRename()
    case 'pin':
    case 'unpin': return sheetTogglePinned()
    case 'delete': return sheetDelete()
  }
}

async function sheetRename() {
  const c = currentConv.value
  if (!c) return
  try {
    const { value } = await ElMessageBox.prompt(' ', '重命名对话', {
      inputValue: c.title,
      inputPlaceholder: '请输入对话标题',
      customClass: 'sidebar-msgbox',
      inputValidator: (v: string) => {
        const t = (v || '').trim()
        if (!t) return '标题不能为空'
        if (t.length > 200) return '标题不能超过 200 个字符'
        return true
      },
    })
    const title = (value || '').trim()
    if (!title || title === c.title) return
    await convStore.updateConversation(c.id, { title })
    ElMessage.success('已重命名')
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(convErrorText(e, '重命名失败'))
  }
}

async function sheetTogglePinned() {
  const c = currentConv.value
  if (!c) return
  try {
    await convStore.updateConversation(c.id, { pinned: !c.pinned })
    ElMessage.success(c.pinned ? '已取消置顶' : '已置顶')
  } catch (e) {
    ElMessage.error(convErrorText(e, '操作失败'))
  }
}

/** 阶段切换由底部面板的 @stage 触发；面板展开前已在内部收起 */
async function sheetSetStage(stage: string) {
  const c = currentConv.value
  if (!c || stage === c.project_stage) return
  try {
    await convStore.updateConversation(c.id, { project_stage: stage })
    ElMessage.success(`阶段已更新为「${stage}」`)
  } catch (e) {
    ElMessage.error(convErrorText(e, '阶段更新失败'))
  }
}

async function sheetDelete() {
  const c = currentConv.value
  if (!c) return
  try {
    await ElMessageBox.confirm(`确定删除「${c.title}」？`, '删除对话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'sidebar-msgbox',
    })
  } catch {
    return
  }
  try {
    await convStore.deleteConversation(c.id)
    ElMessage.success('已删除')
    emit('conversation-removed')
  } catch (e) {
    ElMessage.error(convErrorText(e, '删除失败'))
  }
}

const msgRef = ref<HTMLElement>()
const rootRef = ref<HTMLElement | null>(null)
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
  const contentHeight = el.scrollHeight
  // 然后设置为实际高度（最小16px，最大160px）
  el.style.height = Math.max(16, Math.min(contentHeight, 160)) + 'px'
  updateRecommendHidden()
}

/**
 * 输入框是否已经“碰到”推荐区。
 * 推荐区固定在输入栏正上方（bottom = 单行输入栏高度），所以它的底边就是
 * 「容器底边 - 单行输入栏高度」；用真实几何判断：输入框容器上沿越过这条线即视为被盖住。
 * 不读推荐区自身的 rect —— 它可能正处于退场动画中，也可能已被 v-if 移除。
 */
function updateRecommendHidden() {
  const box = inputContainerRef.value
  const root = rootRef.value
  if (!box || !root || inputBarBaseHeight <= 0) return
  // 推荐区固定在输入栏正上方，底边 = 容器底边 - 单行输入栏高度
  const barBottom = root.getBoundingClientRect().bottom - inputBarBaseHeight
  // 0.5px 容差：静止状态刚好贴住不算被盖住
  recommendHidden.value = box.getBoundingClientRect().top < barBottom - 0.5
}

/** 单行基准高度（挂载时测量一次，之后不再变化） */
function ensureBaseMetrics() {
  const box = inputContainerRef.value
  if (!box || boxBaseHeight > 0) return
  boxBaseHeight = box.getBoundingClientRect().height
  if (textareaRef.value) singleLineContentHeight = textareaRef.value.scrollHeight
  const bar = box.closest('.input-bar') as HTMLElement | null
  if (bar) inputBarBaseHeight = bar.getBoundingClientRect().height
}

/**
 * 记录「输入框仍是单行时」的基准高度，写进两个 CSS 变量：
 * - --chat-welcome-h   消息区高度，供移动端欢迎语固定高度居中（输入框被撑高时欢迎语不会被往上顶）
 * - --chat-input-bar-h 输入栏高度，供「为你推荐」贴在输入栏正上方
 * 输入框已被撑高时不记录（此时量到的不是基准高度）；
 * 布局变化（横竖屏、公告条出现等）后会重新校准。
 */
function syncBaseHeights() {
  const root = rootRef.value
  const msg = msgRef.value
  const box = inputContainerRef.value
  if (!root || !msg || !box) return
  const ta = textareaRef.value
  // textarea 高于单行时说明输入框已被撑开，跳过，避免记下被压缩的高度
  if (ta && singleLineContentHeight > 0 && ta.getBoundingClientRect().height > singleLineContentHeight + 1) return
  const h = msg.getBoundingClientRect().height
  if (h > 0) root.style.setProperty('--chat-welcome-h', `${h}px`)
  const bar = box.closest('.input-bar') as HTMLElement | null
  const barH = bar ? bar.getBoundingClientRect().height : 0
  if (barH > 0) {
    inputBarBaseHeight = barH
    root.style.setProperty('--chat-input-bar-h', `${barH}px`)
  }
  syncRecommendListLimit()
}

/**
 * 屏幕不够高时（例如 iPhone SE 667pt），欢迎语 + 5 条推荐会挤在一起，
 * 推荐区会盖住欢迎语副标题。这里按「推荐区顶边不高于欢迎语底边 + 8px」反推出
 * 推荐列表的最大高度，超出部分在列表内滚动；屏幕够高时上限等于自然高度，不出现滚动条。
 */
function syncRecommendListLimit() {
  const root = rootRef.value
  if (!root) return
  const content = root.querySelector('.welcome-content') as HTMLElement | null
  const barEl = root.querySelector('.recommend-bar') as HTMLElement | null
  const list = root.querySelector('.recommend-list') as HTMLElement | null
  if (!content || !barEl || !list) return
  // 先还原上限再量一次，避免把上一次的压缩结果当成自然高度
  root.style.removeProperty('--chat-recommend-list-max-h')
  const overlap = content.getBoundingClientRect().bottom + 8 - barEl.getBoundingClientRect().top
  const limit = Math.max(80, Math.round(list.getBoundingClientRect().height - Math.max(0, overlap)))
  root.style.setProperty('--chat-recommend-list-max-h', `${limit}px`)
}

function handleViewportResize() {
  nextTick(() => {
    syncBaseHeights()
    updateRecommendHidden()
  })
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

/** 推荐条数：与推荐区排版一致 */
const RECOMMEND_COUNT = 5
/** 推荐缓存有效期：期内直接复用，避免每次进页面都等一次生成（1~3s） */
const RECOMMEND_CACHE_TTL = 5 * 60 * 1000
const RECOMMEND_CACHE_KEY = 'campus_agent_recommend_cache'

interface RecommendCacheEntry { items: string[]; at: number }

/** 推荐缓存：按角色分开存，落 sessionStorage 以便刷新页面也能秒开 */
const _recommendCache: Record<string, RecommendCacheEntry> = (() => {
  try {
    const raw = sessionStorage.getItem(RECOMMEND_CACHE_KEY)
    return raw ? (JSON.parse(raw) as Record<string, RecommendCacheEntry>) : {}
  } catch {
    return {}
  }
})()

function saveRecommendCache() {
  try {
    sessionStorage.setItem(RECOMMEND_CACHE_KEY, JSON.stringify(_recommendCache))
  } catch { /* 隐私模式等场景下忽略 */ }
}

/** 拉取推荐：缓存还新鲜就直接复用，否则后台刷新（界面先显示缓存内容） */
function loadRecommendations() {
  const cached = _recommendCache[props.role]
  if (cached?.items?.length && Date.now() - cached.at < RECOMMEND_CACHE_TTL) return
  fetchRecommendations().then(items => {
    const top = items.slice(0, RECOMMEND_COUNT)
    // 接口失败/返回空时才用兜底文案，避免推荐区整个消失
    recommendItems.value = top.length > 0 ? top : [...FALLBACK_RECOMMENDATIONS[props.role]]
    if (top.length === 0) return
    _recommendCache[props.role] = { items: top, at: Date.now() }
    saveRecommendCache()
    // 条目变化会改变推荐区高度，重新算一次矮屏上限
    nextTick(() => {
      syncBaseHeights()
      updateRecommendHidden()
    })
  })
}

/**
 * 接口不可用时的兜底推荐（与后端 DEFAULT_RECOMMENDATIONS 一致）。
 * 只在“请求失败或返回空”时使用：正常路径下推荐文字必须来自后端，
 * 不再先摆一份写死的文案在界面上（那看起来就是“死文字”）。
 */
const FALLBACK_RECOMMENDATIONS: Record<string, string[]> = {
  student: [
    '帮我查一下下周的课程安排',
    '我今天的计划任务有哪些',
    '查一下我的作品集',
    '社区最近有什么热门帖子',
    '有什么好的学习资源推荐',
  ],
  teacher: [
    '帮我查看今天的待办任务',
    '查一下班级学生的考勤情况',
    '帮我看看最近的校园公告',
    '查询学生的成长记录',
    '帮我看一下学生的心理预警',
  ],
}

// 有缓存就直接用它（也是后端上次给的真实结果）；否则先留空，等接口回来再出现
const recommendItems = ref<string[]>(
  _recommendCache[props.role]?.items?.length ? [..._recommendCache[props.role].items] : []
)

const fileInputRef = ref<HTMLInputElement>()
const imageInputRef = ref<HTMLInputElement>()
const pendingFiles = ref<File[]>([])
const pendingImagePreview = ref('')
let uploadedFileUrl = ''

/**
 * “为你推荐”是否已被输入框盖住。
 * 用真实几何判定而非行数阈值：输入框容器被撑高时上沿上移，
 * 一旦越过推荐区底边（= 输入栏上沿）就判定为被盖住，整条动画退场。
 */
const recommendHidden = ref(false)
const inputContainerRef = ref<HTMLElement | null>(null)
/** 单行状态下的输入框容器高度 */
let boxBaseHeight = 0
/** 空输入（单行）时 textarea 的 scrollHeight */
let singleLineContentHeight = 0
/** 单行状态下的输入栏高度（推荐区就贴在它正上方） */
let inputBarBaseHeight = 0
/** 监听消息区尺寸变化的观察者：布局变化时重新校准欢迎语基准高度 */
let msgObserver: ResizeObserver | null = null

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
  // 对话内容要变了，下次新对话的推荐需要重新生成
  delete _recommendCache[props.role]
  saveRecommendCache()

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
          headers: { 'X-Requested-With': 'XMLHttpRequest', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
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
  const text = input.value || (uploadedFileUrl ? '请帮我看看这个物品，是不是有人捡到了' : '')
  const userContent = pendingFiles.value.length > 0
    ? `[上传文件: ${fileNames}]\n${input.value || (uploadedFileUrl ? '请帮我看看这个物品' : '请帮我看看')}`
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
  /** 是否已收到服务端 meta（= 本轮回复已落库） */
  let metaReceived = false
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
      (meta) => {
        // 服务端已把本轮回复落库：同步标题并标记已保存，避免前端重复写入
        metaReceived = true
        if (meta?.title && cid) {
          convStore.patchConversation(cid, { title: meta.title, updated_at: new Date().toISOString() })
        }
      },
    )

    // 兜底：正常路径由后端落库（meta.saved=true）；只有服务端明确未保存时才补写一次，
    // 避免旧实现里"后端存一次 + 前端再存一次"造成的重复消息
    if (!metaReceived && lastAssistantContent && cid) {
      try {
        const token = getToken()
        const resp = await fetch(`/api/agent/conversations/${cid}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify({ role: 'assistant', content: lastAssistantContent, user_message: text }),
        })
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      } catch {
        ElMessage.warning('本条回复可能未保存到历史记录')
      }
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
  // 记录单行状态下的基准几何（此时输入框尚未被内容撑高）
  nextTick(() => {
    ensureBaseMetrics()
    syncBaseHeights()
    updateRecommendHidden()
  })
  // 消息区尺寸变化（横竖屏、公告条出现等）时重新校准基准高度与推荐区显隐
  if (msgRef.value && typeof ResizeObserver !== 'undefined') {
    msgObserver = new ResizeObserver(() => {
      syncBaseHeights()
      updateRecommendHidden()
    })
    msgObserver.observe(msgRef.value)
  }
  window.addEventListener('resize', handleViewportResize)
  // 动态获取推荐（缓存新鲜则直接复用，否则后台静默刷新）
  loadRecommendations()
})

onUnmounted(() => {
  closePreview()
  msgObserver?.disconnect()
  msgObserver = null
  window.removeEventListener('resize', handleViewportResize)
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
/* flex-basis:0 + grow:1 占满剩余空间；shrink:0 让输入框长高时不压缩消息区。
   否则消息区被压缩、其内容锚在顶部，欢迎语就会被顶上去。 */
.messages { flex: 1 0 0%; overflow: hidden; padding: 0; min-height: 0; }
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
  /* 脱离文档流：固定在输入栏正上方（bottom = 单行输入栏高度，由 syncBaseHeights() 量得）。
     不参与布局计算，因此它的出现/消失不会改变消息区高度、不会把欢迎语推着上下移动。 */
  position: absolute;
  left: 0;
  right: 0;
  bottom: var(--chat-input-bar-h, 112px);
  padding: 0 16px 8px;
  background: #fff;
  /* 覆盖在消息区之上（与原先同等层级） */
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
  /* 矮屏上限由 syncRecommendListLimit() 量出，超出部分列表内滚动，避免盖住欢迎语 */
  max-height: var(--chat-recommend-list-max-h, none);
  overflow-y: auto;
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

/* ── “为你推荐”退场动画 ──
   推荐区已绝对定位、不占布局高度，所以可以安全地过渡自身高度与透明度：
   被输入框碰到时整条收起淡出，不会推动输入栏或欢迎语。
   max-height 取足够大的值（内容约 90px），确保过渡期间不被截断。 */
.recommend-out-enter-active,
.recommend-out-leave-active {
  overflow: hidden;
  transition:
    max-height .28s cubic-bezier(.4, 0, .2, 1),
    opacity .28s cubic-bezier(.4, 0, .2, 1),
    transform .28s cubic-bezier(.4, 0, .2, 1);
}
.recommend-out-enter-from,
.recommend-out-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-6px);
}
.recommend-out-enter-to,
.recommend-out-leave-from {
  max-height: 400px;
  opacity: 1;
  transform: translateY(0);
}
@media (prefers-reduced-motion: reduce) {
  .recommend-out-enter-active,
  .recommend-out-leave-active { transition: none; }
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
  /* 画在推荐区之上：输入框被撑高时向上“盖住”推荐，
     推荐区（z-index 10）不再是靠推动让位，而是被逐条遮掉 */
  position: relative;
  z-index: 20;
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
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #6b7280;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  line-height: 1;
  white-space: nowrap;
  /* 平滑过渡：颜色/背景/边框/阴影同时缓动，不做尺寸或缩放动画 */
  transition:
    background-color .26s cubic-bezier(.4, 0, .2, 1),
    border-color .26s cubic-bezier(.4, 0, .2, 1),
    color .26s cubic-bezier(.4, 0, .2, 1),
    box-shadow .26s cubic-bezier(.4, 0, .2, 1);
}
.toggle-btn:hover:not(:disabled) {
  border-color: #c7d9f5;
  background: #f7faff;
  color: #4b6b96;
}
.toggle-btn.active {
  border-color: #a9c6f0;
  background: #eef4ff;
  color: #3b6ea8;
}
.toggle-btn.active:hover:not(:disabled) {
  border-color: #8fb4e8;
  background: #e4eeff;
  color: #34618f;
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

/* 深度思考胶囊按钮：图标取自 chat.deepseek.com 官方图形（四瓣回环 + 中心圆点）。
   静态度量分离 —— 颜色/边框/背景过渡平滑，不缩放、不改变文字宽度。 */
.deep-think-icon {
  display: block;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  transition: color .26s cubic-bezier(.4, 0, .2, 1);
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
  /* 毛玻璃：悬浮在内容之上，滚动内容从下方模糊透出 */
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  padding-top: calc(6px + env(safe-area-inset-top, 0px));
  flex-shrink: 0;
  background: rgba(255, 255, 255, .62);
  -webkit-backdrop-filter: blur(18px) saturate(180%);
  backdrop-filter: blur(18px) saturate(180%);
  border-bottom: 1px solid rgba(255, 255, 255, .55);
  box-shadow: 0 1px 0 rgba(17, 24, 39, .04), 0 6px 18px -8px rgba(17, 24, 39, .12);
}
/* 顶栏下沿的柔化渐隐，避免与消息内容出现硬边 */
.mobile-header::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  height: 14px;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(255, 255, 255, .38), rgba(255, 255, 255, 0));
}
/* 不支持 backdrop-filter 的浏览器降级为更实的底色，保证标题可读 */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .mobile-header { background: rgba(255, 255, 255, .94); }
}
.mobile-header-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  flex: 1;
  min-width: 0;
  padding: 0 4px;
  cursor: default;
  -webkit-tap-highlight-color: transparent;
}
.mobile-header-title.is-actionable { cursor: pointer; }
.mobile-header-title .title-text {
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mobile-header-title .title-caret { flex-shrink: 0; color: #9aa0a6; transition: color .15s ease; }
.mobile-header-title.is-actionable:active .title-caret { color: #6366f1; }
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
  /* 顶栏改为悬浮毛玻璃后，内容需让出顶栏高度 */
  .messages.scrolling {
    padding-top: calc(58px + env(safe-area-inset-top, 0px)) !important;
    scroll-padding-top: calc(58px + env(safe-area-inset-top, 0px));
  }
  /* 悬浮顶栏存在时，右上角的待发送文件预览下移，避免遮挡 */
  .chat-modern:has(.mobile-header) .pending-files-corner {
    top: calc(54px + env(safe-area-inset-top, 0px));
  }
  /* 顶栏四个控件在 375px 下也要放得下：缩小按钮与间距，标题可点开会话面板 */
  .mobile-header { padding: 6px 6px; gap: 2px; }
  .mobile-header-title { font-size: 15px; padding: 0 2px; }
  .menu-toggle { width: 32px; height: 32px; }
  .menu-toggle :deep(.el-icon) { font-size: 18px; }
  /* 欢迎语改用固定高度居中：高度取「输入框仍是单行时」的消息区高度
     （--chat-welcome-h 由 syncBaseHeights() 量得，兜底值 ≈ 单行输入栏 + 底部导航）。
     输入框被撑高时 .messages 会被压缩，但 .welcome 高度不变、内容在固定高度里居中，
     所以欢迎语不会被往上顶。 */
  .welcome { min-height: 0; height: var(--chat-welcome-h, calc(100vh - 178px)); }
  .welcome-content { padding: 20px 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 0; }
  .ai-character { transform: scale(1.15); margin-bottom: 16px; }
  .welcome-greeting h1 { font-size: 22px; margin-bottom: 6px; }
  .welcome-greeting p { font-size: 13px; margin-bottom: 20px; }
  .msg-row { padding: 0 12px; margin-bottom: 8px; margin-left: 0; margin-right: 0; }
  .msg-row.user { flex-direction: row-reverse; margin-left: 0; margin-right: 0; }
  .bubble { padding: 8px 12px; font-size: 13px; }
  .input-bar { padding: 8px 10px; }
  /* 移动端输入栏比桌面端高（输入框一行 + 按钮一行），兜底值同步放大 */
  .recommend-bar { bottom: var(--chat-input-bar-h, 122px); }
  .input-container { border-radius: 20px; padding: 10px; }
  /* 移动端输入区改为「输入框一行 + 按钮一行」：
     左侧深度思考胶囊，右侧附件/麦克风/发送 */
  .input-field-wrap { flex: 1 0 100%; }
  .char-counter { padding-right: 0; }
  .input-actions { justify-content: space-between; gap: 8px; margin-top: 6px; padding: 0; flex-wrap: wrap; }
  .toggle-btn { padding: 5px 11px; font-size: 12px; }
  .feature-toggles { margin-bottom: 6px; }
  .chat-textarea { font-size: 14px; }
  .action-icon-btn { width: 28px; height: 28px; }
  .deep-think-icon { width: 14px; height: 14px; }
  .send-btn { width: 30px; height: 30px; }
  .msg-actions { opacity: 1; }
}
</style>
