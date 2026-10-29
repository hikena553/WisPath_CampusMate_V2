// 校验：v5 移动端改版不污染桌面端
const path = require('path');
const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
const MOCK = (url) => {
  if (url.includes('analysis')) return j({ stats: { total_courses: 12, total_credits: 38, avg_score: 84.5, avg_gpa: 3.42, highest_gpa: 3.8, lowest_gpa: 2.9, pass_rate: 100, gpa_rank: 8, total_students: 120 }, semester_gpa: [{ semester: '2025-1', gpa: 3.21 }, { semester: '2025-2', gpa: 3.42 }], course_type_stats: [], score_distribution: [], top_courses: [{ course_name: '高数', score: 92 }], weak_courses: [{ course_name: '英语听力', score: 71 }] });
  if (url.includes('streak')) return j({ current: 12, longest: 20, today_checked: true });
  if (url.includes('/leave/my')) return j([{ id: 1, student_id: 7, start_date: '2026-10-30', end_date: '2026-10-31', reason: '[事假] 家中事务', leave_type: 'personal', status: 'pending', reject_reason: null, return_confirmed: false, created_at: '2026-10-29T09:12:00', updated_at: '2026-10-29T09:12:00' }]);
  if (url.includes('/service/tickets')) return j([]);
  if (url.includes('agent/proactive')) return j({ actions: [], insight: '本周压力集中在周三前。' });
  if (url.includes('portfolio') || url.includes('project')) return j([]);
  return j([]);
};
const UA = () => localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' }));
let fail = 0;
const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fail++; };
(async () => {
  const b = await chromium.launch();
  const route = (p) => p.route(u => u.pathname.startsWith('/api/'), r => r.fulfill(MOCK(r.request().url())));

  // ---- 桌面端 1180：应保持原样 ----
  const d = await b.newPage({ viewport: { width: 1180, height: 860 } });
  await route(d); await d.addInitScript(UA);
  await d.goto('http://127.0.0.1:5199/student/schedule?tab=grades', { waitUntil: 'networkidle' });
  await d.waitForTimeout(2000);
  const dg = await d.evaluate(() => {
    const c = document.querySelector('.grades-view .analytics-card');
    const chart = document.querySelector('.grades-view .chart');
    return { cardBg: c ? getComputedStyle(c).backgroundColor : '', chartH: chart ? chart.getBoundingClientRect().height : 0 };
  });
  ok(dg.cardBg !== 'rgba(0, 0, 0, 0)' && dg.cardBg !== 'transparent', '桌面成绩卡仍是白卡: ' + dg.cardBg);
  ok(dg.chartH > 150, '桌面图表保持大尺寸: ' + Math.round(dg.chartH) + 'px');

  await d.goto('http://127.0.0.1:5199/student/schedule?tab=plan', { waitUntil: 'networkidle' });
  await d.waitForTimeout(2000);
  const dp = await d.evaluate(() => {
    const h = document.querySelector('.plan-hero');
    const bg = h ? getComputedStyle(h).backgroundImage : '';
    const card = document.querySelector('.plan-page .card');
    return { bg, cardBg: card ? getComputedStyle(card).backgroundColor : '', emptyIco: !!document.querySelector('.empty-ico') && getComputedStyle(document.querySelector('.empty-ico')).display !== 'none' };
  });
  ok(/rgb\(2[0-9]{2}|rgb\(1[0-9]{2}|gradient/.test(dp.bg) && !/15, 61, 46|28, 107, 74/.test(dp.bg), '桌面计划 hero 不是深绿森林色');
  ok(dp.cardBg !== 'rgba(0, 0, 0, 0)' && dp.cardBg !== 'transparent', '桌面计划卡仍是白卡: ' + dp.cardBg);

  await d.goto('http://127.0.0.1:5199/student/schedule?tab=service', { waitUntil: 'networkidle' });
  await d.waitForTimeout(2000);
  const ds = await d.evaluate(() => ({
    seg: !!document.querySelector('.sv-segment'),
    segVisible: document.querySelector('.sv-segment') ? getComputedStyle(document.querySelector('.sv-segment')).display : 'none',
    cta: !!document.querySelector('.sv-cta'),
    forms: document.querySelector('.sv-forms') ? getComputedStyle(document.querySelector('.sv-forms')).display : 'none',
    svCard: document.querySelector('.sv-card') ? getComputedStyle(document.querySelector('.sv-card')).backgroundColor : '',
  }));
  ok(ds.seg && ds.segVisible !== 'none', '桌面请假保留分段控件');
  ok(!ds.cta, '桌面请假无移动端「发起新申请」CTA');
  ok(ds.forms !== 'none', '桌面请假表单常驻可见');
  ok(ds.svCard && ds.svCard !== 'rgba(0, 0, 0, 0)', '桌面请假表单仍是白卡: ' + ds.svCard);

  // ---- 移动端 390：应使用 v5 ----
  const m = await b.newPage({ viewport: { width: 390, height: 844 } });
  await route(m); await m.addInitScript(UA);
  await m.goto('http://127.0.0.1:5199/student/schedule?tab=grades', { waitUntil: 'networkidle' });
  await m.waitForTimeout(2000);
  const mg = await m.evaluate(() => {
    const chart = document.querySelector('.grades-view .chart');
    const hero = document.querySelector('.grades-view .gr-hero');
    return { chartH: chart ? Math.round(chart.getBoundingClientRect().height) : 0, hero: !!hero };
  });
  ok(mg.hero, '移动成绩结论 hero 存在');
  ok(mg.chartH <= 95, '移动图表压缩 ≤95px: ' + mg.chartH + 'px');

  await m.goto('http://127.0.0.1:5199/student/schedule?tab=plan', { waitUntil: 'networkidle' });
  await m.waitForTimeout(2000);
  const mp = await m.evaluate(() => {
    const h = document.querySelector('.plan-hero');
    return { bg: h ? getComputedStyle(h).backgroundImage : '', emptyIco: document.querySelector('.empty-ico') ? getComputedStyle(document.querySelector('.empty-ico')).display : 'none' };
  });
  ok(/15, 61, 46|28, 107, 74/.test(mp.bg), '移动计划 hero 为深绿森林');
  ok(mp.emptyIco === 'none', '移动计划空态无插画');

  await m.goto('http://127.0.0.1:5199/student/schedule?tab=service', { waitUntil: 'networkidle' });
  await m.waitForTimeout(2000);
  const ms = await m.evaluate(() => ({
    cur: !!document.querySelector('.sv-current'),
    cta: !!document.querySelector('.sv-cta'),
    forms: document.querySelector('.sv-forms') ? getComputedStyle(document.querySelector('.sv-forms')).display : 'none',
    recs: document.querySelectorAll('.svr-row').length,
  }));
  ok(ms.cur && ms.cta, '移动请假为订单流（当前申请 + CTA）');
  ok(ms.forms === 'none', '移动请假表单默认收起');
  ok(ms.recs >= 1, '移动请假合并记录 ≥1 条: ' + ms.recs);

  console.log(fail ? `\nFAILURES: ${fail}` : '\nALL PASS');
  await b.close();
  process.exit(fail ? 1 : 0);
})();
