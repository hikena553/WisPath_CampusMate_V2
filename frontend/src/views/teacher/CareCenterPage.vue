﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="tui-page">
    <SubPageHeader title="人文关怀中心" sub="关怀行动 · 温度加温 · 家校联动" fallback="/teacher" />

    <div class="tui-content">
      <!-- 桌面端特色头部：指标本身可点击下钻（点数字即跳到对应清单 / 台账） -->
      <TuiPageHero
        v-if="!isMobile"
        title="人文关怀中心"
        sub="先选学生 → 再点关怀动作 → 做完即留痕；图表降级为一张，其余全部是可执行的清单"
        :icon="Sunny"
        tone="success"
      >
        <button class="tui-hero-metric is-accent cc-hero-metric" type="button" @click="scrollTo(boardRef)">
          <b>{{ overview.event_count }}</b><span>本月关怀事项</span>
        </button>
        <button class="tui-hero-metric cc-hero-metric" type="button" @click="scrollTo(boardRef)">
          <b>{{ overview.visit_count }}</b><span>本月家访</span>
        </button>
        <button class="tui-hero-metric cc-hero-metric" type="button" @click="scrollTo(boardRef)">
          <b>{{ overview.praise_count }}</b><span>本月激励</span>
        </button>
        <button class="tui-hero-metric cc-hero-metric" type="button" @click="goPendingVisits">
          <b>{{ pendingCount }}</b><span>待回访家访</span>
        </button>
        <el-button size="small" round :icon="Refresh" :loading="genLoading" @click="handleGenerate">自动生成</el-button>
      </TuiPageHero>

      <!-- 移动端高频操作 -->
      <div v-if="isMobile" class="tui-actions cc-mobile-ops">
        <el-button size="small" round :icon="Refresh" :loading="genLoading" @click="handleGenerate">自动生成关怀事项</el-button>
      </div>

      <!-- 主区两栏：左＝行动面板 + 加温器；右＝待办清单 + 学生聚焦 + 家校正联。
           窄屏（<1200px）与移动端纵向堆叠（isMobile 直接置 is-stack，双保险）。 -->
      <div class="cc-layout" :class="{ 'is-stack': isMobile }">
        <!-- ================= 左栏 ================= -->
        <div class="cc-col">
          <CareActionPanel
            :student-id="focusId"
            :student="focusStudent"
            :options="allStudents"
            :recent="recentContext"
            @change="onPanelStudent"
            @action="onCareAction"
          />

          <!-- 关怀温度 + 可执行的加温器 -->
          <section class="tui-section cc-warm">
            <div class="tui-section-head">
              <h3><el-icon><DataLine /></el-icon>本月关怀温度</h3>
              <div class="tui-section-extra"><span class="cc-count">{{ overview.month || monthKey }}</span></div>
            </div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>温度由本月「关怀事项 + 家访 + 激励」密度推算，待回访家访越多温度越低；下面的「加温行动」每一项都能点，点了就能立刻去做。</span>
            </div>

            <!-- 复用 TempGauge，只取温度计与等级读数；自带的纯文本 tips 用 :deep 隐藏，
                 改由下方可点击的「加温行动」承担（组件不可改，故在页面侧收敛） -->
            <div class="cc-gauge">
              <TempGauge :score="careScore" :level="careLevel" />
            </div>

            <div class="cc-warmer">
              <div class="cc-warmer-head">加温行动</div>
              <div v-if="!warmers.length" class="cc-warmer-ok">
                <el-icon><CircleCheck /></el-icon>本月关怀节奏不错，继续保持～
              </div>
              <div v-else class="cc-warmer-list">
                <button
                  v-for="w in warmers"
                  :key="w.key"
                  class="cc-warmer-btn"
                  :class="`tone-${w.tone}`"
                  type="button"
                  @click="runWarmer(w.key)"
                >
                  <span class="cc-warmer-text">{{ w.text }}</span>
                  <span class="cc-warmer-go">去处理 →</span>
                </button>
              </div>
            </div>
          </section>
        </div>

        <!-- ================= 右栏 ================= -->
        <div class="cc-col">
          <!-- 待办关怀清单：三条可行动支线 -->
          <section ref="todoRef" class="tui-section cc-todo" :class="{ 'is-flash': todoFlash }">
            <div class="tui-section-head">
              <h3><el-icon><AlarmClock /></el-icon>待办关怀清单</h3>
              <div class="tui-section-extra">
                <el-button class="cc-add" size="small" :icon="Refresh" @click="loadAll">刷新</el-button>
              </div>
            </div>
            <TuiSegmented :model-value="todoTab" :options="todoOptions" @update:model-value="onTodoTab" />

            <!-- ① 待回访家访：标记已回访 / 补充回访记录 -->
            <template v-if="todoTab === 'visits'">
              <div v-if="!pendingVisits.length" class="cc-empty-sm">
                <span class="cc-empty-sm-title">没有待回访的家访</span>
                <span class="cc-empty-sm-desc">家访登记时填写「后续计划」的，会在这里等你回访闭环。</span>
                <el-button class="cc-add" size="small" :icon="Plus" @click="visitVisible = true">登记家访</el-button>
              </div>
              <div v-else class="cc-todo-list tui-scroll-hidden">
                <div v-for="v in pendingVisits" :key="v.id" class="cc-todo-row">
                  <button class="cc-todo-main" type="button" @click="focusStudentById(v.student_id, v.student_name)">
                    <span class="cc-todo-top">
                      <span class="cc-todo-name">{{ v.student_name }}</span>
                      <span class="tui-tag tui-tag-warn">{{ VISIT_METHOD_LABEL[v.method] }}</span>
                      <span class="cc-todo-date">{{ v.visit_date }}</span>
                    </span>
                    <span class="cc-todo-text">{{ v.content }}</span>
                    <span v-if="v.follow_up" class="cc-todo-sub">后续：{{ v.follow_up }}</span>
                  </button>
                  <div class="cc-todo-ops">
                    <button class="cc-link" @click="markVisitDone(v)">标记已回访</button>
                    <button class="cc-link" @click="openFollowUp(v)">补充回访记录</button>
                  </div>
                </div>
              </div>
            </template>

            <!-- ② 待安排的关怀事项 -->
            <template v-else-if="todoTab === 'events'">
              <div v-if="!upcomingEvents.length" class="cc-empty-sm">
                <span class="cc-empty-sm-title">本月没有待安排的关怀事项</span>
                <span class="cc-empty-sm-desc">点「自动生成」按学生情况智能铺排，或手动新增一条。</span>
                <el-button class="cc-add" size="small" :icon="Plus" @click="eventVisible = true">新增事项</el-button>
              </div>
              <div v-else class="cc-todo-list tui-scroll-hidden">
                <div v-for="e in upcomingEvents" :key="e.id" class="cc-todo-row">
                  <button
                    class="cc-todo-main"
                    type="button"
                    :disabled="!e.student_id"
                    @click="e.student_id && focusStudentById(e.student_id, e.student_name)"
                  >
                    <span class="cc-todo-top">
                      <span class="cc-todo-name">{{ e.student_name || '未关联学生' }}</span>
                      <span class="tui-tag" :class="tagClass(e.event_type)">{{ CARE_EVENT_LABEL[e.event_type] }}</span>
                      <span class="cc-todo-date">{{ e.event_date }}</span>
                    </span>
                    <span class="cc-todo-text">{{ e.title }}</span>
                    <span v-if="e.note" class="cc-todo-sub">{{ e.note }}</span>
                  </button>
                  <div class="cc-todo-ops">
                    <button v-if="e.student_id" class="cc-link" @click="focusAndRecord(e.student_id, e.student_name)">记一条关怀</button>
                    <button v-if="e.student_id" class="cc-link" @click="gotoStudentById(e.student_id)">成长档案</button>
                  </div>
                </div>
              </div>
            </template>

            <!-- ③ 未回复的学生求助 -->
            <template v-else>
              <div v-if="!openHelp.length" class="cc-empty-sm">
                <span class="cc-empty-sm-title">没有待回复的求助</span>
                <span class="cc-empty-sm-desc">学生提交求助后会出现在这里，回复即形成帮扶闭环。</span>
              </div>
              <div v-else class="cc-todo-list tui-scroll-hidden">
                <div v-for="h in openHelp" :key="h.id" class="cc-todo-row">
                  <button
                    class="cc-todo-main"
                    type="button"
                    :disabled="h.anonymous || !h.student_id"
                    @click="!h.anonymous && h.student_id && focusStudentById(h.student_id, h.student_name)"
                  >
                    <span class="cc-todo-top">
                      <span class="cc-todo-name">{{ h.anonymous ? '匿名同学' : (h.student_name || '学生') }}</span>
                      <span class="tui-tag tui-tag-brand">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
                      <span class="cc-todo-date">{{ (h.created_at || '').slice(5, 16) }}</span>
                    </span>
                    <span class="cc-todo-text">{{ h.content }}</span>
                  </button>
                  <div class="cc-todo-ops">
                    <button class="cc-link" @click="openReply(h)">{{ h.reply ? '再次回复' : '受理并回复' }}</button>
                  </div>
                </div>
              </div>
            </template>
          </section>

          <!-- 学生关怀聚焦：五类记录合并成一条时间线 -->
          <section v-if="hasFocus" class="tui-section cc-profile">
            <div class="tui-section-head">
              <h3><el-icon><TrendCharts /></el-icon>学生关怀聚焦</h3>
              <div class="tui-section-extra">
                <span class="cc-count">{{ focusStudentName }}</span>
                <button v-if="focusId" class="cc-link" @click="gotoStudentById(focusId)">成长档案</button>
              </div>
            </div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>把「关怀事项 + 家访 + 激励 + 侧写记录 + 家校沟通」按时间倒序合并，一眼看清这位学生的关怀全貌。</span>
            </div>
            <div v-if="!focusTimeline.length" class="cc-empty-sm">
              <span class="cc-empty-sm-title">该生暂无关怀记录</span>
              <span class="cc-empty-sm-desc">从左侧「关怀行动」记一条谈心或家访，开始沉淀档案。</span>
            </div>
            <div v-else class="cc-tl tui-scroll-hidden cc-profile-tl">
              <div v-for="i in focusTimeline.slice(0, 12)" :key="i.key" class="cc-tl-item">
                <span class="cc-tl-node" :class="`tone-${KIND_META[i.kind].tone}`">
                  <el-icon><component :is="KIND_META[i.kind].icon" /></el-icon>
                </span>
                <div class="cc-tl-card">
                  <div class="cc-tl-top">
                    <span class="tui-tag" :class="kindTagClass(i.kind)">{{ i.kindLabel }}</span>
                    <span class="cc-tl-title">{{ i.title }}</span>
                    <span class="cc-tl-date">{{ i.date }}</span>
                  </div>
                  <div v-if="i.desc" class="cc-tl-body">{{ i.desc }}</div>
                </div>
              </div>
              <div v-if="focusTimeline.length > 12" class="cc-more-note">仅显示最近 12 条，共 {{ focusTimeline.length }} 条</div>
            </div>
          </section>

          <!-- 家校正联：数字 + 一键留痕入口 + 该生家校沟通时间轴 -->
          <section class="tui-section cc-guardian">
            <div class="tui-section-head">
              <h3><el-icon><ChatLineRound /></el-icon>家校正联</h3>
              <div class="tui-section-extra">
                <button class="cc-link" @click="gotoGuardianPage">查看家校总览</button>
              </div>
            </div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>家校沟通同样属于人文关怀：只给三个关键数字与一句解释，需要看全量台账请进「家校沟通」页。</span>
            </div>

            <div class="tui-stat-row">
              <button class="tui-stat cc-guardian-stat" type="button" @click="gotoGuardianPage">
                <span class="tui-stat-num">{{ guardianNumbers.students }}</span>
                <span class="tui-stat-label">覆盖学生数（近 {{ GUARDIAN_DAYS }} 天有沟通）</span>
              </button>
              <button class="tui-stat cc-guardian-stat" type="button" @click="gotoGuardianPage">
                <span class="tui-stat-num">{{ guardianNumbers.logs }}</span>
                <span class="tui-stat-label">沟通记录数（近 {{ GUARDIAN_DAYS }} 天留痕）</span>
              </button>
              <button class="tui-stat cc-guardian-stat" type="button" @click="goPendingVisits">
                <span class="tui-stat-num">{{ guardianNumbers.pendingVisits }}</span>
                <span class="tui-stat-label">待回访家访数（待闭环）</span>
              </button>
            </div>

            <div class="cc-guardian-ops">
              <el-button class="cc-add" size="small" :icon="ChatDotRound" @click="openContact('note')">约家长沟通</el-button>
              <el-button class="cc-add" size="small" :icon="Message" @click="openContact('sms')">发短信留痕</el-button>
            </div>

            <div class="cc-guardian-tl">
              <div class="cc-guardian-tl-head">
                <span>{{ focusStudentName }} 的家校沟通记录</span>
                <span class="cc-guardian-tl-sub">{{ hasFocus ? `最近 ${guardianLogs.length} 条` : '未选择学生' }}</span>
              </div>
              <div v-if="!hasFocus" class="cc-empty-sm">
                <span class="cc-empty-sm-title">先选择一名学生</span>
                <span class="cc-empty-sm-desc">选择后可在这里按时间轴查看他与家长的全部沟通留痕。</span>
              </div>
              <div v-else-if="!guardianLogs.length" class="cc-empty-sm">
                <span class="cc-empty-sm-title">该生还没有家校沟通记录</span>
                <span class="cc-empty-sm-desc">点上面「约家长沟通」或「发短信留痕」写下第一条。</span>
              </div>
              <div v-else class="cc-tl">
                <div v-for="l in guardianLogs" :key="l.id" class="cc-tl-item">
                  <span class="cc-tl-node" :class="l.channel === 'sms' ? 'tone-brand' : 'tone-muted'">
                    <el-icon><component :is="l.channel === 'sms' ? Message : ChatLineRound" /></el-icon>
                  </span>
                  <div class="cc-tl-card">
                    <div class="cc-tl-top">
                      <span class="tui-tag" :class="l.scene === 'care' ? 'tui-tag-success' : ''">{{ GUARDIAN_SCENE_LABEL[l.scene] }}</span>
                      <span class="tui-tag">{{ GUARDIAN_CHANNEL_LABEL[l.channel] }}</span>
                      <span class="cc-tl-date">{{ (l.created_at || '').slice(0, 10) }}</span>
                    </div>
                    <div class="cc-tl-body">{{ l.content_summary }}</div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- 全页唯一图表：本月关怀动作分布（自绘，不引依赖） -->
      <section class="tui-section cc-chart">
        <div class="tui-section-head">
          <h3><el-icon><TrendCharts /></el-icon>本月关怀动作分布</h3>
          <div class="tui-section-extra"><span class="cc-count">{{ overview.month || monthKey }} · 共 {{ monthTrend.total }} 次</span></div>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>全页只保留这一张图：把本月「关怀事项 + 家访 + 激励」按天铺开，看出哪几天关怀断档；其余数据一律用清单与数字呈现，不做图表堆砌。</span>
        </div>
        <div class="cc-chart-legend">
          <span class="cc-chart-chip tone-brand">关怀事项 {{ overview.event_count }}</span>
          <span class="cc-chart-chip tone-warn">家访 {{ overview.visit_count }}</span>
          <span class="cc-chart-chip tone-success">激励 {{ overview.praise_count }}</span>
        </div>
        <div class="cc-chart-bars" :style="{ gridTemplateColumns: `repeat(${monthTrend.days}, minmax(0, 1fr))` }">
          <span
            v-for="(c, i) in monthTrend.counts"
            :key="i"
            class="cc-chart-cell"
            :title="`${i + 1} 日 · ${c} 次关怀动作`"
          >
            <i class="cc-chart-bar" :class="{ 'is-zero': !c }" :style="{ height: barHeight(c) }" />
          </span>
        </div>
        <div class="cc-chart-foot"><span>1 日</span><span>{{ monthTrend.days }} 日</span></div>
      </section>

      <!-- 关怀台账：三类台账并行（保留增删 / 自动生成 / 分页），作为历史归档 -->
      <div ref="boardRef" class="cc-board">
        <!-- 第一列：关怀事项 -->
        <section class="tui-section cc-col-card cc-col-events">
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
              <span class="tui-empty-desc">点「自动生成」按学生情况铺排，或手动新增一条</span>
              <el-button class="cc-add" size="small" :icon="Plus" @click="eventVisible = true">去创建</el-button>
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
                    <template v-if="e.student_id">
                      <button class="cc-link" @click="focusStudentById(e.student_id, e.student_name)">{{ e.student_name }}</button>
                    </template>
                    <span v-else class="cc-text-quiet">未关联学生</span>
                    <span>{{ e.event_date }}</span>
                    <span class="cc-tl-actions">
                      <button class="cc-link cc-link-danger" @click="removeEvent(e)">删除</button>
                    </span>
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
        <section class="tui-section cc-col-card cc-col-visits">
          <div class="tui-section-head">
            <h3><el-icon><HomeFilled /></el-icon>家访台账</h3>
            <div class="tui-section-extra">
              <span class="cc-count">{{ shownVisits.length }} 条 · 待回访 {{ shownPendingVisits }}</span>
              <el-button class="cc-add" size="small" :icon="Plus" @click="visitVisible = true">新增</el-button>
            </div>
          </div>
          <div class="cc-col-body tui-scroll-hidden">
            <div v-if="!shownVisits.length" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><HomeFilled /></el-icon></span>
              <span class="tui-empty-title">暂无家访记录</span>
              <span class="tui-empty-desc">记录每次家访与沟通，形成可追溯的台账</span>
              <el-button class="cc-add" size="small" :icon="Plus" @click="visitVisible = true">去创建</el-button>
            </div>
            <div v-else class="cc-tl">
              <div v-for="v in pagedVisits" :key="v.id" class="cc-tl-item">
                <span class="cc-tl-node tone-brand"><el-icon><HomeFilled /></el-icon></span>
                <div class="cc-tl-card">
                  <div class="cc-tl-top">
                    <span class="tui-tag tui-tag-brand">{{ VISIT_METHOD_LABEL[v.method] }}</span>
                    <button class="cc-tl-title cc-link-title" @click="focusStudentById(v.student_id, v.student_name)">{{ v.student_name }}</button>
                    <span class="cc-tl-date">{{ v.visit_date }}</span>
                  </div>
                  <div class="cc-tl-body">{{ v.content }}</div>
                  <div v-if="v.follow_up" class="cc-tl-follow">后续：{{ v.follow_up }}</div>
                  <div class="cc-tl-meta">
                    <span class="cc-status" :class="v.follow_up_status === 'done' ? 'is-done' : 'is-pending'">
                      <i class="cc-status-dot" />{{ FOLLOW_UP_STATUS_LABEL[v.follow_up_status] }}
                    </span>
                    <span class="cc-tl-actions">
                      <button v-if="v.follow_up_status !== 'done'" class="cc-link" @click="markVisitDone(v)">标记已回访</button>
                      <button class="cc-link" @click="openFollowUp(v)">补充回访记录</button>
                      <button class="cc-link cc-link-danger" @click="removeVisit(v)">删除</button>
                    </span>
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
        <section class="tui-section cc-col-card cc-col-praises">
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
              <el-button class="cc-add" size="small" :icon="Plus" @click="praiseVisible = true">去创建</el-button>
            </div>
            <div v-else class="cc-tl">
              <div v-for="p in pagedPraises" :key="p.id" class="cc-tl-item">
                <span class="cc-tl-node tone-success"><el-icon><Star /></el-icon></span>
                <div class="cc-tl-card">
                  <div class="cc-tl-top">
                    <span class="tui-tag tui-tag-success">{{ p.badge_name || PRAISE_TYPE_LABEL[p.praise_type] }}</span>
                    <button class="cc-tl-title cc-link-title" @click="focusStudentById(p.student_id, p.student_name)">{{ p.student_name }}</button>
                    <span class="cc-tl-date">{{ p.occurred_on || (p.created_at || '').slice(0, 10) }}</span>
                  </div>
                  <div class="cc-tl-body">{{ p.reason }}</div>
                  <div class="cc-tl-meta">
                    <span class="cc-tl-actions">
                      <button class="cc-link cc-link-danger" @click="removePraise(p)">删除</button>
                    </span>
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

      <!-- 关怀日历 -->
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
          <span>按天查看该月关怀安排；点「自动生成」可按学生生日、困难情况与学业预警自动铺排事项。</span>
        </div>
        <div class="cc-week">
          <span v-for="w in WEEK_LABELS" :key="w">{{ w }}</span>
        </div>
        <div class="cc-grid">
          <div v-for="(cell, i) in calendarCells" :key="i" class="cc-cell" :class="{ muted: !cell.inMonth, today: cell.isToday }">
            <div class="cc-cell-top">
              <span class="cc-day">{{ cell.day }}</span>
              <span v-if="cell.events.length" class="cc-dot-count">{{ cell.events.length }}</span>
            </div>
            <div class="cc-cell-events">
              <span
                v-for="e in cell.events.slice(0, 2)"
                :key="e.id"
                class="cc-chip"
                :class="`tone-${eventTone(e.event_type)}`"
                :title="e.title"
              >{{ e.title }}</span>
              <span v-if="cell.events.length > 2" class="cc-more">+{{ cell.events.length - 2 }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 求助受理：完整帮扶闭环 -->
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
          <span>「待受理」请尽快响应，回复即形成帮扶闭环；匿名求助不显示学生姓名，但仍可正常回复。</span>
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
              <span class="tui-tag tui-tag-brand">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
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

      <!-- ================= 弹窗 ================= -->
      <CareEventDialog v-model="eventVisible" @saved="loadAll" />
      <HomeVisitDialog v-model="visitVisible" :preset-student-id="focusId" @saved="onCareSaved" />
      <PraiseDialog v-model="praiseVisible" :preset-student-id="focusId" @saved="onCareSaved" />
      <CareRecordDialog
        v-if="focusId"
        v-model="recordVisible"
        :student-id="focusId"
        :student-name="focusStudentName"
        @saved="onCareSaved"
      />
      <ContactLogDialog
        v-if="focusId"
        v-model="contactVisible"
        :student-id="focusId"
        :student="focusStudent"
        :guardians="guardians"
        :initial-scene="contactScene"
        :initial-channel="contactChannel"
        @saved="onCareSaved"
      />

      <!-- 补充回访记录 -->
      <el-dialog
        v-model="followUpVisible"
        title="补充回访记录"
        :width="isMobile ? '90%' : '420px'"
        align-center
        :close-on-click-modal="false"
        destroy-on-close
        class="tui-dialog"
      >
        <div v-if="followUpTarget" class="cc-fu-form">
          <div class="cc-fu-quote">
            <div class="cc-fu-quote-top">
              <span class="cc-help-name">{{ followUpTarget.student_name }}</span>
              <span class="tui-tag tui-tag-warn">{{ followUpTarget.visit_date }} · {{ VISIT_METHOD_LABEL[followUpTarget.method] }}</span>
            </div>
            <div class="cc-fu-quote-body">{{ followUpTarget.content }}</div>
          </div>
          <div class="cc-fu-field">
            <span class="cc-fu-label">回访记录<span class="req">*</span></span>
            <el-input
              v-model="followUpForm.text"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="这次回访了解到什么、家长反馈如何、下一步怎么做……"
            />
          </div>
          <div class="cc-fu-field">
            <span class="cc-fu-label">回访后状态</span>
            <el-radio-group v-model="followUpForm.status">
              <el-radio-button value="done">已回访</el-radio-button>
              <el-radio-button value="pending">仍需回访</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <template #footer>
          <el-button @click="followUpVisible = false">取消</el-button>
          <el-button type="primary" :loading="followUpSaving" :disabled="!followUpForm.text.trim()" @click="submitFollowUp">保存</el-button>
        </template>
      </el-dialog>

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
              <span class="tui-tag tui-tag-brand">{{ HELP_CATEGORY_LABEL[replyTarget.category] }}</span>
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
import { computed, onMounted, ref, watch, type Component } from 'vue'
import {
  AlarmClock, ArrowLeft, ArrowRight, Calendar, ChatDotRound, ChatLineRound, CircleCheck,
  DataLine, HomeFilled, InfoFilled, Message, Notebook, Plus, Refresh, Star, Sunny,
  TrendCharts,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import {
  deleteCareEvent, deleteHomeVisit, deletePraise, generateCareEvents, getCareEvents,
  getCareOverview, getHomeVisits, getPraises, updateHomeVisit,
  CARE_EVENT_LABEL, FOLLOW_UP_STATUS_LABEL, PRAISE_TYPE_LABEL, VISIT_METHOD_LABEL,
  type CareCenterOverview, type CareEvent, type CareEventType, type FollowUpStatus,
  type HomeVisit, type Praise,
} from '@/api/careCenter'
import { getCareRecords, CARE_TYPE_LABEL, type CareRecord } from '@/api/careRecord'
import {
  getContactLogs, getGuardianOverview, getGuardians,
  GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL,
  type ContactLog, type Guardian, type GuardianChannel, type GuardianOverview, type GuardianScene,
} from '@/api/guardian'
import {
  fetchHelpOverview, fetchHelpRequests, replyHelpRequest,
  HELP_CATEGORY_LABEL, HELP_STATUS_LABEL,
  type HelpRequest, type HelpRequestOverview, type HelpStatus,
} from '@/api/helpRequest'
import { getStudents, type StudentSummary } from '@/api/teacher'
import CareEventDialog from '@/components/teacher/carecenter/CareEventDialog.vue'
import HomeVisitDialog from '@/components/teacher/carecenter/HomeVisitDialog.vue'
import PraiseDialog from '@/components/teacher/carecenter/PraiseDialog.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
import ContactLogDialog from '@/components/teacher/guardian/ContactLogDialog.vue'
import CareActionPanel from '@/components/teacher/care/CareActionPanel.vue'
import TempGauge from '@/components/teacher/care/TempGauge.vue'

defineOptions({ name: 'teacher-care-center' })

type CareActionKey = 'record' | 'visit' | 'praise' | 'contact'
type Tone = 'brand' | 'warn' | 'danger' | 'success' | 'muted'
type TimelineKind = 'event' | 'visit' | 'praise' | 'record' | 'contact'

interface TimelineItem {
  key: string
  kind: TimelineKind
  kindLabel: string
  title: string
  desc: string
  date: string
}

interface Warmer {
  key: 'pending-visits' | 'upcoming-events' | 'praise' | 'contact'
  text: string
  tone: Tone
}

const { isMobile } = useResponsive()
const route = useRoute()
const router = useRouter()

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']
/** 家校概览统计窗口（天） */
const GUARDIAN_DAYS = 30
/** 关怀温度目标：本月 12 次关怀动作即视为满温 */
const TEMP_TARGET = 12

/** 时间线节点图标 / 色调（页面私有映射，避免散色） */
const KIND_META: Record<TimelineKind, { icon: Component; tone: Tone }> = {
  event: { icon: ChatDotRound, tone: 'brand' },
  visit: { icon: HomeFilled, tone: 'brand' },
  praise: { icon: Star, tone: 'success' },
  record: { icon: Notebook, tone: 'muted' },
  contact: { icon: ChatLineRound, tone: 'warn' },
}

/* ================= 月份 / 日历 ================= */
const todayDate = new Date()
const calYear = ref(todayDate.getFullYear())
const calMonth = ref(todayDate.getMonth() + 1)
const monthKey = computed(() => `${calYear.value}-${String(calMonth.value).padStart(2, '0')}`)
const todayKey = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

/* ================= 数据 ================= */
const overview = ref<CareCenterOverview>({
  month: '', event_count: 0, visit_count: 0, praise_count: 0,
  pending_events: 0, upcoming_events: 0, closed_visit_count: 0,
})
const events = ref<CareEvent[]>([])
const visits = ref<HomeVisit[]>([])
const praises = ref<Praise[]>([])

/* ================= 学生聚焦（与「关怀行动面板」同一份状态） ================= */
const allStudents = ref<StudentSummary[]>([])
const focusId = ref<number | null>(null)
const focusName = ref('')
const focusStudent = ref<StudentSummary | null>(null)
const focusRecords = ref<CareRecord[]>([])
const focusLogs = ref<ContactLog[]>([])
const guardians = ref<Guardian[]>([])

const focusStudentName = computed(() => focusStudent.value?.name || focusName.value || '该学生')
const hasFocus = computed(() => focusId.value != null || !!focusName.value)

function matchesFocus(id?: number | null, name?: string | null) {
  if (focusId.value != null) return id === focusId.value
  if (focusName.value) return !!name && name === focusName.value
  return true
}

const shownEvents = computed(() => (hasFocus.value ? events.value.filter((e) => matchesFocus(e.student_id, e.student_name)) : events.value))
const shownVisits = computed(() => (hasFocus.value ? visits.value.filter((v) => matchesFocus(v.student_id, v.student_name)) : visits.value))
const shownPraises = computed(() => (hasFocus.value ? praises.value.filter((p) => matchesFocus(p.student_id, p.student_name)) : praises.value))

/** 待回访家访（全局待办，不随聚焦收窄） */
const pendingVisits = computed(() => visits.value.filter((v) => v.follow_up_status === 'pending'))
const pendingCount = computed(() => pendingVisits.value.length)
const shownPendingVisits = computed(() => shownVisits.value.filter((v) => v.follow_up_status === 'pending').length)

/** 待安排的关怀事项（当前查看月份内，含今天起） */
const upcomingEvents = computed(() =>
  events.value
    .filter((e) => (e.event_date || '') >= todayKey.value)
    .slice()
    .sort((a, b) => (a.event_date < b.event_date ? -1 : 1))
)
const upcomingCount = computed(() => upcomingEvents.value.length)

/* ================= 求助受理 ================= */
const helpOverview = ref<HelpRequestOverview>({ pending: 0, processing: 0, resolved: 0, total: 0 })
const helpRequests = ref<HelpRequest[]>([])
const helpStatusFilter = ref<HelpStatus | ''>('')

const shownHelp = computed(() => {
  let list = helpRequests.value
  if (hasFocus.value) list = list.filter((h) => matchesFocus(h.student_id, h.student_name))
  if (helpStatusFilter.value) list = list.filter((h) => h.status === helpStatusFilter.value)
  return list
})
/** 未回复的求助：待办清单第三支线 */
const openHelp = computed(() => helpRequests.value.filter((h) => !h.reply))

async function loadHelp() {
  const [o, list] = await Promise.allSettled([fetchHelpOverview(), fetchHelpRequests()])
  if (o.status === 'fulfilled') helpOverview.value = o.value
  if (list.status === 'fulfilled') helpRequests.value = list.value
}

/* ================= 待办清单（分段） ================= */
const todoTab = ref<string>('visits')
const todoOptions = computed(() => [
  { value: 'visits', label: '待回访家访', count: pendingCount.value },
  { value: 'events', label: '待安排事项', count: upcomingCount.value },
  { value: 'help', label: '待回复求助', count: openHelp.value.length },
])

function onTodoTab(v: string | number) {
  todoTab.value = String(v)
}

/* ================= 关怀温度 + 加温行动 ================= */
const careScore = computed(() => {
  const o = overview.value
  const actions = o.event_count + o.visit_count + o.praise_count
  const base = Math.min(100, Math.round((actions / TEMP_TARGET) * 100))
  const penalty = Math.min(40, pendingCount.value * 5)
  return Math.max(0, Math.min(100, base - penalty))
})
const careLevel = computed(() => (careScore.value >= 80 ? '温暖' : careScore.value >= 50 ? '平稳' : careScore.value >= 25 ? '偏冷' : '需加温'))

/** 本月尚未获得过激励的学生数（用于「给 N 位学生发一条激励」） */
const studentsWithoutPraise = computed(() => {
  if (!allStudents.value.length) return 0
  const withPraise = new Set(praises.value.map((p) => p.student_id))
  return allStudents.value.filter((s) => !withPraise.has(s.id)).length
})

const warmers = computed<Warmer[]>(() => {
  const list: Warmer[] = []
  if (pendingCount.value) list.push({ key: 'pending-visits', text: `还有 ${pendingCount.value} 条家访待回访`, tone: 'warn' })
  if (upcomingCount.value) list.push({ key: 'upcoming-events', text: `本月有 ${upcomingCount.value} 项关怀事项待安排`, tone: 'brand' })
  if (studentsWithoutPraise.value) list.push({ key: 'praise', text: `给 ${studentsWithoutPraise.value} 位学生发一条激励`, tone: 'success' })
  else if (!praises.value.length) list.push({ key: 'praise', text: '给一位学生发一条正向激励', tone: 'success' })
  if (focusId.value && !focusLogs.value.length) list.push({ key: 'contact', text: '该生还没有家校沟通留痕', tone: 'muted' })
  return list
})

function runWarmer(key: Warmer['key']) {
  if (key === 'pending-visits') goPendingVisits()
  else if (key === 'upcoming-events') {
    todoTab.value = 'events'
    flashTodo()
    scrollTo(todoRef.value)
  } else if (key === 'praise') openPraise()
  else openContact('note')
}

/* ================= 学生关怀聚焦时间线 ================= */
const focusTimeline = computed<TimelineItem[]>(() => {
  const items: TimelineItem[] = []
  for (const e of shownEvents.value) {
    items.push({
      key: `event-${e.id}`, kind: 'event', kindLabel: CARE_EVENT_LABEL[e.event_type],
      title: e.title, desc: e.note || '', date: (e.event_date || '').slice(0, 10),
    })
  }
  for (const v of shownVisits.value) {
    items.push({
      key: `visit-${v.id}`, kind: 'visit', kindLabel: VISIT_METHOD_LABEL[v.method],
      title: `家访 · ${v.student_name}`, desc: v.content, date: (v.visit_date || '').slice(0, 10),
    })
  }
  for (const p of shownPraises.value) {
    items.push({
      key: `praise-${p.id}`, kind: 'praise', kindLabel: p.badge_name || PRAISE_TYPE_LABEL[p.praise_type],
      title: `正向激励 · ${p.student_name}`, desc: p.reason,
      date: (p.occurred_on || p.created_at || '').slice(0, 10),
    })
  }
  for (const r of focusRecords.value) {
    items.push({
      key: `record-${r.id}`, kind: 'record', kindLabel: CARE_TYPE_LABEL[r.record_type],
      title: `侧写记录 · ${r.teacher_name || '我'}`, desc: r.content, date: (r.created_at || '').slice(0, 10),
    })
  }
  for (const c of focusLogs.value) {
    items.push({
      key: `contact-${c.id}`, kind: 'contact', kindLabel: `${GUARDIAN_SCENE_LABEL[c.scene]} · ${GUARDIAN_CHANNEL_LABEL[c.channel]}`,
      title: `家校沟通 · ${c.guardian_name || '家长'}`, desc: c.content_summary, date: (c.created_at || '').slice(0, 10),
    })
  }
  return items.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
})

/** 行动面板的最近 3 条上下文 */
const recentContext = computed(() =>
  focusTimeline.value.slice(0, 3).map((i) => ({ id: i.key, label: i.kindLabel, text: i.title, date: i.date }))
)

/** 家校沟通时间轴（该生，最近 5 条） */
const guardianLogs = computed(() =>
  focusLogs.value
    .slice()
    .sort((a, b) => ((a.created_at || '') < (b.created_at || '') ? 1 : -1))
    .slice(0, 5)
)

/* ================= 家校正联数字 ================= */
const guardianOverview = ref<GuardianOverview | null>(null)
const guardianNumbers = computed(() => ({
  students: guardianOverview.value?.totals.students ?? 0,
  logs: guardianOverview.value?.totals.logs ?? 0,
  pendingVisits: pendingCount.value,
}))

/* ================= 唯一图表：本月关怀动作分布 ================= */
const monthTrend = computed(() => {
  const days = new Date(calYear.value, calMonth.value, 0).getDate()
  const counts = new Array<number>(days).fill(0)
  const prefix = `${calYear.value}-${String(calMonth.value).padStart(2, '0')}`
  const add = (raw?: string | null) => {
    const key = (raw || '').slice(0, 10)
    if (!key.startsWith(prefix)) return
    const day = Number(key.slice(8, 10))
    if (day >= 1 && day <= days) counts[day - 1] += 1
  }
  events.value.forEach((e) => add(e.event_date))
  visits.value.forEach((v) => add(v.visit_date))
  praises.value.forEach((p) => add(p.occurred_on || p.created_at))
  return { days, counts, max: Math.max(1, ...counts), total: counts.reduce((a, b) => a + b, 0) }
})
function barHeight(c: number) {
  if (!c) return '3px'
  return `${18 + Math.round((c / monthTrend.value.max) * 62)}px`
}

/* ================= 分页（三类台账） ================= */
const pageEvents = ref(1)
const pageSizeEvents = ref(10)
const pageVisits = ref(1)
const pageSizeVisits = ref(10)
const pagePraises = ref(1)
const pageSizePraises = ref(10)

const pagedEvents = computed(() => shownEvents.value.slice((pageEvents.value - 1) * pageSizeEvents.value, pageEvents.value * pageSizeEvents.value))
const pagedVisits = computed(() => shownVisits.value.slice((pageVisits.value - 1) * pageSizeVisits.value, pageVisits.value * pageSizeVisits.value))
const pagedPraises = computed(() => shownPraises.value.slice((pagePraises.value - 1) * pageSizePraises.value, pagePraises.value * pageSizePraises.value))

function handleEventsSizeChange() { pageEvents.value = 1 }
function handleEventsCurrentChange() { /* v-model 已同步 */ }
function handleVisitsSizeChange() { pageVisits.value = 1 }
function handleVisitsCurrentChange() { /* v-model 已同步 */ }
function handlePraisesSizeChange() { pagePraises.value = 1 }
function handlePraisesCurrentChange() { /* v-model 已同步 */ }

/** 聚焦学生 / 搜索后列表变短，把页码收回有效范围，避免出现空白页 */
watch([() => shownEvents.value.length, pageSizeEvents], () => {
  pageEvents.value = Math.min(pageEvents.value, Math.max(1, Math.ceil(shownEvents.value.length / pageSizeEvents.value)))
})
watch([() => shownVisits.value.length, pageSizeVisits], () => {
  pageVisits.value = Math.min(pageVisits.value, Math.max(1, Math.ceil(shownVisits.value.length / pageSizeVisits.value)))
})
watch([() => shownPraises.value.length, pageSizePraises], () => {
  pagePraises.value = Math.min(pagePraises.value, Math.max(1, Math.ceil(shownPraises.value.length / pageSizePraises.value)))
})

/* ================= 滚动定位 / 高亮 ================= */
const todoRef = ref<HTMLElement | null>(null)
const boardRef = ref<HTMLElement | null>(null)
/** 待办清单高亮：加温行动「去处理」点击后短暂高亮该分区 */
const todoFlash = ref(false)
let flashTimer: ReturnType<typeof setTimeout> | undefined

function scrollTo(el: HTMLElement | null) {
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function flashTodo() {
  todoFlash.value = true
  if (flashTimer) clearTimeout(flashTimer)
  flashTimer = setTimeout(() => { todoFlash.value = false }, 2400)
}

function goPendingVisits() {
  todoTab.value = 'visits'
  flashTodo()
  scrollTo(todoRef.value)
}

/* ================= 弹窗状态 ================= */
const eventVisible = ref(false)
const visitVisible = ref(false)
const praiseVisible = ref(false)
const recordVisible = ref(false)
const contactVisible = ref(false)
const contactScene = ref<GuardianScene>('care')
const contactChannel = ref<GuardianChannel>('note')
const genLoading = ref(false)

function onCareAction(key: CareActionKey) {
  if (!focusId.value) {
    ElMessage.warning('请先在上方选择一名学生')
    return
  }
  if (key === 'record') recordVisible.value = true
  else if (key === 'visit') visitVisible.value = true
  else if (key === 'praise') praiseVisible.value = true
  else openContact('note')
}

function openPraise() {
  if (!focusId.value) {
    ElMessage.warning('请先在上方选择一名学生，再发激励')
    return
  }
  praiseVisible.value = true
}

function openContact(channel: GuardianChannel, scene: GuardianScene = 'care') {
  if (!focusId.value) {
    ElMessage.warning('请先在上方选择一名学生')
    return
  }
  contactChannel.value = channel
  contactScene.value = scene
  contactVisible.value = true
}

/* ================= 学生聚焦 / 深链 ================= */
function setFocus(s: StudentSummary) {
  focusStudent.value = s
  focusId.value = s.id
  focusName.value = s.name
  pageEvents.value = 1
  pageVisits.value = 1
  pagePraises.value = 1
  void loadFocusExtras()
}

function clearFocus() {
  focusStudent.value = null
  focusId.value = null
  focusName.value = ''
  focusRecords.value = []
  focusLogs.value = []
  guardians.value = []
  pageEvents.value = 1
  pageVisits.value = 1
  pagePraises.value = 1
  router.replace({ path: '/teacher/care-center' })
}

function onPanelStudent(s: StudentSummary | null) {
  if (!s) clearFocus()
  else setFocus(s)
}

/** 按 id 聚焦（清单 / 台账里的任意条目都能下钻到该生） */
function focusStudentById(id: number, name?: string) {
  const hit = allStudents.value.find((s) => s.id === id) || (focusStudent.value?.id === id ? focusStudent.value : null)
  if (hit) {
    setFocus(hit)
    return
  }
  // 回退：名单里没有该生时只按 id / 姓名聚焦，记录类接口仍可正常使用
  focusStudent.value = null
  focusId.value = id
  focusName.value = name || ''
  void loadFocusExtras()
}

function focusAndRecord(id: number, name?: string) {
  focusStudentById(id, name)
  recordVisible.value = true
}

/** 闭环出口：跳到该生成长档案 */
function gotoStudentById(id: number) {
  router.push({ path: '/teacher/students', query: { student: String(id) } })
}

/** 闭环出口：家校沟通页（带上当前学生） */
function gotoGuardianPage() {
  router.push({
    path: '/teacher/guardian',
    query: focusId.value ? { student_id: String(focusId.value) } : undefined,
  })
}

/* ================= 数据加载 ================= */
async function loadFocusExtras() {
  if (!focusId.value) {
    focusRecords.value = []
    focusLogs.value = []
    guardians.value = []
    return
  }
  const id = focusId.value
  const [r, l, g] = await Promise.allSettled([
    getCareRecords({ student_id: id, limit: 50 }),
    getContactLogs(id),
    getGuardians(id),
  ])
  if (r.status === 'fulfilled') focusRecords.value = r.value
  if (l.status === 'fulfilled') focusLogs.value = l.value
  if (g.status === 'fulfilled') guardians.value = g.value
}

async function loadGuardianOverview() {
  try {
    guardianOverview.value = await getGuardianOverview({ days: GUARDIAN_DAYS })
  } catch {
    guardianOverview.value = null
  }
}

async function loadAll() {
  const month = monthKey.value
  const [o, e, v, p] = await Promise.allSettled([
    getCareOverview(month),
    getCareEvents(month),
    getHomeVisits(),
    getPraises(),
  ])
  if (o.status === 'fulfilled') overview.value = o.value
  if (e.status === 'fulfilled') events.value = e.value
  if (v.status === 'fulfilled') visits.value = v.value
  if (p.status === 'fulfilled') praises.value = p.value
  await Promise.all([loadHelp(), loadFocusExtras(), loadGuardianOverview()])
}

/** 任何关怀动作保存后：刷新台账 + 该生上下文 */
async function onCareSaved() {
  await loadAll()
}

async function handleGenerate() {
  genLoading.value = true
  try {
    const res = await generateCareEvents(monthKey.value)
    ElMessage.success(res.message)
    await loadAll()
  } catch {
    ElMessage.error('自动生成失败')
  } finally {
    genLoading.value = false
  }
}

/* ================= 台账增删 / 回访闭环 ================= */
async function removeEvent(e: CareEvent) {
  try {
    await ElMessageBox.confirm(`确定删除「${e.title}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteCareEvent(e.id)
  ElMessage.success('已删除')
  await loadAll()
}

async function removeVisit(v: HomeVisit) {
  try {
    await ElMessageBox.confirm(`确定删除 ${v.student_name} 的家访记录？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteHomeVisit(v.id)
  ElMessage.success('已删除')
  await loadAll()
}

async function markVisitDone(v: HomeVisit) {
  try {
    await updateHomeVisit(v.id, { follow_up_status: 'done' })
    ElMessage.success('已标记为已回访')
    await loadAll()
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  }
}

/** 补充回访记录：追加到沟通内容并同步回访状态 */
const followUpVisible = ref(false)
const followUpSaving = ref(false)
const followUpTarget = ref<HomeVisit | null>(null)
const followUpForm = ref<{ text: string; status: FollowUpStatus }>({ text: '', status: 'done' })

function openFollowUp(v: HomeVisit) {
  followUpTarget.value = v
  followUpForm.value = { text: '', status: 'done' }
  followUpVisible.value = true
}

async function submitFollowUp() {
  const target = followUpTarget.value
  const text = followUpForm.value.text.trim()
  if (!target || !text) return
  followUpSaving.value = true
  try {
    const stamp = todayKey.value
    await updateHomeVisit(target.id, {
      content: `${target.content}\n【回访 ${stamp}】${text}`,
      follow_up_status: followUpForm.value.status,
    })
    ElMessage.success('已补充回访记录')
    followUpVisible.value = false
    await loadAll()
  } catch {
    ElMessage.error('保存失败，请稍后再试')
  } finally {
    followUpSaving.value = false
  }
}

async function removePraise(p: Praise) {
  try {
    await ElMessageBox.confirm(`确定删除 ${p.student_name} 的激励记录？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deletePraise(p.id)
  ElMessage.success('已删除')
  await loadAll()
}

/* ================= 求助受理：回复 ================= */
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

/* ================= 日历 ================= */
const calendarCells = computed(() => {
  const first = new Date(calYear.value, calMonth.value - 1, 1)
  const offset = (first.getDay() + 6) % 7
  const daysInMonth = new Date(calYear.value, calMonth.value, 0).getDate()
  const prevDays = new Date(calYear.value, calMonth.value - 1, 0).getDate()
  const cells: { day: number; inMonth: boolean; isToday: boolean; events: CareEvent[] }[] = []

  for (let i = offset - 1; i >= 0; i--) {
    cells.push({ day: prevDays - i, inMonth: false, isToday: false, events: [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const key = `${monthKey.value}-${String(d).padStart(2, '0')}`
    cells.push({
      day: d,
      inMonth: true,
      isToday: key === todayKey.value,
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
  void loadAll()
}

/* ================= 样式辅助 ================= */
function eventTone(t: CareEventType): Tone {
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

function kindTagClass(kind: TimelineKind) {
  const tone = KIND_META[kind].tone
  return tone === 'muted' ? '' : `tui-tag-${tone}`
}

/* ================= 初始化 ================= */
onMounted(async () => {
  const rawId = Number(route.query.student_id)
  const sid = Number.isFinite(rawId) && rawId > 0 ? rawId : 0
  const sname = route.query.student_name ? String(route.query.student_name) : ''

  try {
    allStudents.value = await getStudents()
  } catch {
    allStudents.value = []
  }

  // 闭环：从学生成长档案 / 其它页面深链跳来时直接聚焦该生
  if (sid || sname) {
    const hit = (sid ? allStudents.value.find((s) => s.id === sid) : undefined)
      || (sname ? allStudents.value.find((s) => s.name === sname) : undefined)
    if (hit) {
      focusStudent.value = hit
      focusId.value = hit.id
      focusName.value = hit.name
    } else {
      focusId.value = sid || null
      focusName.value = sname
    }
  }

  await loadAll()
})
</script>

<style scoped>
/* ===== 头部指标可点击 ===== */
.cc-hero-metric {
  border: 1px solid var(--tui-border);
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s var(--tui-ease), background 0.15s var(--tui-ease);
}
.cc-hero-metric:hover { border-color: var(--tui-border-strong); background: var(--tui-surface-muted); }
.cc-hero-metric:active { transform: scale(0.97); }

.cc-mobile-ops { margin-bottom: 10px; }
.cc-text-quiet { color: var(--tui-text-quiet); }
.cc-more-note { font-size: 11.5px; color: var(--tui-text-quiet); padding: 2px 0 0 2px; }

/* ===== 主区两栏 ===== */
.cc-layout {
  display: grid;
  grid-template-columns: minmax(0, 400px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.cc-layout.is-stack { grid-template-columns: minmax(0, 1fr); }
.cc-col { display: flex; flex-direction: column; gap: 12px; min-width: 0; }

/* 窄屏（<1200px）纵向堆叠 */
@media (max-width: 1199px) {
  .cc-layout { grid-template-columns: minmax(0, 1fr); }
}

/* ===== 温度 + 加温器 ===== */
.cc-gauge { margin-bottom: 10px; }
/* TempGauge 自带的纯文本 tips 在此隐藏，改由下方「加温行动」承载可点击版本 */
.cc-gauge :deep(.cc-gauge-tips) { display: none; }

.cc-warmer {
  border-top: 1px solid var(--tui-hairline);
  padding-top: 9px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.cc-warmer-head { font-size: 12px; font-weight: 600; color: var(--tui-text-secondary); }
.cc-warmer-ok { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--tui-success); }
.cc-warmer-list { display: flex; flex-direction: column; gap: 6px; }
.cc-warmer-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--tui-border);
  border-left-width: 3px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  font-family: inherit;
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease);
}
.cc-warmer-btn:hover { background: var(--tui-surface-sunken); }
.cc-warmer-text { flex: 1; min-width: 0; color: var(--tui-text-secondary); font-weight: 500; }
.cc-warmer-go { flex-shrink: 0; font-size: 11.5px; font-weight: 600; color: var(--tui-brand); }
.cc-warmer-btn.tone-warn { border-left-color: var(--tui-warn); }
.cc-warmer-btn.tone-brand { border-left-color: var(--tui-brand); }
.cc-warmer-btn.tone-success { border-left-color: var(--tui-success); }
.cc-warmer-btn.tone-muted { border-left-color: var(--tui-border-strong); }

/* ===== 待办清单 ===== */
.cc-todo { position: relative; overflow: hidden; }
.cc-todo::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
  background: var(--tui-warn);
}
.cc-todo.is-flash { box-shadow: 0 0 0 2px var(--tui-warn-soft), var(--tui-shadow-2); }

.cc-todo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 330px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.cc-todo-row {
  border: 1px solid var(--tui-border);
  border-left: 3px solid var(--tui-border-strong);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  padding: 8px 10px;
}
.cc-todo-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.cc-todo-main:disabled { cursor: default; }
.cc-todo-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cc-todo-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.cc-todo-date { margin-left: auto; font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-todo-text {
  font-size: 12.5px; line-height: 1.6; color: var(--tui-text-secondary);
  white-space: pre-wrap; word-break: break-word;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.cc-todo-sub { font-size: 11.5px; line-height: 1.5; color: var(--tui-warn); }
.cc-todo-ops { display: flex; align-items: center; gap: 12px; margin-top: 7px; }

/* 紧凑空态（列表内使用，避免 .tui-empty 的大留白） */
.cc-empty-sm {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 18px 12px;
  text-align: center;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
}
.cc-empty-sm-title { font-size: 12.5px; font-weight: 600; color: var(--tui-text-tertiary); }
.cc-empty-sm-desc { font-size: 11.5px; line-height: 1.6; color: var(--tui-text-quiet); }

/* ===== 学生关怀聚焦 ===== */
.cc-profile { position: relative; overflow: hidden; }
.cc-profile::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
  background: var(--tui-brand);
}
.cc-profile-tl { max-height: 420px; overflow-y: auto; overscroll-behavior: contain; }

/* ===== 家校正联 ===== */
.cc-guardian { position: relative; overflow: hidden; }
.cc-guardian::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
  background: var(--tui-brand);
}
.cc-guardian-stat { text-align: left; }
.cc-guardian-ops { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.cc-guardian-tl { border-top: 1px solid var(--tui-hairline); padding-top: 9px; }
.cc-guardian-tl-head {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; font-weight: 600; color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
.cc-guardian-tl-sub { font-size: 11px; font-weight: 400; color: var(--tui-text-quiet); }

/* ===== 唯一图表 ===== */
.cc-chart { position: relative; overflow: hidden; }
.cc-chart::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
  background: var(--tui-success);
}
.cc-chart-legend { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.cc-chart-chip {
  font-size: 11.5px; font-weight: 600; border-radius: 999px; padding: 3px 9px;
}
.cc-chart-chip.tone-brand { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-chart-chip.tone-warn { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-chart-chip.tone-success { background: var(--tui-success-soft); color: var(--tui-success); }
.cc-chart-bars {
  display: grid;
  align-items: end;
  gap: 2px;
  height: 90px;
  padding: 0 2px;
  border-bottom: 1px solid var(--tui-border-strong);
}
.cc-chart-cell { display: flex; align-items: flex-end; justify-content: center; height: 100%; }
.cc-chart-bar {
  display: block;
  width: 100%;
  max-width: 14px;
  min-height: 3px;
  border-radius: 3px 3px 0 0;
  background: var(--tui-brand);
  opacity: 0.85;
}
.cc-chart-bar.is-zero { background: var(--tui-border-strong); opacity: 0.6; }
.cc-chart-foot {
  display: flex; justify-content: space-between;
  font-size: 11px; color: var(--tui-text-quiet); padding-top: 5px;
}

/* ===== 台账三列看板 ===== */
.cc-board {
  --cc-col-h: 470px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
  margin-bottom: 12px;
}
.cc-col-card {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  position: relative;
  overflow: hidden;
  height: var(--cc-col-h);
}
.cc-col-card::before {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; height: 2px;
}
.cc-col-events::before { background: var(--tui-brand); }
.cc-col-visits::before { background: var(--tui-warn); }
.cc-col-praises::before { background: var(--tui-success); }
.cc-col-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
.cc-col-body > .tui-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* 窄屏 / 移动端：三列改为纵向堆叠、列高自适应 */
@media (max-width: 1199px) {
  .cc-board { grid-template-columns: minmax(0, 1fr); --cc-col-h: auto; }
  .cc-col-card { height: auto; max-height: none; }
  .cc-col-body { max-height: 420px; }
}

/* ===== 通用小件 ===== */
.cc-count { font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-add {
  height: 28px;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 8px;
  border-color: var(--tui-border-strong);
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-size: 12.5px;
  font-weight: 500;
}
.cc-add:hover,
.cc-add:focus {
  background: var(--tui-surface-muted);
  border-color: var(--tui-border-strong);
  color: var(--tui-text);
}
.cc-add :deep(.el-icon) { font-size: 13px; }

.cc-link {
  border: none; background: none; padding: 0;
  font-family: inherit; font-size: 12px; color: var(--tui-brand); cursor: pointer;
}
.cc-link:hover { text-decoration: underline; }
.cc-link-danger { color: var(--tui-danger); }
.cc-link-title {
  flex: 1; min-width: 0; border: none; background: none; padding: 0;
  font-family: inherit; font-size: 13px; color: var(--tui-text); cursor: pointer;
  text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cc-link-title:hover { color: var(--tui-brand); }

/* 时间轴（台账 / 聚焦 / 家校共用） */
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
.cc-tl-meta { display: flex; align-items: center; gap: 10px; margin-top: 5px; font-size: 11.5px; color: var(--tui-text-quiet); flex-wrap: wrap; }
.cc-tl-actions { margin-left: auto; display: flex; align-items: center; gap: 10px; }

.cc-status { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; }
.cc-status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.cc-status.is-pending { color: var(--tui-warn); }
.cc-status.is-done { color: var(--tui-success); }

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
.cc-chip { font-size: 10px; padding: 1px 5px; border-radius: 999px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-chip.tone-brand { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-chip.tone-warn { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-chip.tone-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }
.cc-chip.tone-muted { background: var(--tui-surface-muted); color: var(--tui-text-tertiary); }
.cc-more { font-size: 10px; color: var(--tui-text-quiet); }

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

/* ===== 补充回访记录弹窗 ===== */
.cc-fu-form { display: flex; flex-direction: column; gap: 14px; }
.cc-fu-quote {
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius-sm);
  padding: 9px 11px; background: var(--tui-surface-muted);
}
.cc-fu-quote-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cc-fu-quote-body {
  font-size: 12.5px; color: var(--tui-text-secondary); line-height: 1.6;
  white-space: pre-wrap; word-break: break-word; margin-top: 6px;
}
.cc-fu-field { display: flex; flex-direction: column; gap: 7px; }
.cc-fu-label { font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary); }
.cc-fu-label .req { color: var(--tui-danger); margin-left: 2px; }

/* ===== 求助回复弹窗 ===== */
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

@media (max-width: 767px) {
  .cc-mobile-ops .el-button { flex: 1; min-height: 40px; margin-left: 0 !important; }
  .cc-cell { min-height: 50px; }
  .cc-cell-events { display: none; }
  .cc-todo-list { max-height: none; }
}
</style>