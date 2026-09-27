import io
import json
import wave
import base64
import logging
import httpx
from datetime import datetime, timezone
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.services.llm_service import _get_client, _get_llm_config, build_system_prompt
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage
from app.models.setting import SystemSetting
from app.models.emotion import EmotionRecord
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.crypto import decrypt_value
from app.services.crisis_service import detect_crisis_keywords

logger = logging.getLogger(__name__)

# 负面情绪标签：持续高频出现时触发心理关注上报
NEGATIVE_EMOTIONS = {"sad", "angry", "fearful", "disgusted"}
EMOTION_LABELS = {
    "neutral": "平静", "happy": "开心", "sad": "难过", "angry": "生气",
    "fearful": "害怕", "disgusted": "厌恶", "surprised": "惊讶",
}

TOKEN_PLAN_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com"
VOICE_STT_URL = f"{TOKEN_PLAN_BASE}/api/v1/services/aigc/multimodal-generation/generation"
VOICE_STT_MODEL = "qwen-audio-3.0-asr-flash"
VOICE_TTS_URL = f"{TOKEN_PLAN_BASE}/api/v1/services/audio/tts/SpeechSynthesizer"
VOICE_TTS_MODEL = "qwen-audio-3.0-tts-plus"
VOICE_TTS_VOICE = "longanhuan_v3.6"


def _get_voice_api_key() -> str:
    """获取语音 API Key：优先数据库 llm_api_key（Token Plan，加密存储），
    兼容旧键 dashscope_api_key，最后回退到 .env"""
    db = SessionLocal()
    try:
        for key_name in ("llm_api_key", "dashscope_api_key"):
            row = db.query(SystemSetting).filter(SystemSetting.key == key_name).first()
            if row and row.value:
                try:
                    decrypted = decrypt_value(row.value)
                except Exception:
                    decrypted = None
                if decrypted:
                    return decrypted
    except Exception:
        logger.exception("读取语音 API Key 失败")
    finally:
        db.close()
    return settings.LLM_API_KEY or settings.DASHSCOPE_API_KEY


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """将裸 PCM（16kHz 16bit mono）包装成 WAV，供语音识别接口使用"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


async def tokenplan_stt(audio_bytes: bytes, client: httpx.AsyncClient | None = None) -> str:
    """调用 Token Plan 语音识别（qwen-audio-3.0-asr-flash，多模态生成端点）"""
    api_key = _get_voice_api_key()
    if not api_key:
        raise RuntimeError("语音识别未配置 API Key")

    wav_bytes = pcm_to_wav(audio_bytes)
    data_uri = "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode()
    payload = {
        "model": VOICE_STT_MODEL,
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
        "parameters": {"format": "wav", "sample_rate": "16000"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def _do(cl: httpx.AsyncClient) -> str:
        resp = await cl.post(VOICE_STT_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"语音识别接口返回 {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        out = body.get("output") or body
        text = out.get("text") or (out.get("sentence") or {}).get("text") or ""
        return text.strip()

    if client is not None:
        return await _do(client)
    else:
        async with httpx.AsyncClient(timeout=60) as owned_client:
            return await _do(owned_client)


async def tokenplan_tts(text: str, client: httpx.AsyncClient | None = None):
    """调用 Token Plan 语音合成（qwen-audio-3.0-tts-plus），yield PCM 16kHz 16bit mono 分块"""
    api_key = _get_voice_api_key()
    if not api_key:
        raise RuntimeError("语音合成未配置 API Key")

    payload = {
        "model": VOICE_TTS_MODEL,
        "input": {
            "text": text,
            "voice": VOICE_TTS_VOICE,
            "format": "pcm",
            "sample_rate": 16000,
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def _fetch(cl: httpx.AsyncClient) -> bytes:
        resp = await cl.post(VOICE_TTS_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"语音合成接口返回 {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        audio_url = (body.get("output") or {}).get("audio", {}).get("url")
        if not audio_url:
            raise RuntimeError(f"语音合成响应缺少音频地址: {body}")
        audio_resp = await cl.get(audio_url)
        audio_resp.raise_for_status()
        return await audio_resp.aread()

    if client is not None:
        pcm = await _fetch(client)
    else:
        tts_timeout = httpx.Timeout(connect=10, read=120, write=10, pool=10)
        async with httpx.AsyncClient(timeout=tts_timeout) as owned_client:
            pcm = await _fetch(owned_client)

    # 分块输出，模拟流式，前端可边收边播
    chunk_size = 16384
    for i in range(0, len(pcm), chunk_size):
        yield pcm[i:i + chunk_size]


async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
    """安全地发送JSON消息，如果连接已关闭则返回False"""
    try:
        if websocket.client_state.CONNECTED:
            await websocket.send_json(data)
            return True
    except Exception:
        logger.debug("WebSocket发送失败，连接可能已关闭")
    return False


def _dominant_emotion(emotion_timeline: list[dict]) -> str | None:
    """取通话期间出现次数最多的情绪，用于结合情绪回应；无数据返回 None"""
    if not emotion_timeline:
        return None
    counts: dict[str, int] = {}
    for e in emotion_timeline:
        counts[e["emotion"]] = counts.get(e["emotion"], 0) + 1
    # 取最近 20 条内最高频情绪，避免整场偏置
    recent = emotion_timeline[-20:]
    recent_counts: dict[str, int] = {}
    for e in recent:
        recent_counts[e["emotion"]] = recent_counts.get(e["emotion"], 0) + 1
    if recent_counts:
        return max(recent_counts.items(), key=lambda x: x[1])[0]
    return max(counts.items(), key=lambda x: x[1])[0]


async def _report_emotional_care(
    db,
    user: User,
    text: str,
    keywords: list[str],
    dominant_emotion: str | None,
    negative_burst: bool,
):
    """AI 主动监测：命中危机词或持续负面情绪时，生成心理关注摘要并通知教师端

    复用现有危机机制（AIDialogSummary 表 + 教师端预警），driver 为语音通话中的
    视觉情绪模块与语音内容。
    """
    from app.models.crisis import AIDialogSummary
    from app.models.user import User, UserRole
    from app.models.notification import Notification

    emo_label = EMOTION_LABELS.get(dominant_emotion, dominant_emotion) if dominant_emotion else "未检测"
    if keywords:
        snippet = f"命中关键词：{', '.join(keywords)}；视觉情绪：{emo_label}"
        level = "moderate" if any(k in text for k in ("不想活", "自杀", "自残", "想死")) else "mild"
        summary_text = f"[语音视觉模块上报] 学生在通话中表达心理困扰：{snippet}"
    elif negative_burst:
        snippet = f"通话中持续出现负面情绪（{emo_label}）"
        level = "mild"
        summary_text = f"[语音视觉模块上报] 学生通话期间情绪低落：{snippet}"
    else:
        return

    try:
        record = AIDialogSummary(
            student_id=user.id,
            summary=summary_text,
            level=level,
            keywords_matched=",".join(keywords) if keywords else emo_label,
            raw_snippet=(text or "")[:200],
        )
        db.add(record)

        # 通知绑定教师端
        from app.models.user import User as _U
        tutor = db.query(_U).filter(_U.id == user.tutor_id).first() if user.tutor_id else None
        if tutor and tutor.role == UserRole.TEACHER:
            db.add(Notification(
                user_id=tutor.id,
                title=f"心理关注：{user.name}",
                content=summary_text,
                type="warning",
            ))
        db.commit()
        logger.info("语音通话心理关注已上报 student_id=%s level=%s", user.id, level)
    except Exception:
        db.rollback()
        logger.exception("语音情绪上报失败")


async def handle_voice_connection(
    websocket: WebSocket,
    user: User,
    conversation_id: int | None,
):
    """语音通话主循环：接收音频 -> STT -> LLM -> TTS -> 回传
    视觉模块：通话中接收前端人脸情绪，结合情绪回应并联动心理关注"""
    audio_buffer = bytearray()
    history: list[dict] = []

    # 通话期间记录的情绪时间线（emotion, confidence, ts）
    emotion_timeline: list[dict] = []

    # 单一数据库会话，贯穿整个连接生命周期
    db = SessionLocal()
    # 共享 HTTP 客户端，TTS 使用更长的超时
    tts_timeout = httpx.Timeout(connect=10, read=120, write=10, pool=10)
    http_client = httpx.AsyncClient(timeout=tts_timeout)

    try:
        # 如果有 conversation_id，加载历史消息
        if conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            ).first()
            if not conv:
                logger.warning(f"对话 {conversation_id} 不属于用户 {user.id}")
                conversation_id = None
            else:
                msgs = (
                    db.query(ConversationMessage)
                    .filter(ConversationMessage.conversation_id == conversation_id)
                    .order_by(ConversationMessage.id)
                    .all()
                )
                for m in msgs:
                    history.append({"role": m.role, "content": m.content})

        system_prompt = build_system_prompt(user)

        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "audio":
                # 累积音频数据
                audio_bytes = base64.b64decode(msg["data"])
                audio_buffer.extend(audio_bytes)

            elif msg["type"] == "emotion":
                # 视觉模块上报当前人脸情绪
                emo = msg.get("emotion")
                if emo and emo in EMOTION_LABELS:
                    emotion_timeline.append({
                        "emotion": emo,
                        "confidence": float(msg.get("confidence") or 0),
                        "ts": datetime.now(timezone.utc),
                    })
                    # 保留最近 200 条，防止内存膨胀
                    if len(emotion_timeline) > 200:
                        emotion_timeline = emotion_timeline[-200:]

            elif msg["type"] == "end_of_speech":
                if len(audio_buffer) < 1000:
                    # 音频太短，忽略
                    audio_buffer.clear()
                    continue

                # 1. STT
                if not await safe_send_json(websocket, {"type": "state", "state": "processing"}):
                    break
                try:
                    text = await tokenplan_stt(bytes(audio_buffer), client=http_client)
                except Exception as e:
                    logger.exception("STT 失败")
                    await safe_send_json(websocket, {"type": "error", "message": "语音识别失败，请重试"})
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    continue
                finally:
                    audio_buffer.clear()

                if not text or not text.strip():
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    continue

                await safe_send_json(websocket, {"type": "transcript", "text": text, "final": True})

                # 2. 结合情绪 + 心理关注：提取主导情绪并检测危机词
                dominant_emotion = _dominant_emotion(emotion_timeline)

                # 2.1 危机关键词上报（AI 主动监测，关键时刻上报教师端）
                keywords = detect_crisis_keywords(text)
                negative_burst = len([
                    e for e in emotion_timeline if e["emotion"] in NEGATIVE_EMOTIONS
                ]) >= 3
                if keywords or negative_burst:
                    await _report_emotional_care(
                        db, user, text, keywords,
                        dominant_emotion=dominant_emotion, negative_burst=negative_burst,
                    )

                # 2. LLM
                messages = [{"role": "system", "content": system_prompt}]
                if dominant_emotion:
                    messages.append({
                        "role": "system",
                        "content": f"视觉情绪模块检测到：学生当前情绪状态为【{EMOTION_LABELS.get(dominant_emotion, dominant_emotion)}】。"
                                   f"请感知并顺应学生的情绪状态，语气温暖、共情地回应；若学生情绪低落或紧张，请给予安抚与支持，"
                                   f"避免生硬说教。回答保持简洁。",
                    })
                messages.extend(history[-10:])  # 最近 10 条历史
                messages.append({"role": "user", "content": text})

                full_response = ""
                try:
                    stream = await _get_client().chat.completions.create(
                        model=_get_llm_config()["model"],
                        messages=messages,
                        stream=True,
                        temperature=0.7,
                        max_tokens=1024,
                    )
                    async for chunk in stream:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            full_response += delta.content
                            if not await safe_send_json(websocket, {"type": "ai_text", "text": delta.content}):
                                break
                except Exception as e:
                    logger.exception("LLM 失败")
                    await safe_send_json(websocket, {"type": "error", "message": "AI 回复失败"})
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    continue

                # 3. TTS
                await safe_send_json(websocket, {"type": "state", "state": "speaking"})
                try:
                    async for audio_chunk in tokenplan_tts(full_response, client=http_client):
                        if not await safe_send_json(websocket, {
                            "type": "ai_audio",
                            "data": base64.b64encode(audio_chunk).decode(),
                        }):
                            break
                except Exception as e:
                    logger.exception("TTS 失败")
                    # TTS 失败不阻断，文字已发送

                # 保存对话历史
                history.append({"role": "user", "content": text})
                history.append({"role": "assistant", "content": full_response})

                # 历史上限，防止内存无限增长
                if len(history) > 50:
                    history = history[-50:]

                # 保存到数据库（复用同一个 session）
                if conversation_id:
                    try:
                        db.add(ConversationMessage(conversation_id=conversation_id, role="user", content=text))
                        db.add(ConversationMessage(conversation_id=conversation_id, role="assistant", content=full_response))
                        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
                        if conv:
                            if conv.title == "新对话":
                                conv.title = text[:20] + ("…" if len(text) > 20 else "")
                            conv.updated_at = datetime.now(timezone.utc)
                        db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception("保存语音对话消息失败")

                await safe_send_json(websocket, {"type": "state", "state": "listening"})

            elif msg["type"] == "ping":
                await safe_send_json(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        logger.info("语音连接正常断开")
    except Exception:
        logger.exception("语音连接异常断开")
    finally:
        audio_buffer.clear()
        # 视觉情绪落库（情绪垃圾桶数据源）
        if emotion_timeline:
            try:
                for e in emotion_timeline:
                    db.add(EmotionRecord(
                        user_id=user.id,
                        emotion=e["emotion"],
                        confidence=e["confidence"],
                        source="voice_call",
                        conversation_id=conversation_id,
                    ))
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("情绪记录落库失败")
        try:
            await websocket.close()
        except Exception:
            pass
        await http_client.aclose()
        db.close()
