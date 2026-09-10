<template>
  <div class="mobile-tab-bar safe-area-bottom">
    <div
      v-for="item in items"
      :key="item.key"
      :class="['tab-item', { active: activeKey === item.key, center: item.center }]"
      @click="$emit('select', item)"
    >
      <div class="tab-icon-wrap">
        <template v-if="item.iconImg">
          <img :src="item.iconImg" class="tab-icon-img" />
        </template>
        <template v-else>
          <el-icon :size="item.center ? 22 : 20"><component :is="item.icon" /></el-icon>
        </template>
        <span v-if="item.badge && unreadCount" class="tab-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </div>
      <span class="tab-label">{{ item.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface TabItem {
  key: string
  label: string
  icon?: Component
  iconImg?: string
  route: string
  center?: boolean
  badge?: boolean
}

defineProps<{
  items: TabItem[]
  activeKey: string
  unreadCount?: number
}>()

defineEmits<{
  select: [item: TabItem]
}>()
</script>

<style scoped>
.mobile-tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: space-around;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  z-index: 1000;
  padding-bottom: env(safe-area-inset-bottom);
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  flex: 1;
  height: 100%;
  cursor: pointer;
  color: #999;
  -webkit-tap-highlight-color: transparent;
}

.tab-item.active {
  color: #409eff;
}

/* 中间标签样式 */
.tab-item.center {
  position: relative;
}

.tab-item.center .tab-icon-img {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  margin-top: -8px;
}

.tab-item.center.active .tab-icon-img {
  transform: scale(1.1);
  filter: drop-shadow(0 2px 8px rgba(64, 158, 255, 0.3));
}

.tab-label {
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
}

.tab-icon-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

.tab-icon-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-badge {
  position: absolute;
  top: -4px;
  right: -10px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #f56c6c;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
</style>
