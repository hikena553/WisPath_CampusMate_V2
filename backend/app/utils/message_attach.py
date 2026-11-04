"""附件消息协议：单聊/群聊消息 content 为 JSON 文本，会话摘要与文件汇总共用同一份解析口径。"""
import json
from typing import Any, Optional

ATTACHMENT_TYPES = ("file", "image", "voice")


def parse_attachment(content: Optional[str]) -> Optional[dict[str, Any]]:
    """解析附件消息，普通文本返回 None。"""
    if not content:
        return None
    raw = content.strip()
    if not raw.startswith("{"):
        return None
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    if parsed.get("type") not in ATTACHMENT_TYPES:
        return None
    url = parsed.get("url")
    if not isinstance(url, str) or not url:
        return None
    text = parsed.get("text")
    return {
        "type": parsed["type"],
        "text": text if isinstance(text, str) else "",
        "url": url,
        "duration": int(parsed.get("duration") or 0),
    }


def _format_duration(seconds: int) -> str:
    total = max(0, seconds)
    return f"{total // 60}:{total % 60:02d}"


def preview_of(content: Optional[str]) -> str:
    """会话列表最后一条消息的纯文本预览。"""
    meta = parse_attachment(content)
    if not meta:
        return content or ""
    if meta["type"] == "image":
        return "[图片]"
    if meta["type"] == "voice":
        return f"[语音] {_format_duration(meta['duration'])}"
    return f"[文件] {meta['text'] or '未命名文件'}"
