/**
 * v4 验证：
 *  1) 主页 A+B 融合：今日学业卡（时间轴 + CTA）+ Daylio 心情卡（打点/周柱/台账）
 *  2) 心情打点 POST /emotions/record (source=manual)，电话同步徽标
 *  3) 入口列表：情绪树洞 / 成长档案移除，学习计划为 tab
 *  4) 学习计划子页（PlanView embedded）+ 成长轨迹含成长记录
 *  5) 旧路由 /student/emotion 重定向
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
const RECORDS = Array.from({ length: 12 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - i);
  return { id: 1000 + i, type: 'honor', title: '成长记录 ' + (i + 1), description: '示例描述', record_date: d.toISOString().slice(0, 10), created_at: d.toISOString() };
});

// 情绪历史：3 天前一条电话识别（happy），今天无记录（等待打点）
// 注意 created_at 必须用「本地时间」字符串：前端 dayKey() 用本地日期对比，UTC ISO 会差一天
const localISO = (d) => {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};
const EMO = (() => {
  const arr = [];
  const mk = (daysAgo, emotion, label, source) => {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    d.setHours(9, 30, 0, 0);
    arr.push({ id: 500 + arr.length, emotion, label, confidence: 0.9, source, conversation_id: null, created_at: localISO(d) });
  };
  mk(3, 'happy', '开心', 'voice_call');
  mk(5, 'sad', '难过', 'manual');
  mk(6, 'neutral', '平静', 'voice_call');
  return arr;
})();

let moodPosted = null;
let MOOD_STORE = [...EMO];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const j = o => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  await p.route(u => u.pathname.startsWith('/api/'), async route => {
    const url = route.request().url();
    const method = route.request().method();
    if (url.includes('/emotions/record') && method === 'POST') {
      const body = route.request().postDataJSON() || {};
      const q = Object.fromEntries(new URL(url).searchParams.entries());
      moodPosted = { ...body, ...q };
      const rec = { id: 900 + MOOD_STORE.length, emotion: q.emotion || body.emotion || 'happy', label: { sad: '难过', fearful: '担忧', neutral: '平静', happy: '开心', surprised: '惊讶' }[q.emotion] || '开心', confidence: 1, source: q.source || 'manual', conversation_id: null, created_at: localISO(new Date()) };
      MOOD_STORE = [rec, ...MOOD_STORE];
      return route.fulfill(j(rec));
    }
    if (url.includes('/emotions/history')) { console.log('history:', JSON.stringify(MOOD_STORE.slice(0, 2).map(r => r.created_at + '|' + r.emotion))); return route.fulfill(j(MOOD_STORE)); }
    if (url.includes('/emotions/stats')) return route.fulfill(j({ total: MOOD_STORE.length, breakdown: [], trending: [] }));
    if (url.includes('/leave/my')) return route.fulfill(j([
      { id: 1, student_id: 7, start_date: '2026-10-30', end_date: '2026-10-31', reason: '[事假] 家中事务', leave_type: 'personal', status: 'pending', reject_reason: null, return_confirmed: false, created_at: '2026-10-29T09:12:00', updated_at: '2026-10-29T09:12:00' },
      { id: 2, student_id: 7, start_date: '2026-10-08', end_date: '2026-10-08', reason: '[病假] 感冒', leave_type: 'sick', status: 'approved', reject_reason: null, return_confirmed: true, created_at: '2026-10-07T10:00:00', updated_at: '2026-10-09T08:00:00' },
    ]));
    if (url.includes('/service/tickets')) return route.fulfill(j([
      { id: 11, type: 'certificate', title: '在读证明 × 1', content: '', status: 'completed', created_at: '2026-10-12T14:02:00', updated_at: '2026-10-13T16:00:00', applicant_name: '', applicant_no: '', applicant_college: '', form_data: null, attachments: null, review_comment: null, approver_name: null },
    ]));
    if (url.includes('/agent/proactive')) return route.fulfill(j({ actions: [
      { trigger: 'homework_due', student_id: 7, priority: 4, action_type: 'homework', title: '高数作业明天截止', content: '第 5 章习题还有 3 道未完成，建议今晚安排 40 分钟完成。', target_role: 'student' },
      { trigger: 'low_quiz', student_id: 7, priority: 3, action_type: 'review', title: '英语测验成绩偏低', content: '上周测验 62 分，低于班级均值，建议本周安排两次单词复盘。', target_role: 'student' },
      { trigger: 'streak', student_id: 7, priority: 2, action_type: 'encourage', title: '学习打卡连续 5 天', content: '保持节奏，本周继续打卡可解锁 7 天徽章。', target_role: 'student' },
    ], insight: '本周作业与测验压力集中在周三前，建议优先完成高数作业。' }));
    if (url.includes('/agent/daily-report')) return route.fulfill(j({
      date: '2026-10-29', greeting: '今天也要稳稳的',
      weather: { text: '晴', temp: '18~25℃', tip: '适合户外活动' },
      mood: { label: '平稳', emoji: '🙂', score: 3, at: '08:20', color: '#7c9cff' },
      fortune: { level: '中吉', score: 72, keyword: '专注', summary: '按计划推进会有回报。', lucky_color: '藏青', lucky_time: '上午' },
      sections: [{ key: 'task', title: '今日重点', items: ['高数第 5 章习题 3 道', '数据结构图遍历复习'] }],
      suggestions: [
        { trigger: 'homework_due', priority: 4, title: '高数作业明天截止', content: '第 5 章习题还有 3 道未完成，建议今晚安排 40 分钟。' },
        { trigger: 'low_quiz', priority: 3, title: '英语测验成绩偏低', content: '上周测验 62 分，建议本周安排两次单词复盘。' },
        { trigger: 'streak', priority: 2, title: '保持打卡节奏', content: '已连续 5 天，继续打卡可解锁 7 天徽章。' }
      ],
      generated_at: '2026-10-29T08:30:00'
    }));
    if (url.includes('/agent/insight')) return route.fulfill(j({ insight: '本周作业与测验压力集中在周三前。' }));
    if (url.includes('/skills') && method === 'PUT') return route.fulfill(j({}));
    if (url.includes('/growth/profile')) return route.fulfill(j(PROFILE));
    if (url.includes('/growth/records')) return route.fulfill(j(RECORDS));
    if (url.includes('/growth/project')) return route.fulfill(j([]));
    if (url.includes('/academic/analysis/')) return route.fulfill(j({ stats: {}, semester_gpa: [], score_distribution: [], course_type_stats: [] }));
    if (url.includes('/grade')) return route.fulfill(j([]));
    if (url.includes('/course') || url.includes('/schedule')) return route.fulfill(j([]));
    if (url.includes('/plan')) return route.fulfill(j([]));
    return route.fulfill(j([]));
  });
  await p.addInitScript(u => localStorage.setItem('campus_user', JSON.stringify(u)), USER);
  await p.goto('http://127.0.0.1:5199/student/schedule', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);

  const fails = [];
  const ok = (cond, msg) => { console.log((cond ? 'PASS ' : 'FAIL ') + msg); if (!cond) fails.push(msg); };

  // 1) 主页固定 Head + 今日学业卡
  const bar = await p.evaluate(() => {
    const b = document.querySelector('.home-bar');
    if (!b) return null;
    const r = b.getBoundingClientRect();
    return { top: Math.round(r.top), h: Math.round(r.height), pos: getComputedStyle(b).position, title: b.querySelector('.sp-title')?.textContent.trim() };
  });
  console.log('主页 Head:', JSON.stringify(bar));
  ok(bar && bar.top === 0 && bar.h === 48 && bar.pos === 'fixed' && bar.title === '学业中心', '主页 48px fixed Head「学业中心」');

  const tc = await p.evaluate(() => {
    const card = document.querySelector('.gd-today-card');
    if (!card) return null;
    return {
      cap: card.querySelector('.gd-tc-cap')?.textContent.trim(),
      cta: card.querySelector('.gd-tc-cta')?.textContent.trim(),
      heroGone: !document.querySelector('.gd-today-line, .gd-metrics'),
    };
  });
  console.log('今日学业卡:', JSON.stringify(tc));
  ok(tc && tc.cap === '今日学业', '今日学业卡存在');
  ok(tc && tc.cta === '开始今天的学习', '主 CTA 文案正确');
  ok(tc && tc.heroGone, '旧 Hero（一句话+四数字）已移除');

  // 去卡片化：主页不再有 .gd-card 结构；五维已删除
  const flat = await p.evaluate(() => ({
    cards: document.querySelectorAll('.growth-dashboard .gd-card').length,
    dims: !!document.querySelector('.growth-dashboard'),
    dimsText: document.body.textContent.includes('五维成长'),
    flats: document.querySelectorAll('.growth-dashboard .gd-flat').length,
  }));
  ok(flat.cards === 0, '主页已无卡片结构（gd-card=0）: ' + JSON.stringify(flat));
  ok(!flat.dimsText, '五维成长已删除');
  ok(flat.flats >= 3, '扁平分区存在（心情/AI/更多）');
  const aiEntry = await p.evaluate(() => ({
    entry: !!document.querySelector('.gd-ai-entry'),
    title: document.querySelector('.gd-ai-entry-title')?.textContent.trim(),
  }));
  ok(aiEntry.entry && /AI .*(近况分析|今日报告)/.test(aiEntry.title || ''), 'AI 压缩为单行入口（gd-ai-entry）：' + aiEntry.title);
  await p.screenshot({ path: path.join(OUT, 'v4-home-01.png') });

  // 2) 心情卡
  const mood = await p.evaluate(() => ({
    dots: document.querySelectorAll('.gd-mood-face').length,
    sync: !!document.querySelector('.gd-mood-sync'),
    bars: document.querySelectorAll('.gd-mood-col').length,
    label: document.querySelector('.gd-mood-label')?.textContent.trim(),
  }));
  console.log('心情卡:', JSON.stringify(mood));
  ok(mood.dots === 5, '5 个心情表情');
  ok(mood.bars === 7, '本周 7 天迷你柱');
  ok(!mood.sync, '今天无电话记录时不显示同步徽标');
  ok(mood.label === '点一下，记下此刻的心情', '未打点默认提示语');

  // 打点：点第 4 个（不错）
  await p.locator('.gd-mood-face').nth(3).click();
  await p.waitForTimeout(900);
  console.log('打点 payload:', JSON.stringify(moodPosted));
  ok(moodPosted && moodPosted.emotion === 'happy' && moodPosted.source === 'manual', '打点 POST source=manual emotion=happy');
  const mood2 = await p.evaluate(() => ({
    label: document.querySelector('.gd-mood-label')?.textContent.trim(),
    active: document.querySelectorAll('.gd-mood-face.is-active').length,
  }));
  console.log('打点后状态:', JSON.stringify(mood2));
  ok(mood2.label.includes('不错') && mood2.active === 1, '打点后选中态与文案更新');
  await p.screenshot({ path: path.join(OUT, 'v4-home-02-mood.png') });

  // 台账弹窗
  await p.locator('.gd-mood-ledger-btn').click();
  await p.waitForTimeout(700);
  const ledger = await p.evaluate(() => ({
    visible: !!document.querySelector('.gd-ledger-dialog'),
    cells: document.querySelectorAll('.gd-ledger-grid .gd-ledger-cell').length,
    rows: document.querySelectorAll('.gd-ledger-row').length,
  }));
  ok(ledger.visible && ledger.cells === 30, '台账弹窗 30 天点阵: ' + JSON.stringify(ledger));
  await p.screenshot({ path: path.join(OUT, 'v4-home-03-ledger.png') });
  await p.keyboard.press('Escape');
  await p.waitForTimeout(500);

  // 3) 更多宫格（v4.2：彩色图标宫格替代 iOS 行列表）
  const tiles = await p.evaluate(() => [...document.querySelectorAll('.gd-tile-label')].map(e => e.textContent.trim()));
  console.log('更多宫格:', tiles.join(' / '));
  ok(tiles.length >= 5 && !tiles.includes('我的申请'), '更多入口 ≥5 且不含「我的申请」（已并入请假服务）');
  ok(await p.evaluate(() => !!document.querySelector('.gd-tile-track')), '更多为横向滑动入口（v4.3）');
  ok(!tiles.includes('情绪树洞') && !tiles.includes('成长档案'), '情绪树洞/成长档案入口已移除');
  ok(tiles.includes('学习计划') && tiles.includes('请假服务'), '学习计划/请假服务入口在');
  ok(await p.evaluate(() => document.querySelectorAll('.gd-link-row').length) === 0, '旧 iOS 行列表已移除');

  // 4) 学习计划 tab（embedded PlanView）
  await p.locator('.gd-tile', { hasText: '学习计划' }).first().click();
  await p.waitForTimeout(1600);
  const plan = await p.evaluate(() => {
    const bar = document.querySelector('.subpage-bar');
    const page = document.querySelector('.plan-page.is-embedded');
    return {
      title: bar?.querySelector('.sp-title')?.textContent.trim(),
      sub: bar?.querySelector('.sp-sub')?.textContent.trim(),
      embedded: !!page,
      ownHeader: !!page?.querySelector('.subpage-header, .sp-bar'),
      hero: !!page?.querySelector('.plan-hero'),
    };
  });
  console.log('学习计划 tab:', JSON.stringify(plan));
  ok(plan.title === '学习计划' && plan.sub === '目标 · 关卡 · 打卡', '计划子页 Head 标题/副标题正确');
  ok(plan.embedded, 'PlanView 以 embedded 模式渲染');
  ok(!plan.ownHeader, 'PlanView 自带顶栏已隐藏');
  ok(plan.hero, '计划页主视觉保留');
  await p.screenshot({ path: path.join(OUT, 'v4-plan.png') });

  // 成长轨迹含成长记录（档案合并）：直接带 tab 参数进入（返回键交互由 v31 脚本覆盖）
  await p.goto('http://127.0.0.1:5199/student/schedule?tab=growth', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2000);
  const growth = await p.evaluate(() => {
    const bar = document.querySelector('.subpage-bar');
    return { title: bar?.querySelector('.sp-title')?.textContent.trim(), records: !!document.querySelector('.gv-records') };
  });
  console.log('成长轨迹:', JSON.stringify(growth));
  ok(growth.title === '成长轨迹' && growth.records, '成长子页含成长记录（档案已合并）');
  await p.screenshot({ path: path.join(OUT, 'v4-growth.png') });

  // 5) AI 分析子页（v4.2）
  await p.goto('http://127.0.0.1:5199/student/schedule?tab=ai', { waitUntil: 'networkidle' });
  await p.waitForTimeout(1800);
  const aiPage = await p.evaluate(() => {
    const bar = document.querySelector('.subpage-bar');
    return {
      title: bar?.querySelector('.sp-title')?.textContent.trim(),
      sub: bar?.querySelector('.sp-sub')?.textContent.trim(),
      dot: !!bar?.querySelector('.sp-dot'),
      actions: document.querySelectorAll('.ai-action').length,
      addBtns: document.querySelectorAll('.ai-add-btn').length,
    };
  });
  console.log('AI 子页:', JSON.stringify(aiPage));
  ok(/AI 分析|今日报告/.test(aiPage.title || '') && aiPage.sub === '近况分析 · 计划生成', 'AI 子页 Head 标题/副标题正确：' + aiPage.title + ' / ' + aiPage.sub);
  ok(aiPage.dot, '子页 Head 带识别色 dot');
  ok(aiPage.actions > 0 && aiPage.addBtns === aiPage.actions, '近况分析列表 + 加入学习计划按钮齐全');
  await p.screenshot({ path: path.join(OUT, 'v4-ai.png') });

  // 5.5) 请假服务 v5：订单流 + 申请记录合并
  await p.goto('http://127.0.0.1:5199/student/schedule?tab=service', { waitUntil: 'networkidle' });
  await p.waitForTimeout(1800);
  const svc = await p.evaluate(() => ({
    current: document.querySelector('.sv-current .svc-title')?.textContent.trim(),
    cta: !!document.querySelector('.sv-cta'),
    formsHidden: getComputedStyle(document.querySelector('.sv-forms')).display === 'none',
    records: document.querySelectorAll('.svr-row').length,
    stOk: document.querySelectorAll('.svr-st.ok').length,
  }));
  console.log('请假服务 v5:', JSON.stringify(svc));
  ok(svc.current && svc.current.includes('2026-10-30'), '当前进行中的申请卡正确');
  ok(svc.cta && svc.formsHidden, '表单收进「发起新申请」二级');
  ok(svc.records === 3 && svc.stOk >= 2, '请假/证明申请记录合并显示（3 条）');
  await p.screenshot({ path: path.join(OUT, 'v5-service.png') });

  // 6) 旧路由重定向
  await p.goto('http://127.0.0.1:5199/student/emotion', { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  const redirected = p.url().includes('/student/schedule');
  ok(redirected, '情绪树洞旧路由重定向到学业中心');

  console.log(fails.length ? '\nFAILURES: ' + fails.length : '\nALL PASS');
  process.exit(fails.length ? 1 : 0);
})();
