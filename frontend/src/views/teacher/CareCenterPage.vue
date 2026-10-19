﻿﻿﻿<template>
  <div class="tui-page">
    <SubPageHeader title="人文关怀中心" sub="关怀温度 · 家访台账 · 正向激励" fallback="/teacher" />

    <div class="tui-content">
      <!-- 桌面端特色头部：关怀语义色 + 太阳图标；右侧挂本月三类台账的条数 -->
      <TuiPageHero
        v-if="!isMobile"
        title="人文关怀中心"
        sub="让关心有温度、有记录：关怀温度 · 家访台账 · 正向激励"
        :icon="Sunny"
        tone="success"
      >
        <div class="tui-hero-metric is-accent"><b>{{ overview.event_count }}</b><span>关怀事项</span></div>
        <div class="tui-hero-metric"><b>{{ overview.visit_count }}</b><span>家访</span></div>
        <div class="tui-hero-metric"><b>{{ overview.praise_count }}</b><span>正向激励</span></div>
        <el-button size="small" round :icon="Refresh" :loading="genLoading" @click="handleGenerate">自动生成</el-button>
      </TuiPageHero>

      <!-- 桌面端专属骨架：三列台账卡片流 + 顶部横向概览带。
           为什么这样改：本页核心是「三类关怀台账并行」，三列同屏比 Tab 切换更接近台账看板；
           温度块抽成横跨三列的概览带，先给全局体感，再逐列处理明细。 -->
      <template v-if="!isMobile">
        <!-- 横向概览带：温度百分比 + 温度进度条 + 待回访提醒 + 温度等级 -->
        <section
          class="cc-band"
          title="温度由本月「关怀事项 + 家访 + 激励」数量综合推算，待处理事项越多温度越低；用来提示哪些学生需要多一分关心。"
        >
          <div class="cc-band-temp">
            <span class="cc-band-label">本月关怀温度</span>
            <span class="cc-temp-num">{{ careScore }}<i>%</i></span>
          </div>
          <div class="tui-progress-track cc-band-bar">
            <span class="tui-progress-fill" :style="{ '--pct': careScore / 100, background: tempColor }" />
          </div>
          <div class="cc-remind cc-band-remind" :class="remindTone">
            <el-icon><Bell /></el-icon>
            <span class="cc-remind-text">
              <template v-if="pendingCount || followUpCount">
                待回访提醒：<b>{{ pendingCount }}</b> 项关怀事项待处理<template v-if="followUpCount">，<b>{{ followUpCount }}</b> 条家访待跟进</template>
              </template>
              <template v-else>本月关怀事项均已跟进，暂无待回访</template>
            </span>
            <button v-if="pendingCount || followUpCount" class="cc-remind-go" type="button" @click="goFollowUp">去处理</button>
          </div>
          <span class="cc-temp-level" :class="`lv-${tempLevel.tone}`">{{ tempLevel.label }}</span>
        </section>

        <!-- 闭环聚焦条：与移动端同一份逻辑，桌面端保留上下文提示 -->
        <div v-if="studentFocus" class="cc-focus">
          <el-icon :size="14"><User /></el-icon>
          <span class="cc-focus-text">已聚焦学生「{{ studentFocus.name || '该生' }}」，仅显示其关怀记录</span>
          <button class="cc-focus-link" type="button" @click="gotoStudent">成长档案</button>
          <button class="cc-focus-clear" type="button" @click="clearStudentFocus">清除</button>
        </div>

        <!-- 三列台账卡片流：关怀事项 / 家访台账 / 正向激励，等宽并排、各自分页与限高滚动 -->
        <div ref="boardRef" class="cc-board">
          <!-- 第一列：关怀事项 -->
          <section class="tui-section cc-col cc-col-events">
            <div class="tui-section-head">
              <h3><el-icon><ChatDotRound /></el-icon>关怀事项</h3>
              <div class="tui-section-extra">
                <span class="cc-count">{{ shownEvents.length }} 条</span>
                <el-button class="cc-add" size="small" :icon="Plus" @click="eventVisible = true">新增</el-button>
              </div>
            </div>
            <div class="cc-col-body tui-scroll-hidden">
              <div v-if="!shownEvents.length" class="tui-empty">
                <span class="tui-empty-icon"><el-icon :size="22"><Calendar /></el-icon></span>
                <span class="tui-empty-title">本月暂无关怀事项</span>
                <span class="tui-empty-desc">点「自动生成」或手动新增一条</span>
              </div>
              <div v-else class="cc-tl">
                <div v-for="e in pagedEvents" :key="e.id" class="cc-tl-item">
                  <span class="cc-tl-node" :class="`tone-${eventTone(e.event_type)}`"><el-icon><ChatDotRound /></el-icon></span>
                  <div class="cc-tl-card">
                    <div class="cc-tl-top">
                      <span class="tui-tag" :class="tagClass(e.event_type)">{{ CARE_EVENT_LABEL[e.event_type] }}</span>
                      <span class="cc-tl-title">{{ e.title }}</span>
                      <el-tag v-if="e.auto_generated" size="small" effect="plain" round>自动</el-tag>
                    </div>
                    <div class="cc-tl-meta">
                      <span v-if="e.student_name">{{ e.student_name }}</span>
                      <span>{{ e.event_date }}</span>
                      <button class="cc-link cc-link-danger" @click="removeEvent(e)">删除</button>
                    </div>
                  </div>
                </div>
                <div v-if="shownEvents.length > pageSizeEvents" class="pagination-wrapper">
                  <el-pagination
                    v-model:current-page="pageEvents"
                    v-model:page-size="pageSizeEvents"
                    :page-sizes="[10, 20, 50]"
                    :total="shownEvents.length"
                    :pager-count="5"
                    small
                    background
                    layout="total, prev, pager, next"
                    @size-change="handleEventsSizeChange"
                    @current-change="handleEventsCurrentChange"
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- 第二列：家访台账 -->
          <section class="tui-section cc-col cc-col-visits">
            <div class="tui-section-head">
              <h3><el-icon><HomeFilled /></el-icon>家访台账</h3>
              <div class="tui-section-extra">
                <span class="cc-count">{{ shownVisits.length }} 条</span>
                <el-button class="cc-add" size="small" :icon="Plus" @click="visitVisible = true">新增</el-button>
              </div>
            </div>
            <div class="cc-col-body tui-scroll-hidden">
              <div v-if="!shownVisits.length" class="tui-empty">
                <span class="tui-empty-icon"><el-icon :size="22"><HomeFilled /></el-icon></span>
                <span class="tui-empty-title">暂无家访记录</span>
                <span class="tui-empty-desc">记录每次家访与沟通，形成可追溯的台账</span>
              </div>
              <div v-else class="cc-tl">
                <div v-for="v in pagedVisits" :key="v.id" class="cc-tl-item">
                  <span class="cc-tl-node tone-brand"><el-icon><HomeFilled /></el-icon></span>
                  <div class="cc-tl-card">
                    <div class="cc-tl-top">
                      <span class="tui-tag tui-tag-brand">{{ VISIT_METHOD_LABEL[v.method] }}</span>
                      <span class="cc-tl-title">{{ v.student_name }}</span>
                      <span class="cc-tl-date">{{ v.visit_date }}</span>
                    </div>
                    <div class="cc-tl-body">{{ v.content }}</div>
                    <div v-if="v.follow_up" class="cc-tl-follow">后续：{{ v.follow_up }}</div>
                    <div class="cc-tl-meta">
                      <button class="cc-link cc-link-danger" @click="removeVisit(v)">删除</button>
                    </div>
                  </div>
                </div>
                <div v-if="shownVisits.length > pageSizeVisits" class="pagination-wrapper">
                  <el-pagination
                    v-model:current-page="pageVisits"
                    v-model:page-size="pageSizeVisits"
                    :page-sizes="[10, 20, 50]"
                    :total="shownVisits.length"
                    :pager-count="5"
                    small
                    background
                    layout="total, prev, pager, next"
                    @size-change="handleVisitsSizeChange"
                    @current-change="handleVisitsCurrentChange"
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- 第三列：正向激励 -->
          <section class="tui-section cc-col cc-col-praises">
            <div class="tui-section-head">
              <h3><el-icon><Star /></el-icon>正向激励</h3>
              <div class="tui-section-extra">
                <span class="cc-count">{{ shownPraises.length }} 条</span>
                <el-button class="cc-add" size="small" :icon="Plus" @click="praiseVisible = true">新增</el-button>
              </div>
            </div>
            <div class="cc-col-body tui-scroll-hidden">
              <div v-if="!shownPraises.length" class="tui-empty">
                <span class="tui-empty-icon"><el-icon :size="22"><Star /></el-icon></span>
                <span class="tui-empty-title">暂无激励记录</span>
                <span class="tui-empty-desc">及时表扬与发放徽章，让正向反馈被看见</span>
              </div>
              <div v-else class="cc-tl">
                <div v-for="p in pagedPraises" :key="p.id" class="cc-tl-item">
                  <span class="cc-tl-node tone-success"><el-icon><Star /></el-icon></span>
                  <div class="cc-tl-card">
                    <div class="cc-tl-top">
                      <span class="tui-tag tui-tag-success">{{ p.badge_name || PRAISE_TYPE_LABEL[p.praise_type] }}</span>
                      <span class="cc-tl-title">{{ p.student_name }}</span>
                      <span class="cc-tl-date">{{ p.occurred_on }}</span>
                    </div>
                    <div class="cc-tl-body">{{ p.reason }}</div>
                    <div class="cc-tl-meta">
                      <button class="cc-link cc-link-danger" @click="removePraise(p)">删除</button>
                    </div>
                  </div>
                </div>
                <div v-if="shownPraises.length > pageSizePraises" class="pagination-wrapper">
                  <el-pagination
                    v-model:current-page="pagePraises"
                    v-model:page-size="pageSizePraises"
                    :page-sizes="[10, 20, 50]"
                    :total="shownPraises.length"
                    :pager-count="5"
                    small
                    background
                    layout="total, prev, pager, next"
                    @size-change="handlePraisesSizeChange"
                    @current-change="handlePraisesCurrentChange"
                  />
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- 关怀日历：月度网格无法塞进窄列，桌面端独占一行保留（功能不删） -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><Calendar /></el-icon>关怀日历</h3>
            <div class="tui-section-extra">
              <el-button text circle @click="shiftMonth(-1)"><el-icon><ArrowLeft /></el-icon></el-button>
              <span class="cc-cal-title">{{ calYear }} 年 {{ calMonth }} 月</span>
              <el-button text circle @click="shiftMonth(1)"><el-icon><ArrowRight /></el-icon></el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>按天查看本月关怀安排；点「自动生成」可按学生生日、困难情况与学业预警自动铺排事项。</span>
          </div>
          <div class="cc-week">
            <span v-for="w in WEEK_LABELS" :key="w">{{ w }}</span>
          </div>
          <div class="cc-grid">
            <div v-for="(cell, i) in calendarCells" :key="i" class="cc-cell"
              :class="{ muted: !cell.inMonth, today: cell.isToday }">
              <div class="cc-cell-top">
                <span class="cc-day">{{ cell.day }}</span>
                <span v-if="cell.events.length" class="cc-dot-count">{{ cell.events.length }}</span>
              </div>
              <div class="cc-cell-events">
                <span v-for="e in cell.events.slice(0, 2)" :key="e.id" class="cc-chip"
                  :class="`tone-${eventTone(e.event_type)}`"
                  :title="e.title">{{ e.title }}</span>
                <span v-if="cell.events.length > 2" class="cc-more">+{{ cell.events.length - 2 }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 求助受理：独立的帮扶闭环，不属三类台账，桌面端保留为独立分区 -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><ChatDotRound /></el-icon>求助受理</h3>
            <div class="tui-section-extra">
              <span class="cc-count">{{ shownHelp.length }} 条</span>
              <el-button class="cc-add" size="small" :icon="Refresh" @click="loadHelp">刷新</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>学生提交的求助会汇总到这里；「待受理」请尽快响应，回复即形成帮扶闭环。匿名求助不显示学生姓名，但仍可正常回复。</span>
          </div>
          <div class="cc-help-stats">
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === '' }" @click="helpStatusFilter = ''">
              <b>{{ helpOverview.total }}</b><span>全部</span>
            </button>
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === 'pending' }" @click="helpStatusFilter = 'pending'">
              <b>{{ helpOverview.pending }}</b><span>待受理</span>
            </button>
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === 'processing' }" @click="helpStatusFilter = 'processing'">
              <b>{{ helpOverview.processing }}</b><span>帮扶中</span>
            </button>
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === 'resolved' }" @click="helpStatusFilter = 'resolved'">
              <b>{{ helpOverview.resolved }}</b><span>已帮助</span>
            </button>
          </div>
          <div v-if="!shownHelp.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><ChatDotRound /></el-icon></span>
            <span class="tui-empty-title">暂无求助</span>
            <span class="tui-empty-desc">学生提交求助后会出现在这里</span>
          </div>
          <div v-else class="cc-help-list">
            <div v-for="h in shownHelp" :key="h.id" class="cc-help-item" :class="`st-${h.status}`">
              <div class="cc-help-top">
                <span class="cc-help-name">{{ h.anonymous ? '匿名同学' : (h.student_name || '学生') }}</span>
                <span class="tui-tag" :class="helpCatClass(h.category)">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
                <span class="cc-help-status" :class="`st-${h.status}`">{{ HELP_STATUS_LABEL[h.status] }}</span>
                <span class="cc-help-time">{{ (h.created_at || '').slice(5, 16) }}</span>
              </div>
              <div class="cc-help-body">{{ h.content }}</div>
              <div v-if="h.reply" class="cc-help-reply">
                <span class="cc-help-reply-label">我的回复</span>
                <span class="cc-help-reply-text">{{ h.reply }}</span>
              </div>
              <div class="cc-help-meta">
                <button v-if="!h.anonymous && h.student_id" class="cc-link" @click="gotoStudentById(h.student_id)">成长档案</button>
                <button class="cc-link cc-help-do" @click="openReply(h)">{{ h.reply ? '再次回复' : '受理并回复' }}</button>
              </div>
            </div>
          </div>
        </section>
      </template>
      <template v-else>
      <!-- 移动端高频操作：自动生成；求助受理随对应分区头部 -->
      <div v-if="isMobile" class="tui-actions cc-mobile-ops">
        <el-button size="small" round :icon="Refresh" :loading="genLoading" @click="handleGenerate">自动生成</el-button>
      </div>

      <!-- 关怀温度：温度进度条 + 待回访提醒条 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Sunny /></el-icon>本月关怀温度</h3>
          <div class="tui-section-extra">
            <span class="cc-temp-level" :class="`lv-${tempLevel.tone}`">{{ tempLevel.label }}</span>
          </div>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>温度由本月「关怀事项 + 家访 + 激励」数量综合推算，待处理事项越多温度越低，用来提示哪些学生需要多一分关心。</span>
        </div>
        <div class="cc-temp">
          <span class="cc-temp-num">{{ careScore }}<i>%</i></span>
          <div class="tui-progress-track">
            <span class="tui-progress-fill" :style="{ '--pct': careScore / 100, background: tempColor }" />
          </div>
        </div>
        <div class="cc-remind" :class="remindTone">
          <el-icon><Bell /></el-icon>
          <span class="cc-remind-text">
            <template v-if="pendingCount || followUpCount">
              待回访提醒：<b>{{ pendingCount }}</b> 项关怀事项待处理<template v-if="followUpCount">，<b>{{ followUpCount }}</b> 条家访待跟进</template>
            </template>
            <template v-else>本月关怀事项均已跟进，暂无待回访</template>
          </span>
          <button v-if="pendingCount || followUpCount" class="cc-remind-go" type="button" @click="goFollowUp">去处理</button>
        </div>
      </section>

      <!-- 闭环：从学生成长档案聚焦该生关怀记录 -->
      <div v-if="studentFocus" class="cc-focus">
        <el-icon :size="14"><User /></el-icon>
        <span class="cc-focus-text">已聚焦学生「{{ studentFocus.name || '该生' }}」，仅显示其关怀记录</span>
        <button class="cc-focus-link" type="button" @click="gotoStudent">成长档案</button>
        <button class="cc-focus-clear" type="button" @click="clearStudentFocus">清除</button>
      </div>

      <div class="tui-seg-wrap">
        <TuiSegmented
          v-model="tab"
          :options="[
            { value: 'calendar', label: '关怀日历', count: shownEvents.length },
            { value: 'visits', label: '家访记录', count: shownVisits.length },
            { value: 'praises', label: '正向激励', count: shownPraises.length },
            { value: 'help', label: '求助受理', count: helpOverview.pending },
          ]"
        />
      </div>

      <!-- 关怀日历 -->
      <template v-if="tab === 'calendar'">
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><Calendar /></el-icon>关怀日历</h3>
            <div class="tui-section-extra">
              <el-button text circle @click="shiftMonth(-1)"><el-icon><ArrowLeft /></el-icon></el-button>
              <span class="cc-cal-title">{{ calYear }} 年 {{ calMonth }} 月</span>
              <el-button text circle @click="shiftMonth(1)"><el-icon><ArrowRight /></el-icon></el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>按天查看本月关怀安排；点「自动生成」可按学生生日、困难情况与学业预警自动铺排事项。</span>
          </div>
          <div class="cc-week">
            <span v-for="w in WEEK_LABELS" :key="w">{{ w }}</span>
          </div>
          <div class="cc-grid">
            <div v-for="(cell, i) in calendarCells" :key="i" class="cc-cell"
              :class="{ muted: !cell.inMonth, today: cell.isToday }">
              <div class="cc-cell-top">
                <span class="cc-day">{{ cell.day }}</span>
                <span v-if="cell.events.length" class="cc-dot-count">{{ cell.events.length }}</span>
              </div>
              <div class="cc-cell-events">
                <span v-for="e in cell.events.slice(0, 2)" :key="e.id" class="cc-chip"
                  :class="`tone-${eventTone(e.event_type)}`"
                  :title="e.title">{{ e.title }}</span>
                <span v-if="cell.events.length > 2" class="cc-more">+{{ cell.events.length - 2 }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 谈心 / 关怀事项时间轴 -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><ChatDotRound /></el-icon>谈心关怀时间轴</h3>
            <div class="tui-section-extra">
              <span class="cc-count">{{ shownEvents.length }} 条</span>
              <el-button class="cc-add" size="small" :icon="Plus" @click="eventVisible = true">新增事项</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>谈心、陪伴、困难帮扶等关怀事项按时间倒序排列；「学业预警」需优先跟进。</span>
          </div>
          <div v-if="!shownEvents.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><Calendar /></el-icon></span>
            <span class="tui-empty-title">本月暂无关怀事项</span>
            <span class="tui-empty-desc">点击「自动生成」按学生情况智能生成，或手动新增一条</span>
          </div>
          <div v-else class="cc-tl">
            <div v-for="e in pagedEvents" :key="e.id" class="cc-tl-item">
              <span class="cc-tl-node" :class="`tone-${eventTone(e.event_type)}`"><el-icon><ChatDotRound /></el-icon></span>
              <div class="cc-tl-card">
                <div class="cc-tl-top">
                  <span class="tui-tag" :class="tagClass(e.event_type)">{{ CARE_EVENT_LABEL[e.event_type] }}</span>
                  <span class="cc-tl-title">{{ e.title }}</span>
                  <el-tag v-if="e.auto_generated" size="small" effect="plain" round>自动</el-tag>
                </div>
                <div class="cc-tl-meta">
                  <span v-if="e.student_name">{{ e.student_name }}</span>
                  <span>{{ e.event_date }}</span>
                  <button class="cc-link cc-link-danger" @click="removeEvent(e)">删除</button>
                </div>
              </div>
            </div>
            <div v-if="shownEvents.length > pageSizeEvents" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="pageEvents"
                v-model:page-size="pageSizeEvents"
                :page-sizes="[10, 20, 50]"
                :total="shownEvents.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="handleEventsSizeChange"
                @current-change="handleEventsCurrentChange"
              />
            </div>
          </div>
        </section>
      </template>

      <!-- 家访记录 -->
      <template v-else-if="tab === 'visits'">
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><HomeFilled /></el-icon>家访时间轴</h3>
            <div class="tui-section-extra">
              <span class="cc-count">{{ shownVisits.length }} 条</span>
              <el-button class="cc-add" size="small" :icon="Plus" @click="visitVisible = true">新增家访</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>记录每一次实地 / 电话家访；填写「后续计划」的事项会自动进入上方待回访提醒。</span>
          </div>
          <div v-if="!shownVisits.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><HomeFilled /></el-icon></span>
            <span class="tui-empty-title">暂无家访记录</span>
            <span class="tui-empty-desc">记录每次家访与沟通，形成可追溯的台账</span>
          </div>
          <div v-else class="cc-tl">
            <div v-for="v in pagedVisits" :key="v.id" class="cc-tl-item">
              <span class="cc-tl-node tone-brand"><el-icon><HomeFilled /></el-icon></span>
              <div class="cc-tl-card">
                <div class="cc-tl-top">
                  <span class="tui-tag tui-tag-brand">{{ VISIT_METHOD_LABEL[v.method] }}</span>
                  <span class="cc-tl-title">{{ v.student_name }}</span>
                  <span class="cc-tl-date">{{ v.visit_date }}</span>
                </div>
                <div class="cc-tl-body">{{ v.content }}</div>
                <div v-if="v.follow_up" class="cc-tl-follow">后续：{{ v.follow_up }}</div>
                <div class="cc-tl-meta">
                  <button class="cc-link cc-link-danger" @click="removeVisit(v)">删除</button>
                </div>
              </div>
            </div>
            <div v-if="shownVisits.length > pageSizeVisits" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="pageVisits"
                v-model:page-size="pageSizeVisits"
                :page-sizes="[10, 20, 50]"
                :total="shownVisits.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="handleVisitsSizeChange"
                @current-change="handleVisitsCurrentChange"
              />
            </div>
          </div>
        </section>
      </template>

      <!-- 正向激励 -->
      <template v-else-if="tab === 'praises'">
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><Star /></el-icon>激励时间轴</h3>
            <div class="tui-section-extra">
              <span class="cc-count">{{ shownPraises.length }} 条</span>
              <el-button class="cc-add" size="small" :icon="Plus" @click="praiseVisible = true">新增激励</el-button>
            </div>
          </div>
          <div class="tui-section-hint success">
            <el-icon><InfoFilled /></el-icon>
            <span>及时表扬与发放徽章，让正向反馈被看见；理由越具体，激励越有力量。</span>
          </div>
          <div v-if="!shownPraises.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><Star /></el-icon></span>
            <span class="tui-empty-title">暂无激励记录</span>
            <span class="tui-empty-desc">及时表扬与发放徽章，让正向反馈被看见</span>
          </div>
          <div v-else class="cc-tl">
            <div v-for="p in pagedPraises" :key="p.id" class="cc-tl-item">
              <span class="cc-tl-node tone-success"><el-icon><Star /></el-icon></span>
              <div class="cc-tl-card">
                <div class="cc-tl-top">
                  <span class="tui-tag tui-tag-success">{{ p.badge_name || PRAISE_TYPE_LABEL[p.praise_type] }}</span>
                  <span class="cc-tl-title">{{ p.student_name }}</span>
                  <span class="cc-tl-date">{{ p.occurred_on }}</span>
                </div>
                <div class="cc-tl-body">{{ p.reason }}</div>
                <div class="cc-tl-meta">
                  <button class="cc-link cc-link-danger" @click="removePraise(p)">删除</button>
                </div>
              </div>
            </div>
            <div v-if="shownPraises.length > pageSizePraises" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="pagePraises"
                v-model:page-size="pageSizePraises"
                :page-sizes="[10, 20, 50]"
                :total="shownPraises.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="handlePraisesSizeChange"
                @current-change="handlePraisesCurrentChange"
              />
            </div>
          </div>
        </section>
      </template>

      <!-- 求助受理：学生求助 → 辅导员受理回复，形成帮扶闭环 -->
      <template v-else>
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><ChatDotRound /></el-icon>求助受理</h3>
            <div class="tui-section-extra">
              <span class="cc-count">{{ shownHelp.length }} 条</span>
              <el-button class="cc-add" size="small" :icon="Refresh" @click="loadHelp">刷新</el-button>
            </div>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>学生提交的求助会汇总到这里；「待受理」请尽快响应，回复即形成帮扶闭环。匿名求助不显示学生姓名，但仍可正常回复。</span>
          </div>
          <div class="cc-help-stats">
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === '' }" @click="helpStatusFilter = ''">
              <b>{{ helpOverview.total }}</b><span>全部</span>
            </button>
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === 'pending' }" @click="helpStatusFilter = 'pending'">
              <b>{{ helpOverview.pending }}</b><span>待受理</span>
            </button>
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === 'processing' }" @click="helpStatusFilter = 'processing'">
              <b>{{ helpOverview.processing }}</b><span>帮扶中</span>
            </button>
            <button type="button" class="cc-help-stat" :class="{ on: helpStatusFilter === 'resolved' }" @click="helpStatusFilter = 'resolved'">
              <b>{{ helpOverview.resolved }}</b><span>已帮助</span>
            </button>
          </div>
          <div v-if="!shownHelp.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><ChatDotRound /></el-icon></span>
            <span class="tui-empty-title">暂无求助</span>
            <span class="tui-empty-desc">学生提交求助后会出现在这里</span>
          </div>
          <div v-else class="cc-help-list">
            <div v-for="h in shownHelp" :key="h.id" class="cc-help-item" :class="`st-${h.status}`">
              <div class="cc-help-top">
                <span class="cc-help-name">{{ h.anonymous ? '匿名同学' : (h.student_name || '学生') }}</span>
                <span class="tui-tag" :class="helpCatClass(h.category)">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
                <span class="cc-help-status" :class="`st-${h.status}`">{{ HELP_STATUS_LABEL[h.status] }}</span>
                <span class="cc-help-time">{{ (h.created_at || '').slice(5, 16) }}</span>
              </div>
              <div class="cc-help-body">{{ h.content }}</div>
              <div v-if="h.reply" class="cc-help-reply">
                <span class="cc-help-reply-label">我的回复</span>
                <span class="cc-help-reply-text">{{ h.reply }}</span>
              </div>
              <div class="cc-help-meta">
                <button v-if="!h.anonymous && h.student_id" class="cc-link" @click="gotoStudentById(h.student_id)">成长档案</button>
                <button class="cc-link cc-help-do" @click="openReply(h)">{{ h.reply ? '再次回复' : '受理并回复' }}</button>
              </div>
            </div>
          </div>
        </section>
      </template>
      </template>

      <CareEventDialog v-model="eventVisible" @saved="loadAll" />
      <HomeVisitDialog v-model="visitVisible" @saved="loadAll" />
      <PraiseDialog v-model="praiseVisible" @saved="loadAll" />

      <!-- 求助受理：回复弹窗 -->
      <el-dialog
        v-model="replyVisible"
        title="受理求助"
        :width="isMobile ? '90%' : '440px'"
        align-center
        :close-on-click-modal="false"
        destroy-on-close
        class="tui-dialog"
      >
        <div v-if="replyTarget" class="cc-reply-form">
          <div class="cc-reply-quote">
            <div class="cc-reply-quote-top">
              <span class="cc-help-name">{{ replyTarget.anonymous ? '匿名同学' : (replyTarget.student_name || '学生') }}</span>
              <span class="tui-tag" :class="helpCatClass(replyTarget.category)">{{ HELP_CATEGORY_LABEL[replyTarget.category] }}</span>
            </div>
            <div class="cc-reply-quote-body">{{ replyTarget.content }}</div>
          </div>
          <div class="cc-reply-field">
            <span class="cc-reply-label">回复内容<span class="req">*</span></span>
            <el-input
              v-model="replyForm.reply"
              type="textarea"
              :rows="4"
              maxlength="1000"
              show-word-limit
              placeholder="给学生一句具体的回应与建议……"
            />
          </div>
          <div class="cc-reply-field">
            <span class="cc-reply-label">处理状态</span>
            <el-radio-group v-model="replyForm.status">
              <el-radio-button value="processing">帮扶中</el-radio-button>
              <el-radio-button value="resolved">已帮助</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <template #footer>
          <el-button @click="replyVisible = false">取消</el-button>
          <el-button type="primary" :loading="replySaving" :disabled="!replyForm.reply.trim()" @click="submitReply">提交回复</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowLeft, ArrowRight, Bell, Calendar, ChatDotRound, HomeFilled, InfoFilled,
  Plus, Refresh, Star, Sunny, User,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import {
  deleteCareEvent, deleteHomeVisit, deletePraise, generateCareEvents, getCareEvents,
  getCareOverview, getHomeVisits, getPraises,
  CARE_EVENT_LABEL, PRAISE_TYPE_LABEL, VISIT_METHOD_LABEL,
  type CareCenterOverview, type CareEvent, type CareEventType, type HomeVisit, type Praise,
} from '@/api/careCenter'
import {
  fetchHelpOverview, fetchHelpRequests, replyHelpRequest,
  HELP_CATEGORY_LABEL, HELP_STATUS_LABEL,
  type HelpRequest, type HelpRequestOverview, type HelpCategory, type HelpStatus,
} from '@/api/helpRequest'
import CareEventDialog from '@/components/teacher/carecenter/CareEventDialog.vue'
import HomeVisitDialog from '@/components/teacher/carecenter/HomeVisitDialog.vue'
import PraiseDialog from '@/components/teacher/carecenter/PraiseDialog.vue'

defineOptions({ name: 'teacher-care-center' })

const { isMobile } = useResponsive()

const route = useRoute()
const router = useRouter()

/** 闭环：从学生成长档案跳来时聚焦该生 */
const studentFocus = ref<{ id: number; name: string } | null>(null)

function matchesFocus(id?: number | null, name?: string | null) {
  const f = studentFocus.value
  if (!f) return true
  if (f.id && id != null) return id === f.id
  if (f.name && name) return name === f.name
  return true
}

const shownEvents = computed(() =>
  studentFocus.value ? events.value.filter((e) => matchesFocus(e.student_id, e.student_name)) : events.value
)
const shownVisits = computed(() =>
  studentFocus.value ? visits.value.filter((v) => matchesFocus(v.student_id, v.student_name)) : visits.value
)
const shownPraises = computed(() =>
  studentFocus.value ? praises.value.filter((p) => matchesFocus(p.student_id, p.student_name)) : praises.value
)

/* ===== 求助受理：学生求助 → 辅导员受理回复 ===== */
const helpOverview = ref<HelpRequestOverview>({ pending: 0, processing: 0, resolved: 0, total: 0 })
const helpRequests = ref<HelpRequest[]>([])
const helpStatusFilter = ref<HelpStatus | ''>('')

const shownHelp = computed(() => {
  let list = helpRequests.value
  if (studentFocus.value) list = list.filter((h) => matchesFocus(h.student_id, h.student_name))
  if (helpStatusFilter.value) list = list.filter((h) => h.status === helpStatusFilter.value)
  return list
})

function helpCatClass(_c: HelpCategory) {
  return 'tui-tag-brand'
}

async function loadHelp() {
  const [o, list] = await Promise.allSettled([fetchHelpOverview(), fetchHelpRequests()])
  if (o.status === 'fulfilled') helpOverview.value = o.value
  if (list.status === 'fulfilled') helpRequests.value = list.value
}

/** 闭环出口：从求助直接跳到该生成长档案 */
function gotoStudentById(id: number) {
  router.push({ path: '/teacher/students', query: { student: String(id) } })
}

/** 闭环出口：回到该生成长档案 */
function gotoStudent() {
  if (!studentFocus.value) return
  router.push({ path: '/teacher/students', query: { student: String(studentFocus.value.id) } })
}

function clearStudentFocus() {
  studentFocus.value = null
  router.replace({ path: '/teacher/care-center' })
}

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']

const tab = ref('calendar')
/** 桌面端三列台账看板的容器引用：供「去处理」滚动定位（移动端为 null） */
const boardRef = ref<HTMLElement | null>(null)
const today = new Date()
const calYear = ref(today.getFullYear())
const calMonth = ref(today.getMonth() + 1)

const overview = ref<CareCenterOverview>({ month: '', event_count: 0, visit_count: 0, praise_count: 0, pending_events: 0 })
const events = ref<CareEvent[]>([])
const visits = ref<HomeVisit[]>([])
const praises = ref<Praise[]>([])

const eventVisible = ref(false)
const visitVisible = ref(false)
const praiseVisible = ref(false)
const genLoading = ref(false)

/* ===== 求助受理：回复弹窗状态 ===== */
const replyVisible = ref(false)
const replySaving = ref(false)
const replyTarget = ref<HelpRequest | null>(null)
const replyForm = ref<{ reply: string; status: HelpStatus }>({ reply: '', status: 'resolved' })

function openReply(h: HelpRequest) {
  replyTarget.value = h
  replyForm.value = { reply: '', status: h.status === 'resolved' ? 'resolved' : 'processing' }
  replyVisible.value = true
}

async function submitReply() {
  if (!replyTarget.value || !replyForm.value.reply.trim()) return
  replySaving.value = true
  try {
    await replyHelpRequest(replyTarget.value.id, {
      reply: replyForm.value.reply.trim(),
      status: replyForm.value.status,
    })
    ElMessage.success('已回复学生')
    replyVisible.value = false
    await loadHelp()
  } catch {
    ElMessage.error('回复失败，请稍后再试')
  } finally {
    replySaving.value = false
  }
}

/* ===== 关怀温度：完全基于现有接口字段派生，不新增后端接口 ===== */
const TEMP_TARGET = 12

/** 温度 = 本月关怀动作密度（目标 12 次封顶），再按待处理事项扣减 */
const careScore = computed(() => {
  const o = overview.value
  const actions = o.event_count + o.visit_count + o.praise_count
  const base = Math.min(100, Math.round((actions / TEMP_TARGET) * 100))
  const penalty = Math.min(40, o.pending_events * 5)
  return Math.max(0, Math.min(100, base - penalty))
})

const tempLevel = computed(() => {
  const s = careScore.value
  if (s >= 80) return { label: '温暖', tone: 'success' }
  if (s >= 50) return { label: '平稳', tone: 'brand' }
  if (s >= 25) return { label: '偏冷', tone: 'warn' }
  return { label: '需加温', tone: 'danger' }
})

const tempColor = computed(() => {
  switch (tempLevel.value.tone) {
    case 'success': return 'var(--tui-success)'
    case 'brand': return 'var(--tui-brand)'
    case 'warn': return 'var(--tui-warn)'
    default: return 'var(--tui-danger)'
  }
})

/** 待回访：待处理关怀事项 + 填写了后续计划的家访 */
const pendingCount = computed(() => overview.value.pending_events)
const followUpCount = computed(() => visits.value.filter((v) => (v.follow_up || '').trim().length > 0).length)
const remindTone = computed(() => (pendingCount.value || followUpCount.value ? 'is-warn' : 'is-ok'))

function goFollowUp() {
  tab.value = pendingCount.value > 0 ? 'calendar' : 'visits'
  // 桌面端三列台账常显、无 Tab 可切，把「去处理」落点改为滚动到台账看板，两端按钮口径一致
  boardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** 事项色调：统一走令牌，避免散色 */
function eventTone(t: CareEventType): 'brand' | 'warn' | 'danger' | 'muted' {
  switch (t) {
    case 'birthday': return 'brand'
    case 'difficulty': return 'warn'
    case 'academic': return 'danger'
    default: return 'muted'
  }
}

function tagClass(t: CareEventType) {
  const tone = eventTone(t)
  return tone === 'muted' ? '' : `tui-tag-${tone}`
}

/* ===== 分页（统一按契约第 2 节） ===== */
const pageEvents = ref(1)
const pageSizeEvents = ref(10)
const pageVisits = ref(1)
const pageSizeVisits = ref(10)
const pagePraises = ref(1)
const pageSizePraises = ref(10)

const pagedEvents = computed(() =>
  shownEvents.value.slice((pageEvents.value - 1) * pageSizeEvents.value, pageEvents.value * pageSizeEvents.value)
)
const pagedVisits = computed(() =>
  shownVisits.value.slice((pageVisits.value - 1) * pageSizeVisits.value, pageVisits.value * pageSizeVisits.value)
)
const pagedPraises = computed(() =>
  shownPraises.value.slice((pagePraises.value - 1) * pageSizePraises.value, pagePraises.value * pageSizePraises.value)
)

function handleEventsSizeChange() { pageEvents.value = 1 }
function handleEventsCurrentChange() { /* v-model 已同步 */ }
function handleVisitsSizeChange() { pageVisits.value = 1 }
function handleVisitsCurrentChange() { /* v-model 已同步 */ }
function handlePraisesSizeChange() { pagePraises.value = 1 }
function handlePraisesCurrentChange() { /* v-model 已同步 */ }

const monthKey = computed(() => `${calYear.value}-${String(calMonth.value).padStart(2, '0')}`)

const calendarCells = computed(() => {
  const first = new Date(calYear.value, calMonth.value - 1, 1)
  const offset = (first.getDay() + 6) % 7 // 周一为第一列
  const daysInMonth = new Date(calYear.value, calMonth.value, 0).getDate()
  const prevDays = new Date(calYear.value, calMonth.value - 1, 0).getDate()
  const todayKey = new Date().toISOString().slice(0, 10)
  const cells: { day: number; inMonth: boolean; isToday: boolean; events: CareEvent[] }[] = []

  for (let i = offset - 1; i >= 0; i--) {
    cells.push({ day: prevDays - i, inMonth: false, isToday: false, events: [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const key = `${monthKey.value}-${String(d).padStart(2, '0')}`
    cells.push({
      day: d,
      inMonth: true,
      isToday: key === todayKey,
      events: shownEvents.value.filter((e) => (e.event_date || '').slice(0, 10) === key),
    })
  }
  while (cells.length % 7 !== 0) {
    cells.push({ day: cells.length - offset - daysInMonth + 1, inMonth: false, isToday: false, events: [] })
  }
  return cells
})

function shiftMonth(delta: number) {
  const d = new Date(calYear.value, calMonth.value - 1 + delta, 1)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadAll()
}

async function loadAll() {
  const month = monthKey.value
  const sid = studentFocus.value?.id || undefined
  const [o, e, v, p] = await Promise.allSettled([
    getCareOverview(month),
    getCareEvents(month, sid),
    getHomeVisits(sid),
    getPraises(sid),
  ])
  if (o.status === 'fulfilled') overview.value = o.value
  if (e.status === 'fulfilled') events.value = e.value
  if (v.status === 'fulfilled') visits.value = v.value
  if (p.status === 'fulfilled') praises.value = p.value
  await loadHelp()
}

async function handleGenerate() {
  genLoading.value = true
  try {
    const res = await generateCareEvents(monthKey.value)
    ElMessage.success(res.message)
    loadAll()
  } catch {
    ElMessage.error('自动生成失败')
  } finally {
    genLoading.value = false
  }
}

async function removeEvent(e: CareEvent) {
  try {
    await ElMessageBox.confirm(`确定删除「${e.title}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteCareEvent(e.id)
  ElMessage.success('已删除')
  loadAll()
}

async function removeVisit(v: HomeVisit) {
  try {
    await ElMessageBox.confirm(`确定删除 ${v.student_name} 的家访记录？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteHomeVisit(v.id)
  ElMessage.success('已删除')
  loadAll()
}

async function removePraise(p: Praise) {
  try {
    await ElMessageBox.confirm(`确定删除 ${p.student_name} 的激励记录？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deletePraise(p.id)
  ElMessage.success('已删除')
  loadAll()
}

onMounted(() => {
  // 闭环：解析学生成长档案传来的聚焦参数
  const sid = Number(route.query.student_id)
  const sname = route.query.student_name ? String(route.query.student_name) : ''
  if (sid || sname) studentFocus.value = { id: sid || 0, name: sname }
  loadAll().then(() => {
    if (!studentFocus.value) return
    // 聚焦该生时优先落在有数据的 Tab
    if (shownEvents.value.length) tab.value = 'calendar'
    else if (shownVisits.value.length) tab.value = 'visits'
    else if (shownPraises.value.length) tab.value = 'praises'
    else if (shownHelp.value.length) tab.value = 'help'
  })
})
</script>

<style scoped>
.cc-mobile-ops { margin-bottom: 10px; }

/* 闭环聚焦条：从学生成长档案跳来时的上下文提示 */
.cc-focus {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 11px;
  margin-bottom: 10px;
  border-radius: 9px;
  background: var(--tui-brand-soft);
  border: 1px solid var(--tui-border);
  color: var(--tui-brand-strong);
  font-size: 12px;
}
.cc-focus-text { flex: 1; min-width: 0; font-weight: 500; }
.cc-focus-link,
.cc-focus-clear {
  flex-shrink: 0;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-brand-strong);
  cursor: pointer;
}
.cc-focus-link:hover,
.cc-focus-clear:hover { text-decoration: underline; }

/* 温度进度条 */
.cc-temp-level { font-size: 11.5px; font-weight: 600; padding: 2px 9px; border-radius: 999px; }
.cc-temp-level.lv-success { background: var(--tui-success-soft); color: var(--tui-success); }
.cc-temp-level.lv-brand { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-temp-level.lv-warn { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-temp-level.lv-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }

.cc-temp { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.cc-temp-num {
  flex-shrink: 0; font-size: var(--tui-fs-num); font-weight: 700; line-height: 1;
  color: var(--tui-text); font-variant-numeric: tabular-nums;
}
.cc-temp-num i { font-size: 11px; font-style: normal; color: var(--tui-text-quiet); margin-left: 1px; }

/* 待回访提醒条 */
.cc-remind {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 10px; border-radius: 9px; font-size: 11.5px; line-height: 1.5;
}
.cc-remind .el-icon { flex-shrink: 0; }
.cc-remind-text { flex: 1; min-width: 0; }
.cc-remind.is-warn { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-remind.is-ok { background: var(--tui-success-soft); color: var(--tui-success); }
.cc-remind-go {
  flex-shrink: 0; border: none; background: none; padding: 0;
  font-family: inherit; font-size: 11.5px; font-weight: 600; color: inherit;
  cursor: pointer; text-decoration: underline;
}

/* 日历 */
.cc-cal-title { font-size: 13px; font-weight: 600; color: var(--tui-text); min-width: 116px; text-align: center; }
.cc-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.cc-week span { text-align: center; font-size: 11px; color: var(--tui-text-quiet); }
.cc-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cc-cell {
  min-height: 56px; border: 1px solid var(--tui-border); border-radius: 8px; padding: 4px 5px;
  background: var(--tui-surface); display: flex; flex-direction: column; gap: 3px; overflow: hidden;
}
.cc-cell.muted { background: var(--tui-surface-muted); opacity: 0.55; }
.cc-cell.today { border-color: var(--tui-brand); box-shadow: 0 0 0 2px var(--tui-brand-soft); }
.cc-cell-top { display: flex; align-items: center; justify-content: space-between; }
.cc-day { font-size: 11px; color: var(--tui-text-secondary); font-weight: 600; }
.cc-dot-count { font-size: 10px; color: var(--tui-surface); background: var(--tui-brand); border-radius: 999px; padding: 0 5px; }
.cc-cell-events { display: flex; flex-direction: column; gap: 2px; }
.cc-chip {
  font-size: 10px; padding: 1px 5px; border-radius: 999px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cc-chip.tone-brand { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-chip.tone-warn { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-chip.tone-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }
.cc-chip.tone-muted { background: var(--tui-surface-muted); color: var(--tui-text-tertiary); }
.cc-more { font-size: 10px; color: var(--tui-text-quiet); }

.cc-count { font-size: 11.5px; color: var(--tui-text-quiet); }

/* 添加入口：移到对应分区头部，中性描边小按钮，去蓝色、简约 */
.cc-add {
  height: 28px;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 8px;
  border-color: var(--tui-border-strong);
  background: #fff;
  color: var(--tui-text-secondary);
  font-size: 12.5px;
  font-weight: 500;
}
.cc-add:hover,
.cc-add:focus {
  background: var(--tui-surface-muted);
  border-color: #d6dbe3;
  color: var(--tui-text);
}
.cc-add :deep(.el-icon) { font-size: 13px; }

/* 时间轴 */
.cc-tl { position: relative; padding-left: 24px; }
.cc-tl::before {
  content: ''; position: absolute; left: 8px; top: 5px; bottom: 5px;
  width: 2px; background: var(--tui-border);
}
.cc-tl-item { position: relative; margin-bottom: 8px; }
.cc-tl-item:last-child { margin-bottom: 0; }
.cc-tl-node {
  position: absolute; left: -24px; top: 2px; width: 18px; height: 18px; border-radius: 50%;
  background: var(--tui-surface); box-shadow: inset 0 0 0 2px var(--tui-border-strong);
  color: var(--tui-text-tertiary); display: flex; align-items: center; justify-content: center;
}
.cc-tl-node .el-icon { font-size: 10px; }
.cc-tl-node.tone-brand { box-shadow: inset 0 0 0 2px var(--tui-brand); color: var(--tui-brand); }
.cc-tl-node.tone-warn { box-shadow: inset 0 0 0 2px var(--tui-warn); color: var(--tui-warn); }
.cc-tl-node.tone-danger { box-shadow: inset 0 0 0 2px var(--tui-danger); color: var(--tui-danger); }
.cc-tl-node.tone-success { box-shadow: inset 0 0 0 2px var(--tui-success); color: var(--tui-success); }
.cc-tl-card {
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius-sm);
  padding: 8px 10px; background: var(--tui-surface-muted);
}
.cc-tl-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cc-tl-title {
  font-size: 13px; color: var(--tui-text); flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cc-tl-date { font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-tl-body { font-size: 12.5px; color: var(--tui-text-secondary); line-height: 1.6; white-space: pre-wrap; margin-top: 5px; }
.cc-tl-follow {
  font-size: 11.5px; color: var(--tui-warn); background: var(--tui-warn-soft);
  border-radius: 7px; padding: 5px 8px; margin-top: 6px;
}
.cc-tl-meta { display: flex; align-items: center; gap: 10px; margin-top: 5px; font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-tl-meta .cc-link { margin-left: auto; }

.cc-link { border: none; background: none; padding: 0; font-size: 12px; color: var(--tui-brand); cursor: pointer; font-family: inherit; }
.cc-link-danger { color: var(--tui-danger); }

/* ===== 求助受理 ===== */
.cc-help-stats { display: flex; gap: 8px; margin-bottom: 10px; }
.cc-help-stat {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 8px 4px; border-radius: 10px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--tui-border); background: var(--tui-surface);
  transition: all 0.15s ease;
}
.cc-help-stat b { font-size: 18px; font-weight: 700; color: var(--tui-text); line-height: 1; font-variant-numeric: tabular-nums; }
.cc-help-stat span { font-size: 11px; color: var(--tui-text-quiet); }
.cc-help-stat:hover { border-color: var(--tui-border-strong); }
.cc-help-stat.on { border-color: var(--tui-brand); background: var(--tui-brand-soft); }
.cc-help-stat.on b { color: var(--tui-brand-strong); }
.cc-help-stat.on span { color: var(--tui-brand-strong); }

.cc-help-list { display: flex; flex-direction: column; gap: 8px; }
.cc-help-item {
  border: 1px solid var(--tui-border); border-left: 3px solid var(--tui-border-strong);
  border-radius: var(--tui-radius-sm); padding: 9px 11px; background: var(--tui-surface);
}
.cc-help-item.st-pending { border-left-color: var(--tui-warn); }
.cc-help-item.st-processing { border-left-color: var(--tui-brand); }
.cc-help-item.st-resolved { border-left-color: var(--tui-success); }
.cc-help-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cc-help-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.cc-help-status { font-size: 11px; font-weight: 600; border-radius: 999px; padding: 1px 8px; }
.cc-help-status.st-pending { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-help-status.st-processing { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-help-status.st-resolved { background: var(--tui-success-soft); color: var(--tui-success); }
.cc-help-time { margin-left: auto; font-size: 11px; color: var(--tui-text-quiet); }
.cc-help-body { font-size: 12.5px; color: var(--tui-text-secondary); line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin-top: 6px; }
.cc-help-reply {
  margin-top: 7px; padding: 7px 9px; border-radius: 8px;
  background: var(--tui-brand-soft); border-left: 3px solid var(--tui-brand);
}
.cc-help-reply-label { display: block; font-size: 11px; font-weight: 700; color: var(--tui-brand-strong); margin-bottom: 2px; }
.cc-help-reply-text { font-size: 12px; color: var(--tui-text-secondary); line-height: 1.6; white-space: pre-wrap; }
.cc-help-meta { display: flex; align-items: center; gap: 12px; margin-top: 7px; }
.cc-help-meta .cc-link { font-size: 12px; font-weight: 600; }
.cc-help-meta .cc-help-do { margin-left: auto; }

/* 回复弹窗 */
.cc-reply-form { display: flex; flex-direction: column; gap: 14px; }
.cc-reply-quote {
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius-sm);
  padding: 9px 11px; background: var(--tui-surface-muted);
}
.cc-reply-quote-top { display: flex; align-items: center; gap: 8px; }
.cc-reply-quote-body {
  font-size: 12.5px; color: var(--tui-text-secondary); line-height: 1.6;
  white-space: pre-wrap; word-break: break-word; margin-top: 6px;
}
.cc-reply-field { display: flex; flex-direction: column; gap: 7px; }
.cc-reply-label { font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary); }
.cc-reply-label .req { color: var(--tui-danger); margin-left: 2px; }

/* ===== 桌面端三列台账看板（仅 v-if="!isMobile" 渲染，移动端零影响） ===== */
/* 横向概览带：把原「本月关怀温度」分区压成一条横带，横跨三列置于顶部 */
.cc-band {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  margin-bottom: 10px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}
/* 左缘语义色细线，与页面 hero（success）呼应，保持本页色彩身份一致 */
.cc-band::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--tui-success);
}
.cc-band-temp { display: flex; align-items: baseline; gap: 8px; flex-shrink: 0; }
.cc-band-label { font-size: 11px; color: var(--tui-text-quiet); }
.cc-band-bar { flex: 0 1 300px; min-width: 120px; }
.cc-band-remind { flex: 1 1 auto; min-width: 200px; }
.cc-band .cc-temp-level { flex-shrink: 0; }

/* 三列并排：等宽列；grid 默认 stretch 让三列可视高度对齐 */
.cc-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
  margin-bottom: 10px;
}

/* 列卡：复用 .tui-section 外壳，叠加「顶部语义色细线 + 纵向 flex」（列头固定、列体滚动） */
.cc-col {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  position: relative;
  overflow: hidden;
}
.cc-col::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
}
.cc-col-events::before { background: var(--tui-brand); }
/* 家访列用 warn 色：家访的「后续计划」会进入待回访提醒（warn 语义），色彩可解释 */
.cc-col-visits::before { background: var(--tui-warn); }
.cc-col-praises::before { background: var(--tui-success); }

/* 列体：限高 + 内部滚动，长列表在列内滑动，三列可视高度一致 */
.cc-col-body {
  flex: 1;
  max-height: 480px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

@media (max-width: 767px) {
  .cc-mobile-ops .el-button { flex: 1; min-height: 40px; margin-left: 0 !important; }
  .cc-cell { min-height: 50px; }
  .cc-cell-events { display: none; }
}
</style>