<template>
  <div class="profile-wrapper" :class="{ 'is-web': !isMobile }">
    <!-- ===== 移动端主页面：封面头部（身份悬浮于背景之上）+ 分组菜单（桌面端改由左侧导航承担） ===== -->
    <transition v-if="isMobile" :name="slideDirection">
      <div v-if="!currentPage" key="main" class="profile-page"
        @touchstart.passive="pull.onStart"
        @touchmove="pull.onMove"
        @touchend="pull.onEnd"
        @touchcancel="pull.onCancel">
        <!-- 移动端下拉刷新：本页无吸顶头，指示器置于封面之前 -->
        <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />
        <!-- 个人中心头部：抖音范式封面 —— 顶部悬浮操作、头像压住封面下边缘、姓名与工号贴在封面右下 -->
        <section class="pf-hero" :class="{ 'is-photo': !!bannerUrl }" :style="heroBannerStyle" @click="openPage('banner')">
          <div class="pf-hero-scrim"></div>

          <div class="pf-hero-top">
            <button type="button" class="pf-top-pill" @click.stop="openPage('banner')">
              <el-icon :size="13"><Camera /></el-icon>
              更换背景
            </button>
            <span class="pf-top-icons">
              <button type="button" class="pf-top-icon" title="校园公告" @click.stop="openPage('announcements')">
                <el-icon :size="16"><Bell /></el-icon>
              </button>
            </span>
          </div>

          <div class="pf-hero-id">
            <div class="pf-hero-id-row">
              <h2 class="pf-cast-name">{{ auth.userName }}</h2>
              <span class="pf-cast-role">教师</span>
              <span v-if="badgeWall" class="pf-lv-chip">Lv.{{ badgeWall.level.level }}</span>
            </div>
            <p class="pf-cast-sub">工号：{{ auth.user?.username || '—' }}</p>
          </div>

          <!-- 头像压住封面与内容区的交界线；右下角「+」即编辑资料入口 -->
          <button type="button" class="pf-hero-avatar" title="编辑资料" @click.stop="openPage('profile')">
            <el-avatar :size="82" :src="auth.user?.avatar || ''" class="pf-avatar">
              {{ auth.userName?.[0] }}
            </el-avatar>
            <span class="pf-avatar-edit"><el-icon :size="13"><Plus /></el-icon></span>
          </button>
        </section>

        <!-- 内容面板：圆角上浮压住封面底边，形成「悬浮于背景之上」的层次 -->
        <div class="pf-body">
          <!-- 数据行：四项数据 + 编辑资料（对应参考图中的「获赞 / 互关 / 关注 / 粉丝 + 编辑主页」） -->
          <div class="pf-profile-top">
            <!-- 勋章条：贴在头像右侧的留白里（QQ 资料卡的等级 + 勋章串），用图标填空而不是留空 -->
            <div v-if="badgeWall" class="pf-badge-strip">
              <span class="pf-badge-strip-icons">
                <button
                  v-for="b in earnedBadgePreview"
                  :key="b.code"
                  type="button"
                  class="pf-badge-mini"
                  :title="b.name"
                  @click="badgeDetail = b"
                >
                  <BadgeMedal :icon="b.icon" :tier="b.tier" :size="22" :ribbon="false" />
                </button>
                <span v-if="badgeWall.earned.length > earnedBadgePreview.length" class="pf-badge-more">
                  +{{ badgeWall.earned.length - earnedBadgePreview.length }}
                </span>
                <span v-if="!earnedBadgePreview.length" class="pf-badge-empty">还没有点亮勋章</span>
              </span>
              <button type="button" class="pf-badge-pill" @click="openPage('badges')">
                勋章 {{ badgeWall.earned.length }} 枚
                <el-icon :size="11"><ArrowRight /></el-icon>
              </button>
            </div>

            <div class="pf-stat-row">
              <div v-if="completionLoading" class="pf-stat-skeleton"><span></span><span></span><span></span></div>
              <template v-else>
                <div v-for="m in completionMetrics" :key="m.key" class="pf-stat" :title="m.hint">
                  <b :class="m.tone ? 'is-' + m.tone : ''">{{ m.value }}<i v-if="m.unit">{{ m.unit }}</i></b>
                  <span>{{ m.title }}</span>
                </div>
              </template>
              <button type="button" class="pf-edit-btn" @click="openPage('profile')">编辑资料</button>
            </div>

            <button type="button" class="pf-bio" :class="{ 'is-empty': !auth.user?.signature }" @click="openPage('profile')">
              {{ auth.user?.signature || '还没有个性签名，点这里填写' }}
            </button>

            <div class="pf-tags">
              <span v-if="auth.user?.college" class="pf-tag">{{ auth.user.college }}</span>
              <span class="pf-tag">所带班级 {{ profileForm.className || '未设置' }}</span>
              <span class="pf-tag">资料完整度 {{ profileCompletion }}%</span>
            </div>

            <!-- 快捷入口行：一屏固定 5 个，其余左右滑查看（勋章已移到头像右侧的勋章条） -->
            <nav class="pf-quick">
              <div class="pf-quick-track">
                <button type="button" class="pf-quick-item" @click="openPage('profile')">
                  <span class="pf-quick-icon"><el-icon :size="21"><User /></el-icon></span>
                  <span class="pf-quick-label">我的资料</span>
                </button>
                <button type="button" class="pf-quick-item" @click="openPage('announcements')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Bell /></el-icon></span>
                  <span class="pf-quick-label">校园公告</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/teacher/tasks')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Calendar /></el-icon></span>
                  <span class="pf-quick-label">待办任务</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/teacher/approval')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Tickets /></el-icon></span>
                  <span class="pf-quick-label">请假审批</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/teacher/crisis')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Warning /></el-icon></span>
                  <span class="pf-quick-label">学生预警</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/teacher/guardian')">
                  <span class="pf-quick-icon"><el-icon :size="21"><ChatDotRound /></el-icon></span>
                  <span class="pf-quick-label">家校沟通</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/teacher/survey')">
                  <span class="pf-quick-icon"><el-icon :size="21"><EditPen /></el-icon></span>
                  <span class="pf-quick-label">匿名互评</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/teacher/portfolio')">
                  <span class="pf-quick-icon"><el-icon :size="21"><FolderOpened /></el-icon></span>
                  <span class="pf-quick-label">成长档案</span>
                </button>
                <button type="button" class="pf-quick-item" @click="openPage('theme')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Sunny /></el-icon></span>
                  <span class="pf-quick-label">主题设置</span>
                </button>
                <button type="button" class="pf-quick-item" @click="openPage('help')">
                  <span class="pf-quick-icon"><el-icon :size="21"><QuestionFilled /></el-icon></span>
                  <span class="pf-quick-label">使用帮助</span>
                </button>
              </div>
            </nav>
          </div>

          <!-- 设置与隐私 -->
          <h3 class="pf-section-title">设置与隐私</h3>
          <section class="pf-section">
            <div class="pf-list">
              <button type="button" class="pf-row" @click="openPage('password')">
                <span class="pf-row-icon is-violet"><el-icon :size="17"><Lock /></el-icon></span>
                <span class="pf-row-label">修改密码</span>
                <span class="pf-row-hint">定期更换更安全</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="pf-row" @click="openPage('about')">
                <span class="pf-row-icon"><el-icon :size="17"><InfoFilled /></el-icon></span>
                <span class="pf-row-label">关于{{ agentName }}</span>
                <span class="pf-row-hint">v1.0.0</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="pf-row" @click="logout">
                <span class="pf-row-icon is-danger"><el-icon :size="17"><SwitchButton /></el-icon></span>
                <span class="pf-row-label">退出登录</span>
                <span class="pf-row-hint">工号 {{ auth.user?.username || '—' }}</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </section>

          <p class="pf-foot-note">{{ agentName }} · 智慧校园服务平台 v1.0.0</p>
        </div>
      </div>
    </transition>

    <!-- ===== 桌面端身份信息条：朴素白卡（网页端不做封面图 / 渐变遮罩） =====
         左侧圆形头像（点按进「账号与安全」）+ 中间姓名身份与工号/学院/职称/所带班级键值对平铺
         + 一行灰色个性签名，最右侧「编辑资料」；仅靠发丝边框与极轻阴影分层。 -->
    <section v-if="!isMobile" class="pf-head">
      <button type="button" class="pf-head-avatar-btn" @click="openPage('profile')">
        <el-avatar :size="60" :src="auth.user?.avatar || ''" class="pf-head-avatar">
          {{ auth.userName?.[0] }}
        </el-avatar>
      </button>

      <div class="pf-head-main">
        <div class="pf-head-name-row">
          <h2 class="pf-head-name">{{ auth.userName }}</h2>
          <span class="tui-chip tui-chip-brand">教师</span>
        </div>
        <div class="pf-head-facts">
          <span class="pf-head-fact"><i>工号</i><b>{{ auth.user?.username || '—' }}</b></span>
          <span class="pf-head-fact"><i>学院</i><b>{{ auth.user?.college || '未设置学院' }}</b></span>
          <span class="pf-head-fact"><i>职称</i><b>{{ profileForm.title || '未设置职称' }}</b></span>
          <span class="pf-head-fact"><i>所带班级</i><b>{{ profileForm.className || '—' }}</b></span>
        </div>
        <button
          type="button"
          class="pf-head-signature"
          :class="{ 'is-empty': !auth.user?.signature }"
          @click="openPage('profile')"
        >
          {{ auth.user?.signature || '未设置签名，点此去填写' }}
        </button>
      </div>

      <el-button class="pf-head-edit" @click="openPage('profile')">编辑资料</el-button>
    </section>

    <!-- ===== 桌面端主体：左侧导航 + 右侧内容 =====
           .profile-body 不参与两端分支判断：它只做桌面端的行容器，
           移动端以 display:contents 退化为「无盒子」，子元素仍按原样定位。 -->
    <div class="profile-body">
      <aside v-if="!isMobile" class="profile-side">
        <nav v-for="g in desktopMenuGroups" :key="g.title" class="side-group">
          <div class="side-group-title">{{ g.title }}</div>
          <button
            v-for="m in g.items"
            :key="m.key"
            type="button"
            class="side-item"
            :class="{ active: activeTab === m.key }"
            @click="currentPage = m.key"
          >
            <el-icon :size="16"><component :is="m.icon" /></el-icon>
            <span class="side-item-label">{{ m.label }}</span>
          </button>
        </nav>

        <button type="button" class="side-item side-item-danger" @click="logout">
          <el-icon :size="16"><SwitchButton /></el-icon>
          <span class="side-item-label">退出登录</span>
        </button>
      </aside>

      <!-- ===== 内容区：移动端走整页切换，桌面端常驻右侧内容栏 ===== -->
      <transition :name="isMobile ? slideDirection : ''">
      <div v-if="activeTab" :key="activeTab" :class="isMobile ? 'sub-page' : 'profile-main'">
        <!-- 移动端子页返回栏（桌面端由左侧导航承担切换） -->
        <div v-if="isMobile" class="sub-page-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="sub-page-title">{{ pageTitle }}</div>
          <div class="sub-page-placeholder"></div>
        </div>
        <div v-else class="web-head">
          <h2 class="web-head-title">{{ pageTitle }}</h2>
          <p class="web-head-sub">{{ pageSubtitle }}</p>
        </div>

        <!-- 数据概览（桌面端整页默认内容区）：我的完成度 + 所带学生综合情况 -->
        <div v-if="activeTab === 'overview'" class="sub-page-content pf-overview">
          <section class="tui-section">
            <div class="tui-section-head">
              <h3><el-icon><DataAnalysis /></el-icon>我的完成度</h3>
            </div>
            <div v-if="completionLoading" class="pf-skeleton">
              <span v-for="i in 2" :key="i" class="pf-skeleton-bar"></span>
            </div>
            <div v-else-if="!hasCompletionData" class="pf-inline-empty">暂无可展示的完成度数据</div>
            <!-- 桌面端完成度：一行 4 个指标卡（数字 + 一句 hint），比例改用细进度条，去掉环形装饰 -->
            <div v-else class="pf-kpi-row">
              <article v-for="m in completionMetrics" :key="m.key" class="pf-kpi">
                <span class="pf-kpi-label">{{ m.title }}</span>
                <span class="pf-kpi-num" :class="m.tone ? 'is-' + m.tone : ''">{{ m.value }}<i v-if="m.unit">{{ m.unit }}</i></span>
                <span class="pf-kpi-hint">{{ m.hint }}</span>
                <span v-if="m.pct !== null" class="tui-progress pf-kpi-progress">
                  <span class="tui-progress-track">
                    <span
                      class="tui-progress-fill"
                      :class="m.tone ? 'is-' + m.tone : ''"
                      :style="{ '--pct': m.pct }"
                    ></span>
                  </span>
                  <span class="tui-progress-text">{{ pctText(m.pct) }}</span>
                </span>
              </article>
            </div>
          </section>

          <section class="tui-section">
            <div class="tui-section-head">
              <h3><el-icon><UserFilled /></el-icon>所带学生综合情况</h3>
            </div>
            <div v-if="studentsLoading" class="pf-skeleton">
              <span v-for="i in 3" :key="i" class="pf-skeleton-bar"></span>
            </div>
            <template v-else-if="hasStudentData">
              <div v-if="dashboardStats" class="pf-stats">
                <div v-for="s in studentStatCards" :key="s.label" class="tui-stat">
                  <span class="tui-stat-num" :class="s.tone ? 'is-' + s.tone : ''">{{ s.value }}</span>
                  <span class="tui-stat-label">{{ s.label }}</span>
                </div>
              </div>
              <div v-if="hasClassCharts" class="pf-charts">
                <div class="pf-chart">
                  <div class="pf-chart-title">危机等级分布</div>
                  <div class="pf-chart-body">
                    <VChart v-if="crisisPieOptions" :option="crisisPieOptions" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="54" />
                  </div>
                </div>
                <div class="pf-chart">
                  <div class="pf-chart-title">成绩分布</div>
                  <div class="pf-chart-body">
                    <VChart v-if="gradeBarOptions" :option="gradeBarOptions" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="54" />
                  </div>
                </div>
                <div class="pf-chart">
                  <div class="pf-chart-title">近 6 个月预警趋势</div>
                  <div class="pf-chart-body">
                    <VChart v-if="crisisTrendOptions" :option="crisisTrendOptions" autoresize />
                    <el-empty v-else description="暂无数据" :image-size="54" />
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="pf-inline-empty">暂无学生数据</div>
          </section>
        </div>

        <!-- 账号与安全（抖音设置页范式）：只读展示 + 点按行弹窗编辑，不再铺一屏输入框 -->
        <div v-if="activeTab === 'profile'" class="sub-page-content set-page">
          <!-- 头像：编辑资料页里的头等行——大圆头像 + 相机角标，一眼知道能点 -->
          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row set-row-ava" @click="triggerAvatarInput">
                <span class="set-row-label">头像</span>
                <span class="set-row-value">
                  <span class="pf-ava-wrap">
                    <el-avatar :size="46" :src="profileForm.avatar" class="pf-ava">
                      {{ profileForm.name?.[0] || '?' }}
                    </el-avatar>
                    <span class="pf-ava-cam"><el-icon :size="10"><Camera /></el-icon></span>
                  </span>
                </span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
            <input ref="avatarInputRef" type="file" accept="image/*" style="display:none" @change="onAvatarSelect" />
          </div>

          <div v-for="g in accGroups" :key="g.title" class="set-group">
            <div class="set-group-title">{{ g.title }}</div>
            <div class="set-list">
              <button
                v-for="f in g.fields"
                :key="f.key"
                type="button"
                class="set-row"
                :class="{ 'is-readonly': f.readonly }"
                @click="openFieldEdit(f)"
              >
                <span class="set-row-label">{{ f.label }}</span>
                <span class="set-row-value" :class="{ 'is-empty': !fieldValue(f) }">
                  {{ fieldValue(f) || (f.readonly ? '—' : '未设置') }}
                </span>
                <el-icon v-if="!f.readonly" class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <div class="sub-page-footer">
            <el-button type="primary" class="footer-btn" @click="handleSaveProfile" :loading="saving">保存</el-button>
          </div>
        </div>

        <!-- 我的勋章：完整勋章墙（等级 + 已获得 + 待解锁进度） -->
        <div v-if="activeTab === 'badges'" class="sub-page-content">
          <BadgeWall
            v-if="badgeWall"
            :earned="badgeWall.earned"
            :locked="badgeWall.locked"
            :level="badgeWall.level"
          />
          <div v-else class="badge-placeholder">勋章数据加载中…</div>
        </div>

        <!-- 修改密码：参考 GitHub / Telegram 的安全设置页，单卡片表单 + 强度提示 -->
        <div v-if="activeTab === 'password'" class="sub-page-content sp-page">
          <div class="sp-card">
            <div class="sp-head">
              <h3 class="sp-title">修改登录密码</h3>
              <p class="sp-desc">建议每 3 个月更换一次，使用 6-20 位字母与数字组合，修改后需重新登录。</p>
            </div>

            <div class="sp-field">
              <span class="sp-label">旧密码</span>
              <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入当前密码" />
            </div>

            <div class="sp-field">
              <span class="sp-label">新密码</span>
              <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="6-20 位字母 / 数字组合" />
              <span v-if="passwordForm.new_password" class="sp-meter">
                <i v-for="n in 3" :key="n" class="sp-meter-bar" :class="{ 'is-on': passwordStrength >= n }"></i>
                <em class="sp-meter-text">强度 {{ passwordStrengthText }}</em>
              </span>
            </div>

            <div class="sp-field">
              <span class="sp-label">确认新密码</span>
              <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
              <span v-if="passwordMismatch" class="sp-error">两次输入的新密码不一致</span>
            </div>

            <div class="sp-field">
              <span class="sp-label">图形验证码</span>
              <span class="sp-captcha">
                <el-input v-model="passwordForm.captcha" placeholder="输入右侧 4 位字符" maxlength="4" />
                <button type="button" class="sp-captcha-code" @click="refreshCaptcha">{{ captchaCode }}</button>
              </span>
            </div>
          </div>

          <button type="button" class="sp-submit" :disabled="changingPassword" @click="handleChangePassword">
            {{ changingPassword ? '正在保存…' : '保存新密码' }}
          </button>
        </div>

        <!-- 校园公告：单条独立卡片，点击在站内阅读（与学生端资讯页同一套阅读器） -->
        <div v-if="activeTab === 'announcements'" class="sub-page-content set-page">
          <div v-loading="loadingAnnouncements" class="ann-cards">
            <button
              v-for="(item, index) in announcements"
              :key="'a' + index"
              type="button"
              class="ann-card"
              @click="openAnnouncement(item)"
            >
              <span class="ann-card-date">{{ item.date }}</span>
              <span class="ann-card-title">{{ stripAnnPrefix(item.title) }}</span>
              <span class="ann-card-foot">
                校园公告
                <el-icon :size="13"><ArrowRight /></el-icon>
              </span>
            </button>
            <p v-if="announcements.length === 0 && !loadingAnnouncements" class="ann-empty">暂无校园公告</p>
          </div>
          <ArticleReader ref="articleReader" />
        </div>

        <!-- 使用帮助 -->
        <div v-if="activeTab === 'help'" class="sub-page-content">
          <div class="help-content">
            <div class="help-item">
              <div class="help-question">如何联系{{ agentName }}？</div>
              <div class="help-answer">在首页直接输入你的问题，{{ agentName }}会即时回复。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看学生档案？</div>
              <div class="help-answer">输入"查学生档案"，即可查看所带班级学生的详细信息。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何审批请假？</div>
              <div class="help-answer">输入"审批请假"，即可查看和处理学生的请假申请。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看班级数据？</div>
              <div class="help-answer">输入"查班级数据"，即可获取班级考勤、成绩等统计数据。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看消息？</div>
              <div class="help-answer">输入"查消息"即可获取最新的系统通知和公告。</div>
            </div>
          </div>
        </div>

        <!-- 主题设置（仅浅色模式提示） -->
        <div v-if="activeTab === 'theme'" class="sub-page-content">
          <div class="theme-options">
            <div class="theme-option active">
              <div class="theme-preview light-preview"></div>
              <span>浅色模式</span>
            </div>
          </div>
          <div class="theme-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>当前系统仅支持浅色模式</span>
          </div>
        </div>

        <!-- 关于绵小城 -->
        <div v-if="activeTab === 'about'" class="sub-page-content">
          <!-- 头部信息 -->
          <div class="about-header">
            <img :src="siteLogo" class="about-logo" />
            <div class="about-name">{{ siteName }}</div>
            <div class="about-version">v1.0.0</div>
            <div class="about-slogan">你的校园智能管家</div>
          </div>

          <!-- 功能简介 -->
          <div class="about-section">
            <div class="about-section-title">功能简介</div>
            <div class="about-text">
              {{ agentName }}是绵阳城市学院官方推出的智慧校园AI助手，基于大语言模型技术，为全校师生提供智能化的校园服务。通过自然语言对话，您可以轻松完成课表查询、成绩查询、请假审批、校园通知查看等日常事务，让校园管理更加便捷高效。
            </div>
          </div>

          <!-- 项目简介 -->
          <div class="about-section">
            <div class="about-section-title">项目简介</div>
            <div class="about-text">
              本项目采用前后端分离架构，前端使用 Vue 3 + TypeScript + Element Plus 构建，后端基于 FastAPI + Python 实现，集成大语言模型 API 提供智能对话能力。项目支持学生端和教师端，涵盖智能对话、办事服务、学生成长档案、校园风采等多个功能模块，致力于打造全方位的智慧校园生态。
            </div>
          </div>

          <!-- 核心功能 -->
          <div class="about-section">
            <div class="about-section-title">核心功能</div>
            <div class="about-features">
              <div class="feature-item">智能对话</div>
              <div class="feature-item">课表查询</div>
              <div class="feature-item">成绩查询</div>
              <div class="feature-item">请假审批</div>
              <div class="feature-item">学生档案</div>
              <div class="feature-item">校园通知</div>
              <div class="feature-item">班级管理</div>
              <div class="feature-item">办事服务</div>
            </div>
          </div>

          <!-- 开发团队 -->
          <div class="about-section">
            <div class="about-section-title">开发团队</div>
            <div class="about-team">
              <div class="team-info">
                <div class="team-name">阿里跳动</div>
                <div class="team-desc">由两位绵阳城市学院校内学生自主开发，致力于用技术创新提升校园数字化服务水平。</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 更换背景（抖音背景选择器范式）：顶部实时预览 + 背景宫格，点选即时生效 -->
        <div v-if="activeTab === 'banner'" class="sub-page-content set-page">
          <div class="set-group">
            <div class="set-group-title">当前背景</div>
            <div class="bg-preview" :class="{ 'is-photo': !!bannerUrl }" :style="heroBannerStyle">
              <div class="bg-preview-scrim"></div>
              <div class="bg-preview-cast">
                <el-avatar :size="40" :src="auth.user?.avatar || ''" class="bg-preview-avatar">
                  {{ auth.userName?.[0] }}
                </el-avatar>
                <div>
                  <div class="bg-preview-name">{{ auth.userName }}</div>
                  <div class="bg-preview-sub">工号：{{ auth.user?.username || '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="set-group">
            <div class="set-group-title">选择背景</div>
            <div class="bg-grid">
              <button
                v-for="preset in presetBanners"
                :key="preset.id"
                type="button"
                class="bg-cell"
                :class="{ 'is-active': !bannerUrl && bannerGradient === preset.color }"
                :style="{ background: preset.color }"
                @click="selectPresetBanner(preset.color)"
              >
                <span v-if="!bannerUrl && bannerGradient === preset.color" class="bg-cell-check">
                  <el-icon :size="11"><Check /></el-icon>
                </span>
              </button>
              <button type="button" class="bg-cell bg-cell-upload" @click="triggerBannerUpload">
                <el-icon :size="18"><Plus /></el-icon>
                <span>从相册选择</span>
              </button>
            </div>
            <p class="bg-hint">自定义背景支持 JPG / PNG，最大 5MB</p>
          </div>

          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="resetBanner">
                <span class="set-row-label">恢复默认背景</span>
                <span class="set-row-value">使用系统预设渐变</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <input ref="bannerInputRef" type="file" accept="image/*" style="display:none" @change="handleBannerUpload" />
        </div>
      </div>
    </transition>
    </div>

    <!-- 账号与安全：字段编辑弹窗（抖音「点按设置项 → 就地编辑」范式） -->
    <!-- 字段编辑（单字段：移动端=底部动作面板） -->
    <ActionSheet
      v-model="editVisible"
      :title="editField ? `修改${editField.label}` : ''"
      width="420px"
    >
      <el-input
        v-if="editField && editField.type === 'text'"
        v-model="editValue"
        :placeholder="editField.placeholder || '请输入'"
        clearable
      />
      <el-input-number
        v-else-if="editField && editField.type === 'number'"
        v-model="editValue"
        :min="1"
        :max="120"
        style="width:100%"
      />
      <el-select v-else v-model="editValue" placeholder="请选择" style="width:100%">
        <el-option v-for="o in editField?.options || []" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmFieldEdit">确定</el-button>
      </template>
    </ActionSheet>

    <!-- 勋章放大查看 -->
    <BadgeDetail :badge="badgeDetail" @close="badgeDetail = null" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
// v6.1 弹窗减负：单字段编辑走底部动作面板
import ActionSheet from '@/components/common/ActionSheet.vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, changePassword } from '@/api/user'
import { uploadFile } from '@/api/upload'
import { getAnnouncements } from '@/api/campus'
import type { Announcement } from '@/types'
import ArticleReader from '@/components/campus/ArticleReader.vue'
import { getMyBadgeWall, type BadgeItem, type BadgeWall as BadgeWallData } from '@/api/badge'
import { syncQuickAccount } from '@/utils/quickLogin'
import { confirmLogout } from '@/utils/logout'
import { getDashboardStats, getClassStats, type DashboardStats, type ClassStats, type ClassEvaluation } from '@/api/teacher'
import { getTeacherTaskSummary, type TeacherTaskSummary } from '@/api/teacherTask'
import { getApprovalStats, type ApprovalStats } from '@/api/approval'
import { getWorkloadStats, type WorkloadStats } from '@/api/careRecord'
import { getPortfolioReport, type PortfolioReport } from '@/api/teacherPortfolio'
import { useClassCharts } from '@/composables/useClassCharts'
import VChart from 'vue-echarts'
import BadgeWall from '@/components/profile/BadgeWall.vue'
import BadgeMedal from '@/components/profile/BadgeMedal.vue'
import BadgeDetail from '@/components/profile/BadgeDetail.vue'
import { syncBadgeAwards } from '@/composables/useBadgeAward'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useResponsive } from '@/composables/useResponsive'
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import {
  ArrowRight, ArrowLeft, Lock, SwitchButton, Sunny, InfoFilled,
  QuestionFilled, Bell, Camera, User, Check, Plus, Medal,
  DataAnalysis, UserFilled, Calendar, Tickets, Warning, ChatDotRound, EditPen, FolderOpened
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()
const { isMobile } = useResponsive()

/** 移动端下拉刷新：重载教师画像统计与勋章墙（桌面端不响应手势） */
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

// 关于页品牌信息与站点配置同源
const { siteName, siteLogo, agentName } = useSiteConfig()

// 页面状态
const currentPage = ref<string | null>(null)

// 移动端个人中心的各设置子页：打开时让出底部悬浮导航
useMobileSubPage(computed(() => isMobile.value && !!currentPage.value))
const slideDirection = ref('slide-left')

// 表单状态
const saving = ref(false)
const changingPassword = ref(false)
const uploadingBanner = ref(false)

// 勋章墙（等级 / 已获得 / 待解锁进度）
const badgeWall = ref<BadgeWallData | null>(null)
/** 点击勋章条上的小勋章 → 放大查看 */
const badgeDetail = ref<BadgeItem | null>(null)

/** 勋章条只陈列前 4 枚已点亮勋章（再多会挤掉右侧入口），其余用 +N 提示 */
const earnedBadgePreview = computed(() => (badgeWall.value?.earned ?? []).slice(0, 4))

/**
 * 结算 + 拉取勋章墙：先让后端按最新使用数据结算（可能解锁新勋章，由布局层的
 * 奖励动画队列播放），再取回完整勋章墙；顺序颠倒会导致新勋章缺席。
 */
async function refreshBadges() {
  try {
    await syncBadgeAwards()
    badgeWall.value = await getMyBadgeWall()
  } catch { /* 拉取失败保持原样 */ }
}

// 背景图
const savedBanner = localStorage.getItem('profileBanner') || ''
const bannerUrl = ref(savedBanner ? savedBanner + (savedBanner.includes('?') ? '&' : '?') + '_t=' + Date.now() : '')
const bannerInputRef = ref<HTMLInputElement>()
const DEFAULT_GRADIENT =
  'radial-gradient(circle at 84% 14%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 10% 86%, rgba(129,161,255,0.28) 0%, rgba(129,161,255,0) 44%), linear-gradient(135deg, #eef4ff 0%, #d8e5ff 100%)'

/**
 * 预设背景：浅色底 + 少量柔光圆点修饰。
 * 每项为多层 background：先铺两处柔光（白色高光 + 一抹同色系淡彩），再叠浅色渐变。
 * 因底色为浅色，封面文字改用深色（自定义背景图仍走深色压底 + 白字）。
 */
const presetBanners = [
  { id: 'gradient1', color: 'radial-gradient(circle at 84% 14%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 10% 86%, rgba(129,161,255,0.28) 0%, rgba(129,161,255,0) 44%), linear-gradient(135deg, #eef4ff 0%, #d8e5ff 100%)' },
  { id: 'gradient2', color: 'radial-gradient(circle at 80% 18%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 14% 84%, rgba(52,211,153,0.22) 0%, rgba(52,211,153,0) 44%), linear-gradient(135deg, #eefaf3 0%, #d5f2e3 100%)' },
  { id: 'gradient3', color: 'radial-gradient(circle at 82% 16%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 12% 86%, rgba(244,114,182,0.20) 0%, rgba(244,114,182,0) 44%), linear-gradient(135deg, #fff1f5 0%, #ffdfe9 100%)' },
  { id: 'gradient4', color: 'radial-gradient(circle at 80% 16%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 14% 86%, rgba(251,191,36,0.20) 0%, rgba(251,191,36,0) 44%), linear-gradient(135deg, #fff7ec 0%, #ffe8cc 100%)' },
  { id: 'gradient5', color: 'radial-gradient(circle at 82% 18%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 12% 84%, rgba(167,139,250,0.22) 0%, rgba(167,139,250,0) 44%), linear-gradient(135deg, #f6f2ff 0%, #e6dfff 100%)' },
  { id: 'gradient6', color: 'radial-gradient(circle at 80% 16%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 40%), radial-gradient(circle at 14% 86%, rgba(148,163,184,0.22) 0%, rgba(148,163,184,0) 44%), linear-gradient(135deg, #f3f6fa 0%, #e2e9f1 100%)' },
]

// 旧的深色渐变已下线：存量值不在预设列表内时回落到默认浅色背景
const presetColors = presetBanners.map((p) => p.color)
const savedGradient = localStorage.getItem('profileBannerColor') || ''
const bannerGradient = ref(presetColors.includes(savedGradient) ? savedGradient : DEFAULT_GRADIENT)

const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '', captcha: '' })
const captchaCode = ref('')

function generateCaptcha() {
  const chars = '0123456789'
  let result = ''
  for (let i = 0; i < 4; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

function refreshCaptcha() {
  captchaCode.value = generateCaptcha()
}

/** 新密码强度：长度、字母数字组合、符号各计一档，最多 3 档 */
const passwordStrength = computed(() => {
  const p = passwordForm.new_password
  if (!p) return 0
  let score = 0
  if (p.length >= 6) score++
  if (p.length >= 10 || (/[a-zA-Z]/.test(p) && /\d/.test(p))) score++
  if (p.length >= 10 && /[a-zA-Z]/.test(p) && /\d/.test(p)) score++
  return Math.min(3, score)
})
const passwordStrengthText = computed(() => ['弱', '一般', '较强', '很强'][passwordStrength.value])
const passwordMismatch = computed(() =>
  !!passwordForm.confirm_password && passwordForm.confirm_password !== passwordForm.new_password
)

const profileForm = reactive({
  username: '', name: '', college: '', gender: '', age: 18,
  hometown: '', phone: '', qq: '', className: '', political_status: '',
  title: '', department: '', avatar: '', signature: ''
})

/** 头像行：点按触发文件选择，选好后上传并暂存，点击保存后正式生效 */
const avatarInputRef = ref<HTMLInputElement>()
function triggerAvatarInput() {
  avatarInputRef.value?.click()
}

async function onAvatarSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 5MB')
    input.value = ''
    return
  }
  try {
    const { url } = await uploadFile(file)
    profileForm.avatar = url
    ElMessage.success('头像已更新，点击保存后生效')
  } catch {
    ElMessage.error('上传失败')
  } finally {
    input.value = ''
  }
}

/**
 * 账号与安全：字段描述表（抖音设置项范式）。
 * 页面只读展示「左侧标签 + 右侧值 + 箭头」，点按行弹出编辑弹窗，
 * 避免把 8 个输入框一次性铺在页面上。
 */
interface AccField {
  key: string
  label: string
  type: 'text' | 'select' | 'number'
  options?: { label: string; value: string }[]
  placeholder?: string
  readonly?: boolean
}

const accGroups: { title: string; fields: AccField[] }[] = [
  {
    title: '账号信息',
    fields: [
      { key: 'username', label: '工号', type: 'text', readonly: true },
      { key: 'name', label: '姓名', type: 'text', readonly: true },
      { key: 'college', label: '学院', type: 'text', readonly: true },
      { key: 'className', label: '所带班级', type: 'text', placeholder: '请输入所带班级' },
    ],
  },
  {
    title: '个人资料',
    fields: [
      { key: 'signature', label: '个性签名', type: 'text', placeholder: '一句话介绍自己，展示在个人主页' },
      {
        key: 'gender', label: '性别', type: 'select',
        options: [{ label: '男', value: '男' }, { label: '女', value: '女' }],
      },
      { key: 'age', label: '年龄', type: 'number' },
      { key: 'hometown', label: '籍贯', type: 'text', placeholder: '请输入籍贯' },
      {
        key: 'political_status', label: '政治面貌', type: 'select',
        options: [
          { label: '群众', value: '群众' },
          { label: '共青团员', value: '共青团员' },
          { label: '中共预备党员', value: '中共预备党员' },
          { label: '中共党员', value: '中共党员' },
        ],
      },
    ],
  },
  {
    title: '联系方式',
    fields: [
      { key: 'phone', label: '联系电话', type: 'text', placeholder: '绑定后可用手机号一键登录' },
      { key: 'qq', label: 'QQ', type: 'text', placeholder: '绑定后可用 QQ 一键登录' },
      { key: 'title', label: '职称', type: 'text', placeholder: '请输入职称' },
      { key: 'department', label: '所属单位', type: 'text', placeholder: '请输入所属单位' },
    ],
  },
]

const editVisible = ref(false)
const editField = ref<AccField | null>(null)
const editValue = ref<any>('')

/** 行右侧展示的文本：下拉项显示选项文案，空值由模板回退为占位文案 */
function fieldValue(f: AccField): string {
  const v = (profileForm as any)[f.key]
  if (v === null || v === undefined || v === '') return ''
  if (f.type === 'select') return f.options?.find((o) => o.value === v)?.label || String(v)
  return String(v)
}

function openFieldEdit(f: AccField) {
  if (f.readonly) return
  editField.value = f
  editValue.value = (profileForm as any)[f.key] ?? ''
  editVisible.value = true
}

function confirmFieldEdit() {
  const f = editField.value
  if (!f) return
  ;(profileForm as any)[f.key] = f.type === 'number' ? Number(editValue.value) || 1 : editValue.value
  editVisible.value = false
}

// 校园公告
const announcements = ref<Announcement[]>([])
const loadingAnnouncements = ref(false)
const articleReader = ref<InstanceType<typeof ArticleReader> | null>(null)

/** 去掉多篇公告共有的「关于…的通知」式前缀，标题更易扫读 */
function stripAnnPrefix(title: string) {
  return title
    .replace(/^关于印发/g, '')
    .replace(/^关于/g, '')
    .replace(/的通知$/, '')
    .trim() || title
}

function openAnnouncement(item: Announcement) {
  if (!item.url) {
    ElMessage.info('该公告暂未提供正文链接')
    return
  }
  articleReader.value?.open(item.url, item.title)
}

/** 身份背景（移动端 .pf-hero 与桌面端横幅共用）：优先用已上传图片，否则用预设渐变 */
const heroBannerStyle = computed(() =>
  bannerUrl.value ? { backgroundImage: `url(${bannerUrl.value})` } : { background: bannerGradient.value }
)

/** 资料完整度：桌面端身份横幅里的一个轻量进度指标，驱动用户补齐联系方式 */
const profileCompletion = computed(() => {
  const fields = [
    profileForm.className, profileForm.gender, profileForm.hometown,
    profileForm.phone, profileForm.political_status, profileForm.title, profileForm.department,
  ]
  const filled = fields.filter((v) => v !== '' && v !== null && v !== undefined).length
  return Math.round((filled / fields.length) * 100)
})

/** 桌面端当前内容页：未选择时默认落在「数据概览」，把完成度与学生概况放在第一屏 */
const activeTab = computed(() => currentPage.value || (isMobile.value ? '' : 'overview'))

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    overview: '数据概览',
    profile: '账号与安全',
    badges: '我的勋章',
    password: '修改密码',
    announcements: '校园公告',
    help: '使用帮助',
    theme: '主题设置',
    about: `关于${agentName.value}`,
    banner: '更换背景'
  }
  return titles[activeTab.value] || ''
})

/** 桌面端内容区副标题：说明该分组做什么，替代移动端的整页标题感 */
const pageSubtitle = computed(() => {
  const subs: Record<string, string> = {
    overview: '我的完成度与所带学生综合情况速览',
    profile: '管理账号信息与登录安全，保存后即时生效',
    badges: '按平台使用进度与深度解锁的勋章，附成长等级与解锁进度',
    password: '定期更换密码可提升账号安全性',
    banner: '选择预设渐变或上传图片，作为个人中心顶栏背景',
    announcements: '来自学校的通知与公告，点击可在新窗口查看详情',
    help: `关于${agentName.value}的常见用法与快捷指令说明`,
    theme: '当前系统仅支持浅色模式',
    about: '产品信息、技术架构与开发团队',
  }
  return subs[activeTab.value] || ''
})

/**
 * 桌面端左侧菜单：桌面改用语网页端的「左导航 + 右内容」设置页结构，
 * 取代移动端「整页推入 + 返回」的交互；退出登录是动作项，单独渲染在菜单底部。
 */
const desktopMenuGroups = [
  {
    title: '概览',
    items: [
      { key: 'overview', label: '数据概览', icon: DataAnalysis },
    ],
  },
  {
    title: '账号',
    items: [
      { key: 'profile', label: '账号与安全', icon: User },
      { key: 'badges', label: '我的勋章', icon: Medal },
      { key: 'password', label: '修改密码', icon: Lock },
    ],
  },
  {
    title: '帮助与设置',
    items: [
      { key: 'announcements', label: '校园公告', icon: Bell },
      { key: 'help', label: '使用帮助', icon: QuestionFilled },
      { key: 'theme', label: '主题设置', icon: Sunny },
      { key: 'about', label: `关于${agentName.value}`, icon: InfoFilled },
    ],
  },
]

/** 用当前登录用户回填个人资料表单 */
function fillProfileForm() {
  const u = auth.user
  if (!u) return
  profileForm.username = u.username
  profileForm.name = u.name
  profileForm.college = u.college || ''
  profileForm.gender = u.gender || ''
  profileForm.age = u.age ?? 18
  profileForm.hometown = u.hometown || ''
  profileForm.phone = u.phone || ''
  profileForm.qq = u.qq || ''
  profileForm.className = (u as any).class_name || ''
  profileForm.political_status = (u as any).political_status || ''
  profileForm.title = (u as any).title || ''
  profileForm.department = (u as any).department || ''
  profileForm.avatar = (u as any).avatar || ''
  profileForm.signature = (u as any).signature || ''
}

// 打开子页面
function openPage(page: string) {
  if (page === 'profile') fillProfileForm()
  slideDirection.value = 'slide-left'
  currentPage.value = page
}

// 关闭子页面
function closePage() {
  slideDirection.value = 'slide-right'
  currentPage.value = null
}

function selectPresetBanner(color: string) {
  bannerUrl.value = ''
  bannerGradient.value = color
  localStorage.setItem('profileBannerType', 'gradient')
  localStorage.setItem('profileBannerColor', color)
  localStorage.removeItem('profileBanner')
  ElMessage.success('背景已更新')
}

function triggerBannerUpload() {
  bannerInputRef.value?.click()
}

async function handleBannerUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  const file = input.files[0]
  
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过5MB')
    return
  }
  
  uploadingBanner.value = true
  try {
    const { url } = await uploadFile(file)
    const cacheBusted = url + (url.includes('?') ? '&' : '?') + '_t=' + Date.now()
    bannerUrl.value = cacheBusted
    localStorage.setItem('profileBanner', url)
    localStorage.setItem('profileBannerType', 'image')
    localStorage.removeItem('profileBannerColor')
    ElMessage.success('背景已更新')
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploadingBanner.value = false
    input.value = ''
  }
}

function resetBanner() {
  bannerUrl.value = ''
  bannerGradient.value = DEFAULT_GRADIENT
  localStorage.removeItem('profileBanner')
  localStorage.removeItem('profileBannerType')
  localStorage.removeItem('profileBannerColor')
  ElMessage.success('已恢复默认背景')
}

function logout() { confirmLogout() }

async function handleChangePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    ElMessage.warning('请填写所有字段'); return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.error('两次输入的新密码不一致'); return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.error('新密码至少6位'); return
  }
  if (!passwordForm.captcha || passwordForm.captcha !== captchaCode.value) {
    ElMessage.error('验证码错误'); refreshCaptcha(); return
  }
  changingPassword.value = true
  try {
    await changePassword(passwordForm.old_password, passwordForm.new_password)
    ElMessage.success('密码修改成功')
    passwordForm.old_password = ''; passwordForm.new_password = ''; passwordForm.confirm_password = ''
    closePage()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '修改失败') }
  finally { changingPassword.value = false }
}

async function handleSaveProfile() {
  saving.value = true
  try {
    const updated = await updateProfile({
      gender: profileForm.gender || null, age: profileForm.age || null,
      hometown: profileForm.hometown || null, phone: profileForm.phone || null,
      qq: profileForm.qq || null,
      class_name: profileForm.className || null,
      political_status: profileForm.political_status || null,
      title: profileForm.title || null,
      department: profileForm.department || null,
      avatar: profileForm.avatar || null,
      signature: profileForm.signature || null,
    })
    auth.updateUser(updated as any)
    // 绑定/解绑手机号、QQ 后刷新本设备一键登录凭证
    await syncQuickAccount(updated as any)
    ElMessage.success('保存成功')
    closePage()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { saving.value = false }
}

async function loadAnnouncements() {
  loadingAnnouncements.value = true
  try {
    announcements.value = await getAnnouncements()
  } catch {
    announcements.value = []
  } finally {
    loadingAnnouncements.value = false
  }
}

/* =========================================================================
   ===== 数据概览：我的完成度 / 所带学生综合情况 =====
   数据来自多个既有聚合接口，全部并发拉取且各自兜底，任一失败只让对应区块降级。
   ========================================================================= */
const taskSummary = ref<TeacherTaskSummary | null>(null)
const approvalStats = ref<ApprovalStats | null>(null)
const workloadStats = ref<WorkloadStats | null>(null)
const portfolioReport = ref<PortfolioReport | null>(null)
const dashboardStats = ref<DashboardStats | null>(null)

// 班级统计 / 评估：图表配置复用班级分析页的 useClassCharts，先给空骨架避免取数前访问空对象
const classStats = ref<ClassStats>({
  total_students: 0, gender_stats: {}, crisis_stats: {},
  grade_stats: {}, political_stats: {}, hometown_stats: {}, crisis_trend: [],
})
const classEval = ref<ClassEvaluation>({
  total_students: 0, avg_gpa: 0, avg_score: 0, growth: {}, crisis: {}, pending_leaves: 0,
})

const { crisisPieOptions, gradeBarOptions, crisisTrendOptions } = useClassCharts(classStats, classEval)

const completionLoading = ref(true)
const studentsLoading = ref(true)

/** 比例安全计算：分母为 0 时返回 0，避免出现 NaN */
function ratio(numerator: number, denominator: number) {
  return denominator > 0 ? numerator / denominator : 0
}

function pctText(p: number) {
  return `${Math.round(p * 100)}%`
}

interface CompletionMetric {
  key: string
  title: string
  value: string
  unit?: string
  hint: string
  /** 完成度环百分比（0~1）；空心卡（计数型指标）为 null */
  pct: number | null
  tone: string
}

/**
 * 四项完成度：待办推进 / 审批处理 / 关怀工作量 / 育人成果。
 * 数字取该项最有代表性的计数，比例交给右侧完成度环，hint 补足处境信息。
 */
const completionMetrics = computed<CompletionMetric[]>(() => {
  const metrics: CompletionMetric[] = []

  const t = taskSummary.value
  if (t) {
    const done = t.done_this_week ?? 0
    const pending = t.pending ?? 0
    const overdue = t.overdue ?? 0
    const pct = ratio(done, done + pending)
    metrics.push({
      key: 'todo', title: '待办推进', value: String(done), unit: '项',
      hint: `本周办结 ${done} 项 · 待处理 ${pending} 项 · 逾期 ${overdue} 项`,
      pct, tone: pct >= 0.8 ? 'success' : pct >= 0.5 ? '' : 'warn',
    })
  } else {
    metrics.push({ key: 'todo', title: '待办推进', value: '—', hint: '任务数据暂不可用', pct: null, tone: '' })
  }

  const a = approvalStats.value
  if (a) {
    const submitted = a.submitted ?? 0
    const archived = (a.approved_window ?? 0) + (a.rejected_window ?? 0)
    const pending = a.pending ?? 0
    const pct = ratio(archived, submitted)
    metrics.push({
      key: 'approval', title: '审批处理', value: String(archived), unit: '项',
      hint: `近 30 天提交 ${submitted} · 已归档 ${archived} · 待批 ${pending}`,
      pct, tone: pct >= 0.8 ? 'success' : pct >= 0.5 ? '' : 'warn',
    })
  } else {
    metrics.push({ key: 'approval', title: '审批处理', value: '—', hint: '审批数据暂不可用', pct: null, tone: '' })
  }

  const w = workloadStats.value
  if (w) {
    const care = w.care ?? 0
    const talk = w.talk ?? 0
    const comment = w.comment ?? 0
    metrics.push({
      key: 'care', title: '关怀工作量', value: String(w.total ?? care + talk + comment), unit: '条',
      hint: `关怀 ${care} · 谈心 ${talk} · 评语 ${comment}`,
      pct: null, tone: '',
    })
  } else {
    metrics.push({ key: 'care', title: '关怀工作量', value: '—', hint: '关怀记录暂不可用', pct: null, tone: '' })
  }

  const p = portfolioReport.value
  if (p) {
    const total = p.total ?? 0
    metrics.push({
      key: 'portfolio', title: '育人成果', value: String(total), unit: '条',
      hint: `荣誉 / 竞赛 / 实践等共 ${total} 条`,
      pct: null, tone: '',
    })
  } else {
    metrics.push({ key: 'portfolio', title: '育人成果', value: '—', hint: '成长档案暂不可用', pct: null, tone: '' })
  }

  return metrics
})

const hasCompletionData = computed(() =>
  !!(taskSummary.value || approvalStats.value || workloadStats.value || portfolioReport.value)
)

/** 指标行：学生总数 / 预警数 / 高危未闭环 / 已闭环 / 待批请假 */
const studentStatCards = computed(() => {
  const d = dashboardStats.value
  return [
    { label: '学生总数', value: d ? d.total_students : '—', tone: '' },
    { label: '预警数', value: d ? d.alert_count : '—', tone: 'warn' },
    { label: '高危未闭环', value: d ? d.severe_alert_count : '—', tone: 'danger' },
    { label: '已闭环', value: d ? d.resolved_alert_count : '—', tone: 'success' },
    { label: '待批请假', value: d ? d.pending_leave_count : '—', tone: '' },
  ]
})

const hasClassCharts = computed(() =>
  !!(crisisPieOptions.value || gradeBarOptions.value || crisisTrendOptions.value)
)
const hasStudentData = computed(() => !!(dashboardStats.value || hasClassCharts.value))

/** 概览数据并发拉取：单个接口失败只让对应区块降级为空态，不影响资料本身展示 */
async function loadOverviewData() {
  const [task, approval, workload, portfolio, dashboard, stats] = await Promise.all([
    getTeacherTaskSummary().catch(() => null),
    getApprovalStats(30).catch(() => null),
    getWorkloadStats().catch(() => null),
    getPortfolioReport().catch(() => null),
    getDashboardStats().catch(() => null),
    getClassStats().catch(() => null),
  ])
  taskSummary.value = task
  approvalStats.value = approval
  workloadStats.value = workload
  portfolioReport.value = portfolio
  dashboardStats.value = dashboard
  if (stats) classStats.value = stats
  completionLoading.value = false
  studentsLoading.value = false
}

/** 下拉刷新：复用概览统计与勋章墙加载，失败静默 */
async function refreshAll() {
  await Promise.all([loadOverviewData(), refreshBadges()])
}

onMounted(() => {
  refreshCaptcha()
  loadAnnouncements()
  refreshBadges()
  loadOverviewData()
  // 身份名片（移动端与桌面端）都要展示「所带班级 / 资料完整度」，故挂载即回填表单
  fillProfileForm()
})
</script>

<style scoped>
.profile-wrapper {
  position: relative;
  height: 100%;
  overflow: hidden;
}

/* ===== 桌面端：身份信息条 + 左导航 + 右内容的网页设置页布局（无封面 / 无背景图 / 无渐变） ===== */
.profile-wrapper.is-web {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 16px 0;
  background: var(--tui-bg);
  overflow: hidden;
}

/* 移动端：行容器退化为无盒子，子元素（子页）仍相对 .profile-wrapper 定位 */
.profile-body { display: contents; }

/* ===== 身份信息条：白卡 + 发丝边框 + 极轻阴影；头像 / 键值对 / 签名 / 编辑按钮一行读完 ===== */
.profile-wrapper.is-web .pf-head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
}
.profile-wrapper.is-web .pf-head-avatar-btn {
  flex-shrink: 0;
  padding: 0;
  border: none;
  background: none;
  line-height: 0;
  cursor: pointer;
}
.profile-wrapper.is-web .pf-head-avatar {
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-size: 22px;
  font-weight: 600;
}
.profile-wrapper.is-web .pf-head-main { flex: 1; min-width: 0; }
.profile-wrapper.is-web .pf-head-name-row { display: flex; align-items: center; gap: 8px; }
.profile-wrapper.is-web .pf-head-name {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--tui-text);
}
.profile-wrapper.is-web .pf-head-facts {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 18px;
  margin-top: 7px;
}
.profile-wrapper.is-web .pf-head-fact {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  min-width: 0;
}
.profile-wrapper.is-web .pf-head-fact i {
  font-style: normal;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.profile-wrapper.is-web .pf-head-fact b {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--tui-text-secondary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 个性签名：身份条内一行灰色小字，未设置时点按可直接去填写 */
.profile-wrapper.is-web .pf-head-signature {
  display: block;
  max-width: 520px;
  margin-top: 6px;
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 12px;
  color: var(--tui-text-tertiary);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.profile-wrapper.is-web .pf-head-signature:hover { color: var(--tui-brand-strong); }
.profile-wrapper.is-web .pf-head-signature.is-empty { color: var(--tui-text-quiet); font-style: italic; }
.profile-wrapper.is-web .pf-head-edit { flex-shrink: 0; }

/* ===== 桌面端数据概览：完成度一行 4 卡（数字 + 一句 hint + 细进度条，无环形装饰） ===== */
.profile-wrapper.is-web .pf-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.profile-wrapper.is-web .pf-kpi {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
}
.profile-wrapper.is-web .pf-kpi-label { font-size: 12px; color: var(--tui-text-tertiary); }
.profile-wrapper.is-web .pf-kpi-num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.profile-wrapper.is-web .pf-kpi-num i {
  margin-left: 2px;
  font-style: normal;
  font-size: 12px;
  font-weight: 500;
  color: var(--tui-text-quiet);
}
.profile-wrapper.is-web .pf-kpi-num.is-success { color: var(--tui-success); }
.profile-wrapper.is-web .pf-kpi-num.is-warn { color: var(--tui-warn); }
.profile-wrapper.is-web .pf-kpi-num.is-danger { color: var(--tui-danger); }
.profile-wrapper.is-web .pf-kpi-hint {
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--tui-text-quiet);
}
.profile-wrapper.is-web .pf-kpi-progress { margin-top: auto; padding-top: 8px; }

/* ===== 桌面端学生综合情况：指标行 + 三张图表，图表容器高度收紧 ===== */
.profile-wrapper.is-web .pf-stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}
.profile-wrapper.is-web .pf-charts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.profile-wrapper.is-web .pf-chart {
  padding: 10px 12px 4px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
}
.profile-wrapper.is-web .pf-chart-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.profile-wrapper.is-web .pf-chart-body { height: 168px; }

/* 桌面端加载骨架 / 行内空态：加载中与无数据时同样保持朴素可读的版式 */
.profile-wrapper.is-web .pf-skeleton { display: flex; flex-direction: column; gap: 8px; }
.profile-wrapper.is-web .pf-skeleton-bar {
  height: 14px;
  border-radius: 6px;
  background: var(--tui-surface-sunken);
}
.profile-wrapper.is-web .pf-inline-empty {
  padding: 18px 4px;
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  text-align: center;
}

/* ===== 主体：左导航 + 右内容，占满横幅以下的剩余高度 ===== */
.profile-wrapper.is-web .profile-body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 14px;
  padding-bottom: 16px;
}

.profile-side {
  flex: 0 0 232px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 12px;
  background: #fff;
  border: none;
  border-radius: 14px;
  overflow-y: auto;
  scrollbar-width: none;
}
.profile-side::-webkit-scrollbar { display: none; width: 0; }

.side-group { display: flex; flex-direction: column; gap: 2px; }
.side-group-title {
  padding: 0 8px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #98a2b3;
}

.side-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 9px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: #475467;
  font-family: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.side-item:hover { background: #f6f7f9; color: #101828; }
.side-item.active {
  background: #eff4ff;
  color: #1d4ed8;
  font-weight: 600;
}
.side-item-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-item-danger { color: #b42318; margin-top: auto; }
.side-item-danger:hover { background: #fef3f2; color: #912018; }

/* 右侧内容栏：常驻不滑动，滚动交给内部 */
.profile-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: none;
  border-radius: 14px;
  overflow: hidden;
}

.web-head {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #f2f4f7;
  flex-shrink: 0;
}
.web-head-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #101828;
}
.web-head-sub {
  margin: 3px 0 0;
  font-size: 12px;
  color: #98a2b3;
}

/* 桌面端把移动端子页的绝对定位改成正常的文档流 */
.profile-wrapper.is-web .sub-page-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 20px;
  background: #fff;
  scrollbar-width: none;
}
.profile-wrapper.is-web .sub-page-content::-webkit-scrollbar { display: none; width: 0; }

/* 按钮改为常规宽度，不再整行拉伸 */
.profile-wrapper.is-web .sub-page-footer {
  display: flex;
  justify-content: flex-start;
  padding: 14px 0 0;
  background: transparent;
  border-top: 1px solid #f2f4f7;
  margin-top: 16px;
}
.footer-btn { min-width: 96px; }
@media (max-width: 767px) {
  .footer-btn { width: 100%; }
  /* 保存按钮与学生端一致：移动端黑底白字，需抬升特异性覆盖 admin-components 的蓝色主按钮 */
  .main-area .sub-page-footer .footer-btn.el-button--primary:not(.is-link):not(.is-text):not(.is-plain) {
    background: #14171a;
    background-image: none;
    border-color: #14171a;
    color: #fff;
  }
  .main-area .sub-page-footer .footer-btn.el-button--primary:not(.is-link):not(.is-text):not(.is-plain):hover,
  .main-area .sub-page-footer .footer-btn.el-button--primary:not(.is-link):not(.is-text):not(.is-plain):focus {
    background: #2a2f34;
    background-image: none;
    border-color: #2a2f34;
    color: #fff;
  }
}

/* 桌面端表单区域宽度受控，避免输入框横跨整页 */
.profile-wrapper.is-web .sp-card,
.profile-wrapper.is-web .sp-submit { max-width: 520px; }

/* 滑动动画 */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(100%);
}
.slide-left-leave-to {
  transform: translateX(-30%);
}
.slide-right-enter-from {
  transform: translateX(-30%);
}
.slide-right-leave-to {
  transform: translateX(100%);
}

/* 主页面：封面通栏铺满，页内边距交由内容面板（.pf-body）承担 */
.profile-page {
  position: absolute;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
  overscroll-behavior-y: contain;
  background: var(--tui-bg);
  padding: 0;
}

/* 子页面 */
.sub-page {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--tui-bg);
  display: flex;
  flex-direction: column;
  z-index: 10;
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
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.sub-page-placeholder {
  width: 36px;
}

.sub-page-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* ===== 修改密码：单卡片表单，参考 GitHub / Telegram 安全设置 ===== */
.sp-card {
  padding: 18px 16px;
  border: 1px solid var(--tui-border);
  border-radius: 16px;
  background: var(--tui-surface);
}
.sp-head { display: block; }
.sp-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--tui-text);
}
.sp-desc {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--tui-text-tertiary);
}
.sp-field { display: block; margin-top: 16px; }
.sp-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 7px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.sp-page :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: var(--tui-surface-sunken);
  box-shadow: 0 0 0 1px var(--tui-border) inset;
  padding: 6px 12px;
}
.sp-page :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--tui-text-tertiary) inset;
}

/* 密码强度：三档中性色进度条 */
.sp-meter { display: flex; align-items: center; gap: 5px; margin-top: 8px; }
.sp-meter-bar {
  width: 26px;
  height: 3px;
  border-radius: 999px;
  background: var(--tui-border);
  transition: background 0.2s;
}
.sp-meter-bar.is-on { background: var(--tui-text); }
.sp-meter-text {
  margin-left: 4px;
  font-style: normal;
  font-size: 11px;
  color: var(--tui-text-tertiary);
}
.sp-error {
  display: block;
  margin-top: 7px;
  font-size: 11.5px;
  color: #d9534f;
}
.sp-captcha { display: flex; gap: 10px; }
.sp-captcha .el-input { flex: 1; }
.sp-captcha-code {
  flex-shrink: 0;
  width: 96px;
  height: 40px;
  border: 1px solid var(--tui-border);
  border-radius: 10px;
  background: var(--tui-surface-sunken);
  color: var(--tui-text);
  font-family: inherit;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 4px;
  cursor: pointer;
}
.sp-captcha-code:active { opacity: 0.7; }
.sp-submit {
  width: 100%;
  height: 44px;
  margin-top: 18px;
  border: none;
  border-radius: 12px;
  background: var(--tui-text);
  color: var(--tui-bg);
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.sp-submit:active { opacity: 0.86; }
.sp-submit:disabled { opacity: 0.45; cursor: default; }

.sub-page-footer {
  padding: 14px 0;
  margin-top: 8px;
}

.sub-page-footer .el-button {
  height: 40px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
}

/* 个人中心头部（抖音范式）：封面通栏、顶部悬浮操作、头像压住封面下边缘 */
.pf-hero {
  position: relative;
  min-height: 160px;
  padding: 10px 16px 0;
  background-color: #d8dee6;
  background-size: cover;
  background-position: center;
  cursor: pointer;
}
/* 暗色压底仅在自定义背景图时叠加（保证白字可读）；浅色预设背景不加压底 */
.pf-hero-scrim {
  position: absolute;
  inset: 0;
  background: none;
}
.pf-hero.is-photo .pf-hero-scrim {
  background: linear-gradient(
    180deg,
    rgba(10, 12, 16, 0.08) 0%,
    rgba(10, 12, 16, 0.16) 40%,
    rgba(10, 12, 16, 0.62) 100%
  );
}
.pf-hero-top {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pf-top-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid rgba(16, 24, 40, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #344054;
  font-family: inherit;
  font-size: 11.5px;
  cursor: pointer;
  backdrop-filter: blur(6px);
}
.pf-top-pill:active { background: rgba(255, 255, 255, 0.9); }
.pf-hero.is-photo .pf-top-pill {
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(10, 12, 16, 0.3);
  color: #fff;
}
.pf-hero.is-photo .pf-top-pill:active { background: rgba(10, 12, 16, 0.46); }
.pf-top-icons { display: inline-flex; align-items: center; gap: 8px; }
.pf-top-icon {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.72);
  color: #344054;
  cursor: pointer;
  backdrop-filter: blur(6px);
}
.pf-top-icon:active { background: rgba(255, 255, 255, 0.9); }
.pf-hero.is-photo .pf-top-icon {
  background: rgba(10, 12, 16, 0.3);
  color: #fff;
}
.pf-hero.is-photo .pf-top-icon:active { background: rgba(10, 12, 16, 0.46); }

/* 姓名 / 身份：贴在封面右下，给左侧头像让出空间 */
.pf-hero-id {
  position: absolute;
  z-index: 2;
  left: 106px;
  right: 16px;
  bottom: 18px;
}
.pf-hero-id-row { display: flex; align-items: center; gap: 6px; min-width: 0; }
.pf-cast-name {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  line-height: 1.2;
  color: #101828;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-cast-role {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 999px;
  border: 1px solid rgba(16, 24, 40, 0.1);
  background: rgba(255, 255, 255, 0.66);
  color: #475467;
  font-size: 10.5px;
  font-weight: 600;
}
/* 等级徽标：QQ 把等级牌挂在昵称右侧，这里沿用同一位置关系 */
.pf-lv-chip {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 999px;
  background: linear-gradient(135deg, #fde68a, #f59e0b);
  color: #4a2f04;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.3px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.26);
}
.pf-cast-sub {
  margin: 5px 0 0;
  font-size: 11.5px;
  color: #667085;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 自定义背景图：压深文字并复原白色样式，保证在任意照片上都清晰 */
.pf-hero.is-photo .pf-cast-name {
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.36);
}
.pf-hero.is-photo .pf-cast-role {
  border-color: rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}
.pf-hero.is-photo .pf-cast-sub { color: rgba(255, 255, 255, 0.8); }

/* 头像：跨在封面与内容面板的交界线上 */
.pf-hero-avatar {
  position: absolute;
  z-index: 3;
  left: 14px;
  bottom: -26px;
  width: 86px;
  height: 86px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
}
.pf-avatar {
  border: 3px solid var(--tui-surface);
  background: linear-gradient(135deg, #7d6cf2, #5747cc);
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.22);
}
.pf-avatar-edit {
  position: absolute;
  right: 0;
  bottom: 2px;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--tui-surface);
  border-radius: 50%;
  background: linear-gradient(135deg, #34d058, #16a34a);
  color: #fff;
}

/* 数据 / 简介 / 标签 / 快捷入口：参考图里头像下方的白色信息区 */
.pf-profile-top {
  position: relative;
  background: var(--tui-surface);
  border-radius: 20px 20px 0 0;
  padding: 50px 16px 10px;
}
/* 勋章条：头像右侧的留白带，等级牌 + 勋章小图标串 + 勋章墙入口（QQ 资料卡样式） */
.pf-badge-strip {
  position: absolute;
  top: 9px;
  left: 108px;
  right: 16px;
  height: 26px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.pf-badge-strip-icons {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  overflow: hidden;
}
/* 迷你勋章不再是圆形图标：复用盾形成就徽章造型（无绶带、缩到 22px），点击可放大查看 */
.pf-badge-mini {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  background: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: transform 0.15s ease;
}
.pf-badge-mini:active { transform: scale(0.93); }
.pf-badge-mini:focus-visible { outline: 2px solid #c7ccd4; outline-offset: 1px; border-radius: 8px; }
.pf-badge-empty {
  font-size: 10.5px;
  color: var(--tui-text-quiet);
  white-space: nowrap;
}
/* 勋章条只放得下前 5 枚，多出来的用 +N 明示，避免和勋章墙数量对不上 */
.pf-badge-more {
  flex-shrink: 0;
  height: 20px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: rgba(17, 20, 24, 0.06);
  color: var(--tui-text-secondary, #667085);
  font-size: 10.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.pf-badge-pill {
  flex-shrink: 0;
  height: 22px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #ffefc2, #f8c65a);
  color: #7a4a06;
  font-family: inherit;
  font-size: 10.5px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}
.pf-badge-pill:active { filter: brightness(0.96); }
.pf-stat-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
.pf-stat {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}
.pf-stat b {
  font-size: 19px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.2px;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.pf-stat b i {
  margin-left: 1px;
  font-style: normal;
  font-size: 9.5px;
  font-weight: 500;
  color: var(--tui-text-quiet);
}
.pf-stat b.is-success { color: var(--tui-success); }
.pf-stat b.is-warn { color: var(--tui-warn); }
.pf-stat b.is-danger { color: var(--tui-danger); }
.pf-stat span {
  font-size: 10.5px;
  line-height: 1.2;
  color: var(--tui-text-tertiary);
  white-space: nowrap;
}
.pf-edit-btn {
  flex-shrink: 0;
  height: 32px;
  margin-left: 6px;
  padding: 0 14px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 7px;
  background: var(--tui-surface);
  color: var(--tui-text);
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.pf-edit-btn:active { background: var(--tui-surface-muted); }
.pf-stat-skeleton { flex: 1; display: flex; gap: 10px; }
.pf-stat-skeleton span {
  flex: 1;
  height: 34px;
  border-radius: 6px;
  background: var(--tui-surface-sunken);
}

.pf-bio {
  display: block;
  width: 100%;
  margin: 12px 0 0;
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--tui-text);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.pf-bio.is-empty { color: var(--tui-text-quiet); }

.pf-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}
.pf-tag {
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-tertiary);
  font-size: 10.5px;
  line-height: 1.5;
  white-space: nowrap;
}

/* 快捷入口：单行横向滑动，一屏固定 5 个，其余功能靠左右滑查看 */
.pf-quick {
  margin-top: 14px;
  padding: 12px 16px 6px;
  border-top: 1px solid var(--tui-border);
}
/* 滚动交给内部轨道：外层带 16px 页边距，若让外层滚动，第 6 个入口会在右侧内边距里露出局部 */
.pf-quick-track {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.pf-quick-track::-webkit-scrollbar { display: none; }
.pf-quick-item {
  /* 5 个等分铺满轨道可视区，gap 共 4 个 12px */
  flex: 0 0 calc((100% - 48px) / 5);
  min-width: 0;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  color: var(--tui-text);
  cursor: pointer;
}
.pf-quick-item:active { opacity: 0.6; }
.pf-quick-icon { position: relative; display: inline-flex; align-items: center; justify-content: center; }
.pf-quick-dot {
  position: absolute;
  top: -1px;
  right: -3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fa5151;
}
.pf-quick-label {
  max-width: 100%;
  font-size: 10.5px;
  line-height: 1.2;
  color: var(--tui-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 内容面板：圆角上浮，压住封面底边，形成「悬浮于背景之上」的层次 =====
   面板内边距为 0：分组通铺到两侧，靠灰底/白底色差分块（微信、QQ 设置页的做法） */
.pf-body {
  position: relative;
  z-index: 2;
  margin-top: -16px;
  padding: 0 0 16px;
  border-radius: 20px 20px 0 0;
  background: var(--tui-bg);
}
.pf-body .pf-section:first-child { margin-top: 0; }

/* ===== 分组：白底行组，无圆角/无边框/无阴影 ===== */
.pf-section {
  margin: 0 0 10px;
  background: var(--tui-surface);
  border: none;
  border-radius: 0;
  box-shadow: none;
  overflow: hidden;
}
.pf-section-title {
  margin: 0;
  padding: 12px 16px 6px;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #8b929e;
}
/* 带右侧动作 / 可折叠的分区头：内边距由头部统一承担 */
.pf-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px 6px;
}
.pf-section-head .pf-section-title { padding: 0; }
.pf-section-body { padding: 12px 16px 14px; }
.pf-list { display: flex; flex-direction: column; }
.pf-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 16px;
  border: none;
  border-bottom: 1px solid var(--tui-border);
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.pf-row:last-child { border-bottom: none; }
.pf-row:active { background: var(--tui-surface-muted); }
.pf-row-icon {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: var(--tui-radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--tui-brand-soft);
  color: var(--tui-brand);
  box-shadow: inset 0 0 0 1px rgba(15, 17, 21, 0.03);
}
.pf-row-icon.is-cyan { background: #ecfeff; color: #0891b2; }
.pf-row-icon.is-violet { background: #f4f3ff; color: #6941c6; }
.pf-row-icon.is-warn { background: var(--tui-warn-soft); color: #f79009; }
.pf-row-icon.is-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }
.pf-row-label {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--tui-text);
}
/* 右侧状态说明：把行内大段空白填成有效信息，而不是留空 */
.pf-row-hint {
  flex-shrink: 0;
  max-width: 46%;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-row-arrow { color: #cbd0d8; flex-shrink: 0; }
/* 头像行：大圆头像 + 相机角标（组件本身桌面/移动共用） */
.set-row-ava { padding: 10px 2px; }
.pf-ava-wrap { position: relative; display: inline-flex; }
.pf-ava {
  border: 2px solid #fff;
  background: linear-gradient(135deg, #7d6cf2, #5747cc);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  box-shadow: 0 0 0 1px #e6eae7, 0 1px 5px rgba(20, 24, 22, .10);
}
.pf-ava-cam {
  position: absolute; right: -3px; bottom: -3px;
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: #14171a; color: #fff;
  border: 2px solid #fff;
}

/* 页脚说明：收住列表下方的灰底空白，避免页面尾部大段留白 */
.pf-foot-note {
  margin: 6px 0 0;
  padding: 4px 16px 0;
  text-align: center;
  font-size: 10.5px;
  letter-spacing: 0.2px;
  color: var(--tui-text-quiet);
}

/* ===== 设置项列表（抖音设置页范式）：左标签 + 右值 + 箭头 ===== */
.set-page .set-group { margin-bottom: 10px; }
.set-page .set-group-title {
  margin: 0 0 6px 16px;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #8b929e;
}
.set-page .set-list {
  background: var(--tui-surface);
  border: none;
  border-radius: 0;
  box-shadow: none;
  overflow: hidden;
}
.set-page .set-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px 16px;
  border: none;
  border-bottom: 1px solid var(--tui-border);
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.set-page .set-row:last-child { border-bottom: none; }
.set-page .set-row:active { background: var(--tui-surface-muted); }
.set-page .set-row.is-readonly { cursor: default; }
.set-page .set-row.is-readonly:active { background: transparent; }
.set-page .set-row-label {
  flex-shrink: 0;
  font-size: 13.5px;
  color: var(--tui-text);
}
.set-page .set-row-value {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 13px;
  color: var(--tui-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.set-page .set-row-value.is-empty { color: var(--tui-text-quiet); }
.set-page .set-row-arrow { color: #cbd0d8; flex-shrink: 0; }

/* ===== 更换背景（抖音背景选择器范式）：实时预览 + 背景宫格 ===== */
.set-page .bg-preview {
  position: relative;
  display: flex;
  align-items: flex-end;
  height: 152px;
  padding: 14px;
  border-radius: var(--tui-radius);
  background-color: #d8dee6;
  background-size: cover;
  background-position: center;
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}
.set-page .bg-preview-scrim {
  position: absolute;
  inset: 0;
  background: none;
}
.set-page .bg-preview.is-photo .bg-preview-scrim {
  background: linear-gradient(
    180deg,
    rgba(10, 12, 16, 0.04) 0%,
    rgba(10, 12, 16, 0.18) 45%,
    rgba(10, 12, 16, 0.64) 100%
  );
}
.set-page .bg-preview-cast {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.set-page .bg-preview-avatar {
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.5);
  color: #344054;
  font-size: 15px;
  font-weight: 600;
}
.set-page .bg-preview.is-photo .bg-preview-avatar { color: #fff; }
.set-page .bg-preview-name {
  font-size: 14px;
  font-weight: 700;
  color: #101828;
}
.set-page .bg-preview.is-photo .bg-preview-name {
  color: #fff;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.3);
}
.set-page .bg-preview-sub {
  margin-top: 2px;
  font-size: 11px;
  color: #667085;
}
.set-page .bg-preview.is-photo .bg-preview-sub { color: rgba(255, 255, 255, 0.82); }
.set-page .bg-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.set-page .bg-cell {
  position: relative;
  height: 62px;
  padding: 0;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background-color: var(--tui-surface-muted);
  background-size: cover;
  background-position: center;
  cursor: pointer;
  overflow: hidden;
}
.set-page .bg-cell.is-active {
  border-color: transparent;
  box-shadow: 0 0 0 2px var(--tui-brand);
}
.set-page .bg-cell-check {
  position: absolute;
  right: 4px;
  bottom: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--tui-brand);
  color: #fff;
}
.set-page .bg-cell-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-style: dashed;
  color: var(--tui-text-tertiary);
  font-size: 11.5px;
}
.set-page .bg-cell-upload:active { background: var(--tui-surface-sunken); }
.set-page .bg-hint {
  margin: 8px 2px 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}

/* 主题设置 */
.theme-options {
  display: flex;
  gap: 16px;
  justify-content: center;
  background: #fff;
  border-radius: 16px;
  padding: 24px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 16px;
  border: 2px solid transparent;
  transition: all 0.2s;
  background: #f9fafb;
}
.theme-option.active {
  border-color: #409eff;
  background: rgba(64,158,255,0.05);
}
.theme-option span {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}
.theme-preview {
  width: 58px;
  height: 58px;
  border-radius: 14px;
  border: 2px solid #eee;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.light-preview { background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%); }

.theme-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--tui-surface-sunken);
  border-radius: 10px;
  color: var(--tui-text-tertiary);
  font-size: 12px;
}

/* 关于 */
.about-header {
  text-align: center;
  background: #fff;
  border-radius: 16px;
  padding: 24px 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.about-logo {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  margin-bottom: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.about-name {
  font-size: 19px;
  font-weight: 700;
  color: #1a1a1a;
}
.about-version {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
.about-slogan {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}
.about-section {
  background: #fff;
  border-radius: 16px;
  padding: 16px 14px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.about-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid #409eff;
}
.about-text {
  font-size: 14px;
  color: #666;
  line-height: 1.8;
  text-align: justify;
}
.about-features {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.feature-item {
  padding: 8px 16px;
  background: linear-gradient(135deg, #f0f8ff 0%, #e8f4ff 100%);
  border-radius: 20px;
  font-size: 13px;
  color: #409eff;
  border: 1px solid rgba(64,158,255,0.15);
}
.about-team {
  display: flex;
  align-items: center;
  gap: 16px;
}
.team-info {
  flex: 1;
}
.team-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 6px;
}
.team-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}

/* 帮助 */
.help-content {
  background: #fff;
  border-radius: 16px;
  padding: 8px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.help-item {
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f5;
}
.help-item:last-child { border-bottom: none; }
.help-question {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.help-question::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
  flex-shrink: 0;
}
.help-answer {
  font-size: 14px;
  color: #666;
  line-height: 1.8;
  padding-left: 12px;
}

/* 公告卡片：每条独立成卡；宽度跟随子页容器（父级已有 16px 页边距），横屏时居中收窄 */
.ann-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 560px;
  margin: 0 auto;
  padding: 0 0 16px;
  box-sizing: border-box;
}
.ann-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 14px;
  text-align: left;
  font-family: inherit;
  border: 1px solid #eef0f3;
  border-radius: 12px;
  background: var(--tui-surface, #fff);
  cursor: pointer;
}
.ann-card:active { background: #fafbfc; }
.ann-card-date {
  font-size: 11px;
  color: #98a2b3;
  font-variant-numeric: tabular-nums;
}
.ann-card-title {
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.5;
  color: #344054;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ann-card-foot {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-top: 2px;
  font-size: 11px;
  color: #b0b7c3;
}

.ann-empty {
  margin: 0;
  padding: 26px 0;
  text-align: center;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
</style>
