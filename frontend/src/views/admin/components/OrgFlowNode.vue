<template>
  <div
    class="flow-node"
    :class="[`is-${node.type}`, { 'is-selected': selected, 'is-dimmed': dimmed }]"
    :style="nodeStyle"
    @click="emit('open', node)"
  >
    <span class="flow-node-bar" />
    <span v-if="node.type !== 'root'" class="flow-port flow-port-in" />

    <div class="flow-node-row">
      <span class="flow-node-icon"><el-icon><component :is="icon" /></el-icon></span>
      <span class="flow-node-name" :title="node.name">{{ node.name }}</span>
      <span class="flow-node-badge">{{ typeLabel }}</span>
    </div>

    <div class="flow-node-code">
      <template v-if="node.code">{{ node.code }}</template>
      <template v-else-if="node.grade">{{ node.grade }} 级</template>
      <template v-else>—</template>
    </div>

    <div class="flow-node-stats">
      <template v-if="statList.length">
        <span v-for="s in statList" :key="s.label" class="flow-node-stat" :class="{ 'is-acc': s.acc }">
          {{ s.value }} {{ s.label }}
        </span>
      </template>
      <span v-else class="flow-node-stat is-empty">暂无下级</span>
    </div>

    <button
      v-if="showPort"
      class="flow-port-btn"
      :class="{ 'is-count': hasHidden, 'is-expanded': node.hasChildren && expanded }"
      :title="portTitle"
      @click.stop="emit('portClick', node)"
    >
      <span v-if="hasHidden">{{ node.childCount }}</span>
      <el-icon v-else-if="node.hasChildren"><Minus /></el-icon>
      <el-icon v-else><Plus /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, defineOptions } from 'vue'
import { Plus, Minus, Building2, School, Library, BookOpen } from 'lucide-vue-next'
import { NODE_W, NODE_H, TYPE_LABEL, CHILD_UNIT, type FlowNode } from './orgFlow'

defineOptions({ name: 'OrgFlowNode' })

const props = defineProps<{
  node: FlowNode
  expanded: boolean
  selected: boolean
  dimmed: boolean
}>()

const emit = defineEmits<{
  (e: 'open', node: FlowNode): void
  (e: 'portClick', node: FlowNode): void
}>()

const iconMap = { root: Building2, college: School, major: Library, class: BookOpen } as const
const icon = computed(() => iconMap[props.node.type])
const typeLabel = computed(() => TYPE_LABEL[props.node.type])

const nodeStyle = computed(() => ({
  left: `${props.node.x}px`,
  top: `${props.node.y}px`,
  width: `${NODE_W}px`,
  height: `${NODE_H}px`,
}))

const hasHidden = computed(() => props.node.hasChildren && !props.expanded)
const showPort = computed(() => props.node.type !== 'class')

const portTitle = computed(() => {
  if (hasHidden.value) return `展开 ${props.node.childCount} 个下级`
  if (props.node.hasChildren) return '收起下级'
  return `新增${CHILD_UNIT[props.node.type]}`
})

const statList = computed(() => {
  const s = props.node.stats
  const list: { label: string; value: number; acc?: boolean }[] = []
  if (props.node.type === 'class') {
    if (s.studentCount) list.push({ label: '人', value: s.studentCount, acc: true })
    return list
  }
  if (s.childCount) list.push({ label: CHILD_UNIT[props.node.type], value: s.childCount })
  if (s.majorCount) list.push({ label: '专业', value: s.majorCount })
  if (s.classCount) list.push({ label: '班级', value: s.classCount })
  if (s.studentCount) list.push({ label: '人', value: s.studentCount, acc: true })
  return list
})
</script>

<style>
/* ══════════ 工作流节点卡片 ══════════ */
.flow-node {
  position: absolute;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
  padding: 10px 14px;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05), 0 1px 2px rgba(16, 24, 40, 0.04);
  cursor: pointer;
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
  --flow-accent: #409eff;
}
.flow-node.is-root { --flow-accent: #667eea; }
.flow-node.is-college { --flow-accent: #409eff; }
.flow-node.is-major { --flow-accent: #e6a23c; }
.flow-node.is-class { --flow-accent: #67c23a; }

.flow-node:hover {
  border-color: color-mix(in srgb, var(--flow-accent) 45%, #eef0f4);
  box-shadow: 0 8px 22px rgba(16, 24, 40, 0.1), 0 2px 6px rgba(16, 24, 40, 0.05);
}
.flow-node.is-selected {
  border-color: var(--flow-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--flow-accent) 16%, transparent),
    0 8px 22px rgba(16, 24, 40, 0.1);
}
.flow-node.is-dimmed {
  opacity: 0.34;
}

/* 左侧色条 */
.flow-node-bar {
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--flow-accent);
}

/* 端口圆点 */
.flow-port {
  position: absolute;
  top: 50%;
  width: 9px;
  height: 9px;
  margin-top: -4.5px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #c9d3e3;
  z-index: 2;
}
.flow-port-in { left: -5px; }

/* 端口操作按钮（新增下级 / 展开 / 收起） */
.flow-port-btn {
  position: absolute;
  right: -13px;
  top: 50%;
  transform: translateY(-50%);
  width: 26px;
  height: 26px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid #d7dfec;
  background: #fff;
  color: #7a8699;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  z-index: 3;
  transition: all 0.18s ease;
}
.flow-node:hover .flow-port-btn,
.flow-node.is-selected .flow-port-btn {
  opacity: 1;
}
.flow-port-btn:hover {
  color: #fff;
  background: var(--flow-accent);
  border-color: var(--flow-accent);
  box-shadow: 0 2px 8px color-mix(in srgb, var(--flow-accent) 40%, transparent);
}
.flow-port-btn.is-count {
  opacity: 1;
  color: #fff;
  background: var(--flow-accent);
  border-color: var(--flow-accent);
  font-size: 11.5px;
}
.flow-port-btn.is-expanded {
  color: var(--flow-accent);
  border-color: color-mix(in srgb, var(--flow-accent) 45%, #d7dfec);
}

/* 第一行：图标 + 名称 + 类型徽标 */
.flow-node-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.flow-node-icon {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  color: var(--flow-accent);
  background: color-mix(in srgb, var(--flow-accent) 12%, transparent);
}
.flow-node-name {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: #1f2d3d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.flow-node-badge {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 18px;
  padding: 0 7px;
  border-radius: 5px;
  color: var(--flow-accent);
  background: color-mix(in srgb, var(--flow-accent) 11%, transparent);
}

/* 第二行：代码 / 年级 */
.flow-node-code {
  font-size: 11.5px;
  line-height: 16px;
  color: #8a94a6;
  font-family: 'Consolas', 'Courier New', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 第三行：统计 */
.flow-node-stats {
  display: flex;
  flex-wrap: nowrap;
  gap: 5px;
  overflow: hidden;
}
.flow-node-stat {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 17px;
  padding: 0 6px;
  border-radius: 5px;
  color: #7a8699;
  background: #f4f6fa;
}
.flow-node-stat.is-acc {
  color: var(--flow-accent);
  background: color-mix(in srgb, var(--flow-accent) 11%, transparent);
  font-weight: 600;
}
.flow-node-stat.is-empty {
  color: #c3cad6;
  background: transparent;
  padding: 0;
}

/* ══════════ 暗色主题 ══════════ */
html.dark .flow-node {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}
html.dark .flow-node:hover {
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.45);
}
html.dark .flow-node-name { color: #e8e8ea; }
html.dark .flow-node-code { color: #8a8a94; }
html.dark .flow-node-stat { color: #a0a0a8; background: rgba(255, 255, 255, 0.06); }
html.dark .flow-port { background: #1e1e20; border-color: #4a4a55; }
html.dark .flow-port-btn {
  background: #26262a;
  border-color: rgba(255, 255, 255, 0.12);
  color: #a0a0a8;
}
</style>