<template>
  <div class="students-page"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel">
    <!-- ============ 桌面端（保持原样） ============ -->
    <template v-if="!isMobile">
      <!-- 学生页头：品牌形象 + 页面标题 + 实时状态 + 更多操作 -->
      <header class="app-head">
        <div class="app-head-bar">
          <div class="app-head-lead">
            <span class="app-head-mark" aria-hidden="true">
              <img :src="siteMascot" :alt="siteName" />
            </span>
            <div class="app-head-text">
              <h1 class="app-head-title">工作台</h1>
              <p class="app-head-sub">
                <span class="app-head-live" :class="headAlert ? 'is-alert' : 'is-calm'">
                  <i class="app-head-live-dot" aria-hidden="true"></i>{{ headStatusText }}
                </span>
                <span class="app-head-divider" aria-hidden="true"></span>
                <span class="app-head-scope">我的事务 · 名单 · 数据分析</span>
              </p>
            </div>
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

      <!--
        概况条 + 名单，合并为「本页主功能区」。
        原来的布局问题：4 个便当格占掉半屏，只有 3 个数字，点开分析后
        才是真正的学生名单 —— 一屏之内看不到任何学生，而「学生」就是这个页面的全部意义。
        现在改成：一条紧凑指标条（只占一行高度），下面是名单。
        指标本身也从「纯数字」升级为「带权重提示」：高危/待批假是需要注意的，
        所以它们带语义色；「在册」「有成果」是中性信息，不抢视线。
      -->
      <section class="roster-panel">
        <div class="metric-strip">
          <div class="ms-item">
            <span class="ms-num">{{ stats.total_students }}</span>
            <span class="ms-label">在册学生</span>
          </div>
          <div class="ms-item" :class="{ 'is-alert': stats.severe_alert_count > 0 }">
            <span class="ms-num">{{ stats.severe_alert_count }}</span>
            <span class="ms-label">高危学生</span>
          </div>
          <div class="ms-item" :class="{ 'is-warn': stats.pending_leave_count > 0 }">
            <span class="ms-num">{{ stats.pending_leave_count }}</span>
            <span class="ms-label">待批请假</span>
          </div>
          <div class="ms-item">
            <span class="ms-num">{{ growthCount }}</span>
            <span class="ms-label">有成长成果</span>
          </div>
          <div class="ms-spacer"></div>
          <button class="ms-action" type="button" @click="showAnalyticsPage = true">
            <el-icon :size="15"><DataAnalysis /></el-icon>
            班级数据分析
          </button>
        </div>

        <!-- 筛选条：搜索独占一行（学生页最常用的动作），筛选器收拢在右侧 -->
        <div class="roster-toolbar">
          <el-input
            v-model="search"
            class="roster-search"
            placeholder="搜索姓名 / 学号 / 学院"
            clearable
            @input="debouncedLoadStudents"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <div class="roster-filters">
            <el-select v-model="filterCrisis" placeholder="危机等级" clearable class="rf-select">
              <el-option label="全部" value="" />
              <el-option label="高危" value="severe" />
              <el-option label="中度" value="moderate" />
              <el-option label="轻度" value="mild" />
              <el-option label="无预警" value="none" />
            </el-select>
            <el-select v-model="filterGrowth" placeholder="成长成果" clearable class="rf-select">
              <el-option label="全部" value="" />
              <el-option label="有成果" value="has" />
              <el-option label="无成果" value="none" />
            </el-select>
            <el-select v-model="filterScore" placeholder="综合评分" clearable class="rf-select">
              <el-option label="全部" value="" />
              <el-option label="突出 (≥80)" value="excellent" />
              <el-option label="良好 (≥65)" value="good" />
              <el-option label="一般 (≥50)" value="average" />
              <el-option label="偏低 (<50)" value="poor" />
            </el-select>
            <el-select v-model="filterSkill" placeholder="技能画像" clearable class="rf-select">
              <el-option label="全部" value="" />
              <el-option label="有技能" value="has" />
              <el-option label="无技能" value="none" />
            </el-select>
            <button v-if="hasActiveFilter" class="rf-clear" type="button" @click="clearFilters">
              <el-icon :size="12"><Close /></el-icon>
              清除
            </button>
          </div>
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
          <div
            v-for="s in pagedStudents"
            :key="s.id"
            :class="['student-card', s.crisis_level ? `level-${s.crisis_level}` : '']"
          >
            <div class="card-head">
              <el-avatar :size="40" :src="s.avatar || undefined" class="card-avatar">{{ s.name[0] }}</el-avatar>
              <div class="card-info">
                <strong class="card-name">{{ s.name }}</strong>
                <span class="card-college">{{ s.college || '未分配' }}</span>
              </div>
              <el-tag v-if="s.crisis_level" :type="crisisType(s.crisis_level)" size="small" effect="dark" class="crisis-tag">
                {{ crisisLabel(s.crisis_level) }}
              </el-tag>
            </div>

            <!--
              卡片主体改成一行「关键事实」，不再是三个等宽大数字。
              教师看名单时真正想知道的是：这人有没有事（预警）、有没有产出（成果）、
              有没有请假（请假），而不是三个并排的 0。
            -->
            <div class="card-facts">
              <span class="cf-item" :class="{ 'is-quiet': !s.growth_count }">
                <b>{{ s.growth_count }}</b> 成果
              </span>
              <span class="cf-sep" aria-hidden="true"></span>
              <span class="cf-item" :class="{ 'is-quiet': !s.leave_count }">
                <b>{{ s.leave_count }}</b> 请假
              </span>
              <span class="cf-sep" aria-hidden="true"></span>
              <span class="cf-item" :class="s.score !== undefined ? scoreClass(s.score) : 'is-quiet'">
                <b>{{ s.score ?? '—' }}</b> 综合分
              </span>
            </div>

            <div v-if="s.latest_crisis_summary" class="card-crisis-note">
              {{ s.latest_crisis_summary }}
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
      </section>

      <!--
        班级数据分析折叠区。
        不放首屏的理由：这是「看趋势、做汇报」才用的，日常最高频的动作是查某个学生。
        但也不能藏进二级页 —— 折叠标题里直接告诉它有什么，需要时一行就能展开。
      -->
      <section class="analytics-section is-collapsed">
        <button class="analytics-toggle" type="button" @click="analyticsOpen = !analyticsOpen">
          <span class="at-main">
            <span class="at-title">班级数据分析</span>
            <span class="at-sub">综合评估 / 成绩分布 / 心理危机 / 生源地等维度</span>
          </span>
          <el-icon :size="14" class="at-arrow" :class="{ 'is-open': analyticsOpen }">
            <ArrowRight />
          </el-icon>
        </button>
        <div v-if="analyticsOpen" class="analytics-body">
          <ClassAnalyticsPanel
            :class-stats="classStats"
            :eval-data="evalData"
            :analysis-result="analysisResult"
            :analysis-loading="analysisLoading"
            @analyze="handleClassAnalysis"
          />
        </div>
      </section>

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
                    <button type="button" class="loop-bar" @click="gotoFeature('/teacher/ai')">
                      <span class="loop-bar-text">智能提示 · 用能力画像推荐联系与资源</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
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
                    <button type="button" class="loop-bar" @click="gotoFeature('/teacher/guardian', { scene: 'care' })">
                      <span class="loop-bar-text">家校沟通 · 把成长成果反馈给家长</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
                    <el-timeline>
                      <el-timeline-item v-for="r in detail.growth_records" :key="r.id" :timestamp="r.date">
                        <el-tag size="small" :type="growthType(r.type)">{{ growthLabel(r.type) }}</el-tag>
                        <p style="margin:4px 0"><strong>{{ r.title }}</strong></p>
                        <p v-if="r.description" style="color:#666;font-size:13px">{{ r.description }}</p>
                        <el-link v-if="r.attachment_url" type="primary" :href="r.attachment_url" target="_blank" style="margin-top:4px;font-size:13px">查看附件</el-link>
                        <div style="margin-top:6px">
                          <el-button size="small" text type="primary" @click="feedbackGuardian(r.title)">反馈家长</el-button>
                        </div>
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-if="!detail.growth_records.length" description="暂无成长记录" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="危机预警" name="crisis">
                  <div class="tab-content">
                    <button type="button" class="loop-bar" @click="gotoCrisisCenter()">
                      <span class="loop-bar-text">预警中心 · 发现 → 干预 → 随访 → 闭环</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
                    <el-timeline v-if="sortedCrisis.length">
                      <el-timeline-item
                        v-for="a in sortedCrisis"
                        :key="a.id"
                        :timestamp="formatTime(a.created_at)"
                        :type="crisisType(a.level)"
                      >
                        <div class="dc-alert-head">
                          <el-tag :type="crisisType(a.level)" size="small" effect="dark">{{ crisisLabel(a.level) }}</el-tag>
                          <el-tag :type="a.resolved ? 'success' : 'warning'" size="small" effect="plain">
                            {{ a.resolved ? '已闭环' : '待处置' }}
                          </el-tag>
                        </div>
                        <p class="dc-alert-text">{{ a.summary }}</p>
                        <div v-if="a.resolved || a.intervention_type" class="crisis-loop">
                          <span class="crisis-loop-tag">{{ a.intervention_type || '已干预' }}</span>
                          <span class="crisis-loop-note">{{ a.intervention_note || '未填写备注' }}</span>
                          <span v-if="a.follow_up_date" class="crisis-loop-fu">随访 {{ a.follow_up_date }}</span>
                        </div>
                        <el-button v-else size="small" type="primary" plain round @click="gotoCrisisCenter(a)">
                          去预警中心处置
                        </el-button>
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-else description="暂无预警记录" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="项目展示" name="projects">
                  <div class="tab-content">
                    <button type="button" class="loop-bar" @click="gotoFeature('/teacher/guardian', { scene: 'care' })">
                      <span class="loop-bar-text">家校沟通 · 把项目成果反馈给家长</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
                    <el-timeline>
                      <el-timeline-item v-for="p in detail.projects" :key="p.id" :timestamp="`${p.start_date} ~ ${p.end_date || '至今'}`">
                        <p style="margin:4px 0"><strong>{{ p.project_name }}</strong></p>
                        <el-tag v-if="p.is_team" size="small" type="primary" round>团队</el-tag>
                        <el-tag v-else size="small" type="info" round>个人</el-tag>
                        <p v-if="p.is_team && p.team_members" style="color:#666;font-size:13px;margin-top:4px">成员：{{ p.team_members }}</p>
                        <div style="margin-top:6px">
                          <el-button size="small" text type="primary" @click="feedbackGuardian(p.project_name)">反馈家长</el-button>
                        </div>
                      </el-timeline-item>
                    </el-timeline>
                    <el-empty v-if="!detail.projects.length" description="暂无项目数据" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="请假记录" name="leave">
                  <div class="tab-content">
                    <button type="button" class="loop-bar" @click="gotoFeature('/teacher/approval')">
                      <span class="loop-bar-text">审批管理 · 受理与审批该生请假</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
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
                      <el-table-column label="操作" width="90">
                        <template #default="{ row }">
                          <el-button v-if="row.status === 'pending'" size="small" text type="primary" @click="gotoFeature('/teacher/approval')">去审批</el-button>
                          <span v-else style="color:#98a2b3;font-size:12px">已处理</span>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-empty v-if="!detail.leave_requests.length" description="无请假记录" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="工作记录" name="work">
                  <div class="tab-content">
                    <button type="button" class="loop-bar" @click="gotoFeature('/teacher/care-center', { view: 'profile' })">
                      <span class="loop-bar-text">关怀中心 · 关怀日历 / 家访台账 / 正向激励</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
                    <CareRecordPanel :student-id="detail.id" :student-name="detail.name" />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="学情诊断" name="insight">
                  <div class="tab-content">
                    <button type="button" class="loop-bar" @click="gotoFeature('/teacher/ai')">
                      <span class="loop-bar-text">智能提示 · 学情诊断与跟进建议</span>
                      <el-icon :size="14"><ArrowRight /></el-icon>
                    </button>
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
      <!-- 移动端页头：问候 + 日期 + 吉祥物（与首页同一套吸顶头部，由 HomeMobileBoard 渲染） -->

      <!-- ===== 首屏主导：原「首页」整块下沉到这里 =====
           教师端首页位置改为校园资讯后，原首页（问候 + 今日重点 + KPI + 常用功能 + 我的节奏）
           成为工作台页的首屏；下拉刷新手势由本页统一挂载，指示器交给看板组件渲染。 -->
      <HomeMobileBoard
        ref="boardRef"
        :pull-indicator-style="pullStyle"
        :pull-active="pull.active"
        @open-records="openRoster"
      />

      <!-- ===== 二级入口：学生名单 / 班级数据分析 =====
           名单既可从 KPI 卡进入，也在这里给一条显式入口，避免首屏只看到首页看板。 -->
      <section class="wb-entries">
        <button class="tui-card wb-entry wb-entry-slim" type="button" @click="openRoster">
          <span class="wb-entry-icon"><el-icon :size="18"><UserFilled /></el-icon></span>
          <span class="wb-entry-main">
            <span class="wb-entry-title">学生名单</span>
            <span class="wb-entry-hint">按危机等级分诊 · 搜索 / 排序 / 进入档案</span>
          </span>
          <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
        </button>
        <button class="tui-card wb-entry wb-entry-slim" type="button" @click="showAnalyticsPage = true">
          <span class="wb-entry-icon"><el-icon :size="18"><DataAnalysis /></el-icon></span>
          <span class="wb-entry-main">
            <span class="wb-entry-title">班级数据分析</span>
            <span class="wb-entry-hint">成绩分布 · 心理危机 · 预警趋势</span>
          </span>
          <el-icon color="#c0c4cc"><ArrowRight /></el-icon>
        </button>
      </section>

      <!-- ===== 二级子页：学生名单 ===== -->
      <transition name="subpage" :duration="320">
        <div v-if="rosterSubPage" class="wb-subpage">
          <div class="wb-subpage-head">
            <button class="wb-back" type="button" aria-label="返回工作台" @click="rosterSubPage = false">
              <el-icon :size="20"><ArrowLeft /></el-icon>
            </button>
            <span class="wb-subpage-title">学生名单</span>
            <span class="wb-subpage-count">{{ filteredStudents.length }} 人</span>
          </div>
          <div class="wb-subpage-body">
      <!-- 名单控制区：搜索 + 排序，紧贴所筛选的列表 -->
      <div class="ms-list-search">
        <el-input v-model="search" class="list-search" placeholder="搜索姓名 / 学号 / 学院" clearable @input="debouncedLoadStudents">
          <template #prefix><el-icon :size="16"><Search /></el-icon></template>
        </el-input>
        <el-dropdown trigger="click" placement="bottom-end" @command="onSortCommand">
          <button class="ms-icon-btn" type="button" aria-label="排序方式" :title="`排序：${sortLabel}`">
            <svg class="ms-sort-svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <path d="M7 4v15M4 16l3 3 3-3" />
              <path d="M14 7h7M14 12h5M14 17h3" />
            </svg>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="o in sortOptions" :key="o.value" :command="o.value">
                {{ o.label }}
                <el-icon v-if="sortMode === o.value" :size="14" class="ms-sort-check"><Check /></el-icon>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 危机等级：带计数的 chips，点之前就知道有几条 -->
      <div class="ms-chip-scroll">
        <button
          v-for="c in crisisChips"
          :key="c.value"
          class="ms-chip"
          :class="{ active: filterCrisis === c.value, 'is-risk': filterCrisis === c.value && c.value === 'severe' }"
          @click="filterCrisis = c.value"
        >{{ c.label }}<b>{{ crisisCounts[c.value] }}</b></button>
      </div>

      <div v-if="!filteredStudents.length && loaded" class="ms-empty">
        <img :src="siteMascot" :alt="siteName" class="ms-empty-mascot" />
        <span>{{ hasActiveFilter || isSearching ? '没有符合条件的学生' : '当前名下暂无学生' }}</span>
      </div>
      <!-- ============================================================
           分诊队列：不按危机等级单维分组，而是「今天必须处理 / 这周要跟进 / 状态平稳」。
           搜索时降级回原来的平铺名单（搜索要的是「找到那个人」，不是分档）。
           ============================================================ -->
      <template v-if="!isSearching">
        <div class="tm-page">
          <div
            v-for="g in triageGroups"
            :key="g.key"
            class="tm-tri"
            :style="{ '--tm-tri-c': g.color }"
          >
            <div class="tm-tri-hd" @click="toggleTri(g.key)">
              <span class="tm-tri-t">{{ g.title }}</span>
              <span class="tm-tri-n">{{ g.items.length }} 人</span>
              <span class="tm-tri-fold">{{ openTri.has(g.key) ? '收起' : '展开' }}</span>
            </div>
            <div v-if="openTri.has(g.key)" class="tm-tri-body">
              <div
                v-for="s in g.items"
                :key="s.id"
                class="tm-row tap"
                @click="openDetail(s)"
              >
                <div class="tm-r-ic" :style="triIconStyle(s)">{{ s.name[0] }}</div>
                <div class="tm-r-bd">
                  <div class="tm-r-t">
                    {{ s.name }}
                    <span v-if="s.crisis_level" class="tm-tag" :class="crisisTagCls(s.crisis_level)">{{
                      crisisLabel(s.crisis_level)
                    }}</span>
                  </div>
                  <div class="tm-r-s">
                    {{ s.college || '未分配' }}<template v-if="lastSeen(s)"> · {{ lastSeen(s) }}</template>
                  </div>
                </div>
                <div class="tm-r-e tm-r-num">
                  {{ s.growth_count ?? 0 }} 成果 · {{ s.leave_count ?? 0 }} 请假
                </div>
              </div>
              <div v-if="!g.items.length" class="tm-empty">这一档现在是空的</div>
            </div>
          </div>

          <div class="tm-tail">
            <b>分档依据：</b>危机等级（severe / moderate / mild）· 最近一次预警时间 ·
            请假与成果记录；分档规则应落到后端 triage_bucket，前端只读不判断
          </div>
        </div>
      </template>
      <template v-else>
        <div v-for="s in filteredStudents" :key="s.id" class="ms-row" :data-risk="s.crisis_level || 'calm'" @click="openDetail(s)">
          <el-avatar :size="40" :src="s.avatar || undefined" class="ms-row-avatar">{{ s.name[0] }}</el-avatar>
          <div class="ms-row-main">
            <div class="ms-row-name">
              <span class="ms-row-nm">{{ s.name }}</span>
              <span v-if="s.crisis_level" class="ms-tag" :class="`is-${s.crisis_level}`">{{ crisisLabel(s.crisis_level) }}</span>
            </div>
            <div class="ms-row-sub">
              <span class="ms-row-college">{{ s.college || '未分配' }}</span>
              <span v-if="lastSeen(s)" class="ms-row-time"><i class="ms-row-dot" aria-hidden="true">·</i>{{ lastSeen(s) }}</span>
            </div>
          </div>
          <div class="ms-row-metrics">
            <div class="ms-m">
              <b :class="{ 'is-zero': !s.growth_count }">{{ s.growth_count ?? 0 }}</b>
              <i>成果</i>
            </div>
            <span class="ms-m-sep" aria-hidden="true"></span>
            <div class="ms-m">
              <b :class="{ 'is-zero': !s.leave_count }">{{ s.leave_count ?? 0 }}</b>
              <i>请假</i>
            </div>
            <span class="ms-m-sep" aria-hidden="true"></span>
            <div class="ms-m">
              <b :class="s.score !== undefined ? scoreClass(s.score) : 'is-zero'">{{ s.score ?? '—' }}</b>
              <i>评分</i>
            </div>
          </div>
        </div>
            <div class="ms-list-foot">共 {{ filteredStudents.length }} 人 · 已显示全部</div>
          </template>
          </div>
        </div>
      </transition>
    </template>

    <!-- 移动端学生详情右滑页 -->
    <transition name="subpage" :duration="320">
      <div v-if="isMobile && detailVisible && detail" class="mobile-detail-page">
        <div class="mobile-detail-header">
          <el-button text circle @click="detailVisible = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="mobile-detail-title">{{ detail.name }} - 学生详情</span>
          <div style="width:36px"></div>
        </div>
        <div class="mobile-detail-body"
          @touchstart.passive="detailPull.onStart"
          @touchmove="detailPull.onMove"
          @touchend="detailPull.onEnd"
          @touchcancel="detailPull.onCancel">
          <PullRefreshIndicator :indicator-style="detailPull.indicatorStyle" :active="detailPull.active" />
          <!-- 方案A：档案头卡（渐变 + 身份风险标签 + 主页入口） -->
          <div class="mstu-hero">
            <div class="mstu-hero-r1">
              <el-avatar :size="52" :src="detail.avatar || undefined" class="mstu-hero-avatar">{{ detail.name[0] }}</el-avatar>
              <div class="mstu-hero-id">
                <div class="mstu-hero-name">{{ detail.name }}</div>
                <div class="mstu-hero-meta">{{ detail.college || '未分配' }} · {{ detail.username }}</div>
              </div>
              <button type="button" class="mstu-hero-home" @click="openStudentHome">
                <el-icon :size="13"><MagicStick /></el-icon>TA 的主页
              </button>
            </div>
            <div class="mstu-hero-tags">
              <span v-if="detailSummary?.crisis_level" class="is-risk">重点关注 · {{ crisisLevelLabel(detailSummary.crisis_level) }}</span>
              <span v-if="detailSummary?.score !== undefined">综合评分 {{ detailSummary.score }}</span>
              <span>成长成果 {{ detail.growth_records.length }}</span>
              <span>请假 {{ detail.leave_requests.length }}</span>
            </div>
          </div>
          <!-- KPI 四格 -->
          <div class="mstu-kpi">
            <div class="k"><b>{{ detail.growth_records.length }}</b><i>成长成果</i></div>
            <div class="k"><b>{{ detail.projects.length }}</b><i>项目</i></div>
            <div class="k"><b :class="pendingCrisisCount ? 'is-bad' : ''">{{ pendingCrisisCount }}</b><i>待处理预警</i></div>
            <div class="k"><b>{{ detailSummary?.score ?? '—' }}</b><i>综合评分</i></div>
          </div>
          <!-- 风险卡置顶（SLA 响应时效） -->
          <div v-if="topCrisis" class="mstu-risk">
            <div class="mstu-risk-head">
              <el-icon :size="15" class="mstu-risk-ic"><WarningFilled /></el-icon>
              <span class="mstu-risk-title">{{ crisisLabel(topCrisis.level) }}预警 · 待处理</span>
              <time class="mstu-risk-time">{{ formatTime(topCrisis.created_at) }}</time>
            </div>
            <p class="mstu-risk-desc">{{ topCrisis.summary }}</p>
            <div class="mstu-risk-foot">
              <div class="mstu-sla">
                <div class="lb"><span>响应时效</span><b>{{ slaLabel(topCrisis.created_at) }}</b></div>
                <div class="bar"><i :style="{ width: slaPct(topCrisis.created_at) + '%' }" /></div>
              </div>
              <button type="button" class="mstu-risk-btn" @click="gotoCrisisCenter(topCrisis)">去处置</button>
            </div>
          </div>
          <div class="mobile-tabbar" role="tablist" aria-label="学生详情分区">
            <button
              v-for="t in detailTabs"
              :key="t.name"
              type="button"
              role="tab"
              class="mobile-tab-chip"
              :class="{ 'is-active': detailTab === t.name }"
              :aria-selected="detailTab === t.name"
              @click="detailTab = t.name"
            >{{ t.label }}</button>
          </div>
          <el-tabs v-model="detailTab" class="mobile-tabs">
            <el-tab-pane label="技能" name="skills">
              <div class="mobile-tab-content">
                <button type="button" class="loop-bar" @click="gotoFeature('/teacher/ai')">
                  <span class="loop-bar-text">智能提示 · 用能力画像推荐联系与资源</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
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
                <button type="button" class="loop-bar" @click="gotoFeature('/teacher/guardian', { scene: 'care' })">
                  <span class="loop-bar-text">家校沟通 · 把成长成果反馈给家长</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
                <div v-for="r in detail.growth_records" :key="r.id" class="mobile-record-card">
                  <div class="mobile-record-top">
                    <el-tag size="small" :type="growthType(r.type)">{{ growthLabel(r.type) }}</el-tag>
                    <small>{{ r.date }}</small>
                  </div>
                  <div class="mobile-record-title">{{ r.title }}</div>
                  <div v-if="r.description" class="mobile-record-desc">{{ r.description }}</div>
                  <button type="button" class="record-op" @click="feedbackGuardian(r.title)">
                    反馈家长<el-icon :size="12"><ArrowRight /></el-icon>
                  </button>
                </div>
                <el-empty v-if="!detail.growth_records?.length" description="暂无记录" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="预警" name="crisis">
              <div class="mobile-tab-content">
                <button type="button" class="loop-bar" @click="gotoCrisisCenter()">
                  <span class="loop-bar-text">预警中心 · 发现 → 干预 → 随访 → 闭环</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
                <div v-if="sortedCrisis.length" class="crisis-list">
                  <div v-if="pendingCrisisCount" class="crisis-summary">
                    <span class="crisis-summary-total">待处理 {{ pendingCrisisCount }} 条</span>
                    <span
                      v-for="s in crisisSummary.filter((x) => x.count)"
                      :key="s.level"
                      class="crisis-summary-item"
                    >
                      <i class="crisis-dot" :class="`is-${s.level}`"></i>{{ s.label }} {{ s.count }}
                    </span>
                  </div>
                  <article
                    v-for="a in sortedCrisis"
                    :key="a.id"
                    class="crisis-card"
                    :class="[`is-${a.level}`, { 'is-resolved': a.resolved }]"
                  >
                    <div class="crisis-card-head">
                      <span class="crisis-level" :class="`is-${a.level}`">{{ crisisLabel(a.level) }}</span>
                      <span class="crisis-state" :class="{ 'is-done': a.resolved }">
                        {{ a.resolved ? '已处理' : '待处理' }}
                      </span>
                      <time class="crisis-time">{{ formatTime(a.created_at) }}</time>
                    </div>
                    <p class="crisis-text">{{ a.summary }}</p>
                    <div v-if="a.keywords.length" class="crisis-keywords">
                      <span v-for="k in a.keywords" :key="k" class="crisis-keyword">{{ k }}</span>
                    </div>

                    <!-- 闭环回流：预警中心的处置结果在学生详情同步可见 -->
                    <div v-if="a.resolved || a.intervention_type" class="crisis-loop">
                      <span class="crisis-loop-tag">{{ a.intervention_type || '已干预' }}</span>
                      <span class="crisis-loop-note">{{ a.intervention_note || '未填写备注' }}</span>
                      <span v-if="a.follow_up_date" class="crisis-loop-fu">随访 {{ a.follow_up_date }}</span>
                    </div>
                    <!-- 未闭环：带着学生与预警跳到预警中心处置 -->
                    <button v-else type="button" class="crisis-op" @click="gotoCrisisCenter(a)">
                      去预警中心处置
                      <el-icon :size="13"><ArrowRight /></el-icon>
                    </button>
                  </article>
                </div>
                <el-empty v-else description="暂无预警" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="项目" name="projects">
              <div class="mobile-tab-content">
                <button type="button" class="loop-bar" @click="gotoFeature('/teacher/guardian', { scene: 'care' })">
                  <span class="loop-bar-text">家校沟通 · 把项目成果反馈给家长</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
                <div v-for="p in detail.projects" :key="p.id" class="mobile-record-card">
                  <div class="mobile-record-top">
                    <el-tag v-if="p.is_team" size="small" type="primary" round>团队</el-tag>
                    <el-tag v-else size="small" type="info" round>个人</el-tag>
                    <small>{{ p.start_date }} ~ {{ p.end_date || '至今' }}</small>
                  </div>
                  <div class="mobile-record-title">{{ p.project_name }}</div>
                  <div v-if="p.team_members" class="mobile-record-desc">成员：{{ p.team_members }}</div>
                  <button type="button" class="record-op" @click="feedbackGuardian(p.project_name)">
                    反馈家长<el-icon :size="12"><ArrowRight /></el-icon>
                  </button>
                </div>
                <el-empty v-if="!detail.projects?.length" description="暂无项目" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="请假" name="leave">
              <div class="mobile-tab-content">
                <button type="button" class="loop-bar" @click="gotoFeature('/teacher/approval')">
                  <span class="loop-bar-text">审批管理 · 受理与审批该生请假</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
                <div v-for="l in detail.leave_requests" :key="l.id" class="mobile-record-card">
                  <div class="mobile-record-top">
                    <el-tag size="small" :type="l.status === 'approved' ? 'success' : l.status === 'rejected' ? 'danger' : 'warning'">
                      {{ l.status === 'approved' ? '通过' : l.status === 'rejected' ? '拒绝' : '待批' }}
                    </el-tag>
                    <small>{{ l.start_date }} ~ {{ l.end_date }}</small>
                  </div>
                  <div class="mobile-record-title">{{ leaveTypeLabel(l.leave_type) }}</div>
                  <div class="mobile-record-desc">{{ l.reason }}</div>
                  <button v-if="l.status === 'pending'" type="button" class="record-op" @click="gotoFeature('/teacher/approval')">
                    去审批<el-icon :size="12"><ArrowRight /></el-icon>
                  </button>
                </div>
                <el-empty v-if="!detail.leave_requests?.length" description="无请假记录" :image-size="48" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="工作" name="work">
              <div class="mobile-tab-content">
                <button type="button" class="loop-bar" @click="gotoFeature('/teacher/care-center', { view: 'profile' })">
                  <span class="loop-bar-text">关怀中心 · 关怀日历 / 家访台账 / 正向激励</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
                <CareRecordPanel :student-id="detail.id" :student-name="detail.name" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="诊断" name="insight">
              <div class="mobile-tab-content">
                <button type="button" class="loop-bar" @click="gotoFeature('/teacher/ai')">
                  <span class="loop-bar-text">智能提示 · 学情诊断与跟进建议</span>
                  <el-icon :size="14"><ArrowRight /></el-icon>
                </button>
                <StudentInsightPanel :student-id="detail.id" :student-name="detail.name" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </transition>

    <!-- QQ 风格学生主页（教师查看学生的「个人空间」） -->
    <transition name="slide-right-in">
      <div v-if="homeVisible && detail" class="qhome">
        <header class="qhome-bar">
          <el-button text circle @click="homeVisible = false"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
          <span class="qhome-bar-title">{{ detail.name }}的主页</span>
          <el-button text circle @click="ElMessage({ message: '更多操作（演示）', type: 'info' })"><el-icon :size="18"><MoreFilled /></el-icon></el-button>
        </header>

        <div class="qhome-body">
          <!-- 封面 -->
          <div class="qhome-cover">
            <div class="qhome-cover-actions">
              <button type="button" @click="detailSummary && openContact(detailSummary)">打声招呼</button>
              <button type="button" @click="ElMessage({ message: '更换封面（演示）', type: 'info' })">更换封面</button>
            </div>
          </div>

          <!-- 头像 + 身份 -->
          <div class="qhome-head">
            <el-avatar :size="72" :src="detail.avatar || undefined" class="qhome-avatar">{{ detail.name[0] }}</el-avatar>
            <div class="qhome-name-row">
              <span class="qhome-name">{{ detail.name }}</span>
              <span class="qhome-lv">LV.{{ homeLevel }}</span>
            </div>
            <div class="qhome-qid">学号：<b>{{ detail.username }}</b> · {{ detail.college || '未分配' }}</div>
            <p class="qhome-sig">{{ homeMotto }}</p>
          </div>

          <!-- 数据带 -->
          <div class="qhome-stats">
            <div class="s"><b>{{ detail.growth_records.length }}</b><i>成果</i></div>
            <div class="s"><b>{{ detail.projects.length }}</b><i>项目</i></div>
            <div class="s"><b>{{ detailSummary?.score ?? '—' }}</b><i>评分</i></div>
            <div class="s"><b>{{ detail.leave_requests.length }}</b><i>请假</i></div>
          </div>

          <!-- 徽章墙 -->
          <template v-if="homeBadges.length">
            <div class="qhome-sec">徽章墙</div>
            <div class="qhome-badges tui-scroll-hidden">
              <div v-for="b in homeBadges" :key="b.name" class="qhome-badge">
                <span class="qhome-badge-ic" :class="`tone-${b.tone}`"><el-icon :size="16"><MagicStick /></el-icon></span>
                <span>{{ b.name }}</span>
              </div>
            </div>
          </template>

          <!-- 相册 -->
          <template v-if="detail.projects.length">
            <div class="qhome-sec">项目相册<span class="spacer">{{ detail.projects.length }} 个</span></div>
            <div class="qhome-photos">
              <div v-for="(p, i) in detail.projects.slice(0, 5)" :key="p.id" class="qhome-photo"
                :style="{ background: PHOTO_TONES[i % PHOTO_TONES.length] }">
                <el-icon :size="18"><Picture /></el-icon>
              </div>
              <button v-if="detail.projects.length > 5" type="button" class="qhome-photo more"
                @click="ElMessage({ message: '完整相册（演示）', type: 'info' })">
                <el-icon :size="16"><Picture /></el-icon>{{ detail.projects.length }} 张
              </button>
            </div>
          </template>

          <!-- 动态流（成长记录） -->
          <div class="qhome-sec">TA 的动态</div>
          <template v-if="homePosts.length">
            <article v-for="(po, i) in homePosts" :key="po.id" class="qhome-post">
              <div class="qhome-post-head">
                <el-avatar :size="36" :src="detail.avatar || undefined">{{ detail.name[0] }}</el-avatar>
                <div>
                  <div class="qhome-post-name">{{ detail.name }}</div>
                  <div class="qhome-post-time">{{ po.date }} · {{ growthLabel(po.type) }}</div>
                </div>
              </div>
              <div class="qhome-post-text">{{ po.title }}</div>
              <p v-if="po.description" class="qhome-post-desc">{{ po.description }}</p>
              <div v-if="i % 3 !== 2" class="qhome-post-imgs" :class="i % 3 === 0 ? 'g1' : 'g2'">
                <div v-for="n in (i % 3 === 0 ? 1 : 2)" :key="n" class="qhome-pimg"
                  :style="{ background: PHOTO_TONES[(i + n) % PHOTO_TONES.length] }">
                  <el-icon :size="15"><Picture /></el-icon>成长瞬间
                </div>
              </div>
              <div class="qhome-post-ops">
                <button type="button" class="qhome-op" :class="{ liked: likedPosts[po.id] }" @click="toggleLike(po)">
                  <svg class="qhome-like" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg>{{ likedPosts[po.id] ? '已赞' : '点赞' }} {{ po.likeN + (likedPosts[po.id] ? 1 : 0) }}
                </button>
                <button type="button" class="qhome-op" @click="ElMessage({ message: '评论（演示）', type: 'info' })">
                  <el-icon :size="15"><ChatLineRound /></el-icon>评论 {{ po.cmtN }}
                </button>
                <button type="button" class="qhome-op" @click="ElMessage({ message: '已收藏该动态（演示）', type: 'success' })">
                  <el-icon :size="15"><Star /></el-icon>收藏
                </button>
              </div>
            </article>
          </template>
          <el-empty v-else description="TA 还没有发布动态" :image-size="56" />
        </div>
      </div>
    </transition>
    <!-- 导入学生数据（上传+预览：移动端=全屏子页） -->
    <ResponsivePopup v-model="importVisible" title="导入学生数据" width="560px" class="ms-dialog">
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
    </ResponsivePopup>

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
import { ref, computed, watch, onMounted, onActivated, onUnmounted } from 'vue'
// v6.1 弹窗减负：导入流程走全屏子页承接
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Search, View, ChatDotRound, Close, ArrowLeft, ArrowRight,
  Download, Upload, DataAnalysis, MoreFilled,
  MagicStick, WarningFilled, ChatLineRound, Star, Picture,
  UserFilled, Check,
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
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import HomeMobileBoard from './HomeMobileBoard.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'

defineOptions({ name: 'teacher-students' })

const { isMobile } = useResponsive()
const route = useRoute()
const router = useRouter()

// 移动端下拉刷新：主列表与统计、学生详情各自一个手势实例（桌面端不响应）
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })
const detailPull = usePullRefresh(refreshDetail, { enabled: () => isMobile.value })

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName } = useSiteConfig()

const search = ref('')
const students = ref<(StudentSummary & { score?: number })[]>([])
const loaded = ref(false)
const detailVisible = ref(false)
const detail = ref<StudentDetail | null>(null)
/** 打开详情时的列表摘要（含 score / crisis_level，详情接口不返回这两个字段） */
const detailSummary = ref<StudentSummary | null>(null)
const detailTab = ref('skills')
/** 移动端详情分区：横向滚动胶囊标签，替代拥挤的下划线 tabs */
const detailTabs = [
  { name: 'skills', label: '技能' },
  { name: 'growth', label: '成长' },
  { name: 'crisis', label: '预警' },
  { name: 'projects', label: '项目' },
  { name: 'leave', label: '请假' },
  { name: 'work', label: '工作' },
  { name: 'insight', label: '诊断' },
]

/** 预警等级优先级：数字越小越紧急 */
const CRISIS_RANK: Record<string, number> = { severe: 0, moderate: 1, mild: 2, normal: 3 }

function keywordList(raw?: string | null): string[] {
  if (!raw) return []
  return raw.split(/[,，、;；\s]+/).filter(Boolean).slice(0, 6)
}

/** 预警按「待处理优先 → 等级高→低 → 时间新→旧」排序，最高优先级置顶 */
const sortedCrisis = computed(() =>
  [...((detail.value?.crisis_alerts || []) as any[])]
    .sort((a, b) => {
      const ra = a.resolved ? 1 : 0
      const rb = b.resolved ? 1 : 0
      if (ra !== rb) return ra - rb
      const la = CRISIS_RANK[a.level] ?? 9
      const lb = CRISIS_RANK[b.level] ?? 9
      if (la !== lb) return la - lb
      return String(b.created_at || '').localeCompare(String(a.created_at || ''))
    })
    .map((a) => ({ ...a, keywords: keywordList(a.keywords_matched) }))
)

const pendingCrisisCount = computed(
  () => ((detail.value?.crisis_alerts || []) as any[]).filter((a) => !a.resolved).length
)

/** 待处理预警的等级分布，用于顶部优先级概览 */
const crisisSummary = computed(() => {
  const pending = ((detail.value?.crisis_alerts || []) as any[]).filter((a) => !a.resolved)
  return [
    { level: 'severe', label: '高危', count: pending.filter((a) => a.level === 'severe').length },
    { level: 'moderate', label: '中度', count: pending.filter((a) => a.level === 'moderate').length },
    { level: 'mild', label: '轻度', count: pending.filter((a) => a.level === 'mild').length },
  ]
})

const filterCrisis = ref('')
const filterGrowth = ref('')
const filterScore = ref('')
const filterSkill = ref('')

const currentPage = ref(1)
const pageSize = ref(12)

// ===== 统计 =====
const stats = ref<DashboardStats>({
  total_students: 0, alert_count: 0, pending_leave_count: 0,
  severe_alert_count: 0, resolved_alert_count: 0,
})

// 有成长成果的学生数（学生维度概览，移动端统计卡使用）
const growthCount = computed(() => students.value.filter(s => (s.growth_count || 0) > 0).length)

// ===== 页头实时状态：把静态说明换成随数据变化的一句话 =====
const headAlert = computed(() => stats.value.severe_alert_count > 0)
const headStatusText = computed(() =>
  headAlert.value ? `${stats.value.severe_alert_count} 人高危待关注` : '暂无高危预警',
)

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
/** 桌面端「班级数据分析」折叠状态：默认收起，让名单占首屏 */
const analyticsOpen = ref(false)

// ===== 移动端二级子页：学生名单（B 版式：首屏主导，名单下沉为子页） =====
const rosterSubPage = ref(false)
/** 首屏看板实例：下拉刷新时一并带上看板数据（看板自己不挂手势，手势在本页根容器） */
const boardRef = ref<InstanceType<typeof HomeMobileBoard> | null>(null)
/** 下拉指示器位移：类型从 CSSProperties 转成组件接受的 Record<string, string> */
const pullStyle = computed<Record<string, string>>(() => ({ ...(pull.indicatorStyle as Record<string, string>) }))

/**
 * 打开名单子页：从首屏看板的「我的学生」KPI、工作量卡、名单摘要卡进来都走这里。
 * 进子页时清掉筛选，避免上次的高危筛选让教师以为「名单只剩这几个人」。
 */
function openRoster() {
  filterCrisis.value = ''
  search.value = ''
  rosterSubPage.value = true
}

// 移动端页内二级页面（学生详情 / 班级分析 / 名单子页）：打开时让出底部悬浮导航
useMobileSubPage(computed(() => isMobile.value && (detailVisible.value || showAnalyticsPage.value || rosterSubPage.value)))

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

/**
 * 最近互动时间：把 ISO 时间压成「今天 / 昨天 / 3天前 / 2周前」。
 * 名单里只用来做一次轻量提示，没有互动记录时返回空串，副标题就只剩学院。
 */
function lastSeen(s: StudentSummary) {
  const iso = conversationTimeMap.value.get(s.id)
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const day = 86400000
  const diff = Date.now() - t
  if (diff < day) return '今天'
  if (diff < day * 2) return '昨天'
  if (diff < day * 7) return `${Math.floor(diff / day)}天前`
  if (diff < day * 30) return `${Math.floor(diff / (day * 7))}周前`
  if (diff < day * 365) return `${Math.floor(diff / (day * 30))}个月前`
  return `${Math.floor(diff / (day * 365))}年前`
}

// ===== 筛选 chips =====
const crisisChips = [
  { label: '全部', value: '' },
  { label: '高危', value: 'severe' },
  { label: '中度', value: 'moderate' },
  { label: '轻度', value: 'mild' },
  { label: '无预警', value: 'none' },
]

const hasActiveFilter = computed(() => {
  return filterCrisis.value || filterGrowth.value || filterScore.value || filterSkill.value
})

const isSearching = computed(() => search.value.trim() !== '')

/**
 * 危机等级之外的筛选（成长 / 评分 / 技能）。
 * 单独抽出来是因为 chips 上的计数要按「除危机等级以外」的口径统计：
 * 否则选中「高危」时其余 chips 会跟着变成 0，用户无法在档位之间横向切换。
 */
const preStudents = computed(() => {
  return students.value.filter(s => {
    if (filterGrowth.value) {
      if (filterGrowth.value === 'has' && (!s.growth_count || s.growth_count === 0)) return false
      if (filterGrowth.value === 'none' && s.growth_count && s.growth_count > 0) return false
    }

    if (filterScore.value && s.score !== undefined) {
      // 与 scoreClass() 的四档保持完全一致，否则「筛选出的」和「标红的」会打架
      if (filterScore.value === 'excellent' && s.score < 80) return false
      if (filterScore.value === 'good' && (s.score < 65 || s.score >= 80)) return false
      if (filterScore.value === 'average' && (s.score < 50 || s.score >= 65)) return false
      if (filterScore.value === 'poor' && s.score >= 50) return false
    }

    if (filterSkill.value) {
      const hasSkills = s.skills_json?.skills?.length && s.skills_json.skills.length > 0
      if (filterSkill.value === 'has' && !hasSkills) return false
      if (filterSkill.value === 'none' && hasSkills) return false
    }

    return true
  })
})

/** chips 计数：键与 crisisChips 的 value 一一对应，'' 为全部 */
const crisisCounts = computed(() => {
  const list = preStudents.value
  const byLevel = (level: string) => list.filter(s => s.crisis_level === level).length
  return {
    '': list.length,
    severe: byLevel('severe'),
    moderate: byLevel('moderate'),
    mild: byLevel('mild'),
    none: list.filter(s => !s.crisis_level).length,
  } as Record<string, number>
})

// ===== 排序（移动端搜索框右侧的排序入口） =====
const sortMode = ref<'recent' | 'risk' | 'score' | 'name'>('recent')
const sortOptions = [
  { label: '最近互动', value: 'recent' },
  { label: '风险优先', value: 'risk' },
  { label: '评分从高到低', value: 'score' },
  { label: '按姓名', value: 'name' },
]
const sortLabel = computed(() => sortOptions.find(o => o.value === sortMode.value)?.label || '')
function onSortCommand(cmd: string | number | object) {
  sortMode.value = cmd as typeof sortMode.value
}
const RISK_ORDER: Record<string, number> = { severe: 3, moderate: 2, mild: 1 }

const filteredStudents = computed(() => {
  const timeMap = conversationTimeMap.value
  return preStudents.value.filter(s => {
    if (filterCrisis.value) {
      if (filterCrisis.value === 'none') {
        if (s.crisis_level) return false
      } else {
        if (s.crisis_level !== filterCrisis.value) return false
      }
    }
    return true
  }).sort((a, b) => {
    if (sortMode.value === 'risk') {
      const diff = (RISK_ORDER[b.crisis_level || ''] || 0) - (RISK_ORDER[a.crisis_level || ''] || 0)
      if (diff) return diff
    } else if (sortMode.value === 'score') {
      return (b.score ?? -1) - (a.score ?? -1)
    } else if (sortMode.value === 'name') {
      return a.name.localeCompare(b.name, 'zh-Hans-CN')
    }
    // 默认（以及风险/评分相同时）按最近互动倒序：最近沟通过的排前面
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

/** 下拉刷新：静默重载学生名单与统计，失败不提示 */
async function refreshAll() {
  await Promise.all([
    loadStudents(),
    loadDashboard(),
    // 首屏看板（原首页那块）的数据也要跟着一起刷新
    boardRef.value?.refresh?.().catch(() => {}),
  ])
}

/** 学生详情下拉刷新：重拉当前详情，失败保持原样 */
async function refreshDetail() {
  if (!detail.value) return
  try {
    detail.value = await getStudentDetail(detail.value.id)
  } catch { /* ignore */ }
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
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度', normal: '正常' }
  return map[level] || level
}

/* ── 移动端分诊队列 ──
   分档只读真实字段：crisis_level 为主，latest_crisis_time 只用来算「多久没更新」。
   注意：后端目前没有 triage_bucket，这里是前端临时推导；等后端落字段后改成只读。 */
const openTri = ref<Set<string>>(new Set())
function toggleTri(key: string) {
  const next = new Set(openTri.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  openTri.value = next
}
const triToday = computed(() => filteredStudents.value.filter((s) => s.crisis_level === 'severe'))
const triWeek = computed(() => filteredStudents.value.filter((s) => s.crisis_level === 'moderate'))
const triCalm = computed(() =>
  filteredStudents.value.filter((s) => s.crisis_level !== 'severe' && s.crisis_level !== 'moderate')
)
const triageGroups = computed(() => [
  { key: 'today', title: '必须今天处理', color: '#dd4257', items: triToday.value },
  { key: 'week', title: '这周要跟进', color: '#d98317', items: triWeek.value },
  { key: 'calm', title: '状态平稳', color: '#0f8e6b', items: triCalm.value },
])
// 默认不写死档位：数据到位后自动展开「第一个有人的档」，
// 避免出现「空档摊开、有人的那档反而收起」的情况。
watch(triageGroups, (gs) => {
  const nonEmpty = gs.filter((g) => g.items.length)
  if (!nonEmpty.length) return // 数据还没来，保持全收起
  if (nonEmpty.some((g) => openTri.value.has(g.key))) return // 已有非空的档展开，不打断用户
  openTri.value = new Set([nonEmpty[0].key])
})
function crisisTagCls(level?: string | null) {
  if (level === 'severe') return 'tm-bad'
  if (level === 'moderate') return 'tm-warn'
  if (level === 'mild') return 'tm-ai'
  return 'tm-mute'
}
function triIconStyle(s: StudentSummary) {
  if (s.crisis_level === 'severe') return { background: 'var(--tm-bad-soft)', color: 'var(--tm-bad)' }
  if (s.crisis_level === 'moderate') return { background: 'var(--tm-warn-soft)', color: 'var(--tm-warn)' }
  return { background: 'var(--tm-brand-soft)', color: 'var(--tm-brand-deep)' }
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

/**
 * 成长综合分档位（0–100）。
 *
 * 这里的阈值必须对齐分数的**实际分布**，不能拍「90 分优秀」这种考试口径。
 * 后端 calc_radar_score 是「成果数 × 系数」累加后取五维均值（见 services/scoring.py），
 * 实测全校学生的分布是 42–88、中位数 ~70 —— 按 ≥90 划分的话，
 * 满屏都是「不及格红」，会把正常学生标成需要干预。
 * 现在的四档：≥80 突出 / ≥65 良好 / ≥50 一般 / <50 偏低，与真实分布同构。
 */
function scoreClass(score: number) {
  if (score >= 80) return 'score-excellent'
  if (score >= 65) return 'score-good'
  if (score >= 50) return 'score-average'
  return 'score-poor'
}

async function openDetail(s: StudentSummary) {
  try {
    detailSummary.value = s
    detail.value = await getStudentDetail(s.id)
    detailVisible.value = true
    detailTab.value = 'skills'
  } catch {}
}

/** 置顶风险卡：最高优先级的未处理预警 */
const topCrisis = computed(() => {
  const first = sortedCrisis.value.find((a) => !a.resolved)
  return first || null
})

/** SLA 响应时效：以 48 小时为响应窗口，展示已流逝时间与进度 */
const SLA_WINDOW_H = 48
function slaHours(iso: string): number {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return 0
  return Math.max(0, (Date.now() - t) / 3600000)
}
function slaLabel(iso: string): string {
  const h = slaHours(iso)
  if (h < 1) return '刚刚产生'
  if (h < 24) return `已等待 ${Math.floor(h)} 小时`
  return `已等待 ${Math.floor(h / 24)} 天 ${Math.floor(h % 24)} 小时`
}
function slaPct(iso: string): number {
  return Math.min(100, Math.round((slaHours(iso) / SLA_WINDOW_H) * 100))
}

/* ================= QQ 风格学生主页 ================= */
const homeVisible = ref(false)
const likedPosts = ref<Record<number, boolean>>({})
const PHOTO_TONES = ['#85b7eb', '#5dcaa5', '#a78bfa', '#f0997b', '#ed93b1']

function openStudentHome() {
  homeVisible.value = true
}

/** 等级：按成长成果数折算，纯展示用 */
const homeLevel = computed(() => 3 + ((detail.value?.growth_records.length || 0) % 5))

/** 个性格言：优先兴趣标签，其次最近一条成长记录，兜底默认 */
const homeMotto = computed(() => {
  const d = detail.value
  if (!d) return ''
  const interests = d.skills_json?.interests
  if (interests?.length) return `兴趣：${interests.slice(0, 3).join(' · ')}`
  return d.growth_records?.[0]?.title || '这个人很懒，什么都没有留下。'
})

/** 徽章墙：技能名取前 6 个 */
const homeBadges = computed(() => {
  const skills = detail.value?.skills_json?.skills || []
  const tones = ['brand', 'success', 'violet', 'warn', 'cyan', 'danger']
  return skills.slice(0, 6).map((sk: { name: string }, i: number) => ({
    name: sk.name,
    tone: tones[i % tones.length],
  }))
})

/** 动态流：成长记录转动态，点赞数为演示用确定性假数据 */
const homePosts = computed(() =>
  (detail.value?.growth_records || []).map((r: any, i: number) => ({
    ...r,
    likeN: (r.id * 7 + i * 3) % 18,
    cmtN: (r.id + i) % 5,
  }))
)

function toggleLike(post: { id: number }) {
  likedPosts.value[post.id] = !likedPosts.value[post.id]
  ElMessage({ message: likedPosts.value[post.id] ? '已点赞，学生端会收到提醒' : '已取消点赞', type: 'success' })
}

function openContact(s: StudentSummary) {
  router.push({ path: '/teacher/messages', query: { studentId: String(s.id), studentName: s.name } })
}

/** 闭环入口：跳到预警中心，可携带当前学生与具体预警，落地即处置 */
function gotoCrisisCenter(alert?: any) {
  const sid = detail.value?.id
  if (!sid) {
    router.push('/teacher/crisis')
    return
  }
  router.push({
    path: '/teacher/crisis',
    query: { student_id: String(sid), ...(alert ? { alert_id: String(alert.id) } : {}) },
  })
}

/** 闭环通用入口：带学生上下文跳到对应功能页，落地即可处理 */
function gotoFeature(path: string, extra?: Record<string, string>) {
  const q: Record<string, string> = {}
  if (detail.value?.id) q.student_id = String(detail.value.id)
  if (detail.value?.name) q.student_name = detail.value.name
  router.push({ path, query: { ...q, ...(extra || {}) } })
}

/** 家校沟通闭环：把成长成果 / 项目成果作为事由带给家长反馈 */
function feedbackGuardian(subject: string) {
  gotoFeature('/teacher/guardian', {
    scene: 'care',
    content: `向家长反馈学生在校成果：${subject}`,
  })
}

/** 深链 ?student=<id>：从消息页、预警中心等入口直达该学生成长档案 */
async function applyDeepLink() {
  const deepId = Number(route.query.student)
  if (!deepId) return
  if (!students.value.length) await loadStudents()
  const target = students.value.find((s) => s.id === deepId)
  if (!target) return
  openDetail(target)
  router.replace({ path: '/teacher/students' })
}

onMounted(async () => {
  await loadStudents()
  loadDashboard()
  loadAnalysisData()
  applyDeepLink()
})

// 本页 keepAlive：从预警中心返回时不会重新 mount，靠 onActivated 兜住深链
onActivated(applyDeepLink)

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.students-page {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
  overscroll-behavior-y: contain;
  padding: 0 16px 24px;
  background: #f6f7f9;
  /* 静默边框令牌：用 1px 发丝线取代阴影与重背景 */
  --sp-line: #ebedf0;
  --sp-line-strong: #e4e7ec;
}

/* ===== 概况条 =====
   桌面端原来的 4 格 Bento（2 格各占两列）已换成 .roster-panel 里的一行 .metric-strip：
   便当格占了半屏却只放 3 个数字，真正的主角「学生名单」被挤到首屏之外。
   移动端仍沿用 bento（图标+数字横排在窄屏上更省地方），所以样式保留但限定作用域。 */

/* ===== 学生页头（品牌栏：形象 + 标题 + 实时状态 + 更多操作） ===== */
/* 吸顶：滚动页面时页头固定不动，内容从其下方滑过 */
.app-head {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #fff;
  border-bottom: 1px solid var(--sp-line);
  padding: 0 16px;
  margin-bottom: 10px;
}
.app-head-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0 10px;
}
.app-head-lead {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
/* 品牌形象：圆形柔光底座承托吉祥物，与教师端其它品牌栏同一视觉语言 */
.app-head-mark {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: radial-gradient(circle at 32% 26%, #ffffff 0%, #eff4ff 58%, #dbeafe 100%);
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.1), 0 2px 8px rgba(37, 99, 235, 0.14);
}
.app-head-mark > img {
  width: 88%;
  height: 88%;
  object-fit: contain;
  display: block;
  user-select: none;
  -webkit-user-drag: none;
}
.app-head-text { min-width: 0; }
.app-head-title {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.3px;
  line-height: 1.2;
  color: #101828;
}
/* 实时状态行：静态说明 → 「状态胶囊 + 范围说明」，随数据变化 */
.app-head-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 5px 0 0;
  min-width: 0;
  font-size: 12.5px;
  color: #71717a;
}
.app-head-live {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
  padding: 2px 9px 2px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.app-head-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.app-head-live.is-alert { background: #fef3f2; color: #d92d20; }
.app-head-live.is-alert .app-head-live-dot { animation: app-head-pulse 1.8s ease-in-out infinite; }
.app-head-live.is-calm { background: #ecfdf3; color: #079455; }
@keyframes app-head-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
@media (prefers-reduced-motion: reduce) {
  .app-head-live.is-alert .app-head-live-dot { animation: none; }
}
.app-head-divider {
  width: 1px;
  height: 11px;
  flex-shrink: 0;
  background: #e4e7ec;
}
.app-head-scope {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-icon-btn {
  width: 32px; height: 32px; flex-shrink: 0;
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
  height: 34px;
  border-radius: 9px;
  padding: 0 11px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--sp-line) inset;
  transition: box-shadow 0.15s ease;
}
.list-search :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #d9dee7 inset; }
.list-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.list-search :deep(.el-input__inner) { height: 34px; font-size: 13px; color: #101828; }
.list-search :deep(.el-input__prefix),
.list-search :deep(.el-input__clear) { color: #9aa4b2; }
.filter-search { width: 210px; flex: none; }

/* 桌面端：吸顶背板 + 圆角白卡。
   背板取页面底色并通栏铺满，吸顶后遮住圆角缝隙里滑过的内容，卡片观感与改版前一致 */
@media (min-width: 768px) {
  .app-head {
    background: #f6f7f9;
    border-bottom: none;
    margin: 0 -16px 0;
    padding: 10px 16px 12px;
  }
  .app-head-bar {
    padding: 10px 14px;
    background: #fff;
    border: 1px solid var(--sp-line);
    border-radius: 10px;
  }
}

/* 空态：吉祥物在此处出现，承担产品个性 */
.empty-mascot { width: 96px; height: 96px; object-fit: contain; opacity: 0.9; }
.empty-text { color: #98a2b3; font-size: 13px; margin: 8px 0 0; }

/* ===== 主功能区：指标条 + 工具条 + 名单，一个整体卡片 ===== */
.roster-panel {
  background: #fff;
  border: 1px solid var(--sp-line);
  border-radius: 12px;
  padding: 0 14px 14px;
  margin-bottom: 10px;
}
/* 移动端概况便当格（模块化磁贴，每格只做一件事）。
   桌面端已改用 .metric-strip，这里只在移动端模板（v-else 分支）里生效。 */
.bento {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 10px 16px 10px;
}
.bento-tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--sp-line);
  border-radius: 10px;
  background: #fff;
}
.bento-tile-lg { grid-column: span 2; }
.bento-label { font-size: 11.5px; color: #71717a; }
.bento-value {
  font-size: 21px;
  font-weight: 700;
  line-height: 1.1;
  color: #101828;
  font-variant-numeric: tabular-nums;
}
.bento-value-warn { color: #d92d20; }
.bento-value-ok { color: #079455; }
.bento-hint { font-size: 11px; color: #a1a1aa; }
.bento-tile-action {
  grid-column: span 2;
  flex-direction: row;
  align-items: center;
  gap: 9px;
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
  width: 30px; height: 30px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 9px;
  background: #eff4ff;
  color: #2563eb;
}
.bento-action-main { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
.bento-tile-action .bento-label { font-size: 13px; font-weight: 600; color: #101828; }
.bento-tile-action .bento-hint { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ===== 概况条桌面端 ===== */
.metric-strip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 11px 0 12px;
  border-bottom: 1px solid #f2f4f7;
  flex-wrap: wrap;
}
.ms-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 14px;
  border-radius: 8px;
  border-right: 1px solid #f2f4f7;
}
.ms-item:last-of-type { border-right: none; }
.ms-num {
  font-size: 20px;
  font-weight: 700;
  color: #101828;
  line-height: 1.1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.ms-label { font-size: 12px; color: #98a2b3; white-space: nowrap; }
/* 只有「需要注意」的指标上色，其余保持中性，避免数字全都抢眼 */
.ms-item.is-alert { background: #fef3f2; }
.ms-item.is-alert .ms-num { color: #d92d20; }
.ms-item.is-alert .ms-label { color: #b42318; }
.ms-item.is-warn { background: #fffaeb; }
.ms-item.is-warn .ms-num { color: #b54708; }
.ms-item.is-warn .ms-label { color: #b54708; }
.ms-spacer { flex: 1; min-width: 8px; }
.ms-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1px solid var(--sp-line);
  border-radius: 8px;
  background: #fff;
  font-size: 12.5px;
  font-weight: 600;
  color: #475467;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.ms-action:hover { border-color: #2563eb; color: #2563eb; background: #eff4ff; }

/* 工具条：搜索独占较大宽度，筛选器靠右成一排 */
.roster-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0 10px;
  flex-wrap: wrap;
}
.roster-search { max-width: 320px; }
.roster-filters { display: flex; align-items: center; gap: 8px; margin-left: auto; flex-wrap: wrap; }
.rf-select { width: 128px; }
.rf-clear {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: none;
  background: none;
  padding: 0 2px;
  font-size: 12px;
  color: #667085;
  cursor: pointer;
}
.rf-clear:hover { color: #d92d20; }

/* ===== 数据分析折叠区 ===== */
.analytics-section { margin-bottom: 10px; }
.analytics-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid var(--sp-line);
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.analytics-toggle:hover { border-color: #cfdcf3; background: #fbfcfe; }
.at-main { display: flex; align-items: baseline; gap: 10px; flex: 1; min-width: 0; flex-wrap: wrap; }
.at-title { font-size: 13.5px; font-weight: 700; color: #101828; }
.at-sub { font-size: 12px; color: #98a2b3; }
.at-arrow { color: #98a2b3; transition: transform 0.18s ease; flex-shrink: 0; }
.at-arrow.is-open { transform: rotate(90deg); }
.analytics-body { margin-top: 10px; }

/*
  名单网格：列宽从 224 收到 196，一行能多放一列。
  原来 1440 屏下只能排 4 列、每张卡右侧留一大片空白，
  而卡片里真正的内容不到 200px 宽 —— 空白全浪费在「凑满列」上。
*/
.student-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(196px, 1fr)); gap: 8px; }
.student-card {
  background: #fff; border-radius: 10px; padding: 10px 12px;
  border: 1px solid var(--sp-line);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  cursor: default;
  display: flex;
  flex-direction: column;
}
.student-card:hover {
  border-color: #cfdcf3;
  box-shadow: 0 2px 8px rgba(16, 24, 40, 0.06);
}
.student-card.level-severe { border-left: 3px solid #f56c6c; }
.student-card.level-moderate { border-left: 3px solid #e6a23c; }
.student-card.level-mild { border-left: 3px solid #909399; }
.card-head { display: flex; align-items: center; gap: 9px; margin-bottom: 6px; }
.card-avatar { flex-shrink: 0; }
.card-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.card-name { font-size: 13.5px; font-weight: 600; color: #1a1a2e; }
.card-college { font-size: 11px; color: #999; margin-top: 1px; }
.crisis-tag { flex-shrink: 0; }

/*
  「关键事实」一行：成果 · 请假 · 综合分。
  原来是三个等宽列各放一个大数字 + 小标签，卡片下半部分显得很空；
  改成一个 inline 事实串，读起来像一句话，卡片也更紧凑。
*/
.card-facts {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 0;
  margin-bottom: 8px;
  border-top: 1px solid #f5f5f5;
  border-bottom: 1px solid #f5f5f5;
  font-size: 11.5px;
  color: #667085;
  flex-wrap: wrap;
}
.cf-item b { font-size: 13px; font-weight: 700; color: #101828; margin-right: 2px; }
.cf-item.is-quiet b { color: #b0b7c3; font-weight: 600; }
.cf-item.is-quiet { color: #b0b7c3; }
.cf-sep { width: 3px; height: 3px; border-radius: 50%; background: #e4e7ec; flex-shrink: 0; }
.score-excellent b, .cf-item.score-excellent { color: #079455; }
.score-good b, .cf-item.score-good { color: #2563eb; }
.score-average b, .cf-item.score-average { color: #b54708; }
.score-poor b, .cf-item.score-poor { color: #d92d20; }

/* 最近一条预警摘要：卡片里唯一需要「读」的句子，给一行半的呼吸空间 */
.card-crisis-note {
  font-size: 11.5px;
  line-height: 1.5;
  color: #b42318;
  background: #fef3f2;
  border-radius: 6px;
  padding: 5px 7px;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-skills { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.card-actions { display: flex; gap: 6px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 12px; padding: 8px 0 0; }

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
  background: #fff; border-radius: 10px;
  border: 1px solid var(--sp-line);
  overflow: hidden;
}
/* ===== 名单行：色条 + 头像 + 三列定量（成果 / 请假 / 评分） =====
   三列固定 38px 且数字等宽，纵向扫读时刻度才对得上；
   风险用「左侧 3px 色条 + 头像描边」双编码，扫一眼就能挑出要处理的人。 */
.ms-row {
  position: relative; display: flex; align-items: center; gap: 10px;
  margin: 0 14px 8px; padding: 11px 12px 11px 13px;
  background: #fff; border-radius: 14px;
  box-shadow: 0 1px 2px rgba(15, 17, 21, 0.04), 0 2px 8px rgba(15, 17, 21, 0.035);
  overflow: hidden; cursor: pointer;
  transition: transform 0.12s var(--tui-ease, ease), background 0.12s ease;
}
.ms-row:active { transform: scale(0.985); background: #fcfcfd; }
.ms-row::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: transparent;
}
.ms-row[data-risk="severe"]::before { background: #d92d20; }
.ms-row[data-risk="moderate"]::before { background: #b54708; }
.ms-row[data-risk="mild"]::before { background: #ca8a04; }

.ms-row-avatar { flex-shrink: 0; background: #f2f4f7; color: #5b6472; font-size: 14px; font-weight: 600; }
.ms-row[data-risk="severe"] .ms-row-avatar {
  background: #fff; color: #d92d20; box-shadow: 0 0 0 2px #d92d20;
}
.ms-row[data-risk="moderate"] .ms-row-avatar {
  background: #fff; color: #b54708; box-shadow: 0 0 0 2px #b54708;
}

.ms-row-main { flex: 1; min-width: 0; }
.ms-row-name { display: flex; align-items: center; gap: 5px; }
.ms-row-nm { font-size: 14.5px; font-weight: 600; color: #0f1115; letter-spacing: 0.1px; }
.ms-tag {
  flex-shrink: 0; font-size: 10px; font-weight: 600; line-height: 1.5;
  padding: 1px 6px; border-radius: 5px;
}
.ms-tag.is-severe { color: #d92d20; background: #fef3f2; }
.ms-tag.is-moderate { color: #b54708; background: #fff4ec; }
.ms-tag.is-mild { color: #ca8a04; background: #fefce8; }
.ms-row-sub {
  display: flex; align-items: center; min-width: 0;
  margin-top: 3px; font-size: 11px; color: #9ca3af;
}
/* 学院名让位给时间：先压学院、保时间，避免「3天前」被截成「3…」 */
.ms-row-college { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 0 1 auto; min-width: 0; }
.ms-row-time { flex: none; white-space: nowrap; }
.ms-row-dot { margin: 0 4px; font-style: normal; color: #ced3da; }

.ms-row-metrics { display: flex; align-items: center; flex-shrink: 0; }
.ms-m { width: 38px; text-align: center; }
.ms-m b {
  display: block; font-size: 14px; font-weight: 650; line-height: 1.15;
  color: #1f2329; font-variant-numeric: tabular-nums;
}
.ms-m b.is-zero { color: #c4c9d1; font-weight: 500; }
.ms-m b.score-excellent { color: #079455; }
.ms-m b.score-good { color: #2563eb; }
.ms-m b.score-average { color: #b54708; }
.ms-m b.score-poor { color: #d92d20; }
.ms-m i { display: block; font-style: normal; font-size: 9.5px; color: #a3a9b4; margin-top: 2px; }
.ms-m-sep { width: 1px; height: 22px; background: #eef0f3; flex-shrink: 0; margin: 0 7px; }
.ms-list-foot {
  text-align: center; font-size: 10.5px; color: #b9bfc9;
  padding: 4px 0 2px; letter-spacing: 0.02em;
}

.ms-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  text-align: center; color: #98a2b3; font-size: 13px; padding: 20px 0;
}
.ms-empty-mascot { width: 64px; height: 64px; object-fit: contain; opacity: 0.85; }

/* 名单区搜索：搜索框 + 排序入口，紧贴它所筛选的列表 */
.ms-list-search { display: flex; align-items: center; gap: 8px; margin: 0 14px 8px; }
.ms-list-search .list-search { flex: 1; min-width: 0; }

/* 排序入口：与搜索框同高的图标按钮，不抢搜索的注意力 */
.ms-icon-btn {
  flex-shrink: 0; width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 12px; background: #fff; color: #4b5563;
  border: 1px solid var(--sp-line); cursor: pointer; font-family: inherit;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  transition: border-color 0.16s ease, color 0.16s ease;
}
.ms-icon-btn:active { background: #f7f8fa; color: #1677ff; border-color: #cfdcf3; }
.ms-sort-svg { display: block; }
.ms-sort-check { margin-left: auto; color: #1677ff; }

/* 移动端搜索框：胶囊形 + 轻投影，聚焦时品牌描边与图标染色 */
.ms-list-search .list-search :deep(.el-input__wrapper) {
  height: 40px;
  padding: 0 15px;
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--sp-line) inset, 0 1px 2px rgba(16, 24, 40, 0.04);
  transition: box-shadow 0.2s ease;
}
.ms-list-search .list-search :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #d5dbe5 inset, 0 2px 6px rgba(16, 24, 40, 0.06);
}
.ms-list-search .list-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px #1677ff inset, 0 0 0 4px rgba(22, 119, 255, 0.12);
}
.ms-list-search .list-search :deep(.el-input__inner) {
  height: 40px;
  font-size: 14px;
  color: #101828;
}
.ms-list-search .list-search :deep(.el-input__inner::placeholder) { color: #98a2b3; }
.ms-list-search .list-search :deep(.el-input__prefix) {
  color: #8a94a6;
  transition: color 0.2s ease;
}
.ms-list-search .list-search :deep(.el-input__wrapper.is-focus .el-input__prefix) { color: #1677ff; }
.ms-list-search .list-search :deep(.el-input__clear) { color: #b0b8c4; }
.ms-list-search .list-search :deep(.el-input__clear:hover) { color: #6b7280; }

/* ===== 移动端学生列表：危机等级 chips ===== */
.ms-chip-scroll {
  display: flex; gap: 6px; overflow-x: auto; margin: 0 14px; padding: 2px 0 10px;
  -ms-overflow-style: none; scrollbar-width: none;
}
.ms-chip-scroll::-webkit-scrollbar { display: none; }
.ms-chip {
  flex-shrink: 0; display: inline-flex; align-items: center; gap: 4px;
  height: 30px; padding: 0 10px; border-radius: 15px;
  background: #fff; color: #555; font-size: 12.5px; font-weight: 500;
  cursor: pointer; border: 1px solid #e5e7eb; font-family: inherit;
}
/* 计数：选中前后都保留，点之前就知道有几条 */
.ms-chip b { font-size: 11px; font-weight: 600; color: #a6adb8; font-variant-numeric: tabular-nums; }
.ms-chip.active { background: #1f2329; color: #fff; font-weight: 600; border-color: #1f2329; }
.ms-chip.active b { color: rgba(255, 255, 255, 0.62); }
.ms-chip.active.is-risk { background: #d92d20; border-color: #d92d20; }

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

/* 移动端右滑动画 */
/* 子页切换动画统一使用全局 .subpage（styles/subpage-transition.css），此处不再自建 */

.mobile-detail-page {
  position: fixed; inset: 0; top: 0; left: 0; right: 0; bottom: 0;
  background: #f5f7fa; z-index: 300; display: flex; flex-direction: column; overflow: hidden;
}
.mobile-detail-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; background: #fff; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
/* 返回键统一规格：34px 触控区，无外圈底色，仅图标本身 */
.mobile-detail-header > .el-button:first-child,
.qhome-bar > .el-button:first-child {
  width: 34px; height: 34px; margin: 0;
  border-radius: 50%; background: transparent; color: #1f2430;
}
.mobile-detail-header > .el-button:first-child:active,
.qhome-bar > .el-button:first-child:active { background: rgba(20, 23, 26, 0.06); }
.mobile-detail-title { font-size: 14px; font-weight: 600; color: #1a1a1a; }
.mobile-detail-body { flex: 1; overflow-y: auto; overscroll-behavior-y: contain; padding: 14px; }
.mobile-profile {
  display: flex; align-items: center; gap: 12px; padding: 14px;
  background: #fff; border-radius: 12px; margin-bottom: 12px;
}
.mobile-profile-info { display: flex; flex-direction: column; gap: 4px; }
.mobile-profile-info strong { font-size: 15px; color: #1a1a1a; }
.mobile-profile-info small { font-size: 12px; color: #8a94a6; }
/* 移动端详情分区：横向可滚动胶囊标签，替代拥挤的下划线 tabs */
.mobile-tabbar {
  display: flex; gap: 8px; overflow-x: auto;
  padding: 2px 0 10px; margin: 0 -2px;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
.mobile-tabbar::-webkit-scrollbar { display: none; }
.mobile-tab-chip {
  flex-shrink: 0; height: 34px; padding: 0 15px;
  border: none; border-radius: 999px; background: #fff; color: #5b6472;
  font-size: 13px; font-family: inherit; cursor: pointer;
  box-shadow: inset 0 0 0 1px #eceef2;
  transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}
.mobile-tab-chip:active { transform: scale(0.97); }
.mobile-tab-chip.is-active {
  background: #1677ff; color: #fff; font-weight: 600;
  box-shadow: 0 4px 10px rgba(22, 119, 255, 0.24);
}

/* el-tabs 仅保留面板，头部由胶囊标签栏接管 */
.mobile-tabs { background: #fff; border-radius: 12px; padding: 0 10px; }
.mobile-tabs :deep(.el-tabs__header) { display: none; }
.mobile-tab-content { padding: 14px 4px 14px; }
.mobile-skill-list { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.mobile-record-card { padding: 13px 12px; border-bottom: 1px solid #f5f5f5; }
.mobile-record-card:last-child { border-bottom: none; }
.mobile-record-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.mobile-record-top small { font-size: 11.5px; color: #8a94a6; }
.mobile-record-title { font-size: 14px; font-weight: 500; color: #333; margin-bottom: 5px; }
.mobile-record-desc { font-size: 12px; color: #666; line-height: 1.6; }

/* ===== 预警：按优先级排序 + 等级可视化 ===== */
.crisis-list { display: flex; flex-direction: column; gap: 10px; }
.crisis-summary {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px;
  padding: 10px 12px; border-radius: 10px; background: #f7f8fa;
  font-size: 12px; color: #5b6472;
}
.crisis-summary-total {
  padding: 1px 7px;
  border-radius: 999px;
  font-weight: 600;
  color: #b54708;
  background: #fffaeb;
}
.crisis-summary-item { display: inline-flex; align-items: center; gap: 5px; }
.crisis-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.crisis-dot.is-severe { background: #d92d20; }
.crisis-dot.is-moderate { background: #f79009; }
.crisis-dot.is-mild { background: #2563eb; }

/* 左侧色条直接表达等级优先级：红 > 橙 > 蓝 */
.crisis-card {
  position: relative; padding: 12px 12px 12px 16px;
  border-radius: 10px; background: #fff; overflow: hidden;
  box-shadow: inset 0 0 0 1px #eef0f3;
}
.crisis-card::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
}
.crisis-card.is-severe::before { background: #d92d20; }
.crisis-card.is-moderate::before { background: #f79009; }
.crisis-card.is-mild::before { background: #2563eb; }
.crisis-card.is-normal::before { background: #98a2b3; }
.crisis-card.is-resolved { background: #fafbfc; }
.crisis-card.is-resolved::before { background: #d5d9df; }
.crisis-card.is-resolved .crisis-text { color: #98a2b3; }

.crisis-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
.crisis-level {
  font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 999px;
}
.crisis-level.is-severe { background: #fef3f2; color: #d92d20; }
.crisis-level.is-moderate { background: #fffaeb; color: #b54708; }
.crisis-level.is-mild { background: #eff4ff; color: #2563eb; }
.crisis-level.is-normal { background: #f2f3f5; color: #5b6472; }
.crisis-state { font-size: 11px; color: #8a94a6; }
.crisis-state.is-done { color: #079455; }
.crisis-time { margin-left: auto; font-size: 11px; color: #98a2b3; }
.crisis-text { margin: 0; font-size: 13px; color: #333; line-height: 1.6; }
.crisis-keywords { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.crisis-keyword {
  font-size: 11px; color: #8a94a6; background: #f4f5f7;
  border-radius: 6px; padding: 2px 7px;
}

/* 闭环：详情 ↔ 预警中心 双向打通 */
.loop-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  width: 100%; margin-bottom: 10px; padding: 10px 12px;
  border: none; border-radius: 10px; cursor: pointer;
  background: #eff4ff; color: #2563eb;
  font-size: 12px; font-family: inherit; text-align: left;
}
.loop-bar-text { font-weight: 600; }
.loop-bar:active { background: #e3ecff; }

.crisis-loop {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px;
  margin-top: 9px; padding-top: 9px; border-top: 1px dashed #eaecf0;
}
.crisis-loop-tag {
  font-size: 11px; font-weight: 600; color: #079455;
  background: #ecfdf3; border-radius: 6px; padding: 2px 7px;
}
.crisis-loop-note { font-size: 12px; color: #5b6472; }
.crisis-loop-fu { font-size: 11px; color: #8a94a6; }

.crisis-op {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 10px; padding: 6px 12px;
  border: none; border-radius: 999px; cursor: pointer;
  background: #1677ff; color: #fff;
  font-size: 12px; font-family: inherit; font-weight: 600;
}
.crisis-op:active { background: #0d5fd6; }

/* 桌面端详情弹窗的预警条目 */
.dc-alert-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dc-alert-text { margin: 0 0 8px; font-size: 13px; color: #333; line-height: 1.6; }

/* 记录卡内的闭环动作（成长 / 项目 / 请假） */
.record-op {
  display: inline-flex; align-items: center; gap: 3px;
  margin-top: 8px; padding: 4px 10px;
  border: none; border-radius: 999px; cursor: pointer;
  background: #eff4ff; color: #2563eb;
  font-size: 11.5px; font-family: inherit; font-weight: 600;
}
.record-op:active { background: #e3ecff; }

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
  .students-page { padding: 0 0 12px; background: #f5f6f7; }
  /* 移动端页头：形象与标题收敛，为状态胶囊留出横向空间 */
  .app-head-mark { width: 36px; height: 36px; }
  .app-head-title { font-size: 18px; }
  .app-head-sub { font-size: 12px; margin-top: 3px; }
}

/* ================= 方案A：档案头卡 + KPI + 风险置顶 ================= */
.mstu-hero {
  background: linear-gradient(150deg, #1d4ed8, #2563eb 55%, #3b82f6);
  border-radius: 20px;
  padding: 16px;
  color: #fff;
}
.mstu-hero-r1 { display: flex; align-items: center; gap: 12px; }
.mstu-hero-avatar { flex-shrink: 0; background: rgba(255, 255, 255, 0.22); border: 2px solid rgba(255, 255, 255, 0.45); color: #fff; font-size: 18px; font-weight: 700; }
.mstu-hero-id { flex: 1; min-width: 0; }
.mstu-hero-name { font-size: 17px; font-weight: 700; line-height: 1.3; }
.mstu-hero-meta { font-size: 11.5px; opacity: 0.85; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mstu-hero-home {
  margin-left: auto;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 999px;
  padding: 6px 11px;
  cursor: pointer;
  font-family: inherit;
}
.mstu-hero-home:active { background: rgba(255, 255, 255, 0.28); }
.mstu-hero-tags { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
.mstu-hero-tags span { font-size: 10.5px; padding: 3px 9px; border-radius: 999px; background: rgba(255, 255, 255, 0.16); }
.mstu-hero-tags span.is-risk { background: rgba(255, 255, 255, 0.92); color: #d92d20; font-weight: 700; }

.mstu-kpi {
  display: flex;
  background: #fff;
  border-radius: 16px;
  border: 1px solid var(--sp-line);
  padding: 12px 0;
  margin-top: 12px;
}
.mstu-kpi .k { flex: 1; text-align: center; position: relative; }
.mstu-kpi .k + .k::before { content: ''; position: absolute; left: 0; top: 6px; bottom: 6px; width: 1px; background: var(--sp-line); }
.mstu-kpi b { font-size: 17px; font-weight: 700; display: block; color: #101828; font-variant-numeric: tabular-nums; }
.mstu-kpi b.is-bad { color: var(--tui-danger); }
.mstu-kpi i { font-style: normal; font-size: 10.5px; color: #98a2b3; }

.mstu-risk {
  background: #fff;
  border: 1px solid var(--sp-line);
  border-left: 4px solid var(--tui-danger);
  border-radius: 16px;
  padding: 13px 14px;
  margin-top: 12px;
}
.mstu-risk-head { display: flex; align-items: center; gap: 8px; }
.mstu-risk-ic { color: var(--tui-danger); }
.mstu-risk-title { flex: 1; font-size: 13.5px; font-weight: 700; color: var(--tui-danger); }
.mstu-risk-time { font-size: 11px; color: #98a2b3; }
.mstu-risk-desc { margin: 7px 0 0; font-size: 12px; color: #475467; line-height: 1.6; }
.mstu-risk-foot { display: flex; align-items: flex-end; gap: 10px; margin-top: 10px; }
.mstu-sla { flex: 1; min-width: 0; }
.mstu-sla .lb { font-size: 11px; color: #98a2b3; display: flex; justify-content: space-between; margin-bottom: 5px; }
.mstu-sla .lb b { color: var(--tui-danger); font-weight: 600; }
.mstu-sla .bar { height: 5px; border-radius: 999px; background: var(--tui-danger-soft); overflow: hidden; }
.mstu-sla .bar i { display: block; height: 100%; border-radius: 999px; background: var(--tui-danger); transition: width 0.4s var(--tui-ease); }
.mstu-risk-btn {
  flex-shrink: 0;
  border: none;
  border-radius: 999px;
  background: var(--tui-danger);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 15px;
  cursor: pointer;
  font-family: inherit;
}
.mstu-risk-btn:active { opacity: 0.85; }

/* ================= QQ 风格学生主页 ================= */
.qhome {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  flex-direction: column;
  background: #f2f4f7;
}
.qhome-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px;
  background: transparent;
}
.qhome-bar-title { flex: 1; text-align: center; font-size: 15px; font-weight: 600; color: #101828; }
.qhome-body { flex: 1; overflow-y: auto; overscroll-behavior-y: contain; padding-bottom: 32px; }
.qhome-cover {
  height: 128px;
  background: linear-gradient(130deg, #12b7f5, #4f8df7 60%, #6a7cf7);
  position: relative;
  overflow: hidden;
  margin-top: -54px;
}
.qhome-cover::after {
  content: '';
  position: absolute;
  right: -30px;
  top: -40px;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
}
.qhome-cover::before {
  content: '';
  position: absolute;
  left: -20px;
  bottom: -60px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}
.qhome-cover-actions { position: absolute; top: 66px; right: 12px; display: flex; gap: 8px; z-index: 4; }
.qhome-cover-actions button {
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 11px;
  border-radius: 999px;
  padding: 5px 11px;
  cursor: pointer;
  font-family: inherit;
}
.qhome-head { padding: 0 14px; margin-top: -36px; position: relative; z-index: 2; }
.qhome-avatar {
  width: 72px;
  height: 72px;
  border-radius: 24px;
  border: 3px solid #fff;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(150deg, #4f8df7, #12b7f5);
  box-shadow: 0 2px 10px rgba(15, 17, 21, 0.06);
}
.qhome-name-row { display: flex; align-items: baseline; gap: 8px; margin-top: 8px; }
.qhome-name { font-size: 19px; font-weight: 700; color: #0f1115; }
.qhome-lv {
  font-size: 10.5px;
  color: #b4780a;
  background: linear-gradient(120deg, #ffe9c2, #ffd98a);
  border-radius: 999px;
  padding: 1px 8px;
  font-weight: 600;
}
.qhome-qid { font-size: 11.5px; color: #98a2b3; margin-top: 3px; }
.qhome-qid b { color: #475467; font-weight: 600; }
.qhome-sig { font-size: 12.5px; color: #475467; margin: 7px 0 0; line-height: 1.55; }
.qhome-stats {
  display: flex;
  background: #fff;
  border-radius: 16px;
  border: 1px solid var(--sp-line);
  padding: 12px 0;
  margin: 14px 14px 0;
}
.qhome-stats .s { flex: 1; text-align: center; position: relative; }
.qhome-stats .s + .s::before { content: ''; position: absolute; left: 0; top: 6px; bottom: 6px; width: 1px; background: var(--sp-line); }
.qhome-stats b { font-size: 16px; font-weight: 700; display: block; color: #101828; font-variant-numeric: tabular-nums; }
.qhome-stats i { font-style: normal; font-size: 10.5px; color: #98a2b3; }
.qhome-sec { display: flex; align-items: center; gap: 7px; margin: 16px 16px 9px; font-size: 13px; font-weight: 700; color: #101828; }
.qhome-sec .spacer { margin-left: auto; font-size: 11px; font-weight: 400; color: #98a2b3; }
.qhome-badges { display: flex; gap: 8px; overflow-x: auto; padding: 0 14px 2px; scrollbar-width: none; }
.qhome-badges::-webkit-scrollbar { display: none; width: 0; height: 0; }
.qhome-badge {
  flex: none;
  width: 76px;
  background: #fff;
  border: 1px solid var(--sp-line);
  border-radius: 12px;
  text-align: center;
  padding: 10px 4px 8px;
  box-shadow: 0 1px 2px rgba(15, 17, 21, 0.04);
}
.qhome-badge-ic {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  margin-bottom: 4px;
  color: #fff;
}
.qhome-badge-ic.tone-brand { background: #2563eb; }
.qhome-badge-ic.tone-success { background: #079455; }
.qhome-badge-ic.tone-violet { background: #7f56d9; }
.qhome-badge-ic.tone-warn { background: #dc6803; }
.qhome-badge-ic.tone-cyan { background: #0e9384; }
.qhome-badge-ic.tone-danger { background: #d92d20; }
.qhome-badge > span:last-child { font-size: 10.5px; color: #667085; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.qhome-photos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; padding: 0 14px; }
.qhome-photo {
  aspect-ratio: 1;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #fff;
  border: none;
  font-size: 11px;
  font-family: inherit;
}
.qhome-photo.more { background: #fff; border: 1px dashed #d0d5dd; color: #98a2b3; flex-direction: column; }
.qhome-post {
  background: #fff;
  border: 1px solid var(--sp-line);
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(15, 17, 21, 0.04);
  padding: 13px 14px;
  margin: 0 14px 10px;
}
.qhome-post-head { display: flex; align-items: center; gap: 9px; }
.qhome-post-name { font-size: 13.5px; font-weight: 700; color: #101828; }
.qhome-post-time { font-size: 11px; color: #98a2b3; }
.qhome-post-text { font-size: 13px; line-height: 1.6; color: #101828; margin-top: 8px; }
.qhome-post-desc { font-size: 12px; color: #667085; line-height: 1.6; margin: 5px 0 0; }
.qhome-post-imgs { display: grid; gap: 6px; margin-top: 9px; }
.qhome-post-imgs.g1 { grid-template-columns: 1fr; }
.qhome-post-imgs.g2 { grid-template-columns: 1fr 1fr; }
.qhome-pimg {
  height: 92px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  gap: 6px;
  font-size: 12px;
}
/* ============================================================
   移动端工作台（B 版式）：首屏主导 + 二级子页
   首屏 = 原首页整块（HomeMobileBoard）；学生名单收成一张摘要卡，
   点进去整页推入子页。子页动效与学生端「校园资讯」分页同规格：
   200ms cubic-bezier(.22,.61,.36,1)，整页从右侧推入 / 推回右侧。
   ============================================================ */
.wb-entries {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0 0 14px;
}
.wb-entry {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 14px 16px;
  border: none;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.wb-entry-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.wb-entry-title {
  font-size: 15px;
  font-weight: 700;
  color: #101828;
}
.wb-entry-more {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: var(--tui-text-quiet, #98a2b3);
}
/* 三个数字：等宽对齐，一眼扫完「多少人 / 几个高危 / 多少有成果」 */
.wb-entry-metrics {
  display: flex;
  align-items: flex-end;
  gap: 22px;
}
.wb-m {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.wb-m b {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  color: #101828;
  font-variant-numeric: tabular-nums;
}
.wb-m i {
  font-style: normal;
  font-size: 11.5px;
  color: var(--tui-text-quiet, #98a2b3);
}
.wb-m.is-warn b { color: #d92d20; }
.wb-m.is-ok b { color: #12b76a; }
/* 优先跟进：把「今天最该看谁」直接摆到首屏，不必先点进名单 */
.wb-entry-risk {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding-top: 2px;
  border-top: 1px solid var(--tui-border, #eaecf0);
}
.wb-entry-risk::-webkit-scrollbar { display: none; }
.wb-risk-chip {
  flex: 0 0 auto;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  background: #f2f4f7;
  color: #475467;
}
.wb-risk-chip.is-severe { background: #fef3f2; color: #d92d20; }
.wb-risk-chip.is-moderate { background: #fffaeb; color: #b54708; }
.wb-risk-chip.is-mild { background: #eff4ff; color: #1d4ed8; }
.wb-risk-more {
  flex: 0 0 auto;
  font-size: 11.5px;
  color: var(--tui-text-quiet, #98a2b3);
}

/* 班级数据分析：横向一行（图标 + 标题 + 说明 + 箭头） */
.wb-entry-slim {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}
.wb-entry-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: #f4f3ff;
  color: #6941c6;
  flex-shrink: 0;
}
.wb-entry-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.wb-entry-hint {
  font-size: 11.5px;
  color: var(--tui-text-quiet, #98a2b3);
}

/* ===== 二级子页：学生名单 ===== */
.wb-subpage {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  flex-direction: column;
  background: #f2f3f5;
  overflow: hidden;
}
.wb-subpage-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.wb-back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #1a1a1a;
  cursor: pointer;
}
.wb-back:active { background: #f2f4f7; }
.wb-subpage-title { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.wb-subpage-count {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 12px;
  color: #1d4ed8;
  background: #eff4ff;
  font-variant-numeric: tabular-nums;
}
.wb-subpage-body {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: 10px 8px 20px;
}
/* 入场 / 出场：与校园资讯分页同一条曲线（整页推入，不缩放不淡出） */
/* 子页切换动画统一使用全局 .subpage（styles/subpage-transition.css），此处不再自建 */

.qhome-post-ops { display: flex; border-top: 1px solid var(--sp-line); margin-top: 11px; padding-top: 9px; }
.qhome-op {
  flex: 1;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: #98a2b3;
  cursor: pointer;
  font-family: inherit;
  padding: 4px 0;
}
.qhome-op.liked { color: #12b7f5; font-weight: 600; }
.qhome-op + .qhome-op { border-left: 1px solid var(--sp-line); }
</style>