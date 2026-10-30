/**
 * 退出登录统一入口。
 * 各退出入口（个人中心、布局下拉、改密页）都走这里：先弹二次确认，确认后再清理
 * 登录态并回到登录页，保证提醒文案与退出行为一致。
 * 弹窗外观由 styles/theme.css 的 `.logout-confirm` 定制（不使用 MessageBox 默认样式）。
 */
import { h } from 'vue'
import { ElMessageBox } from 'element-plus'
import { SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { markLoggingOut, markForcedLogout } from '@/utils/token'

/** 弹窗内容：图标徽章 + 标题 + 说明。每次调用重新创建 VNode，避免复用同一实例 */
function renderContent() {
  return h('div', { class: 'logout-confirm__body' }, [
    h('span', { class: 'logout-confirm__icon' }, [h(SwitchButton)]),
    h('p', { class: 'logout-confirm__title' }, '确定退出登录吗？'),
    h('p', { class: 'logout-confirm__desc' }, '退出后需重新登录才能继续使用当前账号。'),
  ])
}

export async function confirmLogout(): Promise<boolean> {
  try {
    await ElMessageBox.confirm(renderContent(), {
      // title 置为 undefined：隐藏 MessageBox 默认标题栏（含右上角关闭按钮），
      // 标题改由内容区自绘，避免出现「空标题 + ×」的潦草观感
      title: undefined,
      customClass: 'logout-confirm',
      showClose: false,
      cancelButtonText: '取消',
      confirmButtonText: '退出登录',
      cancelButtonClass: 'logout-confirm__btn logout-confirm__btn--cancel',
      confirmButtonClass: 'logout-confirm__btn logout-confirm__btn--confirm',
    })
  } catch {
    // 取消 / 关闭：保持当前登录态不变
    return false
  }
  // 必须先等服务端撤销 Cookie 并清理本地登录态，再做「整页跳转」：
  // SPA 内跳 /login 时守卫可能用残留 Cookie 探活成功把用户弹回角色首页，
  // 而整页跳转等价于用户手动刷新，能彻底丢弃残留的页面与守卫状态，
  // 这正是「必须手动刷新才是真退出」的痛点所在。
  markLoggingOut(true)
  try {
    await useAuthStore().logout()
  } finally {
    // 无论服务端撤销是否成功，都记录「用户已主动退出」：
    // 即使 Cookie 因网络问题残留，刷新后守卫也不会再把用户自动登回来
    markForcedLogout()
    window.location.replace('/login')
  }
  return true
}