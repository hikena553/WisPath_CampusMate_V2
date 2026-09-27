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
  let nextPlayTime = 0
  // 已调度的播放源集合：打断时立即停止所有待播/播放中的音频
  const activeSources = new Set<AudioBufferSourceNode>()

  const VAD_ENERGY_THRESHOLD = 0.02
  const VOICE_START_MS = 40   // 连续发音超过该时长视为开始说话（防单帧毛刺）
  const VOICE_STOP_MS = 400   // 静音持续该时长视为说话结束（说完尽快识别）
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
    let url = `${protocol}//${host}/api/voice/ws?token=${encodeURIComponent(token || '')}`
    if (options.conversationId) {
      url += `&conversation_id=${options.conversationId}`
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
        } catch {
          // ignore parse errors
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
          // 重置音频播放时间，避免与下一次TTS重叠
          if (playbackAudioCtx) {
            nextPlayTime = playbackAudioCtx.currentTime
          }
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

  async function playAudioChunk(buffer: ArrayBuffer) {
    if (!playbackAudioCtx) {
      playbackAudioCtx = new AudioContext({ sampleRate: 16000 })
      nextPlayTime = playbackAudioCtx.currentTime
    }

    // PCM 16bit mono → AudioBuffer
    const samples = new Int16Array(buffer)
    const float32 = new Float32Array(samples.length)
    for (let i = 0; i < samples.length; i++) {
      float32[i] = samples[i] / 32768
    }

    const audioBuffer = playbackAudioCtx.createBuffer(1, float32.length, 16000)
    audioBuffer.getChannelData(0).set(float32)

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
    source.start(startTime)

    // 更新下一块的开始时间
    nextPlayTime = startTime + audioBuffer.duration
  }

  // 打断（barge-in）：立即停止所有排队/播放中的 AI 语音
  function cancelPlayback() {
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

        if (data.audio && ws?.readyState === WebSocket.OPEN && !isMuted.value) {
          // 发送音频数据到服务端（节流合并，避免高频消息挤占 WebSocket）
          const int16 = new Int16Array(data.audio.length)
          for (let i = 0; i < data.audio.length; i++) {
            int16[i] = Math.max(-32768, Math.min(32767, data.audio[i] * 32768))
          }
          pushAudioSamples(int16)
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

        // 发送音频（节流合并）
        if (ws?.readyState === WebSocket.OPEN && !isMuted.value) {
          const int16 = new Int16Array(samples.length)
          for (let i = 0; i < samples.length; i++) {
            int16[i] = Math.max(-32768, Math.min(32767, samples[i] * 32768))
          }
          pushAudioSamples(int16)
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
      return
    }

    const now = performance.now()
    if (energy > VAD_ENERGY_THRESHOLD) {
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
        // 用户开口说话：立即打断 AI（停止播放 + 通知服务端终止生成）
        if (state.value === 'speaking' || state.value === 'processing') {
          cancelPlayback()
          setState('listening')
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'interrupt' }))
          }
        }
        options.onSpeechStart?.()
      }
      lastSpeechActivityAt = now
    } else if (isSpeaking) {
      // 静音持续达到阈值：判定说话结束，通知服务端开始识别
      if (now - lastSpeechActivityAt >= VOICE_STOP_MS) {
        isSpeaking = false
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

  async function startCall() {
    if (state.value !== 'idle' && state.value !== 'error') return

    setState('connecting')
    error.value = ''

    try {
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
  }

  onUnmounted(() => {
    cleanup()
  })

  return {
    state,
    isMuted,
    error,
    startCall,
    endCall,
    toggleMute,
    send,
    cancelPlayback,
  }
}
