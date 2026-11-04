<template>
  <div
    class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="AI 主动洞察" fallback="/teacher" />
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <!-- ============================================================
         移动端 · 顺序阅读版（冷色调）
         一次性读取全部数据 → 结论条 → 四项指标 → 主动发现 → 推荐联系
         两个分区同屏顺序铺开，无分段切换，内容全部加载后统一呈现
         ============================================================ -->
    <div v-if="isMobile" class="tm-page tm-m">
      <div class="tm-ai-strip">
        <div class="tm-ai-hd">
          <span class="tm-ai-mk"><AiMascotMark :size="16" /></span>
          <span class="tm-ai-lb">AI 主动发现</span>
          <span class="tm-ai-time">基于 7 天数据</span>
        </div>
        <p>
          今天有 <b>{{ shownSuggestions.length }} 个学生</b>值得你主动联系，理由和证据都写好了；
          另有 <b>{{ shownActions.length }} 条</b>主动发现，其中 <b>{{ highCount }} 条</b>是高危。
        </p>
      </div>

      <div class="tm-kpis">
        <div class="tm-kpi" :class="{ 'tm-bad': highCount > 0 }">
          <b>{{ shownActions.length }}</b><span>主动发现</span>
        </div>
        <div class="tm-kpi tm-bad"><b>{{ highCount }}</b><span>高危信号</span></div>
        <div class="tm-kpi"><b>{{ shownSuggestions.length }}</b><span>建议联系</span></div>
        <div class="tm-kpi"><b>{{ studentCoverage }}</b><span>涉及学生</span></div>
      </div>

      <div v-if="studentFocus" class="tm-focus">
        <span class="tm-focus-t">已聚焦「{{ studentFocus.name || '该生' }}」，只显示与其相关的发现</span>
        <button type="button" @click="clearStudentFocus">清除</button>
      </div>

      <!-- 全部数据到位后一次性渲染两个分区，避免「只加载一部分」的观感 -->
      <AgentLoading v-if="loading" block :tips="AI_TIPS" />

      <template v-else>
        <div class="tm-blk-sec">
          <b>主动发现</b>
          <span class="tm-blk-n">{{ shownActions.length }} 条</span>
        </div>

        <div v-if="!shownActions.length" class="tm-empty">
          <b>暂无新发现</b>
          <span>班级状态平稳，出现异常信号时这里会自动生成建议</span>
        </div>
        <div
          v-for="act in shownActions"
          :key="`${act.trigger}-${act.student_id}`"
          class="tm-ob-card"
          @click="gotoCrisis(act)"
        >
          <div class="tm-ob-hd">
            <span class="tm-ava">{{ triggerMark(act) }}</span>
            <div style="min-width: 0">
              <div class="tm-ob-nm">{{ act.title }}</div>
              <div class="tm-ob-why">{{ triggerLabel(act.trigger) }} · 学生 #{{ act.student_id }}</div>
            </div>
            <span class="tm-tag" :class="priorityTagCls(act.priority)">{{ priorityText(act.priority) }}</span>
          </div>
          <div class="tm-ob-q">
            <span class="tm-qtx">{{ act.content }}</span>
            <em>AI 依据 · 置信度 {{ act.priority }}%</em>
          </div>
          <div class="tm-ob-evi">
            <span class="tm-evi">置信度 <b>{{ act.priority }}%</b></span>
            <span class="tm-evi">{{ triggerLabel(act.trigger) }}</span>
          </div>
          <div class="tm-ob-ft">
            <button class="tm-ai-a tm-pri" type="button" @click.stop="gotoCrisis(act)">去预警中心处理</button>
            <button class="tm-ai-a" type="button" @click.stop="gotoStudent(act.student_id)">看他档案</button>
            <span class="tm-ob-x">点卡片进入处置</span>
          </div>
        </div>

        <div class="tm-blk-sec">
          <b>推荐联系</b>
          <span class="tm-blk-n">{{ shownSuggestions.length }} 位</span>
          <button
            class="tm-ai-a"
            type="button"
            :disabled="!shownSuggestions.length || batchLoading"
            @click="convertAll"
          >{{ batchLoading ? '正在写入…' : '全部转为跟进' }}</button>
        </div>

        <div v-if="!shownSuggestions.length" class="tm-empty">
          <b>暂无推荐联系对象</b>
          <span>有需要关注的学生时，这里会给出推荐对象与理由</span>
        </div>
        <div v-for="c in shownSuggestions" :key="c.student_id" class="tm-ob-card">
          <div class="tm-ob-hd">
            <span class="tm-ava">{{ c.student_name.slice(0, 1) }}</span>
            <div style="min-width: 0">
              <div class="tm-ob-nm">{{ c.student_name }}</div>
              <div class="tm-ob-why">{{ c.reason }}</div>
            </div>
            <span class="tm-tag" :class="priorityTagCls(contactConfidence(c.priority))">
              {{ contactText(c.priority) }}
            </span>
          </div>
          <div class="tm-ob-evi">
            <span class="tm-evi">建议强度 <b>{{ contactConfidence(c.priority) }}%</b></span>
            <span class="tm-evi">理由 <b>{{ c.reason.slice(0, 8) }}</b></span>
          </div>
          <div class="tm-ob-ft">
            <button
              class="tm-ai-a"
              :class="{ 'tm-pri': !convertedIds.has(c.student_id) }"
              type="button"
              :disabled="convertedIds.has(c.student_id) || loadingIds.has(c.student_id)"
              @click="convert(c)"
            >
              {{ convertedIds.has(c.student_id) ? '已加入今日待办' : loadingIds.has(c.student_id) ? '处理中…' : '采纳，加入今天' }}
            </button>
            <button class="tm-ai-a" type="button" @click="gotoStudent(c.student_id)">看他档案</button>
            <span class="tm-ob-x">{{ contactText(c.priority) }}</span>
          </div>
        </div>
      </template>

      <div class="tm-tail">
        <span>依据：预警等级 · 联系间隔 · 成绩斜率 · 出勤变化，四项加权；两部分内容已一次性全部加载</span>
      </div>
    </div>

    <div v-else class="tui-content">
      <!-- 桌面端特色头部：洞察语义色 + 数据分析图标。
           本页下方「洞察指标」网格已承载四项指标，头部不重复挂数字。 -->
      <TuiPageHero
        v-if="!isMobile"
        title="AI 主动洞察"
        sub="绵小城为你整理的班级信号与建议联系对象，逐条处置后即转为跟进任务"
        :icon="DataAnalysis"
        tone="violet"
      />

      <!-- 洞察指标网格 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><DataAnalysis /></el-icon>洞察指标</h3>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>基于当前已加载的主动发现与建议联系实时统计，聚焦某个学生时指标会随之收敛。</span>
        </div>
        <div class="ai-metrics">
          <div class="ai-metric">
            <span class="ai-metric-num" :class="{ 'is-alert': highCount > 0 }">{{ shownActions.length }}</span>
            <span class="ai-metric-label">主动发现</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-num is-alert">{{ highCount }}</span>
            <span class="ai-metric-label">高危信号</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-num">{{ shownSuggestions.length }}</span>
            <span class="ai-metric-label">建议联系</span>
          </div>
          <div class="ai-metric">
            <span class="ai-metric-num">{{ studentCoverage }}</span>
            <span class="ai-metric-label">涉及学生</span>
          </div>
        </div>
      </section>

      <!-- 周报卡 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Calendar /></el-icon>本周洞察周报</h3>
          <div class="tui-section-extra"><span class="ai-count">{{ weekRange }}</span></div>
        </div>
        <div class="tui-section-hint success">
          <el-icon><InfoFilled /></el-icon>
          <span>周报完全由当前洞察数据汇总生成，帮你快速回顾本周班级整体状态。</span>
        </div>
        <p class="ai-weekly">
          本周共梳理 <b>{{ shownActions.length }}</b> 条主动发现，其中 <b>{{ highCount }}</b> 条为高危信号；
          建议优先联系 <b>{{ shownSuggestions.length }}</b> 位学生，已转为跟进 <b>{{ convertedCount }}</b> 位。
        </p>
      </section>

      <!-- 闭环：从学生成长档案聚焦该生建议 -->
      <div v-if="studentFocus" class="ai-focus">
        <el-icon :size="14"><User /></el-icon>
        <span class="ai-focus-text">已聚焦学生「{{ studentFocus.name || '该生' }}」，仅显示与其相关的发现与建议</span>
        <button class="ai-focus-clear" type="button" @click="clearStudentFocus">清除聚焦</button>
      </div>

      <TuiSegmented v-model="tab" class="ai-seg" :options="segOptions" />

      <!-- 载入态沿用智能体那套反馈：打点 + 轮换文案，取数期间不留空白也不套遮罩 -->
      <div class="ai-body">
        <AgentLoading v-if="loading" block :tips="AI_TIPS" />
        <template v-else>
        <!-- 主动发现：AI 建议卡（置信度进度条） -->
        <section v-if="tab === 'proactive'" class="tui-section">
          <div class="tui-section-head">
            <h3><AiMascotMark :size="16" />AI 建议</h3>
            <div class="tui-section-extra"><span class="ai-count">{{ shownActions.length }} 条</span></div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>置信度由后端信号强度换算，越高越应优先处置；点击卡片直达预警中心处理该生。</span>
          </div>
          <div v-if="!loading && !shownActions.length" class="tui-empty">
            <span class="tui-empty-icon"><AiMascotMark :size="26" /></span>
            <span class="tui-empty-title">暂无新发现</span>
            <span class="tui-empty-desc">班级状态平稳，出现异常信号时这里会自动生成建议</span>
          </div>
          <div v-else class="ai-cards">
            <button
              v-for="act in shownActions"
              :key="`${act.trigger}-${act.student_id}`"
              class="ai-card is-clickable"
              type="button"
              @click="gotoCrisis(act)"
            >
              <div class="ai-card-head">
                <span class="ai-card-title">{{ act.title }}</span>
                <span class="ai-flag" :class="`is-${priorityKey(act.priority)}`">{{ priorityText(act.priority) }}</span>
              </div>
              <div class="ai-card-desc is-clamp">{{ act.content }}</div>
              <div class="ai-conf">
                <span class="ai-conf-label">置信度</span>
                <span class="ai-conf-track">
                  <span class="ai-conf-fill" :class="`is-${priorityKey(act.priority)}`" :style="{ width: act.priority + '%' }" />
                </span>
                <span class="ai-conf-num">{{ act.priority }}%</span>
                <el-icon class="ai-arrow" :size="13"><ArrowRight /></el-icon>
              </div>
            </button>
          </div>
        </section>

        <!-- 推荐联系 -->
        <section v-else class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><User /></el-icon>建议联系</h3>
            <div class="tui-section-extra">
              <span class="ai-count">{{ shownSuggestions.length }} 位</span>
              <el-button
                size="small"
                round
                type="primary"
                :loading="batchLoading"
                :disabled="!shownSuggestions.length"
                @click="convertAll"
              >全部转为跟进</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>建议强度由后端优先级换算；「转为跟进」会在待办任务中生成联系人任务，重复点击不会重复创建。</span>
          </div>
          <div v-if="!loading && !shownSuggestions.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><User /></el-icon></span>
            <span class="tui-empty-title">暂无推荐联系对象</span>
            <span class="tui-empty-desc">有需要关注的学生时，这里会给出推荐联系对象与理由</span>
          </div>
          <div v-else class="ai-cards">
            <div v-for="c in shownSuggestions" :key="c.student_id" class="ai-card is-static">
              <span class="ai-avatar">{{ c.student_name.slice(0, 1) }}</span>
              <div class="ai-card-body">
                <div class="ai-card-head">
                  <button class="ai-name-link" type="button" @click="gotoStudent(c.student_id)">
                    {{ c.student_name }}
                  </button>
                  <span class="ai-flag" :class="`is-${contactKey(c.priority)}`">{{ contactText(c.priority) }}</span>
                </div>
                <div class="ai-card-desc is-clamp">{{ c.reason }}</div>
                <div class="ai-conf">
                  <span class="ai-conf-label">建议强度</span>
                  <span class="ai-conf-track">
                    <span class="ai-conf-fill" :class="`is-${contactKey(c.priority)}`" :style="{ width: contactConfidence(c.priority) + '%' }" />
                  </span>
                  <span class="ai-conf-num">{{ contactConfidence(c.priority) }}%</span>
                  <button
                    class="ai-row-op"
                    type="button"
                    :disabled="convertedIds.has(c.student_id) || loadingIds.has(c.student_id)"
                    @click="convert(c)"
                  >
                    {{ convertedIds.has(c.student_id) ? '已跟进' : loadingIds.has(c.student_id) ? '处理中' : '转为跟进' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Calendar, DataAnalysis, InfoFilled, User } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import AiMascotMark from '@/components/teacher/ui/AiMascotMark.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { useResponsive } from '@/composables/useResponsive'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'
import { suggestContacts, persistContactSuggestions, type ContactSuggestion } from '@/api/teacher'

defineOptions({ name: 'teacher-ai-insights' })

const router = useRouter()
const route = useRoute()
const { isMobile } = useResponsive()

/** 移动端下拉刷新：手动刷新按钮已移除，统一由下拉手势触发 */
const pull = usePullRefresh(load, { enabled: () => isMobile.value })

const loading = ref(false)

/** 加载文案：说清「在读什么」，比一句「加载中」有用 */
const AI_TIPS = [
  '正在读取最近的预警与成长记录',
  '正在筛出值得先聊的学生',
  '正在整理建议与理由',
]
const proactiveActions = ref<ProactiveAction[]>([])
const contactSuggestions = ref<ContactSuggestion[]>([])

/** 闭环：从学生成长档案跳来时聚焦该生 */
const studentFocus = ref<{ id: number; name: string } | null>(null)

function matchesFocus(id?: number | null, name?: string | null) {
  const f = studentFocus.value
  if (!f) return true
  if (f.id && id != null) return id === f.id
  if (f.name && name) return name === f.name
  return true
}

const shownActions = computed(() =>
  studentFocus.value ? proactiveActions.value.filter((a) => matchesFocus(a.student_id)) : proactiveActions.value
)
const shownSuggestions = computed(() =>
  studentFocus.value ? contactSuggestions.value.filter((c) => matchesFocus(c.student_id, c.student_name)) : contactSuggestions.value
)

const tab = ref<'proactive' | 'followup'>('proactive')

const segOptions = computed(() => [
  { value: 'proactive', label: '主动发现', count: shownActions.value.length },
  { value: 'followup', label: '推荐联系', count: shownSuggestions.value.length },
])

const highCount = computed(() => shownActions.value.filter((x) => x.priority >= 80).length)

/** 已转为跟进的学生 id（本地即时反馈，避免重复点击） */
const convertedIds = ref<Set<number>>(new Set())
const loadingIds = ref<Set<number>>(new Set())
const batchLoading = ref(false)

/** 洞察指标网格：涉及学生去重数 */
const studentCoverage = computed(() => {
  const ids = new Set<number>()
  shownActions.value.forEach((a) => ids.add(a.student_id))
  shownSuggestions.value.forEach((c) => ids.add(c.student_id))
  return ids.size
})

/** 周报：本周（周一至今）区间文案 */
const weekRange = computed(() => {
  const now = new Date()
  const mon = new Date(now)
  mon.setDate(now.getDate() - ((now.getDay() + 6) % 7))
  const fmt = (d: Date) => `${d.getMonth() + 1}.${d.getDate()}`
  return `${fmt(mon)} - ${fmt(now)}`
})

const convertedCount = computed(() => convertedIds.value.size)

async function load() {
  loading.value = true
  try {
    const sid = studentFocus.value?.id || undefined
    const [acts, contacts] = await Promise.all([
      fetchProactiveActions(sid).catch(() => [] as ProactiveAction[]),
      suggestContacts(sid).catch(() => [] as ContactSuggestion[]),
    ])
    proactiveActions.value = acts
    contactSuggestions.value = contacts
  } finally {
    loading.value = false
  }
}

async function convert(c: ContactSuggestion) {
  if (convertedIds.value.has(c.student_id)) return
  loadingIds.value.add(c.student_id)
  try {
    const res = await persistContactSuggestions([c])
    convertedIds.value.add(c.student_id)
    ElMessage.success(res.created > 0 ? '已转为跟进任务' : '该学生已在跟进中')
  } catch {
    ElMessage.error('转为跟进失败')
  } finally {
    loadingIds.value.delete(c.student_id)
  }
}

async function convertAll() {
  batchLoading.value = true
  try {
    const res = await persistContactSuggestions(shownSuggestions.value)
    shownSuggestions.value.forEach((c) => convertedIds.value.add(c.student_id))
    ElMessage.success(res.created > 0 ? `已转为跟进任务 ${res.created} 条` : '推荐学生均已在跟进中')
  } catch {
    ElMessage.error('批量转为跟进失败')
  } finally {
    batchLoading.value = false
  }
}

/** 闭环出口：主动发现 → 预警中心（带该生上下文） */
function gotoCrisis(act: ProactiveAction) {
  router.push({ path: '/teacher/crisis', query: { student_id: String(act.student_id) } })
}

/** 闭环出口：推荐联系 → 该生成长档案 */
function gotoStudent(id: number) {
  router.push({ path: '/teacher/students', query: { student: String(id) } })
}

function clearStudentFocus() {
  studentFocus.value = null
  router.replace({ path: '/teacher/ai' })
}

function priorityKey(p: number) {
  if (p >= 80) return 'high'
  if (p >= 60) return 'mid'
  return 'low'
}
/** 移动端：中文标签色（对应 tm-tag 的语义类） */
function priorityTagCls(p: number) {
  if (p >= 80) return 'tm-bad'
  if (p >= 60) return 'tm-warn'
  return 'tm-ai'
}
/** 移动端：主动发现卡左侧的图标字 */
function triggerMark(act: ProactiveAction) {
  const t = triggerLabel(act.trigger)
  return t.slice(0, 1)
}
/** 移动端：触发器 → 人话 */
function triggerLabel(trigger: string) {
  const map: Record<string, string> = {
    crisis: '危机预警',
    absence: '缺勤',
    grade: '成绩下滑',
    leave: '请假异常',
    care: '关怀超期',
    task: '任务逾期',
    score: '综合评分',
  }
  return map[trigger] || trigger || '综合信号'
}
function priorityText(p: number) {
  if (p >= 80) return '高危'
  if (p >= 60) return '关注'
  return '提醒'
}
function contactKey(p: string) {
  if (p === 'high') return 'high'
  if (p === 'medium') return 'mid'
  return 'low'
}
function contactText(p: string) {
  if (p === 'high') return '建议尽快'
  if (p === 'medium') return '建议关注'
  return '保持联系'
}
/** 建议联系强度：由优先级换算，用于进度条展示 */
function contactConfidence(p: string) {
  if (p === 'high') return 90
  if (p === 'medium') return 70
  return 50
}

onMounted(() => {
  // 闭环：解析学生成长档案传来的聚焦参数
  const sid = Number(route.query.student_id)
  const sname = route.query.student_name ? String(route.query.student_name) : ''
  if (sid || sname) studentFocus.value = { id: sid || 0, name: sname }
  load().then(() => {
    // 聚焦该生时，若其无主动发现但有联系建议，自动切到「推荐联系」
    if (studentFocus.value && !shownActions.value.length && shownSuggestions.value.length) {
      tab.value = 'followup'
    }
  })
})
</script>

<style scoped>
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* ---------- 移动端（定稿版）：只补几处本页私有件 ---------- */
.tm-m { min-height: calc(100vh - 60px); }
.tm-focus {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 14px 9px;
  padding: 7px 10px;
  border-radius: 9px;
  border: 1px dashed var(--tm-ai-line);
  background: var(--tm-ai-btn);
  font-size: 10.5px;
  color: var(--tm-ai-act-ink);
  font-weight: 650;
}
.tm-focus .tm-focus-t { flex: 1; min-width: 0; }
.tm-focus button {
  flex: 0 0 auto;
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  font-size: 10.5px;
  font-weight: 750;
  color: var(--tm-ai-act-ink);
  text-decoration: underline;
}
/* 分区标题：主动发现 / 推荐联系 顺序铺开，右侧挂数量与批量操作 */
.tm-blk-sec {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 15px 14px 8px;
}
.tm-blk-sec b {
  font-family: var(--tm-serif);
  font-size: 13.4px;
  font-weight: 700;
  letter-spacing: -.1px;
  color: #2a3a55;
}
.tm-blk-sec .tm-blk-n {
  font-size: 10.4px;
  font-weight: 650;
  color: var(--tm-ink3);
  background: var(--tm-tint-neutral);
  border-radius: 5px;
  padding: 1px 6px;
}
.tm-blk-sec .tm-ai-a { margin-left: auto; }
.tm-empty {
  margin: 0 14px;
  padding: 18px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  border-radius: var(--tm-r);
  border: 1px dashed var(--tm-line2);
  background: var(--tm-surf);
  text-align: center;
}
.tm-empty b { font-size: 12px; color: var(--tm-ink2); font-weight: 700; }
.tm-empty span { font-size: 10px; color: var(--tm-ink3); line-height: 1.5; }
.tm-tail {
  padding: 9px 16px 14px;
  font-size: 9.4px;
  line-height: 1.5;
  color: var(--tm-ink3);
}
.ai-seg { margin-bottom: 12px; }
.ai-count { font-size: 11.5px; color: var(--tui-text-quiet); }

/* 洞察指标网格 */
.ai-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.ai-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 10px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
}
.ai-metric-num {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.ai-metric-num.is-alert { color: var(--tui-danger); }
.ai-metric-label { font-size: 11px; color: var(--tui-text-quiet); }

/* 周报卡 */
.ai-weekly {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--tui-text-secondary);
}
.ai-weekly b { color: var(--tui-brand-strong); font-weight: 700; }

/* 闭环聚焦条：从学生成长档案跳来时的上下文提示 */
.ai-focus {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  margin-bottom: 10px;
  border-radius: 9px;
  background: var(--tui-brand-soft);
  border: 1px solid var(--tui-border);
  color: var(--tui-brand-strong);
  font-size: 12px;
}
.ai-focus-text { flex: 1; min-width: 0; font-weight: 500; }
.ai-focus-clear {
  flex-shrink: 0;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-brand-strong);
  cursor: pointer;
}
.ai-focus-clear:hover { text-decoration: underline; }

.ai-body { min-height: 92px; }

/* AI 建议卡 */
.ai-cards { display: flex; flex-direction: column; gap: 8px; }
.ai-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  font-family: inherit;
  text-align: left;
}
.ai-card.is-clickable { cursor: pointer; }
.ai-card.is-clickable:hover { border-color: var(--tui-border-strong); }
.ai-card-body { flex: 1; min-width: 0; }

.ai-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  margin-bottom: 3px;
}
.ai-card-title {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-card-desc {
  font-size: 12px;
  color: var(--tui-text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-card-desc.is-clamp {
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 置信度进度条 */
.ai-conf {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 8px;
}
.ai-conf-label { flex-shrink: 0; font-size: 11px; color: var(--tui-text-quiet); }
.ai-conf-track {
  flex: 1;
  min-width: 0;
  height: 6px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.ai-conf-fill { display: block; height: 100%; border-radius: 999px; }
.ai-conf-fill.is-high { background: var(--tui-danger); }
.ai-conf-fill.is-mid { background: var(--tui-warn); }
.ai-conf-fill.is-low { background: var(--tui-brand); }
.ai-conf-num {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--tui-text-tertiary);
  font-variant-numeric: tabular-nums;
}

.ai-avatar {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-size: 13px;
  font-weight: 600;
}

.ai-name-link {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  padding: 0;
  text-align: left;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-name-link:hover { color: var(--tui-brand-strong); }

.ai-flag {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
}
.ai-flag.is-high { background: var(--tui-danger-soft); color: var(--tui-danger); }
.ai-flag.is-mid { background: var(--tui-warn-soft); color: var(--tui-warn); }
.ai-flag.is-low { background: var(--tui-surface-sunken); color: var(--tui-text-tertiary); }

.ai-arrow { flex-shrink: 0; color: var(--tui-text-quiet); }

.ai-row-op {
  flex-shrink: 0;
  padding: 3px 10px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 999px;
  background: var(--tui-surface);
  color: var(--tui-brand-strong);
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.ai-row-op:hover:not(:disabled) { background: var(--tui-brand-soft); }
.ai-row-op:disabled {
  border-color: var(--tui-border);
  color: var(--tui-text-quiet);
  cursor: default;
}
</style>