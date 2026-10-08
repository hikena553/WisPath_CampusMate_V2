import request from '@/utils/request'

/** 成长档案条目类型：工作案例 / 荣誉表彰 / 培训研修 / 工作研究成果 */
export type PortfolioItemType = 'case' | 'honor' | 'training' | 'research'

/** 可见性：仅自己 / 公开展示 */
export type PortfolioVisibility = 'private' | 'public'

export interface EvidenceItem {
  name?: string
  url: string
}

export interface PortfolioItem {
  id: number
  teacher_id: number
  item_type: PortfolioItemType
  title: string
  evidence: EvidenceItem[]
  reflection: string | null
  occurred_on: string | null
  visibility: PortfolioVisibility
  reviewer_id: number | null
  review_comment: string | null
  created_at: string
  updated_at: string
}

export interface PortfolioItemPayload {
  item_type?: PortfolioItemType
  title: string
  evidence?: EvidenceItem[]
  reflection?: string | null
  occurred_on?: string | null
  visibility?: PortfolioVisibility
}

export interface PortfolioTypeStat {
  type: PortfolioItemType
  label: string
  count: number
}

export interface PortfolioReport {
  teacher_id: number
  teacher_name: string
  total: number
  by_type: PortfolioTypeStat[]
  items: PortfolioItem[]
  generated_at: string
}

/** 类型中文标签 */
export const PORTFOLIO_TYPE_LABEL: Record<PortfolioItemType, string> = {
  case: '工作案例',
  honor: '荣誉表彰',
  training: '培训研修',
  research: '工作研究成果',
}

/** 类型主题色（用于徽标 / 时间线节点） */
export const PORTFOLIO_TYPE_COLOR: Record<PortfolioItemType, string> = {
  case: '#2563eb',
  honor: '#b54708',
  training: '#6941c6',
  research: '#079455',
}

export function getPortfolioItems(params?: { item_type?: PortfolioItemType; limit?: number; offset?: number }) {
  return request.get<PortfolioItem[]>('/teacher-portfolio', { params })
}

export function createPortfolioItem(data: PortfolioItemPayload) {
  return request.post<PortfolioItem>('/teacher-portfolio', data)
}

export function updatePortfolioItem(id: number, data: Partial<PortfolioItemPayload>) {
  return request.patch<PortfolioItem>(`/teacher-portfolio/${id}`, data)
}

export function deletePortfolioItem(id: number) {
  return request.delete(`/teacher-portfolio/${id}`)
}

export function getPortfolioReport() {
  return request.get<PortfolioReport>('/teacher-portfolio/report')
}