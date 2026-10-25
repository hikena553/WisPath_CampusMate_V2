<template>
  <div class="tui-page">
    <SubPageHeader title="家校沟通" sub="家长零账号可完整留痕" fallback="/teacher">
      <!-- 移动端吸顶栏「更多」：导出 / 模板 / 导入（桌面端不渲染 #right，改由 TuiPageHero 承载） -->
      <template #right>
        <el-dropdown trigger="click" @command="onHeadCommand">
          <button class="gp-more-btn" type="button" aria-label="更多操作">
            <el-icon :size="18"><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="export"><el-icon><Download /></el-icon>导出台账 Excel</el-dropdown-item>
              <el-dropdown-item command="template"><el-icon><Document /></el-icon>下载导入模板</el-dropdown-item>
              <el-dropdown-item command="import" divided><el-icon><Upload /></el-icon>导入台账 Excel</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <!-- 桌面端特色头部：沟通语义色 + 会话图标；右侧保留本页专属的「学生选择器 + 更多」 -->
      <TuiPageHero
        v-if="!isMobile"
        title="家校沟通"
        sub="家长零账号可完整留痕：短信提示 · 报告导出 · 只读链接"
        :icon="ChatDotRound"
        tone="violet"
      >
        <el-select
          v-model="studentId"
          filterable
          remote
          reserve-keyword
          :remote-method="onStudentSearch"
          :loading="studentSearching"
          placeholder="按姓名 / 学号搜索学生"
          class="gp-select"
          @change="onStudentChange"
        >
          <el-option v-for="s in studentOptions" :key="s.id" :label="studentLabel(s)" :value="s.id" />
        </el-select>
        <el-dropdown trigger="click" @command="onHeadCommand">
          <el-button size="small" :icon="MoreFilled">更多</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="export"><el-icon><Download /></el-icon>导出台账 Excel</el-dropdown-item>
              <el-dropdown-item command="template"><el-icon><Document /></el-icon>下载导入模板</el-dropdown-item>
              <el-dropdown-item command="import" divided><el-icon><Upload /></el-icon>导入台账 Excel</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </TuiPageHero>

      <!-- 移动端整行学生选择 -->
      <div v-if="isMobile" class="tui-card gp-picker">
        <div class="tui-card-body">
          <el-select
            v-model="studentId"
            filterable
            remote
            reserve-keyword
            :remote-method="onStudentSearch"
            :loading="studentSearching"
            placeholder="按姓名 / 学号搜索学生"
            style="width: 100%"
            @change="onStudentChange"
          >
            <el-option v-for="s in studentOptions" :key="s.id" :label="studentLabel(s)" :value="s.id" />
          </el-select>
        </div>
      </div>

      <!-- 沟通概览（聚合数据与图表）：桌面端在主从分栏之上，移动端在同位置堆叠 -->
      <GuardianOverviewPanel
        :overview="overview"
        :days="OVERVIEW_DAYS"
        :student-name="currentStudent?.name || ''"
        @focus="focusStudent"
      />

      <div v-if="!studentId" class="tui-card">
        <div class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="26"><User /></el-icon></span>
          <span class="tui-empty-title">请先选择一名学生</span>
          <span class="tui-empty-desc">选择学生后可建档家长联系人并记录沟通台账</span>
        </div>
      </div>

      <!-- 桌面端主从式版面：左「家长联系人」固定窄栏 + 右「沟通台账时间轴」自适应宽栏。
           为什么这样分栏：家校沟通是「选人 → 看/记台账」的主从操作，左选右看能一屏连贯完成；
           原先两段纵向堆叠会让页面很长、来回滚动，且与其它子页面骨架雷同。
           下方的 v-else 分支是移动端原有纵向骨架，结构 / 顺序 / 类名原样保留。 -->
      <div v-else-if="!isMobile" class="gp-split">
        <!-- 左栏（主）：家长联系人 —— 固定 300px；列体限高内部滚动，页面滚动时吸顶 -->
        <aside class="gp-panel gp-panel-list">
          <div class="tui-section-head">
            <h3><el-icon><User /></el-icon>家长联系人</h3>
            <div class="tui-section-extra">
              <span class="gp-count">{{ guardians.length }} 人</span>
              <el-button size="small" type="primary" :icon="Plus" @click="openGuardianCreate">新增联系人</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>先建档家长联系人才能留痕；点击卡片上的「通话 / 短信 / 微信」会以对应方式预填一条沟通台账。</span>
          </div>
          <div class="gp-panel-body tui-scroll-hidden">
            <div v-if="!guardians.length" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="24"><User /></el-icon></span>
              <span class="tui-empty-title">暂无联系人</span>
              <span class="tui-empty-desc">先建档家长联系人，才能发短信 / 留痕</span>
            </div>
            <div v-else class="gp-list">
              <div v-for="g in guardians" :key="g.id" class="gp-card">
                <div class="gp-card-top">
                  <span class="gp-avatar">{{ avatarOf(g.name) }}</span>
                  <div class="gp-card-id">
                    <span class="gp-card-name">{{ g.name }}</span>
                    <span class="gp-card-sub">
                      <el-tag size="small" effect="plain" round>{{ g.relation }}</el-tag>
                      <el-tag v-if="g.is_primary" size="small" type="success" effect="plain" round>主要</el-tag>
                    </span>
                  </div>
                  <div class="gp-card-ops">
                    <button class="gp-link" @click="openGuardianEdit(g)">编辑</button>
                    <button class="gp-link gp-link-danger" @click="removeGuardian(g)">删除</button>
                  </div>
                </div>
                <div class="gp-card-phone">
                  <el-icon :size="13"><Phone /></el-icon>
                  <span>{{ g.phone_masked || '未填手机号' }}</span>
                </div>
                <div class="gp-card-actions">
                  <button class="gp-act" @click="openQuickLog(g, 'note')"><el-icon><Phone /></el-icon>通话</button>
                  <button class="gp-act" @click="openQuickLog(g, 'sms')"><el-icon><Message /></el-icon>短信</button>
                  <button class="gp-act" @click="openQuickLog(g, 'note')"><el-icon><ChatLineRound /></el-icon>微信</button>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右栏（从）：沟通台账时间轴 —— 自适应宽度，承载记录与只读链接操作 -->
        <section class="gp-panel gp-panel-ledger">
          <div class="tui-section-head">
            <h3><el-icon><ChatDotRound /></el-icon>沟通台账时间轴</h3>
            <div class="tui-section-extra">
              <span class="gp-count">{{ logTotal }} 条</span>
              <el-button size="small" :icon="Plus" @click="openLogCreate">记录沟通</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>每次沟通按时间倒序留痕，家长零账号也能通过只读链接查看；危机类记录不会生成分享链接。</span>
          </div>

          <!-- 台账筛选工具条：关键词防抖 + 场景 / 渠道 / 状态 + 日期区间，全部服务端筛选 -->
          <div class="tui-section-tools gp-tools">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索沟通内容 / 家长"
              clearable
              :prefix-icon="Search"
              @input="onKeywordInput"
            />
            <el-select v-model="filters.scene" placeholder="场景" clearable @change="onFilterChange">
              <el-option v-for="s in SCENE_OPTIONS" :key="s" :label="GUARDIAN_SCENE_LABEL[s]" :value="s" />
            </el-select>
            <el-select v-model="filters.channel" placeholder="渠道" clearable @change="onFilterChange">
              <el-option v-for="c in CHANNEL_OPTIONS" :key="c" :label="GUARDIAN_CHANNEL_LABEL[c]" :value="c" />
            </el-select>
            <el-select v-model="filters.status" placeholder="状态" clearable @change="onFilterChange">
              <el-option v-for="st in STATUS_OPTIONS" :key="st" :label="GUARDIAN_STATUS_LABEL[st]" :value="st" />
            </el-select>
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              class="gp-range"
              @change="onFilterChange"
            />
            <button v-if="hasFilters" class="gp-link" @click="resetFilters">重置筛选</button>
          </div>

          <div v-if="!logs.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><ChatDotRound /></el-icon></span>
            <span class="tui-empty-title">{{ hasFilters ? '没有符合条件的记录' : '暂无沟通记录' }}</span>
            <span class="tui-empty-desc">每次沟通都留痕，家长零账号也能查看</span>
          </div>
          <div v-else class="gp-tl">
            <div v-for="l in logs" :key="l.id" class="gp-tl-item">
              <span class="gp-tl-node" :class="`tone-${channelTone(l.channel)}`">
                <el-icon><component :is="CHANNEL_ICON[l.channel]" /></el-icon>
              </span>
              <div class="gp-tl-card">
                <div class="gp-tl-top">
                  <span class="tui-tag">{{ GUARDIAN_SCENE_LABEL[l.scene] }}</span>
                  <span class="tui-tag">{{ GUARDIAN_CHANNEL_LABEL[l.channel] }}</span>
                  <el-tag size="small" :type="statusTag(l.status)" effect="plain" round>
                    {{ GUARDIAN_STATUS_LABEL[l.status] }}
                  </el-tag>
                  <span class="gp-tl-date">{{ (l.created_at || '').slice(0, 10) }}</span>
                </div>
                <div v-if="l.guardian_name" class="gp-tl-who">对象：{{ l.guardian_name }}</div>
                <div class="gp-tl-body">{{ l.content_summary }}</div>
                <div class="gp-tl-ops">
                  <template v-if="links[l.id] && !links[l.id].revoked">
                    <span class="gp-link-valid">链接有效至 {{ (links[l.id].expires_at || '').slice(0, 10) }} · 访问 {{ links[l.id].view_count }} 次</span>
                    <button class="gp-link" @click="copyLink(links[l.id])">复制链接</button>
                    <button class="gp-link gp-link-danger" @click="revoke(links[l.id])">撤销链接</button>
                  </template>
                  <template v-else-if="l.scene !== 'crisis'">
                    <button class="gp-link" @click="makeLink(l)">生成只读链接</button>
                  </template>
                  <span v-else class="gp-link-locked">
                    <el-icon :size="11"><Lock /></el-icon>危机记录不生成链接
                  </span>
                  <button class="gp-link gp-link-danger gp-link-tail" @click="removeLog(l)">删除</button>
                </div>
              </div>
            </div>
            <div v-if="logTotal > 0" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="pageLogs"
                v-model:page-size="pageSizeLogs"
                :page-sizes="[10, 20, 50]"
                :total="logTotal"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="handleLogsSizeChange"
                @current-change="handleLogsCurrentChange"
              />
            </div>
          </div>
        </section>
      </div>

      <div v-else class="tui-stack">
        <!-- 家长联系人卡（含通话 / 短信 / 微信快捷留痕） -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><User /></el-icon>家长联系人</h3>
            <div class="tui-section-extra">
              <span class="gp-count">{{ guardians.length }} 人</span>
              <el-button size="small" type="primary" :icon="Plus" @click="openGuardianCreate">新增联系人</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>先建档家长联系人才能留痕；点击卡片上的「通话 / 短信 / 微信」会以对应方式预填一条沟通台账。</span>
          </div>
          <div v-if="!guardians.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><User /></el-icon></span>
            <span class="tui-empty-title">暂无联系人</span>
            <span class="tui-empty-desc">先建档家长联系人，才能发短信 / 留痕</span>
          </div>
          <div v-else class="gp-cards">
            <div v-for="g in guardians" :key="g.id" class="gp-card">
              <div class="gp-card-top">
                <span class="gp-avatar">{{ avatarOf(g.name) }}</span>
                <div class="gp-card-id">
                  <span class="gp-card-name">{{ g.name }}</span>
                  <span class="gp-card-sub">
                    <el-tag size="small" effect="plain" round>{{ g.relation }}</el-tag>
                    <el-tag v-if="g.is_primary" size="small" type="success" effect="plain" round>主要</el-tag>
                  </span>
                </div>
                <div class="gp-card-ops">
                  <button class="gp-link" @click="openGuardianEdit(g)">编辑</button>
                  <button class="gp-link gp-link-danger" @click="removeGuardian(g)">删除</button>
                </div>
              </div>
              <div class="gp-card-phone">
                <el-icon :size="13"><Phone /></el-icon>
                <span>{{ g.phone_masked || '未填手机号' }}</span>
              </div>
              <div class="gp-card-actions">
                <button class="gp-act" @click="openQuickLog(g, 'note')"><el-icon><Phone /></el-icon>通话</button>
                <button class="gp-act" @click="openQuickLog(g, 'sms')"><el-icon><Message /></el-icon>短信</button>
                <button class="gp-act" @click="openQuickLog(g, 'note')"><el-icon><ChatLineRound /></el-icon>微信</button>
              </div>
            </div>
          </div>
        </section>

        <!-- 沟通台账时间轴 -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><ChatDotRound /></el-icon>沟通台账时间轴</h3>
            <div class="tui-section-extra">
              <span class="gp-count">{{ logTotal }} 条</span>
              <el-button size="small" :icon="Plus" @click="openLogCreate">记录沟通</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>每次沟通按时间倒序留痕，家长零账号也能通过只读链接查看；危机类记录不会生成分享链接。</span>
          </div>

          <div class="tui-section-tools gp-tools">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索沟通内容 / 家长"
              clearable
              :prefix-icon="Search"
              @input="onKeywordInput"
            />
            <el-select v-model="filters.scene" placeholder="场景" clearable @change="onFilterChange">
              <el-option v-for="s in SCENE_OPTIONS" :key="s" :label="GUARDIAN_SCENE_LABEL[s]" :value="s" />
            </el-select>
            <el-select v-model="filters.channel" placeholder="渠道" clearable @change="onFilterChange">
              <el-option v-for="c in CHANNEL_OPTIONS" :key="c" :label="GUARDIAN_CHANNEL_LABEL[c]" :value="c" />
            </el-select>
            <el-select v-model="filters.status" placeholder="状态" clearable @change="onFilterChange">
              <el-option v-for="st in STATUS_OPTIONS" :key="st" :label="GUARDIAN_STATUS_LABEL[st]" :value="st" />
            </el-select>
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              class="gp-range"
              @change="onFilterChange"
            />
            <button v-if="hasFilters" class="gp-link" @click="resetFilters">重置筛选</button>
          </div>

          <div v-if="!logs.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><ChatDotRound /></el-icon></span>
            <span class="tui-empty-title">{{ hasFilters ? '没有符合条件的记录' : '暂无沟通记录' }}</span>
            <span class="tui-empty-desc">每次沟通都留痕，家长零账号也能查看</span>
          </div>
          <div v-else class="gp-tl">
            <div v-for="l in logs" :key="l.id" class="gp-tl-item">
              <span class="gp-tl-node" :class="`tone-${channelTone(l.channel)}`">
                <el-icon><component :is="CHANNEL_ICON[l.channel]" /></el-icon>
              </span>
              <div class="gp-tl-card">
                <div class="gp-tl-top">
                  <span class="tui-tag">{{ GUARDIAN_SCENE_LABEL[l.scene] }}</span>
                  <span class="tui-tag">{{ GUARDIAN_CHANNEL_LABEL[l.channel] }}</span>
                  <el-tag size="small" :type="statusTag(l.status)" effect="plain" round>
                    {{ GUARDIAN_STATUS_LABEL[l.status] }}
                  </el-tag>
                  <span class="gp-tl-date">{{ (l.created_at || '').slice(0, 10) }}</span>
                </div>
                <div v-if="l.guardian_name" class="gp-tl-who">对象：{{ l.guardian_name }}</div>
                <div class="gp-tl-body">{{ l.content_summary }}</div>
                <div class="gp-tl-ops">
                  <template v-if="links[l.id] && !links[l.id].revoked">
                    <span class="gp-link-valid">链接有效至 {{ (links[l.id].expires_at || '').slice(0, 10) }} · 访问 {{ links[l.id].view_count }} 次</span>
                    <button class="gp-link" @click="copyLink(links[l.id])">复制链接</button>
                    <button class="gp-link gp-link-danger" @click="revoke(links[l.id])">撤销链接</button>
                  </template>
                  <template v-else-if="l.scene !== 'crisis'">
                    <button class="gp-link" @click="makeLink(l)">生成只读链接</button>
                  </template>
                  <span v-else class="gp-link-locked">
                    <el-icon :size="11"><Lock /></el-icon>危机记录不生成链接
                  </span>
                  <button class="gp-link gp-link-danger gp-link-tail" @click="removeLog(l)">删除</button>
                </div>
              </div>
            </div>
            <div v-if="logTotal > 0" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="pageLogs"
                v-model:page-size="pageSizeLogs"
                :page-sizes="[10, 20, 50]"
                :total="logTotal"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="handleLogsSizeChange"
                @current-change="handleLogsCurrentChange"
              />
            </div>
          </div>
        </section>
      </div>

      <GuardianDialog
        v-model="guardianVisible"
        :student-id="studentId || 0"
        :student="currentStudent"
        :guardian="editingGuardian"
        @saved="loadAll"
      />
      <ContactLogDialog
        v-model="logVisible"
        :student-id="studentId || 0"
        :student="currentStudent"
        :guardians="guardians"
        :initial-content="logPresetContent"
        :initial-scene="logPresetScene"
        :initial-channel="logPresetChannel"
        :initial-guardian-id="logPresetGuardianId"
        @saved="loadAll"
      />
    </div>

    <!-- 导入台账用的隐藏文件选择器（页头「更多 → 导入台账 Excel」触发） -->
    <input ref="importInput" class="gp-file-input" type="file" accept=".xlsx,.xls" @change="handleImportFile" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue'
import {
  ChatDotRound, ChatLineRound, Document, Download, InfoFilled, Link, Lock, Message,
  MoreFilled, Phone, Plus, Search, Upload, User,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import { getStudents, type StudentSummary } from '@/api/teacher'
import {
  createShareLink, deleteContactLog, deleteGuardian, downloadContactLogTemplate,
  exportContactLogs, getContactLogsPaged, getGuardianOverview, getGuardians,
  getLogShareLink, importContactLogs, revokeShareLink,
  GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL, GUARDIAN_STATUS_LABEL,
  type ContactLog, type Guardian, type GuardianChannel, type GuardianContactStatus,
  type GuardianOverview, type GuardianScene, type ShareLink,
} from '@/api/guardian'
import GuardianDialog from '@/components/teacher/guardian/GuardianDialog.vue'
import ContactLogDialog from '@/components/teacher/guardian/ContactLogDialog.vue'
import GuardianOverviewPanel from '@/components/teacher/guardian/GuardianOverview.vue'
import { useRoute, useRouter } from 'vue-router'

defineOptions({ name: 'teacher-guardian' })

/** 概览统计窗口（天） */
const OVERVIEW_DAYS = 30

/** 沟通渠道 → 时间轴节点图标（统一 Element Plus 图标） */
const CHANNEL_ICON: Record<GuardianChannel, Component> = {
  sms: Message,
  report: Document,
  link: Link,
  note: ChatDotRound,
}

const SCENE_OPTIONS: GuardianScene[] = ['leave', 'crisis', 'academic', 'care', 'other']
const CHANNEL_OPTIONS: GuardianChannel[] = ['sms', 'report', 'link', 'note']
const STATUS_OPTIONS: GuardianContactStatus[] = ['draft', 'sent', 'pending', 'failed']

const { isMobile } = useResponsive()
const route = useRoute()
const router = useRouter()

/* ===== 学生选择器（服务端搜索 + 300ms 防抖） ===== */
const studentOptions = ref<StudentSummary[]>([])
const studentSearching = ref(false)
/** 当前聚焦学生的完整对象：保证搜索后 el-select 仍能回显姓名 */
const selectedStudent = ref<StudentSummary | null>(null)
const studentId = ref<number | undefined>(undefined)

const guardians = ref<Guardian[]>([])
const logs = ref<ContactLog[]>([])
const logTotal = ref(0)
const links = ref<Record<number, ShareLink>>({})
const overview = ref<GuardianOverview | null>(null)

/** 当前已选学生：为弹窗 / 概览提供姓名 / 班级 / 近期预警上下文 */
const currentStudent = computed<StudentSummary | null>(() => {
  const hit = studentOptions.value.find((s) => s.id === studentId.value)
  if (hit) return hit
  return selectedStudent.value && selectedStudent.value.id === studentId.value ? selectedStudent.value : null
})

const guardianVisible = ref(false)
const editingGuardian = ref<Guardian | null>(null)
const logVisible = ref(false)
/** 闭环：来自学生成长档案的反馈预填 */
const logPresetContent = ref('')
const logPresetScene = ref<GuardianScene>('care')
/** 家长联系人卡快捷入口的预填 */
const logPresetChannel = ref<GuardianChannel>('note')
const logPresetGuardianId = ref<number | undefined>(undefined)

/* ===== 台账筛选 + 服务端分页 ===== */
const filters = reactive<{
  keyword: string
  scene?: GuardianScene
  channel?: GuardianChannel
  status?: GuardianContactStatus
}>({ keyword: '', scene: undefined, channel: undefined, status: undefined })
const dateRange = ref<[string, string] | null>(null)
const pageLogs = ref(1)
const pageSizeLogs = ref(10)

const hasFilters = computed(() =>
  Boolean(filters.keyword || filters.scene || filters.channel || filters.status || dateRange.value)
)

function studentLabel(s: StudentSummary) {
  return s.username ? `${s.name} · ${s.username}` : s.name
}

function statusTag(status: GuardianContactStatus) {
  return status === 'sent' ? 'success' : status === 'pending' ? 'warning' : status === 'failed' ? 'danger' : 'info'
}

/** 时间轴节点色调：统一走令牌 */
function channelTone(c: GuardianChannel): 'brand' | 'success' | 'warn' | 'muted' {
  switch (c) {
    case 'sms': return 'brand'
    case 'link': return 'success'
    case 'report': return 'muted'
    default: return 'brand'
  }
}

/** 联系人头像占位：取姓名首字 */
function avatarOf(name?: string) {
  return (name || '家').trim().charAt(0) || '家'
}

/* ===== 学生搜索 ===== */
let studentSearchTimer: ReturnType<typeof setTimeout> | undefined
function onStudentSearch(keyword: string) {
  if (studentSearchTimer) clearTimeout(studentSearchTimer)
  studentSearchTimer = setTimeout(() => { void searchStudents(keyword) }, 300)
}

async function searchStudents(keyword: string) {
  studentSearching.value = true
  try {
    const list = await getStudents(keyword || undefined)
    // 保留当前聚焦学生，避免搜索词不含它时选择框丢失姓名回显
    const cur = selectedStudent.value
    studentOptions.value = cur && !list.some((s) => s.id === cur.id) ? [cur, ...list] : list
  } catch {
    studentOptions.value = selectedStudent.value ? [selectedStudent.value] : []
  } finally {
    studentSearching.value = false
  }
}

/* ===== 数据加载 ===== */
async function loadGuardians() {
  if (!studentId.value) { guardians.value = []; return }
  try {
    guardians.value = await getGuardians(studentId.value)
  } catch {
    guardians.value = []
  }
}

/** 回显当前页已有的分享链接（只查可见页，避免逐条全量请求） */
async function loadLinks() {
  const map: Record<number, ShareLink> = {}
  await Promise.all(
    logs.value.map(async (log) => {
      try {
        const link = await getLogShareLink(log.id)
        if (link) map[log.id] = link
      } catch {
        /* 忽略单个失败 */
      }
    })
  )
  links.value = map
}

/** 台账：服务端筛选 + 分页 */
async function loadLogs() {
  if (!studentId.value) { logs.value = []; logTotal.value = 0; links.value = {}; return }
  const range = Array.isArray(dateRange.value) ? dateRange.value : []
  try {
    const res = await getContactLogsPaged({
      student_id: studentId.value,
      keyword: filters.keyword || undefined,
      scene: filters.scene || undefined,
      channel: filters.channel || undefined,
      status: filters.status || undefined,
      start: range[0] || undefined,
      end: range[1] || undefined,
      page: pageLogs.value,
      page_size: pageSizeLogs.value,
    })
    logs.value = res.items
    logTotal.value = res.total
  } catch {
    logs.value = []
    logTotal.value = 0
  }
  await loadLinks()
}

/** 概览聚合：已选择学生时只看该生，未选择时看全部 */
async function loadOverview() {
  try {
    overview.value = await getGuardianOverview({ days: OVERVIEW_DAYS, student_id: studentId.value })
  } catch {
    overview.value = null
  }
}

async function loadAll() {
  pageLogs.value = 1
  await Promise.all([loadGuardians(), loadLogs(), loadOverview()])
}

/** 台账操作（删除 / 导入）后的局部刷新：不动联系人，避免整页抖动 */
async function refreshLedger() {
  await Promise.all([loadLogs(), loadOverview()])
}

/* ===== 学生切换 ===== */
function onStudentChange() {
  selectedStudent.value = studentOptions.value.find((s) => s.id === studentId.value) || null
  guardianVisible.value = false
  logVisible.value = false
  void loadAll()
}

/** Top5 榜单点击：切换聚焦到该学生 */
async function focusStudent(id: number, name: string) {
  studentId.value = id
  const known = studentOptions.value.find((s) => s.id === id)
  if (known) {
    selectedStudent.value = known
  } else {
    // 榜单只给出 id/姓名，用服务端搜索补齐完整对象（失败则退回空上下文）
    try {
      const list = await getStudents(name)
      const hit = list.find((s) => s.id === id) || null
      selectedStudent.value = hit
      if (hit) studentOptions.value = [hit, ...studentOptions.value.filter((s) => s.id !== id)]
    } catch {
      selectedStudent.value = null
    }
  }
  guardianVisible.value = false
  logVisible.value = false
  await loadAll()
}

/* ===== 筛选交互 ===== */
let keywordTimer: ReturnType<typeof setTimeout> | undefined
function onKeywordInput() {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => { pageLogs.value = 1; void loadLogs() }, 300)
}

function onFilterChange() {
  pageLogs.value = 1
  void loadLogs()
}

function resetFilters() {
  filters.keyword = ''
  filters.scene = undefined
  filters.channel = undefined
  filters.status = undefined
  dateRange.value = null
  onFilterChange()
}

function handleLogsSizeChange() {
  pageLogs.value = 1
  void loadLogs()
}

function handleLogsCurrentChange() {
  void loadLogs()
}

/* ===== 弹窗 / 联系人操作 ===== */
function openGuardianCreate() {
  editingGuardian.value = null
  guardianVisible.value = true
}

function openGuardianEdit(g: Guardian) {
  editingGuardian.value = g
  guardianVisible.value = true
}

/** 新增沟通：清空上次预填 */
function openLogCreate() {
  logPresetContent.value = ''
  logPresetScene.value = 'care'
  logPresetChannel.value = 'note'
  logPresetGuardianId.value = undefined
  logVisible.value = true
}

/** 联系人卡快捷入口：以对应渠道 + 该联系人预填一条沟通台账 */
function openQuickLog(g: Guardian, channel: GuardianChannel) {
  logPresetContent.value = ''
  logPresetScene.value = 'care'
  logPresetChannel.value = channel
  logPresetGuardianId.value = g.id
  logVisible.value = true
}

async function removeGuardian(g: Guardian) {
  try {
    await ElMessageBox.confirm(`确定删除联系人「${g.name}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteGuardian(g.id)
  ElMessage.success('已删除')
  void loadAll()
}

async function makeLink(log: ContactLog) {
  try {
    const link = await createShareLink(log.id)
    links.value = { ...links.value, [log.id]: link }
    ElMessage.success('已生成，7 天内有效')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '生成失败')
  }
}

async function copyLink(link: ShareLink) {
  const url = `${window.location.origin}${link.path}`
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.info(url)
  }
}

async function revoke(link: ShareLink) {
  try {
    await ElMessageBox.confirm('撤销后家长将无法再打开该链接，确定撤销？', '撤销确认', { type: 'warning' })
  } catch {
    return
  }
  const updated = await revokeShareLink(link.id)
  links.value = { ...links.value, [updated.log_id]: updated }
  ElMessage.success('已撤销')
}

async function removeLog(log: ContactLog) {
  try {
    await ElMessageBox.confirm('确定删除这条沟通记录？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteContactLog(log.id)
  ElMessage.success('已删除')
  void refreshLedger()
}

/* ===== 导出 / 模板 / 导入 ===== */
const importInput = ref<HTMLInputElement | null>(null)

function onHeadCommand(cmd: string) {
  if (cmd === 'export') void handleExport()
  else if (cmd === 'template') void handleDownloadTemplate()
  else if (cmd === 'import') importInput.value?.click()
}

/** 当前筛选条件（不含分页），导出与台账查询共用同一口径 */
function buildFilterParams() {
  const range = Array.isArray(dateRange.value) ? dateRange.value : []
  return {
    student_id: studentId.value,
    keyword: filters.keyword || undefined,
    scene: filters.scene || undefined,
    channel: filters.channel || undefined,
    status: filters.status || undefined,
    start: range[0] || undefined,
    end: range[1] || undefined,
  }
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

async function handleExport() {
  try {
    const blob = await exportContactLogs(buildFilterParams())
    saveBlob(blob, '家校沟通台账.xlsx')
    ElMessage.success('台账已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function handleDownloadTemplate() {
  try {
    const blob = await downloadContactLogTemplate()
    saveBlob(blob, '家校沟通台账导入模板.xlsx')
    ElMessage.success('模板已下载')
  } catch {
    ElMessage.error('模板下载失败')
  }
}

function escapeHtml(text: string) {
  return text.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string))
}

async function handleImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const res = await importContactLogs(file)
    await refreshLedger()
    const parts = [`<b>成功导入 ${res.created} 条</b>`]
    if (res.skipped.length) parts.push(`跳过 ${res.skipped.length} 条：<br/>${res.skipped.map(escapeHtml).join('<br/>')}`)
    if (res.errors.length) parts.push(`失败 ${res.errors.length} 条：<br/>${res.errors.map(escapeHtml).join('<br/>')}`)
    await ElMessageBox.alert(parts.join('<br/><br/>'), '导入结果', {
      dangerouslyUseHTMLString: true,
      type: res.errors.length ? 'warning' : 'success',
      confirmButtonText: '知道了',
    }).catch(() => { /* 用户关闭弹窗不视为失败 */ })
    ElMessage.success(`导入完成：新增 ${res.created} 条`)
  } catch {
    ElMessage.error('导入失败，请检查文件格式')
  }
}

/* ===== 初始化 ===== */
async function initPage() {
  try {
    studentOptions.value = await getStudents()
  } catch {
    studentOptions.value = []
  }

  // 闭环：从学生成长档案跳来时直接定位到该学生
  const deepId = Number(route.query.student_id) || 0
  const target = deepId ? studentOptions.value.find((s) => s.id === deepId) : undefined
  if (target) {
    selectedStudent.value = target
    studentId.value = target.id
  } else if (!studentId.value && studentOptions.value.length) {
    selectedStudent.value = studentOptions.value[0]
    studentId.value = studentOptions.value[0].id
  }

  if (studentId.value) await loadAll()
  else await loadOverview()

  // 闭环：带上反馈事由时，落地即打开沟通记录并预填
  if (route.query.content) {
    logPresetContent.value = String(route.query.content)
    logPresetScene.value = (String(route.query.scene || 'care') as GuardianScene)
    logPresetChannel.value = 'note'
    logPresetGuardianId.value = undefined
    logVisible.value = true
    router.replace({ path: '/teacher/guardian' })
  }
}

onMounted(initPage)
</script>

<style scoped>
.gp-picker { margin-bottom: 10px; }
.gp-select { width: 240px; }
.gp-count { font-size: 11.5px; color: var(--tui-text-quiet); }
.gp-file-input { display: none; }

/* 移动端吸顶栏「更多」图标按钮 */
.gp-more-btn {
  display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border: none; border-radius: 50%;
  background: transparent; color: var(--tui-text); cursor: pointer;
}
.gp-more-btn:hover { background: rgba(15, 17, 21, 0.05); }

/* 台账筛选工具条：日期区间需要更宽，单独指定 */
.gp-tools { margin-bottom: 10px; }
.gp-tools .gp-range { width: 240px; }
@media (max-width: 767px) {
  .gp-tools .gp-range { width: 100%; }
}

/* 家长联系人卡 */
.gp-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.gp-card {
  display: flex; flex-direction: column; gap: 8px;
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius-sm);
  padding: 10px 11px; background: var(--tui-surface-muted);
}
.gp-card-top { display: flex; align-items: center; gap: 8px; }
.gp-avatar {
  flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--tui-brand-soft); color: var(--tui-brand-strong);
  font-size: 13px; font-weight: 600;
}
.gp-card-id { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.gp-card-name { font-size: 13.5px; font-weight: 600; color: var(--tui-text); }
.gp-card-sub { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.gp-card-ops { display: flex; gap: 10px; flex-shrink: 0; }
.gp-card-phone { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--tui-text-tertiary); }
.gp-card-actions { display: flex; gap: 6px; }
.gp-act {
  flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  padding: 6px 4px; border: 1px solid var(--tui-border-strong); border-radius: 8px;
  background: var(--tui-surface); color: var(--tui-text-secondary);
  font-family: inherit; font-size: 12px; cursor: pointer;
}
.gp-act:hover { border-color: var(--tui-brand); color: var(--tui-brand); }

/* 沟通台账时间轴 */
.gp-tl { position: relative; padding-left: 24px; }
.gp-tl::before {
  content: ''; position: absolute; left: 8px; top: 5px; bottom: 5px;
  width: 2px; background: var(--tui-border);
}
.gp-tl-item { position: relative; margin-bottom: 8px; }
.gp-tl-item:last-child { margin-bottom: 0; }
.gp-tl-node {
  position: absolute; left: -24px; top: 2px; width: 18px; height: 18px; border-radius: 50%;
  background: var(--tui-surface); box-shadow: inset 0 0 0 2px var(--tui-border-strong);
  color: var(--tui-text-tertiary); display: flex; align-items: center; justify-content: center;
}
.gp-tl-node .el-icon { font-size: 10px; }
.gp-tl-node.tone-brand { box-shadow: inset 0 0 0 2px var(--tui-brand); color: var(--tui-brand); }
.gp-tl-node.tone-success { box-shadow: inset 0 0 0 2px var(--tui-success); color: var(--tui-success); }
.gp-tl-node.tone-warn { box-shadow: inset 0 0 0 2px var(--tui-warn); color: var(--tui-warn); }
.gp-tl-node.tone-muted { box-shadow: inset 0 0 0 2px var(--tui-border-strong); color: var(--tui-text-tertiary); }
.gp-tl-card {
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius-sm);
  padding: 8px 10px; background: var(--tui-surface-muted);
}
.gp-tl-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.gp-tl-date { margin-left: auto; font-size: 11.5px; color: var(--tui-text-quiet); }
.gp-tl-who { font-size: 11.5px; color: var(--tui-text-quiet); margin-top: 5px; }
.gp-tl-body { font-size: 12.5px; color: var(--tui-text-secondary); line-height: 1.6; white-space: pre-wrap; margin-top: 5px; }
.gp-tl-ops { display: flex; align-items: center; gap: 14px; margin-top: 8px; flex-wrap: wrap; }
.gp-link-valid { font-size: 11.5px; color: var(--tui-success); }

.gp-link { border: none; background: none; padding: 0; font-size: 12px; color: var(--tui-brand); cursor: pointer; font-family: inherit; }
.gp-link-danger { color: var(--tui-danger); }
.gp-link-tail { margin-left: auto; }
.gp-link-locked { display: inline-flex; align-items: center; gap: 3px; font-size: 11.5px; color: var(--tui-text-quiet); }

/* ===== 桌面端主从式版面（仅 v-if="!isMobile" 渲染，移动端零影响） ===== */
.gp-split {
  display: grid;
  /* 左栏固定 300px 承载「联系人」主列表，右栏自适应承载「沟通台账」从视图 */
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

/* 两栏共用的面板外壳：白底 + 1px 发丝边框 + 极轻投影，与 .tui-section 同一视觉语言 */
.gp-panel {
  position: relative;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  padding: 12px 13px;
  overflow: hidden;
}
/* 顶部语义色细线：左栏联系人走品牌色，右栏台账走成功色（呼应「只读链接有效」的正向状态） */
.gp-panel::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
}
.gp-panel-list::before { background: var(--tui-brand); }
.gp-panel-ledger::before { background: var(--tui-success); }

/* 左栏在页面滚动时吸顶，强化「左选右看」的主从关系 */
.gp-panel-list { position: sticky; top: 12px; }

/* 左栏列表体：限高 + 内部滚动，保证长名单不会把右栏时间轴顶下去 */
.gp-panel-body {
  max-height: 520px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

/* 联系人行：沿用 .gp-card 卡片，在窄栏内改为单列排布 */
.gp-list { display: flex; flex-direction: column; gap: 8px; }

@media (max-width: 767px) {
  .gp-cards { grid-template-columns: 1fr; }
}
</style>