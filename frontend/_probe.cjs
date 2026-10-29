const { chromium } = require('playwright');
const j = (o) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1180, height: 820 } });
  await p.route(u => u.pathname.startsWith('/api/'), route => route.fulfill(j({ current: 12, longest: 20, today_checked: true })));
  await p.addInitScript(() => localStorage.setItem('campus_user', JSON.stringify({ id: 7, username: '2024001', real_name: '测试同学', role: 'student', college: '计算机学院' })));
  await p.goto('http://127.0.0.1:5199/student/schedule?tab=plan', { waitUntil: 'networkidle' });
  await p.waitForTimeout(2200);
  const info = await p.evaluate(() => {
    const wrap = document.querySelector('.plan-view-wrap');
    const hero = document.querySelector('.plan-hero');
    return {
      wrap: !!wrap, hero: !!hero,
      wrapClass: wrap?.className,
      heroBg: hero ? getComputedStyle(hero).backgroundImage.slice(0, 60) : null,
      heroParentChain: (() => { let el = hero, out = []; for (let i = 0; i < 4 && el; i++) { out.push(el.className); el = el.parentElement; } return out; })(),
    };
  });
  console.log(JSON.stringify(info, null, 1));
  await b.close();
})();
