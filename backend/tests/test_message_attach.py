"""聊天附件消息（图片 / 语音）：解析口径 + 会话摘要 + 发送往返。

协议不变：附件仍是一条普通文本消息，content 里存 JSON
``{"type":"image|voice|file","text":...,"url":...,"duration":...}``。
这里守两条底线：
1. 服务端存原文、不擅自改写（前端按 type 渲染气泡）；
2. 任何「按人展示」的地方（会话摘要）必须给人话，不能把 JSON 甩给用户。
"""
import json

from app.models.user import UserRole
from app.utils.message_attach import parse_attachment, preview_of

IMAGE_URL = "/api/files/root/photo_ab12cd34.png"
VOICE_URL = "/api/files/root/voice-1793799477274_4d8f0412.webm"


def _attach(kind: str, **extra) -> str:
    return json.dumps({"type": kind, "url": extra.pop("url"), **extra})


# ---------------- 解析口径 ----------------

def test_parse_attachment_image_and_voice():
    image = parse_attachment(_attach("image", url=IMAGE_URL, text="合影.png"))
    assert image == {"type": "image", "text": "合影.png", "url": IMAGE_URL, "duration": 0}

    voice = parse_attachment(_attach("voice", url=VOICE_URL, text="", duration="75"))
    assert voice is not None and voice["duration"] == 75  # 字符串时长也吃


def test_parse_attachment_rejects_non_attachment():
    assert parse_attachment("普通文本") is None
    assert parse_attachment(None) is None
    assert parse_attachment("") is None
    assert parse_attachment("{坏掉的 json") is None
    # type 不在白名单 / 缺 url / url 不是站内相对地址，一律当文本
    assert parse_attachment(json.dumps({"type": "video", "url": IMAGE_URL})) is None
    assert parse_attachment(json.dumps({"type": "image"})) is None
    assert parse_attachment(json.dumps({"type": "image", "url": "javascript:alert(1)"})) is None


def test_preview_of_attachment_and_text():
    assert preview_of(_attach("image", url=IMAGE_URL, text="合影.png")) == "[图片]"
    assert preview_of(_attach("voice", url=VOICE_URL, duration=3)) == "[语音 3″]"
    assert preview_of(_attach("voice", url=VOICE_URL, duration=75)) == "[语音 1′15″]"
    assert preview_of(_attach("file", url="/api/files/root/a.pdf", text="报告.pdf")) == "[文件] 报告.pdf"
    # 文本按 80 字截断（与原口径一致）；坏 JSON 原样返回，不丢用户内容
    assert len(preview_of("字" * 200)) == 80
    assert preview_of("{坏 json") == "{坏 json"


# ---------------- 接口往返 ----------------

def test_attachment_message_kept_raw_and_preview_is_human(client, api, login_token):
    """发一条语音：库里/接口里是原文 JSON，会话摘要给人话。"""
    student = login_token()
    tutor = login_token(UserRole.TEACHER)
    content = _attach("voice", url=VOICE_URL, text="", duration=75)

    resp = api.post(
        "/api/messages/send",
        json={"receiver_id": tutor["user"].id, "content": content},
        headers=student["headers"],
    )
    assert resp.status_code == 200

    # 1) 拉聊天记录：原文一字不改 —— 前端靠它解析类型 / 时长
    history = client.get(f"/api/messages/{tutor['user'].id}", headers=student["headers"]).json()
    assert history[-1]["content"] == content

    # 2) 会话摘要：不能出现 {"type":"voice"...
    convs = client.get("/api/messages/conversations", headers=student["headers"]).json()
    conv = next(c for c in convs if c["user_id"] == tutor["user"].id)
    assert conv["last_message"] == "[语音 1′15″]"


def test_image_attachment_preview_in_conversation(client, api, login_token):
    student = login_token()
    tutor = login_token(UserRole.TEACHER)
    resp = api.post(
        "/api/messages/send",
        json={"receiver_id": tutor["user"].id, "content": _attach("image", url=IMAGE_URL, text="校园.png")},
        headers=student["headers"],
    )
    assert resp.status_code == 200
    convs = client.get("/api/messages/conversations", headers=student["headers"]).json()
    conv = next(c for c in convs if c["user_id"] == tutor["user"].id)
    assert conv["last_message"] == "[图片]"
