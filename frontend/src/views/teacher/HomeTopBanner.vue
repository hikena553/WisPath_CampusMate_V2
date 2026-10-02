<template>
  <!-- 移动端头部 -->
  <div v-if="isMobile" class="teacher-header">
    <div class="header-bg-deco"></div>
    <div class="header-main">
      <div class="header-greeting">
        <div class="greeting-badge">
          <span class="badge-dot"></span>
          绵小城 · 教师端
        </div>
        <div class="greeting-text">{{ greeting }}，{{ userName }}</div>
        <div class="greeting-sub">
          <el-tag v-show="pendingCount > 0" type="warning" size="small" effect="plain" style="border:none;background:rgba(255,255,255,0.2);color:#fff;">
            {{ pendingCount }} 件待办
          </el-tag>
          <el-tag v-show="severeAlertCount > 0" type="danger" size="small" effect="plain" style="border:none;background:rgba(255,255,255,0.2);color:#fff;">
            {{ severeAlertCount }} 条高危预警
          </el-tag>
        </div>
      </div>
      <img src="/images/mascot.png" alt="绵小城" class="header-mascot" />
    </div>
  </div>

  <!-- ===== 第一层：欢迎横幅（精简版） ===== -->
  <div v-if="!isMobile" class="welcome-banner">
    <div class="welcome-content">
      <h2 class="welcome-title">{{ greeting }}，{{ userName }}</h2>
      <span class="today-text">{{ todayStr }}</span>
    </div>
    <div class="welcome-tags">
      <el-tag v-if="pendingCount > 0" type="warning" size="small" effect="plain">
        <el-icon><WarningFilled /></el-icon> {{ pendingCount }} 件待办
      </el-tag>
      <el-tag v-if="severeAlertCount > 0" type="danger" size="small" effect="plain">
        <el-icon><WarningFilled /></el-icon> {{ severeAlertCount }} 条高危预警
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'

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
/* ===== Welcome Banner ===== */
.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  border-radius: 10px;
  margin-bottom: 14px;
  border: 1px solid rgba(91, 141, 239, 0.1);
}

.welcome-content {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.welcome-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.today-text {
  font-size: 12px;
  color: #888;
}

.welcome-tags {
  display: flex;
  gap: 6px;
}

/* 移动端头部 */
.teacher-header {
  background: linear-gradient(135deg, #1d4ed8, #2563eb, #3b82f6);
  padding: 16px 14px 32px;
  color: #fff;
  position: relative;
  overflow: visible;
  margin-bottom: -16px;
  border-radius: 0 0 16px 16px;
}

/* 渐隐尾部 */
.teacher-header::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 32px;
  background: linear-gradient(to bottom, transparent, #f5f7fa);
  border-radius: 0 0 16px 16px;
  pointer-events: none;
}
.teacher-header .header-bg-deco {
  position: absolute; top: -30px; right: -30px;
  width: 120px; height: 120px; border-radius: 50%;
  background: rgba(255,255,255,0.08); pointer-events: none;
}
.teacher-header .header-main {
  display: flex; align-items: center; justify-content: space-between;
  position: relative; z-index: 1;
}
.teacher-header .header-greeting { flex: 1; }
.teacher-header .greeting-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; background: rgba(255,255,255,0.18);
  padding: 3px 10px; border-radius: 20px; margin-bottom: 8px;
}
.teacher-header .badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #67e8f9; animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%,100% { opacity:1; transform:scale(1); }
  50% { opacity:0.5; transform:scale(0.7); }
}
.teacher-header .greeting-text {
  font-size: 18px; font-weight: 700; margin-bottom: 4px;
}
.teacher-header .greeting-sub {
  display: flex; gap: 6px; font-size: 13px; opacity: 0.9;
}
.teacher-header .header-mascot {
  width: 64px; height: 64px; object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.2));
  margin-left: 12px; flex-shrink: 0;
}

@media (max-width: 767px) {
  .teacher-header {
    margin-left: -8px;
    margin-right: -8px;
    width: calc(100% + 16px);
  }

  .welcome-banner {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 14px;
  }

  .welcome-content {
    flex-direction: column;
    gap: 2px;
  }

  .welcome-title {
    font-size: 15px;
  }

  .welcome-tags {
    flex-wrap: wrap;
  }
}
</style>