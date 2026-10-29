/**
 * v3.1 验证：
 *  1) 请假服务子页可进入、三段切换、Head 吸顶
 *  2) 技能与兴趣卡片高度压缩
 *  3) 驾驶舱入口含「请假服务」
 *  4) 改名后无「驾驶舱」残留（用户可见文案）
 */
const { chromium } = require('playwright');
const path = require('path');
const OUT = path.join(__dirname, '_shots');

const USER = { id: 1, role: 'student', name: '测试同学', username: '2024001', college: '计算机学院' };
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
  skills: ['编程开发', '数据分析'],
  interests: ['运动'],
};
const RECORDS = Array.from({ length: 24 }, (_, i) => {
  const d = new Date(Date.UTC(2026, 9, 28));
  d.setUTCDate(d.getUTCDate() - i);
  return { id: 1000 + i, type: 'honor', title: '成长记录 ' + (i + 1), description: '示例描述', record_date: d.toISOString().slice(0, 10), created_at: d.toISOString() };
});
let leavePosted = null, ticketPosted = null;

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const j = o => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  await p.route(u => u.pathname.startsWith('/api/'), async route => {
    const url = route.request().url();
    const method = route.request().method();
    if (url.includes('/leave') && method === 'POST') { leavePosted = route.request().postDataJSON(); return route.fulfill(j({ id: 9 })); }
    if (url.includes('/ticket') && method === 'POST') { ticketPosted = route.request().postDataJSON(); return route.fulfill(j({ id: 9 })); }
    if (url.includes('/skills') && method === 'PUT') return route.fulfill(j({}));
    if (url.includes('/growth/profile')) return route.fulfill(j(PROFILE));
    if (url.includes('/growth/records')) return route.fulfill(j(RECORDS));
    if (url.includes('/growth/project')) return route.fulfill(j([]));
    if (url.includes('/academic/analysis/')) return route.fulfill(j({ stats: {}, semester_gpa: [], score_distribution: [], course_type_stats: [] }));
    if (url.includes('/grade')) return route.fulfill(j([]));
    if (url.includes('/course') || url.includes('/schedule')) return route.fulfill(j([]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(u => localStorage.setItem('campus_user', JSON.stringify(u)), USER);
  await p.goto('http://127.0.0.1:5199/student/schedule', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);

  const fails = [];
  const ok = (cond, msg) => { console.log((cond ? 'PASS ' : 'FAIL ') + msg); if (!cond) fails.push(msg); };

  // 3) 驾驶舱入口
  const cellTexts = await p.evaluate(() => [...document.querySelectorAll('.gd-cell-label')].map(e => e.textContent.trim()));
  console.log('入口列表:', cellTexts.join(' / '));
  ok(cellTexts.includes('请假服务'), '驾驶舱含「请假服务」入口');

  // 进入请假服务
  await p.locator('.gd-cell', { hasText: '请假服务' }).first().click();
  await p.waitForTimeout(1400);

  const head = await p.evaluate(() => {
    const bar = document.querySelector('.subpage-bar');
    const r = bar.getBoundingClientRect();
    return { top: Math.round(r.top), h: Math.round(r.height), pos: getComputedStyle(bar).position, title: bar.querySelector('.sp-title').textContent.trim(), sub: bar.querySelector('.sp-sub').textContent.trim() };
  });
  console.log('服务子页 Head:', JSON.stringify(head));
  ok(head.title === '请假服务', '顶栏标题为「请假服务」');
  ok(head.sub === '请假 · 证明 · 项目', '顶栏副标题正确');
  ok(head.top === 0 && head.h === 48 && head.pos === 'fixed', 'Head fixed + 48px 吸顶');
  await p.screenshot({ path: path.join(OUT, 'v31-service-01.png') });

  // 分段切换
  const segs = await p.evaluate(() => [...document.querySelectorAll('.sv-seg-item')].map(e => e.textContent.trim()));
  ok(segs.join(',') === '请假,证明,项目', '分段控制三项: ' + segs.join(','));
  await p.locator('.sv-seg-item', { hasText: '证明' }).click();
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(OUT, 'v31-service-02-cert.png') });
  await p.locator('.sv-seg-item', { hasText: '项目' }).click();
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(OUT, 'v31-service-03-project.png') });

  // 提交请假（切回 + 填表）
  await p.locator('.sv-seg-item', { hasText: '请假' }).click();
  await p.waitForTimeout(300);
  await p.locator('.sv-card:visible .el-select').first().click().catch(e => console.log('select open fail', e.message.slice(0,80)));
  await p.waitForTimeout(400);
  await p.locator('.el-select-dropdown__item', { hasText: '病假' }).first().click().catch(e => console.log('opt fail', e.message.slice(0,80)));
  await p.waitForTimeout(200);
  const dp = p.locator('.sv-card:visible .el-date-editor input'); await dp.nth(0).fill('2026-10-29'); await dp.nth(0).press('Enter'); await dp.nth(1).fill('2026-10-31'); await dp.nth(1).press('Enter');
  await p.locator('.sv-card:visible textarea').fill('身体不适需要休息');
  await p.waitForTimeout(200);
  await p.locator('.sv-card:visible .sv-submit').click();
  await p.waitForTimeout(900);
  ok(!!leavePosted, '请假表单提交成功（API 收到 POST）');
  await p.waitForTimeout(2600);
  if (leavePosted) console.log('  payload:', JSON.stringify(leavePosted));

  // 吸顶复测
  await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 400; });
  await p.waitForTimeout(350);
  const head2 = await p.evaluate(() => {
    const bar = document.querySelector('.subpage-bar');
    const r = bar.getBoundingClientRect();
    const topEl = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return { top: Math.round(r.top), onTop: topEl === bar || bar.contains(topEl) };
  });
  ok(head2.top === 0 && head2.onTop, '滚动 400px 后顶栏仍固定且不被覆盖');

  // 返回主页 → 成长页 → 技能与兴趣高度
  await p.click('.sp-back');
  await p.waitForTimeout(1200);
  await p.getByRole('button', { name: '成长轨迹' }).first().click();
  await p.waitForTimeout(1500);
  const skillsH = await p.evaluate(() => {
    const cards = [...document.querySelectorAll('.growth-view .gv-card')];
    const sc = cards.find(c => c.querySelector('.skills-card, .skills-body'));
    if (!sc) return null;
    return { h: Math.round(sc.getBoundingClientRect().height), text: sc.querySelector('.gv-card-title').textContent.trim() };
  });
  console.log('技能与兴趣卡片:', JSON.stringify(skillsH));
  ok(skillsH && skillsH.h < 140, '技能与兴趣卡片高度 < 140px（压缩后）');
  await p.screenshot({ path: path.join(OUT, 'v31-growth-skills.png') });

  // 弹窗编辑可用
  await p.locator('.skills-card .gv-text-btn').click();
  await p.waitForTimeout(500);
  const dlgVisible = await p.evaluate(() => !!document.querySelector('.skills-edit-dialog .skills-preset-tag'));
  ok(dlgVisible, '编辑弹窗含预设标签');
  await p.screenshot({ path: path.join(OUT, 'v31-skills-dialog.png') });
  await p.locator('.skills-edit-dialog .el-dialog__headerbtn').click();

  // 残留文案检查
  const leftover = await p.evaluate(() => document.body.innerText.includes('驾驶舱'));
  ok(!leftover, '页面无「驾驶舱」残留文案');

  // 顶栏改名
  await p.evaluate(() => { const s = document.querySelector('.content-row'); if (s) s.scrollTop = 0; });
  await p.click('.sp-back');
  await p.waitForTimeout(1200);
  const tabLabel = await p.evaluate(() => {
    const el = [...document.querySelectorAll('.tab-label, .tabbar-item, .mb-tab')].find(e => e.textContent.includes('学业中心'));
    return el ? el.textContent.trim() : null;
  });
  console.log('tabbar 学业中心:', tabLabel);
  await p.screenshot({ path: path.join(OUT, 'v31-home.png') });

  console.log('\n===== 总结 =====');
  console.log(fails.length ? 'FAIL: ' + fails.join('; ') : '全部 PASS');
  await b.close();
})();
