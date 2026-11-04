# -*- coding: utf-8 -*-
"""Apple-style design system helpers for the WisPath CampusMate promo deck.

All geometry in inches, all colours as 6-digit hex strings.
"""
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
from lxml import etree
import copy as _copy

# ---------------------------------------------------------------- palette
INK        = "05060A"
INK_2      = "0B0D14"
WHITE      = "F5F5F7"
WHITE_PURE = "FFFFFF"
GRAY       = "86868B"
GRAY_2     = "A1A1A6"
GRAY_3     = "6E6E73"
LINE       = "2C2C2E"

BLUE       = "0A84FF"
CYAN       = "64D2FF"
PURPLE     = "BF5AF2"
PINK       = "FF375F"
ORANGE     = "FF9F0A"
GREEN      = "30D158"
TEAL       = "40C8E0"
INDIGO     = "5E5CE6"

CN       = "Microsoft YaHei"
CN_LIGHT = "Microsoft YaHei Light"
EN       = "Segoe UI"
EN_LIGHT = "Segoe UI Light"

SLIDE_W = 13.333
SLIDE_H = 7.5

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def E(v):
    """inches -> EMU"""
    return Emu(int(round(v * 914400)))


def rgb(hexstr):
    hexstr = hexstr.lstrip("#")
    return RGBColor.from_string(hexstr.upper())


def _sub(parent, tag, **attrs):
    el = parent.makeelement(qn(tag), attrs)
    parent.append(el)
    return el


def _find_fill(spPr):
    for tag in ("a:noFill", "a:solidFill", "a:gradFill", "a:pattFill", "a:blipFill", "a:grpFill"):
        el = spPr.find(qn(tag))
        if el is not None:
            return el
    return None


def _set_srgb_alpha(srgb_clr, alpha):
    for el in list(srgb_clr):
        if el.tag == qn("a:alpha"):
            srgb_clr.remove(el)
    a = srgb_clr.makeelement(qn("a:alpha"), {"val": str(int(alpha * 100000))})
    srgb_clr.append(a)


def _shape_fill_alpha(shape, alpha):
    """apply alpha to an existing solid fill"""
    spPr = shape.fill._xPr
    fill = _find_fill(spPr)
    if fill is None or fill.tag != qn("a:solidFill"):
        return
    srgb = fill.find(qn("a:srgbClr"))
    if srgb is not None:
        _set_srgb_alpha(srgb, alpha)


# ---------------------------------------------------------------- shadows / effects
def _effect_lst(spPr, create=True):
    el = spPr.find(qn("a:effectLst"))
    if el is None and create:
        el = spPr.makeelement(qn("a:effectLst"), {})
        # effectLst must sit after fill/line and before scene3d / sp3d
        spPr.append(el)
    return el


def drop_shadow(shape, blur=28, dist=12, direction=5400000, alpha=0.45, color="000000"):
    """soft outer shadow. direction in 60000ths of a degree (5400000 = down)."""
    spPr = shape._element.spPr
    eff = _effect_lst(spPr)
    for el in list(eff):
        if el.tag == qn("a:outerShdw"):
            eff.remove(el)
    shdw = etree.SubElement(eff, qn("a:outerShdw"), {
        "blurRad": str(int(blur * 12700)),
        "dist": str(int(dist * 12700)),
        "dir": str(int(direction)),
        "algn": "ctr",
        "rotWithShape": "0",
    })
    clr = etree.SubElement(shdw, qn("a:srgbClr"), {"val": color})
    etree.SubElement(clr, qn("a:alpha"), {"val": str(int(alpha * 100000))})


def soft_edge(shape, radius=18):
    spPr = shape._element.spPr
    eff = _effect_lst(spPr)
    for el in list(eff):
        if el.tag == qn("a:softEdge"):
            eff.remove(el)
    etree.SubElement(eff, qn("a:softEdge"), {"rad": str(int(radius * 12700))})


def blur_shape(shape, radius=90):
    spPr = shape._element.spPr
    eff = _effect_lst(spPr)
    for el in list(eff):
        if el.tag == qn("a:blur"):
            eff.remove(el)
    etree.SubElement(eff, qn("a:blur"), {"rad": str(int(radius * 12700)), "grow": "1"})


# ---------------------------------------------------------------- shapes
def rect(slide, x, y, w, h, fill=WHITE, alpha=None, radius=None, line=None,
         line_w=1.0, line_alpha=None, shadow=None, name=None, shape_type=None):
    if radius is None:
        shp_type = shape_type or MSO_SHAPE.RECTANGLE
    else:
        shp_type = shape_type or MSO_SHAPE.ROUNDED_RECTANGLE
    shp = slide.shapes.add_shape(shp_type, E(x), E(y), E(w), E(h))
    shp.shadow.inherit = False
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
        if alpha is not None:
            _shape_fill_alpha(shp, alpha)
    if radius is not None and shp_type == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            shp.adjustments[0] = max(0.0, min(0.5, radius))
        except Exception:
            pass
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(line_w)
        if line_alpha is not None:
            ln = shp.line._get_or_add_ln()
            srgb = ln.find(qn("a:solidFill")).find(qn("a:srgbClr"))
            _set_srgb_alpha(srgb, line_alpha)
    if shadow:
        drop_shadow(shp, **shadow)
    if name:
        shp.name = name
    tf = shp.text_frame
    tf.word_wrap = False
    tf.margin_left = 0; tf.margin_right = 0
    tf.margin_top = 0; tf.margin_bottom = 0
    return shp


def ellipse(slide, x, y, w, h, fill, alpha=1.0, blur=None, name=None, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, E(x), E(y), E(w), E(h))
    shp.shadow.inherit = False
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    if alpha < 1.0:
        _shape_fill_alpha(shp, alpha)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(1)
    if blur:
        blur_shape(shp, blur)
    if name:
        shp.name = name
    return shp


def line(slide, x1, y1, x2, y2, color=LINE, width=1.0, alpha=None, dash=None):
    from pptx.enum.shapes import MSO_CONNECTOR
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
    conn.line.color.rgb = rgb(color)
    conn.line.width = Pt(width)
    if alpha is not None:
        srgb = conn.line._get_or_add_ln().find(qn("a:solidFill")).find(qn("a:srgbClr"))
        _set_srgb_alpha(srgb, alpha)
    if dash:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        conn.line.dash_style = dash
    return conn


def gradient_rect(slide, x, y, w, h, stops, angle=90, radius=None, line=None,
                  line_alpha=None, shadow=None, name=None):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius is not None else MSO_SHAPE.RECTANGLE,
        E(x), E(y), E(w), E(h))
    shp.shadow.inherit = False
    shp.fill.gradient()
    shp.fill.gradient_angle = angle
    gs = shp.fill.gradient_stops
    for i, (pos, color, alpha) in enumerate(stops):
        if i >= len(gs):
            break
        gs[i].color.rgb = rgb(color)
        gs[i].position = pos
        srgb = gs[i].color._xFill.srgbClr
        _set_srgb_alpha(srgb, alpha if alpha is not None else 1.0)
    if radius is not None:
        try:
            shp.adjustments[0] = max(0.0, min(0.5, radius))
        except Exception:
            pass
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(1)
        if line_alpha is not None:
            srgb = shp.line._get_or_add_ln().find(qn("a:solidFill")).find(qn("a:srgbClr"))
            _set_srgb_alpha(srgb, line_alpha)
    if shadow:
        drop_shadow(shp, **shadow)
    if name:
        shp.name = name
    return shp


# ---------------------------------------------------------------- text
_ALIGN = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT, "j": PP_ALIGN.JUSTIFY}
_ANCHOR = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}


def _set_run_font(run, latin, ea=None, bold=None, italic=None, size=None, color=None, spc=None):
    f = run.font
    if size is not None:
        f.size = Pt(size)
    f.name = latin
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = rgb(color)
    rPr = run._r.get_or_add_rPr()
    if ea:
        for el in rPr.findall(qn("a:ea")):
            rPr.remove(el)
        ea_el = rPr.makeelement(qn("a:ea"), {"typeface": ea})
        # a:ea comes after a:latin
        latin_el = rPr.find(qn("a:latin"))
        if latin_el is not None:
            latin_el.addnext(ea_el)
        else:
            rPr.append(ea_el)
    if spc is not None:
        rPr.set("spc", str(int(spc)))


def _set_run_gradient(run, stops, angle=90):
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:noFill", "a:solidFill", "a:gradFill", "a:pattFill", "a:blipFill", "a:grpFill"):
        for el in rPr.findall(qn(tag)):
            rPr.remove(el)
    gs_xml = []
    for pos, color, alpha in stops:
        gs_xml.append(
            '<a:gs pos="%d"><a:srgbClr val="%s"><a:alpha val="%d"/></a:srgbClr></a:gs>'
            % (int(pos * 100000), color, int(alpha * 100000)))
    xml = (
        '<a:gradFill xmlns:a="%s" rotWithShape="1">'
        '<a:gsLst>%s</a:gsLst>'
        '<a:lin ang="%d" scaled="0"/>'
        '</a:gradFill>' % (NS_A, "".join(gs_xml), int(angle * 60000))
    )
    grad = parse_xml(xml)
    # fill must come before effectLst / highlight / uLn / latin ...
    order = ["a:effectLst", "a:effectDag", "a:highlight", "a:uLnTx", "a:uLn",
             "a:uFillTx", "a:uFill", "a:latin", "a:ea", "a:cs", "a:sym",
             "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst"]
    idx = len(rPr)
    for i, child in enumerate(rPr):
        if child.tag in [qn(t) for t in order]:
            idx = i
            break
    rPr.insert(idx, grad)


def tb(slide, x, y, w, h, lines, size=18, color=WHITE, font=CN, bold=False,
       align="l", anchor="t", line_spacing=None, spc=None, wrap=True,
       margins=(0, 0, 0, 0), name=None, autofit=False):
    """lines: str | list of (str | dict | list-of-run-dicts).

    paragraph dict keys: text, runs, size, color, font, bold, align, line_spacing,
    space_before, space_after, spc, gradient (list of (pos, color, alpha)), alpha.
    A run dict: text, size, color, font, bold, gradient, spc, alpha.
    """
    box = slide.shapes.add_textbox(E(x), E(y), E(w), E(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = E(margins[0]); tf.margin_right = E(margins[1])
    tf.margin_top = E(margins[2]); tf.margin_bottom = E(margins[3])
    tf.vertical_anchor = _ANCHOR[anchor]
    if isinstance(lines, str):
        lines = [lines]
    first = True
    for ln in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = _ALIGN[align]
        cfg = {}
        if isinstance(ln, dict):
            cfg = ln
            runs = ln.get("runs")
            if runs is None:
                runs = [{"text": ln.get("text", "")}]
        elif isinstance(ln, (list, tuple)):
            runs = ln
        else:
            runs = [{"text": ln}]
        p_size = cfg.get("size", size)
        p_color = cfg.get("color", color)
        p_font = cfg.get("font", font)
        p_bold = cfg.get("bold", bold)
        p_align = cfg.get("align", align)
        p.alignment = _ALIGN[p_align]
        ls = cfg.get("line_spacing", line_spacing)
        if ls is not None:
            p.line_spacing = ls
        if cfg.get("space_before") is not None:
            p.space_before = Pt(cfg["space_before"])
        if cfg.get("space_after") is not None:
            p.space_after = Pt(cfg["space_after"])
        style_keys = ("color", "font", "bold", "italic", "spc", "alpha", "gradient")
        for rd in runs:
            if isinstance(rd, str):
                rd = {"text": rd}
            inherited = {k: cfg[k] for k in style_keys if k in cfg}
            inherited.update(rd)
            rd = inherited
            r = p.add_run()
            r.text = rd.get("text", "")
            _set_run_font(r, rd.get("font", p_font), rd.get("ea", p_font),
                          bold=rd.get("bold", p_bold), italic=rd.get("italic"),
                          size=rd.get("size", p_size), color=rd.get("color", p_color),
                          spc=rd.get("spc", cfg.get("spc", spc)))
            if rd.get("gradient"):
                _set_run_gradient(r, rd["gradient"], rd.get("angle", 0))
            if rd.get("alpha") is not None:
                rPr = r._r.get_or_add_rPr()
                sf = rPr.find(qn("a:solidFill"))
                if sf is not None:
                    _set_srgb_alpha(sf.find(qn("a:srgbClr")), rd["alpha"])
    return box


def pill(slide, x, y, w, h, text, *, size=10, color=WHITE, fill=None, alpha=None,
         line=None, line_alpha=None, font=CN, bold=False, spc=None, icon=None):
    shp = rect(slide, x, y, w, h, fill=fill, alpha=alpha, radius=0.5,
               line=line, line_w=1, line_alpha=line_alpha)
    tf = shp.text_frame
    tf.word_wrap = False
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    _set_run_font(r, font, font, size=size, color=color, bold=bold, spc=spc)
    return shp


def picture(slide, path, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = E(w)
    if h is not None:
        kw["height"] = E(h)
    return slide.shapes.add_picture(str(path), E(x), E(y), **kw)


def icon(slide, assets, name, x, y, size=0.34):
    path = assets / ("icon_%s.png" % name)
    if not path.exists():
        return None
    return slide.shapes.add_picture(str(path), E(x), E(y), E(size), E(size))


def set_slide_bg(slide, prs, color=INK):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = rgb(color)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text
