const path = require('path');
const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await p.route(u => u.pathname.startsWith('/api/'), route => {
    const url = route.request().url();
    if (url.includes('analysis')) return route.fulfill(j({ stats: { total_courses: 12, total_credits: 38, avg_score: 84.5, avg_gpa: 3.42, highest_gpa: 3.8, lowest_gpa: 2.9, pass_rate: 100, gpa_rank: 8, total_students: 120 }, semester_gpa: [{ semester: '2025-1', gpa: 3.21 }, { semester: '2025-2', gpa: 3.42 }], course_type_stats: [], score_distribution: [], top_courses: [{ course_name: '高数', score: 92 }], weak_courses: [{ course_name: '英语听力', score: 71 }] }));
    if (url.includes('streak')) return route.fulfill(j({ current: 12, longest: 20, today_checked: true }));
    return route.fulfill(j([]));
  });
  await p.addInitScript(() => localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' })));
  const shots = [['grades', 'v5-live-grades'], ['plan', 'v5-live-plan'], ['ai', 'v5-live-ai']];
  for (const [tab, name] of shots) {
    await p.goto('http://127.0.0.1:5199/student/schedule?tab=' + tab, { waitUntil: 'networkidle' });
    await p.waitForTimeout(2500);
    await p.screenshot({ path: path.join('_shots', name + '.png') });
    console.log('shot', name);
  }
  await b.close();
})();
