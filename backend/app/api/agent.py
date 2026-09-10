import json
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage
from app.schemas.agent import ChatRequest
from app.services.agent_service import chat, generate_reply
from app.services.llm_service import speech_to_text, _get_client, _get_llm_config, build_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat")
async def chat_api(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_id = req.conversation_id
    if req.skip_conversation:
        conv_id = None
    elif conv_id:
        conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
        if not conv:
            raise HTTPException(404, "对话不存在")
        db.add(ConversationMessage(conversation_id=conv_id, role="user", content=req.message))
        db.commit()
    else:
        conv = Conversation(user_id=user.id, title="新对话")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    async def generate():
        async for event in chat(req.message, req.history, user, conv_id=conv_id, file_url=req.file_url, deep_think=req.deep_think):
            if isinstance(event, dict):
                if event["type"] == "reasoning":
                    yield f"event: reasoning\ndata: {json.dumps(event['content'], ensure_ascii=False)}\n\n"
                elif event["type"] == "content":
                    yield f"event: content\ndata: {json.dumps(event['content'], ensure_ascii=False)}\n\n"
            else:
                # 兼容旧的 __SUGGESTIONS__ 格式
                if isinstance(event, str) and event.startswith("__SUGGESTIONS__:"):
                    suggestions_data = event[len("__SUGGESTIONS__:"):]
                    yield f"event: suggestions\ndata: {suggestions_data}\n\n"
                else:
                    yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


class AnalyzeRequest(BaseModel):
    prompt: str


@router.post("/analyze")
async def analyze_api(req: AnalyzeRequest, user: User = Depends(get_current_user)):
    return StreamingResponse(
        generate_reply(req.prompt, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/speech-to-text")
async def speech_to_text_api(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(400, "文件名为空")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"wav", "mp3", "webm", "ogg", "m4a"}
    if ext not in allowed:
        raise HTTPException(400, f"不支持的音频格式: {ext}，支持: {', '.join(allowed)}")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "音频文件不能超过 10MB")
    try:
        text = speech_to_text(content, file.filename)
        return {"text": text}
    except RuntimeError as e:
        raise HTTPException(502, str(e))


@router.get("/recommendations")
async def get_recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """根据用户历史对话生成推荐问题"""
    # 获取用户最近的对话消息
    recent_messages = (
        db.query(ConversationMessage)
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .filter(Conversation.user_id == user.id)
        .order_by(ConversationMessage.timestamp.desc())
        .limit(20)
        .all()
    )

    history_text = ""
    for msg in reversed(recent_messages):
        role = "用户" if msg.role == "user" else "助手"
        history_text += f"{role}: {msg.content[:200]}\n"

    # 如果没有历史对话，返回默认推荐
    if not history_text.strip():
        return {"recommendations": [
            "帮我查一下下周的课程安排",
            "我想看看这学期的成绩单",
            "最近有什么校园活动通知",
            "帮我记录一下获奖信息",
        ]}

    config = _get_llm_config()
    prompt = f"""根据以下用户的历史对话记录，生成4个用户可能接下来想问的推荐问题。

要求：
1. 问题控制在20字以内，自然口语化
2. 结合用户的历史兴趣和需求
3. 涵盖校园AI助手的主要功能（课表、成绩、请假、通知、考试、成长记录等）
4. 直接返回JSON数组格式，不要其他文字

历史对话记录：
{history_text}

返回格式示例：
["帮我查一下下周的课程安排", "我想看看这学期的成绩单", "最近有什么校园活动通知", "帮我记录一下获奖信息"]"""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        content = response.choices[0].message.content or ""
        # 提取JSON数组
        import re
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            recommendations = json.loads(match.group())
            # 确保返回4个
            if len(recommendations) >= 4:
                return {"recommendations": recommendations[:4]}
    except Exception as e:
        logger.error("生成推荐失败: %s", e)

    # 降级返回默认推荐
    return {"recommendations": [
        "查一下我的课表",
        "查一下我的成绩",
        "我需要请假",
        "查一下官网通知",
    ]}
