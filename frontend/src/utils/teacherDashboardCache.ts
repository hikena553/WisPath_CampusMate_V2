/**
 * 教师端首页数据预加载缓存
 * 布局挂载时预加载数据，页面组件直接读取缓存，消除切换时的加载等待
 */

import { getDashboardStats, getClassEvaluation, getClassStats } from '@/api/teacher'
import { getAlerts } from '@/api/crisis'
import { getPendingLeaves } from '@/api/leave'
import { getAnnouncements } from '@/api/campus'
import { getTeacherAnnouncements } from '@/api/announcement'
import { getTeacherSchedules, getOverdueSchedules } from '@/api/teacher'

interface CacheEntry<T> {
  data: T
  timestamp: number
}

const cache = new Map<string, CacheEntry<any>>()
const CACHE_TTL = 60_000 // 60秒缓存有效期

let prefetchPromise: Promise<void> | null = null

/**
 * 预加载教师端首页所有数据（并行请求）
 * 在 TeacherLayout 挂载时调用
 */
export function prefetchDashboardData(): void {
  if (prefetchPromise) return // 避免重复预加载

  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1

  prefetchPromise = Promise.all([
    getDashboardStats().then(d => setCache('dashboard-stats', d)),
    getAlerts(undefined).then(d => setCache('alerts', d)),
    getPendingLeaves().then(d => setCache('pending-leaves', d)),
    getAnnouncements().then(d => setCache('announcements', d)),
    getClassEvaluation().then(d => setCache('class-evaluation', d)),
    getClassStats().then(d => setCache('class-stats', d)),
    getTeacherAnnouncements().then(d => setCache('teacher-announcements', d)),
    getTeacherSchedules(year, month).then(d => setCache('teacher-schedules', d)),
    getOverdueSchedules().then(d => setCache('overdue-schedules', d)),
  ]).then(() => {}).catch(() => {}).finally(() => {
    prefetchPromise = null
  })
}

/**
 * 获取当前预加载的 Promise（如果有的话）
 * 用于页面组件等待预加载完成后再读取缓存
 */
export function getPrefetchPromise(): Promise<void> | null {
  return prefetchPromise
}

/**
 * 读取缓存数据（如果有效）
 */
export function getCachedData<T>(key: string): T | null {
  const entry = cache.get(key)
  if (!entry) return null
  if (Date.now() - entry.timestamp > CACHE_TTL) {
    cache.delete(key)
    return null
  }
  return entry.data as T
}

function setCache<T>(key: string, data: T): void {
  cache.set(key, { data, timestamp: Date.now() })
}
