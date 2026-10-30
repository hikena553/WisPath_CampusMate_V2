<template>
  <div class="plan-page" :class="{ 'is-embedded': embedded }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <!-- embedded 模式（v4 收编为学业中心第 5 个 tab）：隐藏自带顶栏，由父级子页 Head 接管 -->
    <SubPageHeader v-if="!embedded" title="学习计划" fallback="/student" />
    <!-- 移动端下拉刷新：吉祥物指示器（与学业中心 / 工作台共用同一模块） -->
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />
    <!-- 顶部品牌主视觉（桌面） -->
    <div v-if="!isMobile" class="plan-hero">
      <div class="hero-glow g1"></div>
      <div class="hero-glow g2"></div>
      <div class="hero-glow g3"></div>
      <div class="hero-top">
        <div class="hero-heading">
          <div class="hero-title-row">
            <span class="hero-kicker">MY PLAN · 学习计划</span>
            <el-tag class="hero-tag" effect="dark" round>学业中心</el-tag>
          </div>
          <h2 class="hero-title">把大目标，拆成一个个小关卡</h2>
          <p class="hero-sub">逐关消除、提交成果、AI 评估，稳步达成总目标</p>
        </div>
        <el-button class="hero-add" round @click="openPlanDialog()">
          <el-icon style="margin-right:4px"><Plus /></el-icon>新建计划
        </el-button>
      </div>
      <div class="hero-stats">
        <div class="hero-stat">
          <span class="hs-num">{{ streak.longest || 0 }}</span>
          <span class="hs-label">最长连续(天)</span>
        </div>
        <div class="hero-stat-sep"></div>
        <div class="hero-stat">
          <span class="hs-num">{{ streak.current || 0 }}</span>
          <span class="hs-label">当前连续(天)</span>
        </div>
        <div class="hero-stat-sep"></div>
        <div class="hero-stat">
          <span class="hs-num">{{ totalMinutes }}</span>
          <span class="hs-label">累计学习(分钟)</span>
        </div>
      </div>
    </div>

    <!-- ==================================================================
         移动端（v8 重构）
         信息只留三块：① 今天的工作量 ② 今天要做 ③ 闯关流
         首次进入先立一个保底目标（AI 拆关卡），之后可继续新增目标
         ================================================================== -->
    <div v-if="isMobile" class="pm">
      <!-- ---------- 首次进入：立目标 ---------- -->
      <section v-if="pmNeedOnboarding" class="pm-gate">
        <span class="pm-gate-ico">🎯</span>
        <h1 class="pm-gate-h">先给自己立一个目标</h1>
        <p class="pm-gate-p">选一个最近最想达成的事。AI 会结合你的成长档案和每天的状态，把它拆成一条每天都能推进的闯关路线。</p>
        <div class="pm-preset-grid">
          <button
            v-for="p in pmPresets" :key="p.label" type="button"
            class="pm-preset" :class="{ on: pmGoalTitle === p.title }"
            @click="pmPickPreset(p)"
          >
            <span class="pm-preset-ico">{{ p.icon }}</span>
            <span class="pm-preset-t">{{ p.label }}</span>
          </button>
        </div>
        <label class="pm-gate-field">
          <input v-model="pmGoalTitle" type="text" maxlength="40" placeholder="或者，写一句你自己的目标" />
        </label>
        <button type="button" class="pm-gate-cta" :disabled="pmCreating" @click="pmCreateGoal">
          {{ pmCreating ? 'AI 正在拆解闯关路线…' : '开始我的闯关' }}
        </button>
        <p class="pm-gate-tip">先定一个保底目标就好，之后随时可以再加</p>
      </section>

      <template v-else>
        <!-- ---------- ① 今天的工作量 ---------- -->
        <section class="pm-hero">
          <div class="pm-hero-top">
            <div>
              <p class="pm-date">{{ pmDateText }}</p>
              <h1 class="pm-hi">{{ pmGreeting }}</h1>
            </div>
            <div class="pm-streak" :class="{ zero: !streak.current }">
              <span class="pm-streak-ico">🔥</span>
              <b>{{ streak.current }}</b>
              <span class="pm-streak-u">天</span>
            </div>
          </div>

          <div class="pm-hero-main">
            <div class="pm-dial">
              <svg class="pm-dial-svg" viewBox="0 0 84 84" aria-hidden="true">
                <circle class="pm-dial-bg" cx="42" cy="42" r="36" />
                <circle
                  class="pm-dial-fg" cx="42" cy="42" r="36"
                  :stroke-dasharray="`${(pmTodayPct * 2.262).toFixed(1)} 226.2`"
                />
              </svg>
              <div class="pm-dial-txt">
                <b>{{ pmTodayDone }}<i>/{{ pmTodayTotal }}</i></b>
                <span>已完成</span>
              </div>
            </div>
            <div class="pm-hero-side">
              <div class="pm-kv"><span>预计投入</span><b>{{ pmTodayMinutes }}<i>分钟</i></b></div>
              <div class="pm-kv"><span>今天已投入</span><b>{{ pmInvestedToday }}<i>分钟</i></b></div>
              <div class="pm-kv"><span>最长连击</span><b>{{ streak.longest || 0 }}<i>天</i></b></div>
            </div>
          </div>

          <div class="pm-load">
            <div class="pm-load-line">
              <span class="pm-load-t">今日负荷 · {{ pmLoadLabel }}</span>
              <span class="pm-load-v">{{ pmTodayTotal }} 个任务 / {{ pmTodayMinutes }} 分钟</span>
            </div>
            <div class="pm-load-bar"><i :style="{ width: pmLoadPct + '%' }"></i></div>
          </div>
        </section>

        <!-- ---------- ② 今天要做 ---------- -->
        <section class="pm-card">
          <header class="pm-sec-head">
            <h2 class="pm-sec-h">今天要做</h2>
            <button type="button" class="pm-sec-act" @click="pmOpenQuick">＋ 加一条</button>
          </header>

          <div v-if="pmOverdue.length" class="pm-overdue">
            <el-icon :size="13"><WarningFilled /></el-icon>
            <span>{{ pmOverdue.length }} 项已逾期，今天先把它补掉</span>
          </div>

          <ul v-if="todayTasks.length" class="pm-tasks">
            <li
              v-for="(t, i) in pmTasksShown" :key="t.task_id ?? 'x' + i"
              class="pm-task" :class="{ done: t.checked_today, late: pmIsLate(t) }"
            >
              <button
                type="button" class="pm-check" :aria-pressed="t.checked_today"
                :aria-label="t.checked_today ? '撤销打卡' : '打卡完成'"
                @click="handleCheckinFromToday(t)"
              >
                <svg v-if="t.checked_today" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M4.6 10.4l3.3 3.3 7.5-7.5" />
                </svg>
              </button>
              <div class="pm-task-body">
                <p class="pm-task-t">{{ t.title }}</p>
                <p class="pm-task-m">
                  <span class="pm-task-plan">{{ t.plan_title }}</span>
                  <span class="pm-sep">·</span>{{ pmTaskMinutes(t) }} 分钟
                  <template v-if="pmIsLate(t)">
                    <span class="pm-sep">·</span><em class="pm-task-late">逾期 {{ pmLateDays(t) }} 天</em>
                  </template>
                </p>
              </div>
            </li>
          </ul>
          <p v-else class="pm-empty">今天没有到期的任务，去闯关流推进主线吧</p>
          <button v-if="pmTasksRest" type="button" class="pm-more" @click="pmShowAll = !pmShowAll">
            {{ pmShowAll ? '收起' : `还有 ${pmTasksRest} 条` }}
          </button>

          <div v-if="pmQuickOpen" class="pm-quick">
            <input
              v-model="pmQuickTitle" type="text" maxlength="60"
              placeholder="今天还想做什么？" @keyup.enter="pmAddQuick"
            />
            <button type="button" class="pm-quick-save" :disabled="pmQuickSaving" @click="pmAddQuick">
              {{ pmQuickSaving ? '…' : '加入' }}
            </button>
            <button type="button" class="pm-quick-cancel" @click="pmQuickOpen = false">取消</button>
          </div>
        </section>

        <!-- ---------- ③ 闯关流 ---------- -->
        <section class="pm-card pm-quest">
          <header class="pm-sec-head">
            <h2 class="pm-sec-h">闯关流</h2>
            <div class="pm-quest-tools">
              <button
                v-if="pmCanRebuild"
                type="button" class="pm-quest-rebuild"
                :disabled="aiGenLoading === pmPlan?.id"
                @click="pmPlan && handleAiGenerate(pmPlan.id, true)"
              >{{ aiGenLoading === pmPlan?.id ? '重拆中…' : '重新拆解' }}</button>
              <span v-if="pmStages.length" class="pm-quest-count">{{ pmStageDone }}/{{ pmStages.length }} 关</span>
            </div>
          </header>
          <p v-if="pmPlan" class="pm-quest-plan">
            {{ pmPlan.title }}<template v-if="pmCurrentStage"> · 正在闯第 {{ pmStages.indexOf(pmCurrentStage) + 1 }} 关</template>
          </p>

          <div v-if="!pmStages.length" class="pm-quest-empty">
            <p>还没有闯关路线。让 AI 按你的成长档案，把这个目标拆成 4~6 关。</p>
            <button
              type="button" class="pm-quest-ai"
              :disabled="aiGenLoading === pmPlan?.id"
              @click="pmPlan && handleAiGenerate(pmPlan.id)"
            >
              <el-icon :size="14"><MagicStick /></el-icon>
              {{ aiGenLoading === pmPlan?.id ? 'AI 拆解中…' : 'AI 拆解关卡' }}
            </button>
          </div>

          <div v-else class="pm-track">
            <template v-for="(s, i) in pmStages" :key="s.id">
              <div class="pm-step" :class="{ open: expandedStageId === s.id, 'has-line': i < pmStages.length - 1 }">
                <div class="pm-step-rail">
                  <button
                    type="button" class="pm-node" :class="'is-' + s.status"
                    :style="{ '--fill': pmFill(s) + '%' }"
                    :aria-label="`${s.title}（${s.status === 'done' ? '已通关' : s.status === 'locked' ? '未解锁' : '进行中'}）`"
                    @click="pmPlan && toggleStageExpand(pmPlan.id, s.id)"
                  >
                    <i class="pm-node-fill" aria-hidden="true"></i>
                    <span class="pm-node-face">
                      <el-icon v-if="s.status === 'done'" :size="22"><Check /></el-icon>
                      <el-icon v-else-if="s.status === 'locked'" :size="15"><Lock /></el-icon>
                      <b v-else>{{ i + 1 }}</b>
                    </span>
                  </button>
                </div>
                <div class="pm-step-body">
                  <div class="pm-step-top">
                    <p class="pm-step-t">{{ s.title }}</p>
                    <span class="pm-step-v" :class="'is-' + s.status">
                      {{ s.status === 'done' ? '已通关' : s.status === 'locked' ? '未解锁' : pmFill(s) + '%' }}
                    </span>
                  </div>
                  <p class="pm-step-m">
                    {{ pmStageTaskList(s).length }} 个任务
                    <template v-if="s.score != null"><span class="pm-sep">·</span>AI {{ s.score }} 分</template>
                    <template v-else-if="s.status === 'active'"><span class="pm-sep">·</span><b class="pm-step-go">点方块继续</b></template>
                  </p>

                  <!-- 分支：这一关里的任务（主线不动，分支越攒越多） -->
                  <div v-if="expandedStageId === s.id" class="pm-branch">
                    <p v-if="s.goal" class="pm-branch-goal">{{ s.goal }}</p>
                    <ul v-if="pmStageTaskList(s).length" class="pm-branch-list">
                      <li
                        v-for="t in pmStageTaskList(s)" :key="t.id"
                        class="pm-branch-item" :class="{ done: t.status === 'done' }"
                      >
                        <button
                          type="button" class="pm-branch-check"
                          :aria-label="t.status === 'done' ? '标记未完成' : '标记完成'"
                          @click="setTaskStatus(t, t.status === 'done' ? 'doing' : 'done')"
                        >
                          <el-icon v-if="t.status === 'done'" :size="11"><Check /></el-icon>
                        </button>
                        <span class="pm-branch-t">{{ t.title }}</span>
                      </li>
                    </ul>
                    <p v-else class="pm-branch-empty">这一关还没有任务，加几条让液面涨起来</p>
                    <div class="pm-branch-acts">
                      <button type="button" @click="pmPlan && openStageTaskDialog(pmPlan.id, s.id)">＋ 任务</button>
                      <button
                        v-if="s.status === 'active' || s.status === 'submitted'"
                        type="button" class="primary" @click="openSubmitDialog(s)"
                      >{{ s.status === 'submitted' ? '重新提交' : '提交成果' }}</button>
                      <button v-if="s.status === 'submitted'" type="button" @click="confirmStageDone(s)">确认通关</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 阶段奖励：每 3 关一个宝箱 -->
              <div v-if="(i + 1) % 3 === 0" class="pm-reward" :class="{ on: pmRewardDone(i) }">
                <span class="pm-reward-ico">{{ pmRewardDone(i) ? '🎁' : '🔒' }}</span>
                <span class="pm-reward-t">
                  {{ pmRewardDone(i) ? `第 ${i + 1} 关奖励已解锁` : `再通关 ${i + 1 - pmStageDone} 关解锁奖励` }}
                </span>
              </div>
            </template>
          </div>

          <div class="pm-quest-foot">
            <button type="button" @click="pmPlan && openStageDialog(pmPlan.id)">＋ 添加关卡</button>
            <button v-if="pmBranchTasks().length" type="button" @click="pmBranchOpen = !pmBranchOpen">
              支线 {{ pmBranchTasks().length }}{{ pmBranchOpen ? ' ▴' : ' ▾' }}
            </button>
          </div>

          <ul v-if="pmBranchOpen && pmBranchTasks().length" class="pm-branch-list pm-branch-standalone">
            <li
              v-for="t in pmBranchTasks()" :key="t.id"
              class="pm-branch-item" :class="{ done: t.status === 'done' }"
            >
              <button
                type="button" class="pm-branch-check"
                :aria-label="t.status === 'done' ? '标记未完成' : '标记完成'"
                @click="setTaskStatus(t, t.status === 'done' ? 'doing' : 'done')"
              >
                <el-icon v-if="t.status === 'done'" :size="11"><Check /></el-icon>
              </button>
              <span class="pm-branch-t">{{ t.title }}</span>
            </li>
          </ul>
        </section>

        <!-- ---------- 目标 / 主线（一行，可切换） ---------- -->
        <section class="pm-goal">
          <button v-if="goals.length" type="button" class="pm-goal-main" @click="openGoalDialog(goals[0])">
            <span class="pm-goal-ico">🎯</span>
            <span class="pm-goal-txt">
              <b>{{ goals[0].title }}</b>
              <em>{{ goals[0].goal_type }}<template v-if="goals.length > 1"> · 共 {{ goals.length }} 个目标</template></em>
            </span>
          </button>
          <button v-else type="button" class="pm-goal-main is-empty" @click="openGoalDialog()">
            <span class="pm-goal-ico">🎯</span>
            <span class="pm-goal-txt">
              <b>还没有长期目标</b>
              <em>立一个，AI 才能按它拆主线</em>
            </span>
          </button>
          <button v-if="plans.length > 1" type="button" class="pm-goal-add" @click="pmSwitcherOpen = true">
            切换主线
          </button>
          <button v-else type="button" class="pm-goal-add" @click="openGoalDialog()">＋ 新目标</button>
        </section>

        <!-- 主线切换浮层 -->
        <div v-if="pmSwitcherOpen" class="pm-sheet-mask" @click.self="pmSwitcherOpen = false">
          <div class="pm-sheet">
            <div class="pm-sheet-bar" aria-hidden="true"></div>
            <h3 class="pm-sheet-h">切换主线</h3>
            <ul class="pm-sheet-list">
              <li v-for="p in plans" :key="p.id">
                <button
                  type="button" class="pm-sheet-item" :class="{ on: pmPlan?.id === p.id }"
                  @click="pmSelectedPlanId = p.id; pmSwitcherOpen = false; loadStages(p.id)"
                >
                  <span class="pm-sheet-name">{{ p.title }}</span>
                  <span class="pm-sheet-meta">{{ p.goal_title || '未挂目标' }} · {{ p.task_done }}/{{ p.task_total }} 任务</span>
                  <span v-if="pmPlan?.id === p.id" class="pm-sheet-cur">当前</span>
                </button>
              </li>
            </ul>
            <button type="button" class="pm-sheet-close" @click="pmSwitcherOpen = false">关闭</button>
          </div>
        </div>
      </template>
    </div>

    <div v-else class="content">
    <!-- 今日打卡 -->
    <div class="card today-card" :class="{ 'checked': streak.today_checked }">
      <div class="today-head">
        <div class="today-left">
          <div class="today-ring" :class="{ 'ring-on': streak.today_checked }">
            <el-icon v-if="streak.today_checked" :size="18"><Check /></el-icon>
            <template v-else><span class="ring-empty">!</span></template>
          </div>
          <div class="today-title-wrap">
            <div class="today-title">今日打卡</div>
            <div class="today-hint">{{ streak.today_checked ? '今天已坚持，继续保持' : '开始今天的进度吧' }}</div>
          </div>
        </div>
        <el-tag size="small" :type="streak.today_checked ? 'success' : 'warning'" effect="light" round class="today-badge">
          {{ streak.today_checked ? '已打卡' : '未打卡' }}
        </el-tag>
      </div>
      <div v-if="reminderList.length" class="reminder-box">
        <div v-for="(r, i) in reminderList" :key="i" class="reminder-item">
          <el-icon :size="14" style="color:#e6a23c;flex-shrink:0"><WarningFilled /></el-icon>
          <span class="reminder-text">{{ r }}</span>
        </div>
      </div>
    </div>

    <!-- 今日任务 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">今日任务</span>
        <el-button size="small" text type="primary" :loading="aiLoading" @click="runAISuggest">AI 顺延/重排建议</el-button>
      </div>
      <div v-if="!todayTasks.length" class="empty-block">
        <div class="empty-ico">🌤️</div>
        <div class="empty-msg">今天没有到期任务<br />好好休息，或提前推进明天的进度吧</div>
      </div>
      <div v-for="(t, idx) in todayTasks" :key="t.task_id ?? 't' + idx" class="today-task">
        <el-checkbox
          :model-value="t.checked_today"
          @change="() => handleCheckinFromToday(t)"
        />
        <div class="today-task-info">
          <div class="today-task-title" :class="{ 'task-done': t.status === 'done' }">{{ t.title }}</div>
          <div class="today-task-meta">
            <span class="meta-plan"><el-icon :size="12"><MagicStick /></el-icon>{{ t.plan_title }}</span>
            <el-tag v-if="t.due_date" size="small" type="danger" effect="plain" round class="meta-tag">
              {{ t.due_date }}
            </el-tag>
            <el-tag size="small" :type="t.checked_today ? 'success' : 'info'" effect="light" round class="meta-tag">
              {{ t.checked_today ? '已打卡' : '未打卡' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 计划列表 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">我的计划</span>
      </div>
      <div class="plan-filter">
        <el-tag
          v-for="f in planFilters"
          :key="f.value"
          :type="planStatus === f.value ? 'primary' : 'info'"
          :effect="planStatus === f.value ? 'dark' : 'plain'"
          class="filter-tag" round
          @click="switchPlanStatus(f.value)"
        >{{ f.label }}</el-tag>
      </div>
      <div v-if="!plans.length && planStatus !== 'active'" class="empty-block">
        <div class="empty-ico">🗂️</div>
        <div class="empty-msg">暂无{{ planStatusLabel }}的计划</div>
      </div>
      <div v-if="!plans.length && planStatus === 'active'" class="empty-block">
        <div class="empty-ico">🚀</div>
        <div class="empty-msg">还没有进行中的计划<br />点击「新建计划」，让 AI 帮你拆解闯关吧</div>
      </div>
      <div v-for="p in plans" :key="p.id" class="plan-card" :class="{ 'plan-expanded': expandedPlan === p.id }">
        <div class="plan-card-head" @click="toggleExpand(p.id)">
          <div class="plan-ico" :style="{ background: planGrad(p.id) }">
            <template v-if="p.done_rate >= 100">🎉</template>
            <template v-else>{{ (p.title || '?').slice(0, 1) }}</template>
          </div>
          <div class="plan-card-left">
            <div class="plan-title-line">
              <span class="plan-card-title">{{ p.title }}</span>
              <el-tag v-if="p.goal_title" size="small" class="goal-chip" effect="light" round>🎯 {{ p.goal_title }}</el-tag>
            </div>
            <div class="plan-card-meta">
              <span class="meta-date"><el-icon :size="12"><Calendar /></el-icon>{{ p.start_date }} ~ {{ p.end_date || '至今' }}</span>
            </div>
          </div>
          <el-icon class="expand-icon" :class="{ rotated: expandedPlan === p.id }"><ArrowDown /></el-icon>
        </div>
        <div class="plan-progress">
          <div class="plan-progress-head">
            <span class="pp-label">整体完成度</span>
            <span class="pp-rate" :style="{ color: progressColor(p.done_rate) }">{{ p.done_rate }}%</span>
          </div>
          <el-progress :percentage="p.done_rate" :stroke-width="8" :show-text="false" :color="progressColor(p.done_rate)" />
        </div>
        <div class="plan-card-stats">
          <span class="stat"><span class="stat-dot d-task"></span>任务 <b>{{ p.task_done }}/{{ p.task_total }}</b></span>
          <span class="stat" :class="{ 'stat-warn': p.overdue > 0 }"><span class="stat-dot d-overdue"></span>逾期 <b>{{ p.overdue }}</b></span>
          <span class="stat"><span class="stat-dot d-checkin"></span>打卡 <b>{{ p.checkin_days }} 天</b></span>
        </div>
        <div v-if="expandedPlan === p.id" class="plan-detail">
          <div v-if="p.objective" class="plan-objective">{{ p.objective }}</div>
          <div class="detail-actions">
            <el-button size="small" plain type="primary" @click="openTaskDialog(p.id)"><el-icon style="margin-right:4px"><Plus /></el-icon>添加任务</el-button>
            <el-button size="small" plain type="warning" @click="openPlanDialog(p)">编辑计划</el-button>
            <el-button size="small" plain type="primary" :loading="aiLoading" @click="runAISuggest(p.id)">AI 建议</el-button>
            <el-button size="small" plain type="danger" @click="handleDeletePlan(p.id)">删除</el-button>
          </div>

          <!-- 闯关任务流（游戏进阶模式） -->
          <div class="stage-section">
            <div class="stage-head">
              <div class="stage-head-left">
                <span class="stage-title">闯关任务流</span>
                <el-tag v-if="stagesByPlan[p.id]?.length" size="small" effect="light" round>
                  {{ stageProgress(p.id).done }}/{{ stageProgress(p.id).total }} 关
                </el-tag>
              </div>
              <div class="stage-actions">
                <el-button
                  v-if="!stagesByPlan[p.id]?.length"
                  size="small"
                  type="primary"
                  round
                  :loading="aiGenLoading === p.id"
                  @click="handleAiGenerate(p.id)"
                >
                  <el-icon style="margin-right:4px"><MagicStick /></el-icon>AI 拆解关卡
                </el-button>
                <el-button size="small" plain type="primary" round @click="openStageDialog(p.id)">
                  <el-icon style="margin-right:4px"><Plus /></el-icon>添加阶段
                </el-button>
              </div>
            </div>

            <div v-if="!stagesByPlan[p.id]?.length" class="stage-empty">
              让 AI 把计划拆解成闯关关卡，逐关完成、提交成果，AI 评估打分并调整后续任务，助你更稳地达成总目标。
            </div>

            <!-- 消消乐糖果关卡网格 -->
            <template v-else>
              <div class="candy-topbar">
                <div class="candy-lv" :class="{ 'is-done': stageProgress(p.id).done === stageProgress(p.id).total }">
                  <span class="candy-lv-num">{{ stageProgress(p.id).done }}</span>
                  <span class="candy-lv-x">/{{ stageProgress(p.id).total }}</span>
                  <span class="candy-lv-label">通关</span>
                </div>
                <div class="candy-track">
                  <div class="candy-track-fill" :style="{ width: candyPercent(p.id) + '%' }"></div>
                  <span class="candy-track-tip">{{ candyPercent(p.id) }}%</span>
                </div>
                <div class="candy-streak">
                  <span class="candy-streak-x">✦</span>
                  <span class="candy-streak-num">{{ candyStarTotal(p.id) }}</span>
                </div>
              </div>

              <div class="candy-grid">
                <div
                  v-for="(s, idx) in stagesByPlan[p.id]"
                  :key="s.id"
                  class="candy-block"
                  :class="'cb-' + s.status + (expandedStageId === s.id ? ' is-open' : '')"
                  @click="toggleStageExpand(p.id, s.id)"
                >
                  <template v-if="s.status === 'locked'">
                    <div class="cb-lock"><el-icon :size="16"><Lock /></el-icon></div>
                    <div class="cb-face">?</div>
                  </template>
                  <template v-else-if="s.status === 'active'">
                    <div class="cb-no">{{ idx + 1 }}</div>
                    <div class="cb-emoji">{{ candyEmoji(idx) }}</div>
                  </template>
                  <template v-else-if="s.status === 'submitted'">
                    <div class="cb-score">{{ s.score ?? '?' }}</div>
                    <div class="cb-stars">{{ scoreStars(s.score) }}</div>
                  </template>
                  <template v-else>
                    <div class="cb-ok el-icon-ok"><el-icon :size="26"><Check /></el-icon></div>
                    <div class="cb-stars">{{ scoreStars(s.score) }}</div>
                  </template>
                  <div class="cb-title">{{ s.title }}</div>
                  <div class="cb-dot" :class="'dot-' + s.status"></div>
                  <!-- v7 移动端：当前关卡的「开始」气泡（Duolingo 的 START 气泡），桌面端不显示 -->
                  <span v-if="s.status === 'active'" class="cb-start" aria-hidden="true">开始</span>
                </div>
              </div>
              <div class="candy-hint" :class="{ 'is-done': stageProgress(p.id).done === stageProgress(p.id).total }">
                {{ candyHint(p.id) }}
              </div>
            </template>

            <!-- 展开的关卡详情 -->
            <div v-for="s in stagesByPlan[p.id] || []" :key="'d' + s.id">
              <div v-if="expandedStageId === s.id" class="stage-detail">
                <div class="stage-goal">{{ s.goal || '本关目标：按阶段任务推进，完成后提交成果' }}</div>

                <!-- AI 评估报告 -->
                <div v-if="s.status === 'submitted' || s.status === 'done'" class="stage-report">
                  <div class="report-score">
                    <div class="report-score-num" :style="{ color: scoreColor(s.score) }">{{ s.score ?? '-' }}</div>
                    <div class="report-score-label">AI 评分</div>
                    <div class="report-stars">{{ scoreStars(s.score, 5) }}</div>
                  </div>
                  <div v-if="s.evaluation" class="report-block">
                    <div class="report-block-title">综合评估</div>
                    <div class="report-block-text">{{ s.evaluation }}</div>
                  </div>
                  <div v-if="s.weaknesses" class="report-block warn">
                    <div class="report-block-title">不足与改进</div>
                    <div class="report-block-text">{{ s.weaknesses }}</div>
                  </div>
                  <div v-if="s.suggestions" class="report-block good">
                    <div class="report-block-title">后续建议</div>
                    <div class="report-block-text">{{ s.suggestions }}</div>
                  </div>
                  <div v-if="s.submitted_result" class="report-block faint">
                    <div class="report-block-title">我提交的成果</div>
                    <div class="report-block-text">{{ s.submitted_result }}</div>
                  </div>
                </div>

                <!-- 阶段任务 -->
                <div class="stage-tasks">
                  <div class="stage-tasks-head">
                    <span>阶段任务</span>
                    <el-button size="small" text type="primary" @click.stop="openStageTaskDialog(p.id, s.id)">+ 添加任务</el-button>
                  </div>
                  <div v-if="!stageTasks(p.id, s.id).length" class="empty-tip">该阶段还没有任务，可手动添加</div>
                  <div v-for="t in stageTasks(p.id, s.id)" :key="t.id" class="task-item">
                    <div class="task-item-main">
                      <div class="task-title-row">
                        <span class="task-title" :class="{ 'task-done': t.status === 'done' }">{{ t.title }}</span>
                        <el-tag size="small" :type="statusType(t.status)" effect="light" round>{{ statusLabel(t.status) }}</el-tag>
                      </div>
                      <div v-if="t.description" class="task-desc">{{ t.description }}</div>
                    </div>
                    <div class="task-actions">
                      <el-button v-if="t.status === 'todo'" size="small" text type="primary" @click="setTaskStatus(t, 'doing')">开始</el-button>
                      <el-button v-if="t.status === 'doing'" size="small" text type="success" @click="setTaskStatus(t, 'done')">完成</el-button>
                      <el-button size="small" text type="danger" @click="handleDeleteTask(t.id)">删除</el-button>
                    </div>
                  </div>
                </div>

                <!-- 关卡操作 -->
                <div class="stage-actions-row">
                  <template v-if="s.status === 'active' || s.status === 'submitted'">
                    <el-button type="primary" round size="small" :loading="submittingStageId === s.id" @click="openSubmitDialog(s)">
                      {{ s.status === 'submitted' ? '重新提交成果' : '提交阶段成果' }}
                    </el-button>
                  </template>
                  <template v-if="s.status === 'submitted'">
                    <el-button type="success" round size="small" @click="confirmStageDone(s)">确认完成本关</el-button>
                  </template>
                  <template v-if="s.status === 'locked'">
                    <span class="stage-locked-tip">完成上一关并提交成果后可解锁</span>
                  </template>
                  <el-button size="small" text type="danger" @click="handleDeleteStage(p.id, s.id)">删除</el-button>
                </div>
              </div>
            </div>
          </div>

          <div class="free-task-head">自由任务（并行推进）</div>
          <div v-if="!generalTasks(p.id).length" class="empty-tip">暂无自由任务，可添加或在上方关卡中添加阶段任务</div>
          <div v-for="t in generalTasks(p.id)" :key="t.id" class="task-item">
            <div class="task-item-main">
              <div class="task-title-row">
                <span class="task-title" :class="{ 'task-done': t.status === 'done' }">{{ t.title }}</span>
                <el-tag size="small" :type="priorityType(t.priority)" effect="plain" round>{{ priorityLabel(t.priority) }}</el-tag>
              </div>
              <div v-if="t.description" class="task-desc">{{ t.description }}</div>
              <div class="task-meta">
                <span v-if="t.due_date" class="meta-date" :class="{ 'meta-overdue': isOverdue(t) }">
                  <el-icon :size="12"><Calendar /></el-icon> {{ t.due_date }} {{ isOverdue(t) ? '(已逾期)' : '' }}
                </span>
                <el-tag size="small" :type="statusType(t.status)" effect="light" round>{{ statusLabel(t.status) }}</el-tag>
              </div>
            </div>
            <div class="task-actions">
              <el-button v-if="t.status === 'todo'" size="small" text type="primary" @click="setTaskStatus(t, 'doing')">开始</el-button>
              <el-button v-if="t.status === 'doing'" size="small" text type="success" @click="setTaskStatus(t, 'done')">完成</el-button>
              <el-button v-if="t.status !== 'done'" size="small" text type="warning" @click="openCheckinDialog(t)" :disabled="t.checked_today">打卡</el-button>
              <el-button size="small" text type="primary" @click="openTaskDialog(p.id, t)">编辑</el-button>
              <el-button size="small" text type="danger" @click="handleDeleteTask(t.id)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 长期目标 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">长期目标</span>
        <el-button size="small" text type="primary" @click="openGoalDialog()"><el-icon style="margin-right:2px"><Plus /></el-icon>新建目标</el-button>
      </div>
      <div v-if="!goals.length" class="empty-tip">设置长期目标后，AI 会围绕目标为你推荐资源、串联计划</div>
      <div v-for="g in goals" :key="g.id" class="goal-card">
        <div class="goal-head">
          <el-tag size="small" type="primary" effect="dark" round>{{ g.goal_type }}</el-tag>
          <span class="goal-title">{{ g.title }}</span>
        </div>
        <div class="goal-meta">
          <span v-if="g.target_date" class="meta-date">目标日期: {{ g.target_date }}</span>
          <span class="meta-date">关联计划: {{ g.plan_count }} 个</span>
        </div>
        <div class="goal-progress">
          <span class="goal-progress-label">进度</span>
          <el-progress :percentage="g.progress" :stroke-width="6" :show-text="false" class="goal-progress-bar" />
          <el-button size="small" text type="primary" @click="openGoalDialog(g)">编辑</el-button>
          <el-button size="small" text type="danger" @click="handleDeleteGoal(g)">删除</el-button>
        </div>
      </div>
    </div>
    </div>

    <!-- 计划弹窗（多字段重表单：移动端=全屏子页 / 桌面端=弹窗） -->
    <ResponsivePopup v-model="planDialogVisible" :title="planForm.id ? '编辑计划' : '新建计划'" width="480px">
      <el-form :model="planForm" label-width="80px" class="plan-sheet-form">
        <el-form-item label="计划标题" required>
          <el-input v-model="planForm.title" placeholder="例如：Java 基础复习计划" maxlength="50" />
        </el-form-item>
        <el-form-item label="目标">
          <el-select v-model="planForm.goal_id" placeholder="关联长期目标（可选）" clearable style="width:100%">
            <el-option v-for="g in goals" :key="g.id" :label="`${g.goal_type} · ${g.title}`" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划目标">
          <el-input v-model="planForm.objective" type="textarea" :rows="2" placeholder="这个计划想达成什么？" />
        </el-form-item>
        <el-form-item label="当前阶段">
          <el-input v-model="planForm.stage" placeholder="例如：基础阶段 / 冲刺阶段" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始日期" required>
              <el-date-picker v-model="planForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="planForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="planDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPlan" @click="savePlan">保存</el-button>
      </template>
    </ResponsivePopup>

    <!-- 任务弹窗（小表单：移动端=底部动作面板 / 桌面端=弹窗） -->
    <ActionSheet v-model="taskDialogVisible" :title="taskForm.id ? '编辑任务' : '添加任务'" width="460px">
      <el-form :model="taskForm" label-width="80px" class="plan-sheet-form">
        <el-form-item label="任务标题" required>
          <el-input v-model="taskForm.title" placeholder="任务内容" maxlength="100" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="taskForm.description" type="textarea" :rows="2" placeholder="补充说明（可选）" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="taskForm.due_date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="不填则视为无期限" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="taskForm.priority">
            <el-radio-button value="high">高</el-radio-button>
            <el-radio-button value="medium">中</el-radio-button>
            <el-radio-button value="low">低</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingTask" @click="saveTask">保存</el-button>
      </template>
    </ActionSheet>

    <!-- 打卡弹窗（2 字段：移动端=底部动作面板） -->
    <ActionSheet v-model="checkinDialogVisible" title="任务打卡" width="400px">
      <div class="checkin-task-title">「{{ checkinTask?.title }}」</div>
      <el-form label-width="80px" class="plan-sheet-form">
        <el-form-item label="学习时长">
          <el-input-number v-model="checkinForm.minutes" :min="1" :max="600" style="width:100%" />
          <span class="checkin-unit">分钟</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="checkinForm.note" type="textarea" :rows="2" placeholder="今天学得怎么样？（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkinDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="savingCheckin" @click="saveCheckin">确认打卡</el-button>
      </template>
    </ActionSheet>

    <!-- 目标弹窗（多字段重表单：移动端=全屏子页 / 桌面端=弹窗） -->
    <ResponsivePopup v-model="goalDialogVisible" :title="goalForm.id ? '编辑目标' : '新建目标'" width="460px">
      <el-form :model="goalForm" label-width="80px" class="plan-sheet-form">
        <el-form-item label="目标类型" required>
          <el-select v-model="goalForm.goal_type" style="width:100%">
            <el-option v-for="t in goalTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标描述" required>
          <el-input v-model="goalForm.title" placeholder="例如：找到一份后端开发实习" maxlength="100" />
        </el-form-item>
        <el-form-item label="目标日期">
          <el-date-picker v-model="goalForm.target_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item v-if="goalForm.id" label="进度(%)">
          <el-slider v-model="goalForm.progress" :max="100" show-input />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="goalForm.note" type="textarea" :rows="2" placeholder="补充说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="goalDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingGoal" @click="saveGoal">保存</el-button>
      </template>
    </ResponsivePopup>

    <!-- 阶段弹窗（2 字段：移动端=底部动作面板） -->
    <ActionSheet v-model="stageDialogVisible" :title="stageForm.id ? '编辑阶段' : '添加阶段（关卡）'" width="440px">
      <el-form :model="stageForm" label-width="80px" class="plan-sheet-form">
        <el-form-item label="阶段名称" required>
          <el-input v-model="stageForm.title" placeholder="例如：基础夯实 / 进阶提升 / 冲刺实战" maxlength="100" />
        </el-form-item>
        <el-form-item label="阶段目标">
          <el-input v-model="stageForm.goal" type="textarea" :rows="2" placeholder="本关要达成什么？（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stageDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingStage" @click="saveStage">保存</el-button>
      </template>
    </ActionSheet>

    <!-- 提交成果弹窗（1 个长文本：移动端=底部动作面板） -->
    <ActionSheet v-model="submitDialogVisible" :title="'提交阶段成果：' + (submitStageObj?.title || '')" width="460px">
      <div class="submit-tip">填写本关完成情况：完成了哪些任务、产出了什么、数据与收获等。AI 将综合评估打分，指出不足并给出后续调整建议。</div>
      <el-input v-model="submitForm.result" type="textarea" :rows="5" maxlength="3000" show-word-limit placeholder="例如：完成课程1-4章学习并整理笔记，完成3个练手项目，代码已上传仓库…" />
      <template #footer>
        <el-button @click="submitDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingStageId !== null" @click="saveSubmit">提交并评估</el-button>
      </template>
    </ActionSheet>

    <!-- AI 建议弹窗（短列表：移动端=底部动作面板） -->
    <ActionSheet v-model="aiDialogVisible" title="AI 顺延 / 重排建议" width="520px">
      <div class="ai-summary">{{ aiSuggest?.summary }}</div>
      <div v-if="!aiSuggest?.items.length" class="empty-tip">暂无待处理的建议任务</div>
      <div v-for="it in aiSuggest?.items || []" :key="it.task_id" class="ai-item">
        <div class="ai-item-head">
          <span class="ai-item-title">{{ it.title }}</span>
          <el-tag size="small" :type="statusType(it.status)" effect="light" round>{{ statusLabel(it.status) }}</el-tag>
        </div>
        <div class="ai-item-suggest">{{ it.suggest }}</div>
      </div>
    </ActionSheet>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'

/** embedded：作为学业中心「学习计划」tab 的内嵌内容渲染（v4）。
    隐藏自带 SubPageHeader；.plan-page 在 embedded 下由父级样式接管（透明背景、无独立滚动）。 */
const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
import { ElMessage } from 'element-plus'
import { Plus, ArrowDown, Calendar, WarningFilled, MagicStick, Lock, Check } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { useResponsive } from '@/composables/useResponsive'
// v6.1 弹窗减负：小内容/小表单走底部动作面板，重表单走全屏子页，确认类用 actionConfirm
import ActionSheet from '@/components/common/ActionSheet.vue'
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import { usePullRefresh } from '@/composables/usePullRefresh'
import {
  getGoals, createGoal, updateGoal, deleteGoal,
  getPlans, createPlan, updatePlan, deletePlan,
  getTasks, createTask, updateTask, deleteTask,
  createCheckin, deleteCheckin, getStreak, getToday,
  getPlanReminders, getAISuggest, type GrowthGoal, type StudyPlan, type PlanTask,
  type TodayTask, type Streak, type AISuggest,
  getStages, aiGenerateStages, createStage, updateStage, deleteStage, submitStage,
  type PlanStage,
} from '@/api/plan'

// ---------- 状态 ----------
const plans = ref<StudyPlan[]>([])
const goals = ref<GrowthGoal[]>([])
const tasksByPlan = ref<Record<number, PlanTask[]>>({})
const todayTasks = ref<TodayTask[]>([])
const streak = ref<Streak>({ current: 0, longest: 0, today_checked: false, days: [] })
const reminderList = ref<string[]>([])
const expandedPlan = ref<number | null>(null)
const totalMinutes = ref(0)

const planStatus = ref('active')
const planFilters = [
  { label: '进行中', value: 'active' },
  { label: '已完成', value: 'completed' },
  { label: '已逾期', value: 'expired' },
  { label: '全部', value: 'all' },
]
const planStatusLabel = computed(() => planFilters.find(f => f.value === planStatus.value)?.label || '')

// ---------- 弹窗 ----------
const planDialogVisible = ref(false)
const savingPlan = ref(false)
const planForm = reactive<any>({ id: null, title: '', objective: '', stage: '', start_date: '', end_date: null, goal_id: null })

const taskDialogVisible = ref(false)
const savingTask = ref(false)
const taskForm = reactive<any>({ id: null, plan_id: null, stage_id: null, title: '', description: '', due_date: null, priority: 'medium' })

// 闯关任务流
const stagesByPlan = ref<Record<number, PlanStage[]>>({})
const expandedStageId = ref<number | null>(null)
const aiGenLoading = ref<number | null>(null)

const stageDialogVisible = ref(false)
const savingStage = ref(false)
const stageForm = reactive<any>({ id: null, plan_id: null, title: '', goal: '' })

const submitDialogVisible = ref(false)
const submittingStageId = ref<number | null>(null)
const submitStageObj = ref<PlanStage | null>(null)
const submitForm = reactive({ result: '' })

const checkinDialogVisible = ref(false)
const savingCheckin = ref(false)
const checkinTask = ref<PlanTask | null>(null)
const checkinForm = reactive({ minutes: 30, note: '' })

const goalDialogVisible = ref(false)
const savingGoal = ref(false)
const goalTypes = ['就业', '考研', '技能', '竞赛', '证书', '其他']
const goalForm = reactive<any>({ id: null, goal_type: '就业', title: '', target_date: null, note: '', progress: 0 })

const aiDialogVisible = ref(false)
const aiLoading = ref(false)
const aiSuggest = ref<AISuggest | null>(null)

// ---------- 数据加载 ----------
async function loadGoals() {
  goals.value = await getGoals()
}

async function loadPlans() {
  plans.value = await getPlans(planStatus.value === 'all' ? undefined : planStatus.value)
  // 默认展开第一个进行中的计划
  if (!expandedPlan.value && plans.value.length) {
    expandedPlan.value = plans.value[0].id
  }
}

async function loadTasks(planId: number) {
  tasksByPlan.value[planId] = await getTasks({ plan_id: planId })
}

async function loadStages(planId: number) {
  try {
    stagesByPlan.value[planId] = await getStages(planId)
  } catch { stagesByPlan.value[planId] = [] }
}

async function loadToday() {
  streak.value = await getStreak()
  todayTasks.value = await getToday()
  const all = await getCheckins()
  totalMinutes.value = all.reduce((s, c) => s + (Number(c.minutes) || 0), 0)
  const today = pmLocalIso()
  pmInvestedToday.value = all
    .filter(c => c.check_date === today)
    .reduce((s, c) => s + (Number(c.minutes) || 0), 0)
}

async function getCheckins() {
  const { getCheckins: api } = await import('@/api/plan')
  return api()
}

async function loadReminders() {
  try {
    const res = await getPlanReminders()
    reminderList.value = res.triggered || []
  } catch { reminderList.value = [] }
}

async function refreshAll() {
  await Promise.all([loadGoals(), loadPlans(), loadToday(), loadReminders()])
  if (expandedPlan.value) {
    await Promise.all([loadTasks(expandedPlan.value), loadStages(expandedPlan.value)])
  }
}

onMounted(refreshAll)
async function refreshToday() {
  streak.value = await getStreak()
  todayTasks.value = await getToday()
  const all = await getCheckins()
  totalMinutes.value = all.reduce((s, c) => s + (Number(c.minutes) || 0), 0)
  const today = pmLocalIso()
  pmInvestedToday.value = all
    .filter(c => c.check_date === today)
    .reduce((s, c) => s + (Number(c.minutes) || 0), 0)
}

// ---------- 计划 ----------
function toggleExpand(id: number) {
  expandedPlan.value = expandedPlan.value === id ? null : id
  if (expandedPlan.value) {
    loadTasks(expandedPlan.value)
    loadStages(expandedPlan.value)
  }
}

function openPlanDialog(p?: StudyPlan) {
  if (p) {
    Object.assign(planForm, {
      id: p.id, title: p.title, objective: p.objective || '', stage: p.stage || '',
      start_date: p.start_date, end_date: p.end_date, goal_id: p.goal_id,
    })
  } else {
    Object.assign(planForm, { id: null, title: '', objective: '', stage: '', start_date: new Date().toISOString().slice(0, 10), end_date: null, goal_id: null })
  }
  planDialogVisible.value = true
}

async function savePlan() {
  if (!planForm.title.trim()) { ElMessage.warning('请输入计划标题'); return }
  if (!planForm.start_date) { ElMessage.warning('请选择开始日期'); return }
  savingPlan.value = true
  try {
    const data = {
      title: planForm.title.trim(), objective: planForm.objective || null,
      stage: planForm.stage || null, start_date: planForm.start_date,
      end_date: planForm.end_date || null, goal_id: planForm.goal_id || null,
    }
    if (planForm.id) {
      await updatePlan(planForm.id, data)
      ElMessage.success('计划已更新')
    } else {
      const created = await createPlan(data)
      ElMessage.success('计划已创建')
      // 新建后直接按目标拆出细化关卡，避免用户只看到一条空计划
      try {
        await aiGenerateStages(created.id)
        ElMessage.success('AI 已按目标拆出闯关关卡')
      } catch {
        ElMessage.warning('关卡可稍后点「AI 拆解」生成')
      }
    }
    planDialogVisible.value = false
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingPlan.value = false }
}

async function handleDeletePlan(id: number) {
  try {
    const ok = await actionConfirm('删除计划将同时删除其下所有任务与打卡记录，确认删除？', '删除确认', { danger: true, confirmButtonText: '删除' })
    if (!ok) return
    await deletePlan(id)
    ElMessage.success('已删除')
    delete tasksByPlan.value[id]
    await loadPlans()
  } catch {}
}

function switchPlanStatus(v: string) {
  planStatus.value = v
  expandedPlan.value = null
  loadPlans()
}

// ---------- 任务 ----------
function openTaskDialog(planId: number, t?: PlanTask) {
  if (t) {
    Object.assign(taskForm, {
      id: t.id, plan_id: t.plan_id, stage_id: t.stage_id || null, title: t.title, description: t.description || '',
      due_date: t.due_date, priority: t.priority,
    })
  } else {
    Object.assign(taskForm, { id: null, plan_id: planId, stage_id: null, title: '', description: '', due_date: null, priority: 'medium' })
  }
  taskDialogVisible.value = true
}

function openStageTaskDialog(planId: number, stageId: number) {
  Object.assign(taskForm, { id: null, plan_id: planId, stage_id: stageId, title: '', description: '', due_date: null, priority: 'medium' })
  taskDialogVisible.value = true
}

async function saveTask() {
  if (!taskForm.title.trim()) { ElMessage.warning('请输入任务标题'); return }
  savingTask.value = true
  try {
    const data = {
      title: taskForm.title.trim(), description: taskForm.description || null,
      due_date: taskForm.due_date || null, priority: taskForm.priority,
      stage_id: taskForm.stage_id || null,
    }
    if (taskForm.id) await updateTask(taskForm.id, data)
    else await createTask({ ...data, plan_id: taskForm.plan_id })
    ElMessage.success(taskForm.id ? '任务已更新' : '任务已添加')
    taskDialogVisible.value = false
    await loadTasks(taskForm.plan_id)
    await loadStages(taskForm.plan_id)
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingTask.value = false }
}

async function setTaskStatus(t: PlanTask, status: string) {
  try {
    await updateTask(t.id, { status })
    ElMessage.success(statusLabel(status) + '成功')
    await loadTasks(t.plan_id)
    await loadStages(t.plan_id)
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function handleDeleteTask(id: number) {
  try {
    if (!(await actionConfirm('确认删除该任务？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
    await deleteTask(id)
    // 从当前展开计划刷新
    if (expandedPlan.value) {
      await loadTasks(expandedPlan.value)
      await loadStages(expandedPlan.value)
    }
    await loadPlans()
  } catch {}
}

// ---------- 闯关任务流 ----------
async function handleAiGenerate(planId: number, force = false) {
  if (force) {
    const ok = await actionConfirm(
      '重新拆解会用新的细化关卡替换现有全部 AI 关卡，已通关的评分会清空，历史打卡记录保留。继续？',
      '重新拆解',
      { danger: true, confirmButtonText: '重新拆解' },
    )
    if (!ok) return
  }
  aiGenLoading.value = planId
  try {
    const res = await aiGenerateStages(planId, force)
    ElMessage.success(force ? '已按目标重新拆解关卡' : 'AI 已为计划拆解出闯关关卡')
    await loadStages(planId)
    if (res.stages.length) expandedStageId.value = res.stages[0].id
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || 'AI 拆解失败')
  } finally {
    aiGenLoading.value = null
  }
}

function openStageDialog(planId: number, s?: PlanStage) {
  if (s) Object.assign(stageForm, { id: s.id, plan_id: s.plan_id, title: s.title, goal: s.goal || '' })
  else Object.assign(stageForm, { id: null, plan_id: planId, title: '', goal: '' })
  stageDialogVisible.value = true
}

async function saveStage() {
  if (!stageForm.title.trim()) { ElMessage.warning('请输入阶段名称'); return }
  savingStage.value = true
  try {
    if (stageForm.id) await updateStage(stageForm.id, { title: stageForm.title.trim(), goal: stageForm.goal || null })
    else await createStage({ plan_id: stageForm.plan_id, title: stageForm.title.trim(), goal: stageForm.goal || null })
    ElMessage.success(stageForm.id ? '阶段已更新' : '阶段已添加')
    stageDialogVisible.value = false
    await loadStages(stageForm.plan_id)
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingStage.value = false }
}

async function handleDeleteStage(planId: number, stageId: number) {
  try {
    if (!(await actionConfirm('删除该阶段将同时删除其下任务，确认删除？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
    await deleteStage(stageId)
    ElMessage.success('已删除')
    if (expandedStageId.value === stageId) expandedStageId.value = null
    await loadStages(planId)
    await loadPlans()
  } catch {}
}

function openSubmitDialog(s: PlanStage) {
  submitStageObj.value = s
  submitForm.result = s.submitted_result || ''
  submitDialogVisible.value = true
}

async function saveSubmit() {
  if (!submitStageObj.value) return
  if (!submitForm.result.trim()) { ElMessage.warning('请填写阶段成果说明'); return }
  submittingStageId.value = submitStageObj.value.id
  try {
    await submitStage(submitStageObj.value.id, { result: submitForm.result.trim() })
    ElMessage.success('成果已提交，AI 评估完成')
    submitDialogVisible.value = false
    const planId = submitStageObj.value.plan_id
    await loadStages(planId)
    expandedStageId.value = submitStageObj.value.id
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submittingStageId.value = null }
}

async function confirmStageDone(s: PlanStage) {
  try {
    await updateStage(s.id, { status: 'done' })
    ElMessage.success('恭喜通过本关！下一关已解锁')
    await loadStages(s.plan_id)
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

function toggleStageExpand(planId: number, stageId: number) {
  if (expandedStageId.value === stageId) { expandedStageId.value = null; return }
  expandedStageId.value = stageId
  if (!tasksByPlan.value[planId]) loadTasks(planId)
}

function stageTasks(planId: number, stageId: number) {
  return (tasksByPlan.value[planId] || []).filter(t => t.stage_id === stageId)
}

function generalTasks(planId: number) {
  return (tasksByPlan.value[planId] || []).filter(t => !t.stage_id)
}

function stageProgress(planId: number) {
  const list = stagesByPlan.value[planId] || []
  return { done: list.filter(s => s.status === 'done').length, total: list.length }
}

function scoreStars(score: number | null | undefined, max = 3) {
  if (score == null) return '☆'.repeat(max)
  const stars = score >= 85 ? 3 : score >= 70 ? 2 : score >= 55 ? 1 : 0
  return '★'.repeat(stars) + '☆'.repeat(max - stars)
}

function scoreColor(score: number | null | undefined) {
  if (score == null) return '#909399'
  if (score >= 85) return '#67c23a'
  if (score >= 70) return '#409eff'
  if (score >= 55) return '#e6a23c'
  return '#f56c6c'
}

const candyEmojis = ['🍬', '🍭', '🧁', '🍩', '🍬', '🍪', '🎂', '🍫']
const planGrads = [
  'linear-gradient(135deg,#4f8ef7,#36d1dc)',
  'linear-gradient(135deg,#7c6af5,#9f6bee)',
  'linear-gradient(135deg,#f76c5e,#ff9a56)',
  'linear-gradient(135deg,#2fae6e,#4fd38c)',
  'linear-gradient(135deg,#e6820a,#ffb114)',
  'linear-gradient(135deg,#2b8fd6,#5ad0f4)',
]
function planGrad(id: number) {
  return planGrads[id % planGrads.length]
}
function candyEmoji(idx: number) {
  return candyEmojis[idx % candyEmojis.length]
}
function candyPercent(planId: number) {
  const { done, total } = stageProgress(planId)
  return total ? Math.round(done * 100 / total) : 0
}
function candyStarTotal(planId: number) {
  return (stagesByPlan.value[planId] || []).reduce((s, st) => {
    if (st.score == null) return s
    return s + (st.score >= 85 ? 3 : st.score >= 70 ? 2 : st.score >= 55 ? 1 : 0)
  }, 0)
}
function candyHint(planId: number) {
  const { done, total } = stageProgress(planId)
  if (!total) return ''
  if (done === total) return '🎉 全部通关！总目标已达成，为你喝彩！'
  const cur = (stagesByPlan.value[planId] || []).find(s => s.status === 'active')
  if (cur) return `正在消除第 ${done + 1} 关「${cur.title}」，完成后提交成果领取星星 ✦`
  return `已消除 ${done}/${total} 关，继续加油！`
}

// ---------- 打卡 ----------
async function openCheckinDialog(t: PlanTask) {
  checkinTask.value = t
  checkinForm.minutes = 30
  checkinForm.note = ''
  checkinDialogVisible.value = true
}

async function saveCheckin() {
  if (!checkinTask.value) return
  savingCheckin.value = true
  try {
    await createCheckin({
      plan_id: checkinTask.value.plan_id,
      task_id: checkinTask.value.id,
      minutes: checkinForm.minutes || 30,
      note: checkinForm.note || null,
    })
    ElMessage.success('打卡成功，继续保持！')
    checkinDialogVisible.value = false
    await refreshToday()
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '打卡失败') }
  finally { savingCheckin.value = false }
}

async function handleCheckinFromToday(t: TodayTask) {
  if (!t.task_id) return
  // 勾选 = 打卡；取消勾选 = 撤销当天打卡（误点可修正）
  if (t.checked_today) {
    if (!t.checkin_id) return
    try {
      await deleteCheckin(t.checkin_id)
      ElMessage.success('已撤销打卡')
      await refreshToday()
      await loadPlans()
    } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '撤销失败') }
    return
  }
  try {
    await createCheckin({ plan_id: t.plan_id, task_id: t.task_id, minutes: 30 })
    ElMessage.success('打卡成功')
    await refreshToday()
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '打卡失败') }
}

// ---------- 目标 ----------
function openGoalDialog(g?: GrowthGoal) {
  if (g) {
    Object.assign(goalForm, { id: g.id, goal_type: g.goal_type, title: g.title, target_date: g.target_date, note: g.note || '', progress: g.progress || 0 })
  } else {
    Object.assign(goalForm, { id: null, goal_type: '就业', title: '', target_date: null, note: '', progress: 0 })
  }
  goalDialogVisible.value = true
}

async function saveGoal() {
  if (!goalForm.title.trim()) { ElMessage.warning('请输入目标描述'); return }
  savingGoal.value = true
  try {
    const data = {
      goal_type: goalForm.goal_type, title: goalForm.title.trim(),
      target_date: goalForm.target_date || null, note: goalForm.note || null,
      progress: goalForm.progress || 0,
    }
    if (goalForm.id) await updateGoal(goalForm.id, data)
    else await createGoal(data)
    ElMessage.success(goalForm.id ? '目标已更新' : '目标已创建')
    goalDialogVisible.value = false
    await loadGoals()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingGoal.value = false }
}

async function handleDeleteGoal(g: GrowthGoal) {
  try {
    if (!(await actionConfirm(`确认删除目标「${g.title}」？（关联计划将解除绑定）`, '删除确认', { danger: true, confirmButtonText: '删除' }))) return
    await deleteGoal(g.id)
    ElMessage.success('已删除')
    await loadGoals()
    await loadPlans()
  } catch {}
}

// ---------- AI 建议 ----------
async function runAISuggest(planId?: number) {
  aiLoading.value = true
  try {
    aiSuggest.value = await getAISuggest(planId)
    aiDialogVisible.value = true
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || 'AI 建议生成失败') }
  finally { aiLoading.value = false }
}

// ============================================================
// 移动端（v8 重构）：今日工作量 / 今天要做 / 闯关流
// 三个信息块 + 首次进入强制立目标（保底一个，之后可加）
// ============================================================
const { isMobile } = useResponsive()

// 下拉刷新（移动端独立路由）：复用 refreshAll 重拉目标/计划/今日任务；
// embedded（学业中心 tab）由父级滚动区统一接管，这里不重复响应手势
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value && !props.embedded })

/** 移动端当前主线：默认最新的进行中计划，可在底部切换 */
const pmSelectedPlanId = ref<number | null>(null)
const pmPlan = computed(() => {
  const picked = pmSelectedPlanId.value ? plans.value.find(p => p.id === pmSelectedPlanId.value) : null
  return picked || plans.value.find(p => p.status === 'active') || plans.value[0] || null
})
/** 全新用户（既没目标也没计划）必须先立一个保底目标；
    老数据（有计划但没目标）不拦路，只是在底部提示补一个目标 */
const pmNeedOnboarding = computed(() => !goals.value.length && !plans.value.length)
const pmStages = computed(() => (pmPlan.value ? stagesByPlan.value[pmPlan.value.id] || [] : []))
const pmCurrentStage = computed(() => pmStages.value.find(s => s.status === 'active') || null)
const pmStageDone = computed(() => pmStages.value.filter(s => s.status === 'done').length)
/** 旧版空泛拆解可以直接重拆：全部是 AI 关卡即可（重拆会保留打卡历史） */
const pmCanRebuild = computed(() => pmStages.value.length > 0
  && pmStages.value.every(s => s.ai_generated))

function pmLocalIso(d = new Date()) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const pmToday = pmLocalIso()

const pmDateText = computed(() => {
  const d = new Date()
  const w = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 · ${w}`
})
const pmGreeting = computed(() => {
  const h = new Date().getHours()
  return h < 11 ? '早上好' : h < 14 ? '中午好' : h < 18 ? '下午好' : '晚上好'
})

/** 今日任务：已完成的算「工作量」，逾期的当天要补 */
const pmTodayDone = computed(() => todayTasks.value.filter(t => t.checked_today).length)
const pmTodayTotal = computed(() => todayTasks.value.length)
const pmTodayPct = computed(() =>
  pmTodayTotal.value ? Math.round(pmTodayDone.value * 100 / pmTodayTotal.value) : 0,
)
const pmOverdue = computed(() => todayTasks.value.filter(t => pmIsLate(t)))

/** 一个任务的时长估算：按优先级给一个稳定值（库里没有预计时长字段，避免臆造精确数字） */
function pmTaskMinutes(t: TodayTask) {
  return t.priority === 'high' ? 45 : t.priority === 'low' ? 15 : 25
}
function pmIsLate(t: TodayTask) {
  return !t.checked_today && !!t.due_date && t.due_date < pmToday
}
function pmLateDays(t: TodayTask) {
  if (!t.due_date) return 0
  const diff = new Date(`${pmToday}T00:00:00`).getTime() - new Date(`${t.due_date}T00:00:00`).getTime()
  return Math.max(0, Math.round(diff / 86400000))
}
const pmTodayMinutes = computed(() => todayTasks.value.reduce((s, t) => s + pmTaskMinutes(t), 0))
/** 今日负荷：以 150 分钟为「满」的参照（约 3 小时自习），只做体感提示，不做硬性约束 */
const pmLoadPct = computed(() => Math.min(100, Math.round(pmTodayMinutes.value / 150 * 100)))
const pmLoadLabel = computed(() => {
  if (!pmTodayTotal.value) return '今天空着'
  if (pmTodayMinutes.value <= 60) return '轻松'
  if (pmTodayMinutes.value <= 150) return '适中'
  return '偏满'
})

/** 关卡的「充盈度」：任务做得越多液面越高；无任务时用关卡状态兜底 */
function pmFill(s: PlanStage) {
  if (s.status === 'done') return 93
  if (s.status === 'locked') return 0
  const base = s.done_rate || 0
  if (s.status === 'submitted') return Math.min(96, Math.max(base, 62))
  return Math.min(94, Math.max(base, 6))
}
function pmStageTaskList(s: PlanStage) {
  const pid = pmPlan.value?.id
  if (!pid) return [] as PlanTask[]
  return (tasksByPlan.value[pid] || []).filter(t => t.stage_id === s.id)
}
function pmBranchTasks() {
  const pid = pmPlan.value?.id
  if (!pid) return [] as PlanTask[]
  return (tasksByPlan.value[pid] || []).filter(t => !t.stage_id)
}

/** 每 3 关一次阶段奖励（宝箱）：前 3 关都通关才点亮 */
function pmRewardDone(idx: number) {
  return pmStages.value.slice(0, idx + 1).every(s => s.status === 'done')
}

// 首次进入：没有任何长期目标时，先立一个保底目标
const pmGoalTitle = ref('')
const pmGoalType = ref('就业')
const pmCreating = ref(false)
const pmPresets = [
  { icon: '📚', label: '考研上岸', type: '考研', title: '考研上岸：目标院校与专业' },
  { icon: '💼', label: '拿到实习 offer', type: '就业', title: '拿到一份后端实习 offer' },
  { icon: '🎓', label: '过六级', type: '证书', title: '通过英语六级' },
  { icon: '🧩', label: '技能提升', type: '技能', title: '掌握一项能写进简历的核心技能' },
]
function pmPickPreset(p: { type: string; title: string }) {
  pmGoalType.value = p.type
  pmGoalTitle.value = p.title
}
async function pmCreateGoal() {
  const title = pmGoalTitle.value.trim()
  if (!title) { ElMessage.warning('先写一句你想达成的目标'); return }
  pmCreating.value = true
  const start = new Date()
  const end = new Date(Date.now() + 90 * 86400000)
  try {
    const goal = await createGoal({
      goal_type: pmGoalType.value,
      title,
      target_date: pmLocalIso(end),
      note: null,
    })
    // 目标本身不能推进，落到一条主计划上，关卡才有地方挂
    const plan = await createPlan({
      title: title.length > 18 ? `${title.slice(0, 18)}…` : title,
      objective: title,
      stage: null,
      start_date: pmLocalIso(start),
      end_date: pmLocalIso(end),
      goal_id: goal.id,
    })
    await loadGoals()
    await loadPlans()
    expandedPlan.value = plan.id
    pmGoalTitle.value = ''
    // 让 AI 按成长档案拆关卡；失败也不挡路，用户可稍后点「AI 拆解」
    try {
      await aiGenerateStages(plan.id)
      ElMessage.success('目标已立好，AI 已拆出闯关路线')
    } catch {
      ElMessage.warning('目标已立好，闯关路线可稍后点「AI 拆解」生成')
    }
    await refreshAll()
    await loadStages(plan.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建失败，请重试')
  } finally {
    pmCreating.value = false
  }
}

// 今天要做：内联快速添加（落在当前关卡下，保证「打卡 → 充盈度」闭环）
const pmQuickOpen = ref(false)
const pmQuickTitle = ref('')
const pmQuickSaving = ref(false)
function pmOpenQuick() {
  pmQuickOpen.value = true
  pmQuickTitle.value = ''
}
async function pmAddQuick() {
  const title = pmQuickTitle.value.trim()
  if (!title) { ElMessage.warning('写一句今天要做的事'); return }
  if (!pmPlan.value) { ElMessage.warning('还没有计划，先立一个目标'); return }
  pmQuickSaving.value = true
  try {
    await createTask({
      plan_id: pmPlan.value.id,
      stage_id: pmCurrentStage.value?.id ?? null,
      title,
      due_date: pmToday,
      priority: 'medium',
    })
    ElMessage.success('已加入今天')
    pmQuickOpen.value = false
    pmQuickTitle.value = ''
    await refreshToday()
    await loadStages(pmPlan.value.id)
    await loadPlans()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  } finally {
    pmQuickSaving.value = false
  }
}

/** 支线任务默认收起，避免主线被一堆并行任务压散 */
const pmBranchOpen = ref(false)

const pmShowAll = ref(false)
const pmSwitcherOpen = ref(false)
/** 未完成的排前面：今天打开页面先看到「还剩什么」，已完成的沉底 */
const pmTasksSorted = computed(() => {
  const list = [...todayTasks.value]
  list.sort((a, b) => (a.checked_today ? 1 : 0) - (b.checked_today ? 1 : 0))
  return list
})
const pmTasksShown = computed(() =>
  pmShowAll.value ? pmTasksSorted.value : pmTasksSorted.value.slice(0, 6),
)
const pmTasksRest = computed(() => Math.max(0, pmTasksSorted.value.length - pmTasksShown.value.length))

/** 今日已投入分钟（打卡记录里 check_date = 今天） */
const pmInvestedToday = ref(0)

// ---------- 展示辅助 ----------
function progressColor(rate: number) {
  if (rate >= 100) return '#67c23a'
  if (rate >= 60) return '#409eff'
  return '#e6a23c'
}

function priorityType(p: string) {
  return { high: 'danger', medium: 'warning', low: 'info' }[p] || 'info'
}
function priorityLabel(p: string) {
  return { high: '高优先级', medium: '中优先级', low: '低优先级' }[p] || p
}
function statusType(s: string) {
  return { todo: 'info', doing: 'warning', done: 'success' }[s] || 'info'
}
function statusLabel(s: string) {
  return { todo: '待办', doing: '进行中', done: '已完成' }[s] || s
}
function isOverdue(t: PlanTask) {
  return t.status !== 'done' && !!t.due_date && t.due_date < new Date().toISOString().slice(0, 10)
}

/** 供父级（学业中心）子页下拉刷新调用：跳过 onMounted 的一次性守卫，重拉全部计划数据 */
defineExpose({ refreshAll })
</script>

<style scoped>
.plan-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 0 28px;
  background: linear-gradient(180deg, #eef4ff 0%, #f4f7fd 220px, #f7f9ff 100%);
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
  overscroll-behavior-y: contain;
}
/* embedded：作为学业中心子页 tab 内容流进父级滚动区，不再自建滚动容器与渐变底 */
.plan-page.is-embedded {
  max-width: 100%;
  height: auto;
  overflow: visible;
  background: transparent;
  padding: 0 0 8px;
}

/* 移动端：整屏覆盖子页（与资讯搜索/详情子页同一形式）——
   滑入/滑出时连顶栏与底部导航一起盖住，返回走页面顶部的 SubPageHeader。
   z-index 1500：盖过顶栏(100)/底部导航(1000)，低于 Element Plus 弹层基准(2000+)，
   页内的下拉/日期选择等弹出层不受影响。 */
@media (max-width: 767px) {
  /* 仅独立路由（非 embedded）才整屏覆盖；embedded 时它必须留在父级滚动流里，
     否则 position:fixed 会脱流并盖住学业中心固定 48px 的子页头。 */
  .plan-page:not(.is-embedded) {
    position: fixed;
    inset: 0;
    z-index: 1500;
    max-width: none;
  }
  .plan-page > .tui-appbar {
    position: sticky;
    top: 0;
    z-index: 5;
  }
}

/* ========== 顶部品牌主视觉 ========== */
.plan-hero {
  position: relative;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(140deg, #1e40af 0%, #2563eb 42%, #0ea5e9 78%, #22d3ee 100%);
  padding: 24px 20px 20px;
  border-radius: 0 0 28px 28px;
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.25);
}
.hero-glow { position: absolute; border-radius: 50%; filter: blur(2px); pointer-events: none; }
.hero-glow.g1 { width: 200px; height: 200px; background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 62%); top: -90px; right: -40px; }
.hero-glow.g2 { width: 140px; height: 140px; background: radial-gradient(circle, rgba(34,211,238,0.35), transparent 65%); bottom: -60px; left: -30px; }
.hero-glow.g3 { width: 90px; height: 90px; background: radial-gradient(circle, rgba(255,255,255,0.2), transparent 60%); bottom: 10px; right: 40px; }
.hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  position: relative;
  margin-bottom: 18px;
}
.hero-kicker {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 3px;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 8px;
}
.hero-title-row { display: flex; align-items: center; gap: 10px; }
.hero-title {
  margin: 0 0 8px;
  font-size: 21px;
  font-weight: 800;
  line-height: 1.3;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
.hero-sub { margin: 0; font-size: 12px; color: rgba(255, 255, 255, 0.85); line-height: 1.6; }
.hero-tag {
  background: rgba(255, 255, 255, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.35) !important;
  color: #fff !important;
  font-weight: 600;
}
.hero-add {
  flex-shrink: 0;
  background: #fff !important;
  color: #2563eb !important;
  font-weight: 700;
  border: none !important;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  padding: 18px 16px;
}
.hero-stats {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 16px;
  padding: 12px 8px;
  backdrop-filter: blur(6px);
}
.hero-stat { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; }
.hs-num { font-size: 22px; font-weight: 800; line-height: 1; color: #fff; text-shadow: 0 1px 4px rgba(0,0,0,0.15); }
.hs-label { font-size: 10px; color: rgba(255, 255, 255, 0.8); }
.hero-stat-sep { width: 1px; height: 30px; background: rgba(255, 255, 255, 0.22); }

/* ========== 卡片系统 ========== */
.content {
  padding: 14px 14px 0;
}
.card {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
  animation: card-in 0.45s ease both;
}
@keyframes card-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.card-head {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 14px;
}
.head-bar {
  width: 4px;
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(180deg, #2563eb, #22d3ee);
}
.head-title { font-size: 16px; font-weight: 700; color: #101828; flex: 1; letter-spacing: 0.2px; }

/* ========== 今日打卡 ========== */
.today-card { position: relative; }
.today-head { display: flex; align-items: center; justify-content: space-between; }
.today-left { display: flex; align-items: center; gap: 12px; }
.today-ring {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #ffb114, #f76c0e);
  box-shadow: 0 4px 12px rgba(247, 108, 14, 0.35);
}
.today-ring.ring-on {
  background: linear-gradient(135deg, #3fd68f, #1fb06b);
  box-shadow: 0 4px 12px rgba(31, 176, 107, 0.4);
}
.ring-empty { font-size: 20px; font-weight: 800; }
.today-title-wrap { display: flex; flex-direction: column; gap: 2px; }
.today-title { font-size: 16px; font-weight: 700; color: #101828; }
.today-hint { font-size: 11px; color: #98a2b3; }
.today-badge { margin: 0; font-weight: 600; }

.reminder-box {
  margin-top: 12px;
  background: #fffbf0;
  border: 1px solid #ffe8c2;
  border-radius: 12px;
  padding: 8px 12px;
}
.reminder-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 3px 0;
  font-size: 12px;
  color: #b88230;
  line-height: 1.5;
}
.reminder-text { flex: 1; }

/* ========== 今日任务 ========== */
.today-task {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 4px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
}
.today-task:last-child { border-bottom: none; }
.today-task-info { flex: 1; min-width: 0; }
.today-task-title { font-size: 14px; color: #101828; font-weight: 500; line-height: 1.4; }
.task-done { text-decoration: line-through; color: #98a2b3 !important; }
.today-task-meta { display: flex; align-items: center; gap: 8px; margin-top: 5px; flex-wrap: wrap; }
.meta-plan { font-size: 12px; color: #667085; display: inline-flex; align-items: center; gap: 4px; }
.meta-tag { margin: 0; }
.meta-date { font-size: 12px; color: #667085; display: inline-flex; align-items: center; gap: 4px; }
.meta-overdue { color: #f56c6c; }

/* ========== 计划列表 ========== */
.plan-filter {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.filter-tag { cursor: pointer; }

.plan-card {
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  padding: 14px;
  margin-bottom: 12px;
  background: #fff;
  box-shadow: 0 1px 6px rgba(15, 23, 42, 0.04);
  transition: border-color 0.25s, box-shadow 0.25s;
}
.plan-card.plan-expanded {
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.1);
}
.plan-card-head { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.plan-ico {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}
.plan-card-left { flex: 1; min-width: 0; }
.plan-title-line { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.plan-card-title { font-size: 14px; font-weight: 700; color: #101828; }
.goal-chip { margin: 0; font-weight: 500; }
.plan-card-meta { display: flex; align-items: center; gap: 8px; }
.expand-icon { color: #98a2b3; transition: transform 0.25s; flex-shrink: 0; }
.expand-icon.rotated { transform: rotate(180deg); }

.plan-progress { margin: 12px 0 4px; }
.plan-progress-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; }
.pp-label { font-size: 11px; color: #98a2b3; }
.pp-rate { font-size: 14px; font-weight: 800; }

.plan-card-stats {
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: #667085;
  margin-top: 6px;
  flex-wrap: wrap;
}
.stat { display: inline-flex; align-items: center; gap: 5px; }
.stat-dot { width: 7px; height: 7px; border-radius: 50%; }
.d-task { background: #2563eb; }
.d-overdue { background: #f76c5e; }
.d-checkin { background: #1fb06b; }
.stat b { color: #101828; margin-left: 1px; }
.stat-warn b { color: #f56c6c; }

.plan-detail { border-top: 1px dashed rgba(15,23,42,0.1); margin-top: 12px; padding-top: 12px; }
.plan-objective {
  font-size: 13px;
  color: #475467;
  line-height: 1.65;
  background: linear-gradient(135deg, #eef4ff, #f3fbff);
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.detail-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }

/* ========== 任务 ========== */
.task-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 10px 0; border-bottom: 1px solid rgba(15,23,42,0.05); }
.task-item:last-child { border-bottom: none; }
.task-item-main { flex: 1; min-width: 0; }
.task-title-row { display: flex; align-items: center; gap: 8px; }
.task-title { font-size: 14px; color: #101828; font-weight: 500; }
.task-desc { font-size: 12px; color: #667085; margin-top: 4px; line-height: 1.5; }
.task-meta { display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.task-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; flex-shrink: 0; }

/* ========== 长期目标 ========== */
.goal-card {
  border: 1px solid rgba(15,23,42,0.06);
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 10px;
  background: linear-gradient(135deg, #fbfcff, #f6f9ff);
}
.goal-head { display: flex; align-items: center; gap: 8px; }
.goal-title { font-size: 14px; font-weight: 600; color: #101828; }
.goal-meta { display: flex; gap: 12px; margin: 8px 0; }
.goal-progress { display: flex; align-items: center; gap: 10px; }
.goal-progress-label { font-size: 12px; color: #98a2b3; flex-shrink: 0; }
.goal-progress-bar { flex: 1; }

/* ========== 空状态 ========== */
.empty-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 26px 0 20px;
  text-align: center;
}
.empty-ico { font-size: 34px; line-height: 1; filter: saturate(0.9); }
.empty-msg { color: #98a2b3; font-size: 13px; line-height: 1.7; }

.checkin-task-title { font-size: 14px; font-weight: 600; color: #101828; margin-bottom: 12px; }
.checkin-unit { margin-left: 8px; font-size: 12px; color: #98a2b3; }
.ai-summary {
  font-size: 14px;
  color: #101828;
  line-height: 1.7;
  background: linear-gradient(135deg, #eef4ff, #f3fbff);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.ai-item { border: 1px solid rgba(15,23,42,0.06); border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; }
.ai-item-head { display: flex; align-items: center; gap: 8px; }
.ai-item-title { font-size: 14px; font-weight: 500; color: #101828; flex: 1; }
.ai-item-suggest { font-size: 13px; color: #667085; margin-top: 6px; line-height: 1.6; }

/* ========== 闯关任务流（游戏进阶模式） ========== */
.stage-section {
  border-top: 1px dashed rgba(15, 23, 42, 0.1);
  margin-top: 12px;
  padding-top: 12px;
}
.stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;
}
.stage-head-left { display: flex; align-items: center; gap: 8px; }
.stage-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
  font-weight: 700;
  color: #101828;
}
.stage-title::before {
  content: '';
  width: 4px;
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(180deg, #f76c0e, #ffb114);
}
.stage-actions { display: flex; gap: 6px; }
.stage-empty {
  text-align: center;
  color: #909399;
  font-size: 12px;
  line-height: 1.7;
  background: #f7f9fc;
  border: 1px dashed #d0d7e3;
  border-radius: 10px;
  padding: 14px 16px;
}

/* ---------- 消消乐糖果关卡网格 ---------- */
.candy-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, #fff3e0, #ffe9d6);
  border: 1px solid rgba(255, 152, 0, 0.25);
  border-radius: 14px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.candy-lv {
  display: flex;
  align-items: baseline;
  gap: 2px;
  flex-shrink: 0;
}
.candy-lv-num { font-size: 24px; font-weight: 800; color: #f76c0e; line-height: 1; }
.candy-lv-x { font-size: 13px; color: #c2855b; }
.candy-lv-label { font-size: 11px; color: #b07a52; margin-left: 4px; }
.candy-lv.is-done .candy-lv-num { color: #2fae6e; }
.candy-track {
  flex: 1;
  position: relative;
  height: 14px;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 999px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}
.candy-track-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #ffb114, #f76c0e);
  transition: width 0.6s ease;
}
.candy-track-tip {
  position: absolute;
  right: 6px; top: 50%;
  transform: translateY(-50%);
  font-size: 9px;
  font-weight: 700;
  color: #7a4b1f;
}
.candy-streak {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 999px;
  padding: 3px 9px;
}
.candy-streak-x { color: #f6b73c; font-size: 13px; }
.candy-streak-num { font-size: 13px; font-weight: 800; color: #8a5010; }

.candy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(74px, 1fr));
  gap: 10px;
}
.candy-block {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  user-select: none;
  transition: transform 0.25s, box-shadow 0.25s;
  padding: 6px;
}
.candy-block:hover { transform: translateY(-3px); }
.candy-block.is-open {
  transform: translateY(-3px) scale(1.04);
  box-shadow: 0 6px 18px rgba(64, 158, 255, 0.4);
}
/* 未解锁 */
.candy-block.cb-locked {
  background: linear-gradient(160deg, #eef0f4, #dde1e8);
  border: 2px dashed #c3c9d4;
  color: #a5adba;
}
.cb-lock { position: absolute; top: 7px; right: 9px; opacity: 0.7; }
.cb-face { font-size: 30px; font-weight: 800; color: #b7becb; }
/* 进行中 */
.candy-block.cb-active {
  background: linear-gradient(160deg, #ffb56b, #ff7a3d);
  border: 2px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 4px 14px rgba(255, 122, 61, 0.5);
  animation: candy-glow 2s ease-in-out infinite;
}
@keyframes candy-glow {
  0%, 100% { box-shadow: 0 4px 14px rgba(255, 122, 61, 0.5); }
  50% { box-shadow: 0 4px 22px rgba(255, 122, 61, 0.85); }
}
.cb-no {
  position: absolute;
  top: 6px; left: 8px;
  font-size: 11px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(0, 0, 0, 0.14);
  border-radius: 999px;
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
}
.cb-emoji { font-size: 28px; line-height: 1; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.15)); }
/* 待确认 */
.candy-block.cb-submitted {
  background: linear-gradient(160deg, #ffd87a, #ffab2e);
  border: 2px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 4px 12px rgba(255, 171, 46, 0.4);
  animation: candy-pop 0.5s ease;
}
@keyframes candy-pop {
  0% { transform: scale(0.85); }
  60% { transform: scale(1.08); }
  100% { transform: scale(1); }
}
.cb-score { font-size: 24px; font-weight: 800; color: #5b3a06; line-height: 1; }
.cb-stars { font-size: 11px; color: #fff; letter-spacing: 1px; margin-top: 3px; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
/* 已完成 */
.candy-block.cb-done {
  background: linear-gradient(160deg, #5fe0a0, #28b46c);
  border: 2px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 12px rgba(40, 180, 108, 0.45);
  animation: candy-bounce 0.6s ease;
}
@keyframes candy-bounce {
  0% { transform: scale(0.9); }
  45% { transform: scale(1.12); }
  70% { transform: scale(0.97); }
  100% { transform: scale(1); }
}
.cb-ok { color: #fff; display: flex; align-items: center; justify-content: center; }
.cb-title {
  position: absolute;
  left: 4px; right: 4px; bottom: 5px;
  text-align: center;
  font-size: 10px;
  font-weight: 700;
  color: #1a1a2e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candy-block.cb-active .cb-title,
.candy-block.cb-submitted .cb-title,
.candy-block.cb-done .cb-title { color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.3); }
.cb-dot {
  position: absolute;
  top: 7px; left: 8px;
  width: 8px; height: 8px;
  border-radius: 50%;
}
.dot-locked { background: #c3c9d4; }
.dot-active { background: #fff; box-shadow: 0 0 0 2px rgba(255,255,255,0.5); }
.dot-submitted { background: #5b3a06; }
.dot-done { background: #0e7a47; box-shadow: 0 0 6px rgba(255,255,255,0.7); }
/* 当前关「开始」气泡：仅移动端关卡路径显示 */
.cb-start { display: none; }

.candy-hint {
  margin-top: 12px;
  text-align: center;
  font-size: 12px;
  line-height: 1.5;
  color: #5b6470;
  background: #f6f7f9;
  border: 1px solid #e6e9ee;
  border-radius: 10px;
  padding: 9px 10px;
}
.candy-hint.is-done { color: #1f7a4d; background: #f3faf6; border-color: #cbe9d8; }

.stage-detail {
  background: #fafbfe;
  border: 1px solid rgba(64, 158, 255, 0.18);
  border-radius: 12px;
  padding: 12px;
  margin-top: 6px;
}
.stage-goal {
  font-size: 13px;
  color: #44546a;
  line-height: 1.6;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 10px;
}
.stage-report { margin-bottom: 10px; }
.report-score {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
  padding: 8px 0 4px;
}
.report-score-num { font-size: 40px; font-weight: 800; line-height: 1; }
.report-score-label { font-size: 12px; color: #909399; }
.report-stars { font-size: 16px; color: #ffd666; letter-spacing: 2px; }
.report-block {
  background: #fff;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  padding: 8px 12px;
  margin-bottom: 8px;
}
.report-block.warn { border-color: rgba(245, 108, 108, 0.3); background: #fff5f5; }
.report-block.good { border-color: rgba(103, 194, 58, 0.3); background: #f0f9eb; }
.report-block.faint { background: #f7f9fc; }
.report-block-title { font-size: 12px; font-weight: 600; color: #44546a; margin-bottom: 4px; }
.report-block-text { font-size: 13px; color: #333333; line-height: 1.7; white-space: pre-wrap; }

.stage-tasks-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  padding-bottom: 4px;
}
.stage-tasks .task-item { padding: 8px 0; }
.stage-actions-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.stage-locked-tip { font-size: 12px; color: #b0b6c2; }

.free-task-head {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  margin-top: 12px;
  padding-top: 10px;
  padding-bottom: 4px;
}
.submit-tip { font-size: 13px; color: #666666; line-height: 1.6; margin-bottom: 10px; }
/* ============================================================
   移动端 v6：把「闯关任务流」做成 Duolingo 式关卡路径
   ------------------------------------------------------------
   旧版是 `repeat(auto-fill, minmax(74px,1fr))` 的方块网格：一屏 4 列，
   关卡之间没有任何方位关系，读起来是「一张表格」而不是「一条路」。
   新版：单列纵向路径 + 左右交错 + 节点连线（虚线路径），
       已完成=绿✓、当前=橙脉冲、未解锁=灰锁，与 Duolingo 课程地图一致。
   仅作用于 <=767px，桌面端仍用上面的糖果网格。
   ============================================================ */
@media (max-width: 767px) {
  /* ── 区块重排：进入计划页先看到「关卡地图」，打卡/今日任务退到其后 ── */
  .content { display: flex; flex-direction: column; }
  .content > * { order: 5; }
  .content > .card:nth-child(3) { order: 1; }   /* 我的计划（含关卡路径） */
  .content > .card:nth-child(1) { order: 2; }   /* 今日打卡 */
  .content > .card:nth-child(2) { order: 3; }   /* 今日任务 */

  /* ── 路径容器 ── */
  .candy-grid {
    display: flex; flex-direction: column; align-items: center;
    gap: 0; padding: 12px 0 4px;
  }

  /* ── 节点：圆形，内部只有「图标 + 关卡名」两行 ── */
  .candy-block {
    width: 78px; height: 78px; aspect-ratio: auto; flex: none;
    border-radius: 50%; padding: 9px 7px 7px;
    margin-bottom: 38px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 1px;
  }
  .candy-block:last-child { margin-bottom: 6px; }

  /* 左右交错：奇数右偏、偶数左偏，形成 S 形前进感 */
  .candy-block:nth-child(odd) { transform: translateX(26px); }
  .candy-block:nth-child(even) { transform: translateX(-26px); }
  .candy-block:hover { transform: none; }
  .candy-block.is-open { transform: none; box-shadow: 0 6px 18px rgba(255, 122, 61, .38); }
  .candy-block:nth-child(odd).is-open { transform: translateX(26px) scale(1.04); }
  .candy-block:nth-child(even).is-open { transform: translateX(-26px) scale(1.04); }

  /* ── 节点连线：从底端斜向下一关，虚线更像「路」 ── */
  .candy-block::after {
    content: ''; position: absolute; left: 50%; top: 100%;
    width: 3px; height: 66px; border-radius: 2px;
    background: #e2e7ed;
    transform-origin: top center; z-index: 0;
  }
  /* 奇数在右、下一关在左 → 线向左下（负角）；偶数反之 */
  /* 注意方向：rotate(θ) 作用于竖直向下的伪元素时，正角向左、负角向右 */
  .candy-block:nth-child(odd)::after { transform: rotate(52deg); }
  .candy-block:nth-child(even)::after { transform: rotate(-52deg); }
  .candy-block:last-child::after { display: none; }
  /* 已通关的节点下方的路也标成绿色，视觉上「走过这段路」 */
  .candy-block.cb-done::after { background: #a9dfc3; }

  /* ── 节点内部元素缩放 ── */
  .cb-emoji { font-size: 23px; }
  .cb-face { font-size: 24px; }
  .cb-ok :deep(svg), .cb-ok .el-icon { width: 22px; height: 22px; }
  .cb-score { font-size: 19px; }
  .cb-stars { font-size: 9px; letter-spacing: .5px; margin-top: 1px; }
  .cb-no {
    top: 2px; left: 4px; width: 16px; height: 16px;
    font-size: 10px;
  }
  .cb-lock { top: 5px; right: 6px; }
  .cb-lock :deep(svg), .cb-lock .el-icon { width: 13px; height: 13px; }

  /* 关卡名放进圆里：两行省略，不再压在方块底部 */
  .cb-title {
    position: static; left: auto; right: auto; bottom: auto;
    width: 100%; margin-top: 1px;
    font-size: 9.5px; line-height: 1.15; font-weight: 700;
    white-space: normal; text-align: center;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; word-break: break-all;
  }
  .candy-block.cb-locked .cb-title { color: #8f97a3; }

  /* ── 顶部进度条：压扁一点，让路径成为首屏主角 ── */
  .candy-topbar { padding: 9px 11px; margin-bottom: 10px; border-radius: 12px; }
  .candy-lv-num { font-size: 21px; }
  .candy-hint { font-size: 11.5px; margin-top: 10px; }

  /* ── 计划卡内部：四个操作按钮在窄屏上换行排列，不再挤成一行 ── */
  .detail-actions { display: flex; flex-wrap: wrap; gap: 6px; }
  .detail-actions .el-button { margin-left: 0 !important; }

  /* ── v7：路径节奏收紧 + 当前关「开始」气泡 ──
     上一版节点 78px、间距 38px，6 关要滚两屏且顶部节点被卡片圆角切掉一角。
     现在：节点 82px（更好点）、间距 30px、连线 58px，路径整体矮了约 1/4，
     容器顶部留 26px 给气泡；当前关上方挂一枚白色气泡（Duolingo 的 START）。 */
  .stage-section { border-top: 0 !important; margin-top: 8px !important; padding-top: 2px !important; }
  .stage-head { margin-bottom: 8px !important; }
  .candy-grid { padding: 26px 6px 4px !important; overflow: visible !important; background: #f7fbf9; border-radius: 16px; }
  .candy-block { width: 82px !important; height: 82px !important; margin-bottom: 30px !important; }
  .candy-block:nth-child(odd) { transform: translateX(30px) !important; }
  .candy-block:nth-child(even) { transform: translateX(-30px) !important; }
  .candy-block:nth-child(odd).is-open { transform: translateX(30px) scale(1.04) !important; }
  .candy-block:nth-child(even).is-open { transform: translateX(-30px) scale(1.04) !important; }
  .candy-block::after { height: 58px !important; }
  /* 当前关的「开始」气泡：挂在节点**侧面**（奇数关挂左、偶数关挂右），
     不占用上下间距——节点间距只有 30px，气泡放上方会顶到上一关。 */
  .candy-block .cb-start {
    display: flex; align-items: center; justify-content: center;
    position: absolute; top: 50%;
    transform: translateY(-50%);
    padding: 0 9px; height: 20px;
    background: #fff; color: #ef6c1f;
    border: 2px solid #ffd8bf; border-radius: 999px;
    font-size: 10px; font-weight: 800; letter-spacing: 1.2px;
    white-space: nowrap; line-height: 1;
    box-shadow: 0 4px 10px rgba(247, 108, 14, .16);
  }
  .candy-block .cb-start::after { content: none; }
  .candy-block:nth-child(odd) .cb-start { right: calc(100% + 8px); left: auto; }
  .candy-block:nth-child(even) .cb-start { left: calc(100% + 8px); right: auto; }
}

/* ============================================================
   移动端 v8：今日工作量 / 今天要做 / 闯关流
   节点只在 isMobile 时渲染（v-if），样式无需再做媒体查询
   立体关卡：白方块 + 底部厚度阴影（Duolingo 按钮式 3D），
             内部液面高度 = 该关任务完成率，做完一个任务就涨一点
   ============================================================ */
.pm {
  --pm-green: #1f7a4d;
  --pm-ink: #141a17;
  --pm-ink2: #5c6a62;
  --pm-ink3: #98a29c;
  --pm-line: #e7eeea;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 2px 0 20px;
}

/* ── ① 今日 hero ── */
.pm-hero {
  padding: 15px 15px 13px;
  border-radius: 18px;
  border: 1px solid var(--pm-line);
  background:
    radial-gradient(130% 100% at 100% 0%, #eef8f1 0%, rgba(255, 255, 255, 0) 62%),
    #fff;
  box-shadow: 0 1px 2px rgba(18, 74, 52, .04);
}
.pm-hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.pm-date { margin: 0; font-size: 11.5px; color: var(--pm-ink3); letter-spacing: .2px; }
.pm-hi { margin: 3px 0 0; font-size: 20px; line-height: 1.2; font-weight: 700; color: var(--pm-ink); letter-spacing: -.4px; }
.pm-streak {
  display: inline-flex; align-items: baseline; gap: 3px;
  padding: 4px 9px 4px 8px; border-radius: 999px;
  background: #fff5ec; border: 1px solid #ffe2c9; color: #c2600a;
  font-size: 10.5px; white-space: nowrap;
}
.pm-streak b { font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums; }
.pm-streak-ico { font-size: 12px; }
.pm-streak.zero { background: #f5f7f6; border-color: #e7eeea; color: var(--pm-ink3); }

.pm-hero-main { display: flex; align-items: center; gap: 15px; margin-top: 13px; }
.pm-dial { position: relative; width: 84px; height: 84px; flex: none; }
.pm-dial-svg { width: 84px; height: 84px; transform: rotate(-90deg); }
.pm-dial-bg { fill: none; stroke: #eef3f0; stroke-width: 8; }
.pm-dial-fg {
  fill: none; stroke: #4fae35; stroke-width: 8; stroke-linecap: round;
  transition: stroke-dasharray .7s cubic-bezier(.4, 0, .2, 1);
}
.pm-dial-txt { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; }
.pm-dial-txt b { font-size: 19px; font-weight: 700; color: var(--pm-ink); font-variant-numeric: tabular-nums; line-height: 1; }
.pm-dial-txt b i { font-style: normal; font-size: 11.5px; font-weight: 500; color: var(--pm-ink3); }
.pm-dial-txt span { font-size: 9.5px; color: var(--pm-ink3); }

.pm-hero-side { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.pm-kv { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.pm-kv > span { font-size: 11px; color: var(--pm-ink3); white-space: nowrap; }
.pm-kv b { font-size: 14px; font-weight: 700; color: var(--pm-ink); font-variant-numeric: tabular-nums; }
.pm-kv b i { font-style: normal; font-size: 9.5px; font-weight: 500; color: var(--pm-ink3); margin-left: 2px; }

.pm-load { margin-top: 13px; padding-top: 11px; border-top: 1px dashed #e9efeb; }
.pm-load-line { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; font-size: 10.5px; color: var(--pm-ink3); }
.pm-load-t { color: var(--pm-ink2); font-weight: 600; }
.pm-load-bar { margin-top: 7px; height: 6px; border-radius: 3px; background: #eef3f0; overflow: hidden; }
.pm-load-bar i { display: block; height: 100%; border-radius: 3px; background: linear-gradient(90deg, #9ae066, #43a300); transition: width .5s ease; }

/* ── 通用卡片 / 区块头 ── */
.pm-card {
  padding: 14px 14px 12px;
  border-radius: 16px;
  border: 1px solid var(--pm-line);
  background: #fff;
  box-shadow: 0 1px 2px rgba(18, 74, 52, .04);
}
.pm-sec-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 9px; }
.pm-sec-h { margin: 0; font-size: 15px; font-weight: 700; color: var(--pm-ink); letter-spacing: -.2px; }
.pm-sec-act { flex: none; height: 28px; padding: 0 10px; border: 0; border-radius: 8px; background: #f1f7f3; color: var(--pm-green); font-size: 11.5px; font-weight: 600; }

/* ── ② 今天要做 ── */
.pm-overdue {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px; margin-bottom: 6px; border-radius: 9px;
  background: #fdf6ec; color: #a45c09; font-size: 11.5px; line-height: 1.35;
}
.pm-tasks { list-style: none; margin: 0; padding: 0; }
.pm-task { display: flex; align-items: flex-start; gap: 11px; padding: 9px 0; border-bottom: 1px solid #f1f5f2; }
.pm-task:last-child { border-bottom: 0; padding-bottom: 2px; }
.pm-check {
  flex: none; width: 22px; height: 22px; margin-top: 1px; padding: 0;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid #cfd9d3; border-radius: 50%; background: #fff;
  transition: background .18s, border-color .18s, transform .18s;
}
.pm-check:active { transform: scale(.9); }
.pm-check svg { width: 12px; height: 12px; fill: none; stroke: #fff; stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round; }
.pm-task.done .pm-check { background: #43a300; border-color: #43a300; }
.pm-task-body { flex: 1; min-width: 0; }
.pm-task-t { margin: 0; font-size: 13.5px; line-height: 1.35; font-weight: 500; color: var(--pm-ink); word-break: break-word; }
.pm-task.done .pm-task-t { color: #a4ada8; text-decoration: line-through; text-decoration-color: #d6ded9; }
.pm-task-m { margin: 3px 0 0; display: flex; flex-wrap: wrap; align-items: center; gap: 4px; font-size: 10.5px; color: var(--pm-ink3); }
.pm-task-plan { max-width: 132px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pm-sep { color: #ccd6d0; }
.pm-task-late { font-style: normal; font-weight: 600; color: #c2600a; }
.pm-empty { margin: 6px 0 2px; font-size: 12px; color: var(--pm-ink3); }

.pm-more {
  display: block; width: 100%; margin-top: 8px; padding: 7px 0;
  border: 0; border-radius: 9px; background: #f6f9f7;
  color: var(--pm-ink3); font-size: 11px;
}

.pm-quick { display: flex; gap: 6px; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #eaf0ec; }
.pm-quick input {
  flex: 1; min-width: 0; height: 34px; padding: 0 11px;
  border: 1px solid #e2eae5; border-radius: 9px; background: #fafcfb;
  font-size: 12.5px; color: var(--pm-ink);
}
.pm-quick input:focus { outline: none; border-color: #9ed7b6; background: #fff; }
.pm-quick-save { flex: none; height: 34px; padding: 0 13px; border: 0; border-radius: 9px; background: var(--pm-green); color: #fff; font-size: 12px; font-weight: 600; }
.pm-quick-save:disabled { opacity: .6; }
.pm-quick-cancel { flex: none; height: 34px; padding: 0 8px; border: 0; background: transparent; color: var(--pm-ink3); font-size: 12px; }

/* ── ③ 闯关流 ── */
.pm-quest-plan { margin: -3px 0 10px; font-size: 11px; color: var(--pm-ink3); line-height: 1.4; }
.pm-quest-tools { flex: none; display: flex; align-items: center; gap: 6px; }
.pm-quest-rebuild {
  height: 24px; padding: 0 9px; border: 1px solid #dde3e8; border-radius: 7px;
  background: #fff; color: #5b6470; font-family: inherit; font-size: 10.5px; font-weight: 500;
}
.pm-quest-rebuild:disabled { opacity: .55; }
.pm-quest-count { flex: none; padding: 4px 9px; border-radius: 999px; background: #eef7f1; color: var(--pm-green); font-size: 10.5px; font-weight: 600; font-variant-numeric: tabular-nums; }

.pm-track { display: flex; flex-direction: column; padding: 2px 0 0; }
.pm-step { position: relative; display: flex; gap: 12px; padding: 8px 0; }
.pm-step-rail { position: relative; width: 64px; flex: none; display: flex; justify-content: center; }
/* 主任务线：贯穿整个 step 再被节点盖住 —— 用节点自身高度算线会算空（rail 高度=节点高） */
.pm-step.has-line::before {
  content: ''; position: absolute; left: 31px; top: 0; bottom: -8px; width: 3px;
  background: repeating-linear-gradient(180deg, #cfe0d7 0 6px, transparent 6px 12px);
  border-radius: 2px; z-index: 0;
}
.pm-step:first-child::before { top: 50%; }
.pm-step-rail, .pm-step-body { position: relative; z-index: 1; }

/* 立体方块：底部实心厚度 + 内部液面 */
.pm-node {
  position: relative; width: 52px; height: 52px; padding: 0;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid #e0eae4; border-radius: 14px; background: #fff;
  box-shadow: 0 5px 0 #e3ece7, 0 8px 14px rgba(18, 74, 52, .07);
  overflow: hidden;
  transition: transform .16s ease, box-shadow .16s ease, width .16s ease, height .16s ease;
}
/* 玻璃罐高光：顶面一条亮边 + 内壁暗角，削弱「App 图标」的观感 */
.pm-node::after {
  content: ''; position: absolute; inset: 0; z-index: 3; border-radius: inherit; pointer-events: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .95), inset 0 -4px 8px rgba(18, 74, 52, .07);
}
.pm-node:active { transform: translateY(3px); box-shadow: 0 2px 0 #e3ece7, 0 4px 8px rgba(18, 74, 52, .09); }
.pm-node.is-active {
  width: 62px; height: 62px; border-radius: 16px; border-color: #9bd6b5;
  box-shadow: 0 6px 0 #bfe3ce, 0 12px 18px rgba(31, 122, 77, .16);
  animation: pm-node-breathe 2.6s ease-in-out infinite;
}
@keyframes pm-node-breathe {
  0%, 100% { box-shadow: 0 6px 0 #bfe3ce, 0 12px 18px rgba(31, 122, 77, .16), 0 0 0 0 rgba(88, 204, 2, .18); }
  50% { box-shadow: 0 6px 0 #bfe3ce, 0 12px 18px rgba(31, 122, 77, .16), 0 0 0 7px rgba(88, 204, 2, 0); }
}
@media (prefers-reduced-motion: reduce) { .pm-node.is-active { animation: none; } }
.pm-node-fill {
  position: absolute; left: 4px; right: 4px; bottom: 4px;
  height: var(--fill, 0%);
  max-height: calc(100% - 8px);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(133, 226, 71, .9) 0%, rgba(67, 163, 0, .96) 100%);
  transition: height .8s cubic-bezier(.34, 1.1, .5, 1);
}
/* 液面顶端的波光：一条亮弧 + 下方淡淡的反光 */
.pm-node-fill::before {
  content: ''; position: absolute; left: -24%; right: -24%; top: -5px; height: 11px;
  border-radius: 50%;
  background: radial-gradient(ellipse at 50% 100%, rgba(255, 255, 255, .78) 0%, rgba(255, 255, 255, 0) 72%);
}
.pm-node-face {
  position: relative; z-index: 2;
  display: flex; align-items: center; justify-content: center;
  color: #2b7a4c; font-size: 19px; font-weight: 800; font-variant-numeric: tabular-nums;
  text-shadow: 0 1px 0 #fff, 0 0 7px rgba(255, 255, 255, .95);
}
.pm-node.is-done { background: #f3fcec; border-color: #cbe8bd; box-shadow: 0 5px 0 #d8eecb, 0 8px 14px rgba(67, 163, 0, .12); }
.pm-node.is-done .pm-node-fill { background: linear-gradient(180deg, rgba(127, 217, 68, .92) 0%, rgba(67, 163, 0, .96) 100%); }
.pm-node.is-done .pm-node-face { color: #fff; text-shadow: 0 1px 3px rgba(31, 90, 0, .4); font-size: 19px; }
.pm-node.is-locked { width: 46px; height: 46px; background: #f8faf9; border: 1.5px dashed #c7d6ce; box-shadow: none; }
.pm-node.is-done { width: 48px; height: 48px; }
.pm-node.is-locked .pm-node-face { color: #b9c4be; text-shadow: none; }
.pm-node.is-submitted .pm-node-face { color: #b26a06; }

.pm-step-body { flex: 1; min-width: 0; padding-top: 4px; }
.pm-step-top { display: flex; align-items: baseline; gap: 8px; }
.pm-step-t { margin: 0; flex: 1; min-width: 0; font-size: 13px; font-weight: 600; color: var(--pm-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pm-step-v { flex: none; font-size: 10.5px; font-weight: 600; color: var(--pm-ink3); font-variant-numeric: tabular-nums; }
.pm-step-v.is-done { color: #2f9e44; }
.pm-step-v.is-active { color: #c2600a; }
.pm-step-m { margin: 4px 0 0; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; font-size: 10.5px; color: var(--pm-ink3); }
.pm-step-go { color: var(--pm-green); font-weight: 600; }

/* 阶段奖励 */
.pm-reward {
  display: flex; align-items: center; gap: 7px;
  margin: 1px 0 1px 76px; padding: 7px 10px;
  border: 1px dashed #e2e9e5; border-radius: 10px;
  background: #f8faf9; color: #9aa39d; font-size: 10.5px;
}
.pm-reward.on { border-color: #ffe0ae; background: #fffaf0; color: #a4640b; font-weight: 600; }
.pm-reward-ico { font-size: 13px; }

/* 分支（关卡内任务） */
.pm-branch { margin-top: 9px; padding: 9px 10px; border-radius: 11px; border: 1px solid #edf3ef; background: #f8faf9; }
.pm-branch-goal { margin: 0 0 8px; font-size: 11px; line-height: 16px; color: #6b7771; }
.pm-branch-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }
.pm-branch-standalone { margin-top: 10px; padding: 9px 10px; border-radius: 11px; border: 1px solid #edf3ef; background: #f8faf9; }
.pm-branch-item { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; line-height: 1.35; color: #3a453f; }
.pm-branch-t { flex: 1; min-width: 0; }
.pm-branch-item.done .pm-branch-t { color: #a4ada8; text-decoration: line-through; }
.pm-branch-check {
  flex: none; width: 18px; height: 18px; margin-top: 1px; padding: 0;
  display: flex; align-items: center; justify-content: center;
  border: 1.5px solid #cfd9d3; border-radius: 6px; background: #fff; color: #fff;
}
.pm-branch-item.done .pm-branch-check { background: #43a300; border-color: #43a300; }
.pm-branch-empty { margin: 0; font-size: 11px; color: #9aa39d; }
.pm-branch-acts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.pm-branch-acts button {
  height: 28px; padding: 0 11px; border: 1px solid #e2eae5; border-radius: 8px;
  background: #fff; color: #5c6a62; font-size: 11.5px;
}
.pm-branch-acts button.primary { border-color: var(--pm-green); background: var(--pm-green); color: #fff; font-weight: 600; }

.pm-quest-foot { display: flex; gap: 8px; margin-top: 12px; padding-top: 11px; border-top: 1px dashed #eaf0ec; }
.pm-quest-foot button { flex: 1; height: 32px; border: 1px solid #e2eae5; border-radius: 9px; background: #fbfcfb; color: #5c6a62; font-size: 11.5px; font-weight: 500; }

.pm-quest-empty { padding: 12px 6px 4px; text-align: center; }
.pm-quest-empty p { margin: 0 0 12px; font-size: 12px; line-height: 18px; color: #8d9791; }
.pm-quest-ai {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 16px; border: 0; border-radius: 10px;
  background: var(--pm-green); color: #fff; font-size: 12.5px; font-weight: 600;
}
.pm-quest-ai:disabled { opacity: .6; }

/* ── 目标行 ── */
.pm-goal { display: flex; align-items: stretch; gap: 8px; }
.pm-goal-main {
  flex: 1; min-width: 0; display: flex; align-items: center; gap: 9px;
  padding: 9px 11px; border: 1px solid var(--pm-line); border-radius: 12px;
  background: #fff; text-align: left;
}
.pm-goal-ico { font-size: 15px; }
.pm-goal-txt { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.pm-goal-txt b { font-size: 12.5px; font-weight: 600; color: var(--pm-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pm-goal-txt em { font-style: normal; font-size: 10px; color: var(--pm-ink3); }
.pm-goal-main.is-empty { border-style: dashed; border-color: #d9e4de; background: #fbfdfc; }
.pm-goal-add { flex: none; padding: 0 12px; border: 1px dashed #d9e4de; border-radius: 12px; background: #fff; color: var(--pm-green); font-size: 11.5px; font-weight: 600; }

/* 主线切换浮层 */
.pm-sheet-mask {
  position: fixed; inset: 0; z-index: 2600;
  display: flex; align-items: flex-end;
  background: rgba(20, 26, 23, .38);
  backdrop-filter: blur(2px);
}
.pm-sheet {
  width: 100%; padding: 8px 16px calc(16px + env(safe-area-inset-bottom));
  background: #fff; border-radius: 18px 18px 0 0;
  box-shadow: 0 -8px 24px rgba(18, 74, 52, .12);
}
.pm-sheet-bar { width: 38px; height: 4px; margin: 2px auto 12px; border-radius: 2px; background: #e3eae6; }
.pm-sheet-h { margin: 0 0 10px; font-size: 14px; font-weight: 700; color: var(--pm-ink); }
.pm-sheet-list { list-style: none; margin: 0 0 12px; padding: 0; display: flex; flex-direction: column; gap: 8px; max-height: 52vh; overflow-y: auto; }
.pm-sheet-item {
  position: relative;
  width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 3px;
  padding: 11px 12px; border: 1px solid var(--pm-line); border-radius: 12px; background: #fff; text-align: left;
}
.pm-sheet-item.on { border-color: #7ec99b; background: #f4fbf6; }
.pm-sheet-name { font-size: 13px; font-weight: 600; color: var(--pm-ink); }
.pm-sheet-meta { font-size: 10.5px; color: var(--pm-ink3); }
.pm-sheet-cur { position: absolute; top: 11px; right: 12px; font-size: 10px; font-weight: 600; color: #2f9e44; }
.pm-sheet-close {
  width: 100%; height: 42px; border: 0; border-radius: 12px;
  background: #f4f6f5; color: #5c6a62; font-size: 13px; font-weight: 600;
}

/* ── 首次进入：立目标 ── */
.pm-gate { padding: 16px 3px 6px; }
.pm-gate-ico { display: block; font-size: 26px; line-height: 1; }
.pm-gate-h { margin: 11px 0 0; font-size: 22px; font-weight: 700; color: var(--pm-ink); letter-spacing: -.4px; }
.pm-gate-p { margin: 9px 0 16px; font-size: 12.5px; line-height: 1.65; color: #6b7771; }
.pm-preset-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.pm-preset {
  display: flex; flex-direction: column; align-items: flex-start; gap: 6px;
  padding: 12px; border: 1px solid #e6ede9; border-radius: 13px; background: #fff;
  text-align: left; transition: border-color .18s, background .18s, box-shadow .18s;
}
.pm-preset.on { border-color: #7ec99b; background: #f2fbf5; box-shadow: 0 0 0 2px rgba(88, 204, 2, .12); }
.pm-preset-ico { font-size: 18px; line-height: 1; }
.pm-preset-t { font-size: 12px; font-weight: 600; color: #2b342f; }
.pm-gate-field { display: block; margin-top: 12px; }
.pm-gate-field input {
  width: 100%; height: 44px; padding: 0 13px;
  border: 1px solid #e2eae5; border-radius: 12px; background: #fafcfb;
  font-size: 13px; color: var(--pm-ink);
}
.pm-gate-field input:focus { outline: none; border-color: #8ed0ac; background: #fff; }
.pm-gate-cta {
  width: 100%; height: 46px; margin-top: 10px;
  border: 0; border-radius: 13px; background: var(--pm-green); color: #fff;
  font-size: 14px; font-weight: 600;
}
.pm-gate-cta:disabled { opacity: .62; }
.pm-gate-tip { margin: 10px 0 0; text-align: center; font-size: 10.5px; color: #a4ada8; }

</style>