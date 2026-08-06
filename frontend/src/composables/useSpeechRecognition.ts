import { ref, onUnmounted } from 'vue'

export function useSpeechRecognition() {
  const isListening = ref(false)
  const isSupported = ref(false)
  const transcript = ref('')
  const error = ref('')

  let recognition: any = null

  const SpeechRecognitionConstructor =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

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
