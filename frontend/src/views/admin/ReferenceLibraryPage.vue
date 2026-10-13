<template>
  <div class="reference-page">
    <div class="page-header">
      <div class="header-left">
        <h2>开源参考复用</h2>
        <span class="header-sub">只复用许可证允许的开源项目，自动附带出处署名，替代"逆向搬运"</span>
      </div>
      <div class="header-actions">
        <el-button :icon="RefreshCw" :loading="loading" @click="loadReferences">刷新</el-button>
        <el-button type="primary" @click="showAddDialog">添加参考项目</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <!-- ============ 参考库 ============ -->
      <el-tab-pane label="参考库" name="library">
        <div class="filter-bar">
          <el-input
            v-model="search"
            placeholder="搜索名称 / 技术栈 / 可复用范围"
            clearable
            style="width: 300px"
            @keyup.enter="loadReferences"
            @clear="loadReferences"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="categoryFilter" placeholder="许可证分级" clearable style="width: 170px" @change="loadReferences">
            <el-option label="宽松（可商用）" value="permissive" />
            <el-option label="弱传染" value="weak-copyleft" />
            <el-option label="强传染" value="copyleft" />
            <el-option label="未知" value="unknown" />
          </el-select>
          <el-button :loading="loading" @click="loadReferences">查询</el-button>
        </div>

        <el-table :data="references" v-loading="loading" stripe class="ref-table">
          <el-table-column prop="name" label="项目" min-width="180">
            <template #default="{ row }">
              <div class="ref-name">{{ row.name }}</div>
              <div class="ref-repo">{{ row.repo_url }}</div>
            </template>
          </el-table-column>
          <el-table-column label="许可证" width="150">
            <template #default="{ row }">
              <el-tag :type="licenseTagType(row.license_category)" size="small" effect="light">
                {{ row.license }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="stars" label="收藏量" width="110" sortable>
            <template #default="{ row }">{{ row.stars.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column label="技术栈" min-width="180">
            <template #default="{ row }">
              <span class="tags-text">{{ row.tech_tags || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="可复用范围" min-width="240">
            <template #default="{ row }">
              <span class="scope-text">{{ row.reusable_scope || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && references.length === 0" description="暂无参考项目" />
      </el-tab-pane>

      <!-- ============ 骨架生成 ============ -->
      <el-tab-pane label="生成页面骨架" name="scaffold">
        <el-card shadow="never" class="scaffold-form-card">
          <div class="scaffold-tip">
            <el-icon><Info /></el-icon>
            <span>输入页面需求，系统会从参考库匹配可复用项目，并生成符合本项目规范的 Vue 骨架（本地模板生成，自动附带出处署名）。</span>
          </div>
          <el-form label-width="90px" class="scaffold-form" @submit.prevent>
            <el-form-item label="页面需求">
              <el-input
                v-model="scaffoldForm.requirement"
                type="textarea"
                :rows="3"
                placeholder="例如：学生成绩分析页面，包含筛选栏、统计卡片和折线图"
              />
            </el-form-item>
            <el-form-item label="组件名">
              <el-input v-model="scaffoldForm.page_name" placeholder="可选，PascalCase，如 GradeAnalysis" style="width: 260px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="generating" @click="handleGenerate">生成骨架</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <template v-if="scaffoldResult">
          <div class="scaffold-meta">
            <div class="meta-item">
              <span class="meta-label">组件名</span>
              <span class="meta-value">{{ scaffoldResult.page_name }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">建议路由</span>
              <span class="meta-value">{{ scaffoldResult.route_path }}</span>
            </div>
          </div>

          <el-card shadow="never" class="scaffold-refs-card">
            <template #header>
              <span class="card-header-title">参考的开源项目（请保留署名）</span>
            </template>
            <div v-if="scaffoldResult.matched_references.length" class="ref-chips">
              <el-tag
                v-for="r in scaffoldResult.matched_references"
                :key="r.id"
                :type="licenseTagType(r.license_category)"
                effect="plain"
                class="ref-chip"
              >
                {{ r.name }} · {{ r.license }}
              </el-tag>
            </div>
            <el-empty v-else description="未匹配到参考项目" :image-size="60" />
            <ul class="note-list">
              <li v-for="(n, i) in scaffoldResult.notes" :key="i">{{ n }}</li>
            </ul>
          </el-card>

          <el-card
            v-for="(code, filename) in scaffoldResult.files"
            :key="filename"
            shadow="never"
            class="code-card"
          >
            <template #header>
              <div class="code-header">
                <span class="card-header-title">{{ filename }}</span>
                <el-button link type="primary" size="small" :icon="Copy" @click="copyCode(code)">复制代码</el-button>
              </div>
            </template>
            <pre class="code-block"><code>{{ code }}</code></pre>
          </el-card>
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加 / 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑参考项目' : '添加参考项目'" width="560px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="项目 / 模板名称" />
        </el-form-item>
        <el-form-item label="仓库地址">
          <el-input v-model="form.repo_url" placeholder="https://github.com/..." />
        </el-form-item>
        <el-form-item label="官网/演示">
          <el-input v-model="form.homepage" placeholder="可选" />
        </el-form-item>
        <el-form-item label="许可证">
          <el-input v-model="form.license" placeholder="如 MIT / Apache-2.0" style="width: 180px" />
          <el-select v-model="form.license_category" style="width: 150px; margin-left: 10px">
            <el-option label="宽松（可商用）" value="permissive" />
            <el-option label="弱传染" value="weak-copyleft" />
            <el-option label="强传染" value="copyleft" />
            <el-option label="未知" value="unknown" />
          </el-select>
        </el-form-item>
        <el-form-item label="收藏量">
          <el-input-number v-model="form.stars" :min="0" :step="1000" controls-position="right" />
          <el-input v-model="form.language" placeholder="主要语言" style="width: 140px; margin-left: 10px" />
        </el-form-item>
        <el-form-item label="技术栈">
          <el-input v-model="form.tech_tags" placeholder="逗号分隔，如 Vue3,表格,虚拟滚动" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.summary" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="可复用范围">
          <el-input v-model="form.reusable_scope" type="textarea" :rows="2" placeholder="说明哪些部分可以合法复用" />
        </el-form-item>
        <el-form-item label="署名要求">
          <el-input v-model="form.attribution" type="textarea" :rows="2" placeholder="许可证的署名 / 合规要求" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshCw, Info, Copy } from 'lucide-vue-next'
import {
  listReferences,
  createReference,
  updateReference,
  deleteReference,
  generateScaffold,
  type OpenSourceReference,
  type ReferencePayload,
  type ScaffoldResult,
} from '@/api/reference'

const activeTab = ref('library')
const loading = ref(false)
const references = ref<OpenSourceReference[]>([])
const search = ref('')
const categoryFilter = ref('')

const dialogVisible = ref(false)
const editing = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

const emptyForm = (): ReferencePayload => ({
  name: '',
  repo_url: '',
  homepage: '',
  license: 'MIT',
  license_category: 'permissive',
  stars: 0,
  language: '',
  tech_tags: '',
  summary: '',
  reusable_scope: '',
  attribution: '',
})
const form = ref<ReferencePayload>(emptyForm())

const scaffoldForm = ref({ requirement: '', page_name: '' })
const generating = ref(false)
const scaffoldResult = ref<ScaffoldResult | null>(null)

function licenseTagType(category: string): 'success' | 'warning' | 'danger' | 'info' {
  return (
    ({ permissive: 'success', 'weak-copyleft': 'warning', copyleft: 'danger' } as const)[category as
      | 'permissive'
      | 'weak-copyleft'
      | 'copyleft'] || 'info'
  )
}

async function loadReferences() {
  loading.value = true
  try {
    const res = await listReferences({
      search: search.value || undefined,
      license_category: categoryFilter.value || undefined,
    })
    references.value = res.items || []
  } catch {
    ElMessage.error('加载参考库失败')
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  editing.value = false
  editingId.value = null
  form.value = emptyForm()
  dialogVisible.value = true
}

function showEditDialog(row: OpenSourceReference) {
  editing.value = true
  editingId.value = row.id
  form.value = {
    name: row.name,
    repo_url: row.repo_url,
    homepage: row.homepage || '',
    license: row.license,
    license_category: row.license_category,
    stars: row.stars,
    language: row.language || '',
    tech_tags: row.tech_tags || '',
    summary: row.summary || '',
    reusable_scope: row.reusable_scope || '',
    attribution: row.attribution || '',
    enabled: row.enabled ?? true,
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name.trim() || !form.value.repo_url.trim() || !form.value.license.trim()) {
    ElMessage.warning('名称、仓库地址、许可证为必填项')
    return
  }
  saving.value = true
  try {
    if (editing.value && editingId.value != null) {
      await updateReference(editingId.value, form.value)
      ElMessage.success('已更新')
    } else {
      await createReference(form.value)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    await loadReferences()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: OpenSourceReference) {
  try {
    await ElMessageBox.confirm(`确认删除参考项目「${row.name}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteReference(row.id)
    ElMessage.success('已删除')
    await loadReferences()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function handleGenerate() {
  if (!scaffoldForm.value.requirement.trim()) {
    ElMessage.warning('请先填写页面需求')
    return
  }
  generating.value = true
  try {
    scaffoldResult.value = await generateScaffold({
      requirement: scaffoldForm.value.requirement.trim(),
      page_name: scaffoldForm.value.page_name.trim() || undefined,
    })
    ElMessage.success('骨架已生成')
  } catch {
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}

async function copyCode(code: string) {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success('代码已复制')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

onMounted(loadReferences)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}
.header-sub {
  font-size: 13px;
  color: #94a3b8;
}
.header-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.ref-table {
  width: 100%;
}
.ref-name {
  font-weight: 600;
  color: #334155;
}
.ref-repo {
  font-size: 12px;
  color: #94a3b8;
  word-break: break-all;
}
.tags-text {
  font-size: 13px;
  color: #475569;
}
.scope-text {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}
.scaffold-form-card {
  margin-bottom: 16px;
}
.scaffold-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
}
.scaffold-meta {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
}
.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.meta-label {
  font-size: 12px;
  color: #94a3b8;
}
.meta-value {
  font-size: 15px;
  font-weight: 600;
  color: #2563eb;
}
.scaffold-refs-card,
.code-card {
  margin-bottom: 16px;
}
.card-header-title {
  font-weight: 600;
  color: #334155;
}
.ref-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ref-chip {
  margin: 0;
}
.note-list {
  margin: 12px 0 0;
  padding-left: 18px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.8;
}
.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.code-block {
  margin: 0;
  max-height: 460px;
  overflow: auto;
  padding: 14px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  font-size: 12.5px;
  line-height: 1.6;
  font-family: 'JetBrains Mono', Consolas, Menlo, monospace;
  white-space: pre;
}
</style>
