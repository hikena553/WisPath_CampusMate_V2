import { ref, shallowRef } from 'vue'

/**
 * 人脸情绪检测组合式函数
 * 基于 face-api.js 公开预训练模型（tinyFaceDetector 人脸检测 + faceExpressionNet 七类情绪）在浏览器端实时推理
 */
export interface EmotionSnapshot {
  emotion: string
  label: string
  confidence: number
}

export const EMOTION_LABELS: Record<string, string> = {
  neutral: '平静',
  happy: '开心',
  sad: '难过',
  angry: '生气',
  fearful: '害怕',
  disgusted: '厌恶',
  surprised: '惊讶',
}

export const EMOTION_EMOJI: Record<string, string> = {
  neutral: '😐',
  happy: '😄',
  sad: '😢',
  angry: '😡',
  fearful: '😨',
  disgusted: '😖',
  surprised: '😲',
}

const MODELS_PATH = '/models'
let modelsLoaded = false
let faceapiPromise: Promise<any> | null = null

// face-api.js 的 ESM 构建（vite 优先取 module 字段）只有命名导出、没有 default 导出，
// 而 CJS 互操作场景下 .default 指向整个模块对象。这里同时兼容两种形态，
// 并缓存同一个 Promise 供加载与推理循环复用，避免重复初始化。
function loadFaceapi(): Promise<any> {
  if (!faceapiPromise) {
    faceapiPromise = import('face-api.js').then((m) => {
      const ns = (m as any).default ?? m
      if (!ns || !ns.tf) throw new Error('face-api.js 初始化失败：缺少 tf 命名空间')
      return ns
    })
  }
  return faceapiPromise
}

async function loadModels(): Promise<boolean> {
  if (modelsLoaded) return true
  try {
    const faceapi = await loadFaceapi()
    try {
      await faceapi.tf.setBackend('webgl')
    } catch {
      /* webgl 后端不可用时回退默认（cpu）后端 */
    }
    await faceapi.tf.ready()
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_PATH)
    await faceapi.nets.faceExpressionNet.loadFromUri(MODELS_PATH)
    modelsLoaded = true
    return true
  } catch (e) {
    console.warn('[emotion] 情绪模型加载失败：', e)
    return false
  }
}

export function useEmotionDetection() {
  const isSupported = ref(false)
  const isRunning = ref(false)
  const isReady = ref(false)
  const error = ref('')
  const current = shallowRef<EmotionSnapshot | null>(null)
  // 通话过程中的情绪时间线（供通话结束批量上报）
  const timeline = ref<EmotionSnapshot[]>([])

  let stream: MediaStream | null = null
  let videoEl: HTMLVideoElement | null = null
  let raf = 0
  let lastFire = 0
  const FIRE_INTERVAL = 2000 // 每次表情变化至少间隔 2s 记录
  let onEmotion: ((s: EmotionSnapshot) => void) | null = null
  let trackHandle: (() => void) | null = null

  async function start(onChange?: (s: EmotionSnapshot) => void): Promise<boolean> {
    if (isRunning.value) return true
    onEmotion = onChange ?? null
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        error.value = '当前浏览器不支持摄像头'
        return false
      }
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 320, height: 240 },
        audio: false,
      })
      videoEl = document.createElement('video')
      videoEl.srcObject = stream
      videoEl.muted = true
      videoEl.playsInline = true
      await videoEl.play()

      if (!(await loadModels())) {
        error.value = '情绪模型加载失败'
        return false
      }
      isReady.value = true
      isSupported.value = true
      isRunning.value = true
      runDetectionLoop()
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : '摄像头启动失败'
      stop()
      return false
    }
  }

  // 均值平滑：用最近几次结果中和抖动
  const recent: string[] = []
  function smoothedEmotion(emotion: string): string {
    recent.push(emotion)
    if (recent.length > 5) recent.shift()
    const counts: Record<string, number> = {}
    for (const e of recent) counts[e] = (counts[e] || 0) + 1
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
  }

  function runDetectionLoop() {
    const faceapiP = loadFaceapi()
    const loop = async () => {
      if (!isRunning.value || !videoEl) return
      const faceapi = await faceapiP
      const now = Date.now()
      if (faceapi && videoEl && videoEl.readyState >= 2) {
        const detections = (await faceapi
          .detectAllFaces(videoEl, new faceapi.TinyFaceDetectorOptions({ inputSize: 224 }))
          .withFaceExpressions()) as Array<{ expressions: Record<string, number> }>
        if (detections.length > 0) {
          const exp = detections[0].expressions
          const top = Object.entries(exp).sort((a, b) => (b[1] as number) - (a[1] as number))[0]
          const emotion = smoothedEmotion(top[0])
          const confidence = top[1] as number
          const snap: EmotionSnapshot = {
            emotion,
            label: EMOTION_LABELS[emotion] ?? emotion,
            confidence,
          }
          current.value = snap
          if (now - lastFire >= FIRE_INTERVAL) {
            lastFire = now
            timeline.value.push(snap)
            onEmotion?.(snap)
          }
        }
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
  }

  function getVideo(): HTMLVideoElement | null {
    return videoEl
  }

  function stop() {
    isRunning.value = false
    isReady.value = false
    current.value = null
    if (raf) cancelAnimationFrame(raf)
    raf = 0
    if (stream) {
      stream.getTracks().forEach((t) => t.stop())
      stream = null
    }
    if (videoEl) {
      videoEl.srcObject = null
      videoEl = null
    }
    trackHandle?.()
    trackHandle = null
  }

  function clearTimeline() {
    timeline.value = []
  }

  return { isSupported, isRunning, isReady, error, current, timeline, start, stop, getVideo, clearTimeline }
}

/** 快速映射一个情绪标签为中文 */
export function emotionLabel(emotion: string): string {
  return EMOTION_LABELS[emotion] ?? emotion
}