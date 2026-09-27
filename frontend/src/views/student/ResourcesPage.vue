<template>
  <div class="resources-page">
    <!-- 吸顶头部：品牌标题 + 操作 + 频道 Tab（移动端横向滚动，参考今日头条/即刻频道栏） -->
    <div class="res-topbar">
      <div class="topbar-main">
        <div class="brand">
          <span class="brand-emoji">📚</span>
          <div class="brand-text">
            <h2 class="res-title">AI 资源空间</h2>
            <p class="res-sub">为你发现 · 学习资源 · 行业资讯 · 校园信息</p>
          </div>
        </div>
        <div class="topbar-actions">
          <el-button size="small" :loading="refreshLoading" @click="refreshFeedsNow" class="tb-btn">
            <el-icon v-if="!refreshLoading" style="margin-right:4px"><Refresh /></el-icon>
            <span class="tb-btn-text">刷新</span>
          </el-button>
          <el-button size="small" class="tb-btn" @click="openSourceDialog">
            <el-icon style="margin-right:4px"><Setting /></el-icon>
            <span class="tb-btn-text">订阅源</span>
          </el-button>
        </div>
      </div>
      <div class="channel-bar">
        <div
          v-for="t in feedTabs" :key="t.key"
          class="channel-item" :class="{ active: activeFeedTab === t.key }"
          @click="switchFeed(t.key)"
        >{{ t.label }}</div>
      </div>
    </div>

    <!-- 最新资讯（实时外部聚合） -->
    <div class="res-card feeds-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">📰 最新资讯聚合</span>
        <span v-if="feedFetchedAt" class="head-sub">更新于 {{ feedFetchedAt }}</span>
      </div>
      <p class="feed-tip">{{ currentTab?.sub }}</p>
      <div v-loading="feedLoading[activeFeedTab]" class="feed-body">
        <div v-if="!feedLoading[activeFeedTab] && !feedByType[activeFeedTab].length" class="empty-tip">
          暂无内容，点击右上角“刷新”获取最新信息
        </div>

        <!-- 权威排行榜：排名 + 分数条 -->
        <template v-if="activeFeedTab === 'rankings'">
          <div class="rank-list">
            <div v-for="(f, idx) in feedByType.rankings" :key="f.id" class="rank-item">
              <span class="rank-no" :class="rankClass(idx)">{{ idx + 1 }}</span>
              <div class="rank-main">
                <div class="rank-title" @click="openLink(f.link)">{{ f.title }}</div>
                <div class="rank-back"><span class="rank-bar" :style="rankWidth(f)"></span></div>
              </div>
              <div class="rank-side">
                <span class="rank-score">{{ rankScore(f) }}</span>
                <span v-if="f.meta.votes != null" class="rank-votes">{{ formatNum(f.meta.votes) }} 票</span>
              </div>
            </div>
          </div>
        </template>

        <!-- 普通资讯列表 -->
        <template v-else>
          <div v-for="f in feedByType[activeFeedTab]" :key="f.id" class="feed-item">
            <div class="feed-item-title" @click="openLink(f.link)">{{ f.title }}</div>
            <div v-if="f.summary" class="res-item-summary">{{ f.summary }}</div>
            <div v-if="activeFeedTab !== 'news' && (f.meta?.stars != null)" class="feed-meta-badges">
              <span v-if="f.meta.stars != null"><el-icon><StarFilled /></el-icon>{{ formatNum(f.meta.stars) }}</span>
              <span v-if="f.meta.forks != null"><el-icon><Share /></el-icon>{{ formatNum(f.meta.forks) }}</span>
              <span v-if="f.meta.language" class="feed-lang">{{ f.meta.language }}</span>
            </div>
            <div class="feed-item-foot">
              <span class="feed-badge" :class="activeFeedTab">{{ badgeLabel(f) }}</span>
              <span class="feed-source">{{ f.source_name || defaultSource(f) }}</span>
              <span v-if="f.published_at" class="feed-time">{{ formatDate(f.published_at) }}</span>
              <span class="foot-spacer"></span>
              <el-button size="small" text :type="isFeedFaved(f) ? 'warning' : 'default'" class="fav-btn" @click="toggleFeedFav(f)">
                <el-icon style="margin-right:3px"><StarFilled v-if="isFeedFaved(f)" /><Star v-else /></el-icon>
                {{ isFeedFaved(f) ? '已收藏' : '收藏' }}
              </el-button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 订阅源管理对话框（移动端全屏） -->
    <el-dialog v-model="sourceDialogVisible" title="订阅源管理" width="680px" class="source-dialog">
      <div class="source-tip">数据源已动态化：可启停/编辑内置源，也可添加任意 RSS 订阅或官网链接。点击“保存”后，刷新资讯即生效。</div>
      <div class="src-table-wrap">
        <el-table :data="sources" v-loading="sourceLoading" size="small" max-height="380">
          <el-table-column label="名称" min-width="150">
            <template #default="{ row }">
              <div class="src-name-row">
                <el-tag v-if="row.is_builtin" size="small" type="info" effect="plain" style="margin-right:6px">内置</el-tag>
                <el-input v-if="editingId === row.id" v-model="editForm.name" size="small" />
                <span v-else class="src-name">{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="90">
            <template #default="{ row }">{{ kindLabel(row.kind) }}</template>
          </el-table-column>
          <el-table-column label="分类" width="110">
            <template #default="{ row }">{{ sourceTypeLabel(row.source_type) }}</template>
          </el-table-column>
          <el-table-column label="URL" min-width="180" show-overflow-tooltip class-name="src-url-col">
            <template #default="{ row }">
              <el-input v-if="editingId === row.id" v-model="editForm.url" size="small" />
              <span v-else class="src-url">{{ row.url }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" align="right">
            <template #default="{ row }">
              <template v-if="editingId === row.id">
                <el-button size="small" type="primary" text @click="saveSource(row)">保存</el-button>
                <el-button size="small" text @click="editingId = null">取消</el-button>
              </template>
              <template v-else>
                <el-button size="small" text @click="startEdit(row)">编辑</el-button>
                <el-button size="small" text :type="row.enabled ? 'warning' : 'success'" @click="toggleSource(row)">
                  {{ row.enabled ? '停用' : '启用' }}
                </el-button>
                <el-button v-if="!row.is_builtin" size="small" text type="danger" @click="removeSource(row)">删除</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="add-source">
        <div class="add-source-title">+ 添加自定义订阅源</div>
        <div class="add-source-row">
          <el-input v-model="addForm.name" placeholder="名称，如：某某科技官方" style="width:180px" size="small" />
          <el-select v-model="addForm.kind" style="width:100px" size="small">
            <el-option label="RSS" value="rss" />
            <el-option label="网页" value="html" />
          </el-select>
          <el-select v-model="addForm.source_type" style="width:120px" size="small">
            <el-option v-for="t in feedTabs" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
          <el-input v-model="addForm.url" placeholder="https:// 订阅或网页地址" style="flex:1" size="small" @keyup.enter="addSource" />
          <el-button size="small" type="primary" @click="addSource">添加</el-button>
        </div>
        <div class="add-source-row">
          <el-input v-model="addForm.filter_kw" placeholder="可选：标题关键词过滤（逗号分隔，如：AI,大模型）" size="small" />
        </div>
      </div>
      <template #footer>
        <el-button @click="sourceDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 为你发现（AI 推荐） -->
    <div class="res-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">✨ 为你发现</span>
        <span class="head-sub">基于你的学习画像 + 语义匹配</span>
      </div>
      <div v-loading="recoLoading" class="reco-body">
        <div v-if="!recoLoading && !recommends.length" class="empty-tip">完善个人画像后，这里会为你推荐更精准的内容</div>
        <div v-for="r in recommends" :key="r.item_type + '-' + r.item_id" class="reco-item" :class="{ 'reco-faved': isFaved(r) }">
          <div class="reco-head">
            <el-tag size="small" :type="typeTag(r.item_type)" effect="light" round>{{ typeLabel(r.item_type) }}</el-tag>
            <span class="reco-reason">{{ r.reason }}</span>
          </div>
          <div class="reco-title" @click="openLink(r.link)">{{ r.title }}</div>
          <div class="reco-meta">
            <span v-if="r.source" class="reco-source">{{ r.source }}</span>
            <el-button size="small" text :type="isFaved(r) ? 'warning' : 'default'" class="fav-btn" @click="toggleFav(r)">
              <el-icon style="margin-right:3px"><StarFilled v-if="isFaved(r)" /><Star v-else /></el-icon>
              {{ isFaved(r) ? '已收藏' : '收藏' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 资源浏览 -->
    <div class="res-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">资源浏览</span>
      </div>
      <div class="cat-row">
        <el-tag
          v-for="f in catFilters"
          :key="f.value"
          :type="cat === f.value ? 'primary' : 'info'"
          :effect="cat === f.value ? 'dark' : 'plain'"
          class="cat-tag" round
          @click="switchCat(f.value)"
        >{{ f.label }}</el-tag>
      </div>
      <div class="browse-bar">
        <el-input v-model="browseQ" placeholder="在资源中搜索关键词" clearable @keyup.enter="browsePage(1)" @clear="browsePage(1)">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="browsePage(1)">搜索</el-button>
      </div>
      <div v-loading="browseLoading">
        <div v-if="!browseLoading && !items.length" class="empty-tip">暂无资源</div>
        <div v-for="it in items" :key="it.item_type + '-' + it.item_id" class="res-item">
          <div class="res-item-head">
            <el-tag size="small" :type="typeTag(it.item_type)" effect="light" round>{{ typeLabel(it.item_type) }}</el-tag>
            <span v-if="it.category" class="res-item-cat">{{ catLabel(it.category) }}</span>
            <span v-if="it.source" class="res-item-cat">{{ it.source }}</span>
          </div>
          <div class="res-item-title" @click="openLink(it.link)">{{ it.title }}</div>
          <div v-if="it.summary" class="res-item-summary">{{ it.summary }}</div>
          <div class="res-item-foot">
            <el-link v-if="it.link" type="primary" :href="it.link" target="_blank" :underline="false" size="small">
              去查看<el-icon style="margin-left:3px"><TopRight /></el-icon>
            </el-link>
            <el-button size="small" text :type="isFaved(it) ? 'warning' : 'default'" class="fav-btn" @click="toggleFav(it)">
              <el-icon style="margin-right:3px"><StarFilled v-if="isFaved(it)" /><Star v-else /></el-icon>
              {{ isFaved(it) ? '已收藏' : '收藏' }}
            </el-button>
          </div>
        </div>
        <div v-if="browseTotal > pageSize" class="pager-row">
          <el-pagination
            v-model:current-page="browsePageNum"
            :page-size="pageSize"
            :total="browseTotal"
            layout="prev, pager, next"
            background
            small
            @current-change="browsePage"
          />
        </div>
      </div>
    </div>

    <!-- 我的收藏 -->
    <div class="res-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">我的收藏</span>
        <span class="head-sub">收藏会参与你的画像与推荐权重</span>
      </div>
      <div v-if="!favorites.length" class="empty-tip">还没有收藏，看到好内容点个收藏吧</div>
      <div v-for="f in favorites" :key="f.id" class="fav-item">
        <el-icon :size="14" style="color:#e6a23c;flex-shrink:0"><StarFilled /></el-icon>
        <div class="fav-info" @click="openLink(f.link)">
          <div class="fav-title">{{ f.title }}</div>
          <div class="fav-meta">{{ typeLabel(f.item_type) }}<span v-if="f.category"> · {{ catLabel(f.category) }}</span><span v-if="f.created_at"> · {{ formatDate(f.created_at) }}</span></div>
        </div>
        <el-button size="small" text type="danger" @click="unfav(f)">取消</el-button>
      </div>
    </div>

    <!-- 知识库智能检索（保留原有） -->
    <div class="res-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">知识库智能检索</span>
        <span class="head-sub">校园常见问题与文档资料</span>
      </div>
      <div class="res-search">
        <el-input
          v-model="q"
          placeholder="输入关键词，如：图书馆开放时间、奖学金申请、心理咨询……"
          :prefix-icon="Search"
          clearable
          @keyup.enter="doSearch"
        />
        <el-button type="primary" round :loading="loading" @click="doSearch">
          <el-icon v-if="!loading" style="margin-right:4px"><Search /></el-icon>检索
        </el-button>
      </div>
      <div class="res-hot">
        <span class="res-hot-label">热门：</span>
        <el-tag
          v-for="kw in hotKeywords"
          :key="kw"
          class="res-hot-tag"
          effect="plain"
          @click="quickSearch(kw)"
        >{{ kw }}</el-tag>
      </div>
      <div v-loading="loading" class="res-results">
        <el-empty
          v-if="!loading && searched && hits.length === 0"
          description="未找到相关内容，换个关键词试试"
          :image-size="88"
        />
        <div v-for="(h, i) in hits" :key="i" class="res-item">
          <div class="res-item-head">
            <el-tag :type="h.type === 'qa' ? 'success' : 'warning'" size="small" effect="dark">
              {{ h.type === 'qa' ? '智能问答' : '文档资料' }}
            </el-tag>
            <span v-if="h.category" class="res-item-cat">{{ h.category }}</span>
          </div>
          <template v-if="h.type === 'qa'">
            <div class="res-q">{{ h.question }}</div>
            <div class="res-a">{{ h.answer }}</div>
          </template>
          <template v-else>
            <div class="res-q">文档片段</div>
            <div class="res-a">{{ h.content }}</div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { Search, Star, StarFilled, TopRight, Refresh, Share, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
import {
  getResourceItems, getRecommend, getFavorites, addFavorite, removeFavorite,
  getFeeds, refreshFeeds, type ResourceItem, type RecommendItem, type Favorite,
  type FeedItem, type FeedSourceType,
} from '@/api/resources'
import {
  getFeedSources, createFeedSource, updateFeedSource, deleteFeedSource, type FeedSource,
} from '@/api/resources'

// ---------- 外部资讯聚合 ----------
const feedTabs: { key: FeedSourceType; label: string; sub?: string }[] = [
  { key: 'papers', label: 'AI 论文', sub: '订阅 arXiv 最新人工智能/机器学习/自然语言研究' },
  { key: 'opensource', label: '开源项目榜', sub: 'GitHub / Gitee 最热门与最活跃的 AI 优质项目' },
  { key: 'agents', label: '智能体榜', sub: '当前热门的 AI 智能体（Agent）开源项目排行' },
  { key: 'news', label: '时政要闻', sub: '新华网 · 中国政府网 · 央视网 权威要闻' },
  { key: 'ai_news', label: 'AI 行业', sub: 'OpenAI · Google · DeepMind · MIT Technology Review 官方技术资讯' },
  { key: 'rankings', label: '权威排行榜', sub: 'LMArena Chatbot Arena 模型能力竞技榜，随社区对战动态更新' },
  { key: 'cn_ai', label: '国产模型', sub: 'DeepSeek · 豆包(火山) · 通义 · Kimi · MiniMax 官方动态与新品发布' },
]
const activeFeedTab = ref<FeedSourceType>('papers')
const currentTab = computed(() => feedTabs.find(t => t.key === activeFeedTab.value))
const feedByType = reactive<Record<string, FeedItem[]>>({
  papers: [], opensource: [], agents: [], news: [], ai_news: [], rankings: [], cn_ai: [],
})
const feedLoading = reactive<Record<string, boolean>>({
  papers: false, opensource: false, agents: false, news: false, ai_news: false, rankings: false, cn_ai: false,
})
const refreshLoading = ref(false)
const feedFetchedAt = ref('')

async function loadFeed(type: FeedSourceType) {
  feedLoading[type] = true
  try {
    feedByType[type] = await getFeeds({ source_type: type, limit: 20 })
    feedFetchedAt.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch { feedByType[type] = [] }
  finally { feedLoading[type] = false }
}

function switchFeed(key: FeedSourceType) {
  if (activeFeedTab.value === key) return
  activeFeedTab.value = key
  if (!feedByType[key].length) loadFeed(key)
  nextTick(() => {
    document.querySelector('.channel-item.active')?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  })
}

async function refreshFeedsNow() {
  refreshLoading.value = true
  try {
    await refreshFeeds(activeFeedTab.value)
    await loadFeed(activeFeedTab.value)
    ElMessage.success('已更新最新资讯')
  } catch (e: any) {
    ElMessage.warning(e?.response?.data?.detail || '刷新失败，请稍后再试')
  } finally { refreshLoading.value = false }
}

const DEFAULT_SOURCE: Record<FeedSourceType, string> = {
  papers: 'arXiv', agents: '智能体榜', opensource: '开源项目榜', news: '权威要闻',
  ai_news: 'AI 行业', rankings: '权威榜', cn_ai: '国产模型',
}
const defaultSource = (f: FeedItem) => DEFAULT_SOURCE[f.source_type] || ''
const badgeLabel = (f: FeedItem) =>
  ({ papers: '论文', opensource: '项目', agents: '智能体', news: '要闻', ai_news: '行业', rankings: '权威', cn_ai: '国产' }[f.source_type] || f.source_type)
function formatNum(n: any) {
  if (n == null) return ''
  const v = Number(n)
  if (v >= 1000) return (v / 1000).toFixed(1) + 'k'
  return String(v)
}

// 权威排行榜辅助
function rankScore(f: FeedItem) {
  const s = f.meta?.score
  if (s == null) return '—'
  const v = Number(s)
  return Number.isInteger(v) ? String(v) : v.toFixed(1)
}
function rankClass(idx: number) {
  return idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : ''
}
function maxRankScore(items: FeedItem[]) {
  let max = 0
  for (const it of items) {
    const s = Number(it.meta?.score)
    if (s > max) max = s
  }
  return max || 1
}
function rankWidth(f: FeedItem) {
  const s = Number(f.meta?.score)
  if (!s) return { width: '0%' }
  return { width: Math.max(4, Math.round((s / maxRankScore(feedByType.rankings)) * 100)) + '%' }
}

// 外部资讯收藏：复用现有收藏机制（item_type = source_type, item_id = feed.id）
const isFeedFaved = (f: FeedItem) => !!favMap.value[`${f.source_type}:${f.id}`]
async function toggleFeedFav(f: FeedItem) {
  const key = `${f.source_type}:${f.id}`
  if (favMap.value[key]) {
    await removeFavorite(favMap.value[key])
    ElMessage.success('已取消收藏')
  } else {
    await addFavorite({
      item_type: f.source_type, item_id: f.id, title: f.title,
      category: f.source_name, summary: f.summary, link: f.link,
    })
    ElMessage.success('已收藏')
  }
  await loadFavorites()
}

// ---------- 知识库检索（原有） ----------
const q = ref('')
const hits = ref<KnowledgeHit[]>([])
const loading = ref(false)
const searched = ref(false)
const hotKeywords = ['图书馆', '奖学金', '心理咨询', '食堂', '请假流程']

async function doSearch() {
  const keyword = q.value.trim()
  if (!keyword) { ElMessage.warning('请输入检索关键词'); return }
  loading.value = true
  searched.value = true
  try { hits.value = await searchKnowledge(keyword) }
  finally { loading.value = false }
}
function quickSearch(kw: string) {
  q.value = kw
  doSearch()
}

// ---------- 类型/分类映射 ----------
const catFilters = [
  { label: '全部', value: 'all' },
  { label: '学习资源', value: 'learning' },
  { label: '行业资讯', value: 'industry' },
  { label: '校园信息', value: 'campus' },
]
const catLabel = (v: string) => catFilters.find(f => f.value === v)?.label || v
const typeLabel = (v: string) => ({ knowledge: '学习资源', announcement: '校园公告', community: '社区热帖', campus: '校园信息' }[v] || v)
const typeTag = (v: string): any => ({ knowledge: 'primary', announcement: 'warning', community: 'success', campus: 'info' }[v] || 'info')

// ---------- 收藏 ----------
const favorites = ref<Favorite[]>([])
const favMap = ref<Record<string, number>>({}) // `${item_type}:${item_id}` -> fav_id

async function loadFavorites() {
  favorites.value = await getFavorites()
  favMap.value = {}
  for (const f of favorites.value) {
    favMap.value[`${f.item_type}:${f.item_id}`] = f.id
  }
}
const isFaved = (r: ResourceItem | RecommendItem) => !!favMap.value[`${r.item_type}:${r.item_id}`]

async function toggleFav(r: ResourceItem | RecommendItem) {
  const key = `${r.item_type}:${r.item_id}`
  if (favMap.value[key]) {
    await removeFavorite(favMap.value[key])
    ElMessage.success('已取消收藏')
  } else {
    await addFavorite({ item_type: r.item_type, item_id: r.item_id, title: r.title, category: r.category, summary: r.summary, link: r.link })
    ElMessage.success('已收藏')
  }
  await loadFavorites()
}
async function unfav(f: Favorite) {
  await removeFavorite(f.id)
  ElMessage.success('已取消收藏')
  await loadFavorites()
}

// ---------- 为你发现 ----------
const recommends = ref<RecommendItem[]>([])
const recoLoading = ref(false)
async function loadRecommend() {
  recoLoading.value = true
  try { recommends.value = await getRecommend(6) }
  catch { recommends.value = [] }
  finally { recoLoading.value = false }
}

// ---------- 资源浏览 ----------
const cat = ref('all')
const browseQ = ref('')
const items = ref<ResourceItem[]>([])
const browseLoading = ref(false)
const browsePageNum = ref(1)
const browseTotal = ref(0)
const pageSize = 6

function switchCat(c: string) {
  cat.value = c
  browsePage(1)
}
async function browsePage(p: number) {
  browsePageNum.value = p
  browseLoading.value = true
  try {
    const params: any = { page: p, page_size: pageSize }
    if (cat.value !== 'all') params.category = cat.value
    if (browseQ.value.trim()) params.q = browseQ.value.trim()
    const list = await getResourceItems(params)
    items.value = list
    browseTotal.value = list.length < pageSize ? (p - 1) * pageSize + list.length : p * pageSize + 1
  } finally { browseLoading.value = false }
}

// ---------- 订阅源管理 ----------
const sourceDialogVisible = ref(false)
const sources = ref<FeedSource[]>([])
const sourceLoading = ref(false)
const editingId = ref<number | null>(null)
const editForm = ref({ name: '', url: '' })
const addForm = ref({ name: '', kind: 'rss', source_type: 'papers', url: '', filter_kw: '' })

const kindLabel = (k: string) => ({ rss: 'RSS', html: '网页', arxiv: 'arXiv', github: 'GitHub', gitee: 'Gitee', lmarena: '权威榜' }[k] || k)
const sourceTypeLabel = (t: string) => feedTabs.find(x => x.key === t)?.label || t

async function openSourceDialog() {
  sourceDialogVisible.value = true
  sourceLoading.value = true
  try { sources.value = await getFeedSources('all') }
  finally { sourceLoading.value = false }
}
function startEdit(row: FeedSource) {
  editingId.value = row.id
  editForm.value = { name: row.name, url: row.url }
}
async function saveSource(row: FeedSource) {
  await updateFeedSource(row.id, { name: editForm.value.name, url: editForm.value.url })
  ElMessage.success('已保存')
  editingId.value = null
  openSourceDialog()
}
async function toggleSource(row: FeedSource) {
  await updateFeedSource(row.id, { enabled: !row.enabled })
  ElMessage.success(row.enabled ? '已启用' : '已停用')
  openSourceDialog()
}
async function removeSource(row: FeedSource) {
  await deleteFeedSource(row.id)
  ElMessage.success('已删除')
  openSourceDialog()
}
async function addSource() {
  const name = addForm.value.name.trim()
  const url = addForm.value.url.trim()
  if (!name || !url) { ElMessage.warning('请填写名称和地址'); return }
  try {
    await createFeedSource({
      name, kind: addForm.value.kind as any, source_type: addForm.value.source_type as any,
      url,
      filter_kw: addForm.value.filter_kw.split(/[,，]/).map(s => s.trim()).filter(Boolean),
    })
    ElMessage.success('订阅源已添加，刷新资讯后生效')
    addForm.value = { name: '', kind: 'rss', source_type: addForm.value.source_type, url: '', filter_kw: '' }
    openSourceDialog()
  } catch (e: any) {
    ElMessage.warning(e?.response?.data?.detail || '添加失败')
  }
}

// ---------- 工具 ----------
function formatDate(t: string) {
  return t ? String(t).slice(0, 10) : ''
}
function openLink(link?: string | null) {
  if (link) window.open(link, '_blank')
}

onMounted(async () => {
  await Promise.all([loadFavorites(), loadRecommend(), browsePage(1), loadFeed(activeFeedTab.value)])
})
</script>

<style scoped>
/* ========== 移动端优先布局（始终移动宽度居中，参考今日头条/澎湃：吸顶品牌头 + 频道栏 + 卡片信息流） ========== */
.resources-page {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: #f5f6fa;
  color: #1a1a2e;
  padding-bottom: calc(28px + env(safe-area-inset-bottom, 0px));
}

/* 吸顶头部 */
.res-topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 55%, #06b6d4 100%);
  color: #fff;
  padding: calc(14px + env(safe-area-inset-top, 0px)) 14px 0;
  border-radius: 0 0 18px 18px;
  box-shadow: 0 4px 18px rgba(37, 99, 235, 0.22);
}
.topbar-main { display: flex; align-items: center; gap: 10px; }
.brand { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.brand-emoji {
  width: 42px; height: 42px; border-radius: 12px; flex-shrink: 0;
  background: rgba(255, 255, 255, 0.18);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 22px;
}
.brand-text { min-width: 0; }
.res-title { margin: 0; font-size: 18px; font-weight: 700; color: #fff; line-height: 1.3; }
.res-sub { margin: 2px 0 0; font-size: 11px; color: rgba(255, 255, 255, 0.75); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.topbar-actions { display: flex; gap: 8px; flex-shrink: 0; }
.tb-btn.el-button {
  border: none; background: rgba(255, 255, 255, 0.18); color: #fff;
  border-radius: 10px; height: 34px;
}
.tb-btn.el-button:hover, .tb-btn.el-button.is-plain:hover {
  background: rgba(255, 255, 255, 0.3); color: #fff;
}

/* 频道栏：横向滚动胶囊 */
.channel-bar {
  display: flex; gap: 8px;
  overflow-x: auto; scrollbar-width: none;
  padding: 12px 2px 12px;
  -webkit-overflow-scrolling: touch;
}
.channel-bar::-webkit-scrollbar { display: none; }
.channel-item {
  flex-shrink: 0;
  font-size: 13px;
  padding: 6px 15px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.channel-item:active { transform: scale(0.94); }
.channel-item.active {
  background: #fff; color: #2563eb;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.14);
}

/* 通用卡片 */
.res-card {
  background: #fff;
  border-radius: 14px;
  padding: 14px;
  margin: 12px 12px 0;
  box-shadow: 0 1px 8px rgba(31, 41, 55, 0.05);
}
.card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.head-bar { width: 4px; height: 15px; background: linear-gradient(180deg, #2563eb, #06b6d4); border-radius: 3px; }
.head-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.head-sub { margin-left: auto; font-size: 11px; color: #98a0b0; }
.empty-tip { color: #98a0b0; font-size: 13px; text-align: center; padding: 22px 0; }

/* 资讯信息流 */
.feed-tip { font-size: 11px; color: #a0a6b5; margin: 0 0 10px; }
.feed-body { min-height: 80px; }
.feed-item {
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: #f8fafc;
  border: 1px solid #f0f2f7;
}
.feed-item-title { font-size: 15px; font-weight: 600; color: #1f2937; line-height: 1.45; cursor: pointer; }
.feed-item-title:active { color: #2563eb; }
.feed-meta-badges { display: flex; align-items: center; gap: 12px; margin-top: 7px; flex-wrap: wrap; }
.feed-meta-badges span { display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: #6b7280; }
.feed-meta-badges .feed-lang {
  background: rgba(37, 99, 235, 0.09); color: #2563eb; border-radius: 6px; padding: 0 6px;
}
.feed-item-foot { display: flex; align-items: center; gap: 8px; margin-top: 9px; flex-wrap: wrap; }
.foot-spacer { flex: 1; }
.feed-badge {
  font-size: 11px; color: #fff; font-weight: 600; border-radius: 8px; padding: 2px 8px; flex-shrink: 0;
}
.feed-badge.papers { background: #6038c7; }
.feed-badge.opensource { background: #0f6b3c; }
.feed-badge.agents { background: #c0385a; }
.feed-badge.news { background: #b23c21; }
.feed-badge.ai_news { background: #0a5f8a; }
.feed-badge.rankings { background: #8a4d0a; }
.feed-badge.cn_ai { background: #b02a6b; }
.feed-source { font-size: 12px; color: #8a94a6; }
.feed-time {
  font-size: 11px; color: #b0b6c2; background: #eef0f5; border-radius: 6px; padding: 2px 7px;
}
.fav-btn.el-button { min-height: 30px; }

/* 权威排行榜 */
.rank-item {
  display: flex; align-items: center; gap: 12px;
  border-radius: 12px;
  padding: 11px 12px; margin-bottom: 9px;
  background: #f8fafc;
  border: 1px solid #f0f2f7;
}
.rank-no {
  width: 28px; height: 28px; border-radius: 9px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #fff; background: #aab2bf;
}
.rank-no.gold { background: linear-gradient(135deg, #f7b733, #f39c12); }
.rank-no.silver { background: linear-gradient(135deg, #cfd8e3, #9aa8b8); }
.rank-no.bronze { background: linear-gradient(135deg, #d98a5f, #b26a45); }
.rank-main { flex: 1; min-width: 0; }
.rank-title { font-size: 14px; font-weight: 600; color: #1f2937; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-title:active { color: #2563eb; }
.rank-back { height: 6px; border-radius: 4px; background: #e9ecf2; margin-top: 7px; overflow: hidden; }
.rank-bar {
  display: block; height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, #56b4ff, #1e82e8);
}
.rank-side { flex-shrink: 0; text-align: right; }
.rank-score { font-size: 13px; font-weight: 700; color: #1e82e8; }
.rank-votes { display: block; font-size: 11px; color: #a0a6b5; margin-top: 2px; }

/* 推荐 */
.reco-body { min-height: 60px; }
.reco-item {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 11px 12px;
  margin-bottom: 10px;
  background: #f8fafc;
}
.reco-faved { border-color: rgba(230, 162, 60, 0.5); }
.reco-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.reco-reason {
  font-size: 11px; color: #2563eb; background: rgba(37, 99, 235, 0.08);
  padding: 2px 8px; border-radius: 8px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; max-width: 65%;
}
.reco-title { font-size: 14px; font-weight: 600; color: #1a1a2e; line-height: 1.45; cursor: pointer; }
.reco-title:active { color: #2563eb; }
.reco-meta { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; }
.reco-source { font-size: 11px; color: #98a0b0; }

/* 分类 */
.cat-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 11px; }
.cat-tag { cursor: pointer; }
.browse-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.browse-bar .el-input { flex: 1; }

/* 资源条目 */
.res-item {
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: #f8fafc;
  border: 1px solid #f0f2f7;
}
.res-item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.res-item-cat { font-size: 12px; color: #8a94a6; }
.res-item-title { font-size: 14px; font-weight: 600; color: #1f2937; line-height: 1.45; cursor: pointer; }
.res-item-title:active { color: #2563eb; }
.res-item-summary {
  font-size: 13px; color: #6b7280; line-height: 1.6; margin-top: 4px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.res-item-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.pager-row { display: flex; justify-content: center; padding-top: 6px; }

/* 收藏 */
.fav-item {
  display: flex; align-items: center; gap: 10px;
  border: 1px solid rgba(0, 0, 0, 0.06); border-radius: 12px;
  padding: 11px 12px; margin-bottom: 8px;
  background: #f8fafc;
}
.fav-info { flex: 1; min-width: 0; cursor: pointer; }
.fav-title { font-size: 13px; font-weight: 600; color: #1a1a2e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav-meta { font-size: 11px; color: #98a0b0; margin-top: 2px; }

/* 检索 */
.res-search { display: flex; gap: 10px; }
.res-hot { display: flex; align-items: center; gap: 8px; margin: 14px 0 6px; flex-wrap: wrap; }
.res-hot-label { font-size: 13px; color: #8a94a6; }
.res-hot-tag { cursor: pointer; }
.res-results { min-height: 120px; margin-top: 12px; }
.res-q { font-size: 14px; font-weight: 600; color: #1f2937; margin-bottom: 6px; }
.res-a { font-size: 13px; color: #4b5563; line-height: 1.7; white-space: pre-line; }

/* 订阅源弹窗：窄屏全屏（底部抽屉感） */
.source-tip { font-size: 12px; color: #8a94a6; line-height: 1.6; margin-bottom: 10px; }
.src-name-row { display: flex; align-items: center; }
.src-name { font-weight: 500; }
.src-url { font-size: 12px; color: #8a94a6; }
.add-source { margin-top: 14px; }
.add-source-title { font-size: 13px; font-weight: 600; color: #1a1a2e; margin-bottom: 8px; }
.add-source-row { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
:deep(.source-dialog) { border-radius: 16px; }
:deep(.source-dialog .el-dialog__body) { max-height: 62vh; overflow-y: auto; }

@media (max-width: 768px) {
  :deep(.source-dialog) { width: 94vw !important; }
  :deep(.source-dialog .el-dialog__body) { max-height: 62vh; overflow-y: auto; }
  :deep(.src-url-col) { display: none; }
  .add-source-row .el-input, .add-source-row .el-select { flex: 1 1 46%; }
}
</style>
