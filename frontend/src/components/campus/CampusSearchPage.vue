<template>
  <!-- 覆盖式全屏子页：骨架 / 进出场动画 / Esc / 滚动锁全部由 SubPageShell 提供
       （动画本体在 styles/subpage-transition.css）。只在移动端挂载
       （父页 openSearch 分流），桌面端继续用对话框搜索。
       close-on-esc 关掉：本页 Esc 有分级语义（先退搜索结果页、再关整个搜索页），
       统一交给脚本里的 onKeydown。 -->
  <SubPageShell
    v-model="visible"
    aria-label="搜索校园资讯"
    :close-on-esc="false"
    @after-leave="emit('closed')"
  >
    <div class="csp-root">
      <!-- ① 顶栏：返回 + 圆角搜索框 + 「搜索」文字按钮。
           键盘搜索键（enterkeyhint=search）与右侧按钮是同一动作：都走 runSearch()。 -->
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
        <button type="button" class="csp-go" @click="runSearch">搜索</button>
      </header>

      <!-- ② 第二层：搜索页（历史 / 发现 / 热榜）。
           这一层永远是「搜索页」本身，提交搜索不会把它替换掉 ——
           结果页是独立第三层盖在上面，返回一层回到这里，关键词与历史都还在。 -->
      <div class="csp-scroll">
        <!-- 搜索历史：localStorage 持久化，最新在前。收起时只露两行，
             超出才出现展开按钮（参考稿的折叠交互）。
             默认态右侧是垃圾桶入口；点进管理态换成参考稿的「清空 / 完成」，
             每个 chip 内嵌 ×，点 chip 本体等同删除 —— 编辑态下误触搜索比误删更烦人。 -->
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
              class="csp-head-btn"
              aria-label="管理搜索历史"
              @click="historyEditing = true"
            >
              <el-icon :size="16"><Delete /></el-icon>
            </button>
          </div>
          <div
            ref="historyRef"
            class="csp-history"
            :class="{ 'is-collapsed': !historyExpanded }"
          >
            <template v-for="(h, i) in history" :key="h">
              <!-- 折叠态只渲染前 N 条（N 由 measureHistory 量出）。
                   超出两条线的标签**不参与布局**，而不是靠 max-height 裁掉，
                   这样箭头作为流内元素自然排在最后一个可见标签之后，
                   永远不会出现「箭头压在某个标签身上」这种重叠。 -->
              <div
                v-if="historyExpanded || i < visibleCount"
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
            </template>

            <!-- 展开 / 收起箭头：始终是流内最后一个元素，位置由 flex 折行自然决定 -->
            <button
              v-if="historyOverflow"
              type="button"
              class="csp-chip csp-chip-toggle"
              :aria-label="historyExpanded ? '收起搜索历史' : '展开搜索历史'"
              @click="historyExpanded = !historyExpanded"
            >
              <el-icon :size="20"><ArrowUp v-if="historyExpanded" /><ArrowDown v-else /></el-icon>
            </button>
          </div>
        </section>

        <!-- 搜索发现：从当前资讯池随机抽标题，两列排布；「刷新」重抽一批。
             搜索框的占位符取的是**热度最高**的那条帖子，不从这里取 ——
             换一批是发现区的动作，不该顺带改掉输入框里给人看的提示。 -->
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
             稳定排序保住这个顺序）。前 3 名彩色序号，有图出缩略图、无图出「#」灰块。
             切换分类：短下划线滑块平移跟手，榜单整块退场再逐条上浮入场（见下方样式）。 -->
        <section class="csp-sec">
          <nav ref="hotTabNavRef" class="csp-hot-tabs" role="tablist" aria-label="热榜分类">
            <button
              v-for="(t, i) in HOT_TABS"
              :key="t.key"
              :ref="el => setHotTabRef(el, i)"
              type="button"
              role="tab"
              class="csp-hot-tab"
              :class="{ 'is-active': hotTab === t.key }"
              :aria-selected="hotTab === t.key"
              @click="pickHotTab(t.key, i)"
            >{{ t.label }}</button>
            <!-- 指示器：绝对定位，所以不占 flex 槽位；位置由 measureHotInk() 按选中项实测 -->
            <span class="csp-hot-ink" :style="hotInkStyle" aria-hidden="true"></span>
          </nav>
          <Transition name="csp-swap" mode="out-in">
            <ol v-if="hotList.length" :key="hotTab" class="csp-hot-list">
              <li
                v-for="(it, idx) in hotList"
                :key="it.url"
                class="csp-hot-row"
                :style="{ animationDelay: `${Math.min(idx, 9) * 16}ms` }"
              >
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
          </Transition>
        </section>
      </div>

      <!-- ③ 第三层：搜索结果页。盖在搜索页之上，自己带一条顶栏（返回 + 可继续编辑的
           关键词框），返回只退这一层 —— 页面栈是「主页面 → 搜索页 → 结果页」。
           版式对齐社区搜索页：顶栏 → 分类翻页条（综合 / 资讯 / 知识库 + 筛选）→ 无分隔线信息流。
           帖子条目内部的展示（标题 + 来源 · 日期）保持原样，本次只换外框。
           进出场用同一套滑入动画，但留在本页 DOM 里叠着（SubPageShell 的 teleport=false）：
           几何由 .csp-result-page 自己给（absolute inset:0），父层已锁滚动，这一层不再锁。 -->
      <SubPageShell
        v-model="searchDone"
        :teleport="false"
        :z-index="2"
        role="region"
        aria-label="搜索结果"
        :lock-scroll="false"
        :close-on-esc="false"
      >
        <div class="csp-result-page">
          <header class="csp-head csp-head--result">
            <button type="button" class="csp-back" aria-label="返回搜索页" @click="backToSearch">
              <el-icon :size="22"><ArrowLeft /></el-icon>
            </button>
            <div class="csp-field">
              <el-icon class="csp-field-icon" :size="16"><Search /></el-icon>
              <input
                ref="resultInputRef"
                v-model="keyword"
                class="csp-input"
                type="search"
                enterkeyhint="search"
                placeholder="搜索校园资讯"
                @keyup.enter="runSearch"
              />
              <!-- 结果页的 × 只清空输入框，不退层：结果留在这里，等用户敲下一个词 -->
              <button
                v-if="keyword"
                type="button"
                class="csp-clear"
                aria-label="清空关键词"
                @click="clearResultKeyword"
              >
                <el-icon :size="15"><CircleCloseFilled /></el-icon>
              </button>
            </div>
            <button type="button" class="csp-go" @click="runSearch">搜索</button>
          </header>

          <!-- 分类条：左侧 Tab 可横向滚动，右侧「筛选」钉在右边缘。
               语义仍是「结果分组」——综合＝资讯优先、资讯＝只过滤资讯、知识库＝只查知识库。 -->
          <nav class="csp-rtabs" role="tablist" aria-label="搜索结果分类">
            <div class="csp-rtabs-scroll">
              <button
                v-for="t in RESULT_TABS"
                :key="t.key"
                type="button"
                role="tab"
                class="csp-rtab"
                :class="{ 'is-active': resultTab === t.key }"
                :aria-selected="resultTab === t.key"
                @click="resultTab = t.key"
              >{{ t.label }}</button>
            </div>
            <button
              type="button"
              class="csp-filter"
              :class="{ 'is-open': filterOpen }"
              :aria-expanded="filterOpen"
              aria-controls="csp-filter-panel"
              @click="filterOpen = !filterOpen"
            >
              <el-icon :size="14"><Filter /></el-icon>
              <span>筛选</span>
              <el-icon :size="12" class="csp-filter-caret"><ArrowDown /></el-icon>
            </button>
          </nav>

          <!-- 筛选面板：来源栏目（与热榜分榜同一套口径）。选具体栏目会自动切到「资讯」，
               因为栏目只作用于资讯流；知识库不分栏目。 -->
          <Transition name="csp-drop">
            <div v-if="filterOpen" id="csp-filter-panel" class="csp-filter-panel">
              <button
                v-for="s in SOURCE_FILTERS"
                :key="s.key"
                type="button"
                class="csp-fchip"
                :class="{ 'is-active': sourceFilter === s.key }"
                @click="pickSource(s.key)"
              >{{ s.label }}</button>
            </div>
          </Transition>

          <div class="csp-scroll csp-feed-scroll">
            <!-- ① 资讯流（前端过滤，不发请求）。综合 tab 下资讯 0 命中时让位给知识库兜底。 -->
            <template v-if="resultTab === 'news' || (resultTab === 'all' && visibleNews.length)">
              <div class="csp-feed">
                <button
                  v-for="h in visibleNews"
                  :key="h.url"
                  type="button"
                  class="csp-result"
                  @click="openItem(h)"
                >
                  <span class="csp-result-title">{{ h.title }}</span>
                  <span class="csp-result-meta">{{ h.sourceLabel }}<template v-if="h.dateLabel"> · {{ h.dateLabel }}</template></span>
                </button>
              </div>
              <p v-if="!visibleNews.length" class="csp-empty is-block">
                {{ sourceFilter === 'all' ? '没有找到相关资讯' : '当前筛选下没有结果，换个栏目看看' }}
              </p>
            </template>

            <!-- ② 知识库：知识库 tab，或综合 tab 下的兜底（与原来同一层逻辑）。
                 游客没有检索权限，给登录引导。 -->
            <template v-else>
              <p v-if="knowledgeLoading" class="csp-empty is-block">检索中…</p>
              <div v-else-if="knowledgeHits.length" class="csp-feed">
                <div v-for="(h, i) in knowledgeHits" :key="i" class="csp-result is-static">
                  <span class="csp-result-title">{{ h.question || h.content || '未命名' }}</span>
                  <span class="csp-result-meta">{{ h.category || (h.type === 'qa' ? '问答' : '文档') }}</span>
                </div>
              </div>
              <p v-else-if="isGuestMode()" class="csp-empty is-block">
                知识库检索需要登录，<a href="javascript:;" class="csp-link" @click.prevent="onGuestLogin">去登录</a>
              </p>
              <p v-else class="csp-empty is-block">知识库中也没有找到相关内容</p>
            </template>
          </div>
        </div>
      </SubPageShell>
    </div>
  </SubPageShell>
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

/** 上一次进页面用过的占位符标题。放模块作用域而不是组件内：本页每次打开都是重新挂载，
 * 这个「上次是谁」得活得比实例久，才能在连续进页面时避开重复。 */
let lastPlaceholderTitle = ''
</script>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  ArrowLeft, ArrowDown, ArrowUp, CircleCloseFilled,
  Close, Delete, Filter, RefreshRight, Search,
} from '@element-plus/icons-vue'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
// 覆盖式子页外壳：落位 + 进出场动画 + Esc + 滚动锁（与 styles/subpage-transition.css 配套）
import SubPageShell from '@/components/common/SubPageShell.vue'
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
/** 当前这批知识库结果对应哪个关键词（三个 tab 共用，切 tab 不重复请求） */
const kbLoadedFor = ref('')
/** 请求序号：换词后旧请求才回包时直接丢弃，不让它盖掉新词的结果 */
let knowledgeReqId = 0

/** 占位符兜底文案：资讯池还没到位（或一条帖子都没有）时才显示。
 * 正常情况下输入框里显示的是「热度最高的那条帖子标题」——见「热榜」段的 placeholderFull。
 * 实际渲染值由 fitPlaceholder() 按可用宽度裁好（窄屏补「…」）。 */
const PLACEHOLDER_FALLBACK = '搜索校园资讯，如：放假通知'
const placeholder = ref(PLACEHOLDER_FALLBACK)
const ELLIPSIS = '…'
let measureCtx: CanvasRenderingContext2D | null = null
let fitRetryTimer = 0

/** 资讯标题长达 20+ 字，远超胶囊宽度，原生 input 会在右边缘把字硬切成半个。
 * `::placeholder { text-overflow: ellipsis }` 在 Chromium 上不生效（实测无效），
 * 所以自己量宽做截断，超出补「…」。 */
function fitPlaceholder() {
  const el = inputRef.value
  // 布局还没到位（滑入动画首帧）：这时 clientWidth 是 0，绝不能退回全文 ——
  // 那正是「半个字」的来源。短暂重试，等有宽度了再量。
  if (!el || el.clientWidth < 40) {
    if (!fitRetryTimer) {
      fitRetryTimer = window.setTimeout(() => {
        fitRetryTimer = 0
        fitPlaceholder()
      }, 120)
    }
    return
  }
  const full = placeholderFull.value
  if (!measureCtx) measureCtx = document.createElement('canvas').getContext('2d')
  if (!measureCtx) return
  const cs = window.getComputedStyle(el)
  measureCtx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`
  // 留 2px 呼吸位：正好压边的字看着像被切掉
  const avail = el.clientWidth - 2
  if (measureCtx.measureText(full).width <= avail) {
    placeholder.value = full
    return
  }
  // 二分找「最长能放下的前缀 + …」，逐字裁比按字数估更贴合实际字宽
  let lo = 0
  let hi = full.length
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2)
    if (measureCtx.measureText(full.slice(0, mid) + ELLIPSIS).width <= avail) lo = mid
    else hi = mid - 1
  }
  placeholder.value = lo > 0 ? full.slice(0, lo) + ELLIPSIS : ELLIPSIS
}

/** 本页资讯命中：纯前端按标题过滤（池子已按移动端口径去过高教信息 / 系统入口） */
function filterNews(kw: string): SearchPoolItem[] {
  const k = kw.toLowerCase()
  return props.items.filter(i => i.title.toLowerCase().includes(k))
}

async function loadKnowledge(kw: string) {
  // 同一个词只打一次后端：结果页的三个 tab 共用这批数据，来回切 tab 不该重复请求
  if (isGuestMode() || kbLoadedFor.value === kw) return
  const reqId = ++knowledgeReqId
  kbLoadedFor.value = kw
  knowledgeLoading.value = true
  try {
    const hits = await searchKnowledge(kw)
    if (reqId === knowledgeReqId) knowledgeHits.value = hits
  } catch {
    if (reqId === knowledgeReqId) knowledgeHits.value = []
  } finally {
    if (reqId === knowledgeReqId) knowledgeLoading.value = false
  }
}

function runSearch() {
  const kw = keyword.value.trim()
  // 空词不提交、也不退层：在结果页清空后误按回车只是没反应，不会被弹回上一页
  if (!kw) return
  if (keyword.value !== kw) keyword.value = kw
  const firstOpen = !searchDone.value
  newsHits.value = filterNews(kw)
  // 换词＝开一轮新搜索：知识库结果与来源筛选都按新词重来，免得看到上一批的残影
  kbLoadedFor.value = ''
  knowledgeReqId += 1
  knowledgeHits.value = []
  knowledgeLoading.value = false
  sourceFilter.value = 'all'
  searchDone.value = true
  saveHistory(kw)
  // 首次进入结果页：收起键盘，把结果让出来（结果页顶栏可以再点开继续改词）
  if (firstOpen) (document.activeElement as HTMLElement | null)?.blur()
  // 综合 tab 沿用原来的兜底口径（资讯 0 命中才查知识库）；停在知识库 tab 时则必须查
  if (!newsHits.value.length || resultTab.value === 'kb') void loadKnowledge(kw)
}

function quickSearch(kw: string) {
  keyword.value = kw
  runSearch()
  inputRef.value?.blur()
}

/** 结果页返回：只退这一层，回到搜索页。
 * 退回来＝这一轮搜索结束，输入框与结果数据一并清掉（历史、发现、热榜保留），
 * 搜索页回到「刚打开」的空白状态；想看上一轮结果就再点一次历史标签。 */
function backToSearch() {
  searchDone.value = false
  keyword.value = ''
  newsHits.value = []
  knowledgeHits.value = []
  kbLoadedFor.value = ''
  knowledgeLoading.value = false
  knowledgeReqId += 1
  // 下次进来从「综合」看起
  resultTab.value = 'all'
  filterOpen.value = false
  sourceFilter.value = 'all'
  // 退层后焦点不在输入框：搜索页是浏览态，别把键盘顶起来
  ;(document.activeElement as HTMLElement | null)?.blur()
}

/** 搜索页顶栏的 ×：清空输入并留在搜索页 */
function clearKeyword() {
  keyword.value = ''
  newsHits.value = []
  knowledgeHits.value = []
  kbLoadedFor.value = ''
  knowledgeLoading.value = false
  knowledgeReqId += 1
  inputRef.value?.focus()
}

const resultInputRef = ref<HTMLInputElement | null>(null)

/** 结果页顶栏的 ×：**只清空输入框，不退层**。
 * 之前两点共用一个 clearKeyword()，那里会把 searchDone 置假 ——
 * 于是结果页点 × 等于点了返回。现在结果留在页面上（对应上一次提交的词），
 * 用户可以敲下一个词再提交。 */
function clearResultKeyword() {
  keyword.value = ''
  resultInputRef.value?.focus()
}

function openItem(it: SearchPoolItem) {
  emit('open', it.url, it.title, it.source)
}

function onGuestLogin() {
  void promptLogin('检索全校知识库')
}

/* ==================== 搜索历史 ==================== */

const HISTORY_KEY = 'wispath_campus_search_history'
/** 上限放宽到 50 条：折叠态只露两行，存 20 条时多搜几次就把早的挤掉了，用户回头找不回来 */
const HISTORY_MAX = 50

const history = ref<string[]>(loadHistory())
const historyRef = ref<HTMLElement | null>(null)
const historyExpanded = ref(false)
const historyOverflow = ref(false)
/** 折叠态最多渲染几条；Infinity = 全部渲染（展开态，以及「测量中」的瞬间） */
const visibleCount = ref(Number.POSITIVE_INFINITY)
/** 历史区自身的尺寸观察器：折行位置只要变了就重量。
 * 光靠 window.resize 不够 —— 页面滑入、字体替换、进出管理态都可能改宽高却不触发 resize。
 * 上一版箭头错位就是「测完这一帧宽度又变了」。 */
let historyRO: ResizeObserver | null = null
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

/** 折叠态两行的可视高度：两个 chip 行高 + 一个行间距（与 CSS 的 max-height 对齐） */
const CHIP_ROW_H = 31
const CHIP_GAP = 8
const TWO_ROWS_H = CHIP_ROW_H * 2 + CHIP_GAP
/** 展开箭头的宽度，与 CSS 的 .csp-chip-toggle 一致（31px 正方形）；
 *  算「最后一行还剩不剩它的位置」用 */
const TOGGLE_W = 31

/** 测量的并发控制：mount / 字体到位 / resize / ResizeObserver / 历史变化 可能连着触发。
 * 测量是「先临时全展开、再收起」的两步异步流程，**绝不能中途丢弃**：
 * 一旦被顶掉又提前 return，会把「全展开 + 旧的 overflow=false」这个中间态留在页面上
 * （表现就是标签溢出被裁、展开箭头却不见了）。所以改成串行：正在跑时只挂个标记，
 * 当前这一轮跑完再补一轮，保证最后一次写入的一定是完整结论。 */
let measuring = false
let measureQueued = false

async function measureHistory() {
  if (measuring) {
    measureQueued = true
    return
  }
  measuring = true
  try {
    // 最多补 2 轮，防御 ResizeObserver 自激（正常情况下第二轮结论相同、不再改 DOM，自然收敛）
    for (let round = 0; round < 3; round++) {
      measureQueued = false
      await measureHistoryOnce()
      if (!measureQueued) break
    }
  } finally {
    measuring = false
  }
}

/** 量出「折叠态能显示几条」，并把箭头需要的宽度预留出来。
 *
 * 这里不再记录任何绝对坐标 —— 上一版把箭头 position:absolute 到某个 chip 的
 * offsetLeft/Top 上，一旦测完又发生折行（字体晚到、宽度微调），箭头就会落在
 * 别的标签身上、还把它盖住一半。现在改为：超出的标签 v-if 掉、不参与布局，
 * 箭头是流内最后一个元素，折行位置交给 flex 自己算，结构上不可能重叠。
 *
 * 代价是：被 v-if 掉的标签没有几何信息，所以测量前要先把它们临时放回来。
 * 此时容器仍是 max-height:70px + overflow:hidden，放回来也不会多露一行、不会闪。
 */
async function measureHistoryOnce() {
  const el = historyRef.value
  if (!el) return
  // ① 被 v-if 掉的标签没有几何信息，先临时放回 DOM（容器仍被 max-height 裁成两行，不会闪）
  if (!historyExpanded.value && visibleCount.value !== Number.POSITIVE_INFINITY) {
    visibleCount.value = Number.POSITIVE_INFINITY
  }
  // ② 无条件等一次 DOM 刷新。历史变化触发的测量是在 pre-flush 时机跑的，
  //   那时新加的标签还没进 DOM；不等就会量到旧的一批，把「溢出」判成「没溢出」，
  //   结果新标签溢出被裁、展开箭头却不出现（实测就是这样丢的）。
  await nextTick()
  const chips = Array.from(el.querySelectorAll<HTMLElement>('.csp-chip:not(.csp-chip-toggle)'))
  if (!chips.length) {
    historyOverflow.value = false
    visibleCount.value = Number.POSITIVE_INFINITY
    return
  }
  // 全部用 getBoundingClientRect 相对容器算：offsetTop/offsetLeft 是相对 offsetParent 的，
  // 一旦容器的定位上下文变了（或页面还在 transform 滑入中）就会整体偏移，量出来的行号全错。
  const box = el.getBoundingClientRect()
  // 容器还没量出宽度（首帧、或页面还没显示）时不要下结论，否则会把条数误写成 0
  if (!box.width || !box.height) return
  const geo = chips.map(c => {
    const r = c.getBoundingClientRect()
    return { bottom: r.bottom - box.top, right: r.right - box.left }
  })
  const fits = geo.filter(g => g.bottom <= TWO_ROWS_H + 1)
  // 兜底：容器真的被裁了（scrollHeight 超过可视高度）也算溢出。
  // 这样即便上面逐条判断因为半像素/字体回流算错，也不会出现「被裁掉却没有展开箭头」。
  const clipped = el.scrollHeight > el.clientHeight + 1
  const overflow = fits.length < chips.length || clipped
  let count = fits.length
  if (overflow) {
    if (count >= chips.length) count = chips.length - 1 // 一定要让出一条给箭头
    // 箭头在流内要占一个位置：最后一行剩下的宽度不够它 + 间距时，再让出一条
    // （纯几何推算，不需要渲染一次去看箭头落在第几行）
    while (count > 1) {
      const last = geo[count - 1]
      if (box.width - last.right >= TOGGLE_W + CHIP_GAP) break
      count--
    }
  }
  historyOverflow.value = overflow
  visibleCount.value = overflow ? count : Number.POSITIVE_INFINITY
}

watch(() => history.value.length, len => {
  historyExpanded.value = false
  if (!len) {
    // 整段历史被清空时区块会 v-if 掉，连同「有溢出」的旧结论一起清干净，
    // 否则下次有历史时区块重新挂载、箭头会带着旧状态一起回来
    historyEditing.value = false
    historyOverflow.value = false
    visibleCount.value = Number.POSITIVE_INFINITY
  }
  void measureHistory()
})

/** 历史区块是 v-if 出来的：清空后重新有历史时会整块重建，
 * 此时 historyRef 从 null 变成新元素。不在这里补一次测量，
 * 那次「有溢出」的旧结论就会留下来（表现为只有 1 条历史却还挂着展开箭头）。
 * flush: 'post' 保证元素已入 DOM 且完成布局，顺带把尺寸观察器指到新元素上。 */
watch(historyRef, el => {
  historyRO?.disconnect()
  historyRO = null
  if (!el) return
  if (typeof ResizeObserver !== 'undefined') {
    historyRO = new ResizeObserver(() => { void measureHistory() })
    historyRO.observe(el)
  }
  void measureHistory()
}, { flush: 'post' })

// 进/出管理态时 chip 宽度会变（多出 ×），可能多折一行，重量一次才不至于溢出却没展开箭头
watch(historyEditing, () => { void measureHistory() })

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
  // 首次拿到资讯池时顺带抽一条热帖当占位符；「刷新」再进来也会调用，但已抽过就直接跳过
  pickPlaceholder()
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
] as const

const hotTab = ref<string>('all')

const hotTabNavRef = ref<HTMLElement | null>(null)
/** 只用于测量，刻意不进响应式：五个按钮的位置在渲染后量一次就够，放进 ref 数组每帧都要 diff */
const hotTabEls: HTMLElement[] = []

function setHotTabRef(el: unknown, i: number) {
  // 模板里的 :ref 回调拿到的可能是组件实例，这里只要真实元素
  if (el instanceof HTMLElement) hotTabEls[i] = el
}

/** 指示器的目标位置/宽度，实际渲染成 transform + width，位移交给 CSS 过渡 */
const hotInk = ref({ left: 0, width: 0 })
/** 首次量到之前不显示：否则会先闪一个宽度 0 的点再滑出去 */
const hotInkReady = ref(false)

const hotInkStyle = computed(() => ({
  transform: `translateX(${hotInk.value.left}px)`,
  width: `${hotInk.value.width}px`,
  opacity: hotInkReady.value ? 1 : 0,
}))

/** 滑块宽度封顶 20px 并居中压在文字下方：两字 Tab 与四字 Tab 的下划线体量一致，长文案不会被拉成长条 */
function measureHotInk() {
  const idx = HOT_TABS.findIndex(t => t.key === hotTab.value)
  const el = hotTabEls[idx]
  if (!el || !el.offsetWidth) return
  const w = Math.min(el.offsetWidth, 20)
  hotInk.value = { left: el.offsetLeft + (el.offsetWidth - w) / 2, width: w }
  hotInkReady.value = true
}

function pickHotTab(key: string, idx: number) {
  if (hotTab.value === key) return
  hotTab.value = key
  // 点到的 Tab 在横向视口外时滚到居中：这条能横滑，不滚用户就看不到自己选中的是哪个
  const nav = hotTabNavRef.value
  const el = hotTabEls[idx]
  if (!nav || !el) return
  if (el.offsetLeft < nav.scrollLeft || el.offsetLeft + el.offsetWidth > nav.scrollLeft + nav.clientWidth) {
    nav.scrollTo({ left: el.offsetLeft - (nav.clientWidth - el.offsetWidth) / 2, behavior: 'smooth' })
  }
}

watch(hotTab, () => { void nextTick(measureHotInk) })

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

/** 占位符候选：热榜口径下「有互动」的前 10 条（评论×3 + 浏览 > 0）。
 * 真的全站没人互动时，退回最新的 8 条 —— 总得有个能搜的例子，不能空着。 */
const placeholderPool = computed<SearchPoolItem[]>(() => {
  const scored = props.items
    .map(it => ({ it, score: it.comment_count * 3 + it.view_count }))
    .sort((a, b) => b.score - a.score)
  const hot = scored.filter(s => s.score > 0).slice(0, 10)
  return (hot.length >= 3 ? hot : scored.slice(0, 8)).map(s => s.it)
})

/** 搜索框占位符：**每次进页面从上面这批热帖里随机抽一条**，固定不下来。
 * 不跟 hotTab（切分类不改文案）、也不跟「搜索发现」的随机批次（点刷新不改文案）——
 * 提示只在这两种时刻变：进页面时抽一次、资讯池异步到位时补抽一次。
 * `picked` 保证一次会话只抽一次，后续池子怎么更新都不动已显示的文案。 */
const placeholderFull = ref(PLACEHOLDER_FALLBACK)
let placeholderPicked = false

function pickPlaceholder() {
  if (placeholderPicked) return
  const pool = placeholderPool.value
  if (!pool.length) return
  placeholderPicked = true
  // 优先避开上一次进页面用过的标题（只有一条候选时只能重复）
  const fresh = pool.filter(it => it.title.trim() !== lastPlaceholderTitle)
  const list = fresh.length ? fresh : pool
  const pick = list[Math.floor(Math.random() * list.length)]
  lastPlaceholderTitle = pick.title.trim()
  placeholderFull.value = lastPlaceholderTitle
}

// 文案一变就按新宽度重量（截断位置随字号与实际字宽走）
watch(placeholderFull, () => { void nextTick(fitPlaceholder) })

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

/* ==================== 结果页分类与筛选 ====================
   交互对齐社区搜索页（综合 / 内容 / 用户 + 右侧筛选），落到本页的真实数据只有两层：
   资讯（前端标题过滤）与知识库（后端检索）。栏目筛选复用热榜分榜口径，
   已下线栏目与「推荐 / 关注」这类聚合页本来就不在池子里，不重复列。 */

const RESULT_TABS = [
  { key: 'all', label: '综合' },
  { key: 'news', label: '资讯' },
  { key: 'kb', label: '知识库' },
] as const

const resultTab = ref<string>('all')

const SOURCE_FILTERS: { key: string; label: string }[] = [
  { key: 'all', label: '全部来源' },
  ...HOT_TABS.filter(t => t.key !== 'all').map(t => ({ key: t.key as string, label: t.label as string })),
]

const sourceFilter = ref('all')
const filterOpen = ref(false)

/** 筛选只改写资讯流的展示，不动 newsHits 本身 —— 清掉筛选立刻回到全量，不必重新计算命中 */
const visibleNews = computed<SearchPoolItem[]>(() => (
  sourceFilter.value === 'all'
    ? newsHits.value
    : newsHits.value.filter(i => i.source === sourceFilter.value)
))

function pickSource(key: string) {
  sourceFilter.value = key
  filterOpen.value = false
  // 栏目只作用于资讯流：停在知识库 tab 时选了具体栏目，顺手切回资讯，否则点了像是没反应
  if (key !== 'all' && resultTab.value === 'kb') resultTab.value = 'news'
}

watch(resultTab, tab => {
  filterOpen.value = false
  // 知识库按需检索：综合 tab 下资讯已命中时并不会请求，切过来才补
  if (tab === 'kb' && keyword.value.trim()) void loadKnowledge(keyword.value.trim())
})

/* ==================== 生命周期 ====================
   body 滚动锁由 SubPageShell 负责（引用计数版）：本页打开时加锁，退场动画播完才解锁，
   盖在本页之上的资讯详情子页关闭时只释放自己那一层，不会把本页的锁一起拆掉 ——
   早先为此盯 body style 的 MutationObserver 也因此不再需要。 */

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape' || !visible.value) return
  // Esc 与返回箭头同语义：先退结果页这一层，再关整个搜索页
  if (searchDone.value) backToSearch()
  else close()
}

/** 宽度变了 chip 会重新折行：占位符要重量、历史的两行边界要重量、
 * 热榜滑块也要重排（Tab 文字宽度随字号与字宽变） */
function onResize() {
  fitPlaceholder()
  void measureHistory()
  measureHotInk()
}

onMounted(() => {
  visible.value = true
  shufflePick()
  void nextTick(() => {
    void measureHistory()
    fitPlaceholder()
    measureHotInk()
  })
  // 字体加载完字宽会变（chip 宽度跟着变、折行位置也会变），加载后再量
  void document.fonts?.ready.then(() => {
    void measureHistory()
    fitPlaceholder()
    measureHotInk()
  })
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onResize)
  // 历史区的尺寸观察器不在这里建：区块是 v-if 的，清空后重建会换成新元素，
  // 统一交给 watch(historyRef) 在元素就位时挂上，避免盯着一个已卸载的节点。
  // 等滑入动画播完再聚焦：iOS 上动画中途弹键盘会把正在滑入的页面顶得跳动
  window.setTimeout(() => {
    inputRef.value?.focus()
    // 动画结束、尺寸稳定后再量一次
    fitPlaceholder()
    void measureHistory()
    measureHotInk()
  }, 350)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  window.clearTimeout(fitRetryTimer)
  historyRO?.disconnect()
  historyRO = null
})
</script>

<style scoped>
/* ================= 根容器 =================
   整屏骨架（fixed inset:0 / 不透明白底 / 裁切溢出 / z-index）由 SubPageShell 的
   .subpage-root 提供（styles/subpage-transition.css）。这里是页面自己的内容列：
   flex:1 填满外壳，内部仍是「顶栏 + 滚动区」的纵向布局。
   为什么不把类挂在外壳根节点上：根节点在子组件模板里渲染，本组件的 scoped 样式打不到它。 */
.csp-root {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  color: #1d2129;
  -webkit-tap-highlight-color: transparent;
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
  /* 去掉 UA 默认内边距：fitPlaceholder() 用 clientWidth 量可用宽度，要保证这是个干净的内容盒 */
  padding: 0;
}
/* 注意：Chromium 不认 ::placeholder 上的 text-overflow（实测仍会硬切半个字），
   占位符的省略号由 fitPlaceholder() 在脚本里按实际宽度裁好，这里只管颜色 */
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
/* 「搜索」按钮：简约文字款，点击等同键盘回车提交。
   不做底色外框，靠字重与留白和输入框区分；两个顶栏（搜索页 / 结果页）共用，
   flex-shrink 防止被长关键词挤压。 */
.csp-go {
  flex-shrink: 0;
  height: 36px;
  padding: 0 4px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: #1d2129;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.12s ease;
}
.csp-go:active { opacity: 0.55; }
/* 结果页顶栏的输入框改白底描边（参考稿）：灰底胶囊留给搜索页的「待输入」态，
   描边框对应「正在看这批结果、随时改词」的阅读态，两层不至于长得一模一样。 */
.csp-head--result .csp-field {
  background: #fff;
  border: 1px solid #e5e6eb;
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

/* ================= 搜索结果页（第三层） =================
   盖在搜索页之上独立成层，自己带顶栏与滚动区：返回只退这一层。
   背景必须不透明 —— 滑入/滑出时下面是搜索页，透出来就穿帮了。 */
.csp-result-page {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  background: #fff;
}

/* ================= 搜索历史 ================= */
.csp-history {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.csp-history.is-collapsed {
  /* 折叠态只渲染两行内的标签（多出来的直接 v-if 掉、不布局），
     这个 max-height 只是兜底：万一某条 chip 高度异常也不会把页面撑开
     高度 = 31 * 2 + 8 行距，与脚本里的 TWO_ROWS_H 对齐 */
  max-height: 70px;
  overflow: hidden;
}
.csp-chip {
  /* 一行至少三条：3 条各自的上限 + 2 个 8px 间距刚好铺满整行，
     长标题在 chip 内自己省略，不再靠固定 190px 撑出一行只有两条 */
  max-width: calc((100% - 16px) / 3);
  height: 31px;
  padding: 0 12px;
  border: 0;
  /* 浅圆角：参考稿是「几乎直的方角」（半径约等于高度的 1/8），
     8px 在 31px 高度上会显得很圆、像胶囊 */
  border-radius: 4px;
  background: #f2f3f5;
  color: #1d2129;
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
  /* 允许被压缩：nowrap 文本的 min-content 就是它自身宽度，不给 0 会顶宽、把 chip 撑破 */
  min-width: 0;
  max-width: 100%;
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
  flex: none; /* 管理态里让 × 保持原尺寸，被压缩的应该是文字 */
  color: #a5a9b3;
  cursor: pointer;
}
.csp-chip-toggle {
  flex: none; /* 箭头宽度固定，不参与收缩 */
  /* 正方形：与 chip 等高同宽（参考稿里它就是一个 31×31 的灰块） */
  width: 31px;
  padding: 0;
  justify-content: center;
  background: #f2f3f5; /* 与 chip 同底色（参考稿不是描边按钮） */
  border: 0;
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

/* ================= 热榜 =================
   切换分类的动效分两层：Tab 下面一条短滑块平滑滑到新位置（位置由 measureHotInk 实测），
   榜单本身先淡出再逐条上浮 —— 两层叠起来才是「切了个分类」，而不是「页面被替换」。 */
.csp-hot-tabs {
  position: relative;
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
  /* 底部多留 3px：给滑块留出与文字的呼吸位，不然下划线会贴着字 */
  padding: 6px 0 9px;
  font-size: 15px;
  color: #333;
  cursor: pointer;
}
.csp-hot-tab.is-active {
  color: #ff4d3a;
  font-weight: 700;
}
/* 滑块：绝对定位不占 flex 槽位；位移走 transform 而不是 left，才能用 GPU 且不触发重排 */
.csp-hot-ink {
  position: absolute;
  left: 0;
  bottom: 2px;
  height: 3px;
  border-radius: 2px;
  background: #ff4d3a;
  pointer-events: none;
  transition:
    transform 0.26s cubic-bezier(0.34, 1.15, 0.64, 1),
    width 0.2s ease,
    opacity 0.15s ease;
}
/* 榜单退场：只淡出，不位移 —— 位移留给入场，两个方向都动会显得晃 */
.csp-swap-leave-active { transition: opacity 0.12s ease; }
.csp-swap-leave-to { opacity: 0; }
/* 入场逐条上浮：delay 由模板按序号给（封顶 9 条，最后几条一起进场，避免末尾等太久） */
.csp-hot-row {
  animation: csp-hot-rise 0.3s cubic-bezier(0.22, 0.8, 0.36, 1) both;
}
@keyframes csp-hot-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .csp-hot-ink { transition: none; }
  .csp-hot-row { animation: none; }
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

/* ================= 搜索结果页：分类栏 =================
   版式取自社区搜索页：Tab 左对齐可横滑，右侧「筛选」常驻；选中项用短下划线而非色块，
   视觉上比信息流 Tab 更轻，不抢帖子标题的注意力。 */
.csp-rtabs {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 2px 14px 0;
  flex-shrink: 0;
}
.csp-rtabs-scroll {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 26px;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.csp-rtabs-scroll::-webkit-scrollbar { display: none; }
.csp-rtab {
  position: relative;
  flex-shrink: 0;
  border: 0;
  background: none;
  padding: 6px 0 13px;
  font-size: 16px;
  color: #4e5969;
  cursor: pointer;
}
.csp-rtab.is-active {
  color: #1d2129;
  font-weight: 700;
}
/* 短横线居中压在文字下方：宽度固定，跟着字多的 Tab 会自动显得更「短」，与参考稿一致 */
.csp-rtab.is-active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 5px;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  border-radius: 2px;
  background: #1d2129;
}
.csp-filter {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  border: 0;
  background: none;
  padding: 6px 0 13px 10px;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
}
.csp-filter.is-open { color: #1d2129; }
.csp-filter-caret { transition: transform 0.18s ease; }
.csp-filter.is-open .csp-filter-caret { transform: rotate(180deg); }

/* 筛选面板：来源栏目 chips，多行自动换行（栏目数量随资讯源配置变，不写死行数） */
.csp-filter-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 14px 12px;
  flex-shrink: 0;
}
.csp-fchip {
  height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: 15px;
  background: #f2f3f5;
  color: #4e5969;
  font-size: 13px;
  cursor: pointer;
}
.csp-fchip.is-active {
  background: #1d2129;
  color: #fff;
}
.csp-drop-enter-active,
.csp-drop-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}
.csp-drop-enter-from,
.csp-drop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ================= 搜索结果：信息流 =================
   参考稿里帖子之间靠留白分隔、没有分割线，所以这里去掉逐条 border-bottom，
   改由 gap 撑开；条目内部的标题 / 来源 · 日期排版保持原样不动。 */
.csp-feed-scroll { padding-top: 12px; }
.csp-feed {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.csp-result {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  text-align: left;
  cursor: pointer;
}
.csp-result.is-static { cursor: default; }
.csp-result:active .csp-result-title { opacity: 0.6; }
.csp-result.is-static:active .csp-result-title { opacity: 1; }
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
/* 空态居中出现：信息流里上面没有分节标题兜着，左对齐的一句小字容易看成漏加载 */
.csp-empty.is-block {
  margin: 32px 0;
  text-align: center;
}
</style>
