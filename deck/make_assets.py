# -*- coding: utf-8 -*-
"""
WisPath CampusMate deck 视觉素材生成器（Apple 发布会深色主视觉）

纯脚本、可重复运行：
    python deck/make_assets.py                  # 全量生成 + 自检
    python deck/make_assets.py --stage bg       # 只做背景
    python deck/make_assets.py --stage icon     # 只做图标
    python deck/make_assets.py --stage mascot   # 只做吉祥物
    python deck/make_assets.py --stage sheet    # 只做 contact sheet
    python deck/make_assets.py --stage check    # 只跑自检
    python deck/make_assets.py --only bg_00_hero,bg_03_student

产物全部落在 deck/assets/。
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

W, H = 2560, 1440          # 背景画布
ICON = 512                 # 图标画布
SS = 4                     # 图标超采样倍率

# Apple 强调色（只允许出现在光晕里）
BLUE = "#0A84FF"
CYAN = "#64D2FF"
PURPLE = "#BF5AF2"
PINK = "#FF375F"
ORANGE = "#FF9F0A"
GREEN = "#30D158"
INDIGO = "#5E5CE6"
WARM = "#FFE6CC"
WHITE = "#FFFFFF"


# --------------------------------------------------------------------------
# 色彩：光晕在线性光空间相加，最后 filmic 压回 sRGB —— 混色自然、不发灰
# --------------------------------------------------------------------------
def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0).astype(np.float32)
    return np.where(c <= 0.0031308, c * 12.92,
                    1.055 * np.power(c, 1.0 / 2.4) - 0.055).astype(np.float32)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# --------------------------------------------------------------------------
# 背景引擎
# --------------------------------------------------------------------------
_YY = None
_XX = None


def _grid():
    global _YY, _XX
    if _XX is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _YY, _XX = yy, xx
    return _YY, _XX


def _plate_ramp(top="#05060A", mid="#0B0D14", bot="#06070B", mid_at=0.52):
    """近黑垂直渐变 #05060A -> #0B0D14 -> 微压暗，返回 (H,1,3) 线性光。"""
    t = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    c0, c1, c2 = (srgb_to_linear(hex_rgb(x)) for x in (top, mid, bot))
    f1 = smoothstep(t / mid_at)[:, :, None]
    f2 = smoothstep((t - mid_at) / (1.0 - mid_at))[:, :, None]
    lo = c0[None, None, :] * (1 - f1) + c1[None, None, :] * f1
    hi = c1[None, None, :] * (1 - f2) + c2[None, None, :] * f2
    return np.where(t[:, :, None] < mid_at, lo, hi)


def _glow(color, cx, cy, rx, ry, inten, rot=0.0, k=1.25):
    """单个各向异性（可旋转）高斯光斑；cx/cy 可 <0 或 >1，允许柔和溢边。"""
    return dict(color=color, cx=cx, cy=cy, rx=rx, ry=ry, inten=inten, rot=rot, k=k)


def _bloom(color, cx, cy, rx, ry, core, halo, rot=0.0, scale=2.1,
           core_k=2.0, halo_k=1.15):
    """核心亮斑 + 外围宽晕；Apple 风格的光都是这样两层叠出来的。"""
    return [
        _glow(color, cx, cy, rx, ry, core, rot=rot, k=core_k),
        _glow(color, cx, cy, rx * scale, ry * scale, halo, rot=rot, k=halo_k),
    ]


def _glow_field(g):
    yy, xx = _grid()
    cx, cy = g["cx"] * W, g["cy"] * H
    dx = xx - cx
    dy = yy - cy
    if g["rot"]:
        ca, sa = math.cos(g["rot"]), math.sin(g["rot"])
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
    else:
        u, v = dx, dy
    q2 = (u / g["rx"]) ** 2 + (v / g["ry"]) ** 2
    return np.exp(-g["k"] * q2, dtype=np.float32) * g["inten"]


def _zone(cx, cy, rx, ry, strength, rot=0.0):
    """文字安全暗区：对光晕做柔和衰减（1 - strength*高斯），没有硬边。"""
    yy, xx = _grid()
    dx = xx - cx * W
    dy = yy - cy * H
    if rot:
        ca, sa = math.cos(rot), math.sin(rot)
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
    else:
        u, v = dx, dy
    q2 = (u / rx) ** 2 + (v / ry) ** 2
    return 1.0 - strength * np.exp(-1.0 * q2).astype(np.float32)


def _vignette(strength, inner=0.42, outer=1.14):
    yy, xx = _grid()
    nx = xx / W - 0.5
    ny = yy / H - 0.5
    d = np.sqrt(nx * nx + ny * ny) / math.sqrt(0.5)
    return (1.0 - strength * smoothstep((d - inner) / (outer - inner))).astype(np.float32)


def _grain(img, amp=0.011, seed=7, cells=1):
    """胶片颗粒：低频噪声放大 + 1/255 抖动，压住 8bit 色带又不脏。"""
    rng = np.random.default_rng(seed)
    hh, ww = max(2, H // cells), max(2, W // cells)
    n = rng.standard_normal((hh, ww)).astype(np.float32)
    if cells > 1:
        n = np.array(Image.fromarray(n, mode="F").resize((W, H), Image.BILINEAR), dtype=np.float32)
    n /= max(1e-6, float(n.std()))
    a = np.asarray(img, dtype=np.float32) / 255.0
    a = a + (n * amp)[..., None]
    a = a + (rng.random((H, W, 1), dtype=np.float32) - 0.5) / 255.0
    return Image.fromarray(np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB")


def render_bg(spec):
    plate = _plate_ramp(**spec.get("plate", {}))
    total = np.broadcast_to(plate, (H, W, 3)).copy()
    glow = np.zeros((H, W, 3), dtype=np.float32)
    for g in spec["glows"]:
        glow += _glow_field(g)[..., None] * srgb_to_linear(hex_rgb(g["color"]))
    for z in spec.get("zones", []):
        glow *= _zone(**z)[..., None]
    total += glow
    disp = 1.0 - np.exp(-np.maximum(total, 0.0))          # filmic 高光压缩
    disp *= _vignette(spec.get("vignette", 0.26))[..., None]
    out = linear_to_srgb(disp)
    img = Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB")
    return _grain(img, amp=spec.get("grain", 0.011), seed=spec.get("seed", 7),
                  cells=spec.get("grain_cells", 1))


# --------------------------------------------------------------------------
# 9 张背景构图（坐标、半径均为画布比例；每张最多 2~3 组光源，留大片干净暗区）
# --------------------------------------------------------------------------
BACKGROUNDS = {
    # 主视觉：右上紫蓝大光晕（偏上 70%），左下蓝色小光晕，中心偏左留暗区
    "bg_00_hero": dict(
        glows=(
            _bloom(PURPLE, 0.885, 0.075, 480, 430, 0.42, 0.024, rot=-0.35)
            + _bloom(BLUE, 0.755, 0.225, 320, 300, 0.20, 0.014, rot=-0.45)
            + [_glow(INDIGO, 0.820, -0.030, 620, 460, 0.014, rot=-0.3, k=1.1),
               _glow(CYAN, 0.985, 0.240, 220, 205, 0.07, k=2.2)]
            + _bloom(BLUE, 0.060, 0.930, 300, 270, 0.15, 0.015)
        ),
        zones=[dict(cx=0.22, cy=0.56, rx=950, ry=800, strength=0.72)],
        vignette=0.32, grain=0.012, seed=101,
        text_safe=(0.05, 0.28, 0.47, 0.80),
    ),
    # 悬念页：极暗冷调，底部蓝色细光带，上方几乎纯黑
    "bg_01_question": dict(
        plate=dict(top="#040508", mid="#07080E", bot="#05060A", mid_at=0.60),
        glows=(
            [_glow(BLUE, 0.500, 1.040, 1400, 150, 0.16, k=1.8),
             _glow(BLUE, 0.500, 1.030, 1500, 360, 0.050, k=1.2),
             _glow(CYAN, 0.500, 1.052, 900, 70, 0.13, k=2.0),
             _glow(CYAN, 0.500, 1.070, 1100, 200, 0.030, k=1.2),
             _glow(INDIGO, 0.920, -0.060, 620, 380, 0.035, rot=0.4, k=1.3)]
        ),
        zones=[dict(cx=0.50, cy=0.52, rx=1100, ry=420, strength=0.30)],
        vignette=0.30, grain=0.012, seed=102,
        text_safe=(0.14, 0.14, 0.86, 0.62),
    ),
    # 产品页：正后方偏白暖光（聚光灯），左右翼蓝/紫弱光，中心亮四角暗
    "bg_02_product": dict(
        glows=(
            _bloom("#DCE6FF", 0.500, 0.455, 330, 315, 0.29, 0.015, scale=2.2)
            + _bloom("#F2F6FF", 0.500, 0.425, 165, 155, 0.12, 0.005, scale=2.4, halo_k=1.4)
            + _bloom(BLUE, 0.120, 0.500, 290, 310, 0.13, 0.012, core_k=1.9)
            + _bloom(INDIGO, 0.880, 0.500, 290, 310, 0.13, 0.012, core_k=1.9)
        ),
        vignette=0.36, grain=0.011, seed=103,
        text_safe=(0.10, 0.04, 0.90, 0.24),
    ),
    # 学生页：左侧蓝青双光晕（手机区），右半干净暗区放文字
    "bg_03_student": dict(
        glows=(
            _bloom(BLUE, 0.120, 0.380, 470, 440, 0.30, 0.024, rot=0.25)
            + _bloom(CYAN, 0.270, 0.680, 370, 350, 0.21, 0.020, rot=0.35)
            + [_glow(INDIGO, 0.000, 0.060, 700, 500, 0.024, k=1.1)]
        ),
        zones=[dict(cx=0.90, cy=0.50, rx=800, ry=900, strength=0.60)],
        vignette=0.27, grain=0.012, seed=104,
        text_safe=(0.52, 0.14, 0.96, 0.86),
    ),
    # 教师页：右侧橙粉双光晕（手机区），左半干净暗区放文字
    "bg_04_teacher": dict(
        glows=(
            _bloom(ORANGE, 0.875, 0.380, 470, 440, 0.34, 0.018, rot=-0.25)
            + _bloom(PINK, 0.725, 0.680, 370, 350, 0.22, 0.018, rot=-0.35)
            + [_glow(PINK, 0.980, 0.060, 620, 460, 0.024, k=1.1)]
        ),
        zones=[dict(cx=0.10, cy=0.50, rx=800, ry=900, strength=0.60)],
        vignette=0.27, grain=0.012, seed=105,
        text_safe=(0.04, 0.14, 0.48, 0.86),
    ),
    # 管理页：顶部蓝色横向光束 + 底部紫色弱光，中间暗放仪表盘
    "bg_05_admin": dict(
        glows=(
            [_glow(BLUE, 0.470, -0.020, 1400, 230, 0.20, k=1.8, rot=0.03),
             _glow(BLUE, 0.470, -0.020, 1500, 430, 0.030, k=1.2, rot=0.03),
             _glow(CYAN, 0.250, -0.040, 700, 150, 0.10, k=1.9, rot=0.04),
             _glow(PURPLE, 0.560, 1.060, 1100, 260, 0.10, k=1.5),
             _glow(PURPLE, 0.560, 1.050, 1000, 430, 0.024, k=1.2)]
        ),
        zones=[dict(cx=0.50, cy=0.56, rx=1050, ry=520, strength=0.45)],
        vignette=0.28, grain=0.011, seed=106,
        text_safe=(0.06, 0.30, 0.94, 0.44),
    ),
    # 功能矩阵页：极简，三条极弱竖向光柱，几乎全黑，不抢文字
    "bg_06_features": dict(
        glows=(
            [_glow(BLUE, 0.275, 0.560, 120, 850, 0.011, k=1.6),
             _glow(BLUE, 0.275, 0.560, 380, 950, 0.0015, k=1.2),
             _glow(PURPLE, 0.515, 0.500, 110, 900, 0.010, k=1.6),
             _glow(PURPLE, 0.515, 0.500, 360, 960, 0.0013, k=1.2),
             _glow(CYAN, 0.760, 0.580, 120, 850, 0.009, k=1.6),
             _glow(CYAN, 0.760, 0.580, 380, 920, 0.0012, k=1.2),
             _glow(INDIGO, 0.500, 0.420, 700, 500, 0.001, k=1.0)]
        ),
        vignette=0.26, grain=0.011, seed=107,
        text_safe=(0.08, 0.18, 0.92, 0.82),
    ),
    # 收官页：底部多色极光（蓝->青->紫->粉 横向流动），文字区上方仍暗
    "bg_07_summary": dict(
        glows=(
            _bloom(BLUE, 0.080, 1.030, 620, 330, 0.16, 0.012, rot=-0.12, core_k=1.3, halo_k=1.1)
            + _bloom(CYAN, 0.280, 1.050, 600, 320, 0.16, 0.012, rot=-0.05, core_k=1.3, halo_k=1.1)
            + _bloom(INDIGO, 0.500, 1.010, 640, 340, 0.16, 0.012, rot=0.02, core_k=1.3, halo_k=1.1)
            + _bloom(PURPLE, 0.710, 1.040, 620, 330, 0.16, 0.012, rot=0.07, core_k=1.3, halo_k=1.1)
            + _bloom(PINK, 0.900, 1.000, 600, 330, 0.145, 0.011, rot=0.13, core_k=1.3, halo_k=1.1)
            + [_glow(WHITE, 0.500, 0.600, 1000, 700, 0.006, k=1.0)]
        ),
        zones=[dict(cx=0.50, cy=0.05, rx=1250, ry=460, strength=0.50)],
        vignette=0.24, grain=0.012, seed=108,
        text_safe=(0.10, 0.08, 0.90, 0.54),
    ),
    # 技术页：左侧青、右侧紫弱光，中心暗
    "bg_08_tech": dict(
        glows=(
            _bloom(CYAN, 0.080, 0.500, 520, 600, 0.13, 0.013, rot=0.15, core_k=1.9)
            + _bloom(PURPLE, 0.920, 0.500, 520, 600, 0.13, 0.013, rot=-0.15, core_k=1.9)
        ),
        zones=[dict(cx=0.50, cy=0.50, rx=780, ry=900, strength=0.58)],
        vignette=0.28, grain=0.012, seed=109,
        text_safe=(0.22, 0.14, 0.78, 0.86),
    ),
}

JPEG_Q = 95
JPEG_SUBSAMPLING = 2   # 4:2:0：体积友好，画质无感


def save_jpeg(img, path, quality=JPEG_Q, budget_kb=900):
    q = quality
    for _ in range(4):
        img.save(path, "JPEG", quality=q, subsampling=JPEG_SUBSAMPLING,
                 optimize=True, progressive=True)
        if path.stat().st_size <= budget_kb * 1024:
            return q
        q -= 1
    return q


def build_backgrounds(only=None):
    made = {}
    for name, spec in BACKGROUNDS.items():
        if only and name not in only:
            continue
        spec = dict(spec)
        safe = spec.pop("text_safe", None)
        img = render_bg(spec)
        p = ASSETS / (name + ".jpg")
        q = save_jpeg(img, p)
        made[name] = dict(path=p, quality=q, bytes=p.stat().st_size)
        print(f"[bg] {p.name:20s} {img.size[0]}x{img.size[1]} mode=RGB q={q} "
              f"{p.stat().st_size/1024:7.1f} KB")
    return made


# --------------------------------------------------------------------------
# 图标：SF Symbols 风格极简几何，白色描边、圆头、512x512、4x 超采样
# --------------------------------------------------------------------------
ICON_LW = 26                                  # 成品线宽（512px 画布）
ICON_NAMES = ["chat", "spark", "chart", "calendar", "grade", "leave", "shield",
              "heart", "users", "settings", "monitor", "knowledge", "message",
              "bell", "phone", "lock", "clock", "book", "compass", "target"]


class Pen:
    """在 4x 画布上用 [-1,1] 归一化坐标绘制，线宽 / 圆头 / 圆角全部一致。"""

    def __init__(self, draw, size, lw):
        self.d = draw
        self.R = 0.39 * size                   # [-1,1] 映射到画布 78%
        self.c = size / 2.0
        self.lw = lw

    def p(self, x, y):
        return (self.c + x * self.R, self.c + y * self.R)

    def cap(self, pt):
        r = self.lw / 2.0
        self.d.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=255)

    def line(self, pts, close=False):
        pp = [self.p(*q) for q in pts]
        if close:
            pp = pp + [pp[0]]
        self.d.line(pp, fill=255, width=int(self.lw), joint="curve")
        for pt in pp:
            self.cap(pt)

    def bezier(self, pts, samples=24):
        """pts = 起点 + 若干组 (c1,c2,end)，绝对坐标。"""
        out = [pts[0]]
        for i in range(1, len(pts), 3):
            p0, p1, p2, p3 = out[-1], pts[i], pts[i + 1], pts[i + 2]
            for k in range(1, samples + 1):
                t = k / samples
                m = 1.0 - t
                x = m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0]
                y = m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]
                out.append((x, y))
        self.line(out)

    def arc(self, cx, cy, r, a0, a1):
        n = max(8, int(abs(a1 - a0) / 3))
        pts = []
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.line(pts)

    def circle(self, cx, cy, r):
        c = self.p(cx, cy)
        ro = r * self.R
        ri = ro - self.lw
        self.d.ellipse([c[0] - ro, c[1] - ro, c[0] + ro, c[1] + ro], fill=255)
        if ri > 0:
            self.d.ellipse([c[0] - ri, c[1] - ri, c[0] + ri, c[1] + ri], fill=0)

    def rrect(self, x0, y0, x1, y1, r):
        a = self.p(x0, y0)
        b = self.p(x1, y1)
        self.d.rounded_rectangle([a[0], a[1], b[0], b[1]], radius=r * self.R,
                                 outline=255, width=int(round(self.lw)))

    def dot(self, cx, cy, r):
        c = self.p(cx, cy)
        ro = r * self.R
        self.d.ellipse([c[0] - ro, c[1] - ro, c[0] + ro, c[1] + ro], fill=255)


def _sparkle(cx, cy, r, power=2.8, n=120):
    """四角星（凹边）轮廓点。"""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        x = math.copysign(abs(c) ** power, c)
        y = math.copysign(abs(s) ** power, s)
        pts.append((cx + x * r, cy + y * r))
    return pts


def _heart_pts(n=160, size=1.88):
    raw = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        raw.append((x, -y))
    xs = [q[0] for q in raw]
    ys = [q[1] for q in raw]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    s = size / max(w, h)
    mx = (max(xs) + min(xs)) / 2
    my = (max(ys) + min(ys)) / 2
    return [((x - mx) * s, (y - my) * s) for x, y in raw]


# ---- 20 个图标：只保留最强识别特征，宁可简单 ----
def _i_chat(p):
    p.rrect(-0.86, -0.72, 0.86, 0.40, 0.30)
    p.line([(-0.44, 0.40), (-0.52, 0.80), (-0.02, 0.40)])
    p.dot(-0.34, -0.16, 0.105)
    p.dot(0.34, -0.16, 0.105)


def _i_spark(p):
    p.line(_sparkle(0.0, 0.06, 0.86), close=True)
    p.line(_sparkle(0.60, -0.60, 0.30), close=True)


def _i_chart(p):
    for x, top in ((-0.54, -0.06), (0.0, -0.74), (0.54, -0.34)):
        p.line([(x, 0.78), (x, top)])


def _i_calendar(p):
    p.rrect(-0.82, -0.60, 0.82, 0.83, 0.20)
    p.line([(-0.36, -0.86), (-0.36, -0.54)])
    p.line([(0.36, -0.86), (0.36, -0.54)])


def _i_grade(p):
    p.line([(-0.78, 0.55), (-0.30, 0.05), (0.12, 0.40), (0.78, -0.55)])
    p.dot(-0.30, 0.05, 0.14)


def _i_leave(p):
    p.rrect(-0.58, -0.85, 0.60, 0.85, 0.16)
    p.line([(-0.26, 0.0), (-0.04, 0.24), (0.34, -0.26)])


def _i_shield(p):
    p.line([(0, -0.90), (0.72, -0.66), (0.72, 0.05)])
    p.bezier([(0.72, 0.05), (0.70, 0.58), (0.42, 0.82), (0, 0.92)])
    p.bezier([(0, 0.92), (-0.42, 0.82), (-0.70, 0.58), (-0.72, 0.05)])
    p.line([(-0.72, 0.05), (-0.72, -0.66), (0, -0.90)])
    p.line([(-0.27, 0.02), (-0.05, 0.26), (0.33, -0.24)])


def _i_heart(p):
    p.line(_heart_pts(), close=True)


def _i_users(p):
    # 后排（小）：头 + 右肩弧
    p.circle(0.40, -0.52, 0.21)
    p.arc(0.40, 0.19, 0.50, 218, 334)
    # 前排（大）：头 + 左肩弧
    p.circle(-0.30, -0.46, 0.28)
    p.arc(-0.30, 0.44, 0.62, 196, 344)


def _i_settings(p):
    # 8 齿齿轮：根部 0.56 / 齿顶 0.86 的多边形轮廓，圆角靠圆头衔接
    teeth, r_root, r_tip = 8, 0.56, 0.86
    pts = []
    for i in range(teeth):
        a = 360.0 * i / teeth
        for ang, r in ((a - 15.5, r_root), (a - 8.0, r_tip),
                       (a + 8.0, r_tip), (a + 15.5, r_root)):
            rad = math.radians(ang - 90.0)
            pts.append((r * math.cos(rad), r * math.sin(rad)))
    p.line(pts, close=True)
    p.circle(0.0, 0.0, 0.26)


def _i_monitor(p):
    p.rrect(-0.92, -0.76, 0.92, 0.42, 0.16)
    p.line([(0.0, 0.42), (0.0, 0.70)])
    p.line([(-0.44, 0.78), (0.44, 0.78)])


def _i_knowledge(p):
    # 合上的书：圆角书体 + 书脊线（极简，一眼是书）
    p.rrect(-0.62, -0.82, 0.62, 0.84, 0.11)
    p.line([(-0.36, -0.82), (-0.36, 0.84)])


def _i_message(p):
    # 大气泡（右上）+ 小气泡（左下），各带一个小尾巴
    p.rrect(0.02, -0.76, 0.92, 0.26, 0.22)
    p.line([(0.52, 0.26), (0.60, 0.56), (0.78, 0.26)])
    p.rrect(-0.92, -0.18, -0.10, 0.64, 0.20)
    p.line([(-0.58, 0.64), (-0.66, 0.90), (-0.32, 0.64)])


def _i_bell(p):
    p.line([(-0.68, 0.42), (-0.60, -0.10)])
    p.arc(0.0, -0.10, 0.60, 180, 360)
    p.line([(0.60, -0.10), (0.68, 0.42)])
    p.line([(-0.86, 0.42), (0.86, 0.42)])
    p.line([(0.0, -0.88), (0.0, -0.74)])
    p.dot(0.0, 0.66, 0.10)


def _i_phone(p):
    p.rrect(-0.46, -0.92, 0.46, 0.92, 0.18)
    p.line([(-0.14, -0.74), (0.14, -0.74)])


def _i_lock(p):
    p.rrect(-0.66, -0.02, 0.66, 0.86, 0.16)
    p.arc(0.0, -0.02, 0.40, 180, 360)
    p.line([(-0.40, -0.02), (-0.40, 0.08)])
    p.line([(0.40, -0.02), (0.40, 0.08)])
    p.dot(0.0, 0.42, 0.10)


def _i_clock(p):
    p.circle(0.0, 0.0, 0.90)
    p.line([(0.0, 0.0), (0.0, -0.50)])
    p.line([(0.0, 0.0), (0.34, 0.14)])


def _i_book(p):
    p.bezier([(-0.90, -0.55), (-0.62, -0.78), (-0.24, -0.74), (0.0, -0.50)])
    p.bezier([(0.0, -0.50), (0.24, -0.74), (0.62, -0.78), (0.90, -0.55)])
    p.line([(0.90, -0.55), (0.90, 0.48)])
    p.bezier([(0.90, 0.48), (0.62, 0.30), (0.24, 0.34), (0.0, 0.60)])
    p.bezier([(0.0, 0.60), (-0.24, 0.34), (-0.62, 0.30), (-0.90, 0.48)])
    p.line([(-0.90, 0.48), (-0.90, -0.55)])
    p.line([(0.0, -0.50), (0.0, 0.60)])


def _i_compass(p):
    p.circle(0.0, 0.0, 0.90)
    p.line([(0.438, -0.438), (0.110, 0.110), (-0.438, 0.438), (-0.110, -0.110)], close=True)


def _i_target(p):
    p.circle(0.0, 0.0, 0.90)
    p.circle(0.0, 0.0, 0.52)
    p.dot(0.0, 0.0, 0.13)


PAINTERS = {
    "chat": _i_chat, "spark": _i_spark, "chart": _i_chart, "calendar": _i_calendar,
    "grade": _i_grade, "leave": _i_leave, "shield": _i_shield, "heart": _i_heart,
    "users": _i_users, "settings": _i_settings, "monitor": _i_monitor,
    "knowledge": _i_knowledge, "message": _i_message, "bell": _i_bell,
    "phone": _i_phone, "lock": _i_lock, "clock": _i_clock, "book": _i_book,
    "compass": _i_compass, "target": _i_target,
}

ICON_TARGET_FILL = 0.78     # 图形长边占画布 78%


def render_icon(name):
    S = ICON * SS
    mask = Image.new("L", (S, S), 0)
    pen = Pen(ImageDraw.Draw(mask), S, ICON_LW * SS)
    PAINTERS[name](pen)
    bbox = mask.getbbox()
    body = mask.crop(bbox)
    scale = ICON_TARGET_FILL * ICON / max(body.size)
    w = max(1, int(round(body.width * scale)))
    h = max(1, int(round(body.height * scale)))
    body = body.resize((w, h), Image.LANCZOS)          # 4x -> 1x，单次 LANCZOS 收边
    canvas = Image.new("L", (ICON, ICON), 0)
    canvas.paste(body, ((ICON - w) // 2, (ICON - h) // 2))
    out = Image.new("RGBA", (ICON, ICON), (255, 255, 255, 0))
    out.putalpha(canvas)
    return out


def build_icons(only=None):
    made = {}
    for name in ICON_NAMES:
        if only and name not in only and ("icon_" + name) not in only:
            continue
        im = render_icon(name)
        p = ASSETS / ("icon_%s.png" % name)
        im.save(p, "PNG", optimize=True)
        cov = float(np.asarray(im)[..., 3].mean()) / 255.0
        made[name] = dict(path=p, coverage=cov)
        print(f"[icon] {p.name:22s} {ICON}x{ICON} RGBA alpha_cov={cov*100:4.1f}% "
              f"{p.stat().st_size/1024:6.1f} KB")
    return made


# --------------------------------------------------------------------------
# 吉祥物：白底 -> 透明（保留蓝线与浅灰描边），裁切留 6%，长边 900 / 头像 1024
# --------------------------------------------------------------------------
MASCOT_SRC = ROOT.parent / "campus-cockpit" / "assets" / "mascot.png"

# 兜底：源图若是不透明白底，用“白色洪水填充”取背景，不误伤白色主体
_FLAT = ((np.ones((1, 1, 4), np.float32) * [[1.0, 0.0, 0.0, 0.0]]))


def _key_white_bg(arr):
    rgb = arr[..., :3].astype(np.float32)
    h, w = rgb.shape[:2]
    dist = np.sqrt(((255.0 - rgb) ** 2).sum(-1))
    near_white = dist < 34
    bg = np.zeros((h, w), bool)
    for sl in (np.s_[:1, :], np.s_[-1:, :], np.s_[:, :1], np.s_[:, -1:]):
        bg[sl] = near_white[sl]
    while True:
        grow = np.zeros_like(bg)
        grow[1:, :] |= bg[:-1, :]
        grow[:-1, :] |= bg[1:, :]
        grow[:, 1:] |= bg[:, :-1]
        grow[:, :-1] |= bg[:, 1:]
        new = grow & near_white & ~bg
        if not new.any():
            break
        bg |= new
    alpha = np.where(bg, 0, arr[..., 3]).astype(np.uint8)
    arr = arr.copy()
    arr[..., 3] = alpha
    return arr


def _clean_alpha(arr, min_area=6):
    """去掉孤立小岛（JPEG/抠图碎屑），保留全部有效笔画。"""
    a = arr[..., 3]
    if a.min() > 250:
        return arr
    solid = a > 40
    lab = np.zeros(a.shape, np.int32)
    cur = 0
    h, w = a.shape
    stack = []
    for y in range(h):
        row = solid[y]
        for x in np.nonzero(row & (lab[y] == 0))[0]:
            cur += 1
            lab[y, x] = cur
            stack.append((y, x))
            area = 0
            while stack:
                cy, cx = stack.pop()
                area += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and solid[ny, nx] and lab[ny, nx] == 0:
                        lab[ny, nx] = cur
                        stack.append((ny, nx))
    if cur == 0:
        return arr
    keep = np.bincount(lab.ravel()) >= min_area
    keep[0] = False
    small = ~keep[lab] & solid
    if small.any():
        arr = arr.copy()
        arr[..., 3] = np.where(small, 0, a).astype(np.uint8)
    return arr


def _load_mascot():
    im = Image.open(MASCOT_SRC).convert("RGBA")
    arr = np.array(im)
    if arr[..., 3].min() > 250:            # 不透明白底 -> 抠白
        arr = _key_white_bg(arr)
    arr = _clean_alpha(arr)
    return Image.fromarray(arr, "RGBA")


def _trim(im, pad_frac=0.06):
    """按 alpha 裁到内容，再四周补 6% 透明边距（源图贴边也能留白）。"""
    arr = np.array(im)
    alpha = arr[..., 3]
    ys, xs = np.where(alpha > 8)
    if len(xs) == 0:
        return im
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    content = im.crop((x0, y0, x1, y1))
    pad = max(1, int(round(max(x1 - x0, y1 - y0) * pad_frac)))
    canvas = Image.new("RGBA", (content.width + 2 * pad, content.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(content, (pad, pad))
    return canvas


def _upscale_rgba(im, target_long, sharpen=True):
    w, h = im.size
    s = target_long / max(w, h)
    size = (max(1, int(round(w * s))), max(1, int(round(h * s))))
    # 预乘 alpha 再缩放：半透明边缘不会发黑 / 发白
    arr = np.array(im).astype(np.float32)
    al = arr[..., 3:4] / 255.0
    pre = np.clip(arr[..., :3] * al + 0.5, 0, 255).astype(np.uint8)
    rgb = Image.fromarray(pre, "RGB").resize(size, Image.LANCZOS)
    mask = Image.fromarray(arr[..., 3].astype(np.uint8), "L").resize(size, Image.LANCZOS)
    if sharpen:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.3, percent=55, threshold=1))
        mask = mask.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=1))
    rgbf = np.array(rgb).astype(np.float32)
    alf = np.array(mask).astype(np.float32) / 255.0
    out = np.zeros((size[1], size[0], 4), np.float32)
    out[..., :3] = np.where(alf[..., None] > 1e-3,
                            rgbf / np.maximum(alf[..., None], 1e-3), 0.0)
    out[..., 3] = alf * 255.0
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), "RGBA")


def _square_avatar(im, target=1024, margin=1.10):
    w, h = im.size
    side = int(round(max(w, h) * margin))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2))
    return _upscale_rgba(canvas, target)


def build_mascot(only=None):
    want = {"mascot_cut", "mascot_avatar"} if not only else only
    src = _load_mascot()
    trimmed = _trim(src, 0.06)
    if "mascot_cut" in want or "icon" in want:
        cut = _upscale_rgba(trimmed, 900)
        p = ASSETS / "mascot_cut.png"
        cut.save(p, "PNG", optimize=True)
        print(f"[mascot] {p.name:22s} {cut.size[0]}x{cut.size[1]} RGBA "
              f"{p.stat().st_size/1024:6.1f} KB")
    if "mascot_avatar" in want:
        av = _square_avatar(trimmed, 1024)
        p = ASSETS / "mascot_avatar.png"
        av.save(p, "PNG", optimize=True)
        print(f"[mascot] {p.name:22s} {av.size[0]}x{av.size[1]} RGBA "
              f"{p.stat().st_size/1024:6.1f} KB")


# --------------------------------------------------------------------------
# contact sheet：9 背景 + 图标网格 + 吉祥物，一张图检查整体调性
# --------------------------------------------------------------------------
def build_contact_sheet():
    f_cn = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 34)
    f_sm = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 19)
    f_name = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
    Wd = 2400
    margin, gap = 44, 26
    bg_w = (Wd - 2 * margin - 2 * gap) // 3
    bg_h = int(round(bg_w * H / W))
    icon_cols = 10
    icon_cell = (Wd - 2 * margin - (icon_cols - 1) * gap) // icon_cols
    mascot_h = 430

    rows = (len(BACKGROUNDS) + 2) // 3
    y_head = 60
    y_bg = y_head + 96
    bg_block = rows * (bg_h + 34 + gap)
    y_icon = y_bg + bg_block + 104
    icon_block = 2 * (icon_cell + 34 + gap)
    y_mas = y_icon + icon_block + 100
    sheet_h = y_mas + mascot_h + 80

    sheet = Image.new("RGB", (Wd, sheet_h), (16, 17, 20))
    d = ImageDraw.Draw(sheet)
    d.text((margin, 34), "WisPath CampusMate  ·  deck visual assets", font=f_cn,
           fill=(232, 236, 244))
    d.text((margin, y_head + 34),
           "9 backgrounds 2560x1440  ·  20 icons 512x512 white stroke 26px  ·  mascot cut-out",
           font=f_sm, fill=(120, 128, 142))

    for i, name in enumerate(BACKGROUNDS):
        r_, c_ = divmod(i, 3)
        x = margin + c_ * (bg_w + gap)
        y = y_bg + r_ * (bg_h + 34 + gap)
        im = Image.open(ASSETS / (name + ".jpg")).convert("RGB")
        sheet.paste(im.resize((bg_w, bg_h), Image.LANCZOS), (x, y))
        d.text((x + 2, y + bg_h + 7), name, font=f_name, fill=(148, 156, 170))

    d.text((margin, y_icon - 56), "icons  (512x512, alpha)", font=f_sm,
           fill=(120, 128, 142))
    for i, name in enumerate(ICON_NAMES):
        r_, c_ = divmod(i, icon_cols)
        x = margin + c_ * (icon_cell + gap)
        y = y_icon + r_ * (icon_cell + 34 + gap)
        cell = Image.new("RGB", (icon_cell, icon_cell), (24, 26, 31))
        ic = Image.open(ASSETS / ("icon_%s.png" % name)).convert("RGBA")
        s = int(icon_cell * 0.82)
        ic = ic.resize((s, s), Image.LANCZOS)
        cell.paste(ic, ((icon_cell - s) // 2, (icon_cell - s) // 2), ic)
        sheet.paste(cell, (x, y))
        d.text((x + 2, y + icon_cell + 6), name, font=f_sm, fill=(148, 156, 170))

    d.text((margin, y_mas - 56), "mascot  (mascot_cut.png / mascot_avatar.png)",
           font=f_sm, fill=(120, 128, 142))
    for k, fname in enumerate(("mascot_cut.png", "mascot_avatar.png")):
        mp = ASSETS / fname
        if not mp.exists():
            continue
        im = Image.open(mp).convert("RGBA")
        s = mascot_h / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        x = margin + k * 560
        card = Image.new("RGB", (int(mascot_h * 1.35), mascot_h), (26, 28, 33))
        card.paste(im, ((card.width - im.width) // 2, (card.height - im.height) // 2), im)
        sheet.paste(card, (x, y_mas))
        d.text((x, y_mas + mascot_h + 6), fname, font=f_sm, fill=(148, 156, 170))
        d.text((x + card.width + 30, y_mas + 16), "white bg removed, 6% trim",
               font=f_sm, fill=(110, 118, 132))

    p = ASSETS / "contact_sheet.jpg"
    sheet.save(p, "JPEG", quality=92, subsampling=2, optimize=True, progressive=True)
    print(f"[sheet] {p.name} {sheet.size[0]}x{sheet.size[1]} {p.stat().st_size/1024:.0f} KB")
    return p


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def _lum(arr):
    a = arr.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def self_check():
    print("\n=== self check ===")
    ok_all = True
    total = 0
    print("\n-- backgrounds (2560x1440, JPEG, <900KB) --")
    print(f"{'file':22s} {'size':>11s} {'mode':>5s} {'KB':>7s} {'mean':>5s} {'std':>5s} "
          f"{'text zone mean/p99':>20s}")
    for name, spec in BACKGROUNDS.items():
        p = ASSETS / (name + ".jpg")
        im = Image.open(p)
        L = _lum(np.array(im.convert("RGB")))
        kb = p.stat().st_size / 1024
        ts = spec["text_safe"]
        x0, y0, x1, y1 = [int(v * s) for v, s in zip(ts, (W, H, W, H))]
        z = L[y0:y1, x0:x1]
        ok = (im.size == (W, H)) and im.mode == "RGB" and kb < 900 and 3 <= L.mean() <= 30 and L.std() > 2
        ok_all &= ok
        total += p.stat().st_size
        print(f"{p.name:22s} {im.size[0]}x{im.size[1]:<4d} {im.mode:>5s} {kb:7.1f} "
              f"{L.mean():5.1f} {L.std():5.1f} {z.mean():9.1f}/{np.percentile(z, 99):<4.0f} "
              f"{'PASS' if ok else 'FAIL'}")
    print("\n-- icons (512x512, RGBA, alpha coverage 5%~35%) --")
    covs = []
    for name in ICON_NAMES:
        p = ASSETS / ("icon_%s.png" % name)
        im = Image.open(p)
        alpha = np.array(im)[..., 3]
        cov = alpha.mean() / 255.0
        covs.append(cov)
        ok = im.size == (ICON, ICON) and im.mode == "RGBA" and 0.05 <= cov <= 0.35
        ok_all &= ok
        total += p.stat().st_size
        print(f"{p.name:22s} {im.size[0]}x{im.size[1]} {im.mode:>4s} "
              f"cov={cov*100:5.1f}% {p.stat().st_size/1024:5.1f} KB {'PASS' if ok else 'FAIL'}")
    print(f"  alpha coverage: min {min(covs)*100:.1f}%  max {max(covs)*100:.1f}%")

    print("\n-- mascot (RGBA, transparent bg) --")
    for fname, long_expect in (("mascot_cut.png", 900), ("mascot_avatar.png", 1024)):
        p = ASSETS / fname
        im = Image.open(p)
        arr = np.array(im)
        alpha = arr[..., 3]
        transparent = alpha.min() == 0
        bbox = im.getbbox()
        size_ok = max(im.size) == long_expect
        ok = transparent and im.mode == "RGBA" and size_ok
        ok_all &= ok
        total += p.stat().st_size
        print(f"{p.name:22s} {im.size[0]}x{im.size[1]} {im.mode:>4s} "
              f"bbox={bbox} transparent_corner={transparent} "
              f"{p.stat().st_size/1024:6.1f} KB {'PASS' if ok else 'FAIL'}")

    cs = ASSETS / "contact_sheet.jpg"
    if cs.exists():
        im = Image.open(cs)
        total += cs.stat().st_size
        print(f"\n[png/jpg total] {total/1024/1024:.2f} MB   contact_sheet: "
              f"{im.size[0]}x{im.size[1]} {cs.stat().st_size/1024:.0f} KB")
    print(f"\nRESULT: {'ALL PASS' if ok_all else 'SOME CHECKS FAILED'}")
    return ok_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔的产物名，如 bg_00_hero,icon_chat,mascot_cut")
    ap.add_argument("--stage", default="all",
                    choices=["all", "bg", "icon", "mascot", "sheet", "check"])
    args = ap.parse_args()
    only = set(x.strip() for x in args.only.split(",") if x.strip()) or None

    if args.stage in ("all", "bg"):
        build_backgrounds(only)
    if args.stage in ("all", "icon"):
        build_icons(only)
    if args.stage in ("all", "mascot"):
        build_mascot(only)
    if args.stage in ("all", "sheet"):
        build_contact_sheet()
    if args.stage in ("all", "check"):
        self_check()


if __name__ == "__main__":
    main()
