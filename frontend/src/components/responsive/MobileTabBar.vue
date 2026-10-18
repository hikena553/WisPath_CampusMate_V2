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
  /* 切换时颜色需要过渡，否则选中/取消选中会「瞬切」，与圆托的弹性动画不同步 */
  transition: color 0.2s ease;
}

.tab-item.active {
  color: #409eff;
}

/* 中间标签：凸起圆托（底部导航主入口强调，不显示文字） */
.tab-item.center {
  position: relative;
  justify-content: flex-start;
  padding-bottom: 0;
}

.tab-item.center .tab-icon-wrap {
  width: 42px;
  height: 42px;
  margin-top: -3px;
  border-radius: 50%;
  background: radial-gradient(circle at 32% 26%, #ffffff 0%, #eff6ff 58%, #dbeafe 100%);
  /* 4px 白色描边把圆托从导航栏上沿「顶」出来，外圈一条淡描边保证在浅色内容上也有轮廓 */
  box-shadow:
    0 0 0 4px #fff,
    0 0 0 5px rgba(15, 23, 42, 0.06),
    0 6px 16px rgba(64, 158, 255, 0.24);
  transition:
    transform 0.26s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.26s ease;
}

.tab-item.center .tab-icon-img {
  width: 80%;
  height: 80%;
  border-radius: 0;
  margin-top: 0;
}

.tab-item.center .tab-label {
  display: none;
}

/* 选中态：只加强描边与投影，不做缩放（避免点击后「弹一下变大」） */
.tab-item.center.active .tab-icon-wrap {
  box-shadow:
    0 0 0 4px #fff,
    0 0 0 5px rgba(64, 158, 255, 0.22),
    0 6px 16px rgba(64, 158, 255, 0.34);
}

/* 按下态：必须放在 .active 之后，否则特异性相同时会被覆盖，
   导致「已选中时再点一次没有反馈」；只做轻微下压，同样不放大 */
.tab-item.center:active .tab-icon-wrap {
  transform: scale(0.97);
  transition:
    transform 0.12s ease-out,
    box-shadow 0.12s ease-out;
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
