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
    <!-- 两种录入方式：手动逐项填写，或让 AI 根据口述先起草 -->
    <div class="pf-ai">
      <button type="button" class="pf-ai-toggle" @click="aiOpen = !aiOpen">
        <AiMascotMark :size="16" />
        <span class="pf-ai-title">AI 帮写</span>
        <span class="pf-ai-sub">说说大体情况，自动填好标题与反思</span>
        <el-icon class="pf-ai-arrow" :class="{ open: aiOpen }"><ArrowDown /></el-icon>
      </button>

      <div v-if="aiOpen" class="pf-ai-body">
        <el-input
          v-model="aiBrief"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          resize="none"
          placeholder="简单说说时间、对象、做法和结果即可"
        />
        <div class="pf-ai-foot">
          <span class="pf-ai-hint">先说明大体情况；AI 只负责起草，填充后请核对再保存</span>
          <el-button size="small" :loading="aiLoading" :disabled="aiLoading" @click="runAiDraft">
            生成
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="aiFilled" class="pf-ai-filled">
      <el-icon><Check /></el-icon>
      <span>
        {{ aiSource === 'rule'
          ? '模型暂不可用，已按你的描述整理初稿，请补充细节后保存。'
          : 'AI 已填入类型、标题、时间与反思，请核对后保存。' }}
      </span>
    </div>

    <!-- 当前填写摘要：单行小字，不占版面 -->
    <div class="pf-ctx">
      <span class="pf-ctx-item">类型：{{ typeLabel(form.item_type) }}</span>
      <span class="pf-ctx-item">可见性：{{ form.visibility === 'public' ? '公开展示' : '仅自己可见' }}</span>
      <span class="pf-ctx-item">时间：{{ form.occurred_on || '未选择' }}</span>
    </div>

    <div class="pf-form">
      <!-- 类型：四选一，点选即可 -->
      <div class="pf-field">
        <label class="pf-label">类型</label>
        <div class="pf-types">
          <button
            v-for="t in typeOptions"
            :key="t.value"
            type="button"
            class="pf-type"
            :class="{ active: form.item_type === t.value }"
            @click="form.item_type = t.value"
          >
            <el-icon :size="14"><component :is="t.icon" /></el-icon>
            <span>{{ t.label }}</span>
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
          <div ref="dateBoxRef" class="pf-date-box">
            <button type="button" class="pf-date-trigger" @click="toggleDatePanel">
              <el-icon class="pf-date-icon"><Calendar /></el-icon>
              <span :class="{ 'is-placeholder': !form.occurred_on }">
                {{ form.occurred_on || '选择日期' }}
              </span>
              <el-icon class="pf-date-arrow" :class="{ open: dateOpen }"><ArrowDown /></el-icon>
            </button>

            <div v-if="dateOpen" class="pf-date-panel">
              <div class="pf-dp-head">
                <button type="button" @click="changeMonth(-1)">‹</button>
                <span>{{ viewYear }}年{{ viewMonth + 1 }}月</span>
                <button type="button" @click="changeMonth(1)">›</button>
              </div>
              <div class="pf-dp-week">
                <span v-for="w in weekLabels" :key="w">{{ w }}</span>
              </div>
              <div class="pf-dp-grid">
                <button
                  v-for="cell in calendarCells"
                  :key="cell.key"
                  type="button"
                  class="pf-dp-day"
                  :class="{
                    'is-out': !cell.current,
                    'is-today': cell.today,
                    'is-selected': cell.selected,
                  }"
                  @click="pickDate(cell)"
                >
                  {{ cell.day }}
                </button>
              </div>
              <div class="pf-dp-foot">
                <button type="button" @click="clearDate">清除</button>
                <button type="button" @click="pickToday">今天</button>
              </div>
            </div>
          </div>
        </div>
        <div class="pf-field">
          <label class="pf-label">可见性</label>
          <div class="pf-seg">
            <button
              type="button"
              :class="{ active: form.visibility === 'private' }"
              @click="form.visibility = 'private'"
            >
              仅自己可见
            </button>
            <button
              type="button"
              :class="{ active: form.visibility === 'public' }"
              @click="form.visibility = 'public'"
            >
              公开展示
            </button>
          </div>
        </div>
      </div>

      <!-- 证据 -->
      <div class="pf-field">
        <label class="pf-label">
          证据材料
          <small>可直接上传文件，也可粘贴外部链接</small>
        </label>

        <!-- 上传后逐条展示：文件名可点开、可移除 -->
        <div v-for="(e, i) in form.evidence" :key="i" class="pf-evidence">
          <span class="pf-ev-ic"><el-icon :size="14"><Document /></el-icon></span>
          <div class="pf-ev-bd">
            <span class="pf-ev-name" :title="e.name || e.url">{{ e.name || fileNameOf(e.url) }}</span>
            <span class="pf-ev-url">{{ e.url }}</span>
          </div>
          <el-button text circle :icon="View" title="预览" @click="previewEvidence(e.url)" />
          <el-button text circle type="danger" :icon="Delete" title="移除" @click="removeEvidence(i)" />
        </div>

        <div class="pf-ev-actions">
          <el-button round :icon="Upload" :loading="uploading" @click="pickFiles">上传文件</el-button>
          <el-button round :icon="Link" @click="linkOpen = !linkOpen">粘贴链接</el-button>
          <input
            ref="fileInputRef"
            type="file"
            multiple
            class="pf-ev-file"
            accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar"
            @change="onFilesPicked"
          />
        </div>
        <div class="pf-ev-hint">
          支持 PDF / Word / Excel / PPT / 图片 / 压缩包，单个文件不超过 50MB
        </div>

        <!-- 外链录入：默认收起，避免抢主流程 -->
        <div v-if="linkOpen" class="pf-ev-link">
          <el-input v-model="linkForm.name" placeholder="名称（选填）" class="pf-ev-link-name" />
          <el-input v-model="linkForm.url" placeholder="https://..." class="pf-ev-link-url" />
          <el-button size="small" type="primary" @click="confirmLink">添加</el-button>
        </div>
      </div>

      <!-- 反思：AI 提醒式填写（AI 帮写入上方统一触发） -->
      <AiDraftField
        v-model="form.reflection"
        label="反思"
        :rows="4"
        :maxlength="1000"
        placeholder="记录你的做法与反思，让经验可复用……"
        :points="aiPoints"
        :show-generate="false"
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
// v6.1 弹窗减负：移动端弹窗改用全屏子页承接（桌面端仍为 el-dialog）
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import {
  ArrowDown, Calendar, Check, Delete, Document, Link, Medal, Reading, Suitcase,
  TrendCharts, Upload, View,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import AiMascotMark from '@/components/teacher/ui/AiMascotMark.vue'
import { uploadFile } from '@/api/upload'
import {
  aiDraftPortfolio,
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

/** 自绘日期面板：避免浏览器原生日历样式不统一，保持黑白灰 */
const weekLabels = ['一', '二', '三', '四', '五', '六', '日']
const dateOpen = ref(false)
const dateBoxRef = ref<HTMLElement | null>(null)
const viewYear = ref(new Date().getFullYear())
const viewMonth = ref(new Date().getMonth())

function pad2(n: number) {
  return String(n).padStart(2, '0')
}
function formatDate(d: Date) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function initCalendarView() {
  const base = form.occurred_on ? new Date(`${form.occurred_on}T00:00:00`) : new Date()
  viewYear.value = base.getFullYear()
  viewMonth.value = base.getMonth()
}

function toggleDatePanel() {
  if (!dateOpen.value) initCalendarView()
  dateOpen.value = !dateOpen.value
}

function changeMonth(step: number) {
  const next = new Date(viewYear.value, viewMonth.value + step, 1)
  viewYear.value = next.getFullYear()
  viewMonth.value = next.getMonth()
}

const calendarCells = computed(() => {
  const first = new Date(viewYear.value, viewMonth.value, 1)
  // 周一为一周起点
  const offset = (first.getDay() + 6) % 7
  const start = new Date(viewYear.value, viewMonth.value, 1 - offset)
  const today = formatDate(new Date())
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
    const value = formatDate(d)
    return {
      key: `${value}-${i}`,
      year: d.getFullYear(),
      month: d.getMonth(),
      day: d.getDate(),
      current: d.getMonth() === viewMonth.value,
      today: value === today,
      selected: form.occurred_on === value,
    }
  })
})

function pickDate(cell: { year: number; month: number; day: number }) {
  form.occurred_on = formatDate(new Date(cell.year, cell.month, cell.day))
  dateOpen.value = false
}
function pickToday() {
  form.occurred_on = formatDate(new Date())
  dateOpen.value = false
}
function clearDate() {
  form.occurred_on = null
  dateOpen.value = false
}

function onDocumentClick(e: MouseEvent) {
  if (dateOpen.value && dateBoxRef.value && !dateBoxRef.value.contains(e.target as Node)) {
    dateOpen.value = false
  }
}
onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))

/** AI 帮写：口述内容 → 自动填充表单 → 老师核对后保存 */
const aiOpen = ref(false)
const aiBrief = ref('')
const aiLoading = ref(false)
const aiFilled = ref(false)
const aiSource = ref<'ai' | 'rule'>('ai')

function resetAi() {
  aiOpen.value = false
  aiBrief.value = ''
  aiFilled.value = false
  aiSource.value = 'ai'
}

function reset() {
  resetAi()
  dateOpen.value = false
  linkOpen.value = false
  linkForm.name = ''
  linkForm.url = ''
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

async function runAiDraft() {
  const brief = aiBrief.value.trim()
  if (!brief) {
    aiOpen.value = true
    ElMessage.warning('请先说明这次经历的大体情况，AI 才能帮你生成')
    return
  }
  if (aiLoading.value) return
  aiLoading.value = true
  try {
    const draft = await aiDraftPortfolio(brief)
    form.item_type = draft.item_type
    form.title = draft.title
    form.reflection = draft.reflection
    if (draft.occurred_on) form.occurred_on = draft.occurred_on
    aiSource.value = draft.source
    aiFilled.value = true
    aiOpen.value = false
    ElMessage.success(draft.source === 'ai' ? 'AI 已填充，请核对后保存' : '已按描述整理初稿，请补充细节')
  } catch {
    ElMessage.error('AI 生成失败，请手动填写')
  } finally {
    aiLoading.value = false
  }
}

function removeEvidence(i: number) {
  form.evidence.splice(i, 1)
}

/** 外链录入面板 */
const linkOpen = ref(false)
const linkForm = reactive({ name: '', url: '' })

function confirmLink() {
  const url = linkForm.url.trim()
  if (!url) {
    ElMessage.warning('请填写链接地址')
    return
  }
  if (!/^https?:\/\//i.test(url)) {
    ElMessage.warning('链接需以 http:// 或 https:// 开头')
    return
  }
  form.evidence.push({ name: linkForm.name.trim(), url })
  linkForm.name = ''
  linkForm.url = ''
  linkOpen.value = false
}

/* ── 证据材料：文件上传 ──
   后端 /api/upload 已支持 pdf/doc/xls/ppt/图片/压缩包，单文件 50MB，
   返回 { url: '/api/files/root/xxx', filename }，直接存进 evidence.url 即可。 */
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
/** 单文件上限，与后端 MAX_FILE_SIZE 保持一致 */
const MAX_SIZE = 50 * 1024 * 1024

function fileNameOf(url: string) {
  if (!url) return ''
  // /api/files/root/xxx_ab12cd.pdf → 优先还原可读名
  return decodeURIComponent(url.split('/').pop() || url)
}

function pickFiles() {
  if (uploading.value) return
  fileInputRef.value?.click()
}

async function onFilesPicked(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = '' // 允许重复选同一个文件
  if (!files.length) return

  const oversize = files.filter((f) => f.size > MAX_SIZE)
  if (oversize.length) {
    ElMessage.warning(`${oversize[0].name} 超过 50MB，已跳过`)
  }
  const todo = files.filter((f) => f.size <= MAX_SIZE)
  if (!todo.length) return

  uploading.value = true
  let ok = 0
  for (const f of todo) {
    try {
      const res = await uploadFile(f)
      form.evidence.push({ name: f.name, url: res.url })
      ok += 1
    } catch (err) {
      ElMessage.error(`${f.name} 上传失败：${(err as Error).message || '请稍后重试'}`)
    }
  }
  uploading.value = false
  if (ok) ElMessage.success(`已上传 ${ok} 个文件`)
}

/** 预览：上传件直链打开；外部链接同样新窗口打开 */
function previewEvidence(url: string) {
  if (!url) return
  window.open(url, '_blank', 'noopener')
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
      occurred_on: form.occurred_on || null,
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

/* 类型：四选一，直接可见可点 */
.pf-types {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}
.pf-type {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 10px 2px;
  border: 1px solid #e4e8ef;
  border-radius: 10px;
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.3;
  color: #667085;
  cursor: pointer;
}
.pf-type.active {
  border-color: #1f2430;
  background: #f2f4f7;
  color: #1f2430;
  font-weight: 600;
}

/* 发生时间：紧凑日期框 + 自绘黑白日历面板 */
.pf-date-box {
  position: relative;
}
.pf-date-trigger {
  display: flex;
  align-items: center;
  width: 100%;
  height: 30px;
  padding: 0 8px;
  border: 1px solid #e4e8ef;
  border-radius: 9px;
  background: #fff;
  font-family: inherit;
  font-size: 11.5px;
  color: #1f2430;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.pf-date-trigger:hover {
  border-color: #d6dbe3;
}
.pf-date-trigger:focus-visible,
.pf-date-box:focus-within .pf-date-trigger {
  border-color: #1f2430;
  box-shadow: 0 0 0 3px rgba(31, 36, 48, 0.05);
}
.pf-date-trigger .is-placeholder {
  color: #98a2b3;
}
.pf-date-icon {
  flex-shrink: 0;
  margin-right: 6px;
  font-size: 13px;
  color: #98a2b3;
}
.pf-date-arrow {
  flex-shrink: 0;
  margin-left: auto;
  font-size: 12px;
  color: #98a2b3;
  transition: transform 0.18s ease;
}
.pf-date-arrow.open {
  transform: rotate(180deg);
}

/* 日历面板 */
.pf-date-panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  width: 252px;
  padding: 10px;
  border: 1px solid #e4e8ef;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(17, 24, 39, 0.12);
}
.pf-dp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.pf-dp-head span {
  font-size: 12.5px;
  font-weight: 700;
  color: #1f2430;
}
.pf-dp-head button {
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: #f6f7f9;
  font-family: inherit;
  font-size: 14px;
  line-height: 1;
  color: #475467;
  cursor: pointer;
}
.pf-dp-head button:hover {
  background: #eceff3;
}
.pf-dp-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}
.pf-dp-week span {
  font-size: 10.5px;
  line-height: 22px;
  color: #98a2b3;
  text-align: center;
}
.pf-dp-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.pf-dp-day {
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  font-family: inherit;
  font-size: 11.5px;
  color: #1f2430;
  cursor: pointer;
}
.pf-dp-day:hover {
  background: #f2f4f7;
}
.pf-dp-day.is-out {
  color: #c4c9d2;
}
.pf-dp-day.is-today {
  box-shadow: inset 0 0 0 1px #d6dbe3;
}
.pf-dp-day.is-selected {
  background: #f0f2f5;
  box-shadow: inset 0 0 0 1px #1f2430;
  font-weight: 700;
  color: #111;
}
.pf-dp-foot {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f2f5;
}
.pf-dp-foot button {
  height: 24px;
  padding: 0 10px;
  border: 1px solid #e4e8ef;
  border-radius: 999px;
  background: #fff;
  font-family: inherit;
  font-size: 11px;
  color: #475467;
  cursor: pointer;
}
.pf-dp-foot button:hover {
  background: #f6f7f9;
}

/* 可见性：二选一分段控件 */
.pf-seg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 3px;
  border: 1px solid #e4e8ef;
  border-radius: 10px;
  background: #f7f8fa;
}
.pf-seg button {
  height: 30px;
  padding: 0 4px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  font-family: inherit;
  font-size: 12px;
  color: #667085;
  white-space: nowrap;
  cursor: pointer;
}
.pf-seg button.active {
  background: #1f2430;
  color: #fff;
  font-weight: 600;
}

/* AI 帮写入口：中性浅灰卡片，可展开 */
.pf-ai {
  margin-bottom: 12px;
  border: 1px solid #e4e8ef;
  border-radius: 12px;
  background: #fbfcfe;
  overflow: hidden;
}
.pf-ai-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 9px 11px;
  border: 0;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.pf-ai-title {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1f2430;
}
.pf-ai-sub {
  font-size: 11.5px;
  color: #667085;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-ai-arrow {
  margin-left: auto;
  font-size: 13px;
  color: #98a2b3;
  transition: transform 0.18s ease;
}
.pf-ai-arrow.open {
  transform: rotate(180deg);
}
.pf-ai-body {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 0 11px 11px;
}
.pf-ai :deep(.el-textarea__inner) {
  padding: 7px 10px;
  border-radius: 10px;
  border: 1px solid #e4e8ef;
  box-shadow: none;
  background: #fff;
  font-size: 12px;
  line-height: 1.55;
  color: #1f2430;
}
.pf-ai :deep(.el-textarea__inner:focus) {
  border-color: #1f2430;
  box-shadow: 0 0 0 3px rgba(31, 36, 48, 0.05);
}
.pf-ai :deep(.el-input__count) {
  background: transparent;
  color: #9aa1ad;
}
.pf-ai-foot {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pf-ai-hint {
  flex: 1;
  font-size: 11px;
  line-height: 1.5;
  color: #98a2b3;
}
.pf-ai-foot :deep(.el-button) {
  flex-shrink: 0;
  height: 26px;
  padding: 0 14px;
  border-radius: 999px;
  border-color: #1f2430;
  background: #1f2430;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}
.pf-ai-foot :deep(.el-button:hover) {
  border-color: #333a47;
  background: #333a47;
  color: #fff;
}
.pf-ai-foot :deep(.el-button.is-disabled) {
  opacity: 0.45;
}

/* AI 填充后的确认提示：提醒老师核对，不直接提交 */
.pf-ai-filled {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border: 1px solid #e4e8ef;
  border-radius: 10px;
  background: #f4f6f8;
  font-size: 12px;
  line-height: 1.55;
  color: #475467;
}
.pf-ai-filled .el-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: #1f2430;
}

/* 当前填写摘要：压成一行小字，弱化展示 */
.pf-ctx {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  margin-bottom: 8px;
  font-size: 11px;
  line-height: 1.5;
  color: #98a2b3;
}
.pf-ctx-item {
  white-space: nowrap;
}

.pf-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* 证据材料：文件条目 + 上传 / 链接入口 */
.pf-evidence {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  padding: 7px 9px;
  border: 1px solid #e4e8ef;
  border-radius: 10px;
  background: #fbfcfe;
}
.pf-ev-ic {
  flex: 0 0 auto;
  display: flex;
  color: #667085;
}
.pf-ev-bd {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.pf-ev-name {
  font-size: 12.5px;
  color: #1f2430;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-ev-url {
  font-size: 10.5px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-ev-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.pf-ev-file {
  display: none;
}
.pf-ev-hint {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.5;
  color: #98a2b3;
}
.pf-ev-link {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px;
  border-radius: 10px;
  background: #f7f8fa;
}
.pf-ev-link-name { flex: 0 0 32%; }
.pf-ev-link-url { flex: 1; }

@media (max-width: 767px) {
  .pf-grid2 { grid-template-columns: 1fr; }
  .pf-ev-link { flex-wrap: wrap; }
  .pf-ev-link-name { flex: 1 1 100%; }
  .pf-ev-link-url { flex: 1 1 100%; }
}
</style>