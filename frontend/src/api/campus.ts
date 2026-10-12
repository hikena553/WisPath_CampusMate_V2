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

/** 站内阅读器数据：文章正文或列表页链接清单 */
export interface CampusArticleLink {
  title: string
  url: string
  date: string | null
}

export interface CampusArticle {
  kind: 'article' | 'links'
  title: string
  date: string | null
  content_html: string | null
  links: CampusArticleLink[]
  source_url: string
}

/** 站内阅读：后端代理抓取校内页面并提取正文，避免跳出应用 */
export function readCampusArticle(url: string) {
  return request.get<CampusArticle>('/campus/reader', { params: { url } })
}

/**
 * 原页渲染地址：后端反代后的校内页面，供 iframe 嵌入（保留原版排版）。
 * 走同源 /api 代理是安全的：iframe 必须带 sandbox（不含 allow-same-origin），
 * 不透明源下学校页面的脚本拿不到应用的 localStorage / Cookie。
 */
export function campusEmbedUrl(url: string) {
  return `/api/campus/embed?url=${encodeURIComponent(url)}`
}

export interface GalleryImage {
  title: string
  image_url: string
  campus: string
}
