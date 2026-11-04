<template>
  <div class="lostfound-page">
    <!-- 移动端吸顶子页头；桌面端学生布局有侧边栏，标题由面板自带的 .lf-header 承担 -->
    <SubPageHeader title="失物招领" sub="寻物启事 / 捡到招领" fallback="/student/schedule?tab=service" />

    <div class="lostfound-inner">
      <LostFoundPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import LostFoundPanel from '@/components/service/LostFoundPanel.vue'

/**
 * 失物招领独立页。
 *
 * 这项业务原先只挂在旧「工作台」宫格里（工作台页签在 v5 被消息页取代、整页下线），
 * 学业中心的请假服务子页只融合了请假 / 证明 / 项目三类申请，没有失物招领。
 * 为避免随旧页一起消失，这里把现成的 LostFoundPanel 直接挂成一个独立地址，
 * 入口放在学业中心「请假服务」子页底部。
 */
</script>

<style scoped>
.lostfound-page {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--dt-bg, #f5f6f7);
}

.lostfound-inner {
  flex: 1;
  min-height: 0;
  display: flex;
  padding: 12px;
  /* 面板内部列表自己滚动（.lf-list 是 flex:1 + overflow），容器要有确定高度 */
  height: calc(100dvh - 132px);
}

.lostfound-inner > * {
  flex: 1;
  min-width: 0;
}

/* 移动端标题已由子页头承担，面板头只留「发布」按钮，右对齐 */
@media (max-width: 767px) {
  .lostfound-inner :deep(.lf-header) {
    justify-content: flex-end;
  }
  .lostfound-inner :deep(.lf-header h3) {
    display: none;
  }
}
</style>
