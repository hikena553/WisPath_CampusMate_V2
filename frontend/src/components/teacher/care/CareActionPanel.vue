<template>
  <!-- 关怀行动面板：本页第一屏的「特色」所在。
       把散落在各页的关怀能力收敛成「一选学生 + 四个可点动作」：
       动作不直接落库，而是把选中的学生交给页面去打开对应弹窗（预填），
       这样留痕口径（侧写 / 家访 / 激励 / 家校沟通）与被复用的既有弹窗完全一致。 -->
  <section class="tui-section cc-act">
    <div class="tui-section-head">
      <h3><el-icon><MagicStick /></el-icon>关怀行动</h3>
      <div class="tui-section-extra">
        <span v-if="student" class="cc-act-who">{{ student.name }}</span>
        <el-button v-if="student" text size="small" @click="clear">更换学生</el-button>
      </div>
    </div>

    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>先选择一名学生，再点下面的关怀动作：每个动作都会打开对应弹窗并预填该学生，做完即留痕。</span>
    </div>

    <!-- 学生选择 / 搜索：服务端检索（getStudents(keyword)），支持按姓名 / 学号 -->
    <el-select
      class="cc-act-picker"
      :model-value="studentId ?? undefined"
      filterable
      remote
      reserve-keyword
      clearable
      :remote-method="onSearch"
      :loading="searching"
      placeholder="按姓名 / 学号搜索学生"
      @change="onChange"
      @clear="emit('change', null)"
    >
      <el-option v-for="s in selectOptions" :key="s.id" :label="labelOf(s)" :value="s.id" />
    </el-select>

    <!-- 四张关怀动作卡：未选学生时统一提示「先选择学生」 -->
    <div class="cc-act-grid">
      <button
        v-for="a in ACTIONS"
        :key="a.key"
        class="cc-act-card"
        :class="[`tone-${a.tone}`, { 'is-locked': !student }]"
        type="button"
        @click="emit('action', a.key)"
      >
        <span class="cc-act-ic"><el-icon :size="15"><component :is="a.icon" /></el-icon></span>
        <span class="cc-act-name">{{ a.name }}</span>
        <span class="cc-act-desc">{{ student ? a.desc : '先选择学生' }}</span>
      </button>
    </div>

    <!-- 选中学生后的上下文：该生最近 3 条关怀 / 家校记录 -->
    <div class="cc-act-recent">
      <div class="cc-act-recent-head">
        <span>最近关怀 / 家校记录</span>
        <span class="cc-act-recent-sub">{{ student ? '最近 3 条' : '待选择学生' }}</span>
      </div>
      <div v-if="!student" class="cc-act-recent-empty">选择学生后，这里会显示他最近的关怀与家校沟通记录。</div>
      <div v-else-if="!recent.length" class="cc-act-recent-empty">该生暂无关怀或家校记录，从上面的动作开始第一条吧。</div>
      <ul v-else class="cc-act-recent-list">
        <li v-for="r in recent" :key="r.id">
          <span class="cc-act-recent-tag">{{ r.label }}</span>
          <span class="cc-act-recent-text">{{ r.text }}</span>
          <span class="cc-act-recent-date">{{ r.date }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script lang="ts">
/** 关怀动作标识（由页面决定打开哪个弹窗） */
export type CareActionKey = 'record' | 'visit' | 'praise' | 'contact'

/** 上下文记录（该生最近几条关怀 / 家校记录） */
export interface CareContextItem {
  id: string
  label: string
  text: string
  date: string
}
</script>

<script setup lang="ts">
import { computed, ref, watch, type Component } from 'vue'
import { ChatDotRound, HomeFilled, InfoFilled, MagicStick, Notebook, Star } from '@element-plus/icons-vue'
import { getStudents, type StudentSummary } from '@/api/teacher'

const props = defineProps<{
  /** 当前聚焦学生 id（未选为 null） */
  studentId: number | null
  /** 当前聚焦学生（用于回显姓名与提示） */
  student: StudentSummary | null
  /** 页面已加载的学生名单，作为选择器的默认候选 */
  options: StudentSummary[]
  /** 该生最近 3 条关怀 / 家校记录 */
  recent: CareContextItem[]
}>()

const emit = defineEmits<{
  change: [student: StudentSummary | null]
  action: [key: CareActionKey]
}>()

const ACTIONS: { key: CareActionKey; name: string; desc: string; tone: 'brand' | 'warn' | 'success' | 'muted'; icon: Component }[] = [
  { key: 'record', name: '谈心 / 侧写记录', desc: '谈心谈话、侧写、评语', tone: 'brand', icon: Notebook },
  { key: 'visit', name: '家访登记', desc: '登记家访，可同步家校台账', tone: 'warn', icon: HomeFilled },
  { key: 'praise', name: '正向激励', desc: '表扬 / 徽章，让学生看见', tone: 'success', icon: Star },
  { key: 'contact', name: '家校联动', desc: '约家长沟通 / 短信留痕', tone: 'muted', icon: ChatDotRound },
]

const searching = ref(false)
/** 关键词检索结果；未检索时为空，选择器回落到页面传入的名单 */
const searched = ref<StudentSummary[]>([])

/** 候选 = 检索结果（优先）+ 页面名单，且始终保留当前学生用于回显 */
const selectOptions = computed<StudentSummary[]>(() => {
  const base = searched.value.length ? searched.value : props.options
  const list = [...base]
  if (props.student && !list.some((s) => s.id === props.student?.id)) list.unshift(props.student)
  if (searched.value.length) {
    for (const s of props.options) {
      if (!list.some((o) => o.id === s.id)) list.push(s)
    }
  }
  return list
})

function labelOf(s: StudentSummary) {
  return s.username ? `${s.name} · ${s.username}` : s.name
}

let timer: ReturnType<typeof setTimeout> | undefined
function onSearch(keyword: string) {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => { void doSearch(keyword) }, 300)
}

async function doSearch(keyword: string) {
  searching.value = true
  try {
    searched.value = await getStudents(keyword || undefined)
  } catch {
    searched.value = []
  } finally {
    searching.value = false
  }
}

function onChange(val: number | undefined) {
  if (val == null) {
    emit('change', null)
    return
  }
  emit('change', selectOptions.value.find((s) => s.id === val) || null)
}

function clear() {
  searched.value = []
  emit('change', null)
}

// 页面通过深链聚焦某个学生时，保证选择器能回显该生
watch(
  () => props.student,
  (s) => {
    if (!s) {
      searched.value = []
      return
    }
    if (!selectOptions.value.some((o) => o.id === s.id)) searched.value = [s, ...searched.value]
  }
)
</script>

<style scoped>
.cc-act { position: relative; overflow: hidden; }
.cc-act::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
  background: var(--tui-success);
}

.cc-act-who { font-size: 12px; font-weight: 600; color: var(--tui-success); }

.cc-act-picker { width: 100%; margin-bottom: 10px; }

/* 动作卡：2×2 网格，语义色左缘 + 图标底色 */
.cc-act-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.cc-act-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 10px 11px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s var(--tui-ease), background 0.15s var(--tui-ease);
}
.cc-act-card:hover { border-color: var(--tui-border-strong); background: var(--tui-surface-muted); }
.cc-act-card:active { transform: scale(0.985); }
.cc-act-ic {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px; height: 24px;
  border-radius: 7px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
}
.cc-act-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.cc-act-desc { font-size: 11.5px; line-height: 1.45; color: var(--tui-text-quiet); }

.cc-act-card.tone-brand .cc-act-ic { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-act-card.tone-warn .cc-act-ic { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-act-card.tone-success .cc-act-ic { background: var(--tui-success-soft); color: var(--tui-success); }

/* 未选学生：动作卡弱化并提示「先选择学生」 */
.cc-act-card.is-locked { background: var(--tui-surface-muted); opacity: 0.78; }
.cc-act-card.is-locked .cc-act-desc { color: var(--tui-warn); font-weight: 600; }

/* 最近记录 */
.cc-act-recent { margin-top: 11px; border-top: 1px solid var(--tui-hairline); padding-top: 9px; }
.cc-act-recent-head {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; font-weight: 600; color: var(--tui-text-secondary);
  margin-bottom: 6px;
}
.cc-act-recent-sub { font-size: 11px; font-weight: 400; color: var(--tui-text-quiet); }
.cc-act-recent-empty {
  font-size: 11.5px; line-height: 1.6; color: var(--tui-text-quiet);
  background: var(--tui-surface-muted); border-radius: 8px; padding: 8px 10px;
}
.cc-act-recent-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 5px; }
.cc-act-recent-list li {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; color: var(--tui-text-tertiary);
  background: var(--tui-surface-muted); border-radius: 8px; padding: 6px 9px;
}
.cc-act-recent-tag {
  flex-shrink: 0; font-size: 10.5px; font-weight: 600;
  background: var(--tui-surface); border: 1px solid var(--tui-border);
  color: var(--tui-text-tertiary); border-radius: 999px; padding: 1px 6px;
}
.cc-act-recent-text {
  flex: 1; min-width: 0; color: var(--tui-text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cc-act-recent-date { flex-shrink: 0; color: var(--tui-text-quiet); }

@media (max-width: 767px) {
  .cc-act-grid { grid-template-columns: 1fr; }
}
</style>