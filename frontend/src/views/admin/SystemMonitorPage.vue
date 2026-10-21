<template>
  <div class="system-page">
    <div class="page-header">
      <div class="header-left">
        <h2>系统监控与运维</h2>
        <span class="header-sub">项目基底监控：服务 / 数据库 / 后台任务 / 外部集成 + 全站功能模块注册表与维护入口</span>
      </div>
      <div class="header-actions">
        <el-button :icon="RefreshCw" :loading="loading" @click="loadOverview">刷新监控</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <!-- 顶部状态卡 -->
      <div class="stat-cards" v-if="overview">
        <div class="stat-card">
          <div class="stat-label">服务状态</div>
          <div class="stat-value">
            <el-tag :type="overview.service.status === 'ok' ? 'success' : 'warning'" effect="dark">
              {{ overview.service.status === 'ok' ? '运行中' : overview.service.status }}
            </el-tag>
          </div>
          <div class="stat-desc">
            版本 {{ overview.service.version }} · {{ overview.service.env }} · Python {{ overview.service.python }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">持续运行</div>
          <div class="stat-value">{{ formatUptime(overview.service.uptime_seconds) }}</div>
          <div class="stat-desc">启动于 {{ formatTime(overview.service.started_at) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">数据库</div>
          <div class="stat-value">
            <el-tag :type="overview.database.reachable ? 'success' : 'danger'" effect="light">
              {{ overview.database.reachable ? '连接正常' : '不可达' }}
            </el-tag>
          </div>
          <div class="stat-desc">{{ overview.database.dialect }} · {{ overview.database.target }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">外部资讯</div>
          <div class="stat-value">{{ overview.feeds.item_total }}</div>
          <div class="stat-desc">
            资讯源 {{ overview.feeds.source_enabled }}/{{ overview.feeds.source_total }} 启用 ·
            {{ overview.feeds.last_ingested_at ? '最近 ' + formatTime(overview.feeds.last_ingested_at) : '尚未抓取' }}
          </div>
        </div>
      </div>

      <div class="grid-2" v-if="overview">
        <!-- 后台周期任务 -->
        <el-card shadow="never" class="panel">
          <template #header><span class="panel-title">后台周期任务</span></template>
          <el-table :data="overview.background_tasks" size="small">
            <el-table-column prop="name" label="任务" width="150" />
            <el-table-column label="间隔" width="90">
              <template #default="{ row }">{{ formatInterval(row.interval_seconds) }}</template>
            </el-table-column>
            <el-table-column prop="desc" label="说明" min-width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="80">
              <template #default><el-tag size="small" type="success" effect="plain">运行中</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 外部集成 -->
        <el-card shadow="never" class="panel">
          <template #header><span class="panel-title">外部集成配置</span></template>
          <div class="integration-list">
            <div class="integration-item">
              <span class="int-name">大模型 API（LLM）</span>
              <el-tag size="small" :type="overview.integrations.llm_configured ? 'success' : 'warning'" effect="light">
                {{ overview.integrations.llm_configured ? '已配置' : '未配置' }}
              </el-tag>
            </div>
            <div class="integration-item">
              <span class="int-name">文本向量模型</span>
              <el-tag size="small" :type="overview.integrations.embedding_configured ? 'success' : 'warning'" effect="light">
                {{ overview.integrations.embedding_configured ? overview.integrations.embedding_model : '未配置' }}
              </el-tag>
            </div>
            <div class="integration-item">
              <span class="int-name">GitHub Token</span>
              <el-tag size="small" :type="overview.integrations.github_token_set ? 'success' : 'info'" effect="light">
                {{ overview.integrations.github_token_set ? '已配置' : '未配置' }}
              </el-tag>
            </div>
            <div class="integration-item">
              <span class="int-name">Gitee Token</span>
              <el-tag size="small" :type="overview.integrations.gitee_token_set ? 'success' : 'info'" effect="light">
                {{ overview.integrations.gitee_token_set ? '已配置' : '未配置' }}
              </el-tag>
            </div>
            <div class="integration-item">
              <span class="int-name">Sentry 错误监控</span>
              <el-tag size="small" :type="overview.integrations.sentry_configured ? 'success' : 'info'" effect="light">
                {{ overview.integrations.sentry_configured ? '已启用' : '未启用' }}
              </el-tag>
            </div>
            <div class="integration-item">
              <span class="int-name">知识库检索模型</span>
              <el-tag size="small" type="info" effect="light">{{ overview.knowledge.segmenter }}</el-tag>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 知识库索引 + 数据库规模 -->
      <div class="grid-2" v-if="overview">
        <el-card shadow="never" class="panel">
          <template #header><span class="panel-title">知识库索引状态</span></template>
          <div class="kv-list">
            <div class="kv-item"><span>问答对</span><b>{{ overview.knowledge.qa_count }}</b></div>
            <div class="kv-item"><span>外部数据源</span><b>{{ overview.knowledge.document_count }}</b></div>
            <div class="kv-item"><span>文档分块</span><b>{{ overview.knowledge.total_chunks }}</b></div>
            <div class="kv-item"><span>已向量化分块</span><b>{{ overview.knowledge.indexed_chunks }}</b></div>
          </div>
          <div class="progress-line">
            <span class="progress-label">索引覆盖率 {{ overview.knowledge.index_coverage }}%</span>
            <el-progress :percentage="overview.knowledge.index_coverage" :show-text="false" :stroke-width="8" />
          </div>
        </el-card>

        <el-card shadow="never" class="panel">
          <template #header><span class="panel-title">数据库数据规模</span></template>
          <el-table :data="tableCountRows" size="small" max-height="260">
            <el-table-column prop="table" label="数据表" min-width="180" />
            <el-table-column prop="count" label="行数" width="120" align="right">
              <template #default="{ row }">{{ row.count.toLocaleString('zh-CN') }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 功能模块注册表 -->
      <el-card shadow="never" class="panel full" v-if="overview">
        <template #header>
          <div class="panel-head-row">
            <span class="panel-title">全站功能模块注册表</span>
            <span class="panel-note">共 {{ overview.modules.length }} 个功能域 · {{ totalRoutes }} 个接口，用于功能维护与巡检</span>
          </div>
        </template>
        <el-table :data="overview.modules" size="small" max-height="360">
          <el-table-column prop="prefix" label="接口前缀" min-width="200" />
          <el-table-column label="模块标签" min-width="200">
            <template #default="{ row }">
              <el-tag v-for="t in row.tags" :key="t" size="small" effect="plain" class="mod-tag">{{ t }}</el-tag>
              <span v-if="!row.tags.length">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="route_count" label="接口数" width="100" align="right" />
        </el-table>
      </el-card>

      <!-- 维护动作 -->
      <el-card shadow="never" class="panel full">
        <template #header><span class="panel-title">运维维护动作</span></template>
        <div class="maint-actions">
          <el-button type="primary" :loading="maintLoading === 'refresh_feeds'" @click="doMaintenance('refresh_feeds')">
            手动触发外部资讯抓取
          </el-button>
          <el-button type="warning" :loading="maintLoading === 'reindex_knowledge'" @click="doMaintenance('reindex_knowledge')">
            重建知识库向量索引
          </el-button>
        </div>
        <el-alert
          v-if="maintResult"
          :title="maintResult.title"
          :type="maintResult.type"
          :closable="true"
          show-icon
          style="margin-top: 12px"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshCw } from 'lucide-vue-next'
import { getSystemOverview, runMaintenance, type SystemOverview } from '@/api/admin'

const overview = ref<SystemOverview | null>(null)
const loading = ref(false)
const maintLoading = ref('')
const maintResult = ref<{ title: string; type: 'success' | 'warning' | 'error' } | null>(null)

const tableCountRows = computed(() => {
  const counts = overview.value?.database.table_counts || {}
  return Object.entries(counts)
    .map(([table, count]) => ({ table, count }))
    .sort((a, b) => b.count - a.count)
})

const totalRoutes = computed(() =>
  (overview.value?.modules || []).reduce((sum, m) => sum + m.route_count, 0),
)

async function loadOverview() {
  loading.value = true
  try {
    overview.value = await getSystemOverview()
  } catch {
    ElMessage.error('加载系统监控失败')
  } finally {
    loading.value = false
  }
}

async function doMaintenance(action: 'refresh_feeds' | 'reindex_knowledge') {
  maintLoading.value = action
  maintResult.value = null
  try {
    const res = await runMaintenance(action)
    if (action === 'refresh_feeds') {
      maintResult.value = {
        title: `抓取完成：新增 ${res.result?.inserted ?? 0} 条外部资讯`,
        type: 'success',
      }
    } else {
      maintResult.value = res.result?.error
        ? { title: `重建完成（部分跳过）：${res.result.error}`, type: 'warning' }
        : { title: `向量索引重建完成：新增 ${res.result?.indexed ?? 0} 块`, type: 'success' }
    }
    await loadOverview()
  } catch (e: any) {
    maintResult.value = { title: e?.response?.data?.detail || '维护动作失败', type: 'error' }
  } finally {
    maintLoading.value = ''
  }
}

function formatUptime(seconds: number) {
  const s = Math.max(0, Math.floor(seconds))
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d} 天 ${h} 小时`
  if (h > 0) return `${h} 小时 ${m} 分`
  return `${m} 分 ${s % 60} 秒`
}

function formatInterval(seconds: number) {
  if (seconds >= 3600) return `${Math.round(seconds / 3600)} 小时`
  if (seconds >= 60) return `${Math.round(seconds / 60)} 分钟`
  return `${seconds} 秒`
}

function formatTime(t: string | null) {
  if (!t) return '—'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return String(t).slice(0, 19)
  return d.toLocaleString('zh-CN', { hour12: false })
}

onMounted(loadOverview)
</script>

<style scoped>
.system-page {
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
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
  margin-bottom: 6px;
}
.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 6px;
  word-break: break-all;
}
.stat-desc {
  font-size: 12px;
  color: #8a94a6;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.panel {
  border-radius: 12px;
}
.panel.full {
  margin-bottom: 12px;
}
.panel-title {
  font-weight: 600;
  color: #334155;
  font-size: 14px;
}
.panel-head-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.panel-note {
  font-size: 12px;
  color: #94a3b8;
}
.integration-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.integration-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  background: #f7f9fc;
  border-radius: 8px;
  font-size: 13px;
  color: #4b5563;
}
.kv-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.kv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f7f9fc;
  border-radius: 8px;
  font-size: 13px;
  color: #6b7280;
}
.kv-item b {
  color: #1f2d3d;
  font-size: 16px;
}
.progress-line {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.progress-label {
  font-size: 12.5px;
  color: #64748b;
}
.mod-tag {
  margin-right: 6px;
}
.maint-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>