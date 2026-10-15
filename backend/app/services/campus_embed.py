"""校内页面「原版渲染」代理：把学校页面反代成可被应用内 iframe 嵌入的 HTML。

为什么需要这一层：
- 学校站点带 ``X-Frame-Options: SAMEORIGIN``，浏览器拒绝把学校页面直接嵌进应用；
- 这里以「我们自己的响应」返回页面（不带该响应头），浏览器即允许嵌入；
- 注入 ``<base>`` 指回学校站，让相对路径的图片/样式继续生效，尽量保留原版排版。

安全边界（与前端 iframe 的 sandbox 配合）：
- 前端 iframe 必须带 ``sandbox`` 且**不含** ``allow-same-origin``，脚本跑在不透明源，
  拿不到应用的 Cookie / localStorage；
- 仅代理白名单内的校内公开页面，无需登录态（跨源 iframe 也带不上 SameSite=Lax Cookie）。

桥接协议（供前端 ArticleReader 监听 ``window.message``）：
- ``{source: 'campus-reader', type: 'ready', url, title}`` 渲染完成；
- ``{source: 'campus-reader', type: 'navigate', url, title}`` 页内点击链接，请父页面在阅读器内跳转；
- ``{source: 'campus-reader', type: 'error', message}`` 页面脚本报错。
"""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.article_reader import fetch_html, is_allowed_url

BRIDGE_SOURCE = "campus-reader"


def _bridge_script(url: str, extra: str = "") -> str:
    """注入的桥接脚本：通知就绪、拦截页内链接、上报错误。"""
    safe_url = json.dumps(url, ensure_ascii=False)
    return f"""
<script>
(function () {{
  var SOURCE = {json.dumps(BRIDGE_SOURCE)};
  var PAGE_URL = {safe_url};
  function post(type, payload) {{
    try {{
      parent.postMessage(Object.assign({{ source: SOURCE, type: type, url: PAGE_URL }}, payload || {{}}), '*');
    }} catch (e) {{ /* 父窗口不存在时忽略 */ }}
  }}
  document.addEventListener('click', function (ev) {{
    var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) return;
    ev.preventDefault();
    var abs;
    try {{ abs = new URL(href, PAGE_URL).href; }} catch (e) {{ return; }}
    post('navigate', {{ url: abs, title: (a.textContent || '').trim().slice(0, 120) }});
  }}, true);
  window.addEventListener('error', function (e) {{
    post('error', {{ message: (e && e.message) || '页面脚本异常' }});
  }});
  window.addEventListener('load', function () {{
    post('ready', {{ title: document.title || '' }});
  }});
  post('ready', {{ title: document.title || '' }});
  {extra}
}})();
</script>
"""


def build_embed_html(url: str, embed_base: str) -> str:
    """抓取校内页面并注入 ``<base>`` + 桥接脚本，返回可内嵌的 HTML。"""
    final_url, html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # 去掉学校页面自带的 <base> 与可能拦截内嵌/内联脚本的 meta 声明
    for tag in soup.find_all("base"):
        tag.decompose()
    for meta in soup.find_all("meta"):
        http_equiv = (meta.get("http-equiv") or "").lower()
        if http_equiv in ("content-security-policy", "x-frame-options", "refresh"):
            meta.decompose()

    head = soup.head
    if head is None:
        head = soup.new_tag("head")
        if soup.html:
            soup.html.insert(0, head)
        else:
            soup.insert(0, head)

    base_href = urljoin(final_url, ".")
    base_tag = soup.new_tag("base", href=base_href)
    head.insert(0, base_tag)

    # 移动端视口：多数校园老站没有 viewport，补一个避免 iframe 内按桌面宽度缩放
    viewport = soup.new_tag("meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1"})
    head.insert(1, viewport)

    script_tag = BeautifulSoup(_bridge_script(final_url), "html.parser")
    if soup.body:
        soup.body.append(script_tag)
    else:
        soup.append(script_tag)

    return str(soup)


def build_embed_error_html(url: str, message: str) -> str:
    """抓取失败时给 iframe 的可读错误页；会向父页面上报 error，便于前端切到错误态。"""
    safe_msg = re.sub(r"<[^>]*>", "", message or "页面暂不可用")
    error_script = _bridge_script(url, extra=f"post('error', {{ message: {json.dumps(safe_msg, ensure_ascii=False)} }});")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>页面暂不可用</title>
  <style>
    html, body {{ margin: 0; height: 100%; }}
    body {{
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      gap: 10px; padding: 32px 24px; box-sizing: border-box; text-align: center;
      font-family: -apple-system, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
      color: #4b5563; background: #f7f8fa;
    }}
    .mark {{ font-size: 34px; }}
    .title {{ font-size: 15px; font-weight: 600; color: #1f2329; }}
    .desc {{ font-size: 13px; line-height: 1.6; max-width: 320px; color: #6b7280; }}
  </style>
</head>
<body>
  <div class="mark">📄</div>
  <div class="title">页面暂不可用</div>
  <div class="desc">{safe_msg}</div>
{error_script}
</body>
</html>
"""


def assert_allowed(url: str) -> None:
    """供 API 层复用的白名单断言。"""
    if not is_allowed_url(url):
        raise PermissionError("仅支持校内站点链接")