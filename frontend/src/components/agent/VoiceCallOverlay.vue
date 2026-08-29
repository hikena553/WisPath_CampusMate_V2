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

          <!-- AI 字幕 -->
          <div v-if="aiSubtitle" class="ai-subtitle">
            {{ aiSubtitle }}
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

            <!-- 对话记录 -->
            <button
              :class="['control-btn', { active: showChatPanel }]"
              @click="showChatPanel = !showChatPanel"
            >
              <el-icon :size="24"><ChatDotRound /></el-icon>
            </button>
          </div>

          <!-- 液态玻璃对话框 -->
          <Transition name="glass-panel">
            <div v-if="showChatPanel" class="glass-overlay" @click.self="showChatPanel = false">
              <div class="glass-panel">
                <div class="glass-header">
                  <span>对话记录</span>
                  <button class="glass-close" @click="showChatPanel = false">
                    <el-icon :size="16"><CloseBold /></el-icon>
                  </button>
                </div>
                <div class="glass-body" ref="chatListRef">
                  <div v-if="chatHistory.length === 0" class="glass-empty">
                    暂无对话记录
                  </div>
                  <div
                    v-for="(entry, i) in chatHistory"
                    :key="i"
                    :class="['glass-msg', entry.role]"
                  >
                    <div class="glass-msg-role">{{ entry.role === 'user' ? '你' : '绵小城' }}</div>
                    <div class="glass-msg-text">{{ entry.text }}</div>
                  </div>
                </div>
              </div>
            </div>
          </Transition>

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
  Microphone, CloseBold, ChatDotRound,
} from '@element-plus/icons-vue'
import { useVoiceCall, type VoiceState } from '@/composables/useVoiceCall'
import { useAudioVisualizer } from '@/composables/useAudioVisualizer'

const props = defineProps<{
  visible: boolean
  conversationId?: number | null
}>()

const emit = defineEmits<{ close: [] }>()

const callState = ref<VoiceState>('idle')
const isMuted = ref(false)
const errorMsg = ref('')
const aiSubtitle = ref('')
const audioLevel = ref(0)
const showChatPanel = ref(false)
const chatListRef = ref<HTMLElement>()

// 对话历史记录
interface ChatEntry { role: 'user' | 'assistant'; text: string }
const chatHistory = ref<ChatEntry[]>([])

// 自动滚动到底部
function scrollChatToBottom() {
  nextTick(() => {
    if (chatListRef.value) {
      chatListRef.value.scrollTop = chatListRef.value.scrollHeight
    }
  })
}

watch(chatHistory, scrollChatToBottom, { deep: true })

const { frequencyData, connect, disconnect: disconnectVisualizer } = useAudioVisualizer(9)

const { state, isMuted: voiceMuted, startCall, endCall, toggleMute } = useVoiceCall({
  get conversationId() { return props.conversationId },
  onStateChange: (s) => {
    callState.value = s
    // 当从 processing 变为 speaking 时，开始新的 AI 回复
    if (s === 'speaking') {
      aiSubtitle.value = ''
    }
  },
  onAudioLevel: (level) => { audioLevel.value = level },
  onTranscript: (text, final) => {
    if (final && text.trim()) {
      // 用户说完，添加到对话历史
      chatHistory.value.push({ role: 'user', text })
    }
  },
  onAIText: (text) => {
    aiSubtitle.value += text
    // 实时更新最后一条 AI 消息
    if (chatHistory.value.length > 0 && chatHistory.value[chatHistory.value.length - 1].role === 'assistant') {
      chatHistory.value[chatHistory.value.length - 1].text = aiSubtitle.value
    } else {
      chatHistory.value.push({ role: 'assistant', text: aiSubtitle.value })
    }
  },
  onError: (msg) => { errorMsg.value = msg },
})

// 同步 muted 状态
watch(voiceMuted, (v) => { isMuted.value = v })

// 声波柱映射：频率数据 → 像素高度
const visualBars = computed(() => {
  return frequencyData.value.map((v) => {
    // 最小 4px，最大 120px
    return Math.max(4, Math.min(120, v * 160))
  })
})

// 柱子颜色：中心亮，两侧暗
const barColors = [
  '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff',
  '#c7d2fe', '#a5b4fc', '#818cf8', '#6366f1',
]

// 可视化脉动动画（idle 状态）
let pulseRaf = 0
function startPulse() {
  const bars = frequencyData.value
  let t = 0
  function tick() {
    t += 0.03
    for (let i = 0; i < bars.length; i++) {
      bars[i] = 0.1 + 0.05 * Math.sin(t + i * 0.5)
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
    aiSubtitle.value = ''
    errorMsg.value = ''
    if (callState.value === 'idle') {
      startPulse()
    }
  } else {
    stopPulse()
    endCall()
    disconnectVisualizer()
  }
})

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
  endCall()
  disconnectVisualizer()
  emit('close')
}

onUnmounted(() => {
  stopPulse()
})
</script>

<style scoped>
.voice-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 40%, #0f172a 100%);
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
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.top-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
}

.top-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.top-btn.text-btn {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
}

.end-top-btn {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.end-top-btn:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.25);
}

.top-center {
  display: flex;
  justify-content: center;
}

/* 中央可视化区 */
.voice-visual-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.wave-container {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 140px;
}

.wave-bar {
  width: 4px;
  min-height: 4px;
  border-radius: 2px;
  transition: height 0.08s ease;
}

/* 状态文字 */
.voice-status {
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
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
  color: #f87171;
}

/* AI 字幕 */
.ai-subtitle {
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  font-size: 15px;
  padding: 0 20px 12px;
  max-height: 80px;
  overflow-y: auto;
  line-height: 1.5;
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
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.2s;
}

.control-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.control-btn.active {
  background: rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
}

.control-btn.muted {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
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
  color: rgba(255, 255, 255, 0.2);
  font-size: 11px;
  padding: 8px 0;
  flex-shrink: 0;
}

/* 过渡动画 */
.voice-overlay-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.voice-overlay-leave-active {
  transition: opacity 0.2s ease;
}

.voice-overlay-enter-from {
  opacity: 0;
  transform: scale(0.95);
}

.voice-overlay-leave-to {
  opacity: 0;
}

/* 液态玻璃对话框 */
.glass-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
}

.glass-panel {
  width: 90%;
  max-width: 480px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.glass-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.glass-close:hover {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.9);
}

.glass-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.glass-body::-webkit-scrollbar {
  width: 4px;
}

.glass-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

.glass-empty {
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
  padding: 40px 0;
}

.glass-msg {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.5;
  font-size: 13px;
  word-break: break-word;
}

.glass-msg.user {
  align-self: flex-end;
  background: rgba(99, 102, 241, 0.3);
  color: rgba(255, 255, 255, 0.9);
  border-bottom-right-radius: 4px;
}

.glass-msg.assistant {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
  border-bottom-left-radius: 4px;
}

.glass-msg-role {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 4px;
}

.glass-msg-text {
  white-space: pre-wrap;
}

/* 液态玻璃面板动画 */
.glass-panel-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.glass-panel-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.glass-panel-enter-from {
  opacity: 0;
  transform: scale(0.92);
}

.glass-panel-leave-to {
  opacity: 0;
  transform: scale(0.95);
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

  .glass-panel {
    width: 95%;
    max-height: 75vh;
  }
}
</style>
