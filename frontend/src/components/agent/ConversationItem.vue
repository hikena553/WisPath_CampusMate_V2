<template>
  <div :class="['conv-item', { active }]" @click="emit('select')">
    <div class="conv-title" v-html="titleHtml"></div>

    <!-- 桌面端：悬停出 ⋯，点开豆包式下拉菜单 -->
    <el-dropdown
      v-if="!isMobile"
      trigger="click"
      placement="bottom-end"
      @command="onCommand"
      @click.stop
    >
      <button type="button" class="conv-more" aria-label="更多操作">
        <el-icon :size="16"><MoreFilled /></el-icon>
      </button>
      <template #dropdown>
        <el-dropdown-menu class="conv-dropdown-menu">
          <el-dropdown-item :command="conv.pinned ? 'unpin' : 'pin'" class="conv-dropdown-item">
            <span>{{ conv.pinned ? '取消置顶' : '置顶' }}</span>
          </el-dropdown-item>
          <el-dropdown-item command="rename" class="conv-dropdown-item">
            <span>重命名</span>
          </el-dropdown-item>

          <template v-if="stages.length">
            <el-dropdown-item disabled class="conv-dropdown-label">项目阶段</el-dropdown-item>
            <el-dropdown-item
              v-for="s in stages"
              :key="s"
              :command="`stage:${s}`"
              :class="['conv-dropdown-item', { 'is-current': s === conv.project_stage }]"
            >
              <span>{{ s }}</span>
              <el-icon v-if="s === conv.project_stage" class="conv-check"><Check /></el-icon>
            </el-dropdown-item>
          </template>

          <el-dropdown-item command="delete" divided class="conv-dropdown-item danger">
            <span>删除</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <!-- 移动端：⋯ 常显，点击打开豆包式底部操作面板（由 Sidebar 统一托管） -->
    <button v-else type="button" class="conv-more" aria-label="更多操作" @click.stop="emit('menu')">
      <el-icon :size="16"><MoreFilled /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, MoreFilled } from '@element-plus/icons-vue'
import type { Conversation } from '@/stores/conversation'
import { useResponsive } from '@/composables/useResponsive'
import { highlightMatches } from './conversationSearch'
import { stagesOf } from './conversationMeta'

const props = defineProps<{
  conv: Conversation
  active?: boolean
  /** 当前搜索词：用于标题高亮 */
  query?: string
}>()

const emit = defineEmits<{
  select: []
  /** 打开底部操作面板（移动端） */
  menu: []
  /** 菜单命令：pin | unpin | rename | delete */
  command: [cmd: string]
  stage: [stage: string]
}>()

const { isMobile } = useResponsive()

const stages = computed(() => stagesOf(props.conv.project_template))
const titleHtml = computed(() => highlightMatches(props.conv.title, props.query || ''))

/** 阶段项复用同一条 command 通道（stage:xxx），避免菜单里再挂一个事件 */
function onCommand(cmd: string) {
  if (cmd.startsWith('stage:')) {
    emit('stage', cmd.slice('stage:'.length))
    return
  }
  emit('command', cmd)
}
</script>

<style scoped>
/* 豆包式会话行：单行标题 + 悬停才出现的 ⋯，中性浅灰交互色 */
.conv-item {
  display: flex; align-items: center; gap: 4px;
  height: 34px; padding: 0 6px 0 10px; margin: 1px 4px;
  border-radius: 8px; cursor: pointer;
  transition: background .15s ease;
}
.conv-item:hover { background: rgba(15, 23, 42, .05); }
.conv-item.active { background: rgba(15, 23, 42, .08); }

.conv-title {
  flex: 1; min-width: 0;
  font-size: 13px; line-height: 1.4; color: #4b5563;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  transition: color .15s ease;
}
.conv-item:hover .conv-title { color: #1f2937; }
.conv-item.active .conv-title { color: #111827; font-weight: 600; }

/* v-html 注入的高亮片段不带 scope 属性，需要 :deep 才能命中 */
.conv-title :deep(mark.hl) {
  background: rgba(99, 102, 241, .16); color: #4f46e5; font-weight: 600;
  border-radius: 3px; padding: 0 1px;
}

.conv-more {
  flex-shrink: 0; width: 24px; height: 24px; padding: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; background: transparent; border-radius: 6px;
  color: #6b7280; cursor: pointer; opacity: 0;
  transition: opacity .15s ease, background .15s ease, color .15s ease;
}
.conv-more:hover { background: rgba(15, 23, 42, .08); color: #111827; }
.conv-item:hover .conv-more { opacity: 1; }
/* 键盘可达：焦点落上来时同样显示 ⋯ */
.conv-more:focus-visible { opacity: 1; outline: none; }

/* 下拉菜单：豆包式中性灰悬停，不用品牌色 */
.conv-dropdown-menu {
  min-width: 148px; padding: 4px; border-radius: 10px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, .12), 0 0 0 1px rgba(15, 23, 42, .05);
}
.conv-dropdown-item {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  min-height: 34px; padding: 7px 12px; margin: 1px 0;
  border-radius: 7px; font-size: 13px; color: #374151;
  transition: background .12s ease, color .12s ease;
}
.conv-dropdown-item:hover { background: rgba(15, 23, 42, .05); color: #111827; }
.conv-dropdown-item.is-current { color: #4f46e5; font-weight: 500; }
.conv-dropdown-item.danger { color: #ef4444; }
.conv-dropdown-item.danger:hover { background: rgba(239, 68, 68, .07); color: #ef4444; }
.conv-dropdown-label {
  min-height: 24px; padding: 4px 12px; margin: 2px 0 0;
  font-size: 11px; color: #9aa0a6;
}
.conv-check { font-size: 14px; color: #4f46e5; }

@media (max-width: 767px) {
  /* 触屏行：≥44px 可点区域，⋯ 常显且放大，避免误触到"打开对话" */
  .conv-item {
    height: auto; min-height: 46px; gap: 6px; padding: 0 4px 0 10px;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    -webkit-touch-callout: none;
    user-select: none;
  }
  .conv-item:active { background: rgba(15, 23, 42, .08); }
  .conv-title { font-size: 14px; }
  .conv-more {
    opacity: 1; width: 34px; height: 34px; color: #9aa0a6;
    touch-action: manipulation;
  }
  .conv-more:active { background: rgba(15, 23, 42, .1); }
}
</style>