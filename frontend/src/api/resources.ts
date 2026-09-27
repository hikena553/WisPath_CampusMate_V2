import request from '@/utils/request'

export interface ResourceItem {
  item_type: string
  item_id: number
  title: string
  category: string | null
  summary: string | null
  link: string | null
  source: string | null
  extra: Record<string, any>
}

export interface RecommendItem extends ResourceItem {
  reason: string
}

export function getResourceItems(params?: { category?: string; q?: string; page?: number; page_size?: number }) {
  return request.get<ResourceItem[]>('/resources/items', { params })
}

export function getRecommend(limit = 6) {
  return request.get<RecommendItem[]>('/resources/recommend', { params: { limit } })
}

export interface Favorite {
  id: number
  item_type: string
  item_id: number
  title: string
  category: string | null
  summary: string | null
  link: string | null
  created_at: string | null
}

export function getFavorites() {
  return request.get<Favorite[]>('/resources/favorites')
}

export function addFavorite(data: { item_type: string; item_id: number; title: string; category?: string | null; summary?: string | null; link?: string | null }) {
  return request.post<Favorite>('/resources/favorites', data)
}

export function removeFavorite(id: number) {
  return request.delete(`/resources/favorites/${id}`)
}

// ---------- 外部资讯中心（论文/开源榜/智能体榜/权威要闻） ----------

export type FeedSourceType = 'papers' | 'agents' | 'opensource' | 'news' | 'ai_news' | 'rankings' | 'cn_ai'

export interface FeedItem {
  id: number
  source_type: FeedSourceType
  feed_key: string
  title: string
  summary: string | null
  link: string
  author: string | null
  source_name: string | null
  is_highlight: boolean
  meta: Record<string, any>
  published_at: string | null
}

export function getFeeds(params: { source_type: FeedSourceType | 'all'; limit?: number; q?: string }) {
  return request.get<FeedItem[]>('/feeds', { params })
}

export function refreshFeeds(sourceType: FeedSourceType | 'all' = 'all') {
  return request.post<{ sources: Record<string, { fetched: number; inserted: number }> }>(
    `/feeds/refresh?source_type=${sourceType}`,
  )
}

// ---------- 订阅源管理（动态源） ----------

export interface FeedSource {
  id: number
  name: string
  kind: 'rss' | 'html' | 'arxiv' | 'github' | 'gitee' | 'lmarena'
  source_type: FeedSourceType
  url: string
  query: string | null
  base_url: string | null
  filter_kw: string[]
  date_only: boolean
  per_page: number
  is_builtin: boolean
  enabled: boolean
  sort_order: number
}

export function getFeedSources(sourceType?: FeedSourceType | 'all') {
  return request.get<FeedSource[]>('/feeds/sources', { params: { source_type: sourceType } })
}

export function createFeedSource(body: Partial<FeedSource>) {
  return request.post<FeedSource>('/feeds/sources', body)
}

export function updateFeedSource(id: number, body: Partial<FeedSource>) {
  return request.patch<FeedSource>(`/feeds/sources/${id}`, body)
}

export function deleteFeedSource(id: number) {
  return request.delete(`/feeds/sources/${id}`)
}