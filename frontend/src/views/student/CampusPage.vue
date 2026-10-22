<template>
  <div class="campus-page">
    <!-- ===== 页头（桌面 / 移动两套，刻意不合并：两者版式差一整代）=====
         桌面端：白底通栏大标题 + 纯图标搜索；标题本身可点 = 刷新（标题是这页最强的
         「我要看这个」暗示，点它重取比多放一个按钮更省地方）。
         移动端（2026-10 改版，一比一复刻资讯流 App）：
           ① 白底页头：左侧 26px/700 黑色大标题，右侧两枚纯黑线性图标（搜索 / 通知）；
           ② 白底分类 Tab：选中项黑色粗体 + 3px 黑色下划线，其余灰色，可横向滑动；
           ③ 信息流：17px 粗体标题两行 + 13px 灰色元信息，右侧大缩略图，
              行间 1px 浅灰分割线。
         移动端不提供手动刷新：由 10 分钟模块缓存 + 后端 5 分钟缓存兜住，重进页面即可重新取数。
         不放返回箭头：本页是底部导航的一级 Tab，没有「上一页」可回。 -->
    <header v-if="isMobile" class="campus-appbar">
      <div class="appbar-title">
        <h1>校园资讯</h1>
      </div>
      <div class="appbar-actions">
        <button
          v-if="isGuestMode()"
          type="button"
          class="appbar-login"
          @click="goLogin"
        >
          登录
        </button>
        <button
          type="button"
          class="appbar-btn"
          aria-label="搜索校园资讯"
          @click="openSearch"
        >
          <el-icon><Search /></el-icon>
        </button>
        <button
          type="button"
          class="appbar-btn"
          aria-label="通知公告"
          @click="switchTab('jwc_tzgg')"
        >
          <el-icon><Message /></el-icon>
        </button>
      </div>
    </header>

    <section v-else class="campus-hero-head">
      <button
        class="hero-head-text"
        type="button"
        :disabled="refreshing"
        aria-label="刷新校园资讯"
        @click="refreshImpression"
      >
        <h2>校园资讯</h2>
      </button>
      <button
        class="hero-head-search"
        type="button"
        aria-label="搜索校园资讯"
        @click="openSearch"
      >
        <el-icon><Search /></el-icon>
      </button>
    </section>

    <!-- 搜索浮层：先在本页已加载的资讯里过滤，一条都没有再兜到知识库检索。
         这个顺序符合直觉 —— 用户在这页点搜索，多半想找刚看到的某条资讯；
         本页资讯是「校内动态」、知识库是「办事问答」，两层语义不同但都该给到。 -->
    <el-dialog v-model="searchVisible" title="搜索校园资讯" width="600px">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索资讯标题，如：图书馆、放假、招聘……"
        :prefix-icon="Search"
        clearable
        @keyup.enter="runSearch"
      />
      <div class="search-hot">
        <span class="search-hot-label">热门：</span>
        <el-tag
          v-for="kw in SEARCH_HOT_KEYWORDS"
          :key="kw"
          class="search-hot-tag"
          effect="plain"
          @click="quickSearch(kw)"
        >{{ kw }}</el-tag>
      </div>

      <!-- ① 本页资讯命中 -->
      <div v-if="searchDone" class="search-block">
        <div class="search-block-title">校园资讯（{{ newsHits.length }}）</div>
        <a
          v-for="h in newsHits"
          :key="h.url + h.title"
          class="search-hit"
          :href="h.url"
          @click.prevent="openSearchHit(h)"
        >
          <span class="search-hit-source">{{ h.sourceLabel }}</span>
          <span class="search-hit-title">{{ h.title }}</span>
          <span v-if="h.date" class="search-hit-date">{{ h.date }}</span>
        </a>
        <p v-if="!newsHits.length" class="search-empty">本页资讯中没有匹配项</p>
      </div>

      <!-- ② 知识库兜底：仅在本页资讯 0 命中时才去查，避免无谓的后端检索 -->
      <div v-if="searchDone" class="search-block">
        <div class="search-block-title">
          知识库{{ knowledgeLoading ? '' : `（${knowledgeHits.length}）` }}
        </div>
        <p v-if="knowledgeLoading" class="search-empty">检索中…</p>
        <template v-else-if="knowledgeHits.length">
          <div v-for="(h, i) in knowledgeHits" :key="i" class="search-hit search-hit-static">
            <span class="search-hit-source">{{ h.category || (h.type === 'qa' ? '问答' : '文档') }}</span>
            <span class="search-hit-title">{{ h.question || h.content || '未命名' }}</span>
          </div>
        </template>
        <p v-else-if="isGuestMode()" class="search-empty">
          知识库检索需要登录，<a href="javascript:;" @click.prevent="promptLogin('检索全校知识库')">去登录</a>
        </p>
        <p v-else class="search-empty">知识库中也没有找到相关内容</p>
      </div>
    </el-dialog>

    <!-- 移动端分类 Tab：横向滑动、选中项黑色加粗 + 短下划线。
         与下方信息流共用同一份数据，切换只是换 filter，不重新请求。
         吸顶说明：本页滚动容器是 .campus-page，这些区块要跟着页头一起吸住，
         否则页头吸顶、Tab 滚走，分类切换就失去意义。
         不放条数角标：7 个分类在 390px 宽下已接近满宽，再加数字会把「图书馆」
         挤出首屏却看不到可滑动的暗示。 -->
    <nav v-if="isMobile" class="campus-tabs" role="tablist" aria-label="资讯分类">
      <button
        v-for="t in mobileTabs"
        :key="t.key"
        type="button"
        role="tab"
        class="campus-tab"
        :class="{ 'is-active': activeTab === t.key }"
        :aria-selected="activeTab === t.key"
        @click="switchTab(t.key)"
      >
        {{ t.label }}
      </button>
    </nav>

    <!-- 移动端大图轮播：**只在「全部」Tab 顶部**渲染（其余分类是纯信息流）。
         图源 = 全部资讯里带 image_url 的最新条目（教学动态详情页抓到的主图），
         按日期倒序最多 5 张；一张带图的都没有时回落到本地校园风光，避免首屏空一块。
         点击进站内阅读器（与信息流一致），不跳出应用。
         按住图片左右拖动即可切换（鼠标 / 触屏同一套 Pointer 事件逻辑）。
         注意：拖动事件挂在 .hero-track（图片区域）上，**不是**外层 section ——
         挂在外层的话，在标题或留白处按下也会拖着整块轮播平移，像是「整个组件可拖」。
         切换分类时用 :key 重建，轮播计时归零、下次切回「全部」从第 1 张开始。 -->
    <section
      v-if="isMobile && heroSlides.length"
      class="campus-hero-carousel"
      :class="{ 'is-dragging': heroDragging, 'is-resetting': heroResettingTrack }"
      :style="{ '--hero-drag-x': `${heroDragX}px` }"
    >
      <!-- .hero-track 只承担两件事：接收 Pointer 事件、作为自绘指示点的定位参照。
           它**不做位移** —— 位移交给内部的轮播容器（.el-carousel__container，也就是图片那一层），
           这样卡片的圆角与边框始终不动，只有卡片里的图片跟着手指滑动。
           事件绑在外层、位移作用在内层是刻意的：事件层不动，命中区域才稳定。 -->
      <div
        class="hero-track"
        @pointerdown="onHeroPointerDown"
        @pointermove="onHeroPointerMove"
        @pointerup="onHeroPointerUp"
        @pointercancel="onHeroPointerCancel"
        @dragstart="onHeroSlideDragStart"
      >
        <el-carousel
          ref="heroCarouselRef"
          :key="activeTab"
          :autoplay="heroAutoplay"
          :interval="4200"
          height="196px"
          arrow="never"
          indicator-position="none"
          trigger="click"
          @change="onHeroIndexChange"
        >
          <el-carousel-item v-for="s in heroSlides" :key="s.url">
            <a
              class="hero-slide"
              :href="s.url || undefined"
              @click="onHeroSlideClick($event, s)"
            >
              <img class="hero-slide-img" :src="s.image_url" alt="" loading="lazy" draggable="false" />
              <div class="hero-slide-shade" />
              <div class="hero-slide-caption">
                <span class="hero-slide-tag">{{ s.tagLabel }}</span>
                <h3 class="hero-slide-title">{{ s.title }}</h3>
              </div>
            </a>
          </el-carousel-item>
        </el-carousel>
        <!-- 指示点：叠在图片底边内侧，属于卡片装饰，**不跟着图片一起位移**
             （它在 .hero-track 里、不在位移层里）。用绝对定位定位，不参与轮播盒子尺寸。
             纯装饰：pointer-events: none，不影响拖动与点击。 -->
        <div class="hero-dots" aria-hidden="true">
          <span
            v-for="(s, i) in heroSlides"
            :key="s.url + i"
            class="hero-dot"
            :class="{ 'is-active': i === heroIndex }"
          />
        </div>
      </div>
    </section>

    <!-- 移动端信息流：标题两行 + 元信息行 + 右侧缩略图 + 行尾互动数 -->
    <section v-if="isMobile" class="campus-feed">
      <a
        v-for="item in mobileFeed"
        :key="item.url + item.title"
        class="feed-item"
        :href="item.url"
        @click.prevent="openArticle(item.url, item.title)"
      >
        <div class="feed-body">
          <h3 class="feed-title">{{ item.title }}</h3>
          <div class="feed-meta">
            <span class="feed-time">{{ item.timeLabel }}</span>
            <span class="feed-dot">·</span>
            <span class="feed-source">{{ item.sourceLabel }}</span>
          </div>
        </div>
        <!-- 只有真的有图才渲染缩略图：参考稿无图条目是通栏标题，不留右侧空位 -->
        <div v-if="item.image_url" class="feed-thumb">
          <img :src="item.image_url" loading="lazy" alt="" />
        </div>
      </a>
      <p v-if="!mobileFeed.length" class="feed-empty">该分类暂无内容</p>
    </section>

    <!-- 以下为桌面端版式（移动端整块隐藏：由上面的 Tab + 信息流替代） -->
    <template v-if="!isMobile">

    <!-- ① 校园风光轮播图（桌面端专属；移动端首屏已改为 Tab + 信息流） -->
    <section class="campus-carousel">
      <el-carousel :interval="4000" height="320px" arrow="hover" trigger="click">
        <el-carousel-item v-for="img in carouselImages" :key="img.image_url">
          <div class="carousel-item">
            <img :src="img.image_url" class="carousel-img" />
            <div class="carousel-overlay">
              <span class="carousel-title">{{ img.title }}</span>
              <span class="carousel-campus">{{ img.campus }}</span>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
    </section>

    <!-- ② 教务系统入口
         移动端（≤767px）：一张白卡 + 3×2 瓷片宫格，6 个入口瓷片完全同口径（浅蓝底 + 蓝图标），
         主入口「教务管理系统」只靠首位顺序 + 标题字重区分。桌面端沿用原来的 3 列白卡 + 单色图标。 -->
    <section class="campus-section">
      <div class="section-title">教务系统入口</div>
      <div class="entry-card">
        <div class="entry-grid">
          <a v-for="e in visibleEntries" :key="e.url" class="entry-item" :class="{ 'is-primary': isPrimaryEntry(e.title) }"
             :href="e.url" target="_blank" rel="noopener noreferrer"
             :title="entryHint(e.url)" :style="{ '--entry-color': getEntryColor(e.title) }" @click="onEntryClick(e, $event)">
            <span class="entry-chip"><el-icon class="entry-icon"><component :is="getEntryIcon(e.title)" /></el-icon></span>
            <p>{{ e.title }}</p>
            <span v-if="opensInNewWindow(e.url)" class="entry-external">↗</span>
          </a>
        </div>
      </div>
    </section>

    <!-- ② 教学动态 + 通知公告 -->
    <section class="campus-duo">
      <div class="campus-card campus-card-jx" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><DataBoard /></el-icon> 教学动态</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jwgl/jxdt.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jwgl/jxdt.htm', '教学动态')">查看详情 →</a>
        </div>
        <!-- 首条图文大图：桌面端保留在卡内（移动端整块走页面顶部的信息流，不用卡片版式） -->
        <a v-if="impression.jxdt.length" class="jxdt-first" :href="impression.jxdt[0].url" @click.prevent="openArticle(impression.jxdt[0].url, impression.jxdt[0].title)">
          <img v-if="impression.jxdt[0].image_url" :src="impression.jxdt[0].image_url" class="jxdt-first-img" />
          <span class="jxdt-first-title">{{ impression.jxdt[0].title }}</span>
        </a>
        <a v-for="a in impression.jxdt.slice(0, 5)" :key="a.url" class="news-row jxdt-date-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="jxdt-day"><b>{{ splitDay(a.date) }}</b><span class="jxdt-month">{{ splitMonth(a.date) }}</span></span>
          <span class="news-text">{{ a.title }}</span>
        </a>
      </div>
      <div class="campus-card" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Notification /></el-icon> 通知公告</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jwgl/tzgg.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jwgl/tzgg.htm', '通知公告')">查看详情 →</a>
        </div>
        <a v-for="a in impression.tzgg" :key="a.url" class="tzgg-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="tzgg-date">{{ formatDate(a.date) }}</span>
          <span class="news-text">{{ removeCommonPrefix(a.title) }}</span>
        </a>
      </div>
    </section>

    <!-- ③ 高教信息 + 教学建设 -->
    <section class="campus-duo campus-duo-gjxx">
      <div class="campus-card campus-card-gjxx" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><School /></el-icon> 高教信息</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/gjxx.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/gjxx.htm', '高教信息')">查看详情 →</a>
        </div>
        <div class="gjxx-grid">
          <a v-for="a in impression.gjxx" :key="a.url" class="gjxx-item" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
            <el-icon class="gjxx-icon"><Document /></el-icon>
            <span class="gjxx-title">{{ removeCommonPrefix(a.title) }}</span>
            <el-icon class="gjxx-arrow"><ArrowRight /></el-icon>
          </a>
        </div>
      </div>
      <div class="campus-card" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Collection /></el-icon> 教学建设</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jxjs.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jxjs.htm', '教学建设')">查看详情 →</a>
        </div>
        <a v-for="a in impression.jxjs.slice(0, 7)" :key="a.url" class="build-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="build-mark"></span>
          <el-tooltip :content="removeCommonPrefix(a.title)" placement="top" :show-after="300">
            <span class="build-text">{{ removeCommonPrefix(a.title) }}</span>
          </el-tooltip>
          <span class="build-date">{{ a.date }}</span>
        </a>
      </div>
    </section>

    <!-- ④ 专业分院 -->
    <section class="campus-card campus-card-college">
      <div class="card-head">
        <span class="card-title"><el-icon><School /></el-icon> 专业分院</span>
        <span class="section-tag">新闻实时更新</span>
      </div>
      <!-- 桌面端：卡片网格 -->
      <div class="card-body college-body-pc">
        <div class="college-grid">
          <a v-for="c in collegeCards" :key="c.name" class="college-card" :href="c.url" @click.prevent="openArticle(c.url, c.name)">
            <div class="college-head">
              <el-icon class="college-icon" :style="{ color: c.color }"><component :is="c.icon" /></el-icon>
              <span class="college-name">{{ c.name }}</span>
            </div>
            <div class="college-list">
              <div v-for="n in collegeTopNews(c.name)" :key="n.url" class="college-news">
                <span class="news-dot">▪</span><span class="news-text" :title="n.title">{{ n.title }}</span>
                <span v-if="n.day" class="college-date">{{ n.day }}</span>
              </div>
              <!-- 固定补满 2 条槽位：学院 0 条时显示"暂无最新动态"，1 条时补一行空白，
                   保证 7 张卡的新闻区等高、卡片不塌陷 -->
              <div v-if="collegeTopNews(c.name).length < 2" class="college-news">
                <span v-if="!collegeTopNews(c.name).length" class="college-empty">暂无最新动态</span>
              </div>
            </div>
            <span class="college-link">进入官网 →</span>
          </a>
        </div>
      </div>
    </section>

    <!-- ⑤ 绵城印象 + 图书馆 -->
    <section class="campus-duo campus-duo-lib">
      <div class="campus-card campus-card-impression" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><OfficeBuilding /></el-icon> 绵城印象</span>
          <a class="card-more" href="https://www.mycc.edu.cn/mcyx/" @click.prevent="openArticle('https://www.mycc.edu.cn/mcyx/', '绵城印象')">了解更多 →</a>
        </div>
        <div class="impression-list">
          <a v-for="item in impressionItems" :key="item.title" class="impression-row" :href="item.url" @click.prevent="openArticle(item.url, item.title)">
            <el-icon class="impression-icon" :style="{ color: item.color }"><component :is="item.icon" /></el-icon>
            <div class="impression-info">
              <span class="impression-name">{{ item.title }}</span>
              <span class="impression-desc">{{ item.desc }}</span>
            </div>
            <el-icon class="impression-arrow"><ArrowRight /></el-icon>
          </a>
        </div>
      </div>
      <div class="campus-card campus-card-library" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Reading /></el-icon> 图书馆公告</span>
          <a v-if="libraryHome" class="card-more" :href="libraryHome" @click.prevent="openArticle(libraryHome, '图书馆')">进入官网 →</a>
        </div>
        <div class="lib-list">
          <!-- 移动端统一展示 5 条（与教学动态/通知公告列表一致）；桌面端维持 4 条 -->
          <a v-for="a in impression.library.slice(0, 4)" :key="a.title" class="lib-item" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
            <span class="lib-date">{{ formatDate(a.date) }}</span>
            <span class="lib-title">{{ a.title }}</span>
          </a>
        </div>
      </div>
    </section>

    </template>

    <!-- 站内阅读器：点击资讯在应用内打开，不跳出。
         必须放在 .campus-page 内部 —— 它原先与 .campus-page 同级，
         导致本组件是「多根节点（Fragment）」，而 Vue 的 <Transition>
         无法对 Fragment 根做动画，控制台会报
         「Component inside <Transition> renders non-element root node that cannot be animated」，
         且整个页面的切换动画会失效。
         阅读器自己会 Teleport 抽屉到 body，放在这里不会影响布局。 -->
    <ArticleReader ref="readerRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElCarousel } from 'element-plus'
import { getImpression } from '@/api/campus'
import type { ImpressionItem } from '@/types'
import { getCampusImpressionCache, setCampusImpressionCache } from '@/utils/studentDataCache'
import { tilt } from '@/directives/tilt'
import ArticleReader from '@/components/campus/ArticleReader.vue'
import {
  Calendar, Monitor, DataLine, Reading, TrendCharts,
  Document, Clock, Box, Van, ArrowRight,
  Notification, DataBoard,
  School, Collection,
  SetUp, Histogram, HomeFilled, OfficeBuilding, Search, Message
} from '@element-plus/icons-vue'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
import { isGuestMode } from '@/utils/guest'
import { promptLogin } from '@/utils/loginGate'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

/** 游客回登录页：清掉游客标记后进入登录页（与布局顶栏的登录入口保持同一行为） */
function goLogin() {
  auth.exitGuest()
  router.push({ path: '/login', query: { reason: 'login' } })
}

const vTilt = tilt
const isMobile = ref(window.innerWidth <= 767)
window.addEventListener('resize', () => { isMobile.value = window.innerWidth <= 767 })

/** 站内阅读器：点击资讯在应用内打开（移动端全屏抽屉），不跳出应用。
    站内阅读需要登录态，游客点击时先引导登录。 */
const readerRef = ref<InstanceType<typeof ArticleReader> | null>(null)
function openArticle(url: string, title?: string) {
  if (!url) return
  if (isGuestMode()) {
    void promptLogin('阅读资讯全文')
    return
  }
  readerRef.value?.open(url, title)
}

interface GalleryImage {
  title: string
  image_url: string
  campus: string
}

/** 初始值直接取模块级缓存：二次进入命中时首帧就是真实内容，不会闪空态 */
const impressionData = ref<ImpressionItem[]>(getCampusImpressionCache() ?? [])

/** 刷新在途态：桌面端「点标题刷新」用，防重复点击（连点会重复打后端） */
const refreshing = ref(false)

function byDateDesc(a: ImpressionItem, b: ImpressionItem) {
  const da = a.date ? Date.parse(a.date) : NaN
  const db = b.date ? Date.parse(b.date) : NaN
  if (Number.isNaN(da) && Number.isNaN(db)) return 0
  if (Number.isNaN(da)) return 1
  if (Number.isNaN(db)) return -1
  return db - da
}

// 去掉公共前缀
function removeCommonPrefix(title: string) {
  const prefixes = ['绵阳城市学院关于', '绵阳城市学院']
  for (const p of prefixes) {
    if (title.startsWith(p)) {
      return title.slice(p.length)
    }
  }
  return title
}

// 去重（按title去重）
function deduplicateByTitle(items: ImpressionItem[]) {
  const seen = new Set<string>()
  return items.filter(item => {
    if (seen.has(item.title)) return false
    seen.add(item.title)
    return true
  })
}

const impression = computed(() => {
  const all = impressionData.value
  const bySource = (s: string) => deduplicateByTitle(all.filter(i => i.source === s).sort(byDateDesc))
  return {
    entries: bySource('jwc_entries'),
    jxdt: bySource('jwc_jxdt'),
    tzgg: bySource('jwc_tzgg'),
    gjxx: bySource('jwc_gjxx'),
    jxjs: bySource('jwc_jxjs'),
    library: bySource('library'),
    collegeNews: groupCollegeNews(all),
  }
})

/** 图书馆官网入口：取自后端抓取结果（域名可用 .env 的 LIBRARY_SITE_URL 覆盖）；无数据时不展示死链 */
const libraryHome = computed(() => impression.value.library[0]?.url || '')

function groupCollegeNews(all: ImpressionItem[]): Record<string, ImpressionItem[]> {
  const map: Record<string, ImpressionItem[]> = {}
  for (const i of all.filter(x => x.source === 'college_news')) {
    if (!map[i.college_key!]) map[i.college_key!] = []
    map[i.college_key!].push(i)
  }
  for (const key of Object.keys(map)) map[key].sort(byDateDesc)
  return map
}

/** 卡片上展示的学院新闻条数：2 条足够，再多会把网格行高撑得参差 */
const COLLEGE_NEWS_LIMIT = 2

/** 7 个学院：名称必须与后端 college_key 完全一致，否则取不到新闻（取不到时按空态渲染） */
const collegeCards = [
  { name: '马克思主义学院', url: 'https://mksxy.mycc.edu.cn/', icon: Reading, color: '#e74c3c' },
  { name: '人工智能学院', url: 'https://xdjsxy.mycc.edu.cn/', icon: Monitor, color: '#409eff' },
  { name: '智能制造与工程学院', url: 'https://xdcsjsxy.mycc.edu.cn/', icon: SetUp, color: '#e67e22' },
  { name: '健康与教育学院', url: 'https://xdfw.mycc.edu.cn/', icon: OfficeBuilding, color: '#27ae60' },
  { name: '商学院', url: 'https://jgxy.mycc.edu.cn/', icon: Histogram, color: '#9b59b6' },
  { name: '创意设计学院', url: 'https://cysjxy.mycc.edu.cn/', icon: Collection, color: '#f39c12' },
  { name: '终身教育学院', url: 'https://jxjy.mycc.edu.cn/', icon: School, color: '#1abc9c' },
]

/**
 * 学院新闻取前 N 条。
 * - 每个学院固定取相同条数，配合 .college-card 的 flex 列布局 + .college-list 的
 *   min-height，保证各卡片「图标 / 新闻区 / 进入官网」三段基线对齐，空数据学院也不塌陷；
 * - 条数与日期都在这里一次算完并缓存，模板里只做取值，日期不重复解析；
 * - 不用 `impression.collegeNews[c.name] || []` 直接 v-for：学院名与后端
 *   college_key 对不上时 map 取到 undefined，会得到 0 条而非报错，这里统一兜成 []。
 */
const collegeNewsMap = computed<Record<string, { url: string; title: string; day: string }[]>>(() => {
  const out: Record<string, { url: string; title: string; day: string }[]> = {}
  const grouped = impression.value.collegeNews
  for (const c of collegeCards) {
    out[c.name] = (grouped[c.name] || []).slice(0, COLLEGE_NEWS_LIMIT).map(n => ({
      url: n.url,
      title: n.title,
      day: formatDate(n.date),
    }))
  }
  return out
})

function collegeTopNews(name: string) {
  return collegeNewsMap.value[name] || []
}

// 教务系统入口图标映射
const entryIconMap: Record<string, any> = {
  '教务管理系统': Monitor,
  '课表查询': Calendar,
  '教学校历': DataLine,
  '超星在线学习平台': Reading,
  '教学质量管理平台': TrendCharts,
  '毕业论文管理系统': Document,
  '实习管理系统': Box,
  '实验管理平台': Van,
  '作息时间': Clock,
}

// 获取入口图标
function getEntryIcon(title: string) {
  for (const [key, icon] of Object.entries(entryIconMap)) {
    if (title.includes(key) || key.includes(title)) {
      return icon
    }
  }
  return Monitor
}

// 教务入口配色（桌面端）：整组入口图标统一用中性深灰 #4E5969
// （灰 = 底层系统入口，把彩色权重让给页面里的教学动态/专业分院等内容区）。
// 移动端不吃这里的颜色 —— 移动端是「浅蓝瓷片 + 主入口实心蓝」，配色在样式区 @media 块里。
// 想给某个入口单独提色，只需在 ENTRY_COLOR_MAP 里加一条「标题关键词: 色值」，会覆盖默认灰。
const ENTRY_COLOR_MAP: Record<string, string> = {}
const DEFAULT_ENTRY_COLOR = '#4E5969'

function getEntryColor(title: string) {
  for (const [key, color] of Object.entries(ENTRY_COLOR_MAP)) {
    if (title.includes(key) || key.includes(title)) return color
  }
  return DEFAULT_ENTRY_COLOR
}

// 主入口：教务管理系统（学生 90% 的入口使用都在这一个上）。
// 移动端 6 个瓷片完全同口径，主入口只靠「排在第一位 + 标题字重 600」区分；
// 不给它单独上实心蓝 —— 宫格里一块实心会被读成「当前选中」，那是错的语义。
function isPrimaryEntry(title: string) {
  return title.includes('教务管理系统')
}

// 站内阅读器能渲染的校内静态页（实测：jwc 内容页返回链接清单可读；
// jwgl.mycc.edu.cn / syglxt.mycc.edu.cn 是登录型系统，抓取返回 502，无法内嵌）
function isInAppReadable(url: string) {
  return /^https?:\/\/jwc\.mycc\.edu\.cn\//i.test(url)
}

// 是否只能在新窗口打开：登录型教务/实验系统与站外 SaaS 都无法内嵌
// （学校站点统一设了 X-Frame-Options: SAMEORIGIN，禁止 iframe）
function opensInNewWindow(url: string) {
  return !isInAppReadable(url)
}

// 登录型校内系统（教务/实验平台）：能连上但拿不到未登录内容，只能新窗口打开
function isLoginPortal(url: string) {
  return /^https?:\/\/(jwgl|syglxt)\.mycc\.edu\.cn/i.test(url)
}

function entryHint(url: string) {
  if (isInAppReadable(url)) return '在应用内打开'
  if (isLoginPortal(url)) return '需要登录的校内系统，将在新窗口打开'
  return '站外系统，将在新窗口打开'
}

// 入口点击：可站内阅读的走阅读器，其余交给 <a target="_blank"> 原生行为
// （保留中键/右键"在新标签页打开"）
function onEntryClick(e: { url: string; title: string }, ev: MouseEvent) {
  if (!isInAppReadable(e.url)) return
  ev.preventDefault()
  openArticle(e.url, e.title)
}

// “教务系统入口”网格中不展示的项：课表查询/教学校历/作息时间都是教务处静态工具页，
// 与应用内页面重复。后端 fetch_jwc_entries 已按同样规则过滤，这里再兜一层，
// 保证旧进程/缓存数据带出来的也不会显示（标题与链接双重匹配）
const HIDDEN_ENTRY_TITLES = ['课表查询', '教学校历', '作息时间']
const HIDDEN_ENTRY_PATHS = ['/jwgl/kbcx.htm', '/jwgl/jxxl.htm', '/jwgl/zxsj.htm']

function isHiddenEntry(entry: { title: string; url: string }) {
  const title = entry.title || ''
  const url = (entry.url || '').replace(/\/+$/, '')
  return HIDDEN_ENTRY_TITLES.some(t => title.includes(t)) || HIDDEN_ENTRY_PATHS.some(p => url.endsWith(p))
}

// 入口标题清洗：去掉括号补充说明（“毕业论文(设计)管理系统” → “毕业论文管理系统”）
function cleanEntryTitle(title: string) {
  return (title || '').replace(/[（(][^（）()]*[）)]/g, '').trim()
}

// 入口卡片：统一 3 列网格（6 项正好两行），不再按分组分块展示
const visibleEntries = computed(() =>
  impression.value.entries
    .filter(e => !isHiddenEntry(e))
    .map(e => ({ ...e, title: cleanEntryTitle(e.title) })),
)

// 统一日期格式：MM-DD
// 兼容后端两种写法："2026-10-15"（教务各栏目）与 "2026.04.01"（学院新闻），
// 并且只按「年-月-日」解析：日期中段的 "2026-2027学年" 这类区间不会被误切出 "20-20"。
// 无日期（学院新闻 14 条里 10 条 date 为 null）返回空串，由调用方决定不渲染，
// 避免出现空白占位把条目撑开。
function formatDate(d: string | null) {
  const s = (d || '').trim()
  const m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/)
  if (m) return `${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`
  return ''
}

// 日期邮戳格式：日 + 月
function splitDay(d: string | null) {
  if (!d) return ''
  const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return m[3].replace(/^0/, '')
  return ''
}

function splitMonth(d: string | null) {
  if (!d) return ''
  const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return m[2] + '月'
  return ''
}

const impressionItems = [
  { title: '仪器设备', url: 'https://www.mycc.edu.cn/mcyx/yqsb.htm', icon: SetUp, color: '#e67e22', desc: '学校拥有智能制造、人工智能等现代化实验实训设备，为实践教学提供有力支撑。' },
  { title: '生活条件', url: 'https://www.mycc.edu.cn/mcyx/shtj.htm', icon: HomeFilled, color: '#27ae60', desc: '标准化学生公寓、多个学生食堂与运动场馆，营造舒适便捷的校园生活环境。' },
]

async function loadImpression() {
  try {
    const data = await getImpression()
    impressionData.value = data
    setCampusImpressionCache(data)
  } catch { /* 静默：失败保留已有（可能是缓存）内容，不回写空数组 */ }
}

/**
 * 刷新：强制重取一次，绕过前端 10 分钟缓存。
 * 后端对同一份聚合数据另有 5 分钟内存缓存（过期时后台异步刷新、本次仍返回旧数据），
 * 所以点一下未必立刻拿到全新的外网抓取结果 —— 但足以覆盖「前端缓存把旧数据
 * 锁死 10 分钟」这个更常见的场景，且失败时保持旧内容、不清空页面。
 * 入口：移动端页头的刷新按钮、桌面端点标题。两者都是「重新取一次」而非「重置页面」，
 * 所以不给 ElMessage 提示打扰阅读（状态都收在页头副标题/图标旋转上）。
 */
async function refreshImpression() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await loadImpression()
  } finally {
    refreshing.value = false
  }
}

// ---------------- 头部搜索 ----------------

const SEARCH_HOT_KEYWORDS = ['图书馆', '放假', '招聘', '奖学金', '讲座']

/** source 字段 → 中文名：搜索结果每条都标出来源，用户才知道点进去是什么 */
const SOURCE_LABELS: Record<string, string> = {
  jwc_entries: '系统入口',
  jwc_jxdt: '教学动态',
  jwc_tzgg: '通知公告',
  jwc_gjxx: '高教信息',
  jwc_jxjs: '教学建设',
  college_news: '学院动态',
  library: '图书馆',
}

interface NewsHit {
  title: string
  url: string
  date: string
  sourceLabel: string
}

const searchVisible = ref(false)
const searchKeyword = ref('')
const searchDone = ref(false)
/** 本页资讯命中（纯前端过滤，不发请求） */
const newsHits = ref<NewsHit[]>([])
/** 知识库命中（仅本页 0 命中时才发起） */
const knowledgeHits = ref<KnowledgeHit[]>([])
const knowledgeLoading = ref(false)

function openSearch() {
  searchVisible.value = true
  // 每次打开都是干净状态：上次的结果留着会让人以为「已经搜过了」
  searchKeyword.value = ''
  searchDone.value = false
  newsHits.value = []
  knowledgeHits.value = []
}

/**
 * 第一层：在本页已加载的资讯里按标题过滤。
 * 直接吃 impressionData（页面已渲染的那份数据），所以「搜得到 = 看得见」，
 * 不会出现搜索结果里有、页面上却找不到的割裂。
 */
function filterNews(keyword: string): NewsHit[] {
  const kw = keyword.toLowerCase()
  return impressionData.value
    .filter(i => (i.title || '').toLowerCase().includes(kw))
    .map(i => ({
      title: i.title,
      url: i.url,
      date: formatDate(i.date),
      sourceLabel: SOURCE_LABELS[i.source] || '资讯',
    }))
}

/**
 * 第二层：本页 0 命中才兜到知识库（RAG 混合检索，全端可用）。
 * 不做前端空转 —— 本页资讯只有几十条，命中率低是常态，
 * 用户真正想找的「办事问答」在知识库里。
 */
async function runSearch() {
  const keyword = searchKeyword.value.trim()
  if (!keyword) return
  newsHits.value = filterNews(keyword)
  searchDone.value = true
  knowledgeHits.value = []
  if (newsHits.value.length) {
    // 本页已命中，不再打后端：既省一次检索，也避免两段结果互相干扰
    return
  }
  // 游客没有知识库检索权限：只展示本页资讯的本地搜索结果
  if (isGuestMode()) return
  knowledgeLoading.value = true
  try {
    knowledgeHits.value = await searchKnowledge(keyword)
  } catch {
    // 检索失败按「无结果」处理，不弹错打断阅读；下面的空态文案已说明情况
    knowledgeHits.value = []
  } finally {
    knowledgeLoading.value = false
  }
}

function quickSearch(kw: string) {
  searchKeyword.value = kw
  runSearch()
}

/** 点搜索结果：可站内阅读的走阅读器（与页面其它入口一致），其余新窗口打开 */
function openSearchHit(h: NewsHit) {
  if (isInAppReadable(h.url)) {
    openArticle(h.url, h.title)
    searchVisible.value = false
  } else {
    window.open(h.url, '_blank', 'noopener,noreferrer')
  }
}

const galleryImages: GalleryImage[] = [
  { title: '安州校区博润楼', image_url: '/images/campus/安州校区博润楼.jpg', campus: '安州' },
  { title: '安州校区众立楼', image_url: '/images/campus/安州校区众立楼.jpg', campus: '安州' },
  { title: '安州校区博训楼', image_url: '/images/campus/安州校区博训楼.jpg', campus: '安州' },
  { title: '安州校区综合活动馆', image_url: '/images/campus/安州校区综合活动馆.jpg', campus: '安州' },
  { title: '安州校区体育馆', image_url: '/images/campus/安州校区体育馆.jpg', campus: '安州' },
  { title: '安州校区工程训练中心', image_url: '/images/campus/安州校区工程训练中心.jpg', campus: '安州' },
  { title: '安州校区田径运动场', image_url: '/images/campus/安州校区田径运动场.jpg', campus: '安州' },
  { title: '安州校区博文楼', image_url: '/images/campus/安州校区博文楼.jpg', campus: '安州' },
  { title: '安州校区博远楼', image_url: '/images/campus/安州校区博远楼.jpg', campus: '安州' },
  { title: '安州校区博雅楼', image_url: '/images/campus/安州校区博雅楼.jpg', campus: '安州' },
  { title: '游仙校区第一教学楼', image_url: '/images/campus/游仙校区第一教学楼.jpg', campus: '游仙' },
  { title: '游仙校区科技楼', image_url: '/images/campus/游仙校区科技楼.jpg', campus: '游仙' },
  { title: '游仙校区博采溪', image_url: '/images/campus/游仙校区博采溪.jpg', campus: '游仙' },
  { title: '游仙校区行政楼', image_url: '/images/campus/游仙校区行政楼.jpg', campus: '游仙' },
  { title: '游仙校区博识楼', image_url: '/images/campus/游仙校区博识楼.jpg', campus: '游仙' },
  { title: '游仙校区木桥', image_url: '/images/campus/游仙校区木桥.jpg', campus: '游仙' },
  { title: '游仙校区博识楼C区草坪', image_url: '/images/campus/游仙校区博识楼C区草坪.jpg', campus: '游仙' },
  { title: '游仙校区夜景', image_url: '/images/campus/游仙校区夜景.jpg', campus: '游仙' },
  { title: '游仙校区风雨操场', image_url: '/images/campus/游仙校区风雨操场.jpg', campus: '游仙' },
  { title: '游仙校区田径运动场', image_url: '/images/campus/游仙校区田径运动场.jpg', campus: '游仙' },
  { title: '游仙校区篮球场', image_url: '/images/campus/游仙校区篮球场.jpg', campus: '游仙' },
]

/** 校园风光轮播图源：桌面端专属（移动端首屏已改为 Tab + 信息流） */
const carouselImages = computed(() => galleryImages)

/* ==================== 移动端：分类 Tab + 信息流 ==================== */

/**
 * 分类定义。key 直接复用后端的 source 取值，这样切 Tab 只是换一个 filter，
 * 不产生任何网络请求；'all' 为合并流。
 * 与桌面端卡片一一对应：教学动态 / 通知公告 / 高教信息 / 教学建设 / 学院动态 / 图书馆。
 */
type FeedTabKey = 'all' | 'jwc_jxdt' | 'jwc_tzgg' | 'jwc_gjxx' | 'jwc_jxjs' | 'college_news' | 'library'

const FEED_TABS: { key: FeedTabKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'jwc_jxdt', label: '教学动态' },
  { key: 'jwc_tzgg', label: '通知公告' },
  { key: 'jwc_gjxx', label: '高教信息' },
  { key: 'jwc_jxjs', label: '教学建设' },
  { key: 'college_news', label: '学院动态' },
  { key: 'library', label: '图书馆' },
]

const activeTab = ref<FeedTabKey>('all')

/** 某个分类下的条目（已去重 + 按日期倒序） */
function itemsOfTab(key: FeedTabKey): ImpressionItem[] {
  const all = impressionData.value
  if (key === 'all') {
    // 合并流：入口项（系统入口）不是资讯，剔除；其余全部参与排序
    return deduplicateByTitle(all.filter(i => i.source !== 'jwc_entries')).sort(byDateDesc)
  }
  return deduplicateByTitle(all.filter(i => i.source === key)).sort(byDateDesc)
}

/** Tab 列表（只含 key/label）：条数不放在 Tab 上 —— 7 个分类 × 数字会把「图书馆」挤出首屏 */
const mobileTabs = computed(() => FEED_TABS)

function switchTab(key: FeedTabKey) {
  activeTab.value = key
  // 轮播随 activeTab 用 :key 重建，序号必须一起归零，否则指示点会停在上一次的位置
  heroIndex.value = 0
  // 切分类后回到列表顶部：否则停在上一分类的滚动位置，看起来像「没反应」
  const scroller = document.querySelector('.campus-page')
  if (scroller instanceof HTMLElement) scroller.scrollTo?.({ top: 0, behavior: 'smooth' })
}

/**
 * 相对时间：昨天 / 今天 / MM-DD / 更早。
 * 参考图的信息流用「昨天21:57」这种相对表述，比纯日期更符合「看新鲜事」的心理。
 * 无日期的条目（部分学院新闻 date 为 null）返回空串，由模板不渲染。
 */
function relativeTime(d: string | null): string {
  const s = (d || '').trim()
  const m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/)
  if (!m) return ''
  const target = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  target.setHours(0, 0, 0, 0)
  const diffDays = Math.round((today.getTime() - target.getTime()) / 86400000)
  if (diffDays <= 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays === 2) return '前天'
  if (diffDays < 7) return `${diffDays} 天前`
  return `${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`
}

interface FeedItem {
  title: string
  url: string
  image_url: string | null
  timeLabel: string
  sourceLabel: string
}

/**
 * 移动端信息流数据：当前分类 → 渲染项。
 * 标题去掉「绵阳城市学院」等公共前缀 —— 移动端一行只有十几个字，
 * 前缀会把真正的信息挤到第二行甚至截断。
 */
const mobileFeed = computed<FeedItem[]>(() =>
  itemsOfTab(activeTab.value).map(i => ({
    title: removeCommonPrefix(i.title),
    url: i.url,
    image_url: i.image_url,
    timeLabel: relativeTime(i.date),
    sourceLabel: SOURCE_LABELS[i.source] || '资讯',
  }))
)

/* ==================== 移动端：大图轮播 ==================== */

interface HeroSlide {
  title: string
  url: string
  image_url: string
  tagLabel: string
}

/** 「全部」Tab 的兜底图：全部资讯里一张带图的都没有时用（本地校园风光，不依赖外网） */
const HERO_FALLBACK_IMAGES = [
  '/images/campus/游仙校区博识楼.jpg',
  '/images/campus/安州校区博润楼.jpg',
  '/images/campus/游仙校区夜景.jpg',
  '/images/campus/安州校区综合活动馆.jpg',
]

/**
 * 轮播最多张数。5 张 ≈ 一份「首屏推荐」的量；再多用户也不会看完，
 * 反而把信息流挤到第一屏之外。
 */
const HERO_MAX = 5

/**
 * 「全部」Tab 顶部的大图轮播数据。**只在 activeTab === 'all' 时渲染**，
 * 其余分类是纯信息流（用户要的是「在分类里翻资讯」，顶部再来一条大图会白占一屏）。
 * 规则：
 *  ① 取全部资讯里**真带图**的条目（按日期倒序）—— 图与标题都来自资讯本身，
 *     点进去就是这篇资讯，这是最有价值的轮播形态；
 *  ② 一张带图的都没有（教学动态抓取失败 / 首次加载未完成）→ 用本地校园风光兜底，
 *     标题用资讯标题，保证首屏不留一块空白，也不影响点击进阅读器。
 * 纯前端计算：切 Tab 不产生任何请求。
 */
const heroSlides = computed<HeroSlide[]>(() => {
  // 非「全部」分类：不渲染轮播（模板 v-if 已拦截，这里返回空数组兜底）
  if (activeTab.value !== 'all') return []

  const items = itemsOfTab('all')

  // ① 真带图资讯
  const withImage = items.filter((i): i is ImpressionItem & { image_url: string } => !!i.image_url)
  if (withImage.length) {
    return withImage.slice(0, HERO_MAX).map(i => ({
      title: removeCommonPrefix(i.title),
      url: i.url,
      image_url: i.image_url,
      tagLabel: SOURCE_LABELS[i.source] || '资讯',
    }))
  }

  // ② 图文皆无：校园风光兜底（标题沿用资讯标题，仍是可点的资讯）
  return items.slice(0, HERO_MAX).map((i, idx) => ({
    title: removeCommonPrefix(i.title),
    url: i.url,
    image_url: HERO_FALLBACK_IMAGES[idx % HERO_FALLBACK_IMAGES.length],
    tagLabel: SOURCE_LABELS[i.source] || '资讯',
  }))
})

/** 轮播图点击：有 url 就进站内阅读器（兜底风光图也带资讯 url，同样可点） */
function openHeroSlide(s: HeroSlide) {
  if (s.url) openArticle(s.url, s.title)
}

/* ---------- 大图轮播：按住拖动切换（Pointer Events，鼠标 / 触屏同一套逻辑） ----------
   el-carousel 自带的触屏滑动只在真正的 touch 事件上生效：桌面端鼠标拖不动，
   且它一滑就把随后的点击「按惯性」吞掉。这里补一层完全自管的拖拽：
     · 按下即暂停自动轮播（避免边拖边自己翻页）；
     · 水平位移超过阈值（10px）才进入「拖动」态，轨道随手指跟手偏移（带阻尼）；
     · 松手按位移与速度决定「翻页」还是「回弹」—— 慢拖过半才翻，快甩超过阈值速度也翻；
     · 全程没超过阈值 = 一次点击，交给 <a> 的 click 进阅读器；
       超过阈值则吞掉随后的 click，避免「拖完手一松就点进了文章」。
   竖直方向交给页面滚动（touch-action: pan-y），不拦截。
   自动轮播用受控 prop `:autoplay` 启停：Element Plus 的 pause/start 不在组件实例上暴露，
   改 props 会触发内部 watch 正确暂停 / 重启定时器。 */
const heroCarouselRef = ref<InstanceType<typeof ElCarousel> | null>(null)
const heroAutoplay = ref(true)
const heroDragging = ref(false)
/** 补完动画结束后的那一帧：把轨道偏移静默归零（关过渡，否则会再弹回一次） */
const heroResettingTrack = ref(false)
/** 当前页序号：只用来点亮自己画的指示点（el-carousel 的 indicators 已关闭） */
const heroIndex = ref(0)

function onHeroIndexChange(index: number) {
  heroIndex.value = index
}
/** 拖动中实时的水平位移（px），模板里绑到轮播容器上做跟手偏移 */
const heroDragX = ref(0)
/** 阈值（px）：低于它算点击，不算拖动 */
const HERO_DRAG_THRESHOLD = 10
/** 速度阈值（px/ms）：快甩时不用拖过半也能翻页 */
const HERO_FLING_VELOCITY = 0.4

interface HeroDragState {
  pointerId: number
  startX: number
  startY: number
  lastX: number
  lastTime: number
  active: boolean   // 是否已越过阈值、进入拖动
  locked: boolean   // 已判定为纵向滚动，本次手势不再管
}
let heroDrag: HeroDragState | null = null
/** 上一次手势是拖动（而非轻点）：松手后紧随的 click 要吞掉，否则一拖完就点进了文章 */
let heroSuppressClick = false

/** 暂停 / 恢复自动轮播 */
function pauseHeroAutoplay() {
  heroAutoplay.value = false
}
function resumeHeroAutoplay() {
  // 延后一拍恢复：先让 el-carousel 完成翻页过渡，避免过渡途中被定时器打断
  window.setTimeout(() => { heroAutoplay.value = true }, 60)
}

function heroSwipe(direction: 'prev' | 'next') {
  const carousel = heroCarouselRef.value
  if (!carousel) return
  direction === 'next' ? carousel.next() : carousel.prev()
}

function onHeroPointerDown(e: PointerEvent) {
  // 只处理主键 / 单指；右键与双指（缩放）不接管
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (!e.isPrimary) return
  // 只认「从图片上按下」：底部指示点属于轮播容器但不属于图片，点它是切页，
  // 不应该被当成一次拖动的起点（否则松手时会再翻一次页）。
  const target = e.target as HTMLElement | null
  if (!target?.closest('.hero-slide')) return
  heroSuppressClick = false
  const now = Date.now()
  heroDrag = {
    pointerId: e.pointerId,
    startX: e.clientX,
    startY: e.clientY,
    lastX: e.clientX,
    lastTime: now,
    active: false,
    locked: false,
  }
  pauseHeroAutoplay()
}

function onHeroPointerMove(e: PointerEvent) {
  const d = heroDrag
  if (!d || d.pointerId !== e.pointerId || d.locked) return
  const dx = e.clientX - d.startX
  const dy = e.clientY - d.startY

  // 未越过阈值：先定方向。纵向为主 → 交还页面滚动，本次手势彻底放弃
  if (!d.active) {
    if (Math.abs(dy) > HERO_DRAG_THRESHOLD && Math.abs(dy) > Math.abs(dx)) {
      d.locked = true
      heroDragX.value = 0
      resumeHeroAutoplay() // 没有翻页意图，恢复自动轮播
      return
    }
    if (Math.abs(dx) <= HERO_DRAG_THRESHOLD) return
    d.active = true
    heroDragging.value = true
    // 捕获指针：手指滑出轮播区域（甚至滑出窗口）也不丢 up 事件
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  d.lastX = e.clientX
  d.lastTime = Date.now()
  // 跟手偏移：0.72 阻尼，松手时回弹 / 翻页的手感不会「甩得太远」
  heroDragX.value = dx * 0.72
}

function onHeroPointerUp(e: PointerEvent) {
  const d = heroDrag
  heroDrag = null
  if (!d || d.pointerId !== e.pointerId) return

  const wasActive = d.active && !d.locked
  const dx = e.clientX - d.startX
  const dt = Math.max(1, Date.now() - d.lastTime)
  const velocity = (e.clientX - d.lastX) / dt // px/ms，右正左负

  if (!wasActive) {
    // 只是轻点：没有位移，无需过渡，直接归零
    heroDragX.value = 0
    heroDragging.value = false
    resumeHeroAutoplay()
    return
  }

  // 拖动过：吞掉随后那次 click（否则松手就等于点了文章）
  heroSuppressClick = true

  const width = (e.currentTarget as HTMLElement)?.clientWidth || window.innerWidth || 320
  const passedHalf = Math.abs(dx) > width / 2
  // 快甩：速度方向必须与总位移方向一致，避免「先拖过去再甩回来」被误判
  const flingNext = velocity < -HERO_FLING_VELOCITY && dx < 0
  const flingPrev = velocity > HERO_FLING_VELOCITY && dx > 0
  const goNext = dx < 0 && (passedHalf || flingNext)
  const goPrev = dx > 0 && (passedHalf || flingPrev)

  if (goNext || goPrev) {
    // 翻页：只让 el-carousel 自己动。
    //
    // 关键点是「跟手偏移必须先瞬时归零、且不能产生动画」，否则会变成两段动画叠加：
    //   ① 我们的 transform 把图片从当前偏移（如 -0.4w）继续推到 ∓图宽
    //   ② el-carousel 同时把新页从另一侧推到 translateX(0)
    // 两者叠加 → 画面多走一段、时长也不一致，观感就是「滑到位后又慢放一遍」。
    //
    // 做法：先设 is-resetting（关掉我们的过渡）并把偏移归零，让容器**瞬间**回到
    // 标准起点；再调用 next/prev，由组建自己的 .4s 过渡完成翻页。
    // 归零与翻页在同一帧里提交，浏览器绘制的第一帧就已经是「偏移 0 + 翻页过渡进行中」，
    // 所以看不到归零那一下。
    heroResettingTrack.value = true
    heroDragX.value = 0
    if (goNext) heroSwipe('next')
    else heroSwipe('prev')
    // 等这两步渲染完（下一帧），再撤掉 reset 标记，恢复常态过渡供下次使用
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { heroResettingTrack.value = false })
    })
    heroDragging.value = false
    resumeHeroAutoplay()
    return
  }

  // 回弹：没有翻页，只让图片从当前偏移滑回 0（这一条是唯一由我们自己动画的路径）
  heroDragX.value = 0
  heroDragging.value = false
  scheduleHeroTrackReset()
  resumeHeroAutoplay()
}

/**
 * 回弹动画结束后复位偏移（回弹是唯一由我们自己动画的路径，时长用自己的 360ms）。
 * 其实回弹的目标值就是 0，过渡结束后的「复位」是幂等的；保留这个定时器只为
 * 在过渡结束后清掉 will-change，避免长期占用合成层。
 */
const HERO_TRACK_SETTLE_MS = 360
let heroTrackResetTimer: number | undefined

function scheduleHeroTrackReset() {
  window.clearTimeout(heroTrackResetTimer)
  heroTrackResetTimer = window.setTimeout(() => {
    heroDragX.value = 0
  }, HERO_TRACK_SETTLE_MS + 30)
}

function onHeroPointerCancel() {
  // 被系统打断（来电、手势返回、双指缩放）：从当前位置滑回，不翻页
  heroDrag = null
  heroDragX.value = 0
  heroDragging.value = false
  resumeHeroAutoplay()
}

/** 幻灯片点击：拖动过就只吞掉这次 click，正常轻点才进阅读器 */
function onHeroSlideClick(e: MouseEvent, s: HeroSlide) {
  e.preventDefault()
  if (heroSuppressClick) {
    heroSuppressClick = false
    return
  }
  openHeroSlide(s)
}

/** 拖动时禁止原生拖图（否则会拖出一个半透明图片幽灵盖住轮播） */
function onHeroSlideDragStart(e: DragEvent) {
  e.preventDefault()
}

onMounted(() => {
  // 本页组件在每次导航时都会被重建（StudentLayout 未用 keep-alive），
  // 因此不能用「组件是否已挂载」来判断要不要加载，只能看模块级缓存：
  // - 命中缓存（10 分钟内已加载过）→ 直接复用，不发请求，页面首帧即真实内容，不闪；
  // - 未命中 → 拉取一次并写回缓存，供下次进入复用。
  const cached = getCampusImpressionCache()
  if (cached) {
    impressionData.value = cached
    return
  }
  loadImpression()
})
</script>

<style scoped>
.campus-page {
  height: 100%;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 12px 24px 0;
  box-sizing: border-box;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.campus-page::-webkit-scrollbar { display: none; }
/* 直接子元素统一去掉左右内边距（轮播、阅读器、移动端页头除外：
   轮播自带边距、阅读器是 Teleported 抽屉无布局盒、页头要自己算 16px/8px 内边距） */
.campus-page > *:not(.campus-carousel):not(.article-reader-drawer):not(.campus-appbar) {
  padding-left: 0;
  padding-right: 0;
}
.campus-section:last-child {
  padding-bottom: 32px;
}

/* ===== Page Hero Header =====
   本页是一级 Tab（底部导航「校园资讯」），不用 SubPageHeader（带返回箭头、仅移动端）。
   白底通栏：横向铺满整个内容区（抵消 .campus-page 的左右内边距），
   去掉圆角、边框与阴影 —— 只靠「白 vs 浅蓝背景」分层，最干净。
   版式对齐参考稿：左侧一个大号粗体标题，右侧一枚纯黑线性图标，中间大量留白；
   图标不做胶囊底、不带文字，纯粹靠点击热区（32×32）保证可点性。 */
.campus-hero-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  /* 横向铺满：负外边距吃掉父级左右内边距（桌面 24px / 移动 16px，见下方 @media 覆盖）。
     上边 -12px 同样抵消页面 padding-top —— 不抵消的话白条上方会留一条背景色缝隙，通栏就不成立。
     不写 width —— 负外边距 + flex 子项的默认 stretch 已能撑满，
     显式 width 在移动端 column flex 下与 flex-shrink 叠加容易溢出。 */
  margin: -12px -24px 16px;
  background: #fff;
  padding: 18px 24px;
  box-sizing: border-box;
}
/* 标题区做成按钮：点标题即刷新。重置浏览器默认按钮样式，保持纯文字观感 */
.hero-head-text {
  min-width: 0;
  text-align: left;
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  cursor: pointer;
  border-radius: 8px;
}
.hero-head-text:disabled { cursor: default; }
/* 只在键盘聚焦时显示焦点环：鼠标点标题不该出现一圈蓝框 */
.hero-head-text:focus-visible { outline: 2px solid #409eff; outline-offset: 3px; }
.hero-head-text h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #111827;
  /* 参考稿的字距略紧，粗体大字收紧一点更整 */
  letter-spacing: -.2px;
  line-height: 1.2;
  transition: color .18s ease;
}
.hero-head-text:hover:not(:disabled) h2 { color: #409eff; }
/* 搜索：纯图标按钮，无底无边。命中区 32×32（视觉 22px 图标 + 内边距），
   保证触摸目标够大而不显笨重 */
.hero-head-search {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  padding: 0;
  background: none;
  border: 0;
  border-radius: 50%;
  color: #111827;
  font-size: 22px;
  cursor: pointer;
  transition: color .18s ease, background .18s ease;
}
.hero-head-search:hover { color: #409eff; background: #f3f7fd; }
.hero-head-search:focus-visible { outline: 2px solid #409eff; outline-offset: 2px; }

/* ===== 移动端品牌头牌 =====
   为什么是一条渐变蓝：移动端（≤767px）StudentLayout 会把顶部蓝条整个隐藏，这页是首个
   内容页，没有它整页会「没有头」；把品牌色补回来（渐变基色与桌面 topbar 同一族）。
   视觉配方：135° 品牌蓝渐变 + 右上柔光 + 斜向高光 + 内高光/外投影；**矩形通栏、无圆角**，
   上下边直接切齐内容区，像一条真正的 App 品牌栏而不是一张卡片。
   文字只有一枚 22px/800 标题（不放副标题、不放小字）；右侧只留一枚磨砂方角搜索按钮。
   移动端实际样式见文件底部 @media (max-width: 767px)：那里把本块改成白卡顶段且**不吸顶**；
   基础样式保留 sticky 仅用于 >767px 时的极端情况（实际该宽度走桌面版式，不渲染此头牌）。
   z-index 压过下方卡片（含 v-tilt 的 hover 抬升）。
   通栏：负外边距吃掉 .campus-page 移动端的 16px 左右内边距；上内边距为 0（见 @media 覆盖），
   否则页头上方会漏出滚动容器的 8px 内边距缝。 */
.campus-appbar {
  position: sticky;
  top: 0;
  z-index: 30;
  isolation: isolate;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  min-height: 60px;
  box-sizing: border-box;
  margin: 0 -16px 14px;
  padding: 10px 12px 10px 20px;
  overflow: hidden;
  background:
    radial-gradient(120% 150% at 92% -30%, rgba(255, 255, 255, .34) 0%, rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, #1d4ed8 0%, #2563eb 52%, #3b82f6 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .22),
    0 6px 16px rgba(29, 78, 216, .18);
  color: #fff;
}
/* 右上柔光：让纯色条有「光从右上打进来」的层次 */
.campus-appbar::before {
  content: "";
  position: absolute;
  z-index: -1;
  top: -78px;
  right: -54px;
  width: 190px;
  height: 190px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, .30) 0%, rgba(255, 255, 255, 0) 68%);
  pointer-events: none;
}
/* 左下斜向高光：一道克制的斜光，打破纯渐变的平 */
.campus-appbar::after {
  content: "";
  position: absolute;
  z-index: -1;
  left: -18%;
  bottom: -104px;
  width: 260px;
  height: 150px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, .13) 50%, rgba(255, 255, 255, 0) 100%);
  transform: rotate(-12deg);
  pointer-events: none;
}
/* 标题区：3px 白色竖条 + 22px/800 标题。
   竖条不是随手加的装饰 —— 本页区块标题（.section-title）和卡片标题都是「3px 蓝竖条 + 粗体」
   的语言，头牌把它翻成白色，页头与内容区才是同一套排版；图标按钮只用方角磨砂块，
   不抢标题的视觉权重。 */
.appbar-title {
  display: flex;
  align-items: center;
  gap: 11px;
  flex: 1;
  min-width: 0;
}
.appbar-title::before {
  content: "";
  flex-shrink: 0;
  width: 3px;
  height: 20px;
  border-radius: 2px;
  background: rgba(255, 255, 255, .75);
}
.appbar-title h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  /* 中文大标题给一点字距更「设计」；行高压紧，矩形栏里上下留白才均匀 */
  letter-spacing: .5px;
  line-height: 1.2;
  color: #fff;
  text-shadow: 0 1px 2px rgba(11, 34, 84, .22);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.appbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
/* 磨砂方角搜索按钮（36×36）：玻璃质感靠半透明白底 + 描边 + blur */
.appbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, .22);
  border-radius: 12px;
  background: rgba(255, 255, 255, .14);
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  transition: background .2s var(--tui-ease), border-color .2s var(--tui-ease),
    transform .12s var(--tui-ease);
}
.appbar-btn:hover { background: rgba(255, 255, 255, .24); border-color: rgba(255, 255, 255, .32); }
.appbar-btn:active { transform: scale(.93); background: rgba(255, 255, 255, .3); }
.appbar-btn:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

/* 游客专属：页头内的登录入口（移动端顶栏被隐藏，没有它游客会找不到回登录页的路径） */
.appbar-login {
  height: 30px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: #111111;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .5px;
  cursor: pointer;
  flex-shrink: 0;
}
.appbar-login:active { transform: scale(.95); }

/* ===== Search Dialog ===== */
.search-hot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 4px;
}
.search-hot-label { font-size: 12px; color: #9aa5b1; }
.search-hot-tag { cursor: pointer; }
.search-block { margin-top: 16px; }
.search-block-title {
  font-size: 13px;
  font-weight: 600;
  color: #5a6673;
  margin-bottom: 8px;
}
.search-hit {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 2px;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
  color: #42505f;
  text-decoration: none;
  cursor: pointer;
}
.search-hit:last-child { border-bottom: none; }
.search-hit:hover .search-hit-title { color: #409eff; }
.search-hit-static { cursor: default; }
.search-hit-static:hover .search-hit-title { color: #42505f; }
.search-hit-source {
  flex-shrink: 0;
  font-size: 11px;
  color: #7a8694;
  background: #f2f5f9;
  border-radius: 4px;
  padding: 2px 6px;
}
.search-hit-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color .18s ease;
}
.search-hit-date { flex-shrink: 0; font-size: 11px; color: #9aa5b1; }
.search-empty { margin: 6px 0 0; font-size: 12px; color: #b4bcc8; }
.search-empty a { color: #2f6ef2; text-decoration: none; }
.search-empty a:hover { text-decoration: underline; }

/* ===== Section ===== */
.campus-section { margin-bottom: 24px; }
/* 区块标题与卡片标题（.card-title）同一口径：15px/700 + 3px 蓝色竖条 + 8px 内距。
   原先这里用 4px 圆角小竖条 + 16px/600，与页内「通知公告 / 专业分院 / 图书馆公告」
   等卡片标题两种观感，故统一。 */
.section-title {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
  border-left: 3px solid #409eff; padding-left: 8px;
  display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
}
.section-tag {
  font-size: 11px; color: #999; background: #f5f7fa;
  padding: 2px 10px; border-radius: 10px; font-weight: 400;
}

/* ===== Entry Grid ===== */
.entry-card { display: block; }
.entry-chip { display: block; }
.entry-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.entry-item {
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 16px 12px;
  text-align: center;
  cursor: pointer;
  position: relative;
  transition: all .2s ease;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.entry-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(64,158,255,.15);
  border-color: var(--entry-color, #409eff);
}
/* 桌面端：--entry-color（由 getEntryColor 注入，中性深灰 #4E5969）直接落在图标上，克制、让位于内容区；
   移动端的图标配色改由「瓷片」承担，见文末移动端块 */
.entry-icon {
  font-size: 28px;
  color: var(--entry-color, #409eff);
  margin-bottom: 8px;
  transition: color .2s ease;
}
.entry-item p {
  font-size: 13px;
  color: #1d2129;
  margin: 0;
  font-weight: 500;
}
.entry-external {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  color: #86909c;
  background: #f2f3f5;
  padding: 2px 6px;
  border-radius: 4px;
}

/* ===== Duo Cards ===== */
.campus-duo { display: flex; gap: 18px; margin-bottom: 22px; }
.campus-card {
  flex: 1; min-width: 0; background: #fff; border-radius: 14px;
  padding: 16px 18px; box-shadow: 0 1px 6px rgba(0,0,0,.04);
  transition: transform .18s ease, box-shadow .18s ease;
}
.campus-card-jx { flex: 1.5; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.card-title {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
  border-left: 3px solid #409eff; padding-left: 8px;
  display: flex; align-items: center; gap: 6px;
}
.card-title .el-icon { color: #409eff; }
.card-more { font-size: 12px; color: #409eff; text-decoration: none; }
.head-right { display: flex; gap: 12px; align-items: center; }

/* ===== News Rows ===== */
.jxdt-first {
  /* <a> 默认是 inline：行内元素上 overflow/border-radius 不生效，图片方角会溢出圆角边框；
     display:block 后圆角裁剪、标题绝对定位才真正生效 */
  display: block;
  position: relative; border-radius: 8px; overflow: hidden;
  margin-bottom: 12px; cursor: pointer;
  background: linear-gradient(135deg, #dbeafe, #60a5fa); min-height: 96px;
}
/* 自适应高度：按原图比例显示，过高才裁切（原先固定 120px 把 4:3 竖版海报压成只剩中间 39%） */
.jxdt-first-img {
  width: 100%; height: auto; max-height: 230px;
  object-fit: cover; object-position: center top;
  display: block;
}
.jxdt-first-title {
  position: absolute; left: 0; right: 0; bottom: 0;
  padding: 32px 12px 12px;
  background: linear-gradient(transparent 20%, rgba(0,0,0,.45) 50%, rgba(0,0,0,.8) 100%);
  color: #fff; font-size: 14px; font-weight: 600;
  text-shadow: 0 1px 4px rgba(0,0,0,.5);
}
.news-row {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: #444; line-height: 2.05; cursor: pointer;
}
.news-row:hover .news-text { color: #409eff; }
.news-date-right { color: #999; font-size: 11px; flex-shrink: 0; margin-left: auto; }
.news-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 教学动态：日 + 月 邮戳样式 */
.jxdt-date-row { gap: 12px; }
.jxdt-day {
  flex-shrink: 0;
  width: 40px;
  text-align: center;
  border-left: 3px solid #409eff;
  padding-left: 8px;
}
.jxdt-day b {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.1;
}
.jxdt-month {
  display: block;
  font-size: 10px;
  color: #7a8694;
  margin-top: 2px;
}

/* 通知公告：月-日 */
.tzgg-row {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: #444; line-height: 2.05; cursor: pointer;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
}
.tzgg-row:last-child { border-bottom: none; }
.tzgg-row:hover .news-text { color: #409eff; }
.tzgg-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #7a8694;
  width: 45px;
  text-align: center;
}

/* ===== 高教信息（导航样式） ===== */
.campus-card-gjxx {
  background: #f8fafc;
}
.gjxx-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.gjxx-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background .2s ease;
}
.gjxx-item:hover {
  background: #ecf5ff;
}
.gjxx-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid #d7e0ec;
  color: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  transition: all .2s ease;
}
.gjxx-item:hover .gjxx-icon {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}
.gjxx-title {
  flex: 1;
  font-size: 13px;
  color: #42505f;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color .2s ease;
}
.gjxx-item:hover .gjxx-title {
  color: #409eff;
}
.gjxx-arrow {
  flex-shrink: 0;
  color: #7a8694;
  transition: transform .2s ease, color .2s ease;
}
.gjxx-item:hover .gjxx-arrow {
  transform: translateX(3px);
  color: #f56c6c;
}

/* ===== 教学建设 ===== */
.build-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 6px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background .2s ease;
}
.build-row:last-child {
  border-bottom: none;
}
.build-row:hover {
  background: #ecf5ff;
}
.build-mark {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border: 1.5px solid #409eff;
  transform: rotate(45deg);
  margin-top: 6px;
  transition: all .2s ease;
}
.build-row:hover .build-mark {
  background: #f56c6c;
  border-color: #f56c6c;
}
.build-text {
  flex: 1;
  font-size: 13px;
  color: #42505f;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color .2s ease;
}
.build-row:hover .build-text {
  color: #409eff;
}
.build-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #7a8694;
  margin-top: 2px;
}

/* ===== College ===== */
/* 桌面端 7 张卡片：固定 2 列 / 4 列。
   原先 auto-fill minmax(280px,1fr) 在 1200px 容器里每行放 4 个，7 = 4 + 3，
   最后一行拖着 3 张卡留白；改成 4 列 = 4 + 3、2 列 = 4 + 2 + 1，
   行尾恒有卡片占位，不再出现"最后一张卡孤零零占一行"的空档。 */
/* 「专业分院」是 .campus-page 的直接子元素，被上面那条
   `.campus-page > * { padding-left/right: 0 }` 抹掉了左右内边距 ——
   而它内部的 .card-head 并不自带内边距，结果是标题贴着卡片左边缘，
   与嵌在 .campus-duo-lib 里、保住了 .campus-card 的 16px 18px 的
   「图书馆公告」标题不齐。
    只补 .card-head 的左右内边距（而非整个 section）：.card-body 自己已有
    20px 左右内边距，若加在 section 上会叠加成 38px，桌面端学院网格会内缩。 */
.campus-card-college { margin-bottom: 22px; }
.campus-card-college > .card-head { padding-left: 18px; padding-right: 18px; }
.card-body { padding: 14px 20px 16px; }
.college-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.college-card {
  /* 纵向 flex：head / 新闻区 / "进入官网" 三段，
     .college-list 撑满中间，链接被 margin-top:auto 压到卡片底部，7 张卡据此等高对齐 */
  display: flex; flex-direction: column;
  background: #f8fafc; border-radius: 10px; padding: 16px;
  border: 1px solid #e4e7ed; cursor: pointer;
  transition: all .2s ease;
}
.college-card:hover {
  background: #ecf5ff;
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64,158,255,.15);
}
.college-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.college-icon { font-size: 28px; }
.college-name { font-size: 15px; font-weight: 700; color: #1a1a2e; }
/* 两条新闻槽位固定高度（2 × 21.6 ≈ 43px，含 one-line 省略号）：
   学院只有 0/1 条时由 ::after 补一条"暂无最新动态"，卡片不会被内容抽走高度 */
.college-list { flex: 1; min-height: 44px; display: flex; flex-direction: column; justify-content: flex-start; }
.college-news { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #666; line-height: 1.8; }
.news-dot { color: #409eff; flex-shrink: 0; }
/* min-width:0 是必须的：父级是 flex，且标题是 nowrap+ellipsis 的长文本，
   不给收缩下限时长标题（后端可能返回 40 字内的截断标题）会把卡片顶宽 */
.college-news .news-text { min-width: 0; }
/* 日期是 MM-DD 固定宽度，放右侧竖对齐，10 条无日期的条目直接不渲染该节点 */
.college-date { flex-shrink: 0; margin-left: auto; font-size: 11px; color: #9aa5b1; }
.college-empty { font-size: 12px; color: #b4bcc8; line-height: 1.8; }
.college-link { margin-top: auto; padding-top: 10px; font-size: 12px; color: #409eff; }
@media (min-width: 1024px) {
  .college-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

/* ===== Impression List ===== */
.impression-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.impression-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .2s ease;
}
.impression-row:hover {
  background: #ecf5ff;
}
.impression-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.impression-info {
  flex: 1;
  min-width: 0;
}
.impression-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.impression-desc {
  font-size: 12px;
  color: #7a8694;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.impression-arrow {
  flex-shrink: 0;
  color: #7a8694;
  transition: transform .2s ease, color .2s ease;
}
.impression-row:hover .impression-arrow {
  transform: translateX(3px);
  color: #409eff;
}

/* ===== Library ===== */
.campus-card-library { flex: 0.8; }
.lib-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.lib-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
  cursor: pointer;
  transition: background .2s ease;
}
.lib-item:last-child { border-bottom: none; }
.lib-item:hover { background: #ecf5ff; }
.lib-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #7a8694;
  width: 45px;
  text-align: center;
}
.lib-title {
  flex: 1;
  font-size: 13px;
  color: #42505f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color .2s ease;
}
.lib-item:hover .lib-title {
  color: #409eff;
}

/* ===== Carousel ===== */
.campus-carousel {
  margin-bottom: 24px;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
  flex-shrink: 0;
}
.campus-carousel :deep(.el-carousel__indicators) {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}
.campus-carousel :deep(.el-carousel__indicator) {
  padding: 4px;
}
.campus-carousel :deep(.el-carousel__button) {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,.6);
  opacity: 1;
}
.campus-carousel :deep(.el-carousel__indicator.is-active .el-carousel__button) {
  background: #fff;
  width: 10px;
  height: 10px;
}
.carousel-item {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
}
.carousel-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.carousel-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 48px 24px 20px;
  background: linear-gradient(transparent, rgba(0,0,0,.65));
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.carousel-title {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  text-shadow: 0 1px 4px rgba(0,0,0,.4);
}
.carousel-campus {
  font-size: 12px;
  padding: 4px 14px;
  border-radius: 12px;
  background: rgba(255,255,255,.25);
  backdrop-filter: blur(4px);
  color: #fff;
}

/* 3D 倾斜统一处理 */
.entry-item, .campus-card, .college-card { transform-style: preserve-3d; }

/* ===== 外链条目（<div> → <a> 语义化改造）=====
   去掉浏览器默认 <a> 外观（下划线/蓝色/访问后紫色），保持改造前的卡片视觉；
   同时保留原 cursor:pointer 与 hover 效果。
   注：原先还排除了 .college-tag（移动端胶囊自带样式），该标签已改为行式列表
   .college-m-row，此处随之清理；仅剩 .card-more 需要保留自身链接配色。 */
.campus-page a:not(.card-more) {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.campus-page a:not(.card-more):visited {
  color: inherit;
}

/* ===== Mobile =====
   2026-10 改版：一比一复刻资讯流 App（掘金「热点」页）的移动端版式。
   规格按参考稿实测标定（参考稿 670px 宽对应 375pt，换算比 ≈1.786）：
     页头标题 26px/700 · Tab 15px、选中 3px 下划线
     信息流标题 17px/600 两行 · 元信息 13px · 缩略图 129×97 圆角 8px */
@media (max-width: 767px) {
  /* 移动端页面改纵向 flex：桌面端卡片版式整块包在 <template v-if="!isMobile"> 里不渲染。
     参考稿是「浅灰页面底 + 一块浮起的大白卡」：白卡左右各留约 24px 边距、
     顶部留 8px、圆角 13px。所以这里把底色交回页面（移动端 StudentLayout 已是浅底），
     白卡不写在此处 —— 由 .campus-appbar 起负责，见下。 */
  .campus-page {
    padding: 8px 16px 0;
    display: flex;
    flex-direction: column;
    background: transparent;
  }
  .campus-page > section, .campus-page > nav { flex-shrink: 0; }

  /* ---------- 页头：浮起白卡的顶段 ----------
     圆角与白底由页头承担（整张卡的上半），滚出视口时页头不再吸顶，
     Tab 栏单独吸顶并补上圆角 —— 见 .campus-tabs。
     padding 归零：标题与图标直接贴齐白卡边缘（左右不再留 16px 内边距）。
     高度 84px → 56px：原值按参考稿的 375pt 宽度标定，实际渲染时
     标题 26px 加满留白显得过高，压到 56px 后与下方 Tab 的疏密更接近参考稿。 */
  .campus-appbar {
    position: relative;
    z-index: 30;
    min-height: 56px;
    margin: 0;
    padding: 0;
    background: #fff;
    box-shadow: none;
    border-radius: 13px 13px 0 0;
    overflow: hidden;
    color: #1d2129;
  }
  /* 去掉基础样式里的渐变与右上柔光/斜向高光 */
  .campus-appbar::before,
  .campus-appbar::after { display: none; }
  /* padding 归零后，标题与图标由基础样式的 align-items:center 在 min-height 高度里垂直居中 ——
     「贴边」指左右贴齐白卡边缘，上下仍有留白，不会顶到卡边。 */
  .appbar-title::before { display: none; }
  .appbar-title h1 {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -.2px;
    line-height: 1.2;
    color: #1d2129;
    text-shadow: none;
  }
  /* 图标按钮：参考稿是纯黑图标、无底色无边框，命中区 32×32 */
  .appbar-btn {
    width: 32px;
    height: 32px;
    border: 0;
    border-radius: 50%;
    background: none;
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    color: #1d2129;
    font-size: 22px;
  }
  .appbar-btn:hover { background: #f3f4f6; border-color: transparent; }
  .appbar-btn:active { transform: scale(.92); background: #eceef1; }

  /* ---------- 分类 Tab ----------
     是白卡的第二段（紧接页头，白底、左右内边距 20px 与页头标题对齐）；
     16px，选中黑色 700 + 3px 黑色下划线（与文字等宽）。
     单独吸顶：页头上滚出视口后，Tab 仍然吸在顶部，自己补上圆角，
     否则白卡边会「切」在顶边。 */
  .campus-tabs {
    position: sticky;
    top: 0;
    z-index: 29;
    display: flex;
    align-items: center;
    /* 参考稿分类之间留白很紧（「全部 / 热榜 / CS2」几乎贴着），22px 会撑得过宽，
       导致第 6 个分类被截断显示成「专」这种半截字。收到 16px。 */
    gap: 16px;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
    margin: 0;
    padding: 8px 16px 10px;
    background: #fff;
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    border-bottom: 0;
    border-radius: 0;
  }
  .campus-tabs::-webkit-scrollbar { display: none; }
  .campus-tab {
    position: relative;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    padding: 0 0 8px;
    background: none;
    border: 0;
    /* 参考稿 Tab 比标题小一号（标题 26、Tab 约 15），16px 会让一行放不下 7 个分类 */
    font-size: 15px;
    font-weight: 400;
    color: #86909c;
    cursor: pointer;
    transition: color .18s ease;
    -webkit-tap-highlight-color: transparent;
  }
  /* 选中：黑色 700。字号不变，避免行高跳动 */
  .campus-tab.is-active {
    color: #1d2129;
    font-weight: 700;
  }
  /* 下划线：与文字同宽的 3px 黑条（参考稿是整段文字宽，不是短横线），方角 */
  .campus-tab.is-active::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    width: auto;
    transform: none;
    height: 3px;
    border-radius: 0;
    background: #1d2129;
  }

  /* ---------- 大图轮播（只在「全部」Tab 顶部渲染）----------
     位次：Tab 之下、信息流之上，属于同一张白卡的中段 —— 白底不断开，
     左右内边距与页头/Tab/信息流一致（16px），因此它自己留出内边距而不是通栏。
     版式：16:9 左右的圆角大图 + 底部黑色渐变 + 白色标题两行截断；
     指示点用条形（与桌面轮播的圆点区分：这里是信息流 App 的观感）。
     不给左右箭头：手机上没有 hover，箭头会长期压在图上挡内容，按住拖动 + 自动轮播够用。 */
  .campus-hero-carousel {
    flex-shrink: 0;
    margin: 0;
    padding: 12px 16px 4px;
    background: #fff;
  }
  /* ---------- 按住拖动（只有图片层位移）----------
     touch-action / user-select / 光标只写在 .hero-track（图片区）上，**不要写到
     .campus-hero-carousel**：外边距、上下留白属于外层 section，写在外层会让整块区域
     （含留白）都变成「可拖 / 不可选」，手指点在图片外面的白边上也能拖走轮播。
     touch-action: pan-y 把「横向」手势留给 JS（拖动切页），纵向仍交给浏览器滚动页面 ——
     少了它，手指一按浏览器就先接管成页面滚动，拖不动轮播。
     位移**不在 .hero-track 上**：它一层包含「图片容器 + 指示点」，位移写上会整块一起动，
     卡片的圆角与指示点跟着平移，看起来就像卡片在滑。位移只写在 .el-carousel__container
     （纯图片层）上，卡片（圆角、背景、指示点）保持不动。 */
  .hero-track {
    /* 定位上下文：自绘指示点 .hero-dots 相对它定位（= 相对图片区域） */
    position: relative;
    width: 100%;
    /* overflow 交给内层 .el-carousel 裁切：这里加 hidden 会连带裁掉贴在底边的指示点 */
    touch-action: pan-y;
    -webkit-user-select: none;
    user-select: none;
  }
  .hero-track,
  .hero-track :deep(.el-carousel__container),
  .hero-track .hero-slide { cursor: grab; }
  .campus-hero-carousel.is-dragging .hero-track,
  .campus-hero-carousel.is-dragging .hero-track :deep(.el-carousel__container),
  .campus-hero-carousel.is-dragging .hero-track .hero-slide { cursor: grabbing; }
  /* ---------- 图片层：跟手 + 松手接续 ----------
     位移与过渡都放在 .el-carousel__container 上 —— 这就是「卡片里那张图」那一层。
     松手时一次性做三件事（同一帧内）：撤掉 .is-dragging（去掉 transition: none）、
     把偏移量设为目标值、恢复过渡 —— 浏览器会从「当前拖拽到的位置」直接补完剩下的距离，
     所以动画是从松手处接着播，而不是回到 0 再重来。
       翻页：图片层滑到 ∓图宽；同一帧里 el-carousel 翻页、把新页放到另一侧，
             视觉上就是「旧图被推走、新图推上来」，交接处零跳变。
       回弹：图片层滑回 0，反向弹回去。
     必须用 transform：它参与过渡中断的「从当前值接续」，left 不行（会先瞬跳回 0）。 */
  .hero-track :deep(.el-carousel__container) {
    transform: translate3d(var(--hero-drag-x, 0px), 0, 0);
    transition: transform 360ms cubic-bezier(.22, .61, .36, 1);
    will-change: transform;
  }
  .campus-hero-carousel.is-dragging .hero-track :deep(.el-carousel__container) {
    transition: none;
    will-change: auto;
  }
  /* 补完动画结束后的一帧：静默把偏移归零，不能有过渡（否则会再弹回一次） */
  .campus-hero-carousel.is-resetting .hero-track :deep(.el-carousel__container) {
    transition: none;
  }
  /* 拖动中关掉轮播自身的过渡，否则跟手偏移会和它的翻页过渡互相拉扯、出现拖影。
     松手后 is-dragging 立刻撤掉，这层过渡同时恢复 —— 与图片层的补完动画同帧起跑。 */
  .campus-hero-carousel.is-dragging :deep(.el-carousel__item) { transition: none; }
  /* ---------- 卡片（不动的那一层）：圆角 + 裁切 ----------
     overflow: hidden 必须写在**不位移**的元素上才裁得住位移层：
     .el-carousel 不参与位移，它裁掉 .el-carousel__container（图片层）滑出卡片的部分，
     所以拖动时看到的是「卡片边框不动、里面的图片在滑」。
     若把这层 overflow 写到会动的 .el-carousel__container 自己身上，它跟着自己一起平移，
     等于没有裁切，图片会直接露出卡片外。 */
  .campus-hero-carousel :deep(.el-carousel) {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
  }
  .campus-hero-carousel :deep(.el-carousel__container) {
    border-radius: 12px;
  }
  /* 指示点（自绘，叠在图片底边内侧）：不参与布局，因此不会影响轮播高度与图片定位 */
  .hero-dots {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 10px;
    z-index: 6;
    display: flex;
    justify-content: center;
    gap: 5px;
    pointer-events: none;
  }
  .hero-dot {
    width: 14px;
    height: 3px;
    border-radius: 2px;
    background: rgba(255, 255, 255, .45);
    transition: width .22s ease, background .22s ease;
  }
  .hero-dot.is-active {
    width: 22px;
    background: #fff;
  }
  /* 幻灯片整块可点：.hero-slide 是 <a>，块级化后铺满轮播容器 */
  .hero-slide {
    position: relative;
    display: block;
    width: 100%;
    height: 100%;
    overflow: hidden;
    -webkit-tap-highlight-color: transparent;
  }
  .hero-slide:active { opacity: .94; }
  /* 图：与 .feed-thumb 同一套「绝对定位 + 撑满 + cover」防变形方案 */
  .hero-slide-img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    background: #eef1f5;
  }
  /* 底部渐变：保证任意图片（浅底海报也算）上的白字都能读 */
  .hero-slide-shade {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0) 34%, rgba(0, 0, 0, .34) 62%, rgba(0, 0, 0, .72) 100%);
    pointer-events: none;
  }
  .hero-slide-caption {
    position: absolute;
    left: 14px;
    right: 14px;
    bottom: 26px; /* 让开底部指示点 */
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  /* 来源标签：半透明白底 + 白字，压在图上不抢标题 */
  .hero-slide-tag {
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(255, 255, 255, .22);
    -webkit-backdrop-filter: blur(6px);
    backdrop-filter: blur(6px);
    font-size: 11px;
    font-weight: 500;
    line-height: 1.5;
    color: #fff;
  }
  .hero-slide-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.4;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0, 0, 0, .35);
    /* 两行截断：大图轮播里超过两行的标题会把图压得只剩一条 */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* ---------- 白卡主体：Tab 之后的全部内容 ----------
     页头 / Tab / 信息流是**同一张白卡**的不同段：白底不中断、左右内边距一致。
     信息流一直连到屏幕底部（padding-bottom 撑出白卡下沿）并补下圆角。 */
  .campus-feed {
    background: #fff;
    padding-left: 16px;
    padding-right: 16px;
    margin: 0;
    padding-bottom: 24px;
    border-radius: 0 0 13px 13px;
  }

  /* ---------- 信息流 ----------
     参考稿行式结构：左侧标题两行 + 13px 灰色元信息，右侧 129×97 缩略图，
     每行之间一条 1px #F0F0F0 分割线（不是靠留白分隔）。
     行本身不再设左右内边距（由 .campus-feed 统一给 20px），
     分割线因此从内容左缘延伸到卡片右缘内 20px 处，与参考稿一致。 */
  .campus-feed { display: flex; flex-direction: column; }
  .feed-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 16px 0;
    border-bottom: 1px solid #f0f0f0;
    -webkit-tap-highlight-color: transparent;
    transition: opacity .14s ease;
  }
  .feed-item:last-child { border-bottom: 0; }
  .feed-item:active { opacity: .62; }
  .feed-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .feed-title {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
    line-height: 1.5;
    color: #1d2129;
    /* 两行截断：保证右侧缩略图高度与左侧文字块稳定对齐 */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .feed-meta {
    display: flex;
    align-items: center;
    gap: 0;
    font-size: 13px;
    color: #b2b2b2;
    line-height: 1.2;
  }
  /* 参考稿元信息是「昨天21:57·作者」连写，分隔点两侧不留缝 */
  .feed-dot { color: #cfcfcf; margin: 0 2px; }
  /* 缩略图：参考稿约 129×97。
     height 必须配 object-fit:cover 才不会被图片原始比例撑高 ——
     校园资讯抓到的图常见 4:3 或 16:9 竖版海报，不锁高度会把行撑到 160px+。 */
  .feed-thumb {
    flex-shrink: 0;
    width: 129px;
    height: 97px;
    border-radius: 8px;
    overflow: hidden;
    background: #f2f3f5;
    position: relative;
    /* img 是 block 且宽高 100%，但父级没有显式行高时 flex 可能按图片原始尺寸撑开，
       这里把容器自身高度锁死，超出的图片由 overflow:hidden 裁掉 */
    align-self: flex-start;
  }
  .feed-thumb img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    /* 抓到的校站图片往往带内联 width/height 或 svg 原始尺寸，绝对定位 + 撑满
       能保证无论图片原始比例如何，都严格填满 129×97 并被圆角裁切 */
    max-width: 100%;
    max-height: 100%;
  }

  /* ---------- 无图条目：标题占满整行 ----------
     参考稿里没图的条目（如「从 0.1 开始的 AI 使用手册」）标题是**铺满整宽**的，
     右侧不保留缩略图位置。所以无图行不渲染 .feed-thumb，标题自然吃满宽度，
     也不会有占位块和 97px 的假高度。 */
  .feed-empty {
    margin: 40px 0;
    text-align: center;
    font-size: 13px;
    color: #b4bcc8;
  }

  /* 页头与内容：移动端所有卡片版式（轮播 / 入口宫格 / 教学动态 / 专业分院 /
     绵城印象 / 图书馆）都包在桌面端 <template v-if="!isMobile"> 里，不再渲染，
     因此这里无需再为它们写移动端覆盖样式；
     若后续要恢复某个卡片到移动端，把它移出该 template 并在此补样式即可。 */
}
</style>

