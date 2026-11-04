const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1720, height: 1200 }, deviceScaleFactor: 1.4 });
  const errs = [];
  p.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });

  const url = 'file:///' + path.resolve('D:/StudyNote/Mian02/prototypes/teacher-merged-redesign/index.html').replace(/\\/g, '/');
  await p.goto(url, { waitUntil: 'networkidle' });
  await p.waitForTimeout(600);

  const out = 'D:/StudyNote/Mian02/prototypes/teacher-merged-redesign/shots';
  fs.mkdirSync(out, { recursive: true });

  for (const id of ['phA', 'phB', 'phC']) {
    const el = await p.$('#' + id);
    await el.screenshot({ path: path.join(out, id + '-1.png') });
  }

  // A：点第 2 个 Tab（名单）
  await p.click('#phA .pg-tab:nth-child(2)');
  await p.waitForTimeout(420);
  let el = await p.$('#phA');
  await el.screenshot({ path: path.join(out, 'phA-2-roster.png') });

  // A：模拟拖拽到第 3 页（节奏）
  const vb = await (await p.$('#phA .pg-viewport')).boundingBox();
  await p.mouse.move(vb.x + vb.width * 0.75, vb.y + 200);
  await p.mouse.down();
  for (let i = 1; i <= 12; i++) {
    await p.mouse.move(vb.x + vb.width * 0.75 - i * 18, vb.y + 200);
    await p.waitForTimeout(12);
  }
  await p.mouse.up();
  await p.waitForTimeout(420);
  await el.screenshot({ path: path.join(out, 'phA-3-drag.png') });

  // B：点「看全部 42 人 ›」进二级子页，再返回
  await p.click('#phB [data-goto="1"]');
  await p.waitForTimeout(420);
  el = await p.$('#phB');
  await el.screenshot({ path: path.join(out, 'phB-2-subpage.png') });
  await p.click('#phB .tt-back[data-goto="0"]');
  await p.waitForTimeout(420);
  await el.screenshot({ path: path.join(out, 'phB-3-back.png') });

  // C：点第 2 段（班级）
  await p.click('#phC .pg-tab:nth-child(2)');
  await p.waitForTimeout(420);
  el = await p.$('#phC');
  await el.screenshot({ path: path.join(out, 'phC-2-class.png') });

  // 资讯：教师 / 学生
  el = await p.$('#phNews');
  await el.screenshot({ path: path.join(out, 'news-teacher.png') });
  await p.click('.role-switch button[data-role="student"]');
  await p.waitForTimeout(400);
  await el.screenshot({ path: path.join(out, 'news-student.png') });

  const diag = await p.evaluate(() => {
    const res = [];
    document.querySelectorAll('.screen').forEach(s => {
      const pages = Array.from(s.querySelectorAll('.pg-page'));
      res.push({
        id: s.id,
        pages: pages.length,
        overflowX: pages.map(pg => pg.scrollWidth - pg.clientWidth),
        tabs: s.querySelectorAll('.pg-tab').length,
        track: getComputedStyle(s.querySelector('.pg-track')).transition
      });
    });
    return res;
  });

  await p.screenshot({ path: path.join(out, 'full.png'), fullPage: true });
  console.log(JSON.stringify({ errs, diag }, null, 2));
  await b.close();
})();
