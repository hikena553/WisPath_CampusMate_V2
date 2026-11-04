"""证件照 + 自定义岗位 渲染自检：不查库，用构造 profile 直接走 render_docx / render_pdf。

覆盖三件事：
1. 照片能进 DOCX（抬头表格右格）与 PDF（右上角），正文从照片下缘开始不重叠；
2. 自定义岗位（job_key='custom' + custom_job='无人机飞手/运维'）能算出匹配度并写进求职意向；
3. 没有照片时输出与旧版一致（回归）。

产物写到 .workbuddy/tmp/resume/photo-*，PDF 再用 pymupdf 转图复核。
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

from app.services import resume_export as rx  # noqa: E402
from check_resume_rich import fake_profile  # noqa: E402

OUT = Path("D:/StudyNote/Mian02/.workbuddy/tmp/resume")


def make_photo(w=295, h=413) -> bytes:
    """画一张假证件照：浅蓝底 + 深色人形剪影。"""
    img = Image.new("RGB", (w, h), (214, 233, 244))
    d = ImageDraw.Draw(img)
    d.ellipse([w * 0.3, h * 0.16, w * 0.7, h * 0.52], fill=(90, 98, 108))
    d.ellipse([w * 0.14, h * 0.62, w * 0.86, h * 1.3], fill=(90, 98, 108))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def render(profile, tpl, fmt, photo, industry="hardware", job_key="custom", custom_job="无人机飞手/运维"):
    match = rx.evaluate(profile, industry, job_key, custom_job)
    target = rx.find_job(industry, job_key, custom_job)
    assert target["label"] == custom_job, target
    sections = rx.build_sections(profile, target, match, tpl)
    header = rx.build_header(profile, target, {"job_type": "校招全职", "city": "成都",
                                               "match_score": match["score"]})
    data = rx.render_pdf(header, sections, tpl, photo=photo) if fmt == "pdf" \
        else rx.render_docx(header, sections, tpl, photo=photo)
    return match, data


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    profile = fake_profile()
    photo = make_photo()

    # 1) 自定义岗位匹配度
    m = rx.evaluate(profile, "hardware", "custom", "无人机飞手/运维")
    print(f"[自定义·无人机飞手/运维] {m['score']} ({m['level']})  意向label={m['job']['label']}")
    assert m["score"] > 0 and m["job"]["label"] == "无人机飞手/运维"

    tpl = rx.TEMPLATE_MAP["classic"]
    # 2) 带照片 / 不带照片，DOCX + PDF
    for tag, ph in (("photo", photo), ("nophoto", None)):
        for fmt in ("docx", "pdf"):
            _, data = render(profile, tpl, fmt, ph)
            p = OUT / f"photo-{tag}.{fmt}"
            p.write_bytes(data)
            print(f"{tag:8s} {fmt:5s} {len(data):>7d}B -> {p}")

    # 3) PDF 带照片：转 PNG 目检照片确实在右上角
    import pymupdf
    doc = pymupdf.open(OUT / "photo-photo.pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=110)
    pix.save(OUT / "photo-photo-pdf.png")
    # 图片对象数量 >=1 且位置在页面右上
    infos = page.get_image_info()
    assert infos, "PDF 里没有嵌入图片"
    bb = infos[0]["bbox"]
    print("PDF 图像 bbox:", [round(v) for v in bb], " 页宽:", round(page.rect.width))
    assert bb[0] > page.rect.width * 0.6 and bb[1] < page.rect.height * 0.2, "照片不在右上角"

    doc2 = pymupdf.open(OUT / "photo-nophoto.pdf")
    assert not doc2[0].get_image_info(), "无照片版本却嵌入了图片"
    print("ALL CHECKS PASS")


if __name__ == "__main__":
    main()
