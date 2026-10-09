import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from pathlib import Path

from app.core.database import get_db
from app.core.deps import require_role
from app.core.crypto import (
    is_sensitive_key, encrypt_value, decrypt_value,
    is_encrypted, is_masked_value,
)
from app.models.user import User, UserRole
from app.models.setting import SystemSetting
from app.services.setting_service import get_public_settings
from app.services.voice_service import (
    VOICE_STT_MODEL, VOICE_STT_URL,
    VOICE_TTS_MODEL_DEFAULT, VOICE_TTS_URL,
    synthesize_speech, pcm_to_wav,
    _get_tts_voice, _get_tts_prompt,
    _voice_to_model,
    InvalidVoiceError,
    VOICE_MODEL_CATALOG,
    EDGE_TTS_ZH_VOICES,
    is_edge_voice,
)

router = APIRouter(prefix="/api/settings", tags=["系统设置"])

# 品牌图片类设置键：替换时自动清理 uploads/branding 下不再引用的旧文件
BRANDING_KEYS = {"site_logo", "site_mascot"}
BRANDING_URL_PREFIX = "/api/files/branding/"
BRANDING_URL_PREFIX_LEGACY = "/uploads/branding/"
BRANDING_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "branding"


def _cleanup_branding_old_file(db: Session, key: str, new_value: str) -> None:
    """品牌图片被替换后，删除 uploads/branding 中不再被引用的旧文件"""
    if key not in BRANDING_KEYS:
        return
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    old = setting.value if setting else None
    if not old or old == new_value or not (
        old.startswith(BRANDING_URL_PREFIX) or old.startswith(BRANDING_URL_PREFIX_LEGACY)
    ):
        return
    try:
        target = BRANDING_DIR / Path(old).name
        if target.exists() and target.is_file():
            target.unlink()
    except Exception:
        pass


# ===== Schemas =====
class SettingOut(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    value: str


class SettingBatchUpdate(BaseModel):
    settings: dict  # {key: value}


class TTSTestRequest(BaseModel):
    text: str = "你好，我是绵小城，很高兴为你服务。今天天气不错，记得保持好心情哦！"
    voice: Optional[str] = None


class VoicePipelineInfo(BaseModel):
    """语音链路信息：识别/合成模型与当前生效配置，供管理端链路展示"""

    stt: dict
    tts: dict
    voice: str
    voice_model: str  # 当前 voice 对应的 TTS 模型
    voice_prompt: str
    llm_model: str
    # 可选用音色（按模型分组的多分组清单），每项包含 model / verified 字段
    voices: List[dict] = []
    # 顶层模型分组：[{ model: "qwen-audio-3.0-tts-plus", label: "...", voices: [...] }, ...]
    voice_groups: List[dict] = []
    providers: List[str] = ["tokenplan"]


def _voice_groups() -> list[dict]:
    """下发可选用音色清单：仅包含实测可用的音色。

    - tokenplan（阿里云百炼）：当前账号实测仅有 qwen-audio-3.0-tts-plus 模型的 2 个音色。
    - edge（微软免费）：内置 14 个中文音色全部经过实测可用。
    每项均包含 provider / model / verified 字段，前端可按 provider 分组渲染。
    """
    label_map = {
        "qwen-audio-3.0-tts-plus": "阿里云百炼 · 旗舰社交陪伴",
    }
    groups: list[dict] = []
    for model, voices in VOICE_MODEL_CATALOG.items():
        usable = [v for v in voices if v.get("verified")]
        if not usable:
            continue
        groups.append({
            "provider": "tokenplan",
            "model": model,
            "label": label_map.get(model, model),
            "voices": [{**v, "model": model, "provider": "tokenplan"} for v in usable],
        })
    # Edge TTS 组：内置 14 个中文音色，按 locale 分标签
    edge_groups: dict[str, list[dict]] = {}
    edge_locale_order = []
    for v in EDGE_TTS_ZH_VOICES:
        voice_id = v["voice"]
        # zh-CN-SMxxxNeural / zh-CN-liaoning-XiaobeiNeural -> 按 locale 归类
        parts = voice_id.split("-")
        if "liaoning" in voice_id or "shaanxi" in voice_id:
            key = "普通话·方言"
        elif voice_id.startswith("zh-HK"):
            key = "粤语"
        elif voice_id.startswith("zh-TW"):
            key = "台湾国语"
        else:
            key = "普通话"
        if key not in edge_groups:
            edge_groups[key] = []
            edge_locale_order.append(key)
        edge_groups[key].append({
            **v,
            "provider": "edge",
            "model": "edge-tts",
            "verified": True,
        })
    for key in edge_locale_order:
        groups.append({
            "provider": "edge",
            "model": "edge-tts",
            "label": f"Edge TTS · {key}",
            "voices": edge_groups[key],
        })
    return groups


def _flat_voices(groups: list[dict]) -> list[dict]:
    """把分组清单展开成一维数组，保留 model 字段。"""
    return [v for g in groups for v in g["voices"]]


# ===== Endpoints =====
@router.get("", response_model=List[SettingOut])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """获取所有系统设置（仅管理员）"""
    settings = db.query(SystemSetting).all()
    result = []
    for s in settings:
        val = s.value
        # 敏感字段脱敏：只显示首尾各 4 字符
        if is_sensitive_key(s.key) and val and not is_masked_value(val):
            decrypted = decrypt_value(val) if is_encrypted(val) else val
            if len(decrypted) > 8:
                val = decrypted[:4] + "****" + decrypted[-4:]
            else:
                val = "****"
        result.append(SettingOut(id=s.id, key=s.key, value=val, description=s.description))
    return result


@router.get("/public", response_model=dict[str, str])
def read_public_settings(db: Session = Depends(get_db)):
    """获取公开展示类设置（免登录）：站点名称 / Logo / 吉祥物 / 系统公告 / 助手称谓。

    登录页、分享页与各端需在未登录状态下渲染站点品牌，故开放匿名访问；
    仅返回白名单键，API Key 等敏感配置不下发（见 setting_service.get_public_settings）。
    注意：必须声明在 `/{key}` 之前，否则会被其吞掉。
    """
    return get_public_settings(db)


@router.get("/{key}", response_model=SettingOut)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """获取单个设置（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    val = setting.value
    if is_sensitive_key(key) and val and not is_masked_value(val):
        decrypted = decrypt_value(val) if is_encrypted(val) else val
        if len(decrypted) > 8:
            val = decrypted[:4] + "****" + decrypted[-4:]
        else:
            val = "****"
    return SettingOut(id=setting.id, key=setting.key, value=val, description=setting.description)


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    data: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """更新设置（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    value = data.value
    # 敏感字段：掩码值跳过（管理员未修改），明文值加密后存储
    if is_sensitive_key(key):
        if is_masked_value(value):
            # 管理员没有修改，原样返回现有值
            if setting:
                return SettingOut(id=setting.id, key=setting.key, value=value, description=setting.description)
            return SettingOut(id=0, key=key, value=value)
        if value:  # 非空明文 → 加密
            value = encrypt_value(value)

    if not setting:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
    else:
        _cleanup_branding_old_file(db, key, value)
        setting.value = value

    db.commit()
    db.refresh(setting)

    # 返回时脱敏
    display_val = setting.value
    if is_sensitive_key(key) and display_val:
        decrypted = decrypt_value(display_val) if is_encrypted(display_val) else display_val
        if len(decrypted) > 8:
            display_val = decrypted[:4] + "****" + decrypted[-4:]
        else:
            display_val = "****"

    return SettingOut(id=setting.id, key=setting.key, value=display_val, description=setting.description)


@router.put("", response_model=dict)
def batch_update_settings(
    data: SettingBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """批量更新设置（仅管理员）"""
    updated = []
    for key, value in data.settings.items():
        # 敏感字段：掩码值跳过
        if is_sensitive_key(key) and is_masked_value(value):
            continue

        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

        # 敏感字段非空值加密
        if is_sensitive_key(key) and value:
            value = encrypt_value(value)

        if not setting:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            _cleanup_branding_old_file(db, key, value)
            setting.value = value
        updated.append(key)

    db.commit()
    return {"message": f"已更新 {len(updated)} 项设置", "updated": updated}


def _read_setting(db: Session, key: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row and row.value:
        # 敏感字段（如 API Key）已加密存储：链路信息仅用于展示，不解密
        if is_sensitive_key(key):
            return "已配置"
        return row.value.strip()
    return ""


@router.get("/voice/info", response_model=VoicePipelineInfo)
async def get_voice_pipeline_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """获取语音 TTS 链路信息：识别/合成模型、当前生效音色（含归属模型）、
    可选用音色按模型分组的多分组清单与播报提示词（仅管理员）"""
    llm_model = _read_setting(db, "llm_agent_model") or _read_setting(db, "llm_model")

    groups = _voice_groups()
    flat = _flat_voices(groups)

    current_voice = _get_tts_voice()
    current_model = _voice_to_model(current_voice)
    return VoicePipelineInfo(
        stt={"model": VOICE_STT_MODEL, "url": VOICE_STT_URL},
        tts={"model": VOICE_TTS_MODEL_DEFAULT, "url": VOICE_TTS_URL},
        voice=current_voice,
        voice_model=current_model,
        voice_prompt=_get_tts_prompt(),
        llm_model=llm_model,
        voices=flat,
        voice_groups=groups,
    )


@router.post("/tts/test", response_model=dict)
async def test_tts_synthesis(
    data: TTSTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """TTS 试听：按指定音色（缺省用当前生效音色）合成一句示例语音，返回 WAV base64（仅管理员）

    后端按 voice 自动选择对应模型（plus / 3.0-flash / 3.1-flash）调用，
    试听响应里 model 字段告诉前端实际使用的模型，便于用户排查可用音色。"""
    text = data.text.strip() or TTSTestRequest().text
    if len(text) > 200:
        raise HTTPException(status_code=400, detail="试听文本不能超过 200 字")
    voice = (data.voice or "").strip() or _get_tts_voice()

    chunks: list[bytes] = []
    total = 0
    tts_model = _voice_to_model(voice) or VOICE_TTS_MODEL_DEFAULT
    try:
        try:
            async for chunk in synthesize_speech(text, voice=voice):
                chunks.append(chunk)
                total += len(chunk)
                if total > 8 * 1024 * 1024:  # 单次试听最多 8MB 音频，防止异常响应撑爆内存
                    raise HTTPException(status_code=413, detail="合成音频过大，请缩短试听文本")
        except InvalidVoiceError as exc:
            # 非法音色（如前端 allow-create 输入的任意字符串、拼写错），
            # 在发送阿里云请求前拦截，避免 cosyvoice 4xx（如 411）暗错
            raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"语音合成失败：{exc}")

    if not chunks:
        raise HTTPException(status_code=502, detail="语音合成未返回音频数据")

    wav_bytes = pcm_to_wav(b"".join(chunks))
    return {
        "audio_base64": base64.b64encode(wav_bytes).decode(),
        "voice": voice,
        "model": tts_model,
        "chars": len(text),
    }
