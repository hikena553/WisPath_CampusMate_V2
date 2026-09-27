<template>
  <div class="plan-page">
    <!-- 顶部品牌主视觉 -->
    <div class="plan-hero">
      <div class="hero-glow g1"></div>
      <div class="hero-glow g2"></div>
      <div class="hero-glow g3"></div>
      <div class="hero-top">
        <div class="hero-heading">
          <div class="hero-title-row">
            <span class="hero-kicker">MY PLAN · 学习计划</span>
            <el-tag class="hero-tag" effect="dark" round>驾驶舱</el-tag>
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

    <div class="content">
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

    <!-- 计划弹窗 -->
    <el-dialog v-model="planDialogVisible" :title="planForm.id ? '编辑计划' : '新建计划'" width="480px" :close-on-click-modal="false">
      <el-form :model="planForm" label-width="80px">
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
    </el-dialog>

    <!-- 任务弹窗 -->
    <el-dialog v-model="taskDialogVisible" :title="taskForm.id ? '编辑任务' : '添加任务'" width="460px" :close-on-click-modal="false">
      <el-form :model="taskForm" label-width="80px">
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
    </el-dialog>

    <!-- 打卡弹窗 -->
    <el-dialog v-model="checkinDialogVisible" title="任务打卡" width="400px" :close-on-click-modal="false">
      <div class="checkin-task-title">「{{ checkinTask?.title }}」</div>
      <el-form label-width="80px">
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
    </el-dialog>

    <!-- 目标弹窗 -->
    <el-dialog v-model="goalDialogVisible" :title="goalForm.id ? '编辑目标' : '新建目标'" width="460px" :close-on-click-modal="false">
      <el-form :model="goalForm" label-width="80px">
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
    </el-dialog>

    <!-- 阶段弹窗 -->
    <el-dialog v-model="stageDialogVisible" :title="stageForm.id ? '编辑阶段' : '添加阶段（关卡）'" width="440px" :close-on-click-modal="false">
      <el-form :model="stageForm" label-width="80px">
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
    </el-dialog>

    <!-- 提交成果弹窗 -->
    <el-dialog v-model="submitDialogVisible" :title="'提交阶段成果：' + (submitStageObj?.title || '')" width="460px" :close-on-click-modal="false">
      <div class="submit-tip">填写本关完成情况：完成了哪些任务、产出了什么、数据与收获等。AI 将综合评估打分，指出不足并给出后续调整建议。</div>
      <el-input v-model="submitForm.result" type="textarea" :rows="5" maxlength="3000" show-word-limit placeholder="例如：完成课程1-4章学习并整理笔记，完成3个练手项目，代码已上传仓库…" />
      <template #footer>
        <el-button @click="submitDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingStageId !== null" @click="saveSubmit">提交并评估</el-button>
      </template>
    </el-dialog>

    <!-- AI 建议弹窗 -->
    <el-dialog v-model="aiDialogVisible" title="AI 顺延 / 重排建议" width="520px">
      <div class="ai-summary">{{ aiSuggest?.summary }}</div>
      <div v-if="!aiSuggest?.items.length" class="empty-tip">暂无待处理的建议任务</div>
      <div v-for="it in aiSuggest?.items || []" :key="it.task_id" class="ai-item">
        <div class="ai-item-head">
          <span class="ai-item-title">{{ it.title }}</span>
          <el-tag size="small" :type="statusType(it.status)" effect="light" round>{{ statusLabel(it.status) }}</el-tag>
        </div>
        <div class="ai-item-suggest">{{ it.suggest }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Calendar, WarningFilled, MagicStick, Lock, Check } from '@element-plus/icons-vue'
import {
  getGoals, createGoal, updateGoal, deleteGoal,
  getPlans, createPlan, updatePlan, deletePlan,
  getTasks, createTask, updateTask, deleteTask,
  createCheckin, getStreak, getToday,
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
const checkinLoaded = ref(false)
async function refreshToday() {
  streak.value = await getStreak()
  todayTasks.value = await getToday()
  if (!checkinLoaded.value) {
    checkinLoaded.value = true
  }
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
    if (planForm.id) await updatePlan(planForm.id, data)
    else await createPlan(data)
    ElMessage.success(planForm.id ? '计划已更新' : '计划已创建')
    planDialogVisible.value = false
    await loadPlans()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { savingPlan.value = false }
}

async function handleDeletePlan(id: number) {
  try {
    await ElMessageBox.confirm('删除计划将同时删除其下所有任务与打卡记录，确认删除？', '删除确认', { type: 'warning' })
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
    await ElMessageBox.confirm('确认删除该任务？', '删除确认', { type: 'warning' })
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
async function handleAiGenerate(planId: number) {
  aiGenLoading.value = planId
  try {
    const res = await aiGenerateStages(planId)
    ElMessage.success('AI 已为计划拆解出闯关关卡')
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
    await ElMessageBox.confirm('删除该阶段将同时删除其下任务，确认删除？', '删除确认', { type: 'warning' })
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
  if (t.checked_today) return
  if (!t.task_id) return
  try {
    await createCheckin({ plan_id: t.plan_id, task_id: t.task_id, minutes: 30 })
    ElMessage.success('打卡成功')
    await refreshToday()
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
    await ElMessageBox.confirm(`确认删除目标「${g.title}」？（关联计划将解除绑定）`, '删除确认', { type: 'warning' })
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

.candy-hint {
  margin-top: 10px;
  text-align: center;
  font-size: 12px;
  color: #b07a52;
  background: #fff8ef;
  border: 1px dashed #f3c98b;
  border-radius: 10px;
  padding: 8px;
}
.candy-hint.is-done { color: #2fae6e; background: #effaf3; border-color: #a8e6c3; }

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
</style>