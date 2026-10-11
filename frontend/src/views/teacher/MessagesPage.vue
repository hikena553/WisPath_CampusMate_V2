<template>
  <div class="msg-page">
    <!-- 移动端吸顶栏：会话 / 通讯录 / 通知 三视图共用（聊天态由会话页头接管） -->
    <header v-if="isMobile && !activeId" class="msg-appbar">
      <button class="msg-appbar-btn" type="button" aria-label="打开侧边导航" @click="drawerOpen = true">
        <el-icon :size="20"><Menu /></el-icon>
      </button>
      <div class="msg-appbar-title">{{ mobileViewTitle }}</div>
      <div class="msg-appbar-actions">
        <button
          v-if="mobileView === 'messages'"
          class="msg-appbar-btn"
          type="button"
          aria-label="发起会话"
          @click="showAddFriend = true"
        >
          <el-icon :size="20"><Plus /></el-icon>
        </button>
        <button
          v-else-if="mobileView === 'notifications'"
          class="msg-appbar-btn"
          type="button"
          aria-label="全部标记已读"
          @click="handleReadAllNotifications"
        >
          <el-icon :size="19"><Check /></el-icon>
        </button>
      </div>
    </header>

    <div class="msg-sidebar" v-show="isMobile ? !activeId : true">
      <!-- 桌面端头部：移动端改由吸顶栏 + 侧边抽屉承担 -->
      <div v-if="!isMobile" class="sidebar-header">
        <div class="header-left">
          <el-dropdown trigger="click" @command="handleHeaderAction">
            <el-button text circle class="action-btn">
              <el-icon :size="20"><Plus /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="createGroup">
                  <el-icon><ChatRound /></el-icon> 创建群聊
                </el-dropdown-item>
                <el-dropdown-item command="addFriend">
                  <el-icon><User /></el-icon> 添加好友
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="header-center">
          <span class="header-title">消息</span>
        </div>
        <div class="header-right">
          <el-badge :value="totalUnread" :hidden="!totalUnread" :max="99">
            <el-icon :size="18" class="header-icon"><Bell /></el-icon>
          </el-badge>
        </div>
      </div>

      <!-- 桌面端视图切换：消息 / 通讯录 / 通知（移动端收进侧边抽屉） -->
      <div v-if="!isMobile" class="sidebar-seg">
        <div class="tui-seg">
          <button
            v-for="v in viewTabs"
            :key="v.key"
            type="button"
            class="tui-seg-item"
            :class="{ active: mobileView === v.key }"
            @click="switchView(v.key)"
          >
            {{ v.label }}
            <span v-if="v.count > 0" class="seg-count">{{ v.count > 99 ? '99+' : v.count }}</span>
          </button>
        </div>
      </div>

      <div class="sidebar-scroll">
        <!-- ============ 视图一：消息（会话列表） ============ -->
        <template v-if="mobileView === 'messages'">
        <div class="sidebar-search">
          <el-input v-model="search" placeholder="搜索已有会话" size="small" clearable
            @input="filterConversations">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <template v-if="filteredList.length === 0">
          <div class="empty-state">
            <el-icon :size="40" color="#ddd"><ChatDotRound /></el-icon>
            <span>{{ search.trim() ? '未匹配到会话' : '暂无消息' }}</span>
          </div>
        </template>

        <template v-for="item in filteredList" :key="item._key">
          <!-- 群聊 -->
          <template v-if="item._type === 'group'">
            <div class="conv-swipe-wrap" :class="{ swiped: swipedKey === item._key }">
              <div class="conv-swipe-actions">
                <button class="swipe-action" :class="{ pinned: isPinned(item._key) }"
                  @click="togglePin(item._key); swipedKey = null">
                  {{ isPinned(item._key) ? '取消置顶' : '置顶' }}
                </button>
              </div>
              <div class="conv-item" :class="{ active: activeId === item.id && activeType === 'group', pinned: isPinned(item._key) }"
                @click="openChat(item.id, item.name, 'group')"
                @touchstart="onSwipeStart($event, item._key)"
                @touchmove="onSwipeMove($event)"
                @touchend="onSwipeEnd($event)">
                <div class="conv-avatar-wrapper">
                  <el-avatar :size="36" :src="item.avatar || undefined">{{ item.name[0] }}</el-avatar>
                  <span class="group-badge">群</span>
                </div>
                <div class="conv-info">
                  <div class="conv-top">
                    <span class="conv-name">{{ item.name }}</span>
                    <span class="conv-time">{{ formatTime(item.last_message_time) }}</span>
                  </div>
                  <div class="conv-bottom">
                    <span class="conv-preview">{{ item.last_message || '暂无消息' }}</span>
                    <el-badge v-if="item.unread_count" :value="item.unread_count" :max="99" class="conv-badge" />
                  </div>
                </div>
              </div>
            </div>
          </template>
          <!-- 单聊 -->
          <template v-else>
            <div class="conv-swipe-wrap" :class="{ swiped: swipedKey === item._key }">
              <div class="conv-swipe-actions">
                <button class="swipe-action" :class="{ pinned: isPinned(item._key) }"
                  @click="togglePin(item._key); swipedKey = null">
                  {{ isPinned(item._key) ? '取消置顶' : '置顶' }}
                </button>
              </div>
              <div class="conv-item" :class="{ active: activeId === item.id && activeType === 'single', pinned: isPinned(item._key) }"
                @click="openChat(item.id, item.name, 'single')"
                @touchstart="onSwipeStart($event, item._key)"
                @touchmove="onSwipeMove($event)"
                @touchend="onSwipeEnd($event)">
                <div class="conv-avatar-wrapper">
                  <el-badge :value="item.unread_count" :hidden="!item.unread_count" class="conv-badge-avatar">
                    <el-avatar :size="36" :src="item.user_avatar || undefined">{{ item.name[0] }}</el-avatar>
                  </el-badge>
                </div>
                <div class="conv-info">
                  <div class="conv-top">
                    <span class="conv-name">{{ item.name }}</span>
                    <span class="conv-time">{{ formatTime(item.last_message_time) }}</span>
                  </div>
                  <div class="conv-bottom">
                    <span class="conv-preview">{{ item.last_message }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </template>
        </template>

        <!-- ============ 视图二：通讯录 ============ -->
        <template v-else-if="mobileView === 'contacts'">
          <!-- 全校师生检索：命中即可直接发起会话 -->
          <div class="sidebar-search">
            <el-input
              v-model="contactKeyword"
              placeholder="搜索姓名 / 学号 / 工号"
              size="small"
              clearable
              @input="onContactSearch"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </div>

          <div v-if="contactKeyword.trim()" class="addr-search-results">
            <div v-if="contactSearching" class="addr-loading">
              <el-icon class="is-loading"><Loading /></el-icon><span>搜索中…</span>
            </div>
            <div v-else-if="!contactResults.length" class="addr-empty">未找到匹配的师生</div>
            <button
              v-for="u in contactResults"
              :key="u.id"
              type="button"
              class="addr-row"
              @click="startChatWith(u)"
            >
              <el-avatar :size="38" :src="u.avatar || undefined">{{ u.name[0] }}</el-avatar>
              <span class="addr-row-main">
                <span class="addr-row-name">
                  {{ u.name }}
                  <span class="tui-tag" :class="u.role === 'teacher' ? 'tui-tag-warn' : 'tui-tag-brand'">
                    {{ u.role === 'teacher' ? '教师' : '学生' }}
                  </span>
                </span>
                <span class="addr-row-sub">{{ u.username }}</span>
              </span>
            </button>
          </div>

          <template v-else>
            <!-- 我的学生 -->
            <div class="addr-section-head">
              <span class="addr-section-title">我的学生</span>
              <span class="addr-section-count">{{ contactStudents.length }} 人</span>
            </div>
            <div v-if="contactsLoading" class="addr-loading">
              <el-icon class="is-loading"><Loading /></el-icon><span>加载中…</span>
            </div>
            <div v-else-if="!contactStudents.length" class="addr-empty">暂无名下学生</div>
            <button
              v-for="s in contactStudents"
              :key="s.id"
              type="button"
              class="addr-row"
              @click="startChatWith(s)"
            >
              <el-avatar :size="38" :src="s.avatar || undefined">{{ s.name[0] }}</el-avatar>
              <span class="addr-row-main">
                <span class="addr-row-name">
                  {{ s.name }}
                  <span v-if="s.crisis_level && s.crisis_level !== 'none'" class="tui-tag tui-tag-danger">关注</span>
                </span>
                <span class="addr-row-sub">{{ s.college || '—' }} · {{ s.username }}</span>
              </span>
            </button>

            <!-- 组织架构：学院 → 专业 → 班级 -->
            <div class="addr-section-head">
              <span class="addr-section-title">组织架构</span>
              <span class="addr-section-count">{{ orgColleges.length }} 个学院</span>
            </div>
            <div v-if="orgLoading" class="addr-loading">
              <el-icon class="is-loading"><Loading /></el-icon><span>加载中…</span>
            </div>
            <div v-else-if="!orgColleges.length" class="addr-empty">暂无组织架构数据</div>
            <template v-else>
            <template v-for="c in orgColleges" :key="c.id">
              <button type="button" class="addr-row addr-row-org" @click="toggleOrgCollege(c.id)">
                <span class="addr-org-icon"><el-icon :size="17"><OfficeBuilding /></el-icon></span>
                <span class="addr-row-main">
                  <span class="addr-row-name">{{ c.name }}</span>
                  <span class="addr-row-sub">{{ c.code }}</span>
                </span>
                <el-icon class="addr-arrow" :size="15">
                  <ArrowDown v-if="expandedColleges.has(c.id)" /><ArrowRight v-else />
                </el-icon>
              </button>
              <template v-if="expandedColleges.has(c.id)">
                <template v-for="m in (orgMajors[c.id] || [])" :key="m.id">
                  <button type="button" class="addr-row addr-row-major" @click="toggleOrgMajor(m.id)">
                    <span class="addr-org-icon major"><el-icon :size="15"><Collection /></el-icon></span>
                    <span class="addr-row-main">
                      <span class="addr-row-name">{{ m.name }}</span>
                    </span>
                    <el-icon class="addr-arrow" :size="15">
                      <ArrowDown v-if="expandedMajors.has(m.id)" /><ArrowRight v-else />
                    </el-icon>
                  </button>
                  <template v-if="expandedMajors.has(m.id)">
                    <div
                      v-for="cg in (orgClasses[m.id] || [])"
                      :key="cg.id"
                      class="addr-row addr-row-class"
                    >
                      <span class="addr-org-icon klass"><el-icon :size="14"><Notebook /></el-icon></span>
                      <span class="addr-row-main">
                        <span class="addr-row-name">{{ cg.name }}</span>
                        <span class="addr-row-sub">{{ cg.grade }} 级</span>
                      </span>
                      <span class="tui-row-value">{{ cg.student_count ?? 0 }} 人</span>
                    </div>
                  </template>
                </template>
              </template>
            </template>
            </template>
          </template>
        </template>

        <!-- ============ 视图三：通知（不设分类筛选，按时间倒序直出） ============ -->
        <template v-else>
          <div v-if="notifLoading && !notifications.length" class="addr-loading">
            <el-icon class="is-loading"><Loading /></el-icon><span>加载中…</span>
          </div>
          <div v-else-if="!notifications.length" class="empty-state">
            <el-icon :size="40" color="#ddd"><Bell /></el-icon>
            <span>暂无通知</span>
          </div>
          <button
            v-for="n in notifications"
            :key="n.id"
            type="button"
            class="notif-row"
            :class="{ unread: !n.is_read }"
            @click="openNotification(n)"
          >
            <span
              class="notif-icon"
              :style="{ background: notifMeta(n.type).tint, color: notifMeta(n.type).color }"
            >
              <el-icon :size="17"><component :is="notifMeta(n.type).icon" /></el-icon>
            </span>
            <span class="notif-main">
              <span class="notif-top">
                <span class="notif-title">{{ n.title }}</span>
                <span class="notif-time">{{ formatTime(n.created_at) }}</span>
              </span>
              <span class="notif-content">{{ n.content }}</span>
            </span>
            <span v-if="!n.is_read" class="notif-dot" />
          </button>
        </template>
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="msg-chat" v-show="!isMobile || !!activeId">
      <template v-if="activeId">
        <div class="chat-header">
          <div class="chat-header-left">
            <el-button text circle @click="goBack" class="back-btn" v-show="isMobile">
              <el-icon :size="20"><ArrowLeft /></el-icon>
            </el-button>
            <el-avatar v-if="isMobile && activeType === 'group'" :size="34" shape="square"
              :src="currentGroup?.avatar || undefined" class="chat-header-group-avatar">
              <el-icon :size="16"><UserFilled /></el-icon>
            </el-avatar>
            <div class="chat-header-info" @click="activeType === 'group' && isMobile && openGroupSettings()">
              <div class="chat-name">{{ activeName }}</div>
              <div v-if="activeType === 'group'" class="chat-member-count">
                {{ currentGroup?.member_count || 0 }}人
              </div>
            </div>
          </div>
          <div class="chat-header-right">
            <!-- 移动端群聊：进入群设置（QQ 风格） -->
            <el-button v-if="isMobile && activeType === 'group'" text circle class="header-more"
              @click="openGroupSettings">
              <el-icon :size="20"><Menu /></el-icon>
            </el-button>
            <el-dropdown v-if="!isMobile && activeType === 'group'" trigger="click">
              <el-button text circle><el-icon :size="18"><MoreFilled /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="showManageGroup = true">
                    <el-icon><Setting /></el-icon> 群管理
                  </el-dropdown-item>
                  <el-dropdown-item @click="showAddMember = true">
                    <el-icon><Plus /></el-icon> 添加成员
                  </el-dropdown-item>
                  <el-dropdown-item @click="openMemberList">
                    <el-icon><User /></el-icon> 查看成员
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <!-- 单聊且对方为名下学生：档案 / 关怀快捷操作 -->
            <el-dropdown v-if="activeType === 'single' && isMyStudent" trigger="click" @command="onStudentMenuCommand">
              <el-button text circle class="header-more">
                <el-icon :size="isMobile ? 20 : 18"><Menu v-if="isMobile" /><MoreFilled v-else /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon> 查看档案
                  </el-dropdown-item>
                  <el-dropdown-item command="care">
                    <el-icon><ChatDotRound /></el-icon> 记录关怀
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="msg-list" ref="msgListRef"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
          @paste="onPaste">
          <!-- 拖拽遮罩 -->
          <Transition name="fade">
            <div v-if="dragOver" class="drag-overlay">
              <el-icon :size="56"><UploadFilled /></el-icon>
              <span>释放以上传文件</span>
              <small>支持图片、文档、压缩包，最大 50MB</small>
            </div>
          </Transition>
          <!-- 上传进度条 -->
          <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress-bar">
            <div class="upload-progress-inner" :style="{ width: uploadProgress + '%' }"></div>
            <span>上传中 {{ uploadProgress }}%</span>
          </div>
          <template v-for="item in messageTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
            <div v-if="item.type === 'date'" class="date-separator"><span>{{ item.label }}</span></div>
            <div v-else class="msg-row" :class="item.msg.sender_id === userId ? 'mine' : 'theirs'">
              <el-avatar class="msg-avatar" :size="36" :src="avatarOf(item.msg) || undefined">
                {{ initialOf(item.msg) }}
              </el-avatar>
              <div class="msg-col">
                <div v-if="activeType === 'group' && item.msg.sender_id !== userId" class="sender-name">
                  {{ item.msg.sender_name }}
                </div>
                <div class="msg-bubble" :class="item.msg.sender_id === userId ? 'mine' : 'theirs'">
                  <!-- 文件/图片消息 -->
                  <template v-if="getMsgMeta(item.msg).isFile">
                    <template v-if="getMsgMeta(item.msg).fileType === 'image'">
                      <div class="bubble-image" @click="previewImage(getMsgMeta(item.msg).url)">
                        <img :src="getMsgMeta(item.msg).url" :alt="getMsgMeta(item.msg).text" />
                      </div>
                    </template>
                    <div v-else class="bubble-file" @click="downloadFile(getMsgMeta(item.msg).url, getMsgMeta(item.msg).text)">
                      <el-icon :size="28"><Document /></el-icon>
                      <div class="bubble-file-info">
                        <span class="bubble-file-name">{{ getMsgMeta(item.msg).text }}</span>
                        <small>点击下载</small>
                      </div>
                    </div>
                  </template>
                  <!-- 文本消息 -->
                  <div v-else class="bubble-text">{{ item.msg.content }}</div>
                </div>
                <div class="bubble-time">{{ formatTime(item.msg.created_at) }}</div>
              </div>
            </div>
          </template>
          <div v-if="messages.length === 0" class="chat-empty">
            <el-icon :size="48" color="#ddd"><ChatLineRound /></el-icon>
            <span>暂无聊天记录</span>
          </div>
        </div>

        <div class="msg-input-bar">
          <!-- 综合加号按钮：点击展开附件面板 -->
          <div class="plus-panel-wrap">
            <button class="plus-btn" :class="{ open: showAttachPanel }" title="发送附件"
              @click="toggleAttachPanel" aria-label="发送附件">
              <el-icon :size="20"><Plus /></el-icon>
            </button>
            <Transition name="attach">
              <div v-if="showAttachPanel" class="attach-panel">
                <div class="attach-item" @click="pickImage">
                  <div class="attach-item-icon img"><el-icon :size="22"><Picture /></el-icon></div>
                  <span class="attach-item-label">图片</span>
                </div>
                <div class="attach-item" @click="pickFile">
                  <div class="attach-item-icon file"><el-icon :size="22"><Document /></el-icon></div>
                  <span class="attach-item-label">文件</span>
                </div>
              </div>
            </Transition>
            <input type="file" multiple hidden ref="fileInputRef" @change="onFileSelect"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.txt" />
            <input type="file" multiple hidden ref="imageInputRef" @change="onFileSelect"
              accept=".jpg,.jpeg,.png,.gif,.bmp" />
          </div>
          <div class="input-main">
            <el-input v-model="newMsg" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="输入消息..."
              @keydown.enter.exact.prevent="sendMsg" />
          </div>
          <button class="send-btn" :class="{ active: newMsg.trim() }" :disabled="!newMsg.trim()" @click="sendMsg">
            发送
          </button>
        </div>
      </template>

      <div v-else class="no-selection">
        <el-icon :size="80" color="var(--tui-text-quiet)"><ChatLineRound /></el-icon>
        <h2>智慧校园消息中心</h2>
        <p>选择一个会话开始聊天</p>
        <div class="quick-actions">
          <el-button type="primary" @click="showAddFriend = true">
            <el-icon><User /></el-icon> 添加好友
          </el-button>
          <el-button type="primary" @click="showCreateGroup = true">
            <el-icon><ChatRound /></el-icon> 创建群聊
          </el-button>
        </div>
      </div>
    </div>

    <!-- ============= 添加好友弹窗 ============= -->
    <el-dialog v-model="showAddFriend" title="选择联系人" width="480px" :fullscreen="isMobile" :close-on-click-modal="false" @opened="focusAddFriendInput">
      <div class="add-friend-dialog">
        <div class="add-friend-search-box">
          <el-input ref="addFriendInputRef" v-model="addFriendSearch" placeholder="输入学号、工号或姓名搜索"
            size="large" clearable @input="onAddFriendSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <div class="add-friend-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>可搜索全校师生进行添加，支持学号/工号/姓名检索</span>
          </div>
        </div>
        <div class="add-friend-results">
          <div v-if="addFriendSearch.trim() && addFriendLoading" class="search-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>搜索中...</span>
          </div>
          <div v-else-if="addFriendSearch.trim() && !addFriendLoading && addFriendResults.length === 0" class="empty-state">
            <el-icon :size="40" color="#ddd"><User /></el-icon>
            <span>未找到用户</span>
          </div>
          <div v-for="u in addFriendResults" :key="u.id" class="add-friend-item">
            <div class="add-friend-item-left">
              <el-avatar :size="44" :src="u.avatar || undefined">{{ u.name[0] }}</el-avatar>
              <div class="add-friend-item-info">
                <div class="add-friend-item-name">
                  {{ u.name }}
                  <el-tag size="small" :type="u.role === 'teacher' ? 'warning' : 'info'">
                    {{ u.role === 'teacher' ? '教师' : '学生' }}
                  </el-tag>
                </div>
                <div class="add-friend-item-username">{{ u.username }}</div>
              </div>
            </div>
            <el-button type="primary" size="small" @click="addFriendAndChat(u)">
              <el-icon><Plus /></el-icon> 添加
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 创建群聊弹窗 ============= -->
    <el-dialog v-model="showCreateGroup" title="发起群聊" width="480px" :fullscreen="isMobile" :close-on-click-modal="false">
      <div class="create-group-form">
        <el-input v-model="newGroupName" placeholder="请输入群名称" maxlength="20" show-word-limit size="large" />
        <div class="member-search-box" style="margin-top:14px">
          <el-input v-model="memberSearch" placeholder="搜索成员（学号/工号/姓名）" size="small"
            @input="searchMembersForGroup" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div v-if="selectedMembers.length" class="selected-members">
          <el-tag v-for="m in selectedMembers" :key="m.id" closable @close="removeSelectedMember(m.id)">
            {{ m.name }}
          </el-tag>
        </div>
        <div v-if="memberSearchResults.length" class="member-search-results">
          <div v-for="u in memberSearchResults" :key="u.id" class="member-search-item" @click="addSelectedMember(u)">
            <el-avatar :size="32">{{ u.name[0] }}</el-avatar>
            <div class="member-search-info">
              <span class="member-name">{{ u.name }}</span>
              <span class="member-username">{{ u.username }}</span>
            </div>
            <el-icon v-if="selectedMembers.some(m => m.id === u.id)" color="var(--tui-brand)"><Check /></el-icon>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCreateGroup = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup" :disabled="!newGroupName.trim()">创建</el-button>
      </template>
    </el-dialog>

    <!-- ============= 添加群成员弹窗 ============= -->
    <el-dialog v-model="showAddMember" title="邀请成员" width="480px" :fullscreen="isMobile" :close-on-click-modal="false">
      <el-input v-model="addMemberSearch" placeholder="搜索用户" clearable @input="searchMembersToAdd">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div v-if="addMemberResults.length" class="add-member-results">
        <div v-for="u in addMemberResults" :key="u.id" class="add-member-item" @click="handleAddMember(u.id)">
          <el-avatar :size="36">{{ u.name[0] }}</el-avatar>
          <div class="add-member-info">
            <span>{{ u.name }}</span>
            <small>{{ u.username }}</small>
          </div>
          <el-icon color="var(--tui-brand)"><Plus /></el-icon>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 群成员列表弹窗 ============= -->
    <el-dialog v-model="showGroupMembers" title="群成员" width="420px" :fullscreen="isMobile">
      <div class="group-members-list">
        <div v-for="m in groupMembers" :key="m.user_id" class="group-member-item">
          <el-avatar :size="36">{{ m.user_name[0] }}</el-avatar>
          <div class="member-info">
            <span class="member-name">{{ m.user_name }}</span>
            <el-tag v-if="m.role === 'owner'" type="danger" size="small">群主</el-tag>
            <el-tag v-else-if="m.role === 'admin'" type="warning" size="small">管理员</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 群管理弹窗 ============= -->
    <el-dialog v-model="showManageGroup" title="群管理" width="560px" :fullscreen="isMobile" :close-on-click-modal="false" @opened="onManageDialogOpened">
      <div class="manage-group-dialog">
        <!-- 群公告 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <el-icon><Bell /></el-icon> 群公告
            </span>
            <el-button v-if="!editingAnnouncement" type="primary" text size="small" @click="startEditAnnouncement">
              {{ currentGroup?.announcement ? '编辑' : '设置公告' }}
            </el-button>
          </div>
          <template v-if="editingAnnouncement">
            <el-input v-model="announcementText" type="textarea" :rows="3" placeholder="请输入群公告..." maxlength="500" show-word-limit />
            <div class="manage-announcement-actions">
              <el-button size="small" @click="cancelEditAnnouncement">取消</el-button>
              <el-button size="small" type="primary" @click="saveAnnouncement" :loading="savingAnnouncement">保存</el-button>
            </div>
          </template>
          <div v-else class="manage-announcement-content">
            <template v-if="currentGroup?.announcement">
              <p>{{ currentGroup.announcement }}</p>
            </template>
            <span v-else class="manage-empty-hint">暂无群公告</span>
          </div>
        </div>

        <el-divider />

        <!-- 群成员 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <el-icon><User /></el-icon> 群成员
              <span class="member-count-tag">{{ groupMembers.length }}人</span>
            </span>
            <el-button type="primary" text size="small" @click="showManageInvite = !showManageInvite">
              <el-icon><Plus /></el-icon> 邀请成员
            </el-button>
          </div>

          <!-- 邀请成员展开区 -->
          <div v-if="showManageInvite" class="manage-invite-box">
            <el-input v-model="manageInviteSearch" placeholder="搜索用户（学号/工号/姓名）" size="small" clearable @input="searchMembersForManage">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <div v-if="manageInviteResults.length" class="manage-invite-results">
              <div v-for="u in manageInviteResults" :key="u.id" class="manage-invite-item" @click="handleManageAddMember(u.id)">
                <el-avatar :size="32">{{ u.name[0] }}</el-avatar>
                <div class="manage-invite-info">
                  <span>{{ u.name }}</span>
                  <small>{{ u.username }}</small>
                </div>
                <el-icon color="var(--tui-brand)"><Plus /></el-icon>
              </div>
            </div>
          </div>

          <!-- 成员列表 -->
          <div class="manage-members-list">
            <div v-for="m in groupMembers" :key="m.user_id" class="manage-member-item">
              <div class="manage-member-left">
                <el-avatar :size="34">{{ m.user_name[0] }}</el-avatar>
                <div class="manage-member-info">
                  <span class="manage-member-name">{{ m.user_name }}</span>
                  <el-tag v-if="m.role === 'owner'" type="danger" size="small">群主</el-tag>
                  <el-tag v-else-if="m.role === 'admin'" type="warning" size="small">管理员</el-tag>
                </div>
              </div>
              <el-button
                v-if="m.user_id !== userId && isCurrentUserAdmin"
                type="danger" text size="small"
                @click="handleRemoveMember(m.user_id, m.user_name)">
                移除
              </el-button>
            </div>
          </div>
        </div>

        <el-divider />

        <!-- 危险操作 -->
        <div class="manage-section manage-danger-zone">
          <div class="manage-section-title" style="margin-bottom:12px">
            <el-icon><WarningFilled /></el-icon> 危险操作
          </div>
          <div class="manage-danger-actions">
            <el-button v-if="!isCurrentUserOwner" type="danger" plain @click="handleLeaveGroup">
              <el-icon><SwitchButton /></el-icon> 退出群聊
            </el-button>
            <el-button v-if="isCurrentUserOwner" type="danger" @click="handleDisbandGroup">
              <el-icon><Delete /></el-icon> 解散群聊
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 移动端：群设置子页面（QQ 风格） ============= -->
    <div v-if="isMobile && groupSubPage === 'settings'" class="group-sub-page">
      <input type="file" hidden ref="groupAvatarInputRef" accept="image/*" @change="onGroupAvatarSelected" />
      <div class="gsp-header">
        <el-button text circle @click="closeGroupSubPage">
          <el-icon :size="20"><ArrowLeft /></el-icon>
        </el-button>
        <span class="gsp-title">群设置</span>
        <div style="width:32px"></div>
      </div>
      <div class="gsp-hero">
        <div class="gsp-avatar-wrap" :class="{ editable: isCurrentUserAdmin }" @click="triggerGroupAvatar">
          <el-avatar v-if="currentGroup?.avatar" :size="64" shape="square" :src="currentGroup.avatar" class="gsp-avatar" />
          <div v-else class="gsp-avatar">{{ (currentGroup?.name || activeName || '群')[0] }}</div>
          <div v-if="isCurrentUserAdmin" class="gsp-avatar-cam">
            <el-icon :size="14"><Camera /></el-icon>
          </div>
        </div>
        <div class="gsp-name">{{ activeName }}</div>
        <div class="gsp-meta">{{ currentGroup?.member_count || 0 }} 名群成员</div>
      </div>
      <div class="gsp-body">
        <!-- 群公告 -->
        <div class="gsp-menu">
          <div class="gsp-item" @click="groupSubPage = 'announcement'">
            <div class="gsp-item-icon announce"><el-icon :size="18"><Bell /></el-icon></div>
            <span class="gsp-item-label">群公告</span>
            <span class="gsp-item-value">{{ currentGroup?.announcement ? '查看' : '未设置' }}</span>
            <el-icon class="gsp-arrow" color="var(--tui-text-quiet)"><ArrowRight /></el-icon>
          </div>
          <!-- 群文件 -->
          <div class="gsp-item" @click="openGroupFiles">
            <div class="gsp-item-icon filee"><el-icon :size="18"><FolderOpened /></el-icon></div>
            <span class="gsp-item-label">群文件</span>
            <span class="gsp-item-value">{{ groupFiles.length }} 个文件</span>
            <el-icon class="gsp-arrow" color="var(--tui-text-quiet)"><ArrowRight /></el-icon>
          </div>
          <!-- 群成员 -->
          <div class="gsp-item" @click="showGroupMembers = true">
            <div class="gsp-item-icon member"><el-icon :size="18"><User /></el-icon></div>
            <span class="gsp-item-label">群成员</span>
            <span class="gsp-item-value">{{ currentGroup?.member_count || 0 }}人</span>
            <el-icon class="gsp-arrow" color="var(--tui-text-quiet)"><ArrowRight /></el-icon>
          </div>
          <div class="gsp-item" @click="showAddMember = true">
            <div class="gsp-item-icon add"><el-icon :size="18"><Plus /></el-icon></div>
            <span class="gsp-item-label">添加成员</span>
            <el-icon class="gsp-arrow" color="var(--tui-text-quiet)"><ArrowRight /></el-icon>
          </div>
        </div>

        <!-- 危险操作 -->
        <button class="gsp-danger-btn" @click="isCurrentUserOwner ? handleDisbandGroup() : handleLeaveGroup()">
          {{ isCurrentUserOwner ? '解散群聊' : '退出群聊' }}
        </button>
      </div>
    </div>

    <!-- ============= 移动端：群公告子页面 ============= -->
    <div v-if="isMobile && groupSubPage === 'announcement'" class="group-sub-page">
      <div class="gsp-header">
        <el-button text circle @click="groupSubPage = 'settings'">
          <el-icon :size="20"><ArrowLeft /></el-icon>
        </el-button>
        <span class="gsp-title">群公告</span>
        <el-button v-if="isCurrentUserAdmin && !editingAnnouncement" text class="gsp-edit-btn" @click="startEditAnnouncement">
          编辑
        </el-button>
        <div v-else style="width:44px"></div>
      </div>
      <div class="gsp-body">
        <template v-if="editingAnnouncement">
          <el-input v-model="announcementText" type="textarea" :rows="6" maxlength="500" show-word-limit
            placeholder="填写群公告内容，例如：\n1. 请大家按时提交材料\n2. 周五班会时间调整至 16:00" />
          <div class="gsp-ann-actions">
            <button class="gsp-cancel-btn" @click="cancelEditAnnouncement">取消</button>
            <button class="gsp-save-btn" :disabled="!announcementText.trim() || savingAnnouncement" @click="saveAnnouncement">
              {{ savingAnnouncement ? '保存中...' : '保存' }}
            </button>
          </div>
        </template>
        <template v-else>
          <div v-if="currentGroup?.announcement" class="gsp-ann-card">
            <div class="gsp-ann-head">
              <el-icon :size="18"><Bell /></el-icon>
              <span>群公告</span>
            </div>
            <p class="gsp-ann-text">{{ currentGroup.announcement }}</p>
          </div>
          <div v-else class="gsp-empty-box">
            <el-icon :size="40" color="var(--tui-text-quiet)"><Bell /></el-icon>
            <span>暂无群公告</span>
            <small v-if="isCurrentUserAdmin">点击右上角「编辑」发布第一条公告</small>
          </div>
        </template>
      </div>
    </div>

    <!-- ============= 移动端：群文件子页面 ============= -->
    <div v-if="isMobile && groupSubPage === 'files'" class="group-sub-page">
      <div class="gsp-header">
        <el-button text circle @click="groupSubPage = 'settings'">
          <el-icon :size="20"><ArrowLeft /></el-icon>
        </el-button>
        <span class="gsp-title">群文件</span>
        <div style="width:32px"></div>
      </div>
      <div class="gsp-body">
        <input type="file" multiple hidden ref="groupFileInputRef"
          @change="onGroupFileSelect"
          accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.txt" />
        <div v-if="groupFiles.length === 0" class="gsp-empty-box">
          <el-icon :size="40" color="var(--tui-text-quiet)"><FolderOpened /></el-icon>
          <span>暂无群文件</span>
          <small>点击下方按钮上传第一个文件</small>
        </div>
        <div v-else class="gsp-file-list">
          <div v-for="f in groupFiles" :key="f.id" class="gsp-file-item" @click="downloadFile(f.url, f.text)">
            <div class="gsp-file-icon">
              <el-icon :size="22"><Document /></el-icon>
            </div>
            <div class="gsp-file-info">
              <span class="gsp-file-name">{{ f.text }}</span>
              <span class="gsp-file-meta">{{ f.sender_name }} · {{ formatTime(f.created_at) }}</span>
            </div>
            <el-icon color="var(--tui-text-quiet)"><Download /></el-icon>
          </div>
        </div>
        <button class="gsp-upload-btn" @click="groupFileInputRef?.click()">
          <el-icon :size="18"><UploadFilled /></el-icon>
          上传文件到群
        </button>
      </div>
    </div>

    <!-- ============= 群头像裁剪弹窗 ============= -->
    <el-dialog v-model="showGroupCrop" title="裁剪群头像" width="420px" :fullscreen="isMobile" :close-on-click-modal="false" @opened="onGroupCropOpened">
      <div class="group-crop-box">
        <img ref="groupCropImgRef" style="max-width:100%;display:block" />
      </div>
      <template #footer>
        <el-button @click="cancelGroupCrop">取消</el-button>
        <el-button type="primary" :loading="uploadingGroupAvatar" @click="confirmGroupCrop">确认</el-button>
      </template>
    </el-dialog>

    <!-- ============= 图片预览 ============= -->
    <Transition name="fade">
      <div v-if="previewUrl" class="image-preview-overlay" @click="previewUrl = ''">
        <img :src="previewUrl" @click.stop />
      </div>
    </Transition>

    <!-- ============= 记录关怀（单聊学生） ============= -->
    <CareRecordDialog
      v-model="showCareDialog"
      :student-id="careStudentId"
      :student-name="careStudentName"
    />

    <!-- ============= 移动端侧边抽屉（钉钉式）：消息 / 通讯录 / 通知 ============= -->
    <Transition name="drawer-mask">
      <div v-if="isMobile && drawerOpen" class="msg-drawer-mask" @click="drawerOpen = false" />
    </Transition>
    <Transition name="drawer-panel">
      <aside v-if="isMobile && drawerOpen" class="msg-drawer">
        <div class="msg-drawer-head">
          <el-avatar :size="52" shape="square" :src="auth.user?.avatar || ''">
            {{ auth.userName?.[0] || '师' }}
          </el-avatar>
          <div class="msg-drawer-user">
            <span class="msg-drawer-name">{{ auth.userName || '教师' }}</span>
            <span class="msg-drawer-sub">{{ auth.user?.college || siteName }}</span>
          </div>
        </div>
        <nav class="msg-drawer-nav">
          <button
            v-for="v in viewTabs"
            :key="v.key"
            type="button"
            class="msg-drawer-item"
            :class="{ active: mobileView === v.key }"
            @click="switchView(v.key)"
          >
            <span class="msg-drawer-icon"><el-icon :size="19"><component :is="v.icon" /></el-icon></span>
            <span class="msg-drawer-label">{{ v.label }}</span>
            <span v-if="v.count > 0" class="tui-count">{{ v.count > 99 ? '99+' : v.count }}</span>
          </button>
        </nav>
        <div class="msg-drawer-foot">
          <button class="msg-drawer-foot-btn" type="button" @click="openAddFriendFromDrawer">
            <el-icon :size="17"><User /></el-icon> 添加好友
          </button>
          <button class="msg-drawer-foot-btn" type="button" @click="drawerGoHome">
            <el-icon :size="17"><HomeFilled /></el-icon> 返回首页
          </button>
        </div>
      </aside>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import { getConversations, getMessages, sendMessage, markRead } from '@/api/messages'
import {
  getGroups, getGroup, getGroupMembers, createGroup as apiCreateGroup,
  addGroupMembers, sendGroupMessage, getGroupMessages, searchUsers,
  updateGroupAnnouncement, updateGroupAvatar, leaveGroup, disbandGroup, removeGroupMember,
  type GroupOut, type GroupMemberOut, type UserSearchResult
} from '@/api/groups'
import { uploadFile } from '@/api/upload'
import { getStudents, type StudentSummary } from '@/api/teacher'
import {
  getNotifications, markNotificationsRead, markAllNotificationsRead,
  type Notification as NotificationItem,
} from '@/api/notification'
import { getColleges, getMajors, getClassGroups } from '@/api/organization'
import type { College, Major, ClassGroup } from '@/types'
import { useSiteConfig } from '@/composables/useSiteConfig'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
import { getToken } from '@/utils/token'
import { ElMessage } from 'element-plus'
import Cropper from 'cropperjs'
import {
  Search, User, UserFilled, ChatDotRound, ChatLineRound, ArrowLeft, ArrowRight, ArrowDown, Plus,
  Bell, MoreFilled, Loading, Check, InfoFilled, ChatRound, Menu, Stamp, Collection, Notebook,
  OfficeBuilding, HomeFilled,
  UploadFilled, Document, FolderOpened, Picture, Setting, WarningFilled, Delete, SwitchButton, Download, Camera
} from '@element-plus/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const userId = auth.user?.id ?? 0
const { isMobile } = useResponsive()
const { siteName } = useSiteConfig()

// ===== 消息中心视图（消息 / 通讯录 / 通知）=====
// 消息为默认主视图；通讯录与通知在移动端收进侧边抽屉，桌面端置于左栏分段切换
type MsgView = 'messages' | 'contacts' | 'notifications'
const mobileView = ref<MsgView>('messages')
const drawerOpen = ref(false)
const mobileViewTitle = computed(
  () => ({ messages: '消息', contacts: '通讯录', notifications: '通知' } as Record<MsgView, string>)[mobileView.value]
)

const viewTabs = computed(() => [
  { key: 'messages' as MsgView, label: '消息', icon: ChatLineRound, count: totalUnread.value },
  { key: 'contacts' as MsgView, label: '通讯录', icon: User, count: 0 },
  { key: 'notifications' as MsgView, label: '通知', icon: Bell, count: unreadNotifCount.value },
])

function switchView(v: MsgView) {
  mobileView.value = v
  drawerOpen.value = false
  if (v === 'contacts') ensureContacts()
  if (v === 'notifications') loadNotifications()
}

function openAddFriendFromDrawer() {
  drawerOpen.value = false
  showAddFriend.value = true
}

function drawerGoHome() {
  drawerOpen.value = false
  router.push('/teacher')
}

const conversations = ref<any[]>([])
const groups = ref<GroupOut[]>([])

const activeId = ref<number | null>(null)
const activeName = ref('')
const activeType = ref<'single' | 'group'>('single')
const messages = ref<any[]>([])
const newMsg = ref('')
const msgListRef = ref<HTMLDivElement>()

// 单聊对方是否为名下学生（用于展示档案 / 关怀快捷操作）
const myStudentIds = ref<Set<number>>(new Set())
const isMyStudent = computed(
  () => activeType.value === 'single' && !!activeId.value && myStudentIds.value.has(activeId.value)
)
const showCareDialog = ref(false)
const careStudentId = ref(0)
const careStudentName = ref('')

async function loadMyStudents() {
  try {
    const list = await getStudents()
    myStudentIds.value = new Set(list.map((s) => s.id))
  } catch {
    // 非教师账号或接口异常时不展示学生操作入口
  }
}

function onStudentMenuCommand(command: string) {
  if (!activeId.value) return
  if (command === 'profile') {
    router.push({ path: '/teacher/students', query: { student: String(activeId.value) } })
  } else if (command === 'care') {
    careStudentId.value = activeId.value
    careStudentName.value = activeName.value
    showCareDialog.value = true
  }
}

// 侧边栏 — 筛选已有会话
const search = ref('')

// 置顶会话 (localStorage 持久化)
const pinnedKeys = ref<Set<string>>(new Set())
function loadPins() {
  try {
    const raw = localStorage.getItem('teacher-msg-pins')
    if (raw) pinnedKeys.value = new Set(JSON.parse(raw))
  } catch {}
}
function savePins() {
  localStorage.setItem('teacher-msg-pins', JSON.stringify([...pinnedKeys.value]))
}
function togglePin(key: string) {
  if (pinnedKeys.value.has(key)) pinnedKeys.value.delete(key)
  else pinnedKeys.value.add(key)
  savePins()
}
function isPinned(key: string) { return pinnedKeys.value.has(key) }

// 右滑置顶（移动端）
const swipedKey = ref<string | null>(null)
let _swipeStartX = 0
let _swipeStartY = 0
let _swipedItemKey = ''
function onSwipeStart(e: TouchEvent, key: string) {
  _swipeStartX = e.touches[0].clientX
  _swipeStartY = e.touches[0].clientY
  _swipedItemKey = key
}
function onSwipeMove(e: TouchEvent) {
  const dx = _swipeStartX - e.touches[0].clientX
  const dy = _swipeStartY - e.touches[0].clientY
  if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
    e.preventDefault()
  }
}
function onSwipeEnd(e: TouchEvent) {
  const dx = _swipeStartX - e.changedTouches[0].clientX
  if (Math.abs(dx) > 50 && _swipedItemKey) {
    swipedKey.value = swipedKey.value === _swipedItemKey ? null : _swipedItemKey
  } else {
    swipedKey.value = null
  }
  _swipedItemKey = ''
}

function sortByPinnedAndTime(items: any[]) {
  return items.sort((a, b) => {
    const aP = isPinned(a._key)
    const bP = isPinned(b._key)
    if (aP !== bP) return aP ? -1 : 1
    return (b.last_message_time || '').localeCompare(a.last_message_time || '')
  })
}

const filteredList = computed(() => {
  const kw = search.value.trim().toLowerCase()
  const fmt = (m: string) => {
    if (m.startsWith('{') && m.includes('"type"')) {
      try { const p = JSON.parse(m); return p.type === 'image' ? '[图片] ' + (p.text||'') : '[文件] ' + (p.text||'') } catch {}
    }
    return m
  }
  if (!kw) {
    const groupItems = groups.value.map(g => ({ ...g, _key: 'g-' + g.id, _type: 'group', last_message: fmt(g.last_message) }))
    const convItems = conversations.value.map(c => ({
      id: c.user_id, name: c.user_name, user_avatar: c.user_avatar,
      last_message: fmt(c.last_message), last_message_time: c.last_message_time,
      unread_count: c.unread_count, _key: 's-' + c.user_id, _type: 'single'
    }))
    return sortByPinnedAndTime([...groupItems, ...convItems])
  }
  const result: any[] = []
  for (const g of groups.value) {
    if (g.name.toLowerCase().includes(kw)) {
      result.push({ ...g, _key: 'g-' + g.id, _type: 'group', last_message: fmt(g.last_message) })
    }
  }
  for (const c of conversations.value) {
    if (c.user_name.toLowerCase().includes(kw) || String(c.user_id).includes(kw)) {
      result.push({
        id: c.user_id, name: c.user_name, user_avatar: c.user_avatar,
        last_message: fmt(c.last_message), last_message_time: c.last_message_time,
        unread_count: c.unread_count, _key: 's-' + c.user_id, _type: 'single'
      })
    }
  }
  return sortByPinnedAndTime(result)
})

function filterConversations() {}

// 添加好友
const showAddFriend = ref(false)
const addFriendSearch = ref('')
const addFriendResults = ref<UserSearchResult[]>([])
const addFriendLoading = ref(false)
const addFriendInputRef = ref()
let addFriendTimer: ReturnType<typeof setTimeout> | null = null

function focusAddFriendInput() {
  nextTick(() => addFriendInputRef.value?.focus())
}

function onAddFriendSearch() {
  if (addFriendTimer) clearTimeout(addFriendTimer)
  if (!addFriendSearch.value.trim()) {
    addFriendResults.value = []
    return
  }
  addFriendLoading.value = true
  addFriendTimer = setTimeout(async () => {
    try {
      addFriendResults.value = await searchUsers(addFriendSearch.value.trim())
    } catch { addFriendResults.value = [] }
    finally { addFriendLoading.value = false }
  }, 300)
}

async function addFriendAndChat(user: UserSearchResult) {
  showAddFriend.value = false
  addFriendSearch.value = ''
  addFriendResults.value = []
  await openChat(user.id, user.name, 'single')
  ElMessage.success(`已添加 ${user.name}，可以开始聊天了`)
}

// 创建群聊弹窗
const showCreateGroup = ref(false)
const newGroupName = ref('')
const memberSearch = ref('')
const memberSearchResults = ref<UserSearchResult[]>([])
const selectedMembers = ref<UserSearchResult[]>([])

async function searchMembersForGroup() {
  if (!memberSearch.value.trim()) { memberSearchResults.value = []; return }
  try { memberSearchResults.value = await searchUsers(memberSearch.value.trim()) } catch { memberSearchResults.value = [] }
}
function addSelectedMember(u: UserSearchResult) {
  if (!selectedMembers.value.some(m => m.id === u.id)) selectedMembers.value.push(u)
}
function removeSelectedMember(id: number) {
  selectedMembers.value = selectedMembers.value.filter(m => m.id !== id)
}
async function handleCreateGroup() {
  if (!newGroupName.value.trim()) return
  try {
    const result = await apiCreateGroup({
      name: newGroupName.value.trim(),
      member_ids: selectedMembers.value.map(m => m.id)
    })
    ElMessage.success('群聊创建成功')
    showCreateGroup.value = false
    newGroupName.value = ''
    selectedMembers.value = []
    await loadGroups()
    openChat(result.id, result.name, 'group')
  } catch { ElMessage.error('创建失败') }
}

// 群管理
const showAddMember = ref(false)
const addMemberSearch = ref('')
const addMemberResults = ref<UserSearchResult[]>([])
const showGroupMembers = ref(false)
const groupMembers = ref<GroupMemberOut[]>([])
const currentGroup = ref<GroupOut | null>(null)

const showManageGroup = ref(false)

// 移动端群设置子页面（QQ 风格）：settings / announcement / files
const groupSubPage = ref<'settings' | 'announcement' | 'files' | null>(null)
const groupFileInputRef = ref<HTMLInputElement>()
const groupAvatarInputRef = ref<HTMLInputElement>()
const showGroupCrop = ref(false)
const pendingGroupAvatarSrc = ref('')
const uploadingGroupAvatar = ref(false)
let groupCropper: Cropper | null = null
const groupCropImgRef = ref<HTMLImageElement>()

const editingAnnouncement = ref(false)
const announcementText = ref('')
const savingAnnouncement = ref(false)
const showManageInvite = ref(false)
const manageInviteSearch = ref('')
const manageInviteResults = ref<UserSearchResult[]>([])
let manageInviteTimer: ReturnType<typeof setTimeout> | null = null

const isCurrentUserOwner = computed(() => {
  const me = groupMembers.value.find(m => m.user_id === userId)
  return me?.role === 'owner'
})
const isCurrentUserAdmin = computed(() => {
  const me = groupMembers.value.find(m => m.user_id === userId)
  return me?.role === 'owner' || me?.role === 'admin'
})

async function onManageDialogOpened() {
  if (!activeId.value) return
  try {
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
    announcementText.value = currentGroup.value?.announcement || ''
    editingAnnouncement.value = false
    showManageInvite.value = false
    manageInviteSearch.value = ''
    manageInviteResults.value = []
  } catch {}
}

function startEditAnnouncement() {
  announcementText.value = currentGroup.value?.announcement || ''
  editingAnnouncement.value = true
}

function cancelEditAnnouncement() {
  editingAnnouncement.value = false
  announcementText.value = currentGroup.value?.announcement || ''
}

async function saveAnnouncement() {
  if (!activeId.value) return
  if (!announcementText.value.trim()) {
    ElMessage.warning('请输入群公告内容')
    return
  }
  savingAnnouncement.value = true
  try {
    await updateGroupAnnouncement(activeId.value, announcementText.value)
    ElMessage.success('群公告已更新')
    editingAnnouncement.value = false
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('更新失败') }
  finally { savingAnnouncement.value = false }
}

function searchMembersForManage() {
  if (manageInviteTimer) clearTimeout(manageInviteTimer)
  if (!manageInviteSearch.value.trim()) { manageInviteResults.value = []; return }
  manageInviteTimer = setTimeout(async () => {
    try { manageInviteResults.value = await searchUsers(manageInviteSearch.value.trim()) } catch { manageInviteResults.value = [] }
  }, 300)
}

async function handleManageAddMember(uid: number) {
  if (!activeId.value) return
  try {
    await addGroupMembers(activeId.value, [uid])
    ElMessage.success('已添加')
    manageInviteSearch.value = ''
    manageInviteResults.value = []
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('添加失败') }
}

async function handleRemoveMember(uid: number, name: string) {
  if (!activeId.value) return
  try {
    await removeGroupMember(activeId.value, uid)
    ElMessage.success(`已移除 ${name}`)
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('移除失败') }
}

async function handleLeaveGroup() {
  if (!activeId.value) return
  try {
    await leaveGroup(activeId.value)
    ElMessage.success('已退出群聊')
    showManageGroup.value = false
    goBack()
    await loadGroups()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '退群失败')
  }
}

async function handleDisbandGroup() {
  if (!activeId.value) return
  try {
    await disbandGroup(activeId.value)
    ElMessage.success('群聊已解散')
    showManageGroup.value = false
    goBack()
    await loadGroups()
  } catch { ElMessage.error('解散失败') }
}

// 文件上传
const dragOver = ref(false)
const uploadProgress = ref(0)
const fileInputRef = ref<HTMLInputElement>()
const imageInputRef = ref<HTMLInputElement>()
const previewUrl = ref('')

// 加号展开面板
const showAttachPanel = ref(false)
function toggleAttachPanel() {
  showAttachPanel.value = !showAttachPanel.value
}
function pickImage() {
  showAttachPanel.value = false
  imageInputRef.value?.click()
}
function pickFile() {
  showAttachPanel.value = false
  fileInputRef.value?.click()
}

async function searchMembersToAdd() {
  if (!addMemberSearch.value.trim()) { addMemberResults.value = []; return }
  try { addMemberResults.value = await searchUsers(addMemberSearch.value.trim()) } catch { addMemberResults.value = [] }
}
async function handleAddMember(uid: number) {
  if (!activeId.value || activeType.value !== 'group') return
  try {
    await addGroupMembers(activeId.value, [uid])
    ElMessage.success('已添加')
    addMemberSearch.value = ''
    addMemberResults.value = []
    showAddMember.value = false
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('添加失败') }
}
async function openMemberList() {
  showGroupMembers.value = true
  try { groupMembers.value = await getGroupMembers(activeId.value!) } catch {}
}

// ===== 移动端群设置子页面（QQ 风格） =====
async function openGroupSettings() {
  if (activeType.value !== 'group' || !activeId.value) return
  groupSubPage.value = 'settings'
  try {
    const [members, group] = await Promise.all([
      getGroupMembers(activeId.value),
      getGroup(activeId.value),
    ])
    groupMembers.value = members
    currentGroup.value = group
    announcementText.value = group?.announcement || ''
    editingAnnouncement.value = false
  } catch { /* 已有数据则保留 */ }
}

function closeGroupSubPage() {
  groupSubPage.value = null
}

// ===== 群头像编辑 =====
function triggerGroupAvatar() {
  if (!isCurrentUserAdmin.value) return
  groupAvatarInputRef.value?.click()
}
function onGroupAvatarSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input?.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    pendingGroupAvatarSrc.value = ev.target?.result as string
    showGroupCrop.value = true
  }
  reader.readAsDataURL(file)
  input.value = ''
}
function onGroupCropOpened() {
  const img = groupCropImgRef.value
  if (!img || !pendingGroupAvatarSrc.value) return
  img.src = pendingGroupAvatarSrc.value
  const start = () => {
    if (groupCropper) { groupCropper.destroy(); groupCropper = null }
    groupCropper = new Cropper(img, { aspectRatio: 1, viewMode: 1, dragMode: 'move', minCropBoxWidth: 100 })
  }
  if (img.complete) { start() } else { img.onload = start }
}
function cancelGroupCrop() {
  showGroupCrop.value = false
  if (groupCropper) { groupCropper.destroy(); groupCropper = null }
}
async function confirmGroupCrop() {
  if (!activeId.value || !groupCropper) return
  const canvas = groupCropper.getCroppedCanvas({ width: 200, height: 200 })
  if (!canvas) { ElMessage.error('裁剪失败'); return }
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob((b) => r(b), 'image/jpeg', 0.9))
  if (!blob) { ElMessage.error('裁剪失败'); return }
  const file = new File([blob], 'group-avatar.jpg', { type: 'image/jpeg' })
  uploadingGroupAvatar.value = true
  try {
    const result: any = await uploadFile(file)
    await updateGroupAvatar(activeId.value, result.url)
    currentGroup.value = await getGroup(activeId.value)
    showGroupCrop.value = false
    if (groupCropper) { groupCropper.destroy(); groupCropper = null }
    ElMessage.success('群头像已更新')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '更新群头像失败')
  } finally {
    uploadingGroupAvatar.value = false
  }
}

async function openGroupFiles() {
  groupSubPage.value = 'files'
  try {
    if (activeId.value) messages.value = await getGroupMessages(activeId.value)
  } catch {}
}

function onGroupFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) uploadFiles(input.files)
  input.value = ''
}

// 群文件：从群消息中聚合文件类型消息（无额外后端接口，稳定可靠）
const groupFiles = computed(() => {
  if (activeType.value !== 'group') return []
  const files: any[] = []
  for (const m of messages.value) {
    const meta = getMsgMeta(m)
    if (meta.isFile && meta.fileType !== 'image') {
      files.push({ id: m.id, text: meta.text, url: meta.url, sender_name: m.sender_name, created_at: m.created_at })
    }
  }
  return files.reverse()
})

// 消息头像（QQ 风）：群聊用发送者头像，单聊用对方头像，自己用当前用户头像
function avatarOf(msg: any) {
  if (msg.sender_avatar) return msg.sender_avatar
  if (msg.sender_id === userId) return auth.user?.avatar || ''
  if (activeType.value === 'single') {
    return conversations.value.find(c => c.user_id === msg.sender_id)?.user_avatar || ''
  }
  return ''
}
function initialOf(msg: any) {
  if (msg.sender_id === userId) return (auth.user?.name || '我')[0]
  return (msg.sender_name || activeName.value || '?')[0]
}

// 总未读
const totalUnread = computed(() => {
  const convUnread = conversations.value.reduce((s: number, c: any) => s + (c.unread_count || 0), 0)
  const groupUnread = groups.value.reduce((s: number, g) => s + (g.unread_count || 0), 0)
  return convUnread + groupUnread
})

// 时间线
const messageTimeline = computed(() => {
  const items: Array<{ type: 'date'; date: string; label: string } | { type: 'msg'; msg: any }> = []
  let lastDate = ''
  for (const m of messages.value) {
    const d = getDateStr(m.created_at)
    if (d !== lastDate) { items.push({ type: 'date', date: d, label: getDateLabel(m.created_at) }); lastDate = d }
    items.push({ type: 'msg', msg: m })
  }
  return items
})

function getDateStr(t: string) { const d = new Date(t); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` }
function getDateLabel(t: string) {
  const date = new Date(t); const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.floor((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatTime(t: string | null) {
  if (!t) return ''
  try {
    const date = new Date(t + (t.includes('Z') || t.includes('+') ? '' : 'Z'))
    const now = new Date(); const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000); const hours = Math.floor(diff / 3600000)
    const ts = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return ts
  } catch { return t }
}

// WebSocket
let ws: WebSocket | null = null
function connectWs() {
  const token = getToken()
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  // F3：刷新后内存 token 为空时省略 token 参数，由 httpOnly Cookie 兜底认证
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
  ws = new WebSocket(`${proto}//${location.host}/api/messages/ws${tokenParam}`)
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'new_message') {
        loadConversations()
        if (data.sender_id === activeId.value && activeType.value === 'single') {
          messages.value.push({ id: data.id || Date.now(), sender_id: data.sender_id, content: data.content, created_at: data.created_at, read: true })
          scrollToBottom()
        }
      } else if (data.type === 'new_group_message') {
        loadGroups()
        if (data.group_id === activeId.value && activeType.value === 'group') {
          messages.value.push({ id: data.id || Date.now(), group_id: data.group_id, sender_id: data.sender_id, sender_name: data.sender_name, content: data.content, created_at: data.created_at })
          scrollToBottom()
        }
      }
    } catch {}
  }
  ws.onclose = () => { ws = null }
}
function disconnectWs() { if (ws) { ws.close(); ws = null } }

async function loadConversations() { try { conversations.value = await getConversations() } catch {} }
async function loadGroups() { try { groups.value = await getGroups() } catch {} }

/* ==================== 通讯录 ==================== */
// 数据按需加载：仅当用户首次进入「通讯录」时才拉取，避免消息页初始化开销
const contactStudents = ref<StudentSummary[]>([])
const contactsLoading = ref(false)
let contactsLoaded = false
const contactKeyword = ref('')
const contactResults = ref<UserSearchResult[]>([])
const contactSearching = ref(false)
let contactTimer: ReturnType<typeof setTimeout> | null = null

// 组织架构树：学院 → 专业 → 班级，均取自管理端「院系班级」配置
const orgColleges = ref<College[]>([])
const orgMajors = ref<Record<number, Major[]>>({})
const orgClasses = ref<Record<number, ClassGroup[]>>({})
const expandedColleges = ref<Set<number>>(new Set())
const expandedMajors = ref<Set<number>>(new Set())
const orgLoading = ref(false)

async function ensureContacts() {
  if (contactsLoaded) return
  contactsLoaded = true
  contactsLoading.value = true
  orgLoading.value = true
  try {
    const [students, colleges] = await Promise.all([
      getStudents().catch(() => [] as StudentSummary[]),
      getColleges().catch(() => [] as College[]),
    ])
    contactStudents.value = students
    orgColleges.value = colleges
  } finally {
    contactsLoading.value = false
    orgLoading.value = false
  }
}

/** 全校师生检索（后端要求关键词至少 1 个字符，故空串直接清空结果） */
function onContactSearch() {
  if (contactTimer) clearTimeout(contactTimer)
  const kw = contactKeyword.value.trim()
  if (!kw) { contactResults.value = []; contactSearching.value = false; return }
  contactSearching.value = true
  contactTimer = setTimeout(async () => {
    try { contactResults.value = await searchUsers(kw) }
    catch { contactResults.value = [] }
    finally { contactSearching.value = false }
  }, 300)
}

/** 通讯录中点击任一联系人 → 直接进入对应会话 */
async function startChatWith(u: { id: number; name: string }) {
  contactKeyword.value = ''
  contactResults.value = []
  await openChat(u.id, u.name, 'single')
}

async function toggleOrgCollege(id: number) {
  const next = new Set(expandedColleges.value)
  if (next.has(id)) { next.delete(id) } else { next.add(id) }
  expandedColleges.value = next
  if (next.has(id) && !orgMajors.value[id]) {
    const majors = await getMajors(id).catch(() => [] as Major[])
    orgMajors.value = { ...orgMajors.value, [id]: majors }
  }
}

async function toggleOrgMajor(id: number) {
  const next = new Set(expandedMajors.value)
  if (next.has(id)) { next.delete(id) } else { next.add(id) }
  expandedMajors.value = next
  if (next.has(id) && !orgClasses.value[id]) {
    const classes = await getClassGroups({ major_id: id }).catch(() => [] as ClassGroup[])
    orgClasses.value = { ...orgClasses.value, [id]: classes }
  }
}

/* ==================== 通知 ==================== */
// 通知不设分类筛选：按时间倒序直出，点击直达对应子页面
const notifications = ref<NotificationItem[]>([])
const notifLoading = ref(false)
const unreadNotifCount = computed(() => notifications.value.filter((n) => !n.is_read).length)

async function loadNotifications() {
  if (notifLoading.value) return
  notifLoading.value = true
  try {
    notifications.value = await getNotifications({ page_size: 50 })
  } catch { /* 通知拉取失败不影响会话与通讯录 */ }
  finally { notifLoading.value = false }
}

async function handleReadAllNotifications() {
  if (!unreadNotifCount.value) return
  try {
    await markAllNotificationsRead()
    await loadNotifications()
  } catch { ElMessage.error('操作失败') }
}

async function openNotification(n: NotificationItem) {
  if (!n.is_read) {
    try { await markNotificationsRead([n.id]); n.is_read = true } catch { /* 标记失败不阻断跳转 */ }
  }
  if (n.link) router.push(n.link)
}

/** 通知类型 → 图标与语义色，色值取自设计令牌同源色板（teacher-ui.css） */
function notifMeta(type: string): { icon: any; color: string; tint: string } {
  switch (type) {
    case 'approval':
    case 'leave':
      return { icon: Stamp, color: '#b54708', tint: '#fffaeb' }
    case 'crisis':
      return { icon: WarningFilled, color: '#d92d20', tint: '#fef3f2' }
    case 'announcement':
      return { icon: Bell, color: '#2563eb', tint: 'var(--tui-brand-soft)' }
    case 'feedback':
      return { icon: ChatLineRound, color: '#079455', tint: '#ecfdf3' }
    case 'message':
      return { icon: ChatDotRound, color: '#0891b2', tint: '#ecfeff' }
    default:
      return { icon: InfoFilled, color: '#6b7280', tint: '#f2f3f5' }
  }
}

// 打开聊天
async function openChat(id: number, name: string, type: 'single' | 'group') {
  activeId.value = id; activeName.value = name; activeType.value = type
  try {
    if (type === 'single') {
      messages.value = await getMessages(id)
      await markRead(id)
      loadConversations()
    } else {
      messages.value = await getGroupMessages(id)
      currentGroup.value = await getGroup(id)
      loadGroups()
    }
    scrollToBottom()
  } catch {}
}
function goBack() {
  activeId.value = null; activeName.value = ''; messages.value = []; currentGroup.value = null
  groupSubPage.value = null
}
function scrollToBottom() { nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' })) }

// 发送
async function sendMsg() {
  if (!activeId.value) return
  showAttachPanel.value = false
  if (newMsg.value.trim()) {
    await sendTextMsg(newMsg.value.trim())
  }
}

async function sendTextMsg(text: string) {
  if (!activeId.value) return
  try {
    if (activeType.value === 'single') {
      await sendMessage(activeId.value, text)
      messages.value.push({ id: Date.now(), sender_id: userId, receiver_id: activeId.value, content: text, read: true, created_at: new Date().toISOString() })
      await loadConversations()
    } else {
      await sendGroupMessage(activeId.value, text)
      messages.value.push({ id: Date.now(), group_id: activeId.value, sender_id: userId, sender_name: auth.user?.name || '我', content: text, created_at: new Date().toISOString() })
      await loadGroups()
    }
    newMsg.value = ''
    scrollToBottom()
  } catch { ElMessage.error('发送失败') }
}

// 文件/图片消息
function getMsgMeta(msg: any) {
  const c = msg.content || ''
  if (c.startsWith('{') && c.includes('"type"')) {
    try {
      const parsed = JSON.parse(c)
      if (parsed.type === 'file' || parsed.type === 'image') {
        return { isFile: true, fileType: parsed.type, text: parsed.text || '', url: parsed.url || '' }
      }
    } catch {}
  }
  return { isFile: false, fileType: '', text: '', url: '' }
}

function makeFileContent(fileType: string, filename: string, url: string) {
  return JSON.stringify({ type: fileType, text: filename, url })
}

function downloadFile(url: string, name: string) {
  const a = document.createElement('a')
  a.href = url; a.download = name; a.click()
}
function previewImage(url: string) { previewUrl.value = url }

async function uploadAndSend(file: File) {
  uploadProgress.value = 10
  try {
    const result = await uploadFile(file)
    uploadProgress.value = 100
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)
    const content = makeFileContent(isImage ? 'image' : 'file', file.name, result.url)
    await sendTextMsg(content)
  } catch {
    ElMessage.error(`上传 ${file.name} 失败`)
  } finally {
    uploadProgress.value = 0
  }
}

async function uploadFiles(files: FileList | File[]) {
  for (const f of files) {
    if (f.size > 50 * 1024 * 1024) {
      ElMessage.warning(`${f.name} 超过 50MB 限制`)
      continue
    }
    await uploadAndSend(f)
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) uploadFiles(input.files)
  input.value = ''
}

function onDragOver() { dragOver.value = true }
function onDragLeave(e: DragEvent) {
  if (!(e.currentTarget as HTMLElement)?.contains(e.relatedTarget as HTMLElement)) {
    dragOver.value = false
  }
}
async function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files.length) await uploadFiles(e.dataTransfer.files)
}
async function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const files: File[] = []
  for (let i = 0; i < items.length; i++) {
    const blob = items[i].getAsFile()
    if (blob) files.push(blob)
  }
  if (files.length) {
    e.preventDefault()
    await uploadFiles(files)
  }
}

// +号菜单
function handleHeaderAction(cmd: string) {
  if (cmd === 'createGroup') { showCreateGroup.value = true }
  else if (cmd === 'addFriend') { showAddFriend.value = true }
}

onMounted(async () => {
  document.addEventListener('click', onGlobalClick)
  loadPins()
  connectWs()
  await Promise.all([loadConversations(), loadGroups(), loadMyStudents()])
  if (route.query.groupId) {
    openChat(Number(route.query.groupId), (route.query.groupName as string) || '', 'group')
    router.replace({ query: {} })
  } else if (route.query.studentId) {
    openChat(Number(route.query.studentId), (route.query.studentName as string) || '', 'single')
    router.replace({ query: {} })
  }
})
onUnmounted(() => {
  document.removeEventListener('click', onGlobalClick)
  disconnectWs()
})

function onGlobalClick(e: MouseEvent) {
  const panel = document.querySelector('.attach-panel')
  const btn = document.querySelector('.plus-btn')
  if (panel && btn) {
    const t = e.target as HTMLElement
    if (!panel.contains(t) && !btn.contains(t)) showAttachPanel.value = false
  }
  // 点击其他区域关闭右滑置顶
  if (swipedKey.value) {
    const target = e.target as HTMLElement
    if (!target.closest('.conv-swipe-wrap')) {
      swipedKey.value = null
    }
  }
}
</script>

<style scoped>
.msg-page {
  display: flex; height: 100%;
  background: #fff;
  overflow: hidden;
}

/* ===== 侧边栏 ===== */
.msg-sidebar { width: 288px; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid #eaecf0; background: #fafbfc; }
.sidebar-header {
  display: flex; align-items: center; justify-content: space-between;
  min-height: 52px; padding: 0 12px; flex-shrink: 0;
  background: var(--tui-surface); border-bottom: 1px solid var(--tui-hairline);
}
.header-left,.header-right { width: 36px; display: flex; align-items: center; }
.header-right { justify-content: flex-end; }
.header-center { flex: 1; text-align: center; }
.header-title { font-size: 16px; font-weight: 600; color: var(--tui-text); letter-spacing: -0.2px; }
.action-btn { font-size: 18px; color: var(--tui-brand); }
.header-icon { color: var(--tui-text-tertiary); cursor: pointer; }
.header-icon:hover { color: var(--tui-brand); }
.sidebar-search { padding: 10px 12px 6px; }
.sidebar-search :deep(.el-input__wrapper) { border-radius: var(--tui-radius-sm); }
.sidebar-scroll { flex: 1; overflow-y: auto; min-height: 0; padding: 4px 0 8px; }

.conv-item { display: flex; align-items: center; gap: 12px; min-height: 64px; padding: 11px 14px; cursor: pointer; transition: background .15s var(--tui-ease); border-left: 3px solid transparent; }
.conv-item:hover { background: var(--tui-surface-muted); }
.conv-item.active { background: var(--tui-brand-soft); border-left-color: var(--tui-brand); }
.conv-avatar-wrapper { position: relative; flex-shrink: 0; line-height: 0; }
.group-badge { position: absolute; bottom: -2px; right: -2px; width: 16px; height: 16px; border-radius: 5px; background: var(--tui-surface-sunken); color: var(--tui-text-tertiary); font-size: 9px; display: flex; align-items: center; justify-content: center; border: 2px solid var(--tui-surface); }
.conv-badge-avatar { line-height: 0; }
.conv-avatar { flex-shrink: 0; }
.conv-info { flex: 1; min-width: 0; }
.conv-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.conv-name { font-size: 14.5px; font-weight: 600; color: var(--tui-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-time { font-size: 11px; color: var(--tui-text-quiet); font-family: var(--mono); flex-shrink: 0; margin-left: auto; }
.conv-bottom { display: flex; align-items: center; gap: 6px; margin-top: 3px; }
.conv-preview { font-size: 12.5px; color: var(--tui-text-quiet); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-badge { --el-badge-bg-color: var(--tui-danger); flex-shrink: 0; }
.conv-member-count { font-size: 11px; color: var(--tui-text-quiet); flex-shrink: 0; }

.conv-item.pinned { background: var(--tui-surface-muted); }

/* 右滑置顶容器（仅移动端生效，桌面端隐藏） */
.conv-swipe-wrap { position: relative; overflow: hidden; }
.conv-swipe-actions {
  position: absolute; right: 0; top: 0; bottom: 0;
  display: none;
  align-items: stretch; z-index: 1;
}
.swipe-action {
  width: 76px; border: none; background: var(--tui-surface-sunken); color: var(--tui-text-secondary);
  font-size: 14px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .15s; outline: none;
  -webkit-tap-highlight-color: transparent;
}
.swipe-action:active { background: var(--tui-surface-muted); }
.swipe-action:focus, .swipe-action:focus-visible { outline: none; box-shadow: none; }
.swipe-action.pinned { background: #f79009; color: #fff; }
.swipe-action.pinned:active { background: #e0820a; }
.conv-swipe-wrap .conv-item {
  position: relative; z-index: 2; background: #fff;
  transition: transform .24s cubic-bezier(.22,.68,0,1);
  will-change: transform;
}
.conv-swipe-wrap.swiped .conv-item {
  transform: translateX(-76px);
}

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 48px 0; color: var(--tui-text-quiet); font-size: 13px; }

/* ===== 聊天区域 ===== */
.msg-chat { flex: 1; display: flex; flex-direction: column; }
.chat-header { display: flex; align-items: center; justify-content: space-between; min-height: 52px; padding: 8px 18px; border-bottom: 1px solid var(--tui-hairline); background: var(--tui-surface); }
.chat-header-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.chat-name { font-size: 16.5px; font-weight: 600; color: var(--tui-text); }
.chat-member-count { font-size: 11.5px; color: var(--tui-text-quiet); margin-top: 2px; }
.msg-list { flex: 1; overflow-y: auto; padding: 20px; background: var(--tui-bg); }
.date-separator { text-align: center; margin: 16px 0; }
.date-separator span { display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 11px; color: var(--tui-text-quiet); background: var(--tui-surface-sunken); }
/* QQ 风消息行：头像 + 气泡 */
.msg-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 14px; }
.msg-row.mine { flex-direction: row-reverse; }
.msg-avatar { flex-shrink: 0; }
.msg-col { display: flex; flex-direction: column; max-width: min(70%, 420px); }
.msg-row.mine .msg-col { align-items: flex-end; }
.sender-name { font-size: 11px; color: var(--tui-text-quiet); margin: 0 4px 4px; }
.msg-bubble { width: fit-content; max-width: 100%; }
.bubble-text { padding: 9px 12px; border-radius: 14px; font-size: 14px; line-height: 1.5; word-break: break-word; }
.mine .bubble-text { background: var(--tui-brand); color: #fff; border-top-right-radius: 4px; }
.theirs .bubble-text { background: var(--tui-surface); color: var(--tui-text); border-top-left-radius: 4px; box-shadow: var(--tui-shadow-1); }
.bubble-time { font-size: 10.5px; color: var(--tui-text-quiet); font-family: var(--mono); margin-top: 4px; padding: 0 4px; }
.chat-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 60px 0; color: var(--tui-text-quiet); font-size: 13px; }

/* QQ 风单行输入栏：加号按钮 + 胶囊输入框 + 发送按钮 */
.msg-input-bar {
  border-top: 1px solid var(--tui-hairline); background: var(--tui-surface);
  display: flex; align-items: flex-end; gap: 8px;
  padding: 8px 10px; position: relative;
}

/* ===== 综合加号按钮 + 附件面板 ===== */
.plus-panel-wrap { position: relative; flex-shrink: 0; }
.plus-btn {
  width: 36px; height: 36px; padding: 0; border: none; cursor: pointer;
  border-radius: 50%; background: var(--tui-surface-sunken); color: var(--tui-text-secondary);
  display: flex; align-items: center; justify-content: center;
  transition: transform .22s cubic-bezier(.34,1.4,.64,1), background .18s, color .18s;
  -webkit-tap-highlight-color: transparent;
}
.plus-btn:hover { background: var(--tui-surface-sunken); color: var(--tui-text); }
.plus-btn.open {
  transform: rotate(45deg);
  background: var(--tui-surface-sunken);
  color: var(--tui-text);
}

.attach-panel {
  position: absolute; left: 0; bottom: calc(100% + 12px);
  background: var(--tui-surface); border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius); padding: 14px 10px 12px;
  box-shadow: var(--tui-shadow-2);
  display: flex; gap: 8px; z-index: 30;
  transform-origin: bottom left;
}
/* 简约：附件面板不再使用气泡尖角 */
.attach-item {
  width: 68px; display: flex; flex-direction: column; align-items: center; gap: 6px;
  cursor: pointer; padding: 4px 2px; border-radius: 10px;
  transition: background .15s, transform .12s;
}
.attach-item:hover { background: var(--tui-surface-muted); }
.attach-item:active { transform: scale(.94); }
.attach-item-icon {
  width: 50px; height: 50px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  background: var(--tui-surface-muted); color: var(--tui-text-secondary);
}
.attach-item-label { font-size: 11.5px; color: var(--tui-text-tertiary); }

.attach-enter-active { transition: opacity .18s ease-out, transform .22s cubic-bezier(.34,1.4,.64,1); }
.attach-leave-active { transition: opacity .14s ease-in, transform .14s ease-in; }
.attach-enter-from, .attach-leave-to { opacity: 0; transform: translateY(8px) scale(.9); }

.input-main { flex: 1; min-width: 0; }
.input-main .el-textarea__inner {
  min-height: auto !important; padding: 8px 14px; line-height: 20px; resize: none;
  border-radius: 12px; border: none; background: var(--tui-surface-sunken); box-shadow: none;
  transition: background .18s, box-shadow .18s;
}
.input-main .el-textarea__inner:focus {
  background: var(--tui-surface); box-shadow: 0 0 0 1px var(--tui-brand) inset;
}
.send-btn {
  height: 36px; flex-shrink: 0; padding: 0 18px; border: none; border-radius: 12px;
  font-size: 13.5px; font-weight: 600; cursor: pointer;
  background: var(--tui-surface-sunken); color: var(--tui-text-quiet); transition: all .18s;
}
.send-btn.active { background: var(--tui-brand); color: #fff; }
.send-btn:disabled { cursor: not-allowed; }

.no-selection { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--tui-text-quiet); }
.no-selection h2 { font-size: 18px; color: var(--tui-text-secondary); margin: 0; }
.no-selection p { font-size: 13px; color: var(--tui-text-quiet); margin: 0; }
.quick-actions { display: flex; gap: 12px; margin-top: 16px; }

/* ==================== 弹窗统一皮肤（钉钉式） ==================== */
/* 白底 + 发丝线 + 单一品牌主按钮；移动端整页流程，桌面端居中弹窗 */
:deep(.el-dialog) {
  border-radius: var(--tui-radius-lg);
  overflow: hidden;
  box-shadow: var(--tui-shadow-3);
  padding: 0;
}
:deep(.el-dialog__header) {
  display: flex; align-items: center;
  min-height: 52px; margin: 0; padding: 0 18px;
  border-bottom: 1px solid var(--tui-hairline);
}
:deep(.el-dialog__title) { font-size: 16.5px; font-weight: 600; color: var(--tui-text); letter-spacing: -0.2px; }
:deep(.el-dialog__headerbtn) {
  width: 34px; height: 34px; top: 9px; right: 12px;
  border-radius: 50%; transition: background .15s var(--tui-ease);
}
:deep(.el-dialog__headerbtn .el-dialog__close) { color: var(--tui-text-tertiary); }
:deep(.el-dialog__headerbtn:hover) { background: var(--tui-surface-muted); }
:deep(.el-dialog__body) { padding: 16px 18px; color: var(--tui-text-secondary); }
:deep(.el-dialog__footer) {
  padding: 12px 18px calc(12px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--tui-hairline);
  background: var(--tui-surface);
}
:deep(.el-dialog__footer .el-button) {
  min-width: 96px; height: 40px;
  border-radius: var(--tui-radius-sm); font-weight: 600; font-size: 14.5px;
}
/* 次要按钮改中性填充，去掉 Element Plus 默认白底描边的散色观感 */
:deep(.el-dialog__footer .el-button:not(.el-button--primary)) {
  background: var(--tui-surface-sunken); border-color: transparent; color: var(--tui-text-secondary);
}
:deep(.el-dialog__footer .el-button--primary) { box-shadow: none; }

/* 移动端整页（钉钉式流程）：底色下沉、页头吸顶、确定条常驻 */
:deep(.el-dialog.is-fullscreen) {
  display: flex; flex-direction: column;
  height: 100%; margin: 0; overflow: hidden;
  border-radius: 0; box-shadow: none; background: var(--tui-bg);
}
:deep(.el-dialog.is-fullscreen .el-dialog__header) {
  flex-shrink: 0; padding: 0 14px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
}
:deep(.el-dialog.is-fullscreen .el-dialog__body) {
  flex: 1; min-height: 0; overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 14px 14px 20px;
}
:deep(.el-dialog.is-fullscreen .el-dialog__footer) {
  flex-shrink: 0;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
}
:deep(.el-dialog.is-fullscreen .el-dialog__footer > div) { display: flex; gap: 10px; }
:deep(.el-dialog.is-fullscreen .el-dialog__footer .el-button) { flex: 1; margin-left: 0 !important; }

/* 弹窗内输入框：填充式圆角，聚焦转描边（无光晕） */
:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  box-shadow: 0 0 0 1px transparent inset;
  transition: background .18s var(--tui-ease), box-shadow .18s var(--tui-ease);
}
:deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px var(--tui-border-strong) inset; }
:deep(.el-input__wrapper.is-focus) {
  background: var(--tui-surface);
  box-shadow: 0 0 0 1px var(--tui-brand) inset;
}

/* ==================== 弹窗内选择列表 ==================== */
/* 统一为白底 + 发丝线 + 56px 行高，与设计稿的 row 规范一致 */
.member-search-results,
.add-member-results,
.add-friend-results,
.manage-invite-results,
.group-members-list {
  max-height: 340px; overflow-y: auto; overflow-x: hidden;
  margin-top: 10px;
  border: 1px solid var(--tui-border); border-radius: var(--tui-radius);
  background: var(--tui-surface);
}
.member-search-item,
.add-member-item,
.add-friend-item,
.manage-invite-item,
.group-member-item {
  display: flex; align-items: center; gap: 12px;
  width: 100%; min-height: 56px; padding: 10px 14px;
  border: none; border-bottom: 1px solid var(--tui-border); background: transparent;
  cursor: pointer; font-family: inherit; text-align: left;
  transition: background .15s var(--tui-ease);
}
.member-search-item:last-child,
.add-member-item:last-child,
.add-friend-item:last-child,
.manage-invite-item:last-child,
.group-member-item:last-child { border-bottom: none; }
.member-search-item:hover,
.add-member-item:hover,
.add-friend-item:hover,
.manage-invite-item:hover { background: var(--tui-surface-muted); }
.member-search-item:active,
.add-member-item:active,
.add-friend-item:active { background: var(--tui-surface-sunken); }
.add-friend-item { justify-content: space-between; }
.add-friend-item-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
.member-search-info,
.add-member-info,
.manage-invite-info,
.add-friend-item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.add-friend-item-name { font-size: 14px; font-weight: 600; color: var(--tui-text); display: flex; align-items: center; gap: 8px; }
.member-name,
.add-member-info span,
.manage-invite-info span { font-size: 14px; font-weight: 500; color: var(--tui-text); }
.add-friend-item-username,
.member-username,
.add-member-info small,
.manage-invite-info small { font-size: 11.5px; color: var(--tui-text-quiet); }
.member-info { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; }
.member-info .member-name { font-size: 14px; font-weight: 500; color: var(--tui-text); }

/* ===== 选择联系人：搜索框 / 提示 / 已选成员 ===== */
.add-friend-dialog { }
.add-friend-search-box { margin-bottom: 4px; }
.create-group-form { }
.member-search-box { margin-bottom: 4px; }
.add-friend-hint {
  display: flex; align-items: center; gap: 6px; margin-top: 10px;
  font-size: 11.5px; color: var(--tui-text-quiet);
}
.search-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 30px 0; color: var(--tui-text-quiet); font-size: 13px;
}
.selected-members { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 2px; }
.selected-members .el-tag {
  background: var(--tui-brand-soft); border-color: transparent;
  color: var(--tui-brand-strong); font-weight: 500;
}

/* ===== 拖拽上传 ===== */
.msg-list { position: relative; }
.drag-overlay {
  position: absolute; inset: 0; z-index: 10;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  background: var(--tui-brand); color: #fff; border-radius: var(--tui-radius-sm);
}
.drag-overlay span { font-size: 18px; font-weight: 600; }
.drag-overlay small { font-size: 13px; opacity: .85; }

.upload-progress-bar {
  position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: rgba(0,0,0,0.06); z-index: 10;
}
.upload-progress-inner {
  height: 100%; background: var(--tui-brand); transition: width .3s;
  border-radius: 0 2px 2px 0;
}
.upload-progress-bar span {
  position: absolute; top: -22px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: var(--tui-brand); white-space: nowrap;
}

/* ===== 文件/图片消息 ===== */
.bubble-image {
  max-width: 260px; cursor: pointer; border-radius: 12px;
  overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.1);
}
.bubble-image img {
  width: 100%; height: auto; display: block;
  transition: transform .2s;
}
.bubble-image:hover img { transform: scale(1.03); }

.bubble-file {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: 12px; cursor: pointer;
  min-width: 200px;
}
.mine .bubble-file { background: var(--tui-brand); color: #fff; border-top-right-radius: 4px; }
.theirs .bubble-file { background: var(--tui-surface); color: var(--tui-text); border-top-left-radius: 4px; box-shadow: var(--tui-shadow-1); }
.bubble-file-info { flex: 1; min-width: 0; }
.bubble-file-name {
  font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: block;
}
.bubble-file-info small { font-size: 11px; opacity: .7; }

/* ===== 图片预览 ===== */
.image-preview-overlay {
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
}
.image-preview-overlay img {
  max-width: 90vw; max-height: 90vh; border-radius: 8px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.4);
}

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ===== 群管理弹窗 ===== */
.manage-group-dialog { }
.manage-section { margin-bottom: 4px; }
.manage-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.manage-section-title { font-size: 14px; font-weight: 600; color: var(--tui-text); display: flex; align-items: center; gap: 6px; }
.member-count-tag { font-size: 11.5px; color: var(--tui-text-quiet); font-weight: 400; }
.manage-announcement-content { padding: 12px 14px; background: var(--tui-surface-muted); border-radius: var(--tui-radius-sm); min-height: 40px; }
.manage-announcement-content p { margin: 0; font-size: 13px; color: #555; line-height: 1.6; white-space: pre-wrap; }
.manage-empty-hint { font-size: 13px; color: var(--tui-text-quiet); }
.manage-announcement-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.manage-invite-box { margin-bottom: 12px; padding: 12px; background: var(--tui-surface-muted); border-radius: var(--tui-radius-sm); border: 1px solid var(--tui-border); }
.manage-invite-results { max-height: 180px; overflow-y: auto; margin-top: 8px; }
.manage-invite-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; border-radius: 8px; transition: background .15s; }
.manage-invite-item:hover { background: var(--tui-surface-sunken); }
.manage-invite-info { flex: 1; display: flex; flex-direction: column; }
.manage-invite-info span { font-size: 14px; font-weight: 500; color: var(--tui-text); }
.manage-invite-info small { font-size: 11.5px; color: var(--tui-text-quiet); }
.manage-members-list { max-height: 240px; overflow-y: auto; }
.manage-member-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 56px; padding: 10px 2px; border-bottom: 1px solid var(--tui-border); }
.manage-member-item:last-child { border-bottom: none; }
.manage-member-left { display: flex; align-items: center; gap: 10px; }
.manage-member-info { display: flex; align-items: center; gap: 8px; }
.manage-member-name { font-size: 14px; font-weight: 500; color: var(--tui-text); }
.manage-danger-zone { padding: 12px; background: var(--tui-danger-soft); border-radius: var(--tui-radius-sm); border: 1px solid transparent; }
.manage-danger-actions { display: flex; gap: 10px; }

/* ==================== 消息中心：移动端吸顶栏 ==================== */
.msg-appbar {
  display: flex; align-items: center; gap: 6px;
  min-height: 52px; padding: 0 8px; flex-shrink: 0;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid var(--tui-hairline);
}
.msg-appbar-btn {
  width: 40px; height: 40px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; background: transparent;
  color: var(--tui-text); cursor: pointer;
  transition: background .18s var(--tui-ease);
  -webkit-tap-highlight-color: transparent;
}
.msg-appbar-btn:active { background: rgba(15, 17, 21, 0.07); }
.msg-appbar-title {
  flex: 1; min-width: 0;
  font-size: 16.5px; font-weight: 600; letter-spacing: -0.2px; color: var(--tui-text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.msg-appbar-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }

/* ==================== 桌面端视图切换 ==================== */
.sidebar-seg { padding: 10px 12px 4px; }
.sidebar-seg .tui-seg { width: 100%; }
.seg-count {
  margin-left: 4px; padding: 0 5px; border-radius: 999px;
  background: var(--tui-danger); color: #fff;
  font-size: 10px; font-weight: 600; line-height: 15px;
  display: inline-block; vertical-align: 1px;
}

/* ==================== 移动端侧边抽屉（钉钉式） ==================== */
.msg-drawer-mask {
  position: fixed; inset: 0; z-index: 1200;
  background: rgba(15, 17, 21, 0.42);
}
.msg-drawer {
  position: fixed; top: 0; left: 0; bottom: 0; z-index: 1201;
  width: 78vw; max-width: 302px;
  display: flex; flex-direction: column;
  background: var(--tui-surface);
  box-shadow: var(--tui-shadow-3);
}
.msg-drawer-head {
  display: flex; align-items: center; gap: 12px;
  padding: calc(20px + env(safe-area-inset-top)) 18px 18px;
  background: var(--tui-surface);
  border-bottom: 1px solid var(--tui-hairline);
  color: var(--tui-text);
}
.msg-drawer-head :deep(.el-avatar) { border-radius: 14px; background: var(--tui-brand-soft); color: var(--tui-brand-strong); flex-shrink: 0; }
.msg-drawer-user { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.msg-drawer-name { font-size: 15.5px; font-weight: 600; color: var(--tui-text); }
.msg-drawer-sub {
  font-size: 11.5px; color: var(--tui-text-quiet);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.msg-drawer-nav { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 2px; }
.msg-drawer-item {
  display: flex; align-items: center; gap: 12px; width: 100%;
  padding: 12px; border: none; border-radius: var(--tui-radius-sm);
  background: transparent; cursor: pointer; font-family: inherit; text-align: left;
  color: var(--tui-text-secondary); font-size: 14.5px; font-weight: 500;
  transition: background .15s var(--tui-ease), color .15s var(--tui-ease);
}
.msg-drawer-item:active { background: var(--tui-surface-muted); }
.msg-drawer-item.active { background: var(--tui-brand-soft); color: var(--tui-brand-strong); font-weight: 600; }
.msg-drawer-icon { display: flex; color: inherit; }
.msg-drawer-label { flex: 1; }
.msg-drawer-foot {
  padding: 10px 12px calc(14px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--tui-border);
}
.msg-drawer-foot-btn {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 11px 12px; border: none; border-radius: var(--tui-radius-sm);
  background: transparent; cursor: pointer; font-family: inherit;
  color: var(--tui-text-tertiary); font-size: 13.5px;
}
.msg-drawer-foot-btn:active { background: var(--tui-surface-muted); }

.drawer-mask-enter-active, .drawer-mask-leave-active { transition: opacity .22s ease; }
.drawer-mask-enter-from, .drawer-mask-leave-to { opacity: 0; }
.drawer-panel-enter-active { transition: transform .26s cubic-bezier(.22, .68, 0, 1); }
.drawer-panel-leave-active { transition: transform .2s ease-in; }
.drawer-panel-enter-from, .drawer-panel-leave-to { transform: translateX(-100%); }

/* ==================== 通讯录 ==================== */
.addr-section-head { display: flex; align-items: center; gap: 8px; padding: 14px 16px 6px; }
.addr-section-title { font-size: 12.5px; font-weight: 600; color: var(--tui-text-quiet); letter-spacing: .3px; }
.addr-section-count { margin-left: auto; font-size: 11.5px; color: var(--tui-text-quiet); }
.addr-row {
  display: flex; align-items: center; gap: 12px; width: 100%;
  padding: 11px 16px; border: none; background: transparent; cursor: pointer;
  font-family: inherit; text-align: left;
  transition: background .15s var(--tui-ease);
}
.addr-row:active { background: var(--tui-surface-muted); }
.addr-row-main { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.addr-row-name { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 500; color: var(--tui-text); }
.addr-row-sub {
  font-size: 11.5px; color: var(--tui-text-quiet);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.addr-org-icon {
  width: 34px; height: 34px; flex-shrink: 0; border-radius: var(--tui-radius-sm);
  display: flex; align-items: center; justify-content: center;
  background: var(--tui-brand-soft); color: var(--tui-brand-strong);
}
.addr-org-icon.major { width: 30px; height: 30px; background: #f4f3ff; color: #6941c6; }
.addr-org-icon.klass { width: 28px; height: 28px; background: var(--tui-surface-sunken); color: var(--tui-text-tertiary); }
.addr-row-major { padding-left: 30px; }
.addr-row-class { padding-left: 48px; }
.addr-arrow { color: #cbd0d8; flex-shrink: 0; }
.addr-search-results { padding-bottom: 8px; }
.addr-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 22px 0; color: var(--tui-text-quiet); font-size: 13px;
}
.addr-empty { padding: 22px 16px; text-align: center; color: var(--tui-text-quiet); font-size: 12.5px; }

/* ==================== 通知 ==================== */
.notif-row {
  position: relative; display: flex; align-items: flex-start; gap: 12px; width: 100%;
  padding: 13px 16px; border: none; background: transparent; cursor: pointer;
  font-family: inherit; text-align: left;
  transition: background .15s var(--tui-ease);
}
.notif-row::before {
  content: ''; position: absolute; top: 0; left: 58px; right: 16px; height: 1px;
  background: var(--tui-border);
}
.notif-row:first-child::before { display: none; }
.notif-row:active { background: var(--tui-surface-muted); }
.notif-icon {
  width: 34px; height: 34px; flex-shrink: 0; border-radius: var(--tui-radius-sm);
  display: flex; align-items: center; justify-content: center;
}
.notif-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.notif-top { display: flex; align-items: baseline; gap: 8px; }
.notif-title {
  flex: 1; min-width: 0; font-size: 14px; font-weight: 600; color: var(--tui-text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.notif-time { font-size: 10.5px; color: var(--tui-text-quiet); flex-shrink: 0; }
.notif-content { font-size: 12.5px; line-height: 1.5; color: var(--tui-text-tertiary); }
.notif-row.unread .notif-content { color: var(--tui-text-secondary); }
.notif-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--tui-danger); flex-shrink: 0; margin-top: 6px; }

/* 桌面端左栏：通讯录 / 通知 行以白底呈现，与消息列表观感统一 */
@media (min-width: 768px) {
  .addr-row, .notif-row { background: var(--tui-surface); }
  .notif-row::before { left: 46px; right: 12px; }
  .addr-section-head { padding-left: 12px; padding-right: 12px; }
  .addr-row:not(.addr-row-major):not(.addr-row-class) { padding-left: 12px; padding-right: 12px; }
}

/* ===== 移动端适配（QQ 风格） ===== */
.back-btn { display: none; }
@media (max-width: 767px) {
  /* 统一底色 */
  .msg-page { flex-direction: column; border-radius: 0; border: none; box-shadow: none; background: var(--tui-bg); }
  .msg-sidebar { width: 100% !important; flex: 1; min-height: 0; border-right: none; background: var(--tui-bg); }
  .sidebar-header { background: #fff; }
  .sidebar-search { background: #fff; }
  .sidebar-scroll { background: var(--tui-bg); flex: 1; overflow-y: auto; min-height: 0; padding: 4px 0 0; }
  /* 通讯录 / 通知：移动端整行白底，靠发丝线成组，与桌面端卡片观感一致 */
  .addr-row, .notif-row { background: #fff; }
  .addr-row-major, .addr-row-class { background: #fff; }
  .addr-section-head { padding-top: 16px; }
  .conv-swipe-wrap { margin: 0 0 6px; }
  .conv-item { margin: 0; padding: 10px 14px; background: #fff; border-radius: 0; border-left: none; }
  .conv-item:hover { background: var(--tui-surface-muted); }
  .conv-item.active { background: var(--tui-brand-soft); }
  .conv-item.pinned { background: var(--tui-surface-muted); }
  .conv-swipe-wrap.swiped .conv-item { background: var(--tui-surface-muted); }
  .conv-swipe-actions { display: flex; opacity: 0; }
  .conv-swipe-wrap.swiped .conv-swipe-actions { opacity: 1; }
  .group-badge { border-color: #fff; }

  /* 聊天页 */
  .msg-chat { width: 100%; flex: 1; background: #fff; }
  .back-btn { display: inline-flex; color: var(--tui-text); }
  .chat-header {
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: saturate(180%) blur(14px);
    -webkit-backdrop-filter: saturate(180%) blur(14px);
    border-bottom: 1px solid var(--tui-hairline);
    min-height: 52px; padding: 6px 8px;
  }
  .chat-header .el-button { color: var(--tui-text); }
  .chat-name { color: var(--tui-text); font-size: 16.5px; }
  .chat-member-count { color: var(--tui-text-quiet); }
  .chat-header-group-avatar { border-radius: 8px; background: var(--tui-brand-soft); }
  .chat-header-group-avatar .el-avatar__text .el-icon { color: var(--tui-brand-strong); }
  .msg-list { padding: 12px 10px; background: var(--tui-bg); }
  .msg-row { gap: 6px; margin-bottom: 12px; }
  .msg-avatar { width: 34px !important; height: 34px !important; font-size: 14px; }
  .msg-col { max-width: 76%; }
  .bubble-image { max-width: 180px; }
  .bubble-file { min-width: 150px; }
  .msg-input-bar { padding: 7px 8px calc(7px + env(safe-area-inset-bottom)); }

  /* 弹窗在移动端走整页流程（钉钉式）：只微调触控尺寸与列表形态 */
  :deep(.el-dialog.is-fullscreen .el-dialog__body) { padding: 12px 12px 16px; }
  .member-search-results,
  .add-member-results,
  .add-friend-results,
  .manage-invite-results,
  .group-members-list {
    max-height: none; margin-top: 8px;
    border: none; border-radius: 0; background: transparent;
  }
  .member-search-item,
  .add-member-item,
  .add-friend-item,
  .manage-invite-item,
  .group-member-item {
    padding: 12px 14px;
    border-bottom: none;
    background: var(--tui-surface);
    margin-bottom: 1px;
  }
  :deep(.el-dialog .el-textarea__inner) { padding: 10px 12px; line-height: 1.6; }
  :deep(.el-dialog .el-input__inner) { font-size: 15px; }
  :deep(.manage-announcement-content),
  :deep(.manage-invite-box) { border-radius: var(--tui-radius-sm); }
}

/* ===== 移动端群设置 / 公告 / 文件子页面（QQ 风格） ===== */
.group-sub-page {
  position: fixed; inset: 0; z-index: 1200;
  background: var(--tui-bg); display: flex; flex-direction: column;
}
.gsp-header {
  display: flex; align-items: center; justify-content: space-between;
  min-height: 52px; padding: 6px 8px; background: var(--tui-surface); border-bottom: 1px solid var(--tui-hairline);
  flex-shrink: 0;
}
.gsp-title { font-size: 16.5px; font-weight: 600; color: var(--tui-text); letter-spacing: -0.2px; }
.gsp-edit-btn { color: var(--tui-brand); font-size: 14px; }
.gsp-hero {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 24px 16px 18px; background: var(--tui-surface); flex-shrink: 0;
}
.gsp-avatar-wrap { position: relative; display: flex; }
.gsp-avatar-wrap.editable { cursor: pointer; }
.gsp-avatar-wrap.editable:active { transform: scale(.96); }
.gsp-avatar {
  width: 68px; height: 68px; border-radius: var(--tui-radius-lg);
  background: var(--tui-surface-sunken); color: var(--tui-text-secondary);
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 600;
}
.gsp-avatar-cam {
  position: absolute; right: -4px; bottom: -4px;
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--tui-surface); color: var(--tui-text-secondary);
  border: 1px solid var(--tui-border);
  display: flex; align-items: center; justify-content: center;
}
.group-crop-box { max-height: 360px; overflow: hidden; }
.gsp-name { font-size: 17px; font-weight: 600; color: var(--tui-text); text-align: center; margin-top: 2px; }
.gsp-meta { font-size: 11.5px; color: var(--tui-text-quiet); }
.gsp-body { flex: 1; overflow-y: auto; padding: 16px 14px; }
.gsp-menu { background: var(--tui-surface); border: 1px solid var(--tui-border); border-radius: var(--tui-radius); overflow: hidden; box-shadow: var(--tui-shadow-1); }
.gsp-item {
  display: flex; align-items: center; gap: 12px; padding: 14px 16px;
  border-bottom: 1px solid var(--tui-border); cursor: pointer;
  font-size: 14px; color: var(--tui-text); transition: background .15s var(--tui-ease);
}
.gsp-item:active { background: var(--tui-surface-muted); }
.gsp-item:last-child { border-bottom: none; }
.gsp-item-icon {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.gsp-item-icon.announce { background: var(--tui-warn-soft); color: var(--tui-warn); }
.gsp-item-icon.filee { background: var(--tui-surface-sunken); color: var(--tui-text-tertiary); }
.gsp-item-icon.member { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.gsp-item-icon.add { background: var(--tui-success-soft); color: var(--tui-success); }
.gsp-item-icon.manage { background: var(--tui-surface-sunken); color: var(--tui-text-tertiary); }
.gsp-item-label { flex: 1; }
.gsp-item-value { font-size: 12px; color: var(--tui-text-quiet); }
.gsp-arrow { font-size: 14px; }
.gsp-danger-btn {
  margin-top: 16px; width: 100%; padding: 13px 0; border: none; border-radius: 12px;
  background: var(--tui-surface); color: var(--tui-danger); font-size: 14.5px; cursor: pointer;
}
.gsp-empty-box {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 56px 0 30px; color: var(--tui-text-quiet); font-size: 14px;
  background: var(--tui-surface); border-radius: var(--tui-radius);
}
.gsp-empty-box small { font-size: 12px; color: var(--tui-text-quiet); }
.gsp-ann-card { background: var(--tui-surface); border: 1px solid var(--tui-border); border-radius: var(--tui-radius); padding: 16px; }
.gsp-ann-head {
  display: flex; align-items: center; gap: 6px;
  font-size: 15px; font-weight: 600; color: var(--tui-text); margin-bottom: 10px;
}
.gsp-ann-head .el-icon { color: var(--tui-warn); }
.gsp-ann-text { margin: 0; font-size: 14px; color: var(--tui-text-secondary); line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.gsp-ann-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.gsp-cancel-btn, .gsp-save-btn { padding: 8px 22px; border-radius: 8px; font-size: 14px; border: none; cursor: pointer; }
.gsp-cancel-btn { background: var(--tui-surface-sunken); color: var(--tui-text-secondary); }
.gsp-save-btn { background: var(--tui-brand); color: #fff; }
.gsp-save-btn:disabled { opacity: .5; cursor: not-allowed; }
.gsp-file-list { background: var(--tui-surface); border: 1px solid var(--tui-border); border-radius: var(--tui-radius); overflow: hidden; margin-bottom: 14px; }
.gsp-file-item {
  display: flex; align-items: center; gap: 10px; padding: 12px 14px;
  border-bottom: 1px solid var(--tui-border); cursor: pointer;
}
.gsp-file-item:last-child { border-bottom: none; }
.gsp-file-icon {
  width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
  background: var(--tui-surface-sunken); color: var(--tui-text-tertiary);
  display: flex; align-items: center; justify-content: center;
}
.gsp-file-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.gsp-file-name { font-size: 14px; color: var(--tui-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gsp-file-meta { font-size: 11px; color: var(--tui-text-quiet); }
.gsp-upload-btn {
  width: 100%; padding: 13px 0; border: 1px dashed var(--tui-border-strong); border-radius: var(--tui-radius-sm);
  background: var(--tui-surface); color: var(--tui-text-secondary); font-size: 14px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.gsp-upload-btn:active { background: var(--tui-surface-muted); }
</style>