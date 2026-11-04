<template>
  <div class="ai-field">
    <div v-if="label || required" class="ai-field-head">
      <span class="ai-field-label">
        {{ label }}<span v-if="required" class="ai-field-req">*</span>
      </span>
      <span v-if="showGenerate && used && !aiLoading" class="ai-field-src" :class="source">
        {{ source === 'ai' ? 'AI 已生成' : '本地兜底' }}
      </span>
    </div>

    <!-- AI 帮我写：与成长档案 / 问卷发起保持同一套「描述 → 起草 → 核对」的中性卡片 -->
    <div v-if="showGenerate" class="ai-write" :class="{ open: aiOpen }">
      <button type="button" class="ai-write-toggle" @click="toggleAi">
        <AiMascotMark :size="15" />
        <span class="ai-write-title">AI 帮我写</span>
        <span class="ai-write-sub">{{ aiSub }}</span>
        <el-icon class="ai-write-arrow" :class="{ open: aiOpen }"><ArrowDown /></el-icon>
      </button>

      <div v-if="aiOpen" class="ai-write-body">
        <el-input
          v-model="brief"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          resize="none"
          placeholder="说说要写什么：对象、时间、做法、结果……"
        />
        <div class="ai-write-foot">
          <span class="ai-write-hint">AI 只负责起草，填入后请核对事实再提交</span>
          <el-button class="ai-write-run" size="small" round :loading="aiLoading" :disabled="aiLoading" @click="generateDraft">
            {{ used ? '重新生成' : '生成' }}
          </el-button>
        </div>
      </div>
    </div>

    <el-input
      :model-value="modelValue"
      type="textarea"
      :rows="rows"
      :maxlength="maxlength"
      show-word-limit
      :placeholder="placeholder"
      @update:model-value="onInput"
    />

    <!-- AI 提醒式填写：实时提示「还缺哪些要点」 -->
    <div v-if="points.length" class="ai-remind">
      <div class="ai-remind-head">
        <AiMascotMark :size="14" />
        <span class="ai-remind-title">AI 提醒</span>
        <span class="ai-remind-count">{{ covered.length }}/{{ points.length }}</span>
      </div>
      <p class="ai-remind-text">{{ remindText }}</p>
      <div class="ai-remind-points">
        <button
          v-for="p in points"
          :key="p"
          type="button"
          class="ai-remind-point"
          :class="{ on: isCovered(p) }"
          @click="insertPoint(p)"
        >
          <el-icon><Check v-if="isCovered(p)" /><Plus v-else /></el-icon>
          <span>{{ p }}</span>
        </button>
      </div>
    </div>

    <div v-if="used" class="ai-field-note">
      <AiMascotMark :size="13" />
      <span>
        {{ source === 'ai'
          ? 'AI 已根据你的描述起草，请核对后按实际情况修改'
          : '模型暂不可用，已按要点整理初稿，请补充细节后修改' }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AiMascotMark from '@/components/teacher/ui/AiMascotMark.vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, Check, Plus } from '@element-plus/icons-vue'
import { aiDraftText } from '@/api/teacherAi'

const props = withDefaults(
  defineProps<{
    modelValue: string
    label: string
    /** 本地参考草稿：作为 AI 的上下文，也是模型不可用时的兜底 */
    draft?: string
    /** AI 提醒要点：既作为「还缺什么」的检查项，也可点击直接插入 */
    points?: string[]
    placeholder?: string
    rows?: number
    maxlength?: number
    required?: boolean
    /** 是否显示字段内的「AI 帮我写」入口（由外部统一触发起草时可关闭） */
    showGenerate?: boolean
  }>(),
  {
    draft: '',
    points: () => [],
    placeholder: '',
    rows: 4,
    maxlength: 500,
    required: false,
    showGenerate: true,
  }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

/** 本次弹窗内是否已用过 AI 草稿（弹窗 destroy-on-close 后自动重置） */
const used = ref(false)
/** 本次草稿来源：ai=模型生成；rule=本地兜底 */
const source = ref<'ai' | 'rule'>('ai')
const aiOpen = ref(false)
const aiLoading = ref(false)
const brief = ref('')

const text = computed(() => props.modelValue || '')

const aiSub = computed(() => {
  if (aiLoading.value) return '正在根据描述起草…'
  if (aiOpen.value) return '描述要点，AI 据此起草'
  return '描述要点，自动起草'
})

function isCovered(p: string) {
  return text.value.includes(p)
}

/** 已提及的要点数，用于提醒进度 */
const covered = computed(() => props.points.filter((p) => isCovered(p)))

/** 动态提醒文案：空 → 引导；有内容 → 指出还缺哪些要点 */
const remindText = computed(() => {
  const t = text.value.trim()
  const total = props.points.length
  if (!total) return ''
  if (!t) return '还没有内容：可点下方提醒逐条补全，或点上方「AI 帮我写」生成草稿。'
  const miss = props.points.filter((p) => !isCovered(p))
  if (!covered.value.length) return `建议围绕以下 ${total} 个要点展开，记录会更完整。`
  if (!miss.length) return '要点已齐全，复核后即可提交。'
  const shown = miss.slice(0, 3).join('、')
  return `还差 ${miss.length} 项未提及：${shown}${miss.length > 3 ? ' 等' : ''}。`
})

function onInput(v: string) {
  emit('update:modelValue', v)
}

function toggleAi() {
  if (aiLoading.value) return
  aiOpen.value = !aiOpen.value
}

/** 本地兜底：描述 + 要点拼一段初稿 */
function composeFallback(briefText: string) {
  const base = briefText || props.label || '本次工作记录'
  const tail = props.points.length ? `围绕${props.points.join('、')}逐项补充完整。` : ''
  return `${base.replace(/[。；;，,]$/, '')}。${tail}`
}

async function generateDraft() {
  if (aiLoading.value) return
  // 优先用补充描述；未填写时把已输入的内容当作描述
  const briefText = brief.value.trim() || text.value.trim()
  aiLoading.value = true
  try {
    const res = await aiDraftText({
      scene: props.label || '教师工作记录',
      brief: briefText,
      points: props.points,
      reference: props.draft || '',
      max_length: props.maxlength || 500,
    })
    const out = (res.text || '').trim()
    if (!out) throw new Error('empty draft')
    emit('update:modelValue', out)
    source.value = res.source === 'rule' ? 'rule' : 'ai'
    used.value = true
    aiOpen.value = false
    if (source.value === 'ai') {
      ElMessage.success('AI 已起草，请核对后修改')
    } else {
      ElMessage.warning('模型暂不可用，已按要点整理初稿')
    }
  } catch {
    // 网络异常等：本地兜底，保证按钮永远有结果
    const fallback = props.draft || composeFallback(briefText)
    if (!fallback) {
      ElMessage.warning('请先描述这次要写的内容，或直接手动填写')
      return
    }
    emit('update:modelValue', fallback)
    source.value = 'rule'
    used.value = true
    aiOpen.value = false
    ElMessage.warning('模型暂不可用，已按要点整理初稿')
  } finally {
    aiLoading.value = false
  }
}

function insertPoint(p: string) {
  const cur = text.value.trim()
  if (!cur) {
    emit('update:modelValue', p)
    return
  }
  if (cur.includes(p)) return
  const sep = /[。；;，,]$/.test(cur) ? '' : '；'
  emit('update:modelValue', `${cur}${sep}${p}`)
}
</script>

<style scoped>
.ai-field {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.ai-field-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-field-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
/* 来源标签：与问卷发起的 AI 状态标签同一套中性样式 */
.ai-field-src {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 6px;
  background: #f2f4f7;
  color: var(--tui-text-quiet);
  font-size: 11px;
}
.ai-field-src.ai {
  color: #475467;
}

/* ===== AI 帮我写：可展开的中性卡片 ===== */
.ai-write {
  border: 1px solid #e4e8ef;
  border-radius: 12px;
  background: #fbfcfe;
  overflow: hidden;
}
.ai-write.open {
  background: #fff;
}
.ai-write-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.ai-write-title {
  flex-shrink: 0;
  font-size: 12.5px;
  font-weight: 700;
  color: #1f2430;
}
.ai-write-sub {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-write-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: #98a2b3;
  transition: transform 0.18s ease;
}
.ai-write-arrow.open {
  transform: rotate(180deg);
}
.ai-write-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 10px 10px;
}
.ai-write .ai-write-body :deep(.el-textarea__inner) {
  min-height: 58px !important;
  padding: 7px 10px;
  border-radius: 10px;
  border: 1px solid #e4e8ef;
  box-shadow: none;
  background: #fff;
  font-size: 12px;
  line-height: 1.55;
  color: #1f2430;
}
.ai-write .ai-write-body :deep(.el-textarea__inner:focus) {
  border-color: #1f2430;
  box-shadow: 0 0 0 3px rgba(31, 36, 48, 0.05);
}
.ai-write .ai-write-body :deep(.el-input__count) {
  background: transparent;
  color: #9aa1ad;
}
.ai-write-foot {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ai-write-hint {
  flex: 1;
  font-size: 11px;
  line-height: 1.5;
  color: #98a2b3;
}
/* 全局教师端有 `.main-area.teacher-scope .el-button { border-radius: 6px }`，
   这里用更高的选择器 + !important 强制胶囊形，避免被全局圆角覆盖 */
.ai-write-foot :deep(.el-button.ai-write-run) {
  flex-shrink: 0;
  height: 26px;
  padding: 0 14px;
  border-radius: 999px !important;
  border-color: #1f2430;
  background: #1f2430;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.ai-write-foot :deep(.el-button.ai-write-run:hover) {
  border-color: #333a47;
  background: #333a47;
  color: #fff;
}

/* 输入框：浅底 + 圆角 + 聚焦描边，与公告表单同一套输入语言 */
.ai-field :deep(.el-textarea__inner) {
  min-height: 116px !important;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e4e8ef;
  box-shadow: none;
  background: #fbfcfe;
  font-size: 13px;
  line-height: 1.7;
  color: #1f2430;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.ai-field :deep(.el-textarea__inner:hover) {
  border-color: #d7dce4;
  background: #fff;
}
.ai-field :deep(.el-textarea__inner:focus) {
  border-color: #1f2430;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(31, 36, 48, 0.05);
}
.ai-field :deep(.el-input__count) {
  background: transparent;
  color: #9aa1ad;
}
.ai-field-req {
  color: var(--tui-danger);
  margin-left: 2px;
}

/* ===== AI 提醒式填写面板（中性灰，不抢正文） ===== */
.ai-remind {
  padding: 8px 10px;
  border-radius: 10px;
  background: #f7f8fa;
  border: 1px solid #e4e8ef;
}
.ai-remind-head {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #1f2430;
}
.ai-remind-title {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.2px;
}
.ai-remind-count {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: #98a2b3;
}
.ai-remind-text {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: #667085;
}
.ai-remind-points {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 7px;
}
.ai-remind-point {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border: 1px dashed #d6dbe3;
  border-radius: 999px;
  background: #fff;
  color: #667085;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ai-remind-point .el-icon {
  font-size: 11px;
}
.ai-remind-point:hover {
  border-style: solid;
  border-color: #1f2430;
  color: #1f2430;
}
/* 已提及的要点：浅灰实心，一眼看出还缺什么 */
.ai-remind-point.on {
  border-style: solid;
  border-color: transparent;
  background: #eceff3;
  color: #1f2430;
  font-weight: 600;
}

.ai-field-note {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--tui-text-quiet);
}
.ai-field-note :deep(img) {
  flex-shrink: 0;
  margin-top: 1px;
}
</style>
