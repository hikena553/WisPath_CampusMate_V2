<template>
  <header v-if="isMobile" class="tui-appbar">
    <button class="tui-appbar-back" type="button" aria-label="返回" @click="goBack">
      <el-icon :size="20"><ArrowLeft /></el-icon>
    </button>
    <div class="tui-appbar-title">
      <span class="tui-appbar-txt">
        {{ title }}
      </span>
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

<style scoped>
/* ===== v5 统一子页头规范（学生端）=====
   48px 固定高度 + 白底 + 永久发丝线 + 识别色圆点，与学业中心子页 .subpage-bar 同规格。
   教师端沿用 .tui-page 的 sticky 行为，不受影响。 */
.tui-appbar {
  /* 顶部安全区：白底铺进状态栏，返回键/标题让到状态栏与挖孔下方（Android 15 edge-to-edge） */
  height: calc(clamp(46px, 11.8vw, 52px) + var(--sat, 0px));
  min-height: calc(clamp(46px, 11.8vw, 52px) + var(--sat, 0px));
  gap: 8px;
  /* 左右内边距从 12 收到 4：抬头本身就是满宽（390=视口），
     能让它"更宽"的只有内边距和字号这两个变量。
     12px 时标题可用区只剩 334px（返回键 + 内边距占掉 56px），
     中文六个字以上的页面名会直接贴边；收到 4px 后可用区 344px。 */
  padding: var(--sat, 0px) 4px 0;
  background: var(--sp-surface, #ffffff);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-bottom: 1px solid var(--sp-border, #e9ebee);
}

/* 学生端：固定在顶部，滚动内容从其下方穿过（与学业中心子页头一致） */
:global(.portfolio-page) .tui-appbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
}

.tui-appbar-back {
  width: 34px;
  height: 34px;
  margin-left: 0;
  border-radius: 50%;
  background: transparent;
  color: #1f2430;
}
.tui-appbar-back:hover { background: rgba(20, 23, 26, 0.05); }
.tui-appbar-back:active { background: rgba(20, 23, 26, 0.06); }

.tui-appbar-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 17.5px;
  font-weight: 680;
  letter-spacing: -0.2px;
}
.tui-appbar-txt {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
</style>
