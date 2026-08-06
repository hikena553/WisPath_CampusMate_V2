import logging
import httpx
from datetime import date
from openai import AsyncOpenAI, APIError

from app.core.config import settings
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
                'llm_agent_model', 'llm_agent_temperature', 'llm_agent_max_tokens'
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
        if key in db_settings:
            v = db_settings[key]
            if v:
                return v
            return default
        return env_fallback or default

    return {
        'api_key': _val('llm_api_key', settings.llm_api_key),
        'base_url': _val('llm_base_url', settings.LLM_BASE_URL),
        'model': _val('llm_model', settings.LLM_MODEL, "qwen-turbo"),
        'agent_model': _val('llm_agent_model', settings.LLM_AGENT_MODEL),
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
        _client_instance = AsyncOpenAI(api_key=config['api_key'], base_url=config['base_url'])
        _client_config_hash = config_hash
    return _client_instance


def build_system_prompt(user: User | None = None, deep_think: bool = False) -> str:
    role_name = {"student": "同学", "teacher": "老师", "admin": "管理员"}
    greeting = role_name.get(user.role.value, "同学") if user else "同学"
    college = f"，来自{user.college}" if user and user.college else ""

    deep_think_instruction = ""
    if deep_think:
        deep_think_instruction = """
## 深度思考模式
请先进行推理思考，再用 ##思考过程 和 ##回答 两个部分输出。
- ##思考过程：分析用户问题，逐步推理，考虑各种可能性
- ##回答：给出最终答案
思考过程要详细、有逻辑，回答要简洁直接。"""

    if user and user.role == UserRole.STUDENT:
        return f"""你是绵阳城市学院的智慧校园AI助手"绵小城"，{greeting}{college}的校园智能管家。

## 能力
1. 请假 → create_leave | 2. 成长档案 → create_growth_record + confirm_growth_record | 3. 办事申请 → submit_service_request
4. 查课表 → query_schedule | 5. 查成绩 → query_grades | 6. 查考试 → query_exams
7. 查知识 → query_knowledge | 8. 查风景 → query_sceneries | 9. 查通知 → query_announcements
10. 成绩分析 → analyze_grades | 11. 课表分析 → analyze_schedule | 12. 成长分析 → analyze_growth

## 上传文件与成长记录
消息含 [用户上传了证明材料: URL] 时：
1. 先调用 create_growth_record 提取信息（从材料中提取，提取不到的字段留空，不要编造）
2. 将提取结果展示给学生确认（用文字列出：类型、标题、日期、等级、主办方等）
3. 学生确认后调用 confirm_growth_record 保存到数据库
4. 日期默认使用今天的日期（{date.today().isoformat()}），如果材料中有明确日期则使用材料日期

## 项目对话
项目类型对话时，你作为项目经理引导用户推进阶段任务，完成时更新阶段并记录成果。

## 规则
- 请假/获奖立即调用对应工具，不要让学生去其他页面
- 回答简洁，控制在150字以内
- 信息模糊时反问补充，确认后再执行
- 请假类型映射：比赛/竞赛→competition，生病→sick，事假/个人→personal，其他→other
- 不知道的说"我需要向老师确认后回答你"{deep_think_instruction}"""
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
- 不知道的说"我需要确认后回答你"{deep_think_instruction}"""


def speech_to_text(audio_bytes: bytes, filename: str) -> str:
    config = _get_llm_config()
    if not config['api_key']:
        raise RuntimeError("LLM 未配置 API Key")
    url = f"{config['base_url'].rstrip('/')}/audio/transcriptions"
    files = {"file": (filename, audio_bytes, "audio/webm")}
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    try:
        resp = httpx.post(url, headers=headers, files=files, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("text", "")
    except Exception as e:
        raise RuntimeError(f"语音识别失败: {e}")


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
