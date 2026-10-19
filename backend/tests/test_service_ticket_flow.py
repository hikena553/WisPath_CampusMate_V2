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


def test_teacher_can_query_terminal_tickets_for_ledger(client, api, login_token, db):
    """闭环留痕：教师可按状态查终态工单（已通过 / 已拒绝），默认仍是待审批队列。"""
    student = login_token(role=UserRole.STUDENT)
    teacher = login_token(role=UserRole.TEACHER)

    ok = _create_ticket(api, student["headers"], title="已通过留痕单")
    no = _create_ticket(api, student["headers"], title="已拒绝留痕单")
    api.put(
        f"/api/service/tickets/{ok['id']}/approve",
        json={"action": "approve", "comment": "材料齐全，同意"},
        headers=teacher["headers"],
    )
    api.put(
        f"/api/service/tickets/{no['id']}/approve",
        json={"action": "reject", "comment": "材料不全"},
        headers=teacher["headers"],
    )

    resp = api.get("/api/service/tickets", headers=teacher["headers"], params={"status": "approved"})
    assert resp.status_code == 200, resp.text
    approved_rows = resp.json()
    assert all(r["status"] == "approved" for r in approved_rows)
    assert no["id"] not in [r["id"] for r in approved_rows]
    mine = next(r for r in approved_rows if r["id"] == ok["id"])
    assert mine["approver_name"] == teacher["user"].name
    assert mine["review_comment"] == "材料齐全，同意"

    # 默认口径不受影响：终态不出现在待审批队列里
    resp = api.get("/api/service/tickets", headers=teacher["headers"])
    assert ok["id"] not in [t["id"] for t in resp.json()]

    # 非法状态值仍拒绝，避免审批视角把全量数据拉走
    resp = api.get("/api/service/tickets", headers=teacher["headers"], params={"status": "all"})
    assert resp.status_code == 400


def test_claim_assigns_owner_and_my_scope(client, api, login_token, db):
    """受理（认领）：待受理 → 处理中，责任人落地；「我受理的」能查到；别人不能重复受理。"""
    student = login_token(role=UserRole.STUDENT)
    ticket = _create_ticket(api, student["headers"])
    a = login_token(role=UserRole.TEACHER)
    b = login_token(role=UserRole.TEACHER)

    resp = api.put(f"/api/service/tickets/{ticket['id']}/claim", headers=a["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "processing"
    assert resp.json()["approver_name"] == a["user"].name

    row = db.get(ServiceTicket, ticket["id"])
    assert row.status == TicketStatus.PROCESSING
    assert row.approver_id == a["user"].id

    # 我受理的：只出现在受理人的 mine 视图
    mine_a = api.get("/api/service/tickets", headers=a["headers"], params={"scope": "mine"}).json()
    assert ticket["id"] in [t["id"] for t in mine_a]
    mine_b = api.get("/api/service/tickets", headers=b["headers"], params={"scope": "mine"}).json()
    assert ticket["id"] not in [t["id"] for t in mine_b]

    # 共享队列里仍然可见（带责任人），但别人重复受理被拒
    queue = api.get("/api/service/tickets", headers=b["headers"]).json()
    assert ticket["id"] in [t["id"] for t in queue]
    resp = api.put(f"/api/service/tickets/{ticket['id']}/claim", headers=b["headers"])
    assert resp.status_code == 400
    assert "已由" in resp.json()["detail"]

    # scope 取值校验
    resp = api.get("/api/service/tickets", headers=a["headers"], params={"scope": "weird"})
    assert resp.status_code == 400


def test_claim_guards_terminal_and_role(client, api, login_token):
    """终态工单不可再受理；学生不可受理。"""
    student = login_token(role=UserRole.STUDENT)
    teacher = login_token(role=UserRole.TEACHER)

    done = _create_ticket(api, student["headers"], title="已办结单")
    api.put(
        f"/api/service/tickets/{done['id']}/approve",
        json={"action": "approve"},
        headers=teacher["headers"],
    )
    resp = api.put(f"/api/service/tickets/{done['id']}/claim", headers=teacher["headers"])
    assert resp.status_code == 400
    assert "终态" in resp.json()["detail"]

    fresh = _create_ticket(api, student["headers"], title="学生不能受理")
    resp = api.put(f"/api/service/tickets/{fresh['id']}/claim", headers=student["headers"])
    assert resp.status_code == 403


def test_approval_stats_follows_shared_ticket_queue(client, api, login_token):
    """统计口径与共享工单队列一致：导师名下没有该学生，工单通过后统计也要跟着动。"""
    student = login_token(role=UserRole.STUDENT)
    ticket = _create_ticket(api, student["headers"])

    reviewer = login_token(role=UserRole.TEACHER)  # 该导师名下没有学生
    queue_ids = [t["id"] for t in api.get("/api/service/tickets", headers=reviewer["headers"]).json()]
    assert ticket["id"] in queue_ids, "共享队列里应能看到该工单"
    before = api.get("/api/approval/stats", headers=reviewer["headers"]).json()

    resp = api.put(
        f"/api/service/tickets/{ticket['id']}/approve",
        json={"action": "approve"},
        headers=reviewer["headers"],
    )
    assert resp.status_code == 200, resp.text

    after = api.get("/api/approval/stats", headers=reviewer["headers"]).json()
    assert after["approved"] == before["approved"] + 1
    assert after["pending"] == before["pending"] - 1
    assert after["total"] == before["total"]


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