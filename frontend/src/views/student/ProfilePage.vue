<template>
  <div class="profile-wrapper">
    <!-- 主页面 -->
    <transition :name="slideDirection">
      <div
        v-if="!currentPage"
        key="main"
        class="profile-page"
        @touchstart.passive="pull.onStart"
        @touchmove="pull.onMove"
        @touchend="pull.onEnd"
        @touchcancel="pull.onCancel"
      >
        <!-- 下拉刷新指示器：主页面滚动层最上方（封面区在它之后，一起下移） -->
        <PullRefreshIndicator
          v-if="isMobile"
          :indicator-style="pull.indicatorStyle"
          :active="pull.active"
        />
        <!-- 个人中心头部：抖音范式封面 —— 顶部悬浮操作、头像压住封面下边缘、姓名与学号贴在封面右下 -->
        <section class="pf-hero" :class="{ 'is-photo': !!bannerUrl }" :style="heroBannerStyle" @click="openPage('banner')">
          <div class="pf-hero-scrim"></div>

          <div class="pf-hero-top">
            <button type="button" class="pf-top-pill" @click.stop="openPage('banner')">
              <el-icon :size="13"><Camera /></el-icon>
              更换背景
            </button>
            <span class="pf-top-icons">
              <button type="button" class="pf-top-icon" title="设置" @click.stop="openPage('settings')">
                <el-icon :size="16"><Setting /></el-icon>
              </button>
            </span>
          </div>

          <div class="pf-hero-id">
            <div class="pf-hero-id-row">
              <h2 class="pf-cast-name">{{ auth.userName }}</h2>
              <span class="pf-cast-role">学生</span>
              <span v-if="badgeWall" class="pf-lv-chip">Lv.{{ badgeWall.level.level }}</span>
            </div>
            <p class="pf-cast-sub">学号：{{ auth.user?.username || '—' }}</p>
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
          <!-- 数据行 + 编辑资料（对应参考图「关注 / 粉丝 … + 编辑主页」） -->
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
              <div class="pf-stat">
                <b>{{ growthStats.awards || 0 }}</b>
                <span>成长记录</span>
              </div>
              <div class="pf-stat">
                <b>{{ growthStats.skills || 0 }}</b>
                <span>技能标签</span>
              </div>
              <div class="pf-stat">
                <b>{{ growthStats.projects || 0 }}</b>
                <span>项目经历</span>
              </div>
              <div class="pf-stat">
                <b>{{ goalCount }}</b>
                <span>发展目标</span>
              </div>
              <button type="button" class="pf-edit-btn" @click="openPage('profile')">编辑资料</button>
            </div>

            <button type="button" class="pf-bio" :class="{ 'is-empty': !auth.user?.signature }" @click="openPage('profile')">
              {{ auth.user?.signature || '还没有个性签名，点这里填写' }}
            </button>

            <div class="pf-tags">
              <span v-if="auth.user?.college" class="pf-tag">{{ auth.user.college }}</span>
              <span class="pf-tag">画像完整度 {{ imageComplete }}%</span>
            </div>

            <!-- 快捷入口行：一屏固定 5 个，其余左右滑查看（勋章已移到头像右侧的勋章条） -->
            <nav class="pf-quick">
              <div class="pf-quick-track">
                <button type="button" class="pf-quick-item" @click="openPage('profile')">
                  <span class="pf-quick-icon"><el-icon :size="21"><User /></el-icon></span>
                  <span class="pf-quick-label">我的资料</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/student/growth')">
                  <span class="pf-quick-icon"><el-icon :size="21"><TrendCharts /></el-icon></span>
                  <span class="pf-quick-label">成长档案</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/student/plan')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Calendar /></el-icon></span>
                  <span class="pf-quick-label">学习计划</span>
                </button>
                <button type="button" class="pf-quick-item" @click="router.push('/student/portfolio')">
                  <span class="pf-quick-icon"><el-icon :size="21"><FolderOpened /></el-icon></span>
                  <span class="pf-quick-label">我的作品集</span>
                </button>
                <button type="button" class="pf-quick-item" @click="openPage('badges')">
                  <span class="pf-quick-icon"><el-icon :size="21"><Medal /></el-icon></span>
                  <span class="pf-quick-label">勋章墙</span>
                </button>
                <button type="button" class="pf-quick-item" @click="openPage('feedback')">
                  <span class="pf-quick-icon"><el-icon :size="21"><ChatLineSquare /></el-icon></span>
                  <span class="pf-quick-label">意见反馈</span>
                </button>
              </div>
            </nav>
          </div>

          <!-- 收藏的帖子 & 项目经历：同一行 Tab 切换（左右滑可换）+ 下方向下铺开的卡片 -->
          <div class="pf-cards-area">
            <div class="pf-cards-tabs" role="tablist" aria-label="个人内容">
              <button
                type="button"
                role="tab"
                class="pf-cards-tab"
                :class="{ 'is-active': cardTab === 'projects' }"
                :aria-selected="cardTab === 'projects'"
                @click="cardTab = 'projects'"
              >
                项目经历
              </button>
              <button
                type="button"
                role="tab"
                class="pf-cards-tab"
                :class="{ 'is-active': cardTab === 'favorites' }"
                :aria-selected="cardTab === 'favorites'"
                @click="cardTab = 'favorites'"
              >
                收藏的帖子
              </button>
            </div>

            <!-- 左右滑动切换：项目经历在前，向左滑（dx<0）到收藏，向右滑回项目经历 -->
            <div
              class="pf-cards-body"
              @touchstart="onSwipeStart"
              @touchmove="onSwipeMove"
              @touchend="onSwipeEnd"
              @pointerdown="onPointerStart"
              @pointerup="onPointerEnd"
            >
              <template v-if="cardTab === 'favorites'">
                <div v-if="favLoading" class="pf-cards-loading">加载中…</div>
                <div v-else-if="!favorites.length" class="pf-cards-empty">还没有收藏任何帖子</div>
                <div v-else class="pf-media-grid">
                  <div
                    v-for="fav in favorites.slice(0, 4)"
                    :key="fav.id"
                    class="pf-media-card"
                    @click="router.push('/student/campus?tab=favorites')"
                  >
                    <div class="pf-media-cover" :class="`tone-${fav.id % 5}`">
                      <span class="pf-media-cover-text">{{ fav.category || '帖子' }}</span>
                      <span v-if="fav.category" class="pf-media-tag">{{ fav.category }}</span>
                    </div>
                    <div class="pf-media-title">{{ fav.title }}</div>
                    <div class="pf-media-meta">
                      <el-icon :size="11"><Star /></el-icon>
                      <span>{{ fav.created_at ? fav.created_at.slice(0, 10) : '已收藏' }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <template v-else>
                <div v-if="projLoading" class="pf-cards-loading">加载中…</div>
                <div v-else-if="!projects.length" class="pf-cards-empty">还没有项目经历</div>
                <div v-else class="pf-media-grid">
                  <div
                    v-for="p in projects.slice(0, 4)"
                    :key="p.id"
                    class="pf-media-card"
                    @click="router.push('/student/portfolio')"
                  >
                    <div class="pf-media-cover" :class="`tone-${p.id % 5}`">
                      <img v-if="p.cover_url" :src="p.cover_url" :alt="p.project_name" loading="lazy" />
                      <span v-else class="pf-media-cover-text">{{ p.tech_stack || '项目' }}</span>
                      <span v-if="p.is_team" class="pf-media-tag">团队</span>
                    </div>
                    <div class="pf-media-title">{{ p.project_name }}</div>
                    <div class="pf-media-meta">
                      <el-icon :size="11"><Folder /></el-icon>
                      <span>{{ p.start_date.slice(0, 7) }}{{ p.end_date ? ' ~ ' + p.end_date.slice(0, 7) : ' 至今' }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <p class="pf-foot-note">{{ agentName }} · 智慧校园服务平台 v1.0.0</p>
        </div>
      </div>
    </transition>

    <!-- 子页面 -->
    <transition :name="slideDirection">
      <div v-if="currentPage" key="sub" class="sub-page">
        <!-- 子页面头部 -->
        <div class="sub-page-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="sub-page-title">{{ pageTitle }}</div>
          <div class="sub-page-placeholder"></div>
        </div>

        <!-- 设置（抖音设置页范式）：灰底 + 白色圆角卡片 + 无图标纯文字行 + 居中退出登录 -->
        <div v-if="currentPage === 'settings'" class="sub-page-content set-page">
          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="openPage('profile')">
                <span class="set-row-label">账号与安全</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="set-row" @click="openPage('password')">
                <span class="set-row-label">修改密码</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="set-row" @click="openPage('banner')">
                <span class="set-row-label">更换背景</span>
                <span class="set-row-value is-empty">个人主页封面</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="openPage('theme')">
                <span class="set-row-label">主题设置</span>
                <span class="set-row-value">{{ currentTheme === 'dark' ? '深色' : '浅色' }}</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="set-row" @click="openPage('feedback')">
                <span class="set-row-label">意见反馈</span>
                <span class="set-row-value is-empty">帮助我们改进</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="set-row" @click="openPage('help')">
                <span class="set-row-label">使用帮助</span>
                <span class="set-row-value is-empty">新手引导</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="openPage('about')">
                <span class="set-row-label">关于{{ agentName }}</span>
                <span class="set-row-value">v1.0.0</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row set-row-logout" @click="logout">
                <span class="set-row-label">退出登录</span>
              </button>
            </div>
          </div>

          <p class="set-version">{{ agentName }} v1.0.0</p>
        </div>

        <!-- 账号与安全（抖音设置页范式）：只读展示 + 点按行弹窗编辑，不再铺一屏输入框 -->
        <div v-if="currentPage === 'profile'" class="sub-page-content set-page">
          <!-- 头像：抖音「编辑资料」里的一行，右侧直接显示当前头像 -->
          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="triggerAvatarInput">
                <span class="set-row-label">头像</span>
                <span class="set-row-value">
                  <span class="pf-ava-wrap">
                    <el-avatar :size="44" :src="profileForm.avatar" class="pf-ava">
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

          <!-- 我的简历（仅移动端）：上传条 + 文件卡列表 + 底部「导出简历」向导入口 -->
          <div class="set-group pf-resume-group">
            <div class="set-group-title">我的简历</div>
            <button type="button" class="pf-resume-upload" @click="triggerResumeUpload">
              <span class="pf-resume-uplus"><el-icon :size="16"><Plus /></el-icon></span>
              <span class="pf-resume-utext"><b>上传简历文件</b><i>支持 PDF / DOC / DOCX</i></span>
              <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
            </button>
            <div v-for="r in resumes" :key="r.id" class="pf-resume-file">
              <span class="pf-resume-badge" :data-ext="fileExt(r.filename)">{{ fileExt(r.filename) }}</span>
              <span class="pf-resume-info">
                <b>{{ r.filename }}</b>
                <i>{{ r.is_current ? '当前使用 · 投递时优先展示' : '点击「设为当前」作为主力简历' }}</i>
              </span>
              <span class="pf-resume-acts">
                <button type="button" @click.stop="previewResume(r)">预览</button>
                <button v-if="!r.is_current" type="button" @click.stop="makeCurrent(r)">设为当前</button>
                <button type="button" class="is-danger" @click.stop="removeResume(r)">删除</button>
              </span>
            </div>
            <div v-if="!resumes.length" class="pf-resume-empty">还没有简历：可上传文件，或用下方「导出简历」一键生成专属简历</div>
            <input ref="resumeInputRef" type="file" accept=".pdf,.doc,.docx" style="display:none" @change="onResumeFileChange" />
          </div>

          <div class="sub-page-footer pf-profile-foot">
            <el-button type="primary" class="pf-save-btn" @click="handleSaveProfile" :loading="saving">保存</el-button>
            <button type="button" class="pf-export-btn" @click="resumeWizardVisible = true">
              <el-icon :size="15"><Document /></el-icon>导出简历
            </button>
          </div>
        </div>

        <!-- 我的勋章：完整勋章墙（等级 + 已获得 + 待解锁进度） -->
        <div v-if="currentPage === 'badges'" class="sub-page-content">
          <BadgeWall
            v-if="badgeWall"
            :earned="badgeWall.earned"
            :locked="badgeWall.locked"
            :level="badgeWall.level"
          />
          <div v-else class="badge-placeholder">勋章数据加载中…</div>
        </div>

        <!-- 修改密码（同教师端）：单卡片表单 + 密码强度提示 -->
        <div v-if="currentPage === 'password'" class="sub-page-content sp-page">
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

        <!-- 意见反馈（同教师端）：单卡片表单 + 历史记录卡片 -->
        <div v-if="currentPage === 'feedback'" class="sub-page-content sp-page">
          <div class="sp-card">
            <div class="sp-head">
              <h3 class="sp-title">提交反馈</h3>
              <p class="sp-desc">描述遇到的问题或想要的功能，提交后可在下方查看处理进度与官方回复。</p>
            </div>

            <div class="sp-field">
              <span class="sp-label">反馈类型</span>
              <el-select v-model="feedbackForm.type" style="width:100%">
                <el-option label="问题反馈" value="bug" /><el-option label="功能建议" value="feature" />
                <el-option label="投诉" value="complaint" /><el-option label="其他" value="other" />
              </el-select>
            </div>
            <div class="sp-field">
              <span class="sp-label">标题</span>
              <el-input v-model="feedbackForm.title" placeholder="请简要描述" maxlength="100" />
            </div>
            <div class="sp-field">
              <span class="sp-label">内容</span>
              <el-input v-model="feedbackForm.content" type="textarea" :rows="4" placeholder="请详细描述" />
            </div>
            <div class="sp-field">
              <span class="sp-label">联系方式</span>
              <el-input v-model="feedbackForm.contact" placeholder="手机号/邮箱，方便我们联系您" />
            </div>
          </div>

          <button type="button" class="sp-submit" :disabled="submitting" @click="submitFeedback">
            {{ submitting ? '正在提交…' : '提交反馈' }}
          </button>

          <div class="fb-history">
            <h3 class="fb-history-title">历史反馈</h3>
            <div v-loading="loadingFeedback" class="fb-list">
              <div v-if="feedbackList.length === 0 && !loadingFeedback" class="empty-feedback">暂无反馈记录</div>
              <article v-for="item in feedbackList" :key="item.id" class="fb-card">
                <div class="fb-card-head">
                  <span class="fb-type">{{ getTypeLabel(item.type) }}</span>
                  <span class="fb-status" :class="`is-${item.status}`">{{ getStatusLabel(item.status) }}</span>
                </div>
                <div class="fb-title">{{ item.title }}</div>
                <div class="fb-content">{{ item.content }}</div>
                <div v-if="item.reply" class="fb-reply">
                  <div class="fb-reply-label">官方回复</div>
                  <div class="fb-reply-text">{{ item.reply }}</div>
                </div>
                <div class="fb-time">{{ item.created_at?.slice(0, 10) }}</div>
              </article>
            </div>
          </div>
        </div>

        <!-- 使用帮助 -->
        <div v-if="currentPage === 'help'" class="sub-page-content">
          <div class="help-content">
            <div class="help-item">
              <div class="help-question">如何联系{{ agentName }}？</div>
              <div class="help-answer">在首页直接输入你的问题，{{ agentName }}会即时回复。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看课表？</div>
              <div class="help-answer">输入"查课表"即可获取本周课程安排。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何请假？</div>
              <div class="help-answer">输入"我要请假"，按提示填写信息即可。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看成绩？</div>
              <div class="help-answer">输入"查成绩"即可查看各科成绩和GPA。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看通知？</div>
              <div class="help-answer">输入"查通知"即可获取教务处最新公告。</div>
            </div>
          </div>
        </div>

        <!-- 主题设置（同教师端：仅浅色模式 + 说明） -->
        <div v-if="currentPage === 'theme'" class="sub-page-content">
          <div class="theme-options">
            <div class="theme-option" :class="{ active: currentTheme === 'light' }" @click="setTheme('light')">
              <div class="theme-preview light-preview"></div>
              <span>浅色模式</span>
            </div>
          </div>
          <div class="theme-hint">
            <span>当前系统仅支持浅色模式</span>
          </div>
        </div>

        <!-- 关于绵小城 -->
        <div v-if="currentPage === 'about'" class="sub-page-content">
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
              {{ agentName }}是绵阳城市学院官方推出的智慧校园AI助手，基于大语言模型技术，为全校师生提供智能化的校园服务。通过自然语言对话，您可以轻松完成课表查询、成绩查询、请假申请、校园通知查看等日常事务，让校园生活更加便捷高效。
            </div>
          </div>

          <!-- 项目简介 -->
          <div class="about-section">
            <div class="about-section-title">项目简介</div>
            <div class="about-text">
              本项目采用前后端分离架构，前端使用 Vue 3 + TypeScript + Element Plus 构建，后端基于 FastAPI + Python 实现，集成大语言模型 API 提供智能对话能力。项目支持学生端和教师端，涵盖智能对话、办事服务、成长档案、校园风采等多个功能模块，致力于打造全方位的智慧校园生态。
            </div>
          </div>

          <!-- 核心功能 -->
          <div class="about-section">
            <div class="about-section-title">核心功能</div>
            <div class="about-features">
              <div class="feature-item">智能对话</div>
              <div class="feature-item">课表查询</div>
              <div class="feature-item">成绩查询</div>
              <div class="feature-item">请假申请</div>
              <div class="feature-item">成长记录</div>
              <div class="feature-item">校园通知</div>
              <div class="feature-item">学业分析</div>
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
        <div v-if="currentPage === 'banner'" class="sub-page-content set-page">
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
                  <div class="bg-preview-sub">学号：{{ auth.user?.username || '—' }}</div>
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

    <!-- 账号与安全：字段编辑（单字段小内容：移动端=底部动作面板 / 桌面端=弹窗） -->
    <ActionSheet
      v-model="editVisible"
      :title="editField ? `修改${editField.label}` : ''"
      width="86%"
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
      <el-select v-else v-model="editValue" placeholder="请选择" filterable style="width:100%">
        <el-option v-for="o in editField?.options || []" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmFieldEdit">确定</el-button>
      </template>
    </ActionSheet>

    <!-- 头像裁剪（交互工具：移动端=底部动作面板 / 桌面端=弹窗） -->
    <ActionSheet v-model="avatarCropVisible" title="裁剪头像" width="420px">
      <div class="crop-container">
        <img ref="avatarCropImgRef" style="max-width:100%;display:block" />
      </div>
      <template #footer>
        <el-button @click="cancelAvatarCrop">取消</el-button>
        <el-button type="primary" @click="handleAvatarCropConfirm">确认裁剪</el-button>
      </template>
    </ActionSheet>

    <!-- 勋章放大查看 -->
    <BadgeDetail :badge="badgeDetail" @close="badgeDetail = null" />

    <!-- 导出简历向导：问答 → 匹配度 → 模板（真实预览）→ 生成 DOCX/PDF -->
    <ResumeExportWizard v-model="resumeWizardVisible" @generated="loadResumes" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, getTeachers, changePassword } from '@/api/user'
import { createFeedback, getFeedbacks } from '@/api/feedback'
import { uploadFile } from '@/api/upload'
import { getGrowthProfile, getProjects, type GrowthProfile, type StudentProject } from '@/api/growth'
import { getFavorites, type Favorite } from '@/api/resources'
import { getGoals } from '@/api/plan'
import { getMyBadgeWall, type BadgeItem, type BadgeWall as BadgeWallData } from '@/api/badge'
import { syncQuickAccount } from '@/utils/quickLogin'
import { confirmLogout } from '@/utils/logout'
import BadgeWall from '@/components/profile/BadgeWall.vue'
import BadgeMedal from '@/components/profile/BadgeMedal.vue'
import BadgeDetail from '@/components/profile/BadgeDetail.vue'
import { syncBadgeAwards } from '@/composables/useBadgeAward'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useResponsive } from '@/composables/useResponsive'
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
// v6.1 弹窗减负：单字段编辑/裁剪等轻交互走底部动作面板（简历向导与简历删除确认保持原样）
import ActionSheet from '@/components/common/ActionSheet.vue'
import {
  ArrowRight, ArrowLeft,
  ChatLineSquare, Camera, Check, Plus, Setting, Document,
  User, TrendCharts, Calendar, FolderOpened, Medal, Star, Folder
} from '@element-plus/icons-vue'
import { getResumes, createResume, setCurrentResume, deleteResume, type Resume } from '@/api/portfolio'
import ResumeExportWizard from '@/components/resume/ResumeExportWizard.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { isMobile } = useResponsive()

// 关于页品牌信息与站点配置同源
const { siteName, siteLogo, agentName } = useSiteConfig()

// 页面状态
const currentPage = ref<string | null>(null)
const slideDirection = ref('slide-left')

// 个人中心的设置等页内子页打开时，让出移动端底部悬浮导航（一级页面才该有页签）
useMobileSubPage(computed(() => isMobile.value && !!currentPage.value))

// 表单状态
const saving = ref(false)
const submitting = ref(false)
const changingPassword = ref(false)
const uploadingBanner = ref(false)
const teachers = ref<any[]>([])
const currentTheme = ref(localStorage.getItem('theme') || 'light')

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

// 成长统计
const growthStats = reactive({
  awards: 0,
  skills: 0,
  projects: 0,
})

// 成长画像（供 AI 驾驶舱与推荐使用）
const growthProfile = ref<GrowthProfile | null>(null)
const goalCount = ref(0)

// 收藏的帖子 & 项目经历（个人中心卡片展示）
const favorites = ref<Favorite[]>([])
const projects = ref<StudentProject[]>([])
const favLoading = ref(false)
const projLoading = ref(false)

/** 卡片区当前 Tab：项目经历在前，收藏在后 */
const cardTab = ref<'projects' | 'favorites'>('projects')

/**
 * 左右滑动切换（触摸为主，鼠标拖拽辅助）。
 * 用 touchmove 判定而不是只靠 touchend：手指拖动时页面可能开始纵向滚动，
 * 一旦触发 pointercancel 就收不到 pointerup，touchend 反而是可靠的落点。
 */
let swipeStartX: number | null = null
function swipeBegin(x: number) { swipeStartX = x }
function swipeCheck(x: number) {
  if (swipeStartX === null) return
  const dx = x - swipeStartX
  if (Math.abs(dx) < 40) return
  // 项目在前、收藏在后：从右往左滑（dx<0）→ 收藏；从左往右滑 → 项目经历
  cardTab.value = dx < 0 ? 'favorites' : 'projects'
  swipeStartX = null
}
function onSwipeStart(e: TouchEvent) {
  const t = e.touches[0]
  if (t) swipeBegin(t.clientX)
}
function onSwipeMove(e: TouchEvent) {
  const t = e.touches[0]
  if (t) swipeCheck(t.clientX)
}
function onSwipeEnd(e: TouchEvent) {
  const t = e.changedTouches[0]
  if (t) swipeCheck(t.clientX)
  swipeStartX = null
}
// 鼠标（桌面端预览）拖动：只认 mouse，避免和触摸事件重复触发
function onPointerStart(e: PointerEvent) {
  if (e.pointerType === 'mouse') swipeBegin(e.clientX)
}
function onPointerEnd(e: PointerEvent) {
  if (e.pointerType !== 'mouse') return
  swipeCheck(e.clientX)
  swipeStartX = null
}

async function loadFavorites() {
  favLoading.value = true
  try {
    favorites.value = await getFavorites()
  } catch { favorites.value = [] }
  finally { favLoading.value = false }
}

const imageComplete = computed(() => {
  let score = 0
  if ((growthProfile.value?.skills?.length || 0) > 0) score += 30
  if ((growthProfile.value?.interests?.length || 0) > 0) score += 20
  if (goalCount.value > 0) score += 25
  if (growthStats.projects > 0 || (growthProfile.value?.total_records || 0) > 0) score += 25
  return score
})

async function loadGrowth() {
  projLoading.value = true
  try {
    const [p, pros, goals] = await Promise.all([getGrowthProfile(), getProjects(), getGoals()])
    growthProfile.value = p
    projects.value = pros || []
    growthStats.awards = p?.total_records || 0
    growthStats.skills = p?.total_skills || 0
    growthStats.projects = pros?.length || 0
    goalCount.value = goals?.length || 0
  } catch { /* ignore */ }
  finally { projLoading.value = false }
}

// 勋章墙（等级 / 已获得 / 待解锁进度）
const badgeWall = ref<BadgeWallData | null>(null)
/** 点击勋章条上的小勋章 → 放大查看 */
const badgeDetail = ref<BadgeItem | null>(null)

/** 勋章条只陈列前 4 枚已点亮勋章（再多会挤掉右侧入口），其余用 +N 提示 */
const earnedBadgePreview = computed(() => (badgeWall.value?.earned ?? []).slice(0, 4))

/**
 * 结算 + 拉取勋章墙：先让后端按最新使用数据结算（可能解锁新勋章，由布局层的
 * 奖励动画队列播放），再取回完整勋章墙。两者顺序不能颠倒，否则新勋章会缺席。
 */
async function refreshBadges() {
  try {
    await syncBadgeAwards()
    badgeWall.value = await getMyBadgeWall()
  } catch { /* 拉取失败保持原样 */ }
}

const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '', captcha: '' })
const captchaCode = ref('')

/** 新密码强度：0~3 格（长度 6+、字母数字混排、长度 10+ 各计一格） */
const passwordStrength = computed(() => {
  const v = passwordForm.new_password || ''
  let s = 0
  if (v.length >= 6) s += 1
  if (/[a-zA-Z]/.test(v) && /\d/.test(v)) s += 1
  if (v.length >= 10) s += 1
  return Math.min(s, 3)
})
const passwordStrengthText = computed(() => ['弱', '一般', '较强', '强'][passwordStrength.value] || '弱')
/** 两次输入不一致（确认框为空时不提示，避免一进来就报红） */
const passwordMismatch = computed(
  () => !!passwordForm.confirm_password && passwordForm.new_password !== passwordForm.confirm_password,
)

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
const profileForm = reactive({
  username: '', name: '', college: '', gender: '', age: 18,
  hometown: '', phone: '', qq: '', tutor_id: null as number | null,
  className: '', political_status: '', avatar: '', signature: ''
})

/** 身份背景（移动端 .pf-hero / .bg-preview 共用）：优先用已上传图片，否则用预设渐变 */
const heroBannerStyle = computed(() =>
  bannerUrl.value ? { backgroundImage: `url(${bannerUrl.value})` } : { background: bannerGradient.value }
)

/**
 * 账号与安全：字段描述表（抖音设置项范式）。
 * 页面只读展示「左侧标签 + 右侧值 + 箭头」，点按行弹出编辑弹窗；
 * 用 computed 而非常量，是为了让「辅导员」的可选项跟随 teachers 异步加载。
 */
interface AccField {
  key: string
  label: string
  type: 'text' | 'select' | 'number'
  options?: { label: string; value: string | number }[]
  placeholder?: string
  readonly?: boolean
}

const accGroups = computed<{ title: string; fields: AccField[] }[]>(() => [
  {
    title: '账号信息',
    fields: [
      { key: 'username', label: '学号', type: 'text', readonly: true },
      { key: 'name', label: '姓名', type: 'text', readonly: true },
      { key: 'college', label: '学院', type: 'text', readonly: true },
      { key: 'className', label: '班级', type: 'text', placeholder: '请输入班级' },
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
      {
        key: 'tutor_id', label: '辅导员', type: 'select',
        options: teachers.value.map((t: any) => ({ label: `${t.name}（${t.username}）`, value: t.id })),
      },
    ],
  },
])

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

const feedbackForm = reactive({ type: 'other', title: '', content: '', contact: '' })
const feedbackList = ref<any[]>([])
const loadingFeedback = ref(false)

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    settings: '设置',
    profile: '账号与安全',
    badges: '我的勋章',
    password: '修改密码',
    feedback: '意见反馈',
    help: '使用帮助',
    theme: '主题设置',
    about: `关于${agentName.value}`,
    banner: '更换背景'
  }
  return titles[currentPage.value || ''] || ''
})

// 打开子页面
function openPage(page: string) {
  if (page === 'profile') {
    const u = auth.user
    if (u) {
      profileForm.username = u.username
      profileForm.name = u.name
      profileForm.college = u.college || ''
      profileForm.gender = u.gender || ''
      profileForm.age = u.age ?? 18
      profileForm.hometown = u.hometown || ''
      profileForm.phone = u.phone || ''
      profileForm.qq = u.qq || ''
      profileForm.tutor_id = u.tutor_id ?? null
      profileForm.className = (u as any).class_name || ''
      profileForm.political_status = (u as any).political_status || ''
      profileForm.avatar = (u as any).avatar || ''
      profileForm.signature = (u as any).signature || ''
    }
    loadResumes()          // 进资料页即刷新「我的简历」列表
  }
  slideDirection.value = 'slide-left'
  currentPage.value = page
}

// 关闭子页面
function closePage() {
  slideDirection.value = 'slide-right'
  currentPage.value = null
}

// ==================== 我的简历（资料页内管理 + 导出向导入口） ====================
const resumes = ref<Resume[]>([])
const resumeInputRef = ref<HTMLInputElement>()
const resumeWizardVisible = ref(false)

async function loadResumes() {
  try { resumes.value = await getResumes() } catch { /* 资料页不因简历接口失败而阻塞 */ }
}

function triggerResumeUpload() { resumeInputRef.value?.click() }

/** 文件类型徽标文本：简历卡左侧的 PDF / DOC 小方块 */
function fileExt(name: string) {
  const m = /\.([a-z0-9]+)$/i.exec(name || '')
  return (m?.[1] || 'file').toUpperCase().slice(0, 4)
}

async function onResumeFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''            // 允许重复选同一个文件
  if (!file) return
  if (file.size > 10 * 1024 * 1024) { ElMessage.warning('文件不能超过 10MB'); return }
  const loading = ElMessage({ message: '上传中…', duration: 0 })
  try {
    const up = await uploadFile(file)
    await createResume({ filename: file.name, url: up.url, file_size: file.size })
    await loadResumes()
    ElMessage.success('简历已上传')
  } catch {
    ElMessage.error('上传失败，请重试')
  } finally {
    loading.close()
  }
}

function previewResume(r: Resume) {
  if (!r.url) return
  window.open(r.url, '_blank', 'noopener')
}

async function makeCurrent(r: Resume) {
  try {
    await setCurrentResume(r.id)
    await loadResumes()
    ElMessage.success('已设为当前简历')
  } catch {
    ElMessage.error('设置失败，请重试')
  }
}

async function removeResume(r: Resume) {
  try {
    await ElMessageBox.confirm(`删除「${r.filename}」？`, '删除简历', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch { return }
  try {
    await deleteResume(r.id)
    await loadResumes()
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败，请重试')
  }
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

// 头像裁剪
const avatarCropVisible = ref(false)
const avatarInputRef = ref<HTMLInputElement>()
const avatarCropImgRef = ref<HTMLImageElement>()
let avatarCropper: Cropper | null = null
let pendingAvatarSrc = ''

function triggerAvatarInput() {
  avatarInputRef.value?.click()
}

function onAvatarSelect(e: Event) {
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
  const reader = new FileReader()
  reader.onload = () => {
    pendingAvatarSrc = reader.result as string
    avatarCropVisible.value = true
  }
  reader.readAsDataURL(file)
  input.value = ''
}

function onAvatarCropOpened() {
  avatarCropper?.destroy()
  const img = avatarCropImgRef.value
  if (!img) return
  img.src = pendingAvatarSrc
  avatarCropper = new Cropper(img, {
    aspectRatio: 1,
    viewMode: 1,
    autoCropArea: 1,
    background: false,
  })
}

// 打开后初始化裁剪器（ActionSheet 移动端无 opened 事件，watch+nextTick 两端统一触发）
watch(avatarCropVisible, (v) => {
  if (v) nextTick(() => onAvatarCropOpened())
})

function cancelAvatarCrop() {
  avatarCropVisible.value = false
  avatarCropper?.destroy()
  avatarCropper = null
  pendingAvatarSrc = ''
}

async function handleAvatarCropConfirm() {
  const cropper = avatarCropper
  if (!cropper) return
  const canvas = cropper.getCroppedCanvas({ width: 200, height: 200 })
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
  if (!blob) { ElMessage.error('裁剪失败'); return }
  try {
    const { url } = await uploadFile(new File([blob], 'avatar.png', { type: 'image/png' }))
    profileForm.avatar = url
    ElMessage.success('头像已更新，点击保存后生效')
  } catch {
    ElMessage.error('上传失败')
  }
  cancelAvatarCrop()
}

function applyTheme(theme: string) {
  currentTheme.value = theme
  const root = document.documentElement
  
  if (theme === 'dark') {
    root.classList.add('dark')
    root.style.setProperty('--bg-color', '#1a1a1a')
    root.style.setProperty('--text-color', '#e5e5e5')
    root.style.setProperty('--card-bg', '#2a2a2a')
    root.style.setProperty('--border-color', '#3a3a3a')
  } else {
    root.classList.remove('dark')
    root.style.setProperty('--bg-color', '#f5f7fa')
    root.style.setProperty('--text-color', '#1a1a1a')
    root.style.setProperty('--card-bg', '#ffffff')
    root.style.setProperty('--border-color', '#f0f0f0')
  }
  
  localStorage.setItem('theme', theme)
}

function setTheme(theme: string) {
  applyTheme(theme)
  ElMessage.success('主题已切换')
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
      tutor_id: profileForm.tutor_id || null,
      class_name: profileForm.className || null,
      political_status: profileForm.political_status || null,
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

async function submitFeedback() {
  if (!feedbackForm.title || !feedbackForm.content) {
    ElMessage.warning('请填写标题和内容'); return
  }
  submitting.value = true
  try {
    await createFeedback({
      type: feedbackForm.type,
      title: feedbackForm.title,
      content: feedbackForm.content,
      contact: feedbackForm.contact || undefined,
    })
    ElMessage.success('反馈已提交')
    feedbackForm.title = ''; feedbackForm.content = ''; feedbackForm.contact = ''
    loadFeedbacks()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submitting.value = false }
}

async function loadFeedbacks() {
  loadingFeedback.value = true
  try {
    feedbackList.value = await getFeedbacks()
  } catch { feedbackList.value = [] }
  finally { loadingFeedback.value = false }
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    bug: '问题反馈',
    feature: '功能建议',
    other: '其他'
  }
  return labels[type] || '其他'
}

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待处理',
    replied: '已回复',
    resolved: '已解决'
  }
  return labels[status] || status
}

// 下拉刷新：复用主页面已有的加载函数（画像统计 / 勋章 / 收藏 / 简历），失败静默
async function refreshAll() {
  await Promise.all([loadGrowth(), refreshBadges(), loadFavorites(), loadResumes()])
}

const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

onMounted(async () => {
  try { teachers.value = await getTeachers() } catch {}
  refreshCaptcha()
  loadFeedbacks()
  loadGrowth()
  loadFavorites()
  loadResumes()
  refreshBadges()
  applyTheme('light')
  // 支持外部跳转直达子页（如工作台"意见反馈"入口）
  const page = route.query.page as string | undefined
  if (page && ['settings', 'profile', 'badges', 'password', 'feedback', 'help', 'theme', 'about', 'banner'].includes(page)) {
    openPage(page)
  }
})
</script>

<style scoped>
.profile-wrapper {
  position: relative;
  height: 100%;
  overflow: hidden;
}

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

/* 头像裁剪容器 */
.crop-container {
  max-height: 320px;
  overflow: hidden;
  display: flex;
  justify-content: center;
}

/* ===== 单卡片表单（同教师端）：修改密码 / 意见反馈 ===== */
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
.sp-page :deep(.el-input__wrapper),
.sp-page :deep(.el-select .el-input__wrapper) {
  border-radius: 10px;
  background: var(--tui-surface-sunken);
  box-shadow: 0 0 0 1px var(--tui-border) inset;
  padding: 6px 12px;
}
.sp-page :deep(.el-input__wrapper.is-focus),
.sp-page :deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--tui-text-tertiary) inset;
}
.sp-page :deep(.el-textarea__inner) {
  border-radius: 10px;
  background: var(--tui-surface-sunken);
  box-shadow: 0 0 0 1px var(--tui-border) inset;
  padding: 10px 12px;
  resize: none;
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

/* ===== 个人中心头部（抖音范式）：封面通栏、顶部悬浮操作、头像压住封面下边缘 ===== */
.pf-hero {
  position: relative;
  min-height: 154px;
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
  bottom: 26px;
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
.badge-placeholder {
  padding: 14px 4px;
  font-size: 12px;
  color: var(--tui-text-quiet);
  text-align: center;
}

/* 数据 / 简介 / 标签 / 快捷入口：参考图里头像下方的白色信息区 */
.pf-profile-top {
  position: relative;
  background: var(--tui-surface);
  border-radius: 20px 20px 0 0;
  padding: 50px 16px 10px;
}
/* 勋章条：头像右侧的留白带，等级牌 + 迷你金属勋章串 + 勋章墙入口（QQ 资料卡样式） */
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
.pf-stat-row { display: flex; align-items: center; gap: 4px; }
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
  padding: 14px 16px 10px;
  border-top: 1px solid var(--tui-border);
}
/* 滚动交给内部轨道：外层带 16px 页边距，若让外层滚动，第 6 个入口会在右侧内边距里露出局部 */
.pf-quick-track {
  display: flex;
  align-items: flex-start;
  /* 首尾各贴齐页面 16px 页边距，5 个格子等分整行宽度，不留两侧空白 */
  gap: 8px;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.pf-quick-track::-webkit-scrollbar { display: none; }
.pf-quick-item {
  /* 5 个等分铺满轨道可视区；多留 1px，避免亚像素舍入把第 5 个挤出可视区 */
  flex: 0 0 calc((100% - 33px) / 5);
  min-width: 0;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
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
   面板内边距为 0：分组通铺到两侧，靠灰底/白底色差分块（微信、QQ 设置页的做法），
   不用带圆角与阴影的卡片。 */
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
/* 组标签坐在灰色底上（微信/QQ 设置页的小标题位置） */
.pf-section-title {
  margin: 0;
  padding: 12px 16px 6px;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #8b929e;
}
.pf-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px 6px;
}
.pf-section-head .pf-section-title { padding: 0; }
.pf-section-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  cursor: pointer;
}
.pf-section-more:active { color: var(--tui-text-secondary); }
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
.pf-row-arrow { color: #cbd0d8; flex-shrink: 0; }
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
/* 页脚说明：收住列表下方的灰底空白，避免页面尾部大段留白 */
.pf-foot-note {
  margin: 6px 0 0;
  padding: 4px 16px 0;
  text-align: center;
  font-size: 10.5px;
  letter-spacing: 0.2px;
  color: var(--tui-text-quiet);
}

/* ===== 收藏的帖子 & 项目经历：同一行 Tab 切换 + 向下铺开的封面卡 ===== */
.pf-cards-area { padding: 12px 16px 0; }

/* Tab 行：两个标题同一水平线，选中态加粗 + 短下划线（抖音「作品 / 喜欢」范式） */
.pf-cards-tabs {
  display: flex;
  align-items: center;
  gap: 18px;
}
.pf-cards-tab {
  position: relative;
  padding: 0 0 7px;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  color: var(--tui-text-quiet);
  cursor: pointer;
  transition: color 0.15s ease;
}
.pf-cards-tab.is-active {
  font-weight: 600;
  color: var(--tui-text);
}
.pf-cards-tab.is-active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 18px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
  transform: translateX(-50%);
}

.pf-cards-body { margin-top: 10px; touch-action: pan-y; }
.pf-cards-loading,
.pf-cards-empty {
  padding: 16px 8px;
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  text-align: center;
}

/* 两列网格，数据向下铺开（不再横向滑动） */
.pf-media-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 10px;
}
.pf-media-card { min-width: 0; cursor: pointer; }
.pf-media-card:active { opacity: 0.72; }

/* 封面：16:9，圆角 8px；无图时用低饱和渐变 + 分类文字占位（同 B 站专栏封面） */
.pf-media-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: #eef1f5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pf-media-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.pf-media-cover-text {
  padding: 0 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.4px;
  color: #fff;
  text-align: center;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
/* 五种低饱和渐变轮换，避免一片同色 */
.pf-media-cover.tone-0 { background: linear-gradient(135deg, #8ea2c6, #5f739c); }
.pf-media-cover.tone-1 { background: linear-gradient(135deg, #9ab6a4, #6b8d78); }
.pf-media-cover.tone-2 { background: linear-gradient(135deg, #c2a68e, #96795f); }
.pf-media-cover.tone-3 { background: linear-gradient(135deg, #a89cc0, #7a6b96); }
.pf-media-cover.tone-4 { background: linear-gradient(135deg, #90aab8, #637f8f); }
.pf-media-tag {
  position: absolute;
  left: 6px;
  bottom: 6px;
  max-width: calc(100% - 12px);
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(10, 12, 16, 0.56);
  color: rgba(255, 255, 255, 0.94);
  font-size: 10px;
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 标题：B 站式两行截断，封面下 6px */
.pf-media-title {
  margin-top: 6px;
  font-size: 12.5px;
  font-weight: 500;
  line-height: 1.42;
  color: var(--tui-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
/* 元信息：灰字小图标一行，同 B 站「播放量 · 弹幕数」位置 */
.pf-media-meta {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 3px;
  font-size: 10.5px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  white-space: nowrap;
}

/* ===== 设置项列表（抖音设置页范式）=====
   灰底画布 + 白色圆角卡片，行内只有「左标签 / 右值 / 箭头」三段；
   分隔线内缩到文字起点，卡片之间靠灰色间隙分块，不用分组标题与彩色图标。 */
.set-page { padding: 12px 12px 28px; }
.set-page .set-group { margin-bottom: 12px; }
.set-page .set-group-title {
  margin: 0 0 8px 4px;
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 0.2px;
  color: var(--tui-text-quiet);
}
.set-page .set-list {
  background: var(--tui-surface);
  border: none;
  border-radius: 12px;
  box-shadow: none;
  overflow: hidden;
}
.set-page .set-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 54px;
  padding: 0 16px;
  border: none;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
/* 分隔线：距左 16px 起（与文字对齐），右端通到卡片边缘 */
.set-page .set-row + .set-row::before {
  content: '';
  position: absolute;
  top: 0;
  left: 16px;
  right: 0;
  height: 1px;
  background: var(--tui-border);
  transform: scaleY(0.5);
  transform-origin: top;
}
.set-page .set-row:active { background: #f5f5f5; }
.set-page .set-row.is-readonly { cursor: default; }
.set-page .set-row.is-readonly:active { background: transparent; }
.set-page .set-row-label {
  flex-shrink: 0;
  font-size: 15px;
  font-weight: 400;
  color: var(--tui-text);
  line-height: 1.3;
}
.set-page .set-row-value {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 13px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.set-page .set-row-value.is-empty { color: var(--tui-text-quiet); }
.set-page .set-row-arrow { color: #c7ccd4; flex-shrink: 0; }
/* 退出登录：抖音式独立白卡片，整行居中、无箭头 */
.set-page .set-row-logout {
  justify-content: center;
  min-height: 52px;
}
.set-page .set-row-logout .set-row-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--tui-danger);
}
.set-page .set-version {
  margin: 2px 0 0;
  text-align: center;
  font-size: 11.5px;
  letter-spacing: 0.2px;
  color: var(--tui-text-quiet);
}
.set-page .pf-ava-wrap {
  position: relative;
  display: inline-flex;
}
.set-page .pf-ava {
  border: 2px solid #fff;
  background: linear-gradient(135deg, #7d6cf2, #5747cc);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  box-shadow: 0 0 0 1px #e6eae7, 0 1px 5px rgba(20, 24, 22, .10);
}
.set-page .pf-ava-cam {
  position: absolute;
  right: -3px;
  bottom: -3px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #14171a;
  color: #fff;
  border: 2px solid #fff;
}

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
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  background: #f9fafb;
}
.theme-option:hover {
  background: #f5f7fa;
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

/* 历史反馈：标题 + 一卡一条 */
.fb-history { margin-top: 22px; }

.fb-history-title {
  margin: 0 0 10px 4px;
  font-size: 12px;
  font-weight: 400;
  color: var(--tui-text-quiet);
}

.fb-list { min-height: 96px; }

.empty-feedback {
  padding: 32px 0;
  text-align: center;
  font-size: 13px;
  color: var(--tui-text-quiet);
}

.fb-card {
  margin-bottom: 10px;
  padding: 14px;
  border: 1px solid var(--tui-border);
  border-radius: 14px;
  background: var(--tui-surface);
}

.fb-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.fb-type {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--tui-text-tertiary);
}

.fb-status {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  font-size: 11px;
  color: var(--tui-text-tertiary);
}

.fb-status.is-pending { color: var(--tui-text); }
.fb-status.is-replied,
.fb-status.is-resolved { color: var(--tui-text-secondary); }

.fb-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tui-text);
}

.fb-content {
  margin-top: 5px;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--tui-text-secondary);
}

.fb-reply {
  margin-top: 10px;
  padding: 10px 12px;
  border-left: 2px solid var(--tui-border-strong);
  border-radius: 0 10px 10px 0;
  background: var(--tui-surface-sunken);
}

.fb-reply-label {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--tui-text-tertiary);
}

.fb-reply-text {
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--tui-text);
}

.fb-time {
  margin-top: 10px;
  font-size: 11px;
  color: var(--tui-text-quiet);
}

/* ── 我的简历 + 双按钮页脚（仅移动端生效；桌面端资料页保持原样）── */
.pf-resume-group,
.pf-export-btn { display: none; }
/* 桌面端：保存按钮仍是整宽（与原版一致） */
.pf-profile-foot .pf-save-btn { width: 100%; }

@media (max-width: 767px) {
  /* 下拉刷新：避免浏览器原生下拉刷新抢手势 */
  .profile-page { overscroll-behavior-y: contain; }
  .pf-resume-group { display: block; }
  /* 上传条：虚线框整条可点 */
  .pf-resume-upload {
    display: flex; align-items: center; gap: 10px;
    width: 100%; padding: 11px 12px;
    border: 1.5px dashed #c9d2cd; border-radius: 12px;
    background: #fafcfb;
    text-align: left; font-family: inherit;
    cursor: pointer; -webkit-tap-highlight-color: transparent;
  }
  .pf-resume-upload:active { background: #f1f6f3; }
  .pf-resume-uplus {
    flex: none; width: 30px; height: 30px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 9px;
    background: #14171a; color: #fff;
  }
  .pf-resume-utext { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .pf-resume-utext b { font-size: 13px; font-weight: 600; color: #14171a; }
  .pf-resume-utext i { font-style: normal; font-size: 11px; color: #98a1a8; }
  .pf-resume-upload .set-row-arrow { color: #c0c7c3; }

  /* 文件卡：类型徽标 + 名称/状态 + 文字操作 */
  .pf-resume-file {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 2px;
    border-bottom: 1px solid #f1f4f2;
  }
  .pf-resume-file:last-of-type { border-bottom: 0; }
  .pf-resume-badge {
    flex: none;
    min-width: 34px; padding: 0 6px; height: 22px;
    display: inline-flex; align-items: center; justify-content: center;
    border-radius: 6px;
    background: #eef1f4; color: #5b6472;
    font-size: 9.5px; font-weight: 700; letter-spacing: .4px;
    font-variant-numeric: tabular-nums;
  }
  .pf-resume-badge[data-ext="PDF"] { background: #fdecea; color: #c53a30; }
  .pf-resume-badge[data-ext="DOC"], .pf-resume-badge[data-ext="DOCX"] { background: #e8f0fe; color: #2f5fd0; }
  .pf-resume-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .pf-resume-info b {
    font-size: 12.5px; font-weight: 500; color: #14171a;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .pf-resume-info i { font-style: normal; font-size: 10.5px; color: #98a1a8; }
  .pf-resume-acts { flex: none; display: inline-flex; gap: 2px; }
  .pf-resume-acts button {
    border: 0; background: transparent; padding: 4px 6px;
    font-size: 12px; font-family: inherit; color: #0f7a58;
    cursor: pointer; -webkit-tap-highlight-color: transparent;
  }
  .pf-resume-acts button.is-danger { color: #c53a30; }
  .pf-resume-acts button:active { opacity: .65; }
  .pf-resume-empty {
    padding: 12px 2px 4px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--tui-text-tertiary, #999);
  }

  /* 页脚：保存 + 导出简历 同款黑底白字（导出在保存右侧）。
     注意：admin-components.css 里 .main-area .el-button--primary:not(...) 蓝渐变
     特异性 (0,5,0) 会盖掉普通覆盖，这里用带 :not 链的同源选择器抬到 (0,7,0)。 */
  .pf-profile-foot { display: flex; gap: 10px; }
  .pf-profile-foot .pf-save-btn,
  .main-area .pf-profile-foot .pf-save-btn.el-button--primary:not(.is-link):not(.is-text):not(.is-plain) {
    flex: 1; width: auto; margin-left: 0;
    background: #14171a;
    background-image: none;
    border-color: #14171a;
    color: #fff;
  }
  .pf-profile-foot .pf-save-btn:hover,
  .pf-profile-foot .pf-save-btn:focus,
  .main-area .pf-profile-foot .pf-save-btn.el-button--primary:not(.is-link):not(.is-text):not(.is-plain):hover,
  .main-area .pf-profile-foot .pf-save-btn.el-button--primary:not(.is-link):not(.is-text):not(.is-plain):focus {
    background: #2a2f34; background-image: none; border-color: #2a2f34; color: #fff;
  }
  .pf-export-btn {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    /* 与保存按钮(el-button)完全同款：responsive.css 移动端给 .el-button 设了
       min-height:44px、admin-components 设了 8px 圆角，这里对齐保持一致观感 */
    height: 44px;
    border: 1px solid #14171a;
    border-radius: var(--ad-control-radius, 8px);
    background: #14171a;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .pf-export-btn:active { background: #2a2f34; border-color: #2a2f34; }
}
</style>
