import { defineConfig, type Plugin, type ViteDevServer, type PreviewServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { createReadStream, existsSync } from 'node:fs'
import { extname, join } from 'node:path'
import type { IncomingMessage, ServerResponse } from 'node:http'

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

export default defineConfig({
  plugins: [vue(), ortStaticPlugin()],
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
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, ws: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})