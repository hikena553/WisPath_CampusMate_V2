<template>
  <div class="schedule-page">
    <div class="overview-cards">
      <div class="overview-card">
        <div class="oc-icon" style="background:rgba(64,158,255,.1);color:#409eff">
          <el-icon :size="18"><Calendar /></el-icon>
        </div>
        <div class="oc-info">
          <div class="oc-value">{{ todayCoursesRealWeek.length }}</div>
          <div class="oc-label">今日课程</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="oc-icon" style="background:rgba(103,194,58,.1);color:#67c23a">
          <el-icon :size="18"><TrendCharts /></el-icon>
        </div>
        <div class="oc-info">
          <div class="oc-value">{{ gradeAnalysis.stats.avg_gpa }}</div>
          <div class="oc-label">当前 GPA</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="oc-icon" style="background:rgba(230,162,60,.1);color:#e6a23c">
          <el-icon :size="18"><Star /></el-icon>
        </div>
        <div class="oc-info">
          <div class="oc-value">{{ profile?.total_score ?? '--' }}</div>
          <div class="oc-label">综合评分</div>
        </div>
      </div>
      <div class="overview-card">
        <div class="oc-icon" style="background:rgba(144,147,153,.1);color:#909399">
          <el-icon :size="18"><Document /></el-icon>
        </div>
        <div class="oc-info">
          <div class="oc-value">{{ profile?.total_records ?? 0 }}</div>
          <div class="oc-label">成长记录</div>
        </div>
      </div>
    </div>

    <div class="page-tabs">
      <div :class="['tab-item', { active: activeTab === 'schedule' }]" @click="activeTab = 'schedule'">课程表</div>
      <div :class="['tab-item', { active: activeTab === 'grades' }]" @click="activeTab = 'grades'">成绩分析</div>
      <div :class="['tab-item', { active: activeTab === 'growth' }]" @click="activeTab = 'growth'">成长轨迹</div>
    </div>

    <!-- ===== 课程表 ===== -->
    <div v-if="activeTab === 'schedule'" class="schedule-view">
      <div v-if="!scheduleReady" class="ai-loading-card" style="margin:40px auto">
        <div class="ai-loading-header">
          <el-icon class="is-loading" :size="20"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
      </div>
      <template v-if="scheduleReady">
      <div class="schedule-toolbar">
        <div class="week-info">
          <el-button size="small" circle @click="goPrevWeek" :disabled="currentWeek <= 1">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <span class="week-label">第{{ currentWeek }}周</span>
          <el-button size="small" circle @click="goNextWeek">
            <el-icon><ArrowRight /></el-icon>
          </el-button>
          <el-button v-if="!isCurrentRealWeek" size="small" text type="primary" @click="resetWeek" style="margin-left:4px">回到本周</el-button>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <el-tag v-if="todayCoursesRealWeek.length" class="today-count-tag" effect="light" size="small">
            <el-icon><Sunny /></el-icon> 今日 {{ todayCoursesRealWeek.length }} 节课
          </el-tag>
          <el-tag class="week-count-tag" effect="light" size="small">
            <el-icon><Calendar /></el-icon> 本周 {{ uniqueCourseCount }} 门课程
          </el-tag>
        </div>
      </div>

      <div class="schedule-main-row">
        <div class="schedule-grid">
          <div class="sg-header">
            <div class="sg-corner">节次</div>
            <div v-for="d in days" :key="d" class="sg-day">{{ d }}</div>
          </div>
          <Transition :name="'slide-' + slideDir" mode="out-in">
            <div :key="currentWeek" class="sg-body">
              <div v-for="row in courseGrid" :key="row.period" class="sg-row">
                <div class="sg-period" v-html="periodLabels[row.period - 1]"></div>
                <div v-for="cell in row.cells" :key="cell.day" class="sg-cell">
                  <div v-for="c in cell.courses" :key="c.id" class="sg-course"
                    :style="{ background: courseColor(c.name) }">
                    <div class="sgc-name">{{ c.name }}</div>
                    <div class="sgc-meta">{{ c.location }}</div>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <div class="schedule-ai-section">
          <div class="section-title">
            <el-icon><MagicStick /></el-icon> 课程规划建议
            <el-button type="primary" size="small" :loading="scheduleLoading && !scheduleRaw" @click="startScheduleAiAnalysis({ stream: true })" style="margin-left:auto">
              <el-icon v-if="!scheduleLoading"><MagicStick /></el-icon>
              {{ scheduleLoading && !scheduleRaw ? '分析中...' : '重新生成' }}
            </el-button>
          </div>
          <div v-if="scheduleRaw" class="ai-result-card">
            <div v-if="scheduleLoading && scheduleFromCache" class="ai-refresh-bar">
              <el-icon class="is-loading" :size="14"><Loading /></el-icon>
              <span>正在更新...</span>
            </div>
            <div class="ai-result-content" v-html="scheduleRendered"></div>
          </div>
          <div v-else-if="scheduleLoading" class="ai-loading-card">
            <div class="ai-loading-header">
              <el-icon class="is-loading" :size="20"><Loading /></el-icon>
              <span>AI 正在分析您的课表...</span>
            </div>
            <div class="ai-loading-skeleton">
              <div class="skeleton-line" style="width:80%"></div>
              <div class="skeleton-line" style="width:60%"></div>
              <div class="skeleton-line" style="width:90%"></div>
              <div class="skeleton-line" style="width:45%"></div>
            </div>
          </div>
          <div v-else class="ai-placeholder">
            <el-icon :size="40" color="#ddd"><MagicStick /></el-icon>
            <p>点击"重新生成"按钮，AI 将根据您的课表提供学习规划建议</p>
          </div>
        </div>
      </div>

      <div class="today-section">
        <div class="today-header"><el-icon><Sunny /></el-icon> {{ isCurrentRealWeek ? '今日' : todayLabel }}课程</div>
        <TransitionGroup name="today" tag="div" class="today-list">
          <div v-for="c in todayCourses" :key="c.id" class="today-card"
            :style="{ borderLeftColor: courseColor(c.name).slice(0, 7) }">
            <div class="tc-time">第{{ c.start_period }}-{{ c.end_period }}节</div>
            <div class="tc-body">
              <div class="tc-name">{{ c.name }}</div>
              <div class="tc-meta">{{ c.teacher }} · {{ c.location }}</div>
            </div>
          </div>
        </TransitionGroup>
        <div v-if="!todayCourses.length" class="no-today">今日无课程安排</div>
      </div>

      <div class="course-list-section">
        <div class="cl-header">全部课程（第{{ currentWeek }}周）</div>
        <div class="course-list">
          <div v-for="c in currentWeekCourses" :key="c.id" class="cl-card" :style="{ borderLeftColor: courseColor(c.name).slice(0, 7) }">
            <div class="cl-top">
              <span class="cl-name">{{ c.name }}</span>
              <span class="cl-teacher">{{ c.teacher }}</span>
            </div>
            <div class="cl-meta">
              <span>{{ c.location }}</span>
              <span>第{{ c.week_start }}-{{ c.week_end }}周</span>
              <span>{{ dayLabel(c.day_of_week) }} 第{{ c.start_period }}-{{ c.end_period }}节</span>
            </div>
          </div>
          <el-empty v-if="!currentWeekCourses.length" description="本周无课" :image-size="48" />
        </div>
      </div>
      </template>
    </div>
    <div v-if="activeTab === 'grades'" class="grades-view">
      <!-- 成绩统计卡片 -->
      <div class="grade-stats-row">
        <div class="grade-stat-card">
          <div class="stat-icon" style="background: #e8f4fd; color: #409eff">
            <el-icon :size="20"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ gradeAnalysis.stats.total_courses }}</div>
            <div class="stat-label">课程总数</div>
          </div>
        </div>
        <div class="grade-stat-card">
          <div class="stat-icon" style="background: #f0f9eb; color: #67c23a">
            <el-icon :size="20"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ gradeAnalysis.stats.avg_gpa }}</div>
            <div class="stat-label">平均GPA</div>
          </div>
        </div>
        <div class="grade-stat-card">
          <div class="stat-icon" style="background: #fdf6ec; color: #e6a23c">
            <el-icon :size="20"><Star /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ gradeAnalysis.stats.avg_score }}</div>
            <div class="stat-label">平均分</div>
          </div>
        </div>
        <div class="grade-stat-card">
          <div class="stat-icon" style="background: #fef0f0; color: #f56c6c">
            <el-icon :size="20"><Aim /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ gradeAnalysis.stats.pass_rate }}%</div>
            <div class="stat-label">及格率</div>
          </div>
        </div>
      </div>

      <!-- 成绩分析图表 -->
      <div class="grade-charts-row">
        <div class="grade-chart-card">
          <div class="chart-title">成绩分布</div>
          <v-chart v-if="distributionOption" :option="distributionOption" class="grade-chart" autoresize />
          <el-empty v-else description="暂无数据" :image-size="48" />
        </div>
        <div class="grade-chart-card">
          <div class="chart-title">学期GPA趋势</div>
          <v-chart v-if="semesterGpaOption" :option="semesterGpaOption" class="grade-chart" autoresize />
          <el-empty v-else description="暂无数据" :image-size="48" />
        </div>
      </div>

      <!-- 优秀课程 + 目标计划（并排） -->
      <div class="grade-dual-row">
        <div class="grade-course-section" v-if="gradeAnalysis.top_courses.length">
          <div class="section-title"><el-icon><Trophy /></el-icon> 优秀课程</div>
          <div class="mini-course-list">
            <div v-for="c in gradeAnalysis.top_courses.slice(0, 5)" :key="c.course_name" class="mini-course-item good">
              <span class="mc-name">{{ c.course_name }}</span>
              <span class="mc-gpa">GPA {{ c.gpa }}</span>
            </div>
          </div>
        </div>

        <!-- 目标计划 -->
        <div class="goal-section">
          <div class="section-title"><el-icon><Aim /></el-icon> 目标计划</div>
          <div class="goal-list">
            <div v-for="(sem, idx) in semesters" :key="sem" class="goal-item" :class="{ 'is-current': idx === 0 }">
              <div class="goal-item-header">
                <span class="goal-sem-name">{{ sem }}</span>
                <el-tag v-if="idx === 0" type="success" size="small" effect="light">当前学期</el-tag>
                <el-tag v-else type="info" size="small" effect="plain">已完成</el-tag>
              </div>
              <div class="goal-item-body">
                <div class="goal-item-left">
                  <span class="goal-label">目标绩点</span>
                  <template v-if="idx === 0">
                    <div class="goal-input-wrap">
                      <el-input-number v-model="goalInputs[sem]" :min="0" :max="4" :step="0.1" :precision="2"
                        size="small" controls-position="right" style="width:110px" />
                      <el-button type="primary" size="small" @click="saveGoalForSem(sem)" style="margin-left:6px">保存</el-button>
                    </div>
                  </template>
                  <template v-else>
                    <div class="goal-locked">
                      <el-icon><Lock /></el-icon>
                      <span>{{ goals[sem] != null ? goals[sem].toFixed(2) : '未设置' }}</span>
                    </div>
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
              <div v-if="goals[sem] != null" class="goal-item-bar">
                <div class="goal-bar-outer">
                  <div class="goal-bar-inner" :style="{
                    width: Math.min(100, (parseFloat(semStats[sem]?.gpa || '0') / goals[sem]) * 100) + '%',
                    background: parseFloat(semStats[sem]?.gpa || '0') >= goals[sem] ? '#67c23a' : '#409eff'
                  }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- GPA 趋势 + AI 分析 -->
      <div class="trend-row">
        <!-- GPA 趋势 -->
        <div class="trend-section">
          <div class="section-title"><el-icon><TrendCharts /></el-icon> 学期绩点趋势</div>
          <v-chart v-if="trendOption" :option="trendOption" class="trend-chart" autoresize />
          <el-empty v-else description="暂无成绩数据" :image-size="48" />
        </div>

        <!-- AI 学情分析 -->
        <div class="ai-analysis-section">
          <div class="section-title">
            <el-icon><MagicStick /></el-icon> AI 学情智能分析
            <el-button type="primary" size="small" :loading="gradeLoading && !gradeRaw" @click="startAiAnalysis({ stream: true })" style="margin-left:auto">
              <el-icon v-if="!gradeLoading"><MagicStick /></el-icon>
              {{ gradeLoading && !gradeRaw ? '分析中...' : '重新分析' }}
            </el-button>
          </div>
          <div v-if="gradeRaw" class="ai-result-card">
            <div v-if="gradeLoading && gradeFromCache" class="ai-refresh-bar">
              <el-icon class="is-loading" :size="14"><Loading /></el-icon>
              <span>正在更新...</span>
            </div>
            <div class="ai-result-content" v-html="gradeRendered"></div>
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
              <div class="skeleton-line" style="width:45%"></div>
            </div>
          </div>
          <div v-else class="ai-placeholder">
            <el-icon :size="40" color="#ddd"><MagicStick /></el-icon>
            <p>点击"重新分析"按钮，AI 将为您分析学情数据</p>
          </div>
        </div>
      </div>

      <!-- 需加强课程 -->
      <div class="weak-courses-section" v-if="gradeAnalysis.weak_courses.length">
        <div class="section-title"><el-icon><Warning /></el-icon> 需加强课程</div>
        <div class="mini-course-list">
          <div v-for="c in gradeAnalysis.weak_courses.slice(0, 5)" :key="c.course_name" class="mini-course-item weak">
            <span class="mc-name">{{ c.course_name }}</span>
            <span class="mc-gpa">GPA {{ c.gpa }}</span>
          </div>
        </div>
      </div>

      <!-- 学期选择 -->
      <div class="sem-selector">
        <el-select v-model="selectedSem" placeholder="选择学期" style="width:200px">
          <el-option v-for="s in semesters" :key="s" :label="s" :value="s" />
        </el-select>
        <div v-if="selectedSem" class="sem-stats-inline">
          <span>{{ semStats[selectedSem]?.count }} 门</span>
          <span>均分 <b :style="{ color: avgColor(semStats[selectedSem]?.avg) }">{{ semStats[selectedSem]?.avg }}</b></span>
          <span>均绩 <b>{{ semStats[selectedSem]?.gpa }}</b></span>
          <span>学分 <b>{{ semStats[selectedSem]?.credits }}</b></span>
        </div>
      </div>

      <!-- 该学期成绩 -->
      <div v-if="selectedSem" class="selected-sem-grades">
        <div class="grade-grid">
          <div v-for="g in gradesBySem[selectedSem]" :key="g.id" class="grade-card" :class="scoreLevel(g.score)">
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
        <el-empty v-if="!gradesBySem[selectedSem]?.length" description="该学期暂无成绩" :image-size="48" />
      </div>

      <!-- 即将考试 -->
      <div v-if="upcomingExams.length" class="exam-section">
        <div class="section-title"><el-icon><WarningFilled /></el-icon> 即将考试</div>
        <div v-for="e in upcomingExams" :key="e.id" class="exam-card">
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

      <el-empty v-if="!grades.length && !upcomingExams.length" description="暂无考试成绩数据" />
    </div>

    <!-- ===== 成长轨迹 ===== -->
    <div v-if="activeTab === 'growth'" class="growth-view">
      <div class="score-header">
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
        <div class="score-stats">
          <div class="stat-item" v-for="s in statsCards" :key="s.label">
            <span class="stat-num">{{ s.value }}</span>
            <span class="stat-label">{{ s.label }}</span>
          </div>
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-card-header"><el-icon style="margin-right:6px"><DataAnalysis /></el-icon> 综合能力雷达</div>
          <v-chart :option="radarOption" class="chart" autoresize />
        </div>
        <div class="chart-card">
          <div class="chart-card-header"><el-icon style="margin-right:6px"><Histogram /></el-icon> 成长类型分布</div>
          <v-chart :option="growthBarOption" class="chart" autoresize />
        </div>
      </div>

      <div class="charts-row">
        <div class="chart-card wide">
          <div class="chart-card-header"><el-icon style="margin-right:6px"><TrendCharts /></el-icon> 成长趋势</div>
          <v-chart :option="growthLineOption" class="chart" autoresize />
        </div>
        <div class="chart-card wide">
          <div class="chart-card-header"><el-icon style="margin-right:6px"><DataLine /></el-icon> 学习绩点轨迹</div>
          <v-chart :option="gpaOption" class="chart" autoresize />
        </div>
      </div>

      <div class="split-row">
        <div class="tag-card">
          <div class="tag-card-header">
            <span><el-icon style="margin-right:6px"><Coin /></el-icon> 技能标签</span>
            <el-button size="small" type="primary" plain @click="saveSkills">保存</el-button>
          </div>
          <div class="preset-tags">
            <el-tag v-for="p in skillPresets" :key="p"
              :type="localSkills.includes(p) ? 'primary' : 'info'"
              :effect="localSkills.includes(p) ? 'dark' : 'plain'"
              class="preset-tag" @click="toggleSkill(p)">
              {{ p }}
            </el-tag>
          </div>
          <div class="tag-cloud">
            <el-tag v-for="s in localSkills" :key="s" closable :type="skillPresets.includes(s) ? 'primary' : 'warning'"
              @close="removeSkill(s)" class="skill-tag">{{ s }}</el-tag>
          </div>
          <div class="tag-input-row">
            <el-input v-model="newSkill" placeholder="自定义技能" size="small" @keyup.enter="addCustomSkill" />
            <el-button size="small" type="primary" @click="addCustomSkill">添加</el-button>
          </div>
        </div>
        <div class="tag-card">
          <div class="tag-card-header">
            <span><el-icon style="margin-right:6px"><Star /></el-icon> 兴趣领域</span>
            <el-button size="small" type="primary" plain @click="saveSkills">保存</el-button>
          </div>
          <div class="preset-tags">
            <el-tag v-for="p in interestPresets" :key="p"
              :type="localInterests.includes(p) ? 'success' : 'info'"
              :effect="localInterests.includes(p) ? 'dark' : 'plain'"
              class="preset-tag" @click="toggleInterest(p)">
              {{ p }}
            </el-tag>
          </div>
          <div class="tag-cloud">
            <el-tag v-for="s in localInterests" :key="s" closable :type="interestPresets.includes(s) ? 'success' : 'warning'"
              @close="removeInterest(s)" class="skill-tag">{{ s }}</el-tag>
          </div>
          <div class="tag-input-row">
            <el-input v-model="newInterest" placeholder="自定义兴趣" size="small" @keyup.enter="addCustomInterest" />
            <el-button size="small" type="primary" @click="addCustomInterest">添加</el-button>
          </div>
        </div>
      </div>

      <div class="records-section">
        <div class="section-header clickable" @click="recordsExpanded = !recordsExpanded">
          <span class="header-left">
            <el-icon class="collapse-icon" :class="{ collapsed: !recordsExpanded }"><ArrowRight /></el-icon>
            <el-icon style="margin-right:6px"><Collection /></el-icon>
            成长记录
            <el-tag v-if="growthRecords.length" size="small" type="info" effect="plain" style="margin-left:8px">{{ growthRecords.length }}</el-tag>
          </span>
          <el-button type="primary" size="small" @click.stop="openDialog">添加记录</el-button>
        </div>
        <Transition name="collapse">
          <div v-show="recordsExpanded">
            <div v-if="growthRecords.length" class="records-list">
              <div v-for="r in growthRecords" :key="r.id" class="record-card">
                <div class="record-left">
                  <div class="record-dot" :style="{ background: dotColor(r.type) }"></div>
                  <div class="record-line"></div>
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
        </Transition>
      </div>

      <div class="projects-section">
        <div class="section-header clickable" @click="projectsExpanded = !projectsExpanded">
          <span class="header-left">
            <el-icon class="collapse-icon" :class="{ collapsed: !projectsExpanded }"><ArrowRight /></el-icon>
            <el-icon style="margin-right:6px"><FolderOpened /></el-icon>
            项目展示
            <el-tag v-if="projects.length" size="small" type="info" effect="plain" style="margin-left:8px">{{ projects.length }}</el-tag>
          </span>
          <el-button type="primary" size="small" @click.stop="openProjectDialog">添加项目</el-button>
        </div>
        <Transition name="collapse">
          <div v-show="projectsExpanded">
            <div v-if="projects.length" class="project-grid">
              <div v-for="p in projects" :key="p.id" class="project-card">
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
        </Transition>
      </div>

      <el-dialog v-model="projectDialogVisible" :title="editingProject ? '编辑项目' : '添加项目'" width="500px">
        <el-form :model="projectForm" label-width="100px">
          <el-form-item label="项目名称">
            <el-input v-model="projectForm.project_name" placeholder="请输入项目名称" />
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="开始日期">
                <el-date-picker v-model="projectForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束日期">
                <el-date-picker v-model="projectForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" clearable />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="是否团队">
            <el-switch v-model="projectForm.is_team" />
          </el-form-item>
          <el-form-item v-if="projectForm.is_team" label="团队成员">
            <el-input v-model="projectForm.team_members" placeholder="逗号分隔，如：张三, 李四, 王五" />
          </el-form-item>
          <el-form-item label="项目成果">
            <UploadBtn v-model="projectForm.attachment_url" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="projectDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveProject">{{ editingProject ? '保存' : '添加' }}</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="dialogVisible" :title="'添加成长记录 — ' + typeLabel(form.type)" width="600px" class="growth-dialog">
        <el-form :model="form" label-width="100px">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="类型">
                <el-select v-model="form.type" @change="onTypeChange">
                  <el-option label="荣誉" value="honor" />
                  <el-option label="竞赛" value="competition" />
                  <el-option label="实践" value="practice" />
                  <el-option label="论文" value="paper" />
                  <el-option label="成果" value="achievement" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="日期">
                <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <template v-if="form.type === 'honor'">
            <el-form-item label="荣誉等级">
              <el-select v-model="form.honor_level" style="width:100%">
                <el-option label="校级" value="校级" />
                <el-option label="省级" value="省级" />
                <el-option label="国家级" value="国家级" />
                <el-option label="国际级" value="国际级" />
              </el-select>
            </el-form-item>
            <el-form-item label="荣誉名称">
              <el-input v-model="form.title" placeholder="例如：国家奖学金" />
            </el-form-item>
            <el-form-item label="荣誉描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="颁发单位、获奖时间等" />
            </el-form-item>
            <el-form-item label="证明材料">
              <UploadBtn v-model="form.attachment_url" />
            </el-form-item>
          </template>

          <template v-if="form.type === 'competition'">
            <el-form-item label="竞赛名称">
              <el-input v-model="form.title" placeholder="例如：ACM-ICPC国际大学生程序设计竞赛" />
            </el-form-item>
            <el-form-item label="主办方">
              <el-input v-model="form.organizer" placeholder="例如：ACM/ICPC组委会" />
            </el-form-item>
            <el-form-item label="竞赛等级">
              <el-select v-model="form.competition_level" style="width:100%">
                <el-option label="校级" value="校级" />
                <el-option label="省级" value="省级" />
                <el-option label="国家级" value="国家级" />
                <el-option label="国际级" value="国际级" />
              </el-select>
            </el-form-item>
            <el-form-item label="获奖情况">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="金奖/银奖/铜奖/一等奖等" />
            </el-form-item>
            <el-form-item label="证明材料">
              <UploadBtn v-model="form.attachment_url" />
            </el-form-item>
          </template>

          <template v-if="form.type === 'practice'">
            <el-form-item label="实践类型">
              <el-select v-model="form.practice_type" style="width:100%">
                <el-option label="社会志愿活动" value="社会志愿活动" />
                <el-option label="三下乡" value="三下乡" />
                <el-option label="支教" value="支教" />
                <el-option label="西部计划" value="西部计划" />
                <el-option label="筑梦扬帆计划" value="筑梦扬帆计划" />
                <el-option label="其他社会实践" value="其他社会实践" />
              </el-select>
            </el-form-item>
            <el-form-item label="实践名称">
              <el-input v-model="form.title" placeholder="例如：暑期三下乡支教活动" />
            </el-form-item>
            <el-form-item label="实践描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="实践内容、服务时长等" />
            </el-form-item>
            <el-form-item label="荣誉证明">
              <el-input v-model="form.practice_certificate" type="textarea" :rows="2" placeholder="优秀志愿者证书/表彰文件等" />
            </el-form-item>
            <el-form-item label="证明材料">
              <UploadBtn v-model="form.attachment_url" />
            </el-form-item>
          </template>

          <template v-if="form.type === 'paper'">
            <el-form-item label="论文题目">
              <el-input v-model="form.paper_name" placeholder="论文完整标题" />
            </el-form-item>
            <el-form-item label="期刊类型">
              <el-select v-model="form.paper_type" style="width:100%">
                <el-option label="普刊" value="普刊" />
                <el-option label="核心期刊" value="核心期刊" />
                <el-option label="SCI" value="SCI" />
                <el-option label="EI" value="EI" />
                <el-option label="顶刊" value="顶刊" />
                <el-option label="会议论文" value="会议论文" />
              </el-select>
            </el-form-item>
            <el-form-item label="第一作者">
              <el-input v-model="form.first_author" placeholder="姓名" />
            </el-form-item>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="第二作者">
                  <el-input v-model="form.second_author" placeholder="姓名（选填）" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="第三作者">
                  <el-input v-model="form.third_author" placeholder="姓名（选填）" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="备注">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="发表时间、期刊名称等" />
            </el-form-item>
            <el-form-item label="证明材料">
              <UploadBtn v-model="form.attachment_url" />
            </el-form-item>
          </template>

          <template v-if="form.type === 'achievement'">
            <el-form-item label="成果类型">
              <el-select v-model="form.achievement_type" style="width:100%">
                <el-option label="发明专利" value="发明专利" />
                <el-option label="实用新型专利" value="实用新型专利" />
                <el-option label="外观设计专利" value="外观设计专利" />
                <el-option label="软件著作权" value="软件著作权" />
                <el-option label="作品著作权" value="作品著作权" />
              </el-select>
            </el-form-item>
            <el-form-item label="成果名称">
              <el-input v-model="form.achievement_name" placeholder="专利/软著名称" />
            </el-form-item>
            <el-form-item label="成果标题">
              <el-input v-model="form.title" placeholder="简短标题（可选）" />
            </el-form-item>
            <el-form-item label="成果描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="授权号、申请日等信息" />
            </el-form-item>
            <el-form-item label="证明材料">
              <UploadBtn v-model="form.attachment_url" />
            </el-form-item>
          </template>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAdd">确认添加</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCourses as fetchCourses, getGrades, getExams } from '@/api/academic'
import { getGradeAnalysis, type GradeAnalysis } from '@/api/gradeAnalysis'
import { ArrowLeft, ArrowRight, Sunny, WarningFilled, Location, TrendCharts, Aim, CircleCheckFilled, Lock, Calendar, MagicStick, Loading, Document, Star, Trophy, Warning, DataAnalysis, Histogram, DataLine, Coin, Collection, FolderOpened, Link, User, UserFilled } from '@element-plus/icons-vue'
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
import UploadBtn from '@/components/upload/UploadBtn.vue'

use([LineChart, BarChart, PieChart, RadarChart, GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, RadarComponent, CanvasRenderer])

const auth = useAuthStore()
const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'schedule')

// ===== 成绩分析 =====
const gradeAnalysisLoading = ref(false)
const gradeAnalysis = ref<GradeAnalysis>({
  stats: {
    total_courses: 0,
    total_credits: 0,
    avg_score: 0,
    avg_gpa: 0,
    highest_gpa: 0,
    lowest_gpa: 0,
    pass_rate: 0
  },
  semester_gpa: [],
  course_type_stats: [],
  score_distribution: [],
  top_courses: [],
  weak_courses: []
})

// 成绩分布图配置
const distributionOption = computed(() => {
  const data = gradeAnalysis.value.score_distribution
  if (!data || data.length === 0) return null
  return {
    tooltip: { trigger: 'axis', appendToBody: true },
    grid: { left: 55, right: 20, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.range),
      name: '分数段',
      nameLocation: 'center',
      nameGap: 25,
      axisLabel: { color: '#666' }
    },
    yAxis: {
      type: 'value',
      name: '人数',
      nameLocation: 'center',
      nameGap: 35,
      axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: [{
      type: 'bar',
      data: data.map(d => d.count),
      barWidth: '50%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: (params: any) => {
          const colors = ['#67c23a', '#409eff', '#e6a23c', '#f56c6c', '#909399']
          return colors[params.dataIndex] || '#409eff'
        }
      }
    }]
  }
})

// 学期GPA趋势图配置
const semesterGpaOption = computed(() => {
  const data = gradeAnalysis.value.semester_gpa
  if (!data || data.length === 0) return null
  return {
    tooltip: { trigger: 'axis', appendToBody: true },
    grid: { left: 55, right: 60, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: data.map(s => s.semester),
      name: '学期',
      nameLocation: 'center',
      nameGap: 25,
      axisLabel: { color: '#666', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 4,
      name: '绩点',
      nameLocation: 'center',
      nameGap: 35,
      axisLabel: { color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    },
    series: [{
      type: 'line',
      data: data.map(s => s.gpa),
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#409eff', width: 3 },
      itemStyle: { color: '#409eff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.05)' }
          ]
        }
      },
      markLine: {
        data: [
          { yAxis: 3.5, label: { formatter: '优秀', color: '#67c23a' } },
          { yAxis: 2.5, label: { formatter: '警戒', color: '#f56c6c' } }
        ],
        lineStyle: { type: 'dashed' }
      }
    }]
  }
})

async function loadGradeAnalysis() {
  gradeAnalysisLoading.value = true
  try {
    const data = await getGradeAnalysis(auth.user?.id || 0)
    gradeAnalysis.value = data
  } catch (error) {
    console.error('加载成绩分析失败:', error)
  } finally {
    gradeAnalysisLoading.value = false
  }
}

// ===== 课程表 =====
const days = ['周一', '周二', '周三', '周四', '周五']
const periodLabels = ['第1节<br>08:00', '第2节<br>08:55', '第3节<br>10:00', '第4节<br>10:55', '第5节<br>14:00', '第6节<br>14:55', '第7节<br>15:50', '第8节<br>16:45', '第9节<br>19:00', '第10节<br>19:55']
const courses = ref<Course[]>([])

const weekOffset = ref(0)
const baseWeek = ref(1)
const slideDir = ref<'left' | 'right'>('left')
const scheduleReady = ref(false)

const currentWeek = computed(() => Math.max(1, baseWeek.value + weekOffset.value))

const currentWeekCourses = computed(() => {
  const wk = currentWeek.value
  return courses.value.filter(c => wk >= c.week_start && wk <= c.week_end)
})

const uniqueCourseCount = computed(() => {
  return new Set(currentWeekCourses.value.map(c => c.name)).size
})

const maxPeriod = computed(() => {
  const wk = currentWeek.value
  const wkCourses = courses.value.filter(c => wk >= c.week_start && wk <= c.week_end)
  return Math.max(...wkCourses.map(c => c.end_period), 10)
})

const dayMap: Record<string, number> = { '周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7 }

const courseGrid = computed(() => {
  const wk = currentWeek.value
  const rows = []
  for (let p = 1; p <= maxPeriod.value; p++) {
    const cells = days.map(day => ({
      day,
      courses: courses.value.filter(c =>
        c.day_of_week === dayMap[day] &&
        c.start_period === p &&
        wk >= c.week_start && wk <= c.week_end
      )
    }))
    rows.push({ period: p, cells })
  }
  return rows
})

const todayLabel = computed(() => {
  const d = new Date().getDay()
  return ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][d] || ''
})

const todayCourses = computed(() => {
  const day = todayLabel.value
  if (!day) return []
  const wk = currentWeek.value
  return courses.value.filter(c =>
    c.day_of_week === dayMap[day] &&
    wk >= c.week_start && wk <= c.week_end
  ).sort((a, b) => a.start_period - b.start_period)
})

const todayCoursesRealWeek = computed(() => {
  const day = todayLabel.value
  if (!day) return []
  const wk = calcCurrentRealWeek()
  return courses.value.filter(c =>
    c.day_of_week === dayMap[day] &&
    wk >= c.week_start && wk <= c.week_end
  )
})

function calcCurrentRealWeek() {
  const now = new Date()
  const year = now.getFullYear()
  let semesterStart: Date
  if (now.getMonth() >= 8) {
    semesterStart = new Date(year, 8, 1)
  } else if (now.getMonth() >= 1) {
    semesterStart = new Date(year, 1, 24)
  } else {
    semesterStart = new Date(year - 1, 8, 1)
  }
  const diff = (now.getTime() - semesterStart.getTime()) / (7 * 24 * 60 * 60 * 1000)
  return Math.max(1, Math.floor(diff) + 1)
}

const isCurrentRealWeek = computed(() => currentWeek.value === calcCurrentRealWeek())

const palette = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9b59b6', '#1abc9c', '#e67e22', '#2ecc71', '#3498db', '#e74c3c']
const colorMap: Record<string, string> = {}
let colorIdx = 0
function courseColor(name: string) {
  if (!colorMap[name]) {
    colorMap[name] = palette[colorIdx % palette.length] + '18'
    colorIdx++
  }
  return colorMap[name]
}

function dayLabel(d: number) {
  return ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][d] || ''
}

function goPrevWeek() {
  if (currentWeek.value > 1) {
    slideDir.value = 'right'
    weekOffset.value--
  }
}
function goNextWeek() {
  slideDir.value = 'left'
  weekOffset.value++
}
function resetWeek() {
  if (isCurrentRealWeek.value) {
    ElMessage.info('已经在本周了')
    return
  }
  if (courses.value.length) {
    const realWeek = calcCurrentRealWeek()
    slideDir.value = currentWeek.value > realWeek ? 'right' : 'left'
    baseWeek.value = Math.min(...courses.value.map(c => c.week_start))
    weekOffset.value = realWeek - baseWeek.value
  }
}

// ===== 课程AI分析 =====
const { loading: scheduleLoading, rawResult: scheduleRaw, renderedResult: scheduleRendered, fromCache: scheduleFromCache, analyze: runScheduleAnalysis, reset: resetSchedule } = useAiAnalysis('schedule')

async function startScheduleAiAnalysis(opts?: { stream?: boolean }) {
  const scheduleData = courses.value.map(c => ({
    name: c.name,
    teacher: c.teacher,
    location: c.location,
    day: dayLabel(c.day_of_week),
    periods: `第${c.start_period}-${c.end_period}节`,
    weeks: `第${c.week_start}-${c.week_end}周`
  }))

  const todayCoursesData = todayCourses.value.map(c => ({
    name: c.name,
    teacher: c.teacher,
    location: c.location,
    periods: `第${c.start_period}-${c.end_period}节`
  }))

  const prompt = `请根据以下课表数据，为学生提供详细的学习规划建议：
1. 每日学习时间安排建议
2. 课前预习和课后复习的安排
3. 各科目的学习重点和方法
4. 周末和空闲时间的利用建议
5. 考试周的复习规划

本周课程安排：
${JSON.stringify(scheduleData, null, 2)}

今日课程：
${JSON.stringify(todayCoursesData, null, 2)}

当前周数：第${currentWeek.value}周`

  try {
    if (opts?.stream) resetSchedule()
    await runScheduleAnalysis(prompt, opts?.stream ? {
      skipCache: true,
      onStream: (chunk) => { scheduleRaw.value += chunk },
    } : undefined)
  } catch (e: any) {
    ElMessage.error('AI 分析失败：' + (e.message || '请稍后重试'))
  }
}

// ===== 考试成绩 =====
const grades = ref<Grade[]>([])
const exams = ref<Exam[]>([])
const selectedSem = ref('')
const goals = ref<Record<string, number>>({})
const goalInputs = ref<Record<string, number>>({})

// ===== AI 学情分析 =====
const { loading: gradeLoading, rawResult: gradeRaw, renderedResult: gradeRendered, fromCache: gradeFromCache, analyze: runGradeAnalysis, reset: resetGrade } = useAiAnalysis('grades')

async function startAiAnalysis(opts?: { stream?: boolean }) {
  const gradesData = grades.value.map(g => ({
    course: g.course_name,
    score: g.score,
    gpa: g.gpa,
    credit: g.credit,
    semester: g.semester
  }))

  const prompt = `请分析以下学生的成绩数据，给出学情分析报告：
1. 整体学业表现评估
2. 各学期绩点变化趋势分析
3. 优势科目和薄弱科目识别
4. 学习建议和改进方向

成绩数据：
${JSON.stringify(gradesData, null, 2)}

当前学期：${semesters.value[0] || '未知'}
目标绩点：${goals.value[semesters.value[0]] ?? '未设置'}`

  try {
    if (opts?.stream) resetGrade()
    await runGradeAnalysis(prompt, opts?.stream ? {
      skipCache: true,
      onStream: (chunk) => { gradeRaw.value += chunk },
    } : undefined)
  } catch (e: any) {
    ElMessage.error('AI 分析失败：' + (e.message || '请稍后重试'))
  }
}

const semesters = computed(() => [...new Set(grades.value.map(g => g.semester))].sort().reverse())

const gradesBySem = computed(() => {
  const map: Record<string, Grade[]> = {}
  for (const g of grades.value) {
    if (!map[g.semester]) map[g.semester] = []
    map[g.semester].push(g)
  }
  return map
})

const semStats = computed(() => {
  const stats: Record<string, { count: number; avg: number; gpa: string; credits: number }> = {}
  for (const [sem, gs] of Object.entries(gradesBySem.value)) {
    const scores = gs.filter(g => g.score != null).map(g => g.score)
    const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
    const gpa = gs.length ? (gs.reduce((s, g) => s + (g.gpa || 0), 0) / gs.length).toFixed(2) : '0.00'
    const credits = gs.reduce((s, g) => s + (g.credit || 0), 0)
    stats[sem] = { count: gs.length, avg, gpa, credits }
  }
  return stats
})

const trendOption = computed(() => {
  const sems = [...semesters.value].reverse()
  if (!sems.length) return null
  const gpaData = sems.map(s => parseFloat(semStats.value[s]?.gpa || '0'))
  const semLabels = sems.map(s => {
    const parts = s.split('-')
    return parts.length >= 3 ? parts.slice(0, 2).join('-') + (parts[2] === '1' ? '上' : '下') : s
  })
  return {
    tooltip: { trigger: 'axis', appendToBody: true, formatter: (p: any) => `${p[0].axisValue}<br/>绩点: ${p[0].value}` },
    grid: { left: 55, right: 60, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: semLabels, name: '学期', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666', fontSize: 12 } },
    yAxis: { type: 'value', min: 0, max: 4, name: '绩点', nameLocation: 'center', nameGap: 35, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      {
        type: 'bar', data: gpaData, barWidth: '40%',
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#409eff80' }, { offset: 1, color: '#409eff20' }] },
        },
      },
      {
        type: 'line', data: gpaData, smooth: true,
        symbol: 'circle', symbolSize: 8,
        lineStyle: { color: '#409eff', width: 3 },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#409eff40' }, { offset: 1, color: '#409eff05' }] } },
        markLine: { data: [{ yAxis: goals.value[semesters.value[0]] ?? 3.5, label: { formatter: '目标 ' + (goals.value[semesters.value[0]] ?? 3.5), color: '#e6a23c' } }], silent: true, lineStyle: { type: 'dashed', color: '#e6a23c' } },
      },
    ],
  }
})

const upcomingExams = computed(() => {
  const now = new Date()
  return exams.value.filter(e => !e.exam_date || new Date(e.exam_date) >= now)
    .sort((a, b) => (a.exam_date || '').localeCompare(b.exam_date || ''))
})

function scoreLevel(s: number) {
  if (s >= 90) return 'level-a'
  if (s >= 80) return 'level-b'
  if (s >= 70) return 'level-c'
  if (s >= 60) return 'level-d'
  return 'level-f'
}

function avgColor(s?: number) {
  if (!s) return '#999'
  if (s >= 90) return '#67c23a'
  if (s >= 80) return '#409eff'
  if (s >= 70) return '#e6a23c'
  return '#f56c6c'
}

function formatDate(d: string) {
  if (!d) return ''
  const parts = d.split('-')
  return parts[1] + '/' + parts[2]
}

function loadGoals() {
  try {
    const raw = localStorage.getItem('student_sem_goals')
    if (raw) goals.value = JSON.parse(raw)
  } catch { goals.value = {} }
}

function saveGoalForSem(sem: string) {
  const val = goalInputs.value[sem]
  if (val == null) return
  goals.value[sem] = val
  localStorage.setItem('student_sem_goals', JSON.stringify(goals.value))
  ElMessage.success(`${sem} 目标已保存`)
}

// ===== 成长轨迹 =====
const skillPresets = ['编程开发', 'UI/UX设计', '数据分析', '人工智能', '项目管理', '产品设计', '视频剪辑', '摄影', '写作', '翻译', '演讲', '团队协作', '领导力']
const interestPresets = ['音乐', '运动', '阅读', '游戏', '旅行', '美食', '电影', '摄影', '绘画', '舞蹈', '编程', '创业', '公益']

const profile = ref<GrowthProfile | null>(null)
const growthRecords = ref<GrowthRecord[]>([])
const recordsExpanded = ref(false)
const projectsExpanded = ref(false)
const dialogVisible = ref(false)
const form = ref<Record<string, any>>({ type: 'honor', title: '', description: '', date: '' })

const localSkills = ref<string[]>([])
const localInterests = ref<string[]>([])
const newSkill = ref('')
const newInterest = ref('')

const projects = ref<StudentProject[]>([])
const loaded = ref(false)
const projectDialogVisible = ref(false)
const editingProject = ref<StudentProject | null>(null)
const projectForm = ref<Record<string, any>>({
  project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '',
})

function toggleSkill(s: string) {
  const idx = localSkills.value.indexOf(s)
  if (idx >= 0) localSkills.value.splice(idx, 1)
  else localSkills.value.push(s)
}
function removeSkill(s: string) {
  localSkills.value = localSkills.value.filter(x => x !== s)
}
function addCustomSkill() {
  const s = newSkill.value.trim()
  if (!s) return
  if (!localSkills.value.includes(s)) localSkills.value.push(s)
  newSkill.value = ''
}
function toggleInterest(s: string) {
  const idx = localInterests.value.indexOf(s)
  if (idx >= 0) localInterests.value.splice(idx, 1)
  else localInterests.value.push(s)
}
function removeInterest(s: string) {
  localInterests.value = localInterests.value.filter(x => x !== s)
}
function addCustomInterest() {
  const s = newInterest.value.trim()
  if (!s) return
  if (!localInterests.value.includes(s)) localInterests.value.push(s)
  newInterest.value = ''
}
async function saveSkills() {
  try {
    await updateSkills({ skills: localSkills.value, interests: localInterests.value })
    ElMessage.success('技能/兴趣已保存')
    profile.value = await getGrowthProfile()
  } catch { ElMessage.error('保存失败') }
}
function openProjectDialog() {
  editingProject.value = null
  projectForm.value = { project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '' }
  projectDialogVisible.value = true
}
function editProject(p: StudentProject) {
  editingProject.value = p
  projectForm.value = { ...p }
  projectDialogVisible.value = true
}
async function handleSaveProject() {
  try {
    if (editingProject.value) {
      await updateProject(editingProject.value.id, projectForm.value as any)
      ElMessage.success('项目已更新')
    } else {
      await createProject(projectForm.value as any)
      ElMessage.success('项目已添加')
    }
    projectDialogVisible.value = false
    projects.value = await getProjects()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}
async function handleDeleteProject(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该项目？', '确认')
    await deleteProject(id)
    ElMessage.success('已删除')
    projects.value = await getProjects()
  } catch {}
}
function typeLabel(t: string) {
  const labels: Record<string, string> = { honor: '荣誉', competition: '竞赛', practice: '实践', paper: '论文', achievement: '成果' }
  return labels[t] || t
}
function typeTagType(t: string) {
  const types: Record<string, string> = { honor: 'warning', competition: 'primary', practice: 'success', paper: 'danger', achievement: 'info' }
  return types[t] || 'default'
}
function dotColor(t: string) {
  const colors: Record<string, string> = { honor: '#e6a23c', competition: '#409eff', practice: '#67c23a', paper: '#f56c6c', achievement: '#909399' }
  return colors[t] || '#bbb'
}
function formatGrowthDate(d: string) {
  if (!d) return ''
  return d.slice(0, 10)
}
function onTypeChange() {
  form.value.title = ''
  form.value.description = ''
  form.value.honor_level = ''
  form.value.organizer = ''
  form.value.competition_level = ''
  form.value.practice_type = ''
  form.value.practice_certificate = ''
  form.value.paper_type = ''
  form.value.paper_name = ''
  form.value.first_author = ''
  form.value.second_author = ''
  form.value.third_author = ''
  form.value.achievement_type = ''
  form.value.achievement_name = ''
}
function openDialog() {
  onTypeChange()
  dialogVisible.value = true
}
async function handleAdd() {
  const payload: Record<string, any> = {}
  for (const k of Object.keys(form.value)) {
    if (form.value[k] !== '' && form.value[k] !== undefined) {
      payload[k] = form.value[k]
    }
  }
  try {
    await createGrowthRecord(payload as any)
    ElMessage.success('添加成功')
    dialogVisible.value = false
    growthRecords.value = await getGrowthRecords() as any
    profile.value = await getGrowthProfile() as any
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  }
}

const circleLen = 2 * Math.PI * 52
const circleOffset = computed(() => {
  if (!profile.value) return circleLen
  return circleLen - (circleLen * Math.min(100, profile.value.total_score) / 100)
})
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
  radar: {
    indicator: (profile.value?.radar ?? []).map(d => ({ name: d.name, max: 100 })),
    shape: 'circle',
    center: ['50%', '50%'],
    radius: '65%',
    axisName: { color: '#333', fontSize: 12 },
    splitArea: { areaStyle: { color: ['rgba(64,158,255,.03)', 'rgba(64,158,255,.06)'] } },
  },
  series: [{
    type: 'radar',
    data: [{ value: profile.value?.radar.map(d => d.value) ?? [0, 0, 0, 0, 0] }],
    areaStyle: { color: 'rgba(64,158,255,.2)' },
    lineStyle: { color: '#409eff', width: 2 },
    itemStyle: { color: '#409eff' },
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
    animationDelay: function(idx: number) { return idx * 100 }
  }],
  animationDuration: 2000,
  animationEasing: 'cubicOut' as const,
}))
const growthBarOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 55, right: 20, top: 20, bottom: 40 },
  xAxis: {
    type: 'category',
    data: (profile.value?.stats_by_type ?? []).map(s => s.name),
    name: '成长类型',
    nameLocation: 'center',
    nameGap: 25,
    axisLabel: { color: '#666' },
  },
  yAxis: { type: 'value', name: '数量', nameLocation: 'center', nameGap: 35, minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
  series: [{
    type: 'bar',
    data: (profile.value?.stats_by_type ?? []).map(s => s.value),
    barWidth: '40%',
    itemStyle: {
      borderRadius: [6, 6, 0, 0],
      color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#409eff' }, { offset: 1, color: '#67c23a' }] },
    },
    animationDuration: 1500,
    animationEasing: 'elasticOut' as const,
    animationDelay: function(idx: number) { return idx * 200 }
  }],
  animationDuration: 1500,
  animationEasing: 'cubicOut' as const,
}))
const growthLineOption = computed(() => {
  const trend = profile.value?.monthly_trend ?? []
  const months = [...new Set(trend.map(t => t.month))].sort()
  const types = [...new Set(trend.map(t => t.type))]
  const colors: Record<string, string> = { honor: '#e6a23c', competition: '#409eff', practice: '#67c23a', paper: '#f56c6c', achievement: '#909399' }
  const gTypeLabels: Record<string, string> = { honor: '荣誉', competition: '竞赛', practice: '实践', paper: '论文', achievement: '成果' }
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: types.map(t => gTypeLabels[t] || t), bottom: 0 },
    grid: { left: 55, right: 20, top: 20, bottom: 65 },
    xAxis: { type: 'category', data: months, name: '月份', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', name: '记录数', nameLocation: 'center', nameGap: 35, minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: types.map(t => ({
      name: gTypeLabels[t] || t,
      type: 'line',
      smooth: true,
      data: months.map(m => trend.find(item => item.month === m && item.type === t)?.count ?? 0),
      itemStyle: { color: colors[t] || '#909399' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: (colors[t] || '#909399') + '40' }, { offset: 1, color: (colors[t] || '#909399') + '05' }] } },
      animationDuration: 2000,
      animationEasing: 'cubicOut' as const,
      animationDelay: function(idx: number) { return idx * 100 }
    })),
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
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
    grid: { left: 55, right: 60, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: semLabels, name: '学期', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666', fontSize: 13 } },
    yAxis: { type: 'value', min: minGpa, max: 4.0, name: '绩点', nameLocation: 'center', nameGap: 35, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [{
      type: 'line', data: values, smooth: true,
      symbol: 'circle', symbolSize: 10,
      lineStyle: { color: '#e6a23c', width: 3 },
      itemStyle: { color: '#e6a23c' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#e6a23c40' }, { offset: 1, color: '#e6a23c05' }] } },
      markLine: { data: [{ yAxis: 3.5, label: { formatter: '优秀线 3.5', color: '#67c23a' } }, { yAxis: 2.5, label: { formatter: '警戒线 2.5', color: '#f56c6c' } }], silent: true, lineStyle: { type: 'dashed' } },
      animationDuration: 2000,
      animationEasing: 'cubicOut' as const,
      animationDelay: function(idx: number) { return idx * 200 }
    }],
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
  }
})

onMounted(async () => {
  loadGoals()

  const coursePromise = fetchCourses().then(d => { courses.value = d as any }).catch(() => {})
  const gradesPromise = getGrades().then(d => { grades.value = d as any }).catch(() => {})
  const examsPromise = getExams().then(d => { exams.value = d as any }).catch(() => {})
  await Promise.all([coursePromise, gradesPromise, examsPromise])
  if (courses.value.length) {
    baseWeek.value = Math.min(...courses.value.map(c => c.week_start))
    const realWeek = calcCurrentRealWeek()
    weekOffset.value = realWeek - baseWeek.value
  }
  scheduleReady.value = true
  if (semesters.value.length) selectedSem.value = semesters.value[0]
  for (const sem of semesters.value) {
    if (goalInputs.value[sem] == null) {
      goalInputs.value[sem] = goals.value[sem] ?? 3.5
    }
  }
  
  // 加载成绩分析
  loadGradeAnalysis()

  // AI分析：有缓存立即显示，无缓存前台等待
  if (courses.value.length) {
    startScheduleAiAnalysis()
  }
  if (grades.value.length) {
    startAiAnalysis()
  }

  // 加载成长数据
  try {
    const p = await getGrowthProfile()
    profile.value = p
    localSkills.value = [...(p.skills || [])]
    localInterests.value = [...(p.interests || [])]
  } catch {}
  try { growthRecords.value = await getGrowthRecords() as any } catch {}
  try { projects.value = await getProjects(); loaded.value = true } catch {}
})

watch(semesters, (list) => {
  if (list.length && !list.includes(selectedSem.value)) {
    selectedSem.value = list[0]
  }
  for (const sem of list) {
    if (goalInputs.value[sem] == null) {
      goalInputs.value[sem] = goals.value[sem] ?? 3.5
    }
  }
})

watch(() => route.query.tab, (val) => {
  if (val && typeof val === 'string') activeTab.value = val
})
</script>

<style scoped>
.schedule-page { 
  height: 100%; 
  max-width: 1200px; 
  width: 100%; 
  margin: 0 auto; 
  padding: 12px 24px 0; 
  display: flex; 
  flex-direction: column; 
  box-sizing: border-box; 
  overflow-y: auto; 
  scrollbar-width: none; 
  -ms-overflow-style: none;
  animation: fadeInUp 0.35s ease-out;
}
.schedule-page::-webkit-scrollbar { display: none; }
.schedule-view, .grades-view { display: flex; flex-direction: column; }
.schedule-view::-webkit-scrollbar, .grades-view::-webkit-scrollbar { display: none; }

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes slideInDown {
  from { opacity: 0; transform: translateY(-30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.animate-fade-in-up { animation: fadeInUp 0.35s ease-out; }
.animate-fade-in-left { animation: fadeInLeft 0.35s ease-out; }
.animate-fade-in-right { animation: fadeInRight 0.35s ease-out; }
.animate-scale-in { animation: scaleIn 0.3s ease-out; }
.animate-slide-in-down { animation: slideInDown 0.3s ease-out; }
.animate-pulse { animation: pulse 1.5s ease-in-out infinite; }
.animate-float { animation: float 2s ease-in-out infinite; }

.delay-100 { animation-delay: 0.03s; }
.delay-200 { animation-delay: 0.06s; }
.delay-300 { animation-delay: 0.09s; }
.delay-400 { animation-delay: 0.12s; }
.delay-500 { animation-delay: 0.15s; }

.text-gradient {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.text-glow {
  text-shadow: 0 0 10px rgba(64, 158, 255, 0.3);
}
.hover-lift {

  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.12);
}

/* ===== Page Tabs ===== */
.page-tabs { 
  display: flex; 
  gap: 4px; 
  margin-bottom: 20px; 
  background: #f5f7fa; 
  border-radius: 10px; 
  padding: 4px;
  animation: fadeInUp 0.35s ease-out;
}
.tab-item {
  flex: 1; text-align: center; padding: 8px 0; font-size: 14px; font-weight: 600;
  border-radius: 8px; cursor: pointer; transition: all .2s; color: #666;
}
.tab-item:hover { 
  color: #333; 
  transform: translateY(-2px);
}
.tab-item.active { 
  background: #fff; 
  color: #409eff; 
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  animation: scaleIn 0.3s ease-out;
}

/* ===== Overview Cards ===== */
.overview-cards {
  display: flex; gap: 10px; margin-bottom: 16px;
  animation: fadeInUp 0.35s ease-out;
}
.overview-card {
  flex: 1; display: flex; align-items: center; gap: 12px;
  padding: 14px; border-radius: 10px;
  background: linear-gradient(135deg, var(--bg-card), var(--bg-primary));
  border: 1px solid var(--border-color);
}
.oc-icon {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.oc-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.oc-label { font-size: 11px; color: var(--text-muted); }

/* ===== Toolbar ===== */
.schedule-toolbar {
  display: flex; justify-content: flex-start; align-items: center;
  margin-bottom: 20px; padding: 0 4px; flex-wrap: wrap; gap: 10px;
  animation-delay: 0.2s;
  animation-fill-mode: both;
}
.week-info { display: flex; align-items: center; gap: 10px; }
.week-label { 
  font-size: 18px; 
  font-weight: 700; 
  color: #1a1a2e; 
  min-width: 80px; 
  text-align: center; 
  letter-spacing: 1px;
  transition: all 0.3s ease;
}
.week-label:hover {
  color: #409eff;
  text-shadow: 0 0 10px rgba(64, 158, 255, 0.3);
}
.week-count-tag {
  display: inline-flex; align-items: center; gap: 4px;
  background: linear-gradient(135deg, rgba(99,102,241,.08), rgba(99,102,241,.04));
  border: 1px solid rgba(99,102,241,.15); border-radius: 20px;
  color: #6366f1; font-size: 12px; font-weight: 500; padding: 0 12px; height: 26px;
}
.week-count-tag .el-icon { font-size: 12px; }
.today-count-tag {
  display: inline-flex; align-items: center; gap: 4px;
  background: linear-gradient(135deg, rgba(34,197,94,.08), rgba(34,197,94,.04));
  border: 1px solid rgba(34,197,94,.15); border-radius: 20px;
  color: #16a34a; font-size: 12px; font-weight: 500; padding: 0 12px; height: 26px;
}
.today-count-tag .el-icon { font-size: 12px; }

/* ===== Schedule Main Row ===== */
.schedule-main-row { 
  display: flex; 
  gap: 16px; 
  margin-bottom: 28px;
  animation: fadeInUp 0.35s ease-out;
  animation-delay: 0.3s;
  animation-fill-mode: both;
}

/* ===== Grid ===== */
.schedule-grid {
  display: flex; flex-direction: column; border-radius: 14px;
  border: 1px solid rgba(0,0,0,.06); overflow: hidden; background: #fff;
  box-shadow: 0 2px 12px rgba(0,0,0,.04);
  flex: 2;
  transition: all 0.3s ease;
}
.schedule-grid:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}
.schedule-ai-section { 
  flex: 1; 
  min-width: 0; 
  display: flex; 
  flex-direction: column;
  animation: fadeInRight 0.35s ease-out;
  animation-delay: 0.4s;
  animation-fill-mode: both;
}
.schedule-ai-section .section-title {
  font-size: 16px; font-weight: 700; color: #1a1a2e;
  padding-bottom: 14px; margin-bottom: 14px; border-bottom: 2px solid #409eff;
  display: flex; align-items: center; gap: 6px;
}
.schedule-ai-section .ai-result-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f5ff 100%);
  border-radius: 12px; padding: 20px 24px;
  border: 1px solid rgba(64,158,255,.15);
  box-shadow: 0 2px 12px rgba(64,158,255,.08);
  max-height: 420px; overflow-y: auto;
  scrollbar-width: thin; -ms-overflow-style: auto;
}
.schedule-ai-section .ai-result-card::-webkit-scrollbar { width: 4px; display: block; }
.schedule-ai-section .ai-result-card::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.schedule-ai-section .ai-result-card::-webkit-scrollbar { display: none; }
.schedule-ai-section .ai-result-content {
  font-size: 14px; line-height: 1.8; color: #333;
  word-break: break-word;
}
.schedule-ai-section .ai-result-content :deep(p.md-p) { margin: 6px 0; }
.schedule-ai-section .ai-result-content :deep(h1),
.schedule-ai-section .ai-result-content :deep(h2),
.schedule-ai-section .ai-result-content :deep(h3),
.schedule-ai-section .ai-result-content :deep(h4) {
  font-weight: 600; color: #1a1a2e;
  margin: 16px 0 8px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(64,158,255,.1);
}
.schedule-ai-section .ai-result-content :deep(h1) { font-size: 20px; }
.schedule-ai-section .ai-result-content :deep(h2) { font-size: 18px; }
.schedule-ai-section .ai-result-content :deep(h3) { font-size: 16px; }
.schedule-ai-section .ai-result-content :deep(h4) { font-size: 15px; }
.schedule-ai-section .ai-result-content :deep(h1:first-child),
.schedule-ai-section .ai-result-content :deep(h2:first-child),
.schedule-ai-section .ai-result-content :deep(h3:first-child),
.schedule-ai-section .ai-result-content :deep(h4:first-child) { margin-top: 0; }
.schedule-ai-section .ai-result-content :deep(strong) { color: #409eff; font-weight: 600; }
.schedule-ai-section .ai-result-content :deep(em) { font-style: italic; color: #555; }
.schedule-ai-section .ai-result-content :deep(del) { text-decoration: line-through; color: #999; }
.schedule-ai-section .ai-result-content :deep(ul.md-ul),
.schedule-ai-section .ai-result-content :deep(ol.md-ol) { margin: 8px 0; padding-left: 24px; }
.schedule-ai-section .ai-result-content :deep(li.md-li) { margin: 4px 0; color: #555; line-height: 1.7; }
.schedule-ai-section .ai-result-content :deep(a.md-link) {
  color: #409eff; text-decoration: none; border-bottom: 1px dashed rgba(64,158,255,.4);
}
.schedule-ai-section .ai-result-content :deep(a.md-link:hover) { border-bottom-color: #409eff; }
.schedule-ai-section .ai-result-content :deep(code.md-inline-code) {
  background: rgba(64,158,255,.08); color: #e6a23c;
  padding: 2px 6px; border-radius: 4px; font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.schedule-ai-section .ai-result-content :deep(pre.md-code-block) {
  background: #1e1e2e; color: #cdd6f4;
  padding: 14px 18px; border-radius: 8px;
  overflow-x: auto; margin: 10px 0;
  font-size: 13px; line-height: 1.6;
}
.schedule-ai-section .ai-result-content :deep(pre.md-code-block code) {
  background: none; color: inherit; padding: 0;
  font-family: 'Consolas', 'Monaco', monospace;
}
.schedule-ai-section .ai-result-content :deep(blockquote.md-blockquote) {
  border-left: 4px solid #409eff; margin: 10px 0;
  padding: 8px 16px; background: rgba(64,158,255,.05);
  border-radius: 0 8px 8px 0; color: #555;
}
.schedule-ai-section .ai-result-content :deep(hr.md-hr) {
  border: none; border-top: 1px solid #e8e8e8; margin: 16px 0;
}
.schedule-ai-section .ai-result-content :deep(table.md-table) {
  width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px;
}
.schedule-ai-section .ai-result-content :deep(th.md-th),
.schedule-ai-section .ai-result-content :deep(td.md-td) {
  border: 1px solid #e8e8e8; padding: 8px 12px; text-align: left;
}
.schedule-ai-section .ai-result-content :deep(th.md-th) {
  background: #f5f7fa; font-weight: 600; color: #1a1a2e;
}
.schedule-ai-section .ai-result-content :deep(tr.md-tr:hover) { background: rgba(64,158,255,.03); }
.schedule-ai-section .ai-result-content :deep(img.md-image) {
  max-width: 100%; border-radius: 8px; margin: 8px 0;
}
.schedule-ai-section .ai-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
  padding: 30px 20px; background: #fafafa; border-radius: 12px;
  border: 1px dashed #e0e0e0;
}
.schedule-ai-section .ai-placeholder p { font-size: 14px; color: #999; margin: 0; text-align: center; }
.schedule-ai-section .ai-loading-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f5ff 100%);
  border-radius: 12px; padding: 20px 24px;
  border: 1px solid rgba(64,158,255,.15);
  box-shadow: 0 2px 12px rgba(64,158,255,.08);
}
.schedule-ai-section .ai-loading-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; color: #409eff; font-weight: 500; margin-bottom: 16px;
}
.schedule-ai-section .ai-loading-skeleton { display: flex; flex-direction: column; gap: 10px; }
.schedule-ai-section .skeleton-line {
  height: 14px; border-radius: 7px;
  background: linear-gradient(90deg, #e8edf3 25%, #d5dce6 50%, #e8edf3 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
.schedule-ai-section .ai-refresh-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; margin-bottom: 10px;
  background: rgba(64,158,255,.06); border-radius: 8px;
  font-size: 12px; color: #409eff;
}
.sg-header { display: flex; background: #f5f7fa; border-bottom: 1px solid #e8e8e8; }
.sg-corner { width: 76px; flex-shrink: 0; padding: 12px 4px; text-align: center; font-weight: 700; font-size: 13px; color: #666; }
.sg-day { flex: 1; padding: 12px 4px; text-align: center; font-weight: 700; font-size: 14px; color: #555; border-left: 1px solid #e8e8e8; letter-spacing: 2px; }
.sg-row { display: flex; border-bottom: 1px solid #f0f0f0; }
.sg-row:last-child { border-bottom: none; }
.sg-period {
  width: 76px; flex-shrink: 0; padding: 10px 4px; text-align: center;
  font-size: 12px; color: #888; background: #fafafa; display: flex;
  flex-direction: column; align-items: center; justify-content: center; line-height: 1.5; font-weight: 500;
}
.sg-cell { flex: 1; padding: 4px; border-left: 1px solid #f0f0f0; }
.sg-course {
  border-radius: 8px; padding: 6px 8px; margin-bottom: 3px;
  transition: transform .12s; cursor: default;
}
.sg-course:hover { transform: scale(1.04); }
.sgc-name { font-size: 13px; font-weight: 700; color: #1a1a2e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sgc-meta { font-size: 11px; color: #666; margin-top: 1px; }

/* 课程过渡动画 */
.sg-body { position: relative; }

/* 左滑（下一周） */
.slide-left-enter-active, .slide-left-leave-active {
  transition: all .18s cubic-bezier(.4,0,.2,1);
}
.slide-left-enter-from { opacity: 0; transform: translateX(30px); }
.slide-left-leave-to { opacity: 0; transform: translateX(-30px); }

/* 右滑（上一周） */
.slide-right-enter-active, .slide-right-leave-active {
  transition: all .18s cubic-bezier(.4,0,.2,1);
}
.slide-right-enter-from { opacity: 0; transform: translateX(-30px); }
.slide-right-leave-to { opacity: 0; transform: translateX(30px); }

/* ===== Today Section ===== */
.today-section { 
  margin-bottom: 28px;
  animation: fadeInUp 0.35s ease-out;
  animation-delay: 0.5s;
  animation-fill-mode: both;
}
.today-header {
  font-size: 16px; font-weight: 700; color: #1a1a2e;
  padding-bottom: 14px; margin-bottom: 14px; border-bottom: 2px solid #67c23a;
  display: flex; align-items: center; gap: 6px;
}
.today-list { display: flex; flex-direction: column; gap: 10px; }
.today-card {
  display: flex; gap: 16px; align-items: center;
  background: #fff; border-radius: 12px; padding: 14px 18px;
  border: 1px solid rgba(0,0,0,.04); border-left: 5px solid #67c23a;
  box-shadow: 0 2px 8px rgba(0,0,0,.03); 
  transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0;
  transform: translateX(-20px);
  animation: fadeInLeft 0.35s ease-out forwards;
}
.today-card:nth-child(1) { animation-delay: 0.03s; }
.today-card:nth-child(2) { animation-delay: 0.06s; }
.today-card:nth-child(3) { animation-delay: 0.09s; }
.today-card:nth-child(4) { animation-delay: 0.12s; }
.today-card:hover { 
  transform: translateY(-4px) translateX(4px); 
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.tc-time { 
  font-size: 14px; 
  font-weight: 700; 
  color: #409eff; 
  flex-shrink: 0; 
  min-width: 76px;
  transition: all 0.3s ease;
}
.today-card:hover .tc-time {
  color: #67c23a;
  transform: scale(1.05);
}
.tc-body { flex: 1; }
.tc-name { 
  font-size: 15px; 
  font-weight: 600; 
  color: #1a1a2e;
  transition: color 0.2s ease;
}
.today-card:hover .tc-name {
  color: #409eff;
}
.tc-meta { font-size: 13px; color: #888; margin-top: 3px; }
.no-today {
  text-align: center; padding: 20px; color: #999; font-size: 14px;
  background: #fafafa; border-radius: 12px; border: 1px dashed #e0e0e0;
}

/* ===== Course List ===== */
.course-list-section { 
  animation: fadeInUp 0.35s ease-out;
  animation-delay: 0.6s;
  animation-fill-mode: both;
}
.cl-header {
  font-size: 16px; font-weight: 700; color: #1a1a2e;
  padding-bottom: 14px; margin-bottom: 14px; border-bottom: 2px solid #409eff;
}
.course-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.cl-card {
  background: #fff; border-radius: 12px; padding: 16px 18px;
  border: 1px solid rgba(0,0,0,.04); border-left: 5px solid #409eff;
  box-shadow: 0 2px 8px rgba(0,0,0,.03); 
  transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.35s ease-out forwards;
}
.cl-card:nth-child(1) { animation-delay: 0.03s; }
.cl-card:nth-child(2) { animation-delay: 0.06s; }
.cl-card:nth-child(3) { animation-delay: 0.09s; }
.cl-card:nth-child(4) { animation-delay: 0.12s; }
.cl-card:nth-child(5) { animation-delay: 0.15s; }
.cl-card:hover { 
  transform: translateY(-4px); 
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.cl-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.cl-name { 
  font-size: 15px; 
  font-weight: 600; 
  color: #1a1a2e;
  transition: color 0.2s ease;
}
.cl-card:hover .cl-name {
  color: #409eff;
}
.cl-teacher { font-size: 13px; color: #888; }
.cl-meta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 13px; color: #999; }

/* ===== Trend Row ===== */
.trend-row { display: flex; gap: 16px; margin-bottom: 24px; }
.trend-section { flex: 2; }
.section-title {
  font-size: 16px; font-weight: 700; color: #1a1a2e;
  padding-bottom: 14px; margin-bottom: 14px; border-bottom: 2px solid #409eff;
  display: flex; align-items: center; gap: 6px;
}
.trend-chart { width: 100%; height: 280px; background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.03); }

/* ===== AI Analysis Section ===== */
.ai-analysis-section { flex: 1; min-width: 0; }
.ai-result-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f5ff 100%);
  border-radius: 12px; padding: 20px 24px;
  border: 1px solid rgba(64,158,255,.15);
  box-shadow: 0 2px 12px rgba(64,158,255,.08);
  max-height: 420px; overflow-y: auto;
  scrollbar-width: thin; -ms-overflow-style: auto;
}
.ai-result-card::-webkit-scrollbar { width: 4px; }
.ai-result-card::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
.ai-result-content {
  font-size: 14px; line-height: 1.8; color: #333;
  word-break: break-word;
}
.ai-result-content :deep(p.md-p) {
  margin: 6px 0;
}
.ai-result-content :deep(h1), .ai-result-content :deep(h2), .ai-result-content :deep(h3), .ai-result-content :deep(h4) {
  font-weight: 600; color: #1a1a2e;
  margin: 16px 0 8px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(64,158,255,.1);
}
.ai-result-content :deep(h1) { font-size: 20px; }
.ai-result-content :deep(h2) { font-size: 18px; }
.ai-result-content :deep(h3) { font-size: 16px; }
.ai-result-content :deep(h4) { font-size: 15px; }
.ai-result-content :deep(h1:first-child), .ai-result-content :deep(h2:first-child),
.ai-result-content :deep(h3:first-child), .ai-result-content :deep(h4:first-child) { margin-top: 0; }
.ai-result-content :deep(strong) { color: #409eff; font-weight: 600; }
.ai-result-content :deep(em) { font-style: italic; color: #555; }
.ai-result-content :deep(del) { text-decoration: line-through; color: #999; }
.ai-result-content :deep(ul.md-ul), .ai-result-content :deep(ol.md-ol) {
  margin: 8px 0; padding-left: 24px;
}
.ai-result-content :deep(li.md-li) {
  margin: 4px 0; color: #555; line-height: 1.7;
}
.ai-result-content :deep(a.md-link) {
  color: #409eff; text-decoration: none; border-bottom: 1px dashed rgba(64,158,255,.4);
}
.ai-result-content :deep(a.md-link:hover) { border-bottom-color: #409eff; }
.ai-result-content :deep(code.md-inline-code) {
  background: rgba(64,158,255,.08); color: #e6a23c;
  padding: 2px 6px; border-radius: 4px; font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.ai-result-content :deep(pre.md-code-block) {
  background: #1e1e2e; color: #cdd6f4;
  padding: 14px 18px; border-radius: 8px;
  overflow-x: auto; margin: 10px 0;
  font-size: 13px; line-height: 1.6;
}
.ai-result-content :deep(pre.md-code-block code) {
  background: none; color: inherit; padding: 0;
  font-family: 'Consolas', 'Monaco', monospace;
}
.ai-result-content :deep(blockquote.md-blockquote) {
  border-left: 4px solid #409eff; margin: 10px 0;
  padding: 8px 16px; background: rgba(64,158,255,.05);
  border-radius: 0 8px 8px 0; color: #555;
}
.ai-result-content :deep(hr.md-hr) {
  border: none; border-top: 1px solid #e8e8e8; margin: 16px 0;
}
.ai-result-content :deep(table.md-table) {
  width: 100%; border-collapse: collapse; margin: 10px 0;
  font-size: 13px;
}
.ai-result-content :deep(th.md-th), .ai-result-content :deep(td.md-td) {
  border: 1px solid #e8e8e8; padding: 8px 12px; text-align: left;
}
.ai-result-content :deep(th.md-th) {
  background: #f5f7fa; font-weight: 600; color: #1a1a2e;
}
.ai-result-content :deep(tr.md-tr:hover) { background: rgba(64,158,255,.03); }
.ai-result-content :deep(img.md-image) {
  max-width: 100%; border-radius: 8px; margin: 8px 0;
}
.ai-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
  padding: 40px 20px; background: #fafafa; border-radius: 12px;
  border: 1px dashed #e0e0e0; height: calc(100% - 60px);
}
.ai-placeholder p { font-size: 14px; color: #999; margin: 0; text-align: center; }
.ai-loading-card {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f5ff 100%);
  border-radius: 12px; padding: 20px 24px;
  border: 1px solid rgba(64,158,255,.15);
  box-shadow: 0 2px 12px rgba(64,158,255,.08);
}
.ai-loading-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; color: #409eff; font-weight: 500; margin-bottom: 16px;
}
.ai-loading-skeleton { display: flex; flex-direction: column; gap: 10px; }
.ai-loading-skeleton .skeleton-line {
  height: 14px; border-radius: 7px;
  background: linear-gradient(90deg, #e8edf3 25%, #d5dce6 50%, #e8edf3 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
.ai-refresh-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; margin-bottom: 10px;
  background: rgba(64,158,255,.06); border-radius: 8px;
  font-size: 12px; color: #409eff;
}

/* ===== Goal Section ===== */
.goal-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.section-title {
  font-size: 16px; font-weight: 700; color: #1a1a2e;
  padding-bottom: 14px; margin-bottom: 14px; border-bottom: 2px solid #409eff;
  display: flex; align-items: center; gap: 6px;
}
.goal-list { display: flex; flex-direction: column; gap: 10px; }
.goal-item {
  background: #fff; border-radius: 12px; padding: 16px 20px;
  border: 1px solid rgba(0,0,0,.04); box-shadow: 0 2px 8px rgba(0,0,0,.03);
  transition: transform .15s;
}
.goal-item:hover { transform: translateY(-1px); }
.goal-item.is-current { border-left: 4px solid #67c23a; }
.goal-item-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
}
.goal-sem-name { font-size: 14px; font-weight: 700; color: #1a1a2e; }
.goal-item-body { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.goal-item-left { display: flex; align-items: center; gap: 10px; }
.goal-item-right { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #666; }
.goal-label { font-size: 13px; font-weight: 600; color: #333; white-space: nowrap; }
.goal-input-wrap { display: flex; align-items: center; }
.goal-locked {
  display: flex; align-items: center; gap: 4px;
  font-size: 13px; color: #999;
}
.goal-achieve { display: flex; align-items: center; gap: 3px; font-size: 13px; }
.goal-item-bar { margin-top: 10px; }
.goal-bar-outer {
  height: 8px; background: #f0f2f5; border-radius: 4px; overflow: hidden;
}
.goal-bar-inner { height: 100%; border-radius: 4px; transition: width .6s ease; }

/* ===== Semester Selector ===== */
.sem-selector {
  display: flex; align-items: center; gap: 16px; margin-bottom: 16px;
}
.sem-stats-inline { display: flex; gap: 14px; font-size: 13px; color: #999; }
.sem-stats-inline b { color: #1a1a2e; font-weight: 600; }

/* ===== Grade Grid ===== */
.grade-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; margin-bottom: 20px; }
.grade-card {
  background: #fff; border-radius: 10px; padding: 14px 16px;
  border: 1px solid rgba(0,0,0,.04); box-shadow: 0 1px 6px rgba(0,0,0,.02);
  transition: transform .15s;
  border-left: 4px solid #ddd;
}
.grade-card:hover { transform: translateY(-2px); }
.grade-card.level-a { border-left-color: #67c23a; }
.grade-card.level-b { border-left-color: #409eff; }
.grade-card.level-c { border-left-color: #e6a23c; }
.grade-card.level-d { border-left-color: #f56c6c; }
.grade-card.level-f { border-left-color: #c03636; }
.gc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.gc-name { font-size: 14px; font-weight: 600; color: #1a1a2e; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gc-score { font-size: 22px; font-weight: 700; flex-shrink: 0; margin-left: 8px; }
.level-a .gc-score { color: #67c23a; }
.level-b .gc-score { color: #409eff; }
.level-c .gc-score { color: #e6a23c; }
.level-d .gc-score { color: #f56c6c; }
.level-f .gc-score { color: #c03636; }
.gc-meta { display: flex; gap: 12px; font-size: 12px; color: #999; }

/* ===== Grade Stats Row ===== */
.grade-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.grade-stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.grade-stat-card .stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.grade-stat-card .stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
}
.grade-stat-card .stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

/* ===== Grade Charts Row ===== */
.grade-charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.grade-chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.grade-chart-card .chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}
.grade-chart {
  width: 100%;
  height: 220px;
}

/* ===== Grade Courses Row ===== */
.grade-dual-row {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 16px;
  margin-bottom: 20px;
}
.grade-course-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.weak-courses-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
}
.mini-course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.mini-course-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  background: #f8f9fa;
}
.mini-course-item.good {
  border-left: 3px solid #67c23a;
}
.mini-course-item.weak {
  border-left: 3px solid #f56c6c;
}
.mc-name {
  font-size: 13px;
  color: #333;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mc-gpa {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin-left: 12px;
}

/* ===== Exam Section ===== */
.exam-section { margin-top: 24px; }
.exam-card {
  display: flex; gap: 16px; background: #fff; border-radius: 12px; padding: 14px 18px;
  border: 1px solid rgba(0,0,0,.04); box-shadow: 0 2px 8px rgba(0,0,0,.03);
  transition: transform .15s; margin-bottom: 8px;
}
.exam-card:hover { transform: translateY(-1px); }
.ec-left { text-align: center; flex-shrink: 0; width: 80px; padding: 4px 0; }
.ec-date { font-size: 20px; font-weight: 700; color: #409eff; }
.ec-time { font-size: 12px; color: #999; margin-top: 2px; }
.ec-body { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 4px; }
.ec-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.ec-location { font-size: 13px; color: #888; display: flex; align-items: center; gap: 4px; }

/* ===== Growth View ===== */
.growth-view { display: flex; flex-direction: column; }
.score-header {
  display: flex; align-items: center; gap: 36px;
  padding: 20px 28px; margin-bottom: 20px;
  background: var(--gradient-card);
  border-radius: 16px; border: 1px solid var(--border-color);
  animation: fadeInUp 0.35s ease-out;
}
.score-ring { 
  position: relative; 
  width: 110px; 
  height: 110px; 
  flex-shrink: 0;
  animation: scaleIn 0.8s ease-out;
}
.score-svg { 
  width: 110px; 
  height: 110px;
  display: block;
}
.score-center {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.score-value {
  font-size: 28px; font-weight: 700;
  color: var(--accent-blue);
  animation: pulse 2s ease-in-out infinite;
  line-height: 1;
}
.score-label {
  font-size: 11px; color: var(--text-muted); margin-top: 4px;
}
.score-stats { display: flex; gap: 28px; flex: 1; flex-wrap: wrap; }
.stat-item { 
  display: flex; flex-direction: column; align-items: center; min-width: 56px;
  opacity: 0; transform: translateY(20px);
  animation: fadeInUp 0.3s ease-out forwards;
}
.stat-item:nth-child(1) { animation-delay: 0.05s; }
.stat-item:nth-child(2) { animation-delay: 0.1s; }
.stat-item:nth-child(3) { animation-delay: 0.15s; }
.stat-item:nth-child(4) { animation-delay: 0.2s; }
.stat-item:nth-child(5) { animation-delay: 0.25s; }
.stat-item:nth-child(6) { animation-delay: 0.3s; }
.stat-item:nth-child(7) { animation-delay: 0.35s; }
.stat-num {
  font-size: 26px; font-weight: 700; color: var(--text-primary);
  transition: all 0.15s ease;
}
.stat-item:hover .stat-num {
  transform: scale(1.1); color: var(--accent-blue);
}
.stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* ===== Growth Charts ===== */
.charts-row { display: flex; gap: 16px; margin-bottom: 16px; }
.chart-card {
  flex: 1; background: var(--bg-card); border-radius: 14px; padding: 18px 20px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-md);
  opacity: 0; transform: translateY(20px);
  animation: fadeInUp 0.35s ease-out forwards;
}
.chart-card:nth-child(1) { animation-delay: 0.1s; }
.chart-card:nth-child(2) { animation-delay: 0.15s; }
.chart-card.wide { flex: 1; }
.chart-card-header {
  font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px;
  display: flex; align-items: center;
}
.chart { 
  width: 100%; height: 250px;
  animation: scaleIn 0.8s ease-out;
  animation-delay: 0.4s;
  animation-fill-mode: both;
}
.chart-card.wide .chart { height: 200px; }

/* ===== Growth Split Row (Skills + Interests) ===== */
.split-row { display: flex; gap: 16px; margin-bottom: 20px; }
.tag-card {
  flex: 1; background: var(--bg-card); border-radius: 14px; padding: 18px 20px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-md);
  opacity: 0; transform: translateX(-20px);
  animation: fadeInLeft 0.35s ease-out forwards;
}
.tag-card:nth-child(1) { animation-delay: 0.15s; }
.tag-card:nth-child(2) { 
  animation-name: fadeInRight;
  animation-delay: 0.2s;
}
.tag-card-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px; font-size: 14px; font-weight: 600; color: var(--text-primary);
}
.preset-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.preset-tag { 
  cursor: pointer; font-size: 12px;
  transition: all 0.2s ease;
}
.preset-tag:hover { transform: scale(1.05); }
.preset-tag:active { transform: scale(0.95); }
.tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.skill-tag { 
  font-size: 12px; padding: 3px 12px; border-radius: 16px;
  transition: all 0.2s ease;
}
.skill-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.tag-input-row { display: flex; gap: 8px; }

/* ===== Growth Section Headers ===== */
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; font-size: 15px; font-weight: 600; color: var(--text-primary);
}
.section-header.clickable {
  cursor: pointer;
  padding: 10px 16px;
  border-radius: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
  margin-bottom: 12px;
}
.section-header.clickable:hover {
  background: var(--hover-bg, #f5f7fa);
  border-color: var(--accent-blue, #409eff);
}
.header-left {
  display: flex; align-items: center; gap: 2px;
}
.collapse-icon {
  transition: transform 0.15s ease;
  font-size: 14px; margin-right: 4px;
}
.collapse-icon.collapsed { transform: rotate(0deg); }
.collapse-icon:not(.collapsed) { transform: rotate(90deg); }

/* Collapse transition */
.collapse-enter-active, .collapse-leave-active {
  transition: all 0.2s ease; overflow: hidden;
}
.collapse-enter-from, .collapse-leave-to {
  opacity: 0; max-height: 0; transform: translateY(-8px);
}
.collapse-enter-to, .collapse-leave-from {
  opacity: 1; max-height: 2000px; transform: translateY(0);
}

/* ===== Growth Records (Timeline Style) ===== */
.records-section { margin-bottom: 24px; }
.records-list { display: flex; flex-direction: column; gap: 0; position: relative; }
.record-card {
  display: flex; gap: 16px; padding: 14px 18px;
  background: var(--bg-card); border-radius: 12px; margin-bottom: 8px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-sm);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0; transform: translateY(20px);
  animation: fadeInUp 0.35s ease-out forwards;
}
.record-card:nth-child(1) { animation-delay: 0.05s; }
.record-card:nth-child(2) { animation-delay: 0.1s; }
.record-card:nth-child(3) { animation-delay: 0.15s; }
.record-card:nth-child(4) { animation-delay: 0.2s; }
.record-card:nth-child(5) { animation-delay: 0.25s; }
.record-card:hover { 
  transform: translateY(-4px); 
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.record-left {
  display: flex; flex-direction: column; align-items: center;
  width: 12px; flex-shrink: 0; padding-top: 6px;
}
.record-dot { 
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
  transition: all 0.15s ease;
}
.record-card:hover .record-dot {
  transform: scale(1.3);
  box-shadow: 0 0 8px rgba(0,0,0,0.2);
}
.record-body { flex: 1; min-width: 0; }
.record-top { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.record-date { font-size: 11px; color: var(--text-placeholder); }
.record-title {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 2px; transition: color 0.2s ease;
}
.record-card:hover .record-title { color: var(--accent-blue); }
.record-meta { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 4px; }
.record-details { display: flex; gap: 8px; flex-wrap: wrap; }
.detail-item {
  font-size: 12px; color: var(--text-muted); transition: color 0.2s ease;
}
.record-card:hover .detail-item { color: var(--text-secondary); }

/* ===== Growth Projects ===== */
.projects-section { margin-bottom: 24px; }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.project-card {
  background: var(--bg-card); border-radius: 14px; padding: 18px 20px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-md);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0; transform: scale(0.9);
  animation: scaleIn 0.3s ease-out forwards;
}
.project-card:nth-child(1) { animation-delay: 0.05s; }
.project-card:nth-child(2) { animation-delay: 0.1s; }
.project-card:nth-child(3) { animation-delay: 0.15s; }
.project-card:nth-child(4) { animation-delay: 0.2s; }
.project-card:hover { 
  transform: translateY(-6px) scale(1.02); 
  box-shadow: 0 12px 32px rgba(0,0,0,0.15);
}
.project-top { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.project-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: all 0.15s ease;
}
.project-card:hover .project-icon {
  transform: rotate(10deg) scale(1.1);
}
.project-icon.team { background: rgba(64,158,255,.1); color: var(--accent-blue); }
.project-icon.solo { background: rgba(103,194,58,.1); color: var(--accent-green); }
.project-info { flex: 1; min-width: 0; }
.project-name {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  transition: color 0.2s ease;
}
.project-card:hover .project-name { color: var(--accent-blue); }
.project-date { font-size: 11px; color: var(--text-placeholder); margin-top: 2px; }
.project-members { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
.project-attach { margin-bottom: 8px; }
.project-actions { 
  display: flex; gap: 4px; margin-top: 6px; padding-top: 8px; 
  border-top: 1px solid var(--border-light);
  opacity: 0; transform: translateY(10px);
  transition: all 0.15s ease;
}
.project-card:hover .project-actions {
  opacity: 1; transform: translateY(0);
}

/* ===== Dialog overrides ===== */
:deep(.el-dialog__body) { padding: 20px 24px; }

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .schedule-page { padding: 8px 12px 0; }
  .schedule-toolbar { flex-direction: column; align-items: flex-start; }
  .week-info .el-button.is-circle { width: 32px; height: 32px; padding: 0; }
  .schedule-main-row { flex-direction: column; }
  .schedule-grid { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .sg-corner { width: 56px; font-size: 11px; }
  .sg-period { width: 56px; font-size: 10px; padding: 6px 2px; }
  .sg-day { font-size: 12px; padding: 8px 2px; }
  .sgc-name { font-size: 11px; }
  .sgc-meta { font-size: 9px; }
  .grade-stats-row { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .grade-stat-card { padding: 12px; }
  .grade-stat-card .stat-value { font-size: 16px; }
  .grade-charts-row { grid-template-columns: 1fr; }
  .grade-chart { height: 180px; }
  .grade-dual-row { grid-template-columns: 1fr; }
  .trend-row { flex-direction: column; }
  .trend-chart { height: 220px; }
  .grade-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .grade-card { padding: 10px 12px; }
  .gc-score { font-size: 18px; }
  .course-list { grid-template-columns: 1fr; }
  .sem-selector { flex-direction: column; align-items: flex-start; gap: 8px; }
  .sem-stats-inline { flex-wrap: wrap; gap: 8px; }
  .goal-item-body { flex-direction: column; align-items: flex-start; }
  .goal-input-wrap { flex-wrap: wrap; }
  /* Overview Cards */
  .overview-cards { flex-wrap: wrap; }
  .overview-card { min-width: calc(50% - 5px); flex: unset; }
  /* Growth View */
  .score-header { flex-direction: column; align-items: center; gap: 16px; padding: 16px; }
  .score-stats { gap: 16px; justify-content: center; }
  .stat-num { font-size: 20px; }
  .charts-row { flex-direction: column; }
  .chart { height: 200px; }
  .chart-card.wide .chart { height: 180px; }
  .split-row { flex-direction: column; }
  .project-grid { grid-template-columns: 1fr; }
  .record-card { padding: 12px; }
  .record-title { font-size: 13px; }
  /* Mobile entry animations - 更快更轻量 */
  .animate-fade-in-up { animation: fadeInUp 0.2s ease-out; }
  .animate-fade-in-left { animation: fadeInLeft 0.2s ease-out; }
  .animate-fade-in-right { animation: fadeInRight 0.2s ease-out; }
  .animate-scale-in { animation: scaleIn 0.18s ease-out; }
  .animate-slide-in-down { animation: slideInDown 0.18s ease-out; }
  .delay-100 { animation-delay: 0.02s; }
  .delay-200 { animation-delay: 0.04s; }
  .delay-300 { animation-delay: 0.06s; }
  .delay-400 { animation-delay: 0.08s; }
  .delay-500 { animation-delay: 0.1s; }
}
</style>
