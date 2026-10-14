import { ref, onUnmounted } from 'vue'
import { getToken } from '@/utils/token'

export type VoiceState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking' | 'error'

export interface UseVoiceCallOptions {
  conversationId?: number | null
  onStateChange?: (state: VoiceState) => void
  onAudioLevel?: (level: number) => void
  onAIText?: (text: string) => void
  onTranscript?: (text: string, final: boolean) => void
  onSpeechStart?: () => void
  /** 真正发生打断（用户持续说话打断了 AI）时触发，用于丢弃未输出的回答 */
  onBargeIn?: () => void
  onError?: (message: string) => void
}

/**
 * 语音通话核心组合式函数
 * 管理 WebSocket 连接、VAD、音频编解码
 */
export function useVoiceCall(options: UseVoiceCallOptions = {}) {
  const state = ref<VoiceState>('idle')
  const isMuted = ref(false)
  const error = ref('')

  let ws: WebSocket | null = null
  let audioCtx: AudioContext | null = null
  let mediaStream: MediaStream | null = null
  let workletNode: AudioWorkletNode | null = null
  let scriptProcessor: ScriptProcessorNode | null = null
  let sourceNode: MediaStreamAudioSourceNode | null = null
  let playbackAudioCtx: AudioContext | null = null
  let pingInterval: ReturnType<typeof setInterval> | null = null
  let reconnectAttempts = 0
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  // VAD 状态（时间制：与帧长无关，worklet / ScriptProcessor 两条路径行为一致）
  let speechStartCandidateAt = 0 // 连续发音候选起点（毫秒时间戳）
  let lastSpeechActivityAt = 0   // 最近一次发音活动时刻
  let isSpeaking = false
  let speechOnsetAt = 0          // 本轮开口起点（用于二段式打断判定）
  let bargedIn = false           // 本轮是否已触发过打断
  let nextPlayTime = 0
  // 播放串行队列：所有音频块按到达顺序排队处理，避免并发执行时
  // await resume() 交错，导致多个块调度到同一时刻造成重叠/乱序
  let playbackQueue: Promise<void> = Promise.resolve()
  // 播放代际：每次打断自增。后端在收到 interrupt 前已发出的"在途"ai_audio 块
  // 到达前端时若代际已变，则整体丢弃，杜绝旧语音与新一轮回答重叠
  let playbackGeneration = 0
  // 已调度的播放源集合：打断时立即停止所有待播/播放中的音频
  const activeSources = new Set<AudioBufferSourceNode>()
  // 预滚样本与"因 AI 正在播报而暂存"标记
  let prerollSamples: number[] = []
  let prerollArmed = false
  // 采集上下午的实际采样率（浏览器可能忽略请求的 16000，Windows 上多为 48000）
  let captureSampleRate = 16000

  const VAD_ENERGY_THRESHOLD = 0.02
  // 时间制 VAD：调低开口/收口时延，缩短"开口 -> 打断"与"说完 -> 识别"的响应时间，
  // 直接压缩端到端延迟（豆包等实时方案的共同取向）
  const VOICE_START_MS = 30   // 连续发音超过该时长视为开始说话（防单帧毛刺）
  const VOICE_STOP_MS = 420   // 静音持续该时长视为说话结束（说完尽快识别）
  // 二段式打断：开口判定很快（30ms），但"打断 AI"要求持续说话达到该时长，
  // 避免环境噪声/单帧毛刺误触发，把接通问候或正在播报的回答打断掉
  const BARGE_IN_MS = 150
  // AI 播报期间更强地抑制"回声自激打断"：抬高开口阈值 + 要求更长持续说话，
  // 否则扬声器回声会误触发打断，表现为"播报一段就被掐断"
  const BARGE_IN_MS_AI_SPEAKING = 350
  const AI_SPEAKING_VAD_FACTOR = 3
  // 预滚缓冲：AI 播报期间不上传麦克风音频（防回声污染识别），只留最近 300ms，
  // 待开始说话/打断时补发，避免吃掉第一个字
  const PREROLL_SAMPLES = 4800  // 300ms @16kHz
  const MAX_RECONNECT = 3
  const PING_INTERVAL = 15000
  // 音频上传节流：合并小块音频再发送，避免高频消息挤占 WebSocket，
  // 延迟回答文字/语音的回传（豆包等实时方案的共同做法：音频通道限流保活）
  const AUDIO_FLUSH_INTERVAL_MS = 60    // 至多每 60ms 发一包
  const AUDIO_FLUSH_MAX_SAMPLES = 1536  // 每包最多约 96ms 音频
  let pendingAudio: number[] = []
  let lastAudioFlushAt = 0

  function setState(s: VoiceState) {
    state.value = s
    options.onStateChange?.(s)
  }

  function getWsUrl(): string {
    const token = getToken()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // F3：内存 token 存在时显式传入；刷新后为空则后端从 httpOnly Cookie 兜底认证
    let url = `${protocol}//${host}/api/voice/ws`
    if (token) url += `?token=${encodeURIComponent(token)}`
    if (options.conversationId) {
      url += `${url.includes('?') ? '&' : '?'}conversation_id=${options.conversationId}`
    }
    return url
  }

  function connectWs(): Promise<void> {
    return new Promise((resolve, reject) => {
      ws = new WebSocket(getWsUrl())

      ws.onopen = () => {
        reconnectAttempts = 0
        resolve()
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          handleServerMessage(msg)
        } catch (e) {
          if (import.meta.env.DEV) console.warn('[voice] 消息解析失败', e, event.data)
        }
      }

      ws.onclose = (event) => {
        if (event.code === 4001 || event.code === 4004) {
          error.value = event.reason || '认证失败'
          setState('error')
          return
        }

        if (state.value !== 'idle' && state.value !== 'error') {
          // 尝试重连
          if (reconnectAttempts < MAX_RECONNECT) {
            reconnectAttempts++
            const delay = Math.pow(2, reconnectAttempts) * 1000
            reconnectTimeout = setTimeout(() => {
              if (state.value !== 'idle') {
                connectWs().catch(() => {
                  setState('error')
                  error.value = '重连失败'
                })
              }
            }, delay)
          } else {
            setState('error')
            error.value = '连接断开'
          }
        }
      }

      ws.onerror = () => {
        reject(new Error('WebSocket 连接失败'))
      }
    })
  }

  function handleServerMessage(msg: Record<string, unknown>) {
    // 开发期诊断：打印收到的信令（音频只打长度），便于定位"播报中断/文字异常"
    if (import.meta.env.DEV) {
      if (msg.type === 'ai_audio') {
        console.debug('[voice] <- ai_audio b64_len=', (msg.data as string)?.length ?? 0)
      } else {
        console.debug('[voice] <-', msg)
      }
    }
    switch (msg.type) {
      case 'transcript':
        if (msg.text) {
          options.onTranscript?.(msg.text as string, msg.final as boolean)
        }
        break

      case 'ai_text':
        if (msg.text) {
          options.onAIText?.(msg.text as string)
        }
        break

      case 'ai_audio':
        if (msg.data) {
          playAudioChunk(base64ToArrayBuffer(msg.data as string))
        }
        break

      case 'state':
        if (msg.state === 'listening') {
          setState('listening')
          // 注意：此处【不能】作废播放队列。listening 表示"服务端生成完毕"，
          // 此刻前端播放队列往往还没播完（后端出音快于实时播放），一旦 cancel
          // 就会把刚收到的语音整段掐断 —— 症状正是"有文字没声音/语音截断"。
          // 真正需要停播的场景只有"用户打断"，统一由 barge-in 路径处理。
        } else if (msg.state === 'processing') {
          setState('processing')
        } else if (msg.state === 'speaking') {
          setState('speaking')
        }
        break

      case 'error':
        error.value = (msg.message as string) || '未知错误'
        options.onError?.(error.value)
        break

      case 'pong':
        // heartbeat response
        break
    }
  }

  function base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    return bytes.buffer
  }

  function playAudioChunk(buffer: ArrayBuffer) {
    // 串行化：所有音频块按到达顺序排队处理。playAudioChunkInner 内含
    // await resume()，若并发执行，多个块可能在 resume 挂起时读到同一个
    // nextPlayTime，调度到同一时刻造成重叠/乱音（弱网下更易触发）
    const gen = playbackGeneration
    const p = playbackQueue.then(() => playAudioChunkInner(buffer, gen))
    // 队列不因单块失败而中断；错误已在内部兜底
    playbackQueue = p.then(
      () => undefined,
      () => undefined,
    )
    return p
  }

  async function playAudioChunkInner(buffer: ArrayBuffer, gen: number) {
    if (!playbackAudioCtx) {
      playbackAudioCtx = new AudioContext({ sampleRate: 16000 })
      nextPlayTime = playbackAudioCtx.currentTime
    }

    // 浏览器自动播放策略会把 AudioContext 挂起（suspended），此时音频调度静默失效
    // （症状：文字/状态正常但无声）。每次播放前兜底恢复；恢复失败时短暂重试，
    // 避免"恢复失败→丢弃音频块→后续持续无声"（表现为播了一段就没声音）
    if (playbackAudioCtx.state === 'suspended') {
      let resumed = false
      for (let i = 0; i < 3; i++) {
        try {
          await playbackAudioCtx.resume()
          // 注意：TS 会把 state 收窄为 'suspended'，这里显式取字符串比较
          if ((playbackAudioCtx.state as string) === 'running') {
            resumed = true
            break
          }
        } catch {
          // 继续重试
        }
        await new Promise((r) => setTimeout(r, 60))
      }
      if (!resumed) {
        console.warn('[voice] 播放上下文仍挂起，本块音频跳过 state=', playbackAudioCtx.state)
        return
      }
    }

    // PCM 16bit mono → AudioBuffer
    const samples = new Int16Array(buffer)
    const float32 = new Float32Array(samples.length)
    for (let i = 0; i < samples.length; i++) {
      float32[i] = samples[i] / 32768
    }

    const audioBuffer = playbackAudioCtx.createBuffer(1, float32.length, 16000)
    audioBuffer.getChannelData(0).set(float32)

    // 解包期间发生了打断：丢弃本块，避免旧语音继续播报
    if (gen !== playbackGeneration) return

    // 使用调度播放，确保音频块按顺序播放，不会重叠
    const source = playbackAudioCtx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(playbackAudioCtx.destination)

    // 登记播放源，供打断时立即停止
    activeSources.add(source)
    source.onended = () => {
      activeSources.delete(source)
    }

    // 计算播放时间：确保在上一个块结束后开始
    const startTime = Math.max(nextPlayTime, playbackAudioCtx.currentTime)
    try {
      source.start(startTime)
    } catch (e) {
      // 调度失败（如 ctx 刚被清理）：移除登记，避免影响后续块
      activeSources.delete(source)
      console.warn('语音播放调度失败:', e)
      return
    }

    // 更新下一块的开始时间
    nextPlayTime = startTime + audioBuffer.duration
  }

  // 打断（barge-in）：立即停止所有排队/播放中的 AI 语音，
  // 并提升播放代际，使后端已发出但尚未到达的"在途"音频块作废
  function cancelPlayback() {
    playbackGeneration++
    activeSources.forEach((s) => {
      try {
        s.stop()
      } catch {
        // 已停止的源忽略
      }
    })
    activeSources.clear()
    nextPlayTime = playbackAudioCtx ? playbackAudioCtx.currentTime : 0
  }

  async function startCapture() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
    } catch {
      throw new Error('麦克风权限被拒')
    }

    audioCtx = new AudioContext({ sampleRate: 16000 })
    // 记录实际采样率：请求值可能被浏览器忽略（Windows 上多为 48000），
    // 后续按实际值重采样，否则音频变速变调 → ASR 乱码
    captureSampleRate = audioCtx.sampleRate || 16000
    if (import.meta.env.DEV) {
      console.debug('[voice] 采集采样率 =', captureSampleRate, '(请求 16000)')
    }
    sourceNode = audioCtx.createMediaStreamSource(mediaStream)

    // 尝试使用 AudioWorklet，降级到 ScriptProcessor
    try {
      const workletCode = `
        class VADProcessor extends AudioWorkletProcessor {
          constructor() {
            super()
            this._threshold = ${VAD_ENERGY_THRESHOLD}
          }

          process(inputs) {
            const input = inputs[0]
            if (!input || !input[0]) return true

            const samples = input[0]
            let energy = 0
            for (let i = 0; i < samples.length; i++) {
              energy += samples[i] * samples[i]
            }
            energy = Math.sqrt(energy / samples.length)

            this.port.postMessage({ energy })

            // 转发音频数据
            const copy = new Float32Array(samples)
            this.port.postMessage({ audio: copy }, [copy.buffer])

            return true
          }
        }
        registerProcessor('vad-processor', VADProcessor)
      `
      const blob = new Blob([workletCode], { type: 'application/javascript' })
      const url = URL.createObjectURL(blob)
      await audioCtx.audioWorklet.addModule(url)
      URL.revokeObjectURL(url)

      workletNode = new AudioWorkletNode(audioCtx, 'vad-processor')
      sourceNode.connect(workletNode)

      workletNode.port.onmessage = (event) => {
        const data = event.data

        if (data.energy !== undefined) {
          processVAD(data.energy)
        }

        if (data.audio && ws?.readyState === WebSocket.OPEN) {
          // 按"采集上下文实际采样率"重采样到 16k 后统一处理（节流合并 + 回声抑制）
          handleCapturedAudio(toInt16At16k(data.audio as Float32Array, captureSampleRate))
        }
      }
    } catch {
      // 降级到 ScriptProcessor
      scriptProcessor = audioCtx.createScriptProcessor(4096, 1, 1)
      sourceNode.connect(scriptProcessor)
      scriptProcessor.connect(audioCtx.destination)

      scriptProcessor.onaudioprocess = (event) => {
        const samples = event.inputBuffer.getChannelData(0)

        // 计算能量
        let energy = 0
        for (let i = 0; i < samples.length; i++) {
          energy += samples[i] * samples[i]
        }
        energy = Math.sqrt(energy / samples.length)
        processVAD(energy)

        // 发送音频（重采样到 16k + 节流合并 + 回声抑制，统一走 handleCapturedAudio）
        if (ws?.readyState === WebSocket.OPEN) {
          handleCapturedAudio(toInt16At16k(samples, captureSampleRate))
        }
      }
    }

    // 返回音频源供可视化使用
    return sourceNode
  }

  function processVAD(energy: number) {
    // 驱动音量回调
    options.onAudioLevel?.(energy)

    // 麦克风静音时冻结语音活动检测：不打断 AI、不触发说话/结束事件，
    // 保证取消静音后从干净状态重新开始识别
    if (isMuted.value) {
      isSpeaking = false
      speechStartCandidateAt = 0
      lastSpeechActivityAt = 0
      speechOnsetAt = 0
      bargedIn = false
      return
    }

    const now = performance.now()
    // AI 播报期间（activeSources 非空）抬高开口判定阈值：
    // 扬声器声音被麦克风拾取时能量通常较低，抬高阈值可避免 AI 自我打断造成卡壳；
    // 用户正常说话音量远高于该阈值，打断依然灵敏
    const threshold =
      aiSpeaking()
        ? VAD_ENERGY_THRESHOLD * AI_SPEAKING_VAD_FACTOR
        : VAD_ENERGY_THRESHOLD
    if (energy > threshold) {
      if (!isSpeaking) {
        // 连续发音达到阈值才判定开口，避免环境噪声毛刺
        if (speechStartCandidateAt === 0) {
          speechStartCandidateAt = now
        }
        if (now - speechStartCandidateAt < VOICE_START_MS) {
          return
        }
        speechStartCandidateAt = 0
        isSpeaking = true
        speechOnsetAt = now
        bargedIn = false
        options.onSpeechStart?.()
      }
      lastSpeechActivityAt = now

      // 二段式打断（barge-in）：用户持续说话达到 BARGE_IN_MS 才打断 AI，
      // 且仅当确有 AI 输出在播/在生成时才打断，避免"接通瞬间的环境噪声"
      // 把刚触发的问候语整轮掐掉
      // AI 播报期间要求更长的持续说话，避免扬声器回声误触发打断（表现为播报被掐断）
      const bargeInNeedMs = activeSources.size > 0 ? BARGE_IN_MS_AI_SPEAKING : BARGE_IN_MS
      if (!bargedIn && speechOnsetAt > 0 && now - speechOnsetAt >= bargeInNeedMs) {
        const hasActiveAI = aiSpeaking() || state.value === 'processing'
        if (hasActiveAI) {
          bargedIn = true
          cancelPlayback()
          setState('listening')
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'interrupt' }))
          }
          options.onBargeIn?.()
        }
      }
    } else if (isSpeaking) {
      // 静音持续达到阈值：判定说话结束，通知服务端开始识别
      if (now - lastSpeechActivityAt >= VOICE_STOP_MS) {
        isSpeaking = false
        speechOnsetAt = 0
        bargedIn = false
        // 先把节流缓冲中的尾包音频发出，确保服务端收到的音频完整（识别更准）
        flushPendingAudio()
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'end_of_speech' }))
        }
      }
    }
  }

  function arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }

  // ---- 音频上传节流：采集线程先汇入缓冲，按时间/长度阈值批量发送 ----
  /** 线性插值重采样为 16kHz 的 Int16 PCM。
   *  浏览器常忽略我们请求的 16000（Windows 上实际多为 48000），若不按实际
   *  采样率重采样，音频会"变速变调"送进 ASR，识别结果就是乱码（如"滴滴答答"）。 */
  function toInt16At16k(input: Float32Array, srcRate: number): Int16Array {
    const clamp = (v: number) => Math.max(-32768, Math.min(32767, Math.round(v * 32767)))
    if (!srcRate || srcRate === 16000) {
      const out = new Int16Array(input.length)
      for (let i = 0; i < input.length; i++) out[i] = clamp(input[i])
      return out
    }
    const ratio = srcRate / 16000
    const outLen = Math.max(1, Math.floor(input.length / ratio))
    const out = new Int16Array(outLen)
    for (let i = 0; i < outLen; i++) {
      const pos = i * ratio
      const i0 = Math.floor(pos)
      const i1 = Math.min(i0 + 1, input.length - 1)
      const frac = pos - i0
      out[i] = clamp(input[i0] * (1 - frac) + input[i1] * frac)
    }
    return out
  }

  /** AI 是否正在发声（有排队/播放中的音频块，或服务端已进入播报态） */
  function aiSpeaking(): boolean {
    return activeSources.size > 0 || state.value === 'speaking'
  }

  /** 采集音频统一入口。
   *  AI 播报期间麦克风会拾取扬声器回声，若一并上传会污染识别缓冲
   *  （实测会识别成"滴滴答答对对答的"这类乱码），因此只留预滚、不上传。 */
  function handleCapturedAudio(int16: Int16Array) {
    if (isMuted.value) return

    if (aiSpeaking()) {
      for (let i = 0; i < int16.length; i++) prerollSamples.push(int16[i])
      if (prerollSamples.length > PREROLL_SAMPLES) {
        prerollSamples.splice(0, prerollSamples.length - PREROLL_SAMPLES)
      }
      prerollArmed = true
      return
    }

    if (prerollArmed) {
      // 刚从"AI 播报"切回：先补上预滚，保证用户开口的第一个字不被吃掉
      if (prerollSamples.length) pushAudioSamples(new Int16Array(prerollSamples))
      prerollSamples = []
      prerollArmed = false
    }
    pushAudioSamples(int16)
  }

  function pushAudioSamples(int16: Int16Array) {
    for (let i = 0; i < int16.length; i++) {
      pendingAudio.push(int16[i])
    }
    const now = performance.now()
    if (
      now - lastAudioFlushAt >= AUDIO_FLUSH_INTERVAL_MS ||
      pendingAudio.length >= AUDIO_FLUSH_MAX_SAMPLES
    ) {
      lastAudioFlushAt = now
      flushPendingAudio()
    }
  }

  function flushPendingAudio() {
    if (!pendingAudio.length) return
    const samples = new Int16Array(pendingAudio)
    pendingAudio = []
    if (ws?.readyState === WebSocket.OPEN && !isMuted.value) {
      ws.send(JSON.stringify({ type: 'audio', data: arrayBufferToBase64(samples.buffer) }))
    }
  }

  function startPing() {
    pingInterval = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, PING_INTERVAL)
  }

  function stopPing() {
    if (pingInterval) {
      clearInterval(pingInterval)
      pingInterval = null
    }
  }

  /**
   * 解锁播放用 AudioContext（须在用户手势内调用）。
   * 浏览器自动播放策略只信任手势中创建/恢复的上下文，提前解锁可避免
   * 首个 ai_audio 到达时（异步回调，已不在手势栈中）被挂起 → "有文字没声音"。
   */
  async function unlockAudio(): Promise<void> {
    if (!playbackAudioCtx) {
      playbackAudioCtx = new AudioContext({ sampleRate: 16000 })
      nextPlayTime = playbackAudioCtx.currentTime
    }
    if (playbackAudioCtx.state === 'suspended') {
      try {
        await playbackAudioCtx.resume()
      } catch {
        // 恢复失败忽略：每次播放前仍会兜底重试
      }
    }
  }

  async function startCall() {
    if (state.value !== 'idle' && state.value !== 'error') return

    setState('connecting')
    error.value = ''

    try {
      // 用户手势窗口内预热播放上下文（自动播放策略只信任手势中创建/恢复的
      // AudioContext），避免首个 ai_audio 到达时被挂起导致播报无声
      await unlockAudio()

      await connectWs()
      const source = await startCapture()
      startPing()
      setState('listening')

      // 返回音频源供外部连接可视化器
      return source
    } catch (e) {
      setState('error')
      error.value = e instanceof Error ? e.message : '启动失败'
      cleanup()
      throw e
    }
  }

  function endCall() {
    setState('idle')
    cleanup()
  }

  function toggleMute() {
    isMuted.value = !isMuted.value
    // 切换静音时彻底重置 VAD 状态：关闭后不残留中间态，重新打开立即可用
    isSpeaking = false
    speechStartCandidateAt = 0
    lastSpeechActivityAt = 0
    speechOnsetAt = 0
    bargedIn = false
    // 丢弃节流缓冲中未发送的音频：静音期间的残留不混入取消静音后的第一段识别
    pendingAudio = []
    lastAudioFlushAt = 0
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'mute', muted: isMuted.value }))
    }
  }

  // 发送自定义 JSON 消息（如视觉情绪上报）
  function send(data: Record<string, unknown>): boolean {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
      return true
    }
    return false
  }

  function cleanup() {
    stopPing()

    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }

    if (workletNode) {
      workletNode.disconnect()
      workletNode = null
    }

    if (scriptProcessor) {
      scriptProcessor.disconnect()
      scriptProcessor = null
    }

    if (sourceNode) {
      sourceNode.disconnect()
      sourceNode = null
    }

    if (audioCtx) {
      audioCtx.close().catch(() => {})
      audioCtx = null
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop())
      mediaStream = null
    }

    if (playbackAudioCtx) {
      playbackAudioCtx.close().catch(() => {})
      playbackAudioCtx = null
    }
    activeSources.clear()
    // 通话结束：提升代际，作废任何仍在途/残留的音频块
    playbackGeneration++
    // 清空未发送的音频缓冲与定时器残留
    pendingAudio = []
    lastAudioFlushAt = 0

    if (ws) {
      ws.close()
      ws = null
    }

    reconnectAttempts = 0
    isSpeaking = false
    speechStartCandidateAt = 0
    lastSpeechActivityAt = 0
    speechOnsetAt = 0
    bargedIn = false
  }

  onUnmounted(() => {
    cleanup()
  })

  // 触发接通问候：智能体先开口（豆包式）。可选携带首次表情，用于定制开场语
  function requestGreeting(emotion?: string | null, confidence?: number): boolean {
    const payload: Record<string, unknown> = { type: 'start_call' }
    if (emotion) {
      payload.emotion = emotion
      payload.confidence = confidence ?? 0
    }
    return send(payload)
  }

  return {
    state,
    isMuted,
    error,
    startCall,
    endCall,
    toggleMute,
    send,
    requestGreeting,
    unlockAudio,
    cancelPlayback,
  }
}
