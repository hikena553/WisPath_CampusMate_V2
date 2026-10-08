<template>
  <div class="tui-page">
    <SubPageHeader
      title="问卷互评"
      sub="匿名收集反馈，只出聚合结果，不回溯个人"
      fallback="/teacher/more"
    />

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">问卷互评</h2>
          <p class="tui-header-sub">匿名收集反馈，只出聚合结果，不回溯个人</p>
        </div>
        <div class="tui-header-actions">
          <el-button type="primary" round :icon="Plus" @click="createVisible = true">发起问卷</el-button>
        </div>
      </header>

      <!-- 移动端高频操作 -->
      <div v-if="isMobile" class="tui-actions sv-topbar">
        <el-button type="primary" round :icon="Plus" @click="createVisible = true">发起问卷</el-button>
      </div>

      <TuiSegmented
        v-model="tab"
        class="tui-seg-wrap"
        :options="[
          { value: 'join', label: '待参与', count: openSurveys.length },
          { value: 'created', label: '我创建的', count: mySurveys.length },
          { value: 'mine', label: '我的被评', count: mineResults.length },
        ]"
      />

      <!-- 待参与 -->
      <template v-if="tab === 'join'">
        <div v-if="loading" class="tui-empty">
          <span class="tui-empty-title">加载中…</span>
        </div>
        <div v-else-if="!openSurveys.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="28"><EditPen /></el-icon></span>
          <span class="tui-empty-title">当前没有开放中的问卷</span>
        </div>
        <div v-else class="tui-stack">
          <article v-for="s in openSurveys" :key="s.id" class="tui-card">
            <div class="tui-card-body sv-item">
              <div class="tui-row-main">
                <div class="sv-title">
                  <span class="tui-ellipsis-2">{{ s.title }}</span>
                  <el-tag size="small" effect="plain" round>{{ SURVEY_TARGET_LABEL[s.target_type] }}</el-tag>
                </div>
                <div class="tui-meta">
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
          </article>
        </div>
      </template>

      <!-- 我创建的 -->
      <template v-else-if="tab === 'created'">
        <div v-if="!mySurveys.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="28"><Tickets /></el-icon></span>
          <span class="tui-empty-title">你还没有发起过问卷</span>
        </div>
        <div v-else class="tui-stack">
          <article v-for="s in mySurveys" :key="s.id" class="tui-card">
            <div class="tui-card-body sv-item">
              <div class="tui-row-main">
                <div class="sv-title">
                  <span class="tui-ellipsis-2">{{ s.title }}</span>
                  <el-tag :type="statusTag(s.status)" size="small" effect="light" round>
                    {{ SURVEY_STATUS_LABEL[s.status] }}
                  </el-tag>
                </div>
                <div class="tui-meta">
                  <span>{{ SURVEY_TARGET_LABEL[s.target_type] }}</span>
                  <span v-if="s.period">{{ s.period }}</span>
                  <span>已收集 {{ s.response_count }} 份</span>
                </div>
              </div>
              <div class="tui-actions">
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
          </article>
        </div>
      </template>

      <!-- 我的被评结果 -->
      <template v-else-if="tab === 'mine'">
        <div v-if="!mineResults.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="28"><TrendCharts /></el-icon></span>
          <span class="tui-empty-title">暂未收到针对你的评价</span>
        </div>
        <div v-else class="tui-stack">
          <article v-for="r in mineResults" :key="r.survey_id" class="tui-card">
            <div class="tui-card-body sv-block">
              <div class="sv-title">
                <span class="tui-ellipsis-2">{{ r.title }}</span>
                <el-tag size="small" effect="plain" round>{{ SURVEY_TARGET_LABEL[r.target_type] }}</el-tag>
              </div>
              <SurveyResultPanel :result="r" />
            </div>
          </article>
        </div>
      </template>

      <SurveyCreateDialog v-model="createVisible" @created="loadAll" />

      <SurveyFillDialog v-model="fillVisible" :survey="filling" @saved="loadAll" />

      <el-dialog
        v-model="resultVisible"
        :title="resultTitle"
        :width="isMobile ? '94%' : '640px'"
        align-center
        destroy-on-close
      >
        <div v-if="resultLoading" class="tui-empty">
          <span class="tui-empty-title">统计中…</span>
        </div>
        <SurveyResultPanel v-else-if="result" :result="result" />
      </el-dialog>
    </div>
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
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
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
/* 移动端高频操作条 */
.sv-topbar {
  margin-bottom: 12px;
}
.sv-topbar .el-button {
  flex: 1;
  margin-left: 0;
}

/* 问卷卡片 */
.sv-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sv-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sv-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--tui-text);
}
.sv-title > span:first-child {
  flex: 1;
  min-width: 0;
}

@media (max-width: 767px) {
  .sv-item {
    flex-direction: column;
    align-items: stretch;
  }
  .sv-item .tui-actions {
    justify-content: flex-end;
  }
}
</style>