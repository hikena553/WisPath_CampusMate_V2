<template>
  <!--
    通用步骤链路条（教师端构件）。
    · 结构沿用全局 .tui-steps 规范（桌面横向 .h，窄屏自动纵向），供多页面复用；
    · 自适应容器宽度：外层容器查询壳 ts-wrap 提供查询上下文，容器窄于 560px 时
      步骤条自动转纵向，不再依赖「整页是否移动端」的 JS 分支；
    · 横向时标题单行省略、说明最多两行，保证四个步骤始终等高对齐。
  -->
  <div class="ts-wrap">
    <ol class="tui-steps h ts-adapt">
      <li v-for="(s, i) in steps" :key="i" class="tui-step" :class="`is-${s.state || 'todo'}`">
        <span class="tui-step-dot">
          <el-icon v-if="(s.state || 'todo') === 'done'" :size="11"><Check /></el-icon>
          <template v-else>{{ i + 1 }}</template>
        </span>
        <span class="tui-step-line"></span>
        <div class="tui-step-body">
          <div class="tui-step-title">{{ s.title }}</div>
          <div v-if="s.desc" class="tui-step-desc">{{ s.desc }}</div>
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import { Check } from '@element-plus/icons-vue'

export interface TuiStepItem {
  title: string
  desc?: string
  /** done 已完成 / current 进行中 / todo 未开始 */
  state?: 'done' | 'current' | 'todo'
}

defineProps<{ steps: TuiStepItem[] }>()
</script>

<style scoped>
/* 容器查询壳：为内部步骤条提供查询上下文（容器查询只作用于后代，故需要这一层包裹） */
.ts-wrap {
  container-type: inline-size;
}

/* 横向排布：标题单行省略 + 说明两行截断，避免窄容器把步骤撑高、彼此不等高 */
.ts-adapt.ts-adapt .tui-step-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ts-adapt.ts-adapt .tui-step-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 容器过窄（< 560px）：自动转纵向链路（类名与全局 `.tui-steps.h` 的移动端回退一致） */
@container (max-width: 560px) {
  .ts-adapt.ts-adapt {
    flex-direction: column;
  }
  .ts-adapt.ts-adapt .tui-step {
    flex: none;
    flex-direction: row;
    gap: 10px;
    padding-bottom: 14px;
  }
  .ts-adapt.ts-adapt .tui-step:last-child {
    padding-bottom: 0;
  }
  .ts-adapt.ts-adapt .tui-step-line {
    left: 8px;
    right: auto;
    top: 21px;
    bottom: 2px;
    width: 1.5px;
    height: auto;
  }
  .ts-adapt.ts-adapt .tui-step-title {
    white-space: normal;
    overflow: visible;
    text-overflow: clip;
  }
  .ts-adapt.ts-adapt .tui-step-desc {
    display: block;
    overflow: visible;
  }
}
</style>