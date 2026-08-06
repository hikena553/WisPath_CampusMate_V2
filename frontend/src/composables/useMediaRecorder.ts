// 媒体录音器组合式函数
import { ref, onUnmounted } from 'vue'
import { getToken } from '@/utils/token'

export function useMediaRecorder() {
  const isRecording = ref(false)
  const isSupported = ref(false)
  const error = ref('')
  const transcribing = ref(false)

  let mediaRecorder: MediaRecorder | null = null
  let chunks: Blob[] = []

  if (typeof navigator.mediaDevices?.getUserMedia === 'function') {
    isSupported.value = true
  }

  async function start() {
    error.value = ''
    chunks = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
      mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorder.ondataavailable = (e: BlobEvent) => { if (e.data.size > 0) chunks.push(e.data) }
      mediaRecorder.onstop = uploadAudio
      mediaRecorder.onerror = () => { error.value = '录音失败' }
      mediaRecorder.start()
      isRecording.value = true
    } catch {
      error.value = '无法访问麦克风'
    }
  }

  function stop() {
    if (mediaRecorder && isRecording.value) {
      mediaRecorder.stop()
      mediaRecorder.stream.getTracks().forEach(t => t.stop())
      isRecording.value = false
    }
  }

  async function uploadAudio() {
    if (!chunks.length) return
    transcribing.value = true
    const blob = new Blob(chunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
    const formData = new FormData()
    formData.append('file', blob, 'recording.webm')
    try {
      const resp = await fetch('/api/agent/speech-to-text', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
      })
      if (!resp.ok) { error.value = '转写失败'; return }
      const data = await resp.json()
      if (data.text) {
        error.value = data.text
      }
    } catch {
      error.value = '网络错误'
    } finally {
      transcribing.value = false
    }
  }

  onUnmounted(() => {
    if (mediaRecorder && isRecording.value) {
      mediaRecorder.stream.getTracks().forEach(t => t.stop())
    }
  })

  return { isRecording, isSupported, transcribing, error, start, stop }
}
