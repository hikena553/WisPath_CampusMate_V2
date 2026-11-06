// 媒体录音器组合式函数：录音 → 上传后端 /api/agent/speech-to-text → 返回文字
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getToken } from '@/utils/token'

export function useMediaRecorder() {
  const isRecording = ref(false)
  const isSupported = ref(false)
  const error = ref('')
  const transcript = ref('')
  const transcribing = ref(false)

  let mediaRecorder: MediaRecorder | null = null
  let chunks: Blob[] = []
  let startedAt = 0

  if (typeof navigator.mediaDevices?.getUserMedia === 'function') {
    isSupported.value = true
  }

  async function start() {
    error.value = ''
    chunks = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Android WebView 出 webm/opus，Safari 只出 mp4：按支持情况挑
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4'
      mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorder.ondataavailable = (e: BlobEvent) => { if (e.data.size > 0) chunks.push(e.data) }
      mediaRecorder.onstop = uploadAudio
      mediaRecorder.onerror = () => { error.value = '录音失败'; ElMessage.error('录音失败，请重试') }
      mediaRecorder.start()
      startedAt = Date.now()
      isRecording.value = true
    } catch {
      error.value = '无法访问麦克风'
      ElMessage.error('无法访问麦克风，请在系统设置里允许麦克风权限')
    }
  }

  function stop() {
    if (mediaRecorder && isRecording.value) {
      // 录音太短（<0.6s）时后端识别不到语音，直接提示而不是发一段静音上去
      if (Date.now() - startedAt < 600) {
        error.value = '录音时间太短'
        ElMessage.warning('说话时间太短，请按住多说一会儿')
        try {
          mediaRecorder.stream.getTracks().forEach(t => t.stop())
          mediaRecorder.stop()
        } catch { /* 忽略 */ }
        isRecording.value = false
        chunks = []
        return
      }
      mediaRecorder.stop()
      mediaRecorder.stream.getTracks().forEach(t => t.stop())
      isRecording.value = false
    }
  }

  async function uploadAudio() {
    if (!chunks.length) return
    transcribing.value = true
    const mime = mediaRecorder?.mimeType || 'audio/webm'
    const blob = new Blob(chunks, { type: mime })
    // 文件名后缀要和真实容器一致：后端按扩展名判定格式
    const ext = mime.includes('mp4') ? 'm4a' : 'webm'
    const formData = new FormData()
    formData.append('file', blob, `recording.${ext}`)
    try {
      const token = getToken()
      const resp = await fetch('/api/agent/speech-to-text', {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: formData,
      })
      if (!resp.ok) {
        let detail = '语音识别失败'
        try { detail = (await resp.json())?.detail || detail } catch { /* 非 JSON 响应 */ }
        error.value = detail
        ElMessage.error(detail)
        return
      }
      const data = await resp.json()
      if (data.text) {
        transcript.value = data.text
      } else {
        error.value = '没有识别到内容'
        ElMessage.warning('没有识别到语音内容，请再说一遍')
      }
    } catch {
      error.value = '网络错误'
      ElMessage.error('语音识别失败，请检查网络后重试')
    } finally {
      transcribing.value = false
      chunks = []
    }
  }

  onUnmounted(() => {
    if (mediaRecorder && isRecording.value) {
      mediaRecorder.stream.getTracks().forEach(t => t.stop())
    }
  })

  return { isRecording, isSupported, transcribing, error, transcript, start, stop }
}
