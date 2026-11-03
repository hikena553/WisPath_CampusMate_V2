<template>
  <div class="feed-admin-page">
    <div class="page-header">
      <div class="header-left">
        <h2>外部资讯统一管理</h2>
        <span class="header-sub">学生端订阅/爬取的全部外部数据源在此集中查看与维护，形成管理闭环</span>
      </div>
      <div class="header-actions">
        <el-button :icon="RefreshCw" :loading="refreshing" @click="handleRefreshFeeds">触发抓取</el-button>
        <el-button :icon="RefreshCw" :loading="loading" @click="reloadAll">刷新列表</el-button>
        <el-button type="primary" :icon="Plus" @click="showAddDialog">新增资讯源</el-button>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-label">资讯源总数</div>
        <div class="stat-value">{{ sources.length }}</div>
        <div class="stat-desc">启用 {{ enabledCount }} · 停用 {{ sources.length - enabledCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已入库资讯</div>
        <div class="stat-value">{{ itemTotalAll }}</div>
        <div class="stat-desc">按分类抓取去重后快照</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">最近抓取</div>
        <div class="stat-value small">{{ latestIngest }}</div>
        <div class="stat-desc">后台每 30 分钟自动抓取</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">覆盖分类</div>
        <div class="stat-value">{{ Object.keys(typeCounts).length }}</div>
        <div class="stat-desc">论文/开源/智能体/时政/AI/榜单/国产模型</div>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <!-- ============ 资讯源 ============ -->
      <el-tab-pane label="资讯源管理" name="sources">
        <div class="filter-bar">
          <el-select v-model="sourceTypeFilter" placeholder="按分类筛选" clearable style="width: 170px" @change="loadSources">
            <el-option v-for="t in FEED_TYPES" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
          <el-button :loading="loading" @click="loadSources">查询</el-button>
        </div>

        <el-table :data="sources" v-loading="loading" stripe>
          <el-table-column label="名称" min-width="180">
            <template #default="{ row }">
              <div class="src-name-row">
                <el-tag v-if="row.is_builtin" size="small" type="info" effect="plain">内置</el-tag>
                <span class="src-name">{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">{{ kindLabel(row.kind) }}</template>
          </el-table-column>
          <el-table-column label="分类" width="120">
            <template #default="{ row }">{{ typeLabel(row.source_type) }}</template>
          </el-table-column>
          <el-table-column label="地址" min-width="220" show-overflow-tooltip>
            <template #default="{ row }"><span class="src-url">{{ row.url }}</span></template>
          </el-table-column>
          <el-table-column label="条目数" width="90" align="center">
            <template #default="{ row }">{{ row.item_count }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'" effect="light">
                {{ row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最近入库" width="170">
            <template #default="{ row }">
              <span class="src-time">{{ formatTime(row.last_ingested_at) || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
              <el-button link size="small" :type="row.enabled ? 'warning' : 'success'" @click="toggleSource(row)">
                {{ row.enabled ? '停用' : '启用' }}
              </el-button>
              <el-button
                v-if="!row.is_builtin"
                link
                type="danger"
                size="small"
                @click="removeSource(row)"
              >删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && sources.length === 0" description="暂无资讯源" />
      </el-tab-pane>

      <!-- ============ 资讯条目 ============ -->
      <el-tab-pane label="资讯条目" name="items">
        <div class="filter-bar">
          <el-select v-model="itemTypeFilter" placeholder="按分类筛选" clearable style="width: 170px" @change="loadItems">
            <el-option v-for="t in FEED_TYPES" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
          <el-input
            v-model="itemKeyword"
            placeholder="搜索标题 / 摘要"
            clearable
            style="width: 260px"
            @keyup.enter="loadItems"
            @clear="loadItems"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button :loading="itemsLoading" @click="loadItems">查询</el-button>
        </div>

        <el-table :data="items" v-loading="itemsLoading" stripe>
          <el-table-column label="标题" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="item-title">
                <el-tag v-if="row.is_highlight" size="small" type="danger" effect="dark">置顶</el-tag>
                <el-link type="primary" :underline="false" :href="row.link" target="_blank">{{ row.title }}</el-link>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="分类" width="110">
            <template #default="{ row }">{{ typeLabel(row.source_type) }}</template>
          </el-table-column>
          <el-table-column label="来源" width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.source_name || row.feed_key }}</template>
          </el-table-column>
          <el-table-column label="发布时间" width="140">
            <template #default="{ row }">{{ formatTime(row.published_at || row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="toggleHighlight(row)">
                {{ row.is_highlight ? '取消置顶' : '置顶' }}
              </el-button>
              <el-button link type="danger" size="small" @click="removeItem(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrapper" v-if="itemTotal > 0">
          <el-pagination
            v-model:current-page="itemPage"
            v-model:page-size="itemPageSize"
            :page-sizes="[20, 50, 100]"
            :total="itemTotal"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleItemSizeChange"
            @current-change="loadItems"
          />
        </div>
        <el-empty v-else-if="!itemsLoading" description="暂无资讯条目，点击上方「触发抓取」获取" />
      </el-tab-pane>

      <!-- ============ 资讯账号画板：分类源节点 + 虚线连线 + 可拖拽账号卡片 ============ -->
      <el-tab-pane label="账号管理" name="accounts">
        <div class="filter-bar">
          <el-select v-model="accountEnabledFilter" placeholder="按状态筛选" clearable style="width: 150px" @change="loadAccounts">
            <el-option label="启用" value="on" />
            <el-option label="停用" value="off" />
          </el-select>
          <el-button :loading="accountsLoading" @click="loadAccounts">查询</el-button>
          <el-button @click="boardRef?.resetLayout()">重置布局</el-button>
          <div class="filter-spacer"></div>
          <el-button type="primary" :icon="Plus" @click="showAccountDialog()">新增资讯账号</el-button>
        </div>

        <MediaAccountBoard
          ref="boardRef"
          :accounts="accounts"
          :publishing-id="publishingId"
          @publish="publishNow"
          @edit="showAccountDialog"
          @toggle="toggleAccount"
          @remove="removeAccount"
        />
        <el-empty v-if="!accountsLoading && accounts.length === 0" description="暂无资讯账号，新增后自动在交流社区发布资讯帖" />
      </el-tab-pane>
    </el-tabs>

    <!-- 新增 / 编辑资讯账号 -->
    <el-dialog v-model="accountDialogVisible" :title="editingAccountId ? '编辑资讯账号' : '新增资讯账号'" width="560px">
      <el-form ref="accountFormRef" :model="accountForm" :rules="accountRules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="accountForm.name" maxlength="20" show-word-limit placeholder="展示在帖子作者位的名称，如：绵小城资讯站" />
        </el-form-item>
        <el-form-item label="头像" prop="avatar">
          <div class="avatar-row">
            <el-avatar :size="40" :src="accountForm.avatar || undefined">
              {{ (accountForm.name || '资').slice(0, 1) }}
            </el-avatar>
            <el-input v-model="accountForm.avatar" placeholder="可选，图片 URL；留空按名称首字显示" style="flex: 1" />
          </div>
        </el-form-item>
        <el-form-item label="签名" prop="signature">
          <el-input v-model="accountForm.signature" maxlength="30" show-word-limit placeholder="可选，展示在个人主页" />
        </el-form-item>
        <el-form-item label="内容方向" prop="content_scope">
          <el-select
            v-model="accountForm.content_scope" multiple collapse-tags collapse-tags-tooltip
            placeholder="不选 = 转发全部分类" style="width: 100%"
          >
            <el-option v-for="t in FEED_TYPES" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="发帖频率" prop="relay_interval_minutes">
          <el-select v-model="accountForm.relay_interval_minutes" style="width: 100%">
            <el-option v-for="o in RELAY_FREQ_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <span class="form-hint">控制逐条转发的最小间隔；「每日汇总」帖固定每天一条，不受此频率限制</span>
        </el-form-item>
        <el-form-item label="启用" prop="is_enabled">
          <el-switch v-model="accountForm.is_enabled" />
          <span class="form-hint">停用后不参与自动发帖；账号禁止登录，仅由系统发帖</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="accountDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="accountSaving" @click="handleAccountSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增 / 编辑资讯源 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑资讯源' : '新增资讯源'" width="620px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：某某科技官方" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.kind" style="width: 160px">
            <el-option v-for="k in KIND_OPTIONS" :key="k.value" :label="k.label" :value="k.value" />
          </el-select>
          <el-select v-model="form.source_type" style="width: 180px; margin-left: 10px">
            <el-option v-for="t in FEED_TYPES" :key="t.key" :label="t.label" :value="t.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="地址" required>
          <el-input v-model="form.url" placeholder="https:// RSS 订阅或网页地址" />
        </el-form-item>
        <el-form-item label="查询参数">
          <el-input v-model="form.query" placeholder="仅 API 类源（arxiv/github 等）需要，如 topic:ai-agent sort:stars" />
        </el-form-item>
        <el-form-item label="标题过滤">
          <el-input v-model="form.filter_kw_text" placeholder="可选，多个关键词用逗号分隔" />
        </el-form-item>
        <el-form-item label="每条上限">
          <el-input-number v-model="form.per_page" :min="1" :max="50" controls-position="right" />
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search, RefreshCw, Plus } from 'lucide-vue-next'
import MediaAccountBoard from '@/components/admin/MediaAccountBoard.vue'
import {
  getAdminFeedSources, createAdminFeedSource, updateAdminFeedSource, deleteAdminFeedSource,
  getAdminFeedItems, updateAdminFeedItem, deleteAdminFeedItem, refreshAdminFeeds,
  getAdminMediaAccounts, createAdminMediaAccount, updateAdminMediaAccount,
  deleteAdminMediaAccount, publishMediaDigest,
  type AdminFeedSource, type AdminFeedItem, type FeedSourceType, type MediaAccount,
} from '@/api/admin'

const FEED_TYPES: { key: FeedSourceType; label: string }[] = [
  { key: 'papers', label: 'AI 论文' },
  { key: 'opensource', label: '开源项目榜' },
  { key: 'agents', label: '智能体榜' },
  { key: 'news', label: '时政要闻' },
  { key: 'ai_news', label: 'AI 行业' },
  { key: 'rankings', label: '权威排行榜' },
  { key: 'cn_ai', label: '国产模型' },
]

const KIND_OPTIONS = [
  { value: 'rss', label: 'RSS 订阅' },
  { value: 'html', label: '网页解析' },
  { value: 'arxiv', label: 'arXiv API' },
  { value: 'github', label: 'GitHub API' },
  { value: 'gitee', label: 'Gitee API' },
  { value: 'lmarena', label: '权威榜 API' },
]

// 发帖频率（逐条转发的最小间隔，分钟）；0=不逐条转发，仅发每日汇总（展示文案在画板卡片上）
const RELAY_FREQ_OPTIONS = [
  { value: 30, label: '跟随抓取 · 约 30 分钟' },
  { value: 60, label: '每 1 小时' },
  { value: 180, label: '每 3 小时' },
  { value: 360, label: '每 6 小时' },
  { value: 720, label: '每 12 小时' },
  { value: 1440, label: '每天 1 次' },
  { value: 0, label: '不逐条转发 · 仅每日汇总' },
]

const activeTab = ref('sources')

// ---------- 资讯源 ----------
const sources = ref<AdminFeedSource[]>([])
const loading = ref(false)
const sourceTypeFilter = ref<FeedSourceType | ''>('')
const refreshing = ref(false)

const enabledCount = computed(() => sources.value.filter((s) => s.enabled).length)

async function loadSources() {
  loading.value = true
  try {
    sources.value = await getAdminFeedSources((sourceTypeFilter.value || 'all') as FeedSourceType | 'all')
  } catch {
    ElMessage.error('加载资讯源失败')
  } finally {
    loading.value = false
  }
}

async function handleRefreshFeeds() {
  refreshing.value = true
  try {
    const res = await refreshAdminFeeds((sourceTypeFilter.value || 'all') as FeedSourceType | 'all')
    ElMessage.success(`抓取完成：新增 ${res.inserted ?? 0} 条`)
    await reloadAll()
  } catch (e: any) {
    ElMessage.warning(e?.response?.data?.detail || '触发抓取失败，请稍后再试')
  } finally {
    refreshing.value = false
  }
}

// ---------- 新增 / 编辑 ----------
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({
  name: '',
  kind: 'rss',
  source_type: 'ai_news' as FeedSourceType,
  url: '',
  query: '',
  filter_kw_text: '',
  per_page: 10,
})

function resetForm() {
  form.value = { name: '', kind: 'rss', source_type: 'ai_news', url: '', query: '', filter_kw_text: '', per_page: 10 }
}

function showAddDialog() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function showEditDialog(row: AdminFeedSource) {
  editingId.value = row.id
  form.value = {
    name: row.name,
    kind: row.kind,
    source_type: row.source_type,
    url: row.url,
    query: row.query || '',
    filter_kw_text: (row.filter_kw || []).join(','),
    per_page: row.per_page,
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name.trim() || !form.value.url.trim()) {
    ElMessage.warning('名称与地址为必填项')
    return
  }
  saving.value = true
  const filter_kw = form.value.filter_kw_text
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
  try {
    if (editingId.value) {
      await updateAdminFeedSource(editingId.value, {
        name: form.value.name.trim(),
        url: form.value.url.trim(),
        query: form.value.query.trim() || null,
        filter_kw,
        per_page: form.value.per_page,
      })
      ElMessage.success('已更新')
    } else {
      await createAdminFeedSource({
        name: form.value.name.trim(),
        kind: form.value.kind as AdminFeedSource['kind'],
        source_type: form.value.source_type,
        url: form.value.url.trim(),
        query: form.value.query.trim() || null,
        filter_kw,
        per_page: form.value.per_page,
      })
      ElMessage.success('已新增，触发抓取后生效')
    }
    dialogVisible.value = false
    await loadSources()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleSource(row: AdminFeedSource) {
  try {
    await updateAdminFeedSource(row.id, { enabled: !row.enabled })
    ElMessage.success(row.enabled ? '已停用' : '已启用')
    await loadSources()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function removeSource(row: AdminFeedSource) {
  try {
    await ElMessageBox.confirm(`确认删除资讯源「${row.name}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteAdminFeedSource(row.id)
    ElMessage.success('已删除')
    await loadSources()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ---------- 资讯条目 ----------
const items = ref<AdminFeedItem[]>([])
const itemsLoading = ref(false)
const itemTypeFilter = ref<FeedSourceType | ''>('')
const itemKeyword = ref('')
const itemPage = ref(1)
const itemPageSize = ref(20)
const itemTotal = ref(0)
const typeCounts = ref<Record<string, number>>({})
const itemTotalAll = ref(0)
const latestIngest = ref('')

async function loadItems() {
  itemsLoading.value = true
  try {
    const res = await getAdminFeedItems({
      source_type: (itemTypeFilter.value || 'all') as FeedSourceType | 'all',
      q: itemKeyword.value.trim() || undefined,
      page: itemPage.value,
      page_size: itemPageSize.value,
    })
    items.value = res.items
    itemTotal.value = res.total
  } catch {
    ElMessage.error('加载资讯条目失败')
  } finally {
    itemsLoading.value = false
  }
}

function handleItemSizeChange() {
  itemPage.value = 1
  loadItems()
}

async function toggleHighlight(row: AdminFeedItem) {
  try {
    await updateAdminFeedItem(row.id, { is_highlight: !row.is_highlight })
    ElMessage.success(row.is_highlight ? '已取消置顶' : '已置顶')
    await loadItems()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function removeItem(row: AdminFeedItem) {
  try {
    await ElMessageBox.confirm(`确认删除该条资讯「${row.title}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteAdminFeedItem(row.id)
    ElMessage.success('已删除')
    await reloadAll()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ---------- 资讯账号 ----------
const accounts = ref<MediaAccount[]>([])
const accountsLoading = ref(false)
const accountEnabledFilter = ref<'on' | 'off' | ''>('')
const publishingId = ref<number | null>(null)
const boardRef = ref<InstanceType<typeof MediaAccountBoard>>()

async function loadAccounts() {
  accountsLoading.value = true
  try {
    let list = await getAdminMediaAccounts()
    if (accountEnabledFilter.value === 'on') list = list.filter((a) => a.is_enabled)
    if (accountEnabledFilter.value === 'off') list = list.filter((a) => !a.is_enabled)
    accounts.value = list
  } catch {
    ElMessage.error('加载资讯账号失败')
  } finally {
    accountsLoading.value = false
  }
}

// ---------- 新增 / 编辑账号 ----------
const accountDialogVisible = ref(false)
const editingAccountId = ref<number | null>(null)
const accountSaving = ref(false)
const accountFormRef = ref<FormInstance>()
const accountForm = ref({
  name: '',
  avatar: '',
  signature: '',
  content_scope: [] as FeedSourceType[],
  relay_interval_minutes: 30,
  is_enabled: true,
})
const accountRules: FormRules = {
  name: [{ required: true, message: '请填写账号名称', trigger: 'blur' }],
}

function showAccountDialog(row?: MediaAccount) {
  editingAccountId.value = row ? row.id : null
  accountForm.value = row
    ? {
        name: row.name,
        avatar: row.avatar || '',
        signature: row.signature || '',
        content_scope: row.content_scope || [],
        relay_interval_minutes: row.relay_interval_minutes ?? 30,
        is_enabled: row.is_enabled,
      }
    : { name: '', avatar: '', signature: '', content_scope: [], relay_interval_minutes: 30, is_enabled: true }
  accountDialogVisible.value = true
}

async function handleAccountSave() {
  const valid = await accountFormRef.value?.validate().catch(() => false)
  if (!valid) return
  accountSaving.value = true
  const body = {
    name: accountForm.value.name.trim(),
    avatar: accountForm.value.avatar.trim() || null,
    signature: accountForm.value.signature.trim() || null,
    content_scope: accountForm.value.content_scope.length ? accountForm.value.content_scope : null,
    relay_interval_minutes: accountForm.value.relay_interval_minutes,
    is_enabled: accountForm.value.is_enabled,
  }
  try {
    if (editingAccountId.value) {
      await updateAdminMediaAccount(editingAccountId.value, body)
      ElMessage.success('已更新')
    } else {
      await createAdminMediaAccount(body)
      ElMessage.success('已新增资讯账号')
    }
    accountDialogVisible.value = false
    await loadAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    accountSaving.value = false
  }
}

async function toggleAccount(row: MediaAccount) {
  try {
    await updateAdminMediaAccount(row.id, { is_enabled: !row.is_enabled })
    ElMessage.success(row.is_enabled ? '已停用' : '已启用')
    await loadAccounts()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function publishNow(row: MediaAccount) {
  publishingId.value = row.id
  try {
    const res = await publishMediaDigest(row.id)
    if (res.posted) {
      ElMessage.success(`已发布「${res.title}」`)
      await loadAccounts()
    } else {
      // 今日已发过：询问是否覆盖重发
      try {
        await ElMessageBox.confirm(`${res.message}，是否覆盖重发？`, '覆盖确认', { type: 'warning' })
      } catch {
        return
      }
      const forced = await publishMediaDigest(row.id, true)
      if (forced.posted) {
        ElMessage.success(`已覆盖发布「${forced.title}」`)
        await loadAccounts()
      } else {
        ElMessage.info(forced.message)
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败，请稍后再试')
  } finally {
    publishingId.value = null
  }
}

async function removeAccount(row: MediaAccount) {
  try {
    await ElMessageBox.confirm(
      `确认删除资讯账号「${row.name}」？该账号已发布的帖子与互动数据将一并删除，不可恢复。`,
      '删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await deleteAdminMediaAccount(row.id)
    ElMessage.success('已删除')
    await loadAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// 概览统计：由全量资讯源条目数聚合分类计数，并取最新一条作为「最近抓取」参考
async function loadOverview() {
  try {
    const [allSources, latest] = await Promise.all([
      getAdminFeedSources('all'),
      getAdminFeedItems({ source_type: 'all', page: 1, page_size: 1 }),
    ])
    itemTotalAll.value = latest.total
    latestIngest.value = latest.items.length
      ? formatTime(latest.items[0].created_at)
      : ''
    const counts: Record<string, number> = {}
    for (const s of allSources) {
      if (s.item_count > 0) {
        counts[s.source_type] = (counts[s.source_type] || 0) + s.item_count
      }
    }
    typeCounts.value = counts
  } catch {
    /* 概览失败不影响主流程 */
  }
}

async function reloadAll() {
  await Promise.all([loadSources(), loadItems(), loadOverview(), loadAccounts()])
}

// ---------- 工具 ----------
const kindLabel = (k: string) =>
  ({ rss: 'RSS', html: '网页', arxiv: 'arXiv', github: 'GitHub', gitee: 'Gitee', lmarena: '权威榜' }[k] || k)
const typeLabel = (t: string) => FEED_TYPES.find((x) => x.key === t)?.label || t

function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return String(t).slice(0, 19)
  return d.toLocaleString('zh-CN', { hour12: false })
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped>
.feed-admin-page {
  min-height: 100%;
}
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
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: #f8faff;
  border: 1px solid #e3e8f7;
  border-radius: 12px;
  padding: 14px 16px;
}
.stat-label {
  font-size: 12px;
  color: #7b8498;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 4px;
  word-break: break-all;
}
.stat-value.small {
  font-size: 15px;
}
.stat-desc {
  font-size: 12px;
  color: #8a94a6;
}
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.src-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.src-name {
  font-weight: 600;
  color: #334155;
}
.src-url {
  font-size: 12.5px;
  color: #64748b;
  word-break: break-all;
}
.src-time {
  font-size: 12.5px;
  color: #64748b;
}
.item-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.filter-spacer {
  flex: 1;
}
.avatar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: #94a3b8;
}
</style>