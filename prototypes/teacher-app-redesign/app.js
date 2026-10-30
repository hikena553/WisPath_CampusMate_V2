/* =========================================================================
   app.js · 原型交互层（状态 / 渲染 / 事件委托）
   静态外壳在 index.html 内联；本文件只负责填充内容与切换，不重写导航骨架。
   ------------------------------------------------------------------
   v2：为「常用功能」九个功能实现九套专属子页面版式 + 统一的底部弹窗体系。
   组件范式对齐开源成熟方案：Ant Design Mobile（Popup / ActionSheet / Steps /
   Timeline / Progress / Badge / Empty）；图标为 Lucide（ISC）内联 sprite。
   ========================================================================= */
(function () {
  'use strict';

  /* ---------------- 小工具 ---------------- */
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const nl = (s) => esc(s).replace(/\n/g, '<br>');

  function icon(name, size, extra) {
    const s = size || 18;
    return '<svg class="ic ' + (extra || '') + '" width="' + s + '" height="' + s + '" viewBox="0 0 24 24" ' +
      'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<use href="#i-' + name + '"></use></svg>';
  }

  /* 语义色 → soft 底 + 深色字（取自自研令牌，与真实产品同源） */
  const TONE = {
    brand:  { bg: 'var(--tui-brand-soft)',  fg: 'var(--tui-brand-strong)' },
    success:{ bg: 'var(--tui-success-soft)',fg: 'var(--tui-success)' },
    warn:   { bg: 'var(--tui-warn-soft)',   fg: 'var(--tui-warn)' },
    danger: { bg: 'var(--tui-danger-soft)', fg: 'var(--tui-danger)' },
    violet: { bg: 'var(--tui-violet-soft)', fg: 'var(--tui-violet)' },
    cyan:   { bg: 'var(--tui-cyan-soft)',   fg: 'var(--tui-cyan)' },
    pink:   { bg: 'var(--tui-pink-soft)',   fg: 'var(--tui-pink)' },
    blue:   { bg: 'var(--tui-blue-500-soft)', fg: 'var(--tui-blue-500)' },
    quiet:  { bg: 'var(--tui-surface-sunken)', fg: 'var(--tui-text-tertiary)' },
  };
  const tagCls = { brand: 'tag-brand', success: 'tag-success', warn: 'tag-warn', danger: 'tag-danger', violet: 'tag-violet', cyan: 'tag-cyan', pink: '', blue: '', quiet: '' };

  function tile(tone, icName, size, radius) {
    const t = TONE[tone] || TONE.brand;
    const r = radius || 10;
    return '<span class="row-icon" style="background:' + t.bg + ';color:' + t.fg + ';border-radius:' + r + 'px">' +
      icon(icName, size || 18) + '</span>';
  }
  function tag(text, tone) {
    return '<span class="tag ' + (tagCls[tone] || '') + '">' + esc(text) + '</span>';
  }
  function count(n, tone) {
    if (!n) return '';
    return '<span class="count ' + (tone || '') + '">' + (n > 99 ? '99+' : n) + '</span>';
  }

  /* 模块签名色（六色以内 + 语义扩展，均取自 Untitled UI 开源色板） */
  const MOD_TONE = {
    approval: 'warn', crisis: 'danger', announcement: 'brand', portfolio: 'violet',
    survey: 'cyan', care: 'pink', guardian: 'blue', tasks: 'success', ai: 'violet',
  };
  const ACCENT = {
    brand:   { c: '#2563eb', s: '#eff4ff' },
    success: { c: '#079455', s: '#ecfdf3' },
    warn:    { c: '#b54708', s: '#fffaeb' },
    danger:  { c: '#d92d20', s: '#fef3f2' },
    violet:  { c: '#7a5af8', s: '#f4f3ff' },
    cyan:    { c: '#0891b2', s: '#ecfeff' },
    pink:    { c: '#c11574', s: '#fdf2fa' },
    blue:    { c: '#1570ef', s: '#eff8ff' },
    quiet:   { c: '#6b7280', s: '#eceef1' },
  };
  function accentOf(key) { return ACCENT[MOD_TONE[key]] || ACCENT.brand; }

  /* ---------------- 状态 ---------------- */
  const state = {
    tab: 'home',
    mc: 'msg',            // msg | contacts | noti
    mcDrawer: false,
    swiped: null,
    orgOpen: {},
    pinned: {},
    layers: [],
    chatInput: '',
    attachOpen: false,
    toast: null,
    /* v2 */
    subId: null,          // 当前功能模块 key
    seg: {},              // 各模块分段索引
    chip: {},             // 弹窗内单选 chips
    multi: {},            // 弹窗内多选
    pick: { portfolio: 'u1' },  // 成长档案选中学生
    tasksDone: {},        // 任务勾选态
    sheet: null,          // { key, ctx }
    /* v3 */
    stuTab: 'overview',   // 学生详情锚点 Tab
    stuLike: {},          // 主页点赞态
    activeStudent: null,  // 当前查看的学生 id
  };
  let CONVS = [];

  function toast(msg) {
    state.toast = msg;
    const box = $('#toast');
    box.textContent = msg;
    box.classList.add('on');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => box.classList.remove('on'), 1600);
  }

  /* =====================================================================
     首页
     ===================================================================== */
  function renderHome() {
    const me = window.DB.me;
    const entries = window.DB.quickEntries;
    const hour = new Date().getHours();
    const hi = hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好';
    const d = new Date();
    const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()];
    const dateStr = d.getFullYear() + '年' + (d.getMonth() + 1) + '月' + d.getDate() + '日 星期' + week;

    const grid = entries.map((e) => {
      const t = TONE[e.tone] || TONE.brand;
      return '<button class="nav-cell" data-open-sub="' + e.id + '">' +
        '<span class="nav-icon" style="background:' + t.bg + ';color:' + t.fg + '">' + icon(e.icon, 22) + '</span>' +
        '<span class="nav-label">' + esc(e.label) + '</span>' +
        count(e.badge, e.badgeWarn ? 'warn' : '') +
        '</button>';
    }).join('');

    return '' +
      '<header class="hero">' +
        '<div class="hero-top">' +
          '<span class="mascot mascot-md"><img src="assets/mascot.png" alt="绵小城"></span>' +
          '<div>' +
            '<div class="hero-hi">' + hi + '，' + esc(me.name) + '</div>' +
            '<div class="hero-date">' + dateStr + '</div>' +
          '</div>' +
          '<div class="hero-actions">' +
            '<button class="icon-btn" data-action="toast" data-msg="消息中心：3 条未读工作通知">' + icon('bell', 19) + '</button>' +
            '<button class="icon-btn" data-action="go-messages">' + icon('message-circle', 19) + '</button>' +
          '</div>' +
        '</div>' +
        '<div class="hero-strip">' +
          '<span class="hero-strip-ic">' + icon('clock', 18) + '</span>' +
          '<div class="hero-strip-main">' +
            '<div class="hero-strip-title">今天有 3 项待办需要处理</div>' +
            '<div class="hero-strip-sub">2 条请假审批 · 1 条心理预警跟进</div>' +
          '</div>' +
          '<button class="btn btn-soft btn-sm" data-open-sub="approval">去处理</button>' +
        '</div>' +
      '</header>' +
      '<div class="content stagger">' +
        '<div class="focus-card">' +
          '<div class="focus-num">3</div>' +
          '<div class="focus-body">' +
            '<div class="focus-title">今日重点</div>' +
            '<div class="focus-sub">优先处理：陈思远的请假审批与心理跟进</div>' +
          '</div>' +
          '<button class="focus-go" data-open-sub="approval">立即处理</button>' +
        '</div>' +

        '<div class="kpi-row" style="margin-top:12px">' +
          '<button class="kpi" data-action="toast" data-msg="我的学生 · 共 47 人">' +
            '<span class="kpi-ic" style="background:var(--tui-brand-soft);color:var(--tui-brand-strong)">' + icon('users', 20) + '</span>' +
            '<div><div class="kpi-num">47</div><div class="kpi-label">我的学生</div></div>' +
          '</button>' +
          '<button class="kpi" data-open-sub="crisis">' +
            '<span class="kpi-ic" style="background:var(--tui-danger-soft);color:var(--tui-danger)">' + icon('shield-alert', 20) + '</span>' +
            '<div><div class="kpi-num" style="color:var(--tui-danger)">2</div><div class="kpi-label">高危预警</div></div>' +
          '</button>' +
        '</div>' +

        '<div class="card" style="margin-top:12px">' +
          '<div class="card-head">' +
            '<span class="card-head-icon" style="background:var(--tui-brand-soft);color:var(--tui-brand-strong)">' + icon('layout-grid', 14) + '</span>' +
            '常用功能' +
            '<span class="spacer" style="margin-left:auto;display:flex"><button class="link-more" data-open-sub="features">全部功能' + icon('chevron-right', 13) + '</button></span>' +
          '</div>' +
          '<div class="nav-grid">' + grid + '</div>' +
        '</div>' +

        '<div class="group-title">我的节奏<span class="spacer">本周安排与工作沉淀</span></div>' +
        '<div class="pace-grid">' +
          '<button class="pace" data-open-sub="tasks" style="text-align:left;border:1px solid var(--tui-border);cursor:pointer">' +
            '<div class="pace-head">' + icon('calendar', 15) + '本周计划</div>' +
            '<div class="pace-num">5</div><div class="pace-sub">3 项已完成 · 2 项待办</div>' +
          '</button>' +
          '<button class="pace" data-open-sub="care" style="text-align:left;border:1px solid var(--tui-border);cursor:pointer">' +
            '<div class="pace-head">' + icon('chart-column', 15) + '关怀工作量</div>' +
            '<div class="pace-num">12</div><div class="pace-sub">本周谈话 / 家访记录</div>' +
          '</button>' +
        '</div>' +

        '<div class="ai-bar">' +
          '<span class="ai-bar-ic">' + icon('sparkles', 18) + '</span>' +
          '<div style="flex:1;min-width:0">' +
            '<div class="ai-bar-title">绵小城建议：优先关注陈思远</div>' +
            '<div class="ai-bar-sub">近 7 天出勤下降 + 心理测评异常，建议今天完成面谈</div>' +
          '</div>' +
          '<button class="btn btn-soft btn-sm" data-open-sub="care">记录关怀</button>' +
        '</div>' +
      '</div>';
  }

  /* =====================================================================
     消息中心
     ===================================================================== */
  function convRow(c) {
    const isPinned = c.pinned || state.pinned[c.id];
    const avatar = c.type === 'group'
      ? '<span class="avatar sq ' + c.avatarTone + '">' + esc(c.avatarText) + '</span>'
      : (c.isWorkNotice
          ? '<span class="avatar ' + c.avatarTone + '">' + icon('bell', 18) + '</span>'
          : '<span class="avatar ' + c.avatarTone + '">' + esc(c.avatarText) + '</span>');
    const flag = c.type === 'group' ? '<span class="avatar-flag">群</span>' : '';
    return '<li class="conv' + (state.swiped === c.id ? ' swiped' : '') + '" data-conv="' + c.id + '">' +
      '<div class="conv-actions">' +
        '<button class="conv-act pin" data-action="pin" data-id="' + c.id + '">' + (isPinned ? '取消置顶' : '置顶') + '</button>' +
        '<button class="conv-act" data-action="mute" data-id="' + c.id + '">免打扰</button>' +
      '</div>' +
      '<div class="conv-body" data-open-conv="' + c.id + '">' +
        '<div class="avatar-wrap">' + avatar + flag + '</div>' +
        '<div class="row-main">' +
          '<div class="conv-top"><span class="conv-name">' + esc(c.name) + '</span>' +
            '<span class="conv-time">' + esc(c.time) + '</span></div>' +
          '<div class="conv-bot">' +
            (isPinned ? '<span class="pin-chip">置顶</span>' : '') +
            '<span class="conv-preview">' + esc(c.lastMessage) + '</span>' +
            count(c.unread) +
          '</div>' +
        '</div>' +
      '</div>' +
    '</li>';
  }

  function renderMcMsg() {
    const pinned = CONVS.filter((c) => c.pinned || state.pinned[c.id]);
    const rest = CONVS.filter((c) => !(c.pinned || state.pinned[c.id]));
    return '' +
      '<div class="shortcut-row">' +
        '<button class="shortcut" data-action="go-messages-noti">' +
          '<span class="shortcut-ic" style="background:var(--tui-brand-soft);color:var(--tui-brand-strong)">' + icon('bell', 16) + '</span>' +
          '<span class="shortcut-label">工作通知</span>' + count(3) + '</button>' +
        '<button class="shortcut" data-open-sub="approval">' +
          '<span class="shortcut-ic" style="background:var(--tui-warn-soft);color:var(--tui-warn)">' + icon('clipboard-check', 16) + '</span>' +
          '<span class="shortcut-label">待审批</span>' + count(3, 'warn') + '</button>' +
        '<button class="shortcut" data-action="toast" data-msg="我的群聊 · 共 3 个">' +
          '<span class="shortcut-ic" style="background:var(--tui-violet-soft);color:var(--tui-violet)">' + icon('users-round', 16) + '</span>' +
          '<span class="shortcut-label">我的群聊</span>' + count(3, 'soft') + '</button>' +
      '</div>' +
      (pinned.length ? '<div class="group-title">置顶<span class="spacer">' + pinned.length + ' 个会话</span></div>' +
        '<ul class="list">' + pinned.map(convRow).join('') + '</ul>' : '') +
      '<div class="group-title">全部消息<span class="spacer">' + rest.length + ' 个会话</span></div>' +
      '<ul class="list">' + rest.map(convRow).join('') + '</ul>';
  }

  function personRow(p, sub) {
    return '<button class="row" data-open-contact="' + p.id + '">' +
      '<span class="avatar ' + (p.tone || 'tone-slate') + '">' + esc((p.name || '?')[0]) + '</span>' +
      '<span class="row-main">' +
        '<span class="row-label">' + esc(p.name) + (p.risk ? ' <span class="tag tag-danger" style="margin-left:4px">关注</span>' : '') + '</span>' +
        '<span class="row-desc">' + esc(sub || p.username || '') + '</span>' +
      '</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>';
  }

  function orgNodeCollege(col) {
    const open = !!state.orgOpen[col.id];
    const t = TONE[col.tone] || TONE.brand;
    const majors = col.majors.map((mj) => {
      const classes = mj.classes.map((k) => {
        const kop = !!state.orgOpen[k.id];
        const students = k.students.map((s) => personRow(s, s.username)).join('');
        return '<div class="org-node' + (kop ? ' open' : '') + '" data-org-toggle="' + k.id + '" style="padding-left:30px">' +
            icon('chevron-right', 14, 'org-caret') +
            '<span class="org-ic" style="background:var(--tui-surface-sunken);color:var(--tui-text-tertiary)">' + icon('users', 16) + '</span>' +
            '<span class="row-main"><span class="row-label" style="font-size:13px">' + esc(k.name) + '</span></span>' +
            '<span class="row-value">' + k.count + ' 人</span></div>' +
          '<div class="org-children' + (kop ? ' open' : '') + '">' + students + '</div>';
      }).join('');
      return '<div class="org-node" data-org-toggle="' + mj.id + '" style="padding-left:22px">' +
          icon('chevron-right', 14, 'org-caret') +
          '<span class="org-ic" style="background:var(--tui-violet-soft);color:var(--tui-violet)">' + icon('book-open', 16) + '</span>' +
          '<span class="row-main"><span class="row-label" style="font-size:13px">' + esc(mj.name) + '</span></span></div>' +
        '<div class="org-children' + (state.orgOpen[mj.id] ? ' open' : '') + '">' + classes + '</div>';
    }).join('');
    return '<div class="org-node" data-org-toggle="' + col.id + '">' +
        icon('chevron-right', 14, 'org-caret') +
        '<span class="org-ic" style="background:' + t.bg + ';color:' + t.fg + '">' + icon('building', 17) + '</span>' +
        '<span class="row-main"><span class="row-label">' + esc(col.name) + '</span></span></div>' +
      '<div class="org-children' + (open ? ' open' : '') + '">' + majors + '</div>';
  }

  function renderMcContacts() {
    return '' +
      '<div class="search" style="margin-bottom:12px">' + icon('search', 16) +
        '<input placeholder="搜索姓名、学号、工号或部门" readonly data-action="toast" data-msg="通讯录搜索（原型演示）"></div>' +
      '<div class="group-title">快捷入口</div>' +
      '<div class="list">' +
        '<button class="row" data-action="people" data-kind="students">' +
          '<span class="row-icon" style="background:var(--tui-brand-soft);color:var(--tui-brand-strong)">' + icon('users', 18) + '</span>' +
          '<span class="row-main"><span class="row-label">我的学生</span><span class="row-desc">按班级分组，含重点关注标记</span></span>' +
          '<span class="row-value">47 人</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
        '<button class="row" data-action="people" data-kind="colleagues">' +
          '<span class="row-icon" style="background:var(--tui-cyan-soft);color:var(--tui-cyan)">' + icon('users-round', 18) + '</span>' +
          '<span class="row-main"><span class="row-label">全体教师</span><span class="row-desc">同事通讯录，可直接发起会话</span></span>' +
          '<span class="row-value">128 人</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
        '<button class="row" data-action="toast" data-msg="我的班级 · 计科 2301 / 2302 / 软工 2301">' +
          '<span class="row-icon" style="background:var(--tui-violet-soft);color:var(--tui-violet)">' + icon('school', 18) + '</span>' +
          '<span class="row-main"><span class="row-label">我的班级</span><span class="row-desc">我担任辅导员的班级</span></span>' +
          '<span class="row-value">3 个</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
      '</div>' +
      '<div class="group-title">组织架构<span class="spacer">学院 · 专业 · 班级</span></div>' +
      '<div class="list org-tree">' + window.DB.org.map(orgNodeCollege).join('') + '</div>' +
      '<div class="legacy-note">组织架构数据来自管理端「院系班级」配置（College → Major → ClassGroup），教师端按权限可见；点击班级可展开学生名单并直接发起会话。</div>';
  }

  function notiRow(n) {
    const t = TONE[n.tone] || TONE.brand;
    return '<div class="noti-row' + (n.read ? '' : ' unread') + '" data-noti="' + n.id + '">' +
      '<span class="noti-ic" style="background:' + t.bg + ';color:' + t.fg + '">' + icon('bell', 17) + '</span>' +
      '<div class="noti-main">' +
        '<div class="noti-title">' + esc(n.title) + '</div>' +
        '<div class="noti-text">' + esc(n.content) + '</div>' +
        '<div class="noti-meta">' + esc(n.time) + ' · ' + esc(n.type) + '</div>' +
      '</div>' +
    '</div>';
  }

  function renderMcNoti() {
    const unread = window.DB.notifications.filter((n) => !n.read).length;
    return '' +
      '<div class="notice" style="margin-bottom:12px">' + icon('bell', 15) +
        '<span>工作通知汇总审批、预警、公告、反馈等系统消息，共 ' + unread + ' 条未读。</span></div>' +
      '<div class="list">' + window.DB.notifications.map(notiRow).join('') + '</div>' +
      '<div class="legacy-note">通知来源于后端 Notification 模型（type：SYSTEM / APPROVAL / LEAVE / CRISIS / ANNOUNCEMENT / FEEDBACK），点击可直接跳转到对应功能子页面。</div>';
  }

  function renderMessages() {
    const titles = { msg: '消息', contacts: '通讯录', noti: '通知' };
    let body = '';
    if (state.mc === 'msg') body = renderMcMsg();
    else if (state.mc === 'contacts') body = renderMcContacts();
    else body = renderMcNoti();

    return '' +
      '<header class="mc-head">' +
        '<div class="mc-head-row">' +
          '<button class="icon-btn" data-action="mc-drawer-open" aria-label="打开侧边导航">' + icon('ellipsis', 20) + '</button>' +
          '<span class="mc-title">' + titles[state.mc] + '</span>' +
          '<span class="spacer"></span>' +
          '<button class="icon-btn" data-action="toast" data-msg="搜索会话 / 联系人">' + icon('search', 20) + '</button>' +
          '<button class="icon-btn" data-action="plus-menu">' + icon('plus', 20) + '</button>' +
        '</div>' +
      '</header>' +
      '<div class="content">' + body + '</div>';
  }

  function renderMcDrawer() {
    const total = CONVS.reduce((s, c) => s + (c.unread || 0), 0);
    const unreadNoti = window.DB.notifications.filter((n) => !n.read).length;
    const items = [
      ['msg', '消息', 'message-square', total],
      ['contacts', '通讯录', 'users-round', 0],
      ['noti', '通知', 'bell', unreadNoti],
    ].map(([k, l, ic, n]) =>
      '<button class="mc-drawer-item' + (state.mc === k ? ' active' : '') + '" data-mc="' + k + '">' +
        '<span class="mc-drawer-ic">' + icon(ic, 19) + '</span>' +
        '<span class="mc-drawer-label">' + l + '</span>' + count(n) +
      '</button>').join('');
    return '' +
      '<div class="mc-drawer-mask" data-action="mc-drawer-close"></div>' +
      '<aside class="mc-drawer">' +
        '<div class="mc-drawer-head">' +
          '<span class="mc-drawer-avatar">' + esc(window.DB.me.name.slice(0, 1)) + '</span>' +
          '<div class="mc-drawer-user">' +
            '<span class="mc-drawer-name">' + esc(window.DB.me.name) + '</span>' +
            '<span class="mc-drawer-sub">' + esc(window.DB.me.college || '教师') + '</span>' +
          '</div>' +
        '</div>' +
        '<nav class="mc-drawer-nav">' + items + '</nav>' +
        '<div class="mc-drawer-foot">' +
          '<button class="mc-drawer-foot-btn" data-action="mc-drawer-close">' + icon('arrow-left', 17) + ' 收起侧边栏</button>' +
        '</div>' +
      '</aside>';
  }

  /* ---------------- 占位屏 ---------------- */
  function renderPlaceholder(kind) {
    const p = window.DB.placeholder[kind];
    return '<header class="appbar appbar-brand">' +
        '<span class="mascot mascot-sm"><img src="assets/mascot.png" alt="绵小城"></span>' +
        '<div class="appbar-title">' + esc(p.title) + '<small>本次改版未涉及</small></div>' +
      '</header>' +
      '<div class="placeholder">' +
        '<span class="mascot mascot-lg"><img src="assets/mascot.png" alt="绵小城"></span>' +
        '<h3>' + esc(p.title) + '</h3>' +
        '<p>' + nl(p.desc) + '</p>' +
        '<button class="btn btn-ghost btn-sm" data-tab="home">返回首页</button>' +
      '</div>';
  }

  /* =====================================================================
     v3：学生 Tab —— 学生列表 → 学生详情（档案头卡 + 锚点 Tab）→ QQ 风格主页
     ===================================================================== */
  function renderStudents() {
    const list = window.DB.myStudents;
    const risk = list.filter((s) => s.risk);
    const byClass = {};
    list.forEach((s) => { (byClass[s.className] = byClass[s.className] || []).push(s); });
    const row = (s) => '<button class="row" data-open-student="' + s.id + '">' +
        '<span class="avatar ' + (s.tone || 'tone-slate') + '">' + esc(s.name[0]) + '</span>' +
        '<span class="row-main"><span class="row-label">' + esc(s.name) +
          (s.risk ? ' <span class="tag tag-danger" style="margin-left:4px">重点关注</span>' : '') + '</span>' +
          '<span class="row-desc">' + esc(s.className) + ' · ' + esc(s.username) + '</span></span>' +
        icon('chevron-right', 16, 'row-arrow') + '</button>';
    const riskBody = risk.length
      ? '<div class="group-title">重点关注<span class="spacer">' + risk.length + ' 人</span></div><div class="list">' + risk.map(row).join('') + '</div>'
      : '';
    const clsBody = Object.keys(byClass).map((c) =>
      '<div class="group-title">' + esc(c) + '<span class="spacer">' + byClass[c].length + ' 人</span></div>' +
      '<div class="list">' + byClass[c].map(row).join('') + '</div>').join('');
    return '<header class="mc-head"><div class="mc-head-row">' +
        '<span class="mc-title">学生</span><span class="spacer"></span>' +
        '<button class="icon-btn" data-action="toast" data-msg="搜索学生（原型演示）">' + icon('search', 20) + '</button>' +
      '</div></header>' +
      '<div class="content">' +
        '<div class="search" style="margin-bottom:4px">' + icon('search', 16) +
          '<input placeholder="搜索姓名 / 学号" readonly data-action="toast" data-msg="学生搜索（原型演示）"></div>' +
        riskBody + clsBody +
        '<div class="legacy-note">点击学生进入「学生详情」（档案头卡 + 概览 / 课业 / 考勤 / 档案锚点），详情头卡可一键跳转 TA 的 QQ 风格个人主页。</div>' +
      '</div>';
  }

  function buildStuDetail(p) {
    const all = window.DB.studentDetail || {};
    const rich = all[p.id] || {};
    const g = all._generic || {};
    const d = {
      kpis: rich.kpis || g.kpis || [],
      risk: rich.risk || (p.risk ? { level: '重点关注', title: '在校表现波动', source: '辅导员标记',
        desc: '该生被标记为重点关注，请结合近期出勤、测评与谈心记录综合评估。', sla: '建议本周完成一次谈心', pct: 50 } : null),
      grades: rich.grades || g.grades || [],
      attendance: rich.attendance || g.attendance || [],
      dynamics: rich.dynamics || g.dynamics || [],
      records: rich.records || g.records || [],
    };
    return d;
  }

  function renderStudentDetail() {
    const p = findPerson(state.activeStudent) || { name: '学生', tone: 'tone-slate', className: '—', username: '—' };
    const d = buildStuDetail(p);
    const tab = state.stuTab || 'overview';
    const tabs = [['overview', '概览'], ['study', '课业'], ['attend', '考勤'], ['record', '档案']];
    const risk = d.risk
      ? '<div class="stu-card risk-card">' +
          '<div class="rc-head">' + icon('shield-alert', 17) + '<span class="rc-title">' + esc(d.risk.level) + ' · ' + esc(d.risk.title) + '</span>' + tag(d.risk.level, 'danger') + '</div>' +
          '<div class="rc-desc">' + esc(d.risk.desc) + '</div>' +
          '<div style="font-size:11px;color:var(--tui-text-quiet);margin-top:6px">' + esc(d.risk.source) + '</div>' +
          '<div class="sla-line"><div class="lb"><span>' + esc(d.risk.sla) + '</span><b>处置进度 ' + d.risk.pct + '%</b></div>' +
            '<div class="bar"><i style="width:' + d.risk.pct + '%"></i></div></div>' +
          '<button class="btn btn-ghost btn-sm" style="margin-top:11px;color:var(--tui-danger);border-color:#f4c7c3" data-open-sub="crisis">' + icon('arrow-right', 14) + '去跟进处置</button>' +
        '</div>'
      : '';

    let body = '';
    if (tab === 'overview') {
      body = risk +
        '<div class="stu-card"><div class="stu-card-t">' + icon('book-open', 15) + '近期成绩<span class="spacer">查看全部 ›</span></div>' +
          d.grades.map((r) => '<div class="mini-row"><span class="nm">' + esc(r.k) + '</span><span class="sc ' + (r.tone || '') + '">' + esc(r.v) + '</span></div>').join('') +
        '</div>' +
        '<div class="stu-card"><div class="stu-card-t">' + icon('activity', 15) + '最近动态<span class="spacer">成长轨迹 ›</span></div>' +
          d.dynamics.map((r) => '<div class="mini-row"><span class="dot" style="background:' +
            ({ danger: 'var(--tui-danger)', warn: 'var(--tui-warn)', success: 'var(--tui-success)', brand: 'var(--tui-brand)', violet: 'var(--tui-violet)', cyan: 'var(--tui-cyan)' }[r.dot] || 'var(--tui-brand)') +
            '"></span><span class="nm">' + esc(r.k) + '</span><time>' + esc(r.t) + '</time></div>').join('') +
        '</div>';
    } else if (tab === 'study') {
      body = '<div class="stu-card"><div class="stu-card-t">' + icon('graduation-cap', 15) + '成绩单<span class="spacer">本学期</span></div>' +
          d.grades.map((r) => '<div class="mini-row"><span class="nm">' + esc(r.k) + '</span><span class="sc ' + (r.tone || '') + '">' + esc(r.v) + '</span></div>').join('') +
        '</div>' +
        '<div class="stu-card"><div class="stu-card-t">' + icon('chart-line', 15) + '学业趋势</div>' +
          '<div class="mini-row"><span class="nm">学分绩点</span><span class="sc">' + esc((d.kpis[1] || {}).v || '—') + '</span></div>' +
          '<div class="mini-row"><span class="nm">挂科课程</span><span class="sc ' + (p.risk ? 'bad' : '') + '">' + (p.risk ? '1 门' : '0 门') + '</span></div>' +
          '<div class="mini-row"><span class="nm">出勤率</span><span class="sc">' + esc((d.kpis[0] || {}).v || '—') + '</span></div>' +
        '</div>';
    } else if (tab === 'attend') {
      body = '<div class="stu-card"><div class="stu-card-t">' + icon('calendar-check', 15) + '考勤记录<span class="spacer">近 30 天</span></div>' +
          d.attendance.map((r) => '<div class="mini-row"><span class="nm">' + esc(r.k) + '</span><span class="sc ' + (r.tone === 'bad' ? 'bad' : r.tone === 'good' ? 'good' : r.tone === 'warn' ? 'bad' : '') + '" style="' + (r.tone === 'warn' ? 'color:var(--tui-warn)' : '') + '">' + esc(r.v) + '</span></div>').join('') +
        '</div>';
    } else {
      body = '<div class="tl" style="margin-top:12px">' + d.records.map((r) => {
        const t = TONE[r.tone] || TONE.brand;
        return '<div class="tl-item"><span class="tl-node" style="background:' + t.bg + ';color:' + t.fg + '">' + icon(r.icon, 13) + '</span>' +
          '<div class="tl-card"><div class="tl-head"><span class="tl-title" style="flex:1">' + esc(r.k) + '</span><span class="tl-date">' + esc(r.t) + '</span></div></div></div>';
      }).join('') + '</div>';
    }

    return '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-title">学生详情<small>' + esc(p.className) + '</small></div>' +
        '<div class="appbar-actions"><button class="icon-btn" data-action="toast" data-msg="更多操作（原型演示）">' + icon('ellipsis', 19) + '</button></div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="stu-hero">' +
          '<div class="stu-hero-r1">' +
            '<span class="avatar ' + (p.tone || 'tone-slate') + '">' + esc((p.name || '?')[0]) + '</span>' +
            '<div><div class="stu-hero-name">' + esc(p.name) + '</div>' +
              '<div class="stu-hero-meta">' + esc(p.className) + ' · 学号 ' + esc(p.username) + '</div></div>' +
            '<button class="stu-hero-home" data-open-student-home="' + p.id + '">' + icon('sparkles', 13) + 'TA 的主页</button>' +
          '</div>' +
          '<div class="stu-hero-tags">' +
            (p.risk ? '<span>重点关注</span>' : '<span>在校正常</span>') +
            '<span>' + esc(p.className) + '</span>' +
            '<span>我的学生</span>' +
          '</div>' +
        '</div>' +
        '<div class="stu-kpi">' + d.kpis.map((k) =>
          '<div class="k"><b' + (k.tone ? ' style="color:var(--tui-' + (k.tone === 'violet' ? 'violet' : k.tone) + ')"' : '') + '>' + esc(k.v) + '</b><i>' + esc(k.k) + '</i></div>').join('') +
        '</div>' +
        '<div class="stu-tabs">' + tabs.map(([k, l]) =>
          '<button class="' + (tab === k ? 'on' : '') + '" data-stu-tab="' + k + '">' + l + '</button>').join('') + '</div>' +
        body +
        '<div class="legacy-note">学生详情数据聚合自后端 Attendance / Grade / Crisis / TeacherPortfolio 模型；「TA 的主页」为学生端个人空间的教师视角只读版。</div>' +
      '</div>';
  }

  function renderStudentHome() {
    const p = findPerson(state.activeStudent) || { name: '学生', tone: 'tone-slate', username: '—', className: '—' };
    const pg = (window.DB.studentPages || {})[p.id] || { motto: '这个人很懒，什么都没有留下。', likes: 0, visitors: 0, badges: [], photos: 0, posts: [] };
    const IMG_TONES = ['#85b7eb', '#5dcaa5', '#a78bfa', '#f0997b', '#ed93b1'];
    const likedKey = 'home:' + p.id;
    const isLiked = !!state.stuLike[likedKey];
    const badgeEls = pg.badges.map((b) => {
      const t = TONE[b.tone] || TONE.brand;
      return '<div class="qq-badge"><span class="row-icon" style="width:32px;height:32px;border-radius:50%;margin:0 auto 4px;background:' + t.bg + ';color:' + t.fg + '">' + icon(b.icon, 16) + '</span><span>' + esc(b.label) + '</span></div>';
    }).join('');
    const photoEls = Array.from({ length: Math.min(pg.photos, 5) }).map((_, i) =>
      '<div class="qq-photo" style="background:' + IMG_TONES[i % IMG_TONES.length] + '">' + icon('image', 18) + '</div>').join('') +
      '<button class="qq-photo more" data-action="toast" data-msg="相册（原型演示）">' + icon('image', 16) + pg.photos + ' 张</button>';
    const postEls = pg.posts.map((po) => {
      const liked = !!state.stuLike[po.id];
      const imgs = po.imgs
        ? '<div class="qq-post-imgs ' + (po.imgs > 1 ? 'g2' : 'g1') + '">' +
          Array.from({ length: po.imgs }).map((_, i) =>
            '<div class="qq-pimg" style="background:' + IMG_TONES[(i + pg.photos) % IMG_TONES.length] + '">' + icon('image', 16) + '动态配图</div>').join('') + '</div>'
        : '';
      return '<div class="qq-post">' +
        '<div class="qq-post-head"><span class="avatar ' + (p.tone || 'tone-slate') + '">' + esc((p.name || '?')[0]) + '</span>' +
          '<div><div class="qq-post-name">' + esc(p.name) + '</div><div class="qq-post-time">' + esc(po.time) + '</div></div></div>' +
        '<div class="qq-post-text">' + esc(po.text) + '</div>' + imgs +
        '<div class="qq-post-ops">' +
          '<button class="qq-op' + (liked ? ' liked' : '') + '" data-qq-like="' + po.id + '">' + icon('thumbs-up', 15) + (liked ? '已赞 ' : '点赞 ') + (po.likeN + (liked ? 1 : 0)) + '</button>' +
          '<button class="qq-op" data-action="toast" data-msg="评论（原型演示）">' + icon('message-square', 15) + '评论 ' + po.cmtN + '</button>' +
          '<button class="qq-op" data-action="toast" data-msg="已收藏该动态（原型演示）">' + icon('star', 15) + '收藏</button>' +
        '</div></div>';
    }).join('');

    return '<header class="appbar" style="position:absolute;top:0;left:0;right:0;z-index:6;background:transparent;box-shadow:none;pointer-events:none">' +
        '<button class="appbar-back" data-back style="pointer-events:auto">' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-actions" style="pointer-events:auto"><button class="icon-btn" data-action="toast" data-msg="更多（原型演示）" style="background:rgba(255,255,255,.25);color:#fff">' + icon('ellipsis', 19) + '</button></div>' +
      '</header>' +
      '<div class="qq-wrap">' +
        '<div class="qq-cover"><div class="qq-cover-bar">' +
          '<button data-action="toast" data-msg="打招呼（原型演示）">打声招呼</button>' +
          '<button data-action="toast" data-msg="更换封面（原型演示）">更换封面</button>' +
        '</div></div>' +
        '<div class="qq-head">' +
          '<span class="qq-avatar" style="background:' + (TONE[p.tone] || TONE.brand).fg + '">' + esc((p.name || '?')[0]) + '</span>' +
          '<div class="qq-name-row"><span class="qq-name">' + esc(p.name) + '</span><span class="qq-lv">LV.' + (3 + (p.id.length % 4)) + '</span></div>' +
          '<div class="qq-qid">学号：<b>' + esc(p.username) + '</b> · ' + esc(p.className) + '</div>' +
          '<div class="qq-sig">' + esc(pg.motto) + '</div>' +
        '</div>' +
        '<div style="padding:0 14px">' +
          '<div class="qq-stats">' +
            '<div class="s"><b>' + pg.likes + '</b><i>获赞</i></div>' +
            '<div class="s"><b>' + pg.visitors + '</b><i>被访客</i></div>' +
            '<div class="s"><b>' + pg.posts.length + '</b><i>动态</i></div>' +
            '<div class="s"><b>' + pg.photos + '</b><i>照片</i></div>' +
          '</div>' +
          '<div class="qq-sec">展示墙<span class="spacer">QQ 风格徽章 · 与成长档案互通 ›</span></div>' +
          '<div class="qq-badges">' + badgeEls + '</div>' +
          '<div class="qq-sec">精选照片<span class="spacer">共 ' + pg.photos + ' 张 ›</span></div>' +
          '<div class="qq-photos">' + photoEls + '</div>' +
          '<div class="qq-sec">TA 的动态</div>' + postEls +
        '</div>' +
      '</div>' +
      '<div class="act-dock">' +
        '<button class="btn btn-ghost" style="flex:1" data-open-student="' + p.id + '">' + icon('user', 16) + '学生详情</button>' +
        '<button class="btn btn-primary" style="flex:1" data-action="chat-with" data-id="' + p.id + '">' + icon('message-circle', 16) + '发消息</button>' +
      '</div>';
  }

  /* =====================================================================
     二级页：聊天 / 群设置 / 成员 / 人员 / 全部功能
     ===================================================================== */
  function findConv(id) { return CONVS.filter((c) => c.id === id)[0]; }
  function findPerson(id) {
    const pools = [].concat(window.DB.myStudents, window.DB.colleagues);
    window.DB.org.forEach((c) => c.majors.forEach((m) => m.classes.forEach((k) => { pools.push.apply(pools, k.students); })));
    return pools.filter((p) => p.id === id)[0];
  }

  function renderChat() {
    const conv = findConv(state.activeConv) || { name: '会话', type: 'single' };
    const msgs = window.DB.messages[state.activeConv] || window.DB.messages['default'];
    const isGroup = conv.type === 'group';
    const rows = msgs.map((m) => {
      if (m.kind === 'file') {
        return '<div class="msg-row ' + (m.mine ? 'mine' : 'theirs') + '">' +
          '<span class="avatar ' + (m.mine ? 'tone-blue' : (conv.avatarTone || 'tone-slate')) + '">' + esc(m.mine ? window.DB.me.name[0] : (m.senderName || conv.name)[0]) + '</span>' +
          '<div class="msg-col">' +
            (isGroup && !m.mine ? '<span class="sender-name">' + esc(m.senderName) + '</span>' : '') +
            '<div class="bubble-file"><span class="fi">' + icon('file-text', 18) + '</span>' +
              '<div><div class="fname">' + esc(m.fileName) + '</div><div class="fmeta">' + esc(m.fileMeta || '点击下载') + '</div></div></div>' +
            '<span class="bubble-time">' + esc(m.time) + '</span>' +
          '</div></div>';
      }
      return '<div class="msg-row ' + (m.mine ? 'mine' : 'theirs') + '">' +
        '<span class="avatar ' + (m.mine ? 'tone-blue' : (conv.avatarTone || 'tone-slate')) + '">' + esc(m.mine ? window.DB.me.name[0] : (m.senderName || conv.name)[0]) + '</span>' +
        '<div class="msg-col">' +
          (isGroup && !m.mine ? '<span class="sender-name">' + esc(m.senderName) + '</span>' : '') +
          '<div class="bubble ' + (m.mine ? 'mine' : 'theirs') + '">' + nl(m.text) + '</div>' +
          '<span class="bubble-time">' + esc(m.time) + '</span>' +
        '</div></div>';
    }).join('');

    const notice = isGroup
      ? '<div class="notice chat-notice">' + icon('megaphone', 15) +
          '<span>群公告：周一班会调整至 16:00，地点 3 号教学楼 201。</span></div>'
      : '';

    const head = '' +
      '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        (isGroup ? '<span class="avatar sq sm ' + conv.avatarTone + '" style="margin-right:2px">' + esc(conv.avatarText) + '</span>' : '') +
        '<div class="appbar-title">' + esc(conv.name) +
          (isGroup ? '<small>' + (conv.memberCount || 0) + ' 名成员</small>' : (conv.roleTag ? '<small>' + esc(conv.roleTag) + '</small>' : '')) +
        '</div>' +
        '<div class="appbar-actions">' +
          (isGroup
            ? '<button class="icon-btn" data-open-group-settings>' + icon('settings', 19) + '</button>'
            : '<button class="icon-btn" data-action="toast" data-msg="发起语音通话（原型演示）">' + icon('phone', 19) + '</button>' +
              '<button class="icon-btn" data-action="toast" data-msg="发起视频通话（原型演示）">' + icon('video', 19) + '</button>') +
        '</div>' +
      '</header>';

    const attach = state.attachOpen
      ? '<div class="attach-panel">' +
          [['image', '图片'], ['camera', '拍摄'], ['file-text', '文件'], ['mic', '语音'], ['folder', '群文件'], ['award', '成长记录'], ['clipboard-check', '审批单'], ['map-pin', '位置']]
            .map(([i, l]) => '<button class="attach-item" data-action="toast" data-msg="' + l + '（原型演示）"><span class="ai">' + icon(i, 22) + '</span><span>' + l + '</span></button>').join('') +
        '</div>'
      : '';

    return '<div class="chat-wrap">' + head +
      '<div class="chat-scroll" id="chatScroll">' +
        '<div class="day-sep"><span>今天</span></div>' + notice + rows +
      '</div>' +
      '<div class="chat-input">' +
        '<button class="icon-btn" data-attach-toggle style="color:' + (state.attachOpen ? 'var(--tui-brand)' : 'var(--tui-text-secondary)') + '">' + icon(state.attachOpen ? 'x' : 'plus', 21) + '</button>' +
        '<textarea class="field" id="chatField" rows="1" placeholder="输入消息…">' + esc(state.chatInput) + '</textarea>' +
        '<button class="send-btn' + (state.chatInput.trim() ? ' on' : '') + '" data-send' + (state.chatInput.trim() ? '' : ' disabled') + '>发送</button>' +
      '</div>' + attach + '</div>';
  }

  function renderGroupSettings() {
    const conv = findConv(state.activeConv) || { name: '群聊', memberCount: 0, avatarText: '群', avatarTone: 'tone-violet' };
    const members = window.DB.myStudents.slice(0, 7);
    const mini = members.map((m) => '<button class="member-mini" data-open-contact="' + m.id + '">' +
        '<span class="avatar sm ' + m.tone + '">' + esc(m.name[0]) + '</span><span>' + esc(m.name) + '</span></button>').join('') +
      '<div class="member-mini"><button class="add" data-action="toast" data-msg="邀请成员（原型演示）">' + icon('plus', 18) + '</button><span>邀请</span></div>';

    return '' +
      '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-title">群设置</div>' +
        '<div class="appbar-actions"><button class="icon-btn" data-action="toast" data-msg="群管理（原型演示）">' + icon('ellipsis', 19) + '</button></div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="hero-card">' +
          '<span class="avatar sq lg ' + conv.avatarTone + '">' + esc(conv.avatarText) + '</span>' +
          '<div><div class="hero-card-name">' + esc(conv.name) + '</div>' +
            '<div class="hero-card-meta">' + (conv.memberCount || 0) + ' 名群成员 · 我是群主</div></div>' +
        '</div>' +
        '<div class="card" style="margin-top:12px"><div class="card-head">群成员<span class="spacer">' + (conv.memberCount || 0) + ' 人</span></div>' +
          '<div class="member-strip">' + mini + '</div></div>' +
        '<div class="list" style="margin-top:12px">' +
          '<button class="row" data-action="toast" data-msg="群公告：周一班会调整至 16:00">' + tile('brand', 'megaphone') +
            '<span class="row-main"><span class="row-label">群公告</span><span class="row-desc">周一班会调整至 16:00，地点 3 号教学楼 201</span></span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="群文件 · 6 个文件">' + tile('cyan', 'folder') +
            '<span class="row-main"><span class="row-label">群文件</span></span><span class="row-value">6 个</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="查看全部群成员">' + tile('violet', 'users') +
            '<span class="row-main"><span class="row-label">群成员</span></span><span class="row-value">' + (conv.memberCount || 0) + ' 人</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="邀请成员（原型演示）">' + tile('success', 'user-plus') +
            '<span class="row-main"><span class="row-label">添加成员</span></span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="消息免打扰已开启">' + tile('quiet', 'volume-x') +
            '<span class="row-main"><span class="row-label">消息免打扰</span></span><span class="row-value">已关闭</span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
        '</div>' +
        '<button class="btn btn-danger btn-block" style="margin-top:14px" data-action="toast" data-msg="已退出群聊（原型演示）">' + icon('log-out', 16) + '退出群聊</button>' +
      '</div>';
  }

  function renderContact() {
    const p = findPerson(state.activeContact) || { name: '未知', tone: 'tone-slate' };
    const isStudent = !!p.className;
    const rows = isStudent
      ? [['学号', p.username], ['班级', p.className], ['学院', '信息工程学院'], ['联系电话', '138****' + (1000 + (p.id.length * 137) % 9000)]]
      : [['工号', p.username], ['职称', p.title], ['部门', p.department], ['联系电话', '139****' + (1000 + (p.id.length * 173) % 9000)]];
    return '' +
      '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-title">' + (isStudent ? '学生资料' : '教师资料') + '</div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="hero-card">' +
          '<span class="avatar lg ' + (p.tone || 'tone-slate') + '">' + esc((p.name || '?')[0]) + '</span>' +
          '<div><div class="hero-card-name">' + esc(p.name) + (p.risk ? ' ' + tag('重点关注', 'danger') : '') + '</div>' +
            '<div class="hero-card-meta">' + esc(isStudent ? p.className : (p.title || '')) + '</div></div>' +
        '</div>' +
        '<div class="list" style="margin-top:12px">' +
          rows.map(([k, v]) => '<div class="row no-line" style="cursor:default;min-height:48px">' +
            '<span class="row-main"><span class="row-label" style="font-size:13px;font-weight:400;color:var(--tui-text-tertiary)">' + esc(k) + '</span></span>' +
            '<span class="row-value" style="color:var(--tui-text)">' + esc(v) + '</span></div>').join('') +
        '</div>' +
        (p.risk ? '<div class="notice notice-danger" style="margin-top:12px">' + icon('triangle-alert', 15) +
          '<span>该生处于「重点关注」状态：近 7 天出勤下降，心理测评异常，建议尽快跟进。</span></div>' : '') +
        (isStudent
          ? '<div class="item-ops" style="border-top:none;margin-top:14px">' +
              '<button class="btn btn-ghost" data-open-student-home="' + p.id + '">' + icon('sparkles', 16) + 'TA 的主页</button>' +
              '<button class="btn btn-ghost" data-open-student="' + p.id + '">' + icon('user', 16) + '学生详情</button>' +
              '<button class="btn btn-primary" data-action="chat-with" data-id="' + p.id + '">' + icon('message-circle', 16) + '发消息</button>' +
            '</div>'
          : '<div class="item-ops" style="border-top:none;margin-top:14px">' +
              '<button class="btn btn-ghost" data-open-sub="portfolio">' + icon('award', 16) + '成长档案</button>' +
              '<button class="btn btn-primary" data-action="chat-with" data-id="' + p.id + '">' + icon('message-circle', 16) + '发消息</button>' +
            '</div>') +
      '</div>';
  }

  function renderPeople() {
    const kind = state.peopleKind;
    const list = kind === 'students' ? window.DB.myStudents : window.DB.colleagues;
    const title = kind === 'students' ? '我的学生' : '全体教师';
    return '' +
      '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-title">' + title + '<small>共 ' + list.length + ' 人</small></div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="search" style="margin-bottom:12px">' + icon('search', 16) +
          '<input placeholder="搜索姓名 / 学号 / 工号" readonly data-action="toast" data-msg="人员搜索（原型演示）"></div>' +
        '<div class="list">' + list.map((p) => personRow(p, kind === 'students' ? p.className + ' · ' + p.username : (p.title || '') + ' · ' + (p.department || ''))).join('') + '</div>' +
      '</div>';
  }

  function renderFeatures() {
    const groups = window.DB.featureGroups || [];
    const body = groups.map((g) => {
      const rows = g.items.map((it) => {
        const has = !!window.DB.modules[it.id];
        const attr = has
          ? ' data-open-sub="' + it.id + '"'
          : ' data-action="toast" data-msg="' + esc(it.label) + '（原型演示）"';
        return '<button class="row"' + attr + '>' + tile(it.tone, it.icon) +
          '<span class="row-main"><span class="row-label">' + esc(it.label) + '</span>' +
          '<span class="row-desc">' + esc(it.desc) + '</span></span>' +
          count(it.badge, it.badgeWarn ? 'warn' : '') + icon('chevron-right', 16, 'row-arrow') + '</button>';
      }).join('');
      return '<div class="group-title">' + esc(g.title) +
        '<span class="spacer">' + g.items.length + ' 项</span></div>' +
        '<div class="list">' + rows + '</div>';
    }).join('');

    return '' +
      '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-title">全部功能<small>教师工作台功能总览</small></div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="search" style="margin-bottom:12px">' + icon('search', 16) +
          '<input placeholder="搜索功能，如「审批」「家访」" readonly data-action="toast" data-msg="功能搜索（原型演示）"></div>' +
        '<div class="notice" style="margin-bottom:12px">' + icon('bell', 15) +
          '<span>会话、通讯录与通知在底部「消息」页签内，此处为其余功能入口。</span></div>' +
        body +
        '<div class="legacy-note">底部页签已承载 首页 / 学生 / 绵小城 / 消息 / 个人中心，本页只列其余模块；审批与预警的行尾角标来自实时统计。</div>' +
      '</div>';
  }

  /* =====================================================================
     模块通用构件
     ===================================================================== */
  function modHead(m, extra) {
    return '<header class="appbar">' +
      '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
      '<div class="appbar-title">' + esc(m.meta.title) + '<small>' + esc(m.meta.sub) + '</small></div>' +
      '<div class="appbar-actions">' +
        '<button class="icon-btn" data-action="toast" data-msg="筛选 / 排序（原型演示）">' + icon('funnel', 19) + '</button>' +
        (extra || '<button class="icon-btn" data-action="toast" data-msg="更多操作（原型演示）">' + icon('ellipsis', 19) + '</button>') +
      '</div>' +
    '</header>';
  }
  function modWrap(key, inner) {
    const a = accentOf(key);
    return '<div class="content mod" style="--mod-color:' + a.c + ';--mod-soft:' + a.s + '">' + inner + '</div>';
  }
  function segBar(key, items) {
    const i = state.seg[key] || 0;
    return '<div class="seg">' + items.map((s, idx) =>
      '<button class="seg-item' + (idx === i ? ' active' : '') + '" data-mod-seg="' + key + '" data-idx="' + idx + '">' + esc(s) + '</button>').join('') + '</div>';
  }
  function statRow(list) {
    return '<div class="stat-row">' + list.map((s) => {
      const t = TONE[s.tone] || TONE.brand;
      return '<div class="stat2">' +
        '<div class="stat2-top"><span class="stat2-ic" style="background:' + t.bg + ';color:' + t.fg + '">' + icon(s.icon || 'circle-dot', 14) + '</span></div>' +
        '<div class="stat2-num"' + (s.tone === 'quiet' ? '' : ' style="color:' + t.fg + '"') + '>' + s.num + '</div>' +
        '<div class="stat2-label">' + esc(s.label) + '</div></div>';
    }).join('') + '</div>';
  }
  function modFab(key, m) {
    if (!m.fab) return '';
    return '<button class="fab" data-sheet="' + key + '">' + icon(m.fab.icon, 18) + esc(m.fab.label) + '</button>';
  }
  function bar(pct, cls) {
    return '<div class="bar' + (cls ? ' ' + cls : '') + '"><i style="width:' + Math.max(0, Math.min(100, pct)) + '%"></i></div>';
  }
  function confBar(pct) { return bar(pct); }
  function pct(a, b) { return b ? Math.round((a / b) * 100) : 0; }

  /* =====================================================================
     ① 审批 —— 待办优先 + 票据卡（审批流 / 附件 / SLA）+ 底部审批条
     ===================================================================== */
  function renderApproval(m) {
    const t = m.todo;
    const hero = '<div class="mod-hero">' +
      '<div style="display:flex;align-items:center;gap:10px">' +
        '<span style="width:44px;height:44px;border-radius:14px;background:var(--mod-soft);color:var(--mod-color);display:flex;align-items:center;justify-content:center;flex-shrink:0">' + icon('clipboard-check', 22) + '</span>' +
        '<div style="flex:1;min-width:0">' +
          '<div class="mod-hero-title">待我审批 · ' + t.count + ' 条</div>' +
          '<div class="mod-hero-sub">最紧急：' + esc(t.urgentName) + ' · ' + esc(t.urgentType) + '（' + esc(t.sla) + '）</div>' +
        '</div>' +
        '<button class="btn btn-primary btn-sm" data-sheet="approval">立即处理</button>' +
      '</div>' +
      '<div class="sla" style="margin-top:12px">' + icon('timer', 15) + '<span>' + esc(t.note) + '</span></div>' +
    '</div>';

    const items = m.items.map((it) => {
      const a = accentOf('approval');
      const tags = it.urgent ? tag('加急', 'danger') + tag(it.tag, it.tagTone) : tag(it.tag, it.tagTone);
      const files = it.files.length ? it.files.map((f) =>
        '<div class="file-row"><span class="fi" style="background:var(--tui-surface-sunken);color:var(--tui-text-secondary)">' + icon(f.icon, 15) + '</span>' +
        '<span style="flex:1;min-width:0"><span class="fname">' + esc(f.name) + '</span><br><span class="fsize">' + esc(f.size) + '</span></span>' +
        icon('download', 15, 'row-arrow') + '</div>').join('') : '';
      const flow = '<div class="flow">' + it.flow.map((s) =>
        '<div class="flow-step ' + s.state + '"><span class="flow-dot"></span>' +
        '<div class="flow-k">' + esc(s.k) + '</div><div class="flow-t">' + esc(s.t) + '</div></div>').join('') + '</div>';
      return '<div class="ticket' + (it.urgent ? ' is-urgent' : '') + '" style="--mod-color:' + a.c + '" data-sheet="approval" data-ctx="' + it.id + '">' +
        '<div class="ticket-head">' +
          '<span class="avatar ' + it.stuTone + '">' + esc(it.student[0]) + '</span>' +
          '<div style="min-width:0"><div class="ticket-name">' + esc(it.student) + ' · ' + esc(it.type) + '</div>' +
            '<div class="row-desc">' + esc(it.cls) + ' · 提交于 ' + esc(it.submitted) + '</div></div>' +
          '<div class="ticket-tags">' + tags + '</div>' +
        '</div>' +
        '<div class="kv">' +
          '<span class="kv-k">请假时间</span><span class="kv-v">' + esc(it.range) + '</span>' +
          '<span class="kv-k">时长</span><span class="kv-v">' + esc(it.days) + '</span>' +
          '<span class="kv-k">事由</span><span class="kv-v">' + esc(it.reason) + '</span>' +
        '</div>' +
        files + flow +
      '</div>';
    }).join('');

    const dock = '<div class="act-dock">' +
      '<span style="width:34px;height:34px;border-radius:11px;background:var(--mod-soft);color:var(--mod-color);display:flex;align-items:center;justify-content:center;flex-shrink:0">' + icon('clipboard-check', 17) + '</span>' +
      '<div class="dock-main"><div class="dock-title">' + t.count + ' 条待审批待处理</div><div class="dock-sub">点击卡片查看详情，或一键批量处理</div></div>' +
      '<button class="btn btn-primary btn-sm" data-sheet="approval">去审批</button>' +
    '</div>';

    return modHead(m) + modWrap('approval',
      hero + statRow(m.stats.map((s, i) => Object.assign({ icon: ['clipboard-list', 'check-check', 'circle-x'][i] }, s))) +
      '<div class="sect-title">待办列表<span class="spacer">点击查看审批详情</span></div>' +
      '<div class="stack">' + items + '</div>' +
      '<div class="legacy-note">审批数据来自后端 Approval / Leave 模型；审批流节点与真实工作流引擎（WorkflowInstance）一致，同意 / 驳回会写回审批记录并推送工作通知。</div>'
    ) + dock;
  }

  /* =====================================================================
     ② 预警 —— 风险分布环 + SLA + 等级色带卡 + 处置步骤条
     ===================================================================== */
  function renderCrisis(m) {
    const r = m.risk;
    const total = r.high + r.mid + r.low + r.cleared || 1;
    const seg1 = Math.round((r.high / total) * 100);
    const seg2 = seg1 + Math.round((r.mid / total) * 100);
    const seg3 = seg2 + Math.round((r.low / total) * 100);
    const donut = '<div class="donut" style="background:conic-gradient(' +
      'var(--tui-danger) 0 ' + seg1 + '%,' +
      'var(--tui-warn) ' + seg1 + '% ' + seg2 + '%,' +
      'var(--tui-cyan) ' + seg2 + '% ' + seg3 + '%,' +
      'var(--tui-surface-sunken) ' + seg3 + '% 100%)">' +
      '<div class="donut-mid"><div class="ring-num">' + (r.high + r.mid + r.low) + '</div><div class="ring-cap">在办预警</div></div></div>';
    const legend = '<div class="legend">' +
      [['高危', r.high, 'var(--tui-danger)'], ['中危', r.mid, 'var(--tui-warn)'], ['低危', r.low, 'var(--tui-cyan)'], ['已解除', r.cleared, 'var(--tui-text-quiet)']]
        .map(([k, v, c]) => '<div class="legend-row"><span class="legend-dot" style="background:' + c + '"></span>' +
          '<span class="legend-k">' + k + '</span><span class="legend-v" style="color:' + c + '">' + v + '</span></div>').join('') +
    '</div>';

    const hero = '<div class="mod-hero">' +
      '<div style="display:flex;align-items:center;gap:16px">' + donut + legend + '</div>' +
    '</div>' +
    '<div class="sla danger" style="margin-bottom:12px">' + icon('triangle-alert', 15) +
      '<span><b>' + esc(m.sla.title) + '</b> · 剩余 ' + m.sla.hours + ' 小时处置时限　' + esc(m.sla.note) + '</span></div>';

    const items = m.items.map((it) => {
      const a = TONE[it.levelTone] || TONE.danger;
      const sigs = it.signals.map((s) =>
        '<span class="sig ' + s.dir + '">' + esc(s.k) + ' <b>' + esc(s.v) + '</b></span>').join('');
      const steps = '<div class="steps">' + it.steps.map((s) =>
        '<div class="step ' + s.state + '"><span class="step-dot">' + (s.state === 'done' ? icon('check', 11) : '') + '</span>' + esc(s.k) + '</div>').join('') + '</div>';
      return '<div class="warn-card" style="--mod-color:' + a.fg + '" data-sheet="crisis" data-ctx="' + it.id + '">' +
        '<div class="warn-head">' +
          '<span class="warn-avatar ' + it.stuTone + '">' + esc(it.student[0]) + '</span>' +
          '<div style="flex:1;min-width:0"><div class="warn-title">' + esc(it.student) + ' · ' + esc(it.title) + '</div>' +
            '<div class="warn-src">' + esc(it.cls) + ' · ' + esc(it.source) + '</div></div>' +
          tag(it.level, it.levelTone) +
        '</div>' +
        '<div class="sig-row">' + sigs + '</div>' +
        steps +
        '<div class="item-meta">' + icon('clock', 13) + esc(it.triggered) + '</div>' +
      '</div>';
    }).join('');

    return modHead(m) + modWrap('crisis',
      hero +
      statRow(m.stats.map((s, i) => Object.assign({ icon: ['shield-alert', 'shield-check', 'circle-check'][i] }, s))) +
      segBar('crisis', m.segments) +
      '<div class="stack" style="margin-top:12px">' + items + '</div>' +
      '<div class="legacy-note">预警来源于后端 Crisis / 主动预警引擎（proactive_engine）：扣分规则命中后生成事件，处置回写跟进记录，闭环后自动解除。</div>'
    );
  }

  /* =====================================================================
     ③ 公告 —— 触达率 + 公告卡（置顶 / 紧急角标）
     ===================================================================== */
  function renderAnnouncement(m) {
    const rc = m.reach;
    const rate = pct(rc.read, rc.total);
    const hero = '<div class="reach-card">' +
      '<div class="ring" style="background:conic-gradient(var(--mod-color) 0 ' + rate + '%, var(--tui-surface-sunken) ' + rate + '% 100%)">' +
        '<div class="ring-mid"><div class="ring-num" style="color:var(--mod-color)">' + rate + '%</div><div class="ring-cap">平均触达</div></div>' +
      '</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div class="mod-hero-title">本月共发布 ' + rc.published + ' 条公告</div>' +
        '<div class="mod-hero-sub">累计已读 ' + rc.read + ' / ' + rc.total + '　紧急 ' + rc.urgent + ' 条　草稿 ' + rc.draft + ' 条</div>' +
        '<div class="bar-wrap" style="margin-top:10px">' + bar(rate) + '<span class="bar-pct">' + rate + '%</span></div>' +
      '</div>' +
    '</div>';

    const items = m.items.map((it) => {
      const a = TONE[it.levelTone] || TONE.brand;
      const p = pct(it.read, it.total);
      return '<div class="anno' + (it.pinned ? ' pinned' : '') + '" data-action="toast" data-msg="公告详情：' + esc(it.title) + '（原型演示）">' +
        (it.level === '紧急' ? '<span class="ribbon">紧急</span>' : '') +
        '<div class="anno-top">' +
          '<span class="row-icon" style="width:32px;height:32px;background:' + a.bg + ';color:' + a.fg + '">' + icon('megaphone', 16) + '</span>' +
          '<span class="anno-title" style="margin-left:2px">' + esc(it.title) + '</span>' +
          (it.pinned ? '<span style="margin-left:auto">' + tag('置顶', 'brand') + '</span>' : '') +
        '</div>' +
        '<div class="anno-excerpt">' + esc(it.excerpt) + '</div>' +
        '<div class="anno-foot">' +
          '<span class="anno-meta">' + icon('school', 13) + esc(it.scope) + '</span>' +
          '<span class="anno-meta">' + icon('clock', 13) + esc(it.time) + '</span>' +
          '<span class="anno-read">已读 ' + it.read + '/' + it.total + bar(p) + '</span>' +
        '</div>' +
      '</div>';
    }).join('');

    return modHead(m) + modWrap('announcement',
      hero +
      statRow(m.stats.map((s, i) => Object.assign({ icon: ['megaphone', 'eye', 'bell-ring'][i] }, s))) +
      segBar('announcement', m.segments) +
      '<div class="stack" style="margin-top:12px">' + items + '</div>' +
      '<div class="legacy-note">公告发布走后端 Announcement 模型，按班级（ClassGroup）定向推送；已读回执由学生端上报，用于统计触达率与未读名单。</div>'
    ) + modFab('announcement', m);
  }

  /* =====================================================================
     ④ 成长档案 —— 学生选择器 + 徽章墙 + 成长时间轴
     ===================================================================== */
  function renderPortfolio(m) {
    const cur = state.pick.portfolio || (m.students[0] && m.students[0].id);
    const picks = m.students.map((s) =>
      '<button class="pick' + (s.id === cur ? ' on' : '') + '" data-pick-student="' + s.id + '">' +
        '<span class="avatar ' + s.tone + '" style="width:40px;height:40px">' + esc(s.name[0]) + '</span>' +
        '<span class="pick-name">' + esc(s.name) + '</span>' +
        '<span class="pick-count">' + s.count + ' 条</span>' +
      '</button>').join('');

    const badges = m.badges.map((b) => {
      const t = TONE[b.tone] || TONE.brand;
      return '<div class="badge">' +
        '<span class="badge-ic" style="background:' + t.bg + ';color:' + t.fg + '">' + icon(b.icon, 19) + '</span>' +
        '<span class="badge-count" style="color:' + t.fg + '">' + b.count + '</span>' +
        '<span class="badge-name">' + esc(b.name) + '</span>' +
      '</div>';
    }).join('');

    const curName = (m.students.filter((s) => s.id === cur)[0] || m.students[0] || {}).name || '全部学生';
    const tl = m.timeline.map((it) => {
      const a = TONE[it.catTone] || TONE.violet;
      return '<div class="tl-item">' +
        '<span class="tl-node">' + icon(it.icon, 13) + '</span>' +
        '<div class="tl-card">' +
          '<div class="tl-head">' +
            '<span class="avatar ' + it.tone + '" style="width:30px;height:30px;font-size:12px">' + esc(it.student[0]) + '</span>' +
            '<div style="min-width:0;flex:1"><div class="tl-title">' + esc(it.title) + '</div>' +
              '<div class="row-desc">' + esc(it.student) + ' · ' + esc(it.cls) + '</div></div>' +
            '<span class="tl-date">' + esc(it.date) + '</span>' +
          '</div>' +
          '<div class="tl-desc">' + esc(it.desc) + '</div>' +
          (it.thumb ? '<div class="tl-thumb">' + icon('image', 22) + '<span>作品 / 证书预览</span></div>' : '') +
          '<div class="tl-meta">' + tag(it.cat, it.catTone) +
            '<span class="meta-chip">' + icon('bookmark', 12) + '已归档</span>' +
            '<span class="meta-chip" style="margin-left:auto">' + icon('pencil', 12) + '编辑</span>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');

    return modHead(m) + modWrap('portfolio',
      '<div class="mod-hero"><div class="mod-hero-title">学生成长档案</div>' +
        '<div class="mod-hero-sub">共 ' + m.stats[0].num + ' 条成长记录 · 覆盖 ' + m.students.length + ' 名学生，记录学习成果、实践经历与荣誉奖项</div></div>' +
      '<div class="sect-title">选择学生<span class="spacer">左右滑动查看</span></div>' +
      '<div class="pick-row">' + picks + '</div>' +
      statRow(m.stats.map((s, i) => Object.assign({ icon: ['award', 'image', 'trophy'][i] }, s))) +
      '<div class="sect-title">徽章墙<span class="spacer">累计 ' + m.badges.reduce((a, b) => a + b.count, 0) + ' 枚</span></div>' +
      '<div class="badge-grid">' + badges + '</div>' +
      '<div class="sect-title">' + esc(curName) + ' · 成长轨迹<span class="spacer">按时间倒序</span></div>' +
      '<div class="tl">' + tl + '</div>' +
      '<div class="legacy-note">档案条目来自后端 TeacherPortfolio 模型，可关联学生（student_id）与作品附件；徽章由分类统计自动汇总。</div>'
    ) + modFab('portfolio', m);
  }

  /* =====================================================================
     ⑤ 问卷互评 —— 回收率环形进度 + 匿名保护
     ===================================================================== */
  function renderSurvey(m) {
    const items = m.items.map((it) => {
      const r = pct(it.collected, it.total);
      return '<div class="sv-card" data-action="toast" data-msg="问卷详情 / 结果（原型演示）">' +
        '<div class="sv-top">' +
          '<div class="ring" style="width:70px;height:70px;background:conic-gradient(var(--mod-color) 0 ' + r + '%, var(--tui-surface-sunken) ' + r + '% 100%)">' +
            '<div class="ring-mid"><div class="ring-num" style="color:var(--mod-color)">' + r + '%</div><div class="ring-cap">回收率</div></div>' +
          '</div>' +
          '<div class="sv-main">' +
            '<div style="display:flex;align-items:center;gap:8px">' +
              '<span class="sv-title" style="flex:1">' + esc(it.title) + '</span>' + tag(it.status, it.statusTone) +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;margin-top:8px">' +
              '<span class="anon-chip">' + icon('lock', 12) + '匿名保护</span>' +
              '<span class="meta-chip">' + icon('clipboard-list', 12) + it.questions + ' 题</span>' +
            '</div>' +
            '<div class="sv-dims">' + it.dims.map((d) => '<span class="meta-chip">' + esc(d) + '</span>').join('') + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="sv-foot">' +
          '<span>' + icon('users', 13) + ' 回收 ' + it.collected + '/' + it.total + ' 份</span>' +
          '<span>' + icon('calendar-clock', 13) + ' 截止 ' + esc(it.deadline) + '</span>' +
          '<span style="margin-left:auto;color:var(--mod-color);font-weight:600">' + (it.status === '进行中' ? '查看结果' : '查看报告') + icon('chevron-right', 12) + '</span>' +
        '</div>' +
      '</div>';
    }).join('');

    return modHead(m) + modWrap('survey',
      '<div class="mod-hero"><div class="mod-hero-title">问卷中心</div>' +
        '<div class="mod-hero-sub">支持匿名问卷发放、学生互评与结果统计；匿名问卷不记录填写人，结果仅用于关怀与改进。</div></div>' +
      statRow(m.stats.map((s, i) => Object.assign({ icon: ['activity', 'check-check', 'clipboard-list'][i] }, s))) +
      segBar('survey', m.segments) +
      '<div class="stack" style="margin-top:12px">' + items + '</div>' +
      '<div class="legacy-note">问卷走后端 PeerSurvey / 匿名响应模型：匿名问卷的 respondent 字段加密存储，教师端仅可见聚合结果。</div>'
    ) + modFab('survey', m);
  }

  /* =====================================================================
     ⑥ 关怀中心 —— 关怀温度 + 待回访 + 记录时间轴
     ===================================================================== */
  function renderCare(m) {
    const tc = m.temperature;
    const hero = '<div class="temp-card">' +
      '<div class="temp-top"><span class="temp-num">' + tc.score + '</span><span style="font-size:13px;font-weight:600;color:#8a5c7c">关怀温度</span>' +
        '<span style="margin-left:auto;font-size:11px;color:#8a5c7c">满分 100</span></div>' +
      '<div class="temp-bar"><i style="width:' + tc.score + '%"></i></div>' +
      '<div class="temp-note">' + esc(tc.note) + '</div>' +
    '</div>';

    const fu = m.followups.length ? '<div class="sect-title">待回访提醒<span class="spacer">' + m.followups.length + ' 条</span></div>' +
      '<div class="list">' + m.followups.map((f) =>
        '<div class="followup" data-sheet="care">' +
          '<span class="avatar sm ' + f.tone + '">' + esc(f.name[0]) + '</span>' +
          '<span class="row-main"><span class="row-label" style="font-size:13.5px">' + esc(f.name) + '</span>' +
            '<span class="row-desc">' + esc(f.reason) + '</span></span>' +
          '<span class="followup-due">' + esc(f.due) + '</span>' +
        '</div>').join('') + '</div>' : '';

    const tl = m.timeline.map((it) => {
      const a = TONE[it.typeTone] || TONE.warn;
      return '<div class="tl-item">' +
        '<span class="tl-node">' + icon(it.icon, 13) + '</span>' +
        '<div class="tl-card">' +
          '<div class="tl-head">' +
            '<span class="avatar ' + it.tone + '" style="width:30px;height:30px;font-size:12px">' + esc(it.student[0]) + '</span>' +
            '<div style="min-width:0;flex:1"><div class="tl-title">' + esc(it.title) + '</div>' +
              '<div class="row-desc">' + esc(it.student) + ' · ' + esc(it.when) + '</div></div>' +
            tag(it.type, it.typeTone) +
          '</div>' +
          '<div class="tl-desc">' + esc(it.content) + '</div>' +
          '<div class="tl-meta">' +
            (it.place !== '—' ? '<span class="meta-chip">' + icon('map-pin', 12) + esc(it.place) + '</span>' : '') +
            '<span class="meta-chip">' + icon('messages-square', 12) + esc(it.way) + '</span>' +
            '<span class="meta-chip"' + (it.done ? ' style="color:var(--tui-success)"' : '') + '>' +
              icon(it.done ? 'circle-check' : 'rotate-ccw', 12) + (it.done ? '已闭环' : '待回访') + '</span>' +
          '</div>' +
          (it.followup !== '—' ? '<div class="tl-next">' + icon('target', 14) + '<span>后续：' + esc(it.followup) + '</span></div>' : '') +
        '</div>' +
      '</div>';
    }).join('');

    return modHead(m) + modWrap('care',
      hero +
      statRow(m.stats.map((s, i) => Object.assign({ icon: ['heart-pulse', 'rotate-ccw', 'notebook-pen'][i] }, s))) +
      fu +
      '<div class="sect-title">关怀记录<span class="spacer">谈心 / 家访 / 激励</span></div>' +
      segBar('care', m.segments) +
      '<div class="tl" style="margin-top:12px">' + tl + '</div>' +
      '<div class="legacy-note">关怀记录来自后端 CareRecord / CareCenter 模型，支持谈心、家访、激励三类；后续计划到期自动生成待回访提醒。</div>'
    ) + modFab('care', m);
  }

  /* =====================================================================
     ⑦ 家校沟通 —— 家长联系人卡 + 沟通台账
     ===================================================================== */
  function renderGuardian(m) {
    const seg = state.seg.guardian || 0;
    let body;
    if (seg === 0) {
      body = '<div class="stack" style="margin-top:12px">' + m.contacts.map((c) =>
        '<div class="gd-card">' +
          '<div class="gd-top">' +
            '<span class="avatar ' + c.tone + '">' + esc(c.name[0]) + '</span>' +
            '<div style="flex:1;min-width:0"><div class="gd-name">' + esc(c.name) + ' ' + tag(c.relation, c.relTone) + '</div>' +
              '<div class="gd-sub">' + esc(c.student) + ' 家长 · ' + esc(c.cls) + ' · ' + esc(c.phone) + '</div></div>' +
            (c.pending ? count(1, 'warn') : '') +
          '</div>' +
          '<div class="gd-ops">' +
            '<button class="gd-op primary" data-sheet="guardian" data-ctx="' + c.id + '">' + icon('phone-call', 15) + '通话</button>' +
            '<button class="gd-op" data-sheet="guardian" data-ctx="' + c.id + '">' + icon('message-square-plus', 15) + '短信</button>' +
            '<button class="gd-op" data-sheet="guardian" data-ctx="' + c.id + '">' + icon('messages-square', 15) + '微信</button>' +
          '</div>' +
          '<div class="tl-meta" style="margin-top:11px;padding-top:10px;border-top:1px solid var(--tui-border)">' +
            '<span class="meta-chip">' + icon('clock', 12) + '最近沟通 ' + esc(c.last) + '</span>' +
            '<span class="meta-chip">' + icon('phone-outgoing', 12) + '方式 ' + esc(c.channel) + '</span>' +
          '</div>' +
        '</div>').join('') + '</div>';
    } else {
      body = '<div class="tl" style="margin-top:12px">' + m.ledger.map((l) =>
        '<div class="tl-item">' +
          '<span class="tl-node">' + icon(l.channel === '电话' ? 'phone-call' : 'message-square-plus', 13) + '</span>' +
          '<div class="tl-card">' +
            '<div class="tl-head">' +
              '<span class="avatar ' + l.tone + '" style="width:30px;height:30px;font-size:12px">' + esc(l.student[0]) + '</span>' +
              '<div style="min-width:0;flex:1"><div class="tl-title">' + esc(l.student) + ' · ' + esc(l.relation) + '</div>' +
                '<div class="row-desc">' + esc(l.when) + (l.dur !== '—' ? ' · 通话 ' + esc(l.dur) : '') + '</div></div>' +
              tag(l.channel, l.chTone) +
            '</div>' +
            '<div class="tl-desc">' + esc(l.content) + '</div>' +
            (l.pending ? '<div class="tl-next" style="background:var(--tui-warn-soft);color:var(--tui-warn)">' + icon('rotate-ccw', 14) + '<span>待家长反馈，建议明日前再次跟进</span></div>' : '') +
          '</div>' +
        '</div>').join('') + '</div>';
    }

    return modHead(m) + modWrap('guardian',
      '<div class="mod-hero"><div class="mod-hero-title">家校沟通留痕</div>' +
        '<div class="mod-hero-sub">家长联系人 ' + m.contacts.length + ' 位 · 本月沟通 ' + m.stats[1].num + ' 次；所有通话 / 短信自动生成沟通台账，可作为工作留痕与家访凭证。</div></div>' +
      statRow(m.stats.map((s, i) => Object.assign({ icon: ['contact', 'heart-handshake', 'rotate-ccw'][i] }, s))) +
      '<div style="margin-top:12px">' + segBar('guardian', m.segments) + '</div>' +
      body +
      '<div class="legacy-note">沟通记录来自后端 GuardianContact / ContactLog 模型；台账可导出为家访记录，与关怀中心数据互通。</div>'
    ) + modFab('guardian', m);
  }

  /* =====================================================================
     ⑧ 今日任务（v3：时间轴式）—— 日期条 + 逾期/时段分组时间轴
     ===================================================================== */
  function renderTasks(m) {
    const prog = m.progress;
    const rate = pct(prog.done, prog.total);
    const strip = '<div class="date-strip">' + m.dateStrip.map((d) =>
      '<div class="day-cell' + (d.on ? ' on' : '') + '">' + esc(d.w) + '<b>' + esc(d.d) + '</b></div>').join('') + '</div>';

    const secs = m.timeline.map((sec) => {
      const toneMap = { danger: 'var(--tui-danger)', success: 'var(--tui-success)', brand: 'var(--tui-brand)', quiet: 'var(--tui-text-tertiary)' };
      const tone = toneMap[sec.tone] || 'var(--tui-text-tertiary)';
      const items = sec.items.map((it) => {
        const done = state.tasksDone[it.id] != null ? state.tasksDone[it.id] : it.done;
        const nodeCls = sec.tone === 'danger' ? ' urgent' : (sec.tone === 'success' ? ' now' : '');
        return '<div class="tlt' + nodeCls + '">' +
          '<div class="tl-time">' + esc(it.t) + (it.priority === '高' ? '<span style="color:var(--tui-danger)">· 高优先</span>' : '') + '</div>' +
          '<div class="tcard" data-task-toggle="' + it.id + '">' +
            '<span class="tick"' + (done ? ' style="background:var(--tui-success);box-shadow:none;border-color:var(--tui-success)"' : '') + '>' + (done ? icon('check', 13) : '') + '</span>' +
            '<div style="flex:1;min-width:0">' +
              '<div class="task-title"' + (done ? ' style="color:var(--tui-text-quiet);text-decoration:line-through"' : '') + '>' + esc(it.title) + '</div>' +
              '<div class="task-meta">' +
                '<span class="tag ' + (tagCls[it.priTone] || '') + '">' + esc(it.priority) + '优先</span>' +
                '<span class="meta-chip">' + icon('link', 12) + esc(it.from) + '</span>' +
              '</div>' +
            '</div>' +
            '<span style="align-self:center;color:var(--tui-text-quiet)">' + icon('chevron-right', 15) + '</span>' +
          '</div>' +
        '</div>';
      }).join('');
      return '<div class="tlg">' +
          (sec.tone === 'danger' ? icon('triangle-alert', 13) : '') + esc(sec.title) +
          '<span class="tlg-n" style="background:' + tone + '">' + sec.items.length + '</span>' +
          (sec.tone === 'danger' ? '<span style="margin-left:auto;font-size:11px;font-weight:400;color:var(--tui-text-quiet)">建议优先处理</span>' : '') +
        '</div>' +
        '<div class="tl">' + items + '</div>';
    }).join('');

    return modHead(m) + modWrap('tasks',
      strip +
      '<div class="prog-line">今日完成 ' + prog.done + ' / ' + prog.total +
        '<div class="bar"><i style="width:' + rate + '%"></i></div><em>' + rate + '%</em>' +
      '</div>' +
      secs +
      '<div class="legacy-note">任务来自后端 TeacherTask 模型，与审批 / 预警 / 关怀模块联动；逾期任务红色置顶，点击卡片可勾选完成，时间节点自动按截止时间归组。</div>'
    ) + modFab('tasks', m);
  }

  /* =====================================================================
     ⑨ AI 洞察 —— 建议卡（置信度）+ 洞察指标 + 周报
     ===================================================================== */
  function renderAI(m) {
    const hero = '<div class="ai-hero">' +
      '<div class="ai-hero-top">' +
        '<span style="width:40px;height:40px;border-radius:13px;background:#fff;color:var(--mod-color);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:var(--tui-shadow-1)">' + icon('brain', 21) + '</span>' +
        '<div style="flex:1;min-width:0"><div class="mod-hero-title" style="color:#3b2c72">绵小城 · 主动洞察</div>' +
          '<div class="row-desc" style="white-space:normal;margin-top:3px">分析时间：今天 08:00 · 数据源：出勤 / 测评 / 教务 / 反馈</div></div>' +
        '<button class="btn btn-soft btn-sm" data-sheet="ai">生成周报</button>' +
      '</div>' +
      '<div class="ai-hero-text" style="margin-top:12px">' + esc(m.headline) + '</div>' +
    '</div>';

    const insights = m.insights.map((it) => {
      const t = TONE[it.tone] || TONE.violet;
      return '<div class="ai-insight" style="--tone-color:' + t.fg + '" data-sheet="ai" data-ctx="' + it.id + '">' +
        '<div class="ai-insight-head">' +
          '<span class="row-icon" style="background:' + t.bg + ';color:' + t.fg + '">' + icon(it.icon, 18) + '</span>' +
          '<span class="ai-insight-title" style="flex:1;min-width:0">' + esc(it.title) + '</span>' +
          tag(it.tone === 'danger' ? '优先' : it.tone === 'warn' ? '关注' : '正向', it.tone) +
        '</div>' +
        '<div class="ai-insight-desc">' + esc(it.desc) + '</div>' +
        '<div class="ai-insight-foot">' +
          '<div class="conf">' +
            '<div class="conf-top">' + icon('gauge', 12) + '置信度 ' + it.confidence + '%</div>' +
            confBar(it.confidence) +
          '</div>' +
          '<button class="btn btn-primary btn-sm" data-ai-action="' + it.actionKind + '" data-ref="' + esc(it.ref) + '">' + esc(it.action) + '</button>' +
        '</div>' +
      '</div>';
    }).join('');

    const metrics = m.metrics.map((mm) => {
      const t = TONE[mm.tone] || TONE.brand;
      return '<div class="ai-metric">' +
        '<span class="ai-metric-ic" style="background:' + t.bg + ';color:' + t.fg + '">' + icon(mm.icon, 18) + '</span>' +
        '<div><div class="ai-metric-num" style="color:' + t.fg + '">' + mm.value + '</div>' +
          '<div class="ai-metric-label">' + esc(mm.label) + '</div></div>' +
        '<span class="ai-metric-delta" style="color:' + t.fg + '">' + esc(mm.delta) + '</span>' +
      '</div>';
    }).join('');

    const rp = m.report;
    const report = '<div class="report">' +
      '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">' +
        '<span class="row-icon" style="width:32px;height:32px;background:var(--mod-soft);color:var(--mod-color)">' + icon('chart-line', 16) + '</span>' +
        '<div style="flex:1;min-width:0"><div style="font-size:13.5px;font-weight:700">' + esc(rp.week) + ' 洞察周报</div>' +
          '<div class="row-desc">生成于 ' + esc(rp.generated) + '</div></div>' +
        '<button class="link-more" data-action="toast" data-msg="已导出周报（原型演示）">导出' + icon('download', 13) + '</button>' +
      '</div>' +
      rp.points.map((p) => '<div class="report-point">' + esc(p) + '</div>').join('') +
    '</div>';

    return modHead(m, '<button class="icon-btn" data-action="toast" data-msg="洞察设置（原型演示）">' + icon('sliders-horizontal', 19) + '</button>') +
      modWrap('ai',
        hero +
        '<div class="sect-title">洞察概览<span class="spacer">近 14 天</span></div>' +
        '<div class="ai-metric-grid">' + metrics + '</div>' +
        '<div class="sect-title">主动建议<span class="spacer">' + m.insights.length + ' 条</span></div>' +
        '<div class="stack">' + insights + '</div>' +
        '<div class="sect-title">周报</div>' + report +
        '<div class="legacy-note">洞察由后端主动引擎（proactive_engine / proactive_insight）生成，信号来自学习事件、测评与反馈聚合；建议仅为推荐，最终处置由教师确认。</div>'
      ) + modFab('ai', m);
  }

  /* ---------------- 模块分发 ---------------- */
  function renderModule(key) {
    const m = window.DB.modules[key];
    if (!m) return '';
    switch (key) {
      case 'approval': return renderApproval(m);
      case 'crisis': return renderCrisis(m);
      case 'announcement': return renderAnnouncement(m);
      case 'portfolio': return renderPortfolio(m);
      case 'survey': return renderSurvey(m);
      case 'care': return renderCare(m);
      case 'guardian': return renderGuardian(m);
      case 'tasks': return renderTasks(m);
      case 'ai': return renderAI(m);
      default: return '';
    }
  }

  function renderSubPage() {
    if (state.subId === 'features') return renderFeatures();
    if (window.DB.modules[state.subId]) return renderModule(state.subId);
    return renderFeatures();
  }

  /* =====================================================================
     弹窗（底部弹窗 / ActionSheet 范式）
     ===================================================================== */
  function chips(group, options) {
    const sel = state.chip[group];
    return '<div class="chips">' + options.map((o) =>
      '<button class="chip-btn' + (sel === o ? ' on' : '') + '" data-chip="' + group + '" data-val="' + esc(o) + '">' + esc(o) + '</button>').join('') + '</div>';
  }
  /* 多选 chips（用于「可多选」的维度 / 包含项） */
  function chipsMulti(group, options) {
    return '<div class="chips">' + options.map((o) =>
      '<button class="chip-btn' + (state.multi[group + ':' + o] ? ' on' : '') + '" data-multi="' + group + '" data-val="' + esc(o) + '">' + esc(o) + '</button>').join('') + '</div>';
  }
  function optRows(group, rows) {
    return '<div class="fgroup" style="margin:0">' + rows.map((r) => {
      const on = !!state.multi[group + ':' + r.id];
      return '<button class="opt-row' + (on ? ' on' : '') + '" data-multi="' + group + '" data-val="' + r.id + '">' +
        '<span class="opt-check">' + (on ? icon('check', 13) : '') + '</span>' +
        '<span class="avatar sm ' + (r.tone || 'tone-slate') + '">' + esc((r.label || '?')[0]) + '</span>' +
        '<span style="flex:1;min-width:0"><span class="opt-row-label">' + esc(r.label) + '</span>' +
          (r.desc ? '<br><span class="opt-row-desc">' + esc(r.desc) + '</span>' : '') + '</span>' +
      '</button>';
    }).join('') + '</div>';
  }
  function frow(label, value, ph, req) {
    return '<div class="frow"><span class="frow-label">' + esc(label) + (req ? '<span class="frow-req">*</span>' : '') + '</span>' +
      '<span class="frow-main' + (ph ? ' ph' : '') + '">' + esc(value) + '</span>' +
      icon('chevron-down', 15, 'frow-arrow') + '</div>';
  }

  const SHEETS = {
    /* ① 审批：审批处理弹窗 */
    approval: function (ctx) {
      const m = window.DB.modules.approval;
      const it = m.items.filter((x) => x.id === ctx)[0] || m.items[0];
      /* v3：AI 辅助审批 */
      const ai = it.ai || m.aiFallback;
      const adopted = state.chip.apResult === ai.suggest;
      const aiChecks = ai.checks.map((c) =>
        '<div class="ai-check"><span style="display:flex;color:' + (c.ok ? 'var(--tui-success)' : 'var(--tui-warn)') + '">' +
          icon(c.ok ? 'circle-check' : 'triangle-alert', 14) + '</span>' +
          '<span class="ai-check-k">' + esc(c.k) + '</span><span class="ai-check-v">' + esc(c.v) + '</span></div>').join('');
      const aiBlock =
        '<div class="ai-assist">' +
          '<div class="ai-assist-head">' +
            '<span class="ai-assist-ic">' + icon('brain', 17) + '</span>' +
            '<div style="flex:1;min-width:0"><div class="ai-assist-title">绵小城 AI 审批助手</div>' +
              '<div class="ai-assist-sub">自动核验材料与历史数据 · 置信度 ' + ai.confidence + '%</div></div>' +
            (adopted ? tag('已采纳', 'success') : '') +
          '</div>' +
          '<div class="ai-assist-body">' + esc(ai.summary) + '</div>' +
          '<div class="ai-checks">' + aiChecks + '</div>' +
          '<div class="ai-verdict"><span class="ai-verdict-k">建议结论</span>' +
            '<span class="ai-verdict-v" style="color:' + (ai.suggest === '同意' ? 'var(--tui-success)' : 'var(--tui-danger)') + '">' + esc(ai.suggest) + '</span>' +
            '<span class="ai-assist-sub" style="margin-left:auto">仅供参考 · 教师确认</span></div>' +
          '<div class="ai-assist-body">' + esc(ai.reason) + '</div>' +
          '<button class="btn ' + (adopted ? 'btn-ghost' : 'btn-primary') + ' btn-sm" style="margin-top:11px" data-ai-adopt="' + esc(ai.suggest) + '">' +
            icon('wand-sparkles', 15) + (adopted ? '已采纳 AI 建议' : '采纳建议并填充审批意见') + '</button>' +
        '</div>';
      const flow = it.flow.map((s) => '<div class="flow-step ' + s.state + '"><span class="flow-dot"></span>' +
        '<div class="flow-k">' + esc(s.k) + '</div><div class="flow-t">' + esc(s.t) + '</div></div>').join('');
      const files = it.files.length ? it.files.map((f) =>
        '<div class="file-row"><span class="fi" style="background:var(--tui-surface-sunken);color:var(--tui-text-secondary)">' + icon(f.icon, 15) + '</span>' +
        '<span style="flex:1;min-width:0"><span class="fname">' + esc(f.name) + '</span><br><span class="fsize">' + esc(f.size) + '</span></span>' +
        icon('eye', 15, 'row-arrow') + '</div>').join('') : '<div class="frow-main ph" style="text-align:left">无附件</div>';
      const opinion = state.chip.apResult === '驳回'
        ? '证明材料不完整，请补充后重新提交。'
        : (adopted ? ai.opinion : '');
      return {
        icon: 'clipboard-check', title: '审批处理', sub: it.student + ' · ' + it.type,
        body:
          '<div class="detail-block">' +
            '<div class="detail-title">申请信息</div>' +
            '<div class="kv" style="margin-top:0">' +
              '<span class="kv-k">申请学生</span><span class="kv-v">' + esc(it.student) + '（' + esc(it.cls) + '）</span>' +
              '<span class="kv-k">请假时间</span><span class="kv-v">' + esc(it.range) + '</span>' +
              '<span class="kv-k">请假时长</span><span class="kv-v">' + esc(it.days) + '</span>' +
              '<span class="kv-k">事由</span><span class="kv-v">' + esc(it.reason) + '</span>' +
              '<span class="kv-k">提交时间</span><span class="kv-v">' + esc(it.submitted) + '</span>' +
            '</div>' +
          '</div>' +
          '<div class="sect-title" style="margin-top:0">附件</div>' +
          '<div class="fgroup" style="padding:0 0 0">' + files + '</div>' +
          '<div class="sect-title">审批流程</div>' +
          '<div class="detail-block"><div class="flow" style="margin-top:0;border-top:none;padding-top:0">' + flow + '</div></div>' +
          aiBlock +
          '<div class="sect-title">审批意见</div>' +
          chips('apResult', ['同意', '驳回', '转办学工处']) +
          '<div class="sect-title">意见说明</div>' +
          '<textarea class="ftarea" placeholder="驳回时必填，如「证明材料不完整，请补充后重新提交」">' + esc(opinion) + '</textarea>' +
          '<div class="sheet-tip" style="margin-top:12px">' + icon('info', 14) +
            '<span>同意后自动推送给学生与学工处，并计入学生请假台账；驳回将退回学生重新提交。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>稍后处理</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="审批已提交（原型演示）">提交审批</button>',
      };
    },

    /* ② 预警：处置弹窗 */
    crisis: function (ctx) {
      const m = window.DB.modules.crisis;
      const it = m.items.filter((x) => x.id === ctx)[0] || m.items[0];
      const steps = '<div class="steps">' + it.steps.map((s) =>
        '<div class="step ' + s.state + '"><span class="step-dot">' + (s.state === 'done' ? icon('check', 11) : '') + '</span>' + esc(s.k) + '</div>').join('') + '</div>';
      const sigs = it.signals.map((s) => '<span class="sig ' + s.dir + '">' + esc(s.k) + ' <b>' + esc(s.v) + '</b></span>').join('');
      return {
        icon: 'shield-alert', title: '预警处置', sub: it.student + ' · ' + it.title,
        body:
          '<div class="sheet-tip danger">' + icon('triangle-alert', 14) +
            '<span>' + esc(it.level) + '预警 · ' + esc(it.source) + '　触发于 ' + esc(it.triggered) + '</span></div>' +
          '<div class="sect-title">风险信号</div>' +
          '<div class="sig-row" style="margin-top:0">' + sigs + '</div>' +
          '<div class="sect-title">处置流程</div>' +
          '<div class="detail-block">' + steps + '</div>' +
          '<div class="sect-title">本次处置方式</div>' +
          chips('crWay', ['当面谈话', '电话联系', '联系家长', '转介心理中心']) +
          '<div class="sect-title">跟进记录</div>' +
          '<textarea class="ftarea" placeholder="记录本次沟通情况、学生状态与后续安排…">已与学生当面沟通，了解压力来源，情绪较前平稳。</textarea>' +
          '<div class="sect-title">回访时间</div>' +
          '<div class="fgroup">' + frow('回访日期', '2026-10-14', false, true) + frow('提醒方式', '系统提醒 + 工作通知', false) + '</div>' +
          '<div class="sheet-tip" style="margin-top:12px">' + icon('info', 14) +
            '<span>提交后生成关怀记录并写入学生成长档案；高危预警将同步至学院心理健康教师。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>取消</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="处置已记录，已生成关怀记录（原型演示）">提交处置</button>',
      };
    },

    /* ③ 公告：新建公告弹窗 */
    announcement: function (ctx) {
      const m = window.DB.modules.announcement;
      const classes = [
        { id: 'k1', label: '计科 2301', desc: '42 人', tone: 'tone-blue' },
        { id: 'k2', label: '计科 2302', desc: '40 人', tone: 'tone-cyan' },
        { id: 'k3', label: '软工 2301', desc: '38 人', tone: 'tone-violet' },
      ];
      return {
        icon: 'megaphone', title: '发布公告', sub: '面向班级发布通知与公告',
        body:
          '<div class="sect-title" style="margin-top:0">公告标题</div>' +
          '<textarea class="ftarea" style="min-height:52px" placeholder="请输入公告标题，如「关于周一班会时间调整的通知」">关于周一班会时间调整的通知</textarea>' +
          '<div class="sect-title">公告正文</div>' +
          '<textarea class="ftarea" placeholder="请输入公告内容…">原定周一 14:00 的班会调整至 16:00，地点 3 号教学楼 201，请相互转告。</textarea>' +
          '<div class="sect-title">发布对象<span class="spacer">可多选</span></div>' +
          optRows('anClasses', classes) +
          '<div class="sect-title">优先级</div>' +
          chips('anLevel', ['普通', '重要', '紧急']) +
          '<div class="sect-title">发布方式</div>' +
          '<div class="fgroup">' + frow('发布时间', '立即发布', false) + frow('置顶', '是', false) + frow('短信提醒', '仅重要 / 紧急', false) + '</div>' +
          '<div class="sect-title">附件</div>' +
          '<div class="att-grid">' +
            '<span class="att-thumb">' + icon('image', 18, 'fi') + '通知图.png</span>' +
            '<button class="att-add" data-action="toast" data-msg="添加附件（原型演示）">' + icon('plus', 18) + '添加</button>' +
          '</div>' +
          '<div class="sheet-tip" style="margin-top:12px">' + icon('info', 14) +
            '<span>公告推送至学生端 App 与消息中心，并统计已读 / 未读；紧急公告将同步短信提醒家长。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>存为草稿</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="公告已发布，正在推送（原型演示）">发布公告</button>',
      };
    },

    /* ④ 成长档案：新增档案弹窗 */
    portfolio: function (ctx) {
      const m = window.DB.modules.portfolio;
      const students = m.students.map((s) => ({ id: s.id, label: s.name, desc: s.count + ' 条记录', tone: s.tone }));
      return {
        icon: 'award', title: '新增成长档案', sub: '记录学生成长成果',
        body:
          '<div class="sect-title" style="margin-top:0">选择学生</div>' +
          optRows('pfStudent', students) +
          '<div class="sect-title">档案分类</div>' +
          chips('pfCat', ['学习成果', '实践经历', '荣誉奖项', '技能证书']) +
          '<div class="sect-title">标题</div>' +
          '<textarea class="ftarea" style="min-height:52px" placeholder="如「省级程序设计竞赛三等奖」"></textarea>' +
          '<div class="sect-title">时间与说明</div>' +
          '<div class="fgroup">' + frow('获奖 / 完成时间', '2026-09-28', false, true) + frow('颁发 / 组织单位', '请选择或填写', true) + frow('可见范围', '学生本人 + 家长', false) + '</div>' +
          '<textarea class="ftarea" placeholder="补充说明，如团队赛担任队长…"></textarea>' +
          '<div class="sect-title">凭证 / 作品附件</div>' +
          '<div class="att-grid">' +
            '<button class="att-add" data-action="toast" data-msg="上传图片 / 证书（原型演示）">' + icon('upload', 18) + '上传</button>' +
          '</div>' +
          '<div class="sheet-tip" style="margin-top:12px">' + icon('info', 14) +
            '<span>档案提交后计入学生成长轨迹与徽章统计，学生与家长可在学生端查看。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>取消</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="成长档案已录入（原型演示）">保存档案</button>',
      };
    },

    /* ⑤ 问卷：新建问卷弹窗 */
    survey: function (ctx) {
      return {
        icon: 'clipboard-list', title: '新建问卷', sub: '匿名问卷发放与学生互评',
        body:
          '<div class="sect-title" style="margin-top:0">问卷标题</div>' +
          '<textarea class="ftarea" style="min-height:52px" placeholder="如「班级学风建设匿名问卷」"></textarea>' +
          '<div class="sect-title">问卷类型</div>' +
          chips('svType', ['匿名问卷', '实名问卷', '学生互评']) +
          '<div class="sect-title">评价维度<span class="spacer">可多选</span></div>' +
          chipsMulti('svDim', ['学习氛围', '班委工作', '课堂纪律', '活动组织']) +
          '<div class="sect-title">题型</div>' +
          chips('svQ', ['单选题', '多选题', '评分题', '填空题']) +
          '<div class="sect-title">发放与截止</div>' +
          '<div class="fgroup">' + frow('发放对象', '计科 2301（42 人）', false) + frow('截止时间', '2026-10-15 23:59', false, true) + frow('匿名保护', '开启', false) + frow('完成后展示结果', '是', false) + '</div>' +
          '<div class="sheet-tip">' + icon('lock', 14) +
            '<span>匿名问卷不记录填写人身份，教师端仅可见聚合结果，保障学生真实反馈。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>保存草稿</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="问卷已发布并推送学生（原型演示）">发布问卷</button>',
      };
    },

    /* ⑥ 关怀：新增关怀记录弹窗 */
    care: function (ctx) {
      const m = window.DB.modules.care;
      const students = window.DB.myStudents.slice(0, 5).map((s) => ({ id: s.id, label: s.name, desc: s.className, tone: s.tone }));
      return {
        icon: 'heart-pulse', title: '新增关怀记录', sub: '谈心 · 家访 · 激励',
        body:
          '<div class="sect-title" style="margin-top:0">关怀类型</div>' +
          chips('caType', ['谈心', '家访', '激励', '转介']) +
          '<div class="sect-title">关怀对象</div>' +
          optRows('caStudent', students) +
          '<div class="sect-title">时间与方式</div>' +
          '<div class="fgroup">' + frow('关怀时间', '今天 16:20', false, true) + frow('沟通方式', '面对面', false) + frow('地点', '辅导员办公室', false) + '</div>' +
          '<div class="sect-title">记录内容</div>' +
          '<textarea class="ftarea" placeholder="记录沟通情况、学生情绪状态与突出问题…"></textarea>' +
          '<div class="sect-title">后续计划</div>' +
          '<textarea class="ftarea" style="min-height:64px" placeholder="如「建议转介心理中心评估，每周一次沟通」"></textarea>' +
          '<div class="sect-title">回访提醒</div>' +
          '<div class="fgroup">' + frow('回访日期', '2026-10-14', false) + frow('是否同步家长', '否', false) + '</div>' +
          '<div class="sheet-tip">' + icon('info', 14) +
            '<span>提交后写入关怀记录并计入月度关怀工作量；涉及心理风险将提示转介心理中心。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>取消</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="关怀记录已保存（原型演示）">保存记录</button>',
      };
    },

    /* ⑦ 家校：发起沟通弹窗 */
    guardian: function (ctx) {
      const m = window.DB.modules.guardian;
      const c = m.contacts.filter((x) => x.id === ctx)[0] || m.contacts[0];
      return {
        icon: 'heart-handshake', title: '发起沟通', sub: c.student + ' 家长 · ' + c.name,
        body:
          '<div class="detail-block">' +
            '<div class="gd-top">' +
              '<span class="avatar ' + c.tone + '">' + esc(c.name[0]) + '</span>' +
              '<div style="flex:1;min-width:0"><div class="gd-name">' + esc(c.name) + ' ' + tag(c.relation, c.relTone) + '</div>' +
                '<div class="gd-sub">' + esc(c.student) + ' 家长 · ' + esc(c.cls) + ' · ' + esc(c.phone) + '</div></div>' +
            '</div>' +
          '</div>' +
          '<div class="sect-title" style="margin-top:0">沟通渠道</div>' +
          chips('gdChannel', ['电话', '短信', '微信', '面谈']) +
          '<div class="sect-title">话术模板</div>' +
          chips('gdTpl', m.templates) +
          '<div class="sect-title">沟通要点 / 记录</div>' +
          '<textarea class="ftarea" placeholder="记录本次沟通要点，便于后续留痕…">就学生近期缺勤情况与家长沟通，家长承诺督促按时返校。</textarea>' +
          '<div class="sect-title">沟通结果</div>' +
          '<div class="fgroup">' + frow('家长反馈', '待反馈', false) + frow('是否留痕台账', '是', false) + frow('下次跟进', '2026-10-14', false) + '</div>' +
          '<div class="sheet-tip">' + icon('info', 14) +
            '<span>通话 / 短信记录将自动生成沟通台账，可作为家访工作凭证导出。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>取消</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="沟通已记录并留痕（原型演示）">保存并留痕</button>',
      };
    },

    /* ⑧ 任务：新建任务弹窗 */
    tasks: function (ctx) {
      return {
        icon: 'list-checks', title: '新建任务', sub: '待办、逾期与日程统一入口',
        body:
          '<div class="sect-title" style="margin-top:0">任务标题</div>' +
          '<textarea class="ftarea" style="min-height:52px" placeholder="如「审批陈思远事假申请」"></textarea>' +
          '<div class="sect-title">优先级</div>' +
          chips('tkPri', ['高', '中', '低']) +
          '<div class="sect-title">截止时间</div>' +
          '<div class="fgroup">' + frow('截止', '今天 17:00', false, true) + frow('提醒', '提前 30 分钟', false) + '</div>' +
          '<div class="sect-title">关联模块</div>' +
          chips('tkFrom', ['审批', '预警', '关怀', '公告', '问卷', '日常']) +
          '<div class="sect-title">备注</div>' +
          '<textarea class="ftarea" style="min-height:64px" placeholder="补充说明…"></textarea>' +
          '<div class="sheet-tip">' + icon('info', 14) +
            '<span>任务完成后自动归档；逾期任务将在首页「今日重点」与工作通知中提醒。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>取消</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="任务已创建（原型演示）">创建任务</button>',
      };
    },

    /* ⑨ AI：生成洞察周报弹窗 */
    ai: function (ctx) {
      const m = window.DB.modules.ai;
      const it = m.insights.filter((x) => x.id === ctx)[0];
      if (it) {
        return {
          icon: it.icon, title: it.title, sub: 'AI 主动建议 · 置信度 ' + it.confidence + '%',
          body:
            '<div class="sheet-tip ' + (it.tone === 'danger' ? 'danger' : it.tone === 'warn' ? 'warn' : '') + '">' + icon('brain', 14) +
              '<span>' + esc(it.desc) + '</span></div>' +
            '<div class="sect-title">依据信号</div>' +
            '<div class="detail-block" style="margin-bottom:0">' +
              '<div class="kv" style="margin-top:0">' +
                '<span class="kv-k">数据来源</span><span class="kv-v">出勤 / 测评 / 教务 / 反馈</span>' +
                '<span class="kv-k">分析窗口</span><span class="kv-v">近 14 天</span>' +
                '<span class="kv-k">置信度</span><span class="kv-v">' + it.confidence + '%</span>' +
                '<span class="kv-k">建议动作</span><span class="kv-v">' + esc(it.action) + '</span>' +
              '</div>' +
            '</div>' +
            '<div class="sect-title">推荐处置</div>' +
            chips('aiAct', ['立即发起沟通', '记录关怀', '写入成长档案', '仅标记关注']) +
            '<div class="sheet-tip" style="margin-top:12px">' + icon('info', 14) +
              '<span>AI 建议仅供参考，最终处置由教师确认；采纳后会生成对应记录并回写洞察结果。</span></div>',
          foot: '<button class="btn btn-ghost" data-sheet-close>忽略</button>' +
                '<button class="btn btn-primary" data-sheet-submit data-msg="已采纳建议并生成记录（原型演示）">采纳建议</button>',
        };
      }
      return {
        icon: 'wand-sparkles', title: '生成洞察周报', sub: '第 7 教学周 · 全班 47 名学生',
        body:
          '<div class="sect-title" style="margin-top:0">报告范围</div>' +
          chips('aiScope', ['全班 47 人', '重点关注 2 人', '我的班级 3 个']) +
          '<div class="sect-title">时间范围</div>' +
          chips('aiRange', ['近 7 天', '近 14 天', '本月']) +
          '<div class="sect-title">包含内容<span class="spacer">可多选</span></div>' +
          chipsMulti('aiInc', ['出勤分析', '心理关注', '学业预警', '正向激励', '家校沟通建议']) +
          '<div class="sect-title">报告预览</div>' +
          '<div class="report" style="margin:0">' +
            m.report.points.map((p) => '<div class="report-point">' + esc(p) + '</div>').join('') +
          '</div>' +
          '<div class="sheet-tip" style="margin-top:12px">' + icon('info', 14) +
            '<span>周报可导出 PDF 或推送至工作通知；数据统计口径与学工系统一致。</span></div>',
        foot: '<button class="btn btn-ghost" data-sheet-close>取消</button>' +
              '<button class="btn btn-primary" data-sheet-submit data-msg="洞察周报已生成（原型演示）">生成周报</button>',
      };
    },
  };

  function renderSheet() {
    const s = state.sheet;
    if (!s) return '';
    const def = SHEETS[s.key];
    if (!def) return '';
    const info = def(s.ctx);
    const a = accentOf(s.key);
    return '<div class="sheet-mask" data-sheet-close></div>' +
      '<div class="sheet" style="--mod-color:' + a.c + ';--mod-soft:' + a.s + '">' +
        '<div class="sheet-grab"></div>' +
        '<div class="sheet-head">' +
          '<span class="sheet-head-ic" style="background:' + a.s + ';color:' + a.c + '">' + icon(info.icon || 'square-pen', 18) + '</span>' +
          '<div class="sheet-title">' + esc(info.title) + (info.sub ? '<small>' + esc(info.sub) + '</small>' : '') + '</div>' +
          '<button class="sheet-close" data-sheet-close>' + icon('x', 18) + '</button>' +
        '</div>' +
        '<div class="sheet-body">' + info.body + '</div>' +
        '<div class="sheet-foot">' + info.foot + '</div>' +
      '</div>';
  }

  /* ---------------- 二级页渲染分发 ---------------- */
  function renderLayer(layer) {
    switch (layer.type) {
      case 'chat': return renderChat();
      case 'group': return renderGroupSettings();
      case 'contact': return renderContact();
      case 'people': return renderPeople();
      case 'student': return renderStudentDetail();
      case 'studenthome': return renderStudentHome();
      case 'sub': return renderSubPage();
      default: return '';
    }
  }
  function renderLayers() {
    const box = $('#layers');
    const drawer = (state.tab === 'messages' && state.mcDrawer && !state.layers.length) ? renderMcDrawer() : '';
    if (!state.layers.length && !drawer) { box.innerHTML = ''; box.style.pointerEvents = 'none'; return; }
    box.style.pointerEvents = 'auto';
    let html = '';
    if (state.layers.length) {
      const top = state.layers[state.layers.length - 1];
      html = '<div class="layer">' + renderLayer(top) + renderSheet() + '</div>';
    }
    box.innerHTML = html;
    if (drawer) box.insertAdjacentHTML('beforeend', drawer);
  }

  /* ---------------- 主渲染 ---------------- */
  function render() {
    $$('.screen').forEach((s) => s.classList.toggle('active', s.dataset.screen === state.tab));
    if (state.tab === 'home') $('#screen-home').innerHTML = renderHome();
    else if (state.tab === 'messages') $('#screen-messages').innerHTML = renderMessages();
    else if (state.tab === 'students') $('#screen-students').innerHTML = renderStudents();
    else if (state.tab === 'agent') $('#screen-agent').innerHTML = renderPlaceholder('agent');
    else if (state.tab === 'profile') $('#screen-profile').innerHTML = renderProfile();
    $$('.tab-item').forEach((b) => b.classList.toggle('active', b.dataset.tab === state.tab));
    if (state.tab !== 'messages') state.mcDrawer = false;
    $('#tabbar').style.display = (state.layers.length || state.mcDrawer) ? 'none' : '';
    renderLayers();
    const sc = $('#chatScroll'); if (sc) sc.scrollTop = sc.scrollHeight;
    const f = $('#chatField');
    if (f) { f.addEventListener('input', onChatInput); f.addEventListener('keydown', onChatKey); }
  }

  function renderProfile() {
    const me = window.DB.me;
    return '' +
      '<header class="appbar appbar-brand">' +
        '<span class="mascot mascot-sm"><img src="assets/mascot.png" alt="绵小城"></span>' +
        '<div class="appbar-title">个人中心<small>' + esc(me.college) + '</small></div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="hero-card">' +
          '<span class="avatar lg tone-blue">' + esc(me.name[0]) + '</span>' +
          '<div><div class="hero-card-name">' + esc(me.name) + '</div>' +
            '<div class="hero-card-meta">' + esc(me.title) + ' · ' + esc(me.college) + '</div></div>' +
        '</div>' +
        '<div class="list" style="margin-top:12px">' +
          '<button class="row" data-action="toast" data-msg="个人资料（原型演示）">' + tile('brand', 'user') + '<span class="row-main"><span class="row-label">个人资料</span></span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="修改密码（原型演示）">' + tile('warn', 'shield-alert') + '<span class="row-main"><span class="row-label">账号与安全</span></span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="通知设置（原型演示）">' + tile('violet', 'bell') + '<span class="row-main"><span class="row-label">通知设置</span></span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
          '<button class="row" data-action="toast" data-msg="关于绵小城（原型演示）">' + tile('cyan', 'sparkles') + '<span class="row-main"><span class="row-label">关于绵小城</span></span>' + icon('chevron-right', 16, 'row-arrow') + '</button>' +
        '</div>' +
        '<div class="legacy-note">个人中心为占位页，本次改版未涉及，保持现有设计。</div>' +
      '</div>';
  }

  /* ---------------- 交互：聊天输入 ---------------- */
  function onChatInput(e) { state.chatInput = e.target.value; syncSendBtn(); }
  function onChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
  }
  function syncSendBtn() {
    const b = $('[data-send]'); if (!b) return;
    const on = state.chatInput.trim().length > 0;
    b.classList.toggle('on', on);
    b.disabled = !on;
  }
  async function doSend() {
    const text = state.chatInput.trim();
    if (!text) return;
    const convId = state.activeConv;
    const res = await window.API.sendMessage(convId, text);
    const list = window.DB.messages[convId] || (window.DB.messages[convId] = []);
    list.push({ id: res.id, mine: true, text: text, time: res.time, kind: 'text' });
    state.chatInput = '';
    render();
    toast('已发送');
  }

  /* ---------------- 事件委托 ---------------- */
  document.addEventListener('click', async function (e) {
    const t = e.target;
    const closest = (sel) => (t.closest ? t.closest(sel) : null);

    // 底部页签
    const tabBtn = closest('[data-tab]');
    if (tabBtn) { state.tab = tabBtn.dataset.tab; state.layers = []; state.sheet = null; render(); return; }

    // 弹窗：关闭 / 提交
    if (closest('[data-sheet-close]')) { state.sheet = null; render(); return; }
    const submit = closest('[data-sheet-submit]');
    if (submit) { toast(submit.dataset.msg || '已提交（原型演示）'); state.sheet = null; render(); return; }

    // 弹窗内 chips 单选
    const chip = closest('[data-chip]');
    if (chip) {
      const g = chip.dataset.chip, v = chip.dataset.val;
      state.chip[g] = state.chip[g] === v ? null : v;
      render(); return;
    }
    // 弹窗内多选行
    const multi = closest('[data-multi]');
    if (multi) {
      const g = multi.dataset.multi, v = multi.dataset.val;
      state.multi[g + ':' + v] = !state.multi[g + ':' + v];
      render(); return;
    }

    // AI 建议：一键行动（须先于 data-sheet，因建议卡本身也带 data-sheet）
    const aiAct = closest('[data-ai-action]');
    if (aiAct) {
      const kind = aiAct.dataset.aiAction;
      if (kind === 'chat') { toast('已打开与 ' + aiAct.dataset.ref + ' 的会话（原型演示）'); return; }
      state.sheet = { key: 'ai', ctx: null }; render(); return;
    }

    // 打开弹窗
    const sheetBtn = closest('[data-sheet]');
    if (sheetBtn) { state.sheet = { key: sheetBtn.dataset.sheet, ctx: sheetBtn.dataset.ctx || null }; render(); return; }

    // 返回（先关弹窗再返回上一级）
    if (closest('[data-back]')) { state.sheet = null; state.layers.pop(); render(); return; }

    // 消息中心侧边抽屉
    if (closest('[data-action="mc-drawer-open"]')) { state.mcDrawer = true; render(); return; }
    if (closest('[data-action="mc-drawer-close"]')) { state.mcDrawer = false; render(); return; }

    // 消息中心视图切换
    const mc = closest('[data-mc]');
    if (mc) { state.mc = mc.dataset.mc; state.mcDrawer = false; render(); return; }

    // 模块内分段
    const seg = closest('[data-mod-seg]');
    if (seg) { state.seg[seg.dataset.modSeg] = parseInt(seg.dataset.idx, 10); render(); return; }

    // 成长档案：选择学生
    const pick = closest('[data-pick-student]');
    if (pick) { state.pick.portfolio = pick.dataset.pickStudent; render(); return; }

    // v3：学生详情 / 学生主页
    const stu = closest('[data-open-student]');
    if (stu) {
      state.activeStudent = stu.dataset.openStudent;
      state.stuTab = 'overview'; state.sheet = null;
      state.layers.push({ type: 'student' }); render(); return;
    }
    const stuTab = closest('[data-stu-tab]');
    if (stuTab) { state.stuTab = stuTab.dataset.stuTab; render(); return; }
    const stuHome = closest('[data-open-student-home]');
    if (stuHome) {
      if (stuHome.dataset.openStudentHome) state.activeStudent = stuHome.dataset.openStudentHome;
      state.sheet = null;
      state.layers.push({ type: 'studenthome' }); render(); return;
    }
    // v3：QQ 风格主页点赞
    const qlike = closest('[data-qq-like]');
    if (qlike) {
      const k = qlike.dataset.qqLike;
      state.stuLike[k] = !state.stuLike[k];
      render();
      toast(state.stuLike[k] ? '已点赞，学生端会收到提醒' : '已取消点赞');
      return;
    }
    // v3：AI 辅助审批 · 采纳建议
    const adopt = closest('[data-ai-adopt]');
    if (adopt) {
      state.chip.apResult = adopt.dataset.aiAdopt;
      render();
      toast('已采纳 AI 建议：' + adopt.dataset.aiAdopt + '，意见已填充');
      return;
    }

    // 任务勾选
    const task = closest('[data-task-toggle]');
    if (task) {
      const id = task.dataset.taskToggle;
      const m = window.DB.modules.tasks;
      let base = false;
      m.groups.forEach((g) => g.items.forEach((it) => { if (it.id === id) base = it.done; }));
      state.tasksDone[id] = state.tasksDone[id] != null ? !state.tasksDone[id] : !base;
      render();
      toast(state.tasksDone[id] ? '任务已完成' : '已恢复为待办');
      return;
    }

    // 首页宫格 / 功能子页面
    const sub = closest('[data-open-sub]');
    if (sub) {
      state.subId = sub.dataset.openSub;
      state.seg[state.subId] = state.seg[state.subId] || 0;
      state.sheet = null;
      state.layers.push({ type: 'sub' }); render(); return;
    }

    // 会话置顶
    const pin = closest('[data-action="pin"]');
    if (pin) {
      const id = pin.dataset.id;
      const c = findConv(id);
      state.pinned[id] = !(c.pinned || state.pinned[id]);
      state.swiped = null;
      render();
      toast(state.pinned[id] ? '已置顶' : '已取消置顶');
      return;
    }
    const mute = closest('[data-action="mute"]');
    if (mute) { state.swiped = null; render(); toast('已开启免打扰'); return; }

    // 打开会话
    const convBody = closest('[data-open-conv]');
    if (convBody) {
      const id = convBody.dataset.openConv;
      if (state.swiped === id) { state.swiped = null; render(); return; }
      state.activeConv = id; state.chatInput = ''; state.attachOpen = false;
      state.layers.push({ type: 'chat' }); render(); return;
    }
    const convLi = closest('[data-conv]');
    if (convLi && !convBody) { state.swiped = state.swiped === convLi.dataset.conv ? null : convLi.dataset.conv; render(); return; }

    // 群设置
    if (closest('[data-open-group-settings]')) { state.layers.push({ type: 'group' }); render(); return; }

    // 附件面板
    if (closest('[data-attach-toggle]')) { state.attachOpen = !state.attachOpen; render(); return; }
    if (closest('[data-send]')) { doSend(); return; }

    // 成员 / 人员
    const person = closest('[data-open-contact]');
    if (person) { state.activeContact = person.dataset.openContact; state.layers.push({ type: 'contact' }); render(); return; }
    const people = closest('[data-action="people"]');
    if (people) { state.peopleKind = people.dataset.kind; state.layers.push({ type: 'people' }); render(); return; }
    const chatWith = closest('[data-action="chat-with"]');
    if (chatWith) {
      const id = chatWith.dataset.id;
      let conv = CONVS.filter((c) => c.id === 's-' + id.slice(1))[0] || CONVS.filter((c) => c.name === (findPerson(id) || {}).name)[0];
      if (!conv) { conv = { id: 'tmp-' + id, type: 'single', name: (findPerson(id) || {}).name || '会话', avatarTone: 'tone-slate' }; CONVS.push(conv); window.DB.messages[conv.id] = window.DB.messages['default']; }
      state.activeConv = conv.id; state.chatInput = '';
      state.layers = [{ type: 'chat' }]; render(); return;
    }

    // 组织树展开
    const org = closest('[data-org-toggle]');
    if (org) { const id = org.dataset.orgToggle; state.orgOpen[id] = !state.orgOpen[id]; render(); return; }

    // 通知
    const noti = closest('[data-noti]');
    if (noti) {
      const n = window.DB.notifications.filter((x) => x.id === noti.dataset.noti)[0];
      if (n) { n.read = true; }
      if (n && n.link) { state.subId = n.link; state.seg[n.link] = 0; state.layers.push({ type: 'sub' }); }
      render();
      return;
    }

    // 工作通知快捷
    if (closest('[data-action="go-messages-noti"]')) { state.mc = 'noti'; render(); return; }
    if (closest('[data-action="go-messages"]')) { state.tab = 'messages'; state.mc = 'msg'; render(); return; }
    if (closest('[data-action="plus-menu"]')) { toast('发起群聊 / 添加好友 / 扫一扫'); return; }

    // 通用 toast
    const tst = closest('[data-action="toast"]');
    if (tst) { toast(tst.dataset.msg || '原型演示'); return; }
  });

  /* ---------------- 启动 ---------------- */
  (async function init() {
    CONVS = await window.API.getConversations();
    await Promise.all([window.API.getOrgTree(), window.API.getMyStudents(), window.API.getColleagues(), window.API.getNotifications(), window.API.getQuickEntries()]);
    render();
  })();
})();