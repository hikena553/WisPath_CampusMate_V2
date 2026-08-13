<template>
  <div class="lf-bubble" @click="openPanel" @mouseenter="showTooltip = true" @mouseleave="showTooltip = false">
    <transition name="tooltip-fade">
      <div v-if="showTooltip" class="lf-tooltip">失物招领</div>
    </transition>
    <el-badge :value="recentCount" :hidden="recentCount === 0" :offset="[-4, -4]">
      <div class="lf-bubble-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
          <path d="M11 8v2"/>
          <path d="M11 14h.01"/>
        </svg>
      </div>
    </el-badge>

    <!-- 失物招领完整面板弹窗 -->
    <el-dialog v-model="panelVisible" title="失物招领" width="680px" destroy-on-close>
      <div class="lf-full-panel">
        <div class="lf-tabs">
          <span v-for="t in tabs" :key="t.key" :class="['lf-tab', { active: activeType === t.key }]" @click="activeType = t.key">
            {{ t.label }}
          </span>
          <el-button type="primary" size="small" class="lf-publish-btn" @click="openCreate">发布</el-button>
        </div>

        <div v-if="fullLoading" class="lf-empty">加载中...</div>
        <div v-else-if="!fullItems.length" class="lf-empty">暂无{{ activeType === 'all' ? '' : tabs.find(t => t.key === activeType)?.label }}信息</div>

        <div v-else class="lf-list">
          <div v-for="it in fullItems" :key="it.id" class="lf-item" @click="openDetail(it)">
            <div class="lf-item-main">
              <img v-if="it.image_url" :src="it.image_url" class="lf-thumb" loading="lazy" />
              <div class="lf-item-body">
                <div class="lf-item-top">
                  <el-tag :type="it.type === 'lost' ? 'danger' : 'success'" size="small" effect="plain">
                    {{ it.type === 'lost' ? '失物' : '招领' }}
                  </el-tag>
                  <el-tag v-if="it.status === 'claimed'" type="warning" size="small" effect="plain">已认领</el-tag>
                  <el-tag v-else-if="it.status === 'closed'" type="info" size="small" effect="plain">已结束</el-tag>
                </div>
                <div class="lf-title">{{ it.title }}</div>
                <div class="lf-meta">
                  <span>{{ it.location || '地点不详' }}</span>
                  <span>{{ formatDateFull(it.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 发布对话框 -->
      <el-dialog v-model="createVisible" title="发布信息" width="520px" append-to-body>
        <el-form ref="formRef" :model="form" label-width="80px" :rules="formRules">
          <el-form-item label="类型" prop="type">
            <el-radio-group v-model="form.type">
              <el-radio value="lost">寻物启事</el-radio>
              <el-radio value="found">失物招领</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="物品名称" prop="title">
            <el-input v-model="form.title" placeholder="如：黑色钱包 / 蓝色水杯" maxlength="50" show-word-limit />
          </el-form-item>
          <el-form-item label="详细描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="物品特征、品牌、内装物品等" />
          </el-form-item>
          <el-form-item label="物品图片">
            <div class="lf-upload">
              <el-upload
                :show-file-list="false"
                :before-upload="handleImageUpload"
                accept="image/*"
                class="lf-upload-inner"
              >
                <div v-if="form.image_url" class="lf-upload-preview">
                  <img :src="form.image_url" class="lf-upload-img" />
                  <div class="lf-upload-mask">点击更换</div>
                </div>
                <div v-else class="lf-upload-placeholder">
                  <el-icon :size="24"><Plus /></el-icon>
                  <span>上传图片</span>
                </div>
              </el-upload>
              <el-button v-if="form.image_url" type="danger" link size="small" class="lf-upload-remove" @click="removeImage">移除图片</el-button>
              <div class="lf-upload-hint">支持 jpg/png 等格式，上传实物照片可帮助他人更快辨识</div>
            </div>
          </el-form-item>
          <el-form-item label="地点">
            <el-input v-model="form.location" placeholder="丢失/拾取地点，如：食堂二楼" />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="form.contact" placeholder="手机号/QQ/微信" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">发布</el-button>
        </template>
      </el-dialog>

      <!-- 详情对话框 -->
      <el-dialog v-model="detailVisible" :title="detailItem?.title || '详情'" width="640px" append-to-body class="lf-detail-dialog">
        <template v-if="detailItem">
          <div class="lf-detail-header">
            <el-tag :type="detailItem.type === 'lost' ? 'danger' : 'success'" size="small">{{ detailItem.type === 'lost' ? '失物' : '招领' }}</el-tag>
            <el-tag :type="statusTagType(detailItem.status)" size="small" effect="plain">{{ statusLabel(detailItem.status) }}</el-tag>
            <span class="lf-detail-user">{{ detailItem.user_name }} · {{ formatDateFull(detailItem.created_at) }}</span>
          </div>

          <div class="lf-detail-main">
            <div v-if="detailItem.image_url" class="lf-detail-img" @click.stop>
              <el-image
                :src="detailItem.image_url"
                :preview-src-list="[detailItem.image_url]"
                :initial-index="0"
                fit="contain"
                class="lf-detail-img-el"
              />
            </div>

            <div class="lf-detail-info">
              <el-descriptions :column="1" :label-width="72" class="lf-detail-desc">
                <el-descriptions-item label="物品名称">{{ detailItem.title }}</el-descriptions-item>
                <el-descriptions-item v-if="detailItem.description" label="描述">{{ detailItem.description }}</el-descriptions-item>
                <el-descriptions-item label="地点">{{ detailItem.location || '-' }}</el-descriptions-item>
                <el-descriptions-item label="联系方式">{{ detailItem.contact || '-' }}</el-descriptions-item>
              </el-descriptions>

              <div v-if="detailItem.user_id === auth.user?.id && detailItem.status === 'open'" class="lf-detail-actions">
                <el-button type="warning" size="small" @click="updateStatus('claimed')">标记为已认领</el-button>
                <el-button type="danger" size="small" plain @click="handleDelete">删除</el-button>
              </div>

              <div class="lf-comments">
                <div class="lf-comments-title">留言（{{ detailItem.comments?.length || 0 }}）</div>
                <div class="lf-comments-list">
                  <div v-if="!detailItem.comments?.length" class="lf-comments-empty">暂无留言，来说点什么吧</div>
                  <div v-for="c in detailItem.comments" :key="c.id" class="lf-comment">
                    <div class="lf-comment-avatar" :style="{ background: avatarColor(c.user_name) }">{{ avatarText(c.user_name) }}</div>
                    <div class="lf-comment-main">
                      <div class="lf-comment-head">
                        <span class="lf-comment-user">{{ c.user_name || '匿名用户' }}</span>
                        <span class="lf-comment-date">{{ formatDateFull(c.created_at) }}</span>
                      </div>
                      <div class="lf-comment-bubble">{{ c.content }}</div>
                    </div>
                  </div>
                </div>
                <div class="lf-comment-input">
                  <el-input v-model="comment" placeholder="留言联系..." size="small" maxlength="200" @keyup.enter="submitComment" />
                  <el-button type="primary" size="small" :disabled="!comment.trim()" @click="submitComment">发送</el-button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-dialog>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getLostFoundItems, getLostFoundItem, createLostFoundItem, updateLostFoundStatus, deleteLostFoundItem, createLostFoundComment } from '@/api/lost_found'
import { uploadFile } from '@/api/upload'
import type { LostFoundItem } from '@/types'

const auth = useAuthStore()

const STORAGE_KEY = 'lf_last_viewed'
const recentCount = ref(0)
const showTooltip = ref(false)

function getLastViewed(): number {
  const val = localStorage.getItem(STORAGE_KEY)
  return val ? Number(val) : 0
}

function markViewed() {
  localStorage.setItem(STORAGE_KEY, String(Date.now()))
}

const panelVisible = ref(false)
const tabs = [
  { key: 'all', label: '全部' },
  { key: 'lost', label: '失物' },
  { key: 'found', label: '招领' },
]
const activeType = ref('all')
const fullItems = ref<LostFoundItem[]>([])
const fullLoading = ref(false)

const createVisible = ref(false)
const submitting = ref(false)
const form = reactive({ type: 'lost', title: '', description: '', location: '', contact: '', image_url: '' })
const formRef = ref<any>()
const formRules = {
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  title: [{ required: true, message: '请填写物品名称', trigger: 'blur' }],
}

const detailVisible = ref(false)
const detailItem = ref<LostFoundItem | null>(null)
const comment = ref('')

async function loadRecent() {
  try {
    const items = await getLostFoundItems({})
    const lastViewed = getLastViewed()
    if (!lastViewed) {
      recentCount.value = 0
    } else {
      recentCount.value = items.filter((it: LostFoundItem) => new Date(it.created_at).getTime() > lastViewed).length
    }
  } catch { /* ignore */ }
}

async function loadFull() {
  fullLoading.value = true
  try {
    const params = activeType.value === 'all' ? {} : { type: activeType.value }
    fullItems.value = await getLostFoundItems(params)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    fullLoading.value = false
  }
}

function openPanel() {
  panelVisible.value = true
  loadFull()
  markViewed()
  recentCount.value = 0
}

watch(activeType, () => loadFull())

function openCreate() {
  Object.assign(form, { type: 'lost', title: '', description: '', location: '', contact: '', image_url: '' })
  createVisible.value = true
}

async function handleImageUpload(file: File) {
  try {
    const res = await uploadFile(file)
    form.image_url = res.url
    ElMessage.success('图片上传成功')
  } catch {
    ElMessage.error('图片上传失败')
  }
  return false
}

function removeImage() {
  form.image_url = ''
}

async function submit() {
  if (formRef.value) {
    try { await formRef.value.validate() } catch { return }
  }
  submitting.value = true
  try {
    await createLostFoundItem({ ...form })
    ElMessage.success('发布成功')
    createVisible.value = false
    await loadFull()
    await loadRecent()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  } finally {
    submitting.value = false
  }
}

async function openDetail(it: LostFoundItem) {
  detailItem.value = await getLostFoundItem(it.id)
  detailVisible.value = true
}

async function updateStatus(status: string) {
  if (!detailItem.value) return
  try {
    await updateLostFoundStatus(detailItem.value.id, status)
    ElMessage.success('已更新')
    detailVisible.value = false
    await loadFull()
    await loadRecent()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function handleDelete() {
  if (!detailItem.value) return
  try {
    await ElMessageBox.confirm('确定删除这条信息吗？', '确认删除', { type: 'warning' })
  } catch { return }
  try {
    await deleteLostFoundItem(detailItem.value.id)
    ElMessage.success('已删除')
    detailVisible.value = false
    await loadFull()
    await loadRecent()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function submitComment() {
  if (!detailItem.value || !comment.value.trim()) return
  try {
    await createLostFoundComment(detailItem.value.id, comment.value.trim())
    comment.value = ''
    detailItem.value = await getLostFoundItem(detailItem.value.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '留言失败')
  }
}

function formatDateFull(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function statusLabel(s: string) {
  const m: Record<string, string> = { open: '进行中', claimed: '已认领', closed: '已结束' }
  return m[s] || s
}

function statusTagType(s: string) {
  const m: Record<string, string> = { open: 'primary', claimed: 'warning', closed: 'info' }
  return m[s] || 'info'
}

const AVATAR_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9c27b0', '#00bcd4', '#ff9800', '#8e44ad']

function avatarColor(name: string | null): string {
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) {
    hash = (hash * 31 + (name as string).charCodeAt(i)) % 997
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

function avatarText(name: string | null): string {
  return (name || '用').charAt(0)
}

onMounted(loadRecent)
</script>

<style scoped>
.lf-bubble {
  position: fixed;
  right: 32px;
  bottom: 32px;
  z-index: 1000;
  cursor: pointer;
}
.lf-bubble-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.4);
  transition: all 0.3s;
}
.lf-bubble:hover .lf-bubble-icon {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.5);
}

.lf-tooltip {
  position: absolute;
  right: 60px;
  top: 50%;
  transform: translateY(-50%);
  background: linear-gradient(135deg, #303133 0%, #4a4a4a 100%);
  color: white;
  padding: 10px 18px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  pointer-events: none;
}
.lf-tooltip::after {
  content: '';
  position: absolute;
  right: -8px;
  top: 50%;
  transform: translateY(-50%);
  border: 5px solid transparent;
  border-left-color: #303133;
}

.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(8px);
}

/* 面板样式 */
.lf-full-panel {
  min-height: 400px;
}
.lf-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
}
.lf-tab {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 4px 14px;
  border-radius: 14px;
  cursor: pointer;
  background: #f5f7fa;
  transition: all 0.15s;
}
.lf-tab.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}
.lf-publish-btn {
  margin-left: auto;
}
.lf-empty {
  text-align: center;
  color: var(--text-placeholder);
  padding: 40px 0;
  font-size: 14px;
}
.lf-list {
  max-height: 400px;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.lf-list::-webkit-scrollbar {
  display: none;
}
.lf-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid #f0f0f0;
  margin-bottom: 8px;
}
.lf-item:hover {
  background: #f5f7fa;
  border-color: #409eff;
}
.lf-item-main {
  display: flex;
  gap: 12px;
  align-items: center;
}
.lf-thumb {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  background: #f5f7fa;
}
.lf-item-body {
  flex: 1;
  min-width: 0;
}
.lf-item-top {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}
.lf-title {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 4px;
}
.lf-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-placeholder);
}

/* 详情样式 */
.lf-detail-dialog :deep(.el-dialog__body) {
  max-height: 72vh;
  overflow-y: auto;
  padding-top: 8px;
}
.lf-detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.lf-detail-user {
  font-size: 13px;
  color: var(--text-secondary);
}
.lf-detail-main {
  display: flex;
  gap: 16px;
  align-items: stretch;
}
.lf-detail-img {
  width: 220px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #f0f0f0;
  background: #fafafa;
}
.lf-detail-img :deep(.el-image) {
  width: 100%;
  height: 100%;
  min-height: 150px;
  display: block;
}

/* 图片上传样式 */
.lf-upload {
  width: 100%;
}
.lf-upload-inner {
  display: block;
}
.lf-upload :deep(.el-upload) {
  width: 100%;
}
.lf-upload-preview {
  position: relative;
  width: 100%;
  height: 180px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px dashed #dcdfe6;
  cursor: pointer;
}
.lf-upload-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.lf-upload-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 13px;
  opacity: 0;
  transition: opacity 0.2s;
}
.lf-upload-preview:hover .lf-upload-mask {
  opacity: 1;
}
.lf-upload-placeholder {
  width: 100%;
  height: 180px;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  background: #fafafa;
  color: var(--text-placeholder);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.lf-upload-placeholder:hover {
  border-color: #409eff;
  color: #409eff;
}
.lf-upload-remove {
  margin-top: 6px;
}
.lf-upload-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-placeholder);
}
.lf-detail-desc {
  margin-bottom: 12px;
}
.lf-detail-actions {
  margin-bottom: 12px;
}
.lf-comments {
  display: flex;
  flex-direction: column;
}
.lf-comments-list {
  flex: 1;
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
}
.lf-comments-empty {
  text-align: center;
  color: var(--text-placeholder);
  padding: 14px 0;
  font-size: 13px;
}
.lf-comments-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}
.lf-comment {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.lf-comment-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
}
.lf-comment-main {
  flex: 1;
  min-width: 0;
}
.lf-comment-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.lf-comment-user {
  color: #409eff;
  font-size: 12px;
}
.lf-comment-date {
  font-size: 11px;
  color: var(--text-placeholder);
}
.lf-comment-bubble {
  background: #f5f7fa;
  border-radius: 4px 10px 10px 10px;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}
.lf-comment-input {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
