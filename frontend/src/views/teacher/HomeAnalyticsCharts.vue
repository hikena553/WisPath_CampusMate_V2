<template>
  <div class="analytics-row">
    <!-- 左侧：雷达图 + 成绩分布 + 政治面貌 + 预警趋势 + 生源地 -->
    <div class="analytics-left">
      <!-- 第一行：雷达图 + 成绩分布 -->
      <div class="chart-row">
        <div class="chart-half">
          <div class="section-title" @click="emit('navigate', '/teacher/students')">
            <el-icon><DataAnalysis /></el-icon>
            <span>班级综合评估</span>
            <el-link type="primary" :underline="false" class="section-link">
              学生档案 <el-icon><DArrowRight /></el-icon>
            </el-link>
          </div>
          <div class="chart-container">
            <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
            <el-empty v-else description="暂无评估数据" :image-size="60" />
          </div>
        </div>
        <div class="chart-half">
          <div class="section-title">
            <el-icon><Histogram /></el-icon>
            <span>成绩分布</span>
          </div>
          <div class="chart-container">
            <VChart v-if="gradeBarOptions" :option="gradeBarOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
      </div>

      <!-- 第二行：政治面貌 + 预警趋势 -->
      <div class="chart-row">
        <div class="chart-half">
          <div class="section-title">
            <el-icon><UserFilled /></el-icon>
            <span>政治面貌分布</span>
          </div>
          <div class="chart-container">
            <VChart v-if="politicalPieOptions" :option="politicalPieOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
        <div class="chart-half">
          <div class="section-title">
            <el-icon><WarningFilled /></el-icon>
            <span>预警趋势</span>
          </div>
          <div class="chart-container">
            <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
      </div>

      <!-- 第三行：生源地分布（全宽） -->
      <div class="chart-full">
        <div class="section-title">
          <el-icon><Location /></el-icon>
          <span>生源地分布</span>
        </div>
        <div class="chart-container">
          <VChart v-if="hometownBarOptions" :option="hometownBarOptions" autoresize />
          <el-empty v-else description="暂无数据" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- 右侧：两个饼图 -->
    <div class="analytics-right">
      <div class="chart-section half">
        <div class="section-title">
          <el-icon><UserFilled /></el-icon>
          <span>性别比例</span>
        </div>
        <div class="chart-container pie-chart">
          <VChart v-if="genderPieOptions" :option="genderPieOptions" autoresize />
          <el-empty v-else description="暂无数据" :image-size="60" />
        </div>
      </div>
      <div class="chart-divider"></div>
      <div class="chart-section half">
        <div class="section-title">
          <el-icon><WarningFilled /></el-icon>
          <span>心理危机分布</span>
        </div>
        <div class="chart-container pie-chart">
          <VChart v-if="crisisPieOptions" :option="crisisPieOptions" autoresize />
          <el-empty v-else description="暂无数据" :image-size="60" />
        </div>
      </div>
      <div class="chart-divider"></div>
      <div class="ai-analysis-section">
        <div class="section-title">
          <el-icon><DataAnalysis /></el-icon>
          <span>AI 班级分析</span>
        </div>
        <div v-if="!analysisResult && !analysisLoading" class="analysis-placeholder">
          <p>点击按钮，AI 将为您分析班级数据</p>
          <el-button type="primary" @click="emit('analyze')" :loading="analysisLoading" size="small">
            开始分析
          </el-button>
        </div>
        <div v-else-if="analysisLoading" class="analysis-loading">
          <el-icon class="loading-icon"><DataAnalysis /></el-icon>
          <p>AI 正在分析班级数据...</p>
        </div>
        <div v-else class="analysis-content">
          <div class="analysis-text">{{ analysisResult }}</div>
          <el-button text type="primary" size="small" @click="emit('analyze')">
            重新分析
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  DataAnalysis, Histogram, UserFilled, WarningFilled, Location, DArrowRight,
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { useClassCharts } from '@/composables/useClassCharts'
import type { ClassStats, ClassEvaluation } from '@/api/teacher'

const props = defineProps<{
  classStats: ClassStats
  evalData: ClassEvaluation
  analysisResult: string
  analysisLoading: boolean
}>()

const emit = defineEmits<{
  navigate: [link: string]
  analyze: []
}>()

const { evaluationRadarOptions, gradeBarOptions, politicalPieOptions, crisisTrendOptions, hometownBarOptions, genderPieOptions, crisisPieOptions } = useClassCharts(
  computed(() => props.classStats),
  computed(() => props.evalData),
)
</script>

<style scoped>
.analytics-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.analytics-left, .analytics-right {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.analytics-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.chart-half {
  min-width: 0;
}

.chart-full {
  width: 100%;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.section-title:hover {
  opacity: 0.7;
}

.section-link {
  margin-left: auto;
  font-size: 11px;
}

.chart-container {
  width: 100%;
  height: 160px;
}

.chart-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 6px 0;
}

.ai-analysis-section {
  margin-top: 6px;
  padding-top: 6px;
}

.analysis-placeholder {
  text-align: center;
  padding: 12px 8px;
  color: #888;
}

.analysis-placeholder p {
  margin: 0 0 8px 0;
  font-size: 12px;
}

.analysis-loading {
  text-align: center;
  padding: 12px 8px;
}

.loading-icon {
  font-size: 20px;
  color: #5b8def;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.analysis-content {
  font-size: 12px;
  line-height: 1.5;
  color: #555;
}

.analysis-text {
  white-space: pre-wrap;
  margin-bottom: 10px;
  max-height: 160px;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .analytics-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .analytics-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .analytics-left, .analytics-right {
    padding: 10px;
  }

  .chart-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .chart-container {
    height: 200px;
  }
}
</style>