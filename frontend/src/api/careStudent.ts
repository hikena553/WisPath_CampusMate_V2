import request from '@/utils/request'
import type { FollowUpStatus, HomeVisitMethod, PraiseType } from './careCenter'

/** 学生端「我的关怀」概览计数 */
export interface MyCareSummary {
  praises: number
  visits: number
  records: number
}

export interface MyCarePraise {
  id: number
  praise_type: PraiseType
  badge_name: string | null
  reason: string
  occurred_on: string | null
  teacher_name: string
}

export interface MyCareRecord {
  id: number
  record_type: 'care' | 'talk' | 'comment'
  content: string
  created_at: string
  teacher_name: string
}

export interface MyCareVisit {
  id: number
  visit_date: string
  method: HomeVisitMethod
  content: string
  follow_up: string | null
  follow_up_status: FollowUpStatus
  teacher_name: string
}

export function getMyCareSummary() {
  return request.get<MyCareSummary>('/student/care/summary')
}

export function getMyCarePraises() {
  return request.get<MyCarePraise[]>('/student/care/praises')
}

export function getMyCareRecords() {
  return request.get<MyCareRecord[]>('/student/care/records')
}

export function getMyCareVisits() {
  return request.get<MyCareVisit[]>('/student/care/visits')
}