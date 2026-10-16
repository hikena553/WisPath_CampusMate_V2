<template>
  <svg
    class="dt-icon"
    :class="{ 'dt-icon--filled': filled }"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="markup"
  />
</template>

<script setup lang="ts">
/**
 * 钉钉风格图标集（DingTalk Style Icons）
 *
 * 对齐钉钉的图标语言：24×24 网格、1.7px 圆头描边、闭合外形，
 * 选中态可用 filled 切换为实心。用于消息页 / 消息中心 / 小绵管家会话，
 * 替换默认组件库图标，使「组件图案」与钉钉保持一致。
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ name: string; size?: number | string; filled?: boolean }>(),
  { size: 22, filled: false },
)

const ICONS: Record<string, string> = {
  // 导航：消息（气泡）
  message:
    '<path d="M3.6 5.8a2.2 2.2 0 0 1 2.2-2.2h12.4a2.2 2.2 0 0 1 2.2 2.2v8.1a2.2 2.2 0 0 1-2.2 2.2H9.9l-3.9 3.1v-3.1H5.8a2.2 2.2 0 0 1-2.2-2.2z"/>',
  // 导航：通讯录（联系人）
  contacts:
    '<circle cx="9.4" cy="8.6" r="3.4"/><path d="M3.6 19.6c0-3.2 2.9-5 6.2-5s5.4 1.4 6.1 3.6"/><path d="M16.2 5.4a3.2 3.2 0 0 1 0 6.4"/><path d="M17.6 14.9c2.1.5 3.4 1.9 3.4 4.1"/>',
  // 导航：通知（铃铛）
  bell:
    '<path d="M12 3.6a5.4 5.4 0 0 0-5.4 5.4v3.3L5 15.4h14l-1.6-3.1V9A5.4 5.4 0 0 0 12 3.6z"/><path d="M9.7 18.1a2.4 2.4 0 0 0 4.6 0"/>',
  // 通知：消息免打扰（铃铛加斜杠）
  bellOff:
    '<path d="M12 3.6a5.4 5.4 0 0 0-5.4 5.4v3.3L5 15.4h9"/><path d="M9.7 18.1a2.4 2.4 0 0 0 4.6 0"/><path d="M4.2 4.2 19.8 19.8"/>',
  // 导航：工作台（宫格）
  grid:
    '<rect x="3.6" y="3.6" width="7" height="7" rx="1.8"/><rect x="13.4" y="3.6" width="7" height="7" rx="1.8"/><rect x="3.6" y="13.4" width="7" height="7" rx="1.8"/><rect x="13.4" y="13.4" width="7" height="7" rx="1.8"/>',
  // 导航：宫格（圆点极简版，同 grid 语义）
  gridDots:
    '<circle cx="6.75" cy="6.75" r="3" fill="currentColor" stroke="none"/><circle cx="17.25" cy="6.75" r="3" fill="currentColor" stroke="none"/><circle cx="6.75" cy="17.25" r="3" fill="currentColor" stroke="none"/><circle cx="17.25" cy="17.25" r="3" fill="currentColor" stroke="none"/>',
  // 导航：我的（人）
  mine:
    '<circle cx="12" cy="8.2" r="3.7"/><path d="M4.9 20.1c0-3.5 3.2-5.6 7.1-5.6s7.1 2.1 7.1 5.6"/>',
  // 动作：新增
  plus: '<path d="M12 5.2v13.6M5.2 12h13.6"/>',
  // 动作：搜索
  search: '<circle cx="11" cy="11" r="6.2"/><path d="M15.6 15.6 20.2 20.2"/>',
  // 动作：返回
  back: '<path d="M14.6 5.4 8 12l6.6 6.6"/>',
  // 动作：进入（右向箭头）
  arrow: '<path d="M9.4 5.4 16 12l-6.6 6.6"/>',
  // 动作：发送
  send: '<path d="M20.4 3.6 3.6 10.4l7 2.6 2.6 7z"/><path d="M20.4 3.6 10.6 13"/>',
  // 动作：置顶会话
  pin: '<path d="M5.4 5.6h13.2"/><path d="M12 19.4V9.6"/><path d="M7.8 13.8 12 9.6l4.2 4.2"/>',
  // 动作：更多
  more: '<circle cx="12" cy="5.8" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="18.2" r="1.5" fill="currentColor" stroke="none"/>',
  // 动作：删除（回收站）
  trash:
    '<path d="M4.6 6.6h14.8"/><path d="M9.4 6.6V4.9a1.3 1.3 0 0 1 1.3-1.3h2.6a1.3 1.3 0 0 1 1.3 1.3v1.7"/><path d="M17.4 6.6l-.9 11.6a1.8 1.8 0 0 1-1.8 1.7H9.3a1.8 1.8 0 0 1-1.8-1.7L6.6 6.6"/><path d="M10.2 10.6v5.6M13.8 10.6v5.6"/>',
  // 动作：勾选
  check: '<path d="M5.2 12.6 9.6 17 19 6.8"/>',
  // 动作：刷新
  refresh: '<path d="M20.2 12a8.2 8.2 0 1 1-2.5-5.9"/><path d="M20.2 4.4v5.4h-5.4"/>',
  // 动作：关闭
  close: '<path d="M6.2 6.2 17.8 17.8M17.8 6.2 6.2 17.8"/>',
  // 动作：总结对话（文本要点）
  summarize:
    '<path d="M4.4 6.6h15.2M4.4 12h9.4M4.4 17.4h12.2"/><path d="M17.6 14.4v3l2.6-1.5z"/>',
  // 动作：最新资讯（报纸）
  news:
    '<rect x="3.6" y="4.8" width="13.2" height="14.4" rx="2"/><path d="M16.8 8.6h2.2a1.6 1.6 0 0 1 1.6 1.6v6.4a2.4 2.4 0 0 1-2.4 2.4H7.8"/><path d="M6.8 8.6h7M6.8 12h7M6.8 15.4h4"/>',
  // 管家（机器人）
  robot:
    '<rect x="4.4" y="7.2" width="15.2" height="11.6" rx="4"/><path d="M12 3.4v3.8"/><circle cx="9" cy="12.6" r="1.3" fill="currentColor" stroke="none"/><circle cx="15" cy="12.6" r="1.3" fill="currentColor" stroke="none"/><path d="M9.6 16h4.8"/>',
  // 空态：无会话
  empty:
    '<path d="M3.6 5.8a2.2 2.2 0 0 1 2.2-2.2h12.4a2.2 2.2 0 0 1 2.2 2.2v8.1a2.2 2.2 0 0 1-2.2 2.2H9.9l-3.9 3.1v-3.1H5.8a2.2 2.2 0 0 1-2.2-2.2z"/><path d="M8.4 9.4h7.2M8.4 12.6h4.4"/>',
}

const markup = computed(() => ICONS[props.name] || ICONS.message)
</script>

<style scoped>
.dt-icon--filled {
  fill: currentColor;
  stroke: none;
}
.dt-icon--filled :deep(path),
.dt-icon--filled :deep(rect),
.dt-icon--filled :deep(circle) {
  /* 实心态下保留语义：由父级 color 决定填充色 */
  fill: currentColor;
  stroke: none;
}
</style>