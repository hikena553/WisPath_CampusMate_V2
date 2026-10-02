<template>
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">数据分析</span>
      <div style="width:36px"></div>
    </div>
    <div class="sub-page-body">
      <!-- 核心数据图表 -->
      <div class="charts-grid">
        <!-- 班级综合评估 -->
        <div class="mobile-section-card chart-card">
          <div class="chart-card-header">
            <el-icon color="#5b8def"><DataAnalysis /></el-icon>
            <span>班级综合评估</span>
          </div>
          <div class="chart-container" style="height:200px">
            <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="48" />
          </div>
        </div>

        <!-- 成绩分布 -->
        <div class="mobile-section-card chart-card">
          <div class="chart-card-header">
            <el-icon color="#67c23a"><Histogram /></el-icon>
            <span>成绩分布</span>
          </div>
          <div class="chart-container" style="height:200px">
            <VChart v-if="gradeBarOptions" :option="gradeBarOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="48" />
          </div>
        </div>

        <!-- 预警趋势 -->
        <div class="mobile-section-card chart-card">
          <div class="chart-card-header">
            <el-icon color="#f56c6c"><WarningFilled /></el-icon>
            <span>预警趋势</span>
          </div>
          <div class="chart-container" style="height:200px">
            <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="48" />
          </div>
        </div>
      </div>
    </div>

    <!-- 悬浮桌宠：点击查看班级情况分析 -->
    <div class="mascot-pet" @click="handleMascotClick">
      <transition name="tip-pop">
        <div v-if="showMascotTip" class="mascot-tip-bubble">
          <span class="mascot-tip-close" @click.stop="showMascotTip = false"><el-icon><Close /></el-icon></span>
          <span class="mascot-tip-text">点我查看班级情况分析~</span>
        </div>
      </transition>
      <img src="/images/mascot.png" alt="绵小城" class="mascot-pet-img" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ArrowLeft, Close, DataAnalysis, Histogram, WarningFilled } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { useClassCharts } from '@/composables/useClassCharts'
import type { ClassStats, ClassEvaluation } from '@/api/teacher'

const props = defineProps<{
  classStats: ClassStats
  evalData: ClassEvaluation
}>()

const emit = defineEmits<{
  close: []
  'open-analysis': []
}>()

const { evaluationRadarOptions, gradeBarOptions, crisisTrendOptions } = useClassCharts(
  computed(() => props.classStats),
  computed(() => props.evalData),
)

// 桌宠提示气泡：进入图表子页时展示 6 秒后自动消失
const showMascotTip = ref(false)
let mascotTipTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  showMascotTip.value = true
  mascotTipTimer = setTimeout(() => { showMascotTip.value = false }, 6000)
})

onUnmounted(() => {
  if (mascotTipTimer !== null) {
    clearTimeout(mascotTipTimer)
    mascotTipTimer = null
  }
})

function handleMascotClick() {
  showMascotTip.value = false
  emit('open-analysis')
}
</script>

<style scoped>
.sub-page {
  position: fixed; inset: 0; background: #f5f7fa;
  z-index: 100; display: flex; flex-direction: column;
}
.sub-page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fff;
  border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
.sub-page-title {
  font-size: 16px; font-weight: 600; color: #1a1a1a;
}
.sub-page-body {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}

.mobile-section-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.chart-container {
  width: 100%;
  height: 160px;
}

/* 图表卡片列表 */
.charts-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chart-card { border-radius: 14px; }
.chart-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

/* ---- 悬浮桌宠 ---- */
.mascot-pet {
  position: fixed;
  right: 16px;
  bottom: 84px;
  z-index: 130;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  -webkit-tap-highlight-color: transparent;
}
.mascot-pet-img {
  width: 76px;
  height: 76px;
  object-fit: contain;
  filter: drop-shadow(0 6px 14px rgba(91, 141, 239, 0.45));
}
.mascot-pet:active .mascot-pet-img { transform: scale(0.92); }
.mascot-tip-bubble {
  position: relative;
  background: #fff;
  border: 1px solid #e9d5ff;
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  padding: 8px 10px 8px 12px;
  margin-bottom: 10px;
  margin-right: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #4c1d95;
  display: flex;
  align-items: center;
  gap: 8px;
}
.mascot-tip-bubble::after {
  content: '';
  position: absolute;
  right: 22px;
  bottom: -6px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-right: 1px solid #e9d5ff;
  border-bottom: 1px solid #e9d5ff;
  transform: rotate(45deg);
}
.mascot-tip-text { white-space: nowrap; }
.mascot-tip-close {
  display: inline-flex;
  width: 16px; height: 16px;
  align-items: center; justify-content: center;
  border-radius: 50%;
  background: #f3e8ff;
  color: #7c3aed;
  font-size: 10px;
  flex-shrink: 0;
}
.tip-pop-enter-active,
.tip-pop-leave-active {
  transition: all 0.25s ease !important;
}
.tip-pop-enter-from,
.tip-pop-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.92);
}

@media (max-width: 767px) {
  .chart-container {
    height: 200px;
  }
}
</style>