const path = require('path');
const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1180, height: 860 } });
  await p.route(u => u.pathname.startsWith('/api/'), route => {
    const url = route.request().url();
    if (url.includes('analysis')) return route.fulfill(j({ stats: { total_courses: 12, total_credits: 38, avg_score: 84.5, avg_gpa: 3.42, highest_gpa: 3.8, lowest_gpa: 2.9, pass_rate: 100, gpa_rank: 8, total_students: 120 }, semester_gpa: [{ semester: '2025-1', gpa: 3.21 }, { semester: '2025-2', gpa: 3.42 }], course_type_stats: [], score_distribution: [], top_courses: [{ course_name: '高数', score: 92 }], weak_courses: [{ course_name: '英语听力', score: 71 }] }));
    if (url.includes('/academic/grades')) return route.fulfill(j([
      { id: 1, course_name: '高等数学', score: 92, credit: 4, semester: '2025-2', exam_type: '期末', gpa: 4.0 },
      { id: 2, course_name: '大学英语', score: 86, credit: 3, semester: '2025-2', exam_type: '期末', gpa: 3.6 },
      { id: 4, course_name: '线性代数', score: 81, credit: 3, semester: '2025-1', exam_type: '期末', gpa: 3.1 }
    ]));
    if (url.includes('streak')) return route.fulfill(j({ current: 12, longest: 20, today_checked: true }));
    if (url.includes('/leave/my')) return route.fulfill(j([]));
    if (url.includes('/service/tickets')) return route.fulfill(j([]));
    if (url.includes('agent/proactive')) return route.fulfill(j({ actions: [], insight: '' }));
    if (url.includes('portfolio') || url.includes('project')) return route.fulfill(j([]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(() => {
    localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' }));
    localStorage.setItem('student_sem_goals', JSON.stringify({ '2025-1': 3.2, '2025-2': 3.6 }));
  });
  for (const [u, n] of [['/student/schedule?tab=grades', 'd-grades'], ['/student/schedule?tab=service', 'd-service'], ['/student/schedule?tab=plan', 'd-plan']]) {
    await p.goto('http://127.0.0.1:5199' + u, { waitUntil: 'networkidle' });
    await p.waitForTimeout(2200);
    if (n === 'd-grades') {
      const dbg = await p.evaluate(() => ({
        goalItems: document.querySelectorAll('.goal-item').length,
        glItems: document.querySelectorAll('.gl-item').length,
        hasInput: !!document.querySelector('.goal-item .el-input-number'),
      }));
      console.log('DESK-GOAL', JSON.stringify(dbg));
    }
    await p.screenshot({ path: path.join('_shots', n + '.png'), fullPage: false });
    console.log('shot', n);
  }
  await b.close();
})();
