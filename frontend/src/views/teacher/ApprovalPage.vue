<template>
  <div class="tui-page">
    <SubPageHeader title="审批管理" :sub="totalPending + ' 条待处理'" fallback="/teacher/more">
      <template #right>
        <el-button text circle aria-label="刷新" @click="loadData()">
          <el-icon :size="19"><Refresh /></el-icon>
        </el-button>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">审批管理</h2>
          <p class="tui-header-sub">共 {{ totalPending }} 条待审批事项 · 请假、办事、材料一站式处理</p>
        </div>
        <div class="tui-header-actions">
          <el-button round :icon="Refresh" @click="loadData()">刷新</el-button>
        </div>
      </header>

      <!-- 待处理总览 -->
      <div class="tui-stat-row cols-4 ap-overview">
        <div class="tui-stat">
          <span class="tui-stat-num">{{ totalPending }}</span>
          <span class="tui-stat-label">待处理合计</span>
        </div>
        <div class="tui-stat">
          <span class="tui-stat-num ap-warn">{{ pendingLeaves.length }}</span>
          <span class="tui-stat-label">请假待批</span>
        </div>
        <div class="tui-stat">
          <span class="tui-stat-num ap-warn">{{ pendingTickets.length }}</span>
          <span class="tui-stat-label">办事待批</span>
        </div>
        <div class="tui-stat">
          <span class="tui-stat-num ap-warn">{{ pendingMaterials.length }}</span>
          <span class="tui-stat-label">材料待归档</span>
        </div>
      </div>

      <TuiSegmented
        v-model="activeTab"
        class="tui-seg-wrap"
        :options="tabOptions"
        @update:model-value="() => loadData()"
      />

      <template v-if="activeTab === 'pending'">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Document /></el-icon> 请假申请</h3>
            <el-tag v-if="pendingLeaves.length" type="warning" effect="plain" size="small">
              {{ pendingLeaves.length }} 条待批
            </el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedPendingLeaves" v-if="pendingLeaves.length" style="width:100%"
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
              <el-table-column label="AI 分析" min-width="200">
                <template #default="{ row }">
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
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="handleApprove(row)">
                    <el-icon><Check /></el-icon> 通过
                  </el-button>
                  <el-button type="danger" size="small" plain @click="showReject(row)">
                    <el-icon><Close /></el-icon> 拒绝
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
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
          <div class="pagination-wrapper" v-if="pendingLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageLeaves"
              v-model:page-size="pageSizeLeaves"
              :page-sizes="[50, 100, 200]"
              :total="pendingLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleLeaveSizeChange"
              @current-change="handleLeaveCurrentChange"
            />
          </div>
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><Document /></el-icon></span>
            <span class="tui-empty-title">暂无待批请假</span>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Tickets /></el-icon> 办事申请</h3>
            <el-tag v-if="pendingTickets.length" type="warning" effect="plain" size="small">
              {{ pendingTickets.length }} 条待批
            </el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="paginatedPendingTickets" v-if="pendingTickets.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="type" label="类型" width="90">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
              <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="showTicketReview(row, 'approve')">
                    <el-icon><Check /></el-icon> 通过
                  </el-button>
                  <el-button type="danger" size="small" plain @click="showTicketReview(row, 'reject')">
                    <el-icon><Close /></el-icon> 拒绝
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <!-- 移动端卡片 -->
          <div class="mobile-cards" v-if="isMobile && paginatedPendingTickets.length">
            <div class="mobile-card" v-for="row in paginatedPendingTickets" :key="row.id">
              <div class="mobile-card-header">
                <span class="mobile-card-student">{{ row.title }}</span>
                <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row" v-if="row.content">
                  <span class="mobile-card-label">内容</span>
                  <span class="mobile-card-value mobile-card-reason">{{ row.content }}</span>
                </div>
              </div>
              <div class="mobile-card-actions">
                <el-button type="success" size="small" @click="showTicketReview(row, 'approve')">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="showTicketReview(row, 'reject')">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </div>
            </div>
          </div>
          <div class="pagination-wrapper" v-if="pendingTickets.length > 0">
            <el-pagination
              v-model:current-page="currentPageTickets"
              v-model:page-size="pageSizeTickets"
              :page-sizes="[50, 100, 200]"
              :total="pendingTickets.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleTicketSizeChange"
              @current-change="handleTicketCurrentChange"
            />
          </div>
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><Tickets /></el-icon></span>
            <span class="tui-empty-title">暂无待办申请</span>
          </div>
        </div>

        <!-- 材料档案审批 -->
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><FolderOpened /></el-icon> 材料档案</h3>
            <el-tag v-if="pendingMaterials.length" type="warning" effect="plain" size="small">
              {{ pendingMaterials.length }} 条待归档
            </el-tag>
          </div>
          <!-- 桌面端表格 -->
          <div class="desktop-table" v-if="!isMobile">
            <el-table :data="pendingMaterials" v-if="pendingMaterials.length" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="applicant_name" label="学生" width="100" />
              <el-table-column prop="title" label="材料名称" min-width="180" show-overflow-tooltip />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button type="success" size="small" @click="handleMaterialApprove(row.id)">
                    <el-icon><Check /></el-icon> 通过归档
                  </el-button>
                  <el-button type="danger" size="small" plain @click="handleMaterialReject(row.id)">
                    <el-icon><Close /></el-icon> 驳回
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
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
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><FolderOpened /></el-icon></span>
            <span class="tui-empty-title">暂无待归档材料</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'approved'">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleCheck /></el-icon> 已通过请假</h3>
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
          <div class="pagination-wrapper" v-if="approvedLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageApprovedLeaves"
              v-model:page-size="pageSizeApprovedLeaves"
              :page-sizes="[50, 100, 200]"
              :total="approvedLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleApprovedLeaveSizeChange"
              @current-change="handleApprovedLeaveCurrentChange"
            />
          </div>
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><CircleCheck /></el-icon></span>
            <span class="tui-empty-title">暂无已通过请假</span>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'rejected'">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleClose /></el-icon> 已拒绝请假</h3>
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
          <div class="pagination-wrapper" v-if="rejectedLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageRejectedLeaves"
              v-model:page-size="pageSizeRejectedLeaves"
              :page-sizes="[50, 100, 200]"
              :total="rejectedLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleRejectedLeaveSizeChange"
              @current-change="handleRejectedLeaveCurrentChange"
            />
          </div>
          <div v-else class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><CircleClose /></el-icon></span>
            <span class="tui-empty-title">暂无已拒绝请假</span>
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

    <el-dialog v-model="rejectVisible" title="拒绝理由" width="420px" :close-on-click-modal="false">
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules">
        <el-form-item label="拒绝理由" prop="reason">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请填写拒绝理由，如：请假天数超出规定" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectMaterialVisible" title="驳回材料" width="420px" :close-on-click-modal="false">
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

    <el-dialog :title="ticketReviewAction === 'approve' ? '通过申请' : '拒绝申请'" v-model="ticketReviewVisible" width="420px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item :label="ticketReviewAction === 'approve' ? '审批意见（选填）' : '拒绝意见（必填）'" :required="ticketReviewAction === 'reject'">
          <el-input v-model="ticketReviewComment" type="textarea" :rows="3" :placeholder="ticketReviewAction === 'approve' ? '可填写审批意见，如：同意，注意返校日期' : '请填写拒绝意见，如：材料不全，请补充后重新提交'" maxlength="500" show-word-limit />
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
import { ref, reactive, computed, onMounted } from 'vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { ElMessage } from 'element-plus'
import {
  Document, Tickets, CircleCheck, CircleClose,
  InfoFilled, Loading, Check, Close, FolderOpened, PieChart, Histogram, Refresh
} from '@element-plus/icons-vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave, confirmLeaveReturn, getLeaveStats, type LeaveStats } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import { getApprovalPending, reviewApproval, getApprovalStats, type ApprovalItem, type ApprovalStats } from '@/api/approval'
import type { LeaveRequestOut, ServiceTicket } from '@/types'
import { useResponsive } from '@/composables/useResponsive'

const { isMobile } = useResponsive()

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
// 请假分页相关状态
const currentPageLeaves = ref(1)
const pageSizeLeaves = ref(50)

// 工单分页相关状态
const currentPageTickets = ref(1)
const pageSizeTickets = ref(50)

// 已通过请假分页相关状态
const currentPageApprovedLeaves = ref(1)
const pageSizeApprovedLeaves = ref(50)

// 已拒绝请假分页相关状态
const currentPageRejectedLeaves = ref(1)
const pageSizeRejectedLeaves = ref(50)

const totalPending = computed(() => pendingLeaves.value.length + pendingTickets.value.length + pendingMaterials.value.length)

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

async function loadData() {
  loadStats()
  if (activeTab.value === 'pending') {
    try {
      pendingLeaves.value = await getPendingLeaves()
      loadAnalysis()
    } catch {}
    try { pendingTickets.value = (await getTickets()).filter((t: ServiceTicket) => t.status === 'pending' || t.status === 'processing') } catch {}
    try { pendingMaterials.value = await getApprovalPending({ kind: 'material', status: 'pending' }) } catch { pendingMaterials.value = [] }
  } else if (activeTab.value === 'approved') {
    try { approvedLeaves.value = await getAllLeaves('approved') } catch {}
  } else if (activeTab.value === 'rejected') {
    try { rejectedLeaves.value = await getAllLeaves('rejected') } catch {}
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
  try { stats.value = await getApprovalStats(30) } catch { stats.value = null }
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

onMounted(loadData)
</script>

<style scoped>
/* ========== 卡片（对齐 tui 规范：白卡 + 发丝边 + 弱阴影） ========== */
.section-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  padding: 14px 16px;
  margin-bottom: 12px;
}

/* 待处理总览数字语义色（用双类名提高优先级，避免被 .tui-stat-num 覆盖） */
.tui-stat-num.ap-warn { color: var(--tui-warn); }

.section-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px;
}
.section-header h3 {
  font-size: 14.5px; font-weight: 600; color: var(--tui-text); margin: 0;
  display: flex; align-items: center; gap: 6px;
}
.section-header > :deep(.el-tag) { margin-left: auto; }

/* 桌面表格：轻量表头 + 圆角 */
.section-card :deep(.el-table) { border-radius: var(--tui-radius-sm); }
.section-card :deep(.el-table th.el-table__cell) { background: #f8f9fb !important; }

.ai-analyze { display: flex; align-items: center; gap: 6px; }
.analyze-tip { cursor: pointer; color: #909399; font-size: 14px; }
.analyze-tip:hover { color: #409eff; }
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
  font-size: 20px; font-weight: 700; color: var(--tui-text);
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

  :deep(.el-dialog) {
    width: 92vw !important;
    max-height: 70vh;
    margin: 0 auto !important;
    border-radius: 16px 16px 0 0 !important;
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    top: auto !important;
  }

  :deep(.el-dialog__body) {
    max-height: 50vh;
    overflow-y: auto;
  }
}
</style>
