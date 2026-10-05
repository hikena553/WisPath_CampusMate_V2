"""家校沟通：联系人脱敏 / 台账三通道（短信优雅降级）/ 分享链接规则与撤销 / 危机约谈留痕。"""
from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.guardian import (
    Guardian,
    GuardianContactLog,
    GuardianScene,
    GuardianShareLink,
)
from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_guardian_crud_and_phone_masked(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id, name="联系人对象")
    headers = _login(client, teacher)

    created = api.post(
        "/api/guardians",
        json={
            "student_id": student.id,
            "name": "王女士",
            "relation": "母亲",
            "phone": "13800001111",
            "is_primary": True,
            "remark": "工作日晚间联系",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["phone_masked"] == "138****1111"
    assert "13800001111" not in created.text  # 手机号不落明文输出
    assert body["student_name"] == student.name

    listed = api.get("/api/guardians", params={"student_id": student.id}, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = api.patch(
        f"/api/guardians/{body['id']}", json={"relation": "家长"}, headers=headers
    )
    assert updated.json()["relation"] == "家长"

    assert api.delete(f"/api/guardians/{body['id']}", headers=headers).status_code == 200
    assert db.get(Guardian, body["id"]).is_deleted is True


def test_contact_log_sms_degrades_and_share_link_rules(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    headers = _login(client, teacher)

    guardian_id = api.post(
        "/api/guardians",
        json={"student_id": student.id, "name": "李先生", "relation": "父亲", "phone": "13900002222"},
        headers=headers,
    ).json()["id"]

    # 短信通道：未配置服务商 → 优雅降级为 pending，不报错
    sms_log = api.post(
        "/api/guardians/logs",
        json={
            "student_id": student.id,
            "guardian_id": guardian_id,
            "scene": "leave",
            "channel": "sms",
            "content_summary": "学生请假已批准，请注意返校时间",
            "send_sms": True,
        },
        headers=headers,
    )
    assert sms_log.status_code == 200, sms_log.text
    assert sms_log.json()["status"] == "pending"

    # 危机类记录禁止生成分享链接
    crisis_log = api.post(
        "/api/guardians/logs",
        json={
            "student_id": student.id,
            "scene": "crisis",
            "channel": "note",
            "content_summary": "约谈家长，说明近期情绪状况",
        },
        headers=headers,
    ).json()
    blocked = api.post(f"/api/guardians/logs/{crisis_log['id']}/share-link", headers=headers)
    assert blocked.status_code == 400
    assert "禁止" in blocked.json()["detail"]

    # 普通关怀记录可生成链接，家长免登录只读访问
    care_log = api.post(
        "/api/guardians/logs",
        json={
            "student_id": student.id,
            "scene": "care",
            "channel": "link",
            "content_summary": "本月学习状态良好，已获进步之星",
        },
        headers=headers,
    ).json()
    link = api.post(f"/api/guardians/logs/{care_log['id']}/share-link", headers=headers)
    assert link.status_code == 200, link.text
    token = link.json()["token"]
    assert link.json()["path"] == f"/share/guardian/{token}"

    # 公开只读（无鉴权）
    shared = api.get(f"/api/guardians/share/{token}")
    assert shared.status_code == 200, shared.text
    assert shared.json()["scene_label"] == "日常关怀"
    assert shared.json()["content_summary"] == "本月学习状态良好，已获进步之星"

    # 撤销后不可访问
    link_id = link.json()["id"]
    assert api.post(f"/api/guardians/share-links/{link_id}/revoke", headers=headers).status_code == 200
    revoked = api.get(f"/api/guardians/share/{token}")
    assert revoked.status_code == 410
    assert db.get(GuardianShareLink, link_id).revoked is True
    assert db.get(GuardianShareLink, link_id).view_count == 1


def test_crisis_intervention_creates_guardian_log(client, api, make_user, db):
    teacher = make_user(role=UserRole.TEACHER)
    student = make_user(role=UserRole.STUDENT, tutor_id=teacher.id)
    headers = _login(client, teacher)

    alert = AIDialogSummary(
        student_id=student.id,
        summary="近期情绪波动较大",
        level=CrisisLevel.MODERATE,
        resolved=False,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    resp = api.post(
        f"/api/crisis/{alert.id}/intervene",
        json={
            "intervention_type": "约谈家长",
            "intervention_note": "与家长约定周五面谈",
            "resolved": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    logs = (
        db.query(GuardianContactLog)
        .filter(GuardianContactLog.student_id == student.id, GuardianContactLog.scene == GuardianScene.CRISIS)
        .all()
    )
    assert len(logs) == 1
    assert logs[0].content_summary == "与家长约定周五面谈"
    assert logs[0].channel.value == "note"

    listed = api.get("/api/guardians/logs", params={"student_id": student.id}, headers=headers).json()
    assert any(l["scene"] == "crisis" for l in listed)