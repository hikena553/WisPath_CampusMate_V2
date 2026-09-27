import asyncio
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
# flash 快模型：相比 plus 版首包延迟显著更低，音色兼容（longanhuan_v3.6）
VOICE_TTS_MODEL = "qwen-audio-3.0-tts-flash"
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


def _take_tts_phrases(buffer: str, first_early: bool = False) -> tuple[list[str], str]:
    """从流式文本缓冲中切出可立即合成的短语，返回 (短语列表, 剩余缓冲)。

    借鉴豆包/流式语音合成的"早出音"设计：不必等完整句子，
    - 句末标点（。！？!?；;\n…）处必切；
    - 首段（first_early=True）满 4 字即切，把首音前合成等待压到最小；
    - 后续每 6 字一切：粒度比 8 字更细，短语间首包空窗更小、播报更连贯，
      请求次数仍在可控范围。
    """
    phrases: list[str] = []
    start = 0
    min_len = 4 if first_early else 6
    for i, ch in enumerate(buffer):
        if ch in "。！？!?；;\n…":
            phrases.append(buffer[start:i + 1])
            start = i + 1
            min_len = 6
        elif i - start >= min_len:
            phrases.append(buffer[start:i + 1])
            start = i + 1
            min_len = 6
    return phrases, buffer[start:]


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
    """调用 Token Plan 语音合成（qwen-audio-3.0-tts-flash 快模型），
    流式下载音频文件，yield PCM 16kHz 16bit mono 分块（边下载边产出，首块尽早送达）"""
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

    async def _stream(cl: httpx.AsyncClient):
        resp = await cl.post(VOICE_TTS_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"语音合成接口返回 {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        audio_url = (body.get("output") or {}).get("audio", {}).get("url")
        if not audio_url:
            raise RuntimeError(f"语音合成响应缺少音频地址: {body}")
        # 流式下载：不等待整段音频下载完成，边收边产出
        async with cl.stream("GET", audio_url) as audio_resp:
            audio_resp.raise_for_status()
            async for chunk in audio_resp.aiter_bytes():
                yield chunk

    if client is not None:
        async for chunk in _stream(client):
            yield chunk
    else:
        tts_timeout = httpx.Timeout(connect=10, read=120, write=10, pool=10)
        async with httpx.AsyncClient(timeout=tts_timeout) as owned_client:
            async for chunk in _stream(owned_client):
                yield chunk


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
    """语音通话主循环：接收音频 -> STT -> LLM -> 流式句子TTS -> 回传
    视觉模块：通话中接收前端人脸情绪，结合情绪回应并联动心理关注
    打断机制：用户开口时前端发送 interrupt，置位 cancel_event，
    正在进行的生成/合成尽快终止，只保留最近一轮问答。"""
    audio_buffer = bytearray()
    history: list[dict] = []

    # 通话期间记录的情绪时间线（emotion, confidence, ts）
    emotion_timeline: list[dict] = []

    # 打断信号：用户开口时置位；新一轮 end_of_speech 开始时清除
    cancel_event = asyncio.Event()

    # 对话轮次处理任务：串行保证 history/DB 写入顺序
    round_task: asyncio.Task | None = None

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

        # ============================================================
        # 单轮对话处理：STT -> LLM 流式 -> 句子级 TTS 链（边说边出）
        # ============================================================
        async def process_round(audio_bytes: bytes) -> None:
            """处理一轮 语音->识别->对话->合成；全程监听打断信号 cancel_event"""
            interrupted_llm = False
            text = ""
            full_response = ""
            try:
                if not await safe_send_json(websocket, {"type": "state", "state": "processing"}):
                    return

                # 1. STT
                try:
                    text = await tokenplan_stt(audio_bytes, client=http_client)
                except Exception:
                    logger.exception("STT 失败")
                    await safe_send_json(websocket, {"type": "error", "message": "语音识别失败，请重试"})
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    return

                if cancel_event.is_set():
                    # 用户已开口打断本轮，丢弃识别结果
                    return
                if not text or not text.strip():
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    return

                await safe_send_json(websocket, {"type": "transcript", "text": text, "final": True})

                # 2. 情绪 + 心理关注上报
                dominant_emotion = _dominant_emotion(emotion_timeline)
                keywords = detect_crisis_keywords(text)
                negative_burst = len([
                    e for e in emotion_timeline if e["emotion"] in NEGATIVE_EMOTIONS
                ]) >= 3
                if keywords or negative_burst:
                    await _report_emotional_care(
                        db, user, text, keywords,
                        dominant_emotion=dominant_emotion, negative_burst=negative_burst,
                    )

                # 3. LLM 流式 + 句子级 TTS 链
                messages = [{"role": "system", "content": system_prompt}]
                if dominant_emotion:
                    messages.append({
                        "role": "system",
                        "content": f"视觉情绪模块检测到：学生当前情绪状态为【{EMOTION_LABELS.get(dominant_emotion, dominant_emotion)}】。"
                                   f"请感知并顺应学生的情绪状态，语气温暖、共情地回应；若学生情绪低落或紧张，请给予安抚与支持，"
                                   f"避免生硬说教。回答保持简洁。",
                    })
                messages.extend(history[-8:])  # 最近 8 条历史，控制 LLM 首字延迟
                messages.append({"role": "user", "content": text})

                sentence_buf = ""
                speaking_notified = False
                tts_chain: asyncio.Task | None = None

                async def _synth_to_queue(phrase: str, q: asyncio.Queue) -> None:
                    """独立合成一段短语：边产出边放入队列；结束/异常/被打断时放入 None 信号"""
                    try:
                        async for chunk in tokenplan_tts(phrase, client=http_client):
                            if cancel_event.is_set():
                                break
                            await q.put(chunk)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception("短语语音合成失败")
                    finally:
                        await q.put(None)

                def enqueue_tts(phrase: str) -> None:
                    """短语级流式 TTS：合成立即并发发起，发送严格按入队顺序链式执行。
                    每段音频边下载边发送（首块到达即播报，无需等整段下载完），
                    且多段合成时间重叠，整体播报显著提前"""
                    nonlocal tts_chain
                    prev = tts_chain
                    chunk_q: asyncio.Queue[bytes | None] = asyncio.Queue()
                    synth = asyncio.create_task(_synth_to_queue(phrase, chunk_q))

                    async def runner() -> None:
                        nonlocal speaking_notified
                        if prev is not None:
                            try:
                                await prev
                            except asyncio.CancelledError:
                                raise
                            except Exception:
                                pass
                        if cancel_event.is_set():
                            return
                        while True:
                            chunk = await chunk_q.get()
                            if chunk is None:
                                break
                            if cancel_event.is_set():
                                break
                            if not speaking_notified:
                                speaking_notified = True
                                await safe_send_json(websocket, {"type": "state", "state": "speaking"})
                            for i in range(0, len(chunk), 8192):
                                if cancel_event.is_set():
                                    break
                                if not await safe_send_json(websocket, {
                                    "type": "ai_audio",
                                    "data": base64.b64encode(chunk[i:i + 8192]).decode(),
                                }):
                                    break

                    tts_chain = asyncio.create_task(runner())

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
                        if not (delta and delta.content):
                            continue
                        if cancel_event.is_set():
                            # 用户开口打断：终止本轮生成，不保留半截回复
                            interrupted_llm = True
                            break
                        full_response += delta.content
                        sentence_buf += delta.content
                        if not await safe_send_json(websocket, {"type": "ai_text", "text": delta.content}):
                            break
                        # 短语级切分：产出即合成，实现"早开场"（不等完整句子）；
                        # 首段满 4 字即切，尽快合出第一段语音（其余段 8 字巡航）
                        phrases, sentence_buf = _take_tts_phrases(
                            sentence_buf, first_early=(tts_chain is None)
                        )
                        for p in phrases:
                            enqueue_tts(p)

                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("LLM 失败")
                    await safe_send_json(websocket, {"type": "error", "message": "AI 回复失败"})
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    return

                # 打断时：已入队的短语通过 runner 内的 cancel_event 检查跳过发送，
                # 合成任务自然结束，保证本轮历史/DB 正常收尾
                if not interrupted_llm and sentence_buf.strip():
                    enqueue_tts(sentence_buf)

                if tts_chain is not None:
                    try:
                        await tts_chain
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        pass

                # 4. 保存对话历史（被打断的轮次不保留半截回复）
                history.append({"role": "user", "content": text})
                if not interrupted_llm and full_response.strip():
                    history.append({"role": "assistant", "content": full_response})
                if len(history) > 50:
                    history[:] = history[-50:]

                if conversation_id:
                    try:
                        db.add(ConversationMessage(conversation_id=conversation_id, role="user", content=text))
                        if not interrupted_llm and full_response.strip():
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
            except Exception:
                logger.exception("语音处理轮次失败")

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

                payload = bytes(audio_buffer)
                audio_buffer.clear()

                # 上一轮（可能正被中断）先收尾，保证 history/DB 写入顺序
                if round_task is not None and not round_task.done():
                    try:
                        await round_task
                    except (Exception, asyncio.CancelledError):
                        pass
                cancel_event.clear()
                round_task = asyncio.create_task(process_round(payload))

            elif msg["type"] == "interrupt":
                # 用户开口：终止正在进行的生成与合成（只保留最近一轮回答）
                cancel_event.set()
                await safe_send_json(websocket, {"type": "state", "state": "listening"})

            elif msg["type"] == "mute":
                # 麦克风静音：丢弃已累积的音频，避免取消静音后识别到静音前残留
                if msg.get("muted"):
                    audio_buffer.clear()

            elif msg["type"] == "ping":
                await safe_send_json(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        logger.info("语音连接正常断开")
    except Exception:
        logger.exception("语音连接异常断开")
    finally:
        audio_buffer.clear()
        # 取消仍在进行的对话轮次，避免连接关闭后任务继续访问已关闭资源
        if round_task is not None and not round_task.done():
            round_task.cancel()
            try:
                await round_task
            except (Exception, asyncio.CancelledError):
                pass
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
