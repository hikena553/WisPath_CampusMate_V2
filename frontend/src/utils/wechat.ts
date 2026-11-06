/**
 * 微信内置浏览器 / 平台探测。
 *
 * 微信内置浏览器（X5 / XWeb）不支持直接下载安装 APK，
 * 下载页需要引导用户点右上角「···」→「在浏览器打开」。
 */
export function isWeChatBrowser(): boolean {
  if (typeof navigator === 'undefined') return false
  return /MicroMessenger/i.test(navigator.userAgent)
}

export function isIOS(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iPhone|iPad|iPod/i.test(navigator.userAgent)
}

export function isAndroid(): boolean {
  if (typeof navigator === 'undefined') return false
  return /Android/i.test(navigator.userAgent)
}
