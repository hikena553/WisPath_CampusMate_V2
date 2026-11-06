<template>
  <div
    class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="审批管理" fallback="/teacher" />
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <div class="tui-content">
      <!-- 桌面端只保留一行页面标题与待办规模，不再堆叠概览宫格、流程条与规则说明 -->
      <div v-if="!isMobile" class="apm-head">
        <div class="apm-head-main">
          <h2>审批管理</h2>
          <p>请假 {{ pendingLeaves.length }} · 办事 {{ pendingTickets.length }} · 材料 {{ pendingMaterials.length }}
          <template v-if="pendingScheduleChanges.length"> · 调课 {{ pendingScheduleChanges.length }}</template></p>
        </div>
        <span class="apm-head-total"><b>{{ totalPending }}</b> 条待处理</span>
      </div>

      <TuiSegmented
        v-model="activeTab"
        class="tui-seg-wrap ap-status-tabs"
        :options="tabOptions"
      />

      <!-- 闭环：从学生成长档案聚焦该生审批事项（桌面 / 移动共用） -->
      <div v-if="studentFilter" class="ap-focus">
        <el-icon :size="14"><User /></el-icon>
        <span class="ap-focus-text">已聚焦学生「{{ studentFilter.name || '该生' }}」，仅显示其审批事项</span>
        <button class="ap-focus-clear" type="button" @click="clearStudentFilter">清除聚焦</button>
      </div>

      <!-- ============================================================
           移动端 · 收件箱式
           进来先看一句待办规模，然后就是请假条 / 办事 / 材料列表：
           通过、驳回在条内直接完成，不再经过分类入口和二级核验页。
           ============================================================ -->
      <div v-if="isMobile && activeTab === 'pending'" class="apm-page">
        <div class="apm-sum">
          <b>{{ totalPending }}</b><span>条待你处理</span>
          <div class="sp"></div>
          <span class="apm-sum-meta">请假 {{ pendingLeaves.length }} · 办事 {{ pendingTickets.length }} · 材料 {{ pendingMaterials.length }}
          <template v-if="pendingScheduleChanges.length"> · 调课 {{ pendingScheduleChanges.length }}</template></span>
        </div>

        <div class="apm-filters">
          <button
            v-for="f in mobileFilterOptions"
            :key="f.value"
            type="button"
            class="apm-filter"
            :class="{ 'is-on': mobileKind === f.value }"
            @click="mobileKind = f.value"
          >{{ f.label }}<i>{{ f.count }}</i></button>
        </div>

        <div v-if="mobileKind === 'all' || mobileKind === 'leave'" class="apm-group">
          <div v-if="mobileKind === 'all' && pendingLeaves.length" class="apm-group-hd">
            <span>请假</span><em>{{ pendingLeaves.length }} 条待批</em>
          </div>
          <article v-for="l in pendingLeaves" :key="'leave-' + l.id" class="apm-leave">
            <div class="apm-leave-hd">
              <span class="apm-av" :style="{ background: avatarColor(l.student_name) }">{{ l.student_name.slice(0, 1) }}</span>
              <div class="apm-who">
                <b>{{ l.student_name }}</b>
                <span>{{ typeLabel(l.leave_type) }} · {{ leaveDays(l) }} 天</span>
              </div>
              <span class="apm-wait">{{ waitLabel(l.created_at) }}</span>
            </div>
            <div class="apm-meta"><el-icon :size="13"><Clock /></el-icon>{{ l.start_date }} – {{ l.end_date }}</div>
            <p class="apm-desc">{{ l.reason || '未填写请假理由' }}</p>
            <div class="apm-ft">
              <span class="apm-ai" :class="suggestCls(l)">
                <AiMascotMark :size="13" />{{ suggestText(l) }}<em v-if="aiReason(l)"> · {{ aiReason(l) }}</em>
              </span>
              <div class="apm-ops">
                <button type="button" class="apm-btn apm-btn-ghost" @click="showReject(l)">驳回</button>
                <button type="button" class="apm-btn apm-btn-ok" @click="handleApprove(l)">通过</button>
              </div>
            </div>
          </article>
          <div v-if="mobileKind === 'leave' && !pendingLeaves.length" class="apm-none">暂无待批请假</div>
        </div>

        <div v-if="mobileKind === 'all' || mobileKind === 'ticket'" class="apm-group">
          <div v-if="mobileKind === 'all' && pendingTickets.length" class="apm-group-hd">
            <span>办事</span><em>{{ pendingTickets.length }} 条待办</em>
          </div>
          <div v-for="row in pendingTickets" :key="'ticket-' + row.id" class="apm-row">
            <span class="apm-av" :style="{ background: avatarColor(row.applicant_name || '') }">{{ (row.applicant_name || '?').slice(0, 1) }}</span>
            <button type="button" class="apm-row-main" @click="openTicketDetail(row)">
              <b>{{ row.title }}</b>
              <span>{{ row.applicant_name || '—' }} · {{ ticketTypeLabel(row.type) }} · {{ timeLabel(row.created_at) }}</span>
            </button>
            <button v-if="!row.approver_name" type="button" class="apm-mini" @click="handleClaim(row)">受理</button>
            <button v-else type="button" class="apm-mini" @click="openTicketDetail(row)">详情</button>
          </div>
          <div v-if="mobileKind === 'ticket' && !pendingTickets.length" class="apm-none">暂无待办办事申请</div>
        </div>

        <div v-if="mobileKind === 'all' || mobileKind === 'material'" class="apm-group">
          <div v-if="mobileKind === 'all' && pendingMaterials.length" class="apm-group-hd">
            <span>材料</span><em>{{ pendingMaterials.length }} 条待归档</em>
          </div>
          <div v-for="row in pendingMaterials" :key="'material-' + row.id" class="apm-row apm-row-material">
            <span class="apm-av" :style="{ background: avatarColor(row.applicant_name || '') }">{{ (row.applicant_name || '?').slice(0, 1) }}</span>
            <div class="apm-row-main">
              <b>{{ row.title }}</b>
              <span>{{ row.applicant_name }} · {{ timeLabel(row.created_at) }}</span>
            </div>
            <div class="apm-room-ops">
              <button type="button" class="apm-mini" @click="handleMaterialReject(row.id)">驳回</button>
              <button type="button" class="apm-mini apm-mini-ok" @click="handleMaterialApprove(row.id)">归档</button>
            </div>
          </div>
          <div v-if="mobileKind === 'material' && !pendingMaterials.length" class="apm-none">暂无待归档材料</div>
        </div>

        <!-- 调课 / 增课：教师自己提交、等教务审批的申请（进度自查） -->
        <div v-if="mobileKind === 'all' || mobileKind === 'schedule'" class="apm-group">
          <div v-if="mobileKind === 'all' && pendingScheduleChanges.length" class="apm-group-hd">
            <span>调课 / 增课</span><em>{{ pendingScheduleChanges.length }} 条审批中</em>
          </div>
          <div v-for="r in pendingScheduleChanges" :key="'schedule-' + r.id" class="apm-row apm-row-schedule">
            <span class="apm-av apm-av-schedule">{{ r.kind === 'swap' ? '调' : '增' }}</span>
            <div class="apm-row-main">
              <b>{{ r.course_name }}</b>
              <span>
                {{ r.class_name }} · {{ weekdayText(r.day_of_week) }} 第{{ r.start_period }}-{{ r.end_period }}节
                · {{ timeLabel(r.created_at) }}
              </span>
            </div>
            <div class="apm-room-ops">
              <button type="button" class="apm-mini" @click="cancelMyChange(r.id)">撤回</button>
            </div>
          </div>
          <div v-if="mobileKind === 'schedule' && !pendingScheduleChanges.length" class="apm-none">暂无审批中的调课 / 增课申请</div>
        </div>

        <div v-if="!totalPending" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><CircleCheck /></el-icon></span>
          <span class="tui-empty-title">待办已清空</span>
          <span class="tui-empty-desc">新的请假、办事、材料或调课增课申请提交后会出现在这里</span>
        </div>
      </div>

      <template v-if="!isMobile && activeTab === 'pending'">
        <div v-if="pendingLeaves.length" id="ap-sec-leave" class="section-card">
          <div class="section-header">
            <h3><el-icon><Document /></el-icon> 请假申请</h3>
            <el-tag v-if="pendingLeaves.length" type="warning" effect="light" size="small">
              {{ pendingLeaves.length }} 条待批
            </el-tag>
            <el-tag v-else type="success" effect="light" size="small">已处理完</el-tag>
          </div>
          <!-- 桌面端卡片网格：等宽卡片（min 300px）自适应填充 -->
          <div v-if="paginatedPendingLeaves.length" class="ap-grid ap-grid-leave">
            <article v-for="row in paginatedPendingLeaves" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-name">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="ap-card-meta">
                <span class="ap-card-kv"><el-icon><Clock /></el-icon>{{ row.start_date }} ~ {{ row.end_date }}</span>
              </div>
              <p v-if="row.reason" class="ap-card-reason">{{ row.reason }}</p>
              <div class="ap-card-ai">
                <div v-if="isAnalyzed(row)" class="ai-analyze">
                  <el-tag :type="suggestCls(row) === 'tm-ok' ? 'success' : 'danger'" size="small" effect="plain">
                    {{ suggestText(row) }}
                  </el-tag>
                  <el-tooltip placement="top" :show-after="200">
                    <template #content>
                      <div style="max-width:280px;line-height:1.6;font-size:13px">{{ aiReason(row) }}</div>
                    </template>
                    <el-icon class="analyze-tip"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <el-tag v-else type="info" size="small" effect="plain" class="analyzing-tag">
                  <el-icon v-if="!analysisMap[row.id]" class="is-loading"><Loading /></el-icon> {{ suggestText(row) }}
                </el-tag>
              </div>
              <div class="ap-card-actions">
                <el-button type="success" size="small" @click="handleApprove(row)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="showReject(row)">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </div>
            </article>
          </div>
          <div class="pagination-wrapper" v-if="pendingLeaves.length > pageSizeLeaves">
            <el-pagination
              v-model:current-page="currentPageLeaves"
              v-model:page-size="pageSizeLeaves"
              :page-sizes="[10, 20, 50]"
              :total="pendingLeaves.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleLeaveSizeChange"
              @current-change="handleLeaveCurrentChange"
            />
          </div>
          <div v-else-if="!pendingLeaves.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><Document /></el-icon></span>
            <span class="tui-empty-title">暂无待批请假</span>
            <span class="tui-empty-desc">当前没有学生提交请假申请</span>
          </div>
        </div>

        <div v-if="pendingTickets.length" id="ap-sec-ticket" class="section-card">
          <div class="section-header">
            <h3><el-icon><Tickets /></el-icon> 办事申请</h3>
            <el-tag v-if="pendingTickets.length" type="warning" effect="light" size="small">
              {{ pendingTickets.length }} 条{{ ticketScope === 'mine' ? '我受理' : '待批' }}
            </el-tag>
            <el-tag v-else type="success" effect="light" size="small">
              {{ ticketScope === 'mine' ? '我暂无在办' : '已处理完' }}
            </el-tag>
          </div>
          <TuiSegmented
            v-model="ticketScope"
            class="ap-ticket-scope"
            :options="ticketScopeOptions"
          />

          <!-- 桌面端卡片网格：申请人 / 事项类型 / 事由 / 附件 / 时间 全部收进单张卡片，
               操作按钮固定在卡片底部，扫读与决策都在视线内完成 -->
          <div v-if="paginatedPendingTickets.length" class="ap-grid ap-grid-ticket">
            <article v-for="row in paginatedPendingTickets" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-name">{{ row.applicant_name || '—' }}</span>
                <el-tag size="small" effect="plain">{{ ticketTypeLabel(row.type) }}</el-tag>
              </div>
              <div class="ap-card-sub">{{ row.applicant_no || row.applicant_college || '' }}</div>
              <div class="ap-card-title">{{ row.title }}</div>
              <div class="ap-card-meta">
                <span class="ap-card-kv"><el-icon><Clock /></el-icon>{{ row.created_at ? row.created_at.slice(5, 16) : '—' }}</span>
                <span v-if="row.approver_name" class="ap-card-kv">
                  <el-icon><User /></el-icon>{{ row.approver_name }} 受理
                </span>
                <el-button v-else size="small" text type="primary" @click="handleClaim(row)">受理</el-button>
                <span v-if="row.attachments && row.attachments.length" class="ap-attach">
                  <el-icon><Paperclip /></el-icon>{{ row.attachments.length }}
                </span>
                <span v-else class="ap-muted">无附件</span>
              </div>
              <p v-if="row.content" class="ap-card-reason">{{ row.content }}</p>
              <div class="ap-card-actions">
                <el-button size="small" @click="openTicketDetail(row)"><el-icon><View /></el-icon>详情</el-button>
                <el-button type="success" size="small" @click="showTicketReview(row, 'approve')">通过</el-button>
                <el-button type="danger" size="small" plain @click="showTicketReview(row, 'reject')">拒绝</el-button>
              </div>
            </article>
          </div>

          <div class="pagination-wrapper" v-if="pendingTickets.length > pageSizeTickets">
            <el-pagination
              v-model:current-page="currentPageTickets"
              v-model:page-size="pageSizeTickets"
              :page-sizes="[10, 20, 50]"
              :total="pendingTickets.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleTicketSizeChange"
              @current-change="handleTicketCurrentChange"
            />
          </div>
          <div v-else-if="!pendingTickets.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><Tickets /></el-icon></span>
            <span class="tui-empty-title">暂无待办申请</span>
            <span class="tui-empty-desc">学生提交证明 / 项目 / 反馈等事项后会出现在这里</span>
          </div>
        </div>

        <div v-if="pendingMaterials.length" id="ap-sec-material" class="section-card">
          <div class="section-header">
            <h3><el-icon><FolderOpened /></el-icon> 材料档案</h3>
            <el-tag v-if="pendingMaterials.length" type="warning" effect="light" size="small">
              {{ pendingMaterials.length }} 条待归档
            </el-tag>
            <el-tag v-else type="success" effect="light" size="small">已处理完</el-tag>
          </div>
          <!-- 桌面端卡片网格：材料归档信息量小，卡片网格铺满一行即可批量扫读 -->
          <div v-if="pendingMaterials.length" class="ap-grid ap-grid-material">
            <article v-for="row in pendingMaterials" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-name">{{ row.applicant_name }}</span>
                <el-tag size="small" effect="plain">材料档案</el-tag>
              </div>
              <div class="ap-card-title">{{ row.title }}</div>
              <div class="ap-card-meta">
                <span class="ap-card-kv"><el-icon><Clock /></el-icon>{{ row.created_at ? row.created_at.slice(0, 16) : '—' }}</span>
              </div>
              <div class="ap-card-actions">
                <el-button type="success" size="small" @click="handleMaterialApprove(row.id)">
                  <el-icon><Check /></el-icon> 通过归档
                </el-button>
                <el-button type="danger" size="small" plain @click="handleMaterialReject(row.id)">
                  <el-icon><Close /></el-icon> 驳回
                </el-button>
              </div>
            </article>
          </div>
          <div v-if="!pendingMaterials.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><FolderOpened /></el-icon></span>
            <span class="tui-empty-title">暂无待归档材料</span>
            <span class="tui-empty-desc">学生上传材料后会出现在这里，可批量归档</span>
          </div>
        </div>

        <div v-if="!totalPending" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><CircleCheck /></el-icon></span>
          <span class="tui-empty-title">待办已清空</span>
          <span class="tui-empty-desc">新的请假、办事、材料或调课增课申请提交后会出现在这里</span>
        </div>
      </template>

      <template v-else-if="activeTab === 'approved'">
        <!-- 统一台账：请假与办事申请合成一份数据，不再按事项类别分区 -->
        <div class="section-card" :class="{ 'apm-flat': isMobile }">
          <div v-if="!isMobile" class="section-header">
            <h3><el-icon><CircleCheck /></el-icon> 已通过</h3>
            <el-tag v-if="approvedRows.length" type="info" effect="light" size="small">{{ approvedRows.length }} 条</el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedApprovedRows" v-if="approvedRows.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column label="学生 / 申请人" width="150">
                <template #default="{ row }">
                  {{ row.who }}<template v-if="row.meta"> · {{ row.meta }}</template>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.typeLabel }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="title" label="事项" min-width="150" show-overflow-tooltip />
              <el-table-column prop="desc" label="事由" min-width="150" show-overflow-tooltip />
              <el-table-column prop="note" label="审批意见" min-width="140" show-overflow-tooltip />
              <el-table-column label="处理时间" width="120">
                <template #default="{ row }">{{ row.time }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.statusType" size="small" effect="plain">{{ row.statusLabel }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <!-- 能进「已通过」的请假只剩查阅，审批动作已在别处完成 -->
                  <el-button
                    v-if="row.leave"
                    type="primary"
                    size="small"
                    text
                    @click="openLeaveDetail(row.leave)"
                  >详情</el-button>
                  <el-button
                    v-else-if="row.ticket"
                    type="primary"
                    size="small"
                    text
                    @click="openTicketDetail(row.ticket)"
                  >详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端：紧凑台账列表，一屏可扫多条 -->
          <div v-if="isMobile" class="apm-ledger">
            <article v-for="(row, i) in paginatedApprovedRows" :key="'approved-' + i" class="apm-ledger-card">
              <div class="apm-ledger-hd">
                <b>{{ row.who }}</b>
                <span class="apm-tag">{{ row.typeLabel }}</span>
                <time>{{ row.time }}</time>
              </div>
              <div class="apm-ledger-title">{{ row.title }}</div>
              <div v-if="row.desc" class="apm-ledger-sub">{{ row.desc }}</div>
              <div v-if="row.note" class="apm-ledger-note"><b>审批意见</b>{{ row.note }}</div>
              <div class="apm-ledger-ft">
                <span class="apm-status" :class="'is-' + row.statusType">{{ row.statusLabel }}</span>
                <button
                  v-if="row.leave"
                  type="button"
                  class="apm-mini"
                  @click="openLeaveDetail(row.leave)"
                >详情</button>
                <button
                  v-else-if="row.ticket"
                  type="button"
                  class="apm-mini"
                  @click="openTicketDetail(row.ticket)"
                >详情</button>
              </div>
            </article>
          </div>
          <div class="pagination-wrapper" v-if="approvedRows.length > pageSizeApproved">
            <el-pagination
              v-model:current-page="currentPageApproved"
              v-model:page-size="pageSizeApproved"
              :page-sizes="[10, 20, 50]"
              :total="approvedRows.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleApprovedSizeChange"
              @current-change="handleApprovedCurrentChange"
            />
          </div>
          <div v-else-if="!approvedRows.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><CircleCheck /></el-icon></span>
            <span class="tui-empty-title">暂无已通过记录</span>
            <span class="tui-empty-desc">审批通过的请假与办事申请都会归档到这里</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'rejected'">
        <!-- 统一台账：与「已通过」同口径，请假与办事申请合成一份数据 -->
        <div class="section-card" :class="{ 'apm-flat': isMobile }">
          <div v-if="!isMobile" class="section-header">
            <h3><el-icon><CircleClose /></el-icon> 已拒绝</h3>
            <el-tag v-if="rejectedRows.length" type="info" effect="light" size="small">{{ rejectedRows.length }} 条</el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedRejectedRows" v-if="rejectedRows.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column label="学生 / 申请人" width="150">
                <template #default="{ row }">
                  {{ row.who }}<template v-if="row.meta"> · {{ row.meta }}</template>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.typeLabel }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="title" label="事项" min-width="150" show-overflow-tooltip />
              <el-table-column prop="desc" label="事由" min-width="140" show-overflow-tooltip />
              <el-table-column prop="note" label="拒绝理由" min-width="140" show-overflow-tooltip />
              <el-table-column label="处理时间" width="120">
                <template #default="{ row }">{{ row.time }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.statusType" size="small" effect="plain">{{ row.statusLabel }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.ticket"
                    type="primary"
                    size="small"
                    text
                    @click="openTicketDetail(row.ticket)"
                  >详情</el-button>
                  <el-button
                    v-else-if="row.leave"
                    type="primary"
                    size="small"
                    text
                    @click="openLeaveDetail(row.leave)"
                  >详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端：紧凑拒绝台账，理由直接可见 -->
          <div v-if="isMobile" class="apm-ledger">
            <article v-for="(row, i) in paginatedRejectedRows" :key="'rejected-' + i" class="apm-ledger-card">
              <div class="apm-ledger-hd">
                <b>{{ row.who }}</b>
                <span class="apm-tag">{{ row.typeLabel }}</span>
                <time>{{ row.time }}</time>
              </div>
              <div class="apm-ledger-title">{{ row.title }}</div>
              <div v-if="row.desc" class="apm-ledger-sub">{{ row.desc }}</div>
              <div v-if="row.note" class="apm-ledger-note is-bad"><b>拒绝理由</b>{{ row.note }}</div>
              <div class="apm-ledger-ft">
                <span class="apm-status" :class="'is-' + row.statusType">{{ row.statusLabel }}</span>
                <button
                  v-if="row.ticket"
                  type="button"
                  class="apm-mini"
                  @click="openTicketDetail(row.ticket)"
                >详情</button>
                <button
                  v-else-if="row.leave"
                  type="button"
                  class="apm-mini"
                  @click="openLeaveDetail(row.leave)"
                >详情</button>
              </div>
            </article>
          </div>
          <div class="pagination-wrapper" v-if="rejectedRows.length > pageSizeRejected">
            <el-pagination
              v-model:current-page="currentPageRejected"
              v-model:page-size="pageSizeRejected"
              :page-sizes="[10, 20, 50]"
              :total="rejectedRows.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleRejectedSizeChange"
              @current-change="handleRejectedCurrentChange"
            />
          </div>
          <div v-else-if="!rejectedRows.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><CircleClose /></el-icon></span>
            <span class="tui-empty-title">暂无已拒绝记录</span>
            <span class="tui-empty-desc">被拒绝的请假与办事申请都会连同理由归档到这里</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'stats'">
        <!-- 审批总览：统一口径，不按事项类别细分 -->
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><DataAnalysis /></el-icon> 审批总览</h3>
            <el-tag type="info" effect="light" size="small">近 {{ FLOW_DAYS }} 天</el-tag>
          </div>
          <div class="tui-stat-row ap-overview">
            <div class="stat-box">
              <span class="stat-num">{{ stats?.total ?? 0 }}</span>
              <span class="stat-label">提交总量</span>
            </div>
            <div class="stat-box">
              <span class="stat-num warn">{{ stats?.pending ?? 0 }}</span>
              <span class="stat-label">待处理</span>
            </div>
            <div class="stat-box">
              <span class="stat-num ok">{{ stats?.approved ?? 0 }}</span>
              <span class="stat-label">已通过</span>
            </div>
            <div class="stat-box">
              <span class="stat-num danger">{{ stats?.rejected ?? 0 }}</span>
              <span class="stat-label">已拒绝</span>
            </div>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><PieChart /></el-icon> 按请假类型</h3>
          </div>
          <div v-if="leaveStats.by_type.length" class="stat-rows">
            <div v-for="item in leaveStats.by_type" :key="item.key" class="stat-row">
              <div class="stat-row-head">
                <span class="stat-row-label">{{ item.label }}</span>
                <span class="stat-row-total">{{ item.total }} 条</span>
              </div>
              <div class="stat-bar">
                <div class="stat-bar-seg seg-approved" :style="{ width: pct(item.approved, item.total) }"></div>
                <div class="stat-bar-seg seg-pending" :style="{ width: pct(item.pending, item.total) }"></div>
                <div class="stat-bar-seg seg-rejected" :style="{ width: pct(item.rejected, item.total) }"></div>
              </div>
              <div class="stat-legend">
                <span><i class="dot dot-approved"></i>通过 {{ item.approved }}</span>
                <span><i class="dot dot-pending"></i>待批 {{ item.pending }}</span>
                <span><i class="dot dot-rejected"></i>拒绝 {{ item.rejected }}</span>
              </div>
            </div>
          </div>
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><PieChart /></el-icon></span>
            <span class="tui-empty-title">暂无类型统计数据</span>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Histogram /></el-icon> 按班级分布</h3>
          </div>
          <div v-if="leaveStats.by_class.length" class="stat-rows">
            <div v-for="item in leaveStats.by_class" :key="item.key" class="stat-row">
              <div class="stat-row-head">
                <span class="stat-row-label">{{ item.label }}</span>
                <span class="stat-row-total">{{ item.total }} 条</span>
              </div>
              <div class="stat-bar">
                <div class="stat-bar-seg seg-approved" :style="{ width: pct(item.approved, item.total) }"></div>
                <div class="stat-bar-seg seg-pending" :style="{ width: pct(item.pending, item.total) }"></div>
                <div class="stat-bar-seg seg-rejected" :style="{ width: pct(item.rejected, item.total) }"></div>
              </div>
              <div class="stat-legend">
                <span><i class="dot dot-approved"></i>通过 {{ item.approved }}</span>
                <span><i class="dot dot-pending"></i>待批 {{ item.pending }}</span>
                <span><i class="dot dot-rejected"></i>拒绝 {{ item.rejected }}</span>
              </div>
            </div>
          </div>
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><Histogram /></el-icon></span>
            <span class="tui-empty-title">暂无班级分布数据</span>
          </div>
        </div>
      </template>
    </div>

    <!-- ===================== 办事申请详情（先看清再审批） ===================== -->
    <!-- 办事申请详情（重内容：移动端=全屏子页 / 桌面端=弹窗） -->
    <ResponsivePopup
      v-model="ticketDetailVisible"
      title="办事申请详情"
      width="420px"
      align-center
      destroy-on-close
      class="ap-dialog"
    >
      <div v-if="ticketDetailTarget" class="ap-detail">
        <div class="tui-section-hint" :class="{ success: !isTicketReviewable(ticketDetailTarget.status) }">
          <el-icon><InfoFilled /></el-icon>
          <span v-if="isTicketReviewable(ticketDetailTarget.status)">请核对申请人、事由与附件后再决定；通过后由对应科室出证，拒绝须写明理由并会推送学生。</span>
          <span v-else>该申请已审批完成，终态不可再变更；以下为留痕信息，附件可直接打开查看。</span>
        </div>

        <div class="ap-detail-head">
          <div class="ap-detail-who">
            <span class="ap-detail-name">{{ ticketDetailTarget.applicant_name || '—' }}</span>
            <span class="ap-detail-meta">
              <template v-if="ticketDetailTarget.applicant_no">{{ ticketDetailTarget.applicant_no }}</template>
              <template v-if="ticketDetailTarget.applicant_college"> · {{ ticketDetailTarget.applicant_college }}</template>
            </span>
          </div>
          <div class="ap-detail-tags">
            <el-tag size="small" effect="plain">{{ ticketTypeLabel(ticketDetailTarget.type) }}</el-tag>
            <el-tag size="small" effect="light" type="warning">{{ ticketStatusLabel(ticketDetailTarget.status) }}</el-tag>
          </div>
        </div>

        <el-descriptions :column="1" border size="small" class="ap-detail-desc">
          <el-descriptions-item label="事项标题">{{ ticketDetailTarget.title || '—' }}</el-descriptions-item>
          <el-descriptions-item label="事由说明">{{ ticketDetailTarget.content || '—' }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">
            {{ ticketDetailTarget.created_at ? ticketDetailTarget.created_at.slice(0, 16) : '—' }}
          </el-descriptions-item>
          <el-descriptions-item
            v-for="(v, k) in (ticketDetailTarget.form_data || {})"
            :key="k"
            :label="ticketFormLabel(String(k))"
          >{{ v }}</el-descriptions-item>
        </el-descriptions>

        <div class="ap-detail-block">
          <div class="ap-detail-block-title"><el-icon><Paperclip /></el-icon> 附件</div>
          <div v-if="ticketDetailTarget.attachments && ticketDetailTarget.attachments.length" class="ap-detail-files">
            <a v-for="(f, i) in ticketDetailTarget.attachments" :key="i" :href="f" target="_blank" rel="noopener" class="ap-detail-file">
              <el-icon><Paperclip /></el-icon>
              <span>{{ String(f).split('/').pop() }}</span>
            </a>
          </div>
          <div v-else class="ap-muted">该申请没有上传附件</div>
        </div>
      </div>

      <template #footer>
        <el-button @click="ticketDetailVisible = false">关闭</el-button>
        <el-button
          v-if="ticketDetailTarget && isTicketReviewable(ticketDetailTarget.status)"
          type="danger"
          plain
          @click="reviewFromDetail(ticketDetailTarget, 'reject')"
        >拒绝申请</el-button>
        <el-button
          v-if="ticketDetailTarget && isTicketReviewable(ticketDetailTarget.status)"
          type="success"
          @click="reviewFromDetail(ticketDetailTarget, 'approve')"
        >通过申请</el-button>
      </template>
    </ResponsivePopup>

    <!-- ===================== 请假详情（只读留痕） ===================== -->
    <!-- 请假审批完成后没有任何操作入口，但老师仍需要回看：起止 / 天数 / 事由 / 审批结论 -->
    <ResponsivePopup
      v-model="leaveDetailVisible"
      title="请假详情"
      width="420px"
      align-center
      destroy-on-close
      class="ap-dialog"
    >
      <div v-if="leaveDetailTarget" class="ap-detail">
        <div class="tui-section-hint success">
          <el-icon><InfoFilled /></el-icon>
          <span>此处为请假留痕信息，仅供查阅，不可再变更状态。</span>
        </div>

        <div class="ap-detail-head">
          <div class="ap-detail-who">
            <span class="ap-detail-name">{{ leaveDetailTarget.student_name || '—' }}</span>
            <span class="ap-detail-meta">学号 {{ leaveDetailTarget.student_id }}</span>
          </div>
          <div class="ap-detail-tags">
            <el-tag size="small" effect="plain">{{ typeLabel(leaveDetailTarget.leave_type) }}</el-tag>
            <el-tag size="small" effect="light" :type="leaveDetailStatus(leaveDetailTarget).type">
              {{ leaveDetailStatus(leaveDetailTarget).label }}
            </el-tag>
          </div>
        </div>

        <el-descriptions :column="1" border size="small" class="ap-detail-desc">
          <el-descriptions-item label="起止日期">
            {{ leaveDetailTarget.start_date }} ~ {{ leaveDetailTarget.end_date }}
          </el-descriptions-item>
          <el-descriptions-item label="请假天数">{{ leaveDays(leaveDetailTarget) }} 天</el-descriptions-item>
          <el-descriptions-item label="请假类型">{{ typeLabel(leaveDetailTarget.leave_type) }}</el-descriptions-item>
          <el-descriptions-item label="请假事由">{{ leaveDetailTarget.reason || '—' }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">
            {{ leaveDetailTarget.created_at ? leaveDetailTarget.created_at.slice(0, 16).replace('T', ' ') : '—' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="leaveDetailTarget.status === 'approved'" label="审批结果">
            <span class="ap-ok">已通过</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="leaveDetailTarget.status === 'approved'" label="审批时间">
            {{ leaveDetailTarget.updated_at ? leaveDetailTarget.updated_at.slice(0, 16).replace('T', ' ') : '—' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="leaveDetailTarget.status === 'rejected'" label="拒绝理由">
            <span class="ap-bad">{{ leaveDetailTarget.reject_reason || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <template #footer>
        <el-button @click="leaveDetailVisible = false">关闭</el-button>
      </template>
    </ResponsivePopup>

    <!-- ===================== 请假拒绝（1 字段：移动端=底部动作面板） ===================== -->
    <ActionSheet
      v-model="rejectVisible"
      title="拒绝请假"
      width="380px"
      align-center
      :close-on-click-modal="false"
      class="ap-dialog"
    >
      <div class="ap-dialog-context" v-if="rejectTarget">
        <el-icon><InfoFilled /></el-icon>
        <span>
          正在拒绝 <b>{{ rejectTarget.student_name }}</b> 的
          {{ typeLabel(rejectTarget.leave_type) }}（{{ rejectTarget.start_date }} ~ {{ rejectTarget.end_date }}）。
          理由将同步推送给学生。
        </span>
      </div>
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules" label-position="top">
        <el-form-item label="拒绝理由" prop="reason">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请填写拒绝理由，如：请假天数超出规定" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒绝</el-button>
      </template>
    </ActionSheet>

    <!-- ===================== 材料驳回（1 字段：移动端=底部动作面板） ===================== -->
    <ActionSheet
      v-model="rejectMaterialVisible"
      title="驳回材料"
      width="380px"
      align-center
      :close-on-click-modal="false"
      class="ap-dialog"
    >
      <div class="tui-section-hint warn">
        <el-icon><InfoFilled /></el-icon>
        <span>驳回后学生可修改并重新提交；请写明原因，便于学生一次改对。</span>
      </div>
      <el-form label-position="top">
        <el-form-item label="驳回理由" required>
          <el-input v-model="rejectMaterialReason" type="textarea" :rows="3" placeholder="请填写驳回理由，如：材料不清晰、格式不符合要求" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectMaterialVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmMaterialReject">确认驳回</el-button>
      </template>
    </ActionSheet>

    <!-- ===================== 办事申请 通过 / 拒绝（1 字段：移动端=底部动作面板） ===================== -->
    <ActionSheet
      :title="ticketReviewAction === 'approve' ? '通过办事申请' : '拒绝办事申请'"
      v-model="ticketReviewVisible"
      width="380px"
      align-center
      :close-on-click-modal="false"
      class="ap-dialog"
    >
      <div class="ap-dialog-context" v-if="ticketReviewTarget">
        <el-icon><InfoFilled /></el-icon>
        <span>
          <b>{{ ticketReviewTarget.applicant_name }}</b> · {{ ticketTypeLabel(ticketReviewTarget.type) }} ·
          {{ ticketReviewTarget.title }}
        </span>
      </div>
      <el-form label-position="top">
        <el-form-item :label="ticketReviewAction === 'approve' ? '审批意见（选填）' : '拒绝理由（必填）'" :required="ticketReviewAction === 'reject'">
          <el-input v-model="ticketReviewComment" type="textarea" :rows="3" :placeholder="ticketReviewAction === 'approve' ? '可填写审批意见，如：同意，请到教务处领取' : '请填写拒绝意见，如：材料不全，请补充后重新提交'" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ticketReviewVisible = false">取消</el-button>
        <el-button :type="ticketReviewAction === 'approve' ? 'success' : 'danger'" @click="confirmTicketReview">
          {{ ticketReviewAction === 'approve' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </ActionSheet>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onActivated, onMounted, watch } from 'vue'
// v6.1 弹窗减负：详情走全屏子页，单字段审批走底部动作面板
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import ActionSheet from '@/components/common/ActionSheet.vue'
import { useRoute, useRouter } from 'vue-router'
import SubPageHeader from '@/components/common/SubPageHeader.vue'

// keep-alive 缓存需要显式组件名（include 按 name 匹配，见 TeacherLayout cachedNames）
defineOptions({ name: 'teacher-approval' })
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { ElMessage } from 'element-plus'
import {
  Document, Tickets, CircleCheck, CircleClose,
  InfoFilled, Loading, Check, Close, FolderOpened, PieChart, Histogram, User,
  View, Paperclip, Clock, DataAnalysis
} from '@element-plus/icons-vue'
import AiMascotMark from '@/components/teacher/ui/AiMascotMark.vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave, getLeaveStats, type LeaveStats } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi, claimTicket } from '@/api/service'
import { getApprovalPending, reviewApproval, getApprovalStats, type ApprovalItem, type ApprovalStats } from '@/api/approval'
import { cancelScheduleChange, getPendingScheduleChanges, WEEKDAY_LABELS, type ScheduleChangeItem } from '@/api/scheduleChange'
import type { LeaveRequestOut, ServiceTicket } from '@/types'
import { useResponsive } from '@/composables/useResponsive'

const { isMobile } = useResponsive()

/** 移动端下拉刷新：手动刷新按钮已移除，统一由下拉手势触发 */
const pull = usePullRefresh(loadData, { enabled: () => isMobile.value })

const route = useRoute()
const router = useRouter()

/** 闭环：从学生成长档案跳来时聚焦该生，只显示其审批事项 */
const studentFilter = ref<{ id: number; name: string } | null>(null)

function byStudent(id?: number | null, name?: string | null) {
  const f = studentFilter.value
  if (!f) return true
  if (f.id && id != null) return id === f.id
  if (f.name && name) return name === f.name
  return true
}

function clearStudentFilter() {
  studentFilter.value = null
  router.replace({ path: '/teacher/approval' })
  // 聚焦范围变了：徽标计数与当前页签数据都要按「全部学生」重算
  void loadAllCounts()
  void loadData()
}

const activeTab = ref('pending')
/** 移动端列表筛选：默认全部，请假 / 办事 / 材料 / 调课增课一键收窄 */
const mobileKind = ref<'all' | 'leave' | 'ticket' | 'material' | 'schedule'>('all')
const mobileFilterOptions = computed(() => [
  { value: 'all' as const, label: '全部', count: totalPending.value },
  { value: 'leave' as const, label: '请假', count: pendingLeaves.value.length },
  { value: 'ticket' as const, label: '办事', count: pendingTickets.value.length },
  { value: 'material' as const, label: '材料', count: pendingMaterials.value.length },
  { value: 'schedule' as const, label: '调课', count: pendingScheduleChanges.value.length },
])

/** 办事工单视图：共享队列（先到先审）/ 我受理的（责任人是我）——对齐成熟工单系统的 Queue / My tickets */
const ticketScope = ref<'queue' | 'mine'>('queue')
const ticketScopeOptions = [
  { value: 'queue', label: '共享队列' },
  { value: 'mine', label: '我受理的' },
]
const pendingLeaves = ref<LeaveRequestOut[]>([])
const pendingTickets = ref<ServiceTicket[]>([])
const pendingMaterials = ref<ApprovalItem[]>([])
/** 我提交、仍在等教务审批的调课 / 增课申请 */
const pendingScheduleChanges = ref<ScheduleChangeItem[]>([])

function weekdayText(d: number | null | undefined) {
  return (d && WEEKDAY_LABELS[d]) || '—'
}

async function loadMyScheduleChanges() {
  try {
    pendingScheduleChanges.value = await getPendingScheduleChanges()
  } catch {
    pendingScheduleChanges.value = []
  }
}

async function cancelMyChange(id: number) {
  try {
    await cancelScheduleChange(id)
    ElMessage.success('已撤回')
    await loadMyScheduleChanges()
  } catch {
    ElMessage.error('撤回失败')
  }
}

const stats = ref<ApprovalStats | null>(null)
const approvedLeaves = ref<LeaveRequestOut[]>([])
const approvedTickets = ref<ServiceTicket[]>([])
const rejectedLeaves = ref<LeaveRequestOut[]>([])
const rejectedTickets = ref<ServiceTicket[]>([])
const leaveStats = ref<LeaveStats>({
  total: 0, approved: 0, rejected: 0, pending: 0,
  by_type: [], by_class: [],
})
const analysisMap = ref<Record<number, { suggestion: string; reason: string }>>({})
const rejectVisible = ref(false)
const rejectTarget = ref<LeaveRequestOut | null>(null)
const rejectFormRef = ref<any>()
const rejectForm = reactive({ reason: '' })
// 材料档案驳回弹窗状态
const rejectMaterialTarget = ref<number | null>(null)
const rejectMaterialReason = ref('')
const rejectMaterialVisible = ref(false)
// 工单审批弹窗状态
const ticketReviewVisible = ref(false)
const ticketReviewTarget = ref<ServiceTicket | null>(null)
const ticketReviewAction = ref<'approve' | 'reject'>('approve')
const ticketReviewComment = ref('')
const rejectRules = {
  reason: [{ required: true, message: '请填写拒绝理由', trigger: 'blur' }],
}
// 请假分页相关状态（每页 10 条，避免分页条过大）
const currentPageLeaves = ref(1)
const pageSizeLeaves = ref(10)

// 工单分页相关状态
const currentPageTickets = ref(1)
const pageSizeTickets = ref(10)

// 已通过 / 已拒绝台账分页相关状态（统一台账，不区分事项类别）
const currentPageApproved = ref(1)
const pageSizeApproved = ref(10)
const currentPageRejected = ref(1)
const pageSizeRejected = ref(10)

const totalPending = computed(
  () =>
    pendingLeaves.value.length +
    pendingTickets.value.length +
    pendingMaterials.value.length +
    pendingScheduleChanges.value.length,
)

/** 审批流程统计口径（天）：链路条与统计页共用，避免两处天数各写一个 */
const FLOW_DAYS = 30

/** 分段控件选项：与 activeTab 取值一一对应，count 为对应待处理数量 */
const tabOptions = computed(() => [
  { value: 'pending', label: '待审批', count: totalPending.value },
  { value: 'approved', label: '已通过', count: approvedRows.value.length || undefined },
  { value: 'rejected', label: '已拒绝', count: rejectedRows.value.length || undefined },
  { value: 'stats', label: '统计' },
])

const paginatedPendingLeaves = computed(() => {
  const start = (currentPageLeaves.value - 1) * pageSizeLeaves.value
  const end = start + pageSizeLeaves.value
  return pendingLeaves.value.slice(start, end)
})

const paginatedPendingTickets = computed(() => {
  const start = (currentPageTickets.value - 1) * pageSizeTickets.value
  const end = start + pageSizeTickets.value
  return pendingTickets.value.slice(start, end)
})

/** 统一台账行：请假与办事申请归一到同一套字段，列表不再按事项类别分区 */
interface LedgerRow {
  key: string
  who: string
  meta: string
  typeLabel: string
  /** 事项：请假=起止日期，办事=事项标题 */
  title: string
  /** 事由：请假=原因，办事=事由说明 */
  desc: string
  /** 结果说明：请假=拒绝理由，办事=审批意见 */
  note: string
  time: string
  statusLabel: string
  statusType: 'success' | 'warning' | 'danger'
  /** 时间戳，仅用于统一台账排序 */
  sortAt: string
  leave?: LeaveRequestOut
  ticket?: ServiceTicket
}

/** 台账时间：优先取「处理时间」——刚审批完的记录才能排在最前面；
    历史数据只有创建时间时退回创建时间 */
function ledgerTime(updated?: string | null, created?: string | null) {
  const raw = updated || created || ''
  return raw ? raw.slice(0, 16).replace('T', ' ') : '—'
}

/** 台账排序键：处理时间优先 */
function ledgerSortAt(updated?: string | null, created?: string | null) {
  return updated || created || ''
}

/** 已通过台账：请假 + 办事申请，按处理时间倒序（刚办完的排最前） */
const approvedRows = computed<LedgerRow[]>(() =>
  [
    ...approvedLeaves.value.map((l) => ({
      key: `leave-${l.id}`,
      who: l.student_name,
      meta: '',
      typeLabel: typeLabel(l.leave_type),
      title: `${l.start_date} ~ ${l.end_date}`,
      desc: l.reason || '',
      note: '',
      time: ledgerTime(l.updated_at, l.created_at),
      statusLabel: '已通过',
      statusType: 'success' as const,
      sortAt: ledgerSortAt(l.updated_at, l.created_at),
      leave: l,
    })),
    ...approvedTickets.value.map((t) => ({
      key: `ticket-${t.id}`,
      who: t.applicant_name || '—',
      meta: t.applicant_no || '',
      typeLabel: ticketTypeLabel(t.type),
      title: t.title || '—',
      desc: t.content || '',
      note: t.review_comment || '',
      time: ledgerTime(t.updated_at, t.created_at),
      statusLabel: '已通过',
      statusType: 'success' as const,
      sortAt: ledgerSortAt(t.updated_at, t.created_at),
      ticket: t,
    })),
  ].sort((a, b) => (a.sortAt < b.sortAt ? 1 : a.sortAt > b.sortAt ? -1 : 0)),
)

/** 已拒绝台账：同口径，拒绝理由统一放在 note */
const rejectedRows = computed<LedgerRow[]>(() =>
  [
    ...rejectedLeaves.value.map((l) => ({
      key: `leave-${l.id}`,
      who: l.student_name,
      meta: '',
      typeLabel: typeLabel(l.leave_type),
      title: `${l.start_date} ~ ${l.end_date}`,
      desc: l.reason || '',
      note: l.reject_reason || '',
      time: ledgerTime(l.updated_at, l.created_at),
      statusLabel: '已拒绝',
      statusType: 'danger' as const,
      sortAt: ledgerSortAt(l.updated_at, l.created_at),
      leave: l,
    })),
    ...rejectedTickets.value.map((t) => ({
      key: `ticket-${t.id}`,
      who: t.applicant_name || '—',
      meta: t.applicant_no || '',
      typeLabel: ticketTypeLabel(t.type),
      title: t.title || '—',
      desc: t.content || '',
      note: t.review_comment || '',
      time: ledgerTime(t.updated_at, t.created_at),
      statusLabel: '已拒绝',
      statusType: 'danger' as const,
      sortAt: ledgerSortAt(t.updated_at, t.created_at),
      ticket: t,
    })),
  ].sort((a, b) => (a.sortAt < b.sortAt ? 1 : a.sortAt > b.sortAt ? -1 : 0)),
)

const paginatedApprovedRows = computed(() => {
  const start = (currentPageApproved.value - 1) * pageSizeApproved.value
  return approvedRows.value.slice(start, start + pageSizeApproved.value)
})

const paginatedRejectedRows = computed(() => {
  const start = (currentPageRejected.value - 1) * pageSizeRejected.value
  return rejectedRows.value.slice(start, start + pageSizeRejected.value)
})

function handleLeaveSizeChange() {
  currentPageLeaves.value = 1
}

function handleLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleTicketSizeChange() {
  currentPageTickets.value = 1
}

function handleTicketCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleApprovedSizeChange() {
  currentPageApproved.value = 1
}

function handleApprovedCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleRejectedSizeChange() {
  currentPageRejected.value = 1
}

function handleRejectedCurrentChange() {
  // 页码变化时自动更新表格数据
}

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

/* AI 分析分档：approve → 建议通过，其余 → 需判断；分析未返回时不冒充已审。 */
function isAnalyzed(l: LeaveRequestOut) {
  const a = analysisMap.value[l.id]
  if (!a) return false
  return !a.reason.includes('分析中') && !a.reason.includes('不可用')
}
function leaveDays(l: LeaveRequestOut) {
  if (!l.start_date || !l.end_date) return 0
  const ms = new Date(l.end_date).getTime() - new Date(l.start_date).getTime()
  return Math.max(1, Math.round(ms / 86400000) + 1)
}
const AVATAR_COLORS = ['#2f6df6', '#0f97a6', '#6941c6', '#0f8e6b', '#c4700e', '#475467']
function avatarColor(name?: string | null) {
  let n = 0
  for (const ch of name || '') n += ch.charCodeAt(0)
  return AVATAR_COLORS[n % AVATAR_COLORS.length]
}
function timeLabel(iso?: string | null) {
  return iso ? iso.slice(5, 16).replace('T', ' ') : '—'
}
function waitLabel(iso?: string | null) {
  if (!iso) return '待处理'
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return '待处理'
  const mins = Math.max(1, Math.floor((Date.now() - t) / 60000))
  if (mins < 60) return `等 ${mins} 分钟`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `等 ${hours} 小时`
  return `等 ${Math.floor(hours / 24)} 天`
}
function suggestText(l: LeaveRequestOut) {
  if (!isAnalyzed(l)) {
    return analysisMap.value[l.id]?.reason?.includes('不可用') ? 'AI 暂不可用' : 'AI 分析中'
  }
  return analysisMap.value[l.id]?.suggestion === 'approve' ? '建议通过' : '需判断'
}
function suggestCls(l: LeaveRequestOut) {
  if (!isAnalyzed(l)) return 'tm-mute'
  return analysisMap.value[l.id]?.suggestion === 'approve' ? 'tm-ok' : 'tm-warn'
}
function aiReason(l: LeaveRequestOut) {
  if (!isAnalyzed(l)) return ''
  return analysisMap.value[l.id]?.reason || ''
}
/** 办事申请类型标签（与后端 ServiceTicket.type 对齐：leave / certificate / project / feedback）
    注意：leave 是历史遗留的「补假申请」事项，标签用「补假」避免和「请假申请」混为一谈 */
const ticketTypeMap: Record<string, string> = {
  leave: '补假',
  certificate: '证明',
  project: '项目',
  feedback: '反馈',
}
function ticketTypeLabel(t?: string) {
  if (!t) return '办事'
  return ticketTypeMap[t] || t
}

/** 办事工单状态标签：对齐成熟工单系统的生命周期
    （待受理 → 处理中「已认领」→ 已通过 / 已驳回，后两者为办结终态） */
const ticketStatusMap: Record<string, string> = {
  pending: '待受理',
  processing: '处理中',
  approved: '已通过',
  rejected: '已驳回',
}
function ticketStatusLabel(s?: string) {
  return s ? ticketStatusMap[s] || s : '—'
}

/** 只有待审批 / 处理中的工单能再操作：终态（已通过 / 已拒绝）详情里不再给「通过 / 拒绝」 */
function isTicketReviewable(s?: string) {
  return s === 'pending' || s === 'processing'
}

/** 办事申请表单字段中文名（form_data 的 key → 中文） */
const ticketFormLabelMap: Record<string, string> = {
  leave_type: '请假类型',
  start_date: '开始日期',
  end_date: '结束日期',
  certificate_type: '证明类型',
  quantity: '份数',
  project_type: '项目类型',
  project_name: '项目名称',
  advisor: '指导老师',
  team_members: '团队成员',
  budget: '预算',
  dormitory_building: '宿舍楼',
  dormitory_room: '宿舍号',
  parent_proof: '家长证明',
}
function ticketFormLabel(k: string) {
  return ticketFormLabelMap[k] || k
}

/** 办事申请详情弹窗：先看清申请人 / 事由 / 附件，再决定通过或拒绝 */
const ticketDetailVisible = ref(false)
const ticketDetailTarget = ref<ServiceTicket | null>(null)
function openTicketDetail(row: ServiceTicket) {
  ticketDetailTarget.value = row
  ticketDetailVisible.value = true
}
/** 请假详情弹窗：只读留痕，不复用审批表单（审批动作仍走原来的审批弹窗） */
const leaveDetailVisible = ref(false)
const leaveDetailTarget = ref<LeaveRequestOut | null>(null)
function openLeaveDetail(row: LeaveRequestOut) {
  leaveDetailTarget.value = row
  leaveDetailVisible.value = true
}
/** 请假详情里的状态胶囊：与台账 statusLabel 保持同一口径 */
function leaveDetailStatus(l: LeaveRequestOut) {
  if (l.status === 'pending') return { label: '待审批', type: 'warning' as const }
  if (l.status === 'rejected') return { label: '已拒绝', type: 'danger' as const }
  if (l.status === 'approved') return { label: '已通过', type: 'success' as const }
  return { label: l.status || '—', type: 'info' as const }
}

/** 详情弹窗内直接审批：关闭详情并复用统一的审批弹窗 */
function reviewFromDetail(row: ServiceTicket, action: 'approve' | 'reject') {
  ticketDetailVisible.value = false
  showTicketReview(row, action)
}

async function loadData() {
  const sid = studentFilter.value?.id || undefined
  loadStats()
  void loadMyScheduleChanges()
  if (activeTab.value === 'pending') {
    try {
      pendingLeaves.value = (await getPendingLeaves(sid)).filter((l) => byStudent(l.student_id, l.student_name))
      loadAnalysis()
    } catch {}
    try {
      pendingTickets.value = (await getTickets({ scope: ticketScope.value, student_id: sid }))
        .filter((t: ServiceTicket) => (t.status === 'pending' || t.status === 'processing') && byStudent(undefined, t.applicant_name))
    } catch {}
    try {
      pendingMaterials.value = (await getApprovalPending({ kind: 'material', status: 'pending', student_id: sid }))
        .filter((m) => byStudent(m.applicant_id, m.applicant_name))
    } catch { pendingMaterials.value = [] }
  } else if (activeTab.value === 'approved') {
    try { approvedLeaves.value = (await getAllLeaves('approved', sid)).filter((l) => byStudent(l.student_id, l.student_name)) } catch {}
    // 闭环：审批通过的办事申请同样要留痕在「已通过」，否则通过后就查不到了
    try {
      approvedTickets.value = (await getTickets({ status: 'approved', student_id: sid }))
        .filter((t: ServiceTicket) => byStudent(undefined, t.applicant_name))
    } catch { approvedTickets.value = [] }
  } else if (activeTab.value === 'rejected') {
    try { rejectedLeaves.value = (await getAllLeaves('rejected', sid)).filter((l) => byStudent(l.student_id, l.student_name)) } catch {}
    // 闭环：被拒绝的办事申请同样要留痕在「已拒绝」
    try {
      rejectedTickets.value = (await getTickets({ status: 'rejected', student_id: sid }))
        .filter((t: ServiceTicket) => byStudent(undefined, t.applicant_name))
    } catch { rejectedTickets.value = [] }
  } else if (activeTab.value === 'stats') {
    await loadLeaveStats()
  }
}

async function loadLeaveStats() {
  try { leaveStats.value = await getLeaveStats() } catch { /* 统计失败不影响其它 Tab */ }
}

/**
 * 一次性预取三个页签的列表，只为了把页签徽标上的数字（待审批 N / 已通过 N / 已拒绝 N）填上。
 *
 * 背景：loadData() 是按当前页签【分支】只拉一个页签，其余页签的数组一直是空的，
 * 于是「已通过 8」「已拒绝 2」这些计数只有切过去之后才有值 —— 视觉上就是数据没同步。
 * 这里在进入页面时把三份列表并发拉一次；数据量本就是分页展示的，一次拉全量可接受。
 * 注意：只填充计数用的数组，不改变当前页签的展示，也不额外触发渲染分支。
 */
async function loadAllCounts() {
  const sid = studentFilter.value?.id || undefined
  await Promise.allSettled([
    (async () => {
      approvedLeaves.value = (await getAllLeaves('approved', sid)).filter((l) => byStudent(l.student_id, l.student_name))
    })(),
    (async () => {
      approvedTickets.value = (await getTickets({ status: 'approved', student_id: sid }))
        .filter((t: ServiceTicket) => byStudent(undefined, t.applicant_name))
    })(),
    (async () => {
      rejectedLeaves.value = (await getAllLeaves('rejected', sid)).filter((l) => byStudent(l.student_id, l.student_name))
    })(),
    (async () => {
      rejectedTickets.value = (await getTickets({ status: 'rejected', student_id: sid }))
        .filter((t: ServiceTicket) => byStudent(undefined, t.applicant_name))
    })(),
  ])
}

/** 统计条形图分段宽度百分比 */
function pct(part: number, total: number) {
  if (!total) return '0%'
  return `${Math.round((part / total) * 100)}%`
}

async function loadStats() {
  try { stats.value = await getApprovalStats(FLOW_DAYS, studentFilter.value?.id || undefined) } catch { stats.value = null }
}

async function handleMaterialApprove(id: number) {
  try {
    await reviewApproval('material', id, 'approve')
    ElMessage.success('已通过归档')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function handleMaterialReject(id: number) {
  rejectMaterialTarget.value = id
  rejectMaterialReason.value = ''
  rejectMaterialVisible.value = true
}

async function confirmMaterialReject() {
  if (!rejectMaterialTarget.value) return
  if (!rejectMaterialReason.value.trim()) return ElMessage.warning('请填写驳回原因')
  try {
    await reviewApproval('material', rejectMaterialTarget.value, 'reject', rejectMaterialReason.value)
    ElMessage.success('已驳回')
    rejectMaterialVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function chunk<T>(arr: T[], size: number): T[][] {
  const result: T[][] = []
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size))
  }
  return result
}

async function loadAnalysis() {
  // 筛选尚未分析的记录
  const todo = pendingLeaves.value.filter((leave) => !analysisMap.value[leave.id])
  // 先放占位符，UI 立即显示"分析中"
  for (const leave of todo) {
    analysisMap.value[leave.id] = { suggestion: 'approve', reason: '分析中...' }
  }
  // 分批并发（每批 4 个）
  const batches = chunk(todo, 4)
  for (const batch of batches) {
    const results = await Promise.all(
      batch.map(async (leave) => {
        try {
          const result = await analyzeLeave(leave.id)
          return { id: leave.id, result }
        } catch (e) {
          console.error('[AI分析失败]', leave.id, e)
          return { id: leave.id, result: { suggestion: 'approve', reason: 'AI分析暂时不可用' } }
        }
      })
    )
    for (const { id, result } of results) {
      analysisMap.value[id] = result
    }
  }
}

async function handleApprove(row: LeaveRequestOut) {
  try {
    await reviewLeaveApi(row.id, 'approve')
    ElMessage.success('已通过')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function showReject(row: LeaveRequestOut) {
  rejectTarget.value = row
  rejectForm.reason = ''
  rejectFormRef.value?.clearValidate?.()
  rejectVisible.value = true
}

async function confirmReject() {
  if (!rejectTarget.value) return
  if (rejectFormRef.value) {
    try { await rejectFormRef.value.validate() } catch { return }
  }
  try {
    await reviewLeaveApi(rejectTarget.value.id, 'reject', rejectForm.reason || undefined)
    ElMessage.success('已拒绝')
    rejectVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

/** 受理（认领）工单：把责任人落到自己名下，队列里其他人能看到「谁在处理」 */
async function handleClaim(row: ServiceTicket) {
  try {
    await claimTicket(row.id)
    ElMessage.success('已受理，开始处理')
    loadData()
  } catch {
    ElMessage.error('受理失败，可能已被他人受理')
    loadData()
  }
}

function showTicketReview(row: ServiceTicket, action: 'approve' | 'reject') {
  ticketReviewTarget.value = row
  ticketReviewAction.value = action
  ticketReviewComment.value = ''
  ticketReviewVisible.value = true
}

async function confirmTicketReview() {
  if (!ticketReviewTarget.value) return
  if (ticketReviewAction.value === 'reject' && !ticketReviewComment.value.trim()) {
    ElMessage.warning('请填写拒绝意见')
    return
  }
  try {
    await approveTicketApi(ticketReviewTarget.value.id, ticketReviewAction.value, ticketReviewComment.value.trim() || undefined)
    ElMessage.success(ticketReviewAction.value === 'approve' ? '已通过' : '已拒绝')
    ticketReviewVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

onMounted(() => {
  // 闭环：解析学生成长档案传来的聚焦参数
  const sid = Number(route.query.student_id)
  const sname = route.query.student_name ? String(route.query.student_name) : ''
  if (sid || sname) studentFilter.value = { id: sid || 0, name: sname }
  void loadAllCounts()
  loadData()
})

// keep-alive 缓存本页：再次激活时静默重拉审批列表与角标数，首次激活由 onMounted 负责。
let firstActivate = true
onActivated(() => {
  if (firstActivate) { firstActivate = false; return }
  void loadAllCounts()
  loadData()
})

/**
 * 页签切换后加载对应数据。
 *
 * 原来用模板上的 @update:model-value="() => loadData()"：TuiSegmented 先 emit，
 * 父组件此时 activeTab 仍是【旧值】，loadData() 于是按旧页签又拉了一遍，
 * 表现为「点了没反应，要再点一次才更新」。
 * 改用 watch：回调在 activeTab 已经变更之后执行，读到的就是新页签。
 */
watch(activeTab, () => { void loadData() })
watch(ticketScope, () => { void loadData() })
</script>

<style scoped>
.tui-page.pull-enabled { overscroll-behavior-y: contain; }
/* ========== 卡片（对齐 tui 规范：白卡 + 发丝边 + 弱阴影） ========== */
.section-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  padding: 12px 13px;
  margin-bottom: 10px;
}

/* 待处理总览数字语义色（用双类名提高优先级，避免被 .tui-stat-num 覆盖） */
.tui-stat-num.ap-warn { color: var(--tui-warn); }

/* ========== 待办总览：可点击卡片（点击直达对应分区） ========== */
.ap-stat {
  position: relative;
  cursor: pointer;
}
/* 纯 CSS 绘制的引导箭头，避免混用图标语言 */
.ap-stat::after {
  content: '';
  position: absolute;
  right: 12px;
  top: 15px;
  width: 6px;
  height: 6px;
  border-right: 1.5px solid #c7ccd4;
  border-bottom: 1.5px solid #c7ccd4;
  transform: rotate(-45deg);
}
.ap-stat:hover { border-color: #d3ddf5; }
.ap-stat.is-active {
  border-color: var(--tui-brand);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

/* 办理说明条 */
.ap-rule { margin-bottom: 10px; }
.ap-rule b { font-weight: 600; }

/* 审批生命周期链路：横向四步，移动端由 .tui-steps.h 自动转为纵向 */
.ap-lifecycle {
  padding: 12px 14px;
  margin-bottom: 12px;
  border-radius: var(--tui-radius);
  background: var(--tui-surface);
  box-shadow: var(--tui-shadow-1);
}

/* ========== 办事申请：申请人 / 事项 / 附件 / 时间 ========== */
.ap-applicant { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.ap-applicant-name { font-size: 13px; font-weight: 600; color: var(--tui-text); }
.ap-applicant-no { font-size: 11.5px; color: var(--tui-text-quiet); }

.ap-ticket-title { font-size: 13px; font-weight: 500; color: var(--tui-text); line-height: 1.4; }
.ap-ticket-sub {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin-top: 3px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: normal;
}

.ap-attach {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--tui-brand-strong);
}
.ap-muted { font-size: 12px; color: var(--tui-text-quiet); }
.ap-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--tui-text-tertiary);
}

/* ========== 弹窗：上下文提示（让人知道「正在处理谁的事」） ========== */
.ap-dialog-context {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 8px 10px;
  margin-bottom: 12px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  font-size: 12px;
  line-height: 1.55;
  color: var(--tui-text-secondary);
}
.ap-dialog-context :deep(.el-icon) {
  flex-shrink: 0;
  margin-top: 1px;
  font-size: 13px;
  color: var(--tui-text-tertiary);
}

/* ========== 办事申请详情 ========== */
.ap-detail { display: flex; flex-direction: column; gap: 12px; }
.ap-detail-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ap-detail-who { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.ap-detail-name { font-size: 15px; font-weight: 700; color: var(--tui-text); }
.ap-detail-meta { font-size: 11.5px; color: var(--tui-text-quiet); }
.ap-detail-tags { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.ap-detail-desc { border-radius: 10px; overflow: hidden; }
.ap-detail-block { border-top: 1px solid var(--tui-border); padding-top: 10px; }
/* 请假详情里的结论色：通过 / 拒绝 */
.ap-ok { color: #0f8e6b; font-weight: 600; }
.ap-bad { color: #d63a4f; font-weight: 600; }
.ap-detail-block-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
.ap-detail-files { display: flex; flex-direction: column; gap: 6px; }
.ap-detail-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  background: var(--tui-surface-muted);
  color: var(--tui-brand-strong);
  font-size: 12.5px;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap-detail-file:hover { background: var(--tui-brand-soft); }

/* 闭环聚焦条：从学生成长档案跳来时的上下文提示 */
.ap-focus {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  margin-bottom: 12px;
  border-radius: var(--tui-radius-sm);
  background: #eff4ff;
  border: 1px solid #d3e0fb;
  color: #1d4ed8;
  font-size: 12.5px;
}
.ap-focus-text { flex: 1; min-width: 0; font-weight: 500; }
.ap-focus-clear {
  flex-shrink: 0;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #1d4ed8;
  cursor: pointer;
}
.ap-focus-clear:hover { text-decoration: underline; }

.section-header {
  display: flex; align-items: center; gap: 7px;
  margin-bottom: 10px;
}
.section-header h3 {
  font-size: 13.5px; font-weight: 600; color: var(--tui-text); margin: 0;
  display: flex; align-items: center; gap: 5px;
}
.section-header h3 :deep(.el-icon) { font-size: 15px; color: var(--tui-text-tertiary); }
.section-header > :deep(.el-tag) { margin-left: auto; }

/* 桌面表格：轻量表头 + 圆角 */
.section-card :deep(.el-table) { border-radius: var(--tui-radius-sm); }
.section-card :deep(.el-table th.el-table__cell) { background: #f8f9fb !important; }

.ai-analyze { display: flex; align-items: center; gap: 6px; }
.analyze-tip { cursor: pointer; color: var(--tui-text-tertiary); font-size: 13px; }
.analyze-tip:hover { color: var(--tui-brand); }
.analyzing-tag { display: inline-flex; align-items: center; gap: 4px; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  padding: 8px 0;
}

/* ========== 统计 Tab ========== */
.stat-box {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 13px 14px;
  border-radius: var(--tui-radius);
  background: var(--tui-surface-muted);
  border: 1px solid var(--tui-border);
}
.stat-num {
  font-size: var(--tui-fs-num); font-weight: 700; color: var(--tui-text);
  line-height: 1.1; font-variant-numeric: tabular-nums;
}
.stat-num.ok { color: var(--tui-success); }
.stat-num.warn { color: #f79009; }
.stat-num.danger { color: var(--tui-danger); }
.stat-num.purple { color: #6941c6; }
.stat-label { font-size: 11.5px; color: var(--tui-text-quiet); }

.stat-rows { display: flex; flex-direction: column; gap: 16px; }
.stat-row-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 6px;
}
.stat-row-label { font-size: 13px; font-weight: 600; color: #344054; }
.stat-row-total { font-size: 12px; color: #98a2b3; }

.stat-bar {
  display: flex;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #f2f4f7;
}
.stat-bar-seg { height: 100%; }
.seg-approved { background: #10b981; }
.seg-pending { background: #f59e0b; }
.seg-rejected { background: #ef4444; }

.stat-legend {
  display: flex;
  gap: 14px;
  margin-top: 7px;
  font-size: 11.5px;
  color: #667085;
}
.stat-legend .dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-right: 4px;
}
.dot-approved { background: #10b981; }
.dot-pending { background: #f59e0b; }
.dot-rejected { background: #ef4444; }

/* ========== 移动端卡片（对齐 tui 规范：白卡 + 发丝边 + 去边框感）
   叠层切换由 ApprovalCardStack 组件负责，这里只管单张卡片的样式 ========== */
.mobile-card {
  display: flex;
  flex-direction: column;
  padding: 14px 15px;
  border-radius: var(--tui-radius);
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  box-shadow: var(--tui-shadow-1);
}

/* ========== 桌面端概览带：审批链路 + 学生聚焦条拼成 hero 之下的一条横向带 ========== */
.ap-band {
  display: flex;
  flex-direction: column;
}
/* 带内的聚焦条紧贴链路，收掉链路的下外边距避免出现双份留白 */
.ap-band .ap-lifecycle { margin-bottom: 10px; }
.ap-band .ap-focus { margin-bottom: 12px; }

/* ========== 桌面端类别 Tab：横向分段，激活项用品牌色底 + 底部细线强调 ========== */
.ap-cats {
  display: flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 12px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  overflow-x: auto;
  scrollbar-width: none;
}
.ap-cats::-webkit-scrollbar { display: none; width: 0; height: 0; }

.ap-cat {
  position: relative;
  flex: 1 1 0;
  min-width: 132px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 12px 11px;
  border: none;
  border-radius: var(--tui-radius-xs);
  background: transparent;
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), color 0.15s var(--tui-ease);
}
.ap-cat:hover { background: var(--tui-surface-muted); color: var(--tui-text); }
.ap-cat.is-active {
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-weight: 600;
}
/* 纯 CSS 底部细线做激活标记，避免额外图标语言 */
.ap-cat::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 3px;
  width: 0;
  height: 2px;
  border-radius: 999px;
  background: var(--tui-brand);
  transform: translateX(-50%);
  transition: width 0.18s var(--tui-ease);
}
.ap-cat.is-active::after { width: 26px; }
.ap-cat-count {
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-tertiary);
}
.ap-cat.is-active .ap-cat-count { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }

/* ========== 桌面端待办卡片网格：等宽卡片自适应填充 ========== */
.ap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
}
/* 卡片顶部一条语义色细线做类别强调：请假=品牌蓝 / 办事=琥珀 / 材料=绿 */
.ap-grid-leave { --ap-accent: var(--tui-brand); }
.ap-grid-ticket { --ap-accent: #f79009; }
.ap-grid-material { --ap-accent: var(--tui-success); }

.ap-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 13px 13px 11px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  box-shadow: var(--tui-shadow-1);
  transition: border-color 0.15s var(--tui-ease), box-shadow 0.15s var(--tui-ease);
}
.ap-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  border-radius: var(--tui-radius-sm) var(--tui-radius-sm) 0 0;
  background: var(--ap-accent, var(--tui-brand));
}
.ap-card:hover {
  border-color: var(--tui-border-strong);
  box-shadow: var(--tui-shadow-2);
}

.ap-card-head { display: flex; align-items: center; gap: 8px; }
.ap-card-head > :deep(.el-tag) { margin-left: auto; flex-shrink: 0; }
.ap-card-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap-card-sub { font-size: 11.5px; color: var(--tui-text-quiet); }
.ap-card-title { font-size: 13px; font-weight: 500; color: var(--tui-text); line-height: 1.45; }
.ap-card-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ap-card-kv {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text-secondary);
}
.ap-card-kv :deep(.el-icon) { font-size: 12px; color: var(--tui-text-quiet); }
.ap-card-reason {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--tui-text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ap-card-ai { display: flex; align-items: center; min-height: 20px; }
.ap-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 9px;
  border-top: 1px solid var(--tui-hairline);
}
/* Element Plus 会给相邻按钮加左外边距，这里统一改由 gap 控制间距 */
.ap-card-actions :deep(.el-button + .el-button) { margin-left: 0; }

/* ========== 办事工单视图切换（共享队列 / 我受理的）========== */
.ap-ticket-scope { margin-bottom: 10px; }

/* ========== 移动端响应式 ========== */
@media (max-width: 767px) {
  .section-card {
    padding: 13px 14px;
    margin-bottom: 10px;
  }

  /* 隐藏桌面表格，显示移动端卡片 */
  .desktop-table { display: none; }

  .mobile-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .mobile-card-student {
    font-size: 15px;
    font-weight: 600;
    color: var(--tui-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-card-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 10px;
  }

  .mobile-card-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 13px;
    line-height: 1.5;
  }

  .mobile-card-label {
    flex-shrink: 0;
    width: 56px;
    color: var(--tui-text-quiet);
    font-weight: 500;
  }

  .mobile-card-value {
    flex: 1;
    min-width: 0;
    color: var(--tui-text-secondary);
    word-break: break-word;
  }

  .mobile-card-reason {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .mobile-ai-reason {
    display: block;
    font-size: 12px;
    color: var(--tui-text-quiet);
    margin-top: 4px;
    line-height: 1.45;
  }

  .mobile-card-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--tui-border);
  }

  .mobile-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--tui-border);
  }

  .stat-box { padding: 11px 12px; }
  .stat-num { font-size: 18px; }

  /* 分页居中 */
  .pagination-wrapper {
    justify-content: center;
  }

  .pagination-wrapper :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }

  .mobile-card-actions :deep(.el-button) { flex: 1; }

  /* 弹窗：保持水平 + 垂直居中
     原实现用 position:fixed + bottom:0 把弹窗改成贴底抽屉，导致视觉上「不居中」且过宽；
     现只收窄宽度与圆角，居中交给全局 flex + auto 外边距处理。 */
  :deep(.el-dialog) {
    width: min(90vw, 400px) !important;
    max-height: 66vh;
    max-height: 66dvh;
    margin: auto !important;
    border-radius: 14px !important;
  }

  :deep(.el-dialog__body) {
    overflow-y: auto;
  }
}
</style>

<style scoped>
/* ================= 票据卡 + AI 辅助审批（移动端） ================= */
.ap-ticket { display: flex; flex-direction: column; overflow: hidden; }
.ap-ticket-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: -14px -14px 10px;
  padding: 9px 14px;
  background: var(--tui-brand-soft, #eff4ff);
  color: var(--tui-brand-strong, #1d4ed8);
  font-size: 12px;
  font-weight: 600;
}
.ap-ticket-type { margin-left: auto; }
.ap-ticket-no { margin-left: auto; font-size: 11px; color: var(--tui-text-quiet, #98a2b3); font-variant-numeric: tabular-nums; }

.ap-ai {
  background: linear-gradient(160deg, #f4f3ff, #fbfaff);
  border: 1px solid #ded9f8;
  border-radius: 14px;
  padding: 12px 13px;
  margin-top: 10px;
}
.ap-ai-head { display: flex; align-items: center; gap: 9px; }
.ap-ai-ic {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: #7f56d9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ap-ai-title { font-size: 13px; font-weight: 700; color: #3b2c72; }
.ap-ai-sub { font-size: 10.5px; color: var(--tui-text-tertiary, #98a2b3); margin-top: 1px; }
.ap-ai-verdict { margin-left: auto; flex-shrink: 0; }
.ap-ai-body { margin-top: 10px; border-top: 1px dashed #ded9f8; padding-top: 10px; }
.ap-ai-reason { margin: 0; font-size: 12px; color: #475467; line-height: 1.65; }
.ap-ai-adopt { margin-top: 10px; }
.ap-ai-adopt-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  width: 100%;
  justify-content: center;
  border: none;
  border-radius: 10px;
  padding: 9px 0;
  font-size: 12.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  color: #fff;
  background: #7f56d9;
}
.ap-ai-adopt-btn.is-approve { background: var(--tui-success, #079455); }
.ap-ai-adopt-btn.is-reject { background: var(--tui-danger, #d92d20); }
.ap-ai-adopt-btn:active { opacity: 0.85; }
.ap-ticket-actions { margin-top: auto; padding-top: 12px; }
.ap-ticket-actions .el-button { flex: 1; }

/* ================= 移动端多级入口（一类事项一层） ================= */
.ap-drill-list { display: flex; flex-direction: column; gap: 8px; margin: 0 14px 10px; }
.ap-drill {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 13px;
  background: #fff;
  border: 1px solid var(--tm-line, #e8eaef);
  border-radius: 14px;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.ap-drill:active { background: #f7f8fa; }
.ap-drill-ic {
  width: 36px; height: 36px; flex: 0 0 36px;
  border-radius: 11px;
  display: grid; place-items: center;
}
.ap-drill-ic-leave { background: #eef3ff; color: #3563c9; }
.ap-drill-ic-ticket { background: #eef8f1; color: #2b7b4f; }
.ap-drill-ic-material { background: #fdf4e8; color: #9a6416; }
.ap-drill-bd { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ap-drill-bd b { font-size: 14px; font-weight: 700; color: var(--tm-ink, #171a20); }
.ap-drill-bd em { font-style: normal; font-size: 11.5px; color: var(--tm-ink3, #8a91a0); }
.ap-drill-arrow { color: #b8bfcc; }

/* ================= 二级子页外壳：整屏右滑，独立子页头 + 独立滚动区 ================= */
.ap-sub {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  flex-direction: column;
  background: var(--tm-bg, #f3f5f9);
}
.ap-sub-shell {
  width: 100%;
  max-width: 480px;
  height: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  background: var(--tm-bg, #f3f5f9);
}
.ap-subbar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 56px;
  padding: calc(env(safe-area-inset-top) + 6px) 12px 8px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
}
.ap-subbar-back {
  width: 34px; height: 34px; flex: 0 0 34px;
  display: grid; place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #1f2430;
  cursor: pointer;
}
.ap-subbar-back:active { background: rgba(20, 23, 26, 0.06); }
.ap-subbar-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ap-subbar-main b {
  font-size: 16.5px;
  font-weight: 700;
  color: #171a20;
  letter-spacing: -0.2px;
}

.ap-subbar-badge {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 8px;
  background: #e7efff;
  color: #1b4fd1;
  font-size: 11.5px;
  font-weight: 650;
}
/* 队列为空时退回中性灰，避免 0 条也抢注意力 */
.ap-subbar-badge.is-zero {
  background: #f3f4f7;
  color: #78849a;
}
.ap-sub-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 12px 0 calc(18px + env(safe-area-inset-bottom));
}
.ap-sub-pane { display: flex; flex-direction: column; gap: 10px; }
.ap-sub-pane .ap-ticket-scope { margin: 0 14px; }
.ap-sub-pane .tm-empty { margin: 0 14px; background: #fff; border-radius: 14px; }

/* ================= 二级页：开源风格扁平列表（少卡片、多信息密度） ================= */
.ap2-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 14px;
  background: transparent;
  border: 0;
  border-radius: 0;
  overflow: visible;
}
/* 每条事项独立成卡并留出 8px 间隔，展开区仍跟随所属卡片 */
.ap2-item {
  background: #fff;
  border: 1px solid var(--tm-line, #e8eaef);
  border-radius: 14px;
  overflow: hidden;
}
.ap2-list > .ap2-row {
  background: #fff;
  border: 1px solid var(--tm-line, #e8eaef);
  border-radius: 14px;
}
.ap2-item > .ap2-row { border: 0; border-radius: 0; }
.ap2-item + .ap2-item { border-top: 1px solid var(--tm-line, #e8eaef); }
.ap2-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 13px 12px;
  background: #fff;
  border: 0;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.ap2-row:active { background: #f8f9fb; }
.ap2-row-static { cursor: default; }
.ap2-avatar {
  width: 34px; height: 34px; flex: 0 0 34px;
  border-radius: 50%;
  display: grid; place-items: center;
  background: #f1f3f7;
  color: #3a4252;
  font-size: 14px;
  font-weight: 700;
}
.ap2-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ap2-title {
  font-size: 14.5px;
  font-weight: 650;
  color: #171a20;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap2-sub {
  font-size: 12.5px;
  color: #8a91a0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ap2-ellipsis { display: block; }
.ap2-status {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 6px;
  background: #f3f4f7;
  color: #5f6878;
  font-size: 11.5px;
  font-weight: 600;
}
.ap2-status.is-todo { background: #fff4e6; color: #a35a0a; }
/* AI 分析结论：通过=绿、需判断=琥珀、分析中=中性，避免结论与普通状态混淆 */
.ap2-status.tm-ok { background: #e4f6f0; color: #0f8e6b; }
.ap2-status.tm-warn { background: #fdf3e2; color: #b54708; }
.ap2-status.tm-mute { background: #f3f4f7; color: #78849a; }
.ap2-arrow { color: #b8bfcc; flex: 0 0 auto; }
.ap2-chevron { color: #b8bfcc; flex: 0 0 auto; transition: transform 0.18s ease; }
.ap2-chevron.open { transform: rotate(180deg); }
.ap2-expand {
  padding: 2px 12px 12px;
  background: #fafbfc;
  border-top: 1px dashed #eef1f5;
}
.ap2-kv {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  font-size: 12.5px;
  line-height: 1.55;
  color: #6b7280;
}
.ap2-kv b { flex: 0 0 28px; font-size: 11.5px; font-weight: 700; color: #9aa1ad; }
.ap2-kv span { flex: 1; }
.ap2-kv-advice span,
.ap2-kv-advice b { color: #1f2430; }
.ap2-actions { display: flex; gap: 8px; margin-top: 10px; }
.ap2-actions-inline { margin: 0; padding: 0 12px 12px; }
.ap2-btn {
  padding: 6px 13px;
  border: 1px solid #dde2ea;
  border-radius: 9px;
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 650;
  color: #3a4252;
  cursor: pointer;
}
.ap2-btn-main { border-color: #1f2430; background: #1f2430; color: #fff; }
.ap2-reasons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 11.5px;
  color: #9aa1ad;
}
.ap2-reasons button {
  padding: 3px 8px;
  border: 1px solid #e4e7ec;
  border-radius: 999px;
  background: #fff;
  font-family: inherit;
  font-size: 11.5px;
  color: #5f6878;
  cursor: pointer;
}

/* ================= 收件箱式审批（2026-11 改版） ================= */
/* 桌面标题条：只保留页面身份与待办规模 */
.apm-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 2px 14px;
}
.apm-head h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -.2px;
  color: var(--tui-text);
}
.apm-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.apm-head-total {
  flex: none;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.apm-head-total b {
  margin-right: 2px;
  font-size: 16px;
  font-weight: 700;
  color: #c4700e;
}

/* 移动端一句汇总 */
.apm-page { padding-bottom: 6px; }
.apm-sum {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 0 2px 12px;
}
.apm-sum b {
  font-size: 26px;
  font-weight: 750;
  line-height: 1;
  letter-spacing: -.5px;
  color: #101725;
  font-variant-numeric: tabular-nums;
}
.apm-sum span { font-size: 12.5px; color: #3d4a5e; }
.apm-sum .sp { flex: 1; }
.apm-sum .apm-sum-meta { font-size: 10.5px; color: #78849a; }

/* 类型筛选 */
.apm-filters {
  display: flex;
  gap: 7px;
  overflow-x: auto;
  padding: 0 0 11px;
  scrollbar-width: none;
}
.apm-filters::-webkit-scrollbar { display: none; }
.apm-filter {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: none;
  height: 28px;
  padding: 0 11px;
  border: 1px solid #e3e9f3;
  border-radius: 999px;
  background: #fff;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #78849a;
  cursor: pointer;
}
.apm-filter i { font-style: normal; font-size: 10px; color: #9aa6b8; }
.apm-filter.is-on { background: #101725; border-color: #101725; color: #fff; }
.apm-filter.is-on i { color: rgba(255, 255, 255, .7); }

/* 分组标题 */
.apm-group-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 3px 7px;
}
.apm-group-hd span { font-size: 11.5px; font-weight: 700; color: #3d4a5e; }
.apm-group-hd em { font-style: normal; font-size: 10.5px; color: #9aa6b8; }

/* 请假条 */
.apm-leave {
  margin-bottom: 9px;
  padding: 12px 12px 11px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 17, 21, .04), 0 3px 10px rgba(15, 17, 21, .04);
}
.apm-leave-hd { display: flex; align-items: center; gap: 9px; }
.apm-av {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1;
}
.apm-who { flex: 1; min-width: 0; }
.apm-who b {
  display: block;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
  color: #101725;
}
.apm-who span { display: block; margin-top: 2px; font-size: 10.5px; color: #78849a; }
.apm-wait {
  flex: none;
  padding: 3px 7px;
  border-radius: 6px;
  background: #eef1f6;
  font-size: 10px;
  font-weight: 600;
  color: #78849a;
}
.apm-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 9px;
  font-size: 11px;
  color: #3d4a5e;
}
.apm-meta .el-icon { color: #9aa6b8; }
.apm-desc {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 5px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: #78849a;
}
.apm-ft {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid #f0f3f8;
}
.apm-ai {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 10.5px;
}
.apm-ai em {
  font-style: normal;
  color: #78849a;
  overflow: hidden;
  text-overflow: ellipsis;
}
.apm-ai.tm-ok { color: #0f8e6b; }
.apm-ai.tm-warn { color: #c4700e; }
.apm-ai.tm-mute { color: #9aa6b8; }
.apm-ops { display: flex; gap: 6px; flex: none; }
.apm-btn {
  height: 28px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #eef1f6;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #3d4a5e;
  cursor: pointer;
}
.apm-btn-ghost { background: #fff; border-color: #f6cfd6; color: #d63a4f; }
.apm-btn-ok { background: #0f8e6b; color: #fff; }
.apm-btn-sm { height: 30px; }

/* 办事 / 材料行 */
.apm-row {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 9px;
  padding: 11px 12px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 17, 21, .04), 0 3px 10px rgba(15, 17, 21, .04);
}
.apm-row-main {
  flex: 1;
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  font-family: inherit;
  text-align: left;
}
.apm-row-main b {
  display: block;
  font-size: 13px;
  font-weight: 650;
  color: #101725;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.apm-row-main span {
  display: block;
  margin-top: 3px;
  font-size: 10.5px;
  color: #78849a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.apm-mini {
  flex: none;
  height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: #eef1f6;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #3d4a5e;
  cursor: pointer;
}
.apm-mini-ok { background: #0f8e6b; color: #fff; }
.apm-room-ops { display: flex; gap: 5px; flex: none; }

/* 已通过 / 已拒绝台账（移动端） */
.apm-ledger { display: flex; flex-direction: column; gap: 9px; }
.apm-ledger-card {
  padding: 12px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 17, 21, .04), 0 3px 10px rgba(15, 17, 21, .04);
}
.apm-ledger-hd { display: flex; align-items: center; gap: 8px; }
.apm-ledger-hd b { font-size: 13.5px; font-weight: 700; color: #101725; }
.apm-ledger-hd .apm-tag {
  padding: 2px 7px;
  border-radius: 6px;
  background: #eef1f6;
  font-size: 10px;
  color: #5b6b85;
}
.apm-ledger-hd time { margin-left: auto; font-size: 10px; color: #9aa6b8; }
.apm-ledger-title { margin-top: 7px; font-size: 12px; line-height: 1.5; color: #3d4a5e; }
.apm-ledger-sub { margin-top: 3px; font-size: 11px; line-height: 1.5; color: #78849a; }
.apm-ledger-note {
  margin-top: 7px;
  padding: 7px 9px;
  border: 1px solid #f6cfd6;
  border-radius: 8px;
  background: #fdecef;
  font-size: 10.5px;
  line-height: 1.5;
  color: #a8283a;
}
.apm-ledger-note b { margin-right: 4px; font-weight: 650; }
.apm-ledger-ft {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid #f2f5f9;
}
/* 尾部操作靠右：由状态胶囊吃剩余空间，右侧按钮成组紧贴右边。
   注意不要给「每个」.apm-btn/.apm-mini 都加 margin-left:auto ——
   那样每个按钮各自被推一次，第一个按钮会跑到中间。 */
.apm-ledger-ft .apm-status { margin-right: auto; }
.apm-status {
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef1f6;
  font-size: 10.5px;
  font-weight: 600;
  color: #5b6b85;
}
.apm-status.is-success { background: #e4f6f0; color: #0f8e6b; }
.apm-status.is-warning { background: #fdf3e2; color: #c4700e; }
.apm-status.is-danger { background: #fdecef; color: #d63a4f; }
.apm-none {
  padding: 22px 0;
  text-align: center;
  font-size: 11.5px;
  color: #9aa6b8;
}
/* 桌面端状态切换与办事队列切换不做整行拉伸 */
@media (min-width: 768px) {
  .ap-status-tabs { max-width: 560px; margin-bottom: 16px; }
}
.ap-ticket-scope { max-width: 280px; }
/* 移动端台账不再套一层大卡片，避免「卡片里再叠卡片」 */
.apm-flat {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}
</style>
