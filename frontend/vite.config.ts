import { defineConfig, type Plugin, type ViteDevServer, type PreviewServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { createReadStream, existsSync, readFileSync } from 'node:fs'
import { extname, join } from 'node:path'
import type { IncomingMessage, ServerResponse } from 'node:http'

const CERT_DIR = fileURLToPath(new URL('./certs', import.meta.url))
const HTTPS_ENABLED = process.env.VITE_HTTPS === '1'
const HTTPS_KEY = join(CERT_DIR, 'dev-server.key')
const HTTPS_CERT = join(CERT_DIR, 'dev-server.crt')

const ORT_MIME: Record<string, string> = {
  '.mjs': 'text/javascript',
  '.js': 'text/javascript',
  '.wasm': 'application/wasm',
}

/**
 * 静态放行 /ort/* 运行时文件。
 *
 * 背景：onnxruntime-web 的 wasm 后端在运行时用动态 import() 取
 * `ort-wasm-simd-threaded.mjs`，Vite 会给这类请求带上 `?import` 查询串；
 * 而 Vite 对 public 目录下的文件遇到查询串会返回 500，浏览器随即报
 * "Failed to fetch dynamically imported module"，wasm 后端不可用，
 * 模型加载整体失败。这里在 Vite 内部中间件之前直接以静态文件响应（忽略查询串）。
 * 生产环境用静态服务器托管 dist 时不会出现该问题，但加上它可保证 dev/preview 一致。
 */
function ortStaticPlugin(): Plugin {
  const handler =
    (root: string) => (req: IncomingMessage, res: ServerResponse, next: () => void) => {
      const url = req.url || ''
      if (!url.startsWith('/ort/')) return next()
      const file = join(root, 'public', decodeURIComponent(url.split('?')[0]))
      if (!existsSync(file)) return next()
      res.setHeader('Content-Type', ORT_MIME[extname(file)] || 'application/octet-stream')
      res.setHeader('Cache-Control', 'no-cache')
      createReadStream(file).pipe(res)
    }
  return {
    name: 'ort-static',
    configureServer(server: ViteDevServer) {
      server.middlewares.use(handler(server.config.root))
    },
    configurePreviewServer(server: PreviewServer) {
      server.middlewares.use(handler(server.config.root))
    },
  }
}

/**
 * 开发证书下载（仅 HTTPS 模式）。
 *
 * 手机浏览器只有 HTTPS/localhost 才允许调用麦克风；局域网 IP + HTTP 会被浏览器
 * 直接禁用 navigator.mediaDevices。HTTPS 模式下手机需要先安装本地 CA，这里把
 * CA 证书与 iOS 描述文件直接以附件形式提供，避免用户去电脑上找文件。
 */
function devCertDownloadPlugin(): Plugin {
  const files: Record<string, { file: string; type: string }> = {
    '/__dev-ca.crt': { file: 'dev-ca.crt', type: 'application/x-x509-ca-cert' },
    '/__dev-ca.mobileconfig': { file: 'dev-ca.mobileconfig', type: 'application/x-apple-aspen-config' },
  }
  return {
    name: 'dev-cert-download',
    configureServer(server: ViteDevServer) {
      if (!HTTPS_ENABLED) return
      server.middlewares.use((req, res, next) => {
        const path = (req.url || '').split('?')[0]
        const item = files[path]
        if (!item) return next()
        const full = join(CERT_DIR, item.file)
        if (!existsSync(full)) return next()
        res.setHeader('Content-Type', item.type)
        res.setHeader('Content-Disposition', `attachment; filename="${item.file}"`)
        createReadStream(full).pipe(res)
      })
    },
  }
}

const httpsOptions =
  HTTPS_ENABLED && existsSync(HTTPS_KEY) && existsSync(HTTPS_CERT)
    ? { key: readFileSync(HTTPS_KEY), cert: readFileSync(HTTPS_CERT) }
    : undefined

if (HTTPS_ENABLED && !httpsOptions) {
  console.warn('[vite] VITE_HTTPS=1 但未找到 frontend/certs/dev-server.*，本次仍以 HTTP 启动')
}

export default defineConfig({
  plugins: [vue(), ortStaticPlugin(), devCertDownloadPlugin()],
  optimizeDeps: {
    include: ['d3-cloud', 'd3-dispatch']
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    https: httpsOptions,
    proxy: {
      '/api': { target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true, ws: true },
      '/uploads': { target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})