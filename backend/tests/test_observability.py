"""可观测性测试（p4_1）：health 探活扩展 + 结构化日志 + 请求日志中间件。"""
import json
import logging

from app.core.logging_setup import JsonFormatter


def test_health_returns_extended_fields(client):
    """/api/health 扩展字段：status/version/database/timestamp 全部在位。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"]
    assert "timestamp" in body


def test_json_formatter_single_line_json_with_extra():
    """JsonFormatter：单行 JSON，msg 完成格式化，extra 字段自动并入。"""
    record = logging.LogRecord(
        "test.logger", logging.INFO, "mod.py", 1, "hello %s", ("world",), None, None
    )
    record.request_id = "r-1"
    record.duration_ms = 12.3
    line = JsonFormatter().format(record)
    parsed = json.loads(line)  # 可被 json 解析 = 单行合法 JSON
    assert parsed["msg"] == "hello world"
    assert parsed["logger"] == "test.logger"
    assert parsed["level"] == "INFO"
    assert parsed["request_id"] == "r-1"
    assert parsed["duration_ms"] == 12.3
    assert "ts" in parsed


def test_request_log_emits_structured_record(client, caplog):
    """请求日志中间件：每次 HTTP 请求产出结构化 LogRecord（method/path/status/耗时/IP）。"""
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/api/health")
    matches = [
        r
        for r in caplog.records
        if r.name == "app.request" and getattr(r, "path", None) == "/api/health"
    ]
    assert matches, "未捕获 app.request 请求日志"
    record = matches[-1]
    assert record.method == "GET"
    assert record.status_code == 200
    assert record.duration_ms >= 0
    assert record.client_ip