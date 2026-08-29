import { ref, onUnmounted } from 'vue'
import { getToken } from '@/utils/token'

export type VoiceState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking' | 'error'

export interface UseVoiceCallOptions {
  conversationId?: number | null
  onStateChange?: (state: VoiceState) => void
  onAudioLevel?: (level: number) => void
  onAIText?: (text: string) => void
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
  let silenceFrames = 0
  let speechFrames = 0
  let isSpeaking = false

  const VAD_ENERGY_THRESHOLD = 0.02
  const VAD_SPEECH_FRAMES = 3
  const VAD_SILENCE_FRAMES = 20
  const MAX_RECONNECT = 3
  const PING_INTERVAL = 15000

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
        // 用户语音识别结果（可用于字幕显示）
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
    }

    // PCM 16bit mono → AudioBuffer
    const samples = new Int16Array(buffer)
    const float32 = new Float32Array(samples.length)
    for (let i = 0; i < samples.length; i++) {
      float32[i] = samples[i] / 32768
    }

    const audioBuffer = playbackAudioCtx.createBuffer(1, float32.length, 16000)
    audioBuffer.getChannelData(0).set(float32)

    const source = playbackAudioCtx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(playbackAudioCtx.destination)
    source.start()
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
          // 发送音频数据到服务端
          const int16 = new Int16Array(data.audio.length)
          for (let i = 0; i < data.audio.length; i++) {
            int16[i] = Math.max(-32768, Math.min(32767, data.audio[i] * 32768))
          }
          const base64 = arrayBufferToBase64(int16.buffer)
          ws.send(JSON.stringify({ type: 'audio', data: base64 }))
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

        // 发送音频
        if (ws?.readyState === WebSocket.OPEN && !isMuted.value) {
          const int16 = new Int16Array(samples.length)
          for (let i = 0; i < samples.length; i++) {
            int16[i] = Math.max(-32768, Math.min(32767, samples[i] * 32768))
          }
          const base64 = arrayBufferToBase64(int16.buffer)
          ws.send(JSON.stringify({ type: 'audio', data: base64 }))
        }
      }
    }

    // 返回音频源供可视化使用
    return sourceNode
  }

  function processVAD(energy: number) {
    // 驱动音量回调
    options.onAudioLevel?.(energy)

    if (energy > VAD_ENERGY_THRESHOLD) {
      speechFrames++
      silenceFrames = 0
      if (speechFrames >= VAD_SPEECH_FRAMES && !isSpeaking) {
        isSpeaking = true
      }
    } else {
      silenceFrames++
      speechFrames = 0
      if (silenceFrames >= VAD_SILENCE_FRAMES && isSpeaking) {
        isSpeaking = false
        // 语音结束，通知服务端
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
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'mute', muted: isMuted.value }))
    }
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

    if (ws) {
      ws.close()
      ws = null
    }

    reconnectAttempts = 0
    silenceFrames = 0
    speechFrames = 0
    isSpeaking = false
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
  }
}
