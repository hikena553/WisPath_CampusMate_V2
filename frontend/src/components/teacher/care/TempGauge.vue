<template>
  <div class="cc-temp-gauge" :class="`lv-${lv.tone}`">
    <!-- 左：趣味温度计（竖直液柱 + 刻度 + 底部球泡），液柱高度按 score 做 CSS transition -->
    <div class="cc-gauge-visual">
      <svg viewBox="0 0 44 176" class="cc-gauge-svg" role="img" aria-label="本月关怀温度">
        <!-- 刻度 -->
        <line v-for="t in TICKS" :key="t.v" :x1="30" :x2="t.len" :y1="t.y" :y2="t.y" class="cc-gauge-tick" />
        <!-- 管身 -->
        <rect x="11" y="18" width="18" height="132" rx="9" class="cc-gauge-tube" />
        <!-- 液柱：全高的 rect 通过 y 下移实现按比例填充（差值即水位） -->
        <rect
          x="14" y="21" width="12" height="126" rx="6"
          class="cc-gauge-liquid"
          :style="{ fill: color, height: liquidH + 'px', y: liquidY + 'px' }"
        />
        <!-- 底部球泡（始终充盈） -->
        <circle cx="20" cy="158" r="15" class="cc-gauge-bulb" :style="{ fill: color }" />
      </svg>
      <div class="cc-gauge-num">
        <b>{{ clamped }}</b><i>%</i>
      </div>
    </div>

    <!-- 右：等级图标 + 文案 + 加温建议 chips -->
    <div class="cc-gauge-info">
      <div class="cc-gauge-head">
        <span class="cc-gauge-icon" :style="{ color }" v-html="iconMarkup" />
        <span class="cc-gauge-level">{{ level || lv.label }}</span>
        <span class="cc-gauge-score">本月关怀温度 {{ clamped }}%</span>
      </div>
      <div v-if="tipList.length" class="cc-gauge-tips">
        <span v-for="(tip, i) in tipList" :key="i" class="cc-gauge-tip">{{ tip }}</span>
      </div>
      <div v-else class="cc-gauge-tips cc-gauge-tip-ok">本月关怀节奏不错，继续保持～</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  /** 关怀温度分值 0~100 */
  score: number
  /** 可选：等级文案（不传则按 score 自动判定） */
  level?: string
  /** 可选：加温建议 chip 文案 */
  tips?: string[]
}>()

const clamped = computed(() => Math.max(0, Math.min(100, Math.round(props.score || 0))))

/** 液柱几何：管身内区间 y 21 → 147（高 126），按分值换算水位 */
const TUBE_TOP = 21
const TUBE_BOTTOM = 147
const TUBE_H = TUBE_BOTTOM - TUBE_TOP

const liquidH = computed(() => Math.max(2, Math.round((TUBE_H * clamped.value) / 100)))
const liquidY = computed(() => TUBE_BOTTOM - liquidH.value)

const TICKS = [
  { v: 100, y: 21, len: 40 },
  { v: 75, y: 52.5, len: 40 },
  { v: 50, y: 84, len: 40 },
  { v: 25, y: 115.5, len: 40 },
  { v: 0, y: 147, len: 40 },
]

/** 等级：≥80 太阳 / ≥50 温暖 / ≥25 雪花 / 否则 火焰 */
const lv = computed(() => {
  const s = clamped.value
  if (s >= 80) return { key: 'sun', tone: 'success', label: '温暖' }
  if (s >= 50) return { key: 'warm', tone: 'brand', label: '平稳' }
  if (s >= 25) return { key: 'snow', tone: 'warn', label: '偏冷' }
  return { key: 'flame', tone: 'danger', label: '需加温' }
})

const color = computed(() => {
  switch (lv.value.tone) {
    case 'success': return 'var(--tui-success)'
    case 'brand': return 'var(--tui-brand)'
    case 'warn': return 'var(--tui-warn)'
    default: return 'var(--tui-danger)'
  }
})

/** 内联 SVG 图标（零依赖，随等级切换） */
const ICONS: Record<string, { markup: string; fill: boolean }> = {
  sun: {
    fill: false,
    markup: '<circle cx="12" cy="12" r="4.4"/><path d="M12 2.2v2.6M12 19.2v2.6M2.2 12h2.6M19.2 12h2.6M5.1 5.1l1.9 1.9M17 17l1.9 1.9M18.9 5.1L17 7M7 17l-1.9 1.9"/>',
  },
  warm: {
    fill: false,
    markup: '<circle cx="12" cy="13" r="4.6"/><path d="M12 3.4v2.4M3.4 13h2.4M18.2 13h2.4M5.6 6.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 6.6l-1.8 1.8"/>',
  },
  snow: {
    fill: false,
    markup: '<path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6L5.6 18.4"/>',
  },
  flame: {
    fill: true,
    markup: '<path d="M12 2.2c3.2 4.3 5.8 6.2 5.8 10.1a5.8 5.8 0 0 1-11.6 0c0-2 .9-3.2 2-4.3.2 1.9 1.2 2.9 2.1 2.9-.2-3.2-.9-5.2 1.7-8.7z"/>',
  },
}

const iconMarkup = computed(() => {
  const icon = ICONS[lv.value.key] || ICONS.sun
  const style = icon.fill ? 'fill:currentColor;stroke:none' : 'fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round'
  return `<svg width="20" height="20" viewBox="0 0 24 24" style="${style}">${icon.markup}</svg>`
})

const tipList = computed(() => props.tips ?? [])
</script>

<style scoped>
.cc-temp-gauge {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

/* 温度计主体 */
.cc-gauge-visual {
  position: relative;
  flex-shrink: 0;
  width: 44px;
  height: 176px;
}
.cc-gauge-svg { width: 44px; height: 176px; display: block; }

.cc-gauge-tick { stroke: var(--tui-border-strong); stroke-width: 1.5; }
.cc-gauge-tube { fill: var(--tui-surface-muted); stroke: var(--tui-border-strong); stroke-width: 2; }
.cc-gauge-bulb { opacity: 0.9; }
.cc-gauge-liquid {
  opacity: 0.92;
  transition: y 0.7s cubic-bezier(0.34, 1.4, 0.5, 1), height 0.7s cubic-bezier(0.34, 1.4, 0.5, 1);
}

/* 分值读数压在下半部 */
.cc-gauge-num {
  position: absolute;
  left: 50%;
  bottom: 22px;
  transform: translateX(-50%);
  display: flex;
  align-items: baseline;
  gap: 0;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text);
  text-shadow: 0 0 4px var(--tui-surface), 0 0 2px var(--tui-surface);
}
.cc-gauge-num b { font-size: 15px; font-weight: 700; line-height: 1; }
.cc-gauge-num i { font-size: 9px; font-style: normal; color: var(--tui-text-quiet); }

/* 右侧信息区 */
.cc-gauge-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.cc-gauge-head { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.cc-gauge-icon { display: inline-flex; line-height: 0; }
.cc-gauge-level { font-size: 13px; font-weight: 700; color: var(--tui-text); }
.cc-gauge-score { font-size: 11.5px; color: var(--tui-text-quiet); }

.cc-gauge-tips { display: flex; flex-wrap: wrap; gap: 6px; }
.cc-gauge-tip {
  font-size: 11.5px;
  line-height: 1.5;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--tui-surface-muted);
  border: 1px solid var(--tui-border);
  color: var(--tui-text-secondary);
}
.cc-gauge-tip-ok { color: var(--tui-success); }

/* 等级语义色微调：图标与液柱共用一个色 */
.cc-temp-gauge.lv-success .cc-gauge-level { color: var(--tui-success); }
.cc-temp-gauge.lv-brand .cc-gauge-level { color: var(--tui-brand-strong); }
.cc-temp-gauge.lv-warn .cc-gauge-level { color: var(--tui-warn); }
.cc-temp-gauge.lv-danger .cc-gauge-level { color: var(--tui-danger); }
</style>