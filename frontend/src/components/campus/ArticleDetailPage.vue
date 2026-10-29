<template>
  <Teleport to="body">
    <!-- 覆盖式全屏子页：动画复用全局 .subpage（styles/animations.css，全站唯一实现）。
         结构照抄 ArticleReader：Teleport + Transition(name="subpage") + 根元素 fixed inset:0。
         取舍：不用 el-dialog / el-drawer —— 它们自带居中、遮罩、body 滚动锁与 z-index 体系，
         而这页要的是「手机上整页盖上来、桌面端 760px 居中」的确定性版式，自己写样式可控得多。 -->
    <Transition name="subpage" :duration="320" @after-leave="emit('closed')">
      <div
        v-if="visible"
        class="adp-root"
        role="dialog"
        aria-modal="true"
        :aria-label="'资讯详情：' + (data?.title || props.title || '')"
        :style="rootStyle"
      >
        <!-- ① 顶栏：返回 / 「资讯详情」/ 分享
             顶栏只有一行固定文案，不带副标题。
             为什么不用完整文章标题当主标题：35 字以上的校园通知名在 390px 下必然被截成
             「…学业…」这种半截串，既读不完还要占两行；完整标题在下方正文区展示一次就够，
             顶栏只承担「我在哪、从哪回去」，重复一次反而更乱。
             来源栏目（通知公告/教学动态…）改到正文区标题下方的标签里展示，不占顶栏高度。 -->
        <header class="adp-head" :class="{ 'is-scrolled': scrolled }">
          <button type="button" class="adp-icon-btn" aria-label="返回" @click="close">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <div class="adp-head-title">
            <div class="adp-head-main">资讯详情</div>
          </div>
          <!-- 右上角：分享。原先这里是「在浏览器打开」——
               对一个校园通知详情页来说，「把这条发给同学」远比「跳出去用浏览器开」高频，
               而且外跳与详情页「不跳出应用」的定位相悖。 -->
          <button type="button" class="adp-icon-btn" aria-label="分享" @click="onShare">
            <el-icon :size="18"><Share /></el-icon>
          </button>
        </header>

        <!-- ② 滚动区：文章主体 + 互动区 + 评论区同处一个容器。
             为什么合并成一个滚动条：详情页的阅读动线就是「读正文 → 点赞评论 → 看评论」，
             拆成上固定下滚动或内部锚点滚动，会让键盘弹出与 iOS 回弹各管一段，反而更乱。
             底部输入栏用 sticky 贴在滚动区末尾（见 .adp-composer），无需额外占位。 -->
        <div ref="scrollRef" class="adp-scroll" @scroll.passive="onScroll">
          <!-- 加载骨架 -->
          <div v-if="loading" class="adp-skeleton">
            <div class="sk-line w70" />
            <div class="sk-line w50" />
            <div class="sk-gap" />
            <div class="sk-line w100" />
            <div class="sk-line w95" />
            <div class="sk-line w90" />
            <div class="sk-line w100" />
            <div class="sk-line w60" />
          </div>

          <!-- 错误态 -->
          <div v-else-if="error" class="adp-state">
            <el-icon :size="44" class="adp-state-icon"><DocumentDelete /></el-icon>
            <p class="adp-state-title">页面暂不可用</p>
            <p class="adp-state-desc">{{ error }}</p>
            <div class="adp-state-btns">
              <button type="button" class="adp-btn primary" @click="reload">
                <el-icon :size="15"><Refresh /></el-icon> 重试
              </button>
              <button type="button" class="adp-btn" @click="openExternal(currentUrl)">浏览器打开</button>
            </div>
          </div>

          <template v-else-if="data">
            <!-- 标题 + 元信息 + 正文，一屏读到底。
                 正文直接在本页渲染：详情页就是用户点进资讯后想读到的东西，
                 再放一个「阅读全文」让他多点一次是多余的一跳。
                 抓取失败时正文区就地降级，互动与评论照常可用。 -->
            <article class="adp-article">
              <h1 class="adp-title">{{ data.title || headerTitle }}</h1>
              <div class="adp-meta">
                <span v-if="sourceLabel" class="adp-source-tag">{{ sourceLabel }}</span>
                <span v-if="data.date" class="adp-meta-text">{{ data.date }}</span>
                <span v-if="viewCount" class="adp-meta-text">{{ viewCount }} 浏览</span>
              </div>

              <!-- 正文：后端已做脚本 / 事件属性净化。
                   ref 用于渲染后加工 DOM（表格包横滑壳、署名行打标），见 enhanceContent()。 -->
              <div
                v-if="data.kind === 'article'"
                ref="contentRef"
                class="adp-content"
                v-html="data.content_html || ''"
              />

              <!-- 抓取失败：正文区降级为一行提示，互动与评论仍可用 -->
              <div v-else-if="data.kind === 'error'" class="adp-inline-state">
                <el-icon :size="30" class="adp-state-icon"><DocumentDelete /></el-icon>
                <p class="adp-inline-title">正文暂不可用</p>
                <p class="adp-inline-desc">校站页面暂时打不开，可稍后重试。</p>
                <button type="button" class="adp-mini-btn" @click="reload">重试</button>
              </div>

              <!-- 列表页（无正文）：展示可点进的文章清单 -->
              <div v-else class="adp-links">
                <p v-if="!data.links.length" class="adp-empty-line">该页面没有可读正文</p>
                <button
                  v-for="(l, i) in data.links || []"
                  :key="l.url + i"
                  type="button"
                  class="adp-link-row"
                  @click="openSource(l.url)"
                >
                  <span class="adp-link-text">{{ l.title }}</span>
                  <span class="adp-link-meta">
                    <span v-if="l.date" class="adp-link-date">{{ l.date }}</span>
                    <el-icon :size="14" class="adp-link-arrow"><ArrowRight /></el-icon>
                  </span>
                </button>
              </div>

              <!-- 附件下载：校站把附件下载区放在正文容器之外，正文里只剩一行
                   「附件：xxx名单」纯文字，真实地址由后端单独解析返回。
                   这里补一张下载卡片，点击直接走校站下载中转（新标签页，不打断阅读）。 -->
              <div v-if="attachments.length" class="adp-attachments">
                <a
                  v-for="a in attachments"
                  :key="a.url"
                  class="adp-attachment"
                  :href="a.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <el-icon :size="18" class="adp-attachment-icon"><Download /></el-icon>
                  <span class="adp-attachment-name">{{ a.name }}</span>
                  <span class="adp-attachment-action">下载</span>
                </a>
              </div>
            </article>

            <!-- ④ 评论区 -->
            <section class="adp-comments">
              <h2 class="adp-comments-head">{{ commentCount > 0 ? '共 ' + commentCount + ' 条评论' : '评论' }}</h2>

              <div v-if="commentsLoading" class="adp-comments-loading">
                <div class="sk-line w80" />
                <div class="sk-line w60" />
              </div>
              <div v-else-if="commentsError" class="adp-comments-state">
                <span>{{ commentsError }}</span>
                <button type="button" class="adp-mini-btn" @click="loadComments">重试</button>
              </div>
              <p v-else-if="!comments.length" class="adp-comments-empty">还没有评论，来说点什么吧</p>
              <ul v-else class="adp-comment-list">
                <li v-for="c in comments" :key="c.id" class="adp-comment">
                  <el-avatar :size="34" :src="c.author_avatar || undefined" :style="{ background: avatarBg(c) }">
                    {{ firstChar(c) }}
                  </el-avatar>
                  <div class="adp-comment-main">
                    <div class="adp-comment-top">
                      <span class="adp-comment-name">{{ c.author_name || '同学' }}</span>
                      <span class="adp-comment-time">{{ relativeTime(c.created_at) }}</span>
                      <button
                        v-if="c.mine"
                        type="button"
                        class="adp-comment-del"
                        :disabled="deletingId === c.id"
                        @click="onDeleteComment(c)"
                      >
                        删除
                      </button>
                    </div>
                    <p class="adp-comment-text">{{ c.content }}</p>
                  </div>
                </li>
              </ul>
            </section>
          </template>
        </div>

        <!-- ⑤ 底部输入栏：**滚动区之外**的独立一行。
             曾经放在滚动区里用 sticky 常驻，结果在部分浏览器下（截图实测 Edge）
             sticky 没有生效，输入栏直接叠在正文中间，把「三、具体要求」那块盖住了。
             现在改为 flex 列布局里的固定一行：不参与滚动、永远不会盖住内容，
             也不用再靠估算高度给滚动区垫留白。 -->
        <div v-if="data && !error" ref="composerRef" class="adp-composer">
          <div class="adp-input-wrap">
            <textarea
              ref="textareaRef"
              v-model="draft"
              class="adp-textarea"
              rows="1"
              :maxlength="500"
              placeholder="说点什么…"
              @input="autoGrow"
              @focus="autoGrow"
            />
            <span class="adp-count">{{ draft.length }}/500</span>
          </div>
          <button type="button" class="adp-send" :disabled="!canSend" @click="submitComment">
            {{ sending ? '发送中' : '发送' }}
          </button>
          <!-- 互动计数排在发送右侧：正文与评论之间不再单独占一条大按钮行，
               把「点赞 / 收藏 / 评论数」收进这条常驻的输入栏，滚动到哪儿都能点。
               数字按真实值显示（0 也显示），与信息流的计数口径一致。 -->
          <div class="adp-bar-acts">
            <button
              type="button"
              class="adp-bar-act"
              :class="{ 'is-on': liked }"
              :aria-pressed="liked"
              aria-label="点赞"
              @click="onLike"
            >
              <el-icon :size="19" :class="['adp-like-icon', { 'is-pop': likePop }]">
                <StarFilled v-if="liked" />
                <Star v-else />
              </el-icon>
              <span class="adp-bar-num">{{ likeCount }}</span>
            </button>
            <button
              type="button"
              class="adp-bar-act is-fav"
              :class="{ 'is-on': favorited }"
              :aria-pressed="favorited"
              aria-label="收藏"
              @click="onFavorite"
            >
              <el-icon :size="19"><CollectionTag /></el-icon>
              <span class="adp-bar-num">{{ favoriteCount }}</span>
            </button>
            <button type="button" class="adp-bar-act" aria-label="评论" @click="focusComposer">
              <el-icon :size="19"><ChatDotRound /></el-icon>
              <span class="adp-bar-num">{{ commentCount }}</span>
            </button>
          </div>
        </div>

        <!-- ⑥ 转发层：自己画遮罩 + 底部面板（不用 el-dialog，避免组件库默认样式接管版式） -->
        <Transition name="adp-pop">
          <div v-if="repostVisible" class="adp-sheet-mask" @click.self="closeRepost">
            <div class="adp-sheet">
              <div class="adp-sheet-head">
                <span class="adp-sheet-title">转发到</span>
                <button type="button" class="adp-sheet-close" aria-label="关闭" @click="closeRepost">
                  <el-icon :size="16"><Close /></el-icon>
                </button>
              </div>
              <p class="adp-sheet-desc">分享给同学，转发记录会保留</p>
              <textarea
                v-model="repostText"
                class="adp-sheet-textarea"
                rows="3"
                :maxlength="120"
                placeholder="说点什么（选填）"
              />
              <div class="adp-sheet-count">{{ repostText.length }}/120</div>
              <button type="button" class="adp-btn primary block" :disabled="reposting" @click="submitRepost">
                {{ reposting ? '转发中…' : '确认转发' }}
              </button>
              <button type="button" class="adp-copy-link" @click="copyLink">
                <el-icon :size="14"><Link /></el-icon> 复制链接
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 校园资讯「文章详情」子页
 *
 * 定位：移动端信息流（CampusPage.vue 的 .campus-feed）点进一条资讯后的全屏子页，
 * 相当于论坛 / 微博的帖子详情页 —— 正文 + 点赞 / 转发 / 评论 + 底部输入栏。
 *
 * 与 ArticleReader 的分工：ArticleReader 负责「抓取正文 + 原页渲染」的阅读能力，
 * 本组件负责「社区互动」这一层；两者共用同一套 .subpage 覆盖动画，观感是一家的。
 *
 * 用法（父组件持有 ref）：
 *   <ArticleDetailPage ref="detailRef" :article-url="url" :title="title"
 *                      @close="..." @updated="onUpdated" />
 *   detailRef.value?.reload()
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, ArrowRight, ChatDotRound, Close, CollectionTag, DocumentDelete, Download, Link, Refresh, Share, Star, StarFilled,
} from '@element-plus/icons-vue'
import type { CampusArticle } from '@/api/campus'
import {
  createArticleComment,
  deleteArticleComment,
  getArticleComments,
  getArticleDetail,
  repostArticle,
  toggleArticleFavorite,
  toggleArticleLike,
  type CampusArticleComment,
  type CampusArticleDetail,
} from '@/api/campus'

/* 注意：getArticleDetail / getArticleComments / toggleArticleLike / createArticleComment /
   deleteArticleComment / repostArticle 及它们的类型由 Lead 并行在 @/api/campus 补齐；
   补齐前 vue-tsc 会把它们报成「不存在」，属预期，本组件逻辑不依赖其实现细节。 */

/**
 * @prop articleUrl 文章原文地址（互动数据的键）
 * @prop title      列表里显示的标题（详情接口回来前的兜底标题）
 * @prop source     资讯来源 key（jwc_jxdt / jwc_tzgg / college_news …），
 *                  用于顶栏副标题与来源标签。为什么由父页传：
 *                  后端 social.source 只有在该文被互动过之后才有值，全新文章是空的，
 *                  而列表页本来就知道这条资讯来自哪个栏目，传下来最省事也最准。
 */
const props = defineProps<{ articleUrl: string; title?: string; source?: string }>()

const emit = defineEmits<{
  (e: 'close'): void
  /** 退场动画（.subpage 300ms）播完：父页收到后才能卸载本组件 */
  (e: 'closed'): void
  /** 请求父页用站内阅读器打开原文（正文不再由本页渲染） */
  (e: 'read', url: string): void
  (
    e: 'updated',
    payload: {
      url: string
      like_count: number
      favorite_count: number
      comment_count: number
      repost_count: number
      view_count: number
      liked: boolean
      favorited: boolean
    },
  ): void
}>()

/** source → 中文名：与 CampusPage.vue 的 SOURCE_LABELS 同一套文案（两页对不上会很割裂） */
const SOURCE_LABELS: Record<string, string> = {
  jwc_entries: '系统入口',
  jwc_jxdt: '教学动态',
  jwc_tzgg: '通知公告',
  jwc_gjxx: '高教信息',
  jwc_jxjs: '教学建设',
  college_news: '学院动态',
  library: '图书馆',
}

const visible = ref(false)
const loading = ref(false)
const error = ref('')
/** 当前文章的标题/日期等元信息（正文不在本页渲染，只取标题与来源展示） */
const data = ref<CampusArticle | null>(null)
/** 当前文章 URL：所有互动接口都以它为键（父页切换文章时由 watch 同步） */
const currentUrl = ref('')
/** 互动数据：与正文分开存，点赞 / 评论变化不必重拉正文 */
const social = ref<CampusArticleDetail['social'] | null>(null)

const comments = ref<CampusArticleComment[]>([])
const commentsLoading = ref(false)
const commentsError = ref('')

const draft = ref('')
const sending = ref(false)
const deletingId = ref<number | null>(null)

const repostVisible = ref(false)
const repostText = ref('')
const reposting = ref(false)

/** 点赞弹跳：先置真触发动画，320ms 后清掉，保证下次点击还能重播 */
const likePop = ref(false)

const scrollRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const composerRef = ref<HTMLElement | null>(null)
/** 顶栏投影只在滚动后出现，首屏保持干净 */
const scrolled = ref(false)

/* ============ 键盘偏移（VisualViewport） ============
   iOS / 安卓弹出键盘时只缩小 visualViewport，不改 layout viewport，也不触发 100% 高度重排，
   于是 fixed / sticky 的输入栏会被键盘直接挡住。这里用两者高度差算出键盘高度，
   写进 CSS 变量 --kb-offset 把输入栏顶上去。不支持 VisualViewport 的老浏览器保留 0，
   退化成「键盘盖住输入栏、用户自己滚动页面」的原行为，不会更差。 */
const kbOffset = ref(0)
const rootStyle = computed(() => ({ '--kb-offset': kbOffset.value + 'px' }))

let vv: VisualViewport | null = null
function syncKeyboard() {
  if (!window.visualViewport) { kbOffset.value = 0; return }
  const v = window.visualViewport
  // layout 高度 - visual 高度 - 顶部偏移 = 被遮挡高度；小于 80px 视为地址栏折叠等噪声，忽略
  const offset = Math.max(0, window.innerHeight - v.height - v.offsetTop)
  kbOffset.value = offset > 80 ? Math.round(offset) : 0
}

/* ================= 派生数据 ================= */

/** 顶栏主标题：固定文案。完整文章标题在下方正文区展示一次即可，顶栏不重复。 */
const headerTitle = '资讯详情'

/**
 * 顶栏副标题 = 来源栏目中文名（教学动态 / 通知公告 / …）。
 * 曾经放的是完整文章标题（会截断）和来源域名（英文噪音），都不适合手机顶栏；
 * 中文栏目名短、可读、且能回答「这是哪一类的资讯」。
 * 栏目名拿不到时留空，顶栏退化成单行标题，不留空行。
 */
/** 来源 key：父页传的优先，其次后端快照（老文章被互动过才有） */
const sourceKey = computed(() => props.source || social.value?.source || '')

const sourceLabel = computed(() => SOURCE_LABELS[sourceKey.value] || '资讯')

const likeCount = computed(() => social.value?.like_count ?? 0)
const commentCount = computed(() => social.value?.comment_count ?? 0)
const repostCount = computed(() => social.value?.repost_count ?? 0)
const viewCount = computed(() => social.value?.view_count ?? 0)
const liked = computed(() => social.value?.liked ?? false)
const favoriteCount = computed(() => social.value?.favorite_count ?? 0)
const favorited = computed(() => social.value?.favorited ?? false)

/** 正文之外的附件（校站下载区）：后端单独解析，避免正文只剩「附件：xxx」文字 */
const attachments = computed(() => data.value?.attachments || [])

const canSend = computed(() => !sending.value && draft.value.trim().length > 0)

/* ================= 通知父页 ================= */

/**
 * 每次本地计数变化都通知父页：信息流行尾的互动数字靠这个同步，
 * 否则用户返回列表时看到的还是旧数字，会以为操作没生效。
 */
function emitUpdated() {
  if (!currentUrl.value) return
  emit('updated', {
    url: currentUrl.value,
    like_count: likeCount.value,
    favorite_count: favoriteCount.value,
    comment_count: commentCount.value,
    repost_count: repostCount.value,
    view_count: viewCount.value,
    liked: liked.value,
    favorited: favorited.value,
  })
}

/* ================= 加载 ================= */

async function loadDetail() {
  if (!currentUrl.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await getArticleDetail(currentUrl.value)
    data.value = res.article
    social.value = res.social
    emitUpdated()
  } catch (e: any) {
    // 走到这里说明**详情接口本身**失败了（网络/鉴权），不是「校站正文抓不到」——
    // 正文已不在本页渲染，抓取失败在后端会降级成 article.kind === 'error'，不会抛异常。
    error.value = e?.response?.data?.detail || '资讯详情加载失败，请稍后重试'
    data.value = null
    social.value = null
  } finally {
    loading.value = false
  }
  // 详情失败时评论也没有意义，成功后再拉
  if (!error.value) void loadComments()
}

async function loadComments() {
  if (!currentUrl.value) return
  commentsLoading.value = true
  commentsError.value = ''
  try {
    comments.value = await getArticleComments(currentUrl.value)
  } catch {
    // 评论加载失败不打断正文阅读，只在评论区就地给出重试
    commentsError.value = '评论加载失败'
    comments.value = []
  } finally {
    commentsLoading.value = false
  }
}

/* ================= 正文后处理（v-html 渲染完之后） ==================
   v-html 生成的 DOM 在 Vue 模板里拿不到 ref，只能渲染后手动加工。
   为什么在前端做而不是后端改 HTML：可读性取决于**屏幕宽度**，后端不知道这页
   要渲染在 390px 手机还是 760px 桌面 —— 把表格宽度写死成某一档，另一档必然变形。
   后端只负责净化（去脚本、图片地址绝对化），排版适配留给知道自身宽度的地方。 */

const contentRef = ref<HTMLElement | null>(null)

/** 署名 / 页脚信息行：编辑器里与正文同字号，识别后压灰，正文与署名才有视觉分界 */
const BYLINE_RE = /^(供稿|供图|作者|编辑|审核|初审|复审|终审|一审|二审|三审|摄影|来源|撰稿|排版)\s*[\/／:：]/

/**
 * 加工正文 DOM：
 * ① 表格包一层横滑壳 `.adp-table-wrap`（已在壳里的跳过，避免套两层）；
 * ② 给署名行打 `.adp-byline`。
 * v-html 每次重渲染都会整体替换 DOM，因此每次拿到的都是新节点，天然幂等。
 */
function enhanceContent() {
  const root = contentRef.value
  if (!root) return

  root.querySelectorAll('table').forEach((tbl) => {
    if (tbl.parentElement && tbl.parentElement.classList.contains('adp-table-wrap')) return
    const wrap = document.createElement('div')
    wrap.className = 'adp-table-wrap'
    tbl.parentNode && tbl.parentNode.insertBefore(wrap, tbl)
    wrap.appendChild(tbl)
  })

  root.querySelectorAll('p').forEach((el) => {
    const text = (el.textContent || '').trim()
    if (text && text.length <= 40 && BYLINE_RE.test(text)) el.classList.add('adp-byline')
  })
}

/** 正文是接口回来后才渲染的，所以在 DOM 更新后再跑一次 */
watch(
  () => data.value?.content_html,
  async () => {
    await nextTick()
    enhanceContent()
  },
  { immediate: true },
)

/** 重新拉取详情（错误态重试 / 父组件手动刷新） */
async function reload() {
  await loadDetail()
}

/* ================= 生命周期 ================= */

function open(url: string) {
  if (!url) return
  currentUrl.value = url
  data.value = null
  social.value = null
  comments.value = []
  commentsError.value = ''
  draft.value = ''
  error.value = ''
  visible.value = true
  void loadDetail()
}

function close() {
  if (!visible.value) return
  visible.value = false
  repostVisible.value = false
  emit('close')
}

/* ================= 打开原文 ================= */

/**
 * 打开一个校内链接：正文已在本页渲染，本函数只给「列表页（无正文）」的链接行用。
 * - 校内 *.mycc.edu.cn：交给 ArticleReader（应用内阅读，不跳出 App）；
 * - 站外 / 登录型系统：新窗口打开（校内系统设了 X-Frame-Options: SAMEORIGIN，无法内嵌）。
 * 参数缺省时取当前文章地址。
 */
function openSource(target?: string) {
  const url = target || currentUrl.value
  if (!url) return
  let host = ''
  try { host = new URL(url).hostname.toLowerCase() } catch { host = '' }
  const isCampus = host === 'mycc.edu.cn' || host.endsWith('.mycc.edu.cn')
  if (isCampus) {
    emit('read', url)
    return
  }
  openExternal(url)
}

/** 在浏览器打开：新标签页优先，被拦截时回退当前页（与 ArticleReader 同一策略） */
function openExternal(target?: string) {
  const url = target || currentUrl.value
  if (!url) return
  const win = window.open(url, '_blank', 'noopener,noreferrer')
  if (!win) window.location.href = url
}

function onScroll() {
  scrolled.value = (scrollRef.value?.scrollTop || 0) > 4
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key !== 'Escape' || !visible.value) return
  // 转发面板优先级高于整页：Esc 先关面板，再按一次才退出
  if (repostVisible.value) { closeRepost(); return }
  close()
}

/* ================= 互动：点赞 ================= */

/**
 * 点赞用乐观更新：点赞是纯 UI 反馈，等一次 200~400ms 的网络往返才变色，
 * 手感上就是「点了没反应」，用户容易连点。所以先改本地状态，失败再回滚。
 * 回滚用快照而非差量加减：并发连点时差量会累加错，快照总是回到点击前那一个确定值。
 */
async function onLike() {
  if (!social.value) return
  const snapshot = { liked: social.value.liked, like_count: social.value.like_count }
  const nextLiked = !snapshot.liked

  social.value.liked = nextLiked
  social.value.like_count = Math.max(0, snapshot.like_count + (nextLiked ? 1 : -1))
  likePop.value = true
  emitUpdated()

  try {
    const res = await toggleArticleLike(currentUrl.value)
    // 以服务端返回为准：多端并发时本地推算只是猜测
    if (social.value) {
      social.value.liked = res.liked
      social.value.like_count = res.count
    }
    emitUpdated()
  } catch (e: any) {
    if (social.value) {
      social.value.liked = snapshot.liked
      social.value.like_count = snapshot.like_count
    }
    emitUpdated()
    // 5xx / 网络错误已由 request.ts 统一提示，这里只补业务错误，避免重复弹窗
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '点赞失败，请重试')
  } finally {
    window.setTimeout(() => { likePop.value = false }, 320)
  }
}

/* ================= 互动：收藏 ================= */

/**
 * 收藏与点赞同一套乐观更新：先改本地颜色与计数，失败按快照回滚。
 * 收藏是「以后还要找回来」的收藏夹动作，与点赞（认可）互不影响，各记各的计数。
 */
async function onFavorite() {
  if (!social.value) return
  const snapshot = { favorited: social.value.favorited, favorite_count: social.value.favorite_count }
  const nextFavorited = !snapshot.favorited

  social.value.favorited = nextFavorited
  social.value.favorite_count = Math.max(0, snapshot.favorite_count + (nextFavorited ? 1 : -1))
  emitUpdated()

  try {
    const res = await toggleArticleFavorite(currentUrl.value)
    if (social.value) {
      social.value.favorited = res.favorited
      social.value.favorite_count = res.count
    }
    emitUpdated()
  } catch (e: any) {
    if (social.value) {
      social.value.favorited = snapshot.favorited
      social.value.favorite_count = snapshot.favorite_count
    }
    emitUpdated()
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '收藏失败，请重试')
  }
}

/* ================= 互动：评论 ================= */

function focusComposer() {
  composerRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  nextTick(() => textareaRef.value?.focus())
}

/** textarea 自适应 1~4 行：超过 4 行内部滚动，避免输入框把正文顶出屏幕 */
function autoGrow() {
  const el = textareaRef.value
  if (!el) return
  const lh = 22
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, lh * 4 + 20) + 'px'
}

async function submitComment() {
  const content = draft.value.trim()
  if (!content || sending.value || !currentUrl.value) return
  sending.value = true
  try {
    const created = await createArticleComment(currentUrl.value, content)
    comments.value.unshift(created)
    if (social.value) social.value.comment_count += 1
    draft.value = ''
    await nextTick()
    autoGrow()
    emitUpdated()
    ElMessage.success('评论成功')
  } catch (e: any) {
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '评论失败，请重试')
  } finally {
    sending.value = false
  }
}

async function onDeleteComment(c: CampusArticleComment) {
  if (deletingId.value !== null) return
  deletingId.value = c.id
  try {
    await deleteArticleComment(c.id)
    comments.value = comments.value.filter((x) => x.id !== c.id)
    if (social.value) social.value.comment_count = Math.max(0, social.value.comment_count - 1)
    emitUpdated()
  } catch (e: any) {
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '删除失败，请重试')
  } finally {
    deletingId.value = null
  }
}

/* ================= 互动：转发 ================= */

function openRepost() {
  repostText.value = ''
  repostVisible.value = true
}

function closeRepost() {
  repostVisible.value = false
  repostText.value = ''
}

async function submitRepost() {
  if (reposting.value || !currentUrl.value) return
  reposting.value = true
  try {
    const res = await repostArticle(currentUrl.value, repostText.value.trim())
    if (social.value) social.value.repost_count = res.count
    closeRepost()
    emitUpdated()
    ElMessage.success('已转发')
  } catch (e: any) {
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '转发失败，请重试')
  } finally {
    reposting.value = false
  }
}

/** 复制链接：Clipboard API 需要安全上下文（https / localhost），内网 http 下会 reject，故留 execCommand 兜底 */
async function copyLink() {
  const url = currentUrl.value
  if (!url) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      fallbackCopy(url)
    }
    ElMessage.success('链接已复制')
  } catch {
    try {
      fallbackCopy(url)
      ElMessage.success('链接已复制')
    } catch {
      ElMessage.error('复制失败，请手动选择链接')
    }
  }
}

function fallbackCopy(text: string) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.top = '-1000px'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(ta)
  if (!ok) throw new Error('copy failed')
}

/* ================= 分享 ================= */

/**
 * 顶栏分享：优先调用系统原生分享面板（Web Share API），不支持时降级为「复制链接」。
 *
 * 为什么分两条路：
 * - 真机上 `navigator.share` 会拉起系统面板，微信 / QQ / 邮件全在一起，
 *   比自绘一个只能复制的面板有用得多；
 * - 桌面浏览器与 http 内网环境没有 `navigator.share`（它要求安全上下文），
 *   此时复制链接是唯一可行且用户能理解的动作。
 *
 * 取消分享不提示错误：用户主动点了取消，弹「分享失败」是很糟的体验；
 * 但真正失败（非安全上下文、被策略拦截）必须能兜底成复制，否则点了没反应。
 */
async function onShare() {
  const url = currentUrl.value
  if (!url) return
  const shareData: ShareData = {
    title: data.value?.title || url,
    text: data.value?.title || '',
    url,
  }
  const canShare =
    typeof navigator.share === 'function' &&
    (!navigator.canShare || navigator.canShare(shareData))
  if (canShare) {
    try {
      await navigator.share(shareData)
      return
    } catch (e: any) {
      // AbortError = 用户点了取消：安静退出，不打扰
      if (e?.name === 'AbortError') return
      // 其它错误 → 往下走复制链接兜底
    }
  }
  await copyLink()
}

/* ================= 评论区展示工具 ================= */

function firstChar(c: CampusArticleComment) {
  return (c.author_name || '同').trim().slice(0, 1)
}

/** 头像底色：按 user_id 取模落到一组柔和色上，同一个人每次进来颜色一致 */
const AVATAR_COLORS = ['#dbeafe', '#e0e7ff', '#fce7f3', '#dcfce7', '#fef3c7', '#fee2e2', '#ede9fe', '#cffafe']
function avatarBg(c: CampusArticleComment) {
  const idx = Math.abs(Number(c.user_id) || 0) % AVATAR_COLORS.length
  return AVATAR_COLORS[idx]
}

/**
 * 相对时间：刚刚 / N 分钟前 / HH:mm / MM-DD。
 * 评论的时效性集中在「刚刚到几小时」，当天只给时刻，跨天才给月日。
 */
function relativeTime(iso: string | null): string {
  if (!iso) return ''
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  const now = Date.now()
  const diff = now - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  const d = new Date(t)
  const sameDay = new Date(now).toDateString() === d.toDateString()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  if (sameDay) return `${hh}:${mm}`
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/* ================= 侦听 ================= */

// props.articleUrl 变化 = 父页换了文章：在已打开状态下直接重载，避免「先关再开」的闪烁
watch(
  () => props.articleUrl,
  (v) => {
    if (v && v !== currentUrl.value) open(v)
  },
)

// 打开时锁定背景滚动（关闭 / 卸载时恢复），保证 iOS 上不会滚到列表层
watch(visible, async (v) => {
  await nextTick()
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) {
    scrolled.value = false
    syncKeyboard()
  } else {
    kbOffset.value = 0
  }
})

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  if (window.visualViewport) {
    vv = window.visualViewport
    vv.addEventListener('resize', syncKeyboard)
    vv.addEventListener('scroll', syncKeyboard)
  }
  // 父页用 v-if 控制挂载时，挂载即打开，不必再多调一次 open()
  if (props.articleUrl) open(props.articleUrl)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (vv) {
    vv.removeEventListener('resize', syncKeyboard)
    vv.removeEventListener('scroll', syncKeyboard)
    vv = null
  }
  document.body.style.overflow = ''
})

/**
 * 供父页在「打开后立刻做一件事」时使用：
 * 信息流行尾的评论 / 转发小按钮点进来时，直接聚焦输入框或弹转发面板，
 * 省掉「先进详情、再点一次同款按钮」的一步。等详情加载完再执行，
 * 避免输入栏还处于骨架态时 focus 落空。
 */
async function openAnd(url: string, action: 'comment' | 'repost') {
  open(url)
  // 等一次详情加载结束（最长约 12s 抓取超时），再执行动作
  const started = Date.now()
  while (loading.value && Date.now() - started < 12000) {
    await new Promise((r) => window.setTimeout(r, 120))
  }
  if (!visible.value) return
  if (action === 'comment') focusComposer()
  else openRepost()
}

defineExpose({ reload, open, openAnd, close })
</script>

<style scoped>
/* ================= 根容器 =================
   fixed inset:0 的整页覆盖层。z-index 2600 高于移动端底部导航（MobileTabBar 的 1000）
   与顶栏（100）；本页内部的 ElMessage 会落在组件库自己的更高层级，仍可见。
   进出场动画统一走全局 .subpage（styles/animations.css，keyframes 驱动）——
   本页曾是全站第一处 animation 驱动的子页，方案验证后已收编进全局，不再自带一份。 */
.adp-root {
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
.adp-head {
  position: relative;
  z-index: 2;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 52px;
  padding: 6px 8px;
  padding-top: calc(6px + env(safe-area-inset-top, 0px));
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  transition: box-shadow 0.2s ease;
}
/* 滚动后才给投影：首屏不加，避免顶栏和正文之间出现一道灰线 */
.adp-head.is-scrolled { box-shadow: 0 2px 10px rgba(29, 33, 41, 0.06); }

.adp-icon-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #4e5969;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background 0.14s ease, opacity 0.14s ease;
}
.adp-icon-btn:active { background: #f2f3f5; opacity: 0.62; }

.adp-head-title { flex: 1; min-width: 0; text-align: center; }
.adp-head-main {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ================= 滚动区 ================= */
.adp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  background: #fff;
  /* 输入栏已在滚动区之外（.adp-root 的固定一行），这里不需要垫留白，
     只给最后一条评论留一点呼吸空间，免得紧贴输入栏的上边框。 */
  padding-bottom: 8px;
}
.adp-meta-text { font-variant-numeric: tabular-nums; }

/* ================= 正文 ================= */
.adp-article { padding: 16px 16px 4px; }

.adp-title {
  margin: 0 0 10px;
  font-size: 21px;
  font-weight: 700;
  line-height: 1.45;
  color: #1d2129;
  word-break: break-word;
}

.adp-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #86909c;
}
.adp-source-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 11px;
  background: #eef2ff;
  color: #2563eb;
  font-size: 12px;
  line-height: 1;
}

/* ================= 正文富文本 ==================
   校站正文是「所见即所得编辑器」的产物，结构极不规整：获奖名单类文章有 7 张表、
   上百行 × 4 列；`width`/`align` 内联属性到处是；大量 `<br>` 与空 `<p>` 当留白用；
   图片带 `width="800"` 且各自包在 `<p>` 里。原样丢进 390px 屏幕会：表格被压成一条
   竖线、正文一段段被撑出几十像素空洞。下面按「先保证可读」重排：
     1. 表格改成**横向滚动卡片**：不压列宽、不换行，手指横滑看全表；
     2. 单元格 13px / 行高 1.55，表头浅灰底 —— 名单表才有「表格感」；
     3. 图片统一圆角居中，并去掉 `<p>` 包裹造成的双重上下留白；
     4. 段间距交给 CSS，`<br>` 与空段落不占位；
     5. 末尾「供稿/作者/一审」这类署名行压灰，与正文拉开层次。
   ！！scoped 样式对 v-html 内容无效，全部用 :deep() 穿透。 */
.adp-content {
  font-size: 16px;
  /* 1.75 行高：中文长段落 1.6 偏挤、1.9 又散，1.75 是手机阅读的舒适区 */
  line-height: 1.75;
  color: #1f2329;
  letter-spacing: 0.01em;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.adp-content :deep(p) { margin: 0 0 14px; }
.adp-content :deep(p:last-child) { margin-bottom: 0; }
/* 空段落 / 换行：编辑器拿它们当留白，这里一律不占位（否则正文全是空洞） */
.adp-content :deep(p:empty) { display: none; }
.adp-content :deep(br) { display: none; }

/* ---------- 图片 ----------
   后端抓来的图片带 width="800" 这类属性；只允许 max-width 收缩、高度自动，
   否则要么撑破容器，要么被压成 1px 高的细线。
   `p > img:only-child` 把段落 margin 收掉：编辑器常把「一张图一个段落」。 */
.adp-content :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 10px;
  margin: 4px auto;
  background: #f4f5f7;
}
.adp-content :deep(p > img:only-child) { margin-bottom: 0; }
.adp-content :deep(p:has(> img:only-child)) { margin: 0 0 10px; }

/* ---------- 表格：横向滚动而不是压缩 ----------
   原先 `width: 100%` 把 4 列的获奖名单硬塞进 390px，每列不到 90px，汉字被挤成一列
   一个字。现在表格 `width: auto` + `nowrap` 保住列宽，外层包可横滑容器。
   ⚠️ 容器由 JS 在渲染后包上（v-html 无法生成 wrapper），见 enhanceContent()。 */
.adp-content :deep(.adp-table-wrap) {
  margin: 14px 0;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
  border: 1px solid #ebedf0;
  border-radius: 10px;
  background: #fff;
}
.adp-content :deep(.adp-table-wrap::-webkit-scrollbar) { height: 4px; }
.adp-content :deep(.adp-table-wrap::-webkit-scrollbar-thumb) { background: #d9dde3; border-radius: 2px; }
.adp-content :deep(table) {
  width: auto !important;
  min-width: 100%;
  max-width: none;
  border-collapse: collapse;
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
}
.adp-content :deep(td),
.adp-content :deep(th) {
  padding: 8px 10px;
  border: 1px solid #ebedf0;
  text-align: left;
  vertical-align: middle;
  /* 名单表的核心诉求是「一行能读完」，不换行，靠外层横滑看全 */
  white-space: nowrap;
  color: #26282c;
}
.adp-content :deep(td p),
.adp-content :deep(th p) { margin: 0; }
.adp-content :deep(tr:nth-child(even)) { background: #fafbfc; }
/* 表头只认语义化的 <th>：校站 CMS 的表常没有 thead，第一行就是数据行，
   用 `tr:first-child` 会把数据行误当表头加粗（实测踩过）。 */
.adp-content :deep(th) { background: #f2f4f7; font-weight: 600; }
/* 跨列单元格几乎必然是「表格标题」（如「…获奖名单」），居中加粗但不给灰底 */
.adp-content :deep(td[colspan]) { text-align: center; font-weight: 600; }

/* ---------- 其余行内元素 ---------- */
.adp-content :deep(a) { color: #2563eb; text-decoration: none; border-bottom: 1px solid rgba(37, 99, 235, .25); }
.adp-content :deep(strong), .adp-content :deep(b) { font-weight: 700; color: #111827; }
.adp-content :deep(ul),
.adp-content :deep(ol) { padding-left: 20px; margin: 0 0 14px; }
.adp-content :deep(li) { margin: 4px 0; }
.adp-content :deep(blockquote) {
  margin: 14px 0;
  padding: 10px 14px;
  background: #f7f8fa;
  border-left: 3px solid #c9d3e4;
  border-radius: 0 8px 8px 0;
  color: #4e5969;
}
.adp-content :deep(h1),
.adp-content :deep(h2),
.adp-content :deep(h3) { font-size: 17px; line-height: 1.5; margin: 18px 0 10px; color: #111827; }
/* 署名行（供稿 / 作者 / 一审…）：编辑器里与正文同字号，压灰后正文到署名才有分界 */
.adp-content :deep(p.adp-byline) { font-size: 13.5px; color: #86909c; margin-bottom: 4px; }

/* ================= 正文降级 / 列表页 ================= */
.adp-links { border-top: 1px solid #f0f0f0; }
.adp-empty-line { margin: 32px 0; text-align: center; font-size: 13px; color: #b2b2b2; }
/* 抓取失败的就地降级（互动区与评论区仍在下方）：比整页错误页克制得多 */
.adp-inline-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 40px 16px;
  text-align: center;
}
.adp-inline-title { margin: 0; font-size: 15px; font-weight: 600; color: #1d2129; }
.adp-inline-desc { margin: 0 0 8px; font-size: 13px; line-height: 1.6; color: #86909c; }
.adp-link-row {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 0;
  border: none;
  border-bottom: 1px solid #f0f0f0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.14s ease;
}
.adp-link-row:active { opacity: 0.62; }
.adp-link-text { flex: 1; min-width: 0; font-size: 14.5px; line-height: 1.5; color: #26282c; }
.adp-link-meta { display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; }
.adp-link-date { font-size: 11.5px; color: #86909c; }
.adp-link-arrow { color: #b2b2b2; }

/* ================= 附件下载 =================
   正文里那行「附件：xxx名单」是校站编辑器里的纯文字，真正的下载地址在正文容器之外，
   由后端解析后在这里渲染成卡片。手机上没有悬停，整张卡片就是热区。 */
.adp-attachments { display: flex; flex-direction: column; gap: 8px; margin: 12px 0 4px; }
.adp-attachment {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid #ebedf0;
  border-radius: 12px;
  background: #f8fafc;
  color: #1d2129;
  text-decoration: none;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.14s ease;
}
.adp-attachment:active { opacity: 0.62; }
.adp-attachment-icon { flex-shrink: 0; color: #2563eb; }
.adp-attachment-name {
  flex: 1;
  min-width: 0;
  font-size: 14.5px;
  line-height: 1.5;
  word-break: break-all;
}
.adp-attachment-action { flex-shrink: 0; font-size: 13px; color: #2563eb; }

/* ================= 骨架屏 ================= */
.adp-skeleton { padding: 22px 16px; display: flex; flex-direction: column; gap: 14px; }
.sk-gap { height: 6px; }
.sk-line {
  height: 13px;
  border-radius: 7px;
  background: linear-gradient(90deg, #eef0f3, #f6f7f9, #eef0f3);
  background-size: 200% 100%;
  animation: adp-shimmer 1.2s ease-in-out infinite;
}
.sk-line.w50 { width: 50%; } .sk-line.w60 { width: 60%; } .sk-line.w70 { width: 70%; }
.sk-line.w80 { width: 80%; } .sk-line.w90 { width: 90%; } .sk-line.w95 { width: 95%; } .sk-line.w100 { width: 100%; }
@keyframes adp-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ================= 错误态 ================= */
.adp-state {
  /* 绝对定位于 .adp-root：撑满整屏（含页头高度），错误态按整屏上下居中；
     页头 z-index 更高保持可点，本层透明不遮内容 */
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  text-align: center;
}
.adp-state-icon { color: #c9cdd4; }
.adp-state-title { margin: 4px 0 0; font-size: 15px; font-weight: 600; color: #1d2129; }
.adp-state-desc { margin: 0; font-size: 13px; line-height: 1.6; color: #86909c; max-width: 340px; }
.adp-state-btns { display: flex; gap: 10px; margin-top: 12px; }

.adp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 40px;
  padding: 0 16px;
  border: 1px solid #e5e6eb;
  border-radius: 10px;
  background: #fff;
  color: #1d2129;
  font-size: 14px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.14s ease;
}
.adp-btn:active { opacity: 0.62; }
.adp-btn.primary { background: #2563eb; border-color: transparent; color: #fff; }
.adp-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.adp-btn.block { width: 100%; }

/* ================= 点赞弹跳 =================
   点赞 / 收藏 / 评论数已从正文下方的大按钮行搬到底部输入栏右侧（见 .adp-bar-acts），
   这里只保留图标本身的一次弹跳反馈，与动作放在哪里无关。 */

.adp-like-icon.is-pop { animation: adp-like-pop 0.32s ease; }
@keyframes adp-like-pop {
  0% { transform: scale(1); }
  35% { transform: scale(1.35); }
  100% { transform: scale(1); }
}

/* ================= 评论区 ================= */
.adp-comments { padding: 4px 16px 16px; }
.adp-comments-head {
  margin: 16px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}
.adp-comments-loading { display: flex; flex-direction: column; gap: 10px; padding: 8px 0 16px; }
.adp-comments-state,
.adp-comments-empty {
  margin: 0;
  padding: 28px 0;
  text-align: center;
  font-size: 13.5px;
  color: #b2b2b2;
}
.adp-comments-state { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.adp-mini-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 16px;
  background: #fff;
  color: #4e5969;
  font-size: 13px;
  cursor: pointer;
}

.adp-comment-list { list-style: none; margin: 0; padding: 0; }
.adp-comment {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f7f8fa;
}
.adp-comment:last-child { border-bottom: 0; }
.adp-comment-main { flex: 1; min-width: 0; }
.adp-comment-top { display: flex; align-items: center; gap: 8px; }
.adp-comment-name {
  font-size: 13.5px;
  font-weight: 500;
  color: #4e5969;
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.adp-comment-time { font-size: 12px; color: #b2b2b2; }
.adp-comment-del {
  margin-left: auto;
  min-width: 40px;
  height: 28px;
  padding: 0 6px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #86909c;
  font-size: 12.5px;
  cursor: pointer;
}
.adp-comment-del:active { background: #f2f3f5; }
.adp-comment-del:disabled { opacity: 0.5; cursor: not-allowed; }
/* 保留换行：用户手打的换行必须原样呈现，否则多段评论会粘成一坨 */
.adp-comment-text {
  margin: 4px 0 0;
  font-size: 14.5px;
  line-height: 1.65;
  color: #26282c;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ================= 底部输入栏 =================
   位置：在**滚动区之外**，是 .adp-root（flex column）的最后一个 flex 子项。
   为什么不再用 sticky：曾经把它放在滚动区里 sticky 常驻，但实测（Playwright + Edge）
   sticky 没有按预期生效，输入栏直接浮在正文中间，把「三、具体要求」那一段盖住了。
   放在滚动区外是结构性保证 —— flex 行永远在容器底部，不参与滚动，不可能盖住内容。
   键盘弹出时用 VisualViewport 算出的 --kb-offset 把整条栏顶上去；
   padding-bottom 叠加 safe-area，iPhone 手势条不会压住发送按钮。 */
.adp-composer {
  flex-shrink: 0;
  position: relative;
  bottom: var(--kb-offset, 0px);
  z-index: 2;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 10px 16px;
  padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
  background: #fff;
  border-top: 1px solid #f0f0f0;
  transition: bottom 0.16s ease;
}
.adp-input-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  background: #f7f8fa;
  border-radius: 13px;
  padding: 8px 10px 16px;
}
.adp-textarea {
  display: block;
  width: 100%;
  min-height: 22px;
  max-height: 108px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-size: 15px;
  line-height: 22px;
  color: #1d2129;
  font-family: inherit;
  overflow-y: auto;
}
.adp-textarea::placeholder { color: #b2b2b2; }
.adp-count {
  position: absolute;
  right: 10px;
  bottom: 2px;
  font-size: 11px;
  color: #b2b2b2;
  font-variant-numeric: tabular-nums;
}
.adp-send {
  flex-shrink: 0;
  height: 40px;
  min-width: 62px;
  padding: 0 16px;
  border: none;
  border-radius: 20px;
  background: #2563eb;
  color: #fff;
  font-size: 14.5px;
  font-weight: 500;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.14s ease, background 0.14s ease;
}
.adp-send:active:not(:disabled) { opacity: 0.72; }
.adp-send:disabled { background: #c9d4e8; cursor: not-allowed; }

/* 发送右侧的互动区：点赞 / 收藏 / 评论数，竖向「图标 + 数字」紧凑排列。
   放在输入栏里是为了让这三个动作常驻屏幕底部，正文滚到多深都能点；
   数字始终显示（含 0），与信息流的计数口径一致。 */
.adp-bar-acts {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 4px;
  padding-bottom: 4px;
}
.adp-bar-act {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  min-width: 26px;
  padding: 2px 3px;
  border: none;
  background: transparent;
  color: #86909c;
  line-height: 1;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: color 0.14s ease, transform 0.12s ease;
}
.adp-bar-act:active { transform: scale(0.92); }
/* 已点赞 = 品牌蓝；已收藏 = 琥珀色。两个动作各自独立，颜色不共用 */
.adp-bar-act.is-on { color: #2563eb; }
.adp-bar-act.is-fav.is-on { color: #f5a623; }
.adp-bar-num { font-size: 11px; font-variant-numeric: tabular-nums; }

/* ================= 转发面板 ================= */
.adp-sheet-mask {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(17, 20, 24, 0.45);
}
.adp-sheet {
  width: 100%;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom, 0px));
}
.adp-sheet-head { display: flex; align-items: center; justify-content: space-between; }
.adp-sheet-title { font-size: 16px; font-weight: 600; color: #1d2129; }
.adp-sheet-close {
  width: 40px;
  height: 40px;
  margin-right: -8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #86909c;
  cursor: pointer;
}
.adp-sheet-desc { margin: 2px 0 12px; font-size: 13px; color: #86909c; }
.adp-sheet-textarea {
  width: 100%;
  box-sizing: border-box;
  min-height: 76px;
  padding: 10px 12px;
  border: none;
  outline: none;
  resize: none;
  border-radius: 13px;
  background: #f7f8fa;
  font-size: 15px;
  line-height: 1.5;
  color: #1d2129;
  font-family: inherit;
}
.adp-sheet-textarea::placeholder { color: #b2b2b2; }
.adp-sheet-count {
  margin: 6px 2px 12px;
  text-align: right;
  font-size: 11.5px;
  color: #b2b2b2;
  font-variant-numeric: tabular-nums;
}
.adp-copy-link {
  width: 100%;
  height: 40px;
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: none;
  background: transparent;
  color: #86909c;
  font-size: 13.5px;
  cursor: pointer;
}
.adp-copy-link:active { opacity: 0.62; }

/* 面板进出：只动位移与透明度，不引入额外依赖 */
.adp-pop-enter-active,
.adp-pop-leave-active { transition: opacity 0.2s ease; }
.adp-pop-enter-active .adp-sheet,
.adp-pop-leave-active .adp-sheet { transition: transform 0.24s ease; }
.adp-pop-enter-from,
.adp-pop-leave-to { opacity: 0; }
.adp-pop-enter-from .adp-sheet,
.adp-pop-leave-to .adp-sheet { transform: translateY(100%); }

/* ================= 桌面端：居中限宽 760px 的整页，不做额外桌面版式 ================= */
@media (min-width: 768px) {
  .adp-root { align-items: center; }
  .adp-head,
  .adp-scroll { width: 100%; max-width: 760px; }
  .adp-sheet { max-width: 760px; }
}

@media (prefers-reduced-motion: reduce) {
  .adp-root { animation: none !important; }
  .adp-pop-enter-active,
  .adp-pop-leave-active,
  .adp-pop-enter-active .adp-sheet,
  .adp-pop-leave-active .adp-sheet { transition: none !important; }
  .adp-like-icon.is-pop { animation: none !important; }
}
</style>