<template>
  <div class="pcp" :class="{ 'is-closing': closing }" role="dialog" aria-label="发布帖子">
    <!-- ===== 顶栏：返回 / 内容类型 / 发布 =====
         版式照移动端发帖范式：左箭头、中间「内容▾」切换图文或长文、右侧发布。
         发布按钮置灰只是视觉，真正的门槛在 save() 里再判一次（回车/快捷键也能走到）。 -->
    <header class="pcp-bar">
      <button type="button" class="pcp-back" aria-label="返回" @click="requestClose">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true">
          <path d="M15 4.5 7.5 12 15 19.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>

      <div class="pcp-mode">
        <button type="button" class="pcp-mode-btn" aria-haspopup="listbox" @click.stop="modeOpen = !modeOpen">
          {{ mode === 'post' ? '内容' : '文章' }}
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true" :class="{ 'flip': modeOpen }">
            <path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <ul v-if="modeOpen" class="pcp-mode-list" role="listbox">
          <li
            v-for="m in MODES" :key="m.key"
            role="option" :aria-selected="mode === m.key"
            :class="{ active: mode === m.key }"
            @click="switchMode(m.key)"
          >
            <b>{{ m.label }}</b>
            <span>{{ m.desc }}</span>
          </li>
        </ul>
      </div>

      <button
        type="button"
        class="pcp-publish"
        :class="{ 'is-ready': canPublish, 'is-saving': saving }"
        :disabled="!canPublish || saving"
        @click="save"
      >{{ saving ? '发布中' : '发布' }}</button>
    </header>

    <div v-if="modeOpen" class="pcp-mask" @click="modeOpen = false" />

    <!-- ===== 编辑区 ===== -->
    <div class="pcp-body" @click="modeOpen = false">
      <!-- 配图（图文模式置顶；长文模式也能从底部工具条加） -->
      <div v-if="images.length || mode === 'post'" class="pcp-images">
        <div v-for="(img, i) in images" :key="img + i" class="pcp-thumb">
          <img :src="img" alt="" />
          <button type="button" class="pcp-thumb-del" aria-label="移除图片" @click="removeImage(i)">×</button>
        </div>
        <div v-if="uploading" class="pcp-thumb pcp-thumb--loading">
          <span class="pcp-spinner" aria-hidden="true" />
        </div>
        <button
          v-else-if="images.length < MAX_IMAGES"
          type="button"
          class="pcp-thumb pcp-thumb--add"
          aria-label="添加图片"
          @click="pickImages"
        >
          <svg viewBox="0 0 24 24" width="30" height="30" fill="none" aria-hidden="true">
            <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </button>
        <span class="pcp-images-tip">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true">
            <rect x="3.5" y="5" width="17" height="14" rx="2.5" stroke="currentColor" stroke-width="1.5" />
            <path d="m4.5 16.5 4.6-4.3 3.4 3 3-2.6 4 3.9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          文字配图
        </span>
      </div>

      <!-- 标题 -->
      <div class="pcp-title-row">
        <input
          ref="titleRef"
          v-model="title"
          class="pcp-title"
          type="text"
          :maxlength="TITLE_MAX"
          :placeholder="mode === 'article' ? '填写标题（2~30字）' : '填写标题'"
          @keydown.enter.prevent="focusBody"
        />
        <span class="pcp-counter" :class="{ 'is-warn': title.length >= TITLE_MAX }">{{ title.length }}/{{ TITLE_MAX }}</span>
      </div>

      <!-- 长文模式的社区引导（照参考图原文的口径，改成我们真实存在的分类） -->
      <p v-if="mode === 'article'" class="pcp-hint">
        可点击下方「添加分区」选择发到哪个分区，选对分区能让更多同学看到；
        不选分区则按「分享」发出，只出现在社区帖子流里。
      </p>

      <!-- 正文 -->
      <textarea
        ref="bodyRef"
        v-model="content"
        class="pcp-content"
        :placeholder="mode === 'article' ? '添加正文，说清楚你的观点或经历（建议 100 字以上）' : '添加正文'"
        :maxlength="CONTENT_MAX"
      />

      <div class="pcp-body-counter">{{ content.length }} 字</div>
    </div>

    <!-- ===== 底栏：分区 + 工具条 ===== -->
    <footer class="pcp-foot">
      <button type="button" class="pcp-topic" @click.stop="categoryOpen = true">
        <span class="pcp-topic-plus">＋</span>{{ category ? `分区：${category}` : '添加分区及话题' }}
      </button>

      <div class="pcp-tools">
        <button type="button" class="pcp-tool" aria-label="表情" @click.stop="emojiOpen = !emojiOpen">
          <svg viewBox="0 0 24 24" width="23" height="23" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="8.4" stroke="currentColor" stroke-width="1.6" />
            <circle cx="9" cy="10.4" r="1" fill="currentColor" />
            <circle cx="15" cy="10.4" r="1" fill="currentColor" />
            <path d="M8.6 14.2c.9 1.2 2 1.8 3.4 1.8s2.5-.6 3.4-1.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </button>
        <button type="button" class="pcp-tool" aria-label="添加图片" @click.stop="pickImages">
          <svg viewBox="0 0 24 24" width="23" height="23" fill="none" aria-hidden="true">
            <rect x="3.2" y="5" width="17.6" height="14" rx="2.4" stroke="currentColor" stroke-width="1.6" />
            <circle cx="9" cy="10" r="1.4" stroke="currentColor" stroke-width="1.4" />
            <path d="m4.6 16.6 4.8-4.4 3.2 2.8 2.8-2.4 3.9 3.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
    </footer>

    <!-- 表情条 -->
    <div v-if="emojiOpen" class="pcp-emoji" @click.stop>
      <button v-for="e in EMOJIS" :key="e" type="button" class="pcp-emoji-item" @click="appendText(e)">{{ e }}</button>
    </div>

    <!-- 分区选择（底部小面板） -->
    <div v-if="categoryOpen" class="pcp-sheet-mask" @click.self="categoryOpen = false">
      <div class="pcp-sheet">
        <div class="pcp-sheet-head">
          <span>选择分区</span>
          <button type="button" aria-label="关闭" @click="categoryOpen = false">×</button>
        </div>
        <div class="pcp-cats">
          <button
            v-for="c in COMMUNITY_CATEGORIES" :key="c" type="button"
            class="pcp-cat" :class="{ active: category === c }"
            @click="chooseCategory(c)"
          >{{ c }}</button>
        </div>
      </div>
    </div>

    <input ref="fileRef" type="file" accept="image/*" multiple hidden @change="onFiles" />
  </div>
</template>

<script setup lang="ts">
/**
 * 全屏发帖编辑器（移动端范式：顶栏「返回 / 内容·文章 / 发布」+ 配图位 + 标题正文 + 分区与工具条）。
 *
 * 为什么是整页而不是底部面板：参考的是主流社区的写法 —— 长文 + 多图需要整屏空间，
 * 底部面板一撑高就把正文挤成一条缝。桌面端不另做一套，收成居中 640px 的面板。
 *
 * 调用方：校园资讯页发帖悬浮按钮、交流社区页「发帖」按钮。
 *   <PostComposePage v-if="open" @closed="open=false" @published="onPublished" />
 * 挂载即打开、卸载即关闭，退出动画走 is-closing 类，动画结束再 emit('closed')。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createPost, COMMUNITY_CATEGORIES, type CommunityPost } from '@/api/community'
import { uploadFile } from '@/api/upload'
import { actionConfirm } from '@/composables/useActionSheet'

const emit = defineEmits<{
  (e: 'closed'): void
  (e: 'published', post: CommunityPost): void
}>()

const MODES = [
  { key: 'post' as const, label: '内容', desc: '图文动态，适合随手分享' },
  { key: 'article' as const, label: '文章', desc: '长文，适合经验与教程' },
]
const EMOJIS = ['😀', '😄', '😁', '😊', '🙂', '😉', '😍', '🤩', '😎', '🤔', '😅', '😂', '🥲', '😭', '😤', '😴', '👍', '👏', '🙏', '💪', '🎉', '🔥', '✨', '❤️']

const MAX_IMAGES = 9
const TITLE_MAX = 30
const CONTENT_MAX = 2000
const DRAFT_KEY = 'community_post_draft'

const mode = ref<'post' | 'article'>('post')
const title = ref('')
const content = ref('')
const images = ref<string[]>([])
const category = ref<string>('')
const saving = ref(false)
const uploading = ref(false)
const closing = ref(false)
const modeOpen = ref(false)
const emojiOpen = ref(false)
const categoryOpen = ref(false)

const titleRef = ref<HTMLInputElement | null>(null)
const bodyRef = ref<HTMLTextAreaElement | null>(null)
const fileRef = ref<HTMLInputElement | null>(null)

const canPublish = computed(() => {
  const t = title.value.trim()
  const c = content.value.trim()
  if (!t || !c) return false
  if (mode.value === 'article' && t.length < 2) return false
  return true
})

function focusBody() { bodyRef.value?.focus() }

function appendText(text: string) {
  content.value += text
  emojiOpen.value = false
  void nextTick(focusBody)
}

function switchMode(key: 'post' | 'article') {
  mode.value = key
  modeOpen.value = false
  // 文章模式标题有 2 字下限，切过去时把焦点给标题，暗示「先把标题写清楚」
  if (key === 'article') void nextTick(() => titleRef.value?.focus())
}

function chooseCategory(c: string) {
  category.value = category.value === c ? '' : c
  categoryOpen.value = false
}

/* ---------- 配图 ---------- */
function pickImages() { fileRef.value?.click() }

async function onFiles(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  const room = MAX_IMAGES - images.value.length
  if (room <= 0) return ElMessage.warning(`最多 ${MAX_IMAGES} 张图片`)
  uploading.value = true
  try {
    for (const f of files.slice(0, room)) {
      if (!f.type.startsWith('image/')) continue
      if (f.size > 10 * 1024 * 1024) { ElMessage.warning('单张图片不要超过 10MB'); continue }
      const { url } = await uploadFile(f)
      images.value.push(url)
    }
    if (files.length > room) ElMessage.warning(`最多 ${MAX_IMAGES} 张，多余的没有添加`)
  } catch {
    ElMessage.error('图片上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

function removeImage(i: number) {
  images.value.splice(i, 1)
}

/* ---------- 草稿：返回/误触不丢内容 ---------- */
function saveDraft() {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      mode: mode.value, title: title.value, content: content.value, images: images.value, category: category.value,
    }))
  } catch { /* 隐私模式下写不进去，忽略 */ }
}

function readDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return
    const d = JSON.parse(raw)
    mode.value = d.mode === 'article' ? 'article' : 'post'
    title.value = typeof d.title === 'string' ? d.title : ''
    content.value = typeof d.content === 'string' ? d.content : ''
    images.value = Array.isArray(d.images) ? d.images.slice(0, MAX_IMAGES) : []
    category.value = typeof d.category === 'string' ? d.category : ''
  } catch { /* 草稿坏了就当没有 */ }
}

function clearDraft() {
  try { localStorage.removeItem(DRAFT_KEY) } catch { /* ignore */ }
}

let draftTimer: number | undefined
watch([mode, title, content, images, category], () => {
  window.clearTimeout(draftTimer)
  draftTimer = window.setTimeout(saveDraft, 400)
}, { deep: true })

/* ---------- 打开 / 关闭 ---------- */
onMounted(async () => {
  readDraft()
  await nextTick()
  // 已经有草稿就接着写，光标落在正文；空白草稿直接把焦点给标题
  const focusTarget = content.value.trim() ? bodyRef.value : titleRef.value
  focusTarget?.focus()
})

const dirty = computed(() => !!(title.value.trim() || content.value.trim() || images.value.length))

async function requestClose() {
  if (saving.value) return
  if (dirty.value) {
    const leave = await actionConfirm('内容已存为草稿，下次发帖会自动带出来。要离开吗？', '离开编辑', {
      confirmButtonText: '离开', cancelButtonText: '继续编辑',
    })
    if (!leave) return
    saveDraft()
  }
  closing.value = true
  window.setTimeout(() => emit('closed'), 260)
}

/* ---------- 发布 ---------- */
async function save() {
  if (saving.value) return
  const t = title.value.trim()
  const c = content.value.trim()
  if (!t) return ElMessage.warning('请填写标题')
  if (mode.value === 'article' && t.length < 2) return ElMessage.warning('标题至少 2 个字')
  if (!c) return ElMessage.warning('请填写正文')
  saving.value = true
  try {
    const post = await createPost({
      category: category.value || '分享',
      title: t,
      content: c,
      images: images.value,
    })
    ElMessage.success('发布成功')
    clearDraft()
    saving.value = false
    emit('published', post)
    closing.value = true
    window.setTimeout(() => emit('closed'), 260)
  } catch {
    ElMessage.error('发布失败，请稍后再试')
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => window.clearTimeout(draftTimer))
</script>

<style scoped>
/* 整页覆盖：必须压过底部胶囊（1000）与改密提醒浮层（1900）——
   编辑态下这两块都是干扰，写长文时不能被一条横幅切断底栏 */
.pcp {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  background: #fff;
  color: #1a1a2e;
  transform: translateX(100%);
  transition: transform .26s cubic-bezier(.32, .72, 0, 1);
  will-change: transform;
}
.pcp.is-closing { transform: translateX(100%); }
/* 挂载后由 JS 打开展示位：transform 从 100% 收到 0，与子页右滑进场同节奏 */
.pcp:not(.is-closing) { animation: pcp-in .26s cubic-bezier(.32, .72, 0, 1) forwards; }
@keyframes pcp-in { from { transform: translateX(100%); } to { transform: translateX(0); } }
.pcp.is-closing { animation: pcp-out .26s cubic-bezier(.4, 0, 1, 1) forwards; }
@keyframes pcp-out { from { transform: translateX(0); } to { transform: translateX(100%); } }

/* ===== 顶栏 ===== */
.pcp-bar {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: 56px 1fr 76px;
  align-items: center;
  height: 52px;
  padding: 0 6px;
  border-bottom: 1px solid rgba(15, 23, 42, .06);
  background: #fff;
  flex-shrink: 0;
}
.pcp-back {
  width: 44px; height: 44px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 0; background: none; color: #1a1a2e; cursor: pointer;
  border-radius: 50%;
}
.pcp-back:active { background: rgba(15, 23, 42, .06); }

.pcp-mode { position: relative; justify-self: center; }
.pcp-mode-btn {
  display: inline-flex; align-items: center; gap: 2px;
  border: 0; background: none; cursor: pointer;
  font-size: 16px; font-weight: 600; color: #1a1a2e;
  padding: 6px 4px;
}
.pcp-mode-btn svg { transition: transform .18s ease; }
.pcp-mode-btn svg.flip { transform: rotate(180deg); }

.pcp-mode-list {
  position: absolute; top: calc(100% + 6px); left: 50%;
  transform: translateX(-50%);
  width: 216px; margin: 0; padding: 6px;
  list-style: none; background: #fff; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, .16);
  z-index: 20;
}
.pcp-mode-list li {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 10px; border-radius: 8px; cursor: pointer;
}
.pcp-mode-list li b { font-size: 14px; font-weight: 600; }
.pcp-mode-list li span { font-size: 11px; color: #98a2b3; }
.pcp-mode-list li.active { background: rgba(64, 158, 255, .1); }
.pcp-mode-list li.active b { color: #2f7dd1; }
.pcp-mask { position: fixed; inset: 0; z-index: 2; }

.pcp-publish {
  justify-self: end;
  min-width: 62px; height: 32px;
  padding: 0 14px;
  border: 0; border-radius: 16px;
  background: #e5e6eb; color: #fff;
  font-size: 14px; font-weight: 600;
  cursor: default;
  transition: background .18s ease, transform .12s ease;
}
.pcp-publish.is-ready { background: #1d2129; cursor: pointer; }
.pcp-publish.is-ready:active { transform: scale(.96); }
.pcp-publish.is-saving { opacity: .7; }

/* ===== 编辑区 ===== */
.pcp-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 16px 8px;
  -webkit-overflow-scrolling: touch;
}

.pcp-images {
  display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start;
  margin-bottom: 14px;
}
.pcp-thumb {
  position: relative;
  width: 96px; height: 96px;
  border-radius: 10px; overflow: hidden;
  background: #f4f5f7;
  flex-shrink: 0;
}
.pcp-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.pcp-thumb--add {
  border: 0; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  color: #b6bcc8; background: #f4f5f7;
}
.pcp-thumb--add:active { background: #eceef2; }
.pcp-thumb-del {
  position: absolute; top: 4px; right: 4px;
  width: 20px; height: 20px; border-radius: 50%;
  border: 0; background: rgba(15, 23, 42, .55); color: #fff;
  font-size: 14px; line-height: 18px; cursor: pointer;
}
.pcp-thumb--loading { display: inline-flex; align-items: center; justify-content: center; }
.pcp-spinner {
  width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid rgba(15, 23, 42, .12); border-top-color: #1d2129;
  animation: pcp-spin .8s linear infinite;
}
@keyframes pcp-spin { to { transform: rotate(360deg); } }

.pcp-images-tip {
  display: inline-flex; align-items: center; gap: 4px;
  align-self: flex-end;
  padding: 3px 8px; border-radius: 6px;
  font-size: 11px; color: #8b93a3; background: #f4f5f7;
}

.pcp-title-row { display: flex; align-items: center; gap: 8px; }
.pcp-title {
  flex: 1; min-width: 0;
  border: 0; outline: none; background: none;
  font-size: 17px; font-weight: 600; color: #1a1a2e;
  padding: 6px 0;
}
.pcp-title::placeholder { color: #c2c8d2; font-weight: 500; }
.pcp-counter { font-size: 11px; color: #b6bcc8; flex-shrink: 0; }
.pcp-counter.is-warn { color: #f56c6c; }

.pcp-hint {
  margin: 2px 0 6px;
  font-size: 12px; line-height: 1.7; color: #98a2b3;
}

.pcp-content {
  width: 100%;
  min-height: 240px;
  border: 0; outline: none; resize: none; background: none;
  font-size: 15px; line-height: 1.75; color: #2b2f3a;
  padding: 6px 0;
  font-family: inherit;
}
.pcp-content::placeholder { color: #c2c8d2; }
.pcp-body-counter { text-align: right; font-size: 11px; color: #c2c8d2; padding-bottom: 8px; }

/* ===== 底栏 ===== */
.pcp-foot {
  flex-shrink: 0;
  padding: 8px 16px calc(8px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid rgba(15, 23, 42, .06);
  background: #fff;
}
.pcp-topic {
  display: inline-flex; align-items: center; gap: 2px;
  height: 30px; padding: 0 10px;
  border: 0; border-radius: 6px;
  background: #f4f5f7; color: #5b6474;
  font-size: 12px; cursor: pointer;
}
.pcp-topic-plus { font-size: 14px; line-height: 1; }

.pcp-tools { display: flex; align-items: center; gap: 4px; margin-top: 8px; }
.pcp-tool {
  width: 40px; height: 40px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 0; border-radius: 8px; background: none;
  color: #6b7280; cursor: pointer;
}
.pcp-tool:active { background: #f4f5f7; }

.pcp-emoji {
  position: absolute;
  left: 12px; bottom: calc(96px + env(safe-area-inset-bottom, 0px));
  right: 12px;
  display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px;
  padding: 10px;
  background: #fff; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, .16);
  z-index: 5;
}
.pcp-emoji-item {
  height: 34px; border: 0; background: none; border-radius: 8px;
  font-size: 20px; line-height: 1; cursor: pointer;
}
.pcp-emoji-item:active { background: #f4f5f7; }

/* 分区面板 */
.pcp-sheet-mask {
  position: absolute; inset: 0; z-index: 10;
  background: rgba(15, 23, 42, .35);
  display: flex; align-items: flex-end;
}
.pcp-sheet {
  width: 100%;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 14px 16px calc(18px + env(safe-area-inset-bottom, 0px));
}
.pcp-sheet-head {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 15px; font-weight: 600; margin-bottom: 12px;
}
.pcp-sheet-head button { border: 0; background: none; font-size: 20px; color: #b6bcc8; cursor: pointer; }
.pcp-cats { display: flex; flex-wrap: wrap; gap: 8px; }
.pcp-cat {
  height: 34px; padding: 0 16px;
  border: 1px solid rgba(15, 23, 42, .1); border-radius: 17px;
  background: #fff; color: #4b5563; font-size: 13px; cursor: pointer;
}
.pcp-cat.active { border-color: #1d2129; background: #1d2129; color: #fff; }

/* ===== 桌面端：收成居中的编辑面板 ===== */
@media (min-width: 768px) {
  .pcp {
    align-items: center;
    background: rgba(15, 23, 42, .32);
    animation: none !important;
    transform: none;
  }
  .pcp-inner-fallback { display: contents; }
  .pcp > *:not(.pcp-mask) { width: 640px; }
  .pcp-bar { border-radius: 14px 14px 0 0; margin-top: 6vh; }
  .pcp-body { max-height: calc(78vh - 150px); background: #fff; }
  .pcp-foot { border-radius: 0 0 14px 14px; margin-bottom: 6vh; box-shadow: 0 18px 48px rgba(15, 23, 42, .18); }
  .pcp-emoji { position: fixed; left: 50%; transform: translateX(-50%); width: 560px; bottom: 22vh; }
  .pcp-sheet-mask { align-items: center; justify-content: center; background: rgba(15, 23, 42, .45); }
  .pcp-sheet { width: 420px; border-radius: 14px; }
}
</style>
