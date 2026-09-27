<template>
  <Teleport to="body">
    <Transition name="voice-overlay">
      <div v-if="visible" class="voice-overlay" @click.self="handleClose">
        <div class="voice-container">
          <!-- 顶部导航 -->
          <div class="voice-top-bar">
            <div class="top-left" />
            <div class="top-center" />
            <div class="top-right">
              <button class="top-btn end-top-btn" @click="handleClose" title="结束通话">
                <el-icon :size="20"><CloseBold /></el-icon>
              </button>
            </div>
          </div>

          <!-- 中央可视化区 -->
          <div class="voice-visual-area">
            <div class="mascot-wrap">
              <MianCharacter :state="charState" />
            </div>
            <div class="wave-container">
              <div
                v-for="(val, i) in visualBars"
                :key="i"
                class="wave-bar"
                :style="{
                  height: val + 'px',
                  background: barColors[i],
                }"
              />
            </div>
            <!-- 人脸情绪识别面板（视觉模块，通话自动开启） -->
            <div class="emotion-panel" :class="{ 'emotion-on': camActive }">
              <div class="emotion-row">
                <span class="emotion-badge">{{ camActive ? '🎥 视觉情绪' : '👁️ 视觉模块' }}</span>
                <span v-if="camLoading" class="emotion-auto-hint">启动中…</span>
                <span v-else-if="!camActive" class="emotion-auto-hint">通话自动开启</span>
              </div>
              <template v-if="camActive">
                <div class="emotion-body">
                  <div class="cam-thumb">
                    <video
                      v-if="camVideo"
                      ref="camVideoRef"
                      class="cam-video"
                      muted
                      playsinline
                    />
                    <div v-else class="cam-placeholder">📷</div>
                  </div>
                  <div class="emotion-state">
                    <div v-if="currentEmotion" class="current-emoji">{{ currentEmotionEmoji }}</div>
                    <div v-else class="current-emoji dim">🔍</div>
                    <div class="emotion-text">{{ currentEmotion ? currentEmotion.label : '正在检测表情…' }}</div>
                    <div v-if="currentEmotion" class="emotion-conf">
                      {{ Math.round(currentEmotion.confidence * 100) }}% 置信
                    </div>
                  </div>
                </div>
              </template>
              <div v-else class="emotion-hint">开启摄像头，让绵小城感知你的情绪、更懂你</div>
              <div v-if="camError" class="emotion-error">{{ camError }}</div>
            </div>
          </div>

          <!-- 状态文字 -->
          <div class="voice-status">
            <span v-if="callState === 'idle'">点击麦克风开始通话</span>
            <span v-else-if="callState === 'connecting'">连接中...</span>
            <span v-else-if="callState === 'listening'">正在聆听...</span>
            <span v-else-if="callState === 'processing'" class="pulse">思考中...</span>
            <span v-else-if="callState === 'speaking'">绵小城正在回复...</span>
            <span v-else-if="callState === 'error'" class="error-text">{{ errorMsg || '连接失败' }}</span>
          </div>

          <!-- 对话记录区（可滚动） -->
          <div class="voice-conversation" ref="convListRef">
            <div v-if="chatHistory.length === 0" class="voice-conv-empty">
              开始说话，识别出的文字和绵小城的回复会显示在这里
            </div>
            <TransitionGroup name="conv-item">
              <div
                v-for="entry in chatHistory"
                :key="entry.id"
                :class="['conv-row', entry.role]"
              >
                <div class="conv-bubble">
                  <span v-if="entry.role === 'assistant' && !entry.text" class="conv-typing">
                    <i v-for="d in 3" :key="d" class="typing-dot" :style="{ animationDelay: (d * 0.15) + 's' }" />
                  </span>
                  <template v-else>{{ entry.text }}</template>
                </div>
              </div>
            </TransitionGroup>
          </div>

          <!-- 底部控制栏 -->
          <div class="voice-controls">
            <!-- 麦克风 -->
            <button
              :class="['control-btn', { active: callState === 'listening', muted: isMuted }]"
              @click="handleMicClick"
              :disabled="callState === 'connecting'"
            >
              <el-icon :size="24"><Microphone /></el-icon>
              <div v-if="isMuted" class="btn-slash" />
            </button>
          </div>

          <!-- 底部声明 -->
          <p class="voice-disclaimer">内容由 AI 生成</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Microphone, CloseBold,
} from '@element-plus/icons-vue'
import { useVoiceCall, type VoiceState } from '@/composables/useVoiceCall'
import { useAudioVisualizer } from '@/composables/useAudioVisualizer'
import { useEmotionDetection, EMOTION_EMOJI } from '@/composables/useEmotionDetection'
import { batchRecordEmotion } from '@/api/emotion'
import MianCharacter from './MianCharacter.vue'

const props = defineProps<{
  visible: boolean
  conversationId?: number | null
}>()

const emit = defineEmits<{ close: [] }>()

const callState = ref<VoiceState>('idle')
const isMuted = ref(false)
const errorMsg = ref('')
const audioLevel = ref(0)
const convListRef = ref<HTMLElement>()

// 对话历史记录
interface ChatEntry { id: string; role: 'user' | 'assistant'; text: string }
const chatHistory = ref<ChatEntry[]>([])

// 自动滚动到底部
function scrollChatToBottom() {
  nextTick(() => {
    if (convListRef.value) {
      convListRef.value.scrollTop = convListRef.value.scrollHeight
    }
  })
}

watch(chatHistory, scrollChatToBottom, { deep: true })

const { frequencyData, connect, disconnect: disconnectVisualizer } = useAudioVisualizer(9)

const { state, isMuted: voiceMuted, startCall, endCall, toggleMute, send, cancelPlayback } = useVoiceCall({
  get conversationId() { return props.conversationId },
  onStateChange: (s) => {
    callState.value = s
  },
  onAudioLevel: (level) => { audioLevel.value = level },
  onTranscript: (text, final) => {
    if (final && text.trim()) {
      // 新的一轮提问开始：此前的 AI 回答作废，只保留最近一次输出
      discardAI = false
      // 用户说完，追加用户消息 + 空的 AI 占位（等待回复）
      chatHistory.value.push({ id: `u-${Date.now()}`, role: 'user', text })
      chatHistory.value.push({ id: `a-${Date.now()}`, role: 'assistant', text: '' })
    }
  },
  onSpeechStart: () => {
    // 用户开口：AI 正在输出的内容立即作废（界面只保留最新一轮）
    discardAI = true
    const last = chatHistory.value[chatHistory.value.length - 1]
    if (last && last.role === 'assistant') {
      chatHistory.value.pop()
    }
  },
  onAIText: (text) => {
    if (discardAI) return
    // 实时流式更新最后一条 AI 消息
    const last = chatHistory.value[chatHistory.value.length - 1]
    if (last && last.role === 'assistant') {
      last.text += text
    } else {
      chatHistory.value.push({ id: `a-${Date.now()}`, role: 'assistant', text })
    }
  },
  onError: (msg) => { errorMsg.value = msg },
})

// 同步 muted 状态
watch(voiceMuted, (v) => { isMuted.value = v })

// ---- 视觉情绪模块（通话自动开启） ----
const emotionDetection = useEmotionDetection()
const camActive = ref(false)
const camLoading = ref(false)
const currentEmotion = ref<{ emotion: string; label: string; confidence: number } | null>(null)
const camError = ref('')
const camVideo = ref<'cam' | null>(null) // 标记视频元素是否就绪
const camVideoRef = ref<HTMLVideoElement>()
// 用户开口后，AI 旧回答（文字/语音）作废，只保留最近一轮
let discardAI = false

const currentEmotionEmoji = computed(() => {
  if (!currentEmotion.value) return ''
  return EMOTION_EMOJI[currentEmotion.value.emotion] ?? '🙂'
})

// 表情变化时：实时展示 + 通过 WS 上报给后端（结合情绪作答）
watch(() => emotionDetection.current.value, (snap) => {
  if (snap) {
    currentEmotion.value = snap
    if (callState.value !== 'idle' && callState.value !== 'error') {
      send({ type: 'emotion', emotion: snap.emotion, confidence: snap.confidence })
    }
  }
})

// 通话开始后自动开启情绪监测（无需人为开启；摄像头被拒不阻断通话）
async function startEmotionAuto() {
  if (camActive.value || camLoading.value) return
  camError.value = ''
  camLoading.value = true
  try {
    const ok = await emotionDetection.start((snap) => {
      currentEmotion.value = snap
      if (callState.value !== 'idle' && callState.value !== 'error') {
        send({ type: 'emotion', emotion: snap.emotion, confidence: snap.confidence })
      }
    })
    if (ok) {
      camActive.value = true
      await nextTick()
      const vNode = camVideoRef.value
      if (vNode) {
        const camStream = emotionDetection.getVideo()
        if (camStream && camStream.srcObject) {
          // 复用检测用的 video 源
          const src = new MediaStream(
            ((camStream.srcObject as MediaStream).getVideoTracks())
          )
          vNode.srcObject = src
          vNode.muted = true
          vNode.playsInline = true
          await vNode.play().catch(() => {})
          camVideo.value = 'cam'
        }
      }
    } else {
      camError.value = emotionDetection.error.value || '摄像头启动失败'
    }
  } finally {
    camLoading.value = false
  }
}

// 声波柱映射：频率数据 → 像素高度（小幅度）
const visualBars = computed(() => {
  return frequencyData.value.map((v) => {
    return Math.max(3, Math.min(32, v * 50))
  })
})

// 吉祥物状态映射
const charState = computed<'idle' | 'thinking' | 'speaking'>(() => {
  if (callState.value === 'processing') return 'thinking'
  if (callState.value === 'speaking') return 'speaking'
  return 'idle'
})

// 柱子颜色：中心亮，两侧暗
const barColors = [
  '#5b8def', '#409eff', '#66b1ff', '#8fc7ff', '#c6e2ff',
  '#8fc7ff', '#66b1ff', '#409eff', '#5b8def',
]

// 可视化脉动动画（idle 状态）— 小幅度
let pulseRaf = 0
function startPulse() {
  const bars = frequencyData.value
  let t = 0
  function tick() {
    t += 0.03
    for (let i = 0; i < bars.length; i++) {
      bars[i] = 0.08 + 0.04 * Math.sin(t + i * 0.5)
    }
    frequencyData.value = [...bars]
    pulseRaf = requestAnimationFrame(tick)
  }
  tick()
}
function stopPulse() {
  if (pulseRaf) cancelAnimationFrame(pulseRaf)
}

// 监听 visible 变化
watch(() => props.visible, async (v) => {
  if (v) {
    errorMsg.value = ''
    chatHistory.value = []
    if (callState.value === 'idle') {
      startPulse()
    }
  } else {
    stopPulse()
    cancelPlayback()
    await flushEmotionRecords()
    emotionDetection.stop()
    currentEmotion.value = null
    camVideo.value = null
    camActive.value = false
    endCall()
    disconnectVisualizer()
  }
})

// 挂断/关闭时：批量上报本通电话的情绪记录（情绪垃圾桶）
async function flushEmotionRecords() {
  const timeline = emotionDetection.timeline.value
  if (!timeline.length) return
  const records = timeline.slice(-200).map((s) => ({ emotion: s.emotion, confidence: s.confidence }))
  emotionDetection.clearTimeline()
  try {
    await batchRecordEmotion(records)
  } catch {
    // 静默失败不阻断挂断
  }
}

// 监听 state 变化，连接可视化器
watch(state, (s) => {
  if (s === 'listening' || s === 'speaking') {
    stopPulse()
    // 当有音频源时，可视化器由 useVoiceCall 内部管理
  } else if (s === 'idle') {
    startPulse()
  }
})

async function handleMicClick() {
  if (callState.value === 'idle' || callState.value === 'error') {
    try {
      const source = await startCall()
      if (source) {
        connect(source)
        // 通话自动开启情绪监测（不需要人为开启）
        startEmotionAuto()
      }
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : '启动失败')
    }
  } else if (callState.value === 'listening' || callState.value === 'processing' || callState.value === 'speaking') {
    toggleMute()
  }
}

function handleClose() {
  stopPulse()
  cancelPlayback()
  endCall()
  disconnectVisualizer()
  flushEmotionRecords()
  emotionDetection.stop()
  currentEmotion.value = null
  camVideo.value = null
  camActive.value = false
  emit('close')
}

onUnmounted(() => {
  stopPulse()
  emotionDetection.stop()
})
</script>

<style scoped>
.voice-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: linear-gradient(180deg, #f0f7ff 0%, #e8f4fd 45%, #f0f7ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0 20px;
  padding-top: env(safe-area-inset-top, 20px);
  padding-bottom: env(safe-area-inset-bottom, 20px);
}

/* 顶部导航 */
.voice-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0 8px;
  flex-shrink: 0;
}

.top-left, .top-right {
  width: 48px;
  display: flex;
  align-items: center;
}

.top-right {
  justify-content: flex-end;
}

.top-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.7);
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.top-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.95);
}

.top-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.top-btn.text-btn {
  font-size: 15px;
  font-weight: 600;
  color: #666;
}

.end-top-btn {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.end-top-btn:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.22);
}

.top-center {
  display: flex;
  justify-content: center;
}

/* 中央可视化区 */
.voice-visual-area {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 4px 0;
}

.mascot-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  transform: scale(0.85);
  transform-origin: bottom center;
}

.wave-container {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 40px;
  margin-top: -4px;
}

.wave-bar {
  width: 4px;
  min-height: 4px;
  border-radius: 2px;
  transition: height 0.08s ease;
}

/* 视觉情绪面板 */
.emotion-panel {
  width: 100%;
  max-width: 340px;
  margin: 6px auto 0;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(91, 141, 239, 0.16);
  border-radius: 16px;
  padding: 10px 14px;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.08);
  backdrop-filter: blur(6px);
}

.emotion-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.emotion-badge {
  font-size: 12px;
  font-weight: 600;
  color: #5b8def;
}

.emotion-hint {
  font-size: 12px;
  color: rgba(91, 141, 239, 0.6);
  padding: 4px 0 2px;
}

.emotion-auto-hint {
  font-size: 12px;
  color: rgba(91, 141, 239, 0.55);
}

.emotion-error {
  font-size: 12px;
  color: #f56c6c;
  padding: 4px 0 0;
}

.emotion-body {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.cam-thumb {
  width: 92px;
  height: 92px;
  border-radius: 14px;
  overflow: hidden;
  background: #101018;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(91, 141, 239, 0.3);
}

.cam-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scaleX(-1); /* 镜像 */
}

.cam-placeholder {
  font-size: 28px;
  color: rgba(255, 255, 255, 0.4);
}

.emotion-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
}

.current-emoji {
  font-size: 38px;
  line-height: 1.1;
}

.current-emoji.dim {
  font-size: 30px;
  opacity: 0.45;
}

.emotion-text {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-top: 2px;
}

.emotion-conf {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

/* 状态文字 */
.voice-status {
  text-align: center;
  color: #5b8def;
  font-size: 14px;
  padding: 12px 0;
  flex-shrink: 0;
}

.voice-status .pulse {
  animation: textPulse 1.5s ease-in-out infinite;
}

@keyframes textPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.voice-status .error-text {
  color: #f56c6c;
}

/* 对话记录区（可滚动） */
.voice-conversation {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 20px 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.voice-conversation::-webkit-scrollbar {
  width: 4px;
}

.voice-conversation::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}

.voice-conv-empty {
  text-align: center;
  color: rgba(91, 141, 239, 0.55);
  font-size: 13px;
  padding: 24px 0;
}

.conv-row {
  display: flex;
}

.conv-row.user {
  justify-content: flex-end;
}

.conv-row.assistant {
  justify-content: flex-start;
}

.conv-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  line-height: 1.5;
  font-size: 14px;
  word-break: break-word;
  white-space: pre-wrap;
}

.conv-row.user .conv-bubble {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.conv-row.assistant .conv-bubble {
  background: rgba(255, 255, 255, 0.9);
  color: #1a1a1a;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

/* 打字动画 */
.conv-typing {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 2px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
  animation: typing-bounce 1.2s ease-in-out infinite;
}

@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-5px); opacity: 1; }
}

/* 消息进入动画 */
.conv-item-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.conv-item-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

/* 底部控制栏 */
.voice-controls {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 16px 0;
  flex-shrink: 0;
}

.control-btn {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.75);
  color: #5b8def;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.2s;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.12);
}

.control-btn:hover:not(:disabled) {
  background: #ffffff;
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.control-btn.active {
  background: rgba(64, 158, 255, 0.16);
  color: #409eff;
}

.control-btn.muted {
  background: rgba(245, 108, 108, 0.14);
  color: #f56c6c;
}

.btn-slash {
  position: absolute;
  width: 2px;
  height: 36px;
  background: #ef4444;
  transform: rotate(45deg);
  border-radius: 1px;
}

/* 底部声明 */
.voice-disclaimer {
  text-align: center;
  color: rgba(91, 141, 239, 0.4);
  font-size: 11px;
  padding: 8px 0;
  flex-shrink: 0;
}

/* 过渡动画 - 仅保留退出动画，取消入场动画 */
.voice-overlay-enter-active {
  transition: none;
}

.voice-overlay-leave-active {
  transition: opacity 0.2s ease;
}

.voice-overlay-leave-to {
  opacity: 0;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .voice-controls {
    gap: 16px;
  }

  .control-btn {
    width: 52px;
    height: 52px;
  }
}
</style>
