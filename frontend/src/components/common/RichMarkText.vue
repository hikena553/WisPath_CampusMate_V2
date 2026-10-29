<template>
  <span class="rmt">
    <template v-for="(seg, i) in segments" :key="i">
      <mark v-if="seg.kind === 'hl'" class="rmt-hl">{{ seg.text }}</mark>
      <u v-else-if="seg.kind === 'note'" class="rmt-note">{{ seg.text }}</u>
      <strong v-else-if="seg.kind === 'strong'" class="rmt-strong">{{ seg.text }}</strong>
      <span v-else>{{ seg.text }}</span>
    </template>
  </span>
</template>

<script setup lang="ts">
/**
 * 报告文本的重点标注渲染：==重点== → 黄色描色，__留意__ → 虚线下划线，**加粗** → 加粗。
 * 只解析这三种记号，其余内容按纯文本展示（不引入 Markdown，避免 XSS 面）。
 */
import { computed } from 'vue'

const props = defineProps<{ text: string }>()

type Seg = { kind: 'plain' | 'hl' | 'note' | 'strong'; text: string }

const segments = computed<Seg[]>(() => {
  const raw = props.text || ''
  const out: Seg[] = []
  let rest = raw
  const re = /(==[^=]+==|__[^_]+__|\*\*[^*]+\*\*)/
  while (rest) {
    const arr = rest.split(re)
    for (const part of arr) {
      if (!part) continue
      if (part.startsWith('==') && part.endsWith('==')) {
        out.push({ kind: 'hl', text: part.slice(2, -2) })
      } else if (part.startsWith('__') && part.endsWith('__')) {
        out.push({ kind: 'note', text: part.slice(2, -2) })
      } else if (part.startsWith('**') && part.endsWith('**')) {
        out.push({ kind: 'strong', text: part.slice(2, -2) })
      } else {
        out.push({ kind: 'plain', text: part })
      }
    }
    rest = ''
  }
  return out
})
</script>

<style scoped>
/* 黄色描色：模拟荧光笔的上下渐隐，比纯色块更接近手写标注 */
.rmt-hl {
  background: linear-gradient(180deg, rgba(255, 232, 138, 0) 0%, rgba(255, 226, 110, 0.95) 42%, rgba(255, 226, 110, 0.95) 94%, rgba(255, 232, 138, 0) 100%);
  color: inherit;
  padding: 0 2px;
  border-radius: 2px;
}
/* 虚线下划线：靛蓝虚线，表示「留意但不必马上行动」 */
.rmt-note {
  text-decoration: underline dashed;
  text-decoration-color: #7c6cf0;
  text-decoration-thickness: 1.5px;
  text-underline-offset: 3px;
}
.rmt-strong { font-weight: 700; }
</style>
