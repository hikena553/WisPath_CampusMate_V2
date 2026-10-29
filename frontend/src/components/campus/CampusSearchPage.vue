<template>
  <Teleport to="body">
    <!-- 移动端全屏搜索子页：动画复用全局 .subpage（styles/animations.css，全站唯一实现）。
         结构照抄 ArticleReader / ArticleDetailPage：Teleport + Transition(name="subpage") + 根元素 fixed inset:0。
         取舍同前两者：不用 el-dialog / el-drawer —— 手机上的对话框是「半个页面浮着」的形态，
         而这页要的是「整页盖上来」的确定性版式，自己写样式可控得多。 -->
    <Transition name="subpage" :duration="320" @after-leave="emit('closed')">
      <div
        v-if="visible"
        class="csp-root"
        role="dialog"
        aria-modal="true"
        aria-label="搜索资讯"
      >
        <!-- ① 顶栏：返回 + 搜索框。搜索框在顶栏内直接可输入，点开即聚焦，
             不再多一次「点输入框」的点击 —— 打开搜索页的人目的只有一个。 -->
        <header class="csp-head">
          <button type="button" class="csp-icon-btn" aria-label="返回" @click="close">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <form class="csp-field" role="search" @submit.prevent="onSubmit">
            <el-icon class="csp-field-icon" :size="16"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="keyword"
              class="csp-input"
              type="search"
              enterkeyhint="search"
              placeholder="搜索资讯 / 公告"
              aria-label="搜索资讯"
            >
            <button
              v-if="keyword"
              type="button"
              class="csp-clear"
              aria-label="清空输入"
              @click="keyword = ''"
            >
              <el-icon :size="14"><CircleClose /></el-icon>
            </button>
          </form>
          <button
            type="button"
            class="csp-text-btn"
            :disabled="!keyword.trim()"
            @click="onSubmit"
          >
            搜索
          </button>
        </header>

        <div class="csp-scroll">
          <!-- ============ 搜索态：结果视图 ============ -->
          <template v-if="searched">
            <div v-if="!results.length" class="csp-empty">
              <el-icon :size="44" class="csp-empty-icon"><Search /></el-icon>
              <p class="csp-empty-title">没有找到「{{ submitted }}」相关资讯</p>
              <p class="csp-empty-desc">换个关键词试试，或看看下面的热门内容</p>
            </div>

            <template v-else>
              <div class="csp-result-head">
                找到 <b>{{ results.length }}</b> 条相关资讯
              </div>
              <ul class="csp-list">
                <li v-for="item in results" :key="item.url">
                  <button type="button" class="csp-item" @click="openHit(item)">
                    <div class="csp-item-main">
                      <p class="csp-item-title" v-html="highlight(item.title)" />
                      <div class="csp-item-meta">
                        <span class="csp-tag">{{ item.sourceLabel }}</span>
                        <span>{{ item.dateLabel }}</span>
                        <span v-if="item.view_count" class="csp-meta-dot">
                          <el-icon :size="12"><View /></el-icon>{{ item.view_count }}
                        </span>
                        <span v-if="item.comment_count" class="csp-meta-dot">
                          <el-icon :size="12"><ChatDotRound /></el-icon>{{ item.comment_count }}
                        </span>
                      </div>
                    </div>
                    <img
                      v-if="item.image_url"
                      class="csp-item-thumb"
                      :src="item.image_url"
                      alt=""
                      loading="lazy"
                    >
                  </button>
                </li>
              </ul>
            </template>

            <!-- 空结果时把热门兜底也放出来，别让人卡在死路 -->
            <section v-if="!results.length" class="csp-section">
              <h3 class="csp-section-title">热门资讯</h3>
              <ol class="csp-hot">
                <li
                  v-for="(item, idx) in hotList"
                  :key="'hot-e-' + item.url"
                  class="csp-hot-item"
                  @click="openHit(item)"
                >
                  <span class="csp-hot-rank" :class="rankClass(idx)">{{ idx + 1 }}</span>
                  <span class="csp-hot-title">{{ item.title }}</span>
                </li>
              </ol>
            </section>
          </template>

          <!-- ============ 初始态：历史 / 发现 / 热榜 ============ -->
          <template v-else>
            <section v-if="searchHistory.length" class="csp-section">
              <div class="csp-section-head">
                <h3 class="csp-section-title">搜索历史</h3>
                <button type="button" class="csp-section-action" @click="clearHistory">
                  <el-icon :size="14"><Delete /></el-icon>清空
                </button>
              </div>
              <div class="csp-chips">
                <button
                  v-for="h in searchHistory"
                  :key="'h-' + h"
                  type="button"
                  class="csp-chip"
                  @click="applyKeyword(h)"
                >
                  {{ h }}
                </button>
              </div>
            </section>

            <section class="csp-section">
              <h3 class="csp-section-title">搜索发现</h3>
              <div class="csp-chips">
                <button
                  v-for="s in discoveries"
                  :key="'d-' + s"
                  type="button"
                  class="csp-chip is-ghost"
                  @click="applyKeyword(s)"
                >
                  {{ s }}
                </button>
              </div>
            </section>

            <section class="csp-section">
              <div class="csp-section-head">
                <h3 class="csp-section-title">热门资讯</h3>
                <span class="csp-section-sub">近 30 天热度</span>
              </div>
              <ol class="csp-hot">
                <li
                  v-for="(item, idx) in hotList"
                  :key="'hot-' + item.url"
                  class="csp-hot-item"
                  @click="openHit(item)"
                >
                  <span class="csp-hot-rank" :class="rankClass(idx)">{{ idx + 1 }}</span>
                  <span class="csp-hot-title">{{ item.title }}</span>
                </li>
              </ol>
            </section>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  ArrowLeft, Search, CircleClose, Delete, View, ChatDotRound,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

/** 搜索池条目：由父页 CampusPage 统一备好（栏目合并流 + 互动计数 + 去公共前缀），
 * 本页只消费、不自己取数 —— 池子规则只维护一处，免得搜索结果与信息流对不上。 */
export interface SearchPoolItem {
  title: string
  url: string
  source: string
  sourceLabel: string
  /** 父页来源数据这两项可能为 null（后端未给图 / 未给日期），这里照实放宽 */
  date: string | null
  dateLabel: string
  image_url?: string | null
  comment_count: number
  view_count: number
}

const props = defineProps<{ items: SearchPoolItem[] }>()

const emit = defineEmits<{
  /** 动画播完、已卸载 */
  (e: 'closed'): void
  /** 点中一条命中资讯：交由父页打开详情子页（盖在本页之上） */
  (e: 'open', url: string, title: string, source: string): void
}>()

const HISTORY_KEY = 'campus_search_history'
const HISTORY_MAX = 10

const visible = ref(true)
const keyword = ref('')
/** 已提交的关键词（回车/点搜索才算一次），与输入框实时值分开：
 * 边打字边出结果会让「搜过了」这个状态含混，历史记录也会被塞进半截词。 */
const submitted = ref('')
const searched = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)
const searchHistory = ref<string[]>([])

/* ================= 历史 ================= */
function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const list = raw ? JSON.parse(raw) : []
    searchHistory.value = Array.isArray(list) ? list.filter((x: unknown) => typeof x === 'string').slice(0, HISTORY_MAX) : []
  } catch {
    searchHistory.value = []
  }
}

function persist() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(searchHistory.value))
  } catch {
    /* 隐私模式 / 配额满：历史存不下不影响搜索本身，静默降级 */
  }
}

function pushHistory(kw: string) {
  const word = kw.trim()
  if (!word) return
  // 重复词提到最前，不产生重复项
  searchHistory.value = [word, ...searchHistory.value.filter((h) => h !== word)].slice(0, HISTORY_MAX)
  persist()
}

async function clearHistory() {
  try {
    await ElMessageBox.confirm('确定清空全部搜索历史？', '清空搜索历史', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return // 取消
  }
  searchHistory.value = []
  persist()
}

/* ================= 搜索 ================= */
function onSubmit() {
  const kw = keyword.value.trim()
  if (!kw) return
  submitted.value = kw
  searched.value = true
  pushHistory(kw)
  inputRef.value?.blur()
}

function applyKeyword(kw: string) {
  keyword.value = kw
  onSubmit()
}

/** 标题命中高亮：只高亮第一处、且做 HTML 转义后再拼，避免标题里的 < > & 破坏结构 */
function highlight(title: string): string {
  const kw = submitted.value
  if (!kw) return escapeHtml(title)
  const idx = title.toLowerCase().indexOf(kw.toLowerCase())
  if (idx < 0) return escapeHtml(title)
  const head = escapeHtml(title.slice(0, idx))
  const hit = escapeHtml(title.slice(idx, idx + kw.length))
  const tail = escapeHtml(title.slice(idx + kw.length))
  return `${head}<em class="csp-hit">${hit}</em>${tail}`
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const results = computed<SearchPoolItem[]>(() => {
  const kw = submitted.value.toLowerCase()
  if (!kw) return []
  return props.items.filter((i) => (i.title || '').toLowerCase().includes(kw))
})

/** 热榜：有浏览/评论计数的按热度排，全为 0 的退化为「按日期新→旧」 */
const hotList = computed<SearchPoolItem[]>(() => {
  const arr = [...props.items]
  const hasStat = arr.some((i) => i.view_count || i.comment_count)
  if (hasStat) {
    arr.sort(
      (a, b) =>
        b.view_count + b.comment_count * 3 - (a.view_count + a.comment_count * 3),
    )
  } else {
    arr.sort((a, b) => (b.date || '').localeCompare(a.date || ''))
  }
  return arr.slice(0, 10)
})

/** 搜索发现：从池子里取来源栏目 + 高频词，纯本地推导，不额外请求。
 * 少而准比多而杂有用 —— 8 个左右刚好两行。 */
const discoveries = computed<string[]>(() => {
  const stop = new Set([
    '关于', '通知', '公告', '的', '和', '与', '及', '通知公告', '新闻', '动态',
    '我校', '学院', '大学', '学校', '开展', '举行', '召开', '组织', '进一步', '做好',
  ])
  const freq = new Map<string, number>()
  for (const item of props.items) {
    // 中文按 2-4 字切片过粗，这里采用「栏目词 + 标题里的机构/主题词」两路
    for (const token of item.title.split(/[\s,，。、：:；;！!？?「」《》（）()【】\[\]"“”'']+/)) {
      const t = token.trim()
      if (t.length < 2 || t.length > 8 || stop.has(t)) continue
      freq.set(t, (freq.get(t) || 0) + 1)
    }
  }
  const words = [...freq.entries()]
    .filter(([, n]) => n >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([w]) => w)

  const labels = [...new Set(props.items.map((i) => i.sourceLabel).filter(Boolean))]
  return [...labels.slice(0, 4), ...words].slice(0, 8)
})

function rankClass(idx: number): string {
  return idx < 3 ? `is-top${idx + 1}` : ''
}

/* ================= 交互 ================= */
function openHit(item: SearchPoolItem) {
  const kw = submitted.value.trim()
  // 从热榜点进去也算一次意图：有关键词才记，避免把空串写进历史
  if (kw && searched.value) pushHistory(kw)
  emit('open', item.url, item.title, item.source)
}

/** 是否由 popstate 触发关闭 —— 只有「不是」才需要手动把锚记录退掉 */
let closedByPop = false

function close() {
  closedByPop = false
  visible.value = false
}

/** 返回键（安卓）/ 浏览器返回手势：先退出搜索页，而不是把整个页面弹走。
 * 本页不是路由，靠压一条同 URL 的历史记录当「锚」：挂载时 pushState 一条，
 * 用户按返回 → 浏览器回到上一条（即原页面）并触发 popstate → 本页关闭。
 * 注意不能用 replaceState 打标记 —— 那样历史长度不变，popstate 永不触发，
 * 返回键会直接把用户弹出整个资讯页，比不处理更糟。
 * 主动点「返回」按钮时（close）不再动历史：visible 变 false 后组件卸载，
 * 那条锚记录已被这次前进覆盖回原页，无需回退，否则会多退一页。 */
function onPopState() {
  if (visible.value) {
    closedByPop = true
    visible.value = false
  }
}

watch(visible, (v) => {
  if (v) return
  window.removeEventListener('popstate', onPopState)
  // 点按钮关闭时锚记录还在历史里，退掉它 —— 否则用户下次按返回会「原地不动」一次。
  // 先摘监听再回退，避免这次 history.back() 又打到自己的 popstate 上。
  if (!closedByPop) {
    closedByPop = true
    history.back()
  }
})

defineExpose({ close })

/* ================= 初始 ================= */
loadHistory()
history.pushState({ ...(history.state || {}), __csp: true }, '')
window.addEventListener('popstate', onPopState)

nextTick(() => {
  // 桌面端不自动弹键盘，移动端才聚焦（autoFocus 在 iOS 上会顶起视口导致首帧跳动）
  if (window.matchMedia('(pointer: coarse)').matches) {
    inputRef.value?.focus()
  }
})
</script>

<style scoped>
/* ================= 根容器 =================
   fixed inset:0 的整页覆盖层。z-index 2650 —— 高于 ArticleDetailPage 的 2600：
   点搜索结果会打开详情子页盖在本页之上，本页必须比它低一档；
   但仍高于移动端底部导航（1000）与顶栏（100），保证整页压住底部。
   进出场动画走全局 .subpage（styles/animations.css）。 */
.csp-root {
  position: fixed;
  inset: 0;
  z-index: 2650;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  color: #1d2129;
  -webkit-tap-highlight-color: transparent;
  overflow: hidden;
}

/* ================= 顶栏 ================= */
.csp-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  padding-top: calc(6px + env(safe-area-inset-top, 0px));
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.csp-icon-btn {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #4e5969;
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.csp-icon-btn:active { background: #f2f3f5; }

.csp-field {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 10px;
  border-radius: 18px;
  background: #f2f3f5;
  transition: background-color 0.15s ease, box-shadow 0.15s ease;
}
.csp-field:focus-within {
  background: #fff;
  box-shadow: 0 0 0 1.5px rgba(22, 119, 255, 0.35);
}

.csp-field-icon { flex-shrink: 0; color: #86909c; }

.csp-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #1d2129;
  line-height: 1;
  /* iOS 输入框小于 16px 会自动缩放页面，这页是真机高频操作，抬到 16px 更稳 */
  font-size: 16px;
}
.csp-input::placeholder { color: #a9aeb8; font-size: 14px; }
/* 去掉 Safari/Chrome 搜索框自带的清除按钮，统一用自绘的那颗 */
.csp-input::-webkit-search-cancel-button { display: none; }

.csp-clear {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: #c9cdd4;
  color: #fff;
  cursor: pointer;
  padding: 0;
}

.csp-text-btn {
  flex-shrink: 0;
  padding: 0 6px;
  height: 36px;
  border: none;
  background: transparent;
  color: #1677ff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
.csp-text-btn:disabled { color: #c9cdd4; cursor: default; }

/* ================= 滚动区 ================= */
.csp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 12px 12px calc(20px + env(safe-area-inset-bottom, 0px));
  overscroll-behavior: contain;
}

.csp-section { margin-bottom: 18px; }

.csp-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.csp-section-title {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}
.csp-section-head .csp-section-title { margin-bottom: 0; }

.csp-section-sub { font-size: 12px; color: #a9aeb8; }

.csp-section-action {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: none;
  background: transparent;
  padding: 2px 4px;
  font-size: 12px;
  color: #86909c;
  cursor: pointer;
}

/* ================= 关键词胶囊 ================= */
.csp-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.csp-chip {
  max-width: 100%;
  padding: 7px 13px;
  border: none;
  border-radius: 16px;
  background: #fff;
  color: #4e5969;
  font-size: 13px;
  line-height: 1.2;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: background-color 0.15s ease;
}
.csp-chip:active { background: #e8f3ff; color: #1677ff; }
.csp-chip.is-ghost { background: #eef0f3; }

/* ================= 热榜 ================= */
.csp-hot {
  margin: 0;
  padding: 4px 12px;
  list-style: none;
  background: #fff;
  border-radius: 12px;
}

.csp-hot-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid #f7f8fa;
  cursor: pointer;
}
.csp-hot-item:last-child { border-bottom: none; }
.csp-hot-item:active .csp-hot-title { color: #1677ff; }

.csp-hot-rank {
  flex-shrink: 0;
  width: 18px;
  text-align: center;
  font-size: 14px;
  font-weight: 700;
  font-style: italic;
  color: #c9cdd4;
}
/* 前三名用热度色区分，弱化其余名次 —— 一眼能看出「谁最热」 */
.csp-hot-rank.is-top1 { color: #f53f3f; }
.csp-hot-rank.is-top2 { color: #ff7d00; }
.csp-hot-rank.is-top3 { color: #ffb400; }

.csp-hot-title {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 1.5;
  color: #1d2129;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.15s ease;
}

/* ================= 结果列表 ================= */
.csp-result-head {
  padding: 2px 2px 10px;
  font-size: 13px;
  color: #86909c;
}
.csp-result-head b { color: #1677ff; font-weight: 600; }

.csp-list {
  margin: 0;
  padding: 0;
  list-style: none;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.csp-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 14px 12px;
  border: none;
  border-bottom: 1px solid #f7f8fa;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.csp-list li:last-child .csp-item { border-bottom: none; }
.csp-item:active { background: #fafbfc; }

.csp-item-main {
  flex: 1;
  min-width: 0;
}

.csp-item-title {
  margin: 0 0 8px;
  font-size: 15px;
  line-height: 1.45;
  font-weight: 500;
  color: #1d2129;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.csp-item-title :deep(.csp-hit) {
  font-style: normal;
  color: #1677ff;
  font-weight: 600;
}

.csp-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #a9aeb8;
}

.csp-tag {
  padding: 1px 6px;
  border-radius: 4px;
  background: #e8f3ff;
  color: #1677ff;
  font-size: 11px;
  line-height: 1.5;
}

.csp-meta-dot {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.csp-item-thumb {
  flex-shrink: 0;
  width: 84px;
  height: 60px;
  border-radius: 8px;
  object-fit: cover;
  background: #f2f3f5;
}

/* ================= 空态 ================= */
.csp-empty {
  padding: 64px 24px 32px;
  text-align: center;
}
.csp-empty-icon { color: #c9cdd4; }
.csp-empty-title {
  margin: 14px 0 6px;
  font-size: 15px;
  font-weight: 500;
  color: #4e5969;
}
.csp-empty-desc {
  margin: 0;
  font-size: 13px;
  color: #a9aeb8;
  line-height: 1.6;
}
</style>
