<template>
  <div class="chat-modern" ref="rootRef" :class="{ 'is-typing': isMobile && keyboardOpen }">
    <!-- 移动端顶栏
         左右两栏等宽（.mh-side）：右侧多了「新建对话」后，标题仍落在屏幕正中，
         不会因为按钮数量变化被挤偏。 -->
    <div v-if="showMenuButton" class="mobile-header">
      <div class="mh-side mh-left">
        <el-button text circle class="menu-toggle" aria-label="对话列表" @click="emit('toggleSidebar')">
          <div class="hamburger-icon">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </el-button>
      </div>

      <!-- 标题只做展示：对话的重命名/置顶/删除统一收在侧边栏列表里，对话页不再弹操作面板 -->
      <div class="mobile-header-title">
        <span class="title-text">{{ currentTitle }}</span>
      </div>

      <div class="mh-side mh-right">
        <el-button text circle class="menu-toggle" aria-label="语音通话" :disabled="loading" @click="handlePhoneCall">
          <PhoneIcon :size="20" :stroke-width="2" />
        </el-button>
        <!-- 新建对话：对齐 deepseek 移动端顶栏右侧的「方框+笔」图标，一点即开空白新会话 -->
        <button
          type="button"
          class="new-chat-btn"
          aria-label="新建对话"
          title="新建对话"
          :disabled="loading"
          @click="handleNewChat"
        >
          <svg
            class="new-chat-icon" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M12.4 4.4H6.6A2.4 2.4 0 0 0 4.2 6.8v10.6a2.4 2.4 0 0 0 2.4 2.4h10.6a2.4 2.4 0 0 0 2.4-2.4v-5.8" />
            <path d="M17.4 3.7a2.15 2.15 0 0 1 3.04 3.04l-8.06 8.06-3.86.82.82-3.86z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- ── 对话视图 ──
         用 v-show 切换会话时保持挂载：流式回复的定时器、滚动位置、输入草稿都不会丢。 -->
    <div class="chat-view">

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

    <div class="messages" ref="msgRef" :class="{ scrolling: store.messages.length > 0 }" @scroll="onMessagesScroll" @wheel="onMessagesWheel" @touchstart.passive="onMessagesTouchStart" @touchmove="onMessagesTouchMove" @touchend="pull.onEnd" @touchcancel="pull.onCancel">

      <!-- 移动端下拉刷新：吉祥物指示器（与消息页共用同一模块），撑开的高度即下拉位移 -->
      <PullRefreshIndicator v-if="pullRefreshEnabled" :indicator-style="pull.indicatorStyle" :active="pull.active" />

      <!-- Welcome Screen -->
      <div v-if="store.messages.length === 0" class="welcome">
        <div class="welcome-glow"></div>
        <div class="welcome-content">
          <div class="ai-character">
            <MianCharacter :state="charState" :bubble="charBubble" />
          </div>
          <div class="welcome-greeting">
            <h1>你好，我是<span class="gradient-text">{{ agentName }}</span></h1>
            <p>你的校园智能管家，所有事情直接跟我聊，一站式办结</p>
          </div>

          </div>
      </div>

      <!-- Messages（外层包裹：用 ResizeObserver 盯内容高度，任何增高都强制落到最新） -->
      <div ref="msgContentRef" class="msg-content">
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


    </div>

    <!-- 回到最新（QQ 式）：上翻阅读历史时不打断，出现按钮一键回到底部 -->
    <Transition name="scrollbtn">
      <button
        v-if="store.messages.length > 0 && !atBottom"
        type="button"
        class="scroll-bottom-btn"
        @click="scrollToBottom(true)"
      >
        <el-icon :size="15"><ArrowDown /></el-icon>
        <span>回到最新</span>
      </button>
    </Transition>

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
      ref="voiceCallRef"
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
            :placeholder="`给${agentName}发消息...`"
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

          <!-- 图片上传：紧邻文件按钮左侧，一点即开系统相册/文件选择 -->
          <el-tooltip content="上传图片" placement="top" :disabled="isMobile">
            <button
              type="button"
              class="action-icon-btn"
              aria-label="上传图片"
              :disabled="loading"
              @click="triggerImageUpload"
            >
              <el-icon :size="18"><Picture /></el-icon>
            </button>
          </el-tooltip>

          <!-- 文件上传：保持原回形针图标；点击直接选择文件（原下拉已拆分） -->
          <el-tooltip content="上传文件" placement="top" :disabled="isMobile">
            <button
              type="button"
              class="action-icon-btn"
              aria-label="上传文件"
              :disabled="loading"
              @click="triggerUpload"
            >
              <el-icon :size="18"><Paperclip /></el-icon>
            </button>
          </el-tooltip>
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
              <PhoneIcon :size="18" :stroke-width="2" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useConversationStore } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { sendChatMessage, fetchRecommendations } from '@/api/agent'
import { getToken } from '@/utils/token'
import { emitAgentDataChange } from '@/utils/dataSync'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useMediaRecorder } from '@/composables/useMediaRecorder'
import type { ChatMessage, Suggestion } from '@/types'
import {
  Promotion, Paperclip, Picture, Document, Microphone, CopyDocument, EditPen, ArrowDown, Close, Delete,
} from '@element-plus/icons-vue'
import { Phone as PhoneIcon } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useBackLayer } from '@/composables/useBackLayer'
import { useVisualViewport } from '@/composables/useVisualViewport'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import MianCharacter from './MianCharacter.vue'
import DeepThinking from './DeepThinking.vue'
import VoiceCallOverlay from './VoiceCallOverlay.vue'

const { isMobile } = useResponsive()
/* 键盘展开时收起吉祥物：屏幕变矮后它会把问候语挤到悬浮顶栏下面 */
const { keyboardOpen } = useVisualViewport()

// AI 助手称谓取自站点配置（管理端「自我称谓」）：各端对话界面同步显示
const { agentName } = useSiteConfig()

const charState = ref<'idle' | 'thinking' | 'speaking'>('idle')
const charBubble = ref('')
const deepThinkEnabled = ref(false)
const thinkingState = ref<'idle' | 'thinking' | 'done'>('idle')
const MAX_INPUT_CHARS = 8000

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher'; conversationId?: number | null; fetching?: boolean; showMenuButton?: boolean; pullRefresh?: boolean }>(), { role: 'student', fetching: false, showMenuButton: false, pullRefresh: false })
const emit = defineEmits<{ toggleSidebar: []; phoneCall: []; new: [] }>()
const showVoiceCall = ref(false)
const voiceConvId = ref<number | null>(null)
const voiceCallRef = ref<InstanceType<typeof VoiceCallOverlay> | null>(null)

async function handlePhoneCall() {
  // 首个同步动作：在用户手势内解锁音频上下文，保证接通后的语音能出声
  voiceCallRef.value?.primeAudio()
  // 预热表情模型（不弹摄像头）：让接通后更快取到首帧表情，用于定制问候语
  voiceCallRef.value?.prewarmEmotion()
  let cid = props.conversationId ?? null
  if (!cid) {
    // 建会话可能因弱网/接口挂住。此前是直接 await，一旦不返回，浮层根本不会出现，
    // 用户点了电话「没反应」。这里给 5 秒上限：超时就先按「无会话」拨通（后端允许
    // conversation_id 缺省，通话记录不绑定会话；可以正常通话）。
    cid = await Promise.race([
      convStore.createConversation('normal').then(c => c?.id ?? null).catch(() => null),
      new Promise<null>(resolve => setTimeout(() => resolve(null), 5000)),
    ])
  }
  voiceConvId.value = cid
  showVoiceCall.value = true
  // 拨通即接通（豆包式）：在用户手势内同步触发，解锁浏览器音频上下文；
  // 随后智能体先开口问候，无需用户手动开启语音
  voiceCallRef.value?.beginCall(cid)
}

/**
 * 新建对话（移动端顶栏入口，与语音通话按钮并排）：
 * 不在这里自作主张清状态，只把动作抛给外层 ChatShell 的 onNew —— 侧边栏「新对话」
 * 走的是同一条路径（setActive(null) + 清空消息 + chatKey++ 重挂载），
 * 两个入口共用一套逻辑，才不会出现「顶栏新建后草稿/滚动位置还挺着」这类状态差。
 */
function handleNewChat() {
  if (loading.value) return
  emit('new')
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
const route = useRoute()
const input = ref('')

// 当前对话标题
const currentTitle = computed(() => {
  if (!convStore.activeId) return '新对话'
  const conv = convStore.list.find(c => c.id === convStore.activeId)
  return conv?.title || '新对话'
})

const msgRef = ref<HTMLElement>()
/** 消息行的外层包裹：仅用于观察内容高度变化（不含欢迎语，避免破坏其 min-height:100% 居中） */
const msgContentRef = ref<HTMLElement>()
const rootRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement>()
const loading = ref(false)
const previewImage = ref('')

/**
 * 大图预览是一层页内浮层：系统返回先收它，而不是直接离开智能体页（见 useBackLayer）。
 * 与消息页同一套口径：图片预览、相机这类全屏浮层都要各自算一层。
 *
 * 必须放在 previewImage 声明之后：useBackLayer 内部的 watch 是 immediate 的，
 * 写在 ref 之前会立刻求值到 TDZ（Cannot access before initialization），
 * setup 直接抛错 —— 表现就是整个对话页白屏 / 加载不出来。
 */
useBackLayer(computed(() => isMobile.value && !!previewImage.value), () => closePreview())

/**
 * 移动端下拉刷新（由外层 ChatShell 通过 pull-refresh 开启，如学生端首页）：
 * 指示器与手势统一来自公共下拉刷新模块，这里只负责"拉什么"——无会话时刷新会话列表，
 * 否则按服务器最新结果重载当前会话消息。
 */
const pullRefreshEnabled = computed(() => props.pullRefresh && props.showMenuButton)

async function refreshFromPull() {
  if (loading.value) return
  const cid = convStore.activeId
  if (!cid) {
    await convStore.fetchList().catch(() => {})
    return
  }
  await convStore.fetchMessages(cid)
  store.replaceMessages(
    convStore.messages.map(m => ({
      id: m.id.toString(),
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
    })),
  )
  convStore.fetchList()
}

const pull = usePullRefresh(refreshFromPull, {
  enabled: () => pullRefreshEnabled.value,
})
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

/** textarea 是否仍是单行（未被输入内容撑高） */
function isTextareaSingleLine(): boolean {
  const ta = textareaRef.value
  if (!ta || singleLineContentHeight <= 0) return true
  return ta.getBoundingClientRect().height <= singleLineContentHeight + 1
}

/** 输入框里是否有附件/图片预览等额外内容（它们同样会撑高容器） */
function hasExtraInputContent(): boolean {
  return pendingFiles.value.length > 0 || !!pendingImagePreview.value
}

/**
 * 输入框是否已经撑高到该给推荐区让位。
 *
 * 判据：输入框容器是否比自己「单行且无附件」时的基准高度更高。
 * 这里刻意不再用「容器上沿 vs 容器底边 - 单行输入栏高度」推算——那个口径依赖
 * 输入栏高度的测量值，而移动端输入栏是「输入框一行 + 按钮一行」且按钮会换行重排，
 * 一旦基准测得偏小，这条线就永远落在容器上沿之下，推荐区被判成“被盖住”后不再出现
 * （桌面端是单行输入栏，只有真正敲多行时才会触发，所以不暴露）。
 *
 * 用容器自身高度对比基准还顺带解决两件事：输入框回落即自动恢复显示（无需额外复位）；
 * 不读推荐区自身的 rect —— 它可能正处于退场动画中，也可能已被 v-if 移除。
 */
function updateRecommendHidden() {
  const box = inputContainerRef.value
  if (!box || boxBaseHeight <= 0) return
  // 0.5px 容差：亚像素抖动不算被撑高
  recommendHidden.value = box.getBoundingClientRect().height > boxBaseHeight + 0.5
}

/** 单行基准（挂载时量一次，之后由 syncBaseHeights 在单行状态下持续校准） */
function ensureBaseMetrics() {
  const box = inputContainerRef.value
  if (!box || boxBaseHeight > 0) return
  boxBaseHeight = box.getBoundingClientRect().height
  if (textareaRef.value) singleLineContentHeight = textareaRef.value.scrollHeight
  const bar = box.closest('.input-bar') as HTMLElement | null
  const barH = bar ? bar.getBoundingClientRect().height : 0
  // 挂载时就把输入栏高度写进 CSS 变量：否则移动端会退回样式里的兜底值（122px），
  // 与真实的两行输入栏高度不符，推荐区会被白底输入栏压住
  if (barH > 0) rootRef.value?.style.setProperty('--chat-input-bar-h', `${barH}px`)
}

/**
 * 记录「输入框仍是单行时」的基准高度，写进两个 CSS 变量：
 * - --chat-welcome-h   消息区高度，供移动端欢迎语固定高度居中（输入框被撑高时欢迎语不会被往上顶）
 * - --chat-input-bar-h 输入栏高度，供「为你推荐」贴在输入栏正上方
 * 输入框已被撑高时不记录（此时量到的不是基准高度），但会重算推荐区显隐；
 * 布局变化（横竖屏、公告条出现、移动端按钮换行等）后会重新校准。
 */
function syncBaseHeights() {
  const root = rootRef.value
  const msg = msgRef.value
  const box = inputContainerRef.value
  if (!root || !msg || !box) return
  const ta = textareaRef.value
  // 空输入时 textarea 的高度就是单行基准：先刷新它，避免字体/断点变化后这个基准失效
  if (ta && !input.value.trim()) singleLineContentHeight = ta.scrollHeight
  if (!isTextareaSingleLine() || hasExtraInputContent()) {
    // 输入框已被撑开（多行 / 附件）：不覆盖基准，但撑高会影响推荐区显隐，需要重算
    updateRecommendHidden()
    return
  }
  // 单行状态下持续校准容器基准：字体、占位文案、移动端按钮换行都会改变输入框高度，
  // 只量一次会在这些变化之后留下错误基准（基准偏小 → 推荐区被判成被盖住而消失）
  const boxH = box.getBoundingClientRect().height
  if (boxH > 0) boxBaseHeight = boxH
  const h = msg.getBoundingClientRect().height
  // 键盘展开时消息区是被压缩过的，不能当基准：否则收起键盘后欢迎语按小高度居中，
  // 「你好，我是…」两行会被 overflow: hidden 裁掉。收起键盘后由 watch(keyboardOpen) 重算。
  if (h > 0 && !keyboardOpen.value) root.style.setProperty('--chat-welcome-h', h + 'px')
  const bar = box.closest('.input-bar') as HTMLElement | null
  const barH = bar ? bar.getBoundingClientRect().height : 0
  if (barH > 0) {
    root.style.setProperty('--chat-input-bar-h', `${barH}px`)
  }
}

/** 把悬浮顶栏的真实高度写进 --chat-header-h：欢迎语按它让位，适配不同状态栏 / 安全区高度 */
function syncHeaderHeight() {
  const el = rootRef.value?.querySelector('.mobile-header') as HTMLElement | null
  const h = el ? el.getBoundingClientRect().height : 0
  if (h > 0) rootRef.value?.style.setProperty('--chat-header-h', h + 'px')
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

/* 键盘收起后重新校准欢迎语基准高度：展开期间不写 --chat-welcome-h，
   收起后必须主动补一次，否则会沿用小屏幕下的旧基准 */
watch(keyboardOpen, (open) => {
  if (open) return
  nextTick(() => {
    requestAnimationFrame(() => {
      syncBaseHeights()
      updateRecommendHidden()
    })
  })
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

/** 推荐条数：固定 4 条（与后端 RECOMMEND_COUNT 一致，矮屏给欢迎语留出空间） */
const RECOMMEND_COUNT = 4
/** 推荐缓存有效期：期内直接复用，避免每次进页面都等一次生成（1~3s） */
const RECOMMEND_CACHE_TTL = 5 * 60 * 1000
const RECOMMEND_CACHE_KEY = 'campus_agent_recommend_cache_v2'

interface RecommendCacheEntry { items: string[]; at: number }

/** 推荐缓存：按角色分开存。
 * 必须落 localStorage：App 每次冷启动都是新的 WebView 会话，sessionStorage 会被清空 ——
 * 那正是「每次打开 App，为你推荐都要等很久才出来」的根因。localStorage 跨启动保留，
 * 进页面先用上次的真实结果铺上（stale-while-revalidate），后台再静默刷新。 */
const _recommendCache: Record<string, RecommendCacheEntry> = (() => {
  try {
    const raw = localStorage.getItem(RECOMMEND_CACHE_KEY)
    return raw ? (JSON.parse(raw) as Record<string, RecommendCacheEntry>) : {}
  } catch {
    return {}
  }
})()

function saveRecommendCache() {
  try {
    localStorage.setItem(RECOMMEND_CACHE_KEY, JSON.stringify(_recommendCache))
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
  ],
  teacher: [
    '帮我查看今天的待办任务',
    '查一下班级学生的考勤情况',
    '帮我看看最近的校园公告',
    '查询学生的成长记录',
  ],
}

// 有缓存就直接用它（也是后端上次给的真实结果）；否则先留空，等接口回来再出现
// 缓存同样按 RECOMMEND_COUNT 截断：旧版本缓存里可能存着更多条，5 分钟 TTL 内不会刷新
const recommendItems = ref<string[]>(
  _recommendCache[props.role]?.items?.length
    ? [..._recommendCache[props.role].items].slice(0, RECOMMEND_COUNT)
    : []
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
/** 单行、无附件状态下的输入框容器高度（推荐区是否需要让位的基准） */
let boxBaseHeight = 0
/** 空输入（单行）时 textarea 的 scrollHeight */
let singleLineContentHeight = 0
/** 监听消息区尺寸变化的观察者：布局变化时重新校准欢迎语基准高度 */
let msgObserver: ResizeObserver | null = null
/** 监听输入栏尺寸变化的观察者：移动端按钮换行等会改变输入栏高度，需重新校准 */
let inputBarObserver: ResizeObserver | null = null
/** 监听悬浮顶栏尺寸变化的观察者：安全区 / 字号不同时机型高度不同，欢迎语要按真实高度让位 */
let headerObserver: ResizeObserver | null = null
/** 监听消息内容高度变化的观察者：任何增高（流式正文/思考/建议标签/图片）都强制落到最新 */
let msgContentObserver: ResizeObserver | null = null

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
/* 图片 / 文件各由一个按钮触发，原先的「附件下拉」已移除 */

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
  // 本轮生成期间逐帧贴底（含思考展开阶段），直到回复结束
  startStickLoop()

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
        stopStickLoop()
        loading.value = false
        charState.value = 'idle'
        charBubble.value = ''
        lastAssistantContent = full
        // 兜底：流结束但一个字都没收到（服务端异常 / SSE 帧损坏）时，别留一个永远转圈的空气泡
        const lastMsg = store.messages[store.messages.length - 1]
        if (lastMsg?.role === 'assistant' && !lastMsg.content) {
          store.updateMessage(lastMsg.id, { content: '抱歉，我暂时无法回答，请稍后再试。' })
        }
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
      // 本质回答入口已下线，固定走常规模式（服务端仍保留 answer_mode 参数）
      'normal',
      (meta) => {
        // 服务端已把本轮回复落库：同步标题并标记已保存，避免前端重复写入
        metaReceived = true
        if (meta?.title && cid) {
          convStore.patchConversation(cid, { title: meta.title, updated_at: new Date().toISOString() })
        }
      },
    )

    // 智能体这一轮可能通过工具调用改了任务 / 学生 / 关怀数据：
    // 立即广播变更，让已打开的教师端页面马上静默刷新（见 utils/dataSync.ts），
    // 不再等 30 秒轮询或页面重新挂载。
    emitAgentDataChange()

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
    stopStickLoop()
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

/**
 * 是否贴底跟随（QQ 式）：
 * 默认**始终跟随最新消息**；只有在用户「主动上翻」时才暂停，回到底部或发送后立刻恢复。
 * 注意：暂停只能由真实的滚动手势触发——绝不能用「当前滚动距离」来判定，
 * 否则内容增长与程序化滚动的竞态会把跟随误关，导致必须手动点「回到最新」。
 */
const atBottom = ref(true)
/** 判定为「已经到底」的容差（px） */
const BOTTOM_THRESHOLD = 40

function scrollToBottom(force = false) {
  if (force) atBottom.value = true
  if (!atBottom.value) return
  nextTick(() => {
    const el = msgRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

/** 滚动位置回到（或本来就在）底部 → 恢复跟随 */
function onMessagesScroll() {
  const el = msgRef.value
  if (!el) return
  if (el.scrollHeight - el.scrollTop - el.clientHeight <= BOTTOM_THRESHOLD) {
    atBottom.value = true
  }
}

/** 列表是否真的可滚动（内容未超出时不存在"上翻"，不应暂停跟随） */
function listScrollable(): boolean {
  const el = msgRef.value
  return !!el && el.scrollHeight - el.clientHeight > 1
}

/**
 * 下一帧强制贴底（与布局同帧合并，避免高频流式增量反复触发）。
 * 只要仍处于跟随状态就执行——用于兜住「消息加载完/建议标签渲染/图片/换行」等
 * 由内容高度变化引起的增高，确保发消息后始终落在最新一屏。
 */
let stickRaf = 0
function scheduleStick() {
  if (!atBottom.value) return
  if (stickRaf) return
  stickRaf = requestAnimationFrame(() => {
    stickRaf = 0
    const el = msgRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

/**
 * 生成期间的「逐帧贴底」循环。
 * 从发送到本轮结束一直开着：思考（深度思考）展开、正文流式、建议标签渲染……
 * 只要内容高度有任何变化都会在下一帧贴底，不依赖 ResizeObserver 的触发时机，
 * 因此不会出现「思考完整段才回到最新」。
 */
let stickLoop = 0
function startStickLoop() {
  if (stickLoop) return
  const tick = () => {
    if (atBottom.value) {
      const el = msgRef.value
      if (el) el.scrollTop = el.scrollHeight
    }
    stickLoop = requestAnimationFrame(tick)
  }
  stickLoop = requestAnimationFrame(tick)
}

function stopStickLoop() {
  if (stickLoop) {
    cancelAnimationFrame(stickLoop)
    stickLoop = 0
  }
}

/** 用户主动上翻（滚轮向上）→ 暂停自动跟随 */
function onMessagesWheel(e: WheelEvent) {
  if (e.deltaY >= 0) return
  if (!listScrollable()) return
  atBottom.value = false
}

let touchStartY = 0
function onMessagesTouchStart(e: TouchEvent) {
  touchStartY = e.touches[0]?.clientY ?? 0
  pull.onStart(e)
}

/** 用户主动上翻（手指向下拖拽 = 内容上移看历史）→ 暂停自动跟随；顶部继续下拉则交给下拉刷新 */
function onMessagesTouchMove(e: TouchEvent) {
  pull.onMove(e)
  const y = e.touches[0]?.clientY ?? 0
  if (y - touchStartY > 6 && listScrollable()) atBottom.value = false
}

// 新增消息（用户发送 / 切换会话 / 语音通话回填）一律直接展示最新
watch(() => store.messages.length, () => {
  atBottom.value = true
  scrollToBottom()
})

/**
 * 流式回复期间内容持续增长，长度不变、长度 watch 抓不到：
 * 盯最后一条消息的正文/思考长度，保证首字到正文任一时刻都贴底跟随。
 */
watch(
  () => {
    const last = store.messages[store.messages.length - 1]
    return last ? `${last.content?.length ?? 0}:${last.thinking?.length ?? 0}` : ''
  },
  () => scrollToBottom(),
)

/** 通知直达：/student/agent?conv=<id>，进入即打开对应会话。
    换会话三件套照抄 handleVoiceClose：fetchMessages → replaceMessages → setActive/fetchList。 */
function openConvFromQuery() {
  const convParam = Number(route.query.conv)
  if (props.role !== 'student' || !Number.isFinite(convParam) || convParam <= 0) return
  convStore.fetchMessages(convParam).then(() => {
    store.replaceMessages(
      convStore.messages.map(m => ({
        id: m.id.toString(),
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
      })),
    )
    convStore.setActive(convParam)
    convStore.fetchList()
  })
}

onMounted(() => {
  openConvFromQuery()
  scrollToBottom(true)
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
  // 内容高度变化（流式正文/思考/建议标签/图片等）→ 只要仍跟随就强制落到最新
  if (msgContentRef.value && typeof ResizeObserver !== 'undefined') {
    msgContentObserver = new ResizeObserver(() => scheduleStick())
    msgContentObserver.observe(msgContentRef.value)
  }
  // 输入栏尺寸变化（移动端按钮换行、附件行出现等）同样要重新校准：
  // 只挂消息区/窗口 resize 会漏掉这些只改变输入栏高度的布局变化
  const inputBarEl = rootRef.value?.querySelector('.input-bar') as HTMLElement | null
  if (inputBarEl && typeof ResizeObserver !== 'undefined') {
    inputBarObserver = new ResizeObserver(() => {
      syncBaseHeights()
      updateRecommendHidden()
    })
    inputBarObserver.observe(inputBarEl)
  }
  const headerEl = rootRef.value?.querySelector('.mobile-header') as HTMLElement | null
  if (headerEl && typeof ResizeObserver !== 'undefined') {
    headerObserver = new ResizeObserver(() => syncHeaderHeight())
    headerObserver.observe(headerEl)
  }
  syncHeaderHeight()
  window.addEventListener('resize', handleViewportResize)
  // 动态获取推荐（缓存新鲜则直接复用，否则后台静默刷新）
  loadRecommendations()
})

// 同路由 push（/student/agent?conv=）不会重挂载本组件，query 变化必须靠 watch 兜住
watch(() => route.query.conv, openConvFromQuery)

onUnmounted(() => {
  closePreview()
  headerObserver?.disconnect()
  headerObserver = null
  msgObserver?.disconnect()
  msgObserver = null
  inputBarObserver?.disconnect()
  inputBarObserver = null
  msgContentObserver?.disconnect()
  msgContentObserver = null
  if (stickRaf) {
    cancelAnimationFrame(stickRaf)
    stickRaf = 0
  }
  stopStickLoop()
  window.removeEventListener('resize', handleViewportResize)
})

/**
 * 供外部入口（教师端桌面桌宠的快捷指令）直接发一条消息。
 * 复用面板内同一套发送链路，保证流式回包、自动滚动、落库行为完全一致。
 */
async function sendText(text: string) {
  const t = text.trim()
  if (!t || loading.value) return
  input.value = t
  await send()
}

defineExpose({ sendText })
</script>

<style scoped>
.chat-modern { 
  position: relative;
  display: flex; 
  flex-direction: column; 
  /* 撑满父级内容盒，而不是写死 100vh：对话页上方还有顶栏（桌面端约 56px），
     移动端页面根还带 82px 的悬浮胶囊底部让位。用 100vh 面板会比可用区域更高，
     底部「深度思考 / 上传 / 发送」这一行被顶到视口外（移动端还会压在胶囊下面），
     表现为功能点不到、像“无法启用”。height:100% 跟随父级（父级已按 --ui-zoom
     缩放，故不再需要 100vh / --ui-zoom 的换算）。 */
  height: 100%; 
  background: linear-gradient(180deg, #f0f8ff 0%, #fafcff 40%, #fff 100%); 
  overflow: hidden;
}

/* ── 对话视图 ──
   撑满剩余高度；切换会话时由外层 key 重挂载。 */
.chat-view {
  display: flex;
  flex-direction: column;
  flex: 1 1 0%;
  min-height: 0;
}

/* ── Messages Area ── */
/* flex-basis:0 + grow:1 占满剩余空间；shrink:0 让输入框长高时不压缩消息区。
   否则消息区被压缩、其内容锚在顶部，欢迎语就会被顶上去。 */
.messages { flex: 1 0 0%; overflow: hidden; padding: 0; min-height: 0; overscroll-behavior-y: contain; }
.messages.scrolling { overflow-y: auto; padding: 12px 0; scroll-behavior: auto; }
.messages.scrolling::-webkit-scrollbar { width: 4px; }
.messages.scrolling::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.messages.scrolling::-webkit-scrollbar-thumb:hover { background: #b0b5bd; }

/* ── 回到最新（QQ 式）──
   居中悬浮在输入栏上方：只有用户上翻、脱离底部时才出现，点击立即回到底部。 */
.scroll-bottom-btn {
  position: absolute;
  left: 50%;
  bottom: calc(var(--chat-input-bar-h, 112px) + 14px);
  transform: translateX(-50%);
  z-index: 15;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, .96);
  color: #4b5563;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(15, 23, 42, .12);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  transition: background .18s, color .18s, border-color .18s;
}
.scroll-bottom-btn:hover { color: #409eff; border-color: #a9c6f0; background: #f7faff; }
.scrollbtn-enter-active,
.scrollbtn-leave-active { transition: opacity .18s ease, transform .18s ease; }
.scrollbtn-enter-from,
.scrollbtn-leave-to { opacity: 0; transform: translateX(-50%) translateY(6px); }
.scrollbtn-enter-to,
.scrollbtn-leave-from { opacity: 1; transform: translateX(-50%) translateY(0); }

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
  /* 不做内部滚动：矮屏上宁可贴近欢迎语，也保证推荐条目完整可见（原先按剩余高度压限高会出滚动条） */
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

/* 功能开关（输入框下方操作栏里的胶囊按钮） */
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

/* 图片 / 文件上传按钮：并排放在麦克风左侧，间距沿用 .input-actions 的 2px */
.input-actions :deep(.el-tooltip) { display: inline-flex; }

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
  font-size: 16px;
  font-weight: 600;
  color: #333;
  flex: 1;
  min-width: 0;
  padding: 0 4px;
  cursor: default;
}
.mobile-header-title .title-text {
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.menu-toggle { width: 36px; height: 36px; color: #555; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.menu-toggle:hover { color: #409eff; background: rgba(64,158,255,.08); }

/* 顶栏左右两侧等宽：右侧从 1 个按钮变 2 个时，中间标题仍居中（--mh-btn 跟随按钮尺寸） */
.mobile-header { --mh-btn: 36px; }
.mh-side {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 0 0 auto;
  width: calc(var(--mh-btn) * 2 + 2px);
}
.mh-left { justify-content: flex-start; }
.mh-right { justify-content: flex-end; }

/* 新建对话：对齐 deepseek 移动端——纯线条「方框+笔」，默认无底色、中性灰，
   只有按下（.is-pressed 由 :active 提供）才浮出浅灰圆角。
   刻意不复用 .menu-toggle：那个类带蓝色 hover，移动端 tap 后 :hover 会粘住，
   图标会一直亮着蓝，和顶栏其余控件不搭。 */
.new-chat-btn {
  width: var(--mh-btn, 36px);
  height: var(--mh-btn, 36px);
  color: #555;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background .16s ease, color .16s ease, transform .12s ease;
}
/* 图标尺寸按「视觉占位」对齐同排的电话图标（lucide 20px：路径 20/24 格 + 2 描边 → 实际着墨 ~18.3px）。
   这个「方框+笔」的路径只占 16.2/24 格，同样给 20px 会小一圈，看着就是「两个图标不一样大」；
   放大到 24px 后着墨 ~17.9px、描边 1.7px，与电话图标基本一致。 */
.new-chat-btn .new-chat-icon { width: 24px; height: 24px; display: block; }
.new-chat-btn:active:not(:disabled),
.new-chat-btn:focus-visible {
  transform: scale(.92);
  background: rgba(17, 24, 39, .07);
  color: #1f2328;
}
.new-chat-btn:disabled { opacity: .45; cursor: not-allowed; }
/* 有真实指针时才给 hover 反馈；触屏不参与，避免 tap 后高亮残留 */
@media (hover: hover) and (pointer: fine) {
  .new-chat-btn:hover:not(:disabled) { color: #1f2328; background: rgba(17, 24, 39, .05); }
}

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
  /* 注意：这里的 padding 简写必须带上安全区，否则会把基础样式里
     padding-top: calc(6px + env(safe-area-inset-top)) 覆盖掉 —— 顶栏标题会重新钻到
     状态栏/挖孔下面，同时消息区预留的 58px 顶部内边距会露出一大块空白。 */
  .mobile-header { padding: calc(6px + env(safe-area-inset-top, 0px)) 6px 6px; gap: 2px; --mh-btn: 32px; }
  .mobile-header-title { font-size: 15px; padding: 0 2px; }
  .menu-toggle { width: 32px; height: 32px; }
  .menu-toggle :deep(.el-icon) { font-size: 18px; }
  /* 与同排电话图标等大：覆盖基础尺寸时不能跟着按钮一起缩小，否则又会小一圈 */
  .new-chat-btn .new-chat-icon { width: 24px; height: 24px; }
  /* 欢迎语改用固定高度居中：高度取「输入框仍是单行时」的消息区高度
     （--chat-welcome-h 由 syncBaseHeights() 量得，兜底值 ≈ 单行输入栏 + 底部导航）。
     输入框被撑高时 .messages 会被压缩，但 .welcome 高度不变、内容在固定高度里居中，
     所以欢迎语不会被往上顶。 */
  .welcome {
    min-height: 0;
    height: var(--chat-welcome-h, calc(100vh - 178px));
    /* 顶栏是 absolute 悬浮层：欢迎语按实测顶栏高度让位（--chat-header-h 由 ResizeObserver 写），
       兜底 58px + 安全区，兼容顶栏尚未挂载 / 不支持 ResizeObserver 的情况 */
    padding-top: var(--chat-header-h, calc(58px + env(safe-area-inset-top, 0px)));
    box-sizing: border-box;
  }
  .welcome-content {
    margin: 0 auto;
    padding: 20px 16px;
    display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 0;
  }
  .ai-character { transform: scale(1.15); margin-bottom: 16px; }
  /* 键盘展开（用户正在输入）时：吉祥物直接收起，欢迎区高度改跟随可见的消息区，
     问候语仍然居中显示，不会被压缩后的视口裁掉 */
  /* 键盘展开（正在输入）时：吉祥物、问候语 / slogan、为你推荐一起淡出收起，只留输入区；
     键盘收起后再淡入恢复。用 opacity + visibility 过渡（display 不可动画）。 */
  .welcome,
  .recommend-bar {
    transition: opacity .18s ease, transform .18s ease, visibility 0s linear;
  }
  .chat-modern.is-typing .welcome,
  .chat-modern.is-typing .recommend-bar {
    opacity: 0;
    transform: translateY(8px);
    visibility: hidden;
    pointer-events: none;
    /* visibility 延迟到淡出结束再切，避免动画被瞬间掐断 */
    transition: opacity .16s ease, transform .16s ease, visibility 0s linear .16s;
  }
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
  .chat-textarea { font-size: 14px; }
  .action-icon-btn { width: 28px; height: 28px; }
  .deep-think-icon { width: 14px; height: 14px; }
  .send-btn { width: 30px; height: 30px; }
  .msg-actions { opacity: 1; }
}
</style>
