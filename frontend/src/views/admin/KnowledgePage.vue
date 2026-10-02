<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h2>AI知识库管理</h2>
      <div class="header-actions">
        <el-button :icon="RefreshCw" :loading="reindexing" @click="doReindex">重建向量索引</el-button>
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

    <!-- 检索与向量分词模型状态卡片 -->
    <div class="index-cards">
      <div v-if="statusLoading" class="cards-loading">正在加载索引状态…</div>
      <template v-else>
      <div class="index-card">
        <div class="card-label">分词模型</div>
        <div class="card-value">{{ indexStatus?.segmenter || '—' }}</div>
        <div class="card-desc">jieba 中文分词 + 停用词过滤</div>
      </div>
      <div class="index-card">
        <div class="card-label">向量模型</div>
        <div class="card-value">{{ indexStatus?.embedding_model || '未配置' }}</div>
        <div class="card-desc">
          <el-tag size="small" :type="indexStatus?.embedding_configured ? 'success' : 'danger'">
            {{ indexStatus?.embedding_configured ? '已配置' : '未配置 DashScope Key' }}
          </el-tag>
        </div>
      </div>
      <div class="index-card">
        <div class="card-label">索引覆盖率（向量化）</div>
        <div class="card-value">{{ indexStatus?.index_coverage ?? 0 }}%</div>
        <el-progress
          :percentage="indexStatus?.index_coverage ?? 0"
          :stroke-width="8"
          :show-text="false"
          class="card-progress"
        />
        <div class="card-desc">
          {{ indexStatus?.indexed_chunks ?? 0 }} / {{ indexStatus?.total_chunks ?? 0 }} 分块已向量化
        </div>
      </div>
      <div class="index-card">
        <div class="card-label">知识总量</div>
        <div class="card-value">
          {{ indexStatus ? indexStatus.qa_count + indexStatus.document_count : '—' }}
        </div>
        <div class="card-desc">
          问答对 {{ indexStatus?.qa_count ?? 0 }} 条 · 文档 {{ indexStatus?.document_count ?? 0 }} 份
        </div>
      </div>
      </template>
    </div>

    <!-- 向量模型（embedding）配置 -->
    <el-card shadow="never" class="embed-config-card" v-loading="embedLoading">
      <template #header>
        <div class="embed-config-header">
          <div class="embed-config-title">
            <el-icon class="embed-config-icon"><Sparkles /></el-icon>
            <span>向量模型配置</span>
            <el-tag size="small" :type="embedConfig?.configured ? 'success' : 'danger'" effect="light">
              {{ embedConfig?.configured ? '已就绪' : '未配置' }}
            </el-tag>
            <el-tag v-if="embedConfig?.using_env_fallback" size="small" type="warning" effect="light">
              使用环境变量回退
            </el-tag>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="embedForm" class="embed-form" @submit.prevent>
        <el-form-item label="模型名称">
          <el-input v-model="embedForm.model" placeholder="text-embedding-v3" style="width: 210px" clearable />
        </el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="embedForm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" style="width: 330px" clearable />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="embedForm.api_key"
            type="password"
            show-password
            :placeholder="embedConfig?.api_key_set ? '已设置，留空保持不变' : 'OpenAI 兼容 Embeddings API Key'"
            style="width: 230px"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="embedSaving" @click="handleSaveEmbed">保存配置</el-button>
        </el-form-item>
      </el-form>

      <div class="embed-config-tip" v-if="embedConfig">
        <el-icon class="tip-icon"><Info /></el-icon>
        <span class="tip-text">
          {{ embedConfig.hint }}
          <template v-if="embedConfig.model">｜当前模型：<b>{{ embedConfig.model }}</b></template>
          <template v-if="embedConfig.base_url">｜接口：<span class="tip-url">{{ embedConfig.base_url }}</span></template>
          ｜Key：<b :class="embedConfig.api_key_set ? 'key-ok' : 'key-no'">{{ embedConfig.api_key_set ? '已设置' : '未设置' }}</b>
        </span>
        <el-button link type="primary" size="small" :loading="reindexing" @click="doReindex">重建向量索引</el-button>
      </div>
    </el-card>

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

        <el-table :data="paginatedItems" style="width: 100%">
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="answer" label="答案" min-width="300" show-overflow-tooltip />
          <el-table-column prop="tags" label="标签" width="150" show-overflow-tooltip />
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-tooltip content="编辑" placement="top">
                  <el-button class="action-btn edit" circle @click="editItem(row)">
                    <el-icon><PenLine /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-popconfirm title="确定删除吗？" @confirm="deleteItem(row.id)">
                  <template #reference>
                    <el-tooltip content="删除" placement="top">
                      <el-button class="action-btn delete" circle>
                        <el-icon><Trash2 /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </template>
                </el-popconfirm>
              </div>
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
        <el-table :data="paginatedDocuments" style="width: 100%">
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
          <el-table-column label="向量化进度" width="180">
            <template #default="{ row }">
              <template v-if="row.chunk_count">
                <el-progress
                  :percentage="Math.round((row.embedded_count || 0) / row.chunk_count * 100)"
                  :stroke-width="8"
                  :show-text="false"
                />
                <span class="vec-cell">
                  {{ row.embedded_count || 0 }} / {{ row.chunk_count }} 块
                  <el-tag size="small" :type="(row.embedded_count || 0) >= row.chunk_count ? 'success' : 'warning'">
                    {{ (row.embedded_count || 0) >= row.chunk_count ? '已索引' : '待重建' }}
                  </el-tag>
                </span>
              </template>
              <span v-else class="vec-cell">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="上传时间" width="180" />
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-popconfirm title="确定删除吗？" @confirm="deleteDoc(row.id)">
                  <template #reference>
                    <el-tooltip content="删除" placement="top">
                      <el-button class="action-btn delete" circle>
                        <el-icon><Trash2 /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </template>
                </el-popconfirm>
              </div>
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

      <el-tab-pane label="RAG 检索测试" name="rag">
        <div class="rag-panel">
          <div class="rag-search">
            <el-input
              v-model="ragQuery"
              placeholder="输入检索词，验证问答对与文档分块的混合召回……"
              :prefix-icon="Search"
              clearable
              @keyup.enter="doRagSearch"
            />
            <el-button type="primary" :icon="Search" :loading="ragLoading" @click="doRagSearch">检索</el-button>
          </div>
          <el-radio-group v-model="ragLimit" size="small" style="margin-bottom:12px">
            <el-radio-button :value="5">5 条</el-radio-button>
            <el-radio-button :value="10">10 条</el-radio-button>
            <el-radio-button :value="20">20 条</el-radio-button>
          </el-radio-group>

          <!-- 检索/向量分词模型运行信息 -->
          <div v-if="ragMeta" class="rag-meta">
            <div class="meta-row">
              <span class="meta-chip">检索方式：<b>{{ ragMeta.retrieval === 'hybrid' ? '混合召回（关键词 + 向量）' : ragMeta.retrieval === 'vector' ? '向量检索' : '关键词检索' }}</b></span>
              <span class="meta-chip">分词模型：<b>{{ ragMeta.segmenter || '—' }}</b></span>
              <span class="meta-chip">向量模型：<b>{{ ragMeta.embedding_model || '未配置' }}</b></span>
              <span class="meta-chip">索引分块：<b>{{ ragMeta.indexed_chunks }}</b></span>
              <span class="meta-chip">耗时：<b>{{ ragMeta.elapsed_ms }} ms</b></span>
            </div>
            <div class="meta-tokens" v-if="ragMeta.segment_tokens.length">
              分词：<span class="token" v-for="(t, i) in ragMeta.segment_tokens" :key="i">{{ t }}</span>
            </div>
            <el-alert v-if="ragMeta.note" :title="ragMeta.note" type="warning" :closable="false" style="margin-top:8px" />
          </div>

          <div v-loading="ragLoading" class="rag-results" v-if="ragHits.length > 0">
            <el-alert
              v-if="ragTraceId"
              :title="`检索完成 · trace_id：${ragTraceId}`"
              type="success"
              :closable="false"
              style="margin-bottom:12px"
            />
            <div v-for="(hit, i) in ragHits" :key="i" class="rag-item">
              <div class="rag-item-head">
                <el-tag :type="hit.type === 'qa' ? 'success' : 'warning'" size="small" effect="dark">
                  {{ hit.type === 'qa' ? '智能问答' : '文档分块' }}
                </el-tag>
                <template v-if="hit.type === 'qa'">
                  <span class="rag-cat" v-if="hit.category">{{ hit.category }}</span>
                </template>
                <template v-else>
                  <span class="rag-cat">文档 #{{ hit.document_id }}</span>
                </template>
                <span class="rag-score" v-if="hit.score !== null && hit.score !== undefined">相似度 {{ hit.score.toFixed(3) }}</span>
              </div>
              <template v-if="hit.type === 'qa'">
                <div class="rag-question">{{ hit.question }}</div>
                <div class="rag-answer">{{ hit.answer }}</div>
              </template>
              <template v-else>
                <div class="rag-answer">{{ hit.content }}</div>
              </template>
            </div>
          </div>
          <el-empty
            v-else-if="!ragLoading && ragSearched"
            description="未检索到匹配内容，尝试更换关键词"
            :image-size="80"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑问答对' : '添加问答对'" width="680px">
      <el-form :model="formData" label-width="100px">
        <div class="form-grid-2">
          <el-form-item label="分类" required>
            <el-select v-model="formData.category" placeholder="选择分类">
              <el-option label="办事流程" value="办事流程" />
              <el-option label="校园导航" value="校园导航" />
              <el-option label="规章制度" value="规章制度" />
              <el-option label="校园生活" value="校园生活" />
              <el-option label="自定义" value="自定义" />
            </el-select>
          </el-form-item>
          <el-form-item label="标签">
            <el-input v-model="formData.tags" placeholder="多个标签用逗号分隔" />
          </el-form-item>
        </div>
        <el-form-item label="问题" required>
          <el-input v-model="formData.question" placeholder="输入问题" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="formData.answer" type="textarea" :rows="4" placeholder="输入答案" />
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
import { Search, RefreshCw, Sparkles, Info, PenLine, Trash2 } from 'lucide-vue-next'
import {
  getKnowledgeList, createKnowledgeItem, updateKnowledgeItem, deleteKnowledgeItem,
  uploadDocument, getDocumentList, deleteDocument,
  reindexKnowledge, getKnowledgeIndexStatus,
  getEmbeddingConfig, saveEmbeddingConfig,
  type KnowledgeItem, type DocumentInfo, type KnowledgeIndexStatus, type EmbeddingConfig,
} from '@/api/admin'
import { searchKnowledgeRaw, type KnowledgeHit, type KnowledgeSearchMeta } from '@/api/knowledge'

const activeTab = ref('qa')
const items = ref<KnowledgeItem[]>([])
const documents = ref<DocumentInfo[]>([])
const categoryFilter = ref('')
const searchText = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)

// 检索/向量索引状态
const indexStatus = ref<KnowledgeIndexStatus | null>(null)
const statusLoading = ref(true)
const reindexing = ref(false)

// 向量模型配置
const embedConfig = ref<EmbeddingConfig | null>(null)
const embedLoading = ref(false)
const embedSaving = ref(false)
const embedForm = ref({ model: '', base_url: '', api_key: '' })

async function loadEmbedConfig() {
  embedLoading.value = true
  try {
    const cfg = await getEmbeddingConfig()
    embedConfig.value = cfg
    embedForm.value.model = cfg.model
    embedForm.value.base_url = cfg.base_url
    embedForm.value.api_key = ''
  } catch (error) {
    console.error('加载向量模型配置失败:', error)
  } finally {
    embedLoading.value = false
  }
}

async function handleSaveEmbed() {
  embedSaving.value = true
  try {
    const payload: { model?: string; base_url?: string; api_key?: string } = {}
    if (embedForm.value.model.trim()) payload.model = embedForm.value.model.trim()
    if (embedForm.value.base_url.trim()) payload.base_url = embedForm.value.base_url.trim()
    if (embedForm.value.api_key) payload.api_key = embedForm.value.api_key
    if (!payload.model && !payload.base_url && !payload.api_key) {
      ElMessage.warning('请至少填写一项配置')
      return
    }
    const cfg = await saveEmbeddingConfig(payload)
    embedConfig.value = cfg
    embedForm.value.model = cfg.model
    embedForm.value.base_url = cfg.base_url
    embedForm.value.api_key = ''
    ElMessage.success('向量模型配置已保存，重建索引后生效')
    loadIndexStatus()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存配置失败')
  } finally {
    embedSaving.value = false
  }
}

// RAG 检索测试
const ragQuery = ref('')
const ragLimit = ref(10)
const ragHits = ref<KnowledgeHit[]>([])
const ragLoading = ref(false)
const ragSearched = ref(false)
const ragTraceId = ref('')
const ragMeta = ref<KnowledgeSearchMeta | null>(null)

async function loadIndexStatus() {
  statusLoading.value = true
  try {
    indexStatus.value = await getKnowledgeIndexStatus()
  } catch (error) {
    console.error('加载索引状态失败:', error)
  } finally {
    statusLoading.value = false
  }
}

async function doReindex() {
  reindexing.value = true
  try {
    const res = await reindexKnowledge()
    if (res.error) {
      ElMessage.warning(`重建完成，但有 ${res.error}`);
    } else {
      ElMessage.success(`向量索引重建完成：新增 ${res.indexed} 块，跳过 ${res.skipped} 块（${res.model || '未配置模型'}）`)
    }
  } catch (error) {
    console.error('重建索引失败:', error)
    ElMessage.error('重建向量索引失败')
  } finally {
    reindexing.value = false
    loadIndexStatus()
    loadDocuments()
  }
}

async function doRagSearch() {
  const q = ragQuery.value.trim()
  if (!q) {
    ElMessage.warning('请输入检索关键词')
    return
  }
  ragLoading.value = true
  ragSearched.value = true
  try {
    const res = await searchKnowledgeRaw(q, ragLimit.value)
    ragHits.value = res.results
    ragTraceId.value = res.trace_id
    ragMeta.value = res.meta
  } finally {
    ragLoading.value = false
  }
}

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
    loadIndexStatus()
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
    loadIndexStatus()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadItems()
  loadDocuments()
  loadIndexStatus()
  loadEmbedConfig()
})
</script>

<style scoped>
.knowledge-page {
  padding: 16px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 索引状态卡片 */
.index-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.cards-loading {
  grid-column: 1 / -1;
  padding: 24px;
  text-align: center;
  color: #8a93a6;
  font-size: 13px;
}

.index-card {
  background: #f8faff;
  border: 1px solid #e3e8f7;
  border-radius: 12px;
  padding: 14px 16px;
}

.index-card .card-label {
  font-size: 12px;
  color: #7b8498;
  margin-bottom: 4px;
}

.index-card .card-value {
  font-size: 20px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 6px;
  word-break: break-all;
}

.index-card .card-desc {
  font-size: 12px;
  color: #8a94a6;
}

.card-progress {
  margin-bottom: 6px;
}

/* 向量模型配置卡片 */
.embed-config-card {
  margin-bottom: 16px;
  border-radius: 12px;
}
.embed-config-card :deep(.el-card__header) {
  padding: 12px 16px;
}
.embed-config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.embed-config-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #1f2d3d;
}
.embed-config-icon {
  color: #6366f1;
  font-size: 16px;
}
.embed-form {
  display: flex;
  align-items: flex-start;
  gap: 0;
  flex-wrap: wrap;
}
.embed-form :deep(.el-form-item) {
  margin-bottom: 8px;
  margin-right: 18px;
}
.embed-config-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f6f7fb;
  border: 1px dashed #dfe3ee;
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 4px;
  font-size: 12.5px;
  color: #5c677d;
  flex-wrap: wrap;
}
.tip-icon {
  color: #6366f1;
  font-size: 14px;
  flex: none;
}
.tip-text b { color: #1f2d3d; }
.tip-url { color: #6366f1; word-break: break-all; }
.key-ok { color: #10b981; }
.key-no { color: #f59e0b; }

.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  padding: 8px 0;
}

.vec-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

/* RAG 检索测试 */
.rag-search {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.rag-search .el-input {
  flex: 1;
}

.rag-meta {
  background: #f0f7ff;
  border: 1px solid #d6e8ff;
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 12px;
  font-size: 12.5px;
  color: #4b5563;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.meta-chip b {
  color: #1f2d3d;
}

.meta-tokens {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.token {
  background: #ffffff;
  border: 1px solid #d6e8ff;
  border-radius: 6px;
  padding: 1px 8px;
  font-size: 12px;
  color: #2563eb;
}

.rag-results {
  margin-top: 12px;
}

.rag-item {
  background: #f7f9fc;
  border: 1px solid #eef0f4;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}

.rag-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.rag-cat {
  font-size: 12px;
  color: #8a94a6;
}

.rag-score {
  font-size: 12px;
  color: #f59e0b;
}

.rag-question {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.rag-answer {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.7;
  white-space: pre-line;
}
</style>