<template>
  <div class="more-page">
    <header class="more-header">
      <h2>全部功能</h2>
      <p class="more-sub">教师端能力总览 · 点击进入对应模块</p>
    </header>

    <section v-for="g in groups" :key="g.title" class="more-group">
      <div class="more-group-title">
        <el-icon :size="14"><component :is="g.icon" /></el-icon>
        <span>{{ g.title }}</span>
      </div>
      <div class="more-grid">
        <button v-for="it in g.items" :key="it.path" class="more-item" @click="router.push(it.path)">
          <span class="more-icon" :style="{ background: it.tint, color: it.color }">
            <el-icon :size="19"><component :is="it.icon" /></el-icon>
          </span>
          <span class="more-body">
            <span class="more-label">{{ it.label }}</span>
            <span class="more-desc">{{ it.desc }}</span>
          </span>
          <el-icon class="more-arrow" :size="14"><ArrowRight /></el-icon>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  ArrowRight, Bell, ChatDotRound, Collection, Connection, DataAnalysis,
  EditPen, Notebook, Stamp, Sunny, User,
} from '@element-plus/icons-vue'

defineOptions({ name: 'teacher-more' })

const router = useRouter()

/** 功能分组：与桌面端侧边栏一一对应，保证移动端也能到达每个模块 */
const groups = [
  {
    title: '教学管理',
    icon: Notebook,
    items: [
      { path: '/teacher/students', label: '学生档案', desc: '画像 / 成长 / 学情诊断', icon: Notebook, color: '#2563eb', tint: '#eff4ff' },
      { path: '/teacher/approval', label: '审批管理', desc: '请假审批 · 销假 · 统计', icon: Stamp, color: '#b54708', tint: '#fffaeb' },
      { path: '/teacher/crisis', label: '预警工作台', desc: '危机干预 · 待随访', icon: Bell, color: '#d92d20', tint: '#fef3f2' },
      { path: '/teacher/messages', label: '消息', desc: '家校与同事沟通', icon: ChatDotRound, color: '#079455', tint: '#ecfdf3' },
    ],
  },
  {
    title: '我的成长',
    icon: Collection,
    items: [
      { path: '/teacher/portfolio', label: '成长档案', desc: '案例 / 荣誉 / 研修 / 成果', icon: Collection, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher/survey', label: '问卷互评', desc: '匿名互评 · 聚合结果', icon: EditPen, color: '#2563eb', tint: '#eff4ff' },
    ],
  },
  {
    title: '关怀与沟通',
    icon: Sunny,
    items: [
      { path: '/teacher/care-center', label: '关怀中心', desc: '关怀日历 / 家访 / 激励', icon: Sunny, color: '#f79009', tint: '#fffaeb' },
      { path: '/teacher/guardian', label: '家校沟通', desc: '联系人 · 台账 · 只读链接', icon: Connection, color: '#0891b2', tint: '#ecfeff' },
    ],
  },
  {
    title: '智能与数据',
    icon: DataAnalysis,
    items: [
      { path: '/teacher/agent', label: '绵小城智能助手', desc: '对话式办理与学情问答', icon: ChatDotRound, color: '#6941c6', tint: '#f4f3ff' },
      { path: '/teacher', label: '我的工作台', desc: '今日待办 / 本周计划 / 工作量', icon: DataAnalysis, color: '#079455', tint: '#ecfdf3' },
      { path: '/teacher/profile', label: '个人中心', desc: '资料 · 改密 · 退出', icon: User, color: '#667085', tint: '#f2f4f7' },
    ],
  },
]
</script>

<style scoped>
.more-page {
  height: 100%;
  overflow-y: auto;
  padding: 8px 4px 24px;
}

.more-header {
  padding: 0 4px;
  margin-bottom: 14px;
}
.more-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
}
.more-sub {
  margin: 3px 0 0;
  font-size: 12px;
  color: #888;
}

.more-group {
  margin-bottom: 18px;
}
.more-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #475467;
  padding: 0 4px;
  margin-bottom: 9px;
}

.more-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.more-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 13px 14px;
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}
.more-item:hover {
  border-color: #d0d5dd;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.06);
  transform: translateY(-1px);
}
.more-item:active { transform: translateY(0); }

.more-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.more-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.more-label {
  font-size: 13.5px;
  font-weight: 600;
  color: #101828;
}
.more-desc {
  font-size: 11.5px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.more-arrow {
  color: #d0d5dd;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .more-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .more-item { padding: 12px 13px; }
}
</style>