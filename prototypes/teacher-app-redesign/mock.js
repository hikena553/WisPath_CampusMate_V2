/* =========================================================================
   mock.js · 唯一数据源（plain global，无 ES module，保证 file:// 双击可开）
   数据取自真实业务语境：绵阳城市学院 · 信息工程学院 · 辅导员视角
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
    { id: 'c1', name: '信息工程学院', icon: 'building-2', tone: 'tone-blue',
      majors: [
        { id: 'm1', name: '计算机科学与技术', classes: [
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
        { id: 'm2', name: '软件工程', classes: [
          { id: 'k3', name: '软工 2301', count: 38, students: [
            { id: 'u7', name: '周航', username: '20230301', tone: 'tone-slate' },
          ] },
        ] },
      ] },
    { id: 'c2', name: '经济管理学院', icon: 'building-2', tone: 'tone-cyan',
      majors: [
        { id: 'm3', name: '工商管理', classes: [
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
    { id: 'no5', type: '系统', title: '账号安全提示', content: '检测到你的账号在新设备登录，如非本人操作请及时改密。', time: '周三 20:15', read: true, tone: 'slate' },
  ],

  /* ---------------- 首页 · 常用功能宫格（原「更多」模块迁入） ---------------- */
  quickEntries: [
    { id: 'approval', label: '审批', desc: '请假、证明等事项受理与审批', icon: 'clipboard-check', tone: 'warn', badge: 3, badgeWarn: true },
    { id: 'crisis', label: '预警', desc: '学生风险与危机事件跟进', icon: 'shield-alert', tone: 'danger', badge: 2 },
    { id: 'announcement', label: '公告', desc: '面向班级发布通知与公告', icon: 'megaphone', tone: 'brand' },
    { id: 'portfolio', label: '成长档案', desc: '学生成长记录与作品集管理', icon: 'award', tone: 'violet' },
    { id: 'survey', label: '问卷互评', desc: '匿名问卷发放与学生互评', icon: 'bar-chart-3', tone: 'brand' },
    { id: 'care', label: '关怀中心', desc: '谈心记录与心理关怀跟进', icon: 'heart', tone: 'warn' },
    { id: 'guardian', label: '家校沟通', desc: '家长联系人沟通与记录留痕', icon: 'link', tone: 'cyan' },
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
      { id: 'survey', label: '问卷互评', desc: '匿名问卷发放与学生互评', icon: 'bar-chart-3', tone: 'brand' },
      { id: 'care', label: '关怀中心', desc: '谈心记录与心理关怀跟进', icon: 'heart', tone: 'warn' },
      { id: 'guardian', label: '家校沟通', desc: '家长联系人沟通与记录留痕', icon: 'link', tone: 'cyan' },
    ] },
    { title: '效率工具', items: [
      { id: 'tasks', label: '今日任务', desc: '待办、逾期与日程的统一入口', icon: 'clock', tone: 'success' },
      { id: 'ai', label: 'AI 洞察', desc: '主动发现与推荐联系建议', icon: 'sparkles', tone: 'cyan' },
    ] },
  ],

  /* ---------------- 统一子页面模板数据 ---------------- */
  subPages: {
    approval: {
      title: '审批', sub: '请假、证明等事项的受理与审批', accent: 'warn',
      stats: [ { num: 3, label: '待审批', tone: 'warn' }, { num: 12, label: '本月已办', tone: 'success' }, { num: 1, label: '已驳回', tone: 'danger' } ],
      segments: ['待审批 3', '已处理', '全部'],
      items: [
        { title: '陈思远 · 事假', tag: '待审批', tagTone: 'warn', body: '请假时间：10 月 13 日 — 10 月 15 日（3 天）\n事由：家中有事，需返回绵阳处理', meta: '计科 2301 · 提交于 09:24', actions: ['驳回', '同意'] },
        { title: '孙倩 · 病假', tag: '待审批', tagTone: 'warn', body: '请假时间：10 月 14 日（1 天）\n事由：感冒发热，附校医院证明', meta: '计科 2302 · 提交于 08:12', actions: ['驳回', '同意'] },
        { title: '刘洋 · 在读证明', tag: '待审批', tagTone: 'warn', body: '申请事项：开具在读证明（用于助学贷款）', meta: '计科 2301 · 提交于 昨天 16:40', actions: ['驳回', '同意'] },
        { title: '赵敏 · 事假', tag: '已通过', tagTone: 'success', body: '请假时间：10 月 8 日（1 天）\n事由：参加校外竞赛', meta: '计科 2302 · 处理于 10 月 7 日' },
      ],
    },
    crisis: {
      title: '预警', sub: '学生风险与危机事件的预警跟进', accent: 'danger',
      stats: [ { num: 2, label: '高危待跟进', tone: 'danger' }, { num: 5, label: '本月已跟进', tone: 'success' }, { num: 1, label: '已解除', tone: 'quiet' } ],
      segments: ['待跟进 2', '跟进中', '已解除'],
      items: [
        { title: '陈思远 · 心理测评异常', tag: '高危', tagTone: 'danger', body: '测评结果：SCL-90 焦虑因子偏高，近期出勤率下降。\n建议：24 小时内面谈并记录关怀。', meta: '计科 2301 · 触发于 今天 08:30', actions: ['记录关怀', '开始跟进'] },
        { title: '孙倩 · 连续缺勤', tag: '高危', tagTone: 'danger', body: '连续 3 天未签到，联系未果，家长电话无人接听。', meta: '计科 2302 · 触发于 昨天 21:10', actions: ['联系家长', '开始跟进'] },
        { title: '周航 · 学业预警', tag: '中危', tagTone: 'warn', body: '本学期已有 2 门课程挂科，学分绩点低于 2.0。', meta: '软工 2301 · 触发于 10 月 9 日' },
      ],
    },
    announcement: {
      title: '公告', sub: '面向班级发布通知与公告', accent: 'brand',
      stats: [ { num: 6, label: '本月发布', tone: 'brand' }, { num: 128, label: '累计阅读', tone: 'success' }, { num: 2, label: '紧急公告', tone: 'warn' } ],
      segments: ['全部', '普通', '重要', '紧急'],
      items: [
        { title: '关于周一班会时间调整的通知', tag: '重要', tagTone: 'warn', body: '原定周一 14:00 的班会调整至 16:00，地点 3 号教学楼 201，请相互转告。', meta: '计科 2301 · 昨天 17:10 · 已读 38/42' },
        { title: '助学金申请材料提交提醒', tag: '普通', tagTone: 'brand', body: '请需申请助学金的同学于本周五前将材料交至办公室 A203。', meta: '计科 2302 · 10 月 9 日 · 已读 40/40' },
        { title: '【紧急】台风天气停课通知', tag: '紧急', tagTone: 'danger', body: '受台风影响，明日全天停课，请留校注意安全，勿外出。', meta: '全部班级 · 10 月 6 日 · 已读 96/98' },
      ],
    },
    portfolio: {
      title: '成长档案', sub: '学生成长记录与作品集管理', accent: 'violet',
      stats: [ { num: 47, label: '成长记录', tone: 'violet' }, { num: 12, label: '学生作品', tone: 'brand' }, { num: 8, label: '荣誉奖项', tone: 'warn' } ],
      segments: ['全部', '学习成果', '实践经历', '荣誉奖项'],
      items: [
        { title: '陈思远 · 省级程序设计竞赛三等奖', tag: '荣誉奖项', tagTone: 'warn', body: '获奖时间：2026 年 9 月；颁发单位：四川省大学生程序设计竞赛组委会。', meta: '计科 2301 · 录入于 9 月 28 日' },
        { title: '李梦琪 · 暑期社会实践报告', tag: '实践经历', tagTone: 'violet', body: '在绵阳市社区服务中心完成 40 小时志愿服务，提交实践报告一份。', meta: '计科 2301 · 录入于 9 月 15 日' },
        { title: '王浩 · 数据结构课程设计', tag: '学习成果', tagTone: 'brand', body: '完成「校园导航系统」课程设计，评分 92 分。', meta: '计科 2301 · 录入于 9 月 10 日' },
      ],
    },
    survey: {
      title: '问卷互评', sub: '匿名问卷发放与学生互评', accent: 'brand',
      stats: [ { num: 2, label: '进行中', tone: 'brand' }, { num: 5, label: '已结束', tone: 'success' }, { num: 86, label: '回收份数', tone: 'violet' } ],
      segments: ['进行中 2', '已结束', '草稿'],
      items: [
        { title: '班级学风建设匿名问卷', tag: '进行中', tagTone: 'brand', body: '回收 32/42 份 · 截止 10 月 15 日\n包含学习氛围、班委工作、课堂纪律三个维度。', meta: '计科 2301 · 发布于 10 月 8 日' },
        { title: '心理健康状况普测', tag: '进行中', tagTone: 'brand', body: '回收 40/40 份 · 截止 10 月 12 日\n结果仅用于关怀跟进，严格保密。', meta: '计科 2302 · 发布于 10 月 5 日' },
        { title: '上学期班级工作满意度互评', tag: '已结束', tagTone: 'success', body: '回收 41/42 份 · 满意度 92%\n结果已生成报告，可查看明细。', meta: '计科 2301 · 结束于 9 月 20 日' },
      ],
    },
    care: {
      title: '关怀中心', sub: '谈心记录与心理关怀跟进', accent: 'warn',
      stats: [ { num: 4, label: '本月谈心', tone: 'warn' }, { num: 2, label: '待回访', tone: 'danger' }, { num: 9, label: '累计记录', tone: 'success' } ],
      segments: ['谈心记录', '家访记录', '激励记录'],
      items: [
        { title: '陈思远 · 一对一谈心', tag: '谈心', tagTone: 'warn', body: '了解近期焦虑来源，已安抚情绪并约定每周一次沟通。\n后续：建议转介心理中心做进一步评估。', meta: '今天 16:20 · 地点：辅导员办公室' },
        { title: '孙倩 · 家访记录', tag: '家访', tagTone: 'brand', body: '电话家访，家长反馈学生近期状态良好，家庭关系融洽。', meta: '昨天 19:30 · 方式：电话' },
        { title: '李梦琪 · 进步激励', tag: '激励', tagTone: 'success', body: '在班级学风建设中表现突出，予以口头表扬并计入成长档案。', meta: '10 月 9 日 · 记录人：李静' },
      ],
    },
    guardian: {
      title: '家校沟通', sub: '家长联系人沟通与记录留痕', accent: 'cyan',
      stats: [ { num: 6, label: '家长联系人', tone: 'cyan' }, { num: 3, label: '本月沟通', tone: 'brand' }, { num: 1, label: '待反馈', tone: 'warn' } ],
      segments: ['联系人', '沟通台账'],
      items: [
        { title: '陈思远 · 家长：陈建国', tag: '父亲', tagTone: 'cyan', body: '联系电话：138****6621\n沟通记录：已告知学生近期心理测评情况，家长表示会配合关注。', meta: '最近沟通：昨天 19:30' },
        { title: '孙倩 · 家长：王秀兰', tag: '母亲', tagTone: 'cyan', body: '联系电话：139****3387\n沟通记录：就缺勤情况与家长沟通，家长承诺督促学生按时返校。', meta: '最近沟通：昨天 20:10' },
        { title: '刘洋 · 家长：刘海峰', tag: '父亲', tagTone: 'cyan', body: '联系电话：137****1102\n沟通记录：反馈学生在校表现良好，家长表示感谢。', meta: '最近沟通：10 月 8 日' },
      ],
    },
  },

  /* ---------------- 学生档案 / 智能体（占位说明） ---------------- */
  placeholder: {
    students: { title: '学生档案', desc: '本次改版未涉及该模块，保持现有设计不变。\n（学生列表 / 学生成长档案 / 近期互动）' },
    agent: { title: '绵小城 · 智能体', desc: '本次改版未涉及该模块，保持现有设计不变。\n（对话式智能助手入口）' },
  },
};