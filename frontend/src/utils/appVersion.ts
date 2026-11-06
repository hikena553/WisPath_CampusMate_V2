import { computed, ref } from 'vue'
import { Capacitor } from '@capacitor/core'
import { App as CapacitorApp } from '@capacitor/app'

/**
 * 软件版本号：只有一个来源，不再手写。
 *
 * - 网页端：构建时由 vite.config.ts 从 package.json 注入 `__APP_VERSION__`；
 * - Android 壳：运行时读安装包的真实 versionName / versionCode（`App.getInfo()`），
 *   这样即使线上网页已经更新、手机里还是旧 APK，显示的也是「当前装的这一版」。
 */
declare const __APP_VERSION__: string
const BUILD_VERSION =
  typeof __APP_VERSION__ === 'string' && __APP_VERSION__ ? __APP_VERSION__ : '0.0.0'

export const appVersion = ref(`v${BUILD_VERSION}`)
/** 原生壳的构建号（Android versionCode）；网页端为空 */
export const appBuild = ref('')

/** 展示文案：网页端 v1.8.0；壳内 v1.8（9） */
export const appVersionLabel = computed(() =>
  appBuild.value ? `${appVersion.value}（${appBuild.value}）` : appVersion.value,
)

let synced = false

/** 壳内对齐安装包版本；只执行一次，失败保持构建时版本 */
export async function syncAppVersion() {
  if (synced || !Capacitor.isNativePlatform()) return
  synced = true
  try {
    const info = await CapacitorApp.getInfo()
    if (info.version) appVersion.value = `v${info.version}`
    appBuild.value = info.build || ''
  } catch {
    /* 读不到就用构建时版本，不影响页面 */
  }
}
