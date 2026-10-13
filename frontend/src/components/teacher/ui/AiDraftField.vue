<template>
  <div class="ai-field">
    <div class="ai-field-head">
      <span class="ai-field-label">
        {{ label }}<span v-if="required" class="ai-field-req">*</span>
      </span>
      <button
        type="button"
        class="ai-field-btn"
        :disabled="!draft"
        @click="generateDraft"
      >
        <el-icon><MagicStick /></el-icon>
        {{ used ? '重新生成' : 'AI 帮我写' }}
      </button>
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
        <el-icon><MagicStick /></el-icon>
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
      <el-icon><MagicStick /></el-icon>
      <span>AI 草稿由本地模板结合所选类型 / 学生 / 日期生成，请核对后按实际情况修改</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, MagicStick, Plus } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    label: string
    /** AI 一键生成的草稿文本（由调用方按业务语境提供） */
    draft?: string
    /** AI 提醒要点：既作为「还缺什么」的检查项，也可点击直接插入 */
    points?: string[]
    placeholder?: string
    rows?: number
    maxlength?: number
    required?: boolean
  }>(),
  {
    draft: '',
    points: () => [],
    placeholder: '',
    rows: 4,
    maxlength: 500,
    required: false,
  }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

/** 本次弹窗内是否已用过 AI 草稿（弹窗 destroy-on-close 后自动重置） */
const used = ref(false)

const text = computed(() => props.modelValue || '')

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
  if (!t) return '还没有内容：可点下方提醒逐条补全，或点右上「AI 帮我写」生成草稿。'
  const miss = props.points.filter((p) => !isCovered(p))
  if (!covered.value.length) return `建议围绕以下 ${total} 个要点展开，记录会更完整。`
  if (!miss.length) return '要点已齐全，复核后即可提交。'
  const shown = miss.slice(0, 3).join('、')
  return `还差 ${miss.length} 项未提及：${shown}${miss.length > 3 ? ' 等' : ''}。`
})

function onInput(v: string) {
  emit('update:modelValue', v)
}

function generateDraft() {
  if (!props.draft) return
  emit('update:modelValue', props.draft)
  used.value = true
  ElMessage.success('已生成 AI 草稿，可直接修改')
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
  gap: 7px;
}

.ai-field-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-field-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.ai-field-req {
  color: var(--tui-danger);
  margin-left: 2px;
}

/* AI 辅助填写入口：小而克制的胶囊按钮 */
.ai-field-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-size: 11.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s ease;
}
.ai-field-btn:hover:not(:disabled) {
  background: #e0ebff;
}
.ai-field-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ai-field-btn .el-icon {
  font-size: 13px;
}

/* ===== AI 提醒式填写面板 ===== */
.ai-remind {
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--tui-brand-soft);
  border: 1px solid rgba(37, 99, 235, 0.14);
}
.ai-remind-head {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--tui-brand-strong);
}
.ai-remind-head .el-icon {
  font-size: 13px;
}
.ai-remind-title {
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.2px;
}
.ai-remind-count {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--tui-brand-strong);
  opacity: 0.75;
}
.ai-remind-text {
  margin: 4px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--tui-brand-strong);
  opacity: 0.9;
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
  border: 1px dashed rgba(37, 99, 235, 0.35);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--tui-text-tertiary);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ai-remind-point .el-icon {
  font-size: 11px;
}
.ai-remind-point:hover {
  border-style: solid;
  border-color: var(--tui-brand);
  color: var(--tui-brand-strong);
  background: #fff;
}
/* 已提及的要点：实心勾选态，一眼看出还缺什么 */
.ai-remind-point.on {
  border-style: solid;
  border-color: transparent;
  background: var(--tui-success-soft);
  color: var(--tui-success);
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
.ai-field-note .el-icon {
  flex-shrink: 0;
  margin-top: 1px;
  font-size: 12px;
}
</style>