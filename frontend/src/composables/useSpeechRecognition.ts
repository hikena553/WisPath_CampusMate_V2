import { ref, onUnmounted } from 'vue'

/**
 * 浏览器原生语音识别（Web Speech API）。
 *
 * 注意：Android WebView（Capacitor 壳）里 window.webkitSpeechRecognition 虽然存在，
 * 但背后依赖 Chrome 的语音服务，在 App 内不可用 —— 表现为一直「正在聆听」却永远没有
 * 识别结果。所以 App 内直接判定为不支持，交给 useMediaRecorder（录音 → 后端
 * /api/agent/speech-to-text）这条链路。
 *
 * 同理，桌面 Chrome 在无法访问 Google 语音服务时会抛 network / not-allowed，
 * 这里也在运行时降级为不支持，让上层切到录音上传方案。
 */
export function useSpeechRecognition() {
  const isListening = ref(false)
  const isSupported = ref(false)
  const transcript = ref('')
  const error = ref('')

  let recognition: any = null

  const isNativeApp =
    typeof window !== 'undefined' &&
    !!(window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor?.isNativePlatform?.()

  const SpeechRecognitionConstructor = isNativeApp
    ? undefined
    : (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

  if (SpeechRecognitionConstructor) {
    isSupported.value = true
    recognition = new SpeechRecognitionConstructor()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onresult = (event: any) => {
      let interim = ''
      let final = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          final += result[0].transcript
        } else {
          interim += result[0].transcript
        }
      }
      transcript.value = final || interim
    }

    recognition.onerror = (event: any) => {
      error.value = event.error
      isListening.value = false
      // 语音服务不可用（常见于国内网络 / 企业环境）→ 永久降级，让上层改用录音上传
      if (['network', 'not-allowed', 'service-not-allowed', 'audio-capture'].includes(event.error)) {
        isSupported.value = false
        try { recognition.abort() } catch { /* 忽略 */ }
        recognition = null
      }
    }

    recognition.onend = () => {
      isListening.value = false
    }
  }

  function start() {
    error.value = ''
    transcript.value = ''
    if (recognition && !isListening.value) {
      try {
        recognition.start()
        isListening.value = true
      } catch {
        isListening.value = false
      }
    }
  }

  function stop() {
    if (recognition) {
      recognition.stop()
      isListening.value = false
    }
  }

  onUnmounted(() => {
    if (recognition) recognition.abort()
  })

  return { isListening, isSupported, transcript, error, start, stop }
}
