# 语音输入功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 ChatPanel 添加麦克风按钮，用户说话自动转文字填入输入框

**Architecture:** 浏览器 Web Speech API 优先（不依赖后端），DashScope ASR 作为兼容性回退

**Tech Stack:** Web Speech API, MediaRecorder API, DashScope paraformer, FastAPI

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `frontend/src/composables/useSpeechRecognition.ts` | Create | Web Speech API 封装 composable |
| `frontend/src/components/agent/ChatPanel.vue` | Modify | 输入栏增加麦克风按钮，集成语音 composable |
| `backend/app/services/llm_service.py` | Modify | 新增 `speech_to_text()` 方法 |
| `backend/app/api/agent.py` | Modify | 新增 `POST /api/agent/speech-to-text` 端点 |
| `frontend/src/composables/useMediaRecorder.ts` | Create | MediaRecorder 录制 + 上传 composable（备用） |

---

### Task 1: 创建 useSpeechRecognition composable

**Files:**
- Create: `frontend/src/composables/useSpeechRecognition.ts`

- [ ] **Step 1: 创建 composable 文件**

```typescript
// frontend/src/composables/useSpeechRecognition.ts
import { ref, onUnmounted } from 'vue'

export function useSpeechRecognition() {
  const isListening = ref(false)
  const isSupported = ref(false)
  const transcript = ref('')
  const error = ref('')

  let recognition: SpeechRecognition | null = null

  const SpeechRecognitionConstructor =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

  if (SpeechRecognitionConstructor) {
    isSupported.value = true
    recognition = new SpeechRecognitionConstructor()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onresult = (event: SpeechRecognitionEvent) => {
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

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useSpeechRecognition.ts
git commit -m "feat: create useSpeechRecognition composable"
```

---

### Task 2: ChatPanel 集成麦克风按钮

**Files:**
- Modify: `frontend/src/components/agent/ChatPanel.vue`

- [ ] **Step 1: 在 ChatPanel 输入栏增加麦克风按钮**

在 `input-actions` div 中的"上传图片"按钮之后，提交按钮之前插入：

```vue
<el-tooltip :content="micTooltip" placement="top">
  <el-button
    text
    :class="['tool-btn', { 'mic-active': speech.isListening }]"
    :disabled="loading || !speech.isSupported"
    @click="toggleMic"
  >
    <el-icon :size="18"><Microphone /></el-icon>
  </el-button>
</el-tooltip>
```

- [ ] **Step 2: 添加图标 import**

在 import 语句的图标列表中增加 `Microphone`：

```typescript
import {
  Promotion, Paperclip, Picture, Document, Calendar, Clock,
  DataAnalysis, TrendCharts, PictureFilled, WarningFilled, User, CircleCheck, Microphone,
} from '@element-plus/icons-vue'
```

- [ ] **Step 3: 引入 composable 和逻辑**

在 `<script setup>` 中，合适位置插入：

```typescript
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'

const speech = useSpeechRecognition()

const micTooltip = computed(() => {
  if (!speech.isSupported) return '当前浏览器不支持语音输入'
  if (speech.isListening) return '正在聆听...'
  return '语音输入'
})

function toggleMic() {
  if (speech.isListening) {
    speech.stop()
    if (speech.transcript.value) {
      input.value += speech.transcript.value
    }
  } else {
    speech.start()
  }
}
```

- [ ] **Step 4: 添加 CSS 样式**

在 `<style scoped>` 中任意位置插入：

```css
.mic-active {
  color: #f56c6c !important;
  background: rgba(245, 108, 108, 0.1) !important;
  animation: mic-pulse 1.2s ease-in-out infinite;
}
@keyframes mic-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(245, 108, 108, 0); }
}
```

- [ ] **Step 5: 验证 build**

Run: `cd frontend && npm run build`
Expected: 无错误，构建成功

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/agent/ChatPanel.vue
git commit -m "feat: ChatPanel 集成语音输入麦克风按钮"
```

---

### Task 3: 后端 speech-to-text 端点

**Files:**
- Modify: `backend/app/services/llm_service.py`
- Modify: `backend/app/api/agent.py`

- [ ] **Step 1: llm_service.py 新增 speech_to_text 方法**

在 `build_system_prompt` 函数之后新增：

```python
import httpx
import base64

def speech_to_text(audio_bytes: bytes, filename: str) -> str:
    url = f"{settings.LLM_BASE_URL}/audio/transcriptions"
    files = {"file": (filename, audio_bytes, "audio/webm")}
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    try:
        resp = httpx.post(url, headers=headers, files=files, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "")
    except Exception as e:
        raise RuntimeError(f"语音识别失败: {e}")
```

- [ ] **Step 2: agent.py 新增 /speech-to-text 端点**

在 `chat_api` 函数之后新增：

```python
from fastapi import UploadFile, File
from app.services.llm_service import speech_to_text

@router.post("/speech-to-text")
async def speech_to_text_api(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(400, "文件名为空")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"wav", "mp3", "webm", "ogg", "m4a"}
    if ext not in allowed:
        raise HTTPException(400, f"不支持的音频格式: {ext}，支持: {', '.join(allowed)}")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "音频文件不能超过 10MB")
    try:
        text = speech_to_text(content, file.filename)
        return {"text": text}
    except RuntimeError as e:
        raise HTTPException(502, str(e))
```

- [ ] **Step 3: 验证后端可导入**

Run: `python -c "from app.services.llm_service import speech_to_text; print('OK')"`
Expected: OK（可能需要 `cd backend`）

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/llm_service.py backend/app/api/agent.py
git commit -m "feat: 新增语音转文字接口 /api/agent/speech-to-text"
```

---

### Task 4: 创建 useMediaRecorder fallback composable

**Files:**
- Create: `frontend/src/composables/useMediaRecorder.ts`

- [ ] **Step 1: 创建 composable**

```typescript
// frontend/src/composables/useMediaRecorder.ts
import { ref, onUnmounted } from 'vue'
import { getToken } from '@/utils/token'

export function useMediaRecorder() {
  const isRecording = ref(false)
  const isSupported = ref(false)
  const error = ref('')
  const transcribing = ref(false)

  let mediaRecorder: MediaRecorder | null = null
  let chunks: Blob[] = []

  if (navigator.mediaDevices?.getUserMedia) {
    isSupported.value = true
  }

  async function start() {
    error.value = ''
    chunks = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
      mediaRecorder = new MediaRecorder(stream, { mimeType })
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
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
        const inputEl = document.querySelector('.chat-textarea') as HTMLTextAreaElement
        if (inputEl) inputEl.value = (inputEl.value + data.text)
        inputEl?.dispatchEvent(new Event('input'))
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useMediaRecorder.ts
git commit -m "feat: create useMediaRecorder fallback composable"
```

---

### Task 5: ChatPanel 集成 fallback 录音 UI

**Files:**
- Modify: `frontend/src/components/agent/ChatPanel.vue`

- [ ] **Step 1: import useMediaRecorder + 注入 fallback UI**

在 `<script setup>` 中加入：

```typescript
import { useMediaRecorder } from '@/composables/useMediaRecorder'

const recorder = useMediaRecorder()
```

当 `speech.isSupported === false` 时，如果 `recorder.isSupported === true`，显示"录音"按钮代替语音输入。修改 `toggleMic`：

```typescript
function toggleMic() {
  if (!speech.isSupported && recorder.isSupported) {
    if (recorder.isRecording) {
      recorder.stop()
    } else {
      recorder.start()
    }
    return
  }
  if (speech.isListening) {
    speech.stop()
    if (speech.transcript.value) {
      input.value += speech.transcript.value
    }
  } else {
    speech.start()
  }
}
```

修改 tooltip 逻辑：

```typescript
const micTooltip = computed(() => {
  if (!speech.isSupported && recorder.isSupported) {
    if (recorder.isRecording) return '录音中...'
    if (recorder.transcribing) return '转写中...'
    return '录音输入'
  }
  if (!speech.isSupported) return '当前浏览器不支持语音输入'
  if (speech.isListening) return '正在聆听...'
  return '语音输入'
})
```

- [ ] **Step 2: 验证 build**

Run: `cd frontend && npm run build`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/agent/ChatPanel.vue
git commit -m "feat: ChatPanel 集成 fallback 录音输入"
```
