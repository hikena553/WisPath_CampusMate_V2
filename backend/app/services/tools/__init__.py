"""AI 工具注册表子包（p4_2 拆分自 services/tool_registry.py）。

公共 API：TOOL_DEFINITIONS / TEACHER_TOOL_DEFINITIONS / execute_tool
（_tool_call_counters 供测试清理限流计数使用）。
"""

from .definitions import TEACHER_TOOL_DEFINITIONS, TOOL_DEFINITIONS
from .dispatcher import execute_tool
from .sanitize import _tool_call_counters

__all__ = [
    "TOOL_DEFINITIONS",
    "TEACHER_TOOL_DEFINITIONS",
    "execute_tool",
    "_tool_call_counters",
]
