"""枚举序列化辅助函数"""


def safe_enum_val(v):
    """安全获取枚举值，如果是 Enum 则返回 .value，否则原样返回"""
    if v is None:
        return None
    return v.value if hasattr(v, 'value') else v


def safe_enum_str(v, default=""):
    """安全获取枚举字符串值，None 时返回默认值"""
    val = safe_enum_val(v)
    return str(val) if val is not None else default
