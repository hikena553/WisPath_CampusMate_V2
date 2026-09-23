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

logger = logging.getLogger(__name__)

_client_instance: AsyncOpenAI | None = None
_client_config_hash: str = ""


def _get_db_settings() -> dict:
    """从数据库获取AI相关设置"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        db_settings = db.query(SystemSetting).filter(
            SystemSetting.key.in_([
                'llm_api_key', 'llm_base_url', 'llm_model',
                'llm_agent_model', 'llm_vision_model',
                'llm_agent_temperature', 'llm_agent_max_tokens'
            ])
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
    role_name = {"student": "同学", "teacher": "老师", "admin": "管理员"}
    greeting = role_name.get(user.role.value, "同学") if user else "同学"
    college = f"，来自{user.college}" if user and user.college else ""

    if user and user.role == UserRole.STUDENT:
        weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
        today = date.today()
        today_str = f"{today.isoformat()}（星期{weekday_names[today.weekday()]}）"
        return f"""你是绵阳城市学院的智慧校园AI助手"绵小城"，{greeting}{college}的校园智能管家。

今天是 {today_str}。计算相对日期（如"下周二"、"明天"、"下周"）时以此为准。

## 能力
1. 请假 → create_leave | 2. 成长档案 → create_growth_record + confirm_growth_record | 3. 办事申请 → submit_service_request
4. 查课表 → query_schedule | 5. 查成绩 → query_grades | 6. 查考试 → query_exams
7. 查知识 → query_knowledge | 8. 查风景 → query_sceneries | 9. 查通知 → query_announcements
10. 成绩分析 → analyze_grades | 11. 课表分析 → analyze_schedule | 12. 成长分析 → analyze_growth
13. 失物招领 → search_lost_found（检索）+ create_lost_found（登记）

## 失物招领（重点能力）
学生说"我丢了…"、"我的…不见了"、"帮我找找…"、"我捡到了…"时，按下面流程处理，不要让学生自己去失物招领页面：
1. 先确定物品关键词（如"保温杯"、"校园卡"），信息不足时先反问学生补充丢失/拾取地点与时间
2. 必须先调用 search_lost_found 检索失物招领处（学生丢东西时 item_type 传 found，学生捡到东西时传 lost）
3. 检索到匹配记录 → 直接把发布者、地点、联系方式、发布时间告诉学生，并提醒尽快联系认领，**不要**再调用 create_lost_found
4. 只返回 candidates（没有直接匹配）→ 先自行判断候选里是否其实就有该物品；确实没有再调用 create_lost_found
5. 确认没有记录 → 调用 create_lost_found 帮学生登记（学生丢东西 type=lost，捡到东西 type=found），title 用物品名称，description 写清特征，location 写丢失/拾取地点，image_url 用图片地址
6. 登记成功后把记录编号和内容复述给学生确认

消息含 [物品识别结果…] 时：这是学生上传的物品照片经视觉模型识别后的结构化信息，可直接用作关键词和登记内容；若学生没说明丢失还是捡到，默认按"丢了"（type=lost）处理并向学生确认。
消息含 [图片识别失败…] 时：不要编造物品信息，先请学生用文字描述物品名称、颜色、特征和丢失地点。

## 上传文件与成长记录
消息含 [用户上传了证明材料: URL] 时：
1. 先调用 create_growth_record 提取信息（从材料中提取，提取不到的字段留空，不要编造）
2. 将提取结果展示给学生确认（用文字列出：类型、标题、日期、等级、主办方等）
3. 学生确认后调用 confirm_growth_record 保存到数据库
4. 日期默认使用今天的日期（{date.today().isoformat()}），如果材料中有明确日期则使用材料日期

## 项目对话
项目类型对话时，你作为项目经理引导用户推进阶段任务，完成时更新阶段并记录成果。

## 规则
- 请假/获奖/失物招领立即调用对应工具，不要让学生去其他页面
- 回答简洁，控制在150字以内
- 信息模糊时反问补充，确认后再执行
- 请假类型映射：比赛/竞赛→competition，生病→sick，事假/个人→personal，其他→other
- 回答使用纯文本，避免 Markdown 标记（#、列表、代码块等），需要强调重点时可用 **加粗**
- 不知道的说"我需要向老师确认后回答你" """
    else:
        return f"""你是绵阳城市学院的智慧校园AI助手"绵小城"，{greeting}{college}的教学管理助手。

## 能力
1. 请假审批 → query_pending_leaves / approve_leave
2. 学生管理 → query_students / query_student_detail
3. 危机预警 → query_crisis_alerts
4. 成长统计 → query_growth_stats
5. 请假AI分析 → analyze_leave
6. 校园知识 → query_knowledge
7. 通知 → query_announcements

## 规则
- 审批操作前向教师确认，避免误操作
- 回答简洁专业，控制在200字以内
- 教师说"分析这个请假" → 用 analyze_leave 进行AI分析
- 回答使用纯文本，避免 Markdown 标记（#、列表、代码块等），需要强调重点时可用 **加粗**
- 不知道的说"我需要确认后回答你" """


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
    url = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    headers = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        body = resp.json()
        out = body.get("output") or body
        return (out.get("text") or (out.get("sentence") or {}).get("text") or "").strip()
    except Exception as e:
        raise RuntimeError(f"语音识别失败: {e}")


_IMAGE_RECOGNIZE_PROMPT = """请识别这张图片，用于校园失物招领与成长档案场景。只依据图片中真实可见的内容作答，不要编造。

以严格 JSON 返回（不要额外文字、不要代码块标记）：
{
  "is_document": false,
  "category": "",
  "name": "",
  "color": "",
  "brand": "",
  "features": "",
  "document_type": "",
  "document_title": "",
  "description": ""
}

字段说明：
- is_document: 是否为证书/奖状/成绩单/证明类文档
- category: 物品大类，如 水杯/钱包/耳机/钥匙/雨伞/校园卡/书包/充电器/证书/其他
- name: 一句话物品名称，含颜色等关键特征，如"黑色保温杯"
- features: 显著外观特征、磨损、挂件、内含物等
- document_type: 仅当 is_document 为 true 时填写（荣誉证书/竞赛获奖/成绩单/其他证明）
- document_title: 仅当 is_document 为 true 时尽量提取标题原文
- description: 50 字以内综合描述"""


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

    prompt = _IMAGE_RECOGNIZE_PROMPT
    if hint:
        prompt += f"\n\n用户附带的说明（可作为判断线索）：{hint[:300]}"

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
