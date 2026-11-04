<template>
  <div class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel">
    <SubPageHeader
      title="学生成长档案"
      fallback="/teacher"
    />

    <!-- 移动端下拉刷新：指示器插在吸顶栏之后 -->
    <PullRefreshIndicator v-if="isMobile" :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <div class="tui-content">
      <!-- 桌面端特色头部：档案语义色 + 收藏图标；右侧保留本页专属的导出与建档入口 -->
      <TuiPageHero
        v-if="!isMobile"
        title="学生成长档案"
        sub="选择学生查看其成长徽章与成长轨迹，同步维护你的育人档案"
        :icon="Collection"
        tone="violet"
      >
        <div class="tui-hero-metric is-accent"><b>{{ students.length }}</b><span>名下学生</span></div>
        <el-button round :icon="Printer" :loading="reportLoading" @click="openReport">成长报告</el-button>
        <el-button size="small" :icon="Plus" @click="openCreate">新增档案</el-button>
      </TuiPageHero>

      <!-- 移动端高频操作 -->
      <div v-if="isMobile" class="tui-actions pf-topbar">
        <el-button round :icon="Printer" :loading="reportLoading" @click="openReport">成长报告</el-button>
        <el-button size="small" :icon="Plus" @click="openCreate">新增档案</el-button>
      </div>

      <!-- 1. 学生横向选择器 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><User /></el-icon>学生横向选择器</h3>
          <span class="tui-section-extra tui-text-quiet">共 {{ students.length }} 人</span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>左右滑动选择学生，下方徽章墙与成长时间轴会随之切换。</span>
        </div>
        <div v-if="studentsLoading" class="tui-empty">
          <AgentLoading block :tips="['正在读取学生名单', '正在整理成果与人像']" />
        </div>
        <div v-else-if="!students.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><User /></el-icon></span>
          <span class="tui-empty-title">暂无可查看的学生</span>
          <span class="tui-empty-desc">当前账号名下还没有学生，先到「学生管理」导入名单后再查看。</span>
        </div>
        <div v-else class="pf-rail">
          <button
            v-for="s in students"
            :key="s.id"
            type="button"
            class="pf-stu"
            :class="{ active: s.id === activeStudentId }"
            @click="selectStudent(s.id)"
          >
            <span class="pf-stu-avatar">{{ s.name.slice(0, 1) }}</span>
            <span class="pf-stu-name">{{ s.name }}</span>
          </button>
        </div>
      </section>

      <!-- ============================================================
           移动端 · 定稿版「能力条 + 成果轨道」
           桌面端的徽章墙与时间轴在移动端由这一块替代（下方两节对移动端隐藏），
           避免同一份数据在手机上出现两遍。
           条形全部来自真实字段，且刻度是「全班最高值」，竖线是「全班均值」——
           后端没有五维能力打分，不编造维度分。
           ============================================================ -->
      <div v-if="isMobile && activeStudent" class="tm-page">
        <div class="tm-pp-line">
          <span class="tm-pl-t">指标条</span>
          <span class="tm-pl-c">竖线 = 全班均值 · 满格 = 全班最高</span>
        </div>
        <div class="tm-cap">
          <div v-for="c in capBars" :key="c.label" class="tm-cap-i">
            <span class="tm-cap-n">{{ c.label }}</span>
            <div class="tm-cap-b">
              <i :style="{ width: c.pct + '%' }"></i>
              <em :style="{ left: c.avgPct + '%' }"></em>
            </div>
            <span class="tm-cap-v">{{ c.value }}</span>
          </div>
        </div>

        <div class="tm-pp-line">
          <span class="tm-pl-t">成果轨道</span>
          <span class="tm-pl-c">{{ timeline.length }} 条 · 按时间倒序</span>
        </div>
        <div v-if="growthLoading" class="tm-empty">正在读取成长轨迹…</div>
        <div v-else-if="timeline.length" class="tm-trk">
          <div
            v-for="r in timeline"
            :key="r.id"
            class="tm-trk-i"
            :style="{ '--tm-tc': recordColor(r.type) }"
          >
            <div class="tm-trk-y">{{ r.date }}</div>
            <div class="tm-trk-t">
              <span class="tm-tag tm-brand">{{ RECORD_META[r.type].label }}</span>{{ r.title }}
            </div>
            <div v-if="r.description" class="tm-trk-s">{{ r.description }}</div>
          </div>
        </div>
        <div v-else class="tm-empty">这位学生还没有成长记录</div>

        <div class="tm-tail">
          <b>数据来自：</b>成长记录（荣誉 / 竞赛 / 实践 / 论文 / 成果）· 学生技能与评分 ·
          全班同名指标的最高值与均值
        </div>
      </div>

      <!-- 2. 徽章墙 -->
      <section v-if="!isMobile" class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Medal /></el-icon>成长徽章墙</h3>
          <span v-if="activeStudent" class="tui-section-extra">
            <el-tag
              :type="activeStudent.crisis_level ? 'danger' : 'success'"
              size="small"
              effect="plain"
              round
            >
              {{ activeStudent.crisis_level ? '心理关注' : '状态平稳' }}
            </el-tag>
          </span>
        </div>
        <div class="tui-section-hint success">
          <el-icon><InfoFilled /></el-icon>
          <span>徽章由学生档案自动派生（成长记录 / 技能 / 兴趣 / 综合评分），无需手工维护。</span>
        </div>
        <div v-if="!activeStudent" class="tui-empty">
          <span class="tui-empty-title">请先选择一名学生</span>
          <span class="tui-empty-desc">在上方选择学生后，这里会展示其成长徽章。</span>
        </div>
        <div v-else class="pf-badges">
          <div v-for="b in badges" :key="b.key" class="pf-badge" :class="b.tone">
            <el-icon :size="16"><component :is="b.icon" /></el-icon>
            <span class="pf-badge-num">{{ b.value }}</span>
            <span class="pf-badge-lb">{{ b.label }}</span>
          </div>
        </div>
      </section>

      <!-- 3. 成长时间轴（移动端由上面的「成果轨道」承担） -->
      <section v-if="!isMobile" class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Clock /></el-icon>成长时间轴</h3>
          <span v-if="activeStudent" class="tui-section-extra tui-text-quiet">{{ activeStudent.name }}</span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>汇总该学生的荣誉、竞赛、实践、论文与成果记录，按时间倒序排列。</span>
        </div>
        <div v-if="!activeStudent" class="tui-empty">
          <span class="tui-empty-title">暂无学生上下文</span>
          <span class="tui-empty-desc">选择学生后即可查看其成长轨迹。</span>
        </div>
        <div v-else-if="growthLoading" class="tui-empty">
          <AgentLoading block :tips="['正在读取成长轨迹', '正在按时间排好记录']" />
        </div>
        <div v-else-if="!timeline.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><Clock /></el-icon></span>
          <span class="tui-empty-title">{{ activeStudent.name }} 暂无成长记录</span>
          <span class="tui-empty-desc">学生端录入荣誉 / 竞赛 / 实践后，会在这里自动汇总成时间轴。</span>
        </div>
        <div v-else class="tl">
          <div v-for="r in timeline" :key="r.id" class="tl-item">
            <span class="tl-node"><el-icon :size="11"><component :is="RECORD_META[r.type].icon" /></el-icon></span>
            <div class="tl-body">
              <div class="tl-top">
                <span class="tui-chip tui-chip-brand">{{ RECORD_META[r.type].label }}</span>
                <span class="tl-date">{{ r.date }}</span>
              </div>
              <div class="tl-title">{{ r.title }}</div>
              <p v-if="r.description" class="tl-desc">{{ r.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <PortfolioItemDialog v-model="dialogVisible" :item="editing" />

      <!-- 成长报告（移动端=全屏子页；操作内联在报告内，不再压底部按钮栏） -->
      <ResponsivePopup
        v-model="reportVisible"
        title="成长报告"
        width="420px"
        align-center
        :close-on-click-modal="false"
        class="tui-dialog"
        destroy-on-close
      >
        <div v-if="report" class="pf-report">
          <div class="rpt-cover">
            <img class="rpt-mascot" :src="siteMascot" :alt="siteName" />
            <div class="rpt-cover-bd">
              <h3>{{ report.teacher_name }} · 教师成长报告</h3>
              <span>生成于 {{ (report.generated_at || '').slice(0, 10) }} · 共 {{ report.total }} 条育人档案</span>
            </div>
            <el-button class="rpt-print" size="small" :icon="Printer" @click="printReport">打印 / PDF</el-button>
          </div>

          <div class="rpt-types">
            <div v-for="t in report.by_type" :key="t.type" class="rpt-type">
              <div class="rpt-type-hd">
                <span class="rpt-lb">{{ t.label }}</span>
                <span class="rpt-num">{{ t.count }}</span>
              </div>
              <div class="rpt-bar">
                <i
                  :style="{
                    width: (report.total ? Math.round((t.count / report.total) * 100) : 0) + '%',
                    background: PORTFOLIO_TYPE_COLOR[t.type],
                  }"
                ></i>
              </div>
            </div>
          </div>

          <template v-if="report.items.length">
            <div class="rpt-sec">
              <span>档案明细</span>
              <span>{{ report.items.length }} 条</span>
            </div>
            <div class="rpt-list">
              <div v-for="(it, i) in report.items" :key="it.id" class="rpt-item">
                <span class="rpt-idx">{{ i + 1 }}</span>
                <span class="rpt-dot" :style="{ background: PORTFOLIO_TYPE_COLOR[it.item_type] }"></span>
                <span class="rpt-title">{{ it.title }}</span>
                <span class="rpt-meta">
                  {{ PORTFOLIO_TYPE_LABEL[it.item_type] }}<template v-if="it.occurred_on"> · {{ it.occurred_on }}</template>
                </span>
              </div>
            </div>
          </template>

          <div v-else class="rpt-empty">
            <img :src="siteMascot" :alt="siteName" class="rpt-empty-mascot" />
            <b>还没有可汇总的育人档案</b>
            <span>工作案例、荣誉表彰、培训研修与研究成果会自动归入成长报告。</span>
            <el-button type="primary" size="small" :icon="Plus" class="rpt-add-btn" @click="createFromReport">去新增档案</el-button>
          </div>

          <div class="rpt-note">数据来自你的育人档案，补充档案后重新打开即可生成最新报告。</div>
        </div>
      </ResponsivePopup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// v6.1 弹窗减负：报告走全屏子页
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import {
  Clock,
  Collection,
  Document,
  InfoFilled,
  Medal,
  Plus,
  Printer,
  Star,
  Suitcase,
  Trophy,
  User,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
import {
  getPortfolioReport,
  PORTFOLIO_TYPE_COLOR,
  PORTFOLIO_TYPE_LABEL,
  type PortfolioItem,
  type PortfolioReport,
} from '@/api/teacherPortfolio'
import { getStudents, type StudentSummary } from '@/api/teacher'
import { getGrowthRecords } from '@/api/growth'
import type { GrowthRecord } from '@/types'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import PortfolioItemDialog from '@/components/teacher/portfolio/PortfolioItemDialog.vue'

defineOptions({ name: 'teacher-portfolio' })

const { isMobile } = useResponsive()
const { siteMascot, siteName } = useSiteConfig()

// 移动端下拉刷新：桌面端不响应手势
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

const dialogVisible = ref(false)
const route = useRoute()
const router = useRouter()
const editing = ref<PortfolioItem | null>(null)
const report = ref<PortfolioReport | null>(null)
const reportVisible = ref(false)
const reportLoading = ref(false)

// 学生成长：横向选择器 + 徽章墙 + 时间轴
const students = ref<StudentSummary[]>([])
const studentsLoading = ref(false)
const activeStudentId = ref<number | null>(null)
const growthRecords = ref<GrowthRecord[]>([])
const growthLoading = ref(false)

const activeStudent = computed(
  () => students.value.find((s) => s.id === activeStudentId.value) ?? null
)

const RECORD_META: Record<GrowthRecord['type'], { label: string; icon: unknown }> = {
  honor: { label: '荣誉', icon: Medal },
  competition: { label: '竞赛', icon: Trophy },
  practice: { label: '实践', icon: Suitcase },
  paper: { label: '论文', icon: Document },
  achievement: { label: '成果', icon: Star },
}

const badges = computed(() => {
  const s = activeStudent.value
  if (!s) return [] as { key: string; label: string; value: number; icon: unknown; tone: string }[]
  return [
    { key: 'growth', label: '成长记录', value: s.growth_count, icon: Collection, tone: 'brand' },
    { key: 'skill', label: '技能标签', value: s.skills_json?.skills?.length ?? 0, icon: Star, tone: '' },
    { key: 'interest', label: '兴趣方向', value: s.skills_json?.interests?.length ?? 0, icon: Medal, tone: '' },
    { key: 'score', label: '综合评分', value: s.score, icon: Trophy, tone: 'success' },
  ]
})

const timeline = computed(() =>
  [...growthRecords.value].sort((a, b) => (a.date < b.date ? 1 : -1))
)

/* ── 移动端：指标条 + 成果轨道 ──
   后端没有五维能力打分，所以条形用真实存在的四项指标，
   刻度取「全班最高值」，竖线取「全班均值」—— 都是算出来的，不是拍的。 */
const RECORD_COLOR: Record<string, string> = {
  honor: '#0f8e6b',
  competition: '#7c5cf0',
  practice: '#2f6df6',
  paper: '#d98317',
  achievement: '#0f97a6',
}
function recordColor(t: string) {
  return RECORD_COLOR[t] || '#5b5bd6'
}
function skillCount(s: StudentSummary) {
  return s.skills_json?.skills?.length ?? 0
}
function interestCount(s: StudentSummary) {
  return s.skills_json?.interests?.length ?? 0
}
const capBars = computed(() => {
  const pool = students.value
  const max = (fn: (s: StudentSummary) => number) =>
    pool.reduce((m, s) => Math.max(m, fn(s)), 0) || 1
  const avg = (fn: (s: StudentSummary) => number) =>
    pool.length ? pool.reduce((t, s) => t + fn(s), 0) / pool.length : 0
  const s = activeStudent.value
  if (!s) return [] as { label: string; value: number; pct: number; avgPct: number }[]
  const defs: { label: string; value: number; fn: (x: StudentSummary) => number }[] = [
    { label: '成长记录', value: s.growth_count ?? 0, fn: (x) => x.growth_count ?? 0 },
    { label: '技能标签', value: skillCount(s), fn: skillCount },
    { label: '兴趣方向', value: interestCount(s), fn: interestCount },
    { label: '综合评分', value: s.score ?? 0, fn: (x) => x.score ?? 0 },
  ]
  return defs.map((d) => ({
    label: d.label,
    value: d.value,
    pct: Math.min(100, Math.round((d.value / max(d.fn)) * 100)),
    avgPct: Math.min(100, Math.round((avg(d.fn) / max(d.fn)) * 100)),
  }))
})

function selectStudent(id: number) {
  activeStudentId.value = id
}

/** 下拉刷新：复用学生名单加载，失败不提示 */
async function refreshAll() {
  await loadStudents()
}

async function loadStudents() {
  studentsLoading.value = true
  try {
    students.value = await getStudents()
    if (students.value.length && activeStudentId.value === null) {
      activeStudentId.value = students.value[0].id
    }
  } catch {
    students.value = []
  } finally {
    studentsLoading.value = false
  }
}

async function loadGrowth() {
  if (activeStudentId.value === null) {
    growthRecords.value = []
    return
  }
  growthLoading.value = true
  try {
    growthRecords.value = await getGrowthRecords(activeStudentId.value)
  } catch {
    growthRecords.value = []
  } finally {
    growthLoading.value = false
  }
}

watch(activeStudentId, loadGrowth)

function openCreate() {
  editing.value = null
  dialogVisible.value = true
}

/** 成长报告空态：先收起报告再打开新增档案，避免两层弹层叠加 */
function createFromReport() {
  reportVisible.value = false
  openCreate()
}

async function openReport() {
  reportLoading.value = true
  try {
    report.value = await getPortfolioReport()
    reportVisible.value = true
  } catch {
    ElMessage.error('成长报告生成失败')
  } finally {
    reportLoading.value = false
  }
}

/** 打印 / 导出 PDF：打开独立打印窗口，避免页面样式干扰 */
function printReport() {
  const r = report.value
  if (!r) return
  const rows = r.items
    .map(
      (it, i) =>
        `<tr><td>${i + 1}</td><td>${escapeHtml(it.title)}</td><td>${PORTFOLIO_TYPE_LABEL[it.item_type]}</td><td>${it.occurred_on || '-'}</td></tr>`
    )
    .join('')
  const cards = r.by_type
    .map((t) => `<span class="chip">${t.label} <b>${t.count}</b></span>`)
    .join('')
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" />
<title>${escapeHtml(r.teacher_name)} · 教师成长报告</title>
<style>
  body{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",system-ui,sans-serif;color:#101828;padding:32px;}
  h1{font-size:20px;margin:0 0 4px;}
  .meta{color:#98a2b3;font-size:12px;margin-bottom:18px;}
  .chips{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px;}
  .chip{border:1px solid #eaecf0;border-radius:999px;padding:4px 12px;font-size:12px;color:#475467;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th,td{border-bottom:1px solid #eaecf0;padding:8px 6px;text-align:left;}
  th{color:#667085;font-weight:600;font-size:12px;}
  td:first-child,th:first-child{width:40px;color:#98a2b3;}
</style></head><body>
  <h1>${escapeHtml(r.teacher_name)} · 教师成长报告</h1>
  <div class="meta">生成时间：${(r.generated_at || '').slice(0, 10)} ｜ 共 ${r.total} 条</div>
  <div class="chips">${cards}</div>
  <table><thead><tr><th>#</th><th>标题</th><th>类型</th><th>时间</th></tr></thead><tbody>${rows}</tbody></table>
</body></html>`
  const w = window.open('', '_blank', 'width=900,height=1000')
  if (!w) {
    ElMessage.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
    return
  }
  w.document.write(html)
  w.document.close()
  w.focus()
  w.print()
}

function escapeHtml(s: string) {
  return (s || '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string
  )
}

onMounted(async () => {
  await loadStudents()
  // 深链 ?student_id=<id>：从关怀聚焦等入口直达该生成长档案
  const deepId = Number(route.query.student_id || route.query.student)
  if (deepId) {
    if (students.value.some((s) => s.id === deepId)) activeStudentId.value = deepId
    router.replace({ path: '/teacher/portfolio' })
  }
  // 从「我的成长」上传入口进入时直接打开新增档案，减少一次点击
  if (route.query.create === '1') openCreate()
})
</script>

<style scoped>
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* 移动端高频操作条 */
.pf-topbar {
  margin-bottom: 12px;
}
.pf-topbar .el-button {
  flex: 1;
  margin-left: 0;
}

/* 学生横向选择器 */
.pf-rail {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: none;
}
.pf-rail::-webkit-scrollbar {
  display: none;
}
.pf-stu {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 62px;
  padding: 8px 4px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.18s var(--tui-ease);
}
.pf-stu:active {
  transform: scale(0.97);
}
.pf-stu.active {
  border-color: var(--tui-brand);
  background: var(--tui-brand-soft);
}
.pf-stu-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-secondary);
  font-size: 13px;
  font-weight: 600;
}
.pf-stu.active .pf-stu-avatar {
  background: var(--tui-brand);
  color: #fff;
}
.pf-stu-name {
  font-size: 11.5px;
  color: var(--tui-text-secondary);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-stu.active .pf-stu-name {
  color: var(--tui-brand-strong);
  font-weight: 600;
}

/* 徽章墙 */
.pf-badges {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.pf-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px 6px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
}
.pf-badge.brand {
  color: var(--tui-brand-strong);
  background: var(--tui-brand-soft);
  border-color: transparent;
}
.pf-badge.success {
  color: var(--tui-success);
  background: var(--tui-success-soft);
  border-color: transparent;
}
.pf-badge-num {
  font-size: 17px;
  font-weight: 700;
  color: inherit;
  font-variant-numeric: tabular-nums;
}
.pf-badge-lb {
  font-size: 10.5px;
  color: var(--tui-text-quiet);
}
.pf-badge.brand .pf-badge-lb,
.pf-badge.success .pf-badge-lb {
  color: inherit;
  opacity: 0.75;
}

/* 时间轴 */
.tl {
  position: relative;
  padding-left: 26px;
}
.tl::before {
  content: '';
  position: absolute;
  left: 9px;
  top: 6px;
  bottom: 6px;
  width: 2px;
  background: var(--tui-border);
}
.tl-item {
  position: relative;
  margin-bottom: 10px;
}
.tl-item:last-child {
  margin-bottom: 0;
}
.tl-node {
  position: absolute;
  left: -26px;
  top: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--tui-surface);
  box-shadow: inset 0 0 0 2px var(--tui-brand);
  color: var(--tui-brand);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tl-body {
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  padding: 8px 10px;
}
.tl-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.tl-date {
  font-size: 11px;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.tl-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--tui-text);
  margin-top: 4px;
}
.tl-desc {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--tui-text-secondary);
  line-height: 1.55;
}

/* 成长报告：封面 + 分类占比 + 明细 + 空态（操作内联，不再压底部按钮栏） */
.pf-report {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rpt-cover {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-md, 14px);
  background: linear-gradient(135deg, #f4f7ff 0%, #fbfcff 70%);
}
.rpt-mascot {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  object-fit: contain;
}
.rpt-cover-bd {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.rpt-cover-bd h3 {
  margin: 0;
  font-size: 14.5px;
  font-weight: 700;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rpt-cover-bd span {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.rpt-print {
  flex: 0 0 auto;
}
.rpt-types {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.rpt-type {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 8px 10px;
}
.rpt-type-hd {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
}
.rpt-num {
  font-size: 18px;
  font-weight: 750;
  color: var(--tui-brand-strong);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.rpt-lb {
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.rpt-bar {
  height: 4px;
  border-radius: 99px;
  background: rgba(17, 24, 39, 0.08);
  overflow: hidden;
}
.rpt-bar i {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 99px;
  transition: width 0.3s ease;
}
.rpt-sec {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.rpt-sec span:first-child {
  font-weight: 700;
  color: var(--tui-text-secondary);
}
.rpt-list {
  display: flex;
  flex-direction: column;
}
.rpt-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 2px;
  border-bottom: 1px solid var(--tui-border);
  font-size: 12.5px;
}
.rpt-item:last-child {
  border-bottom: none;
}
.rpt-idx {
  width: 16px;
  text-align: center;
  color: var(--tui-text-quiet);
  font-size: 11px;
  flex-shrink: 0;
}
.rpt-dot {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  align-self: center;
  border-radius: 50%;
}
.rpt-title {
  color: var(--tui-text-secondary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rpt-meta {
  font-size: 11px;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}
.rpt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 18px 12px 14px;
  text-align: center;
  border: 1px dashed var(--tui-border);
  border-radius: var(--tui-radius-md, 14px);
  background: var(--tui-surface-muted);
}
.rpt-empty-mascot {
  width: 56px;
  height: 56px;
  object-fit: contain;
  margin-bottom: 2px;
}
.rpt-empty b {
  font-size: 13.5px;
  color: var(--tui-text);
}
.rpt-empty span {
  max-width: 260px;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
}
.rpt-empty .el-button {
  margin-top: 4px;
}
/* 空态入口：紧凑胶囊按钮，不抢内容 */
.rpt-add-btn {
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11.5px;
}
.rpt-add-btn :deep(.el-icon) {
  font-size: 12px;
}
.rpt-note {
  font-size: 11px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
  text-align: center;
}

@media (max-width: 767px) {
  .pf-badges {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>