﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="tui-page">
    <SubPageHeader title="心理预警工作台" fallback="/teacher">
      <template #right>
        <el-button text circle aria-label="刷新" :loading="loading" @click="loadAlerts">
          <el-icon :size="19"><Refresh /></el-icon>
        </el-button>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <!-- 桌面端特色头部：风险语义色 + 处置态势指标（移动端由 SubPageHeader 承担标题） -->
      <TuiPageHero
        v-if="!isMobile"
        title="心理预警工作台"
        sub="风险处置台：发现 → 干预 → 随访 → 闭环"
        :icon="WarningFilled"
        tone="danger"
      >
        <div class="tui-hero-metric is-accent"><b>{{ unresolved.length }}</b><span>待处置</span></div>
        <div class="tui-hero-metric"><b>{{ highRisk.length }}</b><span>高危未闭环</span></div>
        <div class="tui-hero-metric"><b>{{ followingUp }}</b><span>随访中</span></div>
        <el-button text circle aria-label="刷新" :loading="loading" @click="loadAlerts">
          <el-icon :size="18"><Refresh /></el-icon>
        </el-button>
      </TuiPageHero>

      <!-- ===================== 桌面端骨架：处置态势分析 + 三列泳道看板 =====================
           态势区块（关键指标带 / 等级分布 / 处置阶段 / 趋势 / 处置时限 / 敏感词云）
           统一交给 CrisisAnalytics 渲染（数据来自 /crisis/analytics 聚合接口），
           首屏即可读完全局态势；纵向空间让给下方的处置动作（泳道看板）。 -->
      <template v-if="!isMobile">
        <CrisisAnalytics :analytics="analytics" />

        <!-- 预警清单：三列泳道看板（待处置 / 随访中 / 已闭环） -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><List /></el-icon>预警清单</h3>
            <div class="tui-section-extra"><span class="wb-total">{{ filtered.length }} 条</span></div>
          </div>

          <!-- 筛选：沿用 filter ref 与分段控件，放在态势带之下、泳道之上 -->
          <div class="tui-seg wb-seg">
            <button type="button" class="tui-seg-item" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
            <button type="button" class="tui-seg-item" :class="{ active: filter === 'unresolved' }" @click="filter = 'unresolved'">待处置</button>
            <button type="button" class="tui-seg-item" :class="{ active: filter === 'follow_up' }" @click="filter = 'follow_up'">待随访</button>
            <button type="button" class="tui-seg-item" :class="{ active: filter === 'resolved' }" @click="filter = 'resolved'">已闭环</button>
          </div>

          <!-- 闭环：从学生详情跳来，仅看该学生的预警 -->
          <div v-if="studentFilter" class="wb-scope">
            <span class="wb-scope-text">仅看：{{ studentFilterName }}</span>
            <button type="button" class="wb-scope-clear" @click="clearStudentFilter">
              查看全部预警<el-icon :size="12"><Close /></el-icon>
            </button>
          </div>

          <div v-loading="loading" class="wb-lanes">
            <div v-for="lane in lanes" :key="lane.key" class="wb-lane" :class="`lane-${lane.key}`">
              <div class="wb-lane-head">
                <span class="wb-lane-title">{{ lane.label }}</span>
                <span class="wb-lane-count">{{ lane.items.length }}</span>
              </div>
              <div class="wb-lane-body">
                <article v-for="row in lane.items" :key="row.id" class="wb-lc" :class="`lv-${row.level}`">
                  <div class="wb-lc-head">
                    <span class="stu-avatar">{{ row.student_name.slice(0, 1) }}</span>
                    <span class="wb-lc-name">{{ row.student_name }}</span>
                    <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
                  </div>
                  <p class="wb-lc-summary tui-ellipsis-2">{{ row.summary }}</p>
                  <div class="wb-lc-meta">
                    <span>发现 {{ formatTime(row.created_at) }}</span>
                    <template v-if="row.follow_up_date">
                      <span class="tui-meta-sep">·</span>
                      <span :class="{ 'fu-due': isFollowUpDue(row) }">随访 {{ row.follow_up_date }}</span>
                    </template>
                    <template v-else>
                      <span class="tui-meta-sep">·</span>
                      <span>未排随访</span>
                    </template>
                  </div>
                  <!-- 处置时限进度：复用 deadlinePct / daysUntil 与 .tui-progress -->
                  <div v-if="row.follow_up_date && !row.resolved" class="wb-lc-dl">
                    <div class="tui-progress">
                      <div class="tui-progress-track">
                        <span
                          class="tui-progress-fill"
                          :class="daysUntil(row.follow_up_date) <= 0 ? 'is-danger' : daysUntil(row.follow_up_date) <= 3 ? 'is-warn' : ''"
                          :style="{ '--pct': deadlinePct(daysUntil(row.follow_up_date)) / 100 }"
                        />
                      </div>
                      <span class="tui-progress-text">{{ deadlineLabel(daysUntil(row.follow_up_date)) }}</span>
                    </div>
                  </div>
                  <div v-if="row.intervention_type" class="wb-lc-note">
                    <el-tag size="small" type="success" effect="light">{{ row.intervention_type }}</el-tag>
                    <span class="note-text tui-ellipsis-2">{{ row.intervention_note || '未填写备注' }}</span>
                  </div>
                  <!-- 卡片底部操作：沿用原有事件与弹窗，逻辑不变 -->
                  <div class="wb-lc-ops">
                    <el-button size="small" type="primary" :disabled="row.resolved" @click="openIntervene(row)">干预处置</el-button>
                    <el-button size="small" text type="success" :disabled="row.resolved" @click="handleResolve(row)">标记闭环</el-button>
                    <el-button size="small" text @click="gotoStudent(row)">查看档案</el-button>
                  </div>
                </article>

                <!-- 空泳道：复用 .tui-empty -->
                <div v-if="!lane.items.length" class="tui-empty wb-lane-empty">
                  <span class="tui-empty-icon"><el-icon :size="26"><WarningFilled /></el-icon></span>
                  <span class="tui-empty-title">该泳道暂无</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 分页保留在泳道下方：泳道按 paged 切片分列，翻页真实生效 -->
          <div v-if="filtered.length" class="pagination-wrapper">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50]"
              :total="filtered.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </section>
      </template>

      <!-- ===================== 移动端：态势分析 + 处置时限 + 预警清单（类名 / 顺序不变） ===================== -->
      <template v-if="isMobile">

      <!-- ① 处置态势：指标带 + 图表（移动端纵向堆叠）+ 处置时限 + 敏感词云 -->
      <CrisisAnalytics :analytics="analytics" />

      <!-- ② 处置时限：时限进度条 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><AlarmClock /></el-icon>处置时限</h3>
          <div class="tui-section-extra"><span class="wb-total">已到期 {{ followUpDue.length }} · 待随访 {{ followingUp }}</span></div>
        </div>
        <div class="tui-section-hint warn">
          <el-icon><InfoFilled /></el-icon>
          <span>按计划随访日期由近到远排序，逾期项进度条满格并以红色提示。</span>
        </div>
        <div v-if="deadlineItems.length" class="wb-deadlines">
          <div v-for="d in deadlineItems" :key="d.id" class="wb-deadline">
            <div class="wb-dl-head">
              <span class="wb-dl-name">{{ d.name }}</span>
              <span class="wb-dl-date" :class="{ 'is-due': d.days <= 0 }">{{ deadlineLabel(d.days) }} · {{ d.date }}</span>
            </div>
            <!-- 时限进度条：复用教师端统一样式构件（--pct 驱动宽度，语义色走修饰类） -->
            <div class="tui-progress">
              <div class="tui-progress-track">
                <span
                  class="tui-progress-fill"
                  :class="d.days <= 0 ? 'is-danger' : d.days <= 3 ? 'is-warn' : ''"
                  :style="{ '--pct': deadlinePct(d.days) / 100 }"
                />
              </div>
            </div>
          </div>
        </div>
        <div v-else class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="26"><AlarmClock /></el-icon></span>
          <span class="tui-empty-title">暂无待随访时限</span>
          <span class="tui-empty-desc">当前预警都未设置随访日期，或已全部闭环</span>
        </div>
      </section>

      <!-- ③ 预警清单：筛选 + 列表 + 分页 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><List /></el-icon>预警清单</h3>
          <div class="tui-section-extra"><span class="wb-total">{{ filtered.length }} 条</span></div>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>点击“干预处置”登记方式与随访计划；已闭环项不再计入待处置。</span>
        </div>

        <!-- 筛选（手写分段控件，保持 filter ref 逻辑不变） -->
        <div class="tui-seg wb-seg">
          <button type="button" class="tui-seg-item" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
          <button type="button" class="tui-seg-item" :class="{ active: filter === 'unresolved' }" @click="filter = 'unresolved'">待处置</button>
          <button type="button" class="tui-seg-item" :class="{ active: filter === 'follow_up' }" @click="filter = 'follow_up'">待随访</button>
          <button type="button" class="tui-seg-item" :class="{ active: filter === 'resolved' }" @click="filter = 'resolved'">已闭环</button>
        </div>

        <!-- 闭环：从学生详情跳来，仅看该学生的预警 -->
        <div v-if="studentFilter" class="wb-scope">
          <span class="wb-scope-text">仅看：{{ studentFilterName }}</span>
          <button type="button" class="wb-scope-clear" @click="clearStudentFilter">
            查看全部预警<el-icon :size="12"><Close /></el-icon>
          </button>
        </div>

        <!-- 移动端：卡片列表 -->
        <template v-if="isMobile">
          <div v-if="!filtered.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><WarningFilled /></el-icon></span>
            <span class="tui-empty-title">暂无预警记录</span>
            <span class="tui-empty-desc">当前筛选条件下没有预警，切换筛选或稍后刷新</span>
          </div>

          <div v-else class="tui-stack">
            <article v-for="row in paged" :key="row.id" class="tui-card wb-card" :class="`lv-${row.level}`">
              <div class="tui-row">
                <span class="stu-avatar">{{ row.student_name.slice(0, 1) }}</span>
                <span class="tui-row-main">
                  <span class="tui-row-label">{{ row.student_name }}</span>
                  <span class="wb-summary tui-ellipsis-2">{{ row.summary }}</span>
                </span>
                <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
              </div>

              <div class="wb-alert-meta tui-meta">
                <span>{{ formatTime(row.created_at) }}</span>
                <span class="tui-meta-sep">·</span>
                <el-tag :type="row.resolved ? 'success' : 'warning'" size="small" effect="plain">
                  {{ row.resolved ? '已闭环' : '待处置' }}
                </el-tag>
                <template v-if="row.follow_up_date">
                  <span class="tui-meta-sep">·</span>
                  <span :class="{ 'fu-due': isFollowUpDue(row) }">
                    随访 {{ row.follow_up_date }}{{ isFollowUpDue(row) ? ' · 已到期' : '' }}
                  </span>
                </template>
              </div>

              <div v-if="row.intervention_type" class="wb-alert-note">
                <el-tag size="small" type="success" effect="light">{{ row.intervention_type }}</el-tag>
                <span class="note-text">{{ row.intervention_note || '未填写备注' }}</span>
              </div>

              <div class="wb-alert-ops">
                <el-button size="small" type="primary" :disabled="row.resolved" @click="openIntervene(row)">
                  干预处置
                </el-button>
                <el-button size="small" text type="success" :disabled="row.resolved" @click="handleResolve(row)">标记闭环</el-button>
                <el-button size="small" text @click="gotoStudent(row)">查看档案</el-button>
              </div>
            </article>
          </div>
        </template>

        <div v-if="filtered.length" class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="filtered.length"
            :pager-count="5"
            small
            background
            layout="total, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </section>
      </template>

      <!-- 干预弹窗 -->
      <el-dialog
        v-model="dialogVisible"
        title="预警干预处置"
        :width="isMobile ? '90%' : '380px'"
        align-center
        :close-on-click-modal="false"
        class="tui-dialog"
        destroy-on-close
      >
        <div class="tui-section-hint danger">
          <el-icon><InfoFilled /></el-icon>
          <span>正在处置「{{ current?.student_name || '该学生' }}」的预警，保存后将写入处置记录并更新随访计划。</span>
        </div>
        <div v-if="current" class="wb-ctx">
          <div class="wb-ctx-head">
            <span class="stu-avatar">{{ current.student_name.slice(0, 1) }}</span>
            <span class="wb-ctx-name">{{ current.student_name }}</span>
            <el-tag :type="levelTagType(current.level)" size="small" effect="dark">{{ levelText(current.level) }}</el-tag>
            <span class="wb-ctx-time">{{ formatTime(current.created_at) }}</span>
          </div>
          <p class="wb-ctx-summary">{{ current.summary }}</p>
          <div v-if="current.keywords_matched" class="wb-ctx-kw">命中关键词：{{ current.keywords_matched }}</div>
        </div>
        <el-form v-if="current" label-width="80px">
          <el-form-item label="干预方式">
            <el-select v-model="form.intervention_type" placeholder="请选择干预方式" style="width: 100%">
              <el-option v-for="o in interventionOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
          <div class="wb-draft">
            <AiDraftField
              v-model="form.intervention_note"
              label="处置备注"
              :rows="3"
              :maxlength="300"
              placeholder="记录本次处置过程，供后续随访参考……"
              :draft="aiDraft"
              :points="aiPoints"
            />
          </div>
          <el-form-item label="随访日期">
            <el-date-picker v-model="form.follow_up_date" type="date" value-format="YYYY-MM-DD" placeholder="计划跟进时间" style="width:100%" />
          </el-form-item>
          <el-form-item label="处置结果">
            <el-switch v-model="form.resolved" active-text="已闭环" inactive-text="持续跟进" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitIntervene">保存处置</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import CrisisAnalytics from '@/components/teacher/crisis/CrisisAnalytics.vue'
import {
  Refresh,
  WarningFilled,
  Close,
  InfoFilled,
  AlarmClock,
  List,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { getAlerts, resolveAlert, interveneAlert, getCrisisAnalytics } from '@/api/crisis'
import type { CrisisAlert } from '@/types'
import type { CrisisAnalytics as CrisisAnalyticsData } from '@/api/crisis'

const { isMobile } = useResponsive()

const route = useRoute()
const router = useRouter()

const alerts = ref<CrisisAlert[]>([])
/** 聚合分析（等级分布 / 处置阶段 / 趋势 / 敏感词 / 时限），由后端 /crisis/analytics 统一计算 */
const analytics = ref<CrisisAnalyticsData | null>(null)

/** 来自学生详情的闭环参数：?student_id= 只看该学生，?alert_id= 直接打开该条处置 */
const studentFilter = computed(() => Number(route.query.student_id) || null)
const alertFilter = Number(route.query.alert_id) || 0
const studentFilterName = computed(() => {
  if (!studentFilter.value) return ''
  const hit = alerts.value.find((a) => a.student_id === studentFilter.value)
  return hit?.student_name || `学生 #${studentFilter.value}`
})

const loading = ref(false)
const filter = ref<'all' | 'unresolved' | 'follow_up' | 'resolved'>('all')

const dialogVisible = ref(false)
const current = ref<CrisisAlert | null>(null)
const submitting = ref(false)
const form = ref({
  intervention_type: '谈话',
  intervention_note: '',
  follow_up_date: '',
  resolved: true,
})

/** 干预方式下拉选项（值与提交保持一致） */
const interventionOptions = [
  { value: '谈话', label: '谈话疏导' },
  { value: '约谈家长', label: '约谈家长' },
  { value: '转介心理咨询', label: '转介心理咨询' },
  { value: '其他', label: '其他' },
]

/** 今日日期（YYYY-MM-DD）：用于 AI 草稿 */
const today = new Date().toISOString().slice(0, 10)

/** AI 建议要点：随干预方式变化 */
const aiPoints = computed(() => {
  const t = form.value.intervention_type
  if (t === '约谈家长') return ['沟通对象与时间', '家长反馈', '家庭配合措施', '后续联系安排']
  if (t === '转介心理咨询') return ['转介事由', '预警等级', '学生知情情况', '咨询师反馈跟进']
  if (t === '其他') return ['处置方式说明', '学生情绪状态', '已采取措施', '后续随访计划']
  return ['学生情绪状态', '触发事件', '已采取措施', '后续随访计划']
})

/** AI 草稿：结合所选干预方式 + 学生 + 日期，写成处置记录口吻 */
const aiDraft = computed(() => {
  const s = current.value?.student_name || '该生'
  const t = form.value.intervention_type
  if (t === '约谈家长') {
    return `${today}，就${s}近期心理预警情况与其家长电话沟通：反馈其在课堂上的情绪表现与波动，说明学校的关注与跟进安排，请家长在家多加陪伴、留意异常信号并及时反馈。家长表示理解并愿意配合，双方约定保持联系、共同关注其状态。`
  }
  if (t === '转介心理咨询') {
    return `${today}，针对${s}的预警情况填写转介单并转介学校心理咨询中心：说明其预警等级与主要表现，请咨询师尽快安排面谈。已向学生本人说明转介原因，其愿意接受；后续由我配合跟踪咨询进展并做好记录。`
  }
  if (t === '其他') {
    return `${today}，针对${s}的预警情况采取其他处置措施：先了解事情经过与当下情绪，安抚并说明可提供的支持，记录其主要表现与后续安排，约定继续关注并及时反馈。`
  }
  return `${today}，与${s}进行一对一谈话疏导：先了解其近期压力来源与情绪状态，肯定其积极面，引导其识别情绪信号并尝试简单的放松方法。谈话后其情绪较前平稳，约定保持沟通并继续关注。`
})

const unresolved = computed(() => alerts.value.filter(a => !a.resolved))
const highRisk = computed(() => alerts.value.filter(a => !a.resolved && a.level === 'severe'))
const followingUp = computed(() => alerts.value.filter(a => !a.resolved && a.follow_up_date).length)

/** 随访日期已到期且未闭环 */
function isFollowUpDue(row: CrisisAlert) {
  if (row.resolved || !row.follow_up_date) return false
  return row.follow_up_date <= new Date().toISOString().slice(0, 10)
}
const followUpDue = computed(() => alerts.value.filter(isFollowUpDue))

function daysUntil(date: string) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return Math.round((d.getTime() - today.getTime()) / 86400000)
}
function deadlineLabel(days: number) {
  if (days < 0) return `已逾期 ${-days} 天`
  if (days === 0) return '今日到期'
  return `${days} 天后`
}
function deadlinePct(days: number) {
  if (days <= 0) return 100
  return Math.max(12, Math.min(100, 100 - days * 8))
}

/** 处置时限条：未闭环且有随访日期，按到期时间由近到远 */
const deadlineItems = computed(() =>
  alerts.value
    .filter(a => !a.resolved && a.follow_up_date)
    .map(a => ({ id: a.id, name: a.student_name, date: a.follow_up_date as string, days: daysUntil(a.follow_up_date as string) }))
    .sort((x, y) => x.days - y.days)
    .slice(0, 5),
)

const filtered = computed(() => {
  const base = studentFilter.value
    ? alerts.value.filter((a) => a.student_id === studentFilter.value)
    : alerts.value
  if (filter.value === 'unresolved') return base.filter((a) => !a.resolved)
  if (filter.value === 'follow_up') return base.filter(isFollowUpDue)
  if (filter.value === 'resolved') return base.filter((a) => a.resolved)
  return base
})

/* 分页（契约第 2 节统一） */
const currentPage = ref(1)
const pageSize = ref(10)
const paged = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})
function handleSizeChange() {
  currentPage.value = 1
}
function handlePageChange() {
  /* 页码由 v-model 同步，无需额外处理 */
}
watch([filter, studentFilter], () => { currentPage.value = 1 })
watch(() => filtered.value.length, () => { currentPage.value = 1 })

/** 三列泳道看板：待处置（未闭环且未排随访）/ 随访中（未闭环且已排随访）/ 已闭环。
 *  泳道取自 paged（当前分页切片）而非全量 filtered：这样保留下方的分页仍然真实生效，
 *  避免出现「翻了页但看板没变化」的假分页；每列头部条数即当前页该列条数。 */
const lanes = computed(() => {
  const rows = paged.value
  return [
    { key: 'todo', label: '待处置', items: rows.filter((a) => !a.resolved && !a.follow_up_date) },
    { key: 'follow', label: '随访中', items: rows.filter((a) => !a.resolved && !!a.follow_up_date) },
    { key: 'closed', label: '已闭环', items: rows.filter((a) => a.resolved) },
  ]
})

/** 清除学生维度的闭环过滤，回到全部预警 */
function clearStudentFilter() {
  const q = { ...route.query }
  delete q.student_id
  delete q.alert_id
  router.replace({ path: '/teacher/crisis', query: q })
}

/** 反向闭环：从预警回到该学生的成长档案 */
function gotoStudent(row: CrisisAlert) {
  router.push({ path: '/teacher/students', query: { student: String(row.student_id) } })
}

function levelText(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度', normal: '正常' }
  return map[level] || level || '未知'
}

function levelTagType(level: string): 'danger' | 'warning' | 'info' | 'success' {
  const map: Record<string, 'danger' | 'warning' | 'info' | 'success'> = {
    severe: 'danger', moderate: 'warning', mild: 'info', normal: 'success',
  }
  return map[level] || 'info'
}

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** 聚合分析：与列表并行拉取，失败时保留上一次数据、不阻塞预警清单 */
async function loadAnalytics() {
  try {
    analytics.value = await getCrisisAnalytics()
  } catch {
    /* 静默：态势区块保持上一次数据或空态 */
  }
}

async function loadAlerts() {
  loading.value = true
  try {
    alerts.value = await getAlerts()
    // 来自学生详情的闭环：定位到具体预警并直接进入处置
    if (alertFilter) {
      const hit = alerts.value.find((a) => a.id === alertFilter)
      if (hit && !hit.resolved) openIntervene(hit)
    }
  } catch {
    ElMessage.error('预警加载失败')
  } finally {
    loading.value = false
  }
  loadAnalytics()
}

function openIntervene(row: CrisisAlert) {
  current.value = row
  form.value = {
    intervention_type: row.intervention_type || '谈话',
    intervention_note: row.intervention_note || '',
    follow_up_date: row.follow_up_date || '',
    resolved: true,
  }
  dialogVisible.value = true
}

async function submitIntervene() {
  if (!current.value) return
  submitting.value = true
  try {
    await interveneAlert(current.value.id, {
      intervention_type: form.value.intervention_type,
      intervention_note: form.value.intervention_note || undefined,
      follow_up_date: form.value.follow_up_date || undefined,
      resolved: form.value.resolved,
    })
    ElMessage.success('干预记录已保存')
    dialogVisible.value = false
    loadAlerts()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

async function handleResolve(row: CrisisAlert) {
  try {
    await ElMessageBox.confirm(`确认将「${row.student_name}」的预警标记为已闭环？`, '闭环确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await resolveAlert(row.id, true)
    ElMessage.success('已标记闭环')
    loadAlerts()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(loadAlerts)
</script>

<style scoped>
.wb-total { font-size: 11.5px; color: var(--tui-text-quiet); }

/* ===== 桌面端 三列泳道看板 ===== */
.wb-lanes {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-items: start;
}
.wb-lane {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  min-height: 120px;
  border: 1px solid var(--tui-border);
  /* 顶部一条语义色细线做状态强调：待处置=红 / 随访中=琥珀 / 已闭环=绿 */
  border-top: 3px solid var(--tui-border-strong);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
}
.wb-lane.lane-todo { border-top-color: var(--tui-danger); }
.wb-lane.lane-follow { border-top-color: var(--tui-warn); }
.wb-lane.lane-closed { border-top-color: var(--tui-success); }
.wb-lane-head { display: flex; align-items: center; gap: 7px; }
.wb-lane-title { font-size: 12.5px; font-weight: 600; color: var(--tui-text); }
.wb-lane-count {
  margin-left: auto;
  min-width: 20px;
  height: 18px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-tertiary);
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.wb-lane-body { display: flex; flex-direction: column; gap: 8px; }

/* 泳道内的小卡：左侧按等级色带 + 发丝描边 + 极轻投影 */
.wb-lc {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 9px 10px;
  border: 1px solid var(--tui-border);
  border-left: 3px solid var(--tui-border-strong);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  box-shadow: var(--tui-shadow-1);
}
.wb-lc.lv-severe { border-left-color: var(--tui-danger); }
.wb-lc.lv-moderate { border-left-color: var(--tui-warn); }
.wb-lc.lv-mild { border-left-color: var(--tui-brand); }
.wb-lc.lv-normal { border-left-color: var(--tui-success); }
.wb-lc-head { display: flex; align-items: center; gap: 7px; }
.wb-lc-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.wb-lc-head .el-tag { margin-left: auto; }
.wb-lc-summary {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--tui-text-tertiary);
}
.wb-lc-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.wb-lc-dl { margin-top: 1px; }
.wb-lc-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--tui-text-secondary);
}
.wb-lc-ops {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}
.wb-lc-ops .el-button + .el-button { margin-left: 0; }

/* 空泳道：沿用 .tui-empty，仅收紧留白，避免三列大空块压垮看板 */
.wb-lane-empty { padding: 18px 10px; gap: 6px; }
.wb-lane-empty .tui-empty-icon { width: 40px; height: 40px; }

/* ===== 处置时限：时限进度条 ===== */
.wb-deadlines { display: flex; flex-direction: column; gap: 10px; }
.wb-deadline { display: flex; flex-direction: column; gap: 5px; }
.wb-dl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.wb-dl-name { font-size: 12.5px; font-weight: 600; color: var(--tui-text); }
.wb-dl-date { font-size: 11px; color: var(--tui-text-quiet); }
.wb-dl-date.is-due { color: var(--tui-danger); font-weight: 600; }
/* ===== 预警清单 ===== */
.wb-seg { margin-bottom: 10px; }
.wb-table {
  background: var(--tui-surface);
  border-radius: var(--tui-radius-sm);
  overflow: hidden;
}
.stu-cell { display: flex; align-items: center; gap: 8px; }
.stu-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tui-brand-strong);
  font-size: 13px;
  font-weight: 600;
  background: var(--tui-brand-soft);
  flex-shrink: 0;
}
.stu-name { font-weight: 600; color: var(--tui-text); }
.note-text { font-size: 12px; color: var(--tui-text-secondary); }
.note-text.muted { color: var(--tui-text-quiet); }
.fu-due { color: var(--tui-warn); font-weight: 600; }

/* ===== 干预弹窗：上下文信息条 + AI 草稿间距 ===== */
.wb-ctx {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
}
.wb-ctx-head { display: flex; align-items: center; gap: 8px; }
.wb-ctx-name { font-weight: 600; color: var(--tui-text); }
.wb-ctx-time { margin-left: auto; font-size: 11px; color: var(--tui-text-quiet); }
.wb-ctx-summary {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-secondary);
}
.wb-ctx-kw { font-size: 11.5px; color: var(--tui-text-quiet); }
.wb-draft { margin-bottom: 14px; }

/* 移动端卡片：左侧色带等级 */
.wb-card {
  border-left-width: 3px;
  border-left-style: solid;
  border-left-color: var(--tui-border-strong);
}
.wb-card.lv-severe { border-left-color: var(--tui-danger); }
.wb-card.lv-moderate { border-left-color: var(--tui-warn); }
.wb-card.lv-mild { border-left-color: var(--tui-brand); }
.wb-card.lv-normal { border-left-color: var(--tui-success); }
.wb-summary { font-size: 12.5px; color: var(--tui-text-tertiary); line-height: 1.5; }
.wb-alert-meta { padding: 9px 13px 0; }
.wb-alert-note {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 13px 0;
  font-size: 12px;
  color: var(--tui-text-secondary);
}
.wb-alert-ops {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 10px 12px 12px 13px;
}

/* 闭环：学生维度过滤提示条 */
.wb-scope {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 0 0 10px;
  padding: 9px 12px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-brand-soft);
  font-size: 12.5px;
}
.wb-scope-text { font-weight: 600; color: var(--tui-brand-strong); }
.wb-scope-clear {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: none;
  background: transparent;
  color: var(--tui-text-secondary);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.wb-scope-clear:hover { color: var(--tui-text); }
</style>