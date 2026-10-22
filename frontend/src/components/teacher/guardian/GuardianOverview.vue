<template>
  <!-- 家校沟通概览：把「看不到聚合数据」补齐为 4 个指标 + 3 张图 + Top5 榜单。
       数据源由父页面按当前聚焦学生 / 时间范围统一拉取（getGuardianOverview），
       组件只负责渲染与空态，不含任何取数逻辑。 -->
  <section class="tui-section gp-ov">
    <div class="tui-section-head">
      <h3><el-icon><DataAnalysis /></el-icon>沟通概览</h3>
      <div class="tui-section-extra">
        <span class="tui-chip tui-chip-brand">近 {{ days }} 天 · {{ scopeLabel }}</span>
      </div>
    </div>

    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>聚合当前范围内的沟通留痕：场景 / 渠道分布、近 {{ days }} 天趋势与沟通最频繁的学生；选择上方学生后只看该生数据。</span>
    </div>

    <!-- 4 个关键指标：空数据一律显示 0，不出现 NaN -->
    <div class="tui-stat-row cols-4">
      <div class="tui-stat">
        <span class="tui-stat-num">{{ totals.students }}</span>
        <span class="tui-stat-label">覆盖学生数</span>
      </div>
      <div class="tui-stat">
        <span class="tui-stat-num">{{ totals.contacts }}</span>
        <span class="tui-stat-label">家长联系人</span>
      </div>
      <div class="tui-stat">
        <span class="tui-stat-num">{{ totals.logs }}</span>
        <span class="tui-stat-label">沟通记录</span>
      </div>
      <div class="tui-stat">
        <span class="tui-stat-num">{{ totals.sms }}</span>
        <span class="tui-stat-label">短信数</span>
      </div>
    </div>

    <div class="gp-ov-grid">
      <!-- 场景分布饼图 -->
      <div class="gp-ov-cell">
        <div class="gp-ov-title">场景分布</div>
        <div class="gp-ov-chart">
          <VChart v-if="sceneOption" :option="sceneOption" autoresize />
          <el-empty v-else description="暂无数据" :image-size="52" />
        </div>
      </div>

      <!-- 渠道分布条形图 -->
      <div class="gp-ov-cell">
        <div class="gp-ov-title">渠道分布</div>
        <div class="gp-ov-chart">
          <VChart v-if="channelOption" :option="channelOption" autoresize />
          <el-empty v-else description="暂无数据" :image-size="52" />
        </div>
      </div>

      <!-- 沟通最多学生 Top5：点击可切换聚焦 -->
      <div class="gp-ov-cell">
        <div class="gp-ov-title">沟通最多学生 Top5</div>
        <div v-if="topStudents.length" class="gp-ov-top">
          <button
            v-for="(s, i) in topStudents"
            :key="s.student_id"
            type="button"
            class="gp-ov-top-row"
            @click="emit('focus', s.student_id, s.student_name)"
          >
            <span class="gp-ov-rank" :class="`r${i + 1}`">{{ i + 1 }}</span>
            <span class="gp-ov-top-name">{{ s.student_name }}</span>
            <span class="gp-ov-top-count">{{ s.count }} 次</span>
          </button>
        </div>
        <el-empty v-else description="暂无数据" :image-size="52" />
      </div>

      <!-- 近 N 天沟通趋势折线图（全宽） -->
      <div class="gp-ov-cell gp-ov-wide">
        <div class="gp-ov-title">近 {{ days }} 天沟通趋势</div>
        <div class="gp-ov-chart gp-ov-chart-lg">
          <VChart v-if="trendOption" :option="trendOption" autoresize />
          <el-empty v-else description="暂无数据" :image-size="52" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { DataAnalysis, InfoFilled } from '@element-plus/icons-vue'
// 图表按需引入：与 useClassCharts 同一套 echarts/core + use([...]) 注册方式，绝不全量 import
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import type { GuardianOverview } from '@/api/guardian'

use([CanvasRenderer, PieChart, BarChart, LineChart, TooltipComponent, LegendComponent, GridComponent])

const props = withDefaults(
  defineProps<{
    /** 聚合数据；为空时全部走空态 */
    overview: GuardianOverview | null
    /** 统计窗口（天） */
    days?: number
    /** 当前聚焦学生姓名；为空表示「全部学生」口径 */
    studentName?: string
  }>(),
  { days: 30, studentName: '' }
)

const emit = defineEmits<{ focus: [studentId: number, studentName: string] }>()

/** 与教师端语义色一致的图表调色板（echarts 无法直接读 CSS 变量，故按令牌取值硬编码副本） */
const PALETTE = ['#2563eb', '#7f56d9', '#0ea5e9', '#f79009', '#d92d20', '#079455']

const totals = computed(() => props.overview?.totals ?? { students: 0, contacts: 0, logs: 0, sms: 0 })
const scopeLabel = computed(() => props.studentName || '全部学生')

const byScene = computed(() => (props.overview?.by_scene ?? []).filter((i) => i.count > 0))
const byChannel = computed(() => (props.overview?.by_channel ?? []).filter((i) => i.count > 0))
const trend = computed(() => props.overview?.trend ?? [])
const topStudents = computed(() => props.overview?.top_students ?? [])

/** 场景分布饼图：无有效计数返回 null，由模板渲染空态 */
const sceneOption = computed(() => {
  const list = byScene.value
  if (!list.length) return null
  return {
    animation: false,
    tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
    legend: { bottom: 0, textStyle: { color: '#6b7280', fontSize: 11 } },
    series: [
      {
        type: 'pie',
        radius: ['42%', '66%'],
        center: ['50%', '44%'],
        label: { show: false },
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        data: list.map((it, i) => ({ name: it.label, value: it.count, itemStyle: { color: PALETTE[i % PALETTE.length] } })),
      },
    ],
  }
})

/** 渠道分布条形图（横向，渠道名较长时更易读） */
const channelOption = computed(() => {
  const list = byChannel.value
  if (!list.length) return null
  return {
    animation: false,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', bottom: '3%', top: '6%', containLabel: true },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#6b7280', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.05)' } },
    },
    yAxis: {
      type: 'category',
      data: list.map((i) => i.label),
      axisLabel: { color: '#6b7280', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
    },
    series: [
      {
        type: 'bar',
        barWidth: '52%',
        data: list.map((i, idx) => ({ value: i.count, itemStyle: { color: PALETTE[idx % PALETTE.length], borderRadius: [0, 3, 3, 0] } })),
      },
    ],
  }
})

/** 沟通趋势折线图：全 0 视为无数据，避免空轴上出现无意义图形 */
const trendOption = computed(() => {
  const list = trend.value
  if (!list.length) return null
  if (list.reduce((sum, d) => sum + d.count, 0) === 0) return null
  return {
    animation: false,
    tooltip: { trigger: 'axis', formatter: '{b}<br/>沟通 {c} 条' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: list.map((d) => d.day.slice(5)),
      axisLabel: { color: '#6b7280', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#6b7280', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.05)' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: list.map((d) => d.count),
        lineStyle: { color: '#2563eb', width: 2 },
        itemStyle: { color: '#2563eb' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37,99,235,0.24)' },
              { offset: 1, color: 'rgba(37,99,235,0.03)' },
            ],
          },
        },
      },
    ],
  }
})
</script>

<style scoped>
.gp-ov { margin-bottom: 12px; }
.gp-ov-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.gp-ov-cell {
  min-width: 0;
  padding: 10px 11px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
}
.gp-ov-wide { grid-column: 1 / -1; }
.gp-ov-title {
  margin-bottom: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.gp-ov-chart { height: 180px; }
.gp-ov-chart-lg { height: 200px; }

/* Top5 榜单 */
.gp-ov-top { display: flex; flex-direction: column; gap: 6px; }
.gp-ov-top-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  border: 1px solid var(--tui-border);
  border-radius: 9px;
  background: var(--tui-surface);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s var(--tui-ease), background 0.15s var(--tui-ease);
}
.gp-ov-top-row:hover { border-color: var(--tui-brand); background: var(--tui-brand-soft); }
.gp-ov-rank {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-tertiary);
  font-size: 11px;
  font-weight: 700;
}
.gp-ov-rank.r1 { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.gp-ov-rank.r2 { background: #f4f3ff; color: #5925dc; }
.gp-ov-rank.r3 { background: var(--tui-warn-soft); color: var(--tui-warn); }
.gp-ov-top-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--tui-text);
}
.gp-ov-top-count {
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 767px) {
  .gp-ov-grid { grid-template-columns: 1fr; gap: 8px; }
  .gp-ov-chart { height: 200px; }
}
</style>