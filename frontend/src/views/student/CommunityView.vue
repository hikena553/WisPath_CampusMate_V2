<template>
  <div class="community-page">
    <!-- 顶部标题 -->
    <div class="community-header">
      <div>
        <h2 class="community-title">交流社区</h2>
        <p class="community-sub">技术 · 提问 · 分享 · 求助</p>
      </div>
      <el-button type="primary" round @click="openPostDialog()">
        <el-icon style="margin-right:4px"><Plus /></el-icon>发帖
      </el-button>
    </div>

    <!-- 热帖推荐 -->
    <div v-if="hotPosts.length" class="card hot-card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">🔥 热帖推荐</span>
        <span class="head-sub">按学习方向与浏览热度精选</span>
      </div>
      <div v-for="h in hotPosts" :key="h.id" class="hot-item" @click="openDetail(h.id)">
        <el-icon :size="13" style="color:#e6a23c;flex-shrink:0"><StarFilled /></el-icon>
        <span class="hot-title">{{ h.title }}</span>
        <span class="hot-count">{{ h.like_count }} 赞</span>
      </div>
    </div>

    <!-- 帖子列表 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">帖子广场</span>
      </div>
      <div class="filter-row">
        <el-tag
          v-for="f in categoryFilters"
          :key="f.value"
          :type="filters.category === f.value ? 'primary' : 'info'"
          :effect="filters.category === f.value ? 'dark' : 'plain'"
          class="filter-tag" round
          @click="switchCategory(f.value)"
        >{{ f.label }}</el-tag>
      </div>
      <div class="search-row">
        <el-input v-model="filters.q" placeholder="搜索帖子关键词" clearable class="search-input" @keyup.enter="searchPosts" @clear="searchPosts">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filters.sort" style="width:110px" @change="searchPosts">
          <el-option label="最新" value="new" />
          <el-option label="最热" value="hot" />
        </el-select>
        <el-button type="primary" @click="searchPosts">搜索</el-button>
      </div>
      <div v-if="!posts.length" class="empty-tip">暂无帖子，来发布第一条吧</div>
      <div v-for="p in posts" :key="p.id" class="post-card" @click="openDetail(p.id)">
        <div class="post-head">
          <el-avatar :size="28" :src="p.author_avatar || undefined" class="post-avatar">
            {{ (p.author_name || '学').slice(0, 1) }}
          </el-avatar>
          <span class="post-author">{{ p.author_name || '同学' }}</span>
          <el-tag size="small" effect="plain" round class="post-cat">{{ p.category }}</el-tag>
          <span class="post-time">{{ formatTime(p.created_at) }}</span>
        </div>
        <div class="post-title">{{ p.title }}</div>
        <div v-if="p.content" class="post-content">{{ p.content }}</div>
        <div class="post-stats">
          <span class="stat"><el-icon :size="14"><View /></el-icon>{{ p.view_count }}</span>
          <span class="stat"><el-icon :size="14"><ChatLineRound /></el-icon>{{ p.comment_count }}</span>
          <span class="stat" :class="{ 'stat-liked': p.liked }">
            <el-icon :size="14"><Star /></el-icon>{{ p.like_count }}
          </span>
        </div>
      </div>
      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          background
          small
          @current-change="loadPosts"
        />
      </div>
    </div>

    <!-- 发帖弹窗 -->
    <el-dialog v-model="postDialogVisible" title="发布帖子" width="540px" :close-on-click-modal="false">
      <el-form label-width="64px">
        <el-form-item label="分类" required>
          <el-radio-group v-model="postForm.category">
            <el-radio v-for="c in COMMUNITY_CATEGORIES" :key="c" :value="c">{{ c }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="postForm.title" placeholder="一句话说清主题" maxlength="60" show-word-limit />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="postForm.content" type="textarea" :rows="6" placeholder="详细描述你的问题或分享内容（支持多行）" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="postDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPost" @click="savePost">发布</el-button>
      </template>
    </el-dialog>

    <!-- 帖子详情弹窗 -->
    <el-drawer v-model="detailVisible" size="92%" :with-header="false" class="post-drawer">
      <div class="detail-box">
        <div class="detail-top">
          <div class="detail-head">
            <el-avatar :size="34" :src="detailPost?.author_avatar || undefined">
              {{ (detailPost?.author_name || '学').slice(0, 1) }}
            </el-avatar>
            <div class="detail-author">
              <div class="author-name">{{ detailPost?.author_name || '同学' }}</div>
              <div class="author-time">{{ formatTime(detailPost?.created_at) }} · {{ detailPost?.category }}</div>
            </div>
            <el-button size="small" text type="danger" v-if="detailPost?.student_id === myId" @click="removeDetailPost">删除</el-button>
          </div>
          <div class="detail-title">{{ detailPost?.title }}</div>
          <div class="detail-content">{{ detailPost?.content }}</div>
          <div class="detail-stats">
            <el-button
              size="small"
              :type="detailPost?.liked ? 'warning' : 'default'"
              :plain="!detailPost?.liked"
              round
              @click="handleLike"
            >
              <el-icon style="margin-right:3px"><StarFilled /></el-icon>{{ detailPost ? detailPost.like_count : 0 }} 点赞
            </el-button>
            <span class="stat"><el-icon :size="14"><View /></el-icon>{{ detailPost?.view_count || 0 }} 浏览</span>
            <span class="stat"><el-icon :size="14"><ChatLineRound /></el-icon>{{ comments.length }} 评论</span>
          </div>
        </div>

        <div class="comment-section">
          <div class="comment-head">评论 ({{ comments.length }})</div>
          <div v-if="!comments.length" class="empty-tip">暂无评论，来抢沙发吧</div>
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <el-avatar :size="26" :src="c.author_avatar || undefined" class="comment-avatar">
              {{ (c.author_name || '学').slice(0, 1) }}
            </el-avatar>
            <div class="comment-body">
              <div class="comment-meta">
                <span class="comment-author">{{ c.author_name || '同学' }}</span>
                <span class="comment-time">{{ formatTime(c.created_at) }}</span>
                <el-button v-if="c.student_id === myId" size="small" text type="danger" class="comment-del" @click="removeComment(c)">删除</el-button>
              </div>
              <div class="comment-content">{{ c.content }}</div>
            </div>
          </div>
          <div class="comment-input-row">
            <el-input
              v-model="commentDraft"
              placeholder="友善评论，专业交流…"
              maxlength="500"
              :disabled="!detailVisible"
              @keyup.enter="submitComment"
            />
            <el-button type="primary" :loading="sendingComment" @click="submitComment">发表</el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, ChatLineRound, Star, StarFilled } from '@element-plus/icons-vue'
import {
  getPosts, getPost, createPost, deletePost,
  toggleLike, getComments, createComment, deleteComment, getHotPosts,
  COMMUNITY_CATEGORIES, type CommunityPost, type CommunityComment,
} from '@/api/community'
import { useAuthStore } from '@/stores/auth'

// ---------- 状态 ----------
const posts = ref<CommunityPost[]>([])
const hotPosts = ref<CommunityPost[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const filters = reactive<{ category: string; q: string; sort: string }>({ category: 'all', q: '', sort: 'new' })
const categoryFilters = [
  { label: '全部', value: 'all' },
  ...COMMUNITY_CATEGORIES.map(c => ({ label: c, value: c })),
]
const myId = ref<number | null>(null)

// ---------- 工具 ----------
function formatTime(t: string | null | undefined) {
  if (!t) return ''
  const d = new Date(t)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ---------- 数据加载 ----------
async function loadPosts() {
  const params: any = { page: page.value, page_size: pageSize, sort: filters.sort }
  if (filters.category !== 'all') params.category = filters.category
  if (filters.q.trim()) params.q = filters.q.trim()
  const list = await getPosts(params)
  posts.value = list
  // 后端返回数组：不足一页说明到底
  total.value = list.length < pageSize ? (page.value - 1) * pageSize + list.length : page.value * pageSize + 1
}

async function loadHot() {
  try { hotPosts.value = await getHotPosts(5) } catch { hotPosts.value = [] }
}

async function refreshAll() {
  await Promise.all([loadPosts(), loadHot()])
}

onMounted(async () => {
  refreshAll()
  try {
    const auth = useAuthStore()
    myId.value = auth.user?.id ?? null
  } catch { myId.value = null }
})

function switchCategory(c: string) {
  filters.category = c
  page.value = 1
  loadPosts()
}

function searchPosts() {
  page.value = 1
  loadPosts()
}

// ---------- 发帖 ----------
const postDialogVisible = ref(false)
const savingPost = ref(false)
const postForm = reactive({ category: '分享', title: '', content: '' })

function openPostDialog() {
  postForm.category = '分享'
  postForm.title = ''
  postForm.content = ''
  postDialogVisible.value = true
}

async function savePost() {
  if (!postForm.title.trim()) return ElMessage.warning('请填写标题')
  if (!postForm.content.trim()) return ElMessage.warning('请填写内容')
  savingPost.value = true
  try {
    await createPost({ category: postForm.category, title: postForm.title.trim(), content: postForm.content.trim() })
    ElMessage.success('发布成功')
    postDialogVisible.value = false
    page.value = 1
    await Promise.all([loadPosts(), loadHot()])
  } finally { savingPost.value = false }
}

// ---------- 详情 ----------
const detailVisible = ref(false)
const detailPost = ref<CommunityPost | null>(null)
const comments = ref<CommunityComment[]>([])
const commentDraft = ref('')
const sendingComment = ref(false)

async function openDetail(id: number) {
  try {
    detailPost.value = await getPost(id)
    comments.value = await getComments(id)
    detailVisible.value = true
  } catch { ElMessage.error('帖子加载失败') }
}

async function handleLike() {
  if (!detailPost.value) return
  const res = await toggleLike(detailPost.value.id)
  if (detailPost.value) {
    detailPost.value.liked = res.liked
    detailPost.value.like_count = res.count
  }
  loadPosts()
  loadHot()
}

async function submitComment() {
  const content = commentDraft.value.trim()
  if (!content) return
  if (!detailPost.value) return
  sendingComment.value = true
  try {
    await createComment(detailPost.value.id, content)
    commentDraft.value = ''
    comments.value = await getComments(detailPost.value.id)
    if (detailPost.value) detailPost.value.comment_count = comments.value.length
    loadPosts()
    ElMessage.success('评论成功')
  } finally { sendingComment.value = false }
}

async function removeComment(c: CommunityComment) {
  await ElMessageBox.confirm('确定删除这条评论吗？', '删除确认', { type: 'warning' })
  await deleteComment(c.id)
  comments.value = comments.value.filter(x => x.id !== c.id)
  if (detailPost.value) detailPost.value.comment_count = comments.value.length
  loadPosts()
}

async function removeDetailPost() {
  if (!detailPost.value) return
  await ElMessageBox.confirm('确定删除这篇帖子吗？', '删除确认', { type: 'warning' })
  await deletePost(detailPost.value.id)
  ElMessage.success('已删除')
  detailVisible.value = false
  page.value = 1
  await Promise.all([loadPosts(), loadHot()])
}
</script>

<style scoped>
.community-page {
  padding: 16px;
  background: #f8f9fc;
  min-height: 100vh;
  color: #1a1a2e;
  padding-bottom: 90px;
}

.community-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.community-title { margin: 0; font-size: 20px; font-weight: 600; color: #1a1a2e; }
.community-sub { margin: 4px 0 0; font-size: 12px; color: #999; }

.card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.head-bar { width: 3px; height: 14px; background: #409eff; border-radius: 2px; }
.head-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.head-sub { margin-left: auto; font-size: 12px; color: #999; }

.empty-tip { color: #999; font-size: 13px; text-align: center; padding: 22px 0; }

/* 热帖 */
.hot-card { background: linear-gradient(135deg, #fffaf0 0%, #fff 60%); }
.hot-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.2s;
}
.hot-item:hover { background: rgba(230, 162, 60, 0.08); }
.hot-title { flex: 1; font-size: 13px; color: #1a1a2e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hot-count { font-size: 11px; color: #b88230; flex-shrink: 0; }

/* 筛选/搜索 */
.filter-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.filter-tag { cursor: pointer; }
.search-row { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input { flex: 1; }

/* 帖子 */
.post-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.post-card:hover { box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06); }
.post-head { display: flex; align-items: center; gap: 8px; }
.post-avatar { flex-shrink: 0; }
.post-author { font-size: 12px; color: #666; font-weight: 600; }
.post-cat { flex-shrink: 0; color: #409eff; }
.post-time { margin-left: auto; font-size: 11px; color: #bbb; }
.post-title { margin-top: 8px; font-size: 14px; font-weight: 600; color: #1a1a2e; }
.post-content {
  margin-top: 4px; font-size: 13px; color: #666; line-height: 1.6;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.post-stats { display: flex; gap: 18px; margin-top: 8px; }
.stat { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #999; }
.stat-liked { color: #e6a23c; }
.pager-row { display: flex; justify-content: center; padding-top: 6px; }

/* 详情 */
.detail-box { padding: 4px 2px; }
.detail-top { border-bottom: 1px solid rgba(0, 0, 0, 0.06); padding-bottom: 14px; }
.detail-head { display: flex; align-items: center; gap: 10px; }
.detail-author { flex: 1; }
.author-name { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.author-time { font-size: 11px; color: #999; margin-top: 2px; }
.detail-title { margin-top: 14px; font-size: 18px; font-weight: 700; color: #1a1a2e; }
.detail-content {
  margin-top: 10px; font-size: 14px; color: #3a3a4e; line-height: 1.8;
  white-space: pre-wrap; word-break: break-word;
}
.detail-stats { display: flex; align-items: center; gap: 18px; margin-top: 14px; }

/* 评论 */
.comment-section { padding-top: 14px; }
.comment-head { font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 10px; }
.comment-item { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px dashed rgba(0, 0, 0, 0.05); }
.comment-avatar { flex-shrink: 0; }
.comment-body { flex: 1; min-width: 0; }
.comment-meta { display: flex; align-items: center; gap: 8px; }
.comment-author { font-size: 12px; font-weight: 600; color: #555; }
.comment-time { font-size: 11px; color: #bbb; }
.comment-del { margin-left: auto; flex-shrink: 0; }
.comment-content { margin-top: 4px; font-size: 13px; color: #444; line-height: 1.6; word-break: break-word; }
.comment-input-row { display: flex; gap: 8px; margin-top: 14px; }
</style>