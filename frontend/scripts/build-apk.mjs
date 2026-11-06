#!/usr/bin/env node
/**
 * 一键打包 Android 安装包（Capacitor 壳）。
 *
 * 用法（在 frontend 目录）：
 *   npm run apk -- --url https://你的域名        # 调试签名包，可直接安装
 *   npm run apk:release -- --url https://你的域名 # 正式签名包（需 keystore 环境变量）
 *
 * 也可用环境变量 CAPACITOR_SERVER_URL 代替 --url。
 *
 * 脚本做的事：构建 Web → 同步到 Android 工程 → Gradle 出包 →
 * 复制到 public/download/SmartCampus.apk 与 <项目根>/apk/download/mian02.apk
 * （官网下载页与 nginx /download/ 直接生效），最后自动发布到腾讯云 COS。
 * COS 公网对象为无扩展名 key（<prefix>/mian02-latest、<prefix>/releases/...，
 * Content-Type: application/octet-stream，Content-Disposition 仅用 filename*=UTF-8''SmartCampus.apk 让浏览器存成 SmartCampus.apk），
 * 因为 COS 默认域名禁止匿名分发 .apk 后缀 / APK 类型对象（GET 会 403 DownloadForbidden）。
 * 上传失败 / 未配置密钥只告警，不影响本地出包；--no-publish 或 COS_SKIP=1 可跳过上传。
 */
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const args = process.argv.slice(2)

function fail(message) {
  console.error(`\n✖ ${message}\n`)
  process.exit(1)
}

function getArg(name) {
  const index = args.indexOf(name)
  return index !== -1 ? args[index + 1] : undefined
}

function run(command, commandArgs, options = {}) {
  console.log(`▶ ${command} ${commandArgs.join(' ')}`)
  const result = spawnSync(command, commandArgs, {
    cwd: options.cwd || root,
    stdio: 'inherit',
    env: { ...process.env, ...options.env },
    shell: false,
  })
  if (result.error) fail(`无法执行 ${command}：${result.error.message}`)
  if (result.status !== 0) fail(`${command} 执行失败（退出码 ${result.status}）`)
}

// ---------- 1. 解析站点地址 ----------
const siteUrl = (getArg('--url') || process.env.CAPACITOR_SERVER_URL || '')
  .trim()
  .replace(/\/+$/, '')

if (!siteUrl) {
  fail(
    '缺少站点地址，无法生成安装包。\n' +
      '  用法：npm run apk -- --url https://你的域名\n' +
      '  或：  CAPACITOR_SERVER_URL=https://你的域名 npm run apk'
  )
}
if (!/^https?:\/\//i.test(siteUrl)) {
  fail(`站点地址必须带协议（https:// 或 http://），当前为：${siteUrl}`)
}
if (siteUrl.startsWith('http://')) {
  console.warn('⚠ 使用 HTTP 地址打包：仅适合本地联调，正式分发请改用 HTTPS 域名。')
}

const isRelease = args.includes('--release')
const skipBuild = args.includes('--skip-build')
const apkOutput = join(root, 'public', 'download', 'SmartCampus.apk')
const projectRoot = resolve(root, '..')
const publishedApk = join(projectRoot, 'apk', 'download', 'mian02.apk')
const publishScript = join(root, 'scripts', 'publish-apk.mjs')
const noPublish = args.includes('--no-publish')

// ---------- 2. 检查 Android SDK ----------
const androidDir = join(root, 'android')
if (!existsSync(androidDir)) fail('缺少 android/ 工程，请先执行：npx cap add android')

const localProperties = join(androidDir, 'local.properties')
if (!existsSync(localProperties)) {
  const sdkRoot = process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT
  if (!sdkRoot) {
    fail(
      '未找到 Android SDK。\n' +
        '  1) 安装 Android Studio 并完成首次启动（会自动下载 SDK）；\n' +
        '  2) 设置环境变量 ANDROID_HOME 指向 SDK 目录（通常在 %LOCALAPPDATA%\\Android\\Sdk）；\n' +
        '  3) 或直接用 Android Studio 打开 frontend/android 工程，会自动生成 local.properties。'
    )
  }
  // Gradle 的 properties 文件里 Windows 盘符需要转义反斜杠
  writeFileSync(localProperties, `sdk.dir=${sdkRoot.replace(/\\/g, '\\\\')}\n`, 'utf8')
  console.log(`• 已写入 android/local.properties（sdk.dir=${sdkRoot}）`)
}

// ---------- 3. 正式包签名参数 ----------
const gradleExtra = []
if (isRelease) {
  const storeFile = process.env.MIAN02_KEYSTORE
  const storePassword = process.env.MIAN02_KEYSTORE_PASSWORD
  const keyAlias = process.env.MIAN02_KEY_ALIAS || 'mian02'
  const keyPassword = process.env.MIAN02_KEY_PASSWORD
  if (!storeFile || !storePassword || !keyPassword) {
    fail(
      '正式签名包需要以下环境变量：MIAN02_KEYSTORE、MIAN02_KEYSTORE_PASSWORD、MIAN02_KEY_PASSWORD（可选 MIAN02_KEY_ALIAS，默认 mian02）。\n' +
        '  首次生成 keystore：\n' +
        '  keytool -genkeypair -v -keystore mian02-release.jks -alias mian02 -keyalg RSA -keysize 2048 -validity 36500 -storepass 你的密码 -keypass 你的密码 -dname "CN=绵阳城市学院, OU=WisPath, O=CampusMate, L=Mianyang, ST=Sichuan, C=CN"'
    )
  }
  gradleExtra.push(
    `-Pandroid.injected.signing.store.file=${resolve(storeFile)}`,
    `-Pandroid.injected.signing.store.password=${storePassword}`,
    `-Pandroid.injected.signing.key.alias=${keyAlias}`,
    `-Pandroid.injected.signing.key.password=${keyPassword}`
  )
}

// ---------- 4. 构建 Web 资源 ----------
if (!skipBuild) run('npm', ['run', 'build'])
else if (!existsSync(join(root, 'dist'))) fail('--skip-build 需要 dist/ 已存在，请先执行 npm run build')

// ---------- 5. 同步到 Android 工程（注入站点地址） ----------
run('npx', ['cap', 'sync', 'android'], { env: { CAPACITOR_SERVER_URL: siteUrl } })

// ---------- 6. Gradle 出包 ----------
const task = isRelease ? 'assembleRelease' : 'assembleDebug'
const gradleArgs = [task, ...gradleExtra]
if (process.platform === 'win32') {
  run('cmd.exe', ['/c', 'gradlew.bat', ...gradleArgs], { cwd: androidDir })
} else {
  run('./gradlew', gradleArgs, { cwd: androidDir })
}

// ---------- 7. 查找并复制安装包 ----------
const buildType = isRelease ? 'release' : 'debug'
const outputDir = join(androidDir, 'app', 'build', 'outputs', 'apk', buildType)
if (!existsSync(outputDir)) fail(`未找到构建产物目录：${outputDir}`)

const apkFiles = readdirSync(outputDir).filter((file) => file.endsWith('.apk'))
if (apkFiles.length === 0) fail(`构建产物目录里没有 .apk：${outputDir}`)

const produced = join(outputDir, apkFiles[0])
mkdirSync(dirname(apkOutput), { recursive: true })
copyFileSync(produced, apkOutput)

// 兼容旧下载页命名：public/download/ 下再留一份 mian02.apk
const mirrorApk = join(root, 'public', 'download', 'mian02.apk')
if (mirrorApk !== apkOutput) copyFileSync(apkOutput, mirrorApk)

// 线上 nginx 的 /download/ 实际读取 <项目根>/apk/download/，项目根必须有一份
mkdirSync(dirname(publishedApk), { recursive: true })
copyFileSync(apkOutput, publishedApk)

const sizeMb = (statSync(apkOutput).size / 1024 / 1024).toFixed(1)
console.log('')
console.log('✔ 安装包已生成')
console.log('  源文件：' + produced)
console.log('  下载页：' + apkOutput + '（' + sizeMb + ' MB）')
console.log('  线上目录：' + publishedApk + '（nginx /download/mian02.apk 读取此处）')
console.log('  下载地址：' + siteUrl + '/download/SmartCampus.apk')

// ---------- 8. 自动发布到腾讯云 COS（失败只告警，不影响打包） ----------
if (noPublish) {
  console.log('')
  console.log('• 已指定 --no-publish，跳过 COS 上传')
} else if (String(process.env.COS_SKIP || '').trim() === '1') {
  console.log('')
  console.log('• 已设置 COS_SKIP=1，跳过 COS 上传')
} else if (!existsSync(publishScript)) {
  console.warn('')
  console.warn('⚠ 未找到发布脚本 ' + publishScript + '，跳过 COS 上传')
} else {
  console.log('')
  console.log('▶ 发布安装包到腾讯云 COS（失败只告警，不影响本地出包）')
  const publishResult = spawnSync(process.execPath, [publishScript, '--apk', publishedApk], {
    cwd: root,
    stdio: 'inherit',
    env: process.env,
    shell: false,
  })
  if (publishResult.error) {
    console.warn('⚠ COS 上传未执行：' + publishResult.error.message)
  } else if (publishResult.status === 2) {
    console.warn('⚠ 未配置腾讯云 COS 密钥，已跳过上传（配置方式见 deploy/cos.env.example）')
  } else if (publishResult.status !== 0) {
    console.warn('⚠ COS 上传失败（退出码 ' + publishResult.status + '），不影响本地出包；详情见上方日志')
  } else {
    console.log('✔ 已完成 COS 上传（公网对象为无扩展名 key，匿名可直接下载）')
  }
}

console.log('')
console.log('下一步（让官网下载页拿到新包）：')
console.log('  docker compose build frontend && docker compose up -d frontend')
console.log('')
console.log('手机验收：扫码官网二维码 → 下载 → 允许「未知来源」→ 安装 → 登录')
