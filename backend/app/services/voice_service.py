import asyncio
import io
import json
import re
import sys
import time
import wave
import base64
import logging
import httpx
from pathlib import Path
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

# 原生语音接口根地址：跟随 .env 的 LLM_BASE_URL 推导（TTS/ASR/多模态同域名）
TOKEN_PLAN_BASE = settings.llm_native_base
VOICE_STT_URL = f"{TOKEN_PLAN_BASE}/api/v1/services/aigc/multimodal-generation/generation"
VOICE_STT_MODEL = "qwen-audio-3.0-asr-flash"
VOICE_TTS_URL = f"{TOKEN_PLAN_BASE}/api/v1/services/audio/tts/SpeechSynthesizer"
# 语音合成模型：默认 flash（实测当前 Key 可用，返回 pcm 16kHz）。若所用套餐不包含
# flash（历史上 Token Plan 白名单只放 plus），调用会返回 404 Model not exist，
# 此时在系统设置中改用 plus，或把这里改回 qwen-audio-3.0-tts-plus。
VOICE_TTS_MODEL = "qwen-audio-3.0-tts-flash"
VOICE_TTS_VOICE = "longanhuan_v3.6"

# ===================== TTS 引擎（开源豆包方案：Edge TTS 多音色 + 千问原生 TTS 备选） =====================
# Edge TTS（微软免费服务，无需 API Key，400+ 音色，其中中文普通话/粤语/
# 台湾国语/东北、陕西口音共 14 个），作为默认语音合成引擎，解决多音色与
# “语音播报没有声音”（套餐模型受限/不稳定）两大问题；管理端仍可切换到
# 千问原生 TTS（qwen-audio-3.0-tts-flash，精品中文音色，见 VOICE_TTS_MODEL）。
EDGE_TTS_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

# 中文音色静态兜底列表（在线 list_voices 获取失败时使用，与在线列表同源）
EDGE_TTS_ZH_VOICES = [
    {"voice": "zh-CN-XiaoxiaoNeural", "label": "晓晓", "gender": "女", "tag": "普通话·温暖亲切"},
    {"voice": "zh-CN-XiaoyiNeural", "label": "晓伊", "gender": "女", "tag": "普通话·活泼友善"},
    {"voice": "zh-CN-YunjianNeural", "label": "云健", "gender": "男", "tag": "普通话·沉稳有力"},
    {"voice": "zh-CN-YunxiNeural", "label": "云希", "gender": "男", "tag": "普通话·阳光少年"},
    {"voice": "zh-CN-YunxiaNeural", "label": "云夏", "gender": "男", "tag": "普通话·明朗大方"},
    {"voice": "zh-CN-YunyangNeural", "label": "云扬", "gender": "男", "tag": "普通话·专业新闻"},
    {"voice": "zh-CN-liaoning-XiaobeiNeural", "label": "晓贝", "gender": "女", "tag": "东北话·爽朗有趣"},
    {"voice": "zh-CN-shaanxi-XiaoniNeural", "label": "晓妮", "gender": "女", "tag": "陕西话·质朴幽默"},
    {"voice": "zh-HK-HiuGaaiNeural", "label": "曉佳", "gender": "女", "tag": "粤语·亲切"},
    {"voice": "zh-HK-HiuMaanNeural", "label": "曉曼", "gender": "女", "tag": "粤语·温柔"},
    {"voice": "zh-HK-WanLungNeural", "label": "雲龍", "gender": "男", "tag": "粤语·沉稳"},
    {"voice": "zh-TW-HsiaoChenNeural", "label": "曉臻", "gender": "女", "tag": "台湾国语·自然"},
    {"voice": "zh-TW-HsiaoYuNeural", "label": "曉雨", "gender": "女", "tag": "台湾国语·活泼"},
    {"voice": "zh-TW-YunJheNeural", "label": "雲哲", "gender": "男", "tag": "台湾国语·沉稳"},
]

_EDGE_VOICES_CACHE: list[dict] | None = None
_EDGE_VOICES_FETCH_AT = 0.0
_EDGE_VOICES_TTL = 3600.0
_EDGE_VOICES_LOCK = asyncio.Lock()


def _ensure_vendor_on_path() -> None:
    """确保 vendor_packages（内置 edge_tts/sherpa_onnx 等）位于导入路径。

    main.py 仅在 jieba 缺失时才注入 vendor 目录；本机若已装 jieba，
    edge_tts 将不可见，因此这里显式兜底注入（幂等，重复插入无害）。
    """
    vendor = Path(__file__).resolve().parent.parent.parent / "vendor_packages"
    if str(vendor) not in sys.path and vendor.is_dir():
        sys.path.insert(0, str(vendor))


def is_edge_voice(voice: str) -> bool:
    """判断音色是否属于 Edge TTS：edge 音色以 Neural 结尾（如 zh-CN-XiaoxiaoNeural）；
    Token Plan 音色形如 longanhuan_v3.6 / longanlingxi"""
    return bool(voice and voice.strip().lower().endswith("neural"))


def _fmt_edge_locale(locale: str) -> str:
    """地区代码 -> 中文语言标签"""
    loc = (locale or "").lower()
    if loc.startswith("zh-hk"):
        return "粤语"
    if loc.startswith("zh-tw"):
        return "台湾国语"
    if "liaoning" in loc:
        return "东北话"
    if "shaanxi" in loc:
        return "陕西话"
    if loc.startswith("zh"):
        return "普通话"
    return locale or "中文"


async def get_edge_voices(force_refresh: bool = False) -> list[dict]:
    """获取 Edge TTS 可用中文音色：优先在线实时列表（缓存 1 小时），失败回退内置兜底列表"""
    global _EDGE_VOICES_CACHE, _EDGE_VOICES_FETCH_AT
    now = time.time()
    if (not force_refresh and _EDGE_VOICES_CACHE is not None
            and now - _EDGE_VOICES_FETCH_AT < _EDGE_VOICES_TTL):
        return _EDGE_VOICES_CACHE

    async with _EDGE_VOICES_LOCK:
        if (not force_refresh and _EDGE_VOICES_CACHE is not None
                and time.time() - _EDGE_VOICES_FETCH_AT < _EDGE_VOICES_TTL):
            return _EDGE_VOICES_CACHE
        try:
            _ensure_vendor_on_path()
            from edge_tts import list_voices
            raw = await list_voices()
            builtin = {v["voice"]: v for v in EDGE_TTS_ZH_VOICES}
            result: list[dict] = []
            for v in raw:
                short = v.get("ShortName") or ""
                if not short.lower().startswith("zh"):
                    continue
                gender = (v.get("Gender") or "?").lower()
                gender_cn = "女" if gender == "female" else ("男" if gender == "male" else gender)
                old = builtin.get(short)
                label = old["label"] if old else (v.get("FriendlyName") or short)
                tag = old["tag"] if old else _fmt_edge_locale(v.get("Locale") or "")
                result.append({"voice": short, "label": label, "gender": gender_cn, "tag": tag})
            if result:
                _EDGE_VOICES_CACHE = result
                _EDGE_VOICES_FETCH_AT = time.time()
                return result
        except Exception:
            logger.exception("Edge TTS 音色列表在线获取失败，回退内置兜底列表")
    return list(EDGE_TTS_ZH_VOICES)


def _get_tts_voice() -> str:
    """获取语音合成音色：优先系统设置 llm_tts_voice，其次 .env LLM_TTS_VOICE，
    最后默认 Edge 音色晓晓（免费多音色引擎，无需 API Key）"""
    try:
        db = SessionLocal()
        try:
            row = db.query(SystemSetting).filter(SystemSetting.key == "llm_tts_voice").first()
            if row and row.value and row.value.strip():
                return row.value.strip()
        finally:
            db.close()
    except Exception:
        logger.exception("读取语音音色设置失败")
    return settings.LLM_TTS_VOICE or EDGE_TTS_DEFAULT_VOICE


def _get_tts_prompt() -> str:
    """获取语音播报风格提示词：优先系统设置 llm_tts_prompt，其次 .env LLM_TTS_PROMPT

    作用于语音通话链路中的大模型回复风格（让回答更口语化、简短、适合语音播报），
    而非 TTS 合成参数（qwen-audio-3.0-tts-plus 作为 TTS 参数时的 instructions 不在此设置）。
    """
    try:
        db = SessionLocal()
        try:
            row = db.query(SystemSetting).filter(SystemSetting.key == "llm_tts_prompt").first()
            if row and row.value and row.value.strip():
                return row.value.strip()
        finally:
            db.close()
    except Exception:
        logger.exception("读取语音提示词设置失败")
    return (settings.LLM_TTS_PROMPT or "").strip()


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
    """从流式文本缓冲中切出可立即合成的自然语句，返回 (语句列表, 剩余缓冲)。

    语音播报按"完整语句"一段一段地合成，杜绝按字数硬切成 4~6 字碎块——
    碎块每段都要独立发起一次 TTS 请求，段间合成耗时+网络往返叠加成
    不可控的随机停顿（移动端弱网尤其明显）。句子级切分规则：

    - 句末标点（。！？!?；;\n…）处必切：一句一合成，句尾标点自带
      自然停顿，听感连贯；
    - 逗号/顿号是软切分点，仅在两种情况下使用：
        * 首段（first_early=True）累积满 EARLY_LEN：首音不必等整句，
          尽早送达（约 3 秒语音，不会碎）；
        * 任意段累积超过 MAX_SENT_LEN：长句降级分段，避免单次合成
          时间过长拖慢整段播报；
    - 无任何标点可依的超长串，按 MAX_SENT_LEN 硬切兜底。
    """
    EARLY_LEN = 14     # 首段早出音阈值（约 3 秒语音）
    MAX_SENT_LEN = 36  # 长句阈值（约 8 秒语音），超过后找逗号/兜底切分
    phrases: list[str] = []
    start = 0
    for i, ch in enumerate(buffer):
        if ch in "。！？!?；;\n…":
            if i == start and phrases:
                # 连续标点（如省略号"……"、叠加"？！"）：并入上一块末尾并跳过，
                # 避免切出孤立标点块，也避免残留缓冲中出现重复标点
                phrases[-1] += ch
                start = i + 1
            else:
                phrases.append(buffer[start:i + 1])
                start = i + 1
        elif ch in "，、,":
            length = i - start
            if (first_early and length >= EARLY_LEN) or (not first_early and length >= MAX_SENT_LEN):
                phrases.append(buffer[start:i + 1])
                start = i + 1
        elif i - start >= MAX_SENT_LEN:
            # 兜底：极长无标点串按上限硬切，宁可切也不无限等待
            phrases.append(buffer[start:i + 1])
            start = i + 1
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


async def tokenplan_tts(text: str, client: httpx.AsyncClient | None = None, voice: str | None = None):
    """调用千问原生 TTS（VOICE_TTS_MODEL，默认 qwen-audio-3.0-tts-flash），
    流式下载音频文件，yield PCM 16kHz 16bit mono 分块（边下载边产出，首块尽早送达）。
    voice 参数可临时覆盖当前生效音色（如管理端试听）。"""
    api_key = _get_voice_api_key()
    if not api_key:
        raise RuntimeError("语音合成未配置 API Key")

    payload = {
        "model": VOICE_TTS_MODEL,
        "input": {
            "text": text,
            "voice": voice or _get_tts_voice(),
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


async def edge_tts_tts(
    text: str,
    voice: str | None = None,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
):
    """Edge TTS（微软免费）语音合成：MP3(24kHz) -> 解码 -> 重采样 16kHz -> PCM16 分块

    与 tokenplan_tts 输出格式一致（16kHz 16bit 单声道裸 PCM），供流式播报链路直接使用；
    无需 API Key，支持 400+ 音色，是“开源豆包”方案的主合成引擎。
    """
    import numpy as np
    import soundfile as sf
    _ensure_vendor_on_path()
    from edge_tts import Communicate

    voice = voice or _get_tts_voice()
    max_retries = 4
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        mp3_buf = io.BytesIO()
        communicate = Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_buf.write(chunk["data"])
            if mp3_buf.getbuffer().nbytes > 0:
                break  # 合成成功
            last_exc = RuntimeError("微软未返回音频（疑似瞬时限流）")
        except Exception as exc:
            last_exc = exc
        if attempt < max_retries:
            # 微软对高频新连接有限流窗口，快速重试会撞在同一窗口内；
            # 按 1s/2s/4s 退避，等待限流窗口过期
            backoff = float(2 ** (attempt - 1))
            logger.warning(
                "Edge TTS 第 %s/%s 次合成失败 voice=%s: %s；%.0fs 后重试",
                attempt, max_retries, voice, last_exc, backoff,
            )
            await asyncio.sleep(backoff)
    else:
        raise RuntimeError(
            f"Edge TTS 合成失败 voice={voice}（已自动重试 {max_retries} 次）: {last_exc}"
        ) from last_exc

    mp3_buf.seek(0)

    data, sr = sf.read(mp3_buf, dtype="int16")
    if data.ndim > 1:
        data = data[:, 0] if data.shape[1] <= 1 else data.mean(axis=1)
    data = np.ascontiguousarray(data.ravel(), dtype=np.int16)
    if sr != 16000:
        # 线性插值重采样（24k -> 16k：每 3 点取 2 点）
        ratio = sr / 16000
        x_old = np.arange(len(data), dtype=np.float64)
        x_new = np.arange(int(len(data) / ratio), dtype=np.float64) * ratio
        data = np.interp(x_new, x_old, data.astype(np.float64)).astype(np.int16)
    yield data.tobytes()


async def synthesize_speech(text: str, voice: str | None = None):
    """统一语音合成入口（开源豆包方案）：

    - 音色为 Edge 风格（以 Neural 结尾）→ Edge TTS（免费多音色，默认引擎）
      内部自动重试 4 次（1/2/4s 退避），仍失败则自动降级原生 TTS 保证有声音
    - 其余音色（longan 系列等）→ 千问原生 TTS（VOICE_TTS_MODEL，默认 qwen-audio-3.0-tts-flash）
    yield：16kHz 16bit 单声道 PCM 分块
    """
    chosen = (voice or _get_tts_voice() or "").strip()
    if is_edge_voice(chosen):
        try:
            async for chunk in edge_tts_tts(text, voice=chosen):
                yield chunk
            return
        except Exception as exc:
            logger.error("Edge TTS 连续失败，自动降级 Token Plan（voice=%s）: %s", chosen, exc)
            fallback = _get_tts_voice()
            if is_edge_voice(fallback):
                fallback = ""  # 兜底音色本身也是 edge 时置空，交给 tokenplan 默认
        # 降级：走 Token Plan 精品音色，保证播报/试听始终有声音
        async for chunk in tokenplan_tts(text, voice=fallback or None):
            yield chunk
    else:
        async for chunk in tokenplan_tts(text, voice=chosen or None):
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

        # 语音播报风格提示词：叠加到系统提示词，使回复适合语音合成播报
        voice_prompt = _get_tts_prompt()
        if voice_prompt:
            system_prompt = (
                f"{system_prompt}\n\n【语音播报风格要求】{voice_prompt}\n"
                "请遵循以上风格要求回复，并在表达时尽量口语化、简短，便于语音合成朗读。"
            )

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
                keywords = detect_crisis_keywords(text, db)
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
                        async for chunk in synthesize_speech(phrase):
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
                        # 语句级切分：产出即合成，实现"早开场"（不等完整回答）；
                        # 整句归段、首段 14 字早出音，杜绝碎块化造成的随机停顿
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
