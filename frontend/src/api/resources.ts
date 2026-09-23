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