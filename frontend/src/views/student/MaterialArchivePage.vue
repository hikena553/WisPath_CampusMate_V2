<template>
  <div class="material-page">
    <!-- 吸顶头 -->
    <div class="topbar">
      <div class="back" @click="goBack"><el-icon :size="18"><ArrowLeft /></el-icon></div>
      <div class="topbar-title">材料档案</div>
      <div class="add" @click="openUpload">
        <el-icon :size="18"><Plus /></el-icon>
      </div>
    </div>

    <!-- 分类筛选 -->
    <div class="cat-row">
      <span class="cat-chip" :class="{ on: !filterCat }" @click="setCat('')">全部</span>
      <span v-for="c in categories" :key="c.value" class="cat-chip" :class="{ on: filterCat === c.value }" @click="setCat(c.value)">
        {{ c.label }}
      </span>
    </div>

    <!-- 列表 -->
    <div class="group">
      <div v-if="list.length" class="mat-list">
        <div v-for="m in list" :key="m.id" class="mat-card">
          <div class="mat-ico" :style="{ background: catColor(m.category) + '1f', color: catColor(m.category) }">{{ catEmoji(m.category) }}</div>
          <div class="mat-info">
            <div class="mat-title">{{ m.title }}
              <el-tag :type="m.status === 'approved' ? 'success' : m.status === 'rejected' ? 'danger' : 'warning'" size="small" effect="plain" style="margin-left:6px">
                {{ statusLabel(m.status) }}
              </el-tag>
            </div>
            <div class="mat-sub">
              {{ m.category_label }} · {{ m.file_name || '附件' }} ·
              {{ m.created_at ? m.created_at.slice(0, 10) : '' }}
            </div>
            <div v-if="m.status === 'rejected' && m.reject_reason" class="mat-reject">驳回原因：{{ m.reject_reason }}</div>
          </div>
          <div class="mat-actions">
            <el-button text size="small" @click="preview(m)">查看</el-button>
            <el-button text size="small" type="danger" @click="remove(m)">删除</el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="还没有材料，点击右上角 + 上传归档" :image-size="90" />
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="上传材料" width="92%" :append-to-body="true">
      <el-form label-position="top">
        <el-form-item label="材料标题" required>
          <el-input v-model="form.title" placeholder="如：录取通知书、英语四级成绩单" maxlength="60" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width:100%">
            <el-option v-for="c in categories" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="材料文件" required>
          <el-upload
            :auto-upload="false"
            :show-file-list="true"
            :limit="1"
            :on-change="handleFileChange"
            drag
            style="width:100%"
          >
            <div style="padding:14px 0;font-size:13px;color:#909399;">
              <el-icon :size="26"><UploadFilled /></el-icon>
              <div>点击选择文件（jpg / png / pdf / doc 等）</div>
            </div>
          </el-upload>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填，材料说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submit">上传归档</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus, UploadFilled } from '@element-plus/icons-vue'
import { getMyMaterials, createMaterial, deleteMaterial } from '@/api/material'
import type { Material } from '@/types'

const router = useRouter()
const list = ref<Material[]>([])
const filterCat = ref('')
const uploadVisible = ref(false)
const uploading = ref(false)
const form = ref({ title: '', category: 'other', remark: '' })
let pendingFile: File | null = null

const categories = [
  { value: 'identity', label: '证件' },
  { value: 'statement', label: '证明' },
  { value: 'grade', label: '成绩单' },
  { value: 'register', label: '学籍' },
  { value: 'other', label: '其他' },
]
const statusLabel = (s: string) => ({ pending: '归档中', approved: '已归档', rejected: '未通过' }[s] || s)
const catColor = (c: string) => ({ identity: '#5b8def', statement: '#34b37a', grade: '#e6a23c', register: '#a78bfa', other: '#909399' }[c] || '#909399')
const catEmoji = (c: string) => ({ identity: '🪪', statement: '📄', grade: '📊', register: '🗂️', other: '📎' }[c] || '📎')

async function load() {
  try {
    const all = await getMyMaterials()
    list.value = filterCat.value ? all.filter((m) => m.category === filterCat.value) : all
  } catch { list.value = [] }
}
function setCat(c: string) { filterCat.value = c; load() }
function openUpload() {
  form.value = { title: '', category: 'other', remark: '' }
  pendingFile = null
  uploadVisible.value = true
}
function handleFileChange(file: any) {
  pendingFile = file.raw || file
}
async function submit() {
  if (!form.value.title.trim()) return ElMessage.warning('请填写材料标题')
  if (!pendingFile) return ElMessage.warning('请选择材料文件')
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', pendingFile)
    const up: any = await (await import('@/utils/request')).default.post('/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await createMaterial({
      title: form.value.title.trim(),
      category: form.value.category,
      file_url: up.url,
      file_name: up.filename || pendingFile.name,
      file_type: (pendingFile.name.split('.').pop() || '').toLowerCase(),
      remark: form.value.remark,
    })
    ElMessage.success('已上传，等待辅导员归档')
    uploadVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally { uploading.value = false }
}
function preview(m: Material) {
  window.open(m.file_url, '_blank')
}
async function remove(m: Material) {
  try { await ElMessageBox.confirm('确定删除这条材料吗？', '删除材料', { type: 'warning' }) } catch { return }
  try { await deleteMaterial(m.id); ElMessage.success('已删除'); load() } catch { ElMessage.error('删除失败') }
}
function goBack() { router.back() }
onMounted(load)
</script>

<style scoped>
.material-page { width: 100%; max-width: 480px; min-width: 0; margin: 0 auto; min-height: 100%; background: #f5f7fb; padding-bottom: 40px; }
.topbar {
  position: sticky; top: 0; z-index: 20;
  display: flex; align-items: center; justify-content: space-between;
  height: 52px; padding: 0 14px; background: #fff; box-shadow: 0 1px 6px rgba(0,0,0,.04);
}
.back { display: flex; align-items: center; width: 32px; cursor: pointer; color: #1a1a2e; }
.topbar-title { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.add { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; background: #ecf5ff; color: #5b8def; cursor: pointer; }
.cat-row { display: flex; gap: 8px; overflow-x: auto; padding: 12px; background: #fff; }
.cat-chip { flex-shrink: 0; padding: 5px 14px; border-radius: 16px; font-size: 13px; background: #f1f3f8; color: #5a6478; cursor: pointer; }
.cat-chip.on { background: linear-gradient(135deg, #5b8def, #7c6cf0); color: #fff; font-weight: 600; }
.group { padding: 12px 12px 0; }
.mat-list { display: flex; flex-direction: column; gap: 10px; }
.mat-card { display: flex; align-items: center; gap: 12px; background: #fff; border-radius: 12px; padding: 12px 14px; box-shadow: 0 1px 5px rgba(0,0,0,.04); }
.mat-ico { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.mat-info { flex: 1; min-width: 0; }
.mat-title { font-size: 14px; font-weight: 600; color: #1a1a2e; display: flex; align-items: center; flex-wrap: wrap; }
.mat-sub { font-size: 12px; color: #909399; margin-top: 4px; }
.mat-reject { font-size: 12px; color: #f56c6c; margin-top: 4px; }
.mat-actions { display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }
</style>