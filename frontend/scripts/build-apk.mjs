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
 * 复制到 public/download/mian02.apk（官网下载页与二维码直接生效）。
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
const apkOutput = join(root, 'public', 'download', 'mian02.apk')

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

const sizeMb = (statSync(apkOutput).size / 1024 / 1024).toFixed(1)
console.log('\n✔ 安装包已生成')
console.log(`  源文件：${produced}`)
console.log(`  下载页：${apkOutput}（${sizeMb} MB）`)
console.log(`  下载地址：${siteUrl}/download/mian02.apk`)
console.log('\n下一步（项目根目录执行，让官网下载页拿到新包）：')
console.log('  docker compose build frontend && docker compose up -d frontend')
console.log('\n手机验收：扫码官网二维码 → 下载 → 允许「未知来源」→ 安装 → 登录')
