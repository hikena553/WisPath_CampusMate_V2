<template>
  <div class="cc-temp-gauge" :class="`lv-${lv.tone}`">
    <!-- 顶部一行：等级图标 + 文案 + 分值 -->
    <div class="cc-gauge-head">
      <span class="cc-gauge-icon" :style="{ color }" v-html="iconMarkup" />
      <span class="cc-gauge-level">{{ level || lv.label }}</span>
      <span class="cc-gauge-score">本月关怀温度</span>
      <b class="cc-gauge-pct">{{ clamped }}<i>%</i></b>
    </div>

    <!-- 横向温度计：左侧球泡 + 横向管身，液柱从左往右填充 -->
    <div class="cc-gauge-visual">
      <svg viewBox="0 0 260 32" class="cc-gauge-svg" role="img" :aria-label="`本月关怀温度 ${clamped}%`">
        <!-- 刻度 -->
        <line v-for="t in TICKS" :key="t.v" :x1="t.x" :x2="t.x" y1="4" y2="8" class="cc-gauge-tick" />
        <!-- 管身 -->
        <rect x="21" y="9" width="218" height="14" rx="7" class="cc-gauge-tube" />
        <!-- 液柱：宽度按分值比例从左侧延伸 -->
        <rect
          x="21" y="9" :width="liquidW" height="14" rx="7"
          class="cc-gauge-liquid"
          :style="{ fill: color }"
        />
        <!-- 左侧球泡（始终充盈） -->
        <circle cx="15" cy="16" r="12" class="cc-gauge-bulb" :style="{ fill: color }" />
      </svg>
      <div class="cc-gauge-scale" aria-hidden="true">
        <span v-for="t in TICKS" :key="t.v" :style="{ left: tickLeft(t.v) }">{{ t.v }}</span>
      </div>
    </div>

    <!-- 加温建议 chips（看板页会隐藏，由可点击的加温行动替代） -->
    <div v-if="tipList.length" class="cc-gauge-tips">
      <span v-for="(tip, i) in tipList" :key="i" class="cc-gauge-tip">{{ tip }}</span>
    </div>
    <div v-else class="cc-gauge-tips cc-gauge-tip-ok">本月关怀节奏不错，继续保持～</div>
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

/** 液柱几何：管身 x 21 → 239（长 218），按分值换算填充宽度 */
const TUBE_X = 21
const TUBE_W = 218

const liquidW = computed(() => Math.max(3, Math.round((TUBE_W * clamped.value) / 100)))

/** 刻度：0/25/50/75/100 对应管身等分位置 */
const TICKS = [0, 25, 50, 75, 100].map((v) => ({ v, x: TUBE_X + (TUBE_W * v) / 100 }))

/** 刻度读数与 SVG 管身同一坐标系对齐（viewBox 宽 260） */
function tickLeft(v: number) {
  return `${((TUBE_X + (TUBE_W * v) / 100) / 260) * 100}%`
}

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
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

/* 顶部信息行 */
.cc-gauge-head { display: flex; align-items: center; gap: 7px; min-width: 0; }
.cc-gauge-icon { display: inline-flex; line-height: 0; }
.cc-gauge-level { font-size: 13px; font-weight: 700; color: var(--tui-text); }
.cc-gauge-score { font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-gauge-pct {
  margin-left: auto;
  font-size: 19px;
  font-weight: 700;
  line-height: 1;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.cc-gauge-pct i { font-style: normal; font-size: 10px; font-weight: 400; color: var(--tui-text-quiet); }

/* 横向温度计：球泡在左，液柱向右延伸 */
.cc-gauge-visual { min-width: 0; }
.cc-gauge-svg { display: block; width: 100%; max-width: 420px; height: auto; }

.cc-gauge-tick { stroke: #c2d5c9; stroke-width: 1.5; }
.cc-gauge-tube { fill: var(--tui-surface-muted); stroke: var(--tui-border-strong); stroke-width: 1.5; }
.cc-gauge-bulb { opacity: 0.9; }
.cc-gauge-liquid {
  opacity: 0.92;
  transition: width 0.7s cubic-bezier(0.34, 1.4, 0.5, 1);
}

/* 刻度读数：与 SVG 管身两端对齐 */
.cc-gauge-scale {
  position: relative;
  height: 13px;
  margin-top: 1px;
  font-size: 9.5px;
  color: #96a89f;
  font-variant-numeric: tabular-nums;
}
.cc-gauge-scale span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  line-height: 1.2;
}

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
