/* =========================================================================
   学生端驾驶舱原型 · mock.js
   唯一数据源。视角：绵阳城市学院 · 信息工程学院 · 软件工程 2202 班 · 大二
   节次时间与真实产品 SchedulePage.vue 的 periodTimes 完全一致。
   ========================================================================= */

const PERIOD_TIMES = {
  1: '08:30', 2: '09:20', 3: '10:25', 4: '11:15',
  5: '14:10', 6: '15:00', 7: '16:05', 8: '16:55',
  9: '18:30', 10: '19:20', 11: '20:10', 12: '21:00',
};

const PERIOD_ENDS = {
  1: '09:10', 2: '10:00', 3: '11:05', 4: '11:55',
  5: '14:50', 6: '15:40', 7: '16:45', 8: '17:35',
  9: '19:10', 10: '20:00', 11: '20:50', 12: '21:40',
};

const DAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const DB = {
  /* ---------------- 学生档案 ---------------- */
  profile: {
    name: '陈予安',
    shortName: '予安',
    avatarText: '陈',
    college: '信息工程学院',
    major: '软件工程',
    className: '软件工程 2202 班',
    grade: '大二',
    studentNo: '20221730220',
    counselor: '李静',
  },

  /* ---------------- 成长画像 ---------------- */
  growth: {
    totalScore: 78.4,
    comprehensiveScore: 82.6,
    recordCount: 47,
    skillCount: 12,
    semesterRank: '12 / 46',
    dims: [
      { key: 'academic',  name: '学术素养', score: 86.2, level: '优秀', color: 'brand',
        source: '课程成绩 18 条 · 竞赛获奖 3 条 · 论文/专利 1 条',
        tip: '专业核心课均分 88.4，是本学期最稳的一块。程序设计类课程已接近满绩，可向更难的选修课挑战。' },
      { key: 'innovation', name: '创新能力', score: 71.5, level: '良好', color: 'violet',
        source: '学科竞赛 3 条 · 创新项目 1 条 · 专利 0 条',
        tip: '已有省级大创在研，但缺少可展示的成果物。建议本学期把项目做出一个可演示的原型。' },
      { key: 'practice',  name: '实践能力', score: 80.1, level: '良好', color: 'cyan',
        source: '实习实践 4 条 · 志愿服务 6 条 · 项目经历 3 条',
        tip: '实践记录数量充足，质量偏轻。可把一次课程设计升级为完整项目并沉淀到作品集。' },
      { key: 'social',    name: '社交素养', score: 74.8, level: '良好', color: 'success',
        source: '学生工作 2 条 · 社团活动 5 条 · 团队协作 4 条',
        tip: '担任班级学习委员，协作记录稳定。建议补充一次跨专业的团队经历。' },
      { key: 'overall',   name: '综合素质', score: 79.3, level: '良好', color: 'warn',
        source: '第二课堂 9 条 · 荣誉表彰 6 条 · 体美劳 5 条',
        tip: '第二课堂学分已修满。体测成绩是当前短板，建议下学期优先安排。' },
    ],
    monthlyTrend: [
      { month: '3月', value: 71.2 }, { month: '4月', value: 73.6 },
      { month: '5月', value: 74.1 }, { month: '6月', value: 76.8 },
      { month: '9月', value: 77.0 }, { month: '10月', value: 78.4 },
    ],
    gpaTrend: [
      { term: '大一上', gpa: 3.21 }, { term: '大一下', gpa: 3.38 },
      { term: '大二上', gpa: 3.52 },
    ],
  },

  /* ---------------- 课程 ---------------- */
  courses: [
    { id: 'c1', name: '数据结构与算法', teacher: '王成林', location: '实验楼 B302', day: 1, start: 1, len: 2, color: 'brand',  type: '专业核心' },
    { id: 'c2', name: '大学英语（四）',  teacher: '周敏',  location: '教学楼 A205', day: 1, start: 3, len: 2, color: 'cyan',   type: '公共必修' },
    { id: 'c3', name: '概率论与数理统计', teacher: '刘振华', location: '教学楼 C401', day: 1, start: 7, len: 2, color: 'violet', type: '学科基础' },
    { id: 'c4', name: '计算机组成原理', teacher: '王成林', location: '实验楼 B305', day: 2, start: 1, len: 2, color: 'brand',  type: '专业核心' },
    { id: 'c5', name: '软件工程导论',   teacher: '李建国', location: '教学楼 A312', day: 2, start: 5, len: 2, color: 'success', type: '专业核心' },
    { id: 'c6', name: '体育（羽毛球）',  teacher: '张海涛', location: '体育馆',     day: 3, start: 3, len: 2, color: 'warn',   type: '公共必修' },
    { id: 'c7', name: '数据库原理',     teacher: '孙晓月', location: '实验楼 B201', day: 3, start: 1, len: 2, color: 'brand',  type: '专业核心' },
    { id: 'c8', name: '马克思主义基本原理', teacher: '赵文', location: '教学楼 D102', day: 4, start: 3, len: 2, color: 'violet', type: '公共必修' },
    { id: 'c9', name: '数据结构实验',   teacher: '王成林', location: '实验楼 B302', day: 4, start: 7, len: 2, color: 'brand',  type: '实验' },
    { id: 'c10', name: 'Web 前端开发',  teacher: '孙晓月', location: '实验楼 B401', day: 5, start: 1, len: 2, color: 'cyan',  type: '专业选修' },
    { id: 'c11', name: '创新创业基础',  teacher: '李建国', location: '教学楼 A108', day: 5, start: 5, len: 2, color: 'violet', type: '通识' },
  ],

  /* ---------------- 今日待办 ---------------- */
  today: [
    { id: 't1', title: '数据结构第 6 章作业', course: '数据结构与算法', due: '今天 23:59', urgent: true,  done: false, kind: '作业' },
    { id: 't2', title: '软件工程需求文档 v2 提交', course: '软件工程导论', due: '今天 22:00', urgent: true,  done: false, kind: '作业' },
    { id: 't3', title: '英语四级模拟听力第 3 套', course: '大学英语（四）', due: '今天 21:00', urgent: false, done: false, kind: '自习' },
    { id: 't4', title: '概率论作业 4.1—4.8', course: '概率论与数理统计', due: '明天 12:00', urgent: false, done: false, kind: '作业' },
    { id: 't5', title: '蓝桥杯报名信息确认', course: '', due: '10-30 18:00', urgent: false, done: false, kind: '竞赛' },
  ],

  week: [
    { id: 'w1', title: '大创中期检查材料', course: '创新创业基础', due: '11-02 17:00', urgent: false, done: false, kind: '项目' },
    { id: 'w2', title: '数据库课程设计选题', course: '数据库原理', due: '11-04 23:59', urgent: false, done: false, kind: '作业' },
    { id: 'w3', title: '英语四级正式考试', course: '', due: '11-08 09:00', urgent: false, done: false, kind: '考试' },
    { id: 'w4', title: '数据结构第 5 章作业', course: '数据结构与算法', due: '10-24 23:59', urgent: false, done: true, kind: '作业' },
    { id: 'w5', title: '提交 Web 前端实验三', course: 'Web 前端开发', due: '10-23 17:00', urgent: false, done: true, kind: '实验' },
  ],

  overdue: [
    { id: 'o1', title: '计算机组成原理实验报告', course: '计算机组成原理', due: '10-25 23:59', urgent: true, done: false, kind: '实验' },
    { id: 'o2', title: '图书馆超期图书归还', course: '', due: '10-26 18:00', urgent: true, done: false, kind: '生活' },
  ],

  /* ---------------- AI 主动发现 ---------------- */
  aiActions: [
    { id: 'a1', level: 'high',   title: '计算机组成原理实验报告已逾期 2 天', desc: '王成林老师本周五截止补交，逾期将计 0 分',
      action: '去补交', color: 'danger', icon: 'triangle-alert' },
    { id: 'a2', level: 'high',   title: '软件工程需求文档今晚 22:00 截止', desc: '当前进度 60%，剩余「用例图」与「接口说明」两节',
      action: '继续撰写', color: 'warn', icon: 'clock' },
    { id: 'a3', level: 'medium', title: '本学期实验课出勤率 91%', desc: '低于专业平均 96%，缺勤集中在周四下午',
      action: '查看详情', color: 'cyan', icon: 'activity' },
    { id: 'a4', level: 'medium', title: '创新能力维度低于综合水平 7 分', desc: '已有大创项目但缺少成果物，建议补一个可演示原型',
      action: '查看成长', color: 'violet', icon: 'lightbulb' },
    { id: 'a5', level: 'low',    title: '英语四级考试还有 11 天', desc: '近三次模拟听力均分 158，稳定过线，可加强阅读',
      action: '安排复习', color: 'brand', icon: 'book-open' },
  ],

  aiInsight:
    '这周你的压力主要来自两门专业核心课的作业叠加：数据结构第 6 章与软件工程需求文档都在今晚截止。' +
    '从过往记录看，你在晚上 20:00 之后的专注度最高，建议先完成需求文档的用例图部分，再处理算法作业。' +
    '已逾期的那份实验报告不必焦虑——王老师近两年对首次逾期都给了补交窗口，今晚提交仍可计入平时成绩。',

  aiUpdatedAt: '2 分钟前更新',

  /* ---------------- 成绩分析 ---------------- */
  grades: {
    gpa: 3.52,
    rank: 12,
    total: 46,
    credits: 68.5,
    terms: [
      { key: 't2024-1', label: '大一上', gpa: 3.21, rank: 21,
        courses: [
          { name: '高等数学 A1', credit: 5, score: 84, type: '必修' },
          { name: '线性代数',   credit: 3, score: 88, type: '必修' },
          { name: '程序设计基础', credit: 4, score: 91, type: '必修' },
          { name: '大学英语（一）', credit: 3, score: 76, type: '必修' },
          { name: '思想道德与法治', credit: 3, score: 82, type: '必修' },
        ] },
      { key: 't2024-2', label: '大一下', gpa: 3.38, rank: 16,
        courses: [
          { name: '高等数学 A2', credit: 5, score: 81, type: '必修' },
          { name: '离散数学',   credit: 3, score: 86, type: '必修' },
          { name: '面向对象程序设计', credit: 4, score: 93, type: '必修' },
          { name: '大学英语（二）', credit: 3, score: 79, type: '必修' },
          { name: '中国近现代史纲要', credit: 3, score: 85, type: '必修' },
        ] },
      { key: 't2025-1', label: '大二上', gpa: 3.52, rank: 12,
        courses: [
          { name: '数据结构与算法', credit: 4, score: 92, type: '核心' },
          { name: '计算机组成原理', credit: 4, score: 78, type: '核心' },
          { name: '概率论与数理统计', credit: 3, score: 84, type: '必修' },
          { name: '大学英语（四）', credit: 3, score: 81, type: '必修' },
          { name: '软件工程导论', credit: 3, score: 89, type: '核心' },
          { name: '数据库原理',   credit: 4, score: 87, type: '核心' },
        ] },
    ],
  },

  /* ---------------- 快捷入口 ---------------- */
  shortcuts: [
    { key: 'grades',    name: '成绩分析', icon: 'chart-column', color: 'cyan',    route: 'grades' },
    { key: 'growth',    name: '成长轨迹', icon: 'trending-up',  color: 'violet',  route: 'growth' },
    { key: 'plan',      name: '学习计划', icon: 'list-checks',  color: 'brand',   route: 'route:/student/plan' },
    { key: 'portfolio', name: '作品集',   icon: 'folder',       color: 'warn',    route: 'route:/student/portfolio' },
    { key: 'archive',   name: '成长档案', icon: 'notebook-pen', color: 'success', route: 'route:/student/growth' },
    { key: 'emotion',   name: '情绪树洞', icon: 'heart',        color: 'danger',  route: 'route:/student/emotion' },
  ],
};

/* 异步桩：模拟真实接口延迟，用于展示骨架态 */
function getData(key, delay = 320) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(JSON.parse(JSON.stringify(DB[key]))), delay);
  });
}
