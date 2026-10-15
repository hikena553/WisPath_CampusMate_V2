import asyncio
import io
import json
import re
import sys
import time
import wave
import base64
import logging
import logging.handlers
import threading
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

# ===== 语音通话诊断日志 =====
# 单独落盘（backend/logs/voice-call.log），完整记录 STT 文本、逐段 TTS 结果、
# LLM 分片统计与异常，便于定位"播报中断 / 文字异常"等问题，可直接提供该文件排障。
_VOICE_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "logs" / "voice-call.log"


def _ensure_voice_file_log() -> None:
    """为 voice_service 挂专用滚动文件日志（幂等）。"""
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers):
        return
    try:
        _VOICE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            _VOICE_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)
    except Exception:
        logger.exception("语音诊断日志文件初始化失败（不影响功能）")


_ensure_voice_file_log()

# 负面情绪标签：持续高频出现时触发心理关注上报
NEGATIVE_EMOTIONS = {"sad", "angry", "fearful", "disgusted"}
# 接通问候时等待首帧表情的最长时长（秒）。
# 首帧表情需要"摄像头授权 + 模型加载 + 首帧推理"，1.6s 基本等不到，会导致
# 问候永远用不上表情（表现为"没结合我的表情"）。这里放宽到 6s；同时前端在
# 摄像头不可用时会立刻发 emotion_unavailable，让问候立即进行、不空等。
EMOTION_GREET_WAIT = 6.0
# Edge TTS 合成失败时的兜底音色（Token Plan 旗舰中文音色，需已配置 API Key）
FALLBACK_TOKENPLAN_VOICE = "longanlingxin"

# ===== Token Plan TTS 限流保护 =====
# 句子级流式会让多段合成"同时"发起（原设计为缩短首音），但 Token Plan 对 TTS
# 有 QPS 配额，无限并发会触发 429（Throttling.RateQuota），表现为
# "播报一小段后，剩余内容合成失败/没声音"。此处以全局信号量限流（同时保护
# 账号级配额），并对 429 做退避重试，保留"边生成边合成"的流式设计不变。
TTS_MAX_CONCURRENCY = 1      # 同时进行的合成请求数上限（=1 最稳，且仍快于实时播放）
TTS_MAX_RETRY = 3            # 429 限流时的最大重试次数
TTS_RETRY_BACKOFF_S = 1.2    # 429 重试退避基数（秒）

_TTS_SEMAPHORE: asyncio.Semaphore | None = None


def _tts_semaphore() -> asyncio.Semaphore:
    """惰性创建 TTS 并发信号量（避免导入期绑定事件循环）。"""
    global _TTS_SEMAPHORE
    if _TTS_SEMAPHORE is None:
        _TTS_SEMAPHORE = asyncio.Semaphore(TTS_MAX_CONCURRENCY)
    return _TTS_SEMAPHORE
# 一轮识别所需的最少音频（字节）：16kHz/16bit 单声道约 250ms，
# 过滤噪声毛刺触发的空识别（本地 SenseVoice 对纯静音易输出"没。"等幻觉）
MIN_SPEECH_BYTES = 8000

# Edge TTS 熔断：本机实测微软合成端点返回 403（网络/风控受限），
# 若每次都先撞 Edge 会明显拖慢首音；连续失败达阈值后进入冷却期，期间直连 Token Plan。
_EDGE_FAIL_COUNT = 0
_EDGE_COOLDOWN_UNTIL = 0.0
EDGE_FAIL_THRESHOLD = 1          # 连续失败次数达到该值即熔断
EDGE_COOLDOWN_SECONDS = 600.0    # 冷却时长（秒）
EMOTION_LABELS = {
    "neutral": "平静", "happy": "开心", "sad": "难过", "angry": "生气",
    "fearful": "害怕", "disgusted": "厌恶", "surprised": "惊讶",
}

TOKEN_PLAN_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com"
VOICE_STT_URL = f"{TOKEN_PLAN_BASE}/api/v1/services/aigc/multimodal-generation/generation"
VOICE_STT_MODEL = "qwen-audio-3.0-asr-flash"
VOICE_TTS_URL = f"{TOKEN_PLAN_BASE}/api/v1/services/audio/tts/SpeechSynthesizer"
# 默认 TTS 模型：仅在 voice 无法解析到所属模型时使用
# 大多数情况下按 VOICE_MODEL_CATALOG 自动选模型
VOICE_TTS_MODEL_DEFAULT = "qwen-audio-3.0-tts-plus"
# 默认音色（无设置时的兜底）：Edge 微软免费音色，无需 API Key
EDGE_TTS_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
VOICE_TTS_VOICE = EDGE_TTS_DEFAULT_VOICE

# ===== 阿里云百炼 Qwen-Audio-TTS 音色白名单（仅保留账号实测可用的音色） =====
# 来源：https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list
# 当前 Token Plan 账号仅开通 qwen-audio-3.0-tts-plus 模型，flash/3.1-flash
# 模型的音色全部返回 404 "Model not exist."，已全部下架不再下发。
# 多音色需求改由 Edge TTS（微软免费）承担，无需 API Key，详见 EDGE_TTS_ZH_VOICES。
#
# verified 字段：True 表示用户账号/套餐下实测可用。
VOICE_MODEL_CATALOG: dict[str, list[dict]] = {
    "qwen-audio-3.0-tts-plus": [
        # 社交陪伴（旗舰音色，账号实测通过）
        {"voice": "longanlingxin", "label": "龙安灵心", "gender": "女", "tag": "社交陪伴·知心温暖音", "verified": True},
        {"voice": "longanlufeng", "label": "龙安鲁风", "gender": "男", "tag": "社交陪伴·明亮开朗音", "verified": True},
    ],
    "qwen-audio-3.0-tts-flash": [],
    "qwen-audio-3.1-tts-flash": [],
}


def _voice_to_model(voice: str | None) -> str:
    """根据 voice ID 反查所属模型；找不到则用默认模型。"""
    v = (voice or "").strip()
    if not v:
        return VOICE_TTS_MODEL_DEFAULT
    for model, voices in VOICE_MODEL_CATALOG.items():
        for item in voices:
            if item["voice"] == v:
                return model
    return VOICE_TTS_MODEL_DEFAULT


# Token Plan 音色全集（含未实测）：所有可调用的 voice ID 集合
TOKENPLAN_ALLOWED_VOICES: set[str] = {
    item["voice"]
    for voices in VOICE_MODEL_CATALOG.values()
    for item in voices
}

# ===================== TTS 引擎（开源豆包方案：Edge TTS 多音色 + Token Plan 备选） =====================
# Edge TTS（微软免费服务，无需 API Key，400+ 音色，其中中文普通话/粤语/
# 台湾国语/东北、陕西口音共 14 个），作为默认语音合成引擎，解决多音色与
# “语音播报没有声音”（Token Plan 受限/不稳定）两大问题；管理端仍可切换到
# Token Plan（qwen-audio-3.0-tts-plus，精品中文音色）。

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


def is_valid_voice(voice: str | None) -> bool:
    """校验音色 ID 是否合法：是否在 VOICE_MODEL_CATALOG 全集中。

    所有官方支持的系统音色（plus / 3.0-flash / 3.1-flash）均接受，
    后端按 voice 归属自动选择模型调用。但**账号/套餐未实测通过的音色**
    仍可能在阿里云侧返回 4xx（如 411 TTS speak operation failed），
    因此调用失败时日志会完整记录真实响应，便于管理员定位可用品色。
    """
    v = (voice or "").strip()
    if not v:
        return False
    return v in TOKENPLAN_ALLOWED_VOICES


class InvalidVoiceError(ValueError):
    """音色不在官方系统音色全集中，供前端 400 渲染可定位文案"""

    def __init__(self, voice: str | None):
        self.voice = voice or ""
        super().__init__(
            f"音色 ID 不在阿里云官方系统音色列表中：{voice!r}。"
            "请从音色下拉中选择官方音色；未实测通过的音色可能触发 cosyvoice 4xx，"
            "建议先试听确认可用。"
        )


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
    return settings.LLM_TTS_VOICE or VOICE_TTS_VOICE


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


def _is_speakable(text: str) -> bool:
    """该片段是否值得送去合成。

    必须至少含一个字母/数字/汉字：纯空白（如段落换行 "\\n\\n"）或纯标点
    会被 TTS 接口拒（Token Plan 返回 400 InvalidParameter），
    导致该段没有声音（表现为"播报一段后中断"）。
    """
    return any(ch.isalnum() for ch in text)


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
                piece = buffer[start:i + 1]
                # 纯空白/纯标点段（典型：段落间的 "\n\n"）不送去合成，直接丢弃，
                # 否则 TTS 会因"空文本"返回 400，造成该段没有声音
                if _is_speakable(piece):
                    phrases.append(piece)
                start = i + 1
        elif ch in "，、,":
            length = i - start
            if (first_early and length >= EARLY_LEN) or (not first_early and length >= MAX_SENT_LEN):
                piece = buffer[start:i + 1]
                if _is_speakable(piece):
                    phrases.append(piece)
                start = i + 1
        elif i - start >= MAX_SENT_LEN:
            # 兜底：极长无标点串按上限硬切，宁可切也不无限等待
            piece = buffer[start:i + 1]
            if _is_speakable(piece):
                phrases.append(piece)
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
    """调用 Token Plan 语音合成，按 voice 自动选择对应模型（plus / 3.0-flash / 3.1-flash），
    流式下载音频文件，yield PCM 16kHz 16bit mono 分块。
    voice 参数可临时覆盖当前生效音色（如管理端试听）。"""
    api_key = _get_voice_api_key()
    if not api_key:
        raise RuntimeError("语音合成未配置 API Key")

    target_voice = (voice or _get_tts_voice() or "").strip()
    # 发送请求前校验 voice：不在 VOICE_MODEL_CATALOG 全集中的 voice 调用阿里云会触发
    # cosyvoice 4xx（如 411 TTS speak operation failed），此处拦截可避免无效请求
    if not is_valid_voice(target_voice):
        raise InvalidVoiceError(target_voice)

    # 按 voice 自动选择所属模型（避免跨模型调用导致 411）
    target_model = _voice_to_model(target_voice)

    payload = {
        "model": target_model,
        "input": {
            "text": text,
            "voice": target_voice,
            "format": "pcm",
            "sample_rate": 16000,
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def _request_audio_url(cl: httpx.AsyncClient) -> str:
        """申请合成并取回音频直链：带全局并发上限 + 429 限流退避重试。

        Token Plan 对 TTS 有 QPS 配额；句子级流式会同时发起多段合成，
        无限并发会触发 429（Throttling.RateQuota），症状即
        "播报一小段后，剩余内容无法合成"。这里用信号量限流 + 退避重试兜住，
        既保留"边生成边合成"的流式设计，又不撞配额。
        """
        last_body = ""
        for attempt in range(1, TTS_MAX_RETRY + 1):
            async with _tts_semaphore():
                resp = await cl.post(VOICE_TTS_URL, headers=headers, json=payload)
                if resp.status_code < 400:
                    body = resp.json()
                    audio_url = (body.get("output") or {}).get("audio", {}).get("url")
                    if audio_url:
                        return audio_url
                    raise RuntimeError(f"语音合成响应缺少音频地址: {body}")
                last_body = (resp.text or "")[:500]
                if resp.status_code != 429:
                    # 完整记录阿里云返回（含 request_id / code / message），便于定位
                    # 套餐白名单、voice 拼写错误、文本超限等真实原因
                    logger.error(
                        "Token Plan TTS 4xx: status=%s voice=%s model=%s body=%s",
                        resp.status_code, target_voice, target_model, last_body,
                    )
                    raise RuntimeError(f"语音合成接口返回 {resp.status_code}: {last_body}")
            # 429：限流。在信号量之外退避等待，避免占着并发额度空转
            wait = TTS_RETRY_BACKOFF_S * attempt
            logger.warning(
                "Token Plan TTS 触发限流 429（第 %s/%s 次）voice=%s，%.1fs 后重试",
                attempt, TTS_MAX_RETRY, target_voice, wait,
            )
            await asyncio.sleep(wait)
        raise RuntimeError(
            f"语音合成接口返回 429（触发限流，已重试 {TTS_MAX_RETRY} 次）: {last_body}"
        )

    async def _stream(cl: httpx.AsyncClient):
        audio_url = await _request_audio_url(cl)
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
    max_retries = 2
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
            # 403 / 握手失败通常是网络或风控拦截，重试无意义：立即放弃，
            # 交由上层熔断逻辑快速回退 Token Plan，避免首音被拖到十几秒
            if "403" in str(exc) or "Handshake" in type(exc).__name__:
                logger.warning("Edge TTS 被拒（%s），跳过重试", type(exc).__name__)
                break
        if attempt < max_retries:
            # 微软对高频新连接有限流窗口，快速重试会撞在同一窗口内；
            # 按 1s 退避，等待限流窗口过期
            backoff = float(2 ** (attempt - 1))
            logger.warning(
                "Edge TTS 第 %s/%s 次合成失败 voice=%s: %s；%.0fs 后重试",
                attempt, max_retries, voice, last_exc, backoff,
            )
            await asyncio.sleep(backoff)

    if mp3_buf.getbuffer().nbytes == 0:
        raise RuntimeError(
            f"Edge TTS 合成失败 voice={voice}（已尝试 {max_retries} 次）: {last_exc}"
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


# ===================== 本地语音识别（sherpa-onnx SenseVoice，低延迟首选） =====================
# 采用开源成熟的 sherpa-onnx（k2-fsa）离线识别器 + SenseVoice 多语种模型（随仓库内置于
# backend/models/sense-voice），在服务进程内 CPU 推理，免去云端 ASR 的一次网络往返，
# 是语音链路"首字延迟"优化的关键一环。识别失败 / 模型缺失时自动回退云端
# qwen-audio-3.0-asr-flash，保证功能全链路不中断。

_SENSEVOICE_RECOGNIZER = None
_SENSEVOICE_UNAVAILABLE = False
_SENSEVOICE_LOCK = threading.Lock()

# 问候语按表情状态的情绪关照提示（视觉模块 -> 通话开场语定制）
GREETING_EMOTION_HINT: dict[str, str] = {
    "happy": "请用轻快、分享喜悦的语气回应，可以顺着他的好心情聊开。",
    "sad": "请用温柔、安抚的语气，先接住他的情绪，不要急着说教。",
    "angry": "请保持平和包容，先让他平复，避免争辩或说教。",
    "fearful": "请给予安全感，语气坚定而温和，让他安心。",
    "disgusted": "请温和转移话题，不要强化不快的情绪。",
    "surprised": "请带着一点好奇自然地回应，顺着他的关注点聊聊。",
    "neutral": "按日常问候即可，语气亲切自然。",
}


def _get_local_recognizer():
    """懒加载本地 SenseVoice 识别器（进程内单例，线程安全）。

    模型目录：backend/models/sense-voice/{model.int8.onnx,tokens.txt}
    不可用时返回 None，并由调用方回退云端识别（只判定一次，避免反复失败拖慢链路）。
    """
    global _SENSEVOICE_RECOGNIZER, _SENSEVOICE_UNAVAILABLE
    if _SENSEVOICE_RECOGNIZER is not None:
        return _SENSEVOICE_RECOGNIZER
    if _SENSEVOICE_UNAVAILABLE:
        return None
    with _SENSEVOICE_LOCK:
        if _SENSEVOICE_RECOGNIZER is not None:
            return _SENSEVOICE_RECOGNIZER
        if _SENSEVOICE_UNAVAILABLE:
            return None
        try:
            _ensure_vendor_on_path()
            import sherpa_onnx
            model_dir = Path(__file__).resolve().parent.parent.parent / "models" / "sense-voice"
            model_path = model_dir / "model.int8.onnx"
            tokens_path = model_dir / "tokens.txt"
            if not model_path.is_file() or not tokens_path.is_file():
                logger.warning("本地 SenseVoice 模型缺失，改用云端 STT：%s", model_dir)
                _SENSEVOICE_UNAVAILABLE = True
                return None
            _SENSEVOICE_RECOGNIZER = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(model_path),
                tokens=str(tokens_path),
                num_threads=2,
                use_itn=True,
                language="zh",
                debug=False,
            )
            logger.info("本地 SenseVoice 识别器已加载：%s", model_path.name)
            return _SENSEVOICE_RECOGNIZER
        except Exception:
            logger.exception("本地 SenseVoice 加载失败，改用云端 STT")
            _SENSEVOICE_UNAVAILABLE = True
            return None


async def local_sensevoice_stt(audio_bytes: bytes) -> str:
    """本地 SenseVoice 识别：16kHz 16bit 单声道 PCM -> 文本。

    识别为同步 CPU 推理，放入线程池执行，避免阻塞事件循环影响其它连接；
    输出中的 <|lang|> / <|emotion|> 等特殊标记会被剥离。
    """
    import numpy as np

    recognizer = await asyncio.to_thread(_get_local_recognizer)
    if recognizer is None:
        raise RuntimeError("本地识别不可用")

    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return ""

    def _decode() -> str:
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        recognizer.decode_stream(stream)
        return getattr(stream.result, "text", "") or ""

    text = await asyncio.to_thread(_decode)
    # 剥离 SenseVoice 特殊标记（语言/情绪/事件/ITN 等 <|...|> 标记）
    return re.sub(r"<\|[^|]*\|>", "", text).strip()


async def synthesize_speech(text: str, voice: str | None = None):
    """统一语音合成入口：按 voice 自动选择引擎。

    - 以 Neural 结尾的 voice 走 Edge TTS（微软免费，多音色，无需 API Key）。
    - 其它 voice 走 Token Plan（阿里云百炼 qwen-audio-3.0-tts-plus 旗舰音色）。
    Edge TTS 不可用（网络受限 / 403 风控 / 缺少解码依赖）时，自动回退 Token Plan
    （若已配置 Key），避免"有文字没声音"。yield：16kHz 16bit 单声道 PCM 分块
    """
    global _EDGE_FAIL_COUNT, _EDGE_COOLDOWN_UNTIL
    chosen = (voice or _get_tts_voice() or EDGE_TTS_DEFAULT_VOICE).strip()
    if is_edge_voice(chosen):
        # 熔断冷却期内直接用 Token Plan，避免每次合成先撞 Edge 的超时/403
        if time.time() < _EDGE_COOLDOWN_UNTIL:
            logger.debug("Edge TTS 处于熔断冷却期，直接使用 Token Plan 音色")
        else:
            try:
                async for chunk in edge_tts_tts(text, voice=chosen):
                    yield chunk
                _EDGE_FAIL_COUNT = 0
                return
            except Exception:
                _EDGE_FAIL_COUNT += 1
                if _EDGE_FAIL_COUNT >= EDGE_FAIL_THRESHOLD:
                    _EDGE_COOLDOWN_UNTIL = time.time() + EDGE_COOLDOWN_SECONDS
                logger.warning(
                    "Edge TTS 合成失败（连续 %s 次），已回退 Token Plan 音色，冷却 %ss",
                    _EDGE_FAIL_COUNT, int(EDGE_COOLDOWN_SECONDS),
                )
        if not _get_voice_api_key():
            # 没有任何可用 Key，只能把 Edge 的错误抛给上层（前端会提示原因）
            async for chunk in edge_tts_tts(text, voice=chosen):
                yield chunk
            return
        async for chunk in tokenplan_tts(text, voice=FALLBACK_TOKENPLAN_VOICE):
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
    from app.models.notification import Notification, NotificationType

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
                # 必须使用枚举成员：写死字符串 "warning" 不在 NotificationType 内，
                # 提交时整笔事务会抛错回滚，导致心理关注与同事务的对话摘要全部落不了库。
                type=NotificationType.CRISIS,
                link="/teacher/crisis",
                related_id=user.id,
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
        # 语音识别：本地 SenseVoice（低延迟首选）-> 云端 qwen-audio-asr 兜底
        # ============================================================
        async def transcribe_audio(audio_bytes: bytes) -> str:
            t0 = time.monotonic()
            try:
                text = await local_sensevoice_stt(audio_bytes)
                if text:
                    logger.info(
                        "[STT] engine=local-sensevoice bytes=%d ms=%d text=%r",
                        len(audio_bytes), int((time.monotonic() - t0) * 1000), text,
                    )
                    return text
                logger.info("[STT] 本地识别为空，回退云端 bytes=%d", len(audio_bytes))
            except Exception:
                logger.warning("本地 SenseVoice 识别失败，回退云端 STT", exc_info=True)
            t1 = time.monotonic()
            text = await tokenplan_stt(audio_bytes, client=http_client)
            logger.info(
                "[STT] engine=cloud-qwen-asr bytes=%d ms=%d text=%r",
                len(audio_bytes), int((time.monotonic() - t1) * 1000), text,
            )
            return text

        # ============================================================
        # 通用回复链：LLM 流式 -> 句子级 TTS（边说边出）
        # 问候轮次与用户轮次共用，保证"智能体先开口"与正常对话同一套低延迟链路
        # ============================================================
        async def run_llm_tts(run_messages: list[dict]) -> tuple[str, bool]:
            """流式 LLM + 句级 TTS 链。返回 (完整回复文本, 是否被打断)。

            全程监听 cancel_event：用户开口即终止生成、跳过未播音频（豆包式打断），
            已播放/已输出的内容保留，未输出的直接作废。
            """
            full_response = ""
            interrupted = False
            sentence_buf = ""
            speaking_notified = False
            tts_error_notified = False
            tts_chain: asyncio.Task | None = None
            delta_count = 0
            first_delta_ms: int | None = None
            llm_t0 = time.monotonic()

            async def _synth_to_queue(phrase: str, q: asyncio.Queue) -> None:
                """独立合成一段短语：边产出边放入队列；结束/异常/被打断时放入 None 信号"""
                nonlocal tts_error_notified
                t0 = time.monotonic()
                nbytes = 0
                try:
                    async for chunk in synthesize_speech(phrase):
                        if cancel_event.is_set():
                            break
                        nbytes += len(chunk)
                        await q.put(chunk)
                    # 逐段合成结果落日志：这是定位"播报到一半失败"的关键证据
                    logger.info(
                        "[TTS] ok chars=%d bytes=%d ms=%d text=%r",
                        len(phrase), nbytes, int((time.monotonic() - t0) * 1000), phrase,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "[TTS] fail chars=%d bytes=%d ms=%d text=%r",
                        len(phrase), nbytes, int((time.monotonic() - t0) * 1000), phrase,
                    )
                    # 告知前端"这段没声音"，但错误文案保持友好（原始细节只进日志）
                    if not tts_error_notified:
                        tts_error_notified = True
                        await safe_send_json(websocket, {
                            "type": "error",
                            "message": "语音合成暂时不可用，已继续显示文字",
                        })
                finally:
                    await q.put(None)

            def enqueue_tts(phrase: str) -> None:
                """短语级流式 TTS：合成立即并发发起，发送严格按入队顺序链式执行。
                每段音频边下载边发送（首块到达即播报，无需等整段下载完），
                且多段合成时间重叠，整体播报显著提前"""
                nonlocal tts_chain
                prev = tts_chain
                chunk_q: asyncio.Queue[bytes | None] = asyncio.Queue()
                asyncio.create_task(_synth_to_queue(phrase, chunk_q))

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
                    messages=run_messages,
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
                        interrupted = True
                        break
                    delta_count += 1
                    if first_delta_ms is None:
                        first_delta_ms = int((time.monotonic() - llm_t0) * 1000)
                    # 编码异常探测：出现替换字符 U+FFFD 说明上游流式解码有问题（文字乱码根源）
                    if "\ufffd" in delta.content:
                        logger.warning(
                            "[LLM] 分片含替换字符 U+FFFD（疑似上游编码问题）delta#%d=%r",
                            delta_count, delta.content,
                        )
                    full_response += delta.content
                    sentence_buf += delta.content
                    if not await safe_send_json(websocket, {"type": "ai_text", "text": delta.content}):
                        break
                    # 语句级切分：产出即合成，实现"早开场"（不等完整回答）；
                    # 整句归段、首段早出音，杜绝碎块化造成的随机停顿
                    phrases, sentence_buf = _take_tts_phrases(
                        sentence_buf, first_early=(tts_chain is None)
                    )
                    for p in phrases:
                        if not _is_speakable(p):
                            # 纯空白/纯标点不合成（TTS 会 400）
                            continue
                        logger.debug("[PHRASE] enqueue %r", p)
                        enqueue_tts(p)

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("LLM 失败")
                await safe_send_json(websocket, {"type": "error", "message": "AI 回复失败"})
                return full_response, interrupted

            # 打断时：已入队的短语通过 runner 内的 cancel_event 检查跳过发送，
            # 合成任务自然结束，保证本轮历史/DB 正常收尾
            if not interrupted and sentence_buf.strip() and _is_speakable(sentence_buf):
                enqueue_tts(sentence_buf)

            if tts_chain is not None:
                try:
                    await tts_chain
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass

            logger.info(
                "[LLM] done deltas=%d first_delta_ms=%s chars=%d interrupted=%s",
                delta_count, first_delta_ms, len(full_response), interrupted,
            )
            return full_response, interrupted

        # ============================================================
        # 接通问候：智能体先开口（豆包式"AI 先说话"），按摄像头表情状态定制开场语
        # ============================================================
        async def process_greeting(emotion: str | None) -> None:
            """通话接通瞬间由 AI 先说话：结合当前表情状态生成一句自然口语化问候"""
            try:
                if not await safe_send_json(websocket, {"type": "state", "state": "processing"}):
                    return
                logger.info("[GREET] 开始生成问候 emotion=%s", emotion)
                greet_messages = [{"role": "system", "content": system_prompt}]
                if emotion:
                    greet_messages.append({
                        "role": "system",
                        "content": (
                            f"视觉情绪模块刚检测到：学生此刻表情偏【{EMOTION_LABELS.get(emotion, emotion)}】。"
                            f"{GREETING_EMOTION_HINT.get(emotion, '')}"
                        ),
                    })
                greet_messages.append({
                    "role": "system",
                    "content": (
                        "【本次为语音通话接通时刻】请由你先开口，用一句自然、亲切、口语化的问候开启聊天，"
                        "不超过 30 字，不要提及‘接通’‘系统’‘检测’等字眼；"
                        "若已知学生的表情状态，请自然地关照一下他的状态，可顺着你观察到的情绪开口，"
                        "但不要生硬地说‘我检测到你的表情’。"
                    ),
                })
                greet_messages.extend(history[-4:])  # 续聊时让问候承接上文
                full_response, interrupted = await run_llm_tts(greet_messages)
                if not interrupted and full_response.strip():
                    history.append({"role": "assistant", "content": full_response})
                    if len(history) > 50:
                        history[:] = history[-50:]
                    if conversation_id:
                        try:
                            db.add(ConversationMessage(
                                conversation_id=conversation_id, role="assistant", content=full_response,
                            ))
                            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
                            if conv:
                                conv.updated_at = datetime.now(timezone.utc)
                            db.commit()
                        except Exception:
                            db.rollback()
                            logger.exception("保存问候语失败")
                await safe_send_json(websocket, {"type": "state", "state": "listening"})
            except Exception:
                logger.exception("问候轮次失败")

        # ============================================================
        # 单轮对话处理：STT -> LLM 流式 -> 句子级 TTS 链（边说边出）
        # ============================================================
        async def process_round(audio_bytes: bytes) -> None:
            """处理一轮 语音->识别->对话->合成；全程监听打断信号 cancel_event"""
            text = ""
            full_response = ""
            try:
                if not await safe_send_json(websocket, {"type": "state", "state": "processing"}):
                    return

                # 1. STT（本地 SenseVoice 优先，云端兜底）
                try:
                    text = await transcribe_audio(audio_bytes)
                except Exception:
                    logger.exception("STT 失败")
                    await safe_send_json(websocket, {"type": "error", "message": "语音识别失败，请重试"})
                    await safe_send_json(websocket, {"type": "state", "state": "listening"})
                    return

                if cancel_event.is_set():
                    # 用户已开口打断本轮，丢弃识别结果
                    return
                if not text or not text.strip() or not _is_speakable(text):
                    # 空识别或"纯标点"（典型是音频质量差/采样率不匹配造成的幻觉输出），
                    # 不进入对话，避免把"。"当成学生说的内容去回答
                    logger.info("[STT] 识别结果无有效内容，忽略: %r", text)
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

                full_response, interrupted_llm = await run_llm_tts(messages)
                logger.info(
                    "[ROUND] done user=%r chars=%d interrupted=%s",
                    text, len(full_response), interrupted_llm,
                )

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

        # ============================================================
        # 接通即问候（豆包式"AI 先说话"）：连接建立即由后端自动触发，
        # 最多等待 EMOTION_GREET_WAIT 秒以取到首帧表情用于定制开场语。
        # 由后端主动触发（而非依赖前端时序），杜绝"问候语丢失"。
        # ============================================================
        first_emotion: dict = {"value": None}
        emotion_ready = asyncio.Event()
        greeted = False

        async def _greet_after_connect() -> None:
            nonlocal greeted
            t0 = time.monotonic()
            try:
                try:
                    await asyncio.wait_for(emotion_ready.wait(), timeout=EMOTION_GREET_WAIT)
                    waited = "(已就绪)"
                except asyncio.TimeoutError:
                    waited = f"(等待超时 {int(EMOTION_GREET_WAIT)}s)"
                emo = first_emotion["value"]
                logger.info(
                    "[GREET] 表情获取 %s waited_ms=%d emotion=%s → %s",
                    waited, int((time.monotonic() - t0) * 1000), emo,
                    "按表情定制问候" if emo else "未取到表情，用中性问候",
                )
                if greeted or cancel_event.is_set():
                    return
                greeted = True
                await process_greeting(emo)
            except Exception:
                logger.exception("接通问候失败")

        round_task = asyncio.create_task(_greet_after_connect())

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
                    # 首帧表情：用于接通问候的开场语定制
                    if first_emotion["value"] is None:
                        first_emotion["value"] = emo
                    emotion_ready.set()
                    # 保留最近 200 条，防止内存膨胀
                    if len(emotion_timeline) > 200:
                        emotion_timeline = emotion_timeline[-200:]

            elif msg["type"] == "emotion_unavailable":
                # 前端表情识别不可用（摄像头被拒 / 模型未就绪）：立即放行问候，不空等
                logger.info("[GREET] 收到 emotion_unavailable，立即进行问候")
                emotion_ready.set()

            elif msg["type"] == "start_call":
                # 兼容旧前端的显式问候触发：仅补记表情（问候已由连接时自动触发，避免重复）
                emo = msg.get("emotion")
                if emo and emo in EMOTION_LABELS:
                    if first_emotion["value"] is None:
                        first_emotion["value"] = emo
                    emotion_ready.set()

            elif msg["type"] == "end_of_speech":
                if len(audio_buffer) < MIN_SPEECH_BYTES:
                    # 音频太短，忽略（防噪声/毛刺触发空识别）
                    audio_buffer.clear()
                    continue

                payload = bytes(audio_buffer)
                audio_buffer.clear()

                # 不在接收循环里阻塞等待上一轮：把"等上一轮收尾 + 本轮处理"链进新任务，
                # 保证生成期间仍能及时处理 interrupt（用户打断）等信令
                prev_round = round_task

                async def _chained_round(prev: asyncio.Task | None, data: bytes = payload) -> None:
                    if prev is not None and not prev.done():
                        try:
                            await prev
                        except (Exception, asyncio.CancelledError):
                            pass
                    cancel_event.clear()
                    await process_round(data)

                round_task = asyncio.create_task(_chained_round(prev_round))

            elif msg["type"] == "interrupt":
                # 用户开口：终止正在进行的生成与合成（只保留最近一轮回答）
                cancel_event.set()
                # 丢弃已累积音频：此前缓冲里大量是 AI 自身播报的回声，
                # 若保留会与用户新说的话混在一起，被识别成乱码
                audio_buffer.clear()
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
