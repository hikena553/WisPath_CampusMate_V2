<template>
  <div class="lf-panel">
    <div class="lf-header">
      <h3>失物招领</h3>
      <el-button type="primary" size="small" @click="openCreate">发布</el-button>
    </div>

    <div class="lf-tabs">
      <span v-for="t in tabs" :key="t.key" :class="['lf-tab', { active: activeType === t.key }]" @click="activeType = t.key">
        {{ t.label }}
      </span>
    </div>

    <div v-if="loading" class="lf-empty">加载中...</div>
    <div v-else-if="!items.length" class="lf-empty">暂无{{ activeType === 'all' ? '' : tabs.find(t => t.key === activeType)?.label }}信息</div>

    <div v-else class="lf-list">
      <div v-for="it in items" :key="it.id" class="lf-item" @click="openDetail(it)">
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
              <span>{{ formatDate(it.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="createVisible" title="发布信息" width="520px">
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

    <el-dialog v-model="detailVisible" :title="detail?.title || '详情'" width="640px" class="lf-detail-dialog">
      <template v-if="detail">
        <div class="lf-detail-header">
          <el-tag :type="detail.type === 'lost' ? 'danger' : 'success'" size="small">{{ detail.type === 'lost' ? '失物' : '招领' }}</el-tag>
          <el-tag :type="statusTagType(detail.status)" size="small" effect="plain">{{ statusLabel(detail.status) }}</el-tag>
          <span class="lf-detail-user">{{ detail.user_name }} · {{ formatDate(detail.created_at) }}</span>
        </div>

        <div class="lf-detail-main">
          <div v-if="detail.image_url" class="lf-detail-img" @click.stop>
            <el-image
              :src="detail.image_url"
              :preview-src-list="[detail.image_url]"
              :initial-index="0"
              fit="contain"
              class="lf-detail-img-el"
            />
          </div>

          <div class="lf-detail-info">
            <el-descriptions :column="1" :label-width="72" class="lf-detail-desc">
              <el-descriptions-item label="物品名称">{{ detail.title }}</el-descriptions-item>
              <el-descriptions-item v-if="detail.description" label="描述">{{ detail.description }}</el-descriptions-item>
              <el-descriptions-item label="地点">{{ detail.location || '-' }}</el-descriptions-item>
              <el-descriptions-item label="联系方式">{{ detail.contact || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div v-if="detail.user_id === auth.user?.id && detail.status === 'open'" class="lf-detail-actions">
              <el-button type="warning" size="small" @click="updateStatus('claimed')">标记为已认领</el-button>
              <el-button type="danger" size="small" plain @click="handleDelete">删除</el-button>
            </div>

            <div class="lf-comments">
              <div class="lf-comments-title">留言（{{ detail.comments?.length || 0 }}）</div>
              <div class="lf-comments-list">
                <div v-if="!detail.comments?.length" class="lf-comments-empty">暂无留言，来说点什么吧</div>
                <div v-for="c in detail.comments" :key="c.id" class="lf-comment">
                  <div class="lf-comment-avatar" :style="{ background: avatarColor(c.user_name) }">{{ avatarText(c.user_name) }}</div>
                  <div class="lf-comment-main">
                    <div class="lf-comment-head">
                      <span class="lf-comment-user">{{ c.user_name || '匿名用户' }}</span>
                      <span class="lf-comment-date">{{ formatDate(c.created_at) }}</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getLostFoundItems, getLostFoundItem, createLostFoundItem, updateLostFoundStatus, deleteLostFoundItem, createLostFoundComment } from '@/api/lost_found'
import { uploadFile } from '@/api/upload'
import type { LostFoundItem } from '@/types'

const auth = useAuthStore()

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'lost', label: '失物' },
  { key: 'found', label: '招领' },
]
const activeType = ref('all')
const items = ref<LostFoundItem[]>([])
const loading = ref(false)
const submitting = ref(false)
const formRef = ref<any>()
const formRules = {
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  title: [{ required: true, message: '请填写物品名称', trigger: 'blur' }],
}

const createVisible = ref(false)
const detailVisible = ref(false)
const detail = ref<LostFoundItem | null>(null)
const comment = ref('')

const form = reactive({ type: 'lost', title: '', description: '', location: '', contact: '', image_url: '' })

async function load() {
  loading.value = true
  try {
    const params = activeType.value === 'all' ? {} : { type: activeType.value }
    items.value = await getLostFoundItems(params)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

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
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  } finally {
    submitting.value = false
  }
}

async function openDetail(it: LostFoundItem) {
  detail.value = await getLostFoundItem(it.id)
  detailVisible.value = true
}

async function updateStatus(status: string) {
  if (!detail.value) return
  try {
    await updateLostFoundStatus(detail.value.id, status)
    ElMessage.success('已更新')
    detailVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function handleDelete() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm('确定删除这条信息吗？', '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteLostFoundItem(detail.value.id)
    ElMessage.success('已删除')
    detailVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function submitComment() {
  if (!detail.value || !comment.value.trim()) return
  try {
    await createLostFoundComment(detail.value.id, comment.value.trim())
    comment.value = ''
    detail.value = await getLostFoundItem(detail.value.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '留言失败')
  }
}

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日`
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

onMounted(load)
</script>

<style scoped>
.lf-panel {
  display: flex; flex-direction: column; height: 100%; min-height: 260px;
  background: var(--bg-card); border-radius: 10px; padding: 14px;
  box-shadow: var(--shadow-md); overflow: hidden;
}
.lf-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.lf-header h3 { margin: 0; font-size: 14px; }
.lf-tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.lf-tab {
  font-size: 12px; color: var(--text-secondary); padding: 3px 12px;
  border-radius: 12px; cursor: pointer; background: #f5f7fa; transition: all .15s;
}
.lf-tab.active { background: #ecf5ff; color: #409eff; font-weight: 600; }
.lf-empty { text-align: center; color: var(--text-placeholder); padding: 20px 0; font-size: 13px; }
.lf-list { flex: 1; overflow-y: auto; scrollbar-width: none; -ms-overflow-style: none; }
.lf-list::-webkit-scrollbar { display: none; }
.lf-item {
  padding: 10px; border-radius: 8px; cursor: pointer; transition: all .15s;
  border: 1px solid transparent; margin-bottom: 6px;
}
.lf-item:hover { background: #f5f7fa; }
.lf-item-main { display: flex; gap: 10px; align-items: center; }
.lf-thumb { width: 48px; height: 48px; border-radius: 6px; object-fit: cover; flex-shrink: 0; background: #f5f7fa; }
.lf-item-body { flex: 1; min-width: 0; }
.lf-item-top { display: flex; gap: 4px; align-items: center; margin-bottom: 4px; }
.lf-title { font-size: 13px; color: var(--text-primary); font-weight: 500; margin-bottom: 4px; }
.lf-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-placeholder); }
.lf-detail-dialog :deep(.el-dialog__body) { max-height: 72vh; overflow-y: auto; padding-top: 8px; }
.lf-detail-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.lf-detail-user { font-size: 12px; color: var(--text-secondary); }
.lf-detail-main { display: flex; gap: 16px; align-items: stretch; }
.lf-detail-img {
  width: 220px; flex-shrink: 0; border-radius: 8px; overflow: hidden;
  border: 1px solid #f0f0f0; background: #fafafa;
}
.lf-detail-img :deep(.el-image) { width: 100%; height: 100%; min-height: 150px; display: block; }
.lf-detail-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.lf-detail-desc { margin-bottom: 12px; }

/* 图片上传样式 */
.lf-upload { width: 100%; }
.lf-upload-inner { display: block; }
.lf-upload :deep(.el-upload) { width: 100%; }
.lf-upload-preview {
  position: relative; width: 100%; height: 160px; border-radius: 8px; overflow: hidden;
  border: 1px dashed #dcdfe6; cursor: pointer;
}
.lf-upload-img { width: 100%; height: 100%; object-fit: cover; }
.lf-upload-mask {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.45); color: #fff; font-size: 13px; opacity: 0; transition: opacity .2s;
}
.lf-upload-preview:hover .lf-upload-mask { opacity: 1; }
.lf-upload-placeholder {
  width: 100%; height: 160px; border-radius: 8px; border: 1px dashed #dcdfe6; background: #fafafa;
  color: var(--text-placeholder); display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 6px; font-size: 13px; cursor: pointer; transition: all .2s;
}
.lf-upload-placeholder:hover { border-color: #409eff; color: #409eff; }
.lf-upload-remove { margin-top: 6px; }
.lf-upload-hint { margin-top: 6px; font-size: 12px; color: var(--text-placeholder); }
.lf-detail-actions { margin-bottom: 12px; }
.lf-comments-title { font-size: 13px; font-weight: 600; margin-bottom: 12px; }
.lf-comments { display: flex; flex-direction: column; }
.lf-comments-list { flex: 1; max-height: 200px; overflow-y: auto; scrollbar-width: thin; }
.lf-comments-empty { text-align: center; color: var(--text-placeholder); padding: 14px 0; font-size: 13px; }
.lf-comment { display: flex; gap: 10px; margin-bottom: 12px; }
.lf-comment-avatar {
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 14px; flex-shrink: 0;
}
.lf-comment-main { flex: 1; min-width: 0; }
.lf-comment-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 4px; }
.lf-comment-user { color: #409eff; font-size: 12px; }
.lf-comment-date { font-size: 11px; color: var(--text-placeholder); }
.lf-comment-bubble {
  background: #f5f7fa; border-radius: 4px 10px 10px 10px; padding: 8px 10px;
  font-size: 13px; color: var(--text-primary); line-height: 1.5;
  word-break: break-word; white-space: pre-wrap;
}
.lf-comment-input { display: flex; gap: 8px; margin-top: 10px; }
</style>
