/**
 * 游客访问受限功能时的统一登录引导。
 * 不使用弹窗：直接进入登录页，并在登录页顶部以单行提示说明「登录后可以做什么」。
 */
import router from '@/router'
import { setGuestMode } from './guest'

export async function promptLogin(feature = '使用该功能'): Promise<boolean> {
  setGuestMode(false)
  await router.push({ path: '/login', query: { reason: feature } })
  return true
}
