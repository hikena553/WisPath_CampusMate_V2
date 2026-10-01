<template>
  <div class="crisis-monitor-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>危机预警监控</h2>
        <p class="page-sub">全校学生 AI 心理预警闭环监控：发现 → 干预 → 随访 → 闭环（与教师端数据同源实时同步）</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadAlerts">刷新</el-button>
    </div>

    <!-- 危机预警算法：回显算法设计 + 管理员调控 -->
    <div class="algo-panel">
      <div class="algo-head">
        <div class="algo-title">
          <span class="algo-name">
            <el-icon class="algo-ic"><Setting /></el-icon>
            心理危机预警算法
          </span>
          <span class="algo-badge"><i></i>运行中</span>
          <span class="algo-desc">关键词规则匹配 · LLM 语义分级 · 脱敏摘要生成 · 干预闭环</span>
        </div>
        <el-button text size="small" :icon="Setting" @click="configOpen = !configOpen">
          {{ configOpen ? '收起调控' : '调控设置' }}
        </el-button>
      </div>

      <!-- 算法流程回显 -->
      <div class="algo-flow">
        <div class="flow-node">
          <span class="flow-no">1</span>
          <div class="flow-main"><b>关键词规则层</b><i>命中预警敏感词库即触发候选（当前 {{ config.keywords.length }} 词）</i></div>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-node">
          <span class="flow-no">2</span>
          <div class="flow-main"><b>LLM 语义分级</b><i>结合上下文判定风险等级并提取情绪特征</i></div>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-node">
          <span class="flow-no">3</span>
          <div class="flow-main"><b>脱敏摘要生成</b><i>不含姓名、班级、学号等可识别信息</i></div>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-node">
          <span class="flow-no">4</span>
          <div class="flow-main"><b>预警上报与干预闭环</b><i>记录预警 → 通知辅导员 → 干预随访</i></div>
        </div>
      </div>

      <!-- 等级判定规则 -->
      <div class="algo-levels">
        <div class="lvl lvl-danger"><b>severe 严重</b><i>明确自杀 / 自残倾向</i><em>立即干预</em></div>
        <div class="lvl lvl-warn"><b>moderate 中度</b><i>明显焦虑、抑郁、压力过大</i><em>重点关注</em></div>
        <div class="lvl lvl-mild"><b>mild 轻度</b><i>轻度情绪困扰</i><em>观察随访</em></div>
      </div>

      <!-- 调控设置区 -->
      <el-collapse-transition>
        <div v-show="configOpen" class="algo-controls">
          <div class="ctrl-item ctrl-keywords">
            <div class="ctrl-label">
              预警敏感词（逗号分隔）
              <span class="ctrl-hint">命中任一词语即进入语义分级，保存后实时生效</span>
            </div>
            <el-select
              v-model="editKeywords"
              multiple
              filterable
              allow-create
              default-first-option
              collapse-tags
              :max-collapse-tags="3"
              placeholder="输入或粘贴敏感词，回车生成标签（如：失眠、焦虑）"
               empty-text="输入后回车添加"
            />
            <div v-if="normalizedKeywords.length" class="ctrl-tags-count">将保存 {{ normalizedKeywords.length }} 个词组</div>
          </div>
          <div class="ctrl-item ctrl-switch">
            <div class="ctrl-label">
              自动通知辅导员
              <span class="ctrl-hint">产生严重 / 中度预警时自动推送</span>
            </div>
            <el-switch v-model="editNotify" active-text="开启" inactive-text="关闭" inline-prompt />
          </div>
          <div class="ctrl-actions">
            <el-button size="small" @click="resetConfig">恢复默认词库</el-button>
            <el-button size="small" type="primary" :icon="Check" :loading="savingConfig" @click="saveConfig">保存配置</el-button>
          </div>
        </div>
      </el-collapse-transition>
    </div>

    <!-- 统计总览 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ alerts.length }}</div>
        <div class="stat-label">全部预警</div>
      </div>
      <div class="stat-card">
        <div class="stat-value warn">{{ unresolved.length }}</div>
        <div class="stat-label">待处置</div>
      </div>
      <div class="stat-card">
        <div class="stat-value danger">{{ highRisk.length }}</div>
        <div class="stat-label">高危未闭环</div>
      </div>
      <div class="stat-card">
        <div class="stat-value success">{{ intervenedCount }}</div>
        <div class="stat-label">已干预</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-radio-group v-model="filter" size="small">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="unresolved">待处置</el-radio-button>
        <el-radio-button value="resolved">已闭环</el-radio-button>
      </el-radio-group>
      <el-select v-model="levelFilter" placeholder="风险等级" clearable size="small" style="width:130px">
        <el-option label="正常" value="normal" />
        <el-option label="轻度" value="mild" />
        <el-option label="中度" value="moderate" />
        <el-option label="严重" value="severe" />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="搜索学生姓名"
        clearable
        size="small"
        style="width:180px"
        :prefix-icon="Search"
      />
    </div>

    <!-- 预警列表 -->
    <el-table v-loading="loading" :data="filteredAlerts" style="width:100%" empty-text="暂无预警记录">
      <el-table-column label="学生" min-width="170">
        <template #default="{ row }">
          <div class="stu-cell">
            <span class="stu-avatar" :style="{ background: levelColor(row.level) }">{{ row.student_name.slice(0, 1) }}</span>
            <span class="stu-name">{{ row.student_name }}</span>
            <span class="stu-id">#{{ row.student_id }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="等级" width="90">
        <template #default="{ row }">
          <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="预警时间" width="160">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="风险摘要" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">{{ row.summary }}</template>
      </el-table-column>
      <el-table-column label="匹配关键词" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="row.keywords_matched">
            <el-tag v-for="kw in splitKeywords(row.keywords_matched)" :key="kw" size="small" type="danger" effect="plain" style="margin-right:4px">
              {{ kw }}
            </el-tag>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="处置记录" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="row.intervention_type">
            <el-tag size="small" type="success" effect="light" style="margin-right:4px">{{ row.intervention_type }}</el-tag>
            <span class="note-text">{{ row.intervention_note || '未填写备注' }}</span>
          </template>
          <span v-else class="note-text muted">尚未干预</span>
        </template>
      </el-table-column>
      <el-table-column label="随访日期" width="100">
        <template #default="{ row }">
          <span :class="{ 'overdue': isOverdue(row.follow_up_date) && !row.resolved }">{{ row.follow_up_date || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.resolved ? 'success' : 'warning'" size="small" effect="plain">
            {{ row.resolved ? '已闭环' : '待处置' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-tooltip content="干预处置" placement="top">
              <el-button class="action-btn primary" circle :disabled="row.resolved" @click="openIntervene(row)">
                <el-icon><FirstAidKit /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip :content="row.resolved ? '已闭环' : '标记闭环'" placement="top">
              <el-button
                v-if="!row.resolved"
                class="action-btn success" circle
                @click="openIntervene(row, true)"
              >
                <el-icon><Check /></el-icon>
              </el-button>
              <el-button v-else class="action-btn info" circle disabled>
                <el-icon><Check /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="filteredAlerts.length > 0 || alerts.length > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="filteredAlerts.length"
        layout="total, sizes, prev, pager, next, jumper"
      />
    </div>

    <!-- 干预弹窗 -->
    <el-dialog v-model="dialogVisible" title="预警干预处置" width="640px" destroy-on-close>
      <el-form label-width="100px" v-if="current">
        <div class="form-grid-2">
          <el-form-item label="学生">
            <span style="font-weight:600">{{ current.student_name }}</span>
            <el-tag :type="levelTagType(current.level)" size="small" effect="dark" style="margin-left:8px">
              {{ levelText(current.level) }}
            </el-tag>
          </el-form-item>
          <el-form-item label="随访日期">
            <el-date-picker v-model="form.follow_up_date" type="date" value-format="YYYY-MM-DD" placeholder="计划跟进时间" style="width:100%" />
          </el-form-item>
        </div>
        <el-form-item label="风险摘要">
          <div class="summary-box">{{ current.summary }}</div>
        </el-form-item>
        <el-form-item label="干预方式">
          <el-radio-group v-model="form.intervention_type">
            <el-radio value="谈话">谈话疏导</el-radio>
            <el-radio value="约谈家长">约谈家长</el-radio>
            <el-radio value="转介心理咨询">转介心理咨询</el-radio>
            <el-radio value="其他">其他</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处置备注">
          <el-input v-model="form.intervention_note" type="textarea" :rows="3" placeholder="记录本次处置过程，供后续随访参考……" maxlength="300" show-word-limit />
        </el-form-item>
        <el-form-item label="处置结果">
          <el-switch v-model="form.resolved" active-text="已闭环" inactive-text="持续跟进" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitIntervene">保存处置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh, Search, FirstAidKit, Check, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAlerts, interveneAlert, getCrisisConfig, updateCrisisConfig, type CrisisConfig } from '@/api/crisis'
import type { CrisisAlert } from '@/types'

const alerts = ref<CrisisAlert[]>([])
const loading = ref(false)
const filter = ref<'all' | 'unresolved' | 'resolved'>('all')
const levelFilter = ref('')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const dialogVisible = ref(false)
const current = ref<CrisisAlert | null>(null)
const submitting = ref(false)
const form = ref({
  intervention_type: '谈话',
  intervention_note: '',
  follow_up_date: '',
  resolved: true,
})

// ===== 危机预警算法配置 =====
const config = ref<CrisisConfig>({ keywords: [], notify_counselor: false, default_keywords: [] })
const configOpen = ref(false)
const editKeywords = ref<string[]>([])
const editNotify = ref(false)
const savingConfig = ref(false)

/** 展开逗号分隔的条目并去重，得到最终保存的词组 */
const normalizedKeywords = computed(() => {
  const list: string[] = []
  for (const raw of editKeywords.value) {
    for (const part of raw.split(/[,，、;；\s]+/)) {
      const p = part.trim()
      if (p && !list.includes(p)) list.push(p)
    }
  }
  return list
})

async function loadConfig() {
  try {
    config.value = await getCrisisConfig()
    editKeywords.value = [...config.value.keywords]
    editNotify.value = config.value.notify_counselor
  } catch (error) {
    console.error('加载算法配置失败:', error)
  }
}

async function saveConfig() {
  const keywords = normalizedKeywords.value
  if (!keywords.length) {
    ElMessage.warning('预警敏感词不能为空')
    return
  }
  savingConfig.value = true
  try {
    const res = await updateCrisisConfig({ keywords, notify_counselor: editNotify.value })
    config.value.keywords = res.keywords
    config.value.notify_counselor = res.notify_counselor
    editKeywords.value = [...res.keywords]
    editNotify.value = res.notify_counselor
    ElMessage.success(`${res.message}，新词库实时生效`)
  } catch (error) {
    console.error('保存算法配置失败:', error)
    ElMessage.error('保存算法配置失败')
  } finally {
    savingConfig.value = false
  }
}

function resetConfig() {
  editKeywords.value = [...config.value.default_keywords]
  ElMessage.info('已恢复默认词库，点击「保存配置」生效')
}

const unresolved = computed(() => alerts.value.filter(a => !a.resolved))
const highRisk = computed(() => alerts.value.filter(a => !a.resolved && a.level === 'severe'))
const intervenedCount = computed(() => alerts.value.filter(a => a.intervention_type).length)

const filteredAlerts = computed(() => {
  let list = alerts.value
  if (filter.value === 'unresolved') list = list.filter(a => !a.resolved)
  if (filter.value === 'resolved') list = list.filter(a => a.resolved)
  if (levelFilter.value) list = list.filter(a => a.level === levelFilter.value)
  if (keyword.value.trim()) {
    const kw = keyword.value.trim().toLowerCase()
    list = list.filter(a => a.student_name.toLowerCase().includes(kw))
  }
  const start = (currentPage.value - 1) * pageSize.value
  return list.slice(start, start + pageSize.value)
})

async function loadAlerts() {
  loading.value = true
  try {
    alerts.value = await getAlerts()
  } catch (error) {
    console.error('加载预警失败:', error)
    ElMessage.error('加载预警列表失败')
  } finally {
    loading.value = false
  }
}

function openIntervene(row: CrisisAlert, justResolve = false) {
  current.value = row
  form.value = {
    intervention_type: row.intervention_type || '谈话',
    intervention_note: row.intervention_note || '',
    follow_up_date: row.follow_up_date || '',
    resolved: !justResolve,
  }
  dialogVisible.value = true
}

async function submitIntervene() {
  if (!current.value) return
  submitting.value = true
  try {
    await interveneAlert(current.value.id, {
      intervention_type: form.value.intervention_type,
      intervention_note: form.value.intervention_note,
      follow_up_date: form.value.follow_up_date,
      resolved: form.value.resolved,
    })
    ElMessage.success('处置记录已保存')
    dialogVisible.value = false
    loadAlerts()
  } catch (error) {
    console.error('保存处置失败:', error)
    ElMessage.error('保存处置失败')
  } finally {
    submitting.value = false
  }
}

function splitKeywords(kw: string) {
  return kw.split(/[,，、;\s]+/).filter(Boolean).slice(0, 4)
}

function formatTime(t: string) {
  if (!t) return '—'
  return t.replace('T', ' ').slice(0, 16)
}

function isOverdue(date: string | null) {
  if (!date) return false
  return new Date(date).getTime() < Date.now()
}

function levelTagType(level: string) {
  const map: Record<string, string> = { normal: 'info', mild: 'success', moderate: 'warning', severe: 'danger' }
  return map[level] || 'info'
}

function levelText(level: string) {
  const map: Record<string, string> = { normal: '正常', mild: '轻度', moderate: '中度', severe: '严重' }
  return map[level] || level
}

function levelColor(level: string) {
  const map: Record<string, string> = { normal: '#909399', mild: '#67c23a', moderate: '#e6a23c', severe: '#f56c6c' }
  return map[level] || '#909399'
}

onMounted(() => {
  loadAlerts()
  loadConfig()
})
</script>

<style scoped>
.crisis-monitor-page {
  padding: 24px 28px;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0 0 4px;
}

.page-sub {
  font-size: 13px;
  color: #8a94a6;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

/* ===== 危机预警算法面板 ===== */
.algo-panel {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  padding: 14px 18px;
  margin-bottom: 16px;
}

.algo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.algo-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.algo-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 700;
  color: #1f2d3d;
}

.algo-ic {
  color: #409eff;
  font-size: 16px;
}

.algo-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
  border-radius: 20px;
  padding: 1px 10px;
}

.algo-badge i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
  animation: algo-pulse 1.6s ease-in-out infinite;
}

@keyframes algo-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.45); }
  50% { box-shadow: 0 0 0 5px rgba(103, 194, 58, 0); }
}

.algo-desc {
  font-size: 12px;
  color: #8a94a6;
}

.algo-flow {
  display: flex;
  align-items: stretch;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.flow-node {
  flex: 1 1 170px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: #f7f9fc;
  border: 1px solid #eef0f4;
  border-radius: 10px;
  padding: 10px 12px;
  min-width: 150px;
}

.flow-no {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.flow-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.flow-main b {
  font-size: 13px;
  color: #1f2937;
}

.flow-main i {
  font-style: normal;
  font-size: 11.5px;
  color: #8a94a6;
  line-height: 1.5;
}

.flow-arrow {
  align-self: center;
  color: #c0c8d4;
  font-size: 15px;
  font-style: normal;
}

.algo-levels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 4px;
}

.lvl {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 12px;
}

.lvl b { font-size: 12.5px; }
.lvl i { font-style: normal; color: #4b5563; flex: 1; }
.lvl em { font-style: normal; font-weight: 600; font-size: 11.5px; }

.lvl-danger { background: rgba(245, 108, 108, 0.08); border: 1px solid rgba(245, 108, 108, 0.25); }
.lvl-danger b { color: #f56c6c; }
.lvl-danger em { color: #f56c6c; }

.lvl-warn { background: rgba(230, 162, 60, 0.08); border: 1px solid rgba(230, 162, 60, 0.25); }
.lvl-warn b { color: #e6a23c; }
.lvl-warn em { color: #e6a23c; }

.lvl-mild { background: rgba(103, 194, 58, 0.08); border: 1px solid rgba(103, 194, 58, 0.25); }
.lvl-mild b { color: #67c23a; }
.lvl-mild em { color: #67c23a; }

.algo-controls {
  border-top: 1px dashed #e8ecf2;
  margin-top: 12px;
  padding-top: 14px;
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 24px;
  align-items: start;
}

.ctrl-keywords {
  min-width: 0;
}

.ctrl-keywords :deep(.el-select) {
  width: 100%;
}

.ctrl-keywords :deep(.el-select__wrapper) {
  border-radius: 8px;
  padding: 4px 10px;
  min-height: 36px;
  box-shadow: 0 0 0 1px #dfe4ec inset;
  transition: box-shadow 0.2s ease;
}

.ctrl-keywords :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px #c8d2e0 inset;
}

.ctrl-keywords :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1.5px #409eff inset;
}

.ctrl-keywords :deep(.el-select__selection) {
  gap: 2px 6px;
}

.ctrl-keywords :deep(.el-tag) {
  border-radius: 6px;
  height: 24px;
}

.ctrl-switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 36px;
  padding: 2px 0;
}

.ctrl-switch .ctrl-label {
  margin-bottom: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}

.ctrl-label {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ctrl-hint {
  font-weight: 400;
  font-size: 11.5px;
  color: #9aa4b2;
  white-space: nowrap;
}

.ctrl-tags-count {
  font-size: 11.5px;
  color: #9aa4b2;
  margin-top: 8px;
}

.ctrl-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  grid-column: 1 / -1;
  padding-top: 4px;
}

@media (max-width: 900px) {
  .algo-controls { grid-template-columns: 1fr; gap: 16px; }
  .ctrl-actions { justify-content: flex-start; }
  .flow-arrow { display: none; }
}

.stat-card {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2d3d;
}

.stat-value.warn { color: #e6a23c; }
.stat-value.danger { color: #f56c6c; }
.stat-value.success { color: #67c23a; }

.stat-label {
  font-size: 12px;
  color: #8a94a6;
  margin-top: 4px;
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  align-items: center;
}

.stu-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.stu-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: #fff;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stu-name {
  font-weight: 600;
  font-size: 13.5px;
  color: #1f2937;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stu-id {
  font-size: 11px;
  color: #b0b8c4;
  flex-shrink: 0;
  margin-left: 2px;
}

.note-text {
  font-size: 12.5px;
  color: #4b5563;
}

.muted {
  color: #b0b8c4;
}

.overdue {
  color: #f56c6c;
  font-weight: 600;
}

.summary-box {
  background: #f7f9fc;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  color: #4b5563;
  width: 100%;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>