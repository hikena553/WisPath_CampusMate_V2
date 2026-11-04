<template>
  <ResponsivePopup
    :model-value="modelValue"
    :title="survey?.title || '参与评价'"
    :width="isMobile ? '90%' : '380px'"
    align-center
    :close-on-click-modal="false"
    class="tui-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- ============================================================
         移动端 · 定稿版「题卡」：一屏一题，选完自动进下一题
         第 0 步选对象 → 1..N 题 → 最后一步写建议并提交
         ============================================================ -->
    <div v-if="survey && isMobile" class="tm-page tm-fill">
      <!-- 进度点 -->
      <div class="tm-fill-prog">
        <i :class="{ 'tm-done': targetId }"></i>
        <i v-for="(q, i) in survey.questions" :key="q.key" :class="{ 'tm-done': (scores[q.key] || 0) > 0, 'tm-cur': step === i + 1 }"></i>
        <i :class="{ 'tm-cur': step === survey.questions.length + 1 }"></i>
        <span>{{ step }} / {{ survey.questions.length + 1 }}</span>
      </div>

      <!-- 步骤 0：选评价对象 -->
      <template v-if="step === 0">
        <div class="tm-qcard tm-qcard-plain">
          <div class="tm-q-no"><b>先选评价对象</b><span>匿名 · 对方看不到是谁评的</span></div>
          <div class="tm-q-t">这次要评价谁？</div>
          <div class="tm-pick">
            <button
              v-for="t in candidates"
              :key="t.id"
              type="button"
              class="tm-pick-i"
              :class="{ 'tm-on': targetId === t.id }"
              @click="pickTarget(t.id)"
            >
              <span class="tm-pick-av">{{ t.name.slice(0, 1) }}</span>
              <span class="tm-pick-n">
                <b>{{ t.name }}</b>
                <em>{{ t.college || '未填学院' }}</em>
              </span>
            </button>
          </div>
        </div>
        <button class="tm-fill-next" type="button" :disabled="!targetId" @click="step = 1">开始评分</button>
      </template>

      <!-- 步骤 1..N：题卡 -->
      <template v-else-if="step <= survey.questions.length">
        <div class="tm-deck">
          <div class="tm-qcard">
            <div class="tm-q-no">
              <b>第 {{ step }} / {{ survey.questions.length }} 题</b>
              <span>匿名 · 仅用于成长档案</span>
            </div>
            <div class="tm-q-t">{{ survey.questions[step - 1].label }}</div>
            <div class="tm-q-scale">
              <button
                v-for="v in 5"
                :key="v"
                type="button"
                :class="{ 'tm-on': (scores[survey.questions[step - 1].key] || 0) === v }"
                @click="pickScore(survey.questions[step - 1].key, v)"
              >{{ v }}</button>
            </div>
            <div class="tm-q-hint"><span>很不同意</span><span>很同意</span></div>
          </div>
        </div>

        <!-- 下一题预览 -->
        <div v-if="step < survey.questions.length" class="tm-qpeek" @click="step += 1">
          <div class="tm-qp-h"><span>下一题</span><span>第 {{ step + 1 }} / {{ survey.questions.length }}</span></div>
          <div class="tm-qp-t">{{ survey.questions[step].label }}</div>
        </div>
        <div v-else class="tm-qpeek" @click="step += 1">
          <div class="tm-qp-h"><span>最后一步</span><span>写一条建议</span></div>
          <div class="tm-qp-t">5 个维度都评完了，再写一句可改进的具体建议</div>
        </div>

        <div class="tm-q-nav">
          <button type="button" :disabled="step === 1" @click="step -= 1">上一题</button>
          <button type="button" class="tm-pri" :disabled="!(scores[survey.questions[step - 1].key] || 0)" @click="step += 1">
            下一题
          </button>
        </div>
      </template>

      <!-- 步骤 N+1：建议 + 提交 -->
      <template v-else>
        <div class="tm-qcard tm-qcard-plain">
          <div class="tm-q-no"><b>最后一步</b><span>{{ scoreSummary }}</span></div>
          <div class="tm-q-t">给他一条具体建议</div>
          <AiDraftField
            v-model="suggestion"
            label=""
            :rows="4"
            :maxlength="300"
            placeholder="例如：遇到突发情况时及时留下书面记录，方便同事跟进……"
            :draft="aiDraft"
            :points="aiPoints"
          />
        </div>
        <button class="tm-fill-next" type="button" :disabled="!canSubmit || saving" @click="submit">
          {{ saving ? '提交中…' : '匿名提交' }}
        </button>
        <div class="tm-tail">提交后不可修改；系统不保存任何可回溯身份的信息</div>
      </template>
    </div>

    <div v-else-if="survey" class="sf-form">
      <div class="tui-section-hint success">
        <el-icon><Lock /></el-icon>
        <span>本问卷完全匿名：系统不记录填写人，也不保存任何可回溯身份的信息；评分需逐项填写后才能提交。</span>
      </div>

      <div class="sf-ctx">
        <el-icon><Tickets /></el-icon>
        <span>{{ SURVEY_TARGET_LABEL[survey.target_type] }} · {{ survey.questions.length }} 个维度 · {{ survey.period || '未标注周期' }}</span>
      </div>

      <div class="sf-field">
        <label class="sf-label">评价对象</label>
        <el-select v-model="targetId" placeholder="选择被评价的辅导员" style="width: 100%">
          <el-option
            v-for="t in candidates"
            :key="t.id"
            :label="`${t.name}${t.college ? ' · ' + t.college : ''}`"
            :value="t.id"
          />
        </el-select>
      </div>

      <div class="sf-field">
        <label class="sf-label">评分<small>1–5 分，逐项必填</small></label>
        <div v-for="q in survey.questions" :key="q.key" class="sf-q">
          <span class="sf-q-label">{{ q.label }}</span>
          <el-rate v-model="scores[q.key]" :max="q.max || 5" />
        </div>
      </div>

      <AiDraftField
        v-model="suggestion"
        label="建议"
        :rows="3"
        :maxlength="300"
        placeholder="给这位老师一条建设性建议……"
        :draft="aiDraft"
        :points="aiPoints"
      />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!canSubmit" @click="submit">
        匿名提交
      </el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
// v6.1 弹窗减负：移动端弹窗改用全屏子页承接（桌面端仍为 el-dialog）
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { Lock, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import { getTeachers } from '@/api/user'
import { submitSurvey, SURVEY_TARGET_LABEL, type PeerSurvey } from '@/api/peerSurvey'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'

const props = defineProps<{ modelValue: boolean; survey: PeerSurvey | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()

const { isMobile } = useResponsive()
const auth = useAuthStore()

const teachers = ref<{ id: number; name: string; college?: string | null }[]>([])
const targetId = ref<number | undefined>(undefined)
const scores = reactive<Record<string, number>>({})
const suggestion = ref('')
const saving = ref(false)
/** 移动端题卡：0=选对象，1..N=题，N+1=建议 */
const step = ref(0)

function pickTarget(id: number) {
  targetId.value = id
}
/** 选分：记下来并自动进下一题（最后一题进建议步） */
function pickScore(key: string, v: number) {
  scores[key] = v
  window.setTimeout(() => {
    if (step.value <= (props.survey?.questions.length || 1)) step.value += 1
  }, 180)
}
/** 建议步的一句小结 */
const scoreSummary = computed(() => {
  const list = Object.values(scores)
  if (!list.length) return '匿名提交'
  const avg = list.reduce((a, b) => a + b, 0) / list.length
  return `${list.length} 项平均 ${avg.toFixed(1)} 分`
})

/** 排除自己：不自评 */
const candidates = computed(() => teachers.value.filter((t) => t.id !== auth.user?.id))

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** AI 草稿：结合问卷评价类型 + 被评老师 + 日期，写成真实教师口吻的匿名建议 */
const aiDraft = computed(() => {
  const t = teachers.value.find((x) => x.id === targetId.value)
  const name = t?.name || '这位老师'
  const target = SURVEY_TARGET_LABEL[props.survey?.target_type ?? 'peer']
  return `${today()} 匿名反馈（${target}）：${name}老师日常对学生的情绪与诉求回应比较及时，沟通也较坦诚。建议继续保持陪伴投入，遇到突发情况及时留下书面记录、主动同步进展，便于家校与同事协同跟进。`
})
const aiPoints = ['课堂与陪伴投入', '沟通的及时性', '处事是否公正', '一条可改进的具体建议']

const canSubmit = computed(() => {
  if (!props.survey || !targetId.value) return false
  return props.survey.questions.every((q) => (scores[q.key] || 0) > 0)
})

async function loadTeachers() {
  try {
    teachers.value = await getTeachers()
  } catch {
    teachers.value = []
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    step.value = 0
    targetId.value = undefined
    suggestion.value = ''
    Object.keys(scores).forEach((k) => delete scores[k])
    if (!teachers.value.length) await loadTeachers()
  }
)

async function submit() {
  if (!props.survey || !targetId.value) return
  saving.value = true
  try {
    await submitSurvey(props.survey.id, {
      target_teacher_id: targetId.value,
      scores: { ...scores },
      suggestion: suggestion.value.trim() || null,
    })
    ElMessage.success('已匿名提交，感谢反馈')
    emit('update:modelValue', false)
    emit('saved')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '提交失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* ---------- 移动端（定稿版·题卡） ---------- */
.tm-fill { padding: 4px 0 10px; }
.tm-fill-prog {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 16px 10px;
}
.tm-fill-prog i {
  width: 16px;
  height: 4px;
  border-radius: 99px;
  background: #e7ecf6;
  transition: 0.18s;
}
.tm-fill-prog i.tm-done { background: var(--tm-brand); }
.tm-fill-prog i.tm-cur { background: var(--tm-brand-deep); box-shadow: 0 0 0 2px var(--tm-brand-soft); }
.tm-fill-prog span {
  margin-left: auto;
  font-size: 9.2px;
  font-weight: 700;
  color: var(--tm-ink3);
  font-variant-numeric: tabular-nums;
}
.tm-deck { padding: 0 14px; }
.tm-qcard-plain { margin: 0 14px; }
.tm-pick { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.tm-pick-i {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  border-radius: 10px;
  border: 1px solid var(--tm-line);
  background: var(--tm-surf2);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.tm-pick-i.tm-on { border-color: var(--tm-brand); background: var(--tm-brand-soft); }
.tm-pick-av {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--tm-brand-soft);
  color: var(--tm-brand-deep);
  font-size: 11px;
  font-weight: 800;
}
.tm-pick-n { display: flex; flex-direction: column; min-width: 0; }
.tm-pick-n b { font-size: 11.6px; font-weight: 700; color: #16233a; }
.tm-pick-n em { font-style: normal; font-size: 9px; color: var(--tm-ink3); }
.tm-fill-next {
  display: block;
  width: calc(100% - 28px);
  margin: 10px 14px 0;
  height: 40px;
  border: 0;
  border-radius: 11px;
  background: var(--tm-ai-grad);
  color: #fff;
  font: inherit;
  font-size: 12.5px;
  font-weight: 750;
  cursor: pointer;
}
.tm-fill-next:disabled { opacity: 0.45; }
.tm-q-nav { display: flex; gap: 8px; padding: 0 14px; }
.tm-q-nav button {
  flex: 1;
  height: 34px;
  border-radius: 10px;
  border: 1px solid var(--tm-line2);
  background: var(--tm-surf);
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  color: var(--tm-ink2);
  cursor: pointer;
}
.tm-q-nav button.tm-pri { background: var(--tm-ink); border-color: transparent; color: #fff; }
.tm-q-nav button:disabled { opacity: 0.4; }

.sf-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sf-ctx {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 11px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
.sf-ctx .el-icon {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.sf-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 6px;
}
.sf-label small {
  font-size: 11px;
  font-weight: 400;
  color: var(--tui-text-quiet);
}
.sf-q {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 0;
  border-bottom: 1px solid var(--tui-border);
}
.sf-q:last-child {
  border-bottom: none;
}
.sf-q-label {
  font-size: 12.5px;
  color: var(--tui-text);
}
</style>