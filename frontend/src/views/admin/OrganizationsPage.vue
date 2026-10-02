<template>
  <div class="org-page">
    <!-- ═══ 页头 ═══ -->
    <div class="page-header">
      <h2>院系班级管理</h2>
      <div class="header-actions">
        <el-input v-model="keyword" placeholder="搜索学院 / 专业 / 班级" clearable style="width: 220px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button @click="expandAll"><el-icon><Expand /></el-icon>展开全部</el-button>
        <el-button @click="collapseAll"><el-icon><Minimize /></el-icon>收起全部</el-button>
        <el-button type="primary" @click="openCreateDialog('college')">
          <el-icon><Plus /></el-icon>新增节点
        </el-button>
      </div>
    </div>

    <!-- ═══ 指标卡 ═══ -->
    <section class="kpis">
      <div v-for="k in kpis" :key="k.label" class="kpi">
        <div class="kpi-icon" :style="{ color: k.color, background: hexA(k.color, 0.12) }">
          <el-icon :size="19"><component :is="k.icon" /></el-icon>
        </div>
        <div class="kpi-body">
          <span class="kpi-label">{{ k.label }}</span>
          <div class="kpi-value-row">
            <span class="kpi-value" :style="{ color: k.color }">{{ k.value }}</span>
            <span class="kpi-unit">{{ k.unit }}</span>
          </div>
          <span class="kpi-tag">{{ k.tag }}</span>
        </div>
      </div>
    </section>

    <!-- ═══ 节点面板 + 画布 ═══ -->
    <div class="flow-layout">
      <aside class="panel node-panel">
        <div class="panel-head">
          <span class="panel-title"><i />节点面板</span>
        </div>
        <div class="panel-body">
          <button
            v-for="p in palette"
            :key="p.type"
            class="palette-item"
            @click="openCreateDialog(p.type)"
          >
            <span class="palette-icon" :style="{ color: p.color, background: hexA(p.color, 0.12) }">
              <el-icon><component :is="p.icon" /></el-icon>
            </span>
            <span class="palette-text">
              <b>{{ p.label }}</b>
              <em>{{ p.hint }}</em>
            </span>
            <el-icon class="palette-add"><Plus /></el-icon>
          </button>

          <p class="palette-tip">
            点击节点类型添加到画布；也可点击画布中节点右侧的圆形按钮，直接为它新增下级。
          </p>
        </div>
      </aside>

      <div class="canvas-panel">
        <div v-if="!loaded" class="canvas-placeholder">正在加载院系数据…</div>
        <OrgFlowCanvas
          v-else-if="colleges.length"
          :tree="tree"
          :expanded="expandedKeys"
          :selected-key="selectedKey"
          :search="keyword"
          @open="onNodeOpen"
          @port-click="onPortClick"
          @clear="selectedKey = null"
        />
        <div v-else class="canvas-placeholder canvas-empty">
          <el-empty description="还没有院系数据，从左侧节点面板添加第一个学院">
            <el-button type="primary" @click="openCreateDialog('college')">
              <el-icon><Plus /></el-icon>新增学院
            </el-button>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- ═══ 节点详情（模态框） ═══ -->
    <el-dialog
      v-model="drawerVisible"
      class="org-detail-modal"
      width="920px"
      align-center
      :show-close="false"
    >
      <template #header>
        <div v-if="detailNode" class="odm-head" :style="{ '--od-accent': accentOf(detailNode.type) }">
          <span class="odm-head-glow" />
          <div class="odm-head-inner">
            <button class="odm-close" title="关闭" @click="drawerVisible = false">
              <el-icon><X /></el-icon>
            </button>
            <div class="odm-head-main">
              <span class="odm-head-icon"><el-icon><component :is="iconOf(detailNode.type)" /></el-icon></span>
              <div class="odm-head-text">
                <h3>{{ detailNode.name }}</h3>
                <div class="odm-tags">
                  <span class="odm-tag odm-tag-type">{{ typeLabelOf(detailNode.type) }}</span>
                  <span v-if="detailNode.code" class="odm-tag odm-tag-code">{{ detailNode.code }}</span>
                  <span v-if="detailNode.type === 'class' && detailNode.grade" class="odm-tag">
                    {{ detailNode.grade }} 级
                  </span>
                </div>
              </div>
            </div>
            <nav class="odm-crumb">
              <template v-for="(seg, i) in pathSegments" :key="i">
                <span class="odm-crumb-seg" :class="{ 'is-last': i === pathSegments.length - 1 }">{{ seg }}</span>
                <el-icon v-if="i < pathSegments.length - 1" class="odm-crumb-sep"><ArrowRight /></el-icon>
              </template>
            </nav>
          </div>
        </div>
      </template>

      <div v-if="detailNode" class="odm-body" :style="{ '--od-accent': accentOf(detailNode.type) }">
        <div class="odm-inner">
          <!-- 主列 -->
          <div class="odm-main">
            <section v-if="detailStats.length" class="odm-card">
              <div class="odm-card-head"><span class="odm-card-bar" />数据概览</div>
              <div class="odm-tiles">
                <div v-for="s in detailStats" :key="s.label" class="odm-tile">
                  <span class="odm-tile-value">{{ s.value }}</span>
                  <span class="odm-tile-label">{{ s.label }}</span>
                </div>
              </div>
            </section>

            <section class="odm-card">
              <div class="odm-card-head"><span class="odm-card-bar" />基本信息</div>
              <div class="odm-rows">
                <div class="odm-row">
                  <span class="odm-row-k">节点名称</span>
                  <span class="odm-row-v">{{ detailNode.name }}</span>
                </div>
                <div class="odm-row">
                  <span class="odm-row-k">节点类型</span>
                  <span class="odm-row-v">{{ typeLabelOf(detailNode.type) }}</span>
                </div>
                <div v-if="detailNode.code" class="odm-row">
                  <span class="odm-row-k">编码</span>
                  <span class="odm-row-v odm-mono">{{ detailNode.code }}</span>
                </div>
                <div v-if="detailNode.type === 'class'" class="odm-row">
                  <span class="odm-row-k">年级</span>
                  <span class="odm-row-v">{{ detailNode.grade ?? '—' }} 级</span>
                </div>
                <div class="odm-row">
                  <span class="odm-row-k">学生人数</span>
                  <span class="odm-row-v">{{ detailNode.stats.studentCount }} 人</span>
                </div>
                <div class="odm-row odm-row-block">
                  <span class="odm-row-k">描述</span>
                  <span class="odm-row-v">{{ detailNode.description || '—' }}</span>
                </div>
              </div>
            </section>
          </div>

          <!-- 侧列 -->
          <aside class="odm-side">
            <section class="odm-card">
              <div class="odm-card-head"><span class="odm-card-bar" />组织路径</div>
              <ol class="odm-steps">
                <li
                  v-for="(seg, i) in pathSegments"
                  :key="i"
                  class="odm-step"
                  :class="{ 'is-last': i === pathSegments.length - 1 }"
                >
                  <span class="odm-step-dot" />
                  <span class="odm-step-name">{{ seg }}</span>
                </li>
              </ol>
            </section>

            <section class="odm-card">
              <div class="odm-card-head"><span class="odm-card-bar" />层级关系</div>
              <div class="odm-rows">
                <div class="odm-row">
                  <span class="odm-row-k">上级归属</span>
                  <span class="odm-row-v">{{ parentPath }}</span>
                </div>
                <div class="odm-row">
                  <span class="odm-row-k">下级组织</span>
                  <span class="odm-row-v">{{ childSummary }}</span>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>

      <template #footer>
        <div class="odm-footer">
          <span class="odm-footer-hint">
            {{ detailNode ? `${typeLabelOf(detailNode.type)}节点` : '' }}
          </span>
          <div class="odm-footer-actions">
            <el-button v-if="detailNode && detailNode.type !== 'class'" @click="onAddChildFromDrawer">
              <el-icon><Plus /></el-icon>新增下级
            </el-button>
            <el-button v-if="detailNode && detailNode.type !== 'root'" type="danger" plain @click="confirmDelete(detailNode)">
              <el-icon><Trash2 /></el-icon>删除
            </el-button>
            <el-button v-if="detailNode" type="primary" @click="openEditDialog(detailNode)">
              <el-icon><PenLine /></el-icon>编辑内容
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- ═══ 新增 / 编辑节点弹窗 ═══ -->
    <el-dialog
      v-model="dialogVisible"
      class="org-dialog"
      width="560px"
      align-center
      :show-close="false"
    >
      <template #header>
        <div class="odg-head">
          <span class="odg-head-icon" :style="{ color: formAccent, background: hexA(formAccent, 0.12) }">
            <el-icon><component :is="iconOf(form.nodeType)" /></el-icon>
          </span>
          <div class="odg-head-text">
            <h3>{{ dialogMode === 'create' ? '新增节点' : '编辑节点' }}</h3>
            <p>{{ dialogMode === 'create' ? '选择节点类型并填写信息，保存后即出现在画布中' : '修改该节点的基本信息与归属关系' }}</p>
          </div>
          <button class="odg-close" title="关闭" @click="dialogVisible = false">
            <el-icon><X /></el-icon>
          </button>
        </div>
      </template>

      <el-form :model="form" label-position="top" class="odg-form">
        <section class="odg-sec">
          <div class="odg-sec-head">节点类型</div>
          <div class="odg-types">
            <button
              v-for="t in typeCards"
              :key="t.type"
              type="button"
              class="odg-type"
              :class="{ 'is-active': form.nodeType === t.type, 'is-locked': dialogMode === 'edit' }"
              :style="{ '--tc': t.color }"
              @click="pickType(t.type)"
            >
              <span class="odg-type-icon"><el-icon><component :is="t.icon" /></el-icon></span>
              <b>{{ t.label }}</b>
              <em>{{ t.hint }}</em>
              <span class="odg-type-check"><el-icon><Check /></el-icon></span>
            </button>
          </div>
        </section>

        <section class="odg-sec">
          <div class="odg-sec-head">归属关系</div>
          <el-form-item v-if="form.nodeType === 'major'" label="所属学院" required>
            <el-select v-model="form.parentId" placeholder="请选择学院" style="width: 100%">
              <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-else-if="form.nodeType === 'class'" label="所属专业" required>
            <el-select v-model="form.parentId" placeholder="请选择专业" style="width: 100%">
              <el-option
                v-for="m in majors"
                :key="m.id"
                :label="`${m.college_name} - ${m.name}`"
                :value="m.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-else label="所属上级">
            <el-input value="学校院系组织（总部）" disabled />
          </el-form-item>
        </section>

        <section class="odg-sec">
          <div class="odg-sec-head">基本信息</div>
          <div class="odg-grid">
            <el-form-item :label="`${typeLabelOf(form.nodeType)}名称`" required>
              <el-input v-model="form.name" :placeholder="namePlaceholder" maxlength="50" show-word-limit />
            </el-form-item>
            <el-form-item v-if="form.nodeType !== 'class'" :label="`${typeLabelOf(form.nodeType)}编码`" required>
              <el-input v-model="form.code" :placeholder="codePlaceholder" maxlength="20" />
            </el-form-item>
            <el-form-item v-else label="年级">
              <el-input-number v-model="form.grade" :min="2000" :max="2035" style="width: 100%" />
            </el-form-item>
          </div>
          <el-form-item v-if="form.nodeType !== 'class'" label="描述">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              :placeholder="`${typeLabelOf(form.nodeType)}简介`"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>
        </section>
      </el-form>

      <template #footer>
        <div class="odg-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            {{ dialogMode === 'create' ? '确认新增' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Expand, Minimize, Plus, Trash2, PenLine, X, ArrowRight, Check,
  School, Library, BookOpen, Users,
} from 'lucide-vue-next'
import OrgFlowCanvas from './components/OrgFlowCanvas.vue'
import {
  collectKeys, emptyStats, findFlowNode, findFlowPath,
  CHILD_UNIT, TYPE_LABEL, type FlowNode, type FlowNodeType,
} from './components/orgFlow'
import { getStudentStats } from '@/api/admin'
import type { College, Major, ClassGroup } from '@/types'
import {
  getColleges, createCollege, updateCollege, deleteCollege,
  getMajors, createMajor, updateMajor, deleteMajor,
  getClassGroups, createClassGroup, updateClassGroup, deleteClassGroup,
} from '@/api/organization'

const ROOT_KEY = 'root-0'

// ─── 数据 ─────────────────────────────────────────────
const colleges = ref<College[]>([])
const majors = ref<Major[]>([])
const classGroups = ref<ClassGroup[]>([])
const studentTotal = ref(0)
const loaded = ref(false)
const keyword = ref('')

/** 已归属到班级的学生数（按班级真实人数汇总） */
const assignedStudents = computed(() =>
  classGroups.value.reduce((sum, cg) => sum + (cg.student_count ?? 0), 0),
)
/** 未分配到班级的学生数，用于解释「学院之和 ≠ 全校总数」 */
const unassignedStudents = computed(() => Math.max(0, studentTotal.value - assignedStudents.value))

const accentMap: Record<FlowNodeType, string> = {
  root: '#667eea',
  college: '#409eff',
  major: '#e6a23c',
  class: '#67c23a',
}
const iconMap = { root: School, college: School, major: Library, class: BookOpen } as const

const accentOf = (t: FlowNodeType) => accentMap[t]
const iconOf = (t: FlowNodeType) => iconMap[t]
const typeLabelOf = (t: FlowNodeType) => TYPE_LABEL[t]
const childUnitOf = (t: FlowNodeType) => CHILD_UNIT[t]

function hexA(hex: string, alpha: number) {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}

const kpis = computed(() => [
  { label: '学院总数', value: colleges.value.length, unit: '个', tag: '一级组织', color: '#409eff', icon: School },
  { label: '专业总数', value: majors.value.length, unit: '个', tag: '二级组织', color: '#e6a23c', icon: Library },
  { label: '班级总数', value: classGroups.value.length, unit: '个', tag: '三级组织', color: '#67c23a', icon: BookOpen },
  {
    label: '学生总数',
    value: studentTotal.value,
    unit: '人',
    tag: unassignedStudents.value > 0 ? `其中 ${unassignedStudents.value} 人未分配班级` : '在册学生',
    color: '#667eea',
    icon: Users,
  },
])

const palette = [
  { type: 'college' as FlowNodeType, label: '学院', hint: '一级组织节点', color: '#409eff', icon: School },
  { type: 'major' as FlowNodeType, label: '专业', hint: '挂在学院之下', color: '#e6a23c', icon: Library },
  { type: 'class' as FlowNodeType, label: '班级', hint: '挂在专业之下', color: '#67c23a', icon: BookOpen },
]

const typeCards = [
  { type: 'college' as FlowNodeType, label: '学院', hint: '一级组织', color: '#409eff', icon: School },
  { type: 'major' as FlowNodeType, label: '专业', hint: '隶属学院', color: '#e6a23c', icon: Library },
  { type: 'class' as FlowNodeType, label: '班级', hint: '隶属专业', color: '#67c23a', icon: BookOpen },
]

/** 构建 总部 → 学院 → 专业 → 班级 层级树 */
const tree = computed<FlowNode>(() => {
  const majorsByCollege = new Map<number, FlowNode[]>()
  majors.value.forEach((m) => {
    const node: FlowNode = {
      key: `major-${m.id}`, type: 'major', id: m.id,
      name: m.name, code: m.code, description: m.description,
      stats: emptyStats(), hasChildren: false, childCount: 0,
      children: [], raw: m, depth: 0, x: 0, y: 0,
    }
    const list = majorsByCollege.get(m.college_id) ?? []
    list.push(node)
    majorsByCollege.set(m.college_id, list)
  })

  const classesByMajor = new Map<number, FlowNode[]>()
  classGroups.value.forEach((cg) => {
    const node: FlowNode = {
      key: `class-${cg.id}`, type: 'class', id: cg.id,
      name: cg.name, code: null, description: null, grade: cg.grade,
      stats: { ...emptyStats(), studentCount: cg.student_count ?? 0 },
      hasChildren: false, childCount: 0,
      children: [], raw: cg, depth: 0, x: 0, y: 0,
    }
    const list = classesByMajor.get(cg.major_id) ?? []
    list.push(node)
    classesByMajor.set(cg.major_id, list)
  })

  const collegeNodes = colleges.value.map((c) => {
    const node: FlowNode = {
      key: `college-${c.id}`, type: 'college', id: c.id,
      name: c.name, code: c.code, description: c.description,
      stats: emptyStats(), hasChildren: false, childCount: 0,
      children: [], raw: c, depth: 0, x: 0, y: 0,
    }
    node.children = majorsByCollege.get(c.id) ?? []
    node.children.forEach((m) => {
      m.children = classesByMajor.get(m.id) ?? []
      m.childCount = m.children.length
      m.hasChildren = m.childCount > 0
      m.children.forEach((cl) => {
        m.stats.studentCount += cl.stats.studentCount
      })
    })
    node.childCount = node.children.length
    node.hasChildren = node.childCount > 0
    node.children.forEach((m) => {
      node.stats.classCount += m.childCount
      node.stats.studentCount += m.stats.studentCount
    })
    node.stats.majorCount = node.childCount
    return node
  })

  return {
    key: ROOT_KEY, type: 'root', id: 0,
    name: '学校院系组织', code: null,
    description: '全校 学院 → 专业 → 班级 的层级架构',
    stats: {
      childCount: collegeNodes.length,
      majorCount: majors.value.length,
      classCount: classGroups.value.length,
      studentCount: studentTotal.value,
    },
    hasChildren: collegeNodes.length > 0,
    childCount: collegeNodes.length,
    children: collegeNodes,
    depth: 0, x: 0, y: 0,
  }
})

// ─── 展开状态：默认只展开一级节点 ──────────────────────
const expandedKeys = ref<Set<string>>(new Set([ROOT_KEY]))

function expandAll() {
  expandedKeys.value = collectKeys(tree.value)
}

function collapseAll() {
  expandedKeys.value = new Set([ROOT_KEY])
}

function toggleNode(key: string) {
  const next = new Set(expandedKeys.value)
  next.has(key) ? next.delete(key) : next.add(key)
  expandedKeys.value = next
}

// ─── 选中节点 ─────────────────────────────────────────
const selectedKey = ref<string | null>(null)
const drawerVisible = ref(false)

const detailNode = computed(() =>
  selectedKey.value ? findFlowNode(tree.value, selectedKey.value) : null,
)

const pathSegments = computed(() => {
  if (!selectedKey.value) return []
  return findFlowPath(tree.value, selectedKey.value).map((n) => n.name)
})
const parentPath = computed(() =>
  pathSegments.value.length > 1 ? pathSegments.value.slice(0, -1).join(' / ') : '—',
)

const childSummary = computed(() => {
  const n = detailNode.value
  if (!n) return '—'
  if (n.type === 'class') return '班级为最末级，无下级'
  return `${n.childCount} 个${childUnitOf(n.type)}`
})

const detailStats = computed(() => {
  const n = detailNode.value
  if (!n) return []
  if (n.type === 'class') {
    return [{ label: '学生人数', value: n.stats.studentCount }]
  }
  if (n.type === 'root') {
    return [
      { label: '学院', value: n.stats.childCount },
      { label: '专业', value: n.stats.majorCount },
      { label: '班级', value: n.stats.classCount },
      { label: '学生', value: n.stats.studentCount },
    ]
  }
  if (n.type === 'college') {
    return [
      { label: '专业', value: n.stats.majorCount },
      { label: '班级', value: n.stats.classCount },
      { label: '学生', value: n.stats.studentCount },
    ]
  }
  return [
    { label: '班级', value: n.stats.classCount },
    { label: '学生', value: n.stats.studentCount },
  ]
})

function onNodeOpen(node: FlowNode) {
  selectedKey.value = node.key
  drawerVisible.value = true
}

function onPortClick(node: FlowNode) {
  if (node.hasChildren) {
    toggleNode(node.key)
    return
  }
  if (node.type === 'class') return
  const childType: FlowNodeType =
    node.type === 'root' ? 'college' : node.type === 'college' ? 'major' : 'class'
  openCreateDialog(childType, node.type === 'root' ? undefined : node.id)
}

// ─── 新增 / 编辑弹窗 ──────────────────────────────────
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingId = ref(0)
const saving = ref(false)

const form = reactive({
  nodeType: 'college' as FlowNodeType,
  parentId: 0,
  name: '',
  code: '',
  description: '',
  grade: new Date().getFullYear(),
})

const formAccent = computed(() => accentOf(form.nodeType))

const namePlaceholder = computed(
  () => ({ college: '如：软件学院', major: '如：软件工程', class: '如：2024级软件工程1班', root: '' })[form.nodeType],
)
const codePlaceholder = computed(
  () => ({ college: '如：SE、DS', major: '如：SE01', class: '', root: '' })[form.nodeType],
)

function onTypeChange() {
  form.parentId =
    form.nodeType === 'major'
      ? colleges.value[0]?.id ?? 0
      : form.nodeType === 'class'
        ? majors.value[0]?.id ?? 0
        : 0
}

function pickType(type: FlowNodeType) {
  if (dialogMode.value === 'edit' || form.nodeType === type) return
  form.nodeType = type
  onTypeChange()
}

function openCreateDialog(type: FlowNodeType, parentId?: number) {
  dialogMode.value = 'create'
  editingId.value = 0
  form.nodeType = type
  form.name = ''
  form.code = ''
  form.description = ''
  form.grade = new Date().getFullYear()
  form.parentId =
    parentId ??
    (type === 'major'
      ? colleges.value[0]?.id ?? 0
      : type === 'class'
        ? majors.value[0]?.id ?? 0
        : 0)
  dialogVisible.value = true
}

function openEditDialog(node: FlowNode) {
  drawerVisible.value = false
  dialogMode.value = 'edit'
  editingId.value = node.id
  form.nodeType = node.type
  form.name = node.name
  form.code = node.code ?? ''
  form.description = node.description ?? ''
  form.grade = node.grade ?? new Date().getFullYear()
  form.parentId =
    node.type === 'major'
      ? (node.raw as Major).college_id
      : node.type === 'class'
        ? (node.raw as ClassGroup).major_id
        : 0
  dialogVisible.value = true
}

function onAddChildFromDrawer() {
  const node = detailNode.value
  if (!node || node.type === 'class') return
  const childType: FlowNodeType =
    node.type === 'root' ? 'college' : node.type === 'college' ? 'major' : 'class'
  drawerVisible.value = false
  openCreateDialog(childType, node.type === 'root' ? undefined : node.id)
}

function validate() {
  const label = typeLabelOf(form.nodeType)
  if (!form.name.trim()) {
    ElMessage.warning(`请填写${label}名称`)
    return false
  }
  if (form.nodeType !== 'class' && !form.code.trim()) {
    ElMessage.warning(`请填写${label}编码`)
    return false
  }
  if (form.nodeType === 'major' && !form.parentId) {
    ElMessage.warning('请选择所属学院')
    return false
  }
  if (form.nodeType === 'class' && !form.parentId) {
    ElMessage.warning('请选择所属专业')
    return false
  }
  return true
}

async function handleSave() {
  if (!validate()) return
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      if (form.nodeType === 'college') {
        await createCollege({ name: form.name, code: form.code, description: form.description })
      } else if (form.nodeType === 'major') {
        await createMajor({
          college_id: form.parentId, name: form.name, code: form.code, description: form.description,
        })
        expandedKeys.value = new Set([...expandedKeys.value, `college-${form.parentId}`])
      } else {
        await createClassGroup({ major_id: form.parentId, name: form.name, grade: form.grade })
        expandedKeys.value = new Set([...expandedKeys.value, `major-${form.parentId}`])
      }
      ElMessage.success('新增成功')
    } else {
      const id = editingId.value
      if (form.nodeType === 'college') {
        await updateCollege(id, { name: form.name, code: form.code, description: form.description })
      } else if (form.nodeType === 'major') {
        await updateMajor(id, {
          college_id: form.parentId, name: form.name, code: form.code, description: form.description,
        })
      } else {
        await updateClassGroup(id, { major_id: form.parentId, name: form.name, grade: form.grade })
      }
      ElMessage.success('修改成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

// ─── 删除 ─────────────────────────────────────────────
async function confirmDelete(node: FlowNode) {
  if (node.type === 'root') return
  try {
    await ElMessageBox.confirm(
      `确认删除该${typeLabelOf(node.type)}「${node.name}」？其下所有子级将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    if (node.type === 'college') await deleteCollege(node.id)
    else if (node.type === 'major') await deleteMajor(node.id)
    else await deleteClassGroup(node.id)
    ElMessage.success('删除成功')
    if (selectedKey.value === node.key) {
      selectedKey.value = null
      drawerVisible.value = false
    }
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

// ─── 加载 ─────────────────────────────────────────────
async function loadData() {
  const [c, m, cg, stats] = await Promise.all([
    getColleges(), getMajors(), getClassGroups(), getStudentStats(),
  ])
  colleges.value = c as any
  majors.value = m as any
  classGroups.value = cg as any
  // 学生总数与「学生管理」页同源，保证两处一致
  studentTotal.value = stats.total
}

onMounted(async () => {
  try {
    await loadData()
  } finally {
    loaded.value = true
  }
})
</script>

<style scoped>
.org-page {
  padding: 16px;
}

/* ═══ 页头 ═══ */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2d3d;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* ═══ 指标卡 ═══ */
.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.kpi {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.kpi-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kpi-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.kpi-label {
  font-size: 12px;
  color: #8a94a6;
}
.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 3px;
}
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.kpi-unit {
  font-size: 11px;
  color: #b0b8c4;
}
.kpi-tag {
  font-size: 11px;
  color: #b0b8c4;
}

/* ═══ 布局：节点面板 + 画布 ═══ */
.flow-layout {
  display: flex;
  align-items: stretch;
  gap: 12px;
}
.panel {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.node-panel {
  width: 216px;
  flex-shrink: 0;
}
.panel-head {
  padding: 12px 16px 10px;
  border-bottom: 1px solid #f1f3f7;
  flex-shrink: 0;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
}
.panel-title i {
  width: 3px;
  height: 13px;
  border-radius: 2px;
  background: #667eea;
}
.panel-body {
  padding: 12px;
  flex: 1;
  min-height: 0;
}

.palette-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid #eef0f4;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}
.palette-item:hover {
  border-color: #d6e4ff;
  background: #f7faff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
}
.palette-icon {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.palette-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.palette-text b {
  font-size: 13px;
  font-weight: 600;
  color: #1f2d3d;
}
.palette-text em {
  font-size: 11px;
  font-style: normal;
  color: #b0b8c4;
}
.palette-add {
  flex-shrink: 0;
  font-size: 13px;
  color: #c3cad6;
}
.palette-item:hover .palette-add {
  color: #409eff;
}
.palette-tip {
  margin: 12px 2px 0;
  font-size: 11.5px;
  line-height: 1.7;
  color: #b0b8c4;
}

.canvas-panel {
  flex: 1;
  min-width: 0;
}
.canvas-placeholder {
  height: 620px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}

/* ═══ 暗色主题（页面主体） ═══ */
:global(html.dark .org-page .page-header h2) { color: #e8e8ea; }
:global(html.dark .org-page .kpi),
:global(html.dark .org-page .panel),
:global(html.dark .org-page .canvas-placeholder) {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}
:global(html.dark .org-page .kpi-label),
:global(html.dark .org-page .kpi-unit),
:global(html.dark .org-page .kpi-tag) { color: #8a8a94; }
:global(html.dark .org-page .panel-title) { color: #e8e8ea; }
:global(html.dark .org-page .panel-head) { border-bottom-color: rgba(255, 255, 255, 0.06); }
:global(html.dark .org-page .palette-item) {
  background: #26262a;
  border-color: rgba(255, 255, 255, 0.08);
}
:global(html.dark .org-page .palette-text b) { color: #e8e8ea; }

@media (max-width: 1200px) {
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .flow-layout { flex-direction: column; }
  .node-panel { width: 100%; }
  .panel-body { display: flex; flex-wrap: wrap; gap: 8px; }
  .palette-item { width: calc(50% - 4px); margin-bottom: 0; }
  .palette-tip { width: 100%; margin-top: 4px; }
}
</style>

<!-- ════════════════════════════════════════════════════════
     详情模态框 / 新增弹窗（teleport 到 body，需非 scoped 样式）
     设计参考 Ant Design Pro 的 ProDescriptions、vben-admin 的详情面板
     ════════════════════════════════════════════════════════ -->
<style>
/* ---------- 模态框外壳 ---------- */
.el-dialog.org-detail-modal {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-width: 94vw;
  border-radius: 16px;
  background: #f7f8fb;
  box-shadow: 0 18px 48px rgba(16, 24, 40, 0.16);
}
.org-detail-modal .el-dialog__header {
  padding: 0;
  margin: 0;
  flex-shrink: 0;
}
.org-detail-modal .el-dialog__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0;
  max-height: 58vh;
  /* 隐藏滚动条（仍可滚动） */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.org-detail-modal .el-dialog__body::-webkit-scrollbar {
  width: 0;
  height: 0;
}
.org-detail-modal .el-dialog__footer {
  flex-shrink: 0;
  padding: 0;
  border-top: 1px solid #eef0f4;
  background: #fff;
}

/* ---------- 渐变信息头 ---------- */
.odm-head {
  --od-accent: #409eff;
  position: relative;
  overflow: hidden;
  padding: 18px 24px 14px;
  background:
    radial-gradient(120% 150% at 0% 0%, color-mix(in srgb, var(--od-accent) 18%, transparent) 0%, transparent 58%),
    linear-gradient(180deg, #ffffff 0%, #f5f8fd 100%);
  border-bottom: 1px solid #eef0f4;
}
.odm-head-glow {
  position: absolute;
  right: -60px;
  top: -90px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--od-accent) 16%, transparent);
  filter: blur(40px);
  pointer-events: none;
}
.odm-head-inner {
  position: relative;
}
.odm-close {
  position: absolute;
  right: 0;
  top: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.72);
  color: #7a8699;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.16s ease;
}
.odm-close:hover {
  background: #fff;
  color: #f56c6c;
}
.odm-head-main {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-right: 42px;
}
.odm-head-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--od-accent);
  background: #fff;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--od-accent) 22%, transparent);
}
.odm-head-text {
  min-width: 0;
}
.odm-head-text h3 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  line-height: 1.35;
  color: #1f2d3d;
  word-break: break-all;
}
.odm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}
.odm-tag {
  font-size: 11.5px;
  line-height: 20px;
  padding: 0 9px;
  border-radius: 6px;
  color: #6b7688;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #e7ecf4;
}
.odm-tag-type {
  color: var(--od-accent);
  background: color-mix(in srgb, var(--od-accent) 12%, transparent);
  border-color: color-mix(in srgb, var(--od-accent) 26%, transparent);
  font-weight: 600;
}
.odm-tag-code {
  font-family: 'Consolas', 'Courier New', monospace;
}
.odm-crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 3px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e3e8f1;
}
.odm-crumb-seg {
  font-size: 12px;
  color: #8a94a6;
}
.odm-crumb-seg.is-last {
  color: var(--od-accent);
  font-weight: 600;
}
.odm-crumb-sep {
  font-size: 11px;
  color: #c3cad6;
}

/* ---------- 主体两列布局 ---------- */
.odm-body {
  --od-accent: #409eff;
  padding: 18px 24px 22px;
}
.odm-inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: start;
}
.odm-main,
.odm-side {
  min-width: 0;
}

/* ---------- 卡片 ---------- */
.odm-card {
  padding: 16px 18px 18px;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
}
.odm-card + .odm-card {
  margin-top: 18px;
}
.odm-card-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 14px;
  font-size: 14px;
  font-weight: 600;
  color: #2b3245;
}
.odm-card-bar {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--od-accent);
}

/* ---------- 数据概览瓦片 ---------- */
.odm-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}
.odm-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 18px 10px;
  border-radius: 12px;
  border: 1px solid #eef0f4;
  background: linear-gradient(180deg, color-mix(in srgb, var(--od-accent) 8%, #fff) 0%, #fff 100%);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.odm-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 22px rgba(16, 24, 40, 0.08);
}
.odm-tile-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--od-accent);
  font-variant-numeric: tabular-nums;
}
.odm-tile-label {
  font-size: 12px;
  color: #8a94a6;
}

/* ---------- 键值行 ---------- */
.odm-rows {
  display: flex;
  flex-direction: column;
}
.odm-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 2px;
  border-bottom: 1px solid #f4f6f9;
}
.odm-row:last-child {
  border-bottom: none;
}
.odm-row-k {
  flex-shrink: 0;
  width: 84px;
  font-size: 12.5px;
  color: #8a94a6;
}
.odm-row-v {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  color: #2b3245;
  text-align: right;
  word-break: break-all;
}
.odm-row-block {
  align-items: flex-start;
}
.odm-row-block .odm-row-v {
  text-align: left;
  line-height: 1.75;
  color: #5b6478;
}
.odm-mono {
  font-family: 'Consolas', 'Courier New', monospace;
  letter-spacing: 0.3px;
}

/* ---------- 组织路径（竖向步骤条） ---------- */
.odm-steps {
  list-style: none;
  margin: 0;
  padding: 2px 0 0 4px;
}
.odm-step {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 18px;
}
.odm-step:last-child {
  padding-bottom: 0;
}
.odm-step::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 14px;
  bottom: -2px;
  width: 1.5px;
  background: #e3e8f1;
}
.odm-step:last-child::before {
  display: none;
}
.odm-step-dot {
  position: relative;
  z-index: 1;
  width: 11px;
  height: 11px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #c9d3e3;
}
.odm-step.is-last .odm-step-dot {
  border-color: var(--od-accent);
  background: var(--od-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--od-accent) 18%, transparent);
}
.odm-step-name {
  font-size: 13px;
  color: #5b6478;
}
.odm-step.is-last .odm-step-name {
  color: var(--od-accent);
  font-weight: 600;
}

/* ---------- 底部操作条 ---------- */
.odm-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 24px;
}
.odm-footer-hint {
  font-size: 12.5px;
  color: #9aa3b2;
}
.odm-footer-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 860px) {
  .odm-inner {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* ══════════ 新增 / 编辑弹窗 ══════════ */
.org-dialog {
  border-radius: 16px;
  overflow: hidden;
}
.org-dialog .el-dialog__header {
  padding: 0;
  margin: 0;
}
.org-dialog .el-dialog__body {
  padding: 4px 24px 20px;
  max-height: 62vh;
  overflow-y: auto;
  /* 隐藏滚动条（仍可滚动） */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.org-dialog .el-dialog__body::-webkit-scrollbar {
  width: 0;
  height: 0;
}
.org-dialog .el-dialog__footer {
  padding: 14px 24px;
  border-top: 1px solid #eef0f4;
  background: #fafbfd;
}

.odg-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 22px;
  background: linear-gradient(180deg, #f7f9fd 0%, #ffffff 100%);
  border-bottom: 1px solid #eef0f4;
}
.odg-head-icon {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 21px;
}
.odg-head-text {
  flex: 1;
  min-width: 0;
}
.odg-head-text h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
}
.odg-head-text p {
  margin: 3px 0 0;
  font-size: 12px;
  color: #8a94a6;
}
.odg-close {
  position: absolute;
  right: 14px;
  top: 14px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #9aa3b2;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.16s ease;
}
.odg-close:hover {
  background: #fef0f0;
  color: #f56c6c;
}

.odg-form {
  padding-top: 4px;
}
.odg-sec {
  padding: 14px 0 4px;
}
.odg-sec + .odg-sec {
  border-top: 1px dashed #eef1f6;
  margin-top: 6px;
}
.odg-sec-head {
  margin-bottom: 10px;
  font-size: 12.5px;
  font-weight: 600;
  color: #7a8699;
  letter-spacing: 0.4px;
}

/* ---------- 卡片式类型选择 ---------- */
.odg-types {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.odg-type {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 13px 12px 12px;
  border: 1.5px solid #e7ecf4;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}
.odg-type:hover {
  border-color: color-mix(in srgb, var(--tc) 45%, #e7ecf4);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(16, 24, 40, 0.07);
}
.odg-type.is-active {
  border-color: var(--tc);
  background: color-mix(in srgb, var(--tc) 6%, #fff);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tc) 15%, transparent);
}
.odg-type.is-locked {
  cursor: not-allowed;
}
.odg-type.is-locked:not(.is-active) {
  opacity: 0.55;
}
.odg-type-icon {
  width: 30px;
  height: 30px;
  margin-bottom: 6px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--tc);
  background: color-mix(in srgb, var(--tc) 12%, transparent);
}
.odg-type b {
  font-size: 13.5px;
  font-weight: 600;
  color: #1f2d3d;
}
.odg-type em {
  font-size: 11px;
  font-style: normal;
  color: #9aa3b2;
}
.odg-type-check {
  position: absolute;
  right: 9px;
  top: 9px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #fff;
  background: var(--tc);
  opacity: 0;
  transform: scale(0.6);
  transition: all 0.18s ease;
}
.odg-type.is-active .odg-type-check {
  opacity: 1;
  transform: scale(1);
}

.odg-form .el-form-item {
  margin-bottom: 16px;
}
.odg-form .el-form-item__label {
  padding-bottom: 4px;
  font-size: 12.5px;
  color: #5b6478;
}
.odg-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* ══════════ 暗色主题 ══════════ */
/* 详情模态框 */
html.dark .el-dialog.org-detail-modal { background: #141415; }
html.dark .org-detail-modal .el-dialog__footer {
  background: #1e1e20;
  border-top-color: rgba(255, 255, 255, 0.08);
}
html.dark .odm-head {
  background:
    radial-gradient(120% 150% at 0% 0%, color-mix(in srgb, var(--od-accent) 24%, transparent) 0%, transparent 58%),
    linear-gradient(180deg, #1e1e20 0%, #191919 100%);
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
html.dark .odm-head-text h3 { color: #e8e8ea; }
html.dark .odm-head-icon { background: #26262a; }
html.dark .odm-close { background: rgba(255, 255, 255, 0.08); color: #a0a0a8; }
html.dark .odm-close:hover { background: rgba(245, 108, 108, 0.16); color: #f56c6c; }
html.dark .odm-tag {
  color: #a0a0a8;
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}
html.dark .odm-crumb { border-top-color: rgba(255, 255, 255, 0.1); }
html.dark .odm-card {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}
html.dark .odm-card-head { color: #d8d8dc; }
html.dark .odm-tile {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}
html.dark .odm-tile-label { color: #8a8a94; }
html.dark .odm-row { border-bottom-color: rgba(255, 255, 255, 0.06); }
html.dark .odm-row-k { color: #8a8a94; }
html.dark .odm-row-v { color: #d8d8dc; }
html.dark .odm-row-block .odm-row-v { color: #a0a0a8; }
html.dark .odm-step::before { background: rgba(255, 255, 255, 0.1); }
html.dark .odm-step-dot { background: #1e1e20; border-color: #3a3a42; }
html.dark .odm-step-name { color: #a0a0a8; }
html.dark .odm-footer-hint { color: #7a7a84; }

html.dark .org-dialog .el-dialog__footer {
  background: #1a1a1c;
  border-top-color: rgba(255, 255, 255, 0.08);
}
html.dark .odg-head {
  background: linear-gradient(180deg, #1e1e20 0%, #191919 100%);
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
html.dark .odg-head-text h3 { color: #e8e8ea; }
html.dark .odg-sec + .odg-sec { border-top-color: rgba(255, 255, 255, 0.08); }
html.dark .odg-type {
  background: #26262a;
  border-color: rgba(255, 255, 255, 0.1);
}
html.dark .odg-type.is-active { background: color-mix(in srgb, var(--tc) 14%, #26262a); }
html.dark .odg-type b { color: #e8e8ea; }
</style>