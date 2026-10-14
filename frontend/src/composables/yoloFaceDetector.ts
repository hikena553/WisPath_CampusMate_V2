import * as ort from 'onnxruntime-web/wasm'

/**
 * YOLOv8n 单类人脸检测器（浏览器端 ONNX 推理）。
 *
 * 模型来源：本项目在 <b>真实场景人脸检测基准 WIDER FACE</b> 上训练
 * （见 backend/ml/train_yolo_face.py + ml/wider_to_yolo.py），
 * 导出为 320×320 输入、2.0 GFLOPs 的 ONNX（best.onnx，约 11.6 MB）。
 *
 * 为什么用 320 输入：YOLOv8n 在 640 下是 8.1 GFLOPs，浏览器 wasm 单线程下太慢；
 * 通话场景里主目标人脸在画面中占比很大，320 已足够，且能维持约 4 fps 的检测频率。
 *
 * 解码要点（ultralytics 导出格式 [1, 5, N]，N=40²+20²+10²=2100）：
 *   data[c * N + i]：c=0..3 为 cx/cy/w/h（320 letterbox 坐标系），c=4 为类别置信度。
 * 前处理与 ultralytics 严格对齐：letterbox 到 320×320（灰底 114）-> RGB -> /255 -> CHW。
 */
export interface FaceBox {
  x: number
  y: number
  width: number
  height: number
  score: number
}

const YOLO_ONNX_URL = '/models/face_yolov8n.onnx'
const ORT_WASM_PATH = '/ort/'
const DET_SIZE = 320
const CONF_THRES = 0.25
const IOU_THRES = 0.45
const MAX_DET = 20

let yoloPromise: Promise<ort.InferenceSession> | null = null
let detCanvas: HTMLCanvasElement | null = null

function loadYolo(): Promise<ort.InferenceSession> {
  if (!yoloPromise) {
    yoloPromise = (async () => {
      ort.env.wasm.wasmPaths = ORT_WASM_PATH
      ort.env.wasm.numThreads = 1
      ort.env.wasm.proxy = false
      ort.env.logLevel = 'error'
      return ort.InferenceSession.create(YOLO_ONNX_URL, { executionProviders: ['wasm'] })
    })().catch((e) => {
      yoloPromise = null
      throw e
    })
  }
  return yoloPromise
}

/** 预热（仅加载模型，不做推理）。 */
export function prewarmYoloDetector(): Promise<boolean> {
  return loadYolo()
    .then(() => true)
    .catch(() => false)
}

interface Letterbox {
  tensor: ort.Tensor
  scale: number
  padX: number
  padY: number
}

function letterbox(video: HTMLVideoElement): Letterbox | null {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (!vw || !vh) return null
  if (!detCanvas) {
    detCanvas = document.createElement('canvas')
    detCanvas.width = DET_SIZE
    detCanvas.height = DET_SIZE
  }
  const ctx = detCanvas.getContext('2d')
  if (!ctx) return null

  const scale = Math.min(DET_SIZE / vw, DET_SIZE / vh)
  const nw = Math.round(vw * scale)
  const nh = Math.round(vh * scale)
  const padX = Math.floor((DET_SIZE - nw) / 2)
  const padY = Math.floor((DET_SIZE - nh) / 2)

  // 与 ultralytics 一致：先 fill 114 灰底，再把缩放后的画面居中贴入
  ctx.fillStyle = 'rgb(114,114,114)'
  ctx.fillRect(0, 0, DET_SIZE, DET_SIZE)
  ctx.imageSmoothingEnabled = true
  ctx.drawImage(video, 0, 0, vw, vh, padX, padY, nw, nh)

  const { data } = ctx.getImageData(0, 0, DET_SIZE, DET_SIZE)
  const area = DET_SIZE * DET_SIZE
  const out = new Float32Array(3 * area)
  for (let p = 0; p < area; p++) {
    out[p] = data[p * 4] / 255
    out[area + p] = data[p * 4 + 1] / 255
    out[2 * area + p] = data[p * 4 + 2] / 255
  }
  return { tensor: new ort.Tensor('float32', out, [1, 3, DET_SIZE, DET_SIZE]), scale, padX, padY }
}

function iou(a: FaceBox, b: FaceBox): number {
  const x0 = Math.max(a.x, b.x)
  const y0 = Math.max(a.y, b.y)
  const x1 = Math.min(a.x + a.width, b.x + b.width)
  const y1 = Math.min(a.y + a.height, b.y + b.height)
  const inter = Math.max(0, x1 - x0) * Math.max(0, y1 - y0)
  const union = a.width * a.height + b.width * b.height - inter
  return union > 0 ? inter / union : 0
}

/** 检测一帧中的所有（经 NMS 后的）人脸，坐标已还原到视频像素坐标系。 */
export async function detectFacesYolo(video: HTMLVideoElement): Promise<FaceBox[]> {
  const session = await loadYolo()
  const lb = letterbox(video)
  if (!lb) return []
  const out = await session.run({ images: lb.tensor })
  const tensor = out.output0 ?? out[Object.keys(out)[0]]
  const data = tensor.data as Float32Array
  const n = tensor.dims[tensor.dims.length - 1] // 2100

  const boxes: FaceBox[] = []
  for (let i = 0; i < n; i++) {
    const score = data[4 * n + i]
    if (score < CONF_THRES) continue
    const cx = data[i]
    const cy = data[n + i]
    const w = data[2 * n + i]
    const h = data[3 * n + i]
    // letterbox 坐标 -> 视频坐标
    const x0 = (cx - w / 2 - lb.padX) / lb.scale
    const y0 = (cy - h / 2 - lb.padY) / lb.scale
    const bw = w / lb.scale
    const bh = h / lb.scale
    if (!Number.isFinite(x0) || !Number.isFinite(y0) || bw <= 1 || bh <= 1) continue
    boxes.push({ x: x0, y: y0, width: bw, height: bh, score })
  }
  boxes.sort((a, b) => b.score - a.score)

  const keep: FaceBox[] = []
  for (const b of boxes) {
    if (keep.length >= MAX_DET) break
    if (keep.every((k) => iou(k, b) <= IOU_THRES)) keep.push(b)
  }
  return keep
}

/** 取"主要目标人脸"：置信度最高且面积最大者优先（通话场景关注画面主目标）。 */
export async function detectPrimaryFaceYolo(video: HTMLVideoElement): Promise<FaceBox | null> {
  const faces = await detectFacesYolo(video)
  if (faces.length === 0) return null
  const frameArea = video.videoWidth * video.videoHeight || 1
  let best = faces[0]
  let bestScore = -1
  for (const f of faces) {
    // 面积占比 0.6 权重 + 置信度 0.4 权重
    const s = (f.width * f.height) / frameArea * 0.6 + f.score * 0.4
    if (s > bestScore) {
      bestScore = s
      best = f
    }
  }
  return best
}