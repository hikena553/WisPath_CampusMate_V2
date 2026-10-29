const path = require('path');
const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });

const COURSES = [
  { id: 1, name: '高等数学', teacher: '王建国', location: '教1-302', day_of_week: 1, start_period: 1, end_period: 2, week_start: 1, week_end: 16, course_type: '必修' },
  { id: 2, name: '大学英语', teacher: '李薇', location: '外语楼205', day_of_week: 1, start_period: 3, end_period: 4, week_start: 1, week_end: 16, course_type: '必修' },
  { id: 3, name: '数据结构', teacher: '陈志远', location: '计算机楼A401', day_of_week: 2, start_period: 1, end_period: 4, week_start: 1, week_end: 16, course_type: '必修' },
  { id: 4, name: '线性代数', teacher: '赵敏', location: '教2-108', day_of_week: 3, start_period: 3, end_period: 4, week_start: 1, week_end: 12, course_type: '必修' },
  { id: 5, name: '操作系统', teacher: '刘洋', location: '计算机楼B203', day_of_week: 4, start_period: 5, end_period: 6, week_start: 1, week_end: 16, course_type: '必修' },
  { id: 6, name: '体育', teacher: '孙强', location: '东操场', day_of_week: 5, start_period: 7, end_period: 8, week_start: 1, week_end: 16, course_type: '必修' },
  { id: 7, name: '算法设计', teacher: '周晓', location: '计算机楼A305', day_of_week: 5, start_period: 1, end_period: 2, week_start: 1, week_end: 16, course_type: '选修' }
];

const PLAN = {
  id: 1, title: '数据结构期末冲刺', objective: '两个月内吃透树与图，期末 90+',
  stage: '进行中', start_date: '2026-10-01', end_date: '2026-12-20',
  status: 'active', goal_id: null, goal_title: '保研绩点 3.6',
  done_rate: 43, task_done: 6, task_total: 14, overdue: 1, checkin_days: 9,
  created_at: '2026-10-01T09:00:00'
};

const STAGES = [
  { id: 11, plan_id: 1, title: '基础回顾', goal: '梳理线性表与栈队列', order_index: 1, status: 'done', score: 92, evaluation: '概念清晰，练习题完成度高。', weaknesses: '复杂度分析还不够熟。', suggestions: '补 5 道复杂度判断题。', submitted_result: '完成 20 道基础题', created_at: '2026-10-02T10:00:00' },
  { id: 12, plan_id: 1, title: '树与二叉树', goal: '掌握遍历与递归', order_index: 2, status: 'done', score: 88, evaluation: '遍历实现正确。', weaknesses: '非递归写法不熟。', suggestions: '手写 3 种非递归遍历。', submitted_result: '完成遍历作业', created_at: '2026-10-09T10:00:00' },
  { id: 13, plan_id: 1, title: '平衡树', goal: 'AVL 与红黑树', order_index: 3, status: 'done', score: 85, evaluation: '旋转过程能推演。', weaknesses: '红黑树插入边界。', suggestions: '画 5 组插入图。', submitted_result: '完成推导笔记', created_at: '2026-10-16T10:00:00' },
  { id: 14, plan_id: 1, title: '图的遍历', goal: 'DFS / BFS 与应用', order_index: 4, status: 'active', score: null, evaluation: null, weaknesses: null, suggestions: null, submitted_result: null, created_at: '2026-10-23T10:00:00' },
  { id: 15, plan_id: 1, title: '最短路径', goal: 'Dijkstra / Floyd', order_index: 5, status: 'locked', score: null, evaluation: null, weaknesses: null, suggestions: null, submitted_result: null, created_at: '2026-10-23T10:00:00' },
  { id: 16, plan_id: 1, title: '真题模拟', goal: '两套真题限时训练', order_index: 6, status: 'locked', score: null, evaluation: null, weaknesses: null, suggestions: null, submitted_result: null, created_at: '2026-10-23T10:00:00' },
  { id: 17, plan_id: 1, title: '错题复盘', goal: '整理错题本', order_index: 7, status: 'locked', score: null, evaluation: null, weaknesses: null, suggestions: null, submitted_result: null, created_at: '2026-10-23T10:00:00' }
];

const PROFILE = {
  total_score: 78,
  radar: [
    { name: '学习能力', value: 82 }, { name: '实践能力', value: 76 },
    { name: '协作能力', value: 88 }, { name: '创新能力', value: 71 },
    { name: '自我管理', value: 79 }
  ],
  stats_by_type: [{ name: '课程学习', value: 12 }, { name: '项目实践', value: 7 }, { name: '竞赛获奖', value: 3 }, { name: '社会实践', value: 5 }],
  monthly_trend: [
    { month: '2026-07', count: 4, type: '课程学习' }, { month: '2026-08', count: 6, type: '课程学习' },
    { month: '2026-09', count: 9, type: '项目实践' }, { month: '2026-10', count: 11, type: '项目实践' }
  ],
  skills: ['Python', 'Vue', '算法'], interests: ['开源', '视觉设计'],
  skill_items: [], interest_items: [],
  total_records: 27, total_skills: 3,
  gpa_trend: [{ semester: '2025-1', gpa: 3.21 }, { semester: '2025-2', gpa: 3.42 }]
};

const RECORDS = [
  { id: 1, student_id: 7, type: 'course', title: '数据结构期末 92 分', content: '', date: '2026-10-20', tags: [], attachments: [], created_at: '2026-10-20T10:00:00' },
  { id: 2, student_id: 7, type: 'project', title: 'bluebird-agent 上线', content: '', date: '2026-10-12', tags: [], attachments: [], created_at: '2026-10-12T10:00:00' },
  { id: 3, student_id: 7, type: 'competition', title: '蓝桥杯省二', content: '', date: '2026-09-28', tags: [], attachments: [], created_at: '2026-09-28T10:00:00' }
];

const TODAY = [
  { task_id: 1, title: '完成图遍历习题', due_date: '2026-10-29', priority: 'high', status: 'pending', plan_id: 1, plan_title: '数据结构期末冲刺', checked_today: false, checkin_id: null },
  { task_id: 2, title: '复盘红黑树笔记', due_date: '2026-10-29', priority: 'normal', status: 'pending', plan_id: 1, plan_title: '数据结构期末冲刺', checked_today: true, checkin_id: 3 }
];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await p.route(u => u.pathname.startsWith('/api/'), route => {
    const url = route.request().url();
    if (url.includes('/academic/courses')) return route.fulfill(j(COURSES.map(c => ({ ...c, semester: '2026-2027-1', credit: 4, class_group_id: 1 }))));
    if (url.includes('/plan/plans/1/stages')) return route.fulfill(j(STAGES));
    if (url.includes('/plan/plans')) return route.fulfill(j([PLAN]));
    if (url.includes('/plan/stages')) return route.fulfill(j(STAGES));
    if (url.includes('/plan/goals')) return route.fulfill(j([{ id: 1, goal_type: '保研', title: '保研绩点 3.6', target_date: '2027-06-30', status: 'active', progress: 62, note: '', plan_count: 1, created_at: '2026-09-01T10:00:00' }]));
    if (url.includes('/plan/streak')) return route.fulfill(j({ current: 12, longest: 20, today_checked: true }));
    if (url.includes('/plan/today')) return route.fulfill(j(TODAY));
    if (url.includes('/plan/reminders')) return route.fulfill(j({ triggered: [], count: 0 }));
    if (url.includes('/growth/profile')) return route.fulfill(j(PROFILE));
    if (url.includes('/growth/records')) return route.fulfill(j(RECORDS));
    if (url.includes('/growth/projects')) return route.fulfill(j([]));
    if (url.includes('analysis')) return route.fulfill(j({ stats: { total_courses: 12, total_credits: 38, avg_score: 84.5, avg_gpa: 3.42, highest_gpa: 3.8, lowest_gpa: 2.9, pass_rate: 100, gpa_rank: 8, total_students: 120 }, semester_gpa: [{ semester: '2025-1', gpa: 3.21 }, { semester: '2025-2', gpa: 3.42 }], course_type_stats: [], score_distribution: [], top_courses: [{ course_name: '高数', score: 92 }], weak_courses: [{ course_name: '英语听力', score: 71 }] }));
    if (url.includes('/academic/grades')) return route.fulfill(j([
      { id: 1, course_name: '高等数学', score: 92, credit: 4, semester: '2025-2', exam_type: '期末', gpa: 4.0 },
      { id: 2, course_name: '大学英语', score: 86, credit: 3, semester: '2025-2', exam_type: '期末', gpa: 3.6 },
      { id: 3, course_name: '数据结构', score: 88, credit: 3, semester: '2025-2', exam_type: '期末', gpa: 3.8 },
      { id: 4, course_name: '线性代数', score: 81, credit: 3, semester: '2025-1', exam_type: '期末', gpa: 3.1 },
      { id: 5, course_name: '大学物理', score: 79, credit: 3, semester: '2025-1', exam_type: '期末', gpa: 3.0 }
    ]));
    if (url.includes('/academic/exams')) return route.fulfill(j([]));
    if (url.includes('/leave/my')) return route.fulfill(j([
      { id: 1, student_id: 7, start_date: '2026-10-30', end_date: '2026-10-31', reason: '[事假] 家中事务', leave_type: 'personal', status: 'pending', reject_reason: null, return_confirmed: false, created_at: '2026-10-29T09:12:00', updated_at: '2026-10-29T09:12:00' },
      { id: 2, student_id: 7, start_date: '2026-10-08', end_date: '2026-10-08', reason: '[病假] 发烧就医', leave_type: 'sick', status: 'approved', reject_reason: null, return_confirmed: true, created_at: '2026-10-07T20:00:00', updated_at: '2026-10-08T08:30:00' }
    ]));
    if (url.includes('/service/tickets')) return route.fulfill(j([{ id: 11, type: 'certificate', title: '在读证明 × 1', content: '', status: 'completed', created_at: '2026-10-12T14:02:00', updated_at: '2026-10-13T16:00:00', applicant_name: '', applicant_no: '', applicant_college: '', form_data: null, attachments: null, review_comment: null, approver_name: null }]));
    if (url.includes('agent/proactive')) return route.fulfill(j({ actions: [{ trigger: 'a', student_id: 7, priority: 4, action_type: 'homework', title: '高数作业明天截止', content: '第 5 章习题还有 3 道未完成。', target_role: 'student' }], insight: '本周压力集中在周三前。' }));
    if (url.includes('agent/insight')) return route.fulfill(j({ insight: '本周压力集中在周三前。' }));
    if (url.includes('/emotion')) return route.fulfill(j([]));
    if (url.includes('portfolio') || url.includes('project')) return route.fulfill(j([{ id: 1, project_name: 'bluebird-agent', tech_stack: 'TypeScript, FastAPI', my_role: '队长', is_team: true, start_date: '2026-09-01', end_date: null, team_members: '', description: 'AI 值周助手。', project_link: '', attachment_url: '' }]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(() => {
    localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' }));
    localStorage.setItem('student_sem_goals', JSON.stringify({ '2025-1': 3.2, '2025-2': 3.6 }));
  });

  const targets = [
    ['/student/schedule?tab=schedule', 'v6-schedule'],
    ['/student/schedule?tab=growth', 'v6-growth'],
    ['/student/schedule?tab=service', 'v6-service'],
    ['/student/schedule?tab=plan', 'v6-plan'],
    ['/student/schedule?tab=plan', 'v6-plan-scroll', 900],
    ['/student/schedule?tab=grades', 'v6-grades'],
    ['/student/schedule?tab=grades', 'v6-goal', 2400],
    ['/student/schedule', 'v6-home']
  ];
  for (const [u, n, scroll] of targets) {
    await p.goto('http://127.0.0.1:5199' + u, { waitUntil: 'networkidle' });
    await p.waitForTimeout(2400);
    if (scroll) {
      await p.evaluate((y) => {
        const el = document.querySelector('.content-row') || document.querySelector('.plan-page') || window;
        if (el === window) window.scrollTo(0, y); else el.scrollTop = y;
      }, scroll);
      await p.waitForTimeout(700);
    }
    if (n === 'v6-goal') {
      const dbg = await p.evaluate(() => {
        const out = [];
        document.querySelectorAll('.gl-edit .el-button').forEach(el => {
          const cs = getComputedStyle(el);
          out.push({ cls: el.className, bg: cs.backgroundColor, bgImg: cs.backgroundImage, attrs: [...el.attributes].map(a => a.name).join(',') });
        });
        const sheets = [...document.styleSheets].filter(s => { try { return [...s.cssRules].some(r => (r.cssText || '').includes('gl-edit')); } catch { return false; } }).length;
        return { btns: out, sheets };
      });
      console.log('DBG', JSON.stringify(dbg));
    }
    await p.screenshot({ path: path.join('_shots', n + '.png') });
    console.log('shot', n);
  }
  await b.close();
})();
