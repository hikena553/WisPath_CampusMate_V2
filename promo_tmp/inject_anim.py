# -*- coding: utf-8 -*-
"""
为绵小城宣传片 PPTX 注入苹果风动画（v3 - 标准 PowerPoint 结构）：
1. 每页 slide transition（分节页 push，其余 fade）+ 自动换页
2. 每个 shape：fade in 淡入（错峰延迟），使用标准双层 par 结构
3. presentation.xml 添加 showPr 确保放映设置
"""
import zipfile, shutil, re, os, tempfile

PPTX = r"d:\StudyNote\Mian02\绵小城_智慧校园宣传片.pptx"

P14_NS = 'xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"'

def collect_spids(xml_str):
    ids = []
    for m in re.finditer(r'<p:cNvPr\s+id="(\d+)"', xml_str):
        sid = m.group(1)
        if sid != "1":  # skip spTree group
            ids.append(sid)
    return ids

def build_transition(slide_idx):
    """分节页用 push，内容页用 fade；带自动换页时间"""
    section_titles = {1,2,3,4,5,7,9,11,13,15,17,18}
    if slide_idx in section_titles:
        adv = 12000
        # push 转场，p14:dur 控制精确时长(ms)
        return f'<p:transition spd="med" advClick="1" advTm="{adv}" p14:dur="1200"><p:push dir="l"/></p:transition>'
    else:
        adv = 24000
        return f'<p:transition spd="slow" advClick="1" advTm="{adv}" p14:dur="1500"><p:fade/></p:transition>'

def build_timing(spids, base_delay=200, step=180, dur=600):
    """
    标准 PowerPoint 淡入动画结构：
    seq > cTn(mainSeq) > childTnLst > par(点击组, delay) > childTnLst > par(内层) > childTnLst > animEffect
    每个 shape 一个点击组，delay 递增实现依次浮现
    """
    par_blocks = []
    cid = 3
    for i, spid in enumerate(spids):
        delay = min(base_delay + i * step, 2800)
        par_blocks.append(f'''                <p:par>
                  <p:cTn id="{cid}" fill="hold">
                    <p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="{cid+1}" fill="hold">
                          <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                          <p:childTnLst>
                            <p:animEffect transition="in" filter="fade">
                              <p:cBhvr>
                                <p:cTn id="{cid+2}" dur="{dur}" fill="hold"/>
                                <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                                <p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>
                              </p:cBhvr>
                            </p:animEffect>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>''')
        cid += 3

    # 构建列表：告知 PowerPoint 哪些 shape 参与动画
    bld_items = []
    for spid in spids:
        bld_items.append(f'    <p:bldP spid="{spid}" grpId="0" uiExpand="1"/>')
    bld_lst = f'  <p:bldLst>\n{chr(10).join(bld_items)}\n  </p:bldLst>' if bld_items else ''

    timing = f'''<p:timing>
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>
{chr(10).join(par_blocks)}
              </p:childTnLst>
            </p:cTn>
            <p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
            <p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
          </p:seq>
        </p:childTnLst>
      </p:cTn>
    </p:par>
  </p:tnLst>
{bld_lst}
</p:timing>'''
    return timing

def ensure_p14_namespace(xml_str):
    """确保 slide 根元素声明了 p14 命名空间"""
    if 'xmlns:p14' in xml_str:
        return xml_str
    # 在 <p:sld ...> 中插入 p14 命名空间声明
    m = re.match(r'(<p:sld\s[^>]*?)(>)', xml_str, re.S)
    if m:
        return xml_str[:m.start(2)] + ' ' + P14_NS + xml_str[m.start(2):]
    return xml_str

def process_slide(xml_str, slide_idx):
    # 移除旧的 transition 和 timing
    xml_str = re.sub(r'<p:transition\b.*?</p:transition>', '', xml_str, flags=re.S)
    xml_str = re.sub(r'<p:timing\b.*?</p:timing>', '', xml_str, flags=re.S)

    # 确保 p14 命名空间声明
    xml_str = ensure_p14_namespace(xml_str)

    spids = collect_spids(xml_str)
    trans_xml = build_transition(slide_idx)
    timing_xml = build_timing(spids)

    close_tag = "</p:sld>"
    idx = xml_str.rfind(close_tag)
    if idx == -1:
        return xml_str
    return xml_str[:idx] + trans_xml + timing_xml + xml_str[idx:]

def process_presentation(xml_str):
    """在 presentation.xml 中添加 showPr 放映设置"""
    if '<p:showPr' in xml_str:
        return xml_str
    show_pr = '<p:showPr loop="0" showNarration="1"><p:present/></p:showPr>'
    idx = xml_str.rfind('</p:presentation>')
    if idx == -1:
        return xml_str
    return xml_str[:idx] + show_pr + xml_str[idx:]

def main():
    tmp_dir = tempfile.mkdtemp()
    extract_dir = os.path.join(tmp_dir, "extracted")
    os.makedirs(extract_dir)

    with zipfile.ZipFile(PPTX, "r") as z:
        z.extractall(extract_dir)

    slides_dir = os.path.join(extract_dir, "ppt", "slides")
    slide_files = sorted(
        [f for f in os.listdir(slides_dir) if re.match(r"slide\d+\.xml$", f)],
        key=lambda x: int(re.search(r"slide(\d+)", x).group(1))
    )
    print(f"Processing {len(slide_files)} slides...")
    for sf in slide_files:
        idx = int(re.search(r"slide(\d+)", sf).group(1))
        path = os.path.join(slides_dir, sf)
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        new_data = process_slide(data, idx)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_data)
        print(f"  slide {idx}: trans+timing OK ({len(re.findall(r'spid=\"', new_data))} anim refs)")

    pres_path = os.path.join(extract_dir, "ppt", "presentation.xml")
    with open(pres_path, "r", encoding="utf-8") as f:
        data = f.read()
    new_data = process_presentation(data)
    with open(pres_path, "w", encoding="utf-8") as f:
        f.write(new_data)
    print("  presentation.xml: showPr OK")

    out_tmp = PPTX + ".tmp"
    with zipfile.ZipFile(out_tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for root_dir, _, files in os.walk(extract_dir):
            for fn in files:
                full = os.path.join(root_dir, fn)
                arc = os.path.relpath(full, extract_dir)
                zout.write(full, arc)
    shutil.move(out_tmp, PPTX)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("Done.")

if __name__ == "__main__":
    main()
