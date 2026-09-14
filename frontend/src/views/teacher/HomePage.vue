<template>
  <div class="home-dashboard">
    <!-- 移动端头部 -->
    <div v-if="isMobile" class="teacher-header">
      <div class="header-bg-deco"></div>
      <div class="header-main">
        <div class="header-greeting">
          <div class="greeting-badge">
            <span class="badge-dot"></span>
            绵小城 · 教师端
          </div>
          <div class="greeting-text">{{ greeting }}，{{ authStore.userName || '教师' }}</div>
          <div class="greeting-sub">
            <el-tag v-show="pendingCount > 0" type="warning" size="small" effect="plain" style="border:none;background:rgba(255,255,255,0.2);color:#fff;">
              {{ pendingCount }} 件待办
            </el-tag>
            <el-tag v-show="stats.severe_alert_count > 0" type="danger" size="small" effect="plain" style="border:none;background:rgba(255,255,255,0.2);color:#fff;">
              {{ stats.severe_alert_count }} 条高危预警
            </el-tag>
          </div>
        </div>
        <img src="/images/mascot.png" alt="绵小城" class="header-mascot" />
      </div>
    </div>

    <!-- ===== 第一层：欢迎横幅（精简版） ===== -->
    <div v-if="!isMobile" class="welcome-banner">
      <div class="welcome-content">
        <h2 class="welcome-title">{{ greeting }}，{{ authStore.userName || '教师' }}</h2>
        <span class="today-text">{{ todayStr }}</span>
      </div>
      <div class="welcome-tags">
        <el-tag v-if="pendingCount > 0" type="warning" size="small" effect="plain">
          <el-icon><WarningFilled /></el-icon> {{ pendingCount }} 件待办
        </el-tag>
        <el-tag v-if="stats.severe_alert_count > 0" type="danger" size="small" effect="plain">
          <el-icon><WarningFilled /></el-icon> {{ stats.severe_alert_count }} 条高危预警
        </el-tag>
      </div>
    </div>

    <!-- ===== AI 绵小城悬浮按钮 ===== -->
    <div class="ai-float" @click="goAgent">
      <img src="/images/mascot.png" alt="绵小城" class="ai-mascot" />
      <span class="ai-label">绵小城</span>
    </div>

    <!-- ===== 第一层：KPI统计卡片 ===== -->
    <div class="kpi-cards">
      <div class="kpi-card" v-for="card in statCards" :key="card.label"
        :style="{ '--kpi-color': card.color }" @click="navigateTo(card.link)">
        <div class="kpi-icon">
          <el-icon :size="24"><component :is="card.icon" /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ card.value }}</div>
          <div class="kpi-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- ===== 第二层：数据分析区（左2:右1） ===== -->
    <div v-if="!isMobile" class="analytics-row">
      <!-- 左侧：雷达图 + 成绩分布 + 政治面貌 + 预警趋势 + 生源地 -->
      <div class="analytics-left">
        <!-- 第一行：雷达图 + 成绩分布 -->
        <div class="chart-row">
          <div class="chart-half">
            <div class="section-title" @click="navigateTo('/teacher/students')">
              <el-icon><DataAnalysis /></el-icon>
              <span>班级综合评估</span>
              <el-link type="primary" :underline="false" class="section-link">
                学生档案 <el-icon><DArrowRight /></el-icon>
              </el-link>
            </div>
            <div class="chart-container">
              <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
              <el-empty v-else description="暂无评估数据" :image-size="60" />
            </div>
          </div>
          <div class="chart-half">
            <div class="section-title">
              <el-icon><Histogram /></el-icon>
              <span>成绩分布</span>
            </div>
            <div class="chart-container">
              <VChart v-if="gradeBarOptions" :option="gradeBarOptions" autoresize />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </div>
          </div>
        </div>

        <!-- 第二行：政治面貌 + 预警趋势 -->
        <div class="chart-row">
          <div class="chart-half">
            <div class="section-title">
              <el-icon><UserFilled /></el-icon>
              <span>政治面貌分布</span>
            </div>
            <div class="chart-container">
              <VChart v-if="politicalPieOptions" :option="politicalPieOptions" autoresize />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </div>
          </div>
          <div class="chart-half">
            <div class="section-title">
              <el-icon><WarningFilled /></el-icon>
              <span>预警趋势</span>
            </div>
            <div class="chart-container">
              <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
              <el-empty v-else description="暂无数据" :image-size="60" />
            </div>
          </div>
        </div>

        <!-- 第三行：生源地分布（全宽） -->
        <div class="chart-full">
          <div class="section-title">
            <el-icon><Location /></el-icon>
            <span>生源地分布</span>
          </div>
          <div class="chart-container">
            <VChart v-if="hometownBarOptions" :option="hometownBarOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
      </div>

      <!-- 右侧：两个饼图 -->
      <div class="analytics-right">
        <div class="chart-section half">
          <div class="section-title">
            <el-icon><UserFilled /></el-icon>
            <span>性别比例</span>
          </div>
          <div class="chart-container pie-chart">
            <VChart v-if="genderPieOptions" :option="genderPieOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
        <div class="chart-divider"></div>
        <div class="chart-section half">
          <div class="section-title">
            <el-icon><WarningFilled /></el-icon>
            <span>心理危机分布</span>
          </div>
          <div class="chart-container pie-chart">
            <VChart v-if="crisisPieOptions" :option="crisisPieOptions" autoresize />
            <el-empty v-else description="暂无数据" :image-size="60" />
          </div>
        </div>
        <div class="chart-divider"></div>
        <div class="ai-analysis-section">
          <div class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            <span>AI 班级分析</span>
          </div>
          <div v-if="!analysisResult && !analysisLoading" class="analysis-placeholder">
            <p>点击按钮，AI 将为您分析班级数据</p>
            <el-button type="primary" @click="handleClassAnalysis" :loading="analysisLoading" size="small">
              开始分析
            </el-button>
          </div>
          <div v-else-if="analysisLoading" class="analysis-loading">
            <el-icon class="loading-icon"><DataAnalysis /></el-icon>
            <p>AI 正在分析班级数据...</p>
          </div>
          <div v-else class="analysis-content">
            <div class="analysis-text">{{ analysisResult }}</div>
            <el-button text type="primary" size="small" @click="handleClassAnalysis">
              重新分析
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 移动端：数据分析入口 -->
    <div v-if="isMobile" class="mobile-charts">
      <div class="mobile-section-card mobile-chart-entry" @click="showChartSubPage = true">
        <div class="mobile-section-header">
          <div class="section-title"><el-icon><DataAnalysis /></el-icon><span>数据分析</span></div>
          <el-icon color="#ccc"><DArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 移动端首页：逾期未处理提醒条 -->
    <div v-if="isMobile && overdueSchedules.length > 0" class="overdue-home-bar" @click="showTodaySubPage = true">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ overdueSchedules.length }} 个任务已逾期未处理，点击查看</span>
      <el-icon class="overdue-home-arrow"><DArrowRight /></el-icon>
    </div>

    <!-- 移动端：今日任务 + 公告 -->
    <div v-if="isMobile" class="mobile-today-section">
      <div class="mobile-section-card" @click="showTodaySubPage = true" style="cursor:pointer">
        <div class="mobile-section-header">
          <div class="section-title"><el-icon><Calendar /></el-icon><span>今日任务</span></div>
          <div style="display:flex;align-items:center;gap:6px">
            <span v-if="todayLeaves.length + todaySchedules.length > 0" style="font-size:12px;color:#9ca3af">{{ todayLeaves.length + todaySchedules.length }}项</span>
            <el-icon color="#ccc"><DArrowRight /></el-icon>
          </div>
        </div>
        <div v-if="todayLeaves.length === 0 && todaySchedules.length === 0" class="empty-tip-small">今日暂无待办事项</div>
        <div v-else class="task-preview">
          <div v-for="l in todayLeaves.slice(0, 2)" :key="'l-'+l.id" class="today-item" style="padding:6px 0">
            <div class="today-dot dot-leave"></div>
            <div class="today-info">
              <div class="today-title">{{ l.student_name }} 的请假申请</div>
            </div>
          </div>
          <div v-for="s in todaySchedules.slice(0, 2)" :key="'s-'+s.id" class="today-item" style="padding:6px 0">
            <div class="today-dot" :style="{ background: s.completed ? '#10b981' : s.urgency === 'urgent' ? '#ef4444' : '#3b82f6' }"></div>
            <div class="today-info">
              <div class="today-title" :class="{ 'today-done': s.completed }">{{ s.content }}</div>
            </div>
          </div>
          <div v-if="todayLeaves.length + todaySchedules.length > 4" style="font-size:11px;color:#9ca3af;text-align:center;padding-top:4px">
            还有 {{ todayLeaves.length + todaySchedules.length - 4 }} 项...
          </div>
        </div>
      </div>

      <div class="mobile-section-card">
        <div class="mobile-section-header">
          <div class="section-title"><el-icon><Bell /></el-icon><span>校园公告</span></div>
        </div>
        <div v-if="campusAnnouncements.length === 0" class="empty-tip-small">暂无校园公告</div>
        <a v-for="(item, index) in campusAnnouncements.slice(0, 5)" :key="'ca-'+index"
          :href="item.url || '#'" target="_blank" class="today-item today-link">
          <div class="today-dot dot-campus"></div>
          <div class="today-info">
            <div class="today-title">{{ item.title }}</div>
            <div class="today-meta">{{ item.date }}</div>
          </div>
        </a>
      </div>
    </div>

    <!-- 添加日程子页面 -->
    <!-- transition removed -->
      <div v-if="isMobile && showScheduleSubPage" class="sub-page">
        <div class="sub-page-header">
          <el-button text circle @click="showScheduleSubPage = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="sub-page-title">添加日程</span>
          <div style="width:36px"></div>
        </div>
        <div class="sub-page-body">
          <!-- 添加日程表单 -->
          <div class="schedule-form-card">
            <div class="form-section">
              <div class="form-label">
                <el-icon color="#667eea"><Calendar /></el-icon>
                <span>选择日期</span>
              </div>
              <el-date-picker
                v-model="scheduleDate"
                type="date"
                format="YYYY年MM月DD日"
                value-format="YYYY-MM-DD"
                placeholder="点击选择日期"
                style="width:100%"
                :clearable="false"
              />
            </div>

            <div class="form-section">
              <div class="form-label">
                <el-icon color="#667eea"><EditPen /></el-icon>
                <span>日程内容</span>
              </div>
              <el-input
                v-model="scheduleContent"
                type="textarea"
                :rows="4"
                placeholder="请输入日程内容，如：&#10;• 期中考试监考&#10;• 班级会议&#10;• 学生谈话"
                resize="none"
              />
            </div>

            <div class="form-section">
              <div class="form-label">
                <el-icon color="#667eea"><Flag /></el-icon>
                <span>任务等级</span>
              </div>
              <div class="form-urgency-options">
                <button
                  v-for="u in urgencyOptions" :key="u.value"
                  class="form-urgency-opt"
                  :class="{ active: scheduleUrgency === u.value, [u.value]: true }"
                  @click="scheduleUrgency = u.value"
                >{{ u.label }}</button>
              </div>
            </div>

            <button
              class="schedule-submit-btn"
              :class="{ active: scheduleContent.trim() && scheduleDate }"
              :disabled="!scheduleContent.trim() || !scheduleDate"
              @click="handleAddScheduleFromSubPage"
            >
              <el-icon><Check /></el-icon>
              保存日程
            </button>
          </div>

          <!-- 近期日程 -->
          <div class="schedule-upcoming-card">
            <div class="upcoming-header">
              <div class="upcoming-icon">
                <el-icon><Clock /></el-icon>
              </div>
              <span class="upcoming-title">近期日程</span>
              <span class="upcoming-count" v-if="upcomingReminders.length">{{ upcomingReminders.length }}项</span>
            </div>
            <div v-if="upcomingReminders.length === 0" class="upcoming-empty">
              <el-icon :size="32" color="#e5e7eb"><Calendar /></el-icon>
              <span>暂无近期日程</span>
            </div>
            <div v-else class="upcoming-list">
              <div v-for="r in upcomingReminders" :key="r.id" class="upcoming-item">
                <div class="upcoming-date">
                  <span class="upcoming-day">{{ new Date(r.date).getDate() }}</span>
                  <span class="upcoming-month">{{ new Date(r.date).getMonth() + 1 }}月</span>
                </div>
                <div class="upcoming-info">
                  <div class="upcoming-text">{{ r.content }}</div>
                </div>
                <button class="upcoming-delete" @click="handleDeleteSchedule(r.id)">
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
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
      <div v-if="isMobile && showTodaySubPage" class="sub-page task-page">
        <!-- 校园背景头部 -->
        <div class="task-hero">
          <img src="/images/campus/游仙校区博识楼.jpg" class="task-hero-bg" />
          <div class="task-hero-overlay"></div>
          <div class="task-hero-top">
            <button class="task-hero-back" @click="showTodaySubPage = false">
              <el-icon><ArrowLeft /></el-icon>
            </button>
          </div>
          <!-- 日期居中 -->
          <div class="task-hero-center" @click="showDatePopup = true">
            <div class="task-hero-date">{{ taskDateDisplay.month }}月{{ taskDateDisplay.day }}日</div>
            <div class="task-hero-week">
              星期{{ taskDateDisplay.week }}
              <span v-if="taskDateDisplay.isToday" class="task-hero-today">今天</span>
            </div>
            <div class="task-hero-hint">点击查看日历</div>
          </div>
          <!-- 统计 -->
          <div class="task-hero-stats">
            <div class="hero-stat">
              <span class="hero-stat-num">{{ totalTodayCount }}</span>
              <span class="hero-stat-label">总计</span>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat">
              <span class="hero-stat-num hero-stat-green">{{ completedTodayCount }}</span>
              <span class="hero-stat-label">已完成</span>
            </div>
            <div class="hero-stat-divider"></div>
            <div class="hero-stat">
              <span class="hero-stat-num hero-stat-amber">{{ pendingTodayCount }}</span>
              <span class="hero-stat-label">待处理</span>
            </div>
          </div>
        </div>

        <!-- 日期弹窗（日历式月视图） -->
        <div v-if="showDatePopup" class="cal-overlay" @click.self="closePopup">
          <div class="cal-popup">
            <!-- 月份导航 -->
            <div class="cal-popup-nav">
              <button class="cal-nav-btn" @click="popupMonth === 1 ? (popupYear--, popupMonth=12) : popupMonth--">
                <el-icon><ArrowLeft /></el-icon>
              </button>
              <span class="cal-nav-title">{{ popupYear }}年{{ popupMonth }}月</span>
              <button class="cal-nav-btn" @click="popupMonth === 12 ? (popupYear++, popupMonth=1) : popupMonth++">
                <el-icon><DArrowRight /></el-icon>
              </button>
            </div>
            <!-- 星期头 -->
            <div class="cal-week-header">
              <span v-for="d in ['日','一','二','三','四','五','六']" :key="d" :class="{ 'cal-weekend': d === '日' || d === '六' }">{{ d }}</span>
            </div>
            <!-- 日期网格 -->
            <div class="cal-grid">
              <div
                v-for="(day, i) in popupDays"
                :key="i"
                class="cal-cell"
                :class="{
                  'cal-other': day.other,
                  'cal-today': day.isToday,
                  'cal-selected': day.date === selectedTaskDate
                }"
                @click="selectPopupDate(day)"
              >
                <span class="cal-num">{{ day.num }}</span>
                <span v-if="day.hasTask" class="cal-task-dot"></span>
              </div>
            </div>
            <!-- 选中日期的任务 -->
            <div class="cal-day-plan">
              <div class="cal-day-header">
                <span class="cal-day-title">{{ popupSelectedDisplay }}</span>
                <span v-if="popupTasks.length > 0" class="cal-day-count">{{ popupTasks.length }}项</span>
              </div>
              <div v-if="popupTasks.length > 0" class="cal-day-list">
                <div v-for="t in popupTasks" :key="t.id" class="cal-day-item">
                  <span class="cal-day-dot" :style="{ background: t.color }"></span>
                  <span class="cal-day-text">{{ t.text }}</span>
                </div>
              </div>
              <!-- 添加任务 -->
              <div v-if="!popupAdding" class="cal-add-btn" @click="popupAdding = true">
                <el-icon><Plus /></el-icon>
                <span>添加任务</span>
              </div>
              <div v-else class="cal-add-form">
                <input
                  ref="popupInputRef"
                  v-model="popupTaskContent"
                  class="cal-form-input"
                  placeholder="输入任务内容..."
                  @keyup.enter="addTaskFromPopup"
                  @keyup.escape="popupAdding = false"
                />
                <div class="cal-form-urgency">
                  <button
                    v-for="u in urgencyOptions" :key="u.value"
                    class="cal-urgency-opt"
                    :class="{ active: popupTaskUrgency === u.value, [u.value]: true }"
                    @click="popupTaskUrgency = u.value"
                  >{{ u.label }}</button>
                </div>
                <div class="cal-form-actions">
                  <button class="cal-form-cancel" @click="popupAdding = false">取消</button>
                  <button class="cal-form-submit" @click="addTaskFromPopup" :disabled="!popupTaskContent.trim()">添加</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 快速添加：加号悬浮按钮 -->
        <div class="task-quick-add-fab">
          <button class="quick-add-fab" @click="openQuickAddDialog">
            <el-icon :size="22"><Plus /></el-icon>
          </button>
        </div>

        <!-- 任务列表 -->
        <div class="task-body">
          <!-- 待批请假（审批是其唯一完成路径，不提供本地勾选） -->
          <div v-if="todayLeaves.length > 0" class="task-section">
            <div class="task-section-head">
              <span class="task-section-dot" style="background:#f59e0b"></span>
              <span class="task-section-title">待批请假</span>
              <span class="task-section-badge">{{ todayLeaves.length }}</span>
            </div>
            <div
              v-for="l in todayLeaves"
              :key="'tl-'+l.id"
              class="task-card leave-card"
            >
              <div class="task-card-body">
                <div class="task-card-title">{{ l.student_name }} · {{ typeLabel(l.leave_type) }}</div>
                <div class="task-card-sub">{{ l.start_date }} ~ {{ l.end_date }}</div>
              </div>
              <button class="task-card-btn" @click="navigateTo('/teacher/approval')">审批</button>
            </div>
          </div>

          <!-- 逾期未完成（累积全部，不限日期） -->
          <div v-if="overdueSchedules.length > 0" class="task-section">
            <div class="task-section-head">
              <span class="task-section-dot" style="background:#ef4444"></span>
              <span class="task-section-title">逾期未完成</span>
              <span class="task-section-badge orange">{{ overdueSchedules.length }}</span>
            </div>
            <div
              v-for="s in overdueSchedules"
              :key="'od-'+s.id"
              class="task-card schedule-card"
              :class="['task-pending', { 'task-urgent': s.urgency === 'urgent' }]"
            >
              <div class="task-card-check" @click="toggleScheduleComplete(s)">
                <div class="tc-check">
                  <el-icon v-if="s.completed"><Check /></el-icon>
                </div>
              </div>
              <div class="task-card-body">
                <div class="task-card-title">{{ s.content }}</div>
                <div class="task-card-tags">
                  <span class="ur-badge ur-overdue">逾期 {{ s.date }}</span>
                  <span v-if="s.urgency === 'urgent'" class="ur-badge ur-urgent">紧急</span>
                  <span v-else-if="s.urgency === 'important'" class="ur-badge ur-important">重要</span>
                </div>
              </div>
              <button class="task-card-del" @click="handleDeleteSchedule(s.id)">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </div>

          <!-- 日程安排（当前所选日期） -->
          <div v-if="todaySchedules.length > 0" class="task-section">
            <div class="task-section-head">
              <span class="task-section-dot" style="background:#3b82f6"></span>
              <span class="task-section-title">日程安排</span>
              <span class="task-section-badge">{{ todaySchedules.length }}</span>
            </div>
            <div
              v-for="s in todaySchedules"
              :key="'ts-'+s.id"
              class="task-card schedule-card"
              :class="[
                s.completed ? 'task-completed' : 'task-pending',
                { 'task-urgent': !s.completed && s.urgency === 'urgent' }
              ]"
            >
              <div class="task-card-check" @click="toggleScheduleComplete(s)">
                <div class="tc-check" :class="{ checked: s.completed }">
                  <el-icon v-if="s.completed"><Check /></el-icon>
                </div>
              </div>
              <div class="task-card-body">
                <div class="task-card-title">{{ s.content }}</div>
                <div class="task-card-tags">
                  <span v-if="!s.completed && s.urgency === 'urgent'" class="ur-badge ur-urgent">紧急</span>
                  <span v-else-if="!s.completed && s.urgency === 'important'" class="ur-badge ur-important">重要</span>
                  <span v-if="!s.completed && isOverdueSchedule(s)" class="ur-badge ur-overdue">已逾期</span>
                </div>
              </div>
              <button class="task-card-del" @click="handleDeleteSchedule(s.id)">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="todayLeaves.length === 0 && todaySchedules.length === 0 && overdueSchedules.length === 0" class="task-empty">
            <img src="/images/mascot.png" class="task-empty-mascot" />
            <div class="task-empty-text">暂无任务安排</div>
            <div class="task-empty-sub">在上方输入框添加新任务</div>
          </div>
        </div>
      </div>
    <!-- /transition removed -->

    <!-- ===== 第三层：日程 + 公告（桌面端） ===== -->
    <div v-if="!isMobile" class="schedule-row">
      <!-- 左侧：日历 + 提醒 -->
      <div class="schedule-section">
        <div class="section-title">
          <el-icon><Calendar /></el-icon>
          <span>日程安排</span>
        </div>
        <div class="calendar-wrapper">
          <div class="cal-nav">
            <el-button text size="small" @click="prevMonth">&lt;</el-button>
            <span class="cal-title">{{ calYear }}年{{ calMonth }}月</span>
            <el-button text size="small" @click="nextMonth">&gt;</el-button>
            <el-button text size="small" @click="todayMonth" style="margin-left:4px">今天</el-button>
          </div>
          <table class="cal-table">
            <thead><tr>
              <th v-for="d in ['日','一','二','三','四','五','六']" :key="d">{{ d }}</th>
            </tr></thead>
            <tbody>
              <tr v-for="(week, wi) in calWeeks" :key="wi">
                <td v-for="(day, di) in week" :key="di"
                  :class="{
                    'cal-other': day.month !== 0,
                    'cal-today': day.isToday,
                    'cal-past': day.isPast,
                    'cal-has-leave': day.hasLeave,
                    'cal-has-schedule': day.hasSchedule,
                  }"
                  @click="onDayClick(day)"
                >
                  <span class="cal-day-num">{{ day.num }}</span>
                  <div class="cal-dots">
                    <span v-if="day.hasLeave" class="dot-leave" title="有待批请假"></span>
                    <span v-if="day.hasSchedule" class="dot-schedule" title="有日程"></span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="cal-legend">
            <span><span class="dot-leave"></span> 待批请假</span>
            <span><span class="dot-schedule"></span> 日程安排</span>
          </div>
        </div>
        <div class="upcoming-section">
          <div class="reminder-title">📌 近期提醒</div>
          <div v-if="upcomingReminders.length === 0" class="empty-tip-small">暂无提醒</div>
          <div v-for="r in upcomingReminders.slice(0, 3)" :key="r.id" class="reminder-item">
            <span class="reminder-date">{{ r.date.slice(5) }}</span>
            <span class="reminder-content">{{ r.content }}</span>
            <el-button text type="danger" size="small" @click="handleDeleteSchedule(r.id)">删除</el-button>
          </div>
        </div>
      </div>

      <!-- 右侧：公告（Tab切换） -->
      <div class="announcements-section">
        <el-tabs v-model="activeAnnouncementTab" class="announcement-tabs">
          <el-tab-pane label="校园公告" name="campus">
            <div class="announcement-list">
              <div v-if="campusAnnouncements.length === 0" class="empty-tip-small">暂无校园公告</div>
              <a v-for="(item, index) in campusAnnouncements.slice(0, 5)" :key="index"
                :href="item.url || '#'" target="_blank" class="campus-item">
                <span class="campus-title">{{ item.title }}</span>
                <span class="campus-date">{{ item.date }}</span>
              </a>
            </div>
            <el-button text type="primary" size="small" class="view-all-btn"
              href="https://jwc.mycc.edu.cn/jwgl/tzgg.htm" target="_blank">
              查看更多 <el-icon><DArrowRight /></el-icon>
            </el-button>
          </el-tab-pane>
          <el-tab-pane label="班级公告" name="class">
            <div class="tab-header">
              <el-button type="primary" size="small" @click="openCreateDialog">发布公告</el-button>
            </div>
            <div class="announcement-list">
              <div v-if="myAnnouncements.length === 0" class="empty-tip-small">暂无公告</div>
              <div v-for="a in myAnnouncements.slice(0, 5)" :key="a.id" class="announcement-item">
                <el-tag :type="urgencyTagType(a.urgency)" size="small" effect="plain">
                  {{ urgencyLabel(a.urgency) }}
                </el-tag>
                <div class="announcement-content">
                  <div class="announcement-title">{{ a.title }}</div>
                  <div class="announcement-date">{{ formatDate(a.created_at) }}</div>
                </div>
                <a v-if="a.attachment_url" :href="a.attachment_url" target="_blank" class="attach-link" @click.stop>📎</a>
                <el-button text type="danger" size="small" @click="handleDelete(a.id)">删除</el-button>
              </div>
            </div>
            <el-button v-if="myAnnouncements.length > 5" text type="primary" size="small" class="view-all-btn">
              查看全部 <el-icon><DArrowRight /></el-icon>
            </el-button>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 移动端图表子页面 -->
    <!-- transition removed -->
      <div v-if="isMobile && showChartSubPage" class="sub-page">
        <div class="sub-page-header">
          <el-button text circle @click="showChartSubPage = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="sub-page-title">数据分析</span>
          <div style="width:36px"></div>
        </div>
        <div class="sub-page-body">
          <!-- 核心数据图表 -->
          <div class="charts-grid">
            <!-- 班级综合评估 -->
            <div class="mobile-section-card chart-card">
              <div class="chart-card-header">
                <el-icon color="#5b8def"><DataAnalysis /></el-icon>
                <span>班级综合评估</span>
              </div>
              <div class="chart-container" style="height:200px">
                <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>

            <!-- 成绩分布 -->
            <div class="mobile-section-card chart-card">
              <div class="chart-card-header">
                <el-icon color="#67c23a"><Histogram /></el-icon>
                <span>成绩分布</span>
              </div>
              <div class="chart-container" style="height:200px">
                <VChart v-if="gradeBarOptions" :option="gradeBarOptions" autoresize />
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>

            <!-- 预警趋势 -->
            <div class="mobile-section-card chart-card">
              <div class="chart-card-header">
                <el-icon color="#f56c6c"><WarningFilled /></el-icon>
                <span>预警趋势</span>
              </div>
              <div class="chart-container" style="height:200px">
                <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>
          </div>
        </div>

        <!-- 悬浮桌宠：点击查看班级情况分析 -->
        <div class="mascot-pet" @click="openMascotAnalysis">
          <transition name="tip-pop">
            <div v-if="showMascotTip" class="mascot-tip-bubble">
              <span class="mascot-tip-close" @click.stop="showMascotTip = false"><el-icon><Close /></el-icon></span>
              <span class="mascot-tip-text">点我查看班级情况分析~</span>
            </div>
          </transition>
          <img src="/images/mascot.png" alt="绵小城" class="mascot-pet-img" />
        </div>
      </div>
    <!-- /transition removed -->

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
  WarningFilled, DataAnalysis, Calendar, UserFilled,
  WarningFilled as WarnIcon, EditPen, DArrowRight, Histogram, Location,
  ArrowLeft, Plus, Bell, MagicStick, Refresh, Check, Delete, Clock, List, Loading, Close, Flag
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
const { isMobile } = useResponsive()
import { getAlerts } from '@/api/crisis'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import { getDashboardStats, getClassEvaluation, getTeacherSchedules, createTeacherSchedule, deleteTeacherSchedule, getClassStats, getOverdueSchedules, updateTeacherSchedule, getStudents } from '@/api/teacher'
import type { DashboardStats, ClassEvaluation, ClassStats, ScheduleItem, ScheduleUrgency, StudentSummary } from '@/api/teacher'
import { getAnnouncements } from '@/api/campus'
import { getTeacherAnnouncements, createAnnouncement, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import type { CrisisAlert, LeaveRequestOut, Announcement, ServiceTicket } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAiAnalysis } from '@/composables/useAiAnalysis'
import { getCachedData, getPrefetchPromise } from '@/utils/teacherDashboardCache'
import { renderMarkdown } from '@/utils/markdown'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, PieChart, BarChart, LineChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent,
  RadarComponent, GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, RadarChart, PieChart, BarChart, LineChart, TooltipComponent, LegendComponent, RadarComponent, GridComponent])

// keep-alive include 按组件名匹配，必须与 TeacherLayout 的 cachedNames 一致，否则切换时组件被销毁重建导致数据闪变
defineOptions({ name: 'teacher-home' })

const router = useRouter()
const authStore = useAuthStore()

const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})
const alerts = ref<CrisisAlert[]>([])
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
const activeAnnouncementTab = ref('campus')
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

// 任务统计：完成口径只计入日程（请假以审批为完成路径）
const totalTodayCount = computed(() => todayLeaves.value.length + todaySchedules.value.length)
const completedTodayCount = computed(() => todaySchedules.value.filter(s => s.completed).length)
const pendingTodayCount = computed(() => Math.max(totalTodayCount.value - completedTodayCount.value, 0))

function isOverdueSchedule(s: ScheduleItem) {
  const today = new Date().toISOString().slice(0, 10)
  return !s.completed && s.date < today
}

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

// 格式化日期显示
const taskDateDisplay = computed(() => {
  const d = new Date(selectedTaskDate.value)
  const week = ['日', '一', '二', '三', '四', '五', '六']
  const month = d.getMonth() + 1
  const day = d.getDate()
  const today = new Date().toISOString().slice(0, 10)
  const isToday = selectedTaskDate.value === today
  return { month, day, week: week[d.getDay()], isToday }
})

// ===== AI 班级分析 =====
const { loading: analysisLoading, renderedResult: analysisResult, analyze: runAnalysis } = useAiAnalysis('teacher-class-analysis')

// 桌宠与弹窗状态
const showMascotTip = ref(false)
const showAnalysisDialog = ref(false)
const analysisLoadingText = ref('绵小城正在深度分析班级情况...')
const studentProfiles = ref<StudentSummary[]>([])
let mascotTipTimer: ReturnType<typeof setTimeout> | null = null

const renderedAnalysisHtml = computed(() => renderMarkdown(analysisResult.value))

// 进入/退出数据分析子页面时控制桌宠提示气泡
watch(showChartSubPage, (open) => {
  if (mascotTipTimer) { clearTimeout(mascotTipTimer); mascotTipTimer = null }
  if (open) {
    showMascotTip.value = true
    mascotTipTimer = setTimeout(() => { showMascotTip.value = false }, 6000)
  } else {
    showMascotTip.value = false
  }
})

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
  showMascotTip.value = false
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

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

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

const evaluationRadarOptions = computed(() => {
  const g = evalData.value.growth
  if (!g || Object.keys(g).length === 0) return null
  const vals = [g.honor || 0, g.competition || 0, g.practice || 0, g.paper || 0, g.achievement || 0]
  const max = Math.max(...vals, 1)
  return {
    animation: false,
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '荣誉', max: Math.max(max, 1) },
        { name: '竞赛', max: Math.max(max, 1) },
        { name: '实践', max: Math.max(max, 1) },
        { name: '论文', max: Math.max(max, 1) },
        { name: '成果', max: Math.max(max, 1) },
      ],
      axisName: { color: '#666', fontSize: 12 },
      splitArea: {
        areaStyle: {
          color: ['rgba(91,141,239,0.02)', 'rgba(91,141,239,0.06)'],
        },
      },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
      axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: vals,
        name: '班级综合',
        areaStyle: { color: 'rgba(91,141,239,0.25)' },
        lineStyle: { color: '#5b8def', width: 2 },
        itemStyle: { color: '#5b8def' },
      }],
    }],
  }
})

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

// ===== 性别比例饼图 =====
const genderPieOptions = computed(() => {
  const data = classStats.value.gender_stats
  if (!data || Object.keys(data).length === 0) return null
  
  const colors = ['#5b8def', '#f56c6c', '#67c23a', '#e6a23c', '#909399']
  const pieData = Object.entries(data).map(([name, value], index) => ({
    name,
    value,
    itemStyle: { color: colors[index % colors.length] }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 5,
      textStyle: { color: '#666', fontSize: 11 }
    },
    animation: false,
    series: [{
      name: '性别分布',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' }
      },
      data: pieData,
    }]
  }
})

// ===== 心理危机比例饼图 =====
const crisisPieOptions = computed(() => {
  const data = classStats.value.crisis_stats
  if (!data) return null
  
  const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#909399']
  const names = ['高危', '中危', '低危', '已解决']
  const values = [data.severe || 0, data.moderate || 0, data.mild || 0, data.resolved || 0]
  
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  const pieData = names.map((name, index) => ({
    name,
    value: values[index],
    itemStyle: { color: colors[index] }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 5,
      textStyle: { color: '#666', fontSize: 11 }
    },
    animation: false,
    series: [{
      name: '危机分布',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' }
      },
      data: pieData,
    }]
  }
})

// ===== 成绩分布柱状图 =====
const gradeBarOptions = computed(() => {
  const data = classStats.value.grade_stats
  if (!data) return null
  
  const categories = ['优秀', '良好', '中等', '及格', '不及格']
  const values = [data.excellent || 0, data.good || 0, data.medium || 0, data.pass || 0, data.fail || 0]
  
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  const colors = ['#67c23a', '#5b8def', '#e6a23c', '#f56c6c', '#909399']
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#666' }
    },
    animation: false,
    series: [{
      name: '人数',
      type: 'bar',
      barWidth: '50%',
      data: values.map((value, index) => ({
        value,
        itemStyle: { color: colors[index], borderRadius: [3, 3, 0, 0] }
      })),
    }],
  }
})

// ===== 政治面貌饼图 =====
const politicalPieOptions = computed(() => {
  const data = classStats.value.political_stats
  if (!data || Object.keys(data).length === 0) return null
  
  const total = Object.values(data).reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  const colors = ['#5b8def', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
  const pieData = Object.entries(data).map(([name, value], index) => ({
    name,
    value,
    itemStyle: { color: colors[index % colors.length] }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)'
    },
    legend: {
      orient: 'horizontal',
      bottom: 5,
      textStyle: { color: '#666', fontSize: 11 }
    },
    animation: false,
    series: [{
      name: '政治面貌',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 4,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 13, fontWeight: 'bold' }
      },
      data: pieData,
    }]
  }
})

// ===== 预警趋势折线图 =====
const crisisTrendOptions = computed(() => {
  const data = classStats.value.crisis_trend
  if (!data || data.length === 0) return null
  
  return {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>预警数量: {c}'
    },
    grid: {
      left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(d => d.month),
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#666' }
    },
    animation: false,
    series: [{
      name: '预警数量',
      type: 'line',
      data: data.map(d => d.count),
      smooth: true,
      lineStyle: { color: '#f56c6c', width: 2 },
      itemStyle: { color: '#f56c6c' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(245,108,108,0.3)' },
            { offset: 1, color: 'rgba(245,108,108,0.05)' }
          ]
        }
      }
    }]
  }
})

// ===== 生源地柱状图 =====
const hometownBarOptions = computed(() => {
  const data = classStats.value.hometown_stats
  if (!data || Object.keys(data).length === 0) return null
  
  const categories = Object.keys(data)
  const values = Object.values(data)
  
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%', right: '4%', bottom: '10%', top: '8%', containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#666', fontSize: 11, rotate: categories.length > 5 ? 30 : 0 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#666' }
    },
    animation: false,
    series: [{
      name: '人数',
      type: 'bar',
      data: values,
      itemStyle: {
        color: '#5b8def',
        borderRadius: [3, 3, 0, 0]
      }
    }]
  }
})

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
const showDatePopup = ref(false)
const popupTaskContent = ref('')
const popupTaskUrgency = ref<ScheduleUrgency>('normal')
const popupAdding = ref(false)
const popupInputRef = ref<HTMLInputElement | null>(null)

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

// 弹窗日历逻辑
const popupYear = ref(new Date().getFullYear())
const popupMonth = ref(new Date().getMonth() + 1)

const popupDays = computed(() => {
  const y = popupYear.value
  const m = popupMonth.value
  const first = new Date(y, m - 1, 1).getDay()
  const daysInMonth = new Date(y, m, 0).getDate()
  const daysInPrev = new Date(y, m - 1, 0).getDate()
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  // 有任务的日期集合
  const taskDates = new Set<string>()
  pendingLeaves.value.forEach(l => {
    if (l.start_date <= `${y}-${String(m).padStart(2,'0')}-31` && l.end_date >= `${y}-${String(m).padStart(2,'0')}-01`) {
      taskDates.add(l.start_date)
    }
  })
  schedules.value.forEach(s => taskDates.add(s.date))

  const days: { num: number; date: string; other: boolean; isToday: boolean; hasTask: boolean }[] = []
  const totalCells = Math.ceil((first + daysInMonth) / 7) * 7
  for (let i = 0; i < totalCells; i++) {
    let num: number, monthOffset: number
    if (i < first) {
      num = daysInPrev - first + i + 1
      monthOffset = -1
    } else if (i >= first + daysInMonth) {
      num = i - first - daysInMonth + 1
      monthOffset = 1
    } else {
      num = i - first + 1
      monthOffset = 0
    }
    let dateStr = ''
    if (monthOffset === 0) {
      dateStr = `${y}-${String(m).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    } else if (monthOffset === -1) {
      const pm = m === 1 ? 12 : m - 1
      const py = m === 1 ? y - 1 : y
      dateStr = `${py}-${String(pm).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    } else {
      const nm = m === 12 ? 1 : m + 1
      const ny = m === 12 ? y + 1 : y
      dateStr = `${ny}-${String(nm).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    }
    days.push({
      num,
      date: dateStr,
      other: monthOffset !== 0,
      isToday: dateStr === todayStr,
      hasTask: taskDates.has(dateStr)
    })
  }
  return days
})

// 弹窗选中日期的任务
const popupSelectedDisplay = computed(() => {
  const d = new Date(selectedTaskDate.value)
  return `${d.getMonth() + 1}月${d.getDate()}日 计划`
})

const popupTasks = computed(() => {
  const date = selectedTaskDate.value
  const tasks: { id: string; text: string; color: string }[] = []
  pendingLeaves.value.forEach(l => {
    if (l.start_date <= date && l.end_date >= date) {
      tasks.push({ id: 'l-' + l.id, text: `${l.student_name} · ${typeLabel(l.leave_type)}`, color: '#f59e0b' })
    }
  })
  schedules.value.forEach(s => {
    if (s.date === date) {
      const color = s.completed ? '#10b981' : s.urgency === 'urgent' ? '#ef4444' : '#3b82f6'
      tasks.push({ id: 's-' + s.id, text: s.content, color })
    }
  })
  return tasks
})

function selectPopupDate(day: { date: string; other: boolean }) {
  selectedTaskDate.value = day.date
  if (day.other) {
    const d = new Date(day.date)
    popupYear.value = d.getFullYear()
    popupMonth.value = d.getMonth() + 1
  }
  // 同步更新日历年月以加载对应月份数据
  const d = new Date(day.date)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadSchedules()
}

// 关闭弹窗：保留用户选择的日期（不重置为今天），否则历史/逾期任务永远无法在列表中查看勾选
function closePopup() {
  showDatePopup.value = false
}

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

// 弹窗内添加任务
async function addTaskFromPopup() {
  if (!popupTaskContent.value.trim()) return
  try {
    await createTeacherSchedule(selectedTaskDate.value, popupTaskContent.value.trim(), popupTaskUrgency.value)
    ElMessage.success('任务已添加')
    popupTaskContent.value = ''
    popupTaskUrgency.value = 'normal'
    popupAdding.value = false
    const d = new Date(selectedTaskDate.value)
    calYear.value = d.getFullYear()
    calMonth.value = d.getMonth() + 1
    loadSchedules()
  } catch {
    ElMessage.error('添加失败')
  }
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

function goAgent() {
  router.push('/teacher/agent')
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
const scheduleDate = ref(new Date().toISOString().slice(0, 10))
const scheduleFormRef = ref<any>()
const scheduleRules = {
  content: [{ required: true, message: '请输入日程内容', trigger: 'blur' }],
}
const selectedDateStr = ref('')
const leaveDetailVisible = ref(false)
const selectedDayLeaves = ref<LeaveRequestOut[]>([])

const calWeeks = computed(() => {
  const y = calYear.value
  const m = calMonth.value
  const first = new Date(y, m - 1, 1).getDay()
  const daysInMonth = new Date(y, m, 0).getDate()
  const daysInPrev = new Date(y, m - 1, 0).getDate()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`

  const leaveMap = new Map<string, LeaveRequestOut[]>()
  pendingLeaves.value.forEach(l => {
    const d = l.start_date
    if (!leaveMap.has(d)) leaveMap.set(d, [])
    leaveMap.get(d)!.push(l)
  })

  const scheduleMap = new Map<string, boolean>()
  schedules.value.forEach(s => { scheduleMap.set(s.date, true) })

  const weeks: CalDay[][] = []
  let week: CalDay[] = []
  const totalCells = Math.ceil((first + daysInMonth) / 7) * 7
  for (let i = 0; i < totalCells; i++) {
    let num: number, monthOffset: number
    if (i < first) {
      num = daysInPrev - first + i + 1
      monthOffset = -1
    } else if (i >= first + daysInMonth) {
      num = i - first - daysInMonth + 1
      monthOffset = 1
    } else {
      num = i - first + 1
      monthOffset = 0
    }
    let dateStr = ''
    if (monthOffset === 0) {
      dateStr = `${y}-${String(m).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    } else if (monthOffset === -1) {
      const pm = m === 1 ? 12 : m - 1
      const py = m === 1 ? y - 1 : y
      dateStr = `${py}-${String(pm).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    } else {
      const nm = m === 12 ? 1 : m + 1
      const ny = m === 12 ? y + 1 : y
      dateStr = `${ny}-${String(nm).padStart(2, '0')}-${String(num).padStart(2, '0')}`
    }
    week.push({
      num, month: monthOffset, isToday: dateStr === todayStr,
      isPast: monthOffset === 0 && dateStr < todayStr,
      hasLeave: leaveMap.has(dateStr), hasSchedule: scheduleMap.has(dateStr),
      dateStr, leaves: leaveMap.get(dateStr) || [],
    })
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }
  return weeks
})

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

async function handleAddScheduleFromSubPage() {
  const date = scheduleDate.value
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

const urgencyMap: Record<string, { type: string; label: string }> = {
  normal: { type: '', label: '普通' },
  important: { type: 'warning', label: '重要' },
  urgent: { type: 'danger', label: '紧急' },
}

function urgencyTagType(u: string) { return urgencyMap[u]?.type || '' }
function urgencyLabel(u: string) { return urgencyMap[u]?.label || u }

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
  if (mascotTipTimer !== null) {
    clearTimeout(mascotTipTimer)
    mascotTipTimer = null
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

/* ===== Welcome Banner ===== */
.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  border-radius: 10px;
  margin-bottom: 14px;
  border: 1px solid rgba(91, 141, 239, 0.1);
}

.welcome-content {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.welcome-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.today-text {
  font-size: 12px;
  color: #888;
}

.welcome-tags {
  display: flex;
  gap: 6px;
}

/* ===== KPI Cards ===== */
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--kpi-color) 12%, white);
  color: var(--kpi-color);
  flex-shrink: 0;
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.kpi-label {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

.kpi-trend {
  font-size: 12px;
  font-weight: 600;
}

.trend-up { color: #67c23a; }
.trend-down { color: #f56c6c; }

/* ===== Analytics Row ===== */
.analytics-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.analytics-left, .analytics-right {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

.analytics-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.chart-half {
  min-width: 0;
}

.chart-full {
  width: 100%;
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

.section-link {
  margin-left: auto;
  font-size: 11px;
}

.chart-container {
  width: 100%;
  height: 160px;
}

.chart-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 6px 0;
}

/* ===== AI Analysis ===== */
.ai-analysis-section {
  margin-top: 6px;
  padding-top: 6px;
}

.analysis-placeholder {
  text-align: center;
  padding: 12px 8px;
  color: #888;
}

.analysis-placeholder p {
  margin: 0 0 8px 0;
  font-size: 12px;
}

.analysis-loading {
  text-align: center;
  padding: 12px 8px;
}

.loading-icon {
  font-size: 20px;
  color: #5b8def;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.analysis-content {
  font-size: 12px;
  line-height: 1.5;
  color: #555;
}

.analysis-text {
  white-space: pre-wrap;
  margin-bottom: 10px;
  max-height: 160px;
  overflow-y: auto;
}

/* ===== Schedule Row ===== */
.schedule-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.schedule-section, .announcements-section {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

/* ===== Calendar ===== */
.calendar-wrapper {
  margin-bottom: 10px;
}

.cal-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 10px;
}

.cal-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  min-width: 80px;
  text-align: center;
}

.cal-table {
  width: 100%;
  border-collapse: collapse;
}

.cal-table th {
  font-size: 11px;
  color: #999;
  font-weight: 500;
  padding: 4px 0;
  text-align: center;
}

.cal-table td {
  text-align: center;
  padding: 3px 0;
  cursor: pointer;
  border-radius: 6px;
  height: 32px;
}

.cal-table td:hover {
  background: rgba(91,141,239,0.06);
}

.cal-other { opacity: 0.25; pointer-events: none; }
.cal-past { opacity: 0.4; cursor: default; }
.cal-past:hover { background: transparent !important; }
.cal-past .cal-day-num { color: #ccc; }

.cal-today .cal-day-num {
  background: #5b8def;
  color: #fff;
  display: inline-block;
  width: 22px;
  height: 22px;
  line-height: 22px;
  border-radius: 50%;
  font-weight: 600;
}

.cal-day-num { font-size: 12px; font-weight: 500; }

.cal-dots {
  display: flex;
  justify-content: center;
  gap: 2px;
  min-height: 5px;
  margin-top: 1px;
}

.dot-leave {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #f56c6c;
  display: inline-block;
}

.dot-schedule {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #67c23a;
  display: inline-block;
}

.cal-legend {
  font-size: 10px;
  color: #999;
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.cal-legend span {
  display: flex;
  align-items: center;
  gap: 3px;
}

/* ===== Upcoming Section ===== */
.upcoming-section {
  border-top: 1px solid #f0f0f0;
  padding-top: 10px;
}

.reminder-title {
  font-size: 12px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}

.reminder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.reminder-date {
  font-size: 11px;
  font-weight: 600;
  color: #5b8def;
  background: #f0f7ff;
  padding: 1px 6px;
  border-radius: 6px;
  flex-shrink: 0;
}

.reminder-content {
  flex: 1;
  font-size: 12px;
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Announcements ===== */
.announcement-tabs {
  height: 100%;
}

.tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.announcement-list {
  min-height: 140px;
}

.announcement-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-content {
  flex: 1;
  min-width: 0;
}

.announcement-title {
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.announcement-date {
  font-size: 11px;
  color: #999;
  margin-top: 1px;
}

.attach-link {
  text-decoration: none;
  font-size: 13px;
}

.campus-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
  text-decoration: none;
}

.campus-item:last-child {
  border-bottom: none;
}

.campus-item:hover {
  background: #f8f9ff;
}

.campus-title {
  font-size: 13px;
  color: #333;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 10px;
}

.campus-date {
  font-size: 11px;
  color: #999;
  flex-shrink: 0;
}

.view-all-btn {
  margin-top: 6px;
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

/* ===== AI Floating Button ===== */
.ai-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.ai-float:hover { transform: scale(1.1); }

.ai-mascot {
  width: 48px;
  height: 48px;
  object-fit: contain;
  animation: mascot-float 2s ease-in-out infinite;
}

@keyframes mascot-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.ai-label {
  margin-top: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #5b8def;
  background: rgba(255,255,255,0.9);
  padding: 1px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08);
}

/* 移动端头部 */
.teacher-header {
  background: linear-gradient(135deg, #1d4ed8, #2563eb, #3b82f6);
  padding: 16px 14px 32px;
  color: #fff;
  position: relative;
  overflow: visible;
  margin-bottom: -16px;
  border-radius: 0 0 16px 16px;
}

/* 渐隐尾部 */
.teacher-header::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 32px;
  background: linear-gradient(to bottom, transparent, #f5f7fa);
  border-radius: 0 0 16px 16px;
  pointer-events: none;
}
.teacher-header .header-bg-deco {
  position: absolute; top: -30px; right: -30px;
  width: 120px; height: 120px; border-radius: 50%;
  background: rgba(255,255,255,0.08); pointer-events: none;
}
.teacher-header .header-main {
  display: flex; align-items: center; justify-content: space-between;
  position: relative; z-index: 1;
}
.teacher-header .header-greeting { flex: 1; }
.teacher-header .greeting-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; background: rgba(255,255,255,0.18);
  padding: 3px 10px; border-radius: 20px; margin-bottom: 8px;
}
.teacher-header .badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #67e8f9; animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%,100% { opacity:1; transform:scale(1); }
  50% { opacity:0.5; transform:scale(0.7); }
}
.teacher-header .greeting-text {
  font-size: 18px; font-weight: 700; margin-bottom: 4px;
}
.teacher-header .greeting-sub {
  display: flex; gap: 6px; font-size: 13px; opacity: 0.9;
}
.teacher-header .header-mascot {
  width: 64px; height: 64px; object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.2));
  margin-left: 12px; flex-shrink: 0;
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

.mobile-today-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.today-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.today-item:last-child {
  border-bottom: none;
}

.today-link {
  text-decoration: none;
  color: inherit;
}

.today-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-leave { background: #e6a23c; }
.dot-schedule { background: #409eff; }
.dot-announcement { background: #67c23a; }
.dot-campus { background: #909399; }

.today-info {
  flex: 1;
  min-width: 0;
}

.today-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-meta {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.schedule-add-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 1024px) {
  .analytics-row {
    grid-template-columns: 1fr;
  }
  
  .schedule-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .home-dashboard {
    padding: 0 8px 12px;
  }

  .teacher-header {
    margin-left: -8px;
    margin-right: -8px;
    width: calc(100% + 16px);
  }

  .welcome-banner {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 14px;
  }

  .welcome-content {
    flex-direction: column;
    gap: 2px;
  }

  .welcome-title {
    font-size: 15px;
  }

  .welcome-tags {
    flex-wrap: wrap;
  }

  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    position: relative;
    z-index: 1;
  }

  .kpi-card {
    padding: 10px;
  }

  .kpi-icon {
    width: 36px;
    height: 36px;
  }

  .kpi-value {
    font-size: 18px;
  }

  .kpi-label {
    font-size: 11px;
  }

  .analytics-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .analytics-left, .analytics-right {
    padding: 10px;
  }

  .chart-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .chart-container {
    height: 200px;
  }

  .schedule-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .section-title {
    font-size: 13px;
  }

  .ai-float {
    display: none;
  }

  /* ---- 添加日程子页面 ---- */
  .schedule-form-card {
    background: #fff;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }
  .form-section {
    margin-bottom: 20px;
  }
  .form-label {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }
  .form-label .el-icon {
    font-size: 18px;
  }
  :deep(.el-date-editor) {
    width: 100% !important;
  }
  :deep(.el-date-editor .el-input__wrapper) {
    border-radius: 12px;
    box-shadow: 0 0 0 1px #e5e7eb;
  }
  :deep(.el-date-editor .el-input__wrapper:hover) {
    box-shadow: 0 0 0 1px #667eea;
  }
  :deep(.el-textarea__inner) {
    border-radius: 12px;
    box-shadow: 0 0 0 1px #e5e7eb !important;
    font-size: 14px;
    line-height: 1.6;
    padding: 12px 16px;
  }
  :deep(.el-textarea__inner:focus) {
    box-shadow: 0 0 0 1px #667eea !important;
  }
  .schedule-submit-btn {
    width: 100%;
    height: 48px;
    border-radius: 12px;
    border: none;
    background: #e5e7eb;
    color: #9ca3af;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 4px;
  }
  .schedule-submit-btn.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #fff;
    box-shadow: 0 6px 20px rgba(102,126,234,0.4);
    transform: translateY(-1px);
  }
  .schedule-submit-btn:disabled {
    cursor: not-allowed;
  }

  .form-urgency-options {
    display: flex;
    gap: 8px;
  }
  .form-urgency-opt {
    flex: 1;
    height: 38px;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    background: #fff;
    color: #6b7280;
    font-size: 13px;
    cursor: pointer;
  }
  .form-urgency-opt.active {
    border-color: #667eea;
    background: #eef1ff;
    color: #5b5bd6;
    font-weight: 600;
  }
  .form-urgency-opt.active.important {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #b45309;
  }
  .form-urgency-opt.active.urgent {
    border-color: #ef4444;
    background: #fef2f2;
    color: #dc2626;
  }

  .schedule-upcoming-card {
    background: #fff;
    border-radius: 16px;
    padding: 16px;
    margin-top: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }
  .upcoming-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }
  .upcoming-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .upcoming-title {
    font-size: 15px;
    font-weight: 600;
    color: #374151;
  }
  .upcoming-count {
    margin-left: auto;
    font-size: 12px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 2px 10px;
    border-radius: 10px;
  }
  .upcoming-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px 0;
    gap: 10px;
  }
  .upcoming-empty span {
    font-size: 13px;
    color: #9ca3af;
  }
  .upcoming-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .upcoming-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: #f9fafb;
    border-radius: 12px;
  }
  .upcoming-item:active {
    background: #f3f4f6;
  }
  .upcoming-date {
    flex-shrink: 0;
    width: 48px;
    text-align: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
    padding: 8px 4px;
  }
  .upcoming-day {
    display: block;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }
  .upcoming-month {
    display: block;
    font-size: 10px;
    color: rgba(255,255,255,0.8);
    margin-top: 2px;
  }
  .upcoming-info {
    flex: 1;
    min-width: 0;
  }
  .upcoming-text {
    font-size: 14px;
    color: #374151;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .upcoming-delete {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: none;
    background: #fef2f2;
    color: #ef4444;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .upcoming-delete:active {
    background: #fee2e2;
    transform: scale(0.95);
  }

  /* ---- 任务管理子页面（飞书风格） ---- */
  .task-page {
    padding: 0 !important;
    background: #f5f6f8;
  }
  .task-page .sub-page-body {
    padding: 0;
  }

  /* 校园背景头部 */
  .task-hero {
    position: relative;
    height: 180px;
    flex-shrink: 0;
    overflow: hidden;
  }
  .task-hero-bg {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .task-hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.55) 100%);
  }
  .task-hero-top {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
  }
  .task-hero-back {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: none;
    background: rgba(255,255,255,0.2);
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    backdrop-filter: blur(4px);
  }
  .task-hero-title {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
  }
  .task-hero-center {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -60%);
    text-align: center;
    cursor: pointer;
  }
  .task-hero-date {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    line-height: 1.2;
    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }
  .task-hero-week {
    font-size: 13px;
    color: rgba(255,255,255,0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    margin-top: 4px;
  }
  .task-hero-today {
    background: rgba(255,255,255,0.25);
    padding: 1px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
  }
  .task-hero-hint {
    font-size: 11px;
    color: rgba(255,255,255,0.6);
    margin-top: 6px;
  }

  /* 统计条 */
  .task-hero-stats {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px 16px;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(8px);
  }
  .hero-stat {
    flex: 1;
    text-align: center;
  }
  .hero-stat-num {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    display: block;
    line-height: 1;
  }
  .hero-stat-green { color: #86efac; }
  .hero-stat-amber { color: #fcd34d; }
  .hero-stat-label {
    font-size: 10px;
    color: rgba(255,255,255,0.75);
    margin-top: 3px;
    display: block;
  }
  .hero-stat-divider {
    width: 1px;
    height: 20px;
    background: rgba(255,255,255,0.2);
  }

  /* 日期弹窗（日历式） */
  .cal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
  }
  .cal-popup {
    padding: 12px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    width: 280px;
    animation: cal-pop-in 0.2s ease;
  }
  @keyframes cal-pop-in {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }
  .cal-popup-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  .cal-nav-btn {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    border: none;
    background: #f3f4f6;
    color: #374151;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
  }
  .cal-nav-btn:active {
    background: #e5e7eb;
    transform: scale(0.95);
  }
  .cal-nav-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    min-width: 90px;
    text-align: center;
  }
  .cal-week-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    text-align: center;
    margin-bottom: 2px;
  }
  .cal-week-header span {
    font-size: 10px;
    color: #9ca3af;
    font-weight: 500;
    padding: 2px 0;
  }
  .cal-weekend {
    color: #ef4444 !important;
  }
  .cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 1px;
  }
  .cal-cell {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 30px;
    border-radius: 6px;
    cursor: pointer;
  }
  .cal-cell:active {
    transform: scale(0.92);
  }
  .cal-num {
    font-size: 12px;
    color: #374151;
    line-height: 1;
    font-weight: 500;
  }
  .cal-other .cal-num {
    color: #d1d5db;
    font-weight: 400;
  }
  .cal-today {
    background: #eff6ff;
  }
  .cal-today .cal-num {
    color: #3b82f6;
    font-weight: 700;
  }
  .cal-selected {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3);
  }
  .cal-selected .cal-num {
    color: #fff !important;
    font-weight: 700;
  }
  .cal-task-dot {
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: #f59e0b;
    margin-top: 1px;
  }
  .cal-selected .cal-task-dot {
    background: rgba(255,255,255,0.8);
  }

  .cal-day-plan {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #f3f4f6;
  }
  .cal-day-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .cal-day-title {
    font-size: 12px;
    font-weight: 600;
    color: #1f2937;
  }
  .cal-day-count {
    font-size: 10px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 1px 6px;
    border-radius: 8px;
  }
  .cal-day-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-height: 80px;
    overflow-y: auto;
  }
  .cal-day-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #374151;
    padding: 4px 6px;
    background: #f9fafb;
    border-radius: 6px;
  }
  .cal-day-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .cal-day-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 添加任务按钮 */
  .cal-add-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    margin-top: 8px;
    padding: 6px;
    border-radius: 6px;
    border: 1px dashed #d1d5db;
    cursor: pointer;
    font-size: 11px;
    color: #6b7280;
  }
  .cal-add-btn:active {
    border-color: #3b82f6;
    color: #3b82f6;
    background: #eff6ff;
  }

  /* 添加任务表单 */
  .cal-add-form {
    margin-top: 8px;
  }
  .cal-form-input {
    width: 100%;
    height: 30px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 0 8px;
    font-size: 12px;
    outline: none;
    box-sizing: border-box;
  }
  .cal-form-input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.1);
  }
  .cal-form-input::placeholder {
    color: #c0c4cc;
  }
  .cal-form-urgency {
    display: flex;
    gap: 6px;
    margin-top: 6px;
  }
  .cal-urgency-opt {
    flex: 1;
    height: 24px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background: #fff;
    color: #6b7280;
    font-size: 10px;
    cursor: pointer;
  }
  .cal-urgency-opt.active {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #2563eb;
  }
  .cal-urgency-opt.active.important {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #b45309;
  }
  .cal-urgency-opt.active.urgent {
    border-color: #ef4444;
    background: #fef2f2;
    color: #dc2626;
  }
  .cal-form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    margin-top: 6px;
  }
  .cal-form-cancel {
    height: 26px;
    padding: 0 10px;
    border-radius: 6px;
    border: none;
    background: #f3f4f6;
    color: #374151;
    font-size: 11px;
    cursor: pointer;
  }
  .cal-form-cancel:active {
    background: #e5e7eb;
  }
  .cal-form-submit {
    height: 26px;
    padding: 0 12px;
    border-radius: 6px;
    border: none;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: #fff;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(59,130,246,0.3);
  }
  .cal-form-submit:active {
    transform: scale(0.97);
  }
  .cal-form-submit:disabled {
    background: #e5e7eb;
    color: #9ca3af;
    box-shadow: none;
    cursor: not-allowed;
  }

  /* 快速添加：加号悬浮按钮（固定在底部中央） */
  .task-quick-add-fab {
    position: fixed;
    bottom: 76px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 102;
  }
  .quick-add-fab {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: none;
    background: #fff;
    color: #9ca3af;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,0.14);
  }
  .quick-add-fab:active {
    transform: scale(0.95);
    box-shadow: 0 2px 8px rgba(0,0,0,0.14);
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

  /* 任务列表区域 */
  .task-body {
    padding: 0 12px 80px;
  }
  /* 移动端首页顶部逾期提醒条 */
  .overdue-home-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 10px;
    padding: 9px 12px;
    border-radius: 10px;
    background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
    color: #fff;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: 0 2px 10px rgba(220, 38, 38, 0.35);
  }
  .overdue-home-bar span {
    flex: 1;
  }
  .overdue-home-arrow {
    opacity: 0.8;
  }
  .task-section {
    margin-bottom: 14px;
  }
  .task-section-head {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 4px 6px;
  }
  .task-section-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .task-section-title {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
  }
  .task-section-badge {
    margin-left: auto;
    font-size: 10px;
    color: #9ca3af;
    background: #f3f4f6;
    padding: 1px 8px;
    border-radius: 10px;
  }

  /* 任务卡片（飞书风格） */
  .task-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: #fff;
    border-radius: 10px;
    margin-bottom: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  /* 未完成任务：红色系 */
  .task-card.task-pending {
    background: #fff7f7;
    border-left: 3px solid #ef4444;
  }
  /* 已完成任务：绿色系 */
  .task-card.task-completed {
    background: #f0fdf4;
    border-left: 3px solid #10b981;
  }
  .task-card.task-completed .task-card-title {
    text-decoration: line-through;
    color: #6b7280;
  }
  /* 紧急未完成：红色强调置顶标记 */
  .task-card.task-urgent {
    background: #fef2f2;
    border-left: 3px solid #dc2626;
    box-shadow: 0 1px 6px rgba(239, 68, 68, 0.18);
  }
  .task-card-tags {
    display: flex;
    gap: 4px;
    margin-top: 2px;
  }
  .ur-badge {
    font-size: 10px;
    line-height: 1;
    padding: 2px 6px;
    border-radius: 8px;
    font-weight: 500;
  }
  .ur-urgent { background: #dc2626; color: #fff; }
  .ur-important { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
  .ur-overdue { background: #f3f4f6; color: #6b7280; border: 1px solid #e5e7eb; }
  .leave-card {
    background: #fffbeb !important;
    border-left: 3px solid #f59e0b !important;
  }
  .task-card-check {
    flex-shrink: 0;
    cursor: pointer;
  }
  .tc-check {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 1.5px solid #d1d5db;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
  }
  .tc-check.checked {
    background: #10b981;
    border-color: #10b981;
    color: #fff;
  }
  .tc-check .el-icon {
    font-size: 11px;
  }
  .task-card-body {
    flex: 1;
    min-width: 0;
  }
  .task-card-title {
    font-size: 13px;
    color: #1f2937;
    line-height: 1.4;
  }
  .task-done .task-card-title {
    text-decoration: line-through;
    color: #9ca3af;
  }
  .today-done {
    text-decoration: line-through;
    color: #9ca3af;
  }
  .task-card-sub {
    font-size: 11px;
    color: #9ca3af;
    margin-top: 1px;
  }
  .task-card-btn {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: 6px;
    border: none;
    background: #f0f5ff;
    color: #3b82f6;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
  }
  .task-card-del {
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: #d1d5db;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
  }
  .task-card-del:active {
    background: #fef2f2;
    color: #ef4444;
  }

  /* 空状态 */
  .task-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
  }
  .task-empty-mascot {
    width: 72px;
    height: 72px;
    object-fit: contain;
    opacity: 0.5;
    margin-bottom: 12px;
  }
  .task-empty-text {
    font-size: 14px;
    font-weight: 500;
    color: #6b7280;
    margin-bottom: 4px;
  }
  .task-empty-sub {
    font-size: 12px;
    color: #9ca3af;
  }

  /* ---- 数据分析子页面：悬浮桌宠 + 分析弹窗 ---- */
  .mascot-pet {
    position: fixed;
    right: 16px;
    bottom: 84px;
    z-index: 130;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    -webkit-tap-highlight-color: transparent;
  }
  .mascot-pet-img {
    width: 76px;
    height: 76px;
    object-fit: contain;
    filter: drop-shadow(0 6px 14px rgba(91, 141, 239, 0.45));
  }
  .mascot-pet:active .mascot-pet-img { transform: scale(0.92); }
  @keyframes mascot-pet-bounce {
    0%, 100% { transform: translateY(0) scale(1); }
    30% { transform: translateY(-8px) scale(1.04); }
    55% { transform: translateY(0) scale(1); }
    75% { transform: translateY(-4px) scale(1.02); }
  }
  .mascot-tip-bubble {
    position: relative;
    background: #fff;
    border: 1px solid #e9d5ff;
    border-radius: 12px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
    padding: 8px 10px 8px 12px;
    margin-bottom: 10px;
    margin-right: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #4c1d95;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .mascot-tip-bubble::after {
    content: '';
    position: absolute;
    right: 22px;
    bottom: -6px;
    width: 12px;
    height: 12px;
    background: #fff;
    border-right: 1px solid #e9d5ff;
    border-bottom: 1px solid #e9d5ff;
    transform: rotate(45deg);
  }
  .mascot-tip-text { white-space: nowrap; }
  .mascot-tip-close {
    display: inline-flex;
    width: 16px; height: 16px;
    align-items: center; justify-content: center;
    border-radius: 50%;
    background: #f3e8ff;
    color: #7c3aed;
    font-size: 10px;
    flex-shrink: 0;
  }
  .tip-pop-enter-active,
  .tip-pop-leave-active {
    transition: all 0.25s ease !important;
  }
  .tip-pop-enter-from,
  .tip-pop-leave-to {
    opacity: 0;
    transform: translateY(8px) scale(0.92);
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

  .charts-grid {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .chart-card { border-radius: 14px; }
  .chart-card-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 8px;
  }

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
