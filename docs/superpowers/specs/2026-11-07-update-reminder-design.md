# 版本更新提醒窗口 设计

日期:2026-11-07 · 状态:已确认(用户拍板:网页 + 壳内 APK 更新提示)

## 背景

- 版本号唯一来源 `frontend/package.json`(当前 1.8.0),构建时经 `vite.config.ts` 注入 `__APP_VERSION__`;Android 壳运行时读安装包真实 versionName/versionCode(`src/utils/appVersion.ts`)。
- Android 壳 WebView 直接加载**线上站点**(`capacitor.config.ts` 的 `server.url`,打包时注入)——线上网页更新后壳内自动生效,但安装包版本停在旧版。
- APK 发布走腾讯云 COS:`https://www.mianxiaocheng.cn/download/mian02.apk` 为固定「最新版」地址(nginx 302,见 `deploy/COS对象存储接入说明.md`)。

## 目标

1. **网页端刷新提醒**:部署新构建后,停留在旧页面的用户看到「发现新版本 vX.Y.Z」,一键刷新。
2. **壳内 APK 更新提示**:线上版本 versionName > 安装包 versionName 时,提示两个版本号,一键跳系统浏览器下载新 APK。

## 非目标

- 不做强制更新拦截;不做后台版本公告;dev 模式不启用检测。

## 方案(构建时产出 version.json + 运行时比对,不涉及后端)

### 1. `vite.config.ts` — `versionManifestPlugin()`

- 构建:`generateBundle` 向产物根 emit `version.json` = `{ "version": APP_VERSION, "buildTime": <构建时刻 ISO> }`;同一 `buildTime` 经 `define` 注入 `__APP_BUILD_TIME__`(运行页面自证构建时刻的依据)。
- dev:`configureServer` 中间件返回同结构(`buildTime: "dev"`),保证路径不 404。

### 2. `src/composables/useUpdateCheck.ts`(新增)

- 检测时机:启动后 8s 首查;`visibilitychange` 回前台且距上次 ≥5 分钟复查。fetch `BASE_URL + version.json?t=<ts>`、`cache: 'no-store'`,失败静默(老构建无此文件 → 永不提示)。
- 纯函数 `resolveUpdate(manifest, running, installedVersion)`(可单测),优先级:
  1. 壳内且线上 versionName **大于** 安装包 → `apk` 态(隐含刷新,不再叠加刷新提示);
  2. `manifest.buildTime !== __APP_BUILD_TIME__` → `web` 态;
  3. 其余 → null。
- `applyUpdate()`:`web` → `location.reload()`;`apk` → `App.openUrl(COS 下载地址)`。
- `import.meta.env.DEV` 时整体跳过。壳内比较前先 `await syncAppVersion()`(幂等)对齐安装包版本。

### 3. `src/components/common/UpdateReminder.vue`(新增)+ `App.vue` 挂载

- 形态完全复刻 `PasswordChangeReminder` 顶部悬浮细条:单行文案 + 行内动作 + 关闭;手机端位于页签栏上方。
- 12s 无操作自动收起;关闭与自动收起均按**版本指纹**(`version:buildTime`)记 sessionStorage——同一版本本次会话不再弹,**更新的版本会再次提醒**。
- 登录页 / 欢迎页 / 改密页不显示。
- 文案:apk 态「线上已是新版本 vX.Y.Z,你安装的还是 vA.B.C(9)」+「立即更新」;web 态「发现新版本 vX.Y.Z」+「立即刷新」。

## 错误处理

- `version.json` 不存在 / 解析失败 / 字段缺失:静默,不提醒。
- `buildTime` 缺失:仅壳内版本比较生效。

## 测试

- vitest(项目首个测试文件):`compareSemver` / `resolveUpdate` 纯函数(优先级、等于、缺字段、静默路径)。
- `npm run build` 零报错,且 `dist/version.json` 存在、内容与 package.json 版本一致。
