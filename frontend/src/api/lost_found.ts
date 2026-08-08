import request from '@/utils/request'
import type { LostFoundItem, LostFoundComment } from '@/types'

export function getLostFoundItems(params?: { type?: string; status?: string }) {
  return request.get<LostFoundItem[]>('/lost-found/items', { params })
}

export function getLostFoundItem(id: number) {
  return request.get<LostFoundItem>(`/lost-found/items/${id}`)
}

export function createLostFoundItem(data: {
  type: string
  title: string
  description?: string
  location?: string
  contact?: string
  image_url?: string
}) {
  return request.post<LostFoundItem>('/lost-found/items', data)
}

export function updateLostFoundStatus(id: number, status: string) {
  return request.put<LostFoundItem>(`/lost-found/items/${id}/status`, { status })
}

export function deleteLostFoundItem(id: number) {
  return request.delete(`/lost-found/items/${id}`)
}

export function createLostFoundComment(id: number, content: string) {
  return request.post<LostFoundComment>(`/lost-found/items/${id}/comments`, { content })
}
