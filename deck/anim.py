# -*- coding: utf-8 -*-
"""deck/anim.py --- PPTX 原生动画时间轴 / 切换引擎（不依赖 python-pptx 动画能力）。

python-pptx(1.0.2) 完全不支持动画，本模块直接生成 ECMA-376 的 <p:timing> 与
<p:transition> OOXML，写回 slide XML，使 PowerPoint / WPS 打开后**真正会播放**。

设计目标
--------
1. 结构正确性优先：所有 XML 结构均以 **PowerPoint 16 实际写出的 XML 为蓝本**
   （用 COM 生成参考文件 -> 解压 -> 逐节点比对），不是臆造。
2. 全部效果**自动播放**（等价于"上一动画之后 / 与上一动画同时"），不需要点击；
   配合 advTm 自动换片，整份 deck 可无人值守连续播放。
3. API 极简::

       tl = Timeline()
       tl.add(shape, "fadeUp", start=0.3, dur=0.7)
       tl.transition(slide, "fade", advance=12)
       tl.apply(slide)

OOXML 结构（与 PowerPoint 写出的完全一致）
------------------------------------------
::

    p:timing
      p:tnLst / p:par / p:cTn[id=1 nodeType=tmRoot dur=indefinite restart=never]
        p:childTnLst / p:seq[concurrent=1 nextAc=seek]
          p:cTn[id=2 nodeType=mainSeq dur=indefinite]
            p:childTnLst / p:par / p:cTn[id=3 fill=hold]
              p:stCondLst: p:cond delay=indefinite + p:cond evt=onBegin -> p:tn val=2
              p:childTnLst
                p:par / p:cTn[group, fill=hold, cond delay=<绝对起点ms>]   # 每个"时间点"一组
                  p:childTnLst
                    p:par / p:cTn[presetID presetClass presetSubtype grpId=0
                                  nodeType=afterEffect|withEffect]      # 单个效果
                      p:childTnLst -> set / animEffect / anim / animScale / animMotion
          p:prevCondLst  (onPrev -> sldTgt)
          p:nextCondLst  (onNext -> sldTgt)
      p:bldLst / p:bldP[spid grpId=0 animBg=1 | build=allAtOnce]

关键点（都是实测踩出来的）：

* 组 par 的 delay 是**相对 slide 开始的绝对毫秒数**；同一起点(毫秒)的效果共用一个组。
* 组内第一个效果 nodeType="afterEffect"，其余 nodeType="withEffect"；
  COM 读回 TriggerType 分别为 3 / 2，**不会是 1(OnPageClick)** --- 这就是"自动播放"的判据。
* 位移使用 p:anim + p:tavLst，坐标值支持 #ppt_y+0.12 这类**相对表达式**。
* 逐段文字动画靠 p:spTgt/p:txEl/p:pRg[st,end] 定位段落；bldLst 用 build="allAtOnce"。
* <p:fade/> 不带 thruBlk = 平滑交叉淡化；thruBlk="1" 会**闪黑**，所以不用。

作者：animator（WisPath CampusMate V2 宣传片）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from lxml import etree

from pptx.oxml.ns import nsdecls

__all__ = [
    "Timeline",
    "Effect",
    "TransitionSpec",
    "PRESETS",
    "MAX_EFFECTS_PER_SLIDE",
    "enable_show_timings",
]

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
NS_P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"

#: 单页效果数软上限。PowerPoint 打开速度与该值强相关，超过只警告不阻拦。
MAX_EFFECTS_PER_SLIDE = 14

# ---------------------------------------------------------------------------
# 预设表
# ---------------------------------------------------------------------------
# 每一项：
#   preset_id / preset_class / preset_subtype -> 写入 cTn 的三个预设属性
#   kind   -> 行为生成器家族
#   native -> 是否与 PowerPoint 原生预设的行为集合完全一致
#
# presetID 取值来源：用 PowerPoint COM 遍历 AddEffect(effectId=1..120) 后解析它写出的
# XML 得到的权威映射（见 deck/.animtest/_ref/enum-report.txt）。
PRESETS: Dict[str, Dict[str, Any]] = {
    # ---- 淡入类 ----
    "fade":       dict(preset_id=10, preset_class="entr", preset_subtype=0,  kind="fade",      native=True),
    "fadeUp":     dict(preset_id=37, preset_class="entr", preset_subtype=0,  kind="fade_move", native=True,  axis="y", sign=+1),
    "fadeDown":   dict(preset_id=37, preset_class="entr", preset_subtype=0,  kind="fade_move", native=False, axis="y", sign=-1),
    "fadeLeft":   dict(preset_id=37, preset_class="entr", preset_subtype=0,  kind="fade_move", native=False, axis="x", sign=+1),
    "fadeRight":  dict(preset_id=37, preset_class="entr", preset_subtype=0,  kind="fade_move", native=False, axis="x", sign=-1),
    # ---- 缩放 ----
    "zoom":       dict(preset_id=23, preset_class="entr", preset_subtype=16, kind="zoom",      native=False),
    # ---- 擦除（Wipe，filter 决定方向）----
    "wipeUp":     dict(preset_id=22, preset_class="entr", preset_subtype=4,  kind="wipe", native=True,  filter="wipe(up)"),
    "wipeDown":   dict(preset_id=22, preset_class="entr", preset_subtype=4,  kind="wipe", native=True,  filter="wipe(down)"),
    "wipeLeft":   dict(preset_id=22, preset_class="entr", preset_subtype=2,  kind="wipe", native=False, filter="wipe(left)"),
    "wipeRight":  dict(preset_id=22, preset_class="entr", preset_subtype=8,  kind="wipe", native=False, filter="wipe(right)"),
    # ---- 其它入场 ----
    "appear":     dict(preset_id=1,  preset_class="entr", preset_subtype=0,  kind="appear",    native=True),
    # ---- 强调 ----
    "pulse":      dict(preset_id=6,  preset_class="emph", preset_subtype=0,  kind="pulse",     native=True),
    "grow":       dict(preset_id=6,  preset_class="emph", preset_subtype=0,  kind="grow",      native=True),
    # ---- 路径 / 循环 ----
    "float":      dict(preset_id=35, preset_class="path", preset_subtype=0,  kind="float",     native=False),
}

#: 别名 --- 让调用方少踩命名坑
_ALIASES = {
    "fadein": "fade", "fade_in": "fade",
    "fadeup": "fadeUp", "fade_up": "fadeUp", "riseup": "fadeUp", "rise_up": "fadeUp",
    "fadedown": "fadeDown", "fade_down": "fadeDown",
    "fadeleft": "fadeLeft", "fade_left": "fadeLeft",
    "faderight": "fadeRight", "fade_right": "fadeRight",
    "zoom_in": "zoom", "zoomin": "zoom",
    "wipeup": "wipeUp", "wipe_up": "wipeUp",
    "wipedown": "wipeDown", "wipe_down": "wipeDown",
    "wipeleft": "wipeLeft", "wipe_left": "wipeLeft",
    "wiperight": "wipeRight", "wipe_right": "wipeRight",
    "pulsate": "pulse", "beat": "pulse",
    "breathe": "float", "drift": "float",
}


def _norm_preset(name: str) -> str:
    if name in PRESETS:
        return name
    key = str(name).strip()
    if key in PRESETS:
        return key
    low = key.lower().replace("-", "_").replace(" ", "_")
    if low in _ALIASES:
        return _ALIASES[low]
    cand = "".join(ch for ch in low if ch.isalnum())
    for p in PRESETS:
        if p.lower() == cand:
            return p
    if cand in _ALIASES:
        return _ALIASES[cand]
    raise KeyError("未知动画预设 %r；可用：%s" % (name, ", ".join(sorted(PRESETS))))


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
class _Ids:
    """全局唯一 cTn id 分配器（PowerPoint 要求正整数且整棵树内唯一）。"""

    __slots__ = ("_n",)

    def __init__(self, start: int = 1) -> None:
        self._n = start

    def next(self) -> int:
        v = self._n
        self._n += 1
        return v


def _ms(seconds: float) -> int:
    """秒 -> 毫秒（时长用，至少 1ms）。"""
    return max(1, int(round(float(seconds) * 1000.0)))


def _ms_delay(seconds: float) -> int:
    """秒 -> 毫秒（起始延迟用，允许 0）。"""
    return max(0, int(round(float(seconds) * 1000.0)))


def _tgt(spid: int, para: Optional[Tuple[int, int]] = None) -> str:
    """构造 p:tgtEl 内部：整形状 or 指定段落区间。"""
    if para is None:
        return '<p:spTgt spid="%d"/>' % spid
    st, end = int(para[0]), int(para[1])
    return ('<p:spTgt spid="%d"><p:txEl><p:pRg st="%d" end="%d"/></p:txEl></p:spTgt>'
            % (spid, st, end))


# ---------------------------------------------------------------------------
# 行为(behavior)生成器 --- 每个函数返回一段 XML 字符串
# ---------------------------------------------------------------------------
def _b_set_visible(spid: int, para, ids: "_Ids") -> str:
    return ('<p:set><p:cBhvr>'
            '<p:cTn id="%d" dur="1" fill="hold">'
            '<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            '<p:tgtEl>%s</p:tgtEl>'
            '<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
            '</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
            % (ids.next(), _tgt(spid, para)))


def _anim_effect(spid: int, para, ids: "_Ids", dur_ms: int, filt: str) -> str:
    tid = ids.next()
    return ('<p:animEffect transition="in" filter="%s"><p:cBhvr>'
            '<p:cTn id="%d" dur="%d"/>'
            '<p:tgtEl>%s</p:tgtEl>'
            '</p:cBhvr></p:animEffect>'
            % (filt, tid, dur_ms, _tgt(spid, para)))


def _anim_axis(spid: int, para, ids: "_Ids", dur_ms: int, axis: str,
               frm: str, to: str, decel: Optional[int] = None) -> str:
    tid = ids.next()
    eas = (' decel="%d"' % decel) if decel else ""
    return ('<p:anim calcmode="lin" valueType="num"><p:cBhvr>'
            '<p:cTn id="%d" dur="%d"%s fill="hold"/>'
            '<p:tgtEl>%s</p:tgtEl>'
            '<p:attrNameLst><p:attrName>%s</p:attrName></p:attrNameLst>'
            '</p:cBhvr>'
            '<p:tavLst>'
            '<p:tav tm="0"><p:val><p:strVal val="%s"/></p:val></p:tav>'
            '<p:tav tm="100000"><p:val><p:strVal val="%s"/></p:val></p:tav>'
            '</p:tavLst></p:anim>'
            % (tid, dur_ms, eas, _tgt(spid, para), axis, frm, to))


def _anim_scale(spid: int, para, ids: "_Ids", dur_ms: int,
                by: Optional[Tuple[int, int]] = None,
                frm: Optional[Tuple[int, int]] = None,
                to: Optional[Tuple[int, int]] = None) -> str:
    """缩放行为。注意：autoRev / repeatCount 不能写在这里 --- 必须写在外层效果 cTn，
    否则 PowerPoint 会把 Duration 算成接近 0（实测踩坑）。"""
    tid = ids.next()
    attrs = ' id="%d" dur="%d"' % (tid, dur_ms)
    attrs += ' fill="hold"'
    inner = ""
    if by is not None:
        inner += '<p:by x="%d" y="%d"/>' % (int(by[0]), int(by[1]))
    if frm is not None:
        inner += '<p:from x="%d" y="%d"/>' % (int(frm[0]), int(frm[1]))
    if to is not None:
        inner += '<p:to x="%d" y="%d"/>' % (int(to[0]), int(to[1]))
    return ('<p:animScale><p:cBhvr>'
            '<p:cTn%s/>'
            '<p:tgtEl>%s</p:tgtEl>'
            '</p:cBhvr>%s</p:animScale>'
            % (attrs, _tgt(spid, para), inner))


def _anim_motion(spid: int, para, ids: "_Ids", dur_ms: int,
                 path: str) -> str:
    """路径行为。repeatCount 同样只能写在外层效果 cTn。"""
    tid = ids.next()
    rep = ""
    return ('<p:animMotion origin="layout" path="%s" pathEditMode="relative" ptsTypes="">'
            '<p:cBhvr>'
            '<p:cTn id="%d" dur="%d"%s fill="hold"/>'
            '<p:tgtEl>%s</p:tgtEl>'
            '<p:attrNameLst><p:attrName>ppt_x</p:attrName>'
            '<p:attrName>ppt_y</p:attrName></p:attrNameLst>'
            '</p:cBhvr></p:animMotion>'
            % (path, tid, dur_ms, rep, _tgt(spid, para)))


#: fade_move 家族默认位移量（相对于形状自身尺寸），越小越"苹果风"
_FADE_MOVE_DELTA = 0.10
#: 落地缓动，越大越"高级"
_FADE_MOVE_DECEL = 60000


def _repeat_attrs(repeat: Optional[int]) -> str:
    """重复次数 -> 外层 cTn 属性。

    实测结论（见 _ref/_emph2-dump.txt）：PowerPoint 的 RepeatCount 以千分之一为单位，
    Repeat=2 写成 repeatCount="2000"；Repeat=1 时该属性省略。
    """
    if not repeat or int(repeat) <= 1:
        return ""
    return ' repeatCount="%d"' % (int(repeat) * 1000)


def _behaviors(preset: str, spid: int, para, ids: "_Ids",
               dur_ms: int, repeat: Optional[int]) -> Tuple[str, str]:
    """按预设生成效果的所有子行为（顺序与 PowerPoint 一致，不能乱）。

    返回 (行为 XML, 外层效果 cTn 的附加属性)。

    强调/路径类的 autoRev 与 repeatCount 必须挂在最外层效果 cTn 上；
    写在内层行为 cTn 上会让 PowerPoint 的 Duration 退化成接近 0。
    """
    p = PRESETS[preset]
    kind = p["kind"]

    if kind == "appear":
        return _b_set_visible(spid, para, ids), ""

    if kind == "fade":
        return (_b_set_visible(spid, para, ids)
                + _anim_effect(spid, para, ids, dur_ms, "fade")), ""

    if kind == "fade_move":
        axis = p["axis"]
        sign = p["sign"]
        d = _FADE_MOVE_DELTA
        anchor = "#ppt_" + axis
        frm = "%s%s%g" % (anchor, "+" if sign > 0 else "-", d)
        return (_b_set_visible(spid, para, ids)
                + _anim_effect(spid, para, ids, dur_ms, "fade")
                + _anim_axis(spid, para, ids, dur_ms, "ppt_" + axis, frm, anchor,
                             _FADE_MOVE_DECEL)), ""

    if kind == "zoom":
        # 缩放淡入：fade + animScale 0.86 -> 1.0（比 PowerPoint 原生 zoom(0->1) 更克制）
        return (_b_set_visible(spid, para, ids)
                + _anim_effect(spid, para, ids, dur_ms, "fade")
                + _anim_scale(spid, para, ids, dur_ms,
                              frm=(86000, 86000), to=(100000, 100000))), ""

    if kind == "wipe":
        return (_b_set_visible(spid, para, ids)
                + _anim_effect(spid, para, ids, dur_ms, p["filter"])), ""

    if kind == "pulse":
        rep = 2 if repeat is None else repeat
        return (_anim_scale(spid, para, ids, dur_ms, by=(104000, 104000)),
                ' autoRev="1"' + _repeat_attrs(rep))

    if kind == "grow":
        rep = 1 if repeat is None else repeat
        return (_anim_scale(spid, para, ids, dur_ms, by=(130000, 130000)),
                ' autoRev="1"' + _repeat_attrs(rep))

    if kind == "float":
        rep = 2 if repeat is None else repeat
        # 路径类：PowerPoint 原生还带 accel/decel=50000，照抄它的写法
        return (_anim_motion(spid, para, ids, dur_ms, "M 0 0 L 0 -0.025 L 0 0"),
                ' accel="50000" decel="50000"' + _repeat_attrs(rep))

    raise AssertionError("未实现的行为家族: %r" % (kind,))

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Effect:
    """一条动画效果（= PowerPoint 动画窗格里的一项）。"""

    preset: str
    spid: int
    start: float
    dur: float
    node_type: str = "afterEffect"
    para: Optional[Tuple[int, int]] = None
    repeat: Optional[int] = None
    slide_part: Any = None
    order: int = 0

    @property
    def start_ms(self) -> int:
        return _ms_delay(self.start)

    @property
    def total_dur(self) -> float:
        """本效果实际占用时长（考虑 repeat，供自动换片时长核算）。"""
        reps = 1
        if self.repeat and int(self.repeat) > 1:
            reps = int(self.repeat)
        return self.dur * reps

    @property
    def end(self) -> float:
        return self.start + self.total_dur

    def __repr__(self) -> str:  # pragma: no cover
        tgt = "%d" % self.spid if self.para is None else "%d[%d:%d]" % (
            self.spid, self.para[0], self.para[1])
        return "<Effect %s spid=%s start=%.2f dur=%.2f>" % (
            self.preset, tgt, self.start, self.dur)


@dataclass
class TransitionSpec:
    """切页效果。"""

    kind: str = "fade"
    dur: float = 1.0
    advance: Optional[float] = None   # 秒；None = 不自动换片
    click: bool = True


_SPD_BUCKETS = ((0.35, "fast"), (0.9, "med"), (99.0, "slow"))


def _spd_of(dur: float) -> str:
    """把秒映射到 ECMA 的 spd 三档（ECMA 只定义 fast/med/slow，无自定义时长）。"""
    d = float(dur)
    for limit, name in _SPD_BUCKETS:
        if d <= limit:
            return name
    return "slow"


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------
class Timeline:
    """单页（或多页）动画时间轴。用法见模块 docstring。

    典型用法::

        tl = Timeline()
        tl.add(shape_a, "fadeUp", start=0.2, dur=0.6)
        tl.add(shape_b, "fade",   start=0.2, dur=0.6)   # 同一时刻 -> 与上一动画同时
        tl.add(shape_c, "pulse",  start=1.0, dur=0.6)
        tl.transition(slide, "fade", advance=12)
        tl.apply(slide)
    """

    def __init__(self, *, warn_limit: bool = True) -> None:
        self._effects: List[Effect] = []
        self._transitions: Dict[Any, TransitionSpec] = {}
        self._default_transition: Optional[TransitionSpec] = None
        self._order = 0
        self.warn_limit = warn_limit
        self.warnings: List[str] = []

    # -- 查询 ---------------------------------------------------------------
    @property
    def effects(self) -> List[Effect]:
        return list(self._effects)

    def __len__(self) -> int:
        return len(self._effects)

    def total_duration(self) -> float:
        """返回时间轴上所有效果的结束时间（秒）。"""
        return max((e.end for e in self._effects), default=0.0)

    # -- 添加效果 -----------------------------------------------------------
    def add(self, target: Any, preset: str = "fade", start: float = 0.0,
            dur: float = 0.7, *, repeat: Optional[int] = None, slide: Any = None,
            para: Optional[Tuple[int, int]] = None,
            node_type: Optional[str] = None) -> Effect:
        """添加一条效果。

        参数
        ----
        target : pptx shape 对象 或 int(shape_id)。传 int 时必须给 slide=。
        preset : PRESETS 里的名字（大小写/下划线不敏感）。
        start  : 相对本页开始的**绝对秒数**。
        dur    : 持续秒数。
        repeat : 重复次数（pulse/float 有默认值）。
        para   : (起始段, 结束段)，用于文字逐段；一般请用 add_text_build。
        """
        preset = _norm_preset(preset)
        spid, part = self._resolve(target, slide)
        self._order += 1
        eff = Effect(preset=preset, spid=spid, start=max(0.0, float(start)),
                     dur=max(0.01, float(dur)), node_type=node_type or "afterEffect",
                     para=para, repeat=repeat, slide_part=part, order=self._order)
        self._effects.append(eff)
        return eff

    def add_many(self, targets: Sequence[Any], preset: str = "fadeUp",
                 start: float = 0.0, dur: float = 0.6, *, stagger: float = 0.08,
                 slide: Any = None, **kw: Any) -> List[Effect]:
        """对一组 shape 按固定步长依次入场（最常用的卡片/图标编排）。"""
        out: List[Effect] = []
        for i, t in enumerate(targets):
            out.append(self.add(t, preset, start=start + i * stagger, dur=dur,
                                slide=slide, **kw))
        return out

    def add_text_build(self, target: Any, preset: str = "fadeUp",
                       start: float = 0.0, dur: float = 0.5, *,
                       stagger: float = 0.06,
                       paragraphs: Optional[Sequence[int]] = None,
                       slide: Any = None) -> List[Effect]:
        """逐段文字动画。

        实现方式：每个段落一条效果，p:spTgt/p:txEl/p:pRg[st,end] 精确指向段落，
        bldLst 里对该 shape 记 build="allAtOnce"（与 PowerPoint 自己写的一致）。

        注意：不做"逐字(by word)"--- 那需要 p:iterate，实测在部分 WPS 版本上
        会导致整段文字直接出现，因此本模块只做逐段。
        """
        shape, part = self._as_shape(target)
        n = len(shape.text_frame.paragraphs)
        idxs = list(range(n)) if paragraphs is None else [int(i) for i in paragraphs]
        if slide is not None:
            part = self._part_of_slide(slide)
        out: List[Effect] = []
        for k, i in enumerate(idxs):
            self._order += 1
            eff = Effect(preset=_norm_preset(preset), spid=int(shape.shape_id),
                         start=max(0.0, float(start) + k * stagger),
                         dur=max(0.01, float(dur)), node_type="afterEffect",
                         para=(i, i),
                         slide_part=part if part is not None else self._part_of(shape),
                         order=self._order)
            self._effects.append(eff)
            out.append(eff)
        return out

    # -- 切换 ---------------------------------------------------------------
    def transition(self, slide: Any = None, kind: str = "fade", dur: float = 1.0,
                   advance: Optional[float] = 12.0, *, click: bool = True) -> TransitionSpec:
        """设置切页效果。

        kind    : "fade" | "none" | "morph"
        dur     : 切换时长（秒）。ECMA 只有 fast/med/slow 三档，会就近取整。
        advance : 自动换片秒数；None = 不自动换片。**自动换片是整片自动播放的关键。**
        click   : 是否仍响应鼠标点击换片（默认保留）。
        """
        spec = TransitionSpec(kind=str(kind).lower(), dur=float(dur),
                              advance=advance, click=click)
        if slide is None:
            self._default_transition = spec
        else:
            self._transitions[self._part_of_slide(slide)] = spec
        return spec

    # -- 应用 ---------------------------------------------------------------
    def apply(self, slide: Any) -> int:
        """把本 Timeline 中属于该 slide 的效果 + 切换写进 slide XML。

        返回写入的效果条数（不含切换）。
        """
        part = self._part_of_slide(slide)
        sld = slide._element

        effs = [e for e in self._effects if e.slide_part is None or e.slide_part is part]
        effs.sort(key=lambda e: (e.start_ms, e.order))

        self._drop_existing(sld)

        if effs:
            timing = self._build_timing(effs)
            self._insert_sld_child(sld, timing, "p:timing")

        spec = self._transitions.get(part) or self._default_transition
        if spec is not None:
            tr = self._build_transition(spec)
            if tr is not None:
                is_mc = etree.QName(tr).namespace == NS_MC
                self._insert_sld_child(sld, tr, "mc:AlternateContent" if is_mc else "p:transition")

        if self.warn_limit and len(effs) > MAX_EFFECTS_PER_SLIDE:
            self.warnings.append(
                "slide 上有 %d 个效果，超过建议上限 %d，PowerPoint 打开会变慢"
                % (len(effs), MAX_EFFECTS_PER_SLIDE))
        return len(effs)

    def apply_all(self, slides: Iterable[Any]) -> Dict[int, int]:
        """对多个 slide 依次 apply，返回 {slide_index: 效果数}。"""
        out: Dict[int, int] = {}
        for i, s in enumerate(slides):
            out[i] = self.apply(s)
        return out

    def describe(self) -> List[Dict[str, Any]]:
        """导出自检信息（anim_test.py / COM 对账用）。"""
        rows = []
        for e in sorted(self._effects, key=lambda x: (x.start_ms, x.order)):
            rows.append({"preset": e.preset, "spid": e.spid,
                         "para": list(e.para) if e.para else None,
                         "start_ms": e.start_ms, "dur_ms": _ms(e.dur),
                         "node_type": e.node_type})
        return rows

    # -- 内部 ---------------------------------------------------------------
    @staticmethod
    def _part_of_slide(slide: Any) -> Any:
        return getattr(slide, "part", None)

    @staticmethod
    def _part_of(shape: Any) -> Any:
        return getattr(shape, "part", None)

    @staticmethod
    def _as_shape(target: Any) -> Tuple[Any, Any]:
        if isinstance(target, (int, float)):
            raise TypeError("add_text_build 需要传入 shape 对象（要读段落数）")
        if not hasattr(target, "shape_id"):
            raise TypeError("无法识别的 target: %r（应为 pptx shape 或 shape_id）" % (target,))
        return target, getattr(target, "part", None)

    def _resolve(self, target: Any, slide: Any) -> Tuple[int, Any]:
        if isinstance(target, (int, float)) or (isinstance(target, str) and target.isdigit()):
            spid = int(target)
            return spid, (self._part_of_slide(slide) if slide is not None else None)
        if not hasattr(target, "shape_id"):
            raise TypeError("无法识别的 target: %r（应为 pptx shape 对象或 int shape_id）" % (target,))
        part = getattr(target, "part", None)
        if slide is not None:
            part = self._part_of_slide(slide)
        return int(target.shape_id), part

    @staticmethod
    def _drop_existing(sld: Any) -> None:
        for el in list(sld):
            q = etree.QName(el)
            if q.namespace == NS_P and q.localname in ("transition", "timing"):
                sld.remove(el)
            elif q.namespace == NS_MC and q.localname == "AlternateContent":
                if el.find(".//{%s}transition" % NS_P) is not None:
                    sld.remove(el)

    @staticmethod
    def _insert_sld_child(sld: Any, el: Any, tag: str) -> None:
        """按 CT_Slide 的元素顺序把 el 插到正确位置。

        CT_Slide: cSld, clrMapOvr, transition, timing, extLst
        （mc:AlternateContent 包裹的 transition 视作 transition 同位）
        """
        order = {"p:cSld": 0, "p:clrMapOvr": 1, "mc:AlternateContent": 2,
                 "p:transition": 2, "p:timing": 3, "p:extLst": 4}
        mine = order.get(tag, 99)
        idx = 0
        for i, child in enumerate(sld):
            q = etree.QName(child)
            key = None
            if q.namespace == NS_P:
                key = "p:" + q.localname
            elif q.namespace == NS_MC:
                key = "mc:" + q.localname
            theirs = order.get(key, 99)
            if theirs > mine:
                idx = i
                break
            idx = i + 1
        sld.insert(idx, el)

    # -- XML 构造 -----------------------------------------------------------
    @staticmethod
    def _build_timing(effs: List[Effect]) -> Any:
        ids = _Ids(1)
        root_id = ids.next()
        seq_id = ids.next()
        pad_id = ids.next()

        groups: List[Tuple[int, List[Effect]]] = []
        for eff in effs:
            key = eff.start_ms
            if groups and groups[-1][0] == key:
                groups[-1][1].append(eff)
            else:
                groups.append((key, [eff]))

        grp_ids = _assign_grpids(effs)

        group_xml: List[str] = []
        cursor = 0
        for start_ms, members in groups:
            g_id = ids.next()
            eff_xml: List[str] = []
            for i, eff in enumerate(members):
                node_type = "afterEffect" if i == 0 else "withEffect"
                eff.node_type = node_type
                spec = PRESETS[eff.preset]
                e_id = ids.next()
                beh, outer = _behaviors(eff.preset, eff.spid, eff.para, ids,
                                        _ms(eff.dur), eff.repeat)
                eff_xml.append(
                    '<p:par><p:cTn id="%d" presetID="%s" presetClass="%s" '
                    'presetSubtype="%s"%s fill="hold" grpId="%d" nodeType="%s">'
                    '<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                    '<p:childTnLst>%s</p:childTnLst>'
                    '</p:cTn></p:par>'
                    % (e_id, spec["preset_id"], spec["preset_class"],
                       spec["preset_subtype"], outer,
                       grp_ids[cursor + i], node_type, beh))
            cursor += len(members)
            group_xml.append(
                '<p:par><p:cTn id="%d" fill="hold">'
                '<p:stCondLst><p:cond delay="%d"/></p:stCondLst>'
                '<p:childTnLst>%s</p:childTnLst>'
                '</p:cTn></p:par>' % (g_id, start_ms, "".join(eff_xml)))

        bld_xml = _build_bldlst(effs, grp_ids)

        xml = ('<p:timing %s>'
               '<p:tnLst>'
               '<p:par><p:cTn id="%d" dur="indefinite" restart="never" nodeType="tmRoot">'
               '<p:childTnLst>'
               '<p:seq concurrent="1" nextAc="seek">'
               '<p:cTn id="%d" dur="indefinite" nodeType="mainSeq">'
               '<p:childTnLst>'
               '<p:par><p:cTn id="%d" fill="hold">'
               '<p:stCondLst>'
               '<p:cond delay="indefinite"/>'
               '<p:cond evt="onBegin" delay="0"><p:tn val="%d"/></p:cond>'
               '</p:stCondLst>'
               '<p:childTnLst>%s</p:childTnLst>'
               '</p:cTn></p:par>'
               '</p:childTnLst>'
               '</p:cTn>'
               '<p:prevCondLst>'
               '<p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
               '</p:prevCondLst>'
               '<p:nextCondLst>'
               '<p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
               '</p:nextCondLst>'
               '</p:seq>'
               '</p:childTnLst>'
               '</p:cTn></p:par>'
               '</p:tnLst>'
               '%s'
               '</p:timing>') % (nsdecls("p", "a"), root_id, seq_id, pad_id,
                                 seq_id, "".join(group_xml), bld_xml)
        return etree.fromstring(xml.encode("utf-8"))

    @staticmethod
    def _build_transition(spec: TransitionSpec) -> Any:
        kind = (spec.kind or "none").lower()
        if kind in ("none", "off", "cut"):
            return None

        attrs = 'spd="%s"' % _spd_of(spec.dur)
        if spec.advance is not None:
            attrs += ' advTm="%d"' % int(round(float(spec.advance) * 1000.0))
        if not spec.click:
            attrs += ' advClick="0"'

        if kind == "fade":
            # 注意：<p:fade/> 不带 thruBlk => 平滑交叉淡化；thruBlk="1" 会闪黑
            xml = '<p:transition %s %s><p:fade/></p:transition>' % (nsdecls("p", "a"), attrs)
            return etree.fromstring(xml.encode("utf-8"))

        if kind == "morph":
            xml = ('<mc:AlternateContent xmlns:mc="%s" xmlns:p="%s" xmlns:p14="%s">'
                   '<mc:Choice Requires="p14">'
                   '<p:transition %s p14:dur="%d">'
                   '<p14:morph option="2"/>'
                   '</p:transition>'
                   '</mc:Choice>'
                   '<mc:Fallback>'
                   '<p:transition %s><p:fade/></p:transition>'
                   '</mc:Fallback>'
                   '</mc:AlternateContent>') % (
                       NS_MC, NS_P, NS_P14, attrs,
                       int(round(float(spec.dur) * 1000.0)), attrs)
            return etree.fromstring(xml.encode("utf-8"))

        raise ValueError("未知切换 kind=%r（支持 fade / none / morph）" % (spec.kind,))


def _assign_grpids(effs: List[Effect]) -> List[int]:
    """给每个效果分配 grpId（PowerPoint 的"构建组"编号）。

    PowerPoint 的规则（用 COM 实测得到，见 _ref/_multi-pp.pptx）：

    * grpId **按 shape 各自从 0 开始递增**：同一 shape 的第 1、2、3 个整形状动画
      分别是 grpId 0、1、2；换一个 shape 又从 0 开始。
    * 同一 shape 上多个整形状动画若共用同一个 grpId，PowerPoint 会把后来的
      **当成重复项静默丢弃**（这是本模块最初踩的坑）。
    * 逐段文字动画（带 p:txEl/p:pRg）全部共用该 shape 的 grpId 0，
      靠 pRg 的段落区间区分；bldLst 记 build="allAtOnce"。
    * 若某 shape 同时有整形状动画和逐段动画，整形状动画从 grpId 1 起，
      把 0 留给逐段构建。
    """
    para_shapes = {e.spid for e in effs if e.para is not None}
    counters: Dict[int, int] = {}
    out: List[int] = []
    for e in effs:
        if e.para is not None:
            out.append(0)
            continue
        start = 1 if e.spid in para_shapes else 0
        g = counters.get(e.spid, start)
        out.append(g)
        counters[e.spid] = g + 1
    return out


def _build_bldlst(effs: List[Effect], grp_ids: Sequence[int]) -> str:
    """构造 p:bldLst：每个 (spid, grpId) 一条 bldP。

    * 整形状动画 -> <p:bldP spid grpId animBg="1"/>
    * 逐段动画   -> <p:bldP spid grpId="0" build="allAtOnce"/>

    顺序：shape 按其首次出现顺序，同一 shape 内按 grpId 升序。
    """
    shape_order: List[int] = []
    entries: Dict[Tuple[int, int], bool] = {}
    for e, g in zip(effs, grp_ids):
        if e.spid not in shape_order:
            shape_order.append(e.spid)
        key = (e.spid, g)
        is_para = e.para is not None
        entries[key] = entries.get(key, False) or is_para

    if not entries:
        return ""
    parts = ["<p:bldLst>"]
    for spid in shape_order:
        for (s, g), is_para in sorted(
            (kv for kv in entries.items() if kv[0][0] == spid),
            key=lambda kv: kv[0][1],
        ):
            if is_para:
                parts.append('<p:bldP spid="%d" grpId="%d" build="allAtOnce"/>' % (s, g))
            else:
                parts.append('<p:bldP spid="%d" grpId="%d" animBg="1"/>' % (s, g))
    parts.append("</p:bldLst>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# 便利函数
# ---------------------------------------------------------------------------
def enable_show_timings(prs: Any) -> bool:
    """让"幻灯片放映 -> 使用计时"处于开启状态（自动换片依赖它）。

    PowerPoint 默认开启，这里做一次显式兜底，失败不抛异常。
    修改 ppt/presProps.xml 里的 <p:showPr useTimings="1"/>。
    """
    try:
        pkg = prs.part.package
        for part in pkg.iter_parts():
            if str(getattr(part, "partname", "")) == "/ppt/presProps.xml":
                root = etree.fromstring(part.blob)
                show_pr = root.find("{%s}showPr" % NS_P)
                if show_pr is None:
                    show_pr = etree.SubElement(root, "{%s}showPr" % NS_P)
                show_pr.set("useTimings", "1")
                part._blob = etree.tostring(root, xml_declaration=True,
                                            encoding="UTF-8", standalone=True)
                return True
    except Exception:
        return False
    return False
