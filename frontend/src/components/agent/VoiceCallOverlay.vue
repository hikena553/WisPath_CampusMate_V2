<template>
  <Teleport to="body">
    <Transition name="voice-overlay">
      <div v-if="visible" class="vc" :class="`st-${callState}`" @click.self="handleClose">
        <!-- 背景：极光渐变 + 网格 -->
        <div class="vc-bg" aria-hidden="true">
          <div class="vc-aurora a1" />
          <div class="vc-aurora a2" />
          <div class="vc-aurora a3" />
          <div class="vc-grid" />
        </div>

        <!-- 顶部：称谓 + 通话状态 + 关闭 -->
        <header class="vc-top">
          <div class="vc-brand">
            <span class="vc-live" :class="callState" />
            <div class="vc-brand-text">
              <strong>{{ agentName }}</strong>
              <small>语音通话</small>
            </div>
          </div>
          <button class="vc-icon-btn" title="结束通话" @click="handleClose">
            <el-icon :size="20"><CloseBold /></el-icon>
          </button>
        </header>

        <!-- 舞台：智能体形象 -->
        <main class="vc-stage">
          <VoiceMascot :state="charState" :level="smoothedLevel" :size="mascotSize" />
          <div class="vc-status" :class="{ pulse: callState === 'processing' }">{{ statusText }}</div>
          <div v-if="callState === 'speaking'" class="vc-hint">你可以随时开口打断我</div>
          <div v-else-if="callState === 'listening'" class="vc-hint">我正在听，说完停顿一下就好</div>
        </main>

        <!-- 通话字幕：仅展示智能体回答（无气泡/无头像/无时间戳），
             当前回答逐句淡入，上一条自动淡出 -->
        <section class="vc-say" aria-live="polite">
          <div v-if="visibleAnswers.length === 0" class="vc-say-empty">
            接通后 {{ agentName }} 会先向你问好
          </div>
          <template v-else>
            <p
              v-for="(ans, i) in visibleAnswers"
              :key="ans.id"
              :class="['vc-line', { prev: i < visibleAnswers.length - 1 }]"
            >
              <span v-for="(seg, si) in splitSentences(ans.text)" :key="si" class="vc-seg">{{ seg }}</span>
              <span v-if="!ans.text" class="vc-caret" />
            </p>
          </template>
        </section>

        <!-- 底部控制：静音 / 挂断 -->
        <footer class="vc-controls">
          <button
            :class="['ctrl-btn', 'mic', micBtnClass]"
            :disabled="callState === 'connecting'"
            :title="callState === 'idle' || callState === 'error' ? '接通通话' : (isMuted ? '取消静音' : '静音')"
            @click="handleMicClick"
          >
            <span class="mic-ring" />
            <span class="mic-core">
              <el-icon :size="26"><Microphone /></el-icon>
            </span>
            <span v-if="isMuted" class="btn-slash" />
          </button>
          <button class="ctrl-btn hangup" title="结束通话" @click="handleClose">
            <el-icon :size="24"><PhoneFilled /></el-icon>
          </button>
        </footer>

        <p class="vc-disclaimer">内容由 AI 生成 · 通话已开启表情关怀</p>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone, PhoneFilled, CloseBold } from '@element-plus/icons-vue'
import { getToken } from '@/utils/token'
import { useVoiceCall, type VoiceState } from '@/composables/useVoiceCall'
import { useEmotionDetection, type EmotionSnapshot } from '@/composables/useEmotionDetection'
import { batchRecordEmotion } from '@/api/emotion'
import { useResponsive } from '@/composables/useResponsive'
import VoiceMascot from './VoiceMascot.vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

// AI 助手称谓取自站点配置（管理端「自我称谓」）
const { agentName } = useSiteConfig()
const { isMobile } = useResponsive()

const props = defineProps<{
  visible: boolean
  conversationId?: number | null
}>()

const emit = defineEmits<{ close: [] }>()

const callState = ref<VoiceState>('idle')
const isMuted = ref(false)
const errorMsg = ref('')
const audioLevel = ref(0)

const mascotSize = computed(() => (isMobile.value ? 190 : 260))

// 回答记录：仅保留智能体侧文本（需求 1：不展示用户识别内容）
interface ChatEntry { id: string; role: 'assistant'; text: string }
const chatHistory = ref<ChatEntry[]>([])

// 字幕区只展示最近两条回答：上一条淡出、当前条为主字幕
const visibleAnswers = computed(() => chatHistory.value.slice(-2))

/** 按句切分，便于"逐句淡入"（替代逐字打字机，观感更接近通话字幕） */
function splitSentences(text: string): string[] {
  if (!text) return []
  return text.match(/[^。！？!?；;\n]+[。！？!?；;]?/g) ?? [text]
}

let lastConvId: number | null | undefined

// 打开时拉取该会话既有回答（仅 assistant 侧），保留历史轮次
async function loadHistory() {
  if (!activeConvId.value) return
  try {
    const token = getToken()
    const resp = await fetch(`/api/agent/conversations/${activeConvId.value}/messages`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) return
    const msgs: { id: number; role: string; content: string }[] = await resp.json()
    const entries = msgs
      .filter((m) => m.role === 'assistant' && m.content?.trim())
      .slice(-40)
      .map((m) => ({ id: `h-${m.id}`, role: 'assistant' as const, text: m.content }))
    if (entries.length) chatHistory.value = entries
    activeBubbleId = null
  } catch {
    // 静默失败，不阻断通话
  }
}

// 当前通话绑定的会话 ID：由 ChatPanel 在点击电话按钮时同步传入，
// 避免依赖 props 异步更新导致"首次连接丢失会话绑定"
const activeConvId = ref<number | null>(props.conversationId ?? null)
watch(() => props.conversationId, (v) => {
  if (callState.value === 'idle') activeConvId.value = v ?? null
})

const {
  isMuted: voiceMuted, startCall, endCall, toggleMute, send, unlockAudio, cancelPlayback,
} = useVoiceCall({
  get conversationId() { return activeConvId.value },
  onStateChange: (s) => {
    callState.value = s
    // 新一轮开始：解除"作废"标记，并为本轮准备全新的回答气泡（一轮一气泡）
    if (s === 'processing') {
      discardAI = false
      activeBubbleId = null
    }
  },
  onAudioLevel: (level) => { audioLevel.value = level },
  // 需求 1：不再展示用户识别文本，仅保留智能体回答
  onTranscript: () => {},
  onBargeIn: () => {
    // 豆包式打断（仅在"持续说话真正打断"时触发）：立即停播；
    // 未输出的回答作废，已输出的（用户已看到/听到的）保留
    discardAI = true
    cancelPlayback()
    const last = chatHistory.value[chatHistory.value.length - 1]
    if (last && !last.text.trim()) {
      chatHistory.value.pop()
      activeBubbleId = null
    }
  },
  onAIText: (text) => {
    // 直接落屏（不做逐字打字机）：文本随 LLM 流式产出即时呈现，降低感知延迟
    if (discardAI) return
    const id = ensureBubbleId()
    const entry = chatHistory.value.find((e) => e.id === id)
    if (entry) entry.text += text
  },
  onError: (msg) => { errorMsg.value = msg },
})

watch(voiceMuted, (v) => { isMuted.value = v })

// 平滑音量（0~1）：驱动口型与光环，避免抖动
const smoothedLevel = ref(0)
watch(audioLevel, (v) => {
  const target = Math.max(0, Math.min(1, v * 5.5))
  smoothedLevel.value = smoothedLevel.value * 0.68 + target * 0.32
})

// 形象状态映射（豆包式四态）
const charState = computed<'idle' | 'listening' | 'thinking' | 'speaking'>(() => {
  if (callState.value === 'processing') return 'thinking'
  if (callState.value === 'speaking') return 'speaking'
  if (callState.value === 'listening') return 'listening'
  return 'idle'
})

const statusText = computed(() => {
  // 接通后、问候前若仍在取表情，明确提示"正在感知你的状态"，让等待可被理解
  if (primingEmotion.value && (callState.value === 'connecting' || callState.value === 'listening')) {
    return '正在感知你的状态…'
  }
  switch (callState.value) {
    case 'idle': return '正在准备通话…'
    case 'connecting': return '正在接通…'
    case 'listening': return '正在聆听…'
    case 'processing': return '思考中…'
    case 'speaking': return `${agentName.value}正在回复…`
    case 'error': return errorMsg.value || '连接失败'
    default: return ''
  }
})

// 麦克风按钮状态类
const micBtnClass = computed(() => {
  if (isMuted.value) return 'muted'
  if (callState.value === 'listening') return 'recording'
  if (callState.value === 'processing' || callState.value === 'speaking') return 'busy'
  return ''
})

// ---- 回答气泡管理：一轮回答 = 一个气泡，避免多段内容串到同一个气泡 ----
let activeBubbleId: string | null = null
function ensureBubbleId(): string {
  if (!activeBubbleId) {
    activeBubbleId = `a-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    chatHistory.value.push({ id: activeBubbleId, role: 'assistant', text: '' })
  }
  return activeBubbleId
}

// ---- 表情识别（通话内静默运行；首帧表情由后端在接通时用于定制问候） ----
const emotionDetection = useEmotionDetection()
// 是否仍在"取首帧表情"（用于把等待显性化为"正在感知你的状态…"）
const primingEmotion = ref(false)
let discardAI = false
let lastEmotionSentAt = 0

function reportEmotion(snap: EmotionSnapshot) {
  const now = performance.now()
  if (now - lastEmotionSentAt < 800) return
  lastEmotionSentAt = now
  send({ type: 'emotion', emotion: snap.emotion, confidence: snap.confidence })
}

watch(() => emotionDetection.current.value, (snap) => {
  if (snap && callState.value !== 'idle' && callState.value !== 'error') reportEmotion(snap)
})

// 通话开始后自动开启表情监测（静默运行）；返回是否成功（失败要告知后端不必空等）
async function startEmotionAuto(): Promise<boolean> {
  try {
    return await emotionDetection.start((snap) => {
      if (callState.value !== 'idle' && callState.value !== 'error') reportEmotion(snap)
    })
  } catch {
    // 摄像头不可用时静默降级，不阻断通话
    return false
  }
}

/** 预热表情模型（点击电话按钮时调用，不开启摄像头）：让首帧表情更早拿到 */
function prewarmEmotion() {
  void emotionDetection.prewarm()
}

// ---- 打开/关闭面板
watch(() => props.visible, async (v) => {
  if (v) {
    errorMsg.value = ''
    if (activeConvId.value !== lastConvId) {
      chatHistory.value = []
      lastConvId = activeConvId.value
    }
    await loadHistory()
    // 兜底自动接通（豆包式：拨通即通话，无需人为开启语音）
    if (callState.value === 'idle') void beginCall()
  } else {
    cancelPlayback()
    await flushEmotionRecords()
    emotionDetection.stop()
    endCall()
  }
})

// 挂断/关闭时批量上报情绪（情绪树洞）
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

/**
 * 接通并让智能体先开口（豆包式：拨通即自动接通，无需人为开启语音）。
 * 由 ChatPanel 在点击电话按钮的用户手势内同步调用（解锁音频上下文），
 * 同时作为麦克风按钮的"重试"入口。
 */
async function beginCall(conversationId?: number | null) {
  if (callState.value !== 'idle' && callState.value !== 'error') return
  if (conversationId !== undefined) activeConvId.value = conversationId ?? null
  // 先启动表情识别：尽早弹出摄像头授权、尽早跑首帧（问候要结合表情，故必须先于/并行于连接）
  primingEmotion.value = true
  const emotionTask = startEmotionAuto()
  try {
    await startCall()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '接通失败，请点击麦克风重试')
  }
  const emotionOk = await emotionTask
  primingEmotion.value = false
  if (!emotionOk) {
    // 摄像头被拒 / 模型不可用：立即告知后端，直接中性问候，不必空等表情
    send({ type: 'emotion_unavailable' })
  }
}

function handleMicClick() {
  if (callState.value === 'idle' || callState.value === 'error') {
    void beginCall()
  } else {
    toggleMute()
  }
}

// 在用户手势内解锁音频上下文（由 ChatPanel 点击电话按钮时同步调用，保证语音能出声）
function primeAudio() {
  void unlockAudio()
}

defineExpose({ beginCall, primeAudio, prewarmEmotion })

function handleClose() {
  cancelPlayback()
  endCall()
  flushEmotionRecords()
  emotionDetection.stop()
  emit('close')
}

onUnmounted(() => {
  emotionDetection.stop()
})
</script>

<style scoped>
.vc {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  padding: 0 22px;
  padding-top: env(safe-area-inset-top, 18px);
  padding-bottom: env(safe-area-inset-bottom, 16px);
  color: #1f2d43;
  overflow: hidden;
}

/* 背景 */
.vc-bg { position: absolute; inset: 0; z-index: -1; background: linear-gradient(175deg, #eef5ff 0%, #e7f0fd 40%, #f3f0ff 100%); }
.vc-aurora {
  position: absolute;
  border-radius: 50%;
  filter: blur(48px);
  opacity: 0.55;
  animation: vc-drift 14s ease-in-out infinite;
}
.vc-aurora.a1 { width: 320px; height: 320px; left: -80px; top: -60px; background: radial-gradient(circle, rgba(64,158,255,.55), transparent 70%); }
.vc-aurora.a2 { width: 300px; height: 300px; right: -70px; top: 12%; background: radial-gradient(circle, rgba(143,107,255,.45), transparent 70%); animation-delay: 2.5s; }
.vc-aurora.a3 { width: 280px; height: 280px; left: 20%; bottom: -90px; background: radial-gradient(circle, rgba(103,194,58,.28), transparent 70%); animation-delay: 5s; }
@keyframes vc-drift {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(16px, -18px, 0) scale(1.08); }
}
.vc-grid {
  position: absolute; inset: 0; opacity: 0.35;
  background-image: radial-gradient(rgba(91,141,239,.16) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: radial-gradient(circle at 50% 34%, #000 0%, transparent 72%);
  -webkit-mask-image: radial-gradient(circle at 50% 34%, #000 0%, transparent 72%);
}

/* 顶部 */
.vc-top { display: flex; align-items: center; justify-content: space-between; padding: 10px 0 6px; flex-shrink: 0; }
.vc-brand { display: flex; align-items: center; gap: 10px; }
.vc-live { width: 9px; height: 9px; border-radius: 50%; background: #a8b6cf; box-shadow: 0 0 0 0 rgba(64,158,255,.5); transition: background .3s; }
.vc-live.listening { background: #409eff; animation: vc-pulse 1.4s ease-out infinite; }
.vc-live.processing { background: #8f6bff; animation: vc-pulse 1.6s ease-out infinite; }
.vc-live.speaking { background: #52c41a; animation: vc-pulse 1.2s ease-out infinite; }
.vc-live.error { background: #f56c6c; }
@keyframes vc-pulse {
  0% { box-shadow: 0 0 0 0 rgba(64,158,255,.45); }
  100% { box-shadow: 0 0 0 12px rgba(64,158,255,0); }
}
.vc-brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.vc-brand-text strong { font-size: 15px; font-weight: 700; letter-spacing: .5px; }
.vc-brand-text small { font-size: 11px; color: #8a97ad; }
.vc-icon-btn {
  width: 36px; height: 36px; border-radius: 50%; border: none;
  background: rgba(255,255,255,.7); color: #6b7891; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 10px rgba(64,110,190,.12); transition: all .2s;
}
.vc-icon-btn:hover { background: #fff; color: #f56c6c; }

/* 舞台 */
.vc-stage {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 6px;
}
.vc-status { font-size: 15px; font-weight: 600; color: #4a6ea8; letter-spacing: .4px; }
.vc-status.pulse { animation: vc-textpulse 1.6s ease-in-out infinite; }
@keyframes vc-textpulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }
.vc-hint { font-size: 12px; color: #96a4bc; }

/* 通话字幕：无气泡、无头像；当前回答为主字幕，上一条淡出 */
.vc-say {
  flex-shrink: 0; min-height: 26vh;
  display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
  gap: 10px; padding: 0 6px 6px;
  mask-image: linear-gradient(180deg, transparent 0, #000 26%, #000 100%);
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 26%, #000 100%);
}
.vc-say-empty { color: #97a6bd; font-size: 13px; padding: 24px 0; }
.vc-line {
  margin: 0; text-align: center; max-width: 680px;
  transition: opacity .5s ease, transform .5s ease, font-size .3s ease;
  word-break: break-word;
}
.vc-line.prev {
  font-size: 14px; line-height: 1.6; color: rgba(74, 96, 134, .52);
  transform: scale(.97);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.vc-line:not(.prev) {
  font-size: 21px; line-height: 1.6; font-weight: 600; color: #16233b;
  letter-spacing: .2px;
}
/* 逐句淡入：只用透明度/位移，不用 blur —— blur 会让文字看起来发糊（易被当成"乱码"） */
.vc-seg { animation: vc-seg-in .38s ease both; }
@keyframes vc-seg-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.vc-caret {
  display: inline-block; width: 9px; height: 18px; margin-left: 4px; vertical-align: -3px;
  border-radius: 2px; background: linear-gradient(180deg, #409eff, #8f6bff);
  animation: vc-caret 1s steps(2, end) infinite;
}
@keyframes vc-caret { 0%, 50% { opacity: 1; } 50.01%, 100% { opacity: .15; } }

/* 控制栏 */
.vc-controls { flex-shrink: 0; display: flex; align-items: center; justify-content: center; gap: 40px; padding: 14px 0 6px; }
.ctrl-btn {
  position: relative; border: none; cursor: pointer; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; transition: all .25s;
}
.ctrl-btn:disabled { opacity: .4; cursor: not-allowed; }
.mic {
  width: 70px; height: 70px; background: rgba(255,255,255,.92); color: #4a7fe0;
  box-shadow: 0 6px 20px rgba(64,110,190,.2);
}
.mic:hover:not(:disabled) { transform: scale(1.05); background: #fff; }
.mic-core { position: relative; z-index: 1; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
.mic-ring {
  position: absolute; inset: -5px; border-radius: 50%;
  background: conic-gradient(from 0deg, #409eff, #8f6bff, #ff7eb3, #f7b733, #409eff);
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px));
  mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px));
  opacity: .4; pointer-events: none; animation: mic-rotate 4s linear infinite;
}
@keyframes mic-rotate { to { transform: rotate(360deg); } }
.mic.recording { background: linear-gradient(135deg, #409eff, #6fb7ff); color: #fff; }
.mic.recording .mic-ring { opacity: 1; animation: mic-rotate 2.4s linear infinite, mic-breathe 1.5s ease-in-out infinite; }
@keyframes mic-breathe {
  0%,100% { box-shadow: 0 0 0 4px rgba(64,158,255,.18), 0 0 22px rgba(64,158,255,.45); }
  50% { box-shadow: 0 0 0 9px rgba(64,158,255,.1), 0 0 36px rgba(64,158,255,.72); }
}
.mic.busy { background: linear-gradient(135deg, #8f6bff, #409eff); color: #fff; animation: mic-soft 2s ease-in-out infinite; }
@keyframes mic-soft {
  0%,100% { box-shadow: 0 6px 20px rgba(91,141,239,.35); }
  50% { box-shadow: 0 6px 28px rgba(143,107,255,.62); }
}
.mic.muted { background: rgba(255,255,255,.85); color: #f56c6c; }
.mic.muted .mic-ring { opacity: .25; animation: none; }
.btn-slash { position: absolute; width: 2.5px; height: 32px; background: #ef4444; transform: rotate(45deg); border-radius: 2px; z-index: 2; }
.hangup {
  width: 60px; height: 60px; color: #fff;
  background: linear-gradient(135deg, #ff6b6b, #e93c3c);
  box-shadow: 0 6px 18px rgba(233,60,60,.36);
}
.hangup:hover { transform: scale(1.06); box-shadow: 0 8px 24px rgba(233,60,60,.5); }

.vc-disclaimer { flex-shrink: 0; text-align: center; font-size: 11px; color: #9aa8bf; padding: 4px 0 2px; margin: 0; }

/* 整体过渡 */
.voice-overlay-enter-active { transition: none; }
.voice-overlay-leave-active { transition: opacity .2s ease; }
.voice-overlay-leave-to { opacity: 0; }

@media (max-width: 767px) {
  .vc { padding: 0 16px; }
  .vc-say { min-height: 22vh; }
  .vc-line:not(.prev) { font-size: 18px; }
  .vc-controls { gap: 30px; }
  .mic { width: 62px; height: 62px; }
  .hangup { width: 54px; height: 54px; }
}
</style>