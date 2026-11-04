"""教师端「AI 帮我写」统一文案起草服务。

各填写类弹窗（班级公告 / 关怀记录 / 家校沟通 / 危机处置 / 问卷建议等）共用同一入口：
场景 + 老师补充描述 + 必须覆盖的要点 + 本地参考草稿 → 一段可直接编辑的中文文案。
模型未配置或生成失败时抛出异常，由接口层回退到本地参考草稿，保证按钮永远有结果。
"""
import logging

from app.services.llm_service import complete

logger = logging.getLogger(__name__)

_MIN_LEN = 12


def _fallback_text(
    brief: str, points: list[str], reference: str, max_length: int
) -> str:
    """本地兜底：优先沿用参考草稿，其次按描述与要点拼出一段初稿。"""
    if reference.strip():
        return reference.strip()[:max_length]
    base = brief.strip()
    if not base:
        return ""
    text = f"{base.rstrip('。')}。"
    if points:
        text += f"围绕{'、'.join(points)}逐项补充完整。"
    return text[:max_length]


def _build_prompt(
    scene: str, brief: str, points: list[str], reference: str, max_length: int
) -> str:
    point_line = "、".join(points) if points else "无固定要点，按场景自然展开"
    ref_line = reference.strip() or "（无）"
    brief_line = brief.strip() or "（未填写）"
    return (
        "你是高校辅导员工作台的写作助手。请根据下面的信息，起草一段可直接提交的中文文案。\n"
        f"场景：{scene}\n"
        f"老师补充描述：{brief_line}\n"
        f"必须覆盖的要点：{point_line}\n"
        f"可参考的本地草稿（包含真实的场景、对象与时间，请在此基础上改写润色，保留其中的事实）：\n{ref_line}\n"
        "要求：\n"
        "1. 用第一人称，具体、克制，避免空泛套话；\n"
        "2. 覆盖全部要点，行文连贯，不要逐条罗列；\n"
        "3. 不得编造未提供的人名、数字、日期或结果；\n"
        f"4. 不超过 {max_length} 字；\n"
        "5. 只输出正文，不要标题、不要解释、不要引号。"
    )


async def ai_draft(
    scene: str,
    brief: str = "",
    points: list[str] | None = None,
    reference: str = "",
    max_length: int = 500,
) -> str:
    """调用大模型起草文案；失败时抛异常，由接口层兜底。"""
    scene = (scene or "").strip()[:40] or "教师工作记录"
    brief = (brief or "").strip()[:500]
    reference = (reference or "").strip()[:1200]
    points = [str(p).strip()[:40] for p in (points or []) if str(p).strip()][:10]
    max_length = max(20, min(int(max_length), 2000))

    prompt = _build_prompt(scene, brief, points, reference, max_length)
    raw = await complete(
        prompt,
        temperature=0.45,
        max_tokens=min(2000, max(400, int(max_length * 1.6))),
    )
    text = (raw or "").strip().strip('"“”')
    if len(text) < _MIN_LEN:
        raise ValueError("模型未返回有效的文案内容")
    return text[:max_length]


def fallback_text(
    brief: str = "",
    points: list[str] | None = None,
    reference: str = "",
    max_length: int = 500,
) -> str:
    """接口层兜底文案（保证 200 返回，不触发前端全局错误提示）。"""
    max_length = max(20, min(int(max_length), 2000))
    return _fallback_text(brief, list(points or []), reference, max_length)
