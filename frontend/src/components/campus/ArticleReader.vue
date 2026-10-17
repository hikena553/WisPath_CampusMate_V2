<template>
  <Teleport to="body">
    <!-- 打开/关闭动画：移动端复用全局 .subpage（styles/animations.css，全站唯一实现）——
         与工作台子页、驾驶舱子页同一套覆盖式动画：不透明子页从右滑入盖住资讯列表，
         主页面不动，返回时原路滑出。桌面端走原有 reader-fade 淡入（居中卡片不适合整页滑入）。 -->
    <Transition :name="panelTransitionName" :duration="panelTransitionName ? 320 : undefined">
      <div
        v-if="visible"
        class="reader-mask"
        :class="{ 'is-desktop': isDesktop }"
        role="dialog"
        aria-modal="true"
        :aria-label="currentTitle || '校内资讯阅读'"
        @click.self="close"
      >
        <div class="reader-panel" :class="{ 'is-desktop': isDesktop }">
          <!-- 头部：返回 / 标题 / 操作 -->
          <header class="reader-head">
            <button type="button" class="reader-nav" aria-label="返回" @click="close">
              <el-icon :size="19"><ArrowLeft /></el-icon>
            </button>
            <div class="reader-title-wrap">
              <div class="reader-title">{{ currentTitle || '校内资讯' }}</div>
              <div class="reader-sub">{{ currentHost }}</div>
            </div>
            <div class="reader-actions">
              <button
                type="button"
                class="reader-act"
                :class="{ active: mode === 'embed' }"
                :disabled="loading"
                @click="toggleMode"
              >
                {{ mode === 'embed' ? '纯净正文' : '原页渲染' }}
              </button>
              <button type="button" class="reader-nav" aria-label="在浏览器打开" @click="openExternal(currentUrl)">
                <el-icon :size="17"><TopRight /></el-icon>
              </button>
            </div>
          </header>

          <!-- 正文区 -->
          <div class="reader-body" :class="{ 'is-doc': mode === 'article' && !loading && !error }">
            <!-- 分支顺序严格沿用改造前：loading > error > embed > article > links。
                 骨架屏与错误态都放在 Transition 之外：它们只在打开/换页/失败时出现，
                 此时外层覆盖动画（整个面板滑入）正在播放，再叠一层内部滑动会重复发力。
                 注意 error 必须排在 embed 之前（原实现如此）：否则「原页渲染」下
                 iframe 反代失败（onMessage 写入 error）会落入正文/链接清单分支，
                 错误提示被静默吞掉，用户看到的是空白或旧内容。 -->
            <div v-if="loading" class="reader-doc">
              <div class="reader-skeleton">
                <div class="sk-line w60" />
                <div class="sk-line w90" />
                <div class="sk-line w80" />
                <div class="sk-line w90" />
                <div class="sk-line w50" />
              </div>
            </div>

            <!-- 错误态 -->
            <div v-else-if="error" class="reader-doc">
              <div class="reader-state reader-state-error">
                <el-icon :size="42" class="state-icon"><DocumentDelete /></el-icon>
                <p class="state-title">页面暂不可用</p>
                <p class="state-desc">{{ error }}</p>
                <div class="state-btns">
                  <button type="button" class="state-btn primary" @click="retry">
                    <el-icon :size="15"><Refresh /></el-icon> 重试
                  </button>
                  <button
                    v-if="mode === 'article'"
                    type="button"
                    class="state-btn"
                    @click="toggleMode"
                  >
                    原页渲染
                  </button>
                  <button type="button" class="state-btn" @click="openExternal(currentUrl)">
                    浏览器打开
                  </button>
                </div>
              </div>
            </div>

            <!-- 原页渲染（iframe 反代，不透明源沙箱）：切模式用，不参与下钻动画
                 （换 iframe 时原地替换即可，滑动反而像换了一页） -->
            <iframe
              v-else-if="mode === 'embed'"
              :key="embedKey"
              ref="iframeRef"
              class="reader-frame"
              :src="embedSrc"
              sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
              referrerpolicy="no-referrer"
              @load="onFrameLoad"
            />

            <!-- 文档态（正文 / 链接清单）：按 currentUrl 作为一「子页」参与下钻动画。
                 一次下钻 = open() 改 currentUrl = 整块文档替换，滑动发生在「列表 → 文章」这一刻；
                 切模式（toggleMode）与重试（retry）都不改 URL，key 不变 → 不会误播滑动。
                 :duration 320 = CSS 0.3s + 20ms 余量，与外层覆盖动画同一时长。 -->
            <Transition v-else :name="drillTransitionName" :duration="drillTransitionName ? 320 : undefined">
              <div :key="drillKey" class="reader-doc">
                <!-- 正文（纯净阅读） -->
                <div v-if="data?.kind === 'article'" class="reader-article">
                  <h1 class="art-title">{{ data.title }}</h1>
                  <div v-if="data.date" class="art-date">{{ data.date }}</div>
                  <!-- 后端已做正文净化（去脚本/事件属性、相对地址转绝对） -->
                  <div class="art-content" v-html="data.content_html || ''" />
                </div>

                <!-- 链接清单（列表页） -->
                <div v-else class="reader-links">
                  <div v-if="!data?.links?.length" class="reader-state">
                    <el-icon :size="40" class="state-icon"><Document /></el-icon>
                    <p class="state-title">该页面没有可读正文</p>
                    <p class="state-desc">可切换「原页渲染」查看原始排版，或在浏览器中打开。</p>
                  </div>
                  <button
                    v-for="(l, i) in data?.links || []"
                    :key="i"
                    type="button"
                    class="link-row"
                    @click="open(l.url, l.title, 'drill')"
                  >
                    <span class="link-text">{{ l.title }}</span>
                    <span class="link-meta">
                      <span v-if="l.date" class="link-date">{{ l.date }}</span>
                      <el-icon :size="14" class="link-arrow"><ArrowRight /></el-icon>
                    </span>
                  </button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 校内资讯站内阅读器
 *
 * 学校站点设了 X-Frame-Options: SAMEORIGIN，无法直接内嵌；因此：
 * - 「纯净正文」：调用 /api/campus/reader，由后端代抓 + 白名单校验 + 正文净化后渲染；
 * - 「原页渲染」：内嵌 /api/campus/embed 反代页面，配 sandbox（不含 allow-same-origin）
 *   的不透明源，保留原版排版且拿不到应用的 Cookie / localStorage。
 *
 * 用法：`readerRef.value?.open(url, title)`；非校内链接自动回退到新标签页打开。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import { ArrowLeft, ArrowRight, Document, DocumentDelete, Refresh, TopRight } from '@element-plus/icons-vue'
import { campusEmbedUrl, readCampusArticle, type CampusArticle } from '@/api/campus'

const visible = ref(false)
const loading = ref(false)
const error = ref('')
const data = ref<CampusArticle | null>(null)
const currentUrl = ref('')
const currentTitle = ref('')
const mode = ref<'article' | 'embed'>('article')
const embedKey = ref(0)
const iframeRef = ref<HTMLIFrameElement | null>(null)

/** 桌面端居中卡片；移动端全屏抽屉（CSS 断点与全局一致） */
const isDesktop = ref(window.innerWidth > 767)
function onResize() { isDesktop.value = window.innerWidth > 767 }

/* ===== 动画：复用全局 .subpage（styles/animations.css，全站唯一实现） =====
   覆盖式语义：不透明的子页从右滑入盖住主页面，主页面全程不动，返回时原路滑出。
   同一套类名现由三处共用：工作台子页、本阅读器、驾驶舱主页 ↔ 学业子页。

   本组件只需负责两件事（动画本身不在本文件定义）：
   1) 滑动的必须是**不透明的 .reader-panel**，不是半透明遮罩 —— 若平移 mask，
      看到的会是一块半透明黑板横扫屏幕，而不是「一页盖上来」；
      遮罩在移动端因此改为 background: transparent（纯覆盖，背后不加暗色）。
   2) 桌面端居中卡片不适合整页滑入，走原有 reader-fade 淡入。 */

/** 移动端覆盖式滑入 + 关闭时滑出（复用 styles/animations.css 的 .subpage，全站唯一实现）；
    桌面端居中卡片不参与（走原有 reader-fade 淡入） */
const panelTransitionName = computed(() => (isDesktop.value ? 'reader-fade' : 'subpage'))

/** 阅读器内部「链接清单 → 具体文章」的下钻方向：下钻 forward，返回列表 back */
const drillDir = ref<'forward' | 'back'>('forward')
/** 桌面端下钻不做位移（空名 → 无过渡类，Vue 自动检测为立即替换） */
const drillTransitionName = computed(() => (isDesktop.value ? '' : `reader-${drillDir.value}`))

/** 文档层的过渡 key：按 URL 变化。
 *  一次下钻 = currentUrl 改变 = 整块文档作为一「子页」整体替换，
 *  这样推入动画发生在「列表 → 文章」这一刻，而不是等接口返回后「骨架 → 正文」才滑。
 *  切模式（toggleMode）与重试（retry）都不改 URL，key 不变 → 不会误播滑动。 */
const drillKey = computed(() => currentUrl.value)

const embedSrc = computed(() => (currentUrl.value ? campusEmbedUrl(currentUrl.value) : ''))
const currentHost = computed(() => {
  try { return new URL(currentUrl.value).hostname } catch { return '' }
})

/** 与后端白名单一致：仅 *.mycc.edu.cn 走站内阅读 */
function isAllowed(url: string) {
  try {
    const host = new URL(url).hostname.toLowerCase()
    return host === 'mycc.edu.cn' || host.endsWith('.mycc.edu.cn')
  } catch { return false }
}

/** 站外/登录型系统：新标签页打开（被拦截时回退当前页） */
function openExternal(url: string) {
  if (!url) return
  const win = window.open(url, '_blank', 'noopener,noreferrer')
  if (!win) window.location.href = url
}

async function load() {
  if (!currentUrl.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await readCampusArticle(currentUrl.value)
    data.value = res
    if (!currentTitle.value && res.title) currentTitle.value = res.title
    // 列表页没有正文时，默认直接进「原页渲染」，省去一次手动切换
    if (res.kind === 'links' && !res.links.length) mode.value = 'embed'
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '页面抓取失败，可切换原页渲染或稍后重试'
  } finally {
    loading.value = false
  }
}

async function retry() {
  if (mode.value === 'embed') { embedKey.value++; error.value = ''; return }
  await load()
}

function toggleMode() {
  mode.value = mode.value === 'embed' ? 'article' : 'embed'
  error.value = ''
  if (mode.value === 'embed') embedKey.value++
}

/**
 * 打开阅读器：非校内链接直接外跳，保持「不跳出应用」仅作用于校内页面。
 *
 * @param from 调用来源，决定推入方向：
 *   - 'outside'（默认）：来自资讯列表点击 —— 阅读器覆盖式从右滑入；
 *   - 'drill'：阅读器内链接清单点击 —— 内层文档前进（列表 → 文章）；
 *   - 'back'：阅读器内返回父级列表 —— 内层文档反向（文章 → 列表）。
 */
function open(url: string, title?: string, from: 'outside' | 'drill' | 'back' = 'outside') {
  if (!url) return
  if (!isAllowed(url)) { openExternal(url); return }

  // 下钻=前进（新文档从右推入），返回=后退（旧文档向右退出）
  drillDir.value = from === 'back' ? 'back' : 'forward'

  currentUrl.value = url
  currentTitle.value = title || ''
  data.value = null
  error.value = ''
  mode.value = 'article'
  embedKey.value++
  visible.value = true
  void load()
}

function close() {
  drillDir.value = 'forward'
  visible.value = false
  data.value = null
  error.value = ''
}

function onFrameLoad() {
  // 若 iframe 加载的是反代错误页，桥接脚本会 postMessage(error)，此处不重复处理
}

/** 桥接：反代页面通过 postMessage 通知「就绪 / 页内跳转 / 报错」 */
function onMessage(ev: MessageEvent) {
  if (!visible.value) return
  const payload: any = ev.data
  if (!payload || payload.source !== 'campus-reader') return
  // 只接受本组件 iframe 发来的消息，避免其它窗口伪造
  if (!iframeRef.value || ev.source !== iframeRef.value.contentWindow) return
  if (payload.type === 'navigate' && payload.url) {
    // 反代页内跳转：源页面自身就在阅读器里，按「下钻」处理（推入前进）
    open(String(payload.url), payload.title ? String(payload.title) : undefined, 'drill')
  } else if (payload.type === 'error') {
    error.value = String(payload.message || '原页渲染失败，可切换纯净正文查看')
  } else if (payload.type === 'ready') {
    if (payload.title && !currentTitle.value) currentTitle.value = String(payload.title)
    error.value = ''
  }
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && visible.value) close()
}

// 打开时锁定背景滚动
watch(visible, async (v) => {
  await nextTick()
  document.body.style.overflow = v ? 'hidden' : ''
})

onMounted(() => {
  window.addEventListener('message', onMessage)
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  document.body.style.overflow = ''
})

defineExpose({ open })
</script>

<style scoped>
.reader-mask {
  position: fixed;
  inset: 0;
  z-index: 2600;
  /* 移动端：纯覆盖，背后不加暗色（对齐工作台 .sub-page 的整页盖满观感）。
     桌面端是居中卡片，需要压暗背景衬托，由 .is-desktop 类切换（见下）。 */
  background: transparent;
  display: flex;
  align-items: stretch;
  justify-content: center;
}
/* 桌面端：居中卡片需要背景压暗，否则卡片与页面糊在一起、层次不清 */
.reader-mask.is-desktop {
  background: rgba(17, 20, 24, 0.45);
}
.reader-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  /* 整页覆盖的不透明底：滑动时必须不透明，才像「一页盖上来」而不是蒙层滑过 */
  background: var(--dt-bg, #f5f6f8);
  overflow: hidden;
}
/* 桌面端：居中卡片，留出边距 */
.reader-panel.is-desktop {
  width: min(760px, 92vw);
  height: min(84vh, 900px);
  margin: auto;
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
}

.reader-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 52px;
  padding: 8px 10px;
  padding-top: calc(8px + env(safe-area-inset-top, 0px));
  background: var(--dt-surface, #fff);
  border-bottom: 1px solid var(--dt-divider, #ebedf0);
}
.reader-nav {
  width: 34px; height: 34px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 9px; cursor: pointer;
  background: transparent; color: var(--dt-text-secondary, #4b5563);
}
.reader-nav:hover { background: var(--dt-hover, rgba(0, 0, 0, 0.05)); }
.reader-title-wrap { flex: 1; min-width: 0; }
.reader-title {
  font-size: 15.5px; font-weight: 600; color: var(--dt-text, #1f2329);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.reader-sub { font-size: 11.5px; color: var(--dt-text-quiet, #9aa0a6); margin-top: 1px; }
.reader-actions { display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; }
.reader-act {
  height: 30px; padding: 0 11px; border: 1px solid var(--dt-divider, #e5e6eb);
  border-radius: 8px; background: var(--dt-surface, #fff);
  color: var(--dt-text-secondary, #4b5563); font-size: 12.5px; cursor: pointer;
}
.reader-act:hover:not(:disabled) { color: var(--dt-primary-strong, #1677ff); border-color: currentColor; }
.reader-act:disabled { opacity: 0.5; cursor: not-allowed; }

.reader-body {
  flex: 1; min-height: 0; overflow-y: auto; -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}
.reader-body.is-doc { background: var(--dt-surface, #fff); }

/* 骨架屏 */
.reader-skeleton { padding: 22px 18px; display: flex; flex-direction: column; gap: 14px; }
.sk-line { height: 13px; border-radius: 7px; background: linear-gradient(90deg, #eef0f3, #f6f7f9, #eef0f3); background-size: 200% 100%; animation: sk 1.2s ease-in-out infinite; }
.sk-line.w50 { width: 50%; } .sk-line.w60 { width: 60%; } .sk-line.w80 { width: 80%; } .sk-line.w90 { width: 90%; }
@keyframes sk { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* 状态页（错误 / 空） */
.reader-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; padding: 72px 24px; text-align: center;
}
.state-icon { color: var(--dt-text-quiet, #c9cdd4); }
.state-title { margin: 4px 0 0; font-size: 15px; font-weight: 600; color: var(--dt-text, #1f2329); }
.state-desc { margin: 0; font-size: 13px; line-height: 1.6; color: var(--dt-text-tertiary, #6b7280); max-width: 340px; }
.state-btns { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; justify-content: center; }
.state-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 34px; padding: 0 14px; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--dt-divider, #e5e6eb); background: var(--dt-surface, #fff);
  color: var(--dt-text, #1f2329); font-size: 13px;
}
.state-btn.primary { background: var(--dt-primary, #1677ff); border-color: transparent; color: #fff; }

/* 原页渲染 */
.reader-frame { width: 100%; height: 100%; border: 0; display: block; background: #fff; }

/* 正文 */
.reader-article { padding: 20px 18px 40px; }
.art-title { margin: 0 0 8px; font-size: 19px; line-height: 1.45; color: var(--dt-text, #1f2329); }
.art-date { font-size: 12px; color: var(--dt-text-quiet, #9aa0a6); margin-bottom: 14px; }
.art-content { font-size: 15.5px; line-height: 1.78; color: var(--dt-text, #26282c); }
.art-content :deep(p) { margin: 0 0 12px; }
.art-content :deep(img) { max-width: 100%; height: auto; border-radius: 8px; margin: 8px 0; }
.art-content :deep(a) { color: var(--dt-primary-strong, #1677ff); }
.art-content :deep(table) { width: 100% !important; border-collapse: collapse; }
.art-content :deep(td), .art-content :deep(th) { padding: 6px 8px; border: 1px solid var(--dt-divider, #e5e6eb); }

/* 链接清单 */
.reader-links { padding: 6px 0 24px; background: var(--dt-surface, #fff); }
.link-row {
  width: 100%; display: flex; align-items: center; gap: 10px;
  padding: 13px 18px; border: none; border-bottom: 1px solid var(--dt-divider, #f0f1f3);
  background: transparent; text-align: left; cursor: pointer;
}
.link-row:active { background: var(--dt-hover, rgba(0, 0, 0, 0.045)); }
.link-text { flex: 1; min-width: 0; font-size: 14.5px; line-height: 1.5; color: var(--dt-text, #26282c); }
.link-meta { display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; }
.link-date { font-size: 11.5px; color: var(--dt-text-quiet, #9aa0a6); }
.link-arrow { color: var(--dt-text-quiet, #c9cdd4); }

/* 覆盖式滑入/滑出（.subpage）定义在 styles/animations.css，全站唯一实现：
   与工作台子页、驾驶舱子页共用同一套参数与方向语义。此处不再自带一份。 */
.reader-fade-enter-active, .reader-fade-leave-active { transition: opacity 0.2s ease; }
.reader-fade-enter-from, .reader-fade-leave-to { opacity: 0; }

/* 内部下钻「链接清单 ↔ 具体文章」：沿用同一套方向语义与时长，但位移只发生在正文区内 */
.reader-doc { position: relative; min-height: 100%; background: var(--dt-surface, #fff); }
.reader-forward-enter-active.reader-doc,
.reader-back-enter-active.reader-doc { z-index: 2; }
.reader-forward-leave-active.reader-doc,
.reader-back-leave-active.reader-doc {
  position: absolute;
  inset: 0;
  z-index: 1;
  overflow: hidden;
  pointer-events: none;
}
.reader-forward-enter-active.reader-doc,
.reader-forward-leave-active.reader-doc,
.reader-back-enter-active.reader-doc,
.reader-back-leave-active.reader-doc { transition: transform 0.3s ease; }
.reader-forward-enter-from { transform: translateX(100%); }
.reader-forward-leave-to { transform: translateX(-100%); }
.reader-back-enter-from { transform: translateX(-100%); }
.reader-back-leave-to { transform: translateX(100%); }

/* 错误态在 .reader-body 为 is-doc=false 时没有白底，单独补一层，避免离场页透出 */
.reader-state-error { background: var(--dt-surface, #fff); }

@media (prefers-reduced-motion: reduce) {
  .reader-forward-enter-active, .reader-forward-leave-active,
  .reader-back-enter-active, .reader-back-leave-active { transition: opacity 0.2s ease; }
  .reader-forward-enter-from, .reader-forward-leave-to,
  .reader-back-enter-from, .reader-back-leave-to { transform: none; opacity: 0; }
}
</style>
