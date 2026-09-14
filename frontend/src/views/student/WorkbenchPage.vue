<template>
  <div class="workbench-page">
    <!-- 头部欢迎区 -->
    <div class="workbench-header">
      <div class="header-bg-deco"></div>
      <div class="header-main">
        <div class="header-greeting">
          <div class="greeting-badge">
            <span class="badge-dot"></span>
            绵小城 · 工作台
          </div>
          <div class="greeting-text">你好，{{ auth.userName }}</div>
          <div class="greeting-sub">今天想办理什么业务？</div>
        </div>
        <img src="/images/mascot.png" alt="绵小城" class="header-mascot" />
      </div>
    </div>

    <!-- 办事服务 -->
    <div class="section-card">
      <div class="section-title">办事服务</div>
      <div class="service-grid">
        <div v-for="item in serviceItems" :key="item.key" class="service-item" @click="openService(item.key)">
          <div class="service-icon" :style="{ background: item.bgColor, color: item.color }">
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
          </div>
          <div class="service-label">{{ item.label }}</div>
        </div>
      </div>
    </div>

    <!-- 班级公告 -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">班级公告</div>
        <div class="section-more" @click="openAnnouncements">查看全部</div>
      </div>
      <div v-if="announcements.length === 0" class="empty-records">暂无班级公告</div>
      <div v-else class="announce-list">
        <div v-for="a in announcements.slice(0, 3)" :key="a.id" class="announce-item" @click="viewAnnouncement(a)">
          <div class="announce-icon" :class="'announce-icon-' + a.urgency">
            <el-icon :size="16"><Bell /></el-icon>
          </div>
          <div class="announce-info">
            <div class="announce-top">
              <span class="announce-title">{{ a.title }}</span>
              <el-tag :type="urgencyType(a.urgency)" size="small" effect="light" round>{{ urgencyLabel(a.urgency) }}</el-tag>
            </div>
            <div class="announce-content">{{ a.content }}</div>
            <div class="announce-time">{{ formatDate(a.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 联系与沟通 -->
    <div class="section-card">
      <div class="section-title">联系与沟通</div>
      <div class="contact-list">
        <div class="contact-item" @click="openChat">
          <div class="contact-icon" style="background: rgba(64,158,255,0.1); color: #409eff;">
            <el-icon :size="20"><ChatDotRound /></el-icon>
          </div>
          <div class="contact-info">
            <div class="contact-name">联系绵小城</div>
            <div class="contact-desc">AI智能助手，随时解答问题</div>
          </div>
          <el-icon class="contact-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="contact-item" @click="openMessages">
          <div class="contact-icon" style="background: rgba(103,194,58,0.1); color: #67c23a;">
            <el-icon :size="20"><Message /></el-icon>
          </div>
          <div class="contact-info">
            <div class="contact-name">消息中心</div>
            <div class="contact-desc">群聊、私聊、联系辅导员、系统通知</div>
          </div>
          <el-badge v-if="unreadCount" :value="unreadCount" class="contact-badge" />
          <el-icon class="contact-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="contact-item" @click="openPage('feedback')">
          <div class="contact-icon" style="background: rgba(179,127,235,0.1); color: #b37feb;">
            <el-icon :size="20"><Promotion /></el-icon>
          </div>
          <div class="contact-info">
            <div class="contact-name">意见反馈</div>
            <div class="contact-desc">提交问题或建议</div>
          </div>
          <el-icon class="contact-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 最近申请 -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">最近申请</div>
        <div class="section-more" @click="openAllRecords">查看全部</div>
      </div>
      <div v-if="recentRecords.length === 0" class="empty-records">暂无申请记录</div>
      <div v-else class="records-list">
        <div v-for="record in recentRecords" :key="record.id" class="record-item" @click="viewDetail(record)">
          <div class="record-left">
            <div class="record-type">{{ getTypeLabel(record.type) }}</div>
            <div class="record-title">{{ record.title }}</div>
            <div class="record-time">{{ formatDate(record.created_at) }}</div>
          </div>
          <div class="record-right">
            <el-tag :type="getStatusType(record.status)" size="small">{{ getStatusLabel(record.status) }}</el-tag>
          </div>
        </div>
      </div>
    </div>

    <div style="height: 80px;"></div>

    <!-- 子页面：办事服务表单 -->
    <transition name="slide-left">
      <div v-if="currentPage" :class="['sub-page', { 'chat-mode': currentPage === 'tutor' }]">
        <!-- 非聊天页面显示标准头部 -->
        <div v-if="currentPage !== 'tutor'" class="sub-page-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="sub-page-title">{{ pageTitle }}</div>
          <div class="sub-page-placeholder"></div>
        </div>

        <!-- 聊天页面显示简洁头部 -->
        <div v-if="currentPage === 'tutor'" class="chat-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="chat-header-title">{{ chatPartnerName }}</div>
          <div class="chat-header-placeholder"></div>
        </div>

        <div :class="['sub-page-content', { 'chat-content': currentPage === 'tutor' }]">
          <!-- 请假申请 -->
          <div v-if="currentPage === 'leave'">
            <div class="form-tip">
              <el-icon><InfoFilled /></el-icon>
              <span>请假申请提交后将由辅导员审批，请如实填写</span>
            </div>
            <el-form :model="leaveForm" label-position="top" class="sub-form">
              <el-form-item label="请假类型" required>
                <el-select v-model="leaveForm.leave_type" placeholder="请选择请假类型" style="width:100%">
                  <el-option label="课假" value="课假" /><el-option label="公假" value="公假" /><el-option label="宿假" value="宿假" />
                  <el-option label="事假" value="事假" /><el-option label="病假" value="病假" /><el-option label="其他" value="其他" />
                </el-select>
              </el-form-item>
              <div class="form-row">
                <el-form-item label="开始日期" required class="form-row-item">
                  <el-date-picker v-model="leaveForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width:100%" :disabled-date="disableStartDate" />
                </el-form-item>
                <el-form-item label="结束日期" required class="form-row-item">
                  <el-date-picker v-model="leaveForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width:100%" :disabled-date="disableEndDate" />
                </el-form-item>
              </div>
              <el-form-item label="请假理由" required>
                <el-input v-model="leaveForm.reason" type="textarea" :rows="2" placeholder="请详细描述请假原因" />
              </el-form-item>
              <template v-if="leaveForm.leave_type === '课假' || leaveForm.leave_type === '公假'">
                <el-form-item label="证明材料">
                  <UploadBtn @uploaded="addLeaveAttachment" />
                  <div v-for="(f, i) in leaveForm.attachments" :key="i" class="file-tag">
                    <el-tag closable @close="removeLeaveAttachment(i)">{{ fileName(f) }}</el-tag>
                  </div>
                </el-form-item>
              </template>
              <template v-if="leaveForm.leave_type === '宿假'">
                <div class="form-row">
                  <el-form-item label="宿舍楼" class="form-row-item">
                    <el-input v-model="leaveForm.dormitory_building" placeholder="如：A栋" />
                  </el-form-item>
                  <el-form-item label="宿舍号" class="form-row-item">
                    <el-input v-model="leaveForm.dormitory_room" placeholder="如：301" />
                  </el-form-item>
                </div>
                <el-form-item label="家长证明">
                  <UploadBtn v-model="leaveForm.parent_proof" />
                </el-form-item>
                <el-form-item label="其他证明">
                  <UploadBtn @uploaded="addLeaveAttachment" />
                  <div v-for="(f, i) in leaveForm.attachments" :key="i" class="file-tag">
                    <el-tag closable @close="removeLeaveAttachment(i)">{{ fileName(f) }}</el-tag>
                  </div>
                </el-form-item>
              </template>
            </el-form>
            <div class="sub-page-footer">
              <el-button type="primary" @click="submitLeave" :loading="submitting" style="width:100%">提交申请</el-button>
            </div>
          </div>

          <!-- 证明申请 -->
          <div v-if="currentPage === 'certificate'">
            <el-form :model="certForm" label-position="top" class="sub-form">
              <el-form-item label="证明类型" required>
                <el-select v-model="certForm.certificate_type" placeholder="请选择证明类型" style="width:100%">
                  <el-option label="在校证明" value="在校证明" /><el-option label="成绩单" value="成绩单" />
                  <el-option label="在读证明" value="在读证明" /><el-option label="学籍证明" value="学籍证明" /><el-option label="其他" value="其他" />
                </el-select>
              </el-form-item>
              <el-form-item label="用途说明" required>
                <el-input v-model="certForm.content" type="textarea" :rows="3" placeholder="请说明开具证明的用途" />
              </el-form-item>
              <el-form-item label="所需份数">
                <el-input-number v-model="certForm.quantity" :min="1" :max="20" style="width:100%" />
              </el-form-item>
              <el-form-item label="附件材料">
                <UploadBtn @uploaded="(u: string) => certForm.attachments.push(u)" />
                <div v-for="(f, i) in certForm.attachments" :key="i" class="file-tag">
                  <el-tag closable @close="certForm.attachments.splice(i, 1)">{{ fileName(f) }}</el-tag>
                </div>
              </el-form-item>
            </el-form>
            <div class="sub-page-footer">
              <el-button type="primary" @click="submitCert" :loading="submitting" style="width:100%">提交申请</el-button>
            </div>
          </div>

          <!-- 项目申请 -->
          <div v-if="currentPage === 'project'">
            <el-form :model="projectForm" label-position="top" class="sub-form">
              <el-form-item label="项目类型" required>
                <el-select v-model="projectForm.project_type" placeholder="请选择项目类型" style="width:100%">
                  <el-option label="竞赛项目" value="竞赛项目" /><el-option label="科研项目" value="科研项目" />
                  <el-option label="社会实践" value="社会实践" /><el-option label="创业项目" value="创业项目" />
                  <el-option label="学生工作" value="学生工作" /><el-option label="其他" value="其他" />
                </el-select>
              </el-form-item>
              <el-form-item label="项目名称" required>
                <el-input v-model="projectForm.title" placeholder="请输入项目名称" />
              </el-form-item>
              <el-form-item label="指导老师">
                <el-input v-model="projectForm.advisor" placeholder="指导老师姓名" />
              </el-form-item>
              <el-form-item label="团队成员">
                <el-input v-model="projectForm.team_members" placeholder="成员姓名（多个用逗号隔开）" />
              </el-form-item>
              <el-form-item label="开始日期" required>
                <el-date-picker v-model="projectForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" style="width:100%" />
              </el-form-item>
              <el-form-item label="结束日期" required>
                <el-date-picker v-model="projectForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="选择结束日期" style="width:100%" />
              </el-form-item>
              <el-form-item label="预算（元）">
                <el-input-number v-model="projectForm.budget" :min="0" :step="100" style="width:100%" />
              </el-form-item>
              <el-form-item label="项目简介" required>
                <el-input v-model="projectForm.content" type="textarea" :rows="4" placeholder="请描述项目背景、目标、预期成果" />
              </el-form-item>
              <el-form-item label="附件材料">
                <UploadBtn @uploaded="(u: string) => projectForm.attachments.push(u)" />
                <div v-for="(f, i) in projectForm.attachments" :key="i" class="file-tag">
                  <el-tag closable @close="projectForm.attachments.splice(i, 1)">{{ fileName(f) }}</el-tag>
                </div>
              </el-form-item>
            </el-form>
            <div class="sub-page-footer">
              <el-button type="primary" @click="submitProject" :loading="submitting" style="width:100%">提交申请</el-button>
            </div>
          </div>

          <!-- 意见反馈 -->
          <div v-if="currentPage === 'feedback'">
            <el-form :model="feedbackForm" label-position="top" class="sub-form">
              <el-form-item label="反馈类型">
                <el-select v-model="feedbackForm.type" placeholder="请选择反馈类型" style="width:100%">
                  <el-option label="问题反馈" value="bug" /><el-option label="功能建议" value="feature" />
                  <el-option label="投诉" value="complaint" /><el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-form-item label="标题" required>
                <el-input v-model="feedbackForm.title" placeholder="请简要描述您的反馈" maxlength="100" show-word-limit />
              </el-form-item>
              <el-form-item label="详细内容" required>
                <el-input v-model="feedbackForm.content" type="textarea" :rows="4" placeholder="请详细描述您的问题或建议" maxlength="1000" show-word-limit />
              </el-form-item>
              <el-form-item label="联系方式">
                <el-input v-model="feedbackForm.contact" placeholder="手机号/邮箱，方便我们联系您" />
              </el-form-item>
            </el-form>
            <div class="sub-page-footer">
              <el-button type="primary" @click="submitFeedback" :loading="submitting" style="width:100%">提交反馈</el-button>
            </div>
          </div>

          <!-- 失物招领 -->
          <div v-if="currentPage === 'lostfound'">
            <div class="lostfound-tabs">
              <div :class="['tab-item', { active: lostfoundTab === 'browse' }]" @click="lostfoundTab = 'browse'">浏览信息</div>
              <div :class="['tab-item', { active: lostfoundTab === 'publish' }]" @click="lostfoundTab = 'publish'">发布信息</div>
            </div>

            <!-- 浏览失物招领 -->
            <div v-if="lostfoundTab === 'browse'" class="lostfound-list">
              <div v-if="lostfoundItems.length === 0" class="empty-records">暂无失物招领信息</div>
              <div v-for="item in lostfoundItems" :key="item.id" class="lostfound-item" @click="openLostFoundDetail(item)">
                <div class="lostfound-main">
                  <img v-if="item.image_url" :src="item.image_url" class="lostfound-thumb" />
                  <div class="lostfound-body">
                    <div class="lostfound-header">
                      <el-tag :type="item.type === 'lost' ? 'danger' : 'success'" size="small">
                        {{ item.type === 'lost' ? '寻物' : '招领' }}
                      </el-tag>
                      <span class="lostfound-time">{{ formatDate(item.created_at) }}</span>
                    </div>
                    <div class="lostfound-title">{{ item.title }}</div>
                    <div class="lostfound-desc">{{ item.description }}</div>
                    <div class="lostfound-location">
                      <el-icon><Location /></el-icon>
                      <span>{{ item.location || '地点不详' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 发布失物招领 -->
            <div v-if="lostfoundTab === 'publish'">
              <el-form :model="lostfoundForm" label-position="top" class="sub-form">
                <el-form-item label="类型" required>
                  <el-radio-group v-model="lostfoundForm.type">
                    <el-radio value="lost">寻物启事</el-radio>
                    <el-radio value="found">失物招领</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="物品名称" required>
                  <el-input v-model="lostfoundForm.title" placeholder="如：黑色钱包、蓝色水杯" maxlength="50" />
                </el-form-item>
                <el-form-item label="详细描述">
                  <el-input v-model="lostfoundForm.description" type="textarea" :rows="3" placeholder="请描述物品特征" />
                </el-form-item>
                <el-form-item label="地点">
                  <el-input v-model="lostfoundForm.location" placeholder="丢失/拾获地点" />
                </el-form-item>
                <el-form-item label="联系方式">
                  <el-input v-model="lostfoundForm.contact" placeholder="手机号或微信号" />
                </el-form-item>
              </el-form>
              <div class="sub-page-footer">
                <el-button type="primary" @click="submitLostFound" :loading="submitting" style="width:100%">发布信息</el-button>
              </div>
            </div>
          </div>

          <!-- 失物招领详情 -->
          <div v-if="currentPage === 'lostfound' && lostfoundDetailVisible && lostfoundDetail" class="lf-detail-overlay">
            <div class="lf-detail-sheet">
              <div class="sheet-handle"></div>
              <div class="lf-detail-top">
                <el-tag :type="lostfoundDetail.type === 'lost' ? 'danger' : 'success'" size="small">
                  {{ lostfoundDetail.type === 'lost' ? '寻物' : '招领' }}
                </el-tag>
                <span class="lf-detail-user">{{ lostfoundDetail.user_name }} · {{ formatDate(lostfoundDetail.created_at) }}</span>
              </div>
              <img v-if="lostfoundDetail.image_url" :src="lostfoundDetail.image_url" class="lf-detail-img" />
              <div class="lf-detail-info">
                <div class="lf-detail-title">{{ lostfoundDetail.title }}</div>
                <div v-if="lostfoundDetail.description" class="lf-detail-desc">{{ lostfoundDetail.description }}</div>
                <div class="lf-detail-row">
                  <span class="lf-detail-label">地点</span>
                  <span>{{ lostfoundDetail.location || '不详' }}</span>
                </div>
                <div class="lf-detail-row">
                  <span class="lf-detail-label">联系方式</span>
                  <span>{{ lostfoundDetail.contact || '未留' }}</span>
                </div>
              </div>
              <div class="lf-detail-close">
                <el-button type="primary" plain round style="width:100%" @click="lostfoundDetailVisible = false">关闭</el-button>
              </div>
            </div>
          </div>

          <!-- 全部申请记录 -->
          <div v-if="currentPage === 'allRecords'" class="all-records-page">
            <div v-if="allRecords.length === 0" class="empty-records">
              <el-icon :size="48" color="#d0d5dd"><Document /></el-icon>
              <span>暂无申请记录</span>
            </div>
            <div v-else class="all-records-list">
              <div v-for="record in allRecords" :key="record.id" class="record-item" @click="viewDetail(record)">
                <div class="record-left">
                  <div class="record-type">{{ getTypeLabel(record.type) }}</div>
                  <div class="record-title">{{ record.title }}</div>
                  <div class="record-time">{{ formatDate(record.created_at) }}</div>
                </div>
                <div class="record-right">
                  <el-tag :type="getStatusType(record.status)" size="small" round>{{ getStatusLabel(record.status) }}</el-tag>
                </div>
              </div>
            </div>
          </div>

          <!-- 班级公告 -->
          <div v-if="currentPage === 'announcements'" class="announce-page">
            <div v-if="announcements.length === 0" class="empty-records">
              <el-icon :size="48" color="#d0d5dd"><Bell /></el-icon>
              <span>暂无班级公告</span>
            </div>
            <div v-else class="announce-page-list">
              <div v-for="a in announcements" :key="a.id" class="announce-page-card" :class="'announce-page-' + a.urgency">
                <div class="announce-page-head">
                  <span class="announce-page-title">{{ a.title }}</span>
                  <el-tag :type="urgencyType(a.urgency)" size="small" effect="light" round>{{ urgencyLabel(a.urgency) }}</el-tag>
                </div>
                <div class="announce-page-content">{{ a.content }}</div>
                <div class="announce-page-foot">
                  <span>{{ a.teacher_name }} · {{ formatDate(a.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 消息中心 -->
          <div v-if="currentPage === 'messages'" class="messages-page">
            <!-- 辅导员入口 -->
            <div v-if="auth.user?.tutor_id" class="tutor-entry" @click="startTutorChat">
              <div class="tutor-entry-avatar">
                <el-avatar :size="48" style="background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%); color: #fff; font-weight: 600;">导</el-avatar>
              </div>
              <div class="tutor-entry-info">
                <div class="tutor-entry-name">我的辅导员</div>
                <div class="tutor-entry-desc">在线咨询、预约面谈</div>
              </div>
              <el-icon class="tutor-entry-arrow"><ArrowRight /></el-icon>
            </div>

            <!-- 消息列表 -->
            <div class="messages-list">
              <div v-if="conversationList.length === 0" class="empty-messages">
                <el-icon :size="48" color="#d0d5dd"><ChatDotRound /></el-icon>
                <span>暂无消息</span>
              </div>
              <div v-for="conv in conversationList" :key="conv.user_id" class="message-item" @click="openConversation(conv)">
                <div class="message-avatar">
                  <el-avatar :size="48" :src="conv.user_avatar || ''">{{ conv.user_name?.[0] }}</el-avatar>
                  <div v-if="conv.unread_count" class="message-unread">{{ conv.unread_count > 99 ? '99+' : conv.unread_count }}</div>
                </div>
                <div class="message-info">
                  <div class="message-top">
                    <span class="message-name">{{ conv.user_name }}</span>
                    <span class="message-time">{{ formatDate(conv.last_message_time) }}</span>
                  </div>
                  <div class="message-preview">{{ conv.last_message || '暂无消息' }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 聊天页面 -->
          <div v-if="currentPage === 'tutor'" class="chat-page">
            <div class="chat-messages" ref="tutorMsgRef">
              <div v-if="tutorMessages.length === 0" class="empty-chat">
                <el-icon :size="48" color="#d0d5dd"><ChatDotRound /></el-icon>
                <span>暂无消息，发送第一条消息吧</span>
              </div>
              <div v-for="msg in tutorMessages" :key="msg.id" :class="['chat-msg', msg.sender_id === auth.user?.id ? 'mine' : 'theirs']">
                <div class="chat-msg-bubble">{{ msg.content }}</div>
                <div class="chat-msg-time">{{ formatDate(msg.created_at) }}</div>
              </div>
            </div>
            <div class="chat-input-bar">
              <div class="chat-input-container">
                <textarea
                  ref="chatTextareaRef"
                  v-model="tutorNewMsg"
                  placeholder="输入消息..."
                  class="chat-textarea"
                  rows="1"
                  @input="autoResizeChat"
                  @keydown.enter.prevent="sendTutorMessage"
                ></textarea>
                <button type="button" class="chat-send-btn" :disabled="!tutorNewMsg.trim()" @click="sendTutorMessage">
                  <el-icon :size="18"><Promotion /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 详情弹窗 -->
    <el-dialog v-model="showDetail" :show-title="false" width="100%" class="detail-dialog" destroy-on-close>
      <div v-if="currentDetail" class="detail-content">
        <div class="sheet-handle"></div>
        <!-- 状态头部 -->
        <div class="detail-hero" :class="'hero-' + currentDetail.status">
          <div class="hero-status">{{ getStatusLabel(currentDetail.status) }}</div>
          <div class="hero-title">{{ currentDetail._source === 'leave' ? getLeaveTypeLabel(currentDetail.leave_type) + '申请' : currentDetail.title }}</div>
          <div class="hero-time">{{ currentDetail.created_at }}</div>
        </div>
        <!-- 详情列表 -->
        <div class="detail-body">
          <template v-if="currentDetail._source === 'leave'">
            <div class="detail-row">
              <span class="detail-label">请假类型</span>
              <span class="detail-value">{{ getLeaveTypeLabel(currentDetail.leave_type) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">起止日期</span>
              <span class="detail-value">{{ currentDetail.start_date }} ~ {{ currentDetail.end_date }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">请假原因</span>
              <span class="detail-value detail-value-block">{{ currentDetail.reason || currentDetail.content }}</span>
            </div>
            <div v-if="currentDetail.reject_reason" class="detail-row detail-row-reject">
              <span class="detail-label">驳回原因</span>
              <span class="detail-value detail-reject">{{ currentDetail.reject_reason }}</span>
            </div>
          </template>
          <template v-else>
            <div class="detail-row">
              <span class="detail-label">工单类型</span>
              <span class="detail-value">{{ getTypeLabel(currentDetail.type) }}</span>
            </div>
            <div v-if="currentDetail.content" class="detail-row">
              <span class="detail-label">内容说明</span>
              <span class="detail-value detail-value-block">{{ currentDetail.content }}</span>
            </div>
            <template v-if="currentDetail.form_data && Object.keys(currentDetail.form_data).length">
              <div v-for="(val, key) in currentDetail.form_data" :key="key" class="detail-row">
                <span class="detail-label">{{ formFieldLabel(String(key)) }}</span>
                <span class="detail-value">{{ typeof val === 'object' ? JSON.stringify(val) : val || '-' }}</span>
              </div>
            </template>
            <div v-if="currentDetail.attachments?.length" class="detail-row">
              <span class="detail-label">附件材料</span>
              <div class="detail-value">
                <a v-for="(url, i) in currentDetail.attachments" :key="i" :href="url" target="_blank" class="attachment-link">
                  <el-icon :size="14"><Document /></el-icon> {{ fileName(url) }}
                </a>
              </div>
            </div>
          </template>
        </div>
        <!-- 撤销按钮 -->
        <div v-if="currentDetail.status === 'pending'" class="detail-cancel">
          <button type="button" class="revoke-btn revoke-btn-lg" @click="cancelRecord(currentDetail)">
            <el-icon :size="14"><Close /></el-icon> 撤销申请
          </button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { createLeave, getMyLeaves, deleteLeave } from '@/api/leave'
import { createTicket, getTickets, cancelTicket } from '@/api/service'
import { createFeedback } from '@/api/feedback'
import { getLostFoundItems, createLostFoundItem, getLostFoundItem } from '@/api/lost_found'
import { getConversations } from '@/api/messages'
import { getStudentAnnouncements, markAnnouncementRead, type AnnouncementItem } from '@/api/announcement'
import UploadBtn from '@/components/upload/UploadBtn.vue'
import {
  Calendar, Document, Promotion, ChatDotRound, Message,
  ArrowRight, ArrowLeft, Search,
  InfoFilled, Location, Close, Bell
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const currentPage = ref<string | null>(null)
const submitting = ref(false)
const showDetail = ref(false)
const currentDetail = ref<any>(null)
const unreadCount = ref(0)
const lostfoundTab = ref<'browse' | 'publish'>('browse')

const leaveRecords = ref<any[]>([])
const tickets = ref<any[]>([])
const lostfoundItems = ref<any[]>([])
const lostfoundDetail = ref<any>(null)
const lostfoundDetailVisible = ref(false)
const conversationList = ref<any[]>([])
const tutorMessages = ref<any[]>([])
const tutorIdRef = ref<number | null>(null)
const tutorNewMsg = ref('')

const announcements = ref<AnnouncementItem[]>([])

// 办事服务配置
const serviceItems = [
  { key: 'leave', label: '请假申请', icon: Calendar, color: '#409eff', bgColor: 'rgba(64,158,255,0.1)' },
  { key: 'certificate', label: '证明申请', icon: Document, color: '#67c23a', bgColor: 'rgba(103,194,58,0.1)' },
  { key: 'project', label: '项目申请', icon: Promotion, color: '#e6a23c', bgColor: 'rgba(230,162,60,0.1)' },
  { key: 'lostfound', label: '失物招领', icon: Search, color: '#f56c6c', bgColor: 'rgba(245,108,108,0.1)' },
]

// 表单数据
const leaveForm = reactive({
  leave_type: '', start_date: '', end_date: '', reason: '',
  dormitory_building: '', dormitory_room: '', parent_proof: '',
  attachments: [] as string[],
})
const certForm = reactive({ certificate_type: '', content: '', quantity: 1, attachments: [] as string[] })
const projectForm = reactive({
  project_type: '', title: '', advisor: '', content: '',
  team_members: '', start_date: '', end_date: '', budget: 0,
  attachments: [] as string[],
})
const feedbackForm = reactive({ type: 'other', title: '', content: '', contact: '' })
const lostfoundForm = reactive({ type: 'lost', title: '', description: '', location: '', contact: '' })

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    leave: '请假申请',
    certificate: '证明申请',
    project: '项目申请',
    feedback: '意见反馈',
    lostfound: '失物招领',
    messages: '消息中心',
    allRecords: '全部申请',
    announcements: '班级公告'
  }
  return titles[currentPage.value || ''] || ''
})

// 聊天对象名称
const chatPartnerName = computed(() => {
  if (tutorIdRef.value) {
    const conv = conversationList.value.find(c => c.user_id === tutorIdRef.value)
    if (conv) return conv.user_name
  }
  return '辅导员'
})

const chatTextareaRef = ref<HTMLTextAreaElement>()

// 最近记录（最多显示3条）
const recentRecords = computed(() => {
  return [...allRecords.value].slice(0, 3)
})

// 全部记录
const allRecords = computed(() => {
  const all = [
    ...leaveRecords.value.map(r => ({
      id: r.id,
      _source: 'leave',
      type: 'leave',
      title: `${getLeaveTypeLabel(r.leave_type)} ${r.start_date} ~ ${r.end_date}`,
      status: r.status,
      created_at: r.created_at,
      content: r.reason,
      reason: r.reason,
      leave_type: r.leave_type,
      start_date: r.start_date,
      end_date: r.end_date,
      reject_reason: r.reject_reason
    })),
    ...tickets.value.map(r => ({
      id: r.id,
      _source: 'ticket',
      type: r.type,
      title: r.title,
      status: r.status,
      created_at: r.created_at,
      content: r.content,
      form_data: r.form_data,
      attachments: r.attachments
    }))
  ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  return all
})

function getLeaveTypeLabel(type: string) {
  const m: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return m[type] || '请假'
}

function getTypeLabel(type: string) {
  const m: Record<string, string> = { leave: '请假', certificate: '证明', project: '项目', feedback: '反馈' }
  return m[type] || type
}

function getStatusLabel(status: string) {
  const m: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
  return m[status] || status
}

function getStatusType(status: string) {
  const m: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return m[status] || 'info'
}

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function formFieldLabel(k: string) {
  const m: Record<string, string> = { leave_type: '请假类型', start_date: '开始日期', end_date: '结束日期', dormitory_building: '宿舍楼', dormitory_room: '宿舍号', parent_proof: '家长证明', certificate_type: '证明类型', quantity: '份数', project_type: '项目类型', advisor: '指导老师', team_members: '团队成员', budget: '预算', project_name: '项目名称' }
  return m[k] || k
}

function fileName(url: string) {
  return url.split('/').pop() || url
}

// 请假日期校验（与网页端一致）
function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function disableStartDate(d: Date): boolean {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return d.getTime() < today.getTime()
}

function disableEndDate(d: Date): boolean {
  if (!leaveForm.start_date) return false
  return d.getTime() < new Date(leaveForm.start_date + 'T00:00:00').getTime()
}

function addLeaveAttachment(url: string) {
  leaveForm.attachments.push(url)
}

function removeLeaveAttachment(i: number) {
  leaveForm.attachments.splice(i, 1)
}

function openService(key: string) {
  currentPage.value = key
  if (key === 'lostfound') loadLostFound()
}

function openChat() {
  router.push('/student')
}

function openMessages() {
  currentPage.value = 'messages'
  loadConversations()
}

function openAllRecords() {
  currentPage.value = 'allRecords'
}

function openAnnouncements() {
  currentPage.value = 'announcements'
}

async function loadAnnouncements() {
  try {
    announcements.value = await getStudentAnnouncements() as any
  } catch {
    announcements.value = []
  }
}

async function viewAnnouncement(a: AnnouncementItem) {
  try { await markAnnouncementRead(a.id) } catch {}
}

function urgencyType(u: string) {
  const map: Record<string, string> = { urgent: 'danger', important: 'warning', normal: 'info' }
  return map[u] || 'info'
}

function urgencyLabel(u: string) {
  const map: Record<string, string> = { urgent: '紧急', important: '重要', normal: '普通' }
  return map[u] || '普通'
}

async function loadConversations() {
  try {
    const convs = await getConversations()
    conversationList.value = convs as any
  } catch {
    conversationList.value = []
  }
}

function openConversation(conv: any) {
  // 打开与指定用户的聊天
  currentPage.value = 'tutor'
  tutorIdRef.value = conv.user_id
  loadTutorChat(conv.user_id)
}

function startTutorChat() {
  const tutorId = auth.user?.tutor_id
  if (!tutorId) {
    ElMessage.warning('您还未绑定辅导员，请先在个人资料中绑定')
    return
  }
  // 打开与辅导员的聊天页面
  currentPage.value = 'tutor'
  loadTutorChat(tutorId)
}

async function loadTutorChat(tutorId: number) {
  try {
    const { getMessages } = await import('@/api/messages')
    const msgs = await getMessages(tutorId)
    tutorMessages.value = msgs as any
    tutorIdRef.value = tutorId
  } catch {
    tutorMessages.value = []
  }
}

async function sendTutorMessage() {
  if (!tutorNewMsg.value.trim() || !tutorIdRef.value) return
  try {
    const { sendMessage } = await import('@/api/messages')
    const result = await sendMessage(tutorIdRef.value, tutorNewMsg.value)
    tutorMessages.value.push({
      id: result.id,
      sender_id: auth.user?.id || 0,
      receiver_id: tutorIdRef.value,
      content: tutorNewMsg.value,
      read: true,
      created_at: result.created_at
    })
    tutorNewMsg.value = ''
  } catch (e) {
    ElMessage.error('发送失败')
  }
}

function autoResizeChat() {
  const el = chatTextareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.max(20, Math.min(el.scrollHeight, 80)) + 'px'
}

function openPage(page: string) {
  currentPage.value = page
}

function closePage() {
  currentPage.value = null
  showDetail.value = false
  currentDetail.value = null
  lostfoundDetailVisible.value = false
  lostfoundDetail.value = null
}

function viewDetail(record: any) {
  currentDetail.value = record
  showDetail.value = true
}

async function loadData() {
  try {
    const [leaves, ticketList] = await Promise.all([getMyLeaves(), getTickets()])
    leaveRecords.value = leaves as any
    tickets.value = ticketList as any
  } catch {}
  
  loadAnnouncements()

  // 获取未读消息数
  try {
    const convs: any[] = await getConversations()
    unreadCount.value = convs.reduce((sum, c) => sum + (c.unread_count || 0), 0)
  } catch {}
}

async function loadLostFound() {
  try {
    lostfoundItems.value = await getLostFoundItems() as any
  } catch {}
}

function mapLeaveType(label: string): string {
  const m: Record<string, string> = { '课假': 'other', '公假': 'competition', '宿假': 'personal', '事假': 'personal', '病假': 'sick', '其他': 'other' }
  return m[label] || 'other'
}

async function submitLeave() {
  if (!leaveForm.leave_type || !leaveForm.start_date || !leaveForm.end_date || !leaveForm.reason) {
    ElMessage.warning('请填写所有必填项')
    return
  }
  if (leaveForm.start_date < todayStr()) {
    ElMessage.error('开始日期不能早于今天')
    return
  }
  if (leaveForm.end_date < leaveForm.start_date) {
    ElMessage.error('结束日期不能早于开始日期')
    return
  }
  const days = (new Date(leaveForm.end_date + 'T00:00:00').getTime() - new Date(leaveForm.start_date + 'T00:00:00').getTime()) / 86400000
  if (days > 14) {
    ElMessage.error('请假时长不能超过15天')
    return
  }
  submitting.value = true
  try {
    await createLeave({
      start_date: leaveForm.start_date,
      end_date: leaveForm.end_date,
      reason: `[${leaveForm.leave_type}] ${leaveForm.reason}`,
      leave_type: mapLeaveType(leaveForm.leave_type)
    })
    ElMessage.success('请假申请已提交，等待辅导员审批')
    Object.assign(leaveForm, { leave_type: '', start_date: '', end_date: '', reason: '', dormitory_building: '', dormitory_room: '', parent_proof: '', attachments: [] })
    closePage()
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function cancelRecord(record: any) {
  try {
    await ElMessageBox.confirm('确定要撤销这条申请吗？撤销后将直接删除该记录。', '确认撤销', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  try {
    if (record._source === 'leave') {
      await deleteLeave(record.id)
    } else {
      await cancelTicket(record.id)
    }
    ElMessage.success('已撤销')
    showDetail.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '撤销失败')
  }
}

async function submitCert() {
  if (!certForm.certificate_type || !certForm.content) {
    ElMessage.warning('请填写所有必填项')
    return
  }
  submitting.value = true
  try {
    await createTicket({
      type: 'certificate',
      title: certForm.certificate_type,
      content: certForm.content,
      applicant_name: auth.userName || '',
      applicant_no: auth.user?.username || '',
      applicant_college: auth.user?.college || '',
      form_data: { certificate_type: certForm.certificate_type, quantity: certForm.quantity },
      attachments: certForm.attachments.length ? certForm.attachments : undefined
    })
    ElMessage.success('证明申请已提交')
    Object.assign(certForm, { certificate_type: '', content: '', quantity: 1, attachments: [] })
    closePage()
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function submitProject() {
  if (!projectForm.project_type || !projectForm.title || !projectForm.start_date || !projectForm.end_date || !projectForm.content) {
    ElMessage.warning('请填写所有必填项')
    return
  }
  if (projectForm.end_date < projectForm.start_date) {
    ElMessage.error('结束日期不能早于开始日期')
    return
  }
  submitting.value = true
  try {
    await createTicket({
      type: 'project',
      title: projectForm.title,
      content: projectForm.content,
      applicant_name: auth.userName || '',
      applicant_no: auth.user?.username || '',
      applicant_college: auth.user?.college || '',
      form_data: {
        project_type: projectForm.project_type,
        advisor: projectForm.advisor,
        team_members: projectForm.team_members,
        start_date: projectForm.start_date,
        end_date: projectForm.end_date,
        budget: projectForm.budget
      },
      attachments: projectForm.attachments.length ? projectForm.attachments : undefined
    })
    ElMessage.success('项目申请已提交')
    Object.assign(projectForm, { project_type: '', title: '', advisor: '', content: '', team_members: '', start_date: '', end_date: '', budget: 0, attachments: [] })
    closePage()
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function submitFeedback() {
  if (!feedbackForm.title || !feedbackForm.content) {
    ElMessage.warning('请填写所有必填项')
    return
  }
  submitting.value = true
  try {
    await createFeedback(feedbackForm)
    ElMessage.success('反馈已提交，感谢您的意见！')
    Object.assign(feedbackForm, { type: 'other', title: '', content: '', contact: '' })
    closePage()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function openLostFoundDetail(item: any) {
  try {
    lostfoundDetail.value = await getLostFoundItem(item.id)
    lostfoundDetailVisible.value = true
  } catch {
    lostfoundDetail.value = item
    lostfoundDetailVisible.value = true
  }
}

async function submitLostFound() {
  if (!lostfoundForm.title) {
    ElMessage.warning('请填写物品名称')
    return
  }
  submitting.value = true
  try {
    await createLostFoundItem(lostfoundForm)
    ElMessage.success('信息发布成功')
    lostfoundForm.title = ''
    lostfoundForm.description = ''
    lostfoundForm.location = ''
    lostfoundForm.contact = ''
    lostfoundTab.value = 'browse'
    await loadLostFound()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.workbench-page {
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
}

/* 头部 */
.workbench-header {
  background: linear-gradient(135deg, #4f8ef7 0%, #3b6dd4 50%, #2c5282 100%);
  padding: 20px 16px 28px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.header-bg-deco {
  position: absolute;
  top: -40px;
  right: -40px;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
  pointer-events: none;
}

.header-bg-deco::before {
  content: '';
  position: absolute;
  top: 30px;
  left: -60px;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: rgba(255,255,255,0.05);
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}

.header-greeting {
  flex: 1;
}

.greeting-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255,255,255,0.18);
  padding: 4px 10px;
  border-radius: 20px;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67e8f9;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.7); }
}

.greeting-text {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
  letter-spacing: 0.5px;
}

.greeting-sub {
  font-size: 13px;
  opacity: 0.85;
}

.header-mascot {
  width: 80px;
  height: 80px;
  object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.2));
  margin-left: 12px;
  flex-shrink: 0;
}

/* 区域卡片 */
.section-card {
  margin: 0 12px 16px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  position: relative;
}

.workbench-header + .section-card {
  margin-top: -12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.section-header .section-title {
  margin-bottom: 0;
}

.section-more {
  font-size: 12px;
  color: #999;
  cursor: pointer;
}

/* 服务网格 */
.service-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.service-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.service-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.service-item:active .service-icon {
  transform: scale(0.95);
}

.service-label {
  font-size: 12px;
  color: #333;
  font-weight: 500;
}

/* 联系列表 */
.contact-list {
  display: flex;
  flex-direction: column;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  position: relative;
}

.contact-item:last-child {
  border-bottom: none;
}

.contact-item:active {
  background: #f5f7fa;
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.contact-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.contact-info {
  flex: 1;
}

.contact-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 2px;
}

.contact-desc {
  font-size: 12px;
  color: #999;
}

.contact-arrow {
  color: #ccc;
  font-size: 14px;
}

.contact-badge {
  position: absolute;
  right: 28px;
  top: 8px;
}

/* 记录列表 */
.empty-records {
  text-align: center;
  color: #999;
  padding: 20px 0;
  font-size: 13px;
}

/* 班级公告 */
.announce-list { display: flex; flex-direction: column; gap: 8px; }
.announce-item {
  display: flex; gap: 10px; padding: 10px 12px;
  background: #f9fafb; border-radius: 10px; cursor: pointer;
}
.announce-item:active { background: #eef1f5; }
.announce-icon {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.announce-icon-urgent { background: rgba(245,108,108,0.12); color: #f56c6c; }
.announce-icon-important { background: rgba(230,162,60,0.14); color: #e6a23c; }
.announce-icon-normal { background: rgba(144,147,153,0.12); color: #909399; }
.announce-info { flex: 1; min-width: 0; }
.announce-top { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
.announce-title { font-size: 13px; font-weight: 600; color: #1a1a1a; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.announce-content {
  font-size: 12px; color: #888; line-height: 1.5; margin-bottom: 3px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.announce-time { font-size: 11px; color: #ccc; }

/* 公告子页面 */
.announce-page-list { display: flex; flex-direction: column; gap: 10px; }
.announce-page-card {
  background: #fff; border-radius: 12px; padding: 14px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.announce-page-urgent { border-left: 3px solid #f56c6c; }
.announce-page-important { border-left: 3px solid #e6a23c; }
.announce-page-normal { border-left: 3px solid #e5e7eb; }
.announce-page-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.announce-page-title { font-size: 15px; font-weight: 600; color: #1a1a1a; flex: 1; min-width: 0; }
.announce-page-content { font-size: 13px; color: #666; line-height: 1.6; margin-bottom: 8px; white-space: pre-wrap; word-break: break-word; }
.announce-page-foot { font-size: 12px; color: #999; }

.records-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.records-list,
.records-list *,
.records-list :deep(.el-tag),
.records-list :deep(.el-tag *) {
  transition: none !important;
  animation: none !important;
}

.record-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 14px;
  background: #f9fafb;
  border-radius: 10px;
  cursor: pointer;
}

.record-item:active {
  background: #eef1f5;
  transform: scale(0.99);
}

.record-left {
  flex: 1;
  min-width: 0;
}

.record-type {
  display: inline-block;
  font-size: 11px;
  color: #409eff;
  font-weight: 500;
  background: rgba(64,158,255,0.08);
  padding: 1px 8px;
  border-radius: 10px;
  margin-bottom: 4px;
}

.record-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
}

.record-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 12px;
}

.record-time {
  font-size: 11px;
  color: #ccc;
}

.record-actions {
  margin-top: 4px;
}

.revoke-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 12px;
  border: 1.5px solid #fca5a5;
  border-radius: 20px;
  background: linear-gradient(135deg, #fff5f5 0%, #fee2e2 100%);
  color: #dc2626;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
}

.revoke-btn:hover {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border-color: #f87171;
  box-shadow: 0 2px 8px rgba(220,38,38,0.15);
}

.revoke-btn:active {
  transform: scale(0.95);
  background: #fca5a5;
  color: #fff;
}

.revoke-btn-lg {
  padding: 8px 24px;
  font-size: 14px;
  border-radius: 24px;
}

.file-tag {
  display: inline-block;
  margin: 4px 4px 0 0;
}

/* 失物招领 */
.lostfound-tabs {
  display: flex;
  background: #fff;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 16px;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 10px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-item.active {
  background: #409eff;
  color: #fff;
}

.lostfound-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lostfound-item {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  cursor: pointer;
}

.lostfound-main {
  display: flex;
  gap: 12px;
}

.lostfound-thumb {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  background: #f5f7fa;
}

.lostfound-body {
  flex: 1;
  min-width: 0;
}

.lostfound-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.lostfound-time {
  font-size: 12px;
  color: #999;
}

.lostfound-title {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
}

.lostfound-desc {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.lostfound-location {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #999;
}

/* 失物招领详情弹窗 */
.lf-detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 200;
  display: flex;
  align-items: flex-end;
}

.lf-detail-sheet {
  width: 100%;
  max-height: 75vh;
  background: #fff;
  border-radius: 20px 20px 0 0;
  padding: 0 16px 20px;
  overflow-y: auto;
}

.lf-detail-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.lf-detail-user {
  font-size: 12px;
  color: #999;
}

.lf-detail-img {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 10px;
  margin-bottom: 12px;
  background: #f5f7fa;
}

.lf-detail-info {
  margin-bottom: 16px;
}

.lf-detail-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.lf-detail-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 12px;
}

.lf-detail-row {
  display: flex;
  padding: 8px 0;
  font-size: 13px;
  color: #333;
  border-bottom: 1px solid #f5f5f5;
}

.lf-detail-label {
  color: #999;
  width: 56px;
  flex-shrink: 0;
  margin-right: 10px;
}

/* 表单提示 */
.form-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: #ecf5ff;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #409eff;
}

/* 子页面 */
.sub-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  z-index: 100;
  display: flex;
  flex-direction: column;
}

/* 移动端：底部避开导航栏，输入栏落在可见区域 */
@media (max-width: 767px) {
  .sub-page {
    bottom: 56px;
    height: auto;
  }
}

/* 桌面端：顶部避开顶栏 */
@media (min-width: 768px) {
  .sub-page {
    top: 56px;
    height: calc(100% - 56px);
  }
}

.sub-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.back-btn {
  width: 36px;
  height: 36px;
  color: #333;
}

.sub-page-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a1a;
}

.sub-page-placeholder {
  width: 36px;
}

.sub-page-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.sub-form {
  background: #fff;
  border-radius: 16px;
  padding: 16px 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.sub-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.sub-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: #666;
  font-weight: 600;
  padding-bottom: 4px !important;
  line-height: 1.4;
}

/* 日期并排 */
.form-row {
  display: flex;
  gap: 10px;
}

.form-row-item {
  flex: 1;
}

/* ===== 统一输入控件：椭圆矩形填充式 ===== */
.sub-form :deep(.el-input__wrapper),
.sub-form :deep(.el-textarea__inner),
.sub-form :deep(.el-select__wrapper) {
  border-radius: 14px;
  background: #f5f7fa;
  box-shadow: none;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.sub-form :deep(.el-input__wrapper) {
  padding: 1px 14px;
}

.sub-form :deep(.el-input__inner) {
  height: 44px;
  line-height: 44px;
  font-size: 14px;
}

.sub-form :deep(.el-textarea__inner) {
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.6;
}

.sub-form :deep(.el-select__wrapper) {
  min-height: 44px;
  padding: 4px 14px;
}

.sub-form :deep(.el-select__placeholder),
.sub-form :deep(.el-select__selected-item) {
  font-size: 14px;
}

/* placeholder */
.sub-form :deep(.el-input__inner::placeholder),
.sub-form :deep(.el-textarea__inner::placeholder),
.sub-form :deep(.el-select__placeholder) {
  color: #b0b5c0;
  font-weight: 400;
}

/* 悬停 */
.sub-form :deep(.el-input__wrapper:hover),
.sub-form :deep(.el-textarea__inner:hover),
.sub-form :deep(.el-select__wrapper:hover) {
  background: #eef1f5;
}

/* 聚焦：白底 + 主色描边 */
.sub-form :deep(.el-input__wrapper.is-focus),
.sub-form :deep(.el-select__wrapper.is-focused) {
  background: #fff;
  box-shadow: 0 0 0 1.5px #409eff;
}

.sub-form :deep(.el-textarea__inner:focus) {
  background: #fff;
  box-shadow: 0 0 0 1.5px #409eff;
}

/* 前缀图标（日期选择等） */
.sub-form :deep(.el-input__prefix .el-icon),
.sub-form :deep(.el-select__caret) {
  color: #b0b5c0;
}

.sub-form :deep(.el-input__wrapper.is-focus .el-input__prefix .el-icon) {
  color: #409eff;
}

/* 数字输入框 */
.sub-form :deep(.el-input-number) {
  width: 100%;
}

.sub-form :deep(.el-input-number .el-input__wrapper) {
  padding-left: 44px;
  padding-right: 44px;
}

.sub-form :deep(.el-input-number__decrease),
.sub-form :deep(.el-input-number__increase) {
  width: 32px;
  color: #909399;
  background: transparent;
  border: none;
}

.sub-form :deep(.el-input-number__decrease:hover),
.sub-form :deep(.el-input-number__increase:hover) {
  color: #409eff;
}

/* 单选（失物招领类型）：胶囊卡片式 */
.sub-form :deep(.el-radio) {
  height: 40px;
  padding: 0 20px;
  margin-right: 10px;
  border-radius: 20px;
  background: #f5f7fa;
  border: none;
  transition: all 0.2s ease;
}

.sub-form :deep(.el-radio:hover) {
  background: #eef1f5;
}

.sub-form :deep(.el-radio.is-checked) {
  background: rgba(64,158,255,0.08);
  box-shadow: 0 0 0 1.5px #409eff inset;
}

.sub-form :deep(.el-radio__label) {
  font-size: 14px;
  color: #666;
}

.sub-form :deep(.el-radio.is-checked .el-radio__label) {
  color: #409eff;
  font-weight: 500;
}

.sub-page-footer {
  padding: 16px 0;
  margin-top: 8px;
}

.sub-page-footer .el-button {
  height: 44px;
  border-radius: 12px;
  font-size: 15px;
}

.empty-records {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: #c0c4cc;
  font-size: 14px;
}

/* 禁用弹窗所有过渡和动画 */
.detail-dialog :deep(.el-overlay),
.detail-dialog :deep(.el-dialog),
.detail-dialog :deep(.el-overlay-dialog),
.detail-dialog :deep(.el-dialog__wrapper) {
  transition: none !important;
  animation: none !important;
  transform: none !important;
}

.detail-dialog :deep(.el-dialog) {
  border-radius: 20px 20px 0 0;
  overflow: hidden;
  width: 100vw !important;
  max-width: 100vw;
  margin: 0;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  box-shadow: 0 -4px 24px rgba(0,0,0,0.15);
  transition: none !important;
  animation: none !important;
  transform: none !important;
}

.detail-dialog :deep(.el-dialog__header) {
  display: none;
}

.detail-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.detail-dialog :deep(.el-overlay) {
  background: rgba(0,0,0,0.4);
}

.sheet-handle {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: rgba(0,0,0,0.15);
  margin: 8px auto 0;
}

.detail-content {
  max-height: 70vh;
  overflow-y: auto;
  border-radius: 20px 20px 0 0;
  scrollbar-width: none;
}

.detail-content::-webkit-scrollbar {
  display: none;
}

/* 状态头部 */
.detail-hero {
  padding: 14px 16px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff;
}

.hero-pending {
  background: linear-gradient(135deg, #4f8ef7, #3b6dd4);
}

.hero-approved {
  background: linear-gradient(135deg, #67c23a, #529b2e);
}

.hero-rejected {
  background: linear-gradient(135deg, #f56c6c, #e04b4b);
}

.hero-cancelled {
  background: linear-gradient(135deg, #909399, #787b80);
}

.hero-status {
  flex-shrink: 0;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(255,255,255,0.25);
  letter-spacing: 0.3px;
}

.hero-title {
  font-size: 15px;
  font-weight: 700;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hero-time {
  font-size: 11px;
  opacity: 0.75;
  flex-shrink: 0;
}

/* 详情列表 */
.detail-body {
  padding: 4px 16px 8px;
}

.detail-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
  min-width: 56px;
  margin-right: 10px;
}

.detail-value {
  font-size: 13px;
  color: #303133;
  text-align: right;
  word-break: break-word;
  flex: 1;
  min-width: 0;
}

.detail-value-block {
  text-align: left;
  white-space: pre-wrap;
  line-height: 1.5;
  background: #f9fafb;
  padding: 6px 10px;
  border-radius: 6px;
  width: 100%;
  font-size: 13px;
}

.detail-row-reject {
  background: #fef2f2;
  margin: 4px -16px 0;
  padding: 8px 16px;
  border-radius: 0;
  border-bottom: none;
}

.detail-reject {
  color: #dc2626;
  font-weight: 500;
  font-size: 13px;
}

.attachment-link {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  text-decoration: none;
  font-size: 12px;
  margin-bottom: 2px;
}

.attachment-link:hover {
  text-decoration: underline;
}

.detail-cancel {
  padding: 6px 16px 14px;
  text-align: center;
}

/* 全部记录页面 */
.all-records-page {
  padding: 0;
}

.all-records-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 消息中心 */
.messages-page {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
}

/* 辅导员入口 */
.tutor-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border-bottom: 8px solid #f5f7fa;
  cursor: pointer;
}

.tutor-entry:active {
  background: #f5f7fa;
}

.tutor-entry-avatar {
  position: relative;
  flex-shrink: 0;
}

.tutor-entry-info {
  flex: 1;
}

.tutor-entry-name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  margin-bottom: 2px;
}

.tutor-entry-desc {
  font-size: 12px;
  color: #999;
}

.tutor-entry-arrow {
  color: #ccc;
  font-size: 14px;
}

/* 消息列表 */
.messages-list {
  max-height: 60vh;
  overflow-y: auto;
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: #999;
}

.empty-messages span {
  font-size: 14px;
}

.message-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.15s;
}

.message-item:active {
  background: #f5f7fa;
}

.message-avatar {
  position: relative;
  flex-shrink: 0;
}

.message-unread {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #f56c6c;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-info {
  flex: 1;
  min-width: 0;
}

.message-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.message-name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.message-time {
  font-size: 12px;
  color: #999;
  flex-shrink: 0;
}

.message-preview {
  font-size: 13px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 聊天页面模式 */
.chat-mode {
  background: #f5f7fa;
}

/* 聊天头部 */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.chat-header-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a1a;
  text-align: center;
  flex: 1;
}

.chat-header-placeholder {
  width: 36px;
}

/* 聊天内容区 */
.chat-content {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 聊天页面 */
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 0;
  color: #999;
}

.empty-chat span {
  font-size: 14px;
}

.chat-msg {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
}

.chat-msg.mine {
  align-items: flex-end;
}

.chat-msg.theirs {
  align-items: flex-start;
}

.chat-msg-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.chat-msg.mine .chat-msg-bubble {
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-msg.theirs .chat-msg-bubble {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.chat-msg-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  padding: 0 4px;
}

/* 聊天输入栏 */
.chat-input-bar {
  flex-shrink: 0;
  padding: 10px 16px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.chat-input-container {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  max-width: 100%;
  background: #f5f7fa;
  border-radius: 20px;
  padding: 6px 6px 6px 14px;
}

.chat-textarea {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  font-family: inherit;
  color: #333;
  resize: none;
  line-height: 1.5;
  padding: 4px 0;
  min-height: 20px;
  max-height: 80px;
  overflow-y: auto;
}

.chat-textarea::placeholder {
  color: #999;
}

.chat-textarea::-webkit-scrollbar {
  width: 0;
}

.chat-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #409eff;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s, transform 0.1s;
}

.chat-send-btn:hover:not(:disabled) {
  background: #337ecc;
}

.chat-send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.chat-send-btn:disabled {
  background: #c0c4cc;
  cursor: not-allowed;
}

/* 滑动动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(100%);
}

.slide-left-leave-to {
  transform: translateX(100%);
}
</style>
