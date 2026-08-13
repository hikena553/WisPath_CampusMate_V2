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

    <el-dialog v-model="detailVisible" :title="detail?.title || '详情'" width="560px">
      <template v-if="detail">
        <div class="lf-detail-header">
          <el-tag :type="detail.type === 'lost' ? 'danger' : 'success'" size="small">{{ detail.type === 'lost' ? '失物' : '招领' }}</el-tag>
          <el-tag :type="statusTagType(detail.status)" size="small" effect="plain">{{ statusLabel(detail.status) }}</el-tag>
          <span class="lf-detail-user">{{ detail.user_name }} · {{ formatDate(detail.created_at) }}</span>
        </div>
        <el-descriptions :column="1" border class="lf-detail-desc">
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
          <div v-if="!detail.comments?.length" class="lf-empty" style="padding: 12px 0">暂无留言</div>
          <div v-for="c in detail.comments" :key="c.id" class="lf-comment">
            <span class="lf-comment-user">{{ c.user_name || '用户' }}</span>
            <span class="lf-comment-content">{{ c.content }}</span>
            <span class="lf-comment-date">{{ formatDate(c.created_at) }}</span>
          </div>
          <div class="lf-comment-input">
            <el-input v-model="comment" placeholder="留言联系..." size="small" @keyup.enter="submitComment" />
            <el-button type="primary" size="small" @click="submitComment">发送</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getLostFoundItems, getLostFoundItem, createLostFoundItem, updateLostFoundStatus, deleteLostFoundItem, createLostFoundComment } from '@/api/lost_found'
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

const form = reactive({ type: 'lost', title: '', description: '', location: '', contact: '' })

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
  Object.assign(form, { type: 'lost', title: '', description: '', location: '', contact: '' })
  createVisible.value = true
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
.lf-item-top { display: flex; gap: 4px; align-items: center; margin-bottom: 4px; }
.lf-title { font-size: 13px; color: var(--text-primary); font-weight: 500; margin-bottom: 4px; }
.lf-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-placeholder); }
.lf-detail-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.lf-detail-user { font-size: 12px; color: var(--text-secondary); }
.lf-detail-desc { margin-bottom: 12px; }
.lf-detail-actions { margin-bottom: 12px; }
.lf-comments-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.lf-comment {
  display: flex; align-items: baseline; gap: 8px; padding: 6px 0;
  border-bottom: 1px dashed #eee; font-size: 13px;
}
.lf-comment-user { color: #409eff; font-size: 12px; flex-shrink: 0; }
.lf-comment-content { flex: 1; word-break: break-all; }
.lf-comment-date { font-size: 11px; color: var(--text-placeholder); flex-shrink: 0; }
.lf-comment-input { display: flex; gap: 8px; margin-top: 10px; }
</style>
