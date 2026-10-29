<template>
  <div
    :class="['workbench-page', { 'msg-only': messagesOnly }]"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <!-- 主页面内容：messagesOnly（消息中心直达覆盖层）下不渲染——
         覆盖层背后不画一版隐藏的工作台，动画过程中露出的应是宿主页 -->
    <template v-if="!messagesOnly">
    <!-- 头部欢迎区（不参与下拉位移） -->
    <div class="workbench-header">
      <div class="header-bg-deco"></div>
      <div class="header-main">
        <div class="header-greeting">
          <div class="greeting-badge">
            <span class="badge-dot"></span>
            {{ siteName }} · 工作台
          </div>
          <div class="greeting-text">你好，{{ auth.userName }}</div>
          <div class="greeting-sub">今天想办理什么业务？</div>
        </div>
        <img :src="siteMascot" :alt="siteName" class="header-mascot" />
      </div>
    </div>

    <!-- 移动端下拉刷新：吉祥物指示器（与教师端首页 / 消息页共用同一模块） -->
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <!-- 我的事务 -->
    <div class="section-card">
      <div class="section-title">我的事务</div>
      <div class="my-affairs">
        <div class="affair-item" @click="router.push('/student/my-requests?tab=leave')">
          <div class="affair-ico" style="background:rgba(64,158,255,.1);color:#409eff;"><el-icon :size="20"><Calendar /></el-icon></div>
          <div class="affair-info"><b>我的申请</b><span>请假 / 证明 / 项目</span></div>
          <div class="affair-count" v-if="leaveRecords.length + tickets.length">{{ leaveRecords.length + tickets.length }}</div>
        </div>
        <div class="affair-item" @click="router.push('/student/my-requests?tab=ticket')">
          <div class="affair-ico" style="background:rgba(230,162,60,.1);color:#e6a23c;"><el-icon :size="20"><Tickets /></el-icon></div>
          <div class="affair-info"><b>我的工单</b><span>办事进度跟踪</span></div>
          <div class="affair-count" v-if="tickets.length">{{ tickets.length }}</div>
        </div>
        <div class="affair-item" @click="router.push('/student/materials')">
          <div class="affair-ico" style="background:rgba(103,194,58,.1);color:#67c23a;"><el-icon :size="20"><FolderOpened /></el-icon></div>
          <div class="affair-info"><b>材料档案</b><span>个人材料归档</span></div>
          <div class="affair-count" v-if="materialCount">{{ materialCount }}</div>
        </div>
      </div>
    </div>

    <!-- 办事服务 -->
    <div class="section-card">
      <div class="section-title">办事服务</div>
      <div class="service-grid">
        <div v-for="item in serviceItems" :key="item.key" class="service-item" @click="openService(item)">
          <div class="service-icon" :style="{ background: item.bgColor, color: item.color }">
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
          </div>
          <div class="service-label">{{ item.label }}</div>
        </div>
      </div>
    </div>

    <!-- 学习成长 -->
    <div class="section-card">
      <div class="section-title">学习成长</div>
      <div class="service-grid">
        <div v-for="item in resourceItems" :key="item.key" class="service-item" @click="openService(item)">
          <div class="service-icon" :style="{ background: item.bgColor, color: item.color }">
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
          </div>
          <div class="service-label">{{ item.label }}</div>
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
            <div class="contact-name">联系{{ agentName }}</div>
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
            <div class="contact-desc">群聊、私聊、辅导员、小绵管家</div>
          </div>
          <el-badge v-if="unreadCount" :value="unreadCount" class="contact-badge" />
          <el-icon class="contact-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="contact-item" @click="openAnnouncements">
          <div class="contact-icon" style="background: rgba(179,127,235,0.1); color: #b37feb;">
            <el-icon :size="20"><Bell /></el-icon>
          </div>
          <div class="contact-info">
            <div class="contact-name">班级公告</div>
            <div class="contact-desc">辅导员发布的班级通知</div>
          </div>
          <el-badge v-if="announceUnread" :value="announceUnread" class="contact-badge" />
          <el-icon class="contact-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="contact-item" @click="goFeedback">
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
    </template>

    <!-- 子页面：办事服务表单
         动画统一走 styles/subpage-transition.css 的 .subpage（覆盖式：子页从右滑入盖住列表，
         主页面不动；返回时原路滑出），不再在本文件自带一份 slide-left 定义。 -->
    <transition name="subpage" :duration="320" @after-leave="onSubpageAfterLeave">
      <div v-if="currentPage" :class="['sub-page', { 'chat-mode': isChatMode }]">
        <!-- 非聊天页面显示标准头部（移动端消息中心/搜索子页自带页签头，不套用标准头部） -->
        <div v-if="!isChatMode && !(isMobile && (currentPage === 'messages' || currentPage === 'mmsgSearch'))" class="sub-page-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="sub-page-title">{{ pageTitle }}</div>
          <button
            v-if="currentPage === 'notifications' && notifUnread"
            type="button"
            class="sub-page-action"
            @click="markAllStudentNotificationsRead"
          >
            全部已读
          </button>
          <div v-else class="sub-page-placeholder"></div>
        </div>

        <!-- 聊天页面显示简洁头部（单聊的「进对方主页」入口固定在右上角，与 QQ 一致） -->
        <div v-if="isChatMode" class="chat-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="chat-header-title">
            <el-avatar
              v-if="currentPage === 'tutor'"
              :size="26"
              :src="chatPartnerAvatar || undefined"
              class="chat-header-avatar"
            >{{ chatPartnerName?.[0] }}</el-avatar>
            <span class="chat-header-name">{{ chatHeaderTitle }}</span>
          </div>
          <button
            v-if="currentPage === 'tutor' && tutorIdRef"
            type="button"
            class="chat-header-action"
            title="查看对方主页"
            @click="openUserHomepage(tutorIdRef || 0)"
          >
            <el-icon :size="19"><Postcard /></el-icon>
          </button>
          <div v-else class="chat-header-placeholder"></div>
        </div>

        <div :class="['sub-page-content', { 'chat-content': isChatMode, 'msg-bleed': isMobile && (currentPage === 'messages' || currentPage === 'mmsgSearch') }]">
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
          <div v-if="currentPage === 'announcements'">
            <AnnouncementPanel @read="refreshAnnounceUnread" />
          </div>

          <!-- 消息中心（与搜索子页之间播 push 式覆盖动画，方向见 mmsgPageTransition） -->
          <Transition :name="mmsgPageTransition" :duration="mmsgPageTransition ? 320 : undefined">
          <div v-if="currentPage === 'messages'" key="messages" class="messages-page">
            <!-- 移动端：页签头（好友 / 消息）+ 快捷圆标 + 会话流（原侧边抽屉的二级入口改为圆标直达） -->
            <template v-if="isMobile">
              <div class="mmsg-header">
                <button type="button" class="mmsg-icon-btn" aria-label="返回" @click="closePage">
                  <DtIcon name="back" :size="22" />
                </button>
                <div class="mmsg-tabs">
                  <div :class="['mmsg-tab', { active: msgTab === 'friends' }]" @click="msgTab = 'friends'">好友</div>
                  <div :class="['mmsg-tab', { active: msgTab === 'messages' }]" @click="msgTab = 'messages'">消息</div>
                </div>
                <div class="mmsg-actions">
                  <button type="button" class="mmsg-icon-btn" aria-label="搜索" @click="openMsgSearch">
                    <el-icon :size="20"><Search /></el-icon>
                  </button>
                </div>
              </div>

              <!-- 消息页签：快捷入口 + 群聊与私聊混排的会话流 -->
              <template v-if="msgTab === 'messages'">
                <div class="mmsg-quick">
                  <div v-for="q in mmsgQuickEntries" :key="q.key" class="mmsg-quick-item" @click="gotoPage(q.page)">
                    <div class="mmsg-quick-icon" :style="{ background: q.bg, color: q.color }">
                      <DtIcon :name="q.icon" :size="26" :filled="q.filled" />
                    </div>
                    <span class="mmsg-quick-label">{{ q.label }}</span>
                  </div>
                  <!-- 第 4 格留白：对齐参考稿四宫格节奏（@我的 暂无对应能力，先留空） -->
                  <div class="mmsg-quick-item mmsg-quick-blank" aria-hidden="true"></div>
                </div>

                <div class="mmsg-list">
                  <div v-if="msgFeed.length === 0" class="empty-messages">
                    <DtIcon name="empty" :size="48" style="color: var(--dt-text-quiet);" />
                    <span>暂无消息</span>
                  </div>
                  <div v-for="row in msgFeed" :key="row.key" class="message-item" @click="openMsgRow(row)">
                    <div class="message-avatar">
                      <el-avatar :size="48" :src="row.avatar || undefined">{{ row.name?.[0] }}</el-avatar>
                      <span v-if="row.isGroup" class="mmsg-group-tag">群</span>
                      <div v-if="row.unread" class="message-unread">{{ row.unread > 99 ? '99+' : row.unread }}</div>
                      <span v-if="!row.isGroup && row.online" class="message-online-dot" title="在线" />
                    </div>
                    <div class="message-info">
                      <div class="message-top">
                        <span class="message-name">{{ row.name }}</span>
                        <DtIcon v-if="row.muted" name="bellOff" :size="13" class="muted-icon" />
                        <span class="message-time">{{ formatListTime(row.time) }}</span>
                      </div>
                      <div class="message-preview-row">
                        <span v-if="row.isGroup && row.onlineCount" class="message-online-count">{{ row.onlineCount }}人在线</span>
                        <span class="message-preview">{{ row.last || '暂无消息' }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 好友页签：有过会话的联系人，点头像看主页、点行进聊天 -->
              <template v-else>
                <div class="mmsg-list">
                  <div v-if="msgFriends.length === 0" class="empty-messages">
                    <DtIcon name="contacts" :size="48" style="color: var(--dt-text-quiet);" />
                    <span>暂无好友</span>
                  </div>
                  <div v-for="f in msgFriends" :key="f.user_id" class="message-item" @click="openConversation(f)">
                    <div class="message-avatar">
                      <el-avatar
                        :size="48"
                        :src="f.user_avatar || ''"
                        class="entry-avatar-clickable"
                        title="查看个人主页"
                        @click.stop="openUserHomepage(f.user_id)"
                      >{{ f.user_name?.[0] }}</el-avatar>
                      <span v-if="isOnline(f.user_id)" class="message-online-dot" title="在线" />
                    </div>
                    <div class="message-info">
                      <div class="message-top">
                        <span class="message-name">{{ f.user_name }}</span>
                      </div>
                      <div class="message-preview">{{ isOnline(f.user_id) ? '在线' : '' }}</div>
                    </div>
                  </div>
                </div>
              </template>
            </template>

            <!-- 桌面端：保持原有钉钉式结构（入口列表 + 群聊 + 会话） -->
            <template v-else>
            <!-- 小绵管家：置顶常驻会话（自动推送最新资讯 / 总结对话） -->
            <div class="tutor-entry butler-entry" @click="openButler">
              <div class="tutor-entry-avatar">
                <span class="butler-entry-avatar">
                  <img v-if="siteMascot" :src="siteMascot" alt="小绵管家" />
                  <span v-else>绵</span>
                </span>
                <span class="butler-entry-online" />
              </div>
              <div class="tutor-entry-info">
                <div class="tutor-entry-name">{{ agentName || '小绵' }}管家</div>
                <div class="tutor-entry-desc">{{ butlerPreview }}</div>
              </div>
              <span class="dt-tag">常驻</span>
              <DtIcon name="arrow" :size="16" class="tutor-entry-arrow" />
            </div>

            <!-- 通知：站内通知入口（审批 / 请假 / 公告 / 预警） -->
            <div class="tutor-entry" @click="openNotifications">
              <div class="tutor-entry-avatar">
                <span class="notice-entry-avatar"><DtIcon name="bell" :size="20" /></span>
              </div>
              <div class="tutor-entry-info">
                <div class="tutor-entry-name">通知</div>
                <div class="tutor-entry-desc">审批、请假、公告与预警提醒</div>
              </div>
              <el-badge v-if="notifUnread" :value="notifUnread > 99 ? '99+' : notifUnread" class="contact-badge" />
              <DtIcon name="arrow" :size="16" class="tutor-entry-arrow" />
            </div>

            <!-- 文件：跨会话文件汇总（各聊天里发送过的文件 / 图片 / 语音） -->
            <div class="tutor-entry" @click="openSharedFiles">
              <div class="tutor-entry-avatar">
                <span class="notice-entry-avatar"><DtIcon name="file" :size="20" /></span>
              </div>
              <div class="tutor-entry-info">
                <div class="tutor-entry-name">文件</div>
                <div class="tutor-entry-desc">各聊天里发送过的文件、图片与语音</div>
              </div>
              <DtIcon name="arrow" :size="16" class="tutor-entry-arrow" />
            </div>

            <!-- 我的关怀：教师端「人文关怀」的学生侧闭环（激励 / 关怀记录 / 家访记录） -->
            <div class="tutor-entry" @click="router.push('/student/care')">
              <div class="tutor-entry-avatar">
                <span class="notice-entry-avatar"><DtIcon name="heart" :size="20" /></span>
              </div>
              <div class="tutor-entry-info">
                <div class="tutor-entry-name">我的关怀</div>
                <div class="tutor-entry-desc">老师给的激励、关怀记录与家访留痕</div>
              </div>
              <DtIcon name="arrow" :size="16" class="tutor-entry-arrow" />
            </div>

            <!-- 辅导员入口 -->
            <div v-if="auth.user?.tutor_id" class="tutor-entry" @click="startTutorChat">
              <div class="tutor-entry-avatar">
                <el-avatar
                  :size="48"
                  class="entry-avatar-clickable"
                  title="查看辅导员主页"
                  @click.stop="openUserHomepage(auth.user?.tutor_id || 0)"
                  style="background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%); color: #fff; font-weight: 600;"
                >导</el-avatar>
              </div>
              <div class="tutor-entry-info">
                <div class="tutor-entry-name">我的辅导员</div>
                <div class="tutor-entry-desc">在线咨询、预约面谈</div>
              </div>
              <el-icon class="tutor-entry-arrow"><ArrowRight /></el-icon>
            </div>

            <!-- 群聊（已加入的群：扫码入群后出现在这里） -->
            <template v-if="myGroups.length">
              <div class="mcenter-section-head">
                <span class="mcenter-section-title">群聊</span>
                <span class="mcenter-section-count">{{ myGroups.length }} 个</span>
              </div>
              <div class="messages-list">
                <div v-for="g in myGroups" :key="g.id" class="message-item" @click="openGroupChat(g)">
                  <div class="message-avatar">
                    <el-avatar :size="48" :src="g.avatar || undefined">{{ g.name?.[0] }}</el-avatar>
                    <div v-if="g.unread_count" class="message-unread">{{ g.unread_count > 99 ? '99+' : g.unread_count }}</div>
                  </div>
                  <div class="message-info">
                    <div class="message-top">
                      <span class="message-name">{{ g.name }}</span>
                      <DtIcon v-if="g.is_muted" name="bellOff" :size="13" class="muted-icon" />
                      <span class="message-time">{{ formatDate(g.last_message_time || '') }}</span>
                    </div>
                    <div class="message-preview-row">
                      <span v-if="g.online_count" class="message-online-count">{{ g.online_count }}人在线</span>
                      <span class="message-preview">{{ g.last_message || '暂无消息' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <!-- 消息列表 -->
            <div class="messages-list">
              <div v-if="conversationList.length === 0" class="empty-messages">
                <DtIcon name="empty" :size="48" style="color: var(--dt-text-quiet);" />
                <span>暂无消息</span>
              </div>
              <div v-for="conv in conversationList" :key="conv.user_id" class="message-item" @click="openConversation(conv)">
                <div class="message-avatar">
                  <el-avatar
                    :size="48"
                    :src="conv.user_avatar || ''"
                    class="entry-avatar-clickable"
                    title="查看个人主页"
                    @click.stop="openUserHomepage(conv.user_id)"
                  >{{ conv.user_name?.[0] }}</el-avatar>
                  <div v-if="conv.unread_count" class="message-unread">{{ conv.unread_count > 99 ? '99+' : conv.unread_count }}</div>
                  <span v-if="isOnline(conv.user_id)" class="message-online-dot" title="在线" />
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
            </template>
          </div>

          <!-- 消息中心搜索子页：整页即搜索框（对齐参考稿）——空关键字整页留白，无结果居中「暂无内容」；
               结果行与消息流同构，返回清空关键字回消息中心，点结果进聊天后返回仍停留搜索页 -->
          <div v-else-if="isMobile && currentPage === 'mmsgSearch'" key="mmsgSearch" class="mmsg-search-page">
            <div class="msp-head">
              <button type="button" class="mmsg-icon-btn" aria-label="返回" @click="exitMsgSearch">
                <DtIcon name="back" :size="22" />
              </button>
              <div class="msp-field">
                <DtIcon name="search" :size="16" class="msp-field-icon" />
                <input
                  ref="mspInputRef"
                  v-model="msgKeyword"
                  type="text"
                  class="msp-input"
                  placeholder="搜索联系人或群聊"
                />
                <button v-if="msgKeyword" type="button" class="msp-clear" aria-label="清空" @click="clearMsgSearch">
                  <DtIcon name="close" :size="12" />
                </button>
              </div>
            </div>
            <div class="msp-body">
              <div v-if="msgKeyword.trim() && msgFeed.length" class="msp-result">
                <div v-for="row in msgFeed" :key="row.key" class="message-item" @click="openMsgRow(row)">
                  <div class="message-avatar">
                    <el-avatar :size="48" :src="row.avatar || undefined">{{ row.name?.[0] }}</el-avatar>
                    <span v-if="row.isGroup" class="mmsg-group-tag">群</span>
                    <div v-if="row.unread" class="message-unread">{{ row.unread > 99 ? '99+' : row.unread }}</div>
                    <span v-if="!row.isGroup && row.online" class="message-online-dot" title="在线" />
                  </div>
                  <div class="message-info">
                    <div class="message-top">
                      <span class="message-name">{{ row.name }}</span>
                      <DtIcon v-if="row.muted" name="bellOff" :size="13" class="muted-icon" />
                      <span class="message-time">{{ formatListTime(row.time) }}</span>
                    </div>
                    <div class="message-preview-row">
                      <span v-if="row.isGroup && row.onlineCount" class="message-online-count">{{ row.onlineCount }}人在线</span>
                      <span class="message-preview">{{ row.last || '暂无消息' }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else-if="msgKeyword.trim()" class="empty-messages">
                <DtIcon name="grid" :size="46" style="color: var(--dt-text-quiet);" />
                <span>暂无内容</span>
              </div>
            </div>
          </div>
          </Transition>

          <!-- 聊天页面 -->
          <div v-if="currentPage === 'tutor'" class="chat-page">
            <div class="chat-messages" ref="tutorMsgRef">
              <div v-if="tutorMessages.length === 0" class="empty-chat">
                <DtIcon name="empty" :size="48" style="color: var(--dt-text-quiet);" />
                <span>暂无消息，发送第一条消息吧</span>
              </div>
              <template v-for="item in tutorTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
                <div v-if="item.type === 'date'" class="chat-date-separator"><span>{{ item.label }}</span></div>
                <div v-else :class="['chat-msg', item.msg.sender_id === auth.user?.id ? 'mine' : 'theirs']">
                  <div class="chat-msg-bubble">{{ item.msg.content }}</div>
                </div>
              </template>
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

          <!-- 小绵管家会话（钉钉式）：自动推送最新资讯 / 总结对话内容 -->
          <div v-if="currentPage === 'butler'" class="chat-page butler-page">
            <ButlerChat role="student" />
          </div>

          <!-- 群聊会话（钉钉式）：群消息 + 发言 -->
          <div v-if="currentPage === 'group'" class="chat-page">
            <div class="chat-messages" ref="groupMsgRef">
              <div v-if="groupMessages.length === 0" class="empty-chat">
                <DtIcon name="empty" :size="44" style="color: var(--dt-text-quiet);" />
                <span>暂无消息，发送第一条消息吧</span>
              </div>
              <template v-for="item in groupTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
                <div v-if="item.type === 'date'" class="chat-date-separator"><span>{{ item.label }}</span></div>
                <div v-else :class="['chat-msg', item.msg.sender_id === auth.user?.id ? 'mine' : 'theirs']">
                  <div v-if="item.msg.sender_id !== auth.user?.id" class="chat-msg-sender">{{ item.msg.sender_name }}</div>
                  <div class="chat-msg-bubble">{{ item.msg.content }}</div>
                </div>
              </template>
            </div>
            <div class="chat-input-bar">
              <div class="chat-input-container">
                <textarea
                  v-model="groupNewMsg"
                  placeholder="输入消息..."
                  class="chat-textarea"
                  rows="1"
                  @keydown.enter.prevent="sendGroupMsg"
                ></textarea>
                <button type="button" class="chat-send-btn" :disabled="!groupNewMsg.trim()" @click="sendGroupMsg">
                  <el-icon :size="18"><Promotion /></el-icon>
                </button>
              </div>
            </div>
          </div>

          <!-- 通知列表（钉钉式列表行：未读点 + 标题/正文/时间） -->
          <div v-if="currentPage === 'notifications'" class="notif-page">
            <div v-if="notifLoading" class="empty-messages">
              <el-icon class="is-loading" :size="22"><Loading /></el-icon>
              <span>加载中…</span>
            </div>
            <div v-else-if="!notificationList.length" class="empty-messages">
              <DtIcon name="bell" :size="44" style="color: var(--dt-text-quiet);" />
              <span>暂无通知</span>
            </div>
            <template v-else>
              <button
                v-for="n in notificationList"
                :key="n.id"
                type="button"
                class="notif-row"
                :class="{ unread: !n.is_read }"
                @click="openStudentNotification(n)"
              >
                <span class="notif-dot" :class="{ hidden: n.is_read }" />
                <span class="notif-main">
                  <span class="notif-top">
                    <span class="notif-title">{{ n.title }}</span>
                    <span class="notif-time">{{ formatDate(n.created_at) }}</span>
                  </span>
                  <span class="notif-content">{{ n.content }}</span>
                </span>
              </button>
            </template>
          </div>

          <!-- 所有评论 / 赞和收藏 / 关注：互动流占位页 ——
               后端「与我互动」数据源就绪前先给整屏居中空态，接列表时只需替换本块内容 -->
          <div
            v-if="currentPage === 'myComments' || currentPage === 'myLikes' || currentPage === 'myFollows'"
            class="mmsg-interact-page"
          >
            <div class="empty-messages">
              <DtIcon
                :name="currentPage === 'myComments' ? 'message' : currentPage === 'myLikes' ? 'thumbUp' : 'user'"
                :size="44"
                style="color: var(--dt-text-quiet);"
              />
              <span>{{ currentPage === 'myComments' ? '暂无评论' : currentPage === 'myLikes' ? '暂无赞和收藏' : '暂无关注' }}</span>
              <span class="mmsg-empty-hint">同学与你互动后会出现在这里</span>
            </div>
          </div>

          <!-- 文件：跨会话文件汇总（各聊天里发送过的文件 / 图片 / 语音） -->
          <div v-if="currentPage === 'files'" class="files-page">
            <div class="files-head">
              <el-input v-model="fileKeyword" placeholder="搜索文件名" size="small" clearable @input="onFileSearch">
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <div class="files-filter">
                <button
                  v-for="f in FILE_TYPE_FILTERS"
                  :key="f.key"
                  type="button"
                  class="files-filter-item"
                  :class="{ active: fileTypeFilter === f.key }"
                  @click="setFileTypeFilter(f.key)"
                >{{ f.label }}</button>
              </div>
            </div>

            <div v-if="filesLoading" class="empty-messages">
              <el-icon class="is-loading" :size="22"><Loading /></el-icon>
              <span>加载中…</span>
            </div>
            <div v-else-if="!sharedFiles.length" class="empty-messages">
              <DtIcon name="file" :size="44" style="color: var(--dt-text-quiet);" />
              <span>{{ fileKeyword.trim() ? '未找到匹配的文件' : '暂无聊天文件' }}</span>
            </div>
            <template v-else>
              <div v-for="f in sharedFiles" :key="f.id" class="file-row" @click="openSharedFile(f)">
                <span class="file-row-thumb" :class="'t-' + f.file_type">
                  <img v-if="f.file_type === 'image'" :src="f.url" alt="" loading="lazy" />
                  <el-icon v-else :size="18">
                    <Microphone v-if="f.file_type === 'voice'" />
                    <Document v-else />
                  </el-icon>
                </span>
                <span class="file-row-main">
                  <span class="file-row-name">
                    <template v-if="f.file_type === 'voice'">语音消息 · {{ f.duration || 1 }}″</template>
                    <template v-else>{{ f.name || '未命名文件' }}</template>
                  </span>
                  <span class="file-row-meta">
                    <span class="file-row-source" @click.stop="openFileSession(f)">
                      {{ f.is_group ? '群 · ' : '' }}{{ f.session_name || '会话' }}
                    </span>
                    <span>{{ f.sender_name }}</span>
                    <span>{{ formatDate(f.created_at) }}</span>
                  </span>
                </span>
              </div>
            </template>
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
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { createLeave, getMyLeaves, deleteLeave } from '@/api/leave'
import { createTicket, getTickets, cancelTicket } from '@/api/service'
import { getLostFoundItems, createLostFoundItem, getLostFoundItem } from '@/api/lostFound'
import { getMyMaterials } from '@/api/material'
import { getConversations, getSharedFiles, type SharedFile } from '@/api/messages'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
// 群聊：扫码入群后学生端可在消息中心查看与发言
import {
  getGroups, getGroupMessages, sendGroupMessage, markGroupRead,
  type GroupOut, type GroupMessageOut,
} from '@/api/groups'
import { getStudentAnnouncements, getUnreadCount } from '@/api/announcement'
// 站内通知：审批 / 请假 / 公告 / 预警等事件，学生端在消息中心内查看
import {
  getNotifications, getNotificationCount, markNotificationsRead, markAllNotificationsRead,
  type Notification as NotificationItem,
} from '@/api/notification'
import { usePolling } from '@/composables/usePolling'
import AnnouncementPanel from '@/components/announcement/AnnouncementPanel.vue'
import UploadBtn from '@/components/upload/UploadBtn.vue'
// 小绵管家：教师端与学生端共用的常驻会话（自动推送资讯 + 总结对话）
import ButlerChat from '@/components/butler/ButlerChat.vue'
// 钉钉风格图标（对齐钉钉设计的组件图案）
import DtIcon from '@/components/common/DtIcon.vue'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useButlerPreview } from '@/composables/useButlerPreview'
// 下拉刷新（移动端）：手势逻辑与吉祥物指示器与教师端首页 / 消息页共用同一模块
import { useResponsive } from '@/composables/useResponsive'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import {
  Calendar, Document, Promotion, ChatDotRound,
  ArrowRight, ArrowLeft, Search,
  InfoFilled, Location, Close, Bell, Collection, Tickets, FolderOpened, Loading, Microphone, Postcard, Message
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isMobile } = useResponsive()

// 消息中心直达模式：被其他页面（校园资讯页头信封）当全屏覆盖层挂载。
// 本体不渲染、不涂背景，子页(固定定位)直接盖在宿主页上；路由不切换、底部页签不动，
// 子页滑出动画播完后 emit closed，由宿主卸载覆盖层。
const props = defineProps<{ messagesOnly?: boolean }>()
const emit = defineEmits<{ (e: 'closed'): void }>()

// 吉祥物与站点名称取自站点配置：管理端变更后学生端同步
const { siteMascot, siteName, agentName } = useSiteConfig()
// 小绵管家入口的动态摘要（取最新一条资讯标题）
const { butlerPreview, refreshButlerPreview } = useButlerPreview()

const currentPage = ref<string | null>(null)
// 子页返回栈：消息中心 → 通知/文件/聊天 等二级跳转时压栈，
// 返回键逐级回退（如 通知 → 消息中心 → 最外层），而不是一退就到底
const subpageStack = ref<string[]>([])

/** 子页跳转：已打开某子页时再进新子页，把当前页压入返回栈 */
function gotoPage(page: string) {
  // 仅 消息中心 → 搜索子页 播 push 动画；跳往聊天/通知等其余页面时瞬时切换
  mmsgPageTransition.value = currentPage.value === 'messages' && page === 'mmsgSearch' ? 'mmsg-cover' : ''
  if (currentPage.value) subpageStack.value.push(currentPage.value)
  currentPage.value = page
}
// 移动端消息中心（TapTap 式）：页签 / 整页搜索
const msgTab = ref<'messages' | 'friends'>('messages')
const msgKeyword = ref('')
/** 消息中心 ↔ 搜索子页的过渡方向名：前进 cover / 返回 cover-back，其余页面切换置空瞬时过渡 */
const mmsgPageTransition = ref('')
const submitting = ref(false)
const showDetail = ref(false)
const currentDetail = ref<any>(null)
const unreadCount = ref(0)
const announceUnread = ref(0)
const lostfoundTab = ref<'browse' | 'publish'>('browse')

const leaveRecords = ref<any[]>([])
const tickets = ref<any[]>([])
const materialCount = ref(0)
const materialList = ref<any[]>([])
const lostfoundItems = ref<any[]>([])
const lostfoundDetail = ref<any>(null)
const lostfoundDetailVisible = ref(false)
const conversationList = ref<any[]>([])

// 在线状态（布局层全局 WebSocket 维护）：单聊绿点实时刷新，群聊在线人数需服务端聚合
const { isOnline, syncPresence, presenceTick } = useUnreadSummary()
watch(presenceTick, () => { loadMyGroups() })
const tutorMessages = ref<any[]>([])
const tutorIdRef = ref<number | null>(null)
const tutorNewMsg = ref('')

// 办事服务配置（仅办事类，其余功能归类到驾驶舱/学习成长）
const serviceItems = [
  { key: 'leave', label: '请假申请', icon: Calendar, color: '#409eff', bgColor: 'rgba(64,158,255,0.1)' },
  { key: 'certificate', label: '证明申请', icon: Document, color: '#67c23a', bgColor: 'rgba(103,194,58,0.1)' },
  { key: 'project', label: '项目申请', icon: Promotion, color: '#e6a23c', bgColor: 'rgba(230,162,60,0.1)' },
  { key: 'lostfound', label: '失物招领', icon: Search, color: '#f56c6c', bgColor: 'rgba(245,108,108,0.1)' },
]

// 学习成长配置
const resourceItems = [
  { key: 'resources', label: 'AI 资源空间', icon: Collection, color: '#13c2c2', bgColor: 'rgba(19,194,194,0.1)', link: '/student/resources' },
  { key: 'community', label: '交流社区', icon: ChatDotRound, color: '#722ed1', bgColor: 'rgba(114,46,209,0.1)', link: '/student/community' },
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
const lostfoundForm = reactive({ type: 'lost', title: '', description: '', location: '', contact: '' })

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    leave: '请假申请',
    certificate: '证明申请',
    project: '项目申请',
    lostfound: '失物招领',
    messages: '消息中心',
    notifications: '通知',
    files: '文件',
    myComments: '所有评论',
    myLikes: '赞和收藏',
    myFollows: '关注',
    allRecords: '全部申请',
    announcements: '班级公告'
  }
  return titles[currentPage.value || ''] || ''
})

/** 从搜索结果发起的单聊对象（不在会话列表时的头部名称/头像兜底） */
const chatPartnerOverride = ref<{ name: string; avatar: string } | null>(null)

// 聊天对象名称
const chatPartnerName = computed(() => {
  // 搜索发起的会话对象尚未进会话列表：用 override 撑起头部，列表回填后值一致
  if (chatPartnerOverride.value) return chatPartnerOverride.value.name
  if (tutorIdRef.value) {
    const conv = conversationList.value.find(c => c.user_id === tutorIdRef.value)
    if (conv) return conv.user_name
  }
  return '辅导员'
})

/** 单聊头部头像：优先取会话里的头像，落不到就交给 el-avatar 的姓名首字兜底 */
const chatPartnerAvatar = computed(() => {
  if (chatPartnerOverride.value) return chatPartnerOverride.value.avatar
  if (!tutorIdRef.value) return ''
  const conv = conversationList.value.find(c => c.user_id === tutorIdRef.value)
  return conv?.user_avatar || ''
})

const chatTextareaRef = ref<HTMLTextAreaElement>()

// 聊天态页面：辅导员私聊 + 小绵管家会话 + 群聊共用聊天布局
const isChatMode = computed(
  () => currentPage.value === 'tutor' || currentPage.value === 'butler' || currentPage.value === 'group'
)
const chatHeaderTitle = computed(() => {
  if (currentPage.value === 'butler') return `${agentName.value || '小绵'}管家`
  if (currentPage.value === 'group') return groupActive.value?.name || '群聊'
  return chatPartnerName.value
})

// ===== 群聊（加入的群；扫码入群后在此查看） =====
const myGroups = ref<GroupOut[]>([])
const groupMessages = ref<GroupMessageOut[]>([])
const groupNewMsg = ref('')
const groupActive = ref<GroupOut | null>(null)
const groupMsgRef = ref<HTMLElement>()

async function loadMyGroups() {
  try {
    myGroups.value = await getGroups()
  } catch {
    myGroups.value = []
  }
}

function scrollGroupToBottom() {
  const el = groupMsgRef.value
  if (el) el.scrollTop = el.scrollHeight
}

async function openGroupChat(g: GroupOut) {
  groupActive.value = g
  gotoPage('group')
  try {
    groupMessages.value = await getGroupMessages(g.id)
    markGroupRead(g.id).catch(() => {})
    g.unread_count = 0
  } catch {
    groupMessages.value = []
  }
  await nextTick()
  scrollGroupToBottom()
}

async function sendGroupMsg() {
  const text = groupNewMsg.value.trim()
  const g = groupActive.value
  if (!text || !g) return
  try {
    await sendGroupMessage(g.id, text)
    groupMessages.value.push({
      id: Date.now(),
      group_id: g.id,
      sender_id: auth.user?.id ?? 0,
      sender_name: auth.userName || '我',
      sender_avatar: null,
      content: text,
      created_at: new Date().toISOString(),
    })
    groupNewMsg.value = ''
    await nextTick()
    scrollGroupToBottom()
  } catch {
    ElMessage.error('发送失败')
  }
}

/** 打开小绵管家会话：自动推送最新资讯 / 总结对话内容 */
function openButler() {
  gotoPage('butler')
}

// ===== 站内通知（学生端消息中心的「通知」子页，闭环：列表 → 已读 → 跳转） =====
const notificationList = ref<NotificationItem[]>([])
const notifLoading = ref(false)
const notifUnread = ref(0)

async function loadNotifUnread() {
  try {
    const r = await getNotificationCount()
    notifUnread.value = r.unread ?? 0
  } catch { /* 网络异常时保持 0，不影响页面 */ }
}

/* ===== 文件：跨会话文件汇总（各聊天里发送过的文件 / 图片 / 语音，服务端聚合） ===== */
const sharedFiles = ref<SharedFile[]>([])
const filesLoading = ref(false)
const fileKeyword = ref('')
const fileTypeFilter = ref<'' | 'file' | 'image' | 'voice'>('')
let fileSearchTimer: ReturnType<typeof setTimeout> | null = null

const FILE_TYPE_FILTERS = [
  { key: '' as const, label: '全部' },
  { key: 'image' as const, label: '图片' },
  { key: 'file' as const, label: '文档' },
  { key: 'voice' as const, label: '语音' },
]

async function openSharedFiles() {
  gotoPage('files')
  await loadSharedFiles()
}

async function loadSharedFiles() {
  if (filesLoading.value) return
  filesLoading.value = true
  try {
    const params: { keyword?: string; file_type?: string } = {}
    const kw = fileKeyword.value.trim()
    if (kw) params.keyword = kw
    if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
    const res = await getSharedFiles(params)
    sharedFiles.value = res.items || []
  } catch {
    sharedFiles.value = []
  } finally {
    filesLoading.value = false
  }
}

function onFileSearch() {
  if (fileSearchTimer) clearTimeout(fileSearchTimer)
  fileSearchTimer = setTimeout(() => { void loadSharedFiles() }, 300)
}

function setFileTypeFilter(key: '' | 'file' | 'image' | 'voice') {
  fileTypeFilter.value = key
  loadSharedFiles()
}

/** 打开文件：图片新窗口预览，其余直接下载 */
function openSharedFile(f: SharedFile) {
  const a = document.createElement('a')
  a.href = f.url
  a.rel = 'noopener'
  if (f.file_type === 'image') a.target = '_blank'
  else a.download = f.name || '文件'
  a.click()
}

/** 点击来源会话 → 跳到对应聊天 */
async function openFileSession(f: SharedFile) {
  const targetId = Number(f.session_key.slice(2))
  if (f.is_group) {
    const g = myGroups.value.find((x) => x.id === targetId)
    if (!g) { ElMessage.info('该群聊已不在你的群列表中'); return }
    await openGroupChat(g)
  } else {
    currentPage.value = 'tutor'
    await loadTutorChat(targetId)
  }
}

async function openNotifications() {
  gotoPage('notifications')
  notifLoading.value = true
  try {
    notificationList.value = await getNotifications({ page_size: 50 })
    notifUnread.value = notificationList.value.filter(n => !n.is_read).length
  } catch {
    notificationList.value = []
  } finally {
    notifLoading.value = false
  }
}

async function openStudentNotification(n: NotificationItem) {
  if (!n.is_read) {
    try {
      await markNotificationsRead([n.id])
      n.is_read = true
      notifUnread.value = Math.max(0, notifUnread.value - 1)
    } catch { /* 标记失败不阻断跳转 */ }
  }
  if (n.link) {
    router.push(n.link)
  } else {
    ElMessage.info(n.content || '该通知暂无关联页面')
  }
}

async function markAllStudentNotificationsRead() {
  if (!notifUnread.value) return
  try {
    await markAllNotificationsRead()
    notificationList.value = notificationList.value.map(n => ({ ...n, is_read: true }))
    notifUnread.value = 0
  } catch {
    ElMessage.error('操作失败')
  }
}

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

// 时间解析：后端返回的是「无时区的 UTC 时间串」（如 2025-10-16T02:30:00），
// 直接 new Date() 会被当成本地时间而整体偏移；与教师端消息页保持一致，
// 无时区后缀则补 Z 按 UTC 解析，再以本地时区展示。
function parseTime(iso: string): Date {
  return new Date(iso + (iso.includes('Z') || iso.includes('+') ? '' : 'Z'))
}

function formatDate(iso: string) {
  if (!iso) return ''
  const d = parseTime(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// 聊天时间线：按「本地日期」在消息之间插入日期分隔线（与教师端消息页一致），
// 消息本身不再逐条显示时间，时间归属由分隔线表达。
function getDateStr(t: string) { const d = parseTime(t); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` }
function getDateLabel(t: string) {
  const date = parseTime(t); const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.round((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function buildTimeline(list: any[]) {
  const items: Array<{ type: 'date'; date: string; label: string } | { type: 'msg'; msg: any }> = []
  let lastDate = ''
  for (const m of list) {
    const d = getDateStr(m.created_at)
    if (d !== lastDate) { items.push({ type: 'date', date: d, label: getDateLabel(m.created_at) }); lastDate = d }
    items.push({ type: 'msg', msg: m })
  }
  return items
}

const tutorTimeline = computed(() => buildTimeline(tutorMessages.value))
const groupTimeline = computed(() => buildTimeline(groupMessages.value))

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

function openService(item: { key: string; link?: string }) {
  if (item.link) {
    router.push(item.link)
    return
  }
  currentPage.value = item.key
  if (item.key === 'lostfound') loadLostFound()
}

function openChat() {
  router.push('/student')
}

function openMessages() {
  // 消息已独立成底部页签（/student/messages）：工作台里的「消息中心」入口改为跳转过去，
  // 不再在这里打开旧版子页，避免同一功能出现两套界面。
  // 下方 currentPage === 'messages' 分支仅作历史深链（?messages=1 / ?chat=）的兜底保留。
  router.push('/student/messages')
}

// ===== 移动端消息中心（TapTap 式）：快捷圆标 / 会话流 / 好友页签 =====
/** 快捷圆标：互动流入口（对齐参考稿：所有评论 / 赞和收藏 / 关注 / 留白）。
    图标用实心形态（filled，对齐参考稿的实心圆标）；后端暂无「与我互动」通知流，
    先落整屏居中空态页，数据源就绪后把页内列表接上即可 */
const mmsgQuickEntries = computed(() => [
  { key: 'myComments', label: '所有评论', icon: 'message', bg: '#eceefe', color: '#6d7cf5', page: 'myComments', filled: true },
  { key: 'myLikes', label: '赞和收藏', icon: 'thumbUp', bg: '#e8f1ff', color: '#4a7dfc', page: 'myLikes', filled: true },
  { key: 'myFollows', label: '关注', icon: 'user', bg: '#f1ecfe', color: '#9b7df0', page: 'myFollows', filled: true },
])

interface MsgFeedRow {
  key: string
  isGroup: boolean
  id: number
  name: string
  avatar: string | null
  last: string
  time: string | null
  unread: number
  muted: boolean
  online: boolean
  onlineCount: number
}

function rowTime(ts: string | null) {
  return ts ? parseTime(ts).getTime() : 0
}

/** 群聊 + 私聊混排的会话流（按最后消息时间倒序），搜索行关键字过滤名称 */
const msgFeed = computed<MsgFeedRow[]>(() => {
  const kw = msgKeyword.value.trim().toLowerCase()
  const rows: MsgFeedRow[] = [
    ...myGroups.value.map((g) => ({
      key: `g-${g.id}`, isGroup: true, id: g.id, name: g.name, avatar: g.avatar,
      last: g.last_message, time: g.last_message_time, unread: g.unread_count || 0,
      muted: !!g.is_muted, online: false, onlineCount: g.online_count || 0,
    })),
    ...conversationList.value.map((c: any) => ({
      key: `s-${c.user_id}`, isGroup: false, id: c.user_id, name: c.user_name, avatar: c.user_avatar,
      last: c.last_message, time: c.last_message_time, unread: c.unread_count || 0,
      muted: false, online: !!c.online, onlineCount: 0,
    })),
  ]
  const filtered = kw ? rows.filter((r) => r.name.toLowerCase().includes(kw)) : rows
  return filtered.sort((a, b) => rowTime(b.time) - rowTime(a.time))
})

/** 好友页签：有过会话的联系人（本应用无独立好友实体，会话对象即联系人） */
const msgFriends = computed(() => conversationList.value)

function openMsgRow(row: MsgFeedRow) {
  if (row.isGroup) {
    const g = myGroups.value.find((x) => x.id === row.id)
    if (g) void openGroupChat(g)
  } else {
    const conv = conversationList.value.find((c: any) => c.user_id === row.id)
    openConversation(conv || { user_id: row.id, user_name: row.name })
  }
}

// ===== 搜索子页：整页搜索（对齐参考稿），每次进入从空关键字开始并自动聚焦 =====
const mspInputRef = ref<HTMLInputElement>()

function openMsgSearch() {
  msgKeyword.value = ''
  gotoPage('mmsgSearch')
  nextTick(() => mspInputRef.value?.focus())
}

function exitMsgSearch() {
  msgKeyword.value = ''
  closePage()
}

function clearMsgSearch() {
  msgKeyword.value = ''
  mspInputRef.value?.focus()
}
/** 列表时间：今天只显示时分，昨天带「昨天」前缀，今年显示月-日，往年带年份 */
function formatListTime(iso: string | null) {
  if (!iso) return ''
  const d = parseTime(iso)
  const now = new Date()
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (sameDay(d, now)) return hm
  if (sameDay(d, new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1))) return `昨天${hm}`
  if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}-${d.getDate()}`
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
}

function openAllRecords() {
  currentPage.value = 'allRecords'
}

function openAnnouncements() {
  currentPage.value = 'announcements'
}

async function loadConversations() {
  try {
    const convs = await getConversations()
    conversationList.value = convs as any
    // 用会话列表返回的在线初值回填在线映射
    syncPresence((convs as any[]).map((c) => ({ user_id: c.user_id, online: !!c.online })))
  } catch {
    conversationList.value = []
  }
}

function openConversation(conv: any) {
  // 打开与指定用户的聊天
  chatPartnerOverride.value = null
  gotoPage('tutor')
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
  chatPartnerOverride.value = null
  gotoPage('tutor')
  loadTutorChat(tutorId)
}

async function loadTutorChat(tutorId: number) {
  try {
    const { getMessages, markRead } = await import('@/api/messages')
    const msgs = await getMessages(tutorId)
    tutorMessages.value = msgs as any
    tutorIdRef.value = tutorId
    // 打开会话即标记已读，并清零列表未读角标（此前打开会话后红点不清）
    await markRead(tutorId)
    const conv = conversationList.value.find(c => c.user_id === tutorId)
    if (conv && conv.unread_count) {
      unreadCount.value = Math.max(0, unreadCount.value - conv.unread_count)
      conv.unread_count = 0
    }
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

function goFeedback() {
  router.push('/student/profile?page=feedback')
}

function closePage() {
  // 有上级子页：先逐级回退（如 通知 → 消息中心），列表与数据仍留在内存里
  if (subpageStack.value.length) {
    const prev = subpageStack.value.pop() as string
    // 搜索子页 → 消息中心：播原路滑出的返回动画
    mmsgPageTransition.value = currentPage.value === 'mmsgSearch' && prev === 'messages' ? 'mmsg-cover-back' : ''
    currentPage.value = prev
    return
  }
  mmsgPageTransition.value = ''
  currentPage.value = null
  showDetail.value = false
  currentDetail.value = null
  lostfoundDetailVisible.value = false
  lostfoundDetail.value = null
}

/** messagesOnly：子页滑出动画播完再卸载覆盖层，避免打断返回动画 */
function onSubpageAfterLeave() {
  if (props.messagesOnly) emit('closed')
}

function viewDetail(record: any) {
  currentDetail.value = record
  showDetail.value = true
}

// ─── 班级公告未读提醒 ─────────────────────────────────────
async function refreshAnnounceUnread() {
  try {
    const { count } = await getUnreadCount()
    announceUnread.value = count
  } catch { /* ignore */ }
}

/** 拉取未读公告并弹窗提醒（不自动标记已读） */
async function checkUnreadAnnouncements() {
  let count = 0
  let items: any[] = []
  try {
    const res = await getUnreadCount()
    count = res.count
    if (count > 0) items = (await getStudentAnnouncements(true)) as any
  } catch { return }
  announceUnread.value = count
  if (count > 0 && items.length > 0) {
    showAnnounceAlert(items)
  }
}

function announceUrgencyLabel(u: string) {
  const map: Record<string, string> = { urgent: '紧急', important: '重要', normal: '普通' }
  return map[u] || '普通'
}

function showAnnounceAlert(items: any[]) {
  // 分级提醒：普通公告只计红点不弹窗；重要 → 非阻塞提示；紧急 → 阻塞式强提醒（置顶）
  const notable = items.filter((a: any) => a.urgency !== 'normal')
  if (!notable.length) return
  const sorted = [...notable].sort(
    (a: any, b: any) => (a.urgency === 'urgent' ? 0 : 1) - (b.urgency === 'urgent' ? 0 : 1)
  )
  const urgentCount = sorted.filter((a: any) => a.urgency === 'urgent').length
  if (!urgentCount) {
    // 仅重要：轻提示 + 红点，不打断操作
    ElMessage.warning({
      message: `辅导员发布了 ${sorted.length} 条重要公告，可前往「班级公告」查看`,
      duration: 6000,
    })
    return
  }
  const msg = sorted.slice(0, 5).map((a: any) => `[${announceUrgencyLabel(a.urgency)}] ${a.title}`).join('\n')
  ElMessageBox.alert(msg, `紧急公告（${urgentCount} 条）`, {
    confirmButtonText: '查看公告',
    type: 'warning',
    dangerouslyUseHTMLString: false,
  }).then(() => {
    currentPage.value = 'announcements'
  }).catch(() => {})
}

/** 停留期间轮询：未读数增加时按级别分级提醒（紧急阻塞 / 重要轻提示 / 普通仅红点） */
let lastAnnounceUnread = 0
const announcePolling = usePolling(async () => {
  try {
    const { count } = await getUnreadCount()
    if (count > lastAnnounceUnread) {
      announceUnread.value = count
      const items = (await getStudentAnnouncements(true).catch(() => [])) as any[]
      const notable = items.filter((a: any) => a.urgency !== 'normal')
      const urgent = notable.filter((a: any) => a.urgency === 'urgent')
      if (urgent.length) {
        ElMessageBox.alert(
          urgent.map((a: any) => `【${a.title}】`).join('\n'),
          '紧急公告',
          { confirmButtonText: '查看公告', type: 'warning', dangerouslyUseHTMLString: false }
        ).then(() => {
          currentPage.value = 'announcements'
        }).catch(() => {})
      } else if (notable.length) {
        ElMessage.warning({
          message: `辅导员发布了 ${notable.length} 条重要公告`,
          duration: 6000,
        })
      }
      // 普通公告：只更新红点计数，不打断
    } else {
      announceUnread.value = count
    }
    lastAnnounceUnread = count
  } catch { /* ignore */ }
}, 30000)

async function loadData() {
  try {
    const [leaves, ticketList] = await Promise.all([getMyLeaves(), getTickets()])
    leaveRecords.value = leaves as any
    tickets.value = ticketList as any
  } catch {}

  try {
    materialList.value = (await getMyMaterials()) as any
    materialCount.value = materialList.value.length
  } catch {}

  checkUnreadAnnouncements()

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
  void refreshButlerPreview()
  void loadNotifUnread()
  void loadMyGroups()
  announcePolling.start()
  // 从他人个人主页的「发消息 / 加为好友」跳转而来：直接进消息中心并打开会话，可带预填草稿
  openFromHomepageQuery()
  // 直达覆盖层：挂载即进消息中心（宿主页路由不变）
  if (props.messagesOnly) {
    currentPage.value = 'messages'
    void loadConversations()
  }
})

/**
 * 打开站内其他页面带 query 直达的入口：
 * - ?messages=1：消息中心直达（校园资讯页头信封）
 * - ?chat=<id>：个人主页「发消息 / 加为好友」跳来，直接进消息中心并打开会话，可带预填草稿
 * 已在工作台时再次跳转不会重挂载组件（同路由只换 query），因此除 onMounted 外还需要 watch 兜底。
 */
function openFromHomepageQuery() {
  const chatId = Number(route.query.chat || 0)
  if (!chatId && !route.query.messages) return
  currentPage.value = 'messages'
  subpageStack.value = []
  if (chatId) {
    openConversation({ user_id: chatId, user_name: (route.query.chatName as string) || '' })
    // 会话列表可能还没有这条会话：用 query 里的名字撑起聊天头部
    if (route.query.chatName) chatPartnerOverride.value = { name: String(route.query.chatName), avatar: '' }
    if (route.query.draft) tutorNewMsg.value = String(route.query.draft)
  } else {
    msgTab.value = 'messages'
  }
  // 会话列表不随 loadData 拉，直达时必须补一次，否则消息流是空的
  void loadConversations()
  router.replace({ query: {} })
}

watch(
  () => [route.query.chat, route.query.messages],
  ([chat, messages]) => { if (chat || messages) openFromHomepageQuery() },
)

/** 下拉刷新：并行重拉工作台数据（事务 / 材料 / 未读 / 管家摘要 / 群组），静默更新不触发加载态 */
async function refreshAll() {
  await Promise.all([
    loadData(),
    refreshButlerPreview(),
    loadNotifUnread(),
    loadMyGroups(),
  ]).catch(() => {})
}

// 下拉刷新（移动端）：桌面端不响应手势；指示器复用消息页的吉祥物起跳动画
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })
</script>

<style scoped>
.workbench-page {
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
  /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
  overscroll-behavior-y: contain;
}

/* messagesOnly（消息中心直达覆盖层）：本体不占位、不涂背景——
   子页(固定定位)直接盖在宿主页上，返回动画露出的也是宿主页而不是隐藏的工作台 */
.workbench-page.msg-only {
  height: 0;
  overflow: visible;
  background: transparent;
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

/* 首张卡片上移压住头部下沿（下拉刷新指示器是无高度的一层，需一并写进相邻选择器） */
.workbench-header + .ptr-ind + .section-card {
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

.my-affairs { display: flex; flex-direction: column; gap: 10px; }
.affair-item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; background: #fbfcff; border: 1px solid rgba(64,158,255,.08); border-radius: 12px; cursor: pointer; transition: transform .15s; }
.affair-item:active { transform: scale(.98); }
.affair-ico { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.affair-info { flex: 1; min-width: 0; }
.affair-info b { display: block; font-size: 15px; color: #1a1a2e; }
.affair-info span { font-size: 12px; color: #909399; }
.affair-count { min-width: 22px; height: 22px; padding: 0 7px; border-radius: 11px; background: rgba(64,158,255,.1); color: #409eff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; }

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

/* 移动端：整屏覆盖（与资讯搜索/详情子页同一形式）——
   滑入/滑出时连底部导航一起盖住，返回走子页自己的返回按钮。
   z-index 1500：盖过底部导航(1000)，低于 Element Plus 弹层基准(2000+)，
   表单里的日期选择/下拉等弹出层仍浮在子页之上。 */
@media (max-width: 767px) {
  .sub-page {
    z-index: 1500;
    /* 显式高度：为内部 chat-page / 消息列表的百分比与 flex 高度提供确定基准，
       否则 position:fixed + height:auto 会让嵌套滚动区失去高度约束而无法滚动 */
    height: 100%;
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
  position: relative;
  z-index: 2;
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
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
}

/* 移动端消息中心：去内边距整屏出血（页签头吸顶、列表通栏） */
.sub-page-content.msg-bleed {
  padding: 0;
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

/* 消息中心（钉钉式：分组卡片 + 56/64px 列表行） */
.messages-page {
  background: var(--dt-surface);
  border-radius: var(--dt-radius);
  overflow: hidden;
}

/* 辅导员入口 */
.tutor-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--dt-surface);
  border-bottom: 8px solid var(--dt-bg);
  cursor: pointer;
}

.tutor-entry:active {
  background: var(--dt-surface-press);
}

.tutor-entry-avatar {
  position: relative;
  flex-shrink: 0;
}

.tutor-entry-info {
  flex: 1;
  min-width: 0;
}

.tutor-entry-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--dt-text);
  margin-bottom: 2px;
}

.tutor-entry-desc {
  font-size: 12.5px;
  color: var(--dt-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tutor-entry-arrow {
  color: var(--dt-text-quiet);
  font-size: 14px;
}

/* ===== 小绵管家：置顶常驻会话（钉钉式） ===== */
.butler-entry {
  background: linear-gradient(180deg, var(--dt-primary-soft), #fff 82%);
}

.butler-entry:active {
  background: var(--dt-primary-soft);
}

.butler-entry .tutor-entry-name {
  font-weight: 600;
}

.butler-entry .dt-tag {
  flex-shrink: 0;
  margin-right: 6px;
}

.butler-entry-avatar {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--dt-primary-soft);
  color: var(--dt-primary-strong);
  font-weight: 600;
}

.butler-entry-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.butler-entry-online {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--dt-success);
  border: 2px solid #fff;
}

.butler-page {
  background: var(--dt-bg);
}

/* 移动端：消息中心整屏出血（页签头 / 快捷圆标 / 会话流通栏，无卡片圆角）；
   overflow 放开，让吸顶页签头贴着 .sub-page-content 这个滚动容器工作 */
@media (max-width: 767px) {
  .messages-page {
    overflow: visible;
    border-radius: 0;
    /* 会话很少时页面只有内容高，下方会露出 .sub-page 的灰底（左灰右白的穿帮）——
       撑满整屏白底，任何内容量/动画中间态下都不再露灰 */
    min-height: 100%;
  }

  /* 空态提示整屏居中（含页签头/快捷圆标高度）；快捷圆标保持可点 */
  .mmsg-quick {
    position: relative;
    z-index: 2;
  }

  .mmsg-list .empty-messages {
    position: absolute;
    inset: 0;
    z-index: 1;
  }
}

/* ===== 消息中心：分组小标题 / 群聊补充样式 ===== */
.mcenter-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 6px;
  background: var(--dt-surface);
}

.mcenter-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--dt-text-tertiary);
}

.mcenter-section-count {
  font-size: 12px;
  color: var(--dt-text-quiet);
}

.muted-icon {
  color: var(--dt-text-quiet);
  flex-shrink: 0;
  margin-left: auto;
}

.chat-msg-sender {
  font-size: 11.5px;
  color: var(--dt-text-quiet);
  margin-bottom: 4px;
  padding: 0 4px;
}

/* ===== 通知入口 + 通知列表（钉钉式） ===== */
.notice-entry-avatar {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--dt-primary-soft);
  color: var(--dt-primary-strong);
  display: flex;
  align-items: center;
  justify-content: center;
}

.sub-page-action {
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: var(--dt-primary);
  cursor: pointer;
  padding: 6px 4px;
}

.notif-page {
  background: var(--dt-surface);
  border-radius: var(--dt-radius);
  overflow: hidden;
}

.notif-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  min-height: 56px;
  padding: 12px 16px;
  border: none;
  border-bottom: 1px solid var(--dt-divider);
  background: var(--dt-surface);
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s var(--dt-ease);
}

.notif-row:last-child {
  border-bottom: none;
}

.notif-row:active {
  background: var(--dt-surface-press);
}

.notif-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--dt-danger);
  flex-shrink: 0;
  margin-top: 6px;
}

.notif-dot.hidden {
  background: transparent;
}

.notif-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.notif-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.notif-title {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--dt-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-time {
  font-size: 11px;
  color: var(--dt-text-quiet);
  flex-shrink: 0;
}

.notif-content {
  font-size: 13px;
  line-height: 1.5;
  color: var(--dt-text-tertiary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== 文件页：跨会话文件汇总 ===== */
.files-page {
  background: var(--dt-surface);
  border-radius: var(--dt-radius);
  overflow: hidden;
}

.files-head {
  position: relative;
  z-index: 2;
  padding: 12px 16px 0;
}

.files-filter {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 14px 0 12px;
}

.files-filter-item {
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  line-height: 1;
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--dt-fill-2, #f2f3f5);
  color: var(--dt-text-tertiary);
}

.files-filter-item.active {
  background: var(--dt-primary-soft);
  color: var(--dt-primary-strong);
  font-weight: 600;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
}

.file-row:active {
  background: var(--dt-surface-press, #f5f6f7);
}

.file-row-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--dt-fill-2, #f2f3f5);
  color: var(--dt-primary-strong);
}

.file-row-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-row-thumb.t-voice {
  color: var(--dt-success);
}

.file-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-row-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--dt-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-row-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--dt-text-quiet);
}

.file-row-source {
  max-width: 45%;
  overflow: hidden;
  white-space: nowrap;
  color: var(--dt-primary-strong);
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
  padding: 24px 0;
  color: var(--dt-text-quiet);
}

/* 空态提示整屏居中（含各页页头高度）：绝对定位于 .sub-page（fixed，本区唯一的定位祖先），
   不随内容滚动；可交互头部（子页头 / 搜索行 / 筛选行 / 快捷圆标）z-index 抬高保持可点 */
.notif-page .empty-messages,
.files-page .empty-messages,
.mmsg-interact-page .empty-messages {
  position: absolute;
  inset: 0;
  z-index: 1;
}

/* 所有评论 / 赞和收藏 / 关注：互动流占位页 */
.mmsg-interact-page {
  background: var(--dt-surface);
}

.mmsg-interact-page .mmsg-empty-hint {
  font-size: 12px;
  color: var(--dt-text-quiet);
}

.empty-messages span {
  font-size: 14px;
}

.message-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 64px;
  padding: 12px 16px;
  background: var(--dt-surface);
  border-bottom: 1px solid var(--dt-divider);
  cursor: pointer;
  transition: background 0.15s var(--dt-ease);
}

.message-item:active {
  background: var(--dt-surface-press);
}

.message-avatar {
  position: relative;
  flex-shrink: 0;
}

/* 可点击头像：消息中心会话 / 辅导员头像点开个人主页 */
.entry-avatar-clickable { cursor: pointer; }
.entry-avatar-clickable:active { transform: scale(0.96); }

.message-unread {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: var(--dt-danger);
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
  font-weight: 600;
  color: var(--dt-text);
}

.message-time {
  font-size: 11.5px;
  color: var(--dt-text-quiet);
  flex-shrink: 0;
}

.message-preview {
  font-size: 13px;
  color: var(--dt-text-tertiary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 群聊在线人数：与最后一条消息同行展示 */
.message-preview-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.message-online-count {
  font-size: 12px;
  color: var(--dt-success);
  font-weight: 500;
  flex-shrink: 0;
}

/* 单聊在线绿点：仅对方在线时展示 */
.message-online-dot {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--dt-success);
  border: 2px solid #fff;
  box-sizing: content-box;
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 0;
}
.chat-header-avatar {
  flex-shrink: 0;
  background: var(--dt-primary-soft, #eff6ff);
  color: var(--dt-primary-strong, #1d4ed8);
  font-size: 12px;
}
.chat-header-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 右上角的「进对方主页」入口（QQ 逻辑：资料卡入口固定在头部右侧） */
.chat-header-action {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #4b5563;
  cursor: pointer;
}
.chat-header-action:active { background: #f2f3f5; }

.chat-header-placeholder {
  width: 36px;
}

/* 聊天内容区 */
.chat-content {
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

/* 聊天页面：作为弹性项撑满剩余高度，内部消息区独立滚动 */
.chat-page {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: var(--dt-bg);
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  /* 撑满聊天区高度：空聊提示上下居中 */
  height: 100%;
  padding: 24px 0;
  color: var(--dt-text-quiet);
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
  background: var(--dt-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-msg.theirs .chat-msg-bubble {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* 日期分隔线：与教师端消息页一致的胶囊样式（消息本身不再逐条显示时间） */
.chat-date-separator {
  text-align: center;
  margin: 8px 0;
}

.chat-date-separator span {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--dt-text-quiet);
  background: var(--dt-surface);
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
  background: var(--dt-primary);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s, transform 0.1s;
}

.chat-send-btn:hover:not(:disabled) {
  background: var(--dt-primary-strong);
}

.chat-send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.chat-send-btn:disabled {
  background: #c0c4cc;
  cursor: not-allowed;
}

/* 子页滑动动画见 styles/subpage-transition.css 的 .subpage（全站唯一实现），
   此处不再重复定义 slide-left —— 原先本地那份与全局版本参数不同（0.3s ease 一致但
   方向语义、离场定位各写各的），是本次统一要消除的重复。 */

/* ==================== 消息中心：移动端 TapTap 式改版 ====================
   页签头（好友 / 消息）+ 三个实心快捷圆标（所有评论 / 赞和收藏 / 关注，第 4 格留白）
   + 群聊与私聊混排的会话流；二级页空态一律整屏居中。 */

/* 页签头（吸顶：贴 .sub-page-content.msg-bleed 滚动容器顶部） */
.mmsg-header {
  position: sticky;
  top: 0;
  z-index: 6;
  display: flex;
  align-items: center;
  padding: 8px 8px 0;
  background: var(--dt-surface);
}

.mmsg-icon-btn {
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 50%;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--dt-text);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mmsg-icon-btn:active {
  background: var(--dt-surface-press);
}

.mmsg-tabs {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 26px;
}

.mmsg-tab {
  position: relative;
  padding: 6px 2px 10px;
  font-size: 16px;
  font-weight: 500;
  color: var(--dt-text-secondary);
  cursor: pointer;
  transition: color 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}

.mmsg-tab.active {
  color: var(--dt-text);
  font-weight: 600;
}

/* 选中页签的短下划线（参考稿的黑色小横条） */
.mmsg-tab.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 4px;
  width: 20px;
  height: 3px;
  border-radius: 2px;
  background: var(--dt-text);
  transform: translateX(-50%);
}

.mmsg-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

/* 快捷圆标（参考稿的浅底圆形图标 + 下方小字） */
.mmsg-quick {
  display: flex;
  justify-content: space-around;
  padding: 16px 8px 18px;
  background: var(--dt-surface);
}

.mmsg-quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 72px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

/* 第 4 格留白：占位不响应点击，只为对齐四宫格节奏 */
.mmsg-quick-blank {
  pointer-events: none;
}

.mmsg-quick-icon {
  position: relative;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease;
}

.mmsg-quick-item:active .mmsg-quick-icon {
  transform: scale(0.93);
}

.mmsg-quick-label {
  font-size: 12px;
  color: var(--dt-text);
}

.mmsg-quick-badge {
  position: absolute;
  top: -2px;
  right: -4px;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 9px;
  background: var(--dt-danger);
  color: #fff;
  font-size: 10.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 会话流 / 好友列表：通栏白底，行样式复用 .message-item */
.mmsg-list {
  background: var(--dt-surface);
  border-top: 1px solid var(--dt-divider);
}

/* 群聊头像角标：区分群聊与私聊 */
.mmsg-group-tag {
  position: absolute;
  right: -2px;
  bottom: -2px;
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(23, 26, 29, 0.55);
  color: #fff;
  font-size: 9px;
  line-height: 1.4;
  border: 1.5px solid #fff;
  box-sizing: content-box;
}

/* ==================== 搜索子页：整页即搜索框（对齐参考稿） ==================== */
.mmsg-search-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--dt-surface);
}

.msp-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: var(--dt-surface);
  border-bottom: 1px solid var(--dt-divider);
}

.msp-field {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 10px;
  border-radius: 9px;
  background: var(--dt-fill-2, #f2f3f5);
}

.msp-field-icon {
  color: var(--dt-text-quiet);
  flex-shrink: 0;
}

.msp-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: var(--dt-text);
}

.msp-input::placeholder {
  color: var(--dt-text-quiet);
}

.msp-clear {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--dt-text-quiet);
  color: var(--dt-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.msp-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* 无结果：空态在搜索框以下的整块区域内上下居中（视觉对齐参考稿的屏幕中部） */
.msp-body .empty-messages {
  min-height: 100%;
}

/* 消息中心 ↔ 搜索子页：push 式覆盖动画（与全站子页同一观感）——
   前进：搜索页从右滑入盖住消息中心，消息中心原地不动；
   返回：搜索页原路向右滑出，露出原地不动的消息中心。
   滑动的方绝对定位盖在另一方之上，两页只有一方位移，避免「传送带」穿帮。 */
.mmsg-cover-enter-active {
  position: absolute;
  inset: 0;
  z-index: 2;
  animation: mmsg-cover-in 0.3s ease backwards;
}

.mmsg-cover-back-leave-active {
  position: absolute;
  inset: 0;
  z-index: 2;
  animation: mmsg-cover-out 0.3s ease forwards;
}

@keyframes mmsg-cover-in {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes mmsg-cover-out {
  from { transform: translateX(0); }
  to { transform: translateX(100%); }
}

@media (prefers-reduced-motion: reduce) {
  .mmsg-cover-enter-active,
  .mmsg-cover-back-leave-active {
    animation: none;
  }
}
</style>
