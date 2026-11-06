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
      <!-- 桌面端特色头部：档案语义色 + 收藏图标；本页只承载学生维度，
           教师本人的育人档案已迁至「我的成长」页，入口见下方快捷区 -->
      <TuiPageHero
        v-if="!isMobile"
        title="学生成长档案"
        sub="选择学生查看其成长徽章与成长轨迹"
        :icon="Collection"
        tone="violet"
      >
        <div class="tui-hero-metric is-accent"><b>{{ students.length }}</b><span>名下学生</span></div>
        <el-button :icon="TrendCharts" @click="goMyGrowth">我的育人档案</el-button>
      </TuiPageHero>

      <!-- 移动端高频操作：保留「我的育人档案」入口，避免教师在手机上找不到 -->
      <div v-if="isMobile" class="tui-actions pf-topbar">
        <el-button round :icon="TrendCharts" @click="goMyGrowth">我的育人档案</el-button>
      </div>

      <!-- ============================================================
           一级：选择班级。教师名下学生往往横跨多个班，先收敛到班，
           再在班里选人——否则一屏几十张卡片，找人不现实。
           ============================================================ -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><School /></el-icon>选择班级</h3>
          <span class="tui-section-extra tui-text-quiet">
            {{ classGroups.length }} 个班 · 共 {{ students.length }} 人
          </span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>先选班级，再在班级里选择学生查看其成长档案。</span>
        </div>

        <div v-if="studentsLoading" class="tui-empty">
          <AgentLoading block :tips="['正在读取学生名单', '正在按班级归类']" />
        </div>
        <div v-else-if="!classGroups.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><User /></el-icon></span>
          <span class="tui-empty-title">暂无可查看的学生</span>
          <span class="tui-empty-desc">当前账号名下还没有学生，先到「学生管理」导入名单后再查看。</span>
        </div>

        <div v-else class="pf-classes">
          <button
            v-for="g in classGroups"
            :key="g.key"
            type="button"
            class="pf-class"
            :class="{ active: g.key === activeClassKey }"
            @click="selectClass(g.key)"
          >
            <span class="pf-class-name">{{ g.name }}</span>
            <span class="pf-class-meta">
              <b>{{ g.students.length }}</b> 人
              <em v-if="g.engaged">· {{ g.engaged }} 人有记录</em>
            </span>
          </button>
        </div>
      </section>

      <!-- ============================================================
           二级：班级内的学生。只有选好班级才展开，
           避免「全班学生」和「某班学生」两份名单同时铺在屏幕上。
           ============================================================ -->
      <section v-if="activeClassKey" class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><User /></el-icon>{{ activeClass?.name }} · 学生</h3>
          <span class="tui-section-extra tui-text-quiet">
            {{ activeClass?.students.length ?? 0 }} 人
          </span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>点学生卡片查看其完整成长轨迹；再点一次收起，回到班级列表。</span>
        </div>

        <!-- 搜索 + 排序：班级人多时能快速定位，默认按成长记录多的排前 -->
        <div class="pf-tools">
          <el-input
            v-model="keyword"
            placeholder="搜学生姓名 / 学号"
            :prefix-icon="Search"
            clearable
            class="pf-search"
          />
          <div class="pf-sort">
            <button
              v-for="s in SORTS"
              :key="s.value"
              type="button"
              class="pf-sort-btn"
              :class="{ active: sortBy === s.value }"
              @click="sortBy = s.value"
            >
              {{ s.label }}
            </button>
          </div>
        </div>

        <div v-if="visibleStudents.length" class="pf-grid">
          <button
            v-for="s in visibleStudents"
            :key="s.id"
            type="button"
            class="pf-card"
            :class="{ active: s.id === activeStudentId }"
            @click="selectStudent(s.id)"
          >
            <span class="pf-card-top">
              <span class="pf-card-avatar">{{ s.name.slice(0, 1) }}</span>
              <span class="pf-card-id">
                <span class="pf-card-name">{{ s.name }}</span>
                <span class="pf-card-sub">{{ s.class_name || s.college || '未分班' }}</span>
              </span>
              <span
                v-if="s.crisis_level"
                class="pf-card-flag"
                title="心理关注中"
              >关注</span>
            </span>
            <span class="pf-card-nums">
              <span class="pf-card-num">
                <b>{{ s.growth_count ?? 0 }}</b><em>成长记录</em>
              </span>
              <span class="pf-card-num">
                <b>{{ skillCount(s) }}</b><em>技能</em>
              </span>
              <span class="pf-card-num">
                <b>{{ s.score ?? 0 }}</b><em>综合评分</em>
              </span>
            </span>
            <!-- 成长密度条：相对本班最高值，一眼看出谁积累得多 -->
            <span class="pf-card-bar">
              <i :style="{ width: growthPct(s) + '%' }"></i>
            </span>
          </button>
        </div>
        <div v-else class="tui-empty">
          <span class="tui-empty-title">没有匹配的学生</span>
          <span class="tui-empty-desc">换个姓名或学号试试。</span>
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
        <!-- 详情标题：明确「现在看的是谁」，并给一个回到总览的出口 -->
        <div class="pf-detail-hd">
          <span class="pf-detail-who">
            <b>{{ activeStudent.name }}</b>
            <em>的成长档案</em>
          </span>
          <button type="button" class="pf-detail-back" @click="clearStudent">返回总览</button>
        </div>
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Clock,
  Collection,
  Document,
  InfoFilled,
  Medal,
  School,
  Search,
  Star,
  Suitcase,
  TrendCharts,
  Trophy,
  User,
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
import { getStudents, type StudentSummary } from '@/api/teacher'
import { getGrowthRecords } from '@/api/growth'
import type { GrowthRecord } from '@/types'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'

defineOptions({ name: 'teacher-portfolio' })

const { isMobile } = useResponsive()

// 移动端下拉刷新：桌面端不响应手势
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

const route = useRoute()
const router = useRouter()

// 学生成长：班级 → 学生 → 徽章墙 / 时间轴
const students = ref<StudentSummary[]>([])
const studentsLoading = ref(false)
const activeStudentId = ref<number | null>(null)
const growthRecords = ref<GrowthRecord[]>([])
const growthLoading = ref(false)

/* ── 一级：班级 ──
   教师名下学生常横跨多个班，直接铺全部卡片会让人无从下手。
   这里按 class_group_id 分组，未分班的归入单独一组排在最后。 */
interface ClassGroup {
  key: string
  name: string
  students: StudentSummary[]
  /** 组内有成长记录的人数，给选择时一个「哪个班更值得看」的依据 */
  engaged: number
}
const UNASSIGNED = '__unassigned__'
const activeClassKey = ref<string | null>(null)

const classGroups = computed<ClassGroup[]>(() => {
  const map = new Map<string, ClassGroup>()
  for (const s of students.value) {
    const key = s.class_group_id != null ? String(s.class_group_id) : UNASSIGNED
    const name = s.class_name || '未分班'
    let g = map.get(key)
    if (!g) {
      g = { key, name, students: [], engaged: 0 }
      map.set(key, g)
    }
    g.students.push(s)
  }
  const list = [...map.values()]
  // 有班级名的按名称排，未分班永远垫底
  list.sort((a, b) => {
    if (a.key === UNASSIGNED) return 1
    if (b.key === UNASSIGNED) return -1
    return a.name.localeCompare(b.name, 'zh-CN')
  })
  for (const g of list) {
    g.engaged = g.students.filter((s) => (s.growth_count ?? 0) > 0).length
  }
  return list
})

const activeClass = computed(
  () => classGroups.value.find((g) => g.key === activeClassKey.value) ?? null
)

/* ── 二级：班级内学生 + 搜索 / 排序 ── */
const keyword = ref('')
type SortKey = 'growth' | 'name' | 'score'
const SORTS: { value: SortKey; label: string }[] = [
  { value: 'growth', label: '成长记录' },
  { value: 'name', label: '姓名' },
  { value: 'score', label: '综合评分' },
]
const sortBy = ref<SortKey>('growth')

const visibleStudents = computed(() => {
  const pool = activeClass.value?.students ?? []
  const kw = keyword.value.trim().toLowerCase()
  const filtered = kw
    ? pool.filter(
        (s) =>
          s.name.toLowerCase().includes(kw) ||
          (s.username || '').toLowerCase().includes(kw)
      )
    : [...pool]
  return filtered.sort((a, b) => {
    if (sortBy.value === 'name') return a.name.localeCompare(b.name, 'zh-CN')
    if (sortBy.value === 'score') return (b.score ?? 0) - (a.score ?? 0)
    return (b.growth_count ?? 0) - (a.growth_count ?? 0)
  })
})

/** 成长密度条：以本班最高值为满格，避免跨班量纲不一致 */
const growthMax = computed(() =>
  Math.max(1, ...(activeClass.value?.students ?? []).map((s) => s.growth_count ?? 0))
)
function growthPct(s: StudentSummary) {
  return Math.min(100, Math.round(((s.growth_count ?? 0) / growthMax.value) * 100))
}

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

/** 选班级：切换班级时清空当前学生与搜索词，避免看着 A 班的人翻着 B 班的名单 */
function selectClass(key: string) {
  if (activeClassKey.value === key) return
  activeClassKey.value = key
  activeStudentId.value = null
  keyword.value = ''
}

function selectStudent(id: number) {
  // 再点同一个学生 = 收起详情，回到班级名单
  activeStudentId.value = activeStudentId.value === id ? null : id
}

function clearStudent() {
  activeStudentId.value = null
}

/** 下拉刷新：复用学生名单加载，失败不提示 */
async function refreshAll() {
  await loadStudents()
}

async function loadStudents() {
  studentsLoading.value = true
  try {
    students.value = await getStudents()
    // 默认落到第一个班级，但不预选学生——先看名单，再决定看谁
    if (classGroups.value.length && !activeClassKey.value) {
      activeClassKey.value = classGroups.value[0].key
    }
    // 深链指定过学生时，把他的班级一并展开
    if (activeStudentId.value !== null) {
      const s = students.value.find((x) => x.id === activeStudentId.value)
      if (s) {
        activeClassKey.value = s.class_group_id != null ? String(s.class_group_id) : UNASSIGNED
      }
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

/** 教师本人的育人档案（案例/荣誉/培训/研究成果）已整体迁到「我的成长」页 */
function goMyGrowth() {
  router.push({ path: '/teacher/growth', query: { tab: 'portfolio' } })
}

onMounted(async () => {
  // 深链 ?student_id=<id>：从关怀聚焦等入口直达该生成长档案。
  // 先在加载前记下目标学生，loadStudents 里会按他所属班级展开。
  const deepId = Number(route.query.student_id || route.query.student)
  if (deepId) activeStudentId.value = deepId

  await loadStudents()

  if (deepId) {
    // 不在本人名下：回退到总览，避免停在一个空状态上
    if (!students.value.some((s) => s.id === deepId)) activeStudentId.value = null
    router.replace({ path: '/teacher/portfolio' })
  }
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

/* ── 一级：班级选择 ── */
.pf-classes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 8px;
}
.pf-class {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 11px 13px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s var(--tui-ease);
}
.pf-class:active {
  transform: scale(0.985);
}
.pf-class:hover {
  border-color: var(--tui-border-strong, #c4c9d2);
}
.pf-class.active {
  border-color: transparent;
  background: var(--tui-brand-soft);
  box-shadow: inset 0 0 0 1px var(--tui-brand);
}
.pf-class-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-class.active .pf-class-name {
  color: var(--tui-brand-strong);
}
.pf-class-meta {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.pf-class-meta b {
  color: var(--tui-text-secondary);
  font-variant-numeric: tabular-nums;
}
.pf-class-meta em {
  font-style: normal;
  color: var(--tui-text-quiet);
}
.pf-class.active .pf-class-meta b {
  color: var(--tui-brand-strong);
}

/* ── 二级：搜索 + 排序 ── */
.pf-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.pf-search {
  flex: 1;
  min-width: 0;
}
.pf-sort {
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: var(--tui-surface-sunken);
  flex-shrink: 0;
}
.pf-sort-btn {
  padding: 4px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--tui-text-tertiary);
  font-family: inherit;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.16s ease;
}
.pf-sort-btn.active {
  background: var(--tui-surface);
  color: var(--tui-text);
  font-weight: 600;
}

/* ── 二级：学生卡片网格 ── */
.pf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 8px;
}
.pf-card {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 11px 12px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.18s var(--tui-ease);
}
.pf-card:hover {
  border-color: var(--tui-border-strong, #c4c9d2);
}
.pf-card:active {
  transform: scale(0.985);
}
.pf-card.active {
  border-color: transparent;
  background: var(--tui-brand-soft);
  box-shadow: inset 0 0 0 1px var(--tui-brand);
}
.pf-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pf-card-avatar {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-secondary);
  font-size: 13px;
  font-weight: 600;
}
.pf-card.active .pf-card-avatar {
  background: var(--tui-brand);
  color: #fff;
}
.pf-card-id {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.pf-card-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-card-sub {
  font-size: 11px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-card-flag {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--tui-danger-soft, #fef3f2);
  color: var(--tui-danger, #d92d20);
  font-size: 10.5px;
}
.pf-card-nums {
  display: flex;
  gap: 10px;
}
.pf-card-num {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.pf-card-num b {
  font-size: 15px;
  font-weight: 700;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}
.pf-card-num em {
  font-style: normal;
  font-size: 10px;
  color: var(--tui-text-quiet);
  white-space: nowrap;
}
.pf-card-bar {
  display: block;
  height: 3px;
  border-radius: 99px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.pf-card-bar i {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 99px;
  background: var(--tui-brand);
  transition: width 0.3s ease;
}

/* ── 详情标题：明确「现在看的是谁」+ 回到班级名单 ── */
.pf-detail-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 4px 0 10px;
  padding: 0 14px;
}
.pf-detail-who {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
}
.pf-detail-who b {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--tui-text);
}
.pf-detail-who em {
  font-style: normal;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.pf-detail-back {
  flex-shrink: 0;
  padding: 4px 11px;
  border: 1px solid var(--tui-border);
  border-radius: 999px;
  background: transparent;
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 11.5px;
  cursor: pointer;
}
.pf-detail-back:hover {
  background: var(--tui-surface-sunken);
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

@media (max-width: 767px) {
  .pf-badges {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  /* 手机上班级两列、学生一列，触控区域才够大 */
  .pf-classes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .pf-grid {
    grid-template-columns: 1fr;
  }
  .pf-tools {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .pf-sort {
    justify-content: space-between;
  }
  .pf-sort-btn {
    flex: 1;
    text-align: center;
  }
}
</style>