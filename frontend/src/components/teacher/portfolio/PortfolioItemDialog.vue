<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑成长档案' : '新增成长档案'"
    :width="isMobile ? '94%' : '600px'"
    align-center
    destroy-on-close
    class="pf-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="pf-form">
      <!-- 四段式之一：条目类型 -->
      <div class="pf-field">
        <label class="pf-label">类型</label>
        <div class="pf-type-row">
          <button
            v-for="t in typeOptions"
            :key="t.value"
            class="pf-type"
            :class="{ active: form.item_type === t.value }"
            :style="form.item_type === t.value ? { borderColor: color(t.value), color: color(t.value), background: tint(t.value) } : {}"
            @click="form.item_type = t.value"
          >
            <el-icon :size="15"><component :is="t.icon" /></el-icon>
            {{ t.label }}
          </button>
        </div>
      </div>

      <div class="pf-field">
        <label class="pf-label">标题</label>
        <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="例如：学业困难学生帮扶案例" />
      </div>

      <div class="pf-grid2">
        <div class="pf-field">
          <label class="pf-label">发生时间</label>
          <el-date-picker
            v-model="form.occurred_on"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </div>
        <div class="pf-field">
          <label class="pf-label">可见性</label>
          <el-radio-group v-model="form.visibility">
            <el-radio-button value="private">仅自己</el-radio-button>
            <el-radio-button value="public">公开展示</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 证据 -->
      <div class="pf-field">
        <label class="pf-label">
          证据材料
          <small>附件名 + 链接，可多条</small>
        </label>
        <div v-for="(e, i) in form.evidence" :key="i" class="pf-evidence">
          <el-input v-model="e.name" placeholder="名称（如：帮扶记录.pdf）" class="pf-ev-name" />
          <el-input v-model="e.url" placeholder="链接 / 附件地址" class="pf-ev-url" />
          <el-button text circle type="danger" @click="removeEvidence(i)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button size="small" round :icon="Plus" @click="addEvidence">添加证据</el-button>
      </div>

      <!-- 反思 -->
      <div class="pf-field">
        <label class="pf-label">
          反思
          <small>这次做了什么、为什么有效、下次怎么改</small>
        </label>
        <el-input
          v-model="form.reflection"
          type="textarea"
          :rows="4"
          maxlength="1000"
          show-word-limit
          placeholder="记录你的做法与反思，让经验可复用……"
        />
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!form.title.trim()" @click="submit">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  Delete, Medal, Plus, Reading, Suitcase, TrendCharts,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createPortfolioItem,
  updatePortfolioItem,
  PORTFOLIO_TYPE_COLOR,
  type EvidenceItem,
  type PortfolioItem,
  type PortfolioItemType,
  type PortfolioVisibility,
} from '@/api/teacherPortfolio'

const props = defineProps<{
  modelValue: boolean
  /** 传入则为编辑模式 */
  item?: PortfolioItem | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const { isMobile } = useResponsive()

const typeOptions: { value: PortfolioItemType; label: string; icon: unknown }[] = [
  { value: 'case', label: '工作案例', icon: Suitcase },
  { value: 'honor', label: '荣誉表彰', icon: Medal },
  { value: 'training', label: '培训研修', icon: Reading },
  { value: 'research', label: '研究成果', icon: TrendCharts },
]

const color = (t: PortfolioItemType) => PORTFOLIO_TYPE_COLOR[t]
const tint = (t: PortfolioItemType) => `${PORTFOLIO_TYPE_COLOR[t]}14`

const form = reactive<{
  item_type: PortfolioItemType
  title: string
  occurred_on: string | null
  visibility: PortfolioVisibility
  evidence: EvidenceItem[]
  reflection: string
}>({
  item_type: 'case',
  title: '',
  occurred_on: null,
  visibility: 'private',
  evidence: [],
  reflection: '',
})

const saving = ref(false)
const isEdit = computed(() => !!props.item)

function reset() {
  if (props.item) {
    form.item_type = props.item.item_type
    form.title = props.item.title
    form.occurred_on = props.item.occurred_on
    form.visibility = props.item.visibility
    form.evidence = props.item.evidence.map((e) => ({ name: e.name || '', url: e.url }))
    form.reflection = props.item.reflection || ''
  } else {
    form.item_type = 'case'
    form.title = ''
    form.occurred_on = null
    form.visibility = 'private'
    form.evidence = []
    form.reflection = ''
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) reset()
  }
)

function addEvidence() {
  form.evidence.push({ name: '', url: '' })
}
function removeEvidence(i: number) {
  form.evidence.splice(i, 1)
}

async function submit() {
  const title = form.title.trim()
  if (!title) return
  // 过滤掉空链接的证据行
  const evidence = form.evidence
    .filter((e) => (e.url || '').trim())
    .map((e) => ({ name: (e.name || '').trim(), url: e.url.trim() }))

  saving.value = true
  try {
    const payload = {
      item_type: form.item_type,
      title,
      occurred_on: form.occurred_on,
      visibility: form.visibility,
      evidence,
      reflection: form.reflection.trim() || null,
    }
    if (isEdit.value && props.item) {
      await updatePortfolioItem(props.item.id, payload)
    } else {
      await createPortfolioItem(payload)
    }
    ElMessage.success(isEdit.value ? '已更新' : '已添加')
    emit('update:modelValue', false)
    emit('saved')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.pf-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pf-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  margin-bottom: 8px;
}
.pf-label small {
  font-size: 11px;
  font-weight: 400;
  color: #98a2b3;
}

.pf-type-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.pf-type {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  border: 1px solid #e4e7ec;
  border-radius: 10px;
  background: #fff;
  color: #667085;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
}
.pf-type.active { font-weight: 600; }

.pf-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.pf-evidence {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.pf-ev-name { flex: 0 0 34%; }
.pf-ev-url { flex: 1; }

@media (max-width: 767px) {
  .pf-type-row { grid-template-columns: repeat(2, 1fr); }
  .pf-grid2 { grid-template-columns: 1fr; }
  .pf-evidence { flex-wrap: wrap; }
  .pf-ev-name { flex: 1 1 100%; }
  .pf-ev-url { flex: 1 1 70%; }
}
</style>