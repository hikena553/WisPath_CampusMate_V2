<template>
  <div
    class="tui-page dt-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader
      :title="isMobile ? '心理预警' : '心理预警工作台'"
      fallback="/teacher"
    />
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <!-- ===================== 桌面端：钉钉工作台（搜索 + 指标卡 + 待办/动态 + 清单） ===================== -->
    <div v-if="!isMobile" class="tui-content dt-content">
      <header class="dt-head">
        <div class="dt-head-l">
          <h2>心理预警</h2>
          <p class="dt-head-sub">
            今天 <b>{{ unresolved.length }}</b> 条待处置 · 共 {{ alerts.length }} 条预警
          </p>
        </div>
        <div class="dt-head-r">
          <el-input
            v-model="search"
            class="dt-search"
            placeholder="搜索学生、预警信号"
            clearable
            :prefix-icon="Search"
          />
          <el-select v-model="levelFilter" class="dt-level" size="default">
            <el-option label="全部等级" value="all" />
            <el-option label="高危" value="severe" />
            <el-option label="中度" value="moderate" />
            <el-option label="轻度" value="mild" />
          </el-select>
        </div>
      </header>

      <!-- 四张指标卡：图标块只占小面积，页面主体仍是黑白灰 -->
      <div class="dt-kpis">
        <div class="dt-kpi">
          <span class="dt-ic blue">待</span>
          <div class="dt-kpi-bd"><span>待处置</span><b>{{ unresolved.length }}</b></div>
        </div>
        <div class="dt-kpi">
          <span class="dt-ic red">危</span>
          <div class="dt-kpi-bd"><span>高危未闭环</span><b>{{ highRisk.length }}</b></div>
        </div>
        <div class="dt-kpi">
          <span class="dt-ic orange">时</span>
          <div class="dt-kpi-bd"><span>随访逾期</span><b>{{ followUpDue.length }}</b></div>
        </div>
        <div class="dt-kpi">
          <span class="dt-ic green">闭</span>
          <div class="dt-kpi-bd"><span>已闭环</span><b>{{ closedCount }}</b></div>
        </div>
      </div>

      <div class="dt-cols">
        <section class="dt-card">
          <div class="dt-card-h">
            <b>今日待办</b>
            <button type="button" class="dt-more" @click="goList">全部 {{ unresolved.length }} 条 ›</button>
          </div>
          <button
            v-for="row in ladderTop"
            :key="row.id"
            type="button"
            class="dt-todo-i"
            @click="openIntervene(row)"
          >
            <span class="dt-dot" :class="`lv-${row.level}`"></span>
            <span class="dt-todo-bd">
              <b>{{ row.student_name }} · {{ todoLabel(row) }}</b>
              <span>{{ row.summary || '（无摘要）' }}</span>
            </span>
            <span class="dt-todo-date" :class="dueTone(row)">{{ dueText(row) }}</span>
          </button>
          <div v-if="!ladderTop.length" class="dt-empty">当前没有未闭环预警</div>
        </section>

        <section class="dt-card">
          <div class="dt-card-h">
            <b>预警动态</b>
            <span class="dt-card-sub">最近 {{ recentActivity.length }} 条</span>
          </div>
          <div v-for="it in recentActivity" :key="it.id" class="dt-tl-i">
            <span class="dt-dot" :class="`tl-${it.tone}`"></span>
            <div class="dt-tl-bd">
              <b>{{ it.title }}</b>
              <span>{{ it.desc }}</span>
            </div>
            <span class="dt-tl-time">{{ it.time }}</span>
          </div>
          <div v-if="!recentActivity.length" class="dt-empty">暂无预警记录</div>
        </section>
      </div>

      <!-- 预警清单：钉钉式表格行（学生 / 触发信号 / 状态 / 随访 / 行内操作） -->
      <section id="wb-list" class="dt-card dt-listcard">
        <div class="dt-card-h">
          <b>预警清单</b>
          <span class="dt-card-sub">{{ filtered.length }} 条</span>
        </div>

        <div class="dt-toolbar">
          <div class="dt-seg">
            <button type="button" :class="{ on: filter === 'all' }" @click="filter = 'all'">全部</button>
            <button type="button" :class="{ on: filter === 'unresolved' }" @click="filter = 'unresolved'">待处置</button>
            <button type="button" :class="{ on: filter === 'follow_up' }" @click="filter = 'follow_up'">待随访</button>
            <button type="button" :class="{ on: filter === 'resolved' }" @click="filter = 'resolved'">已闭环</button>
          </div>
          <button type="button" class="dt-reset" @click="resetFilters">重置筛选</button>
        </div>

        <!-- 闭环：从学生详情跳来，仅看该学生的预警 -->
        <div v-if="studentFilter" class="wb-scope">
          <span class="wb-scope-text">仅看：{{ studentFilterName }}</span>
          <button type="button" class="wb-scope-clear" @click="clearStudentFilter">
            查看全部预警<el-icon :size="12"><Close /></el-icon>
          </button>
        </div>

        <AgentLoading v-if="loading && !alerts.length" block :tips="WB_TIPS" />
        <div v-show="!(loading && !alerts.length)">
          <div v-if="!filtered.length" class="dt-empty">
            <b>暂无预警记录</b>
            <span>当前筛选条件下没有预警，切换筛选或稍后刷新</span>
          </div>
          <template v-else>
            <div class="dt-lth">
              <span>学生</span><span>触发信号</span><span>处置状态</span><span>随访时限</span><span>操作</span>
            </div>
            <div v-for="row in paged" :key="row.id" class="dt-li" :class="`lv-${row.level}`">
              <span class="dt-who">
                <span class="dt-avatar" :class="`lv-${row.level}`">{{ row.student_name.slice(0, 1) }}</span>
                <span class="dt-who-bd">
                  <b>{{ row.student_name }}</b>
                  <em :class="`lv-${row.level}`">{{ levelText(row.level) }}</em>
                </span>
              </span>
              <span class="dt-sig" :title="row.summary">{{ row.summary }}</span>
              <span class="dt-st" :class="{ done: row.resolved }">{{ statusText(row) }}</span>
              <span class="dt-fu" :class="{ due: isFollowUpDue(row) }">{{ followText(row) }}</span>
              <span class="dt-ops">
                <button type="button" class="dt-op" :disabled="row.resolved" @click="openIntervene(row)">登记</button>
                <button type="button" class="dt-op" :disabled="row.resolved" @click="handleResolve(row)">闭环</button>
                <button type="button" class="dt-op" @click="gotoStudent(row)">档案</button>
                <button type="button" class="dt-op" @click="exportArchive(row)">导出</button>
              </span>
            </div>
          </template>
        </div>

        <div v-if="filtered.length" class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="filtered.length"
            :pager-count="5"
            small
            background
            layout="total, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </section>

      <!-- 处置态势：图表与分析保留在清单之后，作为下钻视角 -->
      <div class="dt-analytics">
        <CrisisAnalytics :analytics="analytics" />
      </div>
    </div>

    <!-- ===================== 移动端：钉钉工作台（原生白头部 + 指标卡 + 待办 + 宫格入口） ===================== -->
    <template v-else>
      <div v-if="!mobileView" class="dtm-home">
        <div class="dtm-hero">
          <div class="dtm-hero-top">
            <b>今日态势</b>
            <span>共 {{ alerts.length }} 条预警</span>
          </div>
          <div class="dtm-kpis">
            <div class="dtm-kpi"><b>{{ unresolved.length }}</b><span>待处置</span></div>
            <div class="dtm-kpi"><b :class="{ risk: highRisk.length > 0 }">{{ highRisk.length }}</b><span>高危</span></div>
            <div class="dtm-kpi"><b :class="{ warn: followUpDue.length > 0 }">{{ followUpDue.length }}</b><span>逾期</span></div>
            <div class="dtm-kpi"><b>{{ closedCount }}</b><span>闭环</span></div>
          </div>
        </div>

        <div class="dtm-sheet">
          <div class="dtm-sh">
            <b>今日待办</b>
            <span>共 {{ unresolved.length }} 条 ›</span>
          </div>

          <div v-if="followUpDue.length" class="dtm-over">
            <em><el-icon :size="12"><WarningFilled /></el-icon>{{ followUpDue.length }} 条随访已逾期 · 最久 {{ worstOverdueDays }} 天</em>
            <span>逾期最久：{{ worstOverdue.student_name }} · {{ worstOverdue.summary }}</span>
          </div>

          <button
            v-for="a in ladderTop"
            :key="a.id"
            type="button"
            class="dtm-todo-i"
            @click="openIntervene(a)"
          >
            <span class="dt-dot" :class="`lv-${a.level}`"></span>
            <span class="dtm-todo-bd">
              <b>{{ a.student_name }} · {{ todoLabel(a) }}</b>
              <span>{{ a.summary || '（无摘要）' }}</span>
            </span>
            <span class="dtm-todo-date" :class="dueTone(a)">{{ dueText(a) }}</span>
          </button>
          <div v-if="!ladderTop.length" class="dtm-empty">今天没有未闭环预警</div>
          <button v-if="ladder.length > ladderTop.length" type="button" class="dtm-more" @click="mobileView = 'list'">
            查看全部 {{ ladder.length }} 条未闭环预警 ›
          </button>
        </div>

        <div class="dtm-grid">
          <button type="button" class="dtm-gi" @click="mobileView = 'list'">
            <span class="dtm-gic">单</span><span>预警清单</span>
          </button>
          <button type="button" class="dtm-gi" @click="mobileView = 'deadline'">
            <span class="dtm-gic orange">时</span><span>处置时限</span>
          </button>
          <button type="button" class="dtm-gi" @click="mobileView = 'analytics'">
            <span class="dtm-gic green">势</span><span>态势分析</span>
          </button>
        </div>

        <div class="dtm-card">
          <div class="dtm-sh">
            <b>预警动态</b>
            <span>最近 {{ recentActivity.length }} 条</span>
          </div>
          <div v-for="it in recentActivity" :key="it.id" class="dtm-tl-i">
            <span class="dt-dot" :class="`tl-${it.tone}`"></span>
            <div class="dtm-tl-bd">
              <b>{{ it.title }}</b>
              <span>{{ it.desc }}</span>
            </div>
            <span class="dtm-tl-time">{{ it.time }}</span>
          </div>
          <div v-if="!recentActivity.length" class="dtm-empty">暂无预警记录</div>
        </div>

        <div class="dtm-note">
          依据：随访日期（follow_up_date）· 风险等级 · 创建时间；没有随访日期的按「已等待天数」排在后面
        </div>
      </div>

      <!-- 二级页：整屏右滑，头部沿用统一的白色子页头 -->
      <div class="cw-sub-scope" :class="{ 'is-open': mobileView }">
        <header v-if="mobileView" class="cw-subbar">
          <button
            type="button"
            class="cw-subbar-back"
            aria-label="返回预警总览"
            @click="mobileView = ''"
          >
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <div class="cw-subbar-main">
            <b>{{ mobileViewTitle }}</b>
          </div>
        </header>
        <div class="cw-sub-body">
          <!-- 处置态势：满宽分段式（数据带 + 智能分析 + 等级 / 阶段 / 趋势 / 敏感词） -->
          <div v-if="mobileView === 'analytics'" class="dtm-view dtm-ast">
            <div class="dtm-ast-hero">
              <div class="dtm-ast-hero-top">
                <b>态势总览</b>
                <span>{{ astLoaded ? `共 ${ast.total} 条预警` : '统计中…' }}</span>
              </div>
              <div class="dtm-ast-kpis">
                <div>
                  <b>{{ astLoaded ? ast.unresolved : '—' }}</b>
                  <span>待处置</span>
                </div>
                <div>
                  <b :class="{ risk: ast.high_risk > 0 }">{{ astLoaded ? ast.high_risk : '—' }}</b>
                  <span>高危未闭环</span>
                </div>
                <div>
                  <b :class="{ risk: ast.sla.overdue > 0 }">{{ astLoaded ? ast.sla.overdue : '—' }}</b>
                  <span>超时未办</span>
                </div>
                <div>
                  <b>{{ astLoaded ? ast.stage.closed : '—' }}</b>
                  <span>已闭环</span>
                </div>
              </div>
            </div>

            <!-- 智能分析：只喂聚合指标，模型给出研判与今日动作 -->
            <section class="dtm-ast-sec dtm-ast-ai">
              <div class="dtm-ast-h">
                <b><em class="dtm-ast-badge">AI</em>智能分析</b>
                <button
                  type="button"
                  class="dtm-ast-refresh"
                  :disabled="insightLoading"
                  @click="loadInsight(true)"
                >
                  {{ insightLoading ? '分析中…' : '重新分析' }}
                </button>
              </div>

              <AgentLoading v-if="insightLoading" size="md" text="正在综合指标生成研判…" />

              <template v-else-if="insight">
                <p class="dtm-ast-sum">{{ insight.summary }}</p>
                <ol class="dtm-ast-advice">
                  <li v-for="(t, i) in insight.advice" :key="i">
                    <i>{{ i + 1 }}</i>
                    <span>{{ t }}</span>
                  </li>
                </ol>
                <p class="dtm-ast-src">
                  {{ insight.source === 'ai' ? 'AI 综合当前指标生成' : '模型暂不可用 · 已按指标规则生成' }}
                  <template v-if="insightTime"> · {{ insightTime }}</template>
                </p>
              </template>

              <div v-else class="dtm-ast-fail">
                <span>{{ insightError ? '智能分析暂时不可用' : '暂无分析结果' }}</span>
                <button type="button" @click="loadInsight(true)">重新分析</button>
              </div>
            </section>

            <!-- 等级构成：分段条 + 图例，不做环形图卡片 -->
            <section class="dtm-ast-sec">
              <div class="dtm-ast-h">
                <b>等级构成</b>
                <span>{{ ast.total }} 条 · 高危占比 {{ levelPct('severe') }}%</span>
              </div>
              <div class="dtm-ast-stack">
                <span
                  v-for="s in levelSegs"
                  v-show="s.pct > 0"
                  :key="s.key"
                  :style="{ width: s.pct + '%', background: s.color }"
                  :title="`${s.label} ${s.value} 条`"
                />
              </div>
              <div class="dtm-ast-legend">
                <div v-for="s in levelSegs" :key="s.key">
                  <i :style="{ background: s.color }" />
                  <span>{{ s.label }}</span>
                  <b>{{ s.value }}</b>
                  <em>{{ s.pct }}%</em>
                </div>
              </div>
            </section>

            <!-- 处置阶段：发现 → 干预 → 随访 → 闭环 -->
            <section class="dtm-ast-sec">
              <div class="dtm-ast-h">
                <b>处置阶段</b>
                <span>{{ ast.total ? `闭环率 ${closeRate}%` : '暂无数据' }}</span>
              </div>
              <div class="dtm-ast-stage">
                <div v-for="s in stageRows" :key="s.key">
                  <div class="dtm-ast-stage-top">
                    <span>{{ s.label }}</span>
                    <b>{{ s.value }}</b>
                  </div>
                  <div class="dtm-ast-track">
                    <span :class="`is-${s.key}`" :style="{ width: s.pct + '%' }" />
                  </div>
                </div>
              </div>
            </section>

            <!-- 近 N 天趋势：柱状条，零值只留底座 -->
            <section class="dtm-ast-sec">
              <div class="dtm-ast-h">
                <b>预警趋势</b>
                <span>近 {{ AST_DAYS }} 天 · 近 7 天新增 {{ recent7 }} 条</span>
              </div>
              <template v-if="trendHasData">
                <div class="dtm-ast-trend">
                  <span
                    v-for="p in trendBars"
                    :key="p.day"
                    class="dtm-ast-bar"
                    :class="{ zero: p.count === 0, hot: p.count === trendMax && p.count > 0 }"
                    :style="{ height: p.h + '%' }"
                    :title="`${p.day}：${p.count} 条`"
                  />
                </div>
                <div class="dtm-ast-axis">
                  <span>{{ trendFirst }}</span>
                  <span>{{ trendLast }}</span>
                </div>
              </template>
              <div v-else class="dtm-ast-empty">近 {{ AST_DAYS }} 天没有新增预警</div>
            </section>

            <!-- 敏感词：词频标签，高频标红 -->
            <section class="dtm-ast-sec">
              <div class="dtm-ast-h">
                <b>敏感词</b>
                <span>词频 TOP {{ keywordsTop.length }}</span>
              </div>
              <div v-if="keywordsTop.length" class="dtm-ast-chips">
                <span v-for="k in keywordsTop" :key="k.word" :class="{ hot: k.count >= keywordMax }">
                  {{ k.word }}<i>{{ k.count }}</i>
                </span>
              </div>
              <div v-else class="dtm-ast-empty">暂无高频词</div>
              <p class="dtm-ast-note">来源：预警命中关键词与摘要文本的分词统计</p>
            </section>
          </div>

          <!-- 处置时限：整页满宽，不再套卡片 -->
          <div v-if="mobileView === 'deadline'" class="dtm-view">
            <div class="dtm-view-h">
              <b>随访计划</b>
              <span>已到期 {{ followUpDue.length }} · 待随访 {{ followingUp }}</span>
            </div>
            <div class="dtm-view-tip">
              <el-icon><InfoFilled /></el-icon>
              <span>按计划随访日期由近到远排序，逾期项进度条满格并标红。</span>
            </div>
            <div v-if="deadlineItems.length" class="dtm-rows">
              <div v-for="d in deadlineItems" :key="d.id" class="dtm-row">
                <div class="dtm-row-top">
                  <span class="dtm-row-name">{{ d.name }}</span>
                  <span class="dtm-row-date" :class="{ 'is-due': d.days <= 0 }">{{ deadlineLabel(d.days) }}</span>
                </div>
                <div class="dtm-row-sub">计划随访 {{ d.date }}</div>
                <div class="tui-progress">
                  <div class="tui-progress-track">
                    <span
                      class="tui-progress-fill"
                      :class="d.days <= 0 ? 'is-danger' : d.days <= 3 ? 'is-warn' : ''"
                      :style="{ '--pct': deadlinePct(d.days) / 100 }"
                    />
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="26"><AlarmClock /></el-icon></span>
              <span class="tui-empty-title">暂无待随访时限</span>
              <span class="tui-empty-desc">当前预警都未设置随访日期，或已全部闭环</span>
            </div>
          </div>

          <!-- 预警清单：整页满宽列表，不再套卡片 -->
          <div v-if="mobileView === 'list'" class="dtm-view">
            <div class="dtm-filter">
              <div class="dtm-subsearch">
                <el-input v-model="search" placeholder="搜索学生、预警信号" clearable :prefix-icon="Search" />
                <el-select v-model="levelFilter" class="dtm-sublevel">
                  <el-option label="全部等级" value="all" />
                  <el-option label="高危" value="severe" />
                  <el-option label="中度" value="moderate" />
                  <el-option label="轻度" value="mild" />
                </el-select>
              </div>

              <div class="tui-seg wb-seg">
                <button type="button" class="tui-seg-item" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
                <button type="button" class="tui-seg-item" :class="{ active: filter === 'unresolved' }" @click="filter = 'unresolved'">待处置</button>
                <button type="button" class="tui-seg-item" :class="{ active: filter === 'follow_up' }" @click="filter = 'follow_up'">待随访</button>
                <button type="button" class="tui-seg-item" :class="{ active: filter === 'resolved' }" @click="filter = 'resolved'">已闭环</button>
              </div>

              <div v-if="studentFilter" class="wb-scope">
                <span class="wb-scope-text">仅看：{{ studentFilterName }}</span>
                <button type="button" class="wb-scope-clear" @click="clearStudentFilter">
                  查看全部预警<el-icon :size="12"><Close /></el-icon>
                </button>
              </div>
            </div>

            <div class="dtm-view-h dtm-view-h-list">
              <b>全部预警</b>
              <span>{{ filtered.length }} 条</span>
            </div>

            <div v-if="!filtered.length" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="26"><WarningFilled /></el-icon></span>
              <span class="tui-empty-title">暂无预警记录</span>
              <span class="tui-empty-desc">当前筛选条件下没有预警，切换筛选或稍后刷新</span>
            </div>

            <div v-else class="cw2-list">
              <div v-for="row in paged" :key="row.id" class="cw2-item" :class="`lv-${row.level}`">
                <button
                  type="button"
                  class="cw2-row"
                  @click="expandedAlertId = expandedAlertId === row.id ? '' : row.id"
                >
                  <span class="cw2-avatar">{{ row.student_name.slice(0, 1) }}</span>
                  <span class="cw2-main">
                    <span class="cw2-title">
                      {{ row.student_name }}
                      <span class="cw2-lv">{{ levelText(row.level) }}</span>
                      <span class="cw2-state" :class="{ done: row.resolved }">{{ statusText(row) }}</span>
                    </span>
                    <span class="cw2-sum">{{ row.summary }}</span>
                    <span class="cw2-meta">
                      {{ formatTime(row.created_at) }}
                      <template v-if="row.follow_up_date">
                        · <span :class="{ 'fu-due': isFollowUpDue(row) }">随访 {{ row.follow_up_date }}{{ isFollowUpDue(row) ? ' · 已到期' : '' }}</span>
                      </template>
                    </span>
                  </span>
                  <el-icon class="cw2-chevron" :class="{ open: expandedAlertId === row.id }">
                    <ArrowDown />
                  </el-icon>
                </button>

                <div v-if="expandedAlertId === row.id" class="cw2-expand">
                  <div v-if="row.intervention_type" class="cw2-note">
                    <b>{{ row.intervention_type }}</b>
                    <span>{{ row.intervention_note || '未填写备注' }}</span>
                  </div>
                  <div class="cw2-actions">
                    <button type="button" class="cw2-btn cw2-btn-main" :disabled="row.resolved" @click="openIntervene(row)">
                      干预处置
                    </button>
                    <button type="button" class="cw2-btn" :disabled="row.resolved" @click="handleResolve(row)">标记闭环</button>
                    <button type="button" class="cw2-btn" @click="gotoStudent(row)">查看档案</button>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="filtered.length" class="pagination-wrapper dtm-pagination">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50]"
                :total="filtered.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="handleSizeChange"
                @current-change="handlePageChange"
              />
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- 预警干预处置（表单+AI：移动端=全屏子页） -->
    <ResponsivePopup
      v-model="dialogVisible"
      title="预警干预处置"
      width="380px"
      align-center
      :close-on-click-modal="false"
      class="tui-dialog"
      destroy-on-close
    >
      <div class="tui-section-hint danger">
        <el-icon><InfoFilled /></el-icon>
        <span>正在处置「{{ current?.student_name || '该学生' }}」的预警，保存后将写入处置记录并更新随访计划。</span>
      </div>
      <div v-if="current" class="wb-ctx">
        <div class="wb-ctx-head">
          <span class="stu-avatar">{{ current.student_name.slice(0, 1) }}</span>
          <span class="wb-ctx-name">{{ current.student_name }}</span>
          <el-tag :type="levelTagType(current.level)" size="small" effect="dark">{{ levelText(current.level) }}</el-tag>
          <span class="wb-ctx-time">{{ formatTime(current.created_at) }}</span>
        </div>
        <p class="wb-ctx-summary">{{ current.summary }}</p>
        <div v-if="current.keywords_matched" class="wb-ctx-kw">命中关键词：{{ current.keywords_matched }}</div>
      </div>
      <!-- AI 处置建议卡：打开弹窗自动生成，可一键回填干预方式与处置备注 -->
      <div v-if="current" class="wb-advice">
        <div class="wb-advice-head">
          <b>AI 处置建议</b>
          <button type="button" class="wb-advice-btn" :disabled="adviceLoading" @click="loadAdvice(true)">
            {{ adviceLoading ? '生成中…' : (advice ? '重新生成' : '生成建议') }}
          </button>
        </div>
        <template v-if="advice">
          <p class="wb-advice-scheme">推荐：{{ advice.scheme }}</p>
          <ol class="wb-advice-steps">
            <li v-for="(s, i) in advice.steps" :key="i">{{ s }}</li>
          </ol>
          <p class="wb-advice-why">{{ advice.rationale }}</p>
          <p v-if="advice.taboo.length" class="wb-advice-taboo">禁忌：{{ advice.taboo.join('；') }}</p>
          <button type="button" class="wb-advice-apply" @click="applyAdvice">采纳并回填表单</button>
          <span class="wb-advice-src">{{ advice.source === 'ai' ? 'AI 基于学生档案生成' : '规则化建议（模型暂不可用）' }}</span>
        </template>
        <p v-else-if="!adviceLoading" class="wb-advice-why">尚无建议，点击右上角生成。</p>
      </div>
      <el-form v-if="current" label-width="80px">
        <el-form-item label="干预方式">
          <el-select v-model="form.intervention_type" placeholder="请选择干预方式" style="width: 100%">
            <el-option v-for="o in interventionOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <div class="wb-draft">
          <AiDraftField
            v-model="form.intervention_note"
            label="处置备注"
            :rows="3"
            :maxlength="300"
            placeholder="记录本次处置过程，供后续随访参考……"
            :draft="aiDraft"
            :points="aiPoints"
          />
        </div>
        <el-form-item label="随访日期">
          <el-date-picker v-model="form.follow_up_date" type="date" value-format="YYYY-MM-DD" placeholder="计划跟进时间" style="width:100%" />
        </el-form-item>
        <el-form-item label="处置结果">
          <el-switch v-model="form.resolved" active-text="已闭环" inactive-text="持续跟进" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitIntervene">保存处置</el-button>
      </template>
    </ResponsivePopup>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
// v6.1 弹窗减负：处置表单走全屏子页，闭环确认走底部动作面板
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import { useRoute, useRouter } from 'vue-router'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import { onDataChange } from '@/utils/dataSync'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import CrisisAnalytics from '@/components/teacher/crisis/CrisisAnalytics.vue'
import {
  WarningFilled,
  Close,
  InfoFilled,
  AlarmClock,
  ArrowLeft,
  ArrowDown,
  Search,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { getAlerts, resolveAlert, interveneAlert, getCrisisAnalytics, getCrisisInsight, getAlertAdvice, exportStudentCrisisArchive, type CrisisAdvice } from '@/api/crisis'
import type { CrisisAlert } from '@/types'
import type { CrisisAnalytics as CrisisAnalyticsData, CrisisInsight } from '@/api/crisis'

const { isMobile } = useResponsive()

/** 移动端下拉刷新：手动刷新按钮已移除，统一由下拉手势触发 */
const pull = usePullRefresh(loadAlerts, { enabled: () => isMobile.value })

const route = useRoute()
const router = useRouter()

const alerts = ref<CrisisAlert[]>([])
/** 移动端二级页：总览只留「今日待办」，清单/时限/态势各进一层，避免一屏拉得太长 */
const mobileView = ref<'' | 'list' | 'deadline' | 'analytics'>('')
/** 移动端预警清单：当前展开的那一条（同屏只展开一条，避免整页铺满卡片） */
const expandedAlertId = ref<number | string>('')
const mobileViewTitle = computed(() => {
  if (mobileView.value === 'list') return '预警清单'
  if (mobileView.value === 'deadline') return '处置时限'
  if (mobileView.value === 'analytics') return '处置态势'
  return ''
})
watch(mobileView, (v) => {
  // 打开处置态势时按需触发智能分析，避免每次进页面都重复请求
  if (v === 'analytics') loadInsight()
  // 回到总览时把清单筛选还原，保证今日待办与默认口径一致
  if (!v) {
    filter.value = 'all'
    expandedAlertId.value = ''
  }
})
/** 聚合分析（等级分布 / 处置阶段 / 趋势 / 敏感词 / 时限），由后端 /crisis/analytics 统一计算 */
const analytics = ref<CrisisAnalyticsData | null>(null)

/* ================= 处置态势：移动端自研分段视图 ================= */
const AST_DAYS = 30
/** 空数据兜底：未加载时统一走零值，避免模板里到处判空 */
const EMPTY_AST: CrisisAnalyticsData = {
  level_dist: { severe: 0, moderate: 0, mild: 0, normal: 0 },
  stage: { found: 0, intervened: 0, following: 0, closed: 0 },
  trend: [],
  keywords: [],
  sla: { overdue: 0, due_soon: 0, items: [] },
  total: 0,
  unresolved: 0,
  high_risk: 0,
}
const astLoaded = computed(() => !!analytics.value)
const ast = computed<CrisisAnalyticsData>(() => analytics.value ?? EMPTY_AST)

const AST_LEVELS = [
  { key: 'severe', label: '高危', color: '#d92d20' },
  { key: 'moderate', label: '中度', color: '#b54708' },
  { key: 'mild', label: '轻度', color: '#2563eb' },
  { key: 'normal', label: '正常', color: '#9ca3af' },
] as const

const levelSegs = computed(() => {
  const total = ast.value.total || 0
  return AST_LEVELS.map((lv) => {
    const value = ast.value.level_dist[lv.key]
    return { ...lv, value, pct: total ? Math.round((value / total) * 100) : 0 }
  })
})
function levelPct(key: 'severe' | 'moderate' | 'mild' | 'normal') {
  const total = ast.value.total || 0
  return total ? Math.round((ast.value.level_dist[key] / total) * 100) : 0
}

const closeRate = computed(() => {
  const base = ast.value.stage.found || ast.value.total
  return base ? Math.round((ast.value.stage.closed / base) * 100) : 0
})

const stageRows = computed(() => {
  const s = ast.value.stage
  const base = Math.max(s.found, 1)
  return [
    { key: 'found', label: '发现预警', value: s.found },
    { key: 'intervened', label: '已登记干预', value: s.intervened },
    { key: 'following', label: '随访中', value: s.following },
    { key: 'closed', label: '已闭环', value: s.closed },
  ].map((row) => ({ ...row, pct: Math.min(100, Math.round((row.value / base) * 100)) }))
})

const trendMax = computed(() => Math.max(0, ...ast.value.trend.map((p) => p.count)))
const trendHasData = computed(() => trendMax.value > 0)
const trendBars = computed(() => {
  const max = trendMax.value
  return ast.value.trend.map((p) => ({
    ...p,
    h: max && p.count ? Math.max(6, Math.round((p.count / max) * 100)) : 0,
  }))
})
const trendFirst = computed(() => ast.value.trend[0]?.day || '')
const trendLast = computed(() => ast.value.trend[ast.value.trend.length - 1]?.day || '')
const recent7 = computed(() => ast.value.trend.slice(-7).reduce((sum, p) => sum + p.count, 0))

const keywordsTop = computed(() => ast.value.keywords.slice(0, 12))
const keywordMax = computed(() => keywordsTop.value[0]?.count || 0)

/* ---------------- 智能分析 ---------------- */
const insight = ref<CrisisInsight | null>(null)
const insightLoading = ref(false)
const insightError = ref(false)
/** 分析结果缓存时间：联动预警刷新后重新生成 */
let insightLoadedAt = 0

async function loadInsight(force = false) {
  if (insightLoading.value) return
  if (!force && insight.value && Date.now() - insightLoadedAt < 60_000) return
  insightLoading.value = true
  insightError.value = false
  try {
    insight.value = await getCrisisInsight(AST_DAYS)
    insightLoadedAt = Date.now()
  } catch {
    insight.value = null
    insightError.value = true
  } finally {
    insightLoading.value = false
  }
}

const insightTime = computed(() => {
  const raw = insight.value?.generated_at
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
})

/** 来自学生详情的闭环参数：?student_id= 只看该学生，?alert_id= 直接打开该条处置 */
const studentFilter = computed(() => Number(route.query.student_id) || null)
const alertFilter = Number(route.query.alert_id) || 0
const studentFilterName = computed(() => {
  if (!studentFilter.value) return ''
  const hit = alerts.value.find((a) => a.student_id === studentFilter.value)
  return hit?.student_name || `学生 #${studentFilter.value}`
})

const loading = ref(false)

/** 取数文案：交代在「读什么」，等待才不像卡死 */
const WB_TIPS = [
  '正在汇总各班的预警信号',
  '正在按处置进度归位',
  '快好了，正在排序',
]
const filter = ref<'all' | 'unresolved' | 'follow_up' | 'resolved'>('all')
/** 搜索与等级筛选：工作台头部搜索框 / 等级下拉共用 */
const search = ref('')
const levelFilter = ref<'all' | 'severe' | 'moderate' | 'mild'>('all')

const dialogVisible = ref(false)
const current = ref<CrisisAlert | null>(null)
const submitting = ref(false)
const form = ref({
  intervention_type: '谈话',
  intervention_note: '',
  follow_up_date: '',
  resolved: true,
})

/** 干预方式下拉选项（值与提交保持一致） */
const interventionOptions = [
  { value: '谈话', label: '谈话疏导' },
  { value: '约谈家长', label: '约谈家长' },
  { value: '转介心理咨询', label: '转介心理咨询' },
  { value: '其他', label: '其他' },
]

/** 今日日期（YYYY-MM-DD）：用于 AI 草稿 */
const today = new Date().toISOString().slice(0, 10)

/** AI 建议要点：随干预方式变化 */
const aiPoints = computed(() => {
  const t = form.value.intervention_type
  if (t === '约谈家长') return ['沟通对象与时间', '家长反馈', '家庭配合措施', '后续联系安排']
  if (t === '转介心理咨询') return ['转介事由', '预警等级', '学生知情情况', '咨询师反馈跟进']
  if (t === '其他') return ['处置方式说明', '学生情绪状态', '已采取措施', '后续随访计划']
  return ['学生情绪状态', '触发事件', '已采取措施', '后续随访计划']
})

/** AI 草稿：结合所选干预方式 + 学生 + 日期，写成处置记录口吻 */
const aiDraft = computed(() => {
  const s = current.value?.student_name || '该生'
  const t = form.value.intervention_type
  if (t === '约谈家长') {
    return `${today}，就${s}近期心理预警情况与其家长电话沟通：反馈其在课堂上的情绪表现与波动，说明学校的关注与跟进安排，请家长在家多加陪伴、留意异常信号并及时反馈。家长表示理解并愿意配合，双方约定保持联系、共同关注其状态。`
  }
  if (t === '转介心理咨询') {
    return `${today}，针对${s}的预警情况填写转介单并转介学校心理咨询中心：说明其预警等级与主要表现，请咨询师尽快安排面谈。已向学生本人说明转介原因，其愿意接受；后续由我配合跟踪咨询进展并做好记录。`
  }
  if (t === '其他') {
    return `${today}，针对${s}的预警情况采取其他处置措施：先了解事情经过与当下情绪，安抚并说明可提供的支持，记录其主要表现与后续安排，约定继续关注并及时反馈。`
  }
  return `${today}，与${s}进行一对一谈话疏导：先了解其近期压力来源与情绪状态，肯定其积极面，引导其识别情绪信号并尝试简单的放松方法。谈话后其情绪较前平稳，约定保持沟通并继续关注。`
})

const unresolved = computed(() => alerts.value.filter(a => !a.resolved))
const highRisk = computed(() => alerts.value.filter(a => !a.resolved && a.level === 'severe'))
const followingUp = computed(() => alerts.value.filter(a => !a.resolved && a.follow_up_date).length)
const closedCount = computed(() => alerts.value.filter(a => a.resolved).length)

/** 随访日期已到期且未闭环 */
function isFollowUpDue(row: CrisisAlert) {
  if (row.resolved || !row.follow_up_date) return false
  return row.follow_up_date <= new Date().toISOString().slice(0, 10)
}
const followUpDue = computed(() => alerts.value.filter(isFollowUpDue))

function daysUntil(date: string) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return Math.round((d.getTime() - today.getTime()) / 86400000)
}
function deadlineLabel(days: number) {
  if (days < 0) return `已逾期 ${-days} 天`
  if (days === 0) return '今日到期'
  return `${days} 天后`
}
function deadlinePct(days: number) {
  if (days <= 0) return 100
  return Math.max(12, Math.min(100, 100 - days * 8))
}

/** 处置时限条：未闭环且有随访日期，按到期时间由近到远 */
const deadlineItems = computed(() =>
  alerts.value
    .filter(a => !a.resolved && a.follow_up_date)
    .map(a => ({ id: a.id, name: a.student_name, date: a.follow_up_date as string, days: daysUntil(a.follow_up_date as string) }))
    .sort((x, y) => x.days - y.days)
    .slice(0, 5),
)

const filtered = computed(() => {
  let base = studentFilter.value
    ? alerts.value.filter((a) => a.student_id === studentFilter.value)
    : [...alerts.value]
  if (filter.value === 'unresolved') base = base.filter((a) => !a.resolved)
  if (filter.value === 'follow_up') base = base.filter(isFollowUpDue)
  if (filter.value === 'resolved') base = base.filter((a) => a.resolved)
  if (levelFilter.value !== 'all') base = base.filter((a) => a.level === levelFilter.value)
  const q = search.value.trim()
  if (q) {
    base = base.filter((a) =>
      [a.student_name, a.summary, a.keywords_matched].some((v) => v && String(v).includes(q))
    )
  }
  return base
})

/* 分页（契约第 2 节统一） */
const currentPage = ref(1)
const pageSize = ref(10)
const paged = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})
function handleSizeChange() {
  currentPage.value = 1
}
function handlePageChange() {
  /* 页码由 v-model 同步，无需额外处理 */
}
watch([filter, studentFilter, search, levelFilter], () => { currentPage.value = 1 })
watch(() => filtered.value.length, () => { currentPage.value = 1 })

/** 今日待办：未闭环按「随访剩余天数 → 等级 → 创建时间」排序，最紧急的五条 */
const LEVEL_RANK: Record<string, number> = { severe: 0, moderate: 1, mild: 2, normal: 3 }
const ladder = computed(() => {
  const rank = (a: CrisisAlert) => (a.follow_up_date ? daysUntil(a.follow_up_date) : 9999)
  return [...unresolved.value].sort(
    (x, y) =>
      rank(x) - rank(y) ||
      (LEVEL_RANK[x.level] ?? 9) - (LEVEL_RANK[y.level] ?? 9) ||
      String(y.created_at).localeCompare(String(x.created_at))
  )
})
const ladderTop = computed(() => ladder.value.slice(0, 5))

/** 预警动态：按创建时间倒序取最近 4 条，用真实处置状态还原事件 */
const recentActivity = computed(() =>
  [...alerts.value]
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    .slice(0, 4)
    .map((a) => ({
      id: a.id,
      title: a.resolved ? `${a.student_name} 预警已闭环` : `${a.student_name} 触发${levelText(a.level)}预警`,
      desc: a.intervention_type
        ? `${a.intervention_type} · ${a.intervention_note || '已登记处置'}`
        : a.summary,
      time: formatMdTime(a.created_at),
      tone: a.resolved ? 'ok' : a.level === 'severe' ? 'bad' : a.level === 'moderate' ? 'warn' : 'brand',
    }))
)

/** 待办副标题：有随访计划优先写随访，否则写当前处置方式 */
function todoLabel(a: CrisisAlert) {
  if (a.follow_up_date) return '随访'
  if (a.intervention_type) return a.intervention_type
  return '待处置'
}
/** 待办右侧时限：逾期 / 今日 / N 天后 / 未排期 */
function dueText(a: CrisisAlert) {
  if (!a.follow_up_date) return '未排期'
  const d = daysUntil(a.follow_up_date)
  if (d < 0) return `逾期 ${-d} 天`
  if (d === 0) return '今日到期'
  return `${d} 天后`
}
function dueTone(a: CrisisAlert) {
  if (!a.follow_up_date) return ''
  const d = daysUntil(a.follow_up_date)
  if (d <= 0) return 'is-red'
  if (d <= 3) return 'is-warn'
  return ''
}

/** 清单状态文案：已闭环 / 随访中 / 待处置 */
function statusText(row: CrisisAlert) {
  if (row.resolved) return '已闭环'
  return row.follow_up_date ? '随访中' : '待处置'
}
function followText(row: CrisisAlert) {
  if (!row.follow_up_date) return '未排期'
  return `${row.follow_up_date.slice(5)} · ${deadlineLabel(daysUntil(row.follow_up_date))}`
}

function formatMdTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 回到清单并清除筛选 */
function goList() {
  filter.value = 'all'
  levelFilter.value = 'all'
  search.value = ''
  currentPage.value = 1
  document.getElementById('wb-list')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function resetFilters() {
  filter.value = 'all'
  levelFilter.value = 'all'
  search.value = ''
}

/** 清除学生维度的闭环过滤，回到全部预警 */
function clearStudentFilter() {
  const q = { ...route.query }
  delete q.student_id
  delete q.alert_id
  router.replace({ path: '/teacher/crisis', query: q })
}

/** 反向闭环：从预警回到该学生的成长档案 */
function gotoStudent(row: CrisisAlert) {
  router.push({ path: '/teacher/students', query: { student: String(row.student_id) } })
}

function levelText(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度', normal: '正常' }
  return map[level] || level || '未知'
}

const worstOverdue = computed(() =>
  [...followUpDue.value].sort(
    (x, y) => daysUntil(x.follow_up_date as string) - daysUntil(y.follow_up_date as string)
  )[0]
)
const worstOverdueDays = computed(() =>
  worstOverdue.value ? -daysUntil(worstOverdue.value.follow_up_date as string) : 0
)

function levelTagType(level: string): 'danger' | 'warning' | 'info' | 'success' {
  const map: Record<string, 'danger' | 'warning' | 'info' | 'success'> = {
    severe: 'danger', moderate: 'warning', mild: 'info', normal: 'success',
  }
  return map[level] || 'info'
}

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** 聚合分析：与列表并行拉取，失败时保留上一次数据、不阻塞预警清单 */
async function loadAnalytics() {
  try {
    analytics.value = await getCrisisAnalytics()
    // 指标更新后旧研判作废；若正停留在态势页，直接重新生成
    insightLoadedAt = 0
    if (mobileView.value === 'analytics') loadInsight(true)
  } catch {
    /* 静默：态势区块保持上一次数据或空态 */
  }
}

async function loadAlerts() {
  loading.value = true
  try {
    alerts.value = await getAlerts()
    // 来自学生详情的闭环：定位到具体预警并直接进入处置
    if (alertFilter) {
      const hit = alerts.value.find((a) => a.id === alertFilter)
      if (hit && !hit.resolved) openIntervene(hit)
    }
  } catch {
    ElMessage.error('预警加载失败')
  } finally {
    loading.value = false
  }
  loadAnalytics()
}

function openIntervene(row: CrisisAlert) {
  current.value = row
  form.value = {
    intervention_type: row.intervention_type || '谈话',
    intervention_note: row.intervention_note || '',
    follow_up_date: row.follow_up_date || '',
    resolved: true,
  }
  dialogVisible.value = true
  loadAdvice(false)
}

/** AI 处置建议：同一条预警只请求一次，可手动强制重新生成 */
const advice = ref<CrisisAdvice | null>(null)
const adviceLoading = ref(false)
let adviceForId = 0

async function loadAdvice(force: boolean) {
  if (!current.value) return
  if (!force && adviceForId === current.value.id && advice.value) return
  adviceForId = current.value.id
  advice.value = null
  adviceLoading.value = true
  try {
    advice.value = await getAlertAdvice(current.value.id)
  } catch {
    ElMessage.warning('AI 处置建议暂不可用')
  } finally {
    adviceLoading.value = false
  }
}

function applyAdvice() {
  if (!advice.value) return
  const match = interventionOptions.find((o) => o.label.includes(advice.value!.scheme) || advice.value!.scheme.includes(o.label))
  if (match) form.value.intervention_type = match.value
  if (!form.value.intervention_note) {
    form.value.intervention_note = advice.value.steps.join('；')
  }
  ElMessage.success('已按建议回填表单')
}

/** 按学生导出干预档案 Excel（默认全量；导出动作为脱敏内容并留审计） */
async function exportArchive(row: CrisisAlert) {
  try {
    const blob = await exportStudentCrisisArchive(row.student_id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `crisis-archive-${row.student_name}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('导出失败')
  }
}

async function submitIntervene() {
  if (!current.value) return
  submitting.value = true
  try {
    await interveneAlert(current.value.id, {
      intervention_type: form.value.intervention_type,
      intervention_note: form.value.intervention_note || undefined,
      follow_up_date: form.value.follow_up_date || undefined,
      resolved: form.value.resolved,
    })
    ElMessage.success('干预记录已保存')
    dialogVisible.value = false
    loadAlerts()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

async function handleResolve(row: CrisisAlert) {
  try {
    if (!(await actionConfirm(`确认将「${row.student_name}」的预警标记为已闭环？`, '闭环确认', { confirmButtonText: '确认闭环' }))) return
  } catch {
    return
  }
  try {
    await resolveAlert(row.id, true)
    ElMessage.success('已标记闭环')
    loadAlerts()
  } catch {
    ElMessage.error('操作失败')
  }
}

/** SSE 实时推送：teacher-crisis 域变更时自动刷新预警清单（不再依赖手动刷新）。
    severe/moderate 会同时收到站内强提醒，这里负责把工作台数据拉成最新。 */
let crisisSyncTimer: ReturnType<typeof setTimeout> | null = null
onDataChange(['teacher-crisis'], () => {
  if (crisisSyncTimer) return
  crisisSyncTimer = setTimeout(() => {
    crisisSyncTimer = null
    loadAlerts()
  }, 800)
})

onUnmounted(() => {
  if (crisisSyncTimer) {
    clearTimeout(crisisSyncTimer)
    crisisSyncTimer = null
  }
})

onMounted(loadAlerts)
</script>

<style scoped>
/* 本页视觉收敛到钉钉设计令牌（--dt-*，见 styles/dingtalk.css）：
   页面底色 #f2f3f5、白色圆角卡、发丝分割线、黑白灰为主，
   红色只用于高危/逾期，蓝色只出现在链接与图标小块。 */
.tui-page.dt-page { background: #f2f3f5; }
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* ================= 桌面端：工作台头部 ================= */
.dt-head {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 12px;
}
.dt-head-l h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.2px;
  color: var(--dt-text);
}
.dt-head-sub {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: var(--dt-text-tertiary);
}
.dt-head-sub b { color: var(--dt-danger); font-weight: 600; }
.dt-head-r {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dt-search { width: 250px; }
.dt-search :deep(.el-input__wrapper) {
  border-radius: 15px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--dt-divider) inset;
}
.dt-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--dt-primary) inset;
}
.dt-level { width: 108px; }
.dt-level :deep(.el-select__wrapper) {
  border-radius: 15px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--dt-divider) inset;
}

/* ================= 四张指标卡 ================= */
.dt-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.dt-kpi {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: var(--dt-surface);
  border-radius: var(--dt-radius-sm);
  box-shadow: var(--dt-shadow-1);
}
.dt-ic {
  width: 34px;
  height: 34px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}
.dt-ic.blue { background: #e8f3ff; color: #0070d9; }
.dt-ic.red { background: #ffece8; color: #d83931; }
.dt-ic.orange { background: #fff3e6; color: #d46b08; }
.dt-ic.green { background: #e8f5ee; color: #2e7d5b; }
.dt-kpi-bd span {
  display: block;
  font-size: 10.5px;
  color: var(--dt-text-tertiary);
}
.dt-kpi-bd b {
  display: block;
  margin-top: 2px;
  font-size: 21px;
  font-weight: 600;
  line-height: 1.15;
  color: var(--dt-text);
  font-variant-numeric: tabular-nums;
}

/* ================= 双卡：今日待办 / 预警动态 ================= */
.dt-cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 10px;
  margin-top: 10px;
}
.dt-card {
  background: var(--dt-surface);
  border-radius: var(--dt-radius-sm);
  box-shadow: var(--dt-shadow-1);
  overflow: hidden;
}
.dt-card-h {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 46px;
  padding: 0 14px;
  border-bottom: 1px solid var(--dt-divider);
}
.dt-card-h b {
  font-size: 13px;
  font-weight: 600;
  color: var(--dt-text);
}
.dt-card-sub { font-size: 10.5px; color: var(--dt-text-tertiary); }
.dt-more {
  margin-left: auto;
  padding: 2px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 10.5px;
  color: var(--dt-link);
  cursor: pointer;
}
.dt-more:hover { color: var(--dt-primary-strong); }

.dt-todo-i {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border: 0;
  background: var(--dt-surface);
  text-align: left;
  font: inherit;
  cursor: pointer;
  transition: background 0.15s var(--dt-ease);
}
.dt-todo-i + .dt-todo-i { border-top: 1px solid rgba(0, 0, 0, 0.04); }
.dt-todo-i:hover { background: #f7f8fa; }
.dt-todo-bd { flex: 1; min-width: 0; }
.dt-todo-bd b {
  display: block;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--dt-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-todo-bd span {
  display: block;
  margin-top: 2px;
  font-size: 10.5px;
  color: var(--dt-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-todo-date { flex: none; font-size: 10.5px; color: var(--dt-text-tertiary); }
.dt-todo-date.is-red { color: var(--dt-danger); font-weight: 600; }
.dt-todo-date.is-warn { color: var(--dt-warning); }

/* 等级 / 事件圆点：只做识别，不给整块上色 */
.dt-dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  background: #c9cdd4;
}
.dt-dot.lv-severe { background: var(--dt-danger); }
.dt-dot.lv-moderate { background: var(--dt-warning); }
.dt-dot.lv-mild { background: var(--dt-primary); }
.dt-dot.lv-normal { background: #2e7d5b; }
.dt-dot.tl-bad { background: var(--dt-danger); }
.dt-dot.tl-warn { background: var(--dt-warning); }
.dt-dot.tl-ok { background: #2e7d5b; }
.dt-dot.tl-brand { background: var(--dt-primary); }

.dt-tl-i {
  display: flex;
  gap: 9px;
  padding: 9px 14px;
}
.dt-tl-i + .dt-tl-i { border-top: 1px solid rgba(0, 0, 0, 0.04); }
.dt-tl-i .dt-dot { margin-top: 5px; }
.dt-tl-bd { flex: 1; min-width: 0; }
.dt-tl-bd b {
  display: block;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--dt-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-tl-bd span {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: var(--dt-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-tl-time {
  flex: none;
  font-size: 9.5px;
  color: var(--dt-text-tertiary);
  font-variant-numeric: tabular-nums;
}

/* ================= 预警清单：钉钉式表格行 ================= */
.dt-listcard { margin-top: 10px; }
.dt-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--dt-divider);
}
.dt-seg {
  display: flex;
  gap: 2px;
  padding: 2px;
  background: #f2f3f5;
  border-radius: 8px;
}
.dt-seg button {
  height: 26px;
  padding: 0 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  font: inherit;
  font-size: 11.5px;
  color: var(--dt-text-secondary);
  cursor: pointer;
  transition: background 0.15s var(--dt-ease), color 0.15s var(--dt-ease);
}
.dt-seg button.on {
  background: #fff;
  color: var(--dt-text);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.dt-reset {
  margin-left: auto;
  padding: 2px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 10.5px;
  color: var(--dt-text-tertiary);
  cursor: pointer;
}
.dt-reset:hover { color: var(--dt-text-secondary); }

.dt-lth,
.dt-li {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr) 76px 132px 150px;
  gap: 12px;
  align-items: center;
}
.dt-lth {
  height: 30px;
  padding: 0 14px;
  background: #fafbfc;
  border-bottom: 1px solid var(--dt-divider);
  font-size: 10px;
  color: var(--dt-text-tertiary);
}
.dt-li {
  padding: 9px 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  font-size: 11px;
  transition: background 0.15s var(--dt-ease);
}
.dt-li:hover { background: #f7f8fa; }
.dt-who {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.dt-avatar {
  width: 28px;
  height: 28px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  background: #f2f3f5;
  color: #4e5969;
}
.dt-avatar.lv-severe { background: #fdecee; color: #d83931; }
.dt-avatar.lv-moderate { background: #fdf3e3; color: #a9660f; }
.dt-avatar.lv-mild { background: #eaf1ff; color: #2f6df6; }
.dt-avatar.lv-normal { background: #eaf7ef; color: #2f855a; }
.dt-who-bd {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.dt-who-bd b {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--dt-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-who-bd em {
  flex: none;
  padding: 0 5px;
  height: 17px;
  display: inline-flex;
  align-items: center;
  border-radius: 3px;
  font-style: normal;
  font-size: 9.5px;
  background: #f2f3f5;
  color: var(--dt-text-secondary);
}
.dt-who-bd em.lv-severe { background: #fdecee; color: #d83931; }
.dt-who-bd em.lv-moderate { background: #fdf3e3; color: #a9660f; }
.dt-who-bd em.lv-mild { background: #eaf1ff; color: #2f6df6; }
.dt-who-bd em.lv-normal { background: #eaf7ef; color: #2f855a; }
.dt-sig {
  min-width: 0;
  color: var(--dt-text-tertiary);
  font-size: 10.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-st { font-size: 10.5px; color: var(--dt-text-secondary); }
.dt-st.done { color: #2e7d5b; }
.dt-fu { font-size: 10.5px; color: var(--dt-text-tertiary); }
.dt-fu.due { color: var(--dt-danger); font-weight: 600; }
.dt-ops {
  display: flex;
  justify-content: flex-end;
  gap: 2px;
}
.dt-op {
  padding: 2px 6px;
  border: 0;
  border-radius: 4px;
  background: none;
  font: inherit;
  font-size: 11px;
  color: var(--dt-link);
  cursor: pointer;
}
.dt-op:hover { background: var(--dt-primary-ghost); }
.dt-op:disabled {
  color: var(--dt-text-quiet);
  background: none;
  cursor: default;
}

.dt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 24px 14px;
  font-size: 11.5px;
  color: var(--dt-text-tertiary);
}
.dt-empty b { font-size: 12.5px; font-weight: 600; color: var(--dt-text-secondary); }

.dt-analytics { margin-top: 12px; }

/* 闭环：学生维度过滤提示条 */
.wb-scope {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 10px 14px;
  padding: 9px 12px;
  border-radius: var(--dt-radius-sm);
  background: #eef4ff;
  font-size: 12.5px;
}
.wb-scope-text { font-weight: 600; color: #1b4fd1; }
.wb-scope-clear {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: none;
  background: transparent;
  color: var(--dt-text-secondary);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.wb-scope-clear:hover { color: var(--dt-text); }

/* ================= 移动端：原生白色头部 + 白色卡片 ================= */
/* 头部保持 SubPageHeader 的白底规范，不在这里改色 */
.dtm-home { padding-bottom: 12px; }
.dtm-hero {
  margin: 10px 12px 0;
  padding: 14px;
  background: #fff;
  border-radius: 12px;
}
.dtm-hero-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.dtm-hero-top b { font-size: 13px; font-weight: 600; color: var(--dt-text); }
.dtm-hero-top span {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--dt-text-tertiary);
}
/* 四宫格指标：浅灰底卡片，红色只标注高危、橙色只标注逾期 */
.dtm-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 12px;
}
.dtm-kpi {
  text-align: center;
  padding: 9px 4px;
  border-radius: 8px;
  background: #f7f8fa;
  border: 1px solid #eff1f4;
}
.dtm-kpi b {
  display: block;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--dt-text);
  font-variant-numeric: tabular-nums;
}
.dtm-kpi b.risk { color: #d83931; }
.dtm-kpi b.warn { color: #d46b08; }
.dtm-kpi span {
  font-size: 9.5px;
  color: var(--dt-text-tertiary);
}

/* 待办卡：与指标卡同层白卡，不再压住头部 */
.dtm-sheet {
  position: relative;
  z-index: 2;
  margin: 10px 12px 0;
  padding: 12px 0 2px;
  background: #fff;
  border-radius: 12px;
}
.dtm-sh {
  display: flex;
  align-items: center;
  padding: 0 14px 8px;
}
.dtm-sh b { font-size: 13.5px; font-weight: 600; color: var(--dt-text); }
.dtm-sh span { margin-left: auto; font-size: 10.5px; color: var(--dt-text-tertiary); }

.dtm-over {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin: 0 14px 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff1f0;
  border: 1px solid #ffe0dc;
}
.dtm-over em {
  display: flex;
  align-items: center;
  gap: 4px;
  font-style: normal;
  font-size: 11.5px;
  font-weight: 600;
  color: #b52a22;
}
.dtm-over span {
  font-size: 10.5px;
  line-height: 1.5;
  color: #a34b44;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dtm-todo-i {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 14px;
  border: 0;
  background: #fff;
  text-align: left;
  font: inherit;
  cursor: pointer;
}
.dtm-todo-i + .dtm-todo-i { border-top: 1px solid #f2f3f5; }
.dtm-todo-i:active { background: #f7f8fa; }
.dtm-todo-bd { flex: 1; min-width: 0; }
.dtm-todo-bd b {
  display: block;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--dt-text);
}
.dtm-todo-bd span {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: var(--dt-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dtm-todo-date { flex: none; font-size: 10px; color: var(--dt-text-tertiary); }
.dtm-todo-date.is-red { color: var(--dt-danger); font-weight: 600; }
.dtm-todo-date.is-warn { color: var(--dt-warning); }
.dtm-more {
  display: block;
  width: 100%;
  padding: 10px 14px 12px;
  border: 0;
  border-top: 1px solid #f2f3f5;
  background: #fff;
  font: inherit;
  font-size: 11px;
  color: var(--dt-link);
  text-align: center;
  cursor: pointer;
}
.dtm-empty {
  padding: 18px 14px;
  text-align: center;
  font-size: 11.5px;
  color: var(--dt-text-tertiary);
}

/* 三宫格入口 */
.dtm-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin: 12px 12px 0;
  padding: 14px 6px;
  background: #fff;
  border-radius: 12px;
}
.dtm-gi {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  border: 0;
  background: none;
  font: inherit;
  cursor: pointer;
}
.dtm-gic {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  font-size: 12.5px;
  font-weight: 600;
  background: #e8f3ff;
  color: #0070d9;
}
.dtm-gic.orange { background: #fff3e6; color: #d46b08; }
.dtm-gic.green { background: #e8f5ee; color: #2e7d5b; }
.dtm-gi > span:last-child { font-size: 10.5px; color: #4e5969; }

.dtm-card {
  margin: 12px 12px 0;
  padding: 12px 0 2px;
  background: #fff;
  border-radius: 12px;
}
.dtm-tl-i {
  display: flex;
  gap: 9px;
  padding: 9px 14px;
}
.dtm-tl-i + .dtm-tl-i { border-top: 1px solid #f2f3f5; }
.dtm-tl-i .dt-dot { margin-top: 4px; }
.dtm-tl-bd { flex: 1; min-width: 0; }
.dtm-tl-bd b {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--dt-text);
}
.dtm-tl-bd span {
  display: block;
  margin-top: 2px;
  font-size: 10px;
  color: var(--dt-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dtm-tl-time {
  flex: none;
  font-size: 9.5px;
  color: var(--dt-text-tertiary);
  font-variant-numeric: tabular-nums;
}
.dtm-note {
  margin: 12px 14px 0;
  font-size: 10px;
  line-height: 1.6;
  color: #8a919c;
}

/* ================= 二级页：白色子页头 + 全屏右滑 ================= */
.cw-sub-scope { display: contents; }
.cw-sub-scope.is-open {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  flex-direction: column;
  background: #f2f3f5;
  animation: cwSubIn 0.28s cubic-bezier(0.22, 0.61, 0.36, 1);
}
@keyframes cwSubIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
.cw-subbar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  min-height: 56px;
  padding: calc(env(safe-area-inset-top) + 6px) 12px 8px;
  background: #fff;
  border-bottom: 1px solid var(--dt-divider);
  color: var(--dt-text);
}
.cw-subbar-back {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #1f2430;
  cursor: pointer;
}
.cw-subbar-back:active { background: rgba(20, 23, 26, 0.06); }
.cw-subbar-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.cw-subbar-main b {
  font-size: 16.5px;
  font-weight: 600;
  color: var(--dt-text);
  letter-spacing: -0.2px;
}
.cw-sub-scope.is-open .cw-sub-body {
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0 0 calc(18px + env(safe-area-inset-bottom));
  background: #f2f3f5;
}

/* 二级页满宽视图：复用页面本身底色，只在需要的地方铺白 */
.dtm-view { width: 100%; }
.dtm-view-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px 8px;
}
.dtm-view-h b { font-size: 13px; font-weight: 600; color: var(--dt-text); }
.dtm-view-h span { font-size: 10.5px; color: var(--dt-text-tertiary); }
.dtm-view-h-list {
  padding: 9px 14px;
  border-bottom: 1px solid var(--dt-divider);
  background: #fafbfc;
}
.dtm-view-tip {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  padding: 0 14px 10px;
  font-size: 10.5px;
  line-height: 1.55;
  color: #8a6d3b;
}

/* 处置时限行：满宽 + 发丝分隔，背景交给页面 */
.dtm-rows {
  background: transparent;
  border-top: 1px solid var(--dt-divider);
}
.dtm-row {
  padding: 12px 14px 14px;
  border-top: 1px solid var(--dt-divider);
}
.dtm-row:first-child { border-top: 0; }
.dtm-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.dtm-row-name { font-size: 13px; font-weight: 600; color: var(--dt-text); }
.dtm-row-date { font-size: 11px; color: var(--dt-text-tertiary); }
.dtm-row-date.is-due { color: var(--dt-danger); font-weight: 600; }
.dtm-row-sub {
  margin: 2px 0 8px;
  font-size: 10.5px;
  color: var(--dt-text-tertiary);
}

/* 清单筛选区：不做卡片，白底直接铺在页面上 */
.dtm-filter {
  padding: 10px 14px;
  background: #fff;
  border-bottom: 1px solid var(--dt-divider);
}
/* 两列网格：搜索框占剩余宽度，等级选择固定 108px，避免挤压 */
.dtm-subsearch {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 108px;
  gap: 8px;
  margin: 0 0 8px;
}
.dtm-subsearch :deep(.el-input) { width: 100%; min-width: 0; }
.dtm-subsearch :deep(.el-input__wrapper),
.dtm-sublevel :deep(.el-select__wrapper) {
  border-radius: 9px;
  background: #f2f3f5;
  box-shadow: none;
}
.dtm-sublevel :deep(.el-select__wrapper) { padding: 0 8px; }
.dtm-sublevel { width: 100%; min-width: 0; }
.dtm-filter .wb-seg { margin-bottom: 0; }
.dtm-filter .wb-scope { margin: 8px 0 0; }
.dtm-pagination {
  padding: 12px 14px;
  background: #fff;
  border-top: 1px solid #f0f2f5;
}

/* ================= 处置态势（移动端自研分段视图） ================= */
.dtm-ast { padding-bottom: 10px; }

/* 顶部数据带：带分隔线的指标带，不套卡片 */
.dtm-ast-hero {
  padding: 14px;
  border-bottom: 1px solid var(--dt-divider);
}
.dtm-ast-hero-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.dtm-ast-hero-top b { font-size: 13px; font-weight: 600; color: var(--dt-text); }
.dtm-ast-hero-top span { font-size: 10.5px; color: var(--dt-text-tertiary); }
.dtm-ast-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 12px;
}
.dtm-ast-kpis > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-left: 10px;
  border-left: 1px solid var(--dt-divider);
}
.dtm-ast-kpis > div:first-child { padding-left: 0; border-left: 0; }
.dtm-ast-kpis b {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--dt-text);
  font-variant-numeric: tabular-nums;
}
.dtm-ast-kpis b.risk { color: var(--dt-danger); }
.dtm-ast-kpis span {
  font-size: 10px;
  color: var(--dt-text-tertiary);
  white-space: nowrap;
}

/* 分段：每段一条发丝线，背景沿用页面本身 */
.dtm-ast-sec { padding: 14px; border-top: 1px solid var(--dt-divider); }
.dtm-ast-hero + .dtm-ast-sec { border-top: 0; }
.dtm-ast-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.dtm-ast-h b {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--dt-text);
}
.dtm-ast-h > span { font-size: 10.5px; color: var(--dt-text-tertiary); }
.dtm-ast-badge {
  height: 15px;
  padding: 0 4px;
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  background: #e8f3ff;
  color: #0070d9;
  font-size: 9.5px;
  font-style: normal;
  font-weight: 700;
  letter-spacing: 0.4px;
}
.dtm-ast-refresh {
  flex: none;
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--dt-divider-strong);
  border-radius: 6px;
  background: transparent;
  font: inherit;
  font-size: 10.5px;
  color: #4e5969;
  cursor: pointer;
}
.dtm-ast-refresh:active { background: #eef0f3; }
.dtm-ast-refresh:disabled { opacity: 0.5; cursor: default; }

/* 智能分析正文 */
.dtm-ast-sum { margin: 0; font-size: 12.5px; line-height: 1.7; color: #2f3542; }
.dtm-ast-advice {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}
.dtm-ast-advice li {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 12px;
  line-height: 1.55;
  color: #4e5969;
}
.dtm-ast-advice i {
  flex: none;
  width: 16px;
  height: 16px;
  margin-top: 1px;
  display: grid;
  place-items: center;
  border-radius: 4px;
  background: #f2f3f5;
  font-size: 9.5px;
  font-style: normal;
  font-weight: 600;
  color: #8a919c;
}
.dtm-ast-src { margin: 10px 0 0; font-size: 9.5px; color: #a3a9b4; }
.dtm-ast-fail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0 2px;
  font-size: 11.5px;
  color: var(--dt-text-tertiary);
}
.dtm-ast-fail button {
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  font-size: 11.5px;
  color: var(--dt-link);
  cursor: pointer;
}

/* 等级构成：分段条 + 双列图例 */
.dtm-ast-stack {
  display: flex;
  height: 7px;
  overflow: hidden;
  border-radius: 4px;
  background: #e9ebef;
}
.dtm-ast-legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px 14px;
  margin-top: 10px;
}
.dtm-ast-legend > div { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #6a7280; }
.dtm-ast-legend i { flex: none; width: 6px; height: 6px; border-radius: 50%; }
.dtm-ast-legend b {
  margin-left: auto;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--dt-text);
  font-variant-numeric: tabular-nums;
}
.dtm-ast-legend em {
  width: 32px;
  text-align: right;
  font-style: normal;
  font-size: 10px;
  color: #a3a9b4;
  font-variant-numeric: tabular-nums;
}

/* 处置阶段 */
.dtm-ast-stage { display: flex; flex-direction: column; gap: 10px; }
.dtm-ast-stage-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 11px;
  color: #6a7280;
}
.dtm-ast-stage-top b {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--dt-text);
  font-variant-numeric: tabular-nums;
}
.dtm-ast-track { height: 5px; overflow: hidden; border-radius: 3px; background: #e9ebef; }
.dtm-ast-track span { display: block; height: 100%; transition: width 0.35s ease; }
.dtm-ast-track .is-found { background: #8f959e; }
.dtm-ast-track .is-intervened { background: #2f6df6; }
.dtm-ast-track .is-following { background: #d46b08; }
.dtm-ast-track .is-closed { background: #2e7d5b; }

/* 预警趋势：柱状条，零值只留底座 */
.dtm-ast-trend { display: flex; align-items: flex-end; gap: 2px; height: 82px; }
.dtm-ast-bar {
  flex: 1;
  min-width: 0;
  min-height: 2px;
  border-radius: 2px 2px 0 0;
  background: #1677ff;
  opacity: 0.7;
}
.dtm-ast-bar.zero { background: #e3e5e9; opacity: 1; }
.dtm-ast-bar.hot { background: #d92d20; opacity: 1; }
.dtm-ast-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 9.5px;
  color: #a3a9b4;
  font-variant-numeric: tabular-nums;
}

/* 敏感词 */
.dtm-ast-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.dtm-ast-chips span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border: 1px solid var(--dt-divider-strong);
  border-radius: 6px;
  background: #fff;
  font-size: 11px;
  color: #4e5969;
}
.dtm-ast-chips i { font-style: normal; font-size: 9.5px; color: #a3a9b4; }
.dtm-ast-chips span.hot { border-color: #f3cdd1; background: #fdf2f3; color: #b3261e; }
.dtm-ast-chips span.hot i { color: #c98a90; }
.dtm-ast-empty { padding: 6px 0 2px; font-size: 11.5px; color: var(--dt-text-tertiary); }
.dtm-ast-note { margin: 10px 0 0; font-size: 9.5px; color: #a3a9b4; }

/* ================= 移动端清单 ================= */
.fu-due { color: var(--tui-warn); font-weight: 600; }
/* 清单直接满宽铺排，不做圆角卡片 */
.cw2-list {
  display: flex;
  flex-direction: column;
  margin: 0;
  background: #fff;
  border: 0;
  border-radius: 0;
}
.cw2-item { border-top: 1px solid #f0f2f5; }
.cw2-item:first-child { border-top: 0; }
.cw2-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  background: transparent;
  border: 0;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.cw2-row:active { background: #f7f8fa; }
.cw2-avatar {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #3a4252;
  background: #f2f3f5;
}
/* 等级识别直接挂在头像上，避免整行再套一层卡片描边 */
.cw2-item.lv-severe .cw2-avatar { background: #fdecee; color: #c0313f; }
.cw2-item.lv-moderate .cw2-avatar { background: #fdf3e3; color: #a9660f; }
.cw2-item.lv-mild .cw2-avatar { background: #eaf1ff; color: #2f6df6; }
.cw2-item.lv-normal .cw2-avatar { background: #eaf7ef; color: #2f855a; }
.cw2-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cw2-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 13.5px;
  font-weight: 650;
  color: var(--dt-text);
}
.cw2-lv {
  padding: 0 6px;
  height: 17px;
  display: inline-flex;
  align-items: center;
  border-radius: 5px;
  font-size: 10.5px;
  font-weight: 600;
  background: #f2f3f5;
  color: #5b6472;
}
.cw2-state { font-size: 10.5px; color: #8a91a0; }
.cw2-state.done { color: #2f855a; }
.cw2-sum {
  font-size: 12px;
  line-height: 1.5;
  color: #5b6472;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.cw2-meta { font-size: 11px; color: #98a0ad; }
.cw2-chevron { color: #b8bfcc; transition: transform 0.18s ease; flex-shrink: 0; }
.cw2-chevron.open { transform: rotate(180deg); }
.cw2-expand {
  padding: 0 14px 12px;
  background: #f7f8fa;
  border-top: 1px solid #f0f2f5;
}
.cw2-note {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 10px 0 0;
  padding: 0;
  font-size: 12px;
  color: #5b6472;
}
.cw2-note b { font-size: 12px; font-weight: 650; color: #2f855a; }
.cw2-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.cw2-btn {
  flex: 1;
  min-width: 72px;
  height: 34px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid var(--dt-divider-strong);
  background: #fff;
  color: #3a4252;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.cw2-btn:active { background: #f2f3f5; }
.cw2-btn:disabled { opacity: 0.45; cursor: default; }
.cw2-btn-main { background: #1f2430; border-color: #1f2430; color: #fff; }
.cw2-btn-main:active { background: #333a48; }

/* ================= 干预弹窗 ================= */
.stu-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tui-brand-strong);
  font-size: 13px;
  font-weight: 600;
  background: var(--tui-brand-soft);
  flex-shrink: 0;
}
.wb-ctx {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
}
.wb-ctx-head { display: flex; align-items: center; gap: 8px; }
.wb-ctx-name { font-weight: 600; color: var(--tui-text); }
.wb-ctx-time { margin-left: auto; font-size: 11px; color: var(--tui-text-quiet); }
.wb-ctx-summary {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-secondary);
}
.wb-ctx-kw { font-size: 11.5px; color: var(--tui-text-quiet); }
.wb-draft { margin-bottom: 14px; }

/* AI 处置建议卡 */
.wb-advice { border: 1px solid #b5d4f4; background: var(--tui-surface, #f4f8fd); border-radius: 10px; padding: 10px 12px; margin-bottom: 14px; }
.wb-advice-head { display: flex; justify-content: space-between; align-items: center; }
.wb-advice-head b { font-size: 12.5px; }
.wb-advice-btn { border: none; background: none; color: var(--tui-brand, #185FA5); font-size: 12px; cursor: pointer; padding: 2px 4px; }
.wb-advice-btn:disabled { opacity: .6; cursor: default; }
.wb-advice-scheme { font-size: 13px; font-weight: 600; margin: 6px 0 4px; }
.wb-advice-steps { margin: 0 0 6px; padding-left: 18px; font-size: 12px; color: var(--tui-text-main, #333); }
.wb-advice-steps li { margin: 2px 0; }
.wb-advice-why { font-size: 11.5px; color: var(--tui-text-quiet); margin: 4px 0; }
.wb-advice-taboo { font-size: 11.5px; color: #A32D2D; margin: 4px 0; }
.wb-advice-apply { border: none; border-radius: 6px; background: var(--tui-brand, #185FA5); color: #fff; font-size: 12px; padding: 5px 10px; cursor: pointer; margin-right: 8px; }
.wb-advice-src { font-size: 11px; color: var(--tui-text-quiet); }
</style>
