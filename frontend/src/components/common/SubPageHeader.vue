<template>
  <header v-if="isMobile" class="tui-appbar">
    <button class="tui-appbar-back" type="button" aria-label="返回" @click="goBack">
      <el-icon :size="20"><ArrowLeft /></el-icon>
    </button>
    <div class="tui-appbar-title">
      {{ title }}
      <span v-if="sub" class="tui-appbar-sub">{{ sub }}</span>
    </div>
    <div v-if="$slots.right" class="tui-appbar-actions">
      <slot name="right" />
    </div>
  </header>

  <!-- 桌面端返回链路：侧边栏精简后，子页面必须给出明确的「返回」入口与「从哪来」的面包屑。
       仅教师端（fallback 以 /teacher 开头）渲染，学生端与管理端保持原有桌面布局不变。 -->
  <div v-else-if="isTeacherPage" class="tui-back-row">
    <button class="tui-back-btn" type="button" @click="goBack">
      <el-icon :size="16"><ArrowLeft /></el-icon>
      <span>返回</span>
    </button>
    <nav class="tui-crumbs" aria-label="面包屑">
      <template v-for="(c, i) in crumbs" :key="i">
        <span v-if="i > 0" class="tui-crumbs-sep">/</span>
        <a v-if="c.path" class="tui-crumbs-link" @click.prevent="router.push(c.path)">{{ c.label }}</a>
        <span v-else class="tui-crumbs-current">{{ c.label }}</span>
      </template>
    </nav>
    <!-- 桌面端不在此渲染 #right：页面级操作统一收进页面自己的特色头部（TuiPageHero），
         避免与头部里的刷新按钮重复；该插槽在移动端吸顶栏仍照常渲染。 -->
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps<{
  /** 页面标题（移动端吸顶栏 / 桌面端面包屑末级展示） */
  title: string
  /** 无历史记录时的兜底返回路径 */
  fallback: string
  /** 可选副标题，展示在标题下方 */
  sub?: string
}>()

const { isMobile } = useResponsive()
const router = useRouter()
const route = useRoute()

/** 归属父级：这些子路由未在侧边栏单列，面包屑给出其所属的一级入口 */
const PARENT_CRUMBS: { prefix: string; label: string; path: string }[] = [
  { prefix: '/teacher/portfolio', label: '学生档案', path: '/teacher/students' },
  { prefix: '/teacher/survey', label: '学生档案', path: '/teacher/students' },
  { prefix: '/teacher/ai', label: '首页', path: '/teacher' },
]

const isTeacherPage = computed(() => props.fallback.startsWith('/teacher'))

interface Crumb {
  label: string
  /** 有 path 的层级可点击跳转；末级无 path，仅作展示 */
  path?: string
}

/**
 * 面包屑：首页 →（可选父级）→ 当前页。
 * 已单列在侧边栏的一级页面只有「首页 / 当前页」两层；
 * 成长档案、问卷互评等下钻页补出所属父级，避免层级跳跃。
 */
const crumbs = computed<Crumb[]>(() => {
  const home: Crumb = { label: '首页', path: '/teacher' }
  const current: Crumb = { label: props.title }
  if (!isTeacherPage.value) return [home, current]
  const parent = PARENT_CRUMBS.find((p) => route.path.startsWith(p.prefix))
  if (!parent) return [home, current]
  // 归属就是首页时不再重复一层
  if (parent.path === '/teacher') return [home, current]
  return [home, { label: parent.label, path: parent.path }, current]
})

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push(props.fallback)
  }
}
</script>
