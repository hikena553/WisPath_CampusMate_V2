const path = require('path');
const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await p.route(u => u.pathname.startsWith('/api/'), route => {
    const url = route.request().url();
    if (url.includes('project')) return route.fulfill(j([
      { id: 1, project_name: 'bluebird-agent', tech_stack: 'TypeScript, FastAPI', my_role: '队长', is_team: true, start_date: '2026-09-01', end_date: null, team_members: '', description: 'AI 值周助手：语音情绪识别 + 主动发现引擎，Vue3 + FastAPI。', project_link: '', attachment_url: '' },
      { id: 2, project_name: 'timetable-v4', tech_stack: 'Vue, Vite', my_role: '', is_team: false, start_date: '2026-10-01', end_date: null, team_members: '', description: '移动端课程表重设计：48px 固定 Head、扁平分区、心情打点。', project_link: '', attachment_url: '' },
    ]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(() => localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' })));
  await p.goto('http://127.0.0.1:5199/student/portfolio', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);
  await p.screenshot({ path: path.join('_shots', 'v5-live-portfolio.png') });
  console.log('ok');
  await b.close();
})();
