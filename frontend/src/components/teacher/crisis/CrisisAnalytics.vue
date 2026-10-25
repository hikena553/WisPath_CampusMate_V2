<template>
  <!-- ① 处置态势：关键指标带 + 等级分布 / 处置阶段 / 预警趋势 -->
  <section class="tui-section">
    <div class="tui-section-head">
      <h3><el-icon><WarningFilled /></el-icon>处置态势</h3>
      <div class="tui-section-extra">
        <span class="cxa-total">共 {{ loaded ? a.total : '—' }} 条预警</span>
      </div>
    </div>

    <!-- 关键指标带：待处置 / 高危未闭环 / 随访中 / 已闭环 -->
    <div class="tui-stat-row cols-4 cxa-metrics">
      <div class="tui-stat">
        <span class="tui-stat-num cxa-num-danger">{{ loaded ? a.unresolved : '—' }}</span>
        <span class="tui-stat-label">待处置</span>
      </div>
      <div class="tui-stat">
        <span class="tui-stat-num cxa-num-danger">{{ loaded ? a.high_risk : '—' }}</span>
        <span class="tui-stat-label">高危未闭环</span>
      </div>
      <div class="tui-stat">
        <span class="tui-stat-num cxa-num-warn">{{ loaded ? a.stage.following : '—' }}</span>
        <span class="tui-stat-label">随访中</span>
      </div>
      <div class="tui-stat">
        <span class="tui-stat-num cxa-num-success">{{ loaded ? a.stage.closed : '—' }}</span>
        <span class="tui-stat-label">已闭环</span>
      </div>
    </div>

    <!-- 图表区：桌面端两列并排，移动端纵向堆叠（宽度自适应） -->
    <div class="cxa-charts">
      <div class="cxa-chart">
        <div class="cxa-chart-title">等级分布</div>
        <div class="cxa-chart-body">
          <VChart v-if="levelPieOption" class="cxa-canvas" :option="levelPieOption" autoresize />
          <div v-else class="tui-empty cxa-empty">
            <span class="tui-empty-icon"><el-icon :size="22"><WarningFilled /></el-icon></span>
            <span class="tui-empty-title">暂无预警数据</span>
          </div>
        </div>
      </div>

      <div class="cxa-chart">
        <div class="cxa-chart-title">处置阶段</div>
        <div class="cxa-chart-body">
          <VChart v-if="stageBarOption" class="cxa-canvas" :option="stageBarOption" autoresize />
          <div v-else class="tui-empty cxa-empty">
            <span class="tui-empty-icon"><el-icon :size="22"><WarningFilled /></el-icon></span>
            <span class="tui-empty-title">暂无可统计阶段</span>
          </div>
        </div>
      </div>

      <div class="cxa-chart cxa-span">
        <div class="cxa-chart-title">近 {{ props.days }} 天预警趋势</div>
        <div class="cxa-chart-body">
          <VChart v-if="trendLineOption" class="cxa-canvas cxa-canvas-line" :option="trendLineOption" autoresize />
          <div v-else class="tui-empty cxa-empty">
            <span class="tui-empty-icon"><el-icon :size="22"><WarningFilled /></el-icon></span>
            <span class="tui-empty-title">近 {{ props.days }} 天无预警记录</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ② 处置时限（SLA）：24 小时内应办结，超时高亮 -->
  <section class="tui-section">
    <div class="tui-section-head">
      <h3><el-icon><AlarmClock /></el-icon>处置时限</h3>
      <div class="tui-section-extra"><span class="cxa-total">未闭环按发现时间计</span></div>
    </div>
    <div class="cxa-sla">
      <div class="cxa-sla-stat is-overdue">
        <span class="cxa-sla-num">{{ loaded ? a.sla.overdue : '—' }}</span>
        <span class="cxa-sla-label">已超 24 小时</span>
      </div>
      <div class="cxa-sla-stat is-due">
        <span class="cxa-sla-num">{{ loaded ? a.sla.due_soon : '—' }}</span>
        <span class="cxa-sla-label">12–24 小时待办结</span>
      </div>
    </div>

    <div v-if="slaItems.length" class="cxa-sla-list">
      <div v-for="it in slaItems" :key="it.id" class="cxa-sla-item">
        <div class="cxa-sla-item-head">
          <span class="cxa-sla-name">{{ it.student_name || '未知学生' }}</span>
          <span class="cxa-sla-time">{{ formatTime(it.created_at) }}</span>
        </div>
        <span class="cxa-sla-summary tui-ellipsis-2">{{ it.summary || '（无摘要）' }}</span>
      </div>
    </div>
    <div v-else class="tui-empty cxa-empty">
      <span class="tui-empty-icon"><el-icon :size="22"><AlarmClock /></el-icon></span>
      <span class="tui-empty-title">暂无限时预警</span>
      <span class="tui-empty-desc">当前未闭环预警均在 12 小时内</span>
    </div>
  </section>

  <!-- ③ 敏感词云：命中关键词 + 摘要分词高频词 -->
  <section class="tui-section">
    <div class="tui-section-head">
      <h3><el-icon><DataAnalysis /></el-icon>敏感词云</h3>
      <div class="tui-section-extra"><span class="cxa-total">{{ a.keywords.length }} 个高频词</span></div>
    </div>
    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>词频越高字号越大，来源为预警命中关键词与摘要文本的分词统计。</span>
    </div>
    <CrisisWordCloud :words="a.keywords" />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled, AlarmClock, DataAnalysis, InfoFilled } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'
import CrisisWordCloud from './CrisisWordCloud.vue'
import type { CrisisAnalytics } from '@/api/crisis'

// echarts 按需注册（副作用，全局生效一次）
use([CanvasRenderer, PieChart, BarChart, LineChart, TooltipComponent, LegendComponent, GridComponent])

const props = withDefaults(defineProps<{
  analytics: CrisisAnalytics | null
  days?: number
}>(), { days: 30 })

/** 空数据兜底：未加载 / 后端返回空时统一走零值，避免 NaN 与空白 */
const EMPTY: CrisisAnalytics = {
  level_dist: { severe: 0, moderate: 0, mild: 0, normal: 0 },
  stage: { found: 0, intervened: 0, following: 0, closed: 0 },
  trend: [],
  keywords: [],
  sla: { overdue: 0, due_soon: 0, items: [] },
  total: 0,
  unresolved: 0,
  high_risk: 0,
}

const a = computed<CrisisAnalytics>(() => props.analytics ?? EMPTY)
const loaded = computed(() => !!props.analytics)
const slaItems = computed(() => a.value.sla.items.slice(0, 5))

/* 等级分布：环形（doughnut） */
const levelPieOption = computed<EChartsOption | null>(() => {
  const d = a.value.level_dist
  const data = [
    { name: '高危', value: d.severe, itemStyle: { color: '#d92d20' } },
    { name: '中度', value: d.moderate, itemStyle: { color: '#b54708' } },
    { name: '轻度', value: d.mild, itemStyle: { color: '#2563eb' } },
    { name: '正常', value: d.normal, itemStyle: { color: '#9ca3af' } },
  ]
  if (!data.some(x => x.value > 0)) return null

  return {
    animation: false,
    tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
    legend: {
      orient: 'horizontal',
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#6b7280', fontSize: 11 },
    },
    series: [{
      name: '等级分布',
      type: 'pie',
      radius: ['46%', '68%'],
      center: ['50%', '44%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold' } },
      data,
    }],
  }
})

/* 处置阶段：横向条形，按 发现→干预→随访→闭环 的收敛表达 */
const stageBarOption = computed<EChartsOption | null>(() => {
  const s = a.value.stage
  const values = [s.found, s.intervened, s.following, s.closed]
  if (!values.some(v => v > 0)) return null

  const colors = ['#d92d20', '#b54708', '#2563eb', '#079455']
  return {
    animation: false,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: '{b}: {c} 条' },
    grid: { left: 4, right: 20, top: 6, bottom: 0, containLabel: true },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#9ca3af', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(15,17,21,0.06)' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: ['发现', '干预', '随访', '闭环'],
      axisLabel: { color: '#6b7280', fontSize: 11 },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [{
      name: '阶段',
      type: 'bar',
      barWidth: 12,
      data: values.map((value, index) => ({
        value,
        itemStyle: { color: colors[index], borderRadius: [0, 6, 6, 0] },
      })),
    }],
  }
})

/* 预警趋势：近 days 天逐日折线 */
const trendLineOption = computed<EChartsOption | null>(() => {
  const trend = a.value.trend
  if (!trend.length || !trend.some(p => p.count > 0)) return null

  return {
    animation: false,
    tooltip: { trigger: 'axis', formatter: '{b}<br/>预警: {c} 条' },
    grid: { left: 4, right: 12, top: 10, bottom: 0, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trend.map(p => p.day),
      axisLabel: { color: '#9ca3af', fontSize: 10 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(15,17,21,0.08)' } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#9ca3af', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(15,17,21,0.06)' } },
    },
    series: [{
      name: '预警数量',
      type: 'line',
      smooth: true,
      symbolSize: 5,
      data: trend.map(p => p.count),
      lineStyle: { color: '#d92d20', width: 2 },
      itemStyle: { color: '#d92d20' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(217,45,32,0.26)' },
            { offset: 1, color: 'rgba(217,45,32,0.04)' },
          ],
        },
      },
    }],
  }
})

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.cxa-total { font-size: 11.5px; color: var(--tui-text-quiet); }

/* ===== 关键指标带：复用 .tui-stat，数字按语义着色 ===== */
.cxa-metrics { margin-bottom: 12px; }
.cxa-num-danger { color: var(--tui-danger); }
.cxa-num-warn { color: var(--tui-warn); }
.cxa-num-success { color: var(--tui-success); }

/* ===== 图表区：桌面两列，移动端纵向堆叠 ===== */
.cxa-charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.cxa-chart {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cxa-span { grid-column: 1 / -1; }
.cxa-chart-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.cxa-chart-body {
  height: 190px;
  min-width: 0;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  padding: 6px;
}
.cxa-canvas { width: 100%; height: 100%; }
.cxa-canvas-line { height: 100%; }

/* 图表内空态：收紧留白 */
.cxa-empty { padding: 14px 8px; gap: 6px; }
.cxa-empty .tui-empty-icon { width: 40px; height: 40px; }

/* ===== 处置时限（SLA） ===== */
.cxa-sla {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}
.cxa-sla-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--tui-radius-sm);
  border-left: 3px solid var(--tui-border-strong);
  background: var(--tui-surface-muted);
}
.cxa-sla-stat.is-overdue {
  border-left-color: var(--tui-danger);
  background: var(--tui-danger-soft);
}
.cxa-sla-stat.is-due {
  border-left-color: var(--tui-warn);
  background: var(--tui-warn-soft);
}
.cxa-sla-num {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.cxa-sla-label { font-size: 11.5px; color: var(--tui-text-tertiary); }

.cxa-sla-list { display: flex; flex-direction: column; gap: 8px; }
.cxa-sla-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px 11px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
}
.cxa-sla-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cxa-sla-name { font-size: 12.5px; font-weight: 600; color: var(--tui-text); }
.cxa-sla-time {
  margin-left: auto;
  font-size: 11px;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.cxa-sla-summary {
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--tui-text-tertiary);
}

@media (max-width: 767px) {
  /* 移动端：图表纵向堆叠，宽度自适应 */
  .cxa-charts { grid-template-columns: minmax(0, 1fr); gap: 10px; }
  .cxa-chart-body { height: 180px; }
  .cxa-span { grid-column: auto; }
}
</style>