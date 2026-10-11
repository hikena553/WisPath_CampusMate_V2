<template>
  <div class="tui-page">
    <!-- 移动端吸顶栏（首页下钻的子页面，返回回首页） -->
    <SubPageHeader title="全部功能" sub="教师工作台功能总览" fallback="/teacher" />

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">全部功能</h2>
          <p class="tui-header-sub">教师工作台的功能总览，点击直达对应子页面</p>
        </div>
      </header>

      <!-- 搜索：功能较多时按名称 / 说明快速定位 -->
      <div class="feat-search">
        <el-input
          v-model="keyword"
          placeholder="搜索功能，如「审批」「家访」"
          clearable
          :prefix-icon="Search"
        />
      </div>

      <div v-if="!keyword.trim()" class="tui-notice feat-tip">
        <el-icon :size="15"><InfoFilled /></el-icon>
        <span>会话、通讯录与通知在底部「消息」页签内，此处为其余功能入口</span>
      </div>

      <template v-for="g in visibleGroups" :key="g.title">
        <div class="tui-group-title">
          {{ g.title }}
          <span class="tui-group-count">{{ g.items.length }} 项</span>
        </div>
        <div class="tui-list">
          <button
            v-for="it in g.items"
            :key="it.path"
            type="button"
            class="tui-row"
            @click="router.push(it.path)"
          >
            <span class="tui-row-icon" :style="{ background: it.tint, color: it.color }">
              <el-icon :size="18"><component :is="it.icon" /></el-icon>
            </span>
            <span class="tui-row-main">
              <span class="tui-row-label">{{ it.label }}</span>
              <span class="tui-row-desc">{{ it.desc }}</span>
            </span>
            <span
              v-if="countOf(it) > 0"
              class="tui-count"
              :class="{ 'tui-count-warn': it.tone === 'warn' }"
            >{{ countOf(it) > 99 ? '99+' : countOf(it) }}</span>
            <el-icon class="tui-row-arrow" :size="15"><ArrowRight /></el-icon>
          </button>
        </div>
      </template>

      <!-- 空结果：与其它子页面一致的空态表达 -->
      <div v-if="!visibleGroups.length" class="tui-empty">
        <span class="tui-empty-icon"><el-icon :size="26"><Search /></el-icon></span>
        <span class="tui-empty-title">没有匹配「{{ keyword }}」的功能</span>
        <span class="tui-empty-desc">换个关键词试试，或清空搜索查看全部</span>
      </div>

      <p class="feat-foot">{{ siteName }} · 教师工作台</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { getCachedData, getPrefetchPromise } from '@/utils/teacherDashboardCache'
import { getDashboardStats, type DashboardStats } from '@/api/teacher'
import {
  ArrowRight, Bell, ChatDotRound, Collection, Connection, EditPen, InfoFilled,
  Notebook, Search, Stamp, Sunny, WarningFilled,
} from '@element-plus/icons-vue'

defineOptions({ name: 'teacher-features' })

const router = useRouter()
const { siteName } = useSiteConfig()
const { isMobile } = useResponsive()

const keyword = ref('')

interface FeatureItem {
  path: string
  label: string
  desc: string
  icon: Component
  color: string
  tint: string
  /** 关联的实时角标数据键：有值时在行尾显示数量 */
  badgeKey?: 'approval' | 'crisis'
  tone?: 'warn'
}
interface FeatureGroup {
  title: string
  items: FeatureItem[]
}

/**
 * 功能总览：底部页签已承载 首页 / 学生 / 绵小城 / 消息 / 个人中心，
 * 此处只列其余模块，保证同一功能不重复出现。色值取自设计令牌同源色板。
 */
const groups: FeatureGroup[] = [
  {
    title: '学生事务',
    items: [
      { path: '/teacher/approval', label: '审批', desc: '请假、证明等事项的受理与审批', icon: Stamp, color: '#b54708', tint: '#fffaeb', badgeKey: 'approval', tone: 'warn' },
      { path: '/teacher/crisis', label: '预警', desc: '学生风险与危机事件的预警跟进', icon: WarningFilled, color: '#d92d20', tint: '#fef3f2', badgeKey: 'crisis' },
      { path: '/teacher/announcement', label: '公告', desc: '面向班级发布通知与公告', icon: Bell, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '成长与关怀',
    items: [
      { path: '/teacher/portfolio', label: '成长档案', desc: '学生成长记录与作品集管理', icon: Collection, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher/survey', label: '问卷互评', desc: '匿名问卷发放与学生互评', icon: EditPen, color: '#2563eb', tint: '#eff4ff' },
      { path: '/teacher/care-center', label: '关怀中心', desc: '谈心记录与心理关怀跟进', icon: Sunny, color: '#f79009', tint: '#fffaeb' },
      { path: '/teacher/guardian', label: '家校沟通', desc: '家长联系人沟通与记录留痕', icon: Connection, color: '#0891b2', tint: '#ecfeff' },
    ],
  },
  {
    title: '效率工具',
    items: [
      { path: '/teacher/tasks', label: '今日任务', desc: '待办、逾期与日程的统一入口', icon: Notebook, color: '#079455', tint: '#ecfdf3' },
      { path: '/teacher/ai', label: 'AI 洞察', desc: '主动发现与推荐联系建议', icon: ChatDotRound, color: '#0891b2', tint: '#ecfeff' },
    ],
  },
]

/** 实时角标：待批请假数 / 高危预警数，优先读首页已预取的 dashboard 缓存 */
const badges = ref<Record<string, number>>({ approval: 0, crisis: 0 })

function applyStats(stats: DashboardStats) {
  badges.value = {
    approval: stats.pending_leave_count || 0,
    crisis: stats.severe_alert_count || 0,
  }
}

function countOf(it: FeatureItem): number {
  return it.badgeKey ? badges.value[it.badgeKey] || 0 : 0
}

onMounted(async () => {
  const cached = getCachedData<DashboardStats>('dashboard-stats')
  if (cached) { applyStats(cached); return }
  const pending = getPrefetchPromise()
  if (pending) {
    await pending
    const after = getCachedData<DashboardStats>('dashboard-stats')
    if (after) { applyStats(after); return }
  }
  try {
    applyStats(await getDashboardStats())
  } catch {
    /* 角标拉取失败不影响功能导航 */
  }
})

/** 搜索：按名称 / 分区名 / 说明匹配，命中后仅保留命中的模块 */
const visibleGroups = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return groups
  return groups
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (it) => it.label.includes(kw) || g.title.includes(kw) || it.desc.includes(kw)
      ),
    }))
    .filter((g) => g.items.length > 0)
})
</script>

<style scoped>
/* 移动端收小页边距，与吸顶栏 10px 内边距对齐 */
@media (max-width: 767px) {
  .tui-content {
    padding-left: 10px;
    padding-right: 10px;
  }
}

.feat-search { margin-bottom: 12px; }
.feat-search :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 5px 12px;
  background: var(--tui-surface-sunken);
  box-shadow: none;
  transition: background 0.18s var(--tui-ease), box-shadow 0.18s var(--tui-ease);
}
.feat-search :deep(.el-input__wrapper.is-focus) {
  background: var(--tui-surface);
  box-shadow: 0 0 0 1px var(--tui-brand) inset;
}

.feat-tip { margin-bottom: 4px; }

.feat-foot {
  margin: 22px 0 0;
  text-align: center;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  letter-spacing: 0.4px;
}
</style>