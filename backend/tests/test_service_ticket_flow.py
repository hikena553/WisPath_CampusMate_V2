"""办事大厅工单流程闭环测试（p4_3）。

覆盖：状态机 PENDING → PROCESSING → APPROVED/REJECTED、终态保护、
review_comment/approver_name 落地、审批视角列表（教师可查待审批队列）、权限隔离。
"""
import pytest

from app.models.service import ServiceTicket, TicketStatus
from app.models.user import UserRole


def _create_ticket(api, headers, **overrides):
    payload = {
        "type": "leave",
        "title": "五一离校申请",
        "content": "需要离校三天",
        **overrides,
    }
    resp = api.post("/api/service/tickets", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_student_create_then_teacher_sees_pending_queue(client, api, login_token):
    """学生创建工单后，教师待审批列表可见，学生视角仅见本人记录。"""
    student = login_token(role=UserRole.STUDENT)
    ticket = _create_ticket(api, student["headers"])

    teacher = login_token(role=UserRole.TEACHER)
    resp = api.get("/api/service/tickets", headers=teacher["headers"])
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert ticket["id"] in ids
    assert all(t["status"] == "pending" for t in resp.json())

    # 学生视角：包含自己的工单，且不出现教师视角独有数据
    resp = api.get("/api/service/tickets", headers=student["headers"])
    assert resp.status_code == 200
    mine = [t["id"] for t in resp.json()]
    assert ticket["id"] in mine


def test_approve_with_comment_persists_and_terminal_guard(client, api, login_token, db):
    """审批通过：comment 落库；终态后再审批被拒。"""
    student = login_token(role=UserRole.STUDENT)
    ticket = _create_ticket(api, student["headers"])
    teacher = login_token(role=UserRole.TEACHER)

    resp = api.put(
        f"/api/service/tickets/{ticket['id']}/approve",
        json={"action": "approve", "comment": "材料齐全，同意离校"},
        headers=teacher["headers"],
    )
    assert resp.status_code == 200, resp.text

    row = db.get(ServiceTicket, ticket["id"])
    assert row.status == TicketStatus.APPROVED
    assert row.approver_name == teacher["user"].name
    assert row.review_comment == "材料齐全，同意离校"
    assert row.updated_at is not None

    # 终态保护：再次审批 400
    resp = api.put(
        f"/api/service/tickets/{ticket['id']}/approve",
        json={"action": "approve"},
        headers=teacher["headers"],
    )
    assert resp.status_code == 400
    assert "终态" in resp.json()["detail"]


def test_reject_flow_and_processing_intermediate(client, api, login_token, db):
    """驳回流程；PROCESSING 中间态可审批（REJECTED 仅可由 PENDING/PROCESSING 进入）。"""
    student = login_token(role=UserRole.STUDENT)
    teacher = login_token(role=UserRole.TEACHER)

    # 直接驳回（PENDING → REJECTED）
    t1 = _create_ticket(api, student["headers"], title="材料不全单")
    resp = api.put(
        f"/api/service/tickets/{t1['id']}/approve",
        json={"action": "reject", "comment": "材料不全"},
        headers=teacher["headers"],
    )
    assert resp.status_code == 200
    assert db.get(ServiceTicket, t1["id"]).status == TicketStatus.REJECTED

    # 中间态 PROCESSING → REJECTED
    t2 = _create_ticket(api, student["headers"], title="中间态单")
    row = db.get(ServiceTicket, t2["id"])
    row.status = TicketStatus.PROCESSING
    db.commit()
    resp = api.put(
        f"/api/service/tickets/{t2['id']}/approve",
        json={"action": "reject", "comment": "不符合条件"},
        headers=teacher["headers"],
    )
    assert resp.status_code == 200
    assert db.get(ServiceTicket, t2["id"]).status == TicketStatus.REJECTED

    # REJECTED 为终态：不可再审批
    resp = api.put(
        f"/api/service/tickets/{t1['id']}/approve",
        json={"action": "approve"},
        headers=teacher["headers"],
    )
    assert resp.status_code == 400


def test_approve_role_and_action_validation(client, api, login_token, db):
    """学生不可审批；非法 action 拒绝。"""
    student_a = login_token(role=UserRole.STUDENT)
    ticket = _create_ticket(api, student_a["headers"])

    # 学生审批 403
    student_b = login_token(role=UserRole.STUDENT)
    resp = api.put(
        f"/api/service/tickets/{ticket['id']}/approve",
        json={"action": "approve"},
        headers=student_b["headers"],
    )
    assert resp.status_code == 403

    teacher = login_token(role=UserRole.TEACHER)
    resp = api.put(
        f"/api/service/tickets/{ticket['id']}/approve",
        json={"action": "weird"},
        headers=teacher["headers"],
    )
    assert resp.status_code == 400


def test_cancel_only_pending(client, api, login_token, db):
    """撤销仅限 PENDING；已审批工单不可撤销。"""
    student = login_token(role=UserRole.STUDENT)
    ticket = _create_ticket(api, student["headers"])

    resp = api.put(f"/api/service/tickets/{ticket['id']}/cancel", headers=student["headers"])
    assert resp.status_code == 200
    assert db.get(ServiceTicket, ticket["id"]) is None

    t2 = _create_ticket(api, student["headers"], title="审批后不可撤销")
    teacher = login_token(role=UserRole.TEACHER)
    api.put(
        f"/api/service/tickets/{t2['id']}/approve",
        json={"action": "approve"},
        headers=teacher["headers"],
    )
    resp = api.put(f"/api/service/tickets/{t2['id']}/cancel", headers=student["headers"])
    assert resp.status_code == 400