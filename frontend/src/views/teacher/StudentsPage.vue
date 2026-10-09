<template>
  <div class="students-page">
    <!-- ============ 桌面端（保持原样） ============ -->
    <template v-if="!isMobile">
      <!-- 学生页头：页面标题 + 范围说明 + 更多操作 -->
      <header class="app-head">
        <div class="app-head-bar">
          <div class="app-head-lead">
            <h1 class="app-head-title">学生</h1>
            <p class="app-head-sub">名单 · 档案 · 数据分析</p>
          </div>
          <el-dropdown trigger="click" @command="onHeadCommand">
            <button class="app-icon-btn" type="button" aria-label="更多操作" title="更多操作">
              <el-icon :size="18"><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export"><el-icon><Download /></el-icon>导出学生数据</el-dropdown-item>
                <el-dropdown-item command="import"><el-icon><Upload /></el-icon>导入学生数据</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 概况便当格（Bento Grid）：模块化磁贴，每格只做一件事 -->
      <section class="bento">
        <div class="bento-tile bento-tile-lg">
          <span class="bento-label">在册学生</span>
          <span class="bento-value">{{ stats.total_students }}</span>
          <span class="bento-hint">成长档案 · 班级数据分析</span>
        </div>
        <div class="bento-tile">
          <span class="bento-label">高危学生</span>
          <span class="bento-value bento-value-warn">{{ stats.severe_alert_count }}</span>
        </div>
        <div class="bento-tile">
          <span class="bento-label">有成长成果</span>
          <span class="bento-value bento-value-ok">{{ growthCount }}</span>
        </div>
        <button class="bento-tile bento-tile-action" type="button" @click="showAnalyticsPage = true">
          <span class="bento-action-icon"><el-icon :size="18"><DataAnalysis /></el-icon></span>
          <span class="bento-action-main">
            <span class="bento-label">班级数据分析</span>
            <span class="bento-hint">成绩分布 · 心理危机 · 预警趋势</span>
          </span>
          <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
        </button>
      </section>

      <!-- 班级数据分析：与学生相关的数据维度，归属本页 -->
      <section class="analytics-section">
        <div class="analytics-section-head">
          <span class="analytics-section-title">班级数据分析</span>
          <span class="analytics-section-sub">班级综合评估 / 成绩分布 / 心理危机 / 学生成长等维度</span>
        </div>
        <ClassAnalyticsPanel
          :class-stats="classStats"
          :eval-data="evalData"
          :analysis-result="analysisResult"
          :analysis-loading="analysisLoading"
          @analyze="handleClassAnalysis"
        />
      </section>

      <div class="filter-bar">
        <el-input v-model="search" class="list-search filter-search" placeholder="搜索姓名 / 学号 / 学院" clearable @input="debouncedLoadStudents">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
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
        <el-empty :image-size="96">
          <template #image>
            <img :src="siteMascot" :alt="siteName" class="empty-mascot" />
          </template>
          <p class="empty-text">{{ hasActiveFilter ? '没有符合条件的学生' : '当前名下暂无学生' }}</p>
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
                <el-tab-pane label="工作记录" name="work">
                  <div class="tab-content">
                    <CareRecordPanel :student-id="detail.id" :student-name="detail.name" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="学情诊断" name="insight">
                  <div class="tab-content">
                    <StudentInsightPanel :student-id="detail.id" :student-name="detail.name" />
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
      <!-- 移动端页头：与桌面端同一套（页面标题 + 范围说明 + 更多操作） -->
      <header class="app-head">
        <div class="app-head-bar">
          <div class="app-head-lead">
            <h1 class="app-head-title">学生</h1>
            <p class="app-head-sub">名单 · 档案 · 数据分析</p>
          </div>
          <el-dropdown trigger="click" @command="onHeadCommand">
            <button class="app-icon-btn" type="button" aria-label="更多操作" title="更多操作">
              <el-icon :size="18"><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export"><el-icon><Download /></el-icon>导出学生数据</el-dropdown-item>
                <el-dropdown-item command="import"><el-icon><Upload /></el-icon>导入学生数据</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 概况便当格（Bento Grid）：模块化磁贴，每格只做一件事 -->
      <section class="bento">
        <div class="bento-tile bento-tile-lg">
          <span class="bento-label">在册学生</span>
          <span class="bento-value">{{ stats.total_students }}</span>
          <span class="bento-hint">成长档案 · 班级数据分析</span>
        </div>
        <div class="bento-tile">
          <span class="bento-label">高危学生</span>
          <span class="bento-value bento-value-warn">{{ stats.severe_alert_count }}</span>
        </div>
        <div class="bento-tile">
          <span class="bento-label">有成长成果</span>
          <span class="bento-value bento-value-ok">{{ growthCount }}</span>
        </div>
        <button class="bento-tile bento-tile-action" type="button" @click="showAnalyticsPage = true">
          <span class="bento-action-icon"><el-icon :size="18"><DataAnalysis /></el-icon></span>
          <span class="bento-action-main">
            <span class="bento-label">班级数据分析</span>
            <span class="bento-hint">成绩分布 · 心理危机 · 预警趋势</span>
          </span>
          <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
        </button>
      </section>

      <!-- 名单控制区：搜索 + 危机 chips + 筛选抽屉，紧贴所筛选的列表 -->
      <div class="ms-list-search">
        <el-input v-model="search" class="list-search" placeholder="搜索姓名 / 学号 / 学院" clearable @input="debouncedLoadStudents">
          <template #prefix><el-icon :size="16"><Search /></el-icon></template>
        </el-input>
      </div>

      <div class="ms-list-toolbar">
        <div class="ms-chip-scroll">
          <button
            v-for="c in crisisChips"
            :key="c.value"
            class="ms-chip"
            :class="{ active: filterCrisis === c.value }"
            @click="filterCrisis = c.value"
          >{{ c.label }}</button>
        </div>
        <span class="ms-filter-btn" @click="showFilterSheet = true">
          <el-icon :size="16"><Filter /></el-icon>
          <span>筛选</span>
        </span>
      </div>

      <div v-if="!filteredStudents.length && loaded" class="ms-empty">
        <img :src="siteMascot" :alt="siteName" class="ms-empty-mascot" />
        <span>{{ hasActiveFilter || isSearching ? '没有符合条件的学生' : '当前名下暂无学生' }}</span>
      </div>
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
            <el-tab-pane label="工作" name="work">
              <div class="mobile-tab-content">
                <CareRecordPanel :student-id="detail.id" :student-name="detail.name" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="诊断" name="insight">
              <div class="mobile-tab-content">
                <StudentInsightPanel :student-id="detail.id" :student-name="detail.name" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </transition>

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

    <!-- 移动端：班级数据分析子页（与学生相关的数据维度） -->
    <ClassAnalyticsMobile v-if="isMobile && showAnalyticsPage" :class-stats="classStats" :eval-data="evalData"
      @close="showAnalyticsPage = false" @open-analysis="openMascotAnalysis" />

    <!-- 桌宠弹窗：班级情况分析 -->
    <ClassAnalysisDialog v-model:visible="showAnalysisDialog" :analysis-result="analysisResult"
      :analysis-loading="analysisLoading" :analyze="runAnalysis" :load-profiles="loadStudentProfiles"
      :build-prompt="buildAnalysisPrompt" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Search, View, ChatDotRound, Close, ArrowLeft, ArrowRight,
  Filter, Download, Upload, DataAnalysis, MoreFilled,
} from '@element-plus/icons-vue'
import {
  getStudents, getStudentDetail, getDashboardStats, getClassEvaluation, getClassStats, importStudents,
  type StudentSummary, type StudentDetail, type DashboardStats, type ClassEvaluation, type ClassStats, type StudentImportItem,
} from '@/api/teacher'
import { getConversations, type ConversationOut } from '@/api/messages'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import CareRecordPanel from '@/components/teacher/care/CareRecordPanel.vue'
import StudentInsightPanel from '@/components/teacher/insight/StudentInsightPanel.vue'
import ClassAnalyticsPanel from '@/components/teacher/analytics/ClassAnalyticsPanel.vue'
import ClassAnalyticsMobile from '@/components/teacher/analytics/ClassAnalyticsMobile.vue'
import ClassAnalysisDialog from '@/components/teacher/analytics/ClassAnalysisDialog.vue'
import { useAiAnalysis } from '@/composables/useAiAnalysis'

defineOptions({ name: 'teacher-students' })

const { isMobile } = useResponsive()
const route = useRoute()
const router = useRouter()

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName } = useSiteConfig()

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

// ===== 统计 =====
const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})

// 有成长成果的学生数（学生维度概览，移动端统计卡使用）
const growthCount = computed(() => students.value.filter(s => (s.growth_count || 0) > 0).length)

// ===== 班级数据分析（与学生相关的数据维度，随本页承载） =====
const evalData = ref<ClassEvaluation>({
  total_students: 0, avg_gpa: 0, avg_score: 0,
  growth: {}, crisis: {}, pending_leaves: 0,
})
const classStats = ref<ClassStats>({
  total_students: 0,
  gender_stats: {}, crisis_stats: {}, grade_stats: {},
  political_stats: {}, hometown_stats: {}, crisis_trend: [],
})
const showAnalyticsPage = ref(false)

const { loading: analysisLoading, renderedResult: analysisResult, analyze: runAnalysis } = useAiAnalysis('teacher-class-analysis')

// 桌宠与弹窗状态
const showAnalysisDialog = ref(false)
const studentProfiles = ref<StudentSummary[]>([])

/** 拉取学生成长画像（供 AI 班级分析使用） */
async function loadStudentProfiles() {
  if (studentProfiles.value.length) return
  try {
    studentProfiles.value = await getStudents()
  } catch {
    studentProfiles.value = students.value // 拉取失败时退化为使用当前列表
  }
}

function buildAnalysisPrompt() {
  const cs = classStats.value
  const ev = evalData.value
  const g = ev.growth || {}
  const profiles = studentProfiles.value.length ? studentProfiles.value : students.value
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

  return `作为辅导员老师，请基于以下班级图表数据与学生成长数据，分析班级情况并提出建议：

班级图表数据：
- 学生总数：${cs.total_students}
- 性别比例：${JSON.stringify(cs.gender_stats)}
- 政治面貌：${JSON.stringify(cs.political_stats)}
- 生源地分布：${JSON.stringify(cs.hometown_stats)}
- 心理危机分布：高危${cs.crisis_stats?.severe || 0}人、中危${cs.crisis_stats?.moderate || 0}人、低危${cs.crisis_stats?.mild || 0}人、已解决${cs.crisis_stats?.resolved || 0}人
- 成绩分布：优秀${cs.grade_stats?.excellent || 0}人、良好${cs.grade_stats?.good || 0}人、中等${cs.grade_stats?.medium || 0}人、及格${cs.grade_stats?.pass || 0}人、不及格${cs.grade_stats?.fail || 0}人
- 危机预警趋势（近6个月）：${JSON.stringify(cs.crisis_trend)}

班级成长数据：
- 平均GPA：${ev.avg_gpa}，平均综合评分：${ev.avg_score}
- 成长记录统计：荣誉${g.honor || 0}条、竞赛${g.competition || 0}条、实践${g.practice || 0}条、论文${g.paper || 0}条、成果${g.achievement || 0}条
- 待审批请假：${ev.pending_leaves}人

学生成长明细：
${profileText}

请从以下方面进行分析：
1. 班级整体概况与综合能力画像
2. 学业成绩分析
3. 心理健康与危机预警分析
4. 学生成长发展分析（成长记录、技能、竞赛、实践等维度）
5. 辅导员工作建议（对需重点关注的个别学生点名提醒）

请用简洁专业的语言，控制在600字以内。`
}

async function loadAnalysisData() {
  try { evalData.value = await getClassEvaluation() } catch {}
  try { classStats.value = await getClassStats() } catch {}
}

/** 桌宠：打开分析弹窗（首次自动分析由子组件负责） */
function openMascotAnalysis() {
  showAnalysisDialog.value = true
}

async function handleClassAnalysis() {
  await loadStudentProfiles()
  await runAnalysis(buildAnalysisPrompt(), { skipCache: true })
}

// ===== 导入导出 =====
const importVisible = ref(false)
const importing = ref(false)
const importRows = ref<StudentImportItem[]>([])
const importSkipped = ref<string[]>([])

// ===== 最近互动时间（作为学生列表默认排序：最近沟通过的排前面） =====
const conversations = ref<ConversationOut[]>([])

const conversationTimeMap = computed(() => {
  const map = new Map<number, string>()
  conversations.value.forEach(c => {
    if (c.last_message_time) map.set(c.user_id, c.last_message_time)
  })
  return map
})

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
  const timeMap = conversationTimeMap.value
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
  }).sort((a, b) => {
    const ta = timeMap.get(a.id)
    const tb = timeMap.get(b.id)
    if (ta && tb) return tb.localeCompare(ta)
    if (ta) return -1
    if (tb) return 1
    return 0
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

// ===== 业务函数 =====
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

/** 页头「更多」菜单：导入 / 导出 */
function onHeadCommand(cmd: string) {
  if (cmd === 'export') handleExportStudents()
  else if (cmd === 'import') importVisible.value = true
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

onMounted(async () => {
  await loadStudents()
  loadDashboard()
  loadAnalysisData()
  // 从消息页等入口深链：?student=<id> 直接打开该学生详情
  const deepId = Number(route.query.student)
  if (deepId) {
    const target = students.value.find((s) => s.id === deepId)
    if (target) openDetail(target)
  }
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.students-page {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px 24px;
  background: #f6f7f9;
  /* 静默边框令牌：用 1px 发丝线取代阴影与重背景 */
  --sp-line: #ebedf0;
  --sp-line-strong: #e4e7ec;
}

/* ===== 概况便当格（Bento Grid）：模块化磁贴，每格只做一件事 ===== */
.bento {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.bento-tile {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--sp-line);
  border-radius: 12px;
  background: #fff;
}
.bento-tile-lg { grid-column: span 2; }
.bento-label { font-size: 12px; color: #71717a; }
.bento-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
  color: #101828;
  font-variant-numeric: tabular-nums;
}
.bento-value-warn { color: #d92d20; }
.bento-value-ok { color: #079455; }
.bento-hint { font-size: 11.5px; color: #a1a1aa; }
.bento-tile-action {
  grid-column: span 2;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  background: #f8fafc;
  border-color: #e6ecf6;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.bento-tile-action:hover { border-color: #cfdcf3; }
.bento-tile-action:active { background: #eff4ff; }
.bento-action-icon {
  width: 34px; height: 34px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 10px;
  background: #eff4ff;
  color: #2563eb;
}
.bento-action-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.bento-tile-action .bento-label { font-size: 13.5px; font-weight: 600; color: #101828; }
.bento-tile-action .bento-hint { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

@media (max-width: 767px) {
  .bento { margin: 12px 16px 14px; }
}

/* ===== 学生页头（极简应用栏：仅标题 + 更多操作） ===== */
.app-head {
  background: #fff;
  border-bottom: 1px solid #ebedf0;
  padding: 0 16px;
  margin-bottom: 14px;
}
.app-head-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0 12px;
}
.app-head-lead { min-width: 0; }
.app-head-title {
  margin: 0;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.3px;
  line-height: 1.2;
  color: #101828;
}
.app-head-sub {
  margin: 3px 0 0;
  font-size: 12.5px;
  color: #71717a;
}

.app-icon-btn {
  width: 36px; height: 36px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 999px;
  background: transparent; color: #4b5563;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.app-icon-btn:active { background: #f2f3f5; }
.app-icon-btn:hover { background: #f2f3f5; color: #2563eb; }

/* 搜索：白底 + 发丝边（与静默卡片同语言），聚焦时品牌描边 + 柔光环 */
.list-search :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 10px;
  padding: 0 12px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--sp-line) inset;
  transition: box-shadow 0.15s ease;
}
.list-search :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #d9dee7 inset; }
.list-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.list-search :deep(.el-input__inner) { height: 38px; font-size: 13.5px; color: #101828; }
.list-search :deep(.el-input__prefix),
.list-search :deep(.el-input__clear) { color: #9aa4b2; }
.filter-search { width: 240px; flex: none; }

/* 桌面端：应用栏收敛为带圆角的白色卡片 */
@media (min-width: 768px) {
  .app-head {
    border: 1px solid #ebedf0;
    border-radius: 12px;
    margin-bottom: 16px;
  }
}

.filter-bar {
  display: flex; gap: 8px; margin-bottom: 14px; padding: 10px 12px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--sp-line);
  flex-wrap: wrap; align-items: center;
}

/* 空态：吉祥物在此处出现，承担产品个性 */
.empty-mascot { width: 96px; height: 96px; object-fit: contain; opacity: 0.9; }
.empty-text { color: #98a2b3; font-size: 13px; margin: 8px 0 0; }

.analytics-section { margin-bottom: 14px; }
.analytics-section-head { display: flex; align-items: baseline; gap: 10px; padding: 0 4px 8px; }
.analytics-section-title { font-size: 15px; font-weight: 700; color: #101828; }
.analytics-section-sub { font-size: 12px; color: #98a2b3; }

.student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.student-card {
  background: #fff; border-radius: 12px; padding: 14px;
  border: 1px solid var(--sp-line);
  transition: border-color 0.15s ease; cursor: default;
}
.student-card:hover { border-color: #cfdcf3; }
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

/* 通用卡片（静默：1px 发丝边，无阴影） */
.ms-card {
  background: #fff; border-radius: 12px;
  border: 1px solid var(--sp-line);
  overflow: hidden;
}
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

.ms-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  text-align: center; color: #98a2b3; font-size: 13px; padding: 26px 0;
}
.ms-empty-mascot { width: 72px; height: 72px; object-fit: contain; opacity: 0.85; }

/* 名单区搜索：全宽单行，紧贴它所筛选的列表 */
.ms-list-search { margin: 0 16px 10px; }

/* ===== 移动端学生列表工具条 ===== */
.ms-list-toolbar { display: flex; align-items: center; gap: 10px; margin: 0 12px; }
.ms-list-toolbar .ms-chip-scroll { flex: 1; margin: 0; padding: 0 0 4px; }
.ms-list-toolbar .ms-filter-btn { margin-bottom: 4px; }

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