<template>
  <Teleport to="body">
    <!-- 全屏帖子详情：移动端右滑进入；桌面端 760px 居中整页。
         退场分两步：close = 开始滑出（父页下层立刻归位），closed = 动画播完（父页卸载）。 -->
    <Transition name="subpage" :duration="320" @after-leave="onAfterLeave">
      <div
        v-if="visible"
        class="pd-root"
        role="dialog"
        aria-modal="true"
        aria-label="帖子详情"
        :style="rootStyle"
      >
        <header class="pd-head" :class="{ 'is-scrolled': scrolled }">
          <button type="button" class="pd-icon-btn" aria-label="返回" @click="close">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <div class="pd-head-title">帖子详情</div>
          <button
            v-if="isMine"
            type="button"
            class="pd-head-del"
            :disabled="deleting"
            @click="removePost"
          >删除</button>
          <span v-else class="pd-head-side" />
        </header>

        <div ref="scrollRef" class="pd-scroll" @scroll.passive="onScroll">
          <div v-if="loading" class="pd-skeleton">
            <div class="sk-line w60" />
            <div class="sk-line w35" />
            <div class="sk-gap" />
            <div class="sk-line w100" />
            <div class="sk-line w95" />
            <div class="sk-line w85" />
          </div>

          <div v-else-if="error" class="pd-state">
            <el-icon :size="42" class="pd-state-icon"><DocumentDelete /></el-icon>
            <p class="pd-state-title">帖子暂时打不开</p>
            <p class="pd-state-desc">{{ error }}</p>
            <button type="button" class="pd-btn" @click="reload">
              <el-icon :size="15"><Refresh /></el-icon> 重试
            </button>
          </div>

          <template v-else-if="post">
            <article class="pd-article">
              <div class="pd-author-row">
                <el-avatar
                  :size="38"
                  :src="post.author_avatar || undefined"
                  class="pd-avatar"
                  @click="openUserHomepage(post.student_id)"
                >
                  {{ (post.author_name || '学').slice(0, 1) }}
                </el-avatar>
                <div class="pd-author-main">
                  <span class="pd-author-name" @click="openUserHomepage(post.student_id)">
                    {{ post.author_name || '同学' }}
                  </span>
                  <span class="pd-author-meta">{{ relativeTime(post.created_at) }} · {{ post.category }}</span>
                </div>
                <button
                  v-if="post.student_id !== myId"
                  type="button"
                  class="pd-follow"
                  :class="{ 'is-following': post.author_is_following }"
                  :disabled="followLoading"
                  @click="toggleFollow"
                >{{ post.author_is_following ? '已关注' : '+ 关注' }}</button>
              </div>

              <h1 class="pd-title">{{ post.title }}</h1>
              <div class="pd-content">{{ post.content }}</div>

              <div v-if="images.length" class="pd-imgs" :class="{ 'is-single': images.length === 1 }">
                <el-image
                  v-for="(img, i) in images"
                  :key="img + i"
                  :src="img"
                  :preview-src-list="images"
                  :initial-index="i"
                  preview-teleported
                  fit="cover"
                  class="pd-img"
                />
              </div>

              <div class="pd-stats">
                <span class="pd-stat"><el-icon :size="14"><View /></el-icon>{{ post.view_count }} 浏览</span>
                <span class="pd-stat"><el-icon :size="14"><ChatDotRound /></el-icon>{{ commentTotal }} 评论</span>
                <span class="pd-stat" :class="{ 'is-liked': post.liked }">
                  <el-icon :size="14"><StarFilled v-if="post.liked" /><Star v-else /></el-icon>{{ post.like_count }} 点赞
                </span>
              </div>

              <button
                v-if="post.student_id === myId"
                type="button"
                class="pd-del-post"
                :disabled="deleting"
                @click="removePost"
              >删除这篇帖子</button>
            </article>

            <section class="pd-comments">
              <h2 class="pd-comments-head">{{ commentTotal > 0 ? `共 ${commentTotal} 条评论` : '评论' }}</h2>

              <div v-if="commentsLoading" class="pd-comments-hint">评论加载中…</div>
              <div v-else-if="commentsError" class="pd-comments-hint is-error">
                <span>{{ commentsError }}</span>
                <button type="button" class="pd-mini-btn" @click="loadComments">重试</button>
              </div>
              <p v-else-if="!comments.length" class="pd-comments-empty">还没有评论，来抢沙发吧</p>
              <ul v-else class="pd-comment-list">
                <li v-for="c in comments" :key="c.id" class="pd-comment">
                  <el-avatar
                    :size="30"
                    :src="c.author_avatar || undefined"
                    class="pd-comment-avatar"
                    @click="openUserHomepage(c.student_id)"
                  >
                    {{ (c.author_name || '学').slice(0, 1) }}
                  </el-avatar>
                  <div class="pd-comment-main">
                    <div class="pd-comment-top">
                      <span class="pd-comment-name" @click="openUserHomepage(c.student_id)">
                        {{ c.author_name || '同学' }}
                      </span>
                      <span class="pd-comment-time">{{ relativeTime(c.created_at) }}</span>
                      <button
                        v-if="c.student_id === myId"
                        type="button"
                        class="pd-comment-del"
                        :disabled="deletingCommentId === c.id"
                        @click="removeComment(c)"
                      >删除</button>
                    </div>
                    <p class="pd-comment-text">{{ c.content }}</p>
                  </div>
                </li>
              </ul>
            </section>
          </template>
        </div>

        <div v-if="post && !error" ref="composerRef" class="pd-composer">
          <div class="pd-input-wrap">
            <textarea
              ref="textareaRef"
              v-model="draft"
              class="pd-textarea"
              rows="1"
              :maxlength="500"
              placeholder="友善评论，专业交流…"
              @input="autoGrow"
              @focus="autoGrow"
              @keydown.enter.exact="onEnter"
            />
            <span class="pd-count">{{ draft.length }}/500</span>
          </div>
          <button type="button" class="pd-send" :disabled="!canSend" @click="submitComment">
            {{ sending ? '发送中' : '发送' }}
          </button>
          <button
            type="button"
            class="pd-bar-act"
            :class="{ 'is-on': post.liked }"
            aria-label="点赞"
            :aria-pressed="post.liked"
            @click="onLike"
          >
            <el-icon :size="19"><StarFilled v-if="post.liked" /><Star v-else /></el-icon>
            <span class="pd-bar-num">{{ post.like_count }}</span>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 交流社区「帖子详情」子页
 *
 * 从旧独立社区页的详情抽屉抽出：移动端整页右滑进入，桌面端 760px 居中整页。
 * 正文 + 配图 + 点赞 / 关注 / 评论 / 删除都在这里；列表数据由父页
 * （CampusPage → CommunityFeed）负责，互动后通过 updated / deleted 通知刷新。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, ChatDotRound, DocumentDelete, Refresh, Star, StarFilled, View,
} from '@element-plus/icons-vue'
import {
  createComment,
  deleteComment,
  deletePost,
  getComments,
  getPost,
  toggleLike,
  type CommunityComment,
  type CommunityPost,
} from '@/api/community'
import { followUser, unfollowUser } from '@/api/social'
import { actionConfirm } from '@/composables/useActionSheet'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { useAuthStore } from '@/stores/auth'
import { promptLogin } from '@/utils/loginGate'

const props = defineProps<{ postId: number }>()

const emit = defineEmits<{
  /** 开始退场：父页收到后让下层归位 */
  (e: 'close'): void
  /** 退场动画播完：父页收到后才卸载本组件 */
  (e: 'closed'): void
  /** 点赞 / 评论 / 关注等计数变化，父页据此刷新帖子流 */
  (e: 'updated'): void
  /** 帖子已被删除 */
  (e: 'deleted'): void
}>()

const visible = ref(false)
const loading = ref(false)
const error = ref('')
const post = ref<CommunityPost | null>(null)
const comments = ref<CommunityComment[]>([])
const commentsLoading = ref(false)
const commentsError = ref('')
const draft = ref('')
const sending = ref(false)
const deleting = ref(false)
const deletingCommentId = ref<number | null>(null)
const followLoading = ref(false)
const scrolled = ref(false)

const scrollRef = ref<HTMLElement | null>(null)
const composerRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const auth = useAuthStore()
const myId = computed(() => auth.user?.id ?? null)
const isMine = computed(() => !!post.value && myId.value === post.value.student_id)
const images = computed(() => (post.value && Array.isArray(post.value.images) ? post.value.images : []))
const commentTotal = computed(() => post.value?.comment_count ?? comments.value.length)
const canSend = computed(() => !sending.value && draft.value.trim().length > 0)

/* ---------- 键盘偏移：与资讯详情同一套 VisualViewport 方案 ---------- */
const kbOffset = ref(0)
const rootStyle = computed(() => ({ '--kb-offset': `${kbOffset.value}px` }))
let vv: VisualViewport | null = null

function syncKeyboard() {
  if (!window.visualViewport) {
    kbOffset.value = 0
    return
  }
  const v = window.visualViewport
  const offset = Math.max(0, window.innerHeight - v.height - v.offsetTop)
  kbOffset.value = offset > 80 ? Math.round(offset) : 0
}

/* ---------- 数据 ---------- */
async function loadPost() {
  loading.value = true
  error.value = ''
  try {
    post.value = await getPost(props.postId)
    draft.value = ''
  } catch (e: any) {
    post.value = null
    error.value = e?.response?.data?.detail || '帖子加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
  if (!error.value) void loadComments()
}

async function loadComments() {
  commentsLoading.value = true
  commentsError.value = ''
  try {
    comments.value = await getComments(props.postId)
    if (post.value) post.value.comment_count = comments.value.length
  } catch {
    comments.value = []
    commentsError.value = '评论加载失败'
  } finally {
    commentsLoading.value = false
  }
}

async function reload() {
  await loadPost()
}

function emitUpdated() {
  emit('updated')
}

/* ---------- 互动 ---------- */
async function onLike() {
  if (!post.value) return
  if (!myId.value) {
    void promptLogin('点赞帖子')
    return
  }
  const p = post.value
  const snapshot = { liked: p.liked, like_count: p.like_count }
  const nextLiked = !snapshot.liked
  p.liked = nextLiked
  p.like_count = Math.max(0, snapshot.like_count + (nextLiked ? 1 : -1))
  emitUpdated()
  try {
    const res = await toggleLike(p.id)
    p.liked = res.liked
    p.like_count = res.count
    emitUpdated()
  } catch (e: any) {
    p.liked = snapshot.liked
    p.like_count = snapshot.like_count
    emitUpdated()
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '点赞失败，请重试')
  }
}

async function toggleFollow() {
  if (!post.value) return
  if (!myId.value) {
    void promptLogin('关注作者')
    return
  }
  if (followLoading.value) return
  followLoading.value = true
  const p = post.value
  try {
    const res = p.author_is_following
      ? await unfollowUser(p.student_id)
      : await followUser(p.student_id)
    p.author_is_following = res.is_following
    emitUpdated()
    ElMessage.success(res.is_following ? `已关注 ${p.author_name || '该作者'}` : '已取消关注')
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  } finally {
    followLoading.value = false
  }
}

async function submitComment() {
  if (!post.value) return
  if (!myId.value) {
    void promptLogin('评论帖子')
    return
  }
  const content = draft.value.trim()
  if (!content || sending.value) return
  sending.value = true
  try {
    const created = await createComment(post.value.id, content)
    comments.value.push(created)
    post.value.comment_count = comments.value.length
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

async function removeComment(c: CommunityComment) {
  if (deletingCommentId.value !== null) return
  if (!(await actionConfirm('确定删除这条评论吗？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  deletingCommentId.value = c.id
  try {
    await deleteComment(c.id)
    comments.value = comments.value.filter((x) => x.id !== c.id)
    if (post.value) post.value.comment_count = comments.value.length
    emitUpdated()
  } catch (e: any) {
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '删除失败，请重试')
  } finally {
    deletingCommentId.value = null
  }
}

async function removePost() {
  if (!post.value || deleting.value) return
  if (!(await actionConfirm('确定删除这篇帖子吗？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  deleting.value = true
  try {
    await deletePost(post.value.id)
    ElMessage.success('已删除')
    emit('deleted')
    close()
  } catch (e: any) {
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '删除失败，请重试')
  } finally {
    deleting.value = false
  }
}

/* ---------- 展示工具 ---------- */
function relativeTime(iso: string | null): string {
  if (!iso) return ''
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  const d = new Date(t)
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  if (d.toDateString() === now.toDateString()) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.getFullYear() === now.getFullYear()) return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function onScroll() {
  scrolled.value = (scrollRef.value?.scrollTop || 0) > 4
}

/** Enter 发送；中文输入法选词时的 Enter 不能当成发送 */
function onEnter(ev: KeyboardEvent) {
  if (ev.isComposing) return
  ev.preventDefault()
  void submitComment()
}

function autoGrow() {
  const el = textareaRef.value
  if (!el) return
  const lh = 22
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, lh * 4 + 20)}px`
}

function focusComposer() {
  composerRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  void nextTick(() => textareaRef.value?.focus())
}

/* ---------- 开关 ---------- */
function close() {
  if (!visible.value) return
  visible.value = false
  emit('close')
}

function onAfterLeave() {
  document.body.style.overflow = ''
  emit('closed')
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && visible.value) close()
}

watch(
  () => props.postId,
  (id) => {
    if (!id) return
    if (visible.value && id !== post.value?.id) {
      post.value = null
      comments.value = []
      void loadPost()
    }
  },
)

watch(visible, async (v) => {
  await nextTick()
  if (v) {
    document.body.style.overflow = 'hidden'
    scrolled.value = false
    syncKeyboard()
  } else {
    // 解锁放到退场动画结束（onAfterLeave），避免背景在滑出的 300ms 里跟着滚动
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
  document.body.style.overflow = 'hidden'
  visible.value = true
  void loadPost()
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

defineExpose({ reload, close, focusComposer })
</script>

<style scoped>
/* ---------- 根容器 ---------- */
.pd-root {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  flex-direction: column;
  background: #fff;
  color: #1d2129;
  overflow: hidden;
  -webkit-tap-highlight-color: transparent;
}

/* ---------- 顶栏 ---------- */
.pd-head {
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
.pd-head.is-scrolled { box-shadow: 0 2px 10px rgba(29, 33, 41, 0.06); }
.pd-icon-btn {
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
}
.pd-icon-btn:active { background: #f2f3f5; opacity: 0.62; }
.pd-head-title {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pd-head-side { width: 40px; flex-shrink: 0; }
.pd-head-del {
  flex-shrink: 0;
  min-width: 40px;
  height: 40px;
  padding: 0 4px;
  border: none;
  background: transparent;
  color: #86909c;
  font-size: 13px;
  cursor: pointer;
}
.pd-head-del:disabled { opacity: 0.5; }

/* ---------- 滚动区 ---------- */
.pd-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  background: #fff;
  padding-bottom: 8px;
}

/* ---------- 正文 ---------- */
.pd-article { padding: 16px 16px 4px; }
.pd-author-row { display: flex; align-items: center; gap: 10px; }
.pd-avatar { flex-shrink: 0; cursor: pointer; background: #f2f3f5; color: #4e5969; }
.pd-author-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.pd-author-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  cursor: pointer;
}
.pd-author-meta { font-size: 11.5px; color: #86909c; }
.pd-follow {
  flex-shrink: 0;
  height: 30px;
  padding: 0 12px;
  border: 1px solid #1d2129;
  border-radius: 15px;
  background: #fff;
  color: #1d2129;
  font-size: 12px;
  cursor: pointer;
}
.pd-follow.is-following { border-color: #e5e6eb; color: #86909c; }
.pd-follow:disabled { opacity: 0.5; }

.pd-title {
  margin: 16px 0 0;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.45;
  color: #1d2129;
  word-break: break-word;
}
.pd-content {
  margin-top: 10px;
  font-size: 15px;
  line-height: 1.75;
  color: #26282c;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.pd-imgs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 12px;
}
.pd-imgs.is-single { grid-template-columns: minmax(0, 1fr); }
.pd-img {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  overflow: hidden;
  background: #f2f3f5;
  cursor: pointer;
}
.pd-imgs.is-single .pd-img { aspect-ratio: 16 / 10; }

.pd-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f0f0f0;
}
.pd-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #86909c;
  font-variant-numeric: tabular-nums;
}
.pd-stat.is-liked { color: #1d2129; }
.pd-del-post {
  width: 100%;
  height: 38px;
  margin-top: 12px;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  background: #fff;
  color: #86909c;
  font-size: 13px;
  cursor: pointer;
}
.pd-del-post:disabled { opacity: 0.5; }

/* ---------- 评论 ---------- */
.pd-comments { padding: 4px 16px 16px; }
.pd-comments-head {
  margin: 16px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}
.pd-comments-hint,
.pd-comments-empty {
  margin: 0;
  padding: 26px 0;
  text-align: center;
  font-size: 13px;
  color: #b2b2b2;
}
.pd-comments-hint.is-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #86909c;
}
.pd-comment-list { list-style: none; margin: 0; padding: 0; }
.pd-comment {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f7f8fa;
}
.pd-comment:last-child { border-bottom: 0; }
.pd-comment-avatar { flex-shrink: 0; cursor: pointer; background: #f2f3f5; color: #4e5969; }
.pd-comment-main { flex: 1; min-width: 0; }
.pd-comment-top { display: flex; align-items: center; gap: 8px; }
.pd-comment-name {
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
  color: #4e5969;
  cursor: pointer;
}
.pd-comment-time { font-size: 11.5px; color: #b2b2b2; }
.pd-comment-del {
  margin-left: auto;
  min-width: 40px;
  height: 28px;
  padding: 0 6px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #86909c;
  font-size: 12px;
  cursor: pointer;
}
.pd-comment-del:active { background: #f2f3f5; }
.pd-comment-del:disabled { opacity: 0.5; }
.pd-comment-text {
  margin: 4px 0 0;
  font-size: 14px;
  line-height: 1.65;
  color: #26282c;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---------- 底部输入栏 ---------- */
.pd-composer {
  flex-shrink: 0;
  position: relative;
  bottom: var(--kb-offset, 0px);
  z-index: 2;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
  background: #fff;
  border-top: 1px solid #f0f0f0;
  transition: bottom 0.16s ease;
}
.pd-input-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  padding: 8px 10px 16px;
  border-radius: 13px;
  background: #f7f8fa;
}
.pd-textarea {
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
.pd-textarea::placeholder { color: #b2b2b2; }
.pd-count {
  position: absolute;
  right: 10px;
  bottom: 2px;
  font-size: 10.5px;
  color: #b2b2b2;
  font-variant-numeric: tabular-nums;
}
.pd-send {
  flex-shrink: 0;
  height: 40px;
  min-width: 58px;
  padding: 0 14px;
  border: none;
  border-radius: 20px;
  background: #1d2129;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.pd-send:active:not(:disabled) { opacity: 0.72; }
.pd-send:disabled { background: #c9cdd4; cursor: not-allowed; }
.pd-bar-act {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  min-width: 28px;
  padding: 6px 2px;
  border: none;
  background: transparent;
  color: #86909c;
  line-height: 1;
  cursor: pointer;
}
.pd-bar-act.is-on { color: #1d2129; }
.pd-bar-num { font-size: 10.5px; font-variant-numeric: tabular-nums; }

/* ---------- 状态 ---------- */
.pd-skeleton { padding: 22px 16px; display: flex; flex-direction: column; gap: 14px; }
.sk-gap { height: 6px; }
.sk-line {
  height: 13px;
  border-radius: 7px;
  background: linear-gradient(90deg, #eef0f3, #f6f7f9, #eef0f3);
  background-size: 200% 100%;
  animation: pd-shimmer 1.2s ease-in-out infinite;
}
.sk-line.w35 { width: 35%; }
.sk-line.w60 { width: 60%; }
.sk-line.w85 { width: 85%; }
.sk-line.w95 { width: 95%; }
.sk-line.w100 { width: 100%; }
@keyframes pd-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.pd-state {
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
.pd-state-icon { color: #c9cdd4; }
.pd-state-title { margin: 4px 0 0; font-size: 15px; font-weight: 600; color: #1d2129; }
.pd-state-desc { margin: 0; font-size: 13px; line-height: 1.6; color: #86909c; max-width: 340px; }
.pd-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 38px;
  margin-top: 8px;
  padding: 0 16px;
  border: 1px solid #e5e6eb;
  border-radius: 19px;
  background: #fff;
  color: #1d2129;
  font-size: 13.5px;
  cursor: pointer;
}
.pd-mini-btn {
  height: 30px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 15px;
  background: #fff;
  color: #4e5969;
  font-size: 12.5px;
  cursor: pointer;
}

/* ---------- 桌面端：760px 居中整页 ---------- */
@media (min-width: 768px) {
  .pd-root { align-items: center; background: #f2f3f5; }
  .pd-head,
  .pd-scroll,
  .pd-composer { width: 100%; max-width: 760px; }
}

@media (prefers-reduced-motion: reduce) {
  .pd-root { animation: none !important; }
}
</style>
