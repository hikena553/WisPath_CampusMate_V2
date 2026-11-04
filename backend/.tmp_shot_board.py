"""临时截图验证：账号管理画板（初始/拖拽卡片/展开/平移），验证完删除"""
import os
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

BASE = "http://127.0.0.1:5173"
OUT = r"E:\studyScore\创意集市\WisPath_CampusMate_V2\backend"

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1600, "height": 950}, device_scale_factor=1.5, locale="zh-CN")
    ctx.add_init_script("localStorage.setItem('mian02_welcome_seen', '1')")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:200]))

    # 用户 vite(5173) 的前端是热更新新代码；其 :8000 后端是旧进程，按 pathname 把 /api 转到 :8010 新后端
    def _redirect_api(route):
        req = route.request
        if urlparse(req.url).path.startswith("/api/"):
            route.continue_(url=req.url.replace("127.0.0.1:5173", "127.0.0.1:8010"))
        else:
            route.continue_()

    page.route("**/*", _redirect_api)

    page.goto(BASE + "/login", wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.get_by_placeholder("学号 / 工号").fill("admin")
    page.get_by_placeholder("密码").fill("admin123")
    page.locator(".agree input").check()
    page.locator("button[type=submit]").click()
    page.wait_for_timeout(4000)

    page.goto(BASE + "/admin/feeds", wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.get_by_role("tab", name="账号管理").click()
    page.wait_for_timeout(1500)
    page.screenshot(path=os.path.join(OUT, ".tmp_shot_board_1.png"))

    # 拖拽第一张卡片到右下
    card = page.locator(".board-card").first
    box = card.bounding_box()
    if box:
        cx, cy = box["x"] + box["width"] / 2, box["y"] + 30
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + 260, cy + 200, steps=12)
        page.mouse.up()
        page.wait_for_timeout(600)
    page.screenshot(path=os.path.join(OUT, ".tmp_shot_board_2.png"))

    # 刷新页面验证 localStorage 位置记忆
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(2500)
    page.get_by_role("tab", name="账号管理").click()
    page.wait_for_timeout(1200)
    page.screenshot(path=os.path.join(OUT, ".tmp_shot_board_3.png"))

    # 展开卡片（点状态条）
    page.locator(".board-card .acc-foot").first.click()
    page.wait_for_timeout(600)
    page.screenshot(path=os.path.join(OUT, ".tmp_shot_board_4.png"))

    print("page errors:", errs or "none")
    b.close()
