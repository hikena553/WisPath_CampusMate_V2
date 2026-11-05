<template>
  <div
    class="tui-page cc-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="关怀与家校" fallback="/teacher" />
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <div class="tui-content cc-home">
      <div class="cc-shell">
        <!-- 桌面端极简页头（移动端由 SubPageHeader 承担） -->
        <header v-if="!isMobile" class="cc-head">
          <div class="cc-head-main">
            <h1 class="cc-head-title">关怀与家校</h1>
            <p class="cc-head-sub">关怀动作与家长沟通在同一页留痕，先选学生再动手</p>
          </div>
        </header>

        <!-- 学生切换：先行选择，再看关系网络 -->
        <div class="cc-chips" role="group" aria-label="切换学生">
          <button
            v-for="s in chipStudents"
            :key="s.id"
            class="cc-stu-chip"
            :class="{ 'on': s.id === focusId }"
            type="button"
            @click="setFocus(s)"
          >
            {{ s.name }}
          </button>
          <button class="cc-stu-chip cc-stu-chip--more" type="button" @click="router.push('/teacher/students')">
            全部学生
          </button>
          <button v-if="hasFocus" class="cc-stu-chip cc-stu-chip--clear" type="button" @click="clearFocus">
            清除聚焦
          </button>
        </div>

        <!-- 关系地图：学生为圆心，家长联系人与近 30 天温度 -->
        <section class="cc-relmap" aria-label="学生支持网络">
          <div v-if="!hasFocus" class="cc-relmap-empty">
            <b>选一位学生，查看支持网络</b>
            <span>家长联系人、最近沟通与关怀温度会聚合到这张关系图。</span>
          </div>
          <template v-else>
            <div class="cc-relmap-canvas">
              <svg viewBox="0 0 320 178" aria-hidden="true">
                <line v-if="relNodes.length > 0" x1="160" y1="89" x2="65" y2="42" stroke="#cfe0d7" stroke-width="1" />
                <line v-if="relNodes.length > 1" x1="160" y1="89" x2="255" y2="38" stroke="#cfe0d7" stroke-width="1" />
                <line v-if="relNodes.length > 2" x1="160" y1="89" x2="255" y2="136" stroke="#cfe0d7" stroke-width="1" />
                <line v-if="relNodes.length > 3" x1="160" y1="89" x2="65" y2="138" stroke="#cfe0d7" stroke-width="1" />
                <circle cx="160" cy="89" r="36" fill="#12554a" opacity=".08" />
                <circle cx="160" cy="89" r="26" fill="#12554a" />
                <circle v-if="relNodes.length > 0" cx="65" cy="42" r="4" fill="#8fb8a6" />
                <circle v-if="relNodes.length > 1" cx="255" cy="38" r="4" fill="#8fb8a6" />
                <circle v-if="relNodes.length > 2" cx="255" cy="136" r="4" fill="#8fb8a6" />
                <circle v-if="relNodes.length > 3" cx="65" cy="138" r="4" fill="#8fb8a6" />
              </svg>
              <button class="cc-relmap-center" type="button" @click="openPage('profile')">
                {{ focusStudentName.slice(0, 4) }}<span>查看聚焦</span>
              </button>
              <span
                v-for="(n, i) in relNodes"
                :key="n.key"
                class="cc-rel-node"
                :class="[`n${i + 1}`, { 'is-dim': n.dim }]"
              >
                <b>{{ n.title }}</b>
                <i>{{ n.meta }}</i>
              </span>
            </div>

            <div class="cc-relmetric">
              <b>{{ guardians.length }}</b>
              <span>位家长联系人</span>
              <span class="cc-relmetric-sp"></span>
              <span class="cc-relmetric-tag">近 {{ GUARDIAN_DAYS }} 天 {{ focusLogs.length }} 次沟通</span>
            </div>

            <div class="cc-heat">
              <div class="cc-heat-hd">
                <span>30 天关怀温度</span>
                <b>{{ careScore }}<i>/100</i></b>
              </div>
              <div class="cc-heat-grid" aria-hidden="true">
                <i v-for="(lv, i) in heatCells" :key="i" :class="`l${lv}`"></i>
              </div>
              <div class="cc-heat-scale"><span>30 天前</span><span>今天</span></div>
            </div>

            <div class="cc-relmap-links">
              <button class="cc-link" type="button" @click="openPage('profile')">查看 {{ focusStudentName }} 的关怀聚焦</button>
              <button class="cc-link" type="button" @click="openPage('guardian')">家校沟通 →</button>
            </div>
          </template>
        </section>

        <!-- 桌面端：快速记录常驻 -->
        <section v-if="!isMobile" class="cc-block">
          <div class="cc-block-hd">
            <span>快速记录关怀</span>
            <span class="cc-block-note">谈心 / 家访 / 激励 / 家校联动</span>
          </div>
          <div class="cc-block-body">
            <CareActionPanel
              :student-id="focusId"
              :student="focusStudent"
              :options="allStudents"
              :recent="recentContext"
              @change="onPanelStudent"
              @action="onCareAction"
            />
          </div>
        </section>

        <!-- 关怀工作台：单行列表，避免逐项卡片堆叠 -->
        <section class="cc-block">
          <div class="cc-block-hd">
            <span>关怀工作台</span>
            <button class="cc-link" type="button" :disabled="genLoading" @click="handleGenerate">
              <el-icon><Refresh /></el-icon>{{ genLoading ? '生成中…' : '自动生成' }}
            </button>
          </div>

          <!-- 移动端：快速记录折叠为一行，展开后再出现完整动作面板 -->
          <button v-if="isMobile && !recordOpen" class="cc-row" type="button" @click="recordOpen = true">
            <span class="cc-row-ic"><el-icon :size="17"><EditPen /></el-icon></span>
            <span class="cc-row-bd">
              <span class="cc-row-title">快速记录关怀</span>
              <span class="cc-row-sub">谈心 / 家访 / 激励 / 学业帮扶，一步留痕</span>
            </span>
            <el-icon class="cc-row-go"><ArrowRight /></el-icon>
          </button>
          <div v-if="isMobile && recordOpen" class="cc-block-body">
            <div class="cc-block-body-hd">
              <span>快速记录关怀</span>
              <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="recordOpen = false">收起</button>
            </div>
            <CareActionPanel
              :student-id="focusId"
              :student="focusStudent"
              :options="allStudents"
              :recent="recentContext"
              @change="onPanelStudent"
              @action="onCareAction"
            />
          </div>

          <button class="cc-row" type="button" @click="openPage('todo')">
            <span class="cc-row-ic"><el-icon :size="17"><AlarmClock /></el-icon></span>
            <span class="cc-row-bd">
              <span class="cc-row-title">待办清单<span class="cc-row-badge" :class="{ 'is-warn': todoTotal }">{{ todoTotal }}</span></span>
              <span class="cc-row-sub">待回访 {{ pendingCount }} · 待安排 {{ upcomingCount }} · 待回复 {{ openHelp.length }}</span>
            </span>
            <el-icon class="cc-row-go"><ArrowRight /></el-icon>
          </button>
          <button class="cc-row" type="button" @click="openPage('ledger')">
            <span class="cc-row-ic"><el-icon :size="17"><Notebook /></el-icon></span>
            <span class="cc-row-bd">
              <span class="cc-row-title">关怀台账<span class="cc-row-badge">{{ ledgerTotal }}</span></span>
              <span class="cc-row-sub">关怀事项 {{ events.length }} · 家访 {{ visits.length }} · 激励 {{ praises.length }}</span>
            </span>
            <el-icon class="cc-row-go"><ArrowRight /></el-icon>
          </button>
          <button class="cc-row" type="button" @click="openPage('help')">
            <span class="cc-row-ic"><el-icon :size="17"><ChatLineRound /></el-icon></span>
            <span class="cc-row-bd">
              <span class="cc-row-title">
                求助信箱
                <span class="cc-row-badge" :class="{ 'is-warn': helpOverview.pending }">{{ helpOverview.pending }}</span>
              </span>
              <span class="cc-row-sub">待受理 {{ helpOverview.pending }} · 帮扶中 {{ helpOverview.processing }} · 已帮助 {{ helpOverview.resolved }}</span>
            </span>
            <el-icon class="cc-row-go"><ArrowRight /></el-icon>
          </button>
          <button class="cc-row" type="button" @click="openPage('guardian')">
            <span class="cc-row-ic"><el-icon :size="17"><Connection /></el-icon></span>
            <span class="cc-row-bd">
              <span class="cc-row-title">家校沟通<span class="cc-row-badge">{{ guardsCount }}</span></span>
              <span class="cc-row-sub">{{ guardianRowSub }}</span>
            </span>
            <el-icon class="cc-row-go"><ArrowRight /></el-icon>
          </button>
          <button class="cc-row" type="button" @click="openPage('board')">
            <span class="cc-row-ic"><el-icon :size="17"><Calendar /></el-icon></span>
            <span class="cc-row-bd">
              <span class="cc-row-title">关怀看板<span class="cc-row-badge">{{ careScore }}%</span></span>
              <span class="cc-row-sub">本月温度 {{ careLevel }} · 动作分布 · 关怀日历</span>
            </span>
            <el-icon class="cc-row-go"><ArrowRight /></el-icon>
          </button>
        </section>

        <!-- 最近 3 条关怀动态 -->
        <section class="cc-block">
          <div class="cc-block-hd">
            <span>最近关怀动态</span>
            <button class="cc-link" type="button" @click="openLedger('events')">查看全部</button>
          </div>
          <div v-if="!recentFeed.length" class="cc-empty cc-empty--plain">
            <span class="cc-empty-title">还没有关怀记录</span>
            <span class="cc-empty-desc">从上方快速记录开始第一次谈心、家访或激励。</span>
          </div>
          <div v-else class="cc-feed">
            <button
              v-for="i in recentFeed"
              :key="i.key"
              class="cc-feed-row"
              type="button"
              @click="openLedgerForKind(i.kind)"
            >
              <span class="tui-tag" :class="kindTagClass(i.kind)">{{ i.label }}</span>
              <span class="cc-feed-title">{{ i.title }}</span>
              <span class="cc-feed-date">{{ i.date }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>

    <!-- ================= 二级页（全屏覆盖 + 统一右滑进入） ================= -->
    <transition-group name="cc-slide" tag="div" class="cc-page-stack">
      <section
        v-for="(page, idx) in pageStack"
        :key="page.key"
        class="cc-subpage"
        :style="{ zIndex: idx }"
      >
        <header class="cc-subhd">
          <div class="cc-subhd-in">
            <button class="cc-subhd-back" type="button" aria-label="返回" @click="backPage">
              <el-icon :size="20"><ArrowLeft /></el-icon>
            </button>
            <span class="cc-subhd-title">{{ pageTitle(page.type) }}</span>
            <div class="cc-subhd-act">
              <button
                v-if="page.type === 'ledger'"
                class="cc-outline-btn cc-outline-btn--sm"
                type="button"
                @click="openCreateForLedger"
              >
                <el-icon><Plus /></el-icon>新增
              </button>
              <button
                v-else-if="page.type === 'profile' && hasFocus"
                class="cc-outline-btn cc-outline-btn--sm"
                type="button"
                @click="gotoFocusStudent"
              >
                成长档案
              </button>
            </div>
          </div>
        </header>

        <div class="cc-subbody">
          <div class="cc-shell cc-sub-shell">
            <!-- ================= 待办清单 ================= -->
            <div v-if="page.type === 'todo'" class="cc-subpad">
              <TuiSegmented :model-value="todoTab" :options="todoOptions" @update:model-value="onTodoTab" />

              <div class="cc-toolbar">
                <span class="cc-toolbar-meta">
                  <template v-if="todoTab === 'visits'">共 {{ pendingCount }} 条待回访</template>
                  <template v-else-if="todoTab === 'events'">共 {{ upcomingCount }} 项待安排</template>
                  <template v-else>共 {{ openHelp.length }} 条待回复</template>
                </span>
                <div class="cc-toolbar-actions">
                  <template v-if="todoTab === 'visits'">
                    <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="visitVisible = true">
                      <el-icon><Plus /></el-icon>登记家访
                    </button>
                  </template>
                  <template v-else-if="todoTab === 'events'">
                    <button class="cc-outline-btn cc-outline-btn--sm" type="button" :disabled="genLoading" @click="handleGenerate">
                      <el-icon><Refresh /></el-icon>{{ genLoading ? '生成中…' : '自动生成' }}
                    </button>
                    <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="eventVisible = true">
                      <el-icon><Plus /></el-icon>新增事项
                    </button>
                  </template>
                  <span v-else class="cc-toolbar-meta">回复即形成帮扶闭环</span>
                </div>
              </div>

              <!-- ① 待回访家访 -->
              <template v-if="todoTab === 'visits'">
                <div v-if="!pendingVisits.length" class="cc-empty">
                  <span class="cc-empty-title">没有待回访的家访</span>
                  <span class="cc-empty-desc">家访登记时填写「后续计划」的，会在这里等你回访闭环。</span>
                  <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="visitVisible = true">
                    <el-icon><Plus /></el-icon>登记家访
                  </button>
                </div>
                <div v-else class="cc-list">
                  <div v-for="v in pendingVisits" :key="v.id" class="cc-item cc-item--warn">
                    <button
                      class="cc-item-main"
                      type="button"
                      @click="openStudentFocus(v.student_id, v.student_name)"
                    >
                      <span class="cc-item-top">
                        <span class="cc-item-name">{{ v.student_name }}</span>
                        <span class="tui-tag tui-tag-warn">{{ VISIT_METHOD_LABEL[v.method] }}</span>
                        <span class="cc-item-date">{{ v.visit_date }}</span>
                      </span>
                      <span class="cc-item-text">{{ v.content }}</span>
                      <span v-if="v.follow_up" class="cc-item-sub">后续：{{ v.follow_up }}</span>
                    </button>
                    <div class="cc-item-ops">
                      <button class="cc-link" type="button" @click="markVisitDone(v)">标记已回访</button>
                      <button class="cc-link" type="button" @click="openFollowUp(v)">补充回访记录</button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- ② 待安排的关怀事项 -->
              <template v-else-if="todoTab === 'events'">
                <div v-if="!upcomingEvents.length" class="cc-empty">
                  <span class="cc-empty-title">本月没有待安排的关怀事项</span>
                  <span class="cc-empty-desc">点「自动生成」按学生情况智能铺排，或手动新增一条。</span>
                  <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="eventVisible = true">
                    <el-icon><Plus /></el-icon>新增事项
                  </button>
                </div>
                <div v-else class="cc-list">
                  <div v-for="e in upcomingEvents" :key="e.id" class="cc-item">
                    <button
                      class="cc-item-main"
                      type="button"
                      :disabled="!e.student_id"
                      @click="e.student_id && openStudentFocus(e.student_id, e.student_name)"
                    >
                      <span class="cc-item-top">
                        <span class="cc-item-name">{{ e.student_name || '未关联学生' }}</span>
                        <span class="tui-tag" :class="tagClass(e.event_type)">{{ CARE_EVENT_LABEL[e.event_type] }}</span>
                        <span class="cc-item-date">{{ e.event_date }}</span>
                      </span>
                      <span class="cc-item-text">{{ e.title }}</span>
                      <span v-if="e.note" class="cc-item-note">{{ e.note }}</span>
                    </button>
                    <div class="cc-item-ops">
                      <button
                        v-if="e.student_id"
                        class="cc-link"
                        type="button"
                        @click="focusAndRecord(e.student_id, e.student_name)"
                      >记一条关怀</button>
                      <button
                        v-if="e.student_id"
                        class="cc-link"
                        type="button"
                        @click="gotoStudentById(e.student_id)"
                      >成长档案</button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- ③ 未回复的学生求助 -->
              <template v-else>
                <div v-if="!openHelp.length" class="cc-empty">
                  <span class="cc-empty-title">没有待回复的求助</span>
                  <span class="cc-empty-desc">学生提交求助后会出现在这里，回复即形成帮扶闭环。</span>
                </div>
                <div v-else class="cc-list">
                  <div v-for="h in openHelp" :key="h.id" class="cc-item cc-item--brand">
                    <button
                      class="cc-item-main"
                      type="button"
                      :disabled="h.anonymous || !h.student_id"
                      @click="!h.anonymous && h.student_id && openStudentFocus(h.student_id, h.student_name)"
                    >
                      <span class="cc-item-top">
                        <span class="cc-item-name">{{ h.anonymous ? '匿名同学' : (h.student_name || '学生') }}</span>
                        <span class="tui-tag tui-tag-brand">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
                        <span class="cc-item-date">{{ (h.created_at || '').slice(5, 16) }}</span>
                      </span>
                      <span class="cc-item-text">{{ h.content }}</span>
                    </button>
                    <div class="cc-item-ops">
                      <button class="cc-link" type="button" @click="openReply(h)">{{ h.reply ? '再次回复' : '受理并回复' }}</button>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <!-- ================= 关怀台账 ================= -->
            <div v-else-if="page.type === 'ledger'" class="cc-subpad">
              <TuiSegmented :model-value="ledgerTab" :options="ledgerOptions" @update:model-value="onLedgerTab" />

              <div class="cc-toolbar">
                <span class="cc-toolbar-meta">
                  <template v-if="ledgerTab === 'events'">共 {{ events.length }} 条关怀事项</template>
                  <template v-else-if="ledgerTab === 'visits'">共 {{ visits.length }} 条家访 · 待回访 {{ pendingCount }}</template>
                  <template v-else>共 {{ praises.length }} 条正向激励</template>
                </span>
                <div class="cc-toolbar-actions">
                  <button
                    v-if="ledgerTab === 'events'"
                    class="cc-outline-btn cc-outline-btn--sm"
                    type="button"
                    :disabled="genLoading"
                    @click="handleGenerate"
                  >
                    <el-icon><Refresh /></el-icon>{{ genLoading ? '生成中…' : '自动生成' }}
                  </button>
                  <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="openCreateForLedger">
                    <el-icon><Plus /></el-icon>新增
                  </button>
                </div>
              </div>

              <!-- 关怀事项 -->
              <template v-if="ledgerTab === 'events'">
                <div v-if="!events.length" class="cc-empty">
                  <span class="cc-empty-title">本月暂无关怀事项</span>
                  <span class="cc-empty-desc">点「自动生成」按学生情况铺排，或手动新增一条。</span>
                  <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="eventVisible = true">
                    <el-icon><Plus /></el-icon>新增事项
                  </button>
                </div>
                <template v-else>
                  <div class="cc-list">
                    <div v-for="e in pagedEvents" :key="e.id" class="cc-item">
                      <div class="cc-item-top">
                        <span class="tui-tag" :class="tagClass(e.event_type)">{{ CARE_EVENT_LABEL[e.event_type] }}</span>
                        <span class="cc-item-name cc-item-name--flex">{{ e.title }}</span>
                        <span v-if="e.auto_generated" class="tui-tag">自动</span>
                        <span class="cc-item-date">{{ e.event_date }}</span>
                      </div>
                      <div class="cc-item-meta">
                        <template v-if="e.student_id">
                          <button class="cc-link" type="button" @click="openStudentFocus(e.student_id, e.student_name)">{{ e.student_name }}</button>
                        </template>
                        <span v-else class="cc-text-quiet">未关联学生</span>
                        <button class="cc-link cc-link-danger cc-item-action" type="button" @click="removeEvent(e)">删除</button>
                      </div>
                    </div>
                  </div>
                  <div v-if="events.length > pageSizeEvents" class="pagination-wrapper">
                    <el-pagination
                      v-model:current-page="pageEvents"
                      v-model:page-size="pageSizeEvents"
                      :page-sizes="[10, 20, 50]"
                      :total="events.length"
                      :pager-count="5"
                      small
                      background
                      layout="total, prev, pager, next"
                      @size-change="handleEventsSizeChange"
                      @current-change="handleEventsCurrentChange"
                    />
                  </div>
                </template>
              </template>

              <!-- 家访台账 -->
              <template v-else-if="ledgerTab === 'visits'">
                <div v-if="!visits.length" class="cc-empty">
                  <span class="cc-empty-title">暂无家访记录</span>
                  <span class="cc-empty-desc">记录每次家访与沟通，形成可追溯的台账。</span>
                  <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="visitVisible = true">
                    <el-icon><Plus /></el-icon>登记家访
                  </button>
                </div>
                <template v-else>
                  <div class="cc-list">
                    <div v-for="v in pagedVisits" :key="v.id" class="cc-item">
                      <div class="cc-item-top">
                        <span class="tui-tag tui-tag-brand">{{ VISIT_METHOD_LABEL[v.method] }}</span>
                        <button class="cc-item-name cc-link-title" type="button" @click="openStudentFocus(v.student_id, v.student_name)">{{ v.student_name }}</button>
                        <span class="cc-item-date">{{ v.visit_date }}</span>
                      </div>
                      <div class="cc-item-text">{{ v.content }}</div>
                      <div v-if="v.follow_up" class="cc-item-follow">后续：{{ v.follow_up }}</div>
                      <div class="cc-item-meta">
                        <span class="cc-status" :class="v.follow_up_status === 'done' ? 'is-done' : 'is-pending'">
                          <i class="cc-status-dot" />{{ FOLLOW_UP_STATUS_LABEL[v.follow_up_status] }}
                        </span>
                        <span class="cc-item-action">
                          <button v-if="v.follow_up_status !== 'done'" class="cc-link" type="button" @click="markVisitDone(v)">标记已回访</button>
                          <button class="cc-link" type="button" @click="openFollowUp(v)">补充回访记录</button>
                          <button class="cc-link cc-link-danger" type="button" @click="removeVisit(v)">删除</button>
                        </span>
                      </div>
                    </div>
                  </div>
                  <div v-if="visits.length > pageSizeVisits" class="pagination-wrapper">
                    <el-pagination
                      v-model:current-page="pageVisits"
                      v-model:page-size="pageSizeVisits"
                      :page-sizes="[10, 20, 50]"
                      :total="visits.length"
                      :pager-count="5"
                      small
                      background
                      layout="total, prev, pager, next"
                      @size-change="handleVisitsSizeChange"
                      @current-change="handleVisitsCurrentChange"
                    />
                  </div>
                </template>
              </template>

              <!-- 正向激励 -->
              <template v-else>
                <div v-if="!praises.length" class="cc-empty">
                  <span class="cc-empty-title">暂无激励记录</span>
                  <span class="cc-empty-desc">及时表扬与发放徽章，让正向反馈被看见。</span>
                  <button class="cc-outline-btn cc-outline-btn--sm" type="button" @click="praiseVisible = true">
                    <el-icon><Plus /></el-icon>新增激励
                  </button>
                </div>
                <template v-else>
                  <div class="cc-list">
                    <div v-for="p in pagedPraises" :key="p.id" class="cc-item">
                      <div class="cc-item-top">
                        <span class="tui-tag tui-tag-success">{{ p.badge_name || PRAISE_TYPE_LABEL[p.praise_type] }}</span>
                        <button class="cc-item-name cc-link-title" type="button" @click="openStudentFocus(p.student_id, p.student_name)">{{ p.student_name }}</button>
                        <span class="cc-item-date">{{ p.occurred_on || (p.created_at || '').slice(0, 10) }}</span>
                      </div>
                      <div class="cc-item-text">{{ p.reason }}</div>
                      <div class="cc-item-meta">
                        <span class="cc-item-action cc-item-action--end">
                          <button class="cc-link cc-link-danger" type="button" @click="removePraise(p)">删除</button>
                        </span>
                      </div>
                    </div>
                  </div>
                  <div v-if="praises.length > pageSizePraises" class="pagination-wrapper">
                    <el-pagination
                      v-model:current-page="pagePraises"
                      v-model:page-size="pageSizePraises"
                      :page-sizes="[10, 20, 50]"
                      :total="praises.length"
                      :pager-count="5"
                      small
                      background
                      layout="total, prev, pager, next"
                      @size-change="handlePraisesSizeChange"
                      @current-change="handlePraisesCurrentChange"
                    />
                  </div>
                </template>
              </template>
            </div>

            <!-- ================= 求助信箱 ================= -->
            <div v-else-if="page.type === 'help'" class="cc-subpad">
              <TuiSegmented :model-value="helpStatusFilter" :options="helpOptions" @update:model-value="onHelpTab" />

              <div class="cc-toolbar">
                <span class="cc-toolbar-meta">共 {{ shownHelp.length }} 条</span>
                <span class="cc-toolbar-meta">匿名求助不显示姓名，仍可正常回复</span>
              </div>

              <div v-if="!shownHelp.length" class="cc-empty">
                <span class="cc-empty-title">暂无求助</span>
                <span class="cc-empty-desc">学生提交求助后会出现在这里。</span>
              </div>
              <div v-else class="cc-list">
                <div v-for="h in shownHelp" :key="h.id" class="cc-item" :class="`st-${h.status}`">
                  <div class="cc-item-top">
                    <span class="cc-item-name">{{ h.anonymous ? '匿名同学' : (h.student_name || '学生') }}</span>
                    <span class="tui-tag tui-tag-brand">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
                    <span class="cc-help-status" :class="`st-${h.status}`">{{ HELP_STATUS_LABEL[h.status] }}</span>
                    <span class="cc-item-date">{{ (h.created_at || '').slice(5, 16) }}</span>
                  </div>
                  <div class="cc-item-text">{{ h.content }}</div>
                  <div v-if="h.reply" class="cc-help-reply">
                    <span class="cc-help-reply-label">我的回复</span>
                    <span class="cc-help-reply-text">{{ h.reply }}</span>
                  </div>
                  <div class="cc-item-meta">
                    <button
                      v-if="!h.anonymous && h.student_id"
                      class="cc-link"
                      type="button"
                      @click="gotoStudentById(h.student_id)"
                    >成长档案</button>
                    <span class="cc-item-action">
                      <button class="cc-link" type="button" @click="openReply(h)">{{ h.reply ? '再次回复' : '受理并回复' }}</button>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- ================= 家校沟通 ================= -->
            <div v-else-if="page.type === 'guardian'" class="cc-subpad cc-subpad--flat">
              <GuardianPanel
                :students="allStudents"
                :student-id="focusId"
                :student="focusStudent"
                :student-name="hasFocus ? focusStudentName : ''"
                :preset-content="guardianPresetContent"
                :preset-scene="guardianPresetScene"
                @select-student="onGuardianSelect"
              />
            </div>

            <!-- ================= 关怀看板 ================= -->
            <div v-else-if="page.type === 'board'" class="cc-subpad">
              <!-- 温度 + 加温行动 -->
              <section class="cc-card">
                <div class="cc-card-hd">
                  <h3><el-icon><DataLine /></el-icon>本月关怀温度</h3>
                  <div class="cc-card-extra">{{ overview.month || monthKey }}</div>
                </div>
                <div class="cc-card-hint">
                  <el-icon><InfoFilled /></el-icon>
                  <span>温度由本月「关怀事项 + 家访 + 激励」密度推算，待回访家访越多温度越低；下方每一项加温行动都可以直接去做。</span>
                </div>
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

              <!-- 本月关怀动作分布 -->
              <section class="cc-card">
                <div class="cc-card-hd">
                  <h3><el-icon><TrendCharts /></el-icon>本月关怀动作分布</h3>
                  <div class="cc-card-extra">{{ overview.month || monthKey }} · 共 {{ monthTrend.total }} 次</div>
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

              <!-- 关怀日历 -->
              <section class="cc-card">
                <div class="cc-card-hd">
                  <h3><el-icon><Calendar /></el-icon>关怀日历</h3>
                  <div class="cc-card-extra">
                    <button class="cc-cal-nav" type="button" aria-label="上个月" @click="shiftMonth(-1)">
                      <el-icon><ArrowLeft /></el-icon>
                    </button>
                    <span class="cc-cal-title">{{ calYear }} 年 {{ calMonth }} 月</span>
                    <button class="cc-cal-nav" type="button" aria-label="下个月" @click="shiftMonth(1)">
                      <el-icon><ArrowRight /></el-icon>
                    </button>
                  </div>
                </div>
                <div class="cc-week">
                  <span v-for="w in WEEK_LABELS" :key="w">{{ w }}</span>
                </div>
                <div class="cc-grid">
                  <div
                    v-for="(cell, i) in calendarCells"
                    :key="i"
                    class="cc-cell"
                    :class="{ muted: !cell.inMonth, today: cell.isToday }"
                  >
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

              <button v-if="hasFocus" class="cc-focus-link" type="button" @click="openPage('profile')">
                <el-icon><TrendCharts /></el-icon>
                <span class="cc-focus-text">进入 <b>{{ focusStudentName }}</b> 的学生关怀聚焦</span>
                <el-icon class="cc-focus-arrow"><ArrowRight /></el-icon>
              </button>
            </div>

            <!-- ================= 学生关怀聚焦 ================= -->
            <div v-else class="cc-subpad">
              <div v-if="!hasFocus" class="cc-empty">
                <span class="cc-empty-title">还没有选择学生</span>
                <span class="cc-empty-desc">请先在一级页「关怀行动」中选择一名学生。</span>
              </div>
              <template v-else>
                <section class="cc-profile-hero">
                  <div class="cc-profile-ava">
                    <img v-if="focusStudent?.avatar" :src="focusStudent.avatar" alt="" />
                    <span v-else>{{ focusStudentName.slice(0, 1) }}</span>
                  </div>
                  <div class="cc-profile-info">
                    <div class="cc-profile-name">{{ focusStudentName }}</div>
                    <div class="cc-profile-meta">
                      {{ focusStudent?.college || '未分配' }}
                      <template v-if="focusStudent?.username"> · {{ focusStudent.username }}</template>
                    </div>
                  </div>
                </section>

                <div class="cc-facts">
                  <div><b>{{ shownEvents.length }}</b><span>关怀事项</span></div>
                  <div><b>{{ shownVisits.length }}</b><span>家访</span></div>
                  <div><b>{{ shownPraises.length }}</b><span>激励</span></div>
                  <div><b>{{ focusLogs.length }}</b><span>家校沟通</span></div>
                </div>

                <div class="cc-quick-grid">
                  <button class="cc-quick" type="button" @click="onCareAction('record')">
                    <el-icon><Notebook /></el-icon>谈心 / 侧写
                  </button>
                  <button class="cc-quick" type="button" @click="onCareAction('visit')">
                    <el-icon><HomeFilled /></el-icon>家访登记
                  </button>
                  <button class="cc-quick" type="button" @click="onCareAction('praise')">
                    <el-icon><Star /></el-icon>正向激励
                  </button>
                  <button class="cc-quick" type="button" @click="onCareAction('contact')">
                    <el-icon><ChatLineRound /></el-icon>家校联动
                  </button>
                </div>

                <section class="cc-flat">
                  <div class="cc-flat-hd">
                    <span>支持网络</span>
                    <button class="cc-link" type="button" @click="gotoGuardianPage">家校总览 →</button>
                  </div>
                  <div class="cc-relmap-mini">
                    <svg viewBox="0 0 320 150" aria-hidden="true">
                      <line v-if="relNodes.length > 0" x1="160" y1="75" x2="66" y2="34" stroke="#cfe0d7" stroke-width="1" />
                      <line v-if="relNodes.length > 1" x1="160" y1="75" x2="254" y2="32" stroke="#cfe0d7" stroke-width="1" />
                      <line v-if="relNodes.length > 2" x1="160" y1="75" x2="254" y2="116" stroke="#cfe0d7" stroke-width="1" />
                      <line v-if="relNodes.length > 3" x1="160" y1="75" x2="66" y2="118" stroke="#cfe0d7" stroke-width="1" />
                      <circle cx="160" cy="75" r="30" fill="#12554a" opacity=".08" />
                      <circle cx="160" cy="75" r="24" fill="#12554a" />
                      <circle v-if="relNodes.length > 0" cx="66" cy="34" r="3.5" fill="#8fb8a6" />
                      <circle v-if="relNodes.length > 1" cx="254" cy="32" r="3.5" fill="#8fb8a6" />
                      <circle v-if="relNodes.length > 2" cx="254" cy="116" r="3.5" fill="#8fb8a6" />
                      <circle v-if="relNodes.length > 3" cx="66" cy="118" r="3.5" fill="#8fb8a6" />
                    </svg>
                    <span class="cc-mmap-center">{{ focusStudentName.slice(0, 3) }}</span>
                  </div>
                  <div class="cc-rel-legend">
                    <span v-for="n in relNodes" :key="n.key" :class="{ 'is-dim': n.dim }">
                      <i></i><b>{{ n.title }}</b>{{ n.meta }}
                    </span>
                  </div>
                  <div class="cc-support-tip">
                    <b>支持网络完整度 {{ supportPct }}%</b>
                    <template v-if="!guardians.length">：还没有家长联系人，建议先建档再沟通。</template>
                    <template v-else-if="supportPct < 60">：部分家长近 {{ GUARDIAN_DAYS }} 天尚未沟通，建议本周补一次联络。</template>
                    <template v-else>：关键联系人都有沟通记录，关系维护良好。</template>
                  </div>
                </section>

                <section class="cc-flat">
                  <div class="cc-flat-hd">
                    <span>关怀轨迹</span>
                    <span class="cc-flat-note">共 {{ focusTimeline.length }} 条</span>
                  </div>
                  <div v-if="!focusTimeline.length" class="cc-empty">
                    <span class="cc-empty-title">该生暂无关怀记录</span>
                    <span class="cc-empty-desc">从上方关怀动作记一条谈心、家访或激励，开始沉淀档案。</span>
                  </div>
                  <div v-else class="cc-tl2">
                    <div v-for="i in focusTimeline.slice(0, 30)" :key="i.key" class="cc-tl2-item">
                      <div class="cc-tl2-date">
                        <b>{{ i.date.slice(8, 10) }}</b>
                        <span>{{ i.date.slice(5, 7) }} 月</span>
                      </div>
                      <div class="cc-tl2-body">
                        <div class="cc-tl2-top">
                          <span class="cc-tl2-kind">{{ i.kindLabel }}</span>
                          <span class="cc-tl2-title">{{ i.title }}</span>
                        </div>
                        <p v-if="i.desc">{{ i.desc }}</p>
                      </div>
                    </div>
                    <div v-if="focusTimeline.length > 30" class="cc-more-note">
                      仅显示最近 30 条，共 {{ focusTimeline.length }} 条
                    </div>
                  </div>
                </section>
              </template>
            </div>
          </div>
        </div>
      </section>
    </transition-group>

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

    <!-- 补充回访记录（1 文本 + 1 单选：移动端 = 底部动作面板） -->
    <ActionSheet
      v-model="followUpVisible"
      title="补充回访记录"
      width="420px"
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
    </ActionSheet>

    <!-- 求助受理（1 文本 + 1 单选：移动端 = 底部动作面板） -->
    <ActionSheet
      v-model="replyVisible"
      title="受理求助"
      width="440px"
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
    </ActionSheet>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type Component } from 'vue'
import ActionSheet from '@/components/common/ActionSheet.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import {
  AlarmClock, ArrowLeft, ArrowRight, Calendar, ChatDotRound, ChatLineRound, CircleCheck,
  Connection, DataLine, EditPen, HomeFilled, InfoFilled, Notebook, Plus, Refresh, Star, TrendCharts,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
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
  getContactLogs, getGuardians,
  GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL,
  type ContactLog, type Guardian, type GuardianChannel, type GuardianScene,
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
import GuardianPanel from '@/components/teacher/guardian/GuardianPanel.vue'
import CareActionPanel from '@/components/teacher/care/CareActionPanel.vue'
import TempGauge from '@/components/teacher/care/TempGauge.vue'

defineOptions({ name: 'teacher-care-center' })

type CareActionKey = 'record' | 'visit' | 'praise' | 'contact'
type Tone = 'brand' | 'warn' | 'danger' | 'success' | 'muted'
type TimelineKind = 'event' | 'visit' | 'praise' | 'record' | 'contact'
type SubPageKey = 'todo' | 'ledger' | 'help' | 'guardian' | 'board' | 'profile'
type TodoTab = 'visits' | 'events' | 'help'
type LedgerTab = 'events' | 'visits' | 'praises'

interface TimelineItem {
  key: string
  kind: TimelineKind
  kindLabel: string
  title: string
  desc: string
  date: string
}

interface FeedItem {
  key: string
  kind: 'event' | 'visit' | 'praise'
  label: string
  title: string
  date: string
}

interface Warmer {
  key: 'pending-visits' | 'upcoming-events' | 'praise' | 'contact'
  text: string
  tone: Tone
}

interface SubPageEntry {
  /** 唯一 key：transition-group 依靠它做右滑进入 / 退出 */
  key: number
  type: SubPageKey
}

const { isMobile } = useResponsive()
const route = useRoute()
const router = useRouter()

/** 移动端下拉刷新：手势只在 .tui-page 自身滚动区生效，固定覆盖层不参与 */
const pull = usePullRefresh(loadAll, { enabled: () => isMobile.value })

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']
/** 家校概览统计窗口（天） */
const GUARDIAN_DAYS = 30
/** 关怀温度目标：本月 12 次关怀动作即视为满温 */
const TEMP_TARGET = 12

const PAGE_TITLE: Record<SubPageKey, string> = {
  todo: '待办清单',
  ledger: '关怀台账',
  help: '求助信箱',
  guardian: '家校沟通',
  board: '关怀看板',
  profile: '学生关怀聚焦',
}

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

/** 家校子页：从成长档案闭环带来的反馈事由 */
const guardianPresetContent = ref('')
const guardianPresetScene = ref<GuardianScene>('care')
/** 家校入口角标与副标题 */
const guardsCount = computed(() => guardians.value.length)
const guardianRowSub = computed(() =>
  hasFocus.value
    ? `家长联系人 ${guardians.value.length} · 沟通记录 ${focusLogs.value.length} 条`
    : '家长联系人、沟通台账与沟通统计'
)

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

/** 待安排的关怀事项（今天起） */
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
  if (helpStatusFilter.value) list = list.filter((h) => h.status === helpStatusFilter.value)
  return list
})
/** 未回复的求助：待办清单第三支线 */
const openHelp = computed(() => helpRequests.value.filter((h) => !h.reply))

const helpOptions = computed(() => [
  { value: '', label: '全部', count: helpOverview.value.total },
  { value: 'pending', label: '待受理', count: helpOverview.value.pending },
  { value: 'processing', label: '帮扶中', count: helpOverview.value.processing },
  { value: 'resolved', label: '已帮助', count: helpOverview.value.resolved },
])

async function loadHelp() {
  const [o, list] = await Promise.allSettled([fetchHelpOverview(), fetchHelpRequests()])
  if (o.status === 'fulfilled') helpOverview.value = o.value
  if (list.status === 'fulfilled') helpRequests.value = list.value
}

/* ================= 二级页导航（统一右滑进入 / 返回） ================= */
const pageStack = ref<SubPageEntry[]>([])
/** 移动端快速记录面板默认折叠，作为一个一级入口 */
const recordOpen = ref(false)
let pageSeq = 0

function openPage(type: SubPageKey) {
  if (type === 'profile' && !hasFocus.value) {
    ElMessage.warning('请先在一级页选择一名学生')
    return
  }
  pageStack.value.push({ key: ++pageSeq, type })
}

function backPage() {
  const top = pageStack.value[pageStack.value.length - 1]
  // 关闭家校子页时清掉一次性预填，避免下次打开重复弹出
  if (top?.type === 'guardian') guardianPresetContent.value = ''
  pageStack.value.pop()
}

function pageTitle(type: SubPageKey) {
  if (type === 'profile' && hasFocus.value) return `${focusStudentName.value} · 关怀聚焦`
  return PAGE_TITLE[type]
}

/* ================= 待办清单（分段） ================= */
const todoTab = ref<TodoTab>('visits')
const todoOptions = computed(() => [
  { value: 'visits', label: '待回访家访', count: pendingCount.value },
  { value: 'events', label: '待安排事项', count: upcomingCount.value },
  { value: 'help', label: '待回复求助', count: openHelp.value.length },
])
const todoTotal = computed(() => pendingCount.value + upcomingCount.value + openHelp.value.length)

function onTodoTab(v: string | number) {
  todoTab.value = String(v) as TodoTab
}

function openTodo(tab: TodoTab) {
  todoTab.value = tab
  openPage('todo')
}

/* ================= 台账分段 ================= */
const ledgerTab = ref<LedgerTab>('events')
const ledgerOptions = computed(() => [
  { value: 'events', label: '关怀事项', count: events.value.length },
  { value: 'visits', label: '家访', count: visits.value.length },
  { value: 'praises', label: '正向激励', count: praises.value.length },
])
const ledgerTotal = computed(() => events.value.length + visits.value.length + praises.value.length)

function onLedgerTab(v: string | number) {
  ledgerTab.value = String(v) as LedgerTab
}

function openLedger(tab: LedgerTab) {
  ledgerTab.value = tab
  openPage('ledger')
}

function openLedgerForKind(kind: FeedItem['kind']) {
  if (kind === 'visit') openLedger('visits')
  else if (kind === 'praise') openLedger('praises')
  else openLedger('events')
}

function openCreateForLedger() {
  if (ledgerTab.value === 'visits') visitVisible.value = true
  else if (ledgerTab.value === 'praises') praiseVisible.value = true
  else eventVisible.value = true
}

/* ================= 最近 3 条动态 ================= */
const recentFeed = computed<FeedItem[]>(() => {
  const items: FeedItem[] = []
  for (const e of events.value) {
    items.push({
      key: `event-${e.id}`,
      kind: 'event',
      label: CARE_EVENT_LABEL[e.event_type],
      title: e.student_name ? `${e.student_name} · ${e.title}` : e.title,
      date: (e.event_date || '').slice(5, 10),
    })
  }
  for (const v of visits.value) {
    items.push({
      key: `visit-${v.id}`,
      kind: 'visit',
      label: VISIT_METHOD_LABEL[v.method],
      title: `${v.student_name} · 家访`,
      date: (v.visit_date || '').slice(5, 10),
    })
  }
  for (const p of praises.value) {
    items.push({
      key: `praise-${p.id}`,
      kind: 'praise',
      label: p.badge_name || PRAISE_TYPE_LABEL[p.praise_type],
      title: `${p.student_name} · ${p.reason}`,
      date: (p.occurred_on || p.created_at || '').slice(5, 10),
    })
  }
  return items.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)).slice(0, 3)
})

/* ================= 关怀温度 + 加温行动 ================= */
const careScore = computed(() => {
  const o = overview.value
  const actions = o.event_count + o.visit_count + o.praise_count
  const base = Math.min(100, Math.round((actions / TEMP_TARGET) * 100))
  const penalty = Math.min(40, pendingCount.value * 5)
  return Math.max(0, Math.min(100, base - penalty))
})
const careLevel = computed(() => (careScore.value >= 80 ? '温暖' : careScore.value >= 50 ? '平稳' : careScore.value >= 25 ? '偏冷' : '需加温'))

/** 本月尚未获得过激励的学生数 */
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
  if (key === 'pending-visits') openTodo('visits')
  else if (key === 'upcoming-events') openTodo('events')
  else if (key === 'praise') openPraise()
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

/** 关系地图：学生为圆心，家长联系人围绕；无联系人时给一个建档引导节点 */
const relNodes = computed(() => {
  const nodes = guardians.value.slice(0, 4).map((g) => {
    const logs = focusLogs.value.filter((l) => l.guardian_id === g.id)
    const last = logs.reduce<ContactLog | null>(
      (acc, cur) => (!acc || (cur.created_at || '') > (acc.created_at || '') ? cur : acc),
      null
    )
    return {
      key: `guardian-${g.id}`,
      title: `${g.relation} ${g.name}${g.is_primary ? ' · 主要' : ''}`,
      meta: last ? `${(last.created_at || '').slice(5, 10)} 最近沟通` : '尚未沟通',
      dim: !last,
    }
  })
  if (nodes.length) return nodes
  return [{ key: 'guardian-empty', title: '家长联系人', meta: '未建档 · 去添加', dim: true }]
})

/** 支持网络完整度：有沟通记录的家长占比 */
const supportPct = computed(() => {
  if (!guardians.value.length) return 0
  const contacted = guardians.value.filter((g) =>
    focusLogs.value.some((l) => l.guardian_id === g.id)
  ).length
  return Math.round((contacted / guardians.value.length) * 100)
})

/** 首页 / 聚焦页共用的学生切换 chips */
const chipStudents = computed(() => allStudents.value.slice(0, 5))

/** 近 30 天关怀温度：把时间轴聚合到 30 个格子里 */
const heatCells = computed(() => {
  const cells = new Array<number>(30).fill(0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  focusTimeline.value.forEach((item) => {
    if (!item.date) return
    const d = new Date(`${item.date}T00:00:00`)
    const diff = Math.round((today.getTime() - d.getTime()) / 86400000)
    if (diff >= 0 && diff < 30) cells[29 - diff] += 1
  })
  return cells.map((c) => (c === 0 ? 0 : c <= 1 ? 1 : c <= 2 ? 2 : c <= 3 ? 3 : 4))
})

/** 行动面板的最近 3 条上下文 */
const recentContext = computed(() =>
  focusTimeline.value.slice(0, 3).map((i) => ({ id: i.key, label: i.kindLabel, text: i.title, date: i.date }))
)

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

const pagedEvents = computed(() => events.value.slice((pageEvents.value - 1) * pageSizeEvents.value, pageEvents.value * pageSizeEvents.value))
const pagedVisits = computed(() => visits.value.slice((pageVisits.value - 1) * pageSizeVisits.value, pageVisits.value * pageSizeVisits.value))
const pagedPraises = computed(() => praises.value.slice((pagePraises.value - 1) * pageSizePraises.value, pagePraises.value * pageSizePraises.value))

function handleEventsSizeChange() { pageEvents.value = 1 }
function handleEventsCurrentChange() { /* v-model 已同步 */ }
function handleVisitsSizeChange() { pageVisits.value = 1 }
function handleVisitsCurrentChange() { /* v-model 已同步 */ }
function handlePraisesSizeChange() { pagePraises.value = 1 }
function handlePraisesCurrentChange() { /* v-model 已同步 */ }

/** 数据变短后把页码收回有效范围，避免出现空白页 */
watch([() => events.value.length, pageSizeEvents], () => {
  pageEvents.value = Math.min(pageEvents.value, Math.max(1, Math.ceil(events.value.length / pageSizeEvents.value)))
})
watch([() => visits.value.length, pageSizeVisits], () => {
  pageVisits.value = Math.min(pageVisits.value, Math.max(1, Math.ceil(visits.value.length / pageSizeVisits.value)))
})
watch([() => praises.value.length, pageSizePraises], () => {
  pagePraises.value = Math.min(pagePraises.value, Math.max(1, Math.ceil(praises.value.length / pageSizePraises.value)))
})

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
    ElMessage.warning('请先选择一名学生')
    return
  }
  if (key === 'record') recordVisible.value = true
  else if (key === 'visit') visitVisible.value = true
  else if (key === 'praise') praiseVisible.value = true
  else openContact('note')
}

function openPraise() {
  if (!focusId.value) {
    ElMessage.warning('请先选择一名学生，再发激励')
    return
  }
  praiseVisible.value = true
}

function openContact(channel: GuardianChannel, scene: GuardianScene = 'care') {
  if (!focusId.value) {
    ElMessage.warning('请先选择一名学生')
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

/** 家校子页内切换学生：与一级页聚焦保持同一份状态 */
function onGuardianSelect(s: StudentSummary | null) {
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

/** 从台账 / 清单点学生姓名：聚焦并进入学生关怀聚焦页 */
function openStudentFocus(id: number, name?: string) {
  focusStudentById(id, name)
  openPage('profile')
}

function focusAndRecord(id: number, name?: string) {
  focusStudentById(id, name)
  recordVisible.value = true
}

/** 闭环出口：跳到该生成长档案（学生成长档案页，深链直达该生） */
function gotoStudentById(id: number) {
  router.push({ path: '/teacher/portfolio', query: { student_id: String(id) } })
}

function gotoFocusStudent() {
  if (focusId.value) gotoStudentById(focusId.value)
}

/** 闭环出口：家校沟通已并入本页，直接打开子页 */
function gotoGuardianPage() {
  openPage('guardian')
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
  await Promise.all([loadHelp(), loadFocusExtras()])
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
    if (!(await actionConfirm(`确定删除「${e.title}」？`, '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  } catch {
    return
  }
  await deleteCareEvent(e.id)
  ElMessage.success('已删除')
  await loadAll()
}

async function removeVisit(v: HomeVisit) {
  try {
    if (!(await actionConfirm(`确定删除 ${v.student_name} 的家访记录？`, '删除确认', { danger: true, confirmButtonText: '删除' }))) return
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
    if (!(await actionConfirm(`确定删除 ${p.student_name} 的激励记录？`, '删除确认', { danger: true, confirmButtonText: '删除' }))) return
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

function onHelpTab(v: string | number) {
  helpStatusFilter.value = String(v) as HelpStatus | ''
}

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
      events: events.value.filter((e) => (e.event_date || '').slice(0, 10) === key),
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

  // 首屏默认聚焦第一位学生：关系地图直接有内容，避免「选一位学生」空态被误读成未实现
  if (!focusId.value && !focusName.value && allStudents.value.length) {
    const first = allStudents.value[0]
    focusStudent.value = first
    focusId.value = first.id
    focusName.value = first.name
    void loadFocusExtras()
  }

  // 合并后闭环：旧「家校沟通」入口重定向到本页并带 tab=guardian，
  // 从学生档案带来的 content / scene 直接在家校子页预填一条沟通记录
  const wantGuardian = String(route.query.tab || '') === 'guardian' || !!route.query.content
  const wantProfile = String(route.query.view || '') === 'profile'
  if (wantGuardian) {
    guardianPresetContent.value = route.query.content ? String(route.query.content) : ''
    guardianPresetScene.value = String(route.query.scene || 'care') as GuardianScene
    openPage('guardian')
    router.replace({
      path: '/teacher/care-center',
      query: focusId.value ? { student_id: String(focusId.value) } : {},
    })
  } else if (wantProfile && hasFocus.value) {
    // 闭环：学生档案的「关怀中心」直接落到该生关怀聚焦，而不是停在总览
    openPage('profile')
    router.replace({
      path: '/teacher/care-center',
      query: focusId.value ? { student_id: String(focusId.value) } : {},
    })
  }
})
</script>

<style scoped>
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* ================= 一级页 ================= */
.cc-shell {
  width: 100%;
  max-width: 960px;
  margin: 0 auto;
}

.cc-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.cc-head-title {
  margin: 0;
  font-size: var(--tui-fs-title);
  font-weight: 680;
  letter-spacing: -0.2px;
  color: var(--tui-text);
}
.cc-head-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--tui-text-quiet);
}

/* ================= 方案 C · 关系地图 ================= */
.cc-page {
  --cc-ink-line: #cfe0d7;
  --cc-ink-soft: #e9f4ef;
  --cc-ink: #12554a;
  background: #f7faf8;
}
.cc-subpage { background: #f7faf8; }

.cc-chips {
  display: flex;
  gap: 6px;
  margin: 0 0 10px;
  padding: 2px 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.cc-chips::-webkit-scrollbar { display: none; }
.cc-stu-chip {
  flex: 0 0 auto;
  padding: 5px 11px;
  border: 1px solid #d3e1da;
  border-radius: 999px;
  background: #fff;
  color: #5c756a;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.cc-stu-chip.on { background: var(--cc-ink); border-color: var(--cc-ink); color: #fff; }
.cc-stu-chip--more { color: #82958c; }
.cc-stu-chip--clear { color: #7b6a4a; border-color: #e3d9c9; }

.cc-relmap {
  margin-bottom: 14px;
  padding: 6px 0 12px;
  border-top: 1px solid var(--cc-ink-line);
  border-bottom: 1px solid var(--cc-ink-line);
}
.cc-relmap-empty {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 22px 4px;
  text-align: center;
}
.cc-relmap-empty b { font-size: 13px; font-weight: 650; color: #28443a; }
.cc-relmap-empty span { font-size: 11.5px; line-height: 1.6; color: #71867c; }
.cc-relmap-canvas {
  position: relative;
  width: 100%;
  max-width: 560px;
  /* 与 viewBox 保持同一比例，SVG 不会被留白，标签百分比坐标才能和圆点对齐 */
  aspect-ratio: 320 / 178;
  margin: 0 auto;
}
.cc-relmap-canvas svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.cc-relmap-center {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  padding: 0;
  border: none;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  background: var(--cc-ink);
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.cc-relmap-center span { font-size: 9px; font-weight: 400; color: #cfe6db; }
.cc-rel-node {
  position: absolute;
  width: 112px;
  margin-left: -56px;
  font-size: 9.5px;
  line-height: 1.45;
  color: #466056;
  text-align: center;
}
.cc-rel-node b { display: block; font-size: 11px; font-weight: 650; color: #1c332b; }
.cc-rel-node i { font-style: normal; font-size: 9px; color: #82958c; }
/* 标签按 SVG 圆点的百分比坐标对齐，桌面端放大后仍与连线端点重合 */
.cc-rel-node.n1 { left: 20.3%; top: 2%; }
.cc-rel-node.n2 { left: 79.7%; top: 1%; }
.cc-rel-node.n3 { left: 79.7%; bottom: 2%; }
.cc-rel-node.n4 { left: 20.3%; bottom: 2%; }
.cc-rel-node.is-dim b { color: #87968f; }
.cc-rel-node.is-dim i { color: #a0ada6; }

.cc-relmetric {
  display: flex;
  align-items: center;
  gap: 7px;
  max-width: 560px;
  margin: 0 auto;
  padding: 8px 0 0;
  border-top: 1px solid #e0ebe5;
}
.cc-relmetric b { font-size: 17px; font-weight: 750; color: #14201c; }
.cc-relmetric > span { font-size: 10.5px; color: #71867c; }
.cc-relmetric-sp { flex: 1; }
.cc-relmetric-tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--cc-ink-soft);
  color: #2c6b59 !important;
  font-size: 10px !important;
}

.cc-heat { max-width: 560px; margin: 10px auto 0; }
.cc-heat-hd { display: flex; align-items: baseline; gap: 8px; }
.cc-heat-hd span { font-size: 11px; font-weight: 650; color: #28443a; }
.cc-heat-hd b { margin-left: auto; font-size: 15px; font-weight: 750; color: #14201c; }
.cc-heat-hd b i { font-style: normal; font-size: 9px; font-weight: 400; color: #82958c; }
.cc-heat-grid { display: grid; grid-template-columns: repeat(15, 1fr); gap: 3px; margin-top: 6px; }
.cc-heat-grid i { aspect-ratio: 1 / 1; border-radius: 2px; background: #e7efe9; }
.cc-heat-grid i.l1 { background: #d7e8df; }
.cc-heat-grid i.l2 { background: #a9cdbb; }
.cc-heat-grid i.l3 { background: #5f9c83; }
.cc-heat-grid i.l4 { background: #1f6b57; }
.cc-heat-scale { display: flex; justify-content: space-between; margin-top: 4px; font-size: 9px; color: #96a89f; }

.cc-relmap-links {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  max-width: 560px;
  margin: 10px auto 0;
}
.cc-relmap-links .cc-link { color: #2c6b59; }

.cc-outline-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 9px;
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), border-color 0.15s var(--tui-ease);
}
.cc-outline-btn:hover { background: var(--tui-surface-muted); border-color: var(--tui-border-strong); color: var(--tui-text); }
.cc-outline-btn:disabled { opacity: 0.6; cursor: default; }
.cc-outline-btn :deep(.el-icon) { font-size: 13px; }
.cc-outline-btn--sm { height: 28px; padding: 0 9px; border-radius: 8px; font-size: 12px; }

.cc-focus-link {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin: 0 0 14px;
  padding: 10px 14px;
  border: none;
  border-left: 3px solid var(--tui-text);
  border-radius: 0;
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
}
.cc-focus-link:hover { background: var(--tui-surface-muted); }
.cc-focus-link > .el-icon:first-child { color: var(--tui-text-tertiary); }
.cc-focus-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-focus-text b { color: var(--tui-text); font-weight: 600; }
.cc-focus-arrow { color: var(--tui-text-quiet); flex-shrink: 0; }

/* ---------- 一级 · 平铺工作台（单容器 + 发丝分割，不做逐项卡片） ---------- */
.cc-block {
  margin-bottom: 14px;
  background: var(--tui-surface);
  border-top: 1px solid var(--tui-border);
  border-bottom: 1px solid var(--tui-border);
  overflow: hidden;
}
.cc-block-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 11px 14px 4px;
}
.cc-block-hd > span { font-size: 12px; font-weight: 650; color: var(--tui-text-secondary); }
.cc-block-note { font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-block-body { padding: 10px 14px 12px; }
.cc-block-body-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.cc-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-top: 1px solid var(--tui-hairline);
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.cc-row:active { background: var(--tui-surface-muted); }
.cc-row-ic {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--tui-surface-muted);
  color: var(--tui-text-secondary);
}
.cc-row-bd { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.cc-row-title { display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 600; color: var(--tui-text); }
.cc-row-badge {
  display: inline-block;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 9px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
  font-size: 10.5px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.cc-row-badge.is-warn { color: var(--tui-warn); border-color: var(--tui-warn-soft); background: var(--tui-warn-soft); }
.cc-row-sub {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cc-row-go { color: #cbd0d8; flex-shrink: 0; }
.cc-subpad--flat { gap: 0; }

/* 动作面板嵌在平铺块内时，不再叠一层卡片外框 */
.cc-block :deep(.cc-act) {
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}
/* 一级块已有「快速记录关怀」标题，避免面板再重复一行标题 */
.cc-block :deep(.cc-act .tui-section-head) { display: none; }
.cc-block :deep(.cc-act-card) {
  padding: 8px 2px;
  border: none;
  border-top: 1px solid var(--tui-hairline);
  border-radius: 0;
  background: transparent;
}
.cc-block :deep(.cc-act-card:hover),
.cc-block :deep(.cc-act-card.is-locked) { background: transparent; }

/* ================= 分区 / 常用小件（默认不加卡片外框） ================= */
.cc-card {
  padding: 12px 2px;
  background: transparent;
  border: none;
  border-top: 1px solid var(--tui-border);
  border-radius: 0;
  box-shadow: none;
}
.cc-card-hd { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.cc-card-hd h3 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 13.5px;
  font-weight: 650;
  color: var(--tui-text);
}
.cc-card-hd h3 .el-icon { font-size: 14px; color: var(--tui-text-tertiary); }
.cc-card-extra {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.cc-card-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0 0 12px;
  padding: 8px 10px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
  font-size: 11.5px;
  line-height: 1.6;
}
.cc-card-hint .el-icon { flex-shrink: 0; margin-top: 2px; font-size: 13px; }

.cc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 20px 12px;
  border-top: 1px solid var(--tui-hairline);
  border-bottom: 1px solid var(--tui-hairline);
  background: transparent;
  text-align: center;
}
.cc-empty--plain { border: none; padding: 18px 12px; }
.cc-empty-title { font-size: 12.5px; font-weight: 600; color: var(--tui-text-tertiary); }
.cc-empty-desc { font-size: 11.5px; line-height: 1.6; color: var(--tui-text-quiet); }

.cc-count { font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-text-quiet { color: var(--tui-text-quiet); }
.cc-more-note { font-size: 11.5px; color: var(--tui-text-quiet); padding: 6px 2px 0; }
.cc-link {
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  color: var(--tui-brand);
  cursor: pointer;
}
.cc-link:hover { text-decoration: underline; }
.cc-link-danger { color: var(--tui-danger); }
.cc-link-title {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 13px;
  color: var(--tui-text);
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cc-link-title:hover { color: var(--tui-brand); }

/* 最近动态 */
.cc-feed { display: flex; flex-direction: column; padding: 0 14px; }
.cc-feed-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border: none;
  border-top: 1px solid var(--tui-hairline);
  background: none;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.cc-feed-row:first-child { border-top: none; }
.cc-feed-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
}
.cc-feed-date { flex: 0 0 auto; font-size: 11px; color: var(--tui-text-quiet); }

/* ================= 二级页覆盖层（统一右滑进入） ================= */
.cc-page-stack {
  position: fixed;
  inset: 0;
  z-index: 300;
  pointer-events: none;
}
.cc-subpage {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: var(--tui-bg);
  overflow: hidden;
  pointer-events: auto;
}
.cc-slide-enter-active,
.cc-slide-leave-active { transition: transform 0.26s var(--tui-ease); }
.cc-slide-enter-from,
.cc-slide-leave-to { transform: translateX(100%); }

.cc-subhd {
  flex-shrink: 0;
  padding-top: env(safe-area-inset-top);
  background: var(--tui-surface);
  border-bottom: 1px solid var(--tui-border-strong);
}
.cc-subhd-in {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
}
.cc-subhd-back {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--tui-text);
  cursor: pointer;
}
.cc-subhd-back:active { background: var(--tui-surface-muted); }
.cc-subhd-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15.5px;
  font-weight: 650;
  letter-spacing: -0.2px;
  color: var(--tui-text);
}
.cc-subhd-act { flex: 0 0 auto; display: flex; align-items: center; gap: 8px; }

.cc-subbody {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: 12px 14px 28px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.cc-subbody::-webkit-scrollbar { display: none; width: 0; height: 0; }
.cc-sub-shell { width: 100%; max-width: 960px; margin: 0 auto; }
.cc-subpad { display: flex; flex-direction: column; gap: 12px; }

.cc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.cc-toolbar-meta { font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-toolbar-actions { display: flex; align-items: center; gap: 8px; }

/* ================= 列表 / 台账项（单容器 + 发丝分割） ================= */
.cc-list {
  display: flex;
  flex-direction: column;
  background: var(--tui-surface);
  border-top: 1px solid var(--tui-border);
  border-bottom: 1px solid var(--tui-border);
}
.cc-item {
  padding: 11px 14px;
  border: none;
  border-top: 1px solid var(--tui-hairline);
  border-radius: 0;
  background: transparent;
}
.cc-list .cc-item:first-child { border-top: none; }
.cc-item--warn { box-shadow: inset 3px 0 0 var(--tui-warn); }
.cc-item--brand { box-shadow: inset 3px 0 0 var(--tui-border-strong); }
.cc-item.st-pending { box-shadow: inset 3px 0 0 var(--tui-warn); }
.cc-item.st-processing { box-shadow: inset 3px 0 0 var(--tui-brand); }
.cc-item.st-resolved { box-shadow: inset 3px 0 0 var(--tui-success); }
.cc-item-main {
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
.cc-item-main:disabled { cursor: default; }
.cc-item-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
.cc-item-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.cc-item-name--flex {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cc-item-date { margin-left: auto; font-size: 11.5px; color: var(--tui-text-quiet); }
.cc-item-text {
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}
.cc-item-note { font-size: 11.5px; color: var(--tui-text-quiet); line-height: 1.5; }
.cc-item-sub { font-size: 11.5px; line-height: 1.5; color: var(--tui-warn); }
.cc-item-follow {
  margin-top: 6px;
  padding: 5px 8px;
  border-radius: 7px;
  background: var(--tui-warn-soft);
  font-size: 11.5px;
  color: var(--tui-warn);
}
.cc-item-ops { display: flex; align-items: center; gap: 12px; margin-top: 8px; flex-wrap: wrap; }
.cc-item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  flex-wrap: wrap;
}
.cc-item-action { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.cc-item-action--end { margin-left: auto; }

.cc-status { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; }
.cc-status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.cc-status.is-pending { color: var(--tui-warn); }
.cc-status.is-done { color: var(--tui-success); }

/* ================= 求助信箱 ================= */
.cc-help-status { font-size: 11px; font-weight: 600; border-radius: 999px; padding: 1px 8px; }
.cc-help-status.st-pending { background: var(--tui-warn-soft); color: var(--tui-warn); }
.cc-help-status.st-processing { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.cc-help-status.st-resolved { background: var(--tui-success-soft); color: var(--tui-success); }
.cc-help-reply {
  margin-top: 7px;
  padding: 7px 9px;
  border-radius: 8px;
  background: var(--tui-surface-muted);
  border-left: 3px solid var(--tui-border-strong);
}
.cc-help-reply-label { display: block; font-size: 11px; font-weight: 700; color: var(--tui-text-tertiary); margin-bottom: 2px; }
.cc-help-reply-text { font-size: 12px; color: var(--tui-text-secondary); line-height: 1.6; white-space: pre-wrap; }

/* ================= 关怀看板 ================= */
.cc-gauge { margin-bottom: 12px; }
/* TempGauge 自带纯文本 tips 在此隐藏，改由下方可点击的加温行动承载 */
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

.cc-chart-legend { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.cc-chart-chip { font-size: 11.5px; font-weight: 600; border-radius: 999px; padding: 3px 9px; }
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
  display: flex;
  justify-content: space-between;
  padding-top: 5px;
  font-size: 11px;
  color: var(--tui-text-quiet);
}

.cc-cal-nav {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--tui-border);
  border-radius: 7px;
  background: var(--tui-surface);
  color: var(--tui-text-tertiary);
  cursor: pointer;
}
.cc-cal-nav:active { background: var(--tui-surface-muted); }
.cc-cal-title { min-width: 92px; text-align: center; font-size: 12px; font-weight: 600; color: var(--tui-text-secondary); }
.cc-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.cc-week span { text-align: center; font-size: 11px; color: var(--tui-text-quiet); }
.cc-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cc-cell {
  min-height: 56px;
  border: 1px solid var(--tui-border);
  border-radius: 8px;
  padding: 4px 5px;
  background: var(--tui-surface);
  display: flex;
  flex-direction: column;
  gap: 3px;
  overflow: hidden;
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

/* ================= 学生关怀聚焦 ================= */
.cc-profile-hero {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 2px 12px;
  border: none;
  border-bottom: 1px solid var(--tui-border);
  border-radius: 0;
  background: var(--tui-surface);
  box-shadow: none;
}
.cc-profile-ava {
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  border-radius: 50%;
  border: none;
  background: var(--cc-ink);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}
.cc-profile-ava img { width: 100%; height: 100%; object-fit: cover; }
.cc-profile-info { flex: 1; min-width: 0; }
.cc-profile-name { font-size: 17px; font-weight: 700; color: #14201c; }
.cc-profile-meta { margin-top: 3px; font-size: 11.5px; color: var(--tui-text-quiet); }

.cc-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 12px;
  border-top: 1px solid var(--cc-ink-line);
  border-bottom: 1px solid var(--cc-ink-line);
}
.cc-facts > div { padding: 9px 4px; border-left: 1px solid var(--cc-ink-line); text-align: center; }
.cc-facts > div:first-child { border-left: none; }
.cc-facts b { display: block; font-size: 18px; font-weight: 700; line-height: 1.2; color: #14201c; font-variant-numeric: tabular-nums; }
.cc-facts span { display: block; margin-top: 2px; font-size: 10.5px; color: #71867c; }

.cc-quick-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }
.cc-quick {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 6px;
  border: 1px solid var(--cc-ink-line);
  border-radius: 6px;
  background: #fff;
  color: #3f5c50;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.cc-quick:hover { border-color: #b9d2c6; color: #12554a; background: #fbfefc; }
.cc-quick .el-icon { color: #2c6b59; font-size: 14px; }

.cc-flat { margin-top: 16px; }
.cc-flat-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 7px;
  border-bottom: 1px solid var(--cc-ink-line);
  font-size: 12px;
  font-weight: 650;
  color: #28443a;
}
.cc-flat-note { margin-left: auto; font-size: 11px; font-weight: 400; color: #82958c; }
.cc-flat-hd .cc-link { margin-left: auto; color: #2c6b59; }

/* 学生聚焦：支持网络迷你图 */
.cc-relmap-mini {
  position: relative;
  height: 150px;
  margin-top: 10px;
  border: 1px solid var(--cc-ink-line);
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}
.cc-relmap-mini svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.cc-mmap-center {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #12554a;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .02em;
}
.cc-rel-legend { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 12px; padding-top: 8px; }
.cc-rel-legend > span {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  font-size: 10px;
  line-height: 1.6;
  color: #6c8177;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cc-rel-legend i { width: 5px; height: 5px; border-radius: 50%; background: #8fb8a6; flex: none; }
.cc-rel-legend b { font-weight: 650; color: #28443a; }
.cc-rel-legend > span.is-dim { color: #a0ada6; }
.cc-rel-legend > span.is-dim i { background: #d3ded8; }
.cc-rel-legend > span.is-dim b { color: #87968f; }
.cc-support-tip {
  margin-top: 10px;
  padding: 8px 10px;
  border-left: 2px solid #2c6b59;
  background: #eef6f1;
  font-size: 11.5px;
  line-height: 1.65;
  color: #587267;
}
.cc-support-tip b { color: #1f5747; }

/* 学生聚焦：时间轴（左日期 / 右事实） */
.cc-tl2 { margin-top: 2px; }
.cc-tl2-item {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #e3ece6;
}
.cc-tl2-date { font-size: 9.5px; color: #82958c; line-height: 1.4; }
.cc-tl2-date b { display: block; font-size: 15px; font-weight: 700; color: #28443a; }
.cc-tl2-body { position: relative; padding-left: 10px; border-left: 1px solid var(--cc-ink-line); }
.cc-tl2-body::before {
  content: '';
  position: absolute;
  left: -3.5px;
  top: 3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8fb8a6;
}
.cc-tl2-top { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.cc-tl2-kind {
  flex: none;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--cc-ink-soft);
  color: #2c6b59;
  font-size: 10px;
}
.cc-tl2-title { flex: 1; min-width: 0; font-size: 12.5px; font-weight: 600; color: #14201c; }
.cc-tl2-body p { margin-top: 3px; font-size: 11.5px; line-height: 1.6; color: #5f776c; white-space: pre-wrap; }

/* ================= 弹窗表单 ================= */
.cc-fu-form { display: flex; flex-direction: column; gap: 14px; }
.cc-fu-quote,
.cc-reply-quote {
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  padding: 9px 11px;
  background: var(--tui-surface-muted);
}
.cc-fu-quote-top,
.cc-reply-quote-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cc-fu-quote-body,
.cc-reply-quote-body {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}
.cc-fu-field,
.cc-reply-field { display: flex; flex-direction: column; gap: 7px; }
.cc-fu-label,
.cc-reply-label { font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary); }
.cc-fu-label .req,
.cc-reply-label .req { margin-left: 2px; color: var(--tui-danger); }
.cc-help-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.cc-reply-form { display: flex; flex-direction: column; gap: 14px; }

/* ================= 响应式 ================= */
@media (min-width: 768px) {
  .cc-subbody { padding: 16px 18px 32px; }
  .cc-quick-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  /* 关系图在宽屏下按比例放大，节点文字同步放大，避免图上文字过小 */
  .cc-relmap-canvas { max-width: 520px; }
  .cc-rel-node { width: 132px; margin-left: -66px; font-size: 10.5px; }
  .cc-rel-node b { font-size: 12.5px; }
  .cc-rel-node i { font-size: 10px; }
  .cc-relmap-center { width: 74px; height: 74px; font-size: 15px; }
  .cc-relmap-center span { font-size: 10px; }
}

@media (max-width: 767px) {
  .cc-row-sub { font-size: 11px; }
  .cc-cell { min-height: 50px; }
  .cc-cell-events { display: none; }
  .cc-subhd-in { padding: 6px 14px; }
  .cc-subhd-title { font-size: 15px; }
}
</style>
