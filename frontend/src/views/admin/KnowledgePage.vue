<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h2>AI知识库管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog">添加问答对</el-button>
        <el-upload
          :show-file-list="false"
          :before-upload="handleUpload"
          accept=".pdf,.docx,.txt"
        >
          <el-button type="success">上传文档</el-button>
        </el-upload>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="问答对" name="qa">
        <div class="filter-bar">
          <el-select v-model="categoryFilter" placeholder="选择分类" clearable style="width: 150px">
            <el-option label="办事流程" value="办事流程" />
            <el-option label="校园导航" value="校园导航" />
            <el-option label="规章制度" value="规章制度" />
            <el-option label="校园生活" value="校园生活" />
            <el-option label="自定义" value="自定义" />
          </el-select>
          <el-input v-model="searchText" placeholder="搜索问题或答案" clearable style="width: 250px">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <el-table :data="paginatedItems" style="width: 100%" border>
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="answer" label="答案" min-width="300" show-overflow-tooltip />
          <el-table-column prop="tags" label="标签" width="150" show-overflow-tooltip />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="editItem(row)">编辑</el-button>
              <el-popconfirm title="确定删除吗？" @confirm="deleteItem(row.id)">
                <template #reference>
                  <el-button type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper" v-if="totalItems > 0">
          <el-pagination
            v-model:current-page="currentItemPage"
            v-model:page-size="itemPageSize"
            :page-sizes="[50, 100, 200]"
            :total="totalItems"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleItemSizeChange"
            @current-change="handleItemCurrentChange"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="文档管理" name="docs">
        <el-table :data="paginatedDocuments" style="width: 100%" border>
          <el-table-column prop="filename" label="文件名" min-width="200" />
          <el-table-column prop="file_type" label="类型" width="100" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
                {{ row.status === 'completed' ? '已完成' : row.status === 'failed' ? '失败' : '处理中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分块数" width="100" />
          <el-table-column prop="created_at" label="上传时间" width="180" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-popconfirm title="确定删除吗？" @confirm="deleteDoc(row.id)">
                <template #reference>
                  <el-button type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper" v-if="documents.length > 0">
          <el-pagination
            v-model:current-page="currentDocPage"
            v-model:page-size="docPageSize"
            :page-sizes="[50, 100, 200]"
            :total="documents.length"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleDocSizeChange"
            @current-change="handleDocCurrentChange"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑问答对' : '添加问答对'" width="600px">
      <el-form :model="formData" label-width="80px">
        <el-form-item label="分类" required>
          <el-select v-model="formData.category" placeholder="选择分类">
            <el-option label="办事流程" value="办事流程" />
            <el-option label="校园导航" value="校园导航" />
            <el-option label="规章制度" value="规章制度" />
            <el-option label="校园生活" value="校园生活" />
            <el-option label="自定义" value="自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题" required>
          <el-input v-model="formData.question" placeholder="输入问题" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="formData.answer" type="textarea" :rows="4" placeholder="输入答案" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="formData.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import {
  getKnowledgeList, createKnowledgeItem, updateKnowledgeItem, deleteKnowledgeItem,
  uploadDocument, getDocumentList, deleteDocument,
  type KnowledgeItem, type DocumentInfo,
} from '@/api/admin'

const activeTab = ref('qa')
const items = ref<KnowledgeItem[]>([])
const documents = ref<DocumentInfo[]>([])
const categoryFilter = ref('')
const searchText = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)

// 问答对分页相关状态
const currentItemPage = ref(1)
const itemPageSize = ref(50)
const totalItems = ref(0)

// 文档分页相关状态
const currentDocPage = ref(1)
const docPageSize = ref(50)

const formData = ref({
  category: '',
  question: '',
  answer: '',
  tags: '',
})

// 从后端返回的数据中提取当前页的问答对列表
const paginatedItems = computed(() => items.value)

// 文档列表（前端分页）
const paginatedDocuments = computed(() => {
  const start = (currentDocPage.value - 1) * docPageSize.value
  const end = start + docPageSize.value
  return documents.value.slice(start, end)
})

// 当筛选条件变化时，重置到第一页并重新加载
watch([categoryFilter, searchText], () => {
  currentItemPage.value = 1
  loadItems()
})

// 当页码或每页条数变化时，重新加载
watch([currentItemPage, itemPageSize], () => {
  loadItems()
})

function handleItemSizeChange() {
  currentItemPage.value = 1
}

function handleItemCurrentChange() {
  // 页码变化时自动更新表格数据（通过 watch 自动响应）
}

function handleDocSizeChange() {
  currentDocPage.value = 1
}

function handleDocCurrentChange() {
  // 页码变化时自动更新表格数据
}

async function loadItems() {
  try {
    const response = await getKnowledgeList({
      page: currentItemPage.value,
      page_size: itemPageSize.value,
      category: categoryFilter.value || undefined,
      search: searchText.value || undefined,
    })
    items.value = response.items
    totalItems.value = response.total
  } catch (error) {
    console.error('加载知识库失败:', error)
    ElMessage.error('加载知识库失败')
  }
}

async function loadDocuments() {
  try {
    documents.value = await getDocumentList()
  } catch (error) {
    console.error('加载文档列表失败:', error)
    ElMessage.error('加载文档列表失败')
  }
}

function showAddDialog() {
  editingId.value = null
  formData.value = { category: '', question: '', answer: '', tags: '' }
  dialogVisible.value = true
}

function editItem(item: KnowledgeItem) {
  editingId.value = item.id
  formData.value = {
    category: item.category,
    question: item.question,
    answer: item.answer,
    tags: item.tags || '',
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formData.value.category || !formData.value.question || !formData.value.answer) {
    ElMessage.warning('请填写必填项')
    return
  }

  submitting.value = true
  try {
    if (editingId.value) {
      await updateKnowledgeItem(editingId.value, formData.value)
      ElMessage.success('更新成功')
    } else {
      await createKnowledgeItem(formData.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadItems()
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function deleteItem(id: number) {
  try {
    await deleteKnowledgeItem(id)
    ElMessage.success('删除成功')
    loadItems()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

async function handleUpload(file: File) {
  try {
    await uploadDocument(file)
    ElMessage.success('上传成功')
    loadDocuments()
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传失败')
  }
  return false
}

async function deleteDoc(id: number) {
  try {
    await deleteDocument(id)
    ElMessage.success('删除成功')
    loadDocuments()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadItems()
  loadDocuments()
})
</script>

<style scoped>
.knowledge-page {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 12px 0;
}
</style>
