<template>
  <div class="tui-page">
    <SubPageHeader title="心理预警工作台" sub="风险处置台 · 发现 → 干预 → 随访 → 闭环" fallback="/teacher">
      <template #right>
        <el-button text circle aria-label="刷新" :loading="loading" @click="loadAlerts">
          <el-icon :size="19"><Refresh /></el-icon>
        </el-button>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <!-- 桌面端页头（移动端由 SubPageHeader 承担标题，避免重复） -->
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">心理预警工作台</h2>
          <p class="tui-header-sub">风险处置台：发现 → 干预 → 随访 → 闭环（v3.0 实施文档 §4）</p>
        </div>
        <div class="tui-header-actions">
          <el-button type="primary" round :icon="Refresh" :loading="loading" @click="loadAlerts">刷新</el-button>
        </div>
      </header>

      <!-- ① 风险态势：分布环 + 四等级（单行排布） -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><WarningFilled /></el-icon>风险态势</h3>
          <div class="tui-section-extra"><span class="wb-total">高危未闭环 {{ highRisk.length }} · 共 {{ alerts.length }} 条</span></div>
        </div>
        <div class="tui-section-hint danger">
          <el-icon><InfoFilled /></el-icon>
          <span>一行速览：环形为待处置总量，右侧四档按等级分布（高危 / 中度 / 轻度 / 正常·其它），高危未闭环请优先处置。</span>
        </div>
        <div class="wb-situation">
          <div class="wb-ring-wrap">
            <span class="ring" :style="ringStyle"><span class="ring-mid">{{ unresolved.length }}</span></span>
            <span class="wb-ring-cap">待处置</span>
          </div>
          <div class="wb-levels">
            <div class="wb-level lv-danger">
              <span class="wb-level-num">{{ dist.severe }}</span>
              <span class="wb-level-label">高危</span>
            </div>
            <div class="wb-level lv-warn">
              <span class="wb-level-num">{{ dist.moderate }}</span>
              <span class="wb-level-label">中度</span>
            </div>
            <div class="wb-level lv-brand">
              <span class="wb-level-num">{{ dist.mild }}</span>
              <span class="wb-level-label">轻度</span>
            </div>
            <div class="wb-level lv-muted">
              <span class="wb-level-num">{{ dist.other }}</span>
              <span class="wb-level-label">正常 / 其它</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ② 闭环进度：处置步骤条 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Connection /></el-icon>闭环进度</h3>
        </div>
        <div class="tui-section-hint success">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>四步闭环：发现 → 干预 → 随访 → 闭环，下方数字为各阶段条数。</span>
        </div>
        <div class="wb-steps">
          <div v-for="s in steps" :key="s.key" class="wb-step" :class="`step-${s.key}`">
            <span class="wb-step-icon"><el-icon :size="16"><component :is="s.icon" /></el-icon></span>
            <span class="wb-step-num">{{ s.count }}</span>
            <span class="wb-step-label">{{ s.label }}</span>
          </div>
        </div>
      </section>

      <!-- ③ 处置时限：时限进度条 -->
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
            <div class="wb-dl-bar">
              <i
                :class="d.days <= 0 ? 'bar-danger' : d.days <= 3 ? 'bar-warn' : 'bar-brand'"
                :style="{ width: deadlinePct(d.days) + '%' }"
              ></i>
            </div>
          </div>
        </div>
        <div v-else class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="26"><AlarmClock /></el-icon></span>
          <span class="tui-empty-title">暂无待随访时限</span>
          <span class="tui-empty-desc">当前预警都未设置随访日期，或已全部闭环</span>
        </div>
      </section>

      <!-- ④ 预警清单：筛选 + 列表 + 分页 -->
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

        <!-- 桌面端：表格 -->
        <el-table v-if="!isMobile" v-loading="loading" :data="paged" class="wb-table">
          <el-table-column label="学生" min-width="120">
            <template #default="{ row }">
              <div class="stu-cell">
                <span class="stu-avatar">{{ row.student_name.slice(0, 1) }}</span>
                <span class="stu-name">{{ row.student_name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="等级" width="90">
            <template #default="{ row }">
              <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="预警时间" width="150">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="风险摘要" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.summary }}</template>
          </el-table-column>
          <el-table-column label="处置记录" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <template v-if="row.intervention_type">
                <el-tag size="small" type="success" effect="light" style="margin-right:4px">{{ row.intervention_type }}</el-tag>
                <span class="note-text">{{ row.intervention_note || '未填写备注' }}</span>
              </template>
              <span v-else class="note-text muted">尚未干预</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.resolved ? 'success' : 'warning'" size="small" effect="plain">
                {{ row.resolved ? '已闭环' : '待处置' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="随访" width="130">
            <template #default="{ row }">
              <template v-if="row.follow_up_date">
                <span :class="{ 'fu-due': isFollowUpDue(row) }">
                  {{ row.follow_up_date }}{{ isFollowUpDue(row) ? ' · 已到期' : '' }}
                </span>
              </template>
              <span v-else class="note-text muted">未设置</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" :disabled="row.resolved" @click="openIntervene(row)">
                干预处置
              </el-button>
              <el-button size="small" text type="success" :disabled="row.resolved" @click="handleResolve(row)">标记闭环</el-button>
              <el-button size="small" text @click="gotoStudent(row)">查看档案</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <div class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="26"><WarningFilled /></el-icon></span>
              <span class="tui-empty-title">暂无预警记录</span>
              <span class="tui-empty-desc">当前筛选条件下没有预警，切换筛选或稍后刷新</span>
            </div>
          </template>
        </el-table>

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
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import {
  Refresh,
  WarningFilled,
  Close,
  InfoFilled,
  Connection,
  CircleCheckFilled,
  AlarmClock,
  List,
  FirstAidKit,
  Calendar,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { getAlerts, resolveAlert, interveneAlert } from '@/api/crisis'
import type { CrisisAlert } from '@/types'

const { isMobile } = useResponsive()

const route = useRoute()
const router = useRouter()

const alerts = ref<CrisisAlert[]>([])

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
const intervenedCount = computed(() => alerts.value.filter(a => a.intervention_type).length)
const resolvedCount = computed(() => alerts.value.filter(a => a.resolved).length)
const followingUp = computed(() => alerts.value.filter(a => !a.resolved && a.follow_up_date).length)

/** 等级分布（驱动风险分布环 + 左侧色带等级卡） */
const dist = computed(() => {
  const severe = alerts.value.filter(a => a.level === 'severe').length
  const moderate = alerts.value.filter(a => a.level === 'moderate').length
  const mild = alerts.value.filter(a => a.level === 'mild').length
  return {
    severe,
    moderate,
    mild,
    other: alerts.value.length - severe - moderate - mild,
  }
})

/** 风险分布环：conic-gradient 纯 CSS，无新依赖 */
const ringStyle = computed(() => {
  const total = alerts.value.length || 1
  const a = (dist.value.severe / total) * 100
  const b = a + (dist.value.moderate / total) * 100
  const c = b + (dist.value.mild / total) * 100
  return {
    background: `conic-gradient(var(--tui-danger) 0 ${a}%, var(--tui-warn) ${a}% ${b}%, var(--tui-brand) ${b}% ${c}%, var(--tui-surface-sunken) ${c}% 100%)`,
  }
})

/** 处置步骤条 */
const steps = computed(() => [
  { key: 'found', label: '发现', count: alerts.value.length, icon: WarningFilled },
  { key: 'intervene', label: '干预', count: intervenedCount.value, icon: FirstAidKit },
  { key: 'follow', label: '随访', count: followingUp.value, icon: Calendar },
  { key: 'closed', label: '闭环', count: resolvedCount.value, icon: CircleCheckFilled },
])

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

/* ===== 风险态势：分布环 + 四等级「单行」排布 =====
   原实现桌面端是 2×2 网格、移动端竖排，导致整块高达 3 行；现统一压成一行：
   环形 + 4 个等宽等级卡（色带由左侧改为顶部，横向排列时更整齐）。 */
.wb-situation {
  display: flex;
  align-items: stretch;
  gap: 8px;
  flex-wrap: nowrap;
}
.wb-ring-wrap {
  flex: 0 0 62px;
  width: 62px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.ring {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.ring::after {
  content: '';
  position: absolute;
  inset: 7px;
  border-radius: 50%;
  background: var(--tui-surface);
}
.ring-mid {
  position: relative;
  z-index: 1;
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text);
}
.wb-ring-cap { font-size: 10px; color: var(--tui-text-quiet); white-space: nowrap; }

.wb-levels {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}
.wb-level {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  min-width: 0;
  padding: 8px 4px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  border-top: 3px solid var(--tui-border-strong);
}
.wb-level.lv-danger { border-top-color: var(--tui-danger); background: var(--tui-danger-soft); }
.wb-level.lv-warn { border-top-color: var(--tui-warn); background: var(--tui-warn-soft); }
.wb-level.lv-brand { border-top-color: var(--tui-brand); background: var(--tui-brand-soft); }
.wb-level.lv-muted { border-top-color: var(--tui-border-strong); }
.wb-level-num {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.wb-level-label {
  font-size: 10.5px;
  line-height: 1.2;
  color: var(--tui-text-tertiary);
  white-space: nowrap;
}

/* ===== 闭环进度：处置步骤条 ===== */
.wb-steps { display: flex; align-items: flex-start; }
.wb-step {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}
.wb-step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 15px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: var(--tui-border-strong);
  z-index: 0;
}
.wb-step-icon {
  position: relative;
  z-index: 1;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.wb-step.step-found .wb-step-icon { background: var(--tui-danger-soft); color: var(--tui-danger); }
.wb-step.step-intervene .wb-step-icon { background: var(--tui-warn-soft); color: var(--tui-warn); }
.wb-step.step-follow .wb-step-icon { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.wb-step.step-closed .wb-step-icon { background: var(--tui-success-soft); color: var(--tui-success); }
.wb-step-num {
  font-size: 15px;
  font-weight: 700;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.wb-step-label { font-size: 11px; color: var(--tui-text-quiet); }

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
.wb-dl-bar {
  height: 6px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.wb-dl-bar > i { display: block; height: 100%; border-radius: 999px; }
.bar-danger { background: var(--tui-danger); }
.bar-warn { background: var(--tui-warn); }
.bar-brand { background: var(--tui-brand); }

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

@media (max-width: 767px) {
  /* 风险态势保持「一行」：只收紧间距与尺寸，不再竖排堆叠 */
  .wb-situation { gap: 6px; }
  .wb-ring-wrap { flex: 0 0 52px; width: 52px; }
  .ring { width: 48px; height: 48px; }
  .ring::after { inset: 6px; }
  .ring-mid { font-size: 14px; }
  .wb-levels { gap: 4px; }
  .wb-level { padding: 7px 2px; }
  .wb-level-num { font-size: 15px; }
  .wb-level-label { font-size: 10px; }
  .wb-alert-meta { padding: 9px 13px 0; }
}
</style>