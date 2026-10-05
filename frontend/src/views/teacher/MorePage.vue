<template>
  <div class="tui-page">
    <header class="tui-header">
      <div>
        <h2 class="tui-header-title">全部功能</h2>
        <p class="tui-header-sub">按职能分类，点击图标直达</p>
      </div>
    </header>

    <div class="tui-groups">
      <section v-for="g in groups" :key="g.title" class="tui-card">
        <div class="tui-card-head">
          <span>{{ g.title }}</span>
          <span class="tui-group-count">{{ g.items.length }} 项</span>
        </div>

        <div class="tui-grid-nav">
          <button
            v-for="it in g.items"
            :key="it.path"
            class="tui-nav-cell"
            @click="router.push(it.path)"
          >
            <span class="tui-nav-icon" :style="{ background: it.tint, color: it.color }">
              <el-icon :size="20"><component :is="it.icon" /></el-icon>
            </span>
            <span class="tui-nav-label">{{ it.short }}</span>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  Bell, ChatDotRound, Collection, Connection, EditPen, Stamp, Sunny, WarningFilled,
} from '@element-plus/icons-vue'

defineOptions({ name: 'teacher-more' })

const router = useRouter()

/**
 * 「更多」= 非页签模块的宫格入口（首页 / 学生 / 绵小城 / 个人中心 已在底部导航，此处不重复）。
 * 每个模块归属唯一分组，互不交叉。
 */
const groups = [
  {
    title: '学生工作',
    items: [
      { path: '/teacher/approval', short: '审批', icon: Stamp, color: '#b54708', tint: '#fffaeb' },
      { path: '/teacher/crisis', short: '预警', icon: WarningFilled, color: '#d92d20', tint: '#fef3f2' },
      { path: '/teacher/announcement', short: '公告', icon: Bell, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '我的成长',
    items: [
      { path: '/teacher/portfolio', short: '成长档案', icon: Collection, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher/survey', short: '问卷互评', icon: EditPen, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '关怀与沟通',
    items: [
      { path: '/teacher/care-center', short: '关怀', icon: Sunny, color: '#f79009', tint: '#fffaeb' },
      { path: '/teacher/guardian', short: '家校', icon: Connection, color: '#0891b2', tint: '#ecfeff' },
      { path: '/teacher/messages', short: '消息', icon: ChatDotRound, color: '#079455', tint: '#ecfdf3' },
    ],
  },
]
</script>