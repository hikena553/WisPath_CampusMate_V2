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
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.crypto import decrypt_value

logger = logging.getLogger(__name__)

DASHSCOPE_STT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/transcriptions"
DASHSCOPE_STT_MODEL = "paraformer-realtime-v2"
DASHSCOPE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation"


def _get_dashscope_api_key() -> str:
    """获取 DashScope（阿里云百炼）语音 API Key：优先数据库设置，回退到 .env"""
    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter(SystemSetting.key == "dashscope_api_key").first()
        if row and row.value:
            decrypted = decrypt_value(row.value)
            if decrypted:
                return decrypted
    except Exception:
        logger.exception("读取 DashScope API Key 失败")
    finally:
        db.close()
    return settings.DASHSCOPE_API_KEY


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """将裸 PCM（16kHz 16bit mono）包装成 WAV，供语音识别接口使用"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


async def dashscope_stt(audio_bytes: bytes, client: httpx.AsyncClient | None = None) -> str:
    """调用 DashScope 语音识别 API（Paraformer）"""
    api_key = _get_dashscope_api_key()
    if not api_key:
        raise RuntimeError("语音识别未配置 DashScope API Key")

    headers = {"Authorization": f"Bearer {api_key}"}
    wav_bytes = pcm_to_wav(audio_bytes)
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {"model": DASHSCOPE_STT_MODEL}

    if client is not None:
        resp = await client.post(DASHSCOPE_STT_URL, headers=headers, data=data, files=files)
        resp.raise_for_status()
        return resp.json().get("text", "")
    else:
        async with httpx.AsyncClient(timeout=30) as owned_client:
            resp = await owned_client.post(DASHSCOPE_STT_URL, headers=headers, data=data, files=files)
            resp.raise_for_status()
            return resp.json().get("text", "")


async def dashscope_tts(text: str, client: httpx.AsyncClient | None = None):
    """调用 DashScope CosyVoice TTS，yield 音频块（PCM 16kHz 16bit mono）"""
    api_key = _get_dashscope_api_key()
    if not api_key:
        raise RuntimeError("语音合成未配置 DashScope API Key")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "cosyvoice-v2",
        "input": {"text": text},
        "parameters": {
            "voice": "longxiaochun",
            "format": "pcm",
            "sample_rate": 16000,
        },
    }

    if client is not None:
        async with client.stream("POST", DASHSCOPE_TTS_URL, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(4096):
                if chunk:
                    yield chunk
    else:
        tts_timeout = httpx.Timeout(connect=10, read=120, write=10, pool=10)
        async with httpx.AsyncClient(timeout=tts_timeout) as owned_client:
            async with owned_client.stream("POST", DASHSCOPE_TTS_URL, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(4096):
                    if chunk:
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


async def handle_voice_connection(
    websocket: WebSocket,
    user: User,
    conversation_id: int | None,
):
    """语音通话主循环：接收音频 -> STT -> LLM -> TTS -> 回传"""
    audio_buffer = bytearray()
    history: list[dict] = []

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

            elif msg["type"] == "end_of_speech":
                if len(audio_buffer) < 1000:
                    # 音频太短，忽略
                    audio_buffer.clear()
                    continue

                # 1. STT
                if not await safe_send_json(websocket, {"type": "state", "state": "processing"}):
                    break
                try:
                    text = await dashscope_stt(bytes(audio_buffer), client=http_client)
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

                # 2. LLM
                messages = [{"role": "system", "content": system_prompt}]
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
                    async for audio_chunk in dashscope_tts(full_response, client=http_client):
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
        try:
            await websocket.close()
        except Exception:
            pass
        await http_client.aclose()
        db.close()
