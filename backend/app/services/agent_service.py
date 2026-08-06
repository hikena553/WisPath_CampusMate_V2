import re
import json
import logging

from sqlalchemy import or_
from sqlalchemy.orm import Session
from openai import APIError

from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.knowledge import KnowledgeItem
from app.models.conversation import Conversation, ConversationMessage
from app.services.llm_service import build_system_prompt
from app.services.tool_registry import TOOL_DEFINITIONS, TEACHER_TOOL_DEFINITIONS, execute_tool
from app.services.crisis_service import detect_crisis_keywords, save_crisis_summary
from app.services.llm_service import _get_client, _get_llm_config

logger = logging.getLogger(__name__)


STUDENT_STRATEGIES = {
    "at_risk": {
        "style": "gentle_care",
        "tone": "温和鼓励",
        "max_questions": 1,
        "greeting_extra": "最近过得怎么样？有什么想聊聊的吗？",
        "rules": ["避免追问学业压力", "多关心情绪状态", "回复控制在100字以内"],
    },
    "high_performer": {
        "style": "challenge_growth",
        "tone": "积极引导",
        "max_questions": 3,
        "greeting_extra": "最近有没有参加什么有意思的比赛或项目？",
        "rules": ["推荐更高阶的挑战", "主动介绍竞赛/论文机会"],
    },
    "disengaged": {
        "style": "re_engage",
        "tone": "轻松友好",
        "max_questions": 1,
        "greeting_extra": "好久不见！最近有什么新鲜事吗？",
        "rules": ["从轻松话题切入", "避免追问近况", "多分享校园趣事"],
    },
    "normal": {
        "style": "standard",
        "tone": "标准",
        "max_questions": 2,
        "greeting_extra": "",
        "rules": [],
    },
}


class _SimpleFunction:
    def __init__(self, name="", arguments=""):
        self.name = name
        self.arguments = arguments


class _SimpleToolCall:
    def __init__(self, id="", function=None):
        self.id = id
        self.function = function or _SimpleFunction()


def select_conversation_strategy(profile) -> tuple[str, dict]:
    if profile is None:
        return "normal", STUDENT_STRATEGIES["normal"]
    if profile.psychological_risk > 60 or profile.overall_risk > 50:
        return "at_risk", STUDENT_STRATEGIES["at_risk"]
    if profile.academic_score > 75 and profile.engagement_score > 60:
        return "high_performer", STUDENT_STRATEGIES["high_performer"]
    if profile.engagement_score < 30:
        return "disengaged", STUDENT_STRATEGIES["disengaged"]
    return "normal", STUDENT_STRATEGIES["normal"]


def build_context(message: str, user: User, db: Session | None = None) -> str:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        from app.services.knowledge_service import search_knowledge
        results = search_knowledge(db, message, limit=5)
        if results:
            context = "相关校园知识：\n"
            for r in results:
                if r["type"] == "qa":
                    context += f"[{r['category']}] Q: {r['question']}\nA: {r['answer']}\n\n"
                elif r["type"] == "document":
                    context += f"[文档参考] {r['content']}\n\n"
            return context
        return ""
    finally:
        if close_db:
            db.close()


async def call_llm_with_tools(messages: list[dict], tools: list[dict]) -> tuple[str, list | None]:
    config = _get_llm_config()
    kwargs = {
        "model": config['model'],
        "messages": messages,
        "temperature": config['temperature'],
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    resp = await _get_client().chat.completions.create(**kwargs)
    msg = resp.choices[0].message
    if msg.tool_calls:
        return "", msg.tool_calls
    return msg.content or "", None


async def call_llm_stream(messages: list[dict], tools: list[dict] | None = None):
    """流式输出LLM响应，返回 ('chunk', 文本) 或 ('tool_calls', 列表) 或 ('done', 完整文本)。"""
    config = _get_llm_config()
    kwargs = {
        "model": config['model'],
        "messages": messages,
        "temperature": config['temperature'],
        "stream": True,
        "max_tokens": config.get('max_tokens', 4096),
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    try:
        response = await _get_client().chat.completions.create(**kwargs)
    except APIError as e:
        logger.error("LLM API error: %s", e)
        yield ("error", str(e))
        return

    content = ""
    tool_calls_buffer: dict[int, _SimpleToolCall] = {}

    async for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if not delta:
            continue

        if delta.content:
            content += delta.content
            yield ("chunk", delta.content)

        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_buffer:
                    tool_calls_buffer[idx] = _SimpleToolCall(id="", function=_SimpleFunction())
                if tc.id:
                    tool_calls_buffer[idx].id += tc.id
                if tc.function:
                    if tc.function.name:
                        tool_calls_buffer[idx].function.name += tc.function.name
                    if tc.function.arguments:
                        tool_calls_buffer[idx].function.arguments += tc.function.arguments

    if tool_calls_buffer:
        result_calls = []
        for idx in sorted(tool_calls_buffer.keys()):
            result_calls.append(tool_calls_buffer[idx])
        yield ("tool_calls", result_calls)
    else:
        yield ("done", content)


async def generate_reply(prompt: str, user: User):
    """简单流式回复，不涉及会话、工具或保存。"""
    config = _get_llm_config()
    msgs = [
        {"role": "system", "content": f"你是绵阳城市学院的智慧校园AI助手绵小城。请用中文简洁回答，控制在500字以内。"},
        {"role": "user", "content": prompt},
    ]
    try:
        response = await _get_client().chat.completions.create(
            model=config['model'], messages=msgs,
            temperature=0.5, max_tokens=2048, stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception:
        logger.exception("生成回复失败")
        yield "抱歉，分析暂时不可用，请稍后再试。"


async def chat(message: str, history: list[dict], user: User, conv_id: int | None = None, file_url: str | None = None, deep_think: bool = False):
    system_prompt = build_system_prompt(user, deep_think=deep_think)

    from app.services.student_profile_engine import get_latest_profile
    from app.services.conversation_memory import get_relevant_memories
    strategy_db = SessionLocal()
    try:
        profile = get_latest_profile(strategy_db, user.id)
        strategy_name, strategy = select_conversation_strategy(profile)
        strategy_notes = ""
        if strategy["rules"]:
            strategy_notes = "\n".join(f"- {r}" for r in strategy["rules"])
            strategy_notes = f"\n\n## 本次对话策略\n{strategy_notes}"
        memory_context = get_relevant_memories(strategy_db, user.id, message)
    finally:
        strategy_db.close()

    context = build_context(message, user)
    system_content = system_prompt
    if context:
        system_content += "\n\n参考以下校园知识回答：\n" + context
    if strategy_notes:
        system_content += strategy_notes
    if memory_context:
        system_content += f"\n\n关于该生的历史记忆：{memory_context}"

    messages = [{"role": "system", "content": system_content}]
    for h in history[-10:]:
        messages.append(h)
    user_content = message
    if file_url:
        user_content = f"[用户上传了证明材料: {file_url}]\n{message}"
    messages.append({"role": "user", "content": user_content})

    try:
        tools = TOOL_DEFINITIONS if user.role == UserRole.STUDENT else TEACHER_TOOL_DEFINITIONS
        full_reply = ""
        tool_calls_detected = None

        stream = call_llm_stream(messages, tools)
        async for event_type, data in stream:
            if event_type == "chunk":
                full_reply += data
                yield data
            elif event_type == "tool_calls":
                tool_calls_detected = data
                break
            elif event_type == "done":
                full_reply = data
            elif event_type == "error":
                yield "抱歉，我暂时无法回答，请稍后再试。"
                return

        if tool_calls_detected:
            for tc in tool_calls_detected:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}
                result = await execute_tool(fn_name, fn_args, user, conv_id=conv_id)
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": fn_name, "arguments": tc.function.arguments}}]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            full_reply = ""
            second_stream = call_llm_stream(messages, [])
            async for event_type2, data2 in second_stream:
                if event_type2 == "chunk":
                    full_reply += data2
                    yield data2
                elif event_type2 == "done":
                    full_reply = data2

        suggestions = _extract_suggestions(full_reply)
        if suggestions:
            yield f"\n__SUGGESTIONS__:{json.dumps(suggestions, ensure_ascii=False)}"

        keywords = detect_crisis_keywords(message)
        if keywords:
            crisis_db = SessionLocal()
            try:
                await save_crisis_summary(crisis_db, user.id, message, full_reply, keywords)
            except Exception:
                logger.exception("保存危机预警失败")
            finally:
                crisis_db.close()

        await _try_extract_skills(message, user)

    except Exception:
        logger.exception("AI对话处理异常")
        error_msg = "抱歉，我暂时无法回答，请稍后再试。你也可以联系辅导员获取帮助。"
        yield error_msg
        return


def _extract_suggestions(text: str) -> list[dict]:
    suggestions = []
    pattern = r'\[(.+?)\]\((.+?)\)'
    for match in re.finditer(pattern, text):
        suggestions.append({"text": match.group(1), "link": match.group(2)})
    return suggestions


async def _try_extract_skills(user_message: str, user: User):
    if user.role != UserRole.STUDENT:
        return
    skill_keywords = ["学", "考", "参加", "研究", "练习", "做", "开发", "写"]
    if not any(kw in user_message for kw in skill_keywords):
        return
    try:
        prompt = f"""从学生的发言中提取技能和兴趣信息。只提取明确提及的技能或兴趣。

学生发言：{user_message}

以JSON格式返回：
{{
    "skills": [{{"name": "技能名称", "context": "上下文"}}],
    "interests": ["兴趣1", "兴趣2"]
}}
如果没有提取到，返回 {{"skills": [], "interests": []}}"""

        config = _get_llm_config()
        resp = await _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        extracted = json.loads(content)

        db = SessionLocal()
        try:
            current_user = db.query(User).filter(User.id == user.id).first()
            if not current_user:
                return
            current = current_user.skills_json or {"skills": [], "interests": []}
            changed = False
            for s in extracted.get("skills", []):
                if not any(existing["name"] == s["name"] for existing in current["skills"]):
                    current["skills"].append(s)
                    changed = True
            for i in extracted.get("interests", []):
                if i not in current["interests"]:
                    current["interests"].append(i)
                    changed = True
            if changed:
                current_user.skills_json = current
                db.commit()
        finally:
            db.close()
    except Exception:
        logger.debug("技能提取失败", exc_info=True)


def _save_assistant_response(conv_id: int | None, reply: str, user_message: str, user: User):
    if not conv_id:
        return
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            return
        db.add(ConversationMessage(conversation_id=conv_id, role="assistant", content=reply))
        if conv.title == "新对话" and user_message:
            clean = user_message.replace("\n", " ").replace("\r", "").strip()
            title = clean[:20] + ("…" if len(clean) > 20 else "")
            conv.title = title
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()

        msg_count = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conv_id
        ).count()
        if msg_count > 0 and msg_count % 20 == 0:
            from app.services.conversation_memory import summarize_conversation
            import asyncio
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(summarize_conversation(db, conv_id))
            except RuntimeError:
                pass
    except Exception:
        logger.exception("保存助手回复失败")
    finally:
        db.close()
