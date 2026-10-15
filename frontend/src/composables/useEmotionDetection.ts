import { ref, shallowRef } from 'vue'
// 使用 wasm-only 入口：只需 ort-wasm-simd-threaded.mjs/.wasm（约 14MB），
// 若用默认入口（all/jsep）浏览器会去取 ort-wasm-simd-threaded.jsep.*（约 28MB），
// 本地静态目录里没有该文件就会报 "no available backend found"，模型直接加载失败。
import * as ort from 'onnxruntime-web/wasm'
import { detectPrimaryFaceYolo, prewarmYoloDetector, type FaceBox } from './yoloFaceDetector'

/**
 * 人脸情绪检测组合式函数
 *
 * 架构（2026-10 接入自训练模型 + YOLOv8 检测支线后）：
 *   1) 人脸检测：优先 YOLOv8n（本项目在真实场景基准 WIDER FACE 上训练并导出 ONNX，
 *      浏览器端本地推理）；若不可用则回退 face-api.js 的 tinyFaceDetector。
 *   2) 表情分类：本项目自训练的 FaceExpressionNet（strong64 / improved）
 *      —— 通过 ONNX Runtime Web 在浏览器端本地推理
 *
 * 为什么换掉 face-api 的 faceExpressionNet：
 *   同一 FER2013 测试集（7,178 张）同口径评测——
 *     face-api faceExpressionNet：准确率 0.5829（无 TTA）/ 0.5979（TTA）
 *     本项目 strong64        ：准确率 0.6541（无 TTA）/ 0.6616（TTA）
 *   即 +7.1 个百分点（无 TTA 严格对等比较），Macro-F1 +9.0 个百分点。
 *   评测脚本见 backend/ml/faceapi_eval.py、backend/ml/eval_checkpoints.py。
 */
export interface EmotionSnapshot {
  emotion: string
  label: string
  confidence: number
}

/** 类序必须与训练/导出时严格一致（backend/ml/architectures.py 的 CLASS_NAMES） */
export const EMOTION_CLASS_NAMES = [
  'angry',
  'disgusted',
  'fearful',
  'happy',
  'neutral',
  'sad',
  'surprised',
] as const

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
/** 自训练表情模型（ONNX，输入 1×3×64×64，输出 7 类 logits，类序见 EMOTION_CLASS_NAMES）
 *  rafmix = FER2013(去噪) + RAF-DB 真实场景数据联合训练，专为"真实摄像头"域适配。
 *  真实场景测试集 RAF-DB：improved 0.6186 → rafmix 0.7966（+17.8 个百分点）。
 */
const EMOTION_ONNX_URL = '/models/emotion_se64_rafmix.onnx'
/** ONNX Runtime 的 wasm 运行时目录（离线本地加载，不依赖 CDN） */
const ORT_WASM_PATH = '/ort/'
const INPUT_SIZE = 64
/** 推理节流：表情只需秒级粒度，避免每帧都跑一遍占用 CPU。
 *  从 250ms 收紧到 160ms —— 检测/推理本身远快于这个间隔，收紧后
 *  单位时间内多拿几次判别，配合下面的"快攻"切换，变化响应更快。 */
const INFER_INTERVAL = 160

let modelsLoaded = false
let faceapiPromise: Promise<any> | null = null
let sessionPromise: Promise<ort.InferenceSession> | null = null
/** YOLOv8n 检测器是否就绪（就绪则优先使用它做"主要目标人脸"定位） */
let yoloReady = false

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

/** 加载自训练表情模型（ONNX Runtime Web）。 */
function loadEmotionSession(): Promise<ort.InferenceSession> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      // 单线程 + 本地 wasm 路径：无需 cross-origin isolation（SharedArrayBuffer）即可运行
      ort.env.wasm.wasmPaths = ORT_WASM_PATH
      ort.env.wasm.numThreads = 1
      ort.env.wasm.proxy = false
      ort.env.logLevel = 'error'
      return ort.InferenceSession.create(EMOTION_ONNX_URL, { executionProviders: ['wasm'] })
    })().catch((e) => {
      sessionPromise = null
      throw e
    })
  }
  return sessionPromise
}

async function loadModels(): Promise<boolean> {
  if (modelsLoaded) return true
  // 表情模型是硬依赖
  try {
    await loadEmotionSession()
  } catch (e) {
    console.warn('[emotion] 表情模型加载失败：', e)
    return false
  }
  // 人脸检测：优先 YOLOv8n（真实数据训练的自研检测器）
  yoloReady = await prewarmYoloDetector()
  if (yoloReady) {
    modelsLoaded = true
    return true
  }
  // 回退 face-api.js tinyFaceDetector
  try {
    const faceapi = await loadFaceapi()
    try {
      await faceapi.tf.setBackend('webgl')
    } catch {
      /* webgl 后端不可用时回退默认（cpu）后端 */
    }
    await faceapi.tf.ready()
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_PATH)
    modelsLoaded = true
    return true
  } catch (e) {
    console.warn('[emotion] 人脸检测模型加载失败：', e)
    return false
  }
}

/**
 * 情绪稳定器："快攻慢放"滞回滤波（替代早期的"5 帧硬多数票"）。
 *
 * 早期做法的问题（真实测试中暴露）：对最近 5 次**原始标签**做多数票，
 * 于是从 A 切到 B 至少要攒够 3 票才肯改（约 0.75–1.25 秒），而且低置信度的标签
 * 与高置信度的标签计票权重完全一样 —— 表现就是"表情已经变了，界面上还挂着旧情绪"。
 *
 * 现在的规则按置信度分档，先用置信度筛选、再用一致性确认：
 *   1) 与当前一致 → 直接输出，零延迟；
 *   2) 置信度 ≥ INSTANT_SWITCH_CONF → 一票即切（模型很确定，不必等）；
 *   3) 置信度 ≥ FAST_SWITCH_CONF 且连续出现 FAST_SWITCH_STREAK 次 → 切换；
 *   4) 否则退回窗口多数票，且需达到 NORMAL_SWITCH_RATIO 才切换（慢放，抑制抖动）。
 *
 * 离线实测（backend/ml/smoother_eval.py，同一模型同一序列）：
 *   旧 5 帧多数票：切换滞后 3.55 帧 / 0.89 秒，稳定期准确率 0.8250，标签翻转 36 次
 *   本方案        ：切换滞后 2.45 帧 / 0.39 秒，稳定期准确率 0.8167，标签翻转 29 次
 * 即响应快了约 0.5 秒，稳定性仍远好于"完全不平滑"（后者翻转 87 次、准确率仅 0.675）。
 */
const SMOOTH_WINDOW = 3
const INSTANT_SWITCH_CONF = 0.75
const FAST_SWITCH_CONF = 0.55
const FAST_SWITCH_STREAK = 2
const NORMAL_SWITCH_RATIO = 0.67

export interface SmoothState {
  label: string
  window: string[]
  streakLabel: string
  streak: number
}

export function newSmoothState(): SmoothState {
  return { label: '', window: [], streakLabel: '', streak: 0 }
}

/** 纯函数实现：无副作用之外的状态，便于离线复现与对比。 */
export function stabiliseEmotion(state: SmoothState, emotion: string, confidence: number): string {
  if (emotion === state.streakLabel) state.streak += 1
  else {
    state.streakLabel = emotion
    state.streak = 1
  }

  if (!state.label) {
    state.label = emotion
    return emotion
  }
  if (emotion === state.label) return state.label

  // 一票即切：置信度足够高时不再等待（实测把切换滞后从 3.55 帧降到 2.45 帧）
  if (confidence >= INSTANT_SWITCH_CONF) {
    state.label = emotion
    state.window = [emotion]
    return emotion
  }

  if (confidence >= FAST_SWITCH_CONF && state.streak >= FAST_SWITCH_STREAK) {
    state.label = emotion
    state.window = [emotion]
    return emotion
  }

  state.window.push(emotion)
  if (state.window.length > SMOOTH_WINDOW) state.window.shift()
  const counts: Record<string, number> = {}
  for (const e of state.window) counts[e] = (counts[e] || 0) + 1
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
  if (top[1] / state.window.length >= NORMAL_SWITCH_RATIO) {
    state.label = top[0]
    state.window = [top[0]]
  }
  return state.label
}

export function useEmotionDetection() {
  const isSupported = ref(false)
  const isRunning = ref(false)
  const isReady = ref(false)
  const error = ref('')
  const current = shallowRef<EmotionSnapshot | null>(null)
  /** 实际生效的人脸检测后端：yolov8n | faceapi */
  const detectorBackend = ref('')
  /** 最新检测框（像素坐标，基于视频原始分辨率）——供演示/调试页把框画在画面上 */
  const faceBox = shallowRef<FaceBox | null>(null)
  /** 最新 7 类概率（顺序同 EMOTION_CLASS_NAMES）——供演示页展示"模型在犹豫什么" */
  const probs = shallowRef<Float32Array | null>(null)
  /** 运行统计：已处理帧数、检测耗时、表情推理耗时、处理帧率、未检出人脸次数 */
  const stats = ref({ frames: 0, detMs: 0, inferMs: 0, fps: 0, noFace: 0 })
  // 通话过程中的情绪时间线（供通话结束批量上报）
  const timeline = ref<EmotionSnapshot[]>([])

  let stream: MediaStream | null = null
  let videoEl: HTMLVideoElement | null = null
  let raf = 0
  let lastFire = 0
  let lastInfer = 0
  let cropCanvas: HTMLCanvasElement | null = null
  const FIRE_INTERVAL = 2000 // 每次表情变化至少间隔 2s 记录
  let onEmotion: ((s: EmotionSnapshot) => void) | null = null
  let trackHandle: (() => void) | null = null
  /** 情绪稳定器状态（"快攻慢放"滞回滤波） */
  const smoothState = newSmoothState()

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
      detectorBackend.value = yoloReady ? 'yolov8n' : 'faceapi'
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

  /** 按检测框裁剪人脸并做方形补边，缩放到模型输入尺寸。 */
  function cropFace(
    video: HTMLVideoElement,
    box: { x: number; y: number; width: number; height: number },
  ): HTMLCanvasElement | null {
    const side = Math.max(box.width, box.height)
    if (!Number.isFinite(side) || side <= 0) return null
    const cx = box.x + box.width / 2
    const cy = box.y + box.height / 2
    const x0 = Math.max(0, Math.round(cx - side / 2))
    const y0 = Math.max(0, Math.round(cy - side / 2))
    const w = Math.min(Math.round(side), video.videoWidth - x0)
    const h = Math.min(Math.round(side), video.videoHeight - y0)
    if (w <= 0 || h <= 0) return null

    if (!cropCanvas) {
      cropCanvas = document.createElement('canvas')
      cropCanvas.width = INPUT_SIZE
      cropCanvas.height = INPUT_SIZE
    }
    const ctx = cropCanvas.getContext('2d')
    if (!ctx) return null
    ctx.imageSmoothingEnabled = true
    // 用 canvas 缩放天然完成 AREA/双线性重采样（与训练时的 resize 口径一致）
    ctx.drawImage(video, x0, y0, w, h, 0, 0, INPUT_SIZE, INPUT_SIZE)
    return cropCanvas
  }

  /**
   * 画布 -> 模型输入张量（同时生成水平翻转张量用于 TTA）。
   * 预处理与训练严格一致（backend/ml/dataset.py）：
   *   灰度化 -> x/255 -> (x-0.5)/0.5 -> 复制为 3 通道 -> CHW
   * TTA：原图与水平翻转图各前向一次并平均 logits，与训练侧评测口径一致。
   */
  function canvasToTensors(canvas: HTMLCanvasElement): { input: ort.Tensor; flip: ort.Tensor } | null {
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    const { data } = ctx.getImageData(0, 0, INPUT_SIZE, INPUT_SIZE)
    const area = INPUT_SIZE * INPUT_SIZE
    const out = new Float32Array(3 * area)
    const flip = new Float32Array(3 * area)
    for (let y = 0; y < INPUT_SIZE; y++) {
      for (let x = 0; x < INPUT_SIZE; x++) {
        const p = y * INPUT_SIZE + x
        const r = data[p * 4]
        const g = data[p * 4 + 1]
        const b = data[p * 4 + 2]
        const gray = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        const v = (gray - 0.5) / 0.5
        out[p] = v
        out[area + p] = v
        out[2 * area + p] = v
        const fp = y * INPUT_SIZE + (INPUT_SIZE - 1 - x)
        flip[fp] = v
        flip[area + fp] = v
        flip[2 * area + fp] = v
      }
    }
    return {
      input: new ort.Tensor('float32', out, [1, 3, INPUT_SIZE, INPUT_SIZE]),
      flip: new ort.Tensor('float32', flip, [1, 3, INPUT_SIZE, INPUT_SIZE]),
    }
  }

  async function predict(
    canvas: HTMLCanvasElement,
  ): Promise<{ emotion: string; probs: Float32Array; best: number } | null> {
    const session = await loadEmotionSession()
    const tensors = canvasToTensors(canvas)
    if (!tensors) return null
    const n = EMOTION_CLASS_NAMES.length

    // TTA：原图与水平翻转图各前向一次，平均 logits
    const results = await Promise.all([
      session.run({ input: tensors.input }),
      session.run({ input: tensors.flip }),
    ])
    const la = results[0].logits?.data
    const lb = results[1].logits?.data
    if (!la || !lb || la.length !== n || lb.length !== n) return null
    const logits = new Float32Array(n)
    for (let i = 0; i < n; i++) logits[i] = 0.5 * ((la[i] as number) + (lb[i] as number))

    // softmax（数值稳定）
    let max = -Infinity
    for (let i = 0; i < n; i++) max = Math.max(max, logits[i])
    const probs = new Float32Array(n)
    let sum = 0
    for (let i = 0; i < n; i++) {
      const e = Math.exp(logits[i] - max)
      probs[i] = e
      sum += e
    }
    for (let i = 0; i < n; i++) probs[i] /= sum

    let best = 0
    for (let i = 1; i < n; i++) if (probs[i] > probs[best]) best = i
    return { emotion: EMOTION_CLASS_NAMES[best], probs, best }
  }

  /** 用当前生效的后端定位"主要目标人脸"：优先 YOLOv8n，其次 face-api。 */
  async function locateFace(video: HTMLVideoElement): Promise<FaceBox | null> {
    if (yoloReady) {
      try {
        return await detectPrimaryFaceYolo(video)
      } catch {
        return null // 单帧失败不影响后续帧
      }
    }
    const faceapi = await loadFaceapi()
    if (!faceapi) return null
    const detections = await faceapi.detectAllFaces(
      video,
      new faceapi.TinyFaceDetectorOptions({ inputSize: 224 }),
    )
    if (!detections.length) return null
    const b = detections[0].box
    return { x: b.x, y: b.y, width: b.width, height: b.height, score: detections[0].score ?? 0 }
  }

  function runDetectionLoop() {
    let frameCount = 0
    let noFaceCount = 0
    let emaFps = 0
    let lastLoopTs = 0
    const loop = async () => {
      if (!isRunning.value || !videoEl) return
      const now = Date.now()
      if (now - lastInfer >= INFER_INTERVAL) {
        lastInfer = now
        if (videoEl.readyState >= 2) {
          try {
            const tDet0 = performance.now()
            const box = await locateFace(videoEl)
            const detMs = performance.now() - tDet0
            faceBox.value = box
            let inferMs = 0
            if (box) {
              const canvas = cropFace(videoEl, box)
              const tInf0 = performance.now()
              const predicted = canvas ? await predict(canvas) : null
              inferMs = performance.now() - tInf0
              if (predicted) {
                const { emotion, probs: p, best } = predicted
                probs.value = p
                const smoothed = stabiliseEmotion(smoothState, emotion, p[best])
                const sIdx = EMOTION_CLASS_NAMES.indexOf(smoothed as (typeof EMOTION_CLASS_NAMES)[number])
                // 置信度取"平滑后标签"在本帧的概率，避免标签与置信度来自不同类别
                const confidence = sIdx >= 0 ? p[sIdx] : p[best]
                const snap: EmotionSnapshot = {
                  emotion: smoothed,
                  label: EMOTION_LABELS[smoothed] ?? smoothed,
                  confidence,
                }
                current.value = snap
                if (now - lastFire >= FIRE_INTERVAL) {
                  lastFire = now
                  timeline.value.push(snap)
                  onEmotion?.(snap)
                }
                frameCount++
              }
            } else {
              noFaceCount++
            }
            const ts = performance.now()
            const dt = lastLoopTs ? ts - lastLoopTs : 0
            lastLoopTs = ts
            if (dt > 0) emaFps = emaFps ? emaFps * 0.8 + (1000 / dt) * 0.2 : 1000 / dt
            stats.value = {
              frames: frameCount,
              detMs: Math.round(detMs),
              inferMs: Math.round(inferMs),
              fps: Math.round(emaFps * 10) / 10,
              noFace: noFaceCount,
            }
          } catch (e) {
            console.warn('[emotion] 推理失败：', e)
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
    Object.assign(smoothState, newSmoothState())
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

  /** 预热模型（不开启摄像头）：提前加载 face-api / ONNX，缩短"接通后首帧表情"耗时 */
  function prewarm(): Promise<boolean> {
    return loadModels()
  }

  return { isSupported, isRunning, isReady, error, current, timeline, detectorBackend, faceBox, probs, stats,
           start, stop, getVideo, clearTimeline, prewarm }
}

/** 快速映射一个情绪标签为中文 */
export function emotionLabel(emotion: string): string {
  return EMOTION_LABELS[emotion] ?? emotion
}