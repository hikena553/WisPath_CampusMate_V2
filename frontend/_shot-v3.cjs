const { chromium } = require('D:/StudyNote/Mian02/node_modules/playwright');
const path = require('path');
const OUT = 'D:/StudyNote/Mian02/frontend/_shots';
const BASE = 'http://127.0.0.1:5199';
const USER = { id: 9001, role: 'student', username: '予安', real_name: '予安' };

const pad = (n) => String(n).padStart(2, '0');
const dstr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const today = new Date();
const dayAgo = (n) => { const d = new Date(today); d.setDate(d.getDate() - n); return dstr(d); };

const PROFILE = {
  total_score: 78.4,
  radar: [
    { name: '学术素养', value: 86 }, { name: '创新能力', value: 71 },
    { name: '实践能力', value: 80 }, { name: '社交素养', value: 74 },
    { name: '综合素质', value: 79 },
  ],
  stats_by_type: [{ name: '荣誉', value: 6 }, { name: '竞赛', value: 3 }, { name: '实践', value: 5 }, { name: '论文', value: 2 }, { name: '成果', value: 1 }],
  monthly_trend: [
    { month: '5月', count: 4, type: '荣誉' }, { month: '6月', count: 7, type: '竞赛' },
    { month: '9月', count: 5, type: '荣誉' }, { month: '10月', count: 9, type: '竞赛' },
  ],
  skills: ['Python', 'Vue', '数据分析'], interests: ['算法', '开源'],
  total_records: 47, total_skills: 12,
  gpa_trend: [{ semester: '大二上', gpa: 3.42 }, { semester: '大二下', gpa: 3.52 }],
};

const RECORDS = [
  { id: 1, type: 'honor', title: '国家奖学金', date: dayAgo(1), honor_level: '国家级', description: '学年综合测评前 3%' },
  { id: 2, type: 'competition', title: 'ACM-ICPC 省级银奖', date: dayAgo(3), competition_level: '省级', organizer: 'ACM/ICPC 组委会' },
  { id: 3, type: 'practice', title: '暑期三下乡支教', date: dayAgo(12), practice_type: '三下乡', description: '连续两年参与' },
  { id: 4, type: 'paper', title: '面向校园场景的轻量推荐模型', date: dayAgo(20), paper_type: '核心期刊', paper_name: '计算机应用研究' },
  { id: 5, type: 'achievement', title: '智慧校园考勤系统软著', date: dayAgo(28), achievement_type: '软件著作权', achievement_name: 'CampusMate 考勤模块' },
  { id: 6, type: 'honor', title: '校级三好学生', date: dayAgo(35), honor_level: '校级' },
  { id: 7, type: 'competition', title: '蓝桥杯省赛一等奖', date: dayAgo(42), competition_level: '省级' },
  { id: 8, type: 'practice', title: '社区数字助老志愿活动', date: dayAgo(50), practice_type: '社会志愿活动' },
];
// 在近 8 周内补一些记录，让热力图有内容
for (let i = 0; i < 16; i++) {
  RECORDS.push({ id: 100 + i, type: 'honor', title: `学习笔记 ${i + 1}`, date: dayAgo(2 + i * 3), honor_level: '校级' });
}

const GRADES = {
  stats: { total_courses: 12, total_credits: 68.5, avg_score: 84.2, avg_gpa: 3.52, highest_gpa: 3.9, lowest_gpa: 3.1, pass_rate: 100, gpa_rank: 12, total_students: 46 },
  semester_gpa: [
    { semester: '2024-2025-1', gpa: 3.2, credits: 18, course_count: 5 },
    { semester: '2024-2025-2', gpa: 3.35, credits: 20, course_count: 5 },
    { semester: '2025-2026-1', gpa: 3.52, credits: 17, course_count: 4 },
  ],
  course_type_stats: [
    { type: '专业核心', count: 4, avg_score: 88, avg_gpa: 3.8 },
    { type: '学科基础', count: 3, avg_score: 74, avg_gpa: 2.5 },
  ],
  score_distribution: [
    { range: '60-69', count: 1, percentage: 8 },
    { range: '70-79', count: 2, percentage: 17 },
    { range: '80-89', count: 5, percentage: 42 },
    { range: '90-100', count: 4, percentage: 33 },
  ],
  top_courses: [
    { course_name: '数据结构与算法', score: 92, gpa: 4.2 },
    { course_name: '数据库原理', score: 88, gpa: 3.8 },
  ],
  weak_courses: [{ course_name: '概率论与数理统计', score: 74, gpa: 2.4 }],
};
const GRADE_LIST = [
  { id: 1, course_name: '数据结构与算法', score: 92, credit: 4, gpa: 4.2, semester: '2025-2026-1' },
  { id: 2, course_name: '数据库原理', score: 88, credit: 3.5, gpa: 3.8, semester: '2025-2026-1' },
  { id: 3, course_name: '软件工程导论', score: 85, credit: 3, gpa: 3.5, semester: '2025-2026-1' },
  { id: 4, course_name: '大学英语（四）', score: 78, credit: 3, gpa: 2.8, semester: '2025-2026-1' },
  { id: 5, course_name: '概率论与数理统计', score: 74, credit: 4, gpa: 2.4, semester: '2025-2026-1' },
];
const EXAMS = [
  { id: 1, course_name: '概率论与数理统计', exam_date: '2026-11-08', start_time: '09:00', end_time: '11:00', location: '教学楼 A205' },
];
const SEM = '2026-2027-1';
const SCHEDULE = [
  { id: 1, name: '数据库原理', teacher: '孙晓月', location: '实验楼 B201', day_of_week: 1, start_period: 1, end_period: 2, week_start: 1, week_end: 16, semester: SEM },
  { id: 2, name: '数据结构与算法', teacher: '王成林', location: '实验楼 B302', day_of_week: 1, start_period: 3, end_period: 4, week_start: 1, week_end: 16, semester: SEM },
  { id: 3, name: '大学英语（四）', teacher: '周敏', location: '教学楼 A205', day_of_week: 2, start_period: 1, end_period: 2, week_start: 1, week_end: 16, semester: SEM },
  { id: 4, name: '体育（羽毛球）', teacher: '张海涛', location: '体育馆', day_of_week: 3, start_period: 3, end_period: 4, week_start: 1, week_end: 16, semester: SEM },
  { id: 5, name: '软件工程导论', teacher: '李建国', location: '教学楼 A312', day_of_week: 4, start_period: 5, end_period: 6, week_start: 1, week_end: 16, semester: SEM },
  { id: 6, name: '概率论与数理统计', teacher: '陈立', location: '教学楼 B108', day_of_week: 5, start_period: 1, end_period: 2, week_start: 1, week_end: 16, semester: SEM },
];

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push('ERR ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE ' + m.text().slice(0, 160)); });

  await p.route(u => u.pathname.startsWith('/api/'), (r) => {
    const url = r.request().url();
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(d) });
    if (url.includes('/auth/me')) return j(USER);
    if (url.includes('/growth/profile')) return j(PROFILE);
    if (url.includes('/growth/records')) return j(RECORDS);
    if (url.includes('/growth/project')) return j([]);
    if (url.includes('/academic/analysis/')) return j(GRADES);
    if (url.includes('/academic/grades')) return j(GRADE_LIST);
    if (url.includes('/academic/exams')) return j(EXAMS);
    if (url.includes('/grade')) return j(GRADES);
    if (url.includes('/course') || url.includes('/schedule')) return j(SCHEDULE);
    if (url.includes('/plan/today')) return j([]);
    if (url.includes('/agent/proactive')) return j({ insight: '', actions: [] });
    return j([]);
  });
  await p.addInitScript(u => localStorage.setItem('campus_user', JSON.stringify(u)), USER);
  await p.goto(BASE + '/student/schedule', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);
  await p.screenshot({ path: path.join(OUT, 'v3-home.png') });

  const results = [];
  for (const key of ['growth', 'grades', 'schedule']) {
    if (key === 'schedule') {
      await p.click('.gd-today-sub');
    } else {
      const label = key === 'grades' ? '成绩分析' : '成长轨迹';
      await p.getByRole('button', { name: label }).first().click();
    }
    await p.waitForTimeout(1900);
    await p.screenshot({ path: path.join(OUT, `v3-${key}-01.png`) });

    if (key === 'grades') {
      /* 回归检查：成绩页两张图之间的间距必须 > 0（移动端隐藏了竖分割线，
         曾经因为用 margin 而 flex 列布局忽略，两块图贴在一起看不清边界） */
      const gap = await p.evaluate(() => {
        const [a, b] = [...document.querySelectorAll('.grades-view .panel')];
        if (!a || !b) return null;
        return Math.round(b.getBoundingClientRect().top - a.getBoundingClientRect().bottom);
      });
      console.log('grades 面板间距:', gap, gap !== null && gap > 0 ? 'PASS' : 'FAIL');
    }

    const head = await p.evaluate(() => {
      const bar = document.querySelector('.subpage-bar');
      if (!bar) return { found: false };
      const r = bar.getBoundingClientRect();
      const cs = getComputedStyle(bar);
      return { found: true, top: Math.round(r.top), height: Math.round(r.height), position: cs.position };
    });

    await p.evaluate(() => {
      const s = document.querySelector('.content-row');
      if (s) s.scrollTop = 600;
    });
    await p.waitForTimeout(600);
    const head2 = await p.evaluate(() => {
      const bar = document.querySelector('.subpage-bar');
      const s = document.querySelector('.content-row');
      return { top: bar ? Math.round(bar.getBoundingClientRect().top) : null, h: bar ? Math.round(bar.getBoundingClientRect().height) : null, scrollTop: s ? Math.round(s.scrollTop) : null };
    });
    await p.screenshot({ path: path.join(OUT, `v3-${key}-02-scrolled.png`) });

    // 滚回顶部再滚一段拍中段
    await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 0; });
    await p.waitForTimeout(400);
    await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 430; });
    await p.waitForTimeout(500);
    await p.screenshot({ path: path.join(OUT, `v3-${key}-03-mid.png`) });

    results.push({ key, head, scrolled: head2 });
    console.log(key, '初始头部:', JSON.stringify(head), '| 滚 600 后:', JSON.stringify(head2));

    await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 0; });
    await p.waitForTimeout(300);
    await p.click('.sp-back');
    await p.waitForTimeout(1300);
  }

  // 断言：三页头部高度一致 + 滚动后 top 保持 0
  const heights = results.map(r => r.head.height);
  const stable = results.every(r => r.scrolled.top === r.head.top && r.scrolled.h === r.head.height);
  console.log('\n===== 判定 =====');
  console.log('三页头部高度:', heights.join(' / '), heights.every(h => h === heights[0]) ? 'PASS 一致' : 'FAIL 不一致');
  console.log('滚动前后 top 不变:', results.map(r => `${r.head.top}→${r.scrolled.top}`).join(' / '), stable ? 'PASS 固定吸顶' : 'FAIL 有偏移');
  console.log('position:', results.map(r => r.head.position).join(' / '));

  console.log(errs.length ? '\n' + [...new Set(errs)].slice(0, 8).join('\n') : '\nNO ERRORS');
  await b.close();
})();
