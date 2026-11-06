<template>
  <div class="af-page">
    <!-- 子页头：返回 + 居中标题，与学生端「添加朋友」同一套规格（48px 白底 + 发丝线） -->
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
          placeholder="搜索 学号 / 工号 / 姓名"
        />
        <button v-if="keyword" type="button" class="af-clear" aria-label="清空" @click="clearKeyword">
          <el-icon :size="15"><CircleCloseFilled /></el-icon>
        </button>
      </div>

      <!-- Ⅰ 搜索结果：按学号 / 工号 / 姓名找人，选中直接发起会话 -->
      <template v-if="kw">
        <p v-if="searching" class="af-status">搜索中…</p>
        <div v-else-if="!results.length" class="af-blank">
          <el-icon :size="28"><Search /></el-icon>
          <p>没找到「{{ kw }}」</p>
          <span>试试完整工号 / 学号，或者姓名</span>
        </div>
        <ul v-else class="af-people">
          <li v-for="u in results" :key="u.id" class="af-person">
            <el-avatar :size="42" :src="u.avatar || undefined" class="af-avatar">{{ u.name.slice(0, 1) }}</el-avatar>
            <div class="af-person-main">
              <span class="af-person-name">{{ u.name }}</span>
              <span class="af-person-sub">{{ u.username }} · {{ u.role === 'teacher' ? '教师' : '学生' }}</span>
            </div>
            <div class="af-person-acts">
              <button type="button" class="af-mini is-primary" @click="startChat(u)">聊天</button>
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

        <!-- 我的名片：二维码 + 工号。本系统没有内置扫码入口，
             所以码里就是一张**纯文字名片**（相机扫出来直接能看到工号），而不是一个打不开的链接。 -->
        <section ref="cardRef" class="af-card">
          <div class="af-card-qr">
            <img v-if="qrDataUrl" :src="qrDataUrl" alt="我的名片二维码" />
            <div v-else class="af-card-qr-ph" />
          </div>
          <p class="af-card-name">{{ me?.name || '我' }}</p>
          <p class="af-card-sub">
            {{ me?.username || '' }}<template v-if="me?.college"> · {{ me.college }}</template>
          </p>
          <p class="af-card-tip">师生用相机扫码即可看到你的工号，在「添加朋友」里搜一下就能找到你</p>
          <button v-if="me?.username" type="button" class="af-copy" @click="copyAccount">
            <el-icon :size="14"><CopyDocument /></el-icon>
            <span>复制工号</span>
          </button>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
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
} from '@element-plus/icons-vue'
import type { Component } from 'vue'
import QRCode from 'qrcode'
import { useAuthStore } from '@/stores/auth'
import { searchUsers, type UserSearchResult } from '@/api/groups'

const router = useRouter()
const auth = useAuthStore()
const me = computed(() => auth.user)

/* ==================== 页头 / 返回 ==================== */
function goBack() {
  // 从消息页 push 进来，正常就是 history.back；直接输地址进来时没有上一条，退回消息页
  if (window.history.length > 1) router.back()
  else void router.replace({ name: 'teacher-messages' })
}

/* ==================== 搜索 ==================== */
const keyword = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const results = ref<UserSearchResult[]>([])
const searching = ref(false)
const kw = computed(() => keyword.value.trim())

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
  // 300ms 防抖：边打边搜会把请求打满，手机键盘输入又特别碎
  searchTimer = setTimeout(() => void runSearch(q), 300)
})

async function runSearch(q: string) {
  try {
    const list = await searchUsers(q)
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

/** 发起会话：组织内用户无需好友关系，选中即打开单聊（与钉钉一致） */
function startChat(u: UserSearchResult) {
  void router.push({ name: 'teacher-messages', query: { chat: String(u.id), chatName: u.name } })
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

const cardRef = ref<HTMLElement | null>(null)

const entries = computed<EntryRow[]>(() => [
  {
    key: 'group',
    title: '发起群聊',
    sub: '选几位师生，一起建个群',
    color: '#4b8bf5',
    icon: ChatLineRound,
    // 建群表单在消息页的「＋」面板里，带 action 回消息页直接弹出，避免这一页再复制一套选人逻辑
    action: () => void router.push({ name: 'teacher-messages', query: { action: 'group' } }),
  },
  {
    key: 'contacts',
    title: '通讯录',
    sub: '最近联系人 / 我的学生',
    color: '#2aa06b',
    icon: Notebook,
    action: () => void router.push({ name: 'teacher-messages', query: { view: 'contacts' } }),
  },
  {
    key: 'card',
    title: '我的名片',
    sub: '让师生扫码找到你',
    color: '#7c6cf0',
    icon: Postcard,
    action: () => {
      cardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    },
  },
])

/* ==================== 名片 ==================== */
const qrDataUrl = ref('')

/** 名片二维码：纯文字名片，任何相机都能扫出工号 —— 本系统没有内置扫码器，做成链接反而是死码 */
async function renderCard() {
  const u = auth.user
  if (!u) return
  const text = [
    '绵小城 · 校园名片',
    `姓名：${u.name}`,
    `学号/工号：${u.username}`,
    u.college ? `学院：${u.college}` : '',
  ]
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
    ElMessage.success('工号已复制')
  } catch {
    ElMessage.warning(`工号：${account}`)
  }
}

onMounted(() => {
  void renderCard()
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

/* 移动端：路由级「二级子页」，与学生端「添加朋友」同款整屏子页 */
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
  /* 统一页头规范：高度/内边距取 --appbar-* 变量（styles/responsive.css），
     原先是写死的 calc(8px + env(...))，比其它页多 2px 留白。 */
  min-height: var(--appbar-h);
  padding: var(--sat, 0px) var(--appbar-px) 0;
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

/* ================= 人（搜索结果） ================= */
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
