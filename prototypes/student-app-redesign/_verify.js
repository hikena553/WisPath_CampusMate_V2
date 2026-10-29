const { chromium } = require('D:/StudyNote/Mian02/node_modules/playwright');
const URL = 'file:///D:/StudyNote/Mian02/prototypes/student-app-redesign/index.html';
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  await p.goto(URL); await p.waitForTimeout(1000);

  const r = await p.evaluate(() => {
    const out = [];
    const q = (s) => document.querySelector(s);
    const cs = (el, prop) => el ? getComputedStyle(el)[prop] : '(无元素)';

    // 1. 文档说：卡片全站只有一档阴影
    const cards = [...document.querySelectorAll('.card')];
    const shadows = [...new Set(cards.map(c => getComputedStyle(c).boxShadow))];
    out.push(['卡片数量', cards.length]);
    out.push(['卡片阴影种类', shadows.length + ' 种: ' + shadows.join(' | ')]);

    // 2. 文档说：--accent 只出现在 2 处小面积
    const accentUse = [];
    const walk = (el) => {
      const s = getComputedStyle(el);
      ['color','backgroundColor','backgroundImage','borderLeftColor','borderTopColor'].forEach(pr => {
        const v = s[pr];
        if (v && (v.includes('26, 79, 214') || v.includes('25, 79, 214') || v.includes('#1a4fd6'))) {
          const rect = el.getBoundingClientRect();
          accentUse.push({ cls: el.className || el.tagName, prop: pr, area: Math.round(rect.width) + 'x' + Math.round(rect.height) });
        }
      });
      [...el.children].forEach(walk);
    };
    walk(document.getElementById('scr-home'));
    out.push(['--accent 使用处', accentUse.length]);
    accentUse.forEach(u => out.push(['   ', u.cls + ' / ' + u.prop + ' / ' + u.area]));

    // 3. 文档说：进度条全灰，仅最低项赭红
    const bars = [...document.querySelectorAll('.dim-row')].map(row => ({
      name: row.querySelector('.dim-name')?.textContent.trim(),
      fill: getComputedStyle(row.querySelector('.dim-track > i')).backgroundColor,
      low: row.classList.contains('is-low'),
    }));
    out.push(['五维条', JSON.stringify(bars, null, 0)]);

    // 4. 文档说：.tab 选中 近黑 + 2px 短线
    const activeTab = q('.tab.active');
    out.push(['选中页签色', cs(activeTab, 'color')]);
    out.push(['选中页签线', activeTab ? getComputedStyle(activeTab, '::after').backgroundColor + ' / h=' + getComputedStyle(activeTab, '::after').height : '-']);

    // 5. 文档说：fn-cell 两列、图标 16px、灰
    const fn = q('.fn-cell');
    out.push(['fn-cell 存在', !!fn]);
    if (fn) {
      out.push(['fn-cell 图标色', cs(fn.querySelector('svg'), 'color')]);
      out.push(['fn-cell 图标尺寸', cs(fn.querySelector('svg'), 'width')]);
      out.push(['fn-cell 布局', getComputedStyle(q('.fn-list')).gridTemplateColumns]);
    }

    // 6. 文档说：today-line em 是标记笔
    const em = q('#todayLine em');
    out.push(['标记笔', em ? cs(em, 'backgroundImage') : '(无 em)']);

    // 7. 雷达图颜色
    const rl = q('.radar-legend-row');
    out.push(['雷达 legend 存在', !!rl]);

    return out;
  });

  r.forEach(([k, v]) => console.log(String(k).padEnd(18), v));
  await b.close();
})();
