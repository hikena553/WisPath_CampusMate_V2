<template>
  <div
    class="campus-page"
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
        <button
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
        placeholder="搜索资讯标题，如：图书馆、放假、招聘……"
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
         不放条数角标：7 个分类在 390px 宽下已超出首屏、需要横向滑动，
         再加数字只会把「图书馆」推得更远，却没有滑动暗示。
         分类口径：移动端不展示「高教信息」（见 MOBILE_HIDDEN_SOURCES），
         所以这里比桌面端卡片少一栏 —— 桌面端「高教信息」卡片保留不变。
         「推荐」= 原「全部」合并流；「关注」为新增 Tab，数据源待接（见 itemsOfTab）。 -->
    <nav
      v-if="isMobile"
      class="campus-tabs"
      :class="{
        'is-pager-dragging': pagerDragging,
        'is-pager-resetting': pagerResetting,
        'is-tab-instant': tabClickSwitch,
      }"
      role="tablist"
      aria-label="资讯分类"
    >
      <button
        v-for="t in mobileTabs"
        :key="t.key"
        :ref="el => setTabRef(t.key, el)"
        type="button"
        role="tab"
        class="campus-tab"
        :aria-selected="activeTab === t.key"
        @click="onTabClick(t.key)"
      >
        <span class="campus-tab-label">{{ t.label }}</span>
        <!-- 同一段文字的深色副本：叠在文字框里，只显示滑条所占的那一段 ——
             放在按钮内部是为了复用同一个文字框，两层字的字体 / 宽度必然一致，
             不会像「另起一行复制」那样因字体或加粗差几个像素而重影。 -->
        <span
          class="campus-tab-label campus-tab-label-dark"
          :style="tabDarkClip[t.key]"
          aria-hidden="true"
        >{{ t.label }}</span>
      </button>
      <!-- 选中下划线做成独立滑条：拖卡片时按位移比例在相邻 Tab 之间移动，
           与卡片同步；点 Tab / 吸附完成时用同一段 200ms 过渡滑到目标位。 -->
      <span class="campus-tab-indicator" :style="tabIndicatorStyle" aria-hidden="true" />
    </nav>

    <!-- 移动端卡片分页（三页轨道）
         一次渲染「当前分类」和它左右两侧的邻居分类，三张卡片铺在同一条横向轨道上：
         手指往左拖时整条轨道跟着走，右侧那一页从边缘同步进来，松手按位移 / 速度
         吸附到最近一页（或回弹）。全程「跟手」，不会等到松手后才补动画。
         邻居页只在拖动开始时挂载（pagerOpen），松手吸附完成后立即卸载，
         页面高度回到当前分类自己的高度，不在底部留多余白区。
         每页 = 一条分类的完整卡片：「推荐」页含顶部大图轮播，「关注」页是空态，其余是纯信息流。
         轮播自己的拖动仍挂在 .hero-track 上，与分类翻页互不干扰（按压必须落在
         .campus-feed 上才会启动分类拖动）。 -->
    <!-- 下拉刷新指示器：放在两段吸顶头（页头 / 分类 Tab）之后，
         靠自身高度把信息流下推、吸顶头保持不动（见 usePullRefresh 注释） -->
    <PullRefreshIndicator
      v-if="isMobile"
      :indicator-style="pull.indicatorStyle"
      :active="pull.active"
    />

    <!-- 裁切层：overflow:hidden 必须挂在「不参与位移」的这一层上。
         挂在会 translate 的轨道上时，裁切框会跟着轨道一起移走 ——
         轨道平移到 ±一页宽时，可视区正好落在裁切框之外，整页变成空白。
         所以这里拆成「外层裁切 + 内层平移」两层。 -->
    <div v-if="isMobile" class="campus-pager-viewport">
    <div
      ref="pagerRef"
      class="campus-pager"
      :class="{
        'is-pager-dragging': pagerDragging,
        'is-pager-resetting': pagerResetting,
        'is-pager-jumping': trackJumping,
        'is-pager-open': pagerOpen,
        'is-pager-animating': pagerAnimating,
      }"
      :style="{ transform: pagerTransform }"
      @pointerdown="onPagerPointerDown"
      @pointermove="onPagerPointerMove"
      @pointerup="onPagerPointerUp"
      @pointercancel="onPagerPointerCancel"
      @click.capture="onPagerClickCapture"
      @dragstart.prevent
    >
      <!-- v-memo：拖动时 pagerX 每帧变化会让整个组件重渲染，三页信息流（含图标 SVG）
           会被逐帧 diff，手机上就是卡顿来源。页面内容只跟分类数据有关，
           依赖不变时整棵子树直接跳过 patch。 -->
      <div
        v-for="entry in pagerPages"
        :key="entry.key"
        v-memo="[entry.key, entry.items, entry.slides]"
        class="campus-pager-page"
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
        <section v-if="!isCustomTab(entry.key)" class="campus-feed">
          <div
            v-for="item in entry.items"
            :key="item.url + item.title"
            class="feed-item"
            role="link"
            tabindex="0"
            @click="openDetail(item.url, item.title)"
            @keydown.enter.prevent="openDetail(item.url, item.title)"
          >
            <div class="feed-body">
              <h3 class="feed-title">{{ item.title }}</h3>
              <div class="feed-meta">
                <span class="feed-time">{{ item.timeLabel }}</span>
                <span class="feed-dot">·</span>
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
                    @click.stop="openDetail(item.url, item.title, 'comment')"
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

        <!-- 收藏：沿用资讯行的版式（标题 + 来源/时间），点整行跳到原帖 -->
        <section v-if="entry.key === 'favorites'" class="campus-feed">
          <p v-if="customTabLoading" class="feed-empty">加载中…</p>
          <p v-else-if="!myFavorites.length" class="feed-empty">还没有收藏的帖子</p>
          <template v-else>
            <div
              v-for="f in myFavorites"
              :key="'fav-' + f.id"
              class="feed-item"
              role="link"
              tabindex="0"
              @click="openFavorite(f)"
              @keydown.enter.prevent="openFavorite(f)"
            >
              <div class="feed-body">
                <h3 class="feed-title">{{ f.title }}</h3>
                <div class="feed-meta">
                  <span class="feed-time">{{ (f.created_at || '').slice(0, 10) }}</span>
                  <span class="feed-dot">·</span>
                  <span class="feed-source">{{ f.category || '收藏' }}</span>
                </div>
              </div>
            </div>
          </template>
        </section>

        <!-- AI 资源：内容与 AI 资源空间同源（爬取的论文 / 开源榜 / 智能体榜 …），
             版式沿用校园资讯行（标题 + 元信息行），点整行打开原文。 -->
        <section v-else-if="entry.key === 'ai_resources'" class="campus-feed ai-feed">
          <!-- 子频道：论文 / 开源 / 智能体 …，与 AI 资源空间同一套分类口径 -->
          <div class="ai-channels">
            <button
              v-for="c in AI_CHANNELS"
              :key="c.key"
              type="button"
              class="ai-channel"
              :class="{ 'is-active': aiChannel === c.key }"
              @click="switchAiChannel(c.key)"
            >{{ c.label }}</button>
          </div>
          <p v-if="aiLoading" class="feed-empty">加载中…</p>
          <p v-else-if="!aiFeeds.length" class="feed-empty">暂无 AI 资源</p>
          <template v-else>
            <div
              v-for="f in aiFeeds"
              :key="'res-' + f.source_type + '-' + f.id"
              class="feed-item"
              role="link"
              tabindex="0"
              @click="openFeed(f)"
              @keydown.enter.prevent="openFeed(f)"
            >
              <div class="feed-body">
                <h3 class="feed-title">{{ f.title }}</h3>
                <div class="feed-meta">
                  <span class="feed-time">{{ feedDateLabel(f.published_at) }}</span>
                  <span class="feed-dot">·</span>
                  <span class="feed-source">{{ f.source_name || AI_DEFAULT_SOURCE[f.source_type] }}</span>
                  <span class="feed-dot">·</span>
                  <span class="feed-source">{{ aiChannelLabel(f.source_type) }}</span>
                </div>
              </div>
            </div>
          </template>
        </section>
      </div>
    </div>
    </div>

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

    <!-- ② 我的收藏 / AI 资源（与移动端两个 Tab 同一份数据，桌面版式保留入口） -->
    <section class="campus-section">
      <div class="section-title">我的收藏</div>
      <div class="campus-card">
        <p v-if="customTabLoading" class="feed-empty">加载中…</p>
        <p v-else-if="!myFavorites.length" class="feed-empty">还没有收藏的帖子</p>
        <template v-else>
        <div
          v-for="f in myFavorites.slice(0, 6)"
          :key="'d-fav-' + f.id"
          class="feed-item"
          role="link"
          tabindex="0"
          @click="openFavorite(f)"
          @keydown.enter.prevent="openFavorite(f)"
        >
          <div class="feed-body">
            <h3 class="feed-title">{{ f.title }}</h3>
            <div class="feed-meta">
              <span class="feed-time">{{ (f.created_at || '').slice(0, 10) }}</span>
              <span class="feed-dot">·</span>
              <span class="feed-source">{{ f.category || '收藏' }}</span>
            </div>
          </div>
        </div>
        </template>
      </div>
    </section>

    <section class="campus-section">
      <div class="section-title">AI 资源</div>
      <div class="campus-card">
        <p v-if="aiLoading" class="feed-empty">加载中…</p>
        <p v-else-if="!aiFeeds.length" class="feed-empty">暂无 AI 资源</p>
        <template v-else>
        <div
          v-for="f in aiFeeds.slice(0, 6)"
          :key="'d-res-' + f.source_type + '-' + f.id"
          class="feed-item"
          role="link"
          tabindex="0"
          @click="openFeed(f)"
          @keydown.enter.prevent="openFeed(f)"
        >
          <div class="feed-body">
            <h3 class="feed-title">{{ f.title }}</h3>
            <div class="feed-meta">
              <span class="feed-time">{{ feedDateLabel(f.published_at) }}</span>
              <span class="feed-dot">·</span>
              <span class="feed-source">{{ f.source_name || AI_DEFAULT_SOURCE[f.source_type] }}</span>
            </div>
          </div>
        </div>
        </template>
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

    <!-- ⑤ 绵城印象 + 图书馆 -->
    <section class="campus-duo campus-duo-lib">
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
      <div class="campus-card campus-card-library" v-tilt>
        <div class="card-head">
          <span class="card-title"><el-icon><Reading /></el-icon> 图书馆公告</span>
          <a v-if="libraryHome" class="card-more" :href="libraryHome" @click.prevent="openArticle(libraryHome, '图书馆')">进入官网 →</a>
        </div>
        <div class="lib-list">
          <!-- 移动端统一展示 5 条（与教学动态/通知公告列表一致）；桌面端维持 4 条 -->
          <a v-for="a in impression.library.slice(0, 4)" :key="a.title" class="lib-item" :href="a.url" @click.prevent="openArticle(a.url, a.title)">
            <span class="lib-date">{{ formatDate(a.date) }}</span>
            <span class="lib-title">{{ a.title }}</span>
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
    <ArticleReader ref="readerRef" />

    <!-- 移动端全屏搜索子页（移动端页头放大镜的落点；桌面端仍走上面的 el-dialog）：
         搜索历史 / 搜索发现 / 热榜三段 + 结果视图，资讯池由父页备好传入。
         点资讯命中条目 → 详情子页盖在本页之上（同 z-index、后挂载者在上），
         详情返回后仍停留在搜索页，搜索上下文不丢。 -->
    <CampusSearchPage
      v-if="searchTarget"
      :items="searchPool"
      @closed="searchTarget = false"
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
      @close="closeDetail"
      @closed="onDetailClosed"
      @updated="onDetailUpdated"
      @read="onDetailRead"
    />

    <!-- 互动消息面板（论坛侧，与聊天隔离）：页头信封点开的也是这个 -->
    <ForumInboxSheet v-model="forumInboxOpen" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, nextTick, onMounted, watch } from 'vue'
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
import { useUnreadSummary } from '@/composables/useUnreadSummary'
import { useMobileSubPage } from '@/composables/useMobileSubPage'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { getArticleInteractions, type CampusArticleInteract } from '@/api/campus'
import {
  Calendar, Monitor, DataLine, Reading, TrendCharts,
  Document, Clock, Box, Van, ArrowRight,
  Notification, DataBoard,
  School, Collection,
  SetUp, Histogram, HomeFilled, OfficeBuilding, Search, Message,
  ChatDotRound, View
} from '@element-plus/icons-vue'
import { searchKnowledge, type KnowledgeHit } from '@/api/knowledge'
import { getFavorites, getFeeds, type Favorite, type FeedItem as FeedEntry, type FeedSourceType } from '@/api/resources'
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

const vTilt = tilt
const isMobile = ref(window.innerWidth <= 767)
window.addEventListener('resize', () => { isMobile.value = window.innerWidth <= 767 })
// 从桌面宽度缩回移动端时 Tab 才重新渲染：落位后再量一次滑条基准
watch(isMobile, v => { if (v) void nextTick(measureTabs) })

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

/** 「收藏」Tab：我的收藏（资源收藏接口） */
const myFavorites = ref<Favorite[]>([])
/** 「AI资源」Tab：外部资讯中心抓取条目（论文 / 开源榜 / 智能体榜 …），与 AI 资源空间同一份数据 */
const aiFeedCache = reactive<Partial<Record<FeedSourceType, FeedEntry[]>>>({})
/** AI资源子频道：默认「论文」，与 AI 资源空间默认频道一致 */
const aiChannel = ref<FeedSourceType>('papers')
/** AI资源子频道定义（顺序与 AI 资源空间一致） */
const AI_CHANNELS: { key: FeedSourceType; label: string }[] = [
  { key: 'papers', label: '论文' },
  { key: 'opensource', label: '开源' },
  { key: 'agents', label: '智能体' },
  { key: 'news', label: '要闻' },
  { key: 'ai_news', label: '行业' },
  { key: 'rankings', label: '权威' },
  { key: 'cn_ai', label: '国产' },
]
/** 每个频道兜底来源名（接口没给 source_name 时用） */
const AI_DEFAULT_SOURCE: Record<FeedSourceType, string> = {
  papers: 'arXiv',
  opensource: '开源项目榜',
  agents: '智能体榜',
  news: '权威要闻',
  ai_news: 'AI 行业',
  rankings: '权威排行榜',
  cn_ai: '国产模型',
}
const aiFeeds = computed(() => aiFeedCache[aiChannel.value] ?? [])
/** 这两个非资讯 Tab 的加载态 */
const customTabLoading = ref(false)
/** AI资源子频道加载态 */
const aiLoading = ref(false)

async function loadAiChannel(type: FeedSourceType, force = false) {
  if (!force && aiFeedCache[type]?.length) return
  aiLoading.value = true
  try {
    const rows = await getFeeds({ source_type: type, limit: 20 })
    aiFeedCache[type] = Array.isArray(rows) ? rows : []
  } catch {
    aiFeedCache[type] = aiFeedCache[type] ?? []
  } finally {
    aiLoading.value = false
  }
}

function switchAiChannel(type: FeedSourceType) {
  if (aiChannel.value === type) return
  aiChannel.value = type
  void loadAiChannel(type)
}

/** 频道的分类标签（元信息行里的小标签） */
function aiChannelLabel(type: FeedSourceType) {
  return AI_CHANNELS.find(c => c.key === type)?.label || 'AI'
}
/** 条目日期：只显示到天，抓取时间对读者没意义 */
function feedDateLabel(iso: string | null) {
  if (!iso) return '最近'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '最近'
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function loadCustomTabData() {
  customTabLoading.value = true
  try {
    const favs = await getFavorites().catch(() => [] as Favorite[])
    myFavorites.value = Array.isArray(favs) ? favs : []
  } finally {
    customTabLoading.value = false
  }
  void loadAiChannel(aiChannel.value)
}

/** 站内路径直接跳；站外链接新开页签 */
function openSavedLink(link: string | null) {
  if (!link) return
  if (link.startsWith('/')) router.push(link)
  else window.open(link, '_blank', 'noopener')
}
function openFavorite(f: Favorite) { openSavedLink(f.link) }
function openFeed(f: FeedEntry) { openSavedLink(f.link) }

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
    library: bySource('library'),
    collegeNews: groupCollegeNews(all),
  }
})

/** 图书馆官网入口：取自后端抓取结果（域名可用 .env 的 LIBRARY_SITE_URL 覆盖）；无数据时不展示死链 */
const libraryHome = computed(() => impression.value.library[0]?.url || '')

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

const SEARCH_HOT_KEYWORDS = ['图书馆', '放假', '招聘', '奖学金', '讲座']

/** source 字段 → 中文名：搜索结果每条都标出来源，用户才知道点进去是什么 */
const SOURCE_LABELS: Record<string, string> = {
  jwc_entries: '系统入口',
  jwc_jxdt: '教学动态',
  jwc_tzgg: '通知公告',
  jwc_gjxx: '高教信息',
  jwc_jxjs: '教学建设',
  college_news: '学院动态',
  library: '图书馆',
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
 * 'following' 是「关注」：只放用户关注的栏目 / 来源的资讯 ——
 *   关注关系与数据源尚未接入，当前 itemsOfTab 固定返回空数组、页面走空态，
 *   后续接后端时只改 itemsOfTab 一处即可（轮播仍只属于推荐页，见 heroSlidesOf）。
 * 其余 5 个与桌面端卡片一一对应：教学动态 / 通知公告 / 教学建设 / 学院动态 / 图书馆。
 * 「高教信息」不设 Tab：移动端信息流不展示该栏目的内容（见 itemsOfTab），
 * 与桌面端「高教信息」卡片并列的只剩「教学建设」，那条桌面布局保持不变。
 */
type FeedTabKey =
  | 'recommend'
  | 'following'
  | 'jwc_jxdt'
  | 'jwc_tzgg'
  | 'jwc_jxjs'
  | 'college_news'
  | 'library'
  | 'favorites'
  | 'ai_resources'

const FEED_TABS: { key: FeedTabKey; label: string }[] = [
  { key: 'recommend', label: '推荐' },
  { key: 'following', label: '关注' },
  { key: 'jwc_jxdt', label: '教学动态' },
  { key: 'jwc_tzgg', label: '通知公告' },
  { key: 'jwc_jxjs', label: '教学建设' },
  { key: 'college_news', label: '学院动态' },
  { key: 'library', label: '图书馆' },
  { key: 'favorites', label: '收藏' },
  { key: 'ai_resources', label: 'AI资源' },
]

/** 这两个 Tab 不是资讯流：数据源是收藏记录 / AI 资源库，模板里单独渲染 */
function isCustomTab(key: FeedTabKey): boolean {
  return key === 'favorites' || key === 'ai_resources'
}

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
  // 关注流：关注关系（用户 → 栏目 / 来源）尚未落地，先返回空数组走空态。
  // 后续接入时在这里按「我关注的来源」过滤即可，口径与推荐流保持一致（同样剔除系统入口）。
  if (key === 'following') return []

  const all = impressionData.value.filter(i => !MOBILE_HIDDEN_SOURCES.includes(i.source))
  if (key === 'recommend') {
    // 合并流：入口项（系统入口）不是资讯，剔除；其余全部参与排序
    return deduplicateByTitle(all.filter(i => i.source !== 'jwc_entries')).sort(byDateDesc)
  }
  return deduplicateByTitle(all.filter(i => i.source === key)).sort(byDateDesc)
}

/** Tab 列表（只含 key/label）：条数不放在 Tab 上 —— 7 个分类 × 数字会把「图书馆」挤出首屏 */
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
 * 点 Tab：内容横向滑过去，与手指切换同一段 200ms。
 * 相邻与跨分类共用一条两页轨道（出发页 + 目标页一次对滑），不逐页播。
 */
function onTabClick(key: FeedTabKey) {
  if (key === activeTab.value) {
    // 已在目标分类：只收掉可能还在跑的拖动 / 吸附 / 换页动画
    cancelPagerMotion()
    return
  }
  startTabSlide(key)
}

/**
 * 点 Tab 的换页动画：
 *   ① 同一帧里把轨道瞬时摆到「出发页」（关过渡，只关轨道，Tab 滑条照常走过渡）；
 *   ② 强制结算这一帧后放开过渡、把 pagerX 推到 0 —— 出发页滑出、目标页滑入；
 *   ③ 200ms 后卸载出发页、轨道瞬时归零（与吸附换页同一套归位做法）。
 * activeTab 在①就落到目标位，所以 Tab 的滑条 / 染色全程是目标态。
 */
function startTabSlide(key: FeedTabKey) {
  const from = activeTab.value
  const fromIndex = FEED_TABS.findIndex(t => t.key === from)
  const toIndex = FEED_TABS.findIndex(t => t.key === key)
  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return

  // 收掉拖动 / 吸附残留（不走 cancelPagerMotion 的 rAF：起手帧要自己控制）
  window.clearTimeout(pagerTimer)
  window.clearTimeout(tabSlideTimer)
  cancelQueuedPagerX()
  pagerDrag = null
  pagerDragging.value = false
  pagerOpen.value = false

  measurePagerWidth()
  const width = pagerWidth.value || pagerRef.value?.clientWidth || window.innerWidth || 320
  const dir: 1 | -1 = toIndex > fromIndex ? 1 : -1

  trackJumping.value = true
  pagerAnimating.value = true // 动画期间不接新手势
  tabClickSwitch.value = true // 点 Tab 不做「逐字扫过」染色，文字随滑条直接落位
  tabSwitch.value = { from, to: key, dir }
  pagerX.value = dir > 0 ? width : -width
  switchTab(key)

  requestAnimationFrame(() => {
    // 先让「关过渡 + 起点位移」结算成上一帧样式，再放开过渡推向终点
    void pagerRef.value?.offsetWidth
    trackJumping.value = false
    pagerX.value = 0
    window.clearTimeout(tabSlideTimer)
    tabSlideTimer = window.setTimeout(finishTabSlide, PAGER_SLIDE_MS + 30)
  })
}

/** 点 Tab 换页收尾：卸载出发页、轨道瞬时归零（当前页是同一个 DOM 节点，画面不跳） */
function finishTabSlide() {
  trackJumping.value = true
  tabSwitch.value = null
  pagerX.value = 0
  requestAnimationFrame(() => {
    void pagerRef.value?.offsetWidth
    trackJumping.value = false
    pagerAnimating.value = false
    // 收尾这一帧再放开染色过渡：重新量 Tab 后裁剪会差 1~2px，
    // 提前放开会让这点差值又补一段「扫过」动画
    tabClickSwitch.value = false
  })
}

/** 中止轨道上的一切位移 / 定时器：把轨道瞬时归位、收起邻居，不再接后续动作 */
function cancelPagerMotion() {
  window.clearTimeout(pagerTimer)
  window.clearTimeout(tabSlideTimer)
  cancelQueuedPagerX()
  pagerDrag = null
  tabSwitch.value = null
  tabClickSwitch.value = false
  pagerAnimating.value = false
  pagerDragging.value = false
  trackJumping.value = true
  pagerResetting.value = true
  pagerOpen.value = false
  pagerX.value = 0
  requestAnimationFrame(() => {
    void pagerRef.value?.offsetWidth
    trackJumping.value = false
    pagerResetting.value = false
  })
}

/* ==================== 移动端：卡片分页（跟手切换分类） ==================== */

/** 分页里的一页：某个分类的完整卡片（「推荐」页额外带顶部大图轮播，「关注」页为空态） */
interface PagerPage {
  key: FeedTabKey
  label: string
  items: FeedItem[]
  slides: HeroSlide[]
}

/**
 * 卡片分页：当前分类居中，左右各挂一页邻居，三张卡片排在同一条横向轨道上。
 *   · 手指往左拖：整条轨道 1:1 跟着走，右侧邻居页从屏幕边缘同步进来 ——
 *     不是松手后才补动画，拖动过程中就已经看得到下一页；
 *   · 松手：位移超过阈值 / 快甩 → 吸附到相邻页；否则回弹归位；
 *   · 吸附完成后：切换 activeTab、把轨道瞬时归零、卸载两侧邻居 —— 当前页始终是
 *     轨道里同一个 DOM 节点（v-for :key 按分类），换页瞬间不重建页面、不会闪；
 *   · 邻居页只在拖动开始时挂载，静止时只渲染当前页，页面高度不被邻居撑高；
 *   · 首 / 尾分类没有对应方向的邻居页：该方向直接不接手势，卡片一动不动 ——
 *     不做阻尼回弹，避免在边缘拉出一条白色空档。
 * 轮播区域不接分类手势（按压必须落在 .campus-feed 上），两套拖动互不干扰。
 * 吸顶的页头 / Tab 保持不动，位移只作用于这条卡片轨道。
 */
const pagerRef = ref<HTMLElement | null>(null)
/** 一页的宽度（px）：页宽 = 分页容器宽度，吸附位移与边界判断都按它算 */
const pagerWidth = ref(0)
/** 是否挂载左右邻居页（拖动开始 → 吸附完成） */
const pagerOpen = ref(false)
/** 轨道正在跟手（关过渡） */
const pagerDragging = ref(false)
/** 换页后瞬时归位（关过渡）：切数据与轨道归零必须在同一帧完成 */
const pagerResetting = ref(false)
/** 吸附 / 回弹动画进行中：不接新手势 */
const pagerAnimating = ref(false)
/** 轨道相对「当前页居中」的位移（px，向左为负） */
const pagerX = ref(0)
/** 点 Tab 换页时轨道瞬时落到「出发页」位（关过渡）：只作用于轨道，不影响 Tab 滑条的过渡 */
const trackJumping = ref(false)

/**
 * 点 Tab 换页动画：不是拖动，但同样在轨道上「出发页滑出、目标页滑入」。
 * 有它时轨道只摆两页（顺序按 Tab 先后），滑条与染色不再跟 pagerX 走 ——
 * 点击后 activeTab 已经直接落到目标位，这两者交给各自的 200ms 过渡。
 */
interface TabSwitch {
  from: FeedTabKey
  to: FeedTabKey
  dir: 1 | -1
}
const tabSwitch = ref<TabSwitch | null>(null)
/** 点 Tab 换页期间：关掉深色文字层的 clip-path 过渡（见 startTabSlide 的注释） */
const tabClickSwitch = ref(false)
let tabSlideTimer: number | undefined

/** 进入拖动态的最小水平位移（px）：低于它算点击，不算滑动 */
const PAGER_DRAG_THRESHOLD = 12
/** 松手判定翻页的最小位移（px） */
const PAGER_SWIPE_THRESHOLD = 56
/** 速度阈值（px/ms）：快甩时即使位移不够也翻页 */
const PAGER_FLING_VELOCITY = 0.35
/** 吸附 / 回弹时长（ms），与样式里的 transform 过渡保持一致 */
const PAGER_SLIDE_MS = 200

function measurePagerWidth() {
  if (pagerRef.value) pagerWidth.value = pagerRef.value.clientWidth
}

/* ---------------- 分类 Tab 的滑条 + 随条染色 ----------------
   下划线不画在选中 Tab 的 ::after 上（那样只能整块闪一下），
   而是一个独立滑条，位置 / 宽度按「当前 Tab → 目标 Tab」的进度插值：
     · 拖动卡片时进度 = |pagerX| / 页宽，滑条与卡片严格同步；
     · 松手吸附 / 点 Tab 时交给 CSS 过渡，200ms 走完，与卡片同一段缓动。
   位置用按钮的 offsetLeft / offsetWidth 量（Tab 行可横向滚动，滑条会跟着滚）。 */
const tabEls = new Map<FeedTabKey, HTMLElement>()
const tabMetrics = ref<{ left: number; width: number }[]>([])

function setTabRef(key: FeedTabKey, el: unknown) {
  if (el instanceof HTMLElement) tabEls.set(key, el)
  else tabEls.delete(key)
}

function measureTabs() {
  tabMetrics.value = mobileTabs.value.map(t => {
    const el = tabEls.get(t.key)
    return el ? { left: el.offsetLeft, width: el.offsetWidth } : { left: 0, width: 0 }
  })
}

/**
 * 滑条几何（相对 Tab 行的 padding box）：左边界 + 宽度。
 * 滑条绘制与深色文字裁剪共用这一份，二者永远不会错位。
 */
const tabBar = computed(() => {
  const index = FEED_TABS.findIndex(t => t.key === activeTab.value)
  const cur = tabMetrics.value[index]
  if (!cur) return null
  const width = pagerWidth.value
  // 点 Tab 换页时 pagerX 只是为了推动轨道，滑条已经直接落到目标位、交给 CSS 过渡，
  // 不能再按 pagerX 插值，否则跨分类点一下会先滑到隔壁 Tab 再折回
  const progress = !tabSwitch.value && width ? Math.min(1, Math.abs(pagerX.value) / width) : 0
  // 卡片往左拖 = 去下一个 Tab；往右拖 = 去上一个 Tab
  const dir = pagerX.value < 0 ? 1 : pagerX.value > 0 ? -1 : 0
  const next = dir ? tabMetrics.value[index + dir] : undefined
  return {
    left: next ? cur.left + (next.left - cur.left) * progress : cur.left,
    width: next ? cur.width + (next.width - cur.width) * progress : cur.width,
  }
})

const tabIndicatorStyle = computed(() => {
  const bar = tabBar.value
  if (!bar) return { transform: 'translate3d(0, 0, 0)', width: '0px', opacity: '0' }
  return {
    transform: `translate3d(${bar.left}px, 0, 0)`,
    width: `${bar.width}px`,
    opacity: '1',
  }
})

/**
 * 每个 Tab 的深色文字裁多少：把滑条的左右边界换算到该 Tab 自己的文字框里。
 * 左 / 右内缩只作用于这一格，所以「条到哪儿，深色字就渲染到哪儿」，
 * 不需要额外一层整行文字去对齐，天然不会重影。
 *
 * 裁剪样式对象按 Tab 复用：拖动时通常只有「当前 / 目标」两格的 inset 在变，
 * 其余 Tab 拿到同一个对象引用，Vue 的 vnode diff 会直接跳过 style patch。
 * 每格只保留最近一次，缓存不会随拖动无限增长。
 */
const clipCache = new Map<FeedTabKey, { value: string; style: { clipPath: string } }>()
function clipStyle(key: FeedTabKey, clipPath: string) {
  const hit = clipCache.get(key)
  if (hit && hit.value === clipPath) return hit.style
  const style = { clipPath }
  clipCache.set(key, { value: clipPath, style })
  return style
}

const tabDarkClip = computed(() => {
  const bar = tabBar.value
  const clips = {} as Record<FeedTabKey, { clipPath: string }>
  mobileTabs.value.forEach((t, i) => {
    const rect = tabMetrics.value[i]
    if (!bar || !rect || !rect.width) {
      clips[t.key] = clipStyle(t.key, 'inset(0 100% 0 0)')
      return
    }
    const left = Math.min(Math.max(bar.left - rect.left, 0), rect.width)
    const right = Math.min(
      Math.max(rect.left + rect.width - (bar.left + bar.width), 0),
      rect.width - left,
    )
    clips[t.key] = clipStyle(t.key, `inset(0 ${right}px 0 ${left}px)`)
  })
  return clips
})

/** 轨道上要渲染的页：拖动时是 [上一页, 当前页, 下一页]，静止时只有当前页 */
const pagerPages = computed<PagerPage[]>(() => {
  const index = FEED_TABS.findIndex(t => t.key === activeTab.value)
  const build = (i: number): PagerPage => ({
    key: FEED_TABS[i].key,
    label: FEED_TABS[i].label,
    items: feedItemsOf(FEED_TABS[i].key),
    slides: heroSlidesOf(FEED_TABS[i].key),
  })
  const pages: PagerPage[] = []
  const sw = tabSwitch.value
  // 点 Tab 换页：轨道上只摆「出发页 + 目标页」，两页一次对滑 ——
  // 跨多个分类也只走一次 200ms，不逐页播；顺序按 Tab 先后，方向与手指切换一致
  if (sw) {
    const fromIndex = FEED_TABS.findIndex(t => t.key === sw.from)
    const toIndex = FEED_TABS.findIndex(t => t.key === sw.to)
    if (fromIndex >= 0 && toIndex >= 0) {
      return sw.dir > 0
        ? [build(fromIndex), build(toIndex)]
        : [build(toIndex), build(fromIndex)]
    }
  }
  if (pagerOpen.value && index > 0) pages.push(build(index - 1))
  pages.push(build(index))
  if (pagerOpen.value && index < FEED_TABS.length - 1) pages.push(build(index + 1))
  return pages
})

/** 当前页在渲染数组里的下标：0 = 最左，1 = 中间，2 = 最右 */
const pagerAnchor = computed(() =>
  Math.max(0, pagerPages.value.findIndex(p => p.key === activeTab.value)),
)

/**
 * 轨道位移 = 「把当前页挪到中点」的基准偏移 + 手指位移。
 * 收尾换页时 activeTab 变化会改变基准偏移，同时 pagerX 归零 —— 两者在同一次渲染里
 * 相互抵消，画面上当前页仍停在原处，所以看不到跳动。
 */
const pagerTransform = computed(() => {
  const offset = -pagerAnchor.value * pagerWidth.value + pagerX.value
  return `translate3d(${offset}px, 0, 0)`
})

interface PagerDragState {
  pointerId: number
  startX: number
  startY: number
  lastX: number
  lastTime: number
  /** 已越过阈值、进入拖动 */
  active: boolean
  /** 已判定为纵向滚动，本次手势彻底放弃 */
  locked: boolean
}
let pagerDrag: PagerDragState | null = null
/** 上一次手势是滑动（而非轻点）：随后紧跟着的 click 要吞掉，否则一滑完就点进了文章 */
let pagerSuppressClick = false
let pagerTimer: number | undefined
/** 跟手位移按帧提交：同一帧内多次 pointermove 只触发一次渲染 */
let pagerRaf = 0
let pendingPagerX = 0

function queuePagerX(x: number) {
  pendingPagerX = x
  if (pagerRaf) return
  pagerRaf = requestAnimationFrame(() => {
    pagerRaf = 0
    pagerX.value = pendingPagerX
  })
}

/** 吸附 / 回弹要直接写目标值：先丢掉还排队的跟手帧，避免它把动画目标覆盖回去 */
function cancelQueuedPagerX() {
  if (pagerRaf) {
    cancelAnimationFrame(pagerRaf)
    pagerRaf = 0
  }
  pendingPagerX = 0
}

function onPagerPointerDown(e: PointerEvent) {
  // 每次按下先复位：避免上一次滑动没产生 click 时，把下一次正常点击吞掉
  pagerSuppressClick = false
  cancelQueuedPagerX()
  if (!isMobile.value || pagerAnimating.value) return
  // 只处理主键 / 单指；右键与双指不接管
  if (e.pointerType === 'mouse' && e.button !== 0) return
  if (!e.isPrimary) return
  const target = e.target as HTMLElement | null
  // 只从信息流上起手：轮播图片有自己的拖动；行内互动按钮优先当点击
  if (!target?.closest('.campus-feed')) return
  if (target.closest('button')) return
  measurePagerWidth()
  // 滑条位置按 Tab 按钮实测宽度算：起手时重新量一次，避免字体 / 宽度变化后对不上
  measureTabs()
  pagerDrag = {
    pointerId: e.pointerId,
    startX: e.clientX,
    startY: e.clientY,
    lastX: e.clientX,
    lastTime: Date.now(),
    active: false,
    locked: false,
  }
}

function onPagerPointerMove(e: PointerEvent) {
  const d = pagerDrag
  if (!d || d.pointerId !== e.pointerId || d.locked) return
  const dx = e.clientX - d.startX
  const dy = e.clientY - d.startY
  const index = FEED_TABS.findIndex(t => t.key === activeTab.value)
  // 这个方向有没有邻居页：往右拖要有上一页，往左拖要有下一页
  const hasTarget = dx < 0 ? index < FEED_TABS.length - 1 : index > 0

  // 未越过阈值：先定方向。纵向为主 → 交还页面滚动，本次手势放弃
  if (!d.active) {
    if (Math.abs(dy) > PAGER_DRAG_THRESHOLD && Math.abs(dy) > Math.abs(dx)) {
      d.locked = true
      return
    }
    if (Math.abs(dx) <= PAGER_DRAG_THRESHOLD) return
    // 已在最左 / 最右分类：该方向没有邻居页，不接管手势 —— 卡片固定不动，
    // 既不露白也不回弹；手指抬起后仍是普通点击
    if (!hasTarget) return
    d.active = true
    // 邻居页与位移同一次渲染上屏：从第一帧起三张卡片就在轨道上
    pagerOpen.value = true
    pagerDragging.value = true
    // 捕获指针：手指滑出列表区域也不丢 up 事件
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  d.lastX = e.clientX
  d.lastTime = Date.now()
  // 1:1 跟手；起步后把方向反向拉过起点（该方向没有邻居）时硬停在 0，同样不露白
  queuePagerX(hasTarget ? dx : 0)
}

function onPagerPointerUp(e: PointerEvent) {
  const d = pagerDrag
  pagerDrag = null
  if (!d || d.pointerId !== e.pointerId) return
  // 松手后由吸附 / 回弹直接写目标值，丢掉还没落地的跟手帧
  cancelQueuedPagerX()

  // 没进入拖动（轻点）或已判定为纵向滚动：直接归位，click 照常交给行 / 按钮
  if (!d.active || d.locked) {
    pagerX.value = 0
    pagerDragging.value = false
    return
  }

  // 滑动过：吞掉随后那次 click
  pagerSuppressClick = true
  window.setTimeout(() => { pagerSuppressClick = false }, 350)

  const dx = e.clientX - d.startX
  const dt = Math.max(1, Date.now() - d.lastTime)
  const velocity = (e.clientX - d.lastX) / dt
  const wantNext = dx < 0 && (Math.abs(dx) > PAGER_SWIPE_THRESHOLD || velocity < -PAGER_FLING_VELOCITY)
  const wantPrev = dx > 0 && (Math.abs(dx) > PAGER_SWIPE_THRESHOLD || velocity > PAGER_FLING_VELOCITY)

  const index = FEED_TABS.findIndex(t => t.key === activeTab.value)
  const targetIndex = wantNext ? index + 1 : wantPrev ? index - 1 : -1

  // 已到首 / 尾分类，或位移不够：回弹
  if (targetIndex < 0 || targetIndex >= FEED_TABS.length) {
    springBackPager()
    return
  }

  snapPager(wantNext ? 'next' : 'prev', FEED_TABS[targetIndex].key)
}

/**
 * 回弹：轨道滑回当前页，动画结束后收起邻居页。
 * 邻居页卸载时当前页仍在原位，所以不会有任何位移。
 */
function springBackPager() {
  cancelQueuedPagerX()
  pagerAnimating.value = true
  pagerDragging.value = false
  pagerX.value = 0
  window.clearTimeout(pagerTimer)
  pagerTimer = window.setTimeout(closePager, PAGER_SLIDE_MS + 20)
}

/**
 * 吸附到相邻页：轨道滑到 ±页宽（此时邻居正好落在中位）。
 * 动画结束后在同一帧里做三件事：切分类、把轨道归零、卸载邻居 ——
 * 当前页始终是同一个 DOM 节点（:key 按分类），画面不重建、不闪。
 */
function snapPager(direction: 'next' | 'prev', key: FeedTabKey) {
  const width = pagerWidth.value || pagerRef.value?.clientWidth || window.innerWidth || 320
  cancelQueuedPagerX()
  pagerAnimating.value = true
  pagerDragging.value = false
  pagerX.value = direction === 'next' ? -width : width
  window.clearTimeout(pagerTimer)
  pagerTimer = window.setTimeout(() => {
    pagerResetting.value = true
    switchTab(key)
    pagerOpen.value = false
    pagerX.value = 0
    requestAnimationFrame(() => {
      // 强制结算归位后的这一帧，再恢复过渡，避免残留目标值再补一段动画
      void pagerRef.value?.offsetWidth
      pagerResetting.value = false
      pagerAnimating.value = false
    })
  }, PAGER_SLIDE_MS + 20)
}

/** 收起邻居页：当前页仍在原位，卸载邻居不产生视觉位移 */
function closePager() {
  cancelQueuedPagerX()
  pagerResetting.value = true
  pagerOpen.value = false
  pagerX.value = 0
  requestAnimationFrame(() => {
    void pagerRef.value?.offsetWidth
    pagerResetting.value = false
    pagerAnimating.value = false
  })
}

function onPagerPointerCancel() {
  // 被系统打断（来电、手势返回、双指缩放）：回弹，不翻页
  pagerDrag = null
  cancelQueuedPagerX()
  if (!pagerOpen.value) {
    pagerX.value = 0
    pagerDragging.value = false
    return
  }
  springBackPager()
}

/** 滑动结束后那一次 click 在此截停：不让它落到行（进详情）或按钮上 */
function onPagerClickCapture(e: MouseEvent) {
  if (!pagerSuppressClick) return
  pagerSuppressClick = false
  e.preventDefault()
  e.stopPropagation()
}

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
  return itemsOfTab(key).map(i => {
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
}

/** 当前分类的信息流（详情页取来源、页面渲染都读这一份） */
const mobileFeed = computed<FeedItem[]>(() => feedItemsOf(activeTab.value))

/**
 * 信息流空态文案。
 * 「关注」是空态的常客（关注关系还没接，itemsOfTab 固定返回空数组），
 * 单独给一句中性说明；等关注功能落地后，这里换成「还没有关注的栏目」之类的引导文案。
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

// 校园资讯的搜索页 / 文章详情 / 论坛信箱属于二级页，打开时让出移动端底部悬浮导航
useMobileSubPage(computed(() => isMobile.value && (searchTarget.value || !!detailTarget.value || forumInboxOpen.value)))

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

/** 子页退场播完：真正卸载，并把详情里改过的互动数同步回信息流 */
function onDetailClosed() {
  detailTarget.value = null
  interactionMap.value = { ...interactionMap.value }
}

/**
 * 详情子页点「阅读全文」：正文不在详情页渲染，交给站内阅读器（ArticleReader）。
 * 先关详情再开阅读器：两者都是整页覆盖层，同时挂载会互相抢 body 滚动锁与 z-index；
 * 先收起讨论页、露出阅读器，视觉上是「讨论 → 阅读」的一次正常推进，不会叠层。
 */
function onDetailRead(url: string) {
  const title = detailTarget.value?.title || ''
  closeDetail()
  nextTick(() => openArticle(url, title))
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
  // 分页宽度要等 DOM 渲染完才能量：吸附位移、边界判断都按它算
  void nextTick(measurePagerWidth)
  // Tab 滑条同样要等按钮落位后再量；字体异步加载完成后再补量一次
  void nextTick(measureTabs)
  void document.fonts?.ready.then(measureTabs)
  // 收藏 / AI资源 Tab 的数据与资讯流缓存无关，单独拉取（失败静默走空态）
  void loadCustomTabData()
  // 深链：个人中心「收藏的帖子」→ /student/campus?tab=favorites
  const tabParam = route.query.tab
  if (typeof tabParam === 'string' && FEED_TABS.some(t => t.key === tabParam)) {
    activeTab.value = tabParam as FeedTabKey
  }
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
   原先这里用 4px 圆角小竖条 + 16px/600，与页内「通知公告 / 专业分院 / 图书馆公告」
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
   与嵌在 .campus-duo-lib 里、保住了 .campus-card 的 16px 18px 的
   「图书馆公告」标题不齐。
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

/* ===== Library ===== */
.campus-card-library { flex: 0.8; }
.lib-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.lib-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
  cursor: pointer;
  transition: background .2s ease;
}
.lib-item:last-child { border-bottom: none; }
.lib-item:hover { background: #ecf5ff; }
.lib-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #7a8694;
  width: 45px;
  text-align: center;
}
.lib-title {
  flex: 1;
  font-size: 13px;
  color: #42505f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color .2s ease;
}
.lib-item:hover .lib-title {
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
     分割线统一放在顶栏最下沿（见 .campus-tabs）。 */
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

  /* ---------- 分类 Tab：吸顶在页头下沿 ----------
     是白卡的第二段（紧接页头，白底）；15px，选中项深色（不变字重）+ 3px 黑色下划线（与文字等宽）。
     吸顶偏移量 = 页头高度（--campus-appbar-h），两层无缝拼成一个白色顶栏；
     滚到信息流任何位置都能直接切分类，不用先滚回顶部。
     层级压在页头之下（30 > 25），但高于信息流里带 z-index 的轮播指示点（6）。
     最下沿一条极浅分割线：白色顶栏与下方滚动内容之间留一个层级边界。
     overflow-x 仍是 auto：吸顶不影响这一行自身的横向滑动。 */
  .campus-tabs {
    position: sticky;
    top: var(--campus-appbar-h);
    z-index: 25;
    display: flex;
    align-items: center;
    /* 滑条绝对定位在这条 Tab 行里（sticky 本身就是定位元素，随内容横向滚动） */
    /* 参考稿分类之间留白很紧（「全部 / 热榜 / CS2」几乎贴着），22px 会撑得过宽，
       导致第 6 个分类被截断显示成「专」这种半截字。收到 16px。 */
    gap: 16px;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
    margin: 0;
    padding: 8px 16px 10px;
    background: #fff;
    box-shadow: 0 1px 0 #f0f1f3;
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    border-bottom: 0;
    border-radius: 0;
  }
  .campus-tabs::-webkit-scrollbar { display: none; }
  .campus-tab {
    position: relative;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    padding: 0 0 8px;
    background: none;
    border: 0;
    /* 参考稿 Tab 比标题小一号（标题 26、Tab 约 15），16px 会让一行放不下 6 个分类 */
    font-size: 15px;
    /* 按钮默认字体不继承页面：深色文字层用的是同款 span，必须显式继承，
       两层文字的字体 / 字宽才会完全一致，裁剪边界才对得上 */
    font-family: inherit;
    font-weight: 400;
    color: #86909c;
    cursor: pointer;
    transition: color .18s ease;
    -webkit-tap-highlight-color: transparent;
  }
  /* 拖动中颜色 / 裁剪都是逐帧写入的，不能再走过渡 —— 否则会滞后于卡片与滑条 */
  .campus-tabs.is-pager-dragging .campus-tab {
    transition: none;
  }
  /* Tab 文字：两层同宽文字叠在按钮内容框里。
     底层永远是灰色；上层是同款深色，用 clip-path 只留滑条覆盖的那一段 ——
     「条到哪儿，深色文字就渲染到哪儿」，条走到两个 Tab 中间时，
     左边那段字深、右边那段字灰，分界线与条严格重合。 */
  .campus-tab-label {
    display: block;
    white-space: nowrap;
    text-align: left;
  }
  .campus-tab-label-dark {
    position: absolute;
    /* 四边都贴着按钮内容框：底部让开 8px（下划线留白），与真实文字框完全重合 */
    inset: 0 0 8px 0;
    color: #1d2129;
    pointer-events: none;
    transition: clip-path 200ms cubic-bezier(.22, .61, .36, 1);
  }
  .campus-tabs.is-pager-dragging .campus-tab-label-dark,
  .campus-tabs.is-pager-resetting .campus-tab-label-dark,
  .campus-tabs.is-tab-instant .campus-tab-label-dark {
    transition: none;
  }
  /* 选中下划线：独立滑条（不是 is-active::after），宽度随 Tab 文字宽度变化。
     位置 / 宽度由 tabIndicatorStyle 逐帧写入：
       · 拖动卡片时关过渡，跟手指 1:1 在相邻 Tab 之间挪；
       · 松手吸附 / 点 Tab 时开过渡，200ms 与卡片同一段缓动滑到目标位；
       · 换页归零那一帧关过渡（类名由 .campus-tabs 上的状态控制），避免倒着补动画。
     下沿对齐 Tab 文字底部：Tab 行 padding-bottom 10px，滑条 bottom 也取 10px。 */
  .campus-tab-indicator {
    position: absolute;
    left: 0;
    bottom: 10px;
    height: 3px;
    border-radius: 0;
    background: #1d2129;
    pointer-events: none;
    will-change: transform, width;
    transition:
      transform 200ms cubic-bezier(.22, .61, .36, 1),
      width 200ms cubic-bezier(.22, .61, .36, 1);
  }
  .campus-tabs.is-pager-dragging .campus-tab-indicator,
  .campus-tabs.is-pager-resetting .campus-tab-indicator {
    transition: none;
  }

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
     三张卡片（上一页 / 当前页 / 下一页）首尾相接排在同一条横向轨道上：
     手指往左拖时整条轨道跟着走，当前页跟手、右侧邻居页从边缘同步进来。
     位移由 pagerX 驱动（模板内联 transform）；这里只管过渡与手势归属：
       · 常态：200ms 过渡，用于吸附 / 回弹；
       · 拖动中 / 换页归位：关掉过渡，位移严格跟手 / 瞬时归位；
       · 裁切必须由**不参与位移的外层**（.campus-pager-viewport）负责：
         如果把 overflow: hidden 挂在会 translate 的轨道上，裁切框会跟着轨道一起
         移走 —— 轨道平移到 ±一页宽时，可视区正好落在裁切框之外，整页变空白。
         外层裁切后，邻居页只在真正进入内容区后才可见，也不会溢到左右 16px 边距里。 */
  .campus-pager-viewport {
    position: relative;
    width: 100%;
    flex-shrink: 0;
    overflow: hidden;
  }
  .campus-pager {
    display: flex;
    width: 100%;
    flex-shrink: 0;
    transition: transform 200ms cubic-bezier(.22, .61, .36, 1);
    touch-action: pan-y;            /* 横向手势交给 Pointer 逻辑，纵向仍归页面滚动 */
    -webkit-user-select: none;
    user-select: none;
  }
  .campus-pager.is-pager-dragging,
  .campus-pager.is-pager-resetting,
  .campus-pager.is-pager-jumping {
    transition: none;
  }
  .campus-pager.is-pager-dragging { will-change: transform; }
  /* 吸附 / 回弹动画进行中不响应点按：避免落在还没停稳的邻居页上误开文章 */
  .campus-pager.is-pager-animating { pointer-events: none; }
  /* 拖动 / 吸附过程中整条轨道垫白：边界分类回弹时露出的边缘也是白卡，
     不会闪出一条页面底色；收起邻居页后撤掉（当前页自带白底与圆角）。 */
  .campus-pager.is-pager-open { background: #fff; }
  /* 拖动中不保留按下态的压暗：滑动是切分类，不是「按住这一行」 */
  .campus-pager.is-pager-dragging .feed-item:active { opacity: 1; }

  /* 一张卡片 = 一个分类的完整内容：「推荐」页是轮播 + 信息流，「关注」页只有空态，其余只有信息流。
     flex: 0 0 100% 让每页正好占满一屏宽（100% 相对轨道自身宽度，轨道宽度 = 内容区宽）。
     页容器自带白底与下圆角：邻居页比当前页矮时也能把卡片补齐，拖动时不会露底色。 */
  .campus-pager-page {
    flex: 0 0 100%;
    width: 100%;
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

  /* ---------- AI资源子频道 ----------
     横向可滑的胶囊标签行，压在信息流上方。
     与页面 Tab 区分：Tab 是文字 + 下划线，这里用浅灰胶囊，一眼看出是「二级筛选」。 */
  .ai-channels {
    display: flex;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    padding: 4px 0 12px;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }
  .ai-channels::-webkit-scrollbar { display: none; }
  .ai-channel {
    flex-shrink: 0;
    padding: 5px 12px;
    border-radius: 999px;
    border: 1px solid #ebedf0;
    background: #f7f8fa;
    font-family: inherit;
    font-size: 12px;
    line-height: 1.5;
    color: #86909c;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background .16s ease, color .16s ease, border-color .16s ease;
  }
  .ai-channel:active { opacity: .72; }
  .ai-channel.is-active {
    background: #1d2129;
    border-color: #1d2129;
    color: #fff;
    font-weight: 600;
  }
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
     绵城印象 / 图书馆）都包在桌面端 <template v-if="!isMobile"> 里，不再渲染，
     因此这里无需再为它们写移动端覆盖样式；
     若后续要恢复某个卡片到移动端，把它移出该 template 并在此补样式即可。 */
}
</style>

