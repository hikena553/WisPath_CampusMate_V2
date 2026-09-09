import request from '@/utils/request'
import type { CampusScenery, Announcement, ImpressionItem } from '@/types'

export function getSceneries(area?: string) {
  return request.get<CampusScenery[]>('/campus/sceneries', { params: { area } })
}

export function getAnnouncements() {
  return request.get<Announcement[]>('/campus/announcements')
}

export function getGallery() {
  return request.get<GalleryImage[]>('/campus/gallery')
}

export function getImpression() {
  return request.get<ImpressionItem[]>('/campus/impression')
}

export interface GalleryImage {
  title: string
  image_url: string
  campus: string
}
