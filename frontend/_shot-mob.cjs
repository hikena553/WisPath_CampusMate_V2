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
    if (url.includes('/leave/my')) return route.fulfill(j([{ id: 1, student_id: 7, start_date: '2026-10-30', end_date: '2026-10-31', reason: '[事假] 家中事务', leave_type: 'personal', status: 'pending', reject_reason: null, return_confirmed: false, created_at: '2026-10-29T09:12:00', updated_at: '2026-10-29T09:12:00' }]));
    if (url.includes('/service/tickets')) return route.fulfill(j([{ id: 11, type: 'certificate', title: '在读证明 × 1', content: '', status: 'completed', created_at: '2026-10-12T14:02:00', updated_at: '2026-10-13T16:00:00', applicant_name: '', applicant_no: '', applicant_college: '', form_data: null, attachments: null, review_comment: null, approver_name: null }]));
    if (url.includes('agent/proactive')) return route.fulfill(j({ actions: [{ trigger: 'a', student_id: 7, priority: 4, action_type: 'homework', title: '高数作业明天截止', content: '第 5 章习题还有 3 道未完成。', target_role: 'student' }], insight: '本周压力集中在周三前。' }));
    if (url.includes('portfolio') || url.includes('project')) return route.fulfill(j([{ id: 1, project_name: 'bluebird-agent', tech_stack: 'TypeScript, FastAPI', my_role: '队长', is_team: true, start_date: '2026-09-01', end_date: null, team_members: '', description: 'AI 值周助手：语音情绪识别 + 主动发现引擎。', project_link: '', attachment_url: '' }]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(() => localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' })));
  for (const [u, n] of [['/student/schedule?tab=service', 'm-service'], ['/student/schedule?tab=grades', 'm-grades'], ['/student/schedule?tab=plan', 'm-plan'], ['/student/schedule?tab=ai', 'm-ai'], ['/student/portfolio', 'm-portfolio']]) {
    await p.goto('http://127.0.0.1:5199' + u, { waitUntil: 'networkidle' });
    await p.waitForTimeout(2400);
    await p.screenshot({ path: path.join('_shots', n + '.png') });
    console.log('shot', n);
  }
  await b.close();
})();
