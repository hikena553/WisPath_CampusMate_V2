import request from '@/utils/request'

export type StudyMode = 'focus' | 'short_break' | 'long_break'

export interface StudySession {
  id: number
  mode: StudyMode
  task_title: string | null
  planned_minutes: number
  actual_minutes: number
  completed: boolean
  study_date: string
  start_time: string | null
  end_time: string | null
  created_at: string | null
}

export interface StudyDay {
  date: string
  focus_minutes: number
  session_count: number
}

export interface StudyToday {
  date: string
  focus_minutes: number
  session_count: number
}

export interface StudyOverview {
  today: StudyToday
  days: StudyDay[]
  sessions: StudySession[]
}

export function getStudyOverview(days = 30) {
  return request.get<StudyOverview>('/study-room/overview', { params: { days } })
}

export function createStudySession(data: {
  mode: StudyMode
  task_title?: string | null
  planned_minutes: number
  actual_minutes: number
  completed: boolean
  started_at?: string | null
  ended_at?: string | null
}) {
  return request.post<StudySession>('/study-room/sessions', data)
}
