<template>
  <div class="tui-page">
    <!-- 移动端吸顶栏（「更多」为底部页签页，无返回键） -->
    <header v-if="isMobile" class="tui-appbar">
      <div class="tui-appbar-title">
        全部功能
        <span class="tui-appbar-sub">按职能分区，点击图标直达</span>
      </div>
      <div class="tui-appbar-actions">
        <el-button text circle aria-label="搜索" @click="focusSearch">
          <el-icon :size="19"><Search /></el-icon>
        </el-button>
      </div>
    </header>

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">全部功能</h2>
          <p class="tui-header-sub">按职能分区，每个模块只做一件事，点击图标直达</p>
        </div>
      </header>

      <!-- 搜索 -->
      <div class="more-search">
        <el-input
          ref="searchRef"
          v-model="keyword"
          placeholder="搜索功能，如「预警」「家访」"
          clearable
          :prefix-icon="Search"
        />
      </div>

      <!-- 常用操作 -->
      <section v-if="!keyword" class="tui-card more-quick">
        <div class="tui-card-head">
          <span class="tui-card-head-icon" :style="{ background: '#eff4ff', color: '#1d4ed8' }">
            <el-icon :size="13"><Star /></el-icon>
          </span>
          常用操作
          <span class="tui-group-count">高频入口</span>
        </div>
        <div class="quick-grid">
          <button
            v-for="q in quickItems"
            :key="q.path"
            type="button"
            class="quick-cell"
            @click="router.push(q.path)"
          >
            <span class="quick-icon" :style="{ background: q.tint, color: q.color }">
              <el-icon :size="21"><component :is="q.icon" /></el-icon>
            </span>
            <span class="quick-main">
              <span class="quick-label">{{ q.label }}</span>
              <span class="quick-desc">{{ q.desc }}</span>
            </span>
            <el-icon class="quick-arrow" :size="14"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <!-- 分组宫格 -->
      <section
        v-for="g in visibleGroups"
        :key="g.title"
        class="tui-card more-group"
      >
        <div class="tui-card-head">
          <span class="tui-card-head-icon" :style="{ background: g.tint, color: g.color }">
            <el-icon :size="13"><component :is="g.icon" /></el-icon>
          </span>
          {{ g.title }}
          <span class="tui-group-count">{{ g.items.length }} 项</span>
        </div>
        <div class="tui-grid-nav">
          <button
            v-for="it in g.items"
            :key="it.path"
            type="button"
            class="tui-nav-cell"
            @click="router.push(it.path)"
          >
            <span class="tui-nav-icon" :style="{ background: it.tint, color: it.color }">
              <el-icon :size="22"><component :is="it.icon" /></el-icon>
            </span>
            <span class="tui-nav-label">{{ it.label }}</span>
          </button>
        </div>
      </section>

      <!-- 空结果 -->
      <div v-if="keyword && !visibleGroups.length" class="tui-empty">
        <span class="tui-empty-icon"><el-icon :size="26"><Search /></el-icon></span>
        <span class="tui-empty-title">没有匹配「{{ keyword }}」的功能</span>
        <span class="tui-empty-desc">换个关键词试试，或清空搜索查看全部</span>
      </div>

      <p class="more-foot">绵小城 · 教师工作台</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import {
  ArrowRight, Bell, ChatDotRound, Collection, Connection, EditPen, FolderOpened,
  Search, Star, Stamp, Sunny, WarningFilled,
} from '@element-plus/icons-vue'

defineOptions({ name: 'teacher-more' })

const router = useRouter()
const { isMobile } = useResponsive()

const keyword = ref('')
const searchRef = ref<{ focus: () => void } | null>(null)

function focusSearch() {
  searchRef.value?.focus?.()
}

/** 常用操作：跨分组的最高频三项，避免在宫格里来回找 */
const quickItems = [
  { path: '/teacher/approval', label: '审批管理', desc: '请假 / 办事 / 材料', icon: Stamp, color: '#b54708', tint: '#fffaeb' },
  { path: '/teacher/crisis', label: '预警工作台', desc: '心理预警闭环处置', icon: WarningFilled, color: '#d92d20', tint: '#fef3f2' },
  { path: '/teacher/announcement', label: '班级公告', desc: '发布通知给学生', icon: Bell, color: '#2563eb', tint: '#eff4ff' },
]

/**
 * 「更多」= 非页签模块的宫格入口（首页 / 学生 / 绵小城 / 个人中心 已在底部导航，此处不重复）。
 * 每个模块归属唯一分组，互不交叉。
 */
const groups = [
  {
    title: '学生工作',
    icon: FolderOpened,
    color: '#1d4ed8',
    tint: '#eff4ff',
    items: [
      { path: '/teacher/approval', label: '审批', icon: Stamp, color: '#b54708', tint: '#fffaeb' },
      { path: '/teacher/crisis', label: '预警', icon: WarningFilled, color: '#d92d20', tint: '#fef3f2' },
      { path: '/teacher/announcement', label: '公告', icon: Bell, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '我的成长',
    icon: Collection,
    color: '#6941c6',
    tint: '#f4f3ff',
    items: [
      { path: '/teacher/portfolio', label: '成长档案', icon: Collection, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher/survey', label: '问卷互评', icon: EditPen, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '关怀与沟通',
    icon: Sunny,
    color: '#b54708',
    tint: '#fffaeb',
    items: [
      { path: '/teacher/care-center', label: '关怀中心', icon: Sunny, color: '#f79009', tint: '#fffaeb' },
      { path: '/teacher/guardian', label: '家校沟通', icon: Connection, color: '#0891b2', tint: '#ecfeff' },
      { path: '/teacher/messages', label: '消息', icon: ChatDotRound, color: '#079455', tint: '#ecfdf3' },
    ],
  },
]

/** 搜索：按模块名 + 分组名匹配，命中后仅保留命中的模块 */
const visibleGroups = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return groups
  return groups
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (it) => it.label.includes(kw) || g.title.includes(kw)
      ),
    }))
    .filter((g) => g.items.length > 0)
})
</script>

<style scoped>
.more-search {
  margin-bottom: 12px;
}
.more-search :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 3px 12px;
  box-shadow: 0 0 0 1px #eceded inset;
}
.more-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset;
}

/* 常用操作：三行大热区，图标 + 标题 + 副标题 + 箭头 */
.more-quick .quick-grid {
  display: flex;
  flex-direction: column;
  padding: 8px 6px 10px;
}
.quick-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 10px;
  border: none;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: background 0.18s ease, transform 0.18s ease;
}
.quick-cell:hover { background: #f7f8fa; }
.quick-cell:active { background: #eceef1; transform: scale(0.985); }
.quick-icon {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.quick-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.quick-label {
  font-size: 14.5px;
  font-weight: 600;
  color: #0f1115;
}
.quick-desc {
  font-size: 12px;
  color: #9ca3af;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.quick-arrow { color: #cbd0d8; flex-shrink: 0; }

.more-group + .more-group { margin-top: 12px; }

.more-foot {
  margin: 22px 0 0;
  text-align: center;
  font-size: 11.5px;
  color: #c2c7cf;
  letter-spacing: 0.4px;
}
</style>