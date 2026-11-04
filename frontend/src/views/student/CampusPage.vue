<template>
  <div
    class="campus-page subpage-underlay"
    :class="{ 'is-subpushed': campusPushed }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <!-- ===== 页头（桌面 / 移动两套，刻意不合并：两者版式差一整代）=====
         桌面端：白底通栏大标题 + 纯图标搜索；标题本身可点 = 刷新（标题是这页最强的
         「我要看这个」暗示，点它重取比多放一个按钮更省地方）。
         移动端（2026-10 改版，一比一复刻资讯流 App）：
           ① 白底页头：左侧 26px/700 黑色大标题，右侧两枚纯黑线性图标（搜索 / 通知）；
              页头吸顶（sticky）：信息流往下滚时标题与两个入口始终留在顶部；
           ② 白底分类 Tab：选中项黑色粗体 + 3px 黑色下划线，其余灰色，可横向滑动；
              紧跟在页头下方一起吸顶，滚到信息流深处也能直接换分类；
           ③ 信息流：15px 粗体标题两行 + 12px 灰色元信息，右侧大缩略图，
              行间 1px 浅灰分割线。
         移动端不提供手动刷新：由 10 分钟模块缓存 + 后端 5 分钟缓存兜住，重进页面即可重新取数。
         不放返回箭头：本页是底部导航的一级 Tab，没有「上一页」可回。 -->
    <header v-if="isMobile" class="campus-appbar">
      <div class="appbar-title">
        <h1>校园资讯</h1>
      </div>
      <div class="appbar-actions">
        <!-- 教师端扩展位：教师端复用本页（UI 与内容不变）时，由外层注入本端专属入口
             （如「发布」）。学生端不传插槽，这里什么都不渲染。 -->
        <slot name="appbar-actions" />
        <button
          v-if="isGuestMode()"
          type="button"
          class="appbar-login"
          @click="goLogin"
        >
          登录
        </button>
        <button
          type="button"
          class="appbar-btn"
          aria-label="搜索校园资讯"
          @click="openSearch"
        >
          <el-icon><Search /></el-icon>
        </button>
        <!-- 互动消息：学生社区（论坛）互动回执，学生端专属；
             教师端复用本页时不渲染（教师不走学生社区互动，两端读同一份资讯、写入口按角色分开） -->
        <button
          v-if="role === 'student'"
          type="button"
          class="appbar-btn appbar-btn--dot"
          aria-label="互动消息"
          @click="openForumInbox"
        >
          <el-icon><Message /></el-icon>
          <i v-if="forumUnread" class="appbar-dot">{{ forumUnread > 99 ? '99+' : forumUnread }}</i>
        </button>
      </div>
    </header>

    <section v-else class="campus-hero-head">
      <button
        class="hero-head-text"
        type="button"
        :disabled="refreshing"
        aria-label="刷新校园资讯"
        @click="refreshImpression"
      >
        <h2>校园资讯</h2>
      </button>
      <button
        class="hero-head-search"
        type="button"
        aria-label="搜索校园资讯"
        @click="openSearch"
      >
        <el-icon><Search /></el-icon>
      </button>
      <!-- 桌面端也留互动消息入口：论坛的赞 / 收藏 / 评论只在这里看 -->
      <button
        class="hero-head-search hero-head-dot"
        type="button"
        aria-label="互动消息"
        @click="openForumInbox"
      >
        <el-icon><Message /></el-icon>
        <i v-if="forumUnread" class="appbar-dot">{{ forumUnread > 99 ? '99+' : forumUnread }}</i>
      </button>
    </section>

    <!-- 搜索浮层：先在本页已加载的资讯里过滤，一条都没有再兜到知识库检索。
         这个顺序符合直觉 —— 用户在这页点搜索，多半想找刚看到的某条资讯；
         本页资讯是「校内动态」、知识库是「办事问答」，两层语义不同但都该给到。 -->
    <!-- 搜索（轻内容：移动端=底部动作面板 / 桌面端=弹窗） -->
    <ActionSheet v-model="searchVisible" title="搜索校园资讯" width="600px">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索资讯标题，如：放假、招聘、奖学金……"
        :prefix-icon="Search"
        clearable
        @keyup.enter="runSearch"
      />
      <div class="search-hot">
        <span class="search-hot-label">热门：</span>
        <el-tag
          v-for="kw in SEARCH_HOT_KEYWORDS"
          :key="kw"
          class="search-hot-tag"
          effect="plain"
          @click="quickSearch(kw)"
        >{{ kw }}</el-tag>
      </div>

      <!-- ① 本页资讯命中 -->
      <div v-if="searchDone" class="search-block">
        <div class="search-block-title">校园资讯（{{ newsHits.length }}）</div>
        <a
          v-for="h in newsHits"
          :key="h.url + h.title"
          class="search-hit"
          :href="h.url"
          @click.prevent="openSearchHit(h)"
        >
          <span class="search-hit-source">{{ h.sourceLabel }}</span>
          <span class="search-hit-title">{{ h.title }}</span>
          <span v-if="h.date" class="search-hit-date">{{ h.date }}</span>
        </a>
        <p v-if="!newsHits.length" class="search-empty">本页资讯中没有匹配项</p>
      </div>

      <!-- ② 知识库兜底：仅在本页资讯 0 命中时才去查，避免无谓的后端检索 -->
      <div v-if="searchDone" class="search-block">
        <div class="search-block-title">
          知识库{{ knowledgeLoading ? '' : `（${knowledgeHits.length}）` }}
        </div>
        <p v-if="knowledgeLoading" class="search-empty">检索中…</p>
        <template v-else-if="knowledgeHits.length">
          <div v-for="(h, i) in knowledgeHits" :key="i" class="search-hit search-hit-static">
            <span class="search-hit-source">{{ h.category || (h.type === 'qa' ? '问答' : '文档') }}</span>
            <span class="search-hit-title">{{ h.question || h.content || '未命名' }}</span>
          </div>
        </template>
        <p v-else-if="isGuestMode()" class="search-empty">
          知识库检索需要登录，<a href="javascript:;" @click.prevent="promptLogin('检索全校知识库')">去登录</a>
        </p>
        <p v-else class="search-empty">知识库中也没有找到相关内容</p>
      </div>
    </ActionSheet>

    <!-- 移动端分类 Tab：横向滑动、选中项深色 + 短下划线（不改字重）。
         与下方信息流共用同一份数据，切换只是换 filter，不重新请求。
         滚动说明：页头与 Tab 一起吸顶（Tab 粘在页头下沿），滚到信息流任何位置都能
         直接切分类；两者叠成一个白色顶栏，不会在信息流上方切出两条分离的悬浮条。
         不放条数角标：6 个分类在 390px 宽下已超出首屏、需要横向滑动，
         再加数字只会把后面的 Tab 推得更远，却没有滑动暗示。
         分类口径：移动端不展示「高教信息」（见 MOBILE_HIDDEN_SOURCES），
         所以这里比桌面端卡片少一栏 —— 桌面端「高教信息」卡片保留不变。
         「推荐」= 原「全部」合并流；「关注」= 我关注的人发的帖子（见 FollowingFeed）。 -->
    <!-- 移动端分类 Tab：横向滑动、选中项深色 + 短下划线（不改字重）。
         动画本体（下划线滑条 + 文字随条染色）已抽到 components/common/SlidingTabs.vue，
         分页位移的口径在 components/common/SwipePager.vue，
         本页只负责把组件的「拖动进度 / 方向 / 逐帧状态」转给 Tab —— 滑条位置与手指严格同步。
         与下方信息流共用同一份数据，切换只是换 filter，不重新请求。 -->
    <SlidingTabs
      v-if="isMobile"
      class="campus-tabs"
      :tabs="mobileTabs"
      :model-value="activeTab"
      :progress="pagerState.progress"
      :direction="pagerState.direction"
      :dragging="pagerState.dragging"
      :resetting="pagerState.resetting"
      :instant-sweep="pagerState.sliding"
      sticky-top="var(--campus-appbar-h)"
      aria-label="资讯分类"
      @select="onTabSelect"
    />

    <!-- 下拉刷新指示器：放在两段吸顶头（页头 / 分类 Tab）之后，
         靠自身高度把信息流下推、吸顶头保持不动（见 usePullRefresh 注释） -->
    <PullRefreshIndicator
      v-if="isMobile"
      :indicator-style="pull.indicatorStyle"
      :active="pull.active"
    />

    <!-- 卡片分页轨道：手势、位移、吸附 / 回弹 / 点 Tab 换页全部在 components/common/SwipePager.vue，
         本页只管「轨道上摆哪几页」和每页的内容。
         轨道上摆哪些页由组件算（renderedPages：静止 = 当前页，拖动 = 前后邻居，点 Tab = 出发页 + 目标页），
         本页不再判断「邻居页什么时候挂载」。 -->
    <SwipePager
      v-if="isMobile"
      ref="pagerRef"
      class="campus-pager"
      :model-value="activeTab"
      :pages="feedTabKeys"
      start-selector=".campus-feed"
      @update:model-value="onPagerChange"
    >
      <!-- v-memo：拖动时跟手位移每帧变化会让本页重渲染，三页信息流（含图标 SVG）
           会被逐帧 diff，手机上就是卡顿来源。页面内容只跟分类数据有关，
           依赖不变时整棵子树直接跳过 patch。
           （v-for + v-memo 留在调用方而不是交给组件：组件的插槽每次渲染都会被重建，
             只有写在本页渲染函数里，memo 缓存才真正命中。） -->
      <div
        v-for="entry in pagerPages"
        :key="entry.key"
        v-memo="[entry.key, entry.items, entry.slides]"
        class="sw-pager-page campus-pager-page"
      >
        <!-- 大图轮播：只在「推荐」那一页的顶部渲染。
             图源 = 全部资讯里带 image_url 的最新条目（各来源详情页抓到的正文首图），
             按日期倒序最多 5 张；一张带图的都没有时回落到本地校园风光，避免首屏空一块。
             点击进站内阅读器（与信息流一致），不跳出应用。
             按住图片左右拖动即可切换（鼠标 / 触屏同一套 Pointer 事件逻辑）。
             注意：拖动事件挂在 .hero-track（图片区域）上，**不是**外层 section ——
             挂在外层的话，在标题或留白处按下也会拖着整块轮播平移，像是「整个组件可拖」。 -->
        <section
          v-if="entry.slides.length"
          class="campus-hero-carousel"
          :class="{ 'is-dragging': heroDragging, 'is-resetting': heroResettingTrack }"
          :style="{ '--hero-drag-x': `${heroDragX}px` }"
        >
          <!-- .hero-track 只承担两件事：接收 Pointer 事件、作为自绘指示点的定位参照。
               它**不做位移** —— 位移交给内部的轮播容器（.el-carousel__container，也就是图片那一层），
               这样卡片的圆角与边框始终不动，只有卡片里的图片跟着手指滑动。
               事件绑在外层、位移作用在内层是刻意的：事件层不动，命中区域才稳定。 -->
          <div
            class="hero-track"
            @pointerdown="onHeroPointerDown"
            @pointermove="onHeroPointerMove"
            @pointerup="onHeroPointerUp"
            @pointercancel="onHeroPointerCancel"
            @dragstart="onHeroSlideDragStart"
          >
            <!-- ref 用函数形式：轮播在 v-for 的页面里，最多只有一个（只有「推荐」有图），
                 用字符串 ref 会被当成数组，轮播的 next/prev 就取不到了。 -->
            <el-carousel
              :ref="setHeroCarouselRef"
              :autoplay="heroAutoplay"
              :interval="4200"
              height="196px"
              arrow="never"
              indicator-position="none"
              trigger="click"
              @change="onHeroIndexChange"
            >
              <el-carousel-item v-for="s in entry.slides" :key="s.url">
                <a
                  class="hero-slide"
                  :href="s.url || undefined"
                  @click="onHeroSlideClick($event, s)"
                >
                  <img class="hero-slide-img" :src="s.image_url" alt="" loading="lazy" draggable="false" />
                  <div class="hero-slide-shade" />
                  <div class="hero-slide-caption">
                    <span class="hero-slide-tag">{{ s.tagLabel }}</span>
                    <h3 class="hero-slide-title">{{ s.title }}</h3>
                  </div>
                </a>
              </el-carousel-item>
            </el-carousel>
            <!-- 指示点：叠在图片底边内侧，属于卡片装饰，**不跟着图片一起位移**
                 （它在 .hero-track 里、不在位移层里）。用绝对定位定位，不参与轮播盒子尺寸。
                 纯装饰：pointer-events: none，不影响拖动与点击。 -->
            <div class="hero-dots" aria-hidden="true">
              <span
                v-for="(s, i) in entry.slides"
                :key="s.url + i"
                class="hero-dot"
                :class="{ 'is-active': i === heroIndex }"
              />
            </div>
          </div>
        </section>

        <!-- 信息流：标题两行 + 元信息行 + 右侧缩略图 + 行尾互动数。
             点整行进「资讯详情子页」（正文 + 评论 / 点赞 / 转发），不再直接跳站内阅读器 ——
             只读阅读器留下了「读完了想说两句却说不了」的断点；详情子页把社区那一层补齐，
             正文抓取仍复用后端同一套解析，只是多了一层互动。 -->
        <!-- 交流社区：帖子流有自己的分区筛选 / 排序 / 分页，整块交给 CommunityFeed；
             点一条在本页打开 PostDetailPage（社区独立页已下线，交互全部收在这里） -->
        <CommunityFeed
          v-if="entry.key === 'community'"
          :ref="el => { if (el) communityFeedRef = el as any }"
          @open="openPostDetail"
        />

        <!-- 关注：我关注的人发的帖子（头像条 + 大卡片流），数据与分页都在 FollowingFeed 内部。
             点卡片进帖子详情、点头像进个人主页、空态引导切到交流社区 —— 三件事都回到本页已有的链路，
             不新开独立页面（关注是资讯页的一个分类，跳走会丢浏览位置）。 -->
        <FollowingFeed
          v-else-if="entry.key === 'following'"
          :ref="el => { if (el) followingFeedRef = el as any }"
          @open="openPostDetail"
          @open-user="openUserHomepage"
          @browse="onTabClick('community')"
        />

        <section v-else class="campus-feed">
          <div
            v-for="item in entry.items"
            :key="item.url + item.title"
            class="feed-item"
            :data-kind="item.kind === 'post' ? 'post' : 'article'"
            :data-post-id="item.post_id || null"
            role="link"
            tabindex="0"
            @click="openFeedItem(item)"
            @keydown.enter.prevent="openFeedItem(item)"
          >
            <div class="feed-body">
              <h3 class="feed-title">{{ item.title }}</h3>
              <div class="feed-meta">
                <span class="feed-time">{{ item.timeLabel }}</span>
                <span class="feed-dot">·</span>
                <!-- 社区帖与资讯同款行，只多一个「社区」词：不加底色，跟旁边的来源文字同一套样式 -->
                <template v-if="item.kind === 'post'">
                  <span class="feed-source">社区</span>
                  <span class="feed-dot">·</span>
                </template>
                <span class="feed-source">{{ item.sourceLabel }}</span>
                <!-- 互动数跟时间 / 标签同一行：信息流一行的「元信息」一次读完，
                     标题下方不再单独占一条图标行，行高更紧凑。
                     只留「评论」与「浏览量」，不做收藏 / 点赞：
                     评论进详情子页并直接把输入框聚焦（openDetail 的 from 参数），
                     省掉「进去再点一次」；浏览量只做数字展示（没有可点的去向）。
                     评论量与浏览量都按真实数字显示，0 也显示：
                     「0 条评论、0 次浏览」本身就是有效信息，说明这篇还没人参与。 -->
                <div class="feed-acts">
                  <button
                    type="button"
                    class="feed-act"
                    :aria-label="`评论 ${item.comment_count} 条`"
                    @click.stop="item.kind === 'post' ? openFeedItem(item) : openDetail(item.url, item.title, 'comment')"
                  >
                    <el-icon><ChatDotRound /></el-icon>
                    <span>{{ item.comment_count }}</span>
                  </button>
                  <span class="feed-act is-static" :aria-label="`浏览 ${item.view_count} 次`">
                    <el-icon><View /></el-icon>
                    <span>{{ item.view_count }}</span>
                  </span>
                </div>
              </div>
            </div>
            <!-- 只有真的有图才渲染缩略图：参考稿无图条目是通栏标题，不留右侧空位 -->
            <div v-if="item.image_url" class="feed-thumb">
              <img :src="item.image_url" loading="lazy" alt="" />
            </div>
          </div>
          <p v-if="!entry.items.length" class="feed-empty">{{ emptyTextOf(entry.key) }}</p>
        </section>

        <!-- 收藏不在这里：资讯详情的「收藏」是给学生「以后还要找回来」用的，
             回来找的时候人已经不在资讯页了 —— 入口统一放在个人中心的「收藏」，
             两边各挂一份只会变成两个不同步的单子。 -->

      </div>
    </SwipePager>

    <!-- 以下为桌面端版式（移动端整块隐藏：由上面的 Tab + 信息流替代） -->
    <template v-if="!isMobile">

    <!-- ① 校园风光轮播图（桌面端专属；移动端首屏已改为 Tab + 信息流） -->
    <section class="campus-carousel">
      <el-carousel :interval="4000" height="320px" arrow="hover" trigger="click">
        <el-carousel-item v-for="img in carouselImages" :key="img.image_url">
          <div class="carousel-item">
            <img :src="img.image_url" class="carousel-img" />
            <div class="carousel-overlay">
              <span class="carousel-title">{{ img.title }}</span>
              <span class="carousel-campus">{{ img.campus }}</span>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
    </section>

    <!-- ② 教务系统入口
         移动端（≤767px）：一张白卡 + 3×2 瓷片宫格，6 个入口瓷片完全同口径（浅蓝底 + 蓝图标），
         主入口「教务管理系统」只靠首位顺序 + 标题字重区分。桌面端沿用原来的 3 列白卡 + 单色图标。 -->
    <section class="campus-section">
      <div class="section-title">教务系统入口</div>
      <div class="entry-card">
        <div class="entry-grid">
          <a v-for="e in visibleEntries" :key="e.url" class="entry-item" :class="{ 'is-primary': isPrimaryEntry(e.title) }"
             :href="e.url" target="_blank" rel="noopener noreferrer"
             :title="entryHint(e.url)" :style="{ '--entry-color': getEntryColor(e.title) }" @click="onEntryClick(e, $event)">
            <span class="entry-chip"><el-icon class="entry-icon"><component :is="getEntryIcon(e.title)" /></el-icon></span>
            <p>{{ e.title }}</p>
            <span v-if="opensInNewWindow(e.url)" class="entry-external">↗</span>
          </a>
        </div>
      </div>
    </section>

    <!-- ③ 交流社区（桌面端没有分类页签，保留一张卡片作为入口：
         社区独立页已下线，桌面用户也得有地方进帖子流 / 发帖） -->
    <section class="campus-section">
      <div class="section-title">
        交流社区
        <button type="button" class="section-action" @click="openPostSheet">
          <el-icon :size="13"><Plus /></el-icon>发帖
        </button>
      </div>
      <div class="campus-card">
        <CommunityFeed
          :ref="el => { if (el) desktopCommunityFeedRef = el as any }"
          compact
          @open="openPostDetail"
        />
      </div>
    </section>

    <!-- ② 教学动态 + 通知公告 -->
    <section class="campus-duo">
      <div class="campus-card campus-card-jx" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><DataBoard /></el-icon> 教学动态</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jwgl/jxdt.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jwgl/jxdt.htm', '教学动态')">查看详情 →</a>
        </div>
        <!-- 首条图文大图：桌面端保留在卡内（移动端整块走页面顶部的信息流，不用卡片版式） -->
        <a v-if="impression.jxdt.length" class="jxdt-first" :href="impression.jxdt[0].url" @click.prevent="openArticle(impression.jxdt[0].url, impression.jxdt[0].title)">
          <img v-if="impression.jxdt[0].image_url" :src="impression.jxdt[0].image_url" class="jxdt-first-img" />
          <span class="jxdt-first-title">{{ impression.jxdt[0].title }}</span>
        </a>
        <a v-for="a in impression.jxdt.slice(0, 5)" :key="a.url" class="news-row jxdt-date-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="jxdt-day"><b>{{ splitDay(a.date) }}</b><span class="jxdt-month">{{ splitMonth(a.date) }}</span></span>
          <span class="news-text">{{ a.title }}</span>
        </a>
      </div>
      <div class="campus-card" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Notification /></el-icon> 通知公告</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jwgl/tzgg.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jwgl/tzgg.htm', '通知公告')">查看详情 →</a>
        </div>
        <a v-for="a in impression.tzgg" :key="a.url" class="tzgg-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="tzgg-date">{{ formatDate(a.date) }}</span>
          <span class="news-text">{{ removeCommonPrefix(a.title) }}</span>
        </a>
      </div>
    </section>

    <!-- ③ 高教信息 + 教学建设 -->
    <section class="campus-duo campus-duo-gjxx">
      <div class="campus-card campus-card-gjxx" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><School /></el-icon> 高教信息</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/gjxx.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/gjxx.htm', '高教信息')">查看详情 →</a>
        </div>
        <div class="gjxx-grid">
          <a v-for="a in impression.gjxx" :key="a.url" class="gjxx-item" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
            <el-icon class="gjxx-icon"><Document /></el-icon>
            <span class="gjxx-title">{{ removeCommonPrefix(a.title) }}</span>
            <el-icon class="gjxx-arrow"><ArrowRight /></el-icon>
          </a>
        </div>
      </div>
      <div class="campus-card" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Collection /></el-icon> 教学建设</span>
          <a class="card-more" href="https://jwc.mycc.edu.cn/jxjs.htm" @click.prevent="openArticle('https://jwc.mycc.edu.cn/jxjs.htm', '教学建设')">查看详情 →</a>
        </div>
        <a v-for="a in impression.jxjs.slice(0, 7)" :key="a.url" class="build-row" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
          <span class="build-mark"></span>
          <el-tooltip :content="removeCommonPrefix(a.title)" placement="top" :show-after="300">
            <span class="build-text">{{ removeCommonPrefix(a.title) }}</span>
          </el-tooltip>
          <span class="build-date">{{ a.date }}</span>
        </a>
      </div>
    </section>

    <!-- ④ 专业分院 -->
    <section class="campus-card campus-card-college">
      <div class="card-head">
        <span class="card-title"><el-icon><School /></el-icon> 专业分院</span>
        <span class="section-tag">新闻实时更新</span>
      </div>
      <!-- 桌面端：卡片网格 -->
      <div class="card-body college-body-pc">
        <div class="college-grid">
          <a v-for="c in collegeCards" :key="c.name" class="college-card" :href="c.url" @click.prevent="openArticle(c.url, c.name)">
            <div class="college-head">
              <el-icon class="college-icon" :style="{ color: c.color }"><component :is="c.icon" /></el-icon>
              <span class="college-name">{{ c.name }}</span>
            </div>
            <div class="college-list">
              <div v-for="n in collegeTopNews(c.name)" :key="n.url" class="college-news">
                <span class="news-dot">▪</span><span class="news-text" :title="n.title">{{ n.title }}</span>
                <span v-if="n.day" class="college-date">{{ n.day }}</span>
              </div>
              <!-- 固定补满 2 条槽位：学院 0 条时显示"暂无最新动态"，1 条时补一行空白，
                   保证 7 张卡的新闻区等高、卡片不塌陷 -->
              <div v-if="collegeTopNews(c.name).length < 2" class="college-news">
                <span v-if="!collegeTopNews(c.name).length" class="college-empty">暂无最新动态</span>
              </div>
            </div>
            <span class="college-link">进入官网 →</span>
          </a>
        </div>
      </div>
    </section>

    <!-- ⑤ 绵城印象 -->
    <section class="campus-duo">
      <div class="campus-card campus-card-impression" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><OfficeBuilding /></el-icon> 绵城印象</span>
          <a class="card-more" href="https://www.mycc.edu.cn/mcyx/" @click.prevent="openArticle('https://www.mycc.edu.cn/mcyx/', '绵城印象')">了解更多 →</a>
        </div>
        <div class="impression-list">
          <a v-for="item in impressionItems" :key="item.title" class="impression-row" :href="item.url" @click.prevent="openArticle(item.url, item.title)">
            <el-icon class="impression-icon" :style="{ color: item.color }"><component :is="item.icon" /></el-icon>
            <div class="impression-info">
              <span class="impression-name">{{ item.title }}</span>
              <span class="impression-desc">{{ item.desc }}</span>
            </div>
            <el-icon class="impression-arrow"><ArrowRight /></el-icon>
          </a>
        </div>
      </div>
    </section>

    </template>

    <!-- 站内阅读器：点击资讯在应用内打开，不跳出。
         必须放在 .campus-page 内部 —— 它原先与 .campus-page 同级，
         导致本组件是「多根节点（Fragment）」，而 Vue 的 <Transition>
         无法对 Fragment 根做动画，控制台会报
         「Component inside <Transition> renders non-element root node that cannot be animated」，
         且整个页面的切换动画会失效。
         阅读器自己会 Teleport 抽屉到 body，放在这里不会影响布局。 -->
    <ArticleReader ref="readerRef" @visible-change="readerOpen = $event" />

    <!-- 移动端全屏搜索子页（移动端页头放大镜的落点；桌面端仍走上面的 el-dialog）：
         搜索历史 / 搜索发现 / 热榜三段 + 结果视图，资讯池由父页备好传入。
         点资讯命中条目 → 详情子页盖在本页之上（同 z-index、后挂载者在上），
         详情返回后仍停留在搜索页，搜索上下文不丢。 -->
    <CampusSearchPage
      v-if="searchTarget"
      :items="searchPool"
      @close-start="onSearchLeaving"
      @closed="onSearchClosed"
      @open="openHitFromSearch"
    />

    <!-- 资讯详情子页（移动端信息流点进一条资讯后的落地页）：
         正文由 /api/campus/articles/detail 返回，附带评论 / 点赞 / 转发。
         v-if 控制挂载：组件挂载即打开，卸载即关闭，不必手动管理 visible。 -->
    <ArticleDetailPage
      ref="detailRef"
      v-if="detailTarget"
      :article-url="detailTarget.url"
      :title="detailTarget.title"
      :source="detailTarget.source"
      @close="onDetailLeaving"
      @closed="onDetailClosed"
      @updated="onDetailUpdated"
      @read="onDetailRead"
    />

    <!-- 互动消息面板（论坛侧，与聊天隔离）：页头信封点开的也是这个 -->
    <ForumInboxSheet v-model="forumInboxOpen" />

    <!-- 发帖悬浮按钮：移动端所有分类 Tab 常驻。
         社区已经是本页的一个分类页签，但「想发一条」这件事跟正在看哪个分类无关，
         所以入口留在这一层，不随分类切换消失。游客点击先走登录引导，不发请求。 -->
    <button
      v-if="isMobile && role === 'student'"
      type="button"
      class="community-fab"
      aria-label="发帖"
      @click="openPostSheet"
    >
      <el-icon :size="24"><Plus /></el-icon>
    </button>

    <!-- 发帖编辑器（全屏）：上面那颗悬浮按钮打开的就是它 -->
    <PostComposePage
      v-if="composeOpen"
      @closed="composeOpen = false"
      @published="onPostPublished"
    />

    <!-- 帖子详情（全屏子页 / 桌面端 760px 居中整页）：交流社区页签点一条就落在这里。
         close / closed 两个事件与资讯详情同义：close 是开始退场（下层立刻归位），
         closed 是动画播完（此时才卸载，否则退场动画根本没机会播）。 -->
    <PostDetailPage
      v-if="communityDetailId"
      :post-id="communityDetailId"
      @close="onPostDetailLeaving"
      @closed="onPostDetailClosed"
      @updated="onPostUpdated"
      @deleted="onPostDeleted"
    />
  </div>
</template>

<script setup lang="ts">
// 组件名：两端共用（学生端「校园资讯」Tab 与教师端首页），keep-alive include 按名匹配
defineOptions({ name: 'campus-page' })

/**
 * 角色：本页被学生端与教师端复用，UI 与内容完全一致（同一份资讯流、同一套交互），
 * 差异只在「按角色开放的写入口」：学生端有社区互动回执，教师端由外层插槽补发布入口。
 */
withDefaults(defineProps<{ role?: 'student' | 'teacher' }>(), { role: 'student' })

import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { ElCarousel } from 'element-plus'
// v6.1 弹窗减负：搜索改用底部动作面板承接
import ActionSheet from '@/components/common/ActionSheet.vue'
import { getImpression } from '@/api/campus'
import type { ImpressionItem } from '@/types'
import { getCampusImpressionCache, setCampusImpressionCache } from '@/utils/studentDataCache'
import { tilt } from '@/directives/tilt'
import ArticleReader from '@/components/campus/ArticleReader.vue'
import ArticleDetailPage from '@/components/campus/ArticleDetailPage.vue'
import CampusSearchPage, { type SearchPoolItem } from '@/components/campus/CampusSearchPage.vue'
import ForumInboxSheet from '@/components/community/ForumInboxSheet.vue'
import PostComposePage from '@/components/community/PostComposePage.vue'
import PostDetailPage from '@/components/community/PostDetailPage.vue'
import CommunityFeed from '@/components/community/CommunityFeed.vue'
import FollowingFeed from '@/components/community/FollowingFeed.vue'
import { openUserHomepage } from '@/composables/useUserHomepage'
import type { CommunityPost } from '@/api/community'
import { getRecommendedPosts } from '@/api/community'
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { useMobileSubPage, useSubpagePush } from '@/composables/useMobileSubPage'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
// 分类 Tab 的动画（滑动下划线 + 文字随条染色）已抽成通用组件
import SlidingTabs from '@/components/common/SlidingTabs.vue'
import SwipePager from '@/components/common/SwipePager.vue'
import { getArticleInteractions, type CampusArticleInteract } from '@/api/campus'
import {
  Calendar, Monitor, DataLine, Reading, TrendCharts,
  Document, Clock, Box, Van, ArrowRight,
  Notification, DataBoard,
  School, Collection,
  SetUp, Histogram, HomeFilled, OfficeBuilding, Search, Message,
  ChatDotRound, View, Plus
} from '@element-plus/icons-vue'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
import { isGuestMode } from '@/utils/guest'
import { promptLogin } from '@/utils/loginGate'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

/** 游客回登录页：清掉游客标记后进入登录页（与布局顶栏的登录入口保持同一行为） */
function goLogin() {
  auth.exitGuest()
  router.push({ path: '/login', query: { reason: 'login' } })
}

/** 页头信封 → 互动消息面板（论坛的赞 / 收藏 / 评论 / 新粉丝）：需登录态，游客先引导登录 */
const { forum: forumUnread, refresh: refreshUnread } = useUnreadSummary()
const forumInboxOpen = ref(false)

function openForumInbox() {
  if (isGuestMode()) {
    void promptLogin('查看互动消息')
    return
  }
  forumInboxOpen.value = true
  void refreshUnread()
}

/* ---------- 发帖（悬浮按钮 → 全屏编辑器 PostComposePage） ----------
   发帖入口留在资讯页，但帖子流在独立页，所以发完直接把人带到交流社区，
   让他当场看到自己刚发的这条——否则「发布成功」之后页面上什么都没变，
   看起来像没发出去。 */
const composeOpen = ref(false)

function openPostSheet() {
  if (isGuestMode()) {
    void promptLogin('发帖')
    return
  }
  composeOpen.value = true
}

function onPostPublished() {
  // 发完就在本页看到结果：刷新帖子流并切到「交流社区」页签，
  // 不再跳独立社区页 —— 社区已经是这里的一个分类，跳走反而丢了当前浏览位置。
  void communityFeedRef.value?.refresh()
  void desktopCommunityFeedRef.value?.refresh()
  void followingFeedRef.value?.refresh()
  if (activeTab.value !== 'community') onTabClick('community')
}

const vTilt = tilt
const isMobile = ref(window.innerWidth <= 767)
window.addEventListener('resize', () => { isMobile.value = window.innerWidth <= 767 })

/** 站内阅读器：点击资讯在应用内打开（移动端全屏抽屉），不跳出应用。
    站内阅读需要登录态，游客点击时先引导登录。 */
const readerRef = ref<InstanceType<typeof ArticleReader> | null>(null)

/** 资讯详情子页（移动端信息流 → 详情）：用于「点评论/转发直接落到对应面板」 */
const detailRef = ref<InstanceType<typeof ArticleDetailPage> | null>(null)
function openArticle(url: string, title?: string) {
  if (!url) return
  if (isGuestMode()) {
    void promptLogin('阅读资讯全文')
    return
  }
  readerRef.value?.open(url, title)
}

interface GalleryImage {
  title: string
  image_url: string
  campus: string
}

/** 初始值直接取模块级缓存：二次进入命中时首帧就是真实内容，不会闪空态 */
const impressionData = ref<ImpressionItem[]>(getCampusImpressionCache() ?? [])

/** 刷新在途态：桌面端「点标题刷新」用，防重复点击（连点会重复打后端） */
const refreshing = ref(false)

function byDateDesc(a: ImpressionItem, b: ImpressionItem) {
  const da = a.date ? Date.parse(a.date) : NaN
  const db = b.date ? Date.parse(b.date) : NaN
  if (Number.isNaN(da) && Number.isNaN(db)) return 0
  if (Number.isNaN(da)) return 1
  if (Number.isNaN(db)) return -1
  return db - da
}

// 去掉公共前缀
function removeCommonPrefix(title: string) {
  const prefixes = ['绵阳城市学院关于', '绵阳城市学院']
  for (const p of prefixes) {
    if (title.startsWith(p)) {
      return title.slice(p.length)
    }
  }
  return title
}

// 去重（按title去重）
function deduplicateByTitle(items: ImpressionItem[]) {
  const seen = new Set<string>()
  return items.filter(item => {
    if (seen.has(item.title)) return false
    seen.add(item.title)
    return true
  })
}

const impression = computed(() => {
  const all = impressionData.value
  const bySource = (s: string) => deduplicateByTitle(all.filter(i => i.source === s).sort(byDateDesc))
  return {
    entries: bySource('jwc_entries'),
    jxdt: bySource('jwc_jxdt'),
    tzgg: bySource('jwc_tzgg'),
    gjxx: bySource('jwc_gjxx'),
    jxjs: bySource('jwc_jxjs'),
    collegeNews: groupCollegeNews(all),
  }
})

function groupCollegeNews(all: ImpressionItem[]): Record<string, ImpressionItem[]> {
  const map: Record<string, ImpressionItem[]> = {}
  for (const i of all.filter(x => x.source === 'college_news')) {
    if (!map[i.college_key!]) map[i.college_key!] = []
    map[i.college_key!].push(i)
  }
  for (const key of Object.keys(map)) map[key].sort(byDateDesc)
  return map
}

/** 卡片上展示的学院新闻条数：2 条足够，再多会把网格行高撑得参差 */
const COLLEGE_NEWS_LIMIT = 2

/** 7 个学院：名称必须与后端 college_key 完全一致，否则取不到新闻（取不到时按空态渲染） */
const collegeCards = [
  { name: '马克思主义学院', url: 'https://mksxy.mycc.edu.cn/', icon: Reading, color: '#e74c3c' },
  { name: '人工智能学院', url: 'https://xdjsxy.mycc.edu.cn/', icon: Monitor, color: '#409eff' },
  { name: '智能制造与工程学院', url: 'https://xdcsjsxy.mycc.edu.cn/', icon: SetUp, color: '#e67e22' },
  { name: '健康与教育学院', url: 'https://xdfw.mycc.edu.cn/', icon: OfficeBuilding, color: '#27ae60' },
  { name: '商学院', url: 'https://jgxy.mycc.edu.cn/', icon: Histogram, color: '#9b59b6' },
  { name: '创意设计学院', url: 'https://cysjxy.mycc.edu.cn/', icon: Collection, color: '#f39c12' },
  { name: '终身教育学院', url: 'https://jxjy.mycc.edu.cn/', icon: School, color: '#1abc9c' },
]

/**
 * 学院新闻取前 N 条。
 * - 每个学院固定取相同条数，配合 .college-card 的 flex 列布局 + .college-list 的
 *   min-height，保证各卡片「图标 / 新闻区 / 进入官网」三段基线对齐，空数据学院也不塌陷；
 * - 条数与日期都在这里一次算完并缓存，模板里只做取值，日期不重复解析；
 * - 不用 `impression.collegeNews[c.name] || []` 直接 v-for：学院名与后端
 *   college_key 对不上时 map 取到 undefined，会得到 0 条而非报错，这里统一兜成 []。
 */
const collegeNewsMap = computed<Record<string, { url: string; title: string; day: string }[]>>(() => {
  const out: Record<string, { url: string; title: string; day: string }[]> = {}
  const grouped = impression.value.collegeNews
  for (const c of collegeCards) {
    out[c.name] = (grouped[c.name] || []).slice(0, COLLEGE_NEWS_LIMIT).map(n => ({
      url: n.url,
      title: n.title,
      day: formatDate(n.date),
    }))
  }
  return out
})

function collegeTopNews(name: string) {
  return collegeNewsMap.value[name] || []
}

// 教务系统入口图标映射
const entryIconMap: Record<string, any> = {
  '教务管理系统': Monitor,
  '课表查询': Calendar,
  '教学校历': DataLine,
  '超星在线学习平台': Reading,
  '教学质量管理平台': TrendCharts,
  '毕业论文管理系统': Document,
  '实习管理系统': Box,
  '实验管理平台': Van,
  '作息时间': Clock,
}

// 获取入口图标
function getEntryIcon(title: string) {
  for (const [key, icon] of Object.entries(entryIconMap)) {
    if (title.includes(key) || key.includes(title)) {
      return icon
    }
  }
  return Monitor
}

// 教务入口配色（桌面端）：整组入口图标统一用中性深灰 #4E5969
// （灰 = 底层系统入口，把彩色权重让给页面里的教学动态/专业分院等内容区）。
// 移动端不吃这里的颜色 —— 移动端是「浅蓝瓷片 + 主入口实心蓝」，配色在样式区 @media 块里。
// 想给某个入口单独提色，只需在 ENTRY_COLOR_MAP 里加一条「标题关键词: 色值」，会覆盖默认灰。
const ENTRY_COLOR_MAP: Record<string, string> = {}
const DEFAULT_ENTRY_COLOR = '#4E5969'

function getEntryColor(title: string) {
  for (const [key, color] of Object.entries(ENTRY_COLOR_MAP)) {
    if (title.includes(key) || key.includes(title)) return color
  }
  return DEFAULT_ENTRY_COLOR
}

// 主入口：教务管理系统（学生 90% 的入口使用都在这一个上）。
// 移动端 6 个瓷片完全同口径，主入口只靠「排在第一位 + 标题字重 600」区分；
// 不给它单独上实心蓝 —— 宫格里一块实心会被读成「当前选中」，那是错的语义。
function isPrimaryEntry(title: string) {
  return title.includes('教务管理系统')
}

// 站内阅读器能渲染的校内静态页（实测：jwc 内容页返回链接清单可读；
// jwgl.mycc.edu.cn / syglxt.mycc.edu.cn 是登录型系统，抓取返回 502，无法内嵌）
function isInAppReadable(url: string) {
  return /^https?:\/\/jwc\.mycc\.edu\.cn\//i.test(url)
}

// 是否只能在新窗口打开：登录型教务/实验系统与站外 SaaS 都无法内嵌
// （学校站点统一设了 X-Frame-Options: SAMEORIGIN，禁止 iframe）
function opensInNewWindow(url: string) {
  return !isInAppReadable(url)
}

// 登录型校内系统（教务/实验平台）：能连上但拿不到未登录内容，只能新窗口打开
function isLoginPortal(url: string) {
  return /^https?:\/\/(jwgl|syglxt)\.mycc\.edu\.cn/i.test(url)
}

function entryHint(url: string) {
  if (isInAppReadable(url)) return '在应用内打开'
  if (isLoginPortal(url)) return '需要登录的校内系统，将在新窗口打开'
  return '站外系统，将在新窗口打开'
}

// 入口点击：可站内阅读的走阅读器，其余交给 <a target="_blank"> 原生行为
// （保留中键/右键"在新标签页打开"）
function onEntryClick(e: { url: string; title: string }, ev: MouseEvent) {
  if (!isInAppReadable(e.url)) return
  ev.preventDefault()
  openArticle(e.url, e.title)
}

// “教务系统入口”网格中不展示的项：课表查询/教学校历/作息时间都是教务处静态工具页，
// 与应用内页面重复。后端 fetch_jwc_entries 已按同样规则过滤，这里再兜一层，
// 保证旧进程/缓存数据带出来的也不会显示（标题与链接双重匹配）
const HIDDEN_ENTRY_TITLES = ['课表查询', '教学校历', '作息时间']
const HIDDEN_ENTRY_PATHS = ['/jwgl/kbcx.htm', '/jwgl/jxxl.htm', '/jwgl/zxsj.htm']

function isHiddenEntry(entry: { title: string; url: string }) {
  const title = entry.title || ''
  const url = (entry.url || '').replace(/\/+$/, '')
  return HIDDEN_ENTRY_TITLES.some(t => title.includes(t)) || HIDDEN_ENTRY_PATHS.some(p => url.endsWith(p))
}

// 入口标题清洗：去掉括号补充说明（“毕业论文(设计)管理系统” → “毕业论文管理系统”）
function cleanEntryTitle(title: string) {
  return (title || '').replace(/[（(][^（）()]*[）)]/g, '').trim()
}

// 入口卡片：统一 3 列网格（6 项正好两行），不再按分组分块展示
const visibleEntries = computed(() =>
  impression.value.entries
    .filter(e => !isHiddenEntry(e))
    .map(e => ({ ...e, title: cleanEntryTitle(e.title) })),
)

// 统一日期格式：MM-DD
// 兼容后端两种写法："2026-10-15"（教务各栏目）与 "2026.04.01"（学院新闻），
// 并且只按「年-月-日」解析：日期中段的 "2026-2027学年" 这类区间不会被误切出 "20-20"。
// 无日期（学院新闻 14 条里 10 条 date 为 null）返回空串，由调用方决定不渲染，
// 避免出现空白占位把条目撑开。
function formatDate(d: string | null) {
  const s = (d || '').trim()
  const m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/)
  if (m) return `${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`
  return ''
}

// 日期邮戳格式：日 + 月
function splitDay(d: string | null) {
  if (!d) return ''
  const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return m[3].replace(/^0/, '')
  return ''
}

function splitMonth(d: string | null) {
  if (!d) return ''
  const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return m[2] + '月'
  return ''
}

const impressionItems = [
  { title: '仪器设备', url: 'https://www.mycc.edu.cn/mcyx/yqsb.htm', icon: SetUp, color: '#e67e22', desc: '学校拥有智能制造、人工智能等现代化实验实训设备，为实践教学提供有力支撑。' },
  { title: '生活条件', url: 'https://www.mycc.edu.cn/mcyx/shtj.htm', icon: HomeFilled, color: '#27ae60', desc: '标准化学生公寓、多个学生食堂与运动场馆，营造舒适便捷的校园生活环境。' },
]

async function loadImpression() {
  try {
    const data = await getImpression()
    impressionData.value = data
    setCampusImpressionCache(data)
  } catch { /* 静默：失败保留已有（可能是缓存）内容，不回写空数组 */ }
}

/**
 * 刷新：强制重取一次，绕过前端 10 分钟缓存。
 * 后端对同一份聚合数据另有 5 分钟内存缓存（过期时后台异步刷新、本次仍返回旧数据），
 * 所以点一下未必立刻拿到全新的外网抓取结果 —— 但足以覆盖「前端缓存把旧数据
 * 锁死 10 分钟」这个更常见的场景，且失败时保持旧内容、不清空页面。
 * 入口：移动端页头的刷新按钮、桌面端点标题。两者都是「重新取一次」而非「重置页面」，
 * 所以不给 ElMessage 提示打扰阅读（状态都收在页头副标题/图标旋转上）。
 */
async function refreshImpression() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await loadImpression()
  } finally {
    refreshing.value = false
  }
}

/** 下拉刷新：重取资讯流并顺带刷新未读（复用现有加载，失败静默） */
async function refreshAll() {
  await loadImpression()
  void refreshUnread()
}

const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

// ---------------- 头部搜索 ----------------

const SEARCH_HOT_KEYWORDS = ['放假', '招聘', '奖学金', '讲座']

/** source 字段 → 中文名：搜索结果每条都标出来源，用户才知道点进去是什么 */
const SOURCE_LABELS: Record<string, string> = {
  jwc_entries: '系统入口',
  jwc_jxdt: '教学动态',
  jwc_tzgg: '通知公告',
  jwc_gjxx: '高教信息',
  jwc_jxjs: '教学建设',
  college_news: '学院动态',
}

interface NewsHit {
  title: string
  url: string
  date: string
  sourceLabel: string
}

const searchVisible = ref(false)
const searchKeyword = ref('')
const searchDone = ref(false)
/** 本页资讯命中（纯前端过滤，不发请求） */
const newsHits = ref<NewsHit[]>([])
/** 知识库命中（仅本页 0 命中时才发起） */
const knowledgeHits = ref<KnowledgeHit[]>([])
const knowledgeLoading = ref(false)

/**
 * 移动端搜索入口：打开全屏搜索子页（CampusSearchPage），不再走对话框 ——
 * 手机上对话框是「半个页面浮着」的形态，与参考的资讯流 App 搜索页差一代；
 * 桌面端维持原对话框（全屏子页是移动端专属版式）。
 */
const searchTarget = ref(false)

/** 搜索页的资讯池：全部栏目合并流（即「推荐」页的口径：剔系统入口与已下线栏目），
 * 并入互动计数、去掉公共前缀 —— 池子规则只在父页维护，搜索页只消费。 */
const searchPool = computed<SearchPoolItem[]>(() =>
  itemsOfTab('recommend').map(i => {
    const s = interactionMap.value[i.url]
    return {
      title: removeCommonPrefix(i.title),
      url: i.url,
      source: i.source,
      sourceLabel: SOURCE_LABELS[i.source] || '资讯',
      date: i.date,
      dateLabel: formatDate(i.date),
      image_url: i.image_url,
      comment_count: s?.comment_count ?? 0,
      view_count: s?.view_count ?? 0,
    }
  }),
)

function openSearch() {
  if (isMobile.value) {
    searchLeaving.value = false
    searchTarget.value = true
    return
  }
  searchVisible.value = true
  // 每次打开都是干净状态：上次的结果留着会让人以为「已经搜过了」
  searchKeyword.value = ''
  searchDone.value = false
  newsHits.value = []
  knowledgeHits.value = []
}

/** 搜索子页点资讯命中：详情子页盖在搜索页上（同为 Teleport 覆盖层，后挂载者在
 * 上层），详情返回后仍停留在搜索页。来源从命中条目自带，不走 mobileFeed 反查 ——
 * 搜索命中的条目不一定在当前分类的信息流里。 */
function openHitFromSearch(url: string, title: string, source: string) {
  detailTarget.value = { url, title, source, from: 'row' }
}

/**
 * 第一层：在本页已加载的资讯里按标题过滤。
 * 直接吃 impressionData（页面已渲染的那份数据），所以「搜得到 = 看得见」，
 * 不会出现搜索结果里有、页面上却找不到的割裂。
 * 移动端额外剔除已下线栏目的条目（MOBILE_HIDDEN_SOURCES）：手机上没有「高教信息」的
 * 列表可看，却能在搜索结果里点进去、且被标成「高教信息」，反而制造新的割裂。
 * 桌面端信息流完整，搜索照旧覆盖全部栏目。
 */
function filterNews(keyword: string): NewsHit[] {
  const kw = keyword.toLowerCase()
  const pool = isMobile.value
    ? impressionData.value.filter(i => !MOBILE_HIDDEN_SOURCES.includes(i.source))
    : impressionData.value
  return pool
    .filter(i => (i.title || '').toLowerCase().includes(kw))
    .map(i => ({
      title: i.title,
      url: i.url,
      date: formatDate(i.date),
      sourceLabel: SOURCE_LABELS[i.source] || '资讯',
    }))
}

/**
 * 第二层：本页 0 命中才兜到知识库（RAG 混合检索，全端可用）。
 * 不做前端空转 —— 本页资讯只有几十条，命中率低是常态，
 * 用户真正想找的「办事问答」在知识库里。
 */
async function runSearch() {
  const keyword = searchKeyword.value.trim()
  if (!keyword) return
  newsHits.value = filterNews(keyword)
  searchDone.value = true
  knowledgeHits.value = []
  if (newsHits.value.length) {
    // 本页已命中，不再打后端：既省一次检索，也避免两段结果互相干扰
    return
  }
  // 游客没有知识库检索权限：只展示本页资讯的本地搜索结果
  if (isGuestMode()) return
  knowledgeLoading.value = true
  try {
    knowledgeHits.value = await searchKnowledge(keyword)
  } catch {
    // 检索失败按「无结果」处理，不弹错打断阅读；下面的空态文案已说明情况
    knowledgeHits.value = []
  } finally {
    knowledgeLoading.value = false
  }
}

function quickSearch(kw: string) {
  searchKeyword.value = kw
  runSearch()
}

/** 点搜索结果：可站内阅读的走阅读器（与页面其它入口一致），其余新窗口打开 */
function openSearchHit(h: NewsHit) {
  if (isInAppReadable(h.url)) {
    openArticle(h.url, h.title)
    searchVisible.value = false
  } else {
    window.open(h.url, '_blank', 'noopener,noreferrer')
  }
}

const galleryImages: GalleryImage[] = [
  { title: '安州校区博润楼', image_url: '/images/campus/安州校区博润楼.jpg', campus: '安州' },
  { title: '安州校区众立楼', image_url: '/images/campus/安州校区众立楼.jpg', campus: '安州' },
  { title: '安州校区博训楼', image_url: '/images/campus/安州校区博训楼.jpg', campus: '安州' },
  { title: '安州校区综合活动馆', image_url: '/images/campus/安州校区综合活动馆.jpg', campus: '安州' },
  { title: '安州校区体育馆', image_url: '/images/campus/安州校区体育馆.jpg', campus: '安州' },
  { title: '安州校区工程训练中心', image_url: '/images/campus/安州校区工程训练中心.jpg', campus: '安州' },
  { title: '安州校区田径运动场', image_url: '/images/campus/安州校区田径运动场.jpg', campus: '安州' },
  { title: '安州校区博文楼', image_url: '/images/campus/安州校区博文楼.jpg', campus: '安州' },
  { title: '安州校区博远楼', image_url: '/images/campus/安州校区博远楼.jpg', campus: '安州' },
  { title: '安州校区博雅楼', image_url: '/images/campus/安州校区博雅楼.jpg', campus: '安州' },
  { title: '游仙校区第一教学楼', image_url: '/images/campus/游仙校区第一教学楼.jpg', campus: '游仙' },
  { title: '游仙校区科技楼', image_url: '/images/campus/游仙校区科技楼.jpg', campus: '游仙' },
  { title: '游仙校区博采溪', image_url: '/images/campus/游仙校区博采溪.jpg', campus: '游仙' },
  { title: '游仙校区行政楼', image_url: '/images/campus/游仙校区行政楼.jpg', campus: '游仙' },
  { title: '游仙校区博识楼', image_url: '/images/campus/游仙校区博识楼.jpg', campus: '游仙' },
  { title: '游仙校区木桥', image_url: '/images/campus/游仙校区木桥.jpg', campus: '游仙' },
  { title: '游仙校区博识楼C区草坪', image_url: '/images/campus/游仙校区博识楼C区草坪.jpg', campus: '游仙' },
  { title: '游仙校区夜景', image_url: '/images/campus/游仙校区夜景.jpg', campus: '游仙' },
  { title: '游仙校区风雨操场', image_url: '/images/campus/游仙校区风雨操场.jpg', campus: '游仙' },
  { title: '游仙校区田径运动场', image_url: '/images/campus/游仙校区田径运动场.jpg', campus: '游仙' },
  { title: '游仙校区篮球场', image_url: '/images/campus/游仙校区篮球场.jpg', campus: '游仙' },
]

/** 校园风光轮播图源：桌面端专属（移动端首屏已改为 Tab + 信息流） */
const carouselImages = computed(() => galleryImages)

/* ==================== 移动端：分类 Tab + 信息流 ==================== */

/**
 * 分类定义。key 直接复用后端的 source 取值，这样切 Tab 只是换一个 filter，
 * 不产生任何网络请求。
 * 'recommend' 是合并流（原「全部」）：所有栏目混排 + 顶部大图轮播，即首屏的推荐位；
 * 'following' 是「关注」：我关注的人发的帖子，数据源是 /community/following（人 → 帖子），
 *   和上面几个「栏目 → 资讯」的分类不是同一套数据，所以整块交给 FollowingFeed 渲染，
 *   这里返回空数组只是为了不参与资讯过滤（轮播同样只属于推荐页，见 heroSlidesOf）。
 * 其余 4 个与桌面端卡片一一对应：教学动态 / 通知公告 / 教学建设 / 学院动态。
 * 「高教信息」不设 Tab：移动端信息流不展示该栏目的内容（见 itemsOfTab），
 * 与桌面端「高教信息」卡片并列的只剩「教学建设」，那条桌面布局保持不变。
 */
type FeedTabKey =
  | 'recommend'
  | 'following'
  | 'community'
  | 'jwc_jxdt'
  | 'jwc_tzgg'
  | 'jwc_jxjs'
  | 'college_news'

const FEED_TABS: { key: FeedTabKey; label: string }[] = [
  { key: 'recommend', label: '推荐' },
  { key: 'following', label: '关注' },
  // 交流社区紧跟在「关注」右边：都是「和我有关的动态」，放在一排的开头位置
  { key: 'community', label: '交流社区' },
  { key: 'jwc_jxdt', label: '教学动态' },
  { key: 'jwc_tzgg', label: '通知公告' },
  { key: 'jwc_jxjs', label: '教学建设' },
  { key: 'college_news', label: '学院动态' },
]

const activeTab = ref<FeedTabKey>('recommend')

/**
 * 移动端信息流不展示的栏目（source 取值）。
 * 「高教信息」（jwc_gjxx）已在移动端下线：分类 Tab 里没有它，
 * 「推荐」合并流里也要一并剔除，否则它会以「高教信息」的来源标签混在首屏，
 * 用户既点不到对应分类、也找不到它在哪 —— 搜得到却翻不到，比不展示更困惑。
 * 桌面端不受影响：桌面卡片直接读 impression.gjxx。
 */
const MOBILE_HIDDEN_SOURCES: string[] = ['jwc_gjxx']

/** 某个分类下的条目（已去重 + 按日期倒序） */
function itemsOfTab(key: FeedTabKey): ImpressionItem[] {
  // 关注流的数据源是「人 → 帖子」（/community/following），不在这份资讯数据里，
  // 整块由 FollowingFeed 渲染；这里返回空数组，避免它被当成一个永远匹配不到的空栏目。
  if (key === 'following') return []

  // 交流社区不是资讯栏目：帖子来自 /api/community/posts，整块由 CommunityFeed 渲染，
  // 不参与下面的资讯过滤（否则 source 永远匹配不到，会一直被当成空分类）。
  if (key === 'community') return []

  const all = impressionData.value.filter(i => !MOBILE_HIDDEN_SOURCES.includes(i.source))
  if (key === 'recommend') {
    // 合并流：入口项（系统入口）不是资讯，剔除；其余全部参与排序
    return deduplicateByTitle(all.filter(i => i.source !== 'jwc_entries')).sort(byDateDesc)
  }
  return deduplicateByTitle(all.filter(i => i.source === key)).sort(byDateDesc)
}

/** Tab 列表（只含 key/label）：条数不放在 Tab 上 —— 6 个分类 × 数字会把后面的 Tab 挤出首屏 */
const mobileTabs = computed(() => FEED_TABS)

/**
 * 切换分类。
 * 切完立刻回到列表顶部，用瞬时跳转而不是平滑滚动 ——
 * 平滑滚动和横向换页动画叠在一起，看起来就像「旧分类自己在往上爬」。
 */
function switchTab(key: FeedTabKey) {
  activeTab.value = key
  // 切分类后回到列表顶部：否则停在上一分类的滚动位置，看起来像「没反应」
  const scroller = document.querySelector('.campus-page')
  if (scroller instanceof HTMLElement) scroller.scrollTop = 0
}

/**
/**
 * 点 Tab：内容横向滑过去，与手指切换同一段 200ms。
 * 相邻与跨分类共用一条两页轨道（出发页 + 目标页一次对滑），不逐页播。
 * 动画本体在 SwipePager.slideTo()，本页只决定「切到哪一页 / 要不要收掉残留动画」。
 */
function onTabClick(key: FeedTabKey) {
  if (!pagerRef.value) {
    // 桌面端没有分页轨道（Tab 行本身也只在移动端渲染，这里只是兜底）
    if (key !== activeTab.value) switchTab(key)
    return
  }
  if (key === activeTab.value) {
    // 已在目标分类：只收掉可能还在跑的拖动 / 吸附 / 换页动画
    pagerRef.value.cancel()
    return
  }
  pagerRef.value.slideTo(key)
}

/** SlidingTabs 的 select 载荷是 string（组件不认识本页的分类联合类型），这里收窄回来 */
function onTabSelect(key: string) {
  onTabClick(key as FeedTabKey)
}

/** 分页组件回报「当前页变了」（拖动吸附完成、或点 Tab 换页出发那一刻），落到分类状态上 */
function onPagerChange(key: string) {
  switchTab(key as FeedTabKey)
}

/* ==================== 移动端：卡片分页（跟手切换分类） ==================== */

/**
 * 分页轨道本体在 components/common/SwipePager.vue：
 * 拖动 1:1 跟手、松手按位移 / 速度吸附或回弹、点 Tab 两页对滑、邻居页的挂载与卸载，
 * 都在组件里；本页只留两件事：
 *   ① 告诉轨道「有哪些页」并给每页提供内容（pageDataMap / pagerPages）；
 *   ② 把组件的即时状态转给 SlidingTabs，让滑条与文字染色跟手指严格同步。
 */
const pagerRef = ref<InstanceType<typeof SwipePager> | null>(null)

/** 全部分类的 key（有序）：组件据此判断左右邻居与首尾边界 */
const feedTabKeys = FEED_TABS.map(t => t.key)

/**
 * 每个分类的页数据（items / slides）。
 * 整表一次算好、只在资讯数据变化时重算 —— 页对象（items / slides 数组）引用因此稳定，
 * 模板里的 v-memo 才能在拖动（每帧重渲染）期间真正命中，跳过三页 DOM 的 diff。
 */
const pageDataMap = computed(() => {
  const map = {} as Record<FeedTabKey, { items: FeedItem[]; slides: HeroSlide[] }>
  FEED_TABS.forEach((t) => {
    map[t.key] = { items: feedItemsOf(t.key), slides: heroSlidesOf(t.key) }
  })
  return map
})

/** 轨道上的一页：某个分类的完整内容（「推荐」页额外带顶部大图轮播，「关注」页为空态） */
interface PagerPage {
  key: FeedTabKey
  items: FeedItem[]
  slides: HeroSlide[]
}

/**
 * 轨道上正在渲染的页：静止 = 当前页，拖动 / 吸附 = 加上左右邻居，点 Tab 换页 = 出发页 + 目标页。
 * 具体摆哪几页由组件算（renderedPages），本页按 key 取数据即可 ——
 * 邻居页只在拖动开始时挂载，静止时只渲染当前页，页面高度不被邻居撑高。
 */
const pagerPages = computed<PagerPage[]>(() => {
  const keys = (pagerRef.value?.renderedPages ?? [activeTab.value]) as FeedTabKey[]
  return keys.map(key => ({ key, ...pageDataMap.value[key] }))
})

/**
 * 组件状态 → SlidingTabs 的输入：
 *   · progress：拖动时 = |位移| / 页宽，滑条与卡片严格同步；
 *     点 Tab 换页时为 null —— 那一趟位移只为推动页面轨道，滑条已直接落到目标位、
 *     交给 CSS 过渡，不能再按位移插值（否则跨分类点一下会先滑到隔壁再折回）；
 *   · direction：往左拖 = 下一项，往右拖 = 上一项；
 *   · dragging / resetting / sliding：逐帧写入时关掉过渡的三个状态位。
 * 组件用 defineExpose 暴露的是 computed ref，父级模板取值时自动解包。
 */
const pagerState = computed(() => ({
  progress: pagerRef.value?.progress ?? null,
  direction: pagerRef.value?.direction ?? 0,
  dragging: pagerRef.value?.dragging ?? false,
  resetting: pagerRef.value?.resetting ?? false,
  sliding: pagerRef.value?.sliding ?? false,
}))

/**
 * 相对时间：昨天 / 今天 / MM-DD / 更早。
 * 参考图的信息流用「昨天21:57」这种相对表述，比纯日期更符合「看新鲜事」的心理。
 * 无日期的条目（部分学院新闻 date 为 null）返回空串，由模板不渲染。
 */
function relativeTime(d: string | null): string {
  const s = (d || '').trim()
  const m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/)
  if (!m) return ''
  const target = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  target.setHours(0, 0, 0, 0)
  const diffDays = Math.round((today.getTime() - target.getTime()) / 86400000)
  if (diffDays <= 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays === 2) return '前天'
  if (diffDays < 7) return `${diffDays} 天前`
  return `${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`
}

interface FeedItem {
  title: string
  url: string
  image_url: string | null
  timeLabel: string
  sourceLabel: string
  /** 来源栏目 key（jwc_jxdt / jwc_tzgg …）：详情页用它显示顶栏副标题与来源标签 */
  source: string
  comment_count: number
  view_count: number
  /** 推荐流混排用：article = 资讯（默认），post = 交流社区帖子 */
  kind?: 'article' | 'post'
  /** 帖子才有：点行时用它打开 PostDetailPage */
  post_id?: number
}

/* ---------- 交流社区：帖子流 / 详情由 CommunityFeed、PostDetailPage 承担 ----------
   本页只留三件事：点开详情、发布后刷新列表、深链（?post=）落地。 */
const communityFeedRef = ref<InstanceType<typeof CommunityFeed> | null>(null)
const desktopCommunityFeedRef = ref<InstanceType<typeof CommunityFeed> | null>(null)
/** 关注流：「关注」页签那一页（头像条 + 动态卡片），发帖 / 点赞 / 关注变化后刷新 */
const followingFeedRef = ref<InstanceType<typeof FollowingFeed> | null>(null)
const communityDetailId = ref(0)
/** 帖子详情是否在退场中：与资讯详情同义，用来决定下层什么时候归位 */
const postDetailLeaving = ref(false)

function openPostDetail(post: CommunityPost) {
  postDetailLeaving.value = false
  communityDetailId.value = post.id
}

/** 推荐流里点一条帖子：与社区页签里点开同一条走同一个详情子页 */
function openPostDetailById(id: number) {
  postDetailLeaving.value = false
  communityDetailId.value = id
}

/** 推荐流里的一行：帖子进社区详情子页，资讯仍进资讯详情子页 */
function openFeedItem(item: FeedItem) {
  if (item.kind === 'post' && item.post_id) {
    openPostDetailById(item.post_id)
    return
  }
  openDetail(item.url, item.title)
}

/* ---------- 推荐流混排：资讯之间插入社区帖子 ----------
   为什么是「插位」而不是统一打分：资讯没有点赞 / 评论这类可比热度，
   塞进同一套分数里会被帖子整体挤到后面；而帖子有自己的打分（后端 /community/recommend），
   这里只负责按密度把它们摆进固定的位置 —— 也是贴吧、小红书那类信息流的做法。 */
const recommendedPosts = ref<CommunityPost[]>([])
/** 每 3 条资讯插 1 条帖子（约 25%），社区内容能被看见，又不至于盖过校内资讯 */
const POST_MIX_EVERY = 3
/** 开头 2 条先给资讯：权威信息不该被社区内容挤出首屏 */
const POST_MIX_LEAD = 2

async function loadRecommendedPosts() {
  if (isGuestMode()) { recommendedPosts.value = []; return }
  try {
    recommendedPosts.value = await getRecommendedPosts(12)
  } catch {
    // 静默：推荐位是增强功能，取不到就退回纯资讯流，不留空位也不报错
    recommendedPosts.value = []
  }
}

function postToFeedItem(p: CommunityPost): FeedItem {
  return {
    title: p.title,
    // community:<id> 只作唯一的行 key，不会被当成资讯链接去开阅读器
    url: `community:${p.id}`,
    image_url: p.images?.[0] ?? null,
    timeLabel: relativeTime(p.created_at),
    sourceLabel: `${p.author_name || '同学'} · ${p.category}`,
    source: 'community_post',
    comment_count: p.comment_count,
    view_count: p.view_count,
    kind: 'post',
    post_id: p.id,
  }
}

function mixCommunityPosts(articles: FeedItem[]): FeedItem[] {
  const posts = recommendedPosts.value
  if (!posts.length) return articles
  const out: FeedItem[] = []
  let pi = 0
  let sincePost = 0
  articles.forEach((a, i) => {
    out.push(a)
    sincePost++
    if (i < POST_MIX_LEAD) return
    if (sincePost >= POST_MIX_EVERY && pi < posts.length) {
      out.push(postToFeedItem(posts[pi]))
      pi++
      sincePost = 0
    }
  })
  return out
}

/** 开始退场：下层立刻从 -30% 归位，与子页 0.3s 右滑同拍（等 after-leave 就晚了 300ms） */
function onPostDetailLeaving() {
  postDetailLeaving.value = true
}

function onPostDetailClosed() {
  communityDetailId.value = 0
  postDetailLeaving.value = false
}

/** 详情里点赞 / 关注 / 评论后，列表上的计数跟着变（不整页重拉，只刷一次第一页成本也不高，
 *  这里选择只重拉第一页：帖子流是「最新优先」，重拉后顺序与真实数据一致） */
function onPostUpdated() {
  void communityFeedRef.value?.refresh()
  void desktopCommunityFeedRef.value?.refresh()
  // 关注流也要重拉：在详情里点了赞 / 关注了作者，回到列表计数与「关注了谁」都得对得上
  void followingFeedRef.value?.refresh()
  // 推荐流里的帖子行也重拉：刚评论/点赞完返回，计数得对得上（顺序微调可接受）
  void loadRecommendedPosts()
}

function onPostDeleted() {
  onPostUpdated()
}

/**
 * 一条分类的完整信息流（含互动计数）。
 * 标题去掉「绵阳城市学院」等公共前缀 —— 移动端一行只有十几个字，
 * 前缀会把真正的信息挤到第二行甚至截断。
 * 互动数字来自 interactionMap（默认 0）：没被任何同学互动过的文章不额外建记录，
 * 所以「有计数」本身就是一条值得显示的信息。
 * 卡片分页里每一页都走这里取数，口径与当前页完全一致。
 */
function feedItemsOf(key: FeedTabKey): FeedItem[] {
  const items = itemsOfTab(key).map(i => {
    const s = interactionMap.value[i.url]
    return {
      title: removeCommonPrefix(i.title),
      url: i.url,
      image_url: i.image_url,
      timeLabel: relativeTime(i.date),
      sourceLabel: SOURCE_LABELS[i.source] || '资讯',
      source: i.source,
      comment_count: s?.comment_count ?? 0,
      view_count: s?.view_count ?? 0,
    }
  })
  // 只有「推荐」页混入社区帖子；其余分类是纯栏目流，插进去只会让人找不到规律
  return key === 'recommend' ? mixCommunityPosts(items) : items
}

/** 当前分类的信息流（详情页取来源、页面渲染都读这一份） */
const mobileFeed = computed<FeedItem[]>(() => feedItemsOf(activeTab.value))

/**
 * 信息流空态文案。
 * 「关注」页签由 FollowingFeed 自己渲染（空态文案更细：没关注人 / 关注的人没发帖），
 * 走不到这里；留着这句是为了模板里 else 分支的兜底不出现空白。
 * 其余分类沿用原文案；「推荐」几乎不会为空，也按普通分类处理，不额外造一句。
 */
function emptyTextOf(key: FeedTabKey): string {
  return key === 'following' ? '还没有关注的内容' : '该分类暂无内容'
}

/* ==================== 移动端：大图轮播 ==================== */

interface HeroSlide {
  title: string
  url: string
  image_url: string
  tagLabel: string
}

/** 「推荐」Tab 的兜底图：全部资讯里一张带图的都没有时用（本地校园风光，不依赖外网） */
const HERO_FALLBACK_IMAGES = [
  '/images/campus/游仙校区博识楼.jpg',
  '/images/campus/安州校区博润楼.jpg',
  '/images/campus/游仙校区夜景.jpg',
  '/images/campus/安州校区综合活动馆.jpg',
]

/**
 * 轮播最多张数。5 张 ≈ 一份「首屏推荐」的量；再多用户也不会看完，
 * 反而把信息流挤到第一屏之外。
 */
const HERO_MAX = 5

/**
 * 某个分类顶部的大图轮播数据。只有「推荐」分类有图，其余分类（含「关注」）返回空数组（纯信息流）。
 * 规则：
 *  ① 取全部资讯里**真带图**的条目（按日期倒序）—— 图与标题都来自资讯本身，
 *     点进去就是这篇资讯，这是最有价值的轮播形态；
 *  ② 一张带图的都没有（教学动态抓取失败 / 首次加载未完成）→ 用本地校园风光兜底，
 *     标题用资讯标题，保证首屏不留一块空白，也不影响点击进阅读器。
 * 纯前端计算：切 Tab 不产生任何请求。
 */
function heroSlidesOf(key: FeedTabKey): HeroSlide[] {
  // 非「推荐」分类：不渲染轮播（模板 v-if 已拦截，这里返回空数组兜底）
  if (key !== 'recommend') return []

  const items = itemsOfTab('recommend')

  // ① 真带图资讯
  const withImage = items.filter((i): i is ImpressionItem & { image_url: string } => !!i.image_url)
  if (withImage.length) {
    return withImage.slice(0, HERO_MAX).map(i => ({
      title: removeCommonPrefix(i.title),
      url: i.url,
      image_url: i.image_url,
      tagLabel: SOURCE_LABELS[i.source] || '资讯',
    }))
  }

  // ② 图文皆无：校园风光兜底（标题沿用资讯标题，仍是可点的资讯）
  return items.slice(0, HERO_MAX).map((i, idx) => ({
    title: removeCommonPrefix(i.title),
    url: i.url,
    image_url: HERO_FALLBACK_IMAGES[idx % HERO_FALLBACK_IMAGES.length],
    tagLabel: SOURCE_LABELS[i.source] || '资讯',
  }))
}

/** 轮播图点击：有 url 就进站内阅读器（兜底风光图也带资讯 url，同样可点） */
function openHeroSlide(s: HeroSlide) {
  if (s.url) openArticle(s.url, s.title)
}

/* ---------- 大图轮播：按住拖动切换（Pointer Events，鼠标 / 触屏同一套逻辑） ----------
   el-carousel 自带的触屏滑动只在真正的 touch 事件上生效：桌面端鼠标拖不动，
   且它一滑就把随后的点击「按惯性」吞掉。这里补一层完全自管的拖拽：
     · 按下即暂停自动轮播（避免边拖边自己翻页）；
     · 水平位移超过阈值（10px）才进入「拖动」态，轨道随手指跟手偏移（带阻尼）；
     · 松手按位移与速度决定「翻页」还是「回弹」—— 慢拖过半才翻，快甩超过阈值速度也翻；
     · 全程没超过阈值 = 一次点击，交给 <a> 的 click 进阅读器；
       超过阈值则吞掉随后的 click，避免「拖完手一松就点进了文章」。
   竖直方向交给页面滚动（touch-action: pan-y），不拦截。
   自动轮播用受控 prop `:autoplay` 启停：Element Plus 的 pause/start 不在组件实例上暴露，
   改 props 会触发内部 watch 正确暂停 / 重启定时器。 */
const heroCarouselRef = ref<InstanceType<typeof ElCarousel> | null>(null)
const heroAutoplay = ref(true)
const heroDragging = ref(false)
/** 补完动画结束后的那一帧：把轨道偏移静默归零（关过渡，否则会再弹回一次） */
const heroResettingTrack = ref(false)
/** 当前页序号：只用来点亮自己画的指示点（el-carousel 的 indicators 已关闭） */
const heroIndex = ref(0)

function onHeroIndexChange(index: number) {
  heroIndex.value = index
}

/**
 * 函数式 ref：轮播渲染在分页的 v-for 页面里，字符串 ref 会被收成数组，
 * next / prev 就取不到了；这里直接记住唯一的轮播实例（只有「推荐」页有图）。
 * 实例（重新）挂载时把指示点序号归零：轮播从第 1 张开始，点也要跟着归零。
 */
function setHeroCarouselRef(el: unknown) {
  const inst = (el as InstanceType<typeof ElCarousel> | null) || null
  if (inst && inst !== heroCarouselRef.value) heroIndex.value = 0
  heroCarouselRef.value = inst
}
/** 拖动中实时的水平位移（px），模板里绑到轮播容器上做跟手偏移 */
const heroDragX = ref(0)
/** 阈值（px）：低于它算点击，不算拖动 */
const HERO_DRAG_THRESHOLD = 10
/** 速度阈值（px/ms）：快甩时不用拖过半也能翻页 */
const HERO_FLING_VELOCITY = 0.4

interface HeroDragState {
  pointerId: number
  startX: number
  startY: number
  lastX: number
  lastTime: number
  active: boolean   // 是否已越过阈值、进入拖动
  locked: boolean   // 已判定为纵向滚动，本次手势不再管
}
let heroDrag: HeroDragState | null = null
/** 上一次手势是拖动（而非轻点）：松手后紧随的 click 要吞掉，否则一拖完就点进了文章 */
let heroSuppressClick = false

/** 暂停 / 恢复自动轮播 */
function pauseHeroAutoplay() {
  heroAutoplay.value = false
}
function resumeHeroAutoplay() {
  // 延后一拍恢复：先让 el-carousel 完成翻页过渡，避免过渡途中被定时器打断
  window.setTimeout(() => { heroAutoplay.value = true }, 60)
}

function heroSwipe(direction: 'prev' | 'next') {
  const carousel = heroCarouselRef.value
  if (!carousel) return
  direction === 'next' ? carousel.next() : carousel.prev()
}

function onHeroPointerDown(e: PointerEvent) {
  // 只处理主键 / 单指；右键与双指（缩放）不接管
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (!e.isPrimary) return
  // 只认「从图片上按下」：底部指示点属于轮播容器但不属于图片，点它是切页，
  // 不应该被当成一次拖动的起点（否则松手时会再翻一次页）。
  const target = e.target as HTMLElement | null
  if (!target?.closest('.hero-slide')) return
  heroSuppressClick = false
  const now = Date.now()
  heroDrag = {
    pointerId: e.pointerId,
    startX: e.clientX,
    startY: e.clientY,
    lastX: e.clientX,
    lastTime: now,
    active: false,
    locked: false,
  }
  pauseHeroAutoplay()
}

function onHeroPointerMove(e: PointerEvent) {
  const d = heroDrag
  if (!d || d.pointerId !== e.pointerId || d.locked) return
  const dx = e.clientX - d.startX
  const dy = e.clientY - d.startY

  // 未越过阈值：先定方向。纵向为主 → 交还页面滚动，本次手势彻底放弃
  if (!d.active) {
    if (Math.abs(dy) > HERO_DRAG_THRESHOLD && Math.abs(dy) > Math.abs(dx)) {
      d.locked = true
      heroDragX.value = 0
      resumeHeroAutoplay() // 没有翻页意图，恢复自动轮播
      return
    }
    if (Math.abs(dx) <= HERO_DRAG_THRESHOLD) return
    d.active = true
    heroDragging.value = true
    // 捕获指针：手指滑出轮播区域（甚至滑出窗口）也不丢 up 事件
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  d.lastX = e.clientX
  d.lastTime = Date.now()
  // 跟手偏移：0.72 阻尼，松手时回弹 / 翻页的手感不会「甩得太远」
  heroDragX.value = dx * 0.72
}

function onHeroPointerUp(e: PointerEvent) {
  const d = heroDrag
  heroDrag = null
  if (!d || d.pointerId !== e.pointerId) return

  const wasActive = d.active && !d.locked
  const dx = e.clientX - d.startX
  const dt = Math.max(1, Date.now() - d.lastTime)
  const velocity = (e.clientX - d.lastX) / dt // px/ms，右正左负

  if (!wasActive) {
    // 只是轻点：没有位移，无需过渡，直接归零
    heroDragX.value = 0
    heroDragging.value = false
    resumeHeroAutoplay()
    return
  }

  // 拖动过：吞掉随后那次 click（否则松手就等于点了文章）
  heroSuppressClick = true

  const width = (e.currentTarget as HTMLElement)?.clientWidth || window.innerWidth || 320
  const passedHalf = Math.abs(dx) > width / 2
  // 快甩：速度方向必须与总位移方向一致，避免「先拖过去再甩回来」被误判
  const flingNext = velocity < -HERO_FLING_VELOCITY && dx < 0
  const flingPrev = velocity > HERO_FLING_VELOCITY && dx > 0
  const goNext = dx < 0 && (passedHalf || flingNext)
  const goPrev = dx > 0 && (passedHalf || flingPrev)

  if (goNext || goPrev) {
    // 翻页：只让 el-carousel 自己动。
    //
    // 关键点是「跟手偏移必须先瞬时归零、且不能产生动画」，否则会变成两段动画叠加：
    //   ① 我们的 transform 把图片从当前偏移（如 -0.4w）继续推到 ∓图宽
    //   ② el-carousel 同时把新页从另一侧推到 translateX(0)
    // 两者叠加 → 画面多走一段、时长也不一致，观感就是「滑到位后又慢放一遍」。
    //
    // 做法：先设 is-resetting（关掉我们的过渡）并把偏移归零，让容器**瞬间**回到
    // 标准起点；再调用 next/prev，由组建自己的 .4s 过渡完成翻页。
    // 归零与翻页在同一帧里提交，浏览器绘制的第一帧就已经是「偏移 0 + 翻页过渡进行中」，
    // 所以看不到归零那一下。
    heroResettingTrack.value = true
    heroDragX.value = 0
    if (goNext) heroSwipe('next')
    else heroSwipe('prev')
    // 等这两步渲染完（下一帧），再撤掉 reset 标记，恢复常态过渡供下次使用
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { heroResettingTrack.value = false })
    })
    heroDragging.value = false
    resumeHeroAutoplay()
    return
  }

  // 回弹：没有翻页，只让图片从当前偏移滑回 0（这一条是唯一由我们自己动画的路径）
  heroDragX.value = 0
  heroDragging.value = false
  scheduleHeroTrackReset()
  resumeHeroAutoplay()
}

/**
 * 回弹动画结束后复位偏移（回弹是唯一由我们自己动画的路径，时长用自己的 360ms）。
 * 其实回弹的目标值就是 0，过渡结束后的「复位」是幂等的；保留这个定时器只为
 * 在过渡结束后清掉 will-change，避免长期占用合成层。
 */
const HERO_TRACK_SETTLE_MS = 360
let heroTrackResetTimer: number | undefined

function scheduleHeroTrackReset() {
  window.clearTimeout(heroTrackResetTimer)
  heroTrackResetTimer = window.setTimeout(() => {
    heroDragX.value = 0
  }, HERO_TRACK_SETTLE_MS + 30)
}

function onHeroPointerCancel() {
  // 被系统打断（来电、手势返回、双指缩放）：从当前位置滑回，不翻页
  heroDrag = null
  heroDragX.value = 0
  heroDragging.value = false
  resumeHeroAutoplay()
}

/** 幻灯片点击：拖动过就只吞掉这次 click，正常轻点才进阅读器 */
function onHeroSlideClick(e: MouseEvent, s: HeroSlide) {
  e.preventDefault()
  if (heroSuppressClick) {
    heroSuppressClick = false
    return
  }
  openHeroSlide(s)
}

/** 拖动时禁止原生拖图（否则会拖出一个半透明图片幽灵盖住轮播） */
function onHeroSlideDragStart(e: DragEvent) {
  e.preventDefault()
}

/* ==================== 移动端：资讯详情子页 / 互动计数 ==================== */

/**
 * 当前打开的文章（v-if 控制详情子页挂载）。
 * from 记录入口来源：'comment' / 'repost' 是信息流行尾小按钮点的，
 * 详情页打开后要直接把对应面板递到用户面前，省掉一次「再点一下」。
 */
const detailTarget = ref<{ url: string; title: string; source: string; from: 'row' | 'comment' | 'repost' } | null>(null)

/**
 * 底部悬浮导航的去留，按子页类型分两套 —— 这是本页最容易改错的一处。
 *
 * ① 全屏子页（搜索 / 详情 / 阅读器）：**不登记隐藏**，让胶囊留在 DOM 里，
 *    由下面的 useSubpagePush 推着一起走（-30%），与消息页会话层同一套。
 *    它们都是 SubPageShell 的 fixed 整屏覆盖层（z-index 2600 > 胶囊 1000），
 *    滑到位后自己就把胶囊盖住了；反过来一打开就 v-if 卸掉，会在子页推开的
 *    同一帧凭空挖掉屏幕底部一块（内容还在原地、导航已经没了），比「被盖住」割裂得多。
 * ② 互动消息（el-drawer 全屏抽屉）：仍登记隐藏。它是从底部/侧边弹出的独立抽屉层，
 *    不是本页的「下一层」，让胶囊跟着页面位移没有意义。
 */
useMobileSubPage(computed(() => isMobile.value && forumInboxOpen.value))

/** 站内阅读器的开关（由 ArticleReader 的 visible-change 通报）：
 *  它是 Teleport 到 body 的覆盖层，本页拿不到它的 visible，只能靠事件同步。 */
const readerOpen = ref(false)

/**
 * 子页打开时下层页面让位（-30%），与子页滑入同一条 0.3s 曲线 —— 即个人中心
 * 「编辑资料」那套（见 animations.css 的 .subpage-underlay）。
 * 只算真正的全屏子页：搜索页 / 详情 / 阅读器。论坛信箱是半屏面板，不推页面。
 * 移动端限定：桌面端这几个子页同样是整屏覆盖层，但没有底部导航要躲，
 * 下层位移只会让桌面观感变廉价（与 page-card 的断点划分同一个道理）。
 */
/**
 * 子页「退场中」：从开始滑出（close() 那一刻）到卸载完成（after-leave）。
 *
 * campusPushed 认的是**语义可见性** = 已挂载 && 不在退场中，而不是挂载态。
 * 挂载态要等 after-leave 才翻假：子页 300ms 已经滑出屏幕了，下层还钉在 -117
 * 一动不动，等子页卸载完才开始 300ms 归位 —— 中间那段静止就是「返回卡一下」。
 * 换成退场开始即归位后，两者的 0.3s 同拍走完，返回是一气呵成的。
 */
const searchLeaving = ref(false)
const detailLeaving = ref(false)

/**
 * 详情 → 阅读器的接力标记。
 * 「阅读全文」是同一层的推进（详情收起、阅读器展开），下层不该跟着回位再推回去；
 * 所以这条路径下退场不算「语义关闭」，一直保持让位，由阅读器接管。
 */
let detailHandoffToReader = false

const campusPushed = computed(
  () =>
    isMobile.value &&
    ((searchTarget.value && !searchLeaving.value) ||
      (!!detailTarget.value && !detailLeaving.value) ||
      // 帖子详情与资讯详情是同一层的全屏子页，让位规则必须一致
      (!!communityDetailId.value && !postDetailLeaving.value) ||
      readerOpen.value),
)
// 布局层的底部胶囊跟着一起走（它不在本页里，只能靠全局登记）
useSubpagePush(campusPushed)

/**
 * 互动计数表：url → 计数 + 当前用户是否点赞。
 * 组件每次导航都会重建，所以这份表放在**模块级**作用域（与 impression 缓存同理），
 * 返回列表时计数器不会闪回 0；详情页里的改动通过 onDetailUpdated 回写。
 */
const interactionMap = ref<Record<string, CampusArticleInteract>>({})

/** 已在途的计数请求：切分类连续触发时只保留最后一次结果，避免旧响应覆盖新数据 */
let interactionReqSeq = 0

/**
 * 拉取当前分类可见文章的互动计数。
 * 用批量接口一次请求补齐整屏（/campus/interactions 接收 url 列表），
 * 若逐条请求，一个分类 20 条就是 20 个请求 —— 这在手机上很容易把首屏拖成好几秒。
 * 失败静默：计数只是附加信息，拿不到就按 0 显示，不能因此让资讯流报错。
 */
async function loadInteractions(urls: string[]) {
  const targets = urls.filter(u => !!u)
  if (!targets.length) return
  const seq = ++interactionReqSeq
  try {
    const res = await getArticleInteractions(targets)
    // 过期的响应直接丢弃：用户可能已经切到别的分类了
    if (seq !== interactionReqSeq) return
    interactionMap.value = { ...interactionMap.value, ...res }
  } catch { /* 静默：计数拿不到不影响阅读 */ }
}

/** 详情页只回传计数字段（不含标题/来源），合并时与已有记录取并集 */
type DetailUpdatedPayload = Pick<
  CampusArticleInteract,
  'url' | 'like_count' | 'favorite_count' | 'comment_count' | 'repost_count' | 'view_count' | 'liked' | 'favorited'
>

/** 把详情页回传的最新计数合并回信息流（点赞 / 评论 / 转发都会走这里） */
function onDetailUpdated(payload: DetailUpdatedPayload) {
  const prev = interactionMap.value[payload.url]
  interactionMap.value = {
    ...interactionMap.value,
    [payload.url]: { ...(prev || {}), ...payload } as CampusArticleInteract,
  }
}

/**
 * 打开详情子页。
 * - from = 'row'：整行点击，正常落到详情首屏；
 * - from = 'comment' / 'repost'：信息流行尾的小按钮，详情页挂载后由 openAnd() 直接把
 *   输入框聚焦 / 转发面板弹出来 —— 用户点「评论」的意图很明确，不该还要在详情里再点一次。
 */
function openDetail(url: string, title?: string, from: 'row' | 'comment' | 'repost' = 'row') {
  if (!url) return
  // 来源栏目从信息流项里取：详情页要用它显示顶栏副标题与来源标签
  const source = mobileFeed.value.find(f => f.url === url)?.source || ''
  detailLeaving.value = false
  detailTarget.value = { url, title: title || '', source, from }
  if (from === 'row') return
  const action = from
  // 等 v-if 把子组件挂上去（下一帧），再让它执行打开后的动作
  nextTick(() => {
    if (detailTarget.value?.url === url) detailRef.value?.openAnd(url, action)
  })
}

/**
 * 关详情子页。
 * 退场动画在子页内部播（全局 .subpage 的 300ms 右滑）：它把 visible 置 false 后播完才发
 * closed，父页那时再卸载。若这里立刻把 detailTarget 置空，整棵子树（含 Transition）
 * 会当场被卸载，退场动画根本没机会播 —— 只剩进场、没有出场。
 */
function closeDetail() {
  detailRef.value?.close()
}

/**
 * 子页开始退场（详情页 close() 里发的 close 事件）：
 * 立刻把下层从让位态放回来，与子页滑出同一条 0.3s —— 等 after-leave 就晚了 300ms。
 * 「阅读全文」那种层内接力不在此列，见 detailHandoffToReader。
 */
function onDetailLeaving() {
  if (detailHandoffToReader) return
  detailLeaving.value = true
}

/** 子页退场播完：真正卸载，并把详情里改过的互动数同步回信息流 */
function onDetailClosed() {
  detailTarget.value = null
  detailLeaving.value = false
  interactionMap.value = { ...interactionMap.value }
}

/** 搜索子页同理：开始退场就让下层归位，播完再卸载 */
function onSearchLeaving() {
  searchLeaving.value = true
}

function onSearchClosed() {
  searchTarget.value = false
  searchLeaving.value = false
}

/**
 * 详情子页点「阅读全文」：正文不在详情页渲染，交给站内阅读器（ArticleReader）。
 * 先关详情再开阅读器：两者都是整页覆盖层，同时挂载会互相抢 body 滚动锁与 z-index；
 * 先收起讨论页、露出阅读器，视觉上是「讨论 → 阅读」的一次正常推进，不会叠层。
 *
 * 下层这次保持让位（不回位再推回去）：两条都是「第一层」的子页，
 * 中间回位会闪一下；由阅读器接管 is-subpushed 直到它关闭。
 */
function onDetailRead(url: string) {
  const title = detailTarget.value?.title || ''
  detailHandoffToReader = true
  closeDetail()
  nextTick(() => {
    openArticle(url, title)
    detailHandoffToReader = false
  })
}

/**
 * 为轨道上可见的页面（当前 + 拖动时挂载的邻居）补齐互动计数。
 * 只为「正在渲染」的这批文章取数：邻居页一旦挂载，计数就不会在翻到它之后才跳出来。
 * watch immediate 保证首屏（默认「推荐」）也会拉，不用在 onMounted 里再写一遍。
 */
watch(
  () => pagerPages.value.map(p => p.items.map(i => i.url).join(',')).join('|'),
  () => {
    if (!isMobile.value) return
    void loadInteractions(pagerPages.value.flatMap(p => p.items.map(i => i.url)))
  },
  { immediate: true },
)

onMounted(() => {
  // 推荐流要混入社区帖子：与资讯并行拉，失败时自动退回纯资讯流
  void loadRecommendedPosts()
  const tabParam = route.query.tab
  // 旧链接兜底：收藏 Tab 已下沉到个人中心，历史地址带 ?tab=favorites 的改送个人中心收藏页
  if (tabParam === 'favorites') {
    void router.replace({ path: '/student/profile', query: { page: 'favorites' } })
    return
  }
  if (typeof tabParam === 'string' && FEED_TABS.some(t => t.key === tabParam)) {
    activeTab.value = tabParam as FeedTabKey
  }
  // 深链：工作台 / 消息里的帖子入口都会带 ?post=<id>，落地即开详情
  openDeepLinkedPost()
  // 本页组件在每次导航时都会被重建（StudentLayout 未用 keep-alive），
  // 因此不能用「组件是否已挂载」来判断要不要加载，只能看模块级缓存：
  // - 命中缓存（10 分钟内已加载过）→ 直接复用，不发请求，页面首帧即真实内容，不闪；
  // - 未命中 → 拉取一次并写回缓存，供下次进入复用。
  const cached = getCampusImpressionCache()
  if (cached) {
    impressionData.value = cached
    return
  }
  loadImpression()
})

/** 地址里的 ?post=<id>：切到社区页签并打开这条帖子（同页再次点消息里的帖子也走这里） */
function openDeepLinkedPost() {
  const id = Number(route.query.post)
  if (!Number.isFinite(id) || id <= 0) return
  if (isGuestMode()) {
    void promptLogin('查看社区帖子')
    return
  }
  if (activeTab.value !== 'community') activeTab.value = 'community'
  postDetailLeaving.value = false
  communityDetailId.value = id
}

watch(() => route.query.post, (v) => { if (v) openDeepLinkedPost() })
</script>

<style scoped>
.campus-page {
  height: 100%;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 12px 24px 0;
  box-sizing: border-box;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.campus-page::-webkit-scrollbar { display: none; }
/* 直接子元素统一去掉左右内边距（轮播、阅读器、移动端页头除外：
   轮播自带边距、阅读器是 Teleported 抽屉无布局盒、页头要自己算 16px/8px 内边距） */
.campus-page > *:not(.campus-carousel):not(.article-reader-drawer):not(.campus-appbar) {
  padding-left: 0;
  padding-right: 0;
}
.campus-section:last-child {
  padding-bottom: 32px;
}

/* ===== Page Hero Header =====
   本页是一级 Tab（底部导航「校园资讯」），不用 SubPageHeader（带返回箭头、仅移动端）。
   白底通栏：横向铺满整个内容区（抵消 .campus-page 的左右内边距），
   去掉圆角、边框与阴影 —— 只靠「白 vs 浅蓝背景」分层，最干净。
   版式对齐参考稿：左侧一个大号粗体标题，右侧一枚纯黑线性图标，中间大量留白；
   图标不做胶囊底、不带文字，纯粹靠点击热区（32×32）保证可点性。 */
.campus-hero-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  /* 横向铺满：负外边距吃掉父级左右内边距（桌面 24px / 移动 16px，见下方 @media 覆盖）。
     上边 -12px 同样抵消页面 padding-top —— 不抵消的话白条上方会留一条背景色缝隙，通栏就不成立。
     不写 width —— 负外边距 + flex 子项的默认 stretch 已能撑满，
     显式 width 在移动端 column flex 下与 flex-shrink 叠加容易溢出。 */
  margin: -12px -24px 16px;
  background: #fff;
  padding: 18px 24px;
  box-sizing: border-box;
}
/* 标题区做成按钮：点标题即刷新。重置浏览器默认按钮样式，保持纯文字观感 */
.hero-head-text {
  min-width: 0;
  text-align: left;
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  cursor: pointer;
  border-radius: 8px;
}
.hero-head-text:disabled { cursor: default; }
/* 只在键盘聚焦时显示焦点环：鼠标点标题不该出现一圈蓝框 */
.hero-head-text:focus-visible { outline: 2px solid #409eff; outline-offset: 3px; }
.hero-head-text h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: #111827;
  /* 参考稿的字距略紧，粗体大字收紧一点更整 */
  letter-spacing: -.2px;
  line-height: 1.2;
  transition: color .18s ease;
}
.hero-head-text:hover:not(:disabled) h2 { color: #409eff; }
/* 搜索：纯图标按钮，无底无边。命中区 32×32（视觉 22px 图标 + 内边距），
   保证触摸目标够大而不显笨重 */
.hero-head-search {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  padding: 0;
  background: none;
  border: 0;
  border-radius: 50%;
  color: #111827;
  font-size: 22px;
  cursor: pointer;
  transition: color .18s ease, background .18s ease;
}
.hero-head-search:hover { color: #409eff; background: #f3f7fd; }
.hero-head-search:focus-visible { outline: 2px solid #409eff; outline-offset: 2px; }
/* 桌面页头的互动消息信封：与搜索并排，未读红点挂在右上（共用 .appbar-dot） */
.hero-head-dot { position: relative; }

/* ===== 移动端品牌头牌 =====
   为什么是一条渐变蓝：移动端（≤767px）StudentLayout 会把顶部蓝条整个隐藏，这页是首个
   内容页，没有它整页会「没有头」；把品牌色补回来（渐变基色与桌面 topbar 同一族）。
   视觉配方：135° 品牌蓝渐变 + 右上柔光 + 斜向高光 + 内高光/外投影；**矩形通栏、无圆角**，
   上下边直接切齐内容区，像一条真正的 App 品牌栏而不是一张卡片。
   文字只有一枚 22px/800 标题（不放副标题、不放小字）；右侧只留一枚磨砂方角搜索按钮。
   移动端实际样式见文件底部 @media (max-width: 767px)：那里把本块改成白卡顶段。
   此处不设 sticky：本头牌只在移动端渲染，吸顶（sticky）由文末 @media 块统一接管
   （桌面端走另一套 .campus-hero-head，根本不渲染此头牌）。
   z-index 压过下方卡片（含 v-tilt 的 hover 抬升）。
   通栏：负外边距吃掉 .campus-page 移动端的 16px 左右内边距；上内边距为 0（见 @media 覆盖），
   页头上沿直接贴住滚动容器顶边，吸顶时不会漏出一条背景色细缝。 */
.campus-appbar {
  position: relative;
  z-index: 30;
  isolation: isolate;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  min-height: 60px;
  box-sizing: border-box;
  margin: 0 -16px 14px;
  padding: 10px 12px 10px 20px;
  overflow: hidden;
  background:
    radial-gradient(120% 150% at 92% -30%, rgba(255, 255, 255, .34) 0%, rgba(255, 255, 255, 0) 58%),
    linear-gradient(135deg, #1d4ed8 0%, #2563eb 52%, #3b82f6 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .22),
    0 6px 16px rgba(29, 78, 216, .18);
  color: #fff;
}
/* 右上柔光：让纯色条有「光从右上打进来」的层次 */
.campus-appbar::before {
  content: "";
  position: absolute;
  z-index: -1;
  top: -78px;
  right: -54px;
  width: 190px;
  height: 190px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, .30) 0%, rgba(255, 255, 255, 0) 68%);
  pointer-events: none;
}
/* 左下斜向高光：一道克制的斜光，打破纯渐变的平 */
.campus-appbar::after {
  content: "";
  position: absolute;
  z-index: -1;
  left: -18%;
  bottom: -104px;
  width: 260px;
  height: 150px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, .13) 50%, rgba(255, 255, 255, 0) 100%);
  transform: rotate(-12deg);
  pointer-events: none;
}
/* 标题区：3px 白色竖条 + 22px/800 标题。
   竖条不是随手加的装饰 —— 本页区块标题（.section-title）和卡片标题都是「3px 蓝竖条 + 粗体」
   的语言，头牌把它翻成白色，页头与内容区才是同一套排版；图标按钮只用方角磨砂块，
   不抢标题的视觉权重。 */
.appbar-title {
  display: flex;
  align-items: center;
  gap: 11px;
  flex: 1;
  min-width: 0;
}
.appbar-title::before {
  content: "";
  flex-shrink: 0;
  width: 3px;
  height: 20px;
  border-radius: 2px;
  background: rgba(255, 255, 255, .75);
}
.appbar-title h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  /* 中文大标题给一点字距更「设计」；行高压紧，矩形栏里上下留白才均匀 */
  letter-spacing: .5px;
  line-height: 1.2;
  color: #fff;
  text-shadow: 0 1px 2px rgba(11, 34, 84, .22);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.appbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
/* 磨砂方角搜索按钮（36×36）：玻璃质感靠半透明白底 + 描边 + blur */
.appbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, .22);
  border-radius: 12px;
  background: rgba(255, 255, 255, .14);
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  transition: background .2s var(--tui-ease), border-color .2s var(--tui-ease),
    transform .12s var(--tui-ease);
}
.appbar-btn:hover { background: rgba(255, 255, 255, .24); border-color: rgba(255, 255, 255, .32); }
.appbar-btn:active { transform: scale(.93); background: rgba(255, 255, 255, .3); }
.appbar-btn:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

/* 互动消息入口：未读数量挂在图标右上角（信封=论坛互动，聊天走底部「消息」页签） */
.appbar-btn--dot { position: relative; }
.appbar-dot {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #f53f3f;
  color: #fff;
  font-size: 10px;
  font-style: normal;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 0 0 1.5px rgba(0, 0, 0, .18);
}

/* 游客专属：页头内的登录入口（移动端顶栏被隐藏，没有它游客会找不到回登录页的路径） */
.appbar-login {
  height: 30px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: #111111;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .5px;
  cursor: pointer;
  flex-shrink: 0;
}
.appbar-login:active { transform: scale(.95); }

/* ===== 发帖悬浮按钮 =====
   移动端全部分类常驻。与底部 dock 胶囊的间距规则：到胶囊顶边的垂直间隙 =
   到屏幕右缘的水平间隙。水平对齐「个人中心」页签中轴：胶囊宽 W=min(100vw,440px)
   左右各内缩 14px、内部再 8px 内边距，5 个页签等分，中轴距右缘 0.1W+17.6px；
   FAB 宽 52 需右收 26px → 右缘 = 0.1W−8.4px。
   垂直：胶囊顶边距屏底 74px → bottom = 0.1W+65.6px + 安全区。 */
.community-fab {
  position: fixed;
  right: calc(min(100vw, 440px) * 0.1 - 8.4px);
  bottom: calc(min(100vw, 440px) * 0.1 + 65.6px + env(safe-area-inset-bottom, 0px));
  z-index: 30;
  width: 52px;
  height: 52px;
  border: 0;
  border-radius: 50%;
  background: #1d2129;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(29, 33, 41, .35);
  cursor: pointer;
  transition: transform .15s ease;
}
.community-fab:active { transform: scale(.94); }

/* ===== Search Dialog ===== */
.search-hot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 4px;
}
.search-hot-label { font-size: 12px; color: #9aa5b1; }
.search-hot-tag { cursor: pointer; }
.search-block { margin-top: 16px; }
.search-block-title {
  font-size: 13px;
  font-weight: 600;
  color: #5a6673;
  margin-bottom: 8px;
}
.search-hit {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 2px;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
  color: #42505f;
  text-decoration: none;
  cursor: pointer;
}
.search-hit:last-child { border-bottom: none; }
.search-hit:hover .search-hit-title { color: #409eff; }
.search-hit-static { cursor: default; }
.search-hit-static:hover .search-hit-title { color: #42505f; }
.search-hit-source {
  flex-shrink: 0;
  font-size: 11px;
  color: #7a8694;
  background: #f2f5f9;
  border-radius: 4px;
  padding: 2px 6px;
}
.search-hit-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color .18s ease;
}
.search-hit-date { flex-shrink: 0; font-size: 11px; color: #9aa5b1; }
.search-empty { margin: 6px 0 0; font-size: 12px; color: #b4bcc8; }
.search-empty a { color: #2f6ef2; text-decoration: none; }
.search-empty a:hover { text-decoration: underline; }

/* ===== Section ===== */
.campus-section { margin-bottom: 24px; }
/* 区块标题与卡片标题（.card-title）同一口径：15px/700 + 3px 蓝色竖条 + 8px 内距。
   原先这里用 4px 圆角小竖条 + 16px/600，与页内「通知公告 / 专业分院」
   等卡片标题两种观感，故统一。 */
.section-title {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
  border-left: 3px solid #409eff; padding-left: 8px;
  display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
}
.section-tag {
  font-size: 11px; color: #999; background: #f5f7fa;
  padding: 2px 10px; border-radius: 10px; font-weight: 400;
}
/* 分区标题右侧的轻操作（当前只有「交流社区 → 发帖」用） */
.section-action {
  margin-left: auto;
  display: inline-flex; align-items: center; gap: 3px;
  height: 26px; padding: 0 10px;
  border: 1px solid rgba(15, 23, 42, .1); border-radius: 13px;
  background: #fff; color: #1d2129;
  font-size: 12px; font-weight: 500; cursor: pointer;
}
.section-action:hover { background: #f4f5f7; }

/* ===== Entry Grid ===== */
.entry-card { display: block; }
.entry-chip { display: block; }
.entry-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.entry-item {
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 12px;
  padding: 16px 12px;
  text-align: center;
  cursor: pointer;
  position: relative;
  transition: all .2s ease;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.entry-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(64,158,255,.15);
  border-color: var(--entry-color, #409eff);
}
/* 桌面端：--entry-color（由 getEntryColor 注入，中性深灰 #4E5969）直接落在图标上，克制、让位于内容区；
   移动端的图标配色改由「瓷片」承担，见文末移动端块 */
.entry-icon {
  font-size: 28px;
  color: var(--entry-color, #409eff);
  margin-bottom: 8px;
  transition: color .2s ease;
}
.entry-item p {
  font-size: 13px;
  color: #1d2129;
  margin: 0;
  font-weight: 500;
}
.entry-external {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  color: #86909c;
  background: #f2f3f5;
  padding: 2px 6px;
  border-radius: 4px;
}

/* ===== Duo Cards ===== */
.campus-duo { display: flex; gap: 18px; margin-bottom: 22px; }
.campus-card {
  flex: 1; min-width: 0; background: #fff; border-radius: 14px;
  padding: 16px 18px; box-shadow: 0 1px 6px rgba(0,0,0,.04);
  transition: transform .18s ease, box-shadow .18s ease;
}
.campus-card-jx { flex: 1.5; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.card-title {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
  border-left: 3px solid #409eff; padding-left: 8px;
  display: flex; align-items: center; gap: 6px;
}
.card-title .el-icon { color: #409eff; }
.card-more { font-size: 12px; color: #409eff; text-decoration: none; }
.head-right { display: flex; gap: 12px; align-items: center; }

/* ===== News Rows ===== */
.jxdt-first {
  /* <a> 默认是 inline：行内元素上 overflow/border-radius 不生效，图片方角会溢出圆角边框；
     display:block 后圆角裁剪、标题绝对定位才真正生效 */
  display: block;
  position: relative; border-radius: 8px; overflow: hidden;
  margin-bottom: 12px; cursor: pointer;
  background: linear-gradient(135deg, #dbeafe, #60a5fa); min-height: 96px;
}
/* 自适应高度：按原图比例显示，过高才裁切（原先固定 120px 把 4:3 竖版海报压成只剩中间 39%） */
.jxdt-first-img {
  width: 100%; height: auto; max-height: 230px;
  object-fit: cover; object-position: center top;
  display: block;
}
.jxdt-first-title {
  position: absolute; left: 0; right: 0; bottom: 0;
  padding: 32px 12px 12px;
  background: linear-gradient(transparent 20%, rgba(0,0,0,.45) 50%, rgba(0,0,0,.8) 100%);
  color: #fff; font-size: 14px; font-weight: 600;
  text-shadow: 0 1px 4px rgba(0,0,0,.5);
}
.news-row {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: #444; line-height: 2.05; cursor: pointer;
}
.news-row:hover .news-text { color: #409eff; }
.news-date-right { color: #999; font-size: 11px; flex-shrink: 0; margin-left: auto; }
.news-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 教学动态：日 + 月 邮戳样式 */
.jxdt-date-row { gap: 12px; }
.jxdt-day {
  flex-shrink: 0;
  width: 40px;
  text-align: center;
  border-left: 3px solid #409eff;
  padding-left: 8px;
}
.jxdt-day b {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.1;
}
.jxdt-month {
  display: block;
  font-size: 10px;
  color: #7a8694;
  margin-top: 2px;
}

/* 通知公告：月-日 */
.tzgg-row {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: #444; line-height: 2.05; cursor: pointer;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
}
.tzgg-row:last-child { border-bottom: none; }
.tzgg-row:hover .news-text { color: #409eff; }
.tzgg-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #7a8694;
  width: 45px;
  text-align: center;
}

/* ===== 高教信息（导航样式） ===== */
.campus-card-gjxx {
  background: #f8fafc;
}
.gjxx-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.gjxx-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background .2s ease;
}
.gjxx-item:hover {
  background: #ecf5ff;
}
.gjxx-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid #d7e0ec;
  color: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  transition: all .2s ease;
}
.gjxx-item:hover .gjxx-icon {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}
.gjxx-title {
  flex: 1;
  font-size: 13px;
  color: #42505f;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color .2s ease;
}
.gjxx-item:hover .gjxx-title {
  color: #409eff;
}
.gjxx-arrow {
  flex-shrink: 0;
  color: #7a8694;
  transition: transform .2s ease, color .2s ease;
}
.gjxx-item:hover .gjxx-arrow {
  transform: translateX(3px);
  color: #f56c6c;
}

/* ===== 教学建设 ===== */
.build-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 6px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background .2s ease;
}
.build-row:last-child {
  border-bottom: none;
}
.build-row:hover {
  background: #ecf5ff;
}
.build-mark {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border: 1.5px solid #409eff;
  transform: rotate(45deg);
  margin-top: 6px;
  transition: all .2s ease;
}
.build-row:hover .build-mark {
  background: #f56c6c;
  border-color: #f56c6c;
}
.build-text {
  flex: 1;
  font-size: 13px;
  color: #42505f;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color .2s ease;
}
.build-row:hover .build-text {
  color: #409eff;
}
.build-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #7a8694;
  margin-top: 2px;
}

/* ===== College ===== */
/* 桌面端 7 张卡片：固定 2 列 / 4 列。
   原先 auto-fill minmax(280px,1fr) 在 1200px 容器里每行放 4 个，7 = 4 + 3，
   最后一行拖着 3 张卡留白；改成 4 列 = 4 + 3、2 列 = 4 + 2 + 1，
   行尾恒有卡片占位，不再出现"最后一张卡孤零零占一行"的空档。 */
/* 「专业分院」是 .campus-page 的直接子元素，被上面那条
   `.campus-page > * { padding-left/right: 0 }` 抹掉了左右内边距 ——
   而它内部的 .card-head 并不自带内边距，结果是标题贴着卡片左边缘，
   与嵌在 .campus-duo 里、保住了 .campus-card 的 16px 18px 的
   「绵城印象」标题不齐。
    只补 .card-head 的左右内边距（而非整个 section）：.card-body 自己已有
    20px 左右内边距，若加在 section 上会叠加成 38px，桌面端学院网格会内缩。 */
.campus-card-college { margin-bottom: 22px; }
.campus-card-college > .card-head { padding-left: 18px; padding-right: 18px; }
.card-body { padding: 14px 20px 16px; }
.college-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.college-card {
  /* 纵向 flex：head / 新闻区 / "进入官网" 三段，
     .college-list 撑满中间，链接被 margin-top:auto 压到卡片底部，7 张卡据此等高对齐 */
  display: flex; flex-direction: column;
  background: #f8fafc; border-radius: 10px; padding: 16px;
  border: 1px solid #e4e7ed; cursor: pointer;
  transition: all .2s ease;
}
.college-card:hover {
  background: #ecf5ff;
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64,158,255,.15);
}
.college-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.college-icon { font-size: 28px; }
.college-name { font-size: 15px; font-weight: 700; color: #1a1a2e; }
/* 两条新闻槽位固定高度（2 × 21.6 ≈ 43px，含 one-line 省略号）：
   学院只有 0/1 条时由 ::after 补一条"暂无最新动态"，卡片不会被内容抽走高度 */
.college-list { flex: 1; min-height: 44px; display: flex; flex-direction: column; justify-content: flex-start; }
.college-news { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #666; line-height: 1.8; }
.news-dot { color: #409eff; flex-shrink: 0; }
/* min-width:0 是必须的：父级是 flex，且标题是 nowrap+ellipsis 的长文本，
   不给收缩下限时长标题（后端可能返回 40 字内的截断标题）会把卡片顶宽 */
.college-news .news-text { min-width: 0; }
/* 日期是 MM-DD 固定宽度，放右侧竖对齐，10 条无日期的条目直接不渲染该节点 */
.college-date { flex-shrink: 0; margin-left: auto; font-size: 11px; color: #9aa5b1; }
.college-empty { font-size: 12px; color: #b4bcc8; line-height: 1.8; }
.college-link { margin-top: auto; padding-top: 10px; font-size: 12px; color: #409eff; }
@media (min-width: 1024px) {
  .college-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}

/* ===== Impression List ===== */
.impression-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.impression-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .2s ease;
}
.impression-row:hover {
  background: #ecf5ff;
}
.impression-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.impression-info {
  flex: 1;
  min-width: 0;
}
.impression-name {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.impression-desc {
  font-size: 12px;
  color: #7a8694;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.impression-arrow {
  flex-shrink: 0;
  color: #7a8694;
  transition: transform .2s ease, color .2s ease;
}
.impression-row:hover .impression-arrow {
  transform: translateX(3px);
  color: #409eff;
}

/* ===== Carousel ===== */
.campus-carousel {
  margin-bottom: 24px;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,.08);
  flex-shrink: 0;
}
.campus-carousel :deep(.el-carousel__indicators) {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}
.campus-carousel :deep(.el-carousel__indicator) {
  padding: 4px;
}
.campus-carousel :deep(.el-carousel__button) {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,.6);
  opacity: 1;
}
.campus-carousel :deep(.el-carousel__indicator.is-active .el-carousel__button) {
  background: #fff;
  width: 10px;
  height: 10px;
}
.carousel-item {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
}
.carousel-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.carousel-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 48px 24px 20px;
  background: linear-gradient(transparent, rgba(0,0,0,.65));
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.carousel-title {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  text-shadow: 0 1px 4px rgba(0,0,0,.4);
}
.carousel-campus {
  font-size: 12px;
  padding: 4px 14px;
  border-radius: 12px;
  background: rgba(255,255,255,.25);
  backdrop-filter: blur(4px);
  color: #fff;
}

/* 3D 倾斜统一处理 */
.entry-item, .campus-card, .college-card { transform-style: preserve-3d; }

/* ===== 外链条目（<div> → <a> 语义化改造）=====
   去掉浏览器默认 <a> 外观（下划线/蓝色/访问后紫色），保持改造前的卡片视觉；
   同时保留原 cursor:pointer 与 hover 效果。
   注：原先还排除了 .college-tag（移动端胶囊自带样式），该标签已改为行式列表
   .college-m-row，此处随之清理；仅剩 .card-more 需要保留自身链接配色。 */
.campus-page a:not(.card-more) {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.campus-page a:not(.card-more):visited {
  color: inherit;
}

/* ===== Mobile =====
   2026-10 改版：一比一复刻资讯流 App（掘金「热点」页）的移动端版式。
   规格按参考稿实测标定（参考稿 670px 宽对应 375pt，换算比 ≈1.786）：
     页头标题 26px/700 · Tab 15px、选中 3px 下划线
     信息流标题 17px/600 两行 · 元信息 13px · 缩略图 120×68（16:9）圆角 8px */
@media (max-width: 767px) {
  /* 移动端页面改纵向 flex：桌面端卡片版式整块包在 <template v-if="!isMobile"> 里不渲染。
     底色交回页面（移动端 StudentLayout 已是浅底），白卡从页头开始：
     页头改为通栏吸顶（左右不留边），Tab / 轮播 / 信息流仍是左右各 16px 的白卡。 */
  .campus-page {
    /* 顶部不再留 8px：页头已改成通栏吸顶，上沿要直接贴住滚动容器顶边，
       否则吸顶瞬间上方会悬出一条背景色细缝 */
    padding: 0 16px;
    /* 页头高度：Tab 的吸顶偏移量必须与它严格相等，否则两层之间会漏出滚动内容 */
    --campus-appbar-h: 56px;
    display: flex;
    flex-direction: column;
    background: transparent;
    /* 卡片轨道左右各挂一页邻居，拖动时会平移出可视区：横向裁掉，避免撑出横向滚动条 */
    overflow-x: hidden;
    /* 下拉刷新：避免浏览器原生下拉刷新抢手势 */
    overscroll-behavior-y: contain;
  }
  .campus-page > section, .campus-page > nav { flex-shrink: 0; }

  /* ---------- 页头：吸顶 App Bar ----------
     页头在整个信息流上方吸顶（sticky top:0）：越往下翻，标题与搜索 / 通知入口越要
     随手可及 —— 这两枚图标是「找一条资讯」的入口，滚走后再让用户滚回顶部是反直觉的。
     通栏：负外边距吃掉 .campus-page 的 16px 左右内边距，白底铺满整屏 ——
     否则信息流从下方滚过时，页头两侧会露出半截文字。内边距相应内移 16px，
     标题与图标仍与信息流左缘对齐。
     圆角归零：吸顶后页头上沿贴着屏幕，保留 13px 圆角会在两个角上露出背后滚动的内容。
     高度 56px（--campus-appbar-h）；标题与图标靠 align-items:center 垂直居中。
     底部不画分割线：下方 Tab 也是吸顶的，两者要拼成一个完整的白色顶栏，
     分割线统一放在顶栏最下沿（见 components/common/SlidingTabs.vue 的 box-shadow）。 */
  .campus-appbar {
    position: sticky;
    top: 0;
    z-index: 30;
    min-height: var(--campus-appbar-h);
    margin: 0 -16px;
    padding: 0 16px;
    background: #fff;
    box-shadow: none;
    border-radius: 0;
    overflow: hidden;
    color: #1d2129;
  }
  /* 去掉基础样式里的渐变与右上柔光/斜向高光 */
  .campus-appbar::before,
  .campus-appbar::after { display: none; }
  /* 页头左右内边距 16px：标题与信息流左缘对齐；标题与图标由基础样式的
     align-items:center 在 min-height 高度里垂直居中。 */
  .appbar-title::before { display: none; }
  .appbar-title h1 {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -.2px;
    line-height: 1.2;
    color: #1d2129;
    text-shadow: none;
  }
  /* 图标按钮：参考稿是纯黑图标、无底色无边框，命中区 32×32 */
  .appbar-btn {
    width: 32px;
    height: 32px;
    border: 0;
    border-radius: 50%;
    background: none;
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    color: #1d2129;
    font-size: 22px;
  }
  .appbar-btn:hover { background: #f3f4f6; border-color: transparent; }
  .appbar-btn:active { transform: scale(.92); background: #eceef1; }

  /* ---------- 分类 Tab ----------
     分类 Tab 的样式与动画已整体搬进 components/common/SlidingTabs.vue
     （滑动下划线 + 文字随条染色 + 吸顶偏移都自带），这里不再重复定义，避免两套规则打架。 */

  /* ---------- 大图轮播（只在「推荐」那一页的顶部渲染）----------
     位次：页内最上方，信息流之上，属于同一张白卡的上半段；
     左右内边距在分页里被清零（见 .campus-pager … 的补平规则），图片铺满卡片宽度。
     版式：16:9 左右的圆角大图 + 底部黑色渐变 + 白色标题两行截断；
     指示点用条形（与桌面轮播的圆点区分：这里是信息流 App 的观感）。
     不给左右箭头：手机上没有 hover，箭头会长期压在图上挡内容，按住拖动 + 自动轮播够用。
     分类翻页的横向位移由外层 .campus-pager 统一承担，轮播自身不再位移。 */
  .campus-hero-carousel {
    flex-shrink: 0;
    margin: 0;
    padding: 12px 16px 4px;
    background: #fff;
  }
  /* ---------- 按住拖动（只有图片层位移）----------
     touch-action / user-select / 光标只写在 .hero-track（图片区）上，**不要写到
     .campus-hero-carousel**：外边距、上下留白属于外层 section，写在外层会让整块区域
     （含留白）都变成「可拖 / 不可选」，手指点在图片外面的白边上也能拖走轮播。
     touch-action: pan-y 把「横向」手势留给 JS（拖动切页），纵向仍交给浏览器滚动页面 ——
     少了它，手指一按浏览器就先接管成页面滚动，拖不动轮播。
     位移**不在 .hero-track 上**：它一层包含「图片容器 + 指示点」，位移写上会整块一起动，
     卡片的圆角与指示点跟着平移，看起来就像卡片在滑。位移只写在 .el-carousel__container
     （纯图片层）上，卡片（圆角、背景、指示点）保持不动。 */
  .hero-track {
    /* 定位上下文：自绘指示点 .hero-dots 相对它定位（= 相对图片区域） */
    position: relative;
    width: 100%;
    /* overflow 交给内层 .el-carousel 裁切：这里加 hidden 会连带裁掉贴在底边的指示点 */
    touch-action: pan-y;
    -webkit-user-select: none;
    user-select: none;
  }
  .hero-track,
  .hero-track :deep(.el-carousel__container),
  .hero-track .hero-slide { cursor: grab; }
  .campus-hero-carousel.is-dragging .hero-track,
  .campus-hero-carousel.is-dragging .hero-track :deep(.el-carousel__container),
  .campus-hero-carousel.is-dragging .hero-track .hero-slide { cursor: grabbing; }
  /* ---------- 图片层：跟手 + 松手接续 ----------
     位移与过渡都放在 .el-carousel__container 上 —— 这就是「卡片里那张图」那一层。
     松手时一次性做三件事（同一帧内）：撤掉 .is-dragging（去掉 transition: none）、
     把偏移量设为目标值、恢复过渡 —— 浏览器会从「当前拖拽到的位置」直接补完剩下的距离，
     所以动画是从松手处接着播，而不是回到 0 再重来。
       翻页：图片层滑到 ∓图宽；同一帧里 el-carousel 翻页、把新页放到另一侧，
             视觉上就是「旧图被推走、新图推上来」，交接处零跳变。
       回弹：图片层滑回 0，反向弹回去。
     必须用 transform：它参与过渡中断的「从当前值接续」，left 不行（会先瞬跳回 0）。 */
  .hero-track :deep(.el-carousel__container) {
    transform: translate3d(var(--hero-drag-x, 0px), 0, 0);
    transition: transform 360ms cubic-bezier(.22, .61, .36, 1);
    will-change: transform;
  }
  .campus-hero-carousel.is-dragging .hero-track :deep(.el-carousel__container) {
    transition: none;
    will-change: auto;
  }
  /* 补完动画结束后的一帧：静默把偏移归零，不能有过渡（否则会再弹回一次） */
  .campus-hero-carousel.is-resetting .hero-track :deep(.el-carousel__container) {
    transition: none;
  }
  /* 拖动中关掉轮播自身的过渡，否则跟手偏移会和它的翻页过渡互相拉扯、出现拖影。
     松手后 is-dragging 立刻撤掉，这层过渡同时恢复 —— 与图片层的补完动画同帧起跑。 */
  .campus-hero-carousel.is-dragging :deep(.el-carousel__item) { transition: none; }
  /* ---------- 卡片（不动的那一层）：圆角 + 裁切 ----------
     overflow: hidden 必须写在**不位移**的元素上才裁得住位移层：
     .el-carousel 不参与位移，它裁掉 .el-carousel__container（图片层）滑出卡片的部分，
     所以拖动时看到的是「卡片边框不动、里面的图片在滑」。
     若把这层 overflow 写到会动的 .el-carousel__container 自己身上，它跟着自己一起平移，
     等于没有裁切，图片会直接露出卡片外。 */
  .campus-hero-carousel :deep(.el-carousel) {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
  }
  .campus-hero-carousel :deep(.el-carousel__container) {
    border-radius: 12px;
  }
  /* 指示点（自绘，叠在图片底边内侧）：不参与布局，因此不会影响轮播高度与图片定位 */
  .hero-dots {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 10px;
    z-index: 6;
    display: flex;
    justify-content: center;
    gap: 5px;
    pointer-events: none;
  }
  .hero-dot {
    width: 14px;
    height: 3px;
    border-radius: 2px;
    background: rgba(255, 255, 255, .45);
    transition: width .22s ease, background .22s ease;
  }
  .hero-dot.is-active {
    width: 22px;
    background: #fff;
  }
  /* 幻灯片整块可点：.hero-slide 是 <a>，块级化后铺满轮播容器 */
  .hero-slide {
    position: relative;
    display: block;
    width: 100%;
    height: 100%;
    overflow: hidden;
    -webkit-tap-highlight-color: transparent;
  }
  .hero-slide:active { opacity: .94; }
  /* 图：与 .feed-thumb 同一套「绝对定位 + 撑满 + cover」防变形方案 */
  .hero-slide-img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    background: #eef1f5;
  }
  /* 底部渐变：保证任意图片（浅底海报也算）上的白字都能读 */
  .hero-slide-shade {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0) 34%, rgba(0, 0, 0, .34) 62%, rgba(0, 0, 0, .72) 100%);
    pointer-events: none;
  }
  .hero-slide-caption {
    position: absolute;
    left: 14px;
    right: 14px;
    bottom: 26px; /* 让开底部指示点 */
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  /* 来源标签：半透明白底 + 白字，压在图上不抢标题 */
  .hero-slide-tag {
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(255, 255, 255, .22);
    -webkit-backdrop-filter: blur(6px);
    backdrop-filter: blur(6px);
    font-size: 11px;
    font-weight: 500;
    line-height: 1.5;
    color: #fff;
  }
  .hero-slide-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.4;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0, 0, 0, .35);
    /* 两行截断：大图轮播里超过两行的标题会把图压得只剩一条 */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* ---------- 卡片分页轨道 ----------
     轨道本身（裁切层、跟手位移、吸附过渡、首尾边界）已抽到 components/common/SwipePager.vue，
     这里只剩「这一页长什么样」：
       · .campus-pager 落在组件根节点上（组件根会继承本页的 scope id），只往下传设计变量；
       · .campus-pager-page 是每页的容器，底色与下圆角按本页白卡的规格给
         （等宽的 flex-basis 由组件统一提供，见组件的 :deep(.sw-pager-page) 规则）。 */
  .campus-pager {
    /* 拖动 / 吸附时整条轨道垫白：边界分类回弹时露出的边缘也是白卡，
       不会闪出一条页面底色；收起邻居页后组件撤掉这个底色。 */
    --sw-track-bg: #fff;
  }

  /* 拖动中不保留按下态的压暗：滑动是切分类，不是「按住这一行」。
     状态类由分页组件挂在根节点上（is-dragging），仍在本页的 scope 里，可直接选中。 */
  .campus-pager.is-dragging .feed-item:active { opacity: 1; }

  /* 一张卡片 = 一个分类的完整内容：「推荐」页是轮播 + 信息流，「关注」页只有空态，其余只有信息流。
     页容器自带白底与下圆角：邻居页比当前页矮时也能把卡片补齐，拖动时不会露底色。 */
  .campus-pager-page {
    background: #fff;
    border-radius: 0 0 13px 13px;
  }

  /* 分页里的轮播不再是 .campus-page 的直接子元素，
     原先那条「直接子元素去掉左右内边距」的规则不再生效，这里补平：
     轮播图保持通栏（图片铺满卡片宽度，左右不留白）；
     信息流则保留卡片内边距（见下方 .campus-feed），标题不贴卡片边缘。 */
  .campus-pager .campus-hero-carousel {
    padding-left: 0;
    padding-right: 0;
  }

  /* ---------- 白卡主体：Tab 之后的当前页 ----------
     信息流一直连到屏幕底部（padding-bottom 撑出白卡下沿）并补下圆角。
     左右不再单独留卡片内边距：页面容器的 16px 就是内容到屏幕的距离
     （参考稿里标题 / 图片 / 互动栏共用同一条左基线，约 12–16px）。
     卡片白底与页面白底同色，视觉上仍是一整块内容区，不会显得贴边。 */
  .campus-feed {
    display: flex;
    flex-direction: column;
    background: #fff;
    margin: 0;
    padding: 0 0 24px;
    border-radius: 0 0 13px 13px;
  }

  /* ---------- 信息流 ----------
     参考稿行式结构：左侧标题两行 + 12px 灰色元信息，右侧 16:9 缩略图，
     每行之间一条 1px #F0F0F0 分割线（不是靠留白分隔）。
     行本身不再设左右内边距（由 .campus-feed 统一给 20px），
     分割线因此从内容左缘延伸到卡片右缘内 20px 处，与参考稿一致。 */
  .campus-feed { display: flex; flex-direction: column; }

  .feed-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 13px 0;
    border-bottom: 1px solid #f0f0f0;
    -webkit-tap-highlight-color: transparent;
    transition: opacity .14s ease;
  }
  .feed-item:last-child { border-bottom: 0; }
  .feed-item:active { opacity: .62; }
  /* 信息流行从 <a> 改成了 <div role="link">：行内要嵌评论/点赞/转发三个按钮，
     按钮不能嵌套在 <a> 里（点击会被父链接吞掉，且 HTML 不允许交互元素嵌套）。
     因此整行可点由 @click 承担，键盘可达由 tabindex + Enter 补上。 */
  .feed-item { cursor: pointer; outline: none; }
  .feed-item:focus-visible { outline: 2px solid #2563eb; outline-offset: -2px; border-radius: 8px; }
  .feed-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
  /* 行尾互动：图标 + 数字，无底色无边框。热区用 padding 撑到 32px 高，
     但**视觉**上只是 13px 小字，避免评论区数字抢走标题的视觉权重。
     与时间 / 标签同一行：左侧留 12px 起，组内 gap 16px，
     不写 margin-top，行高由 .feed-meta 决定。 */
  .feed-acts {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-left: 12px;
  }
  .feed-act {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    /* 负外边距把热区往四周扩出去，视觉位置不变但手指更好点 */
    padding: 6px 2px;
    margin: -6px -2px;
    background: none;
    border: 0;
    font: inherit;
    font-size: 12px;
    line-height: 1;
    color: #b2b2b2;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: color .16s ease, transform .12s ease;
  }
  .feed-act .el-icon { font-size: 14px; }
  .feed-act:active { transform: scale(.9); }
  .feed-act:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; border-radius: 4px; }
  /* 浏览量：只做数字展示（没有可点的去向），去掉按钮的按压反馈 */
  .feed-act.is-static { cursor: default; }
  .feed-act.is-static:active { transform: none; }
  .feed-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.5;
    color: #1d2129;
    /* 两行截断：保证右侧缩略图高度与左侧文字块稳定对齐 */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .feed-meta {
    display: flex;
    align-items: center;
    gap: 0;
    font-size: 12px;
    color: #b2b2b2;
    line-height: 1.2;
  }
  /* 参考稿元信息是「昨天21:57·作者」连写，分隔点两侧不留缝 */
  .feed-dot { color: #cfcfcf; margin: 0 2px; }
  /* 缩略图：统一 16:9（资讯流通用比例，B 站 / 头条同款）。
     原来锁 129×97（≈4:3）会把校站抓来的 16:9 会议照上下裁得很空，
     还让标题区少一截宽度；改成纯比例锁宽后高度自动算，比例恒定。
     必须配 object-fit:cover，图片原始比例再怪也只裁不拉伸。 */
  .feed-thumb {
    flex-shrink: 0;
    width: 104px;
    aspect-ratio: 16 / 9;
    border-radius: 8px;
    overflow: hidden;
    background: #f2f3f5;
    position: relative;
    /* 缩略图高度小于左侧文字块：顶部对齐，行高由文字块决定 */
    align-self: flex-start;
  }
  .feed-thumb img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    /* 抓到的校站图片往往带内联 width/height 或 svg 原始尺寸，绝对定位 + 撑满
       能保证无论图片原始比例如何，都严格填满容器并被圆角裁切 */
    max-width: 100%;
    max-height: 100%;
  }

  /* ---------- 无图条目：标题占满整行 ----------
     参考稿里没图的条目（如「从 0.1 开始的 AI 使用手册」）标题是**铺满整宽**的，
     右侧不保留缩略图位置。所以无图行不渲染 .feed-thumb，标题自然吃满宽度，
     也不会有占位块和 97px 的假高度。 */
  .feed-empty {
    margin: 40px 0;
    text-align: center;
    font-size: 13px;
    color: #b4bcc8;
  }

  /* 页头与内容：移动端所有卡片版式（轮播 / 入口宫格 / 教学动态 / 专业分院 /
     绵城印象）都包在桌面端 <template v-if="!isMobile"> 里，不再渲染，
     因此这里无需再为它们写移动端覆盖样式；
     若后续要恢复某个卡片到移动端，把它移出该 template 并在此补样式即可。 */
}
</style>

