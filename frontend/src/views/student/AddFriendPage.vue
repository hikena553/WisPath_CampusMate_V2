<template>
  <div class="af-page subpage-underlay" :class="{ 'is-subpushed': isMobile && createGroupOpen }">
    <!-- 子页头：返回 + 居中标题。样式与学业中心 / 搜索子页同规格（48px 白底 + 发丝线），
         移动端吸顶、桌面端退化成同一条（宽度由 .af-body 收窄），不进底部导航白名单。 -->
    <header class="af-head">
      <button type="button" class="af-back" aria-label="返回" @click="goBack">
        <el-icon :size="20"><ArrowLeft /></el-icon>
      </button>
      <h1 class="af-title">添加朋友</h1>
      <span class="af-head-side" aria-hidden="true" />
    </header>

    <div class="af-body">
      <div class="af-search">
        <el-icon :size="15"><Search /></el-icon>
        <input
          ref="inputRef"
          v-model="keyword"
          class="af-input"
          type="search"
          enterkeyhint="search"
          placeholder="搜索 学号 / 姓名"
        />
        <button v-if="keyword" type="button" class="af-clear" aria-label="清空" @click="clearKeyword">
          <el-icon :size="15"><CircleCloseFilled /></el-icon>
        </button>
      </div>

      <!-- Ⅰ 搜索结果：按学号 / 姓名找人，直接关注或开聊 -->
      <template v-if="kw">
        <p v-if="searching" class="af-status">搜索中…</p>
        <div v-else-if="!results.length" class="af-blank">
          <el-icon :size="28"><Search /></el-icon>
          <p>没找到「{{ kw }}」</p>
          <span>试试完整学号，或者同学的姓名</span>
        </div>
        <ul v-else class="af-people">
          <li v-for="u in results" :key="u.id" class="af-person">
            <el-avatar :size="42" :src="u.avatar || undefined" class="af-avatar">{{ u.name.slice(0, 1) }}</el-avatar>
            <div class="af-person-main">
              <span class="af-person-name">{{ u.name }}</span>
              <span class="af-person-sub">{{ u.username }} · {{ u.role === 'teacher' ? '教师' : '学生' }}</span>
            </div>
            <!-- 一个动作位、两种身份：没关注只有「关注」，关注之后它原地变成「发消息」——
                 没关注就不给发消息入口，避免「加没加上人都还没定，先把消息发出去」。 -->
            <div class="af-person-acts">
              <button
                v-if="isFollowing(u.id)"
                type="button"
                class="af-mini is-primary"
                @click="startChat(u.id)"
              >
                发消息
              </button>
              <button
                v-else
                type="button"
                class="af-mini is-primary"
                :disabled="followingId === u.id"
                @click="follow(u.id)"
              >
                {{ followingId === u.id ? '关注中…' : '关注' }}
              </button>
            </div>
          </li>
        </ul>
      </template>

      <!-- Ⅱ 还没输入：入口列表 + 我的名片 -->
      <template v-else>
        <ul class="af-entries">
          <li v-for="row in entries" :key="row.key" class="af-entry">
            <button type="button" class="af-entry-btn" @click="row.action()">
              <span class="af-entry-icon" :style="{ color: row.color }">
                <el-icon :size="22"><component :is="row.icon" /></el-icon>
              </span>
              <span class="af-entry-main">
                <span class="af-entry-title">{{ row.title }}</span>
                <span class="af-entry-sub">{{ row.sub }}</span>
              </span>
              <el-icon class="af-chevron" :size="15"><ArrowRight /></el-icon>
            </button>
          </li>
        </ul>

        <!-- 可能认识的人：就地展开，不跳页 —— 这一屏正是「加人」的场景，出去再回来反而断节奏 -->
        <section v-if="suggestOpen" class="af-suggest">
          <div class="af-suggest-head">
            <span>可能认识的人</span>
            <button v-if="suggestLoading" type="button" class="af-text-btn" disabled>加载中…</button>
          </div>
          <p v-if="!suggestLoading && !suggestions.length" class="af-suggest-empty">
            暂时没有推荐，先去社区逛逛，关注感兴趣的同学
          </p>
          <div v-for="s in suggestions" :key="s.id" class="af-person">
            <el-avatar :size="42" :src="s.avatar || undefined" class="af-avatar">{{ s.name.slice(0, 1) }}</el-avatar>
            <div class="af-person-main">
              <span class="af-person-name">{{ s.name }}</span>
              <span class="af-person-sub">{{ suggestMeta(s) }}</span>
            </div>
            <!-- 与搜索结果同一套：关注前只有「关注」，关注后变成「发消息」 -->
            <div class="af-person-acts">
              <button
                v-if="isFollowing(s.id)"
                type="button"
                class="af-mini is-primary"
                @click="startChat(s.id)"
              >
                发消息
              </button>
              <button
                v-else
                type="button"
                class="af-mini is-primary"
                :disabled="followingId === s.id"
                @click="follow(s.id)"
              >
                {{ followingId === s.id ? '关注中…' : '关注' }}
              </button>
            </div>
          </div>
        </section>

        <!-- 我的名片：二维码 + 学号。本系统没有内置扫码入口，
             所以码里就是一张**纯文字名片**（相机扫出来直接能看到学号），而不是一个打不开的链接。 -->
        <section ref="cardRef" class="af-card">
          <div class="af-card-qr">
            <img v-if="qrDataUrl" :src="qrDataUrl" alt="我的名片二维码" />
            <div v-else class="af-card-qr-ph" />
          </div>
          <p class="af-card-name">{{ me?.name || '我' }}</p>
          <p class="af-card-sub">
            {{ me?.username || '' }}<template v-if="me?.college"> · {{ me.college }}</template>
          </p>
          <p class="af-card-tip">同学用相机扫码即可看到你的学号，在「添加朋友」里搜一下就能找到你</p>
          <button v-if="me?.username" type="button" class="af-copy" @click="copyAccount">
            <el-icon :size="14"><CopyDocument /></el-icon>
            <span>复制学号</span>
          </button>
        </section>
      </template>
    </div>

    <CreateGroupPopup v-model="createGroupOpen" @created="onGroupCreated" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  ChatLineRound,
  CircleCloseFilled,
  CopyDocument,
  Notebook,
  Postcard,
  Search,
  User,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'
import QRCode from 'qrcode'
import CreateGroupPopup from '@/components/chat/CreateGroupPopup.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import { searchUsers } from '@/api/groups'
import { followUser, getContacts, getSuggestions, type SuggestUser } from '@/api/social'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const me = computed(() => auth.user)
// 发起群聊在本页是移动端整屏子页：打开时本页退 30% 让位（is-subpushed），
// 桌面端弹的是居中对话框，页面不动 —— 所以只看移动端。
const { isMobile } = useResponsive()

/* ==================== 页头 / 返回 ==================== */
function goBack() {
  // 从消息页 push 进来，正常就是 history.back；直接输地址进来时没有上一条，退回消息页
  if (window.history.length > 1) router.back()
  else void router.replace({ name: 'student-messages' })
}

/* ==================== 搜索 ==================== */
const keyword = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const results = ref<Array<{ id: number; name: string; username: string; avatar: string | null; role: string }>>([])
const searching = ref(false)
const kw = computed(() => keyword.value.trim())

/** 已关注的人：搜索结果与推荐共用一份，关注后立刻变「已关注」，不用重新搜 */
const following = ref<Set<number>>(new Set())
let followingLoaded = false
const followingId = ref<number | null>(null)

function isFollowing(id: number) {
  return following.value.has(id)
}

async function ensureFollowing() {
  if (followingLoaded) return
  try {
    const list = await getContacts({ tab: 'following', limit: 200 })
    following.value = new Set(list.map((c) => c.id))
    followingLoaded = true
  } catch {
    /* 拿不到就按「未关注」显示，点一下后端也会返回真实状态 */
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(keyword, (v) => {
  if (searchTimer) clearTimeout(searchTimer)
  const q = v.trim()
  if (!q) {
    results.value = []
    searching.value = false
    return
  }
  searching.value = true
  // 300ms 防抖：边打边搜会把 20 条结果的请求打满，手机键盘输入又特别碎
  searchTimer = setTimeout(() => void runSearch(q), 300)
})

async function runSearch(q: string) {
  try {
    const [list] = await Promise.all([searchUsers(q), ensureFollowing()])
    // 关键词已经变了：这批结果作废，避免旧请求后到把新结果盖掉
    if (q !== kw.value) return
    results.value = list
  } catch {
    results.value = []
  } finally {
    if (q === kw.value) searching.value = false
  }
}

function clearKeyword() {
  keyword.value = ''
  results.value = []
}

async function follow(id: number) {
  if (isFollowing(id) || followingId.value) return
  followingId.value = id
  try {
    const state = await followUser(id)
    if (state.is_following) following.value = new Set([...following.value, id])
    ElMessage.success('已关注，对方会收到通知')
  } catch {
    ElMessage.error('关注失败，请稍后再试')
  } finally {
    followingId.value = null
  }
}

/** 发起会话：复用消息页的 ?chat=s-<id> 入口，落地即打开这条会话。
 *  只对「已关注」的人开放 —— 这一页的语义是先关注、再聊天，
 *  没关注的人连入口都不给（按钮会显示成「关注」）。 */
function startChat(id: number) {
  if (!isFollowing(id)) {
    ElMessage.warning('先关注对方，才能发消息')
    return
  }
  void router.push({ name: 'student-messages', query: { chat: `s-${id}` } })
}

/* ==================== 入口列表 ==================== */
interface EntryRow {
  key: string
  title: string
  sub: string
  color: string
  icon: Component
  action: () => void
}

const createGroupOpen = ref(false)
const suggestOpen = ref(false)
const suggestions = ref<SuggestUser[]>([])
const suggestLoading = ref(false)
const cardRef = ref<HTMLElement | null>(null)

const entries = computed<EntryRow[]>(() => [
  {
    key: 'group',
    title: '发起群聊',
    sub: '选几个同学，一起建个群',
    color: '#4b8bf5',
    icon: ChatLineRound,
    action: () => {
      createGroupOpen.value = true
    },
  },
  {
    key: 'suggest',
    title: '可能认识的人',
    sub: '同学院、同班的同学',
    color: '#f0a020',
    icon: User,
    action: () => void toggleSuggest(),
  },
  {
    key: 'contacts',
    title: '通讯录',
    sub: '我关注的 / 关注我的',
    color: '#2aa06b',
    icon: Notebook,
    action: () => void router.push({ name: 'student-message-friends' }),
  },
  {
    key: 'card',
    title: '我的名片',
    sub: '让同学扫码加你',
    color: '#7c6cf0',
    icon: Postcard,
    action: () => {
      cardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    },
  },
])

async function toggleSuggest() {
  if (suggestOpen.value) {
    suggestOpen.value = false
    return
  }
  suggestOpen.value = true
  if (suggestions.value.length || suggestLoading.value) {
    await nextTick()
    return
  }
  suggestLoading.value = true
  try {
    const [list] = await Promise.all([getSuggestions(8), ensureFollowing()])
    suggestions.value = list
  } catch {
    suggestions.value = []
  } finally {
    suggestLoading.value = false
  }
}

function suggestMeta(s: SuggestUser) {
  return [s.class_name, s.college].filter(Boolean).join(' · ') || (s.role === 'teacher' ? '教师' : '同学')
}

/* ==================== 建群 / 名片 ==================== */
/** 建完直接回到消息页并打开这个群：入口在本页，落点仍该是「能说话的地方」 */
function onGroupCreated(group: { id: number; name: string }) {
  void router.replace({ name: 'student-messages', query: { chat: `g-${group.id}` } })
}

const qrDataUrl = ref('')

/** 名片二维码：纯文字名片，任何相机都能扫出学号 —— 本系统没有内置扫码器，做成链接反而是死码 */
async function renderCard() {
  const u = auth.user
  if (!u) return
  const text = ['绵小城 · 校园名片', `姓名：${u.name}`, `学号/工号：${u.username}`, u.college ? `学院：${u.college}` : '']
    .filter(Boolean)
    .join('\n')
  try {
    qrDataUrl.value = await QRCode.toDataURL(text, { width: 420, margin: 1, errorCorrectionLevel: 'M' })
  } catch {
    qrDataUrl.value = ''
  }
}

async function copyAccount() {
  const account = auth.user?.username
  if (!account) return
  try {
    await navigator.clipboard.writeText(account)
    ElMessage.success('学号已复制')
  } catch {
    ElMessage.warning(`学号：${account}`)
  }
}

onMounted(() => {
  void renderCard()
  void ensureFollowing()
  // 从「通讯录空态」等入口带 kw 进来时直接给出结果，少一次手动输入
  const seed = typeof route.query.kw === 'string' ? route.query.kw : ''
  if (seed) keyword.value = seed
})
</script>

<style scoped>
.af-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fff;
  color: #1f2329;
  -webkit-tap-highlight-color: transparent;
}

/* 移动端：路由级「二级子页」，进出场走 animations.css 的 route-subpage。
   那套过渡在移动端要求「进场页自身 fixed 脱流」，否则离开的消息页会与它在
   .main-area 的 flex 列里各分一半高度（0.3s 的抽动）。本路由不在 TAB_BAR_ROUTES、
   顶栏在 ≤767px 也隐藏，所以 fixed 整屏与流内区域完全重合，落位不跳。 */
@media (max-width: 767px) {
  .af-page {
    position: fixed;
    inset: 0;
    z-index: 1500;
  }
}

/* ================= 页头 ================= */
.af-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: calc(8px + env(safe-area-inset-top, 0px)) 12px 8px;
  background: #fff;
  border-bottom: 1px solid #f0f1f3;
}
.af-back {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: -4px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: none;
  color: #1f2329;
  cursor: pointer;
}
.af-back:active { background: rgba(20, 23, 26, 0.06); }
/* 标题居中靠左右两枚等宽占位，不靠绝对定位：绝对定位一旦右侧没内容，标题会随文字长度左右漂 */
.af-title {
  flex: 1;
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  text-align: center;
  letter-spacing: 0.2px;
}
.af-head-side { width: 32px; flex-shrink: 0; margin-right: -4px; }

/* ================= 主体 ================= */
.af-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding-bottom: calc(28px + env(safe-area-inset-bottom, 0px));
  max-width: 640px;
  width: 100%;
  margin: 0 auto;
}

.af-search {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  margin: 12px 16px 4px;
  padding: 0 11px;
  border-radius: 10px;
  background: #f5f6f8;
  color: #9aa0a6;
}
.af-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0;
  border: 0;
  outline: none;
  background: transparent;
  /* 16px：iOS 上小于 16px 的输入框聚焦会自动放大整页 */
  font-size: 16px;
  color: #1f2329;
}
.af-input::placeholder { color: #9aa0a6; }
.af-input::-webkit-search-cancel-button { display: none; }
.af-clear {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 2px;
  border: 0;
  border-radius: 50%;
  background: none;
  color: #c0c4cc;
  cursor: pointer;
}

/* ================= 入口行 ================= */
.af-entries { margin: 12px 0 0; padding: 0; list-style: none; }
/* 分隔线从文字左沿起（图标 24 + 间距 14 + 内边距 16 = 54），不横穿图标那一列 */
.af-entry + .af-entry .af-entry-btn { position: relative; }
.af-entry + .af-entry .af-entry-btn::before {
  content: '';
  position: absolute;
  left: 54px;
  right: 16px;
  top: 0;
  height: 1px;
  background: #f0f1f3;
}
.af-entry-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 14px 16px;
  border: 0;
  background: none;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.af-entry-btn:active { background: #f7f8fa; }
.af-entry-icon {
  flex-shrink: 0;
  width: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.af-entry-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.af-entry-title { font-size: 16px; color: #1d2129; line-height: 1.25; }
.af-entry-sub { font-size: 12.5px; color: #9aa0a6; line-height: 1.25; }
.af-chevron { flex-shrink: 0; color: #c6cad1; }

/* ================= 人（搜索结果 / 推荐共用一套行） ================= */
.af-people { margin: 8px 0 0; padding: 0; list-style: none; }
.af-person {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
}
.af-person + .af-person { border-top: 1px solid #f4f5f7; }
.af-avatar { flex-shrink: 0; background: #e4e8ee; color: #5b6472; font-size: 16px; font-weight: 500; }
.af-person-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.af-person-name { font-size: 15.5px; color: #1d2129; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-person-sub { font-size: 12.5px; color: #9aa0a6; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.af-person-acts { flex-shrink: 0; display: flex; gap: 8px; }
.af-mini {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #e3e6ea;
  border-radius: 15px;
  background: #fff;
  color: #4e5969;
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
}
.af-mini:active { background: #f4f5f7; }
.af-mini.is-primary { border-color: #3b82f6; color: #3b82f6; }
.af-mini.is-primary:active { background: #eef4ff; }

/* ================= 可能认识的人 ================= */
.af-suggest { margin-top: 6px; padding-top: 6px; border-top: 8px solid #f5f6f8; }
.af-suggest-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 2px;
  font-size: 13px;
  color: #6b7280;
}
.af-text-btn { border: 0; background: none; color: #3b82f6; font-size: 12.5px; cursor: pointer; }
.af-text-btn:disabled { color: #a8adb5; cursor: default; }
.af-suggest-empty { margin: 0; padding: 14px 16px 18px; font-size: 13px; color: #9aa0a6; }

/* ================= 我的名片 ================= */
.af-card {
  margin-top: 8px;
  padding: 28px 24px 34px;
  border-top: 8px solid #f5f6f8;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.af-card-qr {
  width: 188px;
  height: 188px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 14px rgba(17, 24, 39, 0.08);
}
.af-card-qr img { width: 172px; height: 172px; display: block; }
.af-card-qr-ph { width: 172px; height: 172px; border-radius: 10px; background: #f5f6f8; }
.af-card-name { margin: 10px 0 0; font-size: 16px; font-weight: 600; color: #1d2129; }
.af-card-sub { margin: 0; font-size: 12.5px; color: #9aa0a6; }
.af-card-tip {
  margin: 6px 0 0;
  max-width: 260px;
  font-size: 12px;
  line-height: 1.6;
  color: #a8adb5;
  text-align: center;
}
.af-copy {
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 12px;
  border: 1px solid #e3e6ea;
  border-radius: 15px;
  background: #fff;
  color: #4e5969;
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
}
.af-copy:active { background: #f4f5f7; }

/* ================= 状态位 ================= */
.af-status { margin: 18px 16px; font-size: 13px; color: #9aa0a6; }
.af-blank {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 56px 24px;
  color: #c0c4cc;
}
.af-blank p { margin: 0; font-size: 14px; color: #6b7280; }
.af-blank span { font-size: 12.5px; color: #9aa0a6; }

/* 桌面端：页头与内容一起收窄成一列，两侧留出页面底色，靠一层很轻的投影把这一列托起来 */
@media (min-width: 768px) {
  .af-page { background: #f5f6f8; }
  .af-head {
    max-width: 640px;
    width: 100%;
    margin: 0 auto;
    background: #fff;
    border-radius: 14px 14px 0 0;
    box-shadow: 0 6px 18px rgba(17, 24, 39, 0.05);
    position: relative;
    z-index: 1;
  }
  .af-body { background: #fff; box-shadow: 0 12px 30px rgba(17, 24, 39, 0.05); }
  .af-entry-btn { padding: 16px 20px; }
  .af-entry + .af-entry .af-entry-btn::before { left: 58px; right: 20px; }
  .af-person { padding: 12px 20px; }
  .af-search { margin: 14px 20px 6px; }
}
</style>
