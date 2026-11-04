"""简历「模板预览」接口自检。

模板预览 = 用学生真实档案走与导出相同的渲染管线，任何签名/参数不一致都会
在运行期抛 NameError（历史上就因为漏了 industry/job_key 参数导致 500）。
这里用 TestClient 直接打接口，把三套模板 + 带/不带照片 + 自定义岗位都过一遍。

    D:/conda/envs/mianyang/python.exe scripts/check_resume_preview.py
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

USERNAME = "2024001"
PASSWORD = "123456"


def main() -> int:
    client = TestClient(app, raise_server_exceptions=True)
    token = client.post(
        "/api/auth/login", json={"username": USERNAME, "password": PASSWORD}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    failed = 0

    def check(label: str, params: dict) -> None:
        nonlocal failed
        try:
            r = client.get(
                "/api/portfolio/resume/template-preview", params=params, headers=headers
            )
        except Exception as exc:  # noqa: BLE001 - 自检要打印真实异常
            failed += 1
            print(f"FAIL {label}: {type(exc).__name__}: {exc}")
            return
        if r.status_code != 200:
            failed += 1
            print(f"FAIL {label}: HTTP {r.status_code} {r.text[:160]}")
            return
        image = r.json().get("image", "")
        if not image.startswith("data:image/png;base64,"):
            failed += 1
            print(f"FAIL {label}: 返回的不是 PNG dataURL")
            return
        png = base64.b64decode(image.split(",", 1)[1])
        if png[:8] != b"\x89PNG\r\n\x1a\n":
            failed += 1
            print(f"FAIL {label}: PNG 头不对")
            return
        print(f"PASS {label}: {len(png) // 1024}KB png")

    for key in ("classic", "accent", "compact"):
        check(f"{key} 默认参数", {"template_key": key})
        check(
            f"{key} 带行业岗位",
            {
                "template_key": key,
                "industry": "internet",
                "job_key": "backend",
                "job_type": "校招",
                "city": "杭州",
            },
        )

    check(
        "自定义岗位",
        {
            "template_key": "accent",
            "industry": "hardware",
            "job_key": "custom",
            "custom_job": "无人机飞手/运维",
        },
    )

    r = client.get(
        "/api/portfolio/resume/template-preview",
        params={"template_key": "nope"},
        headers=headers,
    )
    if r.status_code == 404:
        print("PASS 未知模板 → 404")
    else:
        failed += 1
        print(f"FAIL 未知模板应为 404，实际 {r.status_code}")

    print("\nALL CHECKS PASS" if not failed else f"\n{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
