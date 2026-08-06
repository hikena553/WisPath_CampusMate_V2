<template>
  <div class="figures-page">
    <div class="page-header">
      <h2>人物风采管理</h2>
      <el-button type="primary" @click="openDialog()">添加人物</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="categoryFilter" placeholder="全部类别" clearable style="width:150px">
        <el-option label="学生" value="student" />
        <el-option label="教师" value="teacher" />
        <el-option label="校友" value="alumni" />
      </el-select>
    </div>

    <el-table :data="paginatedFigures" style="width:100%" border v-loading="loading">
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="title" label="称号" width="200" show-overflow-tooltip />
      <el-table-column prop="category" label="身份" width="100">
        <template #default="{ row }">
          <el-tag :type="row.category === 'student' ? 'primary' : row.category === 'teacher' ? 'success' : 'warning'" size="small">
            {{ row.category === 'student' ? '学生' : row.category === 'teacher' ? '教师' : '校友' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
      <el-table-column label="头像" width="80">
        <template #default="{ row }">
          <el-avatar :size="36" :src="row.avatar || undefined">{{ row.name[0] }}</el-avatar>
        </template>
      </el-table-column>
      <el-table-column label="证明材料" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.proofs && JSON.parse(row.proofs).length" type="success" size="small">{{ JSON.parse(row.proofs).length }} 份</el-tag>
          <span v-else style="color:#999">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
          <el-popconfirm title="确定删除该人物吗？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="filteredFigures.length > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[50, 100, 200]"
        :total="filteredFigures.length"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑人物' : '添加人物'" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="称号" required>
          <el-input v-model="form.title" placeholder="如：国家奖学金获得者" />
        </el-form-item>
        <el-form-item label="身份" required>
          <el-select v-model="form.category" placeholder="请选择身份" style="width:100%">
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="校友" value="alumni" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" required>
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入人物描述" />
        </el-form-item>
        <el-form-item label="头像">
          <div class="avatar-upload-area">
            <div class="avatar-preview" :class="{ 'has-image': form.avatar }">
              <img v-if="form.avatar" :src="form.avatar" class="avatar-img" />
              <div v-else class="avatar-placeholder">
                <el-icon :size="32"><Plus /></el-icon>
                <span>点击选择头像</span>
              </div>
            </div>
            <el-upload
              :show-file-list="false"
              :before-upload="handleAvatarUpload"
              accept="image/*"
            >
              <el-button type="primary" plain size="small">选择文件</el-button>
            </el-upload>
          </div>
        </el-form-item>
        <el-form-item label="证明材料">
          <div class="upload-row">
            <el-upload
              multiple
              :show-file-list="false"
              :before-upload="handleProofUpload"
              accept="image/*,.pdf,.doc,.docx"
            >
              <el-button type="success" plain>选择文件</el-button>
            </el-upload>
            <span class="upload-hint">支持 jpg/png/pdf/doc</span>
          </div>
          <div v-if="proofFiles.length" class="proof-list">
            <div v-for="(f, i) in proofFiles" :key="i" class="proof-item">
              <el-icon><Document /></el-icon>
              <span class="proof-name">{{ f.name }}</span>
              <el-button type="danger" link size="small" @click="removeProof(i)">移除</el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Plus } from '@element-plus/icons-vue'
import type { CampusFigure } from '@/types'
import { getAdminFigures, createFigure, updateFigure, deleteFigure } from '@/api/campus'
import { uploadFile } from '@/api/upload'

const loading = ref(false)
const saving = ref(false)
const figures = ref<CampusFigure[]>([])
const categoryFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ name: '', title: '', category: '', description: '', avatar: '' })
const proofFiles = ref<{ name: string; url: string }[]>([])

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(50)

const filteredFigures = computed(() => {
  return figures.value
})

const paginatedFigures = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredFigures.value.slice(start, end)
})

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 页码变化时自动更新表格数据
}

async function fetchData() {
  loading.value = true
  try {
    figures.value = await getAdminFigures(categoryFilter.value || undefined)
  } finally {
    loading.value = false
  }
}

watch(categoryFilter, () => fetchData())
onMounted(() => fetchData())

function openDialog(row?: CampusFigure) {
  if (row) {
    editingId.value = row.id
    form.value = { name: row.name, title: row.title, category: row.category, description: row.description, avatar: row.avatar || '' }
    proofFiles.value = row.proofs ? JSON.parse(row.proofs) : []
  } else {
    editingId.value = null
    form.value = { name: '', title: '', category: '', description: '', avatar: '' }
    proofFiles.value = []
  }
  dialogVisible.value = true
}

async function handleAvatarUpload(file: File) {
  try {
    const res = await uploadFile(file)
    form.value.avatar = res.url
  } catch {
    ElMessage.error('头像上传失败')
  }
  return false
}

async function handleProofUpload(file: File) {
  try {
    const res = await uploadFile(file)
    proofFiles.value.push({ name: res.filename, url: res.url })
  } catch {
    ElMessage.error('证明材料上传失败')
  }
  return false
}

function removeProof(index: number) {
  proofFiles.value.splice(index, 1)
}

async function handleSave() {
  if (!form.value.name || !form.value.title || !form.value.category || !form.value.description) {
    ElMessage.warning('请填写完整信息')
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value, proofs: JSON.stringify(proofFiles.value), category: form.value.category as 'student' | 'teacher' | 'alumni' }
    if (editingId.value) {
      await updateFigure(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createFigure(payload)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  await deleteFigure(id)
  ElMessage.success('删除成功')
  await fetchData()
}
</script>

<style scoped>
.figures-page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #1a1a2e; }
.filter-bar { margin-bottom: 16px; }
.avatar-upload-area { display: flex; align-items: center; gap: 16px; }
.avatar-preview {
  width: 100px; height: 120px; border-radius: 8px;
  border: 2px dashed #d9d9d9; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  background: #fafafa; transition: border-color .2s;
  flex-shrink: 0;
}
.avatar-preview.has-image { border: 2px solid #e0e0e0; background: #fff; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.avatar-placeholder {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  color: #bbb; cursor: default;
}
.avatar-placeholder span { font-size: 12px; }
.proof-list { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; }
.proof-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.proof-name { flex: 1; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 12px 0;
}
</style>
