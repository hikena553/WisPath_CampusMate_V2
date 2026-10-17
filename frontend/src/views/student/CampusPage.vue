<template>
  <div class="campus-page">
    <!-- 移动端顶部：教学动态图文轮播 —— 图片来源 =「教学动态」卡片内展示的前 5 条（仅取带图的条目，
         按列表顺序、从第一条的图开始），每张图叠加深色渐变标题，点按进对应动态。
         桌面端不渲染：桌面端顶部为校园风光轮播，该图文大图在「教学动态」卡片内展示（见下） -->
    <section v-if="isMobile && jxdtCarouselSlides.length" class="campus-jxdt-hero">
      <el-carousel :interval="4000" height="200px" arrow="always" trigger="click">
        <el-carousel-item v-for="s in jxdtCarouselSlides" :key="s.url">
          <a class="carousel-item" :href="s.url" @click.prevent="openArticle(s.url, s.title)">
            <img :src="s.image_url" class="carousel-img" />
            <div class="carousel-overlay">
              <span class="carousel-title">{{ s.title }}</span>
            </div>
          </a>
        </el-carousel-item>
      </el-carousel>
    </section>

    <!-- ① 校园风光轮播图（仅桌面端：移动端整块不展示，顶部由教学动态图文轮播打头，见文件头部） -->
    <section v-if="!isMobile" class="campus-carousel">
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

    <!-- ② 教务系统入口 -->
    <section class="campus-section">
      <div class="section-title"><span class="sec-dot"></span> 教务系统入口</div>
      <div class="entry-grid">
        <a v-for="e in visibleEntries" :key="e.url" class="entry-item" :href="e.url" target="_blank" rel="noopener noreferrer"
           :title="entryHint(e.url)" @click="onEntryClick(e, $event)">
          <el-icon class="entry-icon"><component :is="getEntryIcon(e.title)" /></el-icon>
          <p>{{ e.title }}</p>
          <span v-if="opensInNewWindow(e.url)" class="entry-external">↗</span>
        </a>
      </div>
    </section>

    <!-- ② 教学动态 + 通知公告 -->
    <section class="campus-duo">
      <div class="campus-card campus-card-jx" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><DataBoard /></el-icon> 教学动态</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jwgl/jxdt.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jwgl/jxdt.htm', '教学动态')">查看详情 →</a>
        </div>
        <!-- 首条图文大图：桌面端保留在卡内（移动端已挪至页面顶部 .campus-jxdt-hero，卡内只留文字列表） -->
        <a v-if="!isMobile && impression.jxdt.length" class="jxdt-first" :href="impression.jxdt[0].url" @click.prevent="openArticle(impression.jxdt[0].url, impression.jxdt[0].title)">
          <img v-if="impression.jxdt[0].image_url" :src="impression.jxdt[0].image_url" class="jxdt-first-img" />
          <span class="jxdt-first-title">{{ impression.jxdt[0].title }}</span>
        </a>
        <a v-for="a in impression.jxdt.slice(0, 5)" :key="a.url" class="news-row jxdt-date-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <!-- 移动端与通知公告/图书馆统一：灰色文本日期；桌面端保留「日+月」邮戳 -->
          <span v-if="isMobile" class="jxdt-date-text">{{ formatDate(a.date) }}</span>
          <span v-else class="jxdt-day"><b>{{ splitDay(a.date) }}</b><span class="jxdt-month">{{ splitMonth(a.date) }}</span></span>
          <span class="news-text">{{ a.title }}</span>
        </a>
      </div>
      <div class="campus-card" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Notification /></el-icon> 通知公告</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jwgl/tzgg.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jwgl/tzgg.htm', '通知公告')">查看详情 →</a>
        </div>
        <a v-for="a in (isMobile ? impression.tzgg.slice(0, 5) : impression.tzgg)" :key="a.url" class="tzgg-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
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
      <!-- 移动端：极简列表 —— 图标 + 名称 + 箭头，整行点击进学院官网（2026-10 改版）。
           新闻只在桌面端卡片内展示，移动端刻意保持干净；图标为内联 Heroicons，见 collegeMobileIcons。 -->
      <div class="college-body-m">
        <div class="college-m-list">
          <a
            v-for="c in collegeCards"
            :key="c.name"
            class="college-m-row"
            :style="{ '--row-color': c.color }"
            :href="c.url"
            @click.prevent="openArticle(c.url, c.name)"
          >
            <span class="college-m-badge">
              <svg
                class="college-m-icon"
                width="19"
                height="19"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path v-for="(d, i) in collegeMobileIcons[c.name]" :key="i" :d="d" />
              </svg>
            </span>
            <span class="college-m-name">{{ c.name }}</span>
            <svg
              class="college-m-arrow"
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M8.25 4.5L15.75 12L8.25 19.5" />
            </svg>
          </a>
        </div>
      </div>
    </section>

    <!-- ⑤ 绵城印象 + 图书馆（移动端该区排在专业分院之前，由 .campus-duo-lib 的 order 控制） -->
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
          <a v-for="a in (isMobile ? impression.library.slice(0, 5) : impression.library.slice(0, 4))" :key="a.title" class="lib-item" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
            <span class="lib-date">{{ formatDate(a.date) }}</span>
            <span class="lib-title">{{ a.title }}</span>
          </a>
        </div>
      </div>
    </section>

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
  SetUp, Histogram, HomeFilled, OfficeBuilding
} from '@element-plus/icons-vue'

const vTilt = tilt
const isMobile = ref(window.innerWidth <= 767)
window.addEventListener('resize', () => { isMobile.value = window.innerWidth <= 767 })

/** 站内阅读器：点击资讯在应用内打开（移动端全屏抽屉），不跳出应用 */
const readerRef = ref<InstanceType<typeof ArticleReader> | null>(null)
function openArticle(url: string, title?: string) {
  if (!url) return
  readerRef.value?.open(url, title)
}

interface GalleryImage {
  title: string
  image_url: string
  campus: string
}

/** 初始值直接取模块级缓存：二次进入命中时首帧就是真实内容，不会闪空态 */
const impressionData = ref<ImpressionItem[]>(getCampusImpressionCache() ?? [])

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
 * 移动端「专业分院」极简列表的细线图标（Heroicons Outline，24 viewBox、1.5 描边，MIT 许可）。
 * 直接内联 path，不新增 npm 依赖；键必须与 collegeCards.name / 后端 college_key 完全一致。
 * 选型记要：智能制造用齿轮（原「扳手+螺丝刀」在 19px 行内尺寸下线条粘连糊团）；
 * 其余 6 枚均经 19px 可读性复核。素材来源：github.com/tailwindlabs/heroicons。
 */
const collegeMobileIcons: Record<string, string[]> = {
  '马克思主义学院': [
    'M12 6.04168C10.4077 4.61656 8.30506 3.75 6 3.75C4.94809 3.75 3.93834 3.93046 3 4.26212V18.5121C3.93834 18.1805 4.94809 18 6 18C8.30506 18 10.4077 18.8666 12 20.2917M12 6.04168C13.5923 4.61656 15.6949 3.75 18 3.75C19.0519 3.75 20.0617 3.93046 21 4.26212V18.5121C20.0617 18.1805 19.0519 18 18 18C15.6949 18 13.5923 18.8666 12 20.2917M12 6.04168V20.2917',
  ],
  '人工智能学院': [
    'M8.25 3V4.5M4.5 8.25H3M21 8.25H19.5M4.5 12H3M21 12H19.5M4.5 15.75H3M21 15.75H19.5M8.25 19.5V21M12 3V4.5M12 19.5V21M15.75 3V4.5M15.75 19.5V21M6.75 19.5H17.25C18.4926 19.5 19.5 18.4926 19.5 17.25V6.75C19.5 5.50736 18.4926 4.5 17.25 4.5H6.75C5.50736 4.5 4.5 5.50736 4.5 6.75V17.25C4.5 18.4926 5.50736 19.5 6.75 19.5ZM7.5 7.5H16.5V16.5H7.5V7.5Z',
  ],
  '智能制造与工程学院': [
    'M9.59356 3.94014C9.68397 3.39768 10.1533 3.00009 10.7033 3.00009H13.2972C13.8472 3.00009 14.3165 3.39768 14.4069 3.94014L14.6204 5.22119C14.6828 5.59523 14.9327 5.9068 15.2645 6.09045C15.3387 6.13151 15.412 6.17393 15.4844 6.21766C15.8095 6.41393 16.2048 6.47495 16.5604 6.34175L17.7772 5.88587C18.2922 5.69293 18.8712 5.9006 19.1462 6.37687L20.4432 8.6233C20.7181 9.09957 20.6085 9.70482 20.1839 10.0544L19.1795 10.8812C18.887 11.122 18.742 11.4938 18.7491 11.8726C18.7498 11.915 18.7502 11.9575 18.7502 12.0001C18.7502 12.0427 18.7498 12.0852 18.7491 12.1275C18.742 12.5064 18.887 12.8782 19.1795 13.119L20.1839 13.9458C20.6085 14.2953 20.7181 14.9006 20.4432 15.3769L19.1462 17.6233C18.8712 18.0996 18.2922 18.3072 17.7772 18.1143L16.5604 17.6584C16.2048 17.5252 15.8095 17.5862 15.4844 17.7825C15.412 17.8263 15.3387 17.8687 15.2645 17.9097C14.9327 18.0934 14.6828 18.4049 14.6204 18.779L14.4069 20.06C14.3165 20.6025 13.8472 21.0001 13.2972 21.0001H10.7033C10.1533 21.0001 9.68397 20.6025 9.59356 20.06L9.38005 18.779C9.31771 18.4049 9.06774 18.0934 8.73597 17.9097C8.66179 17.8687 8.58847 17.8263 8.51604 17.7825C8.19101 17.5863 7.79568 17.5252 7.44011 17.6584L6.22325 18.1143C5.70826 18.3072 5.12926 18.0996 4.85429 17.6233L3.55731 15.3769C3.28234 14.9006 3.39199 14.2954 3.81657 13.9458L4.82092 13.119C5.11343 12.8782 5.25843 12.5064 5.25141 12.1276C5.25063 12.0852 5.25023 12.0427 5.25023 12.0001C5.25023 11.9575 5.25063 11.915 5.25141 11.8726C5.25843 11.4938 5.11343 11.122 4.82092 10.8812L3.81657 10.0544C3.39199 9.70484 3.28234 9.09958 3.55731 8.62332L4.85429 6.37688C5.12926 5.90061 5.70825 5.69295 6.22325 5.88588L7.4401 6.34176C7.79566 6.47496 8.19099 6.41394 8.51603 6.21767C8.58846 6.17393 8.66179 6.13151 8.73597 6.09045C9.06774 5.9068 9.31771 5.59523 9.38005 5.22119L9.59356 3.94014Z',
    'M15 12C15 13.6569 13.6569 15 12 15C10.3431 15 9 13.6569 9 12C9 10.3432 10.3431 9.00001 12 9.00001C13.6569 9.00001 15 10.3432 15 12Z',
  ],
  '健康与教育学院': [
    'M21 8.25C21 5.76472 18.9013 3.75 16.3125 3.75C14.3769 3.75 12.7153 4.87628 12 6.48342C11.2847 4.87628 9.62312 3.75 7.6875 3.75C5.09867 3.75 3 5.76472 3 8.25C3 15.4706 12 20.25 12 20.25C12 20.25 21 15.4706 21 8.25Z',
  ],
  '商学院': [
    'M3 13.125C3 12.5037 3.50368 12 4.125 12H6.375C6.99632 12 7.5 12.5037 7.5 13.125V19.875C7.5 20.4963 6.99632 21 6.375 21H4.125C3.50368 21 3 20.4963 3 19.875V13.125Z',
    'M9.75 8.625C9.75 8.00368 10.2537 7.5 10.875 7.5H13.125C13.7463 7.5 14.25 8.00368 14.25 8.625V19.875C14.25 20.4963 13.7463 21 13.125 21H10.875C10.2537 21 9.75 20.4963 9.75 19.875V8.625Z',
    'M16.5 4.125C16.5 3.50368 17.0037 3 17.625 3H19.875C20.4963 3 21 3.50368 21 4.125V19.875C21 20.4963 20.4963 21 19.875 21H17.625C17.0037 21 16.5 20.4963 16.5 19.875V4.125Z',
  ],
  '创意设计学院': [
    'M9.53086 16.1224C9.08517 15.0243 8.00801 14.25 6.75 14.25C5.09315 14.25 3.75 15.5931 3.75 17.25C3.75 18.4926 2.74262 19.5 1.49998 19.5C1.44928 19.5 1.39898 19.4983 1.34912 19.495C2.12648 20.8428 3.58229 21.75 5.24998 21.75C7.72821 21.75 9.73854 19.7467 9.74993 17.2711C9.74998 17.2641 9.75 17.2571 9.75 17.25C9.75 16.8512 9.67217 16.4705 9.53086 16.1224ZM9.53086 16.1224C10.7252 15.7153 11.8612 15.1705 12.9175 14.5028M7.875 14.4769C8.2823 13.2797 8.8281 12.1411 9.49724 11.0825M12.9175 14.5028C14.798 13.3141 16.4259 11.7362 17.6806 9.85406L21.5566 4.04006C21.6827 3.85093 21.75 3.6287 21.75 3.40139C21.75 2.76549 21.2345 2.25 20.5986 2.25C20.3713 2.25 20.1491 2.31729 19.9599 2.44338L14.1459 6.31937C12.2638 7.57413 10.6859 9.20204 9.49724 11.0825M12.9175 14.5028C12.2396 12.9833 11.0167 11.7604 9.49724 11.0825',
  ],
  '终身教育学院': [
    'M4.25933 10.1466C3.98688 12.2307 3.82139 14.3483 3.76853 16.494C6.66451 17.703 9.41893 19.1835 12 20.9036C14.5811 19.1835 17.3355 17.703 20.2315 16.494C20.1786 14.3484 20.0131 12.2307 19.7407 10.1467M4.25933 10.1466C3.38362 9.8523 2.49729 9.58107 1.60107 9.3337C4.84646 7.05887 8.32741 5.0972 12 3.49255C15.6727 5.0972 19.1536 7.05888 22.399 9.33371C21.5028 9.58109 20.6164 9.85233 19.7407 10.1467M4.25933 10.1466C6.94656 11.0499 9.5338 12.1709 12.0001 13.4886C14.4663 12.1709 17.0535 11.0499 19.7407 10.1467M6.75 15C7.16421 15 7.5 14.6642 7.5 14.25C7.5 13.8358 7.16421 13.5 6.75 13.5C6.33579 13.5 6 13.8358 6 14.25C6 14.6642 6.33579 15 6.75 15ZM6.75 15V11.3245C8.44147 10.2735 10.1936 9.31094 12 8.44329M4.99264 19.9926C6.16421 18.8211 6.75 17.2855 6.75 15.75V14.25',
  ],
}

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

/** 校园风光轮播图源：仅桌面端渲染（移动端顶部改为教学动态图文轮播，见 jxdtCarouselSlides），直接给全量图集 */
const carouselImages = computed(() => galleryImages)

/** 移动端顶部轮播的图源：取「教学动态」卡片内展示的前 5 条（与列表 slice 一致）中带图的条目，按列表顺序。
 *  filter 用类型谓词收窄：image_url 类型为 string | null，收窄为 string 后模板 :src 才能直接绑定 */
const jxdtCarouselSlides = computed(() =>
  impression.value.jxdt
    .slice(0, 5)
    .filter((i): i is ImpressionItem & { image_url: string } => !!i.image_url)
)

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
/* 直接子元素统一去掉左右内边距（轮播与阅读器除外：
   轮播自带边距、阅读器是 Teleported 抽屉无布局盒） */
.campus-page > *:not(.campus-carousel):not(.article-reader-drawer) {
  padding-left: 0;
  padding-right: 0;
}
.campus-section:last-child {
  padding-bottom: 32px;
}

/* ===== Section ===== */
.campus-section { margin-bottom: 24px; }
.section-title {
  font-size: 16px; font-weight: 600; color: #1a1a2e;
  display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
}
.section-between { justify-content: space-between; }
.sec-dot { width: 4px; height: 16px; background: #409eff; border-radius: 2px; flex-shrink: 0; }
.section-tag {
  font-size: 11px; color: #999; background: #f5f7fa;
  padding: 2px 10px; border-radius: 10px; font-weight: 400;
}

/* ===== Entry Grid ===== */
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
  border-color: #409eff;
}
.entry-icon {
  font-size: 28px;
  color: #409eff;
  margin-bottom: 8px;
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
.campus-card-college { margin-bottom: 22px; }
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
/* 移动端整块栅格隐藏（改用下方 .college-m* 的行式列表） */
.college-body-m { display: none; }
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

/* ===== Mobile ===== */
@media (max-width: 767px) {
  /* 移动端页面改纵向 flex：支持按 order 调换区块顺序。
     图书馆公告区（⑤：绵城印象在移动端隐藏）排到专业分院之前 ——
     这两块本就是页面最后的两个 section，order 1/2 与其他区块（默认 0）不冲突 */
  .campus-page { padding: 8px 16px 0; display: flex; flex-direction: column; }
  .campus-page > section { flex-shrink: 0; }
  .campus-duo-lib { order: 1; }
  .campus-card-college { order: 2; flex: none; }
  /* 移动端顶部：教学动态图文轮播（占原轮播的第一屏位置，点按进对应动态）——
     容器观感对齐轮播形态（圆角 + 轻阴影），标题压两行防止长标题糊满整图 */
  .campus-jxdt-hero {
    margin-bottom: 24px;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
  }
  /* 幻灯片整块可点：.carousel-item 原用于 <div>，改 <a> 后需块级化才能撑满轮播容器 */
  .campus-jxdt-hero .carousel-item { display: block; }
  .campus-jxdt-hero .carousel-title {
    font-size: 14px;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  /* 标题让位给底部指示点：基础样式 20px 下距与居中圆点在竖直方向重叠，抬高到 36px */
  .campus-jxdt-hero .carousel-overlay { padding-bottom: 36px; }
  /* 指示点：8px 小圆点，样式对齐桌面轮播（白点半透明） */
  .campus-jxdt-hero :deep(.el-carousel__indicators) {
    position: absolute;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
  }
  .campus-jxdt-hero :deep(.el-carousel__indicator) { padding: 4px; }
  .campus-jxdt-hero :deep(.el-carousel__button) {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255,255,255,.6);
    opacity: 1;
  }
  .campus-jxdt-hero :deep(.el-carousel__indicator.is-active .el-carousel__button) {
    background: #fff;
  }
  .campus-duo { flex-direction: column; }
  .campus-duo-gjxx { display: none; }
  .campus-card-impression { display: none; }
  /* 移动端：教学动态行与通知公告/图书馆统一 —— 灰色文本日期 + 发丝虚线分隔、间距对齐 */
  .jxdt-date-row { gap: 10px; padding: 6px 0; border-bottom: 1px dashed #ebeef5; }
  .jxdt-date-row:last-child { border-bottom: none; }
  .jxdt-date-text { flex-shrink: 0; font-size: 12px; color: #7a8694; width: 45px; text-align: center; }
  .entry-grid { grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .entry-item { padding: 12px 8px; }
  .entry-icon { font-size: 24px; }
  .entry-item p { font-size: 12px; }
  .college-body-pc { display: none; }
  .college-body-m { display: block; }
  /* 移动端：极简列表（2026-10 改版）—— 一整张白卡 + 行间发丝线，
     每行 = 细线图标（Heroicons，内联 SVG）+ 名称 + 箭头，整行点击进该院官网。
     新闻只在桌面端展示：移动端不再渲染新闻行，头部「新闻实时更新」标签随之隐藏。 */
  .campus-card-college .section-tag { display: none; }
  .college-m-list {
    margin-top: 10px;
    background: #fff;
    border: 1px solid #eef2f7;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(16, 32, 64, .04);
  }
  .college-m-row {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 10px 13px;
    transition: background .2s ease;
  }
  .college-m-row + .college-m-row { border-top: 1px solid #f1f4f8; }
  .college-m-row:active { background: #f7f9fc; }
  /* 中性浅底徽章：颜色只留在图标上，整块列表更克制 */
  .college-m-badge {
    width: 32px;
    height: 32px;
    border-radius: 9px;
    background: #f2f5f9;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .college-m-icon { display: block; color: var(--row-color, #409eff); }
  .college-m-name {
    flex: 1;
    min-width: 0;
    font-size: 14px;
    font-weight: 600;
    color: #1a1a2e;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .college-m-arrow { display: block; flex-shrink: 0; color: #c9d2dc; }
}
</style>
