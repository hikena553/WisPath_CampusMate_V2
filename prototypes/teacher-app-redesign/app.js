/* =========================================================================
   app.js · 原型交互层（状态 / 渲染 / 事件委托）
   静态外壳在 index.html 内联；本文件只负责填充内容与切换，不重写导航骨架。
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

  /* 语义色 → soft 底 + 深色字 的图标块 */
  const TONE = {
    brand:  { bg: 'var(--tui-brand-soft)',  fg: 'var(--tui-brand-strong)' },
    success:{ bg: 'var(--tui-success-soft)',fg: 'var(--tui-success)' },
    warn:   { bg: 'var(--tui-warn-soft)',   fg: 'var(--tui-warn)' },
    danger: { bg: 'var(--tui-danger-soft)', fg: 'var(--tui-danger)' },
    violet: { bg: 'var(--tui-violet-soft)', fg: 'var(--tui-violet)' },
    cyan:   { bg: 'var(--tui-cyan-soft)',   fg: 'var(--tui-cyan)' },
    quiet:  { bg: 'var(--tui-surface-sunken)', fg: 'var(--tui-text-tertiary)' },
  };
  const tagCls = { brand: 'tag-brand', success: 'tag-success', warn: 'tag-warn', danger: 'tag-danger', violet: 'tag-violet', cyan: 'tag-cyan', quiet: '' };

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

  /* ---------------- 状态 ---------------- */
  const state = {
    tab: 'home',
    mc: 'msg',            // msg | contacts | noti
    mcDrawer: false,       // 消息中心侧边抽屉（通讯录 / 通知 收在其中）
    swiped: null,          // 被滑出操作位的会话 key
    orgOpen: {},           // 组织树展开态
    pinned: {},            // 会话置顶态（本地交互演示）
    layers: [],            // 二级页栈
    chatInput: '',
    attachOpen: false,
    toast: null,
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

  /* ---------------- 首页 ---------------- */
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
            '<span class="card-head-icon" style="background:var(--tui-brand-soft);color:var(--tui-brand-strong)">' + icon('grid', 14) + '</span>' +
            '常用功能' +
            '<span class="spacer" style="margin-left:auto;display:flex"><button class="link-more" data-open-sub="features">全部功能' + icon('chevron-right', 13) + '</button></span>' +
          '</div>' +
          '<div class="nav-grid">' + grid + '</div>' +
        '</div>' +

        '<div class="group-title">我的节奏<span class="spacer">本周安排与工作沉淀</span></div>' +
        '<div class="pace-grid">' +
          '<div class="pace">' +
            '<div class="pace-head">' + icon('calendar', 15) + '本周计划</div>' +
            '<div class="pace-num">5</div><div class="pace-sub">3 项已完成 · 2 项待办</div>' +
          '</div>' +
          '<div class="pace">' +
            '<div class="pace-head">' + icon('bar-chart-3', 15) + '工作量</div>' +
            '<div class="pace-num">12</div><div class="pace-sub">本周谈话 / 家访记录</div>' +
          '</div>' +
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

  /* ---------------- 消息中心 ---------------- */
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
        '<span class="org-ic" style="background:' + t.bg + ';color:' + t.fg + '">' + icon('building-2', 17) + '</span>' +
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
      '<div class="legacy-note">通知来源于后端 Notification 模型（type：SYSTEM / APPROVAL / LEAVE / CRISIS / ANNOUNCEMENT / FEEDBACK），与公告、审批、预警模块打通，点击可直接跳转到对应子页面。</div>';
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
          '<button class="icon-btn" data-action="mc-drawer-open" aria-label="打开侧边导航">' + icon('more-horizontal', 20) + '</button>' +
          '<span class="mc-title">' + titles[state.mc] + '</span>' +
          '<span class="spacer"></span>' +
          '<button class="icon-btn" data-action="toast" data-msg="搜索会话 / 联系人">' + icon('search', 20) + '</button>' +
          '<button class="icon-btn" data-action="plus-menu">' + icon('plus', 20) + '</button>' +
        '</div>' +
      '</header>' +
      '<div class="content">' + body + '</div>';
  }

  /* 消息中心侧边抽屉：通讯录 / 通知 收在其中，消息保持默认主视图 */
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

  /* ---------------- 二级页：聊天 ---------------- */
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
          [['image', '图片'], ['camera', '拍摄'], ['file-text', '文件'], ['mic', '语音'], ['folder', '群文件'], ['award', '成长记录'], ['clipboard-check', '审批单'], ['location', '位置']]
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

  /* ---------------- 二级页：群设置 ---------------- */
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
        '<div class="appbar-actions"><button class="icon-btn" data-action="toast" data-msg="群管理（原型演示）">' + icon('more-horizontal', 19) + '</button></div>' +
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

  /* ---------------- 二级页：成员详情 ---------------- */
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
        (p.risk ? '<div class="notice notice-danger" style="margin-top:12px">' + icon('alert-triangle', 15) +
          '<span>该生处于「重点关注」状态：近 7 天出勤下降，心理测评异常，建议尽快跟进。</span></div>' : '') +
        '<div class="item-ops" style="border-top:none;margin-top:14px">' +
          '<button class="btn btn-ghost" data-action="toast" data-msg="已跳转学生成长档案（原型演示）">' + icon('award', 16) + '成长档案</button>' +
          '<button class="btn btn-primary" data-action="chat-with" data-id="' + p.id + '">' + icon('message-circle', 16) + '发消息</button>' +
        '</div>' +
      '</div>';
  }

  /* ---------------- 二级页：人员列表 ---------------- */
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

  /* ---------------- 二级页：全部功能总览 ---------------- */
  function renderFeatures() {
    const groups = window.DB.featureGroups || [];
    const body = groups.map((g) => {
      const rows = g.items.map((it) => {
        const has = !!window.DB.subPages[it.id];
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
        '<div class="legacy-note">底部页签已承载 首页 / 学生 / 绵小城 / 消息 / 个人中心，本页只列其余模块，保证同一功能不重复出现；审批与预警的行尾角标来自实时统计。</div>' +
      '</div>';
  }

  /* ---------------- 二级页：统一子页面模板 ---------------- */
  function renderSubPage() {
    if (state.subId === 'features') return renderFeatures();
    const sp = window.DB.subPages[state.subId] || { title: '功能', sub: '', items: [], stats: [], segments: [] };
    if (!sp) return '';
    const t = TONE[sp.accent] || TONE.brand;
    const stats = sp.stats.map((s) => {
      const st = TONE[s.tone] || TONE.brand;
      return '<div class="stat"><div class="stat-num" style="color:' + (s.tone === 'quiet' ? 'var(--tui-text)' : st.fg) + '">' + s.num + '</div>' +
        '<div class="stat-label">' + esc(s.label) + '</div></div>';
    }).join('');
    const seg = sp.segments.map((s, i) =>
      '<button class="seg-item' + (i === 0 ? ' active' : '') + '" data-sub-seg>' + esc(s) + '</button>').join('');
    const items = sp.items.map((it) => {
      const ops = it.actions
        ? '<div class="item-ops">' +
            '<button class="btn btn-ghost btn-sm" data-action="toast" data-msg="' + esc(it.actions[0]) + '：' + esc(it.title) + '">' + esc(it.actions[0]) + '</button>' +
            '<button class="btn btn-primary btn-sm" data-action="toast" data-msg="' + esc(it.actions[1]) + '：' + esc(it.title) + '">' + esc(it.actions[1]) + '</button>' +
          '</div>' : '';
      return '<div class="item-card">' +
        '<div class="item-head"><span class="item-title">' + esc(it.title) + '</span>' +
          (it.tag ? '<span style="margin-left:auto">' + tag(it.tag, it.tagTone) + '</span>' : '') + '</div>' +
        '<div class="item-body">' + nl(it.body) + '</div>' +
        '<div class="item-meta">' + icon('clock', 13) + esc(it.meta) + '</div>' + ops +
      '</div>';
    }).join('');
    return '' +
      '<header class="appbar">' +
        '<button class="appbar-back" data-back>' + icon('arrow-left', 20) + '</button>' +
        '<div class="appbar-title">' + esc(sp.title) + '<small>' + esc(sp.sub) + '</small></div>' +
        '<div class="appbar-actions"><button class="icon-btn" data-action="toast" data-msg="更多操作（原型演示）">' + icon('more-horizontal', 19) + '</button></div>' +
      '</header>' +
      '<div class="content">' +
        '<div class="stat-row">' + stats + '</div>' +
        '<div class="seg" style="margin-bottom:12px">' + seg + '</div>' +
        '<div class="stack">' + items + '</div>' +
        '<div class="legacy-note">本页已按全局设计规范统一：吸顶 AppBar（吉祥物/返回）+ 语义化指标卡 + 分段筛选 + 白卡列表；' +
          '配色仅取自 --tui-brand / --tui-warn / --tui-danger / --tui-success 等令牌，' +
          '不再使用 #409eff、#f56c6c 等 Element Plus 默认散色。</div>' +
      '</div>';
  }

  /* ---------------- 二级页渲染分发 ---------------- */
  function renderLayer(layer) {
    switch (layer.type) {
      case 'chat': return renderChat();
      case 'group': return renderGroupSettings();
      case 'contact': return renderContact();
      case 'people': return renderPeople();
      case 'sub': return renderSubPage();
      default: return '';
    }
  }
  function renderLayers() {
    const box = $('#layers');
    const drawer = (state.tab === 'messages' && state.mcDrawer && !state.layers.length) ? renderMcDrawer() : '';
    if (!state.layers.length && !drawer) { box.innerHTML = ''; box.style.pointerEvents = 'none'; return; }
    box.style.pointerEvents = 'auto';
    if (state.layers.length) {
      const top = state.layers[state.layers.length - 1];
      box.innerHTML = '<div class="layer">' + renderLayer(top) + '</div>';
    } else {
      box.innerHTML = '';
    }
    if (drawer) box.insertAdjacentHTML('beforeend', drawer);
  }

  /* ---------------- 主渲染 ---------------- */
  function render() {
    $$('.screen').forEach((s) => s.classList.toggle('active', s.dataset.screen === state.tab));
    if (state.tab === 'home') $('#screen-home').innerHTML = renderHome();
    else if (state.tab === 'messages') $('#screen-messages').innerHTML = renderMessages();
    else if (state.tab === 'students') $('#screen-students').innerHTML = renderPlaceholder('students');
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
    if (tabBtn) { state.tab = tabBtn.dataset.tab; state.layers = []; render(); return; }

    // 返回
    if (closest('[data-back]')) { state.layers.pop(); render(); return; }

    // 消息中心侧边抽屉：打开 / 收起
    if (closest('[data-action="mc-drawer-open"]')) { state.mcDrawer = true; render(); return; }
    if (closest('[data-action="mc-drawer-close"]')) { state.mcDrawer = false; render(); return; }

    // 消息中心视图切换（消息 / 通讯录 / 通知），选中后自动收起抽屉
    const mc = closest('[data-mc]');
    if (mc) { state.mc = mc.dataset.mc; state.mcDrawer = false; render(); return; }
    const subSeg = closest('[data-sub-seg]');
    if (subSeg) {
      const wrap = subSeg.parentNode;
      $$('.seg-item', wrap).forEach((b) => b.classList.remove('active'));
      subSeg.classList.add('active');
      toast('已切换筛选：' + subSeg.textContent.trim());
      return;
    }

    // 首页宫格 / 子页面
    const sub = closest('[data-open-sub]');
    if (sub) { state.subId = sub.dataset.openSub; state.layers.push({ type: 'sub' }); render(); return; }

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

    // 打开会话（若已滑出操作位则先收起）
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
      if (n && n.link) { state.subId = n.link; state.layers.push({ type: 'sub' }); }
      render();
      return;
    }

    // 工作通知快捷 → 通知 Tab
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