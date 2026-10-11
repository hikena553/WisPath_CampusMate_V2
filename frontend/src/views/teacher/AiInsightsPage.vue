<template>
  <div class="tui-page">
    <SubPageHeader title="智能提示" sub="主动发现 · 推荐联系" fallback="/teacher" />

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">智能提示</h2>
          <p class="tui-header-sub">绵小城为你整理的班级情况与建议联系对象，逐条处置后即转为跟进任务</p>
        </div>
        <div class="tui-header-actions">
          <el-button round :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </header>

      <div class="tui-stat-row cols-2">
        <div class="tui-stat">
          <span class="tui-stat-num" :class="{ 'is-alert': highCount > 0 }">{{ shownActions.length }}</span>
          <span class="tui-stat-label">主动发现</span>
        </div>
        <div class="tui-stat">
          <span class="tui-stat-num">{{ shownSuggestions.length }}</span>
          <span class="tui-stat-label">建议联系</span>
        </div>
      </div>

      <!-- 闭环：从学生成长档案聚焦该生建议 -->
      <div v-if="studentFocus" class="ai-focus">
        <el-icon :size="14"><User /></el-icon>
        <span class="ai-focus-text">已聚焦学生「{{ studentFocus.name || '该生' }}」，仅显示与其相关的发现与建议</span>
        <button class="ai-focus-clear" type="button" @click="clearStudentFocus">清除聚焦</button>
      </div>

      <TuiSegmented v-model="tab" class="ai-seg" :options="segOptions" />

      <div v-loading="loading" class="ai-body">
        <!-- 主动发现 -->
        <template v-if="tab === 'proactive'">
          <div v-if="!loading && !shownActions.length" class="ai-empty">暂无新发现，班级状态平稳</div>
          <button
            v-for="act in shownActions"
            :key="`${act.trigger}-${act.student_id}`"
            class="ai-row is-clickable"
            type="button"
            @click="gotoCrisis(act)"
          >
            <span class="ai-flag" :class="`is-${priorityKey(act.priority)}`">{{ priorityText(act.priority) }}</span>
            <span class="ai-row-main">
              <span class="ai-row-title">{{ act.title }}</span>
              <span class="ai-row-desc">{{ act.content }}</span>
            </span>
            <el-icon class="ai-arrow" :size="13"><ArrowRight /></el-icon>
          </button>
        </template>

        <!-- 推荐联系 -->
        <template v-else>
          <div v-if="!loading && !shownSuggestions.length" class="ai-empty">暂无推荐联系对象</div>
          <template v-else>
            <div class="ai-batch">
              <span class="ai-batch-text">建议优先联系 {{ shownSuggestions.length }} 位学生</span>
              <button class="ai-batch-btn" type="button" :disabled="batchLoading" @click="convertAll">
                {{ batchLoading ? '处理中…' : '全部转为跟进' }}
              </button>
            </div>
            <div v-for="c in shownSuggestions" :key="c.student_id" class="ai-row">
              <span class="ai-avatar">{{ c.student_name.slice(0, 1) }}</span>
              <span class="ai-row-main">
                <span class="ai-row-title">
                  <button class="ai-name-link" type="button" @click="gotoStudent(c.student_id)">
                    {{ c.student_name }}
                  </button>
                  <span class="ai-flag" :class="`is-${contactKey(c.priority)}`">{{ contactText(c.priority) }}</span>
                </span>
                <span class="ai-row-desc is-clamp">{{ c.reason }}</span>
              </span>
              <button
                class="ai-row-op"
                type="button"
                :disabled="convertedIds.has(c.student_id) || loadingIds.has(c.student_id)"
                @click="convert(c)"
              >
                {{ convertedIds.has(c.student_id) ? '已跟进' : loadingIds.has(c.student_id) ? '处理中' : '转为跟进' }}
              </button>
            </div>
          </template>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Refresh, User } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { useResponsive } from '@/composables/useResponsive'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'
import { suggestContacts, persistContactSuggestions, type ContactSuggestion } from '@/api/teacher'

defineOptions({ name: 'teacher-ai-insights' })

const router = useRouter()
const route = useRoute()
const { isMobile } = useResponsive()

const loading = ref(false)
const proactiveActions = ref<ProactiveAction[]>([])
const contactSuggestions = ref<ContactSuggestion[]>([])

/** 闭环：从学生成长档案跳来时聚焦该生 */
const studentFocus = ref<{ id: number; name: string } | null>(null)

function matchesFocus(id?: number | null, name?: string | null) {
  const f = studentFocus.value
  if (!f) return true
  if (f.id && id != null) return id === f.id
  if (f.name && name) return name === f.name
  return true
}

const shownActions = computed(() =>
  studentFocus.value ? proactiveActions.value.filter((a) => matchesFocus(a.student_id)) : proactiveActions.value
)
const shownSuggestions = computed(() =>
  studentFocus.value ? contactSuggestions.value.filter((c) => matchesFocus(c.student_id, c.student_name)) : contactSuggestions.value
)

const tab = ref<'proactive' | 'followup'>('proactive')

const segOptions = computed(() => [
  { value: 'proactive', label: '主动发现', count: shownActions.value.length },
  { value: 'followup', label: '推荐联系', count: shownSuggestions.value.length },
])

const highCount = computed(() => shownActions.value.filter((x) => x.priority >= 80).length)

/** 已转为跟进的学生 id（本地即时反馈，避免重复点击） */
const convertedIds = ref<Set<number>>(new Set())
const loadingIds = ref<Set<number>>(new Set())
const batchLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const sid = studentFocus.value?.id || undefined
    const [acts, contacts] = await Promise.all([
      fetchProactiveActions(sid).catch(() => [] as ProactiveAction[]),
      suggestContacts(sid).catch(() => [] as ContactSuggestion[]),
    ])
    proactiveActions.value = acts
    contactSuggestions.value = contacts
  } finally {
    loading.value = false
  }
}

async function convert(c: ContactSuggestion) {
  if (convertedIds.value.has(c.student_id)) return
  loadingIds.value.add(c.student_id)
  try {
    const res = await persistContactSuggestions([c])
    convertedIds.value.add(c.student_id)
    ElMessage.success(res.created > 0 ? '已转为跟进任务' : '该学生已在跟进中')
  } catch {
    ElMessage.error('转为跟进失败')
  } finally {
    loadingIds.value.delete(c.student_id)
  }
}

async function convertAll() {
  batchLoading.value = true
  try {
    const res = await persistContactSuggestions(shownSuggestions.value)
    shownSuggestions.value.forEach((c) => convertedIds.value.add(c.student_id))
    ElMessage.success(res.created > 0 ? `已转为跟进任务 ${res.created} 条` : '推荐学生均已在跟进中')
  } catch {
    ElMessage.error('批量转为跟进失败')
  } finally {
    batchLoading.value = false
  }
}

/** 闭环出口：主动发现 → 预警中心（带该生上下文） */
function gotoCrisis(act: ProactiveAction) {
  router.push({ path: '/teacher/crisis', query: { student_id: String(act.student_id) } })
}

/** 闭环出口：推荐联系 → 该生成长档案 */
function gotoStudent(id: number) {
  router.push({ path: '/teacher/students', query: { student: String(id) } })
}

function clearStudentFocus() {
  studentFocus.value = null
  router.replace({ path: '/teacher/ai' })
}

function priorityKey(p: number) {
  if (p >= 80) return 'high'
  if (p >= 60) return 'mid'
  return 'low'
}
function priorityText(p: number) {
  if (p >= 80) return '高危'
  if (p >= 60) return '关注'
  return '提醒'
}
function contactKey(p: string) {
  if (p === 'high') return 'high'
  if (p === 'medium') return 'mid'
  return 'low'
}
function contactText(p: string) {
  if (p === 'high') return '建议尽快'
  if (p === 'medium') return '建议关注'
  return '保持联系'
}

onMounted(() => {
  // 闭环：解析学生成长档案传来的聚焦参数
  const sid = Number(route.query.student_id)
  const sname = route.query.student_name ? String(route.query.student_name) : ''
  if (sid || sname) studentFocus.value = { id: sid || 0, name: sname }
  load().then(() => {
    // 聚焦该生时，若其无主动发现但有联系建议，自动切到「推荐联系」
    if (studentFocus.value && !shownActions.value.length && shownSuggestions.value.length) {
      tab.value = 'followup'
    }
  })
})
</script>

<style scoped>
.tui-stat-num.is-alert { color: #d92d20; }
.ai-seg { margin-bottom: 12px; }

/* 闭环聚焦条：从学生成长档案跳来时的上下文提示 */
.ai-focus {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  margin-bottom: 12px;
  border-radius: 10px;
  background: #eff4ff;
  border: 1px solid #d3e0fb;
  color: #1d4ed8;
  font-size: 12.5px;
}
.ai-focus-text { flex: 1; min-width: 0; font-weight: 500; }
.ai-focus-clear {
  flex-shrink: 0;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #1d4ed8;
  cursor: pointer;
}
.ai-focus-clear:hover { text-decoration: underline; }

.ai-body {
  min-height: 92px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-empty {
  padding: 26px 0;
  text-align: center;
  font-size: 12.5px;
  color: #98a2b3;
}

.ai-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 1px solid #f2f4f7;
  border-radius: 10px;
  background: #fff;
  font-family: inherit;
  text-align: left;
}
.ai-row.is-clickable { cursor: pointer; }
.ai-row.is-clickable:hover { border-color: #d0d5dd; }

.ai-avatar {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #eff4ff;
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 600;
}

.ai-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ai-row-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #101828;
  min-width: 0;
}
.ai-row-desc {
  font-size: 12px;
  color: #667085;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-row-desc.is-clamp {
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.ai-name-link {
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #101828;
  cursor: pointer;
}
.ai-name-link:hover { color: #2563eb; }

.ai-flag {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
}
.ai-flag.is-high { background: #fef3f2; color: #d92d20; }
.ai-flag.is-mid { background: #fffaeb; color: #b54708; }
.ai-flag.is-low { background: #f2f4f7; color: #667085; }

.ai-arrow { flex-shrink: 0; color: #98a2b3; }

.ai-row-op {
  flex-shrink: 0;
  padding: 4px 10px;
  border: 1px solid #cfdcf3;
  border-radius: 999px;
  background: #fff;
  color: #1d4ed8;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.ai-row-op:hover:not(:disabled) { background: #eff4ff; }
.ai-row-op:disabled {
  border-color: #e4e7ec;
  color: #98a2b3;
  cursor: default;
}

.ai-batch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f7f9fc;
}
.ai-batch-text { font-size: 12px; color: #667085; }
.ai-batch-btn {
  flex-shrink: 0;
  padding: 5px 12px;
  border: none;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.ai-batch-btn:hover:not(:disabled) { background: #1d4ed8; }
.ai-batch-btn:disabled { background: #b6c6e8; cursor: default; }
</style>