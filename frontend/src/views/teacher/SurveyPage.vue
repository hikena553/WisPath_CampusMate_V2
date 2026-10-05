<template>
  <div class="survey-page">
    <header class="sv-header">
      <div class="sv-header-left">
        <h2>问卷互评</h2>
        <p class="sv-sub">匿名收集反馈，只出聚合结果，不回溯个人</p>
      </div>
      <el-button type="primary" round :icon="Plus" @click="createVisible = true">发起问卷</el-button>
    </header>

    <el-tabs v-model="tab" class="sv-tabs">
      <!-- 待参与 -->
      <el-tab-pane label="待参与" name="join">
        <div v-if="loading" class="sv-empty">加载中…</div>
        <div v-else-if="!openSurveys.length" class="sv-empty">
          <el-icon :size="38" color="#d0d5dd"><EditPen /></el-icon>
          <p>当前没有开放中的问卷</p>
        </div>
        <div v-else class="sv-list">
          <div v-for="s in openSurveys" :key="s.id" class="sv-card">
            <div class="sv-card-main">
              <div class="sv-card-title">
                {{ s.title }}
                <el-tag size="small" effect="plain" round>{{ SURVEY_TARGET_LABEL[s.target_type] }}</el-tag>
              </div>
              <div class="sv-card-meta">
                <span v-if="s.period">{{ s.period }}</span>
                <span>{{ s.questions.length }} 个维度</span>
                <span>已收集 {{ s.response_count }} 份</span>
              </div>
            </div>
            <el-button
              type="primary"
              round
              size="small"
              :disabled="s.my_submitted"
              @click="openFill(s)"
            >{{ s.my_submitted ? '已提交' : '参与评价' }}</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 我创建的 -->
      <el-tab-pane label="我创建的" name="created">
        <div v-if="!mySurveys.length" class="sv-empty">
          <el-icon :size="38" color="#d0d5dd"><Tickets /></el-icon>
          <p>你还没有发起过问卷</p>
        </div>
        <div v-else class="sv-list">
          <div v-for="s in mySurveys" :key="s.id" class="sv-card">
            <div class="sv-card-main">
              <div class="sv-card-title">
                {{ s.title }}
                <el-tag :type="statusTag(s.status)" size="small" effect="light" round>
                  {{ SURVEY_STATUS_LABEL[s.status] }}
                </el-tag>
              </div>
              <div class="sv-card-meta">
                <span>{{ SURVEY_TARGET_LABEL[s.target_type] }}</span>
                <span v-if="s.period">{{ s.period }}</span>
                <span>已收集 {{ s.response_count }} 份</span>
              </div>
            </div>
            <div class="sv-card-ops">
              <el-button size="small" round @click="viewResult(s)">查看结果</el-button>
              <el-button
                v-if="s.status === 'open'"
                size="small"
                round
                type="warning"
                plain
                @click="toggleStatus(s, 'closed')"
              >结束</el-button>
              <el-button
                v-else-if="s.status === 'draft'"
                size="small"
                round
                type="success"
                plain
                @click="toggleStatus(s, 'open')"
              >开放</el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 我的被评结果 -->
      <el-tab-pane label="我的被评" name="mine">
        <div v-if="!mineResults.length" class="sv-empty">
          <el-icon :size="38" color="#d0d5dd"><TrendCharts /></el-icon>
          <p>暂未收到针对你的评价</p>
        </div>
        <div v-else class="sv-list">
          <div v-for="r in mineResults" :key="r.survey_id" class="sv-card sv-card-block">
            <div class="sv-card-title">
              {{ r.title }}
              <el-tag size="small" effect="plain" round>{{ SURVEY_TARGET_LABEL[r.target_type] }}</el-tag>
            </div>
            <SurveyResultPanel :result="r" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <SurveyCreateDialog v-model="createVisible" @created="loadAll" />

    <SurveyFillDialog v-model="fillVisible" :survey="filling" @saved="loadAll" />

    <el-dialog
      v-model="resultVisible"
      :title="resultTitle"
      :width="isMobile ? '94%' : '640px'"
      align-center
      destroy-on-close
    >
      <div v-if="resultLoading" class="sv-empty">统计中…</div>
      <SurveyResultPanel v-else-if="result" :result="result" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { EditPen, Plus, Tickets, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import {
  getMySurveyResults,
  getSurveyResult,
  listSurveys,
  updateSurveyStatus,
  SURVEY_STATUS_LABEL,
  SURVEY_TARGET_LABEL,
  type PeerSurvey,
  type PeerSurveyMine,
  type PeerSurveyResult,
  type SurveyStatus,
} from '@/api/peerSurvey'
import SurveyCreateDialog from '@/components/teacher/survey/SurveyCreateDialog.vue'
import SurveyFillDialog from '@/components/teacher/survey/SurveyFillDialog.vue'
import SurveyResultPanel from '@/components/teacher/survey/SurveyResultPanel.vue'

defineOptions({ name: 'teacher-survey' })

const { isMobile } = useResponsive()
const auth = useAuthStore()

const tab = ref('join')
const surveys = ref<PeerSurvey[]>([])
const mineResults = ref<PeerSurveyMine[]>([])
const loading = ref(false)

const createVisible = ref(false)
const fillVisible = ref(false)
const filling = ref<PeerSurvey | null>(null)

const resultVisible = ref(false)
const resultLoading = ref(false)
const result = ref<PeerSurveyResult | null>(null)
const resultTitle = ref('聚合结果')

const openSurveys = computed(() => surveys.value.filter((s) => s.status === 'open'))
const mySurveys = computed(() => surveys.value.filter((s) => s.created_by === auth.user?.id))

function statusTag(status: SurveyStatus) {
  return status === 'open' ? 'success' : status === 'draft' ? 'info' : 'warning'
}

async function loadAll() {
  loading.value = true
  try {
    surveys.value = await listSurveys()
  } catch {
    ElMessage.error('问卷列表加载失败')
  } finally {
    loading.value = false
  }
  try {
    mineResults.value = await getMySurveyResults()
  } catch {
    mineResults.value = []
  }
}

function openFill(s: PeerSurvey) {
  filling.value = s
  fillVisible.value = true
}

async function toggleStatus(s: PeerSurvey, status: SurveyStatus) {
  try {
    await updateSurveyStatus(s.id, status)
    ElMessage.success(status === 'open' ? '已开放' : '已结束')
    loadAll()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function viewResult(s: PeerSurvey) {
  resultTitle.value = `${s.title} · 聚合结果`
  resultVisible.value = true
  resultLoading.value = true
  result.value = null
  try {
    result.value = await getSurveyResult(s.id)
  } catch {
    ElMessage.error('结果加载失败')
  } finally {
    resultLoading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.survey-page {
  height: 100%;
  overflow-y: auto;
  padding: 8px 4px 24px;
}

.sv-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 0 4px;
  margin-bottom: 12px;
}
.sv-header-left h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}
.sv-sub {
  margin: 3px 0 0;
  font-size: 12px;
  color: #888;
}

.sv-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 52px 0;
  color: #98a2b3;
  font-size: 13px;
}
.sv-empty p { margin: 0; }

.sv-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sv-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 12px;
  padding: 13px 15px;
}
.sv-card-block {
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
}
.sv-card-main {
  flex: 1;
  min-width: 0;
}
.sv-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #101828;
  margin-bottom: 5px;
}
.sv-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #98a2b3;
}
.sv-card-ops {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .sv-card {
    flex-direction: column;
    align-items: stretch;
  }
  .sv-card-ops {
    justify-content: flex-end;
  }
  .sv-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>