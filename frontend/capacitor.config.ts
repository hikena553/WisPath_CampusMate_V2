import type { CapacitorConfig } from '@capacitor/cli'

/**
 * Android 壳工程配置（Capacitor）。
 *
 * 站点地址在打包时注入（`CAPACITOR_SERVER_URL`，见 scripts/build-apk.mjs）：
 * WebView 直接加载线上站点，因此：
 * - 前端相对路径 `/api`、二维码、下载页全部与该域名同源，无需改动业务代码；
 * - 官网更新后无需重新发版，装一次 APK 即可一直用最新页面。
 *
 * 未注入地址时（例如 IDE 直接打开 android/ 工程）回落到本地 Web 资源，
 * 此时 `/api` 请求不可用，仅用于调试壳本身。
 */
const serverUrl = (process.env.CAPACITOR_SERVER_URL || '')
  .trim()
  .replace(/\/+$/, '')

const config: CapacitorConfig = {
  appId: 'com.mian02.campus',
  appName: '绵小城',
  webDir: 'dist',
  // 首次进入的启动背景，避免 WebView 白屏
  backgroundColor: '#ffffff',
  server: serverUrl
    ? {
        url: serverUrl,
        // 仅本地联调（http://192.168.x.x）允许明文，正式域名必须 https
        cleartext: serverUrl.startsWith('http://'),
        androidScheme: 'https',
      }
    : {
        androidScheme: 'https',
      },
  android: {
    // 线上站点一律 HTTPS，禁止 WebView 混入 HTTP 资源
    allowMixedContent: false,
  },
}

export default config
