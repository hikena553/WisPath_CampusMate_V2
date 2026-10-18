﻿<template>
  <div class="tui-page">
    <SubPageHeader title="审批管理" :sub="totalPending + ' 条待处理'" fallback="/teacher">
      <template #right>
        <el-button text circle aria-label="刷新" @click="loadData()">
          <el-icon :size="19"><Refresh /></el-icon>
        </el-button>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <!-- 桌面端特色头部：待办语义色（琥珀）+ 印章图标。
           本页已有「待处理总览」四宫格作为导航型指标区，头部不再重复挂数字，
           只承担页面身份与刷新入口。 -->
      <TuiPageHero
        v-if="!isMobile"
        title="审批管理"
        sub="请假、办事、材料一站式处理，按办理链路推进"
        :icon="Stamp"
        tone="warn"
      >
        <el-button text circle aria-label="刷新" @click="loadData()">
          <el-icon :size="18"><Refresh /></el-icon>
        </el-button>
      </TuiPageHero>

      <!-- 桌面端概览带：把「审批链路 + 学生聚焦条」提到 hero 之下、类别 Tab 之上，
           作为进入具体待办前的一条横向概览——先看流程走到哪一步、当前聚焦的是谁，
           再决定去处理哪一类待办。移动端仍沿用下方原位节点，不受影响。 -->
      <div v-if="!isMobile" class="ap-band">
        <ol class="tui-steps h ap-lifecycle">
          <li class="tui-step is-done">
            <span class="tui-step-dot"><el-icon :size="11"><Check /></el-icon></span>
            <span class="tui-step-line" />
            <div class="tui-step-body">
              <div class="tui-step-title">提交</div>
              <div class="tui-step-desc">学生发起请假 / 办事申请</div>
            </div>
          </li>
          <li class="tui-step is-done">
            <span class="tui-step-dot"><el-icon :size="11"><Check /></el-icon></span>
            <span class="tui-step-line" />
            <div class="tui-step-body">
              <div class="tui-step-title">受理</div>
              <div class="tui-step-desc">自动归类到请假 / 办事 / 材料</div>
            </div>
          </li>
          <li class="tui-step" :class="totalPending ? 'is-current' : 'is-done'">
            <span class="tui-step-dot">
              <el-icon v-if="!totalPending" :size="11"><Check /></el-icon>
              <template v-else>3</template>
            </span>
            <span class="tui-step-line" />
            <div class="tui-step-body">
              <div class="tui-step-title">审批</div>
              <div class="tui-step-desc">{{ totalPending ? `当前待处理 ${totalPending} 条` : '已全部处理完毕' }}</div>
            </div>
          </li>
          <li class="tui-step" :class="totalPending ? 'is-todo' : 'is-done'">
            <span class="tui-step-dot">
              <el-icon v-if="!totalPending" :size="11"><Check /></el-icon>
              <template v-else>4</template>
            </span>
            <span class="tui-step-line" />
            <div class="tui-step-body">
              <div class="tui-step-title">归档</div>
              <div class="tui-step-desc">结果即时推送并留痕</div>
            </div>
          </li>
        </ol>

        <div v-if="studentFilter" class="ap-focus">
          <el-icon :size="14"><User /></el-icon>
          <span class="ap-focus-text">已聚焦学生「{{ studentFilter.name || '该生' }}」，仅显示其审批事项</span>
          <button class="ap-focus-clear" type="button" @click="clearStudentFilter">清除聚焦</button>
        </div>
      </div>

      <!-- 桌面端类别 Tab：沿用原「待处理总览」的 anchor + jumpTo() 分段逻辑，
           点击即切到待审批并滚动定位到对应类别的卡片网格，避免长页面里来回找分区 -->
      <div v-if="!isMobile" class="ap-cats" role="tablist">
        <button
          v-for="c in categoryTabs"
          :key="c.id || 'all'"
          type="button"
          role="tab"
          class="ap-cat"
          :class="{ 'is-active': anchor === c.id }"
          :aria-selected="anchor === c.id"
          @click="jumpTo(c.id)"
        >
          <span class="ap-cat-label">{{ c.label }}</span>
          <span class="ap-cat-count">{{ c.count }}</span>
        </button>
      </div>

      <!-- 待处理总览：点击卡片直达对应分区 -->
      <div class="tui-stat-row cols-4 ap-overview">
        <button class="tui-stat ap-stat" type="button" :class="{ 'is-active': anchor === '' }" @click="jumpTo('')">
          <span class="tui-stat-num">{{ totalPending }}</span>
          <span class="tui-stat-label">待处理合计</span>
        </button>
        <button class="tui-stat ap-stat" type="button" :class="{ 'is-active': anchor === 'ap-sec-leave' }" @click="jumpTo('ap-sec-leave')">
          <span class="tui-stat-num ap-warn">{{ pendingLeaves.length }}</span>
          <span class="tui-stat-label">请假待批</span>
        </button>
        <button class="tui-stat ap-stat" type="button" :class="{ 'is-active': anchor === 'ap-sec-ticket' }" @click="jumpTo('ap-sec-ticket')">
          <span class="tui-stat-num ap-warn">{{ pendingTickets.length }}</span>
          <span class="tui-stat-label">办事待批</span>
        </button>
        <button class="tui-stat ap-stat" type="button" :class="{ 'is-active': anchor === 'ap-sec-material' }" @click="jumpTo('ap-sec-material')">
          <span class="tui-stat-num ap-warn">{{ pendingMaterials.length }}</span>
          <span class="tui-stat-label">材料待归档</span>
        </button>
      </div>

      <!-- 办理说明：一眼看懂优先级与规则（原页面缺失的引导） -->
      <div class="tui-section-hint warn ap-rule">
        <el-icon><InfoFilled /></el-icon>
        <span>建议办理顺序：<b>请假</b>（需 24 小时内响应，直接影响考勤销假）→ <b>办事</b>（证明 / 项目 / 反馈类，通过后由对应科室出证）→ <b>材料</b>（归档类，可批量处理）。任一项拒绝都须填写理由，系统会即时推送学生。</span>
      </div>

      <!-- 链路（移动端原位保留）：一条申请从提交到归档的全流程，当前阶段由待处理量实时点亮 -->
      <ol v-if="isMobile" class="tui-steps h ap-lifecycle">
        <li class="tui-step is-done">
          <span class="tui-step-dot"><el-icon :size="11"><Check /></el-icon></span>
          <span class="tui-step-line" />
          <div class="tui-step-body">
            <div class="tui-step-title">提交</div>
            <div class="tui-step-desc">学生发起请假 / 办事申请</div>
          </div>
        </li>
        <li class="tui-step is-done">
          <span class="tui-step-dot"><el-icon :size="11"><Check /></el-icon></span>
          <span class="tui-step-line" />
          <div class="tui-step-body">
            <div class="tui-step-title">受理</div>
            <div class="tui-step-desc">自动归类到请假 / 办事 / 材料</div>
          </div>
        </li>
        <li class="tui-step" :class="totalPending ? 'is-current' : 'is-done'">
          <span class="tui-step-dot">
            <el-icon v-if="!totalPending" :size="11"><Check /></el-icon>
            <template v-else>3</template>
          </span>
          <span class="tui-step-line" />
          <div class="tui-step-body">
            <div class="tui-step-title">审批</div>
            <div class="tui-step-desc">{{ totalPending ? `当前待处理 ${totalPending} 条` : '已全部处理完毕' }}</div>
          </div>
        </li>
        <li class="tui-step" :class="totalPending ? 'is-todo' : 'is-done'">
          <span class="tui-step-dot">
            <el-icon v-if="!totalPending" :size="11"><Check /></el-icon>
            <template v-else>4</template>
          </span>
          <span class="tui-step-line" />
          <div class="tui-step-body">
            <div class="tui-step-title">归档</div>
            <div class="tui-step-desc">结果即时推送并留痕</div>
          </div>
        </li>
      </ol>

      <!-- 闭环（移动端原位保留）：从学生成长档案聚焦该生审批事项 -->
      <div v-if="isMobile && studentFilter" class="ap-focus">
        <el-icon :size="14"><User /></el-icon>
        <span class="ap-focus-text">已聚焦学生「{{ studentFilter.name || '该生' }}」，仅显示其审批事项</span>
        <button class="ap-focus-clear" type="button" @click="clearStudentFilter">清除聚焦</button>
      </div>

      <TuiSegmented
        v-model="activeTab"
        class="tui-seg-wrap"
        :options="tabOptions"
        @update:model-value="() => loadData()"
      />

      <template v-if="activeTab === 'pending'">
        <div id="ap-sec-leave" class="section-card">
          <div class="section-header">
            <h3><el-icon><Document /></el-icon> 请假申请</h3>
            <el-tag v-if="pendingLeaves.length" type="warning" effect="light" size="small">
              {{ pendingLeaves.length }} 条待批
            </el-tag>
            <el-tag v-else type="success" effect="light" size="small">已处理完</el-tag>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>通过后学生考勤自动销假；「AI 分析」是基于出勤率与历史请假给出的建议，点 ⓘ 可查看判断依据，仅供参考。</span>
          </div>
          <!-- 桌面端卡片网格：等宽卡片（min 300px）自适应填充，替代原表格 —— 待办是「逐条决策」场景，
               卡片比表格更适合承载 事由 + AI 建议 + 操作 三块信息 -->
          <div v-if="!isMobile && paginatedPendingLeaves.length" class="ap-grid ap-grid-leave">
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
                <div v-if="analysisMap[row.id]" class="ai-analyze">
                  <el-tag :type="analysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                    {{ analysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                  </el-tag>
                  <el-tooltip placement="top" :show-after="200">
                    <template #content>
                      <div style="max-width:280px;line-height:1.6;font-size:13px">{{ analysisMap[row.id].reason }}</div>
                    </template>
                    <el-icon class="analyze-tip"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <el-tag v-else type="info" size="small" effect="plain" class="analyzing-tag">
                  <el-icon class="is-loading"><Loading /></el-icon> 分析中
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
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedPendingLeaves.length">
            <div class="mobile-card" v-for="row in paginatedPendingLeaves" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">日期</span>
                  <span class="mobile-card-value">{{ row.start_date }} ~ {{ row.end_date }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reason">
                  <span class="mobile-card-label">原因</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reason }}</span>
                </div>
                <div class="mobile-card-row" v-if="analysisMap[row.id]">
                  <span class="mobile-card-label">AI 分析</span>
                  <span class="mobile-card-value">
                    <el-tag :type="analysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                      {{ analysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                    </el-tag>
                    <span class="mobile-ai-reason">{{ analysisMap[row.id].reason }}</span>
                  </span>
                </div>
                <div class="mobile-card-row" v-else>
                  <span class="mobile-card-label">AI 分析</span>
                  <span class="mobile-card-value">
                    <el-tag type="info" size="small" effect="plain" class="analyzing-tag">
                      <el-icon class="is-loading"><Loading /></el-icon> 分析中
                    </el-tag>
                  </span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button type="success" size="small" @click="handleApprove(row)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="showReject(row)">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </div>
            </div>
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

        <div id="ap-sec-ticket" class="section-card">
          <div class="section-header">
            <h3><el-icon><Tickets /></el-icon> 办事申请</h3>
            <el-tag v-if="pendingTickets.length" type="warning" effect="light" size="small">
              {{ pendingTickets.length }} 条待批
            </el-tag>
            <el-tag v-else type="success" effect="light" size="small">已处理完</el-tag>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>办事申请 = 学生提交的<b>在校 / 在读证明、成绩单、项目立项、反馈</b>等事项。办理前请先点「详情」核对申请人、事由与附件；通过后由对应科室出证，拒绝须写明理由。</span>
          </div>

          <!-- 桌面端卡片网格：申请人 / 事项类型 / 事由 / 附件 / 时间 全部收进单张卡片，
               操作按钮固定在卡片底部，扫读与决策都在视线内完成 -->
          <div v-if="!isMobile && paginatedPendingTickets.length" class="ap-grid ap-grid-ticket">
            <article v-for="row in paginatedPendingTickets" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-name">{{ row.applicant_name || '—' }}</span>
                <el-tag size="small" effect="plain">{{ ticketTypeLabel(row.type) }}</el-tag>
              </div>
              <div class="ap-card-sub">{{ row.applicant_no || row.applicant_college || '' }}</div>
              <div class="ap-card-title">{{ row.title }}</div>
              <div class="ap-card-meta">
                <span class="ap-card-kv"><el-icon><Clock /></el-icon>{{ row.created_at ? row.created_at.slice(5, 16) : '—' }}</span>
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

          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedPendingTickets.length">
            <div class="mobile-card" v-for="row in paginatedPendingTickets" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.title }}</span>
                <el-tag size="small" effect="plain">{{ ticketTypeLabel(row.type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">申请人</span>
                  <span class="mobile-card-value">
                    {{ row.applicant_name || '—' }}<template v-if="row.applicant_no"> · {{ row.applicant_no }}</template>
                  </span>
                </div>
                <div class="mobile-card-row" v-if="row.content">
                  <span class="mobile-card-label">事由</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.content }}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="mobile-card-label">提交</span>
                  <span class="mobile-card-value">{{ row.created_at ? row.created_at.slice(0, 16) : '—' }}</span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button size="small" @click="openTicketDetail(row)"><el-icon><View /></el-icon>详情</el-button>
                <el-button type="success" size="small" @click="showTicketReview(row, 'approve')">通过</el-button>
                <el-button type="danger" size="small" plain @click="showTicketReview(row, 'reject')">拒绝</el-button>
              </div>
            </div>
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

        <!-- 材料档案审批 -->
        <div id="ap-sec-material" class="section-card">
          <div class="section-header">
            <h3><el-icon><FolderOpened /></el-icon> 材料档案</h3>
            <el-tag v-if="pendingMaterials.length" type="warning" effect="light" size="small">
              {{ pendingMaterials.length }} 条待归档
            </el-tag>
            <el-tag v-else type="success" effect="light" size="small">已处理完</el-tag>
          </div>
          <div class="tui-section-hint success">
            <el-icon><InfoFilled /></el-icon>
            <span>材料归档属于「入库」动作：通过即写入学生成长档案并计入统计，驳回需说明原因让学生重新提交，可批量处理。</span>
          </div>
          <!-- 桌面端卡片网格：材料归档信息量小，卡片网格铺满一行即可批量扫读 -->
          <div v-if="!isMobile && pendingMaterials.length" class="ap-grid ap-grid-material">
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
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && pendingMaterials.length">
            <div class="mobile-card" v-for="row in pendingMaterials" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.applicant_name }}</span>
                <el-tag size="small" effect="plain">材料档案</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">材料</span>
                  <span class="mobile-card-value">{{ row.title }}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="mobile-card-label">提交时间</span>
                  <span class="mobile-card-value">{{ row.created_at ? row.created_at.slice(0, 16) : '' }}</span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button type="success" size="small" @click="handleMaterialApprove(row.id)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="handleMaterialReject(row.id)">
                  <el-icon><Close /></el-icon> 驳回
                </el-button>
              </div>
            </div>
          </div>
          <div v-else-if="!pendingMaterials.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><FolderOpened /></el-icon></span>
            <span class="tui-empty-title">暂无待归档材料</span>
            <span class="tui-empty-desc">学生上传材料后会出现在这里，可批量归档</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'approved'">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleCheck /></el-icon> 已通过请假</h3>
            <el-tag v-if="approvedLeaves.length" type="info" effect="light" size="small">{{ approvedLeaves.length }} 条</el-tag>
          </div>
          <div class="tui-section-hint success">
            <el-icon><InfoFilled /></el-icon>
            <span>学生返校后请点「确认返校」完成销假闭环；未及时销假的记录会在统计中计为「待销假」。</span>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedApprovedLeaves" v-if="approvedLeaves.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="student_name" label="学生" width="100" />
              <el-table-column prop="leave_type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_date" label="开始日期" width="110" />
              <el-table-column prop="end_date" label="结束日期" width="110" />
              <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
              <el-table-column label="销假" width="90">
                <template #default="{ row }">
                  <el-tag v-if="row.return_confirmed" type="success" size="small" effect="plain">已销假</el-tag>
                  <el-tag v-else type="warning" size="small" effect="plain">待销假</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button v-if="!row.return_confirmed" type="primary" size="small" @click="handleConfirmReturn(row)">
                    确认返校
                  </el-button>
                  <span v-else class="closed-hint">已闭环</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedApprovedLeaves.length">
            <div class="mobile-card" v-for="row in paginatedApprovedLeaves" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">日期</span>
                  <span class="mobile-card-value">{{ row.start_date }} ~ {{ row.end_date }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reason">
                  <span class="mobile-card-label">原因</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reason }}</span>
                </div>
              </div>
              <div class="mobile-card-footer">
                <el-tag v-if="row.return_confirmed" type="success" size="small" effect="plain">已销假</el-tag>
                <el-tag v-else type="warning" size="small" effect="plain">待销假</el-tag>
                <el-button v-if="!row.return_confirmed" type="primary" size="small" @click="handleConfirmReturn(row)">
                  确认返校
                </el-button>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="approvedLeaves.length > pageSizeApprovedLeaves">
            <el-pagination
              v-model:current-page="currentPageApprovedLeaves"
              v-model:page-size="pageSizeApprovedLeaves"
              :page-sizes="[10, 20, 50]"
              :total="approvedLeaves.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleApprovedLeaveSizeChange"
              @current-change="handleApprovedLeaveCurrentChange"
            />
          </div>
          <div v-else-if="!approvedLeaves.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><CircleCheck /></el-icon></span>
            <span class="tui-empty-title">暂无已通过请假</span>
            <span class="tui-empty-desc">审批通过的请假记录会归档到这里</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'rejected'">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleClose /></el-icon> 已拒绝请假</h3>
            <el-tag v-if="rejectedLeaves.length" type="info" effect="light" size="small">{{ rejectedLeaves.length }} 条</el-tag>
          </div>
          <div class="tui-section-hint danger">
            <el-icon><InfoFilled /></el-icon>
            <span>拒绝记录保留「拒绝理由」并已推送学生；若学生补充材料后可重新提交，不占用本次拒绝次数。</span>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedRejectedLeaves" v-if="rejectedLeaves.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="student_name" label="学生" width="100" />
              <el-table-column prop="leave_type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_date" label="开始日期" width="110" />
              <el-table-column prop="end_date" label="结束日期" width="110" />
              <el-table-column prop="reason" label="原因" min-width="140" show-overflow-tooltip />
              <el-table-column prop="reject_reason" label="拒绝理由" min-width="140" show-overflow-tooltip />
              <el-table-column label="状态" width="90">
                <template #default>
                  <el-tag type="danger" size="small" effect="dark">已拒绝</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedRejectedLeaves.length">
            <div class="mobile-card" v-for="row in paginatedRejectedLeaves" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="mobile-card-label">日期</span>
                  <span class="mobile-card-value">{{ row.start_date }} ~ {{ row.end_date }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reason">
                  <span class="mobile-card-label">原因</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reason }}</span>
                </div>
                <div class="mobile-card-row" v-if="row.reject_reason">
                  <span class="mobile-card-label">拒绝理由</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.reject_reason }}</span>
                </div>
              </div>
              <div class="mobile-card-footer">
                <el-tag type="danger" size="small" effect="dark">已拒绝</el-tag>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="rejectedLeaves.length > pageSizeRejectedLeaves">
            <el-pagination
              v-model:current-page="currentPageRejectedLeaves"
              v-model:page-size="pageSizeRejectedLeaves"
              :page-sizes="[10, 20, 50]"
              :total="rejectedLeaves.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleRejectedLeaveSizeChange"
              @current-change="handleRejectedLeaveCurrentChange"
            />
          </div>
          <div v-else-if="!rejectedLeaves.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="24"><CircleClose /></el-icon></span>
            <span class="tui-empty-title">暂无已拒绝请假</span>
            <span class="tui-empty-desc">被拒绝的请假会连同理由归档到这里</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'stats'">
        <div class="tui-stat-row ap-overview">
          <div class="stat-box">
            <span class="stat-num">{{ leaveStats.total }}</span>
            <span class="stat-label">总申请</span>
          </div>
          <div class="stat-box">
            <span class="stat-num ok">{{ leaveStats.approved }}</span>
            <span class="stat-label">已通过</span>
          </div>
          <div class="stat-box">
            <span class="stat-num warn">{{ leaveStats.pending }}</span>
            <span class="stat-label">待审批</span>
          </div>
          <div class="stat-box">
            <span class="stat-num danger">{{ leaveStats.rejected }}</span>
            <span class="stat-label">已拒绝</span>
          </div>
          <div class="stat-box">
            <span class="stat-num purple">{{ leaveStats.awaiting_return }}</span>
            <span class="stat-label">待销假</span>
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
    <el-dialog
      v-model="ticketDetailVisible"
      title="办事申请详情"
      :width="isMobile ? '92%' : '420px'"
      align-center
      destroy-on-close
      class="ap-dialog"
    >
      <div v-if="ticketDetailTarget" class="ap-detail">
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>请核对申请人、事由与附件后再决定；通过后由对应科室出证，拒绝须写明理由并会推送学生。</span>
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
          v-if="ticketDetailTarget"
          type="danger"
          plain
          @click="reviewFromDetail(ticketDetailTarget, 'reject')"
        >拒绝申请</el-button>
        <el-button
          v-if="ticketDetailTarget"
          type="success"
          @click="reviewFromDetail(ticketDetailTarget, 'approve')"
        >通过申请</el-button>
      </template>
    </el-dialog>

    <!-- ===================== 请假拒绝 ===================== -->
    <el-dialog
      v-model="rejectVisible"
      title="拒绝请假"
      :width="isMobile ? '90%' : '380px'"
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
    </el-dialog>

    <!-- ===================== 材料驳回 ===================== -->
    <el-dialog
      v-model="rejectMaterialVisible"
      title="驳回材料"
      :width="isMobile ? '90%' : '380px'"
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
    </el-dialog>

    <!-- ===================== 办事申请 通过 / 拒绝 ===================== -->
    <el-dialog
      :title="ticketReviewAction === 'approve' ? '通过办事申请' : '拒绝办事申请'"
      v-model="ticketReviewVisible"
      :width="isMobile ? '90%' : '380px'"
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
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { ElMessage } from 'element-plus'
import {
  Document, Tickets, CircleCheck, CircleClose, Stamp,
  InfoFilled, Loading, Check, Close, FolderOpened, PieChart, Histogram, Refresh, User,
  View, Paperclip, Clock
} from '@element-plus/icons-vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave, confirmLeaveReturn, getLeaveStats, type LeaveStats } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import { getApprovalPending, reviewApproval, getApprovalStats, type ApprovalItem, type ApprovalStats } from '@/api/approval'
import type { LeaveRequestOut, ServiceTicket } from '@/types'
import { useResponsive } from '@/composables/useResponsive'

const { isMobile } = useResponsive()

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
  loadData()
}

const activeTab = ref('pending')
const pendingLeaves = ref<LeaveRequestOut[]>([])
const pendingTickets = ref<ServiceTicket[]>([])
const pendingMaterials = ref<ApprovalItem[]>([])
const stats = ref<ApprovalStats | null>(null)
const approvedLeaves = ref<LeaveRequestOut[]>([])
const rejectedLeaves = ref<LeaveRequestOut[]>([])
const leaveStats = ref<LeaveStats>({
  total: 0, approved: 0, rejected: 0, pending: 0, awaiting_return: 0,
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

// 已通过请假分页相关状态
const currentPageApprovedLeaves = ref(1)
const pageSizeApprovedLeaves = ref(10)

// 已拒绝请假分页相关状态
const currentPageRejectedLeaves = ref(1)
const pageSizeRejectedLeaves = ref(10)

const totalPending = computed(() => pendingLeaves.value.length + pendingTickets.value.length + pendingMaterials.value.length)

/** 桌面端类别 Tab：id 与各分区锚点一一对应（'' 代表「全部」），点击复用 jumpTo() 的分段与定位逻辑 */
const categoryTabs = computed(() => [
  { id: '', label: '全部待批', count: totalPending.value },
  { id: 'ap-sec-leave', label: '请假待批', count: pendingLeaves.value.length },
  { id: 'ap-sec-ticket', label: '办事待批', count: pendingTickets.value.length },
  { id: 'ap-sec-material', label: '材料待批', count: pendingMaterials.value.length },
])

/** 分段控件选项：与 activeTab 取值一一对应，count 为对应待处理数量 */
const tabOptions = computed(() => [
  { value: 'pending', label: '待审批', count: totalPending.value },
  { value: 'approved', label: '已通过', count: approvedLeaves.value.length || undefined },
  { value: 'rejected', label: '已拒绝', count: rejectedLeaves.value.length || undefined },
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

const paginatedApprovedLeaves = computed(() => {
  const start = (currentPageApprovedLeaves.value - 1) * pageSizeApprovedLeaves.value
  const end = start + pageSizeApprovedLeaves.value
  return approvedLeaves.value.slice(start, end)
})

const paginatedRejectedLeaves = computed(() => {
  const start = (currentPageRejectedLeaves.value - 1) * pageSizeRejectedLeaves.value
  const end = start + pageSizeRejectedLeaves.value
  return rejectedLeaves.value.slice(start, end)
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

function handleApprovedLeaveSizeChange() {
  currentPageApprovedLeaves.value = 1
}

function handleApprovedLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleRejectedLeaveSizeChange() {
  currentPageRejectedLeaves.value = 1
}

function handleRejectedLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

/** 办事申请类型标签（与后端 ServiceTicket.type 对齐：leave / certificate / project / feedback） */
const ticketTypeMap: Record<string, string> = {
  leave: '请假',
  certificate: '证明',
  project: '项目',
  feedback: '反馈',
}
function ticketTypeLabel(t?: string) {
  if (!t) return '办事'
  return ticketTypeMap[t] || t
}

/** 办事申请状态标签 */
const ticketStatusMap: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  approved: '已通过',
  rejected: '已拒绝',
}
function ticketStatusLabel(s?: string) {
  return s ? ticketStatusMap[s] || s : '—'
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

/** 总览卡片点击 → 切到待审批并滚动定位到对应分区 */
const anchor = ref('')
function jumpTo(id: string) {
  activeTab.value = 'pending'
  anchor.value = id
  loadData()
  nextTick(() => {
    const page = document.querySelector('.tui-page') as HTMLElement | null
    if (!page) return
    if (!id) {
      page.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }
    const el = document.getElementById(id)
    if (!el) return
    const top = page.scrollTop + (el.getBoundingClientRect().top - page.getBoundingClientRect().top) - 56
    page.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
  })
}

/** 办事申请详情弹窗：先看清申请人 / 事由 / 附件，再决定通过或拒绝 */
const ticketDetailVisible = ref(false)
const ticketDetailTarget = ref<ServiceTicket | null>(null)
function openTicketDetail(row: ServiceTicket) {
  ticketDetailTarget.value = row
  ticketDetailVisible.value = true
}
/** 详情弹窗内直接审批：关闭详情并复用统一的审批弹窗 */
function reviewFromDetail(row: ServiceTicket, action: 'approve' | 'reject') {
  ticketDetailVisible.value = false
  showTicketReview(row, action)
}

async function loadData() {
  const sid = studentFilter.value?.id || undefined
  loadStats()
  if (activeTab.value === 'pending') {
    try {
      pendingLeaves.value = (await getPendingLeaves(sid)).filter((l) => byStudent(l.student_id, l.student_name))
      loadAnalysis()
    } catch {}
    try {
      pendingTickets.value = (await getTickets({ student_id: sid }))
        .filter((t: ServiceTicket) => (t.status === 'pending' || t.status === 'processing') && byStudent(undefined, t.applicant_name))
    } catch {}
    try {
      pendingMaterials.value = (await getApprovalPending({ kind: 'material', status: 'pending', student_id: sid }))
        .filter((m) => byStudent(m.applicant_id, m.applicant_name))
    } catch { pendingMaterials.value = [] }
  } else if (activeTab.value === 'approved') {
    try { approvedLeaves.value = (await getAllLeaves('approved', sid)).filter((l) => byStudent(l.student_id, l.student_name)) } catch {}
  } else if (activeTab.value === 'rejected') {
    try { rejectedLeaves.value = (await getAllLeaves('rejected', sid)).filter((l) => byStudent(l.student_id, l.student_name)) } catch {}
  } else if (activeTab.value === 'stats') {
    await loadLeaveStats()
  }
}

async function loadLeaveStats() {
  try { leaveStats.value = await getLeaveStats() } catch { /* 统计失败不影响其它 Tab */ }
}

/** 统计条形图分段宽度百分比 */
function pct(part: number, total: number) {
  if (!total) return '0%'
  return `${Math.round((part / total) * 100)}%`
}

async function handleConfirmReturn(row: LeaveRequestOut) {
  try {
    await confirmLeaveReturn(row.id)
    ElMessage.success('已确认返校')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

async function loadStats() {
  try { stats.value = await getApprovalStats(30, studentFilter.value?.id || undefined) } catch { stats.value = null }
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
          console.log('[AI分析]', leave.id, result)
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
  loadData()
})
</script>

<style scoped>
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

.closed-hint { font-size: 12px; color: #98a2b3; }

/* ========== 移动端卡片列表（对齐 tui 规范：白卡 + 发丝边 + 去边框感） ========== */
.mobile-cards { display: flex; flex-direction: column; gap: 10px; }

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
