# -*- coding: utf-8 -*-
"""Build the WisPath CampusMate Apple-style animated promo deck.

Run:  python deck/build_deck.py [--out deck/out/WisPath_CampusMate_宣传片.pptx] [--no-anim]
"""
import sys, os, json, math
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import theme as T
from theme import (E, rect, ellipse, gradient_rect, line, tb, pill, picture, icon,
                   drop_shadow, blur_shape, SLIDE_W, SLIDE_H, set_slide_bg, notes)

try:
    import content as C
    COPY_SOURCE = "deck/content.py"
except Exception:
    import copy_draft as C
    COPY_SOURCE = "deck/copy_draft.py"

ASSETS = HERE / "assets"
try:
    import anim as ANIM
except Exception:
    ANIM = None

# --------------------------------------------------------------- animation registry
RECORDS = []          # list of dict(effects=[...], transition=dict or None, slide=slide)
_current = {"effects": [], "transition": None}

def A(shape, preset="fadeUp", start=0.3, dur=0.7, **kw):
    """register an animation for the current slide"""
    if shape is None:
        return shape
    _current["effects"].append(dict(shape=shape, preset=preset, start=start, dur=dur, **kw))
    return shape

def TRANSITION(kind="fade", dur=1.0, advance=None):
    _current["transition"] = dict(kind=kind, dur=dur, advance=advance)

# --------------------------------------------------------------- page chrome
def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, prs, T.INK)
    return slide

def background(slide, img_name, fallback_glows=()):
    p = ASSETS / img_name
    if p.exists():
        slide.shapes.add_picture(str(p), 0, 0, E(SLIDE_W), E(SLIDE_H))
    else:
        gradient_rect(slide, 0, 0, SLIDE_W, SLIDE_H,
                      [(0, "0B0D14", 1), (0.55, "05060A", 1), (1, "05060A", 1)], angle=90)
        for x, y, w, h, color, alpha in fallback_glows:
            ellipse(slide, x, y, w, h, color, alpha=alpha, blur=110)

def kicker(slide, text, x, y, color=T.BLUE, w=6.0, align="l"):
    return tb(slide, x, y, w, 0.28, [{"text": text, "size": 10.5, "color": color,
                                       "spc": 260, "bold": True, "font": T.EN}],
              align=align, anchor="m")

def title_lines(text, max_chars=9):
    """split a Chinese headline into 1-3 balanced lines at punctuation."""
    text = (text or "").strip()
    if "\n" in text:
        return [t for t in text.split("\n") if t]
    if len(text) <= max_chars:
        return [text]
    for mark in ("，", "。", "、", "；"):
        idx = text.find(mark)
        if 0 < idx < len(text) - 1 and idx + 1 <= max_chars + 2:
            return [text[:idx] + mark, text[idx + 1:]]
    mid = len(text) // 2
    return [text[:mid], text[mid:]]


def footer(slide, idx, total=10, label=None, color=T.GRAY_3, alpha=None):
    label = label or (C.BRAND["en"].upper() + "  ·  " + C.BRAND["school"])
    left = {"text": label, "size": 8, "color": color, "spc": 120, "font": T.EN}
    right = {"text": "%02d / %02d" % (idx, total), "size": 8, "color": color,
             "spc": 140, "font": T.EN}
    if alpha is not None:
        left["alpha"] = alpha
        right["alpha"] = alpha
    tb(slide, 0.95, 7.02, 8.0, 0.24, [left], anchor="m")
    tb(slide, 10.9, 7.02, 1.46, 0.24, [right], align="r", anchor="m")

def glow(slide, x, y, w, h, color, alpha=0.35, blur=110, t=1.0):
    e = ellipse(slide, x, y, w, h, color, alpha=alpha, blur=blur)
    A(e, "fade", start=t, dur=1.6)
    return e

def hairline(slide, x, y, w, alpha=0.10):
    line(slide, x, y, x + w, y, color="FFFFFF", width=0.75, alpha=alpha)

# --------------------------------------------------------------- chat bubble
def bubble_h(text, w, size):
    cpl = max(6, int((w - 0.20) / (size * 0.0139)))
    lines = max(1, math.ceil(len(text) / cpl))
    return max(0.34, 0.14 + lines * (size * 0.0205))


def bubble(slide, x, y, w, h, text, role="ai", u=2.5, size=None, name=None):
    """u = phone width, used to scale text/radius"""
    size = size or max(6.2, 3.15 * u)
    radius = 0.20 if role == "ai" else 0.22
    fill = T.BLUE if role == "user" else "FFFFFF"
    alpha = 0.92 if role == "user" else 0.09
    shp = rect(slide, x, y, w, h, fill=fill, alpha=alpha, radius=radius)
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = E(0.10); tf.margin_right = E(0.10)
    tf.margin_top = E(0.055); tf.margin_bottom = E(0.055)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    p.line_spacing = 1.22
    r = p.add_run(); r.text = text
    r.font.size = Pt(size)
    r.font.name = T.CN
    r.font.color.rgb = T.rgb(T.WHITE_PURE if role == "user" else "E8E8ED")
    from theme import _set_run_font
    _set_run_font(r, T.CN, T.CN, size=size, color=(T.WHITE_PURE if role == "user" else "E8E8ED"))
    return shp

# --------------------------------------------------------------- phone frame
def phone(slide, x, y, w, h, shadow=True, name="phone"):
    r = w * 0.17
    frame = rect(slide, x, y, w, h, fill="08080A", radius=r,
                 line="3A3A3C", line_w=1.1, name=name)
    if shadow:
        drop_shadow(frame, blur=44, dist=20, alpha=0.55)
    # side buttons
    rect(slide, x - 0.026, y + h * 0.20, 0.030, h * 0.075, fill="2A2A2C", radius=0.4)
    rect(slide, x - 0.026, y + h * 0.30, 0.030, h * 0.11, fill="2A2A2C", radius=0.4)
    rect(slide, x + w - 0.004, y + h * 0.26, 0.030, h * 0.13, fill="2A2A2C", radius=0.4)
    bx = w * 0.036
    sx, sy = x + bx, y + bx
    sw, sh = w - 2 * bx, h - 2 * bx
    screen = rect(slide, sx, sy, sw, sh, fill="0B0B10", radius=r * 0.86)
    # dynamic island
    iw = w * 0.30
    rect(slide, x + (w - iw) / 2, y + h * 0.014, iw, w * 0.075,
         fill="000000", radius=0.5, line="1C1C1E", line_w=0.6)
    # home indicator
    rect(slide, x + w * 0.34, y + h - bx - 0.055, w * 0.32, 0.035,
         fill="FFFFFF", alpha=0.45, radius=0.5)
    return dict(x=sx, y=sy, w=sw, h=sh, frame=frame, screen=screen, u=w)

def status_bar(slide, ph, color=T.WHITE):
    sx, sy, sw = ph["x"], ph["y"], ph["w"]
    u = ph["u"]
    # time
    tb(slide, sx + 0.14, sy + 0.075, 0.5, 0.18,
       [{"text": "9:41", "size": max(6.0, 2.7 * u), "color": color, "bold": True, "font": T.EN}],
       anchor="m")
    # signal bars
    bx = sx + sw - 0.72
    for i in range(4):
        bh = 0.035 + i * 0.018
        rect(slide, bx + i * 0.045, sy + 0.155 - bh, 0.024, bh, fill=color, alpha=0.95, radius=0.3)
    # battery
    rect(slide, sx + sw - 0.30, sy + 0.085, 0.20, 0.10, fill=None, radius=0.25,
         line=color, line_w=0.6, line_alpha=0.55)
    rect(slide, sx + sw - 0.285, sy + 0.100, 0.15, 0.07, fill=color, alpha=0.9, radius=0.2)
    rect(slide, sx + sw - 0.092, sy + 0.112, 0.012, 0.045, fill=color, alpha=0.6, radius=0.3)

def chat_input(slide, ph, placeholder="问问绵小城…", y_off=None):
    sx, sy, sw, sh = ph["x"], ph["y"], ph["w"], ph["h"]
    u = ph["u"]
    ih = 0.075 * u
    iy = y_off if y_off is not None else sy + sh - ih - 0.10
    bar = rect(slide, sx + 0.09, iy, sw - 0.18, ih, fill="FFFFFF", alpha=0.07,
               radius=0.5, line="FFFFFF", line_w=0.6, line_alpha=0.10)
    tb(slide, sx + 0.19, iy, sw - 0.62, ih,
       [{"text": placeholder, "size": max(5.8, 2.65 * u), "color": T.GRAY}], anchor="m")
    # mic
    rect(slide, sx + sw - 0.36, iy + ih / 2 - 0.055, 0.11, 0.11, fill=T.WHITE, alpha=0.55, radius=0.5)
    # send
    gradient_rect(slide, sx + sw - 0.27, iy + ih / 2 - 0.085, 0.17, 0.17,
                  [(0, T.BLUE, 1), (1, T.PURPLE, 1)], angle=45, radius=0.5)
    return bar

def phone_header(slide, ph, title, sub, avatar=None, accent=T.GREEN):
    sx, sy, sw = ph["x"], ph["y"], ph["w"]
    u = ph["u"]
    if avatar and avatar.exists():
        picture(slide, avatar, sx + 0.10, sy + 0.30, 0.30, 0.30)
    else:
        gradient_rect(slide, sx + 0.10, sy + 0.30, 0.30, 0.30,
                      [(0, T.BLUE, 1), (1, T.PURPLE, 1)], angle=45, radius=0.5)
    tb(slide, sx + 0.46, sy + 0.30, sw - 0.55, 0.18,
       [{"text": title, "size": max(6.8, 3.0 * u), "color": T.WHITE, "bold": True, "font": T.CN}], anchor="m")
    # online dot + sub
    ellipse(slide, sx + 0.47, sy + 0.505, 0.045, 0.045, accent, alpha=1.0)
    tb(slide, sx + 0.54, sy + 0.47, sw - 0.65, 0.14,
       [{"text": sub, "size": max(5.2, 2.35 * u), "color": T.GRAY_2}], anchor="m")
    hairline(slide, sx + 0.02, sy + 0.68, sw - 0.04, 0.08)

# =============================================================== 01  hello
def slide_hello(prs):
    s = new_slide(prs)
    background(s, "bg_00_hero.jpg", [
        (8.4, -1.6, 6.4, 6.4, T.PURPLE, 0.30),
        (9.6, 0.6, 5.0, 5.0, T.BLUE, 0.26),
        (-1.8, 4.2, 5.2, 5.2, T.BLUE, 0.18),
    ])
    TRANSITION("fade", 1.2, advance=6.5)
    brand = tb(s, 0, 0.62, SLIDE_W, 0.26,
               [{"text": "WISPATH  CAMPUSMATE", "size": 10.5, "color": T.GRAY_2,
                 "spc": 420, "font": T.EN}], align="c", anchor="m")
    A(brand, "fade", 0.15, 1.0)

    # Apple-style hello: reveal character by character (CJK glyph = 1em wide)
    hello_txt = C.HELLO["hello"]
    em = 118 / 72.0
    cx0 = SLIDE_W / 2
    for ci, ch in enumerate(hello_txt[:2]):
        ccx = cx0 - em * (len(hello_txt) / 2.0) + em * (ci + 0.5)
        box = tb(s, ccx - 1.05, 1.72, 2.10, 2.36,
                 [{"text": ch, "size": 118, "color": T.WHITE_PURE, "font": T.CN_LIGHT}],
                 align="c", anchor="m")
        A(box, "zoom", 0.5 + ci * 0.18, 1.0)

    sub = tb(s, 0, 4.16, SLIDE_W, 0.44,
             [{"text": C.HELLO["sub"], "size": 21, "color": "E8E8ED", "font": T.CN_LIGHT}],
             align="c", anchor="m")
    A(sub, "fadeUp", 1.75, 0.9)

    tag = tb(s, 0, 4.80, SLIDE_W, 0.34,
             [{"text": C.HELLO["tagline"], "size": 13.5, "color": T.GRAY}],
             align="c", anchor="m")
    A(tag, "fadeUp", 2.35, 0.8)

    # bottom hint
    hint = gradient_rect(s, 6.645, 6.02, 0.018, 0.44,
                         [(0, "FFFFFF", 0.0), (1, "FFFFFF", 0.55)], angle=90)
    A(hint, "fade", 3.0, 0.8)
    hint2 = tb(s, 0, 6.52, SLIDE_W, 0.26,
               [{"text": "向下，看看校园里的另一面", "size": 9, "color": T.GRAY_3}], align="c")
    A(hint2, "fade", 3.2, 0.8)

    fl = tb(s, 0.95, 7.02, 9.0, 0.24,
            [{"text": "绵阳城市学院  ·  智慧校园 AI 服务平台", "size": 8, "color": T.GRAY_3}],
            anchor="m")
    A(fl, "fade", 3.6, 0.8)
    return s


# =============================================================== 02  questions
def slide_questions(prs):
    s = new_slide(prs)
    background(s, "bg_01_question.jpg", [
        (2.0, 6.3, 9.0, 3.4, T.BLUE, 0.16),
    ])
    TRANSITION("fade", 1.0, advance=9.0)

    qmark = tb(s, 8.35, -0.55, 5.2, 7.0,
               [{"text": "?", "size": 400, "color": T.WHITE_PURE, "font": T.EN_LIGHT,
                 "alpha": 0.035}], align="l", anchor="m")
    A(qmark, "fade", 0.2, 2.6)

    k = kicker(s, "每天，我们都在重复这些问题", 0.95, 1.02, T.GRAY_2, w=8.0)
    A(k, "fadeUp", 0.3, 0.8)

    ys = [1.92, 3.06, 4.20]
    for i, q in enumerate(C.QUESTIONS[:3]):
        num = tb(s, 0.95, ys[i] + 0.06, 0.6, 0.26,
                 [{"text": "0%d" % (i + 1), "size": 10, "color": T.BLUE, "bold": True,
                   "spc": 120, "font": T.EN}], anchor="m")
        A(num, "fade", 0.8 + i * 0.55, 0.6)
        main = tb(s, 1.72, ys[i] - 0.10, 8.6, 0.62,
                  [{"text": q["main"], "size": 30, "color": T.WHITE, "font": T.CN_LIGHT}],
                  anchor="m")
        A(main, "fadeUp", 0.85 + i * 0.55, 0.8)
        subq = tb(s, 1.74, ys[i] + 0.47, 8.0, 0.26,
                  [{"text": q["sub"], "size": 10.5, "color": T.GRAY}], anchor="m")
        A(subq, "fade", 1.0 + i * 0.55, 0.7)
        if i < 2:
            hairline(s, 1.72, ys[i] + 1.02, 7.2, 0.06)

    ans = tb(s, 0.92, 5.50, 10.8, 0.88,
             [{"text": "如果，一句话就能解决？", "size": 42, "font": T.CN_LIGHT,
               "gradient": [(0, "FFFFFF", 1), (1, "7FB6FF", 1)], "color": T.WHITE}],
             anchor="m")
    A(ans, "wipeUp", 3.3, 1.0)

    cap = tb(s, 0.95, 6.56, 9.0, 0.26,
             [{"text": "接下来，认识一下替你回答的那个人。", "size": 10, "color": T.GRAY_3}], anchor="m")
    A(cap, "fade", 4.3, 0.8)
    footer(s, 2)
    return s


# =============================================================== 03  product
def slide_product(prs):
    s = new_slide(prs)
    background(s, "bg_02_product.jpg", [
        (4.8, 1.2, 8.0, 5.6, T.BLUE, 0.14),
        (8.6, 0.4, 5.4, 5.4, T.PURPLE, 0.14),
    ])
    TRANSITION("fade", 1.0, advance=11.0)
    k = kicker(s, "WISPATH  CAMPUSMATE", 0.95, 0.86, T.BLUE, w=6.0)
    A(k, "fadeUp", 0.2, 0.7)
    title = tb(s, 0.92, 1.18, 4.55, 1.85,
               [{"text": "一次对话，", "size": 44, "color": T.WHITE, "font": T.CN_LIGHT,
                 "line_spacing": 1.06},
                {"text": "连接整个校园。", "size": 44, "color": T.WHITE, "font": T.CN_LIGHT,
                 "line_spacing": 1.06}], anchor="t")
    A(title, "fadeUp", 0.5, 0.9)
    sub = tb(s, 0.95, 3.22, 4.15, 1.15,
             [{"text": "查课表、问流程、办请假、看成长——所有校园服务，都在同一个对话里完成。",
               "size": 12, "color": T.GRAY_2, "line_spacing": 1.55}], anchor="t")
    A(sub, "fadeUp", 1.0, 0.8)

    # stats
    stats = [(C.FACTS["pages"].split(" ")[0], "个前端页面"),
             (C.FACTS["api_modules"].split(" ")[0], "个 API 模块"),
             (C.FACTS["models"].split(" ")[0], "张数据表")]
    sx = 0.95
    for i, (num, label) in enumerate(stats):
        x = sx + i * 1.48
        n = tb(s, x, 4.86, 1.4, 0.40, [{"text": num, "size": 24, "color": T.WHITE,
                                        "font": T.EN_LIGHT}], anchor="m")
        l = tb(s, x, 5.26, 1.4, 0.24, [{"text": label, "size": 8.5, "color": T.GRAY}], anchor="m")
        A(n, "fadeUp", 1.55 + i * 0.12, 0.7); A(l, "fade", 1.65 + i * 0.12, 0.6)
        if i:
            line(s, x - 0.12, 4.86, x - 0.12, 5.42, color="FFFFFF", width=0.75, alpha=0.10)

    # ---------------- chat window
    wx, wy, ww, wh = 5.28, 1.26, 7.10, 4.98
    win = gradient_rect(s, wx, wy, ww, wh, [(0, "1B1B24", 0.94), (1, "0B0B10", 0.96)],
                        angle=120, radius=0.045, line="FFFFFF", line_alpha=0.12,
                        shadow=dict(blur=60, dist=26, alpha=0.55))
    A(win, "zoom", 0.65, 1.0)
    # header
    mascot = ASSETS / "mascot_avatar.png"
    if mascot.exists():
        picture(s, mascot, wx + 0.22, wy + 0.16, 0.36, 0.36)
    else:
        gradient_rect(s, wx + 0.22, wy + 0.16, 0.36, 0.36,
                      [(0, T.BLUE, 1), (1, T.PURPLE, 1)], angle=45, radius=0.5)
    tb(s, wx + 0.70, wy + 0.14, 2.4, 0.22,
       [{"text": "绵小城", "size": 13, "color": T.WHITE, "bold": True}], anchor="m")
    ellipse(s, wx + 0.72, wy + 0.44, 0.055, 0.055, T.GREEN)
    tb(s, wx + 0.81, wy + 0.395, 2.2, 0.18,
       [{"text": "在线 · 时刻待命", "size": 8, "color": T.GRAY}], anchor="m")
    sp = pill(s, wx + ww - 1.52, wy + 0.20, 1.30, 0.30, "SSE 流式输出", size=8,
              color=T.GREEN, fill=T.GREEN, alpha=0.10, line=T.GREEN, line_alpha=0.30, spc=60)
    A(sp, "fade", 1.4, 0.6)
    hairline(s, wx + 0.02, wy + 0.66, ww - 0.04, 0.10)

    b1 = bubble(s, wx + ww - 3.05, wy + 0.84, 2.82, 0.44, "我这学期的课表在哪看？", "user", u=4.6, size=10)
    A(b1, "fadeUp", 1.65, 0.55)
    b2 = bubble(s, wx + 0.28, wy + 1.38, 4.55, 0.62,
                "已为你找到本周 6 门课程。\n第一节是《数据结构》，周三 8:00 · A301。", "ai", u=4.6, size=10)
    A(b2, "fadeUp", 2.2, 0.7)
    tool = pill(s, wx + 0.30, wy + 2.12, 2.20, 0.32, "课表查询 · 工具已调用", size=8,
                color="C7F9CC", fill=T.GREEN, alpha=0.10, line=T.GREEN, line_alpha=0.35)
    A(tool, "fadeUp", 2.8, 0.6)
    b3 = bubble(s, wx + ww - 2.86, wy + 2.60, 2.62, 0.44, "顺便帮我请个周五的假？", "user", u=4.6, size=10)
    A(b3, "fadeUp", 3.15, 0.55)
    b4 = bubble(s, wx + 0.28, wy + 3.14, 3.10, 0.44, "已打开请假申请，填好即可提交。", "ai", u=4.6, size=10)
    A(b4, "fadeUp", 3.6, 0.6)
    # typing dots
    dots_box = rect(s, wx + 0.30, wy + 3.76, 0.80, 0.34, fill="FFFFFF", alpha=0.09, radius=0.5)
    for i in range(3):
        d = ellipse(s, wx + 0.43 + i * 0.14, wy + 3.88, 0.065, 0.065, T.GRAY_2, alpha=0.95)
        A(d, "pulse", 4.1 + i * 0.18, 0.9, repeat=2)
    A(dots_box, "fade", 4.05, 0.4)

    # input bar
    ib = rect(s, wx + 0.22, wy + wh - 0.66, ww - 0.44, 0.50, fill="FFFFFF", alpha=0.06,
              radius=0.5, line="FFFFFF", line_w=0.75, line_alpha=0.12)
    A(ib, "fadeUp", 3.95, 0.6)
    tb(s, wx + 0.40, wy + wh - 0.66, 4.6, 0.50,
       [{"text": "问问绵小城：今天有什么通知？", "size": 9.5, "color": T.GRAY}], anchor="m")
    # mic + send
    rect(s, wx + ww - 1.02, wy + wh - 0.52, 0.22, 0.22, fill=T.WHITE, alpha=0.45, radius=0.5)
    gradient_rect(s, wx + ww - 0.70, wy + wh - 0.57, 0.32, 0.32,
                  [(0, T.BLUE, 1), (1, T.PURPLE, 1)], angle=45, radius=0.5)

    footer(s, 3)
    return s


# =============================================================== 04  pillars
def slide_pillars(prs):
    s = new_slide(prs)
    background(s, "bg_06_features.jpg", [
        (2.0, 0.4, 5.4, 4.4, T.BLUE, 0.10),
        (7.0, 3.0, 5.2, 4.4, T.PURPLE, 0.10),
    ])
    TRANSITION("fade", 1.0, advance=10.0)
    k = kicker(s, "核心能力", 0.95, 0.72, T.BLUE)
    t = tb(s, 0.92, 1.02, 10.0, 0.78,
           [{"text": "把整个校园，装进一次对话。", "size": 36, "color": T.WHITE,
             "font": T.CN_LIGHT}], anchor="m")
    A(t, "fadeUp", 0.25, 0.9)
    sub = tb(s, 0.95, 1.78, 9.6, 0.30,
             [{"text": "四个能力互相咬合：问得懂、记得住、办得快、看得见。", "size": 11.5,
               "color": T.GRAY}], anchor="m")
    A(sub, "fadeUp", 0.5, 0.7)

    card_w, gap, cy, ch = 2.62, 0.27, 2.35, 3.22
    x0 = (SLIDE_W - (4 * card_w + 3 * gap)) / 2
    tones = [T.BLUE, T.CYAN, T.GREEN, T.PURPLE]
    for i, p in enumerate(C.PILLARS[:4]):
        x = x0 + i * (card_w + gap)
        card = rect(s, x, cy, card_w, ch, fill="FFFFFF", alpha=0.045, radius=0.045,
                    line="FFFFFF", line_w=0.75, line_alpha=0.10)
        A(card, "fadeUp", 0.85 + i * 0.14, 0.85)
        # index
        idx = tb(s, x + card_w - 0.62, cy + 0.22, 0.46, 0.24,
                 [{"text": "0%d" % (i + 1), "size": 9, "color": T.GRAY_3, "font": T.EN,
                   "spc": 100}], align="r", anchor="m")
        # icon plate
        plate = rect(s, x + 0.26, cy + 0.24, 0.58, 0.58, fill=tones[i], alpha=0.16,
                     radius=0.28, line=tones[i], line_w=0.75, line_alpha=0.35)
        ic = icon(s, ASSETS, p["icon"], x + 0.395, cy + 0.375, 0.31)
        if ic is None:
            ic = ellipse(s, x + 0.42, cy + 0.40, 0.26, 0.26, tones[i], alpha=0.9)
        A(ic, "zoom", 1.0 + i * 0.14, 0.6)
        nm = tb(s, x + 0.26, cy + 1.10, card_w - 0.5, 0.34,
                [{"text": p["title"], "size": 18, "color": T.WHITE, "font": T.CN}], anchor="m")
        A(nm, "fadeUp", 1.05 + i * 0.14, 0.6)
        ds = tb(s, x + 0.26, cy + 1.52, card_w - 0.5, 1.05,
                [{"text": p["desc"], "size": 10.5, "color": T.GRAY_2, "line_spacing": 1.55}],
                anchor="t")
        A(ds, "fadeUp", 1.15 + i * 0.14, 0.6)
        tg = pill(s, x + 0.26, cy + ch - 0.62, 1.16, 0.30, p["tag"], size=8, color=tones[i],
                  fill=tones[i], alpha=0.12, line=tones[i], line_alpha=0.25)
        A(tg, "fadeUp", 1.3 + i * 0.14, 0.55)

    cap = tb(s, 0.95, 6.12, 11.4, 0.28,
             [{"text": "查 · 问 · 办 · 伴   ——   一个入口，四种体验。", "size": 10,
               "color": T.GRAY_3, "spc": 80}], align="c", anchor="m")
    A(cap, "fade", 2.2, 0.8)
    footer(s, 4)
    return s


# =============================================================== 05  student phone
def slide_student(prs):
    s = new_slide(prs)
    background(s, "bg_03_student.jpg", [
        (0.4, 1.4, 5.4, 5.6, T.BLUE, 0.18),
        (2.6, 4.0, 4.4, 4.0, T.CYAN, 0.10),
    ])
    TRANSITION("fade", 1.1, advance=12.0)
    # glow behind phones
    g = ellipse(s, 0.85, 2.05, 5.1, 4.0, T.BLUE, alpha=0.16, blur=120)
    A(g, "fade", 0.3, 2.0)

    # ---- secondary phone (growth)
    ph2 = phone(s, 3.74, 1.86, 2.02, 4.28, name="phone_growth")
    A(ph2["frame"], "fadeUp", 0.95, 1.0)
    sx, sy, sw, sh = ph2["x"], ph2["y"], ph2["w"], ph2["h"]
    status_bar(s, ph2)
    tb(s, sx + 0.12, sy + 0.34, sw - 0.3, 0.24,
       [{"text": "成长档案", "size": 8.6, "color": T.WHITE, "bold": True}], anchor="m")
    tb(s, sx + 0.12, sy + 0.57, sw - 0.3, 0.18,
       [{"text": "2025-2026 学年", "size": 5.4, "color": T.GRAY}], anchor="m")
    # donut
    donut = s.shapes.add_shape(MSO_SHAPE.DONUT, E(sx + 0.42), E(sy + 0.82), E(1.02), E(1.02))
    donut.shadow.inherit = False
    donut.fill.gradient()
    donut.fill.gradient_angle = 45
    donut.fill.gradient_stops[0].color.rgb = T.rgb(T.BLUE)
    donut.fill.gradient_stops[1].color.rgb = T.rgb(T.PURPLE)
    donut.line.fill.background()
    donut.adjustments[0] = 0.13
    A(donut, "zoom", 1.5, 0.9)
    tb(s, sx + 0.42, sy + 0.99, 1.02, 0.30,
       [{"text": "92", "size": 19, "color": T.WHITE, "font": T.EN_LIGHT}], align="c", anchor="m")
    tb(s, sx + 0.58, sy + 1.30, 0.70, 0.14,
       [{"text": "综合评分", "size": 5.0, "color": T.GRAY}], align="c", anchor="m")
    # bars
    rows = [("学业", 0.86, T.BLUE), ("心理", 0.92, T.CYAN), ("参与", 0.78, T.GREEN)]
    for i, (label, v, col) in enumerate(rows):
        yy = sy + 2.02 + i * 0.35
        tb(s, sx + 0.16, yy, 0.42, 0.20, [{"text": label, "size": 5.4, "color": T.GRAY}], anchor="m")
        rect(s, sx + 0.62, yy + 0.055, 0.90, 0.075, fill="FFFFFF", alpha=0.10, radius=0.5)
        rect(s, sx + 0.62, yy + 0.055, 0.90 * v, 0.075, fill=col, alpha=0.95, radius=0.5)
    # tags
    tags = ["竞赛", "实践", "论文"]
    for i, tg in enumerate(tags):
        pill(s, sx + 0.14 + i * 0.58, sy + 3.22, 0.52, 0.24, tg, size=5.2, color=T.GRAY_2,
             fill="FFFFFF", alpha=0.07, line="FFFFFF", line_alpha=0.10)
    tb(s, sx + 0.16, sy + 3.64, sw - 0.3, 0.34,
       [{"text": "荣誉 8 项 · 实践 5 项", "size": 5.6, "color": T.GRAY_2}], anchor="m")

    # ---- main phone (chat)
    ph = phone(s, 1.32, 1.05, 2.52, 5.28, name="phone_chat")
    A(ph["frame"], "fadeUp", 0.55, 1.05)
    sx, sy, sw, sh = ph["x"], ph["y"], ph["w"], ph["h"]
    status_bar(s, ph)
    phone_header(s, ph, C.STUDENT["phone_title"], C.STUDENT["phone_sub"],
                 avatar=ASSETS / "mascot_avatar.png")
    # messages
    msgs = C.STUDENT["chat"][:4]
    yy = sy + 0.86
    for i, m in enumerate(msgs):
        w = 1.78 if m["role"] == "user" else 1.98
        h = bubble_h(m["text"], w, max(6.2, 3.15 * ph["u"]))
        x = sx + sw - 0.10 - w if m["role"] == "user" else sx + 0.10
        b = bubble(s, x, yy, w, h, m["text"], m["role"], u=ph["u"])
        A(b, "fadeUp", 1.55 + i * 0.42, 0.5)
        yy += h + 0.075
    chat_input(s, ph)

    # ---- right column copy
    x = 7.30
    k = kicker(s, C.STUDENT["eyebrow"], x, 0.92, T.BLUE, w=5.2)
    A(k, "fadeUp", 0.35, 0.7)
    t = tb(s, x - 0.02, 1.16, 5.25, 1.60,
           [{"text": line_, "size": 34, "color": T.WHITE, "font": T.CN_LIGHT,
             "line_spacing": 1.14} for line_ in title_lines(C.STUDENT["headline"], 6)], anchor="t")
    A(t, "fadeUp", 0.6, 0.9)
    sub = tb(s, x, 2.70, 4.95, 0.72,
             [{"text": C.STUDENT["sub"], "size": 11, "color": T.GRAY_2, "line_spacing": 1.5}],
             anchor="t")
    A(sub, "fadeUp", 0.95, 0.8)

    fy = 3.52
    for i, f in enumerate(C.STUDENT["features"][:4]):
        yy = fy + i * 0.68
        ic = icon(s, ASSETS, f["icon"], x, yy, 0.30)
        if ic is None:
            ic = gradient_rect(s, x, yy, 0.30, 0.30, [(0, T.BLUE, 1), (1, T.PURPLE, 1)],
                               angle=45, radius=0.5)
        A(ic, "fadeLeft", 1.25 + i * 0.13, 0.55)
        nm = tb(s, x + 0.44, yy - 0.02, 4.4, 0.26,
                [{"text": f["title"], "size": 13, "color": T.WHITE}], anchor="m")
        A(nm, "fadeLeft", 1.3 + i * 0.13, 0.55)
        ds = tb(s, x + 0.44, yy + 0.24, 4.4, 0.24,
                [{"text": f["desc"], "size": 9.5, "color": T.GRAY}], anchor="m")
        A(ds, "fadeLeft", 1.35 + i * 0.13, 0.55)

    # chips
    cx, cy = x, 6.34
    widths = [0.82, 0.82, 0.72, 0.98, 0.98, 0.98]
    for i, chip in enumerate(C.STUDENT["chips"][:6]):
        w = widths[i % len(widths)]
        p = pill(s, cx, cy, w, 0.30, chip, size=8.5, color=T.GRAY_2, fill="FFFFFF",
                 alpha=0.06, line="FFFFFF", line_alpha=0.12)
        A(p, "fadeUp", 1.9 + i * 0.06, 0.45)
        cx += w + 0.10
    footer(s, 5)
    return s

# =============================================================== 06  teacher phone
def slide_teacher(prs):
    s = new_slide(prs)
    background(s, "bg_04_teacher.jpg", [
        (7.4, 1.2, 5.6, 5.6, T.ORANGE, 0.16),
        (9.4, 3.4, 4.6, 4.2, T.PINK, 0.12),
    ])
    TRANSITION("fade", 1.1, advance=12.0)
    g = ellipse(s, 7.55, 2.0, 4.9, 4.0, T.ORANGE, alpha=0.14, blur=120)
    A(g, "fade", 0.3, 2.0)

    # ---- left copy
    x = 0.95
    k = kicker(s, C.TEACHER["eyebrow"], x, 0.92, T.ORANGE, w=5.2)
    A(k, "fadeUp", 0.35, 0.7)
    t = tb(s, x - 0.02, 1.16, 5.15, 1.60,
           [{"text": line_, "size": 34, "color": T.WHITE, "font": T.CN_LIGHT,
             "line_spacing": 1.14} for line_ in title_lines(C.TEACHER["headline"], 6)], anchor="t")
    A(t, "fadeUp", 0.6, 0.9)
    sub = tb(s, x, 2.70, 4.85, 0.66,
             [{"text": C.TEACHER["sub"], "size": 11, "color": T.GRAY_2, "line_spacing": 1.5}], anchor="t")
    A(sub, "fadeUp", 0.95, 0.8)

    fy = 3.52
    for i, f in enumerate(C.TEACHER["features"][:4]):
        yy = fy + i * 0.68
        ic = icon(s, ASSETS, f["icon"], x, yy, 0.30)
        if ic is None:
            ic = gradient_rect(s, x, yy, 0.30, 0.30, [(0, T.ORANGE, 1), (1, T.PINK, 1)],
                               angle=45, radius=0.5)
        A(ic, "fadeRight", 1.25 + i * 0.13, 0.55)
        nm = tb(s, x + 0.44, yy - 0.02, 4.4, 0.26,
                [{"text": f["title"], "size": 13, "color": T.WHITE}], anchor="m")
        A(nm, "fadeRight", 1.3 + i * 0.13, 0.55)
        ds = tb(s, x + 0.44, yy + 0.24, 4.4, 0.24,
                [{"text": f["desc"], "size": 9.5, "color": T.GRAY}], anchor="m")
        A(ds, "fadeRight", 1.35 + i * 0.13, 0.55)

    cx, cy = x, 6.30
    widths = [0.82, 0.98, 0.98, 0.92, 0.98, 0.86]
    for i, chip in enumerate(C.TEACHER["chips"][:6]):
        w = widths[i % len(widths)]
        p = pill(s, cx, cy, w, 0.30, chip, size=8.5, color=T.GRAY_2, fill="FFFFFF",
                 alpha=0.06, line="FFFFFF", line_alpha=0.12)
        A(p, "fadeUp", 1.95 + i * 0.06, 0.45)
        cx += w + 0.10

    # ---- phone
    ph = phone(s, 8.86, 1.02, 2.60, 5.36, name="phone_teacher")
    A(ph["frame"], "fadeUp", 0.6, 1.05)
    sx, sy, sw, sh = ph["x"], ph["y"], ph["w"], ph["h"]
    status_bar(s, ph)
    phone_header(s, ph, "t1001 · 王老师", "计算机学院 · 软工 2201",
                 avatar=ASSETS / "mascot_avatar.png", accent=T.GREEN)

    # kpi grid
    tone_map = {"blue": T.BLUE, "green": T.GREEN, "orange": T.ORANGE, "red": T.PINK}
    tw = (sw - 0.30) / 2
    for i, kpi in enumerate(C.TEACHER["kpis"][:4]):
        col, row = i % 2, i // 2
        x0 = sx + 0.12 + col * (tw + 0.06)
        y0 = sy + 0.82 + row * 0.70
        tone = tone_map.get(kpi.get("tone", "blue"), T.BLUE)
        card = rect(s, x0, y0, tw, 0.62, fill="FFFFFF", alpha=0.055, radius=0.10,
                    line="FFFFFF", line_w=0.6, line_alpha=0.09)
        A(card, "fadeUp", 1.35 + i * 0.08, 0.5)
        rect(s, x0 + 0.11, y0 + 0.12, 0.055, 0.20, fill=tone, radius=0.5)
        v = tb(s, x0 + 0.20, y0 + 0.07, tw - 0.30, 0.28,
               [{"text": kpi["value"], "size": 15, "color": T.WHITE, "font": T.EN_LIGHT}], anchor="m")
        lb = tb(s, x0 + 0.20, y0 + 0.36, tw - 0.30, 0.18,
                [{"text": kpi["label"], "size": 5.8, "color": T.GRAY}], anchor="m")
        A(v, "fadeUp", 1.4 + i * 0.08, 0.5); A(lb, "fade", 1.45 + i * 0.08, 0.4)

    # approval card
    ap = C.TEACHER["approval"]
    ay = sy + 2.46
    card = rect(s, sx + 0.12, ay, sw - 0.24, 1.06, fill="FFFFFF", alpha=0.06, radius=0.08,
                line="FFFFFF", line_w=0.6, line_alpha=0.10)
    A(card, "fadeUp", 2.05, 0.7)
    tb(s, sx + 0.24, ay + 0.09, 1.2, 0.22, [{"text": ap["name"], "size": 9.5, "color": T.WHITE,
                                             "bold": True}], anchor="m")
    tb(s, sx + 0.24, ay + 0.31, 1.3, 0.18, [{"text": ap["type"], "size": 6.6, "color": T.GRAY_2}], anchor="m")
    tb(s, sx + 0.24, ay + 0.50, 1.3, 0.16, [{"text": ap["time"], "size": 5.6, "color": T.GRAY}], anchor="m")
    # status + buttons
    st = pill(s, sx + sw - 0.90, ay + 0.09, 0.66, 0.22, "待审批", size=5.6, color=T.ORANGE,
              fill=T.ORANGE, alpha=0.14, line=T.ORANGE, line_alpha=0.30)
    A(st, "fade", 2.15, 0.4)
    ok = pill(s, sx + sw - 0.90, ay + 0.44, 0.66, 0.26, "同意", size=6.4, color=T.INK,
              fill=T.GREEN, alpha=0.92)
    A(ok, "zoom", 2.5, 0.45)
    no = pill(s, sx + sw - 0.90, ay + 0.75, 0.66, 0.22, "拒绝", size=6.0, color=T.GRAY_2,
              fill="FFFFFF", alpha=0.06, line="FFFFFF", line_alpha=0.14)
    A(no, "fade", 2.6, 0.4)
    # tap ripple
    ring = ellipse(s, sx + sw - 0.94, ay + 0.38, 0.74, 0.38, T.GREEN, alpha=0.25, blur=18)
    A(ring, "pulse", 3.1, 0.7, repeat=2)

    toast = pill(s, sx + 0.20, ay + 1.22, sw - 0.40, 0.30, "已同意 · 已通知学生", size=6.2,
                 color="C9F7D2", fill=T.GREEN, alpha=0.16, line=T.GREEN, line_alpha=0.35)
    A(toast, "fadeUp", 3.3, 0.6)

    # today list
    ty = ay + 1.66
    tb(s, sx + 0.18, ty, 1.6, 0.18, [{"text": "今日待办", "size": 6.4, "color": T.GRAY_2,
                                      "bold": True}], anchor="m")
    todos = [("09:40", "听课 · 数据结构"), ("14:00", "班会 · 软工 2201"), ("16:30", "危机工单回访")]
    for i, (tm, tx) in enumerate(todos):
        yy = ty + 0.24 + i * 0.30
        tb(s, sx + 0.18, yy, 0.42, 0.20, [{"text": tm, "size": 5.2, "color": T.GRAY}], anchor="m")
        dot = ellipse(s, sx + 0.62, yy + 0.065, 0.05, 0.05, T.GREEN if i != 2 else T.PINK)
        tb(s, sx + 0.72, yy, sw - 0.9, 0.20, [{"text": tx, "size": 5.8, "color": T.GRAY_2}], anchor="m")

    # floating crisis alert card
    ax, ayy = 6.42, 2.40
    alert = rect(s, ax, ayy, 2.18, 1.18, fill="2A0A12", alpha=0.92, radius=0.10,
                 line=T.PINK, line_w=0.9, line_alpha=0.45,
                 shadow=dict(blur=36, dist=14, alpha=0.5))
    A(alert, "fadeUp", 4.0, 0.7)
    ic = icon(s, ASSETS, "shield", ax + 0.18, ayy + 0.18, 0.30)
    if ic is None:
        ellipse(s, ax + 0.20, ayy + 0.20, 0.24, 0.24, T.PINK, alpha=0.9)
    A(ic, "pulse", 4.4, 0.9, repeat=2)
    tb(s, ax + 0.58, ayy + 0.14, 1.5, 0.22, [{"text": "危机预警", "size": 8.6, "color": "FFD5DD",
                                              "bold": True}], anchor="m")
    tb(s, ax + 0.58, ayy + 0.36, 1.5, 0.18, [{"text": "1 位学生情绪风险升高", "size": 6.2,
                                              "color": "F3B6C1"}], anchor="m")
    tb(s, ax + 0.18, ayy + 0.72, 1.8, 0.16, [{"text": "语义识别 · 已分级推送", "size": 5.6,
                                              "color": "D898A5"}], anchor="m")
    cr = pill(s, ax + 1.42, ayy + 0.76, 0.58, 0.24, "去处理", size=5.8, color=T.WHITE,
              fill=T.PINK, alpha=0.85)
    A(cr, "fadeUp", 4.5, 0.5)
    footer(s, 6)
    return s


# =============================================================== 07  admin dashboard
def slide_admin(prs):
    s = new_slide(prs)
    background(s, "bg_05_admin.jpg", [
        (1.0, 1.6, 6.6, 3.2, T.BLUE, 0.12),
        (6.0, 4.6, 6.4, 3.6, T.PURPLE, 0.10),
    ])
    TRANSITION("fade", 1.1, advance=12.0)
    k = kicker(s, C.ADMIN["eyebrow"], 0.95, 0.58, T.CYAN, w=6.0)
    A(k, "fadeUp", 0.25, 0.7)
    t = tb(s, 0.92, 0.86, 6.6, 0.66,
           [{"text": C.ADMIN["headline"], "size": 34, "color": T.WHITE, "font": T.CN_LIGHT}], anchor="m")
    A(t, "fadeUp", 0.45, 0.85)
    sub = tb(s, 0.95, 1.55, 5.3, 0.30,
             [{"text": C.ADMIN["sub"], "size": 10.5, "color": T.GRAY}], anchor="m")
    A(sub, "fadeUp", 0.7, 0.7)
    # feature pills
    px = 6.92
    for i, f in enumerate(C.ADMIN["features"][:4]):
        p = pill(s, px, 1.52, 1.28, 0.34, f["title"], size=9, color=T.WHITE,
                 fill="FFFFFF", alpha=0.06, line="FFFFFF", line_alpha=0.14)
        A(p, "fadeUp", 1.0 + i * 0.08, 0.5)
        px += 1.37

    # ---------------- window
    wx, wy, ww, wh = 0.95, 2.10, 11.43, 4.58
    win = gradient_rect(s, wx, wy, ww, wh, [(0, "17171E", 0.95), (1, "0A0A0E", 0.97)],
                        angle=120, radius=0.028, line="FFFFFF", line_alpha=0.12,
                        shadow=dict(blur=56, dist=24, alpha=0.55))
    A(win, "zoom", 0.55, 1.0)
    # title bar
    for i, col in enumerate(["FF5F57", "FEBC2E", "28C840"]):
        ellipse(s, wx + 0.20 + i * 0.19, wy + 0.15, 0.105, 0.105, col)
    tb(s, wx + 0.95, wy + 0.07, 3.6, 0.26,
       [{"text": "WisPath 管理后台  ·  数据看板", "size": 8.4, "color": T.GRAY_2}], anchor="m")
    tb(s, wx + ww - 1.4, wy + 0.07, 1.2, 0.26,
       [{"text": "admin  ·  管理员", "size": 7.6, "color": T.GRAY, "font": T.CN}], align="r", anchor="m")
    hairline(s, wx, wy + 0.42, ww, 0.10)

    # sidebar
    sb = rect(s, wx, wy + 0.42, 1.55, wh - 0.42, fill="000000", alpha=0.28)
    nav = ["数据看板", "组织架构", "账号权限", "知识库", "通知公告", "系统监控"]
    for i, n in enumerate(nav):
        yy = wy + 0.62 + i * 0.46
        if i == 0:
            rect(s, wx + 0.12, yy - 0.06, 1.31, 0.34, fill=T.BLUE, alpha=0.16, radius=0.16)
        rect(s, wx + 0.22, yy + 0.035, 0.13, 0.13, fill=T.BLUE if i == 0 else T.GRAY_3,
             alpha=0.9, radius=0.25)
        tb(s, wx + 0.44, yy - 0.06, 1.05, 0.32,
           [{"text": n, "size": 7.4, "color": T.WHITE if i == 0 else T.GRAY}], anchor="m")

    # main area
    mx = wx + 1.72
    mw = ww - 1.72 - 0.22
    # kpi tiles
    kw = (mw - 2 * 0.18) / 3
    for i, kpi in enumerate(C.ADMIN["kpis"][:3]):
        x0 = mx + i * (kw + 0.18)
        tile = rect(s, x0, wy + 0.60, kw, 0.86, fill="FFFFFF", alpha=0.045, radius=0.06,
                    line="FFFFFF", line_w=0.6, line_alpha=0.08)
        A(tile, "fadeUp", 1.2 + i * 0.1, 0.6)
        tb(s, x0 + 0.18, wy + 0.68, kw - 0.3, 0.20,
           [{"text": kpi["label"], "size": 7.6, "color": T.GRAY}], anchor="m")
        v = tb(s, x0 + 0.18, wy + 0.88, kw - 0.3, 0.38,
               [{"text": kpi["value"], "size": 20, "color": T.WHITE, "font": T.EN_LIGHT}], anchor="m")
        A(v, "fadeUp", 1.28 + i * 0.1, 0.55)
        delta = tb(s, x0 + kw - 0.95, wy + 0.90, 0.80, 0.24,
                   [{"text": kpi.get("delta", ""), "size": 7.2, "color": T.GREEN}], align="r", anchor="m")
        A(delta, "fade", 1.35 + i * 0.1, 0.45)

    # chart panel
    cx0, cy0, cw, chh = mx, wy + 1.66, mw - 3.10, 2.12
    panel = rect(s, cx0, cy0, cw, chh, fill="FFFFFF", alpha=0.03, radius=0.05,
                 line="FFFFFF", line_w=0.6, line_alpha=0.07)
    tb(s, cx0 + 0.18, cy0 + 0.12, 3.0, 0.24,
       [{"text": "近 7 日 AI 对话量", "size": 8.2, "color": T.WHITE}], anchor="m")
    tb(s, cx0 + cw - 1.6, cy0 + 0.12, 1.42, 0.24,
       [{"text": "单位：次", "size": 6.6, "color": T.GRAY}], align="r", anchor="m")
    base_y = cy0 + chh - 0.34
    heights = [0.78, 0.55, 0.86, 0.68, 0.95, 1.18, 1.05]
    labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    bw = 0.34
    gap = (cw - 0.6 - 7 * bw) / 6
    for i, hgt in enumerate(heights):
        bx = cx0 + 0.30 + i * (bw + gap)
        bar = gradient_rect(s, bx, base_y - hgt, bw, hgt,
                            [(0, T.BLUE, 0.95), (1, T.CYAN, 0.35)], angle=90, radius=0.12)
        A(bar, "wipeUp", 1.55 + i * 0.07, 0.55)
        tb(s, bx - 0.06, base_y + 0.03, bw + 0.12, 0.18,
           [{"text": labels[i], "size": 5.6, "color": T.GRAY}], align="c", anchor="m")
    hairline(s, cx0 + 0.2, base_y, cw - 0.4, 0.10)

    # right panel
    rx, ry, rw, rh = cx0 + cw + 0.18, cy0, 2.92, chh
    panel2 = rect(s, rx, ry, rw, rh, fill="FFFFFF", alpha=0.03, radius=0.05,
                  line="FFFFFF", line_w=0.6, line_alpha=0.07)
    tb(s, rx + 0.18, ry + 0.12, 2.0, 0.24, [{"text": "系统健康度", "size": 8.2, "color": T.WHITE}], anchor="m")
    donut = s.shapes.add_shape(MSO_SHAPE.DONUT, E(rx + 0.30), E(ry + 0.52), E(1.02), E(1.02))
    donut.shadow.inherit = False
    donut.fill.gradient()
    donut.fill.gradient_angle = 45
    donut.fill.gradient_stops[0].color.rgb = T.rgb(T.GREEN)
    donut.fill.gradient_stops[1].color.rgb = T.rgb(T.CYAN)
    donut.line.fill.background()
    donut.adjustments[0] = 0.14
    A(donut, "zoom", 2.0, 0.8)
    tb(s, rx + 0.30, ry + 0.82, 1.02, 0.26, [{"text": "99.9%", "size": 14, "color": T.WHITE,
                                              "font": T.EN_LIGHT}], align="c", anchor="m")
    tb(s, rx + 0.30, ry + 1.10, 1.02, 0.16, [{"text": "服务可用率", "size": 5.2, "color": T.GRAY}],
       align="c", anchor="m")
    svc = [("API 服务", "正常", T.GREEN), ("模型调用", "正常", T.GREEN), ("消息通道", "正常", T.GREEN)]
    for i, (name, stt, col) in enumerate(svc):
        yy = ry + 0.62 + i * 0.44
        tb(s, rx + 1.46, yy, 0.86, 0.20, [{"text": name, "size": 6.2, "color": T.GRAY_2}], anchor="m")
        ellipse(s, rx + 2.32, yy + 0.045, 0.08, 0.08, col)
        tb(s, rx + 2.44, yy, 0.42, 0.20, [{"text": stt, "size": 6.0, "color": col}], anchor="m")
    tb(s, rx + 0.18, ry + rh - 0.28, rw - 0.36, 0.20,
       [{"text": "所有核心服务运行正常", "size": 6.4, "color": T.GRAY}], anchor="m")

    # table strip
    tx0, ty0 = mx, wy + wh - 0.62
    tb(s, tx0, ty0, 1.8, 0.20, [{"text": "最近操作", "size": 7.0, "color": T.GRAY}], anchor="m")
    ops = ["10:24  更新知识库词条", "10:02  新增教师账号", "09:41  导出班级课表"]
    for i, op in enumerate(ops):
        tb(s, tx0 + 0.95 + i * 3.05, ty0, 2.95, 0.20,
           [{"text": op, "size": 6.2, "color": T.GRAY_3}], anchor="m")
    tb(s, wx + ww - 1.85, wy + wh - 0.60, 1.65, 0.20,
       [{"text": "界面示意 · 数据为演示", "size": 5.8, "color": T.GRAY_3}], align="r", anchor="m")
    footer(s, 7)
    return s


# =============================================================== 08  tech
def slide_tech(prs):
    s = new_slide(prs)
    background(s, "bg_08_tech.jpg", [
        (0.2, 3.4, 4.8, 4.6, T.CYAN, 0.10),
        (7.6, 0.6, 5.2, 4.6, T.PURPLE, 0.12),
    ])
    TRANSITION("fade", 1.0, advance=10.0)
    k = kicker(s, "技术底座", 0.95, 0.80, T.CYAN)
    A(k, "fadeUp", 0.2, 0.7)
    t = tb(s, 0.92, 1.06, 5.25, 1.55,
           [{"text": line_, "size": 32, "color": T.WHITE, "font": T.CN_LIGHT,
             "line_spacing": 1.16} for line_ in title_lines(C.TECH["headline"], 8)], anchor="t")
    A(t, "fadeUp", 0.45, 0.9)
    sub = tb(s, 0.95, 2.72, 4.35, 0.66,
             [{"text": C.TECH["sub"], "size": 10.5, "color": T.GRAY_2, "line_spacing": 1.5}], anchor="t")
    A(sub, "fadeUp", 0.8, 0.75)
    # security rows
    for i, sec in enumerate(C.TECH["security"][:3]):
        yy = 3.72 + i * 0.44
        ic = icon(s, ASSETS, "shield", 0.95, yy, 0.26)
        if ic is None:
            ellipse(s, 0.95, yy, 0.22, 0.22, T.GREEN, alpha=0.8)
        A(ic, "fadeLeft", 1.15 + i * 0.12, 0.5)
        tx = tb(s, 1.32, yy - 0.03, 3.9, 0.28, [{"text": sec, "size": 9.5, "color": T.GRAY_2}], anchor="m")
        A(tx, "fadeLeft", 1.2 + i * 0.12, 0.5)

    # bottom-left key numbers (fill the negative space with facts)
    stat = [("4", "层架构"), ("357", "个接口"), ("53", "个 AI 工具")]
    for si, (num, label) in enumerate(stat):
        sx = 0.95 + si * 1.48
        n = tb(s, sx, 5.42, 1.3, 0.44, [{"text": num, "size": 23, "color": T.WHITE,
                                        "font": T.EN_LIGHT}], anchor="m")
        l = tb(s, sx, 5.86, 1.3, 0.24, [{"text": label, "size": 8.5, "color": T.GRAY}], anchor="m")
        A(n, "fadeUp", 1.55 + si * 0.1, 0.6)
        A(l, "fade", 1.62 + si * 0.1, 0.5)
        if si:
            line(s, sx - 0.12, 5.42, sx - 0.12, 5.98, color="FFFFFF", width=0.75, alpha=0.10)

    # layers
    lx, ly, lw, lh, lg = 6.55, 1.16, 5.85, 0.98, 0.17
    for i, layer in enumerate(C.TECH["layers"][:4]):
        yy = ly + i * (lh + lg)
        card = rect(s, lx, yy, lw, lh, fill="FFFFFF", alpha=0.045, radius=0.07,
                    line="FFFFFF", line_w=0.65, line_alpha=0.10)
        A(card, "fadeLeft", 0.7 + i * 0.18, 0.7)
        # accent edge
        rect(s, lx, yy + 0.10, 0.035, lh - 0.20, fill=[T.BLUE, T.CYAN, T.PURPLE, T.GREEN][i],
             alpha=0.85, radius=0.5)
        num = tb(s, lx + 0.18, yy + 0.10, 0.34, 0.20,
                 [{"text": "0%d" % (i + 1), "size": 6.8, "color": T.GRAY_3, "font": T.EN}], anchor="m")
        nm = tb(s, lx + 0.18, yy + 0.30, 1.06, 0.34,
                [{"text": layer["name"], "size": 12, "color": T.WHITE}], anchor="m")
        A(nm, "fadeLeft", 0.8 + i * 0.18, 0.55)
        line(s, lx + 1.28, yy + 0.18, lx + 1.28, yy + lh - 0.18, color="FFFFFF", width=0.75, alpha=0.10)
        # pills
        ix = lx + 1.42
        for j, item in enumerate(layer["items"][:4]):
            iw = min(1.18, 0.28 + 0.082 * len(item))
            p = pill(s, ix, yy + 0.31, iw, 0.34, item, size=7.4, color=T.GRAY_2,
                     fill="FFFFFF", alpha=0.05, line="FFFFFF", line_alpha=0.10, font=T.CN)
            A(p, "fade", 0.95 + i * 0.18 + j * 0.05, 0.45)
            ix += iw + 0.09

    foot = tb(s, 0.95, 6.62, 11.4, 0.26,
              [{"text": "前后端分离  ·  SSE 流式对话  ·  WebSocket 实时消息  ·  JWT 三角色鉴权",
                "size": 9, "color": T.GRAY_3, "spc": 60}], align="c", anchor="m")
    A(foot, "fade", 1.9, 0.8)
    footer(s, 8)
    return s


# =============================================================== 09  feature matrix
def slide_matrix(prs):
    s = new_slide(prs)
    background(s, "bg_06_features.jpg", [
        (1.0, 0.2, 5.0, 4.0, T.BLUE, 0.08),
        (7.6, 3.6, 5.2, 4.2, T.PURPLE, 0.08),
    ])
    TRANSITION("fade", 1.0, advance=11.0)
    k = kicker(s, "功能全景", 0, 0.58, T.BLUE, w=SLIDE_W, align="c")
    A(k, "fadeUp", 0.2, 0.7)
    t = tb(s, 0, 0.86, SLIDE_W, 0.62,
           [{"text": "三端协同，各司其职。", "size": 32, "color": T.WHITE, "font": T.CN_LIGHT}],
           align="c", anchor="m")
    A(t, "fadeUp", 0.4, 0.85)
    sub = tb(s, 0, 1.50, SLIDE_W, 0.28,
             [{"text": "同一套账号与数据，三种角色视角，核心功能一览。", "size": 10.5, "color": T.GRAY}],
             align="c", anchor="m")
    A(sub, "fadeUp", 0.6, 0.65)

    cols = [
        ("学生端", "Student", T.BLUE, C.FEATURES_MATRIX["student"]),
        ("教师端", "Teacher", T.ORANGE, C.FEATURES_MATRIX["teacher"]),
        ("管理员", "Admin", T.PURPLE, C.FEATURES_MATRIX["admin"]),
    ]
    cw, gap, cy, ch = 3.55, 0.30, 2.02, 4.58
    x0 = (SLIDE_W - (3 * cw + 2 * gap)) / 2
    for ci, (cn, en, tone, items) in enumerate(cols):
        x = x0 + ci * (cw + gap)
        card = rect(s, x, cy, cw, ch, fill="FFFFFF", alpha=0.04, radius=0.045,
                    line="FFFFFF", line_w=0.7, line_alpha=0.09)
        A(card, "fadeUp", 0.85 + ci * 0.16, 0.8)
        rect(s, x + 0.24, cy + 0.26, 0.30, 0.045, fill=tone, radius=0.5)
        tb(s, x + 0.24, cy + 0.40, 2.0, 0.36, [{"text": cn, "size": 17, "color": T.WHITE}], anchor="m")
        tb(s, x + cw - 1.30, cy + 0.40, 1.06, 0.36,
           [{"text": en.upper(), "size": 7.4, "color": T.GRAY_3, "spc": 240, "font": T.EN}],
           align="r", anchor="m")
        hairline(s, x + 0.24, cy + 0.88, cw - 0.48, 0.08)
        for ri, item in enumerate(items[:8]):
            yy = cy + 1.02 + ri * 0.42
            ellipse(s, x + 0.28, yy + 0.10, 0.075, 0.075, tone, alpha=0.85)
            tb(s, x + 0.46, yy, cw - 0.66, 0.28,
               [{"text": item, "size": 9.6, "color": "DCDCE2"}], anchor="m")

    cap = tb(s, 0, 6.78, SLIDE_W, 0.24,
             [{"text": "学生 / 教师 / 管理员  ·  路由级权限隔离  ·  按钮级权限控制",
               "size": 8.5, "color": T.GRAY_3, "spc": 60}], align="c", anchor="m")
    A(cap, "fade", 2.2, 0.7)
    footer(s, 9)
    return s


# =============================================================== 10  summary
def slide_summary(prs):
    s = new_slide(prs)
    background(s, "bg_07_summary.jpg", [
        (1.4, 4.6, 7.0, 4.2, T.PURPLE, 0.20),
        (5.8, 5.0, 7.0, 4.0, T.PINK, 0.16),
        (3.0, 4.4, 6.0, 4.4, T.BLUE, 0.16),
    ])
    TRANSITION("fade", 1.4, advance=None)
    k = tb(s, 0, 0.92, SLIDE_W, 0.26,
           [{"text": "WISPATH  CAMPUSMATE", "size": 10, "color": T.GRAY_2, "spc": 420,
             "font": T.EN}], align="c", anchor="m")
    A(k, "fade", 0.3, 1.0)
    t = tb(s, -0.2, 1.42, SLIDE_W + 0.4, 1.98,
           [{"text": line_, "size": 50, "font": T.CN_LIGHT,
             "gradient": [(0, "FFFFFF", 1), (1, "9BC4FF", 1)],
             "color": T.WHITE, "line_spacing": 1.12}
            for line_ in C.SUMMARY["headline"].split("\n")], align="c", anchor="m")
    A(t, "wipeUp", 0.6, 1.1)
    sub = tb(s, 0, 3.66, SLIDE_W, 0.32,
             [{"text": C.SUMMARY["sub"], "size": 14, "color": T.GRAY_2}], align="c", anchor="m")
    A(sub, "fadeUp", 1.7, 0.8)

    vals = C.SUMMARY["values"][:4]
    total_w = 4 * 1.55 + 3 * 0.62
    x0 = (SLIDE_W - total_w) / 2
    for i, v in enumerate(vals):
        x = x0 + i * (1.55 + 0.62)
        tv = tb(s, x, 4.48, 1.55, 0.34, [{"text": v, "size": 15, "color": T.WHITE}],
                align="c", anchor="m")
        A(tv, "fadeUp", 2.35 + i * 0.14, 0.55)
        if i < 3:
            line(s, x + 1.55 + 0.31, 4.50, x + 1.55 + 0.31, 4.80, color="FFFFFF", width=0.75, alpha=0.18)

    cta = tb(s, 0, 5.30, SLIDE_W, 0.36,
             [{"text": C.SUMMARY["cta"], "size": 16, "color": "E8E8ED", "font": T.CN_LIGHT}],
             align="c", anchor="m")
    A(cta, "fadeUp", 3.1, 0.8)

    # logo row
    lx = (SLIDE_W - 3.6) / 2
    gradient_rect(s, lx, 6.28, 0.30, 0.30, [(0, T.BLUE, 1), (1, T.PURPLE, 1)],
                  angle=45, radius=0.28)
    tb(s, lx, 6.28, 0.30, 0.30,
       [{"text": "W", "size": 10, "color": T.WHITE, "bold": True, "font": T.EN}],
       align="c", anchor="m")
    tb(s, lx + 0.40, 6.26, 4.0, 0.34,
       [{"text": C.BRAND["en"] + "  ·  " + C.BRAND["school"], "size": 9, "color": T.GRAY_2,
         "font": T.CN}], anchor="m")
    av = ASSETS / "mascot_avatar.png"
    if av.exists():
        picture(s, av, 11.55, 6.10, 0.62, 0.62)
    footer(s, 10, color="FFFFFF", alpha=0.55)
    return s


# =============================================================== build
BUILDERS = [slide_hello, slide_questions, slide_product, slide_pillars, slide_student,
            slide_teacher, slide_admin, slide_tech, slide_matrix, slide_summary]


def apply_animations(prs, use_anim=True):
    if not (use_anim and ANIM is not None):
        return 0
    applied = 0
    for i, (slide, rec) in enumerate(RECORDS):
        try:
            tl = ANIM.Timeline()
        except Exception:
            return applied
        try:
            import inspect
            add_params = set(inspect.signature(tl.add).parameters)
        except Exception:
            add_params = set()
        for e in rec["effects"]:
            kw = {k: v for k, v in e.items() if k not in ("shape", "preset", "start", "dur")
                  and (not add_params or k in add_params)}
            try:
                tl.add(e["shape"], preset=e["preset"], start=e["start"], dur=e["dur"], **kw)
            except TypeError:
                try:
                    tl.add(e["shape"], e["preset"], start=e["start"], dur=e["dur"])
                except Exception as ex:
                    print("anim add fallback failed slide %d: %s" % (i + 1, ex))
            except Exception as ex:
                print("anim add failed slide %d: %s" % (i + 1, ex))
        if rec.get("transition"):
            try:
                tl.transition(slide, **rec["transition"])
            except Exception as ex:
                print("transition failed slide %d: %s" % (i + 1, ex))
        try:
            tl.apply(slide)
            applied += 1
        except Exception as ex:
            print("anim apply failed slide %d: %s" % (i + 1, ex))
    return applied


def main():
    out = None
    use_anim = True
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out = Path(args[i + 1])
        elif a == "--no-anim":
            use_anim = False
    out = out or (HERE / "out" / "WisPath_CampusMate_宣传片.pptx")
    out.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = E(SLIDE_W)
    prs.slide_height = E(SLIDE_H)
    for idx, fn in enumerate(BUILDERS):
        _current["effects"] = []
        _current["transition"] = None
        slide = fn(prs)
        RECORDS.append((slide, {"effects": list(_current["effects"]),
                                "transition": _current["transition"]}))
        if getattr(C, "NOTES", None):
            n = C.NOTES.get(str(idx + 1))
            if n:
                notes(slide, n)

    prs.core_properties.title = "WisPath CampusMate · 智慧校园 AI 服务平台"
    prs.core_properties.author = C.BRAND["school"]
    prs.core_properties.subject = "苹果风动画产品宣传"
    prs.core_properties.comments = "Powered by python-pptx + native OOXML animation timing"
    n_applied = apply_animations(prs, use_anim)
    prs.save(str(out))
    print(json.dumps({
        "out": str(out),
        "slides": len(prs.slides),
        "copy": COPY_SOURCE,
        "anim_module": bool(ANIM),
        "animated_slides": n_applied,
        "effects": sum(len(r["effects"]) for _, r in RECORDS),
        "size_kb": round(out.stat().st_size / 1024, 1),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
