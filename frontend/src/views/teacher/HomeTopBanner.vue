<template>
  <!-- 首页头部：简约问候卡
       克制留白 + 一条品牌发丝边；吉祥物与品牌点承载产品个性，不再使用整块大渐变。 -->
  <section v-if="isMobile" class="hm-head">
    <div class="hm-head-main">
      <h1 class="hm-head-title">{{ greeting }}，{{ userName }}</h1>
      <p class="hm-head-meta">
        <span class="hm-dot"></span>{{ siteName }} · 教师端
        <span class="hm-sep">·</span>{{ todayShort }}
      </p>
    </div>
    <img :src="siteMascot" :alt="siteName" class="hm-head-mascot" />
  </section>
  <div v-if="isMobile" class="hm-chips">
    <span v-if="pendingCount > 0" class="hm-chip hm-chip-warn">
      <el-icon><Tickets /></el-icon>{{ pendingCount }} 件待办
    </span>
    <span v-if="severeAlertCount > 0" class="hm-chip hm-chip-danger">
      <el-icon><WarningFilled /></el-icon>{{ severeAlertCount }} 条高危预警
    </span>
    <span v-if="pendingCount === 0 && severeAlertCount === 0" class="hm-chip hm-chip-quiet">
      <el-icon><CircleCheck /></el-icon>今日无待办与预警
    </span>
  </div>

  <!-- 桌面端：同款问候卡，状态胶囊右对齐 -->
  <section v-else class="hm-head hm-head-desk">
    <div class="hm-head-main">
      <h2 class="hm-head-title">{{ greeting }}，{{ userName }}</h2>
      <p class="hm-head-meta">
        <span class="hm-dot"></span>{{ siteName }} · 教师端
        <span class="hm-sep">·</span>{{ todayStr }}
      </p>
    </div>
    <div class="hm-chips hm-chips-desk">
      <span v-if="pendingCount > 0" class="hm-chip hm-chip-warn">
        <el-icon><Tickets /></el-icon>{{ pendingCount }} 件待办
      </span>
      <span v-if="severeAlertCount > 0" class="hm-chip hm-chip-danger">
        <el-icon><WarningFilled /></el-icon>{{ severeAlertCount }} 条高危预警
      </span>
      <span v-if="pendingCount === 0 && severeAlertCount === 0" class="hm-chip hm-chip-quiet">
        <el-icon><CircleCheck /></el-icon>今日无待办与预警
      </span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Tickets, WarningFilled, CircleCheck } from '@element-plus/icons-vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName } = useSiteConfig()

// 移动端用短日期，避免元信息行过长
const todayShort = computed(() => {
  const d = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getMonth() + 1}月${d.getDate()}日 星期${week[d.getDay()]}`
})

defineProps<{
  isMobile: boolean
  userName: string
  greeting: string
  pendingCount: number
  severeAlertCount: number
  todayStr: string
}>()
</script>

<style scoped>
/* ===== 问候卡 ===== */
.hm-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(37, 99, 235, 0.12);
  background: linear-gradient(135deg, #ffffff 0%, #f3f8ff 100%);
  box-shadow: 0 1px 2px rgba(15, 17, 21, 0.03);
}
.hm-head-main { min-width: 0; }
.hm-head-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.2px;
  color: #101828;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hm-head-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 5px 0 0;
  font-size: 12px;
  color: #667085;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hm-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
  flex-shrink: 0;
}
.hm-sep { color: #cbd0d8; }
.hm-head-mascot {
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  object-fit: contain;
  filter: drop-shadow(0 4px 10px rgba(37, 99, 235, 0.22));
}

/* ===== 状态胶囊 ===== */
.hm-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.hm-chips-desk { margin-top: 0; flex-shrink: 0; }
.hm-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
}
.hm-chip .el-icon { font-size: 13px; }
.hm-chip-warn { background: #fffaeb; color: #b54708; }
.hm-chip-danger { background: #fef3f2; color: #d92d20; }
.hm-chip-quiet { background: #f2f4f7; color: #667085; font-weight: 500; }

/* ===== 桌面端 ===== */
.hm-head-desk { padding: 16px 20px; }

@media (prefers-reduced-motion: reduce) {
  .hm-dot { box-shadow: none; }
}
</style>