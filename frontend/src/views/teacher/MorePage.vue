<template>
  <div class="tui-page">
    <!-- 移动端吸顶品牌栏（「更多」为底部页签页，无返回键） -->
    <header v-if="isMobile" class="tui-appbar tui-appbar-brand">
      <div class="tui-appbar-title">
        全部功能
        <span class="tui-appbar-sub">{{ siteName }} · 按职能分区，点击直达</span>
      </div>
      <div class="tui-appbar-actions">
        <el-button text circle :aria-label="searchOpen ? '收起搜索' : '搜索'" @click="toggleSearch">
          <el-icon :size="19"><component :is="searchOpen ? Close : Search" /></el-icon>
        </el-button>
      </div>
    </header>

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header tui-header-brand">
        <div class="tui-header-lead">
          <div>
            <h2 class="tui-header-title">全部功能</h2>
            <p class="tui-header-sub">{{ siteName }} · 按职能分区，每个模块只做一件事</p>
          </div>
        </div>
        <div class="tui-header-actions">
          <el-button text circle :aria-label="searchOpen ? '收起搜索' : '搜索'" @click="toggleSearch">
            <el-icon :size="19"><component :is="searchOpen ? Close : Search" /></el-icon>
          </el-button>
        </div>
      </header>

      <!-- 搜索框默认收起，只保留头部的小搜索按钮，需要时展开 -->
      <Transition name="more-search-fade">
        <div v-if="searchOpen" class="more-search">
          <el-input
            ref="searchRef"
            v-model="keyword"
            placeholder="搜索功能，如「预警」「家访」"
            clearable
            :prefix-icon="Search"
            @keyup.esc="closeSearch"
          />
        </div>
      </Transition>

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

      <p class="more-foot">{{ siteName }} · 教师工作台</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import {
  Bell, ChatDotRound, Close, Collection, Connection, EditPen, FolderOpened,
  Search, Stamp, Sunny, WarningFilled,
} from '@element-plus/icons-vue'

defineOptions({ name: 'teacher-more' })

const router = useRouter()

// 站点名称取自站点配置：管理端变更后教师端同步
const { siteName } = useSiteConfig()
const { isMobile } = useResponsive()

const keyword = ref('')
/** 搜索框默认收起：头部只留一个小搜索按钮，不与内容区重复占位 */
const searchOpen = ref(false)
const searchRef = ref<{ focus: () => void } | null>(null)

function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) {
    nextTick(() => searchRef.value?.focus?.())
  } else {
    keyword.value = ''
  }
}

function closeSearch() {
  searchOpen.value = false
  keyword.value = ''
}

/**
 * 「更多」= 非页签模块的宫格入口（首页 / 学生 / 绵小城 / 个人中心 已在底部导航，此处不重复）。
 * 每个模块归属唯一分组，互不交叉；同一功能在本页只出现一次。
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

/* 展开/收起：轻微下滑淡入，避免突兀 */
.more-search-fade-enter-active,
.more-search-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.more-search-fade-enter-from,
.more-search-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
@media (prefers-reduced-motion: reduce) {
  .more-search-fade-enter-active,
  .more-search-fade-leave-active { transition: none; }
}

.more-group + .more-group { margin-top: 12px; }

.more-foot {
  margin: 22px 0 0;
  text-align: center;
  font-size: 11.5px;
  color: #c2c7cf;
  letter-spacing: 0.4px;
}
</style>