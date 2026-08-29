import { ref, onUnmounted } from 'vue'

/**
 * 声波动画组合式函数
 * 使用 Web Audio API AnalyserNode 获取频率数据，驱动声波柱动画
 */
export function useAudioVisualizer(barCount = 9) {
  const frequencyData = ref<number[]>(new Array(barCount).fill(0))

  let audioCtx: AudioContext | null = null
  let analyser: AnalyserNode | null = null
  let sourceNode: AudioNode | null = null
  let rafId = 0

  function connect(source: AudioNode, ctx?: AudioContext) {
    disconnect()

    audioCtx = ctx || (source.context as AudioContext)
    analyser = audioCtx.createAnalyser()
    analyser.fftSize = 256 // 128 frequency bins
    analyser.smoothingTimeConstant = 0.7

    source.connect(analyser)
    sourceNode = source

    updateLoop()
  }

  function connectFromMediaStream(stream: MediaStream, ctx?: AudioContext) {
    const _ctx = ctx || new AudioContext()
    const source = _ctx.createMediaStreamSource(stream)
    connect(source, _ctx)
    return _ctx
  }

  function connectFromAudioElement(el: HTMLAudioElement, ctx?: AudioContext) {
    const _ctx = ctx || new AudioContext()
    const source = _ctx.createMediaElementSource(el)
    connect(source, _ctx)
    return _ctx
  }

  function updateLoop() {
    if (!analyser) return

    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyser.getByteFrequencyData(dataArray)

    // 取中间的 bin 映射到 barCount 根柱子
    const step = Math.floor(bufferLength / barCount)
    const bars: number[] = []
    for (let i = 0; i < barCount; i++) {
      const idx = Math.floor(bufferLength / 2) - Math.floor(barCount / 2) * step + i * step
      const val = idx >= 0 && idx < bufferLength ? dataArray[idx] : 0
      bars.push(val / 255) // 归一化到 0~1
    }
    frequencyData.value = bars

    rafId = requestAnimationFrame(updateLoop)
  }

  function disconnect() {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = 0
    }
    if (sourceNode && analyser) {
      try {
        sourceNode.disconnect(analyser)
      } catch {
        // already disconnected
      }
    }
    sourceNode = null
    analyser = null
    frequencyData.value = new Array(barCount).fill(0)
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    frequencyData,
    connect,
    connectFromMediaStream,
    connectFromAudioElement,
    disconnect,
  }
}
