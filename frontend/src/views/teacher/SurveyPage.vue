<template>
  <div class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel">
    <SubPageHeader
      title="问卷中心"
      fallback="/teacher"
    />

    <!-- 移动端下拉刷新：指示器插在吸顶栏之后 -->
    <PullRefreshIndicator v-if="isMobile" :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <!-- ============================================================
         移动端 · 定稿版「题卡」版式
         列表页只回答「哪几份要你填、填到哪了」；真正的填答点进去是题卡流
         ============================================================ -->
    <div v-if="isMobile" class="tm-page tm-m">
      <!-- ① 三个数 -->
      <div class="tm-kpis">
        <div class="tm-kpi tm-ok"><b>{{ overall.rate }}%</b><span>整体回收</span></div>
        <div class="tm-kpi"><b>{{ overall.responses }}</b><span>已回收</span></div>
        <div class="tm-kpi" :class="pendingCount > 0 ? 'tm-warn' : ''"><b>{{ pendingCount }}</b><span>待我参与</span></div>
      </div>

      <!-- 发起入口 + AI 辅助设计：移动端原先没有「发起问卷」按钮，空状态文案指向右上角却无处可点 -->
      <button type="button" class="tm-ai-launch" @click="createVisible = true">
        <img class="tm-ai-launch-ic" :src="siteMascot" alt="绵小城" />
        <span class="tm-ai-launch-bd">
          <b>AI 辅助发起问卷</b>
          <em>描述场景自动推荐维度，也可手动创建；匿名收集只出聚合结果</em>
        </span>
        <span class="tm-ai-launch-go">发起</span>
      </button>

      <div class="tm-seg">
        <button type="button" :class="{ 'tm-on': tab === 'join' }" @click="tab = 'join'">待参与 {{ pendingCount }}</button>
        <button type="button" :class="{ 'tm-on': tab === 'created' }" @click="tab = 'created'">我创建的 {{ mySurveys.length }}</button>
        <button type="button" :class="{ 'tm-on': tab === 'mine' }" @click="tab = 'mine'">我的被评 {{ mineResults.length }}</button>
      </div>

      <div v-if="loading" class="tm-m-load">
        <AgentLoading block :tips="['正在读取问卷', '正在核对参与状态']" />
      </div>

      <!-- ③ 待参与：题卡入口 -->
      <template v-else-if="tab === 'join'">
        <div v-if="!pendingList.length" class="tm-empty">
          <b>当前没有开放中的问卷</b>
          <span>有同事发起互评或被指派评价任务时，这里会出现</span>
        </div>
        <div v-else class="tm-feed">
          <button v-for="s in pendingList" :key="s.id" type="button" class="tm-sv" @click="openFill(s)">
            <div class="tm-sv-hd">
              <span class="tm-sv-t">{{ s.title }}</span>
              <span class="tm-tag tm-ai">{{ SURVEY_TARGET_LABEL[s.target_type] }}</span>
            </div>
            <div class="tm-sv-chips">
              <span v-for="q in s.questions.slice(0, 4)" :key="q.key" class="tm-chip">{{ q.label }}</span>
            </div>
            <div class="tm-sv-ft">
              <span>{{ s.questions.length }} 题 · 约 {{ s.questions.length * 15 }} 秒 · {{ s.period || '未标注周期' }}</span>
              <span class="tm-sv-go">开始填 ›</span>
            </div>
          </button>
        </div>
        <div v-if="submittedToday.length" class="tm-sec" style="margin-top: 11px">
          <span class="tm-sec-t">已提交</span>
          <span class="tm-sec-m">{{ submittedToday.length }} 份</span>
        </div>
        <div v-if="submittedToday.length" class="tm-feed">
          <div v-for="s in submittedToday" :key="s.id" class="tm-sv tm-sv-done">
            <div class="tm-sv-hd">
              <span class="tm-sv-t">{{ s.title }}</span>
              <span class="tm-tag tm-ok">已提交</span>
            </div>
            <div class="tm-sv-ft"><span>提交后不可修改，结果只做聚合</span></div>
          </div>
        </div>
      </template>

      <!-- ④ 我创建的：回收率 + 结束/开放 -->
      <template v-else-if="tab === 'created'">
        <div v-if="!mySurveys.length" class="tm-empty">
          <b>你还没有发起过问卷</b>
          <span>点上方「AI 辅助发起问卷」，描述场景即可自动推荐维度并开始收集</span>
        </div>
        <div v-else class="tm-feed">
          <div v-for="s in mySurveys" :key="s.id" class="tm-sv">
            <div class="tm-sv-hd">
              <span class="tm-sv-t">{{ s.title }}</span>
              <span class="tm-tag" :class="s.status === 'open' ? 'tm-ok' : s.status === 'draft' ? 'tm-mute' : 'tm-warn'">
                {{ SURVEY_STATUS_LABEL[s.status] }}
              </span>
            </div>
            <div class="tm-sv-bar">
              <div class="tm-sv-tr"><i :style="{ width: rateOf(s) + '%' }"></i></div>
              <span class="tm-sv-v">{{ rateOf(s) }}%</span>
            </div>
            <div class="tm-sv-ft">
              <span>已收集 {{ s.response_count }} 份 · {{ SURVEY_TARGET_LABEL[s.target_type] }}</span>
              <span class="tm-sv-ops">
                <button type="button" @click="viewResult(s)">结果</button>
                <button
                  v-if="s.status === 'open'"
                  type="button"
                  class="tm-sv-danger"
                  @click="toggleStatus(s, 'closed')"
                >结束</button>
                <button v-else-if="s.status === 'draft'" type="button" @click="toggleStatus(s, 'open')">开放</button>
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- ⑤ 我的被评：聚合结果 -->
      <template v-else>
        <div v-if="!mineResults.length" class="tm-empty">
          <b>暂未收到对你的评价</b>
          <span>样本不足时只显示均值区间，不回溯到个人</span>
        </div>
        <div v-else class="tm-feed">
          <div v-for="r in mineResults" :key="r.survey_id" class="tm-sv">
            <div class="tm-sv-hd">
              <span class="tm-sv-t">{{ r.title }}</span>
              <span class="tm-tag tm-ai">{{ SURVEY_TARGET_LABEL[r.target_type] }}</span>
            </div>
            <SurveyResultPanel :result="r" />
          </div>
        </div>
      </template>

      <div class="tm-tail">匿名保护：系统不记录填写人，样本不足不展示分布</div>
    </div>

    <div v-else class="tui-content">
      <!-- 桌面端特色头部：问卷语义色 + 编辑图标；右侧是本页的回收概况与发起入口 -->
      <TuiPageHero
        v-if="!isMobile"
        title="问卷中心"
        sub="匿名收集反馈，只出聚合结果，不回溯个人"
        :icon="EditPen"
        tone="cyan"
      >
        <div class="tui-hero-metric is-accent"><b>{{ openSurveys.length }}</b><span>进行中</span></div>
        <div class="tui-hero-metric"><b>{{ mySurveys.length }}</b><span>我发起的</span></div>
        <div class="tui-hero-metric"><b>{{ overall.rate }}%</b><span>回收率</span></div>
        <el-button size="small" :icon="Plus" @click="createVisible = true">发起问卷</el-button>
      </TuiPageHero>

      <!-- 移动端高频操作 -->
      <div v-if="isMobile" class="tui-actions sv-topbar">
        <el-button size="small" :icon="Plus" @click="createVisible = true">发起问卷</el-button>
      </div>

      <!-- 回收率环形进度卡 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><TrendCharts /></el-icon>回收概览</h3>
          <span class="tui-section-extra">
            <span class="tui-tag tui-tag-success"><el-icon><Lock /></el-icon>匿名保护</span>
          </span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>回收率 = 已回收份数 ÷ 预计受众（按评价类型估算），样本不足时不展示分布与建议。</span>
        </div>
        <div class="sv-overview">
          <span
            class="ring"
            :style="{ background: `conic-gradient(var(--tui-brand) 0 ${overall.rate}%, var(--tui-surface-sunken) ${overall.rate}% 100%)` }"
          >
            <span class="ring-mid">{{ overall.rate }}%</span>
          </span>
          <div class="sv-ov-meta">
            <div class="sv-ov-title">整体回收率</div>
            <div class="tui-meta">
              <span>已回收 {{ overall.responses }} 份</span>
              <span class="tui-meta-sep">·</span>
              <span>预计受众 {{ overall.audience }} 份</span>
            </div>
            <div class="sv-ov-tags">
              <span class="tui-chip">不记录填写人</span>
              <span class="tui-chip">仅出聚合结果</span>
            </div>
          </div>
        </div>
      </section>

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
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>这里列出发放给你的开放问卷，提交后不可修改，结果只做聚合展示。</span>
        </div>
        <div v-if="loading" class="tui-empty">
          <AgentLoading block :tips="['正在读取开放中的问卷', '正在核对参与状态']" />
        </div>
        <div v-else-if="!openSurveys.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><EditPen /></el-icon></span>
          <span class="tui-empty-title">当前没有开放中的问卷</span>
          <span class="tui-empty-desc">等有同事发起互评，或被指派评价任务时，这里会出现待参与问卷。</span>
        </div>
        <template v-else>
          <div class="tui-stack">
            <article v-for="s in joinPaged" :key="s.id" class="tui-card">
              <div class="tui-card-body sv-item">
                <div class="tui-row-main">
                  <div class="sv-title">
                    <span class="tui-ellipsis-2">{{ s.title }}</span>
                    <el-tag size="small" effect="plain" round>{{ SURVEY_TARGET_LABEL[s.target_type] }}</el-tag>
                  </div>
                  <div class="sv-dims">
                    <span v-for="q in s.questions" :key="q.key" class="tui-chip">{{ q.label }}</span>
                  </div>
                  <div class="tui-meta">
                    <span v-if="s.period">{{ s.period }}</span>
                    <span>已收集 {{ s.response_count }} 份</span>
                    <span class="tui-meta-sep">·</span>
                    <span class="sv-anon"><el-icon><Lock /></el-icon>匿名</span>
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
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="joinPage"
              v-model:page-size="joinPageSize"
              :page-sizes="[10, 20, 50]"
              :total="openSurveys.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleJoinSizeChange"
              @current-change="handleJoinCurrentChange"
            />
          </div>
        </template>
      </template>

      <!-- 我创建的 -->
      <template v-else-if="tab === 'created'">
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>你发起的问卷：右侧环形为回收率；开放中可「结束」，草稿可「开放」。</span>
        </div>
        <div v-if="!mySurveys.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><Tickets /></el-icon></span>
          <span class="tui-empty-title">你还没有发起过问卷</span>
          <span class="tui-empty-desc">点击「发起问卷」，选择一个主题与评价维度即可开始收集。</span>
        </div>
        <template v-else>
          <div class="tui-stack">
            <article v-for="s in createdPaged" :key="s.id" class="tui-card">
              <div class="tui-card-body sv-item">
                <div class="tui-row-main">
                  <div class="sv-title">
                    <span class="tui-ellipsis-2">{{ s.title }}</span>
                    <el-tag :type="statusTag(s.status)" size="small" effect="light" round>
                      {{ SURVEY_STATUS_LABEL[s.status] }}
                    </el-tag>
                  </div>
                  <div class="sv-dims">
                    <span v-for="q in s.questions" :key="q.key" class="tui-chip">{{ q.label }}</span>
                  </div>
                  <div class="tui-meta">
                    <span>{{ SURVEY_TARGET_LABEL[s.target_type] }}</span>
                    <span v-if="s.period">{{ s.period }}</span>
                    <span>已收集 {{ s.response_count }} 份</span>
                    <span class="tui-meta-sep">·</span>
                    <span class="sv-anon"><el-icon><Lock /></el-icon>匿名</span>
                  </div>
                </div>
                <div class="sv-side">
                  <span
                    class="ring sm"
                    :style="{ background: `conic-gradient(var(--tui-brand) 0 ${rateOf(s)}%, var(--tui-surface-sunken) ${rateOf(s)}% 100%)` }"
                  >
                    <span class="ring-mid">{{ rateOf(s) }}%</span>
                  </span>
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
              </div>
            </article>
          </div>
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="createdPage"
              v-model:page-size="createdPageSize"
              :page-sizes="[10, 20, 50]"
              :total="mySurveys.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleCreatedSizeChange"
              @current-change="handleCreatedCurrentChange"
            />
          </div>
        </template>
      </template>

      <!-- 我的被评结果 -->
      <template v-else-if="tab === 'mine'">
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>这是别人对你的匿名评价聚合结果，样本不足时只显示均值区间。</span>
        </div>
        <div v-if="!mineResults.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><TrendCharts /></el-icon></span>
          <span class="tui-empty-title">暂未收到针对你的评价</span>
          <span class="tui-empty-desc">当同事或学生完成对你的评价后，聚合结果会在这里出现。</span>
        </div>
        <template v-else>
          <div class="tui-stack">
            <article v-for="r in minePaged" :key="r.survey_id" class="tui-card">
              <div class="tui-card-body sv-block">
                <div class="sv-title">
                  <span class="tui-ellipsis-2">{{ r.title }}</span>
                  <el-tag size="small" effect="plain" round>{{ SURVEY_TARGET_LABEL[r.target_type] }}</el-tag>
                </div>
                <SurveyResultPanel :result="r" />
              </div>
            </article>
          </div>
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="minePage"
              v-model:page-size="minePageSize"
              :page-sizes="[10, 20, 50]"
              :total="mineResults.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleMineSizeChange"
              @current-change="handleMineCurrentChange"
            />
          </div>
        </template>
      </template>

    </div>

    <!-- 发起 / 填答 / 结果三个浮层放在移动端·桌面端分支之外：
         此前它们嵌在桌面端 v-else 内，移动端点击「AI 辅助发起问卷」或「开始填」时组件根本不渲染，
         表现就是“点击没有反应”。 -->
    <SurveyCreateDialog v-model="createVisible" @created="loadAll" />

    <SurveyFillDialog v-model="fillVisible" :survey="filling" @saved="loadAll" />

    <!-- 聚合结果（长内容：移动端=全屏子页） -->
    <ResponsivePopup
      v-model="resultVisible"
      :title="resultTitle"
      width="400px"
      align-center
      :close-on-click-modal="false"
      class="tui-dialog"
      destroy-on-close
    >
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>以下为聚合统计结果，不包含任何可回溯到个人的信息。</span>
      </div>
      <div v-if="resultLoading" class="tui-empty">
        <span class="tui-empty-title">统计中…</span>
      </div>
      <SurveyResultPanel v-else-if="result" :result="result" />
    </ResponsivePopup>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
// v6.1 弹窗减负：结果查看走全屏子页承接
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { EditPen, InfoFilled, Lock, Plus, Tickets, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
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
  type SurveyTargetType,
} from '@/api/peerSurvey'
import { getTeachers } from '@/api/user'
import { getStudents } from '@/api/teacher'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import SurveyCreateDialog from '@/components/teacher/survey/SurveyCreateDialog.vue'
import SurveyFillDialog from '@/components/teacher/survey/SurveyFillDialog.vue'
import SurveyResultPanel from '@/components/teacher/survey/SurveyResultPanel.vue'

defineOptions({ name: 'teacher-survey' })

const { isMobile } = useResponsive()
const { siteMascot } = useSiteConfig()
const auth = useAuthStore()

// 移动端下拉刷新：桌面端不响应手势
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

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

// 回收率估算所需的受众规模（复用既有接口，不新增后端）
const teacherCount = ref(0)
const studentCount = ref(0)

// 各分组分页（契约 §2，pageSize 默认 10）
const joinPage = ref(1)
const joinPageSize = ref(10)
const createdPage = ref(1)
const createdPageSize = ref(10)
const minePage = ref(1)
const minePageSize = ref(10)

const openSurveys = computed(() => surveys.value.filter((s) => s.status === 'open'))
const mySurveys = computed(() => surveys.value.filter((s) => s.created_by === auth.user?.id))

/* ---------- 移动端（定稿版·题卡）私有计算 ---------- */
/** 待我参与：开放中且我没提交过的 */
const pendingList = computed(() => openSurveys.value.filter((s) => !s.my_submitted))
const pendingCount = computed(() => pendingList.value.length)
/** 已提交过（同一批公开问卷里） */
const submittedToday = computed(() => openSurveys.value.filter((s) => s.my_submitted))

function paged<T>(list: T[], page: number, size: number) {
  return list.slice((page - 1) * size, page * size)
}

const joinPaged = computed(() => paged(openSurveys.value, joinPage.value, joinPageSize.value))
const createdPaged = computed(() => paged(mySurveys.value, createdPage.value, createdPageSize.value))
const minePaged = computed(() => paged(mineResults.value, minePage.value, minePageSize.value))

function audienceFor(target: SurveyTargetType) {
  return target === 'student' ? studentCount.value : teacherCount.value
}

function rateOf(s: { target_type: SurveyTargetType; response_count: number }) {
  const audience = audienceFor(s.target_type)
  if (!audience) return 0
  return Math.min(100, Math.round((s.response_count / audience) * 100))
}

const overall = computed(() => {
  const list = surveys.value.filter((s) => s.status !== 'draft')
  const responses = list.reduce((n, s) => n + s.response_count, 0)
  const audience = list.reduce((n, s) => n + audienceFor(s.target_type), 0)
  const rate = audience ? Math.min(100, Math.round((responses / audience) * 100)) : 0
  return { responses, audience, rate }
})

function statusTag(status: SurveyStatus) {
  return status === 'open' ? 'success' : status === 'draft' ? 'info' : 'warning'
}

async function loadAll(silent = false) {
  loading.value = true
  try {
    surveys.value = await listSurveys()
  } catch {
    if (!silent) ElMessage.error('问卷列表加载失败')
  } finally {
    loading.value = false
  }
  try {
    mineResults.value = await getMySurveyResults()
  } catch {
    mineResults.value = []
  }
}

/** 下拉刷新：复用问卷列表与受众统计加载，失败不提示 */
async function refreshAll() {
  await Promise.all([loadAll(true), loadAudience()])
}

async function loadAudience() {
  try {
    teacherCount.value = (await getTeachers()).length
  } catch {
    teacherCount.value = 0
  }
  try {
    studentCount.value = (await getStudents()).length
  } catch {
    studentCount.value = 0
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

function handleJoinSizeChange() {
  joinPage.value = 1
}
function handleJoinCurrentChange() {
  joinPage.value = joinPage.value || 1
}
function handleCreatedSizeChange() {
  createdPage.value = 1
}
function handleCreatedCurrentChange() {
  createdPage.value = createdPage.value || 1
}
function handleMineSizeChange() {
  minePage.value = 1
}
function handleMineCurrentChange() {
  minePage.value = minePage.value || 1
}

onMounted(() => {
  loadAll()
  loadAudience()
})
</script>

<style scoped>
/* ---------- 移动端（定稿版·题卡）私有件 ---------- */
/* 首屏指标块与吸顶栏之间留出呼吸感，避免三个数字贴在 Header 下沿 */
.tm-m > .tm-kpis:first-child {
  margin-top: 16px;
}
.tm-sv {
  width: 100%;
  display: block;
  text-align: left;
  font-family: inherit;
  background: var(--tm-surf);
  border: 1px solid var(--tm-line);
  border-radius: 11px;
  padding: 9px 10px;
  cursor: pointer;
}
.tm-sv-done { opacity: 0.72; cursor: default; }
.tm-sv-hd { display: flex; align-items: flex-start; gap: 6px; }
.tm-sv-t {
  flex: 1;
  min-width: 0;
  font-size: 12.8px;
  font-weight: 700;
  line-height: 1.4;
  color: #16233a;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tm-sv-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.tm-sv-bar { display: flex; align-items: center; gap: 6px; margin-top: 7px; }
.tm-sv-tr { flex: 1; height: 4px; border-radius: 99px; background: #eef2f9; overflow: hidden; }
.tm-sv-tr i { display: block; height: 100%; border-radius: 99px; background: var(--tm-brand); }
.tm-sv-v { font-size: 10px; font-weight: 750; color: var(--tm-brand); font-variant-numeric: tabular-nums; }
.tm-sv-ft {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 7px;
  padding-top: 6px;
  border-top: 1px dashed var(--tm-line);
  font-size: 10.2px;
  color: var(--tm-ink3);
  font-weight: 600;
}
.tm-sv-ft > span:first-child { flex: 1; min-width: 0; }
.tm-sv-go { color: var(--tm-brand-deep); font-weight: 750; }
.tm-sv-ops { display: flex; align-items: center; gap: 9px; }
.tm-sv-ops button {
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  font-size: 10.6px;
  font-weight: 700;
  color: var(--tm-brand-deep);
  cursor: pointer;
}
.tm-sv-ops .tm-sv-danger { color: var(--tm-warn); }
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* 移动端高频操作条 */
.sv-topbar {
  margin-bottom: 12px;
}
.sv-topbar .el-button {
  flex: 1;
  margin-left: 0;
}

/* 回收率环形进度卡 */
.sv-overview {
  display: flex;
  align-items: center;
  gap: 14px;
}
.ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}
.ring::after {
  content: '';
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: var(--tui-surface);
}
.ring-mid {
  position: relative;
  z-index: 1;
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text);
}
.ring.sm {
  width: 48px;
  height: 48px;
}
.ring.sm::after {
  inset: 6px;
}
.ring.sm .ring-mid {
  font-size: 12px;
}

.sv-ov-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.sv-ov-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
}
.sv-ov-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
.sv-dims {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 5px;
}
.sv-anon {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--tui-success);
}
.sv-side {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .sv-item {
    flex-direction: column;
    align-items: stretch;
  }
  .sv-item .tui-actions {
    justify-content: flex-end;
  }
  .sv-side {
    justify-content: space-between;
  }
}

/* ================= 移动端 AI 发起入口 ================= */
.tm-ai-launch {
  display: flex;
  align-items: center;
  gap: 10px;
  width: calc(100% - 28px);
  margin: 10px 14px 4px;
  padding: 12px 13px;
  background: var(--tm-surf, #fff);
  border: 1px solid var(--tm-line, #e8eaef);
  border-radius: var(--tm-r, 14px);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.tm-ai-launch:active { background: var(--tm-surf2, #f6f7f9); }
/* 产品形象替掉原先的 MagicStick 图标块：透明底、等比缩放，不裁切吉祥物 */
.tm-ai-launch-ic {
  width: 38px; height: 38px; flex: 0 0 38px;
  object-fit: contain;
  display: block;
  border-radius: 10px;
  background: transparent;
  user-select: none;
  -webkit-user-drag: none;
}
.tm-ai-launch-bd { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.tm-ai-launch-bd b { font-size: 14.5px; font-weight: 700; color: var(--tm-ink, #171a20); }
.tm-ai-launch-bd em { font-style: normal; font-size: 12px; line-height: 1.45; color: var(--tm-ink3, #8a91a0); }
.tm-ai-launch-go {
  flex: 0 0 auto;
  padding: 6px 11px;
  border-radius: 8px;
  background: #1f2430;
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
}
</style>