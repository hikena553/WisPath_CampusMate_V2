<template>
  <Teleport to="body">
    <!-- 全屏子页：版式与 CampusPage 的资讯详情（ArticleDetailPage）同一套 ——
         同样的 52px 顶栏、同样 21px 标题 + 13px 元信息、同样 16px/1.75 正文、
         同样的评论区密度与「输入框 + 计数 + 发送 + 右侧互动列」底栏。
         差异只在内容本体：帖子有作者行（可关注）与配图，资讯有来源标签与附件。
         动画复用全局 .subpage（styles/animations.css），与详情 / 搜索 / 阅读器一致；
         Teleport 到 body 是必需的：父页打开子页时会挂 .subpage-underlay 退 -30%，
         留在父页里会因为祖先 transform 把 fixed 定位改成相对父元素定位。 -->
    <Transition name="subpage" :duration="320" @after-leave="emit('closed')">
      <div
        v-if="visible"
        class="pdp-root"
        role="dialog"
        aria-modal="true"
        :aria-label="'帖子详情：' + (post?.title || '')"
        :style="rootStyle"
      >
        <!-- ① 顶栏：返回 /「帖子详情」/ 删除（仅作者）+ 分享 -->
        <header class="pdp-head" :class="{ 'is-scrolled': scrolled }">
          <button type="button" class="pdp-icon-btn" aria-label="返回" @click="close">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <div class="pdp-head-title">
            <div class="pdp-head-main">帖子详情</div>
          </div>
          <div class="pdp-head-acts">
            <button v-if="isMine" type="button" class="pdp-del-btn" @click="removePost">删除</button>
            <button type="button" class="pdp-icon-btn" aria-label="分享" @click="onShare">
              <el-icon :size="18"><Share /></el-icon>
            </button>
          </div>
        </header>

        <!-- ② 滚动区：作者 / 标题 / 正文 / 配图 / 评论区同处一个滚动条 -->
        <div ref="scrollRef" class="pdp-scroll" @scroll.passive="onScroll">
          <!-- 骨架屏：行宽节奏与资讯详情一致，避免「加载中…」一行字带来的空屏跳变 -->
          <div v-if="loading" class="pdp-skeleton">
            <div class="pdp-sk-line w40" />
            <div class="pdp-sk-gap" />
            <div class="pdp-sk-line w100" />
            <div class="pdp-sk-line w95" />
            <div class="pdp-sk-line w90" />
            <div class="pdp-sk-line w100" />
            <div class="pdp-sk-line w60" />
          </div>

          <!-- 错误态：帖子被删 / 网络失败。与资讯详情同样是整屏居中的独立态 -->
          <div v-else-if="error" class="pdp-state">
            <el-icon :size="44" class="pdp-state-icon"><DocumentDelete /></el-icon>
            <p class="pdp-state-title">帖子暂不可用</p>
            <p class="pdp-state-desc">{{ error }}</p>
            <div class="pdp-state-btns">
              <button type="button" class="pdp-btn primary" @click="reload">
                <el-icon :size="15"><Refresh /></el-icon> 重试
              </button>
            </div>
          </div>

          <template v-else-if="post">
            <article class="pdp-article">
              <!-- 作者行：帖子比资讯多出来的信息。关注按钮留在这一行右端，
                   与信息流里的作者展示口径一致；自己的帖子不显示关注 -->
              <div class="pdp-author">
                <el-avatar :size="36" :src="post.author_avatar || undefined" :style="{ background: avatarBg(post.student_id) }">
                  {{ (post.author_name || '同').slice(0, 1) }}
                </el-avatar>
                <div class="pdp-author-main">
                  <div class="pdp-author-name">{{ post.author_name || '同学' }}</div>
                  <!-- 时间只在下方元信息行出现一次：作者行再放一遍同款时间，
                       一屏里会看到两个一模一样的 13:45，反而让人怀疑哪个是发布时间 -->
                </div>
                <button
                  v-if="!isMine"
                  type="button"
                  class="pdp-follow"
                  :class="{ 'is-on': post.author_is_following }"
                  :disabled="followLoading"
                  @click="toggleFollow"
                >{{ post.author_is_following ? '已关注' : '+ 关注' }}</button>
              </div>

              <h1 class="pdp-title">{{ post.title }}</h1>

              <!-- 元信息：分类标签 + 时间 + 浏览，与资讯详情的「来源标签 + 日期 + 浏览」同一版式 -->
              <div class="pdp-meta">
                <span v-if="post.category" class="pdp-tag">{{ post.category }}</span>
                <span v-if="post.created_at" class="pdp-meta-text">{{ timeLabel(post.created_at) }}</span>
                <span class="pdp-meta-text">{{ post.view_count }} 浏览</span>
              </div>

              <!-- 正文：纯文本，保留用户手打的换行（white-space: pre-wrap） -->
              <div v-if="post.content" class="pdp-content">{{ post.content }}</div>

              <!-- 配图：单图走整幅（保留原始比例），多图走网格；点开可全屏预览。
                   z-index 3000 是必须的：本页根节点 2600，预览层若用组件默认的 2000
                   会被整页盖在下面，点了像没反应。 -->
              <div v-if="post.images?.length" class="pdp-imgs" :data-count="post.images.length">
                <el-image
                  v-for="(img, i) in post.images"
                  :key="img + i"
                  class="pdp-img"
                  :src="img"
                  fit="cover"
                  :preview-src-list="post.images"
                  :initial-index="i"
                  :z-index="3000"
                  preview-teleported
                  loading="lazy"
                />
              </div>
            </article>

            <!-- ③ 评论区：标题口径（共 N 条评论）、头像尺寸、行距全部对齐资讯详情 -->
            <section class="pdp-comments">
              <h2 class="pdp-comments-head">{{ commentCount > 0 ? '共 ' + commentCount + ' 条评论' : '评论' }}</h2>

              <div v-if="commentsLoading" class="pdp-comments-loading">
                <div class="pdp-sk-line w80" />
                <div class="pdp-sk-line w60" />
              </div>
              <div v-else-if="commentsError" class="pdp-comments-state">
                <span>{{ commentsError }}</span>
                <button type="button" class="pdp-mini-btn" @click="loadComments">重试</button>
              </div>
              <p v-else-if="!comments.length" class="pdp-comments-empty">还没有评论，来说点什么吧</p>
              <ul v-else class="pdp-comment-list">
                <li v-for="c in comments" :key="c.id" class="pdp-comment">
                  <el-avatar :size="34" :src="c.author_avatar || undefined" :style="{ background: avatarBg(c.student_id) }">
                    {{ (c.author_name || '同').slice(0, 1) }}
                  </el-avatar>
                  <div class="pdp-comment-main">
                    <div class="pdp-comment-top">
                      <span class="pdp-comment-name">{{ c.author_name || '同学' }}</span>
                      <span class="pdp-comment-time">{{ relativeTime(c.created_at) }}</span>
                      <button
                        v-if="c.student_id === myId"
                        type="button"
                        class="pdp-comment-del"
                        @click="removeComment(c)"
                      >
                        删除
                      </button>
                    </div>
                    <p class="pdp-comment-text">{{ c.content }}</p>
                  </div>
                </li>
              </ul>
            </section>
          </template>
        </div>

        <!-- ④ 底部输入栏：滚动区之外的一行，键盘弹出时用 --kb-offset 顶上去。
             右侧互动列（点赞 / 评论）与资讯详情同构，正文滚到多深都能点。 -->
        <div v-if="post && !error" ref="composerRef" class="pdp-composer">
          <div class="pdp-input-wrap">
            <textarea
              ref="textareaRef"
              v-model="draft"
              class="pdp-textarea"
              rows="1"
              :maxlength="500"
              placeholder="说点什么…"
              @input="autoGrow"
              @focus="autoGrow"
            />
            <span class="pdp-count">{{ draft.length }}/500</span>
          </div>
          <button type="button" class="pdp-send" :disabled="!canSend" @click="submitComment">
            {{ sending ? '发送中' : '发送' }}
          </button>
          <div class="pdp-bar-acts">
            <button
              type="button"
              class="pdp-bar-act"
              :class="{ 'is-on': post.liked }"
              :aria-pressed="post.liked"
              aria-label="点赞"
              @click="handleLike"
            >
              <el-icon :size="19" :class="['pdp-like-icon', { 'is-pop': likePop }]">
                <StarFilled v-if="post.liked" />
                <Star v-else />
              </el-icon>
              <span class="pdp-bar-num">{{ post.like_count }}</span>
            </button>
            <button type="button" class="pdp-bar-act" aria-label="评论" @click="focusComposer">
              <el-icon :size="19"><ChatDotRound /></el-icon>
              <span class="pdp-bar-num">{{ commentCount }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 帖子详情（全屏子页 / 桌面端 760px 居中整页）
 *
 * 从交流社区页签点一条帖子打开；点赞、关注作者、评论、删除都在这里闭环 ——
 * 独立社区页下线后，这些交互不能再依赖那个页面。
 *
 * 版式刻意与 CampusPage 的资讯详情（components/campus/ArticleDetailPage.vue）逐条对齐：
 * 顶栏高度与图标尺寸、标题 21px/1.45、元信息 13px #86909c、正文 16px/1.75、
 * 评论区 34px 头像与 14.5px 正文、底部「输入框 + 计数 + 蓝色发送胶囊 + 右侧互动列」。
 * 两个页面在同一条浏览动线上前后出现，任何一处排版分叉都会被看成「两个 App」。
 * 改动这里的排版请同步 ArticleDetailPage，反之亦然。
 *
 * 用法（父页 v-if 控制挂载，挂载即打开）：
 *   <PostDetailPage v-if="id" :post-id="id" @close="onLeaving" @closed="id = 0" />
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, ChatDotRound, DocumentDelete, Refresh, Share, Star, StarFilled,
} from '@element-plus/icons-vue'
import {
  getPost, toggleLike, getComments, createComment, deleteComment, deletePost,
  type CommunityPost, type CommunityComment,
} from '@/api/community'
import { followUser, unfollowUser } from '@/api/social'
import { actionConfirm } from '@/composables/useActionSheet'
import { useAuthStore } from '@/stores/auth'
import { parseServerTime } from '@/utils/datetime'

const props = defineProps<{ postId: number }>()
const emit = defineEmits<{
  /** 开始退场（.subpage 300ms 右滑）：父页据此立刻让下层归位 */
  (e: 'close'): void
  /** 退场动画播完，父页此时才卸载本组件 */
  (e: 'closed'): void
  (e: 'updated', post: CommunityPost): void
  (e: 'deleted', id: number): void
}>()

const post = ref<CommunityPost | null>(null)
/** 当前已加载的帖子 id：父页换帖时用来判断要不要重载 */
const loadedId = ref(0)
const comments = ref<CommunityComment[]>([])
const loading = ref(false)
const error = ref('')
const commentsLoading = ref(false)
const commentsError = ref('')
const visible = ref(false)
const followLoading = ref(false)
const sending = ref(false)
const draft = ref('')
const myId = ref<number | null>(null)
const likePop = ref(false)

const scrollRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const composerRef = ref<HTMLElement | null>(null)
/** 顶栏投影只在滚动后出现，首屏保持干净（与资讯详情同一个细节） */
const scrolled = ref(false)

/* ============ 键盘偏移（VisualViewport） ============
   与资讯详情同一套：软键盘只缩 visualViewport，fixed 底栏会被直接盖住，
   用布局高度与可视高度之差算出键盘高度写进 --kb-offset。 */
const kbOffset = ref(0)
const rootStyle = computed(() => ({ '--kb-offset': kbOffset.value + 'px' }))
let vv: VisualViewport | null = null
function syncKeyboard() {
  if (!window.visualViewport) { kbOffset.value = 0; return }
  const v = window.visualViewport
  const offset = Math.max(0, window.innerHeight - v.height - v.offsetTop)
  kbOffset.value = offset > 80 ? Math.round(offset) : 0
}

/* ================= 派生数据 ================= */

const isMine = computed(() => !!post.value && post.value.student_id === myId.value)
const commentCount = computed(() => post.value?.comment_count ?? comments.value.length)
const canSend = computed(() => !sending.value && draft.value.trim().length > 0)

function timeLabel(t: string | null): string {
  // 后端时间是「无时区的 UTC」，直接 new Date() 会按本地时间解析、整体差一个时区
  const ms = parseServerTime(t)
  if (Number.isNaN(ms)) return ''
  const d = new Date(ms)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/* ================= 加载 ================= */

async function load() {
  loading.value = true
  error.value = ''
  loadedId.value = props.postId
  try {
    post.value = await getPost(props.postId)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '帖子不存在或已被删除'
    post.value = null
  } finally {
    loading.value = false
  }
  // 详情拿不到时评论没有意义，成功后再拉
  if (!error.value) void loadComments()
}

async function loadComments() {
  if (!props.postId) return
  commentsLoading.value = true
  commentsError.value = ''
  try {
    comments.value = await getComments(props.postId)
    // 以实际列表长度为准回写计数：列表页的 comment_count 来自聚合查询，
    // 与逐条评论偶尔会有偏差，详情页内两个数字必须能对上。
    if (post.value) post.value.comment_count = comments.value.length
  } catch {
    commentsError.value = '评论加载失败'
    comments.value = []
  } finally {
    commentsLoading.value = false
  }
}

async function reload() {
  await load()
}

/* ================= 生命周期 ================= */

function open() {
  post.value = null
  comments.value = []
  commentsError.value = ''
  error.value = ''
  draft.value = ''
  visible.value = true
  void load()
}

function close() {
  if (!visible.value) return
  visible.value = false
  emit('close')
}

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

/**
 * 已打开状态下父页换了帖子（消息里点另一条帖子、或地址栏 ?post= 变化）：
 * 就地重载，不要「先关再开」——那会让整页闪一下白。
 * 父页 v-if 只认 id 非零，组件不会因此卸载重建，所以必须自己认这一跳。
 */
watch(
  () => props.postId,
  (v) => {
    if (!v || v === loadedId.value) return
    post.value = null
    comments.value = []
    commentsError.value = ''
    error.value = ''
    draft.value = ''
    if (scrollRef.value) scrollRef.value.scrollTop = 0
    void load()
  },
)

function onScroll() {
  scrolled.value = (scrollRef.value?.scrollTop || 0) > 4
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && visible.value) close()
}

onMounted(async () => {
  try { myId.value = useAuthStore().user?.id ?? null } catch { myId.value = null }
  window.addEventListener('keydown', onKeydown)
  if (window.visualViewport) {
    vv = window.visualViewport
    vv.addEventListener('resize', syncKeyboard)
    vv.addEventListener('scroll', syncKeyboard)
  }
  open()
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

/* ================= 互动：点赞 =================
   乐观更新：先改本地状态再发请求，失败按快照回滚（与资讯详情同一套手感）。 */
async function handleLike() {
  const p = post.value
  if (!p) return
  const snapshot = { liked: p.liked, count: p.like_count }
  const next = !snapshot.liked
  p.liked = next
  p.like_count = Math.max(0, snapshot.count + (next ? 1 : -1))
  likePop.value = true
  emit('updated', p)
  try {
    const res = await toggleLike(p.id)
    p.liked = res.liked
    p.like_count = res.count
  } catch {
    p.liked = snapshot.liked
    p.like_count = snapshot.count
    ElMessage.error('操作失败，请稍后再试')
  } finally {
    emit('updated', p)
    // 320ms 后清标记，保证下次点击还能重播弹跳动画
    window.setTimeout(() => { likePop.value = false }, 320)
  }
}

/* ================= 互动：关注作者 ================= */

async function toggleFollow() {
  const p = post.value
  if (!p || followLoading.value) return
  followLoading.value = true
  try {
    const res = p.author_is_following
      ? await unfollowUser(p.student_id)
      : await followUser(p.student_id)
    p.author_is_following = res.is_following
    ElMessage.success(res.is_following ? `已关注 ${p.author_name || '该作者'}` : '已取消关注')
    emit('updated', p)
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  } finally {
    followLoading.value = false
  }
}

/* ================= 互动：评论 ================= */

function focusComposer() {
  composerRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  nextTick(() => textareaRef.value?.focus())
}

/** textarea 自适应 1~4 行：超出后内部滚动，避免输入框把正文顶出屏幕 */
function autoGrow() {
  const el = textareaRef.value
  if (!el) return
  const lh = 22
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, lh * 4 + 20) + 'px'
}

async function submitComment() {
  const p = post.value
  if (!p || sending.value) return
  const text = draft.value.trim()
  if (!text) return
  sending.value = true
  try {
    const created = await createComment(p.id, text)
    comments.value.unshift(created)
    p.comment_count = comments.value.length
    draft.value = ''
    await nextTick()
    autoGrow()
    emit('updated', p)
    ElMessage.success('评论成功')
  } catch {
    ElMessage.error('评论失败，请稍后再试')
  } finally {
    sending.value = false
  }
}

async function removeComment(c: CommunityComment) {
  const p = post.value
  if (!p) return
  if (!(await actionConfirm('确定删除这条评论吗？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  try {
    await deleteComment(c.id)
    comments.value = comments.value.filter(x => x.id !== c.id)
    p.comment_count = comments.value.length
    emit('updated', p)
  } catch {
    ElMessage.error('删除失败')
  }
}

/* ================= 删除帖子 ================= */

async function removePost() {
  const p = post.value
  if (!p) return
  if (!(await actionConfirm('确定删除这篇帖子吗？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  try {
    await deletePost(p.id)
    ElMessage.success('已删除')
    emit('deleted', p.id)
    close()
  } catch {
    ElMessage.error('删除失败')
  }
}

/* ================= 分享 =================
   与资讯详情同一策略：优先系统分享面板，不支持（桌面 / http 内网）时降级复制链接。 */
const shareUrl = computed(() =>
  post.value ? `${window.location.origin}/student/campus?tab=community&post=${post.value.id}` : '',
)

async function onShare() {
  const url = shareUrl.value
  if (!url) return
  const data: ShareData = {
    title: post.value?.title || '校园社区帖子',
    text: post.value?.title || '',
    url,
  }
  const canShare = typeof navigator.share === 'function' && (!navigator.canShare || navigator.canShare(data))
  if (canShare) {
    try {
      await navigator.share(data)
      return
    } catch (e: any) {
      if (e?.name === 'AbortError') return
    }
  }
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(url)
    else fallbackCopy(url)
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

/* ================= 展示工具 ================= */

/** 头像底色：按 student_id 取模落到一组柔和色上，同一个人每次进来颜色一致 */
const AVATAR_COLORS = ['#dbeafe', '#e0e7ff', '#fce7f3', '#dcfce7', '#fef3c7', '#fee2e2', '#ede9fe', '#cffafe']
function avatarBg(id: number | null | undefined) {
  const idx = Math.abs(Number(id) || 0) % AVATAR_COLORS.length
  return AVATAR_COLORS[idx]
}

/** 相对时间（评论用）：刚刚 / N 分钟前 / HH:mm / MM-DD，与资讯详情评论区口径一致 */
function relativeTime(iso: string | null): string {
  const t = parseServerTime(iso)
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
</script>

<style scoped>
/* ================= 根容器 =================
   与 .adp-root 一致：fixed inset:0 的整页覆盖层，flex 纵向三段（顶栏 / 滚动区 / 输入栏）。
   z-index 2600 与资讯详情同层：压过改密提醒横幅（1900）、底部胶囊（1000）与顶栏（100），
   同时低于 Element Plus 的图片预览层（本页给 el-image 传了 z-index 3000）。 */
.pdp-root {
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
.pdp-head {
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
.pdp-head.is-scrolled { box-shadow: 0 2px 10px rgba(29, 33, 41, 0.06); }

.pdp-icon-btn {
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
.pdp-icon-btn:active { background: #f2f3f5; opacity: 0.62; }

.pdp-head-title { flex: 1; min-width: 0; text-align: center; }
.pdp-head-main {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 右侧：删除（仅作者）+ 分享。删除用文字而非图标 —— 破坏性动作给图标容易被误读成「更多」 */
.pdp-head-acts { flex-shrink: 0; display: flex; align-items: center; gap: 2px; }
.pdp-del-btn {
  height: 40px;
  padding: 0 6px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #f53f3f;
  font-size: 13.5px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.pdp-del-btn:active { background: #fff1f0; }

/* ================= 滚动区 ================= */
.pdp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  background: #fff;
  padding-bottom: 8px;
}
.pdp-meta-text { font-variant-numeric: tabular-nums; }

/* ================= 正文 ================= */
.pdp-article { padding: 16px 16px 4px; }

/* 作者行：帖子独有的信息，但视觉上只用一组极轻的分隔，不抢标题 */
.pdp-author {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 14px;
  margin-bottom: 16px;
  border-bottom: 1px solid #f2f3f5;
}
.pdp-author-main { flex: 1; min-width: 0; }
.pdp-author-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pdp-follow {
  flex-shrink: 0;
  height: 28px;
  padding: 0 12px;
  border: 1px solid #2563eb;
  border-radius: 14px;
  background: #2563eb;
  color: #fff;
  font-size: 12.5px;
  line-height: 1;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.14s ease;
}
.pdp-follow.is-on { background: #fff; border-color: #e5e6eb; color: #86909c; }
.pdp-follow:active { opacity: 0.7; }
.pdp-follow:disabled { opacity: 0.6; cursor: default; }

.pdp-title {
  margin: 0 0 10px;
  font-size: 21px;
  font-weight: 700;
  line-height: 1.45;
  color: #1d2129;
  word-break: break-word;
}

.pdp-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #86909c;
}
.pdp-tag {
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

.pdp-content {
  font-size: 16px;
  /* 1.75 行高：与资讯正文同一档，中文长段落在手机上最舒服的密度 */
  line-height: 1.75;
  color: #1f2329;
  letter-spacing: 0.01em;
  /* 用户手打的换行必须原样呈现 */
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* ---------- 配图 ----------
   单图整幅（保留原始比例，截图类配图不会被裁掉内容）；
   2 图两列、3 图以上三列，与信息流缩略图的比例语言一致。 */
.pdp-imgs { display: grid; gap: 6px; margin-top: 14px; }
.pdp-imgs[data-count='1'] { grid-template-columns: 1fr; }
.pdp-imgs[data-count='2'] { grid-template-columns: repeat(2, 1fr); }
.pdp-imgs:not([data-count='1']):not([data-count='2']) { grid-template-columns: repeat(3, 1fr); }
.pdp-img {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  overflow: hidden;
  background: #f4f5f7;
}
.pdp-imgs[data-count='1'] .pdp-img { aspect-ratio: auto; }
.pdp-imgs[data-count='1'] :deep(.el-image__inner) { height: auto; object-fit: contain; }
.pdp-imgs[data-count='2'] .pdp-img { aspect-ratio: 4 / 3; }

/* ================= 骨架屏 ================= */
.pdp-skeleton { padding: 22px 16px; display: flex; flex-direction: column; gap: 14px; }
.pdp-sk-gap { height: 6px; }
.pdp-sk-line {
  height: 13px;
  border-radius: 7px;
  background: linear-gradient(90deg, #eef0f3, #f6f7f9, #eef0f3);
  background-size: 200% 100%;
  animation: pdp-shimmer 1.2s ease-in-out infinite;
}
.pdp-sk-line.w40 { width: 40%; } .pdp-sk-line.w60 { width: 60%; } .pdp-sk-line.w80 { width: 80%; }
.pdp-sk-line.w90 { width: 90%; } .pdp-sk-line.w95 { width: 95%; } .pdp-sk-line.w100 { width: 100%; }
@keyframes pdp-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ================= 错误态 ================= */
.pdp-state {
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
.pdp-state-icon { color: #c9cdd4; }
.pdp-state-title { margin: 4px 0 0; font-size: 15px; font-weight: 600; color: #1d2129; }
.pdp-state-desc { margin: 0; font-size: 13px; line-height: 1.6; color: #86909c; max-width: 340px; }
.pdp-state-btns { display: flex; gap: 10px; margin-top: 12px; }

.pdp-btn {
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
.pdp-btn:active { opacity: 0.62; }
.pdp-btn.primary { background: #2563eb; border-color: transparent; color: #fff; }

/* ================= 评论区 ================= */
.pdp-comments { padding: 4px 16px 16px; }
.pdp-comments-head {
  margin: 16px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}
.pdp-comments-loading { display: flex; flex-direction: column; gap: 10px; padding: 8px 0 16px; }
.pdp-comments-state,
.pdp-comments-empty {
  margin: 0;
  padding: 28px 0;
  text-align: center;
  font-size: 13.5px;
  color: #b2b2b2;
}
.pdp-comments-state { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.pdp-mini-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 16px;
  background: #fff;
  color: #4e5969;
  font-size: 13px;
  cursor: pointer;
}

.pdp-comment-list { list-style: none; margin: 0; padding: 0; }
.pdp-comment {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f7f8fa;
}
.pdp-comment:last-child { border-bottom: 0; }
.pdp-comment-main { flex: 1; min-width: 0; }
.pdp-comment-top { display: flex; align-items: center; gap: 8px; }
.pdp-comment-name {
  font-size: 13.5px;
  font-weight: 500;
  color: #4e5969;
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pdp-comment-time { font-size: 12px; color: #b2b2b2; }
.pdp-comment-del {
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
.pdp-comment-del:active { background: #f2f3f5; }
.pdp-comment-text {
  margin: 4px 0 0;
  font-size: 14.5px;
  line-height: 1.65;
  color: #26282c;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ================= 底部输入栏 =================
   固定在滚动区之外（.pdp-root 的最后一个 flex 子项）——
   放滚动区里用 sticky 在部分浏览器会失效并盖住正文（资讯详情踩过），
   flex 行是结构性保证：不参与滚动，永远不可能盖住内容。 */
.pdp-composer {
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
.pdp-input-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  background: #f7f8fa;
  border-radius: 13px;
  padding: 8px 10px 16px;
}
.pdp-textarea {
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
.pdp-textarea::placeholder { color: #b2b2b2; }
.pdp-count {
  position: absolute;
  right: 10px;
  bottom: 2px;
  font-size: 11px;
  color: #b2b2b2;
  font-variant-numeric: tabular-nums;
}
.pdp-send {
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
.pdp-send:active:not(:disabled) { opacity: 0.72; }
.pdp-send:disabled { background: #c9d4e8; cursor: not-allowed; }

/* 发送右侧的互动区：点赞 / 评论数，竖向「图标 + 数字」，常驻屏幕底部 */
.pdp-bar-acts {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 4px;
  padding-bottom: 4px;
}
.pdp-bar-act {
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
.pdp-bar-act:active { transform: scale(0.92); }
.pdp-bar-act.is-on { color: #2563eb; }
.pdp-bar-num { font-size: 11px; font-variant-numeric: tabular-nums; }

.pdp-like-icon.is-pop { animation: pdp-like-pop 0.32s ease; }
@keyframes pdp-like-pop {
  0% { transform: scale(1); }
  35% { transform: scale(1.35); }
  100% { transform: scale(1); }
}

/* ================= 桌面端：居中限宽 760px 的整页 =================
   与资讯详情完全一致 —— 不做「带遮罩的居中弹窗」。
   两者在桌面端是同一条动线上的相邻两页，一个是弹窗一个是整页会显得割裂。 */
@media (min-width: 768px) {
  .pdp-root { align-items: center; }
  .pdp-head,
  .pdp-scroll,
  .pdp-composer { width: 100%; max-width: 760px; }
}

@media (prefers-reduced-motion: reduce) {
  .pdp-root { animation: none !important; }
  .pdp-like-icon.is-pop { animation: none !important; }
}
</style>
