import request from '@/utils/request'

// ---------- 长期目标 ----------
export interface GrowthGoal {
  id: number
  student_id: number
  goal_type: string
  title: string
  target_date: string | null
  status: string
  progress: number
  note: string | null
  created_at: string | null
  plan_count: number
}

export function getGoals() {
  return request.get<GrowthGoal[]>('/plan/goals')
}

export function createGoal(data: { goal_type: string; title: string; target_date?: string | null; note?: string | null }) {
  return request.post<GrowthGoal>('/plan/goals', data)
}

export function updateGoal(id: number, data: Partial<GrowthGoal>) {
  return request.put<GrowthGoal>(`/plan/goals/${id}`, data)
}

export function deleteGoal(id: number) {
  return request.delete(`/plan/goals/${id}`)
}

// ---------- 学习计划 ----------
export interface StudyPlan {
  id: number
  student_id: number
  goal_id: number | null
  title: string
  objective: string | null
  stage: string | null
  start_date: string
  end_date: string | null
  status: string
  created_at: string | null
  task_total: number
  task_done: number
  done_rate: number
  overdue: number
  goal_title: string | null
  checkin_days: number
}

export function getPlans(status?: string) {
  return request.get<StudyPlan[]>('/plan/plans', { params: { status } })
}

export function createPlan(data: { title: string; objective?: string | null; stage?: string | null; start_date: string; end_date?: string | null; goal_id?: number | null }) {
  return request.post<StudyPlan>('/plan/plans', data)
}

export function updatePlan(id: number, data: Partial<StudyPlan>) {
  return request.put<StudyPlan>(`/plan/plans/${id}`, data)
}

export function deletePlan(id: number) {
  return request.delete(`/plan/plans/${id}`)
}

// ---------- 任务 ----------
export interface PlanTask {
  id: number
  plan_id: number
  title: string
  description: string | null
  due_date: string | null
  priority: string
  status: string
  order_index: number
  created_at: string | null
  plan_title: string | null
  checked_today?: boolean
}

export function getTasks(params?: { plan_id?: number; status?: string }) {
  return request.get<PlanTask[]>('/plan/tasks', { params })
}

export function createTask(data: { plan_id: number; title: string; description?: string | null; due_date?: string | null; priority?: string; order_index?: number }) {
  return request.post<PlanTask>('/plan/tasks', data)
}

export function updateTask(id: number, data: Partial<PlanTask>) {
  return request.put<PlanTask>(`/plan/tasks/${id}`, data)
}

export function deleteTask(id: number) {
  return request.delete(`/plan/tasks/${id}`)
}

// ---------- 打卡 ----------
export interface Checkin {
  id: number
  plan_id: number
  task_id: number | null
  check_date: string
  minutes: number
  note: string | null
  plan_title: string | null
}

export function createCheckin(data: { plan_id: number; task_id?: number | null; minutes?: number; note?: string | null }) {
  return request.post<Checkin>('/plan/checkin', data)
}

export function getCheckins() {
  return request.get<Checkin[]>('/plan/checkins')
}

export interface Streak {
  current: number
  longest: number
  today_checked: boolean
  days: string[]
}

export function getStreak() {
  return request.get<Streak>('/plan/streak')
}

// ---------- 今日任务 ----------
export interface TodayTask {
  task_id: number | null
  title: string
  due_date: string | null
  priority: string
  status: string
  plan_id: number
  plan_title: string
  checked_today: boolean
}

export function getToday() {
  return request.get<TodayTask[]>('/plan/today')
}

// ---------- 提醒与洞察 ----------
export interface PlanRemindersResult {
  triggered: string[]
  count: number
}

export function getPlanReminders() {
  return request.get<PlanRemindersResult>('/plan/reminders')
}

export interface PlanInsights {
  total_plans: number
  completed_plans: number
  active_plans: number
  expired_plans: number
  task_total: number
  task_done: number
  checkin_total: number
  minutes_total: number
  risk: string[]
}

export function getPlanInsights() {
  return request.get<PlanInsights>('/plan/insights')
}

// ---------- AI 顺延/重排建议 ----------
export interface AISuggestItem {
  task_id: number
  title: string
  due_date: string | null
  status: string
  suggest: string
}

export interface AISuggest {
  summary: string
  items: AISuggestItem[]
}

export function getAISuggest(plan_id?: number) {
  return request.post<AISuggest>('/plan/ai-suggest', null, { params: { plan_id } })
}