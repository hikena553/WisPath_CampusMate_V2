import request from '@/utils/request'

export type SurveyTargetType = 'peer' | 'student'
export type SurveyStatus = 'draft' | 'open' | 'closed'

export interface SurveyQuestion {
  key: string
  label: string
  max?: number
}

export interface PeerSurvey {
  id: number
  title: string
  target_type: SurveyTargetType
  period: string | null
  questions: SurveyQuestion[]
  status: SurveyStatus
  created_by: number
  created_at: string
  response_count: number
  my_submitted: boolean
}

export interface QuestionStat {
  key: string
  label: string
  average: number | null
  distribution: Record<string, number>
  response_count: number
}

export interface PeerSurveyResult {
  survey_id: number
  title: string
  target_teacher_id: number | null
  response_count: number
  min_sample: number
  enough_sample: boolean
  overall_average: number | null
  questions: QuestionStat[]
  suggestions: string[]
}

export interface PeerSurveyMine extends PeerSurveyResult {
  period: string | null
  target_type: SurveyTargetType
}

export const SURVEY_STATUS_LABEL: Record<SurveyStatus, string> = {
  draft: '草稿',
  open: '进行中',
  closed: '已结束',
}

export const SURVEY_TARGET_LABEL: Record<SurveyTargetType, string> = {
  peer: '辅导员互评',
  student: '学生评辅导员',
}

/** 默认问卷模板：四道通用评分题 */
export const DEFAULT_SURVEY_QUESTIONS: SurveyQuestion[] = [
  { key: 'care', label: '他/她在关心学生方面做得如何？', max: 5 },
  { key: 'fair', label: '他/她在处事公正方面做得如何？', max: 5 },
  { key: 'comm', label: '他/她与学生、同事的沟通是否及时？', max: 5 },
  { key: 'duty', label: '他/她对工作是否认真负责？', max: 5 },
]

export interface SurveyAIDraft {
  title: string
  questions: SurveyQuestion[]
  /** ai=大模型生成；rule=未配置模型时的本地规则兜底 */
  source: 'ai' | 'rule'
}

/** AI 辅助发起：一句场景描述 → 推荐问卷标题与评价维度 */
export function generateSurveyDraft(data: { scene: string; target_type: SurveyTargetType }) {
  return request.post<SurveyAIDraft>('/peer-surveys/ai-draft', data)
}

export function listSurveys() {
  return request.get<PeerSurvey[]>('/peer-surveys')
}

export function createSurvey(data: {
  title: string
  target_type?: SurveyTargetType
  period?: string | null
  questions?: SurveyQuestion[]
  status?: SurveyStatus
}) {
  return request.post<PeerSurvey>('/peer-surveys', data)
}

export function updateSurveyStatus(id: number, status: SurveyStatus) {
  return request.patch<PeerSurvey>(`/peer-surveys/${id}/status`, { status })
}

export function submitSurvey(
  id: number,
  data: { target_teacher_id: number; scores: Record<string, number>; suggestion?: string | null }
) {
  return request.post<{ message: string }>(`/peer-surveys/${id}/responses`, data)
}

export function getSurveyResult(id: number, targetTeacherId?: number) {
  const params = targetTeacherId ? { target_teacher_id: targetTeacherId } : {}
  return request.get<PeerSurveyResult>(`/peer-surveys/${id}/result`, { params })
}

export function getMySurveyResults() {
  return request.get<PeerSurveyMine[]>('/peer-surveys/mine')
}