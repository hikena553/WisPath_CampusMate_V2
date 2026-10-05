import request from '@/utils/request'

export type CareEventType = 'birthday' | 'difficulty' | 'academic' | 'other'
export type HomeVisitMethod = 'home' | 'phone' | 'video' | 'school' | 'other'
export type PraiseType = 'praise' | 'badge'

export interface CareEvent {
  id: number
  teacher_id: number
  student_id: number | null
  student_name: string
  event_type: CareEventType
  event_date: string
  title: string
  note: string | null
  auto_generated: boolean
  created_at: string
}

export interface HomeVisit {
  id: number
  student_id: number
  student_name: string
  teacher_id: number
  visit_date: string
  method: HomeVisitMethod
  content: string
  follow_up: string | null
  created_at: string
}

export interface Praise {
  id: number
  student_id: number
  student_name: string
  teacher_id: number
  praise_type: PraiseType
  badge_name: string | null
  reason: string
  occurred_on: string | null
  created_at: string
}

export interface CareCenterOverview {
  month: string
  event_count: number
  visit_count: number
  praise_count: number
  pending_events: number
}

export const CARE_EVENT_LABEL: Record<CareEventType, string> = {
  birthday: '生日关怀',
  difficulty: '困难学生',
  academic: '学业预警',
  other: '其他事项',
}

export const CARE_EVENT_COLOR: Record<CareEventType, string> = {
  birthday: '#ec4899',
  difficulty: '#f79009',
  academic: '#d92d20',
  other: '#667085',
}

export const VISIT_METHOD_LABEL: Record<HomeVisitMethod, string> = {
  home: '实地家访',
  phone: '电话沟通',
  video: '视频沟通',
  school: '校内约谈',
  other: '其他方式',
}

export const PRAISE_TYPE_LABEL: Record<PraiseType, string> = {
  praise: '表扬',
  badge: '徽章',
}

export function getCareOverview(month?: string) {
  return request.get<CareCenterOverview>('/care-center/overview', { params: { month } })
}

export function getCareEvents(month?: string) {
  return request.get<CareEvent[]>('/care-center/events', { params: { month } })
}

export function createCareEvent(data: {
  event_type?: CareEventType
  event_date: string
  title: string
  note?: string | null
  student_id?: number | null
}) {
  return request.post<CareEvent>('/care-center/events', data)
}

export function generateCareEvents(month?: string) {
  return request.post<{ created: number; message: string }>('/care-center/events/generate', null, {
    params: { month },
  })
}

export function deleteCareEvent(id: number) {
  return request.delete(`/care-center/events/${id}`)
}

export function getHomeVisits(studentId?: number) {
  return request.get<HomeVisit[]>('/care-center/visits', { params: { student_id: studentId } })
}

export function createHomeVisit(data: {
  student_id: number
  visit_date: string
  method?: HomeVisitMethod
  content: string
  follow_up?: string | null
}) {
  return request.post<HomeVisit>('/care-center/visits', data)
}

export function deleteHomeVisit(id: number) {
  return request.delete(`/care-center/visits/${id}`)
}

export function getPraises(studentId?: number) {
  return request.get<Praise[]>('/care-center/praises', { params: { student_id: studentId } })
}

export function createPraise(data: {
  student_id: number
  praise_type?: PraiseType
  badge_name?: string | null
  reason: string
  occurred_on?: string | null
}) {
  return request.post<Praise>('/care-center/praises', data)
}

export function deletePraise(id: number) {
  return request.delete(`/care-center/praises/${id}`)
}