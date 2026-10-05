<template>
  <div class="tui-page">
    <header class="tui-header">
      <div>
        <h2 class="tui-header-title">全部功能</h2>
        <p class="tui-header-sub">按职能分类，每个模块只做一件事</p>
      </div>
    </header>

    <div class="tui-groups">
      <section v-for="g in groups" :key="g.title">
        <div class="tui-group-title">
          <el-icon :size="14"><component :is="g.icon" /></el-icon>
          <span>{{ g.title }}</span>
          <span class="tui-group-count">{{ g.items.length }} 项</span>
        </div>

        <div class="tui-list">
          <button v-for="it in g.items" :key="it.path + it.label" class="tui-row" @click="router.push(it.path)">
            <span class="tui-row-icon" :style="{ background: it.tint, color: it.color }">
              <el-icon :size="18"><component :is="it.icon" /></el-icon>
            </span>
            <span class="tui-row-main">
              <span class="tui-row-label">{{ it.label }}</span>
              <span class="tui-row-desc">{{ it.desc }}</span>
            </span>
            <el-icon class="tui-row-arrow" :size="14"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  ArrowRight, Bell, ChatDotRound, Collection, Connection, DataAnalysis,
  EditPen, Stamp, Sunny, User,
} from '@element-plus/icons-vue'

defineOptions({ name: 'teacher-more' })

const router = useRouter()

/**
 * 功能分类中枢：只放"非底部页签"的模块，学生档案与首页已在底部页签，此处不再重复。
 * 每个模块归属唯一分组，互不交叉。
 */
const groups = [
  {
    title: '学生工作',
    icon: Stamp,
    items: [
      { path: '/teacher/approval', label: '审批管理', desc: '请假审批 · 销假确认 · 统计', icon: Stamp, color: '#b54708', tint: '#fffaeb' },
      { path: '/teacher/crisis', label: '预警工作台', desc: '危机干预 · 随访跟踪', icon: Bell, color: '#d92d20', tint: '#fef3f2' },
      { path: '/teacher/announcement', label: '班级公告', desc: '发布通知 · 紧急程度标记', icon: Bell, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '我的成长',
    icon: Collection,
    items: [
      { path: '/teacher/portfolio', label: '成长档案', desc: '工作案例 · 荣誉 · 研修 · 成果', icon: Collection, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher/survey', label: '问卷互评', desc: '匿名互评 · 聚合结果', icon: EditPen, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '关怀与沟通',
    icon: Sunny,
    items: [
      { path: '/teacher/care-center', label: '关怀中心', desc: '关怀日历 · 家访 · 正向激励', icon: Sunny, color: '#f79009', tint: '#fffaeb' },
      { path: '/teacher/guardian', label: '家校沟通', desc: '联系人 · 沟通台账 · 只读链接', icon: Connection, color: '#0891b2', tint: '#ecfeff' },
      { path: '/teacher/messages', label: '消息', desc: '与同事、学生的会话', icon: ChatDotRound, color: '#079455', tint: '#ecfdf3' },
    ],
  },
  {
    title: '智能与数据',
    icon: DataAnalysis,
    items: [
      { path: '/teacher/agent', label: '绵小城智能助手', desc: '对话式办理与学情问答', icon: ChatDotRound, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher/profile', label: '个人中心', desc: '资料 · 改密 · 退出登录', icon: User, color: '#667085', tint: '#f2f4f7' },
    ],
  },
]
</script>