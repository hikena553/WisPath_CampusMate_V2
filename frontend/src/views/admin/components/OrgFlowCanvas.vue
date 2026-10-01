<template>
  <div class="flow-canvas">
    <div
      ref="stageRef"
      class="flow-scroll"
      :class="{ 'is-panning': panning }"
      @mousedown="onMouseDown"
      @wheel="onWheel"
      @click="onBackgroundClick"
    >
      <div class="flow-sizer" :style="sizerStyle">
        <div class="flow-viewport" :style="viewportStyle">
          <svg
            class="flow-edges"
            :width="layout.width"
            :height="layout.height"
            :viewBox="`0 0 ${layout.width} ${layout.height}`"
          >
            <path
              v-for="edge in layout.edges"
              :key="edge.key"
              :d="edge.path"
              class="flow-edge"
              :class="{ 'is-active': activeEdgeKeys.has(edge.key) }"
            />
          </svg>

          <OrgFlowNode
            v-for="node in layout.nodes"
            :key="node.key"
            :node="node"
            :expanded="expanded.has(node.key)"
            :selected="selectedKey === node.key"
            :dimmed="isDimmed(node)"
            @open="emit('open', $event)"
            @port-click="emit('portClick', $event)"
          />
        </div>
      </div>
    </div>

    <!-- 图例 -->
    <div class="flow-legend">
      <span v-for="item in legend" :key="item.type" class="flow-legend-item">
        <i :style="{ background: item.color }" />{{ item.label }}
      </span>
    </div>

    <!-- 缩放控件 -->
    <div class="flow-controls" @mousedown.stop @wheel.stop>
      <button class="flow-ctrl-btn" title="缩小" @click="zoomOut"><el-icon><ZoomOut /></el-icon></button>
      <button class="flow-ctrl-value" title="恢复 100%" @click="resetView">{{ zoomPercent }}%</button>
      <button class="flow-ctrl-btn" title="放大" @click="zoomIn"><el-icon><ZoomIn /></el-icon></button>
      <span class="flow-ctrl-split" />
      <button class="flow-ctrl-btn" title="适应画布" @click="fitView"><el-icon><FullScreen /></el-icon></button>
      <button class="flow-ctrl-btn" title="重置视图" @click="resetView"><el-icon><Refresh /></el-icon></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ZoomIn, ZoomOut, FullScreen, Refresh } from '@element-plus/icons-vue'
import OrgFlowNode from './OrgFlowNode.vue'
import { buildFlowLayout, type FlowNode } from './orgFlow'

const props = defineProps<{
  tree: FlowNode
  expanded: Set<string>
  selectedKey: string | null
  search: string
}>()

const emit = defineEmits<{
  (e: 'open', node: FlowNode): void
  (e: 'portClick', node: FlowNode): void
  (e: 'clear'): void
}>()

const ZOOM_MIN = 0.3
const ZOOM_MAX = 1.6

const layout = computed(() => buildFlowLayout(props.tree, props.expanded))

const activeEdgeKeys = computed(() => {
  const keys = new Set<string>()
  if (!props.selectedKey) return keys
  layout.value.edges.forEach((e) => {
    if (e.from === props.selectedKey || e.to === props.selectedKey) keys.add(e.key)
  })
  return keys
})

/** 搜索：命中节点及其祖先保持高亮，其余淡出 */
const hitKeys = computed<Set<string> | null>(() => {
  const kw = props.search.trim().toLowerCase()
  if (!kw) return null
  const hit = new Set<string>()
  const walk = (n: FlowNode): boolean => {
    const self = [n.name, n.code ?? '', n.description ?? ''].join(' ').toLowerCase().includes(kw)
    let childHit = false
    n.children.forEach((c) => {
      if (walk(c)) childHit = true
    })
    if (self || childHit) hit.add(n.key)
    return self || childHit
  }
  walk(props.tree)
  return hit
})

function isDimmed(node: FlowNode) {
  return hitKeys.value ? !hitKeys.value.has(node.key) : false
}

const legend = [
  { type: 'root', label: '总部', color: '#667eea' },
  { type: 'college', label: '学院', color: '#409eff' },
  { type: 'major', label: '专业', color: '#e6a23c' },
  { type: 'class', label: '班级', color: '#67c23a' },
]

// ─── 缩放 / 平移 ───────────────────────────────────────
const stageRef = ref<HTMLElement | null>(null)
const zoom = ref(1)
const panning = ref(false)
const panOrigin = { x: 0, y: 0, sl: 0, st: 0 }

const zoomPercent = computed(() => Math.round(zoom.value * 100))
const sizerStyle = computed(() => ({
  width: `${Math.round(layout.value.width * zoom.value)}px`,
  height: `${Math.round(layout.value.height * zoom.value)}px`,
}))
const viewportStyle = computed(() => ({
  transform: `scale(${zoom.value})`,
  transformOrigin: '0 0',
}))

const clampZoom = (v: number) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Number(v.toFixed(3))))

function applyZoom(next: number) {
  const stage = stageRef.value
  const z = clampZoom(next)
  if (z === zoom.value) return
  if (!stage) {
    zoom.value = z
    return
  }
  const cx = (stage.scrollLeft + stage.clientWidth / 2) / zoom.value
  const cy = (stage.scrollTop + stage.clientHeight / 2) / zoom.value
  zoom.value = z
  nextTick(() => {
    stage.scrollLeft = cx * z - stage.clientWidth / 2
    stage.scrollTop = cy * z - stage.clientHeight / 2
  })
}

const zoomIn = () => applyZoom(zoom.value + 0.1)
const zoomOut = () => applyZoom(zoom.value - 0.1)

function fitView() {
  const stage = stageRef.value
  if (!stage) return
  const { width, height } = layout.value
  if (!width || !height) return
  zoom.value = clampZoom(
    Math.min((stage.clientWidth - 24) / width, (stage.clientHeight - 24) / height, 1),
  )
  nextTick(() => {
    stage.scrollLeft = Math.max(0, (width * zoom.value - stage.clientWidth) / 2)
    stage.scrollTop = 0
  })
}

function resetView() {
  const stage = stageRef.value
  zoom.value = 1
  nextTick(() => {
    if (stage) {
      stage.scrollLeft = 0
      stage.scrollTop = 0
    }
  })
}

function onMouseDown(e: MouseEvent) {
  const el = e.target as HTMLElement
  if (el.closest('.flow-node') || el.closest('.flow-controls')) return
  const stage = stageRef.value
  if (!stage) return
  panning.value = true
  panOrigin.x = e.clientX
  panOrigin.y = e.clientY
  panOrigin.sl = stage.scrollLeft
  panOrigin.st = stage.scrollTop
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', onPanEnd)
}

function onPanMove(e: MouseEvent) {
  const stage = stageRef.value
  if (!stage) return
  stage.scrollLeft = panOrigin.sl - (e.clientX - panOrigin.x)
  stage.scrollTop = panOrigin.st - (e.clientY - panOrigin.y)
}

function onPanEnd() {
  panning.value = false
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
}

function onWheel(e: WheelEvent) {
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  applyZoom(zoom.value * (e.deltaY > 0 ? 0.92 : 1.08))
}

function onBackgroundClick(e: MouseEvent) {
  if ((e.target as HTMLElement).closest('.flow-node')) return
  emit('clear')
}

// 首次渲染后自动适应画布
let fitted = false
watch(
  () => layout.value.width,
  (w) => {
    if (fitted || !w) return
    fitted = true
    nextTick(fitView)
  },
)

onMounted(() => {
  nextTick(() => {
    if (!fitted) {
      fitted = true
      fitView()
    }
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', onPanEnd)
})

defineExpose({ fitView })
</script>

<style>
/* ══════════ 工作流画布 ══════════ */
.flow-canvas {
  position: relative;
  height: 620px;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  background-color: #f8f9fc;
  background-image: radial-gradient(circle, #dfe4ee 1px, transparent 1px);
  background-size: 20px 20px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05), 0 1px 2px rgba(16, 24, 40, 0.04);
  overflow: hidden;
}

.flow-scroll {
  width: 100%;
  height: 100%;
  overflow: auto;
  cursor: grab;
}
.flow-scroll.is-panning { cursor: grabbing; }
.flow-scroll::-webkit-scrollbar { width: 10px; height: 10px; }
.flow-scroll::-webkit-scrollbar-thumb { background: #ccd6e6; border-radius: 5px; }
.flow-scroll::-webkit-scrollbar-thumb:hover { background: #b6c2d8; }
.flow-scroll::-webkit-scrollbar-track { background: transparent; }

/* transform 不改变布局尺寸，按缩放后尺寸裁剪，
   避免缩小时多余滚动空白、放大时内容被裁切 */
.flow-sizer { position: relative; overflow: hidden; }
.flow-viewport { position: relative; width: max-content; }

.flow-edges {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
  pointer-events: none;
}
.flow-edge {
  fill: none;
  stroke: #c9d3e3;
  stroke-width: 1.6;
  stroke-linecap: round;
  transition: stroke 0.2s ease, stroke-width 0.2s ease;
}
.flow-edge.is-active {
  stroke: #409eff;
  stroke-width: 2.2;
}

/* ── 图例 ── */
.flow-legend {
  position: absolute;
  left: 14px;
  bottom: 14px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 12px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #eef0f4;
  box-shadow: 0 2px 8px rgba(16, 24, 40, 0.06);
  backdrop-filter: blur(6px);
}
.flow-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: #7a8699;
}
.flow-legend-item i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

/* ── 缩放控件 ── */
.flow-controls {
  position: absolute;
  right: 14px;
  bottom: 14px;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 5px 7px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #eef0f4;
  box-shadow: 0 2px 10px rgba(16, 24, 40, 0.08);
  backdrop-filter: blur(6px);
  cursor: default;
}
.flow-ctrl-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: #7a8699;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.16s ease;
}
.flow-ctrl-btn:hover { background: #ecf5ff; color: #409eff; }
.flow-ctrl-value {
  min-width: 46px;
  height: 28px;
  border: none;
  border-radius: 7px;
  background: transparent;
  font-size: 12.5px;
  font-weight: 600;
  color: #4b5264;
  cursor: pointer;
  transition: all 0.16s ease;
}
.flow-ctrl-value:hover { background: #ecf5ff; color: #409eff; }
.flow-ctrl-split {
  width: 1px;
  height: 18px;
  margin: 0 4px;
  background: #eef0f4;
}

/* ══════════ 暗色主题 ══════════ */
html.dark .flow-canvas {
  background-color: #141415;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.09) 1px, transparent 1px);
  border-color: rgba(255, 255, 255, 0.08);
}
html.dark .flow-edge { stroke: #4a4a55; }
html.dark .flow-edge.is-active { stroke: #409eff; }
html.dark .flow-legend,
html.dark .flow-controls {
  background: rgba(30, 30, 32, 0.95);
  border-color: rgba(255, 255, 255, 0.08);
}
html.dark .flow-legend-item { color: #a0a0a8; }
html.dark .flow-ctrl-btn,
html.dark .flow-ctrl-value { color: #a0a0a8; }
html.dark .flow-ctrl-btn:hover,
html.dark .flow-ctrl-value:hover { background: rgba(64, 158, 255, 0.14); color: #409eff; }
html.dark .flow-ctrl-split { background: rgba(255, 255, 255, 0.08); }
html.dark .flow-scroll::-webkit-scrollbar-thumb { background: #3a3a42; }
</style>