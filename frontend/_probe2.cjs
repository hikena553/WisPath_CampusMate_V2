const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1180, height: 820 } });
  await p.route(u => u.pathname.startsWith('/api/'), route => {
    const url = route.request().url();
    if (url.includes('streak')) return route.fulfill(j({ current: 12, longest: 20, today_checked: true }));
    if (url.includes('/plan/plans')) return route.fulfill(j([
      { id: 1, title: '高数第 5 章冲刺', objective: '完成第 5 章习题并复盘', start_date: '2026-10-27', end_date: '2026-11-02', done_rate: 40, task_done: 2, task_total: 5, overdue: 0, checkin_days: 3, goal_title: '' },
      { id: 2, title: 'bluebird 接口重构', objective: '统一 Promise 封装', start_date: '2026-10-29', end_date: '2026-11-04', done_rate: 10, task_done: 1, task_total: 10, overdue: 0, checkin_days: 1, goal_title: '' },
    ]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(() => localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' })));
  await p.goto('http://127.0.0.1:5199/student/schedule?tab=plan', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2400);
  const info = await p.evaluate(() => {
    const card = document.querySelector('.plan-page .card');
    return { bg: card ? getComputedStyle(card).backgroundColor : null, pl: card ? getComputedStyle(card).paddingLeft : null,
      cards: document.querySelectorAll('.plan-card').length };
  });
  console.log(JSON.stringify(info));
  await p.screenshot({ path: '_shots/v5-desk-plan.png', fullPage: false });
  await b.close();
})();
