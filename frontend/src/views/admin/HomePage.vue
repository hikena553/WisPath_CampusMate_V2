<template>
  <div class="admin-home">
    <!-- Welcome banner -->
    <div class="welcome-banner">
      <div class="welcome-text">
        <h1>管理员控制台</h1>
        <p>欢迎回来，<strong>{{ auth.userName }}</strong> · {{ dateStr }}</p>
      </div>
      <div class="welcome-badge">
        <el-tag size="large" effect="dark" color="#409eff">管理员</el-tag>
      </div>
    </div>

    <!-- Stats row -->
    <div class="stats-row">
      <div
        v-for="(stat, i) in statCards"
        :key="i"
        class="stat-card hover-lift"
        :style="{ '--accent': stat.color }"
      >
        <div class="stat-icon" :style="{ background: stat.bg, color: stat.color }">
          <el-icon :size="22"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </div>
    </div>

    <!-- Charts row 1: Student gender + Teacher gender + College distribution -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-header">
          <h4>全校学生性别比例</h4>
        </div>
        <VChart
          v-if="studentGenderOption"
          :option="studentGenderOption"
          autoresize
          style="height:220px"
          @click="(e: any) => onChartClick('student_gender', e)"
        />
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>
      <div class="chart-card">
        <div class="chart-header">
          <h4>全校教师性别比例</h4>
        </div>
        <VChart
          v-if="teacherGenderOption"
          :option="teacherGenderOption"
          autoresize
          style="height:220px"
          @click="(e: any) => onChartClick('teacher_gender', e)"
        />
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>
      <div class="chart-card chart-card-wide">
        <div class="chart-header">
          <h4>各学院学生分布</h4>
        </div>
        <VChart
          v-if="collegeBarOption"
          :option="collegeBarOption"
          autoresize
          style="height:220px"
          @click="(e: any) => onChartClick('college', e)"
        />
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>
    </div>

    <!-- Charts row 2: Crisis distribution + Teacher college distribution -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-header">
          <h4>危机等级分布</h4>
        </div>
        <VChart
          v-if="crisisPieOption"
          :option="crisisPieOption"
          autoresize
          style="height:220px"
          @click="(e: any) => onChartClick('crisis', e)"
        />
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>
      <div class="chart-card chart-card-wide" v-if="teacherCollegeBarOption">
        <div class="chart-header">
          <h4>各学院教师分布</h4>
        </div>
        <VChart
          :option="teacherCollegeBarOption"
          autoresize
          style="height:200px"
          @click="(e: any) => onChartClick('teacher_college', e)"
        />
      </div>
    </div>

    <!-- Charts row 3: Agent usage stats (charts) -->
    <div class="charts-row">
      <div class="chart-card chart-card-full">
        <div class="chart-header">
          <h4>智能体运行数据</h4>
        </div>
        <div class="agent-charts-container">
          <div class="agent-chart-section">
            <VChart
              v-if="agentOverviewOption"
              :option="agentOverviewOption"
              autoresize
              style="height:200px"
            />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
          <div class="agent-metrics-section">
            <div class="agent-metric-card">
              <div class="metric-icon primary">
                <el-icon :size="20"><ChatDotRound /></el-icon>
              </div>
              <div class="metric-content">
                <span class="metric-value">{{ avgMsgPerStudent }}</span>
                <span class="metric-label">学生人均消息</span>
              </div>
            </div>
            <div class="agent-metric-card">
              <div class="metric-icon success">
                <el-icon :size="20"><ChatDotRound /></el-icon>
              </div>
              <div class="metric-content">
                <span class="metric-value">{{ avgMsgPerTeacher }}</span>
                <span class="metric-label">教师人均消息</span>
              </div>
            </div>
            <div class="agent-metric-card">
              <div class="metric-icon warning">
                <el-icon :size="20"><Document /></el-icon>
              </div>
              <div class="metric-content">
                <span class="metric-value">{{ dashboard?.knowledge_count ?? 0 }}</span>
                <span class="metric-label">知识库条目</span>
              </div>
            </div>
            <div class="agent-metric-card">
              <div class="metric-icon info">
                <el-icon :size="20"><Files /></el-icon>
              </div>
              <div class="metric-content">
                <span class="metric-value">{{ dashboard?.document_count ?? 0 }}</span>
                <span class="metric-label">文档数</span>
              </div>
            </div>
            <div class="agent-metric-card delay-card">
              <div class="metric-icon danger">
                <el-icon :size="20"><Timer /></el-icon>
              </div>
              <div class="metric-content">
                <span class="metric-value">{{ dashboard?.avg_response_time ?? '0.0' }}s</span>
                <span class="metric-label">平均响应延迟</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick data management widget -->
    <div class="data-widget">
      <div class="data-widget-content">
        <div class="data-widget-icon">
          <el-icon :size="24"><DataAnalysis /></el-icon>
        </div>
        <div class="data-widget-info">
          <h4>数据管理</h4>
          <p>导入或导出学生、教师数据</p>
        </div>
        <el-button type="primary" @click="dataDialogVisible = true" class="hover-lift">
          <el-icon style="margin-right:6px"><Operation /></el-icon>
          数据导入/导出
        </el-button>
      </div>
    </div>

    <!-- Data import/export dialog -->
    <el-dialog v-model="dataDialogVisible" title="数据导入/导出" width="520px" :close-on-click-modal="false">
      <div class="data-dialog-content">
        <el-tabs v-model="dataDialogTab" type="border-card">
          <el-tab-pane label="数据导出" name="export">
            <div class="dialog-section">
              <p class="section-desc">导出用户数据为 Excel 文件</p>
              <div class="export-options">
                <el-button type="primary" @click="handleExport('student')" :loading="exporting" class="hover-lift export-btn">
                  <el-icon style="margin-right:6px"><User /></el-icon>
                  导出学生数据
                </el-button>
                <el-button type="success" @click="handleExport('teacher')" :loading="exporting" class="hover-lift export-btn">
                  <el-icon style="margin-right:6px"><UserFilled /></el-icon>
                  导出教师数据
                </el-button>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="数据导入" name="import">
            <div class="dialog-section">
              <p class="section-desc">从 Excel 文件导入用户数据（重复学号/工号将跳过）</p>
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
                  show-icon :closable="false"
                />
                <div v-if="importResult.errors.length > 0" class="error-list">
                  <p>错误信息：</p>
                  <ul><li v-for="(err, i) in importResult.errors" :key="i">{{ err }}</li></ul>
                </div>
              </div>
              <el-collapse style="margin-top:12px">
                <el-collapse-item title="导入模板格式说明" name="1">
                  <h4>学生：</h4>
                  <p>学号 | 姓名 | 学院 | 班级 | 性别 | 年龄 | 联系电话 | 籍贯</p>
                  <h4>教师：</h4>
                  <p>工号 | 姓名 | 学院 | 性别 | 年龄 | 职称 | 所属单位 | 联系电话</p>
                  <p style="color:#999;font-size:12px">第一行为表头，重复学号/工号自动跳过，默认密码 123456</p>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>


    <!-- Chart detail dialog -->
    <el-dialog v-model="detailVisible" :title="detailTitle" width="600px">
      <el-table :data="detailData" size="small" max-height="380">
        <el-table-column :prop="detailNameKey" :label="detailNameLabel" />
        <el-table-column prop="value" :label="detailValueLabel" width="120" align="center" sortable />
        <el-table-column label="占比" width="120" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="detailPercent(row.value)"
              :stroke-width="8"
              :color="detailProgressColor"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { getDashboardStats, exportData, importData, type DashboardStats, type ImportResult } from '@/api/admin'
import {
  User, UserFilled, Document, School, ChatDotRound,
  Files, Timer, DataAnalysis, Operation, Upload
} from '@element-plus/icons-vue'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent, GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, PieChart, BarChart, TooltipComponent, LegendComponent, GridComponent])

const auth = useAuthStore()
const router = useRouter()

const dateStr = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
})

const dashboard = ref<DashboardStats | null>(null)

const statCards = computed(() => {
  const d = dashboard.value
  return [
    { label: '教师总数', value: d?.teacher_count ?? 0, icon: User, color: '#409eff', bg: '#e8f4ff' },
    { label: '学生总数', value: d?.student_count ?? 0, icon: UserFilled, color: '#67c23a', bg: '#edf7ed' },
    { label: '学院总数', value: d?.college_count ?? 0, icon: School, color: '#e6a23c', bg: '#fef5e8' },
    { label: '知识库条目', value: d?.knowledge_count ?? 0, icon: Document, color: '#f56c6c', bg: '#fef0f0' },
    { label: '文档数', value: d?.document_count ?? 0, icon: Files, color: '#9b59b6', bg: '#f5f0fa' },
    { label: '总会话数', value: d?.conversation_count ?? 0, icon: ChatDotRound, color: '#17becf', bg: '#e8fafc' },
  ]
})

const avgMsgPerStudent = computed(() => {
  const d = dashboard.value
  if (!d || d.student_count === 0) return '0'
  return (d.message_count / d.student_count).toFixed(1)
})

const avgMsgPerTeacher = computed(() => {
  const d = dashboard.value
  if (!d || d.teacher_count === 0) return '0'
  return (d.message_count / d.teacher_count).toFixed(1)
})

const GENDER_COLORS: Record<string, string> = { '男': '#409eff', '女': '#f56c6c', '未知': '#c0c4cc' }
const CRISIS_COLORS: Record<string, string> = { severe: '#f56c6c', moderate: '#e6a23c', mild: '#909399', none: '#67c23a' }
const CRISIS_LABELS: Record<string, string> = { severe: '严重', moderate: '中等', mild: '轻微', none: '无' }

function makePieOption(data: Record<string, number>, colorMap: Record<string, string>, labelMap?: Record<string, string>) {
  const entries = Object.entries(data)
  if (entries.length === 0) return null
  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: (params: any) => {
        const label = labelMap?.[params.name] || params.name
        return `${label}: <b>${params.value}</b> (${params.percent}%)`
      },
    },
    legend: {
      orient: 'horizontal' as const,
      bottom: 5,
      textStyle: { color: '#999', fontSize: 12 },
    },
    series: [{
      type: 'pie' as const,
      radius: ['40%', '65%'],
      center: ['50%', '43%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
        scaleSize: 12,
      },
      data: entries.map(([name, value]) => ({
        name: labelMap?.[name] || name,
        value,
        itemStyle: { color: colorMap[name] || '#909399' },
      })),
    }],
  }
}

const studentGenderOption = computed(() => {
  if (!dashboard.value?.student_gender_stats) return null
  return makePieOption(dashboard.value.student_gender_stats, GENDER_COLORS)
})

const teacherGenderOption = computed(() => {
  if (!dashboard.value?.teacher_gender_stats) return null
  return makePieOption(dashboard.value.teacher_gender_stats, GENDER_COLORS)
})

const crisisPieOption = computed(() => {
  if (!dashboard.value?.crisis_stats?.length) return null
  const data: Record<string, number> = {}
  for (const item of dashboard.value.crisis_stats) {
    data[item.level] = item.count
  }
  return makePieOption(data, CRISIS_COLORS, CRISIS_LABELS)
})

const collegeBarOption = computed(() => {
  const data = dashboard.value?.college_stats
  if (!data?.length) return null
  const sorted = [...data].sort((a, b) => b.count - a.count)
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `${p.name}: <b>${p.value}</b> 人`
      },
    },
    grid: { left: '3%', right: '10%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: {
      type: 'value' as const,
      axisLabel: { color: '#999', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    yAxis: {
      type: 'category' as const,
      data: sorted.map(item => item.college),
      axisLabel: { color: '#666', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      inverse: true,
    },
    series: [{
      type: 'bar' as const,
      data: sorted.map((item, i) => ({
        value: item.count,
        itemStyle: {
          color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9b59b6', '#17becf', '#ff7f0e', '#8c564b'][i % 8],
          borderRadius: [0, 4, 4, 0],
        },
      })),
      label: { show: true, position: 'right' as const, color: '#666', fontSize: 11 },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.3)' },
      },
      barMaxWidth: 28,
    }],
  }
})

const teacherCollegeBarOption = computed(() => {
  const data = dashboard.value?.teacher_college_stats
  if (!data?.length) return null
  const sorted = [...data].sort((a, b) => b.count - a.count)
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `${p.name}: <b>${p.value}</b> 人`
      },
    },
    grid: { left: '3%', right: '10%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: {
      type: 'value' as const,
      axisLabel: { color: '#999', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    yAxis: {
      type: 'category' as const,
      data: sorted.map(item => item.college),
      axisLabel: { color: '#666', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      inverse: true,
    },
    series: [{
      type: 'bar' as const,
      data: sorted.map((item, i) => ({
        value: item.count,
        itemStyle: {
          color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9b59b6', '#17becf'][i % 6],
          borderRadius: [0, 4, 4, 0],
        },
      })),
      label: { show: true, position: 'right' as const, color: '#666', fontSize: 11 },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.3)' },
      },
      barMaxWidth: 28,
    }],
  }
})

const agentOverviewOption = computed(() => {
  const d = dashboard.value
  if (!d) return null

  const data = [
    { name: '总会话数', value: d.conversation_count ?? 0 },
    { name: '总消息数', value: d.message_count ?? 0 },
    { name: '知识库条目', value: d.knowledge_count ?? 0 },
    { name: '文档数', value: d.document_count ?? 0 },
  ]

  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `${p.name}: <b>${p.value}</b>`
      },
    },
    grid: { left: '3%', right: '8%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: data.map(item => item.name),
      axisLabel: { color: '#666', fontSize: 12 },
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { color: '#999', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f5f5f5' } },
    },
    series: [{
      type: 'bar' as const,
      data: data.map((item, i) => ({
        value: item.value,
        itemStyle: {
          color: ['#409eff', '#67c23a', '#e6a23c', '#9b59b6'][i % 4],
          borderRadius: [6, 6, 0, 0],
        },
      })),
      barWidth: '40%',
      label: { show: true, position: 'top' as const, color: '#666', fontSize: 12 },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' },
      },
    }],
  }
})

// ===== Chart click → detail dialog =====
const detailVisible = ref(false)
const detailTitle = ref('')
const detailNameLabel = ref('')
const detailNameKey = ref('name')
const detailValueLabel = ref('数量')
const detailData = ref<{ name: string; value: number }[]>([])
const detailProgressColor = ref('#409eff')

function detailPercent(v: number) {
  const total = detailData.value.reduce((s, d) => s + d.value, 0)
  return total > 0 ? Math.round((v / total) * 100) : 0
}

function onChartClick(chartType: string, event: any) {
  if (!event || !event.name) return

  const d = dashboard.value
  if (!d) return

  if (chartType === 'student_gender') {
    detailTitle.value = `学生性别 - ${event.name}`
    detailNameLabel.value = '性别'
    detailValueLabel.value = '人数'
    detailProgressColor.value = '#409eff'
    const stats = d.student_gender_stats || {}
    detailData.value = Object.entries(stats).map(([k, v]) => ({ name: k, value: v }))
    detailVisible.value = true
  } else if (chartType === 'teacher_gender') {
    detailTitle.value = `教师性别 - ${event.name}`
    detailNameLabel.value = '性别'
    detailValueLabel.value = '人数'
    detailProgressColor.value = '#67c23a'
    const stats = d.teacher_gender_stats || {}
    detailData.value = Object.entries(stats).map(([k, v]) => ({ name: k, value: v }))
    detailVisible.value = true
  } else if (chartType === 'college') {
    router.push('/admin/students')
  } else if (chartType === 'crisis') {
    detailTitle.value = `危机等级 - ${CRISIS_LABELS[event.name] || event.name}`
    detailNameLabel.value = '等级'
    detailValueLabel.value = '人数'
    detailProgressColor.value = '#f56c6c'
    const stats = d.crisis_stats || []
    detailData.value = stats.map(s => ({ name: CRISIS_LABELS[s.level] || s.level, value: s.count }))
    detailVisible.value = true
  } else if (chartType === 'teacher_college') {
    router.push('/admin/teachers')
  }
}

// ===== Export/Import =====
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
      const text = typeof data === 'string' ? data : JSON.stringify(data)
      if (text.includes('detail') || text.includes('error')) throw new Error(text)
      blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    }
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = role === 'student' ? '学生数据.xlsx' : '教师数据.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '导出失败'
    ElMessage.error(msg)
  } finally {
    exporting.value = false
  }
}

async function handleImport(file: File) {
  importing.value = true
  importResult.value = null
  try {
    const result = await importData(importRole.value, file)
    importResult.value = result
    ElMessage.success('导入完成')
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
  return false
}

onMounted(async () => {
  try {
    dashboard.value = await getDashboardStats()
  } catch {}
})
</script>

<style scoped>
.admin-home {
  padding: 16px 20px;
  overflow-y: auto;
  height: 100%;
}

/* ===== Welcome Banner ===== */
.welcome-banner {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #e8f4ff 0%, #f0f8ff 50%, #e8f4ff 100%);
  border-radius: 10px; padding: 14px 20px; margin-bottom: 14px;
  border: 1px solid rgba(64,158,255,0.1);
}
.welcome-text h1 {
  font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 0 0 3px;
}
.welcome-text p {
  font-size: 13px; color: #666; margin: 0;
}
.welcome-text p strong { color: #409eff; }

/* ===== Stats Row ===== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.stat-card {
  display: flex; align-items: center; gap: 10px;
  background: #fff; border-radius: 8px; padding: 10px 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
  cursor: default;
}

.stat-icon {
  width: 34px; height: 34px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  display: flex; flex-direction: column; flex: 1; min-width: 0;
}
.stat-value {
  font-size: 20px; font-weight: 700; color: #1a1a2e; line-height: 1.15;
}
.stat-label {
  font-size: 12px; color: #999; margin-top: 1px; white-space: nowrap;
}

.hover-lift {
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.hover-lift:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}

/* ===== Charts Row ===== */
.charts-row {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.chart-card {
  flex: 1;
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
  min-width: 0;
}

.chart-card-wide {
  flex: 2;
}

.chart-card-full {
  flex: none;
  width: 100%;
}

.chart-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.chart-header h4 {
  margin: 0; font-size: 14px; font-weight: 600; color: #333;
}

/* ===== Agent Stats ===== */
.agent-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.agent-stat-item {
  text-align: center;
  padding: 12px 8px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  transition: transform 0.2s ease;
}
.agent-stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

.agent-stat-label {
  display: block;
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
}

.agent-stat-value {
  font-size: 22px;
  font-weight: 700;
}
.agent-stat-value.primary { color: #409eff; }
.agent-stat-value.success { color: #67c23a; }
.agent-stat-value.warning { color: #e6a23c; }
.agent-stat-value.info { color: #9b59b6; }

.agent-extra {
  display: flex;
  gap: 10px;
}

.agent-metric {
  flex: 1;
  display: flex; flex-direction: column; align-items: center;
  padding: 8px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}
.agent-metric span {
  font-size: 11px; color: #999; margin-bottom: 3px;
}
.agent-metric strong {
  font-size: 16px; color: #333;
}

/* ===== Card common ===== */
.card-desc { color: #666; font-size: 12px; margin: 0 0 10px; }
.export-actions { display: flex; gap: 8px; }
.import-result { margin-top: 10px; }
.error-list { margin-top: 6px; font-size: 12px; color: #e6a23c; }
.error-list ul { margin: 3px 0 0 14px; padding: 0; }
.error-list h4 { font-size: 13px; color: #333; margin: 8px 0 6px; }
.error-list h4:first-child { margin-top: 0; }

/* ===== Responsive ===== */
@media (max-width: 1400px) {
  .stats-row {
    grid-template-columns: repeat(3, 1fr);
  }
  .charts-row {
    flex-wrap: wrap;
  }
  .chart-card-wide {
    flex: 1 1 100%;
  }
  .agent-charts-container {
    flex-direction: column;
  }
  .agent-metrics-section {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .agent-metric-card {
    flex: 1 1 calc(50% - 5px);
    min-width: 140px;
  }
}

/* ===== Agent Charts ===== */
.agent-charts-container {
  display: flex;
  gap: 14px;
}

.agent-chart-section {
  flex: 2;
  min-width: 0;
}

.agent-metrics-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.agent-metric-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s ease;
}

.agent-metric-card:hover {
  transform: translateX(3px);
  box-shadow: 0 3px 10px rgba(0,0,0,0.05);
}

.agent-metric-card.delay-card {
  background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
  border-color: #fee2e2;
}

.metric-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-icon.primary { background: #e8f4ff; color: #409eff; }
.metric-icon.success { background: #edf7ed; color: #67c23a; }
.metric-icon.warning { background: #fef5e8; color: #e6a23c; }
.metric-icon.info { background: #f5f0fa; color: #9b59b6; }
.metric-icon.danger { background: #fef0f0; color: #f56c6c; }

.metric-content {
  display: flex;
  flex-direction: column;
}

.metric-value {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.15;
}

.metric-label {
  font-size: 10px;
  color: #999;
  margin-top: 1px;
}

/* ===== Data Widget ===== */
.data-widget {
  margin-top: 14px;
  background: linear-gradient(135deg, #f0f9ff 0%, #fff 100%);
  border-radius: 10px;
  padding: 14px 18px;
  border: 1px solid rgba(64,158,255,0.15);
}

.data-widget-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.data-widget-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.data-widget-info {
  flex: 1;
}

.data-widget-info h4 {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}

.data-widget-info p {
  margin: 0;
  font-size: 12px;
  color: #666;
}

/* ===== Data Dialog ===== */
.data-dialog-content {
  min-height: 200px;
}

.dialog-section {
  padding: 4px 0;
}

.section-desc {
  color: #666;
  font-size: 12px;
  margin: 0 0 10px;
}

.export-options {
  display: flex;
  gap: 10px;
}

.export-btn {
  flex: 1;
  height: 36px;
  font-size: 12px;
}

@media (max-width: 768px) {
  .data-widget-content {
    flex-direction: column;
    text-align: center;
  }
  .export-options {
    flex-direction: column;
  }
  .agent-metric-card {
    flex: 1 1 100%;
  }
}
</style>
