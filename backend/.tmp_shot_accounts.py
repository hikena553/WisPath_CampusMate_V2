"""临时截图验证：管理端资讯管理 → 账号管理卡片流（验证完删除）"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT = r"E:\studyScore\创意集市\WisPath_CampusMate_V2\backend"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5, locale="zh-CN")
    ctx.add_init_script("localStorage.setItem('mian02_welcome_seen', '1')")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:200]))

    # 用户自己的 vite(5173) 前端是热更新的新代码，但其后端(:8000)是旧进程；
    # 用路由拦截把真正的 /api 请求转到本验证用新后端 :8010，不动用户进程。
    # 注意：不能只按 glob '**/api/**' 匹配——vite 的模块路径 /src/api/*.ts 也会命中。
    from urllib.parse import urlparse

    def _redirect_api(route):
        req = route.request
        if urlparse(req.url).path.startswith("/api/"):
            route.continue_(url=req.url.replace("127.0.0.1:5173", "127.0.0.1:8010"))
        else:
            route.continue_()

    page.route("**/*", _redirect_api)

    page.goto(BASE + "/login", wait_until="networkidle")
    page.wait_for_timeout(1200)
    print("after goto url:", page.url)
    if not page.get_by_placeholder("学号 / 工号").count():
        page.screenshot(path=os.path.join(OUT, ".tmp_shot_login_debug.png"))
        print("login input missing!")
        b.close()
        raise SystemExit(1)
    page.get_by_placeholder("学号 / 工号").fill("admin")
    page.get_by_placeholder("密码").fill("admin123")
    page.locator(".agree input").check()
    page.locator("button[type=submit]").click()
    page.wait_for_timeout(4000)

    page.goto(BASE + "/admin/feeds", wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.get_by_role("tab", name="账号管理").click()
    page.wait_for_timeout(1500)
    page.screenshot(path=os.path.join(OUT, ".tmp_shot_accounts_1.png"))

    # 展开第一张卡片
    cards = page.locator(".acc-card")
    if cards.count():
        cards.first.locator(".acc-foot").click()
        page.wait_for_timeout(600)
    page.screenshot(path=os.path.join(OUT, ".tmp_shot_accounts_2.png"))

    print("page errors:", errs or "none")
    b.close()
