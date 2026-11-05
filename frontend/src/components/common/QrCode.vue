<template>
  <canvas
    ref="canvasEl"
    class="qr-canvas"
    :style="{ width: `${size}px`, height: `${size}px` }"
    role="img"
    :aria-label="`二维码：${value}`"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'

const props = withDefaults(defineProps<{ value: string; size?: number }>(), { size: 132 })

const canvasEl = ref<HTMLCanvasElement>()
let renderSeq = 0

async function render() {
  if (!canvasEl.value || !props.value) return
  const seq = ++renderSeq
  const canvas = canvasEl.value
  try {
    await QRCode.toCanvas(canvas, props.value, {
      // 用两倍像素绘制再缩放到显示尺寸，保证扫码识别率
      width: Math.max(256, props.size * 2),
      margin: 2,
      errorCorrectionLevel: 'M',
      color: { dark: '#111111', light: '#ffffff' },
    })
    // qrcode 库会把 canvas 的 style 宽高改写为绘制像素尺寸，
    // 这里再按组件传入的显示尺寸覆写，避免二维码在页面里被放大
    if (seq === renderSeq) {
      canvas.style.width = `${props.size}px`
      canvas.style.height = `${props.size}px`
    }
  } catch {
    // 绘制失败时保留空白画布，不打断页面其它内容
  }
}

watch(() => [props.value, props.size], render, { flush: 'post' })

onMounted(render)

onBeforeUnmount(() => {
  renderSeq++
})
</script>

<style scoped>
.qr-canvas {
  display: block;
  border-radius: 12px;
  background: #ffffff;
}
</style>
