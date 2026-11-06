/**
 * 教师「我的计划」统一条目。
 *
 * 历史原因：计划卡片读的是 teacher_schedules（日程），待办页读的是 teacher_tasks（任务），
 * 同一件事在两处各建一份，用户感觉「计划与待办不重叠」。
 * 现在新增入口统一写入待办，计划视图把「待办 + 旧日程」合并成同一种条目展示，
 * 旧日程保留只读兼容，不再新增。
 */
import type { TaskPriority, TeacherTask } from '@/api/teacherTask'
import type { ScheduleItem, ScheduleUrgency } from '@/api/teacher'

export type PlanItemKind = 'task' | 'schedule'

export interface PlanItem {
  /** 跨表唯一键：t-12 / s-3 */
  key: string
  rawId: number
  kind: PlanItemKind
  /** YYYY-MM-DD */
  date: string
  content: string
  completed: boolean
  urgency: ScheduleUrgency
  priority: TaskPriority
}

/** 任务优先级 → 日程紧急度（计划卡片沿用原来的三色 chip 语言） */
export function priorityToUrgency(priority?: TaskPriority | null): ScheduleUrgency {
  if (priority === 'high') return 'urgent'
  if (priority === 'low') return 'normal'
  return 'important'
}

/** 日程紧急度 → 任务优先级（新增入口写入待办时使用） */
export function urgencyToPriority(urgency: ScheduleUrgency): TaskPriority {
  if (urgency === 'urgent') return 'high'
  if (urgency === 'normal') return 'low'
  return 'mid'
}

function dateOnly(value: string | null | undefined): string {
  return (value || '').slice(0, 10)
}

export function taskToPlanItem(task: TeacherTask): PlanItem | null {
  const date = dateOnly(task.due_at)
  if (!date) return null
  const priority = task.priority || 'mid'
  return {
    key: `t-${task.id}`,
    rawId: task.id,
    kind: 'task',
    date,
    content: task.title,
    completed: task.status === 'done',
    urgency: priorityToUrgency(priority),
    priority,
  }
}

export function scheduleToPlanItem(schedule: ScheduleItem): PlanItem {
  const urgency: ScheduleUrgency =
    schedule.urgency === 'urgent' || schedule.urgency === 'important' ? schedule.urgency : 'normal'
  return {
    key: `s-${schedule.id}`,
    rawId: schedule.id,
    kind: 'schedule',
    date: dateOnly(schedule.date),
    content: schedule.content,
    completed: !!schedule.completed,
    urgency,
    priority: urgencyToPriority(urgency),
  }
}

/** 合并待办与旧日程，按日期升序、同级内未完成在前 */
export function mergePlanItems(
  tasks: TeacherTask[],
  schedules: ScheduleItem[],
): PlanItem[] {
  const items: PlanItem[] = []
  for (const t of tasks) {
    const item = taskToPlanItem(t)
    if (item) items.push(item)
  }
  for (const s of schedules) items.push(scheduleToPlanItem(s))
  items.sort((a, b) => {
    if (a.date !== b.date) return a.date.localeCompare(b.date)
    if (a.completed !== b.completed) return a.completed ? 1 : -1
    return a.key.localeCompare(b.key)
  })
  return items
}

export function isPlanItemOverdue(item: PlanItem, today = new Date().toISOString().slice(0, 10)): boolean {
  return !item.completed && item.date < today
}