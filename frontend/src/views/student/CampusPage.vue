<template>
  <div class="campus-page">
    <!-- ① 校园风光轮播图 -->
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
        <a v-if="impression.jxdt.length" class="jxdt-first" :href="impression.jxdt[0].url" @click.prevent="openArticle(impression.jxdt[0].url, impression.jxdt[0].title)">
          <img v-if="impression.jxdt[0].image_url" :src="impression.jxdt[0].image_url" class="jxdt-first-img" />
          <span class="jxdt-first-title">{{ impression.jxdt[0].title }}</span>
        </a>
        <a v-for="a in impression.jxdt.slice(1, 7)" :key="a.url" class="news-row jxdt-date-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="jxdt-day"><b>{{ splitDay(a.date) }}</b><span class="jxdt-month">{{ splitMonth(a.date) }}</span></span>
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
            <div v-for="n in impression.collegeNews[c.name] || []" :key="n.url" class="college-news">
              <span class="news-dot">▪</span><span class="news-text">{{ n.title }}</span>
            </div>
            <span class="college-link">进入官网 →</span>
          </a>
        </div>
      </div>
      <!-- 移动端：标签化 -->
      <div class="college-body-m">
        <div class="college-tags">
          <a
            v-for="c in collegeCards"
            :key="c.name"
            class="college-tag"
            :style="{ '--tag-color': c.color }"
            :href="c.url"
            @click.prevent="openArticle(c.url, c.name)"
          >
            <el-icon class="college-tag-icon"><component :is="c.icon" /></el-icon>
            <span>{{ c.name }}</span>
          </a>
        </div>
      </div>
    </section>

    <!-- ⑤ 绵城印象 + 图书馆 -->
    <section class="campus-duo">
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
          <a v-for="a in impression.library.slice(0, 4)" :key="a.title" class="lib-item" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
            <span class="lib-date">{{ formatDate(a.date) }}</span>
            <span class="lib-title">{{ a.title }}</span>
          </a>
        </div>
      </div>
    </section>
  </div>

  <!-- 站内阅读器：点击资讯在应用内打开，不跳出 -->
  <ArticleReader ref="readerRef" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getImpression } from '@/api/campus'
import type { ImpressionItem } from '@/types'
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

const impressionData = ref<ImpressionItem[]>([])

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

const collegeCards = [
  { name: '马克思主义学院', url: 'https://mksxy.mycc.edu.cn/', icon: Reading, color: '#e74c3c' },
  { name: '人工智能学院', url: 'https://xdjsxy.mycc.edu.cn/', icon: Monitor, color: '#409eff' },
  { name: '智能制造与工程学院', url: 'https://xdcsjsxy.mycc.edu.cn/', icon: SetUp, color: '#e67e22' },
  { name: '健康与教育学院', url: 'https://xdfw.mycc.edu.cn/', icon: OfficeBuilding, color: '#27ae60' },
  { name: '商学院', url: 'https://jgxy.mycc.edu.cn/', icon: Histogram, color: '#9b59b6' },
  { name: '创意设计学院', url: 'https://cysjxy.mycc.edu.cn/', icon: Collection, color: '#f39c12' },
  { name: '终身教育学院', url: 'https://jxjy.mycc.edu.cn/', icon: School, color: '#1abc9c' },
]

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
function formatDate(d: string | null) {
  if (!d) return ''
  const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return `${m[2]}-${m[3]}`
  return d.slice(5, 10)
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
    impressionData.value = await getImpression()
  } catch { /* 静默 */ }
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

const carouselImages = computed(() => {
  if (!isMobile.value) return galleryImages
  const anzhou = galleryImages.filter(i => i.campus === '安州')
  const youxian = galleryImages.filter(i => i.campus === '游仙')
  return [anzhou[0], anzhou[3], anzhou[5], youxian[0], youxian[2], youxian[7]]
})

onMounted(async () => {
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
.campus-page > *:not(.campus-carousel) {
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
.campus-card-college { margin-bottom: 22px; }
.card-body { padding: 14px 20px 16px; }
.college-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.college-card {
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
.college-news { display: flex; gap: 6px; font-size: 12px; color: #666; line-height: 1.85; }
.news-dot { color: #409eff; flex-shrink: 0; }
.college-link { margin-top: 10px; display: inline-block; font-size: 12px; color: #409eff; }
.college-body-m { display: none; }

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
   同时保留原 cursor:pointer 与 hover 效果 */
.campus-page a:not(.card-more):not(.college-tag) {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.campus-page a:not(.card-more):not(.college-tag):visited {
  color: inherit;
}

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .campus-page { padding: 8px 16px 0; }
  .campus-carousel { border-radius: 10px; }
  .campus-carousel :deep(.el-carousel__container) { height: 200px !important; }
  .campus-carousel :deep(.el-carousel__indicators) {
    display: flex !important;
    flex-wrap: nowrap !important;
    max-width: calc(100% - 32px);
    overflow: hidden;
    justify-content: center;
  }
  .campus-carousel :deep(.el-carousel__indicator) { padding: 2px; }
  .campus-carousel :deep(.el-carousel__button) { width: 5px; height: 5px; }
  .campus-duo { flex-direction: column; }
  .campus-duo-gjxx { display: none; }
  .campus-card-impression { display: none; }
  .entry-grid { grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .entry-item { padding: 12px 8px; }
  .entry-icon { font-size: 24px; }
  .entry-item p { font-size: 12px; }
  .college-body-pc { display: none; }
  .college-body-m { display: block; }
  .college-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px 0 4px 24px;
  }
  .college-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 8px 16px;
    border-radius: 20px;
    background: #fff;
    border: 1.5px solid #e4e7ed;
    color: #333;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    -webkit-tap-highlight-color: transparent;
  }
  .college-tag:active {
    background: var(--tag-color, #409eff);
    border-color: var(--tag-color, #409eff);
    color: #fff;
    transform: scale(0.96);
  }
  .college-tag:active .college-tag-icon {
    color: #fff;
  }
  .college-tag-icon {
    font-size: 16px;
    color: var(--tag-color, #409eff);
  }
}
</style>
