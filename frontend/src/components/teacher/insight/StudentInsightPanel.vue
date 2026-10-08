<template>
  <div class="si-panel">
    <div v-if="loading" class="si-state">诊断中…</div>

    <div v-else-if="!insight" class="si-state">
      <p>诊断失败，请稍后重试</p>
      <el-button size="small" round @click="load">重新诊断</el-button>
    </div>

    <template v-else>
      <!-- 风险结论（完全来自证据清单） -->
      <div class="si-risk" :class="`risk-${insight.profile.risk_level}`">
        <div class="si-risk-head">
          <span class="si-risk-label">
            {{ insight.profile.risk_level === 'high' ? '高风险' : insight.profile.risk_level === 'medium' ? '中风险' : '低风险' }}
          </span>
          <span class="si-risk-window">近 {{ insight.profile.days }} 天</span>
        </div>
        <div v-if="insight.profile.risk_reasons.length" class="si-risk-reasons">
          <span v-for="(r, i) in insight.profile.risk_reasons" :key="i" class="si-reason">{{ r }}</span>
        </div>
        <div v-else class="si-risk-reasons"><span class="si-reason muted">未发现明显异常</span></div>
      </div>

      <!-- AI 建议 -->
      <div class="si-advice">
        <div class="si-advice-head">
          <el-icon><MagicStick /></el-icon>
          <span>辅导建议</span>
          <el-tag v-if="insight.degraded" size="small" type="warning" effect="plain" round>
            已降级为规则建议
          </el-tag>
        </div>
        <div class="si-advice-body">{{ insight.advice }}</div>
        <div class="si-advice-ops">
          <el-button
            size="small"
            type="primary"
            round
            :loading="converting"
            :disabled="converted"
            @click="convert"
          >{{ converted ? '已转为跟进' : '转为跟进任务' }}</el-button>
          <el-button size="small" round :loading="loading" @click="load">重新诊断</el-button>
        </div>
      </div>

      <!-- 证据清单（可溯源） -->
      <div class="si-evidence">
        <div class="si-evidence-title">证据清单（结论依据，均取自系统数据）</div>
        <div class="si-evidence-grid">
          <div v-for="e in insight.profile.evidence" :key="e.label" class="si-evidence-item">
            <span class="si-evidence-label">{{ e.label }}</span>
            <span class="si-evidence-value">{{ e.value }}</span>
          </div>
        </div>
      </div>

      <!-- 关键指标可视化（ECharts，复用项目既有图表栈） -->
      <div class="si-chart">
        <div class="si-evidence-title">关键指标</div>
        <VChart class="si-chart-canvas" :option="chartOption" autoresize />
      </div>

      <!-- 行为分布 -->
      <div v-if="insight.profile.by_verb.length" class="si-verbs">
        <div class="si-evidence-title">行为分布</div>
        <div class="si-verb-list">
          <span v-for="v in insight.profile.by_verb" :key="v.verb" class="si-verb-chip">
            {{ v.verb }} · {{ v.count }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  convertInsightToTask,
  getStudentInsight,
  type StudentInsight,
} from '@/api/teacher'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{ studentId: number; studentName?: string }>()
const emit = defineEmits<{ converted: [] }>()

const loading = ref(false)
const converting = ref(false)
const converted = ref(false)
const insight = ref<StudentInsight | null>(null)

/** 关键指标柱状图：全部取自画像 metrics，与证据清单同源 */
const chartOption = computed(() => {
  const m = (insight.value?.profile.metrics || {}) as Record<string, string | number>
  const labels = ['学情事件', '请假', '关怀侧写', '成长记录', '未办结任务']
  const values = [
    m.learning_total,
    m.leave_total,
    m.care_total,
    m.growth_total,
    m.open_tasks,
  ].map((v) => Number(v ?? 0))

  return {
    grid: { left: 4, right: 8, top: 16, bottom: 2, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#eaecf0' } },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: '#98a2b3' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f2f4f7' } },
      axisLabel: { fontSize: 10, color: '#98a2b3' },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barWidth: 16,
        itemStyle: { borderRadius: [6, 6, 0, 0], color: '#5b8def' },
      },
    ],
    textStyle: { fontFamily: 'Noto Sans CJK SC, WenQuanYi Micro Hei, sans-serif' },
  }
})

async function load() {
  if (!props.studentId) return
  loading.value = true
  converted.value = false
  try {
    insight.value = await getStudentInsight(props.studentId)
  } catch {
    insight.value = null
    ElMessage.error('学情诊断失败')
  } finally {
    loading.value = false
  }
}

async function convert() {
  if (!insight.value) return
  converting.value = true
  try {
    await convertInsightToTask(
      insight.value.student_id,
      insight.value.advice,
      insight.value.profile.risk_level
    )
    converted.value = true
    ElMessage.success('已转为跟进任务')
    emit('converted')
  } catch {
    ElMessage.error('转为跟进失败')
  } finally {
    converting.value = false
  }
}

watch(() => props.studentId, load)
onMounted(load)
</script>

<style scoped>
.si-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.si-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 0;
  color: #98a2b3;
  font-size: 13px;
}
.si-state p { margin: 0; }

.si-risk {
  border-radius: 12px;
  padding: 12px 14px;
  background: #f9fafb;
  border-left: 3px solid #98a2b3;
}
.si-risk.risk-high { background: #fef3f2; border-left-color: #d92d20; }
.si-risk.risk-medium { background: #fffaeb; border-left-color: #b54708; }
.si-risk.risk-low { background: #ecfdf3; border-left-color: #079455; }

.si-risk-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.si-risk-label {
  font-size: 14px;
  font-weight: 700;
  color: #101828;
}
.si-risk-window {
  font-size: 11.5px;
  color: #98a2b3;
}
.si-risk-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.si-reason {
  font-size: 12px;
  color: #475467;
  background: rgba(255, 255, 255, 0.75);
  border-radius: 999px;
  padding: 2px 9px;
}
.si-reason.muted { color: #98a2b3; }

.si-advice {
  border: 1px solid #f0f1f3;
  border-radius: 12px;
  padding: 12px 14px;
  background: #fff;
}
.si-advice-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #101828;
  margin-bottom: 8px;
}
.si-advice-head .el-icon { color: #6941c6; }
.si-advice-body {
  font-size: 13px;
  color: #344054;
  line-height: 1.7;
  white-space: pre-wrap;
}
.si-advice-ops {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.si-evidence-title {
  font-size: 13px;
  font-weight: 600;
  color: #101828;
  margin-bottom: 8px;
}
.si-evidence-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.si-evidence-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  background: #fcfcfd;
  border: 1px solid #f2f4f7;
  border-radius: 9px;
  padding: 7px 10px;
}
.si-evidence-label {
  font-size: 12px;
  color: #667085;
}
.si-evidence-value {
  font-size: 13px;
  font-weight: 600;
  color: #101828;
}

.si-chart {
  border: 1px solid #f0f1f3;
  border-radius: 12px;
  padding: 12px 12px 6px;
  background: #fff;
}
.si-chart-canvas {
  width: 100%;
  height: 150px;
}

.si-verb-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.si-verb-chip {
  font-size: 11.5px;
  color: #475467;
  background: #f2f4f7;
  border-radius: 999px;
  padding: 2px 9px;
}

@media (max-width: 767px) {
  .si-evidence-grid { grid-template-columns: 1fr; }
}
</style>