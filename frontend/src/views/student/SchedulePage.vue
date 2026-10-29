<template>
  <div ref="pageEl" class="schedule-page" :class="{ 'has-subpage': isMobile && activeTab !== 'home' }"
      @touchstart.passive="pull.onStart"
      @touchmove="pull.onMove"
      @touchend="pull.onEnd"
      @touchcancel="pull.onCancel"
    >
    <!-- 移动端下拉刷新：吉祥物指示器（与教师端首页 / 学生工作台共用同一模块） -->
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <!-- ===== 移动端：驾驶舱主页（成长总览 + 内置学业功能区，子页面入口） =====
         主页**刻意放在 <Transition> 之外**：这样它永远收不到 enter/leave 类，
         任何时刻都不会有动画 —— 进子页时被子页盖住，返回时子页滑走即露出主页。
         （此前主页与子页是同一个 <Transition> 的两个互斥分支，导致「返回主页」时
         主页作为进场页从右侧滑入，看起来像「主页面有滑出动画」，已按此结构消除。）
         桌面端不渲染本块（!isMobile），由下面的 .content-row 承载两栏布局。 -->
    <!-- 主页固定 Head（v4.1）：与子页同规格——48px fixed + 同底色 + 滚动阴影线，
         保证「学业中心」标题始终在视口顶部；滚动区由 .dashboard-home 让出高度 -->
    <div v-if="isMobile && activeTab === 'home'" class="home-bar">
      <div class="sp-title-wrap">
        <span class="sp-title">学业中心</span>
      </div>
    </div>
    <div v-if="isMobile && activeTab === 'home'" class="dashboard-home">
      <GrowthDashboard
        ref="dashboardRef"
        :courses="courses"
        :current-week="currentWeek"
        :period-times="periodTimes"
        :is-holiday="isHoliday"
        :courses-loading="!scheduleReady"
        @open="openSubPage"
      />
    </div>
    <!-- ===== 内容区：移动端子页面 / 桌面端两栏布局 =====
         只有本块参与过渡（覆盖式：从右滑入 / 原路向右滑出），主页在 Transition 之外不动。 -->
    <Transition :name="subpageTransitionName" :duration="subpageTransitionName ? 320 : undefined">
    <div v-if="!isMobile || activeTab !== 'home'" key="content" class="content-row" @scroll.passive="onSubpageScroll">
      <div class="content-main">
        <!-- ===== 移动端子页面：固定顶栏（Head） =====
             三个子页共用同一个顶栏，高度恒为 48px 且 sticky 吸顶 —— 滚动时不再消失。
             旧版是一个 38px 的圆角卡片，作为普通流节点躺在滚动内容里，滚 600px 后
             top 变成 -592（整条滚出视口）。现在 .content-row 仍是滚动容器，
             顶栏改为 sticky 后贴在它的顶部；内容区自带 8px 上下留白也一并交给滚动区。
             左右两个 .sp-side 等宽，保证标题真正居中（而不是被右侧占位挤偏）。
             进入页面后随滚动收起副标题，48px 不变 —— 高度恒定是无障碍要求（避免布局跳动）。 -->
        <div v-if="isMobile" class="subpage-bar" :class="{ 'is-scrolled': subpageScrolled }">
          <div class="sp-side sp-left">
            <button class="sp-back" type="button" aria-label="返回主页" @click="backToHome">
              <el-icon :size="19"><ArrowLeft /></el-icon>
            </button>
          </div>
          <div class="sp-title-wrap">
            <span v-if="subPageAccent" class="sp-dot" :style="{ background: subPageAccent }" aria-hidden="true"></span>
            <span class="sp-txt">
              <span class="sp-title">{{ subPageTitle }}</span>
              <span v-if="subPageSub" class="sp-sub">{{ subPageSub }}</span>
            </span>
          </div>
          <div class="sp-side sp-right"></div>
        </div>
        <Transition name="tab-fade" mode="out-in">
        <div v-if="activeTab === 'schedule'" key="schedule" class="schedule-view">
          <div v-if="!scheduleReady" class="loading-box">
            <el-icon class="is-loading" :size="20"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <template v-if="scheduleReady">
            <!-- 教学安排 + 本周课表 -->
            <div class="content-card" style="margin-bottom:20px;position:relative">
              <div class="schedule-toolbar">
                <span class="schedule-toolbar-title">教学安排</span>
                <div class="week-nav">
                  <button class="week-nav-btn" @click="goPrevWeek" :disabled="currentWeek <= 1">‹</button>
                  <span class="week-label">第{{ currentWeek }}周</span>
                  <button class="week-nav-btn" @click="goNextWeek">›</button>
                </div>
                <el-button v-if="showResetBtn" size="small" text type="primary" class="reset-week-btn" @click="resetWeek">回到本周</el-button>
                <el-select v-model="selectedScheduleSem" size="small" class="semester-tag semester-select" popper-class="semester-select-popper" fit-input-width>
                  <el-option v-for="s in scheduleSemesterOptions" :key="s.value" :label="isMobile ? semesterLabelCompact(s.value) : s.label" :value="s.value" />
                </el-select>
              </div>
              <div style="border-bottom:1px solid #ebeef5;margin:0"></div>
              <div class="card-body" style="padding:0">
                <div v-if="isHoliday" class="holiday-box">
                  <div class="holiday-icon">🎉</div>
                  <div class="holiday-title">当前为假期，暂无课程安排</div>
                  <div class="holiday-sub">假期愉快，注意劳逸结合哦</div>
                </div>
                <Transition v-else :name="'slide-' + slideDir" mode="out-in">
                  <div :key="currentWeek">
                    <table class="schedule-table">
                      <thead>
                        <tr>
                          <th>节次</th>
                          <th v-for="d in visibleDays" :key="d" :class="{ 'th-today': isTodayCol(d) }">{{ d }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="row in courseGrid" :key="row.period">
                          <td class="period-cell">
                            <div class="period-name">第{{ row.period }}节</div>
                            <div class="period-time">{{ periodTimeLabel(row.period) }}</div>
                          </td>
                          <template v-for="(cell, ci) in row.cells" :key="ci">
                            <td v-if="cell.empty" :class="{ 'td-today': isTodayCol(cell.day) }"></td>
                            <td v-else :rowspan="cell.rowspan" :class="['cell-filled', { 'td-today': isTodayCol(cell.day) }]">
                              <div class="schedule-course" :class="{ 'course-today': isTodayCol(cell.day) }" :style="{ borderLeftColor: courseColor(cell.course.name).slice(0,7), background: courseCellBg(cell.course.name, cell.day) }"
                                @mouseenter="onCourseEnter(cell.course, $event)" @mouseleave="onCourseLeave" @click="onCourseClick(cell.course, $event)">
                                <div class="course-name">{{ cell.course.name }}</div>
                                <div class="course-teacher">{{ cell.course.teacher }}</div>
                                <div class="course-loc">{{ cell.course.location }}</div>
                              </div>
                            </td>
                          </template>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- 课程悬浮详情 -->
            <Teleport to="body">
              <Transition name="course-tip">
                <div v-if="courseTipVisible && hoverCourse" class="course-tip-layer">
                  <div class="course-tip"
                    :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px', borderLeftColor: tipColor, background: tipBg }"
                    @click.stop @mouseenter="onTipEnter" @mouseleave="onTipLeave">
                    <div class="ct-name">{{ hoverCourse.name }}</div>
                    <div class="ct-detail"><span class="ct-label">教师</span>{{ hoverCourse.teacher }}</div>
                    <div class="ct-detail"><span class="ct-label">教室</span>{{ hoverCourse.location }}</div>
                    <div class="ct-detail"><span class="ct-label">时间</span>{{ dayName(hoverCourse.day_of_week) }} 第{{ hoverCourse.start_period }}-{{ hoverCourse.end_period }}节</div>
                    <div class="ct-detail"><span class="ct-label">周次</span>第{{ hoverCourse.week_start }}-{{ hoverCourse.week_end }}周</div>
                    <div class="ct-detail"><span class="ct-label">学分</span>{{ hoverCourse.credit ?? '--' }}</div>
                    <div class="ct-detail"><span class="ct-label">学期</span>{{ formatSemester(hoverCourse.semester) }}</div>
                  </div>
                </div>
              </Transition>
            </Teleport>
          </template>
        </div>

        <!-- ===== 成绩分析 ===== -->
        <div v-else-if="activeTab === 'grades'" key="grades" class="grades-view">
          <!-- 成绩数据按需加载：首次进入本页签时才请求，先给一次加载态，避免闪出「暂无数据」 -->
          <div v-if="!gradesReady" class="loading-box">
            <el-icon class="is-loading" :size="20"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <template v-else>
          <!-- v5：结论优先 hero（仿 Apple Health 高亮摘要），图表压缩成辅助 -->
          <div class="gr-hero">
            <p class="gr-hero-big">绩点 <b>{{ gradeAnalysis.stats.avg_gpa || '--' }}</b> · {{ gradeAnalysis.stats.gpa_rank ? `排名第 ${gradeAnalysis.stats.gpa_rank}` : '暂无排名' }}<span class="gr-hero-of"> / {{ gradeAnalysis.stats.total_students }} 人</span></p>
            <p class="gr-hero-sub">均分 {{ gradeAnalysis.stats.avg_score || '--' }} · 总学分 {{ gradeAnalysis.stats.total_credits || '--' }} · 数据详见下方明细</p>
          </div>
          <!-- 核心指标 -->
          <div class="grade-stats-row">
            <div class="grade-stat-card">
              <div class="stat-icon" style="background:rgba(64,158,255,.1);color:#409eff"><el-icon :size="20"><Trophy /></el-icon></div>
              <div class="stat-info">
                <div class="stat-value">{{ gradeAnalysis.stats.gpa_rank ? `第${gradeAnalysis.stats.gpa_rank}名` : '--' }}</div>
                <div class="stat-label">绩点排名 / 共{{ gradeAnalysis.stats.total_students }}人</div>
              </div>
            </div>
            <div class="grade-stat-card stat-clickable" @click="openFormula('gpa')">
              <div class="stat-icon" style="background:rgba(103,194,58,.1);color:#67c23a"><el-icon :size="20"><TrendCharts /></el-icon></div>
              <div class="stat-info"><div class="stat-value">{{ gradeAnalysis.stats.avg_gpa || '--' }}</div><div class="stat-label">平均绩点 <el-icon class="stat-help"><InfoFilled /></el-icon></div></div>
            </div>
            <div class="grade-stat-card stat-clickable" @click="openFormula('score')">
              <div class="stat-icon" style="background:rgba(230,162,60,.1);color:#e6a23c"><el-icon :size="20"><Star /></el-icon></div>
              <div class="stat-info"><div class="stat-value">{{ gradeAnalysis.stats.avg_score || '--' }}</div><div class="stat-label">平均分 <el-icon class="stat-help"><InfoFilled /></el-icon></div></div>
            </div>
            <div class="grade-stat-card">
              <div class="stat-icon" style="background:rgba(124,92,255,.1);color:#7c5cff"><el-icon :size="20"><Collection /></el-icon></div>
              <div class="stat-info"><div class="stat-value">{{ gradeAnalysis.stats.total_credits || '--' }}</div><div class="stat-label">总学分</div></div>
            </div>
          </div>

          <!-- 成绩趋势 -->
          <div class="analytics-card">
            <div class="analytics-head">
              <span class="head-bar"></span>
              <span class="head-title">成绩趋势</span>
              <span class="head-sub">学期绩点走势与分数段分布</span>
            </div>
            <div class="analytics-body duo">
              <div class="panel" style="flex:6">
                <div class="panel-title"><el-icon><TrendCharts /></el-icon>学期绩点趋势</div>
                <v-chart v-if="gradeAnalysis.semester_gpa.length" :option="semGpaOption" class="chart" autoresize />
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
              <div class="panel-divider"></div>
              <div class="panel" style="flex:5">
                <div class="panel-title"><el-icon><Histogram /></el-icon>分数段分布</div>
                <v-chart v-if="hasScores" :option="distOption" class="chart" autoresize />
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>
          </div>

          <!-- 课程画像（移动端默认折叠，点击标题行展开，带高度过渡动画） -->
          <div class="analytics-card course-profile-card" :class="{ 'is-open': courseProfileOpen }">
            <div class="analytics-head" @click="toggleCourseProfile">
              <span class="head-bar"></span>
              <span class="head-title">课程画像</span>
              <span class="head-sub">课程类型表现与优劣势科目</span>
              <el-icon class="head-toggle"><ArrowDown /></el-icon>
            </div>
            <el-collapse-transition>
              <div v-if="!isMobile || courseProfileOpen" class="analytics-body duo">
                <div class="panel" style="flex:5">
                  <div class="panel-title"><el-icon><DataAnalysis /></el-icon>课程类型均分</div>
                  <v-chart v-if="gradeAnalysis.course_type_stats.length" :option="typeOption" class="chart" autoresize />
                  <el-empty v-else description="暂无数据" :image-size="48" />
                </div>
                <div class="panel-divider"></div>
                <div class="panel" style="flex:6">
                  <div class="panel-title"><el-icon><Trophy /></el-icon>优势与待提升课程</div>
                  <div class="course-rank-scroll">
                    <div class="cr-group-label good">优势课程</div>
                    <template v-if="gradeAnalysis.top_courses.length">
                      <div v-for="c in gradeAnalysis.top_courses.slice(0, 4)" :key="'t' + c.course_name" class="course-rank-item">
                        <span class="cr-name" :title="c.course_name">{{ c.course_name }}</span>
                        <div class="cr-bar"><div class="cr-bar-inner good" :style="{ width: barWidth(c.score) }"></div></div>
                        <span class="cr-score good">{{ c.score ?? '--' }}</span>
                      </div>
                    </template>
                    <div v-else class="cr-empty">暂无优势课程记录</div>
                    <div class="cr-group-label weak">待提升课程</div>
                    <template v-if="gradeAnalysis.weak_courses.length">
                      <div v-for="c in gradeAnalysis.weak_courses.slice(0, 4)" :key="'w' + c.course_name" class="course-rank-item">
                        <span class="cr-name" :title="c.course_name">{{ c.course_name }}</span>
                        <div class="cr-bar"><div class="cr-bar-inner weak" :style="{ width: barWidth(c.score) }"></div></div>
                        <span class="cr-score weak">{{ c.score ?? '--' }}</span>
                      </div>
                    </template>
                    <div v-else class="cr-empty">太棒了，暂无薄弱课程</div>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <!-- 学期明细 + 右侧栏 -->
          <div class="grades-detail-row">
            <div class="analytics-card detail-card">
              <div class="analytics-head">
                <span class="head-bar"></span>
                <span class="head-title">学期成绩明细</span>
                <span class="head-sub">按学期查看各科成绩</span>
              </div>
              <div class="analytics-body">
                <div class="sem-selector">
                  <el-select v-model="selectedSem" placeholder="选择学期" class="semester-tag semester-select" popper-class="semester-select-popper">
                    <el-option v-for="s in semesters" :key="s" :label="semesterLabel(s)" :value="s" />
                  </el-select>
                  <div v-if="selectedSem" class="sem-stats-inline">
                    <span>{{ semStats[selectedSem]?.count }} 门</span>
                    <span>均分 <b :style="{ color: avgColor(semStats[selectedSem]?.avg) }">{{ semStats[selectedSem]?.avg }}</b></span>
                    <span>均绩 <b>{{ semStats[selectedSem]?.gpa }}</b></span>
                    <span>学分 <b>{{ semStats[selectedSem]?.credits }}</b></span>
                  </div>
                  <a href="https://jwgl.mycc.edu.cn/frame/homes.action?v=32141370228717481160781" target="_blank" class="sem-link-action">
                    <el-icon :size="14"><Link /></el-icon>
                    <span>查询学期 / 下载证明</span>
                    <el-icon :size="12"><ArrowRight /></el-icon>
                  </a>
                </div>
                <div v-if="selectedSem && gradesBySem[selectedSem]?.length" class="grade-grid" ref="gradeGridRef">
                  <div v-for="g in visibleGrades" :key="g.id" class="grade-card" :class="scoreLevel(g.score)">
                    <div class="gc-top">
                      <span class="gc-name">{{ g.course_name }}</span>
                      <span class="gc-score">{{ g.score }}</span>
                    </div>
                    <div class="gc-meta">
                      <span>绩点 {{ g.gpa }}</span>
                      <span>学分 {{ g.credit }}</span>
                    </div>
                  </div>
                  <div class="grade-card grade-card-more" @click="allGradesVisible = true">
                    <div class="gc-top">
                      <span class="gc-name more-text"><el-icon :size="14" class="more-icon"><Grid /></el-icon> 全部课程</span>
                      <span class="gc-score more-arrow"><el-icon :size="12"><ArrowRight /></el-icon></span>
                    </div>
                    <div class="gc-meta"><span>点击查看明细</span></div>
                  </div>
                </div>
                <el-empty v-else description="该学期暂无成绩" :image-size="48" />

                <!-- 全部成绩弹窗 -->
                <el-dialog v-model="allGradesVisible" title="全部成绩明细" width="900px" top="6vh">
                  <div class="grade-grid grade-grid-all">
                    <div v-for="g in gradesBySem[selectedSem]" :key="'a-' + g.id" class="grade-card" :class="scoreLevel(g.score)">
                      <div class="gc-top">
                        <span class="gc-name">{{ g.course_name }}</span>
                        <span class="gc-score">{{ g.score }}</span>
                      </div>
                      <div class="gc-meta">
                        <span>绩点 {{ g.gpa }}</span>
                        <span>学分 {{ g.credit }}</span>
                      </div>
                    </div>
                  </div>
                  <template #footer>
                    <el-button @click="allGradesVisible = false">关闭</el-button>
                  </template>
                </el-dialog>
              </div>
            </div>
            <div class="grades-side-col">
              <div v-if="upcomingExams.length" class="analytics-card side-exam-card">
                <div class="analytics-head">
                  <span class="head-bar"></span>
                  <span class="head-title">即将考试</span>
                  <span class="head-sub">{{ upcomingExams.length }} 场</span>
                </div>
                <div class="analytics-body exam-list">
                  <div v-for="e in upcomingExams.slice(0, 6)" :key="e.id" class="exam-card">
                    <div class="ec-left">
                      <div class="ec-date">{{ formatDate(e.exam_date) }}</div>
                      <div class="ec-time">{{ e.start_time?.slice(0, 5) }} - {{ e.end_time?.slice(0, 5) }}</div>
                    </div>
                    <div class="ec-body">
                      <div class="ec-name">{{ e.course_name }}</div>
                      <div class="ec-location"><el-icon><Location /></el-icon> {{ e.location }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <!-- AI 学情智能分析（侧栏） -->
              <div class="analytics-card side-ai-card">
                <div class="analytics-head">
                  <span class="head-bar"></span>
                  <span class="head-title">AI 学情分析</span>
                  <span class="head-sub">个性化学习建议</span>
                  <el-button type="primary" size="small" class="head-save" :loading="gradeLoading && !gradeRaw" @click="startAiAnalysis({ stream: true })">
                    <el-icon v-if="!gradeLoading"><MagicStick /></el-icon>
                    {{ gradeLoading && !gradeRaw ? '分析中...' : '重新分析' }}
                  </el-button>
                </div>
                <div class="analytics-body ai-side-body">
                  <div v-if="gradeRaw" class="ai-result-card">
                    <div v-if="gradeLoading && gradeFromCache" class="ai-refresh-bar">
                      <el-icon class="is-loading" :size="14"><Loading /></el-icon>
                      <span>正在更新...</span>
                    </div>
                    <div class="ai-result-content" v-html="gradeHtml"></div>
                  </div>
                  <div v-else-if="gradeLoading" class="ai-loading-card">
                    <div class="ai-loading-header">
                      <el-icon class="is-loading" :size="20"><Loading /></el-icon>
                      <span>AI 正在分析您的学情数据...</span>
                    </div>
                    <div class="ai-loading-skeleton">
                      <div class="skeleton-line" style="width:80%"></div>
                      <div class="skeleton-line" style="width:60%"></div>
                      <div class="skeleton-line" style="width:90%"></div>
                    </div>
                  </div>
                  <div v-else class="ai-placeholder">
                    <el-icon :size="40" color="#ddd"><MagicStick /></el-icon>
                    <p>点击"重新分析"按钮，AI 将为您分析学情数据</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 目标计划 -->
          <div class="analytics-card">
            <div class="analytics-head">
              <span class="head-bar"></span>
              <span class="head-title">目标计划</span>
              <span class="head-sub">设定学期绩点目标并跟踪达成情况</span>
            </div>
            <div class="analytics-body goal-list">
              <!-- 移动端 v6：里程碑阶梯（抄 Duolingo 关卡进度 + Strava 目标）——
                   把「距目标还差多少」拆成 4 级刻度，当前绩点落在哪一级、还差几步一目了然。
                   桌面端仍走下面的表格式 goal-item，结构不动。 -->
              <template v-if="isMobile">
                <div
                  v-for="(sem, idx) in semesters" :key="'gl-' + sem"
                  class="gl-item" :class="{ 'is-current': idx === 0 }"
                >
                  <div class="gl-head">
                    <span class="gl-sem">{{ semesterLabel(sem) }}</span>
                    <span v-if="idx === 0" class="gl-badge">当前学期</span>
                    <span v-else class="gl-badge is-past">{{ glDone(sem) ? '已达成' : '未达成' }}</span>
                  </div>

                  <template v-if="glTarget(sem) != null">
                    <div class="gl-track">
                      <span class="gl-rail" aria-hidden="true"></span>
                      <span class="gl-fill" :style="{ width: glPct(sem) + '%' }" aria-hidden="true"></span>
                      <span class="gl-mark" :style="{ left: glPct(sem) + '%' }" aria-hidden="true"></span>
                      <div
                        v-for="(n, ni) in glNodes(sem)" :key="ni"
                        class="gl-node" :class="'is-' + n.state"
                        :style="{ left: n.pos + '%' }"
                      >
                        <i></i>
                        <b>{{ n.value.toFixed(2) }}</b>
                      </div>
                    </div>
                    <p class="gl-hint" :class="{ 'is-ok': glDone(sem) }">{{ glHint(sem) }}</p>
                    <div v-if="idx === 0" class="gl-edit">
                      <span class="gl-edit-label">调整目标</span>
                      <el-input-number v-model="goalInputs[sem]" :min="0" :max="4" :step="0.1" :precision="2" size="small" controls-position="right" style="width:104px" />
                      <el-button type="primary" size="small" @click="saveGoalForSem(sem)">保存</el-button>
                    </div>
                  </template>

                  <template v-else>
                    <p class="gl-hint">还没有设定目标绩点</p>
                    <div v-if="idx === 0" class="gl-edit">
                      <span class="gl-edit-label">目标绩点</span>
                      <el-input-number v-model="goalInputs[sem]" :min="0" :max="4" :step="0.1" :precision="2" size="small" controls-position="right" style="width:104px" />
                      <el-button type="primary" size="small" @click="saveGoalForSem(sem)">保存</el-button>
                    </div>
                  </template>
                </div>
              </template>
              <template v-else>
              <div v-for="(sem, idx) in semesters" :key="sem" class="goal-item" :class="{ 'is-current': idx === 0 }">
                <div class="goal-item-header">
                  <span class="goal-sem-name">{{ semesterLabel(sem) }}</span>
                  <el-tag v-if="idx === 0" type="success" size="small" effect="light">当前学期</el-tag>
                  <el-tag v-else type="info" size="small" effect="plain">已完成</el-tag>
                </div>
                <div class="goal-item-body">
                  <div class="goal-item-left">
                    <span class="goal-label">目标绩点</span>
                    <template v-if="idx === 0">
                      <div class="goal-input-wrap">
                        <el-input-number v-model="goalInputs[sem]" :min="0" :max="4" :step="0.1" :precision="2" size="small" controls-position="right" style="width:110px" />
                        <el-button type="primary" size="small" @click="saveGoalForSem(sem)" style="margin-left:6px">保存</el-button>
                      </div>
                    </template>
                    <template v-else>
                      <div class="goal-locked"><el-icon><Lock /></el-icon><span>{{ goals[sem] != null ? goals[sem].toFixed(2) : '未设置' }}</span></div>
                    </template>
                  </div>
                  <div class="goal-item-right">
                    <span>实际 <b :style="{ color: avgColor(semStats[sem]?.avg) }">{{ semStats[sem]?.gpa || '--' }}</b></span>
                    <span v-if="goals[sem] != null" class="goal-achieve">
                      <template v-if="parseFloat(semStats[sem]?.gpa || '0') >= goals[sem]">
                        <el-icon color="#67c23a"><CircleCheckFilled /></el-icon> 已达成
                      </template>
                      <template v-else>
                        <el-icon color="#f56c6c"><WarningFilled /></el-icon> 差 {{ (goals[sem] - parseFloat(semStats[sem]?.gpa || '0')).toFixed(2) }}
                      </template>
                    </span>
                  </div>
                </div>
              </div>
              </template>
            </div>
          </div>
          <el-empty v-if="!grades.length && !upcomingExams.length && !gradeAnalysis.semester_gpa.length" description="暂无考试成绩数据" />

          <!-- 移动端：右下角绵小城（点击弹出 AI 学情分析） -->
          <div class="grades-mascot" @click="mascotDialogVisible = true">
            <img :src="siteMascot" :alt="siteName" draggable="false" />
          </div>

          <!-- 移动端：AI 学情分析弹窗 -->
          <el-dialog v-model="mascotDialogVisible" title="AI 学情分析" width="92%" top="6vh" class="mascot-ai-dialog">
            <div class="mascot-ai-head">
              <img :src="siteMascot" :alt="siteName" draggable="false" />
              <div class="mascot-ai-head-text">
                <div class="mascot-ai-title">{{ siteName }}学情报告</div>
                <div class="mascot-ai-sub">个性化学习建议</div>
              </div>
              <el-button type="primary" size="small" :loading="gradeLoading && !gradeRaw" @click="startAiAnalysis({ stream: true })">
                <el-icon v-if="!gradeLoading"><MagicStick /></el-icon>
                {{ gradeRaw ? '重新分析' : '开始分析' }}
              </el-button>
            </div>
            <div class="mascot-ai-body">
              <div v-if="gradeRaw" class="ai-result-card">
                <div v-if="gradeLoading && gradeFromCache" class="ai-refresh-bar">
                  <el-icon class="is-loading" :size="14"><Loading /></el-icon>
                  <span>正在更新...</span>
                </div>
                <div class="ai-result-content" v-html="gradeHtml"></div>
              </div>
              <div v-else-if="gradeLoading" class="ai-loading-card">
                <div class="ai-loading-header">
                  <el-icon class="is-loading" :size="20"><Loading /></el-icon>
                  <span>AI 正在分析您的学情数据...</span>
                </div>
                <div class="ai-loading-skeleton">
                  <div class="skeleton-line" style="width:80%"></div>
                  <div class="skeleton-line" style="width:60%"></div>
                  <div class="skeleton-line" style="width:90%"></div>
                </div>
              </div>
              <div v-else class="ai-placeholder ai-placeholder-small">
                <el-icon :size="32" color="#ddd"><MagicStick /></el-icon>
                <p>点击"开始分析"按钮，AI 将为您分析学情数据</p>
              </div>
            </div>
            <template #footer>
              <el-button @click="mascotDialogVisible = false">关闭</el-button>
            </template>
          </el-dialog>
          </template>

        </div>

        <!-- ===== 成长轨迹 ===== -->
        <div v-else-if="activeTab === 'growth'" key="growth" class="growth-view">
          <!-- 成长数据按需加载：首次进入本页签时才请求 -->
          <div v-if="!growthLoaded" class="loading-box">
            <el-icon class="is-loading" :size="20"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <template v-else>
          <!-- ===== 状态卡（参考 Keep 9.0「数据概览」健康状态卡） =====
               原来这里是一个渐变底大卡 + 92px 渐变圆环 + 吉祥物 + 7 个横排数字，占满整屏。
               现在：一句人话评价 + 一句具体建议 + 一排紧凑数字。色彩只落在评分圆环和
               警示数字上，卡片本身是白底。 -->
          <section class="gv-hero" :class="'tone-' + growthTier.tone">
            <div class="gv-hero-top">
              <div class="gv-score">
                <div class="gv-gauge">
                  <svg viewBox="0 0 60 60" class="gv-gauge-svg" aria-hidden="true">
                    <circle cx="30" cy="30" r="25" fill="none" stroke="#eef0f3" stroke-width="5" />
                    <circle cx="30" cy="30" r="25" fill="none" stroke="currentColor" stroke-width="5"
                      :stroke-dasharray="gaugeLen" :stroke-dashoffset="gaugeOffset" stroke-linecap="round"
                      transform="rotate(-90, 30, 30)" />
                  </svg>
                  <span class="gv-gauge-val">{{ profile?.total_score ?? '--' }}</span>
                </div>
                <div class="gv-score-text">
                  <div class="gv-tier">{{ growthTier.label }}</div>
                  <div class="gv-advice">{{ growthAdvice }}</div>
                </div>
              </div>
              <button class="gv-add" type="button" @click="openDialog">
                <el-icon :size="15"><Plus /></el-icon>
                <span>记一笔</span>
              </button>
            </div>

            <!-- 紧凑数字网格：2 行 × 4 列，替代原来占半屏的 7 个横排大字 -->
            <div class="gv-metrics">
              <div v-for="m in growthMetrics" :key="m.label" class="gv-metric">
                <span class="gv-metric-val">{{ m.value }}</span>
                <span class="gv-metric-label">{{ m.label }}</span>
              </div>
            </div>
          </section>

          <!-- ===== 坚持日历（参考 Duolingo 连续打卡热力图） =====
               只占用约 90px 高度，但能把「我这学期一直在记」这件事变成看得见的东西。 -->
          <section class="gv-card gv-heat">
            <header class="gv-card-head">
              <h3 class="gv-card-title">坚持情况</h3>
              <span class="gv-card-meta" v-if="growthStreak">连续 {{ growthStreak }} 天</span>
            </header>
            <div class="gv-heat-body">
              <div class="gv-heat-grid" role="img" :aria-label="`近 ${growthHeatmap.rangeWeeks} 周共 ${growthHeatmap.totalInRange} 次学习活动，${growthHeatmap.activeDays} 天有记录`">
                <div v-for="(col, ci) in growthHeatmap.weeks" :key="ci" class="gv-heat-week" role="presentation">
                  <span
                    v-for="(cell, di) in col"
                    :key="di"
                    class="gv-heat-cell"
                    :class="[`lv-${cell.level}`, { 'is-today': cell.isToday }]"
                    :title="cell.isFuture ? '' : cell.title"
                  ></span>
                </div>
              </div>
              <div class="gv-heat-foot">
                <span v-if="growthHeatmap.hasAny">近 {{ growthHeatmap.rangeWeeks }} 周 {{ growthHeatmap.totalInRange }} 次 · {{ growthHeatmap.activeDays }} 天</span>
                <span v-else>还没有记录，打卡一次或记一笔就会出现第一个格子</span>
                <div class="gv-heat-legend" aria-hidden="true">
                  <span class="gv-heat-cell lv-0"></span>
                  <span class="gv-heat-cell lv-1"></span>
                  <span class="gv-heat-cell lv-2"></span>
                  <span class="gv-heat-cell lv-3"></span>
                </div>              </div>
            </div>
          </section>

          <!-- ===== 能力画像：小雷达与五维数字**并排**（参考 Keep 上周运动周报） =====
               原来雷达图单独占 280~400px 高的一整块，五维数字根本看不见，用户只能读图猜数值。 -->
          <section class="gv-card">
            <header class="gv-card-head">
              <h3 class="gv-card-title">能力画像</h3>
              <span class="gv-card-meta">满分 100</span>
            </header>
            <div class="gv-dim-body">
              <div class="gv-radar">
                <v-chart v-if="profile?.radar?.length" :option="radarOption" class="gv-radar-chart" autoresize />
                <el-empty v-else description="暂无数据" :image-size="40" />
              </div>
              <div class="gv-dim-list">
                <div
                  v-for="d in (profile?.radar ?? [])"
                  :key="d.name"
                  class="gv-dim-row"
                  :class="{ 'is-low': d.name === growthLowestDim && d.value < 80 }"
                >
                  <div class="gv-dim-top">
                    <span class="gv-dim-name">{{ d.name }}</span>
                    <span class="gv-dim-val">{{ d.value }}</span>
                  </div>
                  <div class="gv-dim-track"><div class="gv-dim-fill" :style="{ width: Math.min(100, d.value) + '%' }"></div></div>
                </div>
              </div>
            </div>
            <p class="gv-insight" v-if="growthAdvice">{{ growthAdvice }}</p>
          </section>

          <!-- ===== 记录构成：48px 迷你柱状图（参考 Apple Health 噪音模块） =====
               柱状图从占满一屏压到 48px，把省下的空间给一句结论。 -->
          <section class="gv-card">
            <header class="gv-card-head">
              <h3 class="gv-card-title">记录构成</h3>
              <span class="gv-card-meta">{{ growthBarInsight }}</span>
            </header>
            <div class="gv-mini">
              <v-chart v-if="profile?.stats_by_type?.length" :option="growthBarOption" class="gv-mini-chart" autoresize />
              <el-empty v-else description="暂无数据" :image-size="40" />
            </div>
          </section>

          <!-- ===== 成长历程：折线压到 110px，饼图去掉（分布已由上面的柱状图承担） ===== -->
          <section class="gv-card">
            <header class="gv-card-head">
              <h3 class="gv-card-title">成长历程</h3>
              <span class="gv-card-meta">{{ growthTrendInsight }}</span>
            </header>
            <div class="gv-mini is-line">
              <v-chart v-if="profile?.monthly_trend?.length" :option="growthLineOption" class="gv-line-chart" autoresize />
              <el-empty v-else description="暂无数据" :image-size="40" />
            </div>
          </section>

          <!-- 成长记录 -->
          <section class="gv-card gv-records">
            <header class="gv-card-head">
              <h3 class="gv-card-title">成长记录</h3>
              <span class="gv-card-meta" v-if="growthRecords.length">{{ growthRecords.length }} 条</span>
              <button v-if="growthRecords.length > 3" class="gv-text-btn" type="button" @click="allRecordsVisible = true">全部</button>
            </header>
            <div v-if="growthRecords.length" class="gv-record-list">
              <button
                v-for="r in growthRecords.slice(0, 3)"
                :key="r.id"
                class="gv-record"
                type="button"
                @click="showRecordDetail(r)"
              >
                <span class="gv-record-dot" :style="{ background: dotColor(r.type) }"></span>
                <span class="gv-record-main">
                  <span class="gv-record-title">{{ r.title }}</span>
                  <span class="gv-record-sub">{{ typeLabel(r.type) }} · {{ formatGrowthDate(r.date) }}</span>
                </span>
                <el-icon class="gv-record-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
            <p v-else class="gv-empty-text">还没有成长记录，点右上角「记一笔」开始</p>
            <button class="gv-add-block" type="button" @click="openDialog">
              <el-icon :size="14"><Plus /></el-icon>
              <span>添加成长记录</span>
            </button>
          </section>

          <!-- 项目展示 -->
          <section class="gv-card">
            <header class="gv-card-head">
              <h3 class="gv-card-title">项目展示</h3>
              <span class="gv-card-meta" v-if="projects.length">{{ projects.length }} 个</span>
              <button v-if="projects.length > 3" class="gv-text-btn" type="button" @click="showAllProjects = !showAllProjects">{{ showAllProjects ? '收起' : '更多' }}</button>
            </header>
            <div v-if="projects.length" class="gv-project-list">
              <button v-for="p in visibleProjects" :key="p.id" class="gv-project" type="button" @click="editProject(p)">
                <span class="gv-project-icon" :class="p.is_team ? 'team' : 'solo'">
                  <el-icon :size="15"><UserFilled v-if="p.is_team" /><User v-else /></el-icon>
                </span>
                <span class="gv-project-main">
                  <span class="gv-project-name">{{ p.project_name }}</span>
                  <span class="gv-project-sub">{{ p.start_date }} ~ {{ p.end_date || '至今' }}<template v-if="p.is_team && p.team_members"> · {{ p.team_members }}</template></span>
                </span>
                <el-icon class="gv-record-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
            <p v-else class="gv-empty-text">还没有项目，可以把课程设计、竞赛作品放进来</p>
            <button class="gv-add-block" type="button" @click="openProjectDialog">
              <el-icon :size="14"><Plus /></el-icon>
              <span>添加项目</span>
            </button>
          </section>

          <!-- 技能与兴趣（AI 归纳版）
               标签不再由学生手动增删：绵小城依据成长档案（成长记录 / 项目作品 / 课程成绩 /
               对话沉淀）自动归纳，学生只读查看；点击任意标签展开「来源证据」，
               能直接看到这条标签是从哪一条档案推出来的，避免出现无依据的标签。 -->
          <section class="gv-card skills-card">
            <header class="gv-card-head">
              <h3 class="gv-card-title">技能与兴趣</h3>
              <span class="gv-card-meta" v-if="aiTags.length">绵小城归纳 · {{ aiTags.length }}</span>
            </header>
            <div class="skills-body skills-body-compact">
              <div v-if="aiTags.length" class="tag-cloud">
                <button
                  v-for="t in aiTags"
                  :key="t.key"
                  type="button"
                  class="ai-tag"
                  :class="[`is-${t.kind}`, { active: activeTagKey === t.key }]"
                  @click="toggleTagEvidence(t.key)"
                >
                  <span class="ai-tag-name">{{ t.name }}</span>
                  <span class="ai-tag-count">{{ t.evidence.length }}</span>
                </button>
              </div>
              <p v-else class="skills-empty">成长档案还很空，记录一条成长或完成一次打卡后，绵小城会自动归纳标签</p>

              <div v-if="activeTag" class="tag-evidence">
                <div class="tag-evidence-head">
                  <span class="tag-evidence-head-title">{{ activeTag.name }} · 来源证据</span>
                  <button class="tag-evidence-close" type="button" @click="activeTagKey = ''">收起</button>
                </div>
                <div v-if="activeTag.evidence.length" class="tag-evidence-list">
                  <div v-for="(e, i) in activeTag.evidence" :key="i" class="tag-evidence-item">
                    <span class="tag-evidence-label" :class="`src-${e.source}`">{{ e.label }}</span>
                    <span class="tag-evidence-main">
                      <span class="tag-evidence-title">{{ e.title }}</span>
                      <span class="tag-evidence-detail">{{ e.detail }}<template v-if="e.date"> · {{ e.date }}</template></span>
                    </span>
                  </div>
                </div>
                <p v-else class="tag-evidence-empty">这个标签来自对话记忆，暂时没有可展示的档案条目</p>
              </div>
            </div>
          </section>

          <!-- Dialogs -->
          <el-dialog v-model="projectDialogVisible" :title="editingProject ? '编辑项目' : '添加项目'" width="500px">
            <el-form ref="projectFormRef" :model="projectForm" label-width="100px" :rules="projectRules">
              <el-form-item label="项目名称" prop="project_name"><el-input v-model="projectForm.project_name" placeholder="请输入项目名称，如：基于大数据的智慧校园平台" /></el-form-item>
              <el-row :gutter="20">
                <el-col :span="12"><el-form-item label="开始日期" prop="start_date"><el-date-picker v-model="projectForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="请选择开始日期" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="结束日期"><el-date-picker v-model="projectForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" clearable placeholder="不填表示进行中" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="是否团队"><el-switch v-model="projectForm.is_team" active-text="团队" inactive-text="个人" /></el-form-item>
              <el-form-item v-if="projectForm.is_team" label="团队成员" prop="team_members"><el-input v-model="projectForm.team_members" placeholder="逗号分隔，如：张三, 李四, 王五" /></el-form-item>
              <el-form-item label="项目成果"><UploadBtn v-model="projectForm.attachment_url" /></el-form-item>
            </el-form>
            <template #footer>
              <el-button v-if="editingProject" type="danger" text @click="handleDeleteProject(editingProject.id)">删除项目</el-button>
              <el-button @click="projectDialogVisible = false">取消</el-button>
              <el-button type="primary" @click="handleSaveProject">{{ editingProject ? '保存' : '添加' }}</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="dialogVisible" :title="'添加成长记录 — ' + typeLabel(form.type)" width="600px" class="growth-dialog">
            <el-form ref="growthFormRef" :model="form" label-width="100px" :rules="growthRules">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="类型" prop="type">
                    <el-select v-model="form.type" placeholder="请选择记录类型" @change="onTypeChange">
                      <el-option label="荣誉" value="honor" />
                      <el-option label="竞赛" value="competition" />
                      <el-option label="实践" value="practice" />
                      <el-option label="论文" value="paper" />
                      <el-option label="成果" value="achievement" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="日期" prop="date"><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="请选择发生日期" /></el-form-item>
                </el-col>
              </el-row>
              <template v-if="form.type === 'honor'">
                <el-form-item label="荣誉等级" prop="honor_level"><el-select v-model="form.honor_level" placeholder="请选择荣誉等级" style="width:100%"><el-option label="校级" value="校级" /><el-option label="省级" value="省级" /><el-option label="国家级" value="国家级" /><el-option label="国际级" value="国际级" /></el-select></el-form-item>
                <el-form-item label="荣誉名称" prop="title"><el-input v-model="form.title" placeholder="例如：国家奖学金" /></el-form-item>
                <el-form-item label="荣誉描述"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="颁发单位、获奖时间等" /></el-form-item>
                <el-form-item label="证明材料"><UploadBtn v-model="form.attachment_url" /></el-form-item>
              </template>
              <template v-if="form.type === 'competition'">
                <el-form-item label="竞赛名称" prop="title"><el-input v-model="form.title" placeholder="例如：ACM-ICPC国际大学生程序设计竞赛" /></el-form-item>
                <el-form-item label="主办方"><el-input v-model="form.organizer" placeholder="例如：ACM/ICPC组委会" /></el-form-item>
                <el-form-item label="竞赛等级" prop="competition_level"><el-select v-model="form.competition_level" placeholder="请选择竞赛等级" style="width:100%"><el-option label="校级" value="校级" /><el-option label="省级" value="省级" /><el-option label="国家级" value="国家级" /><el-option label="国际级" value="国际级" /></el-select></el-form-item>
                <el-form-item label="获奖情况"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="金奖/银奖/铜奖/一等奖等" /></el-form-item>
                <el-form-item label="证明材料"><UploadBtn v-model="form.attachment_url" /></el-form-item>
              </template>
              <template v-if="form.type === 'practice'">
                <el-form-item label="实践类型" prop="practice_type"><el-select v-model="form.practice_type" placeholder="请选择实践类型" style="width:100%"><el-option label="社会志愿活动" value="社会志愿活动" /><el-option label="三下乡" value="三下乡" /><el-option label="支教" value="支教" /><el-option label="西部计划" value="西部计划" /><el-option label="筑梦扬帆计划" value="筑梦扬帆计划" /><el-option label="其他社会实践" value="其他社会实践" /></el-select></el-form-item>
                <el-form-item label="实践名称" prop="title"><el-input v-model="form.title" placeholder="例如：暑期三下乡支教活动" /></el-form-item>
                <el-form-item label="实践描述"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="实践内容、服务时长等" /></el-form-item>
                <el-form-item label="荣誉证明"><el-input v-model="form.practice_certificate" type="textarea" :rows="2" placeholder="优秀志愿者证书/表彰文件等" /></el-form-item>
                <el-form-item label="证明材料"><UploadBtn v-model="form.attachment_url" /></el-form-item>
              </template>
              <template v-if="form.type === 'paper'">
                <el-form-item label="论文题目" prop="paper_name"><el-input v-model="form.paper_name" placeholder="论文完整标题" /></el-form-item>
                <el-form-item label="期刊类型" prop="paper_type"><el-select v-model="form.paper_type" placeholder="请选择期刊类型" style="width:100%"><el-option label="普刊" value="普刊" /><el-option label="核心期刊" value="核心期刊" /><el-option label="SCI" value="SCI" /><el-option label="EI" value="EI" /><el-option label="顶刊" value="顶刊" /><el-option label="会议论文" value="会议论文" /></el-select></el-form-item>
                <el-form-item label="第一作者"><el-input v-model="form.first_author" placeholder="姓名，如：张三" /></el-form-item>
                <el-row :gutter="20">
                  <el-col :span="12"><el-form-item label="第二作者"><el-input v-model="form.second_author" placeholder="姓名" /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="第三作者"><el-input v-model="form.third_author" placeholder="姓名" /></el-form-item></el-col>
                </el-row>
                <el-form-item label="备注"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="发表时间、期刊名称等" /></el-form-item>
                <el-form-item label="证明材料"><UploadBtn v-model="form.attachment_url" /></el-form-item>
              </template>
              <template v-if="form.type === 'achievement'">
                <el-form-item label="成果类型" prop="achievement_type"><el-select v-model="form.achievement_type" placeholder="请选择成果类型" style="width:100%"><el-option label="发明专利" value="发明专利" /><el-option label="实用新型专利" value="实用新型专利" /><el-option label="外观设计专利" value="外观设计专利" /><el-option label="软件著作权" value="软件著作权" /><el-option label="作品著作权" value="作品著作权" /></el-select></el-form-item>
                <el-form-item label="成果名称" prop="achievement_name"><el-input v-model="form.achievement_name" placeholder="专利/软著名称" /></el-form-item>
                <el-form-item label="成果标题"><el-input v-model="form.title" placeholder="简短标题" /></el-form-item>
                <el-form-item label="成果描述"><el-input v-model="form.description" type="textarea" :rows="2" placeholder="授权号、申请日等信息" /></el-form-item>
                <el-form-item label="证明材料"><UploadBtn v-model="form.attachment_url" /></el-form-item>
              </template>
            </el-form>
            <template #footer>
              <el-button @click="dialogVisible = false">取消</el-button>
              <el-button type="primary" @click="handleAdd">确认添加</el-button>
            </template>
          </el-dialog>

          <!-- 查看全部成长记录 -->
          <el-dialog v-model="allRecordsVisible" title="全部成长记录" width="680px" top="5vh">
            <div class="all-records-scroll">
              <div v-for="r in growthRecords" :key="r.id" class="record-card">
                <div class="record-left">
                  <div class="record-dot" :style="{ background: dotColor(r.type) }"></div>
                </div>
                <div class="record-body">
                  <div class="record-top">
                    <el-tag :type="typeTagType(r.type)" size="small" effect="dark" round>{{ typeLabel(r.type) }}</el-tag>
                    <span class="record-date">{{ formatGrowthDate(r.date) }}</span>
                  </div>
                  <div class="record-title">{{ r.title }}</div>
                  <div class="record-meta" v-if="r.description">{{ r.description }}</div>
                  <div class="record-details" v-if="r.type === 'honor' && r.honor_level">
                    <el-tag size="small" hit effect="plain">{{ r.honor_level }}</el-tag>
                  </div>
                  <div class="record-details" v-else-if="r.type === 'competition'">
                    <span v-if="r.organizer" class="detail-item">主办方: {{ r.organizer }}</span>
                    <span v-if="r.competition_level" class="detail-item">等级: {{ r.competition_level }}</span>
                  </div>
                  <div class="record-details" v-else-if="r.type === 'practice' && r.practice_type">
                    <span class="detail-item">{{ r.practice_type }}</span>
                  </div>
                  <div class="record-details" v-else-if="r.type === 'paper'">
                    <span v-if="r.paper_name" class="detail-item">{{ r.paper_name }}</span>
                    <span v-if="r.paper_type" class="detail-item">[{{ r.paper_type }}]</span>
                  </div>
                  <div class="record-details" v-else-if="r.type === 'achievement'">
                    <span v-if="r.achievement_name" class="detail-item">{{ r.achievement_name }}</span>
                    <span v-if="r.achievement_type" class="detail-item">[{{ r.achievement_type }}]</span>
                  </div>
                </div>
              </div>
            </div>
          </el-dialog>

          <!-- 成长记录详情弹窗 -->
          <el-dialog v-model="recordDetailVisible" :title="recordDetail?.title || '记录详情'" width="420px" top="8vh" class="record-detail-dialog">
            <template v-if="recordDetail">
              <div class="rd-header">
                <el-tag :type="typeTagType(recordDetail.type)" size="small" effect="dark" round>{{ typeLabel(recordDetail.type) }}</el-tag>
                <span class="rd-date">{{ formatGrowthDate(recordDetail.date) }}</span>
              </div>
              <div v-if="recordDetail.description" class="rd-desc">{{ recordDetail.description }}</div>
              <div class="rd-fields">
                <template v-if="recordDetail.type === 'honor'">
                  <div v-if="recordDetail.honor_level" class="rd-field"><span class="rd-label">荣誉等级</span><span class="rd-value">{{ recordDetail.honor_level }}</span></div>
                </template>
                <template v-else-if="recordDetail.type === 'competition'">
                  <div v-if="recordDetail.organizer" class="rd-field"><span class="rd-label">主办方</span><span class="rd-value">{{ recordDetail.organizer }}</span></div>
                  <div v-if="recordDetail.competition_level" class="rd-field"><span class="rd-label">竞赛等级</span><span class="rd-value">{{ recordDetail.competition_level }}</span></div>
                </template>
                <template v-else-if="recordDetail.type === 'practice'">
                  <div v-if="recordDetail.practice_type" class="rd-field"><span class="rd-label">实践类型</span><span class="rd-value">{{ recordDetail.practice_type }}</span></div>
                  <div v-if="recordDetail.practice_certificate" class="rd-field"><span class="rd-label">荣誉证明</span><span class="rd-value">{{ recordDetail.practice_certificate }}</span></div>
                </template>
                <template v-else-if="recordDetail.type === 'paper'">
                  <div v-if="recordDetail.paper_name" class="rd-field"><span class="rd-label">论文题目</span><span class="rd-value">{{ recordDetail.paper_name }}</span></div>
                  <div v-if="recordDetail.paper_type" class="rd-field"><span class="rd-label">期刊类型</span><span class="rd-value">{{ recordDetail.paper_type }}</span></div>
                  <div v-if="recordDetail.first_author" class="rd-field"><span class="rd-label">作者</span><span class="rd-value">{{ [recordDetail.first_author, recordDetail.second_author, recordDetail.third_author].filter(Boolean).join('、') }}</span></div>
                </template>
                <template v-else-if="recordDetail.type === 'achievement'">
                  <div v-if="recordDetail.achievement_name" class="rd-field"><span class="rd-label">成果名称</span><span class="rd-value">{{ recordDetail.achievement_name }}</span></div>
                  <div v-if="recordDetail.achievement_type" class="rd-field"><span class="rd-label">成果类型</span><span class="rd-value">{{ recordDetail.achievement_type }}</span></div>
                </template>
                <div v-if="recordDetail.attachment_url" class="rd-field"><span class="rd-label">证明材料</span><el-link type="primary" :href="recordDetail.attachment_url" target="_blank">查看附件</el-link></div>
              </div>
            </template>
            <template #footer>
              <el-button @click="recordDetailVisible = false">关闭</el-button>
            </template>
          </el-dialog>
          </template>

        </div>
        </Transition>

        <!-- 计算规则说明弹窗（独立于各页签，始终可触发） -->
        <el-dialog v-model="formulaDialogVisible" :title="formulaDialogTitle" width="700px" top="6vh" class="formula-dialog">          <!-- GPA 计算规则 -->
          <template v-if="formulaDialogType === 'gpa'">
            <div class="formula-tip">
              <el-icon><InfoFilled /></el-icon>
              <span>当前 GPA 即已录入的全部课程绩点的平均值。<b>注意：</b>这里采用的是简单平均而非按学分加权平均。</span>
            </div>
            <div class="formula-block">
              <div class="formula-title">计算公式</div>
              <div class="formula-line">平均GPA =（课程1绩点 + 课程2绩点 + … + 课程{{ gradeAnalysis.stats.total_courses }}绩点）÷ 课程总数</div>
              <div class="formula-sub">
                当前数据：共 <b>{{ gradeAnalysis.stats.total_courses }}</b> 门课程，当前 GPA = <b>{{ Number(gradeAnalysis.stats.avg_gpa).toFixed(2) }}</b>
              </div>
            </div>
            <div class="formula-block">
              <div class="formula-title">各课程绩点明细 <span style="font-weight:400;font-size:12px;color:#999">（便于找出拉低平均绩点的课程）</span></div>
              <div class="formula-table-wrap">
                <table class="formula-table">
                  <thead>
                    <tr><th>课程</th><th>学期</th><th>分数</th><th>绩点</th><th>学分</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(c, idx) in gpaFormulaCourses" :key="idx">
                      <td class="ft-name">{{ c.course_name }}</td>
                      <td>{{ c.semester }}</td>
                      <td>{{ c.score ?? '--' }}</td>
                      <td class="ft-gpa" :class="{ low: c.gpa < 3.5 }">{{ c.gpa.toFixed(2) }}</td>
                      <td>{{ c.credit }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="formula-tip">
              <el-icon><WarningFilled /></el-icon>
              <span>提升建议：重点提升绩点低于平均值的课程，绩点低于 3.5 的课程（红色标注）是提高整体 GPA 的关键突破口。</span>
            </div>
          </template>

          <!-- 综合评分计算规则 -->
          <template v-else>
            <div class="formula-tip">
              <el-icon><InfoFilled /></el-icon>
              <span>综合评分由 <b>5 个能力维度</b>构成，每个维度满分 100 分，综合评分即 5 个维度得分的<b>平均值</b>。</span>
            </div>
            <div class="formula-block">
              <div class="formula-title">计算公式</div>
              <div class="formula-line">综合评分 =（学术素养 + 创新能力 + 实践能力 + 社交素养 + 综合素质）÷ 5</div>
              <div class="formula-sub">
                当前数据：综合评分 = 各维度得分之和 ÷ 5 = <b>{{ profile?.total_score ?? '--' }}</b>
              </div>
            </div>
            <div class="formula-block">
              <div class="formula-title">各维度得分与计算规则</div>
              <div class="formula-dims">
                <div v-for="d in scoreDetail.dims" :key="d.name" class="formula-dim">
                  <div class="fd-top">
                    <span class="fd-name">{{ d.name }}</span>
                    <span class="fd-value">{{ d.value }} 分</span>
                  </div>
                  <div class="fd-bar"><div class="fd-bar-inner" :style="{ width: d.value + '%', background: fdColor(d.value) }"></div></div>
                  <div class="fd-formula">min(100, {{ d.formula }})</div>
                </div>
              </div>
            </div>
            <div class="formula-tip">
              <el-icon><WarningFilled /></el-icon>
              <span>提升建议：优先补齐得分偏低的维度（<b>{{ scoreSuggest(scoreDetail.dims) }}</b>），多记录成长档案、参与竞赛/实践、完善技能与兴趣，即可快速提升综合评分。</span>
            </div>
          </template>
          <template #footer>
            <el-button @click="formulaDialogVisible = false">关闭</el-button>
          </template>
        </el-dialog>

        <!-- ===== 请假服务子页（v3 新增）=====
            把原工作台的「请假申请 / 证明申请 / 项目申请」三个入口融合成一个子页，
            顶部用分段控制切换（对照 Apple Health 的「分类浏览」+ iOS 分段控件）。
            设计沿用子页规范：白卡 + 每页一个识别色（葡萄紫 #6d28d9，与课表赭橙 / 成绩青绿 / 成长靛蓝互不串色），
            表单项按 8px 节奏收紧，主按钮通栏。
            注意：这里用 v-if 而非 v-else-if —— 本页与 growth 之间隔着 Transition 边界，
            链式写法会因中间的独立弹窗元素而编译失败。 -->
        <div v-if="activeTab === 'service'" key="service" class="service-view">
          <!-- v5：美团订单流——顶部当前申请进度（无图标），表单收进「发起新申请」二级
               仅移动端；桌面端保持 v3 的「分段控件 + 常驻表单」原样。 -->
          <div v-if="isMobile && svCurrent" class="sv-current">
            <span class="svc-cap">当前进行中的申请</span>
            <h4 class="svc-title">{{ svCurrent.title }}</h4>
            <div class="svc-steps">
              <div class="svc-step done"><i>✓</i><p>已提交</p></div>
              <div class="svc-step cur"><i></i><p>审批中</p></div>
              <div class="svc-step"><i></i><p>完成</p></div>
            </div>
            <p class="svc-hint">预计 24 小时内出结果，进展会同步到主页心情卡提醒</p>
          </div>
          <button v-if="isMobile" type="button" class="sv-cta" @click="svShowForms = !svShowForms">
            {{ svShowForms ? '收起申请表单' : '＋ 发起新申请' }}
          </button>
          <div v-show="isMobile ? svShowForms : true" class="sv-forms">
          <div class="sv-segment" role="tablist" aria-label="申请类型">
            <button v-for="t in SERVICE_TABS" :key="t.key" type="button" role="tab"
              :aria-selected="svTab === t.key"
              :class="['sv-seg-item', { active: svTab === t.key }]"
              @click="svTab = t.key">{{ t.label }}</button>
          </div>

          <!-- 请假 -->
          <div v-show="svTab === 'leave'" class="sv-card">
            <div class="sv-tip"><el-icon :size="13"><InfoFilled /></el-icon><span>提交后由辅导员审批，请如实填写</span></div>
            <div class="sv-field">
              <label class="sv-label">请假类型</label>
              <el-select v-model="svLeave.leave_type" placeholder="请选择" style="width:100%">
                <el-option label="课假" value="课假" /><el-option label="公假" value="公假" /><el-option label="宿假" value="宿假" />
                <el-option label="事假" value="事假" /><el-option label="病假" value="病假" /><el-option label="其他" value="其他" />
              </el-select>
            </div>
            <div class="sv-row2">
              <div class="sv-field"><label class="sv-label">开始日期</label>
                <el-date-picker v-model="svLeave.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始" style="width:100%" :disabled-date="svDisableStart" /></div>
              <div class="sv-field"><label class="sv-label">结束日期</label>
                <el-date-picker v-model="svLeave.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束" style="width:100%" :disabled-date="svDisableEnd" /></div>
            </div>
            <div class="sv-field">
              <label class="sv-label">请假理由</label>
              <el-input v-model="svLeave.reason" type="textarea" :rows="3" placeholder="请描述请假原因" />
            </div>
            <template v-if="svLeave.leave_type === '课假' || svLeave.leave_type === '公假'">
              <div class="sv-field"><label class="sv-label">证明材料</label><UploadBtn @uploaded="svLeave.attachments.push($event)" />
                <div class="sv-files"><el-tag v-for="(f, i) in svLeave.attachments" :key="i" closable @close="svLeave.attachments.splice(i, 1)">{{ svFileName(f) }}</el-tag></div></div>
            </template>
            <template v-if="svLeave.leave_type === '宿假'">
              <div class="sv-row2">
                <div class="sv-field"><label class="sv-label">宿舍楼</label><el-input v-model="svLeave.dormitory_building" placeholder="如：A栋" /></div>
                <div class="sv-field"><label class="sv-label">宿舍号</label><el-input v-model="svLeave.dormitory_room" placeholder="如：301" /></div>
              </div>
              <div class="sv-field"><label class="sv-label">家长证明</label><UploadBtn v-model="svLeave.parent_proof" /></div>
            </template>
            <button class="sv-submit" type="button" :disabled="svSubmitting" @click="svSubmitLeave">{{ svSubmitting ? '提交中…' : '提交申请' }}</button>
          </div>

          <!-- 证明 -->
          <div v-show="svTab === 'certificate'" class="sv-card">
            <div class="sv-field">
              <label class="sv-label">证明类型</label>
              <el-select v-model="svCert.certificate_type" placeholder="请选择" style="width:100%">
                <el-option label="在校证明" value="在校证明" /><el-option label="成绩单" value="成绩单" />
                <el-option label="在读证明" value="在读证明" /><el-option label="学籍证明" value="学籍证明" /><el-option label="其他" value="其他" />
              </el-select>
            </div>
            <div class="sv-field"><label class="sv-label">用途说明</label><el-input v-model="svCert.content" type="textarea" :rows="3" placeholder="请说明开具证明的用途" /></div>
            <div class="sv-field"><label class="sv-label">所需份数</label><el-input-number v-model="svCert.quantity" :min="1" :max="20" style="width:100%" /></div>
            <div class="sv-field"><label class="sv-label">附件材料</label><UploadBtn @uploaded="(u: string) => svCert.attachments.push(u)" />
              <div class="sv-files"><el-tag v-for="(f, i) in svCert.attachments" :key="i" closable @close="svCert.attachments.splice(i, 1)">{{ svFileName(f) }}</el-tag></div></div>
            <button class="sv-submit" type="button" :disabled="svSubmitting" @click="svSubmitCert">{{ svSubmitting ? '提交中…' : '提交申请' }}</button>
          </div>

          <!-- 项目 -->
          <div v-show="svTab === 'project'" class="sv-card">
            <div class="sv-field">
              <label class="sv-label">项目类型</label>
              <el-select v-model="svProject.project_type" placeholder="请选择" style="width:100%">
                <el-option label="竞赛项目" value="竞赛项目" /><el-option label="科研项目" value="科研项目" />
                <el-option label="社会实践" value="社会实践" /><el-option label="创业项目" value="创业项目" />
                <el-option label="学生工作" value="学生工作" /><el-option label="其他" value="其他" />
              </el-select>
            </div>
            <div class="sv-field"><label class="sv-label">项目名称</label><el-input v-model="svProject.title" placeholder="请输入项目名称" /></div>
            <div class="sv-row2">
              <div class="sv-field"><label class="sv-label">指导老师</label><el-input v-model="svProject.advisor" placeholder="姓名" /></div>
              <div class="sv-field"><label class="sv-label">预算（元）</label><el-input-number v-model="svProject.budget" :min="0" :step="100" style="width:100%" /></div>
            </div>
            <div class="sv-field"><label class="sv-label">团队成员</label><el-input v-model="svProject.team_members" placeholder="多个用逗号隔开" /></div>
            <div class="sv-row2">
              <div class="sv-field"><label class="sv-label">开始日期</label><el-date-picker v-model="svProject.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始" style="width:100%" /></div>
              <div class="sv-field"><label class="sv-label">结束日期</label><el-date-picker v-model="svProject.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束" style="width:100%" /></div>
            </div>
            <div class="sv-field"><label class="sv-label">项目简介</label><el-input v-model="svProject.content" type="textarea" :rows="4" placeholder="项目背景、目标、预期成果" /></div>
            <div class="sv-field"><label class="sv-label">附件材料</label><UploadBtn @uploaded="(u: string) => svProject.attachments.push(u)" />
              <div class="sv-files"><el-tag v-for="(f, i) in svProject.attachments" :key="i" closable @close="svProject.attachments.splice(i, 1)">{{ svFileName(f) }}</el-tag></div></div>
            <button class="sv-submit" type="button" :disabled="svSubmitting" @click="svSubmitProject">{{ svSubmitting ? '提交中…' : '提交申请' }}</button>
          </div>
          </div>

          <!-- v5：全部申请记录（请假/证明/项目合并，原「我的申请」并入这里）——仅移动端 -->
          <div v-if="isMobile" class="sv-records">
            <div class="ai-sec-head">
              <h3 class="ai-sec-title">全部申请记录</h3>
              <span class="ai-sec-count">{{ svRecords.length }} 条</span>
            </div>
            <div v-for="r in svRecords" :key="r.kind + '-' + r.id" class="svr-row">
              <div class="svr-main"><h5>{{ r.title }}</h5><small>{{ r.date }}</small></div>
              <span class="svr-st" :class="svStatusClass(r.status)">{{ svStatusLabel(r.status) }}</span>
            </div>
            <p v-if="!svRecords.length && !svRecordsLoading" class="ai-empty">还没有申请记录</p>
          </div>
        </div>

        <!-- ===== 学习计划子页（v4：原 /student/plan 独立路由收编为第 5 个 tab） =====
             PlanView 以 embedded 模式渲染（隐藏自带顶栏与滚动容器），内容流进本页滚动区。
             独立 v-if 而非挂进 v-else-if 链：与 service 同理，链中间隔着 Transition 边界。 -->
        <div v-if="activeTab === 'plan'" key="plan" class="plan-view-wrap">
          <PlanView embedded />
        </div>

        <!-- ===== AI 今日报告子页（v5）：心情 / 任务 / 已实现 / 天气 + 运势 =====
             事实由后端采集（心情今日优先、缺省沿用昨晚；任务含今日与遗留；实时天气），
             LLM 只负责措辞与重点标注；报告中带重点标注的条目可一键转成学习计划。 -->
        <div v-if="activeTab === 'ai'" key="ai" class="ai-view">
          <div v-if="reportLoading && !dailyReport" class="report-loading">
            <el-icon class="is-loading" :size="18"><Loading /></el-icon>
            <div>
              <p class="rl-title">正在生成今日报告…</p>
              <p class="rl-sub">读取今日心情、任务、成长积累与实时天气</p>
            </div>
          </div>

          <template v-else-if="dailyReport">
            <section class="rp-hero">
              <div class="rp-hero-top">
                <div class="rp-hero-left">
                  <p class="rp-date">{{ reportDateText }}</p>
                  <h2 class="rp-greet">{{ dailyReport.greeting }}</h2>
                </div>
                <div v-if="dailyReport.weather" class="rp-weather" :title="`${dailyReport.weather.city} 实时天气`">
                  <span class="rp-weather-emoji">{{ dailyReport.weather.emoji }}</span>
                  <div class="rp-weather-main">
                    <span class="rp-weather-temp">{{ dailyReport.weather.temp }}℃</span>
                    <span class="rp-weather-desc">{{ dailyReport.weather.desc }}</span>
                  </div>
                  <span class="rp-weather-range">{{ dailyReport.weather.low }}~{{ dailyReport.weather.high }}℃<br />降水 {{ dailyReport.weather.rain }}%</span>
                </div>
                <div v-else class="rp-weather rp-weather-off">
                  <span class="rp-weather-emoji">🌡️</span>
                  <div class="rp-weather-main"><span class="rp-weather-desc">天气暂不可用</span></div>
                </div>
              </div>
              <div class="rp-chips">
                <span class="rp-chip" :style="{ '--chip-c': dailyReport.mood.color }">
                  <span class="rp-chip-emoji">{{ dailyReport.mood.emoji }}</span>
                  <template v-if="dailyReport.mood.from === 'none'">还没记录心情</template>
                  <template v-else-if="dailyReport.mood.from === 'last_night'">昨晚 · {{ dailyReport.mood.label }}</template>
                  <template v-else>今天 · {{ dailyReport.mood.label }}</template>
                </span>
                <button type="button" class="rp-chip rp-chip-btn" @click="aiRefresh">
                  <el-icon :size="11"><MagicStick /></el-icon>重新生成
                </button>
              </div>
            </section>

            <section class="rp-fortune" :class="'rp-tone-' + fortuneTone(dailyReport.fortune.level)">
              <div class="rp-fortune-head">
                <div class="rp-fortune-title">
                  <span class="rp-fortune-label">今日运势</span>
                  <span class="rp-fortune-level">{{ dailyReport.fortune.level }}</span>
                </div>
                <span class="rp-fortune-score">{{ dailyReport.fortune.score }}<small>分</small></span>
              </div>
              <div class="rp-fortune-meter" aria-hidden="true">
                <i :style="{ width: dailyReport.fortune.score + '%' }"></i>
              </div>
              <p class="rp-fortune-key"><i class="rp-fortune-dot"></i>今日关键词 · {{ dailyReport.fortune.keyword }}</p>
              <p v-if="dailyReport.fortune.summary" class="rp-fortune-summary">{{ dailyReport.fortune.summary }}</p>
              <div class="rp-fortune-meta">
                <div class="rp-fortune-meta-item">
                  <small>幸运色</small>
                  <span>{{ dailyReport.fortune.lucky_color }}</span>
                </div>
                <div class="rp-fortune-meta-item">
                  <small>幸运时段</small>
                  <span>{{ dailyReport.fortune.lucky_time }}</span>
                </div>
              </div>
            </section>

            <section v-for="sec in dailyReport.sections" :key="sec.key" class="rp-sec">
              <div class="rp-sec-head">
                <span class="rp-sec-ico">{{ sectionIcon(sec.key) }}</span>
                <h3 class="rp-sec-title">{{ sec.title }}</h3>
              </div>
              <p v-for="(line, li) in sec.items" :key="li" class="rp-sec-line">
                <RichMarkText :text="line" />
              </p>
            </section>

            <section class="rp-sec rp-suggest">
              <div class="rp-sec-head">
                <span class="rp-sec-ico">🎯</span>
                <h3 class="rp-sec-title">可以加入学习计划的建议</h3>
                <span class="ai-sec-count">{{ reportSuggestions.length }} 条</span>
              </div>
              <ul v-if="reportSuggestions.length" class="ai-action-list">
                <li v-for="(a, i) in reportSuggestions" :key="i" class="ai-action">
                  <span class="ai-prio" :style="{ background: aiPrioMeta(a.priority).bg, color: aiPrioMeta(a.priority).ink }">{{ aiPrioMeta(a.priority).label }}</span>
                  <div class="ai-action-main">
                    <p class="ai-action-title">
                      <span v-if="a.when" class="ai-action-when">{{ a.when }}</span>{{ a.title }}
                    </p>
                    <p class="ai-action-content"><RichMarkText :text="a.content" /></p>
                    <button v-if="!aiAdded[i]" type="button" class="ai-add-btn" @click="aiAddToPlan(a, i)">＋ 生成近期计划并加入学习计划</button>
                    <span v-else class="ai-added">✓ 已加入学习计划</span>
                  </div>
                </li>
              </ul>
              <p v-else class="ai-empty">今天状态不错，暂时没有需要额外加入计划的事。</p>
            </section>

            <div class="rp-export-row">
              <button type="button" class="rp-export-btn" @click="exportReport">
                <el-icon :size="12"><Download /></el-icon>一键导出
              </button>
            </div>
          </template>

          <p v-else class="ai-empty">今日报告暂时生成失败，下拉刷新或稍后再试。</p>
        </div>
        </div>


    <!-- ===== 右侧垂直标签栏（桌面端），移动端由驾驶舱入口卡片代替 ===== -->
    <div class="page-tabs" v-if="!isMobile">
      <div :class="['page-tab', { active: activeTab === 'schedule' }]" @click="openSubPage('schedule')">
        <el-icon><Calendar /></el-icon> 课程表
      </div>
      <div :class="['page-tab', { active: activeTab === 'grades' }]" @click="openSubPage('grades')">
        <el-icon><DataLine /></el-icon> 成绩分析
      </div>
      <div :class="['page-tab', { active: activeTab === 'growth' }]" @click="openSubPage('growth')">
        <el-icon><TrendCharts /></el-icon> 成长轨迹
      </div>
      <div :class="['page-tab', { active: activeTab === 'service' }]" @click="openSubPage('service')">
        <el-icon><Tickets /></el-icon> 请假服务
      </div>
      <div :class="['page-tab', { active: activeTab === 'plan' }]" @click="openSubPage('plan')">
        <el-icon><Aim /></el-icon> 学习计划
      </div>
      <div :class="['page-tab', { active: activeTab === 'ai' }]" @click="openSubPage('ai')">
        <el-icon><MagicStick /></el-icon> 今日报告
      </div>
      <div class="page-tab" @click="goPortfolio">
        <el-icon><FolderOpened /></el-icon> 我的作品集
      </div>
      <!-- v4：情绪树洞淡出（心情卡承接），成长档案并入成长轨迹，桌面标签同步移除 -->
    </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCourses as fetchCourses, getGrades, getExams } from '@/api/academic'
import { getGradeAnalysis, type GradeAnalysis } from '@/api/gradeAnalysis'
import { WarningFilled, Location, TrendCharts, CircleCheckFilled, Lock, Calendar, MagicStick, Loading, Star, Trophy, DataAnalysis, Histogram, DataLine, Collection, FolderOpened, Link, User, UserFilled, InfoFilled, ArrowRight, ArrowDown, ArrowLeft, Grid, Plus, Tickets, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, ElCollapseTransition } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart, PieChart, RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, RadarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { Course, Grade, Exam, LeaveRequestOut, ServiceTicket } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { useAiAnalysis } from '@/composables/useAiAnalysis'
import { studentDataCache } from '@/utils/studentDataCache'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { getGrowthRecords, createGrowthRecord, getGrowthProfile, getProjects, createProject, updateProject, deleteProject } from '@/api/growth'
import type { GrowthProfile, StudentProject, GrowthTagItem } from '@/api/growth'
import { getStreak, createPlan } from '@/api/plan'
import type { Streak } from '@/api/plan'
import type { GrowthRecord } from '@/types'
import { renderMarkdown } from '@/utils/markdown'
import { createLeave, getMyLeaves } from '@/api/leave'
import { createTicket, getTickets } from '@/api/service'
import { fetchDailyReport, type DailyReport } from '@/api/agent'
import UploadBtn from '@/components/upload/UploadBtn.vue'
import RichMarkText from '@/components/common/RichMarkText.vue'
import GrowthDashboard from '@/components/growth/GrowthDashboard.vue'
import PlanView from '@/views/student/PlanView.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'

use([LineChart, BarChart, PieChart, RadarChart, GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, RadarComponent, CanvasRenderer])

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { isMobile } = useResponsive()

// 吉祥物与站点名称取自站点配置：管理端变更后学生端同步
const { siteMascot, siteName } = useSiteConfig()

// ===== 驾驶舱直达入口 =====
function goPortfolio() { router.push('/student/portfolio') }

// ===== 视图状态：home=主页（移动端），schedule/grades/growth/service=子页面 =====
const tabKeys = ['schedule', 'grades', 'growth', 'service', 'plan', 'ai'] as const
const validInitTab = (route.query.tab as string) || ''
const activeTab = ref<string>(
  (tabKeys as readonly string[]).includes(validInitTab)
    ? validInitTab
    : isMobile.value ? 'home' : 'schedule'
)
const subPageTitle = computed(() => {
  const map: Record<string, string> = { schedule: '课程表', grades: '成绩分析', growth: '成长轨迹', service: '请假服务', plan: '学习计划', ai: '今日报告' }
  return map[activeTab.value] || '学业中心'
})
/** 子页副标题：一句话说清这一页能做什么，滚动后自动收起，48px 高度不变 */
const subPageSub = computed(() => {
  const map: Record<string, string> = {
    schedule: '本周课程 · 时间地点',
    grades: '学期成绩 · 绩点趋势',
    growth: '记录 · 画像 · 里程碑',
    service: '请假 · 证明 · 项目',
    plan: '目标 · 关卡 · 打卡',
    ai: '近况分析 · 计划生成',
  }
  return map[activeTab.value] || ''
})
/** 模块识别色：只用于标题前的 6px 圆点（不铺色块） */
const subPageAccent = computed(() => {
  const map: Record<string, string> = {
    schedule: '#b45309', grades: '#0f7a58', growth: '#1a4fd6',
    service: '#3d4a57', plan: '#0369a1', ai: '#4f46e5',
  }
  return map[activeTab.value] || ''
})



// ===== 请假服务子页（v3 新增：融合原工作台的三个申请入口） =====
const SERVICE_TABS = [
  { key: 'leave', label: '请假' },
  { key: 'certificate', label: '证明' },
  { key: 'project', label: '项目' },
] as const
const svTab = ref<'leave' | 'certificate' | 'project'>('leave')
const svSubmitting = ref(false)
const svLeave = ref({ leave_type: '', start_date: '', end_date: '', reason: '', dormitory_building: '', dormitory_room: '', parent_proof: '', attachments: [] as string[] })
const svCert = ref({ certificate_type: '', content: '', quantity: 1, attachments: [] as string[] })
const svProject = ref({ project_type: '', title: '', advisor: '', team_members: '', start_date: '', end_date: '', budget: 0, content: '', attachments: [] as string[] })
function svFileName(u: string) { try { return decodeURIComponent(u.split('/').pop() || u).split('?')[0] } catch { return u } }
function svToday() { return new Date().toISOString().slice(0, 10) }
function svDisableStart(d: Date) { return d.getTime() < new Date(svToday() + 'T00:00:00').getTime() }
function svDisableEnd(d: Date) { return svLeave.value.start_date ? d.getTime() < new Date(svLeave.value.start_date + 'T00:00:00').getTime() : svDisableStart(d) }
function svMapLeaveType(label: string): string {
  const m: Record<string, string> = { '课假': 'other', '公假': 'competition', '宿假': 'personal', '事假': 'personal', '病假': 'sick', '其他': 'other' }
  return m[label] || 'other'
}
function svResetLeave() { Object.assign(svLeave.value, { leave_type: '', start_date: '', end_date: '', reason: '', dormitory_building: '', dormitory_room: '', parent_proof: '', attachments: [] }) }

async function svSubmitLeave() {
  const f = svLeave.value
  if (!f.leave_type || !f.start_date || !f.end_date || !f.reason) { ElMessage.warning('请填写所有必填项'); return }
  if (f.start_date < svToday()) { ElMessage.error('开始日期不能早于今天'); return }
  if (f.end_date < f.start_date) { ElMessage.error('结束日期不能早于开始日期'); return }
  if ((new Date(f.end_date + 'T00:00:00').getTime() - new Date(f.start_date + 'T00:00:00').getTime()) / 86400000 > 14) { ElMessage.error('请假时长不能超过15天'); return }
  svSubmitting.value = true
  try {
    await createLeave({ start_date: f.start_date, end_date: f.end_date, reason: `[${f.leave_type}] ${f.reason}`, leave_type: svMapLeaveType(f.leave_type) })
    ElMessage.success('请假申请已提交，等待辅导员审批')
    svResetLeave()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') } finally { svSubmitting.value = false }
}
async function svSubmitCert() {
  const f = svCert.value
  if (!f.certificate_type || !f.content) { ElMessage.warning('请填写所有必填项'); return }
  svSubmitting.value = true
  try {
    await createTicket({
      type: 'certificate', title: f.certificate_type, content: f.content,
      applicant_name: auth.userName || '', applicant_no: auth.user?.username || '', applicant_college: auth.user?.college || '',
      form_data: { certificate_type: f.certificate_type, quantity: f.quantity },
      attachments: f.attachments.length ? f.attachments : undefined,
    })
    ElMessage.success('证明申请已提交')
    Object.assign(f, { certificate_type: '', content: '', quantity: 1, attachments: [] })
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') } finally { svSubmitting.value = false }
}
async function svSubmitProject() {
  const f = svProject.value
  if (!f.project_type || !f.title || !f.start_date || !f.end_date || !f.content) { ElMessage.warning('请填写所有必填项'); return }
  if (f.end_date < f.start_date) { ElMessage.error('结束日期不能早于开始日期'); return }
  svSubmitting.value = true
  try {
    await createTicket({
      type: 'project', title: f.title, content: f.content,
      applicant_name: auth.userName || '', applicant_no: auth.user?.username || '', applicant_college: auth.user?.college || '',
      form_data: { project_type: f.project_type, advisor: f.advisor, team_members: f.team_members, start_date: f.start_date, end_date: f.end_date, budget: f.budget },
      attachments: f.attachments.length ? f.attachments : undefined,
    })
    ElMessage.success('项目申请已提交')
    Object.assign(f, { project_type: '', title: '', advisor: '', content: '', team_members: '', start_date: '', end_date: '', budget: 0, attachments: [] })
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') } finally { svSubmitting.value = false }
}

// ===== AI 今日报告子页（v5）：心情 / 任务 / 已实现 / 天气 + 运势 =====
const dailyReport = ref<DailyReport | null>(null)
const reportLoading = ref(false)
const aiAdded = ref<Record<number, boolean>>({})
const reportSuggestions = computed(() => dailyReport.value?.suggestions ?? [])

/** 加载报告；失败时保留旧内容，页面显示空态 */
async function loadAiFeed() {
  reportLoading.value = true
  try {
    const data = await fetchDailyReport()
    if (data) {
      dailyReport.value = data
      aiAdded.value = {}
    }
  } finally { reportLoading.value = false }
}

function aiRefresh() {
  void loadAiFeed()
}

/** 报告日期：2026-10-29 周四 */
const reportDateText = computed(() => {
  const d = dailyReport.value?.date
  if (!d) return ''
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date(`${d}T00:00:00`).getDay()]
  return `${d} ${week}`
})

/** 四段报告的小图标 */
function sectionIcon(key: string): string {
  return ({ review: '🪵', today: '🗓', mood: '💗', task: '🎯', weather: '🌦', achievement: '🏆' } as Record<string, string>)[key] || '·'
}

/** 运势等级 → 配色档位（上签喜庆、平签稳重、缓行签柔和，不用红色渲染负向） */
function fortuneTone(level: string): 'great' | 'good' | 'mid' | 'soft' {
  if (level.includes('上上')) return 'great'
  if (level.includes('上')) return 'good'
  if (level.includes('中')) return 'mid'
  return 'soft'
}

/** 优先级 → 徽标样式（数字越大越紧急） */
function aiPrioMeta(p: number): { label: string; bg: string; ink: string } {
  if (p >= 4) return { label: '紧急', bg: '#fdeaea', ink: '#c0392b' }
  if (p >= 3) return { label: '需关注', bg: '#fdf3e3', ink: '#b45309' }
  return { label: '提示', bg: '#e8f1fa', ink: '#0369a1' }
}

function aiFmtDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

type ReportSuggestion = DailyReport['suggestions'][number]

/** 把一条建议转成 7 天近期计划，写入学习计划 */
async function aiAddToPlan(a: ReportSuggestion, i: number) {
  const start = new Date()
  const end = new Date(Date.now() + 7 * 86400000)
  try {
    await createPlan({ title: a.title, objective: a.content, stage: null, start_date: aiFmtDate(start), end_date: aiFmtDate(end), goal_id: null })
    aiAdded.value = { ...aiAdded.value, [i]: true }
    ElMessage.success('已生成近期计划并加入学习计划')
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '加入失败，请重试') }
}

/** 去掉报告里的标注记号，导出为纯文本 */
function stripReportMarks(text: string): string {
  return text
    .replace(/==([^=]+)==/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
}

/** 一键导出今日报告为 Markdown 文件 */
function exportReport() {
  const r = dailyReport.value
  if (!r) return
  const w = r.weather
  const lines: string[] = []
  lines.push(`# AI 今日报告 · ${reportDateText.value}`, '', r.greeting)
  if (w) lines.push(`天气：${w.city} ${w.temp}℃ ${w.desc}（${w.low}~${w.high}℃，降水 ${w.rain}%）`)
  const moodText = r.mood.from === 'none' ? '还没记录心情' : r.mood.from === 'last_night' ? `昨晚 · ${r.mood.label}` : `今天 · ${r.mood.label}`
  lines.push(`心情：${moodText}`)

  lines.push('', `## 今日运势 · ${r.fortune.level} ${r.fortune.score} 分`)
  if (r.fortune.keyword) lines.push(`关键词：${r.fortune.keyword}`)
  if (r.fortune.summary) lines.push(r.fortune.summary)
  lines.push(`幸运色：${r.fortune.lucky_color}　幸运时段：${r.fortune.lucky_time}`)

  for (const sec of r.sections) {
    lines.push('', `## ${sec.title}`)
    for (const item of sec.items) lines.push(`- ${stripReportMarks(item)}`)
  }

  if (r.suggestions.length) {
    lines.push('', '## 学习计划建议')
    for (const s of r.suggestions) {
      lines.push(`- ${s.when ? `[${s.when}] ` : ''}${s.title}：${stripReportMarks(s.content)}`)
    }
  }

  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `AI今日报告_${r.date}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出今日报告')
}

// ===== 请假服务 v5：美团订单流 + 全部申请记录（「我的申请」已合并进来） =====
interface SvRecord { kind: 'leave' | 'ticket'; id: number; title: string; date: string; status: string }
const svRecordsLoading = ref(false)
const svRecords = ref<SvRecord[]>([])
const svShowForms = ref(false)
const svCurrent = computed(() => svRecords.value.find(r => ['pending', 'processing'].includes(r.status)) || null)

function svStatusLabel(st: string): string {
  const m: Record<string, string> = { pending: '审批中', processing: '处理中', approved: '已通过', rejected: '已退回', completed: '已办结', cancelled: '已取消', returned: '已销假' }
  return m[st] || st
}
function svStatusClass(st: string): string {
  return ['approved', 'completed', 'returned'].includes(st) ? 'ok' : ['rejected', 'cancelled'].includes(st) ? 'no' : 'ing'
}

async function loadServiceRecords() {
  if (svRecordsLoading.value) return
  svRecordsLoading.value = true
  try {
    const [leaves, tickets] = await Promise.all([
      getMyLeaves(),
      getTickets({ student_id: auth.user?.id || undefined }).catch(() => [] as ServiceTicket[]),
    ])
    const l = (leaves as LeaveRequestOut[]).map(v => ({
      kind: 'leave' as const, id: v.id,
      title: `请假 · ${v.start_date}${v.end_date && v.end_date !== v.start_date ? ' ~ ' + v.end_date : ''}`,
      date: (v.updated_at || v.created_at || '').slice(0, 10),
      status: v.return_confirmed ? 'returned' : v.status,
    }))
    const t = (tickets as ServiceTicket[]).map(v => ({
      kind: 'ticket' as const, id: v.id, title: v.title,
      date: (v.updated_at || v.created_at || '').slice(0, 10), status: v.status,
    }))
    svRecords.value = [...l, ...t].sort((a, b) => b.date.localeCompare(a.date))
  } catch { /* 静默：失败时显示空态 */ } finally { svRecordsLoading.value = false }
}

/** 子页顶栏的滚动收起状态：监听 .content-row 的滚动（它是子页真正的滚动容器） */
const subpageScrolled = ref(false)
function onSubpageScroll(e: Event) {
  const next = ((e.target as HTMLElement)?.scrollTop ?? 0) > 24
  if (next !== subpageScrolled.value) subpageScrolled.value = next
}

// ===== 驾驶舱主页 ↔ 学业子页面：覆盖式滑入/滑出 =====
// 用全局 .subpage（styles/animations.css，全站唯一实现）：子页从右滑入盖住主页，
// 返回时原路向右滑出。主页放在 <Transition> **之外**（见模板），所以它全程静止、
// 不会有任何动画；只有子页在动 —— 与工作台子页、校园资讯阅读器结构一致。
const subpageTransitionName = computed(() => (isMobile.value ? 'subpage' : ''))

/** .schedule-page 是整页滚动容器；进出子页统一从顶部开始更符合移动端导航习惯
    （子页滑入时若沿用主页的滚动位置，新页会显示在中段，观感突兀） */
const pageEl = ref<HTMLElement | null>(null)
function resetPageScroll() { if (pageEl.value) pageEl.value.scrollTop = 0 }

// 下拉刷新（移动端）：手势逻辑与吉祥物指示器与教师端首页 / 学生工作台共用同一模块
const dashboardRef = ref<InstanceType<typeof GrowthDashboard> | null>(null)

function openSubPage(tab: string) {
  if (activeTab.value === tab) return
  if (isMobile.value && activeTab.value === 'home') resetPageScroll()
  activeTab.value = tab
}
function backToHome() {
  if (activeTab.value === 'home') return
  if (isMobile.value) resetPageScroll()
  activeTab.value = 'home'
}

// ===== 移动端：课程画像折叠（默认收起，点击标题行展开；桌面端恒为展开） =====
const courseProfileOpen = ref(false)
function toggleCourseProfile() { if (isMobile.value) courseProfileOpen.value = !courseProfileOpen.value }

// ===== 页签 =====

// ===== 成绩分析 =====
/** 成绩分析页签的数据是否已就绪（按需加载：首次进入该页签才请求；加载态由它统一承载） */
const gradesReady = ref(false)
const gradeAnalysis = ref<GradeAnalysis>({
  stats: { total_courses: 0, total_credits: 0, avg_score: 0, avg_gpa: 0, highest_gpa: 0, lowest_gpa: 0, pass_rate: 0, gpa_rank: 0, total_students: 0 },
  semester_gpa: [], course_type_stats: [], score_distribution: [], top_courses: [], weak_courses: []
})

async function loadGradeAnalysis() {
  try {
    const data = await getGradeAnalysis(auth.user?.id || 0)
    gradeAnalysis.value = data
  } catch (error) {
    console.error('加载成绩分析失败:', error)
  }
}

// ===== 成绩分析图表 =====
const hasScores = computed(() => gradeAnalysis.value.score_distribution.some(d => d.count > 0))
function shortSem(sem: string) {
  const parts = sem.split('-')
  if (parts.length < 3) return sem
  return `${parts[0].slice(2)}-${parts[1].slice(2)}·${parts[2]}`
}
/** 分数段配色（v3）：不再用「红黄蓝绿」四色并列，改成同一识别色的深浅梯度。
    分数段本身就是「好→更好」的有序关系，用梯度表达比用四个色相更准确，
    也让成绩页只保留青绿一个色系（避免图表五颜六色）。 */
function distColor(range: string) {
  if (range === '90-100') return '#0f7a58'
  if (range === '80-89') return '#2f9c76'
  if (range === '70-79') return '#7fc2a8'
  if (range === '60-69') return '#b8dccc'
  return '#dce9e3'
}
function barWidth(s?: number) { return Math.max(6, Math.min(100, s ?? 0)) + '%' }
/* v3：成绩页三个图表全部改为「无轴 + 值标图上」的迷你样式，
   chartAxis / chartSplitLine 两个旧常量已无引用，删除以免 vue-tsc 报 TS6133。 */

const semGpaOption = computed(() => {
  const gpas = gradeAnalysis.value.semester_gpa.map(s => s.gpa)
  const hi = Math.max(...gpas, 0.01)
  const lo = Math.min(...gpas, hi - 0.01)
  /* y 轴不能写死 0–4：绩点基本都在 3.0–3.8 之间，0–4 的固定区间会把三个点压成一条直线，
     「趋势」就消失了。这里按实际数据上下各留 0.15 的余量，
     既让起伏看得见，又不会放大到把 0.03 的波动画成悬崖。
     刻度与网格线同时隐藏 —— 读者看的是形状，精确值已在点上标出。 */
  const pad = Math.max(0.12, (hi - lo) * 0.35)
  const yMin = Math.max(0, +(lo - pad).toFixed(2))
  const yMax = +Math.min(4, hi + pad * 1.4).toFixed(2)
  return {
    tooltip: {
      trigger: 'axis', confine: true,
      backgroundColor: 'rgba(255,255,255,0.97)', borderColor: '#e9ebee', borderWidth: 1,
      textStyle: { color: '#14171a', fontSize: 12 },
      formatter: (p: any) => `${p[0]?.axisValue}：绩点 <b>${p[0]?.value}</b>`,
    },
    grid: { left: 4, right: 10, top: 18, bottom: 2, containLabel: true },
    xAxis: {
      type: 'category', boundaryGap: false,
      data: gradeAnalysis.value.semester_gpa.map(s => shortSem(s.semester)),
      axisLabel: { fontSize: 10, color: '#6b737c', interval: 0, margin: 6 },
      axisLine: { lineStyle: { color: '#e9ebee' } }, axisTick: { show: false },
    },
    yAxis: {
      type: 'value', min: yMin, max: yMax,
      axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false },
      splitLine: { show: false },
    },
    series: [{
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 5,
      data: gpas,
      lineStyle: { width: 2, color: '#0f7a58' },
      itemStyle: { color: '#0f7a58', borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: 'rgba(15, 122, 88, .10)' },
      label: { show: true, position: 'top', distance: 5, fontSize: 10, color: '#5b6470', formatter: (p: any) => p.value },
      markLine: gradeAnalysis.value.stats.avg_gpa ? {
        silent: true, symbol: 'none',
        lineStyle: { color: '#b9bec6', type: 'dashed' },
        label: { formatter: `总均绩 ${gradeAnalysis.value.stats.avg_gpa}`, fontSize: 10, color: '#6b737c', position: 'insideStartTop' },
        data: [{ yAxis: gradeAnalysis.value.stats.avg_gpa }]
      } : undefined
    }],
    animationDuration: 800
  }
})

const distOption = computed(() => ({
  tooltip: { trigger: 'axis', confine: true, formatter: (p: any) => `${p[0]?.axisValue}：<b>${p[0]?.value}</b> 门` },
  grid: { left: 4, right: 6, top: 18, bottom: 2, containLabel: true },
  xAxis: {
    type: 'category',
    data: gradeAnalysis.value.score_distribution.map(d => d.range.replace('0-59', '<60')),
    axisLabel: { fontSize: 10, color: '#6b737c', margin: 6 },
    axisLine: { lineStyle: { color: '#e9ebee' } }, axisTick: { show: false },
  },
  /* y 轴整条隐去：柱顶已标数值，读者要的是「哪档人多」的相对高低，不是刻度 */
  yAxis: { type: 'value', minInterval: 1, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
  series: [{
    type: 'bar', barWidth: '46%',
    data: gradeAnalysis.value.score_distribution.map(d => ({ value: d.count, itemStyle: { color: distColor(d.range), borderRadius: [4, 4, 0, 0] } })),
    label: { show: true, position: 'top', fontSize: 10, color: '#5b6470', distance: 4 }
  }],
  animationDuration: 800
}))

const typeOption = computed(() => ({
  tooltip: { trigger: 'axis', confine: true, formatter: (p: any) => { const t = gradeAnalysis.value.course_type_stats[p[0]?.dataIndex]; return t ? `${t.type}：均分 ${t.avg_score} / 均绩 ${t.avg_gpa} / ${t.count} 门` : '' } },
  grid: { left: 4, right: 6, top: 18, bottom: 2, containLabel: true },
  xAxis: {
    type: 'category', data: gradeAnalysis.value.course_type_stats.map(t => t.type),
    axisLabel: { fontSize: 10, color: '#6b737c', margin: 6, interval: 0 },
    axisLine: { lineStyle: { color: '#e9ebee' } }, axisTick: { show: false },
  },
  yAxis: {
    type: 'value', min: 0, max: 100,
    axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false },
  },
  series: [{
    type: 'bar', barWidth: '40%',
    data: gradeAnalysis.value.course_type_stats.map(t => ({ value: t.avg_score, itemStyle: { color: '#0f7a58', borderRadius: [4, 4, 0, 0] } })),
    label: { show: true, position: 'top', fontSize: 10, color: '#5b6470', distance: 4 }
  }],
  animationDuration: 800
}))

// ===== 课程表 =====
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const periodTimes: Record<number, string> = {
  1: '08:30', 2: '09:20', 3: '10:25', 4: '11:15',
  5: '14:10', 6: '15:00', 7: '16:05', 8: '16:55',
  9: '18:30', 10: '19:20', 11: '20:10', 12: '21:00'
}
function periodTimeLabel(p: number) { return periodTimes[p] || '' }
const allCourses = ref<Course[]>([])
const courses = computed(() => allCourses.value.filter(c => !selectedScheduleSem.value || c.semester === selectedScheduleSem.value))
const weekOffset = ref(0)
const baseWeek = ref(1)
const slideDir = ref<'left' | 'right'>('left')
const scheduleReady = ref(false)
const currentWeek = computed(() => Math.max(1, baseWeek.value + weekOffset.value))
const maxPeriod = 12
const dayMap: Record<string, number> = { '周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7 }

/**
 * 本周实际要显示的星期列。桌面端固定周一~周日（信息密度低，7 列更利于横向对照）；
 * 移动端 375px 下 7 列会把每列压到 ~41px，课程名和教室读不出来，
 * 因此无课的周末列不占位：只要周六或周日任一有课就两天一起显示，避免出现"周五 + 周日"这种断列。
 */
const visibleDays = computed(() => {
  if (!isMobile.value) return days
  const wk = currentWeek.value
  const hasWeekend = courses.value.some(c =>
    (c.day_of_week === 6 || c.day_of_week === 7) && wk >= c.week_start && wk <= c.week_end,
  )
  return hasWeekend ? days : days.slice(0, 5)
})

const courseGrid = computed(() => {
  const wk = currentWeek.value
  const shownDays = visibleDays.value
  const segEnd = (p: number) => (p <= 4 ? 4 : p <= 8 ? 8 : 12)
  const dayBlocks: Record<number, { start: number; end: number; course: Course }[]> = {}
  for (const day of shownDays) {
    const dayN = dayMap[day]
    const list = courses.value.filter(c => c.day_of_week === dayN && wk >= c.week_start && wk <= c.week_end)
    const blocks: { start: number; end: number; course: Course }[] = []
    for (const c of list) {
      let s = c.start_period
      while (s <= c.end_period) {
        const se = segEnd(s)
        const e = Math.min(c.end_period, se)
        blocks.push({ start: s, end: e, course: c })
        s = e + 1
      }
    }
    dayBlocks[dayN] = blocks
  }
  const rows = []
  /* v3 移动端：只渲染到「本周最后一节课结束的节次」，不再死板铺满 12 节。
     原来移动端固定 12 行 × 56px ≈ 672px，加上表头整块接近一整屏，
     一周只有 5~6 节课时下面全是空行，用户要滚很久才能看到下面内容。
     最少保留 8 节（上午 4 + 下午 4），保证表格看起来是「一天」而不是被截断。 */
  let lastUsed = 0
  if (isMobile.value) {
    for (const day of shownDays) {
      for (const b of dayBlocks[dayMap[day]] ?? []) lastUsed = Math.max(lastUsed, b.end)
    }
  }
  const rowCount = isMobile.value ? Math.min(maxPeriod, Math.max(8, lastUsed)) : maxPeriod
  for (let p = 1; p <= rowCount; p++) {
    const cells: any[] = []
    for (const day of shownDays) {
      const blocks = dayBlocks[dayMap[day]]
      const starts = blocks.filter(b => b.start === p)
      if (starts.length) {
        for (const b of starts) cells.push({ day, rowspan: b.end - b.start + 1, course: b.course, empty: false })
        continue
      }
      const covered = blocks.some(b => b.start < p && p <= b.end)
      if (covered) continue
      cells.push({ day, rowspan: 1, course: null, empty: true })
    }
    rows.push({ period: p, cells })
  }
  return rows
})

function calcCurrentRealWeek() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  let semesterStart: Date
  
  if (month >= 9) {
    semesterStart = new Date(year, 8, 1)
  } else if (month >= 3) {
    semesterStart = new Date(year, 2, 1)
  } else {
    semesterStart = new Date(year - 1, 8, 1)
  }
  
  const diff = Math.floor((now.getTime() - semesterStart.getTime()) / (7 * 24 * 60 * 60 * 1000))
  return Math.max(1, diff + 1)
}

function calcCurrentSemester() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  let semesterStartYear: number, term: number

  if (month >= 9) {
    // 9月起进入新学年第一学期
    semesterStartYear = year
    term = 1
  } else if (month >= 3) {
    // 3~8月属于上学年第二学期
    semesterStartYear = year - 1
    term = 2
  } else {
    // 1~2月寒假属上学年第一学期末
    semesterStartYear = year - 1
    term = 1
  }

  return {
    label: `${semesterStartYear}-${semesterStartYear + 1}学年${term === 1 ? '第一' : '第二'}学期`,
    year: semesterStartYear,
    term,
    maxWeeks: 19
  }
}

const currentSemester = computed(() => calcCurrentSemester())

const semesterKey = computed(() => `${currentSemester.value.year}-${currentSemester.value.year + 1}-${currentSemester.value.term}`)
const isHoliday = computed(() => currentWeek.value > currentSemester.value.maxWeeks)

// ===== 学期切换（可回退查看历史学期） =====
const selectedScheduleSem = ref(semesterKey.value)
const scheduleSemesterOptions = computed(() => {
  const sems = [...new Set(allCourses.value.map(c => c.semester || ''))].filter(Boolean).sort().reverse()
  return (sems.includes(semesterKey.value) ? sems : [semesterKey.value, ...sems]).map(s => ({ value: s, label: semesterLabel(s) }))
})
const isRealtimeView = computed(() => selectedScheduleSem.value === semesterKey.value && currentWeek.value === calcCurrentRealWeek())
const showResetBtn = computed(() => selectedScheduleSem.value === semesterKey.value && !isRealtimeView.value)
watch(selectedScheduleSem, () => {
  slideDir.value = 'left'
  const list = allCourses.value.filter(c => c.semester === selectedScheduleSem.value)
  baseWeek.value = list.length ? Math.min(...list.map(c => c.week_start)) : 1
  weekOffset.value = 0
})

// ===== 今日课程列高亮 =====
const todayDayN = new Date().getDay() === 0 ? 7 : new Date().getDay()
function isTodayCol(day: string) { return isRealtimeView.value && dayMap[day] === todayDayN }
/* 今天列的课程块再淡一档。旧实现用 base.slice(0,7) 取 #RRGGBB 再加 '3d'，
   等于把 palette 的 8 位色值截成了不透明色 —— 今天列的色块反而比其它天更实。
   现在直接对整串色值追加 alpha 后缀，保持同样的「更淡」语义。 */
function courseCellBg(name: string, day: string) {
  const base = courseColor(name)
  return isTodayCol(day) ? (base.length === 9 ? base.slice(0, 7) + '06' : base) : base
}

const palette = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9b59b6', '#1abc9c', '#e67e22', '#2ecc71', '#3498db', '#e74c3c']
const colorMap: Record<string, string> = {}
let colorIdx = 0
/* v3：课程块底色由 palette + '18'（约 9% 不透明度）降到 '0a'（约 4%）。
   一格 57px 宽、5 个色相铺满整屏时，「彩色」会盖过「课程名」本身；
   压到几乎白以后，颜色只在左侧 2px 色条上辨认，文字回到第一视觉层。 */
function courseColor(name: string) { if (!colorMap[name]) { colorMap[name] = palette[colorIdx % palette.length] + '0a'; colorIdx++ } return colorMap[name] }
function goPrevWeek() { if (currentWeek.value > 1) { slideDir.value = 'right'; weekOffset.value-- } }
function goNextWeek() { slideDir.value = 'left'; weekOffset.value++ }
function resetWeek() {
  const realWeek = calcCurrentRealWeek()
  if (currentWeek.value === realWeek) {
    ElMessage.info('已经在本周了')
    return
  }
  slideDir.value = currentWeek.value > realWeek ? 'right' : 'left'
  if (courses.value.length) {
    baseWeek.value = Math.min(...courses.value.map(c => c.week_start))
    weekOffset.value = realWeek - baseWeek.value
  } else {
    baseWeek.value = 1
    weekOffset.value = realWeek - 1
  }
}

// ===== 课程悬浮详情 =====
function dayName(d: number) { return ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][d - 1] || '' }
function formatSemester(sem: string) {
  if (!sem) return '--'
  const parts = sem.split('-')
  if (parts.length < 3) return sem
  return `${parts[0]}-${parts[1]} 第${parts[2] === '1' ? '一' : '二'}学期`
}
const isCoarse = ref(typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches)
const courseTipVisible = ref(false)
const hoverCourse = ref<(Course & { rowspan?: number }) | null>(null)
const tooltipPos = ref({ x: 0, y: 0 })
const tipColor = ref('#409eff')
const tipBg = ref('#f5f7fa')
let tipHideTimer: ReturnType<typeof setTimeout> | null = null

function lightenHex(hex: string, ratio = 0.9) {
  const n = parseInt(hex.slice(1), 16)
  if (Number.isNaN(n)) return '#f5f7fa'
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  const mix = (c: number) => Math.round(c + (255 - c) * ratio)
  return `rgb(${mix(r)}, ${mix(g)}, ${mix(b)})`
}

function hideCourseTip() {
  if (tipHideTimer) { clearTimeout(tipHideTimer); tipHideTimer = null }
  courseTipVisible.value = false
}

function showCourseTip(course: Course, e: Event) {
  hoverCourse.value = course
  const el = e.currentTarget as HTMLElement
  const r = el.getBoundingClientRect()
  // 气泡高约 200px：纵向也要夹取，否则下方第 8-12 节的课程信息会溢出视口、点不到也看不到
  const tipHeight = 210
  tooltipPos.value = {
    x: Math.min(r.right + 8, window.innerWidth - 236),
    y: Math.min(Math.max(8, r.top), Math.max(8, window.innerHeight - tipHeight))
  }
  const col = courseColor(course.name).slice(0, 7)
  tipColor.value = col
  tipBg.value = lightenHex(col)
  if (tipHideTimer) { clearTimeout(tipHideTimer); tipHideTimer = null }
  courseTipVisible.value = true
}

function onCourseEnter(course: Course, e: Event) {
  if (isCoarse.value) return
  showCourseTip(course, e)
}

function onCourseLeave() {
  if (isCoarse.value) return
  if (tipHideTimer) { clearTimeout(tipHideTimer) }
  tipHideTimer = setTimeout(() => { courseTipVisible.value = false }, 160)
}

function onCourseClick(course: Course, e: Event) {
  if (!isCoarse.value) return
  if (courseTipVisible.value && hoverCourse.value?.id === course.id) {
    hideCourseTip()
  } else {
    showCourseTip(course, e)
  }
}

function onTipEnter() {
  if (tipHideTimer) { clearTimeout(tipHideTimer); tipHideTimer = null }
}

function onTipLeave() {
  if (tipHideTimer) { clearTimeout(tipHideTimer) }
  tipHideTimer = setTimeout(() => { courseTipVisible.value = false }, 160)
}

function onDocClick(e: MouseEvent) {
  if (!courseTipVisible.value) return
  const target = e.target as HTMLElement
  if (target.closest('.schedule-course') || target.closest('.course-tip')) return
  hideCourseTip()
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('scroll', hideCourseTip, true)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('scroll', hideCourseTip, true)
})

// ===== 考试成绩 =====
const grades = ref<Grade[]>([])
const exams = ref<Exam[]>([])
const selectedSem = ref('')
const allGradesVisible = ref(false)
const gradeGridRef = ref<HTMLElement | null>(null)

// ===== 成绩卡片两行截断逻辑 =====
const gradeCols = ref(4)
function updateGradeCols() {
  const el = gradeGridRef.value
  if (!el) return
  const w = el.offsetWidth
  const minCol = 160
  const gap = 10
  gradeCols.value = Math.max(1, Math.floor((w + gap) / (minCol + gap)))
}
const maxVisible = computed(() => gradeCols.value * 2)
const visibleGrades = computed(() => {
  const list = selectedSem.value ? gradesBySem.value[selectedSem.value] || [] : []
  return list.slice(0, maxVisible.value)
})

watch(selectedSem, () => nextTick(updateGradeCols))
onMounted(() => { updateGradeCols(); window.addEventListener('resize', updateGradeCols) })
onUnmounted(() => window.removeEventListener('resize', updateGradeCols))
const goals = ref<Record<string, number>>({})
const goalInputs = ref<Record<string, number>>({})

// ===== AI 学情分析 =====
const { loading: gradeLoading, rawResult: gradeRaw, fromCache: gradeFromCache, analyze: runGradeAnalysis, reset: resetGrade } = useAiAnalysis('grades')
const gradeHtml = computed(() => renderMarkdown(gradeRaw.value))

async function startAiAnalysis(opts?: { stream?: boolean }) {
  const gradesData = grades.value.map(g => ({ course: g.course_name, score: g.score, gpa: g.gpa, credit: g.credit, semester: g.semester }))
  const prompt = `请分析以下学生的成绩数据，给出学情分析报告：\n1. 整体学业表现评估\n2. 各学期绩点变化趋势分析\n3. 优势科目和薄弱科目识别\n4. 学习建议和改进方向\n\n要求：基于数据直接给出分析结论与建议，不要反问、不要向用户提问；行文紧凑，段落之间不留空行。\n\n成绩数据：\n${JSON.stringify(gradesData, null, 2)}\n\n当前学期：${semesters.value[0] || '未知'}\n目标绩点：${goals.value[semesters.value[0]] ?? '未设置'}`
  try { if (opts?.stream) resetGrade(); await runGradeAnalysis(prompt, opts?.stream ? { skipCache: true } : undefined) } catch (e: any) { ElMessage.error('AI 分析失败：' + (e.message || '请稍后重试')) }
}

const semesters = computed(() => [...new Set(grades.value.map(g => g.semester))].sort().reverse())
function semesterLabel(sem?: string) {
  if (!sem) return ''
  const parts = sem.split('-')
  if (parts.length < 3) return sem
  return `${parts[0]}-${parts[1]}学年 第${parts[2] === '1' ? '一' : '二'}学期`
}
// 移动端工具栏空间紧张：学期标签用紧凑写法（如 “25-26 第一学期”）
function semesterLabelCompact(sem?: string) {
  if (!sem) return ''
  const parts = sem.split('-')
  if (parts.length < 3) return sem
  return `${parts[0].slice(2)}-${parts[1].slice(2)} 第${parts[2] === '1' ? '一' : '二'}学期`
}
const gradesBySem = computed(() => { const map: Record<string, Grade[]> = {}; for (const g of grades.value) { if (!map[g.semester]) map[g.semester] = []; map[g.semester].push(g) } return map })
const semStats = computed(() => { const stats: Record<string, { count: number; avg: number; gpa: string; credits: number }> = {}; for (const [sem, gs] of Object.entries(gradesBySem.value)) { const scores = gs.filter(g => g.score != null).map(g => g.score); const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0; const gpa = gs.length ? (gs.reduce((s, g) => s + (g.gpa || 0), 0) / gs.length).toFixed(2) : '0.00'; const credits = gs.reduce((s, g) => s + (g.credit || 0), 0); stats[sem] = { count: gs.length, avg, gpa, credits } } return stats })
const upcomingExams = computed(() => { const now = new Date(); return exams.value.filter(e => !e.exam_date || new Date(e.exam_date) >= now).sort((a, b) => (a.exam_date || '').localeCompare(b.exam_date || '')) })
function scoreLevel(s: number) { if (s >= 90) return 'level-a'; if (s >= 80) return 'level-b'; if (s >= 70) return 'level-c'; if (s >= 60) return 'level-d'; return 'level-f' }
function avgColor(s?: number) { if (!s) return '#6b737c'; if (s >= 90) return '#0a5b41'; if (s >= 80) return '#0f7a58'; if (s >= 70) return '#4a5a54'; return '#c2410c' }
function formatDate(d: string) { if (!d) return ''; const parts = d.split('-'); return parts[1] + '/' + parts[2] }
function loadGoals() { try { const raw = localStorage.getItem('student_sem_goals'); if (raw) goals.value = JSON.parse(raw) } catch { goals.value = {} } }
/* ===== 目标计划 v6（移动端）：4 级里程碑 =====
   刻度取「目标 -0.3 / -0.2 / -0.1 / 目标」，与用户设的目标绑定（改目标即刻重排）；
   实际绩点用一条填充轨 + 游标标出，节点按「已过 / 当前待过 / 未到」三态着色。 */
function glGpa(sem: string): number {
  return parseFloat(String(semStats.value[sem]?.gpa ?? '')) || 0
}
function glTarget(sem: string): number | null {
  const t = goals.value[sem]
  return t == null ? null : Number(t)
}
function glNodes(sem: string) {
  const target = glTarget(sem)
  if (target == null) return [] as { value: number; pos: number; state: string }[]
  const gpa = glGpa(sem)
  const vals = [-0.3, -0.2, -0.1, 0].map(d => Math.max(0, +(target + d).toFixed(2)))
  let nextFound = false
  return vals.map((v, i) => {
    let state = 'todo'
    if (gpa > 0 && gpa >= v) state = 'done'
    else if (!nextFound) { state = 'next'; nextFound = true }
    return { value: v, pos: (i / (vals.length - 1)) * 100, state }
  })
}
function glPct(sem: string): number {
  const target = glTarget(sem)
  if (target == null) return 0
  const lo = Math.max(0, +(target - 0.3).toFixed(2))
  const gpa = glGpa(sem)
  if (target <= lo) return gpa >= target ? 100 : 0
  if (gpa <= lo) return 0
  return Math.min(100, Math.round(((gpa - lo) / (target - lo)) * 100))
}
function glDone(sem: string): boolean {
  const t = glTarget(sem)
  return t != null && glGpa(sem) >= t
}
function glHint(sem: string): string {
  const t = glTarget(sem)
  if (t == null) return ''
  const gpa = glGpa(sem)
  if (!gpa) return '还没有绩点数据'
  if (gpa >= t) return `已达成目标，超出 ${(gpa - t).toFixed(2)}`
  const nodes = glNodes(sem)
  const done = nodes.filter(n => n.state === 'done').length
  const next = nodes.find(n => n.state === 'next')
  const gap = (t - gpa).toFixed(2)
  if (!next) return `差 ${gap} 达成 ${t.toFixed(2)}`
  return `已过 ${done}/4 级 · 再涨 ${(next.value - gpa).toFixed(2)} 到 ${next.value.toFixed(2)}，差 ${gap} 达标`
}
function saveGoalForSem(sem: string) { const val = goalInputs.value[sem]; if (val == null) return; goals.value[sem] = val; localStorage.setItem('student_sem_goals', JSON.stringify(goals.value)); ElMessage.success(`${sem} 目标已保存`) }

// ===== 成长轨迹 =====
const profile = ref<GrowthProfile | null>(null)
const growthRecords = ref<GrowthRecord[]>([])
const planStreak = ref<Streak | null>(null)
const dialogVisible = ref(false)
const allRecordsVisible = ref(false)
const recordDetailVisible = ref(false)
const recordDetail = ref<any>(null)
function showRecordDetail(r: any) { recordDetail.value = r; recordDetailVisible.value = true }
const showAllProjects = ref(false)
const form = ref<Record<string, any>>({ type: 'honor', title: '', description: '', date: '' })
const growthFormRef = ref()
const projectFormRef = ref()

const projectRules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  team_members: [{ required: true, message: '请填写团队成员', trigger: 'blur' }],
}

const growthRules = computed(() => {
  const base: Record<string, any> = {
    type: [{ required: true, message: '请选择记录类型', trigger: 'change' }],
    date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  }
  const t = form.value.type
  if (t === 'honor') {
    base.honor_level = [{ required: true, message: '请选择荣誉等级', trigger: 'change' }]
    base.title = [{ required: true, message: '请输入荣誉名称', trigger: 'blur' }]
  } else if (t === 'competition') {
    base.title = [{ required: true, message: '请输入竞赛名称', trigger: 'blur' }]
    base.competition_level = [{ required: true, message: '请选择竞赛等级', trigger: 'change' }]
  } else if (t === 'practice') {
    base.practice_type = [{ required: true, message: '请选择实践类型', trigger: 'change' }]
    base.title = [{ required: true, message: '请输入实践名称', trigger: 'blur' }]
  } else if (t === 'paper') {
    base.paper_name = [{ required: true, message: '请输入论文题目', trigger: 'blur' }]
    base.paper_type = [{ required: true, message: '请选择期刊类型', trigger: 'change' }]
  } else if (t === 'achievement') {
    base.achievement_type = [{ required: true, message: '请选择成果类型', trigger: 'change' }]
    base.achievement_name = [{ required: true, message: '请输入成果名称', trigger: 'blur' }]
  }
  return base
})
const projects = ref<StudentProject[]>([])
const visibleProjects = computed(() => showAllProjects.value ? projects.value : projects.value.slice(0, 3))
const loaded = ref(false)
const growthLoaded = ref(false)
const projectDialogVisible = ref(false)
const editingProject = ref<StudentProject | null>(null)
const projectForm = ref<Record<string, any>>({ project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '' })

/** 技能与兴趣标签：由绵小城依据成长档案归纳，只读展示；每条标签带来源证据 */
const aiTags = computed(() => {
  const p = profile.value
  const items: GrowthTagItem[] = []
  if (p?.skill_items?.length) items.push(...p.skill_items)
  else if (p?.skills?.length) items.push(...p.skills.map(name => ({ name, kind: 'skill' as const, evidence: [] })))
  if (p?.interest_items?.length) items.push(...p.interest_items)
  else if (p?.interests?.length) items.push(...p.interests.map(name => ({ name, kind: 'interest' as const, evidence: [] })))
  return items.map(t => ({ ...t, key: `${t.kind}-${t.name}` }))
})
const activeTagKey = ref('')
const activeTag = computed(() => aiTags.value.find(t => t.key === activeTagKey.value) ?? null)
function toggleTagEvidence(key: string) { activeTagKey.value = activeTagKey.value === key ? '' : key }
function openProjectDialog() { editingProject.value = null; projectForm.value = { project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '' }; projectDialogVisible.value = true }
function editProject(p: StudentProject) { editingProject.value = p; projectForm.value = { ...p }; projectDialogVisible.value = true }
async function handleSaveProject() { if (projectFormRef.value) { try { await projectFormRef.value.validate() } catch { return } } try { if (editingProject.value) { await updateProject(editingProject.value.id, projectForm.value as any); ElMessage.success('项目已更新') } else { await createProject(projectForm.value as any); ElMessage.success('项目已添加') } projectDialogVisible.value = false; projects.value = await getProjects() } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') } }
async function handleDeleteProject(id: number) { try { await ElMessageBox.confirm('确定删除该项目？', '确认'); await deleteProject(id); ElMessage.success('已删除'); projects.value = await getProjects() } catch {} }
function typeLabel(t: string) { const labels: Record<string, string> = { honor: '荣誉', competition: '竞赛', practice: '实践', paper: '论文', achievement: '成果' }; return labels[t] || t }
function typeTagType(t: string) { const types: Record<string, string> = { honor: 'warning', competition: 'primary', practice: 'success', paper: 'danger', achievement: 'info' }; return types[t] || 'default' }
function dotColor(t: string) { const colors: Record<string, string> = { honor: '#e6a23c', competition: '#409eff', practice: '#67c23a', paper: '#f56c6c', achievement: '#909399' }; return colors[t] || '#bbb' }
function formatGrowthDate(d: string) { if (!d) return ''; return d.slice(0, 10) }
function onTypeChange() { form.value.title = ''; form.value.description = ''; form.value.honor_level = ''; form.value.organizer = ''; form.value.competition_level = ''; form.value.practice_type = ''; form.value.practice_certificate = ''; form.value.paper_type = ''; form.value.paper_name = ''; form.value.first_author = ''; form.value.second_author = ''; form.value.third_author = ''; form.value.achievement_type = ''; form.value.achievement_name = '' }
function openDialog() { onTypeChange(); dialogVisible.value = true }
async function handleAdd() { if (growthFormRef.value) { try { await growthFormRef.value.validate() } catch { return } } const payload: Record<string, any> = {}; for (const k of Object.keys(form.value)) { if (form.value[k] !== '' && form.value[k] !== undefined) { payload[k] = form.value[k] } } if (!payload.title && payload.paper_name) payload.title = payload.paper_name; if (!payload.title && payload.achievement_name) payload.title = payload.achievement_name; try { await createGrowthRecord(payload as any); ElMessage.success('添加成功'); dialogVisible.value = false; growthRecords.value = await getGrowthRecords() as any; profile.value = await getGrowthProfile() as any } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '添加失败') } }

// ===== 计算公式说明弹窗 =====
const formulaDialogVisible = ref(false)
const formulaDialogType = ref<'gpa' | 'score'>('gpa')
const formulaDialogTitle = computed(() => formulaDialogType.value === 'gpa' ? '当前 GPA 计算说明' : '综合评分计算说明')

function openFormula(type: 'gpa' | 'score') { formulaDialogType.value = type; formulaDialogVisible.value = true }

// ===== 移动端：绵小城弹窗（AI 学情分析） =====
const mascotDialogVisible = ref(false)

const gpaFormulaCourses = computed(() => [...grades.value].sort((a, b) => (b.gpa ?? 0) - (a.gpa ?? 0)).map(g => ({
  course_name: g.course_name || '未知课程',
  gpa: g.gpa ?? 0,
  score: g.score,
  credit: g.credit ?? 0,
  semester: g.semester || ''
})))

const scoreDetail = computed(() => {
  const p = profile.value
  const records = p?.total_records ?? 0
  const skills = p?.total_skills ?? 0
  const interests = p?.interests?.length ?? 0
  const cnt = (n: string) => p?.stats_by_type?.find(s => s.name === n)?.value ?? 0
  const practice = cnt('实践')
  const competition = cnt('竞赛')
  const achievement = cnt('成果')
  const honor = cnt('荣誉')
  const paper = cnt('论文')
  const dims = [
    { name: '学术素养', value: Math.min(100, honor * 15 + paper * 30 + records * 3), formula: '荣誉数×15 + 论文数×30 + 成长记录数×3' },
    { name: '创新能力', value: Math.min(100, competition * 25 + achievement * 30), formula: '竞赛数×25 + 成果数×30' },
    { name: '实践能力', value: Math.min(100, records * 10 + skills * 8 + practice * 10), formula: '成长记录数×10 + 技能数×8 + 实践数×10' },
    { name: '社交素养', value: Math.min(100, interests * 15 + practice * 15), formula: '兴趣数×15 + 实践数×15' },
    { name: '综合素质', value: Math.min(100, (records + skills) * 8), formula: '(成长记录数 + 技能数)×8' },
  ]
  return { records, skills, interests, practice, competition, achievement, honor, paper, dims }
})

function fdColor(v: number) { if (v >= 80) return '#67c23a'; if (v >= 60) return '#409eff'; if (v >= 40) return '#e6a23c'; return '#f56c6c' }
function scoreSuggest(dims: { name: string; value: number }[]) { if (!dims.length) return '—'; const min = Math.min(...dims.map(d => d.value)); return dims.filter(d => d.value === min).map(d => d.name).join('、') }

/** 状态卡里的小评分环（r=25，周长 157.08） */
const gaugeLen = 2 * Math.PI * 25
const gaugeOffset = computed(() => {
  const s = Math.min(100, Math.max(0, profile.value?.total_score ?? 0))
  return gaugeLen - (gaugeLen * s) / 100
})
// ===== 成长页 v3：状态卡 / 热力日历 / 图表解读 =====
// 设计参考 Keep 9.0「数据概览」：状态卡先给一句人话评价和建议，指标放后面。
// 关键是**不煽情、不数落**——先承认现状，再给一个门槛极低的下一步。

/** 综合评分所在的档位：用于状态卡的标题与识别色 */
const growthTier = computed(() => {
  const s = profile.value?.total_score ?? 0
  if (s >= 85) return { key: 'high', label: '状态很好', tone: 'ok' as const, hint: '继续保持，可以把重心放在拔高上' }
  if (s >= 70) return { key: 'mid', label: '状态良好', tone: 'accent' as const, hint: '基础扎实，还有一两个方向可以再推一把' }
  if (s >= 50) return { key: 'low', label: '正在积累', tone: 'warning' as const, hint: '先把记录和标签补起来，评分会跟着动' }
  return { key: 'empty', label: '等待起步', tone: 'warning' as const, hint: '从一条成长记录开始，其它都会跟着长出来' }
})

/** 状态卡第二行：最低维度 + 具体可执行的一句话（对标 Keep「表达能力可再练」） */
const growthAdvice = computed(() => {
  const dims = profile.value?.radar ?? []
  if (!dims.length) return ''
  const low = dims.reduce((a, b) => (a.value <= b.value ? a : b))
  if (low.value >= 80) return '五个维度都在 80 分以上，很均衡'
  const tips: Record<string, string> = {
    学术素养: '补一篇论文或一份荣誉，这一项涨得最快',
    创新能力: '参加一次竞赛，或登记一个成果',
    实践能力: '再记一次实践，顺手补两个技能标签',
    社交素养: '补几项兴趣或多参加一次实践',
    综合素质: '成长记录和技能都还能再加一些',
  }
  return `${low.name} ${low.value} 分，${tips[low.name] ?? '这一项还有提升空间'}`
})

/** 最低维度的名字（用于在五维列表里点出警示色） */
const growthLowestDim = computed(() => {
  const dims = profile.value?.radar ?? []
  if (!dims.length) return ''
  return dims.reduce((a, b) => (a.value <= b.value ? a : b)).name
})

/** 紧凑数字网格：7 个数字改成 4 列 × 2 行，替代原来占半屏的横排大字 */
const growthMetrics = computed(() => {
  const p = profile.value
  const cnt = (n: string) => p?.stats_by_type?.find(s => s.name === n)?.value ?? 0
  return [
    { label: '成长记录', value: p?.total_records ?? 0 },
    { label: '技能', value: p?.total_skills ?? 0 },
    { label: '荣誉', value: cnt('荣誉') },
    { label: '竞赛', value: cnt('竞赛') },
    { label: '实践', value: cnt('实践') },
    { label: '论文', value: cnt('论文') },
    { label: '成果', value: cnt('成果') },
    { label: '兴趣', value: p?.interests?.length ?? 0 },
  ]
})

/**
 * 近 20 周热力日历（Duolingo / GitHub 贡献图的做法）。
 * 点亮规则：某一天有「学习动作」就点亮 —— 成长记录记一笔算 1 次，学习计划打卡一次也算 1 次。
 * 格子里存的不是布尔值而是当天的次数，颜色深浅按次数分 4 档：
 * 0 次=灰、1 次=浅、2~3 次=中、4 次及以上=深；连续天数同时参考成长记录与计划打卡的连击。
 * 按**自然周**分列（每列一周，周一到周日），20 列共 140 天；未来日期留白不渲染灰块。
 */
const HEAT_WEEKS = 20
const growthHeatmap = computed(() => {
  const counts = new Map<string, number>()
  const key = (d: Date) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
  const bump = (d: Date) => counts.set(key(d), (counts.get(key(d)) ?? 0) + 1)
  const parseDay = (raw: string) => {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(raw)
    return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(raw)
  }
  for (const r of growthRecords.value ?? []) {
    const raw = (r as any).date
    if (!raw) continue
    const d = parseDay(String(raw))
    if (Number.isNaN(d.getTime())) continue
    bump(d)
  }
  // 学习计划打卡同样点亮：坚持情况统计的是「这一天有没有学习动作」，不只是成长记录
  for (const day of planStreak.value?.days ?? []) {
    const d = parseDay(day)
    if (!Number.isNaN(d.getTime())) bump(d)
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const todayKey = key(today)
  // 本周一为第 7 天，往前推 HEAT_WEEKS-1 周 → 共 HEAT_WEEKS 列
  const mondayOffset = (today.getDay() + 6) % 7
  const start = new Date(today)
  start.setDate(today.getDate() - mondayOffset - 7 * (HEAT_WEEKS - 1))
  start.setHours(0, 0, 0, 0)

  const weeks: { level: number; title: string; isToday: boolean; isFuture: boolean }[][] = []
  let totalInRange = 0
  let activeDays = 0
  for (let w = 0; w < HEAT_WEEKS; w++) {
    const col: { level: number; title: string; isToday: boolean; isFuture: boolean }[] = []
    for (let d = 0; d < 7; d++) {
      const cur = new Date(start)
      cur.setDate(start.getDate() + w * 7 + d)
      const c = key(cur)
      const isFuture = cur > today
      const n = counts.get(c) ?? 0
      if (!isFuture && n > 0) { totalInRange += n; activeDays += 1 }
      col.push({
        level: isFuture ? -1 : n === 0 ? 0 : n === 1 ? 1 : n <= 3 ? 2 : 3,
        title: `${cur.getMonth() + 1}月${cur.getDate()}日${n ? ` · ${n} 次` : ''}`,
        isToday: c === todayKey,
        isFuture,
      })
    }
    weeks.push(col)
  }

  const monthLabel = `${start.getMonth() + 1}月`
  return { weeks, totalInRange, activeDays, rangeWeeks: HEAT_WEEKS, monthLabel, hasAny: totalInRange > 0 }
})

/** 连续记录天数（Duolingo 式「别断了」的心理锚点），成长记录与计划打卡取较长者 */
const growthStreak = computed(() => {
  const days = new Set<string>()
  for (const r of growthRecords.value ?? []) {
    const raw = (r as any).date
    if (!raw) continue
    const d = new Date(raw)
    if (Number.isNaN(d.getTime())) continue
    days.add(`${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`)
  }
  let streak = 0
  const cur = new Date()
  cur.setHours(0, 0, 0, 0)
  // 今天还没记录不算断 —— 从昨天开始数，符合「今天还有机会」的直觉
  const started = days.has(`${cur.getFullYear()}-${cur.getMonth() + 1}-${cur.getDate()}`)
  if (!started) cur.setDate(cur.getDate() - 1)
  for (let i = 0; i < 400; i++) {
    const k = `${cur.getFullYear()}-${cur.getMonth() + 1}-${cur.getDate()}`
    if (!days.has(k)) break
    streak += 1
    cur.setDate(cur.getDate() - 1)
  }
  return Math.max(streak, planStreak.value?.current ?? 0)
})

/** 图表解读：每个迷你图配一句话（Keep 的核心做法，图表只是佐证） */
const growthBarInsight = computed(() => {
  const stats = profile.value?.stats_by_type ?? []
  if (!stats.length) return '还没有分类数据'
  const top = stats.reduce((a, b) => (a.value >= b.value ? a : b))
  const total = stats.reduce((s, x) => s + x.value, 0) || 1
  return `${top.name}最多，占 ${Math.round((top.value / total) * 100)}%`
})
const growthTrendInsight = computed(() => {
  const trend = profile.value?.monthly_trend ?? []
  if (trend.length < 1) return '暂无足够数据'
  const byMonth = new Map<string, number>()
  for (const t of trend) byMonth.set(t.month, (byMonth.get(t.month) ?? 0) + t.count)
  const keys = [...byMonth.keys()].sort()
  const last = byMonth.get(keys[keys.length - 1]) ?? 0
  const prev = keys.length > 1 ? (byMonth.get(keys[keys.length - 2]) ?? 0) : 0
  if (!prev) return `最近记录 ${last} 条`
  const diff = last - prev
  if (diff === 0) return `与上月持平，${last} 条`
  return diff > 0 ? `比上月多 ${diff} 条` : `比上月少 ${-diff} 条`
})

const radarOption = computed(() => {
  const rad = profile.value?.radar ?? []
  return {
    animationDuration: 700,
    animationEasing: 'cubicOut' as const,
    tooltip: { show: false },
    radar: {
      indicator: rad.map(d => ({ name: d.name, max: 100 })),
      shape: 'polygon',
      center: ['50%', '50%'],
      radius: '72%',
      axisName: { show: false },
      axisLine: { lineStyle: { color: '#e9ebee' } },
      splitLine: { lineStyle: { color: '#e9ebee' } },
      splitArea: { show: false },
    },
    series: [{
      type: 'radar',
      silent: true,
      symbol: 'circle',
      symbolSize: 3,
      data: [{
        value: rad.map(d => d.value),
        lineStyle: { color: '#1a4fd6', width: 1.5 },
        itemStyle: { color: '#1a4fd6' },
        areaStyle: { color: 'rgba(26, 79, 214, 0.14)' },
      }],
    }],
  }
})
const growthBarOption = computed(() => {
  const stats = profile.value?.stats_by_type ?? []
  const max = Math.max(1, ...stats.map(s => s.value))
  return {
    animationDuration: 700,
    animationEasing: 'cubicOut' as const,
    tooltip: { show: false },
    grid: { left: 0, right: 0, top: 14, bottom: 0, containLabel: true },
    xAxis: {
      type: 'category',
      data: stats.map(s => s.name),
      axisLine: { lineStyle: { color: '#e9ebee' } },
      axisTick: { show: false },
      axisLabel: { color: '#6b737c', fontSize: 10, interval: 0, margin: 5 },
    },
    yAxis: { type: 'value', show: false, max: max * 1.34 },
    series: [{
      type: 'bar',
      barWidth: '46%',
      data: stats.map(s => ({ value: s.value, itemStyle: { color: '#1a4fd6', opacity: 0.28 + 0.55 * (s.value / max) } })),
      itemStyle: { borderRadius: [3, 3, 0, 0] },
      label: { show: true, position: 'top', color: '#5b6470', fontSize: 10, distance: 2 },
    }],
  }
})
/**
 * 成长历程折线（v3）。
 * 旧版问题：月份用 [...new Set()].sort() 排序，「10月」按字符串排在「5月」前面，
 * 且 5 条分类型折线 + 底部图例把 110px 的图压得只剩骨架。现在：
 * - 月份按真实时间顺序排（解析「N月」的数字）；
 * - 只画一条「每月总记录数」主线，颜色用成长页识别色；
 * - 不显示图例（单序列不需要），x 轴不显示「月份」轴名（标题已说明）。
 */
const growthLineOption = computed(() => {
  const trend = profile.value?.monthly_trend ?? []
  const byMonth = new Map<string, number>()
  for (const t of trend) byMonth.set(t.month, (byMonth.get(t.month) ?? 0) + t.count)
  const monthNum = (m: string) => {
    const n = parseInt(m.replace(/[^0-9]/g, ''), 10)
    return Number.isNaN(n) ? 99 : n
  }
  const months = [...byMonth.keys()].sort((a, b) => monthNum(a) - monthNum(b))
  return {
    animationDuration: 700,
    animationEasing: 'cubicOut' as const,
    tooltip: {
      trigger: 'axis', confine: true,
      backgroundColor: 'rgba(255,255,255,0.97)', borderColor: '#e9ebee', borderWidth: 1,
      textStyle: { color: '#14171a', fontSize: 12 },
      formatter: (p: any) => `${p[0]?.axisValue}：<b>${p[0]?.value}</b> 条记录`,
    },
    /* 折线卡片自带底部内边距，图表里就不再给 bottom，只留 2px 防止线条贴边。
       x 轴标签靠 containLabel 计算进内边距，这样「5月」不会被卡片下沿切掉。 */
    grid: { left: 0, right: 6, top: 16, bottom: 2, containLabel: true },
    xAxis: {
      type: 'category', boundaryGap: false, data: months,
      axisLine: { lineStyle: { color: '#e9ebee' } }, axisTick: { show: false },
      axisLabel: { color: '#6b737c', fontSize: 10, margin: 6 },
    },
    yAxis: {
      type: 'value', minInterval: 1, splitNumber: 2,
      axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f2f3f5' } },
    },
    series: [{
      name: '记录数', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      data: months.map(m => byMonth.get(m) ?? 0),
      lineStyle: { width: 2, color: '#1a4fd6' },
      itemStyle: { color: '#1a4fd6' },
      areaStyle: { color: 'rgba(26, 79, 214, 0.10)' },
      label: { show: true, position: 'top', fontSize: 10, color: '#5b6470', distance: 4 },
    }],
  }
})

onMounted(() => {
  loadGoals()
  // 只拉当前页签需要的数据；移动端首页由 GrowthDashboard 自己取数，父组件不发任何请求
  void ensureTabData(activeTab.value)
  // 课程数据随首屏立即并行加载：驾驶舱 Hero「下一节课」/今日课程时间线依赖它，
  // 加载期间由 GrowthDashboard 骨架占位（courses-loading），避免先闪空态再出内容
  void ensureTabData('schedule')
  // 其余子页内容后台预取：首屏让行后错峰拉成绩（含 AI 学情分析）与成长档案，进子页即读
  scheduleSubPagePrefetch()
})

/**
 * 下拉刷新：重拉课程（驾驶舱 Hero / 课表的数据源）、驾驶舱首页看板与当前页签数据。
 * 各加载器自带幂等守卫（只加载一次），这里绕过守卫直接取最新数据，缓存同步刷新。
 */
async function refreshAll() {
  const all = (await fetchCourses().catch(() => null)) as Course[] | null
  if (all) {
    studentDataCache.courses = all
    allCourses.value = all
    scheduleReady.value = true
    computeWeekBase()
  }
  if (activeTab.value === 'grades') {
    const [gradeList, examList] = await Promise.all([
      getGrades().catch(() => [] as any),
      getExams().catch(() => [] as any),
    ])
    grades.value = gradeList as Grade[]
    exams.value = examList as Exam[]
  } else if (activeTab.value === 'growth') {
    const [p, recordList, projectList, streak] = await Promise.all([
      getGrowthProfile().catch(() => null),
      getGrowthRecords().catch(() => [] as any),
      getProjects().catch(() => [] as any),
      getStreak().catch(() => null),
    ])
    if (p) profile.value = p
    growthRecords.value = recordList as any
    projects.value = projectList as any
    if (streak) planStreak.value = streak
  } else {
    await dashboardRef.value?.refresh()
  }
}

// 下拉刷新：桌面端不响应手势；指示器复用消息页的吉祥物起跳动画
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

/** 页签切换时补拉该页签的数据（每个页签只请求一次） */
watch(activeTab, (tab) => {
  void ensureTabData(tab)
})

/** 由当前课程集推导周次基准（缓存路径与网络路径都要算，否则 Hero 会先按第 1 周过滤而闪空态） */
function computeWeekBase() {
  const realWeek = calcCurrentRealWeek()
  if (courses.value.length) {
    baseWeek.value = Math.min(...courses.value.map(c => c.week_start))
    weekOffset.value = realWeek - baseWeek.value
  } else {
    baseWeek.value = 1
    weekOffset.value = realWeek - 1
  }
}

/** 课程表页签：只需要课程数据 */
async function loadScheduleData() {
  if (scheduleReady.value) return
  // 命中缓存先立即渲染（含空数组：上轮确实无课就直接显示空态），首帧即真实内容、不闪骨架，
  // 避免「骨架 → 内容」的高度跳变叠加在页面切换动画上（表现为下方卡片被推动的抽搐）
  if (studentDataCache.courses) {
    allCourses.value = studentDataCache.courses
    computeWeekBase()
    scheduleReady.value = true
  }
  // 请求失败时返回 null（不清空缓存、不把失败结果当成「确实无课」缓存下来）
  const all = (await fetchCourses().catch(() => null)) as Course[] | null
  if (all) {
    studentDataCache.courses = all
    allCourses.value = all
  }
  computeWeekBase()
  scheduleReady.value = true
}

/** 成绩分析页签：成绩 + 考试 + 成绩分析指标；进入后才发起 AI 学情分析 */
async function loadGradesData() {
  if (gradesReady.value) return
  const [gradeList, examList] = await Promise.all([
    getGrades().catch(() => [] as any),
    getExams().catch(() => [] as any),
    loadGradeAnalysis(),
  ])
  grades.value = gradeList as Grade[]
  exams.value = examList as Exam[]
  if (semesters.value.length) selectedSem.value = semesters.value[0]
  for (const sem of semesters.value) {
    if (goalInputs.value[sem] == null) goalInputs.value[sem] = goals.value[sem] ?? 3.5
  }
  gradesReady.value = true
  // 流式 AI 分析只在这里触发（不再一进页面就打一次 LLM），不阻塞页签渲染
  if (grades.value.length) startAiAnalysis()
}

/** 成长轨迹页签：成长画像 + 成长记录 + 项目 + 计划打卡（热力图点亮依据） */
async function loadGrowthData() {
  if (growthLoaded.value) return
  const [p, recordList, projectList, streak] = await Promise.all([
    getGrowthProfile().catch(() => null),
    getGrowthRecords().catch(() => [] as any),
    getProjects().catch(() => [] as any),
    getStreak().catch(() => null),
  ])
  if (p) profile.value = p
  if (streak) planStreak.value = streak
  growthRecords.value = recordList as any
  projects.value = projectList as any
  loaded.value = true
  growthLoaded.value = true
}

/** 页签数据单飞（single-flight）：按需加载与后台预取并发时复用同一次请求，避免重复打接口。
    各加载器自带幂等守卫（scheduleReady / gradesReady / growthLoaded）且内部已吞错（总会 resolve），
    失败也不会悬挂后续调用 */
const tabLoadPromises: Partial<Record<'schedule' | 'grades' | 'growth' | 'ai', Promise<void>>> = {}
function ensureTabData(tab: string): Promise<void> {
  if (tab === 'schedule') return (tabLoadPromises.schedule ??= loadScheduleData())
  if (tab === 'grades') return (tabLoadPromises.grades ??= loadGradesData())
  if (tab === 'growth') return (tabLoadPromises.growth ??= loadGrowthData())
  if (tab === 'ai') return (tabLoadPromises.ai ??= loadAiFeed())
  if (tab === 'service') return loadServiceRecords()
  return Promise.resolve()
}

// ===== 子页内容后台预取 =====
// 课程数据已在 onMounted 随首屏立即加载（驾驶舱 Hero 依赖）；此处只错峰预取其余子页：
// 1.6s 成绩数据：loadGradesData 在数据就绪后自动触发 AI 学情分析（LLM 流式生成），
// 提前开始意味着用户进入成绩分析时内容已就绪或接近完成；同刻并行拉成长档案数据。
// 用户若抢在预取前点入子页，按需加载照常生效且与预取单飞复用，不会重复请求；
// 卸载时清理定时器，已在途的 AI 流会写入 useAiAnalysis 的模块级缓存，下次进入秒开。
const prefetchTimers: number[] = []
function scheduleSubPagePrefetch() {
  prefetchTimers.push(window.setTimeout(() => {
    void ensureTabData('grades')
    void ensureTabData('growth')
  }, 1600))
}
onUnmounted(() => {
  prefetchTimers.forEach(t => window.clearTimeout(t))
  prefetchTimers.length = 0
})

watch(semesters, (list) => {
  if (list.length && !list.includes(selectedSem.value)) { selectedSem.value = list[0] }
  for (const sem of list) { if (goalInputs.value[sem] == null) { goalInputs.value[sem] = goals.value[sem] ?? 3.5 } }
})

watch(() => route.query.tab, (val) => {
  if (val && typeof val === 'string') {
    const t = val as string
    if ((tabKeys as readonly string[]).includes(t)) openSubPage(t)
    else if (t === 'home' && isMobile.value) backToHome()
  }
})
</script>

<style scoped>
.schedule-page {
  height: 100%; width: 100%; padding: 12px 16px 0; display: flex; flex-direction: column; box-sizing: border-box;
  overflow-y: auto; overflow-x: hidden; scrollbar-width: none; -ms-overflow-style: none;
  /* 整屏推入/推出过渡：离场元素转绝对定位后的对齐基准（随移动端媒体查询同步覆盖） */
  position: relative; --sp-pad-t: 12px; --sp-pad-x: 16px;
  /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
  overscroll-behavior-y: contain;
}
.schedule-page::-webkit-scrollbar { display: none; }

/* AI 成长驾驶舱区块（学业中心移动端顶部） */
/* ===== 移动端：驾驶舱主页 ===== */
/* ===== 移动端：驾驶舱主页 ===== */
/* 主页同样铺不透明底：覆盖式滑入的 0.3s 内子页尚未盖满，若主页透明，
   会从子页右侧露出的缝隙里透出下层容器背景，出现闪色。
   （旧模型由 animations.css 统一给进场页铺底，统一后由调用方各自负责。） */
.dashboard-home { display: flex; flex-direction: column; gap: 12px; padding-bottom: 24px; background: var(--dt-bg, #f5f6f7); }

/* ===== 主页固定 Head（v4.2）===== 白底 + 永久发丝线，与浅灰页面底形成区分：
   Head 是唯一常驻的白色横条，滚动内容从它下面穿过（48px 以上被裁掉），边界始终清晰 */
.home-bar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  display: flex; align-items: center; height: 48px; padding: 0 12px; box-sizing: border-box;
  background: var(--sp-surface, #ffffff);
  border-bottom: 1px solid var(--sp-border, #e9ebee);
}

/* ===== 子页去卡片化（v4.1）=====
   与主页同一步调：白卡改为扁平分区——透明底、无阴影无圆角，
   区与区之间用发丝线分隔；内边距保留，视觉密度不变。
   成绩面板 / 成长卡片 / 服务表单统一处理；课程表本身是表格不受影响。 */
@media (max-width: 767px) {
  .grades-view .panel,
  .service-view .sv-card {
    background: transparent !important;
    box-shadow: none !important;
    border-radius: 0 !important;
  }
}
.grades-view .panel + .panel,
.service-view .sv-card + .sv-card {
  border-top: 1px solid var(--sp-border, #e9ebee);
}

/* ===== 移动端子页设计 token（v3：「中性底 + 模块识别色」） =====
   用户明确否掉了纯黑白灰：需要有色彩，但不能再回到大面积铺色。
   规则（对标 Apple Health「白卡片 + 少量强调色指路」）：
   - 底色、卡片、文字仍是中性灰白，不做彩底；
   - 每个子页只认领**一个**低饱和识别色，仅用于：小图标、圆点、
     迷你图表的填充、进度条、当前项指示 —— 不得用于卡片背景或整块区域；
   - 状态色只有两个：需要关注（赭红）/ 已达成（墨绿）。
   三页识别色：课程表=赭橙（时间/安排）→ 成绩=青绿（结果）→ 成长=靛蓝（长期） */
.schedule-page {
  --sp-bg: #f5f6f7;
  --sp-surface: #ffffff;
  --sp-surface-muted: #fafbfc;
  --sp-ink: #14171a;
  --sp-ink-2: #5b6470;
  --sp-ink-3: #6b737c;
  /* --sp-ink-quiet 仅用于装饰性元素（箭头图标、分隔线、图表网格），**不得承载文字**：
     它在白卡上的对比度只有 2.24:1，达不到 WCAG 2.2 AA 的 4.5:1。
     原来这一档被用作 11px 的辅助说明文字，已统一改到 --sp-ink-3（4.81:1）。 */
  --sp-ink-quiet: #a8aeb6;
  --sp-border: #e9ebee;
  --sp-border-strong: #dcdfe4;
  --sp-warning: #c2410c;
  --sp-warning-soft: #fdf4ee;
  --sp-ok: #15803d;
  --sp-ok-soft: #eef7f1;
  --sp-radius-lg: 14px;
  --sp-radius-md: 11px;
  --sp-radius-sm: 8px;
  --sp-shadow-card: 0 1px 2px rgba(20, 23, 26, 0.035);
}
/* 每页一个识别色：--sp-accent / --sp-accent-soft / --sp-accent-ink */
.schedule-view { --sp-accent: #b45309; --sp-accent-soft: #fdf3e4; --sp-accent-ink: #8a3f07; }
/* 课程表的「今天」列底色跟随识别色，而不是原来的青色 #E5F8FC —
   那是 v1 蓝绿配色的残留，和赭橙识别色放在一起会显脏 */
.schedule-page { --dt-today-bg: #fdf3e4; }
.grades-view { --sp-accent: #0f7a58; --sp-accent-soft: #e8f5ef; --sp-accent-ink: #0a5b41; }
.growth-view { --sp-accent: #1a4fd6; --sp-accent-soft: #edf2fd; --sp-accent-ink: #143da3; }
/* 请假服务：石墨灰蓝（事务/服务语义，去彩色化），#3d4a57 在白底对比度 ≈ 9.4:1，AA+ */
.service-view { --sp-accent: #3d4a57; --sp-accent-soft: #f1f3f5; --sp-accent-ink: #2b3440; }

/* ===== 移动端：子页通用骨架（卡片 / 卡片头 / 图表容器） =====
   旧版每块各写一套圆角+阴影+渐变标题条，这组规则把它们收敛成一套。 */
@media (max-width: 767px) {
  /* 卡片：去描边改极淡阴影（描边多了页面会「发灰、发硬」） */
  .analytics-card,
  .content-card,
  .records-section {
    background: var(--sp-surface);
    border: 0;
    border-radius: var(--sp-radius-lg);
    box-shadow: var(--sp-shadow-card);
    margin-bottom: 10px;
  }
  /* 卡片头：色条 + 标题 + 副标题，去掉淡蓝渐变底 */
  .analytics-head {
    padding: 13px 14px 11px;
    gap: 7px;
    border-bottom: 0;
    background: transparent;
  }
  .analytics-head .head-bar {
    width: 3px;
    height: 13px;
    border-radius: 2px;
    background: var(--sp-accent);
  }
  .analytics-head .head-title { font-size: 14px; font-weight: 500; color: var(--sp-ink); }
  /* 副标题在移动端不是隐藏，而是降级为一行小字 —— Keep 式的「数据 + 一句解读」靠它 */
  .analytics-head .head-sub {
    display: block;
    font-size: 11px;
    color: var(--sp-ink-3);
    font-weight: 400;
    margin-left: auto;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 45%;
  }
  .analytics-body { padding: 0 14px 14px; }
  .analytics-body.duo { flex-direction: column; }
  .panel { flex: none; min-width: 0; }
  .panel-divider { display: none; }
  .panel-title { display: none; }
  .chart-unit { display: none; }

  /* 子页之间用 10px 的呼吸，而不是旧的 16~20px */
  .grades-view, .growth-view { display: flex; flex-direction: column; gap: 0; padding-bottom: 12px; }

  /* ───── 成长页 v3 组件 ─────
     统一命名 gv-*（growth view），只在移动端生效；桌面端沿用上面的旧版两栏结构。
     每个组件都遵循同一条约束：白卡 + 中性文字，色彩只出现在识别色的极小面积上。 */
  .gv-card,
  .gv-hero {
    background: var(--sp-surface);
    border: 1px solid var(--sp-border);
    border-radius: 14px;
    box-shadow: 0 1px 2px rgba(20, 23, 26, .04);
    margin-bottom: 10px;
  }
  .gv-card { padding: 13px 14px 14px; }

  /* 卡片头：标题 + 右侧一句结论（结论优先于图表，这是 Keep 的做法） */
  .gv-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; min-height: 18px; }
  .gv-card-title {
    font-size: 14px; font-weight: 500; color: var(--sp-ink);
    margin: 0; line-height: 1.2; flex: none;
  }
  .gv-card-meta {
    font-size: 11px; color: var(--sp-ink-3); line-height: 1.2;
    margin-left: auto; text-align: right;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .gv-text-btn {
    margin-left: auto; padding: 2px 8px; border: 0; border-radius: 6px;
    background: transparent; color: var(--sp-accent);
    font-size: 12px; cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .gv-text-btn:active { background: var(--sp-accent-soft); }
  .gv-card-meta + .gv-text-btn { margin-left: 2px; }

  /* ── 状态卡 ── */
  .gv-hero { padding: 14px; }
  .gv-hero-top { display: flex; align-items: flex-start; gap: 10px; }
  .gv-score { display: flex; align-items: center; gap: 11px; flex: 1; min-width: 0; }
  .gv-gauge { position: relative; width: 60px; height: 60px; flex: none; color: var(--sp-accent); }
  .gv-gauge-svg { width: 60px; height: 60px; display: block; transform: rotate(0deg); }
  .gv-gauge-svg circle { transition: stroke-dashoffset .7s cubic-bezier(.16,1,.3,1); }
  .gv-gauge-val {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    font-size: 17px; font-weight: 500; color: var(--sp-ink);
    font-variant-numeric: tabular-nums;
  }
  .gv-hero.tone-warning .gv-gauge { color: var(--sp-warning); }
  .gv-hero.tone-ok .gv-gauge { color: var(--sp-ok); }
  .gv-score-text { min-width: 0; }
  .gv-tier { font-size: 15px; font-weight: 500; color: var(--sp-ink); line-height: 1.25; }
  .gv-advice {
    font-size: 12px; color: var(--sp-ink-2); line-height: 1.45; margin-top: 3px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .gv-add {
    display: inline-flex; align-items: center; gap: 3px; flex: none;
    height: 30px; padding: 0 11px; border: 0; border-radius: 15px;
    background: var(--sp-accent-soft); color: var(--sp-accent-ink);
    font-size: 12px; font-weight: 500; cursor: pointer;
    transition: transform .18s ease, opacity .18s ease;
    -webkit-tap-highlight-color: transparent;
  }
  .gv-add:active { transform: scale(.96); opacity: .85; }

  /* 紧凑数字网格：4 列 × 2 行，总计约 96px（原来 7 个横排大字要 120px+ 且换行错乱） */
  .gv-metrics {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px; margin-top: 14px;
    background: var(--sp-border); border-radius: var(--sp-radius-sm); overflow: hidden;
  }
  .gv-metric {
    display: flex; flex-direction: column; align-items: center; gap: 1px;
    padding: 8px 2px 7px; background: var(--sp-surface-muted);
  }
  .gv-metric-val {
    font-size: 16px; font-weight: 500; color: var(--sp-ink); line-height: 1.15;
    font-variant-numeric: tabular-nums;
  }
  .gv-metric-label { font-size: 10px; color: var(--sp-ink-3); line-height: 1.2; }

  /* ── 坚持日历（Duolingo / GitHub 贡献图） ──
     格子改成正方形：宽度跟随列等分但上限 14px，高度由 aspect-ratio 跟随宽度，
     20 列 × 7 行 = 140 天，比原来 8 列 56 格更密、更小，也更容易看出「哪周断了」。
     注意不要去掉 max-width：桌面端列宽富余时会撑成巨墙。 */
  .gv-heat-body { display: flex; flex-direction: column; gap: 8px; }
  .gv-heat-grid { display: flex; gap: 3px; }
  .gv-heat-week { display: flex; flex-direction: column; align-items: center; gap: 3px; flex: 1 1 0; min-width: 0; }
  .gv-heat-cell {
    display: block; width: 100%; max-width: 14px; aspect-ratio: 1 / 1;
    border-radius: 3px; background: #eef0f3; flex: none;
  }
  .gv-heat-cell.lv-0 { background: #eef0f3; }
  .gv-heat-cell.lv-1 { background: color-mix(in srgb, var(--sp-accent) 32%, #ffffff); }
  .gv-heat-cell.lv-2 { background: color-mix(in srgb, var(--sp-accent) 62%, #ffffff); }
  .gv-heat-cell.lv-3 { background: var(--sp-accent); }
  /* 未来日期不渲染成灰块（否则像「一片空白」），直接留白 */
  .gv-heat-cell.lv--1 { background: transparent; box-shadow: inset 0 0 0 1px #f2f3f5; }
  .gv-heat-cell.is-today { box-shadow: 0 0 0 1.5px var(--sp-surface), 0 0 0 2.5px var(--sp-ink-quiet); }
  .gv-heat-foot { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--sp-ink-3); }
  .gv-heat-legend { display: flex; align-items: center; gap: 3px; margin-left: auto; }
  .gv-heat-legend .gv-heat-cell { width: 9px; height: 9px; max-width: none; aspect-ratio: auto; }

  /* ── 能力画像：小雷达与五维数字并排 ──
     雷达只占 96px 宽（原来 280px 高独占一屏），数字与横条在右侧读完。 */
  .gv-dim-body { display: flex; align-items: center; gap: 12px; }
  .gv-radar { width: 96px; height: 96px; flex: none; }
  .gv-radar-chart { width: 96px; height: 96px; }
  .gv-dim-list { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
  .gv-dim-row { display: flex; flex-direction: column; gap: 3px; }
  .gv-dim-top { display: flex; align-items: baseline; gap: 6px; }
  .gv-dim-name { font-size: 11px; color: var(--sp-ink-2); line-height: 1.2; }
  .gv-dim-val {
    margin-left: auto; font-size: 12px; font-weight: 500; color: var(--sp-ink);
    line-height: 1.2; font-variant-numeric: tabular-nums;
  }
  .gv-dim-track { height: 3px; border-radius: 2px; background: #eff1f4; overflow: hidden; }
  .gv-dim-fill { height: 100%; border-radius: 2px; background: var(--sp-accent); transition: width .5s cubic-bezier(.16,1,.3,1); }
  /* 最低项用赭红点出来 —— 但只有真的低于 80 分才警示，避免「全员红字」 */
  .gv-dim-row.is-low .gv-dim-fill { background: var(--sp-warning); }
  .gv-dim-row.is-low .gv-dim-val { color: var(--sp-warning); }
  .gv-insight {
    margin: 10px 0 0; padding-left: 9px;
    border-left: 2px solid var(--sp-border-strong);
    font-size: 11px; color: var(--sp-ink-3); line-height: 1.5;
  }

  /* ── 迷你图表：56px / 104px，配一句解读在后面 ── */
  .gv-mini { height: 56px; }
  .gv-mini-chart { width: 100%; height: 56px; }
  /* 折线比柱状多一行 x 轴标签，容器比图表高 6px，
     否则「5月」这类底行标签会被卡片 padding 边缘裁掉一半 */
  .gv-mini.is-line { height: 110px; }
  .gv-line-chart { width: 100%; height: 110px; }

  /* ── 记录 / 项目：行式列表，比卡片网格省一半高度 ── */
  .gv-record-list, .gv-project-list { display: flex; flex-direction: column; }
  .gv-record, .gv-project {
    display: flex; align-items: center; gap: 10px; width: 100%;
    padding: 9px 0; border: 0; border-bottom: 1px solid var(--sp-border);
    background: transparent; text-align: left; cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .gv-record:last-child, .gv-project:last-child { border-bottom: 0; }
  .gv-record:active, .gv-project:active { background: var(--sp-surface-muted); }
  .gv-record-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; }
  .gv-record-main, .gv-project-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .gv-record-title, .gv-project-name {
    font-size: 13px; font-weight: 500; color: var(--sp-ink); line-height: 1.3;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .gv-record-sub, .gv-project-sub {
    font-size: 11px; color: var(--sp-ink-3); line-height: 1.3;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .gv-record-arrow { color: var(--sp-ink-quiet); flex: none; }
  .gv-project-icon {
    width: 28px; height: 28px; border-radius: 8px; flex: none;
    display: flex; align-items: center; justify-content: center;
  }
  .gv-project-icon.team { background: var(--sp-accent-soft); color: var(--sp-accent-ink); }
  .gv-project-icon.solo { background: #f2f4f6; color: var(--sp-ink-2); }
  .gv-empty-text { margin: 2px 0 10px; font-size: 12px; color: var(--sp-ink-3); line-height: 1.5; }
  .gv-add-block {
    display: flex; align-items: center; justify-content: center; gap: 4px; width: 100%;
    height: 34px; margin-top: 10px; border: 1px dashed var(--sp-border-strong);
    border-radius: var(--sp-radius-sm); background: transparent;
    color: var(--sp-ink-2); font-size: 12px; cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .gv-add-block:active { background: var(--sp-surface-muted); }

  /* ── 技能与兴趣（移动端，v3 压缩版）──
     卡片只剩已选标签一行；预设区/自定义输入已移进编辑弹窗（桌面端同样生效）。 */
  .growth-view .skills-body { display: flex; flex-direction: column; gap: 10px; padding: 0; }
  .skills-body-compact { padding: 2px 14px 12px !important; gap: 0 !important; }
  .skills-body-compact .skills-tag-list { min-height: 26px; }
  .skills-body-compact .skills-tag { padding: 3px 10px; font-size: 11px; }
  .growth-view .skills-preset-section { background: var(--sp-surface-muted); border-radius: var(--sp-radius-sm); padding: 9px 10px; }
  .growth-view .skills-preset-label { font-size: 11px; font-weight: 400; color: var(--sp-ink-3); margin-bottom: 7px; }
  .growth-view .skills-tag-skill { background: var(--sp-accent-soft); color: var(--sp-accent-ink); border-color: transparent; }
  .growth-view .skills-tag-interest { background: #f2f4f6; color: var(--sp-ink-2); border-color: transparent; }
  .growth-view .skills-preset-tag { border-color: var(--sp-border); }
  .growth-view .skills-preset-tag.active { background: var(--sp-accent); border-color: var(--sp-accent); color: #fff; }

  /* ── AI 归纳标签：只读 + 点击展开来源证据 ── */
  .tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
  .ai-tag {
    display: inline-flex; align-items: center; gap: 4px; padding: 4px 9px;
    border: 1px solid transparent; border-radius: 999px; font-size: 11px;
    line-height: 1.2; cursor: pointer; -webkit-tap-highlight-color: transparent;
    transition: background .15s, box-shadow .15s;
  }
  .ai-tag.is-skill { background: var(--sp-accent-soft); color: var(--sp-accent-ink); }
  .ai-tag.is-interest { background: #f2f4f6; color: var(--sp-ink-2); }
  .ai-tag.active { box-shadow: inset 0 0 0 1px var(--sp-ink-quiet); }
  .ai-tag-count {
    font-size: 10px; min-width: 14px; padding: 0 4px; border-radius: 999px;
    background: rgba(255, 255, 255, .75); color: inherit; text-align: center;
  }
  .tag-evidence {
    margin-top: 10px; padding: 9px 10px; border-radius: var(--sp-radius-sm);
    background: var(--sp-surface-muted);
  }
  .tag-evidence-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .tag-evidence-head-title { font-size: 11px; color: var(--sp-ink-2); font-weight: 500; }
  .tag-evidence-close {
    margin-left: auto; border: 0; background: transparent; padding: 0;
    font-size: 11px; color: var(--sp-ink-3); cursor: pointer;
  }
  .tag-evidence-list { display: flex; flex-direction: column; }
  .tag-evidence-item {
    display: flex; align-items: flex-start; gap: 8px; padding: 6px 0;
    border-bottom: 1px solid var(--sp-border);
  }
  .tag-evidence-item:last-child { border-bottom: 0; padding-bottom: 0; }
  .tag-evidence-item:first-child { padding-top: 0; }
  .tag-evidence-label {
    flex: none; padding: 1px 6px; border-radius: 5px; font-size: 10px; line-height: 1.5;
    background: var(--sp-surface); border: 1px solid var(--sp-border); color: var(--sp-ink-3);
  }
  .tag-evidence-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .tag-evidence-title {
    font-size: 11px; color: var(--sp-ink); line-height: 1.3;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .tag-evidence-detail { font-size: 10px; color: var(--sp-ink-3); line-height: 1.4; }
  .tag-evidence-empty { margin: 0; font-size: 10px; color: var(--sp-ink-3); line-height: 1.5; }

  /* ───── 成绩页 v3 ───── */
  /* 四张彩色图标卡 → 一张卡内的 4 列指标；色块只留在图标底上。
     选择器带上 .grades-view 提高优先级：文件后半段的旧规则用同名选择器
     写了 repeat(2,1fr)，两者优先级相同、后定义的会赢，故此处必须更高。 */
  .grades-view .grade-stats-row {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0; margin-bottom: 10px;
    background: var(--sp-surface); border-radius: var(--sp-radius-lg);
    box-shadow: var(--sp-shadow-card); overflow: hidden;
  }
  .grades-view .grade-stat-card {
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
    padding: 13px 3px 12px; background: transparent; border: 0; border-radius: 0;
    box-shadow: none; position: relative; min-height: 0;
  }
  .grades-view .grade-stat-card + .grade-stat-card::before {
    content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
    width: 1px; height: 26px; background: var(--sp-border);
  }
  /* 模板结构是 .grade-stat-card > .stat-icon + .stat-info > (.stat-value + .stat-label)，
     旧规则按平铺选择器写会全部落空 —— 必须带上 .stat-info 这一层 */
  .grades-view .grade-stat-card .stat-icon { display: none; }
  .grades-view .grade-stat-card .stat-info {
    display: flex; flex-direction: column; align-items: center; gap: 1px; min-width: 0;
  }
  .grades-view .grade-stat-card .stat-value {
    font-size: 17px; font-weight: 500; color: var(--sp-ink); line-height: 1.2;
    font-variant-numeric: tabular-nums; white-space: nowrap;
  }
  .grades-view .grade-stat-card .stat-label {
    font-size: 10px; color: var(--sp-ink-3); line-height: 1.25;
    text-align: center; white-space: nowrap;
  }
  .grades-view .grade-stat-card .stat-help { display: none; }
  /* 触屏上点击不再浮起，改为轻微压暗 */
  .grades-view .grade-stat-card.stat-clickable:active { background: var(--sp-surface-muted); }
  /* 图表区：两栏并排 → 上下两块，每块 150px 高（原来各 200px） */
  .grades-view .chart { height: 118px; }

  /* 面板小标题（「学期绩点趋势」「分数段分布」）的图标默认是 Element 蓝，
     在青绿识别色的页里像一处漏色；统一到 --sp-accent，文字降到 11px / 500 字重，
     让标题不再和图表抢注意力。 */
  .grades-view .panel-title {
    display: flex; align-items: center; gap: 4px;
    margin-bottom: 2px;
    font-size: 11px; font-weight: 500; color: var(--sp-ink-3);
  }
  .grades-view .panel-title .el-icon { color: var(--sp-accent); font-size: 12px; }
  .grades-view .panel + .panel { margin-top: 0; }
  /* 移动端隐藏了 .panel-divider（竖分割线），两张图之间就只剩 0 间距，
     看起来像同一张图的两个区块。间距给到父容器的 gap 上更稳 ——
     因为 .panel 是 flex 子项，margin 在 flex 列布局里会被忽略。 */
  .grades-view .analytics-body.duo { gap: 14px; }
  .grades-view .analytics-card + .analytics-card { margin-top: 0; }
  /* 学期选择行 */
  .grades-view .sem-selector { gap: 9px; }
  .grades-view .sem-stats-inline { gap: 7px; }
  /* 成绩网格：更紧凑的行高 */
  .grade-card { border-radius: var(--sp-radius-sm); }
  .gc-name { font-size: 12px; }
}

/* ===== 移动端子页面：固定顶栏（Head） =====
   设计参考：Apple Health 分类详情页的导航栏（返回箭头 + 居中标题 + 极细分割线）
   + Keep 9.0 二级页（标题下带一行弱副标题）。
   硬约束：高度恒为 48px，三页一致；吸顶后**纹丝不动**，内容不得从它上下漏出来。

   三次修正的过程留在这里，避免以后又改回去：
   1) 旧版是 38px 圆角卡片、position: static，滚 600px 后 top 变成 -592，整条消失；
   2) 改成 sticky 后位置对了，但**父容器 .content-row 有 padding-top: 8px**，
      sticky 贴的是 padding 内边界，于是顶栏上方永远留一条 8px 缝，
      滚过去的卡片圆角从缝里露出来 —— 视觉上就是「顶栏悬空、没固定住」；
   3) 去掉父容器 padding 后仍有问题：sticky 只是「参与流的固定」，
      内容是从它**背后**滑过的，于是图表的「5月 / 6月」轴标签会贴着顶栏下沿露出来，
      像被裁了一半挂在标题底下。根因是滚动层只会裁到自己的边界，
      不会在顶栏底部多裁 48px。
   最终方案：**脱离滚动流**。顶栏改 position: fixed 钉在视口顶部，
   滚动内容用 padding-top 让出 48px，内容就永远滑不到它下面。
   底色改为实底（半透明会让内容从标题后透出来）。 */
.subpage-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  /* z-index 必须高于兄弟内容：父容器 .content-row 是 z-index:1500 的堆叠上下文，
     子元素的 z-index 只在**这个上下文内部**比较。
     写 20 时它低于同一上下文里创建了层叠的子页根节点（.growth-view 等有背景），
     结果滚动内容直接绘制到顶栏之上 —— 标题和下面的轴标签叠在一行，就是这个问题。
     抬到 100 后仍远低于 popup 基准（2000+），学期选择等弹层照常浮在上面。 */
  z-index: 100;
  display: flex;
  align-items: center;
  height: 48px;
  padding: 0 12px;
  margin: 0;
  box-sizing: border-box;
  background: var(--sp-surface, #ffffff);
  border-bottom: 1px solid var(--sp-border, #e9ebee);
}
/* 滚动内容从顶栏下沿「切」过去时，48px 柱状的边界不够明确，
   加一层极淡的投影把顶栏与内容分开（固定头部有浮起感才不会读成同一块） */
.subpage-bar::after {
  content: '';
  position: absolute;
  left: 0; right: 0; top: calc(100% + 4px);
  height: 5px;
  pointer-events: none;
  opacity: 0;
  background: linear-gradient(to bottom, rgba(20, 23, 26, 0.055), transparent);
  transition: opacity 0.2s ease;
}
.subpage-bar.is-scrolled::after { opacity: 1; }
.sp-side { display: flex; align-items: center; width: 48px; flex: none; }
/* 左槽不加 padding：40px 的返回按钮本身已含 20px 图标 + 四周留白，
   再叠 padding 会让内容右移，中槽标题随之偏左（实测 -4px）。
   两槽等宽 48px，标题才在父容器里几何居中。 */
.sp-left { justify-content: flex-start; }
.sp-back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--sp-ink, #14171a);
  cursor: pointer;
  transition: background 0.18s ease, transform 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}
.sp-back:active { background: rgba(20, 23, 26, 0.06); transform: scale(0.94); }
.sp-back:focus-visible { outline: 2px solid var(--sp-accent, #1a4fd6); outline-offset: 1px; }
.sp-title-wrap { flex: 1; min-width: 0; display: flex; align-items: center; justify-content: center; gap: 7px; }
.sp-dot { width: 6px; height: 6px; border-radius: 50%; flex: none; }
.sp-txt { display: flex; flex-direction: column; align-items: center; min-width: 0; }
.sp-sub {
  font-size: 9.5px; line-height: 1.1; margin-top: 1px;
  color: var(--sp-ink-3, #9aa0a8);
  max-width: 168px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
/* 滚动后收起副标题，Head 高度恒为 48px（避免布局跳动） */
.subpage-bar.is-scrolled .sp-sub { display: none; }
.sp-title { font-size: 16px; font-weight: 500; color: var(--sp-ink, #14171a); line-height: 1.15; letter-spacing: 0.01em; white-space: nowrap; }

/* ===== 页签切换动画 ===== */
.tab-fade-enter-active { transition: opacity .32s cubic-bezier(.16,1,.3,1), transform .32s cubic-bezier(.16,1,.3,1); }
.tab-fade-leave-active { transition: opacity .2s ease, transform .2s ease; }
.tab-fade-enter-from { opacity: 0; transform: translateY(14px) scale(.995); }
.tab-fade-leave-to { opacity: 0; transform: translateY(-8px) scale(.995); }

/* ===== 驾驶舱主页 ↔ 学业子页面（我的学业三个入口）：覆盖式滑入/滑出 =====
   动画实现已提取到 styles/animations.css 的 .subpage（全站唯一实现），本页无需再
   声明任何动画参数 —— 旧版的 --push-inset-t/--push-inset-x 是「传送带式」用来给
   离场页做内缩对齐的（离场页相对含 padding 的滚动容器 padding box 定位），
   新模型离场页用 inset:0 脱离文档流，不再需要这组变量，故一并移除。 */

/* ===== 右侧垂直标签栏 ===== */
.page-tabs { display: flex; flex-direction: column; gap: 6px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); padding: 8px; width: 96px; flex-shrink: 0; align-self: flex-start; position: sticky; top: 12px; }
.page-tab { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 14px 6px; border-radius: 10px; font-size: 12px; font-weight: 500; color: var(--text-secondary); cursor: pointer; transition: all 0.2s ease; letter-spacing: 0.5px; }
.page-tab .el-icon { font-size: 20px; transition: transform 0.2s ease; }
.page-tab:hover { background: var(--hover-bg, rgba(64,158,255,.06)); color: var(--accent-blue, #409eff); }
.page-tab:hover .el-icon { transform: translateY(-1px); }
.page-tab.active { background: linear-gradient(160deg, rgba(64,158,255,.16), rgba(64,158,255,.05)); color: var(--accent-blue, #409eff); font-weight: 600; box-shadow: 0 2px 8px rgba(64,158,255,.18); }
.page-tab.active .el-icon { transform: scale(1.08); }

/* ===== 两栏布局 ===== */
/* 覆盖式滑入时进场的是本容器，必须铺不透明底盖住下面的主页 ——
   （旧版由 animations.css 的 .push-enter-active 统一铺 #f5f6f7，统一到 .subpage 后
   该职责回到调用方，见 animations.css 注释「滑动的元素必须不透明」）。
   桌面端不参与过渡，此背景同样无害。 */
.content-row { display: flex; gap: 16px; flex: 1; min-height: 0; background: var(--dt-bg, #f5f6f7); }
.content-main { flex: 1; min-width: 0; max-width: 1200px; width: 100%; margin: 0 auto; display: flex; flex-direction: column; }

/* ===== 通用卡片 ===== */
.content-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); padding: 12px 16px 16px; }

/* ===== 课表工具栏 ===== */
.schedule-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.schedule-toolbar-title { font-size: 16px; font-weight: 700; color: #1a1a2e; white-space: nowrap; }
/* ===== 学期选择器 ===== */
.semester-tag { font-size: 13px; font-weight: 500; margin-left: auto; }
.semester-select { width: 190px; }
.semester-select :deep(.el-select__wrapper) {
  border-radius: 8px;
  padding: 4px 12px;
  min-height: 32px;
  background: #f5f7fa;
  box-shadow: 0 0 0 1px var(--border-color, #dcdfe6) inset;
  transition: box-shadow .25s ease, background .25s ease, transform .2s ease;
}
.semester-select :deep(.el-select__wrapper:hover) {
  transform: translateY(-1px);
  background: #fff;
  box-shadow: 0 0 0 1px #c0c4cc inset, 0 3px 10px rgba(0,0,0,.06);
}
.semester-select :deep(.el-select__wrapper.is-focused) {
  background: #fff;
  box-shadow: 0 0 0 1.5px var(--accent-blue, #409eff) inset, 0 3px 10px rgba(64,158,255,.12);
}
.semester-select :deep(.el-select__placeholder) { font-weight: 600; color: #1a1a2e; }
.semester-select :deep(.el-select__caret) { color: #909399; transition: transform .3s cubic-bezier(.16,1,.3,1); }
.semester-select :deep(.el-select__caret.is-reverse) { transform: rotate(180deg); }
/* 移动端成绩页：学期选择器改「平铺一行 + 右侧细箭头」，
   不再是一个内嵌灰底胶囊（放进白卡里像输入框，且和下方的指标胶囊重复了「块」的语义）。
   对照 Apple Health 的分类切换行：无边框、无底色，只靠一条底部细线分隔。 */
.grades-view .sem-selector .semester-select :deep(.el-select__wrapper) {
  min-height: 26px;
  padding: 0 2px;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
  font-size: 15px;
}
.grades-view .sem-selector .semester-select :deep(.el-select__wrapper:hover) {
  transform: none;
  background: transparent;
  box-shadow: none;
}
/* 键盘可达的焦点环不能删，这里改为描在行内文字下方的下划线 */
.grades-view .sem-selector .semester-select :deep(.el-select__wrapper.is-focused) {
  background: transparent;
  box-shadow: 0 1px 0 0 var(--sp-accent) inset;
}
.grades-view .sem-selector .semester-select :deep(.el-select__placeholder) {
  font-weight: 500;
  font-size: 15px;
  color: var(--sp-ink);
}
.grades-view .sem-selector .semester-select :deep(.el-select__caret) { color: var(--sp-ink-3); }
/* 门数/均分/均绩/学分：原为四个蓝色胶囊，改成一行极简标签，
   数值用深墨色 + 等宽数字，标签用 10px 灰字，读起来接近一句注释而不是四个按钮。 */
.grades-view .sem-stats-inline { gap: 0; }
.grades-view .sem-stats-inline > span {
  padding: 0;
  background: transparent;
  border-radius: 0;
  font-size: 10px;
  line-height: 16px;
  color: var(--sp-ink-3);
}
.grades-view .sem-stats-inline > span + span::before {
  content: '·';
  margin: 0 6px;
  color: var(--sp-border-strong);
}
.grades-view .sem-stats-inline b {
  margin-right: 2px;
  font-size: 12px;
  font-weight: 500;
  color: var(--sp-ink);
  font-variant-numeric: tabular-nums;
}
/* 当天列高亮 */
.schedule-table thead th.th-today { font-weight: 700; background: var(--dt-today-bg, #E5F8FC); }
.schedule-table .td-today { background: rgba(0,0,0,.025); }
.course-today { box-shadow: inset 0 0 0 1.5px rgba(180, 83, 9, .30); }
.week-nav { display: flex; align-items: center; gap: 6px; }
.week-nav-btn { width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-card); cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.week-nav-btn:hover { background: var(--accent-blue, #409eff); color: #fff; border-color: var(--accent-blue, #409eff); }
.week-label { font-size: 14px; font-weight: 600; color: #1a1a2e; min-width: 50px; text-align: center; }

/* ===== 课表表格 ===== */
.schedule-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
.holiday-box { padding: 80px 20px; text-align: center; }
.holiday-box .holiday-icon { font-size: 56px; margin-bottom: 12px; }
.holiday-box .holiday-title { font-size: 20px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.holiday-box .holiday-sub { font-size: 14px; color: #c0c4cc; }
.schedule-table th, .schedule-table td { border: 1px solid #ebeef5; text-align: center; vertical-align: middle; padding: 0; }
.schedule-table td { height: 60px; }
/* 课程格四周留白（原先是内联 padding：内联优先级高于媒体查询，移动端改不动它） */
.schedule-table td.cell-filled { padding: 4px; }
/* 节次列固定 76px（与表头内联宽度口径统一），星期列均分剩余宽度：
   周末无课时只渲染周一~周五，宽度自动分给这几列，不会留下空白 */
.schedule-table thead th:first-child, .schedule-table .period-cell { width: 76px; min-width: 76px; }
.schedule-table thead th { background: #f5f7fa; font-size: 14px; font-weight: 600; padding: 12px 8px; color: #303133; position: sticky; top: -12px; z-index: 2; }
.schedule-table .period-cell { background: #fafafa; padding: 12px 8px; font-size: 13px; }
.schedule-table .period-cell .period-name { font-weight: 700; font-size: 13px; color: #303133; }
.schedule-table .period-cell .period-time { font-size: 11px; color: #c0c4cc; margin-top: 2px; }
.schedule-course { height: 100%; box-sizing: border-box; border-radius: 6px; padding: 8px; margin: 0; border-left: 3px solid; text-align: left; display: flex; flex-direction: column; justify-content: center; }
.schedule-course .course-name,
  .schedule-course .course-teacher,
  .schedule-course .course-loc { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.schedule-course .course-name { font-weight: 600; font-size: 13px; margin-bottom: 2px; }
  .schedule-course .course-teacher,
  .schedule-course .course-loc { font-size: 11px; color: #909399; line-height: 1.4; }

/* ===== 课程悬浮详情 ===== */
.course-tip-layer { position: fixed; inset: 0; z-index: 2999; pointer-events: none; }
.course-tip { position: absolute; z-index: 3000; width: 220px; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--border-color); border-left: 4px solid; box-shadow: 0 8px 24px rgba(0,0,0,.14); font-size: 13px; color: #303133; line-height: 1.6; text-align: left; overflow: hidden; transform-origin: left center; pointer-events: auto; }
.course-tip .ct-name { font-weight: 700; font-size: 14px; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.course-tip .ct-detail { display: flex; gap: 6px; margin: 2px 0; overflow: hidden; }
.course-tip .ct-detail > :last-child { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.course-tip .ct-label { flex-shrink: 0; color: #909399; }

.course-tip-enter-active, .course-tip-leave-active { transition: opacity .18s ease, transform .18s cubic-bezier(.4,0,.2,1); }
.course-tip-enter-from, .course-tip-leave-to { opacity: 0; transform: translateY(6px) scale(.96); }

/* ===== AI 分析结果 Markdown 样式 ===== */
.ai-result-card :deep(.md-h2),
.ai-result-content :deep(.md-h2) { font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 16px 0 10px; padding-left: 10px; border-left: 4px solid #409eff; }
.ai-result-card :deep(.md-h3),
.ai-result-content :deep(.md-h3) { font-size: 16px; font-weight: 700; color: #1a1a2e; margin: 14px 0 8px; }
.ai-result-card :deep(.md-h4),
.ai-result-content :deep(.md-h4) { font-size: 15px; font-weight: 700; color: #1a1a2e; margin: 14px 0 8px; }
/* 成绩页右栏：考试 + AI 分析 */
.grades-side-col { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.side-exam-card { margin-bottom: 0 !important; }
.side-ai-card { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.side-ai-card .ai-result-card { max-height: 340px; overflow-y: auto; scrollbar-width: thin; }
.side-ai-card .ai-result-card::-webkit-scrollbar { width: 4px; }
.side-ai-card .ai-result-card::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.ai-side-body { padding: 14px 16px 16px !important; flex: 1; min-height: 0; display: flex; flex-direction: column; }
.ai-side-body .ai-placeholder { flex: 1; height: auto; }
.exam-list { display: flex; flex-direction: column; gap: 8px; padding-top: 14px !important; }
.ai-result-card :deep(.md-code-block code),
.ai-result-content :deep(.md-code-block code) { font-family: 'Consolas', 'Menlo', monospace; font-size: 13px; color: #333; }
.ai-result-card :deep(.md-inline-code),
.ai-result-content :deep(.md-inline-code) { background: #f0f2f5; border-radius: 4px; padding: 1px 6px; font-family: 'Consolas', 'Menlo', monospace; font-size: 13px; color: #c7254e; }
.ai-result-card :deep(.md-quote),
.ai-result-content :deep(.md-quote) { margin: 8px 0; padding: 8px 14px; border-left: 3px solid #e0e0e0; background: #fafafa; color: #909399; }
.ai-result-card :deep(.md-table),
.ai-result-content :deep(.md-table) { border-collapse: collapse; margin: 10px 0; width: 100%; }
.ai-result-card :deep(.md-table th),
.ai-result-card :deep(.md-table td),
.ai-result-content :deep(.md-table th),
.ai-result-content :deep(.md-table td) { border: 1px solid #e0e0e0; padding: 6px 10px; text-align: left; }
.ai-result-card :deep(.md-table th),
.ai-result-content :deep(.md-table th) { background: #f5f7fa; font-weight: 600; }
.ai-result-card :deep(strong),
.ai-result-content :deep(strong) { color: #1a1a2e; }

/* ===== 课程过渡动画 ===== */
.slide-left-enter-active, .slide-left-leave-active { transition: all .18s cubic-bezier(.4,0,.2,1); }
.slide-left-enter-from { opacity: 0; transform: translateX(30px); }
.slide-left-leave-to { opacity: 0; transform: translateX(-30px); }
.slide-right-enter-active, .slide-right-leave-active { transition: all .18s cubic-bezier(.4,0,.2,1); }
.slide-right-enter-from { opacity: 0; transform: translateX(-30px); }
.slide-right-leave-to { opacity: 0; transform: translateX(30px); }

/* ===== 成绩分析 ===== */
.grade-stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }
.grade-stat-card { background: var(--bg-card); border-radius: 14px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; border: 1px solid var(--border-color); box-shadow: var(--shadow-md); }
.grade-stat-card .stat-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.grade-stat-card .stat-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.grade-stat-card .stat-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; white-space: nowrap; }
.grade-stat-card .stat-help { font-size: 12px; vertical-align: -2px; color: var(--text-placeholder); }
.grade-stat-card.stat-clickable { cursor: pointer; transition: all .2s; }
.grade-stat-card.stat-clickable:hover { border-color: var(--accent-blue); box-shadow: 0 4px 14px rgba(64,158,255,.12); transform: translateY(-2px); }
.grade-stat-card.stat-clickable:hover .stat-help { color: var(--accent-blue); }
.grades-detail-row { display: grid; grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); gap: 16px; margin-bottom: 16px; align-items: stretch; }
.course-rank-scroll { display: flex; flex-direction: column; gap: 8px; max-height: 264px; overflow-y: auto; scrollbar-width: thin; }
.course-rank-scroll::-webkit-scrollbar { width: 4px; }
.course-rank-scroll::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.cr-group-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin: 4px 0 2px; }
.cr-group-label.good { color: #67c23a; }
.cr-group-label.weak { color: #f56c6c; margin-top: 12px; }
.course-rank-item { display: flex; align-items: center; gap: 10px; }
.cr-name { font-size: 13px; color: var(--text-primary); width: 110px; flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cr-bar { flex: 1; height: 8px; background: var(--border-light); border-radius: 4px; overflow: hidden; }
.cr-bar-inner { height: 100%; border-radius: 4px; transition: width .5s ease; }
.cr-bar-inner.good { background: linear-gradient(90deg, #67c23a, #95d475); }
.cr-bar-inner.weak { background: linear-gradient(90deg, #f56c6c, #fab6b6); }
.cr-score { font-size: 13px; font-weight: 700; width: 36px; text-align: right; flex-shrink: 0; }
.cr-score.good { color: #67c23a; }
.cr-score.weak { color: #f56c6c; }
.cr-empty { font-size: 12px; color: var(--text-placeholder); padding: 4px 0; }
.goal-list { display: flex; flex-direction: column; gap: 10px; }
.goal-item { background: var(--bg-page); border-radius: 12px; padding: 14px 18px; border: 1px solid var(--border-light); transition: transform .15s; }
.goal-item:hover { transform: translateY(-1px); }
.goal-item.is-current { border-left: 4px solid #67c23a; }
.goal-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.goal-sem-name { font-size: 14px; font-weight: 700; color: #1a1a2e; }
.goal-item-body { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.goal-item-left { display: flex; align-items: center; gap: 10px; }
.goal-item-right { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #666; }
/* 移动端专属：右下角绵小城（桌面隐藏） */
.grades-mascot { display: none; }
/* ===== 学期成绩明细：学期选择行（选择器 + 统计胶囊 + 查询链接） ===== */
.sem-selector { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
/* 宽度必须写死：el-select 默认 width:100% 会撑满整行，而 width:auto 在 flex 里会塌缩
   （内部 .el-select__selection 是 flex:1/min-width:0/overflow:hidden，按内容测量时为 0，
   整条只剩尾部箭头）。240px 足够容纳「2025-2026学年 第一学期」不被省略号截断 */
.sem-selector .semester-tag.semester-select { width: 240px; min-width: 0; margin-left: 0; flex: 0 0 auto; }
/* 门数/均分/均绩/学分：胶囊分组，避免四个指标连成一串裸文本 */
.sem-stats-inline { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.sem-stats-inline > span { display: inline-flex; align-items: baseline; gap: 4px; padding: 3px 10px; border-radius: 999px; background: rgba(64,158,255,.07); font-size: 12px; line-height: 18px; color: var(--text-secondary, #6b7280); white-space: nowrap; }
.sem-stats-inline b { color: #1a1a2e; font-weight: 700; }
.grade-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; margin-bottom: 20px; }
.grade-card { background: #fff; border-radius: 10px; padding: 14px 16px; border: 1px solid rgba(0,0,0,.04); box-shadow: 0 1px 6px rgba(0,0,0,.02); transition: transform .15s; border-left: 4px solid #ddd; }
.grade-card:hover { transform: translateY(-2px); }
/* 移动端（.grades-view 作用域）：科目卡的 4px 左侧色条原来是
   绿/蓝/橙/红四色并列，视觉上像四个互不相关的标签，且色相与「分数高低」没有直觉关联。
   v3 改成同一个青绿识别色的深浅梯度 —— 分数越高色条越深、越实，
   色相不跳，只在「深/浅」一个维度上承载有序信息。 */
.grades-view .grade-card { border-left-width: 3px; }
.grades-view .grade-card.level-a { border-left-color: #0f7a58; }
.grades-view .grade-card.level-b { border-left-color: #5aae8d; }
.grades-view .grade-card.level-c { border-left-color: #a8cdbd; }
.grades-view .grade-card.level-d { border-left-color: #d9e8e2; }
.grades-view .grade-card.level-f { border-left-color: #c2410c; }
.grades-view .grade-card-more {
  background: #f3f8f6; border: 1px dashed #cfe3db;
  border-left: 3px solid #0f7a58;
}
.grades-view .grade-card-more .more-text,
.grades-view .grade-card-more .more-icon { color: #0a5b41; }
.grades-view .grade-card-more .more-arrow { color: #a8cdbd; }
.grade-card-more { background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 100%); border: 1.5px solid #d0e0f5; cursor: pointer; transition: all .25s ease; border-left: 4px solid #409eff; }
.grade-card-more:hover { background: linear-gradient(135deg, #e0ecff 0%, #d4e6ff 100%); border-color: #409eff; border-left-color: #409eff; box-shadow: 0 4px 14px rgba(64,158,255,.18); transform: translateY(-2px); }
.grade-card-more .more-text { color: #409eff; }
.grade-card-more .more-icon { color: #409eff; margin-right: 4px; }
.grade-card-more .more-arrow { color: #a0c4ff; transition: transform .2s; }
.grade-card-more:hover .more-arrow { transform: translateX(3px); color: #409eff; }
.grade-grid-all { grid-template-columns: repeat(4, minmax(160px, 1fr)) !important; max-height: 60vh; overflow-y: auto; padding: 4px; }
.gc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.gc-name { font-size: 14px; font-weight: 600; color: #1a1a2e; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gc-score { font-size: 22px; font-weight: 700; flex-shrink: 0; margin-left: 8px; }
/* 分数数字的配色（v3）。
   旧版：≥90 绿 / ≥80 蓝 / ≥70 橙 / 不及格红 —— 四种色相混在同一张网格里，
   既与青绿识别色冲突，又让「80 分的蓝」和旁边卡片的蓝色图标读起来是同一件事。
   现在同一个色相里用「深→浅」表达高低，只有不及格保留赭红（颜色之外还有边框与分数本身）。
   移动端用 .grades-view 前缀覆盖，桌面端保持原样。 */
.level-a .gc-score { color: #67c23a; }
.level-b .gc-score { color: #409eff; }
.level-c .gc-score { color: #e6a23c; }
.level-d .gc-score { color: #f56c6c; }
.level-f .gc-score { color: #c03636; }
.grades-view .level-a .gc-score { color: #0a5b41; }
.grades-view .level-b .gc-score { color: #0f7a58; }
/* 70-79 段用中墨色而不是浅灰：浅灰在白卡上读起来像「被禁用」，
   而 78 分在现实语境里是需要被看见的分数，只是不必和 92 分抢眼。 */
.grades-view .level-c .gc-score { color: #4a5a54; }
.grades-view .level-d .gc-score { color: #7c8a84; }
.grades-view .level-f .gc-score { color: #c2410c; }
/* 即将考试卡的日期数字：原为品牌蓝，与青绿识别色冲突，改用墨色靠字重区分 */
.grades-view .ec-date { color: var(--sp-ink); font-weight: 500; font-size: 18px; }
.gc-meta { display: flex; gap: 12px; font-size: 12px; color: #999; }
.exam-card { display: flex; gap: 16px; background: var(--bg-page); border-radius: 12px; padding: 12px 16px; border: 1px solid var(--border-light); transition: transform .15s; }
.exam-card:hover { transform: translateY(-1px); }
.ec-left { text-align: center; flex-shrink: 0; width: 80px; padding: 4px 0; }
.ec-date { font-size: 20px; font-weight: 700; color: #409eff; }
.ec-time { font-size: 12px; color: #999; margin-top: 2px; }
.ec-body { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 4px; }
.ec-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.ec-location { font-size: 13px; color: #888; display: flex; align-items: center; gap: 4px; }

/* ===== 成长轨迹 ===== */
.growth-view { display: flex; flex-direction: column; }
.score-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 28px; margin-bottom: 20px; background: var(--gradient-card); border-radius: 16px; border: 1px solid var(--border-color); }
.score-ring-group { display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
.score-ring { position: relative; width: 110px; height: 110px; flex-shrink: 0; }
.score-svg { width: 110px; height: 110px; display: block; }
.score-center { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-value { font-size: 28px; font-weight: 700; color: var(--accent-blue); line-height: 1; }
.score-label { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
.score-stats { display: grid; grid-template-columns: repeat(7, max-content); gap: 20px 28px; }
.stat-item { display: flex; flex-direction: column; align-items: center; min-width: 0; }
.stat-num { font-size: 26px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.score-mascot { position: relative; flex-shrink: 0; width: 96px; height: 96px; display: flex; align-items: center; justify-content: center; }
.score-mascot img { width: 100%; height: 100%; object-fit: contain; pointer-events: none; user-select: none; -webkit-user-select: none; -webkit-user-drag: none; }
.growth-two-col { display: flex; gap: 16px; }
.growth-left-col { flex: 1; min-width: 0; }
.growth-right-col { width: 360px; flex-shrink: 0; }
.analytics-card {
  background: var(--bg-card);
  border-radius: 18px;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-md);
  margin-bottom: 16px;
  overflow: hidden;
}
.analytics-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-light);
  background: linear-gradient(180deg, var(--hover-bg) 0%, rgba(64,158,255,0) 100%);
}
.head-bar {
  width: 4px;
  height: 16px;
  border-radius: 2px;
  flex-shrink: 0;
  background: linear-gradient(180deg, var(--accent-blue) 0%, var(--accent-green) 100%);
}
.head-title { font-size: 15px; font-weight: 700; color: var(--text-primary); line-height: 1; }
/* 折叠开关箭头：仅移动端的「课程画像」使用，桌面端卡片恒为展开态 */
.head-toggle { display: none; }
.head-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1;
  margin-left: 2px;
}
.head-save { margin-left: auto; }
/* 学期选择行右侧的轻量链接 */
.sem-link-action { display: inline-flex; align-items: center; gap: 5px; margin-left: auto; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 500; color: var(--accent-blue, #409eff); background: var(--hover-bg, rgba(64,158,255,.06)); text-decoration: none; white-space: nowrap; transition: all .2s ease; flex-shrink: 0; }
.sem-link-action:hover { background: rgba(64,158,255,.12); color: #337ecc; transform: translateY(-1px); }
.analytics-body { padding: 18px 20px 20px; }
.analytics-body.duo { display: flex; align-items: stretch; }
.panel { flex: 1; min-width: 0; }
.panel-radar { flex: 5; }
.panel-bar { flex: 7; }
.panel-divider {
  width: 1px;
  margin: 2px 22px;
  background: var(--border-light);
  flex-shrink: 0;
}
.panel-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600;
  color: var(--text-secondary);
  line-height: 1;
  margin-bottom: 12px;
}
.panel-title .el-icon {
  color: var(--accent-blue);
  font-size: 14px;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
.chart-unit {
  font-size: 12px;
  color: var(--text-placeholder, #909399);
  line-height: 1;
  margin: -6px 0 8px 20px;
}
.radar-chart { height: 280px; }
.line-chart { height: 230px; }
.pie-chart { height: 230px; }
.chart { width: 100%; height: 220px; }
/* 标签删除动画 */
.tag-fade-leave-active { transition: all .25s ease; }
.tag-fade-leave-to { opacity: 0; transform: scale(.85); }
/* 空状态文字淡入 */
.empty-fade-enter-active { transition: all .3s ease; }
.empty-fade-enter-from { opacity: 0; transform: translateY(-6px); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; font-size: 15px; font-weight: 600; color: var(--text-primary); }
.section-header-title { display: flex; align-items: center; line-height: 1; }
/* 技能与兴趣（重设计）。v3 起移动端卡片压缩为「已选标签一行」，
   预设与自定义输入移入编辑弹窗；紧凑态 .skills-body-compact 的内边距
   以 3 个类的优先级压过本条（详见移动端块内注释）。 */
.skills-card .skills-body { display: flex; flex-direction: column; gap: 14px; padding: 14px 16px !important; }
.skills-card .skills-body.skills-body-compact { gap: 0 !important; padding: 2px 14px 12px !important; }
.skills-selected-title { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }
.skills-tag-list { display: flex; flex-wrap: wrap; gap: 8px; min-height: 28px; }
.skills-tag { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500; cursor: pointer; transition: all .2s; }
.skills-tag-skill { background: #ecf5ff; color: #409eff; border: 1px solid #d9ecff; }
.skills-tag-skill:hover { background: #d9ecff; }
.skills-tag-interest { background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8; }
.skills-tag-interest:hover { background: #e1f3d8; }
.skills-tag-close { font-size: 11px; opacity: .5; transition: opacity .15s; }
.skills-tag:hover .skills-tag-close { opacity: 1; }
.skills-empty { font-size: 12px; color: var(--text-placeholder); line-height: 28px; }
.skills-preset-group { display: flex; flex-direction: column; gap: 10px; }
.skills-preset-section { background: var(--hover-bg); border-radius: 10px; padding: 10px 12px; }
.skills-preset-label { display: flex; align-items: center; font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; line-height: 1; }
.skills-preset-label .el-icon { font-size: 14px; vertical-align: middle; }
.skills-preset-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.skills-preset-tag { padding: 3px 10px; border-radius: 12px; font-size: 12px; color: #909399; background: #fff; border: 1px solid #e4e7ed; cursor: pointer; transition: all .15s; user-select: none; }
.skills-preset-tag:hover { color: #409eff; border-color: #b3d8ff; background: #ecf5ff; }
.skills-preset-tag.active { color: #fff; background: #409eff; border-color: #409eff; }
.skills-custom { display: flex; align-items: center; gap: 8px; }
.skills-custom :deep(.el-input__wrapper) { border-radius: 8px; box-shadow: 0 0 0 1px #dcdfe6 inset; transition: box-shadow .2s; }
.skills-custom :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #c0c4cc inset; }
.skills-custom :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #409eff inset; }
.skills-custom :deep(.el-radio-button__inner) { font-size: 12px; padding: 5px 12px; }
/* 成长记录详情弹窗 */
.record-detail-dialog .rd-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.record-detail-dialog .rd-date { font-size: 13px; color: #909399; }
.record-detail-dialog .rd-desc { font-size: 14px; color: #606266; line-height: 1.7; margin-bottom: 16px; padding: 12px 14px; background: #f5f7fa; border-radius: 8px; }
.record-detail-dialog .rd-fields { display: flex; flex-direction: column; gap: 10px; }
.record-detail-dialog .rd-field { display: flex; align-items: center; gap: 8px; }
.record-detail-dialog .rd-label { font-size: 13px; color: #909399; min-width: 64px; flex-shrink: 0; }
.record-detail-dialog .rd-value { font-size: 14px; color: #303133; font-weight: 500; }
.records-section { margin-bottom: 24px; background: var(--bg-card); border-radius: 18px; border: 1px solid var(--border-color); box-shadow: var(--shadow-md); padding: 18px 20px; }
.records-list { display: flex; flex-direction: column; gap: 8px; }
.records-scroll { max-height: 420px; overflow-y: auto; scrollbar-width: thin; }
.records-scroll::-webkit-scrollbar { width: 4px; }
.records-scroll::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.record-card { display: flex; gap: 14px; padding: 14px 16px; background: var(--bg-page); border-radius: 12px; border: 1px solid var(--border-light); transition: all 0.2s; }
.record-card-clickable { cursor: pointer; }
.record-card-clickable:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.08); border-color: rgba(64,158,255,.2); }
.record-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.record-left { display: flex; flex-direction: column; align-items: center; width: 12px; flex-shrink: 0; padding-top: 6px; }
.record-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.record-body { flex: 1; min-width: 0; }
.record-top { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.record-date { font-size: 11px; color: var(--text-placeholder); }
.record-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
.record-meta { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 4px; }
.record-details { display: flex; gap: 8px; flex-wrap: wrap; }
.detail-item { font-size: 12px; color: var(--text-muted); }
.projects-section { margin-bottom: 24px; background: var(--bg-card); border-radius: 18px; border: 1px solid var(--border-color); box-shadow: var(--shadow-md); padding: 18px 20px; }
.project-grid { display: grid; grid-template-columns: 1fr; gap: 14px; }
.project-card { background: var(--bg-page); border-radius: 12px; padding: 16px 18px; border: 1px solid var(--border-light); transition: all 0.2s; }
.project-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.project-top { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.project-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.project-icon.team { background: rgba(64,158,255,.1); color: var(--accent-blue); }
.project-icon.solo { background: rgba(103,194,58,.1); color: var(--accent-green); }
.project-info { flex: 1; min-width: 0; }
.project-name { font-size: 14px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.project-date { font-size: 11px; color: var(--text-placeholder); margin-top: 2px; }
.project-members { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
.project-attach { margin-bottom: 8px; }
.project-actions { display: flex; gap: 4px; margin-top: 6px; padding-top: 8px; border-top: 1px solid var(--border-light); }

/* ===== AI 相关 ===== */
.ai-result-card { background: linear-gradient(135deg, #f8f9ff 0%, #f0f5ff 100%); border-radius: 12px; padding: 20px 24px; border: 1px solid rgba(64,158,255,.15); box-shadow: 0 2px 12px rgba(64,158,255,.08); max-height: 420px; overflow-y: auto; }
.ai-result-content { font-size: 14px; line-height: 1.8; color: #333; word-break: break-word; }
.ai-result-content :deep(p.md-p) { margin: 6px 0; }
.ai-result-content :deep(h1), .ai-result-content :deep(h2), .ai-result-content :deep(h3), .ai-result-content :deep(h4) { font-weight: 600; color: #1a1a2e; margin: 16px 0 8px; padding-bottom: 8px; border-bottom: 1px solid rgba(64,158,255,.1); }
.ai-result-content :deep(h1) { font-size: 20px; }
.ai-result-content :deep(h2) { font-size: 18px; }
.ai-result-content :deep(h3) { font-size: 16px; }
.ai-result-content :deep(h4) { font-size: 15px; }
.ai-result-content :deep(h1:first-child), .ai-result-content :deep(h2:first-child), .ai-result-content :deep(h3:first-child), .ai-result-content :deep(h4:first-child) { margin-top: 0; }
.ai-result-content :deep(strong) { color: #409eff; font-weight: 600; }
.ai-result-content :deep(em) { font-style: italic; color: #555; }
.ai-result-content :deep(del) { text-decoration: line-through; color: #999; }
.ai-result-content :deep(ul.md-ul), .ai-result-content :deep(ol.md-ol) { margin: 8px 0; padding-left: 24px; }
.ai-result-content :deep(li.md-li) { margin: 4px 0; color: #555; line-height: 1.7; }
.ai-result-content :deep(a.md-link) { color: #409eff; text-decoration: none; border-bottom: 1px dashed rgba(64,158,255,.4); }
.ai-result-content :deep(a.md-link:hover) { border-bottom-color: #409eff; }
.ai-result-content :deep(code.md-inline-code) { background: rgba(64,158,255,.08); color: #e6a23c; padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: 'Consolas', 'Monaco', monospace; }
.ai-result-content :deep(pre.md-code-block) { background: #1e1e2e; color: #cdd6f4; padding: 14px 18px; border-radius: 8px; overflow-x: auto; margin: 10px 0; font-size: 13px; line-height: 1.6; }
.ai-result-content :deep(pre.md-code-block code) { background: none; color: inherit; padding: 0; font-family: 'Consolas', 'Monaco', monospace; }
.ai-result-content :deep(blockquote.md-blockquote) { border-left: 4px solid #409eff; margin: 10px 0; padding: 8px 16px; background: rgba(64,158,255,.05); border-radius: 0 8px 8px 0; color: #555; }
.ai-result-content :deep(hr.md-hr) { border: none; border-top: 1px solid #e8e8e8; margin: 16px 0; }
.ai-result-content :deep(table.md-table) { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }
.ai-result-content :deep(th.md-th), .ai-result-content :deep(td.md-td) { border: 1px solid #e8e8e8; padding: 8px 12px; text-align: left; }
.ai-result-content :deep(th.md-th) { background: #f5f7fa; font-weight: 600; color: #1a1a2e; }
.ai-result-content :deep(tr.md-tr:hover) { background: rgba(64,158,255,.03); }
.ai-result-content :deep(img.md-image) { max-width: 100%; border-radius: 8px; margin: 8px 0; }
.ai-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 40px 20px; background: #fafafa; border-radius: 12px; border: 1px dashed #e0e0e0; height: calc(100% - 60px); }
.ai-placeholder p { font-size: 14px; color: #999; margin: 0; text-align: center; }
.ai-placeholder-small { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 20px; background: #fafafa; border-radius: 12px; border: 1px dashed #e0e0e0; }
.ai-placeholder-small p { font-size: 13px; color: #999; margin: 0; }
.ai-loading-card { background: linear-gradient(135deg, #f8f9ff 0%, #f0f5ff 100%); border-radius: 12px; padding: 20px 24px; border: 1px solid rgba(64,158,255,.15); }
.ai-loading-header { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #409eff; font-weight: 500; margin-bottom: 16px; }
.ai-loading-skeleton { display: flex; flex-direction: column; gap: 10px; }
.skeleton-line { height: 14px; border-radius: 7px; background: linear-gradient(90deg, #e8edf3 25%, #d5dce6 50%, #e8edf3 75%); background-size: 200% 100%; animation: shimmer 1.5s ease-in-out infinite; }
.ai-refresh-bar { display: flex; align-items: center; gap: 6px; padding: 6px 12px; margin-bottom: 10px; background: rgba(64,158,255,.06); border-radius: 8px; font-size: 12px; color: #409eff; }
.loading-box { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 40px; color: #409eff; }

@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* ===== Dialog ===== */
:deep(.el-dialog__body) { padding: 20px 24px; }
.formula-dialog { max-height: 86vh; display: flex; flex-direction: column; }
.formula-dialog :deep(.el-dialog__header) { padding: 12px 20px 8px; flex-shrink: 0; }
.formula-dialog :deep(.el-dialog__footer) { padding: 8px 20px 12px; flex-shrink: 0; }
.formula-dialog :deep(.el-dialog__body) { flex: 1; min-height: 0; max-height: 42vh; overflow-y: auto; padding: 10px 20px; scrollbar-width: thin; }
.formula-dialog :deep(.el-dialog__body::-webkit-scrollbar) { width: 6px; }
.formula-dialog :deep(.el-dialog__body::-webkit-scrollbar-thumb) { background: #d0d5dd; border-radius: 4px; }
.formula-tip { display: flex; align-items: flex-start; gap: 6px; font-size: 12px; line-height: 1.6; color: var(--text-secondary); background: rgba(64,158,255,.06); border-radius: 8px; padding: 8px 10px; margin-bottom: 10px; }
.formula-tip .el-icon { color: #409eff; margin-top: 3px; flex-shrink: 0; }
.formula-tip b { color: #1a1a2e; }
.formula-block { background: #f8f9fa; border: 1px solid #ebeef5; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; }
.formula-title { font-size: 13px; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; }
.formula-line { background: #fff; border: 1px dashed #d0d7e2; border-radius: 8px; padding: 6px 10px; font-size: 12px; color: #303133; line-height: 1.6; word-break: break-all; }
.formula-sub { font-size: 12px; color: var(--text-muted); margin-top: 8px; }
.formula-sub b { color: #409eff; }
/* 计算规则弹窗：课程明细表 + 维度卡（原本夹在两个媒体块之间被误删，这里按原样补回） */
.formula-table-wrap { max-height: 150px; overflow-y: auto; scrollbar-width: thin; }
.formula-table-wrap::-webkit-scrollbar { width: 4px; }
.formula-table-wrap::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.formula-table { width: 100%; border-collapse: collapse; font-size: 12px; background: #fff; }
.formula-table th, .formula-table td { border: 1px solid #ebeef5; padding: 5px 8px; text-align: left; }
.formula-table thead th { background: #f5f7fa; font-weight: 600; color: #606266; }
.formula-table .ft-name { font-weight: 600; color: #303133; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.formula-table .ft-gpa { font-weight: 700; color: #409eff; }
.formula-table .ft-gpa.low { color: #f56c6c; }
.formula-dims { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.formula-dim { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; padding: 6px 10px; }
.fd-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.fd-name { font-size: 12px; font-weight: 600; color: #1a1a2e; }
.fd-value { font-size: 12px; font-weight: 700; color: #409eff; }
.fd-bar { height: 6px; background: #f0f2f5; border-radius: 3px; overflow: hidden; margin-bottom: 4px; }
.fd-bar-inner { height: 100%; border-radius: 3px; transition: width .5s ease; }
.fd-formula { font-size: 11px; color: var(--text-muted); word-break: break-all; }
.all-records-scroll { max-height: 60vh; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; scrollbar-width: thin; }
.all-records-scroll::-webkit-scrollbar { width: 4px; }
.all-records-scroll::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }

/* ===== 移动端适配 =====
   原先被拆成两个 @media (max-width: 767px) 块且有 22 条完全重复的声明，
   这里合并为一块：只在该媒体块生效的规则（v-if="!isMobile" 的 .page-tabs、
   已废弃的 .semester-link / .semester-action-card 等）已删除。 */
  /* ── 请假服务子页（v3）──
     分段控制：三枚等宽按钮，选中态用识别色胶囊；表单全部收进一张白卡。
     Element 表单控件在此前的全局主题里偏桌面（32px 高、16px 字），这里统一压到移动尺寸。 */
  .service-view { display: flex; flex-direction: column; gap: 12px; padding-bottom: 16px; }
  .sv-segment {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;
    background: #ececef; border-radius: 10px; padding: 3px;
  }
  .sv-seg-item {
    height: 34px; border: 0; border-radius: 8px; background: transparent;
    font-size: 13px; font-weight: 500; color: var(--sp-ink-2); cursor: pointer;
    transition: background .18s ease, color .18s ease, box-shadow .18s ease;
    -webkit-tap-highlight-color: transparent;
  }
  .sv-seg-item:active { transform: scale(.97); }
  .sv-seg-item.active {
    background: var(--sp-surface); color: var(--sp-accent-ink); font-weight: 600;
    box-shadow: 0 1px 3px rgba(20, 23, 26, .10);
  }
  .sv-seg-item:focus-visible { outline: 2px solid var(--sp-accent); outline-offset: 1px; }
  .sv-card {
    background: var(--sp-surface, #ffffff); border-radius: var(--sp-radius-lg, 16px);
    box-shadow: var(--sp-shadow-card, 0 1px 2px rgba(20,23,26,.04)); padding: 14px;
    display: flex; flex-direction: column; gap: 12px;
  }
  .sv-tip {
    display: flex; align-items: center; gap: 6px;
    padding: 8px 10px; border-radius: var(--sp-radius-sm);
    background: var(--sp-accent-soft); font-size: 11px; color: var(--sp-accent-ink);
  }
  .sv-tip .el-icon { flex: none; }
  .sv-field { display: flex; flex-direction: column; gap: 5px; }
  .sv-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .sv-label { font-size: 12px; font-weight: 500; color: var(--sp-ink-2); line-height: 1.2; }
  .sv-files { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
  /* Element 控件移动端紧凑化：高度 36px、字号 13px、边框收中性灰 */
  .sv-card :deep(.el-input__wrapper),
  .sv-card :deep(.el-select__wrapper),
  .sv-card :deep(.el-textarea__inner) { border-radius: 9px; box-shadow: 0 0 0 1px var(--sp-border-strong) inset; }
  .sv-card :deep(.el-input__wrapper.is-focus),
  .sv-card :deep(.el-select__wrapper.is-focused),
  .sv-card :deep(.el-textarea__inner:focus) { box-shadow: 0 0 0 1.5px var(--sp-accent) inset; }
  .sv-card :deep(.el-input__inner) { font-size: 13px; }
  .sv-card :deep(.el-select__placeholder) { font-size: 13px; }
  .sv-card :deep(.el-textarea__inner) { font-size: 13px; padding: 8px 11px; }
  .sv-card :deep(.el-input-number) { width: 100%; }
  .sv-card :deep(.el-input-number .el-input__inner) { text-align: left; }
  .sv-submit {
    height: 44px; border: 0; border-radius: 11px;
    background: var(--sp-accent); color: #fff;
    font-size: 15px; font-weight: 600; cursor: pointer;
    transition: transform .15s ease, opacity .15s ease;
    -webkit-tap-highlight-color: transparent;
  }

@media (max-width: 767px) {
  .schedule-page { padding: 8px 12px 0; --sp-pad-t: 8px; --sp-pad-x: 12px; }
  /* 主页：整页滚动容器给固定 Head 让出高度（Head 48 + 4 遮罩带） */
  .schedule-page:not(.has-subpage) { padding-top: 48px; }
  .dashboard-home { gap: 0; }
  .content-main { max-width: 100%; }
  .content-row { flex-direction: column; }
  /* 移动端覆盖式布局（仅在子页激活时生效，见下方 .has-subpage 条件）。
     - 显示主页时：主页留在流内撑起 .schedule-page 的滚动高度，仪表盘正常滚动；
     - 显示子页时：子页（.content-row）整屏覆盖 —— 与资讯搜索/详情子页同一形式，
       滑入/滑出时连顶部页头与底部导航一起盖住。子页脱离整页滚动容器后自成滚动区
       （overflow-y:auto），长内容（课程表/成绩列表）在子页内滚动。
     注意 fixed 规则**不能**挂在 .has-subpage 下：返回时 activeTab 先变、has-subpage
     先移除，而滑出动画还在播 —— 挂在条件下会让子页在动画第一帧从整屏跳回流内。
     该元素本身只在子页态渲染（模板 v-if），不加条件等价且动画期间保持整屏。
     主页滑出时绝对定位垫在下层（见下），被完全盖住不需要滚动，原地露出即可。
     z-index 1500：盖过底部导航(1000)，低于 Element Plus 弹层基准(2000+)，
     学期选择/日期等弹出层仍浮在子页之上。 */
  .schedule-page.has-subpage .dashboard-home {
    position: absolute;
    top: var(--sp-pad-t, 8px);
    left: var(--sp-pad-x, 12px);
    right: var(--sp-pad-x, 12px);
    z-index: 1;
  }
  /* 顶栏 fixed 后不占流内空间。滚动区必须**自己**让出 48px：
     只给内容加 padding-top 是不够的 —— 内容滚到顶时第一个像素仍在 y=0，
     紧接着「5月 / 6月」这行轴标签会穿过顶栏下沿露在标题下面（这就是「顶栏没固定住」的观感来源）。
     把 top 设成 48px 后，滚动区从顶栏下沿开始，内容被真正裁在顶栏之上。
     水平 12px 交给 .content-main，顶栏自己负责左右内边距。 */
  .content-row {
    position: fixed;
    top: 48px;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 1500;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    padding: 0;
    box-sizing: border-box;
  }
  .content-row .content-main { padding: 0 12px; }
  /* 顶部留白给到 14px：滚动时上一张卡的圆角顶边会从这个缝里划过，
     8px 时露出一条白色弧线，看着像顶栏底部有毛边。加宽后弧线落在阴影带里，不再显眼。 */
  .content-row .content-main > .schedule-view,
  .content-row .content-main > .grades-view,
  .content-row .content-main > .growth-view,
  .content-row .content-main > .service-view,
  .content-row .content-main > .plan-view-wrap { padding-top: 14px; }

  /* ── 学习计划子页（v4）：PlanView 以 embedded 模式流进本页滚动区 ── */
  .plan-view-wrap { padding-bottom: 16px; }
  .plan-view-wrap :deep(.plan-page) {
    max-width: 100%; height: auto; overflow: visible;
    background: transparent; padding: 0 0 8px;
  }

  .sv-submit:active { transform: scale(.98); opacity: .92; }
  .sv-submit:disabled { opacity: .55; cursor: default; }
  .sv-submit:focus-visible { outline: 2px solid var(--sp-accent-ink); outline-offset: 2px; }

  /* ── 教学安排工具栏 ── */
  .schedule-toolbar { flex-direction: row; flex-wrap: wrap; align-items: center; row-gap: 8px; }
  .schedule-toolbar .schedule-toolbar-title { flex: 1 0 100%; }
  /* 标题独占一行；学期选择器紧贴周次导航右侧。
     wrap 容器是否换行只看 flex-basis：basis 用小值(100px)保证通过换行判定，
     grow:1 拉伸填满剩余空间——标签已缩短，拉伸后宽度 ≈ 内容宽，无明显空白；空间不足时收缩省略 */
  .schedule-toolbar .semester-tag.semester-select { width: auto; min-width: 0; margin-left: 0; flex: 1 1 100px; }
  .schedule-toolbar .semester-tag.semester-select :deep(.el-select__selected-item) { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  /* 「回到本周」浮到卡片右上角（标题行右侧空位），脱流不占行宽、不撑行高，周次 + 学期独占一行 */
  .schedule-toolbar .reset-week-btn { position: absolute; top: 12px; right: 16px; margin: 0; height: 24px; line-height: 24px; padding: 0 8px; }
  /* 30px 的周次按钮在触屏上太小，放大到 40px */
  .week-nav-btn { width: 40px; height: 40px; }

  /* ── 移动端课表 ──
     周末无课时不渲染周六/周日两列（见 visibleDays，仅移动端生效），宽度全部给周一~周五：
     375px 下每列从 ~41px 提升到 ~57px，课程名与教室才读得出来 */
  /* v6：课表格子放大（56 → 76px），节次列 34 → 44px。
     一格能完整容下「课程名 2~3 行 + 教室」，点到课程的概率也提高了。
     整个表格随行数自然变长（8 节 ≈ 620px），滚动区本来就独立，不影响其他区块。 */
  .schedule-table thead th { padding: 10px 0; font-size: 12px; font-weight: 600; }
  .schedule-table td { height: 76px; }
  .schedule-table td.cell-filled { padding: 3px; }
  .schedule-table .period-cell, .schedule-table thead th:first-child { width: 44px !important; min-width: 44px; padding: 8px 2px; }
  .schedule-table .period-cell .period-name { font-size: 10.5px; white-space: nowrap; letter-spacing: -.2px; }
  .schedule-table .period-cell .period-time { font-size: 9.5px; margin-top: 1px; }
  .schedule-course { padding: 5px 3px 4px; border-left-width: 3px; border-radius: 6px; justify-content: flex-start; }
  .schedule-course .course-name { font-size: 11.5px; line-height: 1.28; margin-bottom: 2px; white-space: normal; word-break: break-all; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; }
  .schedule-course .course-teacher { display: none; }
  .schedule-course .course-loc { font-size: 10px; line-height: 1.2; opacity: .78; }

  /* ── 成绩分析 ──
     v3：四张彩色图标卡合并为一张卡内的 4 列指标（样式在文件前面的「子页通用骨架」块里）。
     这里只保留必须留在本媒体块的布局规则，避免和后定义的同名规则互相覆盖。 */
  .grades-detail-row { grid-template-columns: 1fr; }
  .grade-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .grade-card { padding: 10px 12px; }
  .gc-score { font-size: 18px; }
  .sem-selector { flex-direction: column; align-items: flex-start; gap: 12px; }
  .sem-selector .semester-tag { margin-left: 0; }
  /* 选择器占满一行便于点选，统计胶囊收紧字号，查询链接回到左侧与胶囊对齐 */
  .sem-selector .semester-tag.semester-select { width: 100%; flex: 1 1 auto; min-width: 0; }
  .sem-stats-inline { flex-wrap: wrap; gap: 8px; }
  .sem-stats-inline > span { padding: 2px 9px; font-size: 11px; }
  .sem-link-action { margin-left: 0; }
  /* 成绩分析页统一纵向流式布局，便于末尾 el-empty 排序 */
  .grades-view { display: flex; flex-direction: column; }
  /* 子项禁止收缩：容器高度受视口约束，卡片又带 overflow:hidden（min-height:auto → 0），
     展开「课程画像」撑高时空间不足会把上方卡片压扁，而不是交给页面滚动。
     固定为自然高度后，多出的高度由 .schedule-page 的 overflow-y 接管 */
  .grades-view > * { flex-shrink: 0; }
  /* 一项一行四等分只针对环形图下方的统计项；.grades-detail-row 是 grid 行，不参与该 flex 分配 */
  .score-stats { display: flex; flex-wrap: wrap; gap: 16px 12px; justify-content: center; }
  .score-stats .stat-item { flex: 0 0 calc((100% - 36px) / 4); min-width: 0; }
  .score-stats .stat-num { font-size: 18px !important; }
  .stat-num { font-size: 20px; }
  .score-mascot { width: 72px; height: 72px; }
  .score-header { flex-direction: column; align-items: center; gap: 16px; padding: 16px; }
  .grades-view > .el-empty { order: 6; }
  /* AI 学情分析改由右下角绵小城入口承载，隐藏侧栏卡片（桌面端保留） */
  .side-ai-card { display: none; }
  /* 课程画像折叠（点击标题行展开/收起，箭头旋转提示状态） */
  .course-profile-card .analytics-head { cursor: pointer; -webkit-tap-highlight-color: transparent; transition: background .2s ease, border-color .3s ease; }
  .course-profile-card .analytics-head:active { background: rgba(64,158,255,.08); }
  /* 收起时抹掉标题行下边框，否则卡片底部会多出一条悬空的线 */
  .course-profile-card:not(.is-open) .analytics-head { border-bottom-color: transparent; }
  .course-profile-card .head-toggle { display: inline-flex; margin-left: auto; font-size: 15px; color: var(--text-muted, #909399); transition: transform .3s ease; }
  .course-profile-card.is-open .head-toggle { transform: rotate(180deg); }
  /* 过渡期间裁剪内容：组件只在下一帧才写 overflow，补这条避免首帧溢出一闪 */
  .course-profile-card .el-collapse-transition-enter-active,
  .course-profile-card .el-collapse-transition-leave-active { overflow: hidden; }
  .analytics-head { flex-wrap: wrap; row-gap: 6px; padding: 12px 16px; }
  .head-sub { display: none; }
  .chart { height: 200px; }
  .radar-chart { height: 240px; }
  .line-chart { height: 200px; }
  .analytics-body.duo { flex-direction: column; }
  .panel { flex: none; }
  .panel-divider { width: 100%; height: 1px; margin: 14px 12px; }
  /* 右下角绵小城（点击弹出 AI 学情分析） */
  .grades-mascot { display: block; position: fixed; right: 12px; bottom: 68px; width: 64px; height: 64px; z-index: 50; cursor: pointer; animation: mascot-bob 3s ease-in-out infinite; }
  .grades-mascot:active { transform: scale(.92); }
  .grades-mascot img { width: 100%; height: 100%; object-fit: contain; user-select: none; -webkit-user-select: none; -webkit-user-drag: none; filter: drop-shadow(0 4px 8px rgba(0,0,0,.12)); pointer-events: none; }
  @keyframes mascot-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }

  /* ── 成长轨迹 ── */
  .growth-two-col { flex-direction: column; }
  .growth-right-col { width: 100%; }
  .goal-item-body { flex-direction: column; align-items: flex-start; }
  .goal-input-wrap { flex-wrap: wrap; }
  .record-card { padding: 12px; }
  .record-title { font-size: 13px; }
}

@media (max-width: 767px) {
.semester-select-popper .el-select-dropdown__item {
  border-radius: 6px;
  margin: 2px 6px;
  transition: background .2s ease;
  font-size: 13px;
  padding: 0 10px;
  height: 30px;
  line-height: 30px;
}
.semester-select-popper .el-select-dropdown__item:hover {
  background: #f5f7fa;
}
.semester-select-popper .el-select-dropdown__item.is-selected {
  color: #409eff;
  font-weight: 600;
  background: #ecf5ff;
}
.semester-select-popper .el-popper__arrow::before {
  border: 1px solid #e4e7ed;
  background: #fff;
}

/* 移动端绵小城 AI 弹窗（挂 body 下，全局样式） */
.mascot-ai-dialog.el-dialog {
  border-radius: 16px;
}
.mascot-ai-dialog .mascot-ai-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 4px 12px;
}
.mascot-ai-dialog .mascot-ai-head img { width: 48px; height: 48px; object-fit: contain; user-select: none; -webkit-user-drag: none; }
.mascot-ai-dialog .mascot-ai-head-text { flex: 1; min-width: 0; }
.mascot-ai-dialog .mascot-ai-title { font-size: 15px; font-weight: 700; color: #1a1a2e; }
.mascot-ai-dialog .mascot-ai-sub { font-size: 12px; color: #999; margin-top: 2px; }
.mascot-ai-dialog .mascot-ai-head .el-button { margin-left: auto; }
.mascot-ai-dialog .mascot-ai-body { max-height: 62vh; overflow-y: auto; -webkit-overflow-scrolling: touch; }

/* ===== AI 今日报告子页（v5）：心情 / 任务 / 已实现 / 天气 + 运势 ===== */
.ai-view { display: flex; flex-direction: column; padding-bottom: 20px; }

/* 加载态：居中提示，避免骨架屏在移动端抖动 */
.report-loading { display: flex; align-items: center; gap: 10px; padding: 44px 16px; color: #6d5df0; }
.rl-title { margin: 0; font-size: 13.5px; font-weight: 600; color: var(--sp-ink, #14171a); }
.rl-sub { margin: 2px 0 0; font-size: 12px; color: var(--sp-ink-3, #9aa0a8); }

/* 顶部主视觉：问候 + 实时天气 + 心情胶囊 */
.rp-hero {
  position: relative; overflow: hidden;
  padding: 16px 16px 14px; border-radius: 18px;
  background:
    radial-gradient(120% 90% at 100% 0%, rgba(124, 108, 240, 0.16), transparent 60%),
    radial-gradient(100% 80% at 0% 100%, rgba(255, 196, 120, 0.16), transparent 62%),
    linear-gradient(160deg, #f7f8ff 0%, #fbf9f6 100%);
  border: 1px solid rgba(124, 108, 240, 0.10);
}
.rp-hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.rp-hero-left { min-width: 0; flex: 1; }
.rp-date { margin: 0; font-size: 11px; letter-spacing: 0.06em; color: var(--sp-ink-3, #9aa0a8); }
.rp-greet { margin: 5px 0 0; font-size: 19px; line-height: 25px; font-weight: 700; color: var(--sp-ink, #14171a); }
.rp-weather {
  flex: none; display: flex; align-items: center; gap: 7px;
  padding: 8px 10px; border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 1px 3px rgba(20, 23, 26, 0.05);
}
.rp-weather-emoji { font-size: 20px; line-height: 1; }
.rp-weather-main { display: flex; flex-direction: column; gap: 1px; }
.rp-weather-temp { font-size: 15px; font-weight: 700; color: var(--sp-ink, #14171a); line-height: 17px; }
.rp-weather-desc { font-size: 10.5px; color: var(--sp-ink-3, #9aa0a8); line-height: 13px; }
.rp-weather-range { font-size: 10px; line-height: 14px; color: var(--sp-ink-3, #9aa0a8); text-align: right; }
.rp-weather-off { opacity: 0.72; }

.rp-chips { display: flex; align-items: center; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.rp-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 999px;
  background: color-mix(in srgb, var(--chip-c, #9db4c8) 16%, #ffffff);
  color: var(--chip-c, #6b7d92);
  font-size: 11.5px; font-weight: 600; line-height: 16px;
  border: 1px solid color-mix(in srgb, var(--chip-c, #9db4c8) 34%, transparent);
}
.rp-chip-emoji { font-size: 13px; line-height: 1; }
.rp-chip-btn {
  --chip-c: #7c6cf0;
  cursor: pointer; font-family: inherit;
  -webkit-tap-highlight-color: transparent;
}
.rp-chip-btn:active { transform: scale(0.97); }

/* 运势卡：中性底 + 单色点缀，避免整块彩色渐变压迫感 */
.rp-fortune {
  --fc: #6b8399; --fc-soft: #f0f3f6;
  margin-top: 12px; padding: 13px 14px 12px;
  border: 1px solid var(--sp-border, #e9ebee); border-radius: 16px;
  background: var(--sp-surface, #fff);
  color: var(--sp-ink, #14171a);
}
.rp-tone-great { --fc: #b07c24; --fc-soft: #faf3e3; }
.rp-tone-good { --fc: #97732c; --fc-soft: #f8f4e9; }
.rp-tone-mid { --fc: #5b54c9; --fc-soft: #f1effc; }
.rp-tone-soft { --fc: #6b8399; --fc-soft: #eff3f6; }
.rp-fortune-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.rp-fortune-title { display: flex; align-items: center; gap: 8px; min-width: 0; }
.rp-fortune-label { font-size: 11px; letter-spacing: 0.06em; color: var(--sp-ink-3, #9aa0a8); }
.rp-fortune-level {
  padding: 2px 8px; border-radius: 999px;
  background: var(--fc-soft); color: var(--fc);
  font-size: 12px; font-weight: 600; line-height: 17px;
}
.rp-fortune-score {
  font-size: 24px; font-weight: 800; line-height: 1;
  letter-spacing: -0.02em; color: var(--fc);
  font-variant-numeric: tabular-nums;
}
.rp-fortune-score small { margin-left: 2px; font-size: 10px; font-weight: 500; color: var(--sp-ink-3, #9aa0a8); }
.rp-fortune-meter { height: 3px; margin-top: 10px; border-radius: 999px; background: #f0f2f4; overflow: hidden; }
.rp-fortune-meter i { display: block; height: 100%; border-radius: 999px; background: var(--fc); opacity: 0.78; }
.rp-fortune-key {
  display: flex; align-items: center; gap: 6px;
  margin: 10px 0 0; font-size: 12px; font-weight: 600; color: var(--sp-ink, #14171a);
}
.rp-fortune-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--fc); flex: none; }
.rp-fortune-summary { margin: 5px 0 0; font-size: 12px; line-height: 18px; color: var(--sp-ink-2, #5b6472); }
.rp-fortune-meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
.rp-fortune-meta-item {
  display: flex; flex-direction: column; gap: 1px; min-width: 0;
  padding: 7px 9px; border-radius: 10px;
  background: var(--fc-soft);
}
.rp-fortune-meta-item small { font-size: 10px; color: var(--sp-ink-3, #9aa0a8); }
.rp-fortune-meta-item span {
  font-size: 12px; font-weight: 600; color: var(--sp-ink, #14171a);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 四段正文 */
.rp-sec { padding: 15px 0 3px; }
.rp-sec + .rp-sec { border-top: 1px solid var(--sp-border, #e9ebee); }
.rp-sec-head { display: flex; align-items: center; gap: 7px; margin-bottom: 7px; }
.rp-sec-ico { font-size: 14px; line-height: 1; }
.rp-sec-title { margin: 0; font-size: 14.5px; font-weight: 600; color: var(--sp-ink, #14171a); }
.rp-sec-line { margin: 0 0 7px; font-size: 13px; line-height: 20px; color: var(--sp-ink-2, #5b6472); }
.rp-sec-line:last-child { margin-bottom: 0; }

/* 建议卡：时段 + 优先级，动作按钮保持中性 */
.rp-suggest { padding-bottom: 4px; }
.ai-sec-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }
.ai-sec-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--sp-ink, #14171a); }
.ai-sec-count { font-size: 12px; color: var(--sp-ink-3, #9aa0a8); }
.ai-action-list { list-style: none; margin: 0; padding: 0; }
.ai-action { display: flex; gap: 10px; padding: 10px 0; }
.ai-action + .ai-action { border-top: 1px solid var(--sp-border, #e9ebee); }
/* 优先级标签：小号文字胶囊（不能只用颜色传达紧急程度 —— WCAG 1.4.1） */
.ai-prio {
  flex: none; align-self: flex-start; margin-top: 1px;
  padding: 1px 6px; border-radius: 5px;
  font-size: 10px; line-height: 15px; font-weight: 600;
  white-space: nowrap;
}
.ai-action-main { flex: 1; min-width: 0; }
.ai-action-title { margin: 0; font-size: 13.5px; font-weight: 600; color: var(--sp-ink, #14171a); line-height: 19px; }
.ai-action-when {
  display: inline-block; margin-right: 6px; padding: 1px 5px;
  border-radius: 5px; background: #f3f4f6;
  color: var(--sp-ink-2, #5b6472);
  font-size: 10.5px; font-weight: 500; line-height: 15px;
  vertical-align: 1px;
}
.ai-view .ai-sec:first-child { padding-top: 4px; }
.ai-action-content { margin: 2px 0 0; font-size: 12.5px; line-height: 18px; color: var(--sp-ink-2, #5b6472); }
.ai-add-btn {
  margin-top: 8px; padding: 5px 12px;
  border: 1px solid var(--sp-border, #e9ebee); border-radius: 8px;
  background: var(--sp-surface, #ffffff);
  font-family: inherit; font-size: 12px; color: #3730a3; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ai-add-btn:active { transform: scale(0.97); }
.ai-added { display: inline-block; margin-top: 8px; font-size: 12px; color: #15803d; }
.ai-empty { margin: 8px 0 4px; font-size: 13px; color: var(--sp-ink-3, #9aa0a8); }
/* 一键导出：中性描边小按钮，右下角收尾，不与建议卡主色冲突 */
.rp-export-row { display: flex; justify-content: flex-end; margin-top: 14px; }
.rp-export-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--sp-border, #e9ebee); border-radius: 9px;
  background: transparent; color: var(--sp-ink-2, #5b6472);
  font-family: inherit; font-size: 12px; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.rp-export-btn:active { transform: scale(0.97); background: #f7f8f9; }

/* ===== 请假服务 v5（美团订单流，少图标） ===== */
.sv-current {
  background: var(--sp-surface, #fff); border-radius: 16px; padding: 15px 16px 13px;
  box-shadow: 0 1px 2px rgba(20,23,26,.04);
}
.svc-cap { font-size: 11.5px; color: var(--sp-ink-3, #9aa0a8); }
.svc-title { margin: 6px 0 0; font-size: 15px; color: var(--sp-ink, #14171a); }
.svc-steps { display: flex; margin-top: 14px; }
.svc-step { flex: 1; text-align: center; position: relative; }
.svc-step::before { content: ''; position: absolute; top: 10px; left: -50%; width: 100%; height: 2px; background: #e9ebee; }
.svc-step:first-child::before { display: none; }
.svc-step.done::before { background: #3d4a57; }
.svc-step.cur::before { background: linear-gradient(90deg, #3d4a57 0%, #3d4a57 50%, #e9ebee 50%, #e9ebee 100%); }
.svc-step i {
  width: 20px; height: 20px; box-sizing: border-box; border-radius: 50%; margin: 0 auto;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; color: #fff; font-style: normal; position: relative; z-index: 1;
}
.svc-step.done i { background: #3d4a57; }
.svc-step.cur i { background: #fff; border: 2px solid #3d4a57; box-shadow: 0 0 0 3px rgba(61,74,87,.12); }
.svc-step p { font-size: 10.5px; color: var(--sp-ink-3, #9aa0a8); margin: 6px 0 0; }
.svc-step.cur p { color: #3d4a57; font-weight: 600; }
.svc-hint { margin: 10px 0 0; font-size: 11px; color: var(--sp-ink-3, #9aa0a8); line-height: 16px; }
.sv-cta {
  display: block; width: 100%; padding: 12px 0; margin-top: 2px;
  border: none; border-radius: 12px; cursor: pointer;
  background: #1f2328; color: #fff;
  font-family: inherit; font-size: 14.5px; font-weight: 600;
  -webkit-tap-highlight-color: transparent;
}
.sv-cta:active { transform: scale(0.99); }
.svr-row {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 13px;
  background: var(--sp-surface, #fff);
  border: 1px solid var(--sp-border, #e9ebee);
  border-radius: 12px;
}
.svr-row + .svr-row { margin-top: 8px; }
.svr-main { flex: 1; min-width: 0; }
.svr-main h5 { margin: 0; font-size: 12.5px; font-weight: 500; color: var(--sp-ink, #14171a); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.svr-main small { font-size: 10.5px; color: var(--sp-ink-3, #9aa0a8); }
.svr-st { font-size: 11px; font-weight: 600; flex: none; }
.svr-st.ing { color: #b45309; }
.svr-st.ok { color: #2f9e63; }
.svr-st.no { color: #b6bac1; }

/* ===== 成绩分析 v5：结论 hero ===== */
.gr-hero { padding: 2px 2px 12px; }
.gr-hero-big { margin: 0; font-size: 17px; color: var(--sp-ink, #14171a); font-weight: 600; }
.gr-hero-big b { font-size: 22px; color: #0f7a58; }
.gr-hero-of { font-size: 12px; color: var(--sp-ink-3, #9aa0a8); font-weight: 400; }
.gr-hero-sub { margin: 4px 0 0; font-size: 11.5px; color: var(--sp-ink-3, #9aa0a8); }
}


@media (max-width: 767px) {
  /* ============================================================
     学习计划 v5（仅移动端）
     参考：Forest 森林打卡（深绿情绪 hero）+ Duolingo 关卡路径（纵向节点 rail）
           滴答清单（今日任务单行清单，无卡片堆）
     约束：① Head 仍走固定 48px，本区只改内容 ② 计划项之间有路径连贯感
           ③ 空态不用插画，一行灰字即可 ④ 桌面端完全不受影响
     ============================================================ */
  /* ── hero：深绿森林渐变，替代原蓝色 marketing 大块 ── */
  .plan-view-wrap :deep(.plan-hero) {
    background: linear-gradient(158deg, #0f3d2e 0%, #1c6b4a 62%, #247a55 100%) !important;
    border-radius: 16px !important;
    padding: 15px 16px 13px !important;
    box-shadow: none !important;
    margin-bottom: 14px;
  }
  .plan-view-wrap :deep(.hero-glow) { display: none !important; }
  /* 与 48px 子页头重复的「MY PLAN · 学习计划 / 学业中心」在这层隐藏，
     hero 只留一句价值主张 + 三个数字 + 新建入口，避免同一个标题出现两次。 */
  .plan-view-wrap :deep(.hero-kicker),
  .plan-view-wrap :deep(.hero-tag) { display: none !important; }
  .plan-view-wrap :deep(.hero-title) {
    margin: 6px 0 0 !important;
    font-size: 17px !important; line-height: 22px !important;
    color: #fff !important; font-weight: 600 !important;
  }
  .plan-view-wrap :deep(.hero-sub) {
    margin: 4px 0 0 !important;
    font-size: 11px !important; line-height: 15px !important;
    color: rgba(255,255,255,.68) !important;
  }
  .plan-view-wrap :deep(.hero-add) {
    height: 28px !important; padding: 0 12px !important;
    background: rgba(255,255,255,.16) !important; border: 0 !important;
    color: #fff !important; font-size: 12px !important;
  }
  .plan-view-wrap :deep(.hero-stats) { margin-top: 12px !important; gap: 0 !important; }
  .plan-view-wrap :deep(.hs-num) { font-size: 19px !important; color: #fff !important; font-weight: 700 !important; }
  .plan-view-wrap :deep(.hs-label) { font-size: 10px !important; color: rgba(255,255,255,.6) !important; }
  .plan-view-wrap :deep(.hero-stat-sep) { background: rgba(255,255,255,.16) !important; }

  /* ── 卡片去白底：改为发丝线分区（Duolingo 关卡在卡片内，容器不要卡片套卡片） ── */
  .plan-view-wrap :deep(.card) {
    background: transparent !important;
    border: 0 !important; box-shadow: none !important; border-radius: 0 !important;
    padding: 0 !important; margin: 0 0 4px !important;
  }
  .plan-view-wrap :deep(.card + .card) { border-top: 1px solid var(--sp-border, #e9ebee) !important; padding-top: 14px !important; margin-top: 2px !important; }
  .plan-view-wrap :deep(.card-head) { padding: 0 0 8px !important; background: none !important; border: 0 !important; }
  .plan-view-wrap :deep(.card-head .head-bar),
  .plan-view-wrap :deep(.head-bar) { display: none !important; }
  .plan-view-wrap :deep(.head-title) { font-size: 13.5px !important; font-weight: 600 !important; color: var(--sp-ink, #14171a) !important; }
  .plan-view-wrap :deep(.card-head .el-button) { font-size: 11.5px !important; }

  /* 空态：去插画，一行灰字（参考滴答清单空态） */
  .plan-view-wrap :deep(.empty-block) { padding: 10px 0 4px !important; }
  .plan-view-wrap :deep(.empty-ico) { display: none !important; }
  .plan-view-wrap :deep(.empty-msg) { font-size: 12px !important; line-height: 17px !important; color: var(--sp-ink-3, #9aa0a8) !important; }

  /* ── 关卡 rail：每个 plan-card 左侧一枚节点 + 竖线 ── */
  .plan-view-wrap :deep(.plan-list) { position: relative; padding-left: 20px; }
  .plan-view-wrap :deep(.plan-list)::before {
    content: ''; position: absolute; left: 6px; top: 16px; bottom: 14px;
    width: 2px; background: #dce9c8; border-radius: 1px;
  }
  .plan-view-wrap :deep(.plan-card) {
    position: relative;
    background: var(--sp-surface, #fff) !important;
    border: 1px solid var(--sp-border, #e9ebee) !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    padding: 12px 13px !important;
    margin-bottom: 10px !important;
  }
  .plan-view-wrap :deep(.plan-card)::before {
    content: ''; position: absolute; left: -18px; top: 17px;
    width: 9px; height: 9px; border-radius: 50%;
    background: #58cc02; box-shadow: 0 0 0 3px #fff, 0 0 0 4px #dce9c8;
    z-index: 1;
  }
  .plan-view-wrap :deep(.plan-card.is-done)::before { background: #b8c4b0; }
  .plan-view-wrap :deep(.plan-card-title) { font-size: 13.5px !important; font-weight: 600 !important; color: var(--sp-ink, #14171a) !important; }
  .plan-view-wrap :deep(.plan-card-meta) { font-size: 11px !important; color: var(--sp-ink-3, #9aa0a8) !important; gap: 6px !important; }
  .plan-view-wrap :deep(.plan-list) { display: block; }

  /* ── 空态：去插画，只留一行灰字 ── */
  .plan-view-wrap :deep(.el-empty) { padding: 12px 0 !important; }
  .plan-view-wrap :deep(.el-empty__image) { display: none !important; }
  .plan-view-wrap :deep(.el-empty__description) { margin: 0 !important; }
  .plan-view-wrap :deep(.el-empty__description p) { font-size: 12px !important; color: var(--sp-ink-3, #9aa0a8) !important; margin: 0 !important; }
}

@media (max-width: 767px) {
/* ============================================================
   成绩分析 v5（仅移动端）：结论优先 + 迷你图表 + 全扁平
   参考：Apple Health 摘要（结论大字）+ Keep 数据条 + 滴答清单列表
   设计约束：① 图表不超过 88px，不再独占一屏 ② 无白卡，发丝线分区
   ③ 课程成绩用列表行而不是九宫格卡片
   ============================================================ */
  .grades-view { --gr-ink: #14171a; --gr-ink2: #5b6472; --gr-ink3: #9aa0a8; --gr-line: #e9ebee; }

/* ── 结论区：大数字 + 一行解释，替代四张 stat 卡 ── */
  .grades-view .gr-hero { padding: 4px 2px 14px; border-bottom: 1px solid var(--gr-line); }
  .grades-view .gr-hero-big { margin: 0; font-size: 15px; color: var(--gr-ink2); font-weight: 500; }
  .grades-view .gr-hero-big b { font-size: 30px; font-weight: 700; color: #0f7a58; letter-spacing: -.5px; }
  .grades-view .gr-hero-of { font-size: 12.5px; color: var(--gr-ink3); font-weight: 400; }
  .grades-view .gr-hero-sub { margin: 6px 0 0; font-size: 12px; color: var(--gr-ink3); line-height: 17px; }

/* stat 行：极简四列，去白底去边框（保留桌面原样） */
  .grades-view .grade-stats-row {
    background: transparent; border: 0; box-shadow: none; border-radius: 0;
    padding: 12px 0; margin: 0; border-bottom: 1px solid var(--gr-line);
  }
  .grades-view .grade-stat-card { background: transparent !important; border: 0 !important; box-shadow: none !important; }
  .grades-view .stat-icon { display: none; }
  .grades-view .stat-value { font-size: 17px; font-weight: 600; color: var(--gr-ink); }
  .grades-view .stat-label { font-size: 10.5px; color: var(--gr-ink3); }

/* ── 分区容器：全部透明 + 发丝线 ── */
  .grades-view .analytics-card {
    background: transparent !important; border: 0 !important; box-shadow: none !important;
    border-radius: 0 !important; margin: 0 !important; padding: 0 !important;
  }
  .grades-view .analytics-card + .analytics-card { border-top: 1px solid var(--gr-line); }
  .grades-view .analytics-head { padding: 14px 0 8px; }
  .grades-view .analytics-head .head-bar { display: none; }
  .grades-view .analytics-head .head-title { font-size: 14px; font-weight: 600; color: var(--gr-ink); }
  .grades-view .analytics-body { padding: 0 0 12px; gap: 0; }
  .grades-view .analytics-body.duo { flex-direction: column; }
  .grades-view .panel { background: transparent !important; border: 0 !important; box-shadow: none !important; padding: 0 !important; }
  .grades-view .panel + .panel { margin-top: 10px; }
  .grades-view .panel-divider { display: none; }
  .grades-view .panel-title { font-size: 12px; color: var(--gr-ink3); font-weight: 500; margin-bottom: 4px; }
  .grades-view .panel-title .el-icon { display: none; }

/* 迷你图表：88px，去掉背景网格感 */
  .grades-view .chart { height: 88px !important; width: 100%; }

/* 绩点趋势改为「迷你走势条」：容器高度压缩，折线本身足够表达趋势 */
  .grades-view .analytics-card:nth-of-type(1) .chart { height: 82px !important; }

/* ── 课程画像：折叠行更轻 ── */
  .grades-view .course-profile-card .analytics-head { padding: 12px 0; }
  .grades-view .course-rank-item { padding: 7px 0; }
  .grades-view .cr-group-label { font-size: 11px; margin: 8px 0 2px; }
  .grades-view .cr-name { font-size: 12.5px; color: var(--gr-ink); }
  .grades-view .cr-bar { height: 4px; }
  .grades-view .cr-score { font-size: 12.5px; font-weight: 600; }

/* ── 学期明细：课程改为扁平列表行（替代九宫格卡片） ── */
  .grades-view .detail-card { border-top: 1px solid var(--gr-line); }
  .grades-view .sem-selector { padding: 0 0 10px; }
  .grades-view .grade-grid { display: flex; flex-direction: column; gap: 0; }
  .grades-view .grade-card {
    display: flex; align-items: center; gap: 10px;
    background: transparent !important; border: 0 !important; border-radius: 0 !important;
    box-shadow: none !important; padding: 11px 2px !important;
    position: relative;
  }
  .grades-view .grade-card + .grade-card { border-top: 1px solid var(--gr-line) !important; }
  .grades-view .gc-top { flex: 1; display: flex; align-items: center; gap: 8px; margin: 0; }
  .grades-view .gc-name {
    font-size: 13px; color: var(--gr-ink); font-weight: 500;
    flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .grades-view .gc-score { font-size: 15px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .grades-view .gc-meta {
    display: flex; gap: 8px; margin: 0; font-size: 10.5px; color: var(--gr-ink3);
    flex-direction: column; align-items: flex-end; line-height: 1.35;
  }
  .grades-view .grade-card-more { justify-content: center; }
  .grades-view .grade-card-more .gc-name { flex: none; color: #0f7a58; font-size: 12.5px; }

/* 分数等级色：只染分数本身，不给卡片上色 */
  .grades-view .grade-card.excellent .gc-score { color: #0f7a58; }
  .grades-view .grade-card.good .gc-score { color: #0369a1; }
  .grades-view .grade-card.pass .gc-score { color: #b45309; }
  .grades-view .grade-card.fail .gc-score { color: #c0392b; }

/* ── 覆盖：stat 行与空图表彻底扁平 ── */
  .grades-view .grade-stats-row > .grade-stat-card,
  .grades-view .grade-stats-row {
    background: transparent !important;
    border: 0 !important; border-radius: 0 !important; box-shadow: none !important;
  }
  .grades-view .grade-stats-row { border-bottom: 1px solid var(--gr-line) !important; }
  .grades-view .grade-stat-card::before { display: none !important; }
  .grades-view .grade-stat-card { padding: 0 2px !important; align-items: flex-start !important; }
  .grades-view .stat-value { font-size: 17px; }
  .grades-view .stat-label { margin-top: 2px; }

  /* 空图表：不占高度，只留一行灰字（el-empty 需 :deep 才能命中） */
  .grades-view :deep(.el-empty) {
    padding: 4px 0 !important; margin: 0 !important;
    display: block !important; height: auto !important; min-height: 0 !important;
  }
  .grades-view :deep(.el-empty__image) { display: none !important; height: 0 !important; width: 0 !important; }
  .grades-view :deep(.el-empty__description) { margin: 0 !important; height: auto !important; }
  .grades-view :deep(.el-empty__description p) { font-size: 11.5px !important; line-height: 16px !important; color: var(--gr-ink3) !important; margin: 0 !important; }
  .grades-view :deep(.panel) { min-height: 0 !important; }
  .grades-view :deep(.analytics-body) { min-height: 0 !important; }

/* 有数据的图表：压缩到 82px，去掉标题行冗余 */
  .grades-view .panel-title { display: none; }
  .grades-view .analytics-head .head-sub { display: none; }
  .grades-view .analytics-body.duo { gap: 8px !important; }

/* 学期明细：选择器 + 明细行更紧凑 */
  .grades-view .semester-select { max-width: 100%; }
  .grades-view .sem-stats-inline { display: flex; gap: 10px; font-size: 11.5px; color: var(--gr-ink2); padding: 6px 0 2px; }
  .grades-view .sem-link-action { font-size: 12px; }

/* 移动端隐藏吉祥物（占位且与扁平风格冲突） */
  .grades-view .grades-mascot { display: none !important; }

  /* ── 目标计划 v6：4 级里程碑阶梯（抄 Duolingo 关卡进度 + Strava 目标） ──
     一条 3px 轨道 + 4 个刻度节点，已过节点实心墨绿、当前待过节点赭橙描边、
     未到节点浅灰；轨道填充到「实际绩点」位置，末端小圆环是实际值游标。 */
  .gl-item { padding-bottom: 14px; }
  .gl-item + .gl-item {
    border-top: 1px solid var(--sp-border, #e9ebee);
    padding-top: 14px;
  }
  .gl-head { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
  .gl-sem { font-size: 13.5px; font-weight: 600; color: var(--sp-ink, #14171a); letter-spacing: -.2px; }
  .gl-badge {
    font-size: 10.5px; line-height: 1; padding: 3px 7px; border-radius: 999px;
    background: #eef1f4; color: #5b6470; font-weight: 500;
  }
  .gl-badge.is-past { background: transparent; color: #9aa0a8; padding-left: 0; }

  .gl-track { position: relative; height: 32px; margin: 0 17px 4px; }
  .gl-rail, .gl-fill {
    position: absolute; top: 9px; height: 3px; border-radius: 2px;
  }
  .gl-rail { left: 0; right: 0; background: #e9ebee; }
  .gl-fill { left: 0; background: #0f7a58; transition: width .5s cubic-bezier(.16,1,.3,1); }
  .gl-mark {
    position: absolute; top: 5.5px; z-index: 2;
    width: 10px; height: 10px; border-radius: 50%; box-sizing: border-box;
    background: #fff; border: 2px solid #0f7a58; transform: translateX(-5px);
  }
  .gl-node {
    position: absolute; top: 0; z-index: 3;
    transform: translateX(-50%);
    display: flex; flex-direction: column; align-items: center;
  }
  .gl-node i {
    width: 12px; height: 12px; border-radius: 50%; box-sizing: border-box;
    background: #fff; border: 2px solid #cfd5dc; margin-top: 4.5px;
    transition: background .3s ease, border-color .3s ease;
  }
  .gl-node b {
    margin-top: 4px; font-size: 9.5px; font-weight: 500;
    color: #9aa0a8; font-variant-numeric: tabular-nums;
  }
  .gl-node.is-done i { background: #0f7a58; border-color: #0f7a58; }
  .gl-node.is-done b { color: #0f7a58; }
  .gl-node.is-next i { border-color: #b45309; box-shadow: 0 0 0 3px rgba(180, 83, 9, .12); }
  .gl-node.is-next b { color: #b45309; font-weight: 600; }

  .gl-hint { margin: 4px 0 0; font-size: 11.5px; line-height: 1.55; color: var(--sp-ink-3, #6b737c); }
  .gl-hint.is-ok { color: #0f7a58; }
  .gl-edit { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
  .gl-edit-label { font-size: 11.5px; color: var(--sp-ink-3, #6b737c); }
  .gl-edit .el-button { margin-left: 0; }
  /* 保存按钮跟成绩页识别色（青绿）走，不要 Element 默认蓝 */
  .gl-edit .el-button--primary {
    background-image: none !important;
    background-color: #0f7a58 !important;
    border-color: #0f7a58 !important;
    color: #fff !important;
  }
  .gl-edit .el-button--primary:hover {
    background-image: none !important;
    background-color: #0c6448 !important;
    border-color: #0c6448 !important;
  }
}

/* ── 学期选择下拉（teleport 到 body，随父作用域带 data-v 命中） ── */
.semester-select-popper .el-select-dropdown { overflow: visible; }
.semester-select-popper .el-select-dropdown__item {
  border-radius: 6px;
  margin: 2px 6px;
  transition: background .2s ease;
  font-size: 13px;
  padding: 0 10px;
  height: 30px;
  line-height: 30px;
}
.semester-select-popper .el-select-dropdown__item:hover { background: #f5f7fa; }
.semester-select-popper .el-select-dropdown__item.is-selected { color: #409eff; font-weight: 600; background: #ecf5ff; }
</style>

<!-- 下拉面板挂载在 body 下，需用全局样式覆盖 -->
<style>
.semester-select-popper.el-popper {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 6px 18px rgba(0,0,0,.1);
}
</style>
