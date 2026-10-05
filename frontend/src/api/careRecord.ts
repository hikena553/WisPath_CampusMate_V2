import request from '@/utils/request'

/** 侧写记录类型：关怀记录 / 谈心谈话 / 评语 */
export type CareRecordType = 'care' | 'talk' | 'comment'

export interface CareRecord {
  id: number
  student_id: number
  student_name: string
  teacher_id: number
  teacher_name: string
  record_type: CareRecordType
  content: string
  is_private: boolean
  task_id: number | null
  created_at: string
}

export interface CareRecordCreate {
  student_id: number
  record_type?: CareRecordType
  content: string
  is_private?: boolean
  task_id?: number
}

export interface WorkloadStats {
  care: number
  talk: number
  comment: number
  total: number
}

export function getCareRecords(params: {
  student_id?: number
  record_type?: CareRecordType
  limit?: number
  offset?: number
}) {
  return request.get<CareRecord[]>('/care-records', { params })
}

export function createCareRecord(data: CareRecordCreate) {
  return request.post<CareRecord>('/care-records', data)
}

export function updateCareRecord(
  id: number,
  data: { content?: string; is_private?: boolean }
) {
  return request.patch<CareRecord>(`/care-records/${id}`, data)
}

export function deleteCareRecord(id: number) {
  return request.delete(`/care-records/${id}`)
}

export function getWorkloadStats() {
  return request.get<WorkloadStats>('/care-records/workload')
}

/** 侧写类型中文标签 */
export const CARE_TYPE_LABEL: Record<CareRecordType, string> = {
  care: '关怀记录',
  talk: '谈心谈话',
  comment: '评语',
}
