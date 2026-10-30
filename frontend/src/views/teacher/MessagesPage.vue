<template>
  <div class="msg-page">
    <!-- 移动端吸顶栏：会话 / 通讯录 / 通知 三视图共用（聊天态由会话页头接管） -->
    <header v-if="isMobile && !activeId" class="msg-appbar">
      <button class="msg-appbar-btn" type="button" aria-label="打开侧边导航" @click="drawerOpen = true">
        <DtIcon name="menu" :size="21" />
      </button>
      <div class="msg-appbar-title">{{ mobileViewTitle }}</div>
      <div class="msg-appbar-actions">
        <el-dropdown
          v-if="mobileView === 'messages'"
          trigger="click"
          @command="handleHeaderAction"
        >
          <button class="msg-appbar-btn" type="button" aria-label="更多操作">
            <DtIcon name="plus" :size="20" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="createGroup">
                <DtIcon name="message" :size="15" /> 创建群聊
              </el-dropdown-item>
              <el-dropdown-item command="addFriend">
                <DtIcon name="user" :size="15" /> 发起会话
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button
          v-if="hasUnread"
          class="msg-appbar-btn"
          type="button"
          aria-label="清除未读提示"
          @click="handleClearUnread"
        >
          <DtIcon name="check" :size="19" />
        </button>
      </div>
    </header>

    <!-- 移动端：视图切换收进侧边抽屉（吸顶栏汉堡按钮唤起），左栏只承载当前视图内容 -->
    <div class="msg-sidebar" v-show="isMobile ? !activeId : true">
      <!-- 桌面端头部（钉钉式）：整行搜索框 + 右侧「+」新建；刷新 / 清除未读收进「+」菜单 -->
      <div v-if="!isMobile" class="sidebar-header">
        <div class="sidebar-searchbar">
          <el-input
            v-if="mobileView !== 'notifications'"
            v-model="headerKeyword"
            :placeholder="headerSearchPlaceholder"
            size="small"
            clearable
            @input="onHeaderSearch"
          >
            <template #prefix><DtIcon name="search" :size="15" /></template>
          </el-input>
        </div>
        <el-dropdown trigger="click" @command="handleHeaderAction">
          <button class="header-plus-btn" type="button" aria-label="新建 / 更多">
            <DtIcon name="plus" :size="20" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="createGroup">
                <DtIcon name="message" :size="15" /> 创建群聊
              </el-dropdown-item>
              <el-dropdown-item command="addFriend">
                <DtIcon name="user" :size="15" /> 发起会话
              </el-dropdown-item>
              <el-dropdown-item command="clearUnread">
                <DtIcon name="bell" :size="15" /> 清除未读提示
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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

      <div class="sidebar-scroll"
        @touchstart.passive="sidebarPull.onStart"
        @touchmove="sidebarPull.onMove"
        @touchend="sidebarPull.onEnd"
        @touchcancel="sidebarPull.onCancel">
        <!-- 移动端下拉刷新：吉祥物指示器（公共模块，与首页共用同一套动画） -->
        <PullRefreshIndicator :indicator-style="sidebarPull.indicatorStyle" :active="sidebarPull.active" />
        <!-- ============ 视图一：消息（会话列表） ============ -->
        <template v-if="mobileView === 'messages'">
        <!-- 移动端专用：桌面端搜索已上移至钉钉式头部（整宽搜索框） -->
        <div v-if="isMobile" class="sidebar-search">
          <el-input v-model="search" placeholder="搜索已有会话" size="small" clearable
            @input="filterConversations">
            <template #prefix><DtIcon name="search" :size="15" /></template>
          </el-input>
        </div>

        <!-- 小绵管家：置顶常驻会话（自动推送最新资讯 / 总结对话内容） -->
        <div
          class="conv-item butler-entry"
          :class="{ active: activeType === 'butler' && !!activeId }"
          @click="openButler"
        >
          <div class="conv-avatar-wrapper">
            <span class="butler-entry-avatar">
              <img v-if="siteMascot" :src="siteMascot" alt="小绵管家" />
              <DtIcon v-else name="robot" :size="20" />
            </span>
            <span class="butler-entry-online" />
          </div>
          <div class="conv-info">
            <div class="conv-top">
              <span class="conv-name">{{ agentName || '小绵' }}管家</span>
              <span class="dt-tag">常驻</span>
            </div>
            <div class="conv-bottom">
              <span class="conv-preview">{{ butlerPreview }}</span>
            </div>
          </div>
        </div>

        <template v-if="filteredList.length === 0">
          <div class="empty-state">
            <DtIcon name="empty" :size="40" style="color: var(--dt-text-quiet);" />
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
                <button class="swipe-action danger" @click="handleDeleteSession(item)">删除</button>
              </div>
              <div class="conv-item" :class="{ active: activeId === item.id && activeType === 'group', pinned: isPinned(item._key) }"
                @click="openChat(item.id, item.name, 'group')"
                @touchstart="onSwipeStart($event, item._key)"
                @touchmove="onSwipeMove($event)"
                @touchend="onSwipeEnd($event)">
                <div class="conv-avatar-wrapper">
                  <el-badge :value="item.unread_count" :hidden="!item.unread_count" :max="99" class="conv-badge-avatar">
                    <el-avatar :size="44" :src="item.avatar || undefined">{{ item.name[0] }}</el-avatar>
                  </el-badge>
                  <span class="group-badge">群</span>
                </div>
                <div class="conv-info">
                  <div class="conv-top">
                    <span class="conv-name">{{ item.name }}</span>
                    <DtIcon v-if="item.is_muted" name="bellOff" :size="13" class="conv-mute" />
                    <span class="conv-time">{{ formatConvTime(item.last_message_time) }}</span>
                  </div>
                  <div class="conv-bottom">
                    <span v-if="item.online_count" class="conv-online-count">{{ item.online_count }}人在线</span>
                    <span class="conv-preview">{{ item.last_message || '暂无消息' }}</span>
                  </div>
                </div>
                <!-- 桌面端置顶 / 删除入口（移动端用右滑手势） -->
                <button
                  v-if="!isMobile"
                  type="button"
                  class="conv-pin-btn"
                  :class="{ on: isPinned(item._key) }"
                  :aria-label="isPinned(item._key) ? '取消置顶' : '置顶会话'"
                  @click.stop="togglePin(item._key)"
                >
                  <DtIcon name="pin" :size="13" />
                </button>
                <button
                  v-if="!isMobile"
                  type="button"
                  class="conv-del-btn"
                  aria-label="删除会话"
                  @click.stop="handleDeleteSession(item)"
                >
                  <DtIcon name="trash" :size="13" />
                </button>
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
                <button class="swipe-action danger" @click="handleDeleteSession(item)">删除</button>
              </div>
              <div class="conv-item" :class="{ active: activeId === item.id && activeType === 'single', pinned: isPinned(item._key) }"
                @click="openChat(item.id, item.name, 'single')"
                @touchstart="onSwipeStart($event, item._key)"
                @touchmove="onSwipeMove($event)"
                @touchend="onSwipeEnd($event)">
                <div class="conv-avatar-wrapper">
                  <el-badge :value="item.unread_count" :hidden="!item.unread_count" :max="99" class="conv-badge-avatar">
                    <el-avatar
                      :size="44"
                      :src="item.user_avatar || undefined"
                      class="conv-avatar-clickable"
                      title="查看个人主页"
                      @click.stop="openUserHomepage(item.id)"
                    >{{ item.name[0] }}</el-avatar>
                  </el-badge>
                  <span v-if="isOnline(item.id)" class="conv-online-dot" title="在线" />
                </div>
                <div class="conv-info">
                  <div class="conv-top">
                    <span class="conv-name">{{ item.name }}</span>
                    <span class="conv-time">{{ formatConvTime(item.last_message_time) }}</span>
                  </div>
                  <div class="conv-bottom">
                    <span class="conv-preview">{{ item.last_message }}</span>
                  </div>
                </div>
                <!-- 桌面端置顶 / 删除入口（移动端用右滑手势） -->
                <button
                  v-if="!isMobile"
                  type="button"
                  class="conv-pin-btn"
                  :class="{ on: isPinned(item._key) }"
                  :aria-label="isPinned(item._key) ? '取消置顶' : '置顶会话'"
                  @click.stop="togglePin(item._key)"
                >
                  <DtIcon name="pin" :size="13" />
                </button>
                <button
                  v-if="!isMobile"
                  type="button"
                  class="conv-del-btn"
                  aria-label="删除会话"
                  @click.stop="handleDeleteSession(item)"
                >
                  <DtIcon name="trash" :size="13" />
                </button>
              </div>
            </div>
          </template>
        </template>
        </template>

        <!-- ============ 视图二：通讯录 ============ -->
        <template v-else-if="mobileView === 'contacts'">
          <!-- 全校师生检索：命中即可直接发起会话（移动端内嵌；桌面端用头部搜索） -->
          <div v-if="isMobile" class="sidebar-search">
            <el-input
              v-model="contactKeyword"
              placeholder="搜索姓名 / 学号 / 工号"
              size="small"
              clearable
              @input="onContactSearch"
            >
              <template #prefix><DtIcon name="search" :size="15" /></template>
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
              <el-avatar :size="38" :src="u.avatar || undefined" class="addr-avatar" @click.stop="openUserHomepage(u.id)">{{ u.name[0] }}</el-avatar>
              <span class="addr-row-main">
                <span class="addr-row-name">
                  {{ u.name }}
                  <span class="tui-tag" :class="roleTagClass(u.role)">
                    {{ roleLabel(u.role) }}
                  </span>
                </span>
                <span class="addr-row-sub">{{ u.username }}</span>
              </span>
            </button>
          </div>

          <template v-else>
            <!-- 最近联系人：聊过天的人自动进入通讯录，可一键发起会话 -->
            <template v-if="recentContacts.length">
              <div class="addr-section-head">
                <span class="addr-section-title">最近联系人</span>
                <span class="addr-section-count">{{ recentContacts.length }} 人</span>
              </div>
              <button
                v-for="c in recentContacts"
                :key="c.id"
                type="button"
                class="addr-row"
                @click="startChatWith(c)"
              >
                <el-avatar :size="38" :src="c.avatar || undefined" class="addr-avatar" @click.stop="openUserHomepage(c.id)">{{ c.name[0] }}</el-avatar>
                <span class="addr-row-main">
                  <span class="addr-row-name">{{ c.name }}</span>
                  <span class="addr-row-sub">{{ c.online ? '在线' : '离线' }}</span>
                </span>
              </button>
            </template>

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
              <el-avatar :size="38" :src="s.avatar || undefined" class="addr-avatar" @click.stop="openUserHomepage(s.id)">{{ s.name[0] }}</el-avatar>
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
              <span class="addr-section-count">
                {{ orgScopeRestricted ? (orgScope?.college_name || '仅展示所在组织') : `${orgColleges.length} 个学院` }}
              </span>
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
                <DtIcon
                  name="arrow"
                  :size="14"
                  class="addr-chevron"
                  :class="{ open: expandedColleges.has(c.id) }"
                />
              </button>
              <template v-if="expandedColleges.has(c.id)">
                <template v-for="m in (orgMajors[c.id] || [])" :key="m.id">
                  <button type="button" class="addr-row addr-row-major" @click="toggleOrgMajor(m.id)">
                    <span class="addr-org-icon major"><el-icon :size="15"><Collection /></el-icon></span>
                    <span class="addr-row-main">
                      <span class="addr-row-name">{{ m.name }}</span>
                    </span>
                    <DtIcon
                      name="arrow"
                      :size="14"
                      class="addr-chevron"
                      :class="{ open: expandedMajors.has(m.id) }"
                    />
                  </button>
                  <template v-if="expandedMajors.has(m.id)">
                    <template v-for="cg in (orgClasses[m.id] || [])" :key="cg.id">
                      <button type="button" class="addr-row addr-row-class" @click="toggleOrgClass(cg.id)">
                        <span class="addr-org-icon klass"><el-icon :size="14"><Notebook /></el-icon></span>
                        <span class="addr-row-main">
                          <span class="addr-row-name">{{ cg.name }}</span>
                          <span class="addr-row-sub">{{ cg.grade }} 级 · {{ cg.student_count ?? 0 }} 人</span>
                        </span>
                        <DtIcon
                          name="arrow"
                          :size="14"
                          class="addr-chevron"
                          :class="{ open: expandedClasses.has(cg.id) }"
                        />
                      </button>
                      <!-- 班级 → 学生名单 → 点任意学生直接发起会话（闭环） -->
                      <template v-if="expandedClasses.has(cg.id)">
                        <div v-if="classStudentsLoading[cg.id]" class="addr-loading">
                          <el-icon class="is-loading"><Loading /></el-icon><span>加载中…</span>
                        </div>
                        <div v-else-if="!(classStudents[cg.id] || []).length" class="addr-empty">该班级暂无学生</div>
                        <button
                          v-for="s in (classStudents[cg.id] || [])"
                          :key="s.id"
                          type="button"
                          class="addr-row addr-row-student"
                          @click="startChatWith(s)"
                        >
                          <el-avatar :size="32" :src="s.avatar || undefined">{{ s.name?.[0] }}</el-avatar>
                          <span class="addr-row-main">
                            <span class="addr-row-name">
                              {{ s.name }}
                              <span v-if="s.crisis_level && s.crisis_level !== 'none'" class="tui-tag tui-tag-danger">关注</span>
                            </span>
                            <span class="addr-row-sub">{{ s.username }}</span>
                          </span>
                        </button>
                      </template>
                    </template>
                  </template>
                </template>
              </template>
            </template>
            </template>
          </template>
        </template>

        <!-- ============ 视图三：文件（跨会话汇总，QQ「文件」页） ============ -->
        <template v-else-if="mobileView === 'files'">
          <!-- 顶部：搜索 + 类别筛选；搜索框与类别、类别与列表之间都留出间距 -->
          <div class="file-topbar">
            <!-- 移动端内嵌文件搜索；桌面端用钉钉式头部搜索 -->
            <el-input v-if="isMobile" v-model="fileKeyword" placeholder="搜索文件名" size="small" clearable @input="onFileSearch">
              <template #prefix><DtIcon name="search" :size="15" /></template>
            </el-input>

            <div class="file-filter">
              <button
                v-for="f in FILE_TYPE_FILTERS"
                :key="f.key"
                type="button"
                class="file-filter-item"
                :class="{ active: fileTypeFilter === f.key }"
                @click="setFileTypeFilter(f.key)"
              >{{ f.label }}</button>
            </div>
          </div>

          <div v-if="filesLoading" class="addr-loading">
            <el-icon class="is-loading"><Loading /></el-icon><span>加载中…</span>
          </div>
          <div v-else-if="!sharedFiles.length" class="empty-state">
            <DtIcon name="empty" :size="40" style="color: var(--dt-text-quiet);" />
            <span>{{ fileKeyword.trim() ? '未找到匹配的文件' : '暂无聊天文件' }}</span>
          </div>
          <div v-else class="file-list">
            <div v-for="f in sharedFiles" :key="f.id" class="file-item" @click="openSharedFile(f)">
              <div class="file-thumb" :class="'t-' + f.file_type">
                <img v-if="f.file_type === 'image'" :src="f.url" alt="" loading="lazy" />
                <el-icon v-else :size="18"><component :is="fileTypeIcon(f.file_type)" /></el-icon>
              </div>
              <div class="file-body">
                <div class="file-name">
                  <template v-if="f.file_type === 'voice'">语音消息 · {{ f.duration || 1 }}″</template>
                  <template v-else>{{ f.name || '未命名文件' }}</template>
                </div>
                <div class="file-meta">
                  <span class="file-source" :title="f.session_name" @click.stop="openFileSession(f)">
                    <span v-if="f.is_group" class="file-src-tag">群</span>{{ f.session_name || '会话' }}
                  </span>
                  <span>{{ f.sender_name }}</span>
                  <span>{{ formatTime(f.created_at) }}</span>
                </div>
              </div>
              <el-icon class="file-action" :size="16">
                <View v-if="f.file_type === 'image'" />
                <Download v-else />
              </el-icon>
            </div>
          </div>
        </template>

        <!-- ============ 视图四：通知（不设分类筛选，按时间倒序直出） ============ -->
        <template v-else>
          <!-- 桌面端：通知无吸顶栏，提供「全部标记已读」入口 -->
          <div v-if="!isMobile && notifications.length" class="notif-actions">
            <button
              type="button"
              class="notif-action-btn"
              :disabled="!unreadNotifCount"
              @click="handleReadAllNotifications"
            >
              全部标记已读
            </button>
          </div>
          <div v-if="notifLoading && !notifications.length" class="addr-loading">
            <el-icon class="is-loading"><Loading /></el-icon><span>加载中…</span>
          </div>
          <div v-else-if="!notifications.length" class="empty-state">
            <DtIcon name="bell" :size="40" style="color: var(--dt-text-quiet);" />
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
        <!-- 桌面端：聊天主列 + 右侧常驻会话信息面板（≥1200px 显示的列，窄屏由 CSS 隐藏） -->
        <div class="chat-body">
        <div class="chat-main">
        <div class="chat-header">
          <div class="chat-header-left">
            <el-button text circle @click="goBack" class="back-btn" v-show="isMobile">
              <DtIcon name="back" :size="20" />
            </el-button>
            <el-avatar v-if="isMobile && activeType === 'group'" :size="34"
              :src="currentGroup?.avatar || undefined" class="chat-header-group-avatar">
              <DtIcon name="users" :size="16" />
            </el-avatar>
            <!-- 移动端单聊：显示对方头像，仅作身份标识（进主页的入口固定在右上角，与 QQ 一致） -->
            <el-avatar
              v-else-if="isMobile && activeType === 'single' && activeId"
              :size="34"
              :src="singlePeerAvatar || undefined"
              class="chat-header-peer-avatar"
            >{{ activeName?.[0] }}</el-avatar>
            <div class="chat-header-info">
              <div class="chat-name">{{ activeName }}</div>
              <div v-if="chatSubtitle" class="chat-sub">{{ chatSubtitle }}</div>
            </div>
          </div>
          <div class="chat-header-right">
            <!-- 单聊：右上角固定入口，进对方个人主页（QQ 资料卡逻辑） -->
            <el-button
              v-if="activeType === 'single' && activeId"
              text
              circle
              class="chat-head-homepage"
              title="查看个人主页"
              @click="openUserHomepage(activeId)"
            >
              <DtIcon name="user" :size="isMobile ? 20 : 18" />
            </el-button>
            <!-- 群聊：消息免打扰一键开关（复用群设置同一条逻辑） -->
            <button
              v-if="activeType === 'group'"
              type="button"
              class="chat-head-btn"
              :class="{ on: groupMuted }"
              :title="groupMuted ? '关闭消息免打扰' : '开启消息免打扰'"
              @click="onMuteChange(!groupMuted)"
            >
              <DtIcon name="bellOff" :size="18" />
            </button>
            <!-- 移动端群聊：更多（群设置 / 加入任务） -->
            <el-dropdown v-if="isMobile && activeType === 'group'" trigger="click">
              <el-button text circle class="header-more">
                <DtIcon name="menu" :size="20" />
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openGroupSettings">
                    <DtIcon name="settings" :size="15" /> 群设置
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="addToTask">
                    <DtIcon name="calendar" :size="15" /> 加入任务
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <!-- 桌面端群聊：更多（群管理 / 成员 / 加入任务） -->
            <el-dropdown v-if="!isMobile && activeType === 'group'" trigger="click">
              <el-button text circle><DtIcon name="more" :size="18" /></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="showManageGroup = true">
                    <DtIcon name="settings" :size="15" /> 群管理
                  </el-dropdown-item>
                  <el-dropdown-item @click="showAddMember = true">
                    <DtIcon name="plus" :size="15" /> 添加成员
                  </el-dropdown-item>
                  <el-dropdown-item @click="openMemberList">
                    <DtIcon name="users" :size="15" /> 查看成员
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="addToTask">
                    <DtIcon name="calendar" :size="15" /> 加入任务
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <!-- 单聊：更多（对方为学生时含档案 / 关怀；任何单聊都可加入任务） -->
            <el-dropdown v-if="activeType === 'single' && activeId" trigger="click" @command="onStudentMenuCommand">
              <el-button text circle class="header-more">
                <DtIcon :name="isMobile ? 'menu' : 'more'" :size="isMobile ? 20 : 18" />
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="isMyStudent" command="profile">
                    <DtIcon name="document" :size="15" /> 查看档案
                  </el-dropdown-item>
                  <el-dropdown-item v-if="isMyStudent" command="care">
                    <DtIcon name="heart" :size="15" /> 记录关怀
                  </el-dropdown-item>
                  <el-dropdown-item :divided="isMyStudent" @click="addToTask">
                    <DtIcon name="calendar" :size="15" /> 加入任务
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 群公告条：有公告时常驻于聊天头下方，点击进入群公告（桌面端群管理弹窗 / 移动端公告子页） -->
        <div
          v-if="activeType === 'group' && currentGroup?.announcement"
          class="chat-announce"
          @click="isMobile ? (groupSubPage = 'announcement') : (showManageGroup = true)"
        >
          <DtIcon name="bell" :size="14" class="chat-announce-icon" />
          <span class="chat-announce-text">{{ currentGroup.announcement }}</span>
          <DtIcon name="arrow" :size="13" class="chat-announce-arrow" />
        </div>

        <!-- 小绵管家会话：自动推送最新资讯 + 总结对话内容（教师 / 学生通用） -->
        <ButlerChat v-if="activeType === 'butler'" role="teacher" />

        <template v-else>
        <div class="msg-list" ref="msgListRef"
          @touchstart.passive="chatPull.onStart"
          @touchmove="chatPull.onMove"
          @touchend="chatPull.onEnd"
          @touchcancel="chatPull.onCancel"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
          @paste="onPaste">
          <!-- 移动端下拉刷新：吉祥物指示器（公共模块，与首页共用同一套动画） -->
          <PullRefreshIndicator :indicator-style="chatPull.indicatorStyle" :active="chatPull.active" />
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
                  <!-- 文件/图片/语音消息 -->
                  <template v-if="getMsgMeta(item.msg).isFile">
                    <div v-if="getMsgMeta(item.msg).fileType === 'image'" class="bubble-image"
                      @click="previewImage(getMsgMeta(item.msg).url)">
                      <img :src="getMsgMeta(item.msg).url" :alt="getMsgMeta(item.msg).text" />
                    </div>
                    <div v-else-if="getMsgMeta(item.msg).fileType === 'voice'" class="bubble-voice"
                      :class="{ playing: playingVoiceUrl === getMsgMeta(item.msg).url }"
                      :style="{ width: voiceBubbleWidth(getMsgMeta(item.msg).duration) }"
                      @click="toggleVoicePlay(getMsgMeta(item.msg).url)">
                      <el-icon :size="16" class="voice-play-icon">
                        <VideoPause v-if="playingVoiceUrl === getMsgMeta(item.msg).url" />
                        <VideoPlay v-else />
                      </el-icon>
                      <span class="voice-bars"><i v-for="n in 3" :key="n" /></span>
                      <span class="voice-dur">{{ (getMsgMeta(item.msg).duration || 1) }}″</span>
                    </div>
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
              </div>
            </div>
          </template>
          <div v-if="messages.length === 0" class="chat-empty">
            <DtIcon name="empty" :size="48" style="color: var(--dt-text-quiet);" />
            <span>暂无聊天记录</span>
          </div>
        </div>

        <div class="msg-composer">
          <div class="msg-input-bar">
            <!-- 左侧：语音输入 / 键盘切换 -->
            <button class="tool-btn" type="button"
              :title="voiceMode ? '切换到键盘' : '语音输入'" aria-label="语音输入" @click="toggleVoiceMode">
              <el-icon :size="20"><EditPen v-if="voiceMode" /><Microphone v-else /></el-icon>
            </button>

            <div class="input-main composer-input">
              <!-- 语音模式：QQ 风格「按住说话」 -->
              <button v-if="voiceMode" class="hold-talk" type="button"
                :class="{ recording: isRecording, cancel: recordCancelled }"
                @pointerdown.prevent="onTalkStart"
                @pointermove="onTalkMove"
                @pointerup="onTalkEnd"
                @pointercancel="onTalkCancel"
                @contextmenu.prevent>
                {{ isRecording ? (recordCancelled ? '松开取消' : '松开发送') : '按住 说话' }}
              </button>
              <el-input v-else v-model="newMsg" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="输入消息..."
                @keydown.enter.exact.prevent="sendMsg" />
            </div>

            <!-- 右侧：表情 -->
            <button class="tool-btn" :class="{ active: showEmoji }" type="button" title="表情"
              aria-label="表情" @click="toggleEmoji">
              <DtIcon name="smile" :size="21" />
            </button>

            <!-- 右侧动作槽：无内容 → 加号；有内容 → 发送（同尺寸叠放，切换不重排） -->
            <div class="action-slot">
              <button class="send-btn" :class="hasText ? 'visible' : 'hidden'" type="button" @click="sendMsg">发送</button>
              <button class="tool-btn plus-action" :class="[!hasText ? 'visible' : 'hidden', { active: showAttachPanel }]"
                type="button" title="更多" aria-label="更多" @click="toggleAttachPanel">
                <DtIcon name="plus" :size="21" />
              </button>
            </div>
          </div>

          <!-- 底部展开面板（表情 / 更多）：单容器统一定高，内容切换不改变高度，自下而上滑出 -->
          <div class="composer-panel" :class="{ open: !!activePanel }">
            <div class="composer-panel-head">{{ activePanel === 'plus' ? '更多' : '表情' }}</div>
            <!-- 更多：图片 / 文件 -->
            <div v-if="activePanel === 'plus'" class="plus-grid">
              <button class="plus-fn" type="button" @click="pickImage">
                <span class="plus-fn-icon"><DtIcon name="image" :size="24" /></span>
                <span class="plus-fn-label">图片</span>
              </button>
              <button class="plus-fn" type="button" @click="pickFile">
                <span class="plus-fn-icon"><DtIcon name="document" :size="24" /></span>
                <span class="plus-fn-label">文件</span>
              </button>
            </div>
            <!-- 表情 -->
            <div v-else-if="activePanel === 'emoji'" class="emoji-grid">
              <button v-for="e in EMOJIS" :key="e" type="button" class="emoji-cell"
                :title="e" @click="insertEmoji(e)">{{ e }}</button>
            </div>
          </div>

          <input type="file" multiple hidden ref="fileInputRef" @change="onFileSelect"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.txt" />
          <input type="file" multiple hidden ref="imageInputRef" @change="onFileSelect"
            accept=".jpg,.jpeg,.png,.gif,.bmp" />

          <!-- 录音浮层：松开发送 / 上滑取消 -->
          <Transition name="fade">
            <div v-if="isRecording" class="record-overlay" :class="{ cancel: recordCancelled }">
              <DtIcon name="microphone" :size="30" />
              <div class="record-time">{{ recordSeconds }}″</div>
              <div class="record-hint">{{ recordCancelled ? '松开手指，取消发送' : '手指上滑，取消发送' }}</div>
            </div>
          </Transition>
        </div>
        </template>
        </div>

        <!-- 桌面端常驻「会话信息」面板（≥1200px 显示；窄屏由 CSS 隐藏，成员/档案入口回退到弹窗与移动子页） -->
        <aside v-if="activeType !== 'butler'" class="chat-info-panel">
          <!-- 群聊：群成员列表（复用现有群成员数据与弹窗逻辑） -->
          <template v-if="activeType === 'group'">
            <div class="info-profile">
              <el-avatar :size="56" :src="currentGroup?.avatar || undefined" class="info-profile-avatar">
                {{ (currentGroup?.name || activeName || '群')[0] }}
              </el-avatar>
              <div class="info-profile-name">{{ currentGroup?.name || activeName }}</div>
              <div class="info-profile-sub">{{ currentGroup?.member_count || groupMembers.length }} 名成员</div>
            </div>
            <div class="info-section">
              <div class="info-section-head">
                <span class="info-section-title">群成员</span>
                <button type="button" class="info-link" @click="openMemberList">全部成员</button>
              </div>
              <div v-if="groupMembers.length" class="info-member-grid">
                <button
                  v-for="m in groupMembers.slice(0, 9)"
                  :key="m.user_id"
                  type="button"
                  class="info-member"
                  @click="openUserHomepage(m.user_id)"
                >
                  <el-avatar :size="38" :src="m.user_avatar || undefined">{{ m.user_name?.[0] }}</el-avatar>
                  <span class="info-member-name">{{ m.user_name }}</span>
                </button>
                <button type="button" class="info-member info-member-add" @click="showAddMember = true">
                  <span class="info-member-add-icon"><DtIcon name="plus" :size="18" /></span>
                  <span class="info-member-name">添加</span>
                </button>
              </div>
              <div v-else class="info-empty">暂无成员数据</div>
            </div>
            <div class="info-actions">
              <button type="button" class="info-btn" @click="showManageGroup = true">群设置</button>
              <button type="button" class="info-btn" @click="openMemberList">成员管理</button>
            </div>
          </template>
          <!-- 单聊：对方资料 + 学生档案 / 关怀入口 -->
          <template v-else>
            <div class="info-profile">
              <el-avatar :size="56" :src="singlePeerAvatar || undefined" class="info-profile-avatar">
                {{ (activeName || '?')[0] }}
              </el-avatar>
              <div class="info-profile-name">{{ activeName }}</div>
              <div class="info-profile-sub">{{ chatSubtitle }}</div>
            </div>
            <div class="info-actions info-actions--col">
              <button type="button" class="info-btn" @click="openUserHomepage(singlePeerId)">查看个人主页</button>
              <button v-if="isMyStudent" type="button" class="info-btn" @click="onStudentMenuCommand('profile')">查看档案</button>
              <button v-if="isMyStudent" type="button" class="info-btn info-btn--primary" @click="onStudentMenuCommand('care')">记录关怀</button>
            </div>
          </template>
        </aside>
        </div>
      </template>

      <div v-else class="no-selection">
        <DtIcon name="empty" :size="72" style="color: var(--dt-text-quiet); margin: 0 auto;" />
        <h2>智慧校园消息中心</h2>
        <p>选择一个会话开始聊天</p>
        <div class="quick-actions">
          <el-button type="primary" @click="openButler">
            <DtIcon name="robot" :size="16" /> 小绵管家
          </el-button>
          <el-button @click="showAddFriend = true">
            <DtIcon name="user" :size="16" /> 发起会话
          </el-button>
          <el-button @click="showCreateGroup = true">
            <DtIcon name="message" :size="16" /> 创建群聊
          </el-button>
        </div>
      </div>
    </div>

    <!-- ============= 添加好友弹窗 ============= -->
    <!-- 选择联系人（搜索+列表：移动端=全屏子页 / 桌面端=弹窗） -->
    <ResponsivePopup v-model="showAddFriend" class="dt-dialog-limit" title="选择联系人" width="440px" @opened="focusAddFriendInput">
      <div class="add-friend-dialog">
        <div class="add-friend-search-box">
          <el-input ref="addFriendInputRef" v-model="addFriendSearch" placeholder="输入学号、工号或姓名搜索"
            size="large" clearable @input="onAddFriendSearch">
            <template #prefix><DtIcon name="search" :size="17" /></template>
          </el-input>
          <div class="add-friend-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>可搜索全校师生直接发起会话，支持学号/工号/姓名检索</span>
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
            <div class="add-friend-item-left is-clickable" title="查看个人主页" @click="openUserHomepage(u.id)">
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
              <DtIcon name="message" :size="15" /> 聊天
            </el-button>
          </div>
        </div>
      </div>
    </ResponsivePopup>

    <!-- ============= 创建群聊弹窗 ============= -->
    <!-- 发起群聊（表单+选人：移动端=全屏子页） -->
    <ResponsivePopup v-model="showCreateGroup" class="dt-dialog-limit" title="发起群聊" width="440px">
      <div class="create-group-form">
        <el-input v-model="newGroupName" placeholder="请输入群名称" maxlength="20" show-word-limit size="large" />
        <div class="member-search-box" style="margin-top:14px">
          <el-input v-model="memberSearch" placeholder="搜索成员（学号/工号/姓名）" size="small"
            @input="searchMembersForGroup" clearable>
            <template #prefix><DtIcon name="search" :size="15" /></template>
          </el-input>
        </div>
        <!-- 快速勾选：直接从通讯录（最近联系人）多选成员，免去逐个搜索 -->
        <div v-if="!memberSearch.trim() && recentContacts.length" class="group-pick">
          <div class="group-pick-head">
            <span>最近联系人</span>
            <span class="group-pick-hint">点击勾选</span>
          </div>
          <div class="group-pick-list">
            <div
              v-for="c in recentContacts"
              :key="c.id"
              class="group-pick-row"
              :class="{ picked: isMemberSelected(c.id) }"
              @click="toggleRecentContact(c)"
            >
              <el-checkbox :model-value="isMemberSelected(c.id)" class="group-pick-check" />
              <el-avatar :size="30" :src="c.avatar || undefined">{{ c.name[0] }}</el-avatar>
              <span class="group-pick-name">{{ c.name }}</span>
            </div>
          </div>
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
            <DtIcon v-if="selectedMembers.some(m => m.id === u.id)" name="check" :size="16" style="color: var(--dt-primary)" />
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCreateGroup = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup" :disabled="!newGroupName.trim()">创建</el-button>
      </template>
    </ResponsivePopup>

    <!-- ============= 添加群成员弹窗 ============= -->
    <!-- 邀请成员（搜索选人：移动端=全屏子页） -->
    <ResponsivePopup v-model="showAddMember" class="dt-dialog-limit" title="邀请成员" width="440px">
      <el-input v-model="addMemberSearch" placeholder="搜索用户" clearable @input="searchMembersToAdd">
        <template #prefix><DtIcon name="search" :size="15" /></template>
      </el-input>
      <div v-if="addMemberResults.length" class="add-member-results">
        <div v-for="u in addMemberResults" :key="u.id" class="add-member-item" @click="handleAddMember(u.id)">
          <el-avatar :size="36">{{ u.name[0] }}</el-avatar>
          <div class="add-member-info">
            <span>{{ u.name }}</span>
            <small>{{ u.username }}</small>
          </div>
          <DtIcon name="plus" :size="18" style="color: var(--dt-primary)" />
        </div>
      </div>
    </ResponsivePopup>

    <!-- ============= 群成员列表弹窗（群主/管理员可移除成员） ============= -->
    <!-- 群成员（列表：移动端=全屏子页） -->
    <ResponsivePopup v-model="showGroupMembers" class="dt-dialog-limit" title="群成员" width="380px">
      <div class="group-members-list">
        <div v-for="m in groupMembers" :key="m.user_id" class="group-member-item">
          <el-avatar :size="36" class="conv-avatar-clickable" title="查看个人主页" @click="openUserHomepage(m.user_id)">{{ m.user_name[0] }}</el-avatar>
          <div class="member-info">
            <span class="member-name">{{ m.user_name }}</span>
            <el-tag v-if="m.role === 'owner'" type="danger" size="small">群主</el-tag>
            <el-tag v-else-if="m.role === 'admin'" type="warning" size="small">管理员</el-tag>
          </div>
          <el-button
            v-if="canRemoveMember(m)"
            type="danger"
            text
            size="small"
            @click="handleRemoveMember(m.user_id, m.user_name)"
          >
            移除
          </el-button>
        </div>
      </div>
    </ResponsivePopup>

    <!-- ============= 群管理弹窗 ============= -->
    <!-- 群管理（公告+成员+操作：移动端=全屏子页） -->
    <ResponsivePopup v-model="showManageGroup" class="dt-dialog-limit" title="群管理" width="500px" @opened="onManageDialogOpened">
      <div class="manage-group-dialog">
        <!-- 群公告 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <DtIcon name="bell" :size="15" /> 群公告
            </span>
            <el-button v-if="!editingAnnouncement && isCurrentUserAdmin" type="primary" text size="small" @click="startEditAnnouncement">
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
              <DtIcon name="users" :size="15" /> 群成员
              <span class="member-count-tag">{{ groupMembers.length }}人</span>
            </span>
            <el-button type="primary" text size="small" @click="showManageInvite = !showManageInvite">
              <DtIcon name="plus" :size="15" /> 邀请成员
            </el-button>
          </div>

          <!-- 邀请成员展开区 -->
          <div v-if="showManageInvite" class="manage-invite-box">
            <el-input v-model="manageInviteSearch" placeholder="搜索用户（学号/工号/姓名）" size="small" clearable @input="searchMembersForManage">
              <template #prefix><DtIcon name="search" :size="15" /></template>
            </el-input>
            <div v-if="manageInviteResults.length" class="manage-invite-results">
              <div v-for="u in manageInviteResults" :key="u.id" class="manage-invite-item" @click="handleManageAddMember(u.id)">
                <el-avatar :size="32">{{ u.name[0] }}</el-avatar>
                <div class="manage-invite-info">
                  <span>{{ u.name }}</span>
                  <small>{{ u.username }}</small>
                </div>
                <DtIcon name="plus" :size="18" style="color: var(--dt-primary)" />
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

        <!-- 群二维码邀请 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <DtIcon name="link" :size="15" /> 群二维码
            </span>
            <el-button type="primary" text size="small" @click="toggleManageQr">
              {{ showManageQr ? '收起' : '查看二维码' }}
            </el-button>
          </div>
          <template v-if="showManageQr">
            <div class="manage-qr-box">
              <img v-if="qrDataUrl" :src="qrDataUrl" alt="群二维码" />
              <div v-else class="gsp-qr-loading">
                <el-icon class="is-loading" :size="20"><Loading /></el-icon>
                <span>生成中…</span>
              </div>
            </div>
            <div class="manage-qr-actions">
              <el-button size="small" @click="copyInviteLink">复制链接</el-button>
              <el-button size="small" @click="saveQrImage">保存二维码</el-button>
              <el-button size="small" type="danger" text @click="resetInvite">重置</el-button>
            </div>
          </template>
          <span v-else class="manage-empty-hint">生成二维码后，成员扫码登录校园端即可加入本群</span>
        </div>

        <el-divider />

        <!-- 个人设置 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <DtIcon name="settings" :size="15" /> 个人设置
            </span>
          </div>
          <div class="manage-switch-row">
            <span>消息免打扰</span>
            <el-switch :model-value="groupMuted" :loading="savingMute" @change="onMuteChange" />
          </div>
          <span class="manage-empty-hint">开启后该群不再计入未读数，也不接收实时消息推送</span>
        </div>

        <el-divider />

        <!-- 危险操作 -->
        <div class="manage-section manage-danger-zone">
          <div class="manage-section-title" style="margin-bottom:12px">
            <el-icon><WarningFilled /></el-icon> 危险操作
          </div>
          <div class="manage-danger-actions">
            <el-button v-if="!isCurrentUserOwner" type="danger" plain @click="handleLeaveGroup">
              <DtIcon name="logout" :size="15" /> 退出群聊
            </el-button>
            <el-button v-if="isCurrentUserOwner" type="danger" @click="handleDisbandGroup">
              <DtIcon name="trash" :size="15" /> 解散群聊
            </el-button>
          </div>
        </div>
      </div>
    </ResponsivePopup>

    <!-- ============= 移动端：群设置子页面（钉钉式：成员九宫格 + 信息/管理分组卡片） ============= -->
    <div v-if="isMobile && groupSubPage === 'settings'" class="group-sub-page">
      <input type="file" hidden ref="groupAvatarInputRef" accept="image/*" @change="onGroupAvatarSelected" />
      <div class="gsp-header">
        <el-button text circle @click="closeGroupSubPage">
          <DtIcon name="back" :size="20" />
        </el-button>
        <span class="gsp-title">群设置</span>
        <div style="width:32px"></div>
      </div>
      <div class="gsp-body">
        <!-- 群成员：钉钉式九宫格（最多展示 8 位 + 添加入口） -->
        <div class="gsp-card">
          <div class="gsp-card-head">
            <span class="gsp-card-title">群成员</span>
            <button type="button" class="gsp-card-more" @click="openMemberList">
              全部 {{ currentGroup?.member_count || groupMembers.length }} 人
              <DtIcon name="arrow" :size="12" />
            </button>
          </div>
          <div class="gsp-member-grid">
            <button
              v-for="m in groupMembers.slice(0, 8)"
              :key="m.user_id"
              type="button"
              class="gsp-member"
              @click="openMemberList"
            >
              <el-avatar :size="44" :src="m.user_avatar || undefined">{{ m.user_name?.[0] }}</el-avatar>
              <span class="gsp-member-name">{{ m.user_name }}</span>
            </button>
            <button type="button" class="gsp-member gsp-member-add" @click="showAddMember = true">
              <span class="gsp-member-add-icon"><DtIcon name="plus" :size="20" /></span>
              <span class="gsp-member-name">添加</span>
            </button>
          </div>
        </div>

        <!-- 群信息 -->
        <div class="gsp-card">
          <div
            class="gsp-item"
            :class="{ 'is-readonly': !isCurrentUserAdmin }"
            @click="triggerGroupAvatar"
          >
            <span class="gsp-item-label">群头像</span>
            <el-avatar v-if="currentGroup?.avatar" :size="28" :src="currentGroup.avatar" />
            <span v-else class="gsp-item-thumb">{{ (currentGroup?.name || activeName || '群')[0] }}</span>
            <DtIcon v-if="isCurrentUserAdmin" name="arrow" :size="15" class="gsp-arrow" />
          </div>
          <div
            class="gsp-item"
            :class="{ 'is-readonly': !isCurrentUserAdmin }"
            @click="openRenameGroup"
          >
            <span class="gsp-item-label">群名称</span>
            <span class="gsp-item-value">{{ currentGroup?.name || activeName }}</span>
            <DtIcon v-if="isCurrentUserAdmin" name="arrow" :size="15" class="gsp-arrow" />
          </div>
          <div class="gsp-item" @click="groupSubPage = 'announcement'">
            <span class="gsp-item-label">群公告</span>
            <span class="gsp-item-value">{{ currentGroup?.announcement ? '查看' : '未设置' }}</span>
            <DtIcon name="arrow" :size="15" class="gsp-arrow" />
          </div>
          <div class="gsp-item" @click="openGroupFiles">
            <span class="gsp-item-label">群文件</span>
            <span class="gsp-item-value">{{ groupFiles.length }} 个</span>
            <DtIcon name="arrow" :size="15" class="gsp-arrow" />
          </div>
          <div
            class="gsp-item"
            :class="{ 'is-readonly': !isCurrentUserAdmin }"
            @click="openGroupQr"
          >
            <span class="gsp-item-label">群二维码</span>
            <span class="gsp-item-value">{{ isCurrentUserAdmin ? '邀请成员扫码入群' : '仅群主/管理员可查看' }}</span>
            <DtIcon v-if="isCurrentUserAdmin" name="arrow" :size="15" class="gsp-arrow" />
          </div>
        </div>

        <!-- 群管理 -->
        <div class="gsp-card">
          <div class="gsp-item" @click="showAddMember = true">
            <span class="gsp-item-label">添加成员</span>
            <DtIcon name="arrow" :size="15" class="gsp-arrow" />
          </div>
          <div class="gsp-item" @click="openMemberList">
            <span class="gsp-item-label">成员管理</span>
            <span class="gsp-item-value">{{ isCurrentUserAdmin ? '可移除成员' : '查看成员' }}</span>
            <DtIcon name="arrow" :size="15" class="gsp-arrow" />
          </div>
          <div class="gsp-item gsp-item-switch">
            <span class="gsp-item-label">消息免打扰</span>
            <el-switch
              :model-value="groupMuted"
              :loading="savingMute"
              @change="onMuteChange"
            />
          </div>
        </div>

        <!-- 退出 / 解散 -->
        <button class="gsp-danger-btn" @click="isCurrentUserOwner ? handleDisbandGroup() : handleLeaveGroup()">
          {{ isCurrentUserOwner ? '解散群聊' : '退出群聊' }}
        </button>
      </div>
    </div>

    <!-- ============= 移动端：群二维码子页面（钉钉式邀请卡） ============= -->
    <div v-if="isMobile && groupSubPage === 'qr'" class="group-sub-page">
      <div class="gsp-header">
        <el-button text circle @click="groupSubPage = 'settings'">
          <DtIcon name="back" :size="20" />
        </el-button>
        <span class="gsp-title">群二维码</span>
        <div style="width:32px"></div>
      </div>
      <div class="gsp-body">
        <div class="gsp-qr-card">
          <div class="gsp-qr-head">
            <el-avatar v-if="currentGroup?.avatar" :size="42" :src="currentGroup.avatar" />
            <span v-else class="gsp-qr-avatar">{{ (currentGroup?.name || activeName || '群')[0] }}</span>
            <div class="gsp-qr-meta">
              <div class="gsp-qr-name">{{ currentGroup?.name || activeName }}</div>
              <div class="gsp-qr-sub">{{ currentGroup?.member_count || 0 }} 名成员</div>
            </div>
          </div>

          <div class="gsp-qr-box">
            <img v-if="qrDataUrl" :src="qrDataUrl" alt="群二维码" />
            <div v-else class="gsp-qr-loading">
              <el-icon class="is-loading" :size="20"><Loading /></el-icon>
              <span>生成中…</span>
            </div>
          </div>
          <p class="gsp-qr-tip">成员用手机扫码，登录校园端后即可加入本群</p>

          <div class="gsp-qr-actions">
            <button class="gsp-qr-btn" type="button" @click="copyInviteLink">
              <DtIcon name="link" :size="16" /> 复制链接
            </button>
            <button class="gsp-qr-btn" type="button" @click="saveQrImage">
              <el-icon :size="16"><Download /></el-icon> 保存二维码
            </button>
          </div>
          <button class="gsp-qr-reset" type="button" @click="resetInvite">重置二维码（旧码立即失效）</button>
        </div>
      </div>
    </div>

    <!-- 群名称修改弹窗（钉钉式单行输入） -->
    <!-- 修改群名称（单输入：移动端=底部动作面板） -->
    <ActionSheet v-model="showRenameGroup" title="修改群名称" width="330px">
      <el-input v-model="groupNameInput" maxlength="50" show-word-limit placeholder="请输入群名称" @keyup.enter="saveGroupName" />
      <template #footer>
        <el-button @click="showRenameGroup = false">取消</el-button>
        <el-button type="primary" :loading="savingGroupName" @click="saveGroupName">保存</el-button>
      </template>
    </ActionSheet>

    <!-- ============= 移动端：群公告子页面 ============= -->
    <div v-if="isMobile && groupSubPage === 'announcement'" class="group-sub-page">
      <div class="gsp-header">
        <el-button text circle @click="groupSubPage = 'settings'">
          <DtIcon name="back" :size="20" />
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
              <DtIcon name="bell" :size="18" />
              <span>群公告</span>
            </div>
            <p class="gsp-ann-text">{{ currentGroup.announcement }}</p>
          </div>
          <div v-else class="gsp-empty-box">
            <DtIcon name="bell" :size="40" style="color: var(--dt-text-quiet)" />
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
          <DtIcon name="back" :size="20" />
        </el-button>
        <span class="gsp-title">群文件</span>
        <div style="width:32px"></div>
      </div>
      <div class="gsp-body">
        <input type="file" multiple hidden ref="groupFileInputRef"
          @change="onGroupFileSelect"
          accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.txt" />
        <div v-if="groupFiles.length === 0" class="gsp-empty-box">
          <DtIcon name="empty" :size="40" style="color: var(--dt-text-quiet);" />
          <span>暂无群文件</span>
          <small>点击下方按钮上传第一个文件</small>
        </div>
        <div v-else class="gsp-file-list">
          <div v-for="f in groupFiles" :key="f.id" class="gsp-file-item" @click="downloadFile(f.url, f.text)">
            <div class="gsp-file-icon">
              <DtIcon name="document" :size="22" />
            </div>
            <div class="gsp-file-info">
              <span class="gsp-file-name">{{ f.text }}</span>
              <span class="gsp-file-meta">{{ f.sender_name }} · {{ formatTime(f.created_at) }}</span>
            </div>
            <el-icon color="var(--dt-text-quiet)"><Download /></el-icon>
          </div>
        </div>
        <button class="gsp-upload-btn" @click="groupFileInputRef?.click()">
          <DtIcon name="plus" :size="18" />
          上传文件到群
        </button>
      </div>
    </div>

    <!-- ============= 群头像裁剪弹窗 ============= -->
    <!-- 裁剪群头像（移动端=底部动作面板） -->
    <ActionSheet v-model="showGroupCrop" title="裁剪群头像" width="420px" @opened="onGroupCropOpened">
      <div class="group-crop-box">
        <img ref="groupCropImgRef" style="max-width:100%;display:block" />
      </div>
      <template #footer>
        <el-button @click="cancelGroupCrop">取消</el-button>
        <el-button type="primary" :loading="uploadingGroupAvatar" @click="confirmGroupCrop">确认</el-button>
      </template>
    </ActionSheet>

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
          <el-avatar :size="52" :src="auth.user?.avatar || ''">
            {{ auth.userName?.[0] || '师' }}
          </el-avatar>
          <div class="msg-drawer-user">
            <span class="msg-drawer-name">{{ auth.userName || '教师' }}</span>
            <span class="msg-drawer-sub">{{ auth.user?.college || siteName }}</span>
          </div>
        </div>
        <nav class="msg-drawer-nav">
          <div class="msg-drawer-section">消息中心</div>
          <button
            v-for="v in viewTabs"
            :key="v.key"
            type="button"
            class="msg-drawer-item"
            :class="{ active: mobileView === v.key }"
            @click="switchView(v.key)"
          >
            <span class="msg-drawer-icon"><DtIcon :name="v.dtIcon" :size="19" /></span>
            <span class="msg-drawer-label">{{ v.label }}</span>
            <span v-if="v.count > 0" class="tui-count">{{ v.count > 99 ? '99+' : v.count }}</span>
          </button>
        </nav>
      </aside>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
// v6.1 弹窗减负：列表/表单走全屏子页，裁剪走底部动作面板
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
// v6.1 弹窗减负：单输入面板与删除确认走底部动作面板
import ActionSheet from '@/components/common/ActionSheet.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import { useRoute, useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import { useAuthStore } from '@/stores/auth'
import { getConversations, getMessages, sendMessage, markRead, getSessionPins, setSessionPin, deleteSession, getSharedFiles, type SharedFile } from '@/api/messages'
import {
  getGroups, getGroup, getGroupMembers, createGroup as apiCreateGroup,
  addGroupMembers, sendGroupMessage, getGroupMessages, searchUsers,
  updateGroupAnnouncement, updateGroupAvatar, renameGroup, leaveGroup, disbandGroup, removeGroupMember,
  setGroupMuted, getGroupInvite, resetGroupInvite, markGroupRead,
  type GroupOut, type GroupMemberOut, type UserSearchResult
} from '@/api/groups'
import { uploadFile } from '@/api/upload'
import { getStudents, type StudentSummary } from '@/api/teacher'
import {
  getNotifications, markNotificationsRead, markAllNotificationsRead,
  type Notification as NotificationItem,
} from '@/api/notification'
import { getColleges, getMajors, getClassGroups, getOrgScope, type OrgScope } from '@/api/organization'
import type { College, Major, ClassGroup } from '@/types'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { useButlerPreview } from '@/composables/useButlerPreview'
import { usePullRefresh } from '@/composables/usePullRefresh'
// 下拉刷新指示器：教师端首页 / 学生端首页 / 消息页共用同一套吉祥物动画
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
// 小绵管家：教师端与学生端共用的常驻会话（自动推送资讯 + 总结对话）
import ButlerChat from '@/components/butler/ButlerChat.vue'
// 钉钉风格图标（对齐钉钉设计的组件图案）
import DtIcon from '@/components/common/DtIcon.vue'
import { openUserHomepage } from '@/composables/useUserHomepage'
import { getToken } from '@/utils/token'
import { ElMessage } from 'element-plus'
import Cropper from 'cropperjs'
import QRCode from 'qrcode'
import {
  User, ChatDotRound, ChatLineRound,
  Bell, Loading, InfoFilled, Stamp, Collection, Notebook,
  OfficeBuilding,
  UploadFilled, Document, Picture, Setting, WarningFilled, Download,
  Microphone, EditPen, VideoPlay, VideoPause, View
} from '@element-plus/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const userId = auth.user?.id ?? 0
const { isMobile } = useResponsive()
const { siteName, siteMascot, agentName } = useSiteConfig()
// 小绵管家入口的动态摘要（取最新一条资讯标题）
const { butlerPreview, refreshButlerPreview } = useButlerPreview()

// ===== 消息中心视图（消息 / 通讯录 / 文件 / 通知）=====
// 消息为默认主视图；其余在移动端收进侧边抽屉，桌面端置于左栏分段切换
type MsgView = 'messages' | 'contacts' | 'files' | 'notifications'
const mobileView = ref<MsgView>('messages')
const drawerOpen = ref(false)
const mobileViewTitle = computed(
  () => ({ messages: '消息', contacts: '通讯录', files: '文件', notifications: '通知' } as Record<MsgView, string>)[mobileView.value]
)

const viewTabs = computed(() => [
  // dtIcon：钉钉风格导航图标（见 components/common/DtIcon.vue）
  { key: 'messages' as MsgView, label: '消息', icon: ChatLineRound, dtIcon: 'message', count: totalUnread.value },
  { key: 'contacts' as MsgView, label: '通讯录', icon: User, dtIcon: 'contacts', count: 0 },
  { key: 'files' as MsgView, label: '文件', icon: Document, dtIcon: 'file', count: 0 },
  { key: 'notifications' as MsgView, label: '通知', icon: Bell, dtIcon: 'bell', count: unreadNotifCount.value },
])

function switchView(v: MsgView) {
  mobileView.value = v
  drawerOpen.value = false
  if (v === 'contacts') ensureContacts()
  if (v === 'files') loadSharedFiles()
  if (v === 'notifications') loadNotifications()
}

const conversations = ref<any[]>([])
const groups = ref<GroupOut[]>([])

const activeId = ref<number | null>(null)

// 移动端聊天详情是页内二级页面：打开时让出底部悬浮导航，把整屏留给会话
useMobileSubPage(computed(() => isMobile.value && activeId.value !== null))
const activeName = ref('')
const activeType = ref<'single' | 'group' | 'butler'>('single')
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

// ===== 聊天头副标题 / 右侧信息面板（钉钉式）=====
const singlePeerId = computed(() => activeId.value ?? 0)
const singlePeerAvatar = computed(() =>
  activeType.value === 'single' && activeId.value
    ? conversations.value.find((c: any) => c.user_id === activeId.value)?.user_avatar || ''
    : ''
)
const chatSubtitle = computed(() => {
  if (activeType.value === 'group') {
    const n = currentGroup.value?.member_count ?? groupMembers.value.length
    return n ? `${n} 名成员` : ''
  }
  if (activeType.value === 'single' && activeId.value) {
    const base = isOnline(activeId.value) ? '在线' : '离线'
    return isMyStudent.value ? `${base} · 我的学生` : base
  }
  return ''
})

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

/** 把当前会话加入任务日程：任务页支持 student_id / student_name / title 预填 */
function addToTask() {
  if (!activeId.value) return
  if (activeType.value === 'group') {
    router.push({
      path: '/teacher/tasks',
      query: { title: `跟进群聊：${currentGroup.value?.name || activeName.value}` },
    })
    return
  }
  const query: Record<string, string> = {
    student_name: activeName.value,
    title: `跟进联系：${activeName.value}`,
  }
  if (myStudentIds.value.has(activeId.value)) query.student_id = String(activeId.value)
  router.push({ path: '/teacher/tasks', query })
}

// 侧边栏 — 筛选已有会话
const search = ref('')

/** 桌面端钉钉式头部搜索：按当前视图路由到对应关键字（消息 / 通讯录 / 文件），通知视图不展示搜索 */
const headerKeyword = computed({
  get: () => {
    if (mobileView.value === 'contacts') return contactKeyword.value
    if (mobileView.value === 'files') return fileKeyword.value
    return search.value
  },
  set: (v: string) => {
    if (mobileView.value === 'contacts') contactKeyword.value = v
    else if (mobileView.value === 'files') fileKeyword.value = v
    else search.value = v
  },
})
const headerSearchPlaceholder = computed(() => {
  if (mobileView.value === 'contacts') return '搜索姓名 / 学号 / 工号'
  if (mobileView.value === 'files') return '搜索文件名'
  return '搜索已有会话'
})
function onHeaderSearch() {
  if (mobileView.value === 'messages') filterConversations()
  else if (mobileView.value === 'contacts') onContactSearch()
  else if (mobileView.value === 'files') onFileSearch()
}

// 置顶会话（服务端持久化：跨端 / 跨设备同步，替代原 localStorage 方案）
const pinnedKeys = ref<Set<string>>(new Set())
async function loadPins() {
  try {
    const r = await getSessionPins()
    pinnedKeys.value = new Set(r.keys || [])
  } catch { /* 拉取失败时保持无置顶，不影响会话列表展示 */ }
}
function togglePin(key: string) {
  const next = !pinnedKeys.value.has(key)
  const s = new Set(pinnedKeys.value)
  if (next) s.add(key)
  else s.delete(key)
  pinnedKeys.value = s
  setSessionPin(key, next).catch(() => ElMessage.error('置顶同步失败'))
}
function isPinned(key: string) { return pinnedKeys.value.has(key) }

/** 删除会话：只从本人列表移除（记录保留、对方不受影响），对方再来消息会自动恢复 */
async function handleDeleteSession(item: { _key: string; _type: string; name: string }) {
  const tip = item._type === 'group'
    ? `「${item.name}」将从会话列表移除，群聊与聊天记录都还在，群里有新消息会重新出现。`
    : `「${item.name}」将从会话列表移除，聊天记录保留，对方不受影响，对方再来消息会重新出现。`
  if (!(await actionConfirm(tip, '删除会话', { danger: true, confirmButtonText: '删除' }))) return
  try {
    await deleteSession(item._key)
    swipedKey.value = null
    // 服务端已按删除水位过滤，重拉列表即可同步；顺手清掉本地置顶残留
    if (pinnedKeys.value.has(item._key)) togglePin(item._key)
    await Promise.all([loadConversations(), loadGroups()])
    ElMessage.success('已删除会话')
  } catch { ElMessage.error('删除失败') }
}

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
      try {
        const p = JSON.parse(m)
        if (p.type === 'voice') return '[语音]'
        return p.type === 'image' ? '[图片] ' + (p.text||'') : '[文件] ' + (p.text||'')
      } catch {}
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

// 发起会话：组织内用户无需「好友关系」，选中即打开单聊（与钉钉一致，无好友概念）
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
  ElMessage.success(`已打开与 ${user.name} 的会话`)
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
function isMemberSelected(id: number) {
  return selectedMembers.value.some(m => m.id === id)
}
/** 快速勾选：直接从通讯录（最近联系人）多选建群成员，免去逐个搜索 */
function toggleRecentContact(c: RecentContact) {
  if (isMemberSelected(c.id)) removeSelectedMember(c.id)
  else addSelectedMember({ id: c.id, name: c.name, username: '', avatar: c.avatar, role: '' })
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

// 群名称修改（钉钉群设置「群名称」）
const showRenameGroup = ref(false)
const groupNameInput = ref('')
const savingGroupName = ref(false)

// 移动端群设置子页面（钉钉式）：settings / announcement / files / qr
const groupSubPage = ref<'settings' | 'announcement' | 'files' | 'qr' | null>(null)

// 群二维码邀请
const qrDataUrl = ref('')
const inviteCode = ref('')
const inviteLink = computed(() =>
  inviteCode.value ? `${window.location.origin}/join/group/${inviteCode.value}` : ''
)

// 消息免打扰（仅影响自己）
const groupMuted = ref(false)
const savingMute = ref(false)
// 桌面端群管理弹窗内是否展开群二维码
const showManageQr = ref(false)
const groupFileInputRef = ref<HTMLInputElement>()
const groupAvatarInputRef = ref<HTMLInputElement>()
const showGroupCrop = ref(false)
// v6.1：移动端子页无 opened 事件，用 watch 兜底初始化（桌面端 @opened 与之幂等）
watch([showAddFriend, showManageGroup, showGroupCrop], ([a, m, c]) => {
  if (a) nextTick(focusAddFriendInput)
  if (m) nextTick(onManageDialogOpened)
  if (c) nextTick(onGroupCropOpened)
})
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
    showManageQr.value = false
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
    loadGroups()
  } catch { ElMessage.error('添加失败') }
}

/** 是否可移除该成员：群主/管理员可移除他人，群主自身不可被移除 */
function canRemoveMember(m: GroupMemberOut) {
  return isCurrentUserAdmin.value && m.role !== 'owner' && m.user_id !== userId
}

async function handleRemoveMember(uid: number, name: string) {
  if (!activeId.value) return
  const target = groupMembers.value.find((m) => m.user_id === uid)
  if (target && target.role === 'owner') { ElMessage.warning('群主不可被移除'); return }
  try {
    if (!(await actionConfirm(`确定将「${name}」移出群聊吗？`, '移除成员', { danger: true, confirmButtonText: '移出' }))) return
  } catch { return /* 用户取消 */ }
  try {
    await removeGroupMember(activeId.value, uid)
    ElMessage.success(`已移除 ${name}`)
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
    loadGroups()
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
  if (showAttachPanel.value) showEmoji.value = false
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
    loadGroups()
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
    groupMuted.value = !!group?.is_muted
    editingAnnouncement.value = false
  } catch { /* 已有数据则保留 */ }
}

// ===== 群二维码邀请（钉钉式，移动端子页 + 桌面弹窗共用） =====
async function loadGroupQr() {
  if (!activeId.value) return
  try {
    const inv = await getGroupInvite(activeId.value)
    inviteCode.value = inv.code
    await renderQr()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '二维码获取失败')
  }
}

async function openGroupQr() {
  if (!isCurrentUserAdmin.value || !activeId.value) return
  groupSubPage.value = 'qr'
  qrDataUrl.value = ''
  await loadGroupQr()
}

/** 桌面端「群管理」弹窗内展开/收起二维码 */
async function toggleManageQr() {
  if (showManageQr.value) { showManageQr.value = false; return }
  if (!isCurrentUserAdmin.value) { ElMessage.warning('仅群主或管理员可查看群二维码'); return }
  showManageQr.value = true
  if (!qrDataUrl.value) await loadGroupQr()
}

async function renderQr() {
  if (!inviteLink.value) return
  try {
    qrDataUrl.value = await QRCode.toDataURL(inviteLink.value, {
      width: 480,
      margin: 1,
      errorCorrectionLevel: 'M',
    })
  } catch {
    ElMessage.error('二维码生成失败')
  }
}

/** 重置邀请码：此前分享出去的二维码立即失效 */
async function resetInvite() {
  if (!activeId.value) return
  try {
    const inv = await resetGroupInvite(activeId.value)
    inviteCode.value = inv.code
    await renderQr()
    ElMessage.success('二维码已重置，旧码已失效')
  } catch {
    ElMessage.error('重置失败')
  }
}

async function copyInviteLink() {
  if (!inviteLink.value) return
  try {
    await navigator.clipboard.writeText(inviteLink.value)
    ElMessage.success('邀请链接已复制')
  } catch {
    ElMessage.info(inviteLink.value)
  }
}

function saveQrImage() {
  if (!qrDataUrl.value) return
  const a = document.createElement('a')
  a.href = qrDataUrl.value
  a.download = `群二维码-${currentGroup.value?.name || activeName.value}.png`
  a.click()
}

/** 消息免打扰开关：仅影响自己（不计未读、不接收实时推送） */
async function onMuteChange(val: string | number | boolean) {
  if (!activeId.value) return
  const muted = !!val
  savingMute.value = true
  try {
    const r = await setGroupMuted(activeId.value, muted)
    groupMuted.value = r.muted
    ElMessage.success(r.muted ? '已开启消息免打扰' : '已关闭消息免打扰')
    loadGroups()
  } catch {
    groupMuted.value = !muted
    ElMessage.error('设置失败')
  } finally {
    savingMute.value = false
  }
}

function closeGroupSubPage() {
  groupSubPage.value = null
}

/** 打开群名称修改弹窗（仅群主/管理员可改） */
function openRenameGroup() {
  if (!isCurrentUserAdmin.value) return
  groupNameInput.value = currentGroup.value?.name || activeName.value
  showRenameGroup.value = true
}

async function saveGroupName() {
  const name = groupNameInput.value.trim()
  if (!activeId.value) return
  if (!name) { ElMessage.warning('请输入群名称'); return }
  savingGroupName.value = true
  try {
    await renameGroup(activeId.value, name)
    ElMessage.success('群名称已更新')
    showRenameGroup.value = false
    currentGroup.value = await getGroup(activeId.value)
    activeName.value = currentGroup.value?.name || name
    loadGroups()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '修改失败')
  } finally {
    savingGroupName.value = false
  }
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
    // 同步刷新会话列表，避免左侧群头像仍是旧图
    loadGroups()
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

// 全局未读提示（与布局红点同一数据源）：清除后同步刷新页内各列表红点
const {
  clearAll: clearUnreadAll,
  isOnline,
  syncPresence,
  presenceTick,
} = useUnreadSummary()
const hasUnread = computed(() => totalUnread.value > 0 || unreadNotifCount.value > 0)

// 在线状态变更（他人上/下线）后重拉群列表：群在线人数由服务端聚合，需重新取数
watch(presenceTick, () => { loadGroups() })

/** 清除未读提示：单聊 + 群聊 + 站内通知一次清掉 */
async function handleClearUnread() {
  await clearUnreadAll()
  ElMessage.success('已清除未读提示')
  loadConversations()
  loadGroups()
  loadNotifications()
}

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

// 时间解析：后端返回的是「无时区的 UTC 时间串」（如 2025-10-16T02:30:00），
// 直接 new Date() 会被当成本地时间，导致日期分组/相对时间整体错位。
// 这里统一补上 Z 按 UTC 解析，再以本地时区取年月日，日期分隔线才分得对。
function parseTime(t: string): Date {
  return new Date(t + (t.includes('Z') || t.includes('+') ? '' : 'Z'))
}

function getDateStr(t: string) { const d = parseTime(t); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` }
function getDateLabel(t: string) {
  const date = parseTime(t); const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  // 两个本地零点相减：用 round 而非 floor，规避夏令时造成的 23/25 小时误差
  const diff = Math.round((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatTime(t: string | null) {
  if (!t) return ''
  try {
    const date = parseTime(t)
    const now = new Date(); const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000); const hours = Math.floor(diff / 3600000)
    const ts = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return ts
  } catch { return t }
}

/** 会话行时间（钉钉式）：当天显示 HH:mm，更早显示 MM-DD */
function formatConvTime(t: string | null) {
  if (!t) return ''
  try {
    const d = parseTime(t)
    const now = new Date()
    const sameDay = d.getFullYear() === now.getFullYear()
      && d.getMonth() === now.getMonth()
      && d.getDate() === now.getDate()
    if (sameDay) {
      return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    }
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    return `${mm}-${dd}`
  } catch { return '' }
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
      } else if (data.type === 'group_member_joined') {
        // 有人扫码入群：刷新群列表；若正在看该群则同步成员与群信息
        loadGroups()
        if (data.group_id === activeId.value && activeType.value === 'group' && activeId.value) {
          getGroupMembers(activeId.value).then((list) => { groupMembers.value = list }).catch(() => {})
          getGroup(activeId.value).then((g) => { currentGroup.value = g }).catch(() => {})
        }
      }
    } catch {}
  }
  ws.onclose = () => { ws = null }
}
function disconnectWs() { if (ws) { ws.close(); ws = null } }

async function loadConversations() {
  try {
    conversations.value = await getConversations()
    // 用会话列表返回的在线初值回填在线映射（WebSocket 事件在两次拉取之间保持实时）
    syncPresence(conversations.value.map((c: any) => ({ user_id: c.user_id, online: !!c.online })))
  } catch {}
}
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

/** 通讯录「最近联系人」：与我有会话往来的人自动进入通讯录，便于发起会话、快速建群 */
interface RecentContact { id: number; name: string; avatar: string | null; online: boolean }
const recentContacts = computed<RecentContact[]>(() =>
  (conversations.value || []).map((c: any) => ({
    id: c.user_id,
    name: c.user_name,
    avatar: c.user_avatar ?? null,
    online: !!c.online,
  }))
)

// 组织架构树：学院 → 专业 → 班级，均取自管理端「院系班级」配置
const orgColleges = ref<College[]>([])
const orgMajors = ref<Record<number, Major[]>>({})
const orgClasses = ref<Record<number, ClassGroup[]>>({})
const expandedColleges = ref<Set<number>>(new Set())
const expandedMajors = ref<Set<number>>(new Set())
const orgLoading = ref(false)

/** 组织架构范围：只展示「自己所在组织 + 下级架构」 */
const orgScope = ref<OrgScope | null>(null)
const orgScopeRestricted = computed(() => !!orgScope.value && orgScope.value.scope !== 'all')

async function ensureContacts() {
  if (contactsLoaded) return
  contactsLoaded = true
  contactsLoading.value = true
  orgLoading.value = true
  try {
    const [students, colleges, scope] = await Promise.all([
      getStudents().catch(() => [] as StudentSummary[]),
      getColleges().catch(() => [] as College[]),
      getOrgScope().catch(() => null),
    ])
    contactStudents.value = students
    orgScope.value = scope
    // 只保留自己所在的学院；未归属任何组织（scope=all）时才展示全部
    const collegeId = scope?.college_id ?? null
    orgColleges.value = collegeId ? colleges.filter((c) => c.id === collegeId) : colleges
    if (orgColleges.value.length) await expandOwnOrgPath()
  } finally {
    contactsLoading.value = false
    orgLoading.value = false
  }
}

/** 自动展开「学院 → 专业 → 班级」自己的归属路径，直接看到本班学生 */
async function expandOwnOrgPath() {
  const scope = orgScope.value
  if (!scope || scope.scope === 'all' || !scope.college_id) return
  try {
    expandedColleges.value = new Set([scope.college_id])
    const majors = await getMajors(scope.college_id)
    const visibleMajors = scope.major_id ? majors.filter((m) => m.id === scope.major_id) : majors
    orgMajors.value = { ...orgMajors.value, [scope.college_id]: visibleMajors }
    if (!scope.major_id) return

    expandedMajors.value = new Set([scope.major_id])
    const classes = await getClassGroups({ major_id: scope.major_id })
    const visibleClasses = scope.class_group_id ? classes.filter((cg) => cg.id === scope.class_group_id) : classes
    orgClasses.value = { ...orgClasses.value, [scope.major_id]: visibleClasses }
    if (!scope.class_group_id) return

    expandedClasses.value = new Set([scope.class_group_id])
    classStudentsLoading.value = { ...classStudentsLoading.value, [scope.class_group_id]: true }
    try {
      const list = await getStudents(undefined, scope.class_group_id)
      classStudents.value = { ...classStudents.value, [scope.class_group_id]: list }
    } catch {
      classStudents.value = { ...classStudents.value, [scope.class_group_id]: [] }
    } finally {
      classStudentsLoading.value = { ...classStudentsLoading.value, [scope.class_group_id]: false }
    }
  } catch { /* 组织架构加载失败不阻塞消息与检索 */ }
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
    // 收敛到本人所在专业时，只展示该专业
    const scope = orgScope.value
    orgMajors.value = {
      ...orgMajors.value,
      [id]: scope?.major_id && scope.college_id === id ? majors.filter((m) => m.id === scope.major_id) : majors,
    }
  }
}

async function toggleOrgMajor(id: number) {
  const next = new Set(expandedMajors.value)
  if (next.has(id)) { next.delete(id) } else { next.add(id) }
  expandedMajors.value = next
  if (next.has(id) && !orgClasses.value[id]) {
    const classes = await getClassGroups({ major_id: id }).catch(() => [] as ClassGroup[])
    // 收敛到本人所在班级时，只展示该班级
    const scope = orgScope.value
    orgClasses.value = {
      ...orgClasses.value,
      [id]: scope?.class_group_id && scope.major_id === id ? classes.filter((cg) => cg.id === scope.class_group_id) : classes,
    }
  }
}

// 班级 → 学生名单（通讯录下钻最后一跳，点学生即可发起会话）
const expandedClasses = ref<Set<number>>(new Set())
const classStudents = ref<Record<number, StudentSummary[]>>({})
const classStudentsLoading = ref<Record<number, boolean>>({})

async function toggleOrgClass(classGroupId: number) {
  const next = new Set(expandedClasses.value)
  if (next.has(classGroupId)) { next.delete(classGroupId) } else { next.add(classGroupId) }
  expandedClasses.value = next
  if (next.has(classGroupId) && !classStudents.value[classGroupId]) {
    classStudentsLoading.value = { ...classStudentsLoading.value, [classGroupId]: true }
    try {
      const list = await getStudents(undefined, classGroupId)
      classStudents.value = { ...classStudents.value, [classGroupId]: list }
    } catch {
      classStudents.value = { ...classStudents.value, [classGroupId]: [] }
    } finally {
      classStudentsLoading.value = { ...classStudentsLoading.value, [classGroupId]: false }
    }
  }
}

/** 通讯录角色标签：管理员此前会被误标为「学生」 */
function roleLabel(role: string) {
  if (role === 'teacher') return '教师'
  if (role === 'admin') return '管理员'
  return '学生'
}
function roleTagClass(role: string) {
  return role === 'student' ? 'tui-tag-brand' : 'tui-tag-warn'
}

/* ==================== 文件（跨会话汇总，QQ「文件」页） ==================== */
// 汇总历史各聊天里发送/接收过的文件、图片、语音：单聊 + 群聊一次取齐（服务端聚合）
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

function fileTypeIcon(t: SharedFile['file_type']) {
  if (t === 'image') return Picture
  if (t === 'voice') return Microphone
  return Document
}

/** 打开文件：图片走大图预览，其余直接下载 */
function openSharedFile(f: SharedFile) {
  if (f.file_type === 'image') previewImage(f.url)
  else downloadFile(f.url, f.name || '文件')
}

/** 点击来源会话 → 跳到对应聊天 */
function openFileSession(f: SharedFile) {
  openChat(Number(f.session_key.slice(2)), f.session_name, f.is_group ? 'group' : 'single')
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
  if (n.link) {
    router.push(n.link)
  } else {
    // 部分通知（历史数据 / 无跳转目标）没有 link，此前点击完全无反应，
    // 这里给出明确反馈，避免用户以为页面坏了。
    ElMessage.info(n.content || '该通知暂无关联页面')
  }
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
      return { icon: Bell, color: '#2563eb', tint: 'var(--dt-primary-soft)' }
    case 'feedback':
      return { icon: ChatLineRound, color: '#079455', tint: '#ecfdf3' }
    case 'message':
      return { icon: ChatDotRound, color: '#0891b2', tint: '#ecfeff' }
    case 'system':
      return { icon: Setting, color: '#2563eb', tint: 'var(--dt-primary-soft)' }
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
      // 群聊会话头副标题 / 右侧信息面板需要成员与免打扰状态：随打开会话一并取回
      const [g, members] = await Promise.all([
        getGroup(id),
        getGroupMembers(id).catch(() => [] as GroupMemberOut[]),
      ])
      currentGroup.value = g
      groupMembers.value = members
      groupMuted.value = !!g.is_muted
      // 打开群聊即标记已读：否则群未读角标不会清零，会话列表一直“有红点”
      await markGroupRead(id)
      loadGroups()
    }
    scrollToBottom()
  } catch {}
}
function goBack() {
  activeId.value = null; activeName.value = ''; messages.value = []; currentGroup.value = null
  activeType.value = 'single'
  groupSubPage.value = null
}

/** 打开「小绵管家」常驻会话：自动推送资讯 / 总结对话，不占用单聊与群聊状态 */
function openButler() {
  activeType.value = 'butler'
  activeId.value = -1
  activeName.value = `${agentName.value || '小绵'}管家`
  messages.value = []
  currentGroup.value = null
  groupSubPage.value = null
  drawerOpen.value = false
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

// 文件/图片/语音消息
function getMsgMeta(msg: any) {
  const c = msg.content || ''
  if (c.startsWith('{') && c.includes('"type"')) {
    try {
      const parsed = JSON.parse(c)
      if (parsed.type === 'file' || parsed.type === 'image' || parsed.type === 'voice') {
        return {
          isFile: true, fileType: parsed.type, text: parsed.text || '',
          url: parsed.url || '', duration: Number(parsed.duration) || 0,
        }
      }
    } catch {}
  }
  return { isFile: false, fileType: '', text: '', url: '', duration: 0 }
}

function makeFileContent(fileType: string, filename: string, url: string) {
  return JSON.stringify({ type: fileType, text: filename, url })
}

/* ==================== QQ 风格输入：表情面板 ==================== */
const showEmoji = ref(false)
// 常用表情（QQ 输入框表情面板）
const EMOJIS = [
  '😀', '😄', '😁', '😆', '😅', '😂', '😊', '😇',
  '🙂', '😉', '😍', '🥰', '😘', '😋', '😜', '🤪',
  '🤔', '🤨', '😐', '😑', '😶', '🙄', '😏', '😴',
  '😔', '😢', '😭', '😤', '😠', '😡', '🥺', '😱',
  '😳', '🤗', '🤭', '🤫', '😷', '🤒', '🥳', '😎',
  '👍', '👎', '👌', '🙏', '👏', '🙌', '💪', '🤝',
  '❤️', '💔', '💯', '🔥', '✨', '🎉', '🌹', '☕',
  '🍺', '🎁', '⭐', '🌈', '☀️', '🌙', '🐶', '🐱'
]

function toggleEmoji() {
  showEmoji.value = !showEmoji.value
  if (showEmoji.value) { voiceMode.value = false; showAttachPanel.value = false }
}

function toggleVoiceMode() {
  voiceMode.value = !voiceMode.value
  if (voiceMode.value) { showEmoji.value = false; showAttachPanel.value = false }
}

// 输入框是否有内容：决定右侧显示「发送」还是「加号」
const hasText = computed(() => !!newMsg.value.trim())

// 当前展开的底部面板：'emoji' | 'plus' | null
// 两者互斥且共用同一个容器，切换时高度不变，避免"两个面板同时过渡"造成的高度跳动
const activePanel = computed<'emoji' | 'plus' | null>(() => {
  if (showAttachPanel.value) return 'plus'
  if (showEmoji.value && !voiceMode.value) return 'emoji'
  return null
})

// 输入框有内容时右侧「加号」切换为「发送」：同步收起「更多」面板，避免面板悬挂在已消失的按钮上
watch(newMsg, (val) => { if (val.trim()) showAttachPanel.value = false })

/** 表情插入到输入框光标处 */
function insertEmoji(emoji: string) {
  const el = document.querySelector<HTMLTextAreaElement>('.composer-input .el-textarea__inner')
  if (!el) { newMsg.value += emoji; return }
  const start = el.selectionStart ?? newMsg.value.length
  const end = el.selectionEnd ?? start
  newMsg.value = newMsg.value.slice(0, start) + emoji + newMsg.value.slice(end)
  nextTick(() => { el.focus(); el.selectionStart = el.selectionEnd = start + emoji.length })
}

/* ==================== QQ 风格输入：语音消息（按住说话） ==================== */
const voiceMode = ref(false)
const isRecording = ref(false)
const recordCancelled = ref(false)
const recordSeconds = ref(0)
let mediaRecorder: MediaRecorder | null = null
let mediaStream: MediaStream | null = null
let audioChunks: Blob[] = []
let recordTimer: number | null = null
let talkPressed = false
let talkStartY = 0

async function onTalkStart(e: PointerEvent) {
  if (isRecording.value) return
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    ElMessage.warning('当前环境不支持语音录制')
    return
  }
  talkPressed = true
  talkStartY = e.clientY
  recordCancelled.value = false
  recordSeconds.value = 0
  try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId) } catch { /* 指针捕获失败不影响录音 */ }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    // 授权期间用户已松手：直接释放麦克风，避免空录音
    if (!talkPressed) { stream.getTracks().forEach(t => t.stop()); return }
    mediaStream = stream
    audioChunks = []
    const mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
    mediaRecorder = new MediaRecorder(stream, { mimeType: mime })
    mediaRecorder.ondataavailable = (ev: BlobEvent) => { if (ev.data.size > 0) audioChunks.push(ev.data) }
    mediaRecorder.start()
    isRecording.value = true
    const startedAt = Date.now()
    recordTimer = window.setInterval(() => {
      recordSeconds.value = Math.floor((Date.now() - startedAt) / 1000)
    }, 200)
  } catch {
    talkPressed = false
    ElMessage.error('无法访问麦克风，请检查权限')
  }
}

function onTalkMove(e: PointerEvent) {
  if (!isRecording.value) return
  // 手指上滑超过 60px 视为取消发送（QQ / 微信一致的交互）
  recordCancelled.value = (talkStartY - e.clientY) > 60
}

function onTalkCancel() {
  if (isRecording.value) { recordCancelled.value = true; void onTalkEnd() }
  else talkPressed = false
}

async function onTalkEnd() {
  talkPressed = false
  if (!isRecording.value || !mediaRecorder) return
  const cancelled = recordCancelled.value
  const short = recordSeconds.value < 1
  const duration = Math.max(1, Math.round(recordSeconds.value))
  const recorder = mediaRecorder
  const stream = mediaStream
  isRecording.value = false
  if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
  mediaRecorder = null
  mediaStream = null
  await new Promise<void>((resolve) => {
    recorder.addEventListener('stop', () => resolve(), { once: true })
    try { recorder.stop() } catch { resolve() }
  })
  stream?.getTracks().forEach(t => t.stop())
  if (cancelled) { ElMessage.info('已取消发送'); return }
  if (short) { ElMessage.warning('说话时间太短'); return }
  const blob = new Blob(audioChunks, { type: recorder.mimeType || 'audio/webm' })
  audioChunks = []
  if (!blob.size) { ElMessage.error('录音失败，请重试'); return }
  await sendVoiceMessage(blob, duration)
}

async function sendVoiceMessage(blob: Blob, duration: number) {
  try {
    const ext = blob.type.includes('mp4') ? 'm4a' : 'webm'
    const file = new File([blob], `voice-${Date.now()}.${ext}`, { type: blob.type })
    const result = await uploadFile(file)
    await sendTextMsg(JSON.stringify({ type: 'voice', text: '', url: result.url, duration }))
  } catch {
    ElMessage.error('语音发送失败')
  }
}

// 语音消息播放：同一时刻只播放一条
const playingVoiceUrl = ref('')
let voiceAudioEl: HTMLAudioElement | null = null
function toggleVoicePlay(url: string) {
  if (!url) return
  if (playingVoiceUrl.value === url && voiceAudioEl) {
    voiceAudioEl.pause(); voiceAudioEl = null; playingVoiceUrl.value = ''
    return
  }
  if (voiceAudioEl) { voiceAudioEl.pause(); voiceAudioEl = null }
  const audio = new Audio(url)
  voiceAudioEl = audio
  audio.onended = () => { if (playingVoiceUrl.value === url) playingVoiceUrl.value = '' }
  audio.onerror = () => { playingVoiceUrl.value = ''; ElMessage.error('语音播放失败') }
  audio.play().then(() => { playingVoiceUrl.value = url }).catch(() => { ElMessage.error('语音播放失败') })
}

/** 语音气泡宽度随时长递增（QQ 语音条样式） */
function voiceBubbleWidth(duration: number) {
  const d = Number(duration) || 1
  return `${Math.min(180, 84 + d * 8)}px`
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
  else if (cmd === 'clearUnread') { if (hasUnread.value) void handleClearUnread() }
}

/* ==================== 移动端下拉刷新 ==================== */
// 会话 / 通讯录 / 通知三视图共用侧栏滚动容器：下拉时按当前视图重新拉取，
// 兜底 WebSocket 断线或漏推导致的"消息不更新"
async function refreshSidebar() {
  if (mobileView.value === 'messages') {
    await Promise.all([loadConversations(), loadGroups(), refreshButlerPreview()])
  } else if (mobileView.value === 'contacts') {
    contactsLoaded = false
    await Promise.all([ensureContacts(), loadMyStudents()])
  } else if (mobileView.value === 'files') {
    await loadSharedFiles()
  } else {
    await loadNotifications()
  }
}

// 聊天区下拉：重新拉取当前会话消息；原本停在底部时顺带标记已读并回到底部，
// 否则保持当前阅读位置，不打断翻看历史消息
async function refreshChat() {
  const id = activeId.value
  const el = msgListRef.value
  if (!id || id < 0 || !el) return
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 48
  if (activeType.value === 'single') {
    messages.value = await getMessages(id)
    if (atBottom) await markRead(id)
    await loadConversations()
  } else if (activeType.value === 'group') {
    messages.value = await getGroupMessages(id)
    if (atBottom) await markGroupRead(id)
    await loadGroups()
  }
  if (atBottom) scrollToBottom()
}

// 手势仅在移动端生效：桌面端不做下拉刷新交互
const sidebarPull = usePullRefresh(refreshSidebar, { enabled: () => isMobile.value })
const chatPull = usePullRefresh(refreshChat, { enabled: () => isMobile.value })

onMounted(async () => {
  document.addEventListener('click', onGlobalClick)
  loadPins()
  connectWs()
  void refreshButlerPreview()
  await Promise.all([loadConversations(), loadGroups(), loadMyStudents()])
  if (route.query.groupId) {
    openChat(Number(route.query.groupId), (route.query.groupName as string) || '', 'group')
    router.replace({ query: {} })
  } else if (route.query.studentId) {
    openChat(Number(route.query.studentId), (route.query.studentName as string) || '', 'single')
    router.replace({ query: {} })
  } else if (route.query.chat) {
    openFromHomepageQuery()
  }
})

/**
 * 从他人个人主页「发消息 / 加为好友」跳转而来：打开与该用户的会话，带 draft 则预填问候草稿。
 * 单独抽成函数是因为「已在消息页时再次跳转」不会重挂载组件（同路由只换 query），
 * 那条路径由下方 watch 触发。
 */
function openFromHomepageQuery() {
  const chatId = Number(route.query.chat)
  if (chatId) {
    openChat(chatId, (route.query.chatName as string) || '', 'single')
    if (route.query.draft) newMsg.value = String(route.query.draft)
  }
  router.replace({ query: {} })
}

watch(
  () => route.query.chat,
  (v) => { if (v) openFromHomepageQuery() },
)
onUnmounted(() => {
  document.removeEventListener('click', onGlobalClick)
  disconnectWs()
  if (fileSearchTimer) { clearTimeout(fileSearchTimer); fileSearchTimer = null }
  // 释放录音资源：避免离开消息页后麦克风仍在占用
  if (recordTimer) { clearInterval(recordTimer); recordTimer = null }
  try { mediaRecorder?.stop() } catch { /* 忽略停止异常 */ }
  mediaStream?.getTracks().forEach(t => t.stop())
  mediaStream = null
  mediaRecorder = null
  try { voiceAudioEl?.pause() } catch { /* 忽略暂停异常 */ }
  voiceAudioEl = null
})

function onGlobalClick(e: MouseEvent) {
  const t = e.target as HTMLElement
  // 点击其他区域关闭底部面板（触发按钮本身以 .tool-btn 排除）
  const panel = document.querySelector('.composer-panel')
  if (panel && activePanel.value && !panel.contains(t) && !t.closest('.tool-btn')) {
    showEmoji.value = false
    showAttachPanel.value = false
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
/* 本页视觉统一收敛到钉钉设计令牌（--dt-*，见 styles/dingtalk.css），
   颜色 / 圆角 / 边框 / 间距均取自 --dt-*，不再与 --tui-* 混用。 */
.msg-page {
  display: flex; height: 100%; min-height: 0; min-width: 0;
  background: var(--dt-surface);
  overflow: hidden;
}

/* ===== 侧边栏 ===== */
.msg-sidebar { width: 288px; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid var(--dt-divider); background: var(--dt-surface); }
/* 桌面端头部（钉钉式）：一行「整宽搜索框 + 右侧 + 新建」 */
.sidebar-header {
  display: flex; align-items: center; gap: 8px;
  min-height: 56px; padding: 10px 12px; flex-shrink: 0;
  background: var(--dt-surface); border-bottom: 1px solid var(--dt-divider);
}
.sidebar-searchbar { flex: 1; min-width: 0; }
/* 钉钉式搜索框：占满宽度、圆角、浅灰底、无描边 */
.sidebar-searchbar :deep(.el-input__wrapper) {
  border-radius: var(--dt-radius-sm);
  background: #f2f3f5;
  box-shadow: none;
}
.sidebar-searchbar :deep(.el-input__wrapper.is-focus) {
  background: var(--dt-surface);
  box-shadow: 0 0 0 1px var(--dt-primary) inset;
}
.header-plus-btn {
  width: 34px; height: 34px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--dt-radius-sm); background: transparent;
  color: var(--dt-text-secondary); cursor: pointer;
  transition: background .16s var(--dt-ease), color .16s var(--dt-ease);
}
.header-plus-btn:hover { background: var(--dt-hover); color: var(--dt-primary); }
.sidebar-search { padding: 10px 12px 6px; }
.sidebar-search :deep(.el-input__wrapper) { border-radius: var(--dt-radius-sm); background: #f2f3f5; box-shadow: none; }
.sidebar-scroll { flex: 1; overflow-y: auto; min-height: 0; padding: 4px 0 8px; overscroll-behavior-y: contain; }

/* ===== 移动端下拉刷新 ===== */
/* 指示器（.ptr-ind / 吉祥物起跳）由公共模块 components/common/PullRefreshIndicator.vue 提供，
   这里只需保证滚动容器（.sidebar-scroll / .msg-list）自身可滚并阻断原生下拉刷新 */

/* 钉钉式会话行：52px 行高、圆形头像、发丝分割线、按压态 */
.conv-item { display: flex; align-items: center; gap: 10px; min-height: 52px; padding: 8px 12px; cursor: pointer; transition: background .15s var(--dt-ease); border-left: 3px solid transparent; }
.conv-item:hover { background: var(--dt-hover); }
.conv-item.active { background: var(--dt-primary-soft); border-left-color: var(--dt-primary); }
.conv-avatar-wrapper { position: relative; flex-shrink: 0; line-height: 0; }
/* 圆形头像（钉钉式） */
.conv-avatar-wrapper :deep(.el-avatar) { border-radius: 50%; }
.group-badge { position: absolute; bottom: -2px; right: -2px; width: 16px; height: 16px; border-radius: 5px; background: #f2f3f5; color: var(--dt-text-tertiary); font-size: 9px; display: flex; align-items: center; justify-content: center; border: 2px solid var(--dt-surface); }
/* 单聊在线绿点：仅对方在线时展示 */
.conv-online-dot {
  position: absolute; right: -1px; bottom: -1px; width: 10px; height: 10px;
  border-radius: 50%; background: var(--dt-success); border: 2px solid var(--dt-surface);
  box-sizing: content-box;
}
/* 右上角未读红色角标（钉钉式） */
.conv-badge-avatar { line-height: 0; }
.conv-badge-avatar :deep(.el-badge__content) { background: var(--dt-danger); border: none; font-size: 11px; }
.conv-avatar { flex-shrink: 0; }
.conv-info { flex: 1; min-width: 0; }
.conv-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.conv-name { font-size: 14px; font-weight: 600; color: var(--dt-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-time { font-size: 11px; color: var(--dt-text-quiet); font-family: var(--mono); flex-shrink: 0; margin-left: auto; }
.conv-bottom { display: flex; align-items: center; gap: 6px; margin-top: 3px; }
.conv-preview { font-size: 12.5px; color: var(--dt-text-tertiary); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-badge { --el-badge-bg-color: var(--dt-danger); flex-shrink: 0; }
.conv-member-count { font-size: 11px; color: var(--dt-text-quiet); flex-shrink: 0; }
/* 群聊在线人数：紧随最后一条消息前 */
.conv-online-count { font-size: 11.5px; color: var(--dt-success); flex-shrink: 0; font-weight: 500; }

.conv-item.pinned { background: var(--dt-hover); }

/* ===== 小绵管家：置顶常驻会话（钉钉式） ===== */
.butler-entry { background: linear-gradient(180deg, var(--dt-primary-soft), var(--dt-surface) 82%); }
.butler-entry:hover { background: var(--dt-primary-soft); }
.butler-entry.active { background: var(--dt-primary-soft); border-left-color: var(--dt-primary); }
.butler-entry .conv-name { font-weight: 600; }
.butler-entry .dt-tag { flex-shrink: 0; }
.butler-entry-avatar {
  width: 44px; height: 44px; border-radius: 50%; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  background: var(--dt-primary-soft); color: var(--dt-primary-strong);
}
.butler-entry-avatar img { width: 100%; height: 100%; object-fit: cover; }
.butler-entry-online {
  position: absolute; right: -1px; bottom: -1px; width: 10px; height: 10px;
  border-radius: 50%; background: var(--dt-success); border: 2px solid var(--dt-surface);
}

/* 右滑置顶容器（仅移动端生效，桌面端隐藏） */
.conv-swipe-wrap { position: relative; overflow: hidden; }
.conv-swipe-actions {
  position: absolute; right: 0; top: 0; bottom: 0;
  display: none;
  align-items: stretch; z-index: 1;
}
.swipe-action {
  width: 76px; border: none; background: #f2f3f5; color: var(--dt-text-secondary);
  font-size: 14px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .15s; outline: none;
  -webkit-tap-highlight-color: transparent;
}
.swipe-action:active { background: var(--dt-surface-press); }
.swipe-action:focus, .swipe-action:focus-visible { outline: none; box-shadow: none; }
.swipe-action.pinned { background: #f79009; color: #fff; }
.swipe-action.pinned:active { background: #e0820a; }
.swipe-action.danger { background: var(--dt-danger); color: #fff; }
.swipe-action.danger:active { background: #b42318; }
.conv-swipe-wrap .conv-item {
  position: relative; z-index: 2; background: var(--dt-surface);
  transition: transform .24s cubic-bezier(.22,.68,0,1);
  will-change: transform;
}

/* 两个动作（置顶 + 删除）：整行右滑位移按动作总宽计 */
.conv-swipe-wrap.swiped .conv-item {
  transform: translateX(-152px);
}

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 48px 0; color: var(--dt-text-quiet); font-size: 13px; }

/* ===== 聊天区域 ===== */
.msg-chat { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
/* 桌面端：主聊天列 + 右侧常驻信息面板（钉钉式两栏） */
.chat-body { flex: 1; min-height: 0; min-width: 0; display: flex; }
.chat-main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
.chat-header { display: flex; align-items: center; justify-content: space-between; min-height: 56px; padding: 8px 18px; border-bottom: 1px solid var(--dt-divider); background: var(--dt-surface); flex-shrink: 0; }
.chat-header-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
/* 聊天头部左侧：返回 + 头像 + 名称/副标题（不再承担进主页的职责） */
.chat-header-peer-avatar { flex-shrink: 0; }
/* 右上角的「个人主页」入口：与右侧其他圆形按钮同一视觉重量 */
.chat-head-homepage { color: #4b5563; }
.chat-name { font-size: 16px; font-weight: 600; color: var(--dt-text); }
.chat-sub { font-size: 11.5px; color: var(--dt-text-tertiary); margin-top: 2px; }
.chat-header-right { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
/* 聊天头操作按钮（钉钉式浅色方形热区） */
.chat-head-btn {
  width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--dt-radius-sm); background: transparent;
  color: var(--dt-text-secondary); cursor: pointer;
  transition: background .16s var(--dt-ease), color .16s var(--dt-ease);
}
.chat-head-btn:hover { background: var(--dt-hover); }
.chat-head-btn.on { color: var(--dt-primary); background: var(--dt-primary-soft); }
/* 群公告条：有公告时常驻，可点击查看 */
.chat-announce {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 18px; flex-shrink: 0;
  background: var(--dt-warning-soft); color: var(--dt-warning);
  border-bottom: 1px solid var(--dt-divider);
  font-size: 12.5px; cursor: pointer;
  transition: background .16s var(--dt-ease);
}
.chat-announce:hover { background: #fff1d9; }
.chat-announce-icon { flex-shrink: 0; }
.chat-announce-text { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--dt-text-secondary); }
.chat-announce-arrow { flex-shrink: 0; color: var(--dt-text-quiet); }
.msg-list { flex: 1; overflow-y: auto; padding: 20px; background: var(--dt-bg); overscroll-behavior-y: contain; }
/* 日期分隔线：居中灰字 */
.date-separator { text-align: center; margin: 10px 0; }
.date-separator span { display: inline-block; padding: 2px 10px; border-radius: var(--dt-radius-xs); font-size: 11px; color: var(--dt-text-quiet); background: rgba(0, 0, 0, 0.04); }
/* 钉钉风消息行：头像 + 气泡 */
.msg-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 14px; }
.msg-row.mine { flex-direction: row-reverse; }
.msg-avatar { flex-shrink: 0; border-radius: 50% !important; }
.msg-col { display: flex; flex-direction: column; max-width: min(70%, 460px); }
.msg-row.mine .msg-col { align-items: flex-end; }
.sender-name { font-size: 11px; color: var(--dt-text-quiet); margin: 0 4px 4px; }
.msg-bubble { width: fit-content; max-width: 100%; }
/* 文本气泡：圆角 8~10px，我方品牌蓝底白字，对方白底浅描边 */
.bubble-text { padding: 8px 12px; border-radius: var(--dt-radius-sm); font-size: 14px; line-height: 1.5; word-break: break-word; }
.mine .bubble-text { background: var(--dt-primary); color: var(--dt-text-inverse); border-top-right-radius: var(--dt-radius-xs); }
.theirs .bubble-text { background: var(--dt-surface); color: var(--dt-text); border-top-left-radius: var(--dt-radius-xs); border: 1px solid var(--dt-divider); }
.chat-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 60px 0; color: var(--dt-text-quiet); font-size: 13px; }

/* ===== 桌面端常驻「会话信息」面板（≥1200px 显示，窄屏隐藏） ===== */
.chat-info-panel {
  display: none;
  width: 264px; flex-shrink: 0;
  border-left: 1px solid var(--dt-divider);
  background: var(--dt-surface);
  padding: 22px 16px;
  overflow-y: auto;
  flex-direction: column; gap: 16px;
}
.info-profile { display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center; }
.info-profile-avatar { border-radius: 50% !important; background: var(--dt-primary-soft); color: var(--dt-primary-strong); font-size: 20px; }
.info-profile-name { font-size: 15px; font-weight: 600; color: var(--dt-text); }
.info-profile-sub { font-size: 12px; color: var(--dt-text-tertiary); }
.info-section { display: flex; flex-direction: column; gap: 10px; }
.info-section-head { display: flex; align-items: center; justify-content: space-between; }
.info-section-title { font-size: 12.5px; font-weight: 600; color: var(--dt-text-tertiary); }
.info-link { border: none; background: transparent; cursor: pointer; font-family: inherit; font-size: 12.5px; color: var(--dt-primary); padding: 0; }
.info-member-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px 4px; }
.info-member { display: flex; flex-direction: column; align-items: center; gap: 5px; border: none; background: transparent; cursor: pointer; font-family: inherit; padding: 0; }
.info-member :deep(.el-avatar) { border-radius: 50%; }
.info-member-name { max-width: 100%; font-size: 11px; color: var(--dt-text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.info-member-add-icon {
  width: 38px; height: 38px; box-sizing: border-box; border-radius: var(--dt-radius-sm);
  border: 1px dashed var(--dt-divider-strong); color: var(--dt-text-tertiary);
  display: flex; align-items: center; justify-content: center;
}
.info-empty { font-size: 12px; color: var(--dt-text-quiet); padding: 4px 0; }
.info-actions { display: flex; flex-direction: column; gap: 8px; margin-top: auto; }
.info-btn {
  height: 38px; border: 1px solid var(--dt-divider); border-radius: var(--dt-radius-sm);
  background: var(--dt-surface); color: var(--dt-text-secondary);
  font-size: 13.5px; font-family: inherit; cursor: pointer;
  transition: background .16s var(--dt-ease), border-color .16s var(--dt-ease);
}
.info-btn:hover { background: var(--dt-hover); }
.info-btn--primary { background: var(--dt-primary); border-color: var(--dt-primary); color: var(--dt-text-inverse); }
.info-btn--primary:hover { background: var(--dt-primary-strong); }
/* 仅宽屏（≥1200px）展开为钉钉式右侧信息栏，窄屏回退为弹窗 / 移动子页 */
@media (min-width: 1200px) {
  .chat-info-panel { display: flex; }
}

/* 钉钉风输入区：上方留白更紧凑、边框更浅；左工具条（表情 / 更多 / 语音），右发送 */
.msg-composer { position: relative; flex-shrink: 0; }
.msg-input-bar {
  border-top: 1px solid var(--dt-divider); background: var(--dt-surface);
  display: flex; align-items: flex-end; gap: 4px;
  padding: 8px 12px; position: relative;
}
.tool-btn {
  width: 36px; height: 36px; padding: 0; border: none; cursor: pointer;
  border-radius: var(--dt-radius-sm); background: transparent; color: var(--dt-text-secondary);
  display: flex; align-items: center; justify-content: center;
  transition: background .18s, color .18s; -webkit-tap-highlight-color: transparent;
}
.tool-btn:hover { background: var(--dt-hover); color: var(--dt-text); }
/* 面板展开时的按下态：只加深灰度，不给图标着色 */
.tool-btn.active { background: var(--dt-hover); color: var(--dt-primary); }

/* ===== 右侧发送插槽：有内容才出现，切换不重排、无卡顿 ===== */
.action-slot { position: relative; width: 44px; height: 36px; flex-shrink: 0; }
.action-slot > button {
  position: absolute; border: none; cursor: pointer;
  transform-origin: left center;
  transition: opacity .16s ease, transform .18s ease;
}
.action-slot > button.hidden { opacity: 0; transform: scale(.8); pointer-events: none; }
.action-slot > button.visible { opacity: 1; transform: scale(1); pointer-events: auto; }
.send-btn {
  left: 0; top: 0; width: 44px; height: 36px; padding: 0; border-radius: var(--dt-radius-sm);
  font-size: 13px; font-weight: 600;
  background: var(--dt-primary); color: var(--dt-text-inverse);
}
.send-btn:hover { background: var(--dt-primary-strong); }
/* 加号：与发送同尺寸叠放于同一插槽，靠左对齐，切换时不左右漂移 */
.plus-action { left: 0; top: 50%; width: 36px; height: 36px; margin-top: -18px; border-radius: 50%; }

/* ===== 底部展开面板（表情 / 更多）：单容器统一定高，内容切换不改变高度 ===== */
/* 高度 / 内边距 / 分隔线一起过渡，实现「自下而上」平滑展开，消息列表同步让位 */
.composer-panel {
  height: 0; flex-shrink: 0;
  padding: 0 12px;
  border-top: 0 solid var(--dt-divider);
  background: var(--dt-surface);
  display: flex; flex-direction: column;
  overflow: hidden;
  transition: height .24s cubic-bezier(.4, 0, .2, 1),
              padding .24s cubic-bezier(.4, 0, .2, 1),
              border-top-width .24s cubic-bezier(.4, 0, .2, 1);
}
.composer-panel.open { height: 236px; padding: 8px 12px 10px; border-top-width: 1px; }
.composer-panel-head { font-size: 12px; color: var(--dt-text-tertiary); margin-bottom: 8px; flex-shrink: 0; }
.plus-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; align-content: start;
}
.plus-fn {
  border: none; background: transparent; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 8px 2px; border-radius: var(--dt-radius-sm);
  transition: background .15s, transform .12s;
}
.plus-fn:hover { background: var(--dt-hover); }
.plus-fn:active { transform: scale(.94); }
.plus-fn-icon {
  width: 52px; height: 52px; border-radius: var(--dt-radius);
  display: flex; align-items: center; justify-content: center;
  background: #f2f3f5; color: var(--dt-text-secondary);
}
.plus-fn-label { font-size: 12px; color: var(--dt-text-tertiary); }

.input-main { flex: 1; min-width: 0; }
.input-main .el-textarea__inner {
  min-height: auto !important; padding: 8px 14px; line-height: 20px; resize: none;
  border-radius: var(--dt-radius-sm); border: none; background: #f2f3f5; box-shadow: none;
  transition: background .18s, box-shadow .18s;
}
.input-main .el-textarea__inner:focus {
  background: var(--dt-surface); box-shadow: 0 0 0 1px var(--dt-primary) inset;
}

.emoji-grid {
  display: grid; grid-template-columns: repeat(8, 1fr); gap: 2px;
  flex: 1; min-height: 0; overflow-y: auto; align-content: start;
}
.emoji-cell {
  border: none; background: transparent; cursor: pointer;
  font-size: 22px; line-height: 1; padding: 6px 0; border-radius: var(--dt-radius-xs);
  transition: background .14s, transform .12s;
}
.emoji-cell:hover { background: var(--dt-hover); }
.emoji-cell:active { transform: scale(.88); }

/* ===== 「按住说话」（钉钉风） ===== */
.hold-talk {
  width: 100%; height: 38px; border: none; border-radius: var(--dt-radius-sm); cursor: pointer;
  background: #f2f3f5; color: var(--dt-text-secondary);
  font-size: 14px; font-weight: 600;
  user-select: none; -webkit-user-select: none;
  touch-action: none; -webkit-touch-callout: none;
  transition: background .18s, color .18s;
}
.hold-talk.recording { background: var(--dt-primary-soft); color: var(--dt-primary); }
.hold-talk.cancel { background: var(--dt-danger-soft); color: var(--dt-danger); }

/* ===== 录音浮层（松开发送 / 上滑取消） ===== */
.record-overlay {
  position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%);
  width: 168px; padding: 22px 18px; border-radius: 18px;
  background: rgba(17, 24, 39, .82); color: #fff; z-index: 3000;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  box-shadow: 0 12px 40px rgba(0,0,0,.28); backdrop-filter: blur(6px);
}
.record-overlay.cancel { background: rgba(190, 26, 26, .86); }
.record-time { font-size: 22px; font-weight: 700; font-family: var(--mono); }
.record-hint { font-size: 12px; opacity: .85; text-align: center; }

.no-selection { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--dt-text-quiet); }
.no-selection h2 { font-size: 18px; color: var(--dt-text-secondary); margin: 0; }
.no-selection p { font-size: 13px; color: var(--dt-text-quiet); margin: 0; }
.quick-actions { display: flex; gap: 12px; margin-top: 16px; }

/* ==================== 弹窗统一皮肤（钉钉式） ==================== */
/* 白底 + 发丝线 + 单一品牌主按钮；移动端整页流程，桌面端居中弹窗 */
:deep(.el-dialog) {
  border-radius: var(--dt-radius-lg);
  overflow: hidden;
  box-shadow: var(--dt-shadow-2);
  padding: 0;
}
:deep(.el-dialog__header) {
  display: flex; align-items: center;
  min-height: 46px; margin: 0; padding: 0 18px;
  border-bottom: 1px solid var(--dt-divider);
}
:deep(.el-dialog__title) { font-size: 15px; font-weight: 600; color: var(--dt-text); letter-spacing: -0.2px; }
:deep(.el-dialog__headerbtn) {
  width: 34px; height: 34px; top: 9px; right: 12px;
  border-radius: 50%; transition: background .15s var(--dt-ease);
}
:deep(.el-dialog__headerbtn .el-dialog__close) { color: var(--dt-text-tertiary); }
:deep(.el-dialog__headerbtn:hover) { background: #f2f3f5; }
:deep(.el-dialog__body) { padding: 16px 18px; color: var(--dt-text-secondary); }
/* 列表型弹窗（邀请成员 / 群成员 / 群管理 / 选择联系人 / 发起群聊）：
   高度随内容自适应，最高到视口 2/3，超出才在弹窗内滚动——不是写死 2/3 高度 */
:deep(.dt-dialog-limit .el-dialog__body) {
  max-height: 66vh;
  overflow-y: auto;
  overscroll-behavior: contain;
}
:deep(.el-dialog__footer) {
  padding: 12px 18px calc(12px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--dt-divider);
  background: var(--dt-surface);
}
:deep(.el-dialog__footer .el-button) {
  min-width: 96px; height: 40px;
  border-radius: var(--dt-radius-sm); font-weight: 600; font-size: 14.5px;
}
/* 次要按钮改中性填充，去掉 Element Plus 默认白底描边的散色观感 */
:deep(.el-dialog__footer .el-button:not(.el-button--primary)) {
  background: #f2f3f5; border-color: transparent; color: var(--dt-text-secondary);
}
:deep(.el-dialog__footer .el-button--primary) { box-shadow: none; }

/* 移动端整页（钉钉式流程）：底色下沉、页头吸顶、确定条常驻 */
:deep(.el-dialog.is-fullscreen) {
  display: flex; flex-direction: column;
  height: 100%; margin: 0; overflow: hidden;
  border-radius: 0; box-shadow: none; background: var(--dt-bg);
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
  border-radius: var(--dt-radius-sm);
  background: #f2f3f5;
  box-shadow: 0 0 0 1px transparent inset;
  transition: background .18s var(--dt-ease), box-shadow .18s var(--dt-ease);
}
:deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px var(--dt-divider-strong) inset; }
:deep(.el-input__wrapper.is-focus) {
  background: var(--dt-surface);
  box-shadow: 0 0 0 1px var(--dt-primary) inset;
}

/* ==================== 弹窗内选择列表 ==================== */
/* 统一为白底 + 发丝线 + 56px 行高，与钉钉列表行规范一致 */
.member-search-results,
.add-member-results,
.add-friend-results,
.manage-invite-results,
.group-members-list {
  max-height: 56vh; overflow-y: auto; overflow-x: hidden;
  margin-top: 10px;
  border: 1px solid var(--dt-divider); border-radius: var(--dt-radius);
  background: var(--dt-surface);
}
.member-search-item,
.add-member-item,
.add-friend-item,
.manage-invite-item,
.group-member-item {
  display: flex; align-items: center; gap: 12px;
  width: 100%; min-height: 52px; padding: 8px 12px;
  border: none; border-bottom: 1px solid var(--dt-divider); background: transparent;
  cursor: pointer; font-family: inherit; text-align: left;
  transition: background .15s var(--dt-ease);
}
.member-search-item:last-child,
.add-member-item:last-child,
.add-friend-item:last-child,
.manage-invite-item:last-child,
.group-member-item:last-child { border-bottom: none; }
.member-search-item:hover,
.add-member-item:hover,
.add-friend-item:hover,
.manage-invite-item:hover { background: var(--dt-hover); }
.member-search-item:active,
.add-member-item:active,
.add-friend-item:active { background: var(--dt-surface-press); }
.add-friend-item { justify-content: space-between; }
.add-friend-item-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
/* 头像 / 姓名为个人主页入口：点击查看对方主页，与「聊天」按钮并存不冲突 */
.add-friend-item-left.is-clickable { cursor: pointer; border-radius: var(--dt-radius-sm); }
.add-friend-item-left.is-clickable:active { background: #f2f3f5; }
.add-friend-item-left.is-clickable:hover .add-friend-item-name { color: var(--dt-primary); }
/* 可点击头像统一样式：会话头像 / 通讯录头像 / 群成员头像点开个人主页 */
.conv-avatar-clickable,
.addr-avatar { cursor: pointer; }
.member-search-info,
.add-member-info,
.manage-invite-info,
.add-friend-item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.add-friend-item-name { font-size: 15px; font-weight: 600; color: var(--dt-text); display: flex; align-items: center; gap: 8px; }
.member-name,
.add-member-info span,
.manage-invite-info span { font-size: 15px; font-weight: 600; color: var(--dt-text); }
.add-friend-item-username,
.member-username,
.add-member-info small,
.manage-invite-info small { font-size: 12px; color: var(--dt-text-tertiary); }
.member-info { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; }
.member-info .member-name { font-size: 15px; font-weight: 600; color: var(--dt-text); }

/* ===== 选择联系人：搜索框 / 提示 / 已选成员 ===== */
.add-friend-search-box { margin-bottom: 4px; }
.member-search-box { margin-bottom: 4px; }

/* ===== 发起群聊：通讯录「最近联系人」快速勾选 ===== */
.group-pick { margin-top: 12px; }
.group-pick-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12.5px; font-weight: 600; color: var(--dt-text-secondary);
}
.group-pick-hint { font-weight: 400; font-size: 11.5px; color: var(--dt-text-quiet); }
.group-pick-list {
  max-height: 34vh; overflow-y: auto; overflow-x: hidden;
  border: 1px solid var(--dt-divider); border-radius: var(--dt-radius);
  background: var(--dt-surface);
}
.group-pick-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; cursor: pointer;
  border-bottom: 1px solid var(--dt-divider);
  transition: background .15s var(--dt-ease);
}
.group-pick-row:last-child { border-bottom: none; }
.group-pick-row:hover { background: var(--dt-hover); }
.group-pick-row:active { background: var(--dt-surface-press); }
.group-pick-row.picked { background: var(--dt-primary-soft); }
.group-pick-check { pointer-events: none; margin-right: 0; }
.group-pick-name { flex: 1; min-width: 0; font-size: 14px; color: var(--dt-text); }
.add-friend-hint {
  display: flex; align-items: center; gap: 6px; margin-top: 10px;
  font-size: 11.5px; color: var(--dt-text-quiet);
}
.search-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 30px 0; color: var(--dt-text-quiet); font-size: 13px;
}
.selected-members { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 2px; }
.selected-members .el-tag {
  background: var(--dt-primary-soft); border-color: transparent;
  color: var(--dt-primary-strong); font-weight: 500;
}

/* ===== 拖拽上传 ===== */
.msg-list { position: relative; }
.drag-overlay {
  position: absolute; inset: 0; z-index: 10;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  background: var(--dt-primary); color: var(--dt-text-inverse); border-radius: var(--dt-radius-sm);
}
.drag-overlay span { font-size: 18px; font-weight: 600; }
.drag-overlay small { font-size: 13px; opacity: .85; }

.upload-progress-bar {
  position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: rgba(0, 0, 0, 0.06); z-index: 10;
}
.upload-progress-inner {
  height: 100%; background: var(--dt-primary); transition: width .3s;
  border-radius: 0 2px 2px 0;
}
.upload-progress-bar span {
  position: absolute; top: -22px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: var(--dt-primary); white-space: nowrap;
}

/* ===== 文件/图片消息 ===== */
.bubble-image {
  max-width: 260px; cursor: pointer; border-radius: var(--dt-radius-sm);
  overflow: hidden; box-shadow: var(--dt-shadow-1);
}
.bubble-image img {
  width: 100%; height: auto; display: block;
  transition: transform .2s;
}
.bubble-image:hover img { transform: scale(1.03); }

.bubble-file {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 13px; border-radius: var(--dt-radius-sm); cursor: pointer;
  min-width: 200px;
}
.mine .bubble-file { background: var(--dt-primary); color: var(--dt-text-inverse); border-top-right-radius: var(--dt-radius-xs); }
.theirs .bubble-file { background: var(--dt-surface); color: var(--dt-text); border-top-left-radius: var(--dt-radius-xs); border: 1px solid var(--dt-divider); }
.bubble-file-info { flex: 1; min-width: 0; }
.bubble-file-name {
  font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: block;
}
.bubble-file-info small { font-size: 11px; opacity: .7; }

/* 语音消息（钉钉风语音条） */
.bubble-voice {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: var(--dt-radius-sm); cursor: pointer; min-width: 84px;
}
.mine .bubble-voice { background: var(--dt-primary); color: var(--dt-text-inverse); border-top-right-radius: var(--dt-radius-xs); }
.theirs .bubble-voice { background: var(--dt-surface); color: var(--dt-text); border-top-left-radius: var(--dt-radius-xs); border: 1px solid var(--dt-divider); }
.bubble-voice .voice-play-icon { flex-shrink: 0; }
.voice-bars { display: flex; align-items: center; gap: 3px; flex: 1; }
.voice-bars i { width: 3px; height: 8px; border-radius: 2px; background: currentColor; opacity: .55; }
.voice-bars i:nth-child(2) { height: 15px; }
.voice-bars i:nth-child(3) { height: 10px; }
.bubble-voice.playing .voice-bars i { animation: voicePulse .8s ease-in-out infinite; }
.bubble-voice.playing .voice-bars i:nth-child(2) { animation-delay: .15s; }
.bubble-voice.playing .voice-bars i:nth-child(3) { animation-delay: .3s; }
.voice-dur { font-size: 12px; opacity: .8; flex-shrink: 0; font-family: var(--mono); }
@keyframes voicePulse { 0%, 100% { transform: scaleY(.6); } 50% { transform: scaleY(1.5); } }

/* ===== 图片预览 ===== */
.image-preview-overlay {
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(0, 0, 0, 0.85); display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
}
.image-preview-overlay img {
  max-width: 82vw; max-height: 82vh; border-radius: var(--dt-radius-sm);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
}

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ===== 群管理弹窗 ===== */
.manage-section { margin-bottom: 4px; }
.manage-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.manage-section-title { font-size: 14px; font-weight: 600; color: var(--dt-text); display: flex; align-items: center; gap: 6px; }
.member-count-tag { font-size: 11.5px; color: var(--dt-text-quiet); font-weight: 400; }
.manage-announcement-content { padding: 12px 14px; background: #f2f3f5; border-radius: var(--dt-radius-sm); min-height: 40px; }
.manage-announcement-content p { margin: 0; font-size: 12.5px; color: var(--dt-text-secondary); line-height: 1.6; white-space: pre-wrap; }
.manage-empty-hint { font-size: 12.5px; color: var(--dt-text-quiet); }
.manage-announcement-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.manage-invite-box { margin-bottom: 12px; padding: 12px; background: #f2f3f5; border-radius: var(--dt-radius-sm); border: 1px solid var(--dt-divider); }
.manage-invite-results { max-height: 180px; overflow-y: auto; margin-top: 8px; }
.manage-invite-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; border-radius: var(--dt-radius-sm); transition: background .15s; }
.manage-invite-item:hover { background: var(--dt-hover); }
.manage-invite-info { flex: 1; display: flex; flex-direction: column; }
.manage-invite-info span { font-size: 14px; font-weight: 500; color: var(--dt-text); }
.manage-invite-info small { font-size: 11.5px; color: var(--dt-text-quiet); }
.manage-members-list { max-height: 56vh; overflow-y: auto; }
.manage-member-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 52px; padding: 8px 2px; border-bottom: 1px solid var(--dt-divider); }
.manage-member-item:last-child { border-bottom: none; }
.manage-member-left { display: flex; align-items: center; gap: 10px; }
.manage-member-info { display: flex; align-items: center; gap: 8px; }
.manage-member-name { font-size: 14px; font-weight: 500; color: var(--dt-text); }
.manage-danger-zone { padding: 12px; background: var(--dt-danger-soft); border-radius: var(--dt-radius-sm); border: 1px solid transparent; }
.manage-danger-actions { display: flex; gap: 10px; }

/* ==================== 消息中心：移动端吸顶栏 ==================== */
.msg-appbar {
  display: flex; align-items: center; gap: 6px;
  min-height: 52px; padding: 0 8px; flex-shrink: 0;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid var(--dt-divider);
}
.msg-appbar-btn {
  width: 40px; height: 40px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; background: transparent;
  color: var(--dt-text); cursor: pointer;
  transition: background .18s var(--dt-ease);
  -webkit-tap-highlight-color: transparent;
}
.msg-appbar-btn:active { background: var(--dt-hover); }
.msg-appbar-title {
  flex: 1; min-width: 0;
  font-size: 16.5px; font-weight: 600; letter-spacing: -0.2px; color: var(--dt-text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.msg-appbar-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }

/* ==================== 桌面端视图切换 ==================== */
.sidebar-seg { padding: 8px 10px 2px; }
.sidebar-seg .tui-seg { width: 100%; }
.seg-count {
  margin-left: 4px; padding: 0 5px; border-radius: 999px;
  background: var(--dt-danger); color: var(--dt-text-inverse);
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
  background: var(--dt-surface);
  box-shadow: var(--dt-shadow-2);
}
.msg-drawer-head {
  display: flex; align-items: center; gap: 12px;
  padding: calc(20px + env(safe-area-inset-top)) 18px 18px;
  background: var(--dt-surface);
  border-bottom: 1px solid var(--dt-divider);
  color: var(--dt-text);
}
.msg-drawer-head :deep(.el-avatar) { border-radius: 50%; background: var(--dt-primary-soft); color: var(--dt-primary-strong); flex-shrink: 0; }
.msg-drawer-user { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.msg-drawer-name { font-size: 14px; font-weight: 600; color: var(--dt-text); }
.msg-drawer-sub {
  font-size: 11.5px; color: var(--dt-text-quiet);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.msg-drawer-nav { flex: 1; overflow-y: auto; padding: 8px 8px calc(12px + env(safe-area-inset-bottom)); display: flex; flex-direction: column; gap: 2px; }
.msg-drawer-item {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 10px; border: none; border-radius: var(--dt-radius-sm);
  background: transparent; cursor: pointer; font-family: inherit; text-align: left;
  color: var(--dt-text-secondary); font-size: 13.5px; font-weight: 500;
  transition: background .15s var(--dt-ease), color .15s var(--dt-ease);
}
.msg-drawer-item:active { background: var(--dt-hover); }
.msg-drawer-item.active { background: var(--dt-primary-soft); color: var(--dt-primary-strong); font-weight: 600; }
.msg-drawer-icon { display: flex; color: inherit; }
.msg-drawer-label { flex: 1; }
.msg-drawer-section {
  padding: 10px 10px 6px; font-size: 12px; font-weight: 600;
  color: var(--tui-text-quiet); letter-spacing: .3px;
}
.msg-appbar-btn.is-busy .dt-icon { animation: msg-spin 1s linear infinite; }
@keyframes msg-spin { to { transform: rotate(360deg); } }

.drawer-mask-enter-active, .drawer-mask-leave-active { transition: opacity .22s ease; }
.drawer-mask-enter-from, .drawer-mask-leave-to { opacity: 0; }
.drawer-panel-enter-active { transition: transform .26s cubic-bezier(.22, .68, 0, 1); }
.drawer-panel-leave-active { transition: transform .2s ease-in; }
.drawer-panel-enter-from, .drawer-panel-leave-to { transform: translateX(-100%); }

/* ==================== 通讯录（钉钉列表行规范：52px 行高 + 发丝线） ==================== */
.addr-section-head { display: flex; align-items: center; gap: 8px; padding: 12px 14px 6px; }
.addr-section-title { font-size: 12.5px; font-weight: 600; color: var(--dt-text-tertiary); letter-spacing: .2px; }
.addr-section-count { margin-left: auto; font-size: 11.5px; color: var(--dt-text-quiet); }
.addr-row {
  display: flex; align-items: center; gap: 10px; width: 100%;
  min-height: 52px; padding: 8px 14px;
  border: none; border-bottom: 1px solid var(--dt-divider);
  background: var(--dt-surface); cursor: pointer;
  font-family: inherit; text-align: left;
  transition: background .15s var(--dt-ease);
}
.addr-row:hover { background: var(--dt-hover); }
.addr-row:active { background: var(--dt-surface-press); }
.addr-row-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.addr-row-name { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: var(--dt-text); }
.addr-row-sub {
  font-size: 11.5px; color: var(--dt-text-tertiary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.addr-org-icon {
  width: 32px; height: 32px; flex-shrink: 0; border-radius: var(--dt-radius-sm);
  display: flex; align-items: center; justify-content: center;
  background: var(--dt-primary-soft); color: var(--dt-primary-strong);
}
.addr-org-icon.major { width: 28px; height: 28px; background: var(--dt-primary-soft); color: var(--dt-primary-strong); }
.addr-org-icon.klass { width: 26px; height: 26px; background: #f2f3f5; color: var(--dt-text-secondary); }
.addr-row-major { padding-left: 28px; }
.addr-row-class { padding-left: 42px; }
.addr-row-student { padding-left: 54px; background: var(--dt-surface-z1); }

/* 组织架构树：层级缩进 + 每一级都有「导轨竖线 + 折角横线」，形成真正的树状层级 */
.addr-row-org, .addr-row-major, .addr-row-class, .addr-row-student { position: relative; }
.addr-row-major::before,
.addr-row-class::before,
.addr-row-student::before {
  content: ''; position: absolute; top: 0; bottom: 0; width: 1px;
  background: var(--dt-tree-line); pointer-events: none;
}
.addr-row-major::after,
.addr-row-class::after,
.addr-row-student::after {
  content: ''; position: absolute; top: 50%; height: 1px; width: 12px;
  background: var(--dt-tree-line); pointer-events: none;
}
.addr-row-major::before, .addr-row-major::after { left: 18px; }
.addr-row-class::before, .addr-row-class::after { left: 32px; }
.addr-row-student::before, .addr-row-student::after { left: 44px; }
.addr-chevron {
  color: var(--dt-text-quiet);
  flex-shrink: 0;
  transition: transform .18s var(--dt-ease);
}
.addr-chevron.open { transform: rotate(90deg); }
.addr-search-results { padding-bottom: 8px; }
.addr-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 24px 0; color: var(--dt-text-quiet); font-size: 13px;
}
.addr-empty { padding: 24px 16px; text-align: center; color: var(--dt-text-quiet); font-size: 12.5px; }

/* ==================== 文件（跨会话文件汇总） ==================== */
/* 顶部区：搜索框 → 类别筛选 → 列表，三段之间留出呼吸间距 */
.file-topbar { padding: 12px 12px 0; }
.file-topbar .el-input__wrapper { border-radius: var(--dt-radius-sm); }
.file-filter {
  display: flex; gap: 8px; flex-wrap: wrap;
  padding: 16px 0 14px;
}
.file-filter-item {
  border: none; cursor: pointer; font-family: inherit;
  font-size: 13px; line-height: 1; padding: 8px 14px; border-radius: 999px;
  background: #f2f3f5; color: var(--dt-text-secondary);
  transition: background .16s, color .16s;
}
.file-filter-item:hover { color: var(--dt-text); }
.file-filter-item.active { background: var(--dt-primary-soft); color: var(--dt-primary-strong); font-weight: 600; }

.file-list { padding: 0 8px 12px; }
.file-item {
  display: flex; align-items: center; gap: 9px;
  padding: 8px; border-radius: var(--dt-radius-sm); cursor: pointer;
  transition: background .15s;
}
.file-item:hover { background: var(--dt-hover); }
.file-thumb {
  width: 36px; height: 36px; flex-shrink: 0; border-radius: var(--dt-radius-sm);
  display: flex; align-items: center; justify-content: center;
  background: #f2f3f5; color: var(--dt-primary-strong);
  overflow: hidden;
}
.file-thumb img { width: 100%; height: 100%; object-fit: cover; }
.file-thumb.t-voice { color: #079455; }
.file-body { flex: 1; min-width: 0; }
.file-name {
  font-size: 13px; font-weight: 500; color: var(--dt-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-meta {
  display: flex; align-items: center; gap: 8px; margin-top: 4px;
  font-size: 11.5px; color: var(--dt-text-quiet);
}
.file-source {
  display: inline-flex; align-items: center; gap: 3px;
  max-width: 45%; overflow: hidden; white-space: nowrap;
  color: var(--dt-primary-strong);
}
.file-source:hover { text-decoration: underline; }
.file-src-tag {
  flex-shrink: 0; font-size: 10px; line-height: 1;
  padding: 1px 3px; border-radius: var(--dt-radius-xs);
  background: var(--dt-primary-soft); color: var(--dt-primary-strong);
}
.file-action { flex-shrink: 0; color: var(--dt-text-quiet); }

/* ==================== 通知（钉钉列表行规范） ==================== */
.notif-actions { display: flex; justify-content: flex-end; padding: 10px 12px 0; }
.notif-action-btn {
  border: none; background: transparent; cursor: pointer; font-family: inherit;
  font-size: 13px; color: var(--dt-primary);
}
.notif-action-btn:disabled { color: var(--dt-text-quiet); cursor: default; }
.notif-row {
  display: flex; align-items: flex-start; gap: 10px; width: 100%;
  min-height: 50px; padding: 10px 14px;
  border: none; border-bottom: 1px solid var(--dt-divider);
  background: var(--dt-surface); cursor: pointer;
  font-family: inherit; text-align: left;
  transition: background .15s var(--dt-ease);
}
.notif-row:last-child { border-bottom: none; }
.notif-row:active { background: var(--dt-surface-press); }
.notif-icon {
  width: 32px; height: 32px; flex-shrink: 0; border-radius: var(--dt-radius-sm);
  display: flex; align-items: center; justify-content: center;
}
.notif-main { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.notif-top { display: flex; align-items: baseline; gap: 8px; }
.notif-title {
  flex: 1; min-width: 0; font-size: 13.5px; font-weight: 600; color: var(--dt-text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.notif-time { font-size: 11px; color: var(--dt-text-quiet); flex-shrink: 0; }
.notif-content { font-size: 11.5px; line-height: 1.5; color: var(--dt-text-tertiary); }
.notif-row.unread .notif-content { color: var(--dt-text-secondary); }
.notif-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--dt-danger); flex-shrink: 0; margin-top: 7px; }

/* 桌面端左栏：通讯录 / 通知 行以白底呈现，与消息列表观感统一 */
@media (min-width: 768px) {
  .addr-section-head { padding-left: 12px; padding-right: 12px; }
  .addr-row:not(.addr-row-major):not(.addr-row-class),
  .notif-row { padding-left: 12px; padding-right: 12px; }
}

/* ===== 移动端适配 ===== */
.back-btn { display: none; }
@media (max-width: 767px) {
  /* 统一底色 */
  .msg-page { flex-direction: column; border-radius: 0; border: none; box-shadow: none; background: var(--dt-bg); }
  .msg-sidebar { width: 100% !important; flex: 1; min-height: 0; border-right: none; background: var(--dt-bg); }
  .sidebar-header { background: var(--dt-surface); }
  .sidebar-search { background: var(--dt-surface); }
  .sidebar-scroll { background: var(--dt-bg); flex: 1; overflow-y: auto; min-height: 0; padding: 4px 0 0; }
  /* 通讯录 / 通知：移动端整行白底，靠发丝线成组，与桌面端卡片观感一致 */
  .addr-row, .notif-row, .addr-row-major, .addr-row-class { background: var(--dt-surface); }
  .addr-row:hover { background: var(--dt-surface); }
  .addr-section-head { padding-top: 16px; }
  /* 会话行紧贴无间隙，靠发丝线分隔成组 */
  .conv-swipe-wrap { margin: 0; }
  .conv-item { margin: 0; padding: 10px 14px; background: var(--dt-surface); border-radius: 0; border-left: none; border-bottom: 1px solid var(--dt-divider); }
  .conv-item:hover { background: var(--dt-surface); }
  .conv-item.active { background: var(--dt-primary-soft); }
  .conv-item.pinned { background: var(--dt-hover); }
  .conv-swipe-wrap.swiped .conv-item { background: var(--dt-hover); }
  .conv-swipe-actions { display: flex; opacity: 0; }
  .conv-swipe-wrap.swiped .conv-swipe-actions { opacity: 1; }
  .group-badge { border-color: var(--dt-surface); }
  /* 移动端不展示桌面端右侧信息面板（成员信息走弹窗 / 移动子页） */
  .chat-info-panel { display: none; }

  /* 聊天页 */
  .msg-chat { width: 100%; flex: 1; background: var(--dt-surface); }
  .back-btn { display: inline-flex; color: var(--dt-text); }
  .chat-header {
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: saturate(180%) blur(14px);
    -webkit-backdrop-filter: saturate(180%) blur(14px);
    border-bottom: 1px solid var(--dt-divider);
    min-height: 52px; padding: 6px 8px;
  }
  .chat-header .el-button { color: var(--dt-text); }
  .chat-name { color: var(--dt-text); font-size: 16.5px; }
  .chat-sub { color: var(--dt-text-tertiary); }
  .chat-header-group-avatar { border-radius: 50%; background: var(--dt-primary-soft); }
  .chat-header-group-avatar .el-avatar__text .el-icon { color: var(--dt-primary-strong); }
  .msg-list { padding: 12px 10px; background: var(--dt-bg); }
  .msg-row { gap: 6px; margin-bottom: 12px; }
  .msg-avatar { width: 34px !important; height: 34px !important; font-size: 14px; }
  .msg-col { max-width: 76%; }
  .bubble-image { max-width: 180px; }
  .bubble-file { min-width: 150px; }
  .msg-input-bar { padding: 7px 8px calc(7px + env(safe-area-inset-bottom)); }
  /* 底部展开面板在窄屏占满宽度，并留出安全区 */
  .composer-panel.open { height: 224px; padding-bottom: calc(10px + env(safe-area-inset-bottom)); }
  .hold-talk { height: 40px; }
  .tool-btn { width: 34px; height: 34px; }

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
    background: var(--dt-surface);
    margin-bottom: 1px;
  }
  :deep(.el-dialog .el-textarea__inner) { padding: 10px 12px; line-height: 1.6; }
  :deep(.el-dialog .el-input__inner) { font-size: 15px; }
  :deep(.manage-announcement-content),
  :deep(.manage-invite-box) { border-radius: var(--dt-radius-sm); }
}

/* ===== 移动端群设置 / 公告 / 文件子页面（钉钉式：卡片 + 56px 列表行） ===== */
.group-sub-page {
  position: fixed; inset: 0; z-index: 1200;
  background: var(--dt-bg); display: flex; flex-direction: column;
}
.gsp-header {
  display: flex; align-items: center; justify-content: space-between;
  min-height: 48px; padding: 4px 8px; background: var(--dt-surface); border-bottom: 1px solid var(--dt-divider);
  flex-shrink: 0;
}
.gsp-title { font-size: 15px; font-weight: 600; color: var(--dt-text); letter-spacing: -0.2px; }
.gsp-edit-btn { color: var(--dt-primary); font-size: 14px; }
/* 钉钉式群设置：分组卡片 + 成员九宫格 */
.gsp-body { flex: 1; overflow-y: auto; padding: 12px; background: var(--dt-bg); }
.gsp-card { background: var(--dt-surface); border-radius: var(--dt-radius); overflow: hidden; margin-bottom: 12px; }
.gsp-card-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px 4px; }
.gsp-card-title { font-size: 12.5px; font-weight: 600; color: var(--dt-text-tertiary); }
.gsp-card-more {
  display: inline-flex; align-items: center; gap: 2px; border: none; background: transparent;
  cursor: pointer; font-family: inherit; font-size: 12.5px; color: var(--dt-text-quiet);
}
.gsp-card .gsp-item:last-child { border-bottom: none; }
.gsp-item.is-readonly { cursor: default; }
.gsp-item-thumb {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  background: var(--dt-surface-z1); color: var(--dt-text-secondary);
  font-size: 14px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.gsp-member-grid { display: grid; grid-template-columns: repeat(5, 1fr); padding: 8px 6px 14px; }
.gsp-member {
  display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 6px 0;
  border: none; background: transparent; cursor: pointer; font-family: inherit;
}
.gsp-member:active { opacity: .65; }
.gsp-member-name {
  max-width: 100%; font-size: 11.5px; color: var(--dt-text-tertiary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.gsp-member-add-icon {
  width: 44px; height: 44px; box-sizing: border-box; border-radius: 50%;
  border: 1px dashed var(--dt-divider-strong); color: var(--dt-text-tertiary);
  display: flex; align-items: center; justify-content: center;
}
.group-crop-box { max-height: 360px; overflow: hidden; }

/* 群二维码邀请卡（钉钉式） */
.gsp-qr-card {
  display: flex; flex-direction: column; align-items: center;
  padding: 18px 14px; background: var(--dt-surface); border-radius: var(--dt-radius);
}
.gsp-qr-head { display: flex; align-items: center; gap: 10px; width: 100%; }
.gsp-qr-avatar {
  width: 42px; height: 42px; border-radius: 50%; flex-shrink: 0;
  background: var(--dt-primary-soft); color: var(--dt-primary-strong);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 600;
}
.gsp-qr-meta { min-width: 0; }
.gsp-qr-name { font-size: 15px; font-weight: 600; color: var(--dt-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gsp-qr-sub { font-size: 12px; color: var(--dt-text-quiet); margin-top: 2px; }
.gsp-qr-box {
  width: 200px; height: 200px; margin: 18px 0 10px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--dt-divider); border-radius: var(--dt-radius); overflow: hidden;
}
.gsp-qr-box img { width: 100%; height: 100%; object-fit: contain; }
.gsp-qr-loading { display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--dt-text-quiet); font-size: 13px; }
.gsp-qr-tip { margin: 0 0 16px; font-size: 12.5px; color: var(--dt-text-tertiary); text-align: center; line-height: 1.5; }
.gsp-qr-actions { display: flex; gap: 10px; width: 100%; }
.gsp-qr-btn {
  flex: 1; height: 40px; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  border: none; border-radius: var(--dt-radius-sm); cursor: pointer; font-family: inherit;
  font-size: 14px; background: var(--dt-primary-soft); color: var(--dt-primary-strong);
}
.gsp-qr-btn:active { background: #d9ebff; }
.gsp-qr-reset {
  margin-top: 10px; border: none; background: transparent; cursor: pointer; font-family: inherit;
  font-size: 12.5px; color: var(--dt-text-quiet); text-decoration: underline;
}
.gsp-item-switch { cursor: default; }
.conv-mute { color: var(--dt-text-quiet); flex-shrink: 0; }

/* 桌面端会话行尾操作按钮（置顶 / 删除）：常占位不抖动，悬停显形，已置顶常亮 */
.conv-pin-btn,
.conv-del-btn {
  width: 26px; height: 26px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 6px; background: transparent;
  color: var(--dt-text-quiet); cursor: pointer;
  opacity: 0; transition: opacity .15s var(--dt-ease), color .15s var(--dt-ease);
}
.conv-item:hover .conv-pin-btn,
.conv-item:hover .conv-del-btn { opacity: 1; }
.conv-pin-btn:hover,
.conv-del-btn:hover { background: var(--dt-hover); }
.conv-pin-btn.on { opacity: 1; color: var(--dt-primary); }
.conv-del-btn:hover { color: var(--dt-danger); }

/* 桌面端群管理弹窗：二维码与个人设置 */
.manage-qr-box {
  width: 152px; height: 152px; margin: 4px auto 10px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--dt-divider); border-radius: var(--dt-radius); overflow: hidden;
}
.manage-qr-box img { width: 100%; height: 100%; object-fit: contain; }
.manage-qr-actions { display: flex; align-items: center; justify-content: center; gap: 8px; }
.manage-switch-row {
  display: flex; align-items: center; justify-content: space-between;
  min-height: 44px; font-size: 14px; color: var(--dt-text);
}
.gsp-item {
  display: flex; align-items: center; gap: 12px; min-height: 52px; padding: 10px 14px;
  border-bottom: 1px solid var(--dt-divider); cursor: pointer;
  font-size: 15px; color: var(--dt-text); transition: background .15s var(--dt-ease);
}
.gsp-item:active { background: var(--dt-surface-press); }
.gsp-item:last-child { border-bottom: none; }
.gsp-item-icon {
  width: 36px; height: 36px; border-radius: var(--dt-radius-sm); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.gsp-item-icon.announce { background: var(--dt-warning-soft); color: var(--dt-warning); }
.gsp-item-icon.filee { background: var(--dt-surface-z1); color: var(--dt-text-secondary); }
.gsp-item-icon.member { background: var(--dt-primary-soft); color: var(--dt-primary-strong); }
.gsp-item-icon.add { background: var(--dt-success-soft); color: var(--dt-success); }
.gsp-item-icon.manage { background: var(--dt-surface-z1); color: var(--dt-text-secondary); }
.gsp-item-label { flex: 1; }
.gsp-item-value { font-size: 12px; color: var(--dt-text-quiet); }
.gsp-arrow { font-size: 14px; color: var(--dt-text-quiet); }
.gsp-danger-btn {
  margin-top: 16px; width: 100%; padding: 14px 0; border: none; border-radius: var(--dt-radius);
  background: var(--dt-surface); color: var(--dt-danger); font-size: 15px; cursor: pointer;
}
.gsp-empty-box {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 56px 0 30px; color: var(--dt-text-quiet); font-size: 14px;
  background: var(--dt-surface); border-radius: var(--dt-radius);
}
.gsp-empty-box small { font-size: 12px; color: var(--dt-text-quiet); }
.gsp-ann-card { background: var(--dt-surface); border: 1px solid var(--dt-divider); border-radius: var(--dt-radius); padding: 16px; }
.gsp-ann-head {
  display: flex; align-items: center; gap: 6px;
  font-size: 15px; font-weight: 600; color: var(--dt-text); margin-bottom: 10px;
}
.gsp-ann-head .el-icon { color: var(--dt-warning); }
.gsp-ann-text { margin: 0; font-size: 14px; color: var(--dt-text-secondary); line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.gsp-ann-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.gsp-cancel-btn, .gsp-save-btn { padding: 8px 22px; border-radius: var(--dt-radius-sm); font-size: 14px; border: none; cursor: pointer; }
.gsp-cancel-btn { background: var(--dt-surface-z1); color: var(--dt-text-secondary); }
.gsp-save-btn { background: var(--dt-primary); color: #fff; }
.gsp-save-btn:disabled { opacity: .5; cursor: not-allowed; }
.gsp-file-list { background: var(--dt-surface); border: 1px solid var(--dt-divider); border-radius: var(--dt-radius); overflow: hidden; margin-bottom: 14px; }
.gsp-file-item {
  display: flex; align-items: center; gap: 10px; min-height: 52px; padding: 8px 12px;
  border-bottom: 1px solid var(--dt-divider); cursor: pointer;
}
.gsp-file-item:active { background: var(--dt-surface-press); }
.gsp-file-item:last-child { border-bottom: none; }
.gsp-file-icon {
  width: 40px; height: 40px; border-radius: var(--dt-radius-sm); flex-shrink: 0;
  background: var(--dt-surface-z1); color: var(--dt-text-secondary);
  display: flex; align-items: center; justify-content: center;
}
.gsp-file-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.gsp-file-name { font-size: 15px; color: var(--dt-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gsp-file-meta { font-size: 11.5px; color: var(--dt-text-quiet); }
.gsp-upload-btn {
  width: 100%; padding: 14px 0; border: 1px dashed var(--dt-divider-strong); border-radius: var(--dt-radius-sm);
  background: var(--dt-surface); color: var(--dt-text-secondary); font-size: 14px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.gsp-upload-btn:active { background: var(--dt-surface-press); }

/* ==================== 移动端：还原本次「桌面侧边栏密度收紧」之前的原始尺寸 ====================
   本次收紧（会话行 / 通讯录 / 文件 / 通知 / 侧边抽屉）是为桌面端左栏做的信息密度优化，
   移动端不应受影响，故在此把原始数值还原回来。桌面端仍按收紧后的值渲染。 */
@media (max-width: 767px) {
  .conv-item { gap: 12px; min-height: 64px; padding: 11px 14px; }
  .conv-name { font-size: 14.5px; }
  .sidebar-seg { padding: 10px 12px 4px; }

  .msg-drawer-name { font-size: 15.5px; }
  .msg-drawer-item { gap: 12px; padding: 12px; font-size: 14.5px; }

  .addr-section-head { padding: 16px 16px 8px; }
  .addr-section-title { font-size: 13px; }
  .addr-section-count { font-size: 12px; }
  .addr-row { gap: 12px; min-height: 56px; padding: 10px 16px; }
  .addr-row-main { gap: 3px; }
  .addr-row-name { font-size: 15px; }
  .addr-row-sub { font-size: 12.5px; }
  .addr-org-icon { width: 36px; height: 36px; }
  .addr-org-icon.major { width: 32px; height: 32px; }
  .addr-org-icon.klass { width: 30px; height: 30px; }
  .addr-row-major { padding-left: 32px; }
  .addr-row-class { padding-left: 48px; }
  .addr-row-student { padding-left: 60px; }
  .addr-row-major::before, .addr-row-major::after { left: 20px; }
  .addr-row-class::before, .addr-row-class::after { left: 36px; }
  .addr-row-student::before, .addr-row-student::after { left: 48px; }

  .file-item { gap: 10px; padding: 10px; border-radius: 10px; }
  .file-thumb { width: 38px; height: 38px; }
  .file-name { font-size: 13.5px; }

  .notif-row { gap: 12px; min-height: 56px; padding: 12px 16px; }
  .notif-icon { width: 36px; height: 36px; }
  .notif-main { gap: 4px; }
  .notif-title { font-size: 15px; }
  .notif-content { font-size: 12.5px; }
}
</style>