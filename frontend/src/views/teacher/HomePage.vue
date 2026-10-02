<template>
  <div class="home-dashboard">
    <!-- 移动端头部 + 欢迎横幅 -->
    <HomeTopBanner :is-mobile="isMobile" :user-name="authStore.userName || '教师'" :greeting="greeting"
      :pending-count="pendingCount" :severe-alert-count="stats.severe_alert_count" :today-str="todayStr" />

    <!-- ===== 第一层：KPI统计卡片 ===== -->
    <HomeKpiCards :cards="statCards" @navigate="navigateTo" />

    <!-- ===== AI 悬浮按钮 + 决策支持层 ===== -->
    <HomeAiPanel :proactive-actions="proactiveActions" :contact-suggestions="contactSuggestions"
      :ai-loading="aiLoading" @refresh="loadAiDecisions" />

    <!-- ===== 第二层：数据分析区（左2:右1） ===== -->
    <HomeAnalyticsCharts v-if="!isMobile" :class-stats="classStats" :eval-data="evalData"
      :analysis-result="analysisResult" :analysis-loading="analysisLoading" @navigate="navigateTo"
      @analyze="handleClassAnalysis" />

    <!-- 移动端：数据分析入口 -->
    <div v-if="isMobile" class="mobile-charts">
      <div class="mobile-section-card mobile-chart-entry" @click="showChartSubPage = true">
        <div class="mobile-section-header">
          <div class="section-title"><el-icon><DataAnalysis /></el-icon><span>数据分析</span></div>
          <el-icon color="#ccc"><DArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 移动端：逾期提醒 + 今日任务 + 公告 -->
    <HomeMobileToday v-if="isMobile" :today-leaves="todayLeaves" :today-schedules="todaySchedules"
      :campus-announcements="campusAnnouncements" :overdue-count="overdueSchedules.length"
      @open-today="showTodaySubPage = true" />

    <!-- 添加日程子页面 -->
    <!-- transition removed -->
    <HomeMobileSchedule v-if="isMobile && showScheduleSubPage" :content="scheduleContent"
      :urgency="scheduleUrgency" :urgency-options="urgencyOptions" :upcoming-reminders="upcomingReminders"
      @close="showScheduleSubPage = false" @update:content="scheduleContent = $event"
      @update:urgency="scheduleUrgency = $event" @add="handleAddScheduleFromSubPage"
      @delete="handleDeleteSchedule" />
    <!-- /transition removed -->

    <!-- 危机预警子页面 -->
    <!-- transition removed -->
      <div v-if="isMobile && showCrisisSubPage" class="sub-page">
        <div class="sub-page-header">
          <el-button text circle @click="showCrisisSubPage = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="sub-page-title">危机预警</span>
          <div style="width:36px"></div>
        </div>
        <div class="sub-page-body">
          <div v-if="alerts.length === 0" class="empty-tip-small" style="padding:40px 0;text-align:center">暂无危机预警</div>
          <div v-for="a in alerts" :key="a.id" class="mobile-section-card" style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <el-tag :type="a.level === 'severe' ? 'danger' : a.level === 'moderate' ? 'warning' : 'info'" size="small">
                {{ a.level === 'severe' ? '高危' : a.level === 'moderate' ? '中危' : '低危' }}
              </el-tag>
              <small style="color:#999">{{ a.created_at?.slice(0, 10) }}</small>
            </div>
            <div style="font-size:14px;font-weight:500;color:#333;margin-bottom:4px">{{ a.student_name || '未知学生' }}</div>
            <div style="font-size:13px;color:#666;line-height:1.5">{{ a.summary }}</div>
            <div v-if="a.keywords_matched" style="margin-top:6px;font-size:12px;color:#999">关键词：{{ a.keywords_matched }}</div>
          </div>
        </div>
      </div>
    <!-- /transition removed -->

    <!-- 待办任务子页面 -->
    <!-- transition removed -->
    <!-- ===== 移动端：今日任务子页 ===== -->
    <HomeMobileTodayTasks v-if="isMobile && showTodaySubPage" :selected-date="selectedTaskDate"
      :today-leaves="todayLeaves" :today-schedules="todaySchedules" :overdue-schedules="overdueSchedules"
      :schedules="schedules" :pending-leaves="pendingLeaves" :urgency-options="urgencyOptions"
      @close="showTodaySubPage = false" @select-date="handlePopupDateSelect"
      @open-quick-add="openQuickAddDialog" @toggle-complete="toggleScheduleComplete"
      @delete-schedule="handleDeleteSchedule" @navigate="navigateTo" @task-added="handleTaskAdded" />
    <!-- /transition removed -->

    <!-- ===== 第三层：日程 + 公告（桌面端） ===== -->
    <HomeDesktopSchedule
      v-if="!isMobile"
      :schedules="schedules"
      :pending-leaves="pendingLeaves"
      :campus-announcements="campusAnnouncements"
      :my-announcements="myAnnouncements"
      :upcoming-reminders="upcomingReminders"
      :cal-year="calYear"
      :cal-month="calMonth"
      @select-day="onDayClick"
      @prev-month="prevMonth"
      @next-month="nextMonth"
      @today-month="todayMonth"
      @delete-schedule="handleDeleteSchedule"
      @create="openCreateDialog"
      @delete="handleDelete"
    />

    <!-- 移动端图表子页面 -->
    <HomeMobileCharts v-if="isMobile && showChartSubPage" :class-stats="classStats" :eval-data="evalData"
      @close="showChartSubPage = false" @open-analysis="openMascotAnalysis" />

    <!-- 审批管理子页面 -->
    <!-- transition removed -->
      <div v-if="isMobile && showApprovalSubPage" class="sub-page">
        <div class="sub-page-header">
          <el-button text circle @click="showApprovalSubPage = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="sub-page-title">审批管理</span>
          <div style="width:36px"></div>
        </div>
        <div class="sub-page-body" style="padding:12px 16px">
          <!-- Tabs: 待审批 / 已通过 / 已拒绝 -->
          <el-tabs v-model="approvalActiveTab" @tab-change="loadApprovalData">
            <el-tab-pane label="待审批" name="pending">
              <!-- 请假申请列表 -->
              <div class="mobile-section-card" style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                  <span style="font-weight:600;font-size:14px">请假申请</span>
                  <el-tag v-if="approvalPendingLeaves.length" type="warning" size="small" effect="plain">{{ approvalPendingLeaves.length }} 条待批</el-tag>
                </div>
                <div v-if="approvalPendingLeaves.length === 0" class="empty-tip-small">暂无待批请假</div>
                <div v-for="row in approvalPaginatedPendingLeaves" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600;font-size:14px">{{ row.student_name }}</span>
                    <el-tag size="small" effect="plain">{{ approvalTypeLabel(row.leave_type) }}</el-tag>
                  </div>
                  <div style="font-size:13px;color:#666;margin-bottom:4px">{{ row.start_date }} ~ {{ row.end_date }}</div>
                  <div v-if="row.reason" style="font-size:13px;color:#999;margin-bottom:8px;line-height:1.4">{{ row.reason }}</div>
                  <div v-if="approvalAnalysisMap[row.id]" style="margin-bottom:8px">
                    <el-tag :type="approvalAnalysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                      {{ approvalAnalysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                    </el-tag>
                    <span style="font-size:12px;color:#999;margin-left:6px">{{ approvalAnalysisMap[row.id].reason }}</span>
                  </div>
                  <div v-else style="margin-bottom:8px">
                    <el-tag type="info" size="small" effect="plain"><el-icon class="is-loading"><Loading /></el-icon> 分析中</el-tag>
                  </div>
                  <div style="display:flex;gap:8px">
                    <el-button type="success" size="small" @click="approvalHandleApprove(row)"><el-icon><Check /></el-icon> 通过</el-button>
                    <el-button type="danger" size="small" plain @click="approvalShowReject(row)"><el-icon><Close /></el-icon> 拒绝</el-button>
                  </div>
                </div>
                <el-pagination v-if="approvalPendingLeaves.length > 0"
                  v-model:current-page="approvalCurrentPageLeaves"
                  :page-size="10" :total="approvalPendingLeaves.length"
                  layout="prev, pager, next" small style="margin-top:8px" />
              </div>

              <!-- 办事申请列表 -->
              <div class="mobile-section-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                  <span style="font-weight:600;font-size:14px">办事申请</span>
                  <el-tag v-if="approvalPendingTickets.length" type="warning" size="small" effect="plain">{{ approvalPendingTickets.length }} 条待批</el-tag>
                </div>
                <div v-if="approvalPendingTickets.length === 0" class="empty-tip-small">暂无待办申请</div>
                <div v-for="row in approvalPaginatedPendingTickets" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600;font-size:14px">{{ row.title }}</span>
                    <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
                  </div>
                  <div v-if="row.content" style="font-size:13px;color:#999;margin-bottom:8px;line-height:1.4">{{ row.content }}</div>
                  <div style="display:flex;gap:8px">
                    <el-button type="success" size="small" @click="approvalHandleTicketApprove(row.id)"><el-icon><Check /></el-icon> 通过</el-button>
                    <el-button type="danger" size="small" plain @click="approvalHandleTicketReject(row.id)"><el-icon><Close /></el-icon> 拒绝</el-button>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="已通过" name="approved">
              <div class="mobile-section-card">
                <div v-if="approvalApprovedLeaves.length === 0" class="empty-tip-small">暂无已通过请假</div>
                <div v-for="row in approvalPaginatedApprovedLeaves" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <span style="font-weight:600;font-size:14px">{{ row.student_name }}</span>
                    <el-tag size="small" effect="plain">{{ approvalTypeLabel(row.leave_type) }}</el-tag>
                  </div>
                  <div style="font-size:13px;color:#666">{{ row.start_date }} ~ {{ row.end_date }}</div>
                  <div style="margin-top:6px"><el-tag type="success" size="small" effect="dark">已通过</el-tag></div>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="已拒绝" name="rejected">
              <div class="mobile-section-card">
                <div v-if="approvalRejectedLeaves.length === 0" class="empty-tip-small">暂无已拒绝请假</div>
                <div v-for="row in approvalPaginatedRejectedLeaves" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <span style="font-weight:600;font-size:14px">{{ row.student_name }}</span>
                    <el-tag size="small" effect="plain">{{ approvalTypeLabel(row.leave_type) }}</el-tag>
                  </div>
                  <div style="font-size:13px;color:#666">{{ row.start_date }} ~ {{ row.end_date }}</div>
                  <div v-if="row.reject_reason" style="font-size:13px;color:#f56c6c;margin-top:4px">拒绝理由：{{ row.reject_reason }}</div>
                  <div style="margin-top:6px"><el-tag type="danger" size="small" effect="dark">已拒绝</el-tag></div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 拒绝对话框 -->
        <el-dialog v-model="approvalRejectVisible" title="拒绝理由" width="90%" :close-on-click-modal="false">
          <el-input v-model="approvalRejectReason" type="textarea" :rows="3" placeholder="请填写拒绝理由" maxlength="200" show-word-limit />
          <template #footer>
            <el-button @click="approvalRejectVisible = false">取消</el-button>
            <el-button type="danger" @click="approvalConfirmReject">确认拒绝</el-button>
          </template>
        </el-dialog>
      </div>
    <!-- /transition removed -->

    <!-- 发布公告 Dialog -->
    <el-dialog v-model="createDialogVisible" title="发布公告" width="520px">
      <el-form ref="announcementFormRef" :model="createForm" label-position="top" :rules="announcementRules">
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请输入公告标题，如：关于五一放假安排的通知" maxlength="200" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="createForm.content" type="textarea" :rows="4" placeholder="请输入公告内容，建议包含时间、地点、注意事项等" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="createForm.urgency">
            <el-radio value="normal">普通</el-radio>
            <el-radio value="important">重要</el-radio>
            <el-radio value="urgent">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="附件（可选）">
          <input type="file" @change="(e: any) => { if (e.target?.files?.[0]) createFile = e.target.files[0] }" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">发布</el-button>
      </template>
    </el-dialog>

    <!-- 待批请假弹窗 -->
    <el-dialog v-model="leaveDetailVisible" title="待处理事项" width="420px">
      <div v-if="selectedDayLeaves.length === 0" class="empty-tip">今日无待处理事项</div>
      <div v-for="l in selectedDayLeaves" :key="l.id" class="schedule-item" @click="navigateTo('/teacher/approval')">
        <div class="schedule-dot dot-warning"></div>
        <div class="schedule-content">
          <div class="schedule-title">{{ l.student_name }} 的请假申请</div>
          <div class="schedule-meta">{{ l.start_date }} ~ {{ l.end_date }} · {{ typeLabel(l.leave_type) }}</div>
        </div>
        <el-button text size="small" type="primary" @click.stop="navigateTo('/teacher/approval')">详情</el-button>
      </div>
    </el-dialog>

    <!-- 快捷添加任务弹窗（居中自定义）
        <el-dialog v-model="quickAddDialogVisible" title="添加任务" width="88%" :close-on-click-modal="false">
          <p style="margin-bottom:12px;color:#666">任务日期：<strong>{{ selectedTaskDate }}</strong></p>
          <el-form @submit.prevent>
            <el-form-item>
              <el-input
                ref="quickAddInputRef"
                v-model="quickTaskContent"
                placeholder="输入任务内容..."
                maxlength="100"
                @keyup.enter="handleQuickAddTask"
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="quickAddDialogVisible = false">取消</el-button>
            <el-button type="primary" :disabled="!quickTaskContent.trim()" @click="handleQuickAddTask">添加</el-button>
          </template>
        </el-dialog>
        -->
    <div v-if="quickAddDialogVisible" class="quick-add-overlay" @click.self="quickAddDialogVisible = false">
      <div class="quick-add-popup">
        <div class="quick-add-title">添加任务</div>
        <div class="quick-add-date">{{ selectedTaskDate }}</div>
        <input
          ref="quickAddInputRef"
          v-model="quickTaskContent"
          class="quick-add-input"
          placeholder="输入任务内容..."
          maxlength="100"
          @keyup.enter="handleQuickAddTask"
        />
        <div class="quick-add-urgency">
          <button
            v-for="u in urgencyOptions" :key="u.value"
            class="urgency-opt"
            :class="{ active: quickTaskUrgency === u.value, [u.value]: true }"
            @click="quickTaskUrgency = u.value"
          >{{ u.label }}</button>
        </div>
        <div class="quick-add-actions">
          <button class="quick-add-cancel" @click="quickAddDialogVisible = false">取消</button>
          <button class="quick-add-submit" :disabled="!quickTaskContent.trim()" @click="handleQuickAddTask">添加</button>
        </div>
      </div>
    </div>

    <!-- 添加日程弹窗 -->
    <el-dialog v-model="scheduleDialogVisible" title="添加日程" width="400px">
      <p style="margin-bottom:12px;color:#666">日期：<strong>{{ selectedDateStr }}</strong></p>
      <el-form ref="scheduleFormRef" :model="{ content: scheduleContent }" :rules="scheduleRules">
        <el-form-item prop="content">
          <el-input v-model="scheduleContent" type="textarea" :rows="3" placeholder="请输入日程内容，如：期中考试监考" />
        </el-form-item>
        <el-form-item label="等级">
          <el-radio-group v-model="scheduleUrgency">
            <el-radio value="normal">普通</el-radio>
            <el-radio value="important">重要</el-radio>
            <el-radio value="urgent">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddSchedule">保存</el-button>
      </template>
    </el-dialog>

    <!-- 桌宠弹窗：班级情况分析 -->
    <el-dialog
      v-model="showAnalysisDialog"
      class="mascot-analysis-dialog"
      :append-to-body="true"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-header">
          <img src="/images/mascot.png" alt="绵小城" class="dialog-header-mascot" />
          <div class="dialog-header-text">
            <div class="dialog-title">班级情况分析</div>
            <div class="dialog-sub">绵小城基于班级图表与学生成长数据智能生成</div>
          </div>
        </div>
      </template>
      <div class="dialog-content">
        <div v-if="analysisLoading" class="dialog-loading">
          <img src="/images/mascot.png" alt="绵小城" class="dialog-loading-mascot" />
          <p class="dialog-loading-text">{{ analysisLoadingText }}</p>
        </div>
        <div v-else-if="analysisResult" class="analysis-report markdown-body" v-html="renderedAnalysisHtml"></div>
        <div v-else class="dialog-empty">
          <el-icon class="dialog-empty-icon"><MagicStick /></el-icon>
          <p>点击下方按钮，绵小城将为您生成班级分析报告</p>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button round @click="showAnalysisDialog = false">关闭</el-button>
          <el-button round type="primary" :loading="analysisLoading" @click="startMascotAnalysis">
            <el-icon><Refresh /></el-icon> 重新分析
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, onActivated, onDeactivated, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DataAnalysis, UserFilled,
  WarningFilled as WarnIcon, EditPen, DArrowRight,
  ArrowLeft, MagicStick, Refresh, Check, List, Loading, Close
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
const { isMobile } = useResponsive()
import { getAlerts } from '@/api/crisis'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import { getDashboardStats, getClassEvaluation, getTeacherSchedules, createTeacherSchedule, deleteTeacherSchedule, getClassStats, getOverdueSchedules, updateTeacherSchedule, getStudents, suggestContacts } from '@/api/teacher'
import type { DashboardStats, ClassEvaluation, ClassStats, ScheduleItem, ScheduleUrgency, StudentSummary, ContactSuggestion } from '@/api/teacher'
import { getAnnouncements } from '@/api/campus'
import { getTeacherAnnouncements, createAnnouncement, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import type { CrisisAlert, LeaveRequestOut, Announcement, ServiceTicket } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAiAnalysis } from '@/composables/useAiAnalysis'
import { getCachedData, getPrefetchPromise } from '@/utils/teacherDashboardCache'
import { renderMarkdown } from '@/utils/markdown'
import HomeKpiCards from './HomeKpiCards.vue'
import HomeTopBanner from './HomeTopBanner.vue'
import HomeAiPanel from './HomeAiPanel.vue'
import HomeAnalyticsCharts from './HomeAnalyticsCharts.vue'
import HomeMobileCharts from './HomeMobileCharts.vue'
import HomeMobileToday from './HomeMobileToday.vue'
import HomeDesktopSchedule from './HomeDesktopSchedule.vue'
import HomeMobileTodayTasks from './HomeMobileTodayTasks.vue'
import HomeMobileSchedule from './HomeMobileSchedule.vue'

// keep-alive include 按组件名匹配，必须与 TeacherLayout 的 cachedNames 一致，否则切换时组件被销毁重建导致数据闪变
defineOptions({ name: 'teacher-home' })

const router = useRouter()
const authStore = useAuthStore()

const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})
const alerts = ref<CrisisAlert[]>([])
const proactiveActions = ref<ProactiveAction[]>([])
const contactSuggestions = ref<ContactSuggestion[]>([])
const aiLoading = ref(false)

/** 拉取 AI 决策支持数据（主动发现 + 推荐联系），低频调用不参与 30s 轮询 */
async function loadAiDecisions() {
  aiLoading.value = true
  try {
    const [acts, contacts] = await Promise.all([
      fetchProactiveActions().catch(() => [] as ProactiveAction[]),
      suggestContacts().catch(() => [] as ContactSuggestion[]),
    ])
    proactiveActions.value = acts
    contactSuggestions.value = contacts
  } finally {
    aiLoading.value = false
  }
}
const pendingLeaves = ref<LeaveRequestOut[]>([])
const announcements = ref<Announcement[]>([])
const myAnnouncements = ref<AnnouncementItem[]>([])
const createDialogVisible = ref(false)
const createForm = reactive({ title: '', content: '', urgency: 'normal' })
const createFile = ref<File | null>(null)
const announcementFormRef = ref<any>()
const announcementRules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }],
}
const classStats = ref<ClassStats>({
  total_students: 0,
  gender_stats: {},
  crisis_stats: {},
  grade_stats: {},
  political_stats: {},
  hometown_stats: {},
  crisis_trend: [],
})
const campusAnnouncements = ref<Announcement[]>([])
const showChartSubPage = ref(false)
const showScheduleSubPage = ref(false)
const showApprovalSubPage = ref(false)
const dataReady = ref(false) // 标记数据是否已加载完成，防止空状态闪烁

// 同步读取预加载缓存：setup 阶段直接填充数据，避免首次渲染时空状态闪现
function initFromCache() {
  const cachedStats = getCachedData<DashboardStats>('dashboard-stats')
  const cachedAlerts = getCachedData<CrisisAlert[]>('alerts')
  const cachedPendingLeaves = getCachedData<LeaveRequestOut[]>('pending-leaves')
  const cachedAnnouncements = getCachedData<Announcement[]>('announcements')
  const cachedEval = getCachedData<ClassEvaluation>('class-evaluation')
  const cachedClassStats = getCachedData<ClassStats>('class-stats')
  const cachedCampusAnn = getCachedData<Announcement[]>('announcements')
  const cachedSchedules = getCachedData<ScheduleItem[]>('teacher-schedules')
  const cachedMyAnn = getCachedData<AnnouncementItem[]>('teacher-announcements')
  const cachedOverdue = getCachedData<ScheduleItem[]>('overdue-schedules')
  if (cachedStats) stats.value = cachedStats
  if (cachedAlerts) alerts.value = cachedAlerts
  if (cachedPendingLeaves) pendingLeaves.value = cachedPendingLeaves
  if (cachedAnnouncements) announcements.value = cachedAnnouncements
  if (cachedEval) evalData.value = cachedEval
  if (cachedClassStats) classStats.value = cachedClassStats
  if (cachedCampusAnn) campusAnnouncements.value = cachedCampusAnn
  if (cachedSchedules) schedules.value = cachedSchedules
  if (cachedMyAnn) myAnnouncements.value = cachedMyAnn
  if (cachedOverdue) overdueSchedules.value = cachedOverdue
  // 只要任意缓存有数据，就标记为 ready，避免显示加载占位符
  if (cachedStats || cachedAlerts || cachedPendingLeaves || cachedAnnouncements || cachedEval || cachedClassStats || cachedCampusAnn || cachedSchedules || cachedMyAnn) {
    dataReady.value = true
  }
}
initFromCache()

// ===== 审批管理子页面 =====
const approvalActiveTab = ref('pending')
const approvalPendingLeaves = ref<LeaveRequestOut[]>([])
const approvalPendingTickets = ref<ServiceTicket[]>([])
const approvalApprovedLeaves = ref<LeaveRequestOut[]>([])
const approvalRejectedLeaves = ref<LeaveRequestOut[]>([])
const approvalAnalysisMap = ref<Record<number, { suggestion: string; reason: string }>>({})
const approvalRejectVisible = ref(false)
const approvalRejectTarget = ref<LeaveRequestOut | null>(null)
const approvalRejectReason = ref('')
const approvalCurrentPageLeaves = ref(1)
const approvalCurrentPageTickets = ref(1)
const approvalCurrentPageApprovedLeaves = ref(1)
const approvalCurrentPageRejectedLeaves = ref(1)

const approvalPaginatedPendingLeaves = computed(() => {
  const start = (approvalCurrentPageLeaves.value - 1) * 10
  return approvalPendingLeaves.value.slice(start, start + 10)
})
const approvalPaginatedPendingTickets = computed(() => {
  const start = (approvalCurrentPageTickets.value - 1) * 10
  return approvalPendingTickets.value.slice(start, start + 10)
})
const approvalPaginatedApprovedLeaves = computed(() => {
  const start = (approvalCurrentPageApprovedLeaves.value - 1) * 10
  return approvalApprovedLeaves.value.slice(start, start + 10)
})
const approvalPaginatedRejectedLeaves = computed(() => {
  const start = (approvalCurrentPageRejectedLeaves.value - 1) * 10
  return approvalRejectedLeaves.value.slice(start, start + 10)
})

function approvalTypeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

async function loadApprovalData() {
  if (approvalActiveTab.value === 'pending') {
    try {
      approvalPendingLeaves.value = await getPendingLeaves()
      approvalLoadAnalysis()
    } catch {}
    try { approvalPendingTickets.value = (await getTickets()).filter((t: ServiceTicket) => t.status === 'pending') } catch {}
  } else if (approvalActiveTab.value === 'approved') {
    try { approvalApprovedLeaves.value = await getAllLeaves('approved') } catch {}
  } else if (approvalActiveTab.value === 'rejected') {
    try { approvalRejectedLeaves.value = await getAllLeaves('rejected') } catch {}
  }
}

function chunkArray<T>(arr: T[], size: number): T[][] {
  const result: T[][] = []
  for (let i = 0; i < arr.length; i += size) result.push(arr.slice(i, i + size))
  return result
}

async function approvalLoadAnalysis() {
  const todo = approvalPendingLeaves.value.filter((leave) => !approvalAnalysisMap.value[leave.id])
  for (const leave of todo) approvalAnalysisMap.value[leave.id] = { suggestion: 'approve', reason: '分析中...' }
  const batches = chunkArray(todo, 4)
  for (const batch of batches) {
    const results = await Promise.all(batch.map(async (leave) => {
      try { return { id: leave.id, result: await analyzeLeave(leave.id) } }
      catch { return { id: leave.id, result: { suggestion: 'approve', reason: 'AI分析暂时不可用' } } }
    }))
    for (const { id, result } of results) approvalAnalysisMap.value[id] = result
  }
}

async function approvalHandleApprove(row: LeaveRequestOut) {
  try {
    await reviewLeaveApi(row.id, 'approve')
    ElMessage.success('已通过')
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

function approvalShowReject(row: LeaveRequestOut) {
  approvalRejectTarget.value = row
  approvalRejectReason.value = ''
  approvalRejectVisible.value = true
}

async function approvalConfirmReject() {
  if (!approvalRejectReason.value.trim()) { ElMessage.warning('请填写拒绝理由'); return }
  if (!approvalRejectTarget.value) return
  try {
    await reviewLeaveApi(approvalRejectTarget.value.id, 'reject', approvalRejectReason.value)
    ElMessage.success('已拒绝')
    approvalRejectVisible.value = false
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

async function approvalHandleTicketApprove(id: number) {
  try {
    await approveTicketApi(id, 'approve')
    ElMessage.success('已通过')
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

async function approvalHandleTicketReject(id: number) {
  try {
    await approveTicketApi(id, 'reject')
    ElMessage.success('已拒绝')
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

// 当打开审批子页面时加载数据
watch(showApprovalSubPage, (val) => {
  if (val) loadApprovalData()
})

// 今日任务
const todayLeaves = computed(() => {
  const date = selectedTaskDate.value
  return pendingLeaves.value.filter(l => l.start_date <= date && l.end_date >= date)
})
const todaySchedules = computed(() => {
  const date = selectedTaskDate.value
  return schedules.value.filter(s => s.date === date)
})

// 标记任务完成/取消完成：持久化到后端；原地更新状态不重排列表（勾选后卡片不跳位置）；刷新后不丢失
async function toggleScheduleComplete(s: ScheduleItem) {
  const target = !s.completed
  try {
    await updateTeacherSchedule(s.id, target)
    // PATCH 已提交，作废在途的逾期列表请求，防止其旧响应覆盖即将更新的本地状态
    overdueReqSeq++
    s.completed = target
    s.completed_at = target ? new Date().toISOString() : null
    // 逾期提醒条本地即时同步（不等网络往返）
    const todayStr = new Date().toISOString().slice(0, 10)
    if (target) {
      overdueSchedules.value = overdueSchedules.value.filter(o => o.id !== s.id)
    } else if (s.date < todayStr) {
      overdueSchedules.value = [s, ...overdueSchedules.value.filter(o => o.id !== s.id)]
    }
    await loadOverdueSchedules() // 本地同步后与服务器对齐（内部有 guard，失败不抛）
  } catch {
    ElMessage.error('操作失败')
  }
}

// ===== AI 班级分析 =====
const { loading: analysisLoading, renderedResult: analysisResult, analyze: runAnalysis } = useAiAnalysis('teacher-class-analysis')

// 桌宠与弹窗状态
const showAnalysisDialog = ref(false)
const analysisLoadingText = ref('绵小城正在深度分析班级情况...')
const studentProfiles = ref<StudentSummary[]>([])

const renderedAnalysisHtml = computed(() => renderMarkdown(analysisResult.value))


function crisisLevelLabel(level?: string | null) {
  const map: Record<string, string> = { severe: '高危预警', moderate: '中危预警', mild: '低危预警', resolved: '已解决' }
  return level ? (map[level] || level) : '暂无预警'
}

/** 拉取手下学生的成长画像（供 AI 分析使用） */
async function loadStudentProfiles() {
  if (studentProfiles.value.length) return
  try {
    studentProfiles.value = await getStudents()
  } catch {
    studentProfiles.value = [] // 拉取失败时退化为仅用汇总数据分析
  }
}

function buildAnalysisPrompt() {
  const stats = classStats.value
  const ev = evalData.value
  const g = ev.growth || {}
  const profiles = studentProfiles.value
  const listed = profiles.slice(0, 60)
  const profileLines = listed.map((p) => {
    const skills = p.skills_json?.skills?.length ?? 0
    const interests = p.skills_json?.interests?.length ?? 0
    const crisisNote = p.crisis_level && p.latest_crisis_summary
      ? `、最近危机「${p.latest_crisis_summary.slice(0, 40)}」`
      : ''
    return `- ${p.name}：成长记录${p.growth_count}条、综合评分${p.score}分、心理状态「${crisisLevelLabel(p.crisis_level)}」、技能${skills}项、兴趣${interests}项${crisisNote}`
  })
  const profileText = profileLines.length
    ? profileLines.join('\n') + (profiles.length > listed.length ? `\n（其余${profiles.length - listed.length}名学生未列出）` : '')
    : '（暂无学生明细数据）'

  return `作为辅导员老师，请基于以下班级图表数据与手下学生成长数据，分析班级情况并提出建议：

班级图表数据：
- 学生总数：${stats.total_students}
- 性别比例：${JSON.stringify(stats.gender_stats)}
- 政治面貌：${JSON.stringify(stats.political_stats)}
- 生源地分布：${JSON.stringify(stats.hometown_stats)}
- 心理危机分布：高危${stats.crisis_stats?.severe || 0}人、中危${stats.crisis_stats?.moderate || 0}人、低危${stats.crisis_stats?.mild || 0}人、已解决${stats.crisis_stats?.resolved || 0}人
- 成绩分布：优秀${stats.grade_stats?.excellent || 0}人、良好${stats.grade_stats?.good || 0}人、中等${stats.grade_stats?.medium || 0}人、及格${stats.grade_stats?.pass || 0}人、不及格${stats.grade_stats?.fail || 0}人
- 危机预警趋势（近6个月）：${JSON.stringify(stats.crisis_trend)}

班级成长数据：
- 平均GPA：${ev.avg_gpa}，平均综合评分：${ev.avg_score}
- 成长记录统计：荣誉${g.honor || 0}条、竞赛${g.competition || 0}条、实践${g.practice || 0}条、论文${g.paper || 0}条、成果${g.achievement || 0}条
- 待审批请假：${ev.pending_leaves}人

手下学生成长明细：
${profileText}

请从以下方面进行分析：
1. 班级整体概况与综合能力画像
2. 学业成绩分析
3. 心理健康与危机预警分析
4. 学生成长发展分析（成长记录、技能、竞赛、实践等维度）
5. 辅导员工作建议（对需重点关注的个别学生点名提醒）

请用简洁专业的语言，控制在600字以内。`
}

/** 桌宠：打开分析弹窗（首次自动触发分析） */
async function openMascotAnalysis() {
  showAnalysisDialog.value = true
  if (!analysisResult.value && !analysisLoading.value) {
    await startMascotAnalysis()
  }
}

/** 桌宠弹窗：重新/开始分析 */
async function startMascotAnalysis() {
  if (analysisLoading.value) return
  analysisLoadingText.value = '绵小城正在收集班级数据与学生成长记录...'
  await loadStudentProfiles()
  analysisLoadingText.value = '绵小城正在深度分析班级情况...'
  await runAnalysis(buildAnalysisPrompt(), { skipCache: true })
}

async function handleClassAnalysis() {
  await loadStudentProfiles()
  await runAnalysis(buildAnalysisPrompt(), { skipCache: true })
}

const pendingCount = computed(() =>
  stats.value.pending_leave_count + stats.value.severe_alert_count
)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayStr = computed(() => {
  const d = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${week[d.getDay()]}`
})

const pendingTaskCount = computed(() => todayLeaves.value.length + todaySchedules.value.length)

const statCards = computed(() => [
  {
    label: '我的学生', value: stats.value.total_students,
    color: '#5b8def', icon: UserFilled, link: '/teacher/students',
  },
  {
    label: '危机预警', value: stats.value.alert_count,
    color: '#f56c6c', icon: WarnIcon, link: '__crisis__',
  },
  {
    label: '待办任务', value: pendingTaskCount.value,
    color: '#e63946', icon: List, link: '__today__',
  },
  {
    label: '待批请假', value: stats.value.pending_leave_count,
    color: '#e6a23c', icon: EditPen, link: '/teacher/approval',
  },
])

// ===== Class Evaluation Radar =====
const evalData = ref<ClassEvaluation>({
  total_students: 0, avg_gpa: 0, avg_score: 0,
  growth: {}, crisis: {}, pending_leaves: 0,
})

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

const showCrisisSubPage = ref(false)
const showTodaySubPage = ref(false)
watch(showTodaySubPage, (open) => {
  if (open) selectedTaskDate.value = new Date().toISOString().slice(0, 10)
})

// 任务日期选择
const selectedTaskDate = ref(new Date().toISOString().slice(0, 10))
const quickTaskContent = ref('')
const quickTaskUrgency = ref<ScheduleUrgency>('normal')
const quickAddDialogVisible = ref(false)
const quickAddInputRef = ref<HTMLInputElement>()
// 任务等级选项（普通/重要/紧急）
const urgencyOptions: { value: ScheduleUrgency; label: string }[] = [
  { value: 'normal', label: '普通' },
  { value: 'important', label: '重要' },
  { value: 'urgent', label: '紧急' },
]

// 逾期未完成任务提醒（已过期且未完成，跨月份）
const overdueSchedules = ref<ScheduleItem[]>([])
// 逾期列表请求序号：仅写入最新请求的响应，避免轮询旧数据覆盖刚勾选完成的状态
let overdueReqSeq = 0

// 打开快捷添加弹窗并聚焦输入框
function openQuickAddDialog() {
  quickAddDialogVisible.value = true
  quickTaskUrgency.value = 'normal'
  nextTick(() => {
    quickAddInputRef.value?.focus()
  })
}

// 快速添加任务（弹窗）
async function handleQuickAddTask() {
  if (!quickTaskContent.value.trim()) return
  try {
    await createTeacherSchedule(selectedTaskDate.value, quickTaskContent.value.trim(), quickTaskUrgency.value)
    ElMessage.success('任务已添加')
    quickTaskContent.value = ''
    quickTaskUrgency.value = 'normal'
    quickAddDialogVisible.value = false
    // 更新日历年月以加载对应月份数据
    const d = new Date(selectedTaskDate.value)
    calYear.value = d.getFullYear()
    calMonth.value = d.getMonth() + 1
    loadSchedules()
  } catch {
    ElMessage.error('添加失败')
  }
}

// 任务子页弹窗选择日期：同步共享状态并重载对应月份数据
function handlePopupDateSelect(date: string) {
  selectedTaskDate.value = date
  const d = new Date(date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

// 任务子页弹窗内添加任务成功后：同步日历年月以加载对应月份数据
function handleTaskAdded() {
  const d = new Date(selectedTaskDate.value)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

function navigateTo(path: string) {
  if (path === '__crisis__') {
    showCrisisSubPage.value = true
  } else if (path === '__today__') {
    showTodaySubPage.value = true
  } else {
    router.push(path)
  }
}

// ===== Calendar State =====
interface CalDay {
  num: number
  month: number
  isToday: boolean
  isPast: boolean
  hasLeave: boolean
  hasSchedule: boolean
  dateStr: string
  leaves: LeaveRequestOut[]
}
const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth() + 1)
const schedules = ref<ScheduleItem[]>([])
const scheduleDialogVisible = ref(false)
const scheduleContent = ref('')
const scheduleUrgency = ref<ScheduleUrgency>('normal')
const scheduleFormRef = ref<any>()
const scheduleRules = {
  content: [{ required: true, message: '请输入日程内容', trigger: 'blur' }],
}
const selectedDateStr = ref('')
const leaveDetailVisible = ref(false)
const selectedDayLeaves = ref<LeaveRequestOut[]>([])

const upcomingReminders = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const threeDaysLater = new Date(today)
  threeDaysLater.setDate(threeDaysLater.getDate() + 3)
  return schedules.value.filter(s => {
    const d = new Date(s.date)
    return !s.completed && d >= today && d <= threeDaysLater
  }).sort((a, b) => a.date.localeCompare(b.date))
})

function prevMonth() {
  if (calMonth.value === 1) { calYear.value--; calMonth.value = 12 }
  else calMonth.value--
  loadSchedules()
}
function nextMonth() {
  if (calMonth.value === 12) { calYear.value++; calMonth.value = 1 }
  else calMonth.value++
  loadSchedules()
}
function todayMonth() {
  const n = new Date()
  calYear.value = n.getFullYear()
  calMonth.value = n.getMonth() + 1
  loadSchedules()
}

function onDayClick(day: CalDay) {
  if (day.month !== 0 || day.isPast) return
  if (day.hasLeave) {
    selectedDayLeaves.value = day.leaves
    leaveDetailVisible.value = true
  } else {
    selectedDateStr.value = day.dateStr
    scheduleContent.value = ''
    scheduleUrgency.value = 'normal'
    scheduleDialogVisible.value = true
  }
}

async function handleAddSchedule() {
  if (scheduleFormRef.value) {
    try { await scheduleFormRef.value.validate() } catch { return }
  }
  try {
    await createTeacherSchedule(selectedDateStr.value, scheduleContent.value, scheduleUrgency.value)
    ElMessage.success('日程已添加')
    scheduleDialogVisible.value = false
    scheduleUrgency.value = 'normal'
    loadSchedules()
  } catch { ElMessage.error('添加失败') }
}

async function handleAddScheduleFromSubPage(date: string) {
  if (!date || !scheduleContent.value.trim()) return
  try {
    await createTeacherSchedule(date, scheduleContent.value.trim(), scheduleUrgency.value)
    ElMessage.success('日程已添加')
    scheduleContent.value = ''
    scheduleUrgency.value = 'normal'
    showScheduleSubPage.value = false
    loadSchedules()
  } catch { ElMessage.error('添加失败') }
}

async function handleDeleteSchedule(id: number) {
  try {
    await deleteTeacherSchedule(id)
    ElMessage.success('已删除')
    loadSchedules()
  } catch { ElMessage.error('删除失败') }
}

async function loadSchedules() {
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch
  // 仅在本地无数据时用缓存兜底：已有数据时跳过缓存，避免轮询期间旧缓存覆盖刚勾选的完成状态
  const cached = getCachedData<ScheduleItem[]>('teacher-schedules')
  if (cached && schedules.value.length === 0) schedules.value = cached
  try {
    schedules.value = await getTeacherSchedules(calYear.value, calMonth.value)
  } catch { /* ignore */ }
}

async function loadOverdueSchedules() {
  const seq = ++overdueReqSeq
  try {
    const data = await getOverdueSchedules()
    // 仅当前最新请求的响应才写入，防止过期响应覆盖本地刚同步的勾选状态
    if (seq === overdueReqSeq) overdueSchedules.value = data
  } catch { /* ignore */ }
}

async function loadMyAnnouncements() {
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch
  const cached = getCachedData<AnnouncementItem[]>('teacher-announcements')
  if (cached) myAnnouncements.value = cached
  try { myAnnouncements.value = await getTeacherAnnouncements() }
  catch { /* ignore */ }
}

function openCreateDialog() {
  createForm.title = ''
  createForm.content = ''
  createForm.urgency = 'normal'
  createFile.value = null
  createDialogVisible.value = true
}

async function handleCreate() {
  if (announcementFormRef.value) {
    try { await announcementFormRef.value.validate() } catch { return }
  }
  const fd = new FormData()
  fd.append('title', createForm.title)
  fd.append('content', createForm.content)
  fd.append('urgency', createForm.urgency)
  if (createFile.value) fd.append('file', createFile.value)
  try {
    await createAnnouncement(fd)
    ElMessage.success('发布成功')
    createDialogVisible.value = false
    loadMyAnnouncements()
  } catch { ElMessage.error('发布失败') }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此公告？', '提示')
    await deleteAnnouncement(id)
    ElMessage.success('已删除')
    loadMyAnnouncements()
  } catch { /* canceled or error */ }
}

// 数据预加载缓存：优先读取布局预加载的缓存数据（即时显示），然后并行刷新
async function loadData() {
  // 如果预加载仍在进行，先等待其完成（避免从空缓存读取导致数字跳变）
  const prefetch = getPrefetchPromise()
  if (prefetch) await prefetch

  // 从预加载缓存读取
  const cached = {
    s: getCachedData<DashboardStats>('dashboard-stats'),
    a: getCachedData<CrisisAlert[]>('alerts'),
    pl: getCachedData<LeaveRequestOut[]>('pending-leaves'),
    ann: getCachedData<Announcement[]>('announcements'),
    ev: getCachedData<ClassEvaluation>('class-evaluation'),
    cs: getCachedData<ClassStats>('class-stats'),
    ca: getCachedData<Announcement[]>('announcements'),
  }
  // 立即使用缓存数据（如果有的话），消除加载等待
  if (cached.s) stats.value = cached.s
  if (cached.a) alerts.value = cached.a
  if (cached.pl) pendingLeaves.value = cached.pl
  if (cached.ann) announcements.value = cached.ann
  if (cached.ev) evalData.value = cached.ev
  if (cached.cs) classStats.value = cached.cs
  if (cached.ca) campusAnnouncements.value = cached.ca

  // 并行刷新最新数据（静默更新，不触发加载状态）
  const [s, a, pl, ann, ev, cs, ca] = await Promise.all([
    getDashboardStats().catch(() => stats.value),
    getAlerts(undefined).catch(() => alerts.value),
    getPendingLeaves().catch(() => pendingLeaves.value),
    getAnnouncements().catch(() => announcements.value),
    getClassEvaluation().catch(() => evalData.value),
    getClassStats().catch(() => classStats.value),
    getAnnouncements().catch(() => campusAnnouncements.value),
  ])
  stats.value = s
  alerts.value = a
  pendingLeaves.value = pl
  announcements.value = ann
  evalData.value = ev
  classStats.value = cs
  campusAnnouncements.value = ca
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastRefreshAt = 0

// 静默后台刷新：并行加载所有数据，不触发任何加载状态
async function silentRefresh() {
  await Promise.all([
    loadData(),
    loadSchedules(),
    loadMyAnnouncements(),
    loadOverdueSchedules(),
  ]).catch(() => {})
  lastRefreshAt = Date.now()
  dataReady.value = true // 数据加载完成，允许显示空状态
}

onMounted(() => {
  silentRefresh()
  loadAiDecisions()
  pollTimer = setInterval(silentRefresh, 30000)
})

onActivated(() => {
  // 返回首页时重置日期到今天
  selectedTaskDate.value = new Date().toISOString().slice(0, 10)
  // 距上次刷新超过60秒才触发静默刷新（后台更新数据，不触发加载动画）
  if (Date.now() - lastRefreshAt >= 60_000) {
    silentRefresh()
  }
  // 恢复轮询（若被 onDeactivated 暂停）
  if (pollTimer === null) {
    pollTimer = setInterval(silentRefresh, 30000)
  }
})

onDeactivated(() => {
  // 暂停轮询，但保留组件状态
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

onUnmounted(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style>
/* 全局禁用教师首页所有 CSS 动效（非 scoped：覆盖 Element Plus 内部元素与伪元素；ECharts 动画已在各图表选项中单独关闭） */
.home-dashboard,
.home-dashboard *,
.home-dashboard *::before,
.home-dashboard *::after {
  transition: none !important;
  animation: none !important;
}
</style>

<style scoped>
/* ===== Global ===== */
.home-dashboard {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.section-title:hover {
  opacity: 0.7;
}


/* ===== Common ===== */
.empty-tip {
  text-align: center;
  color: #bbb;
  padding: 24px 0;
  font-size: 13px;
}

.empty-tip-small {
  text-align: center;
  color: #bbb;
  padding: 14px 0;
  font-size: 12px;
}

/* ===== Schedule Items ===== */
.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.schedule-item:hover {
  background: rgba(91,141,239,0.05);
}

.schedule-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-warning { background: #e6a23c; }

.schedule-content {
  flex: 1;
  min-width: 0;
}

.schedule-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.schedule-meta {
  font-size: 11px;
  color: #999;
  margin-top: 1px;
}

/* 移动端图表卡片 */
.mobile-charts {
  display: flex; flex-direction: column; gap: 10px;
  margin-bottom: 12px;
}
.mobile-chart-card {
  background: #fff; border-radius: 10px; padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
.mobile-chart-preview {
  display: flex; flex-direction: column;
}
.preview-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid #f5f5f5;
  font-size: 13px; color: #333; cursor: pointer;
}
.preview-item:last-child { border-bottom: none; }
.preview-arrow { color: #ccc; font-size: 14px; }

/* 子页面 */
.sub-page {
  position: fixed; inset: 0; background: #f5f7fa;
  z-index: 100; display: flex; flex-direction: column;
}
.sub-page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fff;
  border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
.sub-page-title {
  font-size: 16px; font-weight: 600; color: #1a1a1a;
}
.sub-page-body {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}

/* 移动端区块卡片 */
.mobile-section-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.mobile-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.dot-leave { background: #e6a23c; }
.dot-schedule { background: #409eff; }

.schedule-add-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

/* ===== Responsive ===== */
@media (max-width: 767px) {
  .home-dashboard {
    padding: 0 8px 12px;
  }

  .section-title {
    font-size: 13px;
  }

  /* 快捷添加任务弹窗 */
  .quick-add-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 2100;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }
  .quick-add-popup {
    width: 280px;
    padding: 20px 16px 16px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  }
  .quick-add-title {
    text-align: center;
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
  }
  .quick-add-date {
    text-align: center;
    font-size: 12px;
    color: #9ca3af;
    margin: 6px 0 14px;
  }
  .quick-add-input {
    width: 100%;
    box-sizing: border-box;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #f9fafb;
    padding: 10px 12px;
    font-size: 14px;
    color: #1f2937;
    outline: none;
  }
  .quick-add-input:focus {
    border-color: #3b82f6;
    background: #fff;
  }
  .quick-add-input::placeholder {
    color: #c0c4cc;
  }
  .quick-add-actions {
    display: flex;
    gap: 10px;
    margin-top: 16px;
  }
  .quick-add-cancel {
    flex: 1;
    padding: 9px 0;
    border: none;
    border-radius: 8px;
    background: #f3f4f6;
    color: #6b7280;
    font-size: 14px;
    cursor: pointer;
  }
  .quick-add-submit {
    flex: 1;
    padding: 9px 0;
    border: none;
    border-radius: 8px;
    background: #3b82f6;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
  }
  .quick-add-submit:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .quick-add-urgency {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  .urgency-opt {
    flex: 1;
    padding: 7px 0;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fff;
    color: #6b7280;
    font-size: 12px;
    cursor: pointer;
  }
  .urgency-opt.active {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #2563eb;
    font-weight: 600;
  }
  .urgency-opt.active.important {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #b45309;
  }
  .urgency-opt.active.urgent {
    border-color: #ef4444;
    background: #fef2f2;
    color: #dc2626;
  }

  @keyframes mascot-pet-bounce {
    0%, 100% { transform: translateY(0) scale(1); }
    30% { transform: translateY(-8px) scale(1.04); }
    55% { transform: translateY(0) scale(1); }
    75% { transform: translateY(-4px) scale(1.02); }
  }

  /* 桌宠分析弹窗 */
  .dialog-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dialog-header-mascot {
    width: 40px; height: 40px;
    object-fit: contain;
    filter: drop-shadow(0 2px 6px rgba(139, 92, 246, 0.35));
  }
  .dialog-header-text { display: flex; flex-direction: column; }
  .dialog-title { font-size: 16px; font-weight: 700; color: #4c1d95; }
  .dialog-sub { font-size: 11px; color: #7c3aed; margin-top: 2px; }
  .dialog-content { min-height: 200px; }
  .dialog-loading {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 36px 12px; gap: 14px;
  }
  .dialog-loading-mascot {
    width: 72px; height: 72px; object-fit: contain;
    animation: mascot-pet-bounce 1.4s ease-in-out infinite !important;
  }
  .dialog-loading-text { font-size: 13px; color: #7c3aed; margin: 0; }
  .dialog-empty {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 36px 12px; gap: 10px;
    color: #9ca3af; font-size: 13px; margin: 0;
  }
  .dialog-empty-icon { font-size: 32px; color: #c4b5fd; }
  .dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }

  :deep(.mascot-analysis-dialog) {
    border-radius: 16px !important;
    background: linear-gradient(180deg, #faf7ff 0%, #ffffff 42%) !important;
  }
  :deep(.mascot-analysis-dialog .el-dialog__header) {
    padding-bottom: 6px;
    margin-right: 0;
  }
  :deep(.mascot-analysis-dialog .el-dialog__body) {
    padding-top: 4px;
  }
  :deep(.markdown-body) {
    font-size: 13px;
    line-height: 1.75;
    color: #374151;
  }
  :deep(.markdown-body .md-h2),
  :deep(.markdown-body .md-h3) {
    font-size: 14px;
    color: #4c1d95;
    margin: 14px 0 6px;
    padding-left: 8px;
    border-left: 3px solid #8b5cf6;
  }
  :deep(.markdown-body .md-ul) {
    padding-left: 18px;
    margin: 6px 0;
  }
  :deep(.markdown-body .md-li) { margin: 3px 0; }
  :deep(.markdown-body strong) { color: #4c1d95; }


  :deep(.el-dialog) {
    width: 92vw !important;
    max-height: 80vh;
    margin: 0 auto !important;
    border-radius: 16px 16px 0 0 !important;
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    top: auto !important;
  }

  :deep(.el-dialog__body) {
    max-height: 60vh;
    overflow-y: auto;
  }
}

</style>
