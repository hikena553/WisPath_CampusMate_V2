"""匿名问卷互评：匿名硬约束（答卷不落提交人、结果只出聚合、小样本不出分布）+ 防重。"""
from app.models.peer_survey import PeerSurveyResponse
from app.models.user import UserRole


def _login(client, user) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": user.username, "password": "TestPass123"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


QUESTIONS = [
    {"key": "care", "label": "关心学生", "max": 5},
    {"key": "fair", "label": "处事公正", "max": 5},
]


def _create_open_survey(api, headers, title="2026 春季辅导员互评"):
    resp = api.post(
        "/api/peer-surveys",
        json={
            "title": title,
            "target_type": "peer",
            "period": "2026-spring",
            "questions": QUESTIONS,
            "status": "open",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_survey_submit_dedup_and_anonymity(client, api, make_user, db):
    creator = make_user(role=UserRole.TEACHER)
    target = make_user(role=UserRole.TEACHER)
    c_headers = _login(client, creator)

    survey_id = _create_open_survey(api, c_headers)

    first = api.post(
        f"/api/peer-surveys/{survey_id}/responses",
        json={"target_teacher_id": target.id, "scores": {"care": 5, "fair": 4}, "suggestion": "多组织班级活动"},
        headers=c_headers,
    )
    assert first.status_code == 200, first.text
    assert "匿名" in first.json()["message"]

    # 防重：同一人 + 同一被评人 第二次提交被拒
    dup = api.post(
        f"/api/peer-surveys/{survey_id}/responses",
        json={"target_teacher_id": target.id, "scores": {"care": 4}},
        headers=c_headers,
    )
    assert dup.status_code == 409

    # 数据库层不存在提交人字段；仅存匿名令牌
    row = db.query(PeerSurveyResponse).filter(PeerSurveyResponse.survey_id == survey_id).first()
    assert row is not None
    assert not hasattr(row, "submitter_id")
    assert row.anonymous_token


def test_survey_result_masks_small_sample_and_never_leaks_token(client, api, make_user, db):
    creator = make_user(role=UserRole.TEACHER)
    target = make_user(role=UserRole.TEACHER)
    c_headers = _login(client, creator)
    survey_id = _create_open_survey(api, c_headers)

    api.post(
        f"/api/peer-surveys/{survey_id}/responses",
        json={"target_teacher_id": target.id, "scores": {"care": 5, "fair": 5}, "suggestion": "很好"},
        headers=c_headers,
    )

    # 样本不足：不出分布 / 均分 / 建议
    small = api.get(
        f"/api/peer-surveys/{survey_id}/result",
        params={"target_teacher_id": target.id},
        headers=c_headers,
    )
    assert small.status_code == 200, small.text
    data = small.json()
    assert data["response_count"] == 1
    assert data["enough_sample"] is False
    assert data["overall_average"] is None
    assert data["suggestions"] == []
    assert all(q["average"] is None and q["distribution"] == {} for q in data["questions"])

    # 补足到 5 份（不同提交人 → 不同匿名令牌），分布与均分出现
    for _ in range(4):
        other = make_user(role=UserRole.TEACHER)
        headers = _login(client, other)
        resp = api.post(
            f"/api/peer-surveys/{survey_id}/responses",
            json={"target_teacher_id": target.id, "scores": {"care": 4, "fair": 5}},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

    full = api.get(
        f"/api/peer-surveys/{survey_id}/result",
        params={"target_teacher_id": target.id},
        headers=c_headers,
    ).json()
    assert full["enough_sample"] is True
    assert full["response_count"] == 5
    assert full["overall_average"] is not None

    # 结果体不得含匿名令牌 / 提交人信息
    raw = api.get(
        f"/api/peer-surveys/{survey_id}/result",
        params={"target_teacher_id": target.id},
        headers=c_headers,
    ).text
    assert "anonymous_token" not in raw
    token = db.query(PeerSurveyResponse).filter(PeerSurveyResponse.survey_id == survey_id).first().anonymous_token
    assert token not in raw


def test_survey_open_required_and_mine(client, api, make_user):
    creator = make_user(role=UserRole.TEACHER)
    target = make_user(role=UserRole.TEACHER)
    c_headers = _login(client, creator)

    # 草稿态不可提交
    draft = api.post(
        "/api/peer-surveys",
        json={"title": "草稿问卷", "questions": QUESTIONS, "status": "draft"},
        headers=c_headers,
    ).json()
    blocked = api.post(
        f"/api/peer-surveys/{draft['id']}/responses",
        json={"target_teacher_id": target.id, "scores": {"care": 5}},
        headers=c_headers,
    )
    assert blocked.status_code == 400

    # 开放后提交，「我的被评结果」能看到该问卷的聚合
    api.patch(
        f"/api/peer-surveys/{draft['id']}/status", json={"status": "open"}, headers=c_headers
    )
    api.post(
        f"/api/peer-surveys/{draft['id']}/responses",
        json={"target_teacher_id": target.id, "scores": {"care": 5, "fair": 5}},
        headers=c_headers,
    )

    t_headers = _login(client, target)
    mine = api.get("/api/peer-surveys/mine", headers=t_headers)
    assert mine.status_code == 200, mine.text
    assert any(m["survey_id"] == draft["id"] for m in mine.json())
    # 被评人也只看得到聚合，拿不到单条答卷
    assert "anonymous_token" not in mine.text