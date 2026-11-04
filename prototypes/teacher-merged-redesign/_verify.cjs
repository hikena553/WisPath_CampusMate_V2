// 版式 B 落地验收：教师端移动端 首页(资讯) → 工作台首屏 → 名单二级子页
const { chromium } = require('playwright')
const path = require('path')
const fs = require('fs')

const OUT = path.join(__dirname, 'shots')
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true })

;(async () => {
  const b = await chromium.launch({ channel: 'msedge', headless: true })
  const c = await b.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
  })
  const p = await c.newPage()
  const errs = []
  p.on('pageerror', (e) => errs.push('PAGEERROR: ' + e.message))
  p.on('console', (m) => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text().slice(0, 200)) })

  // ---- 登录（教师 t1001） ----
  await p.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' })
  await p.getByText('开始使用', { exact: false }).first().click({ timeout: 5000 }).catch(() => {})
  await p.waitForTimeout(800)
  await p.fill('input[placeholder="学号 / 工号"]', 't1001')
  await p.fill('input[placeholder="密码"]', '123456')
  await p.check('input[type="checkbox"]').catch(() => {})
  await p.click('button:has-text("登录")')
  await p.waitForTimeout(4500)
  console.log('URL:', p.url())

  // ---- 1) 首页 = 校园资讯 ----
  await p.waitForTimeout(1200)
  const home = await p.evaluate(() => ({
    hasCampus: !!document.querySelector('.campus-page'),
    appbarTitle: (document.querySelector('.campus-appbar h1') || {}).textContent || null,
    hasPublish: !!document.querySelector('.campus-teacher-publish'),
    hasForumBtn: !!document.querySelector('.appbar-btn--dot'),
    bodyText: document.body.innerText.slice(0, 160).replace(/\n/g, ' | '),
  }))
  console.log('HOME:', JSON.stringify(home))
  await p.screenshot({ path: path.join(OUT, 'b1-home-campus.png') })

  // ---- 2) 工作台首屏 ----
  await p.getByText('工作台', { exact: true }).first().click()
  await p.waitForTimeout(2500)
  const board = await p.evaluate(() => ({
    head: (document.querySelector('.app-head-title') || {}).textContent || null,
    hasBoard: !!document.querySelector('.home-board'),
    hasTodayFocus: !!document.querySelector('.home-board .tf-card, .home-board [class*="tf-"]'),
    hasFeatures: !!document.querySelector('.home-features'),
    hasRhythm: !!document.querySelector('.workbench-section'),
    hasRosterEntry: !!document.querySelector('.wb-entry'),
    entriesText: (document.querySelector('.wb-entries') || {}).innerText || null,
  }))
  console.log('BOARD:', JSON.stringify(board))
  await p.screenshot({ path: path.join(OUT, 'b2-workbench.png'), fullPage: true })

  // ---- 3) 名单二级子页 ----
  await p.locator('.wb-entry').first().click()
  await p.waitForTimeout(900)
  const sub = await p.evaluate(() => {
    const el = document.querySelector('.wb-subpage')
    if (!el) return { open: false }
    const cs = getComputedStyle(el)
    return {
      open: true,
      title: (el.querySelector('.wb-subpage-title') || {}).textContent || null,
      count: (el.querySelector('.wb-subpage-count') || {}).textContent || null,
      rows: el.querySelectorAll('.tm-row, .ms-row').length,
      hasBack: !!el.querySelector('.wb-back'),
      transition: cs.transitionDuration + ' ' + cs.transitionTimingFunction,
      overflowX: el.scrollWidth - el.clientWidth,
    }
  })
  console.log('SUBPAGE:', JSON.stringify(sub))
  await p.screenshot({ path: path.join(OUT, 'b3-roster-subpage.png') })

  // ---- 4) 返回 ----
  await p.locator('.wb-back').click()
  await p.waitForTimeout(600)
  const backOk = await p.evaluate(() => !document.querySelector('.wb-subpage'))
  console.log('BACK_TO_BOARD:', backOk)
  await p.screenshot({ path: path.join(OUT, 'b4-back.png') })

  console.log('ERRORS:', errs.length ? JSON.stringify(errs.slice(0, 8), null, 2) : 'none')
  await b.close()
})()
