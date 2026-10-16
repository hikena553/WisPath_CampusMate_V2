import base64
import json
import logging
import re

import httpx
from datetime import date
from openai import AsyncOpenAI, APIError

from app.core.config import settings
from app.core.crypto import decrypt_value
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.setting import SystemSetting
# 提示词统一收敛在 app.services.prompts（见《提示词工程规范.md》）；
# ESSENCE_MODE_NOTE / build_answer_mode_note 在此再导出，保持既有调用方兼容。
from app.services.prompts import (  # noqa: F401
    ESSENCE_MODE_NOTE,
    ROLE_GREETING,
    build_answer_mode_note,
    build_image_recognize_prompt,
    build_student_system_prompt,
    build_teacher_system_prompt,
)

logger = logging.getLogger(__name__)

_client_instance: AsyncOpenAI | None = None
_client_config_hash: str = ""


# 系统设置中可被 AI 服务读取的配置键
_DB_SETTING_KEYS = (
    'llm_api_key', 'llm_base_url', 'llm_model',
    'llm_agent_model', 'llm_vision_model',
    'llm_agent_temperature', 'llm_agent_max_tokens',
    # AI 助手配置：自我称谓 / 语音音色 / 自定义系统提示词
    'agent_name', 'llm_tts_voice', 'system_prompt',
)


def _get_db_settings() -> dict:
    """从数据库获取AI相关设置"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        db_settings = db.query(SystemSetting).filter(
            SystemSetting.key.in_(_DB_SETTING_KEYS)
        ).all()
        return {s.key: s.value for s in db_settings}
    except Exception:
        logger.exception("获取数据库 LLM 配置失败")
        return {}
    finally:
        db.close()


def _get_llm_config() -> dict:
    """获取LLM配置，优先使用数据库设置，其次使用环境变量"""
    db_settings = _get_db_settings()

    def _val(key: str, env_fallback: str, default: str = "") -> str:
        # 数据库设置优先，未配置时才回退到 .env
        if key in db_settings and db_settings[key]:
            return db_settings[key]
        if env_fallback:
            return env_fallback
        return default

    # api_key 特殊处理：数据库存的是加密值，需解密后判断是否有效（为空则回退 .env）
    db_key = decrypt_value(db_settings.get('llm_api_key') or "")
    api_key = db_key or settings.llm_api_key

    return {
        'api_key': api_key,
        'base_url': _val('llm_base_url', settings.LLM_BASE_URL),
        'model': _val('llm_model', settings.LLM_MODEL, "qwen-turbo"),
        'agent_model': _val('llm_agent_model', settings.LLM_AGENT_MODEL),
        'vision_model': _val('llm_vision_model', settings.LLM_VISION_MODEL, "qwen-vl-plus"),
        'temperature': float(_val('llm_agent_temperature', str(settings.LLM_AGENT_TEMPERATURE), "0.5")),
        'max_tokens': int(_val('llm_agent_max_tokens', str(settings.LLM_AGENT_MAX_TOKENS), "4096")),
    }


def _get_client() -> AsyncOpenAI:
    global _client_instance, _client_config_hash
    config = _get_llm_config()
    config_hash = f"{config['api_key']}:{config['base_url']}"
    if _client_instance is None or config_hash != _client_config_hash:
        if not config['api_key']:
            raise RuntimeError("LLM 未配置 API Key，请在系统设置中配置")
        _client_instance = AsyncOpenAI(api_key=config['api_key'], base_url=config['base_url'], timeout=60.0)
        _client_config_hash = config_hash
    return _client_instance


def build_system_prompt(user: User | None = None) -> str:
    """组装系统提示词。

    本函数只负责读取配置与准备运行时变量（称谓/学院/日期），
    提示词文本与模块结构由 ``app.services.prompts.system`` 提供，
    遵循《提示词工程规范.md》§2/§3/§4。
    """
    db_settings = _get_db_settings()
    agent_name = (db_settings.get('agent_name') or "").strip() or settings.AGENT_NAME

    role = user.role.value if user else "student"
    greeting = ROLE_GREETING.get(role, "同学")
    college = f"，来自{user.college}" if user and user.college else ""
    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    today = date.today()
    today_str = f"{today.isoformat()}（星期{weekday_names[today.weekday()]}）"

    # 自定义系统提示词：管理员在系统设置中配置后直接采用
    # 支持占位符：{agent_name} / {greeting} / {college} / {today}
    custom_prompt = (db_settings.get('system_prompt') or "").strip()
    if custom_prompt:
        try:
            return custom_prompt.format(
                agent_name=agent_name,
                greeting=greeting,
                college=college,
                today=today_str,
                today_date=today.isoformat(),
            )
        except (KeyError, IndexError):
            return custom_prompt

    if role == "student":
        return build_student_system_prompt(
            agent_name=agent_name,
            greeting=greeting,
            college=college,
            today_str=today_str,
            today_iso=today.isoformat(),
        )
    return build_teacher_system_prompt(
        agent_name=agent_name,
        greeting=greeting,
        college=college,
        today_str=today_str,
    )


def speech_to_text(audio_bytes: bytes, filename: str) -> str:
    """调用 Token Plan 语音识别（qwen-audio-3.0-asr-flash，多模态生成端点）"""
    config = _get_llm_config()
    if not config['api_key']:
        raise RuntimeError("LLM 未配置 API Key")

    name_lower = (filename or "").lower()
    if name_lower.endswith(".mp3"):
        mime, fmt = "audio/mpeg", "mp3"
    elif name_lower.endswith(".opus") or name_lower.endswith(".ogg"):
        mime, fmt = "audio/ogg", "opus"
    else:
        mime, fmt = "audio/wav", "wav"
    data_uri = f"data:{mime};base64," + base64.b64encode(audio_bytes).decode()

    payload = {
        "model": "qwen-audio-3.0-asr-flash",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "input_audio": {"data": data_uri}},
                    ],
                }
            ]
        },
        "parameters": {"format": fmt, "sample_rate": "16000"},
    }
    url = f"{settings.llm_native_base}/api/v1/services/aigc/multimodal-generation/generation"
    headers = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        body = resp.json()
        out = body.get("output") or body
        return (out.get("text") or (out.get("sentence") or {}).get("text") or "").strip()
    except Exception as e:
        raise RuntimeError(f"语音识别失败: {e}")


def _parse_json_loose(text: str) -> dict | None:
    """从可能带代码块或前后缀文字的模型回复中提取第一个 JSON 对象。"""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def recognize_image(image_url: str, hint: str = "") -> dict:
    """调用多模态模型识别图片内容。

    成功返回 {"success": True, ...识别字段}；
    不可用时返回 {"success": False, "reason": ...}，调用方必须降级为让用户文字描述。
    """
    from app.utils.image_utils import to_data_url

    config = _get_llm_config()
    vision_model = config.get('vision_model')
    if not vision_model:
        return {"success": False, "reason": "未配置视觉模型 LLM_VISION_MODEL"}
    if not config['api_key']:
        return {"success": False, "reason": "未配置 LLM API Key"}

    data_url = to_data_url(image_url)
    if not data_url:
        # 本地文件读不到时，公网地址可直接交给模型
        if image_url.startswith(("http://", "https://")):
            data_url = image_url
        else:
            return {"success": False, "reason": "图片文件无法读取"}

    prompt = build_image_recognize_prompt(hint)

    try:
        resp = await _get_client().chat.completions.create(
            model=vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=0.2,
            max_tokens=600,
        )
    except Exception as e:
        logger.warning("图片识别调用失败（model=%s）: %s", vision_model, e)
        return {"success": False, "reason": f"图片识别服务不可用: {e}"}

    content = (resp.choices[0].message.content or "").strip()
    parsed = _parse_json_loose(content)
    if not parsed:
        return {"success": False, "reason": "图片识别结果无法解析", "raw": content[:200]}
    parsed["success"] = True
    logger.info("图片识别成功: category=%s name=%s", parsed.get("category"), parsed.get("name"))
    return parsed


async def complete(prompt: str, *, model: str | None = None,
                   temperature: float | None = None, max_tokens: int | None = None,
                   extra_body: dict | None = None) -> str:
    """一次性（非流式）补全，供内部服务生成短文案使用（如主动发现洞察）。

    与 agent 普通对话保持同一口径：
    - 模型优先 agent_model；
    - 默认显式关闭思考（``thinking: disabled``）——本项目所用推理模型在默认/思考模式下
      首字极慢（实测一句 20 token 回复约 8s，开思考时 20s 都出不来），关闭后短文案秒回。
    未配置 API Key 时抛 RuntimeError（调用方据此快速降级，不做网络请求）。
    """
    config = _get_llm_config()
    if not config.get('api_key'):
        raise RuntimeError("LLM 未配置 API Key，请在系统设置中配置")
    resp = await _get_client().chat.completions.create(
        model=model or config.get('agent_model') or config['model'],
        messages=[{"role": "user", "content": prompt}],
        temperature=config['temperature'] if temperature is None else temperature,
        max_tokens=config['max_tokens'] if max_tokens is None else max_tokens,
        extra_body=extra_body if extra_body is not None else {"thinking": {"type": "disabled"}},
    )
    return (resp.choices[0].message.content or "").strip()


async def chat_stream(messages: list[dict]):
    config = _get_llm_config()
    try:
        response = await _get_client().chat.completions.create(
            model=config['model'],
            messages=messages,
            stream=True,
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
        )
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except APIError:
        raise
    except Exception:
        raise