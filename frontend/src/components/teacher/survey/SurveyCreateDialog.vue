<template>
  <ResponsivePopup
    :model-value="modelValue"
    title="发起问卷"
    :width="isMobile ? '90%' : '420px'"
    align-center
    :close-on-click-modal="false"
    class="tui-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- ① 问卷抬头：标题 + 匿名口径 + 待补项 -->
    <div class="sc-hero">
      <div class="sc-hero-hd">
        <span class="sc-hero-badge">匿名问卷</span>
        <span class="sc-hero-state" :class="{ ok: !pendingTips.length }">
          {{ pendingTips.length ? `待补 ${pendingTips.length} 项` : '可创建' }}
        </span>
      </div>
      <label class="sc-title-label">问卷标题<span>*</span></label>
      <el-input
        v-model="form.title"
        class="sc-title-input"
        maxlength="200"
        placeholder="例如：2026 春季辅导员互评"
      />
      <div class="sc-hero-chips">
        <span class="sc-hc" :class="{ on: titleDone }">
          <el-icon><Check v-if="titleDone" /><EditPen v-else /></el-icon>标题
        </span>
        <span class="sc-hc" :class="{ on: dimsValid }">
          <el-icon><Check v-if="dimsValid" /><Grid v-else /></el-icon>题目 {{ form.questions.length }} 题
        </span>
        <span class="sc-hc" :class="{ on: periodDone }">
          <el-icon><Check v-if="periodDone" /><Calendar v-else /></el-icon>周期（选填）
        </span>
      </div>
      <p class="sc-hero-tip">{{ heroTip }}</p>
    </div>

    <!-- ② 题目设计：本题型的核心，逐题写题干并预览 1–5 分评分 -->
    <section class="sc-block">
      <header class="sc-block-hd">
        <span class="sc-idx">1</span>
        <b>题目设计</b>
        <span class="sc-hd-note">{{ form.questions.length }} 题 · 约 {{ estMinutes }} 分钟</span>
      </header>
      <p class="sc-block-sub">所有题目均为评分题，填写人逐题打 1–5 分；聚合结果不回溯到个人。</p>

      <!-- AI 一键出题 -->
      <div class="sc-ai">
        <div class="sc-ai-hd">
          <AiMascotMark :size="15" />
          <b>AI 一键出题</b>
          <span class="sc-src" :class="aiSource">
            {{ aiLoading ? '生成中…' : aiSource === 'rule' ? '本地模板兜底' : aiSource === 'ai' ? 'AI 已生成' : '描述场景即可出题' }}
          </span>
        </div>
        <div class="sc-ai-row">
          <el-input
            v-model="aiTopic"
            size="small"
            placeholder="描述场景，如：班委互评"
            @keyup.enter="() => applyAiDesign()"
          />
          <el-button class="sc-run" size="small" :loading="aiLoading" @click="() => applyAiDesign()">
            出题
          </el-button>
        </div>
        <div class="sc-ai-chips">
          <button
            v-for="s in SCENARIOS"
            :key="s.name"
            type="button"
            class="sc-ai-chip"
            :disabled="aiLoading"
            @click="useScenario(s)"
          >
            {{ s.name }}
          </button>
        </div>
        <div v-if="aiGenerated.length" class="sc-ai-done">
          <span class="sc-ai-done-hd"><el-icon><Check /></el-icon>已生成 {{ aiGenerated.length }} 道题</span>
          <div class="sc-ai-done-list">
            <span v-for="g in aiGenerated" :key="g">{{ g }}</span>
          </div>
        </div>
      </div>

      <!-- 题目卡列表 -->
      <div v-if="form.questions.length" class="sc-qs">
        <article v-for="(q, i) in form.questions" :key="i" class="sc-qcard">
          <header class="sc-qc-hd">
            <span class="sc-qc-no">Q{{ i + 1 }}</span>
            <span class="sc-qc-type">评分题</span>
            <span class="sc-qc-req">必答</span>
            <div class="sc-qc-ops">
              <button type="button" :disabled="i === 0" aria-label="上移" @click="moveQ(i, -1)">
                <el-icon><ArrowUp /></el-icon>
              </button>
              <button
                type="button"
                :disabled="i === form.questions.length - 1"
                aria-label="下移"
                @click="moveQ(i, 1)"
              >
                <el-icon><ArrowDown /></el-icon>
              </button>
              <button type="button" class="sc-qc-del" aria-label="删除题目" @click="removeQ(i)">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </header>
          <el-input
            v-model="q.label"
            type="textarea"
            :rows="2"
            maxlength="60"
            show-word-limit
            resize="none"
            placeholder="请输入题干，例如：他/她在关心学生方面做得如何？"
          />
          <div class="sc-scale">
            <div class="sc-scale-top">
              <span>评分方式</span>
              <b>1–5 分</b>
            </div>
            <div class="sc-scale-track">
              <span v-for="v in 5" :key="v" class="sc-scale-dot">{{ v }}</span>
            </div>
            <div class="sc-scale-lb"><span>很不同意</span><span>很同意</span></div>
          </div>
        </article>
      </div>

      <div v-else class="sc-qempty">还没有题目，点下方按钮添加，或让 AI 一键出题。</div>

      <button type="button" class="sc-add" @click="addQ">
        <el-icon><Plus /></el-icon>添加评分题
      </button>
    </section>

    <!-- ③ 问卷设置 -->
    <section class="sc-block">
      <header class="sc-block-hd">
        <span class="sc-idx">2</span>
        <b>问卷设置</b>
        <span class="sc-hd-note">对象与发布</span>
      </header>
      <div class="sc-grid2">
        <div class="sc-field">
          <label class="sc-label">评价类型</label>
          <el-select v-model="form.target_type" size="small" style="width: 100%">
            <el-option v-for="t in targetOptions" :key="t" :label="SURVEY_TARGET_LABEL[t]" :value="t" />
          </el-select>
        </div>
        <div class="sc-field">
          <label class="sc-label">周期<small>选填</small></label>
          <el-select
            v-model="form.period"
            size="small"
            filterable
            allow-create
            default-first-option
            clearable
            placeholder="选择或输入"
            style="width: 100%"
          >
            <el-option v-for="p in periodOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </div>
      </div>
      <div class="sc-field sc-field-full">
        <label class="sc-label">发布方式</label>
        <el-select v-model="form.status" size="small" style="width: 100%">
          <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
      </div>
      <p class="sc-block-sub">{{ statusDesc }}</p>
    </section>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button class="sc-submit" type="primary" :loading="saving" :disabled="!valid" @click="submit">
        {{ form.status === 'open' ? '创建并开放' : '保存草稿' }}
      </el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
// v6.1 弹窗减负：移动端弹窗改用全屏子页承接（桌面端仍为 el-dialog）
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import AiMascotMark from '@/components/teacher/ui/AiMascotMark.vue'
import { ArrowDown, ArrowUp, Calendar, Check, Delete, EditPen, Grid, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  createSurvey,
  DEFAULT_SURVEY_QUESTIONS,
  generateSurveyDraft,
  SURVEY_TARGET_LABEL,
  type SurveyQuestion,
  type SurveyStatus,
  type SurveyTargetType,
} from '@/api/peerSurvey'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [] }>()

const { isMobile } = useResponsive()

const targetOptions: SurveyTargetType[] = ['peer', 'student']

/** AI 一键出题：场景描述 → 后端大模型推荐标题与题目（本地规则兜底） */
const aiTopic = ref('')
const aiGenerated = ref<string[]>([])
const aiLoading = ref(false)
const aiSource = ref<'ai' | 'rule' | ''>('')
interface Scenario {
  name: string
  kw: string[]
  title: string
  dims: SurveyQuestion[]
}
const SCENARIOS: Scenario[] = [
  {
    name: '学生评教',
    kw: ['教学', '课堂', '评教', '课程'],
    title: '课程教学反馈',
    dims: [
      { key: 'clear', label: '讲解是否清晰易懂', max: 5 },
      { key: 'interact', label: '课堂互动是否充分', max: 5 },
      { key: 'pace', label: '课程进度是否适中', max: 5 },
      { key: 'gain', label: '学习收获是否明显', max: 5 },
      { key: 'material', label: '学习资料是否实用', max: 5 },
    ],
  },
  {
    name: '辅导员互评',
    kw: ['互评', '辅导员', '同事', '协作'],
    title: '辅导员互评',
    dims: DEFAULT_SURVEY_QUESTIONS.map((q) => ({ ...q })),
  },
  {
    name: '活动反馈',
    kw: ['活动', '比赛', '讲座', '培训'],
    title: '活动组织反馈',
    dims: [
      { key: 'organize', label: '活动组织是否有序', max: 5 },
      { key: 'content', label: '活动内容是否有用', max: 5 },
      { key: 'time', label: '时间安排是否合理', max: 5 },
      { key: 'gain', label: '参与收获是否充足', max: 5 },
      { key: 'recommend', label: '是否愿意再次参加', max: 5 },
    ],
  },
  {
    name: '家校沟通',
    kw: ['家访', '家长', '家校', '沟通'],
    title: '家校沟通反馈',
    dims: [
      { key: 'timely', label: '沟通是否及时', max: 5 },
      { key: 'clear', label: '信息表达是否清晰', max: 5 },
      { key: 'patient', label: '沟通态度是否耐心', max: 5 },
      { key: 'together', label: '协同配合是否有效', max: 5 },
    ],
  },
]

/**
 * AI 一键出题：把场景描述交给后端大模型推荐标题与题目；
 * 后端不可用（未配置模型 / 网络异常）时本地规则兜底，保证按钮永远有结果。
 * 注意：period 可能被 el-select 的 clearable 置为 undefined，所有输入都先做空值兜底。
 */
async function applyAiDesign(topicInput?: unknown) {
  if (aiLoading.value) return
  // 只接受字符串：直接绑到 @click 时 Vue 会把事件对象传进来，必须挡掉
  const topic = typeof topicInput === 'string' ? topicInput.trim() : String(aiTopic.value ?? '').trim()
  aiLoading.value = true
  try {
    const draft = await generateSurveyDraft({ scene: topic, target_type: form.target_type })
    form.questions = draft.questions.map((q) => ({ ...q }))
    form.title = draft.title.slice(0, 200)
    aiGenerated.value = form.questions.map((q) => q.label)
    aiSource.value = draft.source
    ElMessage.success(
      draft.source === 'ai'
        ? `AI 已生成 ${form.questions.length} 道题与标题，可继续调整`
        : `已用本地模板生成 ${form.questions.length} 道题，可继续调整`
    )
  } catch {
    // 接口异常：沿用本地场景规则，避免用户看到「点击无反应」
    const hit = topic ? SCENARIOS.find((s) => s.kw.some((k) => topic.includes(k))) : undefined
    const dims = hit ? hit.dims : DEFAULT_SURVEY_QUESTIONS
    form.questions = dims.map((q) => ({ ...q }))
    const period = String(form.period ?? '').trim() || `${new Date().getFullYear()} 春季`
    const base = hit ? hit.title : topic || '辅导员互评'
    form.title = `${period}${SURVEY_TARGET_LABEL[form.target_type]} · ${base}`.slice(0, 200)
    aiGenerated.value = dims.map((q) => q.label)
    aiSource.value = 'rule'
    ElMessage.success(`已生成 ${form.questions.length} 道题，可继续调整`)
  } finally {
    aiLoading.value = false
  }
}

function useScenario(s: Scenario) {
  if (aiLoading.value) return
  aiTopic.value = s.name
  applyAiDesign(s.name)
}

const statusOptions: { value: SurveyStatus; label: string }[] = [
  { value: 'open', label: '立即开放' },
  { value: 'draft', label: '存为草稿' },
]

const form = reactive<{
  title: string
  target_type: SurveyTargetType
  period: string
  status: SurveyStatus
  questions: SurveyQuestion[]
}>({
  title: '',
  target_type: 'peer',
  period: '',
  status: 'open',
  questions: [],
})

const saving = ref(false)

/** 周期候选：当前学年与上一学年，可再手动输入 */
const periodOptions = computed(() => {
  const y = new Date().getFullYear()
  return [
    { label: `${y} 春季学期`, value: `${y}-spring` },
    { label: `${y} 秋季学期`, value: `${y}-fall` },
    { label: `${y - 1} 秋季学期`, value: `${y - 1}-fall` },
    { label: `${y - 1} 春季学期`, value: `${y - 1}-spring` },
  ]
})

/* ---------- 填写进度 / 待补提醒 ---------- */
const titleDone = computed(() => String(form.title ?? '').trim().length > 0)
const periodDone = computed(() => String(form.period ?? '').trim().length > 0)
const dimsValid = computed(() => form.questions.length > 0 && form.questions.every((q) => q.label.trim()))
/** 每题约 15 秒，至少显示 1 分钟 */
const estMinutes = computed(() => Math.max(1, Math.round((form.questions.length * 15) / 60)))
const pendingTips = computed(() => {
  const out: string[] = []
  if (!titleDone.value) out.push('问卷标题')
  if (!dimsValid.value) out.push('题目题干')
  return out
})
const heroTip = computed(() =>
  pendingTips.value.length ? `还差：${pendingTips.value.join('、')}，补齐后即可创建。` : '内容已齐全，核对后即可创建。'
)
const statusDesc = computed(() =>
  form.status === 'open' ? '创建后立即进入「待参与」，受众可马上填答。' : '仅保存到「我创建的」，可在列表里随时开放。'
)

const valid = computed(() => !pendingTips.value.length)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.title = ''
    aiTopic.value = ''
    aiGenerated.value = []
    aiSource.value = ''
    aiLoading.value = false
    form.target_type = 'peer'
    form.period = ''
    form.status = 'open'
    form.questions = DEFAULT_SURVEY_QUESTIONS.map((q) => ({ ...q }))
  }
)

function addQ() {
  form.questions.push({ key: '', label: '', max: 5 })
}
function removeQ(i: number) {
  form.questions.splice(i, 1)
}
function moveQ(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= form.questions.length) return
  const list = form.questions
  ;[list[i], list[j]] = [list[j], list[i]]
}

async function submit() {
  if (!valid.value) return
  saving.value = true
  try {
    // 题目只展示题干，内部标识按顺序补齐并去重，与后端兜底口径一致
    const usedKeys = new Set<string>()
    const questions = form.questions.map((q, i) => {
      const base = q.key.trim() || `q${i + 1}`
      let key = base
      let n = 1
      while (usedKeys.has(key)) key = `${base}_${n++}`
      usedKeys.add(key)
      return { key, label: q.label.trim(), max: q.max || 5 }
    })
    await createSurvey({
      title: String(form.title ?? '').trim(),
      target_type: form.target_type,
      period: String(form.period ?? '').trim() || null,
      questions,
      status: form.status,
    })
    ElMessage.success(form.status === 'open' ? '问卷已开放' : '草稿已保存')
    emit('update:modelValue', false)
    emit('created')
  } catch {
    ElMessage.error('创建失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* ============ 问卷抬头 ============ */
.sc-hero {
  padding: 11px 12px;
  border: 1px solid #e4e8ef;
  border-radius: 12px;
  background: #fbfcfe;
}
.sc-hero-hd {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sc-hero-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: #eceff3;
  color: #1f2430;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2px;
}
.sc-hero-state {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f2f4f7;
  color: #667085;
  font-size: 11px;
  font-weight: 650;
  white-space: nowrap;
}
.sc-hero-state.ok {
  background: #eceff3;
  color: #1f2430;
}
.sc-title-label {
  display: block;
  margin-top: 10px;
  font-size: 12px;
  font-weight: 650;
  color: #667085;
}
.sc-title-label span {
  margin-left: 2px;
  color: #b54708;
}
.sc-title-input {
  margin-top: 5px;
}
.sc-hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}
.sc-hc {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 8px;
  border: 1px dashed #d6dbe3;
  border-radius: 999px;
  background: #fff;
  color: #98a2b3;
  font-size: 11.5px;
  font-weight: 600;
}
.sc-hc .el-icon {
  font-size: 11px;
}
.sc-hc.on {
  border-style: solid;
  border-color: transparent;
  background: #eceff3;
  color: #1f2430;
}
.sc-hero-tip {
  margin: 8px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: #667085;
}

/* ============ 分区卡 ============ */
.sc-block {
  margin-top: 12px;
  padding: 11px 12px;
  border: 1px solid #e4e8ef;
  border-radius: 12px;
  background: #fff;
}
.sc-block-hd {
  display: flex;
  align-items: center;
  gap: 7px;
}
.sc-block-hd b {
  font-size: 13px;
  font-weight: 700;
  color: #1f2430;
}
.sc-idx {
  width: 17px;
  height: 17px;
  flex: 0 0 17px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #1f2430;
  color: #fff;
  font-size: 10.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.sc-hd-note {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  color: #98a2b3;
  font-variant-numeric: tabular-nums;
}
.sc-block-sub {
  margin: 5px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: #98a2b3;
}

/* AI 一键出题 */
.sc-ai {
  margin-top: 10px;
  padding: 9px 10px;
  border: 1px solid #e4e8ef;
  border-radius: 10px;
  background: #f8f9fb;
}
.sc-ai-hd {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sc-ai-hd b {
  font-size: 12.5px;
  font-weight: 700;
  color: #1f2430;
}
.sc-src {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 6px;
  background: #fff;
  color: #98a2b3;
  font-size: 11px;
  white-space: nowrap;
}
.sc-src.ai {
  color: #475467;
}
.sc-ai-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.sc-ai-row :deep(.el-button.sc-run) {
  flex: 0 0 auto;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px !important;
  border-color: #1f2430;
  background: #1f2430;
  color: #fff;
  font-size: 10.5px;
  font-weight: 600;
}
.sc-ai-row :deep(.el-button.sc-run:hover) {
  border-color: #333a47;
  background: #333a47;
  color: #fff;
}
.sc-ai-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.sc-ai-chip {
  padding: 3px 9px;
  border: 1px solid #e4e8ef;
  border-radius: 999px;
  background: #fff;
  color: #667085;
  font-family: inherit;
  font-size: 11.5px;
  cursor: pointer;
}
.sc-ai-chip:hover:not(:disabled) {
  border-color: #1f2430;
  color: #1f2430;
}
.sc-ai-chip:active {
  background: #f7f8fa;
}
.sc-ai-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.sc-ai-done {
  margin-top: 8px;
  padding: 7px 9px;
  border: 1px solid #e4e8ef;
  border-radius: 9px;
  background: #fff;
}
.sc-ai-done-hd {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 700;
  color: #1f2430;
}
.sc-ai-done-hd .el-icon {
  font-size: 11px;
}
.sc-ai-done-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 5px;
}
.sc-ai-done-list span {
  padding: 1px 6px;
  border: 1px solid #e9edf3;
  border-radius: 5px;
  background: #fbfcfe;
  color: #667085;
  font-size: 11px;
}

/* ============ 题目卡 ============ */
.sc-qs {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 11px;
}
.sc-qcard {
  padding: 9px 10px 10px;
  border: 1px solid #e4e8ef;
  border-radius: 11px;
  background: #fff;
}
.sc-qc-hd {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 7px;
}
.sc-qc-no {
  font-size: 12px;
  font-weight: 800;
  color: #1f2430;
  letter-spacing: 0.2px;
  font-variant-numeric: tabular-nums;
}
.sc-qc-type {
  padding: 1px 6px;
  border-radius: 5px;
  background: #f2f4f7;
  color: #667085;
  font-size: 10.5px;
  font-weight: 650;
}
.sc-qc-req {
  padding: 1px 6px;
  border-radius: 5px;
  background: #eceff3;
  color: #475467;
  font-size: 10.5px;
  font-weight: 650;
}
.sc-qc-ops {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 2px;
}
.sc-qc-ops button {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #98a2b3;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.sc-qc-ops button:hover:not(:disabled) {
  background: #f2f4f7;
  color: #1f2430;
}
.sc-qc-ops button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.sc-qc-ops .sc-qc-del:hover:not(:disabled) {
  background: #fdf2f2;
  color: #b42318;
}

/* 评分方式预览 */
.sc-scale {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 9px;
  background: #f8f9fb;
}
.sc-scale-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 11px;
  color: #98a2b3;
}
.sc-scale-top b {
  font-size: 11px;
  font-weight: 700;
  color: #475467;
}
.sc-scale-track {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}
.sc-scale-dot {
  flex: 1;
  height: 22px;
  display: grid;
  place-items: center;
  border: 1px solid #e4e8ef;
  border-radius: 6px;
  background: #fff;
  color: #667085;
  font-size: 11px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}
.sc-scale-lb {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 10px;
  color: #98a2b3;
}

.sc-qempty {
  margin-top: 11px;
  padding: 16px 10px;
  border: 1px dashed #d6dbe3;
  border-radius: 10px;
  background: #fbfcfe;
  text-align: center;
  font-size: 11.5px;
  line-height: 1.5;
  color: #98a2b3;
}
.sc-add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 100%;
  height: 34px;
  margin-top: 9px;
  border: 1px dashed #d6dbe3;
  border-radius: 9px;
  background: #fbfcfe;
  color: #667085;
  font-family: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.sc-add:hover {
  border-color: #1f2430;
  background: #fff;
  color: #1f2430;
}

/* ============ 问卷设置 ============ */
.sc-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}
.sc-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.sc-field-full {
  margin-top: 10px;
}
.sc-label {
  font-size: 12px;
  font-weight: 600;
  color: #667085;
}
.sc-label small {
  font-weight: 400;
  color: #98a2b3;
  margin-left: 4px;
}

/* 输入类控件：浅底 + 发丝描边，聚焦转深墨 */
.sc-block :deep(.el-input__wrapper),
.sc-hero :deep(.el-input__wrapper) {
  border-radius: 9px;
  background: #fbfcfe;
  box-shadow: 0 0 0 1px #e4e8ef inset;
}
.sc-block :deep(.el-input__wrapper:hover),
.sc-hero :deep(.el-input__wrapper:hover) {
  background: #fff;
  box-shadow: 0 0 0 1px #d7dce4 inset;
}
.sc-block :deep(.el-input__wrapper.is-focus),
.sc-hero :deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 0 0 0 1px #1f2430 inset;
}
.sc-title-input :deep(.el-input__inner) {
  height: 34px;
  font-size: 13.5px;
  font-weight: 600;
}
.sc-qcard :deep(.el-textarea__inner) {
  min-height: 56px !important;
  padding: 8px 10px;
  border-radius: 9px;
  border: 1px solid #e4e8ef;
  box-shadow: none;
  background: #fbfcfe;
  font-size: 12.5px;
  line-height: 1.55;
  color: #1f2430;
}
.sc-qcard :deep(.el-textarea__inner:hover) {
  border-color: #d7dce4;
  background: #fff;
}
.sc-qcard :deep(.el-textarea__inner:focus) {
  border-color: #1f2430;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(31, 36, 48, 0.05);
}
.sc-qcard :deep(.el-input__count) {
  background: transparent;
  color: #9aa1ad;
}

/* 底部主按钮：中性深色实心（按钮是弹窗 footer 的直接子节点，需用自身作用域属性命中） */
.sc-submit.el-button {
  border-color: #1f2430 !important;
  background: #1f2430 !important;
  color: #fff !important;
}
.sc-submit.el-button:hover {
  border-color: #333a47 !important;
  background: #333a47 !important;
}
.sc-submit.el-button.is-disabled {
  border-color: #e4e8ef !important;
  background: #f2f4f7 !important;
  color: #98a2b3 !important;
}

@media (max-width: 767px) {
  .sc-grid2 {
    grid-template-columns: 1fr;
  }
}
</style>
