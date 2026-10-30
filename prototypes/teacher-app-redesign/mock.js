/* =========================================================================
   mock.js · 唯一数据源（plain global，无 ES module，保证 file:// 双击可开）
   数据取自真实业务语境：绵阳城市学院 · 信息工程学院 · 辅导员视角
   ------------------------------------------------------------------
   DB.modules.<key> 为「常用功能」九个功能的子页面 + 弹窗数据（本轮重构重点）。
   ========================================================================= */
window.DB = {
  me: { id: 't1', name: '李静', role: 'teacher', college: '信息工程学院', title: '辅导员' },

  /* ---------------- 会话（消息 Tab） ---------------- */
  conversations: [
    { id: 'n-work', type: 'notice', name: '工作通知', avatarText: '通', avatarTone: 'tone-blue',
      lastMessage: '【审批】3 条请假申请待你处理', time: '09:24', unread: 3, pinned: true, isWorkNotice: true },
    { id: 'g-1', type: 'group', name: '计科2301 班级群', avatarText: '群', avatarTone: 'tone-violet',
      lastMessage: '王浩：老师，周一的班会改到几点？', time: '09:12', unread: 6, pinned: true, memberCount: 42, roleTag: '群主' },
    { id: 's-1', type: 'single', name: '陈思远', avatarText: '陈', avatarTone: 'tone-orange',
      lastMessage: '老师，我这两天有点焦虑，想找您聊聊', time: '08:47', unread: 2, pinned: false, roleTag: '我的学生' },
    { id: 's-2', type: 'single', name: '赵敏', avatarText: '赵', avatarTone: 'tone-green',
      lastMessage: '收到，谢谢老师！', time: '昨天', unread: 0, pinned: false, roleTag: '我的学生' },
    { id: 'g-2', type: 'group', name: '信息工程学院辅导员工作群', avatarText: '群', avatarTone: 'tone-cyan',
      lastMessage: '张书记：本周五下午 15:00 学工例会，请准时参加', time: '昨天', unread: 1, pinned: false, memberCount: 28 },
    { id: 's-3', type: 'single', name: '刘洋', avatarText: '刘', avatarTone: 'tone-blue',
      lastMessage: '好的，材料我明天交到办公室', time: '昨天', unread: 0, pinned: false, roleTag: '我的学生' },
    { id: 's-4', type: 'single', name: '周老师', avatarText: '周', avatarTone: 'tone-slate',
      lastMessage: '李老师，麻烦看下这个学生的心理测评结果', time: '周三', unread: 0, pinned: false, roleTag: '同事' },
    { id: 'g-3', type: 'group', name: '2024 级迎新工作组', avatarText: '群', avatarTone: 'tone-red',
      lastMessage: '迎新志愿者名单已更新，请核对', time: '周二', unread: 0, pinned: false, memberCount: 16 },
    { id: 's-5', type: 'single', name: '孙倩', avatarText: '孙', avatarTone: 'tone-violet',
      lastMessage: '老师，助学金申请需要哪些材料呀？', time: '周一', unread: 0, pinned: false, roleTag: '我的学生' },
  ],

  /* ---------------- 聊天记录 ---------------- */
  messages: {
    's-1': [
      { id: 'm1', mine: false, senderName: '陈思远', text: '老师您好，最近课业压力有点大', time: '08:40', kind: 'text' },
      { id: 'm2', mine: false, senderName: '陈思远', text: '晚上也睡不好，白天没精神', time: '08:41', kind: 'text' },
      { id: 'm3', mine: true, text: '我看到了，先别着急，我们约个时间当面聊聊', time: '08:44', kind: 'text' },
      { id: 'm4', mine: true, text: '这是学校心理中心的预约方式，你也可以先了解一下', time: '08:45', kind: 'text' },
      { id: 'm5', mine: true, text: '心理中心预约指南.pdf', time: '08:45', kind: 'file', fileName: '心理中心预约指南.pdf', fileMeta: 'PDF · 1.2 MB' },
      { id: 'm6', mine: false, senderName: '陈思远', text: '好的老师，谢谢您，我下午 4 点去找您', time: '08:47', kind: 'text' },
    ],
    'g-1': [
      { id: 'g1', mine: false, senderName: '王浩', text: '老师，周一的班会改到几点？', time: '09:10', kind: 'text' },
      { id: 'g2', mine: true, text: '周一班会调整到 16:00，地点还是 3 号教学楼 201', time: '09:11', kind: 'text' },
      { id: 'g3', mine: false, senderName: '李梦琪', text: '收到～', time: '09:12', kind: 'text' },
    ],
    'n-work': [
      { id: 'w1', mine: false, senderName: '工作通知', text: '【审批】陈思远提交了请假申请（事假 3 天），待你处理', time: '09:24', kind: 'text' },
      { id: 'w2', mine: false, senderName: '工作通知', text: '【预警】系统检测到 2 名学生心理测评结果异常，建议关注', time: '08:30', kind: 'text' },
    ],
    'default': [
      { id: 'd1', mine: false, senderName: '', text: '在的，你说', time: '10:02', kind: 'text' },
      { id: 'd2', mine: true, text: '好的，收到', time: '10:03', kind: 'text' },
    ],
  },

  /* ---------------- 通讯录 · 组织架构 ---------------- */
  org: [
    { id: 'c1', name: '信息工程学院', tone: 'tone-blue',
      majors: [
        { id: 'mo1', name: '计算机科学与技术', classes: [
          { id: 'k1', name: '计科 2301', count: 42, students: [
            { id: 'u1', name: '陈思远', username: '20230101', tone: 'tone-orange', risk: true },
            { id: 'u2', name: '王浩', username: '20230102', tone: 'tone-blue' },
            { id: 'u3', name: '李梦琪', username: '20230103', tone: 'tone-green' },
            { id: 'u4', name: '刘洋', username: '20230104', tone: 'tone-violet' },
          ] },
          { id: 'k2', name: '计科 2302', count: 40, students: [
            { id: 'u5', name: '赵敏', username: '20230201', tone: 'tone-cyan' },
            { id: 'u6', name: '孙倩', username: '20230202', tone: 'tone-red' },
          ] },
        ] },
        { id: 'mo2', name: '软件工程', classes: [
          { id: 'k3', name: '软工 2301', count: 38, students: [
            { id: 'u7', name: '周航', username: '20230301', tone: 'tone-slate' },
          ] },
        ] },
      ] },
    { id: 'c2', name: '经济管理学院', tone: 'tone-cyan',
      majors: [
        { id: 'mo3', name: '工商管理', classes: [
          { id: 'k4', name: '工商 2301', count: 45, students: [
            { id: 'u8', name: '林晓', username: '20230401', tone: 'tone-green' },
          ] },
        ] },
      ] },
  ],

  myStudents: [
    { id: 'u1', name: '陈思远', username: '20230101', className: '计科 2301', tone: 'tone-orange', risk: true },
    { id: 'u2', name: '王浩', username: '20230102', className: '计科 2301', tone: 'tone-blue' },
    { id: 'u3', name: '李梦琪', username: '20230103', className: '计科 2301', tone: 'tone-green' },
    { id: 'u4', name: '刘洋', username: '20230104', className: '计科 2301', tone: 'tone-violet' },
    { id: 'u5', name: '赵敏', username: '20230201', className: '计科 2302', tone: 'tone-cyan' },
    { id: 'u6', name: '孙倩', username: '20230202', className: '计科 2302', tone: 'tone-red', risk: true },
    { id: 'u7', name: '周航', username: '20230301', className: '软工 2301', tone: 'tone-slate' },
  ],

  colleagues: [
    { id: 't2', name: '张建国', username: 'T2018', title: '学院党委书记', department: '信息工程学院', tone: 'tone-slate' },
    { id: 't3', name: '周敏', username: 'T2021', title: '心理健康教师', department: '学生工作处', tone: 'tone-violet' },
    { id: 't4', name: '王立', username: 'T2019', title: '辅导员', department: '经济管理学院', tone: 'tone-cyan' },
    { id: 't5', name: '刘芳', username: 'T2022', title: '教务秘书', department: '信息工程学院', tone: 'tone-green' },
  ],

  /* ---------------- 通知（通知 Tab） ---------------- */
  notifications: [
    { id: 'no1', type: '审批', title: '请假申请待审批', content: '陈思远提交事假申请（3 天），请及时处理。', time: '今天 09:24', read: false, tone: 'warn', link: 'approval' },
    { id: 'no2', type: '预警', title: '心理测评异常提醒', content: '2 名学生测评结果异常，建议 24 小时内跟进。', time: '今天 08:30', read: false, tone: 'danger', link: 'crisis' },
    { id: 'no3', type: '公告', title: '班会时间调整通知已发布', content: '计科 2301 班会调整至周一 16:00，已推送至学生端。', time: '昨天 17:10', read: true, tone: 'brand', link: 'announcement' },
    { id: 'no4', type: '反馈', title: '学生反馈已收到', content: '孙倩提交了「助学金材料」相关咨询，请回复。', time: '昨天 14:02', read: true, tone: 'cyan' },
    { id: 'no5', type: '系统', title: '账号安全提示', content: '检测到你的账号在新设备登录，如非本人操作请及时改密。', time: '周三 20:15', read: true, tone: 'quiet' },
  ],

  /* ---------------- 首页 · 常用功能宫格（原「更多」模块迁入） ---------------- */
  quickEntries: [
    { id: 'approval', label: '审批', desc: '请假、证明等事项受理与审批', icon: 'clipboard-check', tone: 'warn', badge: 3, badgeWarn: true },
    { id: 'crisis', label: '预警', desc: '学生风险与危机事件跟进', icon: 'shield-alert', tone: 'danger', badge: 2 },
    { id: 'announcement', label: '公告', desc: '面向班级发布通知与公告', icon: 'megaphone', tone: 'brand' },
    { id: 'portfolio', label: '成长档案', desc: '学生成长记录与作品集管理', icon: 'award', tone: 'violet' },
    { id: 'survey', label: '问卷互评', desc: '匿名问卷发放与学生互评', icon: 'clipboard-list', tone: 'cyan' },
    { id: 'care', label: '关怀中心', desc: '谈心记录与心理关怀跟进', icon: 'heart-pulse', tone: 'warn' },
    { id: 'guardian', label: '家校沟通', desc: '家长联系人沟通与记录留痕', icon: 'heart-handshake', tone: 'cyan' },
  ],

  /* 全部功能总览：底部页签之外的模块入口（原「更多」的功能全集） */
  featureGroups: [
    { title: '学生事务', items: [
      { id: 'approval', label: '审批', desc: '请假、证明等事项的受理与审批', icon: 'clipboard-check', tone: 'warn', badge: 3, badgeWarn: true },
      { id: 'crisis', label: '预警', desc: '学生风险与危机事件的预警跟进', icon: 'shield-alert', tone: 'danger', badge: 2 },
      { id: 'announcement', label: '公告', desc: '面向班级发布通知与公告', icon: 'megaphone', tone: 'brand' },
    ] },
    { title: '成长与关怀', items: [
      { id: 'portfolio', label: '成长档案', desc: '学生成长记录与作品集管理', icon: 'award', tone: 'violet' },
      { id: 'survey', label: '问卷互评', desc: '匿名问卷发放与学生互评', icon: 'clipboard-list', tone: 'cyan' },
      { id: 'care', label: '关怀中心', desc: '谈心记录与心理关怀跟进', icon: 'heart-pulse', tone: 'warn' },
      { id: 'guardian', label: '家校沟通', desc: '家长联系人沟通与记录留痕', icon: 'heart-handshake', tone: 'cyan' },
    ] },
    { title: '效率工具', items: [
      { id: 'tasks', label: '今日任务', desc: '待办、逾期与日程的统一入口', icon: 'list-checks', tone: 'success' },
      { id: 'ai', label: 'AI 洞察', desc: '主动发现与推荐联系建议', icon: 'sparkles', tone: 'violet' },
    ] },
  ],

  /* ==================================================================
     「常用功能」九个功能：子页面 + 弹窗数据
     每模块结构各不相同 —— 对应九套专属版式（设计契约 §4）
     ================================================================== */
  modules: {

    /* ---------------- ① 审批 ---------------- */
    approval: {
      meta: { title: '审批', sub: '请假、证明等事项的受理与审批', accent: 'warn', icon: 'clipboard-check' },
      fab: null,
      aiFallback: { suggest: '同意', confidence: 95,
        summary: '在读证明为常规事项申请，学生状态正常，无在办预警。',
        checks: [ { k: '材料核验', v: '无需附件，系统信息一致', ok: true } ],
        reason: '常规事项，建议同意并转教务处盖章。', opinion: '情况属实，同意开具，请到教务处盖章。' },
      todo: { count: 3, urgentName: '陈思远', urgentType: '事假 3 天', sla: '剩余 6 小时', note: '今天 17:00 前需完成审批，逾期将自动上报学工处' },
      stats: [ { num: 3, label: '待我审批', tone: 'warn' }, { num: 12, label: '本月已办', tone: 'success' }, { num: 1, label: '已驳回', tone: 'danger' } ],
      segments: ['待审批 3', '已处理 8', '我发起的 2'],
      items: [
        { id: 'ap1', student: '陈思远', stuTone: 'tone-orange', cls: '计科 2301', type: '事假', tag: '待审批', tagTone: 'warn', urgent: true,
          range: '10 月 13 日 — 10 月 15 日', days: '3 天', reason: '家中有事，需返回绵阳处理',
          submitted: '今天 09:24', sla: '剩余 6 小时', files: [ { name: '家长知情书.jpg', size: '860 KB', icon: 'image' } ],
          flow: [ { k: '学生提交申请', t: '今天 09:24', state: 'done' }, { k: '辅导员审批', t: '进行中', state: 'active' }, { k: '学工处备案', t: '待处理', state: 'wait' } ],
          actions: ['驳回', '同意'],
          ai: { suggest: '同意', confidence: 93,
            summary: '事假 3 天，事由明确（家中有事），已附家长知情书；该生本月首次请假，出勤正常，无在办预警。',
            checks: [
              { k: '材料核验', v: '家长知情书已上传，要素齐全', ok: true },
              { k: '时间冲突', v: '请假期间无考试与实操安排', ok: true },
              { k: '历史记录', v: '本学期首次请假，无逾期未销假', ok: true } ],
            reason: '事由合理、材料齐全，建议同意，销假时间 10 月 15 日。',
            opinion: '情况属实，同意事假 3 天（10.13—10.15），返校后请及时销假。' } },
        { id: 'ap2', student: '孙倩', stuTone: 'tone-red', cls: '计科 2302', type: '病假', tag: '待审批', tagTone: 'warn', urgent: false,
          range: '10 月 14 日（1 天）', days: '1 天', reason: '感冒发热，附校医院就诊证明',
          submitted: '今天 08:12', sla: '剩余 20 小时', files: [ { name: '校医院证明.pdf', size: '1.1 MB', icon: 'file-text' } ],
          flow: [ { k: '学生提交申请', t: '今天 08:12', state: 'done' }, { k: '辅导员审批', t: '进行中', state: 'active' }, { k: '学工处备案', t: '待处理', state: 'wait' } ],
          actions: ['驳回', '同意'],
          ai: { suggest: '同意', confidence: 81,
            summary: '病假 1 天，附校医院就诊证明；但该生近 7 天已缺勤 3 天，且本学期第 2 次病假，需关注连续缺勤风险。',
            checks: [
              { k: '材料核验', v: '校医院证明已上传，与主诉一致', ok: true },
              { k: '历史记录', v: '本学期第 2 次病假（上月 1 次）', ok: false },
              { k: '考勤关联', v: '近 7 天缺勤 3 天，已有预警在办', ok: false } ],
            reason: '病情属实建议同意，但需同步关怀中心跟进缺勤，必要时联系家长。',
            opinion: '同意病假 1 天；已关注近期缺勤情况，返校后约谈了解。' } },
        { id: 'ap3', student: '刘洋', stuTone: 'tone-violet', cls: '计科 2301', type: '在读证明', tag: '待审批', tagTone: 'warn', urgent: false,
          range: '—', days: '—', reason: '申请开具在读证明（用于国家助学贷款）',
          submitted: '昨天 16:40', sla: '剩余 2 天', files: [],
          flow: [ { k: '学生提交申请', t: '昨天 16:40', state: 'done' }, { k: '辅导员审批', t: '进行中', state: 'active' }, { k: '教务处盖章', t: '待处理', state: 'wait' } ],
          actions: ['驳回', '同意'] },
        { id: 'ap4', student: '赵敏', stuTone: 'tone-cyan', cls: '计科 2302', type: '事假', tag: '已通过', tagTone: 'success', urgent: false,
          range: '10 月 8 日（1 天）', days: '1 天', reason: '参加四川省大学生程序设计竞赛',
          submitted: '10 月 7 日', sla: '', files: [],
          flow: [ { k: '学生提交申请', t: '10 月 7 日 09:00', state: 'done' }, { k: '辅导员审批', t: '10 月 7 日 10:20', state: 'done' }, { k: '学工处备案', t: '10 月 7 日 14:00', state: 'done' } ],
          actions: [] },
      ],
    },

    /* ---------------- ② 预警 ---------------- */
    crisis: {
      meta: { title: '预警', sub: '学生风险与危机事件的预警跟进', accent: 'danger', icon: 'shield-alert' },
      fab: null,
      risk: { high: 2, mid: 3, low: 5, cleared: 6 },
      sla: { title: '高危待跟进', hours: 18, note: '孙倩连续缺勤已超 24 小时未处置，建议立即联系家长' },
      stats: [ { num: 2, label: '高危待跟进', tone: 'danger' }, { num: 5, label: '本月已跟进', tone: 'success' }, { num: 1, label: '已解除', tone: 'quiet' } ],
      segments: ['待跟进 2', '跟进中 3', '已解除 1'],
      items: [
        { id: 'cr1', student: '陈思远', stuTone: 'tone-orange', cls: '计科 2301', level: '高危', levelTone: 'danger',
          title: '心理测评异常', source: '系统自动识别 · SCL-90 测评',
          signals: [ { k: '近 7 天出勤', v: '-38%', dir: 'down' }, { k: '焦虑因子', v: '偏高', dir: 'up' }, { k: '夜间活跃', v: '异常', dir: 'up' } ],
          triggered: '今天 08:30',
          steps: [ { k: '发现预警', state: 'done' }, { k: '联系学生', state: 'done' }, { k: '记录关怀', state: 'active' }, { k: '回访闭环', state: 'wait' } ],
          actions: ['记录关怀', '开始跟进'] },
        { id: 'cr2', student: '孙倩', stuTone: 'tone-red', cls: '计科 2302', level: '高危', levelTone: 'danger',
          title: '连续缺勤', source: '考勤系统 · 连续 3 天未签到',
          signals: [ { k: '连续缺勤', v: '3 天', dir: 'up' }, { k: '家长电话', v: '无人接听', dir: 'up' } ],
          triggered: '昨天 21:10',
          steps: [ { k: '发现预警', state: 'done' }, { k: '联系学生', state: 'active' }, { k: '联系家长', state: 'wait' }, { k: '回访闭环', state: 'wait' } ],
          actions: ['联系家长', '开始跟进'] },
        { id: 'cr3', student: '周航', stuTone: 'tone-slate', cls: '软工 2301', level: '中危', levelTone: 'warn',
          title: '学业预警', source: '教务系统 · 学分绩点统计',
          signals: [ { k: '挂科课程', v: '2 门', dir: 'up' }, { k: '学分绩点', v: '1.86', dir: 'down' } ],
          triggered: '10 月 9 日',
          steps: [ { k: '发现预警', state: 'done' }, { k: '学业谈话', state: 'active' }, { k: '制定计划', state: 'wait' }, { k: '回访闭环', state: 'wait' } ],
          actions: ['记录关怀', '开始跟进'] },
      ],
    },

    /* ---------------- ③ 公告 ---------------- */
    announcement: {
      meta: { title: '公告', sub: '面向班级发布通知与公告', accent: 'brand', icon: 'megaphone' },
      fab: { label: '发布公告', icon: 'plus' },
      reach: { published: 6, read: 156, total: 172, urgent: 2, draft: 1 },
      stats: [ { num: 6, label: '本月发布', tone: 'brand' }, { num: 156, label: '累计已读', tone: 'success' }, { num: 2, label: '紧急公告', tone: 'warn' } ],
      segments: ['全部 6', '普通 3', '重要 2', '紧急 1'],
      items: [
        { id: 'an1', title: '关于周一班会时间调整的通知', level: '重要', levelTone: 'warn', pinned: true,
          scope: '计科 2301', read: 38, total: 42, time: '昨天 17:10',
          excerpt: '原定周一 14:00 的班会调整至 16:00，地点 3 号教学楼 201，请相互转告。' },
        { id: 'an2', title: '助学金申请材料提交提醒', level: '普通', levelTone: 'brand', pinned: false,
          scope: '计科 2302', read: 40, total: 40, time: '10 月 9 日',
          excerpt: '请需申请助学金的同学于本周五前将材料交至办公室 A203。' },
        { id: 'an3', title: '台风天气停课通知', level: '紧急', levelTone: 'danger', pinned: true,
          scope: '全部班级', read: 96, total: 98, time: '10 月 6 日',
          excerpt: '受台风影响，明日全天停课，请留校注意安全，勿外出。' },
        { id: 'an4', title: '十月心理健康普测安排', level: '普通', levelTone: 'brand', pinned: false,
          scope: '计科 2301', read: 35, total: 42, time: '10 月 8 日',
          excerpt: '本周三下午统一在实验楼机房完成心理普测，请提前 10 分钟到场。' },
      ],
    },

    /* ---------------- ④ 成长档案 ---------------- */
    portfolio: {
      meta: { title: '成长档案', sub: '学生成长记录与作品集管理', accent: 'violet', icon: 'award' },
      fab: { label: '新增档案', icon: 'plus' },
      stats: [ { num: 47, label: '成长记录', tone: 'violet' }, { num: 12, label: '学生作品', tone: 'brand' }, { num: 8, label: '荣誉奖项', tone: 'warn' } ],
      students: [
        { id: 'u1', name: '陈思远', tone: 'tone-orange', count: 9 },
        { id: 'u3', name: '李梦琪', tone: 'tone-green', count: 7 },
        { id: 'u2', name: '王浩', tone: 'tone-blue', count: 6 },
        { id: 'u5', name: '赵敏', tone: 'tone-cyan', count: 5 },
        { id: 'u4', name: '刘洋', tone: 'tone-violet', count: 4 },
      ],
      badges: [
        { icon: 'trophy', tone: 'warn', name: '竞赛获奖', count: 4 },
        { icon: 'medal', tone: 'violet', name: '荣誉表彰', count: 6 },
        { icon: 'graduation-cap', tone: 'brand', name: '学业成果', count: 12 },
        { icon: 'heart-handshake', tone: 'cyan', name: '志愿服务', count: 5 },
      ],
      segments: ['全部', '学习成果', '实践经历', '荣誉奖项'],
      timeline: [
        { id: 'pf1', student: '陈思远', tone: 'tone-orange', cls: '计科 2301', cat: '荣誉奖项', catTone: 'warn',
          title: '省级程序设计竞赛三等奖', date: '2026-09-28', icon: 'trophy',
          desc: '四川省大学生程序设计竞赛组委会颁发，团队赛，担任队长。', thumb: true },
        { id: 'pf2', student: '李梦琪', tone: 'tone-green', cls: '计科 2301', cat: '实践经历', catTone: 'violet',
          title: '暑期社会实践报告', date: '2026-09-15', icon: 'heart-handshake',
          desc: '在绵阳市社区服务中心完成 40 小时志愿服务，提交实践报告一份。', thumb: true },
        { id: 'pf3', student: '王浩', tone: 'tone-blue', cls: '计科 2301', cat: '学习成果', catTone: 'brand',
          title: '数据结构课程设计', date: '2026-09-10', icon: 'graduation-cap',
          desc: '完成「校园导航系统」课程设计，评分 92 分，被评为优秀作品。', thumb: false },
        { id: 'pf4', student: '赵敏', tone: 'tone-cyan', cls: '计科 2302', cat: '荣誉奖项', catTone: 'warn',
          title: '校级三好学生', date: '2026-07-01', icon: 'medal',
          desc: '2025—2026 学年综合测评专业前 5%，获评校级三好学生。', thumb: false },
      ],
    },

    /* ---------------- ⑤ 问卷互评 ---------------- */
    survey: {
      meta: { title: '问卷互评', sub: '匿名问卷发放与学生互评', accent: 'cyan', icon: 'clipboard-list' },
      fab: { label: '新建问卷', icon: 'plus' },
      stats: [ { num: 2, label: '进行中', tone: 'cyan' }, { num: 5, label: '已结束', tone: 'success' }, { num: 86, label: '回收份数', tone: 'violet' } ],
      segments: ['进行中 2', '已结束 5', '草稿 1'],
      items: [
        { id: 'sv1', title: '班级学风建设匿名问卷', status: '进行中', statusTone: 'cyan', anon: true,
          collected: 32, total: 42, deadline: '10 月 15 日', questions: 12,
          dims: ['学习氛围', '班委工作', '课堂纪律'], scope: '计科 2301', published: '10 月 8 日' },
        { id: 'sv2', title: '心理健康状况普测', status: '进行中', statusTone: 'cyan', anon: true,
          collected: 40, total: 40, deadline: '10 月 12 日', questions: 30,
          dims: ['情绪状态', '人际关系', '压力应对'], scope: '计科 2302', published: '10 月 5 日' },
        { id: 'sv3', title: '上学期班级工作满意度互评', status: '已结束', statusTone: 'success', anon: true,
          collected: 41, total: 42, deadline: '已截止', questions: 15,
          dims: ['班级管理', '活动组织', '服务态度'], scope: '计科 2301', published: '9 月 20 日' },
      ],
    },

    /* ---------------- ⑥ 关怀中心 ---------------- */
    care: {
      meta: { title: '关怀中心', sub: '谈心记录与心理关怀跟进', accent: 'warn', icon: 'heart-pulse' },
      fab: { label: '新增关怀记录', icon: 'plus' },
      temperature: { score: 86, note: '本月重点关注学生关怀覆盖 86%，尚有 2 人未完成首次谈心' },
      stats: [ { num: 4, label: '本月谈心', tone: 'warn' }, { num: 2, label: '待回访', tone: 'danger' }, { num: 9, label: '累计记录', tone: 'success' } ],
      segments: ['谈心记录', '家访记录', '激励记录'],
      followups: [
        { name: '陈思远', tone: 'tone-orange', reason: '焦虑情绪跟进回访', due: '今天到期' },
        { name: '孙倩', tone: 'tone-red', reason: '缺勤情况家访回访', due: '明天到期' },
      ],
      timeline: [
        { id: 'ca1', student: '陈思远', tone: 'tone-orange', type: '谈心', typeTone: 'warn', icon: 'notebook-pen',
          title: '一对一谈心 · 焦虑情绪疏导', when: '今天 16:20', place: '辅导员办公室', way: '面对面',
          content: '了解近期焦虑来源（课业压力 + 家庭期望），已安抚情绪并约定每周一次沟通。',
          followup: '建议转介心理中心做进一步评估', done: false },
        { id: 'ca2', student: '孙倩', tone: 'tone-red', type: '家访', typeTone: 'brand', icon: 'heart-handshake',
          title: '电话家访 · 缺勤情况沟通', when: '昨天 19:30', place: '—', way: '电话',
          content: '与家长沟通连续缺勤情况，家长反馈学生近期在家状态尚可，承诺督促按时返校。',
          followup: '下周一确认返校情况', done: true },
        { id: 'ca3', student: '李梦琪', tone: 'tone-green', type: '激励', typeTone: 'success', icon: 'thumbs-up',
          title: '进步激励 · 班级学风建设', when: '10 月 9 日', place: '教学楼 302', way: '面对面',
          content: '在班级学风建设中表现突出，予以口头表扬并计入成长档案。',
          followup: '—', done: true },
      ],
    },

    /* ---------------- ⑦ 家校沟通 ---------------- */
    guardian: {
      meta: { title: '家校沟通', sub: '家长联系人沟通与记录留痕', accent: 'cyan', icon: 'heart-handshake' },
      fab: { label: '发起沟通', icon: 'plus' },
      stats: [ { num: 6, label: '家长联系人', tone: 'cyan' }, { num: 3, label: '本月沟通', tone: 'brand' }, { num: 1, label: '待反馈', tone: 'warn' } ],
      segments: ['联系人 6', '沟通台账 12'],
      contacts: [
        { id: 'gd1', student: '陈思远', tone: 'tone-orange', cls: '计科 2301', relation: '父亲', relTone: 'cyan',
          name: '陈建国', phone: '138****6621', last: '昨天 19:30', channel: '电话', pending: false },
        { id: 'gd2', student: '孙倩', tone: 'tone-red', cls: '计科 2302', relation: '母亲', relTone: 'cyan',
          name: '王秀兰', phone: '139****3387', last: '昨天 20:10', channel: '电话', pending: true },
        { id: 'gd3', student: '刘洋', tone: 'tone-violet', cls: '计科 2301', relation: '父亲', relTone: 'cyan',
          name: '刘海峰', phone: '137****1102', last: '10 月 8 日', channel: '短信', pending: false },
      ],
      ledger: [
        { id: 'gl1', student: '孙倩', tone: 'tone-red', relation: '母亲 王秀兰', channel: '电话', chTone: 'brand',
          when: '昨天 20:10', dur: '8 分钟',
          content: '就连续缺勤情况与家长沟通，家长承诺督促学生按时返校，将配合学校做好日常提醒。', pending: true },
        { id: 'gl2', student: '陈思远', tone: 'tone-orange', relation: '父亲 陈建国', channel: '电话', chTone: 'brand',
          when: '昨天 19:30', dur: '12 分钟',
          content: '已告知学生近期心理测评情况与在校表现，家长表示会配合关注孩子的情绪状态。' },
        { id: 'gl3', student: '刘洋', tone: 'tone-violet', relation: '父亲 刘海峰', channel: '短信', chTone: 'cyan',
          when: '10 月 8 日', dur: '—',
          content: '反馈学生在校表现良好，提醒按时提交助学贷款材料，家长表示感谢。' },
      ],
      templates: ['缺勤情况沟通', '心理状态告知', '学业预警反馈', '在校表现通报'],
    },

    /* ---------------- ⑧ 今日任务（v3：时间轴式） ---------------- */
    tasks: {
      meta: { title: '任务日程', sub: '逾期、今日与本周任务的时间轴视图', accent: 'success', icon: 'list-checks' },
      fab: { label: '新建任务', icon: 'plus' },
      progress: { total: 9, done: 5 },
      dateStrip: [
        { w: '一', d: '26' }, { w: '二', d: '27' }, { w: '三', d: '28' },
        { w: '四', d: '29' }, { w: '五', d: '30', on: true }, { w: '六', d: '31' },
      ],
      timeline: [
        { title: '已逾期', tone: 'danger', items: [
          { id: 'tk6', title: '回复孙倩助学金材料咨询', done: false, priority: '高', priTone: 'danger', t: '昨天 18:00', from: '反馈', fromTone: 'cyan' },
        ] },
        { title: '今天 · 上午', tone: 'quiet', items: [
          { id: 'tk4', title: '核对迎新志愿者名单', done: true, priority: '低', priTone: 'quiet', t: '12:00 前', from: '日常', fromTone: 'quiet' },
        ] },
        { title: '今天 · 下午', tone: 'success', items: [
          { id: 'tk2', title: '与陈思远完成一对一谈心', done: false, priority: '高', priTone: 'danger', t: '16:20', from: '关怀', fromTone: 'warn' },
          { id: 'tk1', title: '审批陈思远事假申请', done: false, priority: '高', priTone: 'danger', t: '17:00', from: '审批', fromTone: 'warn' },
          { id: 'tk3', title: '发布班会时间调整公告', done: true, priority: '中', priTone: 'brand', t: '17:10', from: '公告', fromTone: 'brand' },
        ] },
        { title: '今天 · 晚间', tone: 'quiet', items: [
          { id: 'tk5', title: '提交本周工作周报', done: false, priority: '中', priTone: 'brand', t: '20:00', from: '日常', fromTone: 'quiet' },
        ] },
        { title: '本周计划', tone: 'brand', items: [
          { id: 'tk8', title: '学风建设问卷数据回收', done: false, priority: '中', priTone: 'brand', t: '周三', from: '问卷', fromTone: 'cyan' },
          { id: 'tk7', title: '十五五规划学习心得提交', done: false, priority: '中', priTone: 'brand', t: '周五', from: '日常', fromTone: 'quiet' },
          { id: 'tk9', title: '学工例会', done: false, priority: '低', priTone: 'quiet', t: '周五 15:00', from: '会议', fromTone: 'violet' },
        ] },
      ],
    },

    /* ---------------- ⑨ AI 洞察 ---------------- */
    ai: {
      meta: { title: 'AI 洞察', sub: '主动发现与推荐联系建议', accent: 'violet', icon: 'sparkles' },
      fab: { label: '生成洞察周报', icon: 'wand-sparkles' },
      headline: '绵小城为你分析了 47 名学生近 14 天的 12 类行为信号，发现 3 条值得优先关注',
      insights: [
        { id: 'ai1', icon: 'heart-pulse', tone: 'danger', title: '优先关注：陈思远',
          desc: '近 7 天出勤下降 38%，心理测评焦虑因子偏高，夜间活跃异常；建议 24 小时内完成面谈并记录关怀。',
          confidence: 92, action: '发起沟通', actionKind: 'chat', ref: '陈思远' },
        { id: 'ai2', icon: 'trending-down', tone: 'warn', title: '学业风险：周航',
          desc: '本学已有 2 门课程挂科，学分绩点 1.86 低于预警线；建议约谈并制定学业提升计划。',
          confidence: 84, action: '记录关怀', actionKind: 'care', ref: '周航' },
        { id: 'ai3', icon: 'thumbs-up', tone: 'success', title: '正向激励：李梦琪',
          desc: '连续 3 周出勤满勤、课堂互动积极，社区服务时长领先；建议计入成长档案并公开表扬。',
          confidence: 78, action: '写入档案', actionKind: 'portfolio', ref: '李梦琪' },
      ],
      metrics: [
        { label: '出勤异常', value: 3, delta: '+2', tone: 'danger', icon: 'activity' },
        { label: '心理关注', value: 2, delta: '持平', tone: 'warn', icon: 'gauge' },
        { label: '学业预警', value: 1, delta: '-1', tone: 'success', icon: 'chart-line' },
        { label: '正向信号', value: 8, delta: '+3', tone: 'violet', icon: 'trending-up' },
      ],
      report: { week: '第 7 教学周', generated: '今天 08:00',
        points: [ '本周班级整体出勤率 96.2%，较上周回升 1.4%', '重点关注名单 2 人，均已建立跟进记录', '学风建设问卷回收率 76%，建议再次提醒未提交学生' ] },
    },
  },

  /* ==================================================================
     v3：学生详情（档案头卡 + 锚点 Tab）· 重点关注学生的富数据
     其他学生由 app.js 按 _generic 模板合成
     ================================================================== */
  studentDetail: {
    _generic: {
      kpis: [ { k: '出勤率', v: '96%', tone: '' }, { k: '绩点', v: '3.2', tone: '' }, { k: '进行任务', v: '1', tone: 'brand' }, { k: '档案', v: '6', tone: 'violet' } ],
      grades: [
        { k: '高等数学 · 期中', v: '82' }, { k: '数据结构 · 平时', v: '88', tone: 'good' },
        { k: '大学英语 · 平时', v: '79' }, { k: '大学物理 · 平时', v: '84' } ],
      attendance: [
        { k: '课堂出勤', v: '本月无缺勤', tone: 'good' },
        { k: '晚归记录', v: '无', tone: '' },
        { k: '图书馆', v: '本月到馆 4 次 · 8h', tone: '' } ],
      dynamics: [
        { dot: 'success', k: '图书馆学习打卡 4 次', t: '本周' },
        { dot: 'brand', k: '提交课程设计选题', t: '10-09' },
        { dot: 'violet', k: '参加社团纳新活动', t: '09-20' } ],
      records: [
        { icon: 'graduation-cap', t: '2026-09-10', k: '数据结构课程设计选题通过', tone: 'brand' },
        { icon: 'medal', t: '2026-06-30', k: '获评 2025-2026 学年优秀学生', tone: 'violet' },
        { icon: 'heart-handshake', t: '2026-05-18', k: '社区志愿服务 8 小时', tone: 'cyan' } ],
    },
    u1: {
      kpis: [ { k: '出勤率', v: '87%', tone: 'warn' }, { k: '绩点', v: '2.8', tone: 'warn' }, { k: '进行任务', v: '3', tone: 'brand' }, { k: '档案', v: '9', tone: 'violet' } ],
      risk: { level: '高危', title: '心理测评异常', source: '系统自动识别 · SCL-90 测评',
        desc: '焦虑因子偏高，近 7 天出勤下降 38%，夜间活跃异常。已建立跟进记录，需完成面谈与回访闭环。',
        sla: '24 小时内完成首次面谈', pct: 68 },
      grades: [
        { k: '高等数学 · 期中', v: '78' }, { k: '数据结构 · 平时', v: '85', tone: 'good' },
        { k: '大学英语 · 平时', v: '72' }, { k: '大学物理 · 平时', v: '58', tone: 'bad' } ],
      attendance: [
        { k: '课堂出勤', v: '近 7 天下降 38%', tone: 'bad' },
        { k: '晚归记录', v: '10-11 晚归 1 次（23:52）', tone: 'warn' },
        { k: '图书馆', v: '本周到馆 6 次 · 12.5h', tone: 'good' } ],
      dynamics: [
        { dot: 'danger', k: '触发高危预警（心理测评异常）', t: '10-13' },
        { dot: 'success', k: '图书馆学习打卡 6 次 · 12.5h', t: '本周' },
        { dot: 'warn', k: '高等数学随堂测验未通过', t: '10-09' },
        { dot: 'violet', k: '院篮球赛亚军（与室友组队）', t: '10-12' } ],
      records: [
        { icon: 'shield-alert', t: '2026-10-13', k: '触发高危预警 · 已启动跟进', tone: 'danger' },
        { icon: 'trophy', t: '2026-09-28', k: '省级程序设计竞赛三等奖（队长）', tone: 'warn' },
        { icon: 'notebook-pen', t: '2026-09-15', k: '一对一谈心 · 开学适应', tone: 'warn' },
        { icon: 'heart-handshake', t: '2026-06-01', k: '社区志愿服务 26 小时', tone: 'cyan' } ],
    },
    u6: {
      kpis: [ { k: '出勤率', v: '81%', tone: 'danger' }, { k: '绩点', v: '2.9', tone: '' }, { k: '进行任务', v: '2', tone: 'brand' }, { k: '档案', v: '5', tone: 'violet' } ],
      risk: { level: '高危', title: '连续缺勤', source: '考勤系统 · 连续 3 天未签到',
        desc: '连续 3 天未签到，家长电话一度无人接听。家访已沟通，待确认返校情况并回访闭环。',
        sla: '明天前确认返校情况', pct: 45 },
    },
  },

  /* ==================================================================
     v3：学生主页（QQ 风格）· 展示墙 / 动态 / 互动
     ================================================================== */
  studentPages: {
    u1: {
      motto: '最近有点累，但想先把这周撑过去。',
      likes: 23, visitors: 56,
      badges: [
        { icon: 'trophy', tone: 'warn', label: '省赛三等奖' },
        { icon: 'heart-handshake', tone: 'cyan', label: '志愿 26h' },
        { icon: 'flame', tone: 'danger', label: '打卡 12 天' },
        { icon: 'graduation-cap', tone: 'brand', label: '课设优秀' },
      ],
      photos: 6,
      posts: [
        { id: 'u1p1', time: '昨天 22:41', text: '图书馆待到闭馆，数据结构练习题总算刷完了，坚持！', imgs: 1, likeN: 12, cmtN: 3 },
        { id: 'u1p2', time: '10-12', text: '和室友拿到院篮球赛亚军，虽然输了但打得很爽，明年再来。', imgs: 2, likeN: 31, cmtN: 8 },
        { id: 'u1p3', time: '09-28', text: '省赛拿了个三等奖，感谢队友带飞，明年再战！', imgs: 1, likeN: 45, cmtN: 12 },
      ],
    },
    u2: {
      motto: '球场上见真章。',
      likes: 18, visitors: 34,
      badges: [ { icon: 'trophy', tone: 'warn', label: '院篮球赛亚军' }, { icon: 'flame', tone: 'danger', label: '打卡 8 天' } ],
      photos: 4,
      posts: [
        { id: 'u2p1', time: '10-12', text: '院篮球赛亚军！最后一球差一点就进了。', imgs: 2, likeN: 28, cmtN: 6 },
        { id: 'u2p2', time: '09-30', text: '新学期第一节实验课，环境搭建终于跑通了。', imgs: 0, likeN: 9, cmtN: 2 },
      ],
    },
    u3: {
      motto: '把每一件小事做好。',
      likes: 41, visitors: 67,
      badges: [ { icon: 'medal', tone: 'violet', label: '三好学生' }, { icon: 'heart-handshake', tone: 'cyan', label: '志愿 40h' }, { icon: 'trending-up', tone: 'success', label: '满勤 3 周' } ],
      photos: 8,
      posts: [
        { id: 'u3p1', time: '10-09', text: '社会实践报告写完了，40 小时的社区服务收获很多。', imgs: 1, likeN: 36, cmtN: 9 },
        { id: 'u3p2', time: '09-18', text: '连续三周满勤打卡，继续保持。', imgs: 0, likeN: 22, cmtN: 4 },
      ],
    },
    u4: { motto: '码农进行时。', likes: 12, visitors: 21, badges: [ { icon: 'graduation-cap', tone: 'brand', label: '课设优秀' } ], photos: 3,
      posts: [ { id: 'u4p1', time: '10-08', text: '校园导航系统课设答辩结束，92 分！', imgs: 1, likeN: 19, cmtN: 5 } ] },
    u5: { motto: '竞赛 Season，冲！', likes: 27, visitors: 39, badges: [ { icon: 'trophy', tone: 'warn', label: '校赛二等奖' }, { icon: 'book-open', tone: 'brand', label: '刷题 200+' } ], photos: 5,
      posts: [ { id: 'u5p1', time: '10-07', text: '程序设计竞赛请了假去打校赛，拿了个二等奖，值了。', imgs: 1, likeN: 24, cmtN: 6 } ] },
    u6: { motto: '最近在调整状态。', likes: 8, visitors: 19, badges: [ { icon: 'heart-handshake', tone: 'cyan', label: '志愿 12h' } ], photos: 2,
      posts: [ { id: 'u6p1', time: '10-05', text: '家里有点事，落了几天课，回来要抓紧补上。', imgs: 0, likeN: 6, cmtN: 2 } ] },
    u7: { motto: '绩点保卫战。', likes: 10, visitors: 18, badges: [ { icon: 'book-open', tone: 'brand', label: '图书馆达人' } ], photos: 3,
      posts: [ { id: 'u7p1', time: '09-26', text: '这学期目标：把绩点拉回 3.0，第一周打卡完成。', imgs: 0, likeN: 11, cmtN: 3 } ] },
  },

  /* ---------------- 学生档案 / 智能体（占位说明） ---------------- */
  placeholder: {
    students: { title: '学生档案', desc: '本次改版未涉及该模块，保持现有设计不变。\n（学生列表 / 学生成长档案 / 近期互动）' },
    agent: { title: '绵小城 · 智能体', desc: '本次改版未涉及该模块，保持现有设计不变。\n（对话式智能助手入口）' },
  },
};