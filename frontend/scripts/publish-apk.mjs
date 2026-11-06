#!/usr/bin/env node
/**
 * 把 Android 安装包发布到腾讯云 COS（对象存储）。
 *
 * 用法（在 frontend 目录执行）：
 *   npm run apk:publish                      上传默认安装包 <项目根>/apk/download/mian02.apk
 *   npm run apk:publish -- --dry-run         只打印 sha256 / 大小 / 目标对象 / URL，不联网
 *   npm run apk:publish -- --sync            远端包一致且 canonical 可匿名下载时跳过上传
 *   npm run apk:publish -- --setup-cors      上传前 best-effort 配置桶 CORS
 *
 * 配置（进程环境优先，其次读项目根目录 .cos.env）：
 *   COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET / COS_REGION / COS_DOMAIN / COS_APK_PREFIX
 *   模板见 deploy/cos.env.example。
 *
 * 上传对象（ACL 均为 public-read）：
 *   <prefix>/mian02-latest                                application/octet-stream, Cache-Control: no-cache
 *   <prefix>/releases/mian02-<versionName>-<versionCode>   application/octet-stream, Cache-Control: public,max-age=31536000,immutable
 *   <prefix>/latest.json                                  application/json, Cache-Control: no-cache

 * ⚠ 腾讯云 COS 默认域名禁止匿名分发 .apk / .ipa 后缀或 APK Content-Type 的对象
 *   （GET 会返回 403 DownloadForbidden，HEAD 却是 200），因此公开下载对象一律不带扩展名、
 *   Content-Type 用 application/octet-stream，Content-Disposition 只能写 filename*=UTF-8''SmartCampus.apk
 *   （实测 filename="SmartCampus.apk" 同样会被拦截，COS 只放行「仅 filename*」这一种写法），
 *   浏览器据此保存为安装包（自行绑定自定义域名后不受此限制，但保持该约定更稳妥）。
 *
 * 退出码：0 成功 / 无需上传；2 缺凭证或桶配置；1 其他失败。
 */
import { createHash } from 'node:crypto'
import { createReadStream, existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const DEFAULT_APK = join(projectRoot, 'apk', 'download', 'mian02.apk')
const ENV_FILE = join(projectRoot, '.cos.env')
const STATE_FILE = join(projectRoot, '.cos-last-upload.json')
const METADATA_FILE = join(projectRoot, 'frontend', 'android', 'app', 'build', 'outputs', 'apk', 'release', 'output-metadata.json')
const APK_FILENAME = 'SmartCampus.apk'
const APK_CONTENT_TYPE = 'application/octet-stream'
const NL = String.fromCharCode(10)

function usageText() {
  return [
    '用法：node scripts/publish-apk.mjs [选项]',
    '',
    '选项：',
    '  --apk <path>            安装包路径（默认 <项目根>/apk/download/mian02.apk）',
    '  --version-name <name>   版本名（默认读 android/app/build/outputs/apk/release/output-metadata.json）',
    '  --version-code <code>   版本号（同上）',
    '  --prefix <prefix>       对象前缀（默认 apk，其次环境变量 COS_APK_PREFIX）',
    '  --dry-run               不联网，只打印 sha256 / 大小 / 目标对象 / URL',
    '  --sync                  远端包一致（sha/url）且 canonical 可匿名下载时跳过上传',
    '  --setup-cors            上传前 best-effort 配置桶 CORS（失败只告警）',
    '  -h, --help              显示本帮助',
    '',
    '凭证配置：项目根目录 .cos.env（模板见 deploy/cos.env.example），或同名环境变量。',
  ].join(NL)
}

function fail(message, code) {
  console.error(NL + '✖ ' + message + NL)
  process.exit(typeof code === 'number' ? code : 1)
}

function warn(message) {
  console.warn('⚠ ' + message)
}

function formatBytes(bytes) {
  return bytes.toLocaleString('en-US') + ' 字节（' + (bytes / 1024 / 1024).toFixed(1) + ' MB）'
}

function trimSlashes(value) {
  let text = String(value === undefined || value === null ? '' : value).trim()
  while (text.startsWith('/')) text = text.slice(1)
  while (text.endsWith('/')) text = text.slice(0, -1)
  return text
}

function parseEnvFile(file) {
  const result = {}
  if (!existsSync(file)) return result
  let text = ''
  try {
    text = readFileSync(file, 'utf8')
  } catch (err) {
    warn('读取 ' + file + ' 失败：' + err.message)
    return result
  }
  for (const rawLine of text.split(NL)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const eq = line.indexOf('=')
    if (eq <= 0) continue
    const key = line.slice(0, eq).trim()
    let value = line.slice(eq + 1).trim()
    if (value.length >= 2) {
      const first = value[0]
      const last = value[value.length - 1]
      if ((first === '"' && last === '"') || (first === "'" && last === "'")) value = value.slice(1, -1)
    }
    if (key) result[key] = value
  }
  return result
}

function sha256File(file) {
  return new Promise((resolvePromise, rejectPromise) => {
    const hash = createHash('sha256')
    const stream = createReadStream(file)
    stream.on('error', rejectPromise)
    stream.on('data', (chunk) => hash.update(chunk))
    stream.on('end', () => resolvePromise(hash.digest('hex')))
  })
}

// ---------- 1. 解析命令行参数 ----------
const opts = { dryRun: false, sync: false, setupCors: false, apk: undefined, versionName: undefined, versionCode: undefined, prefix: undefined }
const argv = process.argv.slice(2)
for (let index = 0; index < argv.length; index += 1) {
  const arg = argv[index]
  const takeValue = () => {
    index += 1
    if (index >= argv.length || argv[index].startsWith('--')) fail('参数 ' + arg + ' 缺少取值' + NL + NL + usageText())
    return argv[index]
  }
  switch (arg) {
    case '--apk': opts.apk = takeValue(); break
    case '--version-name': opts.versionName = takeValue(); break
    case '--version-code': opts.versionCode = takeValue(); break
    case '--prefix': opts.prefix = takeValue(); break
    case '--dry-run': opts.dryRun = true; break
    case '--sync': opts.sync = true; break
    case '--setup-cors': opts.setupCors = true; break
    case '-h':
    case '--help':
      console.log(usageText())
      process.exit(0)
      break
    default:
      fail('未知参数：' + arg + NL + NL + usageText())
  }
}

async function main() {
  // ---------- 2. 读取配置（进程环境优先，其次 .cos.env） ----------
  const fileEnv = parseEnvFile(ENV_FILE)
  const config = (name) => {
    const fromProcess = process.env[name]
    if (fromProcess !== undefined && String(fromProcess).trim() !== '') return String(fromProcess).trim()
    const fromFile = fileEnv[name]
    return fromFile === undefined ? '' : String(fromFile).trim()
  }

  const secretId = config('COS_SECRET_ID')
  const secretKey = config('COS_SECRET_KEY')
  const bucket = config('COS_BUCKET')
  const region = config('COS_REGION')
  const domain = trimSlashes(config('COS_DOMAIN'))
  const prefix = trimSlashes(opts.prefix !== undefined ? opts.prefix : config('COS_APK_PREFIX')) || 'apk'

  const publicDomain = domain || (bucket && region ? 'https://' + bucket + '.cos.' + region + '.myqcloud.com' : '')
  const encodeKey = (key) => key.split('/').map((segment) => encodeURIComponent(segment)).join('/')
  const canonicalKey = prefix + '/mian02-latest'
  const latestKey = prefix + '/latest.json'
  const objectUrl = (key) => (publicDomain ? publicDomain + '/' + encodeKey(key) : '<COS_DOMAIN>/' + key)

  const missingConfigHelp = (reason) => {
    console.error([
      '',
      '✖ ' + reason,
      '',
      '  配置方式（二选一）：',
      '    1) 编辑项目根目录配置文件 ' + ENV_FILE + '（权限 600，不入库）',
      '    2) 执行命令时注入同名环境变量',
      '',
      '  必填：COS_SECRET_ID、COS_SECRET_KEY、COS_BUCKET、COS_REGION',
      '  可选：COS_DOMAIN、COS_APK_PREFIX',
      '  模板：deploy/cos.env.example',
      '',
    ].join(NL))
  }

  // ---------- 3. 安装包信息 ----------
  const apkPath = resolve(opts.apk !== undefined ? opts.apk : DEFAULT_APK)
  if (!existsSync(apkPath)) {
    fail('找不到安装包：' + apkPath + NL + '  请先执行 npm run apk:release，或用 --apk 指定安装包路径。')
  }
  const apkStat = statSync(apkPath)
  if (!apkStat.isFile() || apkStat.size <= 0) fail('安装包不是有效文件：' + apkPath)
  const apkSize = apkStat.size

  const readMetadata = () => {
    if (!existsSync(METADATA_FILE)) return null
    try {
      const meta = JSON.parse(readFileSync(METADATA_FILE, 'utf8'))
      const element = Array.isArray(meta.elements) ? meta.elements[0] : null
      if (!element) return null
      return { versionName: String(element.versionName === undefined ? '' : element.versionName).trim(), versionCode: Number(element.versionCode) }
    } catch (err) {
      return null
    }
  }

  const meta = readMetadata()
  const versionName = String(opts.versionName !== undefined ? opts.versionName : meta ? meta.versionName : '').trim().split('/').join('-')
  const rawCode = opts.versionCode !== undefined ? Number(opts.versionCode) : meta ? meta.versionCode : Number.NaN
  const version = versionName && Number.isFinite(rawCode) && Number.isInteger(rawCode) && rawCode >= 0
    ? { versionName, versionCode: rawCode }
    : null
  const releaseKey = version ? prefix + '/releases/mian02-' + version.versionName + '-' + version.versionCode : ''

  const sha256 = await sha256File(apkPath)

  // ---------- 4. dry-run：不联网 ----------
  if (opts.dryRun) {
    console.log('')
    console.log('🔍 dry-run：不联网、不上传，只展示将要发布的对象')
    console.log('  安装包：' + apkPath)
    console.log('  大小：' + formatBytes(apkSize))
    console.log('  SHA-256：' + sha256)
    if (version) console.log('  版本：' + version.versionName + '（versionCode ' + version.versionCode + '）')
    else console.log('  版本：无法解析（正式上传前请先完整出包，或传 --version-name / --version-code）')
    console.log('  桶：' + (bucket || '<未配置 COS_BUCKET>') + '    地域：' + (region || '<未配置 COS_REGION>'))
    console.log('  凭证：' + (secretId && secretKey ? '已配置（dry-run 不使用）' : '未配置（dry-run 不需要，正式上传前请在 .cos.env 填入）'))
    console.log('  目标对象（ACL: public-read）：')
    console.log('    - ' + canonicalKey + '  (Content-Type: application/octet-stream, Cache-Control: no-cache)')
    if (version) console.log('    - ' + releaseKey + '  (Content-Type: application/octet-stream, Cache-Control: public,max-age=31536000,immutable)')
    console.log('    - ' + latestKey + '  (Content-Type: application/json, Cache-Control: no-cache)')
    console.log('  下载地址：' + objectUrl(canonicalKey))
    if (version) console.log('  版本快照：' + objectUrl(releaseKey))
    console.log('  版本清单：' + objectUrl(latestKey))
    console.log('')
    process.exit(0)
  }

  // ---------- 5. 凭证校验 ----------
  if (!secretId || !secretKey) {
    missingConfigHelp('未配置腾讯云 COS 密钥（COS_SECRET_ID / COS_SECRET_KEY）')
    process.exit(2)
  }
  if (!bucket || !region) {
    missingConfigHelp('缺少 COS 桶信息（COS_BUCKET / COS_REGION）')
    process.exit(2)
  }

  // ---------- 6. 加载 COS SDK ----------
  let COS
  try {
    const mod = await import('cos-nodejs-sdk-v5')
    COS = mod.default || mod
  } catch (err) {
    fail('无法加载 cos-nodejs-sdk-v5：' + err.message + NL + '  请先在 frontend 目录执行：npm install --save-exact cos-nodejs-sdk-v5@3.0.0')
  }
  if (typeof COS !== 'function') fail('cos-nodejs-sdk-v5 导出类型异常，无法初始化客户端')
  const cos = new COS({ SecretId: secretId, SecretKey: secretKey })
  const bucketParams = { Bucket: bucket, Region: region }

  const cosCall = (method, params) => new Promise((resolvePromise, rejectPromise) => {
    cos[method](params, (err, data) => {
      if (err) rejectPromise(err)
      else resolvePromise(data)
    })
  })
  const errorText = (err) => (!err ? '未知错误' : err.message || err.error || err.code || String(err))

  // ---------- 7. --setup-cors：best-effort ----------
  if (opts.setupCors) {
    try {
      await cosCall('putBucketCors', {
        ...bucketParams,
        CORSConfiguration: {
          CORSRules: [
            {
              AllowedOrigins: ['*'],
              AllowedMethods: ['GET', 'HEAD'],
              AllowedHeaders: ['*'],
              ExposeHeaders: ['ETag', 'Content-Length', 'Content-Range', 'Content-Type'],
              MaxAgeSeconds: 600,
            },
          ],
        },
      })
      console.log('✔ 已更新桶 CORS：AllowOrigin=*，GET/HEAD，MaxAge=600')
    } catch (err) {
      warn('配置桶 CORS 失败（不影响上传，可在腾讯云控制台手动配置）：' + errorText(err))
    }
  }

  // ---------- 8. --sync：远端真的可匿名下载且是同一个包，才跳过上传 ----------
  // 不能只看 latest.json 的 sha256：对象可能被 COS 默认域名拦截（HEAD 200 / 真实 GET 403），
  // 或 url 仍指向旧的 .apk 对象。必须同时满足：
  //   (a) 远端 latest.json.sha256 == 本地 sha256
  //   (b) 远端 latest.json.url == 期望 canonical URL
  //   (c) canonical 可匿名下载（Range: bytes=0-0 返回 206/200；HEAD 不可靠，不用）
  // 任一不满足就重新上传。
  if (opts.sync) {
    const canonicalUrl = objectUrl(canonicalKey)
    const latestUrl = objectUrl(latestKey)
    let latest = null
    let latestError = ''
    try {
      const response = await fetch(latestUrl, { signal: AbortSignal.timeout(20000) })
      if (!response.ok) throw new Error('HTTP ' + response.status)
      latest = await response.json()
    } catch (err) {
      latestError = err && err.message ? err.message : String(err)
    }

    const sameSha = !!(latest && typeof latest.sha256 === 'string' && latest.sha256.toLowerCase() === sha256.toLowerCase())
    const sameUrl = !!(latest && typeof latest.url === 'string' && latest.url === canonicalUrl)
    let probeStatus = ''
    let downloadable = false
    if (sameSha && sameUrl) {
      try {
        const probe = await fetch(canonicalUrl, { headers: { Range: 'bytes=0-0' }, signal: AbortSignal.timeout(20000) })
        probeStatus = 'HTTP ' + probe.status
        downloadable = probe.status === 206 || probe.status === 200
        if (probe.body) await probe.body.cancel()
      } catch (err) {
        probeStatus = err && err.message ? err.message : String(err)
      }
    }

    if (sameSha && sameUrl && downloadable) {
      console.log('✔ 远端已是最新且可匿名下载，跳过上传')
      console.log('  SHA-256：' + sha256)
      console.log('  URL：' + canonicalUrl)
      console.log('  Range 探测：' + probeStatus)
      process.exit(0)
    }

    let reason = '远端 latest.json 不可用'
    if (latest) {
      if (!sameSha) reason = 'latest.json.sha256 与本地不一致'
      else if (!sameUrl) reason = 'latest.json.url 未指向 canonical（' + String(latest.url) + '）'
      else reason = 'canonical 匿名下载失败（' + probeStatus + '）'
    }
    if (latestError) warn('读取远端 ' + latestKey + ' 失败（' + latestError + '）')
    console.log('• 需要上传：' + reason)
  }

  if (!version) {
    fail('无法确定安装包版本号：' + METADATA_FILE + ' 不存在或无法解析。' + NL + '  请先完整出包（npm run apk:release），或传 --version-name 与 --version-code。')
  }

  // ---------- 9. 上传 ----------
  const apkHeaders = {
    ContentType: APK_CONTENT_TYPE,
    // 只能写 filename*：实测 filename="SmartCampus.apk" 也会被 COS 默认域名拦截（GET 403）
    ContentDisposition: "attachment; filename*=UTF-8''" + APK_FILENAME,
  }

  const uploadApk = async (key, cacheControl) => {
    console.log('  ↑ 上传 ' + key + '（Cache-Control: ' + cacheControl + '）')
    let data
    try {
      data = await cosCall('putObject', {
        ...bucketParams,
        Key: key,
        Body: createReadStream(apkPath),
        ContentLength: apkSize,
        ACL: 'public-read',
        CacheControl: cacheControl,
        ...apkHeaders,
      })
    } catch (err) {
      throw new Error('上传 ' + key + ' 失败：' + errorText(err))
    }
    const etag = data && data.ETag ? String(data.ETag).split('"').join('') : ''
    console.log('    ✔ 完成' + (etag ? '（ETag ' + etag + '）' : ''))
    return data
  }

  console.log('')
  console.log('▶ 发布安装包到腾讯云 COS')
  console.log('  桶：' + bucket + '    地域：' + region + '    前缀：' + prefix + '/')
  console.log('  文件：' + apkPath)
  console.log('  大小：' + formatBytes(apkSize))
  console.log('  SHA-256：' + sha256)
  console.log('  版本：' + version.versionName + '（versionCode ' + version.versionCode + '）')
  console.log('')

  await uploadApk(releaseKey, 'public,max-age=31536000,immutable')
  await uploadApk(canonicalKey, 'no-cache')

  const uploadedAt = new Date().toISOString()
  const latestPayload = {
    versionName: version.versionName,
    versionCode: version.versionCode,
    size: apkSize,
    sha256,
    url: objectUrl(canonicalKey),
    uploadedAt,
  }

  console.log('  ↑ 上传 ' + latestKey + '（application/json, Cache-Control: no-cache）')
  try {
    await cosCall('putObject', {
      ...bucketParams,
      Key: latestKey,
      Body: JSON.stringify(latestPayload, null, 2) + NL,
      ContentType: 'application/json',
      CacheControl: 'no-cache',
      ACL: 'public-read',
    })
  } catch (err) {
    throw new Error('上传 ' + latestKey + ' 失败：' + errorText(err))
  }
  console.log('    ✔ 完成')

  try {
    writeFileSync(STATE_FILE, JSON.stringify({
      sha256,
      versionName: version.versionName,
      versionCode: version.versionCode,
      url: objectUrl(canonicalKey),
      uploadedAt,
    }, null, 2) + NL, 'utf8')
  } catch (err) {
    warn('写入本地状态文件失败（不影响本次发布）：' + err.message)
  }

  console.log('• 匿名可达性自检（Range: bytes=0-0，HEAD 不可靠故用 GET）...')
  try {
    const probe = await fetch(objectUrl(canonicalKey), { headers: { Range: 'bytes=0-0' }, signal: AbortSignal.timeout(20000) })
    const ok = probe.status === 206 || probe.status === 200
    console.log('  匿名 GET ' + objectUrl(canonicalKey) + ' → HTTP ' + probe.status + (ok ? ' ✔ 可下载' : ' ⚠ 不可匿名下载，请检查对象 ACL / Content-Type / Content-Disposition'))
    if (probe.body) await probe.body.cancel()
  } catch (err) {
    warn('匿名可达性自检失败：' + (err && err.message ? err.message : err))
  }

  console.log('')
  console.log('✔ 发布完成')
  console.log('  下载地址：' + objectUrl(canonicalKey))
  console.log('  版本快照：' + objectUrl(releaseKey))
  console.log('  版本清单：' + objectUrl(latestKey))
  console.log('  本地状态：' + STATE_FILE)
  console.log('')
}

main().catch((err) => {
  console.error('')
  console.error('✖ 发布失败：' + (err && err.message ? err.message : err))
  console.error('  排查建议：确认 .cos.env 的密钥 / 桶名 / 地域正确，服务器可访问 cos.<region>.myqcloud.com；')
  console.error('  若提示 ACL / 权限错误，确认子账号已被授予该桶上传权限、桶未禁止公共读写。')
  console.error('')
  process.exit(1)
})
