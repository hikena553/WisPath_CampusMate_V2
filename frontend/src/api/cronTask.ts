import request from '@/utils/request'

// 与后端 schemas/cron_task.py 的 CronTaskOut 对齐；
// last_run_at/next_run_at 为北京时间 ISO（带 +08:00），new Date 可直接解析
export interface CronTaskItem {
  id: number
  name: string
  prompt: string
  schedule_kind: 'daily' | 'weekly' | 'interval'
  schedule_text: string
  hour: number | null
  minute: number | null
  weekday: number | null
  interval_hours: number | null
  enabled: boolean
  conversation_id: number
  last_run_at: string | null
  next_run_at: string
}

export interface CronTaskCreatePayload {
  name: string
  prompt: string
  schedule_kind: 'daily' | 'weekly' | 'interval'
  hour?: number | null
  minute?: number | null
  weekday?: number | null
  interval_hours?: number | null
}

export function listCronTasks() {
  return request.get<CronTaskItem[]>('/cron-tasks')
}

/** 移动端「+」表单新建；规则与聊天创建一致（周期校验、每人上限、自动建专属会话） */
export function createCronTask(data: CronTaskCreatePayload) {
  return request.post<CronTaskItem>('/cron-tasks', data)
}

export function updateCronTask(id: number, data: { name?: string; enabled?: boolean }) {
  return request.put<CronTaskItem>(`/cron-tasks/${id}`, data)
}

export function deleteCronTask(id: number) {
  return request.delete(`/cron-tasks/${id}`)
}

export function runCronTaskNow(id: number) {
  return request.post(`/cron-tasks/${id}/run-now`)
}
