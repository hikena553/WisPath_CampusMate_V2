<template>
  <div class="students-page">
    <!-- ============ 桌面端（保持原样） ============ -->
    <template v-if="!isMobile">
      <div class="page-header">
        <div class="header-left">
          <h2>学生成长档案</h2>
          <p class="page-sub">共 <strong>{{ filteredStudents.length }}</strong> 名学生</p>
        </div>
        <div class="header-actions">
          <el-input v-model="search" placeholder="搜索姓名/学号/学院" style="width:220px" clearable @input="debouncedLoadStudents">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>

      <div class="filter-bar">
        <el-select v-model="filterCrisis" placeholder="危机等级" clearable style="width:130px">
          <el-option label="全部" value="" />
          <el-option label="高危" value="severe" />
          <el-option label="中度" value="moderate" />
          <el-option label="轻度" value="mild" />
          <el-option label="无预警" value="none" />
        </el-select>
        <el-select v-model="filterGrowth" placeholder="成长成果" clearable style="width:130px">
          <el-option label="全部" value="" />
          <el-option label="有成果" value="has" />
          <el-option label="无成果" value="none" />
        </el-select>
        <el-select v-model="filterScore" placeholder="综合评分" clearable style="width:130px">
          <el-option label="全部" value="" />
          <el-option label="优秀 (≥90)" value="excellent" />
          <el-option label="良好 (≥75)" value="good" />
          <el-option label="及格 (≥60)" value="average" />
          <el-option label="不及格 (<60)" value="poor" />
        </el-select>
        <el-select v-model="filterSkill" placeholder="技能画像" clearable style="width:130px">
          <el-option label="全部" value="" />
          <el-option label="有技能" value="has" />
          <el-option label="无技能" value="none" />
        </el-select>
        <el-button v-if="hasActiveFilter" type="info" text @click="clearFilters">
          <el-icon><Close /></el-icon> 清除筛选
        </el-button>
      </div>

      <div v-if="!filteredStudents.length && loaded" class="empty-wrapper">
        <el-empty description="暂无学生记录" :image-size="100">
          <template #image>
            <el-icon :size="64" color="#ddd"><User /></el-icon>
          </template>
          <p style="color:#999;margin-top:8px">{{ hasActiveFilter ? '没有符合条件的学生' : '当前名下暂无学生' }}</p>
        </el-empty>
      </div>

      <div v-else class="student-grid">
        <div v-for="s in pagedStudents" :key="s.id" :class="['student-card', s.crisis_level ? `level-${s.crisis_level}` : '']">
          <div class="card-head">
            <el-avatar :size="48" :src="s.avatar || undefined" class="card-avatar">{{ s.name[0] }}</el-avatar>
            <div class="card-info">
              <strong class="card-name">{{ s.name }}</strong>
              <span class="card-college">{{ s.college || '未分配' }}</span>
            </div>
            <el-tag v-if="s.crisis_level" :type="crisisType(s.crisis_level)" size="small" effect="dark" class="crisis-tag">
              {{ crisisLabel(s.crisis_level) }}
            </el-tag>
          </div>

          <div class="card-stats">
            <div class="stat-item">
              <span class="stat-num">{{ s.growth_count }}</span>
              <span class="stat-text">成果</span>
            </div>
            <div class="stat-item">
              <span class="stat-num">{{ s.leave_count }}</span>
              <span class="stat-text">请假</span>
            </div>
            <div class="stat-item" v-if="s.score !== undefined">
              <span :class="['stat-num', scoreClass(s.score)]">{{ s.score }}</span>
              <span class="stat-text">综合分</span>
            </div>
          </div>

          <div v-if="s.skills_json?.skills?.length" class="card-skills">
            <el-tag v-for="sk in s.skills_json.skills.slice(0, 3)" :key="sk.name" size="small" round effect="plain">{{ sk.name }}</el-tag>
          </div>

          <div class="card-actions">
            <el-button size="small" type="primary" @click="openDetail(s)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-button size="small" type="success" plain @click="openContact(s)">
              <el-icon><ChatDotRound /></el-icon> 联系
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="filteredStudents.length > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[12, 24, 36, 48]"
          :total="filteredStudents.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- 桌面端详情弹窗 -->
      <el-dialog v-model="detailVisible" :title="detail ? `${detail.name} - 学生详情` : '学生详情'" width="800px" :close-on-click-modal="false" destroy-on-close class="student-detail-dialog">
        <template v-if="detail">
          <div class="dialog-body">
            <div class="dialog-profile">
              <el-avatar :size="56" :src="detail.avatar || undefined">{{ detail.name[0] }}</el-avatar>
              <div class="dialog-profile-info">
                <strong>{{ detail.name }}</strong>
                <small>{{ detail.college || '未分配' }}</small>
                <small>学号: {{ detail.username }}</small>
              </div>
            </div>
            <div class="dialog-tabs-wrapper">
              <el-tabs v-model="detailTab" class="detail-tabs">
                <el-tab-pane label="技能画像" name="skills">
                  <div class="tab-content">
                    <div v-if="detail.skills_json?.skills?.length">
                      <h4>技能</h4>
                      <div class="skill-list">
                        <div v-for="sk in detail.skills_json.skills" :key="sk.name" class="skill-item">
                          <el-tag>{{ sk.name }}</el-tag>
                          <small>{{ sk.context }}</small>
                        </div>
                      </div>
                    </div>
                    <div v-if="detail.skills_json?.interests?.length">
                      <h4>兴趣</h4>
                      <div>
                        <el-tag v-for="i in detail.skills_json.interests" :key="i" round style="margin:4px">{{ i }}</el-tag>
                      </div>
                    </div>
                    <el-empty v-if="!detail.skills_json?.skills?.length && !detail.skills_json?.interests?.length" description="暂无技能画像数据" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="成长记录" name="growth">
                  <div class="tab-content">
                    <el-timeline>
                      <el-timeline-item v-for="r in detail.growth_records" :key="r.id" :timestamp="r.date">
                        <el-tag size="small" :type="growthType(r.type)">{{ growthLabel(r.type) }}</el-tag>
                        <p style="margin:4px 0"><strong>{{ r.title }}</strong></p>
                        <p v-if="r.description" style="color:#666;font-size:13px">{{ r.description }}</p>
                        <el-link v-if="r.attachment_url" type="primary" :href="r.attachment_url" target="_blank" style="margin-top:4px;font-size:13px">查看附件</el-link>
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-if="!detail.growth_records.length" description="暂无成长记录" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="危机预警" name="crisis">
                  <div class="tab-content">
                    <el-timeline>
                      <el-timeline-item v-for="a in detail.crisis_alerts" :key="a.id" :timestamp="formatTime(a.created_at)">
                        <el-alert
                          :title="crisisLabel(a.level)"
                          :type="crisisType(a.level)"
                          :description="a.summary"
                          :closable="false"
                          show-icon
                        />
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-if="!detail.crisis_alerts.length" description="暂无预警记录" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="项目展示" name="projects">
                  <div class="tab-content">
                    <el-timeline>
                      <el-timeline-item v-for="p in detail.projects" :key="p.id" :timestamp="`${p.start_date} ~ ${p.end_date || '至今'}`">
                        <p style="margin:4px 0"><strong>{{ p.project_name }}</strong></p>
                        <el-tag v-if="p.is_team" size="small" type="primary" round>团队</el-tag>
                        <el-tag v-else size="small" type="info" round>个人</el-tag>
                        <p v-if="p.is_team && p.team_members" style="color:#666;font-size:13px;margin-top:4px">成员：{{ p.team_members }}</p>
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-if="!detail.projects.length" description="暂无项目数据" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="请假记录" name="leave">
                  <div class="tab-content">
                    <el-table :data="detail.leave_requests" size="small" style="width:100%"
                      :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
                      <el-table-column prop="start_date" label="日期" width="100" />
                      <el-table-column prop="leave_type" label="类型" width="70">
                        <template #default="{ row }">{{ leaveTypeLabel(row.leave_type) }}</template>
                      </el-table-column>
                      <el-table-column prop="reason" label="原因" min-width="140" />
                      <el-table-column prop="status" label="状态" width="80">
                        <template #default="{ row }">
                          <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
                            {{ row.status === 'approved' ? '通过' : row.status === 'rejected' ? '拒绝' : '待批' }}
                          </el-tag>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-empty v-if="!detail.leave_requests.length" description="无请假记录" />
                  </div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </div>
        </template>
        <template #footer>
          <el-button @click="detailVisible = false">关闭</el-button>
        </template>
      </el-dialog>
    </template>

    <!-- ============ 移动端（全新设计） ============ -->
    <template v-else>
      <!-- 顶部导航：蓝底 + 搜索框 -->
      <div class="ms-header">
        <div class="ms-statusbar-space"></div>
        <div class="ms-header-top">
          <div class="ms-header-greet">
            <div class="ms-greet-line1">{{ greeting }}，{{ teacherName }}老师</div>
            <div class="ms-greet-line2">博学 · 笃行 · 严谨 · 创新</div>
          </div>
          <img src="/images/mascot.png" alt="绵小城" class="ms-mascot" />
        </div>
        <div class="ms-search">
          <el-input
            v-model="search"
            placeholder="搜索姓名 / 学号 / 学院"
            clearable
            class="ms-search-input"
            @input="debouncedLoadStudents"
          >
            <template #prefix><el-icon :size="16"><Search /></el-icon></template>
          </el-input>
        </div>
      </div>

      <!-- 数据统计卡片 -->
      <div class="ms-card ms-stats-card">
        <div class="ms-stats">
          <div class="ms-stat-item" @click="openSubPage('students')">
            <div class="ms-stat-num" style="color:#1677ff">{{ stats.total_students }}</div>
            <div class="ms-stat-label">总学生</div>
          </div>
          <div class="ms-stat-divider"></div>
          <div class="ms-stat-item" @click="openSubPage('lease')">
            <div class="ms-stat-num" style="color:#ff9500">{{ stats.pending_leave_count }}</div>
            <div class="ms-stat-label">请假待批</div>
          </div>
          <div class="ms-stat-divider"></div>
          <div class="ms-stat-item" @click="openStudentsCrisis()">
            <div class="ms-stat-num" style="color:#ff3b30">{{ stats.severe_alert_count }}</div>
            <div class="ms-stat-label">高危学生</div>
          </div>
        </div>
      </div>

      <!-- 功能宫格：圆形彩色图标入口 -->
      <div class="ms-card ms-modules">
        <div class="ms-module-grid">
          <div class="ms-module-cell" @click="openSubPage('students')">
            <div class="ms-module-icon" style="background:#4d9fff"><el-icon :size="20"><User /></el-icon></div>
            <span class="ms-module-name">学员</span>
          </div>
          <div class="ms-module-cell" @click="openSubPage('analysis')">
            <div class="ms-module-icon" style="background:#8f7bff"><el-icon :size="20"><DataAnalysis /></el-icon></div>
            <span class="ms-module-name">学生分析</span>
          </div>
          <div class="ms-module-cell" @click="openSubPage('lease')">
            <div class="ms-module-icon" style="background:#ffb02e"><el-icon :size="20"><Calendar /></el-icon></div>
            <span class="ms-module-name">请假情况</span>
          </div>
          <div class="ms-module-cell" @click="openSubPage('announcement')">
            <div class="ms-module-icon" style="background:#2ed3a1"><el-icon :size="20"><Bell /></el-icon></div>
            <span class="ms-module-name">班级公告</span>
          </div>
          <div class="ms-module-cell" @click="openSubPage('more')">
            <div class="ms-module-icon" style="background:#a8b2c5"><el-icon :size="20"><MoreFilled /></el-icon></div>
            <span class="ms-module-name">更多</span>
          </div>
        </div>
      </div>

      <!-- 最近互动学员 / 搜索结果 -->
      <div class="ms-section-title">
        <span class="ms-section-title-text">{{ isSearching ? '搜索结果' : '最近互动学员' }}</span>
        <span v-if="isSearching" class="ms-section-title-extra">共 {{ students.length }} 人</span>
        <span v-else class="ms-section-title-extra" @click="openSubPage('students')">
          查看全部<el-icon :size="12"><ArrowRight /></el-icon>
        </span>
      </div>

      <!-- 搜索态：在当前页展示搜索结果 -->
      <template v-if="isSearching">
        <div v-if="students.length" class="ms-card ms-student-list">
          <div v-for="(s, i) in students" :key="s.id" class="ms-student-card" :class="{ 'no-border': i === students.length - 1 }" @click="openDetail(s)">
            <el-avatar :size="40" :src="s.avatar || undefined" class="ms-student-avatar">{{ s.name[0] }}</el-avatar>
            <div class="ms-student-info">
              <div class="ms-student-name">
                {{ s.name }}
                <el-tag v-if="s.crisis_level" :type="crisisType(s.crisis_level)" size="small" effect="dark" class="ms-student-tag">
                  {{ crisisLabel(s.crisis_level) }}
                </el-tag>
              </div>
              <div class="ms-student-sub">{{ s.college || '未分配' }} · 综合 {{ s.score ?? '--' }}</div>
            </div>
            <el-icon class="ms-student-arrow" color="#c8c9cc"><ArrowRight /></el-icon>
          </div>
        </div>
        <div v-else-if="loaded" class="ms-empty">未找到相关学生</div>
      </template>

      <!-- 非搜索态：最近互动学员 -->
      <template v-else>
        <div v-if="recentStudents.length" class="ms-card ms-student-list">
          <div v-for="(s, i) in recentStudents" :key="s.id" class="ms-student-card" :class="{ 'no-border': i === recentStudents.length - 1 }" @click="openDetail(s)">
            <el-avatar :size="40" :src="s.avatar || undefined" class="ms-student-avatar">{{ s.name[0] }}</el-avatar>
            <div class="ms-student-info">
              <div class="ms-student-name">
                {{ s.name }}
                <el-tag v-if="s.crisis_level" :type="crisisType(s.crisis_level)" size="small" effect="dark" class="ms-student-tag">
                  {{ crisisLabel(s.crisis_level) }}
                </el-tag>
              </div>
              <div class="ms-student-sub">{{ s.college || '未分配' }} · 综合 {{ s.score ?? '--' }}</div>
            </div>
            <el-icon class="ms-student-arrow" color="#c8c9cc"><ArrowRight /></el-icon>
          </div>
        </div>
        <div v-else-if="loaded" class="ms-empty">暂无可展示的学员</div>
      </template>
    </template>

    <!-- ============ 移动端右滑子页面 ============ -->
    <transition name="slide-right-in">
      <div v-if="isMobile && activeSubPage" class="ms-sub-page">
        <div class="ms-sub-header">
          <el-button text circle @click="activeSubPage = null"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="ms-sub-title">{{ subPageTitle }}</span>
          <div style="width:36px"></div>
        </div>
        <div class="ms-sub-body">
          <!-- 学员列表 -->
          <template v-if="activeSubPage === 'students'">
            <div class="ms-search-row">
              <div class="ms-search-input-wrap">
                <el-input v-model="search" placeholder="搜索姓名 / 学号 / 学院" clearable @input="debouncedLoadStudents">
                  <template #prefix><el-icon><Search /></el-icon></template>
                </el-input>
              </div>
              <span class="ms-filter-btn" @click="showFilterSheet = true">
                <el-icon :size="16"><Filter /></el-icon>
                <span>筛选</span>
              </span>
            </div>

            <div class="ms-chip-scroll">
              <button
                v-for="c in crisisChips"
                :key="c.value"
                class="ms-chip"
                :class="{ active: filterCrisis === c.value }"
                @click="filterCrisis = c.value"
              >{{ c.label }}</button>
            </div>

            <div v-if="!filteredStudents.length && loaded" class="ms-empty">{{ hasActiveFilter ? '没有符合条件的学生' : '当前名下暂无学生' }}</div>
            <div v-else class="ms-card ms-student-list">
              <div v-for="(s, i) in filteredStudents" :key="s.id" class="ms-student-card" :class="{ 'no-border': i === filteredStudents.length - 1 }" @click="openDetail(s)">
                <el-avatar :size="40" :src="s.avatar || undefined" class="ms-student-avatar">{{ s.name[0] }}</el-avatar>
                <div class="ms-student-info">
                  <div class="ms-student-name">
                    {{ s.name }}
                    <el-tag v-if="s.crisis_level" :type="crisisType(s.crisis_level)" size="small" effect="dark" class="ms-student-tag">
                      {{ crisisLabel(s.crisis_level) }}
                    </el-tag>
                  </div>
                  <div class="ms-student-sub">{{ s.college || '未分配' }} · 成果{{ s.growth_count }} · 请假{{ s.leave_count }}</div>
                </div>
                <el-icon class="ms-student-arrow" color="#c8c9cc"><ArrowRight /></el-icon>
              </div>
            </div>
          </template>

          <!-- 学生分析 -->
          <template v-else-if="activeSubPage === 'analysis'">
            <div class="ms-analysis-grid">
              <div class="ms-chart-card">
                <div class="ms-chart-card-header">
                  <el-icon color="#5b8def"><DataAnalysis /></el-icon>
                  <span>班级成长分析</span>
                </div>
                <div class="ms-chart-container">
                  <VChart v-if="evaluationRadarOptions" :option="evaluationRadarOptions" autoresize />
                  <el-empty v-else description="暂无数据" :image-size="48" />
                </div>
              </div>

              <div class="ms-chart-card">
                <div class="ms-chart-card-header">
                  <el-icon color="#f56c6c"><WarningFilled /></el-icon>
                  <span>心理危机分布</span>
                </div>
                <div class="ms-chart-container">
                  <VChart v-if="crisisPieOptions" :option="crisisPieOptions" autoresize />
                  <el-empty v-else description="暂无数据" :image-size="48" />
                </div>
              </div>

              <div class="ms-chart-card">
                <div class="ms-chart-card-header">
                  <el-icon color="#f56c6c"><Histogram /></el-icon>
                  <span>预警趋势</span>
                </div>
                <div class="ms-chart-container">
                  <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
                  <el-empty v-else description="暂无数据" :image-size="48" />
                </div>
              </div>
            </div>

            <!-- AI 智能分析 -->
            <div class="ms-ai-card">
              <div class="ms-ai-header">
                <img src="/images/mascot.png" alt="绵小城" class="ms-ai-mascot" />
                <div class="ms-ai-title">绵小城 · AI 智能分析</div>
              </div>
              <div v-if="!analysisResult && !analysisLoading" class="ms-ai-placeholder">
                <p>点击下方按钮，AI 将结合班级图表与每位学生的成长、心理数据，为你生成深度分析报告。</p>
                <el-button type="primary" size="small" @click="handleClassAnalysis" :loading="analysisLoading">开始分析</el-button>
              </div>
              <div v-else-if="analysisLoading" class="ms-ai-loading">
                <el-icon class="is-loading" :size="20"><Loading /></el-icon>
                <span>绵小城正在深度分析班级情况...</span>
              </div>
              <div v-else class="ms-ai-result">
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div class="ms-ai-text" v-html="renderedAnalysisHtml"></div>
                <el-button text type="primary" size="small" @click="handleClassAnalysis">重新分析</el-button>
              </div>
            </div>
          </template>

          <!-- 请假情况 -->
          <template v-else-if="activeSubPage === 'lease'">
            <el-tabs v-model="leaveTab" @tab-change="loadLeaveData">
              <el-tab-pane label="待审批" name="pending">
                <div v-if="pendingLeaves.length === 0" class="ms-empty">暂无待批请假</div>
                <div v-for="row in pendingLeaves" :key="row.id" class="ms-lease-card">
                  <div class="ms-lease-head">
                    <span class="ms-lease-name">{{ row.student_name }}</span>
                    <el-tag size="small" effect="plain">{{ leaveTypeLabel(row.leave_type) }}</el-tag>
                  </div>
                  <div class="ms-lease-date">{{ row.start_date }} ~ {{ row.end_date }}</div>
                  <div v-if="row.reason" class="ms-lease-reason">{{ row.reason }}</div>
                  <div class="ms-lease-actions">
                    <el-button type="success" size="small" @click="handleApprove(row)"><el-icon><Check /></el-icon> 通过</el-button>
                    <el-button type="danger" size="small" plain @click="showReject(row)"><el-icon><Close /></el-icon> 拒绝</el-button>
                  </div>
                </div>
              </el-tab-pane>
              <el-tab-pane label="已通过" name="approved">
                <div v-if="approvedLeaves.length === 0" class="ms-empty">暂无已通过请假</div>
                <div v-for="row in approvedLeaves" :key="row.id" class="ms-lease-card">
                  <div class="ms-lease-head">
                    <span class="ms-lease-name">{{ row.student_name }}</span>
                    <el-tag size="small" effect="plain">{{ leaveTypeLabel(row.leave_type) }}</el-tag>
                  </div>
                  <div class="ms-lease-date">{{ row.start_date }} ~ {{ row.end_date }}</div>
                  <div style="margin-top:6px"><el-tag type="success" size="small" effect="dark">已通过</el-tag></div>
                </div>
              </el-tab-pane>
              <el-tab-pane label="已拒绝" name="rejected">
                <div v-if="rejectedLeaves.length === 0" class="ms-empty">暂无已拒绝请假</div>
                <div v-for="row in rejectedLeaves" :key="row.id" class="ms-lease-card">
                  <div class="ms-lease-head">
                    <span class="ms-lease-name">{{ row.student_name }}</span>
                    <el-tag size="small" effect="plain">{{ leaveTypeLabel(row.leave_type) }}</el-tag>
                  </div>
                  <div class="ms-lease-date">{{ row.start_date }} ~ {{ row.end_date }}</div>
                  <div v-if="row.reject_reason" class="ms-lease-reason">拒绝理由：{{ row.reject_reason }}</div>
                  <div style="margin-top:6px"><el-tag type="danger" size="small" effect="dark">已拒绝</el-tag></div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </template>

          <!-- 班级公告 -->
          <template v-else-if="activeSubPage === 'announcement'">
            <button type="button" class="ms-announce-publish" @click="openCreateDialog">
              <el-icon :size="16"><Plus /></el-icon>
              <span>发布班级公告</span>
            </button>

            <div v-if="myAnnouncements.length === 0" class="ms-announce-empty">
              <div class="ms-announce-empty-icon"><el-icon :size="28"><Bell /></el-icon></div>
              <p>暂无班级公告</p>
              <span>点击上方按钮，向你的学生发布第一条公告</span>
            </div>

            <div v-else class="ms-announce-list">
              <div v-for="a in myAnnouncements" :key="a.id" class="ms-announce-card" :class="'announce-' + a.urgency">
                <div class="ms-announce-icon" :class="'announce-icon-' + a.urgency">
                  <el-icon :size="18"><Bell /></el-icon>
                </div>
                <div class="ms-announce-main">
                  <div class="ms-announce-top">
                    <span class="ms-announce-title">{{ a.title }}</span>
                    <el-tag :type="urgencyType(a.urgency)" size="small" effect="light" round>{{ urgencyLabel(a.urgency) }}</el-tag>
                  </div>
                  <div class="ms-announce-content">{{ a.content }}</div>
                  <div class="ms-announce-footer">
                    <span>{{ formatDate(a.created_at) }}</span>
                    <el-button text type="danger" size="small" @click="handleDeleteAnnouncement(a.id)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 更多 -->
          <template v-else-if="activeSubPage === 'more'">
            <div class="ms-more-list">
              <div class="ms-more-item" @click="router.push('/teacher/agent')">
                <el-icon color="#6366f1"><ChatDotRound /></el-icon>
                <span>绵小城智能助手</span>
                <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
              </div>
              <div class="ms-more-item" @click="router.push('/teacher/messages')">
                <el-icon color="#10b981"><Message /></el-icon>
                <span>消息</span>
                <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
              </div>
              <div class="ms-more-item" @click="openStudentsCrisis()">
                <el-icon color="#f56c6c"><WarningFilled /></el-icon>
                <span>高危学生名单</span>
                <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
              </div>
              <div class="ms-more-item" @click="router.push('/teacher/profile')">
                <el-icon color="#5b8def"><User /></el-icon>
                <span>个人中心</span>
                <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
              </div>
              <div class="ms-more-item" @click="handleExportStudents">
                <el-icon color="#67c23a"><Download /></el-icon>
                <span>导出学生数据</span>
                <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
              </div>
              <div class="ms-more-item" @click="importVisible = true">
                <el-icon color="#e6a23c"><Upload /></el-icon>
                <span>导入学生数据</span>
                <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
              </div>
            </div>
          </template>
        </div>
      </div>
    </transition>

    <!-- 移动端筛选抽屉 -->
    <el-drawer v-if="isMobile" v-model="showFilterSheet" title="筛选学生" direction="btt" size="55%" :close-on-click-modal="false">
      <div class="ms-drawer-body">
        <div class="ms-drawer-group">
          <div class="ms-drawer-label">危机等级</div>
          <div class="ms-filter-chips">
            <button v-for="c in crisisChips" :key="c.value" class="ms-chip" :class="{ active: filterCrisis === c.value }" @click="filterCrisis = c.value">{{ c.label }}</button>
          </div>
        </div>
        <div class="ms-drawer-group">
          <div class="ms-drawer-label">成长成果</div>
          <div class="ms-filter-chips">
            <button v-for="c in growthChips" :key="c.value" class="ms-chip" :class="{ active: filterGrowth === c.value }" @click="filterGrowth = c.value">{{ c.label }}</button>
          </div>
        </div>
        <div class="ms-drawer-group">
          <div class="ms-drawer-label">综合评分</div>
          <div class="ms-filter-chips">
            <button v-for="c in scoreChips" :key="c.value" class="ms-chip" :class="{ active: filterScore === c.value }" @click="filterScore = c.value">{{ c.label }}</button>
          </div>
        </div>
        <div class="ms-drawer-actions">
          <el-button text type="info" @click="clearFilters">清除筛选</el-button>
          <el-button type="primary" @click="showFilterSheet = false">完成</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 移动端学生详情右滑页 -->
    <transition name="slide-right-in">
      <div v-if="isMobile && detailVisible && detail" class="mobile-detail-page">
        <div class="mobile-detail-header">
          <el-button text circle @click="detailVisible = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="mobile-detail-title">{{ detail.name }} - 学生详情</span>
          <div style="width:36px"></div>
        </div>
        <div class="mobile-detail-body">
          <div class="mobile-profile">
            <el-avatar :size="48" :src="detail.avatar || undefined">{{ detail.name[0] }}</el-avatar>
            <div class="mobile-profile-info">
              <strong>{{ detail.name }}</strong>
              <small>{{ detail.college || '未分配' }} · {{ detail.username }}</small>
            </div>
          </div>
          <el-tabs v-model="detailTab" class="mobile-tabs">
            <el-tab-pane label="技能" name="skills">
              <div class="mobile-tab-content">
                <div v-if="detail.skills_json?.skills?.length" class="mobile-skill-list">
                  <el-tag v-for="sk in detail.skills_json.skills" :key="sk.name" size="small">{{ sk.name }}</el-tag>
                </div>
                <div v-if="detail.skills_json?.interests?.length" class="mobile-skill-list">
                  <el-tag v-for="i in detail.skills_json.interests" :key="i" size="small" round type="info">{{ i }}</el-tag>
                </div>
                <el-empty v-if="!detail.skills_json?.skills?.length && !detail.skills_json?.interests?.length" description="暂无数据" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="成长" name="growth">
              <div class="mobile-tab-content">
                <div v-for="r in detail.growth_records" :key="r.id" class="mobile-record-card">
                  <div class="mobile-record-top">
                    <el-tag size="small" :type="growthType(r.type)">{{ growthLabel(r.type) }}</el-tag>
                    <small>{{ r.date }}</small>
                  </div>
                  <div class="mobile-record-title">{{ r.title }}</div>
                  <div v-if="r.description" class="mobile-record-desc">{{ r.description }}</div>
                </div>
                <el-empty v-if="!detail.growth_records?.length" description="暂无记录" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="预警" name="crisis">
              <div class="mobile-tab-content">
                <div v-for="a in detail.crisis_alerts" :key="a.id" class="mobile-record-card">
                  <el-alert :title="crisisLabel(a.level)" :type="crisisType(a.level)" :description="a.summary" :closable="false" show-icon />
                </div>
                <el-empty v-if="!detail.crisis_alerts?.length" description="暂无预警" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="项目" name="projects">
              <div class="mobile-tab-content">
                <div v-for="p in detail.projects" :key="p.id" class="mobile-record-card">
                  <div class="mobile-record-top">
                    <el-tag v-if="p.is_team" size="small" type="primary" round>团队</el-tag>
                    <el-tag v-else size="small" type="info" round>个人</el-tag>
                    <small>{{ p.start_date }} ~ {{ p.end_date || '至今' }}</small>
                  </div>
                  <div class="mobile-record-title">{{ p.project_name }}</div>
                  <div v-if="p.team_members" class="mobile-record-desc">成员：{{ p.team_members }}</div>
                </div>
                <el-empty v-if="!detail.projects?.length" description="暂无项目" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="请假" name="leave">
              <div class="mobile-tab-content">
                <div v-for="l in detail.leave_requests" :key="l.id" class="mobile-record-card">
                  <div class="mobile-record-top">
                    <el-tag size="small" :type="l.status === 'approved' ? 'success' : l.status === 'rejected' ? 'danger' : 'warning'">
                      {{ l.status === 'approved' ? '通过' : l.status === 'rejected' ? '拒绝' : '待批' }}
                    </el-tag>
                    <small>{{ l.start_date }} ~ {{ l.end_date }}</small>
                  </div>
                  <div class="mobile-record-title">{{ leaveTypeLabel(l.leave_type) }}</div>
                  <div class="mobile-record-desc">{{ l.reason }}</div>
                </div>
                <el-empty v-if="!detail.leave_requests?.length" description="无请假记录" :image-size="48" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </transition>

    <!-- 拒绝对话框 -->
    <el-dialog v-model="rejectVisible" title="拒绝理由" width="90%" :close-on-click-modal="false" class="ms-dialog" align-center>
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写拒绝理由" maxlength="200" show-word-limit />
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>

    <!-- 发布公告 Dialog -->
    <el-dialog v-model="createDialogVisible" title="发布公告" width="90%" :close-on-click-modal="false" class="ms-dialog" align-center>
      <el-form :model="createForm" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="createForm.title" placeholder="请输入公告标题" maxlength="200" />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="createForm.content" type="textarea" :rows="4" placeholder="请输入公告内容" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="createForm.urgency">
            <el-radio value="normal">普通</el-radio>
            <el-radio value="important">重要</el-radio>
            <el-radio value="urgent">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateAnnouncement">发布</el-button>
      </template>
    </el-dialog>

    <!-- 导入学生数据 Dialog -->
    <el-dialog v-model="importVisible" title="导入学生数据" width="90%" :close-on-click-modal="false" class="ms-dialog" align-center>
      <div class="ms-import-tip">
        <p>请上传 CSV 文件，表头需包含「姓名、学号」两列，可选「学院、性别、班级」。导入的账号默认密码为 123456。</p>
        <el-link type="primary" :underline="false" @click="handleDownloadTemplate">
          <el-icon style="margin-right:3px"><Download /></el-icon>下载导入模板
        </el-link>
      </div>

      <label class="ms-import-upload">
        <el-icon :size="18"><Upload /></el-icon>
        <span>{{ importRows.length ? `已选择 ${importRows.length} 名学生` : '选择 CSV 文件' }}</span>
        <input type="file" accept=".csv,text/csv" @change="handleImportFile" />
      </label>

      <div v-if="importRows.length" class="ms-import-preview">
        <div class="ms-import-preview-head">待导入（预览前 5 条）</div>
        <div v-for="(r, i) in importRows.slice(0, 5)" :key="i" class="ms-import-preview-row">
          <span class="ms-import-preview-name">{{ r.name }}</span>
          <span class="ms-import-preview-username">{{ r.username }}</span>
          <span class="ms-import-preview-college">{{ r.college || '-' }}</span>
        </div>
        <div v-if="importSkipped.length" class="ms-import-skipped">有 {{ importSkipped.length }} 条数据格式不完整，将被忽略</div>
      </div>

      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importRows.length" @click="confirmImport">
          {{ importing ? '导入中...' : `确认导入（${importRows.length}）` }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, User, View, ChatDotRound, Close, ArrowLeft, ArrowRight,
  WarningFilled, DataAnalysis, Calendar, Bell, MoreFilled,
  Histogram, Message, Plus, Check, Loading, Filter, Download, Upload,
} from '@element-plus/icons-vue'
import {
  getStudents, getStudentDetail, getDashboardStats, getClassEvaluation, getClassStats, importStudents,
  type StudentSummary, type StudentDetail, type DashboardStats, type ClassEvaluation, type ClassStats, type StudentImportItem,
} from '@/api/teacher'
import { getPendingLeaves, getAllLeaves, reviewLeave } from '@/api/leave'
import { getTeacherAnnouncements, createAnnouncement, deleteAnnouncement, type AnnouncementItem } from '@/api/announcement'
import { getConversations, type ConversationOut } from '@/api/messages'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useAiAnalysis } from '@/composables/useAiAnalysis'
import { renderMarkdown } from '@/utils/markdown'
import type { LeaveRequestOut } from '@/types'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, PieChart, LineChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent, RadarComponent, GridComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, RadarChart, PieChart, LineChart, TooltipComponent, LegendComponent, RadarComponent, GridComponent])

defineOptions({ name: 'teacher-students' })

const { isMobile } = useResponsive()
const router = useRouter()
const authStore = useAuthStore()

const search = ref('')
const students = ref<(StudentSummary & { score?: number })[]>([])
const loaded = ref(false)
const detailVisible = ref(false)
const detail = ref<StudentDetail | null>(null)
const detailTab = ref('skills')

const filterCrisis = ref('')
const filterGrowth = ref('')
const filterScore = ref('')
const filterSkill = ref('')

const currentPage = ref(1)
const pageSize = ref(12)

const showFilterSheet = ref(false)
const activeSubPage = ref<'students' | 'analysis' | 'lease' | 'announcement' | 'more' | null>(null)

const teacherName = computed(() => authStore.userName || '教师')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const subPageTitle = computed(() => {
  const map: Record<string, string> = {
    students: '学员',
    analysis: '学生分析',
    lease: '请假情况',
    announcement: '班级公告',
    more: '更多功能',
  }
  return map[activeSubPage.value || ''] || ''
})

// ===== 统计 =====
const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})

// ===== 班级图表数据 =====
const evalData = ref<ClassEvaluation>({
  total_students: 0, avg_gpa: 0, avg_score: 0,
  growth: {}, crisis: {}, pending_leaves: 0,
})
const classStats = ref<ClassStats>({
  total_students: 0,
  gender_stats: {}, crisis_stats: {}, grade_stats: {},
  political_stats: {}, hometown_stats: {}, crisis_trend: [],
})

// ===== 请假 =====
const leaveTab = ref('pending')
const pendingLeaves = ref<LeaveRequestOut[]>([])
const approvedLeaves = ref<LeaveRequestOut[]>([])
const rejectedLeaves = ref<LeaveRequestOut[]>([])
const rejectVisible = ref(false)
const rejectTarget = ref<LeaveRequestOut | null>(null)
const rejectReason = ref('')

// ===== 公告 =====
const myAnnouncements = ref<AnnouncementItem[]>([])
const createDialogVisible = ref(false)
const createForm = ref({ title: '', content: '', urgency: 'normal' as 'normal' | 'important' | 'urgent' })

// ===== 导入导出 =====
const importVisible = ref(false)
const importing = ref(false)
const importRows = ref<StudentImportItem[]>([])
const importSkipped = ref<string[]>([])

// ===== AI 分析 =====
const { loading: analysisLoading, renderedResult: analysisResult, analyze: runAnalysis } = useAiAnalysis('teacher-class-analysis')
const renderedAnalysisHtml = computed(() => renderMarkdown(analysisResult.value))

// ===== 最近互动（按最近聊天排序） =====
const conversations = ref<ConversationOut[]>([])

const conversationTimeMap = computed(() => {
  const map = new Map<number, string>()
  conversations.value.forEach(c => {
    if (c.last_message_time) map.set(c.user_id, c.last_message_time)
  })
  return map
})

const sortedByRecentChat = computed(() => {
  const timeMap = conversationTimeMap.value
  return [...students.value].sort((a, b) => {
    const ta = timeMap.get(a.id)
    const tb = timeMap.get(b.id)
    if (ta && tb) return tb.localeCompare(ta)
    if (ta) return -1
    if (tb) return 1
    return 0
  })
})

const recentStudents = computed(() => sortedByRecentChat.value.slice(0, 6))

// ===== 筛选 chips =====
const crisisChips = [
  { label: '全部', value: '' },
  { label: '高危', value: 'severe' },
  { label: '中度', value: 'moderate' },
  { label: '轻度', value: 'mild' },
  { label: '无预警', value: 'none' },
]
const growthChips = [
  { label: '全部', value: '' },
  { label: '有成果', value: 'has' },
  { label: '无成果', value: 'none' },
]
const scoreChips = [
  { label: '全部', value: '' },
  { label: '优秀≥90', value: 'excellent' },
  { label: '良好≥75', value: 'good' },
  { label: '及格≥60', value: 'average' },
  { label: '不及格', value: 'poor' },
]

const hasActiveFilter = computed(() => {
  return filterCrisis.value || filterGrowth.value || filterScore.value || filterSkill.value
})

const isSearching = computed(() => search.value.trim() !== '')

const filteredStudents = computed(() => {
  return students.value.filter(s => {
    if (filterCrisis.value) {
      if (filterCrisis.value === 'none') {
        if (s.crisis_level) return false
      } else {
        if (s.crisis_level !== filterCrisis.value) return false
      }
    }

    if (filterGrowth.value) {
      if (filterGrowth.value === 'has' && (!s.growth_count || s.growth_count === 0)) return false
      if (filterGrowth.value === 'none' && s.growth_count && s.growth_count > 0) return false
    }

    if (filterScore.value && s.score !== undefined) {
      if (filterScore.value === 'excellent' && s.score < 90) return false
      if (filterScore.value === 'good' && (s.score < 75 || s.score >= 90)) return false
      if (filterScore.value === 'average' && (s.score < 60 || s.score >= 75)) return false
      if (filterScore.value === 'poor' && s.score >= 60) return false
    }

    if (filterSkill.value) {
      const hasSkills = s.skills_json?.skills?.length && s.skills_json.skills.length > 0
      if (filterSkill.value === 'has' && !hasSkills) return false
      if (filterSkill.value === 'none' && hasSkills) return false
    }

    return true
  })
})

function clearFilters() {
  filterCrisis.value = ''
  filterGrowth.value = ''
  filterScore.value = ''
  filterSkill.value = ''
  currentPage.value = 1
}

const pagedStudents = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredStudents.value.slice(start, end)
})

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 页码变化时自动更新（通过 computed 自动响应）
}

// ===== 图表 options =====
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
      splitArea: { areaStyle: { color: ['rgba(91,141,239,0.02)', 'rgba(91,141,239,0.06)'] } },
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

const crisisPieOptions = computed(() => {
  const data = classStats.value.crisis_stats
  if (!data) return null
  const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#909399']
  const names = ['高危', '中危', '低危', '已解决']
  const values = [data.severe || 0, data.moderate || 0, data.mild || 0, data.resolved || 0]
  const total = values.reduce((sum, v) => sum + v, 0)
  if (total === 0) return null
  const pieData = names.map((name, index) => ({ name, value: values[index], itemStyle: { color: colors[index] } }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
    legend: { orient: 'horizontal', bottom: 5, textStyle: { color: '#666', fontSize: 11 } },
    animation: false,
    series: [{
      name: '危机分布',
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
      data: pieData,
    }],
  }
})

const crisisTrendOptions = computed(() => {
  const data = classStats.value.crisis_trend
  if (!data || data.length === 0) return null
  return {
    tooltip: { trigger: 'axis', formatter: '{b}<br/>预警数量: {c}' },
    grid: { left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true },
    xAxis: { type: 'category', data: data.map(d => d.month), axisLabel: { color: '#666', fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { color: '#666' } },
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
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(245,108,108,0.3)' },
            { offset: 1, color: 'rgba(245,108,108,0.05)' },
          ],
        },
      },
    }],
  }
})

// ===== 业务函数 =====
function openSubPage(page: 'students' | 'analysis' | 'lease' | 'announcement' | 'more') {
  activeSubPage.value = page
  if (page === 'analysis') loadAnalysisData()
  if (page === 'lease') loadLeaveData()
  if (page === 'announcement') loadMyAnnouncements()
}

function openStudentsCrisis() {
  filterCrisis.value = 'severe'
  activeSubPage.value = 'students'
}

async function loadStudents() {
  try {
    students.value = await getStudents(search.value || undefined)
    loaded.value = true
  } catch {}
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
const debouncedLoadStudents = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadStudents()
  }, 300)
}

async function loadDashboard() {
  try {
    stats.value = await getDashboardStats()
  } catch {}
  try {
    conversations.value = await getConversations()
  } catch {}
}

async function loadAnalysisData() {
  try {
    evalData.value = await getClassEvaluation()
  } catch {}
  try {
    classStats.value = await getClassStats()
  } catch {}
}

async function loadLeaveData() {
  const tab = leaveTab.value
  try {
    if (tab === 'pending') pendingLeaves.value = await getPendingLeaves()
    else if (tab === 'approved') approvedLeaves.value = await getAllLeaves('approved')
    else if (tab === 'rejected') rejectedLeaves.value = await getAllLeaves('rejected')
  } catch {}
}

async function handleApprove(row: LeaveRequestOut) {
  try {
    await reviewLeave(row.id, 'approve')
    ElMessage.success('已通过')
    loadLeaveData()
  } catch { ElMessage.error('操作失败') }
}

function showReject(row: LeaveRequestOut) {
  rejectTarget.value = row
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject() {
  if (!rejectReason.value.trim()) { ElMessage.warning('请填写拒绝理由'); return }
  if (!rejectTarget.value) return
  try {
    await reviewLeave(rejectTarget.value.id, 'reject', rejectReason.value)
    ElMessage.success('已拒绝')
    rejectVisible.value = false
    loadLeaveData()
  } catch { ElMessage.error('操作失败') }
}

async function loadMyAnnouncements() {
  try {
    myAnnouncements.value = await getTeacherAnnouncements()
  } catch {}
}

function openCreateDialog() {
  createForm.value = { title: '', content: '', urgency: 'normal' }
  createDialogVisible.value = true
}

async function handleCreateAnnouncement() {
  if (!createForm.value.title.trim() || !createForm.value.content.trim()) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  const fd = new FormData()
  fd.append('title', createForm.value.title)
  fd.append('content', createForm.value.content)
  fd.append('urgency', createForm.value.urgency)
  try {
    await createAnnouncement(fd)
    ElMessage.success('公告已发布')
    createDialogVisible.value = false
    loadMyAnnouncements()
  } catch { ElMessage.error('发布失败') }
}

async function handleDeleteAnnouncement(id: number) {
  try {
    await deleteAnnouncement(id)
    ElMessage.success('已删除')
    loadMyAnnouncements()
  } catch { ElMessage.error('删除失败') }
}

// ===== 数据导入导出 =====
function handleExportStudents() {
  if (!students.value.length) { ElMessage.warning('暂无学生数据可导出'); return }
  const header = ['姓名', '学号', '学院', '综合评分', '心理状态', '成长记录(条)', '请假(次)']
  const rows = students.value.map(s => [
    s.name,
    s.username,
    s.college || '',
    s.score ?? '',
    crisisLevelLabel(s.crisis_level),
    s.growth_count,
    s.leave_count,
  ])
  const csv = [header, ...rows].map(r => r.map(cell => {
    const str = String(cell ?? '')
    return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str
  }).join(',')).join('\r\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `学生数据_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出学生数据')
}

function handleDownloadTemplate() {
  const header = ['姓名', '学号', '学院', '性别', '班级']
  const example = ['张三', '20240001', '人工智能学院', '男', 'AI2401']
  const csv = [header, example].map(r => r.join(',')).join('\r\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '学生导入模板.csv'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function parseCsvLine(line: string): string[] {
  const cells: string[] = []
  let cur = ''
  let inQuote = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuote) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++ }
        else inQuote = false
      } else cur += ch
    } else if (ch === '"') {
      inQuote = true
    } else if (ch === ',') {
      cells.push(cur); cur = ''
    } else cur += ch
  }
  cells.push(cur)
  return cells
}

function handleImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importRows.value = []
  importSkipped.value = []
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const text = String(reader.result || '').replace(/^\ufeff/, '')
      const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
      if (lines.length < 2) { ElMessage.warning('文件内容为空或格式不正确'); return }
      const rows: StudentImportItem[] = []
      const skipped: string[] = []
      lines.slice(1).forEach(l => {
        const [name, username, college, gender, class_name] = parseCsvLine(l)
        if (name && username) {
          rows.push({ name, username, college: college || undefined, gender: gender || undefined, class_name: class_name || undefined })
        } else {
          skipped.push(l)
        }
      })
      if (!rows.length) { ElMessage.warning('未识别到有效数据，请检查文件格式'); return }
      importRows.value = rows
      importSkipped.value = skipped
    } catch {
      ElMessage.error('文件解析失败')
    }
  }
  reader.readAsText(file, 'utf-8')
  input.value = ''
}

async function confirmImport() {
  if (!importRows.value.length) return
  importing.value = true
  try {
    const res = await importStudents(importRows.value)
    ElMessage.success(`成功导入 ${res.created} 名学生${res.skipped.length ? `，跳过 ${res.skipped.length} 条` : ''}`)
    importVisible.value = false
    importRows.value = []
    await loadStudents()
    loadDashboard()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

// ===== AI 分析 =====
async function handleClassAnalysis() {
  await loadAnalysisData()
  const cs = classStats.value
  const ev = evalData.value
  const g = ev.growth || {}
  const profiles = students.value.slice(0, 60).map(p => {
    const crisisNote = p.crisis_level && p.latest_crisis_summary
      ? `、最近危机「${p.latest_crisis_summary.slice(0, 40)}」`
      : ''
    return `- ${p.name}：成长记录${p.growth_count}条、综合评分${p.score}分、心理状态「${crisisLevelLabel(p.crisis_level)}」${crisisNote}`
  }).join('\n')

  const prompt = `作为辅导员老师，请分析班级情况并提出建议：

班级图表数据：
- 学生总数：${cs.total_students}
- 心理危机分布：高危${cs.crisis_stats?.severe || 0}人、中危${cs.crisis_stats?.moderate || 0}人、低危${cs.crisis_stats?.mild || 0}人
- 危机预警趋势：${JSON.stringify(cs.crisis_trend)}

班级成长数据：
- 平均GPA：${ev.avg_gpa}，平均综合评分：${ev.avg_score}
- 成长统计：荣誉${g.honor || 0}、竞赛${g.competition || 0}、实践${g.practice || 0}、论文${g.paper || 0}、成果${g.achievement || 0}

手下学生成长明细：
${profiles || '（暂无）'}

请从班级整体概况、成长分析、心理健康与危机预警、辅导员工作建议（对重点关注学生点名提醒）等方面分析，控制在400字以内。`

  await runAnalysis(prompt, { skipCache: true })
}

// ===== 工具函数 =====
function crisisType(level: string) {
  const map: Record<string, string> = { severe: 'danger', moderate: 'warning', mild: 'info' }
  return map[level] || 'info'
}

function crisisLabel(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度' }
  return map[level] || level
}

function crisisLevelLabel(level?: string | null) {
  const map: Record<string, string> = { severe: '高危预警', moderate: '中危预警', mild: '低危预警', resolved: '已解决' }
  return level ? (map[level] || level) : '暂无预警'
}

function growthType(t: string) {
  const map: Record<string, string> = { honor: 'primary', competition: 'success', award: 'warning', practice: 'info' }
  return map[t] || 'info'
}

function growthLabel(t: string) {
  const map: Record<string, string> = { honor: '荣誉', competition: '竞赛', award: '奖项', practice: '实践', paper: '论文', achievement: '成果' }
  return map[t] || t
}

function leaveTypeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

function formatTime(t: string) {
  try { return new Date(t).toLocaleString('zh-CN') } catch { return t }
}

function formatDate(dateStr: string) {
  try { return new Date(dateStr).toLocaleDateString('zh-CN') } catch { return dateStr }
}

function urgencyType(u: string) {
  const map: Record<string, string> = { urgent: 'danger', important: 'warning', normal: 'info' }
  return map[u] || 'info'
}

function urgencyLabel(u: string) {
  const map: Record<string, string> = { urgent: '紧急', important: '重要', normal: '普通' }
  return map[u] || '普通'
}

function scoreClass(score: number) {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-average'
  return 'score-poor'
}

async function openDetail(s: StudentSummary) {
  try {
    detail.value = await getStudentDetail(s.id)
    detailVisible.value = true
    detailTab.value = 'skills'
  } catch {}
}

function openContact(s: StudentSummary) {
  router.push({ path: '/teacher/messages', query: { studentId: String(s.id), studentName: s.name } })
}

onMounted(() => {
  loadStudents()
  loadDashboard()
})
</script>

<style scoped>
.students-page { height: 100%; overflow-y: auto; overflow-x: hidden; padding: 8px 4px; }

/* ===== 桌面端样式（保留原样） ===== */
.page-header {
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-bottom: 12px; padding: 0 4px;
}
.header-left h2 { font-size: 18px; font-weight:700; color:#1a1a2e; margin:0; }
.page-sub { font-size: 12px; color: #888; margin: 3px 0 0; }
.page-sub strong { color: #5b8def; }
.header-actions { display: flex; gap: 8px; align-items: center; }

.filter-bar {
  display: flex; gap: 8px; margin-bottom: 14px; padding: 10px 14px;
  background: linear-gradient(135deg, #f8faff 0%, #f0f8ff 100%);
  border-radius: 10px; border: 1px solid rgba(64,158,255,0.12);
  flex-wrap: wrap; align-items: center;
  box-shadow: 0 1px 6px rgba(64,158,255,0.06);
}

.student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.student-card {
  background: #fff; border-radius: 10px; padding: 14px;
  border: 1px solid rgba(0,0,0,0.04); box-shadow: 0 1px 6px rgba(0,0,0,0.03);
  transition: all 0.2s ease; cursor: default;
}
.student-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
.student-card.level-severe { border-left: 3px solid #f56c6c; }
.student-card.level-moderate { border-left: 3px solid #e6a23c; }
.student-card.level-mild { border-left: 3px solid #909399; }
.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.card-avatar { flex-shrink: 0; }
.card-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.card-name { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.card-college { font-size: 11px; color: #999; margin-top: 1px; }
.crisis-tag { flex-shrink: 0; }
.card-stats {
  display: flex; gap: 12px; margin-bottom: 10px;
  padding: 8px 0; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5;
}
.stat-item { display: flex; flex-direction: column; align-items: center; flex: 1; }
.stat-num { font-size: 15px; font-weight: 700; color: #333; line-height: 1.2; }
.stat-text { font-size: 10px; color: #999; margin-top: 1px; }
.score-excellent .stat-num, .score-excellent { color: #67c23a; }
.score-good .stat-num, .score-good { color: #409eff; }
.score-average .stat-num, .score-average { color: #e6a23c; }
.score-poor .stat-num, .score-poor { color: #f56c6c; }
.card-skills { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }
.card-actions { display: flex; gap: 6px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; padding: 12px 0; }

:deep(.student-detail-dialog .el-dialog) { height: 520px !important; margin: 12vh auto !important; }
:deep(.student-detail-dialog .el-dialog__body) {
  height: 400px !important; padding: 14px 18px !important;
  display: flex !important; flex-direction: column !important; overflow: hidden !important;
}
.dialog-body { height: 100%; display: flex; flex-direction: column; }
.dialog-profile {
  display: flex; align-items: center; gap: 12px;
  padding: 0 0 12px 0; border-bottom: 1px solid #f0f0f0; margin-bottom: 12px; flex-shrink: 0;
}
.dialog-profile-info { display: flex; flex-direction: column; }
.dialog-profile-info strong { font-size: 15px; }
.dialog-profile-info small { font-size: 12px; color: #999; }
.dialog-tabs-wrapper { flex: 1; min-height: 0; overflow: hidden; }
:deep(.detail-tabs) { height: 100%; }
:deep(.detail-tabs .el-tabs__header) { flex-shrink: 0; margin-bottom: 8px; }
:deep(.detail-tabs .el-tabs__content) { flex: 1; min-height: 0; overflow: hidden !important; }
:deep(.detail-tabs .el-tab-pane) { height: 100%; overflow: hidden; }
.tab-content { height: 100%; overflow-y: auto; -ms-overflow-style: none; scrollbar-width: none; }
.tab-content::-webkit-scrollbar { display: none; }
.skill-list { display: flex; flex-direction: column; gap: 6px; }
.skill-item { display: flex; align-items: center; gap: 6px; }

/* ===== 移动端样式（支付宝风格） ===== */
.ms-header {
  background: linear-gradient(160deg, #2374f0 0%, #1a5fe0 60%, #327df0 100%);
  padding: 0 16px 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.ms-header::after {
  content: '';
  position: absolute; top: -70px; right: -60px;
  width: 200px; height: 200px; border-radius: 50%;
  background: rgba(255,255,255,0.07); pointer-events: none;
}
.ms-statusbar-space { height: 14px; }
.ms-header-top { display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 1; }
.ms-header-greet { display: flex; flex-direction: column; gap: 4px; }
.ms-greet-line1 { font-size: 16px; font-weight: 600; letter-spacing: 0.5px; }
.ms-greet-line2 { font-size: 11px; opacity: 0.82; letter-spacing: 1.5px; }
.ms-mascot {
  width: 38px; height: 38px; object-fit: contain;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,0.22));
  flex-shrink: 0;
}
.ms-search {
  margin-top: 12px; position: relative; z-index: 1;
}
.ms-search-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.96);
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  padding: 4px 14px;
}
.ms-search-input :deep(.el-input__wrapper.is-focus) { box-shadow: 0 2px 10px rgba(0,0,0,0.12); }
.ms-search-input :deep(.el-input__inner) { height: 34px; color: #1a1a2e; font-size: 13px; }
.ms-search-input :deep(.el-input__inner::placeholder) { color: #a6a9ad; }

/* 通用卡片 */
.ms-card {
  background: #fff; border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  overflow: hidden;
}
.ms-stats-card { margin: -10px 12px 0; padding: 14px 6px; position: relative; z-index: 2; }
.ms-stats { display: flex; align-items: center; }
.ms-stat-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; cursor: pointer; }
.ms-stat-item:active { opacity: 0.7; }
.ms-stat-num { font-size: 20px; font-weight: 700; line-height: 1; font-family: 'DIN Alternate', 'Avenir', sans-serif; }
.ms-stat-label { font-size: 11px; color: #888; }
.ms-stat-divider { width: 1px; height: 24px; background: #f0f1f3; }

.ms-modules { margin: 10px 12px 0; padding: 12px 4px 6px; }
.ms-module-grid { display: flex; justify-content: space-around; align-items: flex-start; }
.ms-module-cell { display: flex; flex-direction: column; align-items: center; gap: 6px; flex: 1; cursor: pointer; }
.ms-module-cell:active { opacity: 0.7; }
.ms-module-icon {
  width: 40px; height: 40px; border-radius: 50%; color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}
.ms-module-name { font-size: 11px; color: #333; }

.ms-section-title { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px 8px; }
.ms-section-title-text { font-size: 15px; font-weight: 700; color: #1a1a2e; }
.ms-section-title-extra { display: flex; align-items: center; gap: 2px; font-size: 12px; color: #1677ff; }

.ms-student-list { margin: 0 12px; }
.ms-student-card {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px; margin: 0 2px;
  border-bottom: 1px solid #f5f6f7; cursor: pointer;
}
.ms-student-card.no-border { border-bottom: none; }
.ms-student-card:active { background: #fafafa; }
.ms-student-avatar { flex-shrink: 0; }
.ms-student-info { flex: 1; display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ms-student-name { display: flex; align-items: center; font-size: 14px; font-weight: 600; color: #1a1a2e; }
.ms-student-tag { margin-left: 6px; }
.ms-student-sub { font-size: 12px; color: #999; }
.ms-student-arrow { flex-shrink: 0; }

.ms-empty { text-align: center; color: #999; font-size: 13px; padding: 26px 0; }

/* ===== 移动端右滑子页面 ===== */
.ms-sub-page {
  position: fixed; inset: 0; background: #f5f6f7;
  z-index: 200; display: flex; flex-direction: column; overflow: hidden;
}
.ms-sub-header {
  display: flex; align-items: center; justify-content: space-between;
  height: 50px; padding: 0 12px; background: #fff; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
.ms-sub-title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.ms-sub-body { flex: 1; overflow-y: auto; padding: 12px; }

.ms-search-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.ms-search-input-wrap { flex: 1; }
.ms-search-input-wrap :deep(.el-input__wrapper) {
  border-radius: 22px; padding: 1px 14px;
  background: #fff; box-shadow: 0 0 0 1px #fff inset;
  height: 40px;
}
.ms-search-input-wrap :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #1677ff inset; }
.ms-search-input-wrap :deep(.el-input__inner) { height: 40px; }
.ms-filter-btn {
  display: flex; align-items: center; gap: 4px;
  height: 40px; padding: 0 12px; border-radius: 20px;
  background: #fff; color: #1677ff; font-size: 14px; cursor: pointer; flex-shrink: 0;
}
.ms-filter-btn:active { opacity: 0.7; }

.ms-chip-scroll {
  display: flex; gap: 8px; overflow-x: auto; padding: 4px 2px 12px;
  -ms-overflow-style: none; scrollbar-width: none;
}
.ms-chip-scroll::-webkit-scrollbar { display: none; }
.ms-chip {
  flex-shrink: 0; padding: 6px 16px; border-radius: 18px; border: none;
  background: #fff; color: #555; font-size: 13px; cursor: pointer;
}
.ms-chip.active { background: #1677ff; color: #fff; font-weight: 600; }

.ms-analysis-grid { display: flex; flex-direction: column; gap: 10px; }
.ms-chart-card {
  background: #fff; border-radius: 14px; padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
.ms-chart-card-header { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: #1f2937; margin-bottom: 8px; }
.ms-chart-container { height: 200px; }

.ms-ai-card {
  background: #fff; border-radius: 14px; padding: 12px; margin-top: 10px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
.ms-ai-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.ms-ai-mascot { width: 36px; height: 36px; object-fit: contain; }
.ms-ai-title { font-size: 14px; font-weight: 600; color: #1f2937; }
.ms-ai-placeholder p { font-size: 13px; color: #666; line-height: 1.6; margin: 0 0 12px; }
.ms-ai-loading { display: flex; align-items: center; gap: 8px; color: #666; font-size: 13px; }
.ms-ai-text { font-size: 13px; color: #333; line-height: 1.7; }
.ms-ai-text :deep(.md-h2), .ms-ai-text :deep(.md-h3), .ms-ai-text :deep(.md-h4) { color: #1a1a2e; margin: 10px 0 6px; }
.ms-ai-text :deep(.md-li) { margin: 4px 0; }
.ms-ai-text :deep(.md-ul) { padding-left: 18px; }

.ms-lease-card {
  background: #fff; border-radius: 14px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.ms-lease-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.ms-lease-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.ms-lease-date { font-size: 13px; color: #666; margin-bottom: 4px; }
.ms-lease-reason { font-size: 13px; color: #999; line-height: 1.4; margin-bottom: 8px; }
.ms-lease-actions { display: flex; gap: 8px; }

.ms-announce-publish {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; height: 44px; border: none; border-radius: 12px;
  background: linear-gradient(135deg, #2374f0 0%, #1a5fe0 100%);
  color: #fff; font-size: 15px; font-weight: 600; cursor: pointer;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(35,116,240,0.25);
}
.ms-announce-publish:active { transform: scale(0.98); }

.ms-announce-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  text-align: center; padding: 48px 20px; color: #999;
}
.ms-announce-empty-icon {
  width: 64px; height: 64px; border-radius: 50%; background: #f2f4f7;
  display: flex; align-items: center; justify-content: center; color: #c0c4cc;
}
.ms-announce-empty p { margin: 0; font-size: 15px; color: #666; font-weight: 600; }
.ms-announce-empty span { font-size: 13px; color: #b0b5c0; }

.ms-announce-list { display: flex; flex-direction: column; gap: 10px; }
.ms-announce-card {
  display: flex; gap: 12px;
  background: #fff; border-radius: 14px; padding: 14px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
  position: relative; overflow: hidden;
}
.ms-announce-card.announce-urgent { border-left: 3px solid #f56c6c; }
.ms-announce-card.announce-important { border-left: 3px solid #e6a23c; }
.ms-announce-card.announce-normal { border-left: 3px solid #e5e7eb; }
.ms-announce-icon {
  width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.announce-icon-urgent { background: rgba(245,108,108,0.1); color: #f56c6c; }
.announce-icon-important { background: rgba(230,162,60,0.12); color: #e6a23c; }
.announce-icon-normal { background: rgba(144,147,153,0.1); color: #909399; }
.ms-announce-main { flex: 1; min-width: 0; }
.ms-announce-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.ms-announce-title { font-size: 15px; font-weight: 600; color: #1f2937; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ms-announce-content { font-size: 13px; color: #666; line-height: 1.6; margin-bottom: 8px; word-break: break-word; }
.ms-announce-footer { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: #999; }

.ms-more-list { display: flex; flex-direction: column; gap: 10px; }
.ms-more-item {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border-radius: 14px; padding: 16px 14px;
  font-size: 14px; color: #333;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.ms-more-item :deep(.el-icon:first-child) { font-size: 22px; }
.ms-more-item span { flex: 1; }
.ms-more-item:active { background: #fafafa; }

/* ===== 导入学生数据 ===== */
.ms-import-tip { font-size: 13px; color: #666; line-height: 1.6; margin-bottom: 14px; }
.ms-import-tip p { margin: 0 0 8px; }
.ms-import-upload {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; height: 48px; border: 1px dashed #c0c4cc; border-radius: 12px;
  background: #f7f9fc; color: #409eff; font-size: 14px; cursor: pointer;
  position: relative; overflow: hidden;
}
.ms-import-upload input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.ms-import-preview { margin-top: 14px; }
.ms-import-preview-head { font-size: 12px; color: #999; margin-bottom: 8px; }
.ms-import-preview-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; background: #f9fafb; border-radius: 8px; margin-bottom: 6px;
  font-size: 13px;
}
.ms-import-preview-name { font-weight: 600; color: #333; }
.ms-import-preview-username { color: #409eff; }
.ms-import-preview-college { color: #999; margin-left: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ms-import-skipped { margin-top: 8px; font-size: 12px; color: #e6a23c; }

.ms-drawer-body { padding: 0 8px; }
.ms-drawer-group { margin-bottom: 20px; }
.ms-drawer-label { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 12px; }
.ms-filter-chips { display: flex; flex-wrap: wrap; gap: 10px; }
.ms-drawer-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }

/* 移动端右滑动画 */
.slide-right-in-enter-active,
.slide-right-in-leave-active { transition: transform 0.25s ease; }
.slide-right-in-enter-from,
.slide-right-in-leave-to { transform: translateX(100%); }

.mobile-detail-page {
  position: fixed; inset: 0; top: 0; left: 0; right: 0; bottom: 0;
  background: #f5f7fa; z-index: 300; display: flex; flex-direction: column; overflow: hidden;
}
.mobile-detail-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fff; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
.mobile-detail-title { font-size: 15px; font-weight: 600; color: #1a1a1a; }
.mobile-detail-body { flex: 1; overflow-y: auto; padding: 12px; }
.mobile-profile {
  display: flex; align-items: center; gap: 12px; padding: 12px;
  background: #fff; border-radius: 10px; margin-bottom: 12px;
}
.mobile-profile-info { display: flex; flex-direction: column; gap: 2px; }
.mobile-profile-info strong { font-size: 15px; color: #1a1a1a; }
.mobile-profile-info small { font-size: 12px; color: #999; }
.mobile-tabs { background: #fff; border-radius: 10px; padding: 0 8px; }
.mobile-tabs :deep(.el-tabs__header) { margin-bottom: 8px; }
.mobile-tabs :deep(.el-tabs__item) { font-size: 13px; padding: 0 10px; height: 36px; line-height: 36px; }
.mobile-tab-content { padding: 0 4px 12px; }
.mobile-skill-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.mobile-record-card { padding: 10px; border-bottom: 1px solid #f5f5f5; }
.mobile-record-card:last-child { border-bottom: none; }
.mobile-record-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.mobile-record-top small { font-size: 11px; color: #999; }
.mobile-record-title { font-size: 14px; font-weight: 500; color: #333; margin-bottom: 4px; }
.mobile-record-desc { font-size: 12px; color: #666; line-height: 1.5; }

/* ===== 弹窗美化 ===== */
.ms-dialog :deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  padding: 0;
}
.ms-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 18px 18px 10px;
  text-align: center;
}
.ms-dialog :deep(.el-dialog__title) { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.ms-dialog :deep(.el-dialog__headerbtn) { top: 13px; right: 13px; }
.ms-dialog :deep(.el-dialog__body) { padding: 8px 18px 16px; }
.ms-dialog :deep(.el-dialog__footer) { padding: 0 18px 18px; }
.ms-dialog :deep(.el-dialog__footer .el-button) { border-radius: 22px; padding: 9px 22px; }

/* ===== 桌面端响应式（仅小屏桌面） ===== */
@media (max-width: 767px) {
  .students-page { padding: 0; background: #f5f6f7; }
}
</style>