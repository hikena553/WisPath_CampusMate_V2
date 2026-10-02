"""工具调用限流（S5）与结果脱敏辅助。

- _check_tool_rate_limit：每用户每分钟 N 次调用限流；
- _sanitize_tool_result / _sanitize_value：敏感字段移除、长文本截断、列表限条。
"""




# 简单的每用户工具调用限速（每分钟 30 次）
_tool_call_counters: dict[int, list[float]] = {}
_TOOL_RATE_LIMIT = 30
_TOOL_RATE_WINDOW = 60.0

# ============ S5 工具结果脱敏规则 ============
_SANITIZE_TRUNCATE_SUMMARY = 80   # 危机/文档摘要统一截断长度
_SANITIZE_TRUNCATE_REASON = 50    # 请假原因截断长度
_SANITIZE_TRUNCATE_MESSAGE = 200  # 顶层 message 截断长度
_SANITIZE_MAX_LIST_ITEMS = 20     # 列表条数上限
_SANITIZE_DROP_KEYS = ("username", "phone", "email", "id_card")  # 敏感字段直接移除


def _truncate_text(value: str, limit: int) -> str:
    value = str(value)
    return value if len(value) <= limit else value[:limit] + "…"


def _sanitize_value(value):
    """递归脱敏：移除敏感字段、截断长文本、限制列表条数"""
    if isinstance(value, dict):
        cleaned = {}
        for key, val in value.items():
            if key in _SANITIZE_DROP_KEYS:
                continue
            if key == "summary" and isinstance(val, str):
                cleaned[key] = _truncate_text(val, _SANITIZE_TRUNCATE_SUMMARY)
            elif key == "reason" and isinstance(val, str):
                cleaned[key] = _truncate_text(val, _SANITIZE_TRUNCATE_REASON)
            else:
                cleaned[key] = _sanitize_value(val)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value[:_SANITIZE_MAX_LIST_ITEMS]]
    return value


def _sanitize_tool_result(name: str, result: dict) -> dict:
    """工具结果统一脱敏（S5）：学号等敏感字段移除、危机摘要/请假原因截断、列表限条、message 限长"""
    if not isinstance(result, dict):
        return result
    truncated_hint = any(
        isinstance(v, list) and len(v) > _SANITIZE_MAX_LIST_ITEMS
        for k, v in result.items() if k not in ("message",)
    )
    sanitized = {}
    for key, value in result.items():
        if key in _SANITIZE_DROP_KEYS:
            continue
        if key == "message" and isinstance(value, str):
            text = value
            if truncated_hint and "仅展示" not in text:
                text += f"（数据较多，仅展示前{_SANITIZE_MAX_LIST_ITEMS}条）"
            sanitized[key] = _truncate_text(text, _SANITIZE_TRUNCATE_MESSAGE)
        else:
            sanitized[key] = _sanitize_value(value)
    return sanitized


def _check_tool_rate_limit(user_id: int) -> bool:
    """返回 True 表示允许调用，False 表示超限"""
    import time
    now = time.monotonic()
    calls = _tool_call_counters.setdefault(user_id, [])
    # 清理过期记录
    _tool_call_counters[user_id] = [t for t in calls if now - t < _TOOL_RATE_WINDOW]
    if len(_tool_call_counters[user_id]) >= _TOOL_RATE_LIMIT:
        return False
    _tool_call_counters[user_id].append(now)
    return True
