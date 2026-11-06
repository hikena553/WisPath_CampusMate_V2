"""单聊消息头像：聊天气泡与会话列表必须同源。

会话列表走 ConversationOut.user_avatar，聊天气泡走 MessageOut.sender_avatar。
MessageOut 一旦不返回头像，前端气泡只能退回首字母，就会出现
「列表里是人像、进对话变成字」的割裂（移动端最明显）。
"""
from app.models.user import UserRole

PEER_AVATAR = "/api/files/root/peer_avatar_test.png"


def test_message_and_conversation_share_sender_avatar(api, login_token, db):
    me = login_token(role=UserRole.STUDENT)
    peer = login_token(role=UserRole.STUDENT)
    peer["user"].avatar = PEER_AVATAR
    db.commit()

    # 对方发来一条消息
    resp = api.post(
        "/api/messages/send",
        json={"receiver_id": me["user"].id, "content": "头像口径一致性"},
        headers=peer["headers"],
    )
    assert resp.status_code == 200, resp.text

    # 气泡数据：消息里带回发送者头像
    resp = api.get(f"/api/messages/{peer['user'].id}", headers=me["headers"])
    assert resp.status_code == 200, resp.text
    msgs = resp.json()
    assert msgs and msgs[-1]["sender_id"] == peer["user"].id
    assert msgs[-1]["sender_avatar"] == PEER_AVATAR

    # 列表数据：同一枚头像，前端两处渲染不会各说各话
    resp = api.get("/api/messages/conversations", headers=me["headers"])
    assert resp.status_code == 200, resp.text
    conv = next(c for c in resp.json() if c["user_id"] == peer["user"].id)
    assert conv["user_avatar"] == msgs[-1]["sender_avatar"] == PEER_AVATAR
