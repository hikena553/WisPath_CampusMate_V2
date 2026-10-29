// v5 子页方案截图：按 section 输出 PNG
const path = require('path');
const { chromium } = require('playwright');
const OUT = path.join(__dirname, '_shots');
const SECS = ['sec-growth', 'sec-service', 'sec-plan', 'sec-portfolio', 'sec-tickets'];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 });
  await p.goto('file:///' + path.join(__dirname, 'V5-SUBPAGE-PROPOSAL.html').replace(/\\/g, '/'));
  await p.waitForTimeout(800);
  for (const id of SECS) {
    const el = p.locator('#' + id);
    await el.scrollIntoViewIfNeeded();
    await p.waitForTimeout(200);
    await el.screenshot({ path: path.join(OUT, 'v5-' + id.replace('sec-', '') + '.png') });
    console.log('shot', id);
  }
  await b.close();
})();
