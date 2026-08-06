<template>
  <div class="grade-analysis-page">
    <div class="page-header">
      <h2 class="text-gradient">成绩分析</h2>
      <p class="subtitle">详细的成绩统计与趋势分析</p>
    </div>

    <div v-loading="loading">
      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon" style="background: #e8f4fd; color: #409eff">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ analysis.stats.total_courses }}</div>
            <div class="stat-label">课程总数</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: #f0f9eb; color: #67c23a">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ analysis.stats.avg_gpa }}</div>
            <div class="stat-label">平均GPA</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: #fdf6ec; color: #e6a23c">
            <el-icon :size="24"><Star /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ analysis.stats.highest_gpa }}</div>
            <div class="stat-label">最高GPA</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: #fef0f0; color: #f56c6c">
            <el-icon :size="24"><Aim /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ analysis.stats.pass_rate }}%</div>
            <div class="stat-label">及格率</div>
          </div>
        </div>
      </div>

      <!-- 图表行 -->
      <div class="charts-row">
        <!-- 学期GPA趋势 -->
        <div class="chart-card">
          <div class="chart-title">学期GPA趋势</div>
          <v-chart :option="semesterGpaOption" class="chart" autoresize />
        </div>

        <!-- 成绩分布 -->
        <div class="chart-card">
          <div class="chart-title">成绩分布</div>
          <v-chart :option="distributionOption" class="chart" autoresize />
        </div>
      </div>

      <div class="charts-row">
        <!-- 课程类型统计 -->
        <div class="chart-card">
          <div class="chart-title">课程类型统计</div>
          <v-chart :option="courseTypeOption" class="chart" autoresize />
        </div>

        <!-- GPA分布饼图 -->
        <div class="chart-card">
          <div class="chart-title">GPA分布</div>
          <v-chart :option="gpaPieOption" class="chart" autoresize />
        </div>
      </div>

      <!-- 课程列表 -->
      <div class="course-lists">
        <!-- 优秀课程 -->
        <div class="course-section">
          <div class="section-title">
            <el-icon><Trophy /></el-icon> 优秀课程（GPA ≥ 3.5）
          </div>
          <div class="course-grid">
            <div v-for="course in analysis.top_courses" :key="course.course_name" class="course-item good">
              <div class="course-name">{{ course.course_name }}</div>
              <div class="course-score">
                <span class="score">{{ course.score }}分</span>
                <span class="gpa">GPA {{ course.gpa }}</span>
              </div>
              <div class="course-semester">{{ course.semester }}</div>
            </div>
          </div>
        </div>

        <!-- 薄弱课程 -->
        <div class="course-section">
          <div class="section-title">
            <el-icon><Warning /></el-icon> 薄弱课程（GPA < 2.5）
          </div>
          <div class="course-grid">
            <div v-for="course in analysis.weak_courses" :key="course.course_name" class="course-item weak">
              <div class="course-name">{{ course.course_name }}</div>
              <div class="course-score">
                <span class="score">{{ course.score }}分</span>
                <span class="gpa">GPA {{ course.gpa }}</span>
              </div>
              <div class="course-semester">{{ course.semester }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Document, TrendCharts, Star, Aim, Trophy, Warning } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { getGradeAnalysis, type GradeAnalysis } from '@/api/gradeAnalysis'
import { useAuthStore } from '@/stores/auth'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const auth = useAuthStore()
const loading = ref(false)

const analysis = ref<GradeAnalysis>({
  stats: {
    total_courses: 0,
    total_credits: 0,
    avg_score: 0,
    avg_gpa: 0,
    highest_gpa: 0,
    lowest_gpa: 0,
    pass_rate: 0
  },
  semester_gpa: [],
  course_type_stats: [],
  score_distribution: [],
  top_courses: [],
  weak_courses: []
})

// 学期GPA趋势图配置
const semesterGpaOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: 'category',
    data: analysis.value.semester_gpa.map(s => s.semester),
    axisLabel: { color: '#666', fontSize: 11 }
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 4,
    axisLabel: { color: '#666' },
    splitLine: { lineStyle: { color: '#f0f0f0' } }
  },
  series: [{
    type: 'line',
    data: analysis.value.semester_gpa.map(s => s.gpa),
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    lineStyle: { color: '#409eff', width: 3 },
    itemStyle: { color: '#409eff' },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(64,158,255,0.3)' },
          { offset: 1, color: 'rgba(64,158,255,0.05)' }
        ]
      }
    },
    markLine: {
      data: [
        { yAxis: 3.5, label: { formatter: '优秀', color: '#67c23a' } },
        { yAxis: 2.5, label: { formatter: '警戒', color: '#f56c6c' } }
      ],
      lineStyle: { type: 'dashed' }
    }
  }]
}))

// 成绩分布图配置
const distributionOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: 'category',
    data: analysis.value.score_distribution.map(d => d.range),
    axisLabel: { color: '#666' }
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#666' },
    splitLine: { lineStyle: { color: '#f0f0f0' } }
  },
  series: [{
    type: 'bar',
    data: analysis.value.score_distribution.map(d => d.count),
    barWidth: '50%',
    itemStyle: {
      borderRadius: [6, 6, 0, 0],
      color: (params: any) => {
        const colors = ['#67c23a', '#409eff', '#e6a23c', '#f56c6c', '#909399']
        return colors[params.dataIndex] || '#409eff'
      }
    }
  }]
}))

// 课程类型统计图配置
const courseTypeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['平均分', '平均GPA'], bottom: 0 },
  grid: { left: 50, right: 50, top: 20, bottom: 40 },
  xAxis: {
    type: 'category',
    data: analysis.value.course_type_stats.map(s => s.type),
    axisLabel: { color: '#666' }
  },
  yAxis: [
    {
      type: 'value',
      name: '分数',
      min: 0,
      max: 100,
      axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    {
      type: 'value',
      name: 'GPA',
      min: 0,
      max: 4,
      axisLabel: { color: '#666' },
      splitLine: { show: false }
    }
  ],
  series: [
    {
      name: '平均分',
      type: 'bar',
      data: analysis.value.course_type_stats.map(s => s.avg_score),
      barWidth: '30%',
      itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] }
    },
    {
      name: '平均GPA',
      type: 'bar',
      yAxisIndex: 1,
      data: analysis.value.course_type_stats.map(s => s.avg_gpa),
      barWidth: '30%',
      itemStyle: { color: '#67c23a', borderRadius: [4, 4, 0, 0] }
    }
  ]
}))

// GPA分布饼图配置
const gpaPieOption = computed(() => {
  const distribution = [
    { name: '优秀(≥3.5)', value: 0 },
    { name: '良好(3.0-3.49)', value: 0 },
    { name: '中等(2.5-2.99)', value: 0 },
    { name: '及格(2.0-2.49)', value: 0 },
    { name: '不及格(<2.0)', value: 0 }
  ]
  
  analysis.value.semester_gpa.forEach(s => {
    if (s.gpa >= 3.5) distribution[0].value++
    else if (s.gpa >= 3.0) distribution[1].value++
    else if (s.gpa >= 2.5) distribution[2].value++
    else if (s.gpa >= 2.0) distribution[3].value++
    else distribution[4].value++
  })
  
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: 10, top: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' }
      },
      data: distribution.filter(d => d.value > 0),
      color: ['#67c23a', '#409eff', '#e6a23c', '#f56c6c', '#909399']
    }]
  }
})

async function loadAnalysis() {
  loading.value = true
  try {
    const data = await getGradeAnalysis(auth.user?.id || 0)
    analysis.value = data
  } catch (error) {
    console.error('加载成绩分析失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAnalysis()
})
</script>

<style scoped>
.grade-analysis-page {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.text-gradient {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.chart {
  width: 100%;
  height: 280px;
}

.course-lists {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.course-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.course-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 8px;
  background: #f8f9fa;
}

.course-item.good {
  border-left: 4px solid #67c23a;
}

.course-item.weak {
  border-left: 4px solid #f56c6c;
}

.course-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  flex: 1;
}

.course-score {
  display: flex;
  gap: 12px;
  align-items: center;
}

.score {
  font-size: 14px;
  color: #666;
}

.gpa {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
}

.course-semester {
  font-size: 12px;
  color: #999;
  margin-left: 12px;
}

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .grade-analysis-page { padding: 16px; padding-bottom: 80px; }
  .page-header h2 { font-size: 18px; }
  .stats-row { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .stat-card { padding: 14px 12px; gap: 10px; }
  .stat-icon { width: 36px; height: 36px; }
  .stat-value { font-size: 18px; }
  .charts-row { grid-template-columns: 1fr; gap: 14px; }
  .chart-card { padding: 14px; }
  .chart-title { font-size: 14px; margin-bottom: 10px; }
  .chart { height: 220px; }
  .course-lists { grid-template-columns: 1fr; gap: 14px; }
  .course-section { padding: 14px; }
  .section-title { font-size: 14px; margin-bottom: 12px; }
  .course-item { padding: 10px 12px; }
}
</style>
