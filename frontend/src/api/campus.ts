import request from '@/utils/request'
import type { CampusFigure, CampusScenery, Announcement } from '@/types'

export function getFigures(category?: string) {
  return request.get<CampusFigure[]>('/campus/figures', { params: { category } })
}

// 管理员增删改查
export function getAdminFigures(category?: string) {
  return request.get<CampusFigure[]>('/admin/figures', { params: { category } })
}

export function createFigure(data: Partial<CampusFigure>) {
  return request.post<CampusFigure>('/admin/figures', data)
}

export function updateFigure(id: number, data: Partial<CampusFigure>) {
  return request.put<CampusFigure>(`/admin/figures/${id}`, data)
}

export function deleteFigure(id: number) {
  return request.delete(`/admin/figures/${id}`)
}

export function getSceneries(area?: string) {
  return request.get<CampusScenery[]>('/campus/sceneries', { params: { area } })
}

export function getAnnouncements() {
  return request.get<Announcement[]>('/campus/announcements')
}

export function getGallery() {
  return request.get<GalleryImage[]>('/campus/gallery')
}

export interface GalleryImage {
  title: string
  image_url: string
  campus: string
}
