/**
 * 子页顶栏固定性验证
 * 断言：
 *  1) 三个子页顶栏高度恒为 48px，top 恒为 0（不随滚动移动）
 *  2) 顶栏区域内最上层元素就是顶栏自身（内容没有盖到它上面）
 *  3) 滚动后出现分隔线（is-scrolled）
 */
const { chromium } = require('playwright');
const path = require('path');
const OUT = path.join(__dirname, '_shots');

const USER = { id: 1, role: 'student', name: '测试同学', username: 'test' };
const SEM = '2026-2027-1';
const COURSES = [
  { id: 1, name: '数据结构与算法', teacher: '张老师', location: 'A301', day_of_week: 1, start_period: 1, end_period: 2, week_start: 1, week_end: 16, semester: SEM },
  { id: 2, name: '数据库原理', teacher: '李老师', location: 'B202', day_of_week: 2, start_period: 3, end_period: 4, week_start: 1, week_end: 16, semester: SEM },
  { id: 3, name: '软件工程导论', teacher: '王老师', location: 'C105', day_of_week: 3, start_period: 5, end_period: 6, week_start: 1, week_end: 16, semester: SEM },
  { id: 4, name: '计算机网络', teacher: '赵老师', location: 'A402', day_of_week: 4, start_period: 1, end_period: 2, week_start: 1, week_end: 16, semester: SEM },
  { id: 5, name: '操作系统', teacher: '孙老师', location: 'D201', day_of_week: 5, start_period: 3, end_period: 4, week_start: 1, week_end: 16, semester: SEM },
];
const GRADE_LIST = [
  { id: 1, course_name: '数据结构与算法', score: 92, gpa: 4.2, credit: 4, semester: SEM, course_type: '必修' },
  { id: 2, course_name: '数据库原理', score: 88, gpa: 3.8, credit: 3.5, semester: SEM, course_type: '必修' },
  { id: 3, course_name: '软件工程导论', score: 85, gpa: 3.5, credit: 3, semester: SEM, course_type: '必修' },
  { id: 4, course_name: '大学英语（四）', score: 78, gpa: 3.0, credit: 2, semester: SEM, course_type: '必修' },
  { id: 5, course_name: '体育', score: 74, gpa: 2.7, credit: 1, semester: SEM, course_type: '必修' },
  { id: 6, course_name: '线性代数', score: 95, gpa: 4.5, credit: 3, semester: SEM, course_type: '必修' },
  { id: 7, course_name: '马克思原理', score: 82, gpa: 3.2, credit: 2, semester: SEM, course_type: '必修' },
  { id: 8, course_name: '概率论', score: 90, gpa: 4.0, credit: 3, semester: SEM, course_type: '必修' },
];
const GRADES = {
  stats: { weighted_avg: 84.2, avg_gpa: 3.52, total_credits: 68.5, rank: 12, total_students: 46, pass_rate: 100 },
  semester_gpa: [
    { semester: '2024-2025-1', gpa: 3.2, avg_score: 81 },
    { semester: '2024-2025-2', gpa: 3.35, avg_score: 83 },
    { semester: '2025-2026-1', gpa: 3.52, avg_score: 84.5 },
  ],
  score_distribution: [
    { range: '0-59', count: 0 }, { range: '60-69', count: 1 },
    { range: '70-79', count: 2 }, { range: '80-89', count: 5 }, { range: '90-100', count: 4 },
  ],
  course_type_stats: [
    { type: '必修', avg_score: 84, avg_gpa: 3.5, count: 6 },
    { type: '选修', avg_score: 88, avg_gpa: 3.7, count: 2 },
  ],
};
const EXAMS = [
  { id: 1, course_name: '数据结构与算法', exam_date: '2026-11-08', start_time: '09:00', end_time: '11:00', location: 'A301' },
];
const PROFILE = {
  total_score: 78,
  radar: [
    { name: '学术素养', value: 88 }, { name: '创新能力', value: 71 },
    { name: '实践能力', value: 82 }, { name: '社交素养', value: 76 }, { name: '综合素质', value: 80 },
  ],
  stats_by_type: [
    { name: '荣誉', value: 6 }, { name: '竞赛', value: 3 }, { name: '实践', value: 7 },
    { name: '论文', value: 2 }, { name: '成果', value: 4 }, { name: '兴趣', value: 5 },
  ],
  counts: { records: 27, skills: 9, honors: 6, competitions: 3, practices: 7, papers: 2, achievements: 4, interests: 5 },
  monthly_trend: ['5月', '6月', '9月', '10月'].map((m, i) => ({ month: m, count: 4 + i * 2 })),
};
const RECORDS = Array.from({ length: 24 }, (_, i) => {
  const d = new Date(Date.UTC(2026, 9, 28));
  d.setUTCDate(d.getUTCDate() - i);
  return { id: 1000 + i, type: 'honor', title: '成长记录 ' + (i + 1), description: '示例描述', record_date: d.toISOString().slice(0, 10), created_at: d.toISOString() };
});

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const j = o => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  await p.route(u => u.pathname.startsWith('/api/'), async route => {
    const url = route.request().url();
    if (url.includes('/growth/profile')) return route.fulfill(j(PROFILE));
    if (url.includes('/growth/records')) return route.fulfill(j(RECORDS));
    if (url.includes('/growth/project')) return route.fulfill(j([]));
    if (url.includes('/academic/analysis/')) return route.fulfill(j(GRADES));
    if (url.includes('/academic/grades')) return route.fulfill(j(GRADE_LIST));
    if (url.includes('/academic/exams')) return route.fulfill(j(EXAMS));
    if (url.includes('/course') || url.includes('/schedule')) return route.fulfill(j(COURSES));
    return route.fulfill(j([]));
  });
  await p.addInitScript(u => localStorage.setItem('campus_user', JSON.stringify(u)), USER);
  await p.goto('http://127.0.0.1:5199/student/schedule', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);
  await p.screenshot({ path: path.join(OUT, 'bar-home.png') });

  const failures = [];
  for (const key of ['growth', 'grades', 'schedule']) {
    if (key === 'schedule') await p.click('.gd-today-sub');
    else await p.getByRole('button', { name: key === 'grades' ? '成绩分析' : '成长轨迹' }).first().click();
    await p.waitForTimeout(1800);

    const rows = [];
    for (const target of [0, 60, 300, 700, 1400, 2600]) {
      await p.evaluate(t => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = t; }, target);
      await p.waitForTimeout(280);
      rows.push(await p.evaluate(() => {
        const bar = document.querySelector('.subpage-bar');
        const r = bar.getBoundingClientRect();
        const topEl = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return {
          scrollTop: Math.round(document.querySelector('.content-row').scrollTop),
          top: Math.round(r.top),
          h: Math.round(r.height),
          pos: getComputedStyle(bar).position,
          scrolled: bar.classList.contains('is-scrolled'),
          barOnTop: !!topEl && (topEl === bar || bar.contains(topEl)),
        };
      }));
    }

    console.log('\n--- ' + key + ' ---');
    for (const r of rows) {
      console.log('  scrollTop=' + String(r.scrollTop).padStart(4) + '  top=' + r.top + '  h=' + r.h + '  ' + r.pos + '  barOnTop=' + r.barOnTop + '  is-scrolled=' + r.scrolled);
    }
    const allFixed = rows.every(r => r.top === 0 && r.h === 48);
    const allOnTop = rows.every(r => r.barOnTop);
    console.log('  固定不动: ' + (allFixed ? 'PASS' : 'FAIL') + '   不被内容覆盖: ' + (allOnTop ? 'PASS' : 'FAIL'));
    if (!allFixed) failures.push(key + ' 顶栏位置/高度异常');
    if (!allOnTop) failures.push(key + ' 顶栏被内容覆盖');

    await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 320; });
    await p.waitForTimeout(320);
    await p.screenshot({ path: path.join(OUT, 'bar-' + key + '-scrolled.png') });

    await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 0; });
    await p.waitForTimeout(250);
    await p.screenshot({ path: path.join(OUT, 'bar-' + key + '-top.png') });
    await p.click('.sp-back');
    await p.waitForTimeout(1200);
  }
  console.log('\n===== 总结 =====');
  console.log(failures.length ? 'FAIL: ' + failures.join('; ') : '全部 PASS');
  await b.close();
})();
