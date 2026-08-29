import json
import base64
import logging
import httpx
from fastapi import WebSocket

from app.services.llm_service import _get_client, _get_llm_config, build_system_prompt
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


async def dashscope_stt(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """调用 DashScope 语音识别 API"""
    config = _get_llm_config()
    if not config["api_key"]:
        raise RuntimeError("LLM 未配置 API Key")

    url = f"{config['base_url'].rstrip('/')}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    files = {"file": (filename, audio_bytes, "audio/webm")}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, files=files)
        resp.raise_for_status()
        return resp.json().get("text", "")


async def dashscope_tts(text: str):
    """调用 DashScope CosyVoice TTS，yield 音频块（PCM 16kHz 16bit mono）"""
    config = _get_llm_config()
    if not config["api_key"]:
        raise RuntimeError("LLM 未配置 API Key")

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
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

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(4096):
                if chunk:
                    yield chunk


async def handle_voice_connection(
    websocket: WebSocket,
    user: User,
    conversation_id: int | None,
):
    """语音通话主循环：接收音频 → STT → LLM → TTS → 回传"""
    audio_buffer = bytearray()
    history: list[dict] = []

    # 如果有 conversation_id，加载历史消息
    if conversation_id:
        db = SessionLocal()
        try:
            msgs = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.id)
                .all()
            )
            for m in msgs:
                history.append({"role": m.role, "content": m.content})
        finally:
            db.close()

    system_prompt = build_system_prompt(user)

    try:
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
                await websocket.send_json({"type": "state", "state": "processing"})
                try:
                    text = await dashscope_stt(bytes(audio_buffer))
                except Exception as e:
                    logger.exception("STT 失败")
                    await websocket.send_json({"type": "error", "message": f"语音识别失败: {e}"})
                    await websocket.send_json({"type": "state", "state": "listening"})
                    audio_buffer.clear()
                    continue
                finally:
                    audio_buffer.clear()

                if not text or not text.strip():
                    await websocket.send_json({"type": "state", "state": "listening"})
                    continue

                await websocket.send_json({"type": "transcript", "text": text, "final": True})

                # 2. LLM
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history[-10:])  # 最近 10 条历史
                messages.append({"role": "user", "content": text})

                full_response = ""
                try:
                    async for chunk in _get_client().chat.completions.create(
                        model=_get_llm_config()["model"],
                        messages=messages,
                        stream=True,
                        temperature=0.7,
                        max_tokens=1024,
                    ):
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            full_response += delta.content
                            await websocket.send_json({"type": "ai_text", "text": delta.content})
                except Exception as e:
                    logger.exception("LLM 失败")
                    await websocket.send_json({"type": "error", "message": "AI 回复失败"})
                    await websocket.send_json({"type": "state", "state": "listening"})
                    continue

                # 3. TTS
                await websocket.send_json({"type": "state", "state": "speaking"})
                try:
                    async for audio_chunk in dashscope_tts(full_response):
                        await websocket.send_json({
                            "type": "ai_audio",
                            "data": base64.b64encode(audio_chunk).decode(),
                        })
                except Exception as e:
                    logger.exception("TTS 失败")
                    # TTS 失败不阻断，文字已发送

                # 保存对话历史
                history.append({"role": "user", "content": text})
                history.append({"role": "assistant", "content": full_response})

                # 保存到数据库
                if conversation_id:
                    db = SessionLocal()
                    try:
                        db.add(ConversationMessage(conversation_id=conversation_id, role="user", content=text))
                        db.add(ConversationMessage(conversation_id=conversation_id, role="assistant", content=full_response))
                        db.commit()
                    except Exception:
                        db.rollback()
                        logger.exception("保存语音对话消息失败")
                    finally:
                        db.close()

                await websocket.send_json({"type": "state", "state": "listening"})

            elif msg["type"] == "ping":
                await websocket.send_json({"type": "pong"})

    except Exception as e:
        logger.info(f"语音连接关闭: {e}")
