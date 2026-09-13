<template>
  <div class="schedule-page">
    <!-- ===== 两栏布局：内容 + 右侧栏 ===== -->
    <div class="content-row">
      <div class="content-main">
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
                <el-button v-if="showResetBtn" size="small" text type="primary" @click="resetWeek">回到本周</el-button>
                <el-select v-model="selectedScheduleSem" size="small" class="semester-tag semester-select" popper-class="semester-select-popper" fit-input-width>
                  <el-option v-for="s in scheduleSemesterOptions" :key="s.value" :label="s.label" :value="s.value" />
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
                          <th style="width:76px">节次</th>
                          <th v-for="d in days" :key="d" :class="{ 'th-today': isTodayCol(d) }">{{ d }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="row in courseGrid" :key="row.period">
                          <td class="period-cell">
                            <div class="period-name">第{{ row.period }}节</div>
                            <div class="period-time">{{ periodTimeLabel(row.period) }}</div>
                          </td>
                          <template v-for="(cell, ci) in row.cells" :key="ci">
                            <td v-if="cell.empty" :class="{ 'td-today': isTodayCol(cell.day) }" style="padding:0"></td>
                            <td v-else :rowspan="cell.rowspan" :class="{ 'td-today': isTodayCol(cell.day) }" style="padding:4px;vertical-align:middle">
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

          <!-- 课程画像 -->
          <div class="analytics-card">
            <div class="analytics-head">
              <span class="head-bar"></span>
              <span class="head-title">课程画像</span>
              <span class="head-sub">课程类型表现与优劣势科目</span>
            </div>
            <div class="analytics-body duo">
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
                  <el-select v-model="selectedSem" placeholder="选择学期" style="width:200px">
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
            </div>
          </div>
          <el-empty v-if="!grades.length && !upcomingExams.length && !gradeAnalysis.semester_gpa.length" description="暂无考试成绩数据" />

        </div>

        <!-- ===== 成长轨迹 ===== -->
        <div v-else-if="activeTab === 'growth'" key="growth" class="growth-view">
          <!-- 分数头部 -->
          <div class="score-header">
            <div class="score-ring-group">
              <div class="score-ring">
                <svg viewBox="0 0 120 120" class="score-svg">
                  <circle cx="60" cy="60" r="52" fill="none" stroke="#f0f2f5" stroke-width="8" />
                  <circle cx="60" cy="60" r="52" fill="none" stroke="url(#scoreGrad)" stroke-width="8"
                    :stroke-dasharray="circleLen" :stroke-dashoffset="circleOffset" stroke-linecap="round"
                    transform="rotate(-90, 60, 60)" />
                  <defs><linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#409eff" /><stop offset="100%" stop-color="#67c23a" />
                  </linearGradient></defs>
                </svg>
                <div class="score-center">
                  <div class="score-value">{{ profile?.total_score ?? '--' }}</div>
                  <div class="score-label">综合评分</div>
                </div>
              </div>
              <div class="score-mascot">
                <img src="/images/mascot.png" alt="绵小城" draggable="false" />
              </div>
            </div>
            <div class="score-stats">
              <div class="stat-item" v-for="s in statsCards" :key="s.label">
                <span class="stat-num">{{ s.value }}</span>
                <span class="stat-label">{{ s.label }}</span>
              </div>
            </div>
          </div>

          <!-- 两栏：左=图表+标签，右=记录 -->
          <div class="growth-two-col">
            <div class="growth-left-col">
              <!-- 综合能力画像 -->
              <div class="analytics-card">
                <div class="analytics-head">
                  <span class="head-bar"></span>
                  <span class="head-title">综合能力画像</span>
                  <span class="head-sub">多维能力评分与成长类型构成</span>
                </div>
                <div class="analytics-body duo">
                  <div class="panel panel-radar">
                    <div class="panel-title"><el-icon><DataAnalysis /></el-icon>综合能力雷达</div>
                    <v-chart v-if="profile" :option="radarOption" class="chart radar-chart" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="48" />
                  </div>
                  <div class="panel-divider"></div>
                  <div class="panel panel-bar">
                    <div class="panel-title"><el-icon><Histogram /></el-icon>成长类型分布</div>
                    <div class="chart-unit">单位：数量</div>
                    <v-chart v-if="profile?.stats_by_type?.length" :option="growthBarOption" class="chart bar-chart" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="48" />
                  </div>
                </div>
              </div>

              <!-- 成长历程 -->
              <div class="analytics-card">
                <div class="analytics-head">
                  <span class="head-bar"></span>
                  <span class="head-title">成长历程</span>
                  <span class="head-sub">月度成长趋势</span>
                </div>
                <div class="analytics-body duo">
                  <div class="panel">
                    <div class="panel-title"><el-icon><TrendCharts /></el-icon>成长趋势</div>
                    <div class="chart-unit">单位：记录数</div>
                    <v-chart v-if="profile?.monthly_trend?.length" :option="growthLineOption" class="chart line-chart" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="48" />
                  </div>
                  <div class="panel-divider"></div>
                  <div class="panel">
                    <div class="panel-title"><el-icon><PieChartIcon /></el-icon>成长类型分布</div>
                    <v-chart v-if="profile?.stats_by_type?.length" :option="growthPieOption" class="chart pie-chart" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="48" />
                  </div>
                </div>
              </div>

              <!-- 项目展示 -->
              <div class="projects-section">
                <div class="section-header">
                  <span><el-icon style="margin-right:6px"><FolderOpened /></el-icon> 项目展示 <el-tag v-if="projects.length" size="small" type="info" effect="plain" style="margin-left:8px">{{ projects.length }}</el-tag></span>
                  <div style="display:flex;gap:8px">
                    <el-button v-if="projects.length > 3" size="small" text type="primary" @click="showAllProjects = !showAllProjects">{{ showAllProjects ? '收起' : '展开更多' }}</el-button>
                    <el-button type="primary" size="small" @click="openProjectDialog">添加项目</el-button>
                  </div>
                </div>
                <div v-if="projects.length" class="project-grid">
                  <div v-for="p in visibleProjects" :key="p.id" class="project-card">
                    <div class="project-top">
                      <div class="project-icon" :class="p.is_team ? 'team' : 'solo'">
                        <el-icon :size="22"><UserFilled v-if="p.is_team" /><User v-else /></el-icon>
                      </div>
                      <div class="project-info">
                        <div class="project-name">{{ p.project_name }}</div>
                        <div class="project-date">{{ p.start_date }} ~ {{ p.end_date || '至今' }}</div>
                      </div>
                    </div>
                    <div v-if="p.is_team && p.team_members" class="project-members">成员: {{ p.team_members }}</div>
                    <div v-if="p.attachment_url" class="project-attach">
                      <el-link type="primary" :href="p.attachment_url" target="_blank" :icon="Link">查看附件</el-link>
                    </div>
                    <div class="project-actions">
                      <el-button size="small" text type="primary" @click="editProject(p)">编辑</el-button>
                      <el-button size="small" text type="danger" @click="handleDeleteProject(p.id)">删除</el-button>
                    </div>
                  </div>
                </div>
                <el-empty v-else-if="loaded" description="暂无项目" :image-size="60" />
              </div>
            </div>

            <div class="growth-right-col">
              <div class="records-section">
                <div class="section-header">
                  <span class="section-header-title"><el-icon style="margin-right:6px"><Collection /></el-icon> 成长记录 <el-tag v-if="growthRecords.length" size="small" type="info" effect="plain" style="margin-left:8px">{{ growthRecords.length }} 条</el-tag></span>
                  <div style="display:flex;gap:8px">
                    <el-button v-if="growthRecords.length > 3" size="small" text type="primary" @click="allRecordsVisible = true">查看全部</el-button>
                    <el-button type="primary" size="small" @click="openDialog">添加记录</el-button>
                  </div>
                </div>
                <div v-if="growthRecords.length" class="records-list records-scroll">
                  <div v-for="r in growthRecords.slice(0, 3)" :key="r.id" class="record-card record-card-clickable" @click="showRecordDetail(r)">
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
                <el-empty v-else description="暂无成长记录" />
              </div>

              <!-- 技能与兴趣（重设计） -->
              <div class="analytics-card skills-card">
                <div class="analytics-head">
                  <span class="head-bar"></span>
                  <span class="head-title">技能与兴趣</span>
                  <el-button size="small" type="primary" plain class="head-save" @click="saveSkills">保存</el-button>
                </div>
                <div class="analytics-body skills-body">
                  <div class="skills-selected">
                    <div class="skills-selected-title">已选标签</div>
                    <div class="skills-tag-list">
                      <TransitionGroup name="tag-fade">
                        <span v-for="s in localSkills" :key="'s-' + s" class="skills-tag skills-tag-skill" @click="removeSkill(s)">
                          {{ s }} <el-icon class="skills-tag-close"><Close /></el-icon>
                        </span>
                        <span v-for="s in localInterests" :key="'i-' + s" class="skills-tag skills-tag-interest" @click="removeInterest(s)">
                          {{ s }} <el-icon class="skills-tag-close"><Close /></el-icon>
                        </span>
                      </TransitionGroup>
                      <Transition name="empty-fade">
                        <span v-if="showTagEmpty" class="skills-empty">暂无标签，从下方选择或自定义添加</span>
                      </Transition>
                    </div>
                  </div>
                  <div class="skills-preset-group">
                    <div class="skills-preset-section">
                      <div class="skills-preset-label"><el-icon style="margin-right:4px;color:#409eff"><Aim /></el-icon>技能</div>
                      <div class="skills-preset-tags">
                        <span v-for="p in skillPresets" :key="p" class="skills-preset-tag" :class="{ active: localSkills.includes(p) }" @click="toggleSkill(p)">{{ p }}</span>
                      </div>
                    </div>
                    <div class="skills-preset-section">
                      <div class="skills-preset-label"><el-icon style="margin-right:4px;color:#e6a23c"><MagicStick /></el-icon>兴趣</div>
                      <div class="skills-preset-tags">
                        <span v-for="p in interestPresets" :key="p" class="skills-preset-tag" :class="{ active: localInterests.includes(p) }" @click="toggleInterest(p)">{{ p }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="skills-custom">
                    <el-radio-group v-model="customType" size="small">
                      <el-radio-button value="skill">技能</el-radio-button>
                      <el-radio-button value="interest">兴趣</el-radio-button>
                    </el-radio-group>
                    <el-input v-model="newTag" size="small" placeholder="自定义标签" @keyup.enter="addCustomTag" style="flex:1" />
                    <el-button size="small" type="primary" @click="addCustomTag">添加</el-button>
                  </div>
                </div>
              </div>

            </div>
          </div>

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
    </div>
    <!-- ===== 右侧垂直标签栏（位于 content-row 内，横向排列靠右） ===== -->
    <div class="page-tabs">
      <div :class="['page-tab', { active: activeTab === 'schedule' }]" @click="activeTab = 'schedule'">
        <el-icon><Calendar /></el-icon> 课程表
      </div>
      <div :class="['page-tab', { active: activeTab === 'grades' }]" @click="activeTab = 'grades'">
        <el-icon><DataLine /></el-icon> 成绩分析
      </div>
      <div :class="['page-tab', { active: activeTab === 'growth' }]" @click="activeTab = 'growth'">
        <el-icon><TrendCharts /></el-icon> 成长轨迹
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { getCourses as fetchCourses, getGrades, getExams } from '@/api/academic'
import { getGradeAnalysis, type GradeAnalysis } from '@/api/gradeAnalysis'
import { WarningFilled, Location, TrendCharts, CircleCheckFilled, Lock, Calendar, MagicStick, Loading, Star, Trophy, DataAnalysis, Histogram, DataLine, Collection, FolderOpened, Link, User, UserFilled, InfoFilled, ArrowRight, Grid, PieChart as PieChartIcon, Close, Aim } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart, PieChart, RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, RadarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { Course, Grade, Exam } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { useAiAnalysis } from '@/composables/useAiAnalysis'
import { getGrowthRecords, createGrowthRecord, getGrowthProfile, updateSkills, getProjects, createProject, updateProject, deleteProject } from '@/api/growth'
import type { GrowthProfile, StudentProject } from '@/api/growth'
import type { GrowthRecord } from '@/types'
import { renderMarkdown } from '@/utils/markdown'
import UploadBtn from '@/components/upload/UploadBtn.vue'

use([LineChart, BarChart, PieChart, RadarChart, GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, RadarComponent, CanvasRenderer])

const auth = useAuthStore()
const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'schedule')

// ===== 页签 =====

// ===== 成绩分析 =====
const gradeAnalysisLoading = ref(false)
const gradeAnalysis = ref<GradeAnalysis>({
  stats: { total_courses: 0, total_credits: 0, avg_score: 0, avg_gpa: 0, highest_gpa: 0, lowest_gpa: 0, pass_rate: 0, gpa_rank: 0, total_students: 0 },
  semester_gpa: [], course_type_stats: [], score_distribution: [], top_courses: [], weak_courses: []
})

async function loadGradeAnalysis() {
  gradeAnalysisLoading.value = true
  try { const data = await getGradeAnalysis(auth.user?.id || 0); gradeAnalysis.value = data } catch (error) { console.error('加载成绩分析失败:', error) } finally { gradeAnalysisLoading.value = false }
}

// ===== 成绩分析图表 =====
const hasScores = computed(() => gradeAnalysis.value.score_distribution.some(d => d.count > 0))
function shortSem(sem: string) {
  const parts = sem.split('-')
  if (parts.length < 3) return sem
  return `${parts[0].slice(2)}-${parts[1].slice(2)}·${parts[2]}`
}
function distColor(range: string) {
  if (range === '90-100') return '#67c23a'
  if (range === '80-89') return '#409eff'
  if (range === '70-79') return '#e6a23c'
  if (range === '60-69') return '#f89898'
  return '#f56c6c'
}
function barWidth(s?: number) { return Math.max(6, Math.min(100, s ?? 0)) + '%' }
const chartAxis = { fontSize: 11, color: '#999' }
const chartSplitLine = { lineStyle: { color: '#f0f2f5' } }

const semGpaOption = computed(() => ({
  tooltip: { trigger: 'axis', confine: true },
  grid: { left: 36, right: 16, top: 28, bottom: 26 },
  xAxis: { type: 'category', boundaryGap: false, data: gradeAnalysis.value.semester_gpa.map(s => shortSem(s.semester)), axisLabel: { ...chartAxis, interval: 0 }, axisLine: { lineStyle: { color: '#e5e6eb' } } },
  yAxis: { type: 'value', min: 0, max: 4, splitLine: chartSplitLine, axisLabel: chartAxis },
  series: [{
    type: 'line', smooth: true, symbol: 'circle', symbolSize: 8,
    data: gradeAnalysis.value.semester_gpa.map(s => s.gpa),
    lineStyle: { width: 3, color: '#409eff' },
    itemStyle: { color: '#409eff', borderColor: '#fff', borderWidth: 2 },
    areaStyle: { color: 'rgba(64,158,255,.1)' },
    markLine: gradeAnalysis.value.stats.avg_gpa ? {
      silent: true, symbol: 'none',
      lineStyle: { color: '#e6a23c', type: 'dashed' },
      label: { formatter: `总均绩 ${gradeAnalysis.value.stats.avg_gpa}`, fontSize: 10, color: '#e6a23c' },
      data: [{ yAxis: gradeAnalysis.value.stats.avg_gpa }]
    } : undefined
  }],
  animationDuration: 800
}))

const distOption = computed(() => ({
  tooltip: { trigger: 'axis', confine: true, formatter: (p: any) => `${p[0]?.axisValue}：<b>${p[0]?.value}</b> 门` },
  grid: { left: 36, right: 16, top: 28, bottom: 26 },
  xAxis: { type: 'category', data: gradeAnalysis.value.score_distribution.map(d => d.range.replace('0-59', '<60')), axisLabel: chartAxis, axisLine: { lineStyle: { color: '#e5e6eb' } } },
  yAxis: { type: 'value', minInterval: 1, splitLine: chartSplitLine, axisLabel: chartAxis },
  series: [{
    type: 'bar', barWidth: '46%',
    data: gradeAnalysis.value.score_distribution.map(d => ({ value: d.count, itemStyle: { color: distColor(d.range), borderRadius: [6, 6, 0, 0] } })),
    label: { show: true, position: 'top', fontSize: 11, color: '#666' }
  }],
  animationDuration: 800
}))

const typeOption = computed(() => ({
  tooltip: { trigger: 'axis', confine: true, formatter: (p: any) => { const t = gradeAnalysis.value.course_type_stats[p[0]?.dataIndex]; return t ? `${t.type}：均分 ${t.avg_score} / 均绩 ${t.avg_gpa} / ${t.count} 门` : '' } },
  grid: { left: 36, right: 16, top: 28, bottom: 26 },
  xAxis: { type: 'category', data: gradeAnalysis.value.course_type_stats.map(t => t.type), axisLabel: chartAxis, axisLine: { lineStyle: { color: '#e5e6eb' } } },
  yAxis: { type: 'value', min: 0, max: 100, splitLine: chartSplitLine, axisLabel: chartAxis },
  series: [{
    type: 'bar', barWidth: '40%',
    data: gradeAnalysis.value.course_type_stats.map(t => ({ value: t.avg_score, itemStyle: { color: '#409eff', borderRadius: [6, 6, 0, 0] } })),
    label: { show: true, position: 'top', fontSize: 11, color: '#666' }
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

const courseGrid = computed(() => {
  const wk = currentWeek.value
  const segEnd = (p: number) => (p <= 4 ? 4 : p <= 8 ? 8 : 12)
  const dayBlocks: Record<number, { start: number; end: number; course: Course }[]> = {}
  for (const day of days) {
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
  for (let p = 1; p <= maxPeriod; p++) {
    const cells: any[] = []
    for (const day of days) {
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
function courseCellBg(name: string, day: string) {
  const base = courseColor(name)
  return isTodayCol(day) ? base.slice(0, 7) + '3d' : base
}

const palette = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9b59b6', '#1abc9c', '#e67e22', '#2ecc71', '#3498db', '#e74c3c']
const colorMap: Record<string, string> = {}
let colorIdx = 0
function courseColor(name: string) { if (!colorMap[name]) { colorMap[name] = palette[colorIdx % palette.length] + '18'; colorIdx++ } return colorMap[name] }
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
  tooltipPos.value = {
    x: Math.min(r.right + 8, window.innerWidth - 236),
    y: Math.max(8, r.top)
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
const hasMoreGrades = computed(() => {
  const list = selectedSem.value ? gradesBySem.value[selectedSem.value] || [] : []
  return list.length > maxVisible.value
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
const gradesBySem = computed(() => { const map: Record<string, Grade[]> = {}; for (const g of grades.value) { if (!map[g.semester]) map[g.semester] = []; map[g.semester].push(g) } return map })
const semStats = computed(() => { const stats: Record<string, { count: number; avg: number; gpa: string; credits: number }> = {}; for (const [sem, gs] of Object.entries(gradesBySem.value)) { const scores = gs.filter(g => g.score != null).map(g => g.score); const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0; const gpa = gs.length ? (gs.reduce((s, g) => s + (g.gpa || 0), 0) / gs.length).toFixed(2) : '0.00'; const credits = gs.reduce((s, g) => s + (g.credit || 0), 0); stats[sem] = { count: gs.length, avg, gpa, credits } } return stats })
const upcomingExams = computed(() => { const now = new Date(); return exams.value.filter(e => !e.exam_date || new Date(e.exam_date) >= now).sort((a, b) => (a.exam_date || '').localeCompare(b.exam_date || '')) })
function scoreLevel(s: number) { if (s >= 90) return 'level-a'; if (s >= 80) return 'level-b'; if (s >= 70) return 'level-c'; if (s >= 60) return 'level-d'; return 'level-f' }
function avgColor(s?: number) { if (!s) return '#999'; if (s >= 90) return '#67c23a'; if (s >= 80) return '#409eff'; if (s >= 70) return '#e6a23c'; return '#f56c6c' }
function formatDate(d: string) { if (!d) return ''; const parts = d.split('-'); return parts[1] + '/' + parts[2] }
function loadGoals() { try { const raw = localStorage.getItem('student_sem_goals'); if (raw) goals.value = JSON.parse(raw) } catch { goals.value = {} } }
function saveGoalForSem(sem: string) { const val = goalInputs.value[sem]; if (val == null) return; goals.value[sem] = val; localStorage.setItem('student_sem_goals', JSON.stringify(goals.value)); ElMessage.success(`${sem} 目标已保存`) }

// ===== 成长轨迹 =====
const skillPresets = ['编程开发', 'UI/UX设计', '数据分析', '人工智能', '项目管理', '产品设计', '视频剪辑', '摄影', '写作', '翻译', '演讲', '团队协作', '领导力']
const interestPresets = ['音乐', '运动', '阅读', '游戏', '旅行', '美食', '电影', '摄影', '绘画', '舞蹈', '编程', '创业', '公益']
const profile = ref<GrowthProfile | null>(null)
const growthRecords = ref<GrowthRecord[]>([])
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
const localSkills = ref<string[]>([])
const localInterests = ref<string[]>([])
const newTag = ref('')
const customType = ref<'skill' | 'interest'>('skill')
const projects = ref<StudentProject[]>([])
const visibleProjects = computed(() => showAllProjects.value ? projects.value : projects.value.slice(0, 3))
const loaded = ref(false)
const growthLoaded = ref(false)
const projectDialogVisible = ref(false)
const editingProject = ref<StudentProject | null>(null)
const projectForm = ref<Record<string, any>>({ project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '' })

function toggleSkill(s: string) { const idx = localSkills.value.indexOf(s); if (idx >= 0) localSkills.value.splice(idx, 1); else localSkills.value.push(s) }
function removeSkill(s: string) { localSkills.value = localSkills.value.filter(x => x !== s); syncTagEmpty() }
function toggleInterest(s: string) { const idx = localInterests.value.indexOf(s); if (idx >= 0) localInterests.value.splice(idx, 1); else localInterests.value.push(s); syncTagEmpty() }
function removeInterest(s: string) { localInterests.value = localInterests.value.filter(x => x !== s); syncTagEmpty() }
const showTagEmpty = ref(false)
let tagEmptyTimer: ReturnType<typeof setTimeout> | null = null
function syncTagEmpty() {
  if (tagEmptyTimer) { clearTimeout(tagEmptyTimer); tagEmptyTimer = null }
  if (!localSkills.value.length && !localInterests.value.length) {
    tagEmptyTimer = setTimeout(() => { showTagEmpty.value = true }, 280)
  } else {
    showTagEmpty.value = false
  }
}
function addCustomTag() { const s = newTag.value.trim(); if (!s) return; if (customType.value === 'skill') { if (!localSkills.value.includes(s)) localSkills.value.push(s) } else { if (!localInterests.value.includes(s)) localInterests.value.push(s) } newTag.value = '' }
async function saveSkills() { try { await updateSkills({ skills: localSkills.value, interests: localInterests.value }); ElMessage.success('技能/兴趣已保存'); profile.value = await getGrowthProfile() } catch { ElMessage.error('保存失败') } }
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

const circleLen = 2 * Math.PI * 52
const circleOffset = computed(() => { if (!profile.value) return circleLen; return circleLen - (circleLen * Math.min(100, profile.value.total_score) / 100) })
const statsCards = computed(() => [
  { label: '成长记录', value: profile.value?.total_records ?? 0 },
  { label: '技能数量', value: profile.value?.total_skills ?? 0 },
  { label: '荣誉', value: profile.value?.stats_by_type.find(s => s.name === '荣誉')?.value ?? 0 },
  { label: '竞赛', value: profile.value?.stats_by_type.find(s => s.name === '竞赛')?.value ?? 0 },
  { label: '实践', value: profile.value?.stats_by_type.find(s => s.name === '实践')?.value ?? 0 },
  { label: '论文', value: profile.value?.stats_by_type.find(s => s.name === '论文')?.value ?? 0 },
  { label: '成果', value: profile.value?.stats_by_type.find(s => s.name === '成果')?.value ?? 0 },
])
const radarOption = computed(() => ({
  tooltip: { trigger: 'item', confine: true, backgroundColor: 'rgba(255,255,255,0.96)', borderColor: '#e8e8e8', borderWidth: 1, textStyle: { color: '#333', fontSize: 13 }, formatter: (params: any) => { const indicators = profile.value?.radar ?? []; const values = params.value ?? []; let html = '<div style="font-weight:600;margin-bottom:6px">' + (params.seriesName || '能力指标') + '</div>'; indicators.forEach((item: any, i: number) => { html += `<div style="display:flex;justify-content:space-between;gap:20px"><span style="color:#888">${item.name}</span><span style="font-weight:600;color:#409eff">${values[i] ?? 0}</span></div>` }); return html } },
  radar: { indicator: (profile.value?.radar ?? []).map(d => ({ name: d.name, max: 100 })), shape: 'circle', center: ['50%', '50%'], radius: '65%', axisName: { color: '#333', fontSize: 12 }, splitArea: { areaStyle: { color: ['rgba(64,158,255,.03)', 'rgba(64,158,255,.06)'] } } },
  series: [{ type: 'radar', name: '综合能力', data: [{ value: profile.value?.radar.map(d => d.value) ?? [0, 0, 0, 0, 0] }], areaStyle: { color: 'rgba(64,158,255,.2)' }, lineStyle: { color: '#409eff', width: 2 }, itemStyle: { color: '#409eff' }, symbol: 'circle', symbolSize: 6, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(64,158,255,0.5)' } }, animationDuration: 2000, animationEasing: 'cubicOut' as const, animationDelay: function(idx: number) { return idx * 100 } }],
  animationDuration: 2000, animationEasing: 'cubicOut' as const,
}))
const growthBarOption = computed(() => ({
  tooltip: { trigger: 'axis', confine: true, formatter: (p: any) => `${p[0]?.axisValue}：<b>${p[0]?.value}</b> 条` },
  grid: { left: 32, right: 20, top: 20, bottom: 40 },
  xAxis: { type: 'category', data: (profile.value?.stats_by_type ?? []).map(s => s.name), name: '成长类型', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666' } },
  yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
  series: [{ type: 'bar', data: (profile.value?.stats_by_type ?? []).map((s, i) => ({ value: s.value, itemStyle: { color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'][i % 5] } })), barWidth: '40%', itemStyle: { borderRadius: [6, 6, 0, 0] }, animationDuration: 1500, animationEasing: 'elasticOut' as const, animationDelay: function(idx: number) { return idx * 200 } }],
  animationDuration: 1500, animationEasing: 'cubicOut' as const,
}))
const growthPieOption = computed(() => {
  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
  return {
    tooltip: { trigger: 'item', confine: true, formatter: '{b}：{c} 条（{d}%）' },
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 12, color: '#666' } },
    color: colors,
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '44%'],
      data: (profile.value?.stats_by_type ?? []).map((s, i) => ({ name: s.name, value: s.value, itemStyle: { color: colors[i % colors.length] } })),
      label: { show: true, formatter: '{c}条', fontSize: 12, color: '#666' },
      emphasis: { label: { fontSize: 14, fontWeight: 'bold' }, itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.15)' } },
      animationDuration: 1200
    }]
  }
})
const growthLineOption = computed(() => {
  const trend = profile.value?.monthly_trend ?? []
  const months = [...new Set(trend.map(t => t.month))].sort()
  const types = [...new Set(trend.map(t => t.type))]
  const colors: Record<string, string> = { honor: '#e6a23c', competition: '#409eff', practice: '#67c23a', paper: '#f56c6c', achievement: '#909399' }
  const gTypeLabels: Record<string, string> = { honor: '荣誉', competition: '竞赛', practice: '实践', paper: '论文', achievement: '成果' }
  return {
    tooltip: { trigger: 'axis', confine: true, formatter: (p: any) => { let s = `<b>${p[0]?.axisValue}</b><br/>`; p.forEach((i: any) => { s += `${i.marker} ${i.seriesName}：<b>${i.value}</b> 条<br/>` }); return s } }, legend: { data: types.map(t => gTypeLabels[t] || t), bottom: 0 },
    grid: { left: 32, right: 20, top: 20, bottom: 65 },
    xAxis: { type: 'category', data: months, name: '月份', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: types.map(t => ({ name: gTypeLabels[t] || t, type: 'line', smooth: true, data: months.map(m => trend.find(item => item.month === m && item.type === t)?.count ?? 0), itemStyle: { color: colors[t] || '#909399' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: (colors[t] || '#909399') + '40' }, { offset: 1, color: (colors[t] || '#909399') + '05' }] } }, animationDuration: 2000, animationEasing: 'cubicOut' as const, animationDelay: function(idx: number) { return idx * 100 } })),
    animationDuration: 2000, animationEasing: 'cubicOut' as const,
  }
})
const gpaOption = computed(() => {
  const data = profile.value?.gpa_trend ?? []
  if (!data.length) return {}
  const semLabels = data.map(d => d.semester.replace('2023-2024-1', '23-24 上').replace('2023-2024-2', '23-24 下').replace('2024-2025-1', '24-25 上').replace('2024-2025-2', '24-25 下'))
  const values = data.map(d => d.gpa)
  const minGpa = Math.max(0, Math.floor(Math.min(...values) * 10) / 10 - 0.3)
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>平均绩点: ${p[0].value}` },
    grid: { left: 32, right: 60, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: semLabels, name: '学期', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666', fontSize: 13 } },
    yAxis: { type: 'value', min: minGpa, max: 4.0, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [{ type: 'line', data: values, smooth: true, symbol: 'circle', symbolSize: 10, lineStyle: { color: '#e6a23c', width: 3 }, itemStyle: { color: '#e6a23c' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#e6a23c40' }, { offset: 1, color: '#e6a23c05' }] } }, markLine: { data: [{ yAxis: 3.5, label: { formatter: '优秀线 3.5', color: '#67c23a' } }, { yAxis: 2.5, label: { formatter: '警戒线 2.5', color: '#f56c6c' } }], silent: true, lineStyle: { type: 'dashed' } }, animationDuration: 2000, animationEasing: 'cubicOut' as const, animationDelay: function(idx: number) { return idx * 200 } }],
    animationDuration: 2000, animationEasing: 'cubicOut' as const,
  }
})

onMounted(async () => {
  loadGoals()
  const coursePromise = (async () => {
    const all = (await fetchCourses().catch(() => [])) as any[]
    allCourses.value = all as Course[]
  })()
  const gradesPromise = getGrades().then(d => { grades.value = d as any }).catch(() => {})
  const examsPromise = getExams().then(d => { exams.value = d as any }).catch(() => {})
  const growthProfilePromise = getGrowthProfile().catch(() => null)
  const growthRecordsPromise = getGrowthRecords().catch(() => [])
  const projectsPromise = getProjects().catch(() => [])
  await Promise.all([coursePromise, gradesPromise, examsPromise])
  const realWeek = calcCurrentRealWeek()
  if (courses.value.length) {
    baseWeek.value = Math.min(...courses.value.map(c => c.week_start))
    weekOffset.value = realWeek - baseWeek.value
  } else {
    baseWeek.value = 1
    weekOffset.value = realWeek - 1
  }
  scheduleReady.value = true
  if (semesters.value.length) selectedSem.value = semesters.value[0]
  for (const sem of semesters.value) { if (goalInputs.value[sem] == null) { goalInputs.value[sem] = goals.value[sem] ?? 3.5 } }
  loadGradeAnalysis()
  if (grades.value.length) { startAiAnalysis() }
  growthProfilePromise.then(p => { if (p) { profile.value = p; localSkills.value = [...(p.skills || [])]; localInterests.value = [...(p.interests || [])]; syncTagEmpty() } })
  growthRecordsPromise.then(list => { growthRecords.value = list as any })
  projectsPromise.then(list => { projects.value = list as any; loaded.value = true })
  Promise.all([growthProfilePromise, growthRecordsPromise, projectsPromise]).then(() => { growthLoaded.value = true })
})

watch(semesters, (list) => {
  if (list.length && !list.includes(selectedSem.value)) { selectedSem.value = list[0] }
  for (const sem of list) { if (goalInputs.value[sem] == null) { goalInputs.value[sem] = goals.value[sem] ?? 3.5 } }
})

watch(() => route.query.tab, (val) => { if (val && typeof val === 'string') activeTab.value = val })
</script>

<style scoped>
.schedule-page { height: 100%; width: 100%; padding: 12px 16px 0; display: flex; flex-direction: column; box-sizing: border-box; overflow-y: auto; scrollbar-width: none; -ms-overflow-style: none; }
.schedule-page::-webkit-scrollbar { display: none; }

/* ===== 页签切换动画 ===== */
.tab-fade-enter-active { transition: opacity .32s cubic-bezier(.16,1,.3,1), transform .32s cubic-bezier(.16,1,.3,1); }
.tab-fade-leave-active { transition: opacity .2s ease, transform .2s ease; }
.tab-fade-enter-from { opacity: 0; transform: translateY(14px) scale(.995); }
.tab-fade-leave-to { opacity: 0; transform: translateY(-8px) scale(.995); }

/* ===== 右侧垂直标签栏 ===== */
.page-tabs { display: flex; flex-direction: column; gap: 6px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); padding: 8px; width: 96px; flex-shrink: 0; align-self: flex-start; position: sticky; top: 12px; }
.page-tab { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 14px 6px; border-radius: 10px; font-size: 12px; font-weight: 500; color: var(--text-secondary); cursor: pointer; transition: all 0.2s ease; letter-spacing: 0.5px; }
.page-tab .el-icon { font-size: 20px; transition: transform 0.2s ease; }
.page-tab:hover { background: var(--hover-bg, rgba(64,158,255,.06)); color: var(--accent-blue, #409eff); }
.page-tab:hover .el-icon { transform: translateY(-1px); }
.page-tab.active { background: linear-gradient(160deg, rgba(64,158,255,.16), rgba(64,158,255,.05)); color: var(--accent-blue, #409eff); font-weight: 600; box-shadow: 0 2px 8px rgba(64,158,255,.18); }
.page-tab.active .el-icon { transform: scale(1.08); }

/* ===== 两栏布局 ===== */
.content-row { display: flex; gap: 16px; flex: 1; min-height: 0; }
.content-main { flex: 1; min-width: 0; max-width: 1200px; width: 100%; margin: 0 auto; display: flex; flex-direction: column; }

/* ===== 通用卡片 ===== */
.content-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); padding: 12px 16px 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border-light, #f0f0f0); }
.card-header span { font-size: 15px; font-weight: 600; color: var(--text-primary); }

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
/* 当天列高亮 */
.schedule-table thead th.th-today { font-weight: 700; background: #E5F8FC; }
.schedule-table .td-today { background: rgba(0,0,0,.025); }
.course-today { box-shadow: inset 0 0 0 1.5px rgba(64,158,255,.35); }
.week-nav { display: flex; align-items: center; gap: 6px; }
.week-nav-btn { width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-card); cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.week-nav-btn:hover { background: var(--accent-blue, #409eff); color: #fff; border-color: var(--accent-blue, #409eff); }
.week-label { font-size: 14px; font-weight: 600; color: #1a1a2e; min-width: 50px; text-align: center; }
.semester-link { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: linear-gradient(135deg, #67c23a, #5daf34); color: #fff; border-radius: 8px; font-size: 13px; font-weight: 500; text-decoration: none; cursor: pointer; transition: all 0.2s; margin-left: auto; }
.semester-link:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(103,194,58,.4); }

/* ===== 课表表格 ===== */
.schedule-table { width: 100%; table-layout: fixed; border-collapse: collapse; }
.holiday-box { padding: 80px 20px; text-align: center; }
.holiday-box .holiday-icon { font-size: 56px; margin-bottom: 12px; }
.holiday-box .holiday-title { font-size: 20px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.holiday-box .holiday-sub { font-size: 14px; color: #c0c4cc; }
.schedule-table th, .schedule-table td { border: 1px solid #ebeef5; text-align: center; vertical-align: middle; padding: 0; width: calc((100% - 80px) / 7); }
.schedule-table td { height: 60px; }
.schedule-table .period-cell { width: 80px; }
.schedule-table thead th { background: #f5f7fa; font-size: 14px; font-weight: 600; padding: 12px 8px; color: #303133; position: sticky; top: -12px; z-index: 2; }
.schedule-table .period-cell { background: #fafafa; padding: 12px 8px; font-size: 13px; min-width: 80px; }
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
.ai-result-content :deep(.md-h4) { font-size: 15px; font-weight: 700; color: #1a1a2e; margin: 12px 0 6px; }
.ai-result-card :deep(.md-ul),
.ai-result-content :deep(.md-ul) { margin: 8px 0; padding-left: 22px; list-style: disc; }
.ai-result-card :deep(.md-li),
.ai-result-content :deep(.md-li) { margin: 4px 0; }
.ai-result-card :deep(.md-code-block),
.ai-result-content :deep(.md-code-block) { background: #f6f8fa; border-radius: 6px; padding: 12px 14px; margin: 10px 0; overflow-x: auto; }
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
.semester-action-card { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 12px; background: linear-gradient(135deg, #ecf5ff, #f0f9eb); border: 1px solid rgba(64,158,255,.18); text-decoration: none; color: inherit; cursor: pointer; transition: all .2s; box-shadow: 0 2px 8px rgba(64,158,255,.08); }
.semester-action-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(64,158,255,.22); border-color: #409eff; }
.semester-action-card .sac-icon { width: 44px; height: 44px; border-radius: 12px; background: #fff; color: #409eff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,0,0,.06); }
.semester-action-card .sac-content { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.semester-action-card .sac-title { font-size: 14px; font-weight: 700; color: #1a1a2e; }
.semester-action-card .sac-sub { font-size: 12px; color: #909399; margin-top: 2px; }
.semester-action-card .sac-arrow { color: #409eff; flex-shrink: 0; }
.grades-detail-row { display: grid; grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); gap: 16px; margin-bottom: 16px; align-items: stretch; }
.grades-side-col { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.side-exam-card { margin-bottom: 0 !important; }
.side-ai-card { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.side-ai-card .ai-result-card { max-height: 340px; }
.ai-side-body { padding: 14px 16px 16px !important; flex: 1; min-height: 0; display: flex; flex-direction: column; }
.ai-side-body .ai-placeholder { flex: 1; height: auto; }
.exam-list { display: flex; flex-direction: column; gap: 8px; padding-top: 14px !important; }
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
.goal-label { font-size: 13px; font-weight: 600; color: #333; white-space: nowrap; }
.goal-input-wrap { display: flex; align-items: center; }
.goal-locked { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #999; }
.goal-achieve { display: flex; align-items: center; gap: 3px; font-size: 13px; }
.sem-selector { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.sem-stats-inline { display: flex; gap: 14px; font-size: 13px; color: #999; }
.sem-stats-inline b { color: #1a1a2e; font-weight: 600; }
.grade-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; margin-bottom: 20px; }
.grade-card { background: #fff; border-radius: 10px; padding: 14px 16px; border: 1px solid rgba(0,0,0,.04); box-shadow: 0 1px 6px rgba(0,0,0,.02); transition: transform .15s; border-left: 4px solid #ddd; }
.grade-card:hover { transform: translateY(-2px); }
.grade-card.level-a { border-left-color: #67c23a; }
.grade-card.level-b { border-left-color: #409eff; }
.grade-card.level-c { border-left-color: #e6a23c; }
.grade-card.level-d { border-left-color: #f56c6c; }
.grade-card.level-f { border-left-color: #c03636; }
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
.level-a .gc-score { color: #67c23a; }
.level-b .gc-score { color: #409eff; }
.level-c .gc-score { color: #e6a23c; }
.level-d .gc-score { color: #f56c6c; }
.level-f .gc-score { color: #c03636; }
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
.head-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1;
  margin-left: 2px;
}
.head-save { margin-left: auto; }
/* 卡片头右侧的操作入口（如：查询学期信息/下载证明） */
.semester-action-card.head-action { margin-left: auto; padding: 8px 12px; border-radius: 10px; gap: 10px; }
.semester-action-card.head-action .sac-icon { width: 32px; height: 32px; border-radius: 8px; }
.semester-action-card.head-action .sac-title { font-size: 13px; }
.semester-action-card.head-action .sac-sub { font-size: 11px; }
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
.cloud-block { margin-bottom: 16px; }
.cloud-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; }
.tag-cloud { display: flex; flex-wrap: wrap; gap: 8px; min-height: 30px; }
.cloud-empty { font-size: 12px; color: var(--text-placeholder); line-height: 24px; }
.skill-tag { font-size: 12px; padding: 3px 12px; border-radius: 16px; }
/* 标签删除动画 */
.tag-fade-leave-active { transition: all .25s ease; }
.tag-fade-leave-to { opacity: 0; transform: scale(.85); }
/* 空状态文字淡入 */
.empty-fade-enter-active { transition: all .3s ease; }
.empty-fade-enter-from { opacity: 0; transform: translateY(-6px); }
.preset-block { display: flex; flex-direction: column; gap: 10px; padding: 14px 16px; margin-bottom: 16px; border-radius: 12px; background: var(--hover-bg); border: 1px solid var(--border-light); }
.preset-row { display: flex; align-items: flex-start; gap: 12px; }
.preset-label { flex-shrink: 0; font-size: 12px; font-weight: 600; color: var(--text-muted); line-height: 24px; width: 32px; }
.preset-tags { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; }
.preset-tag { cursor: pointer; font-size: 12px; }
.tag-input-row { display: flex; gap: 8px; align-items: center; }
.tag-input-row .el-input { flex: 1; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; font-size: 15px; font-weight: 600; color: var(--text-primary); }
.section-header-title { display: flex; align-items: center; line-height: 1; }
/* 技能与兴趣（重设计） */
.skills-card .skills-body { display: flex; flex-direction: column; gap: 14px; padding: 14px 16px !important; }
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

/* ===== 移动端适配 ===== */
@media (max-width: 767px) {
  .schedule-page { padding: 8px 12px 0; }
  .content-main { max-width: 100%; }
  .page-tabs { flex-direction: row; order: -1; width: 100%; align-self: auto; position: static; overflow-x: auto; border-radius: 12px; }
  .page-tab { flex: 1; flex-shrink: 0; flex-direction: row; gap: 6px; padding: 10px 16px; justify-content: center; letter-spacing: 0; }
  .page-tab .el-icon { font-size: 16px; }
  .page-tab.active::before { display: none; }
  .content-row { flex-direction: column; }
  .schedule-toolbar { flex-direction: row; flex-wrap: wrap; align-items: center; }
  .schedule-toolbar .schedule-toolbar-title { flex: 1 0 100%; }
  .semester-link { margin-left: 0; margin-top: 8px; }
  .grade-stats-row { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .grade-stat-card { padding: 12px; }
  .grade-stat-card .stat-value { font-size: 16px; }
  .grades-detail-row { grid-template-columns: 1fr; }
  .grade-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .grade-card { padding: 10px 12px; }
  .gc-score { font-size: 18px; }
  .sem-selector { flex-direction: column; align-items: flex-start; gap: 8px; }
  .sem-stats-inline { flex-wrap: wrap; gap: 8px; }
  .goal-item-body { flex-direction: column; align-items: flex-start; }
  .goal-input-wrap { flex-wrap: wrap; }
  .score-header { flex-direction: column; align-items: center; gap: 16px; padding: 16px; }
  .score-stats { display: flex; flex-wrap: wrap; gap: 16px 12px; justify-content: center; }
  .score-stats .stat-item { flex: 0 0 calc((100% - 36px) / 4); min-width: 0; }
  .score-stats .stat-num { font-size: 18px !important; }
  .score-mascot { width: 72px; height: 72px; }
  .stat-num { font-size: 20px; }
  .growth-two-col { flex-direction: column; }
  .growth-right-col { width: 100%; }
  .chart { height: 200px; }
  .analytics-body.duo { flex-direction: column; }
  .panel { flex: none; }
  .panel-divider { width: 100%; height: 1px; margin: 14px 12px; }
  .analytics-head { flex-wrap: wrap; row-gap: 6px; padding: 12px 16px; }
  .head-sub { display: none; }
  .semester-action-card.head-action { margin-left: 0; flex: 1 0 100%; }
  .radar-chart { height: 240px; }
  .line-chart { height: 200px; }
  .record-card { padding: 12px; }
  .record-title { font-size: 13px; }

  /* 移动端课表：固定最小宽度，保证内容完整，横向滑动查看 */
  .schedule-table { min-width: 720px; }
  .schedule-page .card-body { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .schedule-page .card-body::-webkit-scrollbar { height: 6px; }
  .schedule-page .card-body::-webkit-scrollbar-thumb { background: #c0c4cc; border-radius: 3px; }
}
</style>

<!-- 下拉面板挂载在 body 下，需用全局样式覆盖 -->
<style>
.semester-select-popper.el-popper {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 6px 18px rgba(0,0,0,.1);
}
.semester-select-popper .el-select-dropdown {
  overflow: visible;
}
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
</style>
