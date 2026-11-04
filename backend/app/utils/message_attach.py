"""聊天消息内容的展示口径：附件消息（图片 / 语音 / 文件）统一转成一句人话。

聊天里的附件是一条**文本消息**，content 存的是 JSON：

    {"type": "image" | "voice" | "file", "text": "文件名", "url": "/api/files/root/xx", "duration": 3}

好处是不用改表结构、跨端（学生 / 教师 / 小程序）都能读；代价是「会话列表、
通知摘要、文件页」这些地方拿到的是原始 JSON。任何要按**人**展示 content 的地方
（会话摘要、引用回复等）都必须先过这里，别再把 `{"type":"image"...}` 甩给用户看。

与 `app/api/messages.py` 的 `/files` 聚合口径保持一致（同样只认 file/image/voice）。
"""
import json

ATTACHMENT_TYPES = ("file", "image", "voice")

# 会话摘要最多展示多少个字符（与原先 last_msg.content[:80] 对齐）
PREVIEW_LIMIT = 80


def parse_attachment(content: str | None) -> dict | None:
    """解析附件消息，非附件（含普通文本、坏 JSON）返回 None。"""
    if not content or not content.startswith("{"):
        return None
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("type") not in ATTACHMENT_TYPES:
        return None
    url = data.get("url")
    # 只认站内相对地址：javascript: / data: 这类伪协议一旦被文件页拼成 <a href> 就是注入点
    if not isinstance(url, str) or not url.startswith("/") or url.startswith("//"):
        return None
    return {
        "type": data["type"],
        "text": data.get("text") or "",
        "url": url,
        "duration": int(data.get("duration") or 0),
    }


def _format_duration(seconds: int) -> str:
    """语音时长口径：`3″` / `1′05″`（与会话里看到的语音条一致）"""
    seconds = max(0, int(seconds or 0))
    if seconds < 60:
        return f"{seconds}″"
    return f"{seconds // 60}′{seconds % 60:02d}″"


def preview_of(content: str | None) -> str:
    """会话列表 / 摘要用的一句话预览：附件转「[图片]」「[语音 3″]」「[文件] xxx」，文本截断。"""
    if not content:
        return ""
    attach = parse_attachment(content)
    if attach:
        if attach["type"] == "image":
            return "[图片]"
        if attach["type"] == "voice":
            return f"[语音 {_format_duration(attach['duration'])}]"
        return f"[文件] {attach['text']}".strip()
    return content[:PREVIEW_LIMIT]
