<template>
  <div class="admin-home">
    <!-- ===== 核心指标 ===== -->
    <section class="kpis" aria-label="核心指标">
      <div
        v-for="card in kpiCards"
        :key="card.label"
        class="kpi"
        :class="{ 'kpi-link': card.to }"
        :role="card.to ? 'button' : undefined"
        :tabindex="card.to ? 0 : undefined"
        @click="card.to && router.push(card.to)"
        @keydown.enter="card.to && router.push(card.to)"
      >
        <div class="kpi-icon" :style="{ color: card.color, background: hexA(card.color, 0.12) }">
          <el-icon :size="19"><component :is="card.icon" /></el-icon>
        </div>
        <div class="kpi-body">
          <span class="kpi-label">{{ card.label }}</span>
          <div class="kpi-value-row">
            <span class="kpi-value" :style="{ color: card.color }">{{ fmt(card.value) }}</span>
            <span class="kpi-unit">{{ card.unit }}</span>
          </div>
          <span class="kpi-tag">{{ card.tag }}</span>
        </div>
      </div>
    </section>

    <!-- ===== 主区：左中右三栏 ===== -->
    <section class="main">
      <!-- 左栏 -->
      <div class="col">
        <div class="panel">
          <div class="panel-head">
            <span class="panel-title"><i></i>心理危机预警监测</span>
            <button type="button" class="panel-more" @click="router.push('/admin/crisis')">预警中心 »</button>
          </div>
          <div class="panel-body crisis">
            <div
              v-for="row in crisisRows"
              :key="row.key"
              class="crisis-row"
              role="button"
              tabindex="0"
              @click="openCrisisDetail(row.key)"
              @keydown.enter="openCrisisDetail(row.key)"
            >
              <span class="crisis-dot" :style="{ background: row.color }"></span>
              <span class="crisis-name">{{ row.label }}</span>
              <span class="crisis-track">
                <i class="crisis-fill" :style="{ width: row.percent + '%', background: row.color }"></i>
              </span>
              <span class="crisis-count" :style="{ color: row.color }">{{ row.count }}</span>
            </div>
            <div class="crisis-foot">
              <span>重点关注 <b>{{ crisisFocus }}</b> 人</span>
              <span>已建档 <b>{{ crisisTracked }}</b> 人</span>
            </div>
          </div>
        </div>

        <div class="panel panel-grow">
          <div class="panel-head">
            <span class="panel-title"><i></i>各学院学生分布</span>
            <span class="panel-note">点击图表进入学生管理</span>
          </div>
          <div class="panel-body chart-body">
            <VChart
              v-if="collegeBarOption"
              :option="collegeBarOption"
              autoresize
              style="height:100%;width:100%"
              @click="() => onChartClick('college', { name: '' })"
            />
            <div v-else class="empty">暂无数据</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <span class="panel-title"><i></i>每日资讯速览</span>
            <span class="panel-note">每 30 分钟自动抓取</span>
          </div>
          <div class="panel-body feed-body">
            <div v-if="feedList.length" class="feed">
              <div class="feed-list" :class="{ 'feed-anim': feedList.length > 4 && !reducedMotion }">
                <div
                  v-for="(f, i) in feedRows"
                  :key="f.id + '-' + i"
                  class="feed-row"
                  role="link"
                  tabindex="0"
                  :title="f.title"
                  @click="openFeedLink(f)"
                  @keydown.enter="openFeedLink(f)"
                >
                  <span class="feed-badge" :style="feedBadgeStyle(f)">{{ feedTypeLabel(f.source_type) }}</span>
                  <span class="feed-title">{{ f.title }}</span>
                  <span class="feed-time">{{ feedTime(f) }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty">暂无资讯数据</div>
          </div>
        </div>
      </div>

      <!-- 中栏 -->
      <div class="col">
        <div class="panel panel-grow panel-scene">
          <div class="panel-head">
            <span class="panel-title"><i></i>校园数字孪生场景</span>
            <span class="panel-note">CAMPUS DIGITAL TWIN</span>
          </div>
          <div class="panel-body scene">
            <img class="scene-img" src="/images/campus/游仙校区夜景.jpg" alt="校园夜景数字孪生场景" />
            <div class="scene-veil"></div>
            <span class="corner tl"></span><span class="corner tr"></span>
            <span class="corner bl"></span><span class="corner br"></span>
            <div class="scene-tag t1"><i></i><b>学生总数</b><em>{{ fmt(dashboard?.student_count ?? 0) }}</em></div>
            <div class="scene-tag t2"><i></i><b>AI 会话</b><em>{{ fmt(dashboard?.conversation_count ?? 0) }}</em></div>
            <div class="scene-tag t3"><i></i><b>知识库</b><em>{{ fmt(dashboard?.knowledge_count ?? 0) }}</em></div>
            <div class="scene-tag t4"><i></i><b>危机关注</b><em>{{ fmt(crisisFocus) }}</em></div>
            <div class="scene-bar">
              <span>平均响应 <b>{{ dashboard?.avg_response_time ?? '0.0' }}s</b></span>
              <span>教师总数 <b>{{ fmt(dashboard?.teacher_count ?? 0) }}</b></span>
              <span>消息总量 <b>{{ fmt(dashboard?.message_count ?? 0) }}</b></span>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <span class="panel-title"><i></i>师生性别结构</span>
            <span class="panel-note">点击环形查看明细</span>
          </div>
          <div class="panel-body gender">
            <div class="gender-item">
              <div class="gender-chart">
                <VChart
                  v-if="studentGenderOption"
                  :option="studentGenderOption"
                  autoresize
                  style="height:100%;width:100%"
                  @click="(e: any) => onChartClick('student_gender', e)"
                />
                <div v-else class="empty">暂无数据</div>
                <div class="gender-total"><b>{{ fmt(dashboard?.student_count ?? 0) }}</b><span>学生</span></div>
              </div>
            </div>
            <div class="gender-item">
              <div class="gender-chart">
                <VChart
                  v-if="teacherGenderOption"
                  :option="teacherGenderOption"
                  autoresize
                  style="height:100%;width:100%"
                  @click="(e: any) => onChartClick('teacher_gender', e)"
                />
                <div v-else class="empty">暂无数据</div>
                <div class="gender-total"><b>{{ fmt(dashboard?.teacher_count ?? 0) }}</b><span>教师</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏 -->
      <div class="col">
        <div class="panel">
          <div class="panel-head">
            <span class="panel-title"><i></i>智能体运行监测</span>
            <span class="panel-note">平均响应延迟</span>
          </div>
          <div class="panel-body agent">
            <div class="gauge">
              <VChart v-if="agentGaugeOption" :option="agentGaugeOption" autoresize style="height:100%;width:100%" />
              <div v-else class="empty">暂无数据</div>
              <span class="gauge-cap">平均响应延迟</span>
            </div>
            <div class="agent-metrics">
              <div class="agent-metric"><span>学生人均消息</span><b>{{ avgMsgPerStudent }}</b></div>
              <div class="agent-metric"><span>教师人均消息</span><b>{{ avgMsgPerTeacher }}</b></div>
              <div class="agent-metric"><span>知识库条目</span><b>{{ fmt(dashboard?.knowledge_count ?? 0) }}</b></div>
              <div class="agent-metric"><span>文档资料</span><b>{{ fmt(dashboard?.document_count ?? 0) }}</b></div>
            </div>
          </div>
        </div>

        <div class="panel panel-grow">
          <div class="panel-head">
            <span class="panel-title"><i></i>智能体能力雷达</span>
            <span class="panel-note">能力指数</span>
          </div>
          <div class="panel-body chart-body">
            <VChart v-if="agentRadarOption" :option="agentRadarOption" autoresize style="height:100%;width:100%" />
            <div v-else class="empty">暂无数据</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <span class="panel-title"><i></i>学院学生排行</span>
            <button type="button" class="panel-more" @click="router.push('/admin/students')">更多 »</button>
          </div>
          <div class="panel-body rank-body">
            <div v-if="rankList.length" class="rank">
              <div class="rank-list" :class="{ 'rank-anim': rankList.length > 4 && !reducedMotion }">
                <div v-for="(r, i) in rankRows" :key="i" class="rank-row">
                  <span class="rank-no" :class="'rk-' + (i % rankList.length)">{{ pad2((i % rankList.length) + 1) }}</span>
                  <span class="rank-name" :title="r.college">{{ r.college }}</span>
                  <span class="rank-track"><i :style="{ width: r.percent + '%' }"></i></span>
                  <span class="rank-val">{{ r.count }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty">暂无数据</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 页脚信息 ===== -->
    <footer class="footer">
      <div class="footer-item"><span class="footer-label">数据源</span><b>智慧校园 AI 智能体平台</b></div>
      <div class="footer-item"><span class="footer-label">学院覆盖</span><b>{{ dashboard?.college_count ?? 0 }} 个</b></div>
      <div class="footer-item"><span class="footer-label">刷新时间</span><b>{{ refreshAt || '加载中…' }}</b></div>
      <div class="footer-actions">
        <button type="button" class="action" @click="loadDashboard"><el-icon><Refresh /></el-icon>刷新数据</button>
        <button type="button" class="action" @click="router.push('/admin/knowledge')"><el-icon><Collection /></el-icon>知识库</button>
        <button type="button" class="action action-primary" @click="dataDialogVisible = true"><el-icon><Operation /></el-icon>数据导入 / 导出</button>
      </div>
    </footer>

    <!-- ===== 数据导入 / 导出 ===== -->
    <el-dialog v-model="dataDialogVisible" title="数据导入 / 导出" width="680px" :close-on-click-modal="false">
      <div class="data-dialog-content">
        <el-tabs v-model="dataDialogTab" type="border-card">
          <el-tab-pane label="数据导出" name="export">
            <div class="dialog-section">
              <p class="section-desc">导出用户数据为 Excel 文件</p>
              <div class="export-options">
                <el-button type="primary" :loading="exporting" class="hover-lift export-btn" @click="handleExport('student')">
                  <el-icon style="margin-right:6px"><User /></el-icon>
                  导出学生数据
                </el-button>
                <el-button type="success" :loading="exporting" class="hover-lift export-btn" @click="handleExport('teacher')">
                  <el-icon style="margin-right:6px"><UserFilled /></el-icon>
                  导出教师数据
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="数据导入" name="import">
            <div class="dialog-section">
              <p class="section-desc">从 Excel 文件导入用户数据（重复学号 / 工号将跳过）</p>
              <el-radio-group v-model="importRole" style="margin-bottom:16px">
                <el-radio-button value="student">导入学生</el-radio-button>
                <el-radio-button value="teacher">导入教师</el-radio-button>
              </el-radio-group>
              <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls">
                <el-button type="warning" :loading="importing" class="hover-lift">
                  <el-icon style="margin-right:6px"><Upload /></el-icon>
                  选择文件导入
                </el-button>
              </el-upload>
              <div v-if="importResult" class="import-result">
                <el-alert
                  :title="`导入完成：新增 ${importResult.created} 条，跳过 ${importResult.skipped} 条`"
                  :type="importResult.errors.length > 0 ? 'warning' : 'success'"
                  show-icon
                  :closable="false"
                />
                <div v-if="importResult.errors.length > 0" class="error-list">
                  <p>错误信息：</p>
                  <ul>
                    <li v-for="(err, i) in importResult.errors" :key="i">{{ err }}</li>
                  </ul>
                </div>
              </div>
              <el-collapse style="margin-top:12px">
                <el-collapse-item title="导入模板格式说明" name="1">
                  <h4>学生：</h4>
                  <p>学号 | 姓名 | 学院 | 班级 | 性别 | 年龄 | 联系电话 | 籍贯</p>
                  <h4>教师：</h4>
                  <p>工号 | 姓名 | 学院 | 性别 | 年龄 | 职称 | 所属单位 | 联系电话</p>
                  <p style="color:#999;font-size:12px">第一行为表头，重复学号 / 工号自动跳过，默认密码 123456</p>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- ===== 图表明细弹窗 ===== -->
    <el-dialog v-model="detailVisible" :title="detailTitle" width="680px">
      <el-table :data="detailData" size="small" max-height="380">
        <el-table-column :prop="detailNameKey" :label="detailNameLabel" />
        <el-table-column prop="value" :label="detailValueLabel" width="120" align="center" sortable />
        <el-table-column label="占比" width="150" align="center">
          <template #default="{ row }">
            <el-progress :percentage="detailPercent(row.value)" :stroke-width="8" :color="detailProgressColor" />
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { getDashboardStats, exportData, importData, type DashboardStats, type ImportResult } from '@/api/admin'
import { getFeeds, type FeedItem } from '@/api/resources'
import {
  User, UserFilled, Document, School, ChatDotRound,
  Files, Timer, Monitor, Collection, Operation, Upload, Refresh
} from '@element-plus/icons-vue'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, GaugeChart, RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer, PieChart, BarChart, GaugeChart, RadarChart,
  TooltipComponent, LegendComponent, GridComponent,
])

const router = useRouter()

const dashboard = ref<DashboardStats | null>(null)
const refreshAt = ref('')
const reducedMotion = typeof window !== 'undefined'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/* ===== 工具函数 ===== */
function fmt(v: number | null | undefined) {
  return (v ?? 0).toLocaleString('zh-CN')
}
function pad2(n: number) {
  return String(n).padStart(2, '0')
}
function hexA(hex: string, alpha: number) {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map(c => c + c).join('') : h
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

/* ===== 危机等级 ===== */
const CRISIS_META: { key: string; label: string; color: string }[] = [
  { key: 'severe', label: '严重', color: '#f56c6c' },
  { key: 'moderate', label: '中等', color: '#e6a23c' },
  { key: 'mild', label: '轻微', color: '#409eff' },
  { key: 'none', label: '正常', color: '#67c23a' },
]
const CRISIS_LABELS: Record<string, string> = {
  severe: '严重', moderate: '中等', mild: '轻微', none: '无',
}

const crisisRows = computed(() => {
  const stats = dashboard.value?.crisis_stats ?? []
  const map: Record<string, number> = {}
  for (const s of stats) map[s.level] = s.count
  const total = stats.reduce((sum, s) => sum + s.count, 0) || 1
  return CRISIS_META.map(m => {
    const count = map[m.key] ?? 0
    return { ...m, count, percent: Math.round((count / total) * 100) }
  })
})
const crisisFocus = computed(() =>
  (dashboard.value?.crisis_stats ?? [])
    .filter(s => s.level === 'severe' || s.level === 'moderate')
    .reduce((sum, s) => sum + s.count, 0)
)
const crisisTracked = computed(() =>
  (dashboard.value?.crisis_stats ?? []).reduce((sum, s) => sum + s.count, 0)
)

/* ===== 核心指标 ===== */
const kpiCards = computed(() => {
  const d = dashboard.value
  return [
    { label: '学生总数', value: d?.student_count ?? 0, unit: '人', tag: '在册学籍', icon: UserFilled, color: '#409eff', to: '/admin/students' },
    { label: '教师总数', value: d?.teacher_count ?? 0, unit: '人', tag: '在职教职工', icon: User, color: '#67c23a', to: '/admin/teachers' },
    { label: '学院总数', value: d?.college_count ?? 0, unit: '个', tag: '组织架构', icon: School, color: '#e6a23c', to: '/admin/organizations' },
    { label: '知识库条目', value: d?.knowledge_count ?? 0, unit: '条', tag: '问答语料', icon: Document, color: '#764ba2', to: '/admin/knowledge' },
    { label: '文档资料', value: d?.document_count ?? 0, unit: '份', tag: '向量索引', icon: Files, color: '#17becf', to: '/admin/knowledge' },
    { label: 'AI 会话数', value: d?.conversation_count ?? 0, unit: '次', tag: '累计交互', icon: ChatDotRound, color: '#667eea', to: '' },
    { label: '消息总量', value: d?.message_count ?? 0, unit: '条', tag: '师生提问', icon: Monitor, color: '#f78989', to: '' },
    { label: '危机关注', value: crisisFocus.value, unit: '人', tag: '需重点跟进', icon: Timer, color: '#f56c6c', to: '/admin/crisis' },
  ]
})

/* ===== 人均消息 ===== */
const avgMsgPerStudent = computed(() => {
  const d = dashboard.value
  if (!d || !d.student_count) return '0.0'
  return (d.message_count / d.student_count).toFixed(1)
})
const avgMsgPerTeacher = computed(() => {
  const d = dashboard.value
  if (!d || !d.teacher_count) return '0.0'
  return (d.message_count / d.teacher_count).toFixed(1)
})

/* ===== 图表通用 ===== */
const GENDER_COLORS: Record<string, string> = { 男: '#409eff', 女: '#f78989', 未知: '#c0c4cc' }
const TOOLTIP = {
  backgroundColor: 'rgba(255,255,255,0.98)',
  borderColor: '#e4e8f0',
  borderWidth: 1,
  textStyle: { color: '#1f2d3d', fontSize: 12 },
  extraCssText: 'box-shadow:0 6px 20px rgba(15,23,42,.12);border-radius:8px;',
}

function makePieOption(data: Record<string, number>, colorMap: Record<string, string>) {
  const entries = Object.entries(data)
  if (!entries.length) return null
  return {
    tooltip: {
      trigger: 'item' as const,
      ...TOOLTIP,
      formatter: (p: any) => `${p.name}: <b>${p.value}</b> (${p.percent}%)`,
    },
    legend: {
      orient: 'horizontal' as const,
      bottom: 0,
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 14,
      icon: 'circle',
      textStyle: { color: '#8a94a6', fontSize: 11 },
    },
    series: [{
      type: 'pie' as const,
      radius: ['54%', '74%'],
      center: ['50%', '43%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      emphasis: { scaleSize: 6 },
      data: entries.map(([name, value]) => ({
        name,
        value,
        itemStyle: { color: colorMap[name] || '#c0c4cc' },
      })),
    }],
  }
}

const studentGenderOption = computed(() => {
  const stats = dashboard.value?.student_gender_stats
  return stats ? makePieOption(stats, GENDER_COLORS) : null
})
const teacherGenderOption = computed(() => {
  const stats = dashboard.value?.teacher_gender_stats
  return stats ? makePieOption(stats, GENDER_COLORS) : null
})

/* ===== 各学院学生分布 ===== */
const collegeBarOption = computed(() => {
  const data = dashboard.value?.college_stats
  if (!data?.length) return null
  const sorted = [...data].sort((a, b) => b.count - a.count).slice(0, 8)
  const max = Math.max(...sorted.map(s => s.count), 1)
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const, shadowStyle: { color: 'rgba(102,126,234,0.06)' } },
      ...TOOLTIP,
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `${p.name}: <b>${p.value}</b> 人`
      },
    },
    grid: { left: 2, right: 42, top: 6, bottom: 2, containLabel: true },
    xAxis: { type: 'value' as const, max: Math.ceil(max * 1.2), show: false },
    yAxis: {
      type: 'category' as const,
      inverse: true,
      data: sorted.map(s => s.college),
      axisLabel: { color: '#8a94a6', fontSize: 11, width: 92, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [{
      type: 'bar' as const,
      data: sorted.map(s => s.count),
      barWidth: 9,
      showBackground: true,
      backgroundStyle: { color: '#f4f6fa', borderRadius: 5 },
      itemStyle: {
        borderRadius: 5,
        color: {
          type: 'linear' as const, x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' },
          ],
        },
      },
      label: { show: true, position: 'right' as const, color: '#764ba2', fontSize: 11, fontWeight: 'bold' as const },
    }],
  }
})

/* ===== 平均响应延迟仪表盘 ===== */
const agentGaugeOption = computed(() => {
  const d = dashboard.value
  if (!d) return null
  const v = Number(d.avg_response_time ?? 0)
  const max = Math.max(2, Math.ceil(v * 2))
  return {
    series: [{
      type: 'gauge' as const,
      startAngle: 205,
      endAngle: -25,
      min: 0,
      max,
      radius: '96%',
      center: ['50%', '62%'],
      progress: {
        show: true,
        width: 11,
        roundCap: true,
        itemStyle: {
          color: {
            type: 'linear' as const, x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' },
            ],
          },
        },
      },
      axisLine: { roundCap: true, lineStyle: { width: 11, color: [[1, '#eef1f6']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      anchor: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '-2%'],
        formatter: (val: number) => `{v|${val.toFixed(1)}}{u|s}`,
        rich: {
          v: { fontSize: 30, fontWeight: 'bold', color: '#1f2d3d' },
          u: { fontSize: 13, color: '#8a94a6', padding: [0, 0, 0, 3] },
        },
      },
      data: [{ value: v }],
    }],
  }
})

/* ===== 智能体能力雷达 ===== */
const agentRadarOption = computed(() => {
  const d = dashboard.value
  if (!d) return null
  const raw = [
    { name: '会话规模', value: d.conversation_count ?? 0 },
    { name: '消息体量', value: d.message_count ?? 0 },
    { name: '知识储备', value: d.knowledge_count ?? 0 },
    { name: '文档资源', value: d.document_count ?? 0 },
    { name: '学生覆盖', value: d.student_count ?? 0 },
    { name: '师资覆盖', value: d.teacher_count ?? 0 },
  ]
  const max = Math.max(...raw.map(r => r.value), 1)
  return {
    tooltip: {
      ...TOOLTIP,
      formatter: (p: any) => `${p.name}<br/>${raw.map((r, i) => `${r.name}: <b>${p.value[i]}</b>`).join('<br/>')}`,
    },
    radar: {
      indicator: raw.map(r => ({ name: r.name, max: Math.ceil(max * 1.15) })),
      center: ['50%', '50%'],
      radius: '64%',
      axisName: { color: '#8a94a6', fontSize: 11 },
      splitLine: { lineStyle: { color: '#eef1f6' } },
      splitArea: { areaStyle: { color: ['rgba(102,126,234,0.03)', 'rgba(102,126,234,0.01)'] } },
      axisLine: { lineStyle: { color: '#e4e8f0' } },
    },
    series: [{
      type: 'radar' as const,
      symbolSize: 4,
      lineStyle: { color: '#667eea', width: 2 },
      itemStyle: { color: '#667eea' },
      areaStyle: { color: 'rgba(102,126,234,0.2)' },
      data: [{ value: raw.map(r => r.value), name: '能力指数' }],
    }],
  }
})

/* ===== 学院学生排行 ===== */
const rankList = computed(() => {
  const data = dashboard.value?.college_stats
  if (!data?.length) return []
  const sorted = [...data].sort((a, b) => b.count - a.count).slice(0, 8)
  const max = Math.max(...sorted.map(s => s.count), 1)
  return sorted.map(s => ({
    college: s.college,
    count: s.count,
    percent: Math.max(6, Math.round((s.count / max) * 100)),
  }))
})
const rankRows = computed(() =>
  rankList.value.length > 4 ? [...rankList.value, ...rankList.value] : rankList.value
)

/* ===== 每日资讯速览 ===== */
const FEED_TYPE_META: Record<string, { label: string; color: string }> = {
  papers: { label: '论文', color: '#667eea' },
  agents: { label: '智能体', color: '#764ba2' },
  opensource: { label: '开源', color: '#17becf' },
  news: { label: '要闻', color: '#409eff' },
  ai_news: { label: 'AI 行业', color: '#e6a23c' },
  rankings: { label: '榜单', color: '#f78989' },
  cn_ai: { label: '国产模型', color: '#67c23a' },
}
const feedList = ref<FeedItem[]>([])
const feedRows = computed(() =>
  feedList.value.length > 4 ? [...feedList.value, ...feedList.value] : feedList.value
)
function feedTypeLabel(t: string) {
  return FEED_TYPE_META[t]?.label ?? '资讯'
}
function feedBadgeStyle(f: FeedItem) {
  const c = FEED_TYPE_META[f.source_type]?.color ?? '#8a94a6'
  return { color: c, background: hexA(c, 0.1), borderColor: hexA(c, 0.28) }
}
function feedTime(f: FeedItem) {
  if (!f.published_at) return ''
  const d = new Date(f.published_at)
  if (Number.isNaN(d.getTime())) return ''
  const diff = Date.now() - d.getTime()
  const day = 24 * 3600 * 1000
  if (diff >= 0 && diff < day) {
    return d.toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' })
  }
  return `${d.getMonth() + 1}/${d.getDate()}`
}
function openFeedLink(f: FeedItem) {
  if (!f.link) return
  window.open(f.link, '_blank', 'noopener,noreferrer')
}
async function loadFeeds() {
  try {
    const rows = await getFeeds({ source_type: 'all', limit: 30 })
    feedList.value = rows
  } catch {
    /* 资讯加载失败不影响首页其余模块 */
  }
}

/* ===== 明细弹窗 ===== */
const detailVisible = ref(false)
const detailTitle = ref('')
const detailNameLabel = ref('名称')
const detailNameKey = ref('name')
const detailValueLabel = ref('数量')
const detailData = ref<{ name: string; value: number }[]>([])
const detailProgressColor = ref('#409eff')

function detailPercent(v: number) {
  const total = detailData.value.reduce((s, d) => s + d.value, 0)
  return total > 0 ? Math.round((v / total) * 100) : 0
}

function openCrisisDetail(level: string) {
  const d = dashboard.value
  if (!d) return
  detailTitle.value = `危机等级明细 · ${CRISIS_LABELS[level] ?? level}`
  detailNameLabel.value = '等级'
  detailValueLabel.value = '人数'
  detailProgressColor.value = CRISIS_META.find(m => m.key === level)?.color ?? '#409eff'
  detailData.value = (d.crisis_stats ?? []).map(s => ({
    name: CRISIS_LABELS[s.level] ?? s.level,
    value: s.count,
  }))
  detailVisible.value = true
}

function onChartClick(chartType: string, event: any) {
  const d = dashboard.value
  if (!d) return

  if (chartType === 'college') {
    router.push('/admin/students')
    return
  }
  if (!event?.name) return

  if (chartType === 'student_gender') {
    detailTitle.value = `学生性别明细 · ${event.name}`
    detailNameLabel.value = '性别'
    detailValueLabel.value = '人数'
    detailProgressColor.value = '#409eff'
    detailData.value = Object.entries(d.student_gender_stats ?? {}).map(([k, v]) => ({ name: k, value: v }))
    detailVisible.value = true
  } else if (chartType === 'teacher_gender') {
    detailTitle.value = `教师性别明细 · ${event.name}`
    detailNameLabel.value = '性别'
    detailValueLabel.value = '人数'
    detailProgressColor.value = '#f78989'
    detailData.value = Object.entries(d.teacher_gender_stats ?? {}).map(([k, v]) => ({ name: k, value: v }))
    detailVisible.value = true
  }
}

/* ===== 导入 / 导出 ===== */
const exporting = ref(false)
const importing = ref(false)
const importRole = ref<'student' | 'teacher'>('student')
const importResult = ref<ImportResult | null>(null)
const dataDialogVisible = ref(false)
const dataDialogTab = ref('export')

async function handleExport(role: 'student' | 'teacher') {
  exporting.value = true
  try {
    const data = await exportData(role)
    let blob: Blob
    if (data instanceof Blob) {
      blob = data
    } else if (data instanceof ArrayBuffer) {
      blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    } else {
      const text = typeof data === 'string' ? data : JSON.stringify(data) ?? ''
      if (text.includes('detail') || text.includes('error')) throw new Error(text)
      blob = new Blob([text], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    }
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = role === 'student' ? '学生数据.xlsx' : '教师数据.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleImport(file: File) {
  importing.value = true
  importResult.value = null
  try {
    importResult.value = await importData(importRole.value, file)
    ElMessage.success('导入完成')
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
  return false
}

/* ===== 数据加载 ===== */
async function loadDashboard() {
  try {
    dashboard.value = await getDashboardStats()
    refreshAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    ElMessage.error('数据加载失败')
  }
  loadFeeds()
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
/* ===== 页面容器：留白由 AdminLayout 统一提供，这里不再自绘背景 ===== */
.admin-home {
  min-height: 100%;
}

/* ===== 核心指标 ===== */
.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.kpi {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.kpi-link { cursor: pointer; }
.kpi-link:hover,
.kpi-link:focus-visible {
  transform: translateY(-2px);
  border-color: #d6e4ff;
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.14);
  outline: none;
}
.kpi-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kpi-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}
.kpi-label { font-size: 12px; color: #8a94a6; }
.kpi-value-row { display: flex; align-items: baseline; gap: 3px; }
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.kpi-unit { font-size: 11px; color: #b0b8c4; }
.kpi-tag {
  font-size: 11px;
  color: #b0b8c4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 主区三栏 ===== */
.main {
  display: grid;
  grid-template-columns: 1fr 1.42fr 1fr;
  gap: 12px;
  align-items: stretch;
  min-height: 640px;
}
.col { display: flex; flex-direction: column; gap: 12px; min-width: 0; }

.panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.panel-grow { flex: 1; min-height: 0; }
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 16px 10px;
  border-bottom: 1px solid #f1f3f7;
  flex-shrink: 0;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
}
.panel-title i {
  width: 3px;
  height: 13px;
  border-radius: 2px;
  background: linear-gradient(180deg, #667eea, #764ba2);
}
.panel-note { font-size: 11.5px; color: #b0b8c4; white-space: nowrap; }
.panel-more {
  font-size: 12px;
  color: #667eea;
  background: none;
  border: none;
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease;
}
.panel-more:hover,
.panel-more:focus-visible { color: #764ba2; background: #f0f5ff; outline: none; }
.panel-body { padding: 12px 16px 16px; flex: 1; min-height: 0; }
.chart-body { display: flex; padding: 10px 12px 12px; }
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #b0b8c4;
}

/* ===== 危机监测 ===== */
.crisis { display: flex; flex-direction: column; gap: 10px; }
.crisis-row {
  display: grid;
  grid-template-columns: 8px 40px 1fr 46px;
  align-items: center;
  gap: 9px;
  padding: 3px 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.crisis-row:hover,
.crisis-row:focus-visible { background: #f7f9fc; outline: none; }
.crisis-dot { width: 8px; height: 8px; border-radius: 50%; }
.crisis-name { font-size: 12.5px; color: #4b5563; }
.crisis-track { height: 8px; border-radius: 4px; overflow: hidden; background: #f4f6fa; }
.crisis-fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 0.7s cubic-bezier(0.33, 1, 0.68, 1);
}
.crisis-count {
  font-size: 14px;
  font-weight: 700;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.crisis-foot {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px dashed #e8ecf3;
  font-size: 12px;
  color: #8a94a6;
}
.crisis-foot b { color: #f56c6c; font-size: 13px; }

/* ===== 校园场景 ===== */
.panel-scene { min-height: 330px; }
.scene {
  position: relative;
  padding: 0;
  overflow: hidden;
  border-radius: 0 0 11px 11px;
}
.scene-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.scene-veil {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 62% 58% at 50% 46%, transparent 0%, rgba(15, 23, 42, 0.35) 78%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.42) 0%, transparent 30%, transparent 60%, rgba(15, 23, 42, 0.72) 100%);
}
.corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  pointer-events: none;
}
.corner.tl { top: 10px; left: 10px; border-right: none; border-bottom: none; border-radius: 3px 0 0 0; }
.corner.tr { top: 10px; right: 10px; border-left: none; border-bottom: none; border-radius: 0 3px 0 0; }
.corner.bl { bottom: 10px; left: 10px; border-right: none; border-top: none; border-radius: 0 0 0 3px; }
.corner.br { bottom: 10px; right: 10px; border-left: none; border-top: none; border-radius: 0 0 3px 0; }
.scene-tag {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(4px);
  font-size: 11px;
  color: #dbe7f5;
}
.scene-tag i { width: 6px; height: 6px; border-radius: 50%; background: #7dd3fc; }
.scene-tag b { font-weight: 500; }
.scene-tag em {
  font-style: normal;
  font-weight: 700;
  font-size: 14px;
  color: #fff;
  font-variant-numeric: tabular-nums;
}
.scene-tag.t1 { left: 5%; top: 15%; }
.scene-tag.t2 { right: 5%; top: 26%; }
.scene-tag.t3 { left: 9%; bottom: 30%; }
.scene-tag.t4 { right: 8%; bottom: 22%; }
.scene-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  gap: 30px;
  padding: 10px 14px;
  background: linear-gradient(180deg, transparent, rgba(15, 23, 42, 0.82));
  font-size: 11.5px;
  color: #cbd8e6;
}
.scene-bar b { color: #7dd3fc; font-size: 13px; margin-left: 4px; font-variant-numeric: tabular-nums; }

/* ===== 性别环形 ===== */
.gender { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.gender-item { position: relative; min-width: 0; }
.gender-chart { position: relative; height: 178px; }
.gender-total {
  position: absolute;
  left: 0;
  right: 0;
  top: 43%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}
.gender-total b { font-size: 18px; font-weight: 700; color: #1f2d3d; font-variant-numeric: tabular-nums; }
.gender-total span { font-size: 10.5px; color: #b0b8c4; }

/* ===== 智能体监测 ===== */
.agent { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: center; }
.gauge { position: relative; height: 150px; }
.gauge-cap {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 2px;
  text-align: center;
  font-size: 11px;
  color: #b0b8c4;
}
.agent-metrics { display: flex; flex-direction: column; gap: 7px; }
.agent-metric {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #f7f9fc;
  border-left: 2px solid #c7d2fe;
  font-size: 12px;
  color: #6b7688;
}
.agent-metric b {
  font-size: 15px;
  font-weight: 700;
  color: #1f2d3d;
  font-variant-numeric: tabular-nums;
}

/* ===== 学院排行 ===== */
.rank-body { padding: 8px 12px; overflow: hidden; }
.rank { height: 138px; overflow: hidden; }
.rank-list { display: flex; flex-direction: column; }
.rank-anim {
  animation-name: rank-scroll;
  animation-duration: 16s;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
@keyframes rank-scroll {
  0%, 12% { transform: translateY(0); }
  50%, 62% { transform: translateY(-50%); }
  100% { transform: translateY(0); }
}
.rank-row {
  display: grid;
  grid-template-columns: 26px 1fr 74px 34px;
  align-items: center;
  gap: 8px;
  height: 34.5px;
  font-size: 12px;
}
.rank-no {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  font-weight: 700;
  background: #f0f3f8;
  color: #8a94a6;
}
.rank-no.rk-0 { background: linear-gradient(135deg, #f6c453, #e6a23c); color: #fff; }
.rank-no.rk-1 { background: linear-gradient(135deg, #cbd5e1, #94a3b8); color: #fff; }
.rank-no.rk-2 { background: linear-gradient(135deg, #e8a87c, #c98a5e); color: #fff; }
.rank-name {
  color: #4b5563;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-track { height: 6px; border-radius: 3px; background: #f4f6fa; overflow: hidden; }
.rank-track i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #667eea, #764ba2);
}
.rank-val { text-align: right; color: #1f2d3d; font-weight: 700; font-variant-numeric: tabular-nums; }

/* ===== 每日资讯速览 ===== */
.feed-body { padding: 8px 12px; overflow: hidden; }
.feed { height: 138px; overflow: hidden; }
.feed-list { display: flex; flex-direction: column; }
.feed-anim {
  animation-name: rank-scroll;
  animation-duration: 45s;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}
.feed-row {
  display: grid;
  grid-template-columns: 54px 1fr 40px;
  align-items: center;
  gap: 8px;
  height: 34.5px;
  font-size: 12px;
  padding: 0 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.feed-row:hover,
.feed-row:focus-visible { background: #f7f9fc; outline: none; }
.feed-badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid;
  font-size: 10.5px;
  line-height: 16px;
  text-align: center;
  white-space: nowrap;
}
.feed-title {
  color: #4b5563;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.feed-row:hover .feed-title { color: #667eea; }
.feed-time {
  text-align: right;
  font-size: 10.5px;
  color: #b0b8c4;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ===== 页脚 ===== */
.footer {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.footer-item { display: flex; align-items: center; gap: 7px; font-size: 12px; }
.footer-label { color: #8a94a6; }
.footer-item b { color: #1f2d3d; font-weight: 600; }
.footer-actions { display: flex; gap: 9px; margin-left: auto; }
.action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  color: #4b5563;
  background: #f4f6fa;
  border: 1px solid #e8ecf3;
  transition: all 0.18s ease;
}
.action:hover,
.action:focus-visible { color: #1f2d3d; border-color: #d6e4ff; background: #eef4ff; outline: none; }
.action-primary {
  color: #fff;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-color: transparent;
}
.action-primary:hover,
.action-primary:focus-visible {
  color: #fff;
  background: linear-gradient(135deg, #7b90ef, #8a5fb2);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.35);
}

/* ===== 弹窗内样式 ===== */
.dialog-section { padding: 4px 0; }
.section-desc { margin: 0 0 14px; font-size: 13px; color: #606266; }
.export-options { display: flex; gap: 12px; }
.export-btn { flex: 1; }
.import-result { margin-top: 14px; }
.error-list { margin-top: 10px; font-size: 12px; color: #f56c6c; }
.error-list p { margin: 0 0 6px; }
.error-list ul { margin: 0; padding-left: 18px; }
.hover-lift { transition: transform 0.18s ease, box-shadow 0.18s ease; }
.hover-lift:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16); }

/* ===== 响应式 ===== */
@media (max-width: 1280px) {
  .main { grid-template-columns: 1fr 1fr; min-height: 0; }
  .col:last-child {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .main { grid-template-columns: 1fr; }
  .col:last-child { display: flex; }
  .panel-scene { min-height: 0; }
  .scene { min-height: 260px; }
}

@media (max-width: 768px) {
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi-value { font-size: 20px; }
  .agent, .gender { grid-template-columns: 1fr; }
  .footer { gap: 14px; }
  .footer-actions { margin-left: 0; width: 100%; }
  .action { flex: 1; justify-content: center; }
}

@media (max-width: 480px) {
  .kpis { grid-template-columns: 1fr; }
  .scene-bar { gap: 14px; font-size: 10.5px; flex-wrap: wrap; }
  .scene-tag { font-size: 10px; padding: 4px 8px; }
}

@media (prefers-reduced-motion: reduce) {
  .rank-anim, .feed-anim { animation: none !important; }
}
</style>
