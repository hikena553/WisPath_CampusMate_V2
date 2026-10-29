const { chromium } = require('D:/StudyNote/Mian02/node_modules/playwright');
const path = require('path');
const OUT = 'D:/StudyNote/Mian02/frontend/_shots';
const BASE = 'http://localhost:5199';
const USER = { id: 9001, role: 'student', username: '予安', real_name: '予安' };

const PROFILE = {
  total_score: 78.4,
  radar: [
    { name: '学术素养', value: 86.2 }, { name: '创新能力', value: 71.5 },
    { name: '实践能力', value: 80.1 }, { name: '社交素养', value: 74.8 },
    { name: '综合素质', value: 79.3 },
  ],
  stats_by_type: [{ name: '荣誉', value: 6 }, { name: '竞赛', value: 3 }, { name: '实践', value: 5 }],
  monthly_trend: [
    { month: '5月', count: 4, type: '荣誉' }, { month: '6月', count: 7, type: '竞赛' },
    { month: '9月', count: 5, type: '荣誉' }, { month: '10月', count: 9, type: '竞赛' },
  ],
  skills: ['Python', 'Vue', '数据分析'], interests: ['算法', '开源'],
  total_records: 47, total_skills: 12,
  gpa_trend: [{ semester: '大二上', gpa: 3.42 }, { semester: '大二下', gpa: 3.52 }],
};
const GRADES = {
  stats: { total_courses: 12, total_credits: 68.5, avg_score: 84.2, avg_gpa: 3.52, highest_gpa: 3.9, lowest_gpa: 3.1, pass_rate: 100, gpa_rank: 12, total_students: 46 },
  courses: [
    { name: '数据结构与算法', type: '专业核心', credit: 4, score: 92, gpa: 4.2 },
    { name: '数据库原理', type: '专业核心', credit: 3.5, score: 88, gpa: 3.8 },
    { name: '软件工程导论', type: '专业核心', credit: 3, score: 85, gpa: 3.5 },
    { name: '大学英语（四）', type: '公共必修', credit: 3, score: 78, gpa: 2.8 },
    { name: '概率论与数理统计', type: '学科基础', credit: 4, score: 74, gpa: 2.4 },
  ],
  course_type_stats: [{ name: '专业核心', avg_score: 88 }, { name: '学科基础', avg_score: 74 }],
  trend: [{ term: '大一上', gpa: 3.2 }, { term: '大一下', gpa: 3.35 }, { term: '大二上', gpa: 3.42 }, { term: '大二下', gpa: 3.52 }],
};
const SCHEDULE = [
  { id: 1, name: '数据库原理', teacher: '孙晓月', location: '实验楼 B201', day_of_week: 1, start_period: 1, end_period: 2, week_start: 1, week_end: 16 },
  { id: 2, name: '数据结构与算法', teacher: '王成林', location: '实验楼 B302', day_of_week: 1, start_period: 3, end_period: 4, week_start: 1, week_end: 16 },
  { id: 3, name: '大学英语（四）', teacher: '周敏', location: '教学楼 A205', day_of_week: 2, start_period: 1, end_period: 2, week_start: 1, week_end: 16 },
  { id: 4, name: '体育（羽毛球）', teacher: '张海涛', location: '体育馆', day_of_week: 3, start_period: 3, end_period: 4, week_start: 1, week_end: 16 },
  { id: 5, name: '软件工程导论', teacher: '李建国', location: '教学楼 A312', day_of_week: 4, start_period: 5, end_period: 6, week_start: 1, week_end: 16 },
];

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push('ERR ' + e.message));

  await p.route(u => u.pathname.startsWith('/api/'), (r) => {
    const url = r.request().url();
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(d) });
    if (url.includes('/auth/me')) return j(USER);
    if (url.includes('/growth/profile')) return j(PROFILE);
    if (url.includes('/grade')) return j(GRADES);
    if (url.includes('/course') || url.includes('/schedule')) return j(SCHEDULE);
    if (url.includes('/plan/today')) return j([]);
    if (url.includes('/agent/proactive')) return j({ insight: '', actions: [] });
    return j([]);
  });
  await p.addInitScript(u => localStorage.setItem('campus_user', JSON.stringify(u)), USER);
  await p.goto(BASE + '/student/schedule', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);
  await p.screenshot({ path: path.join(OUT, 'before-home.png') });

  // 进入各子页
  for (const [key, name] of [['grades', 'grades'], ['growth', 'growth'], ['schedule', 'schedule']]) {
    const cell = await p.evaluateHandle((k) => {
      const btns = [...document.querySelectorAll('.gd-cell')];
      const map = { grades: 0, growth: 1 };
      return btns[map[k]];
    }, key);
    if (key === 'schedule') {
      // 课程表从「下一节」摘要进入
      await p.click('.gd-today-sub');
    } else {
      await cell.asElement().click();
    }
    await p.waitForTimeout(1500);
    await p.screenshot({ path: path.join(OUT, `before-${name}.png`) });

    // 记录头部高度与是否随滚动消失
    const head = await p.evaluate(() => {
      const bar = document.querySelector('.subpage-bar');
      if (!bar) return { found: false };
      const r = bar.getBoundingClientRect();
      return { found: true, top: Math.round(r.top), height: Math.round(r.height), position: getComputedStyle(bar).position };
    });
    console.log(name, '头部:', JSON.stringify(head));

    // 滚到底再看头部是否还在原位
    await p.evaluate(() => {
      const s = document.querySelector('.content-row') || document.querySelector('.content-main')?.parentElement;
      if (s) s.scrollTop = 600;
    });
    await p.waitForTimeout(500);
    const head2 = await p.evaluate(() => {
      const bar = document.querySelector('.subpage-bar');
      if (!bar) return { found: false };
      return { top: Math.round(bar.getBoundingClientRect().top) };
    });
    console.log(name, '滚动 600 后头部 top:', head2.top);
    await p.click('.subpage-bar');
    await p.waitForTimeout(1200);
  }

  console.log(errs.length ? errs.join('\n') : 'NO ERRORS');
  await b.close();
})();
