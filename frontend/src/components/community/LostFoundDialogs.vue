<template>
  <!-- 发布：寻物启事 / 失物招领 登记 -->
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

  <!-- 详情：图片 + 描述 + 留言 + 本人可标记认领 / 删除 -->
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
            <el-button type="warning" size="small" @click="changeStatus('claimed')">标记为已认领</el-button>
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
</template>

<script setup lang="ts">
/**
 * 失物招领的两个弹窗（发布 / 详情），由交流社区的帖子流调用。
 *
 * 为什么从列表里剥出来：失物与招领现在是交流社区分区行里的两个胶囊，
 * 列表行要跟帖子一模一样（标题 + 元信息 + 缩略图 + 评论数），
 * 列表本身已经由 CommunityFeed 统一渲染；这里只留「点开之后」的那一层，
 * 两个弹窗用 teleport 挂在 body 上，跟列表在哪一屏无关。
 *
 * 对外：openCreate(defaultType) / openDetail(id)；
 * 发布、改状态、删除、留言之后统一 emit('changed')，交回列表重新拉数据。
 */
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  getLostFoundItem,
  createLostFoundItem,
  updateLostFoundStatus,
  deleteLostFoundItem,
  createLostFoundComment,
} from '@/api/lostFound'
import { uploadFile } from '@/api/upload'
import { parseServerTime } from '@/utils/datetime'
import type { LostFoundItem } from '@/types'

const emit = defineEmits<{ (e: 'changed'): void }>()
const auth = useAuthStore()

const createVisible = ref(false)
const detailVisible = ref(false)
const detail = ref<LostFoundItem | null>(null)
const comment = ref('')
const submitting = ref(false)
const formRef = ref<any>()

const formRules = {
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  title: [{ required: true, message: '请填写物品名称', trigger: 'blur' }],
}

const form = reactive({ type: 'lost', title: '', description: '', location: '', contact: '', image_url: '' })

/** 从「失物 / 招领」胶囊点进来时，类型预置成当前分区对应的那一个 */
function openCreate(defaultType: 'lost' | 'found' = 'lost') {
  Object.assign(form, { type: defaultType, title: '', description: '', location: '', contact: '', image_url: '' })
  createVisible.value = true
}

async function openDetail(id: number) {
  try {
    detail.value = await getLostFoundItem(id)
    detailVisible.value = true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  }
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
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  } finally {
    submitting.value = false
  }
}

async function changeStatus(status: string) {
  if (!detail.value) return
  try {
    await updateLostFoundStatus(detail.value.id, status)
    ElMessage.success('已更新')
    detailVisible.value = false
    emit('changed')
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
    emit('changed')
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
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '留言失败')
  }
}

function formatDate(iso: string) {
  // 后端时间是不带时区的 UTC，直接 new Date 会按本地时间解析，刚发的记录会显示成「昨天」
  const ms = parseServerTime(iso)
  if (Number.isNaN(ms)) return ''
  const d = new Date(ms)
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

defineExpose({ openCreate, openDetail })
</script>

<style scoped>
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
.lf-detail-actions { margin-bottom: 12px; }

/* 图片上传 */
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

/* 留言 */
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

@media (max-width: 520px) {
  .lf-detail-main { flex-direction: column; }
  .lf-detail-img { width: 100%; }
}
</style>
