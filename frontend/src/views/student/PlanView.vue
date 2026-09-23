<template>
  <div class="plan-page">
    <!-- 顶部标题 -->
    <div class="plan-header">
      <div>
        <h2 class="plan-title">学习计划</h2>
        <p class="plan-sub">目标拆解 · 任务打卡 · AI 顺延建议</p>
      </div>
      <el-button type="primary" round @click="openPlanDialog()">
        <el-icon style="margin-right:4px"><Plus /></el-icon>新建计划
      </el-button>
    </div>

    <!-- 今日概览 -->
    <div class="card today-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">今日打卡</span>
        <el-tag size="small" :type="streak.today_checked ? 'success' : 'info'" effect="light" round>
          {{ streak.today_checked ? '今日已打卡' : '今日未打卡' }}
        </el-tag>
      </div>
      <div class="streak-row">
        <div class="streak-item">
          <div class="streak-num">{{ streak.current || 0 }}</div>
          <div class="streak-label">当前连续(天)</div>
        </div>
        <div class="streak-divider"></div>
        <div class="streak-item">
          <div class="streak-num">{{ streak.longest || 0 }}</div>
          <div class="streak-label">最长连续(天)</div>
        </div>
        <div class="streak-divider"></div>
        <div class="streak-item">
          <div class="streak-num">{{ totalMinutes }}</div>
          <div class="streak-label">累计学习(分钟)</div>
        </div>
      </div>
      <div v-if="reminderList.length" class="reminder-box">
        <div v-for="(r, i) in reminderList" :key="i" class="reminder-item">
          <el-icon :size="14" style="color:#e6a23c;flex-shrink:0"><WarningFilled /></el-icon>
          <span class="reminder-text">{{ r }}</span>
        </div>
      </div>
    </div>

    <!-- 今日任务 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">今日任务</span>
        <el-button size="small" text type="primary" :loading="aiLoading" @click="runAISuggest">AI 顺延/重排建议</el-button>
      </div>
      <div v-if="!todayTasks.length" class="empty-tip">今天没有到期任务，好好休息或提前推进吧</div>
      <div v-for="(t, idx) in todayTasks" :key="t.task_id ?? 't' + idx" class="today-task">
        <el-checkbox
          :model-value="t.checked_today"
          @change="() => handleCheckinFromToday(t)"
        />
        <div class="today-task-info">
          <div class="today-task-title" :class="{ 'task-done': t.status === 'done' }">{{ t.title }}</div>
          <div class="today-task-meta">
            <span class="meta-plan">{{ t.plan_title }}</span>
            <el-tag v-if="t.due_date" size="small" type="danger" effect="plain" round class="meta-tag">
              {{ t.due_date }}
            </el-tag>
            <el-tag size="small" :type="t.checked_today ? 'success' : 'info'" effect="light" round class="meta-tag">
              {{ t.checked_today ? '已打卡' : '未打卡' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 计划列表 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">我的计划</span>
      </div>
      <div class="plan-filter">
        <el-tag
          v-for="f in planFilters"
          :key="f.value"
          :type="planStatus === f.value ? 'primary' : 'info'"
          :effect="planStatus === f.value ? 'dark' : 'plain'"
          class="filter-tag" round
          @click="switchPlanStatus(f.value)"
        >{{ f.label }}</el-tag>
      </div>
      <div v-if="!plans.length && planStatus !== 'active'" class="empty-tip">暂无{{ planStatusLabel }}的计划</div>
      <div v-if="!plans.length && planStatus === 'active'" class="empty-tip">
        还没有进行中的计划，点击右上角「新建计划」开始吧
      </div>
      <div v-for="p in plans" :key="p.id" class="plan-card" :class="{ 'plan-expanded': expandedPlan === p.id }">
        <div class="plan-card-head" @click="toggleExpand(p.id)">
          <div class="plan-card-left">
            <div class="plan-card-title">{{ p.title }}</div>
            <div class="plan-card-meta">
              <el-tag v-if="p.goal_title" size="small" type="warning" effect="light" round>目标: {{ p.goal_title }}</el-tag>
              <span class="meta-date">{{ p.start_date }} ~ {{ p.end_date || '至今' }}</span>
            </div>
          </div>
          <div class="plan-card-right">
            <span class="plan-rate">{{ p.done_rate }}%</span>
            <el-icon class="expand-icon" :class="{ rotated: expandedPlan === p.id }"><ArrowDown /></el-icon>
          </div>
        </div>
        <div class="plan-progress">
          <el-progress :percentage="p.done_rate" :stroke-width="8" :show-text="false" :color="progressColor(p.done_rate)" />
        </div>
        <div class="plan-card-stats">
          <span class="stat">任务 <b>{{ p.task_done }}/{{ p.task_total }}</b></span>
          <span class="stat" :class="{ 'stat-warn': p.overdue > 0 }">逾期 <b>{{ p.overdue }}</b></span>
          <span class="stat">打卡 <b>{{ p.checkin_days }} 天</b></span>
        </div>
        <div v-if="expandedPlan === p.id" class="plan-detail">
          <div v-if="p.objective" class="plan-objective">{{ p.objective }}</div>
          <div class="detail-actions">
            <el-button size="small" plain type="primary" @click="openTaskDialog(p.id)"><el-icon style="margin-right:4px"><Plus /></el-icon>添加任务</el-button>
            <el-button size="small" plain type="warning" @click="openPlanDialog(p)">编辑计划</el-button>
            <el-button size="small" plain type="primary" :loading="aiLoading" @click="runAISuggest(p.id)">AI 建议</el-button>
            <el-button size="small" plain type="danger" @click="handleDeletePlan(p.id)">删除</el-button>
          </div>
          <div v-if="!tasksByPlan[p.id]?.length" class="empty-tip">该计划还没有任务</div>
          <div v-for="t in tasksByPlan[p.id] || []" :key="t.id" class="task-item">
            <div class="task-item-main">
              <div class="task-title-row">
                <span class="task-title" :class="{ 'task-done': t.status === 'done' }">{{ t.title }}</span>
                <el-tag size="small" :type="priorityType(t.priority)" effect="plain" round>{{ priorityLabel(t.priority) }}</el-tag>
              </div>
              <div v-if="t.description" class="task-desc">{{ t.description }}</div>
              <div class="task-meta">
                <span v-if="t.due_date" class="meta-date" :class="{ 'meta-overdue': isOverdue(t) }">
                  <el-icon :size="12"><Calendar /></el-icon> {{ t.due_date }} {{ isOverdue(t) ? '(已逾期)' : '' }}
                </span>
                <el-tag size="small" :type="statusType(t.status)" effect="light" round>{{ statusLabel(t.status) }}</el-tag>
              </div>
            </div>
            <div class="task-actions">
              <el-button v-if="t.status === 'todo'" size="small" text type="primary" @click="setTaskStatus(t, 'doing')">开始</el-button>
              <el-button v-if="t.status === 'doing'" size="small" text type="success" @click="setTaskStatus(t, 'done')">完成</el-button>
              <el-button v-if="t.status !== 'done'" size="small" text type="warning" @click="openCheckinDialog(t)" :disabled="t.checked_today">打卡</el-button>
              <el-button size="small" text type="primary" @click="openTaskDialog(p.id, t)">编辑</el-button>
              <el-button size="small" text type="danger" @click="handleDeleteTask(t.id)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 长期目标 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">长期目标</span>
        <el-button size="small" text type="primary" @click="openGoalDialog()"><el-icon style="margin-right:2px"><Plus /></el-icon>新建目标</el-button>
      </div>
      <div v-if="!goals.length" class="empty-tip">设置长期目标后，AI 会围绕目标为你推荐资源、串联计划</div>
      <div v-for="g in goals" :key="g.id" class="goal-card">
        <div class="goal-head">
          <el-tag size="small" type="primary" effect="dark" round>{{ g.goal_type }}</el-tag>
          <span class="goal-title">{{ g.title }}</span>
        </div>
        <div class="goal-meta">
          <span v-if="g.target_date" class="meta-date">目标日期: {{ g.target_date }}</span>
          <span class="meta-date">关联计划: {{ g.plan_count }} 个</span>
        </div>
        <div class="goal-progress">
          <span class="goal-progress-label">进度</span>
          <el-progress :percentage="g.progress" :stroke-width="6" :show-text="false" class="goal-progress-bar" />
          <el-button size="small" text type="primary" @click="openGoalDialog(g)">编辑</el-button>
          <el-button size="small" text type="danger" @click="handleDeleteGoal(g)">删除</el-button>
        </div>
      </div>
    </div>

    <!-- 计划弹窗 -->
    <el-dialog v-model="planDialogVisible" :title="planForm.id ? '编辑计划' : '新建计划'" width="480px" :close-on-click-modal="false">
      <el-form :model="planForm" label-width="80px">
        <el-form-item label="计划标题" required>
          <el-input v-model="planForm.title" placeholder="例如：Java 基础复习计划" maxlength="50" />
        </el-form-item>
        <el-form-item label="目标">
          <el-select v-model="planForm.goal_id" placeholder="关联长期目标（可选）" clearable style="width:100%">
            <el-option v-for="g in goals" :key="g.id" :label="`${g.goal_type} · ${g.title}`" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划目标">
          <el-input v-model="planForm.objective" type="textarea" :rows="2" placeholder="这个计划想达成什么？" />
        </el-form-item>
        <el-form-item label="当前阶段">
          <el-input v-model="planForm.stage" placeholder="例如：基础阶段 / 冲刺阶段" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始日期" required>
              <el-date-picker v-model="planForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="planForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="planDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPlan" @click="savePlan">保存</el-button>
      </template>
    </el-dialog>

    <!-- 任务弹窗 -->
    <el-dialog v-model="taskDialogVisible" :title="taskForm.id ? '编辑任务' : '添加任务'" width="460px" :close-on-click-modal="false">
      <el-form :model="taskForm" label-width="80px">
        <el-form-item label="任务标题" required>
          <el-input v-model="taskForm.title" placeholder="任务内容" maxlength="100" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="taskForm.description" type="textarea" :rows="2" placeholder="补充说明（可选）" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="taskForm.due_date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="不填则视为无期限" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="taskForm.priority">
            <el-radio-button value="high">高</el-radio-button>
            <el-radio-button value="medium">中</el-radio-button>
            <el-radio-button value="low">低</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingTask" @click="saveTask">保存</el-button>
      </template>
    </el-dialog>

    <!-- 打卡弹窗 -->
    <el-dialog v-model="checkinDialogVisible" title="任务打卡" width="400px" :close-on-click-modal="false">
      <div class="checkin-task-title">「{{ checkinTask?.title }}」</div>
      <el-form label-width="80px">
        <el-form-item label="学习时长">
          <el-input-number v-model="checkinForm.minutes" :min="1" :max="600" style="width:100%" />
          <span class="checkin-unit">分钟</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="checkinForm.note" type="textarea" :rows="2" placeholder="今天学得怎么样？（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkinDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="savingCheckin" @click="saveCheckin">确认打卡</el-button>
      </template>
    </el-dialog>

    <!-- 目标弹窗 -->
    <el-dialog v-model="goalDialogVisible" :title="goalForm.id ? '编辑目标' : '新建目标'" width="460px" :close-on-click-modal="false">
      <el-form :model="goalForm" label-width="80px">
        <el-form-item label="目标类型" required>
          <el-select v-model="goalForm.goal_type" style="width:100%">
            <el-option v-for="t in goalTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标描述" required>
          <el-input v-model="goalForm.title" placeholder="例如：找到一份后端开发实习" maxlength="100" />
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="goalForm.target_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item v-if="goalForm.id" label="进度(%)">
          <el-slider v-model="goalForm.progress" :max="100" show-input />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="goalForm.note" type="textarea" :rows="2" placeholder="补充说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="goalDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingGoal" @click="saveGoal">保存</el-button>
      </template>
    </el-dialog>

    <!-- AI 建议弹窗 -->
    <el-dialog v-model="aiDialogVisible" title="AI 顺延 / 重排建议" width="520px">
      <div class="ai-summary">{{ aiSuggest?.summary }}</div>
      <div v-if="!aiSuggest?.items.length" class="empty-tip">暂无待处理的建议任务</div>
      <div v-for="it in aiSuggest?.items || []" :key="it.task_id" class="ai-item">
        <div class="ai-item-head">
          <span class="ai-item-title">{{ it.title }}</span>
          <el-tag size="small" :type="statusType(it.status)" effect="light" round>{{ statusLabel(it.status) }}</el-tag>
        </div>
        <div class="ai-item-suggest">{{ it.suggest }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Calendar, WarningFilled } from '@element-plus/icons-vue'
import {
  getGoals, createGoal, updateGoal, deleteGoal,
  getPlans, createPlan, updatePlan, deletePlan,
  getTasks, createTask, updateTask, deleteTask,
  createCheckin, getStreak, getToday,
  getPlanReminders, getAISuggest, type GrowthGoal, type StudyPlan, type PlanTask,
  type TodayTask, type Streak, type AISuggest,
} from '@/api/plan'

// ---------- 状态 ----------
const plans = ref<StudyPlan[]>([])
const goals = ref<GrowthGoal[]>([])
const tasksByPlan = ref<Record<number, PlanTask[]>>({})
const todayTasks = ref<TodayTask[]>([])
const streak = ref<Streak>({ current: 0, longest: 0, today_checked: false, days: [] })
const reminderList = ref<string[]>([])
const expandedPlan = ref<number | null>(null)
const totalMinutes = ref(0)

const planStatus = ref('active')
const planFilters = [
  { label: '进行中', value: 'active' },
  { label: '已完成', value: 'completed' },
  { label: '已逾期', value: 'expired' },
  { label: '全部', value: 'all' },
]
const planStatusLabel = computed(() => planFilters.find(f => f.value === planStatus.value)?.label || '')

// ---------- 弹窗 ----------
const planDialogVisible = ref(false)
const savingPlan = ref(false)
const planForm = reactive<any>({ id: null, title: '', objective: '', stage: '', start_date: '', end_date: null, goal_id: null })

const taskDialogVisible = ref(false)
const savingTask = ref(false)
const taskForm = reactive<any>({ id: null, plan_id: null, title: '', description: '', due_date: null, priority: 'medium' })

const checkinDialogVisible = ref(false)
const savingCheckin = ref(false)
const checkinTask = ref<PlanTask | null>(null)
const checkinForm = reactive({ minutes: 30, note: '' })

const goalDialogVisible = ref(false)
const savingGoal = ref(false)
const goalTypes = ['就业', '考研', '技能', '竞赛', '证书', '其他']
const goalForm = reactive<any>({ id: null, goal_type: '就业', title: '', target_date: null, note: '', progress: 0 })

const aiDialogVisible = ref(false)
const aiLoading = ref(false)
const aiSuggest = ref<AISuggest | null>(null)

// ---------- 数据加载 ----------
async function loadGoals() {
  goals.value = await getGoals()
}

async function loadPlans() {
  plans.value = await getPlans(planStatus.value === 'all' ? undefined : planStatus.value)
  // 默认展开第一个进行中的计划
  if (!expandedPlan.value && plans.value.length) {
    expandedPlan.value = plans.value[0].id
  }
}

async function loadTasks(planId: number) {
  tasksByPlan.value[planId] = await getTasks({ plan_id: planId })
}

async function loadToday() {
  streak.value = await getStreak()
  todayTasks.value = await getToday()
  const all = await getCheckins()
  totalMinutes.value = all.reduce((s, c) => s + (Number(c.minutes) || 0), 0)
}

async function getCheckins() {
  const { getCheckins: api } = await import('@/api/plan')
  return api()
}

async function loadReminders() {
  try {
    const res = await getPlanReminders()
    reminderList.value = res.triggered || []
  } catch { reminderList.value = [] }
}

async function refreshAll() {
  await Promise.all([loadGoals(), loadPlans(), loadToday(), loadReminders()])
  if (expandedPlan.value) await loadTasks(expandedPlan.value)
}

onMounted(refreshAll)
const checkinLoaded = ref(false)
async function refreshToday() {
  streak.value = await getStreak()
  todayTasks.value = await getToday()
  if (!checkinLoaded.value) {
    checkinLoaded.value = true
  }
}

// ---------- 计划 ----------
function toggleExpand(id: number) {
  expandedPlan.value = expandedPlan.value === id ? null : id
  if (expandedPlan.value) loadTasks(expandedPlan.value)
}

function openPlanDialog(p?: StudyPlan) {
  if (p) {
    Object.assign(planForm, {
      id: p.id, title: p.title, objective: p.objective || '', stage: p.stage || '',
      start_date: p.start_date, end_date: p.end_date, goal_id: p.goal_id,
    })
  } else {
    Object.assign(planForm, { id: null, title: '', objective: '', stage: '', start_date: new Date().toISOString().slice(0, 10), end_date: null, goal_id: null })
  }
  planDialogVisible.value = true
}

async function savePlan() {
  if (!planForm.title.trim()) { ElMessage.warning('请输入计划标题'); return }
  if (!planForm.start_date) { ElMessage.warning('请选择开始日期'); return }
  savingPlan.value = true
  try {
    const data = {
      title: planForm.title.trim(), objective: planForm.objective || null,
      stage: planForm.stage || null, start_date: planForm.start_date,
      end_date: planForm.end_date || null, goal_id: planForm.goal_id || null,
    }
    if (planForm.id) await updatePlan(planForm.id, data)
    else await createPlan(data)
    ElMessage.success(planForm.id ? '计划已更新' : '计划已创建')
    planDialogVisible.value = false
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingPlan.value = false }
}

async function handleDeletePlan(id: number) {
  try {
    await ElMessageBox.confirm('删除计划将同时删除其下所有任务与打卡记录，确认删除？', '删除确认', { type: 'warning' })
    await deletePlan(id)
    ElMessage.success('已删除')
    delete tasksByPlan.value[id]
    await loadPlans()
  } catch {}
}

function switchPlanStatus(v: string) {
  planStatus.value = v
  expandedPlan.value = null
  loadPlans()
}

// ---------- 任务 ----------
function openTaskDialog(planId: number, t?: PlanTask) {
  if (t) {
    Object.assign(taskForm, {
      id: t.id, plan_id: t.plan_id, title: t.title, description: t.description || '',
      due_date: t.due_date, priority: t.priority,
    })
  } else {
    Object.assign(taskForm, { id: null, plan_id: planId, title: '', description: '', due_date: null, priority: 'medium' })
  }
  taskDialogVisible.value = true
}

async function saveTask() {
  if (!taskForm.title.trim()) { ElMessage.warning('请输入任务标题'); return }
  savingTask.value = true
  try {
    const data = {
      title: taskForm.title.trim(), description: taskForm.description || null,
      due_date: taskForm.due_date || null, priority: taskForm.priority,
    }
    if (taskForm.id) await updateTask(taskForm.id, data)
    else await createTask({ ...data, plan_id: taskForm.plan_id })
    ElMessage.success(taskForm.id ? '任务已更新' : '任务已添加')
    taskDialogVisible.value = false
    await loadTasks(taskForm.plan_id)
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingTask.value = false }
}

async function setTaskStatus(t: PlanTask, status: string) {
  try {
    await updateTask(t.id, { status })
    ElMessage.success(statusLabel(status) + '成功')
    await loadTasks(t.plan_id)
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function handleDeleteTask(id: number) {
  try {
    await ElMessageBox.confirm('确认删除该任务？', '删除确认', { type: 'warning' })
    await deleteTask(id)
    // 从当前展开计划刷新
    if (expandedPlan.value) await loadTasks(expandedPlan.value)
    await loadPlans()
  } catch {}
}

// ---------- 打卡 ----------
async function openCheckinDialog(t: PlanTask) {
  checkinTask.value = t
  checkinForm.minutes = 30
  checkinForm.note = ''
  checkinDialogVisible.value = true
}

async function saveCheckin() {
  if (!checkinTask.value) return
  savingCheckin.value = true
  try {
    await createCheckin({
      plan_id: checkinTask.value.plan_id,
      task_id: checkinTask.value.id,
      minutes: checkinForm.minutes || 30,
      note: checkinForm.note || null,
    })
    ElMessage.success('打卡成功，继续保持！')
    checkinDialogVisible.value = false
    await refreshToday()
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '打卡失败') }
  finally { savingCheckin.value = false }
}

async function handleCheckinFromToday(t: TodayTask) {
  if (t.checked_today) return
  if (!t.task_id) return
  try {
    await createCheckin({ plan_id: t.plan_id, task_id: t.task_id, minutes: 30 })
    ElMessage.success('打卡成功')
    await refreshToday()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '打卡失败') }
}

// ---------- 目标 ----------
function openGoalDialog(g?: GrowthGoal) {
  if (g) {
    Object.assign(goalForm, { id: g.id, goal_type: g.goal_type, title: g.title, target_date: g.target_date, note: g.note || '', progress: g.progress || 0 })
  } else {
    Object.assign(goalForm, { id: null, goal_type: '就业', title: '', target_date: null, note: '', progress: 0 })
  }
  goalDialogVisible.value = true
}

async function saveGoal() {
  if (!goalForm.title.trim()) { ElMessage.warning('请输入目标描述'); return }
  savingGoal.value = true
  try {
    const data = {
      goal_type: goalForm.goal_type, title: goalForm.title.trim(),
      target_date: goalForm.target_date || null, note: goalForm.note || null,
      progress: goalForm.progress || 0,
    }
    if (goalForm.id) await updateGoal(goalForm.id, data)
    else await createGoal(data)
    ElMessage.success(goalForm.id ? '目标已更新' : '目标已创建')
    goalDialogVisible.value = false
    await loadGoals()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingGoal.value = false }
}

async function handleDeleteGoal(g: GrowthGoal) {
  try {
    await ElMessageBox.confirm(`确认删除目标「${g.title}」？（关联计划将解除绑定）`, '删除确认', { type: 'warning' })
    await deleteGoal(g.id)
    ElMessage.success('已删除')
    await loadGoals()
    await loadPlans()
  } catch {}
}

// ---------- AI 建议 ----------
async function runAISuggest(planId?: number) {
  aiLoading.value = true
  try {
    aiSuggest.value = await getAISuggest(planId)
    aiDialogVisible.value = true
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || 'AI 建议生成失败') }
  finally { aiLoading.value = false }
}

// ---------- 展示辅助 ----------
function progressColor(rate: number) {
  if (rate >= 100) return '#67c23a'
  if (rate >= 60) return '#409eff'
  return '#e6a23c'
}

function priorityType(p: string) {
  return { high: 'danger', medium: 'warning', low: 'info' }[p] || 'info'
}
function priorityLabel(p: string) {
  return { high: '高优先级', medium: '中优先级', low: '低优先级' }[p] || p
}
function statusType(s: string) {
  return { todo: 'info', doing: 'warning', done: 'success' }[s] || 'info'
}
function statusLabel(s: string) {
  return { todo: '待办', doing: '进行中', done: '已完成' }[s] || s
}
function isOverdue(t: PlanTask) {
  return t.status !== 'done' && !!t.due_date && t.due_date < new Date().toISOString().slice(0, 10)
}
</script>

<style scoped>
.plan-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 16px 24px;
  background: #f8f9fc;
  min-height: 100%;
}
.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.plan-title { margin: 0; font-size: 20px; font-weight: 700; color: #1a1a2e; }
.plan-sub { margin: 4px 0 0; font-size: 12px; color: #999999; }

.card {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 14px;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.head-bar { width: 3px; height: 14px; background: #409eff; border-radius: 2px; }
.head-title { font-size: 15px; font-weight: 600; color: #1a1a2e; flex: 1; }

.streak-row {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 6px 0 10px;
}
.streak-item { text-align: center; }
.streak-num { font-size: 22px; font-weight: 700; color: #409eff; }
.streak-label { font-size: 12px; color: #999999; margin-top: 2px; }
.streak-divider { width: 1px; height: 32px; background: rgba(0,0,0,0.06); }

.reminder-box {
  background: #fffbf0;
  border: 1px solid #ffe8c2;
  border-radius: 8px;
  padding: 8px 12px;
}
.reminder-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 3px 0;
  font-size: 12px;
  color: #b88230;
  line-height: 1.5;
}
.reminder-text { flex: 1; }

.today-task {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.today-task:last-child { border-bottom: none; }
.today-task-info { flex: 1; }
.today-task-title { font-size: 14px; color: #1a1a2e; font-weight: 500; }
.task-done { text-decoration: line-through; color: #999999; }
.today-task-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.meta-plan { font-size: 12px; color: #999999; }
.meta-tag { margin: 0; }
.meta-date { font-size: 12px; color: #999999; display: inline-flex; align-items: center; gap: 4px; }
.meta-overdue { color: #f56c6c; }

.plan-filter { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.filter-tag { cursor: pointer; }

.plan-card {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafbfe;
}
.plan-card-expanded { border-color: rgba(64,158,255,0.4); background: #fff; }
.plan-card-head { display: flex; align-items: flex-start; justify-content: space-between; cursor: pointer; }
.plan-card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.plan-card-meta { display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.plan-card-right { display: flex; align-items: center; gap: 8px; }
.plan-rate { font-size: 16px; font-weight: 700; color: #409eff; }
.expand-icon { color: #999999; transition: transform 0.25s; }
.expand-icon.rotated { transform: rotate(180deg); }
.plan-progress { margin: 10px 0 6px; }
.plan-card-stats { display: flex; gap: 16px; font-size: 12px; color: #666666; }
.stat b { color: #1a1a2e; }
.stat-warn b { color: #f56c6c; }

.plan-detail { border-top: 1px dashed rgba(0,0,0,0.08); margin-top: 10px; padding-top: 10px; }
.plan-objective { font-size: 13px; color: #666666; line-height: 1.6; background: #f5f7fa; border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; }
.detail-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }

.task-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.04); }
.task-item:last-child { border-bottom: none; }
.task-item-main { flex: 1; min-width: 0; }
.task-title-row { display: flex; align-items: center; gap: 8px; }
.task-title { font-size: 14px; color: #1a1a2e; font-weight: 500; }
.task-desc { font-size: 12px; color: #666666; margin-top: 4px; line-height: 1.5; }
.task-meta { display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.task-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; flex-shrink: 0; }

.goal-card {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
}
.goal-head { display: flex; align-items: center; gap: 8px; }
.goal-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.goal-meta { display: flex; gap: 12px; margin: 8px 0; }
.goal-progress { display: flex; align-items: center; gap: 10px; }
.goal-progress-label { font-size: 12px; color: #999999; flex-shrink: 0; }
.goal-progress-bar { flex: 1; }

.empty-tip { text-align: center; color: #999999; font-size: 13px; padding: 16px 0; }
.checkin-task-title { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 12px; }
.checkin-unit { margin-left: 8px; font-size: 12px; color: #999999; }
.ai-summary { font-size: 14px; color: #1a1a2e; line-height: 1.7; background: #f0f7ff; border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; }
.ai-item { border: 1px solid rgba(0,0,0,0.06); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.ai-item-head { display: flex; align-items: center; gap: 8px; }
.ai-item-title { font-size: 14px; font-weight: 500; color: #1a1a2e; flex: 1; }
.ai-item-suggest { font-size: 13px; color: #666666; margin-top: 6px; line-height: 1.6; }
</style>