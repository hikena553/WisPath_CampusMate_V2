<template>
  <div class="resources-page">
    <div class="res-header">
      <h2 class="res-title">AI 资源空间</h2>
      <p class="res-sub">为你发现 · 学习资源 · 行业资讯 · 校园信息</p>
    </div>

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
            <el-button size="small" text :type="isFaved(r) ? 'warning' : 'default'" @click="toggleFav(r)">
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
            <el-button size="small" text :type="isFaved(it) ? 'warning' : 'default'" @click="toggleFav(it)">
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
import { ref, onMounted } from 'vue'
import { Search, Star, StarFilled, TopRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
import {
  getResourceItems, getRecommend, getFavorites, addFavorite, removeFavorite,
  type ResourceItem, type RecommendItem, type Favorite,
} from '@/api/resources'

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

// ---------- 工具 ----------
function formatDate(t: string) {
  return t ? String(t).slice(0, 10) : ''
}
function openLink(link?: string | null) {
  if (link) window.open(link, '_blank')
}

onMounted(async () => {
  await Promise.all([loadFavorites(), loadRecommend(), browsePage(1)])
})
</script>

<style scoped>
.resources-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 20px;
  background: #f8f9fc;
  min-height: 100vh;
  color: #1a1a2e;
}
.res-header { margin-bottom: 20px; }
.res-title { margin: 0; font-size: 22px; font-weight: 700; color: #1f2937; }
.res-sub { margin: 6px 0 0; font-size: 13px; color: #8a94a6; }

.res-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
  box-shadow: 0 2px 10px rgba(31, 41, 55, 0.04);
}
.card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.head-bar { width: 3px; height: 14px; background: #409eff; border-radius: 2px; }
.head-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.head-sub { margin-left: auto; font-size: 11px; color: #999; }
.empty-tip { color: #999; font-size: 13px; text-align: center; padding: 20px 0; }

/* 推荐 */
.reco-body { min-height: 60px; }
.reco-item {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.reco-faved { border-color: rgba(230, 162, 60, 0.5); }
.reco-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.reco-reason {
  font-size: 11px; color: #409eff; background: rgba(64, 158, 255, 0.08);
  padding: 2px 8px; border-radius: 8px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; max-width: 60%;
}
.reco-title { font-size: 14px; font-weight: 600; color: #1a1a2e; cursor: pointer; }
.reco-title:hover { color: #409eff; }
.reco-meta { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; }
.reco-source { font-size: 11px; color: #999; }

/* 分类 */
.cat-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.cat-tag { cursor: pointer; }
.browse-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.browse-bar .el-input { flex: 1; }

/* 资源条目 */
.res-item {
  border: 1px solid #eef0f4;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.res-item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.res-item-cat { font-size: 12px; color: #8a94a6; }
.res-item-title { font-size: 14px; font-weight: 600; color: #1f2937; cursor: pointer; }
.res-item-title:hover { color: #409eff; }
.res-item-summary {
  font-size: 13px; color: #6b7280; line-height: 1.6; margin-top: 4px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.res-item-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.pager-row { display: flex; justify-content: center; padding-top: 6px; }

/* 收藏 */
.fav-item {
  display: flex; align-items: center; gap: 10px;
  border: 1px solid rgba(0, 0, 0, 0.06); border-radius: 10px;
  padding: 10px 12px; margin-bottom: 8px;
}
.fav-info { flex: 1; min-width: 0; cursor: pointer; }
.fav-title { font-size: 13px; font-weight: 600; color: #1a1a2e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav-meta { font-size: 11px; color: #999; margin-top: 2px; }

/* 检索 */
.res-search { display: flex; gap: 12px; }
.res-hot { display: flex; align-items: center; gap: 8px; margin: 14px 0 6px; flex-wrap: wrap; }
.res-hot-label { font-size: 13px; color: #8a94a6; }
.res-hot-tag { cursor: pointer; }
.res-results { min-height: 120px; margin-top: 12px; }
.res-q { font-size: 14px; font-weight: 600; color: #1f2937; margin-bottom: 6px; }
.res-a { font-size: 13px; color: #4b5563; line-height: 1.7; white-space: pre-line; }
</style>