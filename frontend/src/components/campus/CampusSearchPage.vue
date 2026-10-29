<template>
  <Teleport to="body">
    <!-- 覆盖式全屏子页：动画复用全局 .subpage（styles/animations.css，keyframes 驱动）。
         结构照抄 ArticleDetailPage：Teleport + Transition(name="subpage") + 根元素 fixed inset:0。
         只在移动端挂载（父页 openSearch 分流），桌面端继续用对话框搜索。 -->
    <Transition name="subpage" :duration="320" @after-leave="emit('closed')">
      <div
        v-if="visible"
        class="csp-root"
        role="dialog"
        aria-modal="true"
        aria-label="搜索校园资讯"
      >
        <!-- ① 顶栏：返回 + 圆角搜索框。参考稿只放这两个元素，
             键盘搜索键提交（enterkeyhint=search），不额外放「搜索」按钮。 -->
        <header class="csp-head">
          <button type="button" class="csp-back" aria-label="返回" @click="close">
            <el-icon :size="22"><ArrowLeft /></el-icon>
          </button>
          <div class="csp-field">
            <el-icon class="csp-field-icon" :size="16"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="keyword"
              class="csp-input"
              type="search"
              enterkeyhint="search"
              :placeholder="placeholder"
              @keyup.enter="runSearch"
            />
            <button
              v-if="keyword"
              type="button"
              class="csp-clear"
              aria-label="清空关键词"
              @click="clearKeyword"
            >
              <el-icon :size="15"><CircleCloseFilled /></el-icon>
            </button>
          </div>
        </header>

        <!-- ② 滚动区：搜索前是「历史 / 发现 / 热榜」三段；提交后整区换成结果。
             历史与发现是纯本地状态，热榜吃父页传来的资讯池（含互动计数）。 -->
        <div class="csp-scroll">
          <template v-if="!searchDone">
            <!-- 搜索历史：localStorage 持久化，最新在前。收起时只露两行，
                 超出才出现展开按钮（参考稿的折叠交互）。
                 管理态（参考稿）：标题右侧换成「清空 / 完成」，每个 chip 内嵌 ×，
                 点 chip 本体等同删除 —— 编辑态下误触搜索比误删更烦人。 -->
            <section v-if="history.length" class="csp-sec">
              <div class="csp-sec-head">
                <h2>搜索历史</h2>
                <div v-if="historyEditing" class="csp-head-actions">
                  <button type="button" class="csp-text-btn is-muted" @click="clearHistory">清空</button>
                  <button type="button" class="csp-text-btn" @click="historyEditing = false">完成</button>
                </div>
                <button
                  v-else
                  type="button"
                  class="csp-text-btn"
                  @click="historyEditing = true"
                >管理</button>
              </div>
              <div
                ref="historyRef"
                class="csp-history"
                :class="{ 'is-collapsed': !historyExpanded }"
              >
                <div
                  v-for="h in history"
                  :key="h"
                  class="csp-chip"
                  :class="{ 'is-editing': historyEditing }"
                >
                  <button
                    type="button"
                    class="csp-chip-text"
                    :aria-label="historyEditing ? `删除历史：${h}` : `搜索：${h}`"
                    @click="historyEditing ? removeHistory(h) : quickSearch(h)"
                  >{{ h }}</button>
                  <button
                    v-if="historyEditing"
                    type="button"
                    class="csp-chip-del"
                    aria-label="删除该条历史"
                    @click="removeHistory(h)"
                  >
                    <el-icon :size="14"><Close /></el-icon>
                  </button>
                </div>
                <button
                  v-if="historyOverflow"
                  type="button"
                  class="csp-chip csp-chip-toggle"
                  :aria-label="historyExpanded ? '收起搜索历史' : '展开搜索历史'"
                  @click="historyExpanded = !historyExpanded"
                >
                  <el-icon :size="14"><ArrowUp v-if="historyExpanded" /><ArrowDown v-else /></el-icon>
                </button>
              </div>
            </section>

            <!-- 搜索发现：从当前资讯池随机抽标题，两列排布；「刷新」重抽一批。
                 占位符也用第一条发现 —— 搜索框里始终有个「可以搜什么」的活例子。 -->
            <section v-if="discovery.length" class="csp-sec">
              <div class="csp-sec-head">
                <h2>搜索发现</h2>
                <button
                  type="button"
                  class="csp-head-btn"
                  :class="{ 'is-spinning': discoverySpinning }"
                  aria-label="换一批发现"
                  @click="refreshDiscovery"
                >
                  <el-icon :size="14"><RefreshRight /></el-icon>
                  <span>刷新</span>
                </button>
              </div>
              <div class="csp-discovery">
                <button
                  v-for="(d, i) in discovery"
                  :key="d.url + i"
                  type="button"
                  class="csp-disc-item"
                  :title="d.title"
                  @click="quickSearch(d.title)"
                >{{ d.title }}</button>
              </div>
            </section>

            <!-- 热榜：首格「校园热榜」是全站总榜，其余为各栏目分榜（口径与信息流 Tab 一致）。
                 排序权重 = 评论×3 + 浏览，没互动过的按日期序兜底（池子本身已按日期倒序，
                 稳定排序保住这个顺序）。前 3 名彩色序号，有图出缩略图、无图出「#」灰块。 -->
            <section class="csp-sec">
              <nav class="csp-hot-tabs" role="tablist" aria-label="热榜分类">
                <button
                  v-for="t in HOT_TABS"
                  :key="t.key"
                  type="button"
                  role="tab"
                  class="csp-hot-tab"
                  :class="{ 'is-active': hotTab === t.key }"
                  :aria-selected="hotTab === t.key"
                  @click="hotTab = t.key"
                >{{ t.label }}</button>
              </nav>
              <ol v-if="hotList.length" class="csp-hot-list">
                <li v-for="(it, idx) in hotList" :key="it.url">
                  <button type="button" class="csp-hot-item" @click="openItem(it)">
                    <span class="csp-rank" :class="`rank-${idx + 1}`">{{ idx + 1 }}</span>
                    <span v-if="it.image_url" class="csp-hot-thumb">
                      <img :src="it.image_url" loading="lazy" alt="" />
                    </span>
                    <span v-else class="csp-hot-hash" aria-hidden="true">#</span>
                    <span class="csp-hot-title">{{ it.title }}</span>
                    <span v-if="isHot(it)" class="csp-tag is-hot">热</span>
                    <span v-else-if="isNew(it)" class="csp-tag is-new">新</span>
                  </button>
                </li>
              </ol>
              <p v-else class="csp-empty">暂无上榜内容</p>
            </section>
          </template>

          <!-- 搜索结果：① 校园资讯（前端过滤，不发请求）。 -->
          <template v-else>
            <section class="csp-sec">
              <div class="csp-sec-head">
                <h2>校园资讯（{{ newsHits.length }}）</h2>
              </div>
              <div v-if="newsHits.length" class="csp-result-list">
                <button
                  v-for="h in newsHits"
                  :key="h.url"
                  type="button"
                  class="csp-result"
                  @click="openItem(h)"
                >
                  <span class="csp-result-title">{{ h.title }}</span>
                  <span class="csp-result-meta">{{ h.sourceLabel }}<template v-if="h.dateLabel"> · {{ h.dateLabel }}</template></span>
                </button>
              </div>
              <p v-else class="csp-empty">没有找到相关资讯</p>
            </section>

            <!-- ② 知识库兜底：仅资讯 0 命中时才检索（与原对话框同一层逻辑）。
                 游客没有检索权限，给登录引导。 -->
            <section v-if="!newsHits.length" class="csp-sec">
              <div class="csp-sec-head">
                <h2>知识库{{ knowledgeLoading ? '' : `（${knowledgeHits.length}）` }}</h2>
              </div>
              <p v-if="knowledgeLoading" class="csp-empty">检索中…</p>
              <template v-else-if="knowledgeHits.length">
                <div class="csp-result-list">
                  <div v-for="(h, i) in knowledgeHits" :key="i" class="csp-result is-static">
                    <span class="csp-result-title">{{ h.question || h.content || '未命名' }}</span>
                    <span class="csp-result-meta">{{ h.category || (h.type === 'qa' ? '问答' : '文档') }}</span>
                  </div>
                </div>
              </template>
              <p v-else-if="isGuestMode()" class="csp-empty">
                知识库检索需要登录，<a href="javascript:;" class="csp-link" @click.prevent="onGuestLogin">去登录</a>
              </p>
              <p v-else class="csp-empty">知识库中也没有找到相关内容</p>
            </section>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts">
/** 父页准备好的可搜条目（去公共前缀、来源已转中文、互动计数已并入）。
 * 父页是唯一所有者：来源口径（隐藏栏目 / 去重 / 排序）都在 CampusPage 里做，
 * 本组件只消费，不重复维护一套过滤规则。 */
export interface SearchPoolItem {
  title: string
  url: string
  /** 来源栏目 key（jwc_tzgg …），热榜分榜与详情页跳转都用它 */
  source: string
  sourceLabel: string
  /** 原始日期串（2026-10-15 / 2026.04.01 / null），「新」标记用它解析 */
  date: string | null
  /** 展示用日期（MM-DD），解析不出为空串 */
  dateLabel: string
  image_url: string | null
  comment_count: number
  view_count: number
}
</script>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  ArrowLeft, ArrowDown, ArrowUp, CircleCloseFilled,
  Close, RefreshRight, Search,
} from '@element-plus/icons-vue'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
import { isGuestMode } from '@/utils/guest'
import { promptLogin } from '@/utils/loginGate'

const props = defineProps<{ items: SearchPoolItem[] }>()
const emit = defineEmits<{
  (e: 'closed'): void
  (e: 'open', url: string, title: string, source: string): void
}>()

/* ==================== 打开 / 关闭 ====================
   与 ArticleDetailPage 同一套约定：父页 v-if 挂载即打开（onMounted 置 visible），
   close() 播退场动画，after-leave 才通知父页卸载。 */

const visible = ref(false)

function close() {
  visible.value = false
}

/* ==================== 搜索框 ==================== */

const inputRef = ref<HTMLInputElement | null>(null)
const keyword = ref('')
const searchDone = ref(false)
const newsHits = ref<SearchPoolItem[]>([])
const knowledgeHits = ref<KnowledgeHit[]>([])
const knowledgeLoading = ref(false)

/** 占位符用第一条「搜索发现」：搜索框里始终有一个可搜的真实例子（参考稿同款） */
const placeholder = computed(() => discovery.value[0]?.title || '搜索校园资讯，如：图书馆、放假……')

/** 本页资讯命中：纯前端按标题过滤（池子已按移动端口径去过高教信息 / 系统入口） */
function filterNews(kw: string): SearchPoolItem[] {
  const k = kw.toLowerCase()
  return props.items.filter(i => i.title.toLowerCase().includes(k))
}

async function loadKnowledge(kw: string) {
  // 本页已命中就不再打后端：两层语义不同，资讯命中时知识库不给结果也不算缺
  if (newsHits.value.length || isGuestMode()) return
  knowledgeLoading.value = true
  try {
    knowledgeHits.value = await searchKnowledge(kw)
  } catch {
    knowledgeHits.value = []
  } finally {
    knowledgeLoading.value = false
  }
}

function runSearch() {
  const kw = keyword.value.trim()
  if (!kw) {
    searchDone.value = false
    return
  }
  if (keyword.value !== kw) keyword.value = kw
  newsHits.value = filterNews(kw)
  searchDone.value = true
  saveHistory(kw)
  void loadKnowledge(kw)
}

function quickSearch(kw: string) {
  keyword.value = kw
  runSearch()
  inputRef.value?.blur()
}

function clearKeyword() {
  keyword.value = ''
  searchDone.value = false
  newsHits.value = []
  knowledgeHits.value = []
  inputRef.value?.focus()
}

// 关键词被清空（键盘删除 / clearable）＝回到发现页，旧结果留着会让人以为还在搜
watch(keyword, v => {
  if (!v.trim() && searchDone.value) {
    searchDone.value = false
    newsHits.value = []
    knowledgeHits.value = []
  }
})

function openItem(it: SearchPoolItem) {
  emit('open', it.url, it.title, it.source)
}

function onGuestLogin() {
  void promptLogin('检索全校知识库')
}

/* ==================== 搜索历史 ==================== */

const HISTORY_KEY = 'wispath_campus_search_history'
const HISTORY_MAX = 20

const history = ref<string[]>(loadHistory())
const historyRef = ref<HTMLElement | null>(null)
const historyExpanded = ref(false)
const historyOverflow = ref(false)
/** 管理态：chip 内嵌 ×、标题右侧换「清空 / 完成」（参考稿） */
const historyEditing = ref(false)

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string').slice(0, HISTORY_MAX) : []
  } catch {
    return []
  }
}

function persistHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
  } catch { /* 隐私模式等存不进去就算了，本次会话内仍可用 */ }
}

function saveHistory(kw: string) {
  history.value = [kw, ...history.value.filter(h => h !== kw)].slice(0, HISTORY_MAX)
  persistHistory()
}

/** 单条删除（管理态）。删空即无历史可管，顺手退出管理态 */
function removeHistory(kw: string) {
  history.value = history.value.filter(h => h !== kw)
  if (!history.value.length) historyEditing.value = false
  persistHistory()
}

/** 清空全量（管理态里的「清空」）。已先进管理态＝一次明确的意图，不再叠二次确认弹窗 */
function clearHistory() {
  history.value = []
  historyExpanded.value = false
  historyEditing.value = false
  try {
    localStorage.removeItem(HISTORY_KEY)
  } catch { /* 忽略 */ }
}

/** 收起态量一次有没有超出两行：超了才出现展开按钮。
 * 展开态不再量（clientHeight 追平 scrollHeight 会误判成没溢出），
 * 收起按钮由展开时记住的 historyOverflow 兜住。 */
function measureHistory() {
  if (historyExpanded.value) return
  const el = historyRef.value
  if (!el) return
  historyOverflow.value = el.scrollHeight > el.clientHeight + 2
}

watch(() => history.value.length, len => {
  historyExpanded.value = false
  if (!len) historyEditing.value = false
  void nextTick(measureHistory)
})

// 进/出管理态时 chip 宽度会变（多出 ×），可能多折一行，重量一次才不至于溢出却没展开按钮
watch(historyEditing, () => { void nextTick(measureHistory) })

/* ==================== 搜索发现 ==================== */

const DISCOVERY_COUNT = 8
const discovery = ref<SearchPoolItem[]>([])
const discoverySpinning = ref(false)

function shufflePick() {
  const arr = [...props.items]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  discovery.value = arr.slice(0, DISCOVERY_COUNT)
}

function refreshDiscovery() {
  shufflePick()
  // 图标转一圈即可，不用等任何真请求：换一批是纯本地操作
  discoverySpinning.value = true
  window.setTimeout(() => { discoverySpinning.value = false }, 600)
}

// 资讯池异步到位（首屏缓存未命中时）后，发现区还是空的才补抽，不打着用户正在看的批次
watch(() => props.items.length, () => {
  if (!discovery.value.length) shufflePick()
})

/* ==================== 热榜 ==================== */

/** 首格是全站总榜，其余与信息流 Tab 同口径（不含「推荐」与「关注」这类聚合页、也不含已下线栏目） */
const HOT_TABS = [
  { key: 'all', label: '校园热榜' },
  { key: 'jwc_jxdt', label: '教学动态' },
  { key: 'jwc_tzgg', label: '通知公告' },
  { key: 'jwc_jxjs', label: '教学建设' },
  { key: 'college_news', label: '学院动态' },
  { key: 'library', label: '图书馆' },
] as const

const hotTab = ref<string>('all')

/** 评论权重 ×3：一条评论比一次浏览更能说明「大家在聊」。
 * 池子已按日期倒序，稳定排序让无互动条目保持「最新优先」的兜底顺序。 */
const hotList = computed<SearchPoolItem[]>(() => {
  const pool = hotTab.value === 'all'
    ? props.items
    : props.items.filter(i => i.source === hotTab.value)
  return [...pool]
    .sort((a, b) => (b.comment_count * 3 + b.view_count) - (a.comment_count * 3 + a.view_count))
    .slice(0, 10)
})

/** 「热」：互动量到了一个值得点进去看的量级（阈值故意放低，校园资讯基数小） */
function isHot(it: SearchPoolItem) {
  return it.comment_count >= 3 || it.view_count >= 50
}

/** 「新」：两天内发布的资讯。后端日期有 2026-10-15 与 2026.04.01 两种写法，统一正则解析 */
function isNew(it: SearchPoolItem) {
  const m = (it.date || '').match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/)
  if (!m) return false
  const t = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime()
  return Date.now() - t < 48 * 3600 * 1000
}

/* ==================== 生命周期 ====================
   body 滚动锁归本页所有。但它不是唯一会碰 body.overflow 的层：盖在本页上的
   资讯详情子页关闭时会把它复位成 ''，而本页还开着 —— 用 MutationObserver 盯住，
   只要本页可见就被复位就立刻锁回去，比在每个覆盖层的关闭回调里反向补救可靠。 */

let bodyLockObserver: MutationObserver | null = null

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && visible.value) close()
}

watch(visible, v => {
  document.body.style.overflow = v ? 'hidden' : ''
})

onMounted(() => {
  visible.value = true
  shufflePick()
  void nextTick(measureHistory)
  window.addEventListener('keydown', onKeydown)
  bodyLockObserver = new MutationObserver(() => {
    if (visible.value && document.body.style.overflow !== 'hidden') {
      document.body.style.overflow = 'hidden'
    }
  })
  bodyLockObserver.observe(document.body, { attributes: true, attributeFilter: ['style'] })
  // 等滑入动画播完再聚焦：iOS 上动画中途弹键盘会把正在滑入的页面顶得跳动
  window.setTimeout(() => inputRef.value?.focus(), 350)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  bodyLockObserver?.disconnect()
  bodyLockObserver = null
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* ================= 根容器：与 .adp-root 同一套覆盖式子页骨架 =================
   进出场动画统一走全局 .subpage（styles/animations.css，keyframes 驱动），本页不再自带。 */
.csp-root {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  flex-direction: column;
  background: #fff;
  color: #1d2129;
  -webkit-tap-highlight-color: transparent;
  overflow: hidden;
}

/* ================= 顶栏 ================= */
.csp-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: calc(8px + env(safe-area-inset-top, 0px)) 14px 8px;
  flex-shrink: 0;
}
.csp-back {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: none;
  color: #1d2129;
  padding: 0;
  cursor: pointer;
}
.csp-field {
  flex: 1;
  min-width: 0;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-radius: 18px;
  background: #f2f3f5;
}
.csp-field-icon {
  color: #9ca0a8;
  flex-shrink: 0;
}
.csp-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 16px; /* ≥16px，避免 iOS 聚焦自动放大 */
  color: #1d2129;
  height: 100%;
}
.csp-input::placeholder { color: #9ca0a8; }
.csp-input::-webkit-search-cancel-button { display: none; }
.csp-clear {
  border: 0;
  background: none;
  padding: 0;
  color: #b0b3b8;
  display: flex;
  cursor: pointer;
}

/* ================= 滚动区与公共段落 ================= */
.csp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
  padding: 4px 16px calc(40px + env(safe-area-inset-bottom, 0px));
}
.csp-scroll::-webkit-scrollbar { display: none; }
.csp-sec { margin-top: 22px; }
.csp-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.csp-sec-head h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #111;
}
.csp-head-btn {
  display: flex;
  align-items: center;
  gap: 3px;
  border: 0;
  background: none;
  padding: 2px;
  color: #8a8f99;
  font-size: 13px;
  cursor: pointer;
}
.csp-head-btn.is-spinning svg {
  animation: csp-spin 0.6s ease;
}
/* 标题右侧的纯文字动作（管理 / 清空 / 完成），参考稿：次级动作灰、主次动作深 */
.csp-head-actions {
  display: flex;
  align-items: center;
  gap: 22px;
}
.csp-text-btn {
  border: 0;
  background: none;
  padding: 4px 0;
  font-size: 14px;
  color: #1d2129;
  cursor: pointer;
}
.csp-text-btn.is-muted { color: #9ca0a8; }
@keyframes csp-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.csp-empty {
  margin: 6px 0;
  font-size: 13px;
  color: #9ca0a8;
}
.csp-link {
  color: var(--el-color-primary, #409eff);
  text-decoration: none;
}

/* ================= 搜索历史 ================= */
.csp-history {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.csp-history.is-collapsed {
  /* 两行 chips（34px 行高 + 8px 间距），溢出部分先藏住 */
  max-height: 76px;
  overflow: hidden;
}
.csp-chip {
  height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  background: #f2f3f5;
  color: #333;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.csp-chip-text {
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  color: inherit;
  max-width: 190px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.csp-chip.is-editing {
  padding-right: 10px;
}
.csp-chip.is-editing .csp-chip-text { cursor: default; }
.csp-chip-del {
  border: 0;
  background: none;
  padding: 0;
  margin-left: 2px;
  display: flex;
  align-items: center;
  color: #a5a9b3;
  cursor: pointer;
}
.csp-chip-toggle {
  width: 34px;
  padding: 0;
  justify-content: center;
  background: #fff;
  border: 1px solid #e5e6eb;
  color: #8a8f99;
  cursor: pointer;
}

/* ================= 搜索发现 ================= */
.csp-discovery {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 16px;
  row-gap: 16px;
}
.csp-disc-item {
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  text-align: left;
  font-size: 14px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}

/* ================= 热榜 ================= */
.csp-hot-tabs {
  display: flex;
  gap: 18px;
  overflow-x: auto;
  scrollbar-width: none;
  margin-bottom: 6px;
}
.csp-hot-tabs::-webkit-scrollbar { display: none; }
.csp-hot-tab {
  flex-shrink: 0;
  border: 0;
  background: none;
  padding: 6px 0;
  font-size: 15px;
  color: #333;
  cursor: pointer;
}
.csp-hot-tab.is-active {
  color: #ff4d3a;
  font-weight: 700;
}
.csp-hot-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.csp-hot-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border: 0;
  background: none;
  text-align: left;
  cursor: pointer;
}
.csp-rank {
  width: 24px;
  flex-shrink: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #c0c4cc;
}
.csp-rank.rank-1 { color: #fe2c55; }
.csp-rank.rank-2 { color: #ff6a2b; }
.csp-rank.rank-3 { color: #ff9f2b; }
.csp-hot-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: #f2f3f5;
}
.csp-hot-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.csp-hot-hash {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 6px;
  background: #f2f3f5;
  color: #c0c4cc;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.csp-hot-title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  color: #1d2129;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.csp-tag {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 1;
  padding: 3px 5px;
  border-radius: 4px;
}
.csp-tag.is-hot {
  color: #ff4d3a;
  background: #ffeeec;
}
.csp-tag.is-new {
  color: #0fae6d;
  background: #e8f8f0;
}

/* ================= 搜索结果 ================= */
.csp-result-list { margin-top: -4px; }
.csp-result {
  display: block;
  width: 100%;
  padding: 12px 0;
  border: 0;
  border-bottom: 1px solid #f2f3f5;
  background: none;
  text-align: left;
  cursor: pointer;
}
.csp-result.is-static { cursor: default; }
.csp-result-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  font-size: 15px;
  line-height: 1.45;
  color: #1d2129;
}
.csp-result-meta {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #9ca0a8;
}
</style>
