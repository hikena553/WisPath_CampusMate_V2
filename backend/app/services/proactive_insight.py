"""AI 主动发现：LLM 个性化洞察（规则文案之外的补充）。

前端先用规则文案渲染卡片，再调 `GET /api/agent/proactive/insight` 在后台补一句
个性化提醒。本模块负责这条链路：

1. 按「学生 + 动作指纹」缓存 30 分钟——同批动作重复请求直接命中，不打 LLM；
2. 并发请求共享在途任务（同一 key 只发一次 LLM 调用），避免重复开销；
3. 未配置 LLM / 超时 / 异常一律返回 None，调用方保持规则文案（不阻塞、不报错）。
"""
import asyncio
import logging
import threading
import time

from app.models.user import User
from app.services.llm_service import complete

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 30 * 60      # 洞察缓存时长
INSIGHT_TIMEOUT_SECONDS = 8      # 单次 LLM 生成超时（超时即降级）
MAX_ACTIONS_IN_PROMPT = 3        # 只把最高优先级的几条交给 LLM
MAX_INSIGHT_CHARS = 60           # 洞察长度上限（前端卡片一行展示）

# key = (student_id, 动作指纹) -> (写入时间戳, 洞察文案)
_cache: dict[tuple[int, str], tuple[float, str]] = {}
# 在途任务：并发请求共享同一次 LLM 调用
_inflight: dict[tuple[int, str], "asyncio.Task[str | None]"] = {}
_lock = threading.Lock()


def _fingerprint(actions: list) -> str:
    """动作指纹：同一批动作（触发器 + 标题）视为同一件事。"""
    parts = sorted(f"{a.trigger}:{a.title}" for a in actions)
    return "|".join(parts)


def get_cached_insight(user: User, actions: list) -> str | None:
    """读取缓存的洞察文案；未命中 / 过期返回 None。"""
    if not actions:
        return None
    key = (user.id, _fingerprint(actions))
    with _lock:
        entry = _cache.get(key)
    if not entry:
        return None
    ts, text = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        with _lock:
            _cache.pop(key, None)
        return None
    return text


def _build_prompt(user: User, actions: list) -> str:
    picked = sorted(actions, key=lambda a: a.priority, reverse=True)[:MAX_ACTIONS_IN_PROMPT]
    lines = "\n".join(f"- {a.title}：{a.content}" for a in picked)
    return f"""你是校园 AI 助手，正在给学生「{user.name or '同学'}」做主动提醒。

系统基于真实数据发现了以下情况：
{lines}

请用一句自然、体贴的中文口语（不超过 {MAX_INSIGHT_CHARS} 字）总结提醒重点，
给出一个可执行的小建议。只返回这一句话，不要列表、不要引号、不要解释。"""


async def _produce(user: User, actions: list, key: tuple[int, str]) -> str | None:
    """真正调用 LLM 生成洞察，成功后写入缓存。"""
    try:
        text = await complete(
            _build_prompt(user, actions),
            temperature=0.6,
            max_tokens=120,
        )
        text = (text or "").strip().strip('"').strip()
        if not text:
            return None
        if len(text) > MAX_INSIGHT_CHARS * 2:
            text = text[:MAX_INSIGHT_CHARS * 2]
        with _lock:
            _cache[key] = (time.time(), text)
        return text
    except Exception as e:
        # 未配置 LLM（RuntimeError）或网络异常：静默降级为规则文案
        logger.info("[AI 洞察] 生成失败，降级为规则文案: %s", e)
        return None
    finally:
        _inflight.pop(key, None)


async def generate_insight(user: User, actions: list) -> str | None:
    """生成（或复用）学生洞察文案；失败一律返回 None。

    命中缓存直接返回；已有同 key 在途任务时复用其结果（await shield）。
    """
    if not actions:
        return None

    key = (user.id, _fingerprint(actions))

    cached = get_cached_insight(user, actions)
    if cached:
        return cached

    task = _inflight.get(key)
    if task is None:
        task = asyncio.create_task(_produce(user, actions, key))
        _inflight[key] = task

    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=INSIGHT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.info("[AI 洞察] 生成超时，降级为规则文案 student=%s", user.id)
        return None
    except Exception as e:
        logger.info("[AI 洞察] 生成异常，降级为规则文案: %s", e)
        return None


def clear_cache() -> None:
    """清空洞察缓存（供测试或配置变更时使用）。"""
    with _lock:
        _cache.clear()