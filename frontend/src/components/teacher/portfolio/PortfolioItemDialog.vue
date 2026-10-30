<template>
  <ResponsivePopup
    :model-value="modelValue"
    :title="isEdit ? '编辑成长档案' : '新增成长档案'"
    :width="isMobile ? '90%' : '400px'"
    align-center
    :close-on-click-modal="false"
    class="tui-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="tui-section-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>
        {{ isEdit ? '正在编辑这条育人档案，保存后会同步更新成长报告。' : '记录一次育人经历：选好类型、写清做法与反思，即可计入成长报告。' }}
      </span>
    </div>
    <div class="pf-ctx">
      <span class="pf-ctx-item">类型：{{ typeLabel(form.item_type) }}</span>
      <span class="pf-ctx-item">可见性：{{ form.visibility === 'public' ? '公开展示' : '仅自己可见' }}</span>
      <span class="pf-ctx-item">时间：{{ form.occurred_on || '未选择' }}</span>
    </div>
    <div class="pf-form">
      <!-- 条目类型：下拉选择 -->
      <div class="pf-field">
        <label class="pf-label">类型</label>
        <el-select v-model="form.item_type" placeholder="请选择档案类型" style="width: 100%">
          <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value">
            <span class="pf-opt">
              <el-icon :size="14"><component :is="t.icon" /></el-icon>
              {{ t.label }}
            </span>
          </el-option>
        </el-select>
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
          <el-select v-model="form.visibility" placeholder="请选择可见性" style="width: 100%">
            <el-option label="仅自己可见" value="private" />
            <el-option label="公开展示" value="public" />
          </el-select>
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

      <!-- 反思：AI 辅助填写 -->
      <AiDraftField
        v-model="form.reflection"
        label="反思"
        :rows="4"
        :maxlength="1000"
        placeholder="记录你的做法与反思，让经验可复用……"
        :draft="aiDraft"
        :points="aiPoints"
      />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!form.title.trim()" @click="submit">
        保存
      </el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
// v6.1 弹窗减负：移动端弹窗改用全屏子页承接（桌面端仍为 el-dialog）
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import {
  Delete, InfoFilled, Medal, Plus, Reading, Suitcase, TrendCharts,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import {
  createPortfolioItem,
  updatePortfolioItem,
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

const typeLabel = (t: PortfolioItemType) =>
  typeOptions.find((o) => o.value === t)?.label || '档案'

/** 今日日期（YYYY-MM-DD）：无发生时间时的 AI 草稿兜底 */
const today = new Date().toISOString().slice(0, 10)

/** AI 建议要点：随档案类型变化 */
const aiPoints = computed(() => {
  const map: Record<PortfolioItemType, string[]> = {
    case: ['问题背景', '处理做法', '取得效果', '经验反思'],
    honor: ['荣誉名称', '取得过程', '个人感悟', '推广价值'],
    training: ['培训主题', '核心收获', '已迁移做法', '后续计划'],
    research: ['研究问题', '方法过程', '研究结论', '应用价值'],
  }
  return map[form.item_type]
})

/** AI 草稿：结合所选类型 + 日期，写成教师第一人称反思口吻 */
const aiDraft = computed(() => {
  const d = form.occurred_on || today
  const t = typeLabel(form.item_type)
  if (form.item_type === 'case') {
    return `${d}，我围绕班级中的典型问题开展了一次${t}：先摸清学生情况与问题成因，再联合家长、任课教师共同制定帮扶措施并跟进落实，学生状态较前期有所好转。有效的关键在于及时介入、多方协同，后续将继续跟踪记录。`
  }
  if (form.item_type === 'honor') {
    return `${d}，本人获得${t}。这份荣誉来自日常教学与班级管理的持续投入，也离不开团队支持。我会把其中的做法梳理成可复用的经验，继续用于育人实践，带动更多学生成长。`
  }
  if (form.item_type === 'training') {
    return `${d}，我参加了${t}，系统学习了相关理念与实操方法，印象最深的是与日常工作紧密结合的案例讲解。我已尝试把其中两点做法迁移到班级管理中，效果有待持续观察与调整。`
  }
  return `${d}，我完成了${t}：围绕工作中的实际问题梳理现状、分析成因，并提出可落地的改进方案。成果将在后续实践中检验，再根据反馈持续优化，形成可推广的经验。`
})

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
  gap: 12px;
}

.pf-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 6px;
}
.pf-label small {
  font-size: 11px;
  font-weight: 400;
  color: var(--tui-text-quiet);
}

/* 下拉选项内的图标 + 文字 */
.pf-opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 弹窗上下文信息条 */
.pf-ctx {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
.pf-ctx-item { white-space: nowrap; }

.pf-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.pf-evidence {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.pf-ev-name { flex: 0 0 34%; }
.pf-ev-url { flex: 1; }

@media (max-width: 767px) {
  .pf-grid2 { grid-template-columns: 1fr; }
  .pf-evidence { flex-wrap: wrap; }
  .pf-ev-name { flex: 1 1 100%; }
  .pf-ev-url { flex: 1 1 70%; }
}
</style>