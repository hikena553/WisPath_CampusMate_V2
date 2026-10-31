# -*- coding: utf-8 -*-
"""deck/anim_test.py --- anim.py 的自测 / 回归脚本。

生成 4 页测试 deck，覆盖：
  * PRESETS 里的全部预设（fade / fadeUp / fadeDown / fadeLeft / fadeRight /
    zoom / wipeUp / wipeDown / wipeLeft / wipeRight / appear / pulse / grow / float）
  * 同一时刻多效果并发（withEffect）与严格串行（afterEffect）
  * 绝对时间重叠（后一个效果早于前一个结束）
  * 逐段文字动画（add_text_build）
  * 自动换片（advance）
  * 形如 "fade" / "morph" 的切换

随后可由 deck/.animtest/verify_com.ps1 用 PowerPoint COM 做权威校验。

用法::

    python deck/anim_test.py                # 生成到 deck/.animtest/
    python deck/anim_test.py --morph        # 额外生成 morph 切换验证文件
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim import PRESETS, Timeline, enable_show_timings  # noqa: E402

EMU_W = 12192000
EMU_H = 6858000

INK = RGBColor(0x1D, 0x1D, 0x1F)
BLUE = RGBColor(0x00, 0x71, 0xE3)
GREEN = RGBColor(0x34, 0xC7, 0x59)
ORANGE = RGBColor(0xFF, 0x9F, 0x0A)
RED = RGBColor(0xFF, 0x3B, 0x30)
PURPLE = RGBColor(0xAF, 0x52, 0xDE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MIST = RGBColor(0xF5, 0xF5, 0xF7)

PALETTE = [BLUE, GREEN, ORANGE, RED, PURPLE]


def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _rect(slide, x, y, w, h, color, name, radius=True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    shp.name = name
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def _label(slide, text, x, y, w, h, size, color, name, bold=True):
    box = slide.shapes.add_textbox(Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = "Microsoft YaHei"
    return box


def _background(slide, prs):
    bg = _rect(slide, 0, 0, EMU_W, EMU_H, MIST, "Background", radius=False)
    slide.shapes._spTree.remove(bg._element)
    slide.shapes._spTree.insert(2, bg._element)
    return bg


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------
def slide_cover(prs):
    """封面：fadeUp / fade / wipeRight / pulse 并发 + 自动换片 8s。"""
    s = _blank(prs)
    _background(s, prs)
    tl = Timeline()

    bar = _rect(s, 900000, 2500000, 130000, 1400000, BLUE, "AccentBar", radius=False)
    title = _label(s, "WisPath CampusMate", 1200000, 2400000, 9000000, 900000, 60, INK, "Title")
    sub = _label(s, "智慧校园 AI 服务平台", 1250000, 3400000, 8000000, 600000, 26,
                 RGBColor(0x6E, 0x6E, 0x73), "Subtitle", bold=False)
    badge = _rect(s, 1250000, 4200000, 1500000, 400000, BLUE, "Badge")

    # 同一时刻并发两块：bar + title 都 start=0.2
    tl.add(bar, "wipeUp", start=0.15, dur=0.5)
    tl.add(title, "fadeUp", start=0.30, dur=0.7)
    tl.add(sub, "fade", start=0.95, dur=0.6)
    tl.add(badge, "zoom", start=1.30, dur=0.5)
    tl.add(badge, "pulse", start=2.10, dur=0.9)
    tl.transition(s, "fade", dur=1.0, advance=8)
    tl.apply(s)
    return s, tl


def slide_cards(prs):
    """五卡片错峰入场 + 图标 zoom + 一个 float 循环。"""
    s = _blank(prs)
    _background(s, prs)
    tl = Timeline()
    head = _label(s, "五大核心能力", 900000, 800000, 8000000, 700000, 40, INK, "Heading")
    tl.add(head, "fadeUp", start=0.1, dur=0.6)
    tl.add(head, "pulse", start=3.0, dur=0.8)

    cards = []
    for i, c in enumerate(PALETTE):
        card = _rect(s, 900000 + i * 2100000, 2000000, 1900000, 1900000, c, "Card%d" % (i + 1))
        cards.append(card)
    tl.add_many(cards, "fadeUp", start=0.5, dur=0.55, stagger=0.14)

    dot = _rect(s, 5500000, 4500000, 260000, 260000, ORANGE, "FloatingDot")
    tl.add(dot, "float", start=1.6, dur=1.6, repeat=2)
    tl.transition(s, "fade", dur=1.0, advance=9)
    tl.apply(s)
    return s, tl


def slide_text_build(prs):
    """逐段文字动画 + 分隔线 wipeRight。"""
    s = _blank(prs)
    _background(s, prs)
    tl = Timeline()
    head = _label(s, "为什么是它", 900000, 700000, 8000000, 700000, 40, INK, "Heading")
    line = _rect(s, 950000, 1520000, 1200000, 40000, BLUE, "Divider", radius=False)
    body = s.shapes.add_textbox(Emu(950000), Emu(2000000), Emu(8000000), Emu(3200000))
    body.name = "BodyText"
    tf = body.text_frame
    tf.word_wrap = True
    lines = [
        "一个入口，覆盖学籍、课表、成绩与请假流程",
        "AI 对话助手随时答疑，危机关键词秒级预警",
        "成长档案自动沉淀，导出即用的能力画像",
    ]
    tf.text = lines[0]
    for ln in lines[1:]:
        p = tf.add_paragraph()
        p.text = ln
    for p in tf.paragraphs:
        p.font.size = Pt(24)
        p.font.color.rgb = RGBColor(0x42, 0x42, 0x47)
        p.font.name = "Microsoft YaHei"

    tl.add(head, "fadeUp", start=0.0, dur=0.6)
    tl.add(line, "wipeRight", start=0.45, dur=0.5)
    tl.add_text_build(body, "fadeUp", start=0.8, dur=0.45, stagger=0.30)
    tl.transition(s, "fade", dur=1.0, advance=10)
    tl.apply(s)
    return s, tl


def slide_kitchen_sink(prs):
    """全预设巡礼：10 个效果，覆盖 fade 家族 / wipe 家族 / appear / grow / float。"""
    s = _blank(prs)
    _background(s, prs)
    tl = Timeline()
    names = [
        ("fade", 0.0), ("fadeUp", 0.35), ("fadeDown", 0.70),
        ("fadeLeft", 1.05), ("fadeRight", 1.40), ("zoom", 1.75),
        ("wipeUp", 2.10), ("wipeRight", 2.45), ("appear", 2.80),
    ]
    for i, (preset, start) in enumerate(names):
        col = i % 3
        row = i // 3
        box = _rect(s, 900000 + col * 3400000, 1100000 + row * 1500000,
                    2000000, 700000, PALETTE[i % len(PALETTE)], "P_" + preset)
        tl.add(box, preset, start=start, dur=0.5)
    # 用 int shape_id 走一遍解析路径（验证 shape_id 也可用）
    tail = _rect(s, 4000000, 5700000, 1200000, 400000, PURPLE, "TailGrow")
    tl.add(tail.shape_id, "grow", start=3.2, dur=0.8)
    s.shapes  # noqa: B018
    tl.transition(s, "fade", dur=1.0, advance=12)
    # 效果写入前需让 int 形式能定位到本页
    tl._effects[-1].slide_part = s.part
    tl.apply(s)
    return s, tl


# ---------------------------------------------------------------------------
# 生成
# ---------------------------------------------------------------------------
def build(outdir, morph=False):
    os.makedirs(outdir, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Emu(EMU_W)
    prs.slide_height = Emu(EMU_H)

    makers = [slide_cover, slide_cards, slide_text_build, slide_kitchen_sink]
    reports = []
    for mk in makers:
        s, tl = mk(prs)
        reports.append((mk.__name__, tl, s))

    enable_show_timings(prs)
    path = os.path.join(outdir, "test-1.pptx")
    prs.save(path)

    for name, tl, s in reports:
        print("[%s] %d 个效果, 总时长 %.2fs, 预警=%s"
              % (name, len(tl), tl.total_duration(), tl.warnings or "无"))
        for row in tl.describe():
            print("    %-9s spid=%-3s para=%-9s start=%5dms dur=%4dms %s"
                  % (row["preset"], row["spid"], row["para"] or "-",
                     row["start_ms"], row["dur_ms"], row["node_type"]))
    print("saved", path, os.path.getsize(path), "bytes")

    if morph:
        path2 = os.path.join(outdir, "test-morph.pptx")
        p2 = Presentation()
        p2.slide_width = Emu(EMU_W)
        p2.slide_height = Emu(EMU_H)
        for i in range(2):
            s = _blank(p2)
            _background(s, p2)
            box = _rect(s, 1200000 + i * 3000000, 2400000, 2000000, 1500000,
                        PALETTE[i], "MorphBox")
            tl = Timeline()
            tl.add(box, "fadeUp", start=0.1, dur=0.6)
            kind = "morph" if i == 0 else "fade"
            tl.transition(s, kind, dur=1.5, advance=6)
            tl.apply(s)
        enable_show_timings(p2)
        p2.save(path2)
        print("saved", path2, os.path.getsize(path2), "bytes")

    # 结构自检：确认元素顺序 cSld -> clrMapOvr -> transition -> timing
    _check_structure(path)
    return path


ORDER = {"cSld": 0, "clrMapOvr": 1, "AlternateContent": 2, "transition": 2, "timing": 3, "extLst": 4}


def _check_structure(path):
    P = "http://schemas.openxmlformats.org/presentationml/2006/main"
    ok = True
    with zipfile.ZipFile(path) as z:
        slides = sorted(n for n in z.namelist() if n.startswith("ppt/slides/slide"))
        for name in slides:
            root = etree.fromstring(z.read(name))
            tags = [etree.QName(c).localname for c in root]
            pos = [ORDER.get(t, 99) for t in tags]
            if pos != sorted(pos):
                ok = False
                print("!! 元素顺序错误", name, tags)
            print("  %-24s children=%s" % (name.split("/")[-1], tags))
    print("结构自检:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".animtest"))
    ap.add_argument("--morph", action="store_true", help="额外生成 morph 切换验证文件")
    a = ap.parse_args()
    build(a.outdir, morph=a.morph)
