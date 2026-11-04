<template>
  <div class="files-page">
    <!-- 移动端吸顶子页头；桌面端学生布局有侧边栏，不渲染该头，标题由下方 .files-title 承担 -->
    <SubPageHeader title="我的文件" sub="聊天里发过的图片 / 文档 / 语音" fallback="/student/messages" />

    <div class="files-inner">
      <h2 class="files-title">我的文件</h2>

      <div class="files-head">
        <el-input
          v-model="keyword"
          placeholder="搜索文件名"
          clearable
          :prefix-icon="Search"
          @input="onSearch"
        />
        <div class="files-filter" role="tablist" aria-label="文件类型">
          <button
            v-for="f in FILE_TYPE_FILTERS"
            :key="f.key"
            type="button"
            role="tab"
            :aria-selected="fileTypeFilter === f.key"
            class="files-filter-item"
            :class="{ active: fileTypeFilter === f.key }"
            @click="setFileTypeFilter(f.key)"
          >{{ f.label }}</button>
        </div>
      </div>

      <div v-if="loading" class="files-state">
        <el-icon class="is-loading" :size="22"><Loading /></el-icon>
        <span>加载中…</span>
      </div>
      <div v-else-if="!files.length" class="files-state">
        <el-icon :size="40" class="files-state-ico"><Document /></el-icon>
        <span>{{ keyword.trim() ? '未找到匹配的文件' : '暂无聊天文件' }}</span>
        <p class="files-state-hint">在单聊或群聊里发过 / 收到的文件会汇总在这里</p>
      </div>
      <div v-else class="files-list">
        <button
          v-for="f in files"
          :key="f.id"
          type="button"
          class="file-row"
          @click="openFile(f)"
        >
          <span class="file-row-thumb" :class="`t-${f.file_type}`">
            <img v-if="f.file_type === 'image'" :src="f.url" alt="" loading="lazy" />
            <el-icon v-else :size="18">
              <Microphone v-if="f.file_type === 'voice'" />
              <Document v-else />
            </el-icon>
          </span>
          <span class="file-row-main">
            <span class="file-row-name">
              <template v-if="f.file_type === 'voice'">语音消息 · {{ f.duration || 1 }}″</template>
              <template v-else>{{ f.name || '未命名文件' }}</template>
            </span>
            <span class="file-row-meta">
              <span class="file-row-source" @click.stop="openSession(f)">
                {{ f.is_group ? '群 · ' : '' }}{{ f.session_name || '会话' }}
              </span>
              <span>{{ f.sender_name }}</span>
              <span>{{ formatDate(f.created_at) }}</span>
            </span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Loading, Microphone, Search } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { getSharedFiles, type SharedFile } from '@/api/messages'
import { parseServerTime } from '@/utils/datetime'

/**
 * 我的文件（跨会话文件汇总）。
 *
 * 从旧「工作台」页抽出来的独立页：工作台页签在 v5 已被消息页取代、整页下线，
 * 但这张「聊天里发过的文件 / 图片 / 语音」的汇总表还在用（消息页 ＋ →「我的文件」），
 * 于是单独给它一个地址 /student/files，而不是继续挂在一张没人维护的旧页里。
 */

const router = useRouter()

const files = ref<SharedFile[]>([])
const loading = ref(false)
const keyword = ref('')
const fileTypeFilter = ref<'' | 'file' | 'image' | 'voice'>('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const FILE_TYPE_FILTERS = [
  { key: '' as const, label: '全部' },
  { key: 'image' as const, label: '图片' },
  { key: 'file' as const, label: '文档' },
  { key: 'voice' as const, label: '语音' },
]

async function load() {
  if (loading.value) return
  loading.value = true
  try {
    const params: { keyword?: string; file_type?: string } = {}
    const kw = keyword.value.trim()
    if (kw) params.keyword = kw
    if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
    const res = await getSharedFiles(params)
    files.value = res.items || []
  } catch {
    files.value = []
  } finally {
    loading.value = false
  }
}

/** 输入防抖 300ms：边打边搜，但不必每个字符都打一次接口 */
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { void load() }, 300)
}

function setFileTypeFilter(key: '' | 'file' | 'image' | 'voice') {
  fileTypeFilter.value = key
  void load()
}

/** 打开文件：图片新窗口预览，其余直接下载（与消息气泡内的点击行为一致） */
function openFile(f: SharedFile) {
  const a = document.createElement('a')
  a.href = f.url
  a.rel = 'noopener'
  if (f.file_type === 'image') a.target = '_blank'
  else a.download = f.name || '文件'
  a.click()
}

/** 点来源会话 → 回到消息页并打开那条会话（消息页按 ?chat= 认路由参数） */
function openSession(f: SharedFile) {
  void router.push({ path: '/student/messages', query: { chat: f.session_key } })
}

/** 服务端时间戳按 UTC 口径解析，避免「刚发的文件显示成 8 小时前」 */
function formatDate(iso: string) {
  const ts = parseServerTime(iso)
  if (Number.isNaN(ts)) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(load)
onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.files-page {
  min-height: 100%;
  background: var(--dt-bg, #f5f6f7);
}

.files-inner {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px 16px 96px;
}

/* 桌面端标题：移动端由 SubPageHeader 承担，这里隐藏避免重复 */
.files-title {
  margin: 0 0 14px;
  font-size: 20px;
  font-weight: 680;
  letter-spacing: -0.2px;
  color: var(--dt-text, #1f2430);
}
@media (max-width: 767px) {
  .files-title { display: none; }
  .files-inner { padding: 12px 12px 96px; }
}

.files-head {
  position: relative;
  z-index: 2;
}

.files-filter {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 14px 0 12px;
}

.files-filter-item {
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  line-height: 1;
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--dt-fill-2, #f2f3f5);
  color: var(--dt-text-tertiary);
}

.files-filter-item.active {
  background: var(--dt-primary-soft);
  color: var(--dt-primary-strong);
  font-weight: 600;
}

.files-list {
  background: var(--dt-surface, #fff);
  border-radius: var(--dt-radius, 12px);
  overflow: hidden;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.file-row + .file-row {
  box-shadow: inset 0 1px 0 var(--dt-border-weak, #f0f1f3);
}

.file-row:active {
  background: var(--dt-surface-press, #f5f6f7);
}

.file-row-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--dt-fill-2, #f2f3f5);
  color: var(--dt-primary-strong);
}

.file-row-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-row-thumb.t-voice {
  color: var(--dt-success, #34c759);
}

.file-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-row-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--dt-text, #1f2430);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-row-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--dt-text-quiet);
}

.file-row-source {
  max-width: 45%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: var(--dt-primary-strong);
}

.files-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 64px 16px;
  color: var(--dt-text-quiet);
  font-size: 13px;
}

.files-state-ico {
  color: var(--dt-text-quiet);
}

.files-state-hint {
  margin: 0;
  font-size: 12px;
  color: var(--dt-text-quiet);
}
</style>
